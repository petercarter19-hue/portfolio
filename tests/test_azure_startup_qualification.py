import json
import re
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from scripts.azure_startup_qualification_status import _live_query
from services.azure_startup_qualification import (
    DEFAULT_WORKLOADS,
    CostDataError,
    build_report,
    cost_rows_from_query,
    planned_budget,
)

ROOT = Path(__file__).resolve().parents[1]


def cost_payload(days):
    rows = []
    service_names = [
        "Azure App Service",
        "Azure AI Search",
        "Azure SQL Database",
        "App Configuration",
        "Azure OpenAI Service",
    ]
    for day, amount in days:
        for index, service_name in enumerate(service_names):
            rows.append(
                [
                    amount,
                    int(day.replace("-", "")),
                    service_name,
                    f"/private/resource/{index}",
                    "USD",
                ]
            )
    return {
        "properties": {
            "columns": [
                {"name": "CostUSD", "type": "Number"},
                {"name": "UsageDate", "type": "Number"},
                {"name": "ServiceName", "type": "String"},
                {"name": "ResourceId", "type": "String"},
                {"name": "Currency", "type": "String"},
            ],
            "rows": rows,
        }
    }


class AzureStartupQualificationTests(unittest.TestCase):
    def test_complete_days_build_a_calendar_continuity_streak(self):
        payload = cost_payload(
            [
                ("2026-08-27", 1.1),
                ("2026-08-28", 1.2),
                ("2026-08-29", 1.05),
                ("2026-08-30", 5),
            ]
        )
        report = build_report(
            cost_rows_from_query(payload),
            generated_at=datetime(2026, 8, 30, 16, tzinfo=timezone.utc),
        )
        self.assertEqual(report.current_streak_days, 3)
        self.assertFalse(report.days[-1].complete)
        self.assertFalse(report.days[-1].qualifies)
        self.assertEqual(report.projected_completion_day.isoformat(), "2026-10-25")

    def test_missing_calendar_day_resets_the_streak(self):
        payload = cost_payload([("2026-08-27", 1.1), ("2026-08-29", 1.1)])
        report = build_report(
            cost_rows_from_query(payload),
            generated_at=datetime(2026, 8, 30, tzinfo=timezone.utc),
        )
        self.assertEqual(report.current_streak_days, 1)
        missing_day = next(
            item for item in report.days if item.day.isoformat() == "2026-08-28"
        )
        self.assertFalse(missing_day.qualifies)
        self.assertEqual(len(missing_day.missing_workloads), 5)

    def test_one_under_threshold_workload_fails_the_whole_day(self):
        payload = cost_payload([("2026-08-29", 1.1)])
        payload["properties"]["rows"][-1][0] = 0.999999
        report = build_report(
            cost_rows_from_query(payload),
            generated_at=datetime(2026, 8, 30, tzinfo=timezone.utc),
        )
        self.assertEqual(report.current_streak_days, 0)
        self.assertEqual(report.days[0].missing_workloads, ("foundry_luna",))

    def test_cost_rows_for_one_service_are_aggregated(self):
        payload = cost_payload([("2026-08-29", 1.1)])
        payload["properties"]["rows"][0][0] = 0.6
        payload["properties"]["rows"].append(
            [0.5, 20260829, "Azure App Service", "/another/private/resource", "USD"]
        )
        report = build_report(
            cost_rows_from_query(payload),
            generated_at=datetime(2026, 8, 30, tzinfo=timezone.utc),
        )
        self.assertTrue(report.days[0].qualifies)

    def test_non_usd_and_malformed_data_fail_closed(self):
        payload = cost_payload([("2026-08-29", 1.1)])
        payload["properties"]["rows"][0][-1] = "EUR"
        with self.assertRaises(CostDataError):
            cost_rows_from_query(payload)
        with self.assertRaises(CostDataError):
            cost_rows_from_query({"properties": {"columns": [], "rows": []}})
        paginated = cost_payload([("2026-08-29", 1.1)])
        paginated["properties"]["nextLink"] = "https://private/next-page"
        with self.assertRaisesRegex(CostDataError, "paginated"):
            cost_rows_from_query(paginated)

    def test_privacy_safe_output_has_no_resource_identifiers(self):
        payload = cost_payload([("2026-08-29", 1.1)])
        report = build_report(
            cost_rows_from_query(payload),
            generated_at=datetime(2026, 8, 30, tzinfo=timezone.utc),
        )
        serialized = json.dumps(report.as_privacy_safe_dict())
        self.assertNotIn("/private/resource", serialized)
        self.assertNotIn("resource_id", serialized)
        self.assertIn("Microsoft for Startups portal", serialized)

    def test_privacy_safe_latest_day_excludes_the_partial_utc_day(self):
        payload = cost_payload(
            [("2026-08-29", 1.1), ("2026-08-30", 9.9)]
        )
        report = build_report(
            cost_rows_from_query(payload),
            generated_at=datetime(2026, 8, 30, 16, tzinfo=timezone.utc),
        )
        latest = report.as_privacy_safe_dict()["latest_day"]
        self.assertEqual(latest["day"], "2026-08-29")
        self.assertTrue(latest["complete"])

    def test_budget_target_is_well_below_the_account_credit_ceiling(self):
        budget = planned_budget(DEFAULT_WORKLOADS)
        self.assertAlmostEqual(budget["workload_plan_daily_usd"], 8.29)
        self.assertAlmostEqual(budget["workload_plan_30_day_usd"], 248.7)
        self.assertEqual(budget["expected_all_in_monthly_usd"], 305.0)
        self.assertLess(
            budget["intervention_forecast_monthly_usd"],
            budget["emergency_alert_monthly_usd"],
        )

    def test_status_cli_accepts_offline_data_and_emits_no_resource_id(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cost.json"
            path.write_text(
                json.dumps(cost_payload([("2026-08-29", 1.1)])), encoding="utf-8"
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/azure_startup_qualification_status.py",
                    "--input",
                    str(path),
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertNotIn("/private/resource", completed.stdout)
        self.assertEqual(json.loads(completed.stdout)["target_workload_count"], 5)

    def test_live_query_rejects_a_non_uuid_subscription_before_azure_cli(self):
        with self.assertRaisesRegex(RuntimeError, "identifier is invalid"):
            _live_query(
                "not-a-subscription",
                datetime.now(timezone.utc).date(),
                datetime.now(timezone.utc).date(),
            )

    def test_live_query_timeout_is_generic_and_does_not_expose_command(self):
        subscription_id = "11111111-1111-1111-1111-111111111111"
        with mock.patch(
            "scripts.azure_startup_qualification_status.subprocess.run",
            side_effect=subprocess.TimeoutExpired(["private-command"], 120),
        ):
            with self.assertRaisesRegex(RuntimeError, "query timed out") as raised:
                _live_query(
                    subscription_id,
                    datetime.now(timezone.utc).date(),
                    datetime.now(timezone.utc).date(),
                )
        self.assertNotIn(subscription_id, str(raised.exception))
        self.assertNotIn("private-command", str(raised.exception))

    def test_schedule_definition_is_active_and_uses_two_daily_windows(self):
        pipeline = (ROOT / "pipelines" / "azure-startup-qualification.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("trigger: none", pipeline)
        self.assertIn("pr: none", pipeline)
        self.assertIn("qualificationActivationEnabled: 'true'", pipeline)
        self.assertIn("qualificationCreditConfirmed: 'true'", pipeline)
        self.assertIn("qualificationAppConfigurationEndpoint:", pipeline)
        self.assertIn('--endpoint "$(qualificationAppConfigurationEndpoint)"', pipeline)
        self.assertNotIn('--name "$(qualificationAppConfigurationName)"', pipeline)
        self.assertEqual(len(re.findall(r"^  - cron:", pipeline, re.MULTILINE)), 2)
        self.assertEqual(pipeline.count("always: true"), 2)
        self.assertEqual(pipeline.count("batch: true"), 2)
        self.assertIn("lockBehavior: sequential", pipeline)
        self.assertIn("qualification/foundry/last-success-day", pipeline)
        self.assertIn("--minimum-fresh-input-tokens", pipeline)
        self.assertIn("--minimum-input-tokens-per-call", pipeline)
        self.assertIn("--minimum-call-interval-seconds", pipeline)
        self.assertIn("qualificationSyntheticContextRecords: '13000'", pipeline)
        self.assertIn("qualificationMinimumFreshInputTokens: '2800000'", pipeline)
        self.assertIn("qualificationMinimumInputTokensPerCall: '272001'", pipeline)
        self.assertIn("qualificationMinimumCallIntervalSeconds: '65'", pipeline)
        self.assertNotIn("--only-show-errors 2>/dev/null || true", pipeline)
        self.assertIn("if latest is None:", pipeline)
        self.assertIn("--hard-cap-usd", pipeline)
        self.assertIn("PEERSLATE_AZURE_SPEND_AUTHORIZATION_REF", pipeline)

    def test_pipeline_does_not_borrow_the_production_deploy_identity(self):
        """A nightly cost read must not hold deploy/migration authority.

        The production connection id is read out of azure-pipelines.yml rather
        than hardcoded here, so this keeps protecting the boundary even if that
        connection is rotated.
        """
        production = (ROOT / "azure-pipelines.yml").read_text(encoding="utf-8")
        match = re.search(
            r"^\s*azureServiceConnectionId:\s*'([0-9a-fA-F-]{36})'",
            production,
            re.MULTILINE,
        )
        self.assertIsNotNone(match, "production service connection id not found")
        production_connection = match.group(1)

        pipeline = (ROOT / "pipelines" / "azure-startup-qualification.yml").read_text(
            encoding="utf-8"
        )
        self.assertNotIn(production_connection, pipeline)
        self.assertIn(
            "qualificationServiceConnectionId: 'peerslate-startup-qualification-wif'",
            pipeline,
        )
        self.assertNotIn("$(azureServiceConnectionId)", pipeline)

    def test_pipeline_gates_every_operative_stage_after_activation(self):
        pipeline = (ROOT / "pipelines" / "azure-startup-qualification.yml").read_text(
            encoding="utf-8"
        )
        self.assertTrue(re.search(r"^schedules:", pipeline, re.MULTILINE))
        operative = [
            block for block in pipeline.split("  - stage: ") if "AzureCLI@2" in block
        ]
        self.assertEqual(len(operative), 2, "expected two operative stages")
        for block in operative:
            condition = block.split("jobs:")[0]
            self.assertIn(
                "ne(variables['qualificationServiceConnectionId'], '')",
                condition,
                "operative stage runs without a supplied service connection",
            )
        foundry = next(block for block in operative if "FoundryEvaluation" in block)
        self.assertIn("always()", foundry.split("jobs:")[0])

    def test_status_cli_can_signal_a_latest_day_shortfall_after_printing(self):
        payload = cost_payload([("2026-08-29", 1.1)])
        payload["properties"]["rows"][-1][0] = 0.5
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cost.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/azure_startup_qualification_status.py",
                    "--input",
                    str(path),
                    "--require-qualified-latest-day",
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertEqual(completed.returncode, 3)
        self.assertFalse(json.loads(completed.stdout)["latest_day"]["qualifies"])


class QualifyingThresholdTests(unittest.TestCase):
    """The milestone rule is ABOVE $1, and this reader must never overstate."""

    def _qualifying_count(self, amount):
        payload = cost_payload([("2026-08-01", amount)])
        report = build_report(
            cost_rows_from_query(payload),
            workloads=DEFAULT_WORKLOADS,
            generated_at=datetime(2026, 8, 2, tzinfo=timezone.utc),
        )
        complete = [day for day in report.days if day.complete]
        self.assertTrue(complete, "expected at least one complete day")
        return len(complete[0].qualified_workloads)

    def test_exactly_one_dollar_does_not_qualify(self):
        self.assertEqual(self._qualifying_count(1.0), 0)

    def test_one_micro_dollar_above_one_dollar_qualifies(self):
        self.assertEqual(self._qualifying_count(1.000001), 5)

    def test_just_below_one_dollar_does_not_qualify(self):
        self.assertEqual(self._qualifying_count(0.999999), 0)


class CurrencyGuardTests(unittest.TestCase):
    """Billing-currency meters must not be scored against a dollar threshold."""

    @staticmethod
    def _payload(cost_column, columns_include_currency):
        columns = [
            {"name": cost_column, "type": "Number"},
            {"name": "UsageDate", "type": "Number"},
            {"name": "ServiceName", "type": "String"},
        ]
        row = [2.5, 20260801, "Azure App Service"]
        if columns_include_currency:
            columns.append({"name": "Currency", "type": "String"})
            row.append("USD")
        return {"properties": {"columns": columns, "rows": [row]}}

    def test_billing_currency_meter_without_currency_column_is_refused(self):
        with self.assertRaises(CostDataError):
            cost_rows_from_query(self._payload("PreTaxCost", False))

    def test_cost_usd_column_needs_no_currency_column(self):
        rows = cost_rows_from_query(self._payload("CostUSD", False))
        self.assertEqual(len(rows), 1)

    def test_billing_currency_meter_with_usd_currency_is_accepted(self):
        rows = cost_rows_from_query(self._payload("PreTaxCost", True))
        self.assertEqual(len(rows), 1)


if __name__ == "__main__":
    unittest.main()
