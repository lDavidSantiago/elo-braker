from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Annotated, Optional
import services,models,schemas
from db import get_db,engine
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone  
from constants import Queues , Regions
app = FastAPI()

@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute("SELECT 1")
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/summoner/{puuid}", response_model=schemas.RiotUserProfile)
async def get_summoner(puuid: str, db: Session = Depends(get_db)):
    summoner = services.getSummoner(db, puuid)
    if not summoner:
        raise HTTPException(status_code=404, detail="Summoner not found")
    return summoner


@app.post("/summoners/", response_model=schemas.RiotUserProfile)
async def create_summoner(gameName: str, tagLine: str, region: str = "americas", db: Session = Depends(get_db)):
    # Busca si existe
    profile = services.getSummoner_by_name(db, gameName, tagLine)
    
    if profile and not services.is_stale(profile):
        print("No need to update")
        return profile
    
    # Fetch desde Riot
    riot_data = await services.fetch_summoner_from_riot(gameName, tagLine, region)
    print("Actualize o Cree")
    profile_data = schemas.RiotUserProfileCreate(
        puuid=riot_data["puuid"],
        gameName=riot_data["gameName"],
        tagLine=riot_data["tagLine"],
        region=riot_data["region"],
        summonerLevel=riot_data["summonerLevel"],
        profileIcon=riot_data["profileIcon"],
        last_updated=datetime.now(timezone.utc)
    )
    
    # Inserta o actualiza según sea necesario
    return services.create_or_update_summoner(db, profile_data)

@app.get("/summoner/{puuid}/matches/")
async def get_summoner_matches(puuid:str , count : int = 20, queue: Optional[str] = None,db: Session = Depends(get_db)):
    get_summoner_region = services.get_summoner_region_by_puuid(db, puuid)
    region = Regions.RegionEq[get_summoner_region].value
    gamesId = await services.fetch_get_matches(puuid,region,queue)
    return gamesId
    
        
