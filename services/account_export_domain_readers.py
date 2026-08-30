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
PS-SETTINGS-EXPORT-004 (replacement package 2) added capture
(dbo.captures, dbo.capture_revisions) and moment (dbo.moments,
dbo.moment_versions, dbo.moment_sources, dbo.moment_placements) --
text truth only. Every content hash, checksum, media/photo/voice/blob/
file reference, transcript linkage, storage locator, and URL to stored
media is excluded from both domains' field lists (neither
dbo.captures/dbo.capture_revisions nor any of the four Moment tables
has such a column, so no row is incomplete for lack of one);
dbo.moment_placements' target_entity_id (a foreign key to
dbo.slate_entities, the Opportunity Slate destination) is also
excluded -- Opportunity Slate is a separate C0 matrix row with its own
future, separately claimed reader, and dbo.slate_entities is not one
of PS-SETTINGS-EXPORT-004's six claimed tables.

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

PS-SETTINGS-EXPORT-005 (replacement package 3, this update) adds
workshop_my_knowledge: dbo.knowledge_items and
dbo.knowledge_item_versions, re-validated against the applied
PS-WORKSHOP-001/PS-WORKSHOP-002 schema files at write time per C0's
own caveat for this row ("current schema, owner reads, and
use-disclosure dependencies must be rechecked"). Text truth only, the
same boundary as every prior package: neither table has a media/hash/
transcript column, and neither has a deleted_at_utc column of any kind
(PS-WORKSHOP-001's own deletion path is a plain hard DELETE, never a
soft-delete flag) -- dbo.knowledge_items' own archived_at_utc records a
real, undeleted item state and is exported as content, the same
"archived is not deleted" treatment PS-SETTINGS-EXPORT-004 already gave
dbo.captures.status = 'archived'. dbo.knowledge_item_versions is the
one table in this program whose version-history reader needed a
different owner-predicate shape than its siblings: unlike
dbo.capture_revisions/dbo.moment_versions, it independently carries its
own owner_profile_id column (required by its own composite foreign key
to dbo.knowledge_items), so its reader asserts the owner predicate on
BOTH sides of the parent join, the same defense in depth
PS-SETTINGS-EXPORT-004 applied to dbo.moment_sources/
dbo.moment_placements. dbo.knowledge_item_versions also has no opaque
key column of its own (unlike dbo.capture_revisions.revision_key or
dbo.moment_versions.moment_version_key); its exported identifying
tuple is (knowledge_item_key, version_number), already unique per
UQ_knowledge_item_versions_number, and no surrogate key is manufactured
for it.

dbo.knowledge_item_save_requests (PS-WORKSHOP-001's idempotency ledger
for one-step Save) is deliberately excluded, for the identical reason
dbo.career_skill_links is: it is recorded as its own named, excluded
DOMAINS entry ("workshop_knowledge_save_requests") rather than silently
folded into "workshop_my_knowledge" or omitted, so a future reader of
this dict never has to guess whether the omission was deliberate. It
carries only an owner-scoped replay key and the resulting
knowledge_item_id -- no title, wording, status, or other
member-authored fact -- so it is machinery, not knowledge content.
PS-WORKSHOP-002 added no table of its own (only a new procedure and a
revised admission predicate on an existing one), so there is no
PS-WORKSHOP-002 "confirmation-machinery table" to exclude here; the
confirmation facts this package exports (item_status,
confirmed_version_number, confirmed_at_utc) are dbo.knowledge_items
columns PS-WORKSHOP-001 itself created, in the same shape
PS-SETTINGS-EXPORT-004 already exported for dbo.moments. PS-WORKSHOP-003
and PS-WORKSHOP-004 were re-read before this package was written and
confirmed to add only procedures, never a column or table on either
claimed table, so the field lists below remain the accurate current
schema.

PS-SETTINGS-EXPORT-006 (replacement package 4, the FINAL content reader
of the 2026-08-29 topology, this update) flips opportunity_slate from
excluded to included: dbo.opportunity_slates, dbo.opportunity_saved_results,
dbo.opportunity_saved_qualifications, and dbo.opportunity_saved_evidence --
the four PS-OPPSLATE-003 (OS-4) tables that are the ONLY durable
Opportunity Slate records in this schema. All four of PS-OPPSLATE-001's
(OS-1/OS-2) tables, all four of PS-OPPSLATE-002's (OS-3) tables, and all
three of PS-OPPSLATE-004's ("the replacement" R1 shell) new tables were
read in full and confirmed EPHEMERAL -- cascade-deleted by the same
usp_PurgeExpiredOpportunityWorkingData/usp_DeleteOpportunityWorkingSessionForOwner
calls that purge working-session infrastructure -- and are therefore not
read by this package; see PS-SETTINGS-EXPORT-006_oppslate_reader.sql's own
header for the exact proof (the literal DELETE statements PS-OPPSLATE-004
issues against its own three new tables, joined back to the same
@ExpiredSessions table as every OS-1/OS-2/OS-3 table). This directly
overturned this package's own "expect" framing at write time -- the two
tables PS-OPPSLATE-004 was expected to make durable turned out to be
ephemeral once the schema was actually read, rather than assumed.

Directive-trimmed per the owner's later 2026-08-29 ruling, which SUPERSEDES
C0's "Included with provenance" disposition for this row: AI/model
provenance (model_name, prompt_contract_version, and -- a reversal
recorded by the independent review round -- saved_analysis_key, a
generation-run identifier squarely inside the directive category's
"Model names/ids" definition, whose member-readable export value is nil
because the run it names is ephemeral and already purged) is excluded
pending a separate review, alongside third-party posting/job text
(source_text, employer_text, covered_text -- every column carrying the
employer's own wording verbatim) and every response/evidence-linkage
column (response_kind, response_text, authored_via,
connected_evidence_title, connected_evidence_version, evidence_kind,
evidence_key, evidence_version, evidence_title, excerpt). What remains is
the member's own saved facts: opaque keys, ordinals, timestamps, the
member's own classification decisions, the application-computed (never
model-opinion) derived_status/citation_count accounting, and the plain
counts/hash the member's own save carries (evidence_considered_count,
qualification_count, input_fingerprint -- none of which is a name, id,
prompt, score, or evidence reference).
opportunity_saved_results.idempotency_key is also
excluded: the migration's own header calls it "the idempotency ledger,"
extending this program's established machinery-not-content precedent to a
column rather than a whole table. dbo.opportunity_saved_qualifications and
dbo.opportunity_saved_evidence carry no soft-delete column of any kind
(PS-OPPSLATE-003's own delete path, usp_DeleteOpportunitySavedSlateForOwner,
is a member-triggered hard delete of the whole slate).
dbo.opportunity_saved_evidence loses nearly all of its payload to the
third-party-text and evidence-link exclusions -- only ordinal and
clause_ordinal survive -- and this package still builds its reader for it
rather than reclassifying the whole domain as excluded, per the writer
brief's explicit instruction for a half-member-fact-half-excluded table;
recorded as an honest limitation, not hidden.

my_opportunities remains unavailable/excluded, re-verified rather than
assumed still correct: PS-MYOPP-001 (the only My Opportunities migration
applied) is its own "C2 shared-side canonical" foundation with, by its own
registry summary, "No member-side objects" -- there is no owner-scoped My
Opportunities table this or any future account-export reader could read,
so the existing reason (do not conflate with Opportunity Slate) remains
factual and is unchanged in substance.

PS-SETTINGS-EXPORT-007 (this update) flips voice_photo from excluded to
included: dbo.voice_media_sources, dbo.voice_transcription_attempts, and
dbo.voice_capture_links (PS-VOICE-001), plus dbo.capture_media_sources and
dbo.capture_media_links (PS-CAPTURE-MEDIA-001) -- the member's own Voice/
Photo capture facts and the member's own transcripts, executing the
owner's accepted "Paper 1" ruling. voice_photo's prior "excluded" reason
(recorded by PS-SETTINGS-EXPORT-004, preserved here for history rather
than silently deleted) was: "every media/transcript/hash/blob column is
PS-SETTINGS-EXPORT-004's defining boundary and is excluded from every
domain that package built (capture, moment). Voice/photo metadata and
transcripts are deferred to a future, separately claimed media/
evidence-decision reader package; this package builds no reader for
them." This package is that future package. Every blob locator (blob_name,
original_blob_name, derivative_blob_name), content digest (sha256_digest,
original_sha256_digest, derivative_sha256_digest), storage etag
(original_blob_etag, derivative_blob_etag), and provider reference
(provider_request_id) is hard-excluded, canaried by the paired
verification script; raw media bytes never live in SQL at all (both
source migrations' own headers: audio/photo bytes live only in private
Blob Storage). Disclosed machinery columns (not a directive category, an
extension of this program's existing idempotency-ledger precedent):
safe_error_code, scan_result, scan_completed_at_utc, and
deletion_capture_row_version (a cleanup claim token PS-CAPTURE-MEDIA-001's
own usp_DeleteCapture writes and usp_FinalizePhotoCaptureDeletion later
checks). Both source tables payload-null every content column when
state = 'deleted' (CK_voice_media_sources_live_payload,
CK_capture_media_sources_original_payload); every reader here filters
state <> 'deleted' accordingly, including the two link readers through
their own joined source. dbo.voice_transcription_attempts reads only
CONCLUDED attempts (state IN ('succeeded', 'failed'), equivalently
completed_at_utc IS NOT NULL) -- an in-flight (queued/processing) attempt
carries no content column at all per
CK_voice_transcription_attempts_result and is transient operational
status, not yet a durable member fact; a failed attempt still appears
(its lifecycle truth), only its safe_error_code is withheld. Every
concluded attempt is exported, not merely the one linked to a confirmed
capture: this is deliberately non-overlapping with
PS-SETTINGS-EXPORT-004's own capture.body (the member's confirmed,
possibly-edited final text), since provider_transcript is the member's
raw spoken words at the moment of that specific attempt.
dbo.voice_capture_links and dbo.capture_media_links both carry no opaque
key of their own; their exported identifying tuple is the joined
source's own source_key alone, already unique per
UQ_voice_capture_links_source/UQ_capture_media_links_source. Both link
tables' own capture_id is excluded outright, never resolved to
dbo.captures.capture_key: dbo.captures sits outside this package's
five-table scope, the identical boundary PS-SETTINGS-EXPORT-004's own
header drew for dbo.moment_placements.target_entity_id/
dbo.slate_entities.

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

read_knowledge_item = _make_reader("usp_ReadAccountExportKnowledgeItemForOwner")
read_knowledge_item_version = _make_reader("usp_ReadAccountExportKnowledgeItemVersionForOwner")

read_opportunity_slate = _make_reader("usp_ReadAccountExportOpportunitySlateForOwner")
read_opportunity_saved_result = _make_reader("usp_ReadAccountExportOpportunitySavedResultForOwner")
read_opportunity_saved_qualification = _make_reader("usp_ReadAccountExportOpportunitySavedQualificationForOwner")
read_opportunity_saved_evidence = _make_reader("usp_ReadAccountExportOpportunitySavedEvidenceForOwner")

read_voice_media_source = _make_reader("usp_ReadAccountExportVoiceMediaSourceForOwner")
read_voice_transcription_attempt = _make_reader("usp_ReadAccountExportVoiceTranscriptionAttemptForOwner")
read_voice_capture_link = _make_reader("usp_ReadAccountExportVoiceCaptureLinkForOwner")
read_capture_media_source = _make_reader("usp_ReadAccountExportCaptureMediaSourceForOwner")
read_capture_media_link = _make_reader("usp_ReadAccountExportCaptureMediaLinkForOwner")


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
        "disposition": "included",
        "reason": None,
        "readers": (
            _reader_entry(
                read_voice_media_source,
                "peerslate.account_export.voice_photo.voice_media_source.v1",
                (
                    "source_key", "content_type", "byte_length", "locale",
                    "client_duration_milliseconds", "verified_duration_milliseconds",
                    "state", "created_at_utc", "updated_at_utc",
                )
                + _READ_WINDOW_FIELDS,
            ),
            _reader_entry(
                read_voice_transcription_attempt,
                "peerslate.account_export.voice_photo.voice_transcription_attempt.v1",
                (
                    "source_key", "attempt_key", "attempt_number", "state",
                    "provider_transcript", "queued_at_utc", "started_at_utc",
                    "completed_at_utc",
                )
                + _READ_WINDOW_FIELDS,
            ),
            _reader_entry(
                read_voice_capture_link,
                "peerslate.account_export.voice_photo.voice_capture_link.v1",
                ("source_key", "attempt_key", "confirmed_at_utc")
                + _READ_WINDOW_FIELDS,
            ),
            _reader_entry(
                read_capture_media_source,
                "peerslate.account_export.voice_photo.capture_media_source.v1",
                (
                    "source_key", "source_type", "original_content_type",
                    "original_byte_length", "derivative_content_type",
                    "derivative_byte_length", "pixel_width", "pixel_height",
                    "state", "created_at_utc", "updated_at_utc",
                )
                + _READ_WINDOW_FIELDS,
            ),
            _reader_entry(
                read_capture_media_link,
                "peerslate.account_export.voice_photo.capture_media_link.v1",
                ("source_key", "confirmed_at_utc")
                + _READ_WINDOW_FIELDS,
            ),
        ),
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
        "disposition": "included",
        "reason": None,
        "readers": (
            _reader_entry(
                read_knowledge_item,
                "peerslate.account_export.workshop_my_knowledge.knowledge_item.v1",
                (
                    "knowledge_item_key", "item_status", "classification", "visibility",
                    "current_version_number", "confirmed_version_number", "confirmed_at_utc",
                    "archived_at_utc", "created_at_utc", "updated_at_utc",
                )
                + _READ_WINDOW_FIELDS,
            ),
            _reader_entry(
                read_knowledge_item_version,
                "peerslate.account_export.workshop_my_knowledge.knowledge_item_version.v1",
                (
                    "knowledge_item_key", "version_number", "title", "approved_wording",
                    "original_member_wording", "body_format", "authored_via", "saved_at_utc",
                )
                + _READ_WINDOW_FIELDS,
            ),
        ),
    },
    # -------------------------------------------------------------
    # knowledge_item_save_requests (PS-WORKSHOP-001): a Workshop table
    # this package deliberately does NOT read, for the identical reason
    # career_skill_links (PS-SETTINGS-EXPORT-003) and target_entity_id/
    # dbo.slate_entities (PS-SETTINGS-EXPORT-004) are recorded as their
    # own named entries -- an idempotency ledger (an owner-scoped replay
    # key and the resulting knowledge_item_id only), not member-authored
    # knowledge content. Recorded here as its own entry (not silently
    # folded into "workshop_my_knowledge") so a future reader of this
    # dict never has to guess whether the omission was deliberate.
    # -------------------------------------------------------------
    "workshop_knowledge_save_requests": {
        "disposition": "excluded",
        "reason": (
            "dbo.knowledge_item_save_requests is PS-WORKSHOP-001's idempotency ledger "
            "for one-step Save: an owner-scoped replay key and the resulting "
            "knowledge_item_id only, no title, wording, status, or other "
            "member-authored fact. It is machinery, not knowledge content; this "
            "package builds no reader for it."
        ),
        "readers": (),
    },
    "opportunity_slate": {
        "disposition": "included",
        "reason": None,
        "readers": (
            _reader_entry(
                read_opportunity_slate,
                "peerslate.account_export.opportunity_slate.opportunity_slate.v1",
                (
                    "slate_key", "visibility", "current_save_version_number",
                    "created_at_utc", "updated_at_utc",
                )
                + _READ_WINDOW_FIELDS,
            ),
            _reader_entry(
                read_opportunity_saved_result,
                "peerslate.account_export.opportunity_slate.opportunity_saved_result.v1",
                (
                    "slate_key", "saved_result_key", "save_version_number",
                    "source_version_number", "requirement_version_number",
                    "evidence_considered_count", "qualification_count", "input_fingerprint",
                    "saved_at_utc",
                )
                + _READ_WINDOW_FIELDS,
            ),
            _reader_entry(
                read_opportunity_saved_qualification,
                "peerslate.account_export.opportunity_slate.opportunity_saved_qualification.v1",
                (
                    "saved_result_key", "ordinal", "statement_class", "derived_status",
                    "citation_count",
                )
                + _READ_WINDOW_FIELDS,
            ),
            _reader_entry(
                read_opportunity_saved_evidence,
                "peerslate.account_export.opportunity_slate.opportunity_saved_evidence.v1",
                (
                    "saved_result_key", "saved_qualification_ordinal", "ordinal",
                    "clause_ordinal",
                )
                + _READ_WINDOW_FIELDS,
            ),
        ),
    },
    "my_opportunities": {
        "disposition": "unavailable",
        "reason": (
            "No current canonical export contract; do not conflate with Opportunity Slate. "
            "Re-verified for this package: PS-MYOPP-001 (the only applied My Opportunities "
            "migration) is its own shared-side canonical foundation with no member-owned "
            "table -- there is nothing owner-scoped here a reader could target."
        ),
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
