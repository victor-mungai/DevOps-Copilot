from fastapi import Request
from fastapi.responses import Response

from .services.routing_service import forward_request


def _path_with_tenant(path: str, tenant_id: str) -> str:
    return path.replace("{tenant_id}", tenant_id)


def _tenant_from_request(request: Request) -> str:
    return request.path_params.get("tenant_id", "")


def _ensure_tenant(request: Request) -> str:
    tenant_id = _tenant_from_request(request)
    if tenant_id:
        return tenant_id
    tenant_id = request.headers.get("X-Tenant-ID", "")
    return tenant_id


def _proxy_or_404(tenant_id: str, request: Request, service: str, path: str) -> Response:
    if not tenant_id:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail="tenant_id is required")
    return forward_request(service, _path_with_tenant(path, tenant_id), request)


from fastapi import APIRouter

router = APIRouter()


@router.get("/v1/health")
async def health_v1():
    return {"status": "ok"}


@router.post("/v1/tenants")
async def create_tenant(request: Request):
    return await forward_request("onboarding", "/tenants", request, inject_tenant=False)


@router.get("/v1/tenants/{tenant_id}/onboarding-link")
async def onboarding_link(request: Request, tenant_id: str):
    return await forward_request(
        "onboarding", f"/tenants/{tenant_id}/onboarding-link", request, inject_tenant=False
    )


@router.post("/v1/tenants/{tenant_id}/verify")
async def verify_role(request: Request, tenant_id: str):
    return await forward_request(
        "onboarding", f"/tenants/{tenant_id}/verify", request, inject_tenant=False
    )


@router.get("/v1/aws/{tenant_id}/ec2/instances")
async def ec2_instances(request: Request, tenant_id: str):
    return await forward_request(
        "aws_connector", f"/aws/{tenant_id}/ec2/instances", request
    )


@router.get("/v1/aws/{tenant_id}/rds/databases")
async def rds_instances(request: Request, tenant_id: str):
    return await forward_request(
        "aws_connector", f"/aws/{tenant_id}/rds/databases", request
    )


@router.get("/v1/aws/{tenant_id}/lambda/functions")
async def lambda_functions(request: Request, tenant_id: str):
    return await forward_request(
        "aws_connector", f"/aws/{tenant_id}/lambda/functions", request
    )


@router.get("/v1/aws/{tenant_id}/cloudwatch/metrics")
async def cloudwatch_metrics(request: Request, tenant_id: str):
    return await forward_request(
        "aws_connector", f"/aws/{tenant_id}/cloudwatch/metrics", request
    )


@router.post("/v1/aws/{tenant_id}/cloudwatch/metric-statistics")
async def cloudwatch_metric_statistics(request: Request, tenant_id: str):
    return await forward_request(
        "aws_connector", f"/aws/{tenant_id}/cloudwatch/metric-statistics", request
    )


@router.get("/v1/metrics/health")
async def metrics_health(request: Request):
    return await forward_request("metrics", "/health", request)


@router.post("/v1/metrics/collect/run")
async def metrics_collect_run(request: Request):
    return await forward_request("metrics", "/collect/run", request)


@router.post("/v1/metrics/collect/tenant/{tenant_id}")
async def metrics_collect_tenant(request: Request, tenant_id: str):
    return await forward_request("metrics", f"/collect/tenant/{tenant_id}", request)
