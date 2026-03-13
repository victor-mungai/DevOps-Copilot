from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .cache.credential_cache import get_cached_credentials, store_credentials
from .db.account_repository import get_connected_account
from .db.connection import get_db
from .models.schemas import AwsClientRequest, AwsResourceResponse, CloudWatchMetricRequest
from .services.aws_session_service import assume_role
from .services.resource_service import (
    get_cloudwatch_metric_statistics,
    list_cloudwatch_metrics,
    list_ec2_instances,
    list_lambda_functions,
    list_rds_instances,
)

router = APIRouter()


def _get_creds(db: Session, tenant_id: str, region: str) -> dict:
    cached = get_cached_credentials(tenant_id)
    if cached:
        return cached

    account = get_connected_account(db, tenant_id)
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    creds = assume_role(account["role_arn"], account["external_id"], region)
    store_credentials(tenant_id, creds)
    return get_cached_credentials(tenant_id)


@router.get("/aws/{tenant_id}/ec2/instances", response_model=AwsResourceResponse)
def get_ec2_instances(
    tenant_id: str, request: AwsClientRequest = Depends(), db: Session = Depends(get_db)
):
    region = request.region or "us-east-1"
    creds = _get_creds(db, tenant_id, region)
    data = list_ec2_instances(creds, region)
    return AwsResourceResponse(data=data)


@router.get("/aws/{tenant_id}/rds/databases", response_model=AwsResourceResponse)
def get_rds_instances(
    tenant_id: str, request: AwsClientRequest = Depends(), db: Session = Depends(get_db)
):
    region = request.region or "us-east-1"
    creds = _get_creds(db, tenant_id, region)
    data = list_rds_instances(creds, region)
    return AwsResourceResponse(data=data)


@router.get("/aws/{tenant_id}/lambda/functions", response_model=AwsResourceResponse)
def get_lambda_functions(
    tenant_id: str, request: AwsClientRequest = Depends(), db: Session = Depends(get_db)
):
    region = request.region or "us-east-1"
    creds = _get_creds(db, tenant_id, region)
    data = list_lambda_functions(creds, region)
    return AwsResourceResponse(data=data)


@router.get("/aws/{tenant_id}/cloudwatch/metrics", response_model=AwsResourceResponse)
def get_cloudwatch_metrics(
    tenant_id: str, request: AwsClientRequest = Depends(), db: Session = Depends(get_db)
):
    region = request.region or "us-east-1"
    creds = _get_creds(db, tenant_id, region)
    data = list_cloudwatch_metrics(creds, region)
    return AwsResourceResponse(data=data)


@router.post(
    "/aws/{tenant_id}/cloudwatch/metric-statistics", response_model=AwsResourceResponse
)
def get_cloudwatch_metric_stats(
    tenant_id: str, payload: CloudWatchMetricRequest, db: Session = Depends(get_db)
):
    region = payload.region or "us-east-1"
    creds = _get_creds(db, tenant_id, region)

    end_time = payload.end_time or datetime.utcnow()
    start_time = payload.start_time or (end_time - timedelta(minutes=5))

    data = get_cloudwatch_metric_statistics(
        creds,
        region,
        payload.namespace,
        payload.metric_name,
        payload.dimensions,
        start_time,
        end_time,
        payload.period,
        payload.statistics,
    )
    return AwsResourceResponse(data=data)
