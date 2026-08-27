import logging
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import NullPool

from ..config import DATABASE_URL

logger = logging.getLogger("insight-engine")

def _init_engine(url: str):
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    try:
        pool_kwargs = {} if url.startswith("sqlite") else {"poolclass": NullPool, "pool_pre_ping": True}
        eng = create_engine(url, connect_args=connect_args, future=True, **pool_kwargs)
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


def ensure_insight_columns() -> None:
    """Upgrade an existing local/remote table without removing insight data."""
    required = {
        "observed_cost": "DOUBLE PRECISION",
        "inactive_hours": "DOUBLE PRECISION",
    }
    try:
        if engine.dialect.name == "sqlite":
            existing = {column["name"] for column in inspect(engine).get_columns("insights")}
            missing = [name for name in required if name not in existing]
            if missing:
                with engine.begin() as conn:
                    for name in missing:
                        conn.execute(text(f"ALTER TABLE insights ADD COLUMN {name} REAL"))
        else:
            with engine.begin() as conn:
                for name, column_type in required.items():
                    conn.execute(text(f"ALTER TABLE insights ADD COLUMN IF NOT EXISTS {name} {column_type}"))
    except Exception as exc:
        logger.warning("Insight column upgrade skipped: %s", type(exc).__name__)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
