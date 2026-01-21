from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class RiotUserProfileBase(BaseModel):
    puuid: str
    gameName: str
    tagLine: str
    region: str
    summonerLevel: Optional[int] = None
    profileIcon: Optional[int] = None
    lastUpdated: Optional[datetime] = None

class RiotUserProfileCreate(RiotUserProfileBase):
    pass  


class RiotUserProfile(RiotUserProfileBase):
    class Config:
        from_attributes = True 


