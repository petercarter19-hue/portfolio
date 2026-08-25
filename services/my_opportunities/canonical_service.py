"""Canonical shared-side rules for My Opportunities C2.

The service is intentionally independent of Flask, identity, routes, provider
credentials, and ``database_service``.  It accepts only shared source material
and persists through an injected repository seam.  No type in this module has a
member key, owner foreign key, or member-side join.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from typing import Iterable, Mapping, Protocol
from urllib.parse import urlsplit
from uuid import NAMESPACE_URL, uuid4, uuid5

from .connectors import ConnectorDescriptor, NormalizedListing, SourceReceiptInput
from .safe_outbound import SafeOutboundClient, SafeOutboundError


DATA_CLASSES = frozenset({"fixture", "production"})
LISTING_STATES = frozenset({"intake", "current", "changed", "closed", "unreachable", "stale", "quarantined", "invalid"})
LINK_STATES = frozenset({"valid", "invalid", "unknown"})
INVALID_LINK_REASONS = frozenset({"unresolvable", "soft_closed", "host_mismatch", "blocked"})
_TERMINAL_STATES = frozenset({"closed", "invalid"})
# This sequence, rather than an incidental set iteration order, is the one
# canonical representation persisted as ``allowed_actions_json`` in C2 SQL.
_POLICY_ACTION_ORDER = (
    "acquire", "ai", "cache", "display", "export",
    "persist", "register", "remove", "retain", "terminate",
)
_POLICY_ACTIONS = frozenset(_POLICY_ACTION_ORDER)
_POLICY_DIMENSIONS = frozenset({
    "display", "excerpt", "full_description", "storage", "ai_ml_use",
    "caching", "retention", "attribution", "removal", "termination", "exit",
    "survivable_minimal_facts",
})
_ACTION_DIMENSIONS: Mapping[str, frozenset[str]] = {
    "acquire": frozenset({"storage"}),
    "persist": frozenset({"storage"}),
    "display": frozenset({"display", "full_description", "attribution"}),
    "retain": frozenset({"retention"}),
    # Destruction authority is governed by the applicable removal decision.
    # Survivability controls the terminal purge shape; it never makes removal
    # unreachable.
    "remove": frozenset({"removal"}),
    "terminate": frozenset({"termination"}),
    "export": frozenset({"exit"}),
    "ai": frozenset({"ai_ml_use"}),
    "cache": frozenset({"caching"}),
}

# These are field names, not a provider-derived retention policy. A later
# provider/counsel decision may name an exact subset in a policy revision. C2
# defaults to the empty set and never expands it implicitly.
_RETAINABLE_SOURCE_FIELDS = frozenset({
    "receipt.source_id", "receipt.external_reference", "receipt.received_at",
    "receipt.content_type", "receipt.byte_count", "receipt.payload",
    "listing.source_id", "listing.external_reference", "listing.expected_application_hosts",
    "source_version.content_sha256", "source_version.observed_at",
    "source_version.employer", "source_version.title", "source_version.locations",
    "source_version.arrangement", "source_version.application_url",
    "source_version.description", "source_version.requirement_clauses",
    "source_version.fields", "requirement_version.clause_fingerprint",
    "requirement_item.ordinal", "requirement_item.normalized_clause",
    "field_attribution.field_name",
})


class MyOpportunitiesCanonicalError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _utc(value: datetime | None = None) -> datetime:
    value = value or datetime.now(timezone.utc)
    if value.tzinfo is None:
        raise MyOpportunitiesCanonicalError("invalid_time")
    return value.astimezone(timezone.utc)


def _key() -> str:
    return str(uuid4())


def _text(value: object) -> str:
    return " ".join(str(value).split()).strip()


def _normal_clause(value: str) -> str:
    return _text(value).casefold()


def _payload_hash(value: bytes) -> str:
    return sha256(value).hexdigest()


def _listing_content_hash(value: NormalizedListing) -> str:
    parts = (
        value.employer,
        value.title,
        "|".join(value.locations),
        value.arrangement or "",
        value.application_url,
        "|".join(_expected_hosts(value.expected_application_hosts)),
        value.description,
        "|".join(value.requirement_clauses),
        "|".join(f"{key}={item}" for key, item in sorted(value.fields.items())),
    )
    return sha256("\x1f".join(parts).encode("utf-8")).hexdigest()


def _expected_hosts(values: Iterable[str]) -> tuple[str, ...]:
    """Return the one deterministic host-set shape C2 persists and compares."""

    return tuple(sorted({_text(item).rstrip(".").casefold() for item in values if _text(item)}))


@dataclass(frozen=True)
class SourcePolicy:
    """Versioned source-policy decision. Missing/false is always a denial."""

    policy_key: str
    version: int
    source_id: str
    data_class: str
    actions: frozenset[str]
    source_priority: int
    effective_at: datetime
    expires_at: datetime | None
    dimensions: Mapping[str, bool]
    evidence_ref: str
    decision_ref: str
    source_class: str = "direct_employer"
    retained_source_fields: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        # A policy never derives a retainable field list from a connector or
        # provider. The only representable list is an explicit, immutable,
        # deterministic tuple carried by the policy revision itself.
        if isinstance(self.retained_source_fields, str):
            values = (self.retained_source_fields,)
        else:
            values = tuple(self.retained_source_fields)
        object.__setattr__(
            self,
            "retained_source_fields",
            tuple(sorted({_text(value) for value in values if _text(value)})),
        )

    def has_consistent_retained_field_allowlist(self) -> bool:
        """False survivability cannot carry source facts.

        A true survivability dimension with its default empty tuple still
        retains nothing. C2 never infers a provider allowlist.
        """

        return (
            set(self.retained_source_fields).issubset(_RETAINABLE_SOURCE_FIELDS)
            and (bool(self.dimensions.get("survivable_minimal_facts")) or not self.retained_source_fields)
        )

    @property
    def allowed_actions_json(self) -> str:
        """Serialize actions in the exact C2 database representation.

        This is deliberately separate from point-of-use authorization: the
        runtime continues to decide which operation is allowed. The storage
        representation only accepts the fixed C2 action vocabulary and cannot
        add an action that is not present on this immutable policy revision.
        """

        actions = frozenset(self.actions)
        if not actions.issubset(_POLICY_ACTIONS):
            raise MyOpportunitiesCanonicalError("invalid_policy_actions_json")
        return json.dumps(
            [action for action in _POLICY_ACTION_ORDER if action in actions],
            separators=(",", ":"),
            ensure_ascii=True,
        )

    @staticmethod
    def actions_from_allowed_actions_json(value: str) -> frozenset[str]:
        """Parse only the exact canonical action array persisted by C2 SQL."""

        try:
            decoded = json.loads(value)
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            raise MyOpportunitiesCanonicalError("invalid_policy_actions_json") from error
        if (
            not isinstance(decoded, list)
            or any(not isinstance(action, str) for action in decoded)
            or len(decoded) != len(set(decoded))
            or any(action not in _POLICY_ACTIONS for action in decoded)
        ):
            raise MyOpportunitiesCanonicalError("invalid_policy_actions_json")
        actions = frozenset(decoded)
        if value != json.dumps(
            [action for action in _POLICY_ACTION_ORDER if action in actions],
            separators=(",", ":"),
            ensure_ascii=True,
        ):
            raise MyOpportunitiesCanonicalError("invalid_policy_actions_json")
        return actions

    def allows(self, action: str, now: datetime) -> bool:
        if action not in _POLICY_ACTIONS or action not in self.actions:
            return False
        if not self.evidence_ref or not self.decision_ref or self.version < 1:
            return False
        if _utc(self.effective_at) > now or (self.expires_at is not None and _utc(self.expires_at) <= now):
            return False
        # Registration requires a complete affirmative policy and every action
        # C2 may later invoke. Point-of-use checks then use the narrow rights
        # required by that operation, so a removal-only revision can still
        # destroy retained content without reopening display or retention.
        required = _POLICY_DIMENSIONS if action == "register" else _ACTION_DIMENSIONS[action]
        return (action != "register" or _POLICY_ACTIONS.issubset(self.actions)) and all(
            self.dimensions.get(name) is True for name in required
        )


@dataclass(frozen=True)
class LiveOpportunityGateConfig:
    """Explicit gate windows. There are no hidden/default 'fresh' values."""

    freshness_window: timedelta
    link_validation_window: timedelta

    def __post_init__(self) -> None:
        if self.freshness_window <= timedelta(0) or self.link_validation_window <= timedelta(0):
            raise ValueError("Live Opportunity Gate windows must be explicitly positive.")


@dataclass(frozen=True)
class SourceReceipt:
    receipt_key: str
    source_id: str | None
    external_reference: str | None
    policy_key: str
    policy_version: int
    data_class: str
    received_at: datetime | None
    content_type: str | None
    byte_count: int | None
    payload_sha256: str | None
    payload: bytes | None
    content_withheld: bool = False
    created_at: datetime | None = None
    tombstone_policy_key: str | None = None
    tombstone_policy_version: int | None = None
    terminal_disposition: str | None = None
    terminal_actor: str | None = None
    retained_source_fields: tuple[str, ...] = ()


@dataclass(frozen=True)
class SourceVersion:
    version_key: str
    listing_key: str
    receipt_key: str
    data_class: str
    content_sha256: str | None
    observed_at: datetime | None
    employer: str | None
    title: str | None
    locations: tuple[str, ...] | None
    arrangement: str | None
    application_url: str | None
    description: str | None
    requirement_clauses: tuple[str, ...] | None
    fields: Mapping[str, str] | None
    content_withheld: bool = False
    created_at: datetime | None = None
    tombstone_policy_key: str | None = None
    tombstone_policy_version: int | None = None
    terminal_disposition: str | None = None
    terminal_actor: str | None = None
    retained_source_fields: tuple[str, ...] = ()


@dataclass(frozen=True)
class SourceListing:
    listing_key: str
    source_id: str | None
    external_reference: str | None
    policy_key: str
    policy_version: int
    data_class: str
    canonical_opportunity_key: str
    current_version_key: str
    state: str
    link_state: str
    link_invalid_reason: str | None
    link_last_attempted_at: datetime | None
    link_last_validated_at: datetime | None
    last_attempted_at: datetime | None
    last_successfully_verified_at: datetime | None
    link_review_pending: bool
    expected_application_hosts: tuple[str, ...]
    content_withheld: bool = False
    tombstone_policy_key: str | None = None
    tombstone_policy_version: int | None = None
    terminal_disposition: str | None = None
    terminal_actor: str | None = None
    retained_source_fields: tuple[str, ...] = ()


@dataclass(frozen=True)
class RequirementItem:
    requirement_item_key: str
    data_class: str
    normalized_clause: str | None
    ordinal: int | None
    content_withheld: bool = False


@dataclass(frozen=True)
class RequirementVersion:
    requirement_version_key: str
    opportunity_key: str
    source_version_key: str
    data_class: str
    clause_fingerprint: str | None
    items: tuple[RequirementItem, ...]
    derived_at: datetime
    content_withheld: bool = False


@dataclass(frozen=True)
class CanonicalOpportunity:
    opportunity_key: str
    data_class: str
    listing_keys: frozenset[str]
    governing_listing_key: str | None
    governing_source_version_key: str | None
    requirement_version_key: str | None
    field_attribution: Mapping[str, tuple[str, str]]
    tombstone_target_key: str | None = None


@dataclass(frozen=True)
class CanonicalEvent:
    event_key: str
    opportunity_key: str
    data_class: str
    kind: str
    at: datetime
    detail: Mapping[str, str]


@dataclass(frozen=True)
class ContentTombstone:
    tombstone_key: str
    receipt_key: str
    source_version_key: str
    data_class: str
    policy_key: str
    policy_version: int
    disposition: str
    reason: str
    actor: str
    retained_source_fields: tuple[str, ...]
    actioned_at: datetime


@dataclass(frozen=True)
class GateDecision:
    passes: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class LinkValidationOutcome:
    state: str
    reason: str | None
    outage: bool


class CanonicalRepository(Protocol):
    def policy_for(self, key: str, version: int, data_class: str | None = None) -> SourcePolicy | None: ...
    def policy_versions(self, key: str, data_class: str | None = None) -> tuple[SourcePolicy, ...]: ...
    def save_policy(self, policy: SourcePolicy) -> None: ...
    def receipt(self, key: str) -> SourceReceipt | None: ...
    def save_receipt(self, receipt: SourceReceipt) -> None: ...
    def listing(self, key: str) -> SourceListing | None: ...
    def listing_for_source_reference(self, data_class: str, source_id: str, external_reference: str) -> SourceListing | None: ...
    def save_listing(self, listing: SourceListing) -> None: ...
    def version(self, key: str) -> SourceVersion | None: ...
    def save_version(self, version: SourceVersion) -> None: ...
    def versions_for_listing(self, listing_key: str) -> tuple[SourceVersion, ...]: ...
    def link_receipt_to_version(self, receipt_key: str, source_version_key: str) -> None: ...
    def receipt_keys_for_version(self, source_version_key: str) -> tuple[str, ...]: ...
    def opportunity(self, key: str) -> CanonicalOpportunity | None: ...
    def save_opportunity(self, opportunity: CanonicalOpportunity) -> None: ...
    def opportunities(self, data_class: str) -> tuple[CanonicalOpportunity, ...]: ...
    def save_requirement_version(self, version: RequirementVersion) -> None: ...
    def requirement_version(self, key: str) -> RequirementVersion | None: ...
    def requirement_versions_for(self, opportunity_key: str) -> tuple[RequirementVersion, ...]: ...
    def requirement_versions_for_source_version(self, source_version_key: str) -> tuple[RequirementVersion, ...]: ...
    def save_event(self, event: CanonicalEvent) -> None: ...
    def tombstone_listing_content(
        self, listing_key: str, *, policy: SourcePolicy, disposition: str,
        reason: str, actor: str, retained_source_fields: tuple[str, ...], now: datetime,
    ) -> SourceListing: ...


class InMemoryCanonicalRepository:
    """Fixture/test repository with append-only source histories.

    This is deliberately the only included runtime repository. It makes C2
    P-1 proof independent of a database and prevents accidental shared-service
    wiring before the later SQL adapter has its own claimed surface.
    """

    def __init__(self) -> None:
        self._policies: dict[tuple[str, str, int], SourcePolicy] = {}
        self._receipts: dict[str, SourceReceipt] = {}
        self._listings: dict[str, SourceListing] = {}
        self._listing_refs: dict[tuple[str, str, str], str] = {}
        self._versions: dict[str, SourceVersion] = {}
        self._versions_by_listing: dict[str, list[str]] = {}
        self._receipt_version_links: dict[str, str] = {}
        self._receipt_keys_by_version: dict[str, set[str]] = {}
        self._opportunities: dict[str, CanonicalOpportunity] = {}
        self._requirement_versions: dict[str, RequirementVersion] = {}
        self._requirements_by_opportunity: dict[str, list[str]] = {}
        self._requirements_by_source_version: dict[str, list[str]] = {}
        self.events: list[CanonicalEvent] = []
        self.content_tombstones: list[ContentTombstone] = []

    def policy_for(self, key: str, version: int, data_class: str | None = None) -> SourcePolicy | None:
        if data_class is not None:
            return self._policies.get((data_class, key, version))
        values = tuple(
            item for (item_data_class, policy_key, policy_version), item in self._policies.items()
            if policy_key == key and policy_version == version
        )
        return values[0] if len(values) == 1 else None

    def policy_versions(self, key: str, data_class: str | None = None) -> tuple[SourcePolicy, ...]:
        return tuple(
            item for (item_data_class, policy_key, _version), item in self._policies.items()
            if policy_key == key and (data_class is None or item_data_class == data_class)
        )

    def save_policy(self, policy: SourcePolicy) -> None:
        existing = self._policies.get((policy.data_class, policy.policy_key, policy.version))
        if existing is not None and existing != policy:
            raise MyOpportunitiesCanonicalError("immutable_policy")
        self._policies[(policy.data_class, policy.policy_key, policy.version)] = policy

    def receipt(self, key: str) -> SourceReceipt | None:
        return self._receipts.get(key)

    def save_receipt(self, receipt: SourceReceipt) -> None:
        if receipt.receipt_key in self._receipts:
            raise MyOpportunitiesCanonicalError("immutable_receipt")
        policy = self.policy_for(receipt.policy_key, receipt.policy_version, receipt.data_class)
        if (
            policy is None
            or policy.data_class != receipt.data_class
            or policy.source_id != receipt.source_id
            or not receipt.external_reference
        ):
            raise MyOpportunitiesCanonicalError("class_mismatch")
        self._receipts[receipt.receipt_key] = receipt

    def listing(self, key: str) -> SourceListing | None:
        return self._listings.get(key)

    def listing_for_source_reference(self, data_class: str, source_id: str, external_reference: str) -> SourceListing | None:
        key = self._listing_refs.get((data_class, source_id, external_reference))
        return None if key is None else self._listings[key]

    def save_listing(self, listing: SourceListing) -> None:
        existing = self._listings.get(listing.listing_key)
        if existing is not None and existing.content_withheld:
            raise MyOpportunitiesCanonicalError("immutable_tombstone")
        policy = self.policy_for(listing.policy_key, listing.policy_version, listing.data_class)
        opportunity = self.opportunity(listing.canonical_opportunity_key)
        if (
            policy is None
            or opportunity is None
            or policy.data_class != listing.data_class
            or policy.source_id != listing.source_id
            or opportunity.data_class != listing.data_class
            or not listing.external_reference
        ):
            raise MyOpportunitiesCanonicalError("class_mismatch")
        self._listings[listing.listing_key] = listing
        self._listing_refs[(listing.data_class, listing.source_id, listing.external_reference)] = listing.listing_key

    def version(self, key: str) -> SourceVersion | None:
        return self._versions.get(key)

    def save_version(self, version: SourceVersion) -> None:
        if version.version_key in self._versions:
            raise MyOpportunitiesCanonicalError("immutable_source_version")
        listing = self.listing(version.listing_key)
        receipt = self.receipt(version.receipt_key)
        if (
            listing is None
            or receipt is None
            or listing.data_class != version.data_class
            or receipt.data_class != version.data_class
            or listing.source_id != receipt.source_id
            or listing.external_reference != receipt.external_reference
            or listing.content_withheld
        ):
            raise MyOpportunitiesCanonicalError("class_mismatch")
        self._versions[version.version_key] = version
        self._versions_by_listing.setdefault(version.listing_key, []).append(version.version_key)

    def versions_for_listing(self, listing_key: str) -> tuple[SourceVersion, ...]:
        return tuple(self._versions[key] for key in self._versions_by_listing.get(listing_key, []))

    def link_receipt_to_version(self, receipt_key: str, source_version_key: str) -> None:
        receipt = self.receipt(receipt_key)
        version = self.version(source_version_key)
        if (
            receipt is None
            or version is None
            or receipt.data_class != version.data_class
            or receipt.content_withheld
            or version.content_withheld
            or (receipt_key in self._receipt_version_links and self._receipt_version_links[receipt_key] != source_version_key)
        ):
            raise MyOpportunitiesCanonicalError("unpaired_receipt")
        listing = self.listing(version.listing_key)
        if (
            listing is None
            or listing.data_class != receipt.data_class
            or listing.source_id != receipt.source_id
            or listing.external_reference != receipt.external_reference
        ):
            raise MyOpportunitiesCanonicalError("class_mismatch")
        self._receipt_version_links[receipt_key] = source_version_key
        self._receipt_keys_by_version.setdefault(source_version_key, set()).add(receipt_key)

    def receipt_keys_for_version(self, source_version_key: str) -> tuple[str, ...]:
        return tuple(sorted(self._receipt_keys_by_version.get(source_version_key, set())))

    def opportunity(self, key: str) -> CanonicalOpportunity | None:
        return self._opportunities.get(key)

    def save_opportunity(self, opportunity: CanonicalOpportunity) -> None:
        existing = self._opportunities.get(opportunity.opportunity_key)
        if existing is not None and existing.data_class != opportunity.data_class:
            raise MyOpportunitiesCanonicalError("class_mismatch")
        for listing_key in opportunity.listing_keys:
            listing = self.listing(listing_key)
            if listing is None or listing.data_class != opportunity.data_class:
                raise MyOpportunitiesCanonicalError("class_mismatch")
        for related_key in (opportunity.governing_listing_key, opportunity.governing_source_version_key):
            if related_key is None:
                continue
            related = self.listing(related_key) if related_key == opportunity.governing_listing_key else self.version(related_key)
            if related is None or related.data_class != opportunity.data_class:
                raise MyOpportunitiesCanonicalError("class_mismatch")
        if opportunity.requirement_version_key is not None:
            requirement = self.requirement_version(opportunity.requirement_version_key)
            if requirement is None or requirement.data_class != opportunity.data_class:
                raise MyOpportunitiesCanonicalError("class_mismatch")
        for listing_key, version_key in opportunity.field_attribution.values():
            listing = self.listing(listing_key)
            version = self.version(version_key)
            if (
                listing is None
                or version is None
                or listing.data_class != opportunity.data_class
                or version.data_class != opportunity.data_class
            ):
                raise MyOpportunitiesCanonicalError("class_mismatch")
        self._opportunities[opportunity.opportunity_key] = opportunity

    def opportunities(self, data_class: str) -> tuple[CanonicalOpportunity, ...]:
        return tuple(item for item in self._opportunities.values() if item.data_class == data_class)

    def save_requirement_version(self, version: RequirementVersion) -> None:
        if version.requirement_version_key in self._requirement_versions:
            raise MyOpportunitiesCanonicalError("immutable_requirement_version")
        opportunity = self.opportunity(version.opportunity_key)
        source_version = self.version(version.source_version_key)
        if (
            opportunity is None
            or source_version is None
            or opportunity.data_class != version.data_class
            or source_version.data_class != version.data_class
            or any(item.data_class != version.data_class for item in version.items)
        ):
            raise MyOpportunitiesCanonicalError("class_mismatch")
        self._requirement_versions[version.requirement_version_key] = version
        self._requirements_by_opportunity.setdefault(version.opportunity_key, []).append(version.requirement_version_key)
        self._requirements_by_source_version.setdefault(version.source_version_key, []).append(version.requirement_version_key)

    def requirement_version(self, key: str) -> RequirementVersion | None:
        return self._requirement_versions.get(key)

    def requirement_versions_for(self, opportunity_key: str) -> tuple[RequirementVersion, ...]:
        return tuple(self._requirement_versions[key] for key in self._requirements_by_opportunity.get(opportunity_key, []))

    def requirement_versions_for_source_version(self, source_version_key: str) -> tuple[RequirementVersion, ...]:
        return tuple(
            self._requirement_versions[key]
            for key in self._requirements_by_source_version.get(source_version_key, [])
        )

    def save_event(self, event: CanonicalEvent) -> None:
        opportunity = self.opportunity(event.opportunity_key)
        if opportunity is None or opportunity.data_class != event.data_class:
            raise MyOpportunitiesCanonicalError("class_mismatch")
        self.events.append(event)

    def tombstone_listing_content(
        self, listing_key: str, *, policy: SourcePolicy, disposition: str,
        reason: str, actor: str, retained_source_fields: tuple[str, ...], now: datetime,
    ) -> SourceListing:
        """Validate the full aggregate, then make its one terminal mutation.

        All validation happens before assignments to the backing maps. This is
        the in-memory equivalent of a single SQL transaction: a corrupt link,
        class mismatch, missing receipt, or second attempt leaves every body
        and relationship untouched.
        """

        listing = self.listing(listing_key)
        recorded_policy = self.policy_for(policy.policy_key, policy.version, policy.data_class)
        if (
            listing is None
            or listing.content_withheld
            or recorded_policy != policy
            or policy.data_class != listing.data_class
            or policy.policy_key != listing.policy_key
            or policy.source_id != listing.source_id
            or disposition not in {"removal", "termination"}
            or not reason
            or not actor
            or retained_source_fields != policy.retained_source_fields
            or tuple(sorted(set(retained_source_fields))) != retained_source_fields
            or not set(retained_source_fields).issubset(_RETAINABLE_SOURCE_FIELDS)
        ):
            raise MyOpportunitiesCanonicalError("invalid_tombstone")

        versions = self.versions_for_listing(listing_key)
        opportunity = self.opportunity(listing.canonical_opportunity_key)
        if opportunity is None or opportunity.data_class != listing.data_class:
            raise MyOpportunitiesCanonicalError("class_mismatch")
        if not versions:
            raise MyOpportunitiesCanonicalError("unpaired_receipt")
        receipt_keys = {
            key for key, receipt in self._receipts.items()
            if receipt.data_class == listing.data_class
            and receipt.source_id == listing.source_id
            and receipt.external_reference == listing.external_reference
        }
        linked_receipt_keys: set[str] = set()
        requirements: list[RequirementVersion] = []
        for version in versions:
            linked = set(self.receipt_keys_for_version(version.version_key))
            if (
                version.content_withheld
                or version.data_class != listing.data_class
                or version.receipt_key not in linked
                or not linked
            ):
                raise MyOpportunitiesCanonicalError("unpaired_receipt")
            for receipt_key in linked:
                receipt = self.receipt(receipt_key)
                if (
                    receipt is None
                    or receipt.content_withheld
                    or receipt.data_class != listing.data_class
                    or receipt.source_id != listing.source_id
                    or receipt.external_reference != listing.external_reference
                    or self._receipt_version_links.get(receipt_key) != version.version_key
                ):
                    raise MyOpportunitiesCanonicalError("unpaired_receipt")
            linked_receipt_keys.update(linked)
            derived = self.requirement_versions_for_source_version(version.version_key)
            if any(
                requirement.content_withheld
                or requirement.data_class != listing.data_class
                or any(item.data_class != listing.data_class or item.content_withheld for item in requirement.items)
                for requirement in derived
            ):
                raise MyOpportunitiesCanonicalError("class_mismatch")
            requirements.extend(derived)
        if receipt_keys != linked_receipt_keys:
            # An observation body cannot survive as a same-reference orphan.
            raise MyOpportunitiesCanonicalError("unpaired_receipt")
        for attributed_listing_key, attributed_version_key in opportunity.field_attribution.values():
            attributed_listing = self.listing(attributed_listing_key)
            attributed_version = self.version(attributed_version_key)
            if (
                attributed_listing is None
                or attributed_version is None
                or attributed_listing.data_class != listing.data_class
                or attributed_version.data_class != listing.data_class
            ):
                raise MyOpportunitiesCanonicalError("class_mismatch")

        allowed = frozenset(retained_source_fields)

        def keep(field: str, value: object, empty: object) -> object:
            return value if field in allowed else empty

        # From this point forward there are no failure-prone validations or
        # calls. The replacements form the aggregate's single terminal state.
        for receipt_key in sorted(linked_receipt_keys):
            receipt = self._receipts[receipt_key]
            self._receipts[receipt_key] = replace(
                receipt,
                source_id=keep("receipt.source_id", receipt.source_id, None),
                external_reference=keep("receipt.external_reference", receipt.external_reference, None),
                received_at=keep("receipt.received_at", receipt.received_at, None),
                content_type=keep("receipt.content_type", receipt.content_type, None),
                byte_count=keep("receipt.byte_count", receipt.byte_count, None),
                payload_sha256=keep("receipt.payload", receipt.payload_sha256, None),
                payload=keep("receipt.payload", receipt.payload, None),
                content_withheld=True,
                tombstone_policy_key=policy.policy_key,
                tombstone_policy_version=policy.version,
                terminal_disposition=disposition,
                terminal_actor=actor,
                retained_source_fields=retained_source_fields,
            )
        for version in versions:
            self._versions[version.version_key] = replace(
                version,
                content_sha256=keep("source_version.content_sha256", version.content_sha256, None),
                observed_at=keep("source_version.observed_at", version.observed_at, None),
                employer=keep("source_version.employer", version.employer, None),
                title=keep("source_version.title", version.title, None),
                locations=keep("source_version.locations", version.locations, None),
                arrangement=keep("source_version.arrangement", version.arrangement, None),
                application_url=keep("source_version.application_url", version.application_url, None),
                description=keep("source_version.description", version.description, None),
                requirement_clauses=keep("source_version.requirement_clauses", version.requirement_clauses, None),
                fields=keep("source_version.fields", version.fields, {}),
                content_withheld=True,
                tombstone_policy_key=policy.policy_key,
                tombstone_policy_version=policy.version,
                terminal_disposition=disposition,
                terminal_actor=actor,
                retained_source_fields=retained_source_fields,
            )
        for requirement in requirements:
            items = tuple(
                replace(
                    item,
                    normalized_clause=keep("requirement_item.normalized_clause", item.normalized_clause, None),
                    ordinal=keep("requirement_item.ordinal", item.ordinal, None),
                    content_withheld=True,
                )
                for item in requirement.items
            )
            self._requirement_versions[requirement.requirement_version_key] = replace(
                requirement,
                clause_fingerprint=keep("requirement_version.clause_fingerprint", requirement.clause_fingerprint, None),
                items=items,
                content_withheld=True,
            )
        self._listing_refs.pop((listing.data_class, listing.source_id, listing.external_reference), None)
        terminal_listing = replace(
            listing,
            source_id=keep("listing.source_id", listing.source_id, None),
            external_reference=keep("listing.external_reference", listing.external_reference, None),
            expected_application_hosts=keep("listing.expected_application_hosts", listing.expected_application_hosts, ()),
            state="closed" if disposition == "removal" else "invalid",
            link_state="unknown",
            link_invalid_reason=None,
            link_last_attempted_at=None,
            link_last_validated_at=None,
            last_attempted_at=None,
            last_successfully_verified_at=None,
            link_review_pending=False,
            content_withheld=True,
            tombstone_policy_key=policy.policy_key,
            tombstone_policy_version=policy.version,
            terminal_disposition=disposition,
            terminal_actor=actor,
            retained_source_fields=retained_source_fields,
        )
        self._listings[listing_key] = terminal_listing
        affected_version_keys = {version.version_key for version in versions}
        self._opportunities[opportunity.opportunity_key] = replace(
            opportunity,
            governing_listing_key=(
                None if opportunity.governing_listing_key == listing_key else opportunity.governing_listing_key
            ),
            governing_source_version_key=(
                None if opportunity.governing_source_version_key in affected_version_keys
                else opportunity.governing_source_version_key
            ),
            requirement_version_key=(
                None
                if opportunity.requirement_version_key in {item.requirement_version_key for item in requirements}
                else opportunity.requirement_version_key
            ),
            field_attribution={
                field_name: attribution
                for field_name, attribution in opportunity.field_attribution.items()
                if attribution[0] != listing_key and attribution[1] not in affected_version_keys
            },
        )
        for version in versions:
            for receipt_key in self.receipt_keys_for_version(version.version_key):
                self.content_tombstones.append(
                    ContentTombstone(
                        _key(), receipt_key, version.version_key, listing.data_class,
                        policy.policy_key, policy.version, disposition, reason, actor,
                        retained_source_fields, now,
                    )
                )
        return terminal_listing


class CanonicalService:
    def __init__(self, repository: CanonicalRepository, gate: LiveOpportunityGateConfig) -> None:
        self._repository = repository
        self._gate = gate
        self._descriptors: dict[tuple[str, str], ConnectorDescriptor] = {}

    def register_policy(self, policy: SourcePolicy, *, now: datetime) -> None:
        now = _utc(now)
        if (
            policy.data_class not in DATA_CLASSES
            or policy.source_priority < 0
            or not policy.has_consistent_retained_field_allowlist()
        ):
            raise MyOpportunitiesCanonicalError("invalid_policy")
        if not policy.allows("register", now):
            raise MyOpportunitiesCanonicalError("policy_denied")
        self._repository.save_policy(policy)

    def revise_policy(self, policy: SourcePolicy, *, now: datetime) -> None:
        """Publish a restrictive source-policy revision without reopening intake.

        Initial registration remains deliberately stricter: it requires all
        affirmative C2 actions and dimensions. A later removal/termination
        revision must instead be reachable even when it has withdrawn those
        affirmative rights, provided it preserves source/class identity and
        can only narrow the prior decision.
        """

        now = _utc(now)
        try:
            prior = self._current_policy(policy.policy_key, policy.data_class)
        except MyOpportunitiesCanonicalError as error:
            raise MyOpportunitiesCanonicalError("invalid_policy_revision") from error
        if (
            policy.version != prior.version + 1
            or policy.source_id != prior.source_id
            or policy.data_class != prior.data_class
            or policy.source_class != prior.source_class
            or policy.source_priority != prior.source_priority
            or policy.data_class not in DATA_CLASSES
            or not policy.evidence_ref
            or not policy.decision_ref
            or not policy.has_consistent_retained_field_allowlist()
            or not policy.actions.issubset(prior.actions)
            or any(
                policy.dimensions.get(name) is True and prior.dimensions.get(name) is not True
                for name in _POLICY_DIMENSIONS
            )
            or not set(policy.retained_source_fields).issubset(prior.retained_source_fields)
        ):
            raise MyOpportunitiesCanonicalError("invalid_policy_revision")
        # A revision is meaningful only when it actually narrows an action,
        # dimension, or explicit allowlist. It cannot be a duplicate rewrite.
        if (
            policy.actions == prior.actions
            and all(policy.dimensions.get(name) is prior.dimensions.get(name) for name in _POLICY_DIMENSIONS)
            and policy.retained_source_fields == prior.retained_source_fields
        ):
            raise MyOpportunitiesCanonicalError("invalid_policy_revision")
        self._repository.save_policy(policy)

    def register_connector(self, descriptor: ConnectorDescriptor, *, now: datetime) -> None:
        now = _utc(now)
        if descriptor.data_class not in DATA_CLASSES or not descriptor.source_id:
            raise MyOpportunitiesCanonicalError("invalid_connector")
        policy = self._policy(descriptor.policy_key, descriptor.policy_version, descriptor.data_class)
        if (
            policy.source_id != descriptor.source_id
            or policy.source_class != descriptor.source_class
            or policy.data_class != descriptor.data_class
            or not policy.allows("register", now)
        ):
            raise MyOpportunitiesCanonicalError("policy_denied")
        self._descriptors[(descriptor.data_class, descriptor.source_id)] = descriptor

    def record_receipt(self, descriptor: ConnectorDescriptor, receipt: SourceReceiptInput, *, now: datetime) -> SourceReceipt:
        now = _utc(now)
        self._registered_descriptor(descriptor)
        policy = self._policy_for_descriptor_at_use(descriptor)
        if not policy.allows("acquire", now) or not policy.allows("persist", now):
            raise MyOpportunitiesCanonicalError("policy_denied")
        if not isinstance(receipt.payload, bytes) or not receipt.payload or len(receipt.payload) > 5 * 1024 * 1024:
            raise MyOpportunitiesCanonicalError("invalid_receipt")
        item = SourceReceipt(
            receipt_key=_key(), source_id=descriptor.source_id, external_reference=_text(receipt.external_reference), policy_key=policy.policy_key,
            policy_version=policy.version, data_class=descriptor.data_class, received_at=_utc(receipt.received_at),
            content_type=_text(receipt.content_type).lower(), byte_count=len(receipt.payload),
            payload_sha256=_payload_hash(receipt.payload), payload=bytes(receipt.payload), created_at=now,
        )
        # Receipt bodies become retained history only in the atomic admission
        # path below. Returning this immutable candidate lets a caller
        # validate class/reference/terminal state before any body can orphan.
        return item

    def admit_observation(
        self, descriptor: ConnectorDescriptor, receipt_input: SourceReceiptInput,
        candidate: NormalizedListing, *, now: datetime,
    ) -> SourceListing:
        """Atomically turn one normalized observation into receipt+version truth."""

        receipt = self.record_receipt(descriptor, receipt_input, now=now)
        return self.admit(descriptor, receipt, candidate, now=now)

    def admit(self, descriptor: ConnectorDescriptor, receipt: SourceReceipt, candidate: NormalizedListing, *, now: datetime) -> SourceListing:
        now = _utc(now)
        self._registered_descriptor(descriptor)
        policy = self._policy_for_descriptor_at_use(descriptor)
        if (
            not policy.allows("persist", now)
            or receipt.source_id != descriptor.source_id
            or receipt.policy_key != descriptor.policy_key
            or receipt.data_class != candidate.data_class
            or candidate.data_class != descriptor.data_class
            or receipt.external_reference != candidate.external_reference
        ):
            raise MyOpportunitiesCanonicalError("policy_denied")
        self._validate_candidate(candidate)
        prior = self._repository.listing_for_source_reference(
            candidate.data_class, descriptor.source_id, candidate.external_reference
        )
        if prior is not None and prior.state in _TERMINAL_STATES:
            # There is no C2 correction/reopening model. A new observation
            # must never revive a closed or invalid source identity.
            raise MyOpportunitiesCanonicalError("terminal_listing")
        source_version = SourceVersion(
            version_key=_key(), listing_key=prior.listing_key if prior else _key(), receipt_key=receipt.receipt_key,
            data_class=candidate.data_class, content_sha256=_listing_content_hash(candidate), observed_at=now, employer=_text(candidate.employer),
            title=_text(candidate.title), locations=tuple(_text(item) for item in candidate.locations),
            arrangement=_text(candidate.arrangement) if candidate.arrangement else None,
            application_url=candidate.application_url, description=candidate.description,
            requirement_clauses=tuple(_text(item) for item in candidate.requirement_clauses), fields=dict(candidate.fields), created_at=now,
        )
        if prior is not None:
            current = self._require_version(prior.current_version_key)
            if current.content_sha256 == source_version.content_sha256:
                self._persist_receipt(receipt)
                self._repository.link_receipt_to_version(receipt.receipt_key, current.version_key)
                return prior
            source_version = replace(source_version, listing_key=prior.listing_key)
            self._persist_receipt(receipt)
            self._repository.save_version(source_version)
            self._repository.link_receipt_to_version(receipt.receipt_key, source_version.version_key)
            expected_hosts = _expected_hosts(candidate.expected_application_hosts)
            application_target_changed = (
                current.application_url != source_version.application_url
                or prior.expected_application_hosts != expected_hosts
            )
            non_target_material_changed = (
                current.employer != source_version.employer
                or current.title != source_version.title
                or current.locations != source_version.locations
                or current.arrangement != source_version.arrangement
                or current.description != source_version.description
                or current.requirement_clauses != source_version.requirement_clauses
                or dict(current.fields or {}) != dict(source_version.fields or {})
            )
            listing = replace(
                prior,
                current_version_key=source_version.version_key,
                # An allowed ATS/application-target migration alone is not a
                # lifecycle conclusion. A compound observation still enters
                # the explicit changed/re-admission workflow.
                state=prior.state if application_target_changed and not non_target_material_changed else "changed",
                expected_application_hosts=expected_hosts,
                link_state="unknown" if application_target_changed else prior.link_state,
                link_invalid_reason=None if application_target_changed else prior.link_invalid_reason,
                link_last_attempted_at=None if application_target_changed else prior.link_last_attempted_at,
                link_last_validated_at=None if application_target_changed else prior.link_last_validated_at,
            )
            self._repository.save_listing(listing)
            self._emit(listing.canonical_opportunity_key, "listing_changed", now, {"listing_key": listing.listing_key})
            return listing

        listing_key = source_version.listing_key
        opportunity, pending = self._match_or_create(candidate, listing_key)
        listing = SourceListing(
            listing_key=listing_key, source_id=descriptor.source_id, external_reference=candidate.external_reference,
            policy_key=policy.policy_key, policy_version=policy.version, data_class=candidate.data_class,
            canonical_opportunity_key=opportunity.opportunity_key, current_version_key=source_version.version_key,
            state="current", link_state="unknown", link_invalid_reason=None, link_last_attempted_at=None,
            link_last_validated_at=None, last_attempted_at=now, last_successfully_verified_at=now,
            link_review_pending=pending, expected_application_hosts=_expected_hosts(candidate.expected_application_hosts),
        )
        self._persist_receipt(receipt)
        self._repository.save_listing(listing)
        self._repository.save_version(source_version)
        self._repository.link_receipt_to_version(receipt.receipt_key, source_version.version_key)
        self._repository.save_opportunity(replace(opportunity, listing_keys=frozenset(set(opportunity.listing_keys) | {listing_key})))
        self._refresh_opportunity(opportunity.opportunity_key, now, "listing_admitted")
        return listing

    def complete_reverification(self, listing_key: str, *, content_changed: bool, now: datetime) -> SourceListing:
        listing = self._require_listing(listing_key)
        now = _utc(now)
        self._require_policy_action(listing, "persist", now)
        if listing.state in _TERMINAL_STATES:
            raise MyOpportunitiesCanonicalError("terminal_listing")
        state = "changed" if content_changed else "current"
        updated = replace(listing, state=state, last_attempted_at=now, last_successfully_verified_at=now)
        self._repository.save_listing(updated)
        self._refresh_opportunity(updated.canonical_opportunity_key, now, "reverified")
        return updated

    def re_admit_changed_listing(self, listing_key: str, *, now: datetime) -> SourceListing:
        listing = self._require_listing(listing_key)
        now = _utc(now)
        self._require_policy_action(listing, "persist", now)
        if listing.state != "changed":
            raise MyOpportunitiesCanonicalError("invalid_transition")
        updated = replace(listing, state="current", last_attempted_at=now, last_successfully_verified_at=now)
        self._repository.save_listing(updated)
        self._refresh_opportunity(updated.canonical_opportunity_key, now, "changed_readmitted")
        return updated

    def record_outage(self, listing_key: str, *, now: datetime) -> SourceListing:
        listing = self._require_listing(listing_key)
        now = _utc(now)
        self._require_policy_action(listing, "persist", now)
        if listing.state not in {"current", "changed", "unreachable", "stale"}:
            raise MyOpportunitiesCanonicalError("invalid_transition")
        updated = replace(listing, state="unreachable", last_attempted_at=now)
        self._repository.save_listing(updated)
        self._refresh_opportunity(updated.canonical_opportunity_key, now, "outage")
        return updated

    def mark_stale(self, listing_key: str, *, now: datetime) -> SourceListing:
        listing = self._require_listing(listing_key)
        now = _utc(now)
        self._require_policy_action(listing, "persist", now)
        if listing.state not in {"current", "unreachable", "changed"}:
            raise MyOpportunitiesCanonicalError("invalid_transition")
        updated = replace(listing, state="stale")
        self._repository.save_listing(updated)
        self._refresh_opportunity(updated.canonical_opportunity_key, now, "stale")
        return updated

    def confirm_closed(self, listing_key: str, *, now: datetime) -> SourceListing:
        listing = self._require_listing(listing_key)
        now = _utc(now)
        self._require_policy_action(listing, "persist", now)
        if listing.state in _TERMINAL_STATES:
            raise MyOpportunitiesCanonicalError("invalid_transition")
        updated = replace(listing, state="closed")
        self._repository.save_listing(updated)
        self._refresh_opportunity(updated.canonical_opportunity_key, now, "closed")
        return updated

    def validate_application_link(self, listing_key: str, client: SafeOutboundClient, *, now: datetime) -> LinkValidationOutcome:
        listing = self._require_listing(listing_key)
        now = _utc(now)
        if listing.state in _TERMINAL_STATES:
            # Link state is separate from source lifecycle. C2 has no
            # terminal-probe or terminal-reopening path.
            raise MyOpportunitiesCanonicalError("terminal_listing")
        self._require_policy_action(listing, "acquire", now)
        self._require_policy_action(listing, "persist", now)
        version = self._require_version(listing.current_version_key)
        attempted = replace(listing, link_last_attempted_at=now)
        try:
            result = client.fetch(version.application_url)
        except SafeOutboundError as error:
            if error.code in {"timeout", "outage", "transport_disabled"}:
                # An unavailable probe changes only link facts. In particular,
                # a disabled injected transport is not evidence that an
                # employer blocked or closed the listing.
                unavailable_listing = replace(
                    attempted, link_state="unknown", link_invalid_reason=None
                )
                self._repository.save_listing(unavailable_listing)
                return LinkValidationOutcome(state="unknown", reason=error.code, outage=True)
            reason = "unresolvable" if error.code == "dns_unavailable" else "blocked"
            updated = replace(attempted, link_state="invalid", link_invalid_reason=reason)
            self._repository.save_listing(updated)
            return LinkValidationOutcome(state="invalid", reason=reason, outage=False)
        host_ok = not listing.expected_application_hosts or result.final_hostname in listing.expected_application_hosts
        if result.status in {404, 410}:
            reason = "soft_closed"
        elif not host_ok:
            reason = "host_mismatch"
        elif not 200 <= result.status < 400:
            reason = "blocked"
        else:
            updated = replace(attempted, link_state="valid", link_invalid_reason=None, link_last_validated_at=now)
            self._repository.save_listing(updated)
            return LinkValidationOutcome(state="valid", reason=None, outage=False)
        updated = replace(attempted, link_state="invalid", link_invalid_reason=reason)
        self._repository.save_listing(updated)
        return LinkValidationOutcome(state="invalid", reason=reason, outage=False)

    def live_gate(self, listing_key: str, *, now: datetime) -> GateDecision:
        listing = self._require_listing(listing_key)
        now = _utc(now)
        version = self._require_version(listing.current_version_key)
        try:
            policy_display_allowed = self._policy_at_use(listing).allows("display", now)
        except MyOpportunitiesCanonicalError:
            policy_display_allowed = False
        reasons: list[str] = []
        if not (version.employer and version.title and version.application_url): reasons.append("identity_incomplete")
        if not policy_display_allowed: reasons.append("policy_denied")
        if listing.state != "current": reasons.append(f"listing_{listing.state}")
        if listing.last_successfully_verified_at is None or now - listing.last_successfully_verified_at > self._gate.freshness_window: reasons.append("stale_verification")
        if listing.link_review_pending: reasons.append("dedupe_pending")
        if listing.link_state != "valid" or listing.link_last_validated_at is None or now - listing.link_last_validated_at > self._gate.link_validation_window: reasons.append("application_link_invalid")
        return GateDecision(passes=not reasons, reasons=tuple(reasons))

    def canonical_gate(self, opportunity_key: str, *, now: datetime) -> GateDecision:
        opportunity = self.resolve_opportunity(opportunity_key)
        decisions = [self.live_gate(key, now=now) for key in opportunity.listing_keys]
        if any(item.passes for item in decisions):
            return GateDecision(True, ())
        return GateDecision(False, tuple(sorted({reason for item in decisions for reason in item.reasons})))

    def merge(self, survivor_key: str, loser_key: str, *, now: datetime) -> CanonicalOpportunity:
        survivor = self.resolve_opportunity(survivor_key)
        loser = self.resolve_opportunity(loser_key)
        if survivor.opportunity_key == loser.opportunity_key or survivor.data_class != loser.data_class:
            raise MyOpportunitiesCanonicalError("invalid_merge")
        now = _utc(now)
        for listing_key in loser.listing_keys:
            listing = self._require_listing(listing_key)
            self._require_policy_action(listing, "persist", now)
            self._repository.save_listing(replace(listing, canonical_opportunity_key=survivor.opportunity_key))
        for listing_key in survivor.listing_keys:
            self._require_policy_action(self._require_listing(listing_key), "persist", now)
        merged = replace(survivor, listing_keys=frozenset(set(survivor.listing_keys) | set(loser.listing_keys)))
        self._repository.save_opportunity(merged)
        self._repository.save_opportunity(replace(loser, tombstone_target_key=survivor.opportunity_key))
        self._emit(survivor.opportunity_key, "merged", now, {"loser_key": loser.opportunity_key})
        self._refresh_opportunity(survivor.opportunity_key, now, "merge")
        return self.resolve_opportunity(survivor.opportunity_key)

    def split(self, tombstone_key: str, listing_keys: Iterable[str], *, now: datetime) -> CanonicalOpportunity:
        tombstone = self._require_opportunity(tombstone_key)
        if tombstone.tombstone_target_key is None:
            raise MyOpportunitiesCanonicalError("not_merged")
        target = self.resolve_opportunity(tombstone.tombstone_target_key)
        selected = frozenset(listing_keys)
        if not selected or not selected.issubset(tombstone.listing_keys):
            raise MyOpportunitiesCanonicalError("invalid_split")
        now = _utc(now)
        for listing_key in selected:
            listing = self._require_listing(listing_key)
            self._require_policy_action(listing, "persist", now)
            self._repository.save_listing(replace(listing, canonical_opportunity_key=tombstone.opportunity_key))
        restored = replace(tombstone, listing_keys=selected, tombstone_target_key=None)
        self._repository.save_opportunity(restored)
        self._repository.save_opportunity(replace(target, listing_keys=frozenset(set(target.listing_keys) - set(selected))))
        self._emit(restored.opportunity_key, "split", now, {"survivor_key": target.opportunity_key})
        self._refresh_opportunity(restored.opportunity_key, now, "split")
        self._refresh_opportunity(target.opportunity_key, now, "split")
        return restored

    def tombstone_source_content(
        self, listing_key: str, *, now: datetime, actor: str = "system:source-policy",
        disposition: str = "removal", reason: str = "rights_withdrawn",
    ) -> None:
        listing = self._require_listing(listing_key)
        if listing.content_withheld:
            raise MyOpportunitiesCanonicalError("immutable_tombstone")
        now = _utc(now)
        policy = self._policy_at_use(listing)
        action = "remove" if disposition == "removal" else "terminate" if disposition == "termination" else ""
        if not action or not policy.allows(action, now):
            raise MyOpportunitiesCanonicalError("policy_denied")
        retained_source_fields = (
            policy.retained_source_fields
            if policy.dimensions.get("survivable_minimal_facts") is True
            else ()
        )
        terminal_listing = self._repository.tombstone_listing_content(
            listing_key,
            policy=policy,
            disposition=disposition,
            reason=reason,
            actor=_text(actor),
            retained_source_fields=retained_source_fields,
            now=now,
        )
        # Recompute only the canonical projection; the removal itself emits
        # exactly one content-free action event.
        self._refresh_opportunity(terminal_listing.canonical_opportunity_key, now, "content_tombstoned", emit=False)
        self._emit(
            terminal_listing.canonical_opportunity_key,
            "content_tombstoned",
            now,
            {"disposition": disposition, "reason": _text(reason)},
        )

    def resolve_opportunity(self, opportunity_key: str) -> CanonicalOpportunity:
        seen: set[str] = set()
        item = self._require_opportunity(opportunity_key)
        while item.tombstone_target_key is not None:
            if item.opportunity_key in seen:
                raise MyOpportunitiesCanonicalError("canonical_cycle")
            seen.add(item.opportunity_key)
            item = self._require_opportunity(item.tombstone_target_key)
        return item

    def _match_or_create(self, candidate: NormalizedListing, listing_key: str) -> tuple[CanonicalOpportunity, bool]:
        key = self._candidate_key(candidate)
        same_class = self._repository.opportunities(candidate.data_class)
        exact: list[CanonicalOpportunity] = []
        near: list[CanonicalOpportunity] = []
        for opportunity in same_class:
            if opportunity.tombstone_target_key is not None: continue
            heads = [self._require_version(self._require_listing(item).current_version_key) for item in opportunity.listing_keys]
            if any(self._candidate_key_from_version(head) == key for head in heads): exact.append(opportunity)
            elif any(self._near_match(candidate, head) for head in heads): near.append(opportunity)
        if exact:
            return sorted(exact, key=lambda item: item.opportunity_key)[0], False
        new = CanonicalOpportunity(_key(), candidate.data_class, frozenset(), None, None, None, {})
        self._repository.save_opportunity(new)
        return new, bool(near)

    def _refresh_opportunity(self, opportunity_key: str, now: datetime, event_kind: str, *, emit: bool = True) -> None:
        opportunity = self.resolve_opportunity(opportunity_key)
        # Governing truth is selected from rights-permitted current heads. The
        # Live Opportunity Gate is stricter (freshness, pending dedupe, and
        # application-link validity); it determines result eligibility, not
        # whether a newly admitted immutable source version receives its
        # requirement provenance.
        eligible = [
            self._require_listing(key)
            for key in opportunity.listing_keys
            if self._require_listing(key).state == "current"
            and self._policy_action_allowed(self._require_listing(key), "display", now)
        ]
        if not eligible:
            updated = replace(opportunity, governing_listing_key=None, governing_source_version_key=None, field_attribution={})
            self._repository.save_opportunity(updated)
            if emit:
                self._emit(opportunity.opportunity_key, event_kind, now, {"eligible": "false"})
            return
        ordered = sorted(eligible, key=lambda item: self._governing_sort_key(item))
        governing = ordered[0]
        governing_version = self._require_version(governing.current_version_key)
        field_attribution: dict[str, tuple[str, str]] = {}
        for field_name in {"employer", "title", "locations", "arrangement", "application_url", "description", *(governing_version.fields or {}).keys()}:
            for listing in ordered:
                source = self._require_version(listing.current_version_key)
                value = getattr(source, field_name, None) if hasattr(source, field_name) else (source.fields or {}).get(field_name)
                if value not in (None, "", (), []):
                    field_attribution[field_name] = (listing.listing_key, source.version_key)
                    break
        requirement = self._ensure_requirement_version(opportunity, governing_version, now)
        updated = replace(opportunity, governing_listing_key=governing.listing_key, governing_source_version_key=governing_version.version_key, requirement_version_key=requirement.requirement_version_key, field_attribution=field_attribution)
        self._repository.save_opportunity(updated)
        if emit:
            self._emit(opportunity.opportunity_key, event_kind, now, {"governing_listing_key": governing.listing_key})

    def _ensure_requirement_version(self, opportunity: CanonicalOpportunity, version: SourceVersion, now: datetime) -> RequirementVersion:
        clauses = tuple(_normal_clause(item) for item in (version.requirement_clauses or ()) if _normal_clause(item))
        fingerprint = sha256("\x1e".join(clauses).encode("utf-8")).hexdigest()
        # A governing source can move A -> B -> A (or fail over to a source
        # that already supplied A). Requirement provenance is append-only, so
        # reuse any live, same-class historical fingerprint rather than trying
        # to create a duplicate version for the same canonical opportunity.
        historical = sorted(
            (
                item
                for item in self._repository.requirement_versions_for(opportunity.opportunity_key)
                if (
                    item.data_class == opportunity.data_class
                    and not item.content_withheld
                    and item.clause_fingerprint == fingerprint
                )
            ),
            key=lambda item: item.requirement_version_key,
        )
        if historical:
            return historical[0]
        items = tuple(
            RequirementItem(
                str(uuid5(NAMESPACE_URL, f"{opportunity.opportunity_key}:{fingerprint}:{index + 1}:{clause}")),
                version.data_class,
                clause,
                index + 1,
            )
            for index, clause in enumerate(clauses)
        )
        derived = RequirementVersion(_key(), opportunity.opportunity_key, version.version_key, version.data_class, fingerprint, items, now)
        self._repository.save_requirement_version(derived)
        return derived

    def _governing_sort_key(self, listing: SourceListing) -> tuple[object, ...]:
        policy = self._policy_at_use(listing)
        version = self._require_version(listing.current_version_key)
        completeness = sum(bool(value) for value in (version.employer, version.title, version.locations, version.arrangement, version.application_url, version.description)) + sum(bool(value) for value in (version.fields or {}).values())
        fresh = listing.last_successfully_verified_at or datetime.min.replace(tzinfo=timezone.utc)
        return (policy.source_priority, -completeness, -fresh.timestamp(), listing.listing_key)

    def _candidate_key(self, candidate: NormalizedListing) -> tuple[str, str, tuple[str, ...], str]:
        return (_text(candidate.employer).casefold(), _text(candidate.title).casefold(), tuple(sorted(_text(item).casefold() for item in candidate.locations)), (urlsplit(candidate.application_url).hostname or "").casefold())

    def _candidate_key_from_version(self, version: SourceVersion) -> tuple[str, str, tuple[str, ...], str]:
        return (_text(version.employer).casefold(), _text(version.title).casefold(), tuple(sorted(_text(item).casefold() for item in version.locations)), (urlsplit(version.application_url).hostname or "").casefold())

    def _near_match(self, candidate: NormalizedListing, version: SourceVersion) -> bool:
        return _text(candidate.employer).casefold() == _text(version.employer).casefold() and _text(candidate.title).casefold() == _text(version.title).casefold() and bool(set(_text(item).casefold() for item in candidate.locations) & set(_text(item).casefold() for item in version.locations))

    def _validate_candidate(self, candidate: NormalizedListing) -> None:
        if candidate.data_class not in DATA_CLASSES or not all((_text(candidate.external_reference), _text(candidate.employer), _text(candidate.title), candidate.application_url)):
            raise MyOpportunitiesCanonicalError("admission_refused")
        parsed = urlsplit(candidate.application_url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise MyOpportunitiesCanonicalError("admission_refused")
        if not candidate.locations or not isinstance(candidate.description, str):
            raise MyOpportunitiesCanonicalError("admission_refused")

    def _policy(self, key: str, version: int, data_class: str | None = None) -> SourcePolicy:
        item = self._repository.policy_for(key, version, data_class)
        if item is None: raise MyOpportunitiesCanonicalError("policy_missing")
        return item

    def _current_policy(self, key: str, data_class: str | None = None) -> SourcePolicy:
        versions = self._repository.policy_versions(key, data_class)
        if not versions:
            raise MyOpportunitiesCanonicalError("policy_missing")
        return max(versions, key=lambda item: item.version)

    def _policy_for_descriptor_at_use(self, descriptor: ConnectorDescriptor) -> SourcePolicy:
        policy = self._current_policy(descriptor.policy_key, descriptor.data_class)
        if (
            policy.source_id != descriptor.source_id
            or policy.source_class != descriptor.source_class
            or policy.data_class != descriptor.data_class
        ):
            raise MyOpportunitiesCanonicalError("policy_denied")
        return policy

    def _policy_at_use(self, listing: SourceListing) -> SourcePolicy:
        """Use the newest recorded policy version without re-ingesting data.

        A later C11 adapter may publish a new policy version after a rights,
        removal, or termination change. Heads retain their receipt-time policy
        reference for provenance, while every render/gate/retention decision
        uses this current version and therefore fails closed immediately.
        """

        policy = self._current_policy(listing.policy_key, listing.data_class)
        if policy.source_id != listing.source_id or policy.data_class != listing.data_class:
            raise MyOpportunitiesCanonicalError("policy_denied")
        return policy

    def _policy_action_allowed(self, listing: SourceListing, action: str, now: datetime) -> bool:
        try:
            return self._policy_at_use(listing).allows(action, now)
        except MyOpportunitiesCanonicalError:
            return False

    def _require_policy_action(self, listing: SourceListing, action: str, now: datetime) -> None:
        if not self._policy_action_allowed(listing, action, now):
            raise MyOpportunitiesCanonicalError("policy_denied")

    def _persist_receipt(self, receipt: SourceReceipt) -> None:
        existing = self._repository.receipt(receipt.receipt_key)
        if existing is None:
            self._repository.save_receipt(receipt)
        elif existing != receipt:
            raise MyOpportunitiesCanonicalError("immutable_receipt")

    def _registered_descriptor(self, descriptor: ConnectorDescriptor) -> None:
        if self._descriptors.get((descriptor.data_class, descriptor.source_id)) != descriptor:
            raise MyOpportunitiesCanonicalError("connector_unregistered")

    def _require_listing(self, key: str) -> SourceListing:
        item = self._repository.listing(key)
        if item is None: raise MyOpportunitiesCanonicalError("listing_not_found")
        return item

    def _require_version(self, key: str) -> SourceVersion:
        item = self._repository.version(key)
        if item is None: raise MyOpportunitiesCanonicalError("source_version_not_found")
        return item

    def _require_opportunity(self, key: str) -> CanonicalOpportunity:
        item = self._repository.opportunity(key)
        if item is None: raise MyOpportunitiesCanonicalError("opportunity_not_found")
        return item

    def _emit(self, opportunity_key: str, kind: str, now: datetime, detail: Mapping[str, str]) -> None:
        opportunity = self._require_opportunity(opportunity_key)
        self._repository.save_event(CanonicalEvent(_key(), opportunity_key, opportunity.data_class, kind, now, dict(detail)))
