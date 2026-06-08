# DevOps-Copilot
DevOps Copilot is an AI-powered platform that connects to AWS environments and automatically analyzes infrastructure metrics to provide operational insights, cost optimization recommendations, and performance diagnostics.
# Features

Secure AWS cross-account integration using IAM roles

Automated infrastructure discovery

CloudWatch metrics analysis

AI-powered insights and recommendations

Multi-tenant architecture

Scalable microservices design

# Architecture

The platform consists of multiple microservices:

Service	Description
# 1 API Gateway	Public API and tenant management


# 2 Onboarding Service	AWS account integration


The onboarding service manages secure AWS account integration for DevOps Copilot tenants.

It handles the lifecycle of connecting a customer's AWS environment using cross-account IAM roles and ExternalId protection.

# Tenant Identification Rules
- `tenant_id` is the primary identifier across all services and APIs.
- `tenant_name` is non-unique and for display/logging only.
- `external_id` must be unique and is used only for STS role assumption.
- All internal operations must rely on `tenant_id`.

# Responsibilities

Create tenants and generate unique External IDs

Generate AWS CloudFormation onboarding links

Verify IAM role access via AWS STS AssumeRole

Persist AWS account integration metadata

# API Endpoints
```
Endpoint	Description
POST /tenants	Create tenant and generate external ID
GET /tenants/{tenant_id}/onboarding-link	Generate AWS onboarding link
POST /tenants/{tenant_id}/verify	Verify IAM role via AssumeRole
AWS Integration Flow
Tenant created
     |
External ID generated
     |
Customer deploys CloudFormation stack
     |
IAM role created in customer account
     |
Role ARN submitted
     |
AssumeRole verification
     |
AWS account connected
Database
```
The service uses PostgreSQL with two main tables:
```
tenants
aws_accounts
Security Model
```
# AWS access uses:

cross-account IAM roles

ExternalId protection

temporary STS credentials

No customer credentials are stored or shared.



AWS Connector	Cross-account role assumption
Metrics Collector	Cloud metrics ingestion
Insight Engine	Infrastructure analysis
LLM Service	AI explanation generation
Worker Service	Background task processing
# Technologies

Python / FastAPI

Docker

PostgreSQL

Redis

Vector Database

AWS SDK

LLM APIs

AWS Integration

Customers connect their AWS accounts via a secure IAM role using an ExternalId-based trust policy.

This allows the platform to safely access:

EC2

RDS

Lambda

CloudWatch

without sharing credentials.
