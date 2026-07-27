import base64
from datetime import date
import json
import unittest
from unittest.mock import call, patch

from app import app
from services.database_service import ALLOWED_PROCEDURES, DatabaseServiceError


USER_KEY = "45ab728a-44bc-4f80-a79f-d010e04d5453"
CAPTURE_KEY = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
MOMENT_KEY = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
ROW_VERSION = bytes.fromhex("0000000000000012")
ROW_VERSION_TOKEN = "0000000000000012"


# A browser always sends at least one same-origin signal on a form post, and
# owner writes now require one. Model that here so the tests exercise the real
# request shape; the cross-site tests override these keys explicitly.
SAME_ORIGIN_HEADERS = {"Origin": "http://localhost", "Sec-Fetch-Site": "same-origin"}


def easy_auth_header(subject="moment-member"):
    principal = {
        "auth_typ": "aad",
        "claims": [
            {"typ": "iss", "val": "https://example.ciamlogin.com/example/v2.0/"},
            {"typ": "oid", "val": subject},
            {"typ": "name", "val": "Moment Member"},
            {"typ": "email", "val": "moment@example.com"},
        ],
    }
    encoded = base64.b64encode(json.dumps(principal).encode("utf-8")).decode(
        "ascii"
    )
    return {"X-MS-CLIENT-PRINCIPAL": encoded, **SAME_ORIGIN_HEADERS}


def identity_row():
    return {
        "account_key": USER_KEY,
        "user_key": USER_KEY,
        "display_name": "Moment Member",
        "email": "moment@example.com",
    }


def moment_row(**overrides):
    row = {
        "moment_key": MOMENT_KEY,
        "visibility": "private",
        "status": "proposal",
        "current_version_number": 2,
        "confirmed_version_number": None,
        "confirmed_at_utc": None,
        "created_at_utc": "2026-07-18T20:00:00Z",
        "updated_at_utc": "2026-07-18T20:10:00Z",
        "row_version": ROW_VERSION,
        "moment_kind": "achievement",
        "title": "Kept a critical project moving",
        "occurred_on": "2026-07-18",
        "occurred_precision": "exact",
        "narrative": "I clarified the decision and unblocked the delivery team.",
        "why_it_matters": "The team recovered a week of schedule risk.",
        "moment_source_key": "cccccccc-cccc-cccc-cccc-cccccccccccc",
        "source_capture_key": CAPTURE_KEY,
        "source_revision_key": "dddddddd-dddd-dddd-dddd-dddddddddddd",
        "source_revision_number": 1,
        "source_state": "available",
        "source_deleted_at_utc": None,
        "source_body": "I clarified the decision and helped unblock delivery.",
        "latest_source_revision_number": 2,
        "newer_source_available": True,
        "can_confirm": True,
    }
    row.update(overrides)
    return row


class OwnerMomentTests(unittest.TestCase):
    def setUp(self):
        self.original_config = {
            "TESTING": app.config.get("TESTING"),
            "PEERSLATE_ALLOW_DEV_IDENTITY": app.config.get(
                "PEERSLATE_ALLOW_DEV_IDENTITY"
            ),
            "PEERSLATE_DEV_USER_KEY": app.config.get("PEERSLATE_DEV_USER_KEY"),
            "PEERSLATE_TRUST_EASYAUTH_HEADERS": app.config.get(
                "PEERSLATE_TRUST_EASYAUTH_HEADERS"
            ),
            "PEERSLATE_AUTH_ISSUER": app.config.get("PEERSLATE_AUTH_ISSUER"),
        }
        app.config.update(
            TESTING=True,
            PEERSLATE_ALLOW_DEV_IDENTITY=False,
            PEERSLATE_DEV_USER_KEY=None,
            PEERSLATE_TRUST_EASYAUTH_HEADERS=False,
            PEERSLATE_AUTH_ISSUER=None,
        )
        self.client = app.test_client()

    def tearDown(self):
        app.config.update(self.original_config)

    def test_moment_procedures_are_explicitly_allowlisted(self):
        expected = {
            "usp_CreateOrReopenMomentProposal",
            "usp_GetMomentForOwner",
            "usp_SaveMomentProposal",
            "usp_ConfirmMoment",
            "usp_DiscardMomentProposal",
        }

        self.assertTrue(expected.issubset(ALLOWED_PROCEDURES))

    @patch("owner_routes.database_service.first_row")
    def test_anonymous_create_review_and_write_redirect_before_moment_calls(
        self, first_row
    ):
        # An anonymous visitor still arrives from a real browser, so the
        # same-origin signal is present and the sign-in redirect (not the
        # cross-site refusal) is the behaviour under test.
        create = self.client.post(
            f"/app/capture/{CAPTURE_KEY}/moment-proposal",
            data={"source_revision_number": "1"},
            headers=SAME_ORIGIN_HEADERS,
        )
        review = self.client.get(f"/app/moments/{MOMENT_KEY}/review")
        save = self.client.post(
            f"/app/moments/{MOMENT_KEY}/save",
            data={"expected_row_version": ROW_VERSION_TOKEN},
            headers=SAME_ORIGIN_HEADERS,
        )

        self.assertEqual(create.status_code, 302)
        self.assertEqual(review.status_code, 302)
        self.assertEqual(save.status_code, 302)
        self.assertEqual(create.headers["Location"], "/auth/sign-in?return_to=/app/capture")
        self.assertIn(
            f"return_to=/app/moments/{MOMENT_KEY}/review",
            review.headers["Location"],
        )
        self.assertIn(
            f"return_to=/app/moments/{MOMENT_KEY}/review",
            save.headers["Location"],
        )
        self.assertFalse(
            any(
                item.args and str(item.args[0]).startswith("usp_")
                and "Moment" in str(item.args[0])
                for item in first_row.call_args_list
            )
        )

    @patch("identity.database_service.first_row")
    def test_create_pins_selected_source_with_server_derived_owner(self, first_row):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True
        first_row.side_effect = [
            identity_row(),
            {"outcome": "created", "moment_key": MOMENT_KEY},
        ]

        response = self.client.post(
            f"/app/capture/{CAPTURE_KEY}/moment-proposal",
            data={"source_revision_number": "1", "owner_profile_id": "forged"},
            headers=easy_auth_header(),
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.headers["Location"], f"/app/moments/{MOMENT_KEY}/review"
        )
        self.assertEqual(
            first_row.call_args_list[-1],
            call(
                "usp_CreateOrReopenMomentProposal",
                [
                    ("@UserKey", USER_KEY),
                    ("@CaptureKey", CAPTURE_KEY),
                    ("@SourceRevisionNumber", 1),
                ],
            ),
        )

    @patch("identity.database_service.first_row")
    def test_create_reopens_existing_proposal_and_denial_is_generic(self, first_row):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True
        first_row.side_effect = [
            identity_row(),
            {"outcome": "existing", "moment_key": MOMENT_KEY},
            identity_row(),
            {"outcome": "not_found_or_changed", "moment_key": None},
        ]

        reopened = self.client.post(
            f"/app/capture/{CAPTURE_KEY}/moment-proposal",
            data={"source_revision_number": "0"},
            headers=easy_auth_header(),
        )
        denied = self.client.post(
            f"/app/capture/{CAPTURE_KEY}/moment-proposal",
            data={"source_revision_number": "0"},
            headers=easy_auth_header(),
        )

        self.assertEqual(
            reopened.headers["Location"], f"/app/moments/{MOMENT_KEY}/review"
        )
        self.assertEqual(denied.headers["Location"], "/app/capture?error=changed")

    @patch("identity.database_service.first_row")
    def test_review_separates_read_only_pinned_source_and_editable_proposal(
        self, first_row
    ):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True
        first_row.side_effect = [identity_row(), moment_row()]

        response = self.client.get(
            f"/app/moments/{MOMENT_KEY}/review", headers=easy_auth_header()
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.count(b'id="main-content"'), 1)
        self.assertIn(b"Pinned source", response.data)
        self.assertIn(b"Read-only", response.data)
        self.assertIn(b"Correction version 1", response.data)
        self.assertIn(b"A newer Capture correction exists", response.data)
        self.assertIn(b"Editable private proposal", response.data)
        self.assertIn(b'name="narrative"', response.data)
        self.assertIn(b'name="confirm_moment"', response.data)
        self.assertNotIn(
            b"Save valid required fields before confirmation becomes available.",
            response.data,
        )
        self.assertIn(b"Nothing leaves this private review", response.data)
        self.assertNotIn(b'name="user_key"', response.data)
        self.assertNotIn(b'name="owner_profile_id"', response.data)
        self.assertNotIn(b'name="visibility"', response.data)
        self.assertNotIn(b"Publish Moment", response.data)
        self.assertNotIn(b"Place in Journal", response.data)
        self.assertEqual(
            first_row.call_args_list[-1],
            call(
                "usp_GetMomentForOwner",
                [("@UserKey", USER_KEY), ("@MomentKey", MOMENT_KEY)],
            ),
        )

    @patch("identity.database_service.first_row")
    def test_invalid_or_source_deleted_proposal_disables_confirmation(
        self, first_row
    ):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True
        first_row.side_effect = [
            identity_row(),
            moment_row(
                title=None,
                narrative=None,
                can_confirm=False,
            ),
            identity_row(),
            moment_row(
                source_state="deleted",
                source_body=None,
                can_confirm=True,
            ),
        ]

        invalid = self.client.get(
            f"/app/moments/{MOMENT_KEY}/review", headers=easy_auth_header()
        )
        deleted = self.client.get(
            f"/app/moments/{MOMENT_KEY}/review", headers=easy_auth_header()
        )

        self.assertIn(
            b"Save valid required fields before confirmation becomes available.",
            invalid.data,
        )
        self.assertIn(
            b'name="confirm_moment" type="checkbox" value="confirm" required disabled',
            invalid.data,
        )
        self.assertIn(b"This unconfirmed proposal cannot be confirmed.", deleted.data)
        self.assertIn(
            b'name="confirm_moment" type="checkbox" value="confirm" required disabled',
            deleted.data,
        )

    @patch("identity.database_service.first_row")
    def test_confirmed_source_deleted_review_retains_only_approved_content(
        self, first_row
    ):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True
        first_row.side_effect = [
            identity_row(),
            moment_row(
                status="confirmed",
                confirmed_version_number=2,
                confirmed_at_utc="2026-07-18T20:20:00Z",
                source_state="deleted",
                source_deleted_at_utc="2026-07-18T20:30:00Z",
                source_body=None,
                newer_source_available=False,
                can_confirm=False,
            ),
        ]

        response = self.client.get(
            f"/app/moments/{MOMENT_KEY}/review", headers=easy_auth_header()
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Confirmed Moment", response.data)
        self.assertIn(b"Source deleted", response.data)
        self.assertIn(b"body-free source tombstone", response.data)
        self.assertIn(b"member-approved Moment is private canonical content", response.data)
        self.assertIn(b"I clarified the decision and unblocked", response.data)
        self.assertNotIn(b'name="narrative"', response.data)
        self.assertNotIn(b"Confirm private Moment", response.data)

    @patch("identity.database_service.first_row")
    def test_foreign_missing_or_discarded_review_is_generic_not_found(self, first_row):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True
        first_row.side_effect = [identity_row(), None]

        response = self.client.get(
            f"/app/moments/{MOMENT_KEY}/review", headers=easy_auth_header()
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_data(as_text=True), "Moment not found.")

    @patch("identity.database_service.first_row")
    def test_save_creates_normalized_private_proposal_version(self, first_row):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True
        first_row.side_effect = [identity_row(), {"outcome": "success"}]

        response = self.client.post(
            f"/app/moments/{MOMENT_KEY}/save",
            data={
                "expected_row_version": ROW_VERSION_TOKEN,
                "moment_kind": "achievement",
                "title": "  Kept a critical project moving  ",
                "occurred_on": "2026-07-18",
                "occurred_precision": "exact",
                "narrative": "  I clarified the decision.  ",
                "why_it_matters": "  It removed schedule risk.  ",
                "owner_profile_id": "forged",
            },
            headers=easy_auth_header(),
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.headers["Location"],
            f"/app/moments/{MOMENT_KEY}/review?changed=saved",
        )
        self.assertEqual(
            first_row.call_args_list[-1],
            call(
                "usp_SaveMomentProposal",
                [
                    ("@UserKey", USER_KEY),
                    ("@MomentKey", MOMENT_KEY),
                    ("@ExpectedRowVersion", ROW_VERSION),
                    ("@MomentKind", "achievement"),
                    ("@Title", "Kept a critical project moving"),
                    ("@OccurredOn", date(2026, 7, 18)),
                    ("@OccurredPrecision", "exact"),
                    ("@Narrative", "I clarified the decision."),
                    ("@WhyItMatters", "It removed schedule risk."),
                ],
            ),
        )

    @patch("identity.database_service.first_row")
    def test_invalid_fields_never_call_save_procedure(self, first_row):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True
        first_row.return_value = identity_row()

        required = self.client.post(
            f"/app/moments/{MOMENT_KEY}/save",
            data={
                "expected_row_version": ROW_VERSION_TOKEN,
                "moment_kind": "achievement",
                "title": "",
                "occurred_precision": "unknown",
                "narrative": "Narrative",
            },
            headers=easy_auth_header(),
        )
        too_long = self.client.post(
            f"/app/moments/{MOMENT_KEY}/save",
            data={
                "expected_row_version": ROW_VERSION_TOKEN,
                "moment_kind": "achievement",
                "title": "Title",
                "occurred_precision": "unknown",
                "narrative": "x" * 8001,
            },
            headers=easy_auth_header(),
        )
        invalid_date = self.client.post(
            f"/app/moments/{MOMENT_KEY}/save",
            data={
                "expected_row_version": ROW_VERSION_TOKEN,
                "moment_kind": "achievement",
                "title": "Title",
                "occurred_precision": "exact",
                "occurred_on": "not-a-date",
                "narrative": "Narrative",
            },
            headers=easy_auth_header(),
        )

        self.assertIn("error=required", required.headers["Location"])
        self.assertIn("error=too-long", too_long.headers["Location"])
        self.assertIn("error=date", invalid_date.headers["Location"])
        self.assertEqual(first_row.call_count, 3)

    @patch("identity.database_service.first_row")
    def test_stale_save_and_source_deleted_save_are_safe(self, first_row):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True
        first_row.side_effect = [
            identity_row(),
            {"outcome": "not_found_or_changed"},
            identity_row(),
            {"outcome": "source_deleted"},
        ]
        data = {
            "expected_row_version": ROW_VERSION_TOKEN,
            "moment_kind": "lesson",
            "title": "A private lesson",
            "occurred_precision": "unknown",
            "narrative": "I learned to clarify the decision earlier.",
        }

        stale = self.client.post(
            f"/app/moments/{MOMENT_KEY}/save",
            data=data,
            headers=easy_auth_header(),
        )
        deleted = self.client.post(
            f"/app/moments/{MOMENT_KEY}/save",
            data=data,
            headers=easy_auth_header(),
        )

        self.assertIn("error=changed", stale.headers["Location"])
        self.assertIn("error=source-deleted", deleted.headers["Location"])

    @patch("identity.database_service.first_row")
    def test_confirmation_requires_checkbox_current_tokens_and_owner(self, first_row):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True
        first_row.side_effect = [
            identity_row(),
            identity_row(),
            {"outcome": "success"},
        ]

        missing_confirmation = self.client.post(
            f"/app/moments/{MOMENT_KEY}/confirm",
            data={
                "expected_row_version": ROW_VERSION_TOKEN,
                "expected_proposal_version": "2",
            },
            headers=easy_auth_header(),
        )
        confirmed = self.client.post(
            f"/app/moments/{MOMENT_KEY}/confirm",
            data={
                "expected_row_version": ROW_VERSION_TOKEN,
                "expected_proposal_version": "2",
                "confirm_moment": "confirm",
                "user_key": "forged",
            },
            headers=easy_auth_header(),
        )

        self.assertIn("error=required", missing_confirmation.headers["Location"])
        self.assertIn("changed=confirmed", confirmed.headers["Location"])
        self.assertEqual(
            first_row.call_args_list[-1],
            call(
                "usp_ConfirmMoment",
                [
                    ("@UserKey", USER_KEY),
                    ("@MomentKey", MOMENT_KEY),
                    ("@ExpectedRowVersion", ROW_VERSION),
                    ("@ExpectedProposalVersion", 2),
                ],
            ),
        )

    @patch("identity.database_service.first_row")
    def test_source_deleted_unconfirmed_proposal_cannot_confirm(self, first_row):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True
        first_row.side_effect = [identity_row(), {"outcome": "source_deleted"}]

        response = self.client.post(
            f"/app/moments/{MOMENT_KEY}/confirm",
            data={
                "expected_row_version": ROW_VERSION_TOKEN,
                "expected_proposal_version": "2",
                "confirm_moment": "confirm",
            },
            headers=easy_auth_header(),
        )

        self.assertIn("error=source-deleted", response.headers["Location"])

    @patch("identity.database_service.first_row")
    def test_discard_requires_explicit_confirmation_and_removes_only_proposal(
        self, first_row
    ):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True
        first_row.side_effect = [
            identity_row(),
            identity_row(),
            {"outcome": "success"},
        ]

        missing = self.client.post(
            f"/app/moments/{MOMENT_KEY}/discard",
            data={"expected_row_version": ROW_VERSION_TOKEN},
            headers=easy_auth_header(),
        )
        discarded = self.client.post(
            f"/app/moments/{MOMENT_KEY}/discard",
            data={
                "expected_row_version": ROW_VERSION_TOKEN,
                "confirm_discard": "discard",
            },
            headers=easy_auth_header(),
        )

        self.assertIn("error=confirm-discard", missing.headers["Location"])
        self.assertEqual(
            discarded.headers["Location"], "/app/capture?changed=moment-discarded"
        )
        self.assertEqual(first_row.call_args_list[-1].args[0], "usp_DiscardMomentProposal")

    @patch("identity.database_service.first_row")
    def test_malformed_keys_versions_and_cross_site_writes_fail_before_mutation(
        self, first_row
    ):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True
        first_row.return_value = identity_row()

        bad_key = self.client.post(
            "/app/moments/not-a-key/save",
            data={"expected_row_version": ROW_VERSION_TOKEN},
            headers=easy_auth_header(),
        )
        bad_version = self.client.post(
            f"/app/moments/{MOMENT_KEY}/confirm",
            data={
                "expected_row_version": "forged",
                "expected_proposal_version": "2",
                "confirm_moment": "confirm",
            },
            headers=easy_auth_header(),
        )
        cross_site = self.client.post(
            f"/app/moments/{MOMENT_KEY}/discard",
            data={
                "expected_row_version": ROW_VERSION_TOKEN,
                "confirm_discard": "discard",
            },
            headers={
                **easy_auth_header(),
                "Origin": "https://attacker.example",
                "Sec-Fetch-Site": "cross-site",
            },
        )

        self.assertEqual(bad_key.status_code, 404)
        self.assertIn("error=changed", bad_version.headers["Location"])
        self.assertEqual(cross_site.status_code, 403)
        self.assertFalse(
            any(
                item.args and str(item.args[0]) in {
                    "usp_SaveMomentProposal",
                    "usp_ConfirmMoment",
                    "usp_DiscardMomentProposal",
                }
                for item in first_row.call_args_list
            )
        )

    @patch("identity.database_service.first_row")
    def test_database_failure_never_reports_false_success(self, first_row):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = True
        first_row.side_effect = [identity_row(), DatabaseServiceError("unavailable")]

        response = self.client.post(
            f"/app/capture/{CAPTURE_KEY}/moment-proposal",
            data={"source_revision_number": "1"},
            headers=easy_auth_header(),
        )

        self.assertEqual(response.status_code, 503)
        self.assertNotIn(b"Moment confirmed", response.data)


if __name__ == "__main__":
    unittest.main()
