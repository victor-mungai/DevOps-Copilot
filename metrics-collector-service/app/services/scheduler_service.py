import logging
import os
import threading
import time

import schedule

from .metrics_service import collect_for_tenants

logger = logging.getLogger("metrics-collector")


def _tenant_list() -> list[str]:
    raw = os.getenv("TENANT_IDS", "")
    return [item.strip() for item in raw.split(",") if item.strip()]


def run_collection_job() -> None:
    tenants = _tenant_list()
    if not tenants:
        logger.info("No tenants configured for scheduled collection")
        return
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
