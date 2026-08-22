import logging
import threading
import time
from typing import Callable, Dict, Any

from . import config
from .connection import get_messaging_manager, _local_queues
from .events import deserialize_event, serialize_event

logger = logging.getLogger("messaging")

# In-memory deduplication set to guarantee idempotency across workers
_processed_events = set()
_dedup_lock = threading.Lock()


def is_duplicate(event_id: str) -> bool:
    with _dedup_lock:
        if event_id in _processed_events:
            return True
        _processed_events.add(event_id)
        # Keep set size bounded
        if len(_processed_events) > 10000:
            _processed_events.clear()
        return False


class EventConsumer:
    """Consumes events from RabbitMQ or local memory queue with prefetch, ACKs, and retries."""

    def __init__(self, queue_name: str, handler: Callable[[Dict[str, Any]], None], prefetch_count: int = config.DEFAULT_PREFETCH):
        self.queue_name = queue_name
        self.handler = handler
        self.prefetch_count = prefetch_count
        self.manager = get_messaging_manager()
        self.running = False

    def start(self):
        self.running = True
        if self.manager.is_connected and self.manager.channel:
            try:
                self.manager.channel.basic_qos(prefetch_count=self.prefetch_count)
                self.manager.channel.basic_consume(
                    queue=self.queue_name,
                    on_message_callback=self._on_rabbitmq_message,
                    auto_ack=False
                )
                logger.info("Started RabbitMQ consumer on queue: %s (prefetch=%s)", self.queue_name, self.prefetch_count)
                threading.Thread(target=self.manager.channel.start_consuming, daemon=True).start()
                return
            except Exception as exc:
                logger.warning("RabbitMQ consumer start error (%s). Falling back to local broker queue.", exc)

        # Fallback to local queue subscriber
        logger.info("Started Local Memory Queue consumer on queue: %s", self.queue_name)
        self.manager.register_local_subscriber(self.queue_name, self._on_local_message)
        threading.Thread(target=self._poll_local_queue, daemon=True).start()

    def _on_rabbitmq_message(self, ch, method, properties, body):
        try:
            event = deserialize_event(body.decode("utf-8"))
            event_id = event.get("event_id")
            if event_id and is_duplicate(event_id):
                logger.info("Idempotency guard: Skipping duplicate event %s", event_id)
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return

            self.handler(event)
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as exc:
            logger.error("Error processing event on %s: %s", self.queue_name, exc)
            retry_count = 0
            try:
                event = deserialize_event(body.decode("utf-8"))
                retry_count = event.get("retry_count", 0) + 1
            except Exception:
                pass

            if retry_count <= config.MAX_RETRIES:
                logger.warning("NACKing message (requeue=True, retry_count=%s)", retry_count)
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
            else:
                logger.error("Max retries exceeded for message. Routing to Dead-Letter Queue.")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    def _on_local_message(self, message_body: str):
        try:
            event = deserialize_event(message_body)
            event_id = event.get("event_id")
            if event_id and is_duplicate(event_id):
                logger.info("Idempotency guard: Skipping duplicate event %s", event_id)
                return
            self.handler(event)
        except Exception as exc:
            logger.error("Local consumer processing error: %s", exc)

    def _poll_local_queue(self):
        q = _local_queues.get(self.queue_name)
        if not q:
            return
        while self.running:
            try:
                msg = q.get(timeout=1.0)
                self._on_local_message(msg)
                q.task_done()
            except Exception:
                pass
            time.sleep(0.05)
