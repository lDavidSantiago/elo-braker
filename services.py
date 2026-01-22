from collections import defaultdict
import os
import httpx
from datetime import datetime, timedelta, timezone
from typing import Optional
import json
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import RiotUserProfile,Matches
from schemas import RiotUserProfileCreate,MatchCreate,MatchTeamCreate

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
        if is_stale(profile):
            for key, value in data.model_dump().items():
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

async def save_match (db:AsyncSession, data:MatchCreate) -> Matches:
     # 1. Buscar si ya existe
    result = await db.execute(
        select(Matches).where(Matches.match_id == data.match_id)
    )
    existing_match = result.scalar_one_or_none()

    if existing_match:
        return existing_match  # 👈 ya estaba guardado
    match = Matches(**data.model_dump())
    db.add(match)
    await db.commit()
    await db.refresh(match)
    return match


# -----------------------------
# RIOT API (ya estaba ASYNC ✅)
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
        await save_match(db,match_schema)

        team_schemas =  filter_match_team(match_data)

        return {
                "match": match_schema,
                "teams": team_schemas,
            }


def filter_match_team(raw_data:dict) -> list[MatchTeamCreate]:
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

            bans=t.get("bans", [])  # ✅ lista directa
        ))
    return rows


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



