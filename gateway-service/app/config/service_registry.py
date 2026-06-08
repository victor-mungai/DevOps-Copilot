import os


def get_service_url(name: str) -> str:
    defaults = {
        "onboarding": os.getenv("ONBOARDING_SERVICE_URL", "http://127.0.0.1:8001"),
        "aws_connector": os.getenv(
            "AWS_CONNECTOR_SERVICE_URL", "http://127.0.0.1:8003"
        ),
        "metrics": os.getenv("METRICS_SERVICE_URL", "http://127.0.0.1:8004"),
        "insight": os.getenv("INSIGHT_SERVICE_URL", "http://127.0.0.1:8005"),
        "ui": os.getenv("UI_SERVICE_URL", "http://127.0.0.1:8002"),
    }

    url = defaults.get(name)
    if not url:
        raise KeyError(f"Unknown service: {name}")
    return url.rstrip("/")
