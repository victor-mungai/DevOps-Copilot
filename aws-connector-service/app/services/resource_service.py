import boto3


def _client(service: str, creds: dict, region: str):
    return boto3.client(
        service,
        region_name=region,
        aws_access_key_id=creds["access_key"],
        aws_secret_access_key=creds["secret_key"],
        aws_session_token=creds["session_token"],
    )


def list_ec2_instances(creds: dict, region: str):
    ec2 = _client("ec2", creds, region)
    return ec2.describe_instances()


def list_rds_instances(creds: dict, region: str):
    rds = _client("rds", creds, region)
    return rds.describe_db_instances()


def list_lambda_functions(creds: dict, region: str):
    lam = _client("lambda", creds, region)
    return lam.list_functions()


def list_cloudwatch_metrics(creds: dict, region: str):
    cw = _client("cloudwatch", creds, region)
    return cw.list_metrics()


def get_cloudwatch_metric_statistics(
    creds: dict,
    region: str,
    namespace: str,
    metric_name: str,
    dimensions: list[dict],
    start_time,
    end_time,
    period: int,
    statistics: list[str],
):
    cw = _client("cloudwatch", creds, region)
    return cw.get_metric_statistics(
        Namespace=namespace,
        MetricName=metric_name,
        Dimensions=dimensions,
        StartTime=start_time,
        EndTime=end_time,
        Period=period,
        Statistics=statistics,
    )


def get_cost_and_usage(
    creds: dict,
    start_date: str,
    end_date: str,
    granularity: str,
    metrics: list[str],
    group_by: list[dict],
):
    ce = _client("ce", creds, "us-east-1")
    return ce.get_cost_and_usage(
        TimePeriod={"Start": start_date, "End": end_date},
        Granularity=granularity,
        Metrics=metrics,
        GroupBy=group_by,
    )


def get_cost_and_usage_with_resources(
    creds: dict,
    start_date: str,
    end_date: str,
    metrics: list[str],
    granularity: str = "DAILY",
):
    """Return AWS's native EC2 resource-level attribution without allocation."""
    ce = _client("ce", creds, "us-east-1")
    if granularity not in {"DAILY", "HOURLY"}:
        raise ValueError("granularity must be DAILY or HOURLY")
    return ce.get_cost_and_usage_with_resources(
        TimePeriod={"Start": start_date, "End": end_date},
        Granularity=granularity,
        Metrics=metrics,
        Filter={
            "Dimensions": {
                "Key": "SERVICE",
                "Values": ["Amazon Elastic Compute Cloud - Compute"],
            }
        },
        GroupBy=[
            {"Type": "DIMENSION", "Key": "REGION"},
            {"Type": "DIMENSION", "Key": "RESOURCE_ID"},
        ],
    )
