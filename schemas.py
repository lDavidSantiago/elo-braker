from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Literal
from datetime import datetime

class RiotUserProfileBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    puuid: str
    gameName: str
    tagLine: str
    region: str
    summonerLevel: Optional[int] = None
    profileIcon: Optional[int] = None

    # Nombre interno (snake_case) -> alias externo (camelCase)
    last_updated: Optional[datetime] = Field(default=None, alias="lastUpdated")


class RiotUserProfileCreate(RiotUserProfileBase):
    pass


class RiotUserProfile(RiotUserProfileBase):
    pass

class MatchBase(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )
    match_id: str = Field(alias="matchId")
    platform_id: str = Field(alias="platformId")
    queue_id: int = Field(alias="queueId")
    game_mode: str = Field(alias="gameMode")
    game_version: str = Field(alias="gameVersion")
    game_start_ts: int = Field(alias="gameStartTimestamp")
    duration_sec: int = Field(alias="gameDuration")

class Match(MatchBase):
    pass

class MatchCreate(MatchBase):
    pass

class MatchTeamBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    match_id: str
    team_id: int  # 100 / 200

    win: bool

    kills: int = 0
    deaths: int = 0
    assists: int = 0

    baron_kills: int = 0
    dragon_kills: int = 0
    herald_kills: int = 0
    tower_kills: int = 0
    inhib_kills: int = 0

    first_blood: bool = False
    first_tower: bool = False

    bans: list[dict] = []


class MatchTeam(MatchTeamBase):
    pass


class MatchTeamCreate(MatchTeamBase):
    pass

Position = Literal["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY", "INVALID", ""]


class MatchParticipantBase(BaseModel):
    model_config = ConfigDict(extra="ignore", from_attributes=True)

    # ----- Keys -----
    match_id: str
    puuid: str

    # ----- Identity / team -----
        # ----- Identity / team -----
    riot_id_name:str
    riot_id_tagline:str
    participant_id: int
    team_id: int
    win: bool

    # ----- Champion / role -----
    champion_id: int
    champ_level: int
    individual_position: Optional[Position] = None
    team_position: Optional[Position] = None

    # ----- Core performance -----
    kills: int
    deaths: int
    assists: int
    killing_sprees: int
    double_kills: int
    triple_kills: int
    quadra_kills: int
    penta_kills: int

    # ----- Economy / farm -----
    gold_earned: int
    gold_spent: int
    total_minions_killed: int
    neutral_minions_killed: int

    # ----- Damage -----
    total_damage_dealt_to_champions: int
    physical_damage_dealt_to_champions: int
    magic_damage_dealt_to_champions: int
    true_damage_dealt_to_champions: int
    total_damage_taken: int
    damage_self_mitigated: int

    # ----- Objectives -----
    damage_dealt_to_objectives: int
    damage_dealt_to_turrets: int
    turret_takedowns: int
    inhibitor_takedowns: int
    dragon_kills: int
    baron_kills: int
    rift_herald_takedowns: Optional[int] = None

    # ----- Vision -----
    vision_score: int
    wards_placed: int
    wards_killed: int
    detector_wards_placed: int

    # ----- Items -----
    item0: int
    item1: int
    item2: int
    item3: int
    item4: int
    item5: int
    item6: int

    # ----- Summoner spells -----
    summoner1_id: int
    summoner2_id: int

    # ----- Advanced (optional) -----
    damage_per_minute: Optional[float] = None
    gold_per_minute: Optional[float] = None
    team_damage_percentage: Optional[float] = None
    kill_participation: Optional[float] = None
    vision_score_per_minute: Optional[float] = None
    lane_minions_first_10_minutes: Optional[int] = None
    solo_kills: Optional[int] = None

class MatchParticipant(MatchParticipantBase):
    pass


class MatchParticipantCreate(MatchParticipantBase):
    pass