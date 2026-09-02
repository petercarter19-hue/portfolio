"""Rights-gated, provider-neutral feed adapters for My Opportunities C11.

This module deliberately contains no default network client.  Production
construction first resolves the exact named settings and then requires a
C9-operated sender.  Recorded fixtures use :class:`RecordedTransport`, whose
only input is already-present bytes and which has no socket path.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
from math import isfinite
from random import uniform
import re
import time
from types import MappingProxyType
from typing import Callable, Iterable, Mapping, Protocol, Sequence
from urllib.parse import urlsplit

from .canonical_service import CanonicalRepository, CanonicalService, SourcePolicy
from .connectors import ConnectorDescriptor, NormalizedListing, SourceReceiptInput


LICENSED_AGGREGATOR = "licensed_commercial_aggregate"
GOVERNMENT_FEED = "permitted_public"
DIRECT_EMPLOYER = "direct_employer"

AGGREGATOR_PROVIDER_SETTING = "PEERSLATE_MYOPP_FEED_AGGREGATOR_PROVIDER"
AGGREGATOR_APP_ID_SETTING = "PEERSLATE_MYOPP_FEED_AGGREGATOR_APP_ID"
AGGREGATOR_API_KEY_SETTING = "PEERSLATE_MYOPP_FEED_AGGREGATOR_API_KEY"
GOVERNMENT_API_KEY_SETTING = "PEERSLATE_MYOPP_FEED_GOVERNMENT_API_KEY"
GOVERNMENT_EMAIL_SETTING = "PEERSLATE_MYOPP_FEED_GOVERNMENT_USER_AGENT_EMAIL"
DIRECT_BOARDS_SETTING = "PEERSLATE_MYOPP_FEED_DIRECT_BOARDS"

_SETTINGS_BY_CLASS = {
    LICENSED_AGGREGATOR: (
        AGGREGATOR_PROVIDER_SETTING,
        AGGREGATOR_APP_ID_SETTING,
        AGGREGATOR_API_KEY_SETTING,
    ),
    GOVERNMENT_FEED: (GOVERNMENT_API_KEY_SETTING, GOVERNMENT_EMAIL_SETTING),
    DIRECT_EMPLOYER: (DIRECT_BOARDS_SETTING,),
}

_ERROR_CODES = frozenset(
    {
        "budget_exhausted",
        "contract_violation",
        "credentials_missing",
        "credentials_rejected",
        "payload_malformed",
        "policy_denied",
        "policy_missing",
        "rate_limited",
        "transient_exhausted",
        "transport_unavailable",
    }
)
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")
_BOARD_RE = re.compile(r"^(greenhouse|lever):([a-z0-9][a-z0-9_-]{0,62})$")
_MAX_DIRECT_BINDING_BYTES = 32 * 1024


class LicensedFeedError(RuntimeError):
    """Closed, content-free adapter failure vocabulary."""

    def __init__(self, code: str, *safe_context: str) -> None:
        if code not in _ERROR_CODES:
            raise ValueError("unknown licensed-feed error code")
        self.code = code
        self.safe_context = tuple(str(value) for value in safe_context)
        message = code
        if self.safe_context:
            message += ":" + ",".join(self.safe_context)
        super().__init__(message)


@dataclass(frozen=True)
class FeedSettings:
    """Resolved setting values; values are intentionally absent from repr."""

    source_class: str
    _values: Mapping[str, str] = field(repr=False)

    @classmethod
    def resolve(cls, environ: Mapping[str, str], source_class: str) -> "FeedSettings":
        required = _SETTINGS_BY_CLASS.get(source_class)
        if required is None:
            raise LicensedFeedError("contract_violation", "source_class")
        values = {name: str(environ.get(name, "")).strip() for name in required}
        missing = tuple(name for name in required if not values[name])
        if missing:
            raise LicensedFeedError("credentials_missing", *missing)
        settings = cls(source_class, MappingProxyType(values))
        settings._validate_shape()
        return settings

    def value(self, name: str) -> str:
        if name not in _SETTINGS_BY_CLASS[self.source_class]:
            raise LicensedFeedError("contract_violation", "setting_name")
        return self._values[name]

    def direct_boards(self) -> tuple[tuple[str, str], ...]:
        if self.source_class != DIRECT_EMPLOYER:
            return ()
        return tuple((ats, board) for ats, board, _employer in self.direct_employers())

    def direct_employers(self) -> tuple[tuple[str, str, str], ...]:
        """Return exact approved board-to-employer bindings from one named setting."""

        if self.source_class != DIRECT_EMPLOYER:
            return ()

        def unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
            result: dict[str, object] = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError("duplicate key")
                result[key] = value
            return result

        raw = self.value(DIRECT_BOARDS_SETTING)
        if len(raw.encode("utf-8")) > _MAX_DIRECT_BINDING_BYTES:
            raise LicensedFeedError("contract_violation", DIRECT_BOARDS_SETTING)
        try:
            configured = json.loads(
                raw,
                object_pairs_hook=unique_object,
            )
        except (json.JSONDecodeError, RecursionError, TypeError, ValueError):
            raise LicensedFeedError(
                "contract_violation", DIRECT_BOARDS_SETTING
            ) from None
        if not isinstance(configured, dict) or not configured or len(configured) > 100:
            raise LicensedFeedError("contract_violation", DIRECT_BOARDS_SETTING)
        bindings: list[tuple[str, str, str]] = []
        for token, value in configured.items():
            match = _BOARD_RE.fullmatch(token)
            if (
                match is None
                or not isinstance(value, str)
                or not value.strip()
                or value != value.strip()
                or len(value.strip()) > 200
                or any(
                    not character.isprintable()
                    or character in "\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069"
                    for character in value
                )
            ):
                raise LicensedFeedError("contract_violation", DIRECT_BOARDS_SETTING)
            bindings.append((match.group(1), match.group(2), value))
        return tuple(sorted(bindings))

    def direct_employer(self, ats: str, board: str) -> str | None:
        for bound_ats, bound_board, employer in self.direct_employers():
            if (bound_ats, bound_board) == (ats, board):
                return employer
        return None

    def _validate_shape(self) -> None:
        if self.source_class == LICENSED_AGGREGATOR:
            provider = self.value(AGGREGATOR_PROVIDER_SETTING).casefold()
            if provider not in {"adzuna", "jooble"}:
                raise LicensedFeedError("contract_violation", AGGREGATOR_PROVIDER_SETTING)
        elif self.source_class == GOVERNMENT_FEED:
            email = self.value(GOVERNMENT_EMAIL_SETTING)
            if "@" not in email or any(character.isspace() for character in email):
                raise LicensedFeedError("contract_violation", GOVERNMENT_EMAIL_SETTING)
        elif not self.direct_boards():
            raise LicensedFeedError("contract_violation", DIRECT_BOARDS_SETTING)


@dataclass(frozen=True)
class FeedRequest:
    """One bounded request; a live sender must enforce ``timeout_seconds``."""

    url: str
    page: int
    headers: Mapping[str, str] = field(repr=False)
    timeout_seconds: float

    def __post_init__(self) -> None:
        if (
            not isinstance(self.timeout_seconds, (int, float))
            or isinstance(self.timeout_seconds, bool)
            or not isfinite(self.timeout_seconds)
            or self.timeout_seconds <= 0
        ):
            raise LicensedFeedError("contract_violation", "request_timeout")


@dataclass(frozen=True)
class RawResponse:
    status: int
    body: bytes = field(repr=False)
    content_type: str = "application/json"
    external_reference: str | None = None
    next_page: bool = False
    retry_after_seconds: float | None = None


@dataclass(frozen=True)
class _RawItemSlice:
    """One decoded provider item paired with its untouched JSON token bytes."""

    value: object
    raw: bytes = field(repr=False)


def _reject_duplicate_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON member")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> object:
    del value
    raise ValueError("non-JSON numeric constant")


def _skip_json_whitespace(text: str, position: int) -> int:
    while position < len(text) and text[position] in " \t\r\n":
        position += 1
    return position


def _slices_at_path(
    text: str,
    position: int,
    path: tuple[str, ...],
    decoder: json.JSONDecoder,
) -> tuple[_RawItemSlice, ...]:
    position = _skip_json_whitespace(text, position)
    if not path:
        if position >= len(text) or text[position] != "[":
            raise ValueError("item container is not an array")
        position = _skip_json_whitespace(text, position + 1)
        items: list[_RawItemSlice] = []
        if position < len(text) and text[position] == "]":
            return ()
        while True:
            start = position
            value, end = decoder.raw_decode(text, start)
            items.append(_RawItemSlice(value, text[start:end].encode("utf-8")))
            position = _skip_json_whitespace(text, end)
            if position >= len(text):
                raise ValueError("unterminated array")
            if text[position] == "]":
                return tuple(items)
            if text[position] != ",":
                raise ValueError("invalid array delimiter")
            position = _skip_json_whitespace(text, position + 1)

    if position >= len(text) or text[position] != "{":
        raise ValueError("item path parent is not an object")
    position = _skip_json_whitespace(text, position + 1)
    selected: tuple[_RawItemSlice, ...] | None = None
    if position < len(text) and text[position] == "}":
        raise ValueError("missing item path")
    while True:
        key, key_end = decoder.raw_decode(text, position)
        if not isinstance(key, str):
            raise ValueError("object member name is not a string")
        position = _skip_json_whitespace(text, key_end)
        if position >= len(text) or text[position] != ":":
            raise ValueError("missing object colon")
        value_start = _skip_json_whitespace(text, position + 1)
        if key == path[0]:
            selected = _slices_at_path(text, value_start, path[1:], decoder)
        _, value_end = decoder.raw_decode(text, value_start)
        position = _skip_json_whitespace(text, value_end)
        if position >= len(text):
            raise ValueError("unterminated object")
        if text[position] == "}":
            if selected is None:
                raise ValueError("missing item path")
            return selected
        if text[position] != ",":
            raise ValueError("invalid object delimiter")
        position = _skip_json_whitespace(text, position + 1)


def _strict_json_decoder() -> json.JSONDecoder:
    return json.JSONDecoder(
        object_pairs_hook=_reject_duplicate_object,
        parse_constant=_reject_json_constant,
    )


def _decode_json_item(raw: bytes) -> object:
    try:
        text = raw.decode("utf-8")
        if text.startswith("\ufeff"):
            raise ValueError("JSON BOM is not accepted")
        decoder = _strict_json_decoder()
        start = _skip_json_whitespace(text, 0)
        value, end = decoder.raw_decode(text, start)
        if _skip_json_whitespace(text, end) != len(text) or not isinstance(value, Mapping):
            raise ValueError("receipt is not exactly one JSON object")
        return value
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, TypeError, ValueError) as error:
        raise LicensedFeedError("contract_violation", "response_shape") from error


def _json_item_slices(
    raw: bytes,
    path: tuple[str, ...],
) -> tuple[object, tuple[_RawItemSlice, ...]]:
    try:
        text = raw.decode("utf-8")
        if text.startswith("\ufeff"):
            raise ValueError("JSON BOM is not accepted")
        decoder = _strict_json_decoder()
        start = _skip_json_whitespace(text, 0)
        document, end = decoder.raw_decode(text, start)
        if _skip_json_whitespace(text, end) != len(text):
            raise ValueError("trailing response material")
        return document, _slices_at_path(text, start, path, decoder)
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, TypeError, ValueError) as error:
        raise LicensedFeedError("contract_violation", "response_shape") from error


class FeedTransport(Protocol):
    def fetch(self, request: FeedRequest) -> RawResponse: ...


class RecordedTransport:
    """Byte-for-byte fixture playback with no network-capable dependency."""

    def __init__(self, responses: Iterable[RawResponse]) -> None:
        self._responses = tuple(responses)
        self._cursor = 0
        self.fetch_count = 0

    def fetch(self, request: FeedRequest) -> RawResponse:
        del request
        self.fetch_count += 1
        if self._cursor >= len(self._responses):
            raise LicensedFeedError("contract_violation", "recording_exhausted")
        response = self._responses[self._cursor]
        self._cursor += 1
        return response


class LiveTransport:
    """A pinned-endpoint, timeout-bound seam; the network sender is C9-owned."""

    def __init__(
        self,
        *,
        endpoint_prefix: str,
        headers: Mapping[str, str],
        sender: Callable[[FeedRequest], RawResponse] | None,
    ) -> None:
        endpoint = urlsplit(endpoint_prefix)
        if (
            endpoint.scheme != "https"
            or not endpoint.hostname
            or endpoint.username
            or endpoint.password
            or endpoint.query
            or endpoint.fragment
        ):
            raise LicensedFeedError("contract_violation", "endpoint")
        if sender is None:
            raise LicensedFeedError("transport_unavailable")
        self._endpoint_prefix = endpoint_prefix.rstrip("/")
        self._endpoint = urlsplit(self._endpoint_prefix)
        self._headers = dict(headers)
        self._sender = sender
        self.fetch_count = 0

    @property
    def headers(self) -> Mapping[str, str]:
        """Expose header names only; values must never enter logs or receipts."""

        return {name: "<redacted>" for name in self._headers}

    def fetch(self, request: FeedRequest) -> RawResponse:
        if (
            not isinstance(request.timeout_seconds, (int, float))
            or isinstance(request.timeout_seconds, bool)
            or not isfinite(request.timeout_seconds)
            or request.timeout_seconds <= 0
        ):
            raise LicensedFeedError("contract_violation", "request_timeout")
        try:
            target = urlsplit(request.url)
            same_origin = (
                target.scheme == self._endpoint.scheme
                and target.hostname == self._endpoint.hostname
                and target.port == self._endpoint.port
                and not target.username
                and not target.password
            )
        except ValueError:
            raise LicensedFeedError("contract_violation", "endpoint") from None
        endpoint_path = self._endpoint.path.rstrip("/") or "/"
        target_path = target.path.rstrip("/") or "/"
        path_is_pinned = target_path == endpoint_path or target_path.startswith(endpoint_path + "/")
        if (
            not same_origin
            or not path_is_pinned
            or target.fragment
            or any(segment == ".." for segment in target.path.split("/"))
        ):
            raise LicensedFeedError("contract_violation", "endpoint")
        self.fetch_count += 1
        started = time.monotonic()
        response = self._sender(replace(request, headers=dict(self._headers)))
        if time.monotonic() - started >= request.timeout_seconds:
            raise TimeoutError("sender exceeded request timeout")
        return response


@dataclass(frozen=True)
class FeedBudget:
    max_pages: int = 5
    max_items: int = 200
    max_total_bytes: int = 10 * 1024 * 1024
    max_payload_bytes: int = 5 * 1024 * 1024
    max_seconds: float = 30.0
    max_transient_retries: int = 2
    max_rate_limit_retries: int = 1
    max_retry_delay_seconds: float = 2.0
    min_request_interval_seconds: float = 0.0

    def __post_init__(self) -> None:
        integer_values = (
            self.max_pages,
            self.max_items,
            self.max_total_bytes,
            self.max_payload_bytes,
        )
        if any(not isinstance(value, int) or isinstance(value, bool) for value in integer_values):
            raise ValueError("feed count and byte budgets must be integers")
        if any(value <= 0 for value in integer_values):
            raise ValueError("feed budgets must be positive")
        if (
            self.max_pages > 5
            or self.max_items > 200
            or self.max_total_bytes > 10 * 1024 * 1024
        ):
            raise ValueError("feed budgets may not exceed the package ceilings")
        if (
            not isinstance(self.max_seconds, (int, float))
            or isinstance(self.max_seconds, bool)
            or not isfinite(self.max_seconds)
            or self.max_seconds <= 0
        ):
            raise ValueError("feed time budget must be positive and finite")
        if self.max_seconds > 30.0:
            raise ValueError("feed time budget may not exceed the package ceiling")
        if self.max_payload_bytes > 5 * 1024 * 1024:
            raise ValueError("payload budget may not exceed C2's receipt cap")
        if (
            not isinstance(self.max_transient_retries, int)
            or isinstance(self.max_transient_retries, bool)
            or not isinstance(self.max_rate_limit_retries, int)
            or isinstance(self.max_rate_limit_retries, bool)
            or self.max_transient_retries < 0
            or self.max_rate_limit_retries < 0
        ):
            raise ValueError("retry budgets may not be negative")
        if self.max_transient_retries > 2 or self.max_rate_limit_retries > 1:
            raise ValueError("retry budgets may not exceed the package ceilings")
        rate_values = (self.max_retry_delay_seconds, self.min_request_interval_seconds)
        if any(
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not isfinite(value)
            or value < 0
            for value in rate_values
        ):
            raise ValueError("rate budgets may not be negative")
        if self.max_retry_delay_seconds > 2.0:
            raise ValueError("retry delay may not exceed the package ceiling")


_GLOBAL_PRODUCTION_LIMIT = FeedBudget(min_request_interval_seconds=0.001)
_GOVERNMENT_PRODUCTION_LIMIT = FeedBudget(min_request_interval_seconds=1.0)
_DIRECT_PRODUCTION_LIMIT = FeedBudget(
    max_pages=2,
    max_items=100,
    min_request_interval_seconds=1.0,
)


def _production_budget(
    requested: FeedBudget | None,
    limit: FeedBudget,
    *,
    require_explicit: bool = False,
) -> FeedBudget:
    if requested is None:
        if require_explicit:
            raise LicensedFeedError("contract_violation", "rate_budget")
        return limit
    upper_bounded = (
        requested.max_pages <= limit.max_pages
        and requested.max_items <= limit.max_items
        and requested.max_total_bytes <= limit.max_total_bytes
        and requested.max_payload_bytes <= limit.max_payload_bytes
        and requested.max_seconds <= limit.max_seconds
        and requested.max_transient_retries <= limit.max_transient_retries
        and requested.max_rate_limit_retries <= limit.max_rate_limit_retries
        and requested.max_retry_delay_seconds <= limit.max_retry_delay_seconds
    )
    if not upper_bounded or requested.min_request_interval_seconds < limit.min_request_interval_seconds:
        raise LicensedFeedError("contract_violation", "rate_budget")
    return requested


@dataclass(frozen=True)
class FeedRunOutcome:
    receipts: tuple[SourceReceiptInput, ...] = field(repr=False)
    pages: int
    attempts: int
    bytes_received: int
    refusal_codes: tuple[str, ...]
    truncated: bool


PolicyReader = Callable[[ConnectorDescriptor], SourcePolicy | None]


class RightsProjection:
    """Conservative normalize-time projection from the current C2 policy."""

    _EXCERPT_FIELDS = frozenset({"excerpt", "snippet", "summary"})
    _ATTRIBUTION_FIELDS = frozenset({"attribution", "attribution_url"})

    def __init__(self, policy_reader: PolicyReader) -> None:
        self._policy_reader = policy_reader

    def current_policy(self, descriptor: ConnectorDescriptor, *, now: datetime) -> SourcePolicy:
        policy = self._policy_reader(descriptor)
        if policy is None:
            raise LicensedFeedError("policy_missing")
        if (
            policy.policy_key != descriptor.policy_key
            or policy.version < max(1, descriptor.policy_version)
            or policy.source_id != descriptor.source_id
            or policy.source_class != descriptor.source_class
            or policy.data_class != descriptor.data_class
        ):
            raise LicensedFeedError("policy_denied")
        when = _utc(now)
        if (
            not policy.evidence_ref
            or not policy.decision_ref
            or _utc(policy.effective_at) > when
            or (policy.expires_at is not None and _utc(policy.expires_at) <= when)
        ):
            raise LicensedFeedError("policy_denied")
        return policy

    def require_action(
        self, descriptor: ConnectorDescriptor, action: str, *, now: datetime
    ) -> SourcePolicy:
        return self.require_actions(descriptor, (action,), now=now)

    def require_actions(
        self,
        descriptor: ConnectorDescriptor,
        actions: Iterable[str],
        *,
        now: datetime,
    ) -> SourcePolicy:
        policy = self.current_policy(descriptor, now=now)
        when = _utc(now)
        for action in tuple(actions):
            if not policy.allows(action, when):
                raise LicensedFeedError("policy_denied", action)
        return policy

    def project(
        self,
        descriptor: ConnectorDescriptor,
        listing: NormalizedListing,
        *,
        now: datetime,
    ) -> NormalizedListing:
        policy = self.current_policy(descriptor, now=now)
        if not policy.allows("persist", _utc(now)):
            return NormalizedListing(
                external_reference="",
                employer="",
                title="",
                locations=(),
                arrangement=None,
                application_url="",
                expected_application_hosts=(),
                description="",
                requirement_clauses=(),
                fields={},
                data_class=listing.data_class,
            )
        fields = dict(listing.fields)
        if policy.dimensions.get("excerpt") is not True:
            fields = {key: value for key, value in fields.items() if key not in self._EXCERPT_FIELDS}
        if policy.dimensions.get("attribution") is not True:
            fields = {key: value for key, value in fields.items() if key not in self._ATTRIBUTION_FIELDS}
        description = listing.description
        clauses = listing.requirement_clauses
        if policy.dimensions.get("full_description") is not True:
            description = ""
            clauses = ()
        return replace(
            listing,
            description=description,
            requirement_clauses=clauses,
            fields=fields,
        )


@dataclass(frozen=True)
class ExitManifest:
    source_id: str
    policy_key: str
    peer_slate_record_keys: tuple[str, ...]
    permitted_source_identifiers: tuple[str, ...]


class TerminationExitRehearsal:
    """Small driver over C2's per-listing removal/termination seams."""

    @staticmethod
    def remove(
        canonical: CanonicalService, listing_key: str, *, now: datetime, reason: str
    ) -> None:
        canonical.tombstone_source_content(
            listing_key,
            now=now,
            disposition="removal",
            reason=reason,
        )

    @staticmethod
    def terminate(
        canonical: CanonicalService,
        repository: CanonicalRepository,
        revision: SourcePolicy,
        listing_keys: Sequence[str],
        *,
        now: datetime,
        reason: str,
    ) -> None:
        when = _utc(now)
        if (
            not isinstance(revision, SourcePolicy)
            or not isinstance(reason, str)
            or not reason.strip()
            or isinstance(listing_keys, (str, bytes))
        ):
            raise LicensedFeedError("contract_violation", "termination_input")
        try:
            keys = tuple(listing_keys)
        except TypeError:
            raise LicensedFeedError("contract_violation", "termination_input") from None
        if (
            not keys
            or any(not isinstance(key, str) or not key.strip() for key in keys)
            or not revision.allows("terminate", when)
            or revision.allows("acquire", when)
            or revision.allows("persist", when)
            or revision.allows("display", when)
        ):
            raise LicensedFeedError("contract_violation", "termination_policy")

        unique_keys = tuple(dict.fromkeys(keys))
        policies = repository.policy_versions(revision.policy_key, revision.data_class)
        if not policies:
            raise LicensedFeedError("contract_violation", "termination_policy")
        current = max(policies, key=lambda policy: policy.version)
        revision_is_current = current == revision
        if not revision_is_current and current.version + 1 != revision.version:
            raise LicensedFeedError("contract_violation", "termination_policy")

        pending_keys: list[str] = []
        for listing_key in unique_keys:
            listing = repository.listing(listing_key)
            if listing is None:
                raise LicensedFeedError("contract_violation", "termination_listing_set")
            if listing.content_withheld:
                completed_by_revision = (
                    revision_is_current
                    and listing.state == "invalid"
                    and listing.terminal_disposition == "termination"
                    and listing.tombstone_policy_key == revision.policy_key
                    and listing.tombstone_policy_version == revision.version
                )
                if not completed_by_revision:
                    raise LicensedFeedError(
                        "contract_violation", "termination_listing_set"
                    )
                continue
            if (
                listing.policy_key != revision.policy_key
                or listing.data_class != revision.data_class
                or listing.source_id != revision.source_id
            ):
                raise LicensedFeedError("contract_violation", "termination_listing_set")
            pending_keys.append(listing_key)

        if not revision_is_current:
            canonical.revise_policy(revision, now=now)
        for listing_key in pending_keys:
            canonical.tombstone_source_content(
                listing_key,
                now=now,
                disposition="termination",
                reason=reason,
            )

    @staticmethod
    def export_manifest(
        descriptor: ConnectorDescriptor,
        *,
        policy_reader: PolicyReader,
        now: datetime,
        peer_slate_record_keys: Iterable[str],
        source_identifiers: Iterable[str],
    ) -> ExitManifest:
        policy = RightsProjection(policy_reader).require_action(
            descriptor,
            "export",
            now=now,
        )
        permitted = ()
        if (
            policy.dimensions.get("survivable_minimal_facts") is True
            and {
                "listing.external_reference",
                "receipt.external_reference",
            }.intersection(policy.retained_source_fields)
        ):
            permitted = tuple(sorted({str(value) for value in source_identifiers}))
        return ExitManifest(
            source_id=policy.source_id,
            policy_key=policy.policy_key,
            peer_slate_record_keys=tuple(sorted({str(value) for value in peer_slate_record_keys})),
            permitted_source_identifiers=permitted,
        )

    @staticmethod
    def assert_member_truth_unchanged(before: object, after: object) -> None:
        if before != after:
            raise LicensedFeedError("contract_violation", "member_truth_changed")


class FeedAdapterBase:
    """Shared describe/acquire/normalize skeleton for all source classes."""

    def __init__(
        self,
        *,
        descriptor: ConnectorDescriptor,
        transport: FeedTransport,
        projection: RightsProjection,
        endpoint_prefix: str,
        budget: FeedBudget | None = None,
        clock: Callable[[], datetime] | None = None,
        monotonic: Callable[[], float] | None = None,
        sleeper: Callable[[float], None] | None = None,
        settings: FeedSettings | None = None,
    ) -> None:
        if descriptor.data_class == "production":
            if settings is None or settings.source_class != descriptor.source_class:
                missing = _SETTINGS_BY_CLASS.get(descriptor.source_class, ())
                raise LicensedFeedError("credentials_missing", *missing)
            if not isinstance(transport, LiveTransport):
                raise LicensedFeedError("contract_violation", "production_transport")
        elif descriptor.data_class == "fixture":
            if settings is not None or not isinstance(transport, RecordedTransport):
                raise LicensedFeedError("contract_violation", "fixture_transport")
        else:
            raise LicensedFeedError("contract_violation", "data_class")
        self._descriptor = descriptor
        self._transport = transport
        self._projection = projection
        self._endpoint_prefix = endpoint_prefix.rstrip("/")
        self._budget = budget or FeedBudget()
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._monotonic = monotonic or time.monotonic
        self._sleeper = sleeper or time.sleep
        self._settings = settings
        self.last_run = FeedRunOutcome((), 0, 0, 0, (), False)

    def describe(self) -> ConnectorDescriptor:
        return self._descriptor

    def acquire(self) -> tuple[SourceReceiptInput, ...]:
        start = self._monotonic()
        receipts: list[SourceReceiptInput] = []
        refusals: list[str] = []
        pages = 0
        attempts = 0
        items_seen = 0
        total_bytes = 0
        retained_receipt_bytes = 0
        seen_references: set[str] = set()
        page = 1
        truncated = False
        stop = False
        while True:
            if page > self._budget.max_pages:
                self._finish(receipts, pages, attempts, total_bytes, refusals, True)
                raise LicensedFeedError("budget_exhausted", "pages")
            transient_retries = 0
            rate_retries = 0
            while True:
                self._check_time(start, receipts, pages, attempts, total_bytes, refusals)
                if attempts and self._budget.min_request_interval_seconds:
                    self._bounded_sleep(
                        self._budget.min_request_interval_seconds,
                        start,
                        receipts,
                        pages,
                        attempts,
                        total_bytes,
                        refusals,
                    )
                try:
                    self._projection.require_actions(
                        self._descriptor,
                        ("acquire", "persist"),
                        now=self._clock(),
                    )
                except LicensedFeedError:
                    self._finish(receipts, pages, attempts, total_bytes, refusals, truncated)
                    raise
                remaining_seconds = self._check_time(
                    start,
                    receipts,
                    pages,
                    attempts,
                    total_bytes,
                    refusals,
                )
                attempts += 1
                try:
                    response = self._transport.fetch(
                        self._request(page, timeout_seconds=remaining_seconds)
                    )
                except LicensedFeedError:
                    raise
                except (TimeoutError, OSError):
                    if transient_retries >= self._budget.max_transient_retries:
                        self._finish(receipts, pages, attempts, total_bytes, refusals, truncated)
                        raise LicensedFeedError("transient_exhausted")
                    transient_retries += 1
                    ceiling = min(
                        0.1 * (2**transient_retries),
                        self._budget.max_retry_delay_seconds,
                    )
                    self._bounded_sleep(
                        uniform(0.0, ceiling),
                        start,
                        receipts,
                        pages,
                        attempts,
                        total_bytes,
                        refusals,
                    )
                    continue
                if not isinstance(response, RawResponse):
                    self._finish(receipts, pages, attempts, total_bytes, refusals, truncated)
                    raise LicensedFeedError("contract_violation", "response_type")
                if (
                    not isinstance(response.status, int)
                    or isinstance(response.status, bool)
                    or not isinstance(response.next_page, bool)
                    or not isinstance(response.content_type, str)
                    or not response.content_type.strip()
                    or (
                        response.external_reference is not None
                        and not isinstance(response.external_reference, str)
                    )
                    or (
                        response.retry_after_seconds is not None
                        and (
                            not isinstance(response.retry_after_seconds, (int, float))
                            or isinstance(response.retry_after_seconds, bool)
                            or not isfinite(response.retry_after_seconds)
                            or response.retry_after_seconds < 0
                        )
                    )
                ):
                    self._finish(receipts, pages, attempts, total_bytes, refusals, truncated)
                    raise LicensedFeedError("contract_violation", "response_metadata")
                self._check_time(start, receipts, pages, attempts, total_bytes, refusals)
                if response.status in {401, 403}:
                    self._finish(receipts, pages, attempts, total_bytes, refusals, truncated)
                    raise LicensedFeedError("credentials_rejected")
                if response.status == 429:
                    if rate_retries >= self._budget.max_rate_limit_retries:
                        self._finish(receipts, pages, attempts, total_bytes, refusals, truncated)
                        raise LicensedFeedError("rate_limited")
                    rate_retries += 1
                    delay = response.retry_after_seconds or 0.0
                    if delay > self._budget.max_retry_delay_seconds:
                        self._finish(receipts, pages, attempts, total_bytes, refusals, truncated)
                        raise LicensedFeedError("rate_limited")
                    self._bounded_sleep(
                        delay,
                        start,
                        receipts,
                        pages,
                        attempts,
                        total_bytes,
                        refusals,
                    )
                    continue
                if 500 <= response.status <= 599:
                    if transient_retries >= self._budget.max_transient_retries:
                        self._finish(receipts, pages, attempts, total_bytes, refusals, truncated)
                        raise LicensedFeedError("transient_exhausted")
                    transient_retries += 1
                    ceiling = min(
                        0.1 * (2**transient_retries),
                        self._budget.max_retry_delay_seconds,
                    )
                    self._bounded_sleep(
                        uniform(0.0, ceiling),
                        start,
                        receipts,
                        pages,
                        attempts,
                        total_bytes,
                        refusals,
                    )
                    continue
                if not 200 <= response.status < 300:
                    self._finish(receipts, pages, attempts, total_bytes, refusals, truncated)
                    raise LicensedFeedError("contract_violation", "http_status")
                break
            pages += 1
            if not isinstance(response.body, bytes):
                self._finish(receipts, pages, attempts, total_bytes, refusals, truncated)
                raise LicensedFeedError("contract_violation", "payload_type")
            media_type = response.content_type.split(";", 1)[0].strip().casefold()
            if media_type != "application/json" and not media_type.endswith("+json"):
                self._finish(receipts, pages, attempts, total_bytes, refusals, truncated)
                raise LicensedFeedError("contract_violation", "content_type")
            size = len(response.body)
            if (
                not response.body
                or size > self._budget.max_payload_bytes
                or total_bytes + size > self._budget.max_total_bytes
            ):
                self._finish(receipts, pages, attempts, total_bytes, refusals, truncated)
                raise LicensedFeedError("contract_violation", "payload_size")
            total_bytes += size
            try:
                raw_items = self._raw_items(response.body)
            except LicensedFeedError:
                self._finish(receipts, pages, attempts, total_bytes, refusals, truncated)
                raise
            if response.external_reference is not None and len(raw_items) != 1:
                self._finish(receipts, pages, attempts, total_bytes, refusals, truncated)
                raise LicensedFeedError("contract_violation", "external_reference")
            page_received_at = _utc(self._clock())
            for raw_item in raw_items:
                if items_seen >= self._budget.max_items:
                    truncated = True
                    stop = True
                    break
                items_seen += 1
                try:
                    candidate = self._map_item(raw_item.value)
                    self._validate_candidate(candidate)
                except LicensedFeedError as error:
                    if error.code == "payload_malformed":
                        refusals.append(error.code)
                        continue
                    self._finish(receipts, pages, attempts, total_bytes, refusals, truncated)
                    raise
                external_reference = candidate.external_reference
                if (
                    response.external_reference is not None
                    and response.external_reference != external_reference
                ):
                    self._finish(receipts, pages, attempts, total_bytes, refusals, truncated)
                    raise LicensedFeedError("contract_violation", "external_reference")
                if external_reference in seen_references:
                    self._finish(receipts, pages, attempts, total_bytes, refusals, truncated)
                    raise LicensedFeedError("contract_violation", "duplicate_external_reference")
                seen_references.add(external_reference)
                self._check_time(start, receipts, pages, attempts, total_bytes, refusals)
                if retained_receipt_bytes + len(raw_item.raw) > self._budget.max_total_bytes:
                    self._finish(receipts, pages, attempts, total_bytes, refusals, True)
                    raise LicensedFeedError("budget_exhausted", "receipt_bytes")
                receipts.append(
                    SourceReceiptInput(
                        external_reference=external_reference,
                        received_at=page_received_at,
                        content_type=str(response.content_type).strip().casefold(),
                        payload=raw_item.raw,
                    )
                )
                retained_receipt_bytes += len(raw_item.raw)
            if stop or (items_seen >= self._budget.max_items and response.next_page):
                truncated = True
                break
            if not response.next_page:
                break
            page += 1
        self._finish(receipts, pages, attempts, total_bytes, refusals, truncated)
        return tuple(receipts)

    def normalize(self, receipt: SourceReceiptInput) -> NormalizedListing:
        candidate = self._map_item(_decode_json_item(receipt.payload))
        self._validate_candidate(candidate)
        if candidate.external_reference != receipt.external_reference:
            raise LicensedFeedError("contract_violation", "external_reference")
        return self._projection.project(
            self._descriptor,
            candidate,
            now=self._clock(),
        )

    def _request(self, page: int, *, timeout_seconds: float) -> FeedRequest:
        return FeedRequest(
            url=f"{self._endpoint_prefix}?page={page}",
            page=page,
            headers={},
            timeout_seconds=timeout_seconds,
        )

    def _raw_items(self, raw: bytes) -> tuple[_RawItemSlice, ...]:
        document, items = _json_item_slices(raw, self._item_path())
        if self._descriptor.data_class == "fixture":
            if not isinstance(document, dict):
                raise LicensedFeedError("contract_violation", "fixture_label")
            fixture = document.get("_fixture")
            if not isinstance(fixture, dict) or fixture.get("data_class") != "fixture":
                raise LicensedFeedError("contract_violation", "fixture_label")
            if not all(fixture.get(name) for name in ("citation_url", "access_date", "transcription_note")):
                raise LicensedFeedError("contract_violation", "fixture_citation")
        elif isinstance(document, dict) and "_fixture" in document:
            raise LicensedFeedError("contract_violation", "fixture_production_mixing")
        return items

    def _map_item(self, payload: object) -> NormalizedListing:
        if not isinstance(payload, Mapping):
            raise LicensedFeedError("payload_malformed")
        try:
            return self._map(payload)
        except LicensedFeedError:
            raise
        except (KeyError, TypeError, ValueError, AttributeError) as error:
            raise LicensedFeedError("payload_malformed") from error

    def _validate_candidate(self, candidate: NormalizedListing) -> None:
        if (
            not candidate.external_reference
            or not candidate.employer
            or not candidate.title
            or not candidate.locations
            or any(not isinstance(location, str) or not location.strip() for location in candidate.locations)
            or not candidate.application_url
            or not _hosts(candidate.application_url)
            or not isinstance(candidate.description, str)
            or candidate.data_class != self._descriptor.data_class
        ):
            raise LicensedFeedError("payload_malformed")

    def _item_path(self) -> tuple[str, ...]:
        raise NotImplementedError

    def _map(self, payload: Mapping[str, object]) -> NormalizedListing:
        raise NotImplementedError

    def _bounded_sleep(
        self,
        delay: float,
        start: float,
        receipts: list[SourceReceiptInput],
        pages: int,
        attempts: int,
        total_bytes: int,
        refusals: list[str],
    ) -> None:
        elapsed = self._monotonic() - start
        remaining = self._budget.max_seconds - elapsed
        if remaining <= 0:
            self._finish(receipts, pages, attempts, total_bytes, refusals, True)
            raise LicensedFeedError("budget_exhausted", "time")
        bounded_delay = max(delay, 0.0)
        self._sleeper(min(bounded_delay, remaining))
        if bounded_delay >= remaining:
            self._finish(receipts, pages, attempts, total_bytes, refusals, True)
            raise LicensedFeedError("budget_exhausted", "time")
        self._check_time(start, receipts, pages, attempts, total_bytes, refusals)

    def _check_time(
        self,
        start: float,
        receipts: list[SourceReceiptInput],
        pages: int,
        attempts: int,
        total_bytes: int,
        refusals: list[str],
    ) -> float:
        remaining = self._budget.max_seconds - (self._monotonic() - start)
        if remaining <= 0:
            self._finish(receipts, pages, attempts, total_bytes, refusals, True)
            raise LicensedFeedError("budget_exhausted", "time")
        return remaining

    def _finish(
        self,
        receipts: Sequence[SourceReceiptInput],
        pages: int,
        attempts: int,
        total_bytes: int,
        refusals: Sequence[str],
        truncated: bool,
    ) -> None:
        self.last_run = FeedRunOutcome(
            tuple(receipts),
            pages,
            attempts,
            total_bytes,
            tuple(refusals),
            truncated,
        )


class AggregatorFeedAdapter(FeedAdapterBase):
    _ENDPOINTS = {
        "adzuna": "https://api.adzuna.com/v1/api/jobs",
        "jooble": "https://jooble.org/api",
        "representative": "recorded://aggregator",
    }

    @classmethod
    def fixture(
        cls,
        *,
        policy_key: str,
        policy_version: int,
        policy_reader: PolicyReader,
        responses: Iterable[RawResponse],
        budget: FeedBudget | None = None,
        clock: Callable[[], datetime] | None = None,
        monotonic: Callable[[], float] | None = None,
        sleeper: Callable[[float], None] | None = None,
    ) -> "AggregatorFeedAdapter":
        descriptor = ConnectorDescriptor(
            "licensed:representative",
            LICENSED_AGGREGATOR,
            policy_key,
            policy_version,
            frozenset({"pull"}),
            ("recorded-fixture-only",),
            "representative",
            "representative-format",
            "fixture",
        )
        return cls(
            descriptor=descriptor,
            transport=RecordedTransport(responses),
            projection=RightsProjection(policy_reader),
            endpoint_prefix=cls._ENDPOINTS["representative"],
            budget=budget,
            clock=clock,
            monotonic=monotonic,
            sleeper=sleeper,
        )

    @classmethod
    def production(
        cls,
        environ: Mapping[str, str],
        *,
        policy_key: str,
        policy_version: int,
        policy_reader: PolicyReader,
        sender: Callable[[FeedRequest], RawResponse] | None,
        territory: str = "gb",
        budget: FeedBudget | None = None,
    ) -> "AggregatorFeedAdapter":
        settings = FeedSettings.resolve(environ, LICENSED_AGGREGATOR)
        provider = settings.value(AGGREGATOR_PROVIDER_SETTING).casefold()
        endpoint = cls._ENDPOINTS[provider]
        headers = {
            "X-PeerSlate-App-Id": settings.value(AGGREGATOR_APP_ID_SETTING),
            "Authorization": f"Bearer {settings.value(AGGREGATOR_API_KEY_SETTING)}",
        }
        descriptor = ConnectorDescriptor(
            f"licensed:{provider}",
            LICENSED_AGGREGATOR,
            policy_key,
            policy_version,
            frozenset({"pull"}),
            ("contract-rate-budget-required",),
            territory,
            provider,
            "production",
        )
        return cls(
            descriptor=descriptor,
            transport=LiveTransport(endpoint_prefix=endpoint, headers=headers, sender=sender),
            projection=RightsProjection(policy_reader),
            endpoint_prefix=endpoint,
            budget=_production_budget(
                budget,
                _GLOBAL_PRODUCTION_LIMIT,
                require_explicit=True,
            ),
            settings=settings,
        )

    def _item_path(self) -> tuple[str, ...]:
        product = self.describe().product
        if product in {"adzuna", "representative-format"}:
            return ("results",)
        if product == "jooble":
            return ("jobs",)
        raise LicensedFeedError("contract_violation", "response_shape")

    def _map(self, payload: Mapping[str, object]) -> NormalizedListing:
        company_value = payload["company"]
        location_value = payload["location"]
        company = company_value.get("display_name") if isinstance(company_value, dict) else company_value
        location = location_value.get("display_name") if isinstance(location_value, dict) else location_value
        description = _plain_text(payload.get("description") or payload.get("snippet"))
        application_url = _optional(payload.get("redirect_url") or payload.get("link")) or ""
        return NormalizedListing(
            external_reference=_optional(payload["id"]) or "",
            employer=_optional(company) or "",
            title=_optional(payload["title"]) or "",
            locations=(str(location),) if location else (),
            arrangement=_optional(payload.get("contract_type") or payload.get("type")),
            application_url=application_url,
            expected_application_hosts=_hosts(application_url),
            description=description,
            requirement_clauses=_requirements(payload.get("requirements"), description),
            fields=_fields(
                snippet=payload.get("snippet"),
                category=payload.get("category"),
                attribution=payload.get("attribution"),
            ),
            data_class=self.describe().data_class,
        )


class GovernmentFeedAdapter(FeedAdapterBase):
    _ENDPOINT = "https://data.usajobs.gov/api/search"

    @classmethod
    def fixture(
        cls,
        *,
        policy_key: str,
        policy_version: int,
        policy_reader: PolicyReader,
        responses: Iterable[RawResponse],
        budget: FeedBudget | None = None,
        clock: Callable[[], datetime] | None = None,
        monotonic: Callable[[], float] | None = None,
        sleeper: Callable[[float], None] | None = None,
    ) -> "GovernmentFeedAdapter":
        descriptor = ConnectorDescriptor(
            "government:usajobs",
            GOVERNMENT_FEED,
            policy_key,
            policy_version,
            frozenset({"pull", "closure_signal"}),
            ("recorded-fixture-only",),
            "US",
            "usajobs-documented-format",
            "fixture",
        )
        return cls(
            descriptor=descriptor,
            transport=RecordedTransport(responses),
            projection=RightsProjection(policy_reader),
            endpoint_prefix="recorded://government",
            budget=budget,
            clock=clock,
            monotonic=monotonic,
            sleeper=sleeper,
        )

    @classmethod
    def production(
        cls,
        environ: Mapping[str, str],
        *,
        policy_key: str,
        policy_version: int,
        policy_reader: PolicyReader,
        sender: Callable[[FeedRequest], RawResponse] | None,
        budget: FeedBudget | None = None,
    ) -> "GovernmentFeedAdapter":
        settings = FeedSettings.resolve(environ, GOVERNMENT_FEED)
        headers = {
            "Authorization-Key": settings.value(GOVERNMENT_API_KEY_SETTING),
            "User-Agent": settings.value(GOVERNMENT_EMAIL_SETTING),
        }
        descriptor = ConnectorDescriptor(
            "government:usajobs",
            GOVERNMENT_FEED,
            policy_key,
            policy_version,
            frozenset({"pull", "closure_signal"}),
            ("documented-rate-budget",),
            "US",
            "usajobs",
            "production",
        )
        return cls(
            descriptor=descriptor,
            transport=LiveTransport(endpoint_prefix=cls._ENDPOINT, headers=headers, sender=sender),
            projection=RightsProjection(policy_reader),
            endpoint_prefix=cls._ENDPOINT,
            budget=_production_budget(budget, _GOVERNMENT_PRODUCTION_LIMIT),
            settings=settings,
        )

    def _item_path(self) -> tuple[str, ...]:
        return ("SearchResult", "SearchResultItems")

    def _map(self, payload: Mapping[str, object]) -> NormalizedListing:
        external_reference = payload.get("MatchedObjectId")
        descriptor = payload.get("MatchedObjectDescriptor")
        if not isinstance(descriptor, Mapping):
            raise LicensedFeedError("payload_malformed")
        locations = descriptor.get("PositionLocation")
        if not isinstance(locations, list):
            raise LicensedFeedError("payload_malformed")
        details = descriptor.get("UserArea") or {}
        details = details.get("Details", {}) if isinstance(details, dict) else {}
        description = _plain_text(
            details.get("JobSummary") or descriptor.get("QualificationSummary")
        )
        requirements = details.get("Requirements") or descriptor.get("QualificationSummary")
        schedules = descriptor.get("PositionSchedule") or []
        schedule = schedules[0].get("Name") if schedules and isinstance(schedules[0], dict) else None
        application_url = _optional(descriptor["PositionURI"]) or ""
        return NormalizedListing(
            external_reference=_optional(external_reference) or "",
            employer=_optional(descriptor["OrganizationName"]) or "",
            title=_optional(descriptor["PositionTitle"]) or "",
            locations=tuple(
                _optional(item["LocationName"]) or ""
                for item in locations
                if isinstance(item, dict) and item.get("LocationName")
            ),
            arrangement=_optional(schedule),
            application_url=application_url,
            expected_application_hosts=_hosts(application_url),
            description=description,
            requirement_clauses=_requirements(requirements, description),
            fields=_fields(
                department=descriptor.get("DepartmentName"),
            ),
            data_class=self.describe().data_class,
        )


class DirectEmployerFeedAdapter(FeedAdapterBase):
    _ENDPOINTS = {
        "greenhouse": "https://boards-api.greenhouse.io/v1/boards",
        "lever": "https://api.lever.co/v0/postings",
    }

    def __init__(
        self,
        *,
        ats: str,
        board: str,
        employer: str | None = None,
        **kwargs: object,
    ) -> None:
        ats, board = _valid_board(ats, board)
        descriptor = kwargs.get("descriptor")
        settings = kwargs.get("settings")
        if (
            not isinstance(descriptor, ConnectorDescriptor)
            or descriptor.source_id != f"direct:{ats}:{board}"
            or descriptor.source_class != DIRECT_EMPLOYER
            or descriptor.product != ats
        ):
            raise LicensedFeedError("contract_violation", "direct_descriptor")
        if descriptor.data_class == "production":
            if employer is not None or not isinstance(settings, FeedSettings):
                raise LicensedFeedError("contract_violation", "employer_registration")
            employer = settings.direct_employer(ats, board)
            if employer is None:
                raise LicensedFeedError("policy_denied", DIRECT_BOARDS_SETTING)
        elif descriptor.data_class == "fixture":
            employer = _optional(employer)
            if not employer:
                raise LicensedFeedError("contract_violation", "employer_registration")
        else:
            raise LicensedFeedError("contract_violation", "data_class")
        self._ats = ats
        self._board = board
        self._employer = employer
        super().__init__(**kwargs)

    @classmethod
    def fixture(
        cls,
        *,
        ats: str,
        board: str,
        employer: str,
        policy_key: str,
        policy_version: int,
        policy_reader: PolicyReader,
        responses: Iterable[RawResponse],
        budget: FeedBudget | None = None,
        clock: Callable[[], datetime] | None = None,
        monotonic: Callable[[], float] | None = None,
        sleeper: Callable[[float], None] | None = None,
    ) -> "DirectEmployerFeedAdapter":
        ats, board = _valid_board(ats, board)
        employer = _optional(employer)
        if not employer:
            raise LicensedFeedError("contract_violation", "employer_registration")
        descriptor = ConnectorDescriptor(
            f"direct:{ats}:{board}",
            DIRECT_EMPLOYER,
            policy_key,
            policy_version,
            frozenset({"pull"}),
            ("recorded-fixture-only",),
            "employer-defined",
            ats,
            "fixture",
        )
        return cls(
            ats=ats,
            board=board,
            employer=employer,
            descriptor=descriptor,
            transport=RecordedTransport(responses),
            projection=RightsProjection(policy_reader),
            endpoint_prefix=f"recorded://direct/{ats}/{board}",
            budget=budget,
            clock=clock,
            monotonic=monotonic,
            sleeper=sleeper,
        )

    @classmethod
    def production(
        cls,
        environ: Mapping[str, str],
        *,
        ats: str,
        board: str,
        policy_key: str,
        policy_version: int,
        policy_reader: PolicyReader,
        sender: Callable[[FeedRequest], RawResponse] | None,
        budget: FeedBudget | None = None,
    ) -> "DirectEmployerFeedAdapter":
        ats, board = _valid_board(ats, board)
        settings = FeedSettings.resolve(environ, DIRECT_EMPLOYER)
        employer = settings.direct_employer(ats, board)
        if employer is None:
            raise LicensedFeedError("policy_denied", DIRECT_BOARDS_SETTING)
        endpoint = f"{cls._ENDPOINTS[ats]}/{board}"
        if ats == "greenhouse":
            endpoint += "/jobs"
        descriptor = ConnectorDescriptor(
            f"direct:{ats}:{board}",
            DIRECT_EMPLOYER,
            policy_key,
            policy_version,
            frozenset({"pull"}),
            ("conservative-fixed-budget",),
            "employer-defined",
            ats,
            "production",
        )
        return cls(
            ats=ats,
            board=board,
            descriptor=descriptor,
            transport=LiveTransport(endpoint_prefix=endpoint, headers={}, sender=sender),
            projection=RightsProjection(policy_reader),
            endpoint_prefix=endpoint,
            budget=_production_budget(budget, _DIRECT_PRODUCTION_LIMIT),
            settings=settings,
        )

    def _item_path(self) -> tuple[str, ...]:
        if self._ats == "greenhouse":
            return ("jobs",)
        if self.describe().data_class == "fixture":
            return ("postings",)
        return ()

    def _map(self, payload: Mapping[str, object]) -> NormalizedListing:
        if self._ats == "greenhouse":
            location = payload.get("location")
            location = location.get("name") if isinstance(location, dict) else location
            description = _plain_text(payload.get("content"))
            application_url = _optional(payload["absolute_url"]) or ""
            employer = self._employer or ""
            title = _optional(payload["title"]) or ""
            external_reference = _optional(payload["id"]) or ""
            arrangement = None
            departments = payload.get("departments") or []
            department = (
                departments[0].get("name")
                if isinstance(departments, list)
                and departments
                and isinstance(departments[0], Mapping)
                else None
            )
            fields = _fields(department=department)
        else:
            categories = payload.get("categories") or {}
            if not isinstance(categories, dict):
                raise LicensedFeedError("payload_malformed")
            location = categories.get("location")
            description = _plain_text(payload.get("descriptionPlain") or payload.get("description"))
            application_url = _optional(payload["hostedUrl"]) or ""
            employer = self._employer or ""
            title = _optional(payload["text"]) or ""
            external_reference = _optional(payload["id"]) or ""
            arrangement = _optional(categories.get("commitment"))
            fields = _fields(team=categories.get("team"))
        return NormalizedListing(
            external_reference=external_reference,
            employer=employer,
            title=title,
            locations=(str(location),) if location else (),
            arrangement=arrangement,
            application_url=application_url,
            expected_application_hosts=_hosts(application_url),
            description=description,
            requirement_clauses=_requirements(payload.get("requirements"), description),
            fields=fields,
            data_class=self.describe().data_class,
        )


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise LicensedFeedError("contract_violation", "time")
    return value.astimezone(timezone.utc)


def _optional(value: object) -> str | None:
    if value is not None and (
        not isinstance(value, (str, int, float)) or isinstance(value, bool)
    ):
        raise LicensedFeedError("payload_malformed")
    if isinstance(value, float) and not isfinite(value):
        raise LicensedFeedError("payload_malformed")
    text = " ".join(str(value or "").split()).strip()
    return text or None


def _fields(**values: object) -> dict[str, str]:
    return {
        key: " ".join(str(value).split()).strip()
        for key, value in values.items()
        if value not in (None, "", (), [], {})
    }


def _requirements(value: object, description: str) -> tuple[str, ...]:
    if isinstance(value, list):
        if any(not isinstance(item, str) for item in value):
            raise LicensedFeedError("payload_malformed")
        return tuple(text for item in value if (text := _plain_text(item)))
    if isinstance(value, str) and value.strip():
        lines = re.split(r"[\n\r]+|(?<=[.;])\s+", _plain_text(value))
    else:
        lines = re.split(r"[\n\r]+", description)
    return tuple(
        line
        for item in lines
        if (line := _optional(item))
        and re.search(r"\b(required|requirement|must|minimum|experience)\b", line, re.IGNORECASE)
    )


def _hosts(url: str) -> tuple[str, ...]:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        return ()
    return (parsed.hostname.rstrip(".").casefold(),)


class _PlainTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._suppressed_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        if tag.casefold() in {"script", "style"}:
            self._suppressed_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() in {"script", "style"} and self._suppressed_depth:
            self._suppressed_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._suppressed_depth:
            self.parts.append(data)


def _plain_text(value: object) -> str:
    parser = _PlainTextParser()
    parser.feed(str(value or ""))
    parser.close()
    return " ".join(" ".join(parser.parts).split()).strip()


def _valid_board(ats: str, board: str) -> tuple[str, str]:
    ats = ats.strip().casefold()
    board = board.strip().casefold()
    if ats not in {"greenhouse", "lever"} or not _SLUG_RE.fullmatch(board.replace("_", "-")):
        raise LicensedFeedError("contract_violation", DIRECT_BOARDS_SETTING)
    return ats, board


__all__ = [
    "AGGREGATOR_API_KEY_SETTING",
    "AGGREGATOR_APP_ID_SETTING",
    "AGGREGATOR_PROVIDER_SETTING",
    "AggregatorFeedAdapter",
    "DIRECT_BOARDS_SETTING",
    "DIRECT_EMPLOYER",
    "DirectEmployerFeedAdapter",
    "ExitManifest",
    "FeedAdapterBase",
    "FeedBudget",
    "FeedRequest",
    "FeedRunOutcome",
    "FeedSettings",
    "FeedTransport",
    "GOVERNMENT_API_KEY_SETTING",
    "GOVERNMENT_EMAIL_SETTING",
    "GOVERNMENT_FEED",
    "GovernmentFeedAdapter",
    "LICENSED_AGGREGATOR",
    "LicensedFeedError",
    "LiveTransport",
    "RawResponse",
    "RecordedTransport",
    "RightsProjection",
    "TerminationExitRehearsal",
]
