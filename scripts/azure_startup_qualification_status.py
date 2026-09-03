#!/usr/bin/env python3
"""Read Azure Cost Management and emit a privacy-safe continuity report."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from services.azure_startup_qualification import (
    build_report,
    cost_rows_from_query,
    planned_budget,
)

COST_QUERY_API_VERSION = "2025-03-01"


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Estimate five-workload continuity from Azure ActualCost data."
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--input", type=Path, help="Offline Cost Management response JSON"
    )
    source.add_argument(
        "--subscription-id",
        help="Subscription UUID for a read-only az rest Cost Management query",
    )
    parser.add_argument("--start", type=date.fromisoformat)
    parser.add_argument("--end", type=date.fromisoformat)
    parser.add_argument("--days", type=int, default=75)
    parser.add_argument("--pretty", action="store_true")
    parser.add_argument("--require-qualified-latest-day", action="store_true")
    return parser.parse_args()


def _query_body(start: date, end: date) -> dict[str, Any]:
    return {
        "type": "ActualCost",
        "timeframe": "Custom",
        "timePeriod": {
            "from": f"{start.isoformat()}T00:00:00Z",
            "to": f"{end.isoformat()}T23:59:59Z",
        },
        "dataset": {
            "granularity": "Daily",
            "aggregation": {"CostUSD": {"name": "CostUSD", "function": "Sum"}},
            "grouping": [
                {"type": "Dimension", "name": "ServiceName"},
                {"type": "Dimension", "name": "ResourceId"},
            ],
        },
    }


def _live_query(subscription_id: str, start: date, end: date) -> dict[str, Any]:
    try:
        parsed_subscription = UUID(subscription_id)
    except (ValueError, AttributeError) as error:
        raise RuntimeError("Azure subscription identifier is invalid") from error
    if str(parsed_subscription) != subscription_id.casefold():
        raise RuntimeError("Azure subscription identifier is not canonical")
    url = (
        "https://management.azure.com/subscriptions/"
        f"{subscription_id}/providers/Microsoft.CostManagement/query"
        f"?api-version={COST_QUERY_API_VERSION}"
    )
    try:
        completed = subprocess.run(
            [
                "az",
                "rest",
                "--method",
                "post",
                "--url",
                url,
                "--body",
                json.dumps(_query_body(start, end), separators=(",", ":")),
                "--output",
                "json",
                "--only-show-errors",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired as error:
        raise RuntimeError("Azure Cost Management query timed out") from error
    if completed.returncode != 0:
        raise RuntimeError("Azure Cost Management query failed")
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError("Azure Cost Management returned invalid JSON") from error
    if not isinstance(result, dict):
        raise TypeError("Azure Cost Management returned an invalid document")
    return result


def main() -> int:
    args = _arguments()
    now = datetime.now(timezone.utc)
    if args.days < 1 or args.days > 366:
        raise SystemExit("--days must be between 1 and 366")
    start = args.start or now.date() - timedelta(days=args.days)
    end = args.end or now.date()
    if end < start:
        raise SystemExit("--end cannot be before --start")

    if args.input:
        try:
            payload = json.loads(args.input.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            print(f"status unavailable: {error}", file=sys.stderr)
            return 2
    else:
        try:
            payload = _live_query(args.subscription_id, start, end)
        except (RuntimeError, TypeError) as error:
            print(str(error), file=sys.stderr)
            return 2

    try:
        report = build_report(cost_rows_from_query(payload), generated_at=now)
    except (TypeError, ValueError) as error:
        print(f"status unavailable: {error}", file=sys.stderr)
        return 2
    output = report.as_privacy_safe_dict()
    output["budget"] = planned_budget()
    print(json.dumps(output, indent=2 if args.pretty else None, sort_keys=True))
    if args.require_qualified_latest_day:
        latest = output.get("latest_day")
        if not isinstance(latest, dict) or not latest.get("qualifies"):
            return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
