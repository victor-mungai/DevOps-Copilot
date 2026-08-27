import logging
import sys
import os

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from dotenv import load_dotenv
from fastapi import FastAPI

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

from .db.connection import Base, engine, ensure_insight_columns
from .observability import RequestContextMiddleware
from .routes import router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("insight-engine")

app = FastAPI(title="DevOps Copilot Insight Engine Service")
app.add_middleware(RequestContextMiddleware)


@app.on_event("startup")
def create_tables() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_insight_columns()
    logger.info("Insight Engine started")


app.include_router(router)
