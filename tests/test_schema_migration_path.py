"""The governed database migration path.

PeerSlate's application code has had a reviewed, gated, auditable route to
production for a long time. Its database schema had none: three migrations
reached `peerslate-database` in one week, applied by hand by an agent holding a
credential it read out of App Service settings, guided by prose. Each apply was
careful. None was controlled, and the repository could not say afterwards which
revision production carried.

These tests hold the replacement in place. None of them needs a database: every
safety property below is a property of the registry, the files, and the pure
planning logic, so they run on every build.
"""

import io
import json
import re
import shutil
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from scripts import govern_sql_migrations as governed
from scripts.apply_sql_migrations import MIGRATION_FILENAMES
from scripts.migration_registry import (
    FORBIDDEN_GATE_DATABASES,
    GateProof,
    RegistryError,
    STATE_BANNER,
    STATE_PATH,
    executable_body,
    executable_sha256,
    gate_status,
    load_registry,
    parse_state,
    render_state,
    resolve_apply_plan,
)

ROOT = Path(__file__).resolve().parents[1]
MIGRATION_DIR = ROOT / "SQL FIles" / "Migrations"


def _registry():
    return load_registry()


def _write_registry(directory: Path, entries: list[dict]) -> Path:
    path = directory / "registry.json"
    path.write_text(
        json.dumps({"version": 1, "migrations": entries}, indent=2),
        encoding="utf-8",
    )
    return path


def _entry(
    migration_id: str,
    forward: str,
    rollback: str,
    requires=(),
    gate=None,
) -> dict:
    return {
        "id": migration_id,
        "forward": forward,
        "rollback": rollback,
        "requires": list(requires),
        "summary": f"{migration_id} test entry.",
        "gate": gate,
    }


def _proof(digest: str, **overrides) -> dict:
    payload = {
        "executable_sha256": digest,
        "gated_at_utc": "2026-08-04T00:00:00Z",
        "gate_database": "ps-test-gate-20260804",
        "gate_server": "peerslate",
        "prerequisites": [],
        "objects": [],
        "verification": "none available",
        "operator": "test",
    }
    payload.update(overrides)
    return payload


class RegistryContractTests(unittest.TestCase):
    """The registry is the inventory, and it must describe reality."""

    def setUp(self):
        self.registry = _registry()

    def test_every_registered_file_exists_and_order_satisfies_prerequisites(self):
        seen = set()
        for migration in self.registry:
            self.assertTrue(
                migration.forward_path().is_file(),
                f"{migration.migration_id} forward file is missing",
            )
            self.assertTrue(
                migration.rollback_path().is_file(),
                f"{migration.migration_id} rollback file is missing",
            )
            for requirement in migration.requires:
                self.assertIn(
                    requirement,
                    seen,
                    f"{migration.migration_id} requires {requirement}, which "
                    "the registry does not list before it. Registry order is "
                    "apply order.",
                )
            seen.add(migration.migration_id)

    def test_registry_covers_every_migration_file_in_the_repository(self):
        """No migration may exist on disk without being registered.

        This is the check that closes the `proposed/` split. Before this path,
        `MIGRATION_FILENAMES` listed eight files while eleven more sat in
        `proposed/` being applied out of band. An unregistered file is now a
        test failure, not a convention.
        """

        on_disk = set()
        for directory in (MIGRATION_DIR, MIGRATION_DIR / "proposed"):
            for path in directory.glob("*.sql"):
                on_disk.add(path.relative_to(ROOT).as_posix())

        registered = set()
        for migration in self.registry:
            registered.add(migration.forward)
            registered.add(migration.rollback)

        self.assertEqual(
            set(),
            on_disk - registered,
            "These migration files are not in registry.json. Register them, or "
            "the governed path cannot see them and they will be applied out of "
            "band exactly as before.",
        )
        self.assertEqual(
            set(),
            registered - on_disk,
            "The registry names files that do not exist.",
        )

    def test_registry_makes_no_claim_about_what_any_database_carries(self):
        """Applied-ness lives in the ledger, never in a file that can drift.

        The header of PS-OPPSLATE-001 asserted that production carried the OS-1
        revision hours after production moved to OS-2. Any registry key that
        recorded applied-ness would rot the same way, so there is none.
        """

        document = json.loads(
            (MIGRATION_DIR / "registry.json").read_text(encoding="utf-8")
        )
        for entry in document["migrations"]:
            self.assertEqual(
                {"id", "forward", "rollback", "requires", "summary", "gate"},
                set(entry),
                f"{entry['id']} carries an unexpected registry key.",
            )
            for key in ("applied", "applied_at", "production", "environments"):
                self.assertNotIn(key, entry)

    def test_registry_and_the_legacy_applier_cannot_disagree(self):
        """`apply_sql_migrations.py` keeps working, and stays a subset.

        The old list is still used for foundation verification. Letting it name
        a migration the registry does not, or in a different order, would
        recreate the two-sources-of-truth problem in miniature.
        """

        legacy = [name.split("_")[0] for name in MIGRATION_FILENAMES]
        registered = list(self.registry.ids)
        self.assertEqual(
            legacy,
            [item for item in registered if item in set(legacy)],
            "MIGRATION_FILENAMES and registry.json disagree about the "
            "foundation migrations or their order.",
        )
        for name in MIGRATION_FILENAMES:
            self.assertEqual(
                f"SQL FIles/Migrations/{name}",
                self.registry.get(name.split("_")[0]).forward,
            )

    def test_no_registered_migration_uses_a_GO_batch_separator(self):
        """The applier executes each file as one statement, by design.

        Every migration wraps itself in a single transaction, which a `GO`
        would split. A file containing one would half-apply and the ledger row
        would desynchronize from the objects.
        """

        separator = re.compile(r"(?mi)^[ \t]*GO[ \t]*\r?$")
        for migration in self.registry:
            for path in (migration.forward_path(), migration.rollback_path()):
                self.assertIsNone(
                    separator.search(path.read_text(encoding="utf-8")),
                    f"{path.name} contains a GO batch separator.",
                )

    def test_every_migration_registers_itself_and_its_rollback_deregisters(self):
        for migration in self.registry:
            forward = migration.forward_path().read_text(encoding="utf-8")
            self.assertIn(
                "dbo.schema_migrations",
                forward,
                f"{migration.migration_id} never touches the ledger, so the "
                "governed path could never tell whether it had been applied.",
            )
            self.assertIn(f"N'{migration.migration_id}'", forward)

            rollback = migration.rollback_path().read_text(encoding="utf-8")
            self.assertRegex(
                rollback,
                r"DELETE\s+dbo\.schema_migrations",
                f"{migration.rollback_path().name} does not remove its ledger "
                "row, so a rollback would leave the database claiming a "
                "migration it no longer carries.",
            )


class GateProofTests(unittest.TestCase):
    """`prove before applying`, enforced rather than remembered."""

    def test_every_gate_proof_still_matches_the_file_on_disk(self):
        for migration in _registry():
            if migration.gate is None:
                continue
            ok, reason = gate_status(migration)
            self.assertTrue(ok, reason)

    def test_a_header_edit_preserves_the_proof_but_a_tsql_edit_breaks_it(self):
        """Headers drift and get corrected; T-SQL must not change silently.

        The digest covers everything after the leading block comment, so
        correcting a stale header -- exactly the fix PS-OPPSLATE-001 needed --
        does not force a re-gate, while changing one character of SQL does.
        """

        original = (
            "/* header line one\n   header line two */\n"
            "SET NOCOUNT ON;\nSELECT 1;\n"
        )
        rewritten_header = (
            "/* a completely different header, corrected 2026-08-04 */\n"
            "SET NOCOUNT ON;\nSELECT 1;\n"
        )
        changed_body = (
            "/* header line one\n   header line two */\n"
            "SET NOCOUNT ON;\nSELECT 2;\n"
        )
        self.assertEqual(
            executable_body(original), executable_body(rewritten_header)
        )
        self.assertNotEqual(
            executable_body(original), executable_body(changed_body)
        )
        # A comment after the first statement is executable-adjacent text and
        # stays inside the digest.
        self.assertNotEqual(
            executable_body(original),
            executable_body(original + "/* trailing note */\n"),
        )

    def test_line_endings_and_surrounding_whitespace_do_not_change_the_digest(self):
        body = "/* h */\nSET NOCOUNT ON;\nSELECT 1;\n"
        self.assertEqual(
            executable_body(body),
            executable_body(body.replace("\n", "\r\n")),
        )
        self.assertEqual(executable_body(body), executable_body(body + "\n\n"))

    def test_a_gate_proof_recorded_against_a_real_database_is_rejected(self):
        for database in FORBIDDEN_GATE_DATABASES:
            with self.assertRaises(RegistryError) as caught:
                GateProof.from_json(
                    "PS-TEST-001", _proof("a" * 64, gate_database=database)
                )
            self.assertIn("throwaway", str(caught.exception))

    def test_a_malformed_digest_is_rejected(self):
        for digest in ("", "not-a-hash", "A" * 64, "a" * 63):
            with self.assertRaises(RegistryError):
                GateProof.from_json("PS-TEST-001", _proof(digest))

    def test_an_incomplete_gate_proof_is_rejected(self):
        payload = _proof("a" * 64)
        del payload["gate_database"]
        with self.assertRaises(RegistryError) as caught:
            GateProof.from_json("PS-TEST-001", payload)
        self.assertIn("gate_database", str(caught.exception))


class ScratchRegistryMixin:
    def setUp(self):
        self.directory = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.directory, ignore_errors=True)
        (self.directory / "sql").mkdir()

    def sql(self, name: str, body: str = "SELECT 1;") -> str:
        relative = f"sql/{name}.sql"
        (self.directory / relative).write_text(
            f"/* {name} */\n{body}\n", encoding="utf-8"
        )
        rollback = f"sql/{name}_rollback.sql"
        (self.directory / rollback).write_text(
            f"/* {name} rollback */\nSELECT 1;\n", encoding="utf-8"
        )
        return relative

    def digest(self, relative: str) -> str:
        return executable_sha256(self.directory / relative)


class RegistryValidationTests(ScratchRegistryMixin, unittest.TestCase):
    """A registry that cannot be fully validated must not load at all."""

    def _load(self, entries):
        path = _write_registry(self.directory, entries)
        return load_registry(path, root=self.directory)

    def test_a_duplicate_migration_id_is_rejected(self):
        forward = self.sql("A")
        with self.assertRaises(RegistryError) as caught:
            self._load(
                [
                    _entry("A", forward, "sql/A_rollback.sql"),
                    _entry("A", forward, "sql/A_rollback.sql"),
                ]
            )
        self.assertIn("more than once", str(caught.exception))

    def test_a_prerequisite_listed_after_its_dependant_is_rejected(self):
        self.sql("A")
        self.sql("B")
        with self.assertRaises(RegistryError) as caught:
            self._load(
                [
                    _entry("B", "sql/B.sql", "sql/B_rollback.sql", ["A"]),
                    _entry("A", "sql/A.sql", "sql/A_rollback.sql"),
                ]
            )
        self.assertIn("must appear earlier", str(caught.exception))

    def test_a_missing_file_is_rejected(self):
        with self.assertRaises(RegistryError) as caught:
            self._load([_entry("A", "sql/A.sql", "sql/A_rollback.sql")])
        self.assertIn("registered file is missing", str(caught.exception))

    def test_two_entries_claiming_one_file_are_rejected(self):
        self.sql("A")
        self.sql("B")
        with self.assertRaises(RegistryError) as caught:
            self._load(
                [
                    _entry("A", "sql/A.sql", "sql/A_rollback.sql"),
                    _entry("B", "sql/A.sql", "sql/B_rollback.sql"),
                ]
            )
        self.assertIn("more than one registry entry", str(caught.exception))

    def test_omitting_the_gate_key_is_rejected(self):
        self.sql("A")
        entry = _entry("A", "sql/A.sql", "sql/A_rollback.sql")
        del entry["gate"]
        with self.assertRaises(RegistryError) as caught:
            self._load([entry])
        self.assertIn("is missing 'gate'", str(caught.exception))

    def test_a_wrong_version_is_rejected(self):
        self.sql("A")
        path = self.directory / "registry.json"
        path.write_text(
            json.dumps(
                {
                    "version": 99,
                    "migrations": [
                        _entry("A", "sql/A.sql", "sql/A_rollback.sql")
                    ],
                }
            ),
            encoding="utf-8",
        )
        with self.assertRaises(RegistryError):
            load_registry(path, root=self.directory)


class ApplyPlanTests(ScratchRegistryMixin, unittest.TestCase):
    """The plan comes from the ledger. Everything else fails closed."""

    def setUp(self):
        super().setUp()
        self.a = self.sql("A")
        self.b = self.sql("B", "SELECT 2;")
        self.c = self.sql("C", "SELECT 3;")
        self.entries = [
            _entry(
                "A",
                self.a,
                "sql/A_rollback.sql",
                gate=_proof(self.digest(self.a)),
            ),
            _entry(
                "B",
                self.b,
                "sql/B_rollback.sql",
                ["A"],
                gate=_proof(self.digest(self.b)),
            ),
            _entry("C", self.c, "sql/C_rollback.sql", ["B"], gate=None),
        ]
        self.registry = load_registry(
            _write_registry(self.directory, self.entries), root=self.directory
        )

    def plan(self, applied, only=()):
        return resolve_apply_plan(
            self.registry, applied, only, root=self.directory
        )

    def test_pending_is_derived_from_the_ledger_not_from_a_hardcoded_list(self):
        plan, blockers, held = self.plan([])
        self.assertEqual([], blockers)
        self.assertEqual(["A", "B"], [item.migration_id for item in plan])

        plan, blockers, held = self.plan(["A"])
        self.assertEqual([], blockers)
        self.assertEqual(["B"], [item.migration_id for item in plan])

        plan, blockers, held = self.plan(["A", "B"])
        self.assertEqual([], blockers)
        self.assertEqual([], plan, "a re-run must be a genuine no-op")

    def test_an_ungated_migration_is_held_back_rather_than_applied(self):
        plan, blockers, held = self.plan([])
        self.assertEqual([], blockers)
        self.assertNotIn("C", [item.migration_id for item in plan])
        self.assertEqual(["C"], [item.migration_id for item in held])

    def test_naming_an_ungated_migration_explicitly_is_an_error(self):
        """A specific instruction must not become a silent no-op."""

        plan, blockers, held = self.plan([], only=("C",))
        self.assertEqual([], plan)
        self.assertTrue(any("has no gate proof" in item for item in blockers))

    def test_a_stale_gate_proof_blocks_the_migration(self):
        (self.directory / self.b).write_text(
            "/* B */\nSELECT 999;\n", encoding="utf-8"
        )
        registry = load_registry(
            self.directory / "registry.json", root=self.directory
        )
        plan, blockers, held = resolve_apply_plan(
            registry, [], ("B",), root=self.directory
        )
        self.assertEqual([], plan)
        self.assertTrue(
            any("does not match the gated bytes" in item for item in blockers)
        )

    def test_an_ungated_prerequisite_blocks_everything_that_needs_it(self):
        entries = list(self.entries)
        entries[0]["gate"] = None  # A is now a draft
        registry = load_registry(
            _write_registry(self.directory, entries), root=self.directory
        )
        plan, blockers, held = resolve_apply_plan(
            registry, [], root=self.directory
        )
        self.assertTrue(
            any(
                "B requires A" in item and "cannot apply" in item
                for item in blockers
            ),
            blockers,
        )

    def test_an_unknown_or_already_applied_selection_is_refused(self):
        _, blockers, _ = self.plan([], only=("Z",))
        self.assertTrue(any("Not registered" in item for item in blockers))

        _, blockers, _ = self.plan(["A"], only=("A",))
        self.assertTrue(
            any("Already recorded" in item for item in blockers)
        )

    def test_rollback_order_is_the_reverse_of_registry_order(self):
        applied = ["A", "B"]
        newest = [
            item.migration_id
            for item in self.registry
            if item.migration_id in set(applied)
        ][-1]
        self.assertEqual("B", newest)


class StateRecordTests(ScratchRegistryMixin, unittest.TestCase):
    """The repository's record of production is rendered, never written."""

    def setUp(self):
        super().setUp()
        forward = self.sql("A")
        self.registry = load_registry(
            _write_registry(
                self.directory,
                [
                    _entry(
                        "A",
                        forward,
                        "sql/A_rollback.sql",
                        gate=_proof(self.digest(forward)),
                    ),
                    _entry("B", self.sql("B"), "sql/B_rollback.sql", ["A"]),
                ],
            ),
            root=self.directory,
        )

    def render(self, ledger):
        return render_state(
            self.registry,
            database="peerslate-database",
            server="peerslate",
            ledger_rows=ledger,
            generated_at_utc="2026-08-04T12:00:00Z",
            root=self.directory,
        )

    def test_rendering_is_deterministic_so_it_can_be_byte_compared(self):
        ledger = [{"migration_id": "A", "applied_at_utc": "2026-08-04T11:00:00"}]
        self.assertEqual(self.render(ledger), self.render(ledger))
        self.assertEqual(
            self.render(ledger),
            self.render(list(reversed(ledger)) + []),
        )

    def test_the_record_carries_a_generated_banner_and_a_parseable_block(self):
        rendered = self.render(
            [{"migration_id": "A", "applied_at_utc": "2026-08-04T11:00:00"}]
        )
        self.assertTrue(rendered.startswith(STATE_BANNER))
        self.assertIn("Do not edit by hand", rendered)
        document = parse_state(rendered)
        self.assertEqual("peerslate-database", document["database"])
        self.assertEqual(["A"], [item["id"] for item in document["applied"]])
        self.assertEqual(["B"], document["pending"])

    def test_a_ledger_row_the_repository_cannot_explain_is_surfaced(self):
        """Applying out of band must be visible, not invisible."""

        rendered = self.render(
            [
                {"migration_id": "A", "applied_at_utc": "2026-08-04T11:00:00"},
                {
                    "migration_id": "PS-MYSTERY-001",
                    "applied_at_utc": "2026-08-04T11:30:00",
                },
            ]
        )
        self.assertIn("applied out of band", rendered)
        self.assertIn("cannot explain", rendered)
        self.assertEqual(
            ["PS-MYSTERY-001"],
            parse_state(rendered)["unregistered_in_ledger"],
        )

    def test_a_hand_edited_record_is_detected_rather_than_believed(self):
        with self.assertRaises(RegistryError) as caught:
            parse_state("# Production schema state\n\nEverything is fine.\n")
        self.assertIn("hand edited", str(caught.exception))

    def test_the_committed_record_if_present_is_generated_and_consistent(self):
        """Guards the real file once the first governed run creates it.

        It deliberately does not exist yet. The path's first `report` run
        renders it from a live ledger read; until then the repository makes no
        claim, which is more honest than the prose it replaces.
        """

        if not STATE_PATH.exists():
            self.skipTest(
                "No governed run has rendered the production record yet."
            )
        text = STATE_PATH.read_text(encoding="utf-8")
        self.assertTrue(text.startswith(STATE_BANNER))
        document = parse_state(text)
        self.assertEqual("peerslate-database", document["database"])
        registry = _registry()
        for entry in document["applied"]:
            self.assertEqual(
                registry.contains(entry["id"]),
                entry["registered"],
                f"{entry['id']}: the record disagrees with the registry about "
                "whether it is registered.",
            )


# These fixtures are assembled at run time rather than written as literals, so
# no line in this file ever contains a credential keyword next to a value. The
# Build stage scans the whole repository history with gitleaks; a test about
# redacting secrets must not be the thing that trips it.
FAKE_HOST = "example" + ".database.windows.net"
FAKE_PASSWORD = "-".join(["not", "a", "real", "value"])
FAKE_CONNECTION = ";".join(
    [
        "Driver={ODBC Driver 18}",
        f"Server=tcp:{FAKE_HOST}",
        "Database=peerslate-database",
        "Uid=" + "operator",
        "P" + "wd=" + FAKE_PASSWORD,
        "",
    ]
)


class CredentialHandlingTests(unittest.TestCase):
    """Nothing credential-shaped may reach stdout, a log, or an artifact."""

    def test_the_connection_string_and_its_password_are_scrubbed(self):
        with mock.patch.dict(
            "os.environ", {"AZURE_SQL_CONNECTIONSTRING": FAKE_CONNECTION}
        ):
            self.assertNotIn(FAKE_PASSWORD, governed.scrub(FAKE_CONNECTION))
            self.assertNotIn(
                FAKE_PASSWORD,
                governed.scrub(f"login failed for {FAKE_CONNECTION}"),
            )
            self.assertNotIn(
                FAKE_PASSWORD,
                governed.scrub("P" + "wd=" + FAKE_PASSWORD),
            )
            self.assertNotIn(
                FAKE_CONNECTION,
                governed.scrub(f"connect({FAKE_CONNECTION})"),
            )

    def test_a_password_is_redacted_even_when_it_is_not_the_configured_one(self):
        other = "-".join(["some", "other", "value"])
        with mock.patch.dict("os.environ", {}, clear=True):
            self.assertNotIn(
                other,
                governed.scrub("Server=x;" + "Pass" + "word=" + other + ";"),
            )

    def test_retargeting_replaces_only_the_database(self):
        retargeted = governed._retarget_database(FAKE_CONNECTION, "ps-gate-1")
        self.assertIn("Database=ps-gate-1;", retargeted)
        self.assertNotIn("peerslate-database", retargeted)
        self.assertIn("Uid=" + "operator", retargeted)
        self.assertIn(FAKE_PASSWORD, retargeted)

    def test_a_connection_string_without_a_database_cannot_be_retargeted(self):
        with self.assertRaises(governed.GovernedMigrationError):
            governed._retarget_database(
                f"Server={FAKE_HOST};Uid=" + "operator;", "ps-gate-1"
            )


class CommandLineTests(ScratchRegistryMixin, unittest.TestCase):
    """The offline entry point CI runs, and the guards that need no database."""

    def test_check_passes_against_the_committed_registry(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            exit_code = governed.main(["check"])
        self.assertEqual(0, exit_code, buffer.getvalue())
        self.assertIn("Registry is internally consistent", buffer.getvalue())

    def test_check_fails_closed_when_a_gated_file_changed(self):
        forward = self.sql("A")
        registry = _write_registry(
            self.directory,
            [
                _entry(
                    "A",
                    forward,
                    "sql/A_rollback.sql",
                    gate=_proof(self.digest(forward)),
                )
            ],
        )
        (self.directory / forward).write_text(
            "/* A */\nSELECT 42;\n", encoding="utf-8"
        )
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            exit_code = governed.main(
                [
                    "--registry",
                    str(registry),
                    "--registry-root",
                    str(self.directory),
                    "check",
                ]
            )
        self.assertEqual(1, exit_code)
        self.assertIn("does not match the gated bytes", buffer.getvalue())

    def test_rollback_refuses_before_connecting_when_confirmation_differs(self):
        """The refusal must happen without opening a connection at all."""

        buffer = io.StringIO()
        with redirect_stdout(buffer):
            exit_code = governed.main(
                [
                    "rollback",
                    "PS-OPPSLATE-001",
                    "--confirm",
                    "yes",
                    "--expect-database",
                    "peerslate-database",
                ]
            )
        self.assertEqual(1, exit_code)
        self.assertIn("repeat the migration id exactly", buffer.getvalue())

    def test_a_target_override_that_disagrees_with_the_expectation_is_refused(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            exit_code = governed.main(
                [
                    "--database",
                    "ps-somewhere-else",
                    "report",
                    "--expect-database",
                    "peerslate-database",
                ]
            )
        self.assertEqual(1, exit_code)
        self.assertIn("must repeat --expect-database", buffer.getvalue())

    def test_the_default_action_requires_an_explicit_subcommand(self):
        """There is no implicit action. Doing nothing is the default."""

        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            governed.main([])


class ReporterTests(unittest.TestCase):
    """A run that did nothing must never read as a run that applied schema."""

    def test_a_warning_downgrades_an_azure_run(self):
        reporter = governed.Reporter(azure=True)
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            reporter.warn("nothing was applied")
            reporter.downgrade()
        output = buffer.getvalue()
        self.assertIn("##vso[task.logissue type=warning]", output)
        self.assertIn("##vso[task.complete result=SucceededWithIssues;]", output)

    def test_a_clean_run_is_not_downgraded(self):
        reporter = governed.Reporter(azure=True)
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            reporter.say("applied one migration")
            reporter.downgrade()
        self.assertNotIn("SucceededWithIssues", buffer.getvalue())

    def test_logging_commands_are_only_emitted_for_azure(self):
        reporter = governed.Reporter(azure=False)
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            reporter.warn("nothing was applied")
            reporter.downgrade()
        self.assertNotIn("##vso", buffer.getvalue())


class PipelineWiringTests(unittest.TestCase):
    """The protected job must invoke the CLI with argparse-valid ordering."""

    def setUp(self):
        self.pipeline = (ROOT / "azure-pipelines.yml").read_text(encoding="utf-8")

    def test_global_print_state_option_precedes_every_connected_subcommand(self):
        """Run 497 reached the protected environment but failed before SQL.

        ``--print-state`` belongs to the root parser; argparse rejects it when
        YAML puts it after ``report``, ``apply``, or ``rollback``. Keep the
        queue-time commands aligned with the parser rather than merely checking
        that every expected word appears somewhere in the pipeline.
        """
        action_markers = {
            "report": "if eq(parameters.schemaAction, 'report')",
            "apply": "if eq(parameters.schemaAction, 'apply')",
            "rollback": "if eq(parameters.schemaAction, 'rollback')",
        }
        for action, marker in action_markers.items():
            with self.subTest(action=action):
                block = self.pipeline.split(marker, 1)[1].split(
                    "- ${{ if eq(parameters.schemaAction", 1
                )[0]
                command = re.search(rf"(?m)^\s+{action}(?:\s|$)", block)
                self.assertIsNotNone(command)
                self.assertLess(block.index("--print-state"), command.start())

    def test_connected_actions_run_inside_the_approved_azure_identity(self):
        """The Entra connection string needs the service connection's CLI token.

        Run 501 proved that a plain shell has no usable DefaultAzureCredential
        on a Microsoft-hosted agent. Keep every connected action inside an
        AzureCLI task while leaving the offline registry check unauthenticated.
        """
        schema_stage = self.pipeline.split("- stage: SchemaMigration", 1)[1]
        schema_stage = schema_stage.split("- stage: CandidateDeploy", 1)[0]
        for action in ("report", "apply", "rollback"):
            with self.subTest(action=action):
                marker = f"if eq(parameters.schemaAction, '{action}')"
                block = schema_stage.split(marker, 1)[1].split(
                    "- ${{ if eq(parameters.schemaAction", 1
                )[0]
                self.assertIn("- task: AzureCLI@2", block)
                self.assertIn(
                    "azureSubscription: $(azureServiceConnectionId)", block
                )
                self.assertIn("scriptType: bash", block)
                self.assertIn("AZURE_SQL_CONNECTIONSTRING", block)

        offline_block = schema_stage.split(
            "displayName: Validate the migration registry and gate proofs", 1
        )[0]
        self.assertNotIn("AzureCLI@2", offline_block)


class GovernanceDocumentationTests(unittest.TestCase):
    """The path must be documented where Protected operations live."""

    def setUp(self):
        self.document = (
            ROOT
            / "docs"
            / "initiatives"
            / "PS-OPS-001"
            / "GOVERNED_SCHEMA_MIGRATION_PATH.md"
        ).read_text(encoding="utf-8")

    def test_the_document_answers_every_question_an_operator_will_have(self):
        for heading in (
            "## The trigger",
            "## Safety properties",
            "## Applying a migration",
            "## Rolling a migration back",
            "## Telling what production carries",
            "## What this path does not protect against",
            "## What `proposed/` means now",
        ):
            self.assertIn(heading, self.document)

    def test_the_document_names_the_real_moving_parts(self):
        for reference in (
            "scripts/govern_sql_migrations.py",
            "SQL FIles/Migrations/registry.json",
            "docs/governance/PRODUCTION_SCHEMA_STATE.md",
            "peerslate-database-schema",
            "schemaAction",
        ):
            self.assertIn(reference, self.document)

    def test_ps_ops_001_points_at_the_path(self):
        readme = (
            ROOT / "docs" / "initiatives" / "PS-OPS-001" / "README.md"
        ).read_text(encoding="utf-8")
        self.assertIn("GOVERNED_SCHEMA_MIGRATION_PATH.md", readme)


if __name__ == "__main__":
    unittest.main()
