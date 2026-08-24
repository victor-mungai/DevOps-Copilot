import sys
import os
import logging

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from dotenv import load_dotenv
from fastapi import FastAPI

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

from .routes import router
from .services.scheduler_service import start_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("metrics-collector")

app = FastAPI(title="DevOps Copilot Metrics Collector")
app.include_router(router)


@app.on_event("startup")
def on_startup() -> None:
    if os.getenv("ENABLE_SCHEDULER", "true").lower() == "true":
        start_scheduler()
