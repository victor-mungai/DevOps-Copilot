import os

PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://18.116.65.134:9090").rstrip("/")

AWS_CONNECTOR_BASE_URL = os.getenv("AWS_CONNECTOR_BASE_URL")
AWS_CONNECTOR_SERVICE_URL = os.getenv("AWS_CONNECTOR_SERVICE_URL")
DEFAULT_CONNECTOR_BASE = "http://127.0.0.1:8000/v1/aws"

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./insights.db")

IDLE_CPU_THRESHOLD = float(os.getenv("IDLE_CPU_THRESHOLD", "5.0"))
IDLE_WINDOW_DAYS = int(os.getenv("IDLE_WINDOW_DAYS", "7"))
DEFAULT_REGION = os.getenv("DEFAULT_METRICS_REGION", "us-east-1")

METRIC_NAME_CPU = os.getenv("METRIC_NAME_CPU", "cpu_utilization")
LABEL_TENANT = os.getenv("PROM_LABEL_TENANT", "tenant")
LABEL_RESOURCE = os.getenv("PROM_LABEL_RESOURCE", "resource")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "700"))
MAX_QUESTION_LENGTH = int(os.getenv("MAX_QUESTION_LENGTH", "2000"))

HTTP_TIMEOUT = int(os.getenv("HTTP_TIMEOUT", "30"))
