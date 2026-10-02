import unittest
from uuid import uuid4

from tools.local_reviewer.private_identity import PrivateAccessDenied, PrivateIdentity


class PrivateIdentityTests(unittest.TestCase):
    def setUp(self):
        self.identity = PrivateIdentity.from_config({
            "origin": "https://test-node.example-tail.ts.net:8443", "login": "owner@example.test",
            "owner": str(uuid4()), "display_name": "My test profile"})
        self.request = {"REMOTE_ADDR": "127.0.0.1", "HTTP_HOST": "test-node.example-tail.ts.net:8443",
                        "HTTP_X_FORWARDED_HOST": "test-node.example-tail.ts.net:8443",
                        "HTTP_X_FORWARDED_PROTO": "https", "HTTP_TAILSCALE_USER_LOGIN": "owner@example.test",
                        "REQUEST_METHOD": "GET"}

    def test_verified_edge_identity_uses_persistent_owner_not_selector_cookie(self):
        self.request["HTTP_COOKIE"] = "reviewer-fictional-owner=g-member-b; mvp1-synthetic-owner=g-member-c"
        self.assertEqual(self.identity.authorize(self.request), self.identity.owner)

    def test_private_profile_refuses_unverified_or_other_account_requests(self):
        changes = [{"HTTP_TAILSCALE_USER_LOGIN": "other@example.test"},
                   {"HTTP_TAILSCALE_USER_LOGIN": ""}, {"HTTP_HOST": "127.0.0.1:53720"},
                   {"REMOTE_ADDR": "100.64.0.2"}, {"HTTP_X_FORWARDED_PROTO": "http"},
                   {"HTTP_X_FORWARDED_HOST": "test-node.example-tail.ts.net:443"}]
        for change in changes:
            with self.subTest(change=change), self.assertRaises(PrivateAccessDenied):
                self.identity.authorize({**self.request, **change})

    def test_private_mutations_require_the_exact_https_origin(self):
        for origin in (None, "null", "https://other.example.test", "https://test-node.example-tail.ts.net"):
            with self.subTest(origin=origin), self.assertRaises(PrivateAccessDenied):
                request = {**self.request, "REQUEST_METHOD": "POST"}
                if origin is not None:
                    request["HTTP_ORIGIN"] = origin
                self.identity.authorize(request)
        self.assertEqual(self.identity.authorize({**self.request, "REQUEST_METHOD": "POST",
                         "HTTP_ORIGIN": self.identity.origin}), self.identity.owner)

    def test_cross_site_navigation_and_incomplete_configuration_refused(self):
        with self.assertRaises(PrivateAccessDenied):
            self.identity.authorize({**self.request, "HTTP_SEC_FETCH_SITE": "cross-site"})
        with self.assertRaises(ValueError):
            PrivateIdentity.from_config({"origin": self.identity.origin, "login": self.identity.login})


if __name__ == "__main__":
    unittest.main()
