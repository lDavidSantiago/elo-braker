from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("POSTGRESQL_URL")

print("Creating Database Engine ⚙️")
engine = create_engine(DATABASE_URL)

#Session Maker help perfom actions in database
SessionLocal = sessionmaker(autoflush=False,bind=engine,autocommit=False)
#Base will help us create tables that we are gonna use in code
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_table():
    Base.metadata.create_all(bind=engine)