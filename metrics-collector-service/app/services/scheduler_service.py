import logging
import os
import threading
import time

import requests
import schedule

from .metrics_service import collect_for_tenants

logger = logging.getLogger("metrics-collector")


def _tenant_list() -> list[str]:
    raw = os.getenv("TENANT_IDS", "")
    return [item.strip() for item in raw.split(",") if item.strip()]


def _discover_tenants() -> list[str]:
    """Prefer an explicit TENANT_IDS override; otherwise discover connected
    tenants from the onboarding service so scheduling works automatically once
    an account is onboarded."""
    explicit = _tenant_list()
    if explicit:
        return explicit

    base = os.getenv("ONBOARDING_SERVICE_URL", "http://127.0.0.1:8001").rstrip("/")
    try:
        resp = requests.get(f"{base}/tenants/connected", timeout=10)
        resp.raise_for_status()
        tenants = resp.json().get("tenants", [])
        return [t["tenant_id"] for t in tenants if t.get("tenant_id")]
    except requests.RequestException as exc:
        logger.warning("Tenant discovery failed (%s); no tenants to collect", exc)
        return []


def run_collection_job() -> None:
    tenants = _discover_tenants()
    if not tenants:
        logger.info("No connected tenants found for scheduled collection")
        return
    logger.info("Scheduling collection for %s tenant(s)", len(tenants))
    collect_for_tenants(tenants)


def start_scheduler() -> None:
    interval = int(os.getenv("COLLECTION_INTERVAL_SECONDS", "60"))
    schedule.clear()
    schedule.every(interval).seconds.do(run_collection_job)

    def loop() -> None:
        while True:
            schedule.run_pending()
            time.sleep(1)

    thread = threading.Thread(target=loop, daemon=True)
    thread.start()
    logger.info("Scheduler started (interval=%s seconds)", interval)
