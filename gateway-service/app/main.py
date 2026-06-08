import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .config.service_registry import get_service_url
from .middleware.auth_middleware import auth_middleware
from .middleware.rate_limit_middleware import rate_limit_middleware
from .routes import router
from .services.routing_service import proxy_request_to

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gateway-service")

app = FastAPI(title="DevOps Copilot Gateway Service")

allowed_origins_env = os.getenv("CORS_ALLOW_ORIGINS", "*")
allowed_origins = [origin.strip() for origin in allowed_origins_env.split(",") if origin]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.middleware("http")(auth_middleware)
app.middleware("http")(rate_limit_middleware)

app.include_router(router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.api_route("/{path:path}", methods=["GET", "HEAD"])
async def ui_proxy(path: str, request: Request):
    ui_base = get_service_url("ui")
    url = f"{ui_base}/{path}" if path else f"{ui_base}/"
    return await proxy_request_to(url, request, inject_tenant=False)
