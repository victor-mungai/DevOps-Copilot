import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

from .db.connection import Base, engine
from .routes import router

app = FastAPI(title="DevOps Copilot Onboarding Service")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("onboarding-service")
logging.getLogger("botocore").setLevel(logging.WARNING)
logging.getLogger("boto3").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

allowed_origins_env = os.getenv(
    "CORS_ALLOW_ORIGINS", "http://127.0.0.1:8002,http://localhost:8002"
)
allowed_origins = [origin.strip() for origin in allowed_origins_env.split(",") if origin]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def create_tables() -> None:
    Base.metadata.create_all(bind=engine)
    try:
        db_url = engine.url.render_as_string(hide_password=True)
    except Exception:
        db_url = "unknown"
    logger.info("Onboarding DB URL: %s", db_url)


app.include_router(router)

TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
if os.path.isdir(TEMPLATES_DIR):
    app.mount("/templates", StaticFiles(directory=TEMPLATES_DIR), name="templates")
