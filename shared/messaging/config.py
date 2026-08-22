import os
from dotenv import load_dotenv

# Load environment configuration from .env file if available
load_dotenv()

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "guest")
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
