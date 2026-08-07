"""Run the approved Community retention purge operations.

Implements the scheduling half of
docs/initiatives/PS-COMMUNITY-PUBLIC-PILOT-001/APPROVED_RETENTION_AND_DELETION_DECISION.md
The SQL itself lives in PS-COMMUNITY-RETENTION-001 and is proven by the
disposable SQL proof. The operational schedule is outside the Flask process in
``scripts/run_community_maintenance.py``; importing this module never schedules
work. Nothing here deletes live content. Every procedure it calls acts only on
rows the author already removed, on body-free audit rows, or on processed
outbox rows.
"""

from __future__ import annotations

import logging
import os
from threading import Lock
import time

from services.database_service import database_service


LOGGER = logging.getLogger(__name__)

CONTENT_RETENTION_DAYS = 30
AUDIT_RETENTION_DAYS = 90
OUTBOX_PROCESSED_RETENTION_DAYS = 30
OUTBOX_ABANDONED_RETENTION_DAYS = 90


class CommunityRetentionService:
    """Call the approved purge procedures in bounded batches."""

    def __init__(self, database=None):
        self.database = database or database_service

    def purge_content(self, batch_size=200):
        """Purge bodies of removed posts and contributions past the window."""
        row = self.database.first_row(
            "usp_PurgeCommunityContent",
            [
                ("@RetentionDays", CONTENT_RETENTION_DAYS),
                ("@BatchSize", batch_size),
            ],
        )
        return dict(row or {})

    def purge_audit_events(self, batch_size=1000):
        row = self.database.first_row(
            "usp_PurgeCommunityAuditEvents",
            [
                ("@RetentionDays", AUDIT_RETENTION_DAYS),
                ("@BatchSize", batch_size),
            ],
        )
        return dict(row or {})

    def purge_outbox(self, batch_size=1000):
        row = self.database.first_row(
            "usp_PurgeCommunityOutbox",
            [
                ("@ProcessedRetentionDays", OUTBOX_PROCESSED_RETENTION_DAYS),
                ("@AbandonedRetentionDays", OUTBOX_ABANDONED_RETENTION_DAYS),
                ("@BatchSize", batch_size),
            ],
        )
        return dict(row or {})

    def sweep_content_best_effort(self, batch_size=200):
        try:
            return self.purge_content(batch_size=batch_size)
        except Exception as error:
            # Deliberately broad. Catching only DatabaseServiceError let a
            # ValueError from the procedure allowlist escape in the retired
            # request-path scheduler (independent review 2026-08-04, F1).
            # Scheduled housekeeping still fails closed and leaves the row
            # eligible for a later run.
            LOGGER.error(
                "Community content purge failed: error_type=%s.",
                type(error).__name__,
                exc_info=True,
            )
            return {}

    def sweep_daily_best_effort(self, batch_size=1000):
        results = {}
        for label, action in (
            ("audit", lambda: self.purge_audit_events(batch_size=batch_size)),
            ("outbox", lambda: self.purge_outbox(batch_size=batch_size)),
        ):
            try:
                results[label] = action()
            except Exception as error:
                LOGGER.error(
                    "Community %s purge failed: error_type=%s.",
                    label,
                    type(error).__name__,
                    exc_info=True,
                )
                results[label] = {}
        return results


class CommunityRetentionMaintenance:
    """Legacy deterministic cadence helper retained for regression tests.

    The Flask app does not instantiate or call this helper. Production uses
    the bounded out-of-process maintenance command.
    """

    def __init__(
        self,
        service=None,
        content_interval_seconds=3600,
        daily_interval_seconds=86400,
        startup_delay_seconds=0.0,
    ):
        self.service = service or community_retention_service
        self.content_interval_seconds = content_interval_seconds
        self.daily_interval_seconds = daily_interval_seconds
        # The retired request-path implementation used this offset to avoid a
        # restart stampede. It defaults to zero so the compatibility helper
        # remains deterministic under test.
        # Independent review, 2026-08-04, F13.
        self.startup_delay_seconds = startup_delay_seconds
        self._next_content_run = None
        self._next_daily_run = None
        self._lock = Lock()

    @staticmethod
    def process_startup_delay(ceiling_seconds=60.0):
        """A stable per-worker offset, derived from the pid.

        Deliberately not random: a given worker's cadence stays reproducible
        when reading a log, and a restart storm still spreads out.
        """
        return (os.getpid() % 60) / 60.0 * ceiling_seconds

    def maybe_run(self):
        """Run whichever cadences are due.

        This compatibility helper performs synchronous work for callers and
        never queues a concurrent call. It is intentionally not wired to an
        HTTP lifecycle.
        """
        if not self._lock.acquire(blocking=False):
            return {}
        try:
            now = time.monotonic()
            if self._next_content_run is None:
                self._next_content_run = now + self.startup_delay_seconds
                self._next_daily_run = self._next_content_run
            ran = {}
            if now >= self._next_content_run:
                self._next_content_run = now + self.content_interval_seconds
                ran["content"] = self.service.sweep_content_best_effort()
            if now >= self._next_daily_run:
                self._next_daily_run = now + self.daily_interval_seconds
                ran.update(self.service.sweep_daily_best_effort())
            return ran
        finally:
            self._lock.release()


community_retention_service = CommunityRetentionService()
