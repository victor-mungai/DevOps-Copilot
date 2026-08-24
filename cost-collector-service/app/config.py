import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres.dgreivfhwwjdrbgkthqc:112262781_Mungai@aws-0-eu-west-1.pooler.supabase.com:5432/postgres?sslmode=require",
)
AWS_CONNECTOR_SERVICE_URL = os.getenv(
    "AWS_CONNECTOR_SERVICE_URL", "http://127.0.0.1:8003"
)
HTTP_TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "10.0"))

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "18.116.65.134")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "devops")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "devops")
RABBITMQ_VHOST = os.getenv("RABBITMQ_VHOST", "/")
