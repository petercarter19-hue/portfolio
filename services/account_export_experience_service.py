"""Route-layer experience service for one member's own account export (C3).

This module is the only thing between owner_routes.py and the three
member-facing procedures added by PS-SETTINGS-EXPORT-001. It exists so the
route layer never assembles SQL parameters, never sees a private artifact
reference, and never has a second place that could decide whose data an
export contains.

Boundaries this module enforces, from C0_ACCOUNT_EXPORT_ARCHITECTURE.md:

* Identity is always the caller-supplied server-derived ``user_key`` taken
  from ``identity.get_current_identity()``. No function here accepts a
  profile id, user id, email, or any other owner selector, so a route,
  form, query, header, cookie, or body value cannot influence whose export
  is read. The three procedures resolve ``@UserKey`` to the active profile
  themselves and filter every row by it.
* Unknown, malformed, foreign, not-yet-ready, and expired jobs are all
  reported the same way -- ``None`` -- so the route can answer one neutral
  404 without disclosing whether a job key exists, belongs to somebody
  else, or simply is not downloadable yet.
* ``load_download`` is the only path that touches the private artifact,
  and it returns verified bytes plus a safe filename. It never returns,
  logs, or renders ``final_artifact_reference``: that value is a private
  server-only locator, not a URL, and it stops here.
"""

from __future__ import annotations

import binascii
from uuid import UUID

from services.account_export_storage_service import (
    AccountExportStorageError,
    AccountExportStorageService,
)
from services.database_service import DatabaseServiceError, database_service

# The three member-facing procedures. The five worker procedures are
# deliberately absent: they are system-wide, take no @UserKey, and belong
# to the separate worker identity, so nothing reachable from a browser
# request may name them.
_REQUEST_PROCEDURE = "usp_RequestAccountExportForOwner"
_STATUS_PROCEDURE = "usp_GetAccountExportStatusForOwner"
_DOWNLOAD_PROCEDURE = "usp_GetAccountExportDownloadMetadataForOwner"

# The closed vocabulary dbo.account_export_jobs.CK_account_export_jobs_state
# already enforces. Anything outside it is treated as unusable rather than
# rendered, so a future state cannot leak to a member as raw text.
_KNOWN_STATES = frozenset({"queued", "running", "ready", "failed", "expired"})


class AccountExportExperienceError(Exception):
    """A content-free failure code for the route layer to map.

    Never carries a SQL message, artifact reference, object name, or any
    other member or infrastructure detail.
    """

    def __init__(self, code):
        super().__init__(code)
        self.code = code


def _coerce_job_key(value):
    """Return a canonical job key, or ``None`` when it is not one.

    A malformed job key is not an error the member needs explained: it is
    indistinguishable, by design, from a job that belongs to somebody
    else, so it returns ``None`` and the route answers the same 404.
    """

    if isinstance(value, UUID):
        return str(value)
    if not isinstance(value, str):
        return None
    candidate = value.strip()
    if not candidate:
        return None
    try:
        return str(UUID(candidate))
    except (ValueError, AttributeError, TypeError):
        return None


def _row_value(row, key):
    if not isinstance(row, dict):
        return None
    return row.get(key)


def _as_bool(value):
    return value is True or value == 1


def _iso(value):
    if value is None:
        return None
    isoformat = getattr(value, "isoformat", None)
    if callable(isoformat):
        return isoformat()
    return str(value)


def request_export(user_key):
    """Create or return this member's one active export job.

    The procedure itself decides between ``created`` and ``existing``
    under a lock, so a double-submit or a refresh cannot produce a second
    concurrent job for the same owner.
    """

    if not user_key:
        raise AccountExportExperienceError("identity_unavailable")

    try:
        row = database_service.first_row(
            _REQUEST_PROCEDURE, [("@UserKey", user_key)]
        )
    except DatabaseServiceError as error:
        raise AccountExportExperienceError("export_unavailable") from error

    job_key = _coerce_job_key(_row_value(row, "job_key"))
    if not job_key:
        # The procedure raises rather than returning an unusable row, so
        # this is an integrity failure, not a member-visible condition.
        raise AccountExportExperienceError("export_unavailable")

    outcome = _row_value(row, "outcome")
    return {
        "job_key": job_key,
        "outcome": outcome if outcome in {"created", "existing"} else "existing",
    }


def load_status(user_key, job_key):
    """Return a safe view of one job this member owns, or ``None``.

    ``None`` covers unknown, malformed, foreign, and no-longer-authorized
    jobs identically. A member's own retained expired job is a real,
    truthful status and is returned.
    """

    if not user_key:
        return None
    canonical_job_key = _coerce_job_key(job_key)
    if not canonical_job_key:
        return None

    try:
        row = database_service.first_row(
            _STATUS_PROCEDURE,
            [("@UserKey", user_key), ("@JobKey", canonical_job_key)],
        )
    except DatabaseServiceError as error:
        raise AccountExportExperienceError("export_unavailable") from error

    if not row:
        return None

    state = _row_value(row, "state")
    if state not in _KNOWN_STATES:
        return None

    # compressed_size_bytes is the member's own archive size and is safe
    # to show. failure_code is a closed internal vocabulary, so it is
    # reported as a boolean the template turns into plain language rather
    # than rendered raw.
    size = _row_value(row, "compressed_size_bytes")
    try:
        size = int(size) if size is not None else None
    except (TypeError, ValueError):
        size = None

    return {
        "job_key": canonical_job_key,
        "state": state,
        "requested_at_utc": _iso(_row_value(row, "requested_at_utc")),
        "completed_at_utc": _iso(_row_value(row, "completed_at_utc")),
        "ready_expires_at_utc": _iso(_row_value(row, "ready_expires_at_utc")),
        "download_available": _as_bool(_row_value(row, "download_available")),
        "failed": state == "failed",
        "compressed_size_bytes": size,
    }


def download_filename(job_key):
    """A stable, member-safe filename built only from the opaque job key."""

    canonical = _coerce_job_key(job_key)
    if not canonical:
        raise AccountExportExperienceError("export_unavailable")
    return "peerslate-export-%s.zip" % canonical


def load_download(user_key, job_key, storage=None):
    """Return verified archive bytes for this member's own ready job.

    Returns ``None`` for every job that must not be downloadable --
    unknown, malformed, foreign, queued, running, failed, or past its
    expiry -- because the procedure returns no row for any of them. The
    caller answers one neutral 404 for all of these alike.

    The bytes are verified against the SHA-256 committed to the job
    ledger at promotion time before they are returned, so a mismatched or
    replaced object fails closed instead of reaching the member.
    """

    if not user_key:
        return None
    canonical_job_key = _coerce_job_key(job_key)
    if not canonical_job_key:
        return None

    try:
        row = database_service.first_row(
            _DOWNLOAD_PROCEDURE,
            [("@UserKey", user_key), ("@JobKey", canonical_job_key)],
        )
    except DatabaseServiceError as error:
        raise AccountExportExperienceError("export_unavailable") from error

    if not row:
        return None

    expected_sha256 = _row_value(row, "final_artifact_sha256")
    expected_size = _row_value(row, "compressed_size_bytes")
    if isinstance(expected_sha256, (bytes, bytearray)):
        expected_sha256 = binascii.hexlify(expected_sha256).decode("ascii")
    if isinstance(expected_sha256, str):
        expected_sha256 = expected_sha256.strip().lower() or None
    else:
        expected_sha256 = None
    try:
        expected_size = int(expected_size) if expected_size is not None else None
    except (TypeError, ValueError):
        expected_size = None

    adapter = storage or AccountExportStorageService()
    try:
        data = adapter.read_final(
            canonical_job_key,
            expected_sha256=expected_sha256,
            expected_size=expected_size,
        )
    except AccountExportStorageError as error:
        # Storage failures are never described to the member: an object
        # name, container, or provider message must not reach a browser.
        raise AccountExportExperienceError("export_unavailable") from error

    return {
        "data": data,
        "filename": download_filename(canonical_job_key),
        "compressed_size_bytes": len(data),
    }


# Human-readable labels for the DOMAINS keys. This is presentation only:
# it never decides what an export contains, and a domain missing from this
# map still appears, under its own key, rather than being silently dropped.
_DOMAIN_LABELS = {
    "account": "Account and identity",
    "profile": "Profile",
    "living_resume": "Living resume",
    "career_skill_links": "Skills evidence",
    "capture": "Captures",
    "voice_photo": "Voice and photo",
    "moment": "Moments",
    "workshop_my_knowledge": "Workshop and My Knowledge",
    "opportunity_slate": "Opportunity Slate",
    "connection_preferences": "Connection preferences",
    "notification_preferences": "Notification preferences",
    "consent_history": "Consent history",
    "own_publication_versions": "Your publication versions",
    "workshop_knowledge_save_requests": "Workshop save requests",
    "community_authored_content": "Community posts you wrote",
    "connection_records": "Connections",
    "notifications_inbox": "Notifications inbox",
    "audit_events": "Audit history",
    "interview_telemetry": "Interview telemetry",
    "ai_proposals": "AI proposals",
    "ask_pete_direct": "Ask Pete messages",
    "home": "Home",
    "file_evidence_metadata": "File evidence details",
    "indexes_caches_provider_backups": "Indexes, caches and backups",
    "profile_publication_foundation": "Profile publication",
    "journal": "Journal",
    "my_opportunities": "My Opportunities",
    "browser_local_interview_history": "Interview history stored in your browser",
    "ask_pete_public": "Public Ask Pete",
    "projects": "Projects",
}


# Plain-language explanations for the domains an export does NOT include.
# Presentation only, exactly like _DOMAIN_LABELS above: DOMAINS remains the
# single source of truth for what an export contains and why, and nothing
# here can add, remove, or recategorise a domain. Each sentence must claim
# no more than the ledger's own reason does. A domain absent from this map
# still renders -- with the ledger's verbatim reason -- so an unmapped
# domain shows the truth rather than hiding it, and a coverage test turns
# a missing mapping into a loud failure instead of quiet jargon.
_DOMAIN_REASONS = {
    "profile_publication_foundation": (
        "Profile publishing isn't built yet, so there's nothing here to include."
    ),
    "own_publication_versions": (
        "Nothing has ever been published through this part of PeerSlate, so "
        "there's "
        "nothing here to include."
    ),
    "journal": (
        "Journal isn't in place yet, and older journal-like records can't "
        "safely be treated as Moments, so nothing is included here."
    ),
    "workshop_knowledge_save_requests": (
        "This is an internal bookkeeping record that holds no title, wording, "
        "or anything else you wrote, so it isn't part of your export."
    ),
    "my_opportunities": (
        "My Opportunities holds nothing that belongs specifically to you yet, "
        "so there's nothing here to include."
    ),
    "community_authored_content": (
        "Your community posts aren't included yet because we can't yet "
        "separate your words from other members' words and context; we plan "
        "a future update that includes your own words only."
    ),
    "connection_records": (
        "Your connections, blocks and reports involve other members too, so "
        "they're on hold until we've decided whether and how they can be "
        "included without exposing anyone else."
    ),
    "notifications_inbox": (
        "Your notifications can mention other members and other content, so "
        "they're on hold until we've reviewed exactly which parts are safe "
        "to include."
    ),
    "audit_events": (
        "Security and audit history needs a separate review before it can be "
        "shared, so it isn't included yet."
    ),
    "browser_local_interview_history": (
        "This history is kept only in your own browser, so a download built "
        "on our servers can't reach it."
    ),
    "interview_telemetry": (
        "This is operational data about how the service runs, rather than "
        "something you created, so it isn't part of your export."
    ),
    "ai_proposals": (
        "Anything you actually kept from an AI suggestion is already included "
        "with whatever it became, such as a chapter, a skill, a Workshop "
        "item, or another record of yours, so the suggestion record itself "
        "would add nothing."
    ),
    "ask_pete_public": (
        "Public Ask Pete content isn't private account data, so it isn't "
        "part of your export."
    ),
    "ask_pete_direct": (
        "These messages hold questions and contact details belonging to "
        "other people, so they're never included in a member download."
    ),
    "projects": (
        "Projects on your career timeline are already included with your "
        "living resume, and there's no separate Projects area to export."
    ),
    "home": (
        "Home is a view built from your other data, so your export includes "
        "the original records, where they're included, instead of a copy of "
        "the Home screen."
    ),
    "file_evidence_metadata": (
        "File evidence details aren't included yet; a rule now sets exactly "
        "what may be shared here, and it will apply when this is built."
    ),
    "indexes_caches_provider_backups": (
        "These are internal indexes, caches and backups rather than "
        "your own files, so they need separate decisions before anything "
        "could be shared."
    ),
}

# F1 drift guard: each mapped sentence is pinned to the EXACT ledger reason
# it paraphrases, by digest. If a ledger reason changes -- an owner ruling
# shifts, a domain's status hardens -- the pin breaks the suite and forces
# the member sentence to be re-worded against the new truth, instead of the
# old paraphrase silently outliving the reason it described. This is the
# second copy the single-source rule worries about, reduced to a hash: it
# can drift-DETECT but never drift-say anything to a member.
_DOMAIN_REASON_SOURCE_DIGESTS = {
    "ai_proposals": "45f32a640f68ee2e11ef5fca3d9471e5e428a531be4c7e5dfe19c30fd4262167",
    "ask_pete_direct": "f8dcc1bc533413a3beeadedc58d90748f08ec66bcb750dd5afed854c7a9e9d9a",
    "ask_pete_public": "88497f626c1dd274403b98b78c5f1bf0c1b1d4fd0aee587def9ed8954255dfbc",
    "audit_events": "c17d5433c13c88da97830bd5ce3e5867e7dabd9934e6f7eb99ee1b458a512dfc",
    "browser_local_interview_history": "2ed8c4f0af645d0e05a5d526f086dee9e3665f7a0f26c430a0dd8d8bef4c763e",
    "community_authored_content": "b9536d2052ac0324213e0729db57a7903b3f39849d3a36e0f9704ba648c1ca48",
    "connection_records": "8e0237cfc80306e06b59d55ed249f9479531a9aa4bae3affc12a841258957f7d",
    "file_evidence_metadata": "58f85468f918aaa245969e0a50140a65ed70f61fe719f1761fc5b25a7893a869",
    "home": "7b9279bfcb23613954b62facd0ea82aeff57915a0929f203ef64c8f47c9a255c",
    "indexes_caches_provider_backups": "f9e86fc67578d207f774045804129131ab421347e9b3b7b62ae5349f7107b7f0",
    "interview_telemetry": "62ef21547d32a2e482da9a53caaad2d8b1028fa9c47ee15df8b99aadb54ac219",
    "journal": "9e1fb70a7de8b40586b7038bc4a4bc9281ae4eeb75e6f76cbb00b27783bb6dc9",
    "my_opportunities": "b3dfff9abdf46b8ecadc6d5bee9ec65ce606713bbd5ea6c8d685cc29bf960248",
    "notifications_inbox": "c4113cabe69e2b18a8152427142a6ebe6c4304d093eb582c340dc8eae3c5145d",
    "own_publication_versions": "418d3808b77533d1c06bfe3f1552093a945608a6aa1b9981f7715fc6b58908b7",
    "profile_publication_foundation": "5b7d04efea5df29018b0911a5588ae9b848373fb5f5f9747de6d37c199c40d4b",
    "projects": "a4f4b7757937146b9719ca0144cd2c51ed2f9cc380f87872908741b1ab22280f",
    "workshop_knowledge_save_requests": "836854dc0662b4fc10ae5c270b459d561836597d6e66653cff4534bf9a09c564",
}


def domain_summary():
    """Render domain truth for the screen, straight from DOMAINS.

    services/account_export_domain_readers.py states that DOMAINS is the
    single source of truth C3+ must read from, "never a second,
    hand-maintained list". So this walks DOMAINS itself: if a domain's
    disposition or reason changes there, this screen changes with it, and
    a newly added domain cannot be quietly missing from what a member is
    told.

    Returned dispositions keep the ledger's own closed vocabulary --
    included, excluded, unavailable -- so the template never has to
    invent a fourth category. Every not-included domain carries a reason:
    the plain-language member sentence when one is mapped (pinned by
    digest to the exact ledger reason it paraphrases), and the ledger's
    verbatim reason when none is.
    """

    from services.account_export_domain_readers import DOMAINS

    included, not_included = [], []
    for key in sorted(DOMAINS):
        entry = DOMAINS[key]
        row = {
            "key": key,
            "label": _DOMAIN_LABELS.get(key, key.replace("_", " ")),
            "disposition": entry.get("disposition"),
            # The mapped plain-language sentence when one exists; the
            # ledger's verbatim reason when one does not. .get(key, default)
            # rather than `or`, so even an intentionally-empty mapping would
            # surface rather than silently falling through.
            "reason": _DOMAIN_REASONS.get(key, entry.get("reason")),
        }
        if row["disposition"] == "included":
            included.append(row)
        else:
            not_included.append(row)
    return {
        "included": included,
        "not_included": not_included,
        "included_count": len(included),
        "total_count": len(included) + len(not_included),
    }
