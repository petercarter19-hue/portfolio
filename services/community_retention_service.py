"""Run the approved Community retention purges on the request cadence.

Implements the scheduling half of
docs/initiatives/PS-COMMUNITY-PUBLIC-PILOT-001/APPROVED_RETENTION_AND_DELETION_DECISION.md
The SQL itself lives in PS-COMMUNITY-RETENTION-001 and is proven by the
disposable SQL proof; this module only decides when to call it.

Why the request cadence rather than a timer thread: it is the mechanism the
media cleanup worker already uses, it needs no scheduler infrastructure, and a
missed window simply means the next request purges a slightly older batch.
Nothing here deletes live content. Every procedure it calls acts only on rows
the author already removed, on body-free audit rows, or on processed outbox
rows.
"""

from __future__ import annotations

import logging
import os
from threading import Lock
import time

from services.database_service import DatabaseServiceError, database_service


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
            # Deliberately broad. This runs from an app-wide before_request,
            # so anything that escapes here returns 500 on every route on the
            # site. Catching only DatabaseServiceError let a ValueError from
            # the procedure allowlist through and did exactly that
            # (independent review 2026-08-04, F1). Housekeeping must never be
            # able to take the site down; the next cadence retries and the row
            # stays eligible meanwhile.
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
    """Hourly content purge and daily audit/outbox purge, as approved."""

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
        # Both timers previously started at zero, so every worker swept on its
        # own first request: a restart across N workers meant N simultaneous
        # sweeps, each inline on a real member request. The app supplies a
        # per-process delay to spread them. It defaults to zero here so the
        # cadence stays deterministic under test — the staggering is a
        # deployment concern, not a behaviour of the scheduler.
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

        This runs the sweep inline, inside the request that finds it due. It
        never blocks a *concurrent* request — the non-blocking lock means a
        second request returns immediately rather than queueing — but the
        request that triggers it does wait for it. The docstring previously
        claimed it never blocks a request at all, which was not true
        (independent review, 2026-08-04, F13). The procedures are batched and
        use READPAST, so the cost is bounded; if it ever stops being bounded,
        the fix is a timer-based worker, not a longer docstring.
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
community_retention_maintenance = CommunityRetentionMaintenance(
    community_retention_service,
    startup_delay_seconds=CommunityRetentionMaintenance.process_startup_delay(),
)
