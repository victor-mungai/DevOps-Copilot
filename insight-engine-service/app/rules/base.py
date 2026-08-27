"""Rule-pack framework (Sprint 3).

Replaces the single monolithic idle-EC2 check with modular rules grouped into
category packs (cost, performance, reliability, availability, security,
compliance). Every rule implements the same tiny interface and is discovered
dynamically by the registry, so adding a rule is just dropping in a module.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Protocol, runtime_checkable


@dataclass
class Ec2Signal:
    """Everything a rule can currently know about one EC2 instance."""

    resource_id: str
    instance_type: Optional[str] = None
    avg_cpu: Optional[float] = None
    samples: int = 0
    tags: dict = field(default_factory=dict)
    state: Optional[str] = None
    region: Optional[str] = None
    account_id: Optional[str] = None
    observed_cost: Optional[float] = None
    cost_window_days: Optional[int] = None
    inactive_hours: Optional[float] = None


@dataclass
class AnalysisContext:
    """Data gathered once per tenant and shared across all rules. Resource lists
    a rule doesn't have data for stay empty, so that rule simply finds nothing."""

    tenant_id: str
    region: Optional[str] = None
    ec2: list[Ec2Signal] = field(default_factory=list)
    # Future signal lists (populated as the connector exposes them):
    ebs: list[dict] = field(default_factory=list)
    rds: list[dict] = field(default_factory=list)
    lambda_functions: list[dict] = field(default_factory=list)
    s3: list[dict] = field(default_factory=list)
    security_groups: list[dict] = field(default_factory=list)
    resource_costs: dict[tuple[str | None, str, str | None], float] = field(default_factory=dict)


@runtime_checkable
class Rule(Protocol):
    id: str
    category: str  # cost_optimization | performance | reliability | availability | security | compliance
    name: str

    def evaluate(self, ctx: AnalysisContext) -> list[dict]:
        ...


def make_finding(
    *,
    tenant_id: str,
    resource_id: str,
    resource_type: str,
    severity: str,
    category: str,
    issue: str,
    recommendation: str,
    confidence: str = "medium",
    estimated_monthly_waste: float = 0.0,
    avg_cpu: Optional[float] = None,
    instance_type: Optional[str] = None,
    window_days: Optional[float] = None,
    aws_account_id: Optional[str] = None,
    region: Optional[str] = None,
    evidence: Optional[str] = None,
    observed_cost: Optional[float] = None,
    inactive_hours: Optional[float] = None,
) -> dict:
    """Build a finding dict matching the `insights` table columns. Non-cost rules
    leave estimated_monthly_waste at 0."""
    return {
        "tenant_id": tenant_id,
        "aws_account_id": aws_account_id,
        "region": region,
        "resource_id": resource_id,
        "resource_type": resource_type,
        "severity": severity,
        "category": category,
        "issue": issue,
        "recommendation": recommendation,
        "confidence": confidence,
        "estimated_monthly_waste": float(estimated_monthly_waste),
        "avg_cpu": avg_cpu,
        "instance_type": instance_type,
        "window_days": window_days,
        "evidence": evidence,
        "observed_cost": observed_cost,
        "inactive_hours": inactive_hours,
    }
