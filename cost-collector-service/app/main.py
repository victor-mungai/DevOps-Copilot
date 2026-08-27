import os
import sys
import logging
import threading

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

from app.db.connection import init_db
from app.routes.cost import router as cost_router
from app.workers.cost_worker import start_cost_worker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cost-collector")

app = FastAPI(title="DevOps Copilot Cost Collector Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(cost_router)


@app.on_event("startup")
def on_startup() -> None:
    logger.info("Initializing Cost Collector Database...")
    try:
        init_db()
    except Exception as exc:
        logger.warning("DB init non-fatal: %s", exc)

    # Start background worker thread to listen on cost.queue
    worker_thread = threading.Thread(target=start_cost_worker, daemon=True)
    worker_thread.start()
    logger.info("Cost Collector worker thread started.")


@app.get("/health")
def health():
    return {"status": "ok", "service": "cost-collector-service"}
