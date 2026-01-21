from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime, JSON, BigInteger
from sqlalchemy.orm import relationship
from db import Base
from datetime import datetime, timezone


class RiotUserProfile(Base):
    __tablename__ = "riot_user_profiles"
    puuid = Column(String(78), primary_key=True, index=True)
    gameName = Column(String, index=True)
    tagLine = Column(String, index=True)
    region = Column(String, index=True)
    summonerLevel = Column(Integer, nullable=True)
    profileIcon = Column(Integer, nullable=True)
    last_updated = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    matches_last_fetched = Column(DateTime, nullable=True)


# ← NUEVAS CLASES AQUÍ ↓

class Match(Base):
    __tablename__ = "matches"
    
    matchId = Column(String, primary_key=True, index=True)
    gameMode = Column(String, nullable=True)
    queueId = Column(Integer, nullable=True)
    gameDuration = Column(Integer, nullable=True)  # en segundos
    gameCreation = Column(BigInteger, nullable=True)  # timestamp
    gameVersion = Column(String, nullable=True)
    platformId = Column(String, nullable=True)
    
    # Relación: una partida tiene muchos participantes
    participants = relationship("MatchParticipant", back_populates="match")


class MatchParticipant(Base):
    __tablename__ = "match_participants"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    matchId = Column(String, ForeignKey("matches.matchId"), index=True)
    puuid = Column(String(78), ForeignKey("riot_user_profiles.puuid"), index=True)
    
    # Info básica
    summonerName = Column(String, nullable=True)
    championId = Column(Integer, nullable=True)
    championName = Column(String, nullable=True)
    teamId = Column(Integer, nullable=True)  # 100 o 200
    teamPosition = Column(String, nullable=True)  # TOP, JUNGLE, MIDDLE, etc.
    
    # Stats
    kills = Column(Integer, nullable=True)
    deaths = Column(Integer, nullable=True)
    assists = Column(Integer, nullable=True)
    goldEarned = Column(Integer, nullable=True)
    totalDamageDealt = Column(Integer, nullable=True)
    totalDamageTaken = Column(Integer, nullable=True)
    visionScore = Column(Integer, nullable=True)
    totalMinionsKilled = Column(Integer, nullable=True)
    neutralMinionsKilled = Column(Integer, nullable=True)
    
    # Items (guardamos como JSON array)
    items = Column(JSON, nullable=True)
    
    # Win/Loss
    win = Column(Boolean, nullable=True)
    
    # Relación: cada participante pertenece a una partida
    match = relationship("Match", back_populates="participants")