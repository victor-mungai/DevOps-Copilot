import os

from .aws_connector_client import list_ec2_instances as connector_list_ec2
from .dev_source import DevSource
from .prometheus_source import PrometheusMetricSource


class PrometheusProvider:
    def __init__(self):
        self._metrics = PrometheusMetricSource()

    def list_ec2_instances(self, tenant_id: str, region: str | None = None) -> list[dict]:
        return connector_list_ec2(tenant_id, region=region)

    def list_rds_databases(self, tenant_id: str, region: str | None = None) -> list[dict]:
        from .aws_connector_client import list_rds_databases
        return list_rds_databases(tenant_id, region=region)

    def list_lambda_functions(self, tenant_id: str, region: str | None = None) -> list[dict]:
        from .aws_connector_client import list_lambda_functions
        return list_lambda_functions(tenant_id, region=region)

    def avg_cpu_over_window(self, tenant_id: str, resource_id: str, days: int):
        return self._metrics.avg_cpu_over_window(tenant_id, resource_id, days)


def get_provider():
    if os.getenv("METRIC_SOURCE", "prometheus").lower() == "dev":
        return DevSource()
    return PrometheusProvider()
