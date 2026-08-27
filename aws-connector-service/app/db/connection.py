import os
import logging
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()
logger = logging.getLogger("aws-connector")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./aws_connector.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)

from sqlalchemy.pool import NullPool

def _init_engine(url: str):
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {"connect_timeout": 10}
    try:
        pool_kwargs = {} if url.startswith("sqlite") else {"poolclass": NullPool, "pool_pre_ping": True}
        eng = create_engine(url, future=True, connect_args=connect_args, **pool_kwargs)
        with eng.connect() as conn:
            pass
        return eng
    except Exception as exc:
        logger.warning("Primary DB %s unreachable (%s). Using local SQLite.", url, exc)
        return create_engine("sqlite:///./aws_connector.db", connect_args={"check_same_thread": False}, future=True)

engine = _init_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
