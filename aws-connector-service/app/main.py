
import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

from .db.connection import Base, engine
from .routes import router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aws-connector")

app = FastAPI(title="DevOps Copilot AWS Connector Service")



@app.on_event("startup")
def create_tables() -> None:
    Base.metadata.create_all(bind=engine)
    try:
        db_url = engine.url.render_as_string(hide_password=True)
    except Exception:
        db_url = "unknown"
    logger.info("AWS Connector DB URL: %s", db_url)
    


app.include_router(router)
