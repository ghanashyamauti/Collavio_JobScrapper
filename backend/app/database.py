import os
import re
from typing import Generator
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.config import settings

Base = declarative_base()


def normalize_db_url(raw_url: str) -> tuple[str, str]:
    """
    Normalizes PostgreSQL connection strings for psycopg3 and handles local SQLite fallback.
    Returns (normalized_url, engine_type).
    """
    is_placeholder = (
        not raw_url
        or not raw_url.strip()
        or "<YOUR_NEON_OR_SUPABASE_URL>" in raw_url
        or "USER:PASSWORD" in raw_url
    )

    if is_placeholder:
        if settings.FALLBACK_SQLITE_FOR_LOCAL_DEV:
            # SQLite fallback for local verification
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(base_dir, "collavio_local.db").replace("\\", "/")
            return f"sqlite:///{db_path}", "sqlite_fallback"
        raise RuntimeError(
            "DATABASE_URL is missing or uses a placeholder value while "
            "FALLBACK_SQLITE_FOR_LOCAL_DEV=false. Set a valid PostgreSQL DATABASE_URL "
            "in backend/.env or GitHub Repository Secrets."
        )

    url = raw_url.strip()

    # Rewrite postgres:// or postgresql:// to postgresql+psycopg://
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://"):]
    elif url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]

    # Ensure sslmode=require is kept for remote PostgreSQL hosts
    parsed = urlparse(url)
    if "postgres" in parsed.scheme:
        query_params = parse_qs(parsed.query)
        if "sslmode" not in query_params:
            query_params["sslmode"] = ["require"]
            new_query = urlencode(query_params, doseq=True)
            url = urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                new_query,
                parsed.fragment
            ))
        return url, "postgres"

    return url, "other"


DB_URL, DB_TYPE = normalize_db_url(settings.DATABASE_URL)

if DB_TYPE == "sqlite_fallback":
    engine = create_engine(
        DB_URL,
        connect_args={"check_same_thread": False},
    )
else:
    engine = create_engine(
        DB_URL,
        pool_pre_ping=True,
        pool_recycle=300,
        pool_size=5,
        max_overflow=10,
        connect_args={"connect_timeout": 15},
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)


def init_db() -> None:
    """Creates all tables if they do not exist."""
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
