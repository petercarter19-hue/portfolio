"""PS-COMMUNITY-RETENTION-001 — the approved schedule, as scheduled.

These tests guard the two things most likely to go wrong quietly: calling the
purges with durations that do not match what Pete approved, and letting a
purge failure reach a member's request.
"""

import re
import unittest
from pathlib import Path
from unittest import mock

from services.community_retention_service import (
    AUDIT_RETENTION_DAYS,
    CONTENT_RETENTION_DAYS,
    OUTBOX_ABANDONED_RETENTION_DAYS,
    OUTBOX_PROCESSED_RETENTION_DAYS,
    CommunityRetentionMaintenance,
    CommunityRetentionService,
)
from services.database_service import DatabaseServiceError


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = (
    ROOT
    / "SQL FIles"
    / "Migrations"
    / "proposed"
    / "PS-COMMUNITY-RETENTION-001_retention.sql"
)
ROLLBACK = (
    ROOT
    / "SQL FIles"
    / "Migrations"
    / "proposed"
    / "PS-COMMUNITY-RETENTION-001_retention_rollback.sql"
)
DECISION = (
    ROOT
    / "docs"
    / "initiatives"
    / "PS-COMMUNITY-PUBLIC-PILOT-001"
    / "APPROVED_RETENTION_AND_DELETION_DECISION.md"
)


class RetentionDurationTests(unittest.TestCase):
    def test_durations_match_the_approved_schedule(self):
        self.assertEqual(CONTENT_RETENTION_DAYS, 30)
        self.assertEqual(AUDIT_RETENTION_DAYS, 90)
        self.assertEqual(OUTBOX_PROCESSED_RETENTION_DAYS, 30)
        self.assertEqual(OUTBOX_ABANDONED_RETENTION_DAYS, 90)

    def test_the_decision_document_records_owner_approval(self):
        text = DECISION.read_text(encoding="utf-8")
        self.assertIn("APPROVED by Pete on 2026-08-03", text)
        # The sign-in revision trigger must survive edits to this file.
        self.assertIn("sign-in", text.lower())


class RetentionServiceTests(unittest.TestCase):
    def setUp(self):
        self.database = mock.Mock()
        self.database.first_row.return_value = {}
        self.service = CommunityRetentionService(database=self.database)

    def called_parameters(self):
        return {
            name: value
            for name, value in self.database.first_row.call_args[0][1]
        }

    def test_content_purge_passes_the_approved_window(self):
        self.service.purge_content()
        procedure = self.database.first_row.call_args[0][0]
        self.assertEqual(procedure, "usp_PurgeCommunityContent")
        self.assertEqual(self.called_parameters()["@RetentionDays"], 30)

    def test_audit_purge_passes_the_approved_window(self):
        self.service.purge_audit_events()
        self.assertEqual(
            self.database.first_row.call_args[0][0],
            "usp_PurgeCommunityAuditEvents",
        )
        self.assertEqual(self.called_parameters()["@RetentionDays"], 90)

    def test_outbox_purge_passes_both_approved_windows(self):
        self.service.purge_outbox()
        parameters = self.called_parameters()
        self.assertEqual(parameters["@ProcessedRetentionDays"], 30)
        self.assertEqual(parameters["@AbandonedRetentionDays"], 90)

    def test_a_purge_failure_never_reaches_the_caller(self):
        self.database.first_row.side_effect = DatabaseServiceError("unavailable")
        self.assertEqual(self.service.sweep_content_best_effort(), {})
        results = self.service.sweep_daily_best_effort()
        self.assertEqual(results, {"audit": {}, "outbox": {}})


class RetentionCadenceTests(unittest.TestCase):
    def test_content_runs_hourly_and_daily_work_runs_once_a_day(self):
        service = mock.Mock()
        service.sweep_content_best_effort.return_value = {"posts_purged": 0}
        service.sweep_daily_best_effort.return_value = {"audit": {}, "outbox": {}}
        maintenance = CommunityRetentionMaintenance(service=service)

        clock = [1000.0]
        with mock.patch("time.monotonic", lambda: clock[0]):
            maintenance.maybe_run()
            self.assertEqual(service.sweep_content_best_effort.call_count, 1)
            self.assertEqual(service.sweep_daily_best_effort.call_count, 1)

            # Ten minutes later nothing is due.
            clock[0] += 600
            maintenance.maybe_run()
            self.assertEqual(service.sweep_content_best_effort.call_count, 1)

            # Just past the hour, content runs again but the daily work waits.
            clock[0] += 3100
            maintenance.maybe_run()
            self.assertEqual(service.sweep_content_best_effort.call_count, 2)
            self.assertEqual(service.sweep_daily_best_effort.call_count, 1)

            # Past a day, the daily work runs again.
            clock[0] += 90000
            maintenance.maybe_run()
            self.assertEqual(service.sweep_daily_best_effort.call_count, 2)

    def test_a_busy_worker_is_skipped_rather_than_queued(self):
        service = mock.Mock()
        maintenance = CommunityRetentionMaintenance(service=service)
        maintenance._lock.acquire()
        try:
            self.assertEqual(maintenance.maybe_run(), {})
            service.sweep_content_best_effort.assert_not_called()
        finally:
            maintenance._lock.release()


class RetentionSqlContractTests(unittest.TestCase):
    def test_purge_only_touches_records_the_author_already_removed(self):
        sql = MIGRATION.read_text(encoding="utf-8")
        # Posts and contributions are only eligible once removed and stamped.
        self.assertIn("deleted_at_utc IS NOT NULL", sql)
        self.assertIn("deleted_at_utc <= @Cutoff", sql)
        # A legal hold suspends the purge for named records.
        self.assertIn("legal_hold_reason IS NULL", sql)
        # Media metadata waits for its bytes to be confirmed gone.
        self.assertIn("blob_cleanup_completed_at_utc IS NOT NULL", sql)

    def test_purge_leaves_a_body_free_tombstone_rather_than_deleting_rows(self):
        sql = MIGRATION.read_text(encoding="utf-8")
        self.assertIn("purged_at_utc = @UtcNow", sql)
        # The post row itself must survive so it cannot reappear.
        self.assertNotIn("DELETE TOP (@BatchSize) FROM dbo.community_posts", sql)
        self.assertNotIn(
            "DELETE TOP (@BatchSize) FROM dbo.community_contributions", sql
        )

    def test_jobs_are_bounded_and_concurrency_safe(self):
        sql = MIGRATION.read_text(encoding="utf-8")
        self.assertIn("UPDLOCK, READPAST", sql)
        for guard in ("@BatchSize < 1", "@RetentionDays < 1"):
            with self.subTest(guard=guard):
                self.assertIn(guard, sql)

    def test_rollback_refuses_while_a_record_is_held(self):
        sql = ROLLBACK.read_text(encoding="utf-8")
        self.assertIn("legal hold", sql.lower())
        self.assertIn("THROW 52510", sql)
        self.assertIn("THROW 52511", sql)

    def test_retention_sql_has_no_byte_order_mark(self):
        for path in (MIGRATION, ROLLBACK):
            with self.subTest(path=path.name):
                self.assertNotEqual(path.read_bytes()[:3], b"\xef\xbb\xbf")

    def test_savepoint_names_fit_the_limit(self):
        for path in (MIGRATION, ROLLBACK):
            for name in re.findall(
                r"SAVE\s+TRANSACTION\s+([A-Za-z0-9_@#]+)",
                path.read_text(encoding="utf-8"),
            ):
                with self.subTest(savepoint=name):
                    self.assertLessEqual(len(name), 32)


if __name__ == "__main__":
    unittest.main()
