"""The two leg documents and the preview harness must not drift from the code.

A runbook that quotes a stale digest, or a spec that names a rate limit the
blueprint no longer declares, is worse than no document: it is read at the one
moment nobody has time to check it. These tests are cheap and they fail loudly
the moment the code moves underneath the prose.

Nothing here imports ``app`` or boots the harness - that is
``run_direct_preview.py --check``'s job, and it is not something to run inside
the suite.
"""

from __future__ import annotations

import ast
import re
import sys
import unittest
from pathlib import Path

from ask_pete_direct_routes import (
    DIRECT_QUESTION_PATH,
    OWNER_INBOX_PATH,
    PLANNED_RATE_LIMITS,
)

from tests.ask_pete_direct.support import REPOSITORY_ROOT


PACKAGE_DOCS = REPOSITORY_ROOT / "docs" / "initiatives" / "PS-ASK-PETE-DIRECT-001"
SPEC = PACKAGE_DOCS / "REGISTRATION_LEG_SPEC.md"
RUNBOOK = PACKAGE_DOCS / "SCHEMA_GATE_RUNBOOK.md"
README = PACKAGE_DOCS / "README.md"
HARNESS = REPOSITORY_ROOT / "tests" / "ask_pete_direct" / "run_direct_preview.py"
FORWARD = (
    REPOSITORY_ROOT
    / "SQL FIles"
    / "Migrations"
    / "proposed"
    / "PS-ASK-PETE-DIRECT-001_recruiter_questions.sql"
)

ALLOWLISTED_PROCEDURES = frozenset(
    {
        "usp_SubmitRecruiterQuestion",
        "usp_ListRecruiterQuestionsForOwner",
        "usp_SetRecruiterQuestionStatusForOwner",
    }
)


def _registry_helpers():
    scripts = str(REPOSITORY_ROOT / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    from migration_registry import ROOT, executable_sha256, load_registry

    return load_registry, executable_sha256, ROOT


class RunbookAccuracyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runbook = RUNBOOK.read_text(encoding="utf-8")

    def test_the_quoted_digest_is_the_files_current_digest(self):
        """If the T-SQL changes, this fails - and it must, because the gate
        proof binds a rehearsal to exact bytes."""
        _, executable_sha256, _ = _registry_helpers()
        actual = executable_sha256(FORWARD)
        self.assertIn(
            actual,
            self.runbook,
            "SCHEMA_GATE_RUNBOOK.md quotes a stale executable_sha256; the "
            "migration changed after the runbook was written.",
        )

    def test_the_quoted_prerequisite_chain_is_the_computed_one(self):
        load_registry, _, _ = _registry_helpers()
        import govern_sql_migrations as governed

        registry = load_registry()
        migration = registry.get("PS-ASK-PETE-DIRECT-001")
        chain = [
            item.migration_id
            for item in governed._prerequisite_chain(registry, migration)
        ]
        self.assertTrue(chain)
        for migration_id in chain:
            with self.subTest(migration_id=migration_id):
                self.assertIn(migration_id, self.runbook)

    def test_the_runbook_marks_which_steps_need_owner_credentials(self):
        self.assertIn("OWNER CREDENTIALS", self.runbook)
        for part in (
            "Part 2 — gate against a throwaway database — **OWNER CREDENTIALS**",
            "Part 4 — governed production apply — **OWNER CREDENTIALS + APPROVER**",
        ):
            with self.subTest(part=part):
                self.assertIn(part, self.runbook)

    def test_the_runbook_uses_the_real_command_surface(self):
        for token in (
            "govern_sql_migrations.py check",
            "gate PS-ASK-PETE-DIRECT-001",
            "--expect-database",
            "--operator",
            "preflight apply",
            "schemaAction",
            "schemaMigrationId",
            "peerslate-database-schema",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.runbook)

    def test_the_runbook_never_suggests_skipping_the_rollback_rehearsal(self):
        self.assertIn("do **not** pass `--no-rehearse-rollback`", self.runbook)

    def test_the_runbook_names_a_throwaway_database_the_tool_would_accept(self):
        from migration_registry import FORBIDDEN_GATE_DATABASES

        for forbidden in FORBIDDEN_GATE_DATABASES:
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(
                    f"--database {forbidden}",
                    self.runbook,
                    "the runbook must never name a protected database as a gate target",
                )

    def test_the_post_apply_checks_prove_archive_only_survived_the_apply(self):
        self.assertIn("Expect **zero rows**", self.runbook)
        self.assertIn("verified = 1", self.runbook)


class RegistrationSpecAccuracyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = SPEC.read_text(encoding="utf-8")

    def test_the_spec_states_the_exact_registration_line(self):
        self.assertIn("app.register_blueprint(ask_pete_direct)", self.spec)
        self.assertIn("from ask_pete_direct_routes import ask_pete_direct", self.spec)

    def test_the_spec_names_the_real_config_key(self):
        self.assertIn("PEERSLATE_ASK_PETE_DIRECT_ENABLED", self.spec)
        self.assertIn(
            "os.environ.get('PEERSLATE_ASK_PETE_DIRECT_ENABLED', 'false').lower() == 'true'",
            self.spec,
        )

    def test_every_planned_rate_limit_appears_in_the_spec_table(self):
        for endpoint, budget in PLANNED_RATE_LIMITS.items():
            with self.subTest(endpoint=endpoint):
                self.assertIn(endpoint, self.spec)
                self.assertIn(budget, self.spec)

    def test_the_spec_warns_that_the_darkness_tests_are_meant_to_fail(self):
        """They are the tripwire. A spec that let someone delete them quietly
        would have removed the only thing forcing registration to be
        deliberate."""
        self.assertIn("test_the_blueprint_is_not_registered_by_any_production_module", self.spec)
        self.assertIn("do not delete them", self.spec)

    def test_the_spec_carries_the_flag_off_and_404_checklist(self):
        for token in (
            "byte-identical",
            "404-neutral" if "404-neutral" in self.spec else "404",
            DIRECT_QUESTION_PATH,
            OWNER_INBOX_PATH,
            "rate_limited",
            "429",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.spec)

    def test_the_spec_separates_registration_from_enablement(self):
        self.assertIn("It does not turn the flag on", self.spec)


class PreviewHarnessTests(unittest.TestCase):
    """Source-level only. Booting it is ``--check``'s job, not the suite's."""

    @classmethod
    def setUpClass(cls):
        cls.source = HARNESS.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)

    def test_the_harness_registers_the_blueprint_the_way_app_py_does(self):
        """It rehearsed the registration before the leg ran, and now finds it
        already done. The guard is what lets it work either way rather than
        raising on a second registration of the same blueprint name."""
        self.assertIn(
            "app.register_blueprint(ask_pete_direct_routes.ask_pete_direct)",
            self.source,
        )
        self.assertIn('if "ask_pete_direct" not in app.blueprints:', self.source)
        self.assertIn("THE REGISTRATION, AND THE FLAG", self.source)

    def test_the_harness_documents_its_usage_and_its_fixture_nature(self):
        docstring = ast.get_docstring(self.tree) or ""
        for token in (
            "USAGE",
            "run_direct_preview.py",
            "--check",
            "127.0.0.1",
            "REGISTRATION LEG'S REHEARSAL",
            "WHAT IS FIXTURE",
        ):
            with self.subTest(token=token):
                self.assertIn(token, docstring)

    def test_the_harness_never_binds_the_airplay_port_or_localhost(self):
        """macOS AirPlay Receiver squats 5000, and "localhost" resolves to it.

        Checked on the CODE, not the docstring - the docstring says both words
        precisely because it explains why neither is used.
        """
        # ast.get_docstring returns the CLEANED text, which is not a substring
        # of the raw source, so slice by the node's line span instead.
        docstring_node = self.tree.body[0]
        code = "\n".join(self.source.splitlines()[docstring_node.end_lineno :])
        for forbidden in ("5000", "localhost"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, code)
        self.assertIn('probe.bind(("127.0.0.1", 0))', self.source)
        self.assertIn('make_server("127.0.0.1", port, app', self.source)

    def test_the_harness_calls_no_provider(self):
        for forbidden in ("anthropic.Anthropic(", "client.messages", "api.anthropic.com"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, self.source)
        self.assertIn("app_module.answer_public_question = _preview_answer", self.source)
        self.assertIn("ask-pete-direct-preview-placeholder", self.source)

    def test_the_fixture_store_stubs_exactly_the_allowlisted_procedures(self):
        named = set(re.findall(r'procedure_name == "(usp_\w+)"', self.source))
        self.assertEqual(named, set(ALLOWLISTED_PROCEDURES))

    def test_the_fixture_store_refuses_a_consentless_write_like_the_procedure(self):
        self.assertIn('if bound.get("@ConsentGiven") != 1:', self.source)

    def test_every_preview_response_is_marked_as_fixture(self):
        self.assertIn('PREVIEW_HEADER = "X-PeerSlate-Preview"', self.source)
        self.assertIn('PREVIEW_HEADER_VALUE = "fixture-in-memory"', self.source)
        self.assertIn("response.headers[PREVIEW_HEADER] = PREVIEW_HEADER_VALUE", self.source)

    def test_the_harness_is_not_production_code(self):
        """It lives under tests/, so the darkness scan of root and services/
        never sees it - which is what keeps the feature dark despite this file
        existing."""
        self.assertTrue(HARNESS.is_relative_to(REPOSITORY_ROOT / "tests"))


class PackageIndexTests(unittest.TestCase):
    def test_the_readme_links_both_leg_documents_and_the_harness(self):
        readme = README.read_text(encoding="utf-8")
        for reference in (
            "REGISTRATION_LEG_SPEC.md",
            "SCHEMA_GATE_RUNBOOK.md",
            "run_direct_preview.py",
        ):
            with self.subTest(reference=reference):
                self.assertIn(reference, readme)


if __name__ == "__main__":
    unittest.main()
