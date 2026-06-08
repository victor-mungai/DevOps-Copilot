# Gateway Service

The Gateway Service is the public entry point for the DevOps Copilot platform.

Responsibilities
- API request routing
- authentication and authorization
- tenant context propagation
- rate limiting
- service aggregation (future)

Default Routes
- / -> UI service
- /v1/health -> gateway health
- /v1/tenants -> onboarding service
- /v1/aws/* -> aws connector service
- /v1/metrics/* -> metrics collector service

Environment
- ONBOARDING_SERVICE_URL
- AWS_CONNECTOR_SERVICE_URL
- UI_SERVICE_URL
- JWT_SECRET
- JWT_ALGORITHM
- AUTH_DISABLED (true/false)
- AUTH_EXEMPT_PATHS
- RATE_LIMIT_PER_MINUTE
- RATE_LIMIT_DISABLED
- CORS_ALLOW_ORIGINS

Run (local)
1. pip install -r requirements.txt
2. uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
