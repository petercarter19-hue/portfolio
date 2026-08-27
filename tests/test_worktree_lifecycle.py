import copy
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

    def owner_reassignment_setup(
        self, label: str
    ) -> tuple[RepositoryFixture, str, str, str, Path, Path]:
        fixture = self.fixture()
        receiver = "agent:replacement-writer"
        successor = f"work/2026-08-27-test-lifecycle-{label}-recovery"
        owner_ref = "session:owner/decision:owner-reassignment"
        git(
            fixture.repo,
            "push",
            "origin",
            f"{fixture.main_sha}:refs/heads/{fixture.branch}",
        )
        fixture.initialize()
        code, old_ensure = fixture.run(
            "ensure",
            "--package",
            fixture.package,
            "--task-ref",
            fixture.writer,
            "--execute",
        )
        self.assertEqual(code, 0, old_ensure)
        code, leased = fixture.run(
            "control",
            "--task-ref",
            receiver,
            "--package",
            fixture.package,
            "--branch",
            f"work/2026-08-27-delivery-owner-reassignment-{label}",
            "--execute",
        )
        self.assertEqual(code, 0, leased)
        return (
            fixture,
            receiver,
            successor,
            owner_ref,
            Path(old_ensure["path"]),
            Path(leased["path"]),
        )

    def run_owner_reassignment_prepare(
        self,
        fixture: RepositoryFixture,
        receiver: str,
        successor: str,
        owner_ref: str,
        control_path: Path,
    ) -> tuple[int, dict]:
        return fixture.run(
            "prepare-owner-reassignment",
            "--package",
            fixture.package,
            "--task-ref",
            receiver,
            "--successor-branch",
            successor,
            "--expected-checkpoint",
            fixture.main_sha,
            "--owner-authorization-ref",
            owner_ref,
            "--execute",
            cwd=control_path,
        )

    def assert_remote_branch_absent(
        self, fixture: RepositoryFixture, branch: str
    ) -> None:
        lookup = subprocess.run(
            ["git", "ls-remote", "--heads", str(fixture.remote), branch],
            text=True,
            encoding="utf-8",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        self.assertEqual(lookup.stdout, "")

    def synthetic_owner_reassignment_preparation(
        self,
        fixture: RepositoryFixture,
        registry: dict,
        *,
        receiver: str,
        successor: str,
        owner_ref: str,
        control_path: Path,
    ) -> dict:
        context = LIFECYCLE._repo_context(fixture.repo)
        source_snapshot = {
            "local_branch_sha": LIFECYCLE._ref_sha(
                context, f"refs/heads/{fixture.branch}"
            ),
            "worktrees": LIFECYCLE._snapshot_branch_worktrees(
                context, fixture.branch, fixture.main_sha
            ),
            "durable_records": LIFECYCLE._source_durable_registry_snapshot(
                context,
                registry,
                package=fixture.package,
                from_ref=fixture.writer,
                from_branch=fixture.branch,
                checkpoint=fixture.main_sha,
            ),
        }
        preparation = {
            "schema_version": 1,
            "status": "completed",
            "package": fixture.package,
            "owner_authorization_ref": owner_ref,
            "from_ref": fixture.writer,
            "to_ref": receiver,
            "from_branch": fixture.branch,
            "to_branch": successor,
            "checkpoint_sha": fixture.main_sha,
            "control_branch": git(control_path, "branch", "--show-current"),
            "prepared_from_main": fixture.main_sha,
            "new_branch_response": (
                f"*\t{fixture.main_sha}:refs/heads/{successor}\t[new branch]"
            ),
            "source_snapshot": source_snapshot,
            "prepared_at": "2026-08-27T00:00:00Z",
        }
        preparation["preparation_id"] = LIFECYCLE._preparation_digest(preparation)
        return preparation

    def test_exact_branch_fetch_refuses_a_tip_that_moves_during_proof(self):
        context = LIFECYCLE.RepoContext(ROOT, ROOT / ".git", ROOT)

        def fake_git_result(_root, *arguments):
            self.assertEqual(arguments[0], "fetch")
            return subprocess.CompletedProcess(arguments, 0, "", "")

        with patch.object(
            LIFECYCLE, "_remote_branch_tip", side_effect=["a" * 40, "b" * 40]
        ), patch.object(
            LIFECYCLE, "_git_result", side_effect=fake_git_result
        ), patch.object(
            LIFECYCLE, "_ref_sha", return_value="a" * 40
        ), self.assertRaises(
            LIFECYCLE.Refusal
        ):
            LIFECYCLE._fetch_origin_branch(
                context, "work/2026-08-27-moving-branch"
            )

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

    def test_existing_schema_one_registry_defaults_owner_preparations(self):
        with tempfile.TemporaryDirectory() as directory:
            registry_path = Path(directory) / "worktree_registry.json"
            registry_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "initialized_at": "2026-08-23T00:00:00Z",
                        "managed_root": str(Path(directory) / "managed"),
                        "evidence_root": str(Path(directory) / "evidence"),
                        "worktrees": [],
                    }
                ),
                encoding="utf-8",
            )
            loaded = LIFECYCLE._load_registry(registry_path)
            self.assertEqual(loaded["owner_reassignment_preparations"], [])
            LIFECYCLE._atomic_write(registry_path, loaded)
            persisted = json.loads(registry_path.read_text(encoding="utf-8"))
            self.assertEqual(persisted["owner_reassignment_preparations"], [])

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
        self.assertIn("does not own the active singleton", missing["error"])
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

    def test_owner_reassignment_prepares_exact_successor_then_ensure_preserves_source(self):
        fixture = self.fixture()
        receiver = "agent:replacement-writer"
        successor = "work/2026-08-27-test-lifecycle-recovery"
        owner_ref = "session:owner/decision:owner-reassignment"
        git(
            fixture.repo,
            "push",
            "origin",
            f"{fixture.main_sha}:refs/heads/{fixture.branch}",
        )
        fixture.initialize()
        code, old_ensure = fixture.run(
            "ensure",
            "--package",
            fixture.package,
            "--task-ref",
            fixture.writer,
            "--execute",
        )
        self.assertEqual(code, 0, old_ensure)
        old_path = Path(old_ensure["path"])
        old_worktree_count = len(LIFECYCLE._worktrees(fixture.repo))

        control_branch = (
            "work/2026-08-27-delivery-owner-reassignment-test-lifecycle"
        )
        code, leased = fixture.run(
            "control",
            "--task-ref",
            receiver,
            "--purpose",
            "control",
            "--package",
            fixture.package,
            "--base",
            "origin/main",
            "--branch",
            control_branch,
            "--execute",
        )
        self.assertEqual(code, 0, leased)
        control_path = Path(leased["path"])
        code, prepared = fixture.run(
            "prepare-owner-reassignment",
            "--package",
            fixture.package,
            "--task-ref",
            receiver,
            "--successor-branch",
            successor,
            "--expected-checkpoint",
            fixture.main_sha,
            "--owner-authorization-ref",
            owner_ref,
            "--execute",
            cwd=control_path,
        )
        self.assertEqual(code, 0, prepared)
        self.assertTrue(prepared["old_branch_preserved"])
        self.assertFalse(prepared["local_successor_created"])
        prepared_registry = json.loads(
            fixture.registry_path.read_text(encoding="utf-8")
        )
        preparations = prepared_registry["owner_reassignment_preparations"]
        self.assertEqual(len(preparations), 1)
        self.assertEqual(preparations[0]["status"], "completed")
        self.assertEqual(preparations[0]["preparation_id"], prepared["preparation_id"])
        self.assertEqual(preparations[0]["package"], fixture.package)
        self.assertEqual(preparations[0]["from_ref"], fixture.writer)
        self.assertEqual(preparations[0]["to_ref"], receiver)
        self.assertEqual(preparations[0]["from_branch"], fixture.branch)
        self.assertEqual(preparations[0]["to_branch"], successor)
        self.assertEqual(preparations[0]["checkpoint_sha"], fixture.main_sha)
        self.assertEqual(preparations[0]["control_branch"], control_branch)
        self.assertEqual(preparations[0]["prepared_from_main"], fixture.main_sha)
        self.assertEqual(
            preparations[0]["preparation_id"],
            LIFECYCLE._preparation_digest(preparations[0]),
        )
        self.assertEqual(
            git(fixture.repo, "ls-remote", "origin", f"refs/heads/{fixture.branch}").split()[0],
            fixture.main_sha,
        )
        self.assertEqual(
            git(fixture.repo, "ls-remote", "origin", f"refs/heads/{successor}").split()[0],
            fixture.main_sha,
        )
        self.assertEqual(len(LIFECYCLE._worktrees(fixture.repo)), old_worktree_count + 1)
        self.assertIsNone(
            LIFECYCLE._ref_sha(
                LIFECYCLE._repo_context(fixture.repo), f"refs/heads/{successor}"
            )
        )
        self.assertEqual(git(old_path, "rev-parse", "HEAD"), fixture.main_sha)
        self.assertEqual(git(old_path, "status", "--porcelain"), "")

        code, before_merge = fixture.run(
            "ensure",
            "--package",
            fixture.package,
            "--task-ref",
            receiver,
            "--execute",
        )
        self.assertEqual(code, 2, before_merge)
        self.assertIn("writer_ref", before_merge["error"])

        claim_path = (
            fixture.repo
            / "docs"
            / "governance"
            / "lane_claims"
            / f"{fixture.package}.json"
        )
        merged_claim = json.loads(claim_path.read_text(encoding="utf-8"))
        merged_claim.update(
            {
                "writer_ref": receiver,
                "branch": successor,
                "handoff": {
                    "type": "owner_reassignment",
                    "from_ref": fixture.writer,
                    "to_ref": receiver,
                    "from_branch": fixture.branch,
                    "to_branch": successor,
                    "checkpoint_sha": fixture.main_sha,
                    "owner_authorization_ref": owner_ref,
                },
            }
        )
        claim_path.write_text(json.dumps(merged_claim, indent=2) + "\n", encoding="utf-8")
        git(fixture.repo, "add", str(claim_path.relative_to(fixture.repo)))
        git(fixture.repo, "commit", "-m", "merge owner reassignment control")
        git(fixture.repo, "push", "origin", "main")

        code, recovered = fixture.run(
            "ensure",
            "--package",
            fixture.package,
            "--task-ref",
            receiver,
            "--execute",
        )
        self.assertEqual(code, 0, recovered)
        new_path = Path(recovered["path"])
        self.assertNotEqual(
            os.path.normcase(str(old_path)), os.path.normcase(str(new_path))
        )
        self.assertEqual(git(new_path, "rev-parse", "HEAD"), fixture.main_sha)
        self.assertEqual(git(old_path, "rev-parse", "HEAD"), fixture.main_sha)
        registry = json.loads(fixture.registry_path.read_text(encoding="utf-8"))
        sources = [
            record
            for record in registry["worktrees"]
            if record.get("kind") == "reassignment_source"
            and record.get("package") == fixture.package
        ]
        durable = [
            record
            for record in registry["worktrees"]
            if record.get("kind") == "durable"
            and record.get("state") == "active"
            and record.get("package") == fixture.package
        ]
        self.assertEqual(len(sources), 1)
        self.assertEqual(len(durable), 1)
        self.assertEqual(sources[0]["branch"], fixture.branch)
        self.assertEqual(durable[0]["branch"], successor)
        consumed = registry["owner_reassignment_preparations"]
        self.assertEqual(len(consumed), 1)
        self.assertEqual(consumed[0]["status"], "consumed")
        self.assertEqual(consumed[0]["preparation_id"], prepared["preparation_id"])
        self.assertEqual(consumed[0]["consumed_on_main"], git(fixture.repo, "rev-parse", "origin/main"))

        (new_path / "sample.txt").write_text(
            "receiver advances successor\n", encoding="utf-8"
        )
        git(new_path, "add", "sample.txt")
        git(new_path, "commit", "-m", "advance recovered successor")
        advanced_sha = git(new_path, "rev-parse", "HEAD")
        git(new_path, "push", "origin", successor)
        code, reused = fixture.run(
            "ensure",
            "--package",
            fixture.package,
            "--task-ref",
            receiver,
            "--execute",
        )
        self.assertEqual(code, 0, reused)
        self.assertEqual(reused["status"], "reused")
        self.assertEqual(reused["head"], advanced_sha)
        self.assertEqual(git(old_path, "rev-parse", "HEAD"), fixture.main_sha)

        git(old_path, "switch", "--detach", fixture.main_sha)
        code, detached_source = fixture.run(
            "ensure",
            "--package",
            fixture.package,
            "--task-ref",
            receiver,
            "--execute",
        )
        self.assertEqual(code, 2, detached_source)
        self.assertIn("source Git identity changed", detached_source["error"])
        git(old_path, "switch", fixture.branch)

        tampered_registry = json.loads(
            fixture.registry_path.read_text(encoding="utf-8")
        )
        preserved_source = next(
            record
            for record in tampered_registry["worktrees"]
            if record.get("kind") == "reassignment_source"
            and record.get("package") == fixture.package
        )
        preserved_source["task_ref"] = "task:tampered-source"
        fixture.registry_path.write_text(
            json.dumps(tampered_registry, indent=2) + "\n", encoding="utf-8"
        )
        code, tampered_source = fixture.run(
            "ensure",
            "--package",
            fixture.package,
            "--task-ref",
            receiver,
            "--execute",
        )
        self.assertEqual(code, 2, tampered_source)
        self.assertIn("source custody changed", tampered_source["error"])

    def test_owner_reassignment_refuses_existing_successor_and_dirty_source(self):
        fixture = self.fixture()
        receiver = "agent:replacement-writer"
        successor = "work/2026-08-27-test-lifecycle-recovery"
        owner_ref = "session:owner/decision:owner-reassignment"
        git(
            fixture.repo,
            "push",
            "origin",
            f"{fixture.main_sha}:refs/heads/{fixture.branch}",
        )
        fixture.initialize()
        code, old_ensure = fixture.run(
            "ensure",
            "--package",
            fixture.package,
            "--task-ref",
            fixture.writer,
            "--execute",
        )
        self.assertEqual(code, 0, old_ensure)
        control_branch = (
            "work/2026-08-27-delivery-owner-reassignment-test-refusal"
        )
        code, leased = fixture.run(
            "control",
            "--task-ref",
            receiver,
            "--package",
            fixture.package,
            "--branch",
            control_branch,
            "--execute",
        )
        self.assertEqual(code, 0, leased)
        control_path = Path(leased["path"])
        (Path(old_ensure["path"]) / "sample.txt").write_text(
            "unpublished source work\n", encoding="utf-8"
        )
        arguments = (
            "prepare-owner-reassignment",
            "--package",
            fixture.package,
            "--task-ref",
            receiver,
            "--successor-branch",
            successor,
            "--expected-checkpoint",
            fixture.main_sha,
            "--owner-authorization-ref",
            owner_ref,
            "--execute",
        )
        code, dirty = fixture.run(*arguments, cwd=control_path)
        self.assertEqual(code, 2, dirty)
        self.assertIn("not pristine", dirty["error"])
        ls_remote = subprocess.run(
            ["git", "ls-remote", "--heads", str(fixture.remote), successor],
            text=True,
            stdout=subprocess.PIPE,
            check=True,
        ).stdout
        self.assertEqual(ls_remote, "")

        git(Path(old_ensure["path"]), "restore", "sample.txt")
        git(
            fixture.repo,
            "push",
            "origin",
            f"{fixture.main_sha}:refs/heads/{successor}",
        )
        code, occupied = fixture.run(*arguments, cwd=control_path)
        self.assertEqual(code, 2, occupied)
        self.assertIn("already exists", occupied["error"])
        self.assertEqual(git(Path(old_ensure["path"]), "rev-parse", "HEAD"), fixture.main_sha)

    def test_owner_reassignment_reconciles_every_source_durable_before_remote_creation(self):
        cases = (
            "detached",
            "switched",
            "missing",
            "wrong_path",
            "relative_path",
            "wrong_task",
            "wrong_branch",
            "wrong_head",
            "dirty",
            "ignored",
            "duplicate",
        )
        for case in cases:
            with self.subTest(case=case):
                (
                    fixture,
                    receiver,
                    successor,
                    owner_ref,
                    source_path,
                    control_path,
                ) = self.owner_reassignment_setup(case.replace("_", "-"))
                registry = json.loads(
                    fixture.registry_path.read_text(encoding="utf-8")
                )
                source_record = next(
                    record
                    for record in registry["worktrees"]
                    if record.get("kind") == "durable"
                    and record.get("package") == fixture.package
                )
                registry_changed = False
                if case == "detached":
                    git(source_path, "switch", "--detach", fixture.main_sha)
                elif case == "switched":
                    git(
                        source_path,
                        "switch",
                        "-c",
                        "work/2026-08-27-source-switched",
                    )
                elif case == "missing":
                    git(fixture.repo, "worktree", "remove", str(source_path))
                elif case == "wrong_path":
                    source_record["path"] = str(fixture.base / "wrong-source-path")
                    registry_changed = True
                elif case == "relative_path":
                    source_record["path"] = "relative-source-path"
                    registry_changed = True
                elif case == "wrong_task":
                    source_record["task_ref"] = "task:wrong-source-writer"
                    registry_changed = True
                elif case == "wrong_branch":
                    source_record["branch"] = "work/2026-08-27-wrong-source"
                    registry_changed = True
                elif case == "wrong_head":
                    source_record["head"] = "f" * 40
                    registry_changed = True
                elif case == "dirty":
                    (source_path / "sample.txt").write_text(
                        "unpublished source mutation\n", encoding="utf-8"
                    )
                elif case == "ignored":
                    (source_path / "ignored.cache").write_text(
                        "ignored source residue\n", encoding="utf-8"
                    )
                elif case == "duplicate":
                    duplicate = dict(source_record)
                    duplicate["path"] = str(fixture.base / "duplicate-source")
                    registry["worktrees"].append(duplicate)
                    registry_changed = True
                if registry_changed:
                    fixture.registry_path.write_text(
                        json.dumps(registry, indent=2) + "\n", encoding="utf-8"
                    )

                code, refused = self.run_owner_reassignment_prepare(
                    fixture,
                    receiver,
                    successor,
                    owner_ref,
                    control_path,
                )
                self.assertEqual(code, 2, refused)
                self.assert_remote_branch_absent(fixture, successor)
                final_registry = json.loads(
                    fixture.registry_path.read_text(encoding="utf-8")
                )
                self.assertIsNone(final_registry["pending"])
                self.assertEqual(
                    final_registry["owner_reassignment_preparations"], []
                )

    def test_owner_reassignment_rejects_namespace_collisions_from_every_live_source(self):
        fixture = self.fixture()
        receiver = "agent:replacement-writer"
        owner_ref = "session:owner/decision:owner-reassignment"
        namespace_parent = "work/2026-08-27-namespace-reserved"
        successor = namespace_parent + "/child"
        other_claim_path = (
            fixture.repo
            / "docs"
            / "governance"
            / "lane_claims"
            / "PS-NAMESPACE-001.json"
        )
        other_claim_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "package": "PS-NAMESPACE-001",
                    "state": "active",
                    "writer_ref": "task:namespace-writer",
                    "branch": namespace_parent,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        git(fixture.repo, "add", str(other_claim_path.relative_to(fixture.repo)))
        git(fixture.repo, "commit", "-m", "add namespace collision claim")
        git(fixture.repo, "push", "origin", "main")
        fixture.main_sha = git(fixture.repo, "rev-parse", "HEAD")
        git(
            fixture.repo,
            "push",
            "origin",
            f"{fixture.main_sha}:refs/heads/{fixture.branch}",
        )
        fixture.initialize()
        code, source = fixture.run(
            "ensure",
            "--package",
            fixture.package,
            "--task-ref",
            fixture.writer,
            "--execute",
        )
        self.assertEqual(code, 0, source)
        namespace_worktree = fixture.base / "namespace-worktree"
        git(
            fixture.repo,
            "worktree",
            "add",
            "-b",
            namespace_parent,
            str(namespace_worktree),
            "origin/main",
        )
        git(
            fixture.repo,
            "push",
            "origin",
            f"{fixture.main_sha}:refs/heads/{namespace_parent}",
        )
        git(
            fixture.repo,
            "fetch",
            "origin",
            f"+refs/heads/{namespace_parent}:refs/remotes/origin/{namespace_parent}",
        )
        registry = json.loads(fixture.registry_path.read_text(encoding="utf-8"))
        registry["worktrees"].append(
            {
                "path": str(LIFECYCLE._canonical(namespace_worktree)),
                "kind": "ephemeral",
                "state": "active",
                "package": "PS-NAMESPACE-001",
                "branch": namespace_parent,
                "source_branch": namespace_parent,
                "head": fixture.main_sha,
                "task_ref": "task:namespace-writer",
                "lease": None,
            }
        )
        fixture.registry_path.write_text(
            json.dumps(registry, indent=2) + "\n", encoding="utf-8"
        )
        control_branch = (
            "work/2026-08-27-delivery-owner-reassignment-namespace"
        )
        code, leased = fixture.run(
            "control",
            "--task-ref",
            receiver,
            "--package",
            fixture.package,
            "--branch",
            control_branch,
            "--execute",
        )
        self.assertEqual(code, 0, leased)
        code, refused = self.run_owner_reassignment_prepare(
            fixture,
            receiver,
            successor,
            owner_ref,
            Path(leased["path"]),
        )
        self.assertEqual(code, 2, refused)
        blockers = refused["blockers"]
        self.assertTrue(any(item.startswith("local head:") for item in blockers))
        self.assertTrue(
            any(item.startswith("origin tracking ref:") for item in blockers)
        )
        self.assertTrue(any(item.startswith("live claim:") for item in blockers))
        self.assertTrue(any(item.startswith("worktree:") for item in blockers))
        self.assertTrue(any(item.startswith("registry:") for item in blockers))
        self.assert_remote_branch_absent(fixture, successor)

    def test_two_successive_owner_reassignments_preserve_each_source_history(self):
        (
            fixture,
            writer_b,
            branch_b,
            owner_ref_ab,
            path_a,
            control_path,
        ) = self.owner_reassignment_setup("two-step-ab")

        def merge_reassignment(
            *,
            from_ref,
            to_ref,
            from_branch,
            to_branch,
            owner_ref,
            message,
        ):
            handoff = {
                "type": "owner_reassignment",
                "from_ref": from_ref,
                "to_ref": to_ref,
                "from_branch": from_branch,
                "to_branch": to_branch,
                "checkpoint_sha": fixture.main_sha,
                "owner_authorization_ref": owner_ref,
            }
            claim_path = (
                fixture.repo
                / "docs"
                / "governance"
                / "lane_claims"
                / f"{fixture.package}.json"
            )
            merged = json.loads(claim_path.read_text(encoding="utf-8"))
            merged.update(
                {"writer_ref": to_ref, "branch": to_branch, "handoff": handoff}
            )
            claim_path.write_text(
                json.dumps(merged, indent=2) + "\n", encoding="utf-8"
            )
            git(fixture.repo, "add", str(claim_path.relative_to(fixture.repo)))
            git(fixture.repo, "commit", "-m", message)
            git(fixture.repo, "push", "origin", "main")
            return handoff

        code, prepared_ab = self.run_owner_reassignment_prepare(
            fixture, writer_b, branch_b, owner_ref_ab, control_path
        )
        self.assertEqual(code, 0, prepared_ab)
        handoff_ab = merge_reassignment(
            from_ref=fixture.writer,
            to_ref=writer_b,
            from_branch=fixture.branch,
            to_branch=branch_b,
            owner_ref=owner_ref_ab,
            message="merge first owner reassignment",
        )
        code, ensured_b = fixture.run(
            "ensure",
            "--package",
            fixture.package,
            "--task-ref",
            writer_b,
            "--execute",
        )
        self.assertEqual(code, 0, ensured_b)
        path_b = Path(ensured_b["path"])

        code, released = fixture.run(
            "finalize-task", "--task-ref", writer_b, "--execute"
        )
        self.assertEqual(code, 0, released)
        writer_c = "agent:second-replacement-writer"
        branch_c = "work/2026-08-27-test-lifecycle-two-step-c-recovery"
        owner_ref_bc = "session:owner/decision:owner-reassignment-second"
        control_branch_bc = (
            "work/2026-08-27-delivery-owner-reassignment-two-step-bc"
        )
        code, leased_bc = fixture.run(
            "control",
            "--task-ref",
            writer_c,
            "--purpose",
            "control",
            "--package",
            fixture.package,
            "--base",
            "origin/main",
            "--branch",
            control_branch_bc,
            "--execute",
        )
        self.assertEqual(code, 0, leased_bc)
        code, prepared_bc = fixture.run(
            "prepare-owner-reassignment",
            "--package",
            fixture.package,
            "--task-ref",
            writer_c,
            "--successor-branch",
            branch_c,
            "--expected-checkpoint",
            fixture.main_sha,
            "--owner-authorization-ref",
            owner_ref_bc,
            "--execute",
            cwd=Path(leased_bc["path"]),
        )
        self.assertEqual(code, 0, prepared_bc)
        handoff_bc = merge_reassignment(
            from_ref=writer_b,
            to_ref=writer_c,
            from_branch=branch_b,
            to_branch=branch_c,
            owner_ref=owner_ref_bc,
            message="merge second owner reassignment",
        )
        code, ensured_c = fixture.run(
            "ensure",
            "--package",
            fixture.package,
            "--task-ref",
            writer_c,
            "--execute",
        )
        self.assertEqual(code, 0, ensured_c)
        path_c = Path(ensured_c["path"])
        code, reused_c = fixture.run(
            "ensure",
            "--package",
            fixture.package,
            "--task-ref",
            writer_c,
            "--execute",
        )
        self.assertEqual(code, 0, reused_c)
        self.assertEqual(reused_c["status"], "reused")
        self.assertEqual(reused_c["path"], str(path_c))

        registry = json.loads(fixture.registry_path.read_text(encoding="utf-8"))
        LIFECYCLE.validate_owner_reassignment_registry(registry)
        preparations = registry["owner_reassignment_preparations"]
        self.assertEqual([item["status"] for item in preparations], ["consumed", "consumed"])
        self.assertEqual(
            [item["preparation_id"] for item in preparations],
            [prepared_ab["preparation_id"], prepared_bc["preparation_id"]],
        )
        sources = [
            record
            for record in registry["worktrees"]
            if record.get("kind") == "reassignment_source"
            and record.get("state") == "active"
            and record.get("package") == fixture.package
        ]
        self.assertEqual(len(sources), 2)
        source_by_branch = {record["branch"]: record for record in sources}
        self.assertEqual(
            source_by_branch[fixture.branch]["preserved_by_owner_reassignment"],
            handoff_ab,
        )
        self.assertEqual(
            source_by_branch[branch_b]["preserved_by_owner_reassignment"],
            handoff_bc,
        )
        durable = [
            record
            for record in registry["worktrees"]
            if record.get("kind") == "durable"
            and record.get("state") == "active"
            and record.get("package") == fixture.package
        ]
        self.assertEqual(len(durable), 1)
        self.assertEqual(durable[0]["branch"], branch_c)
        self.assertEqual(durable[0]["path"], str(path_c))
        self.assertEqual(git(path_a, "status", "--porcelain"), "")
        self.assertEqual(git(path_b, "status", "--porcelain"), "")

    def test_owner_reassignment_requires_one_control_before_remote_creation(self):
        (
            fixture,
            receiver,
            successor,
            owner_ref,
            _source_path,
            control_path,
        ) = self.owner_reassignment_setup("duplicate-control")
        duplicate_path = fixture.base / "duplicate-control-worktree"
        duplicate_branch = (
            "work/2026-08-27-delivery-owner-reassignment-duplicate-extra"
        )
        git(
            fixture.repo,
            "worktree",
            "add",
            "-b",
            duplicate_branch,
            str(duplicate_path),
            "origin/main",
        )
        registry = json.loads(fixture.registry_path.read_text(encoding="utf-8"))
        control = next(
            record
            for record in registry["worktrees"]
            if record.get("kind") == "control_singleton"
        )
        duplicate = LIFECYCLE._new_record(
            path=duplicate_path,
            kind="control_singleton",
            state="active",
            package=fixture.package,
            branch=duplicate_branch,
            head=fixture.main_sha,
            task_ref=receiver,
            lease=dict(control["lease"]),
        )
        registry["worktrees"].append(duplicate)
        fixture.registry_path.write_text(
            json.dumps(registry, indent=2) + "\n", encoding="utf-8"
        )

        code, refused = self.run_owner_reassignment_prepare(
            fixture, receiver, successor, owner_ref, control_path
        )
        self.assertEqual(code, 2, refused)
        self.assertIn("exactly one initialized control_singleton", refused["error"])
        self.assert_remote_branch_absent(fixture, successor)
        retained = json.loads(fixture.registry_path.read_text(encoding="utf-8"))
        self.assertIsNone(retained["pending"])
        self.assertEqual(retained["owner_reassignment_preparations"], [])

    def test_owner_reassignment_rejects_orphan_pending_record_before_remote_creation(self):
        (
            fixture,
            receiver,
            successor,
            owner_ref,
            _source_path,
            control_path,
        ) = self.owner_reassignment_setup("orphan-pending-record")
        registry = json.loads(fixture.registry_path.read_text(encoding="utf-8"))
        orphan = LIFECYCLE._new_record(
            path=fixture.managed / "orphan-pending-verifier",
            kind="ephemeral",
            state="pending",
            package=fixture.package,
            branch=fixture.branch,
            head=fixture.main_sha,
            task_ref=receiver,
        )
        orphan["source_branch"] = fixture.branch
        registry["worktrees"].append(orphan)
        self.assertIsNone(registry["pending"])
        fixture.registry_path.write_text(
            json.dumps(registry, indent=2) + "\n", encoding="utf-8"
        )

        code, refused = self.run_owner_reassignment_prepare(
            fixture, receiver, successor, owner_ref, control_path
        )
        self.assertEqual(code, 2, refused)
        self.assertIn("pending record without an operation journal", refused["error"])
        self.assert_remote_branch_absent(fixture, successor)
        retained = json.loads(fixture.registry_path.read_text(encoding="utf-8"))
        self.assertIsNone(retained["pending"])
        self.assertEqual(retained["owner_reassignment_preparations"], [])

    def test_every_pending_operation_requires_exact_registry_linkage_before_reconcile(self):
        (
            fixture,
            receiver,
            successor,
            _owner_ref,
            _source_path,
            _control_path,
        ) = self.owner_reassignment_setup("pending-linkage-matrix")
        context = LIFECYCLE._repo_context(fixture.repo)
        baseline = json.loads(fixture.registry_path.read_text(encoding="utf-8"))
        durable = next(
            record
            for record in baseline["worktrees"]
            if record.get("kind") == "durable"
            and record.get("package") == fixture.package
        )
        control = next(
            record
            for record in baseline["worktrees"]
            if record.get("kind") == "control_singleton"
        )
        started_at = "2026-08-27T00:00:00Z"

        create_registry = copy.deepcopy(baseline)
        target = LIFECYCLE._new_record(
            path=fixture.managed / "forged-create",
            kind="ephemeral",
            state="pending",
            package=fixture.package,
            branch=None,
            head=fixture.main_sha,
            task_ref=receiver,
        )
        create_registry["worktrees"].append(target)
        forged_target = copy.deepcopy(target)
        forged_target["task_ref"] = "agent:forged-receiver"
        create_registry["pending"] = {
            "operation": "create",
            "path": target["path"],
            "record": forged_target,
            "started_at": started_at,
        }

        retire_registry = copy.deepcopy(baseline)
        forged_retire = copy.deepcopy(durable)
        forged_retire["task_ref"] = "task:forged-retire-owner"
        retire_registry["pending"] = {
            "operation": "retire",
            "path": durable["path"],
            "record": forged_retire,
            "started_at": started_at,
        }

        control_registry = copy.deepcopy(baseline)
        before = {
            field: copy.deepcopy(control.get(field))
            for field in (
                "package",
                "branch",
                "head",
                "task_ref",
                "lease",
                "sparse_paths",
            )
        }
        target_control = {
            **copy.deepcopy(before),
            "base": before["head"],
            "allow_current_moved": True,
        }
        control_registry["pending"] = {
            "operation": "control_repoint",
            "path": control["path"],
            "record": {
                "kind": control["kind"],
                "state": control["state"],
                "package": control["package"],
                "task_ref": "agent:forged-control-owner",
            },
            "before": before,
            "target": target_control,
            "started_at": started_at,
        }

        branch_registry = copy.deepcopy(baseline)
        branch_registry["pending"] = {
            "operation": "owner_reassignment_branch_create",
            "package": fixture.package,
            "task_ref": receiver,
            "from_ref": fixture.writer,
            "from_branch": fixture.branch,
            "successor_branch": successor,
            "checkpoint_sha": fixture.main_sha,
            # owner_authorization_ref is deliberately absent.
            "push_proven_new": False,
            "started_at": started_at,
        }

        for operation, registry in {
            "create": create_registry,
            "retire": retire_registry,
            "control_repoint": control_registry,
            "owner_reassignment_branch_create": branch_registry,
        }.items():
            with self.subTest(operation=operation):
                unchanged = copy.deepcopy(registry)
                with self.assertRaises(LIFECYCLE.Refusal):
                    LIFECYCLE._reconcile_pending(context, registry)
                self.assertEqual(registry, unchanged)

    def test_real_git_orphan_retire_journal_refuses_without_mutation(self):
        (
            fixture,
            receiver,
            _successor,
            _owner_ref,
            source_path,
            control_path,
        ) = self.owner_reassignment_setup("orphan-retire")
        registry = json.loads(fixture.registry_path.read_text(encoding="utf-8"))
        durable = next(
            record
            for record in registry["worktrees"]
            if record.get("kind") == "durable"
            and record.get("package") == fixture.package
        )
        forged = copy.deepcopy(durable)
        forged["head"] = "f" * 40
        registry["pending"] = {
            "operation": "retire",
            "path": durable["path"],
            "record": forged,
            "started_at": "2026-08-27T00:00:00Z",
        }
        fixture.registry_path.write_text(
            json.dumps(registry, indent=2) + "\n", encoding="utf-8"
        )
        exact_before = fixture.registry_path.read_bytes()
        code, refused = fixture.run(
            "control",
            "--task-ref",
            receiver,
            "--package",
            fixture.package,
            "--branch",
            git(control_path, "branch", "--show-current"),
            "--execute",
        )
        self.assertEqual(code, 2, refused)
        self.assertIn("pending lifecycle operation", refused["error"])
        self.assertEqual(fixture.registry_path.read_bytes(), exact_before)
        self.assertTrue(source_path.exists())
        self.assertIsNotNone(LIFECYCLE._worktree_at(fixture.repo, source_path))

    def test_owner_reassignment_poisoned_states_refuse_before_remote_creation(self):
        (
            fixture,
            receiver,
            successor,
            owner_ref,
            _source_path,
            control_path,
        ) = self.owner_reassignment_setup("orphan-consuming")
        clean_registry = json.loads(
            fixture.registry_path.read_text(encoding="utf-8")
        )
        for case, expected_error in (
            ("malformed", "inexact field set"),
            ("duplicate", "duplicated"),
            ("incompatible", "incompatible nonterminal"),
            ("orphan", "no pending receiver creation"),
        ):
            with self.subTest(case=case):
                case_successor = successor + f"-{case}"
                registry = json.loads(json.dumps(clean_registry))
                preparation = self.synthetic_owner_reassignment_preparation(
                    fixture,
                    registry,
                    receiver=receiver,
                    successor=case_successor,
                    owner_ref=owner_ref,
                    control_path=control_path,
                )
                preparations = [preparation]
                if case == "malformed":
                    preparation["unexpected"] = True
                elif case == "duplicate":
                    preparations.append(json.loads(json.dumps(preparation)))
                else:
                    consuming = (
                        preparation
                        if case == "orphan"
                        else json.loads(json.dumps(preparation))
                    )
                    if case == "incompatible":
                        incompatible_branch = case_successor + "-other"
                        consuming.update(
                            {
                                "to_branch": incompatible_branch,
                                "new_branch_response": (
                                    f"*\t{fixture.main_sha}:refs/heads/"
                                    f"{incompatible_branch}\t[new branch]"
                                ),
                                "prepared_at": "2026-08-27T00:00:02Z",
                            }
                        )
                    consuming.update(
                        {
                            "status": "consuming",
                            "consuming_at": "2026-08-27T00:00:03Z",
                            "consuming_on_main": fixture.main_sha,
                            "consuming_receiver_path": str(
                                LIFECYCLE._canonical(
                                    fixture.managed / f"{case}-receiver"
                                )
                            ),
                        }
                    )
                    consuming["preparation_id"] = LIFECYCLE._preparation_digest(
                        consuming
                    )
                    if case == "incompatible":
                        preparations.append(consuming)
                registry["owner_reassignment_preparations"] = preparations
                fixture.registry_path.write_text(
                    json.dumps(registry, indent=2) + "\n", encoding="utf-8"
                )

                code, refused = self.run_owner_reassignment_prepare(
                    fixture,
                    receiver,
                    case_successor,
                    owner_ref,
                    control_path,
                )
                self.assertEqual(code, 2, refused)
                self.assertIn(expected_error, refused["error"])
                self.assert_remote_branch_absent(fixture, case_successor)
                retained = json.loads(
                    fixture.registry_path.read_text(encoding="utf-8")
                )
                self.assertIsNone(retained["pending"])

    def test_owner_reassignment_preparation_schema_rejects_poisoned_history(self):
        (
            fixture,
            receiver,
            successor,
            owner_ref,
            _source_path,
            control_path,
        ) = self.owner_reassignment_setup("schema-matrix")
        code, prepared = self.run_owner_reassignment_prepare(
            fixture, receiver, successor, owner_ref, control_path
        )
        self.assertEqual(code, 0, prepared)
        baseline = json.loads(fixture.registry_path.read_text(encoding="utf-8"))
        LIFECYCLE._validate_owner_reassignment_preparations(baseline)

        for case, expected_error in (
            ("extra_field", "inexact field set"),
            ("malformed_unrelated", "inexact field set"),
            ("malformed_terminal", "inexact field set"),
            ("nonstring_status", "state is invalid"),
            ("nonstring_reference", "string field has an invalid type"),
            ("bad_timestamp", "exact UTC timestamp"),
            ("numeric_checkpoint", "exact SHA string"),
            ("numeric_prepared_main", "exact SHA string"),
            ("numeric_source_local", "exact SHA string"),
            ("numeric_source_head", "exact SHA string"),
            ("numeric_durable_head", "exact SHA string"),
            ("numeric_consuming_main", "exact SHA string"),
            ("numeric_consumed_main", "exact SHA string"),
            ("bad_digest", "identity digest"),
            ("duplicate", "duplicated"),
            ("replayed_handoff", "handoff tuple is replayed"),
            ("orphan_consuming", "no pending receiver creation"),
            ("incompatible_nonterminal", "incompatible nonterminal"),
        ):
            with self.subTest(case=case):
                registry = json.loads(json.dumps(baseline))
                preparation = registry["owner_reassignment_preparations"][0]
                if case == "extra_field":
                    preparation["unexpected"] = True
                elif case == "malformed_unrelated":
                    registry["owner_reassignment_preparations"].append(
                        {"status": "completed"}
                    )
                elif case == "malformed_terminal":
                    preparation["status"] = "consumed"
                elif case == "nonstring_status":
                    preparation["status"] = []
                elif case == "nonstring_reference":
                    preparation["owner_authorization_ref"] = {
                        "session": "type-confusion"
                    }
                    preparation["preparation_id"] = (
                        LIFECYCLE._preparation_digest(preparation)
                    )
                elif case == "bad_timestamp":
                    preparation["prepared_at"] = "not-a-timestamp"
                elif case == "numeric_checkpoint":
                    preparation["checkpoint_sha"] = int("1" * 40)
                    preparation["preparation_id"] = (
                        LIFECYCLE._preparation_digest(preparation)
                    )
                elif case == "numeric_prepared_main":
                    preparation["prepared_from_main"] = int("1" * 40)
                    preparation["preparation_id"] = (
                        LIFECYCLE._preparation_digest(preparation)
                    )
                elif case == "numeric_source_local":
                    preparation["source_snapshot"]["local_branch_sha"] = int(
                        "1" * 40
                    )
                    preparation["preparation_id"] = (
                        LIFECYCLE._preparation_digest(preparation)
                    )
                elif case == "numeric_source_head":
                    preparation["source_snapshot"]["worktrees"][0]["head"] = int(
                        "1" * 40
                    )
                    preparation["preparation_id"] = (
                        LIFECYCLE._preparation_digest(preparation)
                    )
                elif case == "numeric_durable_head":
                    preparation["source_snapshot"]["durable_records"][0][
                        "head"
                    ] = int("1" * 40)
                    preparation["preparation_id"] = (
                        LIFECYCLE._preparation_digest(preparation)
                    )
                elif case == "numeric_consuming_main":
                    preparation.update(
                        {
                            "status": "consuming",
                            "consuming_at": "2026-08-27T00:00:02Z",
                            "consuming_on_main": int("1" * 40),
                            "consuming_receiver_path": str(
                                LIFECYCLE._canonical(
                                    fixture.managed / "numeric-consuming-receiver"
                                )
                            ),
                        }
                    )
                elif case == "numeric_consumed_main":
                    preparation.update(
                        {
                            "status": "consumed",
                            "consumed_at": "2026-08-27T00:00:02Z",
                            "consumed_on_main": int("1" * 40),
                        }
                    )
                elif case == "bad_digest":
                    preparation["preparation_id"] = "0" * 64
                elif case == "duplicate":
                    registry["owner_reassignment_preparations"].append(
                        json.loads(json.dumps(preparation))
                    )
                elif case == "replayed_handoff":
                    replay = json.loads(json.dumps(preparation))
                    replay.update(
                        {
                            "status": "consumed",
                            "control_branch": (
                                "work/2026-08-27-delivery-owner-reassignment-replay"
                            ),
                            "prepared_at": "2026-08-27T00:00:02Z",
                            "consumed_at": "2026-08-27T00:00:03Z",
                            "consumed_on_main": fixture.main_sha,
                        }
                    )
                    replay["preparation_id"] = LIFECYCLE._preparation_digest(replay)
                    registry["owner_reassignment_preparations"].append(replay)
                elif case == "orphan_consuming":
                    preparation.update(
                        {
                            "status": "consuming",
                            "consuming_at": "2026-08-27T00:00:02Z",
                            "consuming_on_main": fixture.main_sha,
                            "consuming_receiver_path": str(
                                LIFECYCLE._canonical(
                                    fixture.managed / "orphan-schema-receiver"
                                )
                            ),
                        }
                    )
                else:
                    consuming = json.loads(json.dumps(preparation))
                    consuming.update(
                        {
                            "status": "consuming",
                            "to_branch": successor + "-second",
                            "new_branch_response": (
                                f"*\t{fixture.main_sha}:refs/heads/"
                                f"{successor}-second\t[new branch]"
                            ),
                            "prepared_at": "2026-08-27T00:00:02Z",
                            "consuming_at": "2026-08-27T00:00:03Z",
                            "consuming_on_main": fixture.main_sha,
                            "consuming_receiver_path": str(
                                LIFECYCLE._canonical(
                                    fixture.managed / "incompatible-receiver"
                                )
                            ),
                        }
                    )
                    consuming["preparation_id"] = LIFECYCLE._preparation_digest(
                        consuming
                    )
                    registry["owner_reassignment_preparations"].append(consuming)
                with self.assertRaisesRegex(LIFECYCLE.Refusal, expected_error):
                    LIFECYCLE._validate_owner_reassignment_preparations(registry)

    def test_owner_reassignment_control_branch_cannot_equal_source_branch(self):
        fixture = self.fixture()
        receiver = "agent:replacement-writer"
        owner_ref = "session:owner/decision:owner-reassignment"
        source_branch = (
            "work/2026-08-27-delivery-owner-reassignment-source-equality"
        )
        successor = "work/2026-08-27-source-equality-recovery"
        claim_path = (
            fixture.repo
            / "docs"
            / "governance"
            / "lane_claims"
            / f"{fixture.package}.json"
        )
        source_claim = json.loads(claim_path.read_text(encoding="utf-8"))
        source_claim["branch"] = source_branch
        claim_path.write_text(
            json.dumps(source_claim, indent=2) + "\n", encoding="utf-8"
        )
        git(fixture.repo, "add", str(claim_path.relative_to(fixture.repo)))
        git(fixture.repo, "commit", "-m", "use control-shaped source branch")
        git(fixture.repo, "push", "origin", "main")
        fixture.main_sha = git(fixture.repo, "rev-parse", "HEAD")
        fixture.branch = source_branch
        git(
            fixture.repo,
            "push",
            "origin",
            f"{fixture.main_sha}:refs/heads/{source_branch}",
        )
        fixture.initialize()
        code, leased = fixture.run(
            "control",
            "--task-ref",
            receiver,
            "--package",
            fixture.package,
            "--branch",
            source_branch,
            "--execute",
        )
        self.assertEqual(code, 0, leased)
        code, refused = self.run_owner_reassignment_prepare(
            fixture,
            receiver,
            successor,
            owner_ref,
            Path(leased["path"]),
        )
        self.assertEqual(code, 2, refused)
        self.assertIn("cannot be the source branch", refused["error"])
        self.assert_remote_branch_absent(fixture, successor)

    def test_unproven_absent_pending_clears_before_a_moved_source_tip_is_checked(self):
        fixture = self.fixture()
        receiver = "agent:replacement-writer"
        successor = "work/2026-08-27-rolled-back-recovery"
        git(
            fixture.repo,
            "push",
            "origin",
            f"{fixture.main_sha}:refs/heads/{fixture.branch}",
        )
        fixture.initialize()
        control_branch = (
            "work/2026-08-27-delivery-owner-reassignment-rollback"
        )
        code, leased = fixture.run(
            "control",
            "--task-ref",
            receiver,
            "--package",
            fixture.package,
            "--branch",
            control_branch,
            "--execute",
        )
        self.assertEqual(code, 0, leased)
        registry = json.loads(fixture.registry_path.read_text(encoding="utf-8"))
        registry["pending"] = {
            "operation": "owner_reassignment_branch_create",
            "package": fixture.package,
            "task_ref": receiver,
            "from_ref": fixture.writer,
            "from_branch": fixture.branch,
            "successor_branch": successor,
            "checkpoint_sha": fixture.main_sha,
            "owner_authorization_ref": "session:owner/decision:rollback",
            "old_local_ref": None,
            "source_worktrees": [],
            "source_durable_records": [],
            "control_branch": control_branch,
            "prepared_from_main": fixture.main_sha,
            "live_claims_snapshot": LIFECYCLE._strict_live_claims(
                LIFECYCLE._repo_context(fixture.repo)
            ),
            "push_proven_new": False,
            "started_at": "2026-08-27T00:00:00Z",
        }
        fixture.registry_path.write_text(
            json.dumps(registry, indent=2) + "\n", encoding="utf-8"
        )
        moved_tip = fixture.publish_claim_branch_commit(
            "source moved after an unstarted push", advance=True
        )
        code, recovered = fixture.run(
            "control",
            "--task-ref",
            receiver,
            "--package",
            fixture.package,
            "--branch",
            control_branch,
            "--execute",
        )
        self.assertEqual(code, 0, recovered)
        self.assertEqual(recovered["recovered_pending"]["outcome"], "rolled_back")
        self.assertEqual(
            git(
                fixture.repo,
                "ls-remote",
                "origin",
                f"refs/heads/{fixture.branch}",
            ).split()[0],
            moved_tip,
        )
        self.assert_remote_branch_absent(fixture, successor)

    def test_successor_final_proof_rechecks_live_origin_main(self):
        (
            fixture,
            receiver,
            successor,
            owner_ref,
            _source_path,
            control_path,
        ) = self.owner_reassignment_setup("final-main-race")
        git(fixture.repo, "switch", "-c", "test/final-main-race", "origin/main")
        (fixture.repo / "sample.txt").write_text(
            "racing main commit\n", encoding="utf-8"
        )
        git(fixture.repo, "add", "sample.txt")
        git(fixture.repo, "commit", "-m", "prepare racing main")
        racing_sha = git(fixture.repo, "rev-parse", "HEAD")
        git(fixture.repo, "push", "origin", "HEAD:refs/heads/test-final-main-race")
        git(fixture.repo, "switch", "main")
        hook = fixture.remote / "hooks" / "post-receive"
        hook.write_text(
            "#!/bin/sh\n"
            "while read old new ref\n"
            "do\n"
            f"  if [ \"$ref\" = \"refs/heads/{successor}\" ]; then\n"
            f"    git update-ref refs/heads/main {racing_sha}\n"
            "  fi\n"
            "done\n",
            encoding="utf-8",
        )
        hook.chmod(0o755)
        code, refused = self.run_owner_reassignment_prepare(
            fixture, receiver, successor, owner_ref, control_path
        )
        self.assertEqual(code, 2, refused)
        self.assertIn("origin/main moved during successor final proof", refused["error"])
        registry = json.loads(fixture.registry_path.read_text(encoding="utf-8"))
        self.assertTrue(registry["pending"]["push_proven_new"])
        self.assertEqual(registry["owner_reassignment_preparations"], [])

    def test_successor_final_proof_rechecks_strict_live_claims(self):
        (
            fixture,
            receiver,
            successor,
            owner_ref,
            _source_path,
            control_path,
        ) = self.owner_reassignment_setup("final-claim-race")
        git(fixture.repo, "switch", "-c", "test/final-claim-race", "origin/main")
        claim_path = (
            fixture.repo
            / "docs"
            / "governance"
            / "lane_claims"
            / f"{fixture.package}.json"
        )
        racing_claim = json.loads(claim_path.read_text(encoding="utf-8"))
        racing_claim["race_marker"] = True
        claim_path.write_text(
            json.dumps(racing_claim, indent=2) + "\n", encoding="utf-8"
        )
        git(fixture.repo, "add", str(claim_path.relative_to(fixture.repo)))
        git(fixture.repo, "commit", "-m", "prepare racing live claim")
        racing_sha = git(fixture.repo, "rev-parse", "HEAD")
        git(fixture.repo, "switch", "main")
        hook = fixture.remote / "hooks" / "post-receive"
        hook.write_text(
            "#!/bin/sh\n"
            "while read old new ref\n"
            "do\n"
            f"  if [ \"$ref\" = \"refs/heads/{successor}\" ]; then\n"
            f"    git --git-dir=\"{fixture.repo / '.git'}\" update-ref "
            f"refs/remotes/origin/main {racing_sha}\n"
            "  fi\n"
            "done\n",
            encoding="utf-8",
        )
        hook.chmod(0o755)
        code, refused = self.run_owner_reassignment_prepare(
            fixture, receiver, successor, owner_ref, control_path
        )
        self.assertEqual(code, 2, refused)
        self.assertIn("live claims changed during successor final proof", refused["error"])
        registry = json.loads(fixture.registry_path.read_text(encoding="utf-8"))
        self.assertTrue(registry["pending"]["push_proven_new"])
        self.assertEqual(registry["owner_reassignment_preparations"], [])

    def test_successor_post_cas_move_never_records_completed_preparation(self):
        (
            fixture,
            receiver,
            successor,
            owner_ref,
            _source_path,
            control_path,
        ) = self.owner_reassignment_setup("successor-post-cas")
        git(fixture.repo, "switch", "-c", "test/successor-post-cas", "origin/main")
        (fixture.repo / "sample.txt").write_text(
            "racing successor commit\n", encoding="utf-8"
        )
        git(fixture.repo, "add", "sample.txt")
        git(fixture.repo, "commit", "-m", "prepare racing successor")
        racing_sha = git(fixture.repo, "rev-parse", "HEAD")
        git(
            fixture.repo,
            "push",
            "origin",
            "HEAD:refs/heads/test-successor-post-cas",
        )
        git(fixture.repo, "switch", "main")
        hook = fixture.remote / "hooks" / "post-receive"
        hook.write_text(
            "#!/bin/sh\n"
            "while read old new ref\n"
            "do\n"
            f"  if [ \"$ref\" = \"refs/heads/{successor}\" ]; then\n"
            f"    git update-ref refs/heads/{successor} {racing_sha}\n"
            "  fi\n"
            "done\n",
            encoding="utf-8",
        )
        hook.chmod(0o755)
        code, refused = self.run_owner_reassignment_prepare(
            fixture, receiver, successor, owner_ref, control_path
        )
        self.assertEqual(code, 2, refused)
        self.assertTrue(
            "successor branch moved" in refused["error"]
            or "successor branch has an unexpected tip" in refused["error"],
            refused,
        )
        registry = json.loads(fixture.registry_path.read_text(encoding="utf-8"))
        self.assertTrue(registry["pending"]["push_proven_new"])
        self.assertEqual(registry["owner_reassignment_preparations"], [])
        self.assertEqual(
            git(
                fixture.repo,
                "ls-remote",
                "origin",
                f"refs/heads/{successor}",
            ).split()[0],
            racing_sha,
        )

    def test_final_claim_read_cannot_hide_successor_move(self):
        (
            fixture,
            receiver,
            successor,
            owner_ref,
            _source_path,
            control_path,
        ) = self.owner_reassignment_setup("successor-final-claim-race")
        git(fixture.repo, "switch", "-c", "test/successor-final-claim-race", "origin/main")
        (fixture.repo / "sample.txt").write_text(
            "successor moved by final claim proof\n", encoding="utf-8"
        )
        git(fixture.repo, "add", "sample.txt")
        git(fixture.repo, "commit", "-m", "prepare final-claim successor race")
        racing_sha = git(fixture.repo, "rev-parse", "HEAD")
        git(
            fixture.repo,
            "push",
            "origin",
            "HEAD:refs/heads/test-successor-final-claim-race",
        )
        git(fixture.repo, "switch", "main")

        original_strict_live_claims = LIFECYCLE._strict_live_claims
        claim_proof_calls = 0

        def racing_claim_proof(inner_context):
            nonlocal claim_proof_calls
            claim_proof_calls += 1
            if claim_proof_calls == 3:
                git(
                    fixture.remote,
                    "update-ref",
                    f"refs/heads/{successor}",
                    racing_sha,
                )
            return original_strict_live_claims(inner_context)

        context = LIFECYCLE._repo_context(fixture.repo)
        arguments = SimpleNamespace(
            execute=True,
            package=fixture.package,
            task_ref=receiver,
            successor_branch=successor,
            expected_checkpoint=fixture.main_sha,
            owner_authorization_ref=owner_ref,
        )
        with patch.object(LIFECYCLE.Path, "cwd", return_value=control_path), patch.object(
            LIFECYCLE, "_strict_live_claims", side_effect=racing_claim_proof
        ):
            with self.assertRaisesRegex(
                LIFECYCLE.Refusal,
                "remote branch tuple moved at owner-reassignment commit boundary",
            ):
                LIFECYCLE.command_prepare_owner_reassignment(context, arguments)
        self.assertEqual(claim_proof_calls, 3)
        registry = json.loads(fixture.registry_path.read_text(encoding="utf-8"))
        self.assertTrue(registry["pending"]["push_proven_new"])
        self.assertEqual(registry["owner_reassignment_preparations"], [])
        self.assertEqual(
            git(
                fixture.repo,
                "ls-remote",
                "origin",
                f"refs/heads/{successor}",
            ).split()[0],
            racing_sha,
        )

    def test_successor_recovery_reproves_tip_at_completion_boundary(self):
        (
            fixture,
            receiver,
            successor,
            owner_ref,
            _source_path,
            control_path,
        ) = self.owner_reassignment_setup("successor-recovery-race")
        context = LIFECYCLE._repo_context(fixture.repo)
        arguments = SimpleNamespace(
            execute=True,
            package=fixture.package,
            task_ref=receiver,
            successor_branch=successor,
            expected_checkpoint=fixture.main_sha,
            owner_authorization_ref=owner_ref,
        )
        with patch.object(LIFECYCLE.Path, "cwd", return_value=control_path), patch.object(
            LIFECYCLE,
            "_reconcile_owner_reassignment_branch_create",
            side_effect=LIFECYCLE.Refusal("simulated crash after successor CAS"),
        ):
            with self.assertRaisesRegex(LIFECYCLE.Refusal, "simulated crash"):
                LIFECYCLE.command_prepare_owner_reassignment(context, arguments)
        retained_before = fixture.registry_path.read_bytes()
        registry = LIFECYCLE._load_registry(fixture.registry_path)
        self.assertTrue(registry["pending"]["push_proven_new"])
        self.assertEqual(registry["owner_reassignment_preparations"], [])

        git(fixture.repo, "switch", "-c", "test/recovery-racing-tip", "origin/main")
        (fixture.repo / "sample.txt").write_text(
            "recovery racing successor\n", encoding="utf-8"
        )
        git(fixture.repo, "add", "sample.txt")
        git(fixture.repo, "commit", "-m", "prepare recovery racing successor")
        racing_sha = git(fixture.repo, "rev-parse", "HEAD")
        git(
            fixture.repo,
            "push",
            "origin",
            "HEAD:refs/heads/test-recovery-racing-tip",
        )
        git(fixture.repo, "switch", "main")
        original_remote_tuple = LIFECYCLE._remote_branch_tuple
        tuple_proof_calls = 0

        def racing_remote_tuple(inner_context, branches):
            nonlocal tuple_proof_calls
            tuple_proof_calls += 1
            git(
                fixture.remote,
                "update-ref",
                "refs/heads/main",
                racing_sha,
            )
            return original_remote_tuple(inner_context, branches)

        with patch.object(
            LIFECYCLE, "_remote_branch_tuple", side_effect=racing_remote_tuple
        ):
            with self.assertRaisesRegex(
                LIFECYCLE.Refusal, "remote branch tuple moved at.*commit boundary"
            ):
                LIFECYCLE._reconcile_pending(context, registry)
        self.assertEqual(tuple_proof_calls, 1)
        self.assertEqual(fixture.registry_path.read_bytes(), retained_before)
        persisted = json.loads(fixture.registry_path.read_text(encoding="utf-8"))
        self.assertTrue(persisted["pending"]["push_proven_new"])
        self.assertEqual(persisted["owner_reassignment_preparations"], [])
        self.assertEqual(
            git(
                fixture.repo,
                "ls-remote",
                "origin",
                "refs/heads/main",
            ).split()[0],
            racing_sha,
        )

    def test_owner_reassignment_pending_requires_recorded_new_branch_proof(self):
        fixture = self.fixture()
        receiver = "agent:replacement-writer"
        successor = "work/2026-08-27-test-lifecycle-recovery"
        owner_ref = "session:owner/decision:owner-reassignment"
        git(
            fixture.repo,
            "push",
            "origin",
            f"{fixture.main_sha}:refs/heads/{fixture.branch}",
        )
        git(
            fixture.repo,
            "push",
            "origin",
            f"{fixture.main_sha}:refs/heads/{successor}",
        )
        fixture.initialize()
        control_branch = (
            "work/2026-08-27-delivery-owner-reassignment-pending"
        )
        control_arguments = (
            "control",
            "--task-ref",
            receiver,
            "--package",
            fixture.package,
            "--branch",
            control_branch,
            "--execute",
        )
        code, leased = fixture.run(*control_arguments)
        self.assertEqual(code, 0, leased)
        registry = json.loads(fixture.registry_path.read_text(encoding="utf-8"))
        registry["pending"] = {
            "operation": "owner_reassignment_branch_create",
            "package": fixture.package,
            "task_ref": receiver,
            "from_ref": fixture.writer,
            "from_branch": fixture.branch,
            "successor_branch": successor,
            "checkpoint_sha": fixture.main_sha,
            "owner_authorization_ref": owner_ref,
            "old_local_ref": None,
            "source_worktrees": [],
            "source_durable_records": [],
            "control_branch": control_branch,
            "prepared_from_main": fixture.main_sha,
            "live_claims_snapshot": LIFECYCLE._strict_live_claims(
                LIFECYCLE._repo_context(fixture.repo)
            ),
            "push_proven_new": False,
            "started_at": "2026-08-27T00:00:00Z",
        }
        fixture.registry_path.write_text(
            json.dumps(registry, indent=2) + "\n", encoding="utf-8"
        )
        code, ambiguous = fixture.run(*control_arguments)
        self.assertEqual(code, 2, ambiguous)
        self.assertIn("ambiguous", ambiguous["error"])
        preserved = json.loads(fixture.registry_path.read_text(encoding="utf-8"))
        self.assertFalse(preserved["pending"]["push_proven_new"])

        preserved["pending"]["push_proven_new"] = True
        preserved["pending"]["push_proven_at"] = "2026-08-27T00:00:01Z"
        preserved["pending"]["new_branch_response"] = "malformed proof"
        fixture.registry_path.write_text(
            json.dumps(preserved, indent=2) + "\n", encoding="utf-8"
        )
        code, malformed = fixture.run(*control_arguments)
        self.assertEqual(code, 2, malformed)
        self.assertIn("invalid new-branch proof", malformed["error"])
        preserved = json.loads(fixture.registry_path.read_text(encoding="utf-8"))
        self.assertTrue(preserved["pending"]["push_proven_new"])
        preserved["pending"]["new_branch_response"] = (
            f"*\t{fixture.main_sha}:refs/heads/{successor}\t[new branch]"
        )
        fixture.registry_path.write_text(
            json.dumps(preserved, indent=2) + "\n", encoding="utf-8"
        )
        code, reconciled = fixture.run(*control_arguments)
        self.assertEqual(code, 0, reconciled)
        self.assertEqual(
            reconciled["recovered_pending"]["operation"],
            "owner_reassignment_branch_create",
        )
        self.assertEqual(reconciled["recovered_pending"]["outcome"], "completed")
        completed_registry = json.loads(
            fixture.registry_path.read_text(encoding="utf-8")
        )
        self.assertIsNone(completed_registry["pending"])
        self.assertEqual(
            completed_registry["owner_reassignment_preparations"][0]["status"],
            "completed",
        )

    def test_owner_reassignment_normal_receiver_create_retains_dirty_pending(self):
        (
            fixture,
            receiver,
            successor,
            owner_ref,
            _source_path,
            control_path,
        ) = self.owner_reassignment_setup("normal-dirty-receiver")
        code, prepared = self.run_owner_reassignment_prepare(
            fixture, receiver, successor, owner_ref, control_path
        )
        self.assertEqual(code, 0, prepared)
        handoff = {
            "type": "owner_reassignment",
            "from_ref": fixture.writer,
            "to_ref": receiver,
            "from_branch": fixture.branch,
            "to_branch": successor,
            "checkpoint_sha": fixture.main_sha,
            "owner_authorization_ref": owner_ref,
        }
        claim_path = (
            fixture.repo
            / "docs"
            / "governance"
            / "lane_claims"
            / f"{fixture.package}.json"
        )
        merged_claim = json.loads(claim_path.read_text(encoding="utf-8"))
        merged_claim.update(
            {
                "writer_ref": receiver,
                "branch": successor,
                "handoff": handoff,
            }
        )
        claim_path.write_text(
            json.dumps(merged_claim, indent=2) + "\n", encoding="utf-8"
        )
        git(fixture.repo, "add", str(claim_path.relative_to(fixture.repo)))
        git(fixture.repo, "commit", "-m", "merge receiver claim for dirty hook")
        git(fixture.repo, "push", "origin", "main")

        hook = fixture.repo / ".git" / "hooks" / "post-checkout"
        hook.write_text(
            "#!/bin/sh\n"
            f"if [ \"$(git branch --show-current)\" = \"{successor}\" ]; then\n"
            "  printf '%s\\n' 'hook-created residue' > unexpected-untracked.txt\n"
            "fi\n",
            encoding="utf-8",
        )
        hook.chmod(0o755)
        code, refused = fixture.run(
            "ensure",
            "--package",
            fixture.package,
            "--task-ref",
            receiver,
            "--execute",
        )
        self.assertEqual(code, 2, refused)
        self.assertIn("receiver worktree is not pristine", refused["error"])
        retained = json.loads(fixture.registry_path.read_text(encoding="utf-8"))
        self.assertIsNotNone(retained["pending"])
        self.assertEqual(
            retained["owner_reassignment_preparations"][0]["status"],
            "consuming",
        )
        receiver_record = next(
            record
            for record in retained["worktrees"]
            if record.get("owner_reassignment_preparation_id")
            == prepared["preparation_id"]
        )
        self.assertEqual(receiver_record["state"], "pending")
        receiver_path = Path(receiver_record["path"])
        self.assertTrue((receiver_path / "unexpected-untracked.txt").exists())
        source_record = next(
            record
            for record in retained["worktrees"]
            if record.get("package") == fixture.package
            and record.get("branch") == fixture.branch
        )
        self.assertEqual(source_record["kind"], "durable")

    def test_owner_reassignment_receiver_create_reconciliation_is_atomic(self):
        for receiver_state in ("absent", "pristine", "dirty", "racing_dirty"):
            with self.subTest(receiver_state=receiver_state):
                worktree_exists = receiver_state != "absent"
                label = f"receiver-{receiver_state.replace('_', '-')}"
                (
                    fixture,
                    receiver,
                    successor,
                    owner_ref,
                    _source_path,
                    control_path,
                ) = self.owner_reassignment_setup(label)
                code, prepared = self.run_owner_reassignment_prepare(
                    fixture,
                    receiver,
                    successor,
                    owner_ref,
                    control_path,
                )
                self.assertEqual(code, 0, prepared)
                handoff = {
                    "type": "owner_reassignment",
                    "from_ref": fixture.writer,
                    "to_ref": receiver,
                    "from_branch": fixture.branch,
                    "to_branch": successor,
                    "checkpoint_sha": fixture.main_sha,
                    "owner_authorization_ref": owner_ref,
                }
                claim_path = (
                    fixture.repo
                    / "docs"
                    / "governance"
                    / "lane_claims"
                    / f"{fixture.package}.json"
                )
                merged_claim = json.loads(
                    claim_path.read_text(encoding="utf-8")
                )
                merged_claim.update(
                    {
                        "writer_ref": receiver,
                        "branch": successor,
                        "handoff": handoff,
                    }
                )
                claim_path.write_text(
                    json.dumps(merged_claim, indent=2) + "\n", encoding="utf-8"
                )
                git(
                    fixture.repo,
                    "add",
                    str(claim_path.relative_to(fixture.repo)),
                )
                git(fixture.repo, "commit", "-m", "merge receiver claim")
                git(fixture.repo, "push", "origin", "main")
                consuming_main = git(fixture.repo, "rev-parse", "HEAD")
                context = LIFECYCLE._repo_context(fixture.repo)
                registry = LIFECYCLE._load_registry(fixture.registry_path)
                preparation = registry["owner_reassignment_preparations"][0]
                source_record = next(
                    record
                    for record in registry["worktrees"]
                    if record.get("kind") == "durable"
                    and record.get("package") == fixture.package
                )
                receiver_path = fixture.managed / f"simulated-{label}"
                target = LIFECYCLE._new_record(
                    path=receiver_path,
                    kind="durable",
                    state="pending",
                    package=fixture.package,
                    branch=successor,
                    head=fixture.main_sha,
                    task_ref=receiver,
                )
                registry["worktrees"].append(target)
                transition = LIFECYCLE._begin_owner_reassignment_worktree_create(
                    preparation=preparation,
                    source_record=source_record,
                    handoff=handoff,
                    receiver_path=receiver_path,
                    origin_main=consuming_main,
                )
                target["owner_reassignment_preparation_id"] = transition[
                    "preparation_id"
                ]
                registry["pending"] = {
                    "operation": "create",
                    "path": target["path"],
                    "record": dict(target),
                    "owner_reassignment": transition,
                    "started_at": "2026-08-27T00:00:00Z",
                }
                LIFECYCLE._atomic_write(fixture.registry_path, registry)
                if worktree_exists:
                    git(
                        fixture.repo,
                        "worktree",
                        "add",
                        "-b",
                        successor,
                        str(receiver_path),
                        f"origin/{successor}",
                    )
                if receiver_state == "dirty":
                    (receiver_path / "unexpected-untracked.txt").write_text(
                        "must retain pending proof\n", encoding="utf-8"
                    )

                loaded = LIFECYCLE._load_registry(fixture.registry_path)
                if receiver_state in {"dirty", "racing_dirty"}:
                    if receiver_state == "racing_dirty":
                        real_fetch = LIFECYCLE._fetch_origin_branch
                        fetch_calls = 0

                        def racing_fetch(*arguments, **keywords):
                            nonlocal fetch_calls
                            result = real_fetch(*arguments, **keywords)
                            fetch_calls += 1
                            if fetch_calls == 1:
                                (
                                    receiver_path / "unexpected-untracked.txt"
                                ).write_text(
                                    "appeared during final proof\n",
                                    encoding="utf-8",
                                )
                            return result

                        with patch.object(
                            LIFECYCLE,
                            "_fetch_origin_branch",
                            side_effect=racing_fetch,
                        ), self.assertRaisesRegex(
                            LIFECYCLE.Refusal,
                            "receiver worktree is not pristine",
                        ):
                            LIFECYCLE._reconcile_pending(context, loaded)
                    else:
                        with self.assertRaisesRegex(
                            LIFECYCLE.Refusal,
                            "receiver worktree is not pristine",
                        ):
                            LIFECYCLE._reconcile_pending(context, loaded)
                    retained = json.loads(
                        fixture.registry_path.read_text(encoding="utf-8")
                    )
                    self.assertIsNotNone(retained["pending"])
                    self.assertEqual(
                        retained["owner_reassignment_preparations"][0]["status"],
                        "consuming",
                    )
                    retained_receiver = next(
                        record
                        for record in retained["worktrees"]
                        if record.get("branch") == successor
                    )
                    self.assertEqual(retained_receiver["state"], "pending")
                    self.assertTrue(
                        (receiver_path / "unexpected-untracked.txt").exists()
                    )
                    continue
                recovered = LIFECYCLE._reconcile_pending(context, loaded)
                self.assertEqual(
                    recovered["outcome"],
                    "completed" if worktree_exists else "rolled_back",
                )
                final = json.loads(
                    fixture.registry_path.read_text(encoding="utf-8")
                )
                self.assertIsNone(final["pending"])
                final_preparation = final["owner_reassignment_preparations"][0]
                if worktree_exists:
                    self.assertEqual(final_preparation["status"], "consumed")
                    final_source = next(
                        record
                        for record in final["worktrees"]
                        if record.get("package") == fixture.package
                        and record.get("kind") == "reassignment_source"
                    )
                    self.assertEqual(final_source["branch"], fixture.branch)
                    final_receiver = next(
                        record
                        for record in final["worktrees"]
                        if record.get("package") == fixture.package
                        and record.get("kind") == "durable"
                    )
                    self.assertEqual(final_receiver["branch"], successor)
                else:
                    self.assertEqual(final_preparation["status"], "completed")
                    final_source = next(
                        record
                        for record in final["worktrees"]
                        if record.get("package") == fixture.package
                    )
                    self.assertEqual(final_source["kind"], "durable")
                    self.assertFalse(receiver_path.exists())

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
