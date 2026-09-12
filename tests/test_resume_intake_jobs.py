"""Durable-job fence tests for MVP1 increment C.

The fence is what stops a late or replayed worker from resurrecting purged
input or overwriting a newer correction. These are pure-state rules, so they
apply identically to the in-memory ledger and the proposed SQL transaction.
"""

from __future__ import annotations

import unittest

from services.resume_intake_jobs import (
    IntakeJobError,
    JobFence,
    StaleJobError,
    complete,
    enqueue,
    fail,
    fence_is_current,
    invalidate_for_source,
    lease,
    present,
)
from services.resume_intake_repository import empty_intake_snapshot


def snapshot_with_source():
    snapshot = empty_intake_snapshot()
    snapshot["policy_version"] = 1
    snapshot["submissions"]["sub-1"] = {"submission_key": "sub-1", "version": 1, "state": "active"}
    snapshot["sources"]["src-1"] = {"source_key": "src-1", "version": 1, "state": "active"}
    return snapshot


def fence(**overrides):
    base = dict(
        source_key="src-1", source_version=1, submission_key="sub-1",
        submission_version=1, policy_version=1, lifecycle_epoch=0,
    )
    base.update(overrides)
    return JobFence(**base)


class JobFenceTests(unittest.TestCase):
    def test_current_fence_can_be_leased_and_completed(self):
        snapshot = snapshot_with_source()
        job = enqueue(snapshot, fence(), "document_parse")
        leased = lease(snapshot, job["job_key"])
        completed = complete(
            snapshot, job["job_key"], leased["lease_id"], result="unresolved", outcome="extracted"
        )
        self.assertEqual(completed["state"], "completed")
        self.assertEqual(completed["result"], "unresolved")
        self.assertIsNone(completed["lease_id"])

    def test_purged_source_fences_a_queued_job(self):
        snapshot = snapshot_with_source()
        job = enqueue(snapshot, fence(), "voice_transcription")
        snapshot["sources"]["src-1"]["state"] = "purged"
        snapshot["sources"]["src-1"]["version"] = 2
        with self.assertRaises(StaleJobError):
            lease(snapshot, job["job_key"])
        self.assertEqual(snapshot["jobs"][job["job_key"]]["state"], "stale")
        self.assertIsNone(snapshot["jobs"][job["job_key"]]["result"])

    def test_lifecycle_epoch_change_fences_a_leased_job(self):
        snapshot = snapshot_with_source()
        job = enqueue(snapshot, fence(), "text_interpretation")
        leased = lease(snapshot, job["job_key"])
        snapshot["lifecycle_epoch"] = 7  # an older draft was corrected or restricted
        with self.assertRaises(StaleJobError):
            complete(snapshot, job["job_key"], leased["lease_id"], result="saved", outcome="saved")
        self.assertEqual(snapshot["jobs"][job["job_key"]]["state"], "stale")
        self.assertNotEqual(snapshot["jobs"][job["job_key"]]["result"], "saved")

    def test_newer_submission_version_fences_a_job(self):
        snapshot = snapshot_with_source()
        job = enqueue(snapshot, fence(), "document_parse")
        leased = lease(snapshot, job["job_key"])
        snapshot["submissions"]["sub-1"]["version"] = 2
        with self.assertRaises(StaleJobError):
            complete(snapshot, job["job_key"], leased["lease_id"], result="saved", outcome="saved")

    def test_policy_version_change_fences_a_job(self):
        snapshot = snapshot_with_source()
        job = enqueue(snapshot, fence(), "document_parse")
        snapshot["policy_version"] = 2
        self.assertFalse(fence_is_current(snapshot, job["fence"]))

    def test_wrong_lease_cannot_write(self):
        snapshot = snapshot_with_source()
        job = enqueue(snapshot, fence(), "document_parse")
        lease(snapshot, job["job_key"])
        with self.assertRaises(IntakeJobError):
            complete(snapshot, job["job_key"], "not-the-lease", result="saved", outcome="saved")

    def test_failed_job_records_a_content_free_code(self):
        snapshot = snapshot_with_source()
        job = enqueue(snapshot, fence(), "document_parse")
        leased = lease(snapshot, job["job_key"])
        failed = fail(snapshot, job["job_key"], leased["lease_id"], "unsupported_type")
        self.assertEqual(failed["state"], "failed")
        self.assertEqual(failed["outcome"], "unsupported_type")

    def test_invalidate_for_source_only_touches_outstanding_jobs(self):
        snapshot = snapshot_with_source()
        first = enqueue(snapshot, fence(), "document_parse")
        second = enqueue(snapshot, fence(), "voice_transcription")
        leased = lease(snapshot, first["job_key"])
        complete(snapshot, first["job_key"], leased["lease_id"], result="unresolved", outcome="x")
        affected = invalidate_for_source(snapshot, "src-1")
        self.assertEqual(affected, 1)
        self.assertEqual(snapshot["jobs"][first["job_key"]]["state"], "completed")
        self.assertEqual(snapshot["jobs"][second["job_key"]]["state"], "stale")

    def test_unknown_kind_and_result_are_rejected(self):
        snapshot = snapshot_with_source()
        with self.assertRaises(IntakeJobError):
            enqueue(snapshot, fence(), "guess_what")
        job = enqueue(snapshot, fence(), "document_parse")
        leased = lease(snapshot, job["job_key"])
        with self.assertRaises(IntakeJobError):
            complete(snapshot, job["job_key"], leased["lease_id"], result="guessed", outcome=None)

    def test_present_shape_is_receipt_safe(self):
        snapshot = snapshot_with_source()
        job = enqueue(snapshot, fence(), "document_parse")
        view = present(job)
        self.assertEqual(
            set(view), {"job_key", "kind", "state", "result", "outcome", "attempts", "created_at"}
        )


if __name__ == "__main__":
    unittest.main()
