#!/usr/bin/env python3
"""Fail closed before deploying Community-aware runtime source.

The Community recovery merges before its additive migration can use the
main-only governed schema path. Automatic main deployment must therefore stop
until that exact migration and its required procedure are present in the exact
production database.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from db import fetch_all_result_sets, get_connection
from services.database_service import DatabaseService, DatabaseServiceError


DATABASE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")
REQUIRED_MIGRATION = "PS-COMMUNITY-REVIVAL-001"
REQUIRED_PROCEDURE = "usp_ClaimPublicCommunityMediaCleanupForOwner"


def verify(expected_database):
    if not DATABASE_NAME.fullmatch(str(expected_database or "")):
        raise ValueError("Invalid expected database name.")
    try:
        with get_connection() as connection:
            cursor = DatabaseService._cursor(connection)
            cursor.execute(
                """
                SELECT DB_NAME() AS database_name,
                       CASE WHEN EXISTS
                       (
                           SELECT 1 FROM dbo.schema_migrations
                           WHERE migration_id = ?
                       ) THEN 1 ELSE 0 END AS migration_applied,
                       CASE WHEN OBJECT_ID(N'dbo.' + ?, N'P') IS NOT NULL
                            THEN 1 ELSE 0 END AS procedure_present;
                """,
                (REQUIRED_MIGRATION, REQUIRED_PROCEDURE),
            )
            result_sets = fetch_all_result_sets(cursor)
    except Exception as error:
        raise DatabaseServiceError("Community release schema check failed.") from error
    row = result_sets[0][0] if result_sets and result_sets[0] else {}
    if (
        row.get("database_name") != expected_database
        or int(row.get("migration_applied") or 0) != 1
        or int(row.get("procedure_present") or 0) != 1
    ):
        raise DatabaseServiceError("Community release schema check failed.")
    return {
        "status": "ready",
        "migration": REQUIRED_MIGRATION,
        "procedure": REQUIRED_PROCEDURE,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expect-database", required=True)
    args = parser.parse_args(argv)
    try:
        report = verify(args.expect_database)
    except Exception as error:
        print(
            json.dumps(
                {"status": "blocked", "error_type": type(error).__name__},
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 1
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
