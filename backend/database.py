"""SQLAlchemy session factory for the backend API."""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from database.models import Base

DB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "database", "travel_assistant.db")
)
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Create all tables if they don't exist (idempotent)."""
    Base.metadata.create_all(bind=engine)


def get_db() -> Session:
    """FastAPI dependency that yields a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
