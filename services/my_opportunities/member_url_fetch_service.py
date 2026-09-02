"""Bounded URL-fetch adapter for the private My Opportunities import port.

The adapter deliberately delegates URL, DNS, address, redirect, content-type,
size, and total-deadline policy to :mod:`safe_outbound`.  This module supplies
the final pinned-address TLS transport, a stricter pre-admission guard for
``http.client`` inputs, truthful C13 failure mapping, and an optional member
budget seam for the later HTTP package.  It has no route, cache, logger, AI,
credential input, or module-level network activity.
"""

from __future__ import annotations

import http.client
import ipaddress
import math
import multiprocessing
import os
import socket
import ssl
import threading
import time
from dataclasses import dataclass, replace
from datetime import date, datetime, time as datetime_time, timedelta, timezone
from types import MappingProxyType
from typing import Callable, Iterable, Mapping, Protocol
from urllib.parse import SplitResult, urljoin, urlsplit

from services.my_opportunities.member_import_service import (
    FetchRefused,
    FetchResult,
    HOST_CLASSES,
    HOST_CLASS_NOT_APPLICABLE,
    MemberImportServiceError,
    REASON_CONTENT_MISMATCH,
    REASON_DENIED_ADDRESS,
    REASON_FETCH_DEADLINE,
    REASON_FETCH_TOO_LARGE,
    REASON_REDIRECT_REFUSED,
    REASON_SCHEME_REFUSED,
)
from services.my_opportunities.safe_outbound import (
    MAX_REDIRECTS,
    AddressResolver,
    OutboundRequest,
    OutboundResponse,
    OutboundTransport,
    SafeOutboundClient,
    SafeOutboundError,
    system_resolver,
)


CONTRACT_VERSION = "1.0"
MAX_URL_LENGTH = 2048
READ_CHUNK_BYTES = 16 * 1024
MAX_CONCURRENT_FETCHES_PER_MEMBER = 1

_DEFAULT_HOP_TIMEOUT_SECONDS = 5.0
_DEFAULT_TOTAL_DEADLINE_SECONDS = 12.0
_DEFAULT_MAX_FETCH_BYTES = 2 * 1024 * 1024
_DEFAULT_DAILY_FETCH_BUDGET_PER_MEMBER = 50

ADMITTED_PIPELINE_TYPES = MappingProxyType(
    {"text/html": "text/plain", "text/plain": "text/plain"}
)

FAILURE_SOURCE_UNREACHABLE = "source_unreachable"
FAILURE_SOURCE_REFUSED = "source_refused"
FAILURE_SOURCE_NOT_FOUND = "source_not_found"
URL_FETCH_FAILURE_CODES = frozenset(
    {FAILURE_SOURCE_UNREACHABLE, FAILURE_SOURCE_REFUSED, FAILURE_SOURCE_NOT_FOUND}
)

BUDGET_ALLOWED = "allowed"
BUDGET_FETCH_IN_PROGRESS = "fetch_in_progress"
BUDGET_EXHAUSTED = "fetch_budget_exhausted"
BUDGET_VERDICTS = frozenset({BUDGET_ALLOWED, BUDGET_FETCH_IN_PROGRESS, BUDGET_EXHAUSTED})

_METADATA_HOSTS = frozenset({"metadata.google.internal", "metadata", "instance-data"})
_SOURCE_REFUSED_STATUSES = frozenset({401, 403, 407, 429, 451})
_SOURCE_NOT_FOUND_STATUSES = frozenset({404, 410})
_BINARY_KINDS = frozenset({"pdf", "zip", "elf", "exe", "binary"})
_RFC1918_NETWORKS = (
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
)
_LINK_LOCAL_V4 = ipaddress.ip_network("169.254.0.0/16")
_LINK_LOCAL_V6 = ipaddress.ip_network("fe80::/10")
_CGNAT = ipaddress.ip_network("100.64.0.0/10")
_ULA = ipaddress.ip_network("fc00::/7")
_NAT64 = ipaddress.ip_network("64:ff9b::/96")
_METADATA_ADDRESS = ipaddress.ip_address("169.254.169.254")


def _positive_float(name: str, default: float) -> float:
    value = float(os.environ.get(name, str(default)))
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name}_invalid")
    return value


def _positive_int(name: str, default: int) -> int:
    value = int(os.environ.get(name, str(default)))
    if value < 1:
        raise ValueError(f"{name}_invalid")
    return value


@dataclass(frozen=True)
class FetchLimits:
    hop_timeout_seconds: float = _DEFAULT_HOP_TIMEOUT_SECONDS
    total_deadline_seconds: float = _DEFAULT_TOTAL_DEADLINE_SECONDS
    max_fetch_bytes: int = _DEFAULT_MAX_FETCH_BYTES
    max_redirects: int = MAX_REDIRECTS

    def __post_init__(self) -> None:
        if (
            self.hop_timeout_seconds <= 0
            or not math.isfinite(self.hop_timeout_seconds)
            or self.total_deadline_seconds <= 0
            or not math.isfinite(self.total_deadline_seconds)
            or self.max_fetch_bytes < 1
            or self.max_redirects < 0
        ):
            raise ValueError("fetch_limits_invalid")


def _configured_limits() -> FetchLimits:
    return FetchLimits(
        hop_timeout_seconds=_positive_float(
            "MYOPP_URL_FETCH_HOP_TIMEOUT_SECONDS", _DEFAULT_HOP_TIMEOUT_SECONDS
        ),
        total_deadline_seconds=_positive_float(
            "MYOPP_URL_FETCH_TOTAL_DEADLINE_SECONDS", _DEFAULT_TOTAL_DEADLINE_SECONDS
        ),
        max_fetch_bytes=_positive_int(
            "MYOPP_URL_FETCH_MAX_BYTES", _DEFAULT_MAX_FETCH_BYTES
        ),
    )


_DNS_RESULT_OK = "ok"
_DNS_RESULT_TIMEOUT = "timeout"
_DNS_RESULT_UNAVAILABLE = "unavailable"
_MAX_DNS_ANSWERS = 64


def _system_resolver_process(connection, hostname: str, port: int) -> None:
    """Resolve in a disposable child without returning host/error text."""

    try:
        answers = tuple(system_resolver(hostname, port))
        if len(answers) > _MAX_DNS_ANSWERS or not all(
            isinstance(answer, str) for answer in answers
        ):
            payload = (_DNS_RESULT_UNAVAILABLE, ())
        else:
            payload = (_DNS_RESULT_OK, answers)
    except TimeoutError:
        payload = (_DNS_RESULT_TIMEOUT, ())
    except BaseException:
        payload = (_DNS_RESULT_UNAVAILABLE, ())
    try:
        connection.send(payload)
    except (BrokenPipeError, EOFError, OSError):
        pass
    finally:
        connection.close()


class BoundedSystemResolver:
    """Process-isolated system DNS with a hard per-call deadline and reap."""

    def __init__(
        self,
        *,
        timeout_seconds: float,
        remaining_seconds: Callable[[], float] | None = None,
        clock: Callable[[], float] = time.monotonic,
        process_context=None,
        worker: Callable[..., None] = _system_resolver_process,
    ) -> None:
        if timeout_seconds <= 0 or not math.isfinite(timeout_seconds):
            raise ValueError("dns_timeout_invalid")
        self._timeout_seconds = timeout_seconds
        self._remaining_seconds = remaining_seconds
        self._clock = clock
        self._process_context = process_context or multiprocessing.get_context("spawn")
        self._worker = worker

    @staticmethod
    def _reap(process) -> None:
        if process.pid is None:
            process.close()
            return
        process.join(timeout=0)
        if process.is_alive():
            process.terminate()
            process.join()
        process.close()

    def __call__(self, hostname: str, port: int) -> Iterable[str]:
        budget = self._timeout_seconds
        if self._remaining_seconds is not None:
            remaining = self._remaining_seconds()
            if not math.isfinite(remaining) or remaining <= 0:
                raise TimeoutError("dns_deadline")
            budget = min(budget, remaining)

        started = self._clock()
        deadline = started + budget
        receive_connection = None
        send_connection = None
        process = None
        try:
            receive_connection, send_connection = self._process_context.Pipe(duplex=False)
            process = self._process_context.Process(
                target=self._worker,
                args=(send_connection, hostname, port),
            )
            process.daemon = True
            process.start()
            send_connection.close()
            send_connection = None

            remaining = deadline - self._clock()
            if remaining <= 0 or not receive_connection.poll(remaining):
                raise TimeoutError("dns_deadline")
            try:
                payload = receive_connection.recv()
            except EOFError as error:
                raise OSError("dns_unavailable") from error
            if self._clock() > deadline:
                raise TimeoutError("dns_deadline")
            if (
                not isinstance(payload, tuple)
                or len(payload) != 2
                or not isinstance(payload[0], str)
                or not isinstance(payload[1], tuple)
            ):
                raise OSError("dns_unavailable")
            status, answers = payload
            if status == _DNS_RESULT_TIMEOUT:
                raise TimeoutError("dns_deadline")
            if status != _DNS_RESULT_OK or not all(
                isinstance(answer, str) for answer in answers
            ):
                raise OSError("dns_unavailable")
            return answers
        except (TimeoutError, OSError):
            raise
        except Exception as error:
            raise OSError("dns_unavailable") from error
        finally:
            if send_connection is not None:
                send_connection.close()
            if receive_connection is not None:
                receive_connection.close()
            if process is not None:
                self._reap(process)


@dataclass(frozen=True)
class UrlAdmission:
    admitted: bool
    kind: str
    ascii_url: str | None


def admit_url(url: object) -> UrlAdmission:
    """Perform the non-network checks needed before ``http.client`` sees a URL."""

    if not isinstance(url, str) or not url:
        return UrlAdmission(False, "invalid_type", None)
    if len(url) > MAX_URL_LENGTH:
        return UrlAdmission(False, "too_long", None)
    if any(ord(character) < 0x21 for character in url):
        return UrlAdmission(False, "control_char", None)
    if any(ord(character) > 0x7E for character in url):
        return UrlAdmission(False, "non_ascii", None)
    try:
        parsed = urlsplit(url)
    except (TypeError, ValueError):
        return UrlAdmission(False, "invalid_url", None)
    if parsed.scheme.lower() != "https":
        return UrlAdmission(False, "scheme", None)
    try:
        hostname = parsed.hostname
        port = parsed.port
    except ValueError:
        return UrlAdmission(False, "port", None)
    if not hostname:
        return UrlAdmission(False, "empty_host", None)
    if parsed.username is not None or parsed.password is not None:
        return UrlAdmission(False, "userinfo", None)
    if parsed.fragment:
        return UrlAdmission(False, "fragment", None)
    if port not in (None, 443):
        return UrlAdmission(False, "port", None)
    return UrlAdmission(True, "ok", parsed.geturl())


def _embedded_ipv4(address: ipaddress.IPv6Address) -> ipaddress.IPv4Address | None:
    if address.ipv4_mapped is not None:
        return address.ipv4_mapped
    if address.sixtofour is not None:
        return address.sixtofour
    if address.teredo is not None:
        return address.teredo[1]
    if address in _NAT64:
        return ipaddress.IPv4Address(int(address) & 0xFFFFFFFF)
    return None


def classify_address(value: str) -> str:
    """Label an already-refused address using C10's content-free host classes."""

    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return "denied_other"
    if isinstance(address, ipaddress.IPv6Address):
        embedded = _embedded_ipv4(address)
        if embedded is not None:
            address = embedded
    if address == _METADATA_ADDRESS:
        return "denied_metadata"
    if address.is_loopback:
        return "denied_loopback"
    if isinstance(address, ipaddress.IPv4Address) and any(
        address in network for network in _RFC1918_NETWORKS
    ):
        return "denied_private"
    if address in (_LINK_LOCAL_V4 if isinstance(address, ipaddress.IPv4Address) else _LINK_LOCAL_V6):
        return "denied_link_local"
    if isinstance(address, ipaddress.IPv4Address) and address in _CGNAT:
        return "denied_cgnat"
    if isinstance(address, ipaddress.IPv6Address) and address in _ULA:
        return "denied_ula"
    if (
        not address.is_global
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    ):
        return "denied_other"
    return "public"


def classify_hostname_refusal(hostname: str) -> str:
    normalized = hostname.rstrip(".").lower()
    if normalized in _METADATA_HOSTS or normalized.endswith(".internal"):
        return "denied_metadata"
    return "denied_other"


class UrlFetchServiceError(MemberImportServiceError):
    """Closed, content-free pre-admission failure for an unreachable source."""

    def __init__(self, failure_code: str) -> None:
        if failure_code not in URL_FETCH_FAILURE_CODES:
            failure_code = FAILURE_SOURCE_UNREACHABLE
        super().__init__(failure_code, recoverable=True)
        self.member_message = {
            FAILURE_SOURCE_UNREACHABLE: (
                "We couldn't reach that page. Paste the text or upload the file instead."
            ),
            FAILURE_SOURCE_REFUSED: (
                "That site wouldn't let PeerSlate read the page. Paste the text or upload the file instead."
            ),
            FAILURE_SOURCE_NOT_FOUND: (
                "That page couldn't be found. Paste the text or upload the file instead."
            ),
        }[failure_code]


class _RecordingResolver:
    def __init__(self, resolver: AddressResolver) -> None:
        self._resolver = resolver
        self.answers: tuple[tuple[str, ...], ...] = ()

    def __call__(self, hostname: str, port: int) -> Iterable[str]:
        try:
            resolved = tuple(self._resolver(hostname, port))
        except Exception:
            self.answers += ((),)
            raise
        self.answers += (resolved,)
        return resolved


class _RecordingTransport:
    def __init__(self, transport: OutboundTransport) -> None:
        self._transport = transport
        self.last_address: str | None = None
        self.last_request: OutboundRequest | None = None
        self.last_response: OutboundResponse | None = None
        self.responses_seen = 0
        self.invalid_redirect = False

    def __call__(self, request: OutboundRequest) -> OutboundResponse:
        self.last_address = request.address
        self.last_request = request
        response = self._transport(request)
        if isinstance(response, OutboundResponse):
            self.last_response = response
            self.responses_seen += 1
            if response.status in {301, 302, 303, 307, 308}:
                location = _header(response.headers, "location")
                if location:
                    try:
                        redirect_url = urljoin(request.url, location)
                    except (TypeError, ValueError):
                        redirect_url = ""
                    if not admit_url(redirect_url).admitted:
                        self.invalid_redirect = True
                        raise OSError("invalid_redirect")
        return response


class _DeadlineTransport:
    """Give each connection only the remaining whole-fetch time budget."""

    def __init__(
        self,
        transport: OutboundTransport,
        *,
        clock: Callable[[], float],
        started: float,
        total_seconds: float,
    ) -> None:
        self._transport = transport
        self._clock = clock
        self._started = started
        self._total_seconds = total_seconds

    def __call__(self, request: OutboundRequest) -> OutboundResponse:
        remaining = self._total_seconds - (self._clock() - self._started)
        if remaining <= 0:
            raise TimeoutError("fetch_deadline")
        bounded = replace(request, timeout_seconds=min(request.timeout_seconds, remaining))
        response = self._transport(bounded)
        if self._clock() - self._started > self._total_seconds:
            raise TimeoutError("fetch_deadline")
        return response


def _default_ssl_context() -> ssl.SSLContext:
    context = ssl.create_default_context()
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    return context


def _request_target(parsed: SplitResult) -> str:
    target = parsed.path or "/"
    if parsed.query:
        target = f"{target}?{parsed.query}"
    return target


def _first_headers(headers: Iterable[tuple[str, str]]) -> Mapping[str, str]:
    selected: dict[str, str] = {}
    seen: set[str] = set()
    for name, value in headers:
        lowered = name.lower()
        if lowered not in seen:
            selected[name] = value
            seen.add(lowered)
    return selected


class PinnedTlsTransport:
    """HTTPS GET transport that connects only to C2's validated numeric IP."""

    def __init__(
        self,
        *,
        connect: Callable[..., socket.socket] | None = None,
        tls_context_factory: Callable[[], ssl.SSLContext] = _default_ssl_context,
        clock: Callable[[], float] = time.monotonic,
        connection_factory: Callable[..., http.client.HTTPSConnection] = http.client.HTTPSConnection,
    ) -> None:
        self._connect = connect
        self._tls_context_factory = tls_context_factory
        self._clock = clock
        self._connection_factory = connection_factory

    def __call__(self, request: OutboundRequest) -> OutboundResponse:
        raw_socket = None
        tls_socket = None
        connection = None
        started = self._clock()

        def remaining_time() -> float:
            remaining = request.timeout_seconds - (self._clock() - started)
            if remaining <= 0:
                raise TimeoutError("fetch_deadline")
            return remaining

        try:
            connector = self._connect or socket.create_connection
            raw_socket = connector(
                (request.address, request.port), timeout=request.timeout_seconds
            )
            if hasattr(raw_socket, "settimeout"):
                raw_socket.settimeout(remaining_time())
            context = self._tls_context_factory()
            tls_socket = context.wrap_socket(raw_socket, server_hostname=request.hostname)
            if hasattr(tls_socket, "settimeout"):
                tls_socket.settimeout(remaining_time())
            connection = self._connection_factory(
                request.hostname,
                request.port,
                timeout=request.timeout_seconds,
                context=context,
            )
            connection.sock = tls_socket
            parsed = urlsplit(request.url)
            connection.putrequest(
                "GET", _request_target(parsed), skip_host=True, skip_accept_encoding=False
            )
            host_header = f"[{request.hostname}]" if ":" in request.hostname else request.hostname
            connection.putheader("Host", host_header)
            for name, value in request.headers.items():
                connection.putheader(name, value)
            connection.endheaders()
            if hasattr(tls_socket, "settimeout"):
                tls_socket.settimeout(remaining_time())
            response = connection.getresponse()

            body = bytearray()
            maximum_read = request.max_response_bytes + 1
            while len(body) < maximum_read:
                remaining = remaining_time()
                if hasattr(tls_socket, "settimeout"):
                    tls_socket.settimeout(remaining)
                remaining_bytes = maximum_read - len(body)
                chunk = response.read(min(READ_CHUNK_BYTES, remaining_bytes))
                if not chunk:
                    break
                body.extend(chunk[:remaining_bytes])
                if self._clock() - started > request.timeout_seconds:
                    raise TimeoutError("fetch_deadline")
            return OutboundResponse(
                status=int(response.status),
                headers=_first_headers(response.getheaders()),
                body=bytes(body),
            )
        except TimeoutError:
            raise
        except OSError:
            raise
        except Exception as error:
            raise OSError("transport_failure") from error
        finally:
            if connection is not None:
                connection.close()
            elif tls_socket is not None:
                tls_socket.close()
            elif raw_socket is not None:
                raw_socket.close()


def _header(headers: Mapping[str, str], wanted: str) -> str | None:
    for name, value in headers.items():
        if name.lower() == wanted.lower():
            return str(value)
    return None


def _sniff_kind(data: bytes) -> str:
    if data.startswith(b"%PDF-"):
        return "pdf"
    if data[:4] in (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"):
        return "zip"
    if data.startswith(b"\x7fELF"):
        return "elf"
    if data[:2] == b"MZ":
        return "exe"
    stripped = data[:4096].lstrip(b"\xef\xbb\xbf \t\r\n\x0c").lower()
    if stripped.startswith(b"<!doctype html") or stripped.startswith(b"<html"):
        return "html"
    if b"\x00" in data[:4096]:
        return "binary"
    return "text"


def _denied_class(resolver: _RecordingResolver) -> str:
    if resolver.answers:
        for answer in resolver.answers[-1]:
            classification = classify_address(answer)
            if classification != "public":
                return classification
    return "denied_other"


def _current_refusal_hostname(
    initial_hostname: str, transport: _RecordingTransport
) -> str:
    if transport.last_request is None or transport.last_response is None:
        return initial_hostname
    location = _header(transport.last_response.headers, "location")
    if not location:
        return initial_hostname
    try:
        redirected = urljoin(transport.last_request.url, location)
        return urlsplit(redirected).hostname or initial_hostname
    except (TypeError, ValueError):
        return initial_hostname


class MemberUrlFetchAdapter:
    def __init__(
        self,
        *,
        resolver: AddressResolver | None = None,
        transport: OutboundTransport | None = None,
        clock: Callable[[], datetime] | None = None,
        monotonic_clock: Callable[[], float] = time.monotonic,
        sniff: Callable[[bytes], str] = _sniff_kind,
        limits: FetchLimits | None = None,
    ) -> None:
        self._resolver = resolver
        self._transport = transport if transport is not None else PinnedTlsTransport()
        self._clock = clock if clock is not None else lambda: datetime.now(timezone.utc)
        self._monotonic_clock = monotonic_clock
        self._sniff = sniff
        self._limits = limits if limits is not None else _configured_limits()

    def _map_outbound_error(
        self,
        code: str,
        resolver: _RecordingResolver,
        transport: _RecordingTransport,
        hostname: str,
    ) -> None:
        recorded_status = (
            transport.last_response.status if transport.last_response is not None else None
        )
        if recorded_status in _SOURCE_NOT_FOUND_STATUSES:
            raise UrlFetchServiceError(FAILURE_SOURCE_NOT_FOUND)
        if (
            recorded_status in _SOURCE_REFUSED_STATUSES
            or recorded_status is not None
            and 400 <= recorded_status <= 599
        ):
            raise UrlFetchServiceError(FAILURE_SOURCE_REFUSED)
        if code == "invalid_url":
            if transport.responses_seen:
                raise FetchRefused(REASON_REDIRECT_REFUSED, "public")
            raise FetchRefused(REASON_SCHEME_REFUSED, HOST_CLASS_NOT_APPLICABLE)
        if code == "outage" and transport.invalid_redirect:
            raise FetchRefused(REASON_REDIRECT_REFUSED, "public")
        if code == "unsafe_address":
            has_answers_for_current_hop = len(resolver.answers) > transport.responses_seen
            host_class = (
                _denied_class(resolver)
                if has_answers_for_current_hop and resolver.answers[-1]
                else classify_hostname_refusal(
                    _current_refusal_hostname(hostname, transport)
                )
            )
            raise FetchRefused(REASON_DENIED_ADDRESS, host_class)
        if code in {"redirect_denied", "redirect_limit"}:
            raise FetchRefused(REASON_REDIRECT_REFUSED, "public")
        if code == "content_type":
            raise FetchRefused(REASON_CONTENT_MISMATCH, "public")
        if code == "response_too_large":
            raise FetchRefused(REASON_FETCH_TOO_LARGE, "public")
        if code == "timeout":
            host_class = "public" if transport.last_address is not None else HOST_CLASS_NOT_APPLICABLE
            raise FetchRefused(REASON_FETCH_DEADLINE, host_class)
        raise UrlFetchServiceError(FAILURE_SOURCE_UNREACHABLE)

    def _fetch(self, url: str) -> FetchResult:
        admission = admit_url(url)
        if not admission.admitted or admission.ascii_url is None:
            raise FetchRefused(REASON_SCHEME_REFUSED, HOST_CLASS_NOT_APPLICABLE)

        parsed = urlsplit(admission.ascii_url)
        hostname = parsed.hostname or ""
        fetch_started = self._monotonic_clock()
        resolver_source = self._resolver
        if resolver_source is None:
            resolver_source = BoundedSystemResolver(
                timeout_seconds=self._limits.hop_timeout_seconds,
                remaining_seconds=lambda: self._limits.total_deadline_seconds
                - (self._monotonic_clock() - fetch_started),
                clock=self._monotonic_clock,
            )
        resolver = _RecordingResolver(resolver_source)
        deadline_transport = _DeadlineTransport(
            self._transport,
            clock=self._monotonic_clock,
            started=fetch_started,
            total_seconds=self._limits.total_deadline_seconds,
        )
        transport = _RecordingTransport(deadline_transport)
        client = SafeOutboundClient(
            resolver=resolver,
            transport=transport,
            timeout_seconds=self._limits.hop_timeout_seconds,
            total_timeout_seconds=self._limits.total_deadline_seconds,
            max_redirects=self._limits.max_redirects,
            max_response_bytes=self._limits.max_fetch_bytes,
            clock=self._monotonic_clock,
        )
        outbound_error_code = None
        unexpected_failure = False
        result = None
        try:
            result = client.fetch(admission.ascii_url)
        except SafeOutboundError as error:
            outbound_error_code = error.code
        except Exception:
            unexpected_failure = True
        if unexpected_failure:
            raise UrlFetchServiceError(FAILURE_SOURCE_UNREACHABLE)
        if outbound_error_code is not None:
            self._map_outbound_error(outbound_error_code, resolver, transport, hostname)
        if result is None or transport.last_response is None or transport.last_address is None:
            raise UrlFetchServiceError(FAILURE_SOURCE_UNREACHABLE)

        status = result.status
        if status in _SOURCE_NOT_FOUND_STATUSES:
            raise UrlFetchServiceError(FAILURE_SOURCE_NOT_FOUND)
        if status in _SOURCE_REFUSED_STATUSES or 400 <= status <= 599:
            raise UrlFetchServiceError(FAILURE_SOURCE_REFUSED)
        if status != 200:
            raise FetchRefused(REASON_CONTENT_MISMATCH, "public")
        if _header(transport.last_response.headers, "content-encoding") is not None:
            raise FetchRefused(REASON_CONTENT_MISMATCH, "public")
        if self._sniff(result.body) in _BINARY_KINDS:
            raise FetchRefused(REASON_CONTENT_MISMATCH, "public")

        fetched_at = self._clock()
        if fetched_at.tzinfo is None:
            fetched_at = fetched_at.replace(tzinfo=timezone.utc)
        return FetchResult(
            data=result.body,
            declared_content_type=ADMITTED_PIPELINE_TYPES[result.content_type],
            submitted_url=admission.ascii_url,
            final_url=result.final_url,
            resolved_address=transport.last_address,
            fetched_at=fetched_at.astimezone(timezone.utc),
            host_class="public",
        )

    def fetch(self, url: str) -> FetchResult:
        try:
            return self._fetch(url)
        except (FetchRefused, UrlFetchServiceError):
            raise
        except Exception:
            pass
        raise UrlFetchServiceError(FAILURE_SOURCE_UNREACHABLE)


@dataclass(frozen=True)
class FetchBudgetPolicy:
    max_concurrent_per_member: int = MAX_CONCURRENT_FETCHES_PER_MEMBER
    daily_budget_per_member: int = _DEFAULT_DAILY_FETCH_BUDGET_PER_MEMBER

    def __post_init__(self) -> None:
        if self.max_concurrent_per_member < 1 or self.daily_budget_per_member < 1:
            raise ValueError("fetch_budget_policy_invalid")


@dataclass(frozen=True)
class BudgetVerdict:
    code: str
    allowed: bool
    retry_after: int | None = None

    def __post_init__(self) -> None:
        if self.code not in BUDGET_VERDICTS or self.allowed != (self.code == BUDGET_ALLOWED):
            raise ValueError("budget_verdict_invalid")
        if self.retry_after is not None and self.retry_after < 0:
            raise ValueError("retry_after_invalid")


class FetchBudgetLedger(Protocol):
    def reserve(self, user_key: str, *, now: datetime) -> BudgetVerdict: ...

    def release(self, user_key: str) -> None: ...


@dataclass
class _BudgetState:
    day: date
    used: int = 0
    active: int = 0


class InMemoryFetchBudgetLedger:
    """Per-process reference ledger; C8 must wire a durable equivalent."""

    def __init__(self, policy: FetchBudgetPolicy | None = None) -> None:
        self._policy = policy or FetchBudgetPolicy(
            daily_budget_per_member=_positive_int(
                "MYOPP_URL_FETCH_DAILY_BUDGET_PER_MEMBER",
                _DEFAULT_DAILY_FETCH_BUDGET_PER_MEMBER,
            )
        )
        self._states: dict[str, _BudgetState] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _normalized_now(now: datetime) -> datetime:
        if not isinstance(now, datetime):
            raise ValueError("now_invalid")
        if now.tzinfo is None:
            return now.replace(tzinfo=timezone.utc)
        return now.astimezone(timezone.utc)

    def reserve(self, user_key: str, *, now: datetime) -> BudgetVerdict:
        if not isinstance(user_key, str) or not user_key:
            raise ValueError("user_key_invalid")
        current = self._normalized_now(now)
        with self._lock:
            state = self._states.get(user_key)
            if state is None or (state.day != current.date() and state.active == 0):
                state = _BudgetState(current.date())
                self._states[user_key] = state
            if state.active >= self._policy.max_concurrent_per_member:
                return BudgetVerdict(BUDGET_FETCH_IN_PROGRESS, False, 1)
            if state.used >= self._policy.daily_budget_per_member:
                next_day = datetime.combine(
                    current.date() + timedelta(days=1), datetime_time.min, tzinfo=timezone.utc
                )
                retry_after = max(0, int((next_day - current).total_seconds()))
                return BudgetVerdict(BUDGET_EXHAUSTED, False, retry_after)
            state.used += 1
            state.active += 1
            return BudgetVerdict(BUDGET_ALLOWED, True)

    def release(self, user_key: str) -> None:
        if not isinstance(user_key, str) or not user_key:
            raise ValueError("user_key_invalid")
        with self._lock:
            state = self._states.get(user_key)
            if state is not None and state.active > 0:
                state.active -= 1


def create_fetch_adapter() -> MemberUrlFetchAdapter:
    """C10's only dynamic entry point; construction performs no I/O."""

    return MemberUrlFetchAdapter(transport=PinnedTlsTransport())


__all__ = (
    "ADMITTED_PIPELINE_TYPES",
    "BUDGET_ALLOWED",
    "BUDGET_EXHAUSTED",
    "BUDGET_FETCH_IN_PROGRESS",
    "BoundedSystemResolver",
    "BudgetVerdict",
    "CONTRACT_VERSION",
    "FAILURE_SOURCE_NOT_FOUND",
    "FAILURE_SOURCE_REFUSED",
    "FAILURE_SOURCE_UNREACHABLE",
    "FetchBudgetLedger",
    "FetchBudgetPolicy",
    "FetchLimits",
    "InMemoryFetchBudgetLedger",
    "MemberUrlFetchAdapter",
    "PinnedTlsTransport",
    "URL_FETCH_FAILURE_CODES",
    "UrlAdmission",
    "UrlFetchServiceError",
    "admit_url",
    "classify_address",
    "classify_hostname_refusal",
    "create_fetch_adapter",
)
