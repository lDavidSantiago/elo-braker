from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime, JSON, BigInteger
from sqlalchemy.orm import Mapped, mapped_column
from db import Base
from datetime import datetime, timezone


class RiotUserProfile(Base):
    __tablename__ = "riot_user_profiles"

    puuid: Mapped[str] = mapped_column(String(78), primary_key=True, index=True)
    gameName: Mapped[str] = mapped_column(String, index=True)
    tagLine: Mapped[str] = mapped_column(String, index=True)
    region: Mapped[str] = mapped_column(String, index=True)

    summonerLevel: Mapped[int | None] = mapped_column(Integer, nullable=True)
    profileIcon: Mapped[int | None] = mapped_column(Integer, nullable=True)

    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

class Matches(Base):
    __tablename__ = "matches"
    matchId : Mapped[str] = mapped_column(primary_key=True, index=True)
    platform_id : Mapped [str] = mapped_column(index=True)
    queue_id : Mapped[int] = mapped_column(index = True)
    game_mode : Mapped[str] = mapped_column(index = True)
    game_version: Mapped[str] = mapped_column(index=True)
    game_start_ts: Mapped[int] = mapped_column(BigInteger, index=True)
    duration_sec : Mapped[int] = mapped_column(index=True)
