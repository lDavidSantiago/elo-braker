import os
import httpx
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import RiotUserProfile,Matches
from schemas import RiotUserProfileCreate,MatchCreate

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
    print(data.puuid,"Esto es <---")
    if profile:
        if is_stale(profile):
            for key, value in data.model_dump().items():
                setattr(profile, key, value)
            await db.commit()
            await db.refresh(profile)
            print("i did this")
        return profile

    # no existe -> crear
    profile_instance = RiotUserProfile(**data.model_dump())
    db.add(profile_instance)
    await db.commit()
    await db.refresh(profile_instance)
    return profile_instance


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

async def get_match_data(matchId:str,routingRegion:str):
    url = f"https://{routingRegion}.api.riotgames.com/lol/match/v5/matches/{matchId}"
    headers = {"X-Riot-Token": RIOT_API_KEY}
    async with httpx.AsyncClient(timeout=20) as client:
        match_data_req = await client.get(url,headers=headers)
        match_data = match_data_req.json()
        info = match_data["info"]
        meta = match_data["metadata"]

        filtered_data ={
            "matchId": meta["matchId"],
            "platform_id" : info["platformId"],
            "queueId": info["queueId"],
            "gameMode": info["gameMode"],
            "gameVersion": info["gameVersion"],
            "gameStartTimestamp": info["gameStartTimestamp"],
            "gameDuration": info["gameDuration"],
    }
        return filtered_data


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
        summoner_matches_ids_data = {

        }



