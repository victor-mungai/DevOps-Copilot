"""Feature 1: Underutilized / Idle EC2 detection.

One rule, done well. An instance is "idle" when its average CPU over the window
is below the threshold AND we have enough samples to trust the verdict.
"""

import os
from typing import Optional

from .. import config

# A 7-day window at the default 60s scrape would be ~10k samples. Require a
# modest fraction so a freshly-connected account doesn't produce false positives.
MIN_SAMPLES_FOR_VERDICT = int(os.getenv("IDLE_MIN_SAMPLES", "60"))


def evaluate(
    tenant_id: str,
    instance_id: str,
    instance_type: Optional[str],
    avg_cpu: float,
    samples: int,
) -> Optional[dict]:
    """Return a structured insight dict if the instance is idle, else None."""
    assert tenant_id, "tenant_id is required"  # Feature 6: tenant isolation

    if samples < MIN_SAMPLES_FOR_VERDICT:
        return None  # not enough history to call it idle yet
    if avg_cpu >= config.IDLE_CPU_THRESHOLD:
        return None

    # Confidence: high when clearly idle with solid data; medium when borderline.
    clearly_idle = avg_cpu < (config.IDLE_CPU_THRESHOLD / 2)
    confidence = "high" if clearly_idle else "medium"

    return {
        "tenant_id": tenant_id,
        "resource_id": instance_id,
        "resource_type": "ec2",
        "severity": "medium",
        "category": "cost_optimization",
        "issue": "Underutilized EC2 Instance",
        "recommendation": "Consider downsizing or terminating this instance.",
        "confidence": confidence,
        "estimated_monthly_waste": 0.0,
        "avg_cpu": round(avg_cpu, 2),
        "instance_type": instance_type,
        "window_days": float(config.IDLE_WINDOW_DAYS),
    }
