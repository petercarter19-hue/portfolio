import base64
import json
import unittest
from unittest.mock import patch

from app import app
from identity import (
    AuthenticationPrincipalInvalid,
    AuthenticationRequired,
    IdentityMappingError,
    _meaningful_name,
    _resolve_display_name,
    get_current_identity,
    get_current_principal,
    get_optional_principal,
)


def name_claim(value):
    return {"typ": "name", "val": value}


def given_claim(value):
    return {"typ": "given_name", "val": value}


def easy_auth_header(subject="member-1", issuer="https://example.ciamlogin.com/example/v2.0/"):
    principal = {
        "auth_typ": "aad",
        "claims": [
            {"typ": "iss", "val": issuer},
            {"typ": "oid", "val": subject},
            {"typ": "name", "val": "Example Member"},
            {"typ": "email", "val": "member@example.com"},
        ],
    }
    encoded = base64.b64encode(json.dumps(principal).encode("utf-8")).decode("ascii")
    return {"X-MS-CLIENT-PRINCIPAL": encoded}


class MeaningfulNameTests(unittest.TestCase):
    def test_real_name_is_kept(self):
        self.assertEqual(_meaningful_name("Danielle Carter"), "Danielle Carter")

    def test_whitespace_is_trimmed(self):
        self.assertEqual(_meaningful_name("  Pete  "), "Pete")

    def test_blank_is_none(self):
        self.assertIsNone(_meaningful_name(""))
        self.assertIsNone(_meaningful_name("   "))
        self.assertIsNone(_meaningful_name(None))

    def test_placeholders_are_none_any_case(self):
        for placeholder in [
            "unknown",
            "Unknown",
            "UNKNOWN",
            "unknownuser",
            "Unknown User",
        ]:
            self.assertIsNone(_meaningful_name(placeholder))


class ResolveDisplayNameTests(unittest.TestCase):
    def test_prefers_real_name_claim(self):
        claims = [name_claim("Danielle Carter"), given_claim("Danielle")]
        self.assertEqual(
            _resolve_display_name(claims, "danielle@example.com"),
            "Danielle Carter",
        )

    def test_unknown_name_falls_back_to_given_name(self):
        claims = [name_claim("unknown"), given_claim("Danielle")]
        self.assertEqual(
            _resolve_display_name(claims, "danielle@example.com"),
            "Danielle",
        )

    def test_falls_back_to_email_local_part(self):
        claims = [name_claim("unknownuser")]
        self.assertEqual(
            _resolve_display_name(claims, "pete.carter@example.com"),
            "pete.carter",
        )

    def test_returns_none_when_nothing_usable(self):
        claims = [name_claim("unknown")]
        self.assertIsNone(_resolve_display_name(claims, None))

    def test_no_name_claims_at_all_uses_email(self):
        self.assertEqual(
            _resolve_display_name([], "member@example.com"),
            "member",
        )


class PrincipalIdentityBoundaryTests(unittest.TestCase):
    """Principal inspection must remain separate from account mapping SQL."""

    def setUp(self):
        self.original_config = {
            "TESTING": app.config.get("TESTING"),
            "PEERSLATE_TRUST_EASYAUTH_HEADERS": app.config.get(
                "PEERSLATE_TRUST_EASYAUTH_HEADERS"
            ),
            "PEERSLATE_ALLOW_DEV_IDENTITY": app.config.get(
                "PEERSLATE_ALLOW_DEV_IDENTITY"
            ),
            "PEERSLATE_DEV_USER_KEY": app.config.get("PEERSLATE_DEV_USER_KEY"),
            "PEERSLATE_AUTH_ISSUER": app.config.get("PEERSLATE_AUTH_ISSUER"),
        }
        app.config.update(
            TESTING=True,
            PEERSLATE_TRUST_EASYAUTH_HEADERS=True,
            PEERSLATE_ALLOW_DEV_IDENTITY=False,
            PEERSLATE_DEV_USER_KEY=None,
            PEERSLATE_AUTH_ISSUER=None,
        )

    def tearDown(self):
        app.config.update(self.original_config)

    def test_new_auth_exceptions_are_siblings_not_missing_authentication(self):
        self.assertFalse(issubclass(AuthenticationPrincipalInvalid, AuthenticationRequired))
        self.assertFalse(issubclass(IdentityMappingError, AuthenticationRequired))

    @patch("identity.database_service.first_row")
    def test_valid_principal_is_cached_without_database_access(self, first_row):
        with app.test_request_context("/", headers=easy_auth_header("member-a")):
            first = get_current_principal()
            second = get_optional_principal()

        self.assertIs(first, second)
        self.assertEqual(first.auth_subject, "member-a")
        first_row.assert_not_called()

    @patch("identity.database_service.first_row")
    def test_identity_maps_a_valid_principal_once_and_caches_the_result(self, first_row):
        first_row.return_value = {
            "account_key": "account-a",
            "user_key": "user-a",
            "display_name": "Account Member",
            "email": "account@example.com",
        }
        with app.test_request_context("/app", headers=easy_auth_header("member-a")):
            first = get_current_identity()
            second = get_current_identity()

        self.assertIs(first, second)
        self.assertEqual(first.user_key, "user-a")
        first_row.assert_called_once()

    @patch("identity.database_service.first_row", return_value=None)
    def test_valid_principal_with_no_account_row_is_a_mapping_error(self, first_row):
        with app.test_request_context("/app", headers=easy_auth_header("member-a")):
            with self.assertRaises(IdentityMappingError):
                get_current_identity()

        first_row.assert_called_once()

    @patch("identity.database_service.first_row")
    def test_malformed_principal_is_not_downgraded_to_optional_anonymous(self, first_row):
        with app.test_request_context(
            "/", headers={"X-MS-CLIENT-PRINCIPAL": "not-base64"}
        ):
            with self.assertRaises(AuthenticationPrincipalInvalid):
                get_optional_principal()

        first_row.assert_not_called()

    @patch("identity.database_service.first_row")
    def test_missing_trusted_principal_is_the_only_optional_anonymous_case(self, first_row):
        with app.test_request_context("/"):
            self.assertIsNone(get_optional_principal())
            with self.assertRaises(AuthenticationRequired):
                get_current_principal()

        first_row.assert_not_called()

    @patch("identity.database_service.first_row")
    def test_development_identity_stays_database_free(self, first_row):
        app.config.update(
            PEERSLATE_TRUST_EASYAUTH_HEADERS=False,
            PEERSLATE_DEV_USER_KEY="dev-member",
        )
        with app.test_request_context("/app"):
            principal = get_current_principal()
            identity = get_current_identity()

        self.assertTrue(principal.is_development)
        self.assertEqual(identity.user_key, "dev-member")
        first_row.assert_not_called()


if __name__ == "__main__":
    unittest.main()
