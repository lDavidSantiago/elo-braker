from sqlalchemy import (
    ForeignKey,
    String,
    Integer,
    Boolean,
    Float,
    SmallInteger,
    Index,
    DateTime,
    BigInteger
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
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
    match_participants = relationship("MatchParticipant", back_populates="player", cascade="all, delete-orphan")


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
    participants = relationship("MatchParticipant", back_populates="match", cascade="all, delete-orphan")

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

    # (opcional) first blood/tower/inhib/baron/dragon 
    first_blood: Mapped[bool] = mapped_column(Boolean, default=False)
    first_tower: Mapped[bool] = mapped_column(Boolean, default=False)

    # (opcional) bans como texto/JSON 
    bans: Mapped[list] = mapped_column(JSONB, default=list)


class MatchParticipant(Base):
    __tablename__ = "match_participants"

    # ----- Keys (PK compuesta) -----
    match_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("matches.matchId", ondelete="CASCADE"),
        primary_key=True,
    )

    puuid: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("riot_user_profiles.puuid", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )

    # ----- Identity / team -----
    riot_id_name:Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    riot_id_tagline:Mapped[str | None] = mapped_column(String, nullable=True, index=True)

    participant_id: Mapped[int] = mapped_column(SmallInteger, index=True)
    team_id: Mapped[int] = mapped_column(SmallInteger, index=True)
    win: Mapped[bool] = mapped_column(Boolean, index=True)

    # ----- Champion / role -----
    champion_id: Mapped[int] = mapped_column(Integer, index=True)
    champ_level: Mapped[int] = mapped_column(SmallInteger)

    # Strings: TOP/JUNGLE/.../UTILITY
    individual_position: Mapped[str | None] = mapped_column(String(16), index=True)
    team_position: Mapped[str | None] = mapped_column(String(16), index=True)

    # ----- Core performance -----
    kills: Mapped[int] = mapped_column(SmallInteger)
    deaths: Mapped[int] = mapped_column(SmallInteger)
    assists: Mapped[int] = mapped_column(SmallInteger)

    killing_sprees: Mapped[int] = mapped_column(SmallInteger)
    double_kills: Mapped[int] = mapped_column(SmallInteger)
    triple_kills: Mapped[int] = mapped_column(SmallInteger)
    quadra_kills: Mapped[int] = mapped_column(SmallInteger)
    penta_kills: Mapped[int] = mapped_column(SmallInteger)

    # ----- Economy / farm -----
    gold_earned: Mapped[int] = mapped_column(Integer)
    gold_spent: Mapped[int] = mapped_column(Integer)
    total_minions_killed: Mapped[int] = mapped_column(Integer)
    neutral_minions_killed: Mapped[int] = mapped_column(Integer)

    # ----- Damage -----
    total_damage_dealt_to_champions: Mapped[int] = mapped_column(Integer)
    physical_damage_dealt_to_champions: Mapped[int] = mapped_column(Integer)
    magic_damage_dealt_to_champions: Mapped[int] = mapped_column(Integer)
    true_damage_dealt_to_champions: Mapped[int] = mapped_column(Integer)
    total_damage_taken: Mapped[int] = mapped_column(Integer)
    damage_self_mitigated: Mapped[int] = mapped_column(Integer)

    # ----- Objectives -----
    damage_dealt_to_objectives: Mapped[int] = mapped_column(Integer)
    damage_dealt_to_turrets: Mapped[int] = mapped_column(Integer)
    turret_takedowns: Mapped[int] = mapped_column(SmallInteger)
    inhibitor_takedowns: Mapped[int] = mapped_column(SmallInteger)
    dragon_kills: Mapped[int] = mapped_column(SmallInteger)
    baron_kills: Mapped[int] = mapped_column(SmallInteger)
    rift_herald_takedowns: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)

    # ----- Vision -----
    vision_score: Mapped[int] = mapped_column(Integer)
    wards_placed: Mapped[int] = mapped_column(SmallInteger)
    wards_killed: Mapped[int] = mapped_column(SmallInteger)
    detector_wards_placed: Mapped[int] = mapped_column(SmallInteger)

    # ----- Items -----
    item0: Mapped[int] = mapped_column(Integer)
    item1: Mapped[int] = mapped_column(Integer)
    item2: Mapped[int] = mapped_column(Integer)
    item3: Mapped[int] = mapped_column(Integer)
    item4: Mapped[int] = mapped_column(Integer)
    item5: Mapped[int] = mapped_column(Integer)
    item6: Mapped[int] = mapped_column(Integer)  # trinket

    # ----- Summoner spells -----
    summoner1_id: Mapped[int] = mapped_column(SmallInteger)
    summoner2_id: Mapped[int] = mapped_column(SmallInteger)

    # ----- Advanced (optional, from challenges) -----
    damage_per_minute: Mapped[float | None] = mapped_column(Float, nullable=True)
    gold_per_minute: Mapped[float | None] = mapped_column(Float, nullable=True)
    team_damage_percentage: Mapped[float | None] = mapped_column(Float, nullable=True)
    kill_participation: Mapped[float | None] = mapped_column(Float, nullable=True)
    vision_score_per_minute: Mapped[float | None] = mapped_column(Float, nullable=True)
    lane_minions_first_10_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    solo_kills: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)

    # ----- Optional relationships -----
    match = relationship("Matches", back_populates="participants")
    player = relationship("RiotUserProfile", back_populates="match_participants")

    __table_args__ = (
        Index("ix_mp_match_team", "match_id", "team_id"),
        Index("ix_mp_puuid_match", "puuid", "match_id"),
        Index("ix_mp_champion_role", "champion_id", "individual_position"),
    )