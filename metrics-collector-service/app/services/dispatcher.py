import abc
import logging
import os
from typing import Callable, Any

logger = logging.getLogger("metrics-collector.dispatcher")


class CollectionJob:
    def __init__(self, tenant_id: str, region: str | None = None):
        self.tenant_id = tenant_id
        self.region = region


class CollectionDispatcher(abc.ABC):
    @abc.abstractmethod
    def dispatch(self, job: CollectionJob, collection_func: Callable[[CollectionJob], Any]) -> None:
        raise NotImplementedError


class LocalDispatcher(CollectionDispatcher):
    """Executes collection jobs locally in-process synchronously or via task pool."""

    def dispatch(self, job: CollectionJob, collection_func: Callable[[CollectionJob], Any]) -> None:
        try:
            collection_func(job)
        except Exception as exc:
            logger.error(f"Error executing collection job for tenant {job.tenant_id}: {exc}")


class SQSDispatcher(CollectionDispatcher):
    """Stub for distributed SQS queue dispatcher."""

    def dispatch(self, job: CollectionJob, collection_func: Callable[[CollectionJob], Any]) -> None:
        logger.info(f"[SQSDispatcher] Queued collection job to SQS for tenant {job.tenant_id} (region: {job.region})")


class CeleryDispatcher(CollectionDispatcher):
    """Stub for distributed Celery task dispatcher."""

    def dispatch(self, job: CollectionJob, collection_func: Callable[[CollectionJob], Any]) -> None:
        logger.info(f"[CeleryDispatcher] Dispatched Celery task for tenant {job.tenant_id} (region: {job.region})")


def get_dispatcher() -> CollectionDispatcher:
    mode = os.getenv("COLLECTION_DISPATCHER_MODE", "local").lower()
    if mode == "sqs":
        return SQSDispatcher()
    elif mode == "celery":
        return CeleryDispatcher()
    return LocalDispatcher()
