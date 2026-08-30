"""Offline contracts for PS-SETTINGS-ACCOUNT-EXPORT-READER-INTEGRATION-001:
the real-reader content source wired into scripts/run_account_export_
worker.py, replacing the retired C2 fixture-only worker.

No network, database, or provider call anywhere in this file. Every DB
interaction is driven through a small, local fake cursor/connection
(shared-queue variant of tests/test_settings_export_core_readers.py's
own AdapterModuleTests fake, needed here because a single worker run
calls MANY readers in sequence over ONE shared connection, not one
reader per fresh connection). Every synthetic value is an obvious,
entropy-dead placeholder (e.g. "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
never a realistic-looking identifier.

Run: C:\\Users\\peter\\Documents\\portfolio\\venv\\Scripts\\python.exe
-m pytest -q tests/test_account_export_integration.py
(env ANTHROPIC_API_KEY=placeholder per the project test convention).
"""

import hashlib
import io
import json
import unittest
import zipfile
from datetime import datetime
from pathlib import Path

from services.account_export_assembly_service import (
    AccountExportAssemblyError,
    AccountExportAssemblyService,
)
from services.account_export_domain_readers import DOMAINS, iter_included_readers
from services.account_export_storage_service import AccountExportStorageService

import scripts.run_account_export_worker as worker_module
from scripts.run_account_export_worker import (
    build_domain_files_from_readers,
    domain_ledger_row_matches_check_shape,
    fetch_owner_user_key,
    run_once,
    summarize_domain_ledger,
)


JOB_KEY = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
OWNER_USER_ID = 4001
OWNER_PROFILE_ID = 9001
OWNER_USER_KEY = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"

# read_consistency_marker() calls bytes(value) on whatever a "clock"
# plan step returns for a @@DBTS read, so these fake markers must
# already be bytes-shaped -- unlike SYSUTCDATETIME() clock steps
# elsewhere in this file, which return a real datetime untouched.
FAKE_DBTS_MARKER_START = b"\x00\x00\x00\x00\x00\x00\x07\xd1"
FAKE_DBTS_MARKER_CUTOFF = b"\x00\x00\x00\x00\x00\x00\x07\xd2"

# Snapshot facts about today's services/account_export_domain_readers.py
# DOMAINS registry, confirmed by direct inspection at the time this
# package was written (12 included domains / 31 readers / 18
# non-included domains / 30 domains total). A future reader package
# legitimately changes these numbers -- exactly as CR2/CR3/CR4 each did
# for their own package's own count in their own test files, CR6
# (PS-SETTINGS-EXPORT-007, which flips voice_photo from excluded to
# included, +1 included domain / +5 readers / -1 non-included domain,
# total domain count unchanged) and CR7 (PS-SETTINGS-EXPORT-008, which
# flips connection_preferences/notification_preferences/consent_history
# from excluded to included, +3 included domains / +3 readers / -3
# non-included domains, total domain count unchanged) each did for this
# file specifically, and CR8 (PS-SETTINGS-EXPORT-009, which flips the
# EXISTING career_skill_links key from excluded to included, +1
# included domain / +1 reader / -1 non-included domain, total domain
# count unchanged) -- and would need to revisit this snapshot, not
# treat it as permanently frozen.
EXPECTED_INCLUDED_DOMAIN_COUNT = 12
EXPECTED_READER_COUNT = 31
EXPECTED_NON_INCLUDED_DOMAIN_COUNT = 18
EXPECTED_TOTAL_DOMAIN_COUNT = 30


# ---------------------------------------------------------------------
# A shared-queue fake connection/cursor. Deliberately NOT the same class
# as tests/test_settings_export_core_readers.py's own AdapterModuleTests
# ._FakeCursor: that one copies its plan per cursor instance because
# each of ITS tests exercises exactly one reader call over a fresh
# connection. build_domain_files_from_readers instead calls MANY readers
# in sequence over ONE shared connection (mirroring the real worker's
# own usage), each opening its own fresh cursor -- so this fake's plan
# must be a single queue that DRAINS across every cursor a connection
# hands out, not a per-cursor copy.
# ---------------------------------------------------------------------


class SharedPlanCursor:
    def __init__(self, plan):
        self.plan = plan  # shared reference -- NOT list(plan)
        self.description = None
        self._rows = []
        self.executed = []

    def execute(self, sql, params=None):
        self.executed.append((sql, params))
        step = self.plan.pop(0)
        kind = step[0]
        if kind == "clock":
            self.description = [("now_utc",)]
            self._rows = [(step[1],)]
        elif kind == "content":
            self.description = step[1]
            self._rows = step[2]
        elif kind == "none":
            self.description = None
            self._rows = []
        elif kind == "raise":
            raise step[1]
        else:
            raise AssertionError("unknown fake step %r" % (kind,))

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return list(self._rows)


class SharedPlanConnection:
    def __init__(self, plan):
        self._plan = plan
        self.cursor_calls = 0

    def cursor(self):
        self.cursor_calls += 1
        return SharedPlanCursor(self._plan)


def _fake_row_values(reader_entry, index, row_index):
    """Deterministic, obviously-synthetic content-column values for one
    fake row, one string per real output column (the two trailing
    read-window columns are appended separately by the caller) -- keyed
    to the reader's own declared field name so a mismatched assertion
    is easy to read by eye."""

    content_fields = reader_entry["fields"][:-2]
    return tuple("FIXTURE-%s-%d-%d" % (field, index, row_index) for field in content_fields)


def build_full_domains_plan(rows_for):
    """Build the complete, ordered fake-cursor plan (and the matching
    "expected content rows per procedure" map) for EVERY DOMAINS
    included reader, in iter_included_readers()'s own order -- the
    exact order build_domain_files_from_readers calls them in, since it
    walks the same DOMAINS dict in the same fixed order.

    rows_for(index, domain_code, procedure) returns how many synthetic
    rows that one reader should "return" (0, 1, or more).
    """

    plan = []
    expected_by_procedure = {}
    for index, (domain_code, reader_entry) in enumerate(iter_included_readers()):
        procedure = reader_entry["procedure"]
        n = rows_for(index, domain_code, procedure)
        fallback_start = datetime(2026, 1, 1, 0, 0, 0)
        fallback_end = datetime(2026, 1, 1, 0, 0, 1)
        if n == 0:
            plan.append(("clock", fallback_start))
            plan.append(("none",))
            plan.append(("clock", fallback_end))
            expected_by_procedure[procedure] = {
                "domain_code": domain_code,
                "reader_entry": reader_entry,
                "rows": [],
                "read_started_at_utc": fallback_start,
                "read_ended_at_utc": fallback_end,
            }
            continue

        description = [(field,) for field in reader_entry["fields"]]
        content_fields = reader_entry["fields"][:-2]
        rows = []
        expected_rows = []
        for row_index in range(n):
            values = _fake_row_values(reader_entry, index, row_index)
            row_started = datetime(2026, 2, 1, 0, index % 24, row_index)
            row_ended = datetime(2026, 2, 1, 0, index % 24, row_index, 500000)
            rows.append(values + (row_started, row_ended))
            expected_rows.append(dict(zip(content_fields, values)))
        # These two "clock" fallback reads still happen (see
        # services/account_export_domain_readers.py's _call_reader) but
        # are UNUSED whenever content rows come back -- the content
        # rows' own trailing columns win instead.
        plan.append(("clock", "UNUSED-FALLBACK-START"))
        plan.append(("content", description, rows))
        plan.append(("clock", "UNUSED-FALLBACK-END"))
        expected_by_procedure[procedure] = {
            "domain_code": domain_code,
            "reader_entry": reader_entry,
            "rows": expected_rows,
            "read_started_at_utc": rows[0][-2],
            "read_ended_at_utc": rows[-1][-1],
        }
    return plan, expected_by_procedure


def default_rows_for(index, domain_code, procedure):
    """0/1/2 rows, cycling by reader index, so the full 22-reader
    harness exercises all three shapes (empty-included, single-row,
    multi-row) without hand-authoring a bespoke count per reader."""

    return index % 3


class FixtureTripwireRetiredTests(unittest.TestCase):
    """Pins the retirement itself: the C2 fixture-only worker and its
    confirmation tripwire are gone from this module, not merely
    superseded or left unused, and the real builder is what main()
    actually wires up."""

    def setUp(self):
        self.source = Path(worker_module.__file__).read_text(encoding="utf-8")

    def test_fixture_builder_and_env_gate_no_longer_exist_as_attributes(self):
        self.assertFalse(hasattr(worker_module, "build_fixture_domain_files"))
        self.assertFalse(hasattr(worker_module, "FIXTURE_MODE_ENV"))

    def test_fixture_source_text_is_gone_from_the_module(self):
        # The names may still appear in explanatory PROSE (this
        # module's own docstring documents what it retired and why),
        # so this checks for the actual CODE constructs, not a bare
        # substring match against the whole file including comments.
        for forbidden in (
            "def build_fixture_domain_files",
            'FIXTURE_MODE_ENV = "ACCOUNT_EXPORT_WORKER_FIXTURE_MODE_CONFIRMED"',
            "SYNTHETIC ACCOUNT EXPORT FIXTURE - NOT REAL MEMBER",
            "fixture_domain_files=",
            "os.environ.get(FIXTURE_MODE_ENV",
        ):
            self.assertNotIn(forbidden, self.source)

    def test_main_wires_the_real_builder_by_name(self):
        self.assertIn(
            "domain_files_builder=build_domain_files_from_readers", self.source
        )


class BuildDomainFilesFromRealReadersTests(unittest.TestCase):
    """The core wiring: build_domain_files_from_readers must call every
    DOMAINS included reader exactly once with the owner's own user_key,
    and must carry every other DOMAINS entry's disposition and reason
    through verbatim."""

    def test_snapshot_of_todays_domains_shape(self):
        # See the module-level comment on these constants: a future
        # reader package legitimately changes these numbers.
        included = [code for code, domain in DOMAINS.items() if domain["disposition"] == "included"]
        non_included = [code for code, domain in DOMAINS.items() if domain["disposition"] != "included"]
        self.assertEqual(len(DOMAINS), EXPECTED_TOTAL_DOMAIN_COUNT)
        self.assertEqual(len(included), EXPECTED_INCLUDED_DOMAIN_COUNT)
        self.assertEqual(len(non_included), EXPECTED_NON_INCLUDED_DOMAIN_COUNT)
        self.assertEqual(len(list(iter_included_readers())), EXPECTED_READER_COUNT)

    def test_every_included_reader_is_invoked_exactly_once_with_the_owners_user_key(self):
        plan, expected = build_full_domains_plan(default_rows_for)
        connection = SharedPlanConnection(plan)

        domain_files = build_domain_files_from_readers(connection, OWNER_USER_KEY)

        included_files = [f for f in domain_files if f["disposition"] == "included"]
        self.assertEqual(len(included_files), EXPECTED_READER_COUNT)
        self.assertEqual(connection.cursor_calls, EXPECTED_READER_COUNT)
        self.assertEqual(len(plan), 0, "every scripted step must be consumed exactly once")

    def test_structural_count_matches_domains_itself_not_a_hardcoded_number(self):
        # Drift-safe companion to the snapshot test above: even if a
        # future package changes DOMAINS' shape, this assertion stays
        # correct because it derives its own expectation from DOMAINS.
        expected_included_files = len(list(iter_included_readers()))
        expected_other_files = sum(
            1 for domain in DOMAINS.values() if domain["disposition"] != "included"
        )
        plan, _ = build_full_domains_plan(default_rows_for)
        connection = SharedPlanConnection(plan)

        domain_files = build_domain_files_from_readers(connection, OWNER_USER_KEY)

        included_files = [f for f in domain_files if f["disposition"] == "included"]
        other_files = [f for f in domain_files if f["disposition"] != "included"]
        self.assertEqual(len(included_files), expected_included_files)
        self.assertEqual(len(other_files), expected_other_files)
        self.assertEqual(len(domain_files), expected_included_files + expected_other_files)

    def test_excluded_and_unavailable_domains_carry_the_domains_reason_verbatim(self):
        plan, _ = build_full_domains_plan(default_rows_for)
        connection = SharedPlanConnection(plan)
        domain_files = build_domain_files_from_readers(connection, OWNER_USER_KEY)

        by_domain_code = {f["domain_code"]: f for f in domain_files if f["disposition"] != "included"}
        for domain_code, domain in DOMAINS.items():
            if domain["disposition"] == "included":
                continue
            with self.subTest(domain=domain_code):
                file_entry = by_domain_code[domain_code]
                self.assertEqual(file_entry["disposition"], domain["disposition"])
                if domain["disposition"] == "excluded":
                    self.assertEqual(file_entry["omission_reason"], domain["reason"])
                    self.assertIsNone(file_entry["failure_reason"])
                else:  # unavailable
                    self.assertEqual(file_entry["failure_reason"], domain["reason"])
                    self.assertIsNone(file_entry["omission_reason"])
                self.assertIsNotNone(domain["reason"])

    def test_zero_row_reader_produces_a_valid_empty_included_file(self):
        def all_zero(index, domain_code, procedure):
            return 0

        plan, expected = build_full_domains_plan(all_zero)
        connection = SharedPlanConnection(plan)
        domain_files = build_domain_files_from_readers(connection, OWNER_USER_KEY)

        included_files = [f for f in domain_files if f["disposition"] == "included"]
        self.assertEqual(len(included_files), EXPECTED_READER_COUNT)
        for file_entry in included_files:
            with self.subTest(path=file_entry["path"]):
                self.assertEqual(file_entry["content"], b"")
                self.assertEqual(file_entry["record_count"], 0)

        # And the whole thing still assembles cleanly end to end.
        service = AccountExportAssemblyService()
        assembled = service.assemble(
            domain_files,
            job_key=JOB_KEY,
            requested_at_utc="2026-08-28T12:00:00.000000Z",
            assembly_started_at_utc="2026-08-28T12:00:01.000000Z",
            assembly_cutoff_at_utc="2026-08-28T12:00:02.000000Z",
        )
        self.assertEqual(assembled["uncompressed_size_bytes"], 0)

    def test_multi_row_reader_content_round_trips_through_ndjson(self):
        def two_rows_for_first_reader(index, domain_code, procedure):
            return 2 if index == 0 else 0

        plan, expected = build_full_domains_plan(two_rows_for_first_reader)
        connection = SharedPlanConnection(plan)
        domain_files = build_domain_files_from_readers(connection, OWNER_USER_KEY)

        first_procedure = next(iter(expected))
        first_expected = expected[first_procedure]
        matching = [
            f
            for f in domain_files
            if f["disposition"] == "included" and f["schema_id"] == first_expected["reader_entry"]["schema_id"]
        ]
        self.assertEqual(len(matching), 1)
        file_entry = matching[0]
        self.assertEqual(file_entry["record_count"], 2)

        lines = [line for line in file_entry["content"].split(b"\n") if line]
        self.assertEqual(len(lines), 2)
        decoded_rows = [json.loads(line) for line in lines]
        self.assertEqual(decoded_rows, first_expected["rows"])
        for line in lines:
            self.assertNotIn(b", ", line)
            self.assertNotIn(b": ", line)

    def test_read_window_uses_the_readers_own_timestamps_not_a_shared_clock(self):
        plan, expected = build_full_domains_plan(default_rows_for)
        connection = SharedPlanConnection(plan)
        domain_files = build_domain_files_from_readers(connection, OWNER_USER_KEY)

        by_schema_id = {f["schema_id"]: f for f in domain_files if f["disposition"] == "included"}
        for procedure, info in expected.items():
            schema_id = info["reader_entry"]["schema_id"]
            with self.subTest(procedure=procedure):
                file_entry = by_schema_id[schema_id]
                self.assertEqual(
                    file_entry["read_window"]["started_at_utc"],
                    worker_module._iso_z(info["read_started_at_utc"]),
                )
                self.assertEqual(
                    file_entry["read_window"]["ended_at_utc"],
                    worker_module._iso_z(info["read_ended_at_utc"]),
                )

    def test_all_paths_are_unique(self):
        plan, _ = build_full_domains_plan(default_rows_for)
        connection = SharedPlanConnection(plan)
        domain_files = build_domain_files_from_readers(connection, OWNER_USER_KEY)

        paths = [f["path"] for f in domain_files]
        self.assertEqual(len(paths), len(set(paths)))

    def test_provenance_records_the_exact_reader_procedure(self):
        plan, expected = build_full_domains_plan(default_rows_for)
        connection = SharedPlanConnection(plan)
        domain_files = build_domain_files_from_readers(connection, OWNER_USER_KEY)

        by_schema_id = {f["schema_id"]: f for f in domain_files if f["disposition"] == "included"}
        for procedure, info in expected.items():
            schema_id = info["reader_entry"]["schema_id"]
            with self.subTest(procedure=procedure):
                self.assertEqual(
                    by_schema_id[schema_id]["provenance"]["reader_procedure"], procedure
                )

    def test_a_reader_exception_propagates_uncaught(self):
        # build_domain_files_from_readers must not swallow or partially
        # tolerate a failing reader -- a partial export would be a
        # truth violation. The failure belongs to run_once's own
        # generic exception handling (see RunOnceOrchestrationTests).
        plan = [("raise", RuntimeError("synthetic reader failure"))]
        connection = SharedPlanConnection(plan)
        with self.assertRaises(RuntimeError):
            build_domain_files_from_readers(connection, OWNER_USER_KEY)

    def test_builder_never_calls_connection_lifetime_methods(self):
        class LifetimeGuardConnection(SharedPlanConnection):
            def commit(self):
                raise AssertionError("builder must never commit the caller's connection")

            def rollback(self):
                raise AssertionError("builder must never roll back the caller's connection")

            def close(self):
                raise AssertionError("builder must never close the caller's connection")

        plan, _ = build_full_domains_plan(default_rows_for)
        connection = LifetimeGuardConnection(plan)
        build_domain_files_from_readers(connection, OWNER_USER_KEY)  # must not raise


class FetchOwnerUserKeyTests(unittest.TestCase):
    class FakeCursor:
        def __init__(self, row):
            self._row = row
            self.executed = None

        def execute(self, sql, params):
            self.executed = (sql, params)

        def fetchone(self):
            return self._row

    def test_returns_the_owners_own_user_key_when_the_row_matches(self):
        cursor = self.FakeCursor(row=(OWNER_USER_KEY,))
        result = fetch_owner_user_key(cursor, OWNER_USER_ID, OWNER_PROFILE_ID)
        self.assertEqual(result, OWNER_USER_KEY)
        sql, params = cursor.executed
        self.assertIn("app_users", sql)
        self.assertIn("member_profiles", sql)
        self.assertIn("user_key", sql)
        self.assertIn("active = 1", sql)
        self.assertEqual(params, (OWNER_USER_ID, OWNER_PROFILE_ID))

    def test_returns_none_when_no_row_matches(self):
        cursor = self.FakeCursor(row=None)
        self.assertIsNone(fetch_owner_user_key(cursor, OWNER_USER_ID, OWNER_PROFILE_ID))

    def test_never_accepts_a_caller_selected_user_key(self):
        # The function's own signature is the proof: it takes only the
        # two already-resolved internal ids, never a @UserKey/user_key
        # argument of any kind.
        import inspect

        parameters = list(inspect.signature(fetch_owner_user_key).parameters)
        self.assertEqual(parameters, ["cursor", "owner_user_id", "owner_profile_id"])


class IsoZDeterminismTests(unittest.TestCase):
    """_iso_z's fixed-width fix, load-bearing for summarize_domain_
    ledger's string min()/max() below."""

    def test_zero_and_nonzero_microseconds_produce_the_same_width(self):
        zero = worker_module._iso_z(datetime(2026, 8, 28, 12, 0, 0, 0))
        nonzero = worker_module._iso_z(datetime(2026, 8, 28, 12, 0, 0, 500000))
        self.assertEqual(len(zero), len(nonzero))
        self.assertTrue(zero.endswith("Z"))
        self.assertTrue(nonzero.endswith("Z"))

    def test_lexical_order_matches_chronological_order_across_microsecond_boundary(self):
        earlier = datetime(2026, 8, 28, 12, 0, 0, 0)
        later = datetime(2026, 8, 28, 12, 0, 0, 500000)
        self.assertLess(worker_module._iso_z(earlier), worker_module._iso_z(later))

    def test_iso_z_or_none_passes_through_none(self):
        self.assertIsNone(worker_module._iso_z_or_none(None))
        self.assertIsNotNone(worker_module._iso_z_or_none(datetime(2026, 1, 1)))


class DeterminismStatementTests(unittest.TestCase):
    """Confirms the precise, disclosed determinism statement: assemble()
    itself is still a pure function; a live run across separate worker
    attempts is not byte-identical once real read windows differ."""

    def test_assemble_is_still_pure_given_identical_real_reader_shaped_input(self):
        plan, _ = build_full_domains_plan(default_rows_for)
        connection = SharedPlanConnection(plan)
        domain_files = build_domain_files_from_readers(connection, OWNER_USER_KEY)

        service = AccountExportAssemblyService()
        kwargs = dict(
            job_key=JOB_KEY,
            requested_at_utc="2026-08-28T12:00:00.000000Z",
            assembly_started_at_utc="2026-08-28T12:00:01.000000Z",
            assembly_cutoff_at_utc="2026-08-28T12:00:02.000000Z",
        )
        first = service.assemble(domain_files, **kwargs)
        second = service.assemble(domain_files, **kwargs)
        self.assertEqual(first["archive_bytes"], second["archive_bytes"])
        self.assertEqual(first["sha256"], second["sha256"])

    def test_two_separate_attempts_with_different_read_windows_differ(self):
        # Same underlying row VALUES, but the fake clock/content
        # timestamps differ between the two plans -- exactly what a
        # real retry against unchanged data would look like, since
        # every reader call captures a fresh wall-clock read window.
        def rows_for(index, domain_code, procedure):
            return 1 if index == 0 else 0

        plan_one, _ = build_full_domains_plan(rows_for)
        plan_two, _ = build_full_domains_plan(rows_for)
        # Shift every timestamp in the second plan forward so the two
        # attempts' read windows genuinely differ, while row VALUES
        # (built from `index`/`row_index` only, not from the plan's
        # timestamps) stay identical.
        def _shift(step):
            if step[0] == "clock":
                value = step[1]
                if isinstance(value, datetime):
                    value = value.replace(hour=(value.hour + 1) % 24)
                return ("clock", value)
            if step[0] == "content":
                shifted_rows = [
                    row[:-2] + (row[-2].replace(hour=(row[-2].hour + 1) % 24), row[-1].replace(hour=(row[-1].hour + 1) % 24))
                    for row in step[2]
                ]
                return ("content", step[1], shifted_rows)
            return step

        plan_two = [_shift(step) for step in plan_two]

        connection_one = SharedPlanConnection(plan_one)
        connection_two = SharedPlanConnection(plan_two)
        domain_files_one = build_domain_files_from_readers(connection_one, OWNER_USER_KEY)
        domain_files_two = build_domain_files_from_readers(connection_two, OWNER_USER_KEY)

        service = AccountExportAssemblyService()
        kwargs = dict(
            job_key=JOB_KEY,
            requested_at_utc="2026-08-28T12:00:00.000000Z",
            assembly_started_at_utc="2026-08-28T12:00:01.000000Z",
            assembly_cutoff_at_utc="2026-08-28T12:00:02.000000Z",
        )
        first = service.assemble(domain_files_one, **kwargs)
        second = service.assemble(domain_files_two, **kwargs)

        # The row CONTENT is identical (content fields never depend on
        # the plan's own timestamps)...
        self.assertEqual(domain_files_one[0]["content"], domain_files_two[0]["content"])
        # ...but the read-window-bearing manifest, and therefore the
        # final archive bytes and hash, legitimately differ -- the
        # precise, disclosed determinism statement this package makes.
        self.assertNotEqual(first["manifest"], second["manifest"])
        self.assertNotEqual(first["sha256"], second["sha256"])


class ManifestLedgerZipThreeWayAgreementTests(unittest.TestCase):
    """The package's central proof: manifest per-file facts, the actual
    bytes serialized into the ZIP, and the ledger-shaped domain summary
    all provably agree."""

    def setUp(self):
        plan, self.expected = build_full_domains_plan(default_rows_for)
        connection = SharedPlanConnection(plan)
        self.domain_files = build_domain_files_from_readers(connection, OWNER_USER_KEY)

        self.service = AccountExportAssemblyService()
        self.assembled = self.service.assemble(
            self.domain_files,
            job_key=JOB_KEY,
            requested_at_utc="2026-08-28T12:00:00.000000Z",
            assembly_started_at_utc="2026-08-28T12:00:01.000000Z",
            assembly_cutoff_at_utc="2026-08-28T12:00:02.000000Z",
        )
        self.manifest = self.assembled["manifest"]
        self.archive = zipfile.ZipFile(io.BytesIO(self.assembled["archive_bytes"]))

    def tearDown(self):
        self.archive.close()

    def test_manifest_record_count_matches_actual_ndjson_lines_in_the_zip(self):
        included_files = [f for f in self.manifest["files"] if f["disposition"] == "included"]
        self.assertEqual(len(included_files), EXPECTED_READER_COUNT)
        for file_entry in included_files:
            with self.subTest(path=file_entry["path"]):
                content = self.archive.read(file_entry["path"])
                lines = [line for line in content.split(b"\n") if line]
                self.assertEqual(len(lines), file_entry["record_count"])
                self.assertEqual(len(content), file_entry["byte_length"])
                self.assertEqual(hashlib.sha256(content).hexdigest(), file_entry["sha256"])

    def test_every_domain_appears_exactly_once_in_the_ledger_summary(self):
        summary = summarize_domain_ledger(self.manifest)
        self.assertEqual(set(summary.keys()), set(DOMAINS.keys()))
        self.assertEqual(len(summary), EXPECTED_TOTAL_DOMAIN_COUNT)

    def test_domain_ledger_summary_totals_match_manifest_totals_per_domain(self):
        summary = summarize_domain_ledger(self.manifest)
        files_by_domain = {}
        for file_entry in self.manifest["files"]:
            files_by_domain.setdefault(file_entry["domain_code"], []).append(file_entry)

        for domain_code, files in files_by_domain.items():
            with self.subTest(domain=domain_code):
                row = summary[domain_code]
                if files[0]["disposition"] == "included":
                    self.assertEqual(
                        row["record_count"], sum(f["record_count"] for f in files)
                    )
                    self.assertEqual(
                        row["byte_count"], sum(f["byte_length"] for f in files)
                    )
                else:
                    self.assertIsNone(row["record_count"])
                    self.assertIsNone(row["byte_count"])

    def test_domain_ledger_summary_rows_all_satisfy_the_real_check_constraint_shape(self):
        summary = summarize_domain_ledger(self.manifest)
        for domain_code, row in summary.items():
            with self.subTest(domain=domain_code):
                self.assertTrue(domain_ledger_row_matches_check_shape(row))

    def test_aggregate_uncompressed_size_equals_sum_of_included_domain_byte_counts(self):
        summary = summarize_domain_ledger(self.manifest)
        total = sum(
            row["byte_count"] for row in summary.values() if row["disposition"] == "included"
        )
        self.assertEqual(total, self.assembled["uncompressed_size_bytes"])

    def test_full_pipeline_through_the_real_storage_adapter_agrees_on_final_bytes(self):
        # Closes the third leg of the proof: the AGGREGATE facts that
        # actually reach the C1 ledger row (via usp_CompleteAccountExportJob)
        # come from AccountExportStorageService.promote()'s own
        # independent readback, which must agree with what assembly
        # itself already computed and what the ledger summary reports.
        class FakeBlob:
            def __init__(self, container, name):
                self.container = container
                self.name = name

            def get_blob_properties(self):
                from types import SimpleNamespace

                return SimpleNamespace(size=len(self.container.payloads[self.name]))

            def download_blob(self):
                from types import SimpleNamespace

                payload = self.container.payloads[self.name]
                return SimpleNamespace(readall=lambda: payload)

        class FakeContainer:
            def __init__(self):
                self.payloads = {}

            def upload_blob(self, **kwargs):
                from azure.core.exceptions import ResourceExistsError

                if kwargs["name"] in self.payloads:
                    raise ResourceExistsError("already exists")
                self.payloads[kwargs["name"]] = kwargs["data"]

            def get_blob_client(self, name):
                return FakeBlob(self, name)

            def delete_blob(self, name, **kwargs):
                from azure.core.exceptions import ResourceNotFoundError

                if name not in self.payloads:
                    raise ResourceNotFoundError("absent")
                del self.payloads[name]

        storage = AccountExportStorageService(
            account_url="https://synthetic.blob.core.windows.net",
            container_name="private-account-export",
        )
        storage._container_client = FakeContainer()

        storage.stage(JOB_KEY, 1, self.assembled["archive_bytes"])
        promoted = storage.promote(JOB_KEY, 1)

        self.assertEqual(promoted["sha256"], self.assembled["sha256"])
        self.assertEqual(
            promoted["compressed_size_bytes"], self.assembled["compressed_size_bytes"]
        )
        self.assertEqual(
            promoted["uncompressed_size_bytes"], self.assembled["uncompressed_size_bytes"]
        )
        summary = summarize_domain_ledger(self.manifest)
        ledger_total = sum(
            row["byte_count"] for row in summary.values() if row["disposition"] == "included"
        )
        self.assertEqual(promoted["uncompressed_size_bytes"], ledger_total)


class SummarizeDomainLedgerValidationTests(unittest.TestCase):
    """Defensive unit tests of the aggregator itself, independent of a
    real assembled manifest."""

    def _manifest(self, files):
        return {"files": files}

    def test_mixed_disposition_within_one_domain_code_is_rejected(self):
        manifest = self._manifest(
            [
                {
                    "domain_code": "x",
                    "disposition": "included",
                    "path": "domains/x/a.ndjson",
                    "record_count": 1,
                    "byte_length": 2,
                    "sha256": "a" * 64,
                    "read_window": {"started_at_utc": "2026-01-01T00:00:00.000000Z", "ended_at_utc": "2026-01-01T00:00:01.000000Z"},
                },
                {
                    "domain_code": "x",
                    "disposition": "excluded",
                    "path": "domains/x.omitted.json",
                    "omission_reason": "test",
                    "failure_reason": None,
                },
            ]
        )
        with self.assertRaises(ValueError):
            summarize_domain_ledger(manifest)

    def test_multiple_non_included_files_for_one_domain_is_rejected(self):
        entry = {
            "domain_code": "x",
            "disposition": "excluded",
            "path": "domains/x.omitted.json",
            "omission_reason": "test",
            "failure_reason": None,
        }
        manifest = self._manifest([dict(entry), dict(entry)])
        with self.assertRaises(ValueError):
            summarize_domain_ledger(manifest)

    def test_empty_manifest_produces_an_empty_summary(self):
        self.assertEqual(summarize_domain_ledger(self._manifest([])), {})

    def test_included_domain_sha256_is_computed_over_sorted_file_hashes_not_one_files_own(self):
        manifest = self._manifest(
            [
                {
                    "domain_code": "x",
                    "disposition": "included",
                    "path": "domains/x/b.ndjson",
                    "record_count": 1,
                    "byte_length": 2,
                    "sha256": "b" * 64,
                    "read_window": {"started_at_utc": "2026-01-01T00:00:01.000000Z", "ended_at_utc": "2026-01-01T00:00:02.000000Z"},
                },
                {
                    "domain_code": "x",
                    "disposition": "included",
                    "path": "domains/x/a.ndjson",
                    "record_count": 3,
                    "byte_length": 4,
                    "sha256": "a" * 64,
                    "read_window": {"started_at_utc": "2026-01-01T00:00:00.000000Z", "ended_at_utc": "2026-01-01T00:00:03.000000Z"},
                },
            ]
        )
        summary = summarize_domain_ledger(manifest)
        expected_hash = hashlib.sha256(("a" * 64 + "b" * 64).encode("ascii")).hexdigest()
        self.assertEqual(summary["x"]["content_sha256"], expected_hash)
        self.assertNotIn(summary["x"]["content_sha256"], ("a" * 64, "b" * 64))
        self.assertEqual(summary["x"]["record_count"], 4)
        self.assertEqual(summary["x"]["byte_count"], 6)
        self.assertEqual(summary["x"]["read_started_at_utc"], "2026-01-01T00:00:00.000000Z")
        self.assertEqual(summary["x"]["read_ended_at_utc"], "2026-01-01T00:00:03.000000Z")


class DomainLedgerRowMatchesCheckShapeTests(unittest.TestCase):
    """Direct unit tests of the CHECK re-implementation, independent of
    summarize_domain_ledger, so a bug in one cannot hide a bug in the
    other."""

    def _row(self, disposition, **overrides):
        base = {
            "disposition": disposition,
            "read_started_at_utc": None,
            "read_ended_at_utc": None,
            "record_count": None,
            "byte_count": None,
            "content_sha256": None,
            "omission_reason": None,
            "failure_reason": None,
        }
        base.update(overrides)
        return base

    def test_included_requires_every_read_fact_and_no_reason(self):
        valid = self._row(
            "included",
            read_started_at_utc="s",
            read_ended_at_utc="e",
            record_count=1,
            byte_count=1,
            content_sha256="a" * 64,
        )
        self.assertTrue(domain_ledger_row_matches_check_shape(valid))
        for missing_field in ("read_started_at_utc", "read_ended_at_utc", "record_count", "byte_count", "content_sha256"):
            with self.subTest(missing=missing_field):
                broken = dict(valid)
                broken[missing_field] = None
                self.assertFalse(domain_ledger_row_matches_check_shape(broken))
        with_reason = dict(valid)
        with_reason["omission_reason"] = "should not be here"
        self.assertFalse(domain_ledger_row_matches_check_shape(with_reason))

    def test_excluded_requires_only_omission_reason(self):
        valid = self._row("excluded", omission_reason="reason")
        self.assertTrue(domain_ledger_row_matches_check_shape(valid))
        with_failure = dict(valid)
        with_failure["failure_reason"] = "also set"
        self.assertFalse(domain_ledger_row_matches_check_shape(with_failure))
        without_reason = self._row("excluded")
        self.assertFalse(domain_ledger_row_matches_check_shape(without_reason))

    def test_unavailable_requires_exactly_one_reason(self):
        with_omission = self._row("unavailable", omission_reason="reason")
        with_failure = self._row("unavailable", failure_reason="reason")
        self.assertTrue(domain_ledger_row_matches_check_shape(with_omission))
        self.assertTrue(domain_ledger_row_matches_check_shape(with_failure))
        neither = self._row("unavailable")
        both = self._row("unavailable", omission_reason="a", failure_reason="b")
        self.assertFalse(domain_ledger_row_matches_check_shape(neither))
        self.assertFalse(domain_ledger_row_matches_check_shape(both))

    def test_unknown_disposition_is_rejected(self):
        self.assertFalse(domain_ledger_row_matches_check_shape(self._row("bogus")))


class RunOnceOrchestrationTests(unittest.TestCase):
    """End-to-end run_once tests using a small, hand-built fake builder
    (not the full 22-reader harness -- that is exercised directly by
    BuildDomainFilesFromRealReadersTests above), a fake storage double,
    and the REAL, unmodified assembly service (pure, no I/O)."""

    class FakeStorage:
        def __init__(self):
            self.staged = {}
            self.staged_calls = []
            self.cleanup_calls = []
            self.promote_result = None
            self.promote_error = None

        def stage(self, job_key, attempt, data):
            self.staged_calls.append((job_key, attempt, len(data)))
            self.staged[(job_key, attempt)] = data

        def promote(self, job_key, attempt):
            if self.promote_error is not None:
                raise self.promote_error
            data = self.staged[(job_key, attempt)]
            import hashlib as _hashlib

            self.promote_result = {
                "reference": "export/v1/final/%s.zip" % job_key,
                "sha256": _hashlib.sha256(data).hexdigest(),
                "compressed_size_bytes": len(data),
                "uncompressed_size_bytes": len(data),
            }
            return self.promote_result

        def cleanup_staging(self, job_key, attempt):
            self.cleanup_calls.append((job_key, attempt))

    def setUp(self):
        self._original_storage = worker_module.account_export_storage_service
        self.fake_storage = self.FakeStorage()
        worker_module.account_export_storage_service = self.fake_storage

    def tearDown(self):
        worker_module.account_export_storage_service = self._original_storage

    def _claim_step(self):
        columns = [
            ("job_key",), ("owner_user_id",), ("owner_profile_id",),
            ("attempt_count",), ("lease_token",), ("lease_expires_at_utc",),
        ]
        row = (JOB_KEY, OWNER_USER_ID, OWNER_PROFILE_ID, 1, "lease-token-1", datetime(2026, 1, 1))
        return ("content", columns, [row])

    def _owner_active_step(self, active=True):
        return ("content", [("one",)], [(1,)]) if active else ("none",)

    def _user_key_step(self):
        return ("content", [("user_key",)], [(OWNER_USER_KEY,)])

    def test_claim_returns_nothing_yields_idle_outcome(self):
        plan = [("none",)]
        connection = SharedPlanConnection(plan)
        result = run_once(connection, domain_files_builder=lambda c, k: (_ for _ in ()).throw(AssertionError("must not be called")))
        self.assertEqual(result, {"outcome": "idle"})

    def test_inactive_owner_fails_without_touching_the_builder_or_storage(self):
        plan = [
            self._claim_step(),
            self._owner_active_step(active=False),
            ("content", [("ok",)], [(1,)]),  # fail_job's own EXEC (no result set needed, but harmless)
        ]
        connection = SharedPlanConnection(plan)

        def guard_builder(connection_arg, user_key):
            raise AssertionError("domain_files_builder must not be called for an inactive owner")

        result = run_once(connection, domain_files_builder=guard_builder)
        self.assertEqual(result["outcome"], "failed")
        self.assertEqual(result["failure_code"], worker_module.OWNER_INACTIVE_FAILURE_CODE)
        self.assertEqual(self.fake_storage.staged_calls, [])

    def test_happy_path_builds_assembles_stages_promotes_and_completes(self):
        def small_builder(connection_arg, user_key):
            self.assertEqual(user_key, OWNER_USER_KEY)
            return [
                {
                    "path": "domains/account/account.ndjson",
                    "domain_code": "account",
                    "schema_id": "peerslate.account_export.account.account.v1",
                    "schema_version": 1,
                    "disposition": "included",
                    "content": b'{"display_name":"FIXTURE"}\n',
                    "record_count": 1,
                    "read_window": {
                        "started_at_utc": "2026-01-01T00:00:00.000000Z",
                        "ended_at_utc": "2026-01-01T00:00:01.000000Z",
                    },
                },
                {
                    "path": "domains/journal.omitted.json",
                    "domain_code": "journal",
                    "schema_id": "peerslate.account_export.journal.v1",
                    "schema_version": 1,
                    "disposition": "unavailable",
                    "failure_reason": "synthetic reason",
                },
            ]

        plan = [
            self._claim_step(),
            self._owner_active_step(active=True),
            self._user_key_step(),
            ("clock", FAKE_DBTS_MARKER_START),
            ("clock", FAKE_DBTS_MARKER_CUTOFF),
            ("content", [("requested_at_utc",)], [(datetime(2025, 12, 31, 23, 0, 0),)]),
            ("content", [("ok",)], [(1,)]),  # complete_job's own EXEC
        ]
        connection = SharedPlanConnection(plan)

        result = run_once(connection, domain_files_builder=small_builder)

        self.assertEqual(result, {"outcome": "completed", "job_key": JOB_KEY})
        self.assertEqual(len(self.fake_storage.staged_calls), 1)
        self.assertEqual(self.fake_storage.staged_calls[0][0], JOB_KEY)
        self.assertEqual(self.fake_storage.staged_calls[0][1], 1)
        self.assertIsNotNone(self.fake_storage.promote_result)

    def test_a_domain_reader_exception_fails_the_job_not_crashes(self):
        def raising_builder(connection_arg, user_key):
            raise RuntimeError("synthetic reader failure")

        plan = [
            self._claim_step(),
            self._owner_active_step(active=True),
            self._user_key_step(),
            ("clock", FAKE_DBTS_MARKER_START),
            ("content", [("ok",)], [(1,)]),  # fail_job's own EXEC
        ]
        connection = SharedPlanConnection(plan)

        result = run_once(connection, domain_files_builder=raising_builder)

        self.assertEqual(result["outcome"], "failed")
        self.assertEqual(result["failure_code"], "internal_error")
        self.assertEqual(self.fake_storage.staged_calls, [])

    def test_oversize_content_fails_the_job_not_crashes(self):
        # Isolates run_once's OWN reaction to a cap breach -- the cap
        # arithmetic itself is already separately proven in
        # tests/test_account_export_assembly.py's own boundary tests.
        def oversize_builder(connection_arg, user_key):
            raise AccountExportAssemblyError("oversize_uncompressed")

        plan = [
            self._claim_step(),
            self._owner_active_step(active=True),
            self._user_key_step(),
            ("clock", FAKE_DBTS_MARKER_START),
            ("content", [("ok",)], [(1,)]),  # fail_job's own EXEC
        ]
        connection = SharedPlanConnection(plan)

        result = run_once(connection, domain_files_builder=oversize_builder)

        self.assertEqual(result["outcome"], "failed")
        self.assertEqual(result["failure_code"], "oversize_uncompressed")

    def test_ledger_shape_backstop_fails_the_job_when_a_manifest_would_violate_the_check(self):
        # A defensive, should-never-happen backstop: force
        # summarize_domain_ledger to see two conflicting dispositions
        # for the same domain_code by having the builder emit a
        # duplicate domain_code with different dispositions, then
        # confirm run_once fails safely instead of completing a job
        # whose own manifest could not satisfy the real CHECK.
        def broken_builder(connection_arg, user_key):
            return [
                {
                    "path": "domains/x/a.ndjson",
                    "domain_code": "x",
                    "schema_id": "peerslate.x.a.v1",
                    "schema_version": 1,
                    "disposition": "included",
                    "content": b'{}\n',
                    "record_count": 1,
                    "read_window": {
                        "started_at_utc": "2026-01-01T00:00:00.000000Z",
                        "ended_at_utc": "2026-01-01T00:00:01.000000Z",
                    },
                },
                {
                    "path": "domains/x.omitted.json",
                    "domain_code": "x",
                    "schema_id": "peerslate.x.v1",
                    "schema_version": 1,
                    "disposition": "excluded",
                    "omission_reason": "synthetic",
                },
            ]

        plan = [
            self._claim_step(),
            self._owner_active_step(active=True),
            self._user_key_step(),
            ("clock", FAKE_DBTS_MARKER_START),
            ("clock", FAKE_DBTS_MARKER_CUTOFF),
            ("content", [("requested_at_utc",)], [(datetime(2025, 12, 31, 23, 0, 0),)]),
            ("content", [("ok",)], [(1,)]),  # fail_job's own EXEC
        ]
        connection = SharedPlanConnection(plan)

        result = run_once(connection, domain_files_builder=broken_builder)

        self.assertEqual(result["outcome"], "failed")
        self.assertEqual(result["failure_code"], "internal_error")
        self.assertEqual(self.fake_storage.staged_calls, [])

    def test_ledger_shape_backstop_itself_fails_the_job_on_a_shape_invalid_row(self):
        # Independent-review finding F1: the test above never reaches the
        # per-row CHECK-shape backstop -- summarize_domain_ledger's own
        # mixed-disposition guard raises first. This test reaches the
        # backstop itself by substituting summarize_domain_ledger's
        # result directly: an "included" row carrying an omission_reason
        # violates the real CK_account_export_job_domains_shape logic,
        # so run_once must fail the job through the backstop, never
        # complete it, and never touch storage. Deleting or bypassing
        # the backstop loop turns this test red.
        def valid_builder(connection_arg, user_key):
            return [
                {
                    "path": "domains/x/a.ndjson",
                    "domain_code": "x",
                    "schema_id": "peerslate.x.a.v1",
                    "schema_version": 1,
                    "disposition": "included",
                    "content": b'{}\n',
                    "record_count": 1,
                    "read_window": {
                        "started_at_utc": "2026-01-01T00:00:00.000000Z",
                        "ended_at_utc": "2026-01-01T00:00:01.000000Z",
                    },
                },
            ]

        shape_invalid_summary = {
            "x": {
                "disposition": "included",
                "read_started_at_utc": "2026-01-01T00:00:00.000000Z",
                "read_ended_at_utc": "2026-01-01T00:00:01.000000Z",
                "record_count": 1,
                "byte_count": 3,
                "content_sha256": "a" * 64,
                "omission_reason": "included-rows-must-never-carry-one",
                "failure_reason": None,
            }
        }
        # Self-check: the fixture really is shape-invalid under the real
        # check function, so the assertion below cannot pass vacuously.
        self.assertFalse(
            domain_ledger_row_matches_check_shape(shape_invalid_summary["x"])
        )

        plan = [
            self._claim_step(),
            self._owner_active_step(active=True),
            self._user_key_step(),
            ("clock", FAKE_DBTS_MARKER_START),
            ("clock", FAKE_DBTS_MARKER_CUTOFF),
            ("content", [("requested_at_utc",)], [(datetime(2025, 12, 31, 23, 0, 0),)]),
            ("content", [("ok",)], [(1,)]),  # fail_job's own EXEC
        ]
        connection = SharedPlanConnection(plan)

        original = worker_module.summarize_domain_ledger
        worker_module.summarize_domain_ledger = (
            lambda manifest: shape_invalid_summary
        )
        try:
            result = run_once(connection, domain_files_builder=valid_builder)
        finally:
            worker_module.summarize_domain_ledger = original

        self.assertEqual(result["outcome"], "failed")
        self.assertEqual(result["failure_code"], "internal_error")
        self.assertEqual(self.fake_storage.staged_calls, [])


if __name__ == "__main__":
    unittest.main()
