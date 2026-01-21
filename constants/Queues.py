from enum import Enum

class QueueId(Enum):
    
    RANKED_SOLO = 420
    RANKED_FLEX = 440
    ARAM = 450
    ONE_FOR_ALL = 1020
    URF = 1900

# uso en Pydantic/FastAPI
from pydantic import BaseModel

class MatchInfo(BaseModel):
    match_id: str
    queue: QueueId
