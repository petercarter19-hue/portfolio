import copy
import contextlib
import os
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch

from scripts import worktree_lifecycle as lifecycle
from scripts import delivery_preflight as preflight


THREAD_ID = "01a097f4-9de5-7723-9b13-65124d7ad4eb"
NATIVE_REF = f"session:{THREAD_ID}"
EXTERNAL_REF = "agent:cursor/receiver-001"
PACKAGE = "PS-CALLER-COMPATIBILITY-001"
CONTEXT_ID = "a" * 32
ROOT = Path(__file__).resolve().parents[1]


class CallerResolverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="caller-context-")
        self.addCleanup(self.temporary.cleanup)
        self.common_dir = Path(self.temporary.name).resolve()
        self.context = {
            "id": CONTEXT_ID,
            "state": "active",
            "repository_common_dir": str(self.common_dir),
            "receiver_ref": EXTERNAL_REF,
            "package": PACKAGE,
            "registered_by": NATIVE_REF,
            "owner_authorization_ref": "session:owner/caller-context-001",
            "registered_at": "2026-09-12T00:00:00Z",
            "revoked_at": None,
            "revoked_by": None,
            "revocation_authorization_ref": None,
        }
        self.registry = {"caller_contexts": [self.context]}

    def resolve(self, **overrides):
        values = {
            "registry": self.registry,
            "repository_common_dir": self.common_dir,
            "caller_context": "",
            "task_ref": None,
            "package": PACKAGE,
        }
        values.update(overrides)
        return lifecycle.resolve_caller_ref(**values)

    def test_native_codex_thread_is_normalized_without_manual_environment(self):
        with patch.dict(os.environ, {"CODEX_THREAD_ID": THREAD_ID}, clear=True):
            self.assertEqual(self.resolve(), NATIVE_REF)

    def test_native_identity_works_in_clean_synthetic_subprocess(self):
        environment = os.environ.copy()
        for name in (
            "PEERSLATE_CALLER_REF",
            lifecycle.CALLER_CONTEXT_ENV,
            "CODEX_SESSION_ID",
        ):
            environment.pop(name, None)
        environment["CODEX_THREAD_ID"] = THREAD_ID
        result = subprocess.run(
            [
                sys.executable,
                "-B",
                "-c",
                "from scripts.worktree_lifecycle import resolve_caller_ref; "
                "print(resolve_caller_ref())",
            ],
            cwd=ROOT,
            env=environment,
            text=True,
            encoding="utf-8",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), NATIVE_REF)

    def test_inherited_parent_session_is_never_an_identity_source(self):
        with patch.dict(os.environ, {"CODEX_SESSION_ID": THREAD_ID}, clear=True):
            with self.assertRaisesRegex(lifecycle.Refusal, "identity unavailable"):
                self.resolve()

    def test_no_identity_and_malformed_native_identity_refuse(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(lifecycle.Refusal, "identity unavailable"):
                self.resolve()
        with patch.dict(os.environ, {"CODEX_THREAD_ID": "not-a-uuid"}, clear=True):
            with self.assertRaisesRegex(lifecycle.Refusal, "exact UUID"):
                self.resolve()

    def test_explicit_native_and_context_sources_must_all_agree(self):
        agreeing = copy.deepcopy(self.registry)
        agreeing["caller_contexts"][0]["receiver_ref"] = NATIVE_REF
        agreeing["caller_contexts"][0]["registered_by"] = "session:other/registrar"
        environment = {
            "CODEX_THREAD_ID": THREAD_ID,
            "PEERSLATE_CALLER_REF": NATIVE_REF,
        }
        with patch.dict(os.environ, environment, clear=True):
            self.assertEqual(
                self.resolve(registry=agreeing, caller_context=CONTEXT_ID),
                NATIVE_REF,
            )
        disagreements = [
            ({"CODEX_THREAD_ID": THREAD_ID, "PEERSLATE_CALLER_REF": "agent:other/caller"}, ""),
            ({"CODEX_THREAD_ID": THREAD_ID}, CONTEXT_ID),
            ({"PEERSLATE_CALLER_REF": NATIVE_REF}, CONTEXT_ID),
        ]
        for environment, context_id in disagreements:
            with self.subTest(environment=environment, context=context_id), patch.dict(
                os.environ, environment, clear=True
            ):
                with self.assertRaisesRegex(lifecycle.Refusal, "identities disagree"):
                    self.resolve(caller_context=context_id)

    def test_argument_and_guarded_child_context_mismatch_refuses(self):
        with patch.dict(
            os.environ,
            {lifecycle.CALLER_CONTEXT_ENV: "b" * 32},
            clear=True,
        ):
            with self.assertRaisesRegex(lifecycle.Refusal, "argument differs"):
                self.resolve(caller_context=CONTEXT_ID)

    def test_falsey_non_text_context_refuses(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(
                lifecycle.Refusal, "caller context identifier is invalid"
            ):
                self.resolve(caller_context=[])

    def test_registered_context_is_live_repository_task_and_package_scoped(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(
                self.resolve(caller_context=CONTEXT_ID, task_ref=EXTERNAL_REF),
                EXTERNAL_REF,
            )
            cases = [
                ({"caller_context": "b" * 32}, "unknown"),
                ({"repository_common_dir": self.common_dir / "other"}, "different Git"),
                ({"task_ref": "agent:other/receiver"}, "claimed task"),
                ({"package": "PS-OTHER-001"}, "package differs"),
            ]
            for changes, message in cases:
                with self.subTest(changes=changes):
                    with self.assertRaisesRegex(lifecycle.Refusal, message):
                        values = {"caller_context": CONTEXT_ID, **changes}
                        self.resolve(**values)

    def test_registered_context_requires_an_exact_operation_package(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(
                lifecycle.Refusal, "requires an exact operation package"
            ):
                self.resolve(caller_context=CONTEXT_ID, package=None)

    def test_no_history_helper_still_reconciles_supplied_identities(self):
        repository_context = SimpleNamespace(common_dir=self.common_dir)
        request = SimpleNamespace(caller_context="")
        registry = {"control_custody_transitions": []}
        environment = {
            "CODEX_THREAD_ID": THREAD_ID,
            "PEERSLATE_CALLER_REF": EXTERNAL_REF,
        }
        with patch.dict(os.environ, environment, clear=True):
            with self.assertRaisesRegex(lifecycle.Refusal, "identities disagree"):
                lifecycle._require_resolved_caller_for_registry(
                    repository_context,
                    registry,
                    request,
                    task_ref=EXTERNAL_REF,
                    package=PACKAGE,
                )

    def test_revoked_and_malformed_contexts_fail_closed(self):
        revoked = copy.deepcopy(self.registry)
        revoked["caller_contexts"][0].update(
            state="revoked",
            revoked_at="2026-09-12T01:00:00Z",
            revoked_by=NATIVE_REF,
            revocation_authorization_ref="session:owner/revoke-context-001",
        )
        malformed = copy.deepcopy(self.registry)
        malformed["caller_contexts"][0]["unexpected"] = True
        malformed_state = copy.deepcopy(self.registry)
        malformed_state["caller_contexts"][0]["state"] = []
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(lifecycle.Refusal, "revoked"):
                self.resolve(registry=revoked, caller_context=CONTEXT_ID)
            with self.assertRaisesRegex(lifecycle.Refusal, "fields are malformed"):
                self.resolve(registry=malformed, caller_context=CONTEXT_ID)
            with self.assertRaisesRegex(lifecycle.Refusal, "state is invalid"):
                self.resolve(registry=malformed_state, caller_context=CONTEXT_ID)

    def test_delivery_preflight_uses_the_same_scoped_context_resolver(self):
        repository = self.common_dir / "worktree"
        repository.mkdir()
        registry = {
            "schema_version": 1,
            "initialized_at": "2026-09-12T00:00:00Z",
            "repository_common_dir": str(self.common_dir),
            "worktrees": [
                {
                    "path": str(repository),
                    "kind": "durable",
                    "state": "active",
                    "package": PACKAGE,
                    "task_ref": EXTERNAL_REF,
                    "branch": "work/2026-09-12-caller-compatibility-001",
                    "lease": None,
                }
            ],
            "caller_contexts": [copy.deepcopy(self.context)],
            "control_custody_transitions": [],
        }
        request = SimpleNamespace(
            intent="write",
            task_ref=EXTERNAL_REF,
            caller_context=CONTEXT_ID,
            lease_token="",
        )
        claim = {
            "package": PACKAGE,
            "writer_ref": EXTERNAL_REF,
            "branch": "work/2026-09-12-caller-compatibility-001",
        }
        facts = SimpleNamespace(
            repository=str(repository),
            branch=claim["branch"],
        )
        registry_path = self.common_dir / preflight.WORKTREE_REGISTRY_REL
        registry_path.parent.mkdir(parents=True)
        registry_path.write_text("{}", encoding="utf-8")
        with patch.dict(os.environ, {}, clear=True), patch.object(
            preflight, "_git_common_dir", return_value=self.common_dir
        ), patch.object(preflight, "_read_json", return_value=registry), patch.object(
            preflight.os.path, "lexists", return_value=False
        ):
            context, errors, _ = preflight.evaluate_local_worktree_context(
                root=repository,
                args=request,
                claim=claim,
                facts=facts,
            )
        self.assertEqual(context["registry"], "initialized")
        self.assertEqual(errors, [])
        self.assertEqual(context["path"], str(registry_path))

        request.task_ref = "agent:other/receiver"
        with patch.dict(os.environ, {}, clear=True), patch.object(
            preflight, "_git_common_dir", return_value=self.common_dir
        ), patch.object(preflight, "_read_json", return_value=registry), patch.object(
            preflight.os.path, "lexists", return_value=False
        ):
            _, errors, _ = preflight.evaluate_local_worktree_context(
                root=repository,
                args=request,
                claim=claim,
                facts=facts,
            )
        self.assertTrue(any("claimed task" in error for error in errors), errors)

        request.intent = "read"
        request.task_ref = EXTERNAL_REF
        with patch.dict(os.environ, {}, clear=True), patch.object(
            preflight, "_git_common_dir", return_value=self.common_dir
        ), patch.object(preflight, "_read_json", return_value=registry):
            context, errors, _ = preflight.evaluate_local_worktree_context(
                root=repository,
                args=request,
                claim=claim,
                facts=facts,
            )
        self.assertEqual(context["registry"], "initialized")
        self.assertEqual(errors, [])

    def test_mutating_preflight_validates_context_before_local_exemptions(self):
        repository = self.common_dir / "worktree"
        repository.mkdir()
        request = SimpleNamespace(
            intent="write",
            task_ref=EXTERNAL_REF,
            caller_context="malformed",
            lease_token="",
        )
        claim = {
            "package": PACKAGE,
            "writer_ref": EXTERNAL_REF,
            "branch": "work/2026-09-12-caller-compatibility-001",
        }
        facts = SimpleNamespace(
            repository=str(repository),
            branch=claim["branch"],
        )
        with patch.dict(os.environ, {}, clear=True), patch.object(
            preflight, "_is_ci_environment", return_value=True
        ):
            context, errors, warnings = preflight.evaluate_local_worktree_context(
                root=repository, args=request, claim=claim, facts=facts
            )
        self.assertEqual(context["registry"], "not_checked")
        self.assertTrue(any("identifier is invalid" in error for error in errors))
        self.assertEqual(warnings, [])

        request.caller_context = ""
        with patch.dict(
            os.environ,
            {lifecycle.CALLER_CONTEXT_ENV: "malformed"},
            clear=True,
        ), patch.object(preflight, "_is_ci_environment", return_value=True):
            context, errors, warnings = preflight.evaluate_local_worktree_context(
                root=repository, args=request, claim=claim, facts=facts
            )
        self.assertEqual(context["registry"], "not_checked")
        self.assertTrue(any("identifier is invalid" in error for error in errors))
        self.assertEqual(warnings, [])

        conflicting_environment = {
            "CODEX_THREAD_ID": THREAD_ID,
            "PEERSLATE_CALLER_REF": EXTERNAL_REF,
        }
        with patch.dict(
            os.environ, conflicting_environment, clear=True
        ), patch.object(preflight, "_is_ci_environment", return_value=True):
            context, errors, warnings = preflight.evaluate_local_worktree_context(
                root=repository, args=request, claim=claim, facts=facts
            )
        self.assertEqual(context["registry"], "not_checked")
        self.assertTrue(any("identities disagree" in error for error in errors))
        self.assertEqual(warnings, [])

        request.caller_context = CONTEXT_ID
        with patch.dict(os.environ, {}, clear=True), patch.object(
            preflight, "_is_ci_environment", return_value=True
        ), patch.object(
            preflight, "_git_common_dir", return_value=self.common_dir
        ):
            context, errors, warnings = preflight.evaluate_local_worktree_context(
                root=repository, args=request, claim=claim, facts=facts
            )
        self.assertEqual(context["registry"], "not_initialized")
        self.assertTrue(any("requires the initialized" in error for error in errors))
        self.assertEqual(warnings, [])

        request.caller_context = "b" * 32
        registry_path = self.common_dir / preflight.WORKTREE_REGISTRY_REL
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        registry_path.write_text("{}", encoding="utf-8")
        registry = {
            "schema_version": 1,
            "initialized_at": "2026-09-12T00:00:00Z",
            "repository_common_dir": str(self.common_dir),
            "worktrees": [],
            "caller_contexts": [copy.deepcopy(self.context)],
            "control_custody_transitions": [],
        }
        with patch.dict(os.environ, {}, clear=True), patch.object(
            preflight, "_is_ci_environment", return_value=True
        ), patch.object(
            preflight, "_git_common_dir", return_value=self.common_dir
        ), patch.object(preflight, "_read_json", return_value=registry):
            context, errors, _ = preflight.evaluate_local_worktree_context(
                root=repository, args=request, claim=claim, facts=facts
            )
        self.assertEqual(context["registry"], "unregistered")
        self.assertTrue(any("caller context is unknown" in error for error in errors))

        request.caller_context = ""
        with patch.dict(os.environ, {}, clear=True), patch.object(
            preflight, "_is_ci_environment", return_value=True
        ):
            context, errors, warnings = preflight.evaluate_local_worktree_context(
                root=repository, args=request, claim=claim, facts=facts
            )
        self.assertEqual(context["registry"], "ci_skipped")
        self.assertEqual(errors, [])
        self.assertTrue(warnings)

    def test_no_history_preflight_reconciles_supplied_identity_conflicts(self):
        repository = self.common_dir / "worktree"
        repository.mkdir()
        registry_path = self.common_dir / preflight.WORKTREE_REGISTRY_REL
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        registry_path.write_text("{}", encoding="utf-8")
        registry = {
            "schema_version": 1,
            "initialized_at": "2026-09-12T00:00:00Z",
            "repository_common_dir": str(self.common_dir),
            "worktrees": [
                {
                    "path": str(repository),
                    "kind": "durable",
                    "state": "active",
                    "package": PACKAGE,
                    "task_ref": EXTERNAL_REF,
                    "branch": "work/2026-09-12-caller-compatibility-001",
                    "lease": None,
                }
            ],
            "caller_contexts": [],
            "control_custody_transitions": [],
        }
        request = SimpleNamespace(
            intent="write",
            task_ref=EXTERNAL_REF,
            caller_context="",
            lease_token="",
        )
        claim = {
            "package": PACKAGE,
            "writer_ref": EXTERNAL_REF,
            "branch": "work/2026-09-12-caller-compatibility-001",
        }
        facts = SimpleNamespace(repository=str(repository), branch=claim["branch"])
        environment = {
            "CODEX_THREAD_ID": THREAD_ID,
            "PEERSLATE_CALLER_REF": EXTERNAL_REF,
        }
        with patch.dict(os.environ, environment, clear=True), patch.object(
            preflight, "_is_ci_environment", return_value=False
        ), patch.object(
            preflight, "_git_common_dir", return_value=self.common_dir
        ), patch.object(preflight, "_read_json", return_value=registry), patch.object(
            preflight.os.path, "lexists", return_value=False
        ):
            _, errors, _ = preflight.evaluate_local_worktree_context(
                root=repository, args=request, claim=claim, facts=facts
            )
        self.assertTrue(any("identities disagree" in error for error in errors), errors)

    def test_lifecycle_parser_exposes_context_on_scoped_commands(self):
        parsed = lifecycle._parser().parse_args(
            [
                "control-run",
                "--task-ref",
                EXTERNAL_REF,
                "--lease-token",
                "f" * 64,
                "--caller-context",
                CONTEXT_ID,
                "--execute",
                "--",
                "python",
                "-V",
            ]
        )
        self.assertEqual(parsed.caller_context, CONTEXT_ID)
        self.assertEqual(parsed.command, ["--", "python", "-V"])

    def test_context_cannot_bootstrap_an_absent_registry(self):
        request = SimpleNamespace(execute=True, caller_context=CONTEXT_ID)
        with self.assertRaisesRegex(
            lifecycle.Refusal,
            "cannot initialize an absent repository registry",
        ):
            lifecycle.command_init(None, request)

    def test_finalize_rechecks_context_package_scope_under_lock(self):
        repository_context = SimpleNamespace(
            registry_path=self.common_dir / "registry.json",
            common_dir=self.common_dir,
        )
        snapshot = {
            "caller_contexts": [copy.deepcopy(self.context)],
            "control_custody_transitions": [],
            "worktrees": [
                {
                    "state": "active",
                    "task_ref": EXTERNAL_REF,
                    "package": PACKAGE,
                    "path": str(self.common_dir / "package"),
                }
            ],
        }
        locked = copy.deepcopy(snapshot)
        locked["worktrees"].append(
            {
                "state": "active",
                "task_ref": EXTERNAL_REF,
                "package": "PS-OTHER-001",
                "path": str(self.common_dir / "other"),
            }
        )
        request = SimpleNamespace(
            execute=True,
            task_ref=EXTERNAL_REF,
            caller_context=CONTEXT_ID,
        )
        with patch.dict(os.environ, {}, clear=True), patch.object(
            lifecycle, "_load_registry", side_effect=[snapshot, locked]
        ), patch.object(
            lifecycle, "_assert_registry_identity"
        ), patch.object(
            lifecycle, "_registry_lock", return_value=contextlib.nullcontext()
        ):
            with self.assertRaisesRegex(
                lifecycle.Refusal,
                "cannot finalize resources for another package",
            ):
                lifecycle.command_finalize_task(repository_context, request)


if __name__ == "__main__":
    unittest.main()
