import json
import re
import subprocess
import sys
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest import mock

from scripts.azure_startup_qualification_status import (
    AzureBillingReadError,
    HttpJsonResponse,
    _cost_details_csv_rows,
    _cost_details_query,
    _cost_details_report,
    _live_query,
    _monthly_ranges,
    _validate_cost_details_poll_url,
    _validated_cost_details_blobs,
)
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
        "Container Registry",
        "Foundry Tools",
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


def cost_details_report_payload(
    start="2026-09-01", end="2026-09-13", *, byte_count=100, blob_name="report"
):
    return {
        "status": "Completed",
        "manifest": {
            "blobCount": 1,
            "blobs": [
                {
                    "blobLink": (
                        "https://ccmreportstorageeastus.blob.core.windows.net/"
                        f"armreports/{blob_name}.csv?sv=1&sig=secret"
                    ),
                    "byteCount": byte_count,
                }
            ],
            "byteCount": byte_count,
            "compressData": False,
            "dataFormat": "Csv",
            "requestContext": {
                "requestBody": {
                    "metric": "ActualCost",
                    "timePeriod": {"start": start, "end": end},
                },
                "requestScope": (
                    "subscriptions/11111111-1111-1111-1111-111111111111"
                ),
            },
        },
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
        self.assertEqual(len(missing_day.missing_workloads), 7)

    def test_one_under_threshold_workload_fails_the_whole_day(self):
        payload = cost_payload([("2026-08-29", 1.1)])
        payload["properties"]["rows"][-1][0] = 0.999999
        report = build_report(
            cost_rows_from_query(payload),
            generated_at=datetime(2026, 8, 30, tzinfo=timezone.utc),
        )
        self.assertEqual(report.current_streak_days, 0)
        self.assertEqual(report.days[0].missing_workloads, ("azure_speech",))

    def test_five_service_streak_survives_two_shortfalls_but_seven_does_not(self):
        payload = cost_payload([("2026-08-29", 1.1)])
        payload["properties"]["rows"][-1][0] = 0.5
        payload["properties"]["rows"][-2][0] = 0.5
        report = build_report(
            cost_rows_from_query(payload),
            generated_at=datetime(2026, 8, 30, tzinfo=timezone.utc),
        )
        self.assertEqual(report.current_five_workload_streak_days, 1)
        self.assertEqual(report.current_streak_days, 0)
        self.assertTrue(report.days[0].qualifies_five)
        self.assertFalse(report.days[0].qualifies)

    def test_five_service_streak_cannot_rotate_workloads_between_days(self):
        payload = cost_payload(
            [("2026-09-02", 1.1), ("2026-09-03", 1.1)]
        )
        rows = payload["properties"]["rows"]
        # Day one misses App Service and Search; day two misses SQL and App
        # Configuration.  Each day has five qualifying workloads, but only
        # Foundry, ACR, and Speech are continuous across both days.
        rows[0][0] = 0.5
        rows[1][0] = 0.5
        rows[9][0] = 0.5
        rows[10][0] = 0.5
        report = build_report(
            cost_rows_from_query(payload),
            generated_at=datetime(2026, 9, 4, tzinfo=timezone.utc),
        )
        self.assertTrue(
            all(day.qualifies_five for day in report.days if day.complete)
        )
        self.assertEqual(report.current_five_workload_streak_days, 1)
        self.assertEqual(report.current_workload_streak_days["foundry_luna"], 2)
        self.assertEqual(report.current_workload_streak_days["app_service"], 1)
        self.assertEqual(report.current_workload_streak_days["azure_sql"], 0)

    def test_privacy_safe_report_includes_each_workload_streak(self):
        payload = cost_payload([("2026-08-29", 1.1)])
        report = build_report(
            cost_rows_from_query(payload),
            generated_at=datetime(2026, 8, 30, tzinfo=timezone.utc),
        )
        output = report.as_privacy_safe_dict()
        self.assertEqual(
            set(output["current_workload_streak_days"]),
            {workload.key for workload in DEFAULT_WORKLOADS},
        )
        self.assertTrue(
            all(value == 1 for value in output["current_workload_streak_days"].values())
        )

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
        self.assertAlmostEqual(budget["workload_plan_daily_usd"], 12.4016)
        self.assertAlmostEqual(budget["workload_plan_30_day_usd"], 372.048)
        self.assertEqual(budget["expected_all_in_monthly_usd"], 427.32)
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
        self.assertEqual(json.loads(completed.stdout)["target_workload_count"], 7)

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

    def test_live_query_falls_back_only_when_cost_management_is_rate_limited(self):
        subscription_id = "11111111-1111-1111-1111-111111111111"
        with mock.patch(
            "scripts.azure_startup_qualification_status._cost_management_query",
            side_effect=AzureBillingReadError("rate_limited", "rate limited"),
        ) as primary, mock.patch(
            "scripts.azure_startup_qualification_status._cost_details_query",
            return_value=cost_payload([("2026-09-12", 1.25)]),
        ) as fallback:
            result = _live_query(
                subscription_id, date(2026, 9, 1), date(2026, 9, 13)
            )
        primary.assert_called_once()
        fallback.assert_called_once_with(
            subscription_id, date(2026, 9, 1), date(2026, 9, 13)
        )
        self.assertEqual(result.fallback_reason, "cost_management_rate_limited")
        self.assertIn("Cost Details", result.source)
        rows = cost_rows_from_query(result.payload)
        self.assertEqual(len(rows), 7)
        self.assertEqual(rows[0].day, date(2026, 9, 12))

    def test_live_query_does_not_mask_a_non_rate_limit_failure(self):
        subscription_id = "11111111-1111-1111-1111-111111111111"
        with mock.patch(
            "scripts.azure_startup_qualification_status._cost_management_query",
            side_effect=AzureBillingReadError("unavailable", "query failed"),
        ) as primary, mock.patch(
            "scripts.azure_startup_qualification_status._cost_details_query"
        ) as fallback:
            with self.assertRaisesRegex(AzureBillingReadError, "query failed"):
                _live_query(
                    subscription_id, date(2026, 9, 1), date(2026, 9, 13)
                )
        primary.assert_called_once()
        fallback.assert_not_called()

    def test_cost_details_fallback_splits_the_full_window_by_calendar_month(self):
        subscription_id = "11111111-1111-1111-1111-111111111111"
        self.assertEqual(
            _monthly_ranges(date(2026, 7, 20), date(2026, 9, 13)),
            (
                (date(2026, 7, 20), date(2026, 7, 31)),
                (date(2026, 8, 1), date(2026, 8, 31)),
                (date(2026, 9, 1), date(2026, 9, 13)),
            ),
        )
        with mock.patch(
            "scripts.azure_startup_qualification_status._cost_details_report",
            return_value=None,
        ) as report:
            payload = _cost_details_query(
                subscription_id, date(2026, 7, 20), date(2026, 9, 13)
            )
        self.assertEqual(cost_rows_from_query(payload), ())
        self.assertEqual(
            sorted(call.args[1:] for call in report.call_args_list),
            [
                (date(2026, 7, 20), date(2026, 7, 31)),
                (date(2026, 8, 1), date(2026, 8, 31)),
                (date(2026, 9, 1), date(2026, 9, 13)),
            ],
        )

    def test_cost_details_polling_requests_exact_period_and_terminates(self):
        subscription_id = "11111111-1111-1111-1111-111111111111"
        poll_url = (
            "https://management.azure.com/subscriptions/"
            f"{subscription_id}/providers/Microsoft.CostManagement/"
            "costDetailsOperationResults/22222222-2222-2222-2222-222222222222"
            "?api-version=2025-03-01"
        )
        credential = mock.Mock()
        client = mock.Mock()
        responses = [
            HttpJsonResponse(
                202, None, {"location": poll_url, "retry-after": "1"}
            ),
            HttpJsonResponse(200, cost_details_report_payload(), {}),
        ]
        with mock.patch(
            "scripts.azure_startup_qualification_status._cost_management_client",
            return_value=(credential, client),
        ), mock.patch(
            "scripts.azure_startup_qualification_status._cost_details_http_response",
            side_effect=responses,
        ) as request, mock.patch(
            "scripts.azure_startup_qualification_status.time.sleep"
        ) as sleep:
            result = _cost_details_report(
                subscription_id=subscription_id,
                start=date(2026, 9, 1),
                end=date(2026, 9, 13),
            )
        self.assertEqual(result, cost_details_report_payload())
        self.assertEqual(request.call_count, 2)
        self.assertEqual(request.call_args_list[0].kwargs["method"], "POST")
        self.assertEqual(
            request.call_args_list[0].kwargs["body"]["timePeriod"],
            {"start": "2026-09-01", "end": "2026-09-13"},
        )
        self.assertEqual(request.call_args_list[1].kwargs["url"], poll_url)
        self.assertEqual(request.call_args_list[1].kwargs["method"], "GET")
        sleep.assert_called_once_with(1)
        client.close.assert_called_once()
        credential.close.assert_called_once()

    def test_cost_details_polling_stops_at_the_attempt_boundary(self):
        subscription_id = "11111111-1111-1111-1111-111111111111"
        poll_url = (
            "https://management.azure.com/subscriptions/"
            f"{subscription_id}/providers/Microsoft.CostManagement/"
            "costDetailsOperationResults/22222222-2222-2222-2222-222222222222"
            "?api-version=2025-03-01"
        )
        credential = mock.Mock()
        client = mock.Mock()
        pending = [
            HttpJsonResponse(
                202,
                None,
                {"location": poll_url, "retry-after": "60"},
            )
        ] + [
            HttpJsonResponse(202, None, {"retry-after": "60"})
            for _ in range(15)
        ]
        with mock.patch(
            "scripts.azure_startup_qualification_status._cost_management_client",
            return_value=(credential, client),
        ), mock.patch(
            "scripts.azure_startup_qualification_status._cost_details_http_response",
            side_effect=pending,
        ) as request, mock.patch(
            "scripts.azure_startup_qualification_status.time.sleep"
        ) as sleep:
            with self.assertRaisesRegex(
                AzureBillingReadError, "report generation timed out"
            ):
                _cost_details_report(
                    subscription_id=subscription_id,
                    start=date(2026, 9, 1),
                    end=date(2026, 9, 13),
                )
        self.assertEqual(request.call_count, 16)
        self.assertEqual(sleep.call_count, 15)
        client.close.assert_called_once()
        credential.close.assert_called_once()

    def test_cost_details_polling_stops_at_the_wall_clock_deadline(self):
        subscription_id = "11111111-1111-1111-1111-111111111111"
        poll_url = (
            "https://management.azure.com/subscriptions/"
            f"{subscription_id}/providers/Microsoft.CostManagement/"
            "costDetailsOperationResults/22222222-2222-2222-2222-222222222222"
            "?api-version=2025-03-01"
        )
        credential = mock.Mock()
        client = mock.Mock()
        with mock.patch(
            "scripts.azure_startup_qualification_status.MAX_COST_DETAILS_POLL_WAIT_SECONDS",
            1,
        ), mock.patch(
            "scripts.azure_startup_qualification_status._cost_management_client",
            return_value=(credential, client),
        ), mock.patch(
            "scripts.azure_startup_qualification_status._cost_details_http_response",
            return_value=HttpJsonResponse(
                202, None, {"location": poll_url, "retry-after": "60"}
            ),
        ) as request, mock.patch(
            "scripts.azure_startup_qualification_status.time.monotonic",
            side_effect=[100.0, 100.0],
        ), mock.patch(
            "scripts.azure_startup_qualification_status.time.sleep"
        ) as sleep:
            with self.assertRaisesRegex(
                AzureBillingReadError, "report generation timed out"
            ):
                _cost_details_report(
                    subscription_id=subscription_id,
                    start=date(2026, 9, 1),
                    end=date(2026, 9, 13),
                )
        request.assert_not_called()
        sleep.assert_not_called()
        client.close.assert_called_once()
        credential.close.assert_called_once()

    def test_cost_details_polling_refuses_an_untrusted_origin(self):
        with self.assertRaisesRegex(AzureBillingReadError, "polling URL is invalid"):
            _validate_cost_details_poll_url(
                "https://attacker.example/steal?api-version=2025-03-01",
                subscription_id="11111111-1111-1111-1111-111111111111",
            )

    def test_cost_details_manifest_binds_the_exact_requested_period(self):
        blobs = _validated_cost_details_blobs(
            cost_details_report_payload(),
            subscription_id="11111111-1111-1111-1111-111111111111",
            start=date(2026, 9, 1),
            end=date(2026, 9, 13),
        )
        self.assertEqual(len(blobs), 1)
        wrong_period = cost_details_report_payload()
        wrong_period["manifest"]["requestContext"]["requestBody"]["timePeriod"] = {
            "start": "2026-09-02",
            "end": "2026-09-13",
        }
        with self.assertRaisesRegex(AzureBillingReadError, "manifest is invalid"):
            _validated_cost_details_blobs(
                wrong_period,
                subscription_id="11111111-1111-1111-1111-111111111111",
                start=date(2026, 9, 1),
                end=date(2026, 9, 13),
            )

    def test_cost_details_fallback_enforces_global_blob_and_byte_limits(self):
        subscription_id = "11111111-1111-1111-1111-111111111111"

        def report_for_period(_subscription_id, start, end, *, byte_count):
            return cost_details_report_payload(
                start.isoformat(),
                end.isoformat(),
                byte_count=byte_count,
                blob_name=start.isoformat(),
            )

        with mock.patch(
            "scripts.azure_startup_qualification_status._cost_details_report",
            side_effect=lambda *args: report_for_period(*args, byte_count=6_000_000),
        ), mock.patch(
            "scripts.azure_startup_qualification_status._download_cost_details_blob"
        ) as download:
            with self.assertRaisesRegex(AzureBillingReadError, "global limit"):
                _cost_details_query(
                    subscription_id, date(2026, 6, 15), date(2026, 9, 13)
                )
        download.assert_not_called()

        with mock.patch(
            "scripts.azure_startup_qualification_status._cost_details_report",
            side_effect=lambda *args: report_for_period(*args, byte_count=100),
        ), mock.patch(
            "scripts.azure_startup_qualification_status._download_cost_details_blob"
        ) as download:
            with self.assertRaisesRegex(AzureBillingReadError, "global limit"):
                _cost_details_query(
                    subscription_id, date(2026, 5, 1), date(2026, 9, 13)
                )
        download.assert_not_called()

    def test_cost_details_csv_accepts_modern_and_legacy_usd_cost_fields(self):
        modern = (
            "Date,ChargeType,MeterCategory,ResourceId,CostInUSD\n"
            "2026-09-12,Usage,Foundry Models,/private/modern,1.25\n"
        )
        legacy = (
            "Date,ChargeType,MeterCategory,ResourceId,"
            "CostInBillingCurrency,BillingCurrencyCode\n"
            "2026-09-12,Usage,Foundry Tools,/private/legacy,1.30,USD\n"
        )
        modern_rows = _cost_details_csv_rows(
            modern, start=date(2026, 9, 1), end=date(2026, 9, 13)
        )
        legacy_rows = _cost_details_csv_rows(
            legacy, start=date(2026, 9, 1), end=date(2026, 9, 13)
        )
        self.assertEqual(modern_rows[0][0], "1.25")
        self.assertEqual(modern_rows[0][2], "Foundry Models")
        self.assertEqual(legacy_rows[0][0], "1.30")
        self.assertEqual(legacy_rows[0][2], "Foundry Tools")

    def test_cost_details_csv_filters_dates_and_non_usage_charges(self):
        content = (
            "Date,ChargeType,MeterCategory,ResourceId,CostInUSD\n"
            "2026-08-31,Usage,Foundry Models,/private/old,4.00\n"
            "2026-09-12,Purchase,Foundry Models,/private/purchase,5.00\n"
        )
        self.assertEqual(
            _cost_details_csv_rows(
                content, start=date(2026, 9, 1), end=date(2026, 9, 13)
            ),
            [],
        )

    def test_cost_details_csv_refuses_non_usd_billing_currency(self):
        content = (
            "Date,ChargeType,MeterCategory,ResourceId,"
            "CostInBillingCurrency,BillingCurrency\n"
            "2026-09-12,Usage,Foundry Models,/private/resource,1.25,EUR\n"
        )
        with self.assertRaisesRegex(AzureBillingReadError, "not in USD"):
            _cost_details_csv_rows(
                content, start=date(2026, 9, 1), end=date(2026, 9, 13)
            )

    def test_cost_details_csv_rows_round_trip_through_cost_parser(self):
        content = (
            "Date,ChargeType,MeterCategory,ResourceId,CostInUSD\n"
            "2026-09-12,Usage,Foundry Models,/private/resource,1.25\n"
        )
        rows = _cost_details_csv_rows(
            content, start=date(2026, 9, 1), end=date(2026, 9, 13)
        )
        payload = {
            "properties": {
                "columns": [
                    {"name": "CostUSD", "type": "Number"},
                    {"name": "UsageDate", "type": "String"},
                    {"name": "ServiceName", "type": "String"},
                    {"name": "ResourceId", "type": "String"},
                    {"name": "Currency", "type": "String"},
                ],
                "rows": rows,
            }
        }
        parsed = cost_rows_from_query(payload)
        self.assertEqual(parsed[0].cost_micro_usd, 1_250_000)
        self.assertEqual(parsed[0].service_name, "Foundry Models")

    def test_cost_details_no_data_period_is_valid(self):
        report = {"status": "NoDataFound"}
        self.assertEqual(
            _validated_cost_details_blobs(
                report,
                subscription_id="11111111-1111-1111-1111-111111111111",
                start=date(2026, 9, 1),
                end=date(2026, 9, 13),
            ),
            (),
        )

    def test_cost_details_query_uses_every_month_even_when_one_has_no_data(self):
        subscription_id = "11111111-1111-1111-1111-111111111111"
        with mock.patch(
            "scripts.azure_startup_qualification_status._cost_details_report",
            return_value=None,
        ) as report:
            payload = _cost_details_query(
                subscription_id, date(2026, 9, 1), date(2026, 9, 13)
            )
        self.assertEqual(cost_rows_from_query(payload), ())
        report.assert_called_once()

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
        self.assertIn('.get("success_marker_eligible")', pipeline)
        self.assertIn("--minimum-fresh-input-tokens", pipeline)
        self.assertIn("--minimum-input-tokens-per-call", pipeline)
        self.assertIn("--minimum-call-interval-seconds", pipeline)
        self.assertIn("qualificationSyntheticContextRecords: '13000'", pipeline)
        self.assertIn("qualificationEvaluationRepeats: '1'", pipeline)
        self.assertIn("qualificationMinimumFreshInputTokens: '2800000'", pipeline)
        self.assertIn("qualificationMinimumInputTokensPerCall: '272001'", pipeline)
        self.assertIn("qualificationMinimumCallIntervalSeconds: '65'", pipeline)
        self.assertNotIn("--only-show-errors 2>/dev/null || true", pipeline)
        self.assertIn("if latest is None:", pipeline)
        self.assertIn("--require-five-qualified-latest-day", pipeline)
        self.assertNotIn("--require-qualified-latest-day \\\n", pipeline)
        self.assertIn("Billing status is unavailable for this run.", pipeline)
        self.assertIn("azure-identity==1.25.3", pipeline)
        self.assertIn("azure-mgmt-costmanagement==5.0.0", pipeline)
        self.assertIn("requests==2.34.2", pipeline)
        self.assertIn("--hard-cap-usd", pipeline)
        self.assertIn("PEERSLATE_AZURE_SPEND_AUTHORIZATION_REF", pipeline)
        self.assertIn("daily product-quality evaluation", pipeline)
        self.assertIn("Automated quality checks passed", pipeline)
        self.assertIn("Stop category", pipeline)
        self.assertIn("Prompts and model output are not retained", pipeline)
        self.assertIn(
            "qualificationContainerRegistryEndpoint: 'https://peerslateacr.azurecr.io'",
            pipeline,
        )
        self.assertNotIn("az acr repository list", pipeline)
        self.assertIn("class RefuseRedirects", pipeline)
        self.assertIn("def redirect_request", pipeline)
        self.assertIn('"scope": "registry:catalog:*"', pipeline)
        self.assertIn("response.geturl() != url", pipeline)
        self.assertIn("response.read(65_537)", pipeline)
        self.assertIn("Registry data-plane catalog access succeeded", pipeline)

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
        self.assertEqual(len(operative), 4, "expected four operative stages")
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
        self.assertEqual(self._qualifying_count(1.000001), 7)

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
