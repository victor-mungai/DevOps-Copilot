"""Resource-level cost lookup.

Resource-level savings must come from AWS billing attribution such as CUR/Data
Exports or a pricing API call with enough scope to be auditable. Until that is
wired, this helper returns 0 so no rule fabricates cost.
"""


def estimate_monthly_cost(instance_type: str | None) -> float:
    return 0.0
