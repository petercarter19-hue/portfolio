"""Bounded Interview AI telemetry retention purge (out of process).

Runs dbo.usp_PurgeInterviewAIServerCalls under the separately named
Interview maintenance identity and prints a content-free JSON report
(row counts and batch counts only). It deliberately shares nothing with
Community maintenance: its own connection-string variable, its own
pipeline schedule, its own enablement flag.

Refuses to run unless INTERVIEW_TELEMETRY_SQL_CONNECTIONSTRING is set —
the app's own connection string is never used here, because the
application identity holds append-only access by design and must not
hold the delete path.

FAILURE CONTRACT (correction C1). Every stage — dependency import,
connection, cursor creation, DB_NAME verification, purge execution,
result parsing, commit, and close — is bounded. This tool emits EXACTLY
ONE JSON object on stdout, drawn from a closed field set with a closed
reason enum, and nothing on stderr. A raw traceback, exception message,
connection string, server name, URL, or any other unrestricted string
never leaves this process: the caller learns WHICH stage failed, never
what the failure said. Any failure returns a nonzero exit code.
"""

import argparse
import json
import os
import re
import sys

CONNECTION_ENV = "INTERVIEW_TELEMETRY_SQL_CONNECTIONSTRING"
_DATABASE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")

# The closed reason vocabulary. The pipeline's guaranteed fallback report
# uses `purge_did_not_run` from this same enum, so both sides of the
# retention path speak one closed language.
REASONS = (
    "invalid_expected_database",
    "batch_size_out_of_bounds",
    "batch_count_out_of_bounds",
    "connection_not_configured",
    "dependency_unavailable",
    "connection_failed",
    "cursor_failed",
    "database_verification_failed",
    "unexpected_database",
    "purge_failed",
    "result_unreadable",
    "commit_failed",
    "close_failed",
    "purge_did_not_run",
)

RESULTS = ("pass", "refused", "failed")

# The complete set of keys any report may carry.
REPORT_FIELDS = (
    "result",
    "reason",
    "deleted_rows",
    "batches_run",
    "batch_size",
    "more_remaining",
)


def _emit(report):
    """Print exactly one bounded JSON object. Never anything else."""
    bounded = {
        key: value for key, value in report.items() if key in REPORT_FIELDS
    }
    assert bounded["result"] in RESULTS
    if bounded.get("reason") is not None:
        assert bounded["reason"] in REASONS
    print(json.dumps(bounded, sort_keys=True))


def _refuse(reason):
    _emit({"result": "refused", "reason": reason})
    return 2


def _fail(reason, counts=None):
    report = {"result": "failed", "reason": reason}
    if counts:
        report.update(counts)
    _emit(report)
    return 1


def run(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=1000)
    parser.add_argument("--max-batches", type=int, default=10)
    parser.add_argument("--expect-database", required=True)
    arguments = parser.parse_args(argv)

    if not _DATABASE_NAME.fullmatch(arguments.expect_database):
        return _refuse("invalid_expected_database")
    if not 1 <= arguments.batch_size <= 5000:
        return _refuse("batch_size_out_of_bounds")
    if not 1 <= arguments.max_batches <= 1000:
        return _refuse("batch_count_out_of_bounds")

    connection_string = os.environ.get(CONNECTION_ENV)
    if not connection_string:
        return _refuse("connection_not_configured")

    # Dependency import is itself a bounded stage: a missing or broken
    # driver must not produce an import traceback on stderr.
    try:
        from mssql_python import connect
    except BaseException:
        return _fail("dependency_unavailable")

    try:
        connection = connect(connection_string, timeout=30)
    except BaseException:
        return _fail("connection_failed")

    # Fix 2 (Pete-approved corrections): the report is emitted EXACTLY
    # ONCE, after the close attempt, so an operational failure and a
    # close failure occurring together still produce one bounded JSON
    # object. The operational outcome takes precedence: close_failed is
    # reported only when everything before the close succeeded.
    outcome = None  # ("pass"|"refused"|"failed", reason_or_None, counts)
    counts = None
    try:
        try:
            cursor = connection.cursor()
        except BaseException:
            outcome = ("failed", "cursor_failed", None)
        if outcome is None:
            try:
                cursor.execute("SELECT DB_NAME();")
                database_name = cursor.fetchone()[0]
            except BaseException:
                outcome = ("failed", "database_verification_failed", None)
        if outcome is None and database_name != arguments.expect_database:
            # Wrong target: refuse BEFORE the purge procedure is invoked
            # and without committing anything.
            outcome = ("refused", "unexpected_database", None)
        if outcome is None:
            try:
                cursor.execute(
                    "EXEC dbo.usp_PurgeInterviewAIServerCalls "
                    "@BatchSize = ?, @MaxBatches = ?;",
                    (arguments.batch_size, arguments.max_batches),
                )
            except BaseException:
                outcome = ("failed", "purge_failed", None)
        if outcome is None:
            try:
                row = cursor.fetchone()
                counts = {
                    "deleted_rows": int(row[0]),
                    "batches_run": int(row[1]),
                    "batch_size": int(row[2]),
                    "more_remaining": bool(row[3]),
                }
            except BaseException:
                outcome = ("failed", "result_unreadable", None)
        if outcome is None:
            try:
                connection.commit()
            except BaseException:
                outcome = ("failed", "commit_failed", None)
        if outcome is None:
            outcome = ("pass", None, counts)
    finally:
        try:
            connection.close()
        except BaseException:
            # A close failure never doubles the report and never masks an
            # operational failure. It becomes the reported reason only
            # when the run had otherwise fully succeeded (the purge is
            # committed, so its true counts are still reported).
            if outcome is None or outcome[0] == "pass":
                outcome = ("failed", "close_failed", counts)

    result, reason, result_counts = outcome
    if result == "pass":
        _emit({"result": "pass", **result_counts})
        return 0
    if result == "refused":
        return _refuse(reason)
    return _fail(reason, result_counts)


def main(argv=None):
    # Last line of defence: nothing unexpected may reach stderr, and the
    # process must still emit exactly one bounded report.
    try:
        return run(argv)
    except SystemExit:
        raise
    except BaseException:
        return _fail("purge_failed")


if __name__ == "__main__":
    sys.exit(main())
