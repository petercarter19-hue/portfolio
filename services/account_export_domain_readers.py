"""Thin read-only adapter over the account-export core-reader procedures
(SQL FIles/Migrations/PS-SETTINGS-EXPORT-003_core_readers.sql) and the
Capture/Moment reader procedures
(SQL FIles/Migrations/PS-SETTINGS-EXPORT-004_capture_moment_readers.sql).

This module does no connection management, holds no configuration, and
is not coupled to services/database_service.py's shared-application-
connection allowlist or to any future worker -- every function here
takes a caller-supplied ``connection`` and does nothing else with it.
It exists so a future domain-population slice, and C3+, have exactly
one place that knows which domains exist, which are actually readable
today, and what each reader returns -- never a second copy of that
truth duplicated into a route or a template.

Every ``read_*`` function:
  - opens one cursor on the given connection;
  - calls its one ``EXEC dbo.usp_ReadAccountExport<Reader>ForOwner
    @UserKey = ?`` procedure and decodes every returned row into a dict
    keyed by the procedure's own output column names;
  - separates the two transport-level ``read_started_at_utc`` /
    ``read_ended_at_utc`` columns every reader returns on each content
    row (see the migration's own header for why the read window is a
    pair of trailing columns, not a second result set or OUTPUT
    parameters) from the domain content itself, surfacing them once at
    the top level instead of duplicated on every row;
  - when at least one content row came back, uses THAT row's own
    read-window columns as the authoritative window (captured on the
    database server, bracketing only the actual table read, not the
    round trip to get there);
  - when zero content rows came back (an unresolved identity, or a
    genuinely empty domain for a real owner), falls back to bracketing
    the call with a SYSUTCDATETIME() read immediately before and after
    on the same connection -- the same "read window" idiom
    scripts/run_account_export_worker.py's own read_consistency_marker
    already uses for @@DBTS -- so a zero-row domain still reports a
    truthful window instead of no window at all;
  - returns ``{"rows": [...], "read_started_at_utc": ..., "read_ended_at_utc": ...}``
    and NOTHING else -- no save, no publish, no send, no delete. This
    module cannot mutate anything; every procedure it calls is a plain
    SELECT (see the migration's and verification script's own grep
    tripwires against transaction control and writes in these
    procedures).

DOMAINS is the single source of truth C3+ must read from, never
duplicate: every C0 V1 domain-matrix row
(docs/initiatives/PS-SETTINGS-MY-DATA-SHELL-001/C0_ACCOUNT_EXPORT_ARCHITECTURE.md)
appears exactly once, with an explicit ``disposition`` of
``"included"``, ``"excluded"``, or ``"unavailable"`` -- the same closed
three-value vocabulary dbo.account_export_job_domains'
CK_account_export_job_domains_disposition and
services/account_export_assembly_service.py's ``_DISPOSITIONS`` already
use, so nothing here invents a fourth value a future manifest write
would have to translate -- and a stable, truthful reason for every
disposition other than "included". An included domain lists every
reader this migration created for it, each with its exact procedure
name, a schema identifier, and the exact allowlisted output field
tuple, INCLUDING the two trailing read-window columns every reader
actually returns -- the same list tests/test_settings_export_core_readers.py
pins against the actual SQL text, so this file can never silently drift
from what the database really returns.

Scope: PS-SETTINGS-EXPORT-003 (replacement package 1) built account,
profile, and Living Resume (one reader per PS-PLAT-006 table).
PS-SETTINGS-EXPORT-004 (replacement package 2, this update) adds two
more: capture (dbo.captures, dbo.capture_revisions) and moment
(dbo.moments, dbo.moment_versions, dbo.moment_sources,
dbo.moment_placements) -- text truth only. Every content hash,
checksum, media/photo/voice/blob/file reference, transcript linkage,
storage locator, and URL to stored media is excluded from both new
domains' field lists (neither dbo.captures/dbo.capture_revisions nor
any of the four Moment tables has such a column, so no row is
incomplete for lack of one); dbo.moment_placements' target_entity_id
(a foreign key to dbo.slate_entities, the Opportunity Slate
destination) is also excluded -- Opportunity Slate is a separate C0
matrix row with its own future, separately claimed reader, and
dbo.slate_entities is not one of PS-SETTINGS-EXPORT-004's six claimed
tables.

dbo.career_skill_links is deliberately excluded: its rows reference
evidence_item_id, whose disclosure rules are undecided, so it is
recorded here as its own excluded entry rather than silently folded
into "living_resume" or omitted. Every other C0 matrix row is recorded
with a truthful disposition and reason drawn from
C0_ACCOUNT_EXPORT_ARCHITECTURE.md's own "V1 domain matrix" and
"Required truth boundary" text -- most as "excluded" (a future,
separately claimed reader this package does not build) and a smaller
set as "unavailable" (the source schema itself is not yet applied, or
the domain is structurally unavailable to a server-side export), never
guessed. "voice_photo" was corrected from "unavailable" to "excluded"
by PS-SETTINGS-EXPORT-004: its prior reason claimed
PS-VOICE-001/PS-CAPTURE-MEDIA-001 were "not gated/applied," but
docs/governance/PRODUCTION_SCHEMA_STATE.md shows both applied in
production (like dbo.captures/dbo.moments, they are gated: null in the
registry -- a disposable-database rehearsal proof, never a claim about
what a real database carries -- so "not yet gated" must not be read as
"not yet applied"). The corrected reason states this package's actual
boundary: every media/transcript/hash column is out of scope pending a
dedicated future reader.

Nothing in this module is wired to any route, worker, or scheduler.
There is still no live export, no populated dbo.account_export_job_domains
row, and no production authority here or anywhere else in this package.
"""

from __future__ import annotations


def _read_clock(cursor):
    """A plain SYSUTCDATETIME() read on the caller's own connection --
    a database-internal clock read, never a domain reader. Matches
    scripts/run_account_export_worker.py's read_consistency_marker
    shape for @@DBTS. Used only as the fallback read window for a
    zero-row result; a non-empty result uses its own rows' read-window
    columns instead (see module docstring)."""

    cursor.execute("SELECT SYSUTCDATETIME() AS now_utc;")
    row = cursor.fetchone()
    return row[0] if row else None


def _rows_as_dicts(cursor):
    """Decode the cursor's current result set into a list of dicts keyed
    by the procedure's own output column names. An unresolved identity
    produces no result set at all (``cursor.description is None``,
    matching every *ForOwner reader's own recorded RETURN-before-any-
    SELECT shape for that case) -- that is a normal, silent empty read,
    never an error."""

    if cursor.description is None:
        return []
    columns = [column[0] for column in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def _call_reader(connection, procedure_name, user_key):
    """Call one core-reader procedure on the caller-supplied connection.
    Never manages the connection's lifetime, transaction state, or
    configuration -- the caller owns all of that."""

    cursor = connection.cursor()
    fallback_started_at_utc = _read_clock(cursor)
    cursor.execute(f"EXEC dbo.{procedure_name} @UserKey = ?;", (user_key,))
    raw_rows = _rows_as_dicts(cursor)
    fallback_ended_at_utc = _read_clock(cursor)

    rows = []
    read_started_at_utc = None
    read_ended_at_utc = None
    for raw_row in raw_rows:
        row = dict(raw_row)
        row_started = row.pop("read_started_at_utc", None)
        row_ended = row.pop("read_ended_at_utc", None)
        if read_started_at_utc is None:
            read_started_at_utc = row_started
        read_ended_at_utc = row_ended
        rows.append(row)

    if not rows:
        read_started_at_utc = fallback_started_at_utc
        read_ended_at_utc = fallback_ended_at_utc

    return {
        "rows": rows,
        "read_started_at_utc": read_started_at_utc,
        "read_ended_at_utc": read_ended_at_utc,
    }


def _make_reader(procedure_name):
    """Build one named, single-purpose reader function for exactly one
    procedure. A factory rather than ten hand-copied bodies, so every
    reader is byte-identical in shape and only the procedure name
    varies -- the same discipline the SQL migration itself follows with
    its repeated identity-resolution header."""

    def reader(connection, user_key):
        return _call_reader(connection, procedure_name, user_key)

    reader.__name__ = "read_" + procedure_name
    reader.procedure_name = procedure_name
    return reader


# ---------------------------------------------------------------------
# One reader per procedure the migration created. Names mirror the SQL
# procedure names (minus the usp_ReadAccountExport.../ForOwner
# wrapping) in snake_case.
# ---------------------------------------------------------------------

read_account = _make_reader("usp_ReadAccountExportAccountForOwner")
read_profile = _make_reader("usp_ReadAccountExportProfileForOwner")

read_career_chapter = _make_reader("usp_ReadAccountExportCareerChapterForOwner")
read_career_experience = _make_reader("usp_ReadAccountExportCareerExperienceForOwner")
read_career_education = _make_reader("usp_ReadAccountExportCareerEducationForOwner")
read_career_credential = _make_reader("usp_ReadAccountExportCareerCredentialForOwner")
read_career_project = _make_reader("usp_ReadAccountExportCareerProjectForOwner")
read_career_achievement = _make_reader("usp_ReadAccountExportCareerAchievementForOwner")
read_career_skill = _make_reader("usp_ReadAccountExportCareerSkillForOwner")
read_career_timeline_event = _make_reader("usp_ReadAccountExportCareerTimelineEventForOwner")

read_capture = _make_reader("usp_ReadAccountExportCaptureForOwner")
read_capture_revision = _make_reader("usp_ReadAccountExportCaptureRevisionForOwner")

read_moment = _make_reader("usp_ReadAccountExportMomentForOwner")
read_moment_version = _make_reader("usp_ReadAccountExportMomentVersionForOwner")
read_moment_source = _make_reader("usp_ReadAccountExportMomentSourceForOwner")
read_moment_placement = _make_reader("usp_ReadAccountExportMomentPlacementForOwner")


def _reader_entry(function, schema_id, fields):
    return {
        "procedure": function.procedure_name,
        "function": function,
        "schema_id": schema_id,
        "fields": tuple(fields),
    }


# The two trailing transport columns every reader returns on each
# content row (see module docstring). Appended to every "fields" tuple
# below so DOMAINS matches the actual SQL output column list exactly,
# in order -- the same property tests/test_settings_export_core_readers.py
# pins against the migration's own SELECT lists.
_READ_WINDOW_FIELDS = ("read_started_at_utc", "read_ended_at_utc")


# ---------------------------------------------------------------------
# DOMAINS: the single source of truth for every C0 V1 domain-matrix row.
# C3+ must render domain truth from this dict, never a second,
# hand-maintained list.
# ---------------------------------------------------------------------

DOMAINS = {
    "account": {
        "disposition": "included",
        "reason": None,
        "readers": (
            _reader_entry(
                read_account,
                "peerslate.account_export.account.account.v1",
                (
                    "display_name", "email", "auth_provider", "profile_image_url",
                    "timezone_name", "user_role", "created_at_utc", "last_seen_at_utc",
                    "updated_at_utc",
                )
                + _READ_WINDOW_FIELDS,
            ),
        ),
    },
    "profile": {
        "disposition": "included",
        "reason": None,
        "readers": (
            _reader_entry(
                read_profile,
                "peerslate.account_export.profile.profile.v1",
                (
                    "profile_slug", "display_name", "headline", "bio", "location_text",
                    "visibility", "created_at_utc", "updated_at_utc",
                )
                + _READ_WINDOW_FIELDS,
            ),
        ),
    },
    "living_resume": {
        "disposition": "included",
        "reason": None,
        "readers": (
            _reader_entry(
                read_career_chapter,
                "peerslate.account_export.living_resume.career_chapter.v1",
                (
                    "chapter_key", "chapter_type", "title", "organization_name", "location_text",
                    "summary", "original_member_wording", "approved_wording", "start_date", "end_date",
                    "date_precision", "visibility", "approval_status", "publication_status", "featured",
                    "display_order", "approved_at_utc", "created_at_utc", "updated_at_utc",
                )
                + _READ_WINDOW_FIELDS,
            ),
            _reader_entry(
                read_career_experience,
                "peerslate.account_export.living_resume.career_experience.v1",
                ("chapter_key", "role_title", "employer_name", "employment_type", "current_role")
                + _READ_WINDOW_FIELDS,
            ),
            _reader_entry(
                read_career_education,
                "peerslate.account_export.living_resume.career_education.v1",
                (
                    "chapter_key", "institution_name", "degree_name", "field_of_study",
                    "education_status", "grade_text",
                )
                + _READ_WINDOW_FIELDS,
            ),
            _reader_entry(
                read_career_credential,
                "peerslate.account_export.living_resume.career_credential.v1",
                (
                    "chapter_key", "credential_name", "issuer_name", "credential_identifier",
                    "issue_date", "expiration_date", "verification_url",
                )
                + _READ_WINDOW_FIELDS,
            ),
            _reader_entry(
                read_career_project,
                "peerslate.account_export.living_resume.career_project.v1",
                ("chapter_key", "project_name", "project_role", "project_status", "project_url")
                + _READ_WINDOW_FIELDS,
            ),
            _reader_entry(
                read_career_achievement,
                "peerslate.account_export.living_resume.career_achievement.v1",
                (
                    "achievement_key", "chapter_key", "original_member_wording", "approved_wording",
                    "metric_value", "metric_label", "visibility", "approval_status", "featured",
                    "display_order", "approved_at_utc", "created_at_utc", "updated_at_utc",
                )
                + _READ_WINDOW_FIELDS,
            ),
            _reader_entry(
                read_career_skill,
                "peerslate.account_export.living_resume.career_skill.v1",
                (
                    "skill_key", "skill_name", "skill_summary", "visibility", "approval_status",
                    "featured", "display_order", "created_at_utc", "updated_at_utc",
                )
                + _READ_WINDOW_FIELDS,
            ),
            _reader_entry(
                read_career_timeline_event,
                "peerslate.account_export.living_resume.career_timeline_event.v1",
                (
                    "timeline_event_key", "chapter_key", "event_label", "event_type", "start_date",
                    "end_date", "date_precision", "visibility", "approval_status",
                    "constellation_featured", "display_order", "created_at_utc", "updated_at_utc",
                )
                + _READ_WINDOW_FIELDS,
            ),
        ),
    },
    # -------------------------------------------------------------
    # career_skill_links (PS-PLAT-006): a Living Resume table this
    # package deliberately does NOT read. Rows reference
    # evidence_item_id, whose disclosure rules are undecided; recorded
    # here as its own entry (not silently folded into "living_resume")
    # so a future reader of this dict never has to guess whether the
    # omission was deliberate.
    # -------------------------------------------------------------
    "career_skill_links": {
        "disposition": "excluded",
        "reason": (
            "Deferred to a future evidence-decision package: rows reference "
            "evidence_item_id, whose disclosure rules (which evidence_items fields, "
            "if any, are safe to export) are undecided. Not read by this package."
        ),
        "readers": (),
    },
    # -------------------------------------------------------------
    # Every other C0 V1 domain-matrix row. This package builds no
    # reader for any of these; each still gets an explicit, truthful
    # disposition and reason -- drawn from
    # C0_ACCOUNT_EXPORT_ARCHITECTURE.md's own "V1 domain matrix" and
    # "Required truth boundary" text -- so a future reader of this dict
    # never has to guess whether an absence is deliberate or a bug.
    # "unavailable" is reserved for a domain whose source schema is not
    # yet applied or that is structurally unavailable to a server-side
    # export; every other not-yet-built domain is "excluded" (a future,
    # separately claimed reader).
    # -------------------------------------------------------------
    "profile_publication_foundation": {
        "disposition": "unavailable",
        "reason": "PS-PROFILE-002 is registered but unapplied in the generated production-schema record; no Profile-native publication source table exists yet.",
        "readers": (),
    },
    "own_publication_versions": {
        "disposition": "excluded",
        "reason": "C0 marks the owner's own entity_publication_versions rows includable only after contract revalidation; this package builds no reader for it. Joint entity_access_grants context is excluded outright per C0.",
        "readers": (),
    },
    "capture": {
        "disposition": "included",
        "reason": None,
        "readers": (
            _reader_entry(
                read_capture,
                "peerslate.account_export.capture.capture.v1",
                (
                    "capture_key", "capture_type", "body", "visibility", "status",
                    "created_at_utc", "updated_at_utc",
                )
                + _READ_WINDOW_FIELDS,
            ),
            _reader_entry(
                read_capture_revision,
                "peerslate.account_export.capture.capture_revision.v1",
                (
                    "revision_key", "capture_key", "revision_number", "body",
                    "correction_note", "corrected_at_utc",
                )
                + _READ_WINDOW_FIELDS,
            ),
        ),
    },
    "voice_photo": {
        "disposition": "excluded",
        "reason": (
            "PS-VOICE-001/PS-CAPTURE-MEDIA-001 are applied in production "
            "(docs/governance/PRODUCTION_SCHEMA_STATE.md), but every "
            "media/transcript/hash/blob column is PS-SETTINGS-EXPORT-004's "
            "defining boundary and is excluded from every domain that "
            "package built (capture, moment). Voice/photo metadata and "
            "transcripts are deferred to a future, separately claimed "
            "media/evidence-decision reader package; this package builds "
            "no reader for them."
        ),
        "readers": (),
    },
    "moment": {
        "disposition": "included",
        "reason": None,
        "readers": (
            _reader_entry(
                read_moment,
                "peerslate.account_export.moment.moment.v1",
                (
                    "moment_key", "visibility", "status", "current_version_number",
                    "confirmed_version_number", "confirmed_at_utc", "created_at_utc",
                    "updated_at_utc",
                )
                + _READ_WINDOW_FIELDS,
            ),
            _reader_entry(
                read_moment_version,
                "peerslate.account_export.moment.moment_version.v1",
                (
                    "moment_version_key", "moment_key", "version_number", "moment_kind",
                    "title", "occurred_on", "occurred_precision", "narrative",
                    "why_it_matters", "saved_at_utc",
                )
                + _READ_WINDOW_FIELDS,
            ),
            _reader_entry(
                read_moment_source,
                "peerslate.account_export.moment.moment_source.v1",
                (
                    "moment_source_key", "moment_key", "source_capture_key",
                    "source_revision_key", "source_revision_number", "source_state",
                    "source_deleted_at_utc", "created_at_utc",
                )
                + _READ_WINDOW_FIELDS,
            ),
            _reader_entry(
                read_moment_placement,
                "peerslate.account_export.moment.moment_placement.v1",
                (
                    "placement_key", "moment_key", "moment_version_number",
                    "placement_status", "created_at_utc", "reactivated_at_utc",
                    "removed_at_utc", "updated_at_utc",
                )
                + _READ_WINDOW_FIELDS,
            ),
        ),
    },
    "journal": {
        "disposition": "unavailable",
        "reason": "PS-JOURNAL-001 is registered but not applied; legacy journal-like records must not be assumed equivalent to Moments.",
        "readers": (),
    },
    "workshop_my_knowledge": {
        "disposition": "excluded",
        "reason": "C0 marks Workshop/My Knowledge includable only after current schema, owner-read, and use-disclosure dependencies are rechecked; this package builds no reader for it.",
        "readers": (),
    },
    "opportunity_slate": {
        "disposition": "excluded",
        "reason": "C0 marks Opportunity Slate includable with provenance for durable member records; this package builds no reader for it.",
        "readers": (),
    },
    "my_opportunities": {
        "disposition": "unavailable",
        "reason": "No current canonical export contract; do not conflate with Opportunity Slate.",
        "readers": (),
    },
    "community_authored_content": {
        "disposition": "excluded",
        "reason": "C0 requires strict redaction of other-member bodies, identities, media, reactions, lists, and relationship context before this domain can be included; this package builds no reader for it.",
        "readers": (),
    },
    "connection_preferences": {
        "disposition": "excluded",
        "reason": "C0 marks this includable with truthful dormant-behavior labeling; this package builds no reader for it.",
        "readers": (),
    },
    "connection_records": {
        "disposition": "excluded",
        "reason": "Joint/other-member connection, block, and report state awaits a separate relationship/privacy decision per C0.",
        "readers": (),
    },
    "notifications_inbox": {
        "disposition": "excluded",
        "reason": "Title/body/related_entity_id/metadata_json can carry other-member, joint, or entity-linked context; excluded pending a reviewed field allowlist per C0.",
        "readers": (),
    },
    "notification_preferences": {
        "disposition": "excluded",
        "reason": "C0 marks this includable after an owner-scoped/dormant field allowlist and truthful behavior labeling; this package builds no reader for it. Distinct from the excluded notifications inbox.",
        "readers": (),
    },
    "consent_history": {
        "disposition": "excluded",
        "reason": "C0 marks this includable in evidence-minimized form (excluding raw claims/excessive evidence); this package builds no reader for it.",
        "readers": (),
    },
    "audit_events": {
        "disposition": "excluded",
        "reason": "Security/audit disclosure needs a separate qualified decision per C0.",
        "readers": (),
    },
    "browser_local_interview_history": {
        "disposition": "unavailable",
        "reason": "A server-side export cannot gather browser-local history.",
        "readers": (),
    },
    "interview_telemetry": {
        "disposition": "excluded",
        "reason": "Operational telemetry is not a member-content export domain per C0.",
        "readers": (),
    },
    "ai_proposals": {
        "disposition": "excluded",
        "reason": "C0 marks this includable only by allowlist and noncanonical, excluding prompts/system instructions/raw telemetry/cache/provider-retained data; this package builds no reader for it.",
        "readers": (),
    },
    "ask_pete_public": {
        "disposition": "unavailable",
        "reason": "Public Ask Pete is not private account-export content.",
        "readers": (),
    },
    "ask_pete_direct": {
        "disposition": "excluded",
        "reason": "Contains third-party visitor questions/contact data that must never surface through a member export.",
        "readers": (),
    },
    "projects": {
        "disposition": "unavailable",
        "reason": "General Projects remains unavailable; career-project records are already covered by the living_resume domain's career_project reader (chapter_type = 'project').",
        "readers": (),
    },
    "home": {
        "disposition": "excluded",
        "reason": "Home is a projection over other domains, not its own source; export underlying canonical sources where included, never a Home projection copy, per C0.",
        "readers": (),
    },
    "file_evidence_metadata": {
        "disposition": "excluded",
        "reason": "C0 marks this includable as safe references only (excluding provider locators, raw bytes, Blob names, object keys, direct URLs, and credentials); this package builds no reader for it.",
        "readers": (),
    },
    "indexes_caches_provider_backups": {
        "disposition": "excluded",
        "reason": "Not canonical member-domain files; requires separate retention, backup/PITR, privacy, and security decisions per C0.",
        "readers": (),
    },
}


def iter_included_readers():
    """Yield (domain_code, reader_entry) for every reader across every
    included domain, in DOMAINS iteration order. A convenience for a
    future caller that wants to walk every real reader without knowing
    the domain shape in advance -- never used by this package itself
    (no worker or route calls this yet)."""

    for domain_code, domain in DOMAINS.items():
        if domain["disposition"] != "included":
            continue
        for reader_entry in domain["readers"]:
            yield domain_code, reader_entry
