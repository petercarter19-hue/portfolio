"""Plan or apply PeerSlate SQL migrations using the configured secure connection."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import time

from dotenv import load_dotenv
from mssql_python import connect

ROOT = Path(__file__).resolve().parents[1]
MIGRATION_DIR = ROOT / "SQL FIles" / "Migrations"
VERIFY_PATH = ROOT / "SQL FIles" / "Verification" / "peerslate_platform_foundation_verify.sql"

EXPECTED_MIGRATIONS = {f"PS-PLAT-{number:03d}" for number in range(1, 8)}
EXPECTED_TABLES = {
    "schema_migrations",
    "audit_events",
    "member_profiles",
    "slate_entities",
    "slate_entity_relations",
    "entity_access_grants",
    "entity_publication_versions",
    "file_assets",
    "evidence_items",
    "evidence_links",
    "ai_proposals",
    "ai_proposal_changes",
    "connection_preferences",
    "connection_requests",
    "member_connections",
    "user_blocks",
    "user_reports",
    "notifications",
    "notification_preferences",
    "user_consents",
    "career_chapters",
    "career_experiences",
    "career_education",
    "career_credentials",
    "career_projects",
    "career_achievements",
    "career_skills",
    "career_skill_links",
    "career_timeline_events",
    "voice_drafts",
    "content_approval_events",
}
EXPECTED_PROGRAMMABLE_OBJECTS = {
    "usp_AppendAuditEvent",
    "usp_GetOwnerLivingResume",
    "usp_GetPublicLivingResumeBySlug",
    "trg_audit_events_immutable",
    "trg_content_approval_events_immutable",
}


def normalize_connection_string(connection_string: str) -> str:
    connection_string = connection_string.replace(
        ".database.windows.net.database.windows.net",
        ".database.windows.net",
    )
    return re.sub(
        r"(?i)(^|;)\s*connection timeout\s*=\s*[^;]*(?=;|$)",
        r"\1",
        connection_string,
    )


def get_connection():
    # Load the local secret only when an apply or verification connection is
    # actually requested. Plan-only mode never reads connection settings.
    load_dotenv(ROOT / ".env")
    connection_string = os.getenv("AZURE_SQL_CONNECTIONSTRING")
    if not connection_string:
        raise RuntimeError("AZURE_SQL_CONNECTIONSTRING is not configured.")
    connection_string = normalize_connection_string(connection_string)
    last_error = None
    for attempt in range(1, 4):
        try:
            connection = connect(connection_string, timeout=60)
            connection.setautocommit(True)
            return connection
        except Exception as error:
            last_error = error
            if attempt < 3:
                time.sleep(5)
    raise RuntimeError("Azure SQL did not accept a connection after three attempts.") from last_error


def forward_migrations() -> list[Path]:
    return sorted(
        path
        for path in MIGRATION_DIR.glob("PS-PLAT-*.sql")
        if not path.name.endswith("_rollback.sql")
    )


def apply_migrations(paths: list[Path]) -> None:
    with get_connection() as connection:
        cursor = connection.cursor()
        for path in paths:
            print(f"Applying {path.name}...")
            cursor.execute(path.read_text(encoding="utf-8"))
            while cursor.nextset():
                pass
            print(f"Applied {path.name}.")


def fetch_result_sets(cursor) -> list[list[dict]]:
    result_sets = []
    while True:
        if cursor.description is not None:
            columns = [column[0] for column in cursor.description]
            result_sets.append(
                [dict(zip(columns, row)) for row in cursor.fetchall()]
            )
        if not cursor.nextset():
            break
    return result_sets


def validate_verification_results(result_sets: list[list[dict]]) -> list[str]:
    failures = []
    if len(result_sets) < 8:
        return ["The verification query returned an incomplete result."]

    migration_ids = {row["migration_id"] for row in result_sets[1]}
    if migration_ids != EXPECTED_MIGRATIONS:
        failures.append(
            "Migration ledger mismatch: expected "
            + ", ".join(sorted(EXPECTED_MIGRATIONS))
            + "."
        )

    table_status = {row["object_name"]: bool(row["exists_flag"]) for row in result_sets[2]}
    missing_tables = sorted(
        name for name in EXPECTED_TABLES if not table_status.get(name, False)
    )
    if missing_tables:
        failures.append("Missing tables: " + ", ".join(missing_tables) + ".")

    object_status = {row["object_name"]: bool(row["exists_flag"]) for row in result_sets[3]}
    missing_objects = sorted(
        name for name in EXPECTED_PROGRAMMABLE_OBJECTS if not object_status.get(name, False)
    )
    if missing_objects:
        failures.append("Missing procedure or trigger: " + ", ".join(missing_objects) + ".")

    if result_sets[5]:
        failures.append("One or more new foreign keys are disabled or untrusted.")
    if result_sets[6]:
        failures.append("One or more check constraints are disabled or untrusted.")

    counts = result_sets[7][0] if result_sets[7] else {}
    if counts.get("profile_count") != counts.get("user_count"):
        failures.append("Not every application user has exactly one member profile.")
    if counts.get("private_profile_count") != counts.get("profile_count"):
        failures.append("One or more migrated member profiles are not private.")
    if counts.get("discovery_off_count") != counts.get("user_count"):
        failures.append("One or more members do not have discovery disabled by default.")

    return failures


def verify_foundation() -> None:
    if not VERIFY_PATH.exists():
        raise RuntimeError(f"Verification script is missing: {VERIFY_PATH}")
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(VERIFY_PATH.read_text(encoding="utf-8"))
        failures = validate_verification_results(fetch_result_sets(cursor))
    if failures:
        for failure in failures:
            print(f"FAILED: {failure}")
        raise RuntimeError("PeerSlate foundation verification failed.")
    print("Verified all seven migration records and all 31 platform and career tables.")
    print("Verified tenant constraints, private profile defaults, and opt-in discovery defaults.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply the forward migrations. Without this flag, only print the plan.",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Run the read-only foundation verification after any requested apply.",
    )
    args = parser.parse_args()
    paths = forward_migrations()
    if not paths:
        raise SystemExit("No PeerSlate platform migrations were found.")

    print("PeerSlate migration order:")
    for path in paths:
        print(f"- {path.name}")

    if not args.apply and not args.verify:
        print("Plan only. No database changes were made.")
        return

    if args.apply:
        apply_migrations(paths)
    if args.verify:
        verify_foundation()


if __name__ == "__main__":
    main()
