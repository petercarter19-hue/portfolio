"""Opportunity Slate ephemeral working session — PS-OPPSLATE-001, slices
OS-1 and OS-2.

Package: docs/initiatives/PS-OPPORTUNITY-SLATE-001. Controlling contract:
01_ARCHITECTURE_AND_IMPLEMENTATION_HANDOFF.md sections 8 (data model),
9 (route/service contract), 11 (security/privacy), and 16 (slices OS-1/OS-2).

This module owns the signed-in member's pre-save workbench: the working
session, the employer source and its append-only captured versions (OS-1),
and — added by OS-2 — the AI proposals made about that source and the
member's decisions on them: extraction-concern reviews, the proposed
requirement set, and per-statement reclassification and clarification.

**No AI call happens anywhere in this module.** It stores proposals; it never
makes one. The single AI seam for this room is
``services/opportunity_analysis_service.py``, which owns every prompt
contract, every validator, and the only Anthropic client. Nothing here
imports that module either — the proposals arrive as plain validated data
from the route layer — so persistence cannot reach the provider by any path.
Alignment analysis is OS-3 and does not exist yet.

Three data classes stay apart in the schema and in the views below (handoff
section 1): the employer's captured wording, the member's own corrections and
decisions, and the AI proposals. A proposal column is never written over a
member column and neither is ever written over the employer's original.

**Nothing here is a saved artifact.** A working session is infrastructure
(handoff section 1): never listed, never exported, never projected, and
bounded by ``expires_at_utc``. Expiry is enforced twice — the migration's
read procedure refuses an expired row, and
:meth:`OpportunitySlateService.get_working_session_for_owner` re-checks the
returned timestamp before handing anything back, so a clock skew or a
future procedure edit cannot quietly resurrect one. Physical destruction
runs through ``usp_PurgeExpiredOpportunityWorkingData``, which the room
route invokes opportunistically for the requesting owner.

**Anonymous mode never reaches this module.** Handoff section 18's public
session holds its state in a signed client token and touches no database
procedure. The one thing both modes share is :func:`validate_source_text`
— a single hard input cap, applied identically to a signed-in member and an
anonymous visitor, so the public boundary cannot be the lenient one.

Row discipline, error codes, ``rowversion`` optimistic concurrency, and the
idempotent-create guard are all mirrored from
``services/knowledge_service.py``. The small shared helpers
(``utf16_length``, ``_require_exact_fields``, ``_version_token``) are
re-implemented here rather than imported, following that module's own
precedent, so this file has no edit-time dependency on another package's
reserved file.
"""

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from services.database_service import database_service


# Hard server-side cap on pasted/typed employer wording, in UTF-16 code
# units. Handoff section 18 safeguard 2 requires this bound on every input
# in BOTH modes; the migration's
# CK_opportunity_source_versions_original_length CHECK enforces exactly the
# same number, so a malformed request is rejected here, before any database
# round trip, with the limit the database itself would apply.
MAX_SOURCE_TEXT_UNITS = 20000

# How long an idle working session stays reachable (handoff section 1's
# proposed 48 hours). Passed to the procedure rather than hardcoded there,
# and re-extended on every write, so "idle" really means idle.
WORKING_SESSION_TTL_HOURS = 48

MAX_IDEMPOTENCY_KEY_UNITS = 200

CAPTURE_METHODS = frozenset({"pasted", "dictated", "uploaded", "imported"})
# Slice OS-1 only ever writes "pasted": dictation is OS-5, upload and
# import are OS-6. The full enum is the contract, not the current surface.
OS1_CAPTURE_METHODS = frozenset({"pasted"})
# Slice OS-6 adds the two guarded capture paths this build now accepts:
# "uploaded" (services/opportunity_source_intake_service.py's document
# extraction) and "imported" (its SSRF-guarded public-link fetch). Both
# call this same save path with pre-extracted, already-capped plain text —
# neither capture method changes anything about how a version is stored.
# "dictated" stays out of this set on purpose: it is slice OS-5's own scope
# and this branch does not carry that slice's routes.
OS6_CAPTURE_METHODS = OS1_CAPTURE_METHODS | {"uploaded", "imported"}

WORKBENCH_STATES = frozenset(
    {
        "role_intake",
        "review_source",
        "source_confirmed",
        # Slice OS-2 adds the two states checkpoint 2 lives between. There is
        # deliberately no analysis or alignment state here: the analysis
        # engine is OS-3, and a state this schema cannot honestly reach is a
        # state it must not carry.
        "review_requirements",
        "requirements_confirmed",
    }
)

# Slice OS-2. A member's decision about one AI-proposed extraction concern.
# "pending" is the state every proposal starts in; the member is the only
# thing that moves it.
CONCERN_RESOLUTIONS = frozenset({"pending", "applied", "dismissed"})

# The four statement classes, as handoff section 10 fixes them. Required,
# Preferred, Responsibilities, and Informational statements stay four separate
# groups on the screen (locked rule, handoff section 14-M14).
STATEMENT_CLASSES = frozenset(
    {
        "required_qualification",
        "preferred_qualification",
        "responsibility",
        "informational_statement",
    }
)

MAX_CLARIFICATION_UNITS = 2000
MAX_STATEMENT_TEXT_UNITS = 1200
MAX_EXPLANATION_UNITS = 400
MAX_STRUCTURE_JSON_UNITS = 4000
MAX_CONCERN_REASON_UNITS = 240
MAX_CONCERN_QUOTE_UNITS = 600
MAX_MODEL_NAME_UNITS = 100
MAX_PROMPT_CONTRACT_UNITS = 60

_VERSION_TOKEN = re.compile(r"^[0-9a-fA-F]{16}$")

GET_ROW_FIELDS = frozenset(
    {
        "working_session_key",
        "workbench_state",
        "expires_at_utc",
        "session_row_version",
        "source_key",
        "current_version_number",
        "confirmed_version_number",
        "confirmed_at_utc",
        "source_row_version",
        "capture_method",
        "original_text",
        "member_corrected_text",
        "corrected_at_utc",
        "captured_at_utc",
    }
)
SAVE_ROW_FIELDS = frozenset(
    {
        "outcome",
        "working_session_key",
        "source_key",
        "version_number",
        "workbench_state",
        "session_row_version",
        "source_row_version",
    }
)
CORRECT_ROW_FIELDS = frozenset({"outcome", "source_row_version", "version_number"})
CONFIRM_ROW_FIELDS = frozenset(
    {"outcome", "source_row_version", "confirmed_version_number"}
)
DELETE_ROW_FIELDS = frozenset({"outcome", "deleted_version_count"})
PURGE_ROW_FIELDS = frozenset({"purged_session_count", "purged_version_count"})

# Slice OS-2 row shapes.
REVIEW_ROW_FIELDS = frozenset(
    {
        "review_key",
        "source_version_number",
        "model_name",
        "prompt_contract_version",
        "concern_count",
        "reviewed_at_utc",
    }
)
CONCERN_ROW_FIELDS = frozenset(
    {
        "concern_key",
        "span_start",
        "span_length",
        "quoted_text",
        "concern_reason",
        "member_resolution",
        "member_corrected_text",
        "resolved_at_utc",
        "concern_row_version",
    }
)
SAVE_REVIEW_ROW_FIELDS = frozenset({"outcome", "review_key", "concern_count"})
RESOLVE_ROW_FIELDS = frozenset({"outcome", "source_row_version", "member_resolution"})
REQUIREMENT_SET_ROW_FIELDS = frozenset(
    {
        "requirement_set_key",
        "set_row_version",
        "version_number",
        "source_version_number",
        "model_name",
        "prompt_contract_version",
        "proposed_at_utc",
        "confirmed_version_number",
        "confirmed_at_utc",
    }
)
STATEMENT_ROW_FIELDS = frozenset(
    {
        "statement_key",
        "ordinal",
        "span_start",
        "span_length",
        "employer_text",
        "proposed_class",
        "proposed_explanation",
        "proposed_structure_json",
        "member_class",
        "member_clarification",
        "member_updated_at_utc",
        "statement_row_version",
    }
)
SAVE_PROPOSAL_ROW_FIELDS = frozenset(
    {"outcome", "requirement_set_key", "version_number", "statement_count"}
)
CORRECT_STATEMENT_ROW_FIELDS = frozenset(
    {"outcome", "statement_row_version", "member_class"}
)
CONFIRM_REQUIREMENTS_ROW_FIELDS = frozenset(
    {"outcome", "set_row_version", "confirmed_version_number"}
)

# Slice OS-3 row shapes.
EVIDENCE_ROW_FIELDS = frozenset(
    {
        "evidence_key",
        "evidence_version",
        "evidence_title",
        "evidence_body",
        "evidence_updated_at_utc",
    }
)
ANALYSIS_ROW_FIELDS = frozenset(
    {
        "analysis_key",
        "analysis_row_version",
        "source_version_number",
        "requirement_version_number",
        "model_name",
        "prompt_contract_version",
        "evidence_considered_count",
        "qualification_count",
        "analyzed_at_utc",
    }
)
ANALYSIS_STATEMENT_ROW_FIELDS = frozenset(
    {"statement_key", "ordinal", "derived_status", "citation_count"}
)
ANALYSIS_CITATION_ROW_FIELDS = frozenset(
    {
        "statement_key",
        "ordinal",
        "clause_ordinal",
        "covered_text",
        "evidence_kind",
        "evidence_key",
        "evidence_version",
        "evidence_title",
        "excerpt",
    }
)
RESPONSE_ROW_FIELDS = frozenset(
    {
        "statement_key",
        "response_key",
        "response_row_version",
        "response_kind",
        "response_text",
        "authored_via",
        "connected_evidence_kind",
        "connected_evidence_key",
        "connected_evidence_version",
        "connected_evidence_title",
        "updated_at_utc",
    }
)
SAVE_ANALYSIS_ROW_FIELDS = frozenset(
    {"outcome", "analysis_key", "qualification_count"}
)
SAVE_RESPONSE_ROW_FIELDS = frozenset({"outcome", "response_key", "response_kind"})

# Slice OS-3. The three named per-statement states image 04 draws, and the
# whole of the qualification accounting. Not an order, not a scale, and not a
# score: nothing in this module ever sums, averages, ranks, or weights them.
ALIGNMENT_STATUSES = frozenset(
    {"supported", "partially_supported", "not_enough_information"}
)
RESPONSE_KINDS = frozenset(
    {"tell_more", "connect_evidence", "real_example", "confirm_not_have", "skip"}
)
AUTHORED_VIA_VALUES = frozenset({"typed", "spoken"})
EVIDENCE_KINDS = frozenset({"knowledge_item", "moment"})

MAX_EVIDENCE_ITEMS = 24
MAX_EVIDENCE_TITLE_UNITS = 200
MAX_EVIDENCE_BODY_UNITS = 8000
MAX_COVERED_TEXT_UNITS = 200
MAX_EXCERPT_UNITS = 400
MAX_RESPONSE_TEXT_UNITS = 4000
MAX_ANALYSED_STATEMENTS = 40
MAX_CITATIONS_PER_STATEMENT = 24

_SAVE_OUTCOMES = frozenset({"success", "existing", "unchanged"})

# ---------------------------------------------------------------------------
# Slice OS-4 — the durable saved slate.
# ---------------------------------------------------------------------------
SLATE_ROW_FIELDS = frozenset(
    {
        "slate_key",
        "slate_row_version",
        "current_save_version_number",
        "slate_created_at_utc",
        "saved_result_key",
        "save_version_number",
        "source_version_number",
        "requirement_version_number",
        "saved_analysis_key",
        "source_text",
        "model_name",
        "prompt_contract_version",
        "evidence_considered_count",
        "qualification_count",
        "input_fingerprint",
        "saved_at_utc",
    }
)
SAVED_VERSION_ROW_FIELDS = frozenset(
    {
        "saved_result_key",
        "save_version_number",
        "source_version_number",
        "requirement_version_number",
        "qualification_count",
        "saved_at_utc",
    }
)
SAVED_QUALIFICATION_ROW_FIELDS = frozenset(
    {
        "qualification_id",
        "ordinal",
        "statement_class",
        "employer_text",
        "derived_status",
        "citation_count",
        "response_kind",
        "response_text",
        "authored_via",
        "connected_evidence_title",
        "connected_evidence_version",
    }
)
SAVED_EVIDENCE_ROW_FIELDS = frozenset(
    {
        "qualification_id",
        "ordinal",
        "clause_ordinal",
        "covered_text",
        "evidence_kind",
        "evidence_key",
        "evidence_version",
        "evidence_title",
        "excerpt",
    }
)
SAVED_CURRENCY_ROW_FIELDS = frozenset(
    {"evidence_kind", "evidence_key", "pinned_version", "current_version"}
)

# The evidence kinds whose CURRENT version this revision can actually resolve.
#
# 2026-08-04 independent review, finding F6. opportunity_saved_evidence's CHECK
# permits `moment` because handoff §17-Q2 plans for it, but the currency query
# resolves only against dbo.knowledge_items, so a saved slate citing a Moment
# would read permanently stale with no action able to clear it. That is the
# quiet kind of wrong, so it is refused loudly instead: a kind this revision
# cannot price is a structural error, not a display state. A slice that adds
# Moment grounding must extend BOTH this set and the procedure's currency
# join in the same change; neither works without the other.
SAVED_EVIDENCE_CURRENCY_KINDS = frozenset({"knowledge_item"})
SAVE_SLATE_ROW_FIELDS = frozenset(
    {
        "outcome",
        "slate_key",
        "saved_result_key",
        "save_version_number",
        "qualification_count",
    }
)
DELETE_SLATE_ROW_FIELDS = frozenset({"outcome", "deleted_result_count"})

# The full four-class enum, matching the migration's own CHECK. A saved
# snapshot records the class the analysis actually held; narrowing it here
# would refuse on read a row the database legitimately accepted (2026-08-04
# SQL gate).
SAVED_STATEMENT_CLASSES = STATEMENT_CLASSES
MAX_SAVED_VERSIONS_LISTED = 50

# The canonical input-digest format. Versioned in its own first line so a
# future change to what counts as an input is a NEW fingerprint rather than a
# silent reinterpretation of the old one: every stored fingerprint would then
# stop matching, which reads as "inputs changed" — conservative, honest, and
# never a false "still current".
#
# v2 (2026-08-04 independent review, finding F1) added ``content_digest``.
# v1 hashed only the two version NUMBERS and the evidence versions, and two
# ordinary member actions change a confirmed input without moving either
# number: correcting the captured source wording rewrites
# ``member_corrected_text`` in place, and correcting a requirement statement
# rewrites ``member_class`` in place. Both left a saved result reading
# "Current for these inputs" over wording the member had since changed. Under
# the copy model that is the expensive lie — the member is reading retained
# old text that the banner labels current — so the digest now covers the
# CONTENT of those inputs, not just their version numbers. Every fingerprint
# stored under v1 stops matching and reads as stale, which is the correct
# conservative fallout.
_FINGERPRINT_VERSION = "os4-input-fingerprint-v2"
_CONTENT_DIGEST_VERSION = "os4-input-content-v1"


def compute_content_digest(source_text, statement_signature):
    """The digest of the input CONTENT a saved result was computed from.

    Two facts, both of which a member can change in place without any version
    number moving:

      * the confirmed employer wording — the correction overlay when there is
        one, otherwise the captured original. This is the text the analysis
        was read from and the text the saved result copied.
      * the analysed statement set: for every statement the analysis actually
        covered, its ordinal, the class in force (the member's correction when
        they made one, otherwise PeerSlate's proposal), and the employer text.
        A reclassification that moves a statement into or out of the analysed
        set changes this signature, as does one that only relabels it.

    Deliberately computable from BOTH sides without a schema change, which is
    what makes it a fair comparison rather than a stored assertion: the live
    side reads the working session and the requirement set; the pinned side
    reads the snapshot's own copied ``source_text`` and saved qualifications,
    which carry exactly these three fields per statement.

    NOT covered, and named here so the omission is a decision rather than an
    oversight: ``member_clarification``. It is member context attached to a
    statement, it is not sent to any AI step (`_qualifications_for_analysis`
    passes ordinal, employer text and clause vocabulary only), and it is not
    part of what a saved result holds. Changing it cannot make a saved result
    wrong. The un-confirmed state it produces is still refused as current by
    the confirmation guard in ``is_current_for``.
    """
    entries = sorted(
        (int(ordinal), str(statement_class), str(employer_text))
        for ordinal, statement_class, employer_text in statement_signature
    )
    canonical = "\n".join(
        [
            _CONTENT_DIGEST_VERSION,
            "source=" + _text_digest(source_text),
            "statements="
            + "|".join(
                f"{ordinal}:{statement_class}:{_text_digest(employer_text)}"
                for ordinal, statement_class, employer_text in entries
            ),
        ]
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _text_digest(text):
    """Hash member text rather than concatenating it.

    Keeps the canonical string a fixed shape whatever the wording contains,
    so no delimiter appearing inside an employer statement can make two
    different readings collide.
    """
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def compute_input_fingerprint(
    source_version_number,
    requirement_version_number,
    evidence_versions,
    *,
    content_digest,
):
    """The digest that decides "Saved" from "Saved but no longer current".

    Handoff section 7 makes savedness and currency two different truths, and
    this function is the whole mechanism. It is deliberately a PURE function
    of four facts, so the same code computes both sides of the comparison:

      * the confirmed source version the result was computed from;
      * the confirmed requirement-set version it was computed from;
      * every evidence record the result cites, paired with a version;
      * ``content_digest`` — the wording of those confirmed inputs, because
        a member can rewrite the source correction or a statement's class in
        place and neither version number moves (finding F1).

    At save time the versions are the ones the analysis PINNED. At read time
    the same evidence keys are paired with the version the member's library
    carries NOW. Equal digests mean "Current for these inputs"; different
    digests mean "Inputs changed - Reanalysis required".

    A record that has been archived, un-confirmed or deleted has no current
    version, and the caller passes ``None``. That is encoded as ``0`` rather
    than dropped: dropping it would make a vanished evidence record
    indistinguishable from one that was never cited, which is precisely the
    change the member most needs to be told about.

    ``evidence_versions`` is sorted here rather than trusted, because the two
    call sites read from different result sets and a digest that depended on
    row order would report spurious staleness.
    """
    pairs = sorted(
        (str(key), int(version or 0)) for key, version in evidence_versions
    )
    canonical = "\n".join(
        [
            _FINGERPRINT_VERSION,
            f"source={int(source_version_number)}",
            f"requirements={int(requirement_version_number)}",
            "evidence=" + "|".join(f"{key}:{version}" for key, version in pairs),
            f"content={content_digest}",
        ]
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class OpportunitySlateServiceError(RuntimeError):
    """Raised when an Opportunity Slate working-session operation cannot be
    completed safely.

    ``.code`` is one of ``required``, ``invalid``, ``too_long``,
    ``changed``, ``not_found``, or ``unavailable`` — the same vocabulary
    ``services/knowledge_service.py`` uses, so the route layer maps a code
    to member-safe copy and re-renders with the member's text intact rather
    than losing it.
    """

    def __init__(self, message, code="unavailable"):
        super().__init__(message)
        self.code = code


def utf16_length(value):
    """Match SQL Server nvarchar and browser maxlength code-unit counting.

    The ``services/moment_service.py`` / ``services/knowledge_service.py``
    idiom, re-implemented here for the same file-ownership reason those
    modules give.
    """
    return len(value.encode("utf-16-le")) // 2


def _require_exact_fields(row, expected, label):
    """Set-equality row discipline: a row missing an expected field OR
    carrying an extra one is rejected outright rather than silently passed
    through or truncated."""
    if not isinstance(row, dict) or set(row) != set(expected):
        raise OpportunitySlateServiceError(
            f"Unexpected {label} result shape.", code="invalid"
        )


def _opaque_key(value, label):
    try:
        return str(UUID(str(value)))
    except (TypeError, ValueError, AttributeError) as error:
        raise OpportunitySlateServiceError(
            f"Invalid {label}.", code="invalid"
        ) from error


def _version_token(value, label):
    """16-hex-character token from a SQL Server binary(8) row_version."""
    if isinstance(value, memoryview):
        value = value.tobytes()
    if isinstance(value, bytearray):
        value = bytes(value)
    if isinstance(value, bytes):
        value = value.hex()
    if not isinstance(value, str) or not _VERSION_TOKEN.fullmatch(value):
        raise OpportunitySlateServiceError(f"Invalid {label}.", code="invalid")
    return value.lower()


def _decode_version_token(value):
    """Inverse of :func:`_version_token`. Returns ``None`` for anything not
    shaped like a version token, rather than guessing or passing an
    unrecognized value through to the database."""
    if isinstance(value, (bytes, bytearray, memoryview)):
        raw = bytes(value)
        return raw if len(raw) == 8 else None
    if isinstance(value, str) and _VERSION_TOKEN.fullmatch(value):
        return bytes.fromhex(value)
    return None


def _utc_timestamp(value, label, *, required=True):
    if value is None:
        if required:
            raise OpportunitySlateServiceError(f"Invalid {label}.", code="invalid")
        return None
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as error:
            raise OpportunitySlateServiceError(
                f"Invalid {label}.", code="invalid"
            ) from error
    else:
        raise OpportunitySlateServiceError(f"Invalid {label}.", code="invalid")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _isoformat(value):
    return None if value is None else value.isoformat().replace("+00:00", "Z")


def _positive_int(value, label):
    try:
        parsed = int(value)
    except (TypeError, ValueError) as error:
        raise OpportunitySlateServiceError(
            f"Invalid {label}.", code="invalid"
        ) from error
    if isinstance(value, bool) or parsed < 1:
        raise OpportunitySlateServiceError(f"Invalid {label}.", code="invalid")
    return parsed


def _optional_positive_int(value, label):
    if value is None:
        return None
    return _positive_int(value, label)


def _non_negative_int(value, label):
    try:
        parsed = int(value)
    except (TypeError, ValueError) as error:
        raise OpportunitySlateServiceError(
            f"Invalid {label}.", code="invalid"
        ) from error
    if isinstance(value, bool) or parsed < 0:
        raise OpportunitySlateServiceError(f"Invalid {label}.", code="invalid")
    return parsed


def _bounded_choice(value, allowed, label):
    if value not in allowed:
        raise OpportunitySlateServiceError(f"Invalid {label}.", code="invalid")
    return value


_FINGERPRINT_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _fingerprint(value):
    """A 64-character lowercase hex digest, or a refusal.

    The database CHECK says the same thing. Asserted here as well so a
    malformed value is refused before the round trip rather than arriving as
    a constraint violation the caller has to interpret.
    """
    text = value.strip().lower() if isinstance(value, str) else ""
    if not _FINGERPRINT_PATTERN.match(text):
        raise OpportunitySlateServiceError(
            "The input fingerprint is invalid.", code="invalid"
        )
    return text


def _bounded_text(value, label, max_units):
    if not isinstance(value, str) or not value:
        raise OpportunitySlateServiceError(f"Invalid {label}.", code="invalid")
    if utf16_length(value) > max_units:
        raise OpportunitySlateServiceError(f"Invalid {label}.", code="invalid")
    return value


def normalize_source_key(value):
    """Opaque-key normalization with the house null-on-failure idiom: a
    malformed key is indistinguishable from an absent one, so a caller can
    never probe for another member's key."""
    try:
        return str(UUID(str(value)))
    except (TypeError, ValueError, AttributeError):
        return None


def validate_source_text(value, *, label="role text"):
    """The single hard cap on captured employer wording, shared by both
    modes.

    The signed-in path and handoff section 18's anonymous public path call
    this same function, so the public boundary can never end up with the
    looser limit. Returns the text with its surrounding whitespace stripped
    (interior wording, including blank lines between sections, is preserved
    verbatim — this is the employer's text, not ours to reflow).

    Raises ``OpportunitySlateServiceError`` with ``.code`` in
    ``{"required", "too_long"}`` so the route re-renders the member's own
    text with a named error instead of discarding it.
    """
    cleaned = value.strip() if isinstance(value, str) else ""
    if not cleaned:
        raise OpportunitySlateServiceError(
            f"Add the {label} before continuing.", code="required"
        )
    if utf16_length(cleaned) > MAX_SOURCE_TEXT_UNITS:
        raise OpportunitySlateServiceError(
            f"That {label} is longer than {MAX_SOURCE_TEXT_UNITS:,} characters.",
            code="too_long",
        )
    return cleaned


def apply_concern_correction(document_text, quoted_text, corrected_text):
    """Splice one concern's corrected wording into the displayed document.

    Deterministic and shared by both modes, for the same reason
    :func:`validate_source_text` is: the anonymous public path must not get a
    looser rule than the signed-in one.

    The quoted span has to appear exactly once in the current document. If it
    appears zero times the wording has already changed underneath the concern;
    if it appears more than once there is no single right place to put the
    correction. Both raise ``code="changed"`` so the member is told the text
    moved and sent to the full editor, rather than having PeerSlate guess at a
    position and quietly rewrite the wrong sentence.
    """
    if not isinstance(document_text, str) or not document_text:
        raise OpportunitySlateServiceError("Invalid role text.", code="invalid")
    quote = quoted_text if isinstance(quoted_text, str) else ""
    if not quote:
        raise OpportunitySlateServiceError("Invalid quoted wording.", code="invalid")
    replacement = validate_source_text(corrected_text, label="corrected wording")

    occurrences = document_text.count(quote)
    if occurrences != 1:
        raise OpportunitySlateServiceError(
            "This wording changed. Review it and correct it in the editor.",
            code="changed",
        )
    updated = document_text.replace(quote, replacement, 1)
    return validate_source_text(updated, label="role text")


@dataclass(frozen=True)
class WorkingSourceView:
    """One member's current working session and its current source version.

    ``original_text`` is the employer's captured wording, exactly as it
    arrived. ``member_corrected_text`` is the member's manual correction of
    it, or ``None``. ``display_text`` is what the Review Source screen
    renders. The two are kept as separate fields rather than collapsed into
    one, because handoff section 1 treats employer source and member
    workbench input as different data classes.
    """

    working_session_key: str
    session_version_token: str
    workbench_state: str
    expires_at: datetime
    source_key: str
    source_version_token: str
    version_number: int
    confirmed_version_number: int | None
    confirmed_at: datetime | None
    capture_method: str
    original_text: str
    member_corrected_text: str | None
    corrected_at: datetime | None
    captured_at: datetime

    @property
    def display_text(self):
        return self.member_corrected_text or self.original_text

    @property
    def has_correction(self):
        return self.member_corrected_text is not None

    @property
    def is_confirmed(self):
        return self.confirmed_version_number == self.version_number

    @property
    def expires_at_iso(self):
        return _isoformat(self.expires_at)


def _serialize_working_row(row):
    _require_exact_fields(row, GET_ROW_FIELDS, "working session row")
    corrected = row["member_corrected_text"]
    if corrected is not None:
        corrected = _bounded_text(
            corrected, "corrected wording", MAX_SOURCE_TEXT_UNITS
        )
    return WorkingSourceView(
        working_session_key=_opaque_key(
            row["working_session_key"], "working session key"
        ),
        session_version_token=_version_token(
            row["session_row_version"], "session row version"
        ),
        workbench_state=_bounded_choice(
            row["workbench_state"], WORKBENCH_STATES, "workbench state"
        ),
        expires_at=_utc_timestamp(row["expires_at_utc"], "expiry time"),
        source_key=_opaque_key(row["source_key"], "source key"),
        source_version_token=_version_token(
            row["source_row_version"], "source row version"
        ),
        version_number=_positive_int(row["current_version_number"], "source version"),
        confirmed_version_number=_optional_positive_int(
            row["confirmed_version_number"], "confirmed version"
        ),
        confirmed_at=_utc_timestamp(
            row["confirmed_at_utc"], "confirmed time", required=False
        ),
        capture_method=_bounded_choice(
            row["capture_method"], CAPTURE_METHODS, "capture method"
        ),
        original_text=_bounded_text(
            row["original_text"], "employer wording", MAX_SOURCE_TEXT_UNITS
        ),
        member_corrected_text=corrected,
        corrected_at=_utc_timestamp(
            row["corrected_at_utc"], "corrected time", required=False
        ),
        captured_at=_utc_timestamp(row["captured_at_utc"], "captured time"),
    )


@dataclass(frozen=True)
class SourceConcernView:
    """One AI-proposed extraction concern and the member's decision on it.

    A third data class (handoff section 1), kept apart from both the
    employer's captured wording and the member's own correction:
    ``quoted_text`` is the employer's characters at the proposed span,
    ``concern_reason`` is the proposal, and ``member_corrected_text`` is the
    member's replacement wording — present only once they have applied one.
    None of the three is ever written over another.
    """

    concern_key: str
    span_start: int
    span_length: int
    quoted_text: str
    concern_reason: str
    member_resolution: str
    member_corrected_text: str | None
    resolved_at: datetime | None
    version_token: str

    @property
    def is_pending(self):
        return self.member_resolution == "pending"

    @property
    def span_end(self):
        return self.span_start + self.span_length


@dataclass(frozen=True)
class SourceReviewView:
    """The record that AI step 1 ran against one captured source version.

    Its existence is what tells "PeerSlate has reviewed this wording and found
    nothing" apart from "PeerSlate has not looked yet" — two different facts
    the screen has to be able to state differently.
    """

    review_key: str
    source_version_number: int
    model_name: str
    prompt_contract_version: str
    concern_count: int
    reviewed_at: datetime
    concerns: tuple

    @property
    def pending_concerns(self):
        return tuple(concern for concern in self.concerns if concern.is_pending)


@dataclass(frozen=True)
class RequirementStatementView:
    """One employer statement: the AI proposal and the member's correction.

    ``proposed_class`` / ``proposed_paths`` are the proposal.
    ``member_class`` / ``member_clarification`` are the member's canonical
    decision. They are separate fields on purpose — ``effective_class``
    derives the display value without either one overwriting the other, so
    "PeerSlate proposed X, the member says Y" stays answerable.
    """

    statement_key: str
    ordinal: int
    span_start: int
    span_length: int
    employer_text: str
    proposed_class: str
    proposed_explanation: str
    proposed_paths: tuple
    member_class: str | None
    member_clarification: str | None
    member_updated_at: datetime | None
    version_token: str

    @property
    def effective_class(self):
        return self.member_class or self.proposed_class

    @property
    def is_reclassified(self):
        return bool(self.member_class) and self.member_class != self.proposed_class

    @property
    def has_member_input(self):
        return bool(self.member_class) or bool(self.member_clarification)


@dataclass(frozen=True)
class RequirementSetView:
    """The current proposed requirement set for one working session."""

    requirement_set_key: str
    version_token: str
    version_number: int
    source_version_number: int
    model_name: str
    prompt_contract_version: str
    proposed_at: datetime
    confirmed_version_number: int | None
    confirmed_at: datetime | None
    statements: tuple

    @property
    def is_confirmed(self):
        return self.confirmed_version_number == self.version_number

    def counts_by_class(self):
        """Per-class counts only.

        Handoff section 1 and the locked rules: qualification accounting is
        per-status counts, never an overall score, percentage, recommendation,
        or verdict. This method is the only aggregation this module performs
        and it returns four independent counts.
        """
        counts = {name: 0 for name in sorted(STATEMENT_CLASSES)}
        for statement in self.statements:
            counts[statement.effective_class] = (
                counts.get(statement.effective_class, 0) + 1
            )
        return counts


def _serialize_concern_row(row):
    _require_exact_fields(row, CONCERN_ROW_FIELDS, "concern row")
    corrected = row["member_corrected_text"]
    if corrected is not None:
        corrected = _bounded_text(
            corrected, "corrected wording", MAX_SOURCE_TEXT_UNITS
        )
    return SourceConcernView(
        concern_key=_opaque_key(row["concern_key"], "concern key"),
        span_start=_non_negative_int(row["span_start"], "span start"),
        span_length=_positive_int(row["span_length"], "span length"),
        quoted_text=_bounded_text(
            row["quoted_text"], "quoted wording", MAX_CONCERN_QUOTE_UNITS
        ),
        concern_reason=_bounded_text(
            row["concern_reason"], "concern reason", MAX_CONCERN_REASON_UNITS
        ),
        member_resolution=_bounded_choice(
            row["member_resolution"], CONCERN_RESOLUTIONS, "concern resolution"
        ),
        member_corrected_text=corrected,
        resolved_at=_utc_timestamp(
            row["resolved_at_utc"], "resolved time", required=False
        ),
        version_token=_version_token(
            row["concern_row_version"], "concern row version"
        ),
    )


def _serialize_statement_row(row):
    _require_exact_fields(row, STATEMENT_ROW_FIELDS, "statement row")
    member_class = row["member_class"]
    if member_class is not None:
        member_class = _bounded_choice(
            member_class, STATEMENT_CLASSES, "member classification"
        )
    clarification = row["member_clarification"]
    if clarification is not None:
        clarification = _bounded_text(
            clarification, "clarification", MAX_CLARIFICATION_UNITS
        )
    return RequirementStatementView(
        statement_key=_opaque_key(row["statement_key"], "statement key"),
        ordinal=_positive_int(row["ordinal"], "statement ordinal"),
        span_start=_non_negative_int(row["span_start"], "span start"),
        span_length=_positive_int(row["span_length"], "span length"),
        employer_text=_bounded_text(
            row["employer_text"], "employer wording", MAX_STATEMENT_TEXT_UNITS
        ),
        proposed_class=_bounded_choice(
            row["proposed_class"], STATEMENT_CLASSES, "proposed classification"
        ),
        proposed_explanation=_bounded_text(
            row["proposed_explanation"], "explanation", MAX_EXPLANATION_UNITS
        ),
        proposed_paths=_decode_structure(row["proposed_structure_json"]),
        member_class=member_class,
        member_clarification=clarification,
        member_updated_at=_utc_timestamp(
            row["member_updated_at_utc"], "correction time", required=False
        ),
        version_token=_version_token(
            row["statement_row_version"], "statement row version"
        ),
    )


def _decode_structure(value):
    """Read the stored interpreted structure back into bounded path tuples.

    Rejects anything that is not the exact shape this package writes. A stored
    blob is not more trustworthy than a model reply just because it made a
    round trip through the database, so it is re-checked on the way out.
    """
    if not isinstance(value, str) or not value:
        raise OpportunitySlateServiceError(
            "Invalid interpreted structure.", code="invalid"
        )
    if utf16_length(value) > MAX_STRUCTURE_JSON_UNITS:
        raise OpportunitySlateServiceError(
            "Invalid interpreted structure.", code="invalid"
        )
    try:
        decoded = json.loads(value)
    except (TypeError, ValueError) as error:
        raise OpportunitySlateServiceError(
            "Invalid interpreted structure.", code="invalid"
        ) from error
    if not isinstance(decoded, list) or not decoded or len(decoded) > 4:
        raise OpportunitySlateServiceError(
            "Invalid interpreted structure.", code="invalid"
        )
    paths = []
    for entry in decoded:
        if (
            not isinstance(entry, dict)
            or set(entry) != {"label", "clauses"}
            or not isinstance(entry["clauses"], list)
            or not entry["clauses"]
            or len(entry["clauses"]) > 8
        ):
            raise OpportunitySlateServiceError(
                "Invalid interpreted structure.", code="invalid"
            )
        clauses = tuple(
            _bounded_text(clause, "clause", 200) for clause in entry["clauses"]
        )
        paths.append(
            {
                "label": _bounded_text(entry["label"], "path label", 20),
                "clauses": clauses,
            }
        )
    return tuple(paths)


def _encode_structure(paths):
    """The inverse of :func:`_decode_structure`, with the same bounds."""
    if not isinstance(paths, (list, tuple)) or not paths or len(paths) > 4:
        raise OpportunitySlateServiceError(
            "Invalid interpreted structure.", code="invalid"
        )
    encoded = []
    for entry in paths:
        if not isinstance(entry, dict) or set(entry) != {"label", "clauses"}:
            raise OpportunitySlateServiceError(
                "Invalid interpreted structure.", code="invalid"
            )
        clauses = entry["clauses"]
        if not isinstance(clauses, (list, tuple)) or not clauses or len(clauses) > 8:
            raise OpportunitySlateServiceError(
                "Invalid interpreted structure.", code="invalid"
            )
        encoded.append(
            {
                "label": _bounded_text(entry["label"], "path label", 20),
                "clauses": [
                    _bounded_text(clause, "clause", 200) for clause in clauses
                ],
            }
        )
    serialized = json.dumps(encoded, separators=(",", ":"), ensure_ascii=False)
    if utf16_length(serialized) > MAX_STRUCTURE_JSON_UNITS:
        raise OpportunitySlateServiceError(
            "Invalid interpreted structure.", code="invalid"
        )
    return serialized


@dataclass(frozen=True)
class EvidenceItemView:
    """One piece of the member's own confirmed evidence, READ ONLY.

    Slice OS-3's fourth data class (handoff section 1). The member's library
    is the one authoritative place this content lives: Opportunity Slate reads
    it, grounds an analysis in it, and writes nothing back. ``version`` is the
    confirmed version number, pinned into any citation that quotes it so the
    member can still tell what the analysis actually read after they edit the
    item.
    """

    evidence_key: str
    version: int
    title: str
    body: str
    updated_at: datetime

    @property
    def kind(self):
        # Slice OS-3 grounds on confirmed Workshop knowledge items only.
        # Moments are part of the architectural enum (handoff section 17-Q2)
        # and are deliberately not read here; the screen says so plainly.
        return "knowledge_item"


@dataclass(frozen=True)
class AnalysisCitationView:
    """One grounded citation: employer words, evidence reference, excerpt.

    ``covered_text`` is a verbatim span of the employer's own confirmed
    clause and ``excerpt`` a verbatim span of the member's own evidence.
    Neither is model prose — see the composition-boundary block in
    ``services/opportunity_analysis_service.py``.
    """

    ordinal: int
    clause_ordinal: int
    covered_text: str
    evidence_kind: str
    evidence_key: str
    evidence_version: int
    evidence_title: str
    excerpt: str


@dataclass(frozen=True)
class AnalysisStatementView:
    """One qualification's result. ``status`` is derived, never model-authored."""

    statement_key: str
    ordinal: int
    status: str
    citation_count: int
    citations: tuple

    @property
    def evidence_references(self):
        """The distinct evidence records this result cites, in citation order."""
        seen = []
        for citation in self.citations:
            key = (citation.evidence_key, citation.evidence_version)
            if key not in [(item.evidence_key, item.evidence_version) for item in seen]:
                seen.append(citation)
        return tuple(seen)


@dataclass(frozen=True)
class AnalysisView:
    """One alignment analysis of one confirmed requirement-set version."""

    analysis_key: str
    version_token: str
    source_version_number: int
    requirement_version_number: int
    model_name: str
    prompt_contract_version: str
    evidence_considered_count: int
    qualification_count: int
    analyzed_at: datetime
    statements: tuple

    def counts_by_status(self):
        """Per-status counts only.

        Handoff section 1 and the locked rules: qualification accounting is
        per-status counts, never an overall score, percentage, recommendation,
        or verdict. This method and
        ``RequirementSetView.counts_by_class`` are the only aggregation this
        module performs, and both return independent counts of named states.
        """
        counts = {name: 0 for name in sorted(ALIGNMENT_STATUSES)}
        for statement in self.statements:
            counts[statement.status] = counts.get(statement.status, 0) + 1
        return counts


@dataclass(frozen=True)
class ResponseView:
    """One member response to one qualification.

    Member-attributed context, stored apart from both the AI proposal and the
    authorized evidence (handoff section 10): it never becomes a citation and
    never changes a derived status.
    """

    statement_key: str
    response_key: str
    version_token: str
    response_kind: str
    response_text: str | None
    authored_via: str
    connected_evidence_kind: str | None
    connected_evidence_key: str | None
    connected_evidence_version: int | None
    connected_evidence_title: str | None
    updated_at: datetime


# ---------------------------------------------------------------------------
# Slice OS-4 views — the durable saved slate.
#
# Every one of these is a COPY the saved result owns, not a live read. That is
# what lets a saved slate outlive the working session, the analysis and the
# purge, and it is why nothing below carries a row-version fence except the
# slate itself: an append-only snapshot has nothing to concurrently update.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SavedEvidenceView:
    """One pinned evidence reference inside a saved qualification."""

    ordinal: int
    clause_ordinal: int
    covered_text: str
    evidence_kind: str
    evidence_key: str
    evidence_version: int
    evidence_title: str
    excerpt: str


@dataclass(frozen=True)
class SavedQualificationView:
    """One qualification as it stood when the member saved it."""

    ordinal: int
    statement_class: str
    employer_text: str
    status: str
    citation_count: int
    response_kind: str | None
    response_text: str | None
    authored_via: str | None
    connected_evidence_title: str | None
    connected_evidence_version: int | None
    evidence: tuple

    @property
    def has_response(self):
        return self.response_kind is not None


@dataclass(frozen=True)
class SavedVersionView:
    """One entry in the versions list (`View saved details`)."""

    saved_result_key: str
    save_version_number: int
    source_version_number: int
    requirement_version_number: int
    qualification_count: int
    saved_at: datetime


@dataclass(frozen=True)
class SavedSlateView:
    """The member's saved slate, opened at one of its saved versions.

    ``is_current`` is the answer to a question the member is entitled to ask
    and that "saved" alone cannot answer: does this result still apply to my
    inputs? It is computed by comparing the fingerprint stored at save time
    with one recomputed from the current inputs. Nothing here reanalyzes,
    and nothing here changes a stored row.
    """

    slate_key: str
    version_token: str
    created_at: datetime
    # The slate's own highest save version number, which — because saves only
    # ever append and a delete removes the whole slate — is the TRUE number of
    # saved versions this member has. ``versions`` below is capped at
    # MAX_SAVED_VERSIONS_LISTED for the rail, so the two can legitimately
    # disagree and the screen must not quote the capped one as the total
    # (2026-08-04 independent review, finding F5).
    total_version_count: int
    saved_result_key: str
    save_version_number: int
    source_version_number: int
    requirement_version_number: int
    saved_analysis_key: str
    source_text: str
    model_name: str
    prompt_contract_version: str
    evidence_considered_count: int
    qualification_count: int
    input_fingerprint: str
    saved_at: datetime
    qualifications: tuple
    versions: tuple
    # ((evidence_key, pinned_version, current_version_or_None), ...)
    evidence_currency: tuple

    def counts_by_status(self):
        """Per-status counts only — the same locked accounting the live
        workbench performs, and for the same reason: there is no aggregate."""
        counts = {name: 0 for name in sorted(ALIGNMENT_STATUSES)}
        for qualification in self.qualifications:
            counts[qualification.status] = counts.get(qualification.status, 0) + 1
        return counts

    def pinned_content_digest(self):
        """The content digest rebuilt from what this snapshot itself copied.

        The copy model pays for currency here: because the saved result owns
        the confirmed source wording and each qualification's ordinal, class
        and employer text, the pinned side of the content comparison needs no
        extra stored column and no extra read.
        """
        return compute_content_digest(
            self.source_text,
            (
                (
                    qualification.ordinal,
                    qualification.statement_class,
                    qualification.employer_text,
                )
                for qualification in self.qualifications
            ),
        )

    def pinned_fingerprint(self):
        """Recompute the digest from what this snapshot PINNED and COPIED.

        An integrity check rather than a display value: it must equal
        ``input_fingerprint``. If it does not, this row and its evidence rows
        disagree about what was saved, and the caller treats the result as not
        current rather than presenting a reassurance it cannot support.
        """
        return compute_input_fingerprint(
            self.source_version_number,
            self.requirement_version_number,
            ((key, pinned) for key, pinned, _ in self.evidence_currency),
            content_digest=self.pinned_content_digest(),
        )

    def current_fingerprint(
        self, source_version_number, requirement_version_number, content_digest
    ):
        """The digest of the member's CURRENT inputs, over the same evidence
        records this snapshot cites, at the versions their library carries
        now, and over the wording those inputs carry now."""
        return compute_input_fingerprint(
            source_version_number,
            requirement_version_number,
            ((key, current) for key, _, current in self.evidence_currency),
            content_digest=content_digest,
        )

    def is_current_for(
        self,
        source_version_number,
        requirement_version_number,
        content_digest,
        *,
        inputs_confirmed,
    ):
        """Does this saved result still apply to the member's current inputs?

        Three independent conditions, each able to answer "no" on its own,
        and the order is worst-consequence-first:

        1. ``inputs_confirmed`` — a structural backstop rather than a content
           test. PeerSlate's whole flow rests on two explicit confirmation
           checkpoints, and a member sitting on a reading they have NOT
           confirmed is mid-edit. Refusing "current" there costs a member at
           worst one unnecessary reanalysis; granting it costs them a wrong
           answer they had no reason to doubt. It also catches any future
           in-place mutation the content digest has not been taught about
           yet, which is exactly how finding F1 happened.
        2. The snapshot agrees with itself.
        3. The current inputs digest to what was saved.
        """
        if not inputs_confirmed:
            return False
        if self.pinned_fingerprint() != self.input_fingerprint:
            return False
        return (
            self.current_fingerprint(
                source_version_number, requirement_version_number, content_digest
            )
            == self.input_fingerprint
        )


def _serialize_saved_qualification_row(row, evidence):
    _require_exact_fields(
        row, SAVED_QUALIFICATION_ROW_FIELDS, "saved qualification row"
    )
    status = _bounded_choice(
        row["derived_status"], ALIGNMENT_STATUSES, "alignment status"
    )
    count = _non_negative_int(row["citation_count"], "citation count")
    if len(evidence) != count:
        # The stored count and the stored rows are two records of one fact.
        # The live workbench refuses when they disagree; a SAVED result that
        # disagreed with itself would be worse, because the member cannot
        # re-run it to find out which one is right.
        raise OpportunitySlateServiceError(
            "The saved result is incomplete.", code="invalid"
        )
    if (count == 0) != (status == "not_enough_information"):
        raise OpportunitySlateServiceError(
            "The saved result is incomplete.", code="invalid"
        )
    kind = row["response_kind"]
    if kind is not None:
        kind = _bounded_choice(kind, RESPONSE_KINDS, "response kind")
    text = row["response_text"]
    if text is not None:
        text = _bounded_text(text, "response", MAX_RESPONSE_TEXT_UNITS)
    provenance = row["authored_via"]
    if provenance is not None:
        provenance = _bounded_choice(
            provenance, AUTHORED_VIA_VALUES, "response provenance"
        )
    title = row["connected_evidence_title"]
    if title is not None:
        title = _bounded_text(title, "evidence title", MAX_EVIDENCE_TITLE_UNITS)
    return SavedQualificationView(
        ordinal=_positive_int(row["ordinal"], "ordinal"),
        statement_class=_bounded_choice(
            row["statement_class"], SAVED_STATEMENT_CLASSES, "statement class"
        ),
        employer_text=_bounded_text(
            row["employer_text"], "employer wording", MAX_STATEMENT_TEXT_UNITS
        ),
        status=status,
        citation_count=count,
        response_kind=kind,
        response_text=text,
        authored_via=provenance,
        connected_evidence_title=title,
        connected_evidence_version=_optional_positive_int(
            row["connected_evidence_version"], "evidence version"
        ),
        evidence=evidence,
    )


def _serialize_saved_evidence_row(row):
    _require_exact_fields(row, SAVED_EVIDENCE_ROW_FIELDS, "saved evidence row")
    return SavedEvidenceView(
        ordinal=_positive_int(row["ordinal"], "evidence ordinal"),
        clause_ordinal=_positive_int(row["clause_ordinal"], "clause ordinal"),
        covered_text=_bounded_text(
            row["covered_text"], "covered wording", MAX_COVERED_TEXT_UNITS
        ),
        evidence_kind=_bounded_choice(
            row["evidence_kind"], EVIDENCE_KINDS, "evidence kind"
        ),
        evidence_key=_opaque_key(row["evidence_key"], "evidence key"),
        evidence_version=_positive_int(row["evidence_version"], "evidence version"),
        evidence_title=_bounded_text(
            row["evidence_title"], "evidence title", MAX_EVIDENCE_TITLE_UNITS
        ),
        excerpt=_bounded_text(row["excerpt"], "evidence excerpt", MAX_EXCERPT_UNITS),
    )


def _serialize_saved_version_row(row):
    _require_exact_fields(row, SAVED_VERSION_ROW_FIELDS, "saved version row")
    return SavedVersionView(
        saved_result_key=_opaque_key(row["saved_result_key"], "saved result key"),
        save_version_number=_positive_int(
            row["save_version_number"], "save version"
        ),
        source_version_number=_positive_int(
            row["source_version_number"], "source version"
        ),
        requirement_version_number=_positive_int(
            row["requirement_version_number"], "requirement version"
        ),
        qualification_count=_positive_int(
            row["qualification_count"], "qualification count"
        ),
        saved_at=_utc_timestamp(row["saved_at_utc"], "save time"),
    )


def _serialize_evidence_row(row):
    _require_exact_fields(row, EVIDENCE_ROW_FIELDS, "evidence row")
    return EvidenceItemView(
        evidence_key=_opaque_key(row["evidence_key"], "evidence key"),
        version=_positive_int(row["evidence_version"], "evidence version"),
        title=_bounded_text(
            row["evidence_title"], "evidence title", MAX_EVIDENCE_TITLE_UNITS
        ),
        body=_bounded_text(
            row["evidence_body"], "evidence wording", MAX_EVIDENCE_BODY_UNITS
        ),
        updated_at=_utc_timestamp(row["evidence_updated_at_utc"], "evidence time"),
    )


def _serialize_citation_row(row):
    _require_exact_fields(row, ANALYSIS_CITATION_ROW_FIELDS, "citation row")
    return AnalysisCitationView(
        ordinal=_positive_int(row["ordinal"], "citation ordinal"),
        clause_ordinal=_positive_int(row["clause_ordinal"], "clause ordinal"),
        covered_text=_bounded_text(
            row["covered_text"], "covered wording", MAX_COVERED_TEXT_UNITS
        ),
        evidence_kind=_bounded_choice(
            row["evidence_kind"], EVIDENCE_KINDS, "evidence kind"
        ),
        evidence_key=_opaque_key(row["evidence_key"], "evidence key"),
        evidence_version=_positive_int(row["evidence_version"], "evidence version"),
        evidence_title=_bounded_text(
            row["evidence_title"], "evidence title", MAX_EVIDENCE_TITLE_UNITS
        ),
        excerpt=_bounded_text(row["excerpt"], "evidence excerpt", MAX_EXCERPT_UNITS),
    )


def _serialize_response_row(row):
    _require_exact_fields(row, RESPONSE_ROW_FIELDS, "response row")
    text = row["response_text"]
    if text is not None:
        text = _bounded_text(text, "response", MAX_RESPONSE_TEXT_UNITS)
    connected_kind = row["connected_evidence_kind"]
    if connected_kind is not None:
        connected_kind = _bounded_choice(
            connected_kind, EVIDENCE_KINDS, "connected evidence kind"
        )
    connected_title = row["connected_evidence_title"]
    if connected_title is not None:
        connected_title = _bounded_text(
            connected_title, "connected evidence title", MAX_EVIDENCE_TITLE_UNITS
        )
    return ResponseView(
        statement_key=_opaque_key(row["statement_key"], "statement key"),
        response_key=_opaque_key(row["response_key"], "response key"),
        version_token=_version_token(
            row["response_row_version"], "response row version"
        ),
        response_kind=_bounded_choice(
            row["response_kind"], RESPONSE_KINDS, "response kind"
        ),
        response_text=text,
        authored_via=_bounded_choice(
            row["authored_via"], AUTHORED_VIA_VALUES, "response provenance"
        ),
        connected_evidence_kind=connected_kind,
        connected_evidence_key=(
            None
            if row["connected_evidence_key"] is None
            else _opaque_key(row["connected_evidence_key"], "connected evidence key")
        ),
        connected_evidence_version=_optional_positive_int(
            row["connected_evidence_version"], "connected evidence version"
        ),
        connected_evidence_title=connected_title,
        updated_at=_utc_timestamp(row["updated_at_utc"], "response time"),
    )


class OpportunitySlateService:
    """Owner-scoped access to the Opportunity Slate working store.

    Every method takes the server-derived ``user_key`` and passes it
    straight to a procedure that resolves the owner itself. No method
    accepts, derives, or trusts an owner id from a caller.
    """

    def __init__(self, database=None):
        self.database = database or database_service

    @staticmethod
    def _require_user_key(user_key):
        if not isinstance(user_key, str) or not user_key.strip():
            raise OpportunitySlateServiceError(
                "A member key is required.", code="required"
            )
        return user_key

    @staticmethod
    def _require_source_key(source_key):
        normalized = normalize_source_key(source_key)
        if not normalized:
            raise OpportunitySlateServiceError("Invalid source key.", code="invalid")
        return normalized

    @staticmethod
    def _require_expected_row_version(version_token):
        decoded = _decode_version_token(version_token)
        if decoded is None:
            # Treated exactly like a stale token: the caller is told the
            # record changed, never that their token was malformed in a way
            # that would help them craft a better one.
            raise OpportunitySlateServiceError(
                "This working session changed. Refresh and try again.", code="changed"
            )
        return decoded

    def purge_expired_working_data_for_owner(self, user_key):
        """Destroy this owner's already-expired working data.

        Invoked opportunistically at the start of a room request (handoff
        section 8). It can only remove rows whose ``expires_at_utc`` has
        already passed — rows the read already refuses to return — so it is
        never a member-visible deletion.
        """
        self._require_user_key(user_key)
        row = self.database.first_row(
            "usp_PurgeExpiredOpportunityWorkingData",
            [("@UserKey", user_key)],
        )
        if not row:
            # No profile resolved, or nothing to purge. Both are ordinary.
            return {"purged_sessions": 0, "purged_versions": 0}
        _require_exact_fields(row, PURGE_ROW_FIELDS, "purge result")
        return {
            "purged_sessions": _non_negative_int(
                row["purged_session_count"], "purged session count"
            ),
            "purged_versions": _non_negative_int(
                row["purged_version_count"], "purged version count"
            ),
        }

    def get_working_session_for_owner(self, user_key):
        """This owner's current working session, or ``None``.

        ``None`` means exactly one thing to the caller: start at role
        intake. It covers "never started", "explicitly deleted", and
        "expired" alike — the member is never shown a tombstone for
        ephemeral infrastructure.
        """
        self._require_user_key(user_key)
        row = self.database.first_row(
            "usp_GetOpportunityWorkingSessionForOwner",
            [("@UserKey", user_key)],
        )
        if not row:
            return None
        view = _serialize_working_row(row)
        # Second expiry enforcement, in the application. The procedure
        # already filters on expires_at_utc; this makes an expired session
        # inaccessible even if that predicate were ever weakened.
        if view.expires_at <= datetime.now(timezone.utc):
            return None
        return view

    def save_source_for_owner(
        self, user_key, idempotency_key, source_text, capture_method="pasted"
    ):
        """Capture (or replace) the employer source for this owner.

        Idempotent: a repeated ``idempotency_key`` for the same owner
        returns the version it already created (outcome ``existing``)
        instead of appending a second one, so a double-submitted intake
        form cannot silently create Source Version 2. Byte-identical
        wording under a fresh key returns ``unchanged`` and likewise
        appends nothing.
        """
        self._require_user_key(user_key)
        if not isinstance(idempotency_key, str) or not idempotency_key.strip():
            raise OpportunitySlateServiceError(
                "An idempotency key is required.", code="required"
            )
        if utf16_length(idempotency_key) > MAX_IDEMPOTENCY_KEY_UNITS:
            raise OpportunitySlateServiceError(
                "Idempotency key exceeds its limit.", code="too_long"
            )
        if capture_method not in OS6_CAPTURE_METHODS:
            # Refusing every value this build does not actually implement
            # keeps an unbuilt capture method (dictation is OS-5's own
            # branch) from ever being recorded as provenance for text that
            # arrived a different way.
            raise OpportunitySlateServiceError(
                "Capture method is invalid.", code="invalid"
            )
        clean_text = validate_source_text(source_text)

        row = self.database.first_row(
            "usp_SaveOpportunitySourceForOwner",
            [
                ("@UserKey", user_key),
                ("@IdempotencyKey", idempotency_key),
                ("@SourceText", clean_text),
                ("@CaptureMethod", capture_method),
                ("@ExpiresInHours", WORKING_SESSION_TTL_HOURS),
            ],
        )
        _require_exact_fields(row, SAVE_ROW_FIELDS, "save result")
        outcome = row["outcome"]
        if outcome not in _SAVE_OUTCOMES or not row["source_key"]:
            # Never report a save without an exact, non-falsy key — the
            # false-save guard from services/journal_service.py.
            raise OpportunitySlateServiceError(
                "The role source could not be captured.", code="not_found"
            )
        return {
            "outcome": outcome,
            "working_session_key": _opaque_key(
                row["working_session_key"], "working session key"
            ),
            "source_key": _opaque_key(row["source_key"], "source key"),
            "version_number": _positive_int(row["version_number"], "source version"),
            "workbench_state": _bounded_choice(
                row["workbench_state"], WORKBENCH_STATES, "workbench state"
            ),
            "session_version_token": _version_token(
                row["session_row_version"], "session row version"
            ),
            "source_version_token": _version_token(
                row["source_row_version"], "source row version"
            ),
            "saved": True,
        }

    def correct_source_for_owner(
        self, user_key, source_key, expected_version_token, corrected_text
    ):
        """Apply the member's manual correction to the displayed wording.

        The employer's captured ``original_text`` is never touched — the
        correction is stored alongside it (handoff section 8). A mismatched
        ``expected_version_token``, a foreign key, and an expired session
        all raise ``code="changed"``, never a false success and never a
        signal about whether some other member's key exists.
        """
        self._require_user_key(user_key)
        clean_source_key = self._require_source_key(source_key)
        expected_row_version = self._require_expected_row_version(
            expected_version_token
        )
        clean_text = validate_source_text(corrected_text, label="corrected wording")

        row = self.database.first_row(
            "usp_CorrectOpportunitySourceForOwner",
            [
                ("@UserKey", user_key),
                ("@SourceKey", clean_source_key),
                ("@ExpectedRowVersion", expected_row_version),
                ("@CorrectedText", clean_text),
            ],
        )
        _require_exact_fields(row, CORRECT_ROW_FIELDS, "correction result")
        self._raise_for_fenced_outcome(row["outcome"], "correction")
        return {
            "outcome": "success",
            "source_version_token": _version_token(
                row["source_row_version"], "source row version"
            ),
            "version_number": _positive_int(row["version_number"], "source version"),
        }

    def confirm_source_for_owner(self, user_key, source_key, expected_version_token):
        """Checkpoint 1 of 2: record which source version the member
        accepted.

        This saves no slate, produces no qualification result, and calls no
        AI. It only records that the member reviewed and accepted this
        exact captured wording.
        """
        self._require_user_key(user_key)
        clean_source_key = self._require_source_key(source_key)
        expected_row_version = self._require_expected_row_version(
            expected_version_token
        )

        row = self.database.first_row(
            "usp_ConfirmOpportunitySourceForOwner",
            [
                ("@UserKey", user_key),
                ("@SourceKey", clean_source_key),
                ("@ExpectedRowVersion", expected_row_version),
            ],
        )
        _require_exact_fields(row, CONFIRM_ROW_FIELDS, "confirmation result")
        self._raise_for_fenced_outcome(row["outcome"], "confirmation")
        return {
            "outcome": "success",
            "source_version_token": _version_token(
                row["source_row_version"], "source row version"
            ),
            "confirmed_version_number": _positive_int(
                row["confirmed_version_number"], "confirmed version"
            ),
        }

    def delete_working_session_for_owner(
        self, user_key, working_session_key, expected_version_token
    ):
        """The member's explicit discard of the whole working session.

        Atomic and complete: source versions, source, and session. There is
        no durable artifact in slice OS-1 for it to leave behind, and it can
        never reach another member's rows.
        """
        self._require_user_key(user_key)
        clean_session_key = self._require_source_key(working_session_key)
        expected_row_version = self._require_expected_row_version(
            expected_version_token
        )

        row = self.database.first_row(
            "usp_DeleteOpportunityWorkingSessionForOwner",
            [
                ("@UserKey", user_key),
                ("@WorkingSessionKey", clean_session_key),
                ("@ExpectedRowVersion", expected_row_version),
            ],
        )
        _require_exact_fields(row, DELETE_ROW_FIELDS, "delete result")
        self._raise_for_fenced_outcome(row["outcome"], "delete")
        return {
            "outcome": "success",
            "deleted_version_count": _non_negative_int(
                row["deleted_version_count"], "deleted version count"
            ),
        }

    # ------------------------------------------------------------------
    # Slice OS-2: AI proposals and the member's decisions about them
    #
    # Every method below takes the same server-derived user key and passes it
    # to a procedure that resolves the owner itself. Nothing here accepts an
    # owner id, and nothing here is reachable from the anonymous public
    # session — handoff section 18's public mode holds its whole working
    # state in a signed browser-held token and calls no procedure at all.
    # ------------------------------------------------------------------

    def get_source_review_for_owner(self, user_key, source_key):
        """The AI step-1 record for this owner's current source version.

        ``None`` means step 1 has not run for this version — deliberately not
        the same answer as "it ran and found nothing", which returns a review
        with an empty ``concerns``.
        """
        self._require_user_key(user_key)
        clean_source_key = self._require_source_key(source_key)
        result_sets = self.database.execute_procedure(
            "usp_GetOpportunitySourceReviewForOwner",
            [("@UserKey", user_key), ("@SourceKey", clean_source_key)],
        )
        review_rows = result_sets[0] if result_sets else []
        if not review_rows:
            return None
        row = review_rows[0]
        _require_exact_fields(row, REVIEW_ROW_FIELDS, "source review row")
        concern_rows = result_sets[1] if len(result_sets) > 1 else []
        concerns = tuple(_serialize_concern_row(item) for item in concern_rows)
        return SourceReviewView(
            review_key=_opaque_key(row["review_key"], "review key"),
            source_version_number=_positive_int(
                row["source_version_number"], "source version"
            ),
            model_name=_bounded_text(
                row["model_name"], "model name", MAX_MODEL_NAME_UNITS
            ),
            prompt_contract_version=_bounded_text(
                row["prompt_contract_version"],
                "prompt contract version",
                MAX_PROMPT_CONTRACT_UNITS,
            ),
            concern_count=_non_negative_int(row["concern_count"], "concern count"),
            reviewed_at=_utc_timestamp(row["reviewed_at_utc"], "review time"),
            concerns=concerns,
        )

    def save_source_review_for_owner(
        self,
        user_key,
        source_key,
        expected_version_token,
        concerns,
        model_name,
        prompt_contract_version,
    ):
        """Record that AI step 1 ran, with its validated proposals.

        The proposals arrive already validated against the stored source by
        ``services/opportunity_analysis_service.py``; this method re-bounds
        every field before it reaches the database rather than trusting that,
        because the two layers are allowed to be corrected independently.
        """
        self._require_user_key(user_key)
        clean_source_key = self._require_source_key(source_key)
        expected_row_version = self._require_expected_row_version(
            expected_version_token
        )
        if not isinstance(concerns, (list, tuple)):
            raise OpportunitySlateServiceError(
                "Invalid concern proposals.", code="invalid"
            )
        if len(concerns) > 20:
            raise OpportunitySlateServiceError(
                "Too many concern proposals.", code="invalid"
            )

        payload = []
        for concern in concerns:
            if not isinstance(concern, dict):
                raise OpportunitySlateServiceError(
                    "Invalid concern proposal.", code="invalid"
                )
            payload.append(
                {
                    "span_start": _non_negative_int(
                        concern.get("span_start"), "span start"
                    ),
                    "span_length": _positive_int(
                        concern.get("span_length"), "span length"
                    ),
                    "quoted_text": _bounded_text(
                        concern.get("quoted_text"),
                        "quoted wording",
                        MAX_CONCERN_QUOTE_UNITS,
                    ),
                    "concern_reason": _bounded_text(
                        concern.get("concern_reason"),
                        "concern reason",
                        MAX_CONCERN_REASON_UNITS,
                    ),
                }
            )

        row = self.database.first_row(
            "usp_SaveOpportunitySourceReviewForOwner",
            [
                ("@UserKey", user_key),
                ("@SourceKey", clean_source_key),
                ("@ExpectedRowVersion", expected_row_version),
                (
                    "@ModelName",
                    _bounded_text(model_name, "model name", MAX_MODEL_NAME_UNITS),
                ),
                (
                    "@PromptContractVersion",
                    _bounded_text(
                        prompt_contract_version,
                        "prompt contract version",
                        MAX_PROMPT_CONTRACT_UNITS,
                    ),
                ),
                (
                    "@ConcernsJson",
                    json.dumps(payload, separators=(",", ":"), ensure_ascii=False),
                ),
            ],
        )
        _require_exact_fields(row, SAVE_REVIEW_ROW_FIELDS, "source review result")
        self._raise_for_fenced_outcome(row["outcome"], "wording review")
        return {
            "outcome": "success",
            "review_key": _opaque_key(row["review_key"], "review key"),
            "concern_count": _non_negative_int(row["concern_count"], "concern count"),
        }

    def resolve_source_concern_for_owner(
        self,
        user_key,
        concern_key,
        expected_version_token,
        resolution,
        corrected_span_text=None,
        document_text=None,
    ):
        """Apply or dismiss one concern.

        ``applied`` writes the member's replacement wording for that span AND
        the resulting whole-document text in one transaction, then clears the
        source confirmation the changed wording invalidates. ``dismissed``
        records the decision and changes no wording at all — the employer's
        text is exactly as it was, so there is nothing to re-confirm.

        The employer's ``original_text`` is never touched by either path.
        """
        self._require_user_key(user_key)
        clean_concern_key = self._require_source_key(concern_key)
        expected_row_version = self._require_expected_row_version(
            expected_version_token
        )
        if resolution not in {"applied", "dismissed"}:
            raise OpportunitySlateServiceError(
                "Invalid concern decision.", code="invalid"
            )
        if resolution == "applied":
            corrected_span_text = validate_source_text(
                corrected_span_text, label="corrected wording"
            )
            document_text = validate_source_text(document_text, label="role text")
        else:
            corrected_span_text = None
            document_text = None

        row = self.database.first_row(
            "usp_ResolveOpportunitySourceConcernForOwner",
            [
                ("@UserKey", user_key),
                ("@ConcernKey", clean_concern_key),
                ("@ExpectedRowVersion", expected_row_version),
                ("@Resolution", resolution),
                ("@CorrectedSpanText", corrected_span_text),
                ("@DocumentText", document_text),
            ],
        )
        _require_exact_fields(row, RESOLVE_ROW_FIELDS, "concern decision result")
        self._raise_for_fenced_outcome(row["outcome"], "concern decision")
        return {
            "outcome": "success",
            "source_version_token": _version_token(
                row["source_row_version"], "source row version"
            ),
            "member_resolution": _bounded_choice(
                row["member_resolution"], CONCERN_RESOLUTIONS, "concern resolution"
            ),
        }

    def get_requirements_for_owner(self, user_key):
        """This owner's current proposed requirement set, or ``None``.

        Returns ``None`` when no proposal exists for the *current* source
        version — a requirement set pinned to superseded wording is never
        shown, because it describes text the member has since replaced.
        """
        self._require_user_key(user_key)
        result_sets = self.database.execute_procedure(
            "usp_GetOpportunityRequirementsForOwner",
            [("@UserKey", user_key)],
        )
        set_rows = result_sets[0] if result_sets else []
        if not set_rows:
            return None
        row = set_rows[0]
        _require_exact_fields(row, REQUIREMENT_SET_ROW_FIELDS, "requirement set row")
        statement_rows = result_sets[1] if len(result_sets) > 1 else []
        statements = tuple(
            _serialize_statement_row(item) for item in statement_rows
        )
        if not statements:
            # A set with no statements is not a set. Refusing it here keeps
            # an empty Review Requirements screen from ever claiming that
            # PeerSlate found nothing in the employer's source.
            raise OpportunitySlateServiceError(
                "The requirement set is incomplete.", code="invalid"
            )
        ordinals = [statement.ordinal for statement in statements]
        if sorted(ordinals) != list(range(1, len(statements) + 1)):
            raise OpportunitySlateServiceError(
                "The requirement set is incomplete.", code="invalid"
            )
        return RequirementSetView(
            requirement_set_key=_opaque_key(
                row["requirement_set_key"], "requirement set key"
            ),
            version_token=_version_token(row["set_row_version"], "set row version"),
            version_number=_positive_int(row["version_number"], "set version"),
            source_version_number=_positive_int(
                row["source_version_number"], "source version"
            ),
            model_name=_bounded_text(
                row["model_name"], "model name", MAX_MODEL_NAME_UNITS
            ),
            prompt_contract_version=_bounded_text(
                row["prompt_contract_version"],
                "prompt contract version",
                MAX_PROMPT_CONTRACT_UNITS,
            ),
            proposed_at=_utc_timestamp(row["proposed_at_utc"], "proposal time"),
            confirmed_version_number=_optional_positive_int(
                row["confirmed_version_number"], "confirmed version"
            ),
            confirmed_at=_utc_timestamp(
                row["confirmed_at_utc"], "confirmed time", required=False
            ),
            statements=tuple(sorted(statements, key=lambda item: item.ordinal)),
        )

    def save_requirement_proposal_for_owner(
        self,
        user_key,
        source_key,
        expected_version_token,
        statements,
        model_name,
        prompt_contract_version,
    ):
        """Record AI step 2's validated statement proposals.

        Writes one proposal version for the working session, replacing any
        earlier one. A working session is ephemeral infrastructure, not a
        member-visible history: keeping superseded AI proposals around would
        be a second copy of employer wording with nothing to show for it. The
        version number still increments, so which run produced the confirmed
        set stays answerable, and OS-4's saved slate pins the confirmed
        content into its own snapshot.
        """
        self._require_user_key(user_key)
        clean_source_key = self._require_source_key(source_key)
        expected_row_version = self._require_expected_row_version(
            expected_version_token
        )
        if not isinstance(statements, (list, tuple)) or not statements:
            raise OpportunitySlateServiceError(
                "Invalid statement proposals.", code="invalid"
            )
        if len(statements) > 60:
            raise OpportunitySlateServiceError(
                "Too many statement proposals.", code="invalid"
            )

        payload = []
        for ordinal, statement in enumerate(statements, start=1):
            if not isinstance(statement, dict):
                raise OpportunitySlateServiceError(
                    "Invalid statement proposal.", code="invalid"
                )
            payload.append(
                {
                    "ordinal": ordinal,
                    "span_start": _non_negative_int(
                        statement.get("span_start"), "span start"
                    ),
                    "span_length": _positive_int(
                        statement.get("span_length"), "span length"
                    ),
                    "employer_text": _bounded_text(
                        statement.get("employer_text"),
                        "employer wording",
                        MAX_STATEMENT_TEXT_UNITS,
                    ),
                    "proposed_class": _bounded_choice(
                        statement.get("proposed_class"),
                        STATEMENT_CLASSES,
                        "proposed classification",
                    ),
                    "proposed_explanation": _bounded_text(
                        statement.get("proposed_explanation"),
                        "explanation",
                        MAX_EXPLANATION_UNITS,
                    ),
                    "proposed_structure_json": _encode_structure(
                        statement.get("proposed_paths")
                    ),
                }
            )

        row = self.database.first_row(
            "usp_SaveOpportunityRequirementProposalForOwner",
            [
                ("@UserKey", user_key),
                ("@SourceKey", clean_source_key),
                ("@ExpectedRowVersion", expected_row_version),
                (
                    "@ModelName",
                    _bounded_text(model_name, "model name", MAX_MODEL_NAME_UNITS),
                ),
                (
                    "@PromptContractVersion",
                    _bounded_text(
                        prompt_contract_version,
                        "prompt contract version",
                        MAX_PROMPT_CONTRACT_UNITS,
                    ),
                ),
                (
                    "@StatementsJson",
                    json.dumps(payload, separators=(",", ":"), ensure_ascii=False),
                ),
            ],
        )
        _require_exact_fields(row, SAVE_PROPOSAL_ROW_FIELDS, "proposal result")
        self._raise_for_fenced_outcome(row["outcome"], "requirement proposal")
        return {
            "outcome": "success",
            "requirement_set_key": _opaque_key(
                row["requirement_set_key"], "requirement set key"
            ),
            "version_number": _positive_int(row["version_number"], "set version"),
            "statement_count": _positive_int(
                row["statement_count"], "statement count"
            ),
        }

    def correct_requirement_statement_for_owner(
        self,
        user_key,
        statement_key,
        expected_version_token,
        member_class=None,
        member_clarification=None,
    ):
        """The member's correction of one statement's meaning.

        Reclassification and clarification are stored in their own columns
        beside the AI proposal, never over it. Correcting a statement clears
        the requirement-set confirmation, exactly as correcting the source
        clears the source confirmation: a confirmed set must never describe
        a reading the member has since changed.
        """
        self._require_user_key(user_key)
        clean_statement_key = self._require_source_key(statement_key)
        expected_row_version = self._require_expected_row_version(
            expected_version_token
        )
        if member_class is not None:
            member_class = _bounded_choice(
                member_class, STATEMENT_CLASSES, "classification"
            )
        if member_clarification is not None:
            cleaned = member_clarification.strip() if isinstance(
                member_clarification, str
            ) else ""
            if not cleaned:
                member_clarification = None
            elif utf16_length(cleaned) > MAX_CLARIFICATION_UNITS:
                raise OpportunitySlateServiceError(
                    f"That clarification is longer than "
                    f"{MAX_CLARIFICATION_UNITS:,} characters.",
                    code="too_long",
                )
            else:
                member_clarification = cleaned

        row = self.database.first_row(
            "usp_CorrectOpportunityRequirementStatementForOwner",
            [
                ("@UserKey", user_key),
                ("@StatementKey", clean_statement_key),
                ("@ExpectedRowVersion", expected_row_version),
                ("@MemberClass", member_class),
                ("@MemberClarification", member_clarification),
            ],
        )
        _require_exact_fields(
            row, CORRECT_STATEMENT_ROW_FIELDS, "statement correction result"
        )
        self._raise_for_fenced_outcome(row["outcome"], "statement correction")
        applied_class = row["member_class"]
        if applied_class is not None:
            applied_class = _bounded_choice(
                applied_class, STATEMENT_CLASSES, "classification"
            )
        return {
            "outcome": "success",
            "statement_version_token": _version_token(
                row["statement_row_version"], "statement row version"
            ),
            "member_class": applied_class,
        }

    def confirm_requirements_for_owner(
        self, user_key, requirement_set_key, expected_version_token
    ):
        """Checkpoint 2 of 2. Records which requirement set the member
        accepted.

        It saves no slate, produces no alignment result, and calls no AI. The
        alignment analysis it precedes is slice OS-3 and does not exist yet.
        """
        self._require_user_key(user_key)
        clean_set_key = self._require_source_key(requirement_set_key)
        expected_row_version = self._require_expected_row_version(
            expected_version_token
        )

        row = self.database.first_row(
            "usp_ConfirmOpportunityRequirementsForOwner",
            [
                ("@UserKey", user_key),
                ("@RequirementSetKey", clean_set_key),
                ("@ExpectedRowVersion", expected_row_version),
            ],
        )
        _require_exact_fields(
            row, CONFIRM_REQUIREMENTS_ROW_FIELDS, "requirement confirmation result"
        )
        self._raise_for_fenced_outcome(row["outcome"], "requirement confirmation")
        return {
            "outcome": "success",
            "set_version_token": _version_token(
                row["set_row_version"], "set row version"
            ),
            "confirmed_version_number": _positive_int(
                row["confirmed_version_number"], "confirmed version"
            ),
        }

    # ------------------------------------------------------------------
    # Slice OS-3: the evidence allowlist, the alignment analysis, and the
    # member's responses.
    #
    # The evidence read is READ ONLY over the member's own Workshop library.
    # Nothing in this module writes a knowledge item, a moment, or any other
    # canonical record: an analysis references evidence by key and pinned
    # version and copies only a bounded excerpt for identifiability.
    # ------------------------------------------------------------------

    def list_evidence_for_owner(self, user_key, *, max_items=MAX_EVIDENCE_ITEMS):
        """This owner's confirmed evidence, bounded, newest first.

        Only CONFIRMED, unarchived knowledge items: a draft or a suggestion is
        not something the member has authorized as evidence about themselves,
        so it never reaches a prompt. An empty list is an ordinary answer and
        the caller renders a truthful "nothing to compare against" screen
        rather than a failure.
        """
        self._require_user_key(user_key)
        bounded = max(1, min(int(max_items or MAX_EVIDENCE_ITEMS), MAX_EVIDENCE_ITEMS))
        result_sets = self.database.execute_procedure(
            "usp_ListOpportunityEvidenceForOwner",
            [("@UserKey", user_key), ("@MaxItems", bounded)],
        )
        rows = result_sets[0] if result_sets else []
        return tuple(_serialize_evidence_row(row) for row in rows)

    def get_analysis_for_owner(self, user_key):
        """``(analysis_or_None, responses_by_statement_key)``.

        The analysis is ``None`` when none has been run for the current
        requirement-set version — deliberately a different fact from "it ran
        and established nothing", which is an analysis whose statements are
        all ``not_enough_information``, and the screen says the two
        differently. Responses are returned either way: they are the member's
        own words and belong to the qualification, not to any one run.
        """
        self._require_user_key(user_key)
        result_sets = self.database.execute_procedure(
            "usp_GetOpportunityAnalysisForOwner",
            [("@UserKey", user_key)],
        )
        result_sets = list(result_sets or [])
        while len(result_sets) < 4:
            result_sets.append([])

        responses = {}
        for row in result_sets[3]:
            view = _serialize_response_row(row)
            responses[view.statement_key] = view

        analysis_rows = result_sets[0]
        if not analysis_rows:
            return None, responses

        row = analysis_rows[0]
        _require_exact_fields(row, ANALYSIS_ROW_FIELDS, "analysis row")

        citations_by_statement = {}
        for citation_row in result_sets[2]:
            _require_exact_fields(
                citation_row, ANALYSIS_CITATION_ROW_FIELDS, "citation row"
            )
            key = _opaque_key(citation_row["statement_key"], "statement key")
            citations_by_statement.setdefault(key, []).append(
                _serialize_citation_row(citation_row)
            )

        statements = []
        for statement_row in result_sets[1]:
            _require_exact_fields(
                statement_row, ANALYSIS_STATEMENT_ROW_FIELDS, "analysis statement row"
            )
            key = _opaque_key(statement_row["statement_key"], "statement key")
            citations = tuple(
                sorted(
                    citations_by_statement.get(key, ()),
                    key=lambda item: item.ordinal,
                )
            )
            status = _bounded_choice(
                statement_row["derived_status"], ALIGNMENT_STATUSES, "alignment status"
            )
            count = _non_negative_int(statement_row["citation_count"], "citation count")
            if len(citations) != count:
                # The stored count and the stored citations are two records of
                # one fact. Disagreeing means the row is not trustworthy, and a
                # trustworthy failure beats a plausible screen.
                raise OpportunitySlateServiceError(
                    "The analysis result is incomplete.", code="invalid"
                )
            if (count == 0) != (status == "not_enough_information"):
                # The database CHECK says the same thing; asserted again here
                # so a future procedure edit cannot quietly present a
                # "supported" result with nothing behind it.
                raise OpportunitySlateServiceError(
                    "The analysis result is incomplete.", code="invalid"
                )
            statements.append(
                AnalysisStatementView(
                    statement_key=key,
                    ordinal=_positive_int(statement_row["ordinal"], "ordinal"),
                    status=status,
                    citation_count=count,
                    citations=citations,
                )
            )

        if not statements:
            raise OpportunitySlateServiceError(
                "The analysis result is incomplete.", code="invalid"
            )

        analysis = AnalysisView(
            analysis_key=_opaque_key(row["analysis_key"], "analysis key"),
            version_token=_version_token(
                row["analysis_row_version"], "analysis row version"
            ),
            source_version_number=_positive_int(
                row["source_version_number"], "source version"
            ),
            requirement_version_number=_positive_int(
                row["requirement_version_number"], "requirement version"
            ),
            model_name=_bounded_text(
                row["model_name"], "model name", MAX_MODEL_NAME_UNITS
            ),
            prompt_contract_version=_bounded_text(
                row["prompt_contract_version"],
                "prompt contract version",
                MAX_PROMPT_CONTRACT_UNITS,
            ),
            evidence_considered_count=_non_negative_int(
                row["evidence_considered_count"], "evidence count"
            ),
            qualification_count=_positive_int(
                row["qualification_count"], "qualification count"
            ),
            analyzed_at=_utc_timestamp(row["analyzed_at_utc"], "analysis time"),
            statements=tuple(sorted(statements, key=lambda item: item.ordinal)),
        )
        return analysis, responses

    def save_analysis_for_owner(
        self,
        user_key,
        requirement_set_key,
        expected_version_token,
        results,
        model_name,
        prompt_contract_version,
        evidence_considered_count,
    ):
        """Record one validated, grounded alignment analysis.

        ``results`` arrive already validated and DERIVED by
        ``services/opportunity_analysis_service.py``; every field is re-bounded
        here before it reaches the database, because the two layers are
        allowed to be corrected independently. Nothing in this method computes
        or accepts an aggregate — there is no field for one.
        """
        self._require_user_key(user_key)
        clean_set_key = self._require_source_key(requirement_set_key)
        expected_row_version = self._require_expected_row_version(
            expected_version_token
        )
        if not isinstance(results, (list, tuple)) or not results:
            raise OpportunitySlateServiceError(
                "Invalid analysis results.", code="invalid"
            )
        if len(results) > MAX_ANALYSED_STATEMENTS:
            raise OpportunitySlateServiceError(
                "Too many analysis results.", code="invalid"
            )

        payload = []
        for result in results:
            if not isinstance(result, dict):
                raise OpportunitySlateServiceError(
                    "Invalid analysis result.", code="invalid"
                )
            citations = result.get("citations") or []
            if not isinstance(citations, (list, tuple)):
                raise OpportunitySlateServiceError(
                    "Invalid analysis citations.", code="invalid"
                )
            if len(citations) > MAX_CITATIONS_PER_STATEMENT:
                raise OpportunitySlateServiceError(
                    "Too many analysis citations.", code="invalid"
                )
            status = _bounded_choice(
                result.get("status"), ALIGNMENT_STATUSES, "alignment status"
            )
            if (len(citations) == 0) != (status == "not_enough_information"):
                raise OpportunitySlateServiceError(
                    "Invalid analysis result.", code="invalid"
                )
            payload.append(
                {
                    "statement_key": _opaque_key(
                        result.get("statement_key"), "statement key"
                    ),
                    "derived_status": status,
                    "citation_count": len(citations),
                    # Independent review finding F7. The evidence IDENTITY is
                    # no longer sent: usp_SaveOpportunityAnalysisForOwner reads
                    # the version, the title and the kind out of the member's
                    # own confirmed Workshop item, exactly as its sibling
                    # usp_SaveOpportunityResponseForOwner already did. Sending
                    # them here would put three fields in the payload that
                    # nothing reads, which is how a caller comes to believe it
                    # controls them.
                    "citations": [
                        {
                            "ordinal": ordinal,
                            "clause_ordinal": _positive_int(
                                citation.get("clause_ordinal"), "clause ordinal"
                            ),
                            "covered_text": _bounded_text(
                                citation.get("covered_text"),
                                "covered wording",
                                MAX_COVERED_TEXT_UNITS,
                            ),
                            "evidence_key": _opaque_key(
                                citation.get("evidence_key"), "evidence key"
                            ),
                            "excerpt": _bounded_text(
                                citation.get("excerpt"),
                                "evidence excerpt",
                                MAX_EXCERPT_UNITS,
                            ),
                        }
                        for ordinal, citation in enumerate(citations, start=1)
                    ],
                }
            )

        row = self.database.first_row(
            "usp_SaveOpportunityAnalysisForOwner",
            [
                ("@UserKey", user_key),
                ("@RequirementSetKey", clean_set_key),
                ("@ExpectedRowVersion", expected_row_version),
                (
                    "@ModelName",
                    _bounded_text(model_name, "model name", MAX_MODEL_NAME_UNITS),
                ),
                (
                    "@PromptContractVersion",
                    _bounded_text(
                        prompt_contract_version,
                        "prompt contract version",
                        MAX_PROMPT_CONTRACT_UNITS,
                    ),
                ),
                (
                    "@EvidenceConsideredCount",
                    _non_negative_int(
                        evidence_considered_count, "evidence count"
                    ),
                ),
                (
                    "@ResultsJson",
                    json.dumps(payload, separators=(",", ":"), ensure_ascii=False),
                ),
            ],
        )
        _require_exact_fields(row, SAVE_ANALYSIS_ROW_FIELDS, "analysis result")
        self._raise_for_fenced_outcome(row["outcome"], "alignment analysis")
        return {
            "outcome": "success",
            "analysis_key": _opaque_key(row["analysis_key"], "analysis key"),
            "qualification_count": _positive_int(
                row["qualification_count"], "qualification count"
            ),
        }

    def save_response_for_owner(
        self,
        user_key,
        statement_key,
        expected_version_token,
        response_kind,
        response_text=None,
        authored_via="typed",
        connected_evidence_key=None,
    ):
        """Record the member's own answer to one qualification.

        The connected-evidence path passes a KEY only: the procedure reads the
        title and the confirmed version from the member's own library, so this
        layer can never label somebody else's record or pin a version that
        does not exist.
        """
        self._require_user_key(user_key)
        clean_statement_key = self._require_source_key(statement_key)
        expected_row_version = self._require_expected_row_version(
            expected_version_token
        )
        kind = _bounded_choice(response_kind, RESPONSE_KINDS, "response kind")
        provenance = _bounded_choice(
            authored_via, AUTHORED_VIA_VALUES, "response provenance"
        )

        cleaned_text = None
        if kind in {"tell_more", "real_example"}:
            cleaned_text = response_text.strip() if isinstance(response_text, str) else ""
            if not cleaned_text:
                raise OpportunitySlateServiceError(
                    "Add your response before continuing.", code="required"
                )
            if utf16_length(cleaned_text) > MAX_RESPONSE_TEXT_UNITS:
                raise OpportunitySlateServiceError(
                    f"That response is longer than {MAX_RESPONSE_TEXT_UNITS:,} "
                    "characters.",
                    code="too_long",
                )

        evidence_key = None
        if kind == "connect_evidence":
            evidence_key = normalize_source_key(connected_evidence_key)
            if not evidence_key:
                raise OpportunitySlateServiceError(
                    "Choose which evidence to connect.", code="required"
                )

        row = self.database.first_row(
            "usp_SaveOpportunityResponseForOwner",
            [
                ("@UserKey", user_key),
                ("@StatementKey", clean_statement_key),
                ("@ExpectedRowVersion", expected_row_version),
                ("@ResponseKind", kind),
                ("@ResponseText", cleaned_text),
                ("@AuthoredVia", provenance),
                ("@ConnectedEvidenceKey", evidence_key),
            ],
        )
        _require_exact_fields(row, SAVE_RESPONSE_ROW_FIELDS, "response result")
        self._raise_for_fenced_outcome(row["outcome"], "response")
        return {
            "outcome": "success",
            "response_key": _opaque_key(row["response_key"], "response key"),
            "response_kind": _bounded_choice(
                row["response_kind"], RESPONSE_KINDS, "response kind"
            ),
        }

    # -----------------------------------------------------------------
    # Slice OS-4 — the save lifecycle.
    # -----------------------------------------------------------------

    def get_saved_slate_for_owner(self, user_key, saved_result_key=None):
        """This owner's saved slate opened at one saved version, or ``None``.

        ``None`` means "no saved slate", which is a different fact from "the
        working analysis is unsaved" and the screen says the two differently.
        A ``saved_result_key`` that is not this owner's also returns ``None``:
        not-found and not-yours are indistinguishable here, exactly as they
        are on every route in this room.
        """
        self._require_user_key(user_key)
        requested = (
            self._require_source_key(saved_result_key)
            if saved_result_key
            else None
        )
        result_sets = self.database.execute_procedure(
            "usp_GetOpportunitySavedSlateForOwner",
            [("@UserKey", user_key), ("@SavedResultKey", requested)],
        )
        result_sets = list(result_sets or [])
        while len(result_sets) < 5:
            result_sets.append([])

        slate_rows = result_sets[0]
        if not slate_rows:
            return None
        row = slate_rows[0]
        _require_exact_fields(row, SLATE_ROW_FIELDS, "saved slate row")

        evidence_by_qualification = {}
        for evidence_row in result_sets[3]:
            view = _serialize_saved_evidence_row(evidence_row)
            evidence_by_qualification.setdefault(
                evidence_row["qualification_id"], []
            ).append(view)

        qualifications = []
        for qualification_row in result_sets[2]:
            key = qualification_row["qualification_id"]
            evidence = tuple(
                sorted(
                    evidence_by_qualification.get(key, ()),
                    key=lambda item: item.ordinal,
                )
            )
            qualifications.append(
                _serialize_saved_qualification_row(qualification_row, evidence)
            )
        if not qualifications:
            # A saved result with no qualifications cannot be created — the
            # procedure refuses a payload with none — so an empty read means
            # the rows disagree, and a trustworthy failure beats a plausible
            # screen.
            raise OpportunitySlateServiceError(
                "The saved result is incomplete.", code="invalid"
            )

        currency = []
        for currency_row in result_sets[4]:
            _require_exact_fields(
                currency_row, SAVED_CURRENCY_ROW_FIELDS, "saved currency row"
            )
            if currency_row["evidence_kind"] not in SAVED_EVIDENCE_CURRENCY_KINDS:
                # Finding F6. Unreachable today — AI step 3 stores the literal
                # `knowledge_item` and nothing else writes saved evidence — and
                # deliberately loud rather than silently stale if that changes.
                raise OpportunitySlateServiceError(
                    "The saved result is incomplete.", code="invalid"
                )
            currency.append(
                (
                    _opaque_key(currency_row["evidence_key"], "evidence key"),
                    _positive_int(currency_row["pinned_version"], "pinned version"),
                    _optional_positive_int(
                        currency_row["current_version"], "current version"
                    ),
                )
            )

        versions = tuple(
            _serialize_saved_version_row(version_row)
            for version_row in result_sets[1][:MAX_SAVED_VERSIONS_LISTED]
        )

        return SavedSlateView(
            slate_key=_opaque_key(row["slate_key"], "slate key"),
            version_token=_version_token(
                row["slate_row_version"], "slate row version"
            ),
            created_at=_utc_timestamp(row["slate_created_at_utc"], "slate time"),
            total_version_count=_positive_int(
                row["current_save_version_number"], "save version count"
            ),
            saved_result_key=_opaque_key(
                row["saved_result_key"], "saved result key"
            ),
            save_version_number=_positive_int(
                row["save_version_number"], "save version"
            ),
            source_version_number=_positive_int(
                row["source_version_number"], "source version"
            ),
            requirement_version_number=_positive_int(
                row["requirement_version_number"], "requirement version"
            ),
            saved_analysis_key=_opaque_key(
                row["saved_analysis_key"], "analysis key"
            ),
            source_text=_bounded_text(
                row["source_text"], "saved source", MAX_SOURCE_TEXT_UNITS
            ),
            model_name=_bounded_text(
                row["model_name"], "model name", MAX_MODEL_NAME_UNITS
            ),
            prompt_contract_version=_bounded_text(
                row["prompt_contract_version"],
                "prompt contract version",
                MAX_PROMPT_CONTRACT_UNITS,
            ),
            evidence_considered_count=_non_negative_int(
                row["evidence_considered_count"], "evidence count"
            ),
            qualification_count=_positive_int(
                row["qualification_count"], "qualification count"
            ),
            input_fingerprint=_fingerprint(row["input_fingerprint"]),
            saved_at=_utc_timestamp(row["saved_at_utc"], "save time"),
            qualifications=tuple(
                sorted(qualifications, key=lambda item: item.ordinal)
            ),
            versions=versions,
            evidence_currency=tuple(currency),
        )

    def save_slate_for_owner(
        self,
        user_key,
        idempotency_key,
        requirement_set_key,
        expected_version_token,
        input_fingerprint,
    ):
        """`Save privately`. Creates one immutable saved result.

        Idempotent: a repeated ``idempotency_key`` for the same owner returns
        the saved version it already created (outcome ``existing``) rather
        than appending a second one, so a double-submitted footer cannot make
        two saves out of one intention.

        The CONTENT is not passed. The procedure builds the snapshot from this
        owner's own confirmed source, confirmed requirement set, current
        analysis and responses, so this layer cannot choose what a saved
        result says about the member. The only two values it supplies are the
        idempotency key and the fingerprint — and the fingerprint is a derived
        currency cache, not a permission: a wrong one can make a result look
        stale, never make a stale one look current, because the read side
        recomputes both sides from server-read facts.
        """
        self._require_user_key(user_key)
        if not isinstance(idempotency_key, str) or not idempotency_key.strip():
            raise OpportunitySlateServiceError(
                "An idempotency key is required.", code="required"
            )
        if utf16_length(idempotency_key) > MAX_IDEMPOTENCY_KEY_UNITS:
            raise OpportunitySlateServiceError(
                "Idempotency key exceeds its limit.", code="too_long"
            )
        clean_set_key = self._require_source_key(requirement_set_key)
        expected_row_version = self._require_expected_row_version(
            expected_version_token
        )

        row = self.database.first_row(
            "usp_SaveOpportunitySlateForOwner",
            [
                ("@UserKey", user_key),
                ("@IdempotencyKey", idempotency_key),
                ("@RequirementSetKey", clean_set_key),
                ("@ExpectedRowVersion", expected_row_version),
                ("@InputFingerprint", _fingerprint(input_fingerprint)),
            ],
        )
        _require_exact_fields(row, SAVE_SLATE_ROW_FIELDS, "saved slate result")
        outcome = row["outcome"]
        if outcome not in {"success", "existing"} or not row["saved_result_key"]:
            # Reuse the shared fence so `changed` and `invalid` raise the
            # codes the route already knows how to render, and never report a
            # save without an exact, non-falsy key.
            self._raise_for_fenced_outcome(outcome, "saved slate")
            raise OpportunitySlateServiceError(
                "The saved slate could not be created.", code="not_found"
            )
        return {
            "outcome": outcome,
            "slate_key": _opaque_key(row["slate_key"], "slate key"),
            "saved_result_key": _opaque_key(
                row["saved_result_key"], "saved result key"
            ),
            "save_version_number": _positive_int(
                row["save_version_number"], "save version"
            ),
            "qualification_count": _positive_int(
                row["qualification_count"], "qualification count"
            ),
        }

    def delete_saved_slate_for_owner(
        self, user_key, slate_key, expected_version_token
    ):
        """The member's explicit deletion of their saved slate.

        Atomic and complete: pinned evidence, saved qualifications, every
        saved version, then the slate. It reaches no working data — the
        member may still be using their session — and a failure leaves the
        slate whole, which is the promise image 09-d makes on screen.
        """
        self._require_user_key(user_key)
        clean_slate_key = self._require_source_key(slate_key)
        expected_row_version = self._require_expected_row_version(
            expected_version_token
        )

        row = self.database.first_row(
            "usp_DeleteOpportunitySavedSlateForOwner",
            [
                ("@UserKey", user_key),
                ("@SlateKey", clean_slate_key),
                ("@ExpectedRowVersion", expected_row_version),
            ],
        )
        _require_exact_fields(row, DELETE_SLATE_ROW_FIELDS, "slate delete result")
        self._raise_for_fenced_outcome(row["outcome"], "saved slate")
        return {
            "outcome": "success",
            "deleted_result_count": _non_negative_int(
                row["deleted_result_count"], "deleted result count"
            ),
        }

    @staticmethod
    def _raise_for_fenced_outcome(outcome, label):
        if outcome == "success":
            return
        if outcome == "changed":
            raise OpportunitySlateServiceError(
                "This role source changed. Review it and try again.", code="changed"
            )
        if outcome == "invalid":
            raise OpportunitySlateServiceError(
                f"The {label} could not be applied.", code="invalid"
            )
        # An unrecognized outcome is a false-success guard, never a pass.
        raise OpportunitySlateServiceError(
            f"The {label} could not be completed.", code="not_found"
        )


opportunity_slate_service = OpportunitySlateService()
