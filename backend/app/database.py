import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    # Resolve the default beside the backend package so starting Uvicorn from
    # a different working directory cannot silently select another database.
    f"sqlite:///{(Path(__file__).resolve().parents[1] / 'agentguard.db').as_posix()}"
)

# SQLite configuration
connect_args = {}

if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

# Create database engine
engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False
)

# Database session
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base class for database models
Base = declarative_base()


# Dependency for FastAPI endpoints
def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()
