from collections import defaultdict
import os
import httpx
from datetime import datetime, timedelta, timezone
from typing import Optional
import json
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import Matches, MatchTeam, MatchParticipant
from sqlalchemy.dialects.postgresql import insert
from models import RiotUserProfile,Matches
from schemas import RiotUserProfileCreate,MatchCreate,MatchTeamCreate,MatchParticipantCreate
from fastapi import HTTPException
RIOT_API_KEY = os.getenv("RIOT_API_KEY")

# TTLs (Time To Live)
SUMMONER_TTL = timedelta(hours=1)
MATCH_FETCH_TTL = timedelta(minutes=15)


# -----------------------------
# Helpers
# -----------------------------
def is_stale(profile: RiotUserProfile) -> bool:
    last_updated = profile.last_updated
    if last_updated is None:
        return True
    if last_updated.tzinfo is None:
        last_updated = last_updated.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - last_updated > SUMMONER_TTL


# -----------------------------
# DB CRUD (ASYNC)
# -----------------------------
async def create_summoner(db: AsyncSession, data: RiotUserProfileCreate) -> RiotUserProfile:
    profile_instance = RiotUserProfile(**data.model_dump())
    db.add(profile_instance)
    await db.commit()
    await db.refresh(profile_instance)
    return profile_instance


async def getSummoner(db: AsyncSession, puuid: str) -> RiotUserProfile | None:
    result = await db.execute(
        select(RiotUserProfile).where(RiotUserProfile.puuid == puuid)
    )
    return result.scalar_one_or_none()


async def getSummoner_by_name(db: AsyncSession, gameName: str, tagLine: str) -> RiotUserProfile | None:
    result = await db.execute(
        select(RiotUserProfile).where(
            RiotUserProfile.gameName == gameName,
            RiotUserProfile.tagLine == tagLine
        )
    )
    return result.scalar_one_or_none()


async def get_summoner_region_by_puuid(db: AsyncSession, puuid: str) -> str | None:
    try:
        result = await db.execute(
            select(RiotUserProfile.region).where(RiotUserProfile.puuid == puuid)
        )
        region = result.scalar_one_or_none()
        if region:
            print(region)
        return region
    except Exception as e:
        print(f"Error al consultar la DB: {e}")
        return None

async def create_or_update_summoner(db: AsyncSession, data: RiotUserProfileCreate) -> RiotUserProfile:
    profile = await getSummoner(db, data.puuid)

    if profile:
        # 1) 
        db_missing = (profile.summonerLevel is None) or (profile.profileIcon is None)
        data_has = (data.summonerLevel is not None) and (data.profileIcon is not None)

        must_update = db_missing and data_has

        # 2) 
        should_update = must_update or is_stale(profile)

        if should_update:
            # no pises con None
            for key, value in data.model_dump(exclude_none=True).items():
                setattr(profile, key, value)

            await db.commit()
            await db.refresh(profile)

        return profile

    # no existe -> crear
    profile_instance = RiotUserProfile(**data.model_dump())
    db.add(profile_instance)
    await db.commit()
    await db.refresh(profile_instance)
    return profile_instance

async def upsert_profiles_from_match(db: AsyncSession, raw_data: dict, region: str):
    rows = []
    region = raw_data["metadata"]["matchId"]

    for p in raw_data["info"]["participants"]:
        rows.append({
            "puuid": p["puuid"],
            "gameName": p.get("riotIdGameName"),
            "tagLine": p.get("riotIdTagline"),
            "region": region.split('_')[0].lower(),
        })
    rows.sort(key=lambda r: r["puuid"])# This line is important to deny Deadlock Error
    stmt = insert(RiotUserProfile).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["puuid"],
        set_={
            "gameName": stmt.excluded.gameName,
            "tagLine": stmt.excluded.tagLine,
            "region": stmt.excluded.region,
        }
    )
    await db.execute(stmt)

async def save_match(
    db: AsyncSession,
    match_data: MatchCreate,
    teams: list[MatchTeamCreate],
    players: list[MatchParticipantCreate],
) -> Matches:
    match_id = match_data.match_id  

    # ya existe?
    result = await db.execute(select(Matches).where(Matches.match_id == match_id))
    existing = result.scalar_one_or_none()
    if existing:
        return existing

    # Insert match
    match = Matches(
        match_id=match_data.match_id,
        platform_id=match_data.platform_id,
        queue_id=match_data.queue_id,
        game_mode=match_data.game_mode,
        game_version=match_data.game_version,
        game_start_ts=match_data.game_start_ts,
        duration_sec=match_data.duration_sec,
    )
    db.add(match)
   
    await db.flush()

    # Insert teams
    db.add_all([MatchTeam(**t.model_dump()) for t in teams])

    # Insert players
    db.add_all([MatchParticipant(**p.model_dump()) for p in players])

    await db.commit()
    await db.refresh(match)
    return match


# -----------------------------
# RIOT API 
# -----------------------------
async def get_puuid(gameName: str, tagLine: str, region: str = "americas") -> str:
    url = f"https://{region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{gameName}/{tagLine}"
    headers = {"X-Riot-Token": RIOT_API_KEY}
    async with httpx.AsyncClient() as client:
        puuid_response = await client.get(url, headers=headers)
        if puuid_response.status_code == 200:
            data = puuid_response.json()
            return data["puuid"]
        raise Exception(f"API error: {puuid_response.status_code} - {puuid_response.text}")


async def fetch_summoner_from_riot(gameName: str, tagLine: str, region: str = "americas") -> dict:
    headers = {"X-Riot-Token": RIOT_API_KEY}

    async with httpx.AsyncClient() as client:
        # Account info
        account_url = f"https://{region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{gameName}/{tagLine}"
        account_response = await client.get(account_url, headers=headers)
        if account_response.status_code != 200:
            raise Exception(f"Account API error: {account_response.status_code} - {account_response.text}")

        account_data = account_response.json()
        puuid = account_data["puuid"]

        # Summoner region
        get_region_url = f"https://{region}.api.riotgames.com/riot/account/v1/region/by-game/lol/by-puuid/{puuid}"
        region_response = await client.get(get_region_url, headers=headers)
        if region_response.status_code != 200:
            raise Exception(f"Summoner region API error: {region_response.status_code} - {region_response.text}")

        summoner_region = region_response.json()["region"]
        print(summoner_region)
        print(f"Región obtenida: {summoner_region}")

        # Profile icon + level
        summoner_level_icon_url = f"https://{summoner_region}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
        level_icon_response = await client.get(summoner_level_icon_url, headers=headers)
        if level_icon_response.status_code != 200:
            raise Exception(f"Summoner API error: {level_icon_response.status_code} - {level_icon_response.text}")

        summoner_level_icon_data = level_icon_response.json()

        return {
            "puuid": account_data["puuid"],
            "gameName": account_data["gameName"],
            "tagLine": account_data["tagLine"],
            "region": summoner_region,
            "summonerLevel": summoner_level_icon_data["summonerLevel"],
            "profileIcon": summoner_level_icon_data["profileIconId"],
        }

# -----------------------------
# GET MATCH DATA FROM USER
# -----------------------------

async def get_match_data(matchId:str,routingRegion:str,db:AsyncSession):
    url = f"https://{routingRegion}.api.riotgames.com/lol/match/v5/matches/{matchId}"
    headers = {"X-Riot-Token": RIOT_API_KEY}
    async with httpx.AsyncClient(timeout=20) as client:
        match_data_req = await client.get(url,headers=headers)
        match_data = match_data_req.json()
        if "info" not in match_data or "metadata" not in match_data:
            raise HTTPException(status_code=502, detail={"bad_payload": match_data})
        info = match_data["info"]
        meta = match_data["metadata"]

        filtered_data ={
            "matchId": meta["matchId"],
            "platformId" : info["platformId"],
            "queueId": info["queueId"],
            "gameMode": info["gameMode"],
            "gameVersion": info["gameVersion"],
            "gameStartTimestamp": info["gameStartTimestamp"],
            "gameDuration": info["gameDuration"],
    }
        match_schema = MatchCreate.model_validate(filtered_data)
        team_schemas =  await filter_match_team(match_data)
        players_schemas = await filter_participants_match_data(match_data)
        await upsert_profiles_from_match(db, match_data, routingRegion)
        await db.flush()
        await save_match(db, match_schema, team_schemas, players_schemas)

        return {
                "match": match_schema,
                "teams": team_schemas,
                "players": players_schemas
            }


async def filter_match_team(raw_data:dict) -> list[MatchTeamCreate]:
    info = raw_data["info"]
    meta = raw_data["metadata"]
    match_id = meta["matchId"]

    # KDA por team desde participants
    acc = defaultdict(lambda: {"kills": 0, "deaths": 0, "assists": 0})
    for p in info["participants"]:
        tid = p["teamId"]
        acc[tid]["kills"] += p.get("kills", 0)
        acc[tid]["deaths"] += p.get("deaths", 0)
        acc[tid]["assists"] += p.get("assists", 0)

    rows = []
    for t in info["teams"]:
        tid = t["teamId"]
        obj = t["objectives"]

        rows.append(MatchTeamCreate(
            match_id=match_id,
            team_id=tid,
            win=bool(t.get("win", False)),

            kills=acc[tid]["kills"],
            deaths=acc[tid]["deaths"],
            assists=acc[tid]["assists"],

            baron_kills=obj["baron"]["kills"],
            dragon_kills=obj["dragon"]["kills"],
            herald_kills=obj["riftHerald"]["kills"],
            tower_kills=obj["tower"]["kills"],
            inhib_kills=obj["inhibitor"]["kills"],

            bans=t.get("bans", [])
            #Bans list are like this
            # {
            #   "Champion id"
            #   "Pick Turn"
            #} 
        ))
    return rows

async def filter_participants_match_data(raw_data: dict) -> list[MatchParticipantCreate]:
    participants_models = []

    for p in raw_data["info"]["participants"]:

        pos = p.get("individualPosition") or ""
        pos = pos.upper()

        allowed = {"TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY", "INVALID", ""}
        if pos not in allowed:
            pos = "INVALID"

        mp = MatchParticipantCreate(
            match_id=raw_data["metadata"]["matchId"],
            puuid=p["puuid"],
            riot_id_name=p["riotIdGameName"],
            riot_id_tagline=p["riotIdTagline"],
            participant_id=p["participantId"],
            team_id=p["teamId"],
            win=p["win"],

            champion_id=p["championId"],
            champ_level=p["champLevel"],

            individual_position=pos,
            team_position=(p.get("teamPosition") or "").upper(),

            kills=p["kills"],
            deaths=p["deaths"],
            assists=p["assists"],
            killing_sprees=p["killingSprees"],
            double_kills=p["doubleKills"],
            triple_kills=p["tripleKills"],
            quadra_kills=p["quadraKills"],
            penta_kills=p["pentaKills"],

            gold_earned=p["goldEarned"],
            gold_spent=p["goldSpent"],
            total_minions_killed=p["totalMinionsKilled"],
            neutral_minions_killed=p["neutralMinionsKilled"],

            total_damage_dealt_to_champions=p["totalDamageDealtToChampions"],
            physical_damage_dealt_to_champions=p["physicalDamageDealtToChampions"],
            magic_damage_dealt_to_champions=p["magicDamageDealtToChampions"],
            true_damage_dealt_to_champions=p["trueDamageDealtToChampions"],
            total_damage_taken=p["totalDamageTaken"],
            damage_self_mitigated=p["damageSelfMitigated"],

            damage_dealt_to_objectives=p["damageDealtToObjectives"],
            damage_dealt_to_turrets=p["damageDealtToTurrets"],
            turret_takedowns=p["turretTakedowns"],
            inhibitor_takedowns=p["inhibitorTakedowns"],
            dragon_kills=p["dragonKills"],
            baron_kills=p["baronKills"],

            vision_score=p["visionScore"],
            wards_placed=p["wardsPlaced"],
            wards_killed=p["wardsKilled"],
            detector_wards_placed=p["detectorWardsPlaced"],
            kill_participation = p["challenges"].get("killParticipation", 0) * 100,

            item0=p["item0"],
            item1=p["item1"],
            item2=p["item2"],
            item3=p["item3"],
            item4=p["item4"],
            item5=p["item5"],
            item6=p["item6"],

            summoner1_id=p["summoner1Id"],
            summoner2_id=p["summoner2Id"],
        )

        participants_models.append(mp)

    return participants_models

async def fetch_get_matches(puuid: str, region: str,num_matches: int = 20 , queue: Optional[str] = None) -> list:
    url = f"https://{region}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids"
    headers = {"X-Riot-Token": RIOT_API_KEY}
    params : dict = {"count": num_matches}
    if queue is not None:
        params["queue"] = queue
    async with httpx.AsyncClient(timeout=20) as client:
        summoner_matches_ids_req = await client.get(url,headers=headers,params=params)
        if summoner_matches_ids_req.status_code != 200:
             raise Exception(f"Summoner API error: {summoner_matches_ids_req.status_code} - {summoner_matches_ids_req.text}")
        data = summoner_matches_ids_req.json()
        return data



async def get_summoner_entries(puuid:str,region:str = "la1"):
    headers = {"X-Riot-Token": RIOT_API_KEY}
    async with httpx.AsyncClient(timeout=20) as client:
        url = f"https://{region}.api.riotgames.com/lol/league/v4/entries/by-puuid/{puuid}"
        summoner_entries_request = await client.get(url,headers=headers)
        if summoner_entries_request.status_code != 200:
             raise HTTPException(
        status_code=summoner_entries_request.status_code,
        detail=summoner_entries_request.text
    )
        data = summoner_entries_request.json()
        return data