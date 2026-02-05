from sqlalchemy.orm import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
from dotenv import load_dotenv
import os
import ssl

load_dotenv()
ssl_ctx = ssl.create_default_context()

DATABASE_URL = os.getenv("POSTGRESQL_URL")

print("Creating Database Engine ⚙️")
engine = create_async_engine(
    DATABASE_URL,
    connect_args={"ssl": ssl_ctx},
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=5,
)
#Session Maker help perfom actions in database
SessionLocal = async_sessionmaker(autoflush=False,bind=engine,expire_on_commit=False,)
#Base will help us create tables that we are gonna use in code
Base = declarative_base()

async def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        await db.close()

async def create_table():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        print("Successful")