"""Offline contracts for services/account_export_assembly_service.py.

No network, database, or provider call anywhere in this file. Every
domain file used here is an obvious synthetic placeholder -- never
anything resembling real member content, matching this claim's hard
rule against real data in fixtures.

Run: C:\\Users\\peter\\Documents\\portfolio\\venv\\Scripts\\python.exe
-m pytest -q tests/test_account_export_assembly.py
(env ANTHROPIC_API_KEY=placeholder per the project test convention).
"""

import hashlib
import io
import json
import unittest
import zipfile

from services.account_export_assembly_service import (
    MANIFEST_FORMAT,
    MANIFEST_PATH,
    MANIFEST_SCHEMA_VERSION,
    AccountExportAssemblyError,
    AccountExportAssemblyService,
)


# The exact pinned ZipInfo values every archive member must carry,
# regardless of the build host or wall-clock time. external_attr is
# NOT 0: zipfile.ZipFile._open_to_write substitutes 0o600 << 16 for a
# falsy value, so this is the value that was always actually being
# written -- pinning it explicitly (rather than relying on that
# substitution) is what services/account_export_assembly_service.py's
# _write_fixed_entry now does.
EXPECTED_ZIP_DATE_TIME = (1980, 1, 1, 0, 0, 0)
EXPECTED_ZIP_CREATE_SYSTEM = 0
EXPECTED_ZIP_EXTERNAL_ATTR = 0o600 << 16


def _included(path, domain_code, content, record_count=1, **extra):
    entry = {
        "path": path,
        "domain_code": domain_code,
        "schema_id": "peerslate." + domain_code + ".v1",
        "schema_version": 1,
        "disposition": "included",
        "content": content,
        "record_count": record_count,
    }
    entry.update(extra)
    return entry


def _excluded(path, domain_code, reason="synthetic omission reason"):
    return {
        "path": path,
        "domain_code": domain_code,
        "schema_id": "peerslate." + domain_code + ".v1",
        "schema_version": 1,
        "disposition": "excluded",
        "omission_reason": reason,
    }


def _unavailable(path, domain_code, failure_reason="synthetic failure reason"):
    return {
        "path": path,
        "domain_code": domain_code,
        "schema_id": "peerslate." + domain_code + ".v1",
        "schema_version": 1,
        "disposition": "unavailable",
        "failure_reason": failure_reason,
    }


ASSEMBLE_KWARGS = dict(
    job_key="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
    requested_at_utc="2026-08-28T12:00:00Z",
    assembly_started_at_utc="2026-08-28T12:00:01Z",
    assembly_cutoff_at_utc="2026-08-28T12:00:02Z",
    consistency_marker_start="00000000000007d1",
    consistency_marker_cutoff="00000000000007d2",
)


class AccountExportAssemblyDeterminismTests(unittest.TestCase):
    def setUp(self):
        self.service = AccountExportAssemblyService()
        self.domain_files = [
            _included(
                "domains/zzz_last.ndjson",
                "zzz_last",
                b'{"note":"SYNTHETIC FIXTURE B"}\n',
            ),
            _excluded("domains/aaa_first.ndjson", "aaa_first"),
            _unavailable("domains/mmm_middle.ndjson", "mmm_middle"),
        ]

    def test_deterministic_byte_identical_assembly(self):
        first = self.service.assemble(self.domain_files, **ASSEMBLE_KWARGS)
        second = self.service.assemble(self.domain_files, **ASSEMBLE_KWARGS)

        self.assertEqual(first["archive_bytes"], second["archive_bytes"])
        self.assertEqual(first["sha256"], second["sha256"])
        self.assertEqual(first["manifest"], second["manifest"])
        self.assertEqual(
            first["compressed_size_bytes"], second["compressed_size_bytes"]
        )
        self.assertEqual(
            first["uncompressed_size_bytes"], second["uncompressed_size_bytes"]
        )

    def test_manifest_completeness_and_ordering(self):
        result = self.service.assemble(self.domain_files, **ASSEMBLE_KWARGS)
        files = result["manifest"]["files"]

        self.assertEqual(len(files), 3)
        self.assertEqual(
            [entry["path"] for entry in files],
            ["domains/aaa_first.ndjson", "domains/mmm_middle.ndjson", "domains/zzz_last.ndjson"],
        )
        by_domain = {entry["domain_code"]: entry for entry in files}
        self.assertEqual(by_domain["aaa_first"]["disposition"], "excluded")
        self.assertIsNotNone(by_domain["aaa_first"]["omission_reason"])
        self.assertIsNone(by_domain["aaa_first"]["failure_reason"])
        self.assertEqual(by_domain["mmm_middle"]["disposition"], "unavailable")
        self.assertIsNotNone(by_domain["mmm_middle"]["failure_reason"])
        self.assertEqual(by_domain["zzz_last"]["disposition"], "included")
        self.assertEqual(by_domain["zzz_last"]["record_count"], 1)
        self.assertEqual(
            by_domain["zzz_last"]["sha256"],
            hashlib.sha256(b'{"note":"SYNTHETIC FIXTURE B"}\n').hexdigest(),
        )

    def test_manifest_top_level_fields(self):
        result = self.service.assemble(self.domain_files, **ASSEMBLE_KWARGS)
        manifest = result["manifest"]

        self.assertEqual(manifest["format"], MANIFEST_FORMAT)
        self.assertEqual(manifest["schema_version"], MANIFEST_SCHEMA_VERSION)
        self.assertEqual(manifest["job_key"], ASSEMBLE_KWARGS["job_key"])
        self.assertEqual(manifest["requested_at_utc"], ASSEMBLE_KWARGS["requested_at_utc"])
        self.assertEqual(
            manifest["consistency_marker_start"],
            ASSEMBLE_KWARGS["consistency_marker_start"],
        )

    def test_manifest_json_has_stable_key_order_and_no_extra_whitespace(self):
        result = self.service.assemble(self.domain_files, **ASSEMBLE_KWARGS)
        with zipfile.ZipFile(io.BytesIO(result["archive_bytes"])) as archive:
            manifest_bytes = archive.read(MANIFEST_PATH)

        self.assertNotIn(b", ", manifest_bytes)
        self.assertNotIn(b": ", manifest_bytes)
        parsed_in_order = json.loads(manifest_bytes, object_pairs_hook=list)
        top_level_keys = [key for key, _ in parsed_in_order]
        self.assertEqual(
            top_level_keys,
            [
                "format",
                "schema_version",
                "job_key",
                "requested_at_utc",
                "assembly_started_at_utc",
                "assembly_cutoff_at_utc",
                "consistency_marker_start",
                "consistency_marker_cutoff",
                "files",
            ],
        )

    def test_no_unlisted_bytes_and_manifest_is_first_entry(self):
        result = self.service.assemble(self.domain_files, **ASSEMBLE_KWARGS)
        with zipfile.ZipFile(io.BytesIO(result["archive_bytes"])) as archive:
            names = archive.namelist()

        self.assertEqual(names[0], MANIFEST_PATH)
        included_paths = [
            entry["path"]
            for entry in result["manifest"]["files"]
            if entry["disposition"] == "included"
        ]
        self.assertEqual(names[1:], included_paths)
        self.assertEqual(len(names), 1 + len(included_paths))

    def test_zip_entries_carry_pinned_metadata_not_host_or_wall_clock_values(self):
        # This is the test that would have caught the external_attr
        # bug: an earlier version wrote 0 intending to pin it there,
        # but zipfile silently substitutes 0o600 << 16 for a falsy
        # external_attr, so the archive never actually carried 0.
        result = self.service.assemble(self.domain_files, **ASSEMBLE_KWARGS)
        with zipfile.ZipFile(io.BytesIO(result["archive_bytes"])) as archive:
            entries = archive.infolist()

        self.assertTrue(entries)
        for info in entries:
            with self.subTest(entry=info.filename):
                self.assertEqual(info.date_time, EXPECTED_ZIP_DATE_TIME)
                self.assertEqual(info.create_system, EXPECTED_ZIP_CREATE_SYSTEM)
                self.assertEqual(info.external_attr, EXPECTED_ZIP_EXTERNAL_ATTR)

    def test_sha256_and_sizes_are_independently_recomputed(self):
        result = self.service.assemble(self.domain_files, **ASSEMBLE_KWARGS)
        archive_bytes = result["archive_bytes"]

        self.assertEqual(result["sha256"], hashlib.sha256(archive_bytes).hexdigest())
        self.assertEqual(result["compressed_size_bytes"], len(archive_bytes))
        with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
            # Excludes manifest.json itself: uncompressed_size_bytes is
            # defined as the exported domain content total, matching
            # the same running total the cap check enforces during the
            # build (see account_export_assembly_service._sum_uncompressed).
            expected_uncompressed = sum(
                info.file_size for info in archive.infolist() if info.filename != MANIFEST_PATH
            )
        self.assertEqual(result["uncompressed_size_bytes"], expected_uncompressed)


class AccountExportAssemblyCapTests(unittest.TestCase):
    def setUp(self):
        self.service = AccountExportAssemblyService()

    def test_uncompressed_cap_boundary_passes_and_over_fails(self):
        content = b"x" * 100
        domain_files = [_included("domains/big.ndjson", "big", content)]

        at_cap = self.service.assemble(
            domain_files, max_uncompressed_bytes=100, **ASSEMBLE_KWARGS
        )
        self.assertEqual(at_cap["uncompressed_size_bytes"], 100)

        with self.assertRaises(AccountExportAssemblyError) as raised:
            self.service.assemble(
                domain_files, max_uncompressed_bytes=99, **ASSEMBLE_KWARGS
            )
        self.assertEqual(raised.exception.code, "oversize_uncompressed")

    def test_compressed_cap_boundary_passes_and_over_fails(self):
        domain_files = [
            _included("domains/big.ndjson", "big", b"synthetic payload " * 50)
        ]
        uncapped = self.service.assemble(
            domain_files, max_compressed_bytes=10**9, **ASSEMBLE_KWARGS
        )
        exact_size = uncapped["compressed_size_bytes"]

        at_cap = self.service.assemble(
            domain_files, max_compressed_bytes=exact_size, **ASSEMBLE_KWARGS
        )
        self.assertEqual(at_cap["compressed_size_bytes"], exact_size)

        with self.assertRaises(AccountExportAssemblyError) as raised:
            self.service.assemble(
                domain_files, max_compressed_bytes=exact_size - 1, **ASSEMBLE_KWARGS
            )
        self.assertEqual(raised.exception.code, "oversize_compressed")

    def test_oversize_raises_before_any_bytes_are_produced(self):
        # A cap violation must never leave a partially built archive
        # observable -- the call either returns a complete dict or
        # raises, nothing in between.
        domain_files = [_included("domains/big.ndjson", "big", b"x" * 1000)]
        try:
            self.service.assemble(
                domain_files, max_uncompressed_bytes=1, **ASSEMBLE_KWARGS
            )
            self.fail("expected AccountExportAssemblyError")
        except AccountExportAssemblyError as error:
            self.assertEqual(error.code, "oversize_uncompressed")


class AccountExportAssemblyValidationTests(unittest.TestCase):
    def setUp(self):
        self.service = AccountExportAssemblyService()

    def _assert_invalid(self, domain_files):
        with self.assertRaises(AccountExportAssemblyError) as raised:
            self.service.assemble(domain_files, **ASSEMBLE_KWARGS)
        self.assertEqual(raised.exception.code, "invalid_domain_input")

    def test_included_requires_content_and_record_count(self):
        entry = _included("domains/x.ndjson", "x", b"{}\n")
        del entry["content"]
        self._assert_invalid([entry])

        entry = _included("domains/x.ndjson", "x", b"{}\n")
        del entry["record_count"]
        self._assert_invalid([entry])

    def test_included_forbids_omission_or_failure_reason(self):
        entry = _included("domains/x.ndjson", "x", b"{}\n", omission_reason="no")
        self._assert_invalid([entry])

    def test_excluded_forbids_content_and_requires_omission_reason(self):
        entry = _excluded("domains/x.ndjson", "x")
        entry["content"] = b"not allowed"
        self._assert_invalid([entry])

        entry = _excluded("domains/x.ndjson", "x")
        entry["omission_reason"] = None
        self._assert_invalid([entry])

    def test_unavailable_requires_exactly_one_reason(self):
        entry = _unavailable("domains/x.ndjson", "x")
        entry["failure_reason"] = None
        entry["omission_reason"] = None
        self._assert_invalid([entry])

        entry = _unavailable("domains/x.ndjson", "x")
        entry["omission_reason"] = "also set"
        self._assert_invalid([entry])

    def test_rejects_duplicate_paths(self):
        domain_files = [
            _included("domains/x.ndjson", "a", b"{}\n"),
            _included("domains/x.ndjson", "b", b"{}\n"),
        ]
        with self.assertRaises(AccountExportAssemblyError) as raised:
            self.service.assemble(domain_files, **ASSEMBLE_KWARGS)
        self.assertEqual(raised.exception.code, "duplicate_domain_path")

    def test_rejects_path_traversal_and_reserved_manifest_path(self):
        for bad_path in ("/absolute.ndjson", "../escape.ndjson", MANIFEST_PATH):
            with self.subTest(path=bad_path):
                self._assert_invalid([_included(bad_path, "x", b"{}\n")])

    def test_rejects_non_dict_entry_and_bad_schema_version(self):
        self._assert_invalid(["not-a-dict"])
        self._assert_invalid([_included("domains/x.ndjson", "x", b"{}\n", schema_version=0)])
        self._assert_invalid(
            [_included("domains/x.ndjson", "x", b"{}\n", disposition="bogus")]
        )

    def test_read_window_forbidden_outside_included(self):
        entry = _excluded("domains/x.ndjson", "x")
        entry["read_window"] = {"started_at_utc": "a", "ended_at_utc": "b"}
        self._assert_invalid([entry])

    def test_empty_domain_files_produce_a_valid_manifest_only_archive(self):
        result = self.service.assemble([], **ASSEMBLE_KWARGS)
        self.assertEqual(result["manifest"]["files"], [])
        with zipfile.ZipFile(io.BytesIO(result["archive_bytes"])) as archive:
            self.assertEqual(archive.namelist(), [MANIFEST_PATH])


if __name__ == "__main__":
    unittest.main()
