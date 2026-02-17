# elo-braker - League of Legends Stats Tracker


A FastAPI caching proxy for the Riot Games API that stores and serves League of Legends player profiles, match lists, match details, and ranked stats with PostgreSQL persistence and TTL-based cache invalidation. [1](#0-0) [2](#0-1) 

## Features

- **Player profiles**: Create/refresh by Riot ID with 1‑hour TTL [3](#0-2) 
- **Match lists**: Fetch recent match IDs with optional queue filter [4](#0-3) 
- **Match details**: Store teams and per‑participant stats with 15‑minute TTL [5](#0-4) 
- **Ranked stats**: Return league entries by PUUID [6](#0-5) 
- **CORS**: Local dev and production frontend origins [7](#0-6) 
- **Deadlock‑safe bulk upserts** for participant profiles [8](#0-7) 

## Tech Stack

- **Runtime**: Python 3.11+
- **Web**: FastAPI with `httpx.AsyncClient` for Riot API calls [9](#0-8) 
- **Database**: PostgreSQL 16 with SQLAlchemy async ORM and connection pooling [10](#0-9) 
- **Validation**: Pydantic schemas with ORM mode and field aliases [11](#0-10) 
- **Environment**: `python-dotenv` for secrets [12](#0-11) 

## Quick Start

1. Clone and install deps:
   ```bash
   git clone https://github.com/lDavidSantiago/elo-braker
   cd elo-braker
   pip install -r requirements.txt
   ```

2. Create `.env`:
   ```env
   POSTGRESQL_URL=postgresql+asyncpg://user:pass@host/db?sslmode=require
   RIOT_API_KEY=your_riot_api_key
   ```

3. Run (auto‑creates tables):
   ```bash
   uvicorn main:app --reload
   ```

   - Health check: `GET /health` [13](#0-12) 
   - Docs: `http://localhost:8000/docs`

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | DB connectivity check [13](#0-12)  |
| POST | `/summoners/` | Create/refresh summoner profile by `gameName` + `tagLine` [14](#0-13)  |
| GET | `/summoners/{puuid}/matches` | List recent match IDs (supports `queue` filter) [15](#0-14)  |
| GET | `/matches/{matchId}` | Fetch and store match details (teams + participants) [16](#0-15)  |
| GET | `/summoners/ranked` | Ranked league entries by `puuid` [17](#0-16)  |

## Architecture Overview

```mermaid
graph TB
  subgraph "Presentation"
    CORS["CORSMiddleware"]
    ROUTES["FastAPI routes"]
  end
  subgraph "Application"
    HANDLERS["Endpoint handlers"]
    DEPS["get_db"]
  end
  subgraph "Business Logic"
    RIOT["Riot API client"]
    XFORM["Data transformers"]
    CACHE["Cache/TTL"]
    CRUD["DB ops"]
  end
  subgraph "Validation"
    PYDANTIC["Pydantic schemas"]
  end
  subgraph "Data Access"
    ORM["SQLAlchemy models"]
    ENGINE["AsyncEngine"]
  end
  subgraph "Persistence"
    PG[(PostgreSQL)]
  end
  CORS --> ROUTES
  ROUTES --> HANDLERS
  HANDLERS --> DEPS
  DEPS --> RIOT
  DEPS --> XFORM
  DEPS --> CACHE
  DEPS --> CRUD
  RIOT --> PYDANTIC
  XFORM --> PYDANTIC
  CACHE --> PYDANTIC
  CRUD --> PYDANTIC
  PYDANTIC --> ORM
  ORM --> ENGINE
  ENGINE --> PG
```

- **Layers**: 5‑tier async stack (Presentation → Application → Business → Validation → Data Access → Persistence). [18](#0-17) 
- **Cache‑first**: Handlers check local DB before calling Riot API; TTLs control freshness. [19](#0-18) 
- **Transactional inserts**: `save_match` flushes before adding children to satisfy FKs. [20](#0-19) 

## Data Model

```mermaid
erDiagram
  RiotUserProfile ||--o{ MatchParticipant : "puuid"
  Matches ||--|{ MatchParticipant : "match_id"
  Matches ||--|{ MatchTeam : "match_id"
  RiotUserProfile {
    string puuid PK
    string gameName
    string tagLine
    string region
    int summonerLevel
    int profileIcon
    datetime last_updated
  }
  Matches {
    string match_id PK
    string platform_id
    int queue_id
    string game_mode
    string game_version
    bigint game_start_ts
    int duration_sec
  }
  MatchTeam {
    string match_id PK,FK
    int team_id PK
    bool win
    int kills
    int deaths
    int assists
    int baron_kills
    int dragon_kills
    int herald_kills
    int tower_kills
    int inhib_kills
    jsonb bans
  }
  MatchParticipant {
    string match_id PK,FK
    string puuid PK,FK
    int participant_id
    int team_id
    bool win
    int champion_id
    string individual_position
    int kills
    int deaths
    int assists
    int gold_earned
    int total_damage_dealt_to_champions
    int vision_score
    int item0_through_item6
  }
```

- Tables: `riot_user_profiles`, `matches`, `match_teams`, `match_participants`. [21](#0-20) 
- Indexes: composite indexes on participants for team, player history, and champion/role queries. [22](#0-21) 

## Environment Variables

| Variable | Required? | Example |
|----------|-----------|---------|
| `POSTGRESQL_URL` | Yes | `postgresql+asyncpg://user:pass@host/db?sslmode=require` [23](#0-22)  |
| `RIOT_API_KEY` | Yes | `RGAPI-...` [24](#0-23)  |

## Development Notes

- All I/O is async (`httpx.AsyncClient`, `AsyncSession`). [9](#0-8) [25](#0-24) 
- Pydantic schemas use `from_attributes=True` to bridge ORM ↔ API. [11](#0-10) 
- Deadlock prevention: profiles are sorted by `puuid` before bulk upsert. [8](#0-7) 
- CORS allows `localhost:5173` and `https://league.ldavidsantiago.dev`. [7](#0-6) 

## Notes

- TTLs: Summoner 1 hour, Match 15 minutes. [2](#0-1) 
- Match insertion is idempotent; existing matches are returned without re-insertion. [26](#0-25) 
- The `create_table` helper can be used for initial DB provisioning. [27](#0-26) 


### Citations

**File:** main.py (L1-8)
```python
from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import datetime, timezone
from typing import Optional
import services, schemas
from db import get_db
from fastapi.middleware.cors import CORSMiddleware
```

**File:** main.py (L10-18)
```python
app = FastAPI()

app.add_middleware(
CORSMiddleware,
allow_origins=["http://localhost:5173","https://league.ldavidsantiago.dev"],
allow_credentials=False,
allow_methods=["*"],
allow_headers=["*"],
)
```

**File:** main.py (L20-26)
```python
@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
```

**File:** main.py (L28-51)
```python
@app.post("/summoners/", response_model=schemas.RiotUserProfile)
async def create_summoner(
    gameName: str,
    tagLine: str,
    region: str = "americas",
    db: AsyncSession = Depends(get_db)
):
    
    profile = await services.getSummoner_by_name(db, gameName, tagLine)
    if profile and  not services.is_stale(profile):
            return profile
    riot_data = await services.fetch_summoner_from_riot(gameName, tagLine, region)

    profile_data = schemas.RiotUserProfileCreate(
        puuid=riot_data["puuid"],
        gameName=riot_data["gameName"],
        tagLine=riot_data["tagLine"],
        region=riot_data["region"],
        summonerLevel=riot_data["summonerLevel"],
        profileIcon=riot_data["profileIcon"],
        last_updated=datetime.now(timezone.utc)
    )

    return await services.create_or_update_summoner(db, profile_data)
```

**File:** main.py (L53-65)
```python
@app.get("/summoners/{puuid}/matches")
async def matches_check(
    puuid: str,
    region: str,
    num_matches: int = 20,
    queue: Optional[int] = None,
):
    return await services.fetch_get_matches(
        puuid=puuid,
        region=region,
        num_matches=num_matches,
        queue=queue,
    )
```

**File:** main.py (L66-73)
```python
@app.get("/matches/{matchId}")
async def match_data(matchId:str,routingRegion:str,db: AsyncSession = Depends(get_db)
):
    return await services.get_match_data(
        matchId=matchId,
        routingRegion=routingRegion,
        db=db
    )
```

**File:** main.py (L74-76)
```python
@app.get("/summoners/ranked")
async def rank_data(puuid: str, region: str = "la1"):
    return await services.get_summoner_entries(puuid=puuid, region=region)
```

**File:** services.py (L14-14)
```python
RIOT_API_KEY = os.getenv("RIOT_API_KEY")
```

**File:** services.py (L16-30)
```python
# TTLs (Time To Live)
SUMMONER_TTL = timedelta(hours=1)
MATCH_FETCH_TTL = timedelta(minutes=15)


# -----------------------------
# Helpers
# -----------------------------
def is_stale(profile: RiotUserProfile) -> bool:
    last_updated = profile.last_updated
    if last_updated is None:
        return True
    if last_updated.tzinfo is None:
        last_updated = last_updated.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - last_updated > SUMMONER_TTL
```

**File:** services.py (L115-115)
```python
    rows.sort(key=lambda r: r["puuid"])# This line is important to deny Deadlock Error
```

**File:** services.py (L127-163)
```python
async def save_match(
    db: AsyncSession,
    match_data: MatchCreate,
    teams: list[MatchTeamCreate],
    players: list[MatchParticipantCreate],
) -> Matches:
    match_id = match_data.match_id  

    # ya existe?
    result = await db.execute(select(Matches).where(Matches.match_id == match_id))
    existing = result.scalar_one_or_none()
    if existing:
        return existing

    # Insert match
    match = Matches(
        match_id=match_data.match_id,
        platform_id=match_data.platform_id,
        queue_id=match_data.queue_id,
        game_mode=match_data.game_mode,
        game_version=match_data.game_version,
        game_start_ts=match_data.game_start_ts,
        duration_sec=match_data.duration_sec,
    )
    db.add(match)
   
    await db.flush()

    # Insert teams
    db.add_all([MatchTeam(**t.model_dump()) for t in teams])

    # Insert players
    db.add_all([MatchParticipant(**p.model_dump()) for p in players])

    await db.commit()
    await db.refresh(match)
    return match
```

**File:** services.py (L169-177)
```python
async def get_puuid(gameName: str, tagLine: str, region: str = "americas") -> str:
    url = f"https://{region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{gameName}/{tagLine}"
    headers = {"X-Riot-Token": RIOT_API_KEY}
    async with httpx.AsyncClient() as client:
        puuid_response = await client.get(url, headers=headers)
        if puuid_response.status_code == 200:
            data = puuid_response.json()
            return data["puuid"]
        raise Exception(f"API error: {puuid_response.status_code} - {puuid_response.text}")
```

**File:** services.py (L224-255)
```python
async def get_match_data(matchId:str,routingRegion:str,db:AsyncSession):
    url = f"https://{routingRegion}.api.riotgames.com/lol/match/v5/matches/{matchId}"
    headers = {"X-Riot-Token": RIOT_API_KEY}
    async with httpx.AsyncClient(timeout=20) as client:
        match_data_req = await client.get(url,headers=headers)
        match_data = match_data_req.json()
        if "info" not in match_data or "metadata" not in match_data:
            raise HTTPException(status_code=502, detail={"bad_payload": match_data})
        info = match_data["info"]
        meta = match_data["metadata"]

        filtered_data ={
            "matchId": meta["matchId"],
            "platformId" : info["platformId"],
            "queueId": info["queueId"],
            "gameMode": info["gameMode"],
            "gameVersion": info["gameVersion"],
            "gameStartTimestamp": info["gameStartTimestamp"],
            "gameDuration": info["gameDuration"],
    }
        match_schema = MatchCreate.model_validate(filtered_data)
        team_schemas =  await filter_match_team(match_data)
        players_schemas = await filter_participants_match_data(match_data)
        await upsert_profiles_from_match(db, match_data, routingRegion)
        await db.flush()
        await save_match(db, match_schema, team_schemas, players_schemas)

        return {
                "match": match_schema,
                "teams": team_schemas,
                "players": players_schemas
            }
```

**File:** services.py (L377-388)
```python
async def fetch_get_matches(puuid: str, region: str,num_matches: int = 20 , queue: Optional[str] = None) -> list:
    url = f"https://{region}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids"
    headers = {"X-Riot-Token": RIOT_API_KEY}
    params : dict = {"count": num_matches}
    if queue is not None:
        params["queue"] = queue
    async with httpx.AsyncClient(timeout=20) as client:
        summoner_matches_ids_req = await client.get(url,headers=headers,params=params)
        if summoner_matches_ids_req.status_code != 200:
             raise Exception(f"Summoner API error: {summoner_matches_ids_req.status_code} - {summoner_matches_ids_req.text}")
        data = summoner_matches_ids_req.json()
        return data
```

**File:** services.py (L392-403)
```python
async def get_summoner_entries(puuid:str,region:str = "la1"):
    headers = {"X-Riot-Token": RIOT_API_KEY}
    async with httpx.AsyncClient(timeout=20) as client:
        url = f"https://{region}.api.riotgames.com/lol/league/v4/entries/by-puuid/{puuid}"
        summoner_entries_request = await client.get(url,headers=headers)
        if summoner_entries_request.status_code != 200:
             raise HTTPException(
        status_code=summoner_entries_request.status_code,
        detail=summoner_entries_request.text
    )
        data = summoner_entries_request.json()
        return data
```

**File:** db.py (L3-10)
```python
from dotenv import load_dotenv
import os
import ssl

load_dotenv()
ssl_ctx = ssl.create_default_context()

DATABASE_URL = os.getenv("POSTGRESQL_URL")
```

**File:** db.py (L13-19)
```python
engine = create_async_engine(
    DATABASE_URL,
    connect_args={"ssl": ssl_ctx},
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=5,
)
```

**File:** db.py (L25-30)
```python
async def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        await db.close()
```

**File:** db.py (L32-35)
```python
async def create_table():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        print("Successful")
```

**File:** schemas.py (L5-15)
```python
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
```

**File:** models.py (L18-167)
```python
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
```
#If u got any more questions ask AI here

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/lDavidSantiago/elo-braker)
