"""Plan or apply PeerSlate SQL migrations using the configured secure connection.

This is the original house applier. It remains the home of the platform
foundation verification (`verify_foundation` and friends) and of the connection
pattern every migration tool uses.

It is no longer the way schema reaches production. Use the governed path in
`scripts/govern_sql_migrations.py`, documented in
`docs/initiatives/PS-OPS-001/GOVERNED_SCHEMA_MIGRATION_PATH.md`: it computes what
is pending by reading `dbo.schema_migrations` instead of trusting
`MIGRATION_FILENAMES` to match reality, refuses any migration that has not been
proven against a throwaway database, and runs from the pipeline's
`SchemaMigration` stage rather than from an agent holding a credential.

`MIGRATION_FILENAMES` below is pinned to `SQL FIles/Migrations/registry.json` by
`tests/test_schema_migration_path.py`, so the two cannot drift apart.
"""

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
COMMUNITY_VERIFY_PATH = (
    ROOT
    / "SQL FIles"
    / "Verification"
    / "PS-COMMUNITY-PUBLIC-PILOT-001_owner_public_verify.sql"
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
    "PS-COMMUNITY-PUBLIC-PILOT-001": (
        MIGRATION_DIR
        / "proposed"
        / "PS-COMMUNITY-PUBLIC-PILOT-001_community.sql"
    ),
    "PS-COMMUNITY-RETENTION-001": (
        MIGRATION_DIR
        / "proposed"
        / "PS-COMMUNITY-RETENTION-001_retention.sql"
    ),
    "PS-COMMUNITY-RESTORE-001": (
        MIGRATION_DIR
        / "proposed"
        / "PS-COMMUNITY-RESTORE-001_restore.sql"
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


COMMUNITY_READ_CONTRACT_MARKERS = {
    "structural_conversation",
    "structural_conversation_end",
    "selected_contribution",
    "selected_contribution_end",
    "selected_wrong_post",
    "selected_wrong_post_end",
    "selected_revoked_author",
    "selected_revoked_author_end",
    "selected_revoked_post_author",
    "selected_revoked_post_author_end",
    "conversation_page_closure",
    "conversation_page_closure_end",
    "shelf_page_one",
    "shelf_page_one_end",
    "shelf_page_two",
    "shelf_page_two_end",
    "feed_boundary_page_one",
    "feed_boundary_page_one_end",
    "feed_boundary_page_two_after_revoke",
    "feed_boundary_page_two_after_revoke_end",
}
COMMUNITY_CLEANUP_SELECTOR_MARKERS = {
    "cleanup_post_selector",
    "cleanup_contribution_selector",
}


def _community_key(value) -> str:
    return str(value or "").lower()


def _validate_community_cleanup_selectors(
    result_sets: list[list[dict]], marker_indexes: dict[str, int]
) -> None:
    missing_markers = COMMUNITY_CLEANUP_SELECTOR_MARKERS - marker_indexes.keys()
    if missing_markers:
        raise RuntimeError(
            "Community verification returned incomplete cleanup-selector evidence."
        )
    for marker, selector_field in (
        ("cleanup_post_selector", "expected_post_key"),
        ("cleanup_contribution_selector", "expected_contribution_key"),
    ):
        marker_row = result_sets[marker_indexes[marker]][0]
        claim_index = marker_indexes[marker] + 1
        claims = result_sets[claim_index] if claim_index < len(result_sets) else []
        expected_media_key = _community_key(marker_row.get("expected_media_key"))
        if (
            not marker_row.get(selector_field)
            or not expected_media_key
            or len(claims) != 1
            or _community_key(claims[0].get("media_key"))
            != expected_media_key
            or not claims[0].get("cleanup_claim_token")
            or set(claims[0]) != {"media_key", "cleanup_claim_token"}
        ):
            raise RuntimeError(
                f"Community cleanup selector contract failed at {marker}."
            )


def _validate_community_read_contracts(
    result_sets: list[list[dict]], marker_indexes: dict[str, int]
) -> None:
    missing_markers = COMMUNITY_READ_CONTRACT_MARKERS - marker_indexes.keys()
    if missing_markers:
        raise RuntimeError(
            "Community verification returned incomplete read-contract evidence markers."
        )

    def marker_row(marker: str) -> dict:
        return result_sets[marker_indexes[marker]][0]

    def rows_after(marker: str, offset: int) -> list[dict]:
        index = marker_indexes[marker] + offset
        return result_sets[index] if index < len(result_sets) else []

    def require_span(start: str, end: str, result_set_count: int) -> None:
        if marker_indexes[end] != marker_indexes[start] + result_set_count + 1:
            raise RuntimeError(
                f"Community verification returned an invalid {start} result-set contract."
            )

    required_media_fields = {
        "media_key",
        "display_name",
        "content_type",
        "byte_length",
        "pixel_width",
        "pixel_height",
    }

    def has_full_media_shape(rows: list[dict]) -> bool:
        return all(
            required_media_fields <= row.keys()
            and bool(row.get("display_name"))
            and bool(row.get("content_type"))
            and int(row.get("byte_length") or 0) > 0
            for row in rows
        )

    require_span("structural_conversation", "structural_conversation_end", 6)
    conversation_expected = marker_row("structural_conversation")
    expected_post_key = _community_key(conversation_expected["expected_post_key"])
    expected_root_key = _community_key(conversation_expected["expected_root_key"])
    expected_hidden_key = _community_key(conversation_expected["expected_hidden_key"])
    expected_selected_key = _community_key(
        conversation_expected["expected_selected_key"]
    )
    expected_omitted_leaf_key = _community_key(
        conversation_expected["expected_omitted_leaf_key"]
    )
    expected_post_media_key = _community_key(
        conversation_expected["expected_post_media_key"]
    )
    expected_root_media_key = _community_key(
        conversation_expected["expected_root_media_key"]
    )
    expected_hidden_media_key = _community_key(
        conversation_expected["expected_hidden_media_key"]
    )
    expected_selected_media_key = _community_key(
        conversation_expected["expected_selected_media_key"]
    )

    post_rows = rows_after("structural_conversation", 1)
    contribution_rows = rows_after("structural_conversation", 2)
    post_media_rows = rows_after("structural_conversation", 3)
    contribution_media_rows = rows_after("structural_conversation", 4)
    viewer_rows = rows_after("structural_conversation", 5)
    boundary_rows = rows_after("structural_conversation", 6)
    if len(post_rows) != 1 or _community_key(post_rows[0].get("post_key")) != expected_post_key:
        raise RuntimeError("Community structural conversation did not return its post.")

    contributions = {
        _community_key(row.get("contribution_key")): row
        for row in contribution_rows
    }
    if not {expected_root_key, expected_hidden_key, expected_selected_key}.issubset(
        contributions
    ) or expected_omitted_leaf_key in contributions:
        raise RuntimeError(
            "Community conversation did not preserve required ancestors or omit a hidden leaf."
        )
    root_row = contributions[expected_root_key]
    hidden_row = contributions[expected_hidden_key]
    selected_row = contributions[expected_selected_key]
    if (
        root_row.get("projection_state") != "active"
        or selected_row.get("projection_state") != "active"
        or not root_row.get("body")
        or not selected_row.get("body")
        or not root_row.get("author_name")
        or not selected_row.get("author_name")
    ):
        raise RuntimeError("Community conversation suppressed authorized content.")
    if hidden_row.get("projection_state") != "unavailable" or any(
        hidden_row.get(field) is not None
        for field in (
            "body",
            "contribution_kind",
            "author_name",
            "author_avatar_url",
        )
    ):
        raise RuntimeError("Community conversation tombstone exposed hidden content.")
    if (
        root_row.get("parent_contribution_key") is not None
        or _community_key(hidden_row.get("parent_contribution_key"))
        != expected_root_key
        or _community_key(selected_row.get("parent_contribution_key"))
        != expected_hidden_key
    ):
        raise RuntimeError("Community conversation tombstone broke the ancestor structure.")
    if int(root_row.get("child_reply_count") or 0) != 0 or int(
        hidden_row.get("child_reply_count") or 0
    ) != 1:
        raise RuntimeError("Community conversation child counts were not authorization-scoped.")

    post_media_keys = {
        _community_key(row.get("media_key")) for row in post_media_rows
    }
    contribution_media_keys = {
        _community_key(row.get("media_key")) for row in contribution_media_rows
    }
    if (
        post_media_keys != {expected_post_media_key}
        or contribution_media_keys
        != {expected_root_media_key, expected_selected_media_key}
        or not has_full_media_shape(post_media_rows)
        or not has_full_media_shape(contribution_media_rows)
    ):
        raise RuntimeError("Community conversation attachment projection is incomplete or unsafe.")
    if (
        len(viewer_rows) != 1
        or not bool(viewer_rows[0].get("saved"))
        or viewer_rows[0].get("response_intention") != "offer_help"
        or len(boundary_rows) != 1
        or bool(boundary_rows[0].get("has_more"))
        or min(
            int(boundary_rows[0].get("selected_candidate_count") or 0), 20
        )
        > len(contribution_rows)
        or len(contribution_rows) > 180
    ):
        raise RuntimeError("Community conversation viewer or boundary contract failed.")

    require_span("conversation_page_closure", "conversation_page_closure_end", 6)
    closure_expected = marker_row("conversation_page_closure")
    closure_post_rows = rows_after("conversation_page_closure", 1)
    closure_contribution_rows = rows_after("conversation_page_closure", 2)
    closure_boundary_rows = rows_after("conversation_page_closure", 6)
    closure_contributions = {
        _community_key(row.get("contribution_key")): row
        for row in closure_contribution_rows
    }
    closure_parent_key = _community_key(closure_expected["expected_parent_key"])
    closure_child_key = _community_key(closure_expected["expected_child_key"])
    closure_boundary_key = _community_key(closure_expected["expected_boundary_key"])
    if (
        len(closure_post_rows) != 1
        or _community_key(closure_post_rows[0].get("post_key"))
        != _community_key(closure_expected["expected_post_key"])
        or closure_parent_key not in closure_contributions
        or closure_child_key not in closure_contributions
        or _community_key(
            closure_contributions[closure_child_key].get(
                "parent_contribution_key"
            )
        )
        != closure_parent_key
        or len(closure_boundary_rows) != 1
        or int(
            closure_boundary_rows[0].get("selected_candidate_count") or 0
        )
        != 21
        or not bool(closure_boundary_rows[0].get("has_more"))
        or _community_key(
            closure_boundary_rows[0].get("boundary_contribution_key")
        )
        != closure_boundary_key
        or set(closure_boundary_rows[0])
        != {
            "selected_candidate_count",
            "has_more",
            "boundary_created_at_utc",
            "boundary_contribution_key",
        }
    ):
        raise RuntimeError(
            "Community conversation page did not preserve ancestor closure."
        )

    require_span("selected_contribution", "selected_contribution_end", 4)
    selected_expected = marker_row("selected_contribution")
    selected_rows = rows_after("selected_contribution", 1)
    selected_media_rows = rows_after("selected_contribution", 2)
    ancestor_rows = rows_after("selected_contribution", 3)
    ancestor_media_rows = rows_after("selected_contribution", 4)
    if (
        len(selected_rows) != 1
        or _community_key(selected_rows[0].get("contribution_key"))
        != _community_key(selected_expected["expected_selected_key"])
        or selected_rows[0].get("projection_state") != "active"
        or not selected_rows[0].get("body")
        or not selected_rows[0].get("author_name")
        or not bool(selected_rows[0].get("viewer_saved"))
    ):
        raise RuntimeError("Community selected-contribution authorization failed.")
    if {
        _community_key(row.get("media_key")) for row in selected_media_rows
    } != {
        _community_key(selected_expected["expected_selected_media_key"])
    } or not has_full_media_shape(selected_media_rows):
        raise RuntimeError("Community selected contribution did not return full attachments.")
    if [
        _community_key(row.get("contribution_key")) for row in ancestor_rows
    ] != [
        _community_key(selected_expected["expected_root_key"]),
        _community_key(selected_expected["expected_hidden_key"]),
    ]:
        raise RuntimeError("Community selected contribution returned an invalid ancestor chain.")
    selected_hidden_row = ancestor_rows[1]
    if (
        ancestor_rows[0].get("projection_state") != "active"
        or not ancestor_rows[0].get("body")
        or not ancestor_rows[0].get("author_name")
    ):
        raise RuntimeError("Community selected-contribution suppressed an active ancestor.")
    if selected_hidden_row.get("projection_state") != "unavailable" or any(
        selected_hidden_row.get(field) is not None
        for field in (
            "body",
            "contribution_kind",
            "author_name",
            "author_avatar_url",
        )
    ):
        raise RuntimeError("Community selected-contribution tombstone exposed content.")
    if (
        ancestor_rows[0].get("parent_contribution_key") is not None
        or _community_key(selected_hidden_row.get("parent_contribution_key"))
        != _community_key(selected_expected["expected_root_key"])
    ):
        raise RuntimeError("Community selected-contribution ancestor structure failed.")
    ancestor_media_keys = {
        _community_key(row.get("media_key")) for row in ancestor_media_rows
    }
    if (
        ancestor_media_keys
        != {_community_key(selected_expected["expected_root_media_key"])}
        or _community_key(selected_expected["expected_hidden_media_key"])
        in ancestor_media_keys
        or not has_full_media_shape(ancestor_media_rows)
    ):
        raise RuntimeError("Community selected-contribution ancestor media was not authorized.")

    for start, end in (
        ("selected_wrong_post", "selected_wrong_post_end"),
        ("selected_revoked_author", "selected_revoked_author_end"),
        ("selected_revoked_post_author", "selected_revoked_post_author_end"),
    ):
        require_span(start, end, 4)
        if any(rows_after(start, offset) for offset in range(1, 5)):
            raise RuntimeError(f"Community selected-contribution denial failed at {start}.")

    require_span("shelf_page_one", "shelf_page_one_end", 4)
    require_span("shelf_page_two", "shelf_page_two_end", 4)
    shelf_one_expected = marker_row("shelf_page_one")
    shelf_one_eligibility = rows_after("shelf_page_one", 1)
    shelf_one_items = rows_after("shelf_page_one", 2)
    shelf_one_media = rows_after("shelf_page_one", 3)
    shelf_one_boundary = rows_after("shelf_page_one", 4)
    shelf_two_eligibility = rows_after("shelf_page_two", 1)
    shelf_two_items = rows_after("shelf_page_two", 2)
    shelf_two_media = rows_after("shelf_page_two", 3)
    shelf_two_boundary = rows_after("shelf_page_two", 4)
    if (
        len(shelf_one_eligibility) != 1
        or _community_key(shelf_one_eligibility[0].get("post_key")) != expected_post_key
        or len(shelf_two_eligibility) != 1
        or _community_key(shelf_two_eligibility[0].get("post_key")) != expected_post_key
        or len(shelf_one_items) != 20
        or shelf_one_media
    ):
        raise RuntimeError("Community shelf eligibility or page bound failed.")
    shelf_one_synthetic = [
        row for row in shelf_one_items if str(row.get("body", "")).startswith("Community shelf page ")
    ]
    shelf_two_synthetic = [
        row for row in shelf_two_items if str(row.get("body", "")).startswith("Community shelf page ")
    ]
    shelf_one_keys = {
        _community_key(row.get("contribution_key")) for row in shelf_one_items
    }
    shelf_two_keys = {
        _community_key(row.get("contribution_key")) for row in shelf_two_items
    }
    shelf_two_by_key = {
        _community_key(row.get("contribution_key")): row for row in shelf_two_items
    }
    if (
        len(shelf_one_synthetic) != 20
        or len(shelf_two_synthetic) != 2
        or shelf_one_keys & shelf_two_keys
        or len(shelf_one_synthetic) + len(shelf_two_synthetic) != 22
        or any(
            row.get("projection_state") != "active"
            or not row.get("body")
            or not row.get("author_name")
            for row in shelf_one_items + shelf_two_items
        )
        or not bool(shelf_two_by_key.get(expected_selected_key, {}).get("viewer_saved"))
    ):
        raise RuntimeError("Community shelf keyset pagination skipped or duplicated rows.")
    if (
        len(shelf_one_boundary) != 1
        or int(shelf_one_boundary[0].get("selected_candidate_count") or 0) != 21
        or not bool(shelf_one_boundary[0].get("has_more"))
        or not shelf_one_boundary[0].get("boundary_created_at_utc")
        or _community_key(shelf_one_boundary[0].get("boundary_contribution_key"))
        != _community_key(shelf_one_expected["expected_boundary_key"])
        or len(shelf_two_boundary) != 1
        or bool(shelf_two_boundary[0].get("has_more"))
        or int(shelf_two_boundary[0].get("selected_candidate_count") or 0)
        != len(shelf_two_items)
    ):
        raise RuntimeError("Community shelf boundary contract failed.")
    shelf_two_media_keys = {
        _community_key(row.get("media_key")) for row in shelf_two_media
    }
    if (
        shelf_two_media_keys
        != {expected_root_media_key, expected_selected_media_key}
        or not has_full_media_shape(shelf_two_media)
    ):
        raise RuntimeError("Community shelf attachment authorization failed.")

    for start, end in (
        ("feed_boundary_page_one", "feed_boundary_page_one_end"),
        (
            "feed_boundary_page_two_after_revoke",
            "feed_boundary_page_two_after_revoke_end",
        ),
    ):
        require_span(start, end, 6)
        feed_expected = marker_row(start)
        expected_key = _community_key(feed_expected["expected_post_key"])
        expected_selected_count = int(
            feed_expected["expected_selected_candidate_count"]
        )
        expected_has_more = bool(feed_expected["expected_has_more"])
        feed_rows = rows_after(start, 1)
        shelf_boundary_rows = rows_after(start, 5)
        feed_boundary_rows = rows_after(start, 6)
        if (
            len(feed_rows) != 1
            or _community_key(feed_rows[0].get("post_key")) != expected_key
            or len(shelf_boundary_rows) != 1
            or _community_key(shelf_boundary_rows[0].get("post_key")) != expected_key
            or len(feed_boundary_rows) != 1
            or int(feed_boundary_rows[0].get("selected_candidate_count") or 0)
            != expected_selected_count
            or bool(feed_boundary_rows[0].get("has_more")) != expected_has_more
            or not feed_boundary_rows[0].get("boundary_published_at_utc")
            or _community_key(feed_boundary_rows[0].get("boundary_post_key"))
            != expected_key
            or set(feed_boundary_rows[0])
            != {
                "selected_candidate_count",
                "has_more",
                "boundary_published_at_utc",
                "boundary_post_key",
            }
        ):
            raise RuntimeError(f"Community Feed boundary contract failed at {start}.")
    revoked_key = _community_key(
        marker_row("feed_boundary_page_two_after_revoke")["revoked_post_key"]
    )
    if any(
        _community_key(row.get("post_key")) == revoked_key
        for row in rows_after("feed_boundary_page_two_after_revoke", 1)
    ):
        raise RuntimeError("Community Feed replayed a revoked boundary post.")


def verify_community(env_path: Path | None = None) -> None:
    if not COMMUNITY_VERIFY_PATH.exists():
        raise RuntimeError(f"Verification script is missing: {COMMUNITY_VERIFY_PATH}")
    with get_connection(env_path) as connection:
        cursor = connection.cursor()
        cursor.execute(COMMUNITY_VERIFY_PATH.read_text(encoding="utf-8"))
        result_sets = fetch_result_sets(cursor)

    marker_indexes = {}
    for index, rows in enumerate(result_sets):
        if len(rows) == 1 and rows[0].get("verification_marker"):
            marker_indexes[rows[0]["verification_marker"]] = index

    required_markers = {
        "publish_conflict",
        "cross_owner_post_edit",
        "contribution_conflict",
        "cross_owner_contribution_edit",
        "public_feed_before_delete",
        "public_detail_before_delete",
        "public_search_before_delete",
        "public_media_before_delete",
        "public_feed_after_delete",
        "public_detail_after_delete",
        "public_detail_after_delete_end",
        "public_search_after_delete",
        "public_media_after_delete",
        "public_media_after_delete_end",
        "cleanup_claim",
        "cleanup_wrong_token",
        "cleanup_complete",
        "cleanup_second_complete",
    } | COMMUNITY_READ_CONTRACT_MARKERS | COMMUNITY_CLEANUP_SELECTOR_MARKERS
    if required_markers - marker_indexes.keys():
        raise RuntimeError("Community verification returned incomplete evidence markers.")

    def rows_after(marker: str, offset: int = 1) -> list[dict]:
        index = marker_indexes[marker] + offset
        return result_sets[index] if index < len(result_sets) else []

    expected = result_sets[marker_indexes["public_feed_before_delete"]][0]
    expected_post_key = str(expected["expected_post_key"]).lower()
    expected_media_key = str(expected["expected_media_key"]).lower()

    expected_outcomes = {
        "publish_conflict": "idempotency_conflict",
        "cross_owner_post_edit": "not_found",
        "contribution_conflict": "idempotency_conflict",
        "cross_owner_contribution_edit": "not_found",
    }
    for marker, outcome in expected_outcomes.items():
        rows = rows_after(marker)
        if not rows or rows[0].get("outcome") != outcome:
            raise RuntimeError(f"Community verification failed at {marker}.")

    before_feed = rows_after("public_feed_before_delete")
    before_detail = rows_after("public_detail_before_delete")
    before_search = rows_after("public_search_before_delete")
    before_media = rows_after("public_media_before_delete")
    if not all(
        any(str(row.get("post_key", "")).lower() == expected_post_key for row in rows)
        for rows in (before_feed, before_detail, before_search)
    ):
        raise RuntimeError("Community public read procedures did not return the eligible post.")
    if not any(
        str(row.get("media_key", "")).lower() == expected_media_key
        for row in before_media
    ):
        raise RuntimeError("Community public media authorization did not return eligible media.")

    after_feed = rows_after("public_feed_after_delete")
    after_search = rows_after("public_search_after_delete")
    if any(
        str(row.get("post_key", "")).lower() == expected_post_key
        for rows in (after_feed, after_search)
        for row in rows
    ):
        raise RuntimeError("Community deletion did not revoke a public feed/search projection.")
    if marker_indexes["public_detail_after_delete_end"] != marker_indexes["public_detail_after_delete"] + 1:
        raise RuntimeError("Community deletion did not revoke public post detail.")
    after_media = rows_after("public_media_after_delete")
    if after_media or marker_indexes["public_media_after_delete_end"] != marker_indexes["public_media_after_delete"] + 2:
        raise RuntimeError("Community deletion did not revoke public media.")

    cleanup_claim = rows_after("cleanup_claim")
    cleanup_wrong_token = rows_after("cleanup_wrong_token")
    cleanup_complete = rows_after("cleanup_complete")
    cleanup_second_complete = rows_after("cleanup_second_complete")
    if (
        len(cleanup_claim) != 1
        or str(cleanup_claim[0].get("media_key", "")).lower() != expected_media_key
        or not cleanup_claim[0].get("cleanup_claim_token")
    ):
        raise RuntimeError("Community deletion did not create a retryable media cleanup claim.")
    if not cleanup_complete or cleanup_complete[0].get("outcome") != "completed":
        raise RuntimeError("Community media cleanup completion failed.")
    if (
        not cleanup_wrong_token
        or cleanup_wrong_token[0].get("outcome") != "not_found"
        or not cleanup_second_complete
        or cleanup_second_complete[0].get("outcome") != "not_found"
    ):
        raise RuntimeError("Community media cleanup lease/idempotency checks failed.")

    _validate_community_read_contracts(result_sets, marker_indexes)
    _validate_community_cleanup_selectors(result_sets, marker_indexes)

    final_rows = next((rows for rows in reversed(result_sets) if rows), [])
    if not final_rows or not bool(final_rows[0].get("verified")):
        raise RuntimeError("PS-COMMUNITY-PUBLIC-PILOT-001 verification failed.")
    print(
        "Verified Community public reads, bounded shelf traversal, selected "
        "contribution authorization, structural tombstones, revocation-safe "
        "Feed boundaries, two-owner write isolation, media cleanup, and rollback."
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
        if "PS-COMMUNITY-PUBLIC-PILOT-001" in args.migration:
            verify_community(args.env_file)


if __name__ == "__main__":
    main()
