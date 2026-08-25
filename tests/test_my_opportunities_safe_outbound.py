from __future__ import annotations

import unittest

from services.my_opportunities.safe_outbound import (
    OutboundResponse,
    SafeOutboundClient,
    SafeOutboundError,
)


class SafeOutboundTests(unittest.TestCase):
    def _client(self, resolver, transport, **kwargs):
        return SafeOutboundClient(resolver=resolver, transport=transport, **kwargs)

    def test_requires_https_no_credentials_standard_port_and_no_fragment(self):
        client = self._client(lambda *_: ["93.184.216.34"], lambda _: None)
        for value in (
            "http://careers.example/role",
            "https://user@careers.example/role",
            "https://careers.example:8443/role",
            "https://careers.example/role#fragment",
        ):
            with self.assertRaisesRegex(SafeOutboundError, "invalid_url"):
                client.resolve_for_connection(value)

    def test_denies_private_loopback_link_local_metadata_and_mapped_ipv6(self):
        for address in ("10.0.0.1", "127.0.0.1", "169.254.169.254", "::1", "::ffff:10.0.0.2", "224.0.0.1"):
            client = self._client(lambda *_: [address], lambda _: None)
            with self.assertRaisesRegex(SafeOutboundError, "unsafe_address"):
                client.resolve_for_connection("https://careers.example/role")
        client = self._client(lambda *_: ["93.184.216.34"], lambda _: None)
        with self.assertRaisesRegex(SafeOutboundError, "unsafe_address"):
            client.resolve_for_connection("https://metadata.google.internal/latest")

    def test_denies_mixed_dns_answers_and_revalidates_each_redirect_hop(self):
        calls = []
        def resolver(host, _port):
            calls.append(host)
            return ["93.184.216.34"] if host == "careers.example" else ["10.0.0.2"]
        def transport(request):
            return OutboundResponse(302, {"Location": "https://rebound.example/role"}, b"")
        with self.assertRaisesRegex(SafeOutboundError, "unsafe_address"):
            self._client(resolver, transport).fetch("https://careers.example/role")
        self.assertEqual(calls, ["careers.example", "rebound.example"])

        mixed = self._client(lambda *_: ["93.184.216.34", "10.0.0.2"], lambda _: None)
        with self.assertRaisesRegex(SafeOutboundError, "unsafe_address"):
            mixed.resolve_for_connection("https://careers.example/role")

    def test_redirect_budget_content_type_and_response_size_are_bounded(self):
        redirects = self._client(
            lambda *_: ["93.184.216.34"],
            lambda _request: OutboundResponse(302, {"Location": "https://careers.example/again"}, b""),
            max_redirects=1,
        )
        with self.assertRaisesRegex(SafeOutboundError, "redirect_limit"):
            redirects.fetch("https://careers.example/role")

        content_type = self._client(lambda *_: ["93.184.216.34"], lambda _: OutboundResponse(200, {"Content-Type": "application/pdf"}, b"x"))
        with self.assertRaisesRegex(SafeOutboundError, "content_type"):
            content_type.fetch("https://careers.example/role")

        too_large = self._client(lambda *_: ["93.184.216.34"], lambda _: OutboundResponse(200, {"Content-Type": "text/html"}, b"x" * 9), max_response_bytes=8)
        with self.assertRaisesRegex(SafeOutboundError, "response_too_large"):
            too_large.fetch("https://careers.example/role")

    def test_transport_is_fail_closed_and_outage_classes_are_stable(self):
        disabled = SafeOutboundClient(resolver=lambda *_: ["93.184.216.34"])
        with self.assertRaisesRegex(SafeOutboundError, "transport_disabled"):
            disabled.fetch("https://careers.example/role")
        for error, code in ((TimeoutError(), "timeout"), (OSError("down"), "outage")):
            client = self._client(lambda *_: ["93.184.216.34"], lambda _request, error=error: (_ for _ in ()).throw(error))
            with self.assertRaisesRegex(SafeOutboundError, code):
                client.fetch("https://careers.example/role")

    def test_total_wall_clock_budget_covers_all_redirect_hops(self):
        ticks = iter((0.0, 0.0, 3.0))
        client = SafeOutboundClient(
            resolver=lambda *_: ["93.184.216.34"],
            transport=lambda _request: OutboundResponse(200, {"Content-Type": "text/html"}, b"ok"),
            total_timeout_seconds=2.0,
            clock=lambda: next(ticks),
        )
        with self.assertRaisesRegex(SafeOutboundError, "timeout"):
            client.fetch("https://careers.example/role")

    def test_transport_receives_numeric_pinned_address_and_no_credentials_or_cookies(self):
        requests = []
        def transport(request):
            requests.append(request)
            return OutboundResponse(200, {"Content-Type": "text/html; charset=utf-8"}, b"ok")
        result = self._client(lambda *_: ["93.184.216.34"], transport).fetch("https://careers.example/role")
        self.assertEqual(result.final_hostname, "careers.example")
        request = requests[0]
        self.assertEqual(request.address, "93.184.216.34")
        self.assertNotIn("Cookie", request.headers)
        self.assertNotIn("Authorization", request.headers)
        self.assertEqual(set(request.headers), {"Accept", "User-Agent"})


if __name__ == "__main__":
    unittest.main()
