"""Bounded scheduled entry point for Community maintenance.

This module is intentionally absent from the Flask application. Community
visibility never starts maintenance, and disabling visibility never stops an
already owed retention action. A scheduler enables this command with the
separate PEERSLATE_COMMUNITY_MAINTENANCE_ENABLED setting.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path
import signal
import sys
import threading
import time


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

LOGGER = logging.getLogger("community_maintenance")

ENABLE_FLAG = "PEERSLATE_COMMUNITY_MAINTENANCE_ENABLED"
LOCK_PATH = Path(os.environ.get("TMPDIR", "/tmp")) / "peerslate-community-maintenance.lock"
TRUE_VALUES = frozenset({"1", "true", "yes", "on"})
EXPECTED_DATABASE = "peerslate-database"
EXPECTED_SQL_CONNECTION = (
    "Server=peerslate.database.windows.net;Database=peerslate-database;"
    "Authentication=ActiveDirectoryDefault;Encrypt=yes;TrustServerCertificate=no"
)
EXPECTED_BLOB_ACCOUNT_URL = "https://peerslatecapturemedia.blob.core.windows.net"
EXPECTED_BLOB_CONTAINER = "peerslate-private-capture-media"

EXIT_OK = 0
EXIT_DISABLED = 0
EXIT_ALREADY_RUNNING = 0
EXIT_FAILED = 1

MIN_BUDGET_SECONDS = 1.0
MAX_BUDGET_SECONDS = 300.0
MIN_MEDIA_BATCH = 1
MAX_MEDIA_BATCH = 20


class MaintenanceBudgetExceeded(TimeoutError):
    """Raised by the process-level wall-clock deadline."""


class WallClockDeadline:
    """Enforce the command budget with the Linux process alarm.

    Azure Pipelines runs this command on Ubuntu in the main thread. Refuse to
    run rather than degrade to a soft deadline on an incompatible host.
    """

    def __init__(self, seconds):
        self.seconds = seconds
        self._previous_handler = None

    @staticmethod
    def _expired(_signum, _frame):
        raise MaintenanceBudgetExceeded("Community maintenance budget expired.")

    def __enter__(self):
        if (
            not hasattr(signal, "SIGALRM")
            or not hasattr(signal, "setitimer")
            or threading.current_thread() is not threading.main_thread()
        ):
            raise RuntimeError("A hard maintenance deadline is unavailable.")
        self._previous_handler = signal.getsignal(signal.SIGALRM)
        signal.signal(signal.SIGALRM, self._expired)
        signal.setitimer(signal.ITIMER_REAL, self.seconds)
        return self

    def __exit__(self, *_):
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, self._previous_handler)
        return False


def enabled(environment=None):
    environment = os.environ if environment is None else environment
    return str(environment.get(ENABLE_FLAG, "")).strip().lower() in TRUE_VALUES


class SingleRun:
    """Acquire a non-blocking process-host lock for one scheduled run."""

    def __init__(self, path=LOCK_PATH):
        self.path = Path(path)
        self._handle = None
        self.error_type = None

    def __enter__(self):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._handle = os.open(
                self.path,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                0o600,
            )
            os.write(self._handle, str(os.getpid()).encode("ascii"))
            return True
        except FileExistsError:
            return False
        except OSError:
            self.error_type = "OSError"
            LOGGER.error(
                "Could not take the Community maintenance lock: error_type=OSError."
            )
            return False

    def __exit__(self, *_):
        if self._handle is not None:
            try:
                os.close(self._handle)
            except OSError:
                pass
            try:
                self.path.unlink()
            except OSError:
                pass
        return False


def _validate_limits(budget_seconds, media_batch):
    if not MIN_BUDGET_SECONDS <= budget_seconds <= MAX_BUDGET_SECONDS:
        raise ValueError("Maintenance wall-clock budget is outside the safe range.")
    if not MIN_MEDIA_BATCH <= media_batch <= MAX_MEDIA_BATCH:
        raise ValueError("Maintenance media batch is outside the safe range.")


def _validate_runtime_contract(environment, expected_database):
    if (
        expected_database != EXPECTED_DATABASE
        or environment.get("AZURE_SQL_CONNECTIONSTRING") != EXPECTED_SQL_CONNECTION
        or environment.get("CAPTURE_MEDIA_BLOB_ACCOUNT_URL")
        != EXPECTED_BLOB_ACCOUNT_URL
        or environment.get("CAPTURE_MEDIA_BLOB_CONTAINER") != EXPECTED_BLOB_CONTAINER
    ):
        raise ValueError("Maintenance provider target is not approved.")


def _run_sweep(label, action, results):
    """Run one sweep and retain only content-free operational evidence."""

    started = time.monotonic()
    try:
        outcome = action()
        results[label] = {
            "status": "ok",
            "result_type": type(outcome).__name__,
        }
        return True
    except MaintenanceBudgetExceeded:
        results[label] = {"status": "failed", "reason": "budget_spent"}
        raise
    except Exception as error:
        LOGGER.error(
            "Community %s maintenance failed: error_type=%s. The next run retries.",
            label,
            type(error).__name__,
        )
        results[label] = {
            "status": "failed",
            "error_type": type(error).__name__,
        }
        return False
    finally:
        if label in results:
            results[label]["duration_ms"] = round(
                (time.monotonic() - started) * 1000
            )


def run(
    *,
    budget_seconds=120.0,
    media_batch=20,
    dry_run=False,
    environment=None,
    lock_path=None,
    expected_database=None,
):
    """Run bounded maintenance and return ``(exit_code, content_free_report)``."""

    _validate_limits(budget_seconds, media_batch)
    runtime_environment = os.environ if environment is None else environment
    if not enabled(runtime_environment):
        return EXIT_DISABLED, {"status": "disabled"}

    if dry_run:
        return EXIT_OK, {
            "status": "dry_run",
            "would_run": ["media", "content", "audit", "outbox"],
        }

    if not expected_database:
        raise ValueError("Maintenance requires an exact expected database.")
    _validate_runtime_contract(runtime_environment, expected_database)

    lock = SingleRun(lock_path or LOCK_PATH)
    with lock as acquired:
        if not acquired:
            if lock.error_type:
                return EXIT_FAILED, {
                    "status": "failed",
                    "stage": "lock",
                    "error_type": lock.error_type,
                }
            return EXIT_ALREADY_RUNNING, {"status": "already_running"}

        # Delayed imports keep inspection and disabled runs dependency-free.
        from services.database_service import database_service
        from services.community_media_service import community_media_service
        from services.community_media_storage import community_media_storage
        from services.community_retention_service import community_retention_service

        results = {}
        ok = True
        try:
            with WallClockDeadline(budget_seconds):
                database_service.assert_database_target(expected_database)
                community_media_storage.assert_container_access()
                for label, action in (
                    ("media", lambda: community_media_service.sweep(limit=media_batch)),
                    ("content", community_retention_service.purge_content),
                    ("audit", community_retention_service.purge_audit_events),
                    ("outbox", community_retention_service.purge_outbox),
                ):
                    ok = _run_sweep(label, action, results) and ok
        except MaintenanceBudgetExceeded:
            results["deadline"] = {"status": "failed", "reason": "budget_spent"}
            ok = False
        except Exception as error:
            LOGGER.error(
                "Community maintenance preflight failed: error_type=%s.",
                type(error).__name__,
            )
            results["preflight"] = {
                "status": "failed",
                "error_type": type(error).__name__,
            }
            ok = False

        return (
            EXIT_OK if ok else EXIT_FAILED,
            {"status": "ran" if ok else "partial", "sweeps": results},
        )


def main(argv=None):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--budget-seconds", type=float, default=120.0)
    parser.add_argument("--media-batch", type=int, default=20)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--expect-database", required=True)
    arguments = parser.parse_args(argv)
    try:
        exit_code, report = run(
            budget_seconds=arguments.budget_seconds,
            media_batch=arguments.media_batch,
            dry_run=arguments.dry_run,
            expected_database=arguments.expect_database,
        )
    except ValueError as error:
        LOGGER.error("Community maintenance refused unsafe limits: %s", error)
        return EXIT_FAILED
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
