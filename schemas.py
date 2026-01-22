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