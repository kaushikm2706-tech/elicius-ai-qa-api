"""
Database layer. Uses SQLAlchemy so the same code works against
PostgreSQL (production, via DATABASE_URL) or SQLite (local dev/tests,
the default) without changing a single query.

Two tables:
  - users: for login (assignment section 2 — JWT auth)
  - chat_logs: one row per /chat call, so latency and token usage
    (assignment section 1) are actually persisted, not just printed.
"""
from datetime import datetime

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings

_engine_kwargs = {}
if settings.database_url.startswith("sqlite"):
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
    if ":memory:" in settings.database_url:
        # An in-memory SQLite DB normally gets wiped every time a new
        # connection is opened. StaticPool forces every request in the
        # test run to reuse the SAME connection, so tables created at
        # startup are still there for the next request.
        _engine_kwargs["poolclass"] = StaticPool

engine = create_engine(settings.database_url, **_engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="user", nullable=False)  # admin | user | readonly


class ChatLog(Base):
    __tablename__ = "chat_logs"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, index=True, nullable=False)
    question = Column(String, nullable=False)
    answer = Column(String, nullable=True)
    provider_used = Column(String, nullable=True)   # "gemini" or "groq" or "cache"
    latency_ms = Column(Float, nullable=False)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    status = Column(String, nullable=False)          # "success" or "error"
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db() -> None:
    """Create tables if they don't exist yet. Called once at startup."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI dependency: gives each request its own DB session and
    always closes it afterwards, even if the request raised an error."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
