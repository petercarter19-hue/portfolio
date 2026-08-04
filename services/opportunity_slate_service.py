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

_SAVE_OUTCOMES = frozenset({"success", "existing", "unchanged"})


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
        if capture_method not in OS1_CAPTURE_METHODS:
            # Slice OS-1 has no dictation, upload, or import path. Refusing
            # the other enum values here keeps an unbuilt capture method
            # from ever being recorded as provenance for text that was in
            # fact pasted.
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
