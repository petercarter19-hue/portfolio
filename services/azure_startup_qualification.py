"""Privacy-safe Azure startup qualification continuity calculations.

This module reads already-returned Cost Management data.  It does not create,
resize, configure, start, or stop Azure resources, and it does not decide
whether Microsoft has awarded a credit tier.  The Microsoft for Startups
portal remains authoritative; this is the conservative operator-side warning
system for the documented daily workload threshold.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

MICRO_USD_PER_USD = 1_000_000
QUALIFYING_DAILY_MICRO_USD = MICRO_USD_PER_USD
SAFE_DAILY_TARGET_MICRO_USD = 1_100_000
TARGET_CONTINUOUS_DAYS = 60
TARGET_WORKLOAD_COUNT = 5


class CostDataError(ValueError):
    """The Cost Management response cannot support a safe status report."""


@dataclass(frozen=True)
class WorkloadDefinition:
    key: str
    label: str
    service_names: frozenset[str]
    resource_id_fragments: tuple[str, ...] = ()
    planned_daily_micro_usd: int = SAFE_DAILY_TARGET_MICRO_USD

    def __post_init__(self) -> None:
        if not self.key or not self.key.replace("_", "").isalnum():
            raise ValueError("workload key must be a bounded identifier")
        if not self.label.strip():
            raise ValueError("workload label is required")
        if not self.service_names:
            raise ValueError("a workload needs at least one service name")
        if self.planned_daily_micro_usd < QUALIFYING_DAILY_MICRO_USD:
            raise ValueError("planned daily spend must not be below the threshold")

    def matches(self, row: DailyCostRow) -> bool:
        service_match = row.service_name.casefold() in {
            value.casefold() for value in self.service_names
        }
        if not service_match:
            return False
        if not self.resource_id_fragments:
            return True
        resource_id = row.resource_id.casefold()
        return any(
            value.casefold() in resource_id for value in self.resource_id_fragments
        )


DEFAULT_WORKLOADS = (
    WorkloadDefinition(
        key="app_service",
        label="Azure App Service",
        service_names=frozenset({"Azure App Service", "App Service"}),
        planned_daily_micro_usd=2_470_000,
    ),
    WorkloadDefinition(
        key="ai_search",
        label="Azure AI Search",
        service_names=frozenset(
            {"Azure AI Search", "Azure Cognitive Search", "Cognitive Search"}
        ),
        planned_daily_micro_usd=2_420_000,
    ),
    WorkloadDefinition(
        key="azure_sql",
        label="Azure SQL Database",
        service_names=frozenset(
            {"Azure SQL Database", "SQL Database", "SQL Database - Single"}
        ),
    ),
    WorkloadDefinition(
        key="app_configuration",
        label="Azure App Configuration Standard",
        service_names=frozenset({"App Configuration", "Azure App Configuration"}),
        planned_daily_micro_usd=1_200_000,
    ),
    WorkloadDefinition(
        key="foundry_luna",
        label="Microsoft Foundry GPT-5.6 Luna",
        service_names=frozenset(
            {
                "Azure OpenAI Service",
                "Azure AI Foundry Models",
                "Microsoft Foundry Models",
                "Foundry Models",
            }
        ),
    ),
)


@dataclass(frozen=True)
class DailyCostRow:
    day: date
    cost_micro_usd: int
    service_name: str
    resource_id: str


@dataclass(frozen=True)
class DailyQualificationStatus:
    day: date
    complete: bool
    workload_costs_micro_usd: Mapping[str, int]
    qualified_workloads: tuple[str, ...]
    missing_workloads: tuple[str, ...]

    @property
    def qualifies(self) -> bool:
        return self.complete and not self.missing_workloads


@dataclass(frozen=True)
class QualificationReport:
    generated_at: datetime
    target_days: int
    threshold_micro_usd: int
    workloads: tuple[WorkloadDefinition, ...]
    days: tuple[DailyQualificationStatus, ...]
    current_streak_days: int
    projected_completion_day: date | None

    def as_privacy_safe_dict(self) -> dict[str, Any]:
        """Return aggregates only; subscription and resource IDs never leave."""

        newest = self.days[-1] if self.days else None
        return {
            "generated_at": self.generated_at.isoformat(),
            "authoritative_source": "Microsoft for Startups portal",
            "status_source": "Azure Cost Management ActualCost estimate",
            "threshold_usd_per_workload_day": self.threshold_micro_usd
            / MICRO_USD_PER_USD,
            "target_continuous_days": self.target_days,
            "target_workload_count": len(self.workloads),
            "current_complete_day_streak": self.current_streak_days,
            "projected_completion_day": (
                self.projected_completion_day.isoformat()
                if self.projected_completion_day
                else None
            ),
            "latest_day": _status_dict(newest) if newest else None,
            "workloads": [
                {
                    "key": workload.key,
                    "label": workload.label,
                    "planned_daily_usd": workload.planned_daily_micro_usd
                    / MICRO_USD_PER_USD,
                }
                for workload in self.workloads
            ],
            "days": [_status_dict(item) for item in self.days],
            "limitations": [
                "Cost Management data can arrive late and the current UTC day is incomplete.",
                "Only the Microsoft for Startups portal can confirm qualifying workloads and tier progress.",
                "A missing or ambiguous row is treated as not qualifying.",
            ],
        }


def _status_dict(status: DailyQualificationStatus) -> dict[str, Any]:
    return {
        "day": status.day.isoformat(),
        "complete": status.complete,
        "qualifies": status.qualifies,
        "qualified_workloads": list(status.qualified_workloads),
        "missing_workloads": list(status.missing_workloads),
        "workload_cost_usd": {
            key: round(value / MICRO_USD_PER_USD, 6)
            for key, value in sorted(status.workload_costs_micro_usd.items())
        },
    }


def _parse_day(value: object) -> date:
    if isinstance(value, bool):
        raise CostDataError("usage date has an invalid type")
    text = str(value).strip()
    if len(text) == 8 and text.isdigit():
        text = f"{text[:4]}-{text[4:6]}-{text[6:]}"
    try:
        return date.fromisoformat(text)
    except ValueError as error:
        raise CostDataError("usage date is not YYYYMMDD or YYYY-MM-DD") from error


def _micro_usd(value: object) -> int:
    try:
        decimal = Decimal(str(value))
    except (InvalidOperation, ValueError) as error:
        raise CostDataError("cost is not numeric") from error
    if not decimal.is_finite() or decimal < 0:
        raise CostDataError("cost must be a finite non-negative value")
    return int(
        (decimal * MICRO_USD_PER_USD).quantize(Decimal(1), rounding=ROUND_HALF_UP)
    )


def cost_rows_from_query(payload: Mapping[str, Any]) -> tuple[DailyCostRow, ...]:
    """Strictly decode one Azure Cost Management query response."""

    properties = payload.get("properties")
    if not isinstance(properties, Mapping):
        raise CostDataError("Cost Management response has no properties object")
    if properties.get("nextLink") or payload.get("nextLink"):
        raise CostDataError("paginated Cost Management data is incomplete")
    columns = properties.get("columns")
    rows = properties.get("rows")
    if not isinstance(columns, Sequence) or isinstance(columns, (str, bytes)):
        raise CostDataError("Cost Management response has no columns")
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        raise CostDataError("Cost Management response has no rows")

    names: list[str] = []
    for column in columns:
        if not isinstance(column, Mapping) or not isinstance(column.get("name"), str):
            raise CostDataError("Cost Management column is malformed")
        names.append(column["name"])
    aliases = {
        "cost": ("CostUSD", "PreTaxCost", "Cost"),
        "day": ("UsageDate",),
        "service": ("ServiceName", "ServiceTier"),
        "resource": ("ResourceId",),
        "currency": ("Currency",),
    }

    def index_for(label: str, *, required: bool = True) -> int | None:
        for candidate in aliases[label]:
            if candidate in names:
                return names.index(candidate)
        if required:
            raise CostDataError(f"Cost Management response is missing {label}")
        return None

    cost_index = index_for("cost")
    day_index = index_for("day")
    service_index = index_for("service")
    resource_index = index_for("resource", required=False)
    currency_index = index_for("currency", required=False)
    # "CostUSD" is denominated in USD by definition.  "PreTaxCost" and "Cost"
    # are billing-currency meters, so without a Currency column their numbers
    # could be euros or pounds scored against a dollar threshold.  Refuse
    # rather than silently compare different currencies.
    if currency_index is None and names[cost_index] != "CostUSD":
        raise CostDataError(
            "qualification estimate requires either a CostUSD column or an "
            "explicit Currency column"
        )

    decoded: list[DailyCostRow] = []
    for row in rows:
        if not isinstance(row, Sequence) or isinstance(row, (str, bytes)):
            raise CostDataError("Cost Management row is malformed")
        if len(row) != len(names):
            raise CostDataError("Cost Management row length does not match columns")
        if currency_index is not None and str(row[currency_index]).upper() != "USD":
            raise CostDataError("qualification estimate requires USD cost data")
        service_name = str(row[service_index]).strip()
        if not service_name:
            raise CostDataError("Cost Management row has no service name")
        decoded.append(
            DailyCostRow(
                day=_parse_day(row[day_index]),
                cost_micro_usd=_micro_usd(row[cost_index]),
                service_name=service_name,
                resource_id=(
                    str(row[resource_index]).strip()
                    if resource_index is not None
                    else ""
                ),
            )
        )
    return tuple(decoded)


def build_report(
    rows: Sequence[DailyCostRow],
    *,
    workloads: Sequence[WorkloadDefinition] = DEFAULT_WORKLOADS,
    generated_at: datetime | None = None,
    target_days: int = TARGET_CONTINUOUS_DAYS,
) -> QualificationReport:
    if len(workloads) < TARGET_WORKLOAD_COUNT:
        raise ValueError("at least five workload definitions are required")
    keys = [workload.key for workload in workloads]
    if len(keys) != len(set(keys)):
        raise ValueError("workload keys must be unique")
    if target_days < 1:
        raise ValueError("target days must be positive")

    now = generated_at or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("generated_at must be timezone-aware")
    utc_now = now.astimezone(timezone.utc)
    today = utc_now.date()
    totals: dict[date, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for row in rows:
        matches = [workload for workload in workloads if workload.matches(row)]
        if len(matches) > 1:
            raise CostDataError("one cost row matched multiple workload definitions")
        if matches:
            totals[row.day][matches[0].key] += row.cost_micro_usd

    if totals:
        first_day = min(totals)
    else:
        first_day = today
    calendar_days: list[DailyQualificationStatus] = []
    cursor = first_day
    while cursor <= today:
        costs = {key: totals[cursor].get(key, 0) for key in keys}
        # The milestone rule is "above $1", so a day worth exactly $1.000000
        # does not qualify.  Strictly greater keeps the estimate conservative:
        # this reader must never claim more progress than Microsoft would.
        qualified = tuple(
            key for key in keys if costs[key] > QUALIFYING_DAILY_MICRO_USD
        )
        missing = tuple(key for key in keys if key not in qualified)
        calendar_days.append(
            DailyQualificationStatus(
                day=cursor,
                complete=cursor < today,
                workload_costs_micro_usd=costs,
                qualified_workloads=qualified,
                missing_workloads=missing,
            )
        )
        cursor += timedelta(days=1)

    streak = 0
    expected = today - timedelta(days=1)
    by_day = {item.day: item for item in calendar_days}
    while expected in by_day and by_day[expected].qualifies:
        streak += 1
        expected -= timedelta(days=1)

    projected = (
        today + timedelta(days=max(0, target_days - streak) - 1)
        if streak < target_days
        else today - timedelta(days=1)
    )
    return QualificationReport(
        generated_at=utc_now,
        target_days=target_days,
        threshold_micro_usd=QUALIFYING_DAILY_MICRO_USD,
        workloads=tuple(workloads),
        days=tuple(calendar_days),
        current_streak_days=streak,
        projected_completion_day=projected,
    )


def planned_budget(
    workloads: Sequence[WorkloadDefinition] = DEFAULT_WORKLOADS,
) -> dict[str, Any]:
    daily = sum(item.planned_daily_micro_usd for item in workloads)
    return {
        "planned_daily_usd": daily / MICRO_USD_PER_USD,
        "planned_30_day_usd": daily * 30 / MICRO_USD_PER_USD,
        "planned_60_day_usd": daily * 60 / MICRO_USD_PER_USD,
        "operating_warning_monthly_usd": 275.0,
        "operating_hard_ceiling_monthly_usd": 325.0,
        "account_credit_ceiling_monthly_usd": 550.0,
    }
