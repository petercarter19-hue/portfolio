"""Regression coverage for the August 4 Community request-path outage."""

import importlib.util
import inspect
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock


os.environ.setdefault("ANTHROPIC_API_KEY", "test-placeholder")

from app import app


ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = ROOT / "scripts" / "run_community_maintenance.py"
ORDINARY_ROUTES = (
    "/",
    "/healthz",
    "/the-slate",
    "/interview-studio",
    "/sitemap.xml",
)


def load_runner():
    spec = importlib.util.spec_from_file_location(
        "community_maintenance_runner",
        RUNNER_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RequestPathIsolationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_testing = app.config["TESTING"]
        cls.original_propagate = app.config.get("PROPAGATE_EXCEPTIONS")
        cls.original_flag = app.config.get(
            "PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED",
            False,
        )
        app.config.update(TESTING=False, PROPAGATE_EXCEPTIONS=False)
        cls.client = app.test_client()

    @classmethod
    def tearDownClass(cls):
        app.config.update(
            TESTING=cls.original_testing,
            PROPAGATE_EXCEPTIONS=cls.original_propagate,
            PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED=cls.original_flag,
        )

    def _assert_no_maintenance(self, community_enabled):
        app.config["PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED"] = community_enabled
        with mock.patch(
            "services.community_media_service.community_media_service.sweep_best_effort"
        ) as media, mock.patch(
            "services.community_retention_service.community_retention_service"
            ".sweep_content_best_effort"
        ) as content, mock.patch(
            "services.community_retention_service.community_retention_service"
            ".sweep_daily_best_effort"
        ) as daily:
            for route in ORDINARY_ROUTES:
                with self.subTest(route=route, community=community_enabled):
                    self.client.get(route)
            media.assert_not_called()
            content.assert_not_called()
            daily.assert_not_called()

    def test_no_request_runs_maintenance_with_community_off(self):
        self._assert_no_maintenance(False)

    def test_no_request_runs_maintenance_with_community_on(self):
        self._assert_no_maintenance(True)

    def test_ordinary_health_routes_still_answer(self):
        app.config["PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED"] = False
        for route in ("/", "/healthz"):
            with self.subTest(route=route):
                self.assertLess(self.client.get(route).status_code, 500)


class ApplicationImportBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / "app.py").read_text(encoding="utf-8")

    def test_app_does_not_import_maintenance_runners(self):
        self.assertNotIn("community_media_maintenance", self.source)
        self.assertNotIn("community_retention_maintenance", self.source)

    def test_before_request_handlers_do_not_call_maybe_run(self):
        for block in self.source.split("@app.before_request")[1:]:
            handler = block.split("\n@", 1)[0]
            self.assertNotIn("maybe_run", handler)

    def test_community_request_modules_do_not_call_media_sweeps(self):
        community_api_source = (ROOT / "community_api.py").read_text(encoding="utf-8")
        self.assertNotIn("sweep_best_effort", community_api_source)

        from services.community_media_service import CommunityMediaService

        for method_name in (
            "reserve_and_upload",
            "reconcile",
            "_reject",
            "_compensate_derivative_completion",
            "remove",
        ):
            with self.subTest(method=method_name):
                method_source = inspect.getsource(
                    getattr(CommunityMediaService, method_name)
                )
                self.assertNotIn("sweep_best_effort", method_source)


class ScheduledRunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runner = load_runner()

    def setUp(self):
        self.target_check = mock.patch(
            "services.database_service.database_service.assert_database_target",
            return_value=True,
        )
        self.storage_check = mock.patch(
            "services.community_media_storage.community_media_storage"
            ".assert_container_access",
            return_value=True,
        )
        self.target_check.start()
        self.storage_check.start()

    def tearDown(self):
        self.storage_check.stop()
        self.target_check.stop()

    def enabled_environment(self):
        return {
            "PEERSLATE_COMMUNITY_MAINTENANCE_ENABLED": "true",
            "AZURE_SQL_CONNECTIONSTRING": self.runner.EXPECTED_SQL_CONNECTION,
            "CAPTURE_MEDIA_BLOB_ACCOUNT_URL": (
                self.runner.EXPECTED_BLOB_ACCOUNT_URL
            ),
            "CAPTURE_MEDIA_BLOB_CONTAINER": self.runner.EXPECTED_BLOB_CONTAINER,
        }

    def test_maintenance_is_independently_default_off(self):
        self.assertFalse(self.runner.enabled({}))
        self.assertFalse(
            self.runner.enabled(
                {"PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED": "true"}
            )
        )
        self.assertTrue(
            self.runner.enabled(
                {"PEERSLATE_COMMUNITY_MAINTENANCE_ENABLED": "true"}
            )
        )

    def test_disabled_and_dry_run_touch_no_services(self):
        self.assertEqual(self.runner.run(environment={})[1]["status"], "disabled")
        self.assertEqual(
            self.runner.run(
                environment={"PEERSLATE_COMMUNITY_MAINTENANCE_ENABLED": "true"},
                dry_run=True,
            )[1]["status"],
            "dry_run",
        )

    def test_single_run_lock_skips_instead_of_queueing(self):
        with tempfile.TemporaryDirectory() as directory:
            lock_path = Path(directory) / "maintenance.lock"
            with self.runner.SingleRun(lock_path) as first:
                self.assertTrue(first)
                with self.runner.SingleRun(lock_path) as second:
                    self.assertFalse(second)
            with self.runner.SingleRun(lock_path) as third:
                self.assertTrue(third)

    def test_lock_failure_fails_the_scheduler_run(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            self.runner.os,
            "open",
            side_effect=OSError("lock unavailable"),
        ):
            code, report = self.runner.run(
                environment=self.enabled_environment(),
                lock_path=Path(directory) / "maintenance.lock",
                expected_database="peerslate-database",
            )
        self.assertEqual(code, self.runner.EXIT_FAILED)
        self.assertEqual(
            report,
            {"status": "failed", "stage": "lock", "error_type": "OSError"},
        )

    def test_limits_fail_closed(self):
        for budget, media_batch in ((0, 20), (301, 20), (120, 0), (120, 21)):
            with self.subTest(budget=budget, media_batch=media_batch):
                with self.assertRaises(ValueError):
                    self.runner.run(
                        budget_seconds=budget,
                        media_batch=media_batch,
                        environment={},
                    )

    def test_enabled_runtime_requires_exact_passwordless_provider_targets(self):
        environment = self.enabled_environment()
        for key, value in (
            ("AZURE_SQL_CONNECTIONSTRING", "Server=wrong;Password=secret"),
            ("CAPTURE_MEDIA_BLOB_ACCOUNT_URL", "https://wrong.example"),
            ("CAPTURE_MEDIA_BLOB_CONTAINER", "wrong-container"),
        ):
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.runner.run(
                    environment={**environment, key: value},
                    expected_database="peerslate-database",
                )

    def test_failure_is_content_free_and_returns_failed_status(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch(
            "services.community_media_service.community_media_service"
            ".sweep",
            side_effect=RuntimeError("member content must not reach evidence"),
        ), mock.patch(
            "services.community_retention_service.community_retention_service"
            ".purge_content",
            return_value={},
        ), mock.patch(
            "services.community_retention_service.community_retention_service"
            ".purge_audit_events",
            return_value={},
        ), mock.patch(
            "services.community_retention_service.community_retention_service"
            ".purge_outbox",
            return_value={},
        ), mock.patch.object(self.runner, "LOGGER") as logger:
            code, report = self.runner.run(
                environment=self.enabled_environment(),
                lock_path=Path(directory) / "maintenance.lock",
                expected_database="peerslate-database",
            )
        self.assertEqual(code, self.runner.EXIT_FAILED)
        self.assertEqual(report["status"], "partial")
        serialized = str(report)
        self.assertNotIn("member content", serialized)
        self.assertNotIn("member content", repr(logger.error.call_args_list))
        self.assertEqual(
            report["sweeps"]["media"]["error_type"],
            "RuntimeError",
        )

    def test_blob_authority_preflight_blocks_every_sweep(self):
        self.storage_check.stop()
        try:
            with tempfile.TemporaryDirectory() as directory, mock.patch(
                "services.community_media_storage.community_media_storage"
                ".assert_container_access",
                side_effect=RuntimeError("provider detail must stay private"),
            ), mock.patch(
                "services.community_media_service.community_media_service.sweep"
            ) as media, mock.patch(
                "services.community_retention_service.community_retention_service"
                ".purge_content"
            ) as content:
                code, report = self.runner.run(
                    environment=self.enabled_environment(),
                    lock_path=Path(directory) / "maintenance.lock",
                    expected_database="peerslate-database",
                )
            self.assertEqual(code, self.runner.EXIT_FAILED)
            self.assertEqual(report["status"], "partial")
            self.assertEqual(
                report["sweeps"]["preflight"]["error_type"], "RuntimeError"
            )
            self.assertNotIn("provider detail", str(report))
            media.assert_not_called()
            content.assert_not_called()
        finally:
            self.storage_check.start()

    def test_hard_deadline_interrupts_a_running_sweep(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch(
            "services.community_media_service.community_media_service.sweep",
            side_effect=lambda **_: self.runner.time.sleep(0.1),
        ), mock.patch.object(self.runner, "MIN_BUDGET_SECONDS", 0.001):
            code, report = self.runner.run(
                environment=self.enabled_environment(),
                lock_path=Path(directory) / "maintenance.lock",
                budget_seconds=0.01,
                expected_database="peerslate-database",
            )
        self.assertEqual(code, self.runner.EXIT_FAILED)
        self.assertEqual(report["status"], "partial")
        self.assertEqual(
            report["sweeps"]["deadline"],
            {"status": "failed", "reason": "budget_spent"},
        )

    def test_success_runs_each_bounded_sweep_once(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch(
            "services.community_media_service.community_media_service"
            ".sweep",
            return_value=0,
        ) as media, mock.patch(
            "services.community_retention_service.community_retention_service"
            ".purge_content",
            return_value={},
        ) as content, mock.patch(
            "services.community_retention_service.community_retention_service"
            ".purge_audit_events",
            return_value={},
        ) as audit, mock.patch(
            "services.community_retention_service.community_retention_service"
            ".purge_outbox",
            return_value={},
        ) as outbox:
            code, report = self.runner.run(
                environment=self.enabled_environment(),
                lock_path=Path(directory) / "maintenance.lock",
                media_batch=7,
                expected_database="peerslate-database",
            )
        self.assertEqual(code, self.runner.EXIT_OK)
        self.assertEqual(report["status"], "ran")
        media.assert_called_once_with(limit=7)
        content.assert_called_once_with()
        audit.assert_called_once_with()
        outbox.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
