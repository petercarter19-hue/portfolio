"""Opportunity Slate REPLACEMENT working session — PS-OPPORTUNITY-SLATE-002,
slice R1 (shell + stage-1 intake + stage-2 captured-source review).

Package: docs/initiatives/PS-OPPORTUNITY-SLATE-002. Controlling contract:
artifacts/2026-08-11-opportunity-slate-architecture/
OPPORTUNITY_SLATE_ARCHITECTURE.md, sections 5.1-5.3 (data architecture),
6.1 (source capture), 6.6 (working-opportunity lifetime), 6.10
(authorization boundaries).

**No AI call happens anywhere in this module, and it imports no AI-capable
module.** R1 has no interpretation, no alignment, and no AI step of any
kind (architecture section 7 is entirely R2+). This is the same structural
guardrail ``services/opportunity_slate_service.py`` carries for the legacy
room, replicated here rather than imported from there — this module is
self-contained by design (architecture section 9 names exactly two modules
the replacement reuses, ``opportunity_source_intake_service`` and, from R2,
``opportunity_analysis_service``; this file is not one of them and does not
import the legacy ``opportunity_slate_service`` module either).

**Table reuse, not code reuse.** R1's source capture/correction/confirm/
delete/read all call the SAME PS-OPPSLATE-001 stored procedures the legacy
room calls (``usp_SaveOpportunitySourceForOwner`` and friends) — the
architecture's "reuses the existing tables wherever the truth shape is
unchanged" (section 5.1) applied at the schema layer. This module owns its
own thin Python wrapper around that same procedure surface, plus the two
PS-OPPSLATE-004 procedures new in this slice
(``usp_SaveOpportunitySourceIdentityForOwner`` /
``usp_GetOpportunitySourceIdentityForOwner``). Not one procedure call here
mutates a legacy row differently than the legacy service already does.

Three data classes stay apart (architecture section 2's owner truth-type
table): the employer's captured wording (``original_text``, write-once),
the member's own correction and identity metadata (``member_corrected_text``,
``opportunity_source_identities``), and — starting in R2 — PeerSlate's AI
proposals. Nothing in R1 writes a proposal column; nothing here can, since
no proposal column is ever referenced.

Row discipline, error codes, ``rowversion`` optimistic concurrency, and the
idempotent-create guard mirror ``services/opportunity_slate_service.py``,
which itself mirrors ``services/knowledge_service.py``. Re-implemented here
rather than imported, for the file-ownership reason those modules already
give for each other.
"""

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from services.database_service import database_service


# Hard server-side cap on pasted/typed/uploaded/imported employer wording,
# in UTF-16 code units. Matches CK_opportunity_source_versions_original_length
# on the shared PS-OPPSLATE-001 table exactly, so a malformed request is
# rejected here, before any database round trip, with the limit the
# database itself would apply.
MAX_SOURCE_TEXT_UNITS = 20000

# Matches the new CK_opportunity_source_identities_employer_length /
# CK_opportunity_source_identities_role_length CHECK bounds (PS-OPPSLATE-004).
MAX_IDENTITY_FIELD_UNITS = 200

MAX_IDEMPOTENCY_KEY_UNITS = 200

# How long an idle working session stays reachable. The architecture
# proposes making the replacement's working opportunity durable until the
# member deletes or replaces it (decision D-1, open); until Pete decides,
# this module keeps the existing PS-OPPSLATE-001 48-hour expiry rather than
# silently changing retention behavior.
WORKING_SESSION_TTL_HOURS = 48

# Image 04 shows three capture entry points (paste/type, upload, import);
# a fourth, dictation, edits the SAME textarea client-side and its result
# always posts as "pasted" text (architecture section 6.1: "dictated ...
# lands as pasted text with authored_via provenance"). "dictated" is
# therefore never a value this module sends to the database, exactly like
# the legacy OS-6 service's own capture-method set.
CAPTURE_METHODS = frozenset({"pasted", "uploaded", "imported"})

WORKBENCH_STATES = frozenset(
    {
        "role_intake",
        "review_source",
        "source_confirmed",
        # R1 has no requirement review; these two states cannot yet be
        # reached, but the shared PS-OPPSLATE-001 table's CHECK already
        # allows them (OS-2 wrote it), so this set stays faithful to the
        # database contract rather than narrower than it.
        "review_requirements",
        "requirements_confirmed",
    }
)

# The whole vocabulary today (architecture section 4.2's "Source type — Job
# posting" meta row); CHECK-pinned identically on
# opportunity_source_identities.source_type.
SOURCE_TYPES = frozenset({"job_posting"})

_VERSION_TOKEN = re.compile(r"^[0-9a-f]{16}$")

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
IDENTITY_SAVE_ROW_FIELDS = frozenset({"outcome", "source_row_version"})
IDENTITY_GET_ROW_FIELDS = frozenset({"employer_name", "role_title", "source_type"})

_SAVE_OUTCOMES = frozenset({"success", "existing", "unchanged"})


class OpportunitySlateV2ServiceError(RuntimeError):
    """Raised when a replacement-room working-session operation cannot be
    completed safely.

    ``.code`` is one of ``required``, ``invalid``, ``too_long``,
    ``changed``, ``not_found``, or ``unavailable`` — the same vocabulary
    ``services/opportunity_slate_service.py`` and
    ``services/knowledge_service.py`` use, so the route layer's copy
    mapping can follow the exact same shape.
    """

    def __init__(self, message, code="unavailable"):
        super().__init__(message)
        self.code = code


def utf16_length(value):
    """Match SQL Server nvarchar and browser maxlength code-unit counting."""
    return len(value.encode("utf-16-le")) // 2


def _require_exact_fields(row, expected, label):
    """Set-equality row discipline: a row missing an expected field OR
    carrying an extra one is rejected outright rather than silently passed
    through or truncated."""
    if not isinstance(row, dict) or set(row) != set(expected):
        raise OpportunitySlateV2ServiceError(
            f"Unexpected {label} result shape.", code="invalid"
        )


def _opaque_key(value, label):
    try:
        return str(UUID(str(value)))
    except (TypeError, ValueError, AttributeError) as error:
        raise OpportunitySlateV2ServiceError(
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
        raise OpportunitySlateV2ServiceError(f"Invalid {label}.", code="invalid")
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
            raise OpportunitySlateV2ServiceError(f"Invalid {label}.", code="invalid")
        return None
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as error:
            raise OpportunitySlateV2ServiceError(
                f"Invalid {label}.", code="invalid"
            ) from error
    else:
        raise OpportunitySlateV2ServiceError(f"Invalid {label}.", code="invalid")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _isoformat(value):
    return None if value is None else value.isoformat().replace("+00:00", "Z")


def _positive_int(value, label):
    try:
        parsed = int(value)
    except (TypeError, ValueError) as error:
        raise OpportunitySlateV2ServiceError(
            f"Invalid {label}.", code="invalid"
        ) from error
    if isinstance(value, bool) or parsed < 1:
        raise OpportunitySlateV2ServiceError(f"Invalid {label}.", code="invalid")
    return parsed


def _optional_positive_int(value, label):
    if value is None:
        return None
    return _positive_int(value, label)


def _non_negative_int(value, label):
    try:
        parsed = int(value)
    except (TypeError, ValueError) as error:
        raise OpportunitySlateV2ServiceError(
            f"Invalid {label}.", code="invalid"
        ) from error
    if isinstance(value, bool) or parsed < 0:
        raise OpportunitySlateV2ServiceError(f"Invalid {label}.", code="invalid")
    return parsed


def _bounded_choice(value, allowed, label):
    if value not in allowed:
        raise OpportunitySlateV2ServiceError(f"Invalid {label}.", code="invalid")
    return value


def _bounded_text(value, label, max_units):
    if not isinstance(value, str) or not value:
        raise OpportunitySlateV2ServiceError(f"Invalid {label}.", code="invalid")
    if utf16_length(value) > max_units:
        raise OpportunitySlateV2ServiceError(f"Invalid {label}.", code="invalid")
    return value


def _optional_bounded_text(value, label, max_units):
    """Blank-to-``None`` normalization for an optional member-entered field
    (image 05's Employer / Role title inputs). An empty submit clears the
    field rather than storing an empty string, matching the database's
    ``NULLIF(LTRIM(RTRIM(...)), N'')`` normalization exactly, so what the
    service validates is what the procedure actually stores.
    """
    if value is None:
        return None
    if not isinstance(value, str):
        raise OpportunitySlateV2ServiceError(f"Invalid {label}.", code="invalid")
    cleaned = value.strip()
    if not cleaned:
        return None
    if utf16_length(cleaned) > max_units:
        raise OpportunitySlateV2ServiceError(
            f"That {label} is longer than {max_units:,} characters.",
            code="too_long",
        )
    return cleaned


def normalize_source_key(value):
    """Opaque-key normalization with the house null-on-failure idiom: a
    malformed key is indistinguishable from an absent one, so a caller can
    never probe for another member's key."""
    try:
        return str(UUID(str(value)))
    except (TypeError, ValueError, AttributeError):
        return None


def normalize_session_key(value):
    try:
        return str(UUID(str(value)))
    except (TypeError, ValueError, AttributeError):
        return None


def validate_source_text(value, *, label="role text"):
    """The single hard cap on captured employer wording.

    Shared shape with ``services/opportunity_slate_service.validate_source_text``
    (same limit, same stripping behavior) so the replacement can never end
    up with a looser bound than the legacy room. Returns the text with its
    surrounding whitespace stripped; interior wording, including blank
    lines between sections, is preserved verbatim — this is the employer's
    text, not ours to reflow.

    Raises :class:`OpportunitySlateV2ServiceError` with ``.code`` in
    ``{"required", "too_long"}`` so the route re-renders the member's own
    text with a named error instead of discarding it.
    """
    cleaned = value.strip() if isinstance(value, str) else ""
    if not cleaned:
        raise OpportunitySlateV2ServiceError(
            f"Add the {label} before continuing.", code="required"
        )
    if utf16_length(cleaned) > MAX_SOURCE_TEXT_UNITS:
        raise OpportunitySlateV2ServiceError(
            f"That {label} is longer than {MAX_SOURCE_TEXT_UNITS:,} characters.",
            code="too_long",
        )
    return cleaned


@dataclass(frozen=True)
class WorkingSourceView:
    """One member's current working opportunity and its current source
    version.

    ``original_text`` is the employer's captured wording, exactly as it
    arrived. ``member_corrected_text`` is the member's manual correction of
    it, or ``None``. ``display_text`` is what stage 2 renders. The two stay
    separate fields (architecture section 2: employer source and member
    response are different truth types).
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
            row["capture_method"],
            frozenset(CAPTURE_METHODS | {"dictated"}),
            "capture method",
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
class SourceIdentityView:
    """Image 05 section A: employer / role title, member-entered.

    Both fields are ``None`` until the member enters them — the honest
    placeholder state (architecture section 4.2), never a fabricated guess.
    """

    employer_name: str | None
    role_title: str | None
    source_type: str


def _serialize_identity_row(row):
    _require_exact_fields(row, IDENTITY_GET_ROW_FIELDS, "source identity row")
    employer_name = row["employer_name"]
    if employer_name is not None:
        employer_name = _bounded_text(
            employer_name, "employer name", MAX_IDENTITY_FIELD_UNITS
        )
    role_title = row["role_title"]
    if role_title is not None:
        role_title = _bounded_text(role_title, "role title", MAX_IDENTITY_FIELD_UNITS)
    return SourceIdentityView(
        employer_name=employer_name,
        role_title=role_title,
        source_type=_bounded_choice(row["source_type"], SOURCE_TYPES, "source type"),
    )


class OpportunitySlateV2Service:
    """Owner-scoped access to the replacement room's working store.

    Every method takes the server-derived ``user_key`` and passes it
    straight to a procedure that resolves the owner itself. No method
    accepts, derives, or trusts an owner id from a caller.
    """

    def __init__(self, database=None):
        self.database = database or database_service

    @staticmethod
    def _require_user_key(user_key):
        if not isinstance(user_key, str) or not user_key.strip():
            raise OpportunitySlateV2ServiceError(
                "A member key is required.", code="required"
            )
        return user_key

    @staticmethod
    def _require_source_key(source_key):
        normalized = normalize_source_key(source_key)
        if not normalized:
            raise OpportunitySlateV2ServiceError("Invalid source key.", code="invalid")
        return normalized

    @staticmethod
    def _require_session_key(session_key):
        normalized = normalize_session_key(session_key)
        if not normalized:
            raise OpportunitySlateV2ServiceError(
                "Invalid working opportunity key.", code="invalid"
            )
        return normalized

    @staticmethod
    def _require_expected_row_version(version_token):
        decoded = _decode_version_token(version_token)
        if decoded is None:
            # Treated exactly like a stale token: the caller is told the
            # record changed, never that their token was malformed in a way
            # that would help them craft a better one.
            raise OpportunitySlateV2ServiceError(
                "This working opportunity changed. Refresh and try again.",
                code="changed",
            )
        return decoded

    def purge_expired_working_data_for_owner(self, user_key):
        """Destroy this owner's already-expired working data.

        Invoked opportunistically at the start of a room request. It can
        only remove rows whose ``expires_at_utc`` has already passed — rows
        the read already refuses to return — so it is never a
        member-visible deletion. The PS-OPPSLATE-004 takeover means this
        now also clears any source identity for that owner's expired
        source versions; R1 never leaves an orphaned identity row.
        """
        self._require_user_key(user_key)
        row = self.database.first_row(
            "usp_PurgeExpiredOpportunityWorkingData",
            [("@UserKey", user_key)],
        )
        if not row:
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
        """This owner's current working opportunity, or ``None``.

        ``None`` means exactly one thing to the caller: render stage 1
        (bring in a role). It covers "never started", "explicitly
        deleted", and "expired" alike.
        """
        self._require_user_key(user_key)
        row = self.database.first_row(
            "usp_GetOpportunityWorkingSessionForOwner",
            [("@UserKey", user_key)],
        )
        if not row:
            return None
        view = _serialize_working_row(row)
        # Second expiry enforcement, in the application, exactly mirroring
        # the legacy room's own belt-and-braces check.
        if view.expires_at <= datetime.now(timezone.utc):
            return None
        return view

    def save_source_for_owner(
        self, user_key, idempotency_key, source_text, capture_method="pasted"
    ):
        """Capture (or replace) the employer source for this owner (image
        04's ``Review source``).

        Idempotent: a repeated ``idempotency_key`` for the same owner
        returns the version it already created (outcome ``existing``)
        instead of appending a second one. Byte-identical wording under a
        fresh key returns ``unchanged`` and likewise appends nothing.
        """
        self._require_user_key(user_key)
        if not isinstance(idempotency_key, str) or not idempotency_key.strip():
            raise OpportunitySlateV2ServiceError(
                "An idempotency key is required.", code="required"
            )
        if utf16_length(idempotency_key) > MAX_IDEMPOTENCY_KEY_UNITS:
            raise OpportunitySlateV2ServiceError(
                "Idempotency key exceeds its limit.", code="too_long"
            )
        if capture_method not in CAPTURE_METHODS:
            raise OpportunitySlateV2ServiceError(
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
            raise OpportunitySlateV2ServiceError(
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
        """Apply the member's manual correction to the displayed wording
        (image 05 section B).

        The employer's captured ``original_text`` is never touched — the
        correction is stored alongside it. A mismatched
        ``expected_version_token`` raises ``code="changed"``, never a false
        success and never a signal about whether another member's key
        exists.
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
        """Image 05's ``Confirm source``: records which source version the
        member accepted.

        This saves no requirement set, produces nothing, and calls no AI.
        It only records that the member reviewed and accepted this exact
        captured wording — interpretation refuses to run against an
        unconfirmed source (R2).
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
        """The member's explicit discard of the whole working opportunity
        (architecture section 6.9 / adaptation N-5's confirmed target)."""
        self._require_user_key(user_key)
        clean_session_key = self._require_session_key(working_session_key)
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

    def save_source_identity_for_owner(
        self, user_key, source_key, expected_version_token, employer_name, role_title
    ):
        """Image 05 section A: save the member-entered employer / role
        title for the source's CURRENT version.

        Fenced on the same ``opportunity_sources.row_version`` token
        ``correct_source_for_owner``/``confirm_source_for_owner`` already
        use — no new concurrency token is invented. An accepted identity
        upsert advances that shared token so a second client carrying the
        prior token is refused instead of silently overwriting it. The write
        never creates a source version, touches ``original_text``, or clears
        the source's confirmation triple: identity is member metadata, not
        employer wording (architecture section 6.1).
        """
        self._require_user_key(user_key)
        clean_source_key = self._require_source_key(source_key)
        expected_row_version = self._require_expected_row_version(
            expected_version_token
        )
        clean_employer = _optional_bounded_text(
            employer_name, "employer name", MAX_IDENTITY_FIELD_UNITS
        )
        clean_role = _optional_bounded_text(
            role_title, "role title", MAX_IDENTITY_FIELD_UNITS
        )

        row = self.database.first_row(
            "usp_SaveOpportunitySourceIdentityForOwner",
            [
                ("@UserKey", user_key),
                ("@SourceKey", clean_source_key),
                ("@ExpectedRowVersion", expected_row_version),
                ("@EmployerName", clean_employer),
                ("@RoleTitle", clean_role),
            ],
        )
        _require_exact_fields(row, IDENTITY_SAVE_ROW_FIELDS, "identity save result")
        self._raise_for_fenced_outcome(row["outcome"], "source identity")
        return {
            "outcome": "success",
            "source_version_token": _version_token(
                row["source_row_version"], "source row version"
            ),
        }

    def get_source_identity_for_owner(self, user_key, source_key):
        """This owner's saved identity for the source's current version, or
        ``None`` when nothing has been entered yet.

        ``None`` renders the honest placeholder (architecture section 4.2)
        rather than a guess — there is no AI prefill in R1 (decision D-6).
        """
        self._require_user_key(user_key)
        clean_source_key = self._require_source_key(source_key)
        row = self.database.first_row(
            "usp_GetOpportunitySourceIdentityForOwner",
            [
                ("@UserKey", user_key),
                ("@SourceKey", clean_source_key),
            ],
        )
        if not row:
            return None
        return _serialize_identity_row(row)

    @staticmethod
    def _raise_for_fenced_outcome(outcome, label):
        if outcome == "success":
            return
        if outcome == "changed":
            raise OpportunitySlateV2ServiceError(
                "This role source changed. Review it and try again.", code="changed"
            )
        if outcome == "invalid":
            raise OpportunitySlateV2ServiceError(
                f"The {label} could not be applied.", code="invalid"
            )
        # An unrecognized outcome is a false-success guard, never a pass.
        raise OpportunitySlateV2ServiceError(
            f"The {label} could not be completed.", code="not_found"
        )


opportunity_slate_v2_service = OpportunitySlateV2Service()
