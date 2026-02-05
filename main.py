from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import datetime, timezone
from typing import Optional
import services, schemas
from db import get_db
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
CORSMiddleware,
allow_origins=["http://localhost:5173","https://league.ldavidsantiago.dev"],
allow_credentials=False,
allow_methods=["*"],
allow_headers=["*"],
)

@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.post("/summoners/", response_model=schemas.RiotUserProfile)
async def create_summoner(
    gameName: str,
    tagLine: str,
    region: str = "americas",
    db: AsyncSession = Depends(get_db)
):
    
    profile = await services.getSummoner_by_name(db, gameName, tagLine)
    if profile and  not services.is_stale(profile):
            return profile
    riot_data = await services.fetch_summoner_from_riot(gameName, tagLine, region)

    profile_data = schemas.RiotUserProfileCreate(
        puuid=riot_data["puuid"],
        gameName=riot_data["gameName"],
        tagLine=riot_data["tagLine"],
        region=riot_data["region"],
        summonerLevel=riot_data["summonerLevel"],
        profileIcon=riot_data["profileIcon"],
        last_updated=datetime.now(timezone.utc)
    )

    return await services.create_or_update_summoner(db, profile_data)

@app.get("/summoners/{puuid}/matches")
async def matches_check(
    puuid: str,
    region: str,
    num_matches: int = 20,
    queue: Optional[int] = None,
):
    return await services.fetch_get_matches(
        puuid=puuid,
        region=region,
        num_matches=num_matches,
        queue=queue,
    )
@app.get("/matches/{matchId}")
async def match_data(matchId:str,routingRegion:str,db: AsyncSession = Depends(get_db)
):
    return await services.get_match_data(
        matchId=matchId,
        routingRegion=routingRegion,
        db=db
    )
@app.get("/summoners/ranked")
async def rank_data(puuid: str, region: str = "la1"):
    return await services.get_summoner_entries(puuid=puuid, region=region)
