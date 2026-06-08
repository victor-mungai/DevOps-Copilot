# Metrics Collector Service

The Metrics Collector gathers infrastructure metrics from customer AWS environments and stores them for analysis.

Responsibilities
- Discover AWS infrastructure resources
- Collect operational metrics
- Normalize metric data
- Store metrics in a time-series system (Prometheus Pushgateway)
- Provide data for the Insight Engine

Environment
- AWS_CONNECTOR_BASE_URL (default: http://127.0.0.1:8000/v1/aws)
- AWS_CONNECTOR_SERVICE_URL (optional direct connector base)
- PROMETHEUS_PUSHGATEWAY_URL (optional)
- DEFAULT_METRICS_REGION (default: us-east-1)
- METRIC_PERIOD_SECONDS (default: 60)
- METRIC_WINDOW_MINUTES (default: 5)
- TENANT_IDS (comma-separated)
- COLLECTION_INTERVAL_SECONDS (default: 60)
- ENABLE_SCHEDULER (true/false)

Run
1. pip install -r requirements.txt
2. uvicorn app.main:app --reload --host 127.0.0.1 --port 8004
