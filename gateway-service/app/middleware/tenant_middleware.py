from fastapi import Request


def get_tenant_headers(request: Request) -> dict:
    headers = {}
    tenant_id = getattr(request.state, "tenant_id", None)
    user_id = getattr(request.state, "user_id", None)
    roles = getattr(request.state, "roles", None)

    if tenant_id:
        headers["X-Tenant-ID"] = str(tenant_id)
    if user_id:
        headers["X-User-ID"] = str(user_id)
    if roles:
        if isinstance(roles, list):
            headers["X-Roles"] = ",".join([str(r) for r in roles])
        else:
            headers["X-Roles"] = str(roles)

    return headers
