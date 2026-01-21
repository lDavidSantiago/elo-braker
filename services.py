from models import RiotUserProfile, Match, MatchParticipant     
from sqlalchemy.orm import Session 
from sqlalchemy.exc import SQLAlchemyError
from schemas import RiotUserProfileCreate, MatchCreate, MatchParticipantBase  
import os
import httpx
from datetime import datetime, timedelta, timezone
from typing import List,Optional  # ← Agregar esto

RIOT_API_KEY = os.getenv("RIOT_API_KEY")

# TTLs (Time To Live)
SUMMONER_TTL = timedelta(hours=1)
MATCH_FETCH_TTL = timedelta(minutes=15)


def create_summoner(db: Session, data: RiotUserProfileCreate):
    profile_instance = RiotUserProfile(**data.model_dump()) 
    db.add(profile_instance)
    db.commit()
    db.refresh(profile_instance)  
    return profile_instance

def create_or_update_summoner(db: Session, data: RiotUserProfileCreate):
    # Busca por puuid
    profile = getSummoner(db, data.puuid)

    if profile:
        # Si ya existe, solo actualiza si está stale
        if is_stale(profile):
            for key, value in data.model_dump().items():
                setattr(profile, key, value)
            db.commit()
            db.refresh(profile)
        return profile
    else:
        # Si no existe, inserta
        profile_instance = RiotUserProfile(**data.model_dump())
        db.add(profile_instance)
        db.commit()
        db.refresh(profile_instance)
        return profile_instance


def getSummoner(db: Session, puuid: str):
    return db.query(RiotUserProfile).filter(RiotUserProfile.puuid == puuid).first()

def getSummoner_by_name(db: Session, gameName: str, tagLine: str):
    return db.query(RiotUserProfile).filter(
        RiotUserProfile.gameName == gameName,
        RiotUserProfile.tagLine == tagLine
    ).first()

def get_summoner_region_by_puuid(db: Session, puuid: str) -> str | None:
    try:
        result = db.query(RiotUserProfile.region).filter(RiotUserProfile.puuid == puuid).first()
        if result:
            print(result[0])
            return result[0]  
        return None
    except Exception as e:
        print(f"Error al consultar la DB: {e}")
        return None


def is_stale(profile):
    last_updated = profile.last_updated
    # Si es naive, lo hacemos aware
    if last_updated.tzinfo is None:
        last_updated = last_updated.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - last_updated > SUMMONER_TTL



#RIOT API LOGIC
async def get_puuid(gameName: str, tagLine: str, region: str = "americas"):
    url = f"https://{region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{gameName}/{tagLine}" 
    headers = {"X-Riot-Token": RIOT_API_KEY}
    async with httpx.AsyncClient() as client:  
        puuid_response = await client.get(url, headers=headers)
        if puuid_response.status_code == 200:  
            data = puuid_response.json()
            return data["puuid"] 
        else:
            raise Exception(f"API error: {puuid_response.status_code} - {puuid_response.text}")


async def fetch_summoner_from_riot(gameName: str, tagLine: str, region: str = "americas"):
    #Get Summoner Puuid , GameName and TagLine
    account_url = f"https://{region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{gameName}/{tagLine}"
    headers = {"X-Riot-Token": RIOT_API_KEY}
    async with httpx.AsyncClient() as client:
        account_response = await client.get(account_url, headers=headers)
        if account_response.status_code != 200:
            raise Exception(f"Account API error: {account_response.status_code} - {account_response.text}")
        #Get Summoner Region
        account_data = account_response.json()
        puuid = account_data["puuid"]

        get_region_url = f"https://{region}.api.riotgames.com/riot/account/v1/region/by-game/lol/by-puuid/{puuid}"
        region_response = await client.get(get_region_url,headers=headers)
        if region_response.status_code != 200:
            raise Exception(f"Summoner API error: {region_response.status_code} - {region_response.text}")
        summoner_region = region_response.json()["region"]
        print(f"Región obtenida: {summoner_region}") 
        
        #Get Summoner ProfileIcon and AccountLevel
        summoner_level_icon_url = f"https://{summoner_region}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
        level_icon_response = await client.get(summoner_level_icon_url,headers=headers)
        if level_icon_response.status_code != 200:
            raise Exception(f"Summoner API error: {region_response.status_code} - {region_response.text}")
        summoner_level_icon_data = level_icon_response.json()

        combined_data = {
            "puuid": account_data["puuid"],
            "gameName": account_data["gameName"],
            "tagLine": account_data["tagLine"],
            "region" : summoner_region,
            "summonerLevel" : summoner_level_icon_data["summonerLevel"],
            "profileIcon" : summoner_level_icon_data["profileIconId"]
        }
        return combined_data
    

async def fetch_get_matches(puuid: str, region: str, queue: Optional[str] = None):
    url = f"https://{region}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids"
    headers = {"X-Riot-Token": RIOT_API_KEY}
    # Query params
    params = {"start": 0, "count": 20}
    print(f"Me mandaste {queue} y los params son {params} ")

    if queue is not None:  # Solo agregar si hay valor
        params["queue"] = queue
        print(f"Me mandaste {queue} y los params son {params} ")
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            # Mejor lanzar excepción con info de error
            raise Exception(f"Riot API error {response.status_code}: {response.text}")



