"""Private recruiter questions: the storage seam for PS-ASK-PETE-DIRECT-001.

One member-facing outcome: a visitor who reached the end of what Ask Pete can
answer from public information may send the remaining question to that member
privately, and the member reads it on their own schedule. Nothing here sends,
publishes, or teaches anything.

What this module is careful about, and why:

* **It resolves no identity.** ``submit_question`` is given the RECIPIENT's
  user key by its caller (derived server-side from configuration, never from a
  request payload) and passes that exact string through to
  ``@OwnerUserKey``; the owner-scoped reads pass their caller's ``user_key``
  through to ``@UserKey`` unchanged. The procedures are solely responsible for
  resolving a key to a profile id and for re-asserting ``owner_profile_id`` on
  every predicate, exactly as ``services/knowledge_service.py`` does. A forged
  or unresolvable key is carried through and fails at the database layer, which
  ``PS-ASK-PETE-DIRECT-001_owner_isolation_verify.sql`` proves.
* **The sender is anonymous and stays that way.** ``submit_question`` takes no
  sender identity, no address, and no fingerprint. The only personal data that
  can ever be stored is the text the sender chose to type into the bounded
  contact field, and only after an explicit yes.
* **Consent is a value, not a default.** ``consent`` must be exactly ``True``
  (``True``, not ``1``, not ``"yes"``, not a truthy object). Anything else
  raises before the database is touched, and the procedure enforces the same
  rule again on its own side.
* **Bounds mirror the migration's CHECK constraints in UTF-16 code units**, the
  ``moment_service.utf16_length`` idiom, so a malformed request is refused here
  rather than becoming a constraint violation the caller cannot interpret.
* **No false success.** A submit reports ``stored`` only for an outcome word
  the procedure actually returned; a missing, unexpected, or ``not_found``
  outcome is an error, matching ``journal_service.save_moment`` discipline.
* **Archive is the only removal.** There is no delete method here because
  there is no delete procedure to call.

``DatabaseServiceError`` is never re-raised to a caller as-is: it is converted
to ``AskPeteDirectError(code="unavailable")`` so a route cannot accidentally
leak a driver message into a response.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from services.database_service import DatabaseServiceError, database_service


SCHEMA_VERSION = "ask-pete-direct-question.v1"

# The exact consent wording a stored question was sent under. The SERVER
# stamps this; a client never supplies it, so a stale or tampered page can
# never make a question look as though it was sent under wording its sender
# did not see. Change the wording -> change this string, and every previously
# stored row keeps recording the wording that was actually shown.
CONSENT_VERSION = "ask-pete-direct-consent.v1"

# Mirrors of the migration's CHECK constraints
# (SQL FIles/Migrations/proposed/PS-ASK-PETE-DIRECT-001_recruiter_questions.sql),
# counted in UTF-16 code units exactly as SQL Server counts nvarchar and as a
# browser's maxlength counts.
MAX_QUESTION_UNITS = 2000
MAX_CONTACT_UNITS = 300
MAX_IDEMPOTENCY_UNITS = 200
MAX_CONSENT_VERSION_UNITS = 60
MAX_LIST_ITEMS = 200

QUESTION_STATUSES = frozenset({"new", "read", "archived"})
# What the owner inbox may ask for. Identical to the column's CHECK, listed
# separately so widening one never silently widens the other.
SETTABLE_STATUSES = frozenset({"new", "read", "archived"})

_VERSION_TOKEN = re.compile(r"^[0-9a-fA-F]{16}$")
_CONSENT_VERSION = re.compile(r"^[A-Za-z0-9._-]+$")

SUBMIT_ROW_FIELDS = frozenset({"outcome"})
LIST_ROW_FIELDS = frozenset(
    {
        "recruiter_question_key",
        "question_status",
        "question_text",
        "contact_text",
        "consent_version",
        "created_at_utc",
        "status_changed_at_utc",
        "row_version",
    }
)
COUNT_ROW_FIELDS = frozenset({"total_count", "new_count"})
STATUS_ROW_FIELDS = frozenset({"outcome", "question_status", "row_version"})

_SUBMIT_OUTCOMES = frozenset({"success", "existing"})
_FENCED_OUTCOMES = frozenset({"success", "changed"})


class AskPeteDirectError(RuntimeError):
    """Raised when a recruiter question cannot be handled safely.

    ``code`` is what a route maps to a status and a sender-safe message. It is
    never the database's own words.
    """

    def __init__(self, message, code="unavailable"):
        super().__init__(message)
        self.code = code


def utf16_length(value):
    """Count UTF-16 code units, matching SQL Server nvarchar and maxlength.

    The same idiom as ``services/moment_service.py`` and
    ``services/knowledge_service.py`` - reused rather than imported so this
    module carries no edit-time dependency on a file another lane owns.
    """
    return len(value.encode("utf-16-le")) // 2


def _require_exact_fields(row, expected, label):
    """Set equality, not a superset check: a row missing an expected field OR
    carrying an extra one is rejected outright rather than partly trusted."""
    if not isinstance(row, dict) or set(row) != set(expected):
        raise AskPeteDirectError(f"Unexpected {label} result shape.", code="invalid")


def _opaque_key(value, label):
    try:
        return str(UUID(str(value)))
    except (TypeError, ValueError, AttributeError) as error:
        raise AskPeteDirectError(f"Invalid {label}.", code="invalid") from error


def _version_token(value, label):
    """16-hex-character token from a SQL Server binary(8) row_version."""
    if isinstance(value, memoryview):
        value = value.tobytes()
    if isinstance(value, bytearray):
        value = bytes(value)
    if isinstance(value, bytes):
        value = value.hex()
    if not isinstance(value, str) or not _VERSION_TOKEN.fullmatch(value):
        raise AskPeteDirectError(f"Invalid {label}.", code="invalid")
    return value.lower()


def _decode_version_token(value):
    """Inverse of ``_version_token``. Returns ``None`` for anything not shaped
    like a version token rather than guessing or passing it through."""
    if isinstance(value, (bytes, bytearray, memoryview)):
        raw = bytes(value)
        return raw if len(raw) == 8 else None
    if isinstance(value, str) and _VERSION_TOKEN.fullmatch(value):
        return bytes.fromhex(value)
    return None


def _utc_timestamp(value, label, *, required=True):
    if value is None:
        if required:
            raise AskPeteDirectError(f"Invalid {label}.", code="invalid")
        return None
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as error:
            raise AskPeteDirectError(f"Invalid {label}.", code="invalid") from error
    else:
        raise AskPeteDirectError(f"Invalid {label}.", code="invalid")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _bounded_choice(value, allowed, label):
    if value not in allowed:
        raise AskPeteDirectError(f"Invalid {label}.", code="invalid")
    return value


def _non_negative_int(value, label):
    try:
        parsed = int(value)
    except (TypeError, ValueError) as error:
        raise AskPeteDirectError(f"Invalid {label}.", code="invalid") from error
    if isinstance(value, bool) or parsed < 0:
        raise AskPeteDirectError(f"Invalid {label}.", code="invalid")
    return parsed


def _bounded_text(value, label, max_units, *, required=True):
    """A string read back OUT of the database, bounded by the same limit the
    CHECK constraint enforces on the way in."""
    if value is None or value == "":
        if required:
            raise AskPeteDirectError(f"Invalid {label}.", code="invalid")
        return None
    if not isinstance(value, str) or utf16_length(value) > max_units:
        raise AskPeteDirectError(f"Invalid {label}.", code="invalid")
    return value


def validate_question_input(question, contact, consent):
    """Apply exactly the rules ``submit_question`` enforces, without storing.

    Returns the cleaned ``(question, contact)`` pair. Raises
    ``AskPeteDirectError`` with ``.code`` in
    ``{"required", "too_long", "invalid", "consent_required"}`` so a caller can
    turn one rung of the ladder into one sender-safe message and re-render the
    form with the sender's own text preserved rather than losing it. Mirrors
    ``knowledge_service.validate_knowledge_item_input``.
    """
    if not isinstance(question, str) or not question.strip():
        raise AskPeteDirectError("A question is required.", code="required")
    clean_question = question.strip()
    if utf16_length(clean_question) > MAX_QUESTION_UNITS:
        raise AskPeteDirectError("The question is too long.", code="too_long")

    if contact is None:
        clean_contact = None
    elif isinstance(contact, str):
        clean_contact = contact.strip() or None
        if clean_contact is not None and utf16_length(clean_contact) > MAX_CONTACT_UNITS:
            raise AskPeteDirectError(
                "The contact details are too long.", code="too_long"
            )
    else:
        raise AskPeteDirectError("The contact details are invalid.", code="invalid")

    # Exactly True. 1, "true", "on", and any other truthy value are refused:
    # consent that was never explicitly given must never be inferred from a
    # coincidentally truthy payload.
    if consent is not True:
        raise AskPeteDirectError(
            "Consent is required before a question can be sent.",
            code="consent_required",
        )

    return clean_question, clean_contact


@dataclass(frozen=True)
class RecruiterQuestionListResult:
    """Return shape of ``list_questions_for_owner``.

    ``items`` is the bounded (TOP 200) page. ``total_count`` and ``new_count``
    are the true counts for the same ``include_archived`` scope, independent of
    that cap, so the inbox can say honestly how many there are instead of
    implying 200 is everything.
    """

    items: list
    total_count: int
    new_count: int


class AskPeteDirectService:
    """Recruiter question storage. ``database`` defaults to the shared
    ``database_service`` singleton; every method below calls exactly one
    allowlisted procedure through it and nothing else."""

    def __init__(self, database=None):
        self.database = database or database_service

    # ------------------------------------------------------------------
    # Shared guards
    # ------------------------------------------------------------------

    @staticmethod
    def _require_user_key(user_key, label):
        if not isinstance(user_key, str) or not user_key.strip():
            raise AskPeteDirectError(f"A resolved {label} is required.", code="no_identity")

    @staticmethod
    def _require_question_key(question_key):
        try:
            return str(UUID(str(question_key)))
        except (TypeError, ValueError, AttributeError) as error:
            raise AskPeteDirectError(
                "A valid question key is required.", code="invalid"
            ) from error

    @staticmethod
    def _require_expected_row_version(expected_version_token):
        expected_row_version = _decode_version_token(expected_version_token)
        if expected_row_version is None:
            raise AskPeteDirectError(
                "A valid expected version is required.", code="invalid"
            )
        return expected_row_version

    def _first_row(self, procedure_name, parameters):
        try:
            return self.database.first_row(procedure_name, parameters)
        except DatabaseServiceError as error:
            # Never surfaced raw: a driver message can carry a procedure name,
            # a server name, or a constraint definition.
            raise AskPeteDirectError(
                "Recruiter questions are unavailable.", code="unavailable"
            ) from error

    def _execute(self, procedure_name, parameters):
        try:
            return self.database.execute_procedure(procedure_name, parameters)
        except DatabaseServiceError as error:
            raise AskPeteDirectError(
                "Recruiter questions are unavailable.", code="unavailable"
            ) from error

    # ------------------------------------------------------------------
    # Public (anonymous-capable) write
    # ------------------------------------------------------------------

    def submit_question(
        self, recipient_user_key, idempotency_key, question, contact, consent
    ):
        """Store one privately sent question (usp_SubmitRecruiterQuestion).

        ``recipient_user_key`` is the member the question is addressed to. It
        comes from server-side configuration, never from the request body: a
        caller-chosen recipient would let anyone write into any member's inbox.

        ``idempotency_key`` is required. A repeated key for the same recipient
        resolves to the SAME question and returns ``already_sent`` - which is
        what makes a double-tapped Send safe, and is the reason the route
        refuses a request that arrives without one.

        Returns ``{"stored": True, "state": "sent" | "already_sent",
        "consent_version": CONSENT_VERSION}``. Never returns the stored
        question's key: the caller is anonymous and must not learn the
        identifier of anything in a member's private inbox, not even their own
        submission.
        """
        self._require_user_key(recipient_user_key, "recipient")
        if not isinstance(idempotency_key, str) or not idempotency_key.strip():
            raise AskPeteDirectError("An idempotency key is required.", code="required")
        clean_idempotency_key = idempotency_key.strip()
        if utf16_length(clean_idempotency_key) > MAX_IDEMPOTENCY_UNITS:
            raise AskPeteDirectError(
                "The idempotency key is too long.", code="too_long"
            )

        clean_question, clean_contact = validate_question_input(
            question, contact, consent
        )

        # Defence in depth against a future edit to the constant itself: the
        # procedure concatenates this value into audit metadata JSON.
        if (
            not _CONSENT_VERSION.fullmatch(CONSENT_VERSION)
            or utf16_length(CONSENT_VERSION) > MAX_CONSENT_VERSION_UNITS
        ):
            raise AskPeteDirectError(
                "The consent version is not usable.", code="invalid"
            )

        row = self._first_row(
            "usp_SubmitRecruiterQuestion",
            [
                ("@OwnerUserKey", recipient_user_key),
                ("@IdempotencyKey", clean_idempotency_key),
                ("@QuestionText", clean_question),
                ("@ContactText", clean_contact),
                ("@ConsentVersion", CONSENT_VERSION),
                ("@ConsentGiven", 1),
            ],
        )

        _require_exact_fields(row, SUBMIT_ROW_FIELDS, "recruiter question submit")
        outcome = row["outcome"]
        if outcome not in _SUBMIT_OUTCOMES:
            # Includes the procedure's own ``not_found`` when the configured
            # recipient does not resolve to an active profile. Nothing was
            # stored, so nothing may be reported as sent.
            raise AskPeteDirectError(
                "The question could not be sent.", code="not_found"
            )

        return {
            "stored": True,
            "state": "sent" if outcome == "success" else "already_sent",
            "consent_version": CONSENT_VERSION,
        }

    # ------------------------------------------------------------------
    # Owner-scoped reads and status changes
    # ------------------------------------------------------------------

    def list_questions_for_owner(self, user_key, *, include_archived=False):
        """Bounded owner-scoped read (usp_ListRecruiterQuestionsForOwner)."""
        self._require_user_key(user_key, "owner identity")

        result_sets = self._execute(
            "usp_ListRecruiterQuestionsForOwner",
            [
                ("@UserKey", user_key),
                ("@IncludeArchived", 1 if include_archived else 0),
            ],
        )
        rows = result_sets[0] if result_sets else []
        count_rows = result_sets[1] if len(result_sets) > 1 else []

        if len(rows) > MAX_LIST_ITEMS:
            # Unreachable against the real procedure (it caps at TOP (200));
            # this catches a future query-shape regression or a malformed test
            # double rather than silently truncating.
            raise AskPeteDirectError(
                "Recruiter question list limit exceeded.", code="invalid"
            )

        total_count = 0
        new_count = 0
        if count_rows:
            if len(count_rows) != 1:
                raise AskPeteDirectError(
                    "Unexpected recruiter question count result.", code="invalid"
                )
            _require_exact_fields(
                count_rows[0], COUNT_ROW_FIELDS, "recruiter question count"
            )
            total_count = _non_negative_int(
                count_rows[0]["total_count"], "total question count"
            )
            new_count = _non_negative_int(
                count_rows[0]["new_count"], "unread question count"
            )

        return RecruiterQuestionListResult(
            items=[self._serialize_list_row(row) for row in rows],
            total_count=total_count,
            new_count=new_count,
        )

    @staticmethod
    def _serialize_list_row(row):
        _require_exact_fields(row, LIST_ROW_FIELDS, "recruiter question list row")
        return {
            "question_key": _opaque_key(
                row["recruiter_question_key"], "recruiter question key"
            ),
            "status": _bounded_choice(
                row["question_status"], QUESTION_STATUSES, "question status"
            ),
            "question": _bounded_text(
                row["question_text"], "question", MAX_QUESTION_UNITS
            ),
            "contact": _bounded_text(
                row["contact_text"], "contact details", MAX_CONTACT_UNITS,
                required=False,
            ),
            "consent_version": _bounded_text(
                row["consent_version"], "consent version", MAX_CONSENT_VERSION_UNITS
            ),
            "created_at": _utc_timestamp(row["created_at_utc"], "created time"),
            "status_changed_at": _utc_timestamp(
                row["status_changed_at_utc"], "status change time", required=False
            ),
            "version_token": _version_token(row["row_version"], "row version"),
        }

    def set_question_status_for_owner(
        self, user_key, question_key, status, expected_version_token
    ):
        """Version-fenced status change (usp_SetRecruiterQuestionStatusForOwner).

        The three reachable statuses are ``new``, ``read``, and ``archived``.
        There is no fourth, and there is no delete: archiving is the only
        removal control v1 gives the member, and it is reversible.

        A mismatched ``expected_version_token`` - including one presented for
        another member's question, or by an unresolvable owner - returns
        outcome ``changed`` and is raised as
        ``AskPeteDirectError(code="changed")``, never a false success.
        """
        self._require_user_key(user_key, "owner identity")
        clean_question_key = self._require_question_key(question_key)
        expected_row_version = self._require_expected_row_version(
            expected_version_token
        )
        if status not in SETTABLE_STATUSES:
            raise AskPeteDirectError("That question status is invalid.", code="invalid")

        row = self._first_row(
            "usp_SetRecruiterQuestionStatusForOwner",
            [
                ("@UserKey", user_key),
                ("@RecruiterQuestionKey", clean_question_key),
                ("@Status", status),
                ("@ExpectedRowVersion", expected_row_version),
            ],
        )

        _require_exact_fields(row, STATUS_ROW_FIELDS, "recruiter question status")
        if row["outcome"] not in _FENCED_OUTCOMES:
            raise AskPeteDirectError("Unexpected status outcome.", code="invalid")
        if row["outcome"] == "changed":
            raise AskPeteDirectError(
                "That question changed before this update.", code="changed"
            )

        return {
            "status": _bounded_choice(
                row["question_status"], QUESTION_STATUSES, "question status"
            ),
            "version_token": _version_token(row["row_version"], "row version"),
            "changed": True,
        }


ask_pete_direct_service = AskPeteDirectService()
