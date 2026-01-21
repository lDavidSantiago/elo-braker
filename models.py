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


