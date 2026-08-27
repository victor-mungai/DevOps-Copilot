import logging
import queue
import threading
import time
from typing import Dict, List, Optional
import pika

from . import config

logger = logging.getLogger("messaging")

_local_queues: Dict[str, queue.Queue] = {
    config.QUEUE_METRICS: queue.Queue(),
    config.QUEUE_INSIGHTS: queue.Queue(),
    config.QUEUE_RAG: queue.Queue(),
    config.QUEUE_NOTIFICATIONS: queue.Queue(),
    config.DLQ_METRICS: queue.Queue(),
    config.DLQ_INSIGHTS: queue.Queue(),
    config.DLQ_RAG: queue.Queue(),
    config.DLQ_NOTIFICATIONS: queue.Queue(),
}
_local_subscribers: Dict[str, List] = {
    config.QUEUE_METRICS: [],
    config.QUEUE_INSIGHTS: [],
    config.QUEUE_RAG: [],
    config.QUEUE_NOTIFICATIONS: [],
}
_lock = threading.Lock()


class MessagingManager:
    """Manages connection to RabbitMQ with automatic reconnection and local broker fallback."""

    def __init__(self):
        self.connection: Optional[pika.BlockingConnection] = None
        self.channel: Optional[pika.adapters.blocking_connection.BlockingChannel] = None
        self.is_connected = False
        self._connect()

    def _connect(self):
        try:
            credentials = pika.PlainCredentials(config.RABBITMQ_USER, config.RABBITMQ_PASSWORD)
            parameters = pika.ConnectionParameters(
                host=config.RABBITMQ_HOST,
                port=config.RABBITMQ_PORT,
                virtual_host=config.RABBITMQ_VHOST,
                credentials=credentials,
                connection_attempts=2,
                retry_delay=1,
                socket_timeout=2
            )
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            self._setup_exchanges_and_queues()
            self.is_connected = True
            logger.info("Connected to RabbitMQ server at %s:%s", config.RABBITMQ_HOST, config.RABBITMQ_PORT)
        except Exception as exc:
            self.is_connected = False
            logger.warning("RabbitMQ server unavailable (%s). Operating in high-performance local memory queue mode.", exc)

    def _setup_exchanges_and_queues(self):
        if not self.channel:
            return
        # Declare Exchanges
        self.channel.exchange_declare(exchange=config.EXCHANGE_NAME, exchange_type="topic", durable=True)
        self.channel.exchange_declare(exchange=config.DLX_EXCHANGE_NAME, exchange_type="topic", durable=True)

        queues = [
            (config.QUEUE_METRICS, ["metrics.#"], config.DLQ_METRICS),
            (config.QUEUE_INSIGHTS, ["insight.analysis.#"], config.DLQ_INSIGHTS),
            (config.QUEUE_RAG, ["rag.#", "insight.created"], config.DLQ_RAG),
            (config.QUEUE_NOTIFICATIONS, ["notification.#", "insight.created"], config.DLQ_NOTIFICATIONS),
        ]

        for q_name, routing_keys, dlq_name in queues:
            # Declare DLQ
            self.channel.queue_declare(queue=dlq_name, durable=True)
            self.channel.queue_bind(queue=dlq_name, exchange=config.DLX_EXCHANGE_NAME, routing_key=dlq_name)

            # Declare Normal Queue with DLX
            self.channel.queue_declare(
                queue=q_name,
                durable=True,
                arguments={
                    "x-dead-letter-exchange": config.DLX_EXCHANGE_NAME,
                    "x-dead-letter-routing-key": dlq_name
                }
            )
            for rk in routing_keys:
                self.channel.queue_bind(queue=q_name, exchange=config.EXCHANGE_NAME, routing_key=rk)

    def publish_message(self, routing_key: str, message_body: str) -> bool:
        if self.is_connected and self.channel:
            try:
                self.channel.basic_publish(
                    exchange=config.EXCHANGE_NAME,
                    routing_key=routing_key,
                    body=message_body.encode("utf-8"),
                    properties=pika.BasicProperties(delivery_mode=2)  # Persistent message
                )
                return True
            except Exception as exc:
                logger.warning("RabbitMQ publish error (%s). Falling back to local broker queue.", exc)
                self.is_connected = False

        # Local Queue Fallback
        target_queue = self._resolve_local_queue(routing_key)
        if target_queue:
            _local_queues[target_queue].put(message_body)
            self._notify_local_subscribers(target_queue, message_body)
            return True
        return False

    def _resolve_local_queue(self, routing_key: str) -> Optional[str]:
        if routing_key.startswith("metrics."):
            return config.QUEUE_METRICS
        if routing_key.startswith("insight.analysis."):
            return config.QUEUE_INSIGHTS
        if routing_key.startswith("rag.") or routing_key == "insight.created":
            return config.QUEUE_RAG
        if routing_key.startswith("notification.") or routing_key == "insight.created":
            return config.QUEUE_NOTIFICATIONS
        return config.QUEUE_METRICS

    def register_local_subscriber(self, queue_name: str, callback):
        with _lock:
            if queue_name in _local_subscribers:
                _local_subscribers[queue_name].append(callback)

    def _notify_local_subscribers(self, queue_name: str, message_body: str):
        with _lock:
            subscribers = list(_local_subscribers.get(queue_name, []))
        for cb in subscribers:
            try:
                threading.Thread(target=cb, args=(message_body,), daemon=True).start()
            except Exception as exc:
                logger.error("Local subscriber execution error: %s", exc)


_manager: Optional[MessagingManager] = None


def get_messaging_manager() -> MessagingManager:
    global _manager
    if _manager is None:
        _manager = MessagingManager()
    return _manager
