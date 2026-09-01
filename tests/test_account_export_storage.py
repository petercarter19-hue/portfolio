"""Offline contracts for services/account_export_storage_service.py and
the worker-side pure helpers in scripts/run_account_export_worker.py.

No network, database, or provider call anywhere in this file: the
Azure Blob SDK is faked (FakeContainer/FakeBlob below, matching
tests/test_capture_media_storage_service.py's own style) and the
worker's DB-facing functions are exercised only through fake
cursor/connection doubles. Every payload here is an obvious synthetic
placeholder.

Run: C:\\Users\\peter\\Documents\\portfolio\\venv\\Scripts\\python.exe
-m pytest -q tests/test_account_export_storage.py
(env ANTHROPIC_API_KEY=placeholder per the project test convention).
"""

import hashlib
import inspect
import io
import unittest
import uuid
import zipfile
from types import SimpleNamespace

from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError

import services.account_export_storage_service as storage_module
from services.account_export_storage_service import (
    AccountExportStorageError,
    AccountExportStorageService,
    final_blob_name,
    staging_blob_name,
)
from scripts.run_account_export_worker import (
    FAILURE_CODES,
    MAX_ATTEMPTS,
    OWNER_INACTIVE_FAILURE_CODE,
    choose_failure_code_for_error,
    content_free_log_fields,
    is_owner_active,
    normalize_job_key,
    post_fail_state,
    verify_promoted_hash,
)


JOB_KEY = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"


def _zip_bytes(entries):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w") as archive:
        for name, data in entries.items():
            archive.writestr(name, data)
    return buffer.getvalue()


VALID_ARCHIVE = _zip_bytes(
    {"manifest.json": b'{"format":"peerslate.account.export"}', "domains/a.ndjson": b"{}\n"}
)


class FakeDownload:
    def __init__(self, payload):
        self.payload = payload

    def readall(self):
        return self.payload


class FakeBlob:
    def __init__(self, container, name):
        self.container = container
        self.name = name

    def get_blob_properties(self):
        if self.name not in self.container.payloads:
            raise KeyError(self.name)
        size = self.container.size_overrides.get(
            self.name, len(self.container.payloads[self.name])
        )
        return SimpleNamespace(size=size)

    def download_blob(self):
        if self.name not in self.container.payloads:
            raise KeyError(self.name)
        return FakeDownload(self.container.payloads[self.name])

    def exists(self):
        return self.name in self.container.payloads


class FakeContainer:
    def __init__(self):
        self.payloads = {}
        self.size_overrides = {}
        self.upload_calls = []
        self.delete_calls = []

    def upload_blob(self, **kwargs):
        self.upload_calls.append(kwargs)
        if kwargs["name"] in self.payloads:
            raise ResourceExistsError("already exists")
        self.payloads[kwargs["name"]] = kwargs["data"]

    def get_blob_client(self, name):
        return FakeBlob(self, name)

    def delete_blob(self, name, **kwargs):
        self.delete_calls.append(name)
        if name not in self.payloads:
            raise ResourceNotFoundError("absent")
        del self.payloads[name]

    def get_container_properties(self, **kwargs):
        return SimpleNamespace(name="fake-container")


def _service(container=None, **kwargs):
    service = AccountExportStorageService(
        account_url="https://synthetic.blob.core.windows.net",
        container_name="private-account-export",
        **kwargs,
    )
    service._container_client = container if container is not None else FakeContainer()
    return service


class StagingAndPromotionTests(unittest.TestCase):
    def test_stage_is_create_only(self):
        container = FakeContainer()
        service = _service(container)

        service.stage(JOB_KEY, 1, VALID_ARCHIVE)
        self.assertEqual(
            container.payloads[staging_blob_name(JOB_KEY, 1)], VALID_ARCHIVE
        )
        self.assertFalse(container.upload_calls[0]["overwrite"])
        self.assertIsNone(container.upload_calls[0]["metadata"])

        with self.assertRaises(AccountExportStorageError) as raised:
            service.stage(JOB_KEY, 1, VALID_ARCHIVE)
        self.assertEqual(raised.exception.code, "storage_conflict")

    def test_stage_rejects_oversize_before_any_upload_attempt(self):
        container = FakeContainer()
        service = _service(container, max_compressed_bytes=10)

        with self.assertRaises(AccountExportStorageError) as raised:
            service.stage(JOB_KEY, 1, VALID_ARCHIVE)

        self.assertEqual(raised.exception.code, "oversize_compressed")
        self.assertEqual(container.upload_calls, [])

    def test_promote_returns_independently_recomputed_facts_and_promotes_once(self):
        container = FakeContainer()
        service = _service(container)
        service.stage(JOB_KEY, 1, VALID_ARCHIVE)

        result = service.promote(JOB_KEY, 1)

        self.assertEqual(result["reference"], final_blob_name(JOB_KEY))
        self.assertEqual(result["compressed_size_bytes"], len(VALID_ARCHIVE))
        with zipfile.ZipFile(io.BytesIO(VALID_ARCHIVE)) as archive:
            # Excludes manifest.json itself -- see the matching
            # exclusion in AccountExportStorageService.promote() and in
            # account_export_assembly_service._sum_uncompressed.
            expected_uncompressed = sum(
                info.file_size for info in archive.infolist() if info.filename != "manifest.json"
            )
        self.assertEqual(result["uncompressed_size_bytes"], expected_uncompressed)
        self.assertEqual(container.payloads[final_blob_name(JOB_KEY)], VALID_ARCHIVE)
        # Staging is cleaned up as part of a successful promotion.
        self.assertNotIn(staging_blob_name(JOB_KEY, 1), container.payloads)

    def test_promote_succeeds_even_when_staging_cleanup_fails(self):
        # A transient staging-delete failure must never turn an
        # already-successful promotion into a reported failure -- the
        # final object is already committed by the time cleanup runs.
        class FlakyCleanupContainer(FakeContainer):
            def delete_blob(self, name, **kwargs):
                raise RuntimeError("transient delete failure")

        container = FlakyCleanupContainer()
        service = _service(container)
        service.stage(JOB_KEY, 1, VALID_ARCHIVE)

        result = service.promote(JOB_KEY, 1)  # must not raise

        self.assertEqual(result["reference"], final_blob_name(JOB_KEY))
        self.assertEqual(result["sha256"], hashlib.sha256(VALID_ARCHIVE).hexdigest())
        self.assertEqual(container.payloads[final_blob_name(JOB_KEY)], VALID_ARCHIVE)
        # Cleanup failed, so staging is (harmlessly) still present --
        # promotion succeeded regardless.
        self.assertIn(staging_blob_name(JOB_KEY, 1), container.payloads)

    def test_promotion_blocked_when_nothing_was_staged(self):
        service = _service()
        with self.assertRaises(AccountExportStorageError) as raised:
            service.promote(JOB_KEY, 1)
        self.assertEqual(raised.exception.code, "storage_read_failed")

    def test_promotion_blocked_when_reported_size_disagrees_with_actual_bytes(self):
        container = FakeContainer()
        service = _service(container)
        service.stage(JOB_KEY, 1, VALID_ARCHIVE)
        container.size_overrides[staging_blob_name(JOB_KEY, 1)] = len(VALID_ARCHIVE) + 1

        with self.assertRaises(AccountExportStorageError) as raised:
            service.promote(JOB_KEY, 1)

        self.assertEqual(raised.exception.code, "storage_invalid_properties")
        # A blocked promotion must never have created the final object.
        self.assertNotIn(final_blob_name(JOB_KEY), container.payloads)

    def test_promotion_blocked_when_archive_has_no_manifest(self):
        container = FakeContainer()
        service = _service(container)
        no_manifest = _zip_bytes({"domains/a.ndjson": b"{}\n"})
        service.stage(JOB_KEY, 1, no_manifest)

        with self.assertRaises(AccountExportStorageError) as raised:
            service.promote(JOB_KEY, 1)

        self.assertEqual(raised.exception.code, "corrupt_archive")
        self.assertNotIn(final_blob_name(JOB_KEY), container.payloads)

    def test_promotion_blocked_when_uncompressed_total_exceeds_cap(self):
        container = FakeContainer()
        service = _service(container, max_uncompressed_bytes=1)
        service.stage(JOB_KEY, 1, VALID_ARCHIVE)

        with self.assertRaises(AccountExportStorageError) as raised:
            service.promote(JOB_KEY, 1)

        self.assertEqual(raised.exception.code, "oversize_uncompressed")
        self.assertNotIn(final_blob_name(JOB_KEY), container.payloads)

    def test_promotion_refuses_to_replace_an_existing_final_object(self):
        container = FakeContainer()
        service = _service(container)
        container.payloads[final_blob_name(JOB_KEY)] = VALID_ARCHIVE
        service.stage(JOB_KEY, 1, VALID_ARCHIVE)

        with self.assertRaises(AccountExportStorageError) as raised:
            service.promote(JOB_KEY, 1)
        self.assertEqual(raised.exception.code, "storage_conflict")


class CleanupIdempotencyTests(unittest.TestCase):
    def test_cleanup_staging_is_idempotent(self):
        container = FakeContainer()
        service = _service(container)
        service.stage(JOB_KEY, 1, VALID_ARCHIVE)

        service.cleanup_staging(JOB_KEY, 1)
        self.assertNotIn(staging_blob_name(JOB_KEY, 1), container.payloads)
        service.cleanup_staging(JOB_KEY, 1)  # already absent: still succeeds

    def test_cleanup_final_is_idempotent(self):
        container = FakeContainer()
        service = _service(container)
        container.payloads[final_blob_name(JOB_KEY)] = VALID_ARCHIVE

        service.cleanup_final(JOB_KEY)
        self.assertNotIn(final_blob_name(JOB_KEY), container.payloads)
        service.cleanup_final(JOB_KEY)  # already absent: still succeeds

    def test_delete_failure_is_reported_with_a_stable_code(self):
        class ExplodingContainer(FakeContainer):
            def delete_blob(self, name, **kwargs):
                raise RuntimeError("provider outage detail that must never leak")

        service = _service(ExplodingContainer())
        with self.assertRaises(AccountExportStorageError) as raised:
            service.cleanup_final(JOB_KEY)
        self.assertEqual(raised.exception.code, "storage_delete_failed")
        self.assertNotIn("provider outage", str(raised.exception))


class NameValidationTests(unittest.TestCase):
    def test_staging_and_final_names_require_a_canonical_job_key(self):
        for bad_key in ("not-a-uuid", JOB_KEY.upper(), "", None, JOB_KEY + "/../x"):
            with self.subTest(job_key=bad_key):
                with self.assertRaises(ValueError):
                    staging_blob_name(bad_key, 1)
                with self.assertRaises(ValueError):
                    final_blob_name(bad_key)

    def test_staging_name_requires_a_bounded_attempt(self):
        for bad_attempt in (0, 4, -1, "1", True):
            with self.subTest(attempt=bad_attempt):
                with self.assertRaises(ValueError):
                    staging_blob_name(JOB_KEY, bad_attempt)


class NoSasNoUrlTests(unittest.TestCase):
    """Assert none of the adapter's public methods can return or log a
    URL or SAS token, and that no SAS-issuing code path exists at all."""

    def test_source_never_references_sas_or_delegation_apis(self):
        source = inspect.getsource(storage_module)
        for forbidden in (
            "generate_blob_sas",
            "generate_container_sas",
            "sas_token",
            "user_delegation",
            "get_user_delegation_key",
        ):
            self.assertNotIn(forbidden, source)

    def test_promote_result_never_contains_a_url(self):
        container = FakeContainer()
        service = _service(container)
        service.stage(JOB_KEY, 1, VALID_ARCHIVE)
        result = service.promote(JOB_KEY, 1)

        for value in result.values():
            self.assertNotIn("http://", str(value))
            self.assertNotIn("https://", str(value))

    def test_reference_is_an_opaque_relative_path_not_the_account_url(self):
        reference = final_blob_name(JOB_KEY)
        self.assertFalse(reference.startswith("http"))
        self.assertNotIn("synthetic.blob.core.windows.net", reference)

    def test_errors_never_embed_account_url_or_container_name(self):
        service = AccountExportStorageService(
            account_url="https://leak-canary.blob.core.windows.net",
            container_name="leak-canary-container",
        )
        with self.assertRaises(AccountExportStorageError) as raised:
            service.promote(JOB_KEY, 1)
        message = str(raised.exception)
        self.assertNotIn("leak-canary", message)
        self.assertNotIn("http", message)


class WorkerOwnerActiveHelperTests(unittest.TestCase):
    """The 'owner-inactive refusal path' proof: is_owner_active is the
    pure, DB-shaped decision function scripts/run_account_export_worker.py
    checks before any storage write."""

    class FakeCursor:
        def __init__(self, row):
            self._row = row
            self.executed = None

        def execute(self, sql, params):
            self.executed = (sql, params)

        def fetchone(self):
            return self._row

    def test_active_owner_row_present_returns_true(self):
        cursor = self.FakeCursor(row=(1,))
        self.assertTrue(is_owner_active(cursor, owner_user_id=7, owner_profile_id=9))
        sql, params = cursor.executed
        self.assertIn("app_users", sql)
        self.assertIn("member_profiles", sql)
        self.assertIn("active = 1", sql)
        self.assertEqual(params, (7, 9))

    def test_inactive_or_unknown_owner_returns_false(self):
        cursor = self.FakeCursor(row=None)
        self.assertFalse(is_owner_active(cursor, owner_user_id=7, owner_profile_id=9))

    def test_owner_inactive_failure_code_is_in_the_closed_enum(self):
        self.assertIn(OWNER_INACTIVE_FAILURE_CODE, FAILURE_CODES)
        self.assertNotIn("attempts_exhausted", FAILURE_CODES)


class WorkerHelperTests(unittest.TestCase):
    def test_normalize_job_key_accepts_str_and_uuid_and_lowercases(self):
        canonical = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
        self.assertEqual(normalize_job_key(canonical.upper()), canonical)
        self.assertEqual(normalize_job_key(uuid.UUID(canonical)), canonical)

    def test_choose_failure_code_maps_known_adapter_codes_through(self):
        for code in ("oversize_compressed", "oversize_uncompressed", "hash_mismatch"):
            error = AccountExportStorageError(code)
            self.assertEqual(choose_failure_code_for_error(error), code)

    def test_choose_failure_code_maps_unavailable_storage_to_worker_unavailable(self):
        error = AccountExportStorageError("storage_unavailable")
        self.assertEqual(choose_failure_code_for_error(error), "worker_unavailable")

    def test_choose_failure_code_defaults_to_internal_error(self):
        self.assertEqual(choose_failure_code_for_error(ValueError("boom")), "internal_error")
        self.assertEqual(choose_failure_code_for_error(TimeoutError()), "assembly_timeout")

    def test_choose_failure_code_never_returns_a_code_outside_the_closed_enum(self):
        for error in (
            AccountExportStorageError("storage_unavailable"),
            AccountExportStorageError("storage_access_denied"),
            AccountExportStorageError("storage_conflict"),
            AccountExportStorageError("storage_upload_failed"),
            AccountExportStorageError("corrupt_archive"),
            ValueError("unexpected"),
            RuntimeError("unexpected"),
        ):
            self.assertIn(choose_failure_code_for_error(error), FAILURE_CODES)

    def test_verify_promoted_hash_passes_when_equal(self):
        verify_promoted_hash({"sha256": "a" * 64}, {"sha256": "a" * 64})  # must not raise

    def test_verify_promoted_hash_raises_hash_mismatch_on_disagreement(self):
        with self.assertRaises(AccountExportStorageError) as raised:
            verify_promoted_hash({"sha256": "a" * 64}, {"sha256": "b" * 64})
        self.assertEqual(raised.exception.code, "hash_mismatch")
        # And the worker's own mapper preserves that exact code, rather
        # than collapsing it to internal_error.
        self.assertEqual(choose_failure_code_for_error(raised.exception), "hash_mismatch")

    def test_post_fail_state_is_queued_while_attempts_remain_else_failed(self):
        for attempt in range(1, MAX_ATTEMPTS):
            with self.subTest(attempt=attempt):
                self.assertEqual(post_fail_state(attempt), "queued")
        for attempt in (MAX_ATTEMPTS, MAX_ATTEMPTS + 1):
            with self.subTest(attempt=attempt):
                self.assertEqual(post_fail_state(attempt), "failed")


class ReadFinalPreReadGuardTests(unittest.TestCase):
    """PS-SETTINGS-ACCOUNT-EXPORT-AVAILABILITY-001: refuse BEFORE reading.

    The 100 MiB compressed cap used to be checked only after
    ``download_blob().readall()`` had already buffered the whole object,
    so it bounded nothing. ``read_final`` must now refuse from the
    provider-reported properties alone — an oversized object, or one
    whose reported size disagrees with the ledger's committed size, costs
    a properties call and zero downloaded bytes. The reported size comes
    from the provider, so the existing post-read verifications still run
    unchanged on the actual bytes; these tests prove only that the cheap
    refusal happens first.
    """

    class SpyingContainer(FakeContainer):
        """Counts download_blob calls so 'refused without a read' is a
        proven fact rather than an assumption."""

        def __init__(self):
            super().__init__()
            self.download_calls = 0

        def get_blob_client(self, name):
            outer = self
            blob = FakeBlob(self, name)
            original_download = blob.download_blob

            def counting_download():
                outer.download_calls += 1
                return original_download()

            blob.download_blob = counting_download
            return blob

    def _ready_container(self):
        container = self.SpyingContainer()
        container.payloads[final_blob_name(JOB_KEY)] = VALID_ARCHIVE
        return container

    def test_provider_reported_oversize_is_refused_without_a_download(self):
        container = self._ready_container()
        # The stored payload is small; only the provider's REPORTED size is
        # oversized. Refusal therefore proves the decision was made from
        # properties, before any byte moved.
        container.size_overrides[final_blob_name(JOB_KEY)] = (
            storage_module.MAX_COMPRESSED_BYTES + 1
        )
        service = _service(container)

        with self.assertRaises(AccountExportStorageError) as caught:
            # No expected_size on purpose: the cap refusal must not depend
            # on the ledger's opinion being available.
            service.read_final(
                JOB_KEY,
                expected_sha256=hashlib.sha256(VALID_ARCHIVE).hexdigest(),
            )
        self.assertEqual(caught.exception.code, "oversize_compressed")
        self.assertEqual(container.download_calls, 0)

    def test_ledger_size_disagreement_is_refused_without_a_download(self):
        container = self._ready_container()
        container.size_overrides[final_blob_name(JOB_KEY)] = (
            len(VALID_ARCHIVE) + 1
        )
        service = _service(container)

        with self.assertRaises(AccountExportStorageError) as caught:
            service.read_final(
                JOB_KEY,
                expected_sha256=hashlib.sha256(VALID_ARCHIVE).hexdigest(),
                expected_size=len(VALID_ARCHIVE),
            )
        self.assertEqual(caught.exception.code, "storage_size_mismatch")
        self.assertEqual(container.download_calls, 0)

    def test_matching_facts_still_download_and_fully_verify(self):
        """The guards must never break the working path: when the reported
        size honours both the cap and the ledger, the bytes are downloaded
        once and every post-read verification still passes."""
        container = self._ready_container()
        service = _service(container)

        data = service.read_final(
            JOB_KEY,
            expected_sha256=hashlib.sha256(VALID_ARCHIVE).hexdigest(),
            expected_size=len(VALID_ARCHIVE),
        )

        self.assertEqual(data, VALID_ARCHIVE)
        self.assertEqual(container.download_calls, 1)

    def test_post_read_verification_survives_the_new_guards(self):
        """Belt and braces stays: a provider that reports an honest size
        but serves different bytes is still caught AFTER the read by the
        unchanged digest check — the pre-read guard replaced nothing."""
        container = self._ready_container()
        service = _service(container)

        with self.assertRaises(AccountExportStorageError) as caught:
            service.read_final(
                JOB_KEY,
                expected_sha256="0" * 64,
                expected_size=len(VALID_ARCHIVE),
            )
        self.assertEqual(caught.exception.code, "storage_hash_mismatch")
        self.assertEqual(container.download_calls, 1)


class ContentFreeLoggingTests(unittest.TestCase):
    def test_only_allowlisted_fields_survive(self):
        fields = content_free_log_fields(
            job_key=JOB_KEY,
            state="ready",
            compressed_size_bytes=123,
            employer_name="SHOULD NOT APPEAR",
            secret_blob_name="export/v1/final/should-not-appear.zip",
            member_email="should-not-appear@example.test",
        )

        self.assertEqual(
            fields,
            {"job_key": JOB_KEY, "state": "ready", "compressed_size_bytes": 123},
        )
        self.assertNotIn("employer_name", fields)
        self.assertNotIn("secret_blob_name", fields)
        self.assertNotIn("member_email", fields)

    def test_none_values_are_dropped(self):
        fields = content_free_log_fields(job_key=JOB_KEY, failure_code=None)
        self.assertEqual(fields, {"job_key": JOB_KEY})


if __name__ == "__main__":
    unittest.main()
