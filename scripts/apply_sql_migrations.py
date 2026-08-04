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
CAPTURE_VERIFY_PATH = (
    ROOT
    / "SQL FIles"
    / "Verification"
    / "PS-CAPTURE-001_owner_isolation_verify.sql"
)
CAPTURE_LIFECYCLE_VERIFY_PATH = (
    ROOT
    / "SQL FIles"
    / "Verification"
    / "PS-CAPTURE-002_lifecycle_verify.sql"
)
MOMENT_VERIFY_PATH = (
    ROOT
    / "SQL FIles"
    / "Verification"
    / "PS-MOMENT-001_owner_isolation_verify.sql"
)
PLACEMENT_VERIFY_PATH = (
    ROOT
    / "SQL FIles"
    / "Verification"
    / "PS-PLACEMENT-001_owner_isolation_verify.sql"
)
VOICE_VERIFY_PATH = (
    ROOT
    / "SQL FIles"
    / "Verification"
    / "PS-VOICE-001_owner_isolation_verify.sql"
)
PHOTO_VERIFY_PATH = (
    ROOT
    / "SQL FIles"
    / "Verification"
    / "PS-CAPTURE-MEDIA-001_owner_isolation_verify.sql"
)
WORKSHOP_VERIFY_PATH = (
    ROOT
    / "SQL FIles"
    / "Verification"
    / "PS-WORKSHOP-001_owner_isolation_verify.sql"
)

MIGRATION_FILENAMES = (
    # PS-PLAT-000 exists because dbo.app_users predates the migration system.
    # Six migrations declare foreign keys against it, but nothing created it,
    # so a database could not be built from this repository at all. Found by
    # the Community disposable SQL proof, 2026-08-03. It is a no-op plus one
    # ledger row on any database that already has the table, including
    # production.
    "PS-PLAT-000_app_users_base.sql",
    "PS-PLAT-001_platform_governance.sql",
    "PS-PLAT-002_profiles_entities_access.sql",
    "PS-PLAT-003_evidence_ai.sql",
    "PS-PLAT-004_connections_notifications.sql",
    "PS-PLAT-005_tenant_integrity.sql",
    "PS-PLAT-006_living_resume_domain.sql",
    "PS-PLAT-007_living_resume_reads.sql",
    "PS-AUTH-001_identity_foundation.sql",
)
EXPECTED_MIGRATIONS = {name.split("_")[0] for name in MIGRATION_FILENAMES}
APPROVED_OPTIONAL_MIGRATIONS = {
    "PS-CAPTURE-001": (
        MIGRATION_DIR / "proposed" / "PS-CAPTURE-001_captures.sql"
    ),
    "PS-CAPTURE-002": (
        MIGRATION_DIR / "proposed" / "PS-CAPTURE-002_capture_lifecycle.sql"
    ),
    "PS-MOMENT-001": (
        MIGRATION_DIR / "proposed" / "PS-MOMENT-001_moments.sql"
    ),
    "PS-PLACEMENT-001": (
        MIGRATION_DIR / "proposed" / "PS-PLACEMENT-001_moment_placements.sql"
    ),
    "PS-VOICE-001": (
        MIGRATION_DIR / "proposed" / "PS-VOICE-001_voice_capture.sql"
    ),
    "PS-CAPTURE-MEDIA-001": (
        MIGRATION_DIR
        / "proposed"
        / "PS-CAPTURE-MEDIA-001_photo_sources.sql"
    ),
    "PS-WORKSHOP-001": (
        MIGRATION_DIR / "proposed" / "PS-WORKSHOP-001_knowledge_items.sql"
    ),
}
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
    "user_identities",
}
EXPECTED_PROGRAMMABLE_OBJECTS = {
    "usp_AppendAuditEvent",
    "usp_GetOwnerLivingResume",
    "usp_GetPublicLivingResumeBySlug",
    "trg_audit_events_immutable",
    "trg_content_approval_events_immutable",
    "usp_UpsertAppUserFromAuth",
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


def get_connection(env_path: Path | None = None):
    # Load the local secret only when an apply or verification connection is
    # actually requested. Plan-only mode never reads connection settings.
    resolved_env_path = env_path or ROOT / ".env"
    if env_path is not None and not resolved_env_path.exists():
        raise RuntimeError(f"Connection environment file is missing: {resolved_env_path}")
    if resolved_env_path.exists():
        load_dotenv(resolved_env_path, override=env_path is not None)
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
    paths = [MIGRATION_DIR / name for name in MIGRATION_FILENAMES]
    missing = [path.name for path in paths if not path.exists()]
    if missing:
        raise RuntimeError("Missing migrations: " + ", ".join(missing) + ".")
    return paths


def selected_optional_migrations(migration_ids: list[str]) -> list[Path]:
    paths = [APPROVED_OPTIONAL_MIGRATIONS[item] for item in migration_ids]
    missing = [path.name for path in paths if not path.exists()]
    if missing:
        raise RuntimeError("Missing migrations: " + ", ".join(missing) + ".")
    return paths


def apply_migrations(paths: list[Path], env_path: Path | None = None) -> None:
    with get_connection(env_path) as connection:
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
    missing_migrations = EXPECTED_MIGRATIONS - migration_ids
    if missing_migrations:
        failures.append(
            "Migration ledger is missing required foundation records: "
            + ", ".join(sorted(missing_migrations))
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
    if counts.get("account_key_count") != counts.get("user_count"):
        failures.append("One or more application users has no internal account UUID.")
    if counts.get("identity_count", 0) < counts.get("mapped_auth_count", 0):
        failures.append("One or more legacy authentication mappings was not migrated.")

    return failures


def verify_foundation(env_path: Path | None = None) -> None:
    if not VERIFY_PATH.exists():
        raise RuntimeError(f"Verification script is missing: {VERIFY_PATH}")
    with get_connection(env_path) as connection:
        cursor = connection.cursor()
        cursor.execute(VERIFY_PATH.read_text(encoding="utf-8"))
        failures = validate_verification_results(fetch_result_sets(cursor))
    if failures:
        for failure in failures:
            print(f"FAILED: {failure}")
        raise RuntimeError("PeerSlate foundation verification failed.")
    print("Verified all eight migration records and all platform, career, and identity tables.")
    print("Verified tenant constraints, private profile defaults, and opt-in discovery defaults.")


def verify_capture(env_path: Path | None = None) -> None:
    if not CAPTURE_VERIFY_PATH.exists():
        raise RuntimeError(f"Verification script is missing: {CAPTURE_VERIFY_PATH}")
    with get_connection(env_path) as connection:
        cursor = connection.cursor()
        cursor.execute(CAPTURE_VERIFY_PATH.read_text(encoding="utf-8"))
        result_sets = fetch_result_sets(cursor)
    final_rows = next((rows for rows in reversed(result_sets) if rows), [])
    if not final_rows or not bool(final_rows[0].get("verified")):
        raise RuntimeError("PS-CAPTURE-001 owner-isolation verification failed.")
    print("Verified PS-CAPTURE-001 with two synthetic owners and a full rollback.")


def verify_capture_lifecycle(env_path: Path | None = None) -> None:
    if not CAPTURE_LIFECYCLE_VERIFY_PATH.exists():
        raise RuntimeError(
            f"Verification script is missing: {CAPTURE_LIFECYCLE_VERIFY_PATH}"
        )
    with get_connection(env_path) as connection:
        cursor = connection.cursor()
        cursor.execute(CAPTURE_LIFECYCLE_VERIFY_PATH.read_text(encoding="utf-8"))
        result_sets = fetch_result_sets(cursor)
    final_rows = next((rows for rows in reversed(result_sets) if rows), [])
    if not final_rows or not bool(final_rows[0].get("verified")):
        raise RuntimeError("PS-CAPTURE-002 lifecycle verification failed.")
    print(
        "Verified PS-CAPTURE-002 lifecycle, two-owner isolation, "
        "no automatic publication, and full synthetic rollback."
    )


def verify_moment(env_path: Path | None = None) -> None:
    if not MOMENT_VERIFY_PATH.exists():
        raise RuntimeError(f"Verification script is missing: {MOMENT_VERIFY_PATH}")
    with get_connection(env_path) as connection:
        cursor = connection.cursor()
        cursor.execute(MOMENT_VERIFY_PATH.read_text(encoding="utf-8"))
        result_sets = fetch_result_sets(cursor)
    final_rows = next((rows for rows in reversed(result_sets) if rows), [])
    if not final_rows or not bool(final_rows[0].get("verified")):
        raise RuntimeError("PS-MOMENT-001 owner-isolation verification failed.")
    print(
        "Verified PS-MOMENT-001 source pinning, two-owner isolation, "
        "deletion tombstones, explicit private confirmation, no automatic "
        "publication/placement, and full synthetic rollback."
    )


def verify_placement(env_path: Path | None = None) -> None:
    if not PLACEMENT_VERIFY_PATH.exists():
        raise RuntimeError(
            f"Verification script is missing: {PLACEMENT_VERIFY_PATH}"
        )
    with get_connection(env_path) as connection:
        cursor = connection.cursor()
        cursor.execute(PLACEMENT_VERIFY_PATH.read_text(encoding="utf-8"))
        result_sets = fetch_result_sets(cursor)
    final_rows = next((rows for rows in reversed(result_sets) if rows), [])
    if not final_rows or not bool(final_rows[0].get("verified")):
        raise RuntimeError("PS-PLACEMENT-001 owner-isolation verification failed.")
    print(
        "Verified PS-PLACEMENT-001 exact-version pinning, two-owner isolation, "
        "destination eligibility, remove/reactivate lifecycle, zero content "
        "copy, no downstream writes, and full synthetic rollback."
    )


def verify_voice(env_path: Path | None = None) -> None:
    if not VOICE_VERIFY_PATH.exists():
        raise RuntimeError(f"Verification script is missing: {VOICE_VERIFY_PATH}")
    with get_connection(env_path) as connection:
        cursor = connection.cursor()
        cursor.execute(VOICE_VERIFY_PATH.read_text(encoding="utf-8"))
        result_sets = fetch_result_sets(cursor)
    final_rows = next((rows for rows in reversed(result_sets) if rows), [])
    if not final_rows or not bool(final_rows[0].get("verified")):
        raise RuntimeError("PS-VOICE-001 owner-isolation verification failed.")
    print(
        "Verified PS-VOICE-001 owner isolation, immutable transcript provenance, "
        "explicit private confirmation, retry, deletion, and zero downstream writes."
    )


def verify_photo(env_path: Path | None = None) -> None:
    if not PHOTO_VERIFY_PATH.exists():
        raise RuntimeError(f"Verification script is missing: {PHOTO_VERIFY_PATH}")
    with get_connection(env_path) as connection:
        cursor = connection.cursor()
        cursor.execute(PHOTO_VERIFY_PATH.read_text(encoding="utf-8"))
        result_sets = fetch_result_sets(cursor)
    final_rows = next((rows for rows in reversed(result_sets) if rows), [])
    if not final_rows or not bool(final_rows[0].get("verified")):
        raise RuntimeError("PS-CAPTURE-MEDIA-001 owner-isolation verification failed.")
    print(
        "Verified PS-CAPTURE-MEDIA-001 owner isolation, fail-closed scan and "
        "derivative gates, explicit private confirmation, deletion, and zero "
        "downstream writes."
    )


def verify_workshop(env_path: Path | None = None) -> None:
    if not WORKSHOP_VERIFY_PATH.exists():
        raise RuntimeError(f"Verification script is missing: {WORKSHOP_VERIFY_PATH}")
    with get_connection(env_path) as connection:
        cursor = connection.cursor()
        cursor.execute(WORKSHOP_VERIFY_PATH.read_text(encoding="utf-8"))
        result_sets = fetch_result_sets(cursor)
    final_rows = next((rows for rows in reversed(result_sets) if rows), [])
    if not final_rows or not bool(final_rows[0].get("verified")):
        raise RuntimeError("PS-WORKSHOP-001 owner-isolation verification failed.")
    print(
        "Verified PS-WORKSHOP-001 owner isolation across all seven knowledge "
        "item procedures, per-owner idempotent Save, version-fenced "
        "Update/Archive/Restore/Delete, forged-owner canaries, and full "
        "synthetic rollback."
    )


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
        help="Run foundation checks and any selected migration verification.",
    )
    parser.add_argument(
        "--migration",
        action="append",
        choices=sorted(APPROVED_OPTIONAL_MIGRATIONS),
        default=[],
        help=(
            "Plan, apply, or verify an explicitly approved optional migration. "
            "Repeat this flag to select more than one."
        ),
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        help=(
            "Use a specific local environment file for apply/verify. "
            "The file is never read in plan-only mode."
        ),
    )
    args = parser.parse_args()
    paths = (
        selected_optional_migrations(args.migration)
        if args.migration
        else forward_migrations()
    )
    if not paths:
        raise SystemExit("No PeerSlate platform migrations were found.")

    print("PeerSlate migration plan:")
    for path in paths:
        print(f"- {path.name}")

    if not args.apply and not args.verify:
        print("Plan only. No database changes were made.")
        return

    if args.apply:
        apply_migrations(paths, args.env_file)
    if args.verify:
        verify_foundation(args.env_file)
        if "PS-CAPTURE-001" in args.migration:
            verify_capture(args.env_file)
        if "PS-CAPTURE-002" in args.migration:
            verify_capture_lifecycle(args.env_file)
        if "PS-MOMENT-001" in args.migration:
            verify_moment(args.env_file)
        if "PS-PLACEMENT-001" in args.migration:
            verify_placement(args.env_file)
        if "PS-VOICE-001" in args.migration:
            verify_voice(args.env_file)
        if "PS-CAPTURE-MEDIA-001" in args.migration:
            verify_photo(args.env_file)
        if "PS-WORKSHOP-001" in args.migration:
            verify_workshop(args.env_file)


if __name__ == "__main__":
    main()
