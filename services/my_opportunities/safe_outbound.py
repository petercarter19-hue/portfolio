"""Fail-closed outbound validation for C2 application-link probes.

The caller supplies both DNS resolution and transport.  Production networking is
therefore impossible until a later, separately owned adapter explicitly injects
one; all C2 tests use deterministic synthetic resolvers/transports.  Each hop is
resolved immediately before its connection and the selected numeric address is
passed to the transport, so the transport cannot silently perform a second,
unvalidated hostname resolution.
"""

from __future__ import annotations

import ipaddress
import socket
import time
from dataclasses import dataclass
from typing import Callable, Iterable, Mapping, Protocol
from urllib.parse import urljoin, urlsplit


MAX_REDIRECTS = 3
MAX_RESPONSE_BYTES = 512 * 1024
ALLOWED_CONTENT_TYPES = frozenset({"text/html", "text/plain"})
_METADATA_HOSTS = frozenset({"metadata.google.internal", "metadata", "instance-data"})


class SafeOutboundError(RuntimeError):
    """Stable, non-sensitive refusal/outage classification."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class OutboundRequest:
    url: str
    hostname: str
    address: str
    port: int
    headers: Mapping[str, str]
    timeout_seconds: float
    max_response_bytes: int


@dataclass(frozen=True)
class OutboundResponse:
    status: int
    headers: Mapping[str, str]
    body: bytes


@dataclass(frozen=True)
class SafeOutboundResult:
    url: str
    final_url: str
    final_hostname: str
    status: int
    content_type: str
    body: bytes
    redirects: int


class AddressResolver(Protocol):
    def __call__(self, hostname: str, port: int) -> Iterable[str]: ...


class OutboundTransport(Protocol):
    def __call__(self, request: OutboundRequest) -> OutboundResponse: ...


def system_resolver(hostname: str, port: int) -> Iterable[str]:
    """Resolve only; callers still need to inject a transport to connect."""

    return sorted(
        {item[4][0] for item in socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)}
    )


def _normalized_content_type(headers: Mapping[str, str]) -> str:
    for key, value in headers.items():
        if key.lower() == "content-type":
            return str(value).split(";", 1)[0].strip().lower()
    return ""


def _header(headers: Mapping[str, str], wanted: str) -> str | None:
    for key, value in headers.items():
        if key.lower() == wanted.lower():
            return str(value)
    return None


def _validated_url(value: str) -> tuple[str, str, int]:
    if not isinstance(value, str) or not value or len(value) > 2048:
        raise SafeOutboundError("invalid_url")
    parsed = urlsplit(value)
    if (
        parsed.scheme.lower() != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        raise SafeOutboundError("invalid_url")
    try:
        port = parsed.port or 443
    except ValueError as error:
        raise SafeOutboundError("invalid_url") from error
    if port != 443:
        raise SafeOutboundError("invalid_url")
    host = parsed.hostname.rstrip(".").lower()
    if host in _METADATA_HOSTS or host.endswith(".internal"):
        raise SafeOutboundError("unsafe_address")
    return parsed.geturl(), host, port


def _public_address(value: str) -> str:
    try:
        address = ipaddress.ip_address(value)
    except ValueError as error:
        raise SafeOutboundError("dns_unavailable") from error
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
        address = address.ipv4_mapped
    # is_global denies RFC1918, loopback, link-local, multicast, reserved,
    # unspecified, documentation, carrier-grade NAT, and cloud metadata IPs.
    if (
        not address.is_global
        or address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    ):
        raise SafeOutboundError("unsafe_address")
    return str(address)


class SafeOutboundClient:
    """Bounded, redirect-aware probe client with no credential channel."""

    def __init__(
        self,
        *,
        resolver: AddressResolver = system_resolver,
        transport: OutboundTransport | None = None,
        timeout_seconds: float = 5.0,
        total_timeout_seconds: float = 10.0,
        max_redirects: int = MAX_REDIRECTS,
        max_response_bytes: int = MAX_RESPONSE_BYTES,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if timeout_seconds <= 0 or total_timeout_seconds <= 0 or max_redirects < 0 or max_response_bytes < 1:
            raise ValueError("Safe outbound bounds must be positive.")
        self._resolver = resolver
        self._transport = transport
        self._timeout_seconds = timeout_seconds
        self._total_timeout_seconds = total_timeout_seconds
        self._max_redirects = max_redirects
        self._max_response_bytes = max_response_bytes
        self._clock = clock

    def resolve_for_connection(self, url: str) -> tuple[str, str, int, str]:
        """Resolve each target at connection time and deny every unsafe answer."""

        normalized, hostname, port = _validated_url(url)
        try:
            addresses = tuple(self._resolver(hostname, port))
        except TimeoutError as error:
            raise SafeOutboundError("timeout") from error
        except OSError as error:
            raise SafeOutboundError("dns_unavailable") from error
        if not addresses:
            raise SafeOutboundError("dns_unavailable")
        # Fail closed if *any* answer is unsafe. Choosing the first public answer
        # would leave a rebinding/mixed-answer route around the boundary.
        validated = tuple(_public_address(address) for address in addresses)
        return normalized, hostname, port, sorted(validated)[0]

    def fetch(self, url: str) -> SafeOutboundResult:
        if self._transport is None:
            raise SafeOutboundError("transport_disabled")
        initial_url = url
        current = url
        started = self._clock()
        for redirects in range(self._max_redirects + 1):
            if self._clock() - started > self._total_timeout_seconds:
                raise SafeOutboundError("timeout")
            normalized, hostname, port, address = self.resolve_for_connection(current)
            request = OutboundRequest(
                url=normalized,
                hostname=hostname,
                address=address,
                port=port,
                # No Cookie, Authorization, proxy authorization, or caller
                # headers are accepted. This is intentionally a new request.
                headers={"Accept": "text/html,text/plain", "User-Agent": "PeerSlate-MyOpp-LinkProbe/1.0"},
                timeout_seconds=self._timeout_seconds,
                max_response_bytes=self._max_response_bytes,
            )
            try:
                response = self._transport(request)
            except TimeoutError as error:
                raise SafeOutboundError("timeout") from error
            except OSError as error:
                raise SafeOutboundError("outage") from error
            if self._clock() - started > self._total_timeout_seconds:
                raise SafeOutboundError("timeout")
            if not isinstance(response, OutboundResponse):
                raise SafeOutboundError("outage")
            if len(response.body) > self._max_response_bytes:
                raise SafeOutboundError("response_too_large")
            if response.status in {301, 302, 303, 307, 308}:
                location = _header(response.headers, "location")
                if not location:
                    raise SafeOutboundError("redirect_denied")
                if redirects >= self._max_redirects:
                    raise SafeOutboundError("redirect_limit")
                current = urljoin(normalized, location)
                # The next loop resolves and validates the redirect target anew.
                continue
            content_type = _normalized_content_type(response.headers)
            if content_type not in ALLOWED_CONTENT_TYPES:
                raise SafeOutboundError("content_type")
            return SafeOutboundResult(
                url=initial_url,
                final_url=normalized,
                final_hostname=hostname,
                status=response.status,
                content_type=content_type,
                body=bytes(response.body),
                redirects=redirects,
            )
        raise SafeOutboundError("redirect_limit")
