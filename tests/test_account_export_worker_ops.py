"""Offline contracts for PS-SETTINGS-ACCOUNT-EXPORT-WORKER-OPS-001: the
retention maintenance mode of scripts/run_account_export_worker.py.

The gap this package closes (C3_ACCOUNT_EXPORT_EXPERIENCE.md, "Expiry is
not deletion"): the owner-approved seven-day ready window was enforced in
the ledger but never on disk -- nothing called
dbo.usp_ExpireAccountExportJobs and nothing ever called
AccountExportStorageService.cleanup_final, so an expired member archive
would sit in the private container forever. These tests pin the new
run_maintenance path: expire first, then delete the physical objects for
exactly the past-ready pending jobs, then -- and only then -- mark each
job cleaned.

The sacred ordering rule, tested from both directions:

1. Never delete an object for a job that is still downloadable. Only
   'expired' (and the C1-cleanup-contract-covered 'failed') jobs with
   cleanup_state = 'pending' are swept; a 'ready' job never has
   cleanup_final called, even if one somehow appears in the sweep's own
   result set (defense in depth beyond the WHERE clause).
2. Never mark a job cleaned before its delete succeeded. A failing
   delete leaves the job unmarked ('pending', retried next run), the run
   continues to the next job, and the whole run fails loudly at the end.

No network, database, or provider call anywhere in this file. Every DB
interaction is driven through the same shared-queue fake cursor and
connection shape tests/test_account_export_integration.py uses (a single
maintenance run issues several statements in sequence over ONE
connection), and storage through a small fake double modeled on that
file's RunOnceOrchestrationTests.FakeStorage. Every synthetic value is
an obvious, entropy-dead placeholder, never a realistic identifier.
"""

import json
import logging
import unittest
from pathlib import Path

import scripts.run_account_export_worker as worker_module
from scripts.run_account_export_worker import (
    MAX_ATTEMPTS,
    content_free_log_fields,
    expire_ready_jobs,
    fetch_cleanup_pending_jobs,
    mark_job_cleaned,
    run_maintenance,
)


EXPIRED_JOB_KEY = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
SECOND_EXPIRED_JOB_KEY = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
READY_JOB_KEY = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
FAILED_JOB_KEY = "dddddddd-dddd-4ddd-8ddd-dddddddddddd"


# ---------------------------------------------------------------------
# The same shared-queue fake connection/cursor shape as
# tests/test_account_export_integration.py's SharedPlanCursor /
# SharedPlanConnection: one plan queue that drains across every cursor a
# connection hands out, because one maintenance run issues its expire,
# sweep-select, and per-job cleanup statements in sequence over one
# shared connection. Redeclared here (not imported) so this file stays
# runnable no matter how the suite maps test-module names, exactly as
# that file itself redeclared its fake rather than importing
# tests/test_settings_export_core_readers.py's.
# ---------------------------------------------------------------------


class SharedPlanCursor:
    def __init__(self, plan):
        self.plan = plan  # shared reference -- NOT list(plan)
        self.description = None
        self._rows = []
        self.executed = []

    def execute(self, sql, params=None):
        self.executed.append((sql, params))
        step = self.plan.pop(0)
        kind = step[0]
        if kind == "content":
            self.description = step[1]
            self._rows = step[2]
        elif kind == "none":
            self.description = None
            self._rows = []
        elif kind == "raise":
            raise step[1]
        else:
            raise AssertionError("unknown fake step %r" % (kind,))

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return list(self._rows)


class SharedPlanConnection:
    def __init__(self, plan):
        self._plan = plan
        self.cursor_calls = 0
        self.cursors = []

    def cursor(self):
        self.cursor_calls += 1
        cursor = SharedPlanCursor(self._plan)
        self.cursors.append(cursor)
        return cursor

    def executed(self):
        statements = []
        for cursor in self.cursors:
            statements.extend(cursor.executed)
        return statements


class FakeStorage:
    """Modeled on tests/test_account_export_integration.py's
    RunOnceOrchestrationTests.FakeStorage, with the two cleanup calls
    this package exercises recorded separately and independently
    failable per job key."""

    def __init__(self):
        self.cleanup_final_calls = []
        self.cleanup_staging_calls = []
        self.cleanup_final_errors = {}
        self.cleanup_staging_errors = {}

    def cleanup_final(self, job_key):
        error = self.cleanup_final_errors.get(job_key)
        if error is not None:
            raise error
        self.cleanup_final_calls.append(job_key)

    def cleanup_staging(self, job_key, attempt):
        error = self.cleanup_staging_errors.get(job_key)
        if error is not None:
            raise error
        self.cleanup_staging_calls.append((job_key, attempt))


def expire_step(expired_count):
    return ("content", [("expired_count",)], [(expired_count,)])


def sweep_step(rows):
    """rows: list of (job_key, state, attempt_count) tuples."""

    return (
        "content",
        [("job_key",), ("state",), ("attempt_count",)],
        list(rows),
    )


def cleanup_step(job_key, cleanup_state="cleaned"):
    return ("content", [("job_key",), ("cleanup_state",)], [(job_key, cleanup_state)])


class ExpireExecutionTests(unittest.TestCase):
    """The expire procedure actually runs, as a bare EXEC, before any
    sweep -- the half of the gap where nothing ever called
    usp_ExpireAccountExportJobs at all."""

    def test_expire_is_a_bare_exec_with_no_parameters(self):
        plan = [expire_step(3), sweep_step([])]
        connection = SharedPlanConnection(plan)

        result = run_maintenance(connection, FakeStorage())

        statements = connection.executed()
        sql, params = statements[0]
        self.assertIn("EXEC dbo.usp_ExpireAccountExportJobs", sql)
        # Bare EXEC: the procedure's own default @BatchSize governs; the
        # worker passes nothing.
        self.assertIsNone(params)
        self.assertEqual(result["expired_count"], 3)
        self.assertEqual(result["outcome"], "completed")

    def test_expire_runs_before_the_sweep_select(self):
        plan = [expire_step(0), sweep_step([])]
        connection = SharedPlanConnection(plan)

        run_maintenance(connection, FakeStorage())

        statements = [sql for sql, _ in connection.executed()]
        self.assertEqual(len(statements), 2)
        self.assertIn("usp_ExpireAccountExportJobs", statements[0])
        self.assertIn("FROM dbo.account_export_jobs", statements[1])

    def test_a_missing_expire_result_set_fails_loudly(self):
        # SET NOCOUNT ON means the procedure's one SELECT is the only
        # result set; if it is somehow absent the count cannot be
        # trusted and the run must not continue as if zero expired.
        plan = [("none",)]
        connection = SharedPlanConnection(plan)

        with self.assertRaises(RuntimeError):
            run_maintenance(connection, FakeStorage())

    def test_expire_ready_jobs_returns_the_procedures_own_count(self):
        plan = [expire_step(41)]
        cursor = SharedPlanCursor(plan)
        self.assertEqual(expire_ready_jobs(cursor), 41)


class SweepScopeTests(unittest.TestCase):
    """Only past-ready pending jobs are swept: the WHERE clause names
    exactly the states usp_CleanupAccountExportJob's own contract
    covers, and a runtime guard refuses anything else even if it
    appears in the result set."""

    def test_a_malformed_ledger_row_is_skipped_not_the_whole_sweep(self):
        # Independent-review finding F4: one malformed job_key aborts
        # only its own row (fail-safe -- nothing was deleted for it),
        # never the remaining jobs' overdue deletions; the run still
        # fails loudly at the end.
        storage = FakeStorage()
        plan = [
            expire_step(0),
            sweep_step(
                [
                    ("NOT-A-UUID", "expired", 1),
                    (EXPIRED_JOB_KEY, "expired", 1),
                ]
            ),
            cleanup_step(EXPIRED_JOB_KEY),
        ]
        connection = SharedPlanConnection(plan)

        result = run_maintenance(connection, storage)

        self.assertEqual(storage.cleanup_final_calls, [EXPIRED_JOB_KEY])
        mark_statements = [
            params
            for sql, params in connection.executed()
            if "usp_CleanupAccountExportJob" in sql
        ]
        self.assertEqual(mark_statements, [(EXPIRED_JOB_KEY,)])
        self.assertEqual(result["cleaned_count"], 1)
        self.assertEqual(result["cleanup_failed_count"], 1)
        self.assertEqual(result["outcome"], "failed")

    def test_sweep_select_names_only_pending_expired_and_failed(self):
        plan = [expire_step(0), sweep_step([])]
        connection = SharedPlanConnection(plan)

        run_maintenance(connection, FakeStorage())

        sweep_sql = connection.executed()[1][0]
        self.assertIn("cleanup_state = N'pending'", sweep_sql)
        self.assertIn("state IN (N'expired', N'failed')", sweep_sql)
        self.assertNotIn("N'ready'", sweep_sql)
        # Job ledger metadata only -- never member content columns.
        for forbidden in ("final_artifact_reference", "owner_user_id", "user_key"):
            self.assertNotIn(forbidden, sweep_sql)

    def test_an_expired_pending_job_is_cleaned(self):
        storage = FakeStorage()
        plan = [
            expire_step(1),
            sweep_step([(EXPIRED_JOB_KEY, "expired", 1)]),
            cleanup_step(EXPIRED_JOB_KEY),
        ]
        connection = SharedPlanConnection(plan)

        result = run_maintenance(connection, storage)

        self.assertEqual(storage.cleanup_final_calls, [EXPIRED_JOB_KEY])
        self.assertEqual(result["cleaned_count"], 1)
        self.assertEqual(result["cleanup_failed_count"], 0)
        self.assertEqual(result["outcome"], "completed")

    def test_a_still_ready_job_never_has_cleanup_final_called(self):
        # Defense in depth for the sacred rule. The WHERE clause already
        # excludes 'ready', but even a fake (or a future regression)
        # that hands back a ready row must not cost a member their
        # still-downloadable archive: the runtime guard refuses the row
        # without any storage call and fails the run loudly.
        storage = FakeStorage()
        plan = [
            expire_step(0),
            sweep_step([(READY_JOB_KEY, "ready", 1)]),
            # Deliberately no cleanup_step: the guard must refuse before
            # issuing any further statement for this job.
        ]
        connection = SharedPlanConnection(plan)

        result = run_maintenance(connection, storage)

        self.assertEqual(storage.cleanup_final_calls, [])
        self.assertEqual(storage.cleanup_staging_calls, [])
        # No usp_CleanupAccountExportJob statement was ever issued.
        cleanup_statements = [
            sql for sql, _ in connection.executed() if "usp_CleanupAccountExportJob" in sql
        ]
        self.assertEqual(cleanup_statements, [])
        self.assertEqual(result["cleaned_count"], 0)
        self.assertEqual(result["cleanup_failed_count"], 1)
        self.assertEqual(result["outcome"], "failed")

    def test_a_failed_pending_job_sweeps_the_final_object_and_staging(self):
        # Independent-review finding F1: CK_account_export_jobs_ready_
        # artifact forces a failed job's LEDGER columns to NULL, but the
        # physical final object can survive a post-promote failure --
        # promote() commits the final blob BEFORE hash verification and
        # the completion call, so a failure after that point orphans a
        # committed final object while retries die on storage_conflict
        # and the job terminates 'failed' with no reference.
        # cleanup_final is therefore called for EVERY swept job: for
        # most failed jobs it just proves absence (idempotent); for a
        # post-promote orphan it deletes the member's archive. A failed
        # job is never downloadable, so the sacred rule is untouched.
        # A terminal 'failed' job has exhausted all MAX_ATTEMPTS
        # attempts, so every staging ordinal 1..3 is swept too.
        storage = FakeStorage()
        plan = [
            expire_step(0),
            sweep_step([(FAILED_JOB_KEY, "failed", 3)]),
            cleanup_step(FAILED_JOB_KEY),
        ]
        connection = SharedPlanConnection(plan)

        result = run_maintenance(connection, storage)

        self.assertEqual(storage.cleanup_final_calls, [FAILED_JOB_KEY])
        self.assertEqual(
            storage.cleanup_staging_calls,
            [(FAILED_JOB_KEY, attempt) for attempt in range(1, MAX_ATTEMPTS + 1)],
        )
        self.assertEqual(result["cleaned_count"], 1)
        self.assertEqual(result["outcome"], "completed")

    def test_an_expired_job_sweeps_final_and_staging_up_to_its_own_attempt_count(self):
        # An expired job's earlier failed attempts may have left staging
        # objects whose best-effort in-run cleanup also failed; the
        # maintenance sweep removes them alongside the final object.
        # Staging can only exist for attempts that actually ran, so the
        # sweep is bounded by the job's own attempt_count (2 here) --
        # never a blind 1..MAX_ATTEMPTS.
        storage = FakeStorage()
        plan = [
            expire_step(0),
            sweep_step([(EXPIRED_JOB_KEY, "expired", 2)]),
            cleanup_step(EXPIRED_JOB_KEY),
        ]
        connection = SharedPlanConnection(plan)

        run_maintenance(connection, storage)

        self.assertEqual(storage.cleanup_final_calls, [EXPIRED_JOB_KEY])
        self.assertEqual(
            storage.cleanup_staging_calls,
            [(EXPIRED_JOB_KEY, 1), (EXPIRED_JOB_KEY, 2)],
        )


class DeleteThenMarkOrderingTests(unittest.TestCase):
    """Never mark cleaned before the delete succeeded, and never let one
    failing job silently end the sweep or silently pass the run."""

    def test_the_mark_statement_follows_the_delete_for_each_job(self):
        storage = FakeStorage()
        plan = [
            expire_step(0),
            sweep_step([(EXPIRED_JOB_KEY, "expired", 1)]),
            cleanup_step(EXPIRED_JOB_KEY),
        ]
        connection = SharedPlanConnection(plan)

        original_cleanup_final = storage.cleanup_final
        deletes_before_mark = []

        def recording_cleanup_final(job_key):
            # At delete time, no usp_CleanupAccountExportJob statement
            # may exist yet for this job.
            issued = [
                sql for sql, _ in connection.executed() if "usp_CleanupAccountExportJob" in sql
            ]
            deletes_before_mark.append((job_key, list(issued)))
            original_cleanup_final(job_key)

        storage.cleanup_final = recording_cleanup_final

        run_maintenance(connection, storage)

        self.assertEqual(deletes_before_mark, [(EXPIRED_JOB_KEY, [])])
        mark_statements = [
            (sql, params)
            for sql, params in connection.executed()
            if "usp_CleanupAccountExportJob" in sql
        ]
        self.assertEqual(len(mark_statements), 1)
        self.assertEqual(mark_statements[0][1], (EXPIRED_JOB_KEY,))

    def test_a_failing_delete_leaves_the_job_unmarked_and_the_run_continues_then_fails_loudly(self):
        storage = FakeStorage()
        storage.cleanup_final_errors[EXPIRED_JOB_KEY] = RuntimeError(
            "synthetic storage delete failure"
        )
        plan = [
            expire_step(0),
            sweep_step(
                [
                    (EXPIRED_JOB_KEY, "expired", 1),
                    (SECOND_EXPIRED_JOB_KEY, "expired", 1),
                ]
            ),
            # Exactly ONE cleanup step: only the second job may be
            # marked. If the first job were marked despite its failed
            # delete, the plan would drain early and the second job's
            # own mark would crash on an exhausted queue.
            cleanup_step(SECOND_EXPIRED_JOB_KEY),
        ]
        connection = SharedPlanConnection(plan)

        result = run_maintenance(connection, storage)

        mark_statements = [
            params
            for sql, params in connection.executed()
            if "usp_CleanupAccountExportJob" in sql
        ]
        self.assertEqual(mark_statements, [(SECOND_EXPIRED_JOB_KEY,)])
        self.assertEqual(storage.cleanup_final_calls, [SECOND_EXPIRED_JOB_KEY])
        self.assertEqual(result["cleaned_count"], 1)
        self.assertEqual(result["cleanup_failed_count"], 1)
        # Loud at the end: the run's own outcome is 'failed', which
        # main() maps to a nonzero exit code.
        self.assertEqual(result["outcome"], "failed")

    def test_an_unconfirmed_mark_counts_as_a_failure_not_a_clean(self):
        # Independent-review finding F3: the defensive marked_state
        # check must actually gate the outcome. A procedure response
        # other than 'cleaned' (here 'not_required' -- the idempotent
        # no-op branch for a row that was never pending) means the
        # ledger does not show the cleanup this run believes it
        # performed: counted as a failure, job left for the next run,
        # loud outcome.
        storage = FakeStorage()
        plan = [
            expire_step(0),
            sweep_step([(EXPIRED_JOB_KEY, "expired", 1)]),
            cleanup_step(EXPIRED_JOB_KEY, cleanup_state="not_required"),
        ]
        connection = SharedPlanConnection(plan)

        result = run_maintenance(connection, storage)

        self.assertEqual(result["cleaned_count"], 0)
        self.assertEqual(result["cleanup_failed_count"], 1)
        self.assertEqual(result["outcome"], "failed")

    def test_a_failing_mark_after_a_successful_delete_counts_as_a_failure(self):
        # The object is gone but the ledger still says pending: truthful
        # -- the next run's delete is an idempotent no-op and the mark
        # is retried. The run must still fail loudly rather than report
        # a clean pass.
        storage = FakeStorage()
        plan = [
            expire_step(0),
            sweep_step([(EXPIRED_JOB_KEY, "expired", 1)]),
            ("raise", RuntimeError("synthetic ledger failure")),
        ]
        connection = SharedPlanConnection(plan)

        result = run_maintenance(connection, storage)

        self.assertEqual(storage.cleanup_final_calls, [EXPIRED_JOB_KEY])
        self.assertEqual(result["cleaned_count"], 0)
        self.assertEqual(result["cleanup_failed_count"], 1)
        self.assertEqual(result["outcome"], "failed")


class IdempotentRerunTests(unittest.TestCase):
    """A re-run after a fully clean sweep touches nothing: already
    cleaned jobs never reappear (the sweep selects only 'pending'), no
    storage call is made, and the run completes."""

    def test_a_rerun_with_nothing_pending_is_a_clean_no_op(self):
        storage = FakeStorage()
        plan = [expire_step(0), sweep_step([])]
        connection = SharedPlanConnection(plan)

        result = run_maintenance(connection, storage)

        self.assertEqual(storage.cleanup_final_calls, [])
        self.assertEqual(storage.cleanup_staging_calls, [])
        cleanup_statements = [
            sql for sql, _ in connection.executed() if "usp_CleanupAccountExportJob" in sql
        ]
        self.assertEqual(cleanup_statements, [])
        self.assertEqual(
            result,
            {
                "outcome": "completed",
                "expired_count": 0,
                "cleaned_count": 0,
                "cleanup_failed_count": 0,
            },
        )

    def test_a_concurrently_cleaned_job_still_counts_as_cleaned(self):
        # usp_CleanupAccountExportJob's own idempotent branch: a job
        # another maintenance run cleaned between this run's select and
        # its mark returns 'cleaned' without re-transitioning. The
        # storage delete this run already performed was itself an
        # idempotent no-op, so nothing was double-deleted.
        storage = FakeStorage()
        plan = [
            expire_step(0),
            sweep_step([(EXPIRED_JOB_KEY, "expired", 1)]),
            cleanup_step(EXPIRED_JOB_KEY, cleanup_state="cleaned"),
        ]
        connection = SharedPlanConnection(plan)

        result = run_maintenance(connection, storage)

        self.assertEqual(result["cleaned_count"], 1)
        self.assertEqual(result["outcome"], "completed")

    def test_mark_job_cleaned_refuses_a_missing_result_set(self):
        plan = [("none",)]
        cursor = SharedPlanCursor(plan)
        with self.assertRaises(RuntimeError):
            mark_job_cleaned(cursor, EXPIRED_JOB_KEY)


class ContentFreeLoggingTests(unittest.TestCase):
    """Maintenance logging stays inside the deliberately widened
    counts-and-states-only allowlist: the three new count fields pass,
    and nothing content-bearing can ever reach a log line."""

    def test_the_new_count_fields_are_allowlisted(self):
        fields = content_free_log_fields(
            stage="maintenance_finished",
            expired_count=3,
            cleaned_count=2,
            cleanup_failed_count=1,
        )
        self.assertEqual(
            fields,
            {
                "stage": "maintenance_finished",
                "expired_count": 3,
                "cleaned_count": 2,
                "cleanup_failed_count": 1,
            },
        )

    def test_content_bearing_fields_are_dropped_not_logged(self):
        fields = content_free_log_fields(
            stage="maintenance_cleaned",
            job_key=EXPIRED_JOB_KEY,
            state="expired",
            omission_reason="SYNTHETIC-REASON-MUST-NEVER-LOG",
            final_artifact_reference="export/v1/final/SYNTHETIC.zip",
            domain_code="SYNTHETIC-DOMAIN-MUST-NEVER-LOG",
            owner_user_id=4001,
        )
        self.assertEqual(
            fields,
            {
                "stage": "maintenance_cleaned",
                "job_key": EXPIRED_JOB_KEY,
                "state": "expired",
            },
        )

    def test_maintenance_log_lines_carry_only_allowlisted_json_fields(self):
        storage = FakeStorage()
        storage.cleanup_final_errors[SECOND_EXPIRED_JOB_KEY] = RuntimeError(
            "synthetic storage delete failure"
        )
        plan = [
            expire_step(2),
            sweep_step(
                [
                    (EXPIRED_JOB_KEY, "expired", 1),
                    (SECOND_EXPIRED_JOB_KEY, "expired", 1),
                ]
            ),
            cleanup_step(EXPIRED_JOB_KEY),
        ]
        connection = SharedPlanConnection(plan)

        with self.assertLogs("account_export_worker", level=logging.INFO) as captured:
            run_maintenance(connection, storage)

        allowed = worker_module._LOG_FIELD_NAMES
        for record in captured.records:
            payload = json.loads(record.getMessage())
            self.assertTrue(set(payload) <= allowed, payload)


class EntrypointWiringTests(unittest.TestCase):
    """The maintenance mode is reachable from the existing entrypoint
    and wired to the real storage adapter -- source-text pins in the
    same style as tests/test_account_export_integration.py's own
    FixtureTripwireRetiredTests."""

    def setUp(self):
        self.source = Path(worker_module.__file__).read_text(encoding="utf-8")

    def test_main_exposes_a_maintenance_flag(self):
        self.assertIn('"--maintenance"', self.source)

    def test_main_wires_run_maintenance_to_the_real_storage_adapter(self):
        self.assertIn(
            "run_maintenance(connection, account_export_storage_service)",
            self.source,
        )

    def test_functions_exist_with_the_agreed_signatures(self):
        self.assertTrue(callable(run_maintenance))
        self.assertTrue(callable(expire_ready_jobs))
        self.assertTrue(callable(fetch_cleanup_pending_jobs))
        self.assertTrue(callable(mark_job_cleaned))


if __name__ == "__main__":
    unittest.main()
