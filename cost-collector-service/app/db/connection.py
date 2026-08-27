import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .. import config

logger = logging.getLogger("cost-collector")

db_url = config.DATABASE_URL
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)

from sqlalchemy.pool import NullPool

def _init_engine(url: str):
    try:
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {"connect_timeout": 10}
        pool_kwargs = {} if url.startswith("sqlite") else {"poolclass": NullPool, "pool_pre_ping": True}
        eng = create_engine(url, connect_args=connect_args, **pool_kwargs)
        with eng.connect() as conn:
            pass
        return eng
    except Exception as exc:
        logger.warning("Failed to connect to primary DB URL %s: %s. Falling back to local SQLite.", url, exc)
        return create_engine("sqlite:///./cost_collector.db", connect_args={"check_same_thread": False}, future=True)

engine = _init_engine(db_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


from sqlalchemy import text


def init_db():
    Base.metadata.create_all(bind=engine)
    try:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE aws_costs ADD COLUMN IF NOT EXISTS net_unblended_cost NUMERIC(18, 8) DEFAULT 0;"))
            conn.execute(text("ALTER TABLE aws_costs ADD COLUMN IF NOT EXISTS net_amortized_cost NUMERIC(18, 8) DEFAULT 0;"))
            conn.execute(text("ALTER TABLE aws_costs ADD COLUMN IF NOT EXISTS record_type VARCHAR DEFAULT 'Usage';"))
    except Exception as exc:
        logger.warning("Column migration warning for aws_costs: %s", exc)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
