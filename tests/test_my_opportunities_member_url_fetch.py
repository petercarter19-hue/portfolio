"""P-1 recorded/offline proofs for C13's private member URL-fetch adapter."""

from __future__ import annotations

import ast
import hashlib
import importlib
import inspect
import multiprocessing
import os
import socket
import ssl
import subprocess
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import services.my_opportunities.member_url_fetch_service as url_fetch
from services.my_opportunities.member_import_service import (
    FETCH_MODULE,
    FLAG_SURFACE,
    FLAG_URL_FETCH,
    FetchRefused,
    FetchResult,
    HOST_CLASSES,
    HOST_CLASS_NOT_APPLICABLE,
    InMemoryAuditSink,
    InMemoryMemberImportRepository,
    MemberImportService,
    MemberImportServiceError,
    OUTCOME_BLOCKED,
    OUTCOME_DECODED,
    OUTCOME_EMPTY,
    OUTCOME_EXTRACTED,
    OUTCOME_FETCHED,
    OUTCOME_PARSED,
    OUTCOME_PARTIAL,
    OUTCOME_REFUSED,
    OUTCOME_TIMEOUT,
    REASON_CONTENT_MISMATCH,
    REASON_COULD_NOT_DECODE,
    REASON_DENIED_ADDRESS,
    REASON_FETCH_DEADLINE,
    REASON_FETCH_TOO_LARGE,
    REASON_HOSTILE_CHARACTERS,
    REASON_OUTPUT_TRUNCATED,
    REASON_REDIRECT_REFUSED,
    REASON_SCHEME_REFUSED,
    _FETCH_REFUSAL_OUTCOME,
    _default_adapter_resolver,
)
from services.my_opportunities.safe_outbound import OutboundRequest, OutboundResponse


ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 9, 2, 12, 0, 0, tzinfo=timezone.utc)
PUBLIC = "93.184.216.34"
C10_STOP_BASE_SHA = "9813ef8caea9a4984481397daf2044dd1cf1d59e"
C10_STOP_RETIREMENT_DIFF_SHA256 = (
    "0688dd6575367d9491a9636cd148c498cd89b1f2a7bf814c4a174bbcb81bd06a"
)

_NETWORK_PATCHES = ()


def _network_forbidden(*_args, **_kwargs):
    raise AssertionError("real_network_forbidden")


def _offline_dns_worker(connection, hostname, _port):
    try:
        if hostname == "slow.example":
            time.sleep(0.75)
        if hostname == "error.example":
            connection.send(("unavailable", ()))
        else:
            connection.send(("ok", (PUBLIC,)))
    except (BrokenPipeError, EOFError, OSError):
        pass
    finally:
        connection.close()


def setUpModule():
    global _NETWORK_PATCHES
    _NETWORK_PATCHES = (
        patch("socket.getaddrinfo", side_effect=_network_forbidden),
        patch("socket.create_connection", side_effect=_network_forbidden),
        patch("socket.socket.connect", side_effect=_network_forbidden),
    )
    for active_patch in _NETWORK_PATCHES:
        active_patch.start()


def tearDownModule():
    for active_patch in reversed(_NETWORK_PATCHES):
        active_patch.stop()


class FakeResolver:
    def __init__(self, answers=None, *, script=None):
        self.answers = answers or {}
        self.script = list(script or ())
        self.calls = []

    def __call__(self, hostname, port):
        self.calls.append((hostname, port))
        if self.script:
            item = self.script.pop(0)
        else:
            item = self.answers.get(hostname, (PUBLIC,))
        if isinstance(item, BaseException):
            raise item
        return tuple(item)


class FakeTransport:
    def __init__(self, *script):
        self.script = list(script)
        self.requests = []

    def __call__(self, request):
        self.requests.append(request)
        if not self.script:
            raise AssertionError("transport_script_exhausted")
        item = self.script.pop(0)
        if isinstance(item, BaseException):
            raise item
        if callable(item):
            return item(request)
        return item


def response(status=200, content_type="text/html", body=b"Role details", **headers):
    response_headers = dict(headers)
    if content_type is not None:
        response_headers["Content-Type"] = content_type
    return OutboundResponse(status, response_headers, body)


def adapter(*, resolver=None, transport=None, max_bytes=1024, monotonic=None, sniff=None):
    kwargs = {
        "resolver": resolver or FakeResolver(),
        "transport": transport or FakeTransport(response()),
        "clock": lambda: NOW,
        "monotonic_clock": monotonic or (lambda: 0.0),
        "limits": url_fetch.FetchLimits(
            hop_timeout_seconds=5.0,
            total_deadline_seconds=12.0,
            max_fetch_bytes=max_bytes,
            max_redirects=3,
        ),
    }
    if sniff is not None:
        kwargs["sniff"] = sniff
    return url_fetch.MemberUrlFetchAdapter(**kwargs)


class ServiceHarness(unittest.TestCase):
    def setUp(self):
        self.repository = InMemoryMemberImportRepository()
        self.sink = InMemoryAuditSink()
        self.counter = 0

    def key(self):
        self.counter += 1
        return f"url-fetch-{self.counter}"

    def service(self, fetch_adapter, *, flags=True):
        return MemberImportService(
            self.repository,
            self.sink,
            flag_reader=(lambda _name: flags) if isinstance(flags, bool) else flags,
            adapter_resolver=lambda: fetch_adapter,
        )


class SeamContractTests(unittest.TestCase):
    def test_factory_and_default_resolver_now_return_real_adapter_without_io(self):
        made = url_fetch.create_fetch_adapter()
        self.assertIsInstance(made, url_fetch.MemberUrlFetchAdapter)
        self.assertIsNone(made._resolver)
        self.assertIn("BoundedSystemResolver", inspect.getsource(made._fetch))
        self.assertIsInstance(_default_adapter_resolver(), url_fetch.MemberUrlFetchAdapter)
        self.assertIs(importlib.import_module(FETCH_MODULE), url_fetch)
        self.assertEqual(len(inspect.signature(url_fetch.create_fetch_adapter).parameters), 0)

    def test_result_uses_c10_contract_and_closed_success_host_class(self):
        result = adapter().fetch("https://careers.example/role")
        self.assertIsInstance(result, FetchResult)
        self.assertEqual(result.host_class, "public")
        self.assertIn(result.host_class, HOST_CLASSES)
        self.assertEqual(result.declared_content_type, "text/plain")

    def test_unexpected_internal_error_becomes_content_free_closed_failure(self):
        broken = adapter(resolver=FakeResolver(script=[ValueError("secret.example/path")]))
        with self.assertRaises(url_fetch.UrlFetchServiceError) as caught:
            broken.fetch("https://secret.example/path")
        self.assertEqual(caught.exception.failure_code, url_fetch.FAILURE_SOURCE_UNREACHABLE)
        self.assertTrue(caught.exception.recoverable)
        self.assertNotIn("secret", str(caught.exception))
        self.assertNotIn("secret", caught.exception.member_message)

    def test_invalid_time_configuration_fails_factory_closed_without_io(self):
        for value in ("0", "-1", "nan", "inf"):
            with self.subTest(value=value), patch.dict(
                os.environ,
                {"MYOPP_URL_FETCH_HOP_TIMEOUT_SECONDS": value},
            ):
                self.assertIsNone(_default_adapter_resolver())

    def test_every_refusal_uses_c10_closed_sets(self):
        cases = (
            adapter(),
            adapter(resolver=FakeResolver(script=[("127.0.0.1",)])),
            adapter(transport=FakeTransport(response(302, body=b"")) ),
            adapter(transport=FakeTransport(response(body=b"%PDF-1.4"))),
            adapter(transport=FakeTransport(TimeoutError())),
            adapter(transport=FakeTransport(response(body=b"x" * 9)), max_bytes=8),
        )
        urls = ("http://bad",) + ("https://careers.example/role",) * 5
        for candidate, value in zip(cases, urls):
            with self.subTest(value=value), self.assertRaises(FetchRefused) as caught:
                candidate.fetch(value)
            self.assertIn(caught.exception.reason, _FETCH_REFUSAL_OUTCOME)
            self.assertIn(caught.exception.host_class, HOST_CLASSES)


class NoNetworkGuardTests(ServiceHarness):
    def test_guard_is_armed(self):
        with self.assertRaisesRegex(AssertionError, "real_network_forbidden"):
            socket.create_connection((PUBLIC, 443))

    def test_import_and_factory_construction_open_no_socket(self):
        importlib.reload(url_fetch)
        made = url_fetch.create_fetch_adapter()
        self.assertIsInstance(made, url_fetch.MemberUrlFetchAdapter)

    def test_parent_or_fetch_flag_off_never_resolves_or_transports(self):
        resolver = FakeResolver()
        transport = FakeTransport(response())
        for enabled_flags, expected_reason in (
            (lambda _name: False, "surface_flag_off"),
            (lambda name: name == FLAG_SURFACE, "fetch_flag_off"),
        ):
            with self.subTest(reason=expected_reason):
                service = MemberImportService(
                    self.repository,
                    self.sink,
                    flag_reader=enabled_flags,
                    adapter_resolver=lambda: adapter(resolver=resolver, transport=transport),
                )
                with self.assertRaises(MemberImportServiceError):
                    service.import_from_url("alice", "https://careers.example/role", self.key(), now=NOW)
                self.assertEqual(self.sink.events[-1].reason_code, expected_reason)
        self.assertEqual(resolver.calls, [])
        self.assertEqual(transport.requests, [])


class BoundedDnsResolutionTests(unittest.TestCase):
    @staticmethod
    def process_context():
        method = "fork" if "fork" in multiprocessing.get_all_start_methods() else "spawn"
        return multiprocessing.get_context(method)

    def test_success_and_failure_are_content_free_and_children_are_reaped(self):
        before = {child.pid for child in multiprocessing.active_children()}
        resolver = url_fetch.BoundedSystemResolver(
            timeout_seconds=2.0,
            worker=_offline_dns_worker,
        )
        self.assertEqual(tuple(resolver("public.example", 443)), (PUBLIC,))
        with self.assertRaisesRegex(OSError, "dns_unavailable") as caught:
            tuple(resolver("error.example", 443))
        self.assertNotIn("error.example", str(caught.exception))
        self.assertEqual(
            {child.pid for child in multiprocessing.active_children()}, before
        )

    def test_slow_dns_is_terminated_inside_deadline_before_transport(self):
        before = {child.pid for child in multiprocessing.active_children()}
        resolver = url_fetch.BoundedSystemResolver(
            timeout_seconds=0.05,
            remaining_seconds=lambda: 0.05,
            process_context=self.process_context(),
            worker=_offline_dns_worker,
        )
        transport = FakeTransport(response())
        candidate = adapter(resolver=resolver, transport=transport)
        started = time.monotonic()
        with self.assertRaises(FetchRefused) as caught:
            candidate.fetch("https://slow.example/role")
        elapsed = time.monotonic() - started
        self.assertEqual(caught.exception.reason, REASON_FETCH_DEADLINE)
        self.assertEqual(caught.exception.host_class, HOST_CLASS_NOT_APPLICABLE)
        self.assertLess(elapsed, 0.5)
        self.assertEqual(transport.requests, [])
        self.assertEqual(
            {child.pid for child in multiprocessing.active_children()}, before
        )


class UrlAdmissionTests(unittest.TestCase):
    def test_https_ascii_standard_port_and_punycode_are_admitted(self):
        for value in (
            "https://example.com/role?x=1",
            "HTTPS://example.com:443/role",
            "https://xn--pple-43d.com/role",
            "https://127.0.0.1/role",
            "https://[::1]/role",
        ):
            with self.subTest(value=value):
                self.assertTrue(url_fetch.admit_url(value).admitted)

    def test_scheme_userinfo_fragment_port_and_bare_forms_are_refused(self):
        for value in (
            "http://example.com",
            "ftp://example.com",
            "file:///etc/passwd",
            "data:text/plain,x",
            "https://user:pw@example.com/role",
            "https://example.com/role#fragment",
            "https://example.com:8443/role",
            "https://example.com:0/role",
            "https:///role",
            "example.com/role",
        ):
            with self.subTest(value=value):
                self.assertFalse(url_fetch.admit_url(value).admitted)

    def test_control_whitespace_non_ascii_and_overlong_are_refused(self):
        for value in (
            "https://example.com/a b",
            "https://example.com/\r\nX: y",
            "https://аpple.com/role",
            "https://example.com/" + "x" * 2049,
        ):
            with self.subTest(value=value):
                admission = url_fetch.admit_url(value)
                self.assertFalse(admission.admitted)
                self.assertIsNone(admission.ascii_url)

    def test_every_admission_refusal_maps_before_dns(self):
        resolver = FakeResolver()
        with self.assertRaises(FetchRefused) as caught:
            adapter(resolver=resolver).fetch("javascript:alert(1)")
        self.assertEqual(caught.exception.reason, REASON_SCHEME_REFUSED)
        self.assertEqual(caught.exception.host_class, HOST_CLASS_NOT_APPLICABLE)
        self.assertEqual(resolver.calls, [])

    def test_ip_literal_and_obfuscated_hosts_are_decided_only_after_resolution(self):
        for value in (
            "https://127.0.0.1/role",
            "https://[::1]/role",
            "https://2130706433/role",
            "https://0x7f000001/role",
            "https://127.1/role",
            "https://0/role",
            "https://[::ffff:127.0.0.1]/role",
        ):
            resolver = FakeResolver(script=[("127.0.0.1",)])
            with self.subTest(value=value), self.assertRaises(FetchRefused) as caught:
                adapter(resolver=resolver).fetch(value)
            self.assertEqual(caught.exception.reason, REASON_DENIED_ADDRESS)
            self.assertEqual(caught.exception.host_class, "denied_loopback")
            self.assertEqual(len(resolver.calls), 1)


class AddressClassificationTests(unittest.TestCase):
    def test_denied_families_are_content_free_and_public_remains_public(self):
        cases = {
            "127.0.0.1": "denied_loopback",
            "::1": "denied_loopback",
            "10.0.0.1": "denied_private",
            "172.16.0.1": "denied_private",
            "192.168.1.1": "denied_private",
            "169.254.1.1": "denied_link_local",
            "fe80::1": "denied_link_local",
            "169.254.169.254": "denied_metadata",
            "100.64.0.1": "denied_cgnat",
            "fc00::1": "denied_ula",
            "0.0.0.0": "denied_other",
            "224.0.0.1": "denied_other",
            "192.0.2.1": "denied_other",
            "::ffff:127.0.0.1": "denied_loopback",
            "2002:0a00:0001::": "denied_private",
            "64:ff9b::a00:1": "denied_private",
            PUBLIC: "public",
            "::ffff:8.8.8.8": "public",
        }
        for value, expected in cases.items():
            with self.subTest(value=value):
                self.assertEqual(url_fetch.classify_address(value), expected)

    def test_metadata_hostname_classification_does_not_expose_name(self):
        for hostname in ("metadata", "metadata.google.internal", "foo.internal"):
            self.assertEqual(url_fetch.classify_hostname_refusal(hostname), "denied_metadata")


class DenySetMatrixTests(unittest.TestCase):
    def test_every_address_family_is_denied_before_transport(self):
        cases = (
            ("127.0.0.1", "denied_loopback"),
            ("10.2.3.4", "denied_private"),
            ("169.254.3.4", "denied_link_local"),
            ("169.254.169.254", "denied_metadata"),
            ("100.64.0.1", "denied_cgnat"),
            ("fd00::1", "denied_ula"),
            ("0.0.0.0", "denied_other"),
            ("::ffff:10.0.0.1", "denied_private"),
            ("2002:7f00:0001::1", "denied_loopback"),
            ("64:ff9b::a00:1", "denied_private"),
        )
        for address, expected in cases:
            transport = FakeTransport(response())
            with self.subTest(address=address), self.assertRaises(FetchRefused) as caught:
                adapter(
                    resolver=FakeResolver(script=[(address,)]), transport=transport
                ).fetch("https://careers.example/role")
            self.assertEqual(caught.exception.reason, REASON_DENIED_ADDRESS)
            self.assertEqual(caught.exception.host_class, expected)
            self.assertEqual(transport.requests, [])

    def test_metadata_name_and_mixed_answers_fail_closed(self):
        transport = FakeTransport(response())
        with self.assertRaises(FetchRefused) as metadata:
            adapter(transport=transport).fetch("https://metadata.google.internal/latest")
        self.assertEqual(metadata.exception.host_class, "denied_metadata")
        with self.assertRaises(FetchRefused) as mixed:
            adapter(
                resolver=FakeResolver(script=[(PUBLIC, "10.0.0.2")]), transport=transport
            ).fetch("https://careers.example/role")
        self.assertEqual(mixed.exception.host_class, "denied_private")
        self.assertEqual(transport.requests, [])


class DnsAndRedirectTests(unittest.TestCase):
    def test_redirect_re_resolves_and_private_second_hop_is_denied(self):
        resolver = FakeResolver(
            {"careers.example": (PUBLIC,), "rebound.example": ("10.0.0.2",)}
        )
        transport = FakeTransport(
            response(302, body=b"", Location="https://rebound.example/role")
        )
        with self.assertRaises(FetchRefused) as caught:
            adapter(resolver=resolver, transport=transport).fetch(
                "https://careers.example/role"
            )
        self.assertEqual(caught.exception.reason, REASON_DENIED_ADDRESS)
        self.assertEqual(caught.exception.host_class, "denied_private")
        self.assertEqual([call[0] for call in resolver.calls], ["careers.example", "rebound.example"])
        self.assertEqual(transport.requests[0].address, PUBLIC)

    def test_same_hostname_dns_rebinding_is_re_resolved_and_denied(self):
        resolver = FakeResolver(script=[(PUBLIC,), ("10.0.0.2",)])
        transport = FakeTransport(
            response(302, body=b"", Location="/second-hop"),
            response(body=b"must-not-be-read"),
        )
        with self.assertRaises(FetchRefused) as caught:
            adapter(resolver=resolver, transport=transport).fetch(
                "https://careers.example/first-hop"
            )
        self.assertEqual(caught.exception.reason, REASON_DENIED_ADDRESS)
        self.assertEqual(caught.exception.host_class, "denied_private")
        self.assertEqual(len(resolver.calls), 2)
        self.assertEqual(len(transport.requests), 1)

    def test_redirect_to_metadata_name_is_denied_as_metadata_without_resolving_it(self):
        resolver = FakeResolver()
        transport = FakeTransport(
            response(
                302,
                body=b"",
                Location="https://metadata.google.internal/latest",
            )
        )
        with self.assertRaises(FetchRefused) as caught:
            adapter(resolver=resolver, transport=transport).fetch(
                "https://careers.example/role"
            )
        self.assertEqual(caught.exception.reason, REASON_DENIED_ADDRESS)
        self.assertEqual(caught.exception.host_class, "denied_metadata")
        self.assertEqual([call[0] for call in resolver.calls], ["careers.example"])

    def test_public_redirect_records_final_url_and_final_address(self):
        second_address = "8.8.8.8"
        resolver = FakeResolver(
            {"careers.example": (PUBLIC,), "jobs.example": (second_address,)}
        )
        transport = FakeTransport(
            response(302, body=b"", Location="https://jobs.example/final"),
            response(body=b"Final role"),
        )
        result = adapter(resolver=resolver, transport=transport).fetch(
            "https://careers.example/role"
        )
        self.assertEqual(result.final_url, "https://jobs.example/final")
        self.assertEqual(result.resolved_address, second_address)
        self.assertEqual([item.address for item in transport.requests], [PUBLIC, second_address])

    def test_redirect_downgrade_missing_location_and_limit_are_closed(self):
        scripts = (
            (response(302, body=b"", Location="http://example.com/final"),),
            (response(302, body=b""),),
            tuple(response(302, body=b"", Location="/again") for _ in range(4)),
        )
        for script in scripts:
            with self.subTest(length=len(script)), self.assertRaises(FetchRefused) as caught:
                adapter(transport=FakeTransport(*script)).fetch("https://careers.example/role")
            self.assertEqual(caught.exception.reason, REASON_REDIRECT_REFUSED)
            self.assertEqual(caught.exception.host_class, "public")

    def test_non_ascii_and_control_redirects_refuse_before_second_dns(self):
        for location in (
            "https://exämple.com/role",
            "https://jobs.example/role with space",
            "https://jobs.example/role\r\nX: y",
            "https://jobs.example:0/role",
        ):
            resolver = FakeResolver()
            transport = FakeTransport(response(302, body=b"", Location=location))
            with self.subTest(location=location), self.assertRaises(FetchRefused) as caught:
                adapter(resolver=resolver, transport=transport).fetch(
                    "https://careers.example/role"
                )
            self.assertEqual(caught.exception.reason, REASON_REDIRECT_REFUSED)
            self.assertEqual([call[0] for call in resolver.calls], ["careers.example"])

    def test_no_resolution_is_reused_across_calls(self):
        resolver = FakeResolver(script=[(PUBLIC,), ("10.0.0.1",)])
        transport = FakeTransport(response(), response())
        candidate = adapter(resolver=resolver, transport=transport)
        candidate.fetch("https://careers.example/one")
        with self.assertRaises(FetchRefused):
            candidate.fetch("https://careers.example/two")
        self.assertEqual(len(resolver.calls), 2)


class MappingAndContentGateTests(unittest.TestCase):
    def test_size_and_timeout_map_to_closed_c10_outcomes(self):
        with self.assertRaises(FetchRefused) as too_large:
            adapter(transport=FakeTransport(response(body=b"123456789")), max_bytes=8).fetch(
                "https://careers.example/role"
            )
        self.assertEqual((too_large.exception.reason, too_large.exception.host_class), (REASON_FETCH_TOO_LARGE, "public"))
        with self.assertRaises(FetchRefused) as connect_timeout:
            adapter(transport=FakeTransport(TimeoutError())).fetch("https://careers.example/role")
        self.assertEqual((connect_timeout.exception.reason, connect_timeout.exception.host_class), (REASON_FETCH_DEADLINE, "public"))
        with self.assertRaises(FetchRefused) as dns_timeout:
            adapter(resolver=FakeResolver(script=[TimeoutError()])).fetch("https://careers.example/role")
        self.assertEqual(dns_timeout.exception.host_class, HOST_CLASS_NOT_APPLICABLE)

    def test_total_deadline_stops_a_later_hop_before_transport(self):
        ticks = iter((0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 13.0))
        transport = FakeTransport(
            response(302, body=b"", Location="https://jobs.example/next"),
            response(body=b"must-not-be-read"),
        )
        candidate = url_fetch.MemberUrlFetchAdapter(
            resolver=FakeResolver(),
            transport=transport,
            clock=lambda: NOW,
            monotonic_clock=lambda: next(ticks),
            limits=url_fetch.FetchLimits(
                hop_timeout_seconds=5.0,
                total_deadline_seconds=12.0,
                max_fetch_bytes=1024,
                max_redirects=3,
            ),
        )
        with self.assertRaises(FetchRefused) as caught:
            candidate.fetch("https://careers.example/role")
        self.assertEqual(caught.exception.reason, REASON_FETCH_DEADLINE)
        self.assertEqual(caught.exception.host_class, "public")
        self.assertEqual(len(transport.requests), 1)

    def test_dns_outage_and_source_statuses_have_three_pre_admission_codes(self):
        cases = (
            (adapter(resolver=FakeResolver(script=[OSError()])), url_fetch.FAILURE_SOURCE_UNREACHABLE),
            (adapter(transport=FakeTransport(OSError())), url_fetch.FAILURE_SOURCE_UNREACHABLE),
            (adapter(transport=FakeTransport(response(404, content_type=None))), url_fetch.FAILURE_SOURCE_NOT_FOUND),
            (adapter(transport=FakeTransport(response(410))), url_fetch.FAILURE_SOURCE_NOT_FOUND),
            (adapter(transport=FakeTransport(response(403))), url_fetch.FAILURE_SOURCE_REFUSED),
            (adapter(transport=FakeTransport(response(429))), url_fetch.FAILURE_SOURCE_REFUSED),
            (adapter(transport=FakeTransport(response(503, content_type=None))), url_fetch.FAILURE_SOURCE_REFUSED),
        )
        for candidate, code in cases:
            with self.subTest(code=code), self.assertRaises(url_fetch.UrlFetchServiceError) as caught:
                candidate.fetch("https://careers.example/secret-path")
            self.assertEqual(caught.exception.failure_code, code)
            self.assertTrue(caught.exception.recoverable)
            self.assertNotIn("secret-path", caught.exception.member_message)

    def test_non_200_success_binary_encoding_and_wrong_types_are_content_mismatch(self):
        cases = (
            response(203),
            response(content_type="application/pdf", body=b"%PDF-1.4"),
            response(content_type=None),
            response(body=b"%PDF-1.4"),
            response(body=b"PK\x03\x04zip"),
            response(body=b"MZbinary"),
            response(body=b"hello\x00world"),
            response(body=b"hello", **{"Content-Encoding": "gzip"}),
        )
        for item in cases:
            with self.subTest(status=item.status, headers=item.headers), self.assertRaises(FetchRefused) as caught:
                adapter(transport=FakeTransport(item)).fetch("https://careers.example/role")
            self.assertEqual(caught.exception.reason, REASON_CONTENT_MISMATCH)

    def test_html_declared_plain_and_plain_declared_html_both_enter_text_pipeline(self):
        for content_type, body in (
            ("text/html", b"<!doctype html><h1>Role</h1>"),
            ("text/plain", b"<html><body>Role</body></html>"),
            ("text/plain", b"Role"),
        ):
            result = adapter(transport=FakeTransport(response(content_type=content_type, body=body))).fetch(
                "https://careers.example/role"
            )
            self.assertEqual(result.declared_content_type, "text/plain")


class PipelineHandoffTests(ServiceHarness):
    def test_real_port_stores_sanitized_html_and_exact_provenance(self):
        wire = (
            b"<!doctype html><html><head><style>.x{}</style></head>"
            b"<body onload='steal()'><h1>Widget Engineer</h1>"
            b"<script>secret_canary()</script><p>Build safely.</p></body></html>"
        )
        fetch = adapter(transport=FakeTransport(response(body=wire)))
        service = self.service(fetch)
        receipt = service.import_from_url(
            "alice", "https://careers.example/role?token=private", self.key(), now=NOW
        )
        self.assertEqual(receipt.outcome, OUTCOME_EXTRACTED)
        record = service.get_import("alice", receipt.import_key, now=NOW)
        self.assertEqual(record.declared_content_type, "text/plain")
        self.assertEqual(record.byte_count, len(wire))
        self.assertEqual(record.content_hash, hashlib.sha256(wire).hexdigest())
        self.assertEqual(record.submitted_url, "https://careers.example/role?token=private")
        self.assertEqual(record.final_url, "https://careers.example/role?token=private")
        self.assertEqual(record.resolved_address, PUBLIC)
        self.assertEqual(record.fetched_at, NOW)
        self.assertIn("Widget Engineer", record.sanitized_text)
        self.assertNotIn("secret_canary", record.sanitized_text)
        self.assertNotIn("onload", record.sanitized_text)
        trail = service.stage_outcomes("alice", receipt.import_key)
        self.assertEqual(
            [stage.outcome for stage in trail],
            [OUTCOME_FETCHED, OUTCOME_DECODED, OUTCOME_PARSED, OUTCOME_EXTRACTED],
        )

    def test_deep_malformed_html_entity_bomb_is_bounded_and_sanitized(self):
        wire = (
            b"<!doctype html><html><body>"
            + b"<div>" * 180_000
            + b"<p>Role</p>"
            + b"&amp;" * 200_000
            + b"<script>private_parser_canary()</script>"
            + b"</span"
        )
        self.assertGreater(len(wire), 1_800_000)
        self.assertLess(len(wire), 2 * 1024 * 1024)
        fetch = adapter(
            transport=FakeTransport(response(body=wire)),
            max_bytes=len(wire) + 1,
        )
        service = self.service(fetch)
        started = time.monotonic()
        receipt = service.import_from_url(
            "alice", "https://careers.example/deep", self.key(), now=NOW
        )
        elapsed = time.monotonic() - started
        self.assertLess(elapsed, 5.0)
        self.assertEqual(
            (receipt.outcome, receipt.outcome_reason),
            (OUTCOME_PARTIAL, REASON_OUTPUT_TRUNCATED),
        )
        record = service.get_import("alice", receipt.import_key, now=NOW)
        self.assertIn("Role", record.sanitized_text)
        self.assertNotIn("private_parser_canary", record.sanitized_text)
        self.assertNotIn("<div", record.sanitized_text)
        self.assertNotIn("<script", record.sanitized_text)

    def test_decode_hostile_empty_and_truncation_states_remain_truthful(self):
        cases = (
            (b"caf\xe9", OUTCOME_REFUSED, REASON_COULD_NOT_DECODE),
            ("hello\u202e world".encode(), OUTCOME_REFUSED, REASON_HOSTILE_CHARACTERS),
            (b"<html><script>only</script></html>", OUTCOME_EMPTY, None),
            (b"<html>" + b"x" * 21000 + b"</html>", OUTCOME_PARTIAL, REASON_OUTPUT_TRUNCATED),
        )
        for wire, outcome, reason in cases:
            with self.subTest(outcome=outcome):
                service = self.service(adapter(transport=FakeTransport(response(body=wire)), max_bytes=30000))
                receipt = service.import_from_url(
                    "alice", "https://careers.example/role", self.key(), now=NOW
                )
                self.assertEqual((receipt.outcome, receipt.outcome_reason), (outcome, reason))

    def test_guarded_refusal_creates_reason_row_but_source_failure_creates_none(self):
        blocked_service = self.service(
            adapter(resolver=FakeResolver(script=[("10.0.0.1",)]))
        )
        blocked = blocked_service.import_from_url(
            "alice", "https://careers.example/role", self.key(), now=NOW
        )
        self.assertEqual((blocked.outcome, blocked.outcome_reason), (OUTCOME_BLOCKED, REASON_DENIED_ADDRESS))
        blocked_record = blocked_service.get_import("alice", blocked.import_key, now=NOW)
        self.assertIsNone(blocked_record.submitted_url)
        self.assertIsNone(blocked_record.resolved_address)

        before = self.repository.state_digest()
        failed_service = self.service(adapter(transport=FakeTransport(response(404))))
        key = self.key()
        with self.assertRaises(url_fetch.UrlFetchServiceError):
            failed_service.import_from_url(
                "alice", "https://careers.example/missing", key, now=NOW
            )
        self.assertEqual(self.repository.state_digest(), before)
        with self.assertRaises(url_fetch.UrlFetchServiceError):
            failed_service = self.service(adapter(transport=FakeTransport(response(404))))
            failed_service.import_from_url(
                "alice", "https://careers.example/missing", key, now=NOW
            )

    def test_cross_member_rows_and_receipts_never_cross(self):
        wire = b"Same role"
        transport = FakeTransport(response(body=wire), response(body=wire))
        fetch = adapter(transport=transport)
        service = self.service(fetch)
        alice = service.import_from_url("alice", "https://careers.example/role", self.key(), now=NOW)
        bob = service.import_from_url("bob", "https://careers.example/role", self.key(), now=NOW)
        self.assertEqual(len(transport.requests), 2)
        self.assertNotEqual(alice.import_key, bob.import_key)
        alice_record = service.get_import("alice", alice.import_key, now=NOW)
        bob_record = service.get_import("bob", bob.import_key, now=NOW)
        self.assertEqual(alice_record.sanitized_text, bob_record.sanitized_text)
        self.assertEqual(alice_record.content_hash, bob_record.content_hash)
        self.assertEqual(alice.outcome, bob.outcome)
        with self.assertRaisesRegex(MemberImportServiceError, "not_found"):
            service.get_import("bob", alice.import_key, now=NOW)
        self.assertEqual(len(service.list_imports("alice", now=NOW)), 1)
        self.assertEqual(len(service.list_imports("bob", now=NOW)), 1)

    def test_audit_and_exceptions_are_content_free(self):
        secret_url = "https://secret-host.example/private-path?token=value"
        service = self.service(adapter(resolver=FakeResolver(script=[("10.0.0.1",)])))
        service.import_from_url("alice", secret_url, self.key(), now=NOW)
        banned = ("secret-host", "private-path", "token", "value", "10.0.0.1")
        for event in self.sink.events:
            rendered = repr(event)
            for fragment in banned:
                self.assertNotIn(fragment, rendered)
        with self.assertRaises(url_fetch.UrlFetchServiceError) as caught:
            adapter(transport=FakeTransport(response(404))).fetch(secret_url)
        rendered = repr(vars(caught.exception)) + str(caught.exception)
        for fragment in banned:
            self.assertNotIn(fragment, rendered)


class IsolationRoutingProofTests(ServiceHarness):
    def test_future_pdf_handoff_via_port_reaches_c10_isolated_child(self):
        """Forward-only proof: C13 v1 itself cannot admit a PDF response."""

        class FuturePdfAdapter:
            def fetch(self, value):
                return FetchResult(
                    data=b"%PDF-1.4\nsynthetic",
                    declared_content_type="application/pdf",
                    submitted_url=value,
                    final_url=value,
                    resolved_address=PUBLIC,
                    fetched_at=NOW,
                    host_class="public",
                )

        completed = type(
            "Completed",
            (),
            {"returncode": 1, "stdout": b"", "stderr": b"private-content-canary"},
        )()
        service = self.service(FuturePdfAdapter())
        with patch(
            "services.my_opportunities.member_import_service.subprocess.run",
            return_value=completed,
        ) as isolated:
            receipt = service.import_from_url(
                "alice", "https://careers.example/future.pdf", self.key(), now=NOW
            )
        self.assertTrue(isolated.called)
        self.assertEqual(receipt.outcome, OUTCOME_REFUSED)
        self.assertEqual(receipt.outcome_reason, "parser_resource_bounds")
        self.assertNotIn("private-content-canary", repr(receipt))


class FlagTruthTableTests(ServiceHarness):
    def test_real_module_present_but_both_flags_are_required_and_rollback_is_immediate(self):
        state = {FLAG_SURFACE: True, FLAG_URL_FETCH: True}
        transport = FakeTransport(response(body=b"Role"))
        made = adapter(transport=transport)
        service = MemberImportService(
            self.repository,
            self.sink,
            flag_reader=lambda name: state[name],
            adapter_resolver=lambda: made,
        )
        self.assertEqual(
            service.import_from_url("alice", "https://careers.example/role", self.key(), now=NOW).outcome,
            OUTCOME_EXTRACTED,
        )
        state[FLAG_URL_FETCH] = False
        with self.assertRaisesRegex(MemberImportServiceError, "url_fetch_unavailable"):
            service.import_from_url("alice", "https://careers.example/other", self.key(), now=NOW)
        self.assertEqual(self.sink.events[-1].reason_code, "fetch_flag_off")
        self.assertEqual(len(transport.requests), 1)

    def test_absent_or_raising_factory_is_identical_adapter_absent(self):
        service = MemberImportService(
            self.repository, self.sink, flag_reader=lambda _name: True
        )
        original = importlib.import_module

        def absent(name, package=None):
            if name == FETCH_MODULE:
                raise ImportError("absent")
            return original(name, package)

        with patch("importlib.import_module", side_effect=absent):
            with self.assertRaises(MemberImportServiceError):
                service.import_from_url("alice", "https://careers.example/role", self.key(), now=NOW)
        self.assertEqual(self.sink.events[-1].reason_code, "adapter_absent")
        with patch.object(url_fetch, "create_fetch_adapter", side_effect=RuntimeError("broken")):
            with self.assertRaises(MemberImportServiceError):
                service.import_from_url("alice", "https://careers.example/role", self.key(), now=NOW)
        self.assertEqual(self.sink.events[-1].reason_code, "adapter_absent")


class FakeTlsSocket:
    def __init__(self):
        self.timeouts = []
        self.closed = False

    def settimeout(self, value):
        self.timeouts.append(value)

    def close(self):
        self.closed = True


class FakeSslContext:
    def __init__(self, tls_socket):
        self.tls_socket = tls_socket
        self.server_hostname = None
        self.raw_socket = None

    def wrap_socket(self, raw_socket, *, server_hostname):
        self.raw_socket = raw_socket
        self.server_hostname = server_hostname
        return self.tls_socket


class FakeHttpResponse:
    def __init__(self, status, headers, chunks):
        self.status = status
        self._headers = headers
        self._chunks = list(chunks)
        self.read_sizes = []

    def read(self, size):
        self.read_sizes.append(size)
        if not self._chunks:
            return b""
        return self._chunks.pop(0)

    def getheaders(self):
        return list(self._headers)


class FakeConnection:
    def __init__(self, response):
        self.response = response
        self.sock = None
        self.requests = []
        self.headers = []
        self.closed = False

    def putrequest(self, method, target, *, skip_host, skip_accept_encoding):
        self.requests.append((method, target, skip_host, skip_accept_encoding))
        if not skip_accept_encoding:
            self.headers.append(("Accept-Encoding", "identity"))

    def putheader(self, name, value):
        self.headers.append((name, value))

    def endheaders(self):
        return None

    def getresponse(self):
        return self.response

    def close(self):
        self.closed = True
        if self.sock is not None:
            self.sock.close()


class TransportTests(unittest.TestCase):
    def request(self, *, maximum=8):
        return OutboundRequest(
            url="https://careers.example/role?q=1",
            hostname="careers.example",
            address=PUBLIC,
            port=443,
            headers={"Accept": "text/html,text/plain", "User-Agent": "PeerSlate-test"},
            timeout_seconds=5.0,
            max_response_bytes=maximum,
        )

    def build(self, chunks, *, status=200, headers=None, clock=None):
        raw = FakeTlsSocket()
        tls = FakeTlsSocket()
        context = FakeSslContext(tls)
        response_value = FakeHttpResponse(
            status, headers or (("Content-Type", "text/html"),), chunks
        )
        connection = FakeConnection(response_value)
        connects = []

        def connect(target, *, timeout):
            connects.append((target, timeout))
            return raw

        def factory(*_args, **_kwargs):
            return connection

        transport = url_fetch.PinnedTlsTransport(
            connect=connect,
            tls_context_factory=lambda: context,
            clock=clock or (lambda: 0.0),
            connection_factory=factory,
        )
        return transport, raw, tls, context, response_value, connection, connects

    def test_connects_to_numeric_ip_uses_hostname_sni_and_fixed_headers_only(self):
        built = self.build([b"hello", b""])
        result = built[0](self.request())
        _transport, _raw, _tls, context, _response, connection, connects = built
        self.assertEqual(connects, [((PUBLIC, 443), 5.0)])
        self.assertEqual(context.server_hostname, "careers.example")
        self.assertEqual(connection.requests, [("GET", "/role?q=1", True, False)])
        self.assertEqual(
            set(connection.headers),
            {
                ("Accept-Encoding", "identity"),
                ("Host", "careers.example"),
                ("Accept", "text/html,text/plain"),
                ("User-Agent", "PeerSlate-test"),
            },
        )
        self.assertEqual(result.body, b"hello")
        self.assertTrue(connection.closed)

    def test_default_tls_context_requires_hostname_verification_and_tls12(self):
        context = url_fetch._default_ssl_context()
        self.assertTrue(context.check_hostname)
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        self.assertGreaterEqual(context.minimum_version, ssl.TLSVersion.TLSv1_2)

    def test_proxy_environment_is_ignored(self):
        built = self.build([b"ok", b""])
        with patch.dict(
            os.environ,
            {
                "HTTPS_PROXY": "http://proxy.invalid:8080",
                "HTTP_PROXY": "http://proxy.invalid:8080",
            },
        ):
            built[0](self.request())
        self.assertEqual(built[6], [((PUBLIC, 443), 5.0)])

    def test_reads_at_most_cap_plus_one_and_returns_redirect_unfollowed(self):
        built = self.build(
            [b"12345678", b"9", b"never"],
            status=302,
            headers=(("Location", "https://example.com/next"),),
        )
        result = built[0](self.request(maximum=8))
        self.assertEqual(result.status, 302)
        self.assertEqual(result.body, b"123456789")
        self.assertEqual(built[4].read_sizes, [9, 1])

    def test_trickle_deadline_and_protocol_errors_fail_closed_and_close(self):
        ticks = iter((0.0, 0.0, 0.0, 0.0, 6.0))
        built = self.build([b"x"], clock=lambda: next(ticks))
        with self.assertRaises(TimeoutError):
            built[0](self.request())
        self.assertTrue(built[5].closed)

        class BrokenConnection(FakeConnection):
            def getresponse(self):
                raise http_client_error("secret.example")

        original = built[5]
        broken = BrokenConnection(original.response)
        transport = url_fetch.PinnedTlsTransport(
            connect=lambda *_args, **_kwargs: built[1],
            tls_context_factory=lambda: built[3],
            clock=lambda: 0.0,
            connection_factory=lambda *_args, **_kwargs: broken,
        )
        with self.assertRaisesRegex(OSError, "transport_failure"):
            transport(self.request())
        self.assertTrue(broken.closed)


class http_client_error(Exception):
    pass


class MemberBudgetLedgerTests(unittest.TestCase):
    def test_one_concurrent_daily_budget_release_and_member_isolation(self):
        ledger = url_fetch.InMemoryFetchBudgetLedger(
            url_fetch.FetchBudgetPolicy(max_concurrent_per_member=1, daily_budget_per_member=2)
        )
        first = ledger.reserve("alice", now=NOW)
        self.assertEqual((first.code, first.allowed), (url_fetch.BUDGET_ALLOWED, True))
        in_progress = ledger.reserve("alice", now=NOW)
        self.assertEqual(in_progress.code, url_fetch.BUDGET_FETCH_IN_PROGRESS)
        self.assertGreaterEqual(in_progress.retry_after, 0)
        self.assertTrue(ledger.reserve("bob", now=NOW).allowed)
        ledger.release("alice")
        self.assertTrue(ledger.reserve("alice", now=NOW).allowed)
        ledger.release("alice")
        exhausted = ledger.reserve("alice", now=NOW)
        self.assertEqual(exhausted.code, url_fetch.BUDGET_EXHAUSTED)
        self.assertGreater(exhausted.retry_after, 0)

    def test_new_utc_day_resets_after_release(self):
        ledger = url_fetch.InMemoryFetchBudgetLedger(
            url_fetch.FetchBudgetPolicy(daily_budget_per_member=1)
        )
        self.assertTrue(ledger.reserve("alice", now=NOW).allowed)
        ledger.release("alice")
        self.assertTrue(ledger.reserve("alice", now=NOW + timedelta(days=1)).allowed)


class StructuralStopTests(unittest.TestCase):
    def test_module_has_no_forbidden_imports_or_module_level_mutable_collections(self):
        tree = ast.parse(inspect.getsource(url_fetch))
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)
        forbidden = ("requests", "urllib3", "urllib.request", "flask", "werkzeug", "anthropic", "openai", "logging")
        for imported in imports:
            for name in forbidden:
                self.assertNotIn(name, imported.lower())
        for name, value in vars(url_fetch).items():
            if name == "__builtins__":
                continue
            self.assertNotIsInstance(value, (dict, list, set), name)

    def test_safe_outbound_is_the_guard_boundary_and_no_real_network_appears_in_tests(self):
        source = inspect.getsource(url_fetch)
        self.assertIn("SafeOutboundClient", source)
        self.assertIn("client.fetch", source)
        test_source = Path(__file__).read_text(encoding="utf-8")
        self.assertNotIn("url" + "open(", test_source)
        self.assertNotIn("requests" + ".get", test_source)

    def test_only_the_three_named_c10_methods_are_removed(self):
        names = (
            "test_default_adapter_resolver_returns_none_because_module_is_absent",
            "test_member_url_fetch_service_module_does_not_exist",
            "test_member_url_fetch_service_module_absent_at_candidate",
        )
        current = (ROOT / "tests/test_my_opportunities_member_import.py").read_text(encoding="utf-8")
        baseline = subprocess.run(
            ["git", "show", f"{C10_STOP_BASE_SHA}:tests/test_my_opportunities_member_import.py"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        for name in names:
            self.assertIn(f"def {name}", baseline)
            self.assertNotIn(f"def {name}", current)
        diff = subprocess.run(
            [
                "git",
                "diff",
                "--no-ext-diff",
                "--full-index",
                "--unified=0",
                C10_STOP_BASE_SHA,
                "--",
                "tests/test_my_opportunities_member_import.py",
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        self.assertEqual(
            hashlib.sha256(diff.encode("utf-8")).hexdigest(),
            C10_STOP_RETIREMENT_DIFF_SHA256,
        )
        removed_defs = [line[1:].strip() for line in diff.splitlines() if line.startswith("-    def test_")]
        self.assertEqual(removed_defs, [f"def {name}(self):" for name in names])
        self.assertFalse(any(line.startswith("+") and not line.startswith("+++") for line in diff.splitlines()))

    def test_no_c2_or_c10_service_delta(self):
        changed = subprocess.run(
            ["git", "diff", "--name-only", "origin/main"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
        self.assertNotIn("services/my_opportunities/safe_outbound.py", changed)
        self.assertNotIn("services/my_opportunities/member_import_service.py", changed)


if __name__ == "__main__":
    unittest.main()
