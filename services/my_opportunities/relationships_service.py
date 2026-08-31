"""Owner-scoped C6 saves, lifecycle overlays, and Slate-link persistence.

Route-free and provider-neutral, mirroring C3/C4/C5: no Flask, no identity,
no provider credentials.  A member's ``user_key`` is always the first,
server-derived argument on every member-facing method (_require_user_key).
Overlays are presentation truth DERIVED at read time from canonical listing
state and the member's own last-reviewed basis; nothing here ever writes an
overlay, and the save/remove/undo machine never touches shared data.
"""

from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import asdict, dataclass, is_dataclass, replace
from datetime import date, datetime, timedelta, timezone
from typing import Protocol, Sequence
from uuid import uuid4

from .canonical_service import DATA_CLASSES, LISTING_STATES
from .qualification_service import GATE_FULLY_VERIFIED, GATE_NOT_FULLY_VERIFIED

CONTRACT_VERSION = "1.0"

# ---------------------------------------------------------------------------
# Closed vocabularies (verbatim from the governing docs; the SQL CHECKs in
# PS-MYOPP-005 must admit every literal below). MINOR 3 self-review
# correction: what the test suite actually proves is literal-PRESENCE
# checking -- each closed-vocabulary string here is confirmed to appear as
# an `N'...'` literal somewhere in the forward migration's DDL text (a
# byte-equal substring match per literal, not a full byte-equal
# reconstruction of each CHECK constraint's value list, so it would not by
# itself catch an extra, unintended literal added to a SQL CHECK). Real
# catalog-shape verification -- that the CHECK constraints exist, parse,
# and evaluate as intended against a live SQL Server catalog -- is what the
# disposable-database gate proof supplies (still outstanding; "gate": null
# in the registry entry).
# ---------------------------------------------------------------------------

# --- doc 03 §7 save machine (closed) ---------------------------------------
SAVE_STATE_SAVED = "saved"
SAVE_STATE_REMOVING = "removing"  # inside the undo window
SAVE_STATE_REMOVED = "removed"  # terminal; re-save creates a new row
SAVE_STATES = frozenset({SAVE_STATE_SAVED, SAVE_STATE_REMOVING, SAVE_STATE_REMOVED})

# --- doc 03 §7 presentation overlays (closed; DERIVED, never persisted) ----
OVERLAY_POSTING_CHANGED = "posting_changed"
OVERLAY_CLOSED_BY_SOURCE = "closed_by_source"
OVERLAY_COULD_NOT_REVERIFY = "could_not_reverify"
OVERLAYS = frozenset({OVERLAY_POSTING_CHANGED, OVERLAY_CLOSED_BY_SOURCE, OVERLAY_COULD_NOT_REVERIFY})
OVERLAY_ORDER = (OVERLAY_POSTING_CHANGED, OVERLAY_CLOSED_BY_SOURCE, OVERLAY_COULD_NOT_REVERIFY)

# --- doc 03 §7 saved-view filters (closed; verbatim: all/current/changed/closed/unreachable)
SAVED_FILTER_ALL = "all"
SAVED_FILTER_CURRENT = "current"  # no overlay
SAVED_FILTER_CHANGED = "changed"  # posting_changed present
SAVED_FILTER_CLOSED = "closed"  # closed_by_source present
SAVED_FILTER_UNREACHABLE = "unreachable"  # could_not_reverify present
SAVED_STATE_FILTERS = frozenset(
    {SAVED_FILTER_ALL, SAVED_FILTER_CURRENT, SAVED_FILTER_CHANGED, SAVED_FILTER_CLOSED, SAVED_FILTER_UNREACHABLE}
)

# --- verification filter: "verification outcome at last assessment" --------
# Gate vocabulary is imported verbatim from C5; "not_assessed" is the truthful
# absent state (doc 09 §5: missing facts are never invented).
VERIFICATION_NOT_ASSESSED = "not_assessed"
VERIFICATION_OUTCOMES = frozenset({GATE_FULLY_VERIFIED, GATE_NOT_FULLY_VERIFIED, VERIFICATION_NOT_ASSESSED})
VERIFICATION_FILTERS = frozenset({"all"}) | VERIFICATION_OUTCOMES

# --- doc 03 §8 slate_link (closed; C6 persists, C7 commands) ---------------
LINK_STATE_LINKED = "linked"
LINK_STATE_UNLINKED = "unlinked"  # history label, terminal; no cascade delete of the save
LINK_STATES = frozenset({LINK_STATE_LINKED, LINK_STATE_UNLINKED})
CREATED_FROM_RESULT = "result"
CREATED_FROM_SAVED = "saved"
CREATED_FROM_SOURCES = frozenset({CREATED_FROM_RESULT, CREATED_FROM_SAVED})  # doc 02 §1

# --- listing states that cannot currently be re-verified (§5.3 rule 4) -----
_COULD_NOT_REVERIFY_LISTING_STATES = frozenset({"unreachable", "stale", "quarantined", "invalid", "intake"})
_LISTING_STATE_CURRENT = "current"
_LISTING_STATE_CHANGED = "changed"
_LISTING_STATE_CLOSED = "closed"
# MINOR 4 self-review addition (doc 03 §9.3): "current" and "changed" both
# describe an existing, tracked governing head -- "current" IS that head;
# "changed" means the head just moved -- so both structurally REQUIRE a
# non-None governing_source_version_key. A basis claiming one of these two
# states with no governing key is not a legitimate absence (unlike
# intake/closed/unreachable/stale/quarantined/invalid, which may or may not
# carry a last-known governing key depending on when/how truth was lost);
# it is a composition bug in whatever built the GoverningBasis.
_LISTING_STATES_REQUIRING_GOVERNING_KEY = frozenset({_LISTING_STATE_CURRENT, _LISTING_STATE_CHANGED})

# --- bounds (C3/C5 values) --------------------------------------------------
MAX_USER_KEY_UTF16_UNITS = 300
MAX_IDEMPOTENCY_KEY_UTF16_UNITS = 200
MAX_OPPORTUNITY_KEY_UTF16_UNITS = 200
MAX_SOURCE_VERSION_KEY_UTF16_UNITS = 200
MAX_SAVE_KEY_UTF16_UNITS = 200
MAX_LINK_KEY_UTF16_UNITS = 200
MAX_WORKSPACE_REF_UTF16_UNITS = 200
MAX_SEARCH_TEXT_UTF16_UNITS = 300
IDEMPOTENCY_TTL = timedelta(hours=24)  # C3 value

DEFAULT_UNDO_WINDOW = timedelta(seconds=30)  # mechanism from doc 03 §7;
# the docs fix the mechanism, not a duration; this is a C6-owned,
# service-configurable implementation default (see the README's "Known
# limitations" -- no owner decision required; changing it is a limits
# change, never a migration).


# ---------------------------------------------------------------------------
# Helpers (copied idioms from qualification_service.py -- same semantics)
# ---------------------------------------------------------------------------


def _utc(value: datetime | None = None) -> datetime:
    resolved = value or datetime.now(timezone.utc)
    if resolved.tzinfo is None:
        raise ValueError("now_requires_timezone")
    return resolved.astimezone(timezone.utc)


def _utf16_units(value: str) -> int:
    return len(value.encode("utf-16-le")) // 2


def _opaque_key() -> str:
    return uuid4().hex


def _bounded_string(value: object, label: str, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RelationshipsServiceError(f"{label}_required")
    normalized = value.strip()
    if _utf16_units(normalized) > maximum:
        raise RelationshipsServiceError(f"{label}_too_long")
    return normalized


def _require_user_key(value: object) -> str:
    return _bounded_string(value, "user_key", MAX_USER_KEY_UTF16_UNITS)


def _owner_key_or_not_found(value: object, maximum: int) -> str:
    """Opaque save_key/link_key guard (conservative resolution -- see the
    README: the closed failure-code list (below) has no dedicated
    ``save_key_required``/``link_key_required`` bounds code, so a
    non-string, empty, or over-length opaque key refuses ``not_found``
    rather than inventing a new code or silently truncating.  Every
    ``_opaque_key()`` this service ever generates is a 32-character
    ``uuid4().hex``, well inside ``maximum``, so a genuinely issued key
    never trips the length guard; this only ever catches malformed input."""
    if not isinstance(value, str) or not value.strip() or _utf16_units(value.strip()) > maximum:
        raise RelationshipsServiceError("not_found")
    return value.strip()


def _canonical_value(value: object) -> object:
    if is_dataclass(value) and not isinstance(value, type):
        return _canonical_value(asdict(value))
    if isinstance(value, dict):
        return {str(key): _canonical_value(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, (frozenset, set)):
        items = [_canonical_value(item) for item in value]
        items.sort(key=lambda item: json.dumps(item, sort_keys=True, default=str))
        return items
    if isinstance(value, (tuple, list)):
        return [_canonical_value(item) for item in value]
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise RelationshipsServiceError("canonical_input_invalid")


def _canonical_hash(command: str, value: object) -> str:
    encoded = json.dumps(
        {"command": command, "input": _canonical_value(value)},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _expect(value: object, expected_type: type) -> object:
    if not isinstance(value, expected_type):
        raise RelationshipsServiceError("idempotency_result_invalid")
    return value


# ---------------------------------------------------------------------------
# Failure codes (closed; doc 09 §4 shape)
# ---------------------------------------------------------------------------


def _failure_message(code: str) -> str:
    return {
        "not_found": "That item is not available.",
        "user_key_required": "A member identity is required.",
        "user_key_too_long": "That member identity is too long.",
        "idempotency_key_required": "A request key is required.",
        "idempotency_key_too_long": "That request key is too long.",
        "idempotency_mismatch": "That request key was already used for a different action.",
        "idempotency_result_invalid": "That request could not be replayed safely.",
        "opportunity_key_required": "An opportunity is required.",
        "opportunity_key_too_long": "That opportunity reference is too long.",
        "source_version_key_required": "A reviewed posting version is required.",
        "source_version_key_too_long": "That posting version reference is too long.",
        "data_class_invalid": "That data class is not valid.",
        "filter_invalid": "That filter is not valid.",
        "search_text_too_long": "That search text is too long.",
        "save_removed": "That saved item was already removed. Save it again to bring it back.",
        "not_removing": "That item is not being removed, so there is nothing to undo.",
        "undo_window_elapsed": "It's too late to undo that removal. Save it again if you want it back.",
        "review_version_not_governing": "This posting is being re-verified. Review it again once the update is confirmed.",
        "active_link_exists": "You already have an active Slate for this opportunity.",
        "link_unlinked": "That Slate link is no longer active.",
        "workspace_ref_required": "A workspace reference is required.",
        "workspace_ref_too_long": "That workspace reference is too long.",
        "created_from_invalid": "That origin is not valid.",
        "save_outcome_unknown": "We couldn't confirm that action went through. Reload and try again.",
        "retry_locked_state_reload_required": "Reload before trying that again.",
    }.get(code, "That request could not be completed.")


class RelationshipsServiceError(RuntimeError):
    """C3/C4/C5 pattern: ``.failure_code``, ``.recoverable``,
    ``.member_message``, plus ``.current_state`` (the doc 09 §4
    ``current_state?`` slot) carrying the live record on state-refusals so
    the caller re-renders truth."""

    def __init__(
        self, failure_code: str, *, recoverable: bool | None = None, current_state: object | None = None
    ) -> None:
        self.failure_code = failure_code
        self.recoverable = bool(recoverable) if recoverable is not None else False
        self.current_state = current_state
        self.member_message = _failure_message(failure_code)
        super().__init__(failure_code)


class RepositoryWriteError(RuntimeError):
    """Raised by a repository write when storage fails.  NEVER converted
    into any save/link state; the service converts this into
    ``save_outcome_unknown`` and fabricates no record (doc 09 §4)."""


# ---------------------------------------------------------------------------
# Record shapes (frozen dataclasses)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RelationshipsLimits:
    undo_window: timedelta = DEFAULT_UNDO_WINDOW

    def __post_init__(self) -> None:
        if self.undo_window <= timedelta(0):
            raise ValueError("relationships_limits_invalid")


@dataclass(frozen=True)
class SavedOpportunity:
    save_key: str
    user_key: str
    data_class: str  # fixture | production (doc 02 fixture isolation)
    opportunity_key: str  # reference, never a copy (doc 02 §1)
    last_reviewed_source_version_key: str  # the version the member last reviewed
    state: str  # SAVE_STATES
    saved_at: datetime
    removal_requested_at: datetime | None  # paired: state in {removing, removed}
    removed_at: datetime | None  # paired: state == removed

    def __post_init__(self) -> None:
        if self.state not in SAVE_STATES:
            raise ValueError("invalid_save_state")
        if self.data_class not in DATA_CLASSES:
            raise ValueError("invalid_data_class")
        if self.state == SAVE_STATE_SAVED and (
            self.removal_requested_at is not None or self.removed_at is not None
        ):
            raise ValueError("invalid_state_timestamp_pairing")
        if self.state == SAVE_STATE_REMOVING and (
            self.removal_requested_at is None or self.removed_at is not None
        ):
            raise ValueError("invalid_state_timestamp_pairing")
        if self.state == SAVE_STATE_REMOVED and (
            self.removal_requested_at is None
            or self.removed_at is None
            or self.removed_at < self.removal_requested_at
        ):
            raise ValueError("invalid_state_timestamp_pairing")
        # MINOR 10: mirror CK_myopp_saved_opportunities_removal_after_save
        # (removal_requested_at_utc IS NULL OR >= saved_at_utc) in Python,
        # not only SQL -- one invariant, enforced at both layers.
        if self.removal_requested_at is not None and self.removal_requested_at < self.saved_at:
            raise ValueError("invalid_state_timestamp_pairing")


@dataclass(frozen=True)
class SlateLink:
    link_key: str
    user_key: str
    data_class: str
    opportunity_key: str
    slate_workspace_ref: str  # opaque reference; see the README §7.2 note (no cross-domain FK)
    created_from: str  # CREATED_FROM_SOURCES (doc 02 §1)
    handoff_source_version_key: str  # the source_version handed off (doc 11 §4)
    state: str  # LINK_STATES
    created_at: datetime
    unlinked_at: datetime | None  # paired: state == unlinked

    def __post_init__(self) -> None:
        if self.state not in LINK_STATES:
            raise ValueError("invalid_link_state")
        if self.data_class not in DATA_CLASSES:
            raise ValueError("invalid_data_class")
        if self.created_from not in CREATED_FROM_SOURCES:
            raise ValueError("invalid_created_from")
        if (self.unlinked_at is not None) != (self.state == LINK_STATE_UNLINKED):
            raise ValueError("invalid_state_timestamp_pairing")
        # MINOR 10: mirror CK_myopp_slate_links_state_timestamps's
        # unlinked_at_utc >= created_at_utc clause in Python too.
        if self.unlinked_at is not None and self.unlinked_at < self.created_at:
            raise ValueError("invalid_state_timestamp_pairing")


@dataclass(frozen=True)
class GoverningBasis:
    """Read-only canonical truth consumed for overlay derivation (doc 08 §1:
    overlay derivation is the system role reading listing states)."""

    opportunity_key: str
    data_class: str
    listing_state: str  # LISTING_STATES (imported from C2)
    governing_source_version_key: str | None  # None while no governing head
    last_attempted_at: datetime | None
    last_successfully_verified_at: datetime | None

    def __post_init__(self) -> None:
        if self.listing_state not in LISTING_STATES:
            raise ValueError("invalid_listing_state")
        if self.data_class not in DATA_CLASSES:
            raise ValueError("invalid_data_class")
        # MINOR 4 (doc 03 §9.3): a "current" or "changed" listing_state
        # without a governing_source_version_key is not a legitimate
        # absence -- both states describe an existing, tracked governing
        # head. Refusing loudly here turns a C2 composition bug into an
        # immediate ValueError instead of a silently wrong derived overlay
        # (derive_lifecycle_overlays would otherwise treat a None
        # governing key on a "current" basis as "nothing to compare,"
        # masking the inconsistency).
        if self.listing_state in _LISTING_STATES_REQUIRING_GOVERNING_KEY and self.governing_source_version_key is None:
            raise ValueError(
                f"governing_basis_inconsistent: listing_state={self.listing_state!r} "
                "requires a non-None governing_source_version_key"
            )


@dataclass(frozen=True)
class SavedDisplayFacts:
    """Resolved-at-read display references for local search only.  May be
    entirely None when rights-removed/unavailable -- never substituted
    (doc 04 §8)."""

    role_title: str | None
    employer_name: str | None


@dataclass(frozen=True)
class SavedListEntry:
    """The derived saved-view row.  Assembled per read; never persisted."""

    save: SavedOpportunity
    overlays: tuple[str, ...]  # subset of OVERLAYS, in OVERLAY_ORDER
    listing_state: str | None  # None when basis unavailable
    verification_outcome: str  # VERIFICATION_OUTCOMES
    display: SavedDisplayFacts
    last_successfully_verified_at: datetime | None  # REC-07: success timestamp...
    last_attempted_at: datetime | None  # ...and attempts rendered separately


# ---------------------------------------------------------------------------
# Protocols (dependency seams; all injected, all read-only toward other
# packages -- C6 changes no C2/C4/C5 file)
# ---------------------------------------------------------------------------


class GoverningBasisReader(Protocol):
    """Canonical read seam (C2-backed in composition; in-memory in P-1)."""

    def governing_basis(self, opportunity_key: str, data_class: str) -> GoverningBasis | None: ...

    def display_facts(self, opportunity_key: str, data_class: str) -> SavedDisplayFacts | None: ...


class VerificationReader(Protocol):
    """Owner-scoped C5 read seam: the member's own latest gate outcome for
    an opportunity; None => never assessed => VERIFICATION_NOT_ASSESSED."""

    def latest_gate_outcome(self, user_key: str, opportunity_key: str) -> str | None: ...


@dataclass(frozen=True)
class _IdempotencyRecord:  # C3 shape, verbatim fields
    command: str
    canonical_input_hash: str
    result: object
    expires_at: datetime


class RelationshipsRepository(Protocol):
    # saves (every method owner-scoped: user_key first, filtered IN the query)
    def save_for_owner(self, user_key: str, save_key: str) -> SavedOpportunity | None: ...

    def active_save_for_opportunity(self, user_key: str, opportunity_key: str) -> SavedOpportunity | None: ...
    # state != removed; at most one by the §7 filtered unique index

    def saves_for_owner(self, user_key: str) -> tuple[SavedOpportunity, ...]: ...

    def persist_save(self, save: SavedOpportunity) -> None: ...  # insert only

    def update_save(self, save: SavedOpportunity) -> None: ...  # legal transitions only

    def saves_with_elapsed_removals(
        self, *, now: datetime, undo_window: timedelta, limit: int
    ) -> tuple[SavedOpportunity, ...]: ...
    # Content-blind bounded sweep primitive (key + age only; doc 08 §5 TTL
    # discipline). Not in the blueprint's own §4 Protocol snippet -- a
    # structural fill-in required for `finalize_elapsed_removals` to exist
    # at all, the same category of addition C4's README records as item 9
    # (mirrors `RetrievalRepository.purge_abandoned_executions`).

    # slate links (persistence primitives only; commands are C7's)
    def link_for_owner(self, user_key: str, link_key: str) -> SlateLink | None: ...

    def active_link_for_opportunity(self, user_key: str, opportunity_key: str) -> SlateLink | None: ...

    def links_for_owner(self, user_key: str, opportunity_key: str | None = None) -> tuple[SlateLink, ...]: ...

    def persist_link(self, link: SlateLink) -> None: ...  # insert only

    def update_link(self, link: SlateLink) -> None: ...  # linked -> unlinked only

    # idempotency (C3 shape)
    def _idempotency_record(self, user_key: str, key: str, now: datetime) -> _IdempotencyRecord | None: ...

    def _record_idempotency(
        self, user_key: str, key: str, command: str, digest: str, result: object, now: datetime
    ) -> None: ...


# ---------------------------------------------------------------------------
# In-memory reference implementation (P-1 truth)
# ---------------------------------------------------------------------------

_SAVE_LEGAL_TRANSITIONS = frozenset(
    {
        (SAVE_STATE_SAVED, SAVE_STATE_REMOVING),
        (SAVE_STATE_REMOVING, SAVE_STATE_SAVED),
        (SAVE_STATE_REMOVING, SAVE_STATE_REMOVED),
    }
)
_SAVE_IDENTITY_FIELDS = ("save_key", "user_key", "data_class", "opportunity_key", "saved_at")

_LINK_LEGAL_TRANSITIONS = frozenset({(LINK_STATE_LINKED, LINK_STATE_UNLINKED)})
_LINK_IDENTITY_FIELDS = (
    "link_key",
    "user_key",
    "data_class",
    "opportunity_key",
    "slate_workspace_ref",
    "created_from",
    "handoff_source_version_key",
    "created_at",
)


def _validate_save_transition(prior: SavedOpportunity, new: SavedOpportunity) -> None:
    if prior.state == SAVE_STATE_REMOVED:
        raise RepositoryWriteError("save_terminal")
    for field_name in _SAVE_IDENTITY_FIELDS:
        if getattr(prior, field_name) != getattr(new, field_name):
            raise RepositoryWriteError("save_identity_changed")
    if new.state != prior.state:
        if (prior.state, new.state) not in _SAVE_LEGAL_TRANSITIONS:
            raise RepositoryWriteError("illegal_save_transition")
    else:
        # Non-state field updates: only last_reviewed_source_version_key may
        # change (member review); removal_requested_at/removed_at must be
        # byte-identical when the state itself did not move.
        if new.removal_requested_at != prior.removal_requested_at or new.removed_at != prior.removed_at:
            raise RepositoryWriteError("illegal_save_field_change")


def _validate_link_transition(prior: SlateLink, new: SlateLink) -> None:
    if prior.state == LINK_STATE_UNLINKED:
        raise RepositoryWriteError("link_terminal")
    for field_name in _LINK_IDENTITY_FIELDS:
        if getattr(prior, field_name) != getattr(new, field_name):
            raise RepositoryWriteError("link_identity_changed")
    if new.state != prior.state and (prior.state, new.state) not in _LINK_LEGAL_TRANSITIONS:
        raise RepositoryWriteError("illegal_link_transition")


class InMemoryRelationshipsRepository:
    """C3/C4/C5 idiom: dict stores keyed by save_key/link_key,
    ``(user_key, opportunity_key)`` active indices, a reentrant lock, owner
    re-check inside every ``*_for_owner`` read (a row is returned only when
    ``row.user_key == user_key``), a TTL-aware idempotency map, and a
    content-safe ``state_digest()``.  ``update_save``/``update_link``
    re-validate the legal-transition table and refuse illegal writes with
    :class:`RepositoryWriteError` even if a service bug asked -- the
    in-memory reference enforces what the SQL triggers enforce, one
    behavior contract in two stores."""

    def __init__(self) -> None:
        self._saves: dict[str, SavedOpportunity] = {}
        self._active_save_index: dict[tuple[str, str], str] = {}  # (user_key, opportunity_key) -> save_key
        self._links: dict[str, SlateLink] = {}
        self._active_link_index: dict[tuple[str, str], str] = {}  # (user_key, opportunity_key) -> link_key
        self._idempotency: dict[tuple[str, str], _IdempotencyRecord] = {}
        self._lock = threading.RLock()

    # -- saves ------------------------------------------------------------

    def save_for_owner(self, user_key: str, save_key: str) -> SavedOpportunity | None:
        save = self._saves.get(save_key)
        return save if save is not None and save.user_key == user_key else None

    def active_save_for_opportunity(self, user_key: str, opportunity_key: str) -> SavedOpportunity | None:
        save_key = self._active_save_index.get((user_key, opportunity_key))
        return self._saves.get(save_key) if save_key is not None else None

    def saves_for_owner(self, user_key: str) -> tuple[SavedOpportunity, ...]:
        return tuple(save for save in self._saves.values() if save.user_key == user_key)

    def persist_save(self, save: SavedOpportunity) -> None:
        with self._lock:
            if save.save_key in self._saves:
                raise RepositoryWriteError("save_exists")
            identity = (save.user_key, save.opportunity_key)
            if save.state != SAVE_STATE_REMOVED and identity in self._active_save_index:
                raise RepositoryWriteError("active_save_exists")
            self._saves[save.save_key] = save
            if save.state != SAVE_STATE_REMOVED:
                self._active_save_index[identity] = save.save_key

    def update_save(self, save: SavedOpportunity) -> None:
        with self._lock:
            prior = self._saves.get(save.save_key)
            if prior is None or prior.user_key != save.user_key:
                raise RepositoryWriteError("save_not_found")
            _validate_save_transition(prior, save)
            self._saves[save.save_key] = save
            identity = (save.user_key, save.opportunity_key)
            if save.state == SAVE_STATE_REMOVED:
                if self._active_save_index.get(identity) == save.save_key:
                    del self._active_save_index[identity]
            else:
                self._active_save_index[identity] = save.save_key

    def saves_with_elapsed_removals(
        self, *, now: datetime, undo_window: timedelta, limit: int
    ) -> tuple[SavedOpportunity, ...]:
        with self._lock:
            candidates = [
                row
                for row in self._saves.values()
                if row.state == SAVE_STATE_REMOVING and now >= row.removal_requested_at + undo_window
            ]
            candidates.sort(key=lambda row: (row.removal_requested_at, row.save_key))
            return tuple(candidates[:limit])

    # -- slate links --------------------------------------------------------

    def link_for_owner(self, user_key: str, link_key: str) -> SlateLink | None:
        link = self._links.get(link_key)
        return link if link is not None and link.user_key == user_key else None

    def active_link_for_opportunity(self, user_key: str, opportunity_key: str) -> SlateLink | None:
        link_key = self._active_link_index.get((user_key, opportunity_key))
        return self._links.get(link_key) if link_key is not None else None

    def links_for_owner(self, user_key: str, opportunity_key: str | None = None) -> tuple[SlateLink, ...]:
        return tuple(
            link
            for link in self._links.values()
            if link.user_key == user_key and (opportunity_key is None or link.opportunity_key == opportunity_key)
        )

    def persist_link(self, link: SlateLink) -> None:
        with self._lock:
            if link.link_key in self._links:
                raise RepositoryWriteError("link_exists")
            identity = (link.user_key, link.opportunity_key)
            if link.state == LINK_STATE_LINKED and identity in self._active_link_index:
                raise RepositoryWriteError("active_link_exists")
            self._links[link.link_key] = link
            if link.state == LINK_STATE_LINKED:
                self._active_link_index[identity] = link.link_key

    def update_link(self, link: SlateLink) -> None:
        with self._lock:
            prior = self._links.get(link.link_key)
            if prior is None or prior.user_key != link.user_key:
                raise RepositoryWriteError("link_not_found")
            _validate_link_transition(prior, link)
            self._links[link.link_key] = link
            identity = (link.user_key, link.opportunity_key)
            if link.state == LINK_STATE_UNLINKED and self._active_link_index.get(identity) == link.link_key:
                del self._active_link_index[identity]

    # -- idempotency (C3 shape) ---------------------------------------------

    def _idempotency_record(self, user_key: str, idempotency_key: str, now: datetime) -> _IdempotencyRecord | None:
        record = self._idempotency.get((user_key, idempotency_key))
        if record is not None and record.expires_at <= now:
            del self._idempotency[(user_key, idempotency_key)]
            return None
        return record

    def _record_idempotency(
        self,
        user_key: str,
        idempotency_key: str,
        command: str,
        canonical_input_hash: str,
        result: object,
        now: datetime,
    ) -> None:
        self._idempotency[(user_key, idempotency_key)] = _IdempotencyRecord(
            command, canonical_input_hash, result, now + IDEMPOTENCY_TTL
        )

    def purge_expired_idempotency(self, *, now: datetime) -> int:
        with self._lock:
            expired = [key for key, row in self._idempotency.items() if row.expires_at <= now]
            for key in expired:
                del self._idempotency[key]
            return len(expired)

    def state_digest(self) -> str:
        """Content-safe test aid proving refusals/derivation did not mutate
        repository state, and that a save operation never touches the link
        store (or vice versa)."""
        with self._lock:
            value = {
                "saves": self._saves,
                "links": self._links,
                "idempotency_keys": sorted(f"{owner}:{key}" for owner, key in self._idempotency),
            }
            return hashlib.sha256(
                json.dumps(_canonical_value(value), sort_keys=True, default=str).encode("utf-8")
            ).hexdigest()


class FailingRelationshipsRepository(InMemoryRelationshipsRepository):
    """Test double: raises :class:`RepositoryWriteError` from the named
    write methods (``persist_save``/``update_save``/``persist_link``/
    ``update_link``), starting at the ``fail_after_calls``'th call to that
    specific method (default 1, i.e. every call) -- used by the doc 09 §4
    unknown-outcome suite (Group G).

    ``fail_mode`` selects WHEN the simulated failure fires relative to the
    underlying write (IMPORTANT 6 self-review finding -- both branches of
    the doc 09 §4 ambiguity need coverage, not only one):

    - ``"pre"`` (default): raises BEFORE the write is attempted at all --
      the did-not-land branch (nothing was persisted).
    - ``"post"``: lets the write complete durably against the underlying
      in-memory store and THEN raises -- the landed branch, simulating a
      connection drop after commit. A retry after a state reload must
      discover the write already succeeded via natural idempotency
      (``active_save_for_opportunity``/``active_link_for_opportunity``
      finding the already-persisted row) rather than duplicate it.
    """

    _WRITE_METHODS = ("persist_save", "update_save", "persist_link", "update_link")
    _FAIL_MODES = frozenset({"pre", "post"})

    def __init__(self, *, fail_on: object = (), fail_after_calls: int = 1, fail_mode: str = "pre") -> None:
        super().__init__()
        self._fail_on = set(fail_on)
        self._fail_after_calls = fail_after_calls
        if fail_mode not in self._FAIL_MODES:
            raise ValueError("fail_mode_invalid")
        self._fail_mode = fail_mode
        self._call_counts = {name: 0 for name in self._WRITE_METHODS}

    def _should_fail(self, method_name: str) -> bool:
        self._call_counts[method_name] += 1
        return method_name in self._fail_on and self._call_counts[method_name] >= self._fail_after_calls

    def persist_save(self, save: SavedOpportunity) -> None:
        fail = self._should_fail("persist_save")
        if fail and self._fail_mode == "pre":
            raise RepositoryWriteError("simulated_write_failure")
        super().persist_save(save)
        if fail and self._fail_mode == "post":
            raise RepositoryWriteError("simulated_write_failure")

    def update_save(self, save: SavedOpportunity) -> None:
        fail = self._should_fail("update_save")
        if fail and self._fail_mode == "pre":
            raise RepositoryWriteError("simulated_write_failure")
        super().update_save(save)
        if fail and self._fail_mode == "post":
            raise RepositoryWriteError("simulated_write_failure")

    def persist_link(self, link: SlateLink) -> None:
        fail = self._should_fail("persist_link")
        if fail and self._fail_mode == "pre":
            raise RepositoryWriteError("simulated_write_failure")
        super().persist_link(link)
        if fail and self._fail_mode == "post":
            raise RepositoryWriteError("simulated_write_failure")

    def update_link(self, link: SlateLink) -> None:
        fail = self._should_fail("update_link")
        if fail and self._fail_mode == "pre":
            raise RepositoryWriteError("simulated_write_failure")
        super().update_link(link)
        if fail and self._fail_mode == "post":
            raise RepositoryWriteError("simulated_write_failure")


# ---------------------------------------------------------------------------
# Audit sink (content-free; doc 08 §4, doc 12 §2 member-action events)
# ---------------------------------------------------------------------------

_AUDIT_EVENT_KINDS = frozenset(
    {
        "save_created",
        "save_removed",
        "save_remove_undone",
        "save_remove_finalized",
        "save_change_reviewed",
        "slate_link_recorded",
        "slate_link_unlinked",
        "persistence_failure",
    }
)


@dataclass(frozen=True)
class RelationshipsAuditEvent:
    event_kind: str
    user_key: str
    keys: tuple[str, ...]  # opaque keys only
    reason_code: str | None
    actor: str  # "member" | "system:finalize_sweep"
    at: datetime

    def __post_init__(self) -> None:
        if self.event_kind not in _AUDIT_EVENT_KINDS:
            raise ValueError("invalid_event_kind")
        object.__setattr__(self, "keys", tuple(self.keys))


class AuditSink(Protocol):
    def emit(self, event: RelationshipsAuditEvent) -> None: ...


class InMemoryAuditSink:
    def __init__(self) -> None:
        self.events: list[RelationshipsAuditEvent] = []

    def emit(self, event: RelationshipsAuditEvent) -> None:
        self.events.append(event)


# ---------------------------------------------------------------------------
# Overlay derivation (pure; the doc 14 stop control made structural)
# ---------------------------------------------------------------------------


def derive_lifecycle_overlays(
    reference_source_version_key: str, basis: GoverningBasis | None
) -> tuple[str, ...]:
    """Presentation truth for ONE member context (a saved row's
    last-reviewed basis, or -- for C8's stale-result rendering, doc 04 §8 --
    a result entry's result-time governing basis).  Pure: takes no
    repository, no user_key, no clock; writes nothing; returns a subset of
    OVERLAYS in OVERLAY_ORDER (doc 03 §§1-2, §7; REC-03 accepted
    disposition)."""
    if basis is None:
        # opportunity absent/fenced/rights-removed: the truthful "cannot
        # re-verify" reading; the entry stays listed (saved history is
        # never deleted by shared-side change).
        return (OVERLAY_COULD_NOT_REVERIFY,)

    overlays: set[str] = set()

    # Rule 2 (REC-03 verbatim): the *member* context stays posting_changed
    # after system re-verification returns the listing to `current` (the
    # governing version moved and the member has not reviewed), and any
    # accepted governing change -- content change or governing failover --
    # drives it. Only mark_change_reviewed clears it, per member.
    posting_changed = (
        basis.governing_source_version_key is not None
        and basis.governing_source_version_key != reference_source_version_key
    ) or basis.listing_state == _LISTING_STATE_CHANGED
    if posting_changed:
        overlays.add(OVERLAY_POSTING_CHANGED)

    # Rule 3: source-confirmed closure only -- an outage is never closure.
    if basis.listing_state == _LISTING_STATE_CLOSED:
        overlays.add(OVERLAY_CLOSED_BY_SOURCE)

    # Rule 4: every non-current, non-changed, non-closed head means the
    # governing content cannot currently be re-verified; conservative
    # single mapping into the closed 3-overlay vocabulary.
    if basis.listing_state in _COULD_NOT_REVERIFY_LISTING_STATES:
        overlays.add(OVERLAY_COULD_NOT_REVERIFY)

    # Rule 5: overlays may coexist; ordered, deduplicated.
    return tuple(overlay for overlay in OVERLAY_ORDER if overlay in overlays)


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class RelationshipsService:
    def __init__(
        self,
        repository: RelationshipsRepository,
        basis_reader: GoverningBasisReader,
        verification_reader: VerificationReader,
        audit_sink: AuditSink | None = None,
        limits: RelationshipsLimits = RelationshipsLimits(),
    ) -> None:
        self.repository = repository
        self._basis_reader = basis_reader
        self._verification_reader = verification_reader
        self._audit_sink = audit_sink or InMemoryAuditSink()
        self._limits = limits
        self._lock = getattr(repository, "_lock", None) or threading.RLock()
        # doc 09 §4 blind-retry lockout (§5.6): user_key -> the set of
        # idempotency_keys whose write outcome is unknown until a state
        # reload proves the truth.
        self._unknown_outcomes: dict[str, set[str]] = {}

    # -- idempotency plumbing (C3 pattern) -----------------------------

    def _begin(
        self, user_key: str, idempotency_key: str, command: str, canonical: object, now: datetime
    ) -> tuple[object | None, str, str]:
        key = _bounded_string(idempotency_key, "idempotency_key", MAX_IDEMPOTENCY_KEY_UTF16_UNITS)
        digest = _canonical_hash(command, canonical)
        record = self.repository._idempotency_record(user_key, key, now)
        if record is not None:
            if record.command == command and record.canonical_input_hash == digest:
                return record.result, key, digest
            raise RelationshipsServiceError("idempotency_mismatch")
        return None, key, digest

    def _finish(
        self, user_key: str, idempotency_key: str, command: str, digest: str, result: object, now: datetime
    ) -> None:
        self.repository._record_idempotency(user_key, idempotency_key, command, digest, result, now)

    def _emit(
        self, event_kind: str, user_key: str, keys: Sequence[str], reason_code: str | None, actor: str, at: datetime
    ) -> None:
        self._audit_sink.emit(
            RelationshipsAuditEvent(
                event_kind=event_kind, user_key=user_key, keys=tuple(keys), reason_code=reason_code, actor=actor, at=at
            )
        )

    # -- doc 09 §4 unknown-outcome write discipline (§5.6) -------------

    def _check_not_locked(self, user_key: str, idempotency_key: str) -> None:
        locked = self._unknown_outcomes.get(user_key)
        if locked and idempotency_key in locked:
            raise RelationshipsServiceError("retry_locked_state_reload_required", recoverable=True)

    def _lock_unknown_outcome(self, user_key: str, idempotency_key: str) -> None:
        self._unknown_outcomes.setdefault(user_key, set()).add(idempotency_key)

    def _clear_unknown_outcomes(self, user_key: str) -> None:
        self._unknown_outcomes.pop(user_key, None)

    def _record_unknown_write_failure(
        self, user_key: str, idempotency_key: str, keys: Sequence[str], now: datetime
    ) -> None:
        # No idempotency receipt is recorded (the command did not complete
        # -- a later legitimate retry must be able to run), no record is
        # fabricated, and the blind-retry lockout is armed before raising.
        self._lock_unknown_outcome(user_key, idempotency_key)
        self._emit("persistence_failure", user_key, keys, None, "member", now)

    # -- lazy finalization (§5.1) --------------------------------------

    def _finalize_if_elapsed(self, save: SavedOpportunity | None, now: datetime) -> SavedOpportunity | None:
        """A ``removing`` row whose undo window has elapsed is finalized to
        ``removed`` before any further logic runs.  Best-effort against the
        repository: a persistence hiccup here must never block a read
        (often the very state-reload a member needs to clear an
        unknown-outcome lock), so the locally computed truth is always what
        is returned/acted on even if the write itself could not be durably
        recorded this pass ("truth is derived, storage catches up" -- see
        the README's "Known limitations")."""
        if save is None or save.state != SAVE_STATE_REMOVING:
            return save
        deadline = save.removal_requested_at + self._limits.undo_window
        if now < deadline:
            return save
        finalized = replace(save, state=SAVE_STATE_REMOVED, removed_at=deadline)
        try:
            self.repository.update_save(finalized)
        except RepositoryWriteError:
            pass
        else:
            self._emit(
                "save_remove_finalized", save.user_key, (finalized.save_key,), None, "system:finalize_sweep", now
            )
        return finalized

    def _load_save_for_owner(self, user_key: str, save_key: str, now: datetime) -> SavedOpportunity:
        save = self.repository.save_for_owner(user_key, save_key)
        if save is None:
            raise RelationshipsServiceError("not_found")
        return self._finalize_if_elapsed(save, now)

    def _replay_save(self, replay: object, now: datetime) -> SavedOpportunity:
        """MINOR 8 self-review adjudication (extended by IMPORTANT 2 to
        every state-returning save command): a replay's IDENTITY is proven
        by the stored receipt (the C3 "byte-identical, no re-execution"
        guarantee is about not re-running the command or writing twice),
        but the RETURNED snapshot for all four state-returning
        ``SavedOpportunity`` commands (``save_opportunity``,
        ``remove_saved``, ``undo_remove``, ``mark_change_reviewed``) is
        re-read live -- through the same lazy-finalization path every
        other read uses -- rather than echoed frozen from receipt time. A
        member who fires the same request twice must see current truth
        (e.g. a row that has since finalized to `removed`, with no undo
        affordance), not a stale snapshot that no longer describes
        reality. This is a deliberate divergence from an immutable-receipt
        echo, recorded in the README."""
        replayed = _expect(replay, SavedOpportunity)
        live = self.repository.save_for_owner(replayed.user_key, replayed.save_key)
        if live is None:
            return replayed  # defensive: this schema has no erasure path
        return self._finalize_if_elapsed(live, now)

    # -- saves ----------------------------------------------------------

    def save_opportunity(
        self,
        user_key: str,
        *,
        opportunity_key: str,
        data_class: str,
        reviewed_source_version_key: str,
        idempotency_key: str,
        now: datetime | None = None,
    ) -> SavedOpportunity:
        user_key = _require_user_key(user_key)
        now = _utc(now)
        opportunity_key = _bounded_string(opportunity_key, "opportunity_key", MAX_OPPORTUNITY_KEY_UTF16_UNITS)
        if data_class not in DATA_CLASSES:
            raise RelationshipsServiceError("data_class_invalid")
        reviewed_source_version_key = _bounded_string(
            reviewed_source_version_key, "source_version_key", MAX_SOURCE_VERSION_KEY_UTF16_UNITS
        )
        idempotency_key = _bounded_string(idempotency_key, "idempotency_key", MAX_IDEMPOTENCY_KEY_UTF16_UNITS)
        command = "save_opportunity"
        canonical = {
            "opportunity_key": opportunity_key,
            "data_class": data_class,
            "reviewed_source_version_key": reviewed_source_version_key,
        }
        with self._lock:
            self._check_not_locked(user_key, idempotency_key)
            replay, key, digest = self._begin(user_key, idempotency_key, command, canonical, now)
            if replay is not None:
                return self._replay_save(replay, now)

            basis = self._basis_reader.governing_basis(opportunity_key, data_class)
            if basis is None:
                raise RelationshipsServiceError("not_found")

            existing = self.repository.active_save_for_opportunity(user_key, opportunity_key)
            if existing is not None:
                existing = self._finalize_if_elapsed(existing, now)
            if existing is not None and existing.state == SAVE_STATE_SAVED:
                # Saving an already-saved opportunity is a natural no-op:
                # the machine defines only none->saved, and the filtered
                # unique index makes a true duplicate impossible anyway.
                # No write, no receipt mutation, no audit event.
                return existing
            if existing is not None and existing.state == SAVE_STATE_REMOVING:
                # BLOCKING 1 self-review adjudication: a Save pressed while
                # the row is `removing` (inside the undo window) expresses
                # the member's intent to KEEP the item -- without this
                # branch the prior code admitted a `removing` row as
                # "existing," wrote nothing, and echoed success, so the row
                # still finalized to `removed` on window elapse even though
                # the member had just "saved" it. Implement it as the doc
                # 03 §7 removing->saved UNDO transition, structurally
                # identical to undo_remove (only removal_requested_at
                # clears; nothing else on the row changes) -- but record it
                # under THIS command's own idempotency receipt (the
                # save_opportunity canonical/digest/key already computed
                # above), so a replay of this exact save_opportunity call
                # returns live state via _replay_save rather than a
                # silently-vanishing echo.
                updated = replace(existing, state=SAVE_STATE_SAVED, removal_requested_at=None)
                try:
                    self.repository.update_save(updated)
                except RepositoryWriteError:
                    self._record_unknown_write_failure(user_key, key, (existing.save_key,), now)
                    raise RelationshipsServiceError("save_outcome_unknown", recoverable=True)
                self._finish(user_key, key, command, digest, updated, now)
                # Same audit event CLASS undo_remove emits for this exact
                # transition -- this IS that transition, triggered by Save.
                self._emit("save_remove_undone", user_key, (updated.save_key,), None, "member", now)
                return updated

            save = SavedOpportunity(
                save_key=_opaque_key(),
                user_key=user_key,
                data_class=data_class,
                opportunity_key=opportunity_key,
                last_reviewed_source_version_key=reviewed_source_version_key,
                state=SAVE_STATE_SAVED,
                saved_at=now,
                removal_requested_at=None,
                removed_at=None,
            )
            try:
                self.repository.persist_save(save)
            except RepositoryWriteError:
                self._record_unknown_write_failure(user_key, key, (save.save_key,), now)
                raise RelationshipsServiceError("save_outcome_unknown", recoverable=True)
            self._finish(user_key, key, command, digest, save, now)
            self._emit("save_created", user_key, (save.save_key,), None, "member", now)
            return save

    def remove_saved(
        self, user_key: str, *, save_key: str, idempotency_key: str, now: datetime | None = None
    ) -> SavedOpportunity:
        user_key = _require_user_key(user_key)
        now = _utc(now)
        save_key = _owner_key_or_not_found(save_key, MAX_SAVE_KEY_UTF16_UNITS)
        idempotency_key = _bounded_string(idempotency_key, "idempotency_key", MAX_IDEMPOTENCY_KEY_UTF16_UNITS)
        command = "remove_saved"
        canonical = {"save_key": save_key}
        with self._lock:
            self._check_not_locked(user_key, idempotency_key)
            replay, key, digest = self._begin(user_key, idempotency_key, command, canonical, now)
            if replay is not None:
                return self._replay_save(replay, now)

            save = self._load_save_for_owner(user_key, save_key, now)
            if save.state == SAVE_STATE_REMOVED:
                raise RelationshipsServiceError("save_removed", current_state=save)
            if save.state == SAVE_STATE_REMOVING:
                # Idempotent no-op: the member's intent already holds.
                return save

            updated = replace(save, state=SAVE_STATE_REMOVING, removal_requested_at=now)
            try:
                self.repository.update_save(updated)
            except RepositoryWriteError:
                self._record_unknown_write_failure(user_key, key, (save.save_key,), now)
                raise RelationshipsServiceError("save_outcome_unknown", recoverable=True)
            self._finish(user_key, key, command, digest, updated, now)
            self._emit("save_removed", user_key, (updated.save_key,), None, "member", now)
            return updated

    def undo_remove(
        self, user_key: str, *, save_key: str, idempotency_key: str, now: datetime | None = None
    ) -> SavedOpportunity:
        user_key = _require_user_key(user_key)
        now = _utc(now)
        save_key = _owner_key_or_not_found(save_key, MAX_SAVE_KEY_UTF16_UNITS)
        idempotency_key = _bounded_string(idempotency_key, "idempotency_key", MAX_IDEMPOTENCY_KEY_UTF16_UNITS)
        command = "undo_remove"
        canonical = {"save_key": save_key}
        with self._lock:
            self._check_not_locked(user_key, idempotency_key)
            replay, key, digest = self._begin(user_key, idempotency_key, command, canonical, now)
            if replay is not None:
                return self._replay_save(replay, now)

            # Finalize INSIDE the decision (not before) so a just-elapsed
            # window is refused with the truthful, freshly finalized state.
            save = self._load_save_for_owner(user_key, save_key, now)
            if save.state == SAVE_STATE_SAVED:
                raise RelationshipsServiceError("not_removing", current_state=save)
            if save.state == SAVE_STATE_REMOVED:
                # Either genuinely already removed, or just finalized by
                # the load above -- either way, undo never resurrects.
                raise RelationshipsServiceError("undo_window_elapsed", current_state=save)

            updated = replace(save, state=SAVE_STATE_SAVED, removal_requested_at=None)
            try:
                self.repository.update_save(updated)
            except RepositoryWriteError:
                self._record_unknown_write_failure(user_key, key, (save.save_key,), now)
                raise RelationshipsServiceError("save_outcome_unknown", recoverable=True)
            self._finish(user_key, key, command, digest, updated, now)
            self._emit("save_remove_undone", user_key, (updated.save_key,), None, "member", now)
            return updated

    def mark_change_reviewed(
        self,
        user_key: str,
        *,
        save_key: str,
        reviewed_source_version_key: str,
        idempotency_key: str,
        now: datetime | None = None,
    ) -> SavedOpportunity:
        user_key = _require_user_key(user_key)
        now = _utc(now)
        save_key = _owner_key_or_not_found(save_key, MAX_SAVE_KEY_UTF16_UNITS)
        reviewed_source_version_key = _bounded_string(
            reviewed_source_version_key, "source_version_key", MAX_SOURCE_VERSION_KEY_UTF16_UNITS
        )
        idempotency_key = _bounded_string(idempotency_key, "idempotency_key", MAX_IDEMPOTENCY_KEY_UTF16_UNITS)
        command = "mark_change_reviewed"
        canonical = {"save_key": save_key, "reviewed_source_version_key": reviewed_source_version_key}
        with self._lock:
            self._check_not_locked(user_key, idempotency_key)
            replay, key, digest = self._begin(user_key, idempotency_key, command, canonical, now)
            if replay is not None:
                return self._replay_save(replay, now)

            save = self._load_save_for_owner(user_key, save_key, now)
            if save.state == SAVE_STATE_REMOVED:
                raise RelationshipsServiceError("save_removed", current_state=save)

            basis = self._basis_reader.governing_basis(save.opportunity_key, save.data_class)
            if basis is not None and basis.listing_state == _LISTING_STATE_CHANGED:
                # BLOCKER 2 self-review adjudication (option b): while the
                # listing is mid re-verification ("changed"),
                # derive_lifecycle_overlays's rule 2 keeps posting_changed
                # live for ANY "changed" listing_state regardless of
                # whether the submitted version matches the current
                # governing head -- so accepting this write would silently
                # no-op the member's review (a dead end: the command
                # "succeeds" but the overlay never clears). Refuse instead
                # of writing a fake success. No write, no receipt, no
                # audit event -- refusals never mutate (doc 09 §4
                # precedence rule).
                raise RelationshipsServiceError(
                    "review_version_not_governing", recoverable=True, current_state=save
                )
            if (
                basis is None
                or basis.governing_source_version_key is None
                or basis.governing_source_version_key != reviewed_source_version_key
            ):
                # The member reviewed stale content -- reviewing an old
                # version never clears a newer change; the UI reloads and
                # re-offers.
                raise RelationshipsServiceError(
                    "review_version_not_governing", recoverable=True, current_state=save
                )

            updated = replace(save, last_reviewed_source_version_key=reviewed_source_version_key)
            try:
                self.repository.update_save(updated)
            except RepositoryWriteError:
                self._record_unknown_write_failure(user_key, key, (save.save_key,), now)
                raise RelationshipsServiceError("save_outcome_unknown", recoverable=True)
            self._finish(user_key, key, command, digest, updated, now)
            self._emit("save_change_reviewed", user_key, (updated.save_key,), None, "member", now)
            return updated

    # -- saved view -------------------------------------------------------

    def _render_entry(self, user_key: str, save: SavedOpportunity, now: datetime) -> SavedListEntry:
        del now  # basis/verification are read at their own live truth, not gated on a clock here
        basis = self._basis_reader.governing_basis(save.opportunity_key, save.data_class)
        overlays = derive_lifecycle_overlays(save.last_reviewed_source_version_key, basis)
        outcome = (
            self._verification_reader.latest_gate_outcome(user_key, save.opportunity_key) or VERIFICATION_NOT_ASSESSED
        )
        display = self._basis_reader.display_facts(save.opportunity_key, save.data_class) or SavedDisplayFacts(
            role_title=None, employer_name=None
        )
        return SavedListEntry(
            save=save,
            overlays=overlays,
            listing_state=basis.listing_state if basis is not None else None,
            verification_outcome=outcome,
            display=display,
            last_successfully_verified_at=basis.last_successfully_verified_at if basis is not None else None,
            last_attempted_at=basis.last_attempted_at if basis is not None else None,
        )

    def get_saved(self, user_key: str, save_key: str, *, now: datetime | None = None) -> SavedListEntry:
        user_key = _require_user_key(user_key)
        now = _utc(now)
        save_key = _owner_key_or_not_found(save_key, MAX_SAVE_KEY_UTF16_UNITS)
        with self._lock:
            save = self._load_save_for_owner(user_key, save_key, now)
            # MINOR 9: a successful OWNER LOAD (found the row, confirmed
            # ownership) is itself the "state reload" doc 09 §4 promises
            # unlocks the blind-retry lockout -- clear it here, BEFORE the
            # removed-row refusal below, so a locked member whose only row
            # happens to be removed can still unlock via this read instead
            # of being stuck needing list_saved/list_slate_links instead.
            self._clear_unknown_outcomes(user_key)
            if save.state == SAVE_STATE_REMOVED:
                # Symmetric with list_saved's exclusion of terminal rows:
                # a removed save is member history, not a live "get" target
                # (conservative resolution -- see the README).
                raise RelationshipsServiceError("not_found")
            entry = self._render_entry(user_key, save, now)
            return entry

    @staticmethod
    def _matches_saved_state_filter(entry: SavedListEntry, saved_state_filter: str) -> bool:
        if saved_state_filter == SAVED_FILTER_ALL:
            return True
        if saved_state_filter == SAVED_FILTER_CURRENT:
            return entry.overlays == ()
        if saved_state_filter == SAVED_FILTER_CHANGED:
            return OVERLAY_POSTING_CHANGED in entry.overlays
        if saved_state_filter == SAVED_FILTER_CLOSED:
            return OVERLAY_CLOSED_BY_SOURCE in entry.overlays
        if saved_state_filter == SAVED_FILTER_UNREACHABLE:
            return OVERLAY_COULD_NOT_REVERIFY in entry.overlays
        raise AssertionError("unreachable: saved_state_filter already validated")

    @staticmethod
    def _matches_search(entry: SavedListEntry, normalized_search: str) -> bool:
        role_title = (entry.display.role_title or "").casefold()
        employer_name = (entry.display.employer_name or "").casefold()
        return normalized_search in role_title or normalized_search in employer_name

    def list_saved(
        self,
        user_key: str,
        *,
        saved_state_filter: str = SAVED_FILTER_ALL,
        verification_filter: str = "all",
        search_text: str | None = None,
        now: datetime | None = None,
    ) -> tuple[SavedListEntry, ...]:
        user_key = _require_user_key(user_key)
        now = _utc(now)
        if saved_state_filter not in SAVED_STATE_FILTERS:
            raise RelationshipsServiceError("filter_invalid")
        if verification_filter not in VERIFICATION_FILTERS:
            raise RelationshipsServiceError("filter_invalid")
        normalized_search: str | None = None
        if search_text is not None:
            if not isinstance(search_text, str) or _utf16_units(search_text) > MAX_SEARCH_TEXT_UTF16_UNITS:
                # No dedicated "search_text_invalid" code exists in the
                # closed vocabulary; a non-string value refuses under the
                # nearest closed bounds code rather than inventing one or
                # silently coercing (conservative resolution).
                raise RelationshipsServiceError("search_text_too_long")
            stripped = search_text.strip().casefold()
            normalized_search = stripped or None

        with self._lock:
            rows = self.repository.saves_for_owner(user_key)
            entries: list[SavedListEntry] = []
            for row in rows:
                finalized = self._finalize_if_elapsed(row, now)
                if finalized.state == SAVE_STATE_REMOVED:
                    continue  # terminal history; excluded from the live view
                entry = self._render_entry(user_key, finalized, now)
                if not self._matches_saved_state_filter(entry, saved_state_filter):
                    continue
                if verification_filter != "all" and entry.verification_outcome != verification_filter:
                    continue
                if normalized_search is not None and not self._matches_search(entry, normalized_search):
                    continue
                entries.append(entry)

            # Deterministic total order: saved_at DESC, then save_key --
            # two stable sorts (ascending save_key, then descending
            # saved_at) rather than one composite key, since datetime has
            # no natural negation.
            entries.sort(key=lambda item: item.save.save_key)
            entries.sort(key=lambda item: item.save.saved_at, reverse=True)
            self._clear_unknown_outcomes(user_key)
            return tuple(entries)

    def finalize_elapsed_removals(self, *, now: datetime, limit: int = 500) -> int:
        """Content-blind bounded sweep (key + age only; doc 08 §5 TTL
        discipline; actor ``system:finalize_sweep``).  No correctness
        depends on this running -- the machine is truthful with lazy
        finalization alone (doc 09 §3 bounded-job rule; no unbounded
        background loop)."""
        now = _utc(now)
        if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0:
            raise ValueError("finalize_limit_invalid")
        with self._lock:
            candidates = self.repository.saves_with_elapsed_removals(
                now=now, undo_window=self._limits.undo_window, limit=limit
            )
            finalized_count = 0
            for row in candidates:
                finalized = self._finalize_if_elapsed(row, now)
                if finalized.state == SAVE_STATE_REMOVED:
                    finalized_count += 1
            return finalized_count

    # -- slate-link persistence primitives (C7 builds its commands on these)

    def record_slate_link(
        self,
        user_key: str,
        *,
        opportunity_key: str,
        data_class: str,
        slate_workspace_ref: str,
        created_from: str,
        handoff_source_version_key: str,
        idempotency_key: str,
        now: datetime | None = None,
    ) -> SlateLink:
        user_key = _require_user_key(user_key)
        now = _utc(now)
        opportunity_key = _bounded_string(opportunity_key, "opportunity_key", MAX_OPPORTUNITY_KEY_UTF16_UNITS)
        if data_class not in DATA_CLASSES:
            raise RelationshipsServiceError("data_class_invalid")
        slate_workspace_ref = _bounded_string(
            slate_workspace_ref, "workspace_ref", MAX_WORKSPACE_REF_UTF16_UNITS
        )
        if created_from not in CREATED_FROM_SOURCES:
            raise RelationshipsServiceError("created_from_invalid")
        handoff_source_version_key = _bounded_string(
            handoff_source_version_key, "source_version_key", MAX_SOURCE_VERSION_KEY_UTF16_UNITS
        )
        idempotency_key = _bounded_string(idempotency_key, "idempotency_key", MAX_IDEMPOTENCY_KEY_UTF16_UNITS)
        command = "record_slate_link"
        canonical = {
            "opportunity_key": opportunity_key,
            "data_class": data_class,
            "slate_workspace_ref": slate_workspace_ref,
            "created_from": created_from,
            "handoff_source_version_key": handoff_source_version_key,
        }
        with self._lock:
            self._check_not_locked(user_key, idempotency_key)
            replay, key, digest = self._begin(user_key, idempotency_key, command, canonical, now)
            if replay is not None:
                return _expect(replay, SlateLink)

            basis = self._basis_reader.governing_basis(opportunity_key, data_class)
            if basis is None:
                raise RelationshipsServiceError("not_found")

            existing = self.repository.active_link_for_opportunity(user_key, opportunity_key)
            if existing is not None:
                # doc 03 §8: exactly one active link per (member,
                # opportunity); continue, don't duplicate. C7's
                # create_slate_from_opportunity implements "continue" from
                # this refusal's carried current_state.
                raise RelationshipsServiceError("active_link_exists", current_state=existing)

            link = SlateLink(
                link_key=_opaque_key(),
                user_key=user_key,
                data_class=data_class,
                opportunity_key=opportunity_key,
                slate_workspace_ref=slate_workspace_ref,
                created_from=created_from,
                handoff_source_version_key=handoff_source_version_key,
                state=LINK_STATE_LINKED,
                created_at=now,
                unlinked_at=None,
            )
            try:
                self.repository.persist_link(link)
            except RepositoryWriteError:
                self._record_unknown_write_failure(user_key, key, (link.link_key,), now)
                raise RelationshipsServiceError("save_outcome_unknown", recoverable=True)
            self._finish(user_key, key, command, digest, link, now)
            self._emit("slate_link_recorded", user_key, (link.link_key,), None, "member", now)
            return link

    def mark_slate_unlinked(
        self, user_key: str, *, link_key: str, idempotency_key: str, now: datetime | None = None
    ) -> SlateLink:
        user_key = _require_user_key(user_key)
        now = _utc(now)
        link_key = _owner_key_or_not_found(link_key, MAX_LINK_KEY_UTF16_UNITS)
        idempotency_key = _bounded_string(idempotency_key, "idempotency_key", MAX_IDEMPOTENCY_KEY_UTF16_UNITS)
        command = "mark_slate_unlinked"
        canonical = {"link_key": link_key}
        with self._lock:
            self._check_not_locked(user_key, idempotency_key)
            replay, key, digest = self._begin(user_key, idempotency_key, command, canonical, now)
            if replay is not None:
                return _expect(replay, SlateLink)

            link = self.repository.link_for_owner(user_key, link_key)
            if link is None:
                raise RelationshipsServiceError("not_found")
            if link.state == LINK_STATE_UNLINKED:
                raise RelationshipsServiceError("link_unlinked", current_state=link)

            updated = replace(link, state=LINK_STATE_UNLINKED, unlinked_at=now)
            try:
                self.repository.update_link(updated)
            except RepositoryWriteError:
                self._record_unknown_write_failure(user_key, key, (link.link_key,), now)
                raise RelationshipsServiceError("save_outcome_unknown", recoverable=True)
            self._finish(user_key, key, command, digest, updated, now)
            self._emit("slate_link_unlinked", user_key, (updated.link_key,), None, "member", now)
            # NEVER cascades to saved_opportunity (doc 03 §8: "no cascade
            # delete of the save") -- structurally true here: this method
            # never touches self.repository's save-side methods at all.
            return updated

    def list_slate_links(
        self, user_key: str, *, opportunity_key: str | None = None
    ) -> tuple[SlateLink, ...]:
        user_key = _require_user_key(user_key)
        if opportunity_key is not None:
            opportunity_key = _bounded_string(opportunity_key, "opportunity_key", MAX_OPPORTUNITY_KEY_UTF16_UNITS)
        with self._lock:
            links = self.repository.links_for_owner(user_key, opportunity_key)
            ordered = tuple(sorted(links, key=lambda link: (link.created_at, link.link_key)))
            self._clear_unknown_outcomes(user_key)
            return ordered
