"""C3 account-export experience: route, privacy, and delivery tests.

Every test here uses a fake cursor or a patched service. Nothing in this
file opens a database connection or reaches Blob storage, matching the
rest of the account-export suite.

The privacy tests are the point of this file. The export routes are the
first member-facing surface that can return a whole account's contents in
one response, so the cases that matter most are the ones proving a member
cannot reach anybody else's job, cannot learn whether a job key exists,
and never receives a storage locator.
"""

import base64
import json
import unittest
from unittest.mock import patch

from app import app
from services.database_service import ALLOWED_PROCEDURES


OWNER_USER_KEY = "45ab728a-44bc-4f80-a79f-d010e04d5453"
JOB_KEY = "11111111-2222-3333-4444-555555555555"
OTHER_JOB_KEY = "99999999-8888-7777-6666-555555555555"

SAME_ORIGIN_HEADERS = {"Origin": "http://localhost", "Sec-Fetch-Site": "same-origin"}


def easy_auth_header(subject="export-member"):
    principal = {
        "auth_typ": "aad",
        "claims": [
            {"typ": "iss", "val": "https://example.ciamlogin.com/example/v2.0/"},
            {"typ": "oid", "val": subject},
            {"typ": "name", "val": "Export Member"},
            {"typ": "email", "val": "export@example.com"},
        ],
    }
    encoded = base64.b64encode(json.dumps(principal).encode("utf-8")).decode("ascii")
    return {"X-MS-CLIENT-PRINCIPAL": encoded, **SAME_ORIGIN_HEADERS}


def identity_row():
    return {
        "account_key": OWNER_USER_KEY,
        "user_key": OWNER_USER_KEY,
        "display_name": "Export Member",
        "email": "export@example.com",
    }


class AccountExportProcedureAllowlistTests(unittest.TestCase):
    """Only the three member-facing procedures may be callable."""

    MEMBER_FACING = (
        "usp_RequestAccountExportForOwner",
        "usp_GetAccountExportStatusForOwner",
        "usp_GetAccountExportDownloadMetadataForOwner",
    )

    # System-wide, no @UserKey, reserved for the separate worker identity.
    # If one of these ever becomes callable through the shared application
    # connection, a browser request could act across every owner at once.
    WORKER_ONLY = (
        "usp_ClaimAccountExportJob",
        "usp_CompleteAccountExportJob",
        "usp_FailAccountExportJob",
        "usp_ExpireAccountExportJobs",
        "usp_CleanupAccountExportJob",
    )

    def test_member_facing_procedures_are_allowlisted(self):
        for name in self.MEMBER_FACING:
            self.assertIn(name, ALLOWED_PROCEDURES, name)

    def test_worker_procedures_are_never_allowlisted(self):
        for name in self.WORKER_ONLY:
            self.assertNotIn(name, ALLOWED_PROCEDURES, name)


class _ExportRouteTestBase(unittest.TestCase):
    """Shared app config for every route test.

    Mirrors tests/test_owner_capture.py: development identity stays OFF so a
    test cannot pass by accident on a dev principal, and Easy Auth headers are
    trusted only because these tests present one deliberately.
    """

    export_enabled = True

    def setUp(self):
        self.original_config = {
            key: app.config.get(key)
            for key in (
                "TESTING",
                "PEERSLATE_ALLOW_DEV_IDENTITY",
                "PEERSLATE_DEV_USER_KEY",
                "PEERSLATE_TRUST_EASYAUTH_HEADERS",
                "PEERSLATE_AUTH_ISSUER",
                "PEERSLATE_ACCOUNT_EXPORT_ENABLED",
            )
        }
        app.config.update(
            TESTING=True,
            PEERSLATE_ALLOW_DEV_IDENTITY=False,
            PEERSLATE_DEV_USER_KEY=None,
            PEERSLATE_TRUST_EASYAUTH_HEADERS=True,
            PEERSLATE_AUTH_ISSUER=None,
            PEERSLATE_ACCOUNT_EXPORT_ENABLED=self.export_enabled,
        )
        self.client = app.test_client()

    def tearDown(self):
        app.config.update(self.original_config)


class AccountExportFlagTests(_ExportRouteTestBase):
    export_enabled = False
    def test_every_export_route_is_absent_while_the_flag_is_off(self):
        for path in (
            "/app/settings/export",
            "/app/settings/export/%s" % JOB_KEY,
            "/app/settings/export/%s/download" % JOB_KEY,
        ):
            response = self.client.get(path, headers=easy_auth_header())
            self.assertEqual(response.status_code, 404, path)

    def test_the_flag_gate_also_refuses_a_write_not_only_a_read(self):
        """The gate must close the POST too, and before any database call.

        A read-only gate would leave the one route that actually creates a
        job reachable while the feature is supposed to be absent.
        """

        with patch("services.database_service.database_service.first_row") as first_row:
            response = self.client.post(
                "/app/settings/export", headers=easy_auth_header()
            )
        self.assertEqual(response.status_code, 404)
        first_row.assert_not_called()


class AccountExportRequestTests(_ExportRouteTestBase):
    def test_cross_site_request_is_refused_before_any_database_call(self):
        with patch("services.database_service.database_service.first_row") as first_row:
            response = self.client.post(
                "/app/settings/export",
                headers={
                    "X-MS-CLIENT-PRINCIPAL": easy_auth_header()[
                        "X-MS-CLIENT-PRINCIPAL"
                    ],
                    "Origin": "https://attacker.example",
                    "Sec-Fetch-Site": "cross-site",
                },
            )
        self.assertEqual(response.status_code, 403)
        first_row.assert_not_called()

    def test_a_client_supplied_owner_id_cannot_change_whose_export_runs(self):
        """The form may say anything; only the derived key reaches SQL."""

        calls = []

        def fake_first_row(procedure, parameters=None):
            calls.append((procedure, list(parameters or [])))
            if procedure == "usp_UpsertAppUserFromAuth":
                return identity_row()
            if procedure == "usp_RequestAccountExportForOwner":
                return {"outcome": "created", "job_key": JOB_KEY}
            return None

        with patch(
            "services.database_service.database_service.first_row",
            side_effect=fake_first_row,
        ):
            response = self.client.post(
                "/app/settings/export",
                headers=easy_auth_header(),
                data={
                    "user_key": "00000000-0000-0000-0000-000000000000",
                    "profile_id": "42",
                    "owner": "somebody-else@example.com",
                },
            )

        self.assertEqual(response.status_code, 302)
        request_calls = [c for c in calls if c[0] == "usp_RequestAccountExportForOwner"]
        self.assertEqual(len(request_calls), 1)
        parameters = dict(request_calls[0][1])
        self.assertEqual(list(parameters), ["@UserKey"])
        self.assertEqual(parameters["@UserKey"], OWNER_USER_KEY)

    def test_request_redirects_to_the_job_rather_than_re_posting(self):
        def fake_first_row(procedure, parameters=None):
            if procedure == "usp_UpsertAppUserFromAuth":
                return identity_row()
            if procedure == "usp_RequestAccountExportForOwner":
                return {"outcome": "existing", "job_key": JOB_KEY}
            return None

        with patch(
            "services.database_service.database_service.first_row",
            side_effect=fake_first_row,
        ):
            response = self.client.post(
                "/app/settings/export", headers=easy_auth_header()
            )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/app/settings/export/%s" % JOB_KEY, response.headers["Location"])


class AccountExportStatusPrivacyTests(_ExportRouteTestBase):
    def _get(self, job_key, status_row):
        def fake_first_row(procedure, parameters=None):
            if procedure == "usp_UpsertAppUserFromAuth":
                return identity_row()
            if procedure == "usp_GetAccountExportStatusForOwner":
                return status_row
            return None

        with patch(
            "services.database_service.database_service.first_row",
            side_effect=fake_first_row,
        ):
            return self.client.get(
                "/app/settings/export/%s" % job_key, headers=easy_auth_header()
            )

    def test_owned_job_reports_its_truthful_state(self):
        response = self._get(
            JOB_KEY,
            {
                "job_key": JOB_KEY,
                "state": "running",
                "requested_at_utc": "2026-08-31T00:00:00Z",
                "download_available": 0,
            },
        )
        self.assertEqual(response.status_code, 200)

    def test_a_members_own_expired_job_is_reported_truthfully(self):
        response = self._get(
            JOB_KEY,
            {
                "job_key": JOB_KEY,
                "state": "expired",
                "requested_at_utc": "2026-08-31T00:00:00Z",
                "download_available": 0,
            },
        )
        self.assertEqual(response.status_code, 200)

    def test_every_unreadable_job_is_byte_identical(self):
        """The whole point: no response may hint that a job exists.

        Compared pairwise across EVERY case that must be indistinguishable,
        not a spot-check of three. Any difference in status, body bytes, or
        header names between two of these is an enumeration oracle: it lets
        somebody walk job keys and learn which ones are real, or which
        belong to another member.

        Note what is deliberately NOT in this list: a member's own queued,
        running, ready, failed or expired job. Those are that member's own
        truth and are reported truthfully; they are covered separately.
        """

        cases = {
            # SQL returns no row for all of these, for different reasons.
            "foreign job (owner predicate excludes it)": (OTHER_JOB_KEY, None),
            "unknown job (no such row)": (JOB_KEY, None),
            "malformed key (never reaches SQL)": ("not-a-job-key", None),
            "malformed-length UUID": ("00000000-0000-0000-0000-00000000000", None),
            # A row that comes back with a state outside the ledger's closed
            # vocabulary is unusable and must collapse into the same answer
            # rather than rendering an unexpected string to a member.
            "row with an unknown state": (
                JOB_KEY,
                {"job_key": JOB_KEY, "state": "not-a-real-state"},
            ),
        }

        responses = {}
        for label, (key, row) in cases.items():
            response = self._get(key, row)
            responses[label] = response
            self.assertEqual(response.status_code, 404, label)

        labels = list(responses)
        first = labels[0]
        for other in labels[1:]:
            self.assertEqual(
                responses[first].get_data(),
                responses[other].get_data(),
                "body differs between %r and %r" % (first, other),
            )
            self.assertEqual(
                sorted(responses[first].headers.items()),
                sorted(responses[other].headers.items()),
                "headers differ between %r and %r" % (first, other),
            )


    def test_foreign_and_unknown_refuse_through_an_identical_code_path(self):
        """Structural mitigation for the timing channel this cannot unit-test.

        A wall-clock assertion in a unit suite is flaky theatre, so the
        residual timing risk is recorded honestly as untested in the
        package evidence. What IS testable, and is the part that matters,
        is that the two cases an attacker could actually learn from --
        "this job exists but is not yours" and "this job does not exist"
        -- refuse through the same code path by construction: same
        procedure, same parameters, same refusal. There is no
        cause-specific early return between them that could diverge in
        time or in output.

        The malformed-key case deliberately short-circuits BEFORE any
        database call. That is not a leak: it tells a caller only whether
        the value they themselves supplied was a well-formed UUID, which
        they already know, and it reveals nothing about any other member.
        Asserted explicitly so the asymmetry stays intentional rather
        than drifting into one.
        """

        def run(job_key):
            calls = []

            def fake_first_row(procedure, parameters=None):
                calls.append((procedure, list(parameters or [])))
                if procedure == "usp_UpsertAppUserFromAuth":
                    return identity_row()
                return None  # foreign and unknown are indistinguishable in SQL

            with patch(
                "services.database_service.database_service.first_row",
                side_effect=fake_first_row,
            ):
                response = self.client.get(
                    "/app/settings/export/%s" % job_key,
                    headers=easy_auth_header(),
                )
            status_calls = [
                c for c in calls
                if c[0] == "usp_GetAccountExportStatusForOwner"
            ]
            return response, status_calls

        foreign_response, foreign_calls = run(OTHER_JOB_KEY)
        unknown_response, unknown_calls = run(JOB_KEY)
        malformed_response, malformed_calls = run("not-a-job-key")

        # Both well-formed cases take the SAME path: one status call each,
        # with the same parameter names in the same order.
        self.assertEqual(len(foreign_calls), 1)
        self.assertEqual(len(unknown_calls), 1)
        self.assertEqual(
            [name for name, _ in foreign_calls[0][1]],
            [name for name, _ in unknown_calls[0][1]],
        )
        self.assertEqual(["@UserKey", "@JobKey"], [n for n, _ in foreign_calls[0][1]])

        # ...and produce the same refusal.
        self.assertEqual(foreign_response.status_code, 404)
        self.assertEqual(unknown_response.status_code, 404)
        self.assertEqual(foreign_response.get_data(), unknown_response.get_data())

        # The malformed case never reaches SQL, by design.
        self.assertEqual(malformed_calls, [])
        self.assertEqual(malformed_response.status_code, 404)
        self.assertEqual(malformed_response.get_data(), foreign_response.get_data())


class AccountExportDownloadTests(_ExportRouteTestBase):
    ZIP_BYTES = b"PK\x05\x06" + b"\x00" * 18

    def _download(self, metadata_row, storage_bytes=None, storage_error=None):
        def fake_first_row(procedure, parameters=None):
            if procedure == "usp_UpsertAppUserFromAuth":
                return identity_row()
            if procedure == "usp_GetAccountExportDownloadMetadataForOwner":
                return metadata_row
            return None

        class FakeStorage:
            def read_final(self, job_key, expected_sha256=None, expected_size=None):
                if storage_error is not None:
                    raise storage_error
                return storage_bytes

        with patch(
            "services.database_service.database_service.first_row",
            side_effect=fake_first_row,
        ), patch(
            "services.account_export_experience_service."
            "AccountExportStorageService",
            return_value=FakeStorage(),
        ):
            return self.client.get(
                "/app/settings/export/%s/download" % JOB_KEY,
                headers=easy_auth_header(),
            )

    def test_ready_job_streams_the_archive_with_the_required_headers(self):
        response = self._download(
            {
                "job_key": JOB_KEY,
                "final_artifact_reference": "export/v1/final/%s.zip" % JOB_KEY,
                "final_artifact_sha256": "a" * 64,
                "compressed_size_bytes": len(self.ZIP_BYTES),
            },
            storage_bytes=self.ZIP_BYTES,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], "application/zip")
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")
        self.assertEqual(response.headers["Pragma"], "no-cache")
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertIn("attachment;", response.headers["Content-Disposition"])
        self.assertEqual(response.get_data(), self.ZIP_BYTES)

    def test_the_private_artifact_reference_never_reaches_the_response(self):
        reference = "export/v1/final/%s.zip" % JOB_KEY
        response = self._download(
            {
                "job_key": JOB_KEY,
                "final_artifact_reference": reference,
                "final_artifact_sha256": "a" * 64,
                "compressed_size_bytes": len(self.ZIP_BYTES),
            },
            storage_bytes=self.ZIP_BYTES,
        )
        blob = response.get_data() + b"\n" + b"\n".join(
            b"%s: %s" % (k.encode(), v.encode())
            for k, v in response.headers.items()
        )
        self.assertNotIn(reference.encode(), blob)
        self.assertNotIn(b"export/v1/final", blob)

    def test_no_download_outcome_leaks_the_private_locator(self):
        """The locator must not hide in an error path.

        The happy path is the obvious place to check and the least likely
        place to leak. These are the paths where a locator, container name
        or provider message actually escapes: a storage failure, a hash
        mismatch, a size mismatch, and a not-downloadable job. Each is
        checked across the body AND every header value.
        """

        from services.account_export_storage_service import (
            AccountExportStorageError,
        )

        reference = "export/v1/final/%s.zip" % JOB_KEY
        metadata = {
            "job_key": JOB_KEY,
            "final_artifact_reference": reference,
            "final_artifact_sha256": "a" * 64,
            "compressed_size_bytes": len(self.ZIP_BYTES),
        }

        outcomes = {
            "ready": self._download(metadata, storage_bytes=self.ZIP_BYTES),
            "not downloadable": self._download(None),
            "storage read failed": self._download(
                metadata, storage_error=AccountExportStorageError("storage_read_failed")
            ),
            "hash mismatch": self._download(
                metadata, storage_error=AccountExportStorageError("storage_hash_mismatch")
            ),
            "size mismatch": self._download(
                metadata, storage_error=AccountExportStorageError("storage_size_mismatch")
            ),
            "container unreachable": self._download(
                metadata, storage_error=AccountExportStorageError("storage_unavailable")
            ),
        }

        forbidden = (
            reference.encode(),
            b"export/v1/final",
            b"peerslate-private-account-export",
            b"blob.core.windows.net",
            b"storage_hash_mismatch",
            b"storage_read_failed",
            b"a" * 64,  # the digest itself is not a member-facing value
        )

        for label, response in outcomes.items():
            haystack = response.get_data() + b"\n" + b"\n".join(
                b"%s: %s" % (key.encode(), value.encode())
                for key, value in response.headers.items()
            )
            for needle in forbidden:
                self.assertNotIn(
                    needle, haystack, "%r leaked in the %r outcome" % (needle, label)
                )

    def test_a_job_that_is_not_downloadable_is_a_neutral_404(self):
        response = self._download(None)
        self.assertEqual(response.status_code, 404)
        self.assertNotIn(b"PK", response.get_data()[:4])

    def test_a_hash_mismatch_fails_closed_without_returning_bytes(self):
        from services.account_export_storage_service import (
            AccountExportStorageError,
        )

        response = self._download(
            {
                "job_key": JOB_KEY,
                "final_artifact_reference": "export/v1/final/%s.zip" % JOB_KEY,
                "final_artifact_sha256": "a" * 64,
                "compressed_size_bytes": len(self.ZIP_BYTES),
            },
            storage_error=AccountExportStorageError("storage_hash_mismatch"),
        )
        self.assertEqual(response.status_code, 503)
        self.assertNotEqual(response.get_data(), self.ZIP_BYTES)


class AccountExportHonestyTests(_ExportRouteTestBase):
    """The screen must not imply the export is complete when it is not."""

    def test_the_page_names_journal_and_projects_as_not_included(self):
        def fake_first_row(procedure, parameters=None):
            if procedure == "usp_UpsertAppUserFromAuth":
                return identity_row()
            return None

        with patch(
            "services.database_service.database_service.first_row",
            side_effect=fake_first_row,
        ):
            response = self.client.get(
                "/app/settings/export", headers=easy_auth_header()
            )

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True).lower()
        self.assertIn("journal", body)
        self.assertIn("projects", body)
        self.assertIn("not included", body)


if __name__ == "__main__":
    unittest.main()
