from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime, JSON, BigInteger
from sqlalchemy.orm import Mapped, mapped_column
from db import Base
from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import JSONB


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

    match_id: Mapped[str] = mapped_column(
        "matchId", primary_key=True, index=True
    )
    platform_id: Mapped[str] = mapped_column(index=True)
    queue_id: Mapped[int] = mapped_column(index=True)
    game_mode: Mapped[str] = mapped_column(index=True)
    game_version: Mapped[str] = mapped_column(index=True)
    game_start_ts: Mapped[int] = mapped_column(BigInteger, index=True)
    duration_sec: Mapped[int] = mapped_column(index=True)

class MatchTeam(Base):
    __tablename__ = "match_teams"

    match_id: Mapped[str] = mapped_column(ForeignKey("matches.matchId"), primary_key=True)
    team_id: Mapped[int] = mapped_column(primary_key=True)  # 100 / 200

    win: Mapped[bool] = mapped_column(Boolean, index=True)

    # Team totals (calculados con participants)
    kills: Mapped[int] = mapped_column(Integer)
    deaths: Mapped[int] = mapped_column(Integer)
    assists: Mapped[int] = mapped_column(Integer)

    # Objectives (vienen de info["teams"][i]["objectives"])
    baron_kills: Mapped[int] = mapped_column(Integer)
    dragon_kills: Mapped[int] = mapped_column(Integer)
    herald_kills: Mapped[int] = mapped_column(Integer)
    tower_kills: Mapped[int] = mapped_column(Integer)
    inhib_kills: Mapped[int] = mapped_column(Integer)

    # (opcional) first blood/tower/inhib/baron/dragon (si te interesa)
    first_blood: Mapped[bool] = mapped_column(Boolean, default=False)
    first_tower: Mapped[bool] = mapped_column(Boolean, default=False)

    # (opcional) bans como texto/JSON (si quieres guardar)
    bans: Mapped[list] = mapped_column(JSONB, default=list)
