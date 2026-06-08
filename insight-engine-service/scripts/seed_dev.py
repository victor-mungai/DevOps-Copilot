"""Seed synthetic metrics for the offline dev provider (METRIC_SOURCE=dev).

Writes a seed_metrics.json describing, per tenant, an idle instance (fires the
rule) and a busy control instance (should NOT produce an insight). This lets the
full value loop be demoed with no Docker / Prometheus / AWS.

Usage:
    python scripts/seed_dev.py --tenant <tenant_id> [--out seed_metrics.json]
"""

import argparse
import json


def build_seed(tenant_id: str) -> dict:
    return {
        "tenants": {
            tenant_id: [
                {
                    "instance_id": "i-0idle1234567890ab",
                    "instance_type": "t3.large",
                    "avg_cpu": 2.1,        # < 5% threshold -> idle
                    "samples": 10080,      # ~7d at 60s -> trusted verdict
                },
                {
                    "instance_id": "i-0busy234567890cd",
                    "instance_type": "t3.medium",
                    "avg_cpu": 55.0,       # busy control -> no insight
                    "samples": 10080,
                },
            ]
        }
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tenant", required=True, help="tenant_id to seed")
    parser.add_argument("--out", default="seed_metrics.json")
    args = parser.parse_args()

    seed = build_seed(args.tenant)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(seed, fh, indent=2)
    print(f"Wrote {args.out} for tenant {args.tenant}")
    print("  i-0idle1234567890ab  cpu=2.1%   -> expect 1 insight")
    print("  i-0busy234567890cd   cpu=55.0%  -> expect no insight")


if __name__ == "__main__":
    main()
