# DevOps-Copilot
DevOps Copilot is an AI-powered platform that connects to AWS environments and automatically analyzes infrastructure metrics to provide operational insights, cost optimization recommendations, and performance diagnostics.
#Features

Secure AWS cross-account integration using IAM roles

Automated infrastructure discovery

CloudWatch metrics analysis

AI-powered insights and recommendations

Multi-tenant architecture

Scalable microservices design

#Architecture

The platform consists of multiple microservices:

Service	Description
API Gateway	Public API and tenant management
Onboarding Service	AWS account integration
AWS Connector	Cross-account role assumption
Metrics Collector	Cloud metrics ingestion
Insight Engine	Infrastructure analysis
LLM Service	AI explanation generation
Worker Service	Background task processing
#Technologies

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
