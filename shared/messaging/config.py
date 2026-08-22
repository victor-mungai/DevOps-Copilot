import os

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "18.116.65.134")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "devops")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "devops")
RABBITMQ_VHOST = os.getenv("RABBITMQ_VHOST", "/")

EXCHANGE_NAME = "devops.events"
DLX_EXCHANGE_NAME = "devops.dlx"

QUEUE_METRICS = "metrics.queue"
QUEUE_INSIGHTS = "insights.queue"
QUEUE_RAG = "rag.queue"
QUEUE_NOTIFICATIONS = "notifications.queue"

DLQ_METRICS = "metrics.dlq"
DLQ_INSIGHTS = "insights.dlq"
DLQ_RAG = "rag.dlq"
DLQ_NOTIFICATIONS = "notifications.dlq"

DEFAULT_PREFETCH = 10
MAX_RETRIES = 3
