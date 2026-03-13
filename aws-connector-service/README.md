# AWS Connector Service

The AWS Connector Service provides secure access to customer AWS environments for the DevOps Copilot platform.

Responsibilities
- Assume customer IAM roles using ExternalId
- Cache temporary STS credentials
- Provide APIs for AWS resource discovery
- Abstract AWS SDK interactions for other microservices

Example APIs
- GET /aws/{tenant_id}/ec2/instances
- GET /aws/{tenant_id}/rds/databases
- GET /aws/{tenant_id}/lambda/functions
- GET /aws/{tenant_id}/cloudwatch/metrics

AWS Access Model
DevOps Copilot Platform
        |
AWS Connector Service
        |
AssumeRole
        |
Customer AWS Account

Technologies
- Python
- FastAPI
- PostgreSQL
- Redis (optional caching)
- AWS SDK
