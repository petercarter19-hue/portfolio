"""Opportunity Slate ephemeral working session — PS-OPPSLATE-001, slice OS-1.

Package: docs/initiatives/PS-OPPORTUNITY-SLATE-001. Controlling contract:
01_ARCHITECTURE_AND_IMPLEMENTATION_HANDOFF.md sections 8 (data model),
9 (route/service contract), 11 (security/privacy), and 16 (slice OS-1).

This module owns the signed-in member's pre-save workbench: the working
session, the employer source, and its append-only captured versions. It is
deliberately small, because slice OS-1 is deliberately small.

**No AI call happens anywhere in this module.** Extraction concerns and
statement interpretation are OS-2; alignment analysis is OS-3. Nothing here
imports the Anthropic client, and nothing here fabricates a proposal.

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

WORKBENCH_STATES = frozenset({"role_intake", "review_source", "source_confirmed"})

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
