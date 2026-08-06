"""Private member knowledge base for Workshop / My Information.

PS-WORKSHOP-001, Slice W1. The checkpoint gate (owner decision, 2026-08-01)
built the My Information main page against a fixed CHECKPOINT FIXTURE —
``_checkpoint_items``/``_checkpoint_suggestion`` and
``get_my_information_checkpoint`` below — before any migration, procedure,
or store existed, so the page could be compared against the approved
mockups first. MINOR 10 correction: that fixture is no longer the
production path. It is kept here deliberately as a clearly-marked,
compound-gated (``PEERSLATE_WORKSHOP_DEV_FIXTURE`` AND
``PEERSLATE_ALLOW_DEV_IDENTITY``) local-preview-only dev/test seam —
workshop_routes.py's ``_workshop_dev_fixture_enabled()`` — used only when a
local preview has no database; every other request path calls the real
methods below.

The data layer for Slice W1 exists (SQL FIles/Migrations/proposed/
PS-WORKSHOP-001_knowledge_items.sql): dbo.knowledge_items,
dbo.knowledge_item_versions, dbo.knowledge_item_save_requests, and the
seven owner-scoped usp_*KnowledgeItemForOwner procedures. The
``*_knowledge_item_for_owner`` methods below wire the class to that real
store via ``self.database`` (the same injected ``database_service``
singleton placeholder the class already declared), following the class
shape docs/initiatives/PS-SLATE-STUDIO-IA-001/17_WORKSHOP_PRODUCT_AND_TECHNICAL_ARCHITECTURE.md
section 7 anticipated. workshop_routes.py now wires every one of these
methods into the real My Information page and the direct-entry
add/edit/archive/restore/delete routes.

Per docs/initiatives/PS-SLATE-STUDIO-IA-001/20_ROUND2_VISUAL_ACCEPTANCE_AND_RECONCILIATION.md
section 6a (owner decision, 2026-08-01), AI use of confirmed information is
always on with no member-facing permission control. Neither the checkpoint
view-model nor the real read/write methods carry a per-item AI-use
permission field, state, or "Use as context" toggle — none of that concept
exists in the product any more, and the migration itself has no such
column. Where the approved mockup's copy referenced the retired permission
concept (the right-rail bullet about "changing AI-use permission" and the
suggestion card's "information you previously allowed it to use"), the
checkpoint fixture's wording is adjusted to stay truthful about what the
page can actually do, per the allowed "truthful state wiring" adaptation
(docs/AI_WORKFLOW.md, "Visual integrity for user-facing work").

No AI call happens anywhere in this module.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from types import MappingProxyType
from uuid import NAMESPACE_URL, UUID, uuid5

from services.database_service import database_service


SCHEMA_VERSION = "workshop-knowledge.v1"

# Real usp_*KnowledgeItemForOwner wiring (PS-WORKSHOP-001, Slice W1 data
# layer). These bounds and enumerations mirror the migration's CHECK
# constraints exactly (SQL FIles/Migrations/proposed/
# PS-WORKSHOP-001_knowledge_items.sql) so a malformed request is rejected
# here, before any database round trip, with the same limits the
# procedures themselves enforce.
MAX_TITLE_UNITS = 160
MAX_WORDING_UNITS = 8000
MAX_LIST_ITEMS = 200
MAX_HISTORY_VERSIONS = 50

ITEM_STATUSES = frozenset({"suggested", "unfinished", "confirmed", "archived"})
CLASSIFICATIONS = frozenset({"work", "personal", "both", "unclassified"})
BODY_FORMATS = frozenset({"plain", "rich"})
AUTHORED_VIA_VALUES = frozenset({"typed", "spoken", "ai_assisted_approved"})

_VERSION_TOKEN = re.compile(r"^[0-9a-fA-F]{16}$")

LIST_ROW_FIELDS = frozenset(
    {
        "knowledge_item_key",
        "item_status",
        "classification",
        "current_version_number",
        "confirmed_version_number",
        "confirmed_at_utc",
        "archived_at_utc",
        "created_at_utc",
        "updated_at_utc",
        "row_version",
        "title",
        "body_format",
        "authored_via",
    }
)
GET_ROW_FIELDS = frozenset(
    {
        "knowledge_item_key",
        "item_status",
        "classification",
        "current_version_number",
        "confirmed_version_number",
        "confirmed_at_utc",
        "archived_at_utc",
        "created_at_utc",
        "updated_at_utc",
        "row_version",
        "version_number",
        "title",
        "approved_wording",
        "original_member_wording",
        "body_format",
        "authored_via",
        "saved_at_utc",
    }
)
HISTORY_ROW_FIELDS = frozenset(
    {"version_number", "title", "body_format", "authored_via", "saved_at_utc"}
)
COUNT_ROW_FIELDS = frozenset({"total_count"})
SAVE_ROW_FIELDS = frozenset(
    {"outcome", "knowledge_item_key", "item_status", "row_version"}
)
UPDATE_ROW_FIELDS = frozenset({"outcome", "version_number", "row_version"})
ARCHIVE_ROW_FIELDS = frozenset({"outcome", "row_version"})
RESTORE_ROW_FIELDS = frozenset({"outcome", "row_version"})
DELETE_ROW_FIELDS = frozenset({"outcome", "deleted_version_count"})
BACKLOG_CONFIRM_ROW_FIELDS = frozenset({"confirmed_count", "remaining_count"})

_SAVE_OUTCOMES = frozenset({"success", "existing"})
_FENCED_OUTCOMES = frozenset({"success", "changed"})

AREA_FILTERS = (
    MappingProxyType({"key": "all", "label": "All"}),
    MappingProxyType({"key": "work", "label": "Work"}),
    MappingProxyType({"key": "personal", "label": "Personal"}),
    MappingProxyType({"key": "both", "label": "Both"}),
)
STATUS_FILTERS = (
    MappingProxyType({"key": "all", "label": "All statuses"}),
    MappingProxyType({"key": "confirmed", "label": "Confirmed"}),
    MappingProxyType({"key": "suggested", "label": "Suggested"}),
    MappingProxyType({"key": "unfinished", "label": "Unfinished"}),
    MappingProxyType({"key": "archived", "label": "Archived"}),
)

# MINOR 10 correction: direct entry shipped in this slice (doc 18 W1) and
# is honestly "available" here too, matching workshop_routes.py's real-path
# availability dict exactly. "Work on Something" and destination/use
# projections remain later slices (doc 18 W2/W4) — declared honestly as
# "coming_later" rather than omitted, per the availability-registry idiom
# in services/owner_home_service.py. This registry only ever backs the
# dev-fixture checkpoint seam below; the real path builds its own
# equivalent dict directly in workshop_routes.py.
AVAILABILITY_REGISTRY = MappingProxyType(
    {
        "direct_entry": MappingProxyType({"state": "available"}),
        "work_on_something": MappingProxyType({"state": "coming_later"}),
        "destination_use": MappingProxyType({"state": "coming_later"}),
    }
)


class KnowledgeServiceError(RuntimeError):
    """Raised when a Workshop knowledge read cannot be completed safely."""

    def __init__(self, message, code="unavailable"):
        super().__init__(message)
        self.code = code


def utf16_length(value):
    """Match SQL Server nvarchar and browser maxlength code-unit counting.

    Same idiom as services/moment_service.py's ``utf16_length`` — reused
    here (not imported) so this module has no edit-time dependency on a
    file reserved by another lane's ownership boundary.
    """
    return len(value.encode("utf-16-le")) // 2


def _require_exact_fields(row, expected, label):
    """Owner_home_service's ``_require_exact_fields`` set-equality
    discipline: a row missing an expected field OR carrying an extra
    (superset) field is rejected outright rather than silently passed
    through or truncated."""
    if not isinstance(row, dict) or set(row) != set(expected):
        raise KnowledgeServiceError(f"Unexpected {label} result shape.", code="invalid")


def _opaque_key(value, label):
    try:
        return str(UUID(str(value)))
    except (TypeError, ValueError, AttributeError) as error:
        raise KnowledgeServiceError(f"Invalid {label}.", code="invalid") from error


def _version_token(value, label):
    """16-hex-character token from a SQL Server binary(8) row_version."""
    if isinstance(value, memoryview):
        value = value.tobytes()
    if isinstance(value, bytearray):
        value = bytes(value)
    if isinstance(value, bytes):
        value = value.hex()
    if not isinstance(value, str) or not _VERSION_TOKEN.fullmatch(value):
        raise KnowledgeServiceError(f"Invalid {label}.", code="invalid")
    return value.lower()


def _decode_version_token(value):
    """Inverse of ``_version_token``: a 16-hex-character string (or raw
    bytes) becomes the binary(8) value the procedures expect for
    @ExpectedRowVersion. Returns ``None`` for anything not shaped like a
    version token, rather than guessing or passing an unrecognized value
    through to the database."""
    if isinstance(value, (bytes, bytearray, memoryview)):
        raw = bytes(value)
        return raw if len(raw) == 8 else None
    if isinstance(value, str) and _VERSION_TOKEN.fullmatch(value):
        return bytes.fromhex(value)
    return None


def _utc_timestamp(value, label, *, required=True):
    if value is None:
        if required:
            raise KnowledgeServiceError(f"Invalid {label}.", code="invalid")
        return None
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as error:
            raise KnowledgeServiceError(f"Invalid {label}.", code="invalid") from error
    else:
        raise KnowledgeServiceError(f"Invalid {label}.", code="invalid")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _bounded_choice(value, allowed, label):
    if value not in allowed:
        raise KnowledgeServiceError(f"Invalid {label}.", code="invalid")
    return value


def _positive_int(value, label):
    try:
        parsed = int(value)
    except (TypeError, ValueError) as error:
        raise KnowledgeServiceError(f"Invalid {label}.", code="invalid") from error
    if isinstance(value, bool) or parsed < 1:
        raise KnowledgeServiceError(f"Invalid {label}.", code="invalid")
    return parsed


def _non_negative_int(value, label):
    """Like ``_positive_int`` but zero is a legitimate value — an owner
    with no items at all has a true total_count of exactly 0."""
    try:
        parsed = int(value)
    except (TypeError, ValueError) as error:
        raise KnowledgeServiceError(f"Invalid {label}.", code="invalid") from error
    if isinstance(value, bool) or parsed < 0:
        raise KnowledgeServiceError(f"Invalid {label}.", code="invalid")
    return parsed


def _optional_positive_int(value, label):
    if value is None:
        return None
    return _positive_int(value, label)


def _bounded_text(value, label, max_units):
    """A required, non-empty, UTF-16-bounded string read back from the
    database. Applies the moment_service ``len(v.encode("utf-16-le"))//2``
    idiom on the way OUT of the database, mirroring the same bound the
    migration's CHECK constraints already enforce on the way in."""
    if not isinstance(value, str) or not value:
        raise KnowledgeServiceError(f"Invalid {label}.", code="invalid")
    if utf16_length(value) > max_units:
        raise KnowledgeServiceError(f"Invalid {label}.", code="invalid")
    return value


def _clean_item_key(value):
    try:
        return str(UUID(str(value)))
    except (TypeError, ValueError, AttributeError):
        return None


def _validate_write_fields(
    title,
    approved_wording,
    original_wording,
    body_format,
    classification,
    authored_via,
    *,
    require_original,
):
    """Shared inbound validation for Save and Update: required text
    present, UTF-16 bounds respected, and every enumerated field one of
    the migration's exact CHECK-constrained values. Raises before any
    database round trip, so a malformed request never reaches a
    procedure."""
    if not isinstance(title, str) or not title.strip():
        raise KnowledgeServiceError("A title is required.", code="required")
    if not isinstance(approved_wording, str) or not approved_wording.strip():
        raise KnowledgeServiceError("Approved wording is required.", code="required")
    if require_original and (
        not isinstance(original_wording, str) or not original_wording.strip()
    ):
        raise KnowledgeServiceError("Original wording is required.", code="required")

    if classification not in CLASSIFICATIONS:
        raise KnowledgeServiceError("Classification is invalid.", code="invalid")
    if body_format not in BODY_FORMATS:
        raise KnowledgeServiceError("Body format is invalid.", code="invalid")
    if authored_via is not None and authored_via not in AUTHORED_VIA_VALUES:
        raise KnowledgeServiceError("Authored-via provenance is invalid.", code="invalid")

    if utf16_length(title) > MAX_TITLE_UNITS:
        raise KnowledgeServiceError("Title exceeds its limit.", code="too_long")
    if utf16_length(approved_wording) > MAX_WORDING_UNITS:
        raise KnowledgeServiceError("Approved wording exceeds its limit.", code="too_long")
    if require_original and utf16_length(original_wording) > MAX_WORDING_UNITS:
        raise KnowledgeServiceError("Original wording exceeds its limit.", code="too_long")


def validate_knowledge_item_input(title, wording, classification):
    """Pre-write validation for the Add/Edit review step.

    Applies exactly the rules ``save_knowledge_item_for_owner`` /
    ``update_knowledge_item_for_owner`` enforce, so the review screen can
    reject a malformed submission before any database round trip — mirroring
    ``services/moment_service.py``'s ``validate_moment_proposal``. Returns the
    stripped ``(title, wording, classification)`` tuple on success. Raises
    ``KnowledgeServiceError`` with ``.code`` in
    ``{"required", "invalid", "too_long"}`` on failure; the route maps that
    code to a member-safe message and re-renders the form with the member's
    text preserved rather than losing it.
    """
    clean_title = title.strip() if isinstance(title, str) else ""
    clean_wording = wording.strip() if isinstance(wording, str) else ""
    _validate_write_fields(
        clean_title,
        clean_wording,
        clean_wording,
        "plain",
        classification,
        "typed",
        require_original=False,
    )
    return clean_title, clean_wording, classification


def _serialize_list_row(row):
    _require_exact_fields(row, LIST_ROW_FIELDS, "knowledge item list row")
    return {
        "item_key": _opaque_key(row["knowledge_item_key"], "knowledge item key"),
        "status": _bounded_choice(row["item_status"], ITEM_STATUSES, "item status"),
        "classification": _bounded_choice(
            row["classification"], CLASSIFICATIONS, "classification"
        ),
        "current_version": _positive_int(
            row["current_version_number"], "current version"
        ),
        "confirmed_version": _optional_positive_int(
            row["confirmed_version_number"], "confirmed version"
        ),
        "confirmed_at": _utc_timestamp(
            row["confirmed_at_utc"], "confirmed time", required=False
        ),
        "archived_at": _utc_timestamp(
            row["archived_at_utc"], "archived time", required=False
        ),
        "created_at": _utc_timestamp(row["created_at_utc"], "created time"),
        "updated_at": _utc_timestamp(row["updated_at_utc"], "updated time"),
        "version_token": _version_token(row["row_version"], "row version"),
        "title": _bounded_text(row["title"], "title", MAX_TITLE_UNITS),
        "body_format": _bounded_choice(row["body_format"], BODY_FORMATS, "body format"),
        "authored_via": _bounded_choice(
            row["authored_via"], AUTHORED_VIA_VALUES, "authored via"
        ),
    }


def _serialize_history_row(row):
    _require_exact_fields(row, HISTORY_ROW_FIELDS, "knowledge item history row")
    return {
        "version": _positive_int(row["version_number"], "history version"),
        "title": _bounded_text(row["title"], "history title", MAX_TITLE_UNITS),
        "body_format": _bounded_choice(
            row["body_format"], BODY_FORMATS, "history body format"
        ),
        "authored_via": _bounded_choice(
            row["authored_via"], AUTHORED_VIA_VALUES, "history authored via"
        ),
        "saved_at": _utc_timestamp(row["saved_at_utc"], "history saved time"),
    }


def _serialize_get_row(row, history_rows):
    _require_exact_fields(row, GET_ROW_FIELDS, "knowledge item")
    if len(history_rows) > MAX_HISTORY_VERSIONS:
        raise KnowledgeServiceError(
            "Knowledge item history limit exceeded.", code="invalid"
        )
    return {
        "item_key": _opaque_key(row["knowledge_item_key"], "knowledge item key"),
        "status": _bounded_choice(row["item_status"], ITEM_STATUSES, "item status"),
        "classification": _bounded_choice(
            row["classification"], CLASSIFICATIONS, "classification"
        ),
        "current_version": _positive_int(
            row["current_version_number"], "current version"
        ),
        "confirmed_version": _optional_positive_int(
            row["confirmed_version_number"], "confirmed version"
        ),
        "confirmed_at": _utc_timestamp(
            row["confirmed_at_utc"], "confirmed time", required=False
        ),
        "archived_at": _utc_timestamp(
            row["archived_at_utc"], "archived time", required=False
        ),
        "created_at": _utc_timestamp(row["created_at_utc"], "created time"),
        "updated_at": _utc_timestamp(row["updated_at_utc"], "updated time"),
        "version_token": _version_token(row["row_version"], "row version"),
        "version": _positive_int(row["version_number"], "version"),
        "title": _bounded_text(row["title"], "title", MAX_TITLE_UNITS),
        "approved_wording": _bounded_text(
            row["approved_wording"], "approved wording", MAX_WORDING_UNITS
        ),
        "original_member_wording": _bounded_text(
            row["original_member_wording"],
            "original wording",
            MAX_WORDING_UNITS,
        ),
        "body_format": _bounded_choice(row["body_format"], BODY_FORMATS, "body format"),
        "authored_via": _bounded_choice(
            row["authored_via"], AUTHORED_VIA_VALUES, "authored via"
        ),
        "saved_at": _utc_timestamp(row["saved_at_utc"], "saved time"),
        "history": [_serialize_history_row(entry) for entry in history_rows],
    }


def _fixture_key(slug):
    """A stable, non-guessable-looking id for one fixture row.

    Deterministic (not random) so repeated renders and tests are stable,
    but shaped exactly like the real ``knowledge_item_key`` a future
    ``usp_ListKnowledgeItemsForOwner`` row will carry.
    """
    return str(uuid5(NAMESPACE_URL, f"peerslate:workshop-checkpoint-fixture:{slug}"))


@dataclass(frozen=True)
class KnowledgeItemFixture:
    item_key: str
    title: str
    status: str  # confirmed | suggested | unfinished | archived
    status_label: str
    classification: str  # work | personal | both
    classification_label: str
    downstream_use_label: str
    body: str
    source_label: str
    selected: bool = False


@dataclass(frozen=True)
class KnowledgeItemListResult:
    """Return shape of ``list_knowledge_items_for_owner``.

    ``items`` is the bounded (TOP 200) list of serialized rows exactly as
    before; ``total_count`` is the owner's TRUE count matching the same
    scope (``@IncludeArchived``), independent of the 200 cap, so a caller
    can render an honest "Showing 200 of <true total>" instead of silently
    implying 200 is everything (BLOCKER 2 correction).
    """

    items: list
    total_count: int


@dataclass(frozen=True)
class SuggestionFixture:
    intro: str
    evidence_lead: str
    evidence_quote: str
    review_label: str
    dismiss_label: str
    do_not_suggest_label: str


@dataclass(frozen=True)
class MyInformationCheckpoint:
    """The full, template-ready view-model for the checkpoint render."""

    schema_version: str
    owner_display_name: str
    items: tuple
    area_filters: tuple
    status_filters: tuple
    selected_area: str
    selected_status: str
    total_item_count: int
    suggestion: SuggestionFixture
    availability: dict


def _checkpoint_items():
    return (
        KnowledgeItemFixture(
            item_key=_fixture_key("systems-engineering"),
            title="Systems Engineering",
            status="confirmed",
            status_label="Confirmed",
            classification="work",
            classification_label="Work",
            downstream_use_label="Not used elsewhere",
            body=(
                "You brought product, hardware, and software teams together "
                "to define a system architecture, resolve major trade-offs, "
                "align requirements, and secure leadership commitment to "
                "move from concept to prototype."
            ),
            source_label="Your words from this Workshop session",
            selected=True,
        ),
        KnowledgeItemFixture(
            item_key=_fixture_key("cross-functional-recovery"),
            title="Led a cross-functional sustainment recovery effort",
            status="confirmed",
            status_label="Confirmed",
            classification="work",
            classification_label="Work",
            downstream_use_label="Not used elsewhere",
            body=(
                "You led a cross-functional recovery effort, coordinating "
                "engineering, sustainment, and program stakeholders to "
                "restore a stalled effort to a credible plan."
            ),
            source_label="Your words from a Workshop session",
        ),
        KnowledgeItemFixture(
            item_key=_fixture_key("mentoring-career-changers"),
            title="Mentoring people changing careers",
            status="confirmed",
            status_label="Confirmed",
            classification="work",
            classification_label="Work",
            downstream_use_label="Not used elsewhere",
            body=(
                "You mentor people moving into a new field, helping them "
                "translate past experience and prepare for interviews with "
                "confidence."
            ),
            source_label="Your words from a Workshop session",
        ),
        KnowledgeItemFixture(
            item_key=_fixture_key("long-distance-running"),
            title="Long-distance running",
            status="confirmed",
            status_label="Confirmed",
            classification="personal",
            classification_label="Personal",
            downstream_use_label="Not used elsewhere",
            body=(
                "You train and race long distances, building the sustained "
                "discipline and pacing that come with distance running."
            ),
            source_label="Your words from a Workshop session",
        ),
    )


def _checkpoint_suggestion():
    return SuggestionFixture(
        # Adapted from the approved mockup's "information you previously
        # allowed it to use": that phrase names the per-item AI-use
        # permission doc 20 section 6a removed entirely. Grounding now
        # follows from confirmed information generally, so the sentence is
        # reworded to stay accurate rather than reference a control that no
        # longer exists.
        intro=(
            "PeerSlate noticed a possible connection in information you've "
            "already confirmed. Review the wording before anything is "
            "confirmed."
        ),
        evidence_lead="Cross-functional leadership",
        evidence_quote="Led a cross-functional sustainment recovery effort.",
        review_label="Review, edit and confirm",
        dismiss_label="Dismiss",
        do_not_suggest_label="Do not suggest this again",
    )


class KnowledgeService:
    """Owner-scoped Workshop knowledge reads and writes.

    ``database`` defaults to the shared ``database_service`` singleton.
    ``get_my_information_checkpoint`` never calls it (a dev/test fixture
    seam); every ``*_knowledge_item_for_owner`` method below calls exactly
    one ``usp_*KnowledgeItemForOwner`` procedure through it.
    """

    def __init__(self, database=None):
        self.database = database or database_service

    def get_my_information_checkpoint(self, owner_identity, *, empty=False):
        """Return the checkpoint fixture view-model for one signed-in member.

        Raises ``KnowledgeServiceError`` if no resolved owner identity is
        given, so the route's fail-closed contract holds even though this
        method does not yet touch the database.

        ``empty`` backs the dev-only ``?_dev_state=empty`` seam (gated by
        ``PEERSLATE_WORKSHOP_DEV_FIXTURE`` in workshop_routes.py): it returns
        the same shape a real member with zero saved items would produce, so
        the first-run empty state can be captured faithfully without a
        database. It never affects the production read path.
        """
        user_key = getattr(owner_identity, "user_key", None)
        if not isinstance(user_key, str) or not user_key.strip():
            raise KnowledgeServiceError(
                "A resolved owner identity is required.", code="no_identity"
            )

        display_name = getattr(owner_identity, "display_name", None)
        owner_display_name = (
            display_name.strip() if isinstance(display_name, str) and display_name.strip() else "PeerSlate member"
        )

        items = () if empty else _checkpoint_items()
        return MyInformationCheckpoint(
            schema_version=SCHEMA_VERSION,
            owner_display_name=owner_display_name,
            items=items,
            area_filters=AREA_FILTERS,
            status_filters=STATUS_FILTERS,
            selected_area="all",
            selected_status="confirmed",
            total_item_count=len(items),
            suggestion=None if empty else _checkpoint_suggestion(),
            availability={name: dict(value) for name, value in AVAILABILITY_REGISTRY.items()},
        )

    # ------------------------------------------------------------------
    # Real usp_*KnowledgeItemForOwner wiring. Each method resolves nothing
    # itself: it passes the exact ``user_key`` string it was given straight
    # through to the named procedure's @UserKey parameter (never a cached,
    # global, or otherwise substituted value), and the procedure is solely
    # responsible for resolving @UserKey -> @ProfileId and re-asserting
    # owner_profile_id on every predicate. A forged or unresolvable
    # ``user_key`` therefore never bypasses the passed key here; it is
    # carried through unchanged and fails at the database layer exactly as
    # PS-WORKSHOP-001_owner_isolation_verify.sql proves.
    # ------------------------------------------------------------------

    @staticmethod
    def _require_user_key(user_key):
        if not isinstance(user_key, str) or not user_key.strip():
            raise KnowledgeServiceError(
                "A resolved owner identity is required.", code="no_identity"
            )

    @staticmethod
    def _require_item_key(item_key):
        clean_item_key = _clean_item_key(item_key)
        if clean_item_key is None:
            raise KnowledgeServiceError(
                "A valid knowledge item key is required.", code="invalid"
            )
        return clean_item_key

    @staticmethod
    def _require_expected_row_version(expected_version_token):
        expected_row_version = _decode_version_token(expected_version_token)
        if expected_row_version is None:
            raise KnowledgeServiceError(
                "A valid expected version is required.", code="invalid"
            )
        return expected_row_version

    def list_knowledge_items_for_owner(self, user_key, *, include_archived=False):
        """Owner-scoped list read (usp_ListKnowledgeItemsForOwner).

        Returns a ``KnowledgeItemListResult``: ``items`` is bounded to
        ``MAX_LIST_ITEMS`` (200) — the same bound the procedure itself
        enforces with ``TOP (200)``; a database result exceeding it is
        treated as a contract violation rather than silently truncated.
        This bound can never actually fire against a real database response
        (the query itself caps at 200 rows), the same defense-in-depth
        idiom as ``_serialize_get_row``'s ``MAX_HISTORY_VERSIONS`` check
        below — both guard against a future query-shape regression or a
        malformed test double, not a reachable production path.

        ``total_count`` is the owner's TRUE count matching the same
        ``@IncludeArchived`` scope, from the procedure's second result set,
        independent of the 200 cap (BLOCKER 2 correction) — 0 when no owner
        resolves, matching the empty-items case exactly.
        """
        self._require_user_key(user_key)

        result_sets = self.database.execute_procedure(
            "usp_ListKnowledgeItemsForOwner",
            [
                ("@UserKey", user_key),
                ("@IncludeArchived", 1 if include_archived else 0),
            ],
        )
        rows = result_sets[0] if result_sets else []
        count_rows = result_sets[1] if len(result_sets) > 1 else []

        if len(rows) > MAX_LIST_ITEMS:
            raise KnowledgeServiceError(
                "Owner knowledge item list limit exceeded.", code="invalid"
            )

        total_count = 0
        if count_rows:
            if len(count_rows) != 1:
                raise KnowledgeServiceError(
                    "Unexpected knowledge item count result.", code="invalid"
                )
            _require_exact_fields(
                count_rows[0], COUNT_ROW_FIELDS, "knowledge item count row"
            )
            total_count = _non_negative_int(
                count_rows[0]["total_count"], "total item count"
            )

        return KnowledgeItemListResult(
            items=[_serialize_list_row(row) for row in rows],
            total_count=total_count,
        )

    def get_knowledge_item_for_owner(self, user_key, item_key):
        """Single-item read plus bounded version history
        (usp_GetKnowledgeItemForOwner)."""
        self._require_user_key(user_key)
        clean_item_key = self._require_item_key(item_key)

        result_sets = self.database.execute_procedure(
            "usp_GetKnowledgeItemForOwner",
            [("@UserKey", user_key), ("@KnowledgeItemKey", clean_item_key)],
        )
        if len(result_sets) != 2:
            raise KnowledgeServiceError(
                "Unexpected knowledge item result.", code="invalid"
            )
        item_rows, history_rows = result_sets
        if not item_rows:
            raise KnowledgeServiceError("Knowledge item not found.", code="not_found")
        if len(item_rows) != 1:
            raise KnowledgeServiceError(
                "Unexpected knowledge item result.", code="invalid"
            )

        return _serialize_get_row(item_rows[0], history_rows or [])

    def save_knowledge_item_for_owner(self, user_key, idempotency_key, fields):
        """Idempotent create (usp_SaveKnowledgeItemForOwner).

        A repeated ``idempotency_key`` for the same owner returns the SAME
        item (outcome ``existing``) rather than a second one. Never reports
        ``saved: True`` without an exact, non-falsy item key: a missing or
        unrecognized outcome (including the database's own ``not_found``
        when ``user_key`` does not resolve) is always a false-save guard,
        matching services/journal_service.py's ``save_moment`` discipline.
        """
        self._require_user_key(user_key)
        if not isinstance(idempotency_key, str) or not idempotency_key.strip():
            raise KnowledgeServiceError(
                "An idempotency key is required.", code="required"
            )
        # MINOR 11 correction: UTF-16 code units, matching the migration's
        # DATALENGTH(@IdempotencyKey)/2 guard and the same idiom every other
        # bounded field in this module already uses — not Python's len(),
        # which undercounts an astral character (e.g. an emoji) as one unit
        # instead of the two UTF-16 code units SQL Server actually stores.
        if utf16_length(idempotency_key) > 200:
            raise KnowledgeServiceError(
                "Idempotency key exceeds its limit.", code="too_long"
            )
        if not isinstance(fields, dict):
            raise KnowledgeServiceError(
                "Knowledge item fields are required.", code="required"
            )

        title = fields.get("title")
        approved_wording = fields.get("approved_wording")
        original_wording = fields.get("original_wording")
        body_format = fields.get("body_format")
        classification = fields.get("classification")
        authored_via = fields.get("authored_via")
        confirm = bool(fields.get("confirm", False))

        _validate_write_fields(
            title,
            approved_wording,
            original_wording,
            body_format,
            classification,
            authored_via,
            require_original=True,
        )

        row = self.database.first_row(
            "usp_SaveKnowledgeItemForOwner",
            [
                ("@UserKey", user_key),
                ("@IdempotencyKey", idempotency_key),
                ("@Title", title),
                ("@ApprovedWording", approved_wording),
                ("@OriginalWording", original_wording),
                ("@BodyFormat", body_format),
                ("@Classification", classification),
                ("@AuthoredVia", authored_via),
                ("@Confirm", 1 if confirm else 0),
            ],
        )

        _require_exact_fields(row, SAVE_ROW_FIELDS, "save result")
        if row["outcome"] not in _SAVE_OUTCOMES or not row["knowledge_item_key"]:
            raise KnowledgeServiceError(
                "The knowledge item could not be saved.", code="not_found"
            )

        return {
            "item_key": _opaque_key(row["knowledge_item_key"], "knowledge item key"),
            "status": _bounded_choice(row["item_status"], ITEM_STATUSES, "item status"),
            "version_token": _version_token(row["row_version"], "row version"),
            "saved": True,
        }

    def update_knowledge_item_for_owner(
        self, user_key, item_key, expected_version_token, fields
    ):
        """Version-fenced edit (usp_UpdateKnowledgeItemForOwner).

        A mismatched ``expected_version_token`` (including one from a
        forged or unresolvable owner) returns outcome ``changed`` and is
        raised as ``KnowledgeServiceError(code="changed")`` — never a
        false success.
        """
        self._require_user_key(user_key)
        clean_item_key = self._require_item_key(item_key)
        expected_row_version = self._require_expected_row_version(expected_version_token)
        if not isinstance(fields, dict):
            raise KnowledgeServiceError(
                "Knowledge item fields are required.", code="required"
            )

        title = fields.get("title")
        approved_wording = fields.get("approved_wording")
        body_format = fields.get("body_format")
        classification = fields.get("classification")
        confirm = bool(fields.get("confirm", False))

        _validate_write_fields(
            title,
            approved_wording,
            None,
            body_format,
            classification,
            None,
            require_original=False,
        )

        row = self.database.first_row(
            "usp_UpdateKnowledgeItemForOwner",
            [
                ("@UserKey", user_key),
                ("@KnowledgeItemKey", clean_item_key),
                ("@ExpectedRowVersion", expected_row_version),
                ("@Title", title),
                ("@ApprovedWording", approved_wording),
                ("@BodyFormat", body_format),
                ("@Classification", classification),
                ("@Confirm", 1 if confirm else 0),
            ],
        )

        _require_exact_fields(row, UPDATE_ROW_FIELDS, "update result")
        if row["outcome"] not in _FENCED_OUTCOMES:
            raise KnowledgeServiceError("Unexpected update outcome.", code="invalid")
        if row["outcome"] == "changed":
            raise KnowledgeServiceError(
                "The knowledge item changed before this update.", code="changed"
            )
        if not row["version_number"] or not row["row_version"]:
            raise KnowledgeServiceError(
                "The knowledge item update did not return a version.", code="invalid"
            )

        return {
            "version": _positive_int(row["version_number"], "version"),
            "version_token": _version_token(row["row_version"], "row version"),
            "updated": True,
        }

    def archive_knowledge_item_for_owner(self, user_key, item_key, expected_version_token):
        """Version-fenced archive (usp_ArchiveKnowledgeItemForOwner)."""
        self._require_user_key(user_key)
        clean_item_key = self._require_item_key(item_key)
        expected_row_version = self._require_expected_row_version(expected_version_token)

        row = self.database.first_row(
            "usp_ArchiveKnowledgeItemForOwner",
            [
                ("@UserKey", user_key),
                ("@KnowledgeItemKey", clean_item_key),
                ("@ExpectedRowVersion", expected_row_version),
            ],
        )

        _require_exact_fields(row, ARCHIVE_ROW_FIELDS, "archive result")
        if row["outcome"] not in _FENCED_OUTCOMES:
            raise KnowledgeServiceError("Unexpected archive outcome.", code="invalid")
        if row["outcome"] == "changed":
            raise KnowledgeServiceError(
                "The knowledge item changed before this archive.", code="changed"
            )
        if not row["row_version"]:
            raise KnowledgeServiceError(
                "The archive did not return a version.", code="invalid"
            )

        return {
            "version_token": _version_token(row["row_version"], "row version"),
            "archived": True,
        }

    def restore_knowledge_item_for_owner(self, user_key, item_key, expected_version_token):
        """Version-fenced restore (usp_RestoreKnowledgeItemForOwner)."""
        self._require_user_key(user_key)
        clean_item_key = self._require_item_key(item_key)
        expected_row_version = self._require_expected_row_version(expected_version_token)

        row = self.database.first_row(
            "usp_RestoreKnowledgeItemForOwner",
            [
                ("@UserKey", user_key),
                ("@KnowledgeItemKey", clean_item_key),
                ("@ExpectedRowVersion", expected_row_version),
            ],
        )

        _require_exact_fields(row, RESTORE_ROW_FIELDS, "restore result")
        if row["outcome"] not in _FENCED_OUTCOMES:
            raise KnowledgeServiceError("Unexpected restore outcome.", code="invalid")
        if row["outcome"] == "changed":
            raise KnowledgeServiceError(
                "The knowledge item changed before this restore.", code="changed"
            )
        if not row["row_version"]:
            raise KnowledgeServiceError(
                "The restore did not return a version.", code="invalid"
            )

        return {
            "version_token": _version_token(row["row_version"], "row version"),
            "restored": True,
        }

    def delete_knowledge_item_for_owner(self, user_key, item_key, expected_version_token):
        """Version-fenced hard delete (usp_DeleteKnowledgeItemForOwner).

        W1 has no downstream use table yet (architecture doc 17 section
        5.4/5.5; doc 18 slice W4), so this is a plain item+versions delete
        with no affected-use warning — exactly as the procedure's own
        header documents. W4 must change both together before any
        knowledge_item_uses row can reference a deleted item.
        """
        self._require_user_key(user_key)
        clean_item_key = self._require_item_key(item_key)
        expected_row_version = self._require_expected_row_version(expected_version_token)

        row = self.database.first_row(
            "usp_DeleteKnowledgeItemForOwner",
            [
                ("@UserKey", user_key),
                ("@KnowledgeItemKey", clean_item_key),
                ("@ExpectedRowVersion", expected_row_version),
            ],
        )

        _require_exact_fields(row, DELETE_ROW_FIELDS, "delete result")
        if row["outcome"] not in _FENCED_OUTCOMES:
            raise KnowledgeServiceError("Unexpected delete outcome.", code="invalid")
        if row["outcome"] == "changed":
            raise KnowledgeServiceError(
                "The knowledge item changed before this delete.", code="changed"
            )
        if not row["deleted_version_count"]:
            raise KnowledgeServiceError(
                "The delete did not report a version count.", code="invalid"
            )

        return {
            "deleted_version_count": _positive_int(
                row["deleted_version_count"], "deleted version count"
            ),
            "deleted": True,
        }

    def confirm_authored_knowledge_backlog_for_owner(self, user_key, *, max_items=None):
        """Leg 9 (PS-WORKSHOP-002): the owner's standing-rule reconciliation
        (usp_ConfirmAuthoredKnowledgeBacklogForOwner).

        Sweeps this owner's PRE-EXISTING ``unfinished`` knowledge items to
        ``confirmed`` in place, with zero member action. This is not an
        edit: the procedure never touches ``updated_at_utc`` (the sole
        ordering column for both this module's own list read and
        ``usp_ListOpportunityEvidenceForOwner``'s evidence window) and never
        writes a ``knowledge_item_versions`` row, so title, approved
        wording, original wording, and authored-via provenance are
        untouched. A ``suggested`` (unaccepted AI proposal) or ``archived``
        row can never be touched by this call.

        Callers wire this in degrade-safe: a ``DatabaseServiceError`` here
        (including "the procedure does not exist yet" before the owner's
        gate/apply) must be treated as skip-not-fail, never as a reason to
        deny the member their page. See workshop_routes.py and
        opportunity_slate_routes.py.
        """
        self._require_user_key(user_key)
        parameters = [("@UserKey", user_key)]
        if max_items is not None:
            parameters.append(("@MaxItems", _positive_int(max_items, "max items")))

        row = self.database.first_row(
            "usp_ConfirmAuthoredKnowledgeBacklogForOwner", parameters
        )
        _require_exact_fields(
            row, BACKLOG_CONFIRM_ROW_FIELDS, "backlog confirmation result"
        )

        return {
            "confirmed_count": _non_negative_int(
                row["confirmed_count"], "confirmed count"
            ),
            "remaining_count": _non_negative_int(
                row["remaining_count"], "remaining count"
            ),
        }


knowledge_service = KnowledgeService()
