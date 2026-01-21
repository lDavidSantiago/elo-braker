
from enum import Enum

class RegionEq(str, Enum):
    br1 = "americas"
    la1 = "americas"
    la2 = "americas"
    na1 = "americas"
    eun1 = "europe"
    euw1 = "europe"
    tr1 = "europe"
    ru = "europe"
    jp1 = "asia"
    kr = "asia"
    sg2 = "asia"
    tw2 = "asia"
    vn2 = "asia"
    oc1 = "sea"

from pydantic import BaseModel
from typing import Optional

class SummonerRegion(BaseModel):
    puuid: str
    region: RegionEq  # aquí validará automáticamente que sea un valor del Enum
