import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from ..config import DATABASE_URL

logger = logging.getLogger("insight-engine")

def _init_engine(url: str):
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    try:
        eng = create_engine(url, connect_args=connect_args, future=True)
        with eng.connect() as conn:
            pass
        return eng
    except Exception as exc:
        logger.warning("Failed to connect to primary DB URL %s: %s. Falling back to local SQLite.", url, exc)
        sqlite_url = "sqlite:///./insight_engine.db"
        return create_engine(sqlite_url, connect_args={"check_same_thread": False}, future=True)

engine = _init_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
