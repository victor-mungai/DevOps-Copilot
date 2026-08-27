import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from botocore.exceptions import BotoCoreError, ClientError
from sqlalchemy.orm import Session

logger = logging.getLogger("aws-connector")

from .cache.credential_cache import get_cached_credentials, store_credentials
from .db.account_repository import get_connected_account, get_connected_accounts
from .db.connection import get_db
from .models.schemas import (
    AwsClientRequest,
    AwsResourceResponse,
    CloudWatchMetricRequest,
    CostAndUsageRequest,
    ResourceCostRequest,
)
from .services.aws_session_service import assume_role
from .services.resource_service import (
    get_cloudwatch_metric_statistics,
    get_cost_and_usage,
    get_cost_and_usage_with_resources,
    list_cloudwatch_metrics,
    list_ec2_instances,
    list_lambda_functions,
    list_rds_instances,
)

router = APIRouter()


@router.get("/health")
@router.get("/")
def health():
    return {"status": "healthy", "service": "aws-connector"}


def _aws_error(exc: Exception) -> HTTPException:
    logger.error("AWS Error encountered in connector route: %s", exc)
    if isinstance(exc, ClientError):
        error = exc.response.get("Error", {})
        code = error.get("Code", "AWSClientError")
        message = error.get("Message", str(exc))
        return HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": code, "message": message},
        )
    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail={"code": "AWSConnectorError", "message": str(exc)},
    )


def _get_creds(db: Session, tenant_id: str, region: str, account: dict) -> dict:
    account_id = account.get("account_id")
    cached = get_cached_credentials(tenant_id, account_id)
    if cached:
        return cached

    try:
        creds = assume_role(account["role_arn"], account["external_id"], region)
        store_credentials(tenant_id, creds, account_id)
    except (BotoCoreError, ClientError, RuntimeError, ValueError) as exc:
        raise _aws_error(exc) from exc

    return get_cached_credentials(tenant_id, account_id)


def _accounts_for_request(db: Session, tenant_id: str, account_id: str | None) -> list[dict]:
    if account_id:
        account = get_connected_account(db, tenant_id, account_id)
        if not account:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connected AWS account not found")
        return [account]
    accounts = get_connected_accounts(db, tenant_id)
    if not accounts:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No connected AWS accounts found")
    return accounts


SUPPORTED_REGIONS = [
    "us-east-1",
    "us-east-2",
    "us-west-1",
    "us-west-2",
    "eu-west-1",
    "eu-central-1",
    "ap-southeast-1",
]


@router.get("/aws/{tenant_id}/ec2/instances", response_model=AwsResourceResponse)
def get_ec2_instances(
    tenant_id: str, request: AwsClientRequest = Depends(), db: Session = Depends(get_db)
):
    all_reservations = []
    for account in _accounts_for_request(db, tenant_id, request.account_id):
        target_region = request.region or account.get("region")
        if not target_region:
            raise HTTPException(status_code=400, detail="region is required")
        regions_to_scan = SUPPORTED_REGIONS if target_region.lower() in ["all", "all-regions"] else [target_region]
        for reg in regions_to_scan:
            try:
                data = list_ec2_instances(_get_creds(db, tenant_id, reg, account), reg)
                if isinstance(data, dict) and "Reservations" in data:
                    all_reservations.extend(data["Reservations"])
            except (BotoCoreError, ClientError, RuntimeError, ValueError) as exc:
                raise _aws_error(exc) from exc

    return AwsResourceResponse(data={"Reservations": all_reservations})


@router.get("/aws/{tenant_id}/rds/databases", response_model=AwsResourceResponse)
def get_rds_instances(
    tenant_id: str, request: AwsClientRequest = Depends(), db: Session = Depends(get_db)
):
    all_dbs = []
    for account in _accounts_for_request(db, tenant_id, request.account_id):
        target_region = request.region or account.get("region")
        if not target_region:
            raise HTTPException(status_code=400, detail="region is required")
        regions_to_scan = SUPPORTED_REGIONS if target_region.lower() in ["all", "all-regions"] else [target_region]
        for reg in regions_to_scan:
            try:
                data = list_rds_instances(_get_creds(db, tenant_id, reg, account), reg)
                if isinstance(data, dict) and "DBInstances" in data:
                    all_dbs.extend(data["DBInstances"])
            except (BotoCoreError, ClientError, RuntimeError, ValueError) as exc:
                raise _aws_error(exc) from exc

    return AwsResourceResponse(data={"DBInstances": all_dbs})


@router.get("/aws/{tenant_id}/lambda/functions", response_model=AwsResourceResponse)
def get_lambda_functions(
    tenant_id: str, request: AwsClientRequest = Depends(), db: Session = Depends(get_db)
):
    all_funcs = []
    for account in _accounts_for_request(db, tenant_id, request.account_id):
        target_region = request.region or account.get("region")
        if not target_region:
            raise HTTPException(status_code=400, detail="region is required")
        regions_to_scan = SUPPORTED_REGIONS if target_region.lower() in ["all", "all-regions"] else [target_region]
        for reg in regions_to_scan:
            try:
                data = list_lambda_functions(_get_creds(db, tenant_id, reg, account), reg)
                if isinstance(data, dict) and "Functions" in data:
                    all_funcs.extend(data["Functions"])
            except (BotoCoreError, ClientError, RuntimeError, ValueError) as exc:
                raise _aws_error(exc) from exc

    return AwsResourceResponse(data={"Functions": all_funcs})


@router.get("/aws/{tenant_id}/cloudwatch/metrics", response_model=AwsResourceResponse)
def get_cloudwatch_metrics(
    tenant_id: str, request: AwsClientRequest = Depends(), db: Session = Depends(get_db)
):
    accounts = _accounts_for_request(db, tenant_id, request.account_id)
    if len(accounts) != 1:
        raise HTTPException(status_code=400, detail="account_id is required when multiple AWS accounts are connected")
    account = accounts[0]
    region = request.region or account.get("region")
    if not region:
        raise HTTPException(status_code=400, detail="region is required")
    creds = _get_creds(db, tenant_id, region, account)
    try:
        data = list_cloudwatch_metrics(creds, region)
    except (BotoCoreError, ClientError, RuntimeError) as exc:
        raise _aws_error(exc) from exc
    return AwsResourceResponse(data=data)


@router.post(
    "/aws/{tenant_id}/cloudwatch/metric-statistics", response_model=AwsResourceResponse
)
def get_cloudwatch_metric_stats(
    tenant_id: str, payload: CloudWatchMetricRequest, db: Session = Depends(get_db)
):
    accounts = _accounts_for_request(db, tenant_id, payload.account_id)
    if len(accounts) != 1:
        raise HTTPException(status_code=400, detail="account_id is required when multiple AWS accounts are connected")
    account = accounts[0]
    region = payload.region or account.get("region")
    if not region:
        raise HTTPException(status_code=400, detail="region is required")
    creds = _get_creds(db, tenant_id, region, account)

    end_time = payload.end_time or datetime.utcnow()
    start_time = payload.start_time or (end_time - timedelta(minutes=5))

    try:
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
    except (BotoCoreError, ClientError, RuntimeError) as exc:
        raise _aws_error(exc) from exc
    return AwsResourceResponse(data=data)


@router.post("/aws/{tenant_id}/cost-and-usage", response_model=AwsResourceResponse)
def get_tenant_cost_and_usage(
    tenant_id: str, payload: CostAndUsageRequest, db: Session = Depends(get_db)
):
    accounts = _accounts_for_request(db, tenant_id, payload.account_id)
    if len(accounts) != 1:
        raise HTTPException(status_code=400, detail="account_id is required when multiple AWS accounts are connected")
    account = accounts[0]
    creds = _get_creds(db, tenant_id, account.get("region") or "us-east-1", account)
    try:
        logger.info(
            "COST_EXPLORER_ASSUMED_ACCOUNT tenant=%s account=%s role=%s region=%s metrics=%s group_by=%s",
            tenant_id, account.get("account_id"), creds.get("assumed_arn"), account.get("region"), payload.metrics, payload.group_by,
        )
        data = get_cost_and_usage(
            creds,
            payload.start_date,
            payload.end_date,
            payload.granularity,
            payload.metrics,
            payload.group_by,
        )
    except (BotoCoreError, ClientError, RuntimeError) as exc:
        raise _aws_error(exc) from exc

    logger.info(
        "COST_EXPLORER_RESPONSE tenant=%s account=%s results_by_time=%s",
        tenant_id, account.get("account_id"), len(data.get("ResultsByTime", [])),
    )

    return AwsResourceResponse(
        data={
            **data,
            "AwsAccountId": account.get("account_id") or creds.get("assumed_account_id"),
            "AssumedArn": creds.get("assumed_arn"),
        }
    )


@router.post("/aws/{tenant_id}/cost-and-usage/resources", response_model=AwsResourceResponse)
def get_tenant_resource_costs(
    tenant_id: str, payload: ResourceCostRequest, db: Session = Depends(get_db)
):
    """Expose only native Cost Explorer resource costs for one connected account."""
    accounts = _accounts_for_request(db, tenant_id, payload.account_id)
    if len(accounts) != 1:
        raise HTTPException(status_code=400, detail="account_id is required when multiple AWS accounts are connected")
    account = accounts[0]
    creds = _get_creds(db, tenant_id, account.get("region") or "us-east-1", account)
    try:
        data = get_cost_and_usage_with_resources(
            creds, payload.start_date, payload.end_date, payload.metrics, payload.granularity
        )
    except (BotoCoreError, ClientError, RuntimeError) as exc:
        raise _aws_error(exc) from exc
    return AwsResourceResponse(
        data={
            **data,
            "AwsAccountId": account.get("account_id") or creds.get("assumed_account_id"),
            "AssumedArn": creds.get("assumed_arn"),
        }
    )
