import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "worktree_lifecycle.py"
SPEC = importlib.util.spec_from_file_location("worktree_lifecycle", SCRIPT)
LIFECYCLE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = LIFECYCLE
SPEC.loader.exec_module(LIFECYCLE)


def git(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-c", "core.quotepath=false", *arguments],
        cwd=root,
        text=True,
        encoding="utf-8",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode:
        raise AssertionError(
            f"git {' '.join(arguments)} failed: {result.stderr or result.stdout}"
        )
    return result.stdout.strip()


class RepositoryFixture:
    package = "PS-TEST-LIFECYCLE-001"
    writer = "task:test-writer"
    branch = "work/2026-08-23-test-lifecycle-001"

    def __init__(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="worktree-lifecycle-")
        self.base = Path(self.temporary.name)
        self.repo = self.base / "repo"
        self.remote = self.base / "origin.git"
        self.managed = self.base / "managed"
        self.evidence = self.base / "evidence"
        self.repo.mkdir()
        git(self.base, "init", "--bare", str(self.remote))
        git(self.repo, "init", "--initial-branch=main")
        git(self.repo, "config", "user.email", "tests@peerslate.invalid")
        git(self.repo, "config", "user.name", "PeerSlate Tests")
        git(self.repo, "config", "core.autocrlf", "false")
        (self.repo / "docs" / "governance" / "lane_claims").mkdir(
            parents=True
        )
        (self.repo / "scripts").mkdir()
        (self.repo / "tests").mkdir()
        (self.repo / "AGENTS.md").write_text("test instructions\n", encoding="utf-8")
        (self.repo / "START_HERE.md").write_text("test start\n", encoding="utf-8")
        (self.repo / "sample.txt").write_text("initial\n", encoding="utf-8")
        (self.repo / ".gitignore").write_text("ignored.cache\n", encoding="utf-8")
        (self.repo / "scripts" / "placeholder.py").write_text("pass\n", encoding="utf-8")
        (self.repo / "tests" / "placeholder.txt").write_text("test\n", encoding="utf-8")
        self.write_claim("active")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-m", "initial test repository")
        git(self.repo, "remote", "add", "origin", str(self.remote))
        git(self.repo, "push", "-u", "origin", "main")
        self.main_sha = git(self.repo, "rev-parse", "HEAD")
        self.publisher_count = 0

    @property
    def registry_path(self) -> Path:
        return self.repo / ".git" / "peerslate" / "worktree_registry.json"

    def write_claim(self, state: str) -> None:
        claim = {
            "schema_version": 1,
            "package": self.package,
            "state": state,
            "writer_ref": self.writer,
            "branch": self.branch,
            "surfaces": ["sample.txt", ".gitignore"],
        }
        path = (
            self.repo
            / "docs"
            / "governance"
            / "lane_claims"
            / f"{self.package}.json"
        )
        path.write_text(json.dumps(claim, indent=2) + "\n", encoding="utf-8")

    def close_claim(self) -> None:
        self.write_claim("closed")
        git(self.repo, "add", f"docs/governance/lane_claims/{self.package}.json")
        git(self.repo, "commit", "-m", "close test claim")
        git(self.repo, "push", "origin", "main")

    def publish_claim_branch_commit(self, content: str, *, advance: bool = False) -> str:
        self.publisher_count += 1
        publisher = self.base / f"publisher-{self.publisher_count}"
        git(self.base, "clone", str(self.remote), str(publisher))
        git(publisher, "config", "user.email", "publisher@peerslate.invalid")
        git(publisher, "config", "user.name", "PeerSlate Publisher")
        start = f"origin/{self.branch}" if advance else "origin/main"
        git(publisher, "checkout", "-b", self.branch, start)
        (publisher / "sample.txt").write_text(content + "\n", encoding="utf-8")
        git(publisher, "add", "sample.txt")
        git(publisher, "commit", "-m", f"publisher change {self.publisher_count}")
        sha = git(publisher, "rev-parse", "HEAD")
        git(publisher, "push", "origin", f"HEAD:refs/heads/{self.branch}")
        return sha

    def run(self, *arguments: str, cwd: Path | None = None) -> tuple[int, dict]:
        result = subprocess.run(
            [sys.executable, "-B", str(SCRIPT), "--repo", str(self.repo), *arguments],
            cwd=cwd or self.repo,
            text=True,
            encoding="utf-8",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError as error:
            raise AssertionError(
                f"CLI did not emit JSON (exit={result.returncode}):\n"
                f"stdout={result.stdout}\nstderr={result.stderr}"
            ) from error
        return result.returncode, payload

    def initialize(self) -> dict:
        code, payload = self.run(
            "init",
            "--task-ref",
            self.writer,
            "--managed-root",
            str(self.managed),
            "--evidence-root",
            str(self.evidence),
            "--execute",
        )
        if code:
            raise AssertionError(payload)
        return payload

    def cleanup(self) -> None:
        self.temporary.cleanup()


class WorktreeLifecycleTests(unittest.TestCase):
    def fixture(self) -> RepositoryFixture:
        fixture = RepositoryFixture()
        self.addCleanup(fixture.cleanup)
        return fixture

    def test_porcelain_z_parser_preserves_spaces_and_detached_state(self):
        payload = (
            "worktree C:/repo with spaces\0HEAD "
            + "a" * 40
            + "\0branch refs/heads/work/test\0\0"
            + "worktree C:/detached\0HEAD "
            + "b" * 40
            + "\0detached\0\0"
        )
        records = LIFECYCLE._parse_worktree_porcelain(payload)
        self.assertTrue(records[0]["worktree"].endswith("repo with spaces"))
        self.assertEqual(records[0]["branch"], "work/test")
        self.assertIsNone(records[1]["branch"])
        self.assertTrue(records[1]["detached"])

    def test_init_ensure_is_idempotent_and_preserves_unrelated_state(self):
        fixture = self.fixture()
        unrelated = fixture.base / "unrelated"
        git(
            fixture.repo,
            "worktree",
            "add",
            "-b",
            "work/unrelated-preserved",
            str(unrelated),
            "origin/main",
        )
        git(fixture.repo, "tag", "keep-this-tag", fixture.main_sha)
        fixture.initialize()

        code, first = fixture.run(
            "ensure",
            "--package",
            fixture.package,
            "--task-ref",
            fixture.writer,
            "--execute",
        )
        self.assertEqual(code, 0, first)
        self.assertEqual(first["status"], "created")
        durable = Path(first["path"])
        self.assertTrue(durable.exists())

        code, second = fixture.run(
            "ensure",
            "--package",
            fixture.package,
            "--task-ref",
            fixture.writer,
            "--execute",
        )
        self.assertEqual(code, 0, second)
        self.assertEqual(second["status"], "reused")
        self.assertEqual(os.path.normcase(second["path"]), os.path.normcase(first["path"]))

        code, wrong = fixture.run(
            "ensure",
            "--package",
            fixture.package,
            "--task-ref",
            "task:wrong-writer",
            "--execute",
        )
        self.assertEqual(code, 2, wrong)
        self.assertIn("writer_ref", wrong["error"])
        self.assertTrue(unrelated.exists())
        self.assertEqual(git(fixture.repo, "rev-parse", "keep-this-tag"), fixture.main_sha)
        listed = git(fixture.repo, "worktree", "list", "--porcelain")
        self.assertIn(str(unrelated).replace("\\", "/"), listed.replace("\\", "/"))

    def test_duplicate_branch_refuses_then_exact_dirty_grandfathered_adoption_reuses(self):
        fixture = self.fixture()
        legacy = fixture.base / "legacy active package"
        git(
            fixture.repo,
            "worktree",
            "add",
            "-b",
            fixture.branch,
            str(legacy),
            "origin/main",
        )
        (legacy / "sample.txt").write_text("dirty preserved\n", encoding="utf-8")
        (legacy / "untracked.txt").write_text("preserve me\n", encoding="utf-8")
        fixture.initialize()

        code, duplicate = fixture.run(
            "ensure",
            "--package",
            fixture.package,
            "--task-ref",
            fixture.writer,
            "--execute",
        )
        self.assertEqual(code, 2, duplicate)
        self.assertIn("use exact adopt", duplicate["error"])

        code, primary = fixture.run(
            "adopt",
            "--package",
            fixture.package,
            "--path",
            str(fixture.repo),
            "--task-ref",
            fixture.writer,
            "--execute",
        )
        self.assertEqual(code, 2, primary)
        self.assertIn("primary", primary["error"])

        code, adopted = fixture.run(
            "adopt",
            "--package",
            fixture.package,
            "--path",
            str(legacy),
            "--task-ref",
            fixture.writer,
            "--execute",
        )
        self.assertEqual(code, 0, adopted)
        self.assertTrue(adopted["dirty_preserved"])
        registry = json.loads(fixture.registry_path.read_text(encoding="utf-8"))
        record = next(item for item in registry["worktrees"] if item.get("package") == fixture.package)
        self.assertTrue(record["outside_managed_root"])
        self.assertFalse(record["retirement_eligible"])

        code, reused = fixture.run(
            "ensure",
            "--package",
            fixture.package,
            "--task-ref",
            fixture.writer,
            "--execute",
        )
        self.assertEqual(code, 0, reused)
        self.assertEqual(reused["status"], "reused")
        self.assertEqual(os.path.normcase(reused["path"]), os.path.normcase(str(legacy.resolve())))

        code, refused = fixture.run(
            "retire",
            "--path",
            str(legacy),
            "--task-ref",
            fixture.writer,
            "--expected-head",
            fixture.main_sha,
            "--execute",
        )
        self.assertEqual(code, 2, refused)
        self.assertTrue(legacy.exists())

    def test_control_singleton_cross_task_lease_and_same_path_reuse(self):
        fixture = self.fixture()
        fixture.initialize()
        code, first = fixture.run(
            "control",
            "--task-ref",
            "task:control-a",
            "--purpose",
            "activate",
            "--package",
            fixture.package,
            "--branch",
            "work/2026-08-23-control-a",
            "--execute",
        )
        self.assertEqual(code, 0, first)
        control_path = Path(first["path"])
        self.assertEqual(control_path.name, "_control")

        code, conflict = fixture.run(
            "control",
            "--task-ref",
            "task:control-b",
            "--purpose",
            "close",
            "--package",
            fixture.package,
            "--branch",
            "work/2026-08-23-control-b",
            "--execute",
        )
        self.assertEqual(code, 2, conflict)
        self.assertIn("another task", conflict["error"])

        code, finalized = fixture.run(
            "finalize-task", "--task-ref", "task:control-a", "--execute"
        )
        self.assertEqual(code, 0, finalized)
        self.assertEqual(finalized["released_singletons"], [str(control_path)])

        code, second = fixture.run(
            "control",
            "--task-ref",
            "task:control-b",
            "--purpose",
            "close",
            "--package",
            fixture.package,
            "--branch",
            "work/2026-08-23-control-b",
            "--execute",
        )
        self.assertEqual(code, 0, second)
        self.assertEqual(os.path.normcase(second["path"]), os.path.normcase(first["path"]))
        self.assertEqual(len(LIFECYCLE._worktrees(fixture.repo)), 2)

    def test_ensure_uses_exact_remote_tip_and_refuses_behind_or_divergent_reuse(self):
        behind_fixture = self.fixture()
        first_remote_tip = behind_fixture.publish_claim_branch_commit("remote one")
        behind_fixture.initialize()
        code, created = behind_fixture.run(
            "ensure",
            "--package",
            behind_fixture.package,
            "--task-ref",
            behind_fixture.writer,
            "--execute",
        )
        self.assertEqual(code, 0, created)
        self.assertEqual(created["head"], first_remote_tip)
        second_remote_tip = behind_fixture.publish_claim_branch_commit(
            "remote two", advance=True
        )
        self.assertNotEqual(second_remote_tip, first_remote_tip)
        code, behind = behind_fixture.run(
            "ensure",
            "--package",
            behind_fixture.package,
            "--task-ref",
            behind_fixture.writer,
            "--execute",
        )
        self.assertEqual(code, 2, behind)
        self.assertIn("behind", behind["error"])
        self.assertEqual(git(Path(created["path"]), "rev-parse", "HEAD"), first_remote_tip)

        divergent_fixture = self.fixture()
        divergent_fixture.initialize()
        code, local = divergent_fixture.run(
            "ensure",
            "--package",
            divergent_fixture.package,
            "--task-ref",
            divergent_fixture.writer,
            "--execute",
        )
        self.assertEqual(code, 0, local)
        registry = json.loads(
            divergent_fixture.registry_path.read_text(encoding="utf-8")
        )
        durable_record = next(
            record for record in registry["worktrees"] if record.get("kind") == "durable"
        )
        self.assertEqual(durable_record["remote_branch_status"], "confirmed_absent")
        local_path = Path(local["path"])
        (local_path / "sample.txt").write_text("local fork\n", encoding="utf-8")
        git(local_path, "add", "sample.txt")
        git(local_path, "commit", "-m", "local fork")
        divergent_fixture.publish_claim_branch_commit("remote fork")
        code, divergent = divergent_fixture.run(
            "ensure",
            "--package",
            divergent_fixture.package,
            "--task-ref",
            divergent_fixture.writer,
            "--execute",
        )
        self.assertEqual(code, 2, divergent)
        self.assertIn("diverges", divergent["error"])

    def test_verify_rejects_tagged_commit_and_stale_candidate_not_at_claim_tip(self):
        fixture = self.fixture()
        git(
            fixture.repo,
            "push",
            "origin",
            f"main:refs/heads/{fixture.branch}",
        )
        tagged_path = fixture.base / "tagged-candidate"
        git(
            fixture.repo,
            "worktree",
            "add",
            "-b",
            "work/tagged-candidate",
            str(tagged_path),
            "origin/main",
        )
        (tagged_path / "sample.txt").write_text("tag only\n", encoding="utf-8")
        git(tagged_path, "add", "sample.txt")
        git(tagged_path, "commit", "-m", "tag-only candidate")
        tagged_sha = git(tagged_path, "rev-parse", "HEAD")
        git(fixture.repo, "tag", "immutable-but-not-package-bound", tagged_sha)
        code, arbitrary = fixture.run(
            "verify",
            "--package",
            fixture.package,
            "--candidate-sha",
            tagged_sha,
            "--task-ref",
            "task:reviewer",
        )
        self.assertEqual(code, 2, arbitrary)
        self.assertIn("claimed-branch tip", arbitrary["error"])

        moved_tip = fixture.publish_claim_branch_commit("new reviewed tip", advance=True)
        code, stale = fixture.run(
            "verify",
            "--package",
            fixture.package,
            "--candidate-sha",
            fixture.main_sha,
            "--task-ref",
            "task:reviewer",
        )
        self.assertEqual(code, 2, stale)
        self.assertIn("claimed-branch tip", stale["error"])
        code, current = fixture.run(
            "verify",
            "--package",
            fixture.package,
            "--candidate-sha",
            moved_tip,
            "--task-ref",
            "task:reviewer",
        )
        self.assertEqual(code, 0, current)
        self.assertEqual(current["candidate_sha"], moved_tip)

    def test_audit_retired_record_does_not_hide_unregistered_growth(self):
        fixture = self.fixture()
        fixture.initialize()
        unexpected = fixture.managed / "unexpected-post-policy"
        git(
            fixture.repo,
            "worktree",
            "add",
            "--detach",
            str(unexpected),
            "origin/main",
        )
        registry = json.loads(fixture.registry_path.read_text(encoding="utf-8"))
        registry["worktrees"].append(
            LIFECYCLE._new_record(
                path=unexpected,
                kind="ephemeral",
                state="retired",
                package=fixture.package,
                branch=None,
                head=fixture.main_sha,
                task_ref="task:old-owner",
            )
        )
        fixture.registry_path.write_text(
            json.dumps(registry, indent=2) + "\n", encoding="utf-8"
        )
        code, audit = fixture.run("audit", "--json")
        self.assertEqual(code, 0, audit)
        unregistered_paths = {
            os.path.normcase(item["worktree"])
            for item in audit["unregistered_post_policy_growth"]
        }
        self.assertIn(os.path.normcase(str(unexpected.resolve())), unregistered_paths)
        self.assertEqual(audit["duplicates"]["paths"], [])
        self.assertEqual(audit["status"], "attention")

    def test_control_repoint_recovers_before_sparse_and_preserves_dirty_pending(self):
        fixture = self.fixture()
        fixture.initialize()
        code, first = fixture.run(
            "control",
            "--task-ref",
            "task:journal-a",
            "--purpose",
            "activate",
            "--package",
            fixture.package,
            "--branch",
            "work/2026-08-23-journal-a",
            "--execute",
        )
        self.assertEqual(code, 0, first)
        code, released = fixture.run(
            "finalize-task", "--task-ref", "task:journal-a", "--execute"
        )
        self.assertEqual(code, 0, released)
        context = LIFECYCLE._repo_context(fixture.repo)
        control_path = Path(first["path"])
        before_entry = LIFECYCLE._worktree_at(fixture.repo, control_path)
        self.assertIsNotNone(before_entry)
        arguments = SimpleNamespace(
            execute=True,
            task_ref="task:journal-b",
            package=fixture.package,
            base="origin/main",
            branch="work/2026-08-23-journal-b",
            purpose="close",
            include=[],
            release=False,
        )
        saw_pending_before_sparse = False

        def interrupted_sparse(path, includes):
            nonlocal saw_pending_before_sparse
            snapshot = json.loads(fixture.registry_path.read_text(encoding="utf-8"))
            self.assertEqual(snapshot["pending"]["operation"], "control_repoint")
            saw_pending_before_sparse = True
            raise LIFECYCLE.Refusal("simulated interruption before sparse mutation")

        with patch.object(LIFECYCLE, "_configure_sparse", side_effect=interrupted_sparse):
            with self.assertRaises(LIFECYCLE.Refusal):
                LIFECYCLE.command_control(context, arguments)
        self.assertTrue(saw_pending_before_sparse)
        interrupted_registry = json.loads(
            fixture.registry_path.read_text(encoding="utf-8")
        )
        self.assertEqual(interrupted_registry["pending"]["operation"], "control_repoint")
        interrupted_entry = LIFECYCLE._worktree_at(fixture.repo, control_path)
        self.assertEqual(
            (interrupted_entry["branch"], interrupted_entry["head"]),
            (before_entry["branch"], before_entry["head"]),
        )
        self.assertEqual(
            sum(
                os.path.normcase(record["path"]) == os.path.normcase(str(control_path))
                for record in interrupted_registry["worktrees"]
            ),
            1,
        )

        residue = control_path / "transaction-residue.tmp"
        residue.write_text("preserve", encoding="utf-8")
        code, dirty = fixture.run(
            "control",
            "--task-ref",
            "task:journal-b",
            "--purpose",
            "close",
            "--package",
            fixture.package,
            "--branch",
            "work/2026-08-23-journal-b",
            "--execute",
        )
        self.assertEqual(code, 2, dirty)
        self.assertIn("residue", dirty["error"])
        dirty_registry = json.loads(fixture.registry_path.read_text(encoding="utf-8"))
        self.assertEqual(dirty_registry["pending"]["operation"], "control_repoint")
        self.assertTrue(residue.exists())
        residue.unlink()

        code, recovered = fixture.run(
            "control",
            "--task-ref",
            "task:journal-b",
            "--purpose",
            "close",
            "--package",
            fixture.package,
            "--branch",
            "work/2026-08-23-journal-b",
            "--execute",
        )
        self.assertEqual(code, 0, recovered)
        self.assertEqual(recovered["recovered_pending"]["operation"], "control_repoint")
        final_registry = json.loads(fixture.registry_path.read_text(encoding="utf-8"))
        self.assertIsNone(final_registry["pending"])
        control = next(
            record
            for record in final_registry["worktrees"]
            if record.get("kind") == "control_singleton"
        )
        self.assertEqual(control["branch"], "work/2026-08-23-journal-b")
        self.assertEqual(control["head"], fixture.main_sha)
        self.assertEqual(control["lease"]["task_ref"], "task:journal-b")
        self.assertEqual(
            sum(
                os.path.normcase(record["path"]) == os.path.normcase(str(control_path))
                for record in final_registry["worktrees"]
            ),
            1,
        )

    def test_control_repoint_target_identity_recovers_then_blocks_other_task(self):
        fixture = self.fixture()
        fixture.initialize()
        code, first = fixture.run(
            "control",
            "--task-ref",
            "task:publish-a",
            "--purpose",
            "activate",
            "--package",
            fixture.package,
            "--branch",
            "work/2026-08-23-publish-a",
            "--execute",
        )
        self.assertEqual(code, 0, first)
        code, released = fixture.run(
            "finalize-task", "--task-ref", "task:publish-a", "--execute"
        )
        self.assertEqual(code, 0, released)
        control_path = Path(first["path"])
        context = LIFECYCLE._repo_context(fixture.repo)
        arguments = SimpleNamespace(
            execute=True,
            task_ref="task:publish-b",
            package=fixture.package,
            base="origin/main",
            branch="work/2026-08-23-publish-b",
            purpose="close",
            include=[],
            release=False,
        )
        original_atomic = LIFECYCLE._atomic_write
        interrupted = False

        def interrupt_publication(path, payload):
            nonlocal interrupted
            control = next(
                record
                for record in payload.get("worktrees", [])
                if record.get("kind") == "control_singleton"
            )
            if (
                not interrupted
                and payload.get("pending") is None
                and control.get("branch") == "work/2026-08-23-publish-b"
                and control.get("lease", {}).get("task_ref") == "task:publish-b"
            ):
                live = LIFECYCLE._worktree_at(fixture.repo, control_path)
                self.assertEqual(live["branch"], "work/2026-08-23-publish-b")
                self.assertEqual(live["head"], fixture.main_sha)
                interrupted = True
                raise LIFECYCLE.Refusal("simulated interruption before registry publication")
            return original_atomic(path, payload)

        with patch.object(LIFECYCLE, "_atomic_write", side_effect=interrupt_publication):
            with self.assertRaises(LIFECYCLE.Refusal):
                LIFECYCLE.command_control(context, arguments)
        self.assertTrue(interrupted)
        interrupted_registry = json.loads(
            fixture.registry_path.read_text(encoding="utf-8")
        )
        self.assertEqual(interrupted_registry["pending"]["operation"], "control_repoint")
        live_target = LIFECYCLE._worktree_at(fixture.repo, control_path)
        self.assertEqual(live_target["branch"], "work/2026-08-23-publish-b")
        self.assertEqual(live_target["head"], fixture.main_sha)

        code, other_task = fixture.run(
            "control",
            "--task-ref",
            "task:publish-c",
            "--purpose",
            "close",
            "--package",
            fixture.package,
            "--branch",
            "work/2026-08-23-publish-c",
            "--execute",
        )
        self.assertEqual(code, 2, other_task)
        self.assertIn("another task", other_task["error"])
        reconciled_registry = json.loads(
            fixture.registry_path.read_text(encoding="utf-8")
        )
        self.assertIsNone(reconciled_registry["pending"])
        control = next(
            record
            for record in reconciled_registry["worktrees"]
            if record.get("kind") == "control_singleton"
        )
        self.assertEqual(control["branch"], "work/2026-08-23-publish-b")
        self.assertEqual(control["head"], fixture.main_sha)
        self.assertEqual(control["lease"]["task_ref"], "task:publish-b")
        self.assertEqual(
            sum(
                os.path.normcase(record["path"]) == os.path.normcase(str(control_path))
                for record in reconciled_registry["worktrees"]
            ),
            1,
        )

        code, same_task = fixture.run(
            "control",
            "--task-ref",
            "task:publish-b",
            "--purpose",
            "close",
            "--package",
            fixture.package,
            "--branch",
            "work/2026-08-23-publish-b",
            "--execute",
        )
        self.assertEqual(code, 0, same_task)
        self.assertEqual(same_task["branch"], "work/2026-08-23-publish-b")
        self.assertEqual(same_task["head"], fixture.main_sha)

    def test_control_repoint_missing_singleton_refuses_and_preserves_registry(self):
        fixture = self.fixture()
        fixture.initialize()
        code, first = fixture.run(
            "control",
            "--task-ref",
            "task:missing-a",
            "--package",
            fixture.package,
            "--branch",
            "work/2026-08-23-missing-a",
            "--execute",
        )
        self.assertEqual(code, 0, first)
        code, released = fixture.run(
            "finalize-task", "--task-ref", "task:missing-a", "--execute"
        )
        self.assertEqual(code, 0, released)
        control_path = Path(first["path"])
        registry = json.loads(fixture.registry_path.read_text(encoding="utf-8"))
        control = next(
            record
            for record in registry["worktrees"]
            if record.get("kind") == "control_singleton"
        )
        registry["pending"] = {
            "operation": "control_repoint",
            "path": str(control_path),
            "record": {"kind": "control_singleton", "state": "active"},
            "before": {"branch": control["branch"], "head": control["head"]},
            "target": {
                "package": fixture.package,
                "branch": "work/2026-08-23-missing-b",
                "head": fixture.main_sha,
                "task_ref": "task:missing-b",
                "lease": {
                    "task_ref": "task:missing-b",
                    "purpose": "control",
                    "package": fixture.package,
                    "acquired_at": "2026-08-23T00:00:00Z",
                },
                "sparse_paths": list(LIFECYCLE.CONTROL_SPARSE_PATHS),
                "base": fixture.main_sha,
                "allow_current_moved": False,
            },
            "started_at": "2026-08-23T00:00:00Z",
        }
        fixture.registry_path.write_text(
            json.dumps(registry, indent=2) + "\n", encoding="utf-8"
        )
        git(fixture.repo, "worktree", "remove", str(control_path))
        code, missing = fixture.run(
            "control",
            "--task-ref",
            "task:missing-b",
            "--package",
            fixture.package,
            "--branch",
            "work/2026-08-23-missing-b",
            "--execute",
        )
        self.assertEqual(code, 2, missing)
        self.assertIn("absent from both filesystem and Git", missing["error"])
        preserved = json.loads(fixture.registry_path.read_text(encoding="utf-8"))
        self.assertEqual(preserved["pending"]["operation"], "control_repoint")
        self.assertEqual(
            sum(
                os.path.normcase(record["path"]) == os.path.normcase(str(control_path))
                for record in preserved["worktrees"]
            ),
            1,
        )

    def test_verify_defaults_to_zero_growth_and_ephemeral_residue_is_retained(self):
        fixture = self.fixture()
        git(
            fixture.repo,
            "push",
            "origin",
            f"main:refs/heads/{fixture.branch}",
        )
        before = len(LIFECYCLE._worktrees(fixture.repo))
        code, diff_only = fixture.run(
            "verify",
            "--package",
            fixture.package,
            "--candidate-sha",
            fixture.main_sha,
            "--task-ref",
            "task:reviewer",
        )
        self.assertEqual(code, 0, diff_only)
        self.assertEqual(diff_only["worktrees_created"], 0)
        self.assertEqual(len(LIFECYCLE._worktrees(fixture.repo)), before)

        fixture.initialize()
        code, singleton = fixture.run(
            "verify",
            "--package",
            fixture.package,
            "--candidate-sha",
            fixture.main_sha,
            "--task-ref",
            "task:reviewer",
            "--runtime-required",
            "--",
            sys.executable,
            "-c",
            "print('verified')",
        )
        self.assertEqual(code, 0, singleton)
        self.assertEqual(singleton["status"], "passed_and_released")
        self.assertEqual(len(LIFECYCLE._worktrees(fixture.repo)), before + 1)

        code, clean_ephemeral = fixture.run(
            "verify",
            "--package",
            fixture.package,
            "--candidate-sha",
            fixture.main_sha,
            "--task-ref",
            "task:ephemeral-clean",
            "--runtime-required",
            "--ephemeral",
            "--",
            sys.executable,
            "-c",
            "print('clean')",
        )
        self.assertEqual(code, 0, clean_ephemeral)
        self.assertEqual(clean_ephemeral["status"], "passed_and_retired")
        self.assertFalse(Path(clean_ephemeral["path"]).exists())

        code, reused_ephemeral = fixture.run(
            "verify",
            "--package",
            fixture.package,
            "--candidate-sha",
            fixture.main_sha,
            "--task-ref",
            "task:ephemeral-clean",
            "--runtime-required",
            "--ephemeral",
            "--",
            sys.executable,
            "-c",
            "print('clean again')",
        )
        self.assertEqual(code, 0, reused_ephemeral)
        registry = json.loads(fixture.registry_path.read_text(encoding="utf-8"))
        matching = [
            record
            for record in registry["worktrees"]
            if os.path.normcase(record["path"])
            == os.path.normcase(clean_ephemeral["path"])
        ]
        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0]["state"], "retired")

        code, residue = fixture.run(
            "verify",
            "--package",
            fixture.package,
            "--candidate-sha",
            fixture.main_sha,
            "--task-ref",
            "task:ephemeral-dirty",
            "--runtime-required",
            "--ephemeral",
            "--include",
            ".gitignore",
            "--",
            sys.executable,
            "-c",
            "from pathlib import Path; Path('ignored.cache').write_text('x')",
        )
        self.assertEqual(code, 1, residue)
        retained_path = Path(residue["path"])
        self.assertTrue(retained_path.exists())
        self.assertTrue(any(item.startswith("!!") for item in residue["residue"]))
        self.assertTrue(residue["lease_released"])
        registry = json.loads(fixture.registry_path.read_text(encoding="utf-8"))
        retained_record = next(
            record
            for record in registry["worktrees"]
            if os.path.normcase(record["path"])
            == os.path.normcase(str(retained_path))
        )
        self.assertIsNone(retained_record["lease"])
        self.assertIsNone(registry["pending"])

        code, dirty_reuse = fixture.run(
            "verify",
            "--package",
            fixture.package,
            "--candidate-sha",
            fixture.main_sha,
            "--task-ref",
            "task:ephemeral-dirty",
            "--runtime-required",
            "--ephemeral",
            "--",
            sys.executable,
            "-c",
            "print('must not run on residue')",
        )
        self.assertEqual(code, 2, dirty_reuse)
        self.assertIn("cannot accept another verifier lease", dirty_reuse["error"])
        registry = json.loads(fixture.registry_path.read_text(encoding="utf-8"))
        retained_record = next(
            record
            for record in registry["worktrees"]
            if os.path.normcase(record["path"])
            == os.path.normcase(str(retained_path))
        )
        self.assertIsNone(retained_record["lease"])
        self.assertIsNone(registry["pending"])

        code, wrong_task = fixture.run(
            "retire",
            "--path",
            str(retained_path),
            "--task-ref",
            "task:not-owner",
            "--expected-head",
            fixture.main_sha,
            "--execute",
        )
        self.assertEqual(code, 2, wrong_task)
        self.assertTrue(retained_path.exists())

        code, blocked_finalize = fixture.run(
            "finalize-task", "--task-ref", "task:ephemeral-dirty", "--execute"
        )
        self.assertEqual(code, 2, blocked_finalize)
        self.assertTrue(blocked_finalize["retained"])
        (retained_path / "ignored.cache").unlink()
        code, finished = fixture.run(
            "finalize-task", "--task-ref", "task:ephemeral-dirty", "--execute"
        )
        self.assertEqual(code, 0, finished)
        self.assertFalse(retained_path.exists())

    def test_runtime_preflight_refuses_missing_command_and_unsafe_include_without_growth(self):
        fixture = self.fixture()
        git(
            fixture.repo,
            "push",
            "origin",
            f"main:refs/heads/{fixture.branch}",
        )
        fixture.initialize()
        worktree_count = len(LIFECYCLE._worktrees(fixture.repo))
        registry_before = fixture.registry_path.read_text(encoding="utf-8")

        def assert_no_runtime_state() -> None:
            self.assertEqual(
                len(LIFECYCLE._worktrees(fixture.repo)), worktree_count
            )
            self.assertEqual(
                fixture.registry_path.read_text(encoding="utf-8"), registry_before
            )
            registry = json.loads(registry_before)
            self.assertIsNone(registry["pending"])
            self.assertFalse(
                any(
                    record.get("kind") in {"ephemeral", "control_singleton"}
                    for record in registry["worktrees"]
                )
            )
            self.assertTrue(
                all(record.get("lease") is None for record in registry["worktrees"])
            )

        code, missing = fixture.run(
            "verify",
            "--package",
            fixture.package,
            "--candidate-sha",
            fixture.main_sha,
            "--task-ref",
            "task:missing-runtime-command",
            "--runtime-required",
        )
        self.assertEqual(code, 2, missing)
        self.assertIn("nonempty command", missing["error"])
        assert_no_runtime_state()

        code, unsafe = fixture.run(
            "verify",
            "--package",
            fixture.package,
            "--candidate-sha",
            fixture.main_sha,
            "--task-ref",
            "task:unsafe-runtime-include",
            "--runtime-required",
            "--ephemeral",
            "--include",
            "../outside",
            "--",
            sys.executable,
            "-c",
            "print('must not run')",
        )
        self.assertEqual(code, 2, unsafe)
        self.assertIn("unsafe sparse include", unsafe["error"])
        assert_no_runtime_state()

    def test_active_ephemeral_reuse_refuses_changed_normalized_scope_without_mutation(self):
        fixture = self.fixture()
        git(
            fixture.repo,
            "push",
            "origin",
            f"main:refs/heads/{fixture.branch}",
        )
        fixture.initialize()
        task_ref = "task:retained-scope"
        code, retained = fixture.run(
            "verify",
            "--package",
            fixture.package,
            "--candidate-sha",
            fixture.main_sha,
            "--task-ref",
            task_ref,
            "--runtime-required",
            "--ephemeral",
            "--",
            sys.executable,
            "-c",
            "raise SystemExit(7)",
        )
        self.assertEqual(code, 7, retained)
        retained_path = Path(retained["path"])
        self.assertTrue(retained_path.exists())
        registry_before = fixture.registry_path.read_text(encoding="utf-8")
        registry = json.loads(registry_before)
        record = next(
            item
            for item in registry["worktrees"]
            if os.path.normcase(item["path"])
            == os.path.normcase(str(retained_path))
        )
        original_scope = list(record["sparse_paths"])
        self.assertEqual(original_scope, sorted(set(original_scope)))
        self.assertIsNone(record["lease"])
        self.assertIsNone(registry["pending"])
        sparse_before = git(retained_path, "sparse-checkout", "list")
        marker = fixture.base / "changed-scope-command-ran"
        worktree_count = len(LIFECYCLE._worktrees(fixture.repo))

        code, changed = fixture.run(
            "verify",
            "--package",
            fixture.package,
            "--candidate-sha",
            fixture.main_sha,
            "--task-ref",
            task_ref,
            "--runtime-required",
            "--ephemeral",
            "--include",
            "docs/new-valid-scope",
            "--",
            sys.executable,
            "-c",
            "from pathlib import Path; import sys; Path(sys.argv[1]).write_text('ran')",
            str(marker),
        )
        self.assertEqual(code, 2, changed)
        self.assertIn("sparse scope differs", changed["error"])
        self.assertFalse(marker.exists())
        self.assertEqual(len(LIFECYCLE._worktrees(fixture.repo)), worktree_count)
        self.assertEqual(
            fixture.registry_path.read_text(encoding="utf-8"), registry_before
        )
        self.assertEqual(git(retained_path, "sparse-checkout", "list"), sparse_before)
        self.assertIsNotNone(LIFECYCLE._worktree_at(fixture.repo, retained_path))

        git(
            retained_path,
            "sparse-checkout",
            "set",
            "--no-cone",
            "AGENTS.md",
            "START_HERE.md",
        )
        self.assertEqual(git(retained_path, "status", "--porcelain"), "")
        self.assertNotEqual(
            git(retained_path, "sparse-checkout", "list"), sparse_before
        )
        code, live_drift = fixture.run(
            "verify",
            "--package",
            fixture.package,
            "--candidate-sha",
            fixture.main_sha,
            "--task-ref",
            task_ref,
            "--runtime-required",
            "--ephemeral",
            "--",
            sys.executable,
            "-c",
            "from pathlib import Path; import sys; Path(sys.argv[1]).write_text('ran')",
            str(marker),
        )
        self.assertEqual(code, 2, live_drift)
        self.assertIn("live sparse scope differs", live_drift["error"])
        self.assertFalse(marker.exists())
        self.assertEqual(len(LIFECYCLE._worktrees(fixture.repo)), worktree_count)
        self.assertEqual(
            fixture.registry_path.read_text(encoding="utf-8"), registry_before
        )
        self.assertIsNotNone(LIFECYCLE._worktree_at(fixture.repo, retained_path))

    def test_retire_refuses_dirty_ignored_untracked_live_cwd_and_unpushed(self):
        fixture = self.fixture()
        fixture.initialize()
        code, ensured = fixture.run(
            "ensure",
            "--package",
            fixture.package,
            "--task-ref",
            fixture.writer,
            "--execute",
        )
        self.assertEqual(code, 0, ensured)
        durable = Path(ensured["path"])
        original = (durable / "sample.txt").read_text(encoding="utf-8")
        (durable / "sample.txt").write_text("candidate\n", encoding="utf-8")
        git(durable, "add", "sample.txt")
        git(durable, "commit", "-m", "candidate work")
        candidate = git(durable, "rev-parse", "HEAD")
        code, refreshed = fixture.run(
            "ensure",
            "--package",
            fixture.package,
            "--task-ref",
            fixture.writer,
            "--execute",
        )
        self.assertEqual(code, 0, refreshed)
        self.assertEqual(refreshed["head"], candidate)
        git(durable, "push", "-u", "origin", f"HEAD:refs/heads/{fixture.branch}")
        fixture.close_claim()

        (durable / "sample.txt").write_text("dirty\n", encoding="utf-8")
        code, dirty = fixture.run(
            "retire",
            "--path",
            str(durable),
            "--task-ref",
            fixture.writer,
            "--expected-head",
            candidate,
            "--execute",
        )
        self.assertEqual(code, 2, dirty)
        self.assertTrue(any("residue" in item for item in dirty["blockers"]))
        (durable / "sample.txt").write_text("candidate\n", encoding="utf-8")

        untracked = durable / "untracked.tmp"
        untracked.write_text("x", encoding="utf-8")
        code, untracked_result = fixture.run(
            "retire",
            "--path",
            str(durable),
            "--task-ref",
            fixture.writer,
            "--expected-head",
            candidate,
            "--execute",
        )
        self.assertEqual(code, 2, untracked_result)
        untracked.unlink()

        ignored = durable / "ignored.cache"
        ignored.write_text("x", encoding="utf-8")
        code, ignored_result = fixture.run(
            "retire",
            "--path",
            str(durable),
            "--task-ref",
            fixture.writer,
            "--expected-head",
            candidate,
            "--execute",
        )
        self.assertEqual(code, 2, ignored_result)
        ignored.unlink()

        code, live_cwd = fixture.run(
            "retire",
            "--path",
            str(durable),
            "--task-ref",
            fixture.writer,
            "--expected-head",
            candidate,
            "--execute",
            cwd=durable,
        )
        self.assertEqual(code, 2, live_cwd)
        self.assertTrue(any("current process" in item for item in live_cwd["blockers"]))

        (durable / "sample.txt").write_text("unpushed\n", encoding="utf-8")
        git(durable, "add", "sample.txt")
        git(durable, "commit", "-m", "unpushed candidate")
        unpushed_candidate = git(durable, "rev-parse", "HEAD")
        code, unpushed = fixture.run(
            "retire",
            "--path",
            str(durable),
            "--task-ref",
            fixture.writer,
            "--expected-head",
            unpushed_candidate,
            "--execute",
        )
        self.assertEqual(code, 2, unpushed)
        self.assertIn("server-verified", unpushed["error"])
        self.assertTrue(durable.exists())

        git(durable, "push", "origin", f"HEAD:refs/heads/{fixture.branch}")
        code, retired = fixture.run(
            "retire",
            "--path",
            str(durable),
            "--task-ref",
            fixture.writer,
            "--expected-head",
            unpushed_candidate,
            "--execute",
        )
        self.assertEqual(code, 0, retired)
        self.assertFalse(durable.exists())
        self.assertEqual(
            git(fixture.repo, "rev-parse", f"refs/remotes/origin/{fixture.branch}"),
            unpushed_candidate,
        )
        self.assertEqual(original, "initial\n")

    def test_pending_create_recovery_lock_contention_and_atomic_registry(self):
        fixture = self.fixture()
        fixture.initialize()
        registry = json.loads(fixture.registry_path.read_text(encoding="utf-8"))
        pending_path = fixture.managed / "pending-does-not-exist"
        pending_record = LIFECYCLE._new_record(
            path=pending_path,
            kind="ephemeral",
            state="pending",
            package=fixture.package,
            branch=None,
            head=fixture.main_sha,
            task_ref="task:pending",
        )
        registry["worktrees"].append(pending_record)
        registry["pending"] = {
            "operation": "create",
            "path": str(pending_path.resolve()),
            "record": pending_record,
            "started_at": "2026-08-23T00:00:00Z",
        }
        fixture.registry_path.write_text(
            json.dumps(registry, indent=2) + "\n", encoding="utf-8"
        )

        code, recovered = fixture.run(
            "ensure",
            "--package",
            fixture.package,
            "--task-ref",
            fixture.writer,
            "--execute",
        )
        self.assertEqual(code, 0, recovered)
        self.assertEqual(recovered["recovered_pending"]["outcome"], "rolled_back")
        self.assertIsNone(
            json.loads(fixture.registry_path.read_text(encoding="utf-8"))["pending"]
        )
        self.assertFalse(
            list(fixture.registry_path.parent.glob("worktree_registry.json.*.tmp"))
        )

        lock = fixture.registry_path.parent / LIFECYCLE.LOCK_DIRECTORY_NAME
        lock.mkdir()
        code, contention = fixture.run(
            "ensure",
            "--package",
            fixture.package,
            "--task-ref",
            fixture.writer,
            "--execute",
        )
        self.assertEqual(code, 2, contention)
        self.assertIn("lock is held", contention["error"])
        lock.rmdir()

    def test_audit_keeps_active_path_registered_when_head_drifts_and_flags_lock(self):
        fixture = self.fixture()
        fixture.initialize()
        code, ensured = fixture.run(
            "ensure",
            "--package",
            fixture.package,
            "--task-ref",
            fixture.writer,
            "--execute",
        )
        self.assertEqual(code, 0, ensured)
        durable = Path(ensured["path"])
        (durable / "sample.txt").write_text("drifted\n", encoding="utf-8")
        git(durable, "add", "sample.txt")
        git(durable, "commit", "-m", "advance durable without registry refresh")
        drifted_head = git(durable, "rev-parse", "HEAD")

        lock = fixture.registry_path.parent / LIFECYCLE.LOCK_DIRECTORY_NAME
        lock.mkdir()
        try:
            code, audit = fixture.run("audit")
        finally:
            lock.rmdir()

        self.assertEqual(code, 0, audit)
        self.assertEqual(audit["status"], "attention")
        self.assertTrue(audit["lock_present"])
        self.assertEqual(audit["unregistered_post_policy_growth"], [])
        mismatch = next(
            item
            for item in audit["mismatches"]
            if os.path.normcase(item["path"]) == os.path.normcase(str(durable))
        )
        self.assertEqual(mismatch["reason"], "live_identity_mismatch")
        self.assertIn("head", mismatch["fields"])
        self.assertEqual(mismatch["live"]["head"], drifted_head)

    def test_retire_requires_current_server_branch_not_stale_ref_or_local_tag(self):
        fixture = self.fixture()
        fixture.initialize()
        code, ensured = fixture.run(
            "ensure",
            "--package",
            fixture.package,
            "--task-ref",
            fixture.writer,
            "--execute",
        )
        self.assertEqual(code, 0, ensured)
        durable = Path(ensured["path"])
        (durable / "sample.txt").write_text("retirement candidate\n", encoding="utf-8")
        git(durable, "add", "sample.txt")
        git(durable, "commit", "-m", "retirement candidate")
        candidate = git(durable, "rev-parse", "HEAD")
        code, refreshed = fixture.run(
            "ensure",
            "--package",
            fixture.package,
            "--task-ref",
            fixture.writer,
            "--execute",
        )
        self.assertEqual(code, 0, refreshed)
        git(durable, "push", "-u", "origin", f"HEAD:refs/heads/{fixture.branch}")
        fixture.close_claim()

        git(fixture.repo, "remote", "set-url", "origin", str(fixture.base / "missing.git"))
        code, unavailable = fixture.run(
            "retire",
            "--path",
            str(durable),
            "--task-ref",
            fixture.writer,
            "--expected-head",
            candidate,
            "--execute",
        )
        self.assertEqual(code, 2, unavailable)
        self.assertTrue(durable.exists())
        git(fixture.repo, "remote", "set-url", "origin", str(fixture.remote))

        fixture.publish_claim_branch_commit("server moved", advance=True)
        code, moved = fixture.run(
            "retire",
            "--path",
            str(durable),
            "--task-ref",
            fixture.writer,
            "--expected-head",
            candidate,
            "--execute",
        )
        self.assertEqual(code, 2, moved)
        self.assertIn("server-verified", moved["error"])
        self.assertTrue(durable.exists())

        git(fixture.repo, "push", "origin", "--delete", fixture.branch)
        stale_ref = f"refs/remotes/origin/{fixture.branch}"
        git(fixture.repo, "update-ref", stale_ref, candidate)
        git(fixture.repo, "tag", "local-only-retirement-proof", candidate)
        code, absent = fixture.run(
            "retire",
            "--path",
            str(durable),
            "--task-ref",
            fixture.writer,
            "--expected-head",
            candidate,
            "--execute",
        )
        self.assertEqual(code, 2, absent)
        self.assertIn("absent from the server", absent["error"])
        self.assertTrue(durable.exists())
        self.assertEqual(git(fixture.repo, "rev-parse", stale_ref), candidate)
        self.assertEqual(
            git(fixture.repo, "rev-parse", "local-only-retirement-proof"), candidate
        )
        registry = json.loads(fixture.registry_path.read_text(encoding="utf-8"))
        record = next(
            item
            for item in registry["worktrees"]
            if os.path.normcase(item["path"]) == os.path.normcase(str(durable))
        )
        self.assertEqual(record["state"], "active")

    def test_ephemeral_invocation_lease_blocks_concurrent_retirement(self):
        fixture = self.fixture()
        git(
            fixture.repo,
            "push",
            "origin",
            f"main:refs/heads/{fixture.branch}",
        )
        fixture.initialize()
        task_ref = "task:concurrent-ephemeral"
        ready = fixture.base / "verifier-ready"
        release = fixture.base / "verifier-release"
        wait_code = (
            "from pathlib import Path\n"
            "import sys, time\n"
            "ready, release = map(Path, sys.argv[1:3])\n"
            "ready.write_text('ready', encoding='utf-8')\n"
            "deadline = time.monotonic() + 30\n"
            "while not release.exists():\n"
            "    if time.monotonic() >= deadline:\n"
            "        raise SystemExit(91)\n"
            "    time.sleep(0.05)\n"
        )
        process = subprocess.Popen(
            [
                sys.executable,
                "-B",
                str(SCRIPT),
                "--repo",
                str(fixture.repo),
                "verify",
                "--package",
                fixture.package,
                "--candidate-sha",
                fixture.main_sha,
                "--task-ref",
                task_ref,
                "--runtime-required",
                "--ephemeral",
                "--",
                sys.executable,
                "-c",
                wait_code,
                str(ready),
                str(release),
            ],
            cwd=fixture.repo,
            text=True,
            encoding="utf-8",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout = ""
        stderr = ""
        try:
            deadline = time.monotonic() + 20
            while not ready.exists() and process.poll() is None:
                if time.monotonic() >= deadline:
                    break
                time.sleep(0.05)
            if not ready.exists():
                stdout, stderr = process.communicate(timeout=5)
                self.fail(
                    "verifier did not acquire its lease and signal readiness: "
                    f"exit={process.returncode} stdout={stdout!r} stderr={stderr!r}"
                )

            registry = json.loads(fixture.registry_path.read_text(encoding="utf-8"))
            record = next(
                item
                for item in registry["worktrees"]
                if item.get("kind") == "ephemeral"
                and item.get("task_ref") == task_ref
            )
            verifier_path = Path(record["path"])
            lease = record["lease"]
            lease_token = lease["token"]
            self.assertEqual(lease["purpose"], "runtime_verify")
            self.assertEqual(lease["pid"], process.pid)
            self.assertEqual(lease["package"], fixture.package)
            self.assertEqual(lease["head"], fixture.main_sha)
            self.assertEqual(lease["source_branch"], fixture.branch)
            self.assertEqual(
                os.path.normcase(lease["path"]), os.path.normcase(str(verifier_path))
            )
            self.assertIsNone(registry["pending"])
            registered_count = len(LIFECYCLE._worktrees(fixture.repo))

            def assert_lease_preserved() -> None:
                current = json.loads(
                    fixture.registry_path.read_text(encoding="utf-8")
                )
                current_record = next(
                    item
                    for item in current["worktrees"]
                    if os.path.normcase(item["path"])
                    == os.path.normcase(str(verifier_path))
                )
                self.assertEqual(current_record["lease"]["token"], lease_token)
                self.assertIsNone(current["pending"])
                self.assertTrue(verifier_path.exists())
                self.assertIsNotNone(
                    LIFECYCLE._worktree_at(fixture.repo, verifier_path)
                )
                self.assertEqual(
                    len(LIFECYCLE._worktrees(fixture.repo)), registered_count
                )

            code, audit = fixture.run("audit")
            self.assertEqual(code, 0, audit)
            self.assertEqual(audit["status"], "attention")
            self.assertEqual(audit["unregistered_post_policy_growth"], [])
            active_lease = next(
                item
                for item in audit["active_ephemeral_invocation_leases"]
                if os.path.normcase(item["path"])
                == os.path.normcase(str(verifier_path))
            )
            self.assertNotIn("token", active_lease["lease"])
            self.assertNotIn(lease_token, json.dumps(audit, sort_keys=True))
            self.assertEqual(active_lease["lease"]["purpose"], "runtime_verify")
            self.assertEqual(active_lease["lease"]["pid"], process.pid)

            code, finalized = fixture.run(
                "finalize-task", "--task-ref", task_ref, "--execute"
            )
            self.assertEqual(code, 2, finalized)
            self.assertIn("invocation lease", finalized["error"])
            assert_lease_preserved()

            code, retired = fixture.run(
                "retire",
                "--path",
                str(verifier_path),
                "--task-ref",
                task_ref,
                "--expected-head",
                fixture.main_sha,
                "--execute",
            )
            self.assertEqual(code, 2, retired)
            self.assertIn("invocation lease", retired["error"])
            assert_lease_preserved()

            code, second = fixture.run(
                "verify",
                "--package",
                fixture.package,
                "--candidate-sha",
                fixture.main_sha,
                "--task-ref",
                task_ref,
                "--runtime-required",
                "--ephemeral",
                "--",
                sys.executable,
                "-c",
                "print('must not run concurrently')",
            )
            self.assertEqual(code, 2, second)
            self.assertIn("another verification invocation", second["error"])
            assert_lease_preserved()

            release.write_text("release", encoding="utf-8")
            stdout, stderr = process.communicate(timeout=30)
        finally:
            if process.poll() is None:
                release.write_text("release", encoding="utf-8")
                try:
                    stdout, stderr = process.communicate(timeout=30)
                except subprocess.TimeoutExpired:
                    process.kill()
                    stdout, stderr = process.communicate(timeout=10)

        self.assertEqual(process.returncode, 0, (stdout, stderr))
        completed = json.loads(stdout)
        self.assertEqual(completed["status"], "passed_and_retired")
        self.assertFalse(verifier_path.exists())
        self.assertIsNone(LIFECYCLE._worktree_at(fixture.repo, verifier_path))
        registry = json.loads(fixture.registry_path.read_text(encoding="utf-8"))
        record = next(
            item
            for item in registry["worktrees"]
            if os.path.normcase(item["path"])
            == os.path.normcase(str(verifier_path))
        )
        self.assertEqual(record["state"], "retired")
        self.assertIsNone(record["lease"])
        self.assertIsNone(registry["pending"])

    def test_command_start_failure_clears_exact_lease_for_finalize(self):
        fixture = self.fixture()
        git(
            fixture.repo,
            "push",
            "origin",
            f"main:refs/heads/{fixture.branch}",
        )
        fixture.initialize()
        task_ref = "task:missing-verifier-command"
        code, retained = fixture.run(
            "verify",
            "--package",
            fixture.package,
            "--candidate-sha",
            fixture.main_sha,
            "--task-ref",
            task_ref,
            "--runtime-required",
            "--ephemeral",
            "--",
            "peerslate-command-that-does-not-exist-7f3b",
        )
        self.assertEqual(code, 2, retained)
        self.assertEqual(retained["status"], "retained")
        self.assertIn("FileNotFoundError", retained["command_start_error"])
        self.assertTrue(retained["lease_released"])
        retained_path = Path(retained["path"])
        registry = json.loads(fixture.registry_path.read_text(encoding="utf-8"))
        record = next(
            item
            for item in registry["worktrees"]
            if os.path.normcase(item["path"])
            == os.path.normcase(str(retained_path))
        )
        self.assertIsNone(record["lease"])
        self.assertIsNone(registry["pending"])

        code, finalized = fixture.run(
            "finalize-task", "--task-ref", task_ref, "--execute"
        )
        self.assertEqual(code, 0, finalized)
        self.assertFalse(retained_path.exists())

    def test_ephemeral_token_swap_is_fail_closed_and_never_cleared(self):
        fixture = self.fixture()
        git(
            fixture.repo,
            "push",
            "origin",
            f"main:refs/heads/{fixture.branch}",
        )
        fixture.initialize()
        task_ref = "task:token-swap"
        swap_code = (
            "import json, sys\n"
            "from pathlib import Path\n"
            "path = Path(sys.argv[1])\n"
            "registry = json.loads(path.read_text(encoding='utf-8'))\n"
            "record = next(item for item in registry['worktrees'] "
            "if item.get('kind') == 'ephemeral')\n"
            "record['lease']['token'] = 'attacker-swapped-token'\n"
            "path.write_text(json.dumps(registry, indent=2) + '\\\n', "
            "encoding='utf-8')\n"
            "raise SystemExit(1)\n"
        )
        code, refused = fixture.run(
            "verify",
            "--package",
            fixture.package,
            "--candidate-sha",
            fixture.main_sha,
            "--task-ref",
            task_ref,
            "--runtime-required",
            "--ephemeral",
            "--",
            sys.executable,
            "-c",
            swap_code,
            str(fixture.registry_path),
        )
        self.assertEqual(code, 2, refused)
        self.assertIn("lease or exact invocation identity changed", refused["error"])
        registry = json.loads(fixture.registry_path.read_text(encoding="utf-8"))
        record = next(
            item
            for item in registry["worktrees"]
            if item.get("kind") == "ephemeral" and item.get("task_ref") == task_ref
        )
        self.assertEqual(record["lease"]["token"], "attacker-swapped-token")
        self.assertTrue(Path(record["path"]).exists())
        self.assertIsNotNone(LIFECYCLE._worktree_at(fixture.repo, Path(record["path"])))
        self.assertIsNone(registry["pending"])

    def test_verifier_removal_refusal_releases_or_preserves_by_exact_state(self):
        fixture = self.fixture()
        git(
            fixture.repo,
            "push",
            "origin",
            f"main:refs/heads/{fixture.branch}",
        )
        fixture.initialize()
        context = LIFECYCLE._repo_context(fixture.repo)
        task_ref = "task:remove-refusal"
        arguments = SimpleNamespace(
            package=fixture.package,
            candidate_sha=fixture.main_sha,
            task_ref=task_ref,
            runtime_required=True,
            ephemeral=True,
            include=[],
            command=[sys.executable, "-c", "pass"],
        )
        original_git = LIFECYCLE._git

        def refuse_remove(root: Path, *git_arguments: str) -> str:
            if git_arguments[:2] == ("worktree", "remove"):
                raise LIFECYCLE.Refusal("simulated ordinary worktree removal refusal")
            return original_git(root, *git_arguments)

        with patch.object(LIFECYCLE, "_git", side_effect=refuse_remove):
            retained, code = LIFECYCLE.command_verify(context, arguments)
        self.assertEqual(code, 2, retained)
        self.assertEqual(retained["status"], "retained")
        self.assertTrue(retained["lease_released"])
        self.assertTrue(retained["retirement_blockers"])
        retained_path = Path(retained["path"])
        registry = json.loads(fixture.registry_path.read_text(encoding="utf-8"))
        record = next(
            item
            for item in registry["worktrees"]
            if os.path.normcase(item["path"])
            == os.path.normcase(str(retained_path))
        )
        self.assertIsNone(record["lease"])
        self.assertIsNone(registry["pending"])
        self.assertTrue(retained_path.exists())
        self.assertIsNotNone(LIFECYCLE._worktree_at(fixture.repo, retained_path))
        code, finalized = fixture.run(
            "finalize-task", "--task-ref", task_ref, "--execute"
        )
        self.assertEqual(code, 0, finalized)

        with patch.object(
            LIFECYCLE,
            "_retirement_blockers",
            return_value=["simulated pre-pending nested-worktree blocker"],
        ):
            pre_pending, code = LIFECYCLE.command_verify(context, arguments)
        self.assertEqual(code, 2, pre_pending)
        self.assertEqual(pre_pending["status"], "retained")
        self.assertTrue(pre_pending["lease_released"])
        self.assertIn(
            "retirement refused", pre_pending["retirement_blockers"][0]
        )
        pre_pending_path = Path(pre_pending["path"])
        registry = json.loads(fixture.registry_path.read_text(encoding="utf-8"))
        record = next(
            item
            for item in registry["worktrees"]
            if os.path.normcase(item["path"])
            == os.path.normcase(str(pre_pending_path))
        )
        self.assertIsNone(record["lease"])
        self.assertIsNone(registry["pending"])
        self.assertTrue(pre_pending_path.exists())
        code, finalized = fixture.run(
            "finalize-task", "--task-ref", task_ref, "--execute"
        )
        self.assertEqual(code, 0, finalized)

        ambiguous = self.fixture()
        git(
            ambiguous.repo,
            "push",
            "origin",
            f"main:refs/heads/{ambiguous.branch}",
        )
        ambiguous.initialize()
        ambiguous_context = LIFECYCLE._repo_context(ambiguous.repo)
        ambiguous_arguments = SimpleNamespace(
            package=ambiguous.package,
            candidate_sha=ambiguous.main_sha,
            task_ref="task:ambiguous-remove",
            runtime_required=True,
            ephemeral=True,
            include=[],
            command=[sys.executable, "-c", "pass"],
        )
        remove_attempted = False
        original_worktree_at = LIFECYCLE._worktree_at

        def ambiguous_remove(root: Path, *git_arguments: str) -> str:
            nonlocal remove_attempted
            if git_arguments[:2] == ("worktree", "remove"):
                remove_attempted = True
                raise LIFECYCLE.Refusal("simulated ambiguous removal refusal")
            return original_git(root, *git_arguments)

        def mismatched_registration(root: Path, path: Path):
            if remove_attempted:
                return None
            return original_worktree_at(root, path)

        with patch.object(LIFECYCLE, "_git", side_effect=ambiguous_remove), patch.object(
            LIFECYCLE, "_worktree_at", side_effect=mismatched_registration
        ):
            with self.assertRaises(LIFECYCLE.Refusal) as caught:
                LIFECYCLE.command_verify(ambiguous_context, ambiguous_arguments)
        self.assertIn("filesystem/Git ambiguity", str(caught.exception))
        registry = json.loads(ambiguous.registry_path.read_text(encoding="utf-8"))
        record = next(
            item
            for item in registry["worktrees"]
            if item.get("kind") == "ephemeral"
        )
        self.assertIsNotNone(record["lease"])
        self.assertEqual(registry["pending"]["operation"], "retire")
        self.assertTrue(Path(record["path"]).exists())
        self.assertIsNotNone(
            LIFECYCLE._worktree_at(ambiguous.repo, Path(record["path"]))
        )

    def test_ephemeral_refetch_and_finalize_preserve_when_server_branch_disappears(self):
        fixture = self.fixture()
        git(
            fixture.repo,
            "push",
            "origin",
            f"main:refs/heads/{fixture.branch}",
        )
        fixture.initialize()
        task_ref = "task:ephemeral-server-proof"
        code, retained = fixture.run(
            "verify",
            "--package",
            fixture.package,
            "--candidate-sha",
            fixture.main_sha,
            "--task-ref",
            task_ref,
            "--runtime-required",
            "--ephemeral",
            "--",
            "git",
            "push",
            "origin",
            "--delete",
            fixture.branch,
        )
        self.assertEqual(code, 2, retained)
        self.assertEqual(retained["status"], "retained")
        self.assertEqual(retained["command_exit_code"], 0)
        self.assertTrue(any("absent from the server" in item for item in retained["proof_blockers"]))
        retained_path = Path(retained["path"])
        self.assertTrue(retained_path.exists())

        stale_ref = f"refs/remotes/origin/{fixture.branch}"
        git(fixture.repo, "update-ref", stale_ref, fixture.main_sha)
        git(fixture.repo, "tag", "local-only-ephemeral-proof", fixture.main_sha)
        worktree_count = len(LIFECYCLE._worktrees(fixture.repo))
        code, early_refusal = fixture.run(
            "verify",
            "--package",
            fixture.package,
            "--candidate-sha",
            fixture.main_sha,
            "--task-ref",
            "task:another-ephemeral",
            "--runtime-required",
            "--ephemeral",
            "--",
            sys.executable,
            "-c",
            "print('must not run')",
        )
        self.assertEqual(code, 2, early_refusal)
        self.assertEqual(len(LIFECYCLE._worktrees(fixture.repo)), worktree_count)

        code, finalized = fixture.run(
            "finalize-task", "--task-ref", task_ref, "--execute"
        )
        self.assertEqual(code, 2, finalized)
        self.assertEqual(finalized["status"], "incomplete")
        self.assertTrue(
            any(
                os.path.normcase(item["path"]) == os.path.normcase(str(retained_path))
                and any("absent from the server" in blocker for blocker in item["blockers"])
                for item in finalized["retained"]
            )
        )
        self.assertTrue(retained_path.exists())
        self.assertEqual(git(fixture.repo, "rev-parse", stale_ref), fixture.main_sha)
        self.assertEqual(
            git(fixture.repo, "rev-parse", "local-only-ephemeral-proof"),
            fixture.main_sha,
        )
        registry = json.loads(fixture.registry_path.read_text(encoding="utf-8"))
        matching = [
            item
            for item in registry["worktrees"]
            if os.path.normcase(item["path"]) == os.path.normcase(str(retained_path))
        ]
        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0]["state"], "active")
        self.assertIsNone(matching[0]["lease"])
        self.assertIsNone(registry["pending"])

    def test_evidence_path_is_external_idempotent_and_budget_aware(self):
        fixture = self.fixture()
        fixture.initialize()
        arguments = (
            "evidence-path",
            "--package",
            fixture.package,
            "--task-ref",
            fixture.writer,
            "--storage-class",
            "azure_artifact",
            "--byte-budget",
            str(2 * 1024**3),
            "--label",
            "runtime-proof",
            "--execute",
        )
        code, first = fixture.run(*arguments)
        self.assertEqual(code, 0, first)
        self.assertTrue(first["external_storage_recommended"])
        self.assertTrue(Path(first["path"]).exists())
        self.assertFalse(LIFECYCLE._is_within(first["path"], fixture.repo))
        code, second = fixture.run(*arguments)
        self.assertEqual(code, 0, second)
        self.assertEqual(second["status"], "reused")
        self.assertEqual(second["path"], first["path"])

    def test_reparse_refusal_and_source_has_no_forbidden_removal_primitives(self):
        registry = {"managed_root": str(Path(tempfile.gettempdir()) / "managed")}
        target = Path(registry["managed_root"]) / "target"
        original = LIFECYCLE._has_reparse_component
        try:
            LIFECYCLE._has_reparse_component = lambda *args, **kwargs: True
            with self.assertRaises(LIFECYCLE.Refusal):
                LIFECYCLE._assert_managed_target(registry, target)
        finally:
            LIFECYCLE._has_reparse_component = original

        source = SCRIPT.read_text(encoding="utf-8")
        for forbidden in (
            '"--force"',
            '"prune"',
            '"gc"',
            '"reset"',
            '"clean"',
            '"branch", "-D"',
            '"tag", "-d"',
        ):
            self.assertNotIn(forbidden, source)
        self.assertEqual(source.count('"worktree", "remove"'), 1)


if __name__ == "__main__":
    unittest.main()
