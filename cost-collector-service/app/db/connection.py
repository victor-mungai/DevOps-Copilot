import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .. import config

logger = logging.getLogger("cost-collector")

db_url = config.DATABASE_URL
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)

def _init_engine(url: str):
    try:
        eng = create_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=10)
        with eng.connect() as conn:
            pass
        return eng
    except Exception as exc:
        logger.warning("Failed to connect to primary DB URL %s: %s. Falling back to local SQLite.", url, exc)
        return create_engine("sqlite:///./cost_collector.db", connect_args={"check_same_thread": False}, future=True)

engine = _init_engine(db_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
