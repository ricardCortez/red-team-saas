"""
Database configuration - Red Team SaaS.
Reads DATABASE_URL from environment or builds it from DB_* vars in .env.
"""
import os, logging
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from typing import Generator

_env_file = Path(__file__).resolve().parents[1] / ".env"
if _env_file.exists():
    for line in _env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())

if not os.environ.get("DATABASE_URL"):
    driver   = os.environ.get("DB_DRIVER",   "postgresql")
    user     = os.environ.get("DB_USER",     "red_team")
    password = os.environ.get("DB_PASSWORD", "SecurePassword123!")
    host     = os.environ.get("DB_HOST",     "localhost")
    port     = os.environ.get("DB_PORT",     "5432")
    name     = os.environ.get("DB_NAME",     "red_team_prod")
    os.environ["DATABASE_URL"] = f"{driver}://{user}:{password}@{host}:{port}/{name}"

DATABASE_URL = os.environ["DATABASE_URL"]
SQL_ECHO = os.environ.get("SQL_ECHO", "false").lower() == "true"
logger = logging.getLogger(__name__)

_is_sqlite = DATABASE_URL.startswith("sqlite")
if _is_sqlite:
    engine = create_engine(DATABASE_URL,
        connect_args={"check_same_thread": False}, poolclass=StaticPool, echo=SQL_ECHO)
else:
    engine = create_engine(DATABASE_URL,
        echo=SQL_ECHO, pool_pre_ping=True, pool_size=20, max_overflow=10)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialised")

def health_check() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
