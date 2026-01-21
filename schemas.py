from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class RiotUserProfileBase(BaseModel):
    puuid: str
    gameName: str
    tagLine: str
    region: str
    summonerLevel: Optional[int] = None
    profileIcon: Optional[int] = None
    last_updated: Optional[datetime] = None

class RiotUserProfileCreate(RiotUserProfileBase):
    pass  


class RiotUserProfile(RiotUserProfileBase):
    class Config:
        from_attributes = True 


# ← NUEVOS SCHEMAS AQUÍ ↓

class MatchParticipantBase(BaseModel):
    """Schema base para un participante de partida"""
    puuid: str
    summonerName: Optional[str] = None
    championId: Optional[int] = None
    championName: Optional[str] = None
    teamId: Optional[int] = None
    teamPosition: Optional[str] = None
    kills: Optional[int] = None
    deaths: Optional[int] = None
    assists: Optional[int] = None
    goldEarned: Optional[int] = None
    totalDamageDealt: Optional[int] = None
    totalDamageTaken: Optional[int] = None
    visionScore: Optional[int] = None
    totalMinionsKilled: Optional[int] = None
    neutralMinionsKilled: Optional[int] = None
    items: Optional[List[int]] = None
    win: Optional[bool] = None


class MatchParticipant(MatchParticipantBase):
    """Schema completo con ID y matchId (para leer de DB)"""
    id: int
    matchId: str
    
    class Config:
        from_attributes = True


class MatchBase(BaseModel):
    """Schema base para una partida"""
    matchId: str
    gameMode: Optional[str] = None
    queueId: Optional[int] = None
    gameDuration: Optional[int] = None
    gameCreation: Optional[int] = None
    gameVersion: Optional[str] = None
    platformId: Optional[str] = None


class Match(MatchBase):
    """Schema completo de partida con participantes (para leer de DB)"""
    participants: List[MatchParticipant] = []
    
    class Config:
        from_attributes = True


class MatchCreate(MatchBase):
    """Schema para crear una partida (cuando viene de Riot API)"""
    participants: List[MatchParticipantBase] = []