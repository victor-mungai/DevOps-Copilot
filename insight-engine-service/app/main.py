import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

from .db.connection import Base, engine
from .observability import RequestContextMiddleware
from .routes import router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("insight-engine")

app = FastAPI(title="DevOps Copilot Insight Engine Service")
app.add_middleware(RequestContextMiddleware)


@app.on_event("startup")
def create_tables() -> None:
    Base.metadata.create_all(bind=engine)
    logger.info("Insight Engine started")


app.include_router(router)
