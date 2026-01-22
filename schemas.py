from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
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