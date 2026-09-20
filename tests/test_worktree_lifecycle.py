import copy
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
COMPAT_FIXTURE = json.loads(
    (ROOT / "tests" / "fixtures" / "delivery_control_compat" / "manifest.json")
    .read_text(encoding="utf-8")
)
PRE_SAFE_CUSTODY_REF = COMPAT_FIXTURE["pre_safe_custody_ref"]
SCRIPT = ROOT / "scripts" / "worktree_lifecycle.py"
SPEC = importlib.util.spec_from_file_location("worktree_lifecycle", SCRIPT)
LIFECYCLE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = LIFECYCLE
SPEC.loader.exec_module(LIFECYCLE)


_IDENTITY_ENVIRONMENT = None


def setUpModule() -> None:
    global _IDENTITY_ENVIRONMENT
    _IDENTITY_ENVIRONMENT = patch.dict(
        os.environ,
        {
            "CODEX_THREAD_ID": "",
            "PEERSLATE_CALLER_REF": "",
            LIFECYCLE.CALLER_CONTEXT_ENV: "",
        },
    )
    _IDENTITY_ENVIRONMENT.start()


def tearDownModule() -> None:
    assert _IDENTITY_ENVIRONMENT is not None
    _IDENTITY_ENVIRONMENT.stop()


def invoke(*arguments: str) -> tuple[int, dict]:
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        code = LIFECYCLE.main(arguments)
    return code, json.loads(output.getvalue())


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

    def run(
        self,
        *arguments: str,
        cwd: Path | None = None,
        environment_overrides: dict[str, str] | None = None,
    ) -> tuple[int, dict]:
        environment = os.environ.copy()
        # Synthetic fixture tasks exercise legacy identity-free behavior unless
        # an individual test supplies an explicit launcher/context identity.
        environment["CODEX_THREAD_ID"] = ""
        environment.update(environment_overrides or {})
        result = subprocess.run(
            [sys.executable, "-B", str(SCRIPT), "--repo", str(self.repo), *arguments],
            cwd=cwd or self.repo,
            env=environment,
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


class HistoricalCheckoutRetirementTests(unittest.TestCase):
    def setup_historical(self, label="sample"):
        fixture = RepositoryFixture()
        self.addCleanup(fixture.cleanup)
        (fixture.repo / "scripts/worktree_lifecycle.py").write_bytes(SCRIPT.read_bytes())
        (fixture.repo / "docs/governance/WORKTREE_LIFECYCLE.md").write_text(
            "historical contract\n", encoding="utf-8"
        )
        (fixture.repo / "tests/test_worktree_lifecycle.py").write_text(
            "historical tests\n", encoding="utf-8"
        )
        git(fixture.repo, "add", ".")
        git(fixture.repo, "commit", "-m", "install historical mechanism")
        git(fixture.repo, "push", "origin", "main")
        target = fixture.base / "historical"
        branch = f"work/2026-09-07-historical-target-{label}"
        git(fixture.repo, "worktree", "add", "-b", branch, str(target), "HEAD")
        head = git(target, "rev-parse", "HEAD")
        git(target, "push", "origin", f"HEAD:refs/heads/{branch}")
        fixture.initialize()
        registry = json.loads(fixture.registry_path.read_text(encoding="utf-8"))
        before = next(record for record in registry["worktrees"] if record["path"] == str(target))
        package = "PS-HISTORICAL-CLEANUP-TEST-001"
        writer = f"agent:historical-writer-{label}"
        cleanup_branch = f"work/2026-09-07-historical-cleanup-{label}"
        owner = f"session:historical-owner/{label}"
        evidence = f"docs/governance/lane_claims/evidence/{package}.md"
        receipt_path = f"docs/governance/lane_claims/receipts/{package}.json"
        claim_path = f"docs/governance/lane_claims/{package}.json"
        allowlist_path = (
            f"docs/governance/worktree_retirement_allowlists/{package}.json"
        )
        claim = {
            "schema_version": 1,
            "package": package,
            "state": "active",
            "outcome": "test historical retirement",
            "assignment": "implementation",
            "writer_ref": writer,
            "branch": cleanup_branch,
            "delivery_path": "Protected",
            "repository_authority": "through_merge",
            "production_authority": "withheld",
            "owner_outcome_ref": owner,
            "review_requirement": "independent",
            "surfaces": [
                claim_path,
                evidence,
                receipt_path,
                allowlist_path,
                *sorted(LIFECYCLE.CLOSED_CUSTODY_REQUIRED_SURFACES),
            ],
            "evidence_surfaces": [evidence],
            "domains": [
                *sorted(LIFECYCLE.CLOSED_CUSTODY_REQUIRED_DOMAINS),
                "tooling:worktree-lifecycle:historical-checkout-retirement",
            ],
        }
        entry = {
            "path": str(target),
            "branch": branch,
            "expected_head": head,
            "registry_record_sha256": hashlib.sha256(
                json.dumps(before, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest(),
        }
        manifest = {
            "schema_version": 1,
            "cleanup_package": package,
            "owner_authorization_ref": owner,
            "repository_common_dir": str(fixture.repo / ".git"),
            "repository_primary_root": str(fixture.repo),
            "targets": [entry],
        }
        for relative, value in ((claim_path, claim), (allowlist_path, manifest)):
            destination = fixture.repo / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
        (fixture.repo / evidence).parent.mkdir(parents=True, exist_ok=True)
        (fixture.repo / evidence).write_text(
            "reviewed historical mechanism and list\n", encoding="utf-8"
        )
        git(fixture.repo, "add", ".")
        git(fixture.repo, "commit", "-m", "historical reviewed candidate")
        candidate = git(fixture.repo, "rev-parse", "HEAD")
        receipt = {
            "schema_version": 1,
            "package": package,
            "candidate_sha": candidate,
            "review_type": "independent",
            "reviewer_ref": f"agent:historical-reviewer-{label}",
            "result": "pass",
            "reviewed_at": "2026-09-07T00:00:00Z",
            "findings": [],
            "evidence_ref": evidence,
        }
        (fixture.repo / receipt_path).parent.mkdir(parents=True, exist_ok=True)
        (fixture.repo / receipt_path).write_text(
            json.dumps(receipt) + "\n", encoding="utf-8"
        )
        git(fixture.repo, "add", ".")
        git(fixture.repo, "commit", "-m", "accept historical review")
        git(fixture.repo, "push", "origin", "main")
        code, ensured = fixture.run(
            "ensure", "--package", package, "--task-ref", writer, "--execute"
        )
        self.assertEqual(code, 0, ensured)
        cleanup = Path(ensured["path"])
        git(cleanup, "push", "origin", f"HEAD:refs/heads/{cleanup_branch}")
        args = dict(
            cleanup_package=package,
            task_ref=writer,
            path=str(target),
            branch=branch,
            expected_head=head,
            owner_authorization_ref=owner,
            execute=True,
        )
        return fixture, target, cleanup, args, before

    def invoke(self, fixture, cleanup, args, **overrides):
        values = {**args, **overrides}
        with contextlib.chdir(cleanup):
            return LIFECYCLE.command_retire_historical(
                LIFECYCLE._repo_context(fixture.repo), SimpleNamespace(**values)
            )

    def test_historical_cli_preserves_refs_stash_and_control_registry_fields(self):
        fixture, target, cleanup, args, before = self.setup_historical("happy")
        git(fixture.repo, "tag", "historical-recovery", args["expected_head"])
        (fixture.repo / "sample.txt").write_text("retained stash\n", encoding="utf-8")
        git(fixture.repo, "stash", "push", "-m", "historical preservation")
        refs = git(fixture.repo, "for-each-ref", "--format=%(refname) %(objectname)")
        before_registry = LIFECYCLE._load_registry(fixture.registry_path)
        transitions = copy.deepcopy(before_registry.get("control_custody_transitions", []))
        lease_clock = before_registry.get("control_lease_clock")
        command = ["retire-historical"]
        for key, value in args.items():
            command.append("--" + key.replace("_", "-"))
            if key != "execute":
                command.append(value)
        code, result = fixture.run(*command, cwd=cleanup)
        self.assertEqual(code, 0, result)
        self.assertEqual(result["status"], "retired_historical")
        self.assertFalse(target.exists())
        self.assertNotIn(str(target), git(fixture.repo, "worktree", "list", "--porcelain"))
        self.assertEqual(
            refs, git(fixture.repo, "for-each-ref", "--format=%(refname) %(objectname)")
        )
        registry = LIFECYCLE._load_registry(fixture.registry_path)
        record = next(item for item in registry["worktrees"] if item["path"] == str(target))
        for key, value in before.items():
            if key != "updated_at":
                self.assertEqual(record[key], "retired" if key == "state" else value)
        self.assertIsNone(registry["pending"])
        self.assertEqual(record["historical_retirement"]["before_record"], before)
        self.assertEqual(registry.get("control_custody_transitions", []), transitions)
        self.assertEqual(registry.get("control_lease_clock"), lease_clock)

    def test_historical_refuses_inexact_request_and_original_record_drift(self):
        fixture, target, cleanup, args, before = self.setup_historical("identity")
        original = fixture.registry_path.read_bytes()
        for override in (
            {"execute": False},
            {"task_ref": "agent:other-writer"},
            {"owner_authorization_ref": "session:other-owner"},
            {"expected_head": "a" * 40},
            {"path": str(fixture.repo)},
            {"branch": "work/2026-09-07-other"},
        ):
            with self.subTest(override=override), self.assertRaises(LIFECYCLE.Refusal):
                self.invoke(fixture, cleanup, args, **override)
            self.assertTrue(target.exists())
            self.assertEqual(fixture.registry_path.read_bytes(), original)
        for key, value in (
            ("kind", "durable"),
            ("task_ref", "agent:original"),
            ("package", fixture.package),
            ("lease", {}),
            ("extra", "changed"),
        ):
            registry = json.loads(original)
            record = next(item for item in registry["worktrees"] if item["path"] == str(target))
            record[key] = value
            fixture.registry_path.write_text(json.dumps(registry), encoding="utf-8")
            changed = fixture.registry_path.read_bytes()
            with self.subTest(key=key), self.assertRaises(LIFECYCLE.Refusal):
                self.invoke(fixture, cleanup, args)
            self.assertTrue(target.exists())
            self.assertEqual(fixture.registry_path.read_bytes(), changed)
        fixture.registry_path.write_bytes(original)

    def test_historical_refuses_residue_nested_repository_detached_and_reparse(self):
        fixture, target, cleanup, args, before = self.setup_historical("residue")
        original = fixture.registry_path.read_bytes()
        source = (target / "sample.txt").read_bytes()
        for relative in ("sample.txt", "untracked.txt", "ignored.cache"):
            (target / relative).write_text("do not remove\n", encoding="utf-8")
            with self.subTest(path=relative), self.assertRaises(LIFECYCLE.Refusal):
                self.invoke(fixture, cleanup, args)
            if relative == "sample.txt":
                (target / relative).write_bytes(source)
            else:
                (target / relative).unlink()
            self.assertEqual(fixture.registry_path.read_bytes(), original)
        nested = target / "nested"
        nested.mkdir()
        git(nested, "init")
        with self.assertRaises(LIFECYCLE.Refusal):
            self.invoke(fixture, cleanup, args)
        git(target, "checkout", "--detach", args["expected_head"])
        with self.assertRaises(LIFECYCLE.Refusal):
            self.invoke(fixture, cleanup, args)
        with patch.object(
            LIFECYCLE,
            "_has_reparse_component",
            side_effect=lambda value, **_: str(value).casefold()
            == str(target).casefold(),
        ):
            with self.assertRaisesRegex(LIFECYCLE.Refusal, "protected path"):
                self.invoke(fixture, cleanup, args)
        self.assertTrue(target.exists())
        self.assertEqual(fixture.registry_path.read_bytes(), original)

    def test_historical_refuses_protected_claim_and_server_race(self):
        fixture, target, cleanup, args, before = self.setup_historical("race")
        original = fixture.registry_path.read_bytes()
        for state in ("active", "paused", "superseded"):
            with patch.object(
                LIFECYCLE,
                "_strict_live_claims",
                return_value=[{"branch": args["branch"], "state": state}],
            ), self.assertRaises(LIFECYCLE.Refusal):
                self.invoke(fixture, cleanup, args)
        with patch.object(
            LIFECYCLE, "_remote_branch_tuple", return_value={}
        ), self.assertRaises(LIFECYCLE.Refusal):
            self.invoke(fixture, cleanup, args)
        self.assertEqual(fixture.registry_path.read_bytes(), original)
        self.assertTrue(target.exists())

    def test_historical_refuses_disjoint_live_worktree_on_same_branch(self):
        fixture, target, cleanup, args, before = self.setup_historical("same-branch")
        duplicate = fixture.base / "disjoint-same-branch"
        git(
            fixture.repo,
            "worktree",
            "add",
            "--force",
            str(duplicate),
            args["branch"],
        )
        original = fixture.registry_path.read_bytes()
        with self.assertRaisesRegex(LIFECYCLE.Refusal, "live worktree identity"):
            self.invoke(fixture, cleanup, args)
        self.assertTrue(target.exists())
        self.assertTrue(duplicate.exists())
        self.assertEqual(fixture.registry_path.read_bytes(), original)

    def test_historical_refuses_local_ref_and_remote_tip_drift(self):
        fixture, target, cleanup, args, before = self.setup_historical("refs")
        cleanup_head = git(cleanup, "rev-parse", "HEAD")
        git(fixture.repo, "update-ref", f"refs/heads/{args['branch']}", cleanup_head)
        with self.assertRaisesRegex(LIFECYCLE.Refusal, "local branch"):
            self.invoke(fixture, cleanup, args)
        git(fixture.repo, "update-ref", f"refs/heads/{args['branch']}", args["expected_head"])
        git(fixture.repo, "push", "--force", "origin", f"{cleanup_head}:refs/heads/{args['branch']}")
        with self.assertRaisesRegex(LIFECYCLE.Refusal, "server branch moved"):
            self.invoke(fixture, cleanup, args)
        self.assertTrue(target.exists())

    def test_historical_refuses_missing_or_changed_cleanup_receipt(self):
        receipt_relative = (
            "docs/governance/lane_claims/receipts/"
            "PS-HISTORICAL-CLEANUP-TEST-001.json"
        )
        for label, remove, expected in (
            ("receipt-missing", True, "not an ordinary reviewed Git blob"),
            ("receipt-changed", False, "changed since accepted review"),
        ):
            with self.subTest(case=label):
                fixture, target, cleanup, args, before = self.setup_historical(label)
                receipt = cleanup / receipt_relative
                if remove:
                    git(cleanup, "rm", receipt_relative)
                else:
                    receipt.write_text(
                        receipt.read_text(encoding="utf-8") + "\n",
                        encoding="utf-8",
                    )
                    git(cleanup, "add", receipt_relative)
                git(cleanup, "commit", "-m", label)
                cleanup_branch = git(cleanup, "branch", "--show-current")
                git(cleanup, "push", "--force", "origin", f"HEAD:refs/heads/{cleanup_branch}")
                original = fixture.registry_path.read_bytes()
                with self.assertRaisesRegex(LIFECYCLE.Refusal, expected):
                    self.invoke(fixture, cleanup, args)
                self.assertTrue(target.exists())
                self.assertEqual(fixture.registry_path.read_bytes(), original)

    def test_historical_refuses_unreviewed_manifest_mechanism_claim_and_evidence(self):
        for label, relative, expected in (
            (
                "manifest",
                "docs/governance/worktree_retirement_allowlists/PS-HISTORICAL-CLEANUP-TEST-001.json",
                "allowlist changed",
            ),
            ("claim", "docs/governance/lane_claims/PS-HISTORICAL-CLEANUP-TEST-001.json", "claim changed"),
            (
                "evidence",
                "docs/governance/lane_claims/evidence/PS-HISTORICAL-CLEANUP-TEST-001.md",
                "evidence changed",
            ),
            ("mechanism", "scripts/worktree_lifecycle.py", "surface is not exact"),
        ):
            with self.subTest(surface=label):
                fixture, target, cleanup, args, before = self.setup_historical(label)
                path = fixture.repo / relative
                path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
                git(fixture.repo, "add", ".")
                git(fixture.repo, "commit", "-m", f"unreviewed {label} change")
                git(fixture.repo, "push", "origin", "main")
                original = fixture.registry_path.read_bytes()
                with self.assertRaisesRegex(LIFECYCLE.Refusal, expected):
                    self.invoke(fixture, cleanup, args)
                self.assertTrue(target.exists())
                self.assertEqual(fixture.registry_path.read_bytes(), original)

    def test_historical_rejects_duplicate_json_keys_and_target_custody(self):
        with self.assertRaisesRegex(LIFECYCLE.Refusal, "duplicate JSON keys"):
            json.loads('{"targets": [], "targets": []}', object_pairs_hook=LIFECYCLE._historical_json_pairs)
        fixture, target, cleanup, args, before = self.setup_historical("duplicates")
        manifest_path = fixture.repo / (
            "docs/governance/worktree_retirement_allowlists/"
            f"{args['cleanup_package']}.json"
        )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["targets"].append(copy.deepcopy(manifest["targets"][0]))
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        git(fixture.repo, "add", ".")
        git(fixture.repo, "commit", "-m", "duplicate reviewed target")
        git(fixture.repo, "push", "origin", "main")
        with patch.object(
            LIFECYCLE,
            "_historical_reviewed_blob",
            side_effect=lambda context, refs, path, label: LIFECYCLE._git_blob_sha(
                context, "origin/main", path
            ),
        ), self.assertRaisesRegex(LIFECYCLE.Refusal, "duplicates path or branch"):
            self.invoke(fixture, cleanup, args)
        self.assertTrue(target.exists())

    def test_historical_present_recovery_reproves_and_never_retries_removal(self):
        fixture, target, cleanup, args, before = self.setup_historical("present")
        with patch.object(
            LIFECYCLE,
            "_ordinary_worktree_remove",
            side_effect=RuntimeError("interrupted"),
        ), self.assertRaises(RuntimeError):
            self.invoke(fixture, cleanup, args)
        pending = fixture.registry_path.read_bytes()
        (target / "ignored.cache").write_text("retain\n", encoding="utf-8")
        with self.assertRaises(LIFECYCLE.Refusal):
            self.invoke(fixture, cleanup, args)
        self.assertEqual(fixture.registry_path.read_bytes(), pending)
        (target / "ignored.cache").unlink()
        with patch.object(LIFECYCLE, "_ordinary_worktree_remove") as remove:
            result = self.invoke(fixture, cleanup, args)
            remove.assert_not_called()
        self.assertEqual(result["status"], "preserved_after_interruption")
        self.assertTrue(target.exists())
        self.assertIsNone(LIFECYCLE._load_registry(fixture.registry_path)["pending"])

    def test_historical_absent_recovery_preserves_proof_after_main_movement(self):
        fixture, target, cleanup, args, before = self.setup_historical("absent")
        remove = LIFECYCLE._ordinary_worktree_remove

        def interrupted(context, path):
            remove(context, path)
            raise RuntimeError("interrupted after remove")

        with patch.object(
            LIFECYCLE, "_ordinary_worktree_remove", side_effect=interrupted
        ), self.assertRaises(RuntimeError):
            self.invoke(fixture, cleanup, args)
        proof = LIFECYCLE._load_registry(fixture.registry_path)["pending"]["after_record"][
            "historical_retirement"
        ]
        (fixture.repo / "unrelated.txt").write_text(
            "disjoint main movement\n", encoding="utf-8"
        )
        git(fixture.repo, "add", ".")
        git(fixture.repo, "commit", "-m", "unrelated main movement")
        git(fixture.repo, "push", "origin", "main")
        result = self.invoke(fixture, cleanup, args)
        self.assertEqual(result["status"], "retired_historical_recovered")
        self.assertEqual(result["custody_proof"], proof)
        self.assertFalse(target.exists())

    def test_historical_journal_poison_and_other_caller_cannot_publish_custody(self):
        fixture, target, cleanup, args, before = self.setup_historical("poison")
        with patch.object(
            LIFECYCLE,
            "_ordinary_worktree_remove",
            side_effect=RuntimeError("interrupted"),
        ), self.assertRaises(RuntimeError):
            self.invoke(fixture, cleanup, args)
        original = fixture.registry_path.read_bytes()
        registry = LIFECYCLE._load_registry(fixture.registry_path)
        with self.assertRaisesRegex(LIFECYCLE.Refusal, "resume the exact"):
            LIFECYCLE._reconcile_pending(LIFECYCLE._repo_context(fixture.repo), registry)
        with self.assertRaises(LIFECYCLE.Refusal):
            self.invoke(fixture, cleanup, args, task_ref="agent:different-writer")
        for field, value in (
            ("path", str(fixture.repo)),
            ("started_at", "2026-09-07T00:00:00Z"),
        ):
            poisoned = json.loads(original)
            poisoned["pending"][field] = value
            fixture.registry_path.write_text(json.dumps(poisoned), encoding="utf-8")
            with self.assertRaises(LIFECYCLE.Refusal):
                LIFECYCLE._load_registry(fixture.registry_path)
        fixture.registry_path.write_bytes(original)
        self.assertTrue(target.exists())


class WorktreeLifecycleTests(unittest.TestCase):
    def fixture(self) -> RepositoryFixture:
        fixture = RepositoryFixture()
        self.addCleanup(fixture.cleanup)
        return fixture

    def publish_superseded_claim(
        self, fixture: RepositoryFixture, *, replacement_state: str = "closed"
    ) -> str:
        replacement = "PS-TEST-LIFECYCLE-REPLACEMENT-001"
        fixture.write_claim("superseded")
        claim_path = (
            fixture.repo
            / "docs"
            / "governance"
            / "lane_claims"
            / f"{fixture.package}.json"
        )
        claim = json.loads(claim_path.read_text(encoding="utf-8"))
        claim["superseded_at"] = "2026-09-07T00:00:00Z"
        claim["supersession"] = {
            "owner_authorization_ref": "session:owner/superseded-retirement",
            "superseded_by": [replacement],
        }
        claim_path.write_text(json.dumps(claim, indent=2) + "\n", encoding="utf-8")
        replacement_path = claim_path.with_name(f"{replacement}.json")
        replacement_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "package": replacement,
                    "state": replacement_state,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        git(
            fixture.repo,
            "add",
            claim_path.relative_to(fixture.repo).as_posix(),
            replacement_path.relative_to(fixture.repo).as_posix(),
        )
        git(fixture.repo, "commit", "-m", "supersede test claim")
        git(fixture.repo, "push", "origin", "main")
        return replacement

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

    def consumed_reassignment_for_transfer(self, label: str):
        fixture, receiver, successor, owner_ref, source_path, control_path = (
            self.owner_reassignment_setup(label)
        )
        code, prepared = self.run_owner_reassignment_prepare(
            fixture, receiver, successor, owner_ref, control_path
        )
        self.assertEqual(code, 0, prepared)
        claim_path = (
            fixture.repo / "docs" / "governance" / "lane_claims"
            / f"{fixture.package}.json"
        )
        claim = json.loads(claim_path.read_text(encoding="utf-8"))
        claim.update({
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
        })
        claim_path.write_text(json.dumps(claim, indent=2) + "\n", encoding="utf-8")
        git(fixture.repo, "add", str(claim_path.relative_to(fixture.repo)))
        git(fixture.repo, "commit", "-m", "accept original owner reassignment")
        git(fixture.repo, "push", "origin", "main")
        code, created = fixture.run(
            "ensure", "--package", fixture.package, "--task-ref", receiver,
            "--execute",
        )
        self.assertEqual(code, 0, created)
        return fixture, receiver, successor, source_path, Path(created["path"]), claim_path, prepared

    def accept_voluntary_transfer(self, fixture, claim_path, from_ref, to_ref, checkpoint):
        claim = json.loads(claim_path.read_text(encoding="utf-8"))
        claim["writer_ref"] = to_ref
        claim["handoff"] = {
            "from_ref": from_ref,
            "to_ref": to_ref,
            "checkpoint_sha": checkpoint,
            "relinquished": True,
        }
        claim_path.write_text(json.dumps(claim, indent=2) + "\n", encoding="utf-8")
        git(fixture.repo, "add", str(claim_path.relative_to(fixture.repo)))
        git(fixture.repo, "commit", "-m", "accept voluntary transfer")
        git(fixture.repo, "push", "origin", "main")
        return git(fixture.repo, "rev-parse", "HEAD")

    def closed_custody_setup(
        self, label: str, *, advance_target: bool = False, completion: bool = False
    ) -> tuple[RepositoryFixture, Path, Path, dict[str, str]]:
        fixture = self.fixture()
        (fixture.repo / "scripts" / "worktree_lifecycle.py").write_bytes(
            SCRIPT.read_bytes()
        )
        (fixture.repo / "docs" / "governance" / "WORKTREE_LIFECYCLE.md").write_text(
            "reviewed lifecycle contract\n", encoding="utf-8"
        )
        (fixture.repo / "tests" / "test_worktree_lifecycle.py").write_text(
            "reviewed lifecycle tests\n", encoding="utf-8"
        )
        if completion:
            for relative in ("scripts/delivery_preflight.py", "tests/test_delivery_preflight.py"):
                (fixture.repo / relative).write_bytes((ROOT / relative).read_bytes())
                git(fixture.repo, "add", relative)
        git(
            fixture.repo,
            "add",
            "scripts/worktree_lifecycle.py",
            "docs/governance/WORKTREE_LIFECYCLE.md",
            "tests/test_worktree_lifecycle.py",
        )
        git(fixture.repo, "commit", "-m", "install reviewed lifecycle candidate")
        git(fixture.repo, "push", "origin", "main")
        fixture.main_sha = git(fixture.repo, "rev-parse", "HEAD")
        fixture.initialize()
        code, target = fixture.run(
            "ensure",
            "--package",
            fixture.package,
            "--task-ref",
            fixture.writer,
            "--execute",
        )
        self.assertEqual(code, 0, target)
        target_path = Path(target["path"])
        git(
            target_path,
            "push",
            "-u",
            "origin",
            f"HEAD:refs/heads/{fixture.branch}",
        )
        target_head = fixture.main_sha
        if advance_target:
            (target_path / "sample.txt").write_text(
                f"closed custody {label}\n", encoding="utf-8"
            )
            git(target_path, "add", "sample.txt")
            git(target_path, "commit", "-m", f"advance closed custody {label}")
            target_head = git(target_path, "rev-parse", "HEAD")
            git(target_path, "push", "origin", f"HEAD:refs/heads/{fixture.branch}")

        cleanup_package = "PS-CLOSED-CUSTODY-CLEANUP-001"
        cleanup_task = f"agent:closed-custody-cleanup-{label}"
        cleanup_branch = f"work/2026-09-04-closed-custody-cleanup-{label}"
        owner_ref = f"session:owner/closed-custody-{label}"
        unavailable_ref = f"session:source-unavailable/closed-custody-{label}"
        evidence = (
            "docs/governance/lane_claims/evidence/"
            f"{cleanup_package}.md"
        )
        cleanup_claim = {
            "schema_version": 1,
            "package": cleanup_package,
            "state": "active",
            "outcome": "test closed custody",
            "assignment": "implementation",
            "writer_ref": cleanup_task,
            "branch": cleanup_branch,
            "delivery_path": "Protected",
            "repository_authority": "through_merge",
            "production_authority": "withheld",
            "owner_outcome_ref": owner_ref,
            "surfaces": [
                f"docs/governance/lane_claims/{cleanup_package}.json",
                evidence,
                (
                    "docs/governance/lane_claims/receipts/"
                    f"{cleanup_package}.json"
                ),
                *sorted(LIFECYCLE.CLOSED_CUSTODY_REQUIRED_SURFACES),
            ],
            "evidence_surfaces": [evidence],
            "domains": sorted(LIFECYCLE.CLOSED_CUSTODY_REQUIRED_DOMAINS),
            "review_requirement": "independent",
        }
        claim_path = (
            fixture.repo
            / "docs"
            / "governance"
            / "lane_claims"
            / f"{cleanup_package}.json"
        )
        claim_path.write_text(
            json.dumps(cleanup_claim, indent=2) + "\n", encoding="utf-8"
        )
        evidence_path = fixture.repo / evidence
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        evidence_path.write_text("accepted review evidence\n", encoding="utf-8")
        receipt_path = (
            fixture.repo
            / "docs"
            / "governance"
            / "lane_claims"
            / "receipts"
            / f"{cleanup_package}.json"
        )
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "package": cleanup_package,
                    "candidate_sha": fixture.main_sha,
                    "review_type": "independent",
                    "reviewer_ref": f"agent:closed-custody-reviewer-{label}",
                    "result": "pass",
                    "reviewed_at": "2026-09-04T00:00:00Z",
                    "findings": [
                        {
                            "status": "informational",
                            "summary": "fixture candidate accepted",
                        }
                    ],
                    "evidence_ref": evidence,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        git(
            fixture.repo,
            "add",
            str(claim_path.relative_to(fixture.repo)),
            str(evidence_path.relative_to(fixture.repo)),
            str(receipt_path.relative_to(fixture.repo)),
        )
        git(fixture.repo, "commit", "-m", "activate reviewed cleanup claim")
        git(fixture.repo, "push", "origin", "main")
        code, controlled = fixture.run(
            "control",
            "--package",
            cleanup_package,
            "--task-ref",
            cleanup_task,
            "--branch",
            f"work/2026-09-04-delivery-activation-{label}",
            "--base",
            "origin/main",
            "--execute",
        )
        self.assertEqual(code, 0, controlled)
        code, released = fixture.run(
            "control",
            "--task-ref",
            cleanup_task,
            "--release",
            "--execute",
        )
        self.assertEqual(code, 0, released)
        code, cleanup = fixture.run(
            "ensure",
            "--package",
            cleanup_package,
            "--task-ref",
            cleanup_task,
            "--execute",
        )
        self.assertEqual(code, 0, cleanup)
        cleanup_path = Path(cleanup["path"])
        git(
            cleanup_path,
            "push",
            "-u",
            "origin",
            f"HEAD:refs/heads/{cleanup_branch}",
        )
        fixture.close_claim()
        facts = {
            "cleanup_package": cleanup_package,
            "cleanup_task": cleanup_task,
            "cleanup_branch": cleanup_branch,
            "owner_ref": owner_ref,
            "unavailable_ref": unavailable_ref,
            "target_head": target_head,
        }
        return fixture, target_path, cleanup_path, facts

    def run_closed_custody(
        self,
        fixture: RepositoryFixture,
        target_path: Path,
        cleanup_path: Path,
        facts: dict[str, str],
        **overrides: str,
    ) -> tuple[int, dict]:
        values = {
            "cleanup_package": facts["cleanup_package"],
            "task_ref": facts["cleanup_task"],
            "target_package": fixture.package,
            "path": str(target_path),
            "branch": fixture.branch,
            "source_task_ref": fixture.writer,
            "expected_head": facts["target_head"],
            "owner_authorization_ref": facts["owner_ref"],
            "source_unavailable_ref": facts["unavailable_ref"],
        }
        values.update(overrides)
        return fixture.run(
            "retire-closed-custody",
            "--cleanup-package",
            values["cleanup_package"],
            "--task-ref",
            values["task_ref"],
            "--target-package",
            values["target_package"],
            "--path",
            values["path"],
            "--branch",
            values["branch"],
            "--source-task-ref",
            values["source_task_ref"],
            "--expected-head",
            values["expected_head"],
            "--owner-authorization-ref",
            values["owner_authorization_ref"],
            "--source-unavailable-ref",
            values["source_unavailable_ref"],
            "--execute",
            cwd=cleanup_path,
        )

    def begin_closed_custody_crash_before_remove(
        self,
        fixture: RepositoryFixture,
        target_path: Path,
        cleanup_path: Path,
        facts: dict[str, str],
    ) -> tuple[object, SimpleNamespace]:
        arguments = SimpleNamespace(
            cleanup_package=facts["cleanup_package"],
            task_ref=facts["cleanup_task"],
            target_package=fixture.package,
            path=str(target_path),
            branch=fixture.branch,
            source_task_ref=fixture.writer,
            expected_head=facts["target_head"],
            owner_authorization_ref=facts["owner_ref"],
            source_unavailable_ref=facts["unavailable_ref"],
            execute=True,
        )
        context = LIFECYCLE._repo_context(fixture.repo)
        previous_cwd = Path.cwd()
        try:
            os.chdir(cleanup_path)
            with patch.object(
                LIFECYCLE,
                "_ordinary_worktree_remove",
                side_effect=LIFECYCLE.Refusal("simulated crash before remove"),
            ):
                with self.assertRaises(LIFECYCLE.Refusal):
                    LIFECYCLE.command_retire_closed_custody(context, arguments)
        finally:
            os.chdir(previous_cwd)
        registry = json.loads(fixture.registry_path.read_text(encoding="utf-8"))
        self.assertEqual(
            registry["pending"]["operation"], "retire_closed_custody"
        )
        return context, arguments

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

    def test_strict_live_claims_treats_superseded_as_terminal(self):
        fixture = self.fixture()
        fixture.write_claim("superseded")
        git(
            fixture.repo,
            "add",
            f"docs/governance/lane_claims/{fixture.package}.json",
        )
        git(fixture.repo, "commit", "-m", "supersede test package")
        git(fixture.repo, "push", "origin", "main")
        context = LIFECYCLE._repo_context(fixture.repo)
        LIFECYCLE._fetch_origin_main(context)
        self.assertEqual(LIFECYCLE._strict_live_claims(context), [])

        fixture.write_claim("withdrawn")
        git(
            fixture.repo,
            "add",
            f"docs/governance/lane_claims/{fixture.package}.json",
        )
        git(fixture.repo, "commit", "-m", "invalid terminal state")
        git(fixture.repo, "push", "origin", "main")
        LIFECYCLE._fetch_origin_main(context)
        with self.assertRaisesRegex(LIFECYCLE.Refusal, "invalid state"):
            LIFECYCLE._strict_live_claims(context)

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

    def test_runtime_verification_propagates_context_in_both_workspace_modes(self):
        fixture = self.fixture()
        git(fixture.repo, "push", "origin", f"main:refs/heads/{fixture.branch}")
        fixture.initialize()
        context_id = "a" * 32
        receiver = "agent:external-verifier"
        repository_context = LIFECYCLE._repo_context(fixture.repo)
        registry = json.loads(fixture.registry_path.read_text(encoding="utf-8"))
        registry.setdefault("caller_contexts", []).append(
            {
                "id": context_id,
                "state": "active",
                "repository_common_dir": str(repository_context.common_dir),
                "receiver_ref": receiver,
                "package": fixture.package,
                "registered_by": "task:context-registrar",
                "owner_authorization_ref": "session:owner/runtime-context",
                "registered_at": "2026-09-12T00:00:00Z",
                "revoked_at": None,
                "revoked_by": None,
                "revocation_authorization_ref": None,
            }
        )
        fixture.registry_path.write_text(
            json.dumps(registry, indent=2) + "\n", encoding="utf-8"
        )
        environment = {
            "PEERSLATE_CALLER_REF": "",
            "CODEX_THREAD_ID": "",
            LIFECYCLE.CALLER_CONTEXT_ENV: "",
        }
        for mode in ("control", "ephemeral"):
            with self.subTest(mode=mode):
                observed = fixture.base / f"{mode}-verification-context.txt"
                script = (
                    "import os; from pathlib import Path; "
                    f"Path({str(observed)!r}).write_text("
                    "os.environ.get('PEERSLATE_CALLER_CONTEXT','') + '|' + "
                    "os.environ.get('PEERSLATE_CALLER_REF',''), encoding='utf-8')"
                )
                arguments = [
                    "verify",
                    "--package",
                    fixture.package,
                    "--candidate-sha",
                    fixture.main_sha,
                    "--task-ref",
                    receiver,
                    "--caller-context",
                    context_id,
                    "--runtime-required",
                ]
                if mode == "ephemeral":
                    arguments.append("--ephemeral")
                arguments.extend(["--", sys.executable, "-B", "-c", script])
                with patch.dict(os.environ, environment):
                    code, payload = fixture.run(*arguments)
                self.assertEqual(code, 0, payload)
                self.assertEqual(
                    observed.read_text(encoding="utf-8"), context_id + "|"
                )

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

    def test_operations_only_close_binds_real_retirement_and_squashed_evidence(self):
        from scripts import delivery_preflight as preflight

        fixture, target, cleanup, facts = self.closed_custody_setup(
            "operations-completion", advance_target=True, completion=True,
        )
        code, result = self.run_closed_custody(fixture, target, cleanup, facts)
        self.assertEqual(0, code, result)
        registry_before = fixture.registry_path.read_bytes()
        records = json.loads(registry_before)["worktrees"]
        proofs = [r["closed_custody_retirement"] for r in records
                  if r.get("closed_custody_retirement")]
        package = facts["cleanup_package"]
        evidence = preflight.evidence_relative_path(package)
        receipt_path = preflight.receipt_relative_path(package)
        git(cleanup, "merge", "origin/main", "--no-edit")
        (cleanup / evidence).write_text(
            "# Completed fixture retirement\n```peerslate-closed-custody-completion\n"
            + json.dumps({"schema_version": 1, "package": package, "retirements": proofs})
            + "\n```\n", encoding="utf-8",
        )
        git(cleanup, "add", evidence)
        git(cleanup, "commit", "-m", "freeze operations-only evidence")
        candidate = git(cleanup, "rev-parse", "HEAD")
        review = json.loads((cleanup / receipt_path).read_text(encoding="utf-8"))
        review["candidate_sha"] = candidate
        review["reviewer_ref"] = "agent:independent-completion-reviewer"
        (cleanup / receipt_path).write_text(json.dumps(review) + "\n", encoding="utf-8")
        git(cleanup, "add", receipt_path)
        git(cleanup, "commit", "-m", "record independent completion review")
        remote_tip = git(cleanup, "rev-parse", "HEAD")
        git(cleanup, "push", "origin", facts["cleanup_branch"])
        git(fixture.repo, "merge", "--squash", facts["cleanup_branch"])
        git(fixture.repo, "commit", "-m", "accept reviewed operations completion")
        merged = git(fixture.repo, "rev-parse", "HEAD")
        git(fixture.repo, "push", "origin", "main")
        git(cleanup, "fetch", "origin", "main")
        claim = json.loads((cleanup / preflight.claim_relative_path(package)).read_text())
        merged_paths = preflight._diff_paths(cleanup, f"{merged}^..{merged}")
        with patch.object(preflight, "_is_ci_environment", return_value=False):
            errors = preflight._operations_only_close_errors(
                cleanup, claim, review, candidate, merged, remote_tip, merged_paths,
            )
        self.assertEqual([], errors)
        self.assertEqual(registry_before, fixture.registry_path.read_bytes())
        self.assertFalse(target.exists())
        self.assertEqual(facts["target_head"], git(
            fixture.repo, "rev-parse", f"refs/remotes/origin/{fixture.branch}"))

        # An evidence-only post-review edit must fail this exception even
        # though ordinary code receipts permit a runtime-inert evidence tail.
        with (cleanup / evidence).open("a", encoding="utf-8") as handle:
            handle.write("Unreviewed completion alteration\n")
        git(cleanup, "add", evidence)
        git(cleanup, "commit", "-m", "alter evidence after review")
        changed_tip = git(cleanup, "rev-parse", "HEAD")
        git(cleanup, "push", "origin", facts["cleanup_branch"])
        with patch.object(preflight, "_is_ci_environment", return_value=False):
            errors = preflight._operations_only_close_errors(
                cleanup, claim, review, candidate, merged, changed_tip, merged_paths,
            )
        self.assertTrue(any("completion bytes changed" in e for e in errors), errors)
        self.assertEqual(registry_before, fixture.registry_path.read_bytes())

    def test_closed_custody_retires_exact_and_stale_ancestor_without_deleting_refs(self):
        for label, advance_target in (("exact", False), ("ancestor", True)):
            with self.subTest(label=label):
                fixture, target_path, cleanup_path, facts = self.closed_custody_setup(
                    label, advance_target=advance_target
                )
                git(fixture.repo, "tag", f"closed-custody-{label}", facts["target_head"])
                code, retired = self.run_closed_custody(
                    fixture, target_path, cleanup_path, facts
                )
                self.assertEqual(code, 0, retired)
                self.assertEqual(retired["status"], "retired_closed_custody")
                self.assertFalse(target_path.exists())
                self.assertEqual(
                    git(fixture.repo, "rev-parse", f"refs/heads/{fixture.branch}"),
                    facts["target_head"],
                )
                self.assertEqual(
                    git(fixture.repo, "rev-parse", f"refs/tags/closed-custody-{label}"),
                    facts["target_head"],
                )
                self.assertIn(
                    facts["target_head"],
                    git(
                        fixture.repo,
                        "ls-remote",
                        "--heads",
                        "origin",
                        f"refs/heads/{fixture.branch}",
                    ),
                )
                registry = json.loads(
                    fixture.registry_path.read_text(encoding="utf-8")
                )
                record = next(
                    item
                    for item in registry["worktrees"]
                    if item.get("package") == fixture.package
                )
                proof = record["closed_custody_retirement"]
                self.assertEqual(record["state"], "retired")
                self.assertEqual(record["task_ref"], fixture.writer)
                self.assertEqual(proof["source_task_ref"], fixture.writer)
                self.assertEqual(proof["cleanup_task_ref"], facts["cleanup_task"])
                self.assertEqual(
                    proof["registry_previous_head"], fixture.main_sha
                )
                self.assertEqual(proof["expected_head"], facts["target_head"])
                self.assertIsNone(registry["pending"])

    def test_closed_custody_refuses_authority_identity_lease_duplicate_and_pending(self):
        fixture, target_path, cleanup_path, facts = self.closed_custody_setup(
            "authority"
        )
        receipt_path = (
            fixture.repo
            / "docs"
            / "governance"
            / "lane_claims"
            / "receipts"
            / f"{facts['cleanup_package']}.json"
        )
        receipt_bytes = receipt_path.read_bytes()
        git(fixture.repo, "rm", str(receipt_path.relative_to(fixture.repo)))
        git(fixture.repo, "commit", "-m", "simulate pre-review main")
        git(fixture.repo, "push", "origin", "main")
        code, pre_review = self.run_closed_custody(
            fixture, target_path, cleanup_path, facts
        )
        self.assertEqual(code, 2, pre_review)
        self.assertIn("receipt is absent", pre_review["error"])
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_bytes(receipt_bytes)
        git(fixture.repo, "add", str(receipt_path.relative_to(fixture.repo)))
        git(fixture.repo, "commit", "-m", "restore accepted review receipt")
        git(fixture.repo, "push", "origin", "main")

        lifecycle_path = fixture.repo / "scripts" / "worktree_lifecycle.py"
        lifecycle_path.write_text("print('pre-merge')\n", encoding="utf-8")
        git(fixture.repo, "add", str(lifecycle_path.relative_to(fixture.repo)))
        git(fixture.repo, "commit", "-m", "simulate unmerged lifecycle script")
        git(fixture.repo, "push", "origin", "main")
        code, pre_merge = self.run_closed_custody(
            fixture, target_path, cleanup_path, facts
        )
        self.assertEqual(code, 2, pre_merge)
        self.assertIn("surface is not exact", pre_merge["error"])
        lifecycle_path.write_bytes(SCRIPT.read_bytes())
        git(fixture.repo, "add", str(lifecycle_path.relative_to(fixture.repo)))
        git(fixture.repo, "commit", "-m", "restore merged lifecycle script")
        git(fixture.repo, "push", "origin", "main")

        for field, value, expected in (
            ("source_task_ref", "agent:not-original", "target claim"),
            ("owner_authorization_ref", "session:owner/not-authorized", "cleanup claim"),
            (
                "source_unavailable_ref",
                facts["owner_ref"],
                "must be distinct",
            ),
            ("path", str(target_path) + "/..", "exact, absolute, and canonical"),
            ("branch", fixture.branch + "-wrong", "target claim"),
        ):
            with self.subTest(field=field):
                code, refused = self.run_closed_custody(
                    fixture,
                    target_path,
                    cleanup_path,
                    facts,
                    **{field: value},
                )
                self.assertEqual(code, 2, refused)
                self.assertIn(expected, refused["error"])
                self.assertTrue(target_path.exists())

        fixture.write_claim("active")
        claim_relative = f"docs/governance/lane_claims/{fixture.package}.json"
        git(fixture.repo, "add", claim_relative)
        git(fixture.repo, "commit", "-m", "temporarily reopen target claim")
        git(fixture.repo, "push", "origin", "main")
        code, active_claim = self.run_closed_custody(
            fixture, target_path, cleanup_path, facts
        )
        self.assertEqual(code, 2, active_claim)
        self.assertIn("target claim", active_claim["error"])
        fixture.close_claim()

        clean_registry = fixture.registry_path.read_bytes()
        registry = json.loads(clean_registry)
        target = next(
            item for item in registry["worktrees"] if item.get("package") == fixture.package
        )
        target["lease"] = {"kind": "forged-live-lease"}
        fixture.registry_path.write_text(
            json.dumps(registry, indent=2) + "\n", encoding="utf-8"
        )
        code, leased = self.run_closed_custody(
            fixture, target_path, cleanup_path, facts
        )
        self.assertEqual(code, 2, leased)
        self.assertIn("identity or lease", leased["error"])
        fixture.registry_path.write_bytes(clean_registry)

        registry = json.loads(clean_registry)
        target = next(
            item for item in registry["worktrees"] if item.get("package") == fixture.package
        )
        duplicate = copy.deepcopy(target)
        duplicate["path"] = str(fixture.managed / "duplicate-target")
        registry["worktrees"].append(duplicate)
        fixture.registry_path.write_text(
            json.dumps(registry, indent=2) + "\n", encoding="utf-8"
        )
        code, duplicated = self.run_closed_custody(
            fixture, target_path, cleanup_path, facts
        )
        self.assertEqual(code, 2, duplicated)
        self.assertIn("duplicated, or ambiguous", duplicated["error"])
        fixture.registry_path.write_bytes(clean_registry)

        unrelated = fixture.repo / "unrelated-registry-head.txt"
        unrelated.write_text("ahead registry custody\n", encoding="utf-8")
        git(fixture.repo, "add", unrelated.name)
        git(fixture.repo, "commit", "-m", "create unrelated registry head")
        nonancestor = git(fixture.repo, "rev-parse", "HEAD")
        for registry_head, expected in (
            (nonancestor, "neither equal to nor an ancestor"),
            ("f" * 40, "commit object is not available"),
        ):
            with self.subTest(registry_head=registry_head):
                registry = json.loads(clean_registry)
                target = next(
                    item
                    for item in registry["worktrees"]
                    if item.get("package") == fixture.package
                )
                target["head"] = registry_head
                fixture.registry_path.write_text(
                    json.dumps(registry, indent=2) + "\n", encoding="utf-8"
                )
                code, stale = self.run_closed_custody(
                    fixture, target_path, cleanup_path, facts
                )
                self.assertEqual(code, 2, stale)
                self.assertIn(expected, stale["error"])
                self.assertTrue(target_path.exists())
        fixture.registry_path.write_bytes(clean_registry)

        registry = json.loads(clean_registry)
        target = next(
            item for item in registry["worktrees"] if item.get("package") == fixture.package
        )
        registry["pending"] = {
            "operation": "retire",
            "path": target["path"],
            "record": copy.deepcopy(target),
            "started_at": "2026-09-04T00:00:00Z",
        }
        fixture.registry_path.write_text(
            json.dumps(registry, indent=2) + "\n", encoding="utf-8"
        )
        exact_pending = fixture.registry_path.read_bytes()
        code, pending = self.run_closed_custody(
            fixture, target_path, cleanup_path, facts
        )
        self.assertEqual(code, 2, pending)
        self.assertIn("unresolved lifecycle journal", pending["error"])
        self.assertEqual(fixture.registry_path.read_bytes(), exact_pending)
        self.assertTrue(target_path.exists())

    def test_closed_custody_refuses_tracked_untracked_ignored_behind_and_divergent(self):
        fixture, target_path, cleanup_path, facts = self.closed_custody_setup(
            "residue"
        )
        original = (target_path / "sample.txt").read_text(encoding="utf-8")
        residue_cases = (
            (target_path / "sample.txt", "tracked residue\n"),
            (target_path / "untracked.tmp", "untracked residue\n"),
            (target_path / "ignored.cache", "ignored residue\n"),
        )
        for residue_path, content in residue_cases:
            with self.subTest(residue=residue_path.name):
                residue_path.write_text(content, encoding="utf-8")
                code, refused = self.run_closed_custody(
                    fixture, target_path, cleanup_path, facts
                )
                self.assertEqual(code, 2, refused)
                self.assertTrue(refused["blockers"])
                if residue_path.name == "sample.txt":
                    residue_path.write_text(original, encoding="utf-8")
                else:
                    residue_path.unlink()

        remote_head = fixture.publish_claim_branch_commit(
            "server advanced closed custody", advance=True
        )
        self.assertNotEqual(remote_head, facts["target_head"])
        code, behind = self.run_closed_custody(
            fixture, target_path, cleanup_path, facts
        )
        self.assertEqual(code, 2, behind)
        self.assertIn("moved at commit boundary", behind["error"])
        self.assertTrue(target_path.exists())

        (target_path / "sample.txt").write_text(
            "local divergent closed custody\n", encoding="utf-8"
        )
        git(target_path, "add", "sample.txt")
        git(target_path, "commit", "-m", "diverge local closed custody")
        facts["target_head"] = git(target_path, "rev-parse", "HEAD")
        code, divergent = self.run_closed_custody(
            fixture, target_path, cleanup_path, facts
        )
        self.assertEqual(code, 2, divergent)
        self.assertIn("moved at commit boundary", divergent["error"])
        self.assertTrue(target_path.exists())

    def test_closed_custody_journal_recovers_before_and_after_remove(self):
        for label, remove_first, expected_recovery in (
            ("crash-before", False, "preserved"),
            ("crash-after", True, "completed"),
        ):
            with self.subTest(label=label):
                fixture, target_path, cleanup_path, facts = self.closed_custody_setup(
                    label
                )
                arguments = SimpleNamespace(
                    cleanup_package=facts["cleanup_package"],
                    task_ref=facts["cleanup_task"],
                    target_package=fixture.package,
                    path=str(target_path),
                    branch=fixture.branch,
                    source_task_ref=fixture.writer,
                    expected_head=facts["target_head"],
                    owner_authorization_ref=facts["owner_ref"],
                    source_unavailable_ref=facts["unavailable_ref"],
                    execute=True,
                )
                context = LIFECYCLE._repo_context(fixture.repo)
                original_remove = LIFECYCLE._ordinary_worktree_remove

                def simulated_crash(remove_context: object, remove_path: Path) -> None:
                    if remove_first:
                        original_remove(remove_context, remove_path)
                    raise LIFECYCLE.Refusal("simulated closed-custody crash")

                previous_cwd = Path.cwd()
                try:
                    os.chdir(cleanup_path)
                    with patch.object(
                        LIFECYCLE,
                        "_ordinary_worktree_remove",
                        side_effect=simulated_crash,
                    ):
                        with self.assertRaises(LIFECYCLE.Refusal):
                            LIFECYCLE.command_retire_closed_custody(
                                context, arguments
                            )
                finally:
                    os.chdir(previous_cwd)
                journal = json.loads(
                    fixture.registry_path.read_text(encoding="utf-8")
                )
                self.assertEqual(
                    journal["pending"]["operation"], "retire_closed_custody"
                )
                code, recovered = self.run_closed_custody(
                    fixture, target_path, cleanup_path, facts
                )
                self.assertEqual(code, 0, recovered)
                self.assertEqual(
                    recovered["recovered_pending"]["outcome"], expected_recovery
                )
                self.assertFalse(target_path.exists())
                final = json.loads(
                    fixture.registry_path.read_text(encoding="utf-8")
                )
                self.assertIsNone(final["pending"])

    def test_closed_custody_present_recovery_retains_journal_on_every_mismatch(self):
        for case in (
            "detached",
            "switched",
            "moved_head",
            "residue",
            "reparse",
            "nested",
            "replaced_path",
        ):
            with self.subTest(case=case):
                fixture, target_path, cleanup_path, facts = self.closed_custody_setup(
                    f"recovery-{case.replace('_', '-')}"
                )
                context, arguments = self.begin_closed_custody_crash_before_remove(
                    fixture, target_path, cleanup_path, facts
                )
                if case == "detached":
                    git(target_path, "switch", "--detach")
                elif case == "switched":
                    git(
                        target_path,
                        "switch",
                        "-c",
                        f"work/2026-09-04-recovery-switched-{case}",
                    )
                elif case == "moved_head":
                    (target_path / "sample.txt").write_text(
                        "moved recovery head\n", encoding="utf-8"
                    )
                    git(target_path, "add", "sample.txt")
                    git(target_path, "commit", "-m", "move recovery head")
                elif case == "residue":
                    (target_path / "ignored.cache").write_text(
                        "retained residue\n", encoding="utf-8"
                    )
                elif case == "nested":
                    nested_path = target_path / "nested-worktree"
                    git(
                        fixture.repo,
                        "worktree",
                        "add",
                        "-b",
                        "work/2026-09-04-nested-recovery-proof",
                        str(nested_path),
                        facts["target_head"],
                    )
                elif case == "replaced_path":
                    target_path.rename(
                        target_path.with_name(target_path.name + "-moved")
                    )
                    target_path.mkdir()

                exact_journal = fixture.registry_path.read_bytes()
                previous_cwd = Path.cwd()
                try:
                    os.chdir(cleanup_path)
                    if case == "reparse":
                        guard = patch.object(
                            LIFECYCLE,
                            "_has_reparse_component",
                            return_value=True,
                        )
                    elif case == "nested":
                        original_pristine = LIFECYCLE._is_pristine

                        def allow_nested_only(check_path: Path):
                            if LIFECYCLE._path_key(check_path) == LIFECYCLE._path_key(
                                target_path
                            ):
                                return True, []
                            return original_pristine(check_path)

                        guard = patch.object(
                            LIFECYCLE, "_is_pristine", side_effect=allow_nested_only
                        )
                    else:
                        guard = contextlib.nullcontext()
                    with guard:
                        with self.assertRaises(LIFECYCLE.Refusal):
                            LIFECYCLE.command_retire_closed_custody(
                                context, arguments
                            )
                finally:
                    os.chdir(previous_cwd)
                self.assertEqual(fixture.registry_path.read_bytes(), exact_journal)
                self.assertIsNotNone(
                    json.loads(exact_journal)["pending"]
                )

    def test_closed_custody_pending_binds_previous_head_and_rejects_poison(self):
        fixture, target_path, cleanup_path, facts = self.closed_custody_setup(
            "pending-head-poison"
        )
        context, arguments = self.begin_closed_custody_crash_before_remove(
            fixture, target_path, cleanup_path, facts
        )
        registry = json.loads(fixture.registry_path.read_text(encoding="utf-8"))
        cleanup = next(
            item
            for item in registry["worktrees"]
            if item.get("package") == facts["cleanup_package"]
        )
        registry["pending"]["after_record"]["closed_custody_retirement"][
            "registry_previous_head"
        ] = cleanup["head"]
        fixture.registry_path.write_text(
            json.dumps(registry, indent=2) + "\n", encoding="utf-8"
        )
        poisoned = fixture.registry_path.read_bytes()
        previous_cwd = Path.cwd()
        try:
            os.chdir(cleanup_path)
            with self.assertRaises(LIFECYCLE.Refusal):
                LIFECYCLE.command_retire_closed_custody(context, arguments)
        finally:
            os.chdir(previous_cwd)
        self.assertEqual(fixture.registry_path.read_bytes(), poisoned)
        self.assertTrue(target_path.exists())

    def test_retire_superseded_original_custody_reconciles_ancestor_head(self):
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
        (durable / "sample.txt").write_text("superseded candidate\n", encoding="utf-8")
        git(durable, "add", "sample.txt")
        git(durable, "commit", "-m", "superseded candidate")
        candidate = git(durable, "rev-parse", "HEAD")
        git(durable, "push", "-u", "origin", f"HEAD:refs/heads/{fixture.branch}")
        self.publish_superseded_claim(fixture)

        code, retired = fixture.run(
            "retire",
            "--path",
            str(durable),
            "--task-ref",
            fixture.writer,
            "--expected-head",
            candidate,
            "--execute",
        )
        self.assertEqual(code, 0, retired)
        self.assertFalse(durable.exists())
        registry = json.loads(fixture.registry_path.read_text(encoding="utf-8"))
        record = next(
            item for item in registry["worktrees"] if item.get("package") == fixture.package
        )
        self.assertEqual(record["state"], "retired")
        self.assertEqual(record["previous_head"], fixture.main_sha)
        self.assertEqual(record["head"], candidate)
        self.assertEqual(git(fixture.repo, "rev-parse", fixture.branch), candidate)
        self.assertEqual(
            git(fixture.repo, "rev-parse", f"refs/remotes/origin/{fixture.branch}"),
            candidate,
        )

    def test_retire_superseded_refuses_open_replacement_wrong_task_and_residue(self):
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
        git(durable, "push", "-u", "origin", f"HEAD:refs/heads/{fixture.branch}")
        replacement = self.publish_superseded_claim(
            fixture, replacement_state="active"
        )

        code, open_replacement = fixture.run(
            "retire",
            "--path",
            str(durable),
            "--task-ref",
            fixture.writer,
            "--expected-head",
            fixture.main_sha,
            "--execute",
        )
        self.assertEqual(code, 2, open_replacement)
        self.assertIn(replacement, open_replacement["error"])
        replacement_path = (
            fixture.repo
            / "docs"
            / "governance"
            / "lane_claims"
            / f"{replacement}.json"
        )
        replacement_claim = json.loads(replacement_path.read_text(encoding="utf-8"))
        replacement_claim["state"] = "closed"
        replacement_path.write_text(
            json.dumps(replacement_claim, indent=2) + "\n", encoding="utf-8"
        )
        git(
            fixture.repo,
            "add",
            replacement_path.relative_to(fixture.repo).as_posix(),
        )
        git(fixture.repo, "commit", "-m", "close replacement claim")
        git(fixture.repo, "push", "origin", "main")

        code, wrong_task = fixture.run(
            "retire",
            "--path",
            str(durable),
            "--task-ref",
            "task:not-original-custody",
            "--expected-head",
            fixture.main_sha,
            "--execute",
        )
        self.assertEqual(code, 2, wrong_task)
        self.assertIn("does not own", wrong_task["error"])

        (durable / "untracked.tmp").write_text("preserve\n", encoding="utf-8")
        code, residue = fixture.run(
            "retire",
            "--path",
            str(durable),
            "--task-ref",
            fixture.writer,
            "--expected-head",
            fixture.main_sha,
            "--execute",
        )
        self.assertEqual(code, 2, residue)
        self.assertTrue(any("residue" in item for item in residue["blockers"]))
        self.assertTrue(durable.exists())

    def test_retire_superseded_refuses_nonancestor_registry_head(self):
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
        (durable / "sample.txt").write_text("target history\n", encoding="utf-8")
        git(durable, "add", "sample.txt")
        git(durable, "commit", "-m", "target history")
        candidate = git(durable, "rev-parse", "HEAD")
        git(durable, "push", "-u", "origin", f"HEAD:refs/heads/{fixture.branch}")

        git(fixture.repo, "checkout", "-b", "work/unrelated-history", "origin/main")
        (fixture.repo / "unrelated.txt").write_text("unrelated\n", encoding="utf-8")
        git(fixture.repo, "add", "unrelated.txt")
        git(fixture.repo, "commit", "-m", "unrelated history")
        unrelated = git(fixture.repo, "rev-parse", "HEAD")
        git(fixture.repo, "checkout", "main")
        self.publish_superseded_claim(fixture)

        registry = json.loads(fixture.registry_path.read_text(encoding="utf-8"))
        record = next(
            item for item in registry["worktrees"] if item.get("package") == fixture.package
        )
        record["head"] = unrelated
        fixture.registry_path.write_text(
            json.dumps(registry, indent=2) + "\n", encoding="utf-8"
        )
        exact_registry = fixture.registry_path.read_bytes()
        code, refused = fixture.run(
            "retire",
            "--path",
            str(durable),
            "--task-ref",
            fixture.writer,
            "--expected-head",
            candidate,
            "--execute",
        )
        self.assertEqual(code, 2, refused)
        self.assertIn("cannot be safely reconciled", refused["error"])
        self.assertEqual(fixture.registry_path.read_bytes(), exact_registry)
        self.assertTrue(durable.exists())

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

    def test_finalize_and_control_repoint_preserve_completed_preparation_bytes(self):
        (
            fixture,
            receiver,
            successor,
            owner_ref,
            _source_path,
            control_path,
        ) = self.owner_reassignment_setup("continuity-custody")
        code, prepared = self.run_owner_reassignment_prepare(
            fixture, receiver, successor, owner_ref, control_path
        )
        self.assertEqual(code, 0, prepared)
        registry_before = json.loads(
            fixture.registry_path.read_text(encoding="utf-8")
        )
        preparation_before = next(
            item
            for item in registry_before["owner_reassignment_preparations"]
            if item["preparation_id"] == prepared["preparation_id"]
        )
        canonical_before = json.dumps(
            preparation_before,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        self.assertEqual(preparation_before["status"], "completed")
        self.assertIsNone(registry_before["pending"])

        code, released = fixture.run(
            "finalize-task", "--task-ref", receiver, "--execute"
        )
        self.assertEqual(code, 0, released)
        (fixture.repo / "unrelated.txt").write_text(
            "strict descendant main movement\n", encoding="utf-8"
        )
        git(fixture.repo, "add", "unrelated.txt")
        git(fixture.repo, "commit", "-m", "unrelated main movement")
        git(fixture.repo, "push", "origin", "main")

        code, repointed = fixture.run(
            "control",
            "--task-ref",
            "task:continuity-follow-up",
            "--purpose",
            "control",
            "--package",
            "PS-CONTINUITY-FOLLOW-UP-001",
            "--base",
            "origin/main",
            "--branch",
            "work/2026-08-27-delivery-owner-reassignment-continuity-follow-up",
            "--execute",
        )
        self.assertEqual(code, 0, repointed)
        registry_after = json.loads(
            fixture.registry_path.read_text(encoding="utf-8")
        )
        preparation_after = next(
            item
            for item in registry_after["owner_reassignment_preparations"]
            if item["preparation_id"] == prepared["preparation_id"]
        )
        canonical_after = json.dumps(
            preparation_after,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        self.assertEqual(canonical_after, canonical_before)
        self.assertEqual(preparation_after["status"], "completed")
        self.assertIsNone(registry_after["pending"])

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

    def test_owner_reassignment_without_a_durable_source_keeps_normal_path(self):
        fixture = self.fixture()
        receiver = "agent:replacement-without-source-worktree"
        successor = "work/2026-08-27-test-lifecycle-no-source-recovery"
        owner_ref = "session:owner/decision:no-source-reassignment"
        git(
            fixture.repo,
            "push",
            "origin",
            f"{fixture.main_sha}:refs/heads/{fixture.branch}",
        )
        fixture.initialize()
        code, leased = fixture.run(
            "control",
            "--task-ref",
            receiver,
            "--package",
            fixture.package,
            "--branch",
            "work/2026-08-27-delivery-owner-reassignment-no-source",
            "--execute",
        )
        self.assertEqual(code, 0, leased)

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
            cwd=Path(leased["path"]),
        )
        self.assertEqual(code, 0, prepared)
        self.assertFalse(prepared["source_registry_head_reconciled"])
        registry = json.loads(fixture.registry_path.read_text(encoding="utf-8"))
        self.assertEqual(
            registry["owner_reassignment_preparations"][0]["source_snapshot"][
                "durable_records"
            ],
            [],
        )

    def test_owner_reassignment_atomically_reconciles_stale_active_durable_head(self):
        (
            fixture,
            receiver,
            successor,
            owner_ref,
            source_path,
            control_path,
        ) = self.owner_reassignment_setup("stale-active-head")
        source_unavailable_ref = "session:orchestrator/source-task-unavailable"
        original_registry = json.loads(
            fixture.registry_path.read_text(encoding="utf-8")
        )
        original_record = next(
            record
            for record in original_registry["worktrees"]
            if record.get("package") == fixture.package
            and record.get("kind") == "durable"
        )
        self.assertEqual(original_record["head"], fixture.main_sha)

        (source_path / "sample.txt").write_text(
            "advanced by the original writer\n", encoding="utf-8"
        )
        git(source_path, "add", "sample.txt")
        git(source_path, "commit", "-m", "advance source checkpoint")
        checkpoint = git(source_path, "rev-parse", "HEAD")
        git(source_path, "push", "origin", fixture.branch)
        self.assertNotEqual(checkpoint, fixture.main_sha)

        code, prepared = fixture.run(
            "prepare-owner-reassignment",
            "--package",
            fixture.package,
            "--task-ref",
            receiver,
            "--successor-branch",
            successor,
            "--expected-checkpoint",
            checkpoint,
            "--owner-authorization-ref",
            owner_ref,
            "--source-unavailable-ref",
            source_unavailable_ref,
            "--execute",
            cwd=control_path,
        )
        self.assertEqual(code, 0, prepared)
        self.assertTrue(prepared["source_registry_head_reconciled"])
        self.assertEqual(prepared["source_unavailable_ref"], source_unavailable_ref)
        registry = json.loads(fixture.registry_path.read_text(encoding="utf-8"))
        self.assertIsNone(registry["pending"])
        record = next(
            item
            for item in registry["worktrees"]
            if item.get("package") == fixture.package
            and item.get("kind") == "durable"
        )
        self.assertEqual(record["head"], checkpoint)
        self.assertEqual(record["previous_head"], fixture.main_sha)
        proof = record["owner_reassignment_head_reconciliation"]
        self.assertEqual(proof["previous_head"], fixture.main_sha)
        self.assertEqual(proof["checkpoint_sha"], checkpoint)
        self.assertEqual(proof["source_unavailable_ref"], source_unavailable_ref)
        self.assertEqual(record["remote_branch_tip"], checkpoint)
        self.assertEqual(record["remote_branch_status"], "fetched")
        LIFECYCLE.validate_owner_reassignment_registry(registry)
        completed_preparation = registry["owner_reassignment_preparations"][0]
        self.assertEqual(completed_preparation["source_head_reconciliation"], proof)
        orphaned_completed = copy.deepcopy(registry)
        orphaned_preparation = orphaned_completed[
            "owner_reassignment_preparations"
        ][0]
        orphaned_preparation.pop("source_head_reconciliation")
        orphaned_preparation["preparation_id"] = LIFECYCLE._preparation_digest(
            orphaned_preparation
        )
        with self.assertRaisesRegex(
            LIFECYCLE.Refusal, "lacks one exact journal or preparation"
        ):
            LIFECYCLE.validate_owner_reassignment_registry(orphaned_completed)
        for field in (
            "owner_reassignment_head_reconciliation",
            "source_head_reconciliation",
        ):
            null_proof = copy.deepcopy(registry)
            if field == "owner_reassignment_head_reconciliation":
                target = next(
                    item
                    for item in null_proof["worktrees"]
                    if item.get("package") == fixture.package
                    and item.get("kind") == "durable"
                )
            else:
                target = null_proof["owner_reassignment_preparations"][0]
            target[field] = None
            with self.assertRaises(LIFECYCLE.Refusal):
                LIFECYCLE.validate_owner_reassignment_registry(null_proof)
        poisoned_completed = copy.deepcopy(registry)
        poisoned_completed_record = next(
            item
            for item in poisoned_completed["worktrees"]
            if item.get("package") == fixture.package
            and item.get("kind") == "durable"
        )
        poisoned_completed_record[
            "owner_reassignment_head_reconciliation"
        ]["source_unavailable_ref"] = owner_ref
        with self.assertRaisesRegex(LIFECYCLE.Refusal, "must be separate"):
            LIFECYCLE.validate_owner_reassignment_registry(poisoned_completed)
        self.assertEqual(
            registry["owner_reassignment_preparations"][0]["checkpoint_sha"],
            checkpoint,
        )
        self.assertEqual(
            git(
                fixture.repo,
                "ls-remote",
                "origin",
                f"refs/heads/{successor}",
            ).split()[0],
            checkpoint,
        )
        handoff = {
            "type": "owner_reassignment",
            "from_ref": fixture.writer,
            "to_ref": receiver,
            "from_branch": fixture.branch,
            "to_branch": successor,
            "checkpoint_sha": checkpoint,
            "owner_authorization_ref": owner_ref,
        }
        claim_path = (
            fixture.repo
            / "docs"
            / "governance"
            / "lane_claims"
            / f"{fixture.package}.json"
        )
        reassigned_claim = json.loads(claim_path.read_text(encoding="utf-8"))
        reassigned_claim.update(
            {"writer_ref": receiver, "branch": successor, "handoff": handoff}
        )
        claim_path.write_text(
            json.dumps(reassigned_claim, indent=2) + "\n", encoding="utf-8"
        )
        git(fixture.repo, "add", str(claim_path.relative_to(fixture.repo)))
        git(fixture.repo, "commit", "-m", "merge stale-head reassignment")
        git(fixture.repo, "push", "origin", "main")
        code, ensured = fixture.run(
            "ensure",
            "--package",
            fixture.package,
            "--task-ref",
            receiver,
            "--execute",
        )
        self.assertEqual(code, 0, ensured)
        consumed_registry = json.loads(
            fixture.registry_path.read_text(encoding="utf-8")
        )
        LIFECYCLE.validate_owner_reassignment_registry(consumed_registry)
        source = next(
            item
            for item in consumed_registry["worktrees"]
            if item.get("kind") == "reassignment_source"
            and item.get("package") == fixture.package
        )
        self.assertEqual(
            source["owner_reassignment_head_reconciliation"], proof
        )

    def test_stale_active_durable_head_requires_unavailability_evidence(self):
        (
            fixture,
            receiver,
            successor,
            owner_ref,
            source_path,
            control_path,
        ) = self.owner_reassignment_setup("stale-head-no-evidence")
        (source_path / "sample.txt").write_text(
            "advanced without a recovery witness\n", encoding="utf-8"
        )
        git(source_path, "add", "sample.txt")
        git(source_path, "commit", "-m", "advance unwitnessed source")
        checkpoint = git(source_path, "rev-parse", "HEAD")
        git(source_path, "push", "origin", fixture.branch)
        before = fixture.registry_path.read_bytes()
        code, refused = fixture.run(
            "prepare-owner-reassignment",
            "--package",
            fixture.package,
            "--task-ref",
            receiver,
            "--successor-branch",
            successor,
            "--expected-checkpoint",
            checkpoint,
            "--owner-authorization-ref",
            owner_ref,
            "--execute",
            cwd=control_path,
        )
        self.assertEqual(code, 2, refused)
        self.assertIn("source-unavailability", refused["error"])
        self.assertEqual(fixture.registry_path.read_bytes(), before)
        self.assert_remote_branch_absent(fixture, successor)
        for reused_ref in (fixture.writer, owner_ref):
            code, refused = fixture.run(
                "prepare-owner-reassignment",
                "--package",
                fixture.package,
                "--task-ref",
                receiver,
                "--successor-branch",
                successor,
                "--expected-checkpoint",
                checkpoint,
                "--owner-authorization-ref",
                owner_ref,
                "--source-unavailable-ref",
                reused_ref,
                "--execute",
                cwd=control_path,
            )
            self.assertEqual(code, 2, refused)
            self.assertIn("must be separate", refused["error"])
            self.assertEqual(fixture.registry_path.read_bytes(), before)
            self.assert_remote_branch_absent(fixture, successor)

    def test_failed_successor_creation_rolls_back_head_reconciliation(self):
        (
            fixture,
            receiver,
            successor,
            owner_ref,
            source_path,
            control_path,
        ) = self.owner_reassignment_setup("stale-head-push-failure")
        (source_path / "sample.txt").write_text(
            "advanced before failed successor creation\n", encoding="utf-8"
        )
        git(source_path, "add", "sample.txt")
        git(source_path, "commit", "-m", "advance source before push failure")
        checkpoint = git(source_path, "rev-parse", "HEAD")
        git(source_path, "push", "origin", fixture.branch)
        registry_before = json.loads(
            fixture.registry_path.read_text(encoding="utf-8")
        )
        source_before = next(
            copy.deepcopy(record)
            for record in registry_before["worktrees"]
            if record.get("package") == fixture.package
            and record.get("kind") == "durable"
        )
        context = LIFECYCLE._repo_context(fixture.repo)
        arguments = SimpleNamespace(
            execute=True,
            package=fixture.package,
            task_ref=receiver,
            successor_branch=successor,
            expected_checkpoint=checkpoint,
            owner_authorization_ref=owner_ref,
            source_unavailable_ref="session:orchestrator/source-task-unavailable",
        )
        original_git_result = LIFECYCLE._git_result

        def refuse_successor_push(root: Path, *git_arguments: str):
            if git_arguments[:2] == ("push", "--porcelain"):
                return subprocess.CompletedProcess(
                    ["git", *git_arguments],
                    1,
                    stdout="",
                    stderr="simulated successor push refusal",
                )
            return original_git_result(root, *git_arguments)

        with patch.object(LIFECYCLE.Path, "cwd", return_value=control_path), patch.object(
            LIFECYCLE, "_git_result", side_effect=refuse_successor_push
        ):
            with self.assertRaisesRegex(
                LIFECYCLE.Refusal, "guarded absent-ref successor creation failed"
            ):
                LIFECYCLE.command_prepare_owner_reassignment(context, arguments)
        registry_after = json.loads(
            fixture.registry_path.read_text(encoding="utf-8")
        )
        source_after = next(
            record
            for record in registry_after["worktrees"]
            if record.get("package") == fixture.package
            and record.get("kind") == "durable"
        )
        self.assertEqual(source_after, source_before)
        self.assertIsNone(registry_after["pending"])
        self.assertEqual(registry_after["owner_reassignment_preparations"], [])
        self.assert_remote_branch_absent(fixture, successor)

    def test_stale_active_durable_head_must_be_checkpoint_ancestor(self):
        (
            fixture,
            receiver,
            successor,
            owner_ref,
            _source_path,
            control_path,
        ) = self.owner_reassignment_setup("stale-head-nonancestor")
        registry = json.loads(fixture.registry_path.read_text(encoding="utf-8"))
        source = next(
            record
            for record in registry["worktrees"]
            if record.get("package") == fixture.package
            and record.get("kind") == "durable"
        )
        source["head"] = "f" * 40
        fixture.registry_path.write_text(
            json.dumps(registry, indent=2) + "\n", encoding="utf-8"
        )
        before = fixture.registry_path.read_bytes()
        code, refused = fixture.run(
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
            "--source-unavailable-ref",
            "session:orchestrator/source-task-unavailable",
            "--execute",
            cwd=control_path,
        )
        self.assertEqual(code, 2, refused)
        self.assertIn("not an ancestor", refused["error"])
        self.assertEqual(fixture.registry_path.read_bytes(), before)
        self.assert_remote_branch_absent(fixture, successor)

    def test_crash_before_successor_push_recovers_prior_registry_head(self):
        (
            fixture,
            receiver,
            successor,
            owner_ref,
            source_path,
            control_path,
        ) = self.owner_reassignment_setup("stale-head-prepush-crash")
        (source_path / "sample.txt").write_text(
            "advanced before simulated process death\n", encoding="utf-8"
        )
        git(source_path, "add", "sample.txt")
        git(source_path, "commit", "-m", "advance before simulated death")
        checkpoint = git(source_path, "rev-parse", "HEAD")
        git(source_path, "push", "origin", fixture.branch)
        registry_before = json.loads(
            fixture.registry_path.read_text(encoding="utf-8")
        )
        source_before = next(
            copy.deepcopy(record)
            for record in registry_before["worktrees"]
            if record.get("package") == fixture.package
            and record.get("kind") == "durable"
        )
        context = LIFECYCLE._repo_context(fixture.repo)
        arguments = SimpleNamespace(
            execute=True,
            package=fixture.package,
            task_ref=receiver,
            successor_branch=successor,
            expected_checkpoint=checkpoint,
            owner_authorization_ref=owner_ref,
            source_unavailable_ref="session:orchestrator/source-task-unavailable",
        )
        original_git_result = LIFECYCLE._git_result

        def crash_before_push(root: Path, *git_arguments: str):
            if git_arguments[:2] == ("push", "--porcelain"):
                raise RuntimeError("simulated process death before successor push")
            return original_git_result(root, *git_arguments)

        with patch.object(LIFECYCLE.Path, "cwd", return_value=control_path), patch.object(
            LIFECYCLE, "_git_result", side_effect=crash_before_push
        ):
            with self.assertRaisesRegex(RuntimeError, "simulated process death"):
                LIFECYCLE.command_prepare_owner_reassignment(context, arguments)
        pending_bytes = fixture.registry_path.read_bytes()
        pending_registry = json.loads(pending_bytes)
        self.assertIsNotNone(pending_registry["pending"])
        pending_source = next(
            record
            for record in pending_registry["worktrees"]
            if record.get("package") == fixture.package
            and record.get("kind") == "durable"
        )
        self.assertEqual(pending_source["head"], checkpoint)
        missing_link = copy.deepcopy(pending_registry)
        missing_link["pending"].pop("source_registry_reconciliation")
        fixture.registry_path.write_text(
            json.dumps(missing_link, indent=2) + "\n", encoding="utf-8"
        )
        with self.assertRaisesRegex(
            LIFECYCLE.Refusal, "lacks one exact journal or preparation"
        ):
            LIFECYCLE._load_registry(fixture.registry_path)
        self.assertEqual(
            json.loads(fixture.registry_path.read_text(encoding="utf-8")),
            missing_link,
        )
        fixture.registry_path.write_bytes(pending_bytes)
        poisoned_pending = copy.deepcopy(pending_registry)
        poisoned_pending_source = next(
            record
            for record in poisoned_pending["worktrees"]
            if record.get("package") == fixture.package
            and record.get("kind") == "durable"
        )
        poisoned_pending_source[
            "owner_reassignment_head_reconciliation"
        ]["source_unavailable_ref"] = fixture.writer
        with self.assertRaisesRegex(LIFECYCLE.Refusal, "must be separate"):
            LIFECYCLE.validate_owner_reassignment_registry(poisoned_pending)
        self.assert_remote_branch_absent(fixture, successor)

        loaded = LIFECYCLE._load_registry(fixture.registry_path)
        recovered = LIFECYCLE._reconcile_pending(context, loaded)
        self.assertEqual(recovered["outcome"], "rolled_back")
        recovered_registry = json.loads(
            fixture.registry_path.read_text(encoding="utf-8")
        )
        recovered_source = next(
            record
            for record in recovered_registry["worktrees"]
            if record.get("package") == fixture.package
            and record.get("kind") == "durable"
        )
        self.assertEqual(recovered_source, source_before)
        self.assertIsNone(recovered_registry["pending"])

    def test_reconciled_source_cannot_be_advanced_by_later_ensure(self):
        (
            fixture,
            receiver,
            successor,
            owner_ref,
            source_path,
            control_path,
        ) = self.owner_reassignment_setup("reconciled-source-freeze")
        (source_path / "sample.txt").write_text(
            "authorized recovery checkpoint\n", encoding="utf-8"
        )
        git(source_path, "add", "sample.txt")
        git(source_path, "commit", "-m", "prepare recovery checkpoint")
        checkpoint = git(source_path, "rev-parse", "HEAD")
        git(source_path, "push", "origin", fixture.branch)
        code, prepared = fixture.run(
            "prepare-owner-reassignment",
            "--package",
            fixture.package,
            "--task-ref",
            receiver,
            "--successor-branch",
            successor,
            "--expected-checkpoint",
            checkpoint,
            "--owner-authorization-ref",
            owner_ref,
            "--source-unavailable-ref",
            "session:orchestrator/source-task-unavailable",
            "--execute",
            cwd=control_path,
        )
        self.assertEqual(code, 0, prepared)

        (source_path / "sample.txt").write_text(
            "unexpected post-preparation movement\n", encoding="utf-8"
        )
        git(source_path, "add", "sample.txt")
        git(source_path, "commit", "-m", "move source after preparation")
        git(source_path, "push", "origin", fixture.branch)
        code, refused = fixture.run(
            "ensure",
            "--package",
            fixture.package,
            "--task-ref",
            fixture.writer,
            "--execute",
        )
        self.assertEqual(code, 2, refused)
        self.assertIn("moved after preparation", refused["error"])
        registry = json.loads(fixture.registry_path.read_text(encoding="utf-8"))
        source = next(
            record
            for record in registry["worktrees"]
            if record.get("package") == fixture.package
            and record.get("kind") == "durable"
        )
        self.assertEqual(source["head"], checkpoint)
        self.assertIsNone(registry["pending"])

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

    def test_consumed_reassignment_accepts_two_proven_voluntary_transfers(self):
        (
            fixture, original, branch, source_path, receiver_path, claim_path, prepared,
        ) = self.consumed_reassignment_for_transfer("voluntary-lineage")
        first = "agent:voluntary-next-writer"
        first_main = self.accept_voluntary_transfer(
            fixture, claim_path, original, first, fixture.main_sha
        )
        code, adopted = fixture.run(
            "adopt", "--package", fixture.package, "--path", str(receiver_path),
            "--task-ref", first, "--execute",
        )
        self.assertEqual(code, 0, adopted)
        registry = LIFECYCLE._load_registry(fixture.registry_path)
        receiver = next(record for record in registry["worktrees"] if record.get("path") == str(receiver_path))
        historical = registry["owner_reassignment_preparations"][0]
        self.assertEqual(historical["to_ref"], original)
        self.assertEqual(historical["preparation_id"], prepared["preparation_id"])
        self.assertEqual(historical["status"], "consumed")
        self.assertEqual(receiver["task_ref"], first)
        self.assertEqual(receiver["voluntary_transfer_lineage"][0]["accepted_main"], first_main)
        self.assertEqual(receiver["voluntary_transfer_lineage"][0]["preparation_id"], prepared["preparation_id"])
        self.assertEqual(git(source_path, "rev-parse", "HEAD"), fixture.main_sha)

        code, reused = fixture.run(
            "ensure", "--package", fixture.package, "--task-ref", first, "--execute"
        )
        self.assertEqual(code, 0, reused)
        self.assertEqual(reused["status"], "reused")
        second = "agent:voluntary-third-writer"
        second_main = self.accept_voluntary_transfer(
            fixture, claim_path, first, second, fixture.main_sha
        )
        code, adopted_again = fixture.run(
            "adopt", "--package", fixture.package, "--path", str(receiver_path),
            "--task-ref", second, "--execute",
        )
        self.assertEqual(code, 0, adopted_again)
        code, reused_again = fixture.run(
            "ensure", "--package", fixture.package, "--task-ref", second,
            "--execute",
        )
        self.assertEqual(code, 0, reused_again)
        self.assertEqual(reused_again["status"], "reused")
        registry = LIFECYCLE._load_registry(fixture.registry_path)
        receiver = next(record for record in registry["worktrees"] if record.get("path") == str(receiver_path))
        self.assertEqual([p["accepted_main"] for p in receiver["voluntary_transfer_lineage"]], [first_main, second_main])
        self.assertEqual(registry["owner_reassignment_preparations"][0]["to_ref"], original)

    def test_consumed_reassignment_rejects_unaccepted_and_forged_transfer(self):
        fixture, original, branch, _source, receiver_path, claim_path, _prepared = (
            self.consumed_reassignment_for_transfer("voluntary-refusal")
        )
        next_writer = "agent:voluntary-next-writer"
        claim = json.loads(claim_path.read_text(encoding="utf-8"))
        claim["writer_ref"] = next_writer
        claim["handoff"] = {
            "from_ref": original, "to_ref": next_writer,
            "checkpoint_sha": fixture.main_sha, "relinquished": True,
        }
        claim_path.write_text(json.dumps(claim, indent=2) + "\n", encoding="utf-8")
        code, unaccepted = fixture.run(
            "adopt", "--package", fixture.package, "--path", str(receiver_path),
            "--task-ref", next_writer, "--execute",
        )
        self.assertEqual(code, 2, unaccepted)
        self.assertIn("writer_ref", unaccepted["error"])
        claim_path.write_text(json.dumps({**claim, "handoff": {**claim["handoff"], "from_ref": "agent:forged"}}, indent=2) + "\n", encoding="utf-8")
        git(fixture.repo, "add", str(claim_path.relative_to(fixture.repo)))
        git(fixture.repo, "commit", "-m", "forged accepted claim in fixture")
        git(fixture.repo, "push", "origin", "main")
        code, forged = fixture.run(
            "adopt", "--package", fixture.package, "--path", str(receiver_path),
            "--task-ref", next_writer, "--execute",
        )
        self.assertEqual(code, 2, forged)
        self.assertIn("exact accepted claim transition", forged["error"])
        registry = LIFECYCLE._load_registry(fixture.registry_path)
        receiver = next(record for record in registry["worktrees"] if record.get("path") == str(receiver_path))
        self.assertEqual(receiver["task_ref"], original)
        self.assertNotIn("voluntary_transfer_lineage", receiver)

    def test_consumed_reassignment_rejects_poisoned_transfer_lineage(self):
        fixture, original, branch, _source, receiver_path, claim_path, prepared = (
            self.consumed_reassignment_for_transfer("voluntary-poison")
        )
        next_writer = "agent:voluntary-next-writer"
        self.accept_voluntary_transfer(
            fixture, claim_path, original, next_writer, fixture.main_sha
        )
        code, adopted = fixture.run(
            "adopt", "--package", fixture.package, "--path", str(receiver_path),
            "--task-ref", next_writer, "--execute",
        )
        self.assertEqual(code, 0, adopted)
        baseline = LIFECYCLE._load_registry(fixture.registry_path)
        for field, value in (
            ("preparation_id", "f" * 64),
            ("path", str(fixture.repo)),
            ("branch", fixture.branch),
            ("from_ref", "agent:forged"),
            ("to_ref", "agent:forged"),
            ("checkpoint_sha", "f" * 40),
            ("accepted_main", "f" * 40),
            ("previous_main", "f" * 40),
        ):
            with self.subTest(field=field):
                registry = json.loads(json.dumps(baseline))
                receiver = next(record for record in registry["worktrees"] if record.get("path") == str(receiver_path))
                receiver["voluntary_transfer_lineage"][0][field] = value
                if field in {"checkpoint_sha", "accepted_main", "previous_main"}:
                    LIFECYCLE.validate_owner_reassignment_registry(registry)
                    context = LIFECYCLE._repo_context(fixture.repo)
                    current_claim = LIFECYCLE._claim_from_origin_main(context, fixture.package)
                    with self.assertRaises(LIFECYCLE.Refusal):
                        LIFECYCLE._reprove_voluntary_transfer_lineage(
                            context, registry, receiver, current_claim
                        )
                else:
                    with self.assertRaises(LIFECYCLE.Refusal):
                        LIFECYCLE.validate_owner_reassignment_registry(registry)
        self.assertEqual(baseline["owner_reassignment_preparations"][0]["preparation_id"], prepared["preparation_id"])

    def test_consumed_reassignment_rejects_wrong_accepted_transfer_tuple(self):
        for case in ("checkpoint", "branch", "to_ref"):
            with self.subTest(case=case):
                fixture, original, branch, _source, receiver_path, claim_path, _prepared = (
                    self.consumed_reassignment_for_transfer(f"wrong-{case.replace('_', '-')}")
                )
                next_writer = "agent:voluntary-next-writer"
                claim = json.loads(claim_path.read_text(encoding="utf-8"))
                claim["writer_ref"] = next_writer
                claim["handoff"] = {
                    "from_ref": original, "to_ref": next_writer,
                    "checkpoint_sha": fixture.main_sha, "relinquished": True,
                }
                if case == "checkpoint":
                    claim["handoff"]["checkpoint_sha"] = "f" * 40
                elif case == "branch":
                    claim["branch"] = "work/2026-08-27-forged-branch"
                else:
                    claim["handoff"]["to_ref"] = "agent:wrong-target"
                claim_path.write_text(json.dumps(claim, indent=2) + "\n", encoding="utf-8")
                git(fixture.repo, "add", str(claim_path.relative_to(fixture.repo)))
                git(fixture.repo, "commit", "-m", f"wrong {case} transfer fixture")
                git(fixture.repo, "push", "origin", "main")
                code, refused = fixture.run(
                    "adopt", "--package", fixture.package,
                    "--path", str(receiver_path), "--task-ref", next_writer,
                    "--execute",
                )
                self.assertEqual(code, 2, refused)
                retained = LIFECYCLE._load_registry(fixture.registry_path)
                receiver = next(record for record in retained["worktrees"] if record.get("path") == str(receiver_path))
                self.assertEqual(receiver["task_ref"], original)
                self.assertNotIn("voluntary_transfer_lineage", receiver)

    def test_transferred_receiver_reuse_refuses_changed_preserved_source(self):
        fixture, original, _branch, source_path, receiver_path, claim_path, _prepared = (
            self.consumed_reassignment_for_transfer("source-drift")
        )
        next_writer = "agent:voluntary-next-writer"
        self.accept_voluntary_transfer(
            fixture, claim_path, original, next_writer, fixture.main_sha
        )
        code, adopted = fixture.run(
            "adopt", "--package", fixture.package, "--path", str(receiver_path),
            "--task-ref", next_writer, "--execute",
        )
        self.assertEqual(code, 0, adopted)
        (source_path / "unexpected-untracked.txt").write_text("source residue\n", encoding="utf-8")
        code, refused = fixture.run(
            "ensure", "--package", fixture.package, "--task-ref", next_writer,
            "--execute",
        )
        self.assertEqual(code, 2, refused)
        self.assertIn("source-branch worktree is not pristine", refused["error"])

    def test_adopt_finds_transfer_before_later_accepted_claim_metadata(self):
        fixture, original, _branch, _source, receiver_path, claim_path, _prepared = (
            self.consumed_reassignment_for_transfer("later-metadata")
        )
        next_writer = "agent:voluntary-next-writer"
        transfer_main = self.accept_voluntary_transfer(
            fixture, claim_path, original, next_writer, fixture.main_sha
        )
        claim = json.loads(claim_path.read_text(encoding="utf-8"))
        claim["owner_outcome_ref"] = "session:owner/accepted-metadata"
        claim_path.write_text(json.dumps(claim, indent=2) + "\n", encoding="utf-8")
        git(fixture.repo, "add", str(claim_path.relative_to(fixture.repo)))
        git(fixture.repo, "commit", "-m", "later accepted claim metadata")
        git(fixture.repo, "push", "origin", "main")
        code, adopted = fixture.run(
            "adopt", "--package", fixture.package, "--path", str(receiver_path),
            "--task-ref", next_writer, "--execute",
        )
        self.assertEqual(code, 0, adopted)
        registry = LIFECYCLE._load_registry(fixture.registry_path)
        record = next(item for item in registry["worktrees"] if item.get("path") == str(receiver_path))
        self.assertEqual(record["voluntary_transfer_lineage"][0]["accepted_main"], transfer_main)

    def test_later_owner_reassignment_after_voluntary_transfer_preserves_chain(self):
        fixture, original, branch, source_path, receiver_path, claim_path, _prepared = (
            self.consumed_reassignment_for_transfer("transfer-then-reassign")
        )
        current_writer = "agent:voluntary-next-writer"
        self.accept_voluntary_transfer(
            fixture, claim_path, original, current_writer, fixture.main_sha
        )
        code, adopted = fixture.run(
            "adopt", "--package", fixture.package, "--path", str(receiver_path),
            "--task-ref", current_writer, "--execute",
        )
        self.assertEqual(code, 0, adopted)
        code, finalized = fixture.run(
            "finalize-task", "--task-ref", original, "--execute"
        )
        self.assertEqual(code, 0, finalized)
        successor_writer = "agent:later-owner-replacement"
        successor_branch = "work/2026-08-27-test-lifecycle-later-owner-recovery"
        owner_ref = "session:owner/decision:later-owner-reassignment"
        code, control = fixture.run(
            "control", "--package", fixture.package, "--task-ref", successor_writer,
            "--branch", "work/2026-08-27-delivery-owner-reassignment-after-transfer",
            "--base", "origin/main", "--execute",
        )
        self.assertEqual(code, 0, control)
        code, prepared = fixture.run(
            "prepare-owner-reassignment", "--package", fixture.package,
            "--task-ref", successor_writer, "--successor-branch", successor_branch,
            "--expected-checkpoint", fixture.main_sha,
            "--owner-authorization-ref", owner_ref, "--execute",
            cwd=Path(control["path"]),
        )
        self.assertEqual(code, 0, prepared)
        claim = json.loads(claim_path.read_text(encoding="utf-8"))
        claim.update({
            "writer_ref": successor_writer,
            "branch": successor_branch,
            "handoff": {
                "type": "owner_reassignment",
                "from_ref": current_writer,
                "to_ref": successor_writer,
                "from_branch": branch,
                "to_branch": successor_branch,
                "checkpoint_sha": fixture.main_sha,
                "owner_authorization_ref": owner_ref,
            },
        })
        claim_path.write_text(json.dumps(claim, indent=2) + "\n", encoding="utf-8")
        git(fixture.repo, "add", str(claim_path.relative_to(fixture.repo)))
        git(fixture.repo, "commit", "-m", "accept later owner reassignment")
        git(fixture.repo, "push", "origin", "main")
        code, ensured = fixture.run(
            "ensure", "--package", fixture.package,
            "--task-ref", successor_writer, "--execute",
        )
        self.assertEqual(code, 0, ensured)
        registry = LIFECYCLE._load_registry(fixture.registry_path)
        self.assertEqual([item["status"] for item in registry["owner_reassignment_preparations"]], ["consumed", "consumed"])
        prior = next(item for item in registry["worktrees"] if item.get("path") == str(receiver_path))
        self.assertEqual(prior["kind"], "reassignment_source")
        self.assertEqual(prior["task_ref"], current_writer)
        self.assertEqual(len(prior["voluntary_transfer_lineage"]), 1)
        self.assertEqual(git(source_path, "rev-parse", "HEAD"), fixture.main_sha)

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


class ControlCustodyTests(unittest.TestCase):
    def setUp(self):
        self.f = RepositoryFixture()
        self.addCleanup(self.f.cleanup)
        self.f.initialize()
        code, result = self.f.run('control', '--task-ref', self.f.writer, '--package', self.f.package,
                                  '--branch', self.f.branch, '--base', self.f.main_sha, '--execute')
        self.assertEqual(code, 0, result)
        self.context = LIFECYCLE._repo_context(str(self.f.repo))
        self.receiver = 'agent:generic-receiver'
        self.proof = dict(path=result['path'], package=self.f.package, branch=self.f.branch,
                          head=self.f.main_sha, from_ref=self.f.writer, to_ref=self.receiver,
                          old_lease=result['lease'], old_token=result['lease_token'],
                          owner_ref='session:owner/authorization', review_ref='agent:independent-review',
                          quiescence_ref='session:host/quiescence', source_liveness='UNKNOWN', owner_revocation=True)
        self.proof_path = self.f.base / 'proof.json'

    def command(self, action, caller=None, **kwargs):
        args = SimpleNamespace(action=action, task_ref=caller or self.receiver, execute=True,
                               proof_file=str(self.proof_path), transition=None, acceptance_ref=None)
        for k, v in kwargs.items():
            setattr(args, k, v)
        self.proof_path.write_text(json.dumps(self.proof), encoding='utf-8')
        with patch.dict(os.environ, {'PEERSLATE_CALLER_REF': caller or self.receiver, 'CODEX_THREAD_ID': ''}):
            return LIFECYCLE.command_control_custody(self.context, args)

    def accepted(self):
        item = self.command('propose')['transition']
        self.command('accept', transition=item['id'], acceptance_ref='agent:receiver/acceptance')
        return item['id']

    def register_context(self, *, package=None, receiver=None, token=None, owner_ref=None):
        args = SimpleNamespace(
            action='register',
            task_ref=self.f.writer,
            package=package or self.f.package,
            receiver_ref=receiver or self.receiver,
            context_id=None,
            owner_authorization_ref=owner_ref or 'session:owner/context-registration',
            lease_token=self.proof['old_token'] if token is None else token,
            caller_context='',
            execute=True,
        )
        with patch.dict(os.environ, {'PEERSLATE_CALLER_REF': self.f.writer, 'CODEX_THREAD_ID': ''}):
            return LIFECYCLE.command_caller_context(self.context, args)

    def test_context_registration_before_acceptance_grants_no_custody(self):
        registered = self.register_context()
        self.assertEqual(registered['status'], 'registered')
        self.assertEqual(registered['owner_authorization_ref'], 'session:owner/context-registration')
        registry = LIFECYCLE._load_registry(self.context.registry_path)
        control = LIFECYCLE._control_record(self.context, registry)
        self.assertEqual(control['task_ref'], self.f.writer)
        self.assertEqual(control['lease'], self.proof['old_lease'])
        with patch.dict(os.environ, {'PEERSLATE_CALLER_REF': '', 'CODEX_THREAD_ID': ''}):
            code, unscoped = self.f.run(
                'control', '--task-ref', self.receiver,
                '--caller-context', registered['caller_context'], '--base', self.f.main_sha,
                '--execute'
            )
            self.assertEqual(code, LIFECYCLE.REFUSAL_EXIT, unscoped)
            self.assertIn('requires an exact operation package', unscoped['error'])
            code, refused = self.f.run(
                'control', '--task-ref', self.receiver, '--package', self.f.package,
                '--caller-context', registered['caller_context'], '--base', self.f.main_sha,
                '--execute'
            )
        self.assertEqual(code, LIFECYCLE.REFUSAL_EXIT, refused)
        self.assertIn('does not hold the current control lease', refused['error'])

        proposed = self.command('propose')['transition']
        receiver_args = SimpleNamespace(
            action='accept', task_ref=self.receiver, execute=True,
            proof_file=None, transition=proposed['id'],
            acceptance_ref='agent:receiver/context-acceptance',
            caller_context=registered['caller_context'],
        )
        with patch.dict(os.environ, {'PEERSLATE_CALLER_REF': '', 'CODEX_THREAD_ID': ''}):
            accepted = LIFECYCLE.command_control_custody(self.context, receiver_args)
            self.assertEqual(accepted['status'], 'accepted')
            receiver_args.action = 'complete'
            receiver_args.acceptance_ref = None
            completed = LIFECYCLE.command_control_custody(self.context, receiver_args)
        self.assertEqual(completed['status'], 'completed')
        registry = LIFECYCLE._load_registry(self.context.registry_path)
        self.assertEqual(
            LIFECYCLE._control_record(self.context, registry)['task_ref'], self.receiver
        )

    def test_no_history_control_reconciles_explicit_and_native_identity(self):
        request = SimpleNamespace(
            execute=True,
            task_ref=self.f.writer,
            package=self.f.package,
            base=self.f.main_sha,
            release=False,
            purpose='identity-conflict-test',
            branch=self.f.branch,
            include=[],
            caller_context='',
        )
        environment = {
            'PEERSLATE_CALLER_REF': self.f.writer,
            'CODEX_THREAD_ID': '01a097f4-9de5-7723-9b13-65124d7ad4eb',
        }
        with patch.dict(os.environ, environment):
            with self.assertRaisesRegex(LIFECYCLE.Refusal, 'identities disagree'):
                LIFECYCLE.command_control(self.context, request)

    def test_context_registration_supports_fresh_unclaimed_package(self):
        fresh_package = 'PS-FRESH-CALLER-CONTEXT-001'
        with patch.dict(os.environ, {'PEERSLATE_CALLER_REF': self.f.writer, 'CODEX_THREAD_ID': ''}):
            code, released = self.f.run(
                'control', '--task-ref', self.f.writer, '--release',
                '--base', self.f.main_sha, '--execute'
            )
            self.assertEqual(code, 0, released)
            code, leased = self.f.run(
                'control', '--task-ref', self.f.writer, '--package', fresh_package,
                '--branch', self.f.branch, '--base', self.f.main_sha, '--execute'
            )
            self.assertEqual(code, 0, leased)
        registered = self.register_context(
            package=fresh_package,
            token=leased['lease_token'],
            owner_ref='session:owner/fresh-package-context',
        )
        self.assertEqual(registered['package'], fresh_package)
        self.assertEqual(
            registered['owner_authorization_ref'],
            'session:owner/fresh-package-context',
        )

    def test_context_registration_and_revocation_require_current_lease(self):
        with self.assertRaisesRegex(LIFECYCLE.Refusal, 'stale or missing'):
            self.register_context(token='')
        with self.assertRaisesRegex(LIFECYCLE.Refusal, 'stale or missing'):
            self.register_context(token='f' * 64)
        registered = self.register_context()
        revoke = SimpleNamespace(
            action='revoke', task_ref=self.f.writer, package=None,
            receiver_ref=None, context_id=registered['caller_context'],
            owner_authorization_ref='session:owner/context-revocation',
            lease_token='', caller_context='', execute=True,
        )
        with patch.dict(os.environ, {'PEERSLATE_CALLER_REF': self.f.writer, 'CODEX_THREAD_ID': ''}):
            with self.assertRaisesRegex(LIFECYCLE.Refusal, 'stale or missing'):
                LIFECYCLE.command_caller_context(self.context, revoke)
            revoke.lease_token = self.proof['old_token']
            revoked = LIFECYCLE.command_caller_context(self.context, revoke)
        self.assertEqual(revoked['status'], 'revoked')
        self.assertEqual(
            revoked['revocation_authorization_ref'],
            'session:owner/context-revocation',
        )
        registry = LIFECYCLE._load_registry(self.context.registry_path)
        with patch.dict(os.environ, {'PEERSLATE_CALLER_REF': '', 'CODEX_THREAD_ID': ''}), self.assertRaisesRegex(
            LIFECYCLE.Refusal, 'revoked'
        ):
            LIFECYCLE.resolve_caller_ref(
                registry=registry,
                repository_common_dir=self.context.common_dir,
                caller_context=registered['caller_context'],
                task_ref=self.receiver,
                package=self.f.package,
            )

    def test_control_run_propagates_scoped_context_without_bare_identity(self):
        registered = self.register_context()
        transition = self.command('propose')['transition']['id']
        receiver = SimpleNamespace(
            action='accept', task_ref=self.receiver, execute=True,
            proof_file=None, transition=transition,
            acceptance_ref='agent:receiver/context-acceptance',
            caller_context=registered['caller_context'],
        )
        with patch.dict(os.environ, {'PEERSLATE_CALLER_REF': '', 'CODEX_THREAD_ID': ''}):
            LIFECYCLE.command_control_custody(self.context, receiver)
            receiver.action = 'complete'
            receiver.acceptance_ref = None
            completed = LIFECYCLE.command_control_custody(self.context, receiver)
            observed = self.f.base / 'guarded-context.txt'
            script = (
                "import os; from pathlib import Path; "
                f"Path({str(observed)!r}).write_text("
                "os.environ.get('PEERSLATE_CALLER_CONTEXT','') + '|' + "
                "os.environ.get('PEERSLATE_CALLER_REF',''), encoding='utf-8')"
            )
            result = LIFECYCLE.command_control_run(
                self.context,
                SimpleNamespace(
                    execute=True,
                    task_ref=self.receiver,
                    lease_token=completed['lease_token'],
                    caller_context=registered['caller_context'],
                    command=[sys.executable, '-B', '-c', script],
                ),
            )
        self.assertEqual(result['returncode'], 0)
        self.assertEqual(
            observed.read_text(encoding='utf-8'),
            registered['caller_context'] + '|',
        )

    def test_lost_source_receiver_acceptance_transfer_and_idempotency(self):
        ident = self.accepted()
        out = self.command('complete', transition=ident)
        self.assertEqual(out['status'], 'completed')
        self.assertNotEqual(out['lease_token'], self.proof['old_token'])
        self.assertEqual(self.command('complete', transition=ident)['lease_token'], out['lease_token'])
        self.assertEqual(self.command('propose')['status'], 'completed')
        reg = LIFECYCLE._load_registry(self.context.registry_path)
        record = LIFECYCLE._control_record(self.context, reg)
        self.assertEqual(record['task_ref'], self.receiver)
        LIFECYCLE.require_control_custody_fence(reg, record, task_ref=self.receiver, lease_token=out['lease_token'])
        with self.assertRaises(LIFECYCLE.Refusal):
            LIFECYCLE.require_control_custody_fence(reg, record, task_ref=self.receiver, lease_token=self.proof['old_token'])
        with self.assertRaises(LIFECYCLE.Refusal):
            LIFECYCLE.require_control_custody_fence(reg, record, task_ref=self.f.writer, lease_token=out['lease_token'])
        record['lease'] = None
        with self.assertRaises(LIFECYCLE.Refusal):
            LIFECYCLE._custody_existing_guard(reg, self.f.writer)

    def test_source_cannot_accept_and_mismatched_caller(self):
        ident = self.command('propose')['transition']['id']
        with self.assertRaises(LIFECYCLE.Refusal):
            self.command('accept', caller=self.f.writer, transition=ident, acceptance_ref='agent:source/pretend')
        with self.assertRaises(LIFECYCLE.Refusal):
            self.command('complete', transition=ident)

    def test_malformed_and_mismatched_proofs_fail_closed(self):
        for key, value in [('owner_revocation', False), ('head', 'a'*40), ('old_token', 'b'*64),
                           ('review_ref', self.receiver), ('quiescence_ref', self.proof['owner_ref']),
                           ('old_lease', {}), ('source_liveness', []), ('from_ref', []), ('to_ref', {})]:
            with self.subTest(key=key):
                old = self.proof[key]
                self.proof[key] = value
                with self.assertRaises(LIFECYCLE.Refusal):
                    self.command('propose')
                self.proof[key] = old
        ident = self.command('propose')['transition']['id']
        with self.assertRaises(LIFECYCLE.Refusal):
            self.command('accept', transition=ident, acceptance_ref=self.proof['review_ref'])

    def test_interrupted_atomic_commit_retries_from_accepted_journal(self):
        ident = self.accepted()
        original = LIFECYCLE._atomic_write
        with patch.object(LIFECYCLE, '_atomic_write', side_effect=OSError('synthetic interruption')):
            with self.assertRaises(OSError):
                self.command('complete', transition=ident)
        reg = LIFECYCLE._load_registry(self.context.registry_path)
        self.assertEqual(reg['control_custody_transitions'][0]['state'], 'accepted')
        self.assertEqual(LIFECYCLE._control_record(self.context, reg)['task_ref'], self.f.writer)
        self.assertEqual(self.command('complete', transition=ident)['status'], 'completed')

    def test_pending_blocks_normal_mutation_and_guarded_writer_lock(self):
        ident = self.command('propose')['transition']['id']
        reg = LIFECYCLE._load_registry(self.context.registry_path)
        with self.assertRaises(LIFECYCLE.Refusal):
            LIFECYCLE._reconcile_pending(self.context, reg)
        self.command('accept', transition=ident, acceptance_ref='agent:receiver/acceptance')
        out = self.command('complete', transition=ident)
        started = self.f.base / "writer-started"
        stop = self.f.base / "writer-stop"
        errors = []
        script = "from pathlib import Path; import time; Path(" + repr(str(started)) + ").touch(); \\nwhile not Path(" + repr(str(stop)) + ").exists(): time.sleep(0.02)"
        script = script.replace("\\n", "\n")
        def run():
            try:
                LIFECYCLE.command_control_run(self.context, SimpleNamespace(execute=True, task_ref=self.receiver,
                    lease_token=out['lease_token'], command=[sys.executable, '-B', '-c', script]))
            except Exception as exc:
                errors.append(exc)
        with patch.dict(os.environ, {'PEERSLATE_CALLER_REF': self.receiver, 'CODEX_THREAD_ID': ''}):
            worker = threading.Thread(target=run)
            worker.start()
            try:
                deadline = time.monotonic() + 5
                while not started.exists() and time.monotonic() < deadline:
                    time.sleep(0.02)
                self.assertTrue(started.exists(), errors)
                with self.assertRaises(LIFECYCLE.Refusal):
                    with LIFECYCLE._registry_lock(self.context.registry_path):
                        pass
            finally:
                stop.touch()
                worker.join(5)
        self.assertFalse(worker.is_alive())
        self.assertFalse(errors, errors)

    def test_live_head_changed_after_acceptance_fails_cas(self):
        ident = self.accepted()
        path = Path(self.proof['path'])
        git(path, 'commit', '--allow-empty', '-m', 'unexpected external writer')
        with self.assertRaises(LIFECYCLE.Refusal):
            self.command('complete', transition=ident)
        reg = LIFECYCLE._load_registry(self.context.registry_path)
        self.assertEqual(reg['control_custody_transitions'][0]['state'], 'accepted')

    def test_after_atomic_write_interruption_is_already_completed(self):
        ident = self.accepted()
        atomic = LIFECYCLE._atomic_write
        def committed_then_interrupted(*args):
            atomic(*args)
            raise OSError('synthetic lost response after atomic commit')
        with patch.object(LIFECYCLE, '_atomic_write', side_effect=committed_then_interrupted):
            with self.assertRaises(OSError):
                self.command('complete', transition=ident)
        self.assertEqual(self.command('complete', transition=ident)['status'], 'completed')

    def test_guarded_success_and_nonzero_commit_refresh_head(self):
        for exit_code in (0, 7):
            with self.subTest(exit_code=exit_code), patch.dict(os.environ, {'PEERSLATE_CALLER_REF': self.f.writer, 'CODEX_THREAD_ID': ''}):
                script = "import subprocess,sys; subprocess.run(['git','commit','--allow-empty','-m','guarded'],check=True,stdout=subprocess.DEVNULL); sys.exit(" + str(exit_code) + ")"
                out = LIFECYCLE.command_control_run(self.context, SimpleNamespace(execute=True, task_ref=self.f.writer,
                    lease_token=self.proof['old_token'], command=[sys.executable, '-B', '-c', script]))
                self.assertEqual(out['returncode'], exit_code)
                reg = LIFECYCLE._load_registry(self.context.registry_path)
                record = LIFECYCLE._control_record(self.context, reg)
                self.assertEqual(record['head'], git(Path(record['path']), 'rev-parse', 'HEAD'))
                self.assertEqual(LIFECYCLE.control_lease_token(record), self.proof['old_token'])

    def test_guarded_branch_switch_persists_truthful_fence(self):
        with patch.dict(os.environ, {'PEERSLATE_CALLER_REF': self.f.writer, 'CODEX_THREAD_ID': ''}):
            with self.assertRaises(LIFECYCLE.Refusal):
                LIFECYCLE.command_control_run(self.context, SimpleNamespace(execute=True, task_ref=self.f.writer,
                    lease_token=self.proof['old_token'], command=['git', 'switch', '-c', 'work/unexpected']))
        reg = LIFECYCLE._load_registry(self.context.registry_path)
        failure = reg['control_guard_failure']
        self.assertEqual(failure['expected_branch'], self.f.branch)
        self.assertEqual(failure['observed_branch'], 'work/unexpected')
        with self.assertRaises(LIFECYCLE.Refusal):
            LIFECYCLE.require_control_custody_fence(reg, LIFECYCLE._control_record(self.context, reg),
                task_ref=self.f.writer, lease_token=self.proof['old_token'])
        with self.assertRaises(LIFECYCLE.Refusal):
            self.command('propose')

    def test_completed_history_rejects_revoked_lease_and_duplicate_receipt(self):
        ident = self.accepted()
        self.command('complete', transition=ident)
        reg = LIFECYCLE._load_registry(self.context.registry_path)
        restored = copy.deepcopy(reg)
        record = LIFECYCLE._control_record(self.context, restored)
        record.update(task_ref=self.proof['from_ref'], lease=copy.deepcopy(self.proof['old_lease']))
        with self.assertRaises(LIFECYCLE.Refusal):
            LIFECYCLE.validate_owner_reassignment_registry(restored)
        with self.assertRaises(LIFECYCLE.Refusal):
            LIFECYCLE.require_control_custody_fence(restored, record, task_ref=self.proof['from_ref'], lease_token=self.proof['old_token'])
        duplicate = copy.deepcopy(reg['control_custody_transitions'][0])
        duplicate['id'] = 'f' * 32
        reg['control_custody_transitions'].append(duplicate)
        with self.assertRaises(LIFECYCLE.Refusal):
            LIFECYCLE.validate_owner_reassignment_registry(reg)

    def test_explicit_return_then_release_fresh_acquire_and_package_change(self):
        original = self.f.writer
        ident = self.accepted()
        self.command('complete', transition=ident)
        reg = LIFECYCLE._load_registry(self.context.registry_path)
        record = LIFECYCLE._control_record(self.context, reg)
        self.proof.update(from_ref=self.receiver, to_ref=original,
                          old_lease=copy.deepcopy(record['lease']), old_token=LIFECYCLE.control_lease_token(record))
        self.receiver = original
        returned = self.command('complete', transition=self.accepted())
        with patch.dict(os.environ, {'PEERSLATE_CALLER_REF': original,
                                    'PEERSLATE_CONTROL_LEASE_TOKEN': returned['lease_token'],
                                    'CODEX_THREAD_ID': ''}):
            code, payload = self.f.run('control', '--task-ref', original, '--release', '--base', self.f.main_sha, '--execute')
            self.assertEqual(code, 0, payload)
            code, payload = self.f.run('control', '--task-ref', original, '--package', 'PS-ANOTHER-PACKAGE-001',
                                      '--branch', self.f.branch, '--base', self.f.main_sha, '--execute')
            self.assertEqual(code, 0, payload)
        self.assertNotEqual(payload['lease_token'], returned['lease_token'])
        reg = LIFECYCLE._load_registry(self.context.registry_path)
        LIFECYCLE.validate_owner_reassignment_registry(reg)
        LIFECYCLE.require_control_custody_fence(reg, LIFECYCLE._control_record(self.context, reg),
            task_ref=original, lease_token=payload['lease_token'])

    def test_fresh_receiver_acquisition_can_be_next_transfer_source(self):
        ident = self.accepted()
        out = self.command('complete', transition=ident)
        with patch.dict(os.environ, {'PEERSLATE_CALLER_REF': self.receiver,
                                    'PEERSLATE_CONTROL_LEASE_TOKEN': out['lease_token'],
                                    'CODEX_THREAD_ID': ''}):
            code, payload = self.f.run('control', '--task-ref', self.receiver, '--release', '--base', self.f.main_sha, '--execute')
            self.assertEqual(code, 0, payload)
            code, payload = self.f.run('control', '--task-ref', self.receiver, '--package', 'PS-ANOTHER-PACKAGE-001',
                                      '--branch', self.f.branch, '--base', self.f.main_sha, '--execute')
            self.assertEqual(code, 0, payload)
        self.proof.update(package='PS-ANOTHER-PACKAGE-001', from_ref=self.receiver, to_ref='agent:third-receiver',
                          old_lease=payload['lease'], old_token=payload['lease_token'])
        self.receiver = 'agent:third-receiver'
        self.assertEqual(self.command('complete', transition=self.accepted())['status'], 'completed')

    def test_frozen_clock_reacquisition_always_issues_fresh_token(self):
        from datetime import datetime, timezone
        frozen = datetime(2026, 1, 1, tzinfo=timezone.utc)
        reg = LIFECYCLE._load_registry(self.context.registry_path)
        record = LIFECYCLE._control_record(self.context, reg)
        tokens = [LIFECYCLE.control_lease_token(record)]
        # Execute in process with the real registry lock and Git worktree, while
        # every wall-clock observation returns the same instant.
        with patch.object(LIFECYCLE, 'datetime') as clock:
            clock.now.return_value = frozen
            clock.fromisoformat.side_effect = datetime.fromisoformat
            clock.strptime.side_effect = datetime.strptime
            for _ in range(3):
                args = SimpleNamespace(execute=True, task_ref=self.f.writer, package=self.f.package,
                    base=self.f.main_sha, branch=self.f.branch, purpose='control', include=[], release=True)
                LIFECYCLE.command_control(self.context, args)
                args.release = False
                out = LIFECYCLE.command_control(self.context, args)
                self.assertNotIn(out['lease_token'], tokens)
                reg = LIFECYCLE._load_registry(self.context.registry_path)
                record = LIFECYCLE._control_record(self.context, reg)
                for old in tokens:
                    with self.assertRaises(LIFECYCLE.Refusal):
                        LIFECYCLE.require_control_custody_fence(reg, record, task_ref=self.f.writer, lease_token=old)
                tokens.append(out['lease_token'])

    def test_lease_clock_absence_compatible_and_malformed_fails_closed(self):
        reg = LIFECYCLE._load_registry(self.context.registry_path)
        reg.pop('control_lease_clock', None)
        LIFECYCLE.validate_owner_reassignment_registry(reg)
        for value in (None, '', 0, {}, [], '2026-01-01', '2026-01-01T00:00:00.1Z'):
            with self.subTest(value=value):
                reg['control_lease_clock'] = value
                with self.assertRaises(LIFECYCLE.Refusal):
                    LIFECYCLE.validate_owner_reassignment_registry(reg)

    def test_lost_pending_receiver_supersession_preserves_fence_and_history(self):
        old_receiver = self.receiver
        old_id = self.accepted()
        self.receiver = 'agent:replacement-receiver'
        self.proof.update(to_ref=self.receiver, supersedes='e' * 32,
                          owner_ref='session:owner/replacement', review_ref='agent:review/replacement',
                          quiescence_ref='session:host/replacement')
        with self.assertRaises(LIFECYCLE.Refusal):
            self.command('propose')
        self.proof['supersedes'] = old_id
        proposed = self.command('propose')
        reg = LIFECYCLE._load_registry(self.context.registry_path)
        self.assertEqual([t['state'] for t in reg['control_custody_transitions']], ['superseded', 'proposed'])
        self.assertEqual(reg['control_custody_transitions'][0]['accepted_by'], old_receiver)
        with self.assertRaises(LIFECYCLE.Refusal):
            LIFECYCLE.require_control_custody_fence(reg, LIFECYCLE._control_record(self.context, reg),
                task_ref=self.f.writer, lease_token=self.proof['old_token'])
        with self.assertRaises(LIFECYCLE.Refusal):
            self.command('accept', caller=old_receiver, transition=old_id, acceptance_ref='agent:receiver/acceptance')
        new_id = proposed['transition']['id']
        self.command('accept', transition=new_id, acceptance_ref='agent:replacement/acceptance')
        self.assertEqual(self.command('complete', transition=new_id)['status'], 'completed')
        reg = LIFECYCLE._load_registry(self.context.registry_path)
        self.assertEqual([t['state'] for t in reg['control_custody_transitions']], ['superseded', 'completed'])
        self.assertEqual(LIFECYCLE._control_record(self.context, reg)['task_ref'], self.receiver)

    def test_legacy_shape_and_strict_history(self):
        reg = LIFECYCLE._load_registry(self.context.registry_path)
        LIFECYCLE.validate_control_custody_registry(reg)
        for bad in (None, {}, 'bad'):
            broken = copy.deepcopy(reg)
            broken['control_custody_transitions'] = bad
            with self.assertRaises(LIFECYCLE.Refusal):
                LIFECYCLE.validate_control_custody_registry(broken)


ROOT_SESSION = "01a0783a-f99a-71a1-8124-2e58ec64f06b"
CHILD_SESSION = "01a0783c-0195-7e51-b4e6-56e824c8c1f8"


class LifecycleReportingHookTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="lifecycle-reporting-")
        self.root = Path(self.temporary.name)
        self.context = SimpleNamespace(root=self.root)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @staticmethod
    def readiness_result(status: str = "pass") -> subprocess.CompletedProcess[str]:
        code = 0 if status == "pass" else LIFECYCLE.REFUSAL_EXIT
        return subprocess.CompletedProcess(
            args=[],
            returncode=code,
            stdout=json.dumps(
                {
                    "schema_version": 1,
                    "environment_status": status,
                    "operation_authority": "unproven",
                    "checks": [],
                }
            ),
            stderr="",
        )

    @staticmethod
    def usage_result(status: str = "available") -> subprocess.CompletedProcess[str]:
        code = 0 if status in {"available", "partial"} else LIFECYCLE.REFUSAL_EXIT
        return subprocess.CompletedProcess(
            args=[],
            returncode=code,
            stdout=json.dumps(
                {
                    "schema_version": 1,
                    "status": status,
                    "sessions_selected": 1,
                    "sessions_available": 1 if code == 0 else 0,
                }
            ),
            stderr="",
        )

    def test_successful_ensure_runs_readiness_after_command_and_preserves_payload(self):
        events: list[str] = []

        def ensured(_context, _args):
            events.append("custody_complete")
            return {"status": "created", "path": str(self.root), "head": "a" * 40}

        def ran(command, **kwargs):
            events.append("report_started")
            self.assertEqual(command[1], "-B")
            self.assertEqual(command[-2:], ["--format", "json"])
            self.assertEqual(kwargs["timeout"], LIFECYCLE.REPORT_TIMEOUT_SECONDS)
            self.assertEqual(kwargs["env"]["PYTHONDONTWRITEBYTECODE"], "1")
            return self.readiness_result()

        with (
            patch.object(LIFECYCLE, "_repo_context", return_value=self.context),
            patch.object(LIFECYCLE, "command_ensure", side_effect=ensured),
            patch.object(LIFECYCLE.subprocess, "run", side_effect=ran),
        ):
            code, payload = invoke(
                "--repo",
                str(self.root),
                "ensure",
                "--package",
                "PS-TEST-001",
                "--task-ref",
                f"session:{ROOT_SESSION}",
                "--execute",
            )

        self.assertEqual(code, 0)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["head"], "a" * 40)
        self.assertEqual(payload["environment_readiness"]["environment_status"], "pass")
        self.assertEqual(events, ["custody_complete", "report_started"])

    def test_refused_ensure_and_audit_never_run_optional_reporting(self):
        with (
            patch.object(LIFECYCLE, "_repo_context", return_value=self.context),
            patch.object(
                LIFECYCLE,
                "command_ensure",
                side_effect=LIFECYCLE.Refusal("synthetic refusal"),
            ),
            patch.object(LIFECYCLE, "command_audit", return_value={"status": "ok"}),
            patch.object(LIFECYCLE.subprocess, "run") as runner,
        ):
            refused_code, refused = invoke(
                "--repo",
                str(self.root),
                "ensure",
                "--package",
                "PS-TEST-001",
                "--task-ref",
                f"session:{ROOT_SESSION}",
                "--execute",
            )
            audit_code, audit = invoke("--repo", str(self.root), "audit")

        self.assertEqual(refused_code, LIFECYCLE.REFUSAL_EXIT)
        self.assertFalse(refused["ok"])
        self.assertNotIn("environment_readiness", refused)
        self.assertEqual(audit_code, 0)
        self.assertTrue(audit["ok"])
        self.assertNotIn("environment_readiness", audit)
        self.assertNotIn("usage_summary", audit)
        runner.assert_not_called()

    def test_incomplete_finalize_never_runs_usage_reporting(self):
        custody = {
            "status": "incomplete",
            "task_ref": f"session:{ROOT_SESSION}",
            "retained": [{"path": "bounded", "blockers": ["synthetic"]}],
        }
        with (
            patch.object(LIFECYCLE, "_repo_context", return_value=self.context),
            patch.object(
                LIFECYCLE,
                "command_finalize_task",
                return_value=(custody, LIFECYCLE.REFUSAL_EXIT),
            ),
            patch.object(LIFECYCLE.subprocess, "run") as runner,
        ):
            code, payload = invoke(
                "--repo",
                str(self.root),
                "finalize-task",
                "--task-ref",
                f"session:{ROOT_SESSION}",
                "--execute",
            )
        self.assertEqual(code, LIFECYCLE.REFUSAL_EXIT)
        self.assertFalse(payload["ok"])
        self.assertNotIn("usage_summary", payload)
        runner.assert_not_called()

    def test_successful_finalize_selects_root_and_explicit_child_once(self):
        commands: list[list[str]] = []

        def ran(command, **_kwargs):
            commands.append(command)
            return self.usage_result()

        with (
            patch.object(LIFECYCLE, "_repo_context", return_value=self.context),
            patch.object(
                LIFECYCLE,
                "command_finalize_task",
                return_value=(
                    {"status": "complete", "task_ref": f"session:{ROOT_SESSION}"},
                    0,
                ),
            ),
            patch.object(LIFECYCLE.subprocess, "run", side_effect=ran),
        ):
            code, payload = invoke(
                "--repo",
                str(self.root),
                "finalize-task",
                "--task-ref",
                f"session:{ROOT_SESSION}",
                "--usage-session-id",
                ROOT_SESSION,
                "--usage-session-id",
                CHILD_SESSION,
                "--usage-session-id",
                CHILD_SESSION,
                "--execute",
            )

        self.assertEqual(code, 0)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["status"], "complete")
        self.assertEqual(payload["usage_summary"]["status"], "available")
        command = commands[0]
        selected = [
            command[index + 1]
            for index, value in enumerate(command)
            if value == "--session-id"
        ]
        self.assertEqual(selected, [ROOT_SESSION, CHILD_SESSION])

    def test_timeout_and_nonzero_pass_claim_stay_non_gating_and_unavailable(self):
        custody = {"status": "complete", "task_ref": f"session:{ROOT_SESSION}"}
        cases = (
            subprocess.TimeoutExpired(cmd=["python"], timeout=1),
            RuntimeError("sensitive unexpected helper failure"),
            subprocess.CompletedProcess(
                args=[],
                returncode=9,
                stdout=json.dumps({"status": "available"}),
                stderr="sensitive detail must not surface",
            ),
        )
        for failure in cases:
            with self.subTest(failure=type(failure).__name__):
                runner_patch = (
                    patch.object(LIFECYCLE.subprocess, "run", side_effect=failure)
                    if isinstance(failure, BaseException)
                    else patch.object(LIFECYCLE.subprocess, "run", return_value=failure)
                )
                with (
                    patch.object(LIFECYCLE, "_repo_context", return_value=self.context),
                    patch.object(
                        LIFECYCLE,
                        "command_finalize_task",
                        return_value=(custody.copy(), 0),
                    ),
                    runner_patch,
                ):
                    before = sorted(
                        path.relative_to(self.root) for path in self.root.rglob("*")
                    )
                    code, payload = invoke(
                        "--repo",
                        str(self.root),
                        "finalize-task",
                        "--task-ref",
                        f"session:{ROOT_SESSION}",
                        "--execute",
                    )
                    after = sorted(
                        path.relative_to(self.root) for path in self.root.rglob("*")
                    )
                    self.assertEqual(code, 0)
                    self.assertTrue(payload["ok"])
                    self.assertEqual(payload["status"], "complete")
                    self.assertEqual(payload["usage_summary"]["status"], "unavailable")
                    self.assertEqual(before, after)
                    self.assertNotIn("sensitive", json.dumps(payload))

    def test_non_session_task_ref_reports_honest_unavailable_without_scanning(self):
        with (
            patch.object(LIFECYCLE, "_repo_context", return_value=self.context),
            patch.object(
                LIFECYCLE,
                "command_finalize_task",
                return_value=({"status": "complete", "task_ref": "task:test"}, 0),
            ),
            patch.object(LIFECYCLE.subprocess, "run") as runner,
        ):
            code, payload = invoke(
                "--repo",
                str(self.root),
                "finalize-task",
                "--task-ref",
                "task:test",
                "--execute",
            )
        self.assertEqual(code, 0)
        self.assertEqual(
            payload["usage_summary"],
            {"status": "unavailable", "reason": "exact_session_id_not_selected"},
        )
        runner.assert_not_called()


class SafeCustodyRegistryTests(unittest.TestCase):
    def claim_path_fixture(self):
        from scripts import delivery_preflight as preflight

        fixture = RepositoryFixture()
        self.addCleanup(fixture.temporary.cleanup)
        claim_path = preflight.claim_relative_path(fixture.package)
        claim = {
            "schema_version": 1,
            "package": fixture.package,
            "state": "active",
            "outcome": "Exercise authoritative claim path validation in a temporary Git repository.",
            "assignment": "implementation",
            "writer_ref": fixture.writer,
            "branch": fixture.branch,
            "delivery_path": "Protected",
            "repository_authority": "through_merge",
            "production_authority": "withheld",
            "activated_from_main": fixture.main_sha,
            "owner_outcome_ref": "task:owner/claim-path-fixture",
            "surfaces": [
                claim_path,
                preflight.evidence_relative_path(fixture.package),
                preflight.receipt_relative_path(fixture.package),
                "sample.txt",
            ],
            "evidence_surfaces": [preflight.evidence_relative_path(fixture.package)],
            "domains": ["testing:lifecycle:claim-path-fixture"],
            "review_requirement": "independent",
            "handoff": None,
            "checkpoint_sha": None,
            "merged_sha": None,
            "closed_at": None,
        }
        (fixture.repo / claim_path).write_text(
            json.dumps(claim, indent=2) + "\n", encoding="utf-8"
        )
        (fixture.repo / "docs/governance/CURRENT_LANES.json").write_bytes(
            (ROOT / "docs/governance/CURRENT_LANES.json").read_bytes()
        )
        (fixture.repo / "scripts/delivery_preflight.py").write_bytes(
            (ROOT / "scripts/delivery_preflight.py").read_bytes()
        )
        (fixture.repo / "scripts/worktree_lifecycle.py").write_bytes(
            SCRIPT.read_bytes()
        )
        self.publish_claim_path_fixture(fixture)
        context = LIFECYCLE._repo_context(fixture.repo)
        return fixture, context, self.registry(), claim, preflight

    def publish_claim_path_fixture(self, fixture):
        git(fixture.repo, "add", "-A")
        git(fixture.repo, "commit", "-m", "publish authoritative claim fixture")
        git(fixture.repo, "push", "origin", "main")
        LIFECYCLE._fetch_origin_main(LIFECYCLE._repo_context(fixture.repo))

    def test_authoritative_claim_path_reaches_actual_validator(self):
        fixture, context, registry, claim, preflight = self.claim_path_fixture()
        raw = LIFECYCLE._strict_live_claims(context)
        self.assertEqual([claim], raw)
        with patch.object(
            preflight, "validate_claim_set", wraps=preflight.validate_claim_set
        ) as validator:
            index = LIFECYCLE._require_safe_custody_capability(context, registry)
        self.assertEqual(4, index["schema_version"])
        validator.assert_called_once()
        validated = validator.call_args.args[0]
        expected_path = preflight.claim_relative_path(fixture.package)
        self.assertEqual([expected_path], list(validated))
        self.assertEqual(expected_path, validated[expected_path]["_relative_path"])
        self.assertEqual([], preflight.validate_claim_set(validated))

    def test_authoritative_claim_path_refuses_malformed_json(self):
        fixture, context, registry, _claim, preflight = self.claim_path_fixture()
        path = fixture.repo / preflight.claim_relative_path(fixture.package)
        path.write_text("{not-json\n", encoding="utf-8")
        self.publish_claim_path_fixture(fixture)
        with patch.object(
            preflight, "validate_claim_set", wraps=preflight.validate_claim_set
        ) as validator:
            with self.assertRaisesRegex(LIFECYCLE.Refusal, "invalid JSON"):
                LIFECYCLE._require_safe_custody_capability(context, registry)
        validator.assert_not_called()

    def test_authoritative_claim_path_refuses_malformed_claim_in_actual_validator(self):
        fixture, context, registry, claim, preflight = self.claim_path_fixture()
        claim["review_requirement"] = "self"
        (fixture.repo / preflight.claim_relative_path(fixture.package)).write_text(
            json.dumps(claim, indent=2) + "\n", encoding="utf-8"
        )
        self.publish_claim_path_fixture(fixture)
        with patch.object(
            preflight, "validate_claim_set", wraps=preflight.validate_claim_set
        ) as validator:
            with self.assertRaisesRegex(LIFECYCLE.Refusal, "claim set is invalid"):
                LIFECYCLE._require_safe_custody_capability(context, registry)
        validator.assert_called_once()
        self.assertTrue(
            any("Protected claims require independent review" in error
                for error in preflight.validate_claim_set(validator.call_args.args[0]))
        )

    def test_authoritative_claim_path_refuses_wrong_filename_before_mapping(self):
        fixture, context, registry, _claim, preflight = self.claim_path_fixture()
        original = preflight.claim_relative_path(fixture.package)
        wrong = preflight.claim_relative_path("PS-TEST-WRONG-FILENAME-001")
        git(fixture.repo, "mv", original, wrong)
        self.publish_claim_path_fixture(fixture)
        with patch.object(
            preflight, "validate_claim_set", wraps=preflight.validate_claim_set
        ) as validator:
            with self.assertRaisesRegex(LIFECYCLE.Refusal, "filename does not match package"):
                LIFECYCLE._require_safe_custody_capability(context, registry)
        validator.assert_not_called()

    def test_authoritative_claim_path_overwrites_forged_payload_path(self):
        fixture, context, registry, claim, preflight = self.claim_path_fixture()
        claim["_relative_path"] = preflight.claim_relative_path("PS-FORGED-001")
        (fixture.repo / preflight.claim_relative_path(fixture.package)).write_text(
            json.dumps(claim, indent=2) + "\n", encoding="utf-8"
        )
        self.publish_claim_path_fixture(fixture)
        self.assertEqual([claim], LIFECYCLE._strict_live_claims(context))
        with patch.object(
            preflight, "validate_claim_set", wraps=preflight.validate_claim_set
        ) as validator:
            LIFECYCLE._require_safe_custody_capability(context, registry)
        validated = validator.call_args.args[0]
        actual = preflight.claim_relative_path(fixture.package)
        self.assertEqual(actual, validated[actual]["_relative_path"])

    def test_authoritative_claim_path_rejects_duplicate_package_before_mapping(self):
        fixture, context, registry, claim, preflight = self.claim_path_fixture()
        duplicate = preflight.claim_relative_path("PS-TEST-ZZZ-DUPLICATE-001")
        (fixture.repo / duplicate).write_text(
            json.dumps(claim, indent=2) + "\n", encoding="utf-8"
        )
        self.publish_claim_path_fixture(fixture)
        with patch.object(
            preflight, "validate_claim_set", wraps=preflight.validate_claim_set
        ) as validator:
            with self.assertRaisesRegex(LIFECYCLE.Refusal, "duplicate authoritative package claim"):
                LIFECYCLE._require_safe_custody_capability(context, registry)
        validator.assert_not_called()

    def install_accepted_safe_custody_tools(
        self, fixture, *, lifecycle_bytes=None
    ):
        (fixture.repo / "scripts" / "delivery_preflight.py").write_bytes(
            (ROOT / "scripts" / "delivery_preflight.py").read_bytes()
        )
        (fixture.repo / "scripts" / "worktree_lifecycle.py").write_bytes(
            SCRIPT.read_bytes() if lifecycle_bytes is None else lifecycle_bytes
        )
        git(fixture.repo, "add", "scripts/delivery_preflight.py", "scripts/worktree_lifecycle.py")
        git(fixture.repo, "commit", "-m", "install accepted safe-custody tools")
        git(fixture.repo, "push", "origin", "main")
        fixture.main_sha = git(fixture.repo, "rev-parse", "HEAD")

    def registry(self):
        registry = {
            "schema_version": 2,
            "safe_custody": {
                "schema_version": 1,
                "migration": {
                    "from_schema": 1,
                    "to_schema": 2,
                    "before_sha256": "1" * 64,
                    "after_sha256": "",
                    "migrated_at": "2026-09-13T00:00:00Z",
                },
                "scope_releases": [],
                "reconciliations": [],
                "package_blocks": {},
            },
        }
        LIFECYCLE._seal_safe_custody_after_sha256(registry)
        return registry

    def seal(self, registry):
        LIFECYCLE._seal_safe_custody_after_sha256(registry)
        return registry

    def owner_reassignment_schema_two_fixture(self, label):
        fixture, context, _registry, _claim, _preflight = self.claim_path_fixture()
        fixture.main_sha = git(fixture.repo, "rev-parse", "HEAD")
        git(
            fixture.repo, "push", "origin",
            f"{fixture.main_sha}:refs/heads/{fixture.branch}",
        )
        fixture.initialize()
        code, source = fixture.run(
            "ensure", "--package", fixture.package,
            "--task-ref", fixture.writer, "--execute",
        )
        self.assertEqual(code, 0, source)
        receiver = "agent:schema-two-receiver"
        code, control = fixture.run(
            "control", "--package", fixture.package,
            "--task-ref", receiver,
            "--branch", f"work/2026-09-19-delivery-owner-reassignment-{label}",
            "--base", "origin/main", "--execute",
        )
        self.assertEqual(code, 0, control)
        registry = json.loads(fixture.registry_path.read_text(encoding="utf-8"))
        registry["schema_version"] = LIFECYCLE.SAFE_CUSTODY_SCHEMA_VERSION
        registry["safe_custody"] = self.registry()["safe_custody"]
        self.seal(registry)
        fixture.registry_path.write_text(json.dumps(registry) + "\n", encoding="utf-8")
        successor = f"work/2026-09-19-schema-two-{label}"
        return fixture, context, Path(source["path"]), Path(control["path"]), receiver, successor

    def prepare_schema_two_successor(
        self, fixture, control_path, receiver, successor, checkpoint, *,
        source_unavailable_ref=None,
    ):
        arguments = [
            "prepare-owner-reassignment", "--package", fixture.package,
            "--task-ref", receiver, "--successor-branch", successor,
            "--expected-checkpoint", checkpoint,
            "--owner-authorization-ref", "session:owner/schema-two-replacement",
        ]
        if source_unavailable_ref:
            arguments.extend(("--source-unavailable-ref", source_unavailable_ref))
        return fixture.run(*arguments, "--execute", cwd=control_path)

    def test_schema_two_owner_reassignment_prepares_successor(self):
        fixture, _context, source_path, control_path, receiver, successor = (
            self.owner_reassignment_schema_two_fixture("normal")
        )
        code, prepared = self.prepare_schema_two_successor(
            fixture, control_path, receiver, successor, fixture.main_sha,
        )
        self.assertEqual(code, 0, prepared)
        self.assertEqual("successor_prepared", prepared["status"])
        self.assertFalse(prepared["source_registry_head_reconciled"])
        self.assertEqual(fixture.main_sha, git(source_path, "rev-parse", "HEAD"))
        self.assertEqual(
            fixture.main_sha,
            git(fixture.repo, "ls-remote", "origin", f"refs/heads/{successor}").split()[0],
        )
        registry = LIFECYCLE._load_registry(fixture.registry_path)
        self.assertIsNone(registry["pending"])
        self.assertEqual("completed", registry["owner_reassignment_preparations"][0]["status"])

    def test_schema_two_owner_reassignment_reconciles_stale_source_head(self):
        fixture, _context, source_path, control_path, receiver, successor = (
            self.owner_reassignment_schema_two_fixture("stale-head")
        )
        (source_path / "sample.txt").write_text("source advanced\n", encoding="utf-8")
        git(source_path, "add", "sample.txt")
        git(source_path, "commit", "-m", "advance source")
        checkpoint = git(source_path, "rev-parse", "HEAD")
        git(source_path, "push", "origin", fixture.branch)
        code, prepared = self.prepare_schema_two_successor(
            fixture, control_path, receiver, successor, checkpoint,
            source_unavailable_ref="session:orchestrator/source-unavailable-schema-two",
        )
        self.assertEqual(code, 0, prepared)
        self.assertTrue(prepared["source_registry_head_reconciled"])
        registry = LIFECYCLE._load_registry(fixture.registry_path)
        source_record = next(
            record for record in registry["worktrees"]
            if record.get("kind") == "durable" and record.get("package") == fixture.package
        )
        self.assertEqual(checkpoint, source_record["head"])
        self.assertEqual(fixture.main_sha, source_record["previous_head"])
        self.assertEqual(
            "session:orchestrator/source-unavailable-schema-two",
            source_record["owner_reassignment_head_reconciliation"]["source_unavailable_ref"],
        )

    def test_schema_two_owner_reassignment_recovers_interrupted_preparation(self):
        fixture, context, _source_path, control_path, receiver, successor = (
            self.owner_reassignment_schema_two_fixture("interrupted")
        )
        arguments = SimpleNamespace(
            execute=True,
            package=fixture.package,
            task_ref=receiver,
            successor_branch=successor,
            expected_checkpoint=fixture.main_sha,
            owner_authorization_ref="session:owner/schema-two-replacement",
            source_unavailable_ref=None,
        )
        original_git_result = LIFECYCLE._git_result

        def crash_before_push(root: Path, *git_arguments: str):
            if git_arguments[:2] == ("push", "--porcelain"):
                raise RuntimeError("simulated process death before successor push")
            return original_git_result(root, *git_arguments)

        with patch.object(LIFECYCLE.Path, "cwd", return_value=control_path), patch.object(
            LIFECYCLE, "_git_result", side_effect=crash_before_push
        ):
            with self.assertRaisesRegex(RuntimeError, "simulated process death"):
                LIFECYCLE.command_prepare_owner_reassignment(context, arguments)
        pending = LIFECYCLE._load_registry(fixture.registry_path)
        self.assertIsNotNone(pending["pending"])
        code, recovered = self.prepare_schema_two_successor(
            fixture, control_path, receiver, successor, fixture.main_sha,
        )
        self.assertEqual(LIFECYCLE.REFUSAL_EXIT, code, recovered)
        self.assertIn("prior pending operation was reconciled", recovered["error"])
        self.assertIsNone(LIFECYCLE._load_registry(fixture.registry_path)["pending"])
        self.assertEqual(
            "", git(fixture.repo, "ls-remote", "origin", f"refs/heads/{successor}"),
        )
        code, prepared = self.prepare_schema_two_successor(
            fixture, control_path, receiver, successor, fixture.main_sha,
        )
        self.assertEqual(code, 0, prepared)
        self.assertEqual("successor_prepared", prepared["status"])

    def test_schema_two_owner_reassignment_refuses_unsealed_registry(self):
        fixture, _context, _source_path, control_path, receiver, successor = (
            self.owner_reassignment_schema_two_fixture("invalid-seal")
        )
        registry = json.loads(fixture.registry_path.read_text(encoding="utf-8"))
        registry["safe_custody"]["migration"]["after_sha256"] = "0" * 64
        fixture.registry_path.write_text(json.dumps(registry) + "\n", encoding="utf-8")
        before = fixture.registry_path.read_bytes()
        code, refused = self.prepare_schema_two_successor(
            fixture, control_path, receiver, successor, fixture.main_sha,
        )
        self.assertEqual(LIFECYCLE.REFUSAL_EXIT, code, refused)
        self.assertIn("after_sha256 does not match", refused["error"])
        self.assertEqual(before, fixture.registry_path.read_bytes())
        self.assertEqual(
            "", git(fixture.repo, "ls-remote", "origin", f"refs/heads/{successor}"),
        )

    def reconciliation(self, *, phase="prepared"):
        order = ["prepared", "merging", "resolved", "committed", "pushed"]
        phases = order[: order.index(phase) + 1] if phase in order else [*order, phase]
        return {
            "operation_id": "a" * 64,
            "package": "PS-TEST-001",
            "task_ref": "task:test-writer",
            "worktree": str(ROOT),
            "branch": "work/2026-09-13-test",
            "source_checkpoint": "1" * 40,
            "target_main": "2" * 40,
            "authoritative_claim_sha256": "3" * 64,
            "allowed_conflict_paths": ["owned/file.py"],
            "nonconflicted_index_sha256": (
                None if phase in {"prepared", "merging", "aborted"} else "7" * 64
            ),
            "preoperation_tree": "4" * 40,
            "preoperation_ref": "1" * 40,
            "phase": phase,
            "expected_tree": "5" * 40 if phase not in {"prepared", "merging", "aborted"} else None,
            "result_sha": "6" * 40 if phase in {"committed", "pushed", "completed", "refresh_required"} else None,
            "remote_before": "1" * 40,
            "started_at": "2026-09-13T00:00:00Z",
            "updated_at": "2026-09-13T00:00:00Z",
            "history": [
                {"phase": item, "at": "2026-09-13T00:00:00Z"}
                for item in phases
            ],
            "supersedes_operation_id": None,
        }

    def test_reconciliation_honors_directory_surfaces_but_not_fixed_controls(self):
        claim = {
            "package": "PS-TEST-001",
            "surfaces": [
                "owned",
                "docs/governance/lane_claims/PS-TEST-001.json",
                "docs/governance/lane_claims/evidence/PS-TEST-001.md",
                "docs/governance/lane_claims/receipts/PS-TEST-001.json",
            ],
        }
        self.assertTrue(
            LIFECYCLE._reconciliation_path_is_owned("owned/nested/file.py", claim)
        )
        self.assertFalse(
            LIFECYCLE._reconciliation_path_is_owned("owned-sibling/file.py", claim)
        )
        for fixed in claim["surfaces"][1:]:
            with self.subTest(fixed=fixed):
                self.assertFalse(
                    LIFECYCLE._reconciliation_path_is_owned(fixed, claim)
                )

    def reconciliation_git_fixture(
        self, *, unowned_conflict=False, owned_conflict=False
    ):
        temporary = tempfile.TemporaryDirectory(prefix="safe-custody-reconcile-")
        self.addCleanup(temporary.cleanup)
        base = Path(temporary.name)
        repo = base / "repo"
        remote = base / "origin.git"
        publisher = base / "publisher"
        repo.mkdir()
        git(base, "init", "--bare", str(remote))
        git(repo, "init", "--initial-branch=main")
        git(repo, "config", "user.email", "tests@peerslate.invalid")
        git(repo, "config", "user.name", "PeerSlate Tests")
        git(repo, "config", "core.autocrlf", "false")
        branch = "work/2026-09-13-safe-custody-reconcile"
        package = "PS-TEST-001"
        task_ref = "task:test-writer"
        claim = {
            "package": package,
            "state": "active",
            "writer_ref": task_ref,
            "branch": branch,
            "surfaces": ["owned.txt", "owned-stable.txt"],
        }
        claim_path = repo / "docs" / "governance" / "lane_claims" / f"{package}.json"
        claim_path.parent.mkdir(parents=True)
        claim_path.write_text(json.dumps(claim) + "\n", encoding="utf-8")
        (repo / "owned.txt").write_text("base\n", encoding="utf-8")
        (repo / "owned-stable.txt").write_text("base\n", encoding="utf-8")
        (repo / "unowned.txt").write_text("base\n", encoding="utf-8")
        git(repo, "add", ".")
        git(repo, "commit", "-m", "base")
        git(repo, "remote", "add", "origin", str(remote))
        git(repo, "push", "-u", "origin", "main")
        git(repo, "checkout", "-b", branch)
        (repo / "owned.txt").write_text("candidate\n", encoding="utf-8")
        if unowned_conflict:
            (repo / "unowned.txt").write_text("candidate conflict\n", encoding="utf-8")
        git(repo, "add", ".")
        git(repo, "commit", "-m", "candidate")
        source = git(repo, "rev-parse", "HEAD")
        git(repo, "push", "-u", "origin", branch)
        git(base, "clone", "--branch", "main", str(remote), str(publisher))
        git(publisher, "config", "user.email", "publisher@peerslate.invalid")
        git(publisher, "config", "user.name", "PeerSlate Publisher")
        (publisher / "unowned.txt").write_text("main change\n", encoding="utf-8")
        if owned_conflict:
            (publisher / "owned.txt").write_text("main conflict\n", encoding="utf-8")
        git(publisher, "add", ".")
        git(publisher, "commit", "-m", "advance main")
        target = git(publisher, "rev-parse", "HEAD")
        git(publisher, "push", "origin", "main")
        git(repo, "fetch", "origin", "main", branch)
        context = LIFECYCLE._repo_context(repo)
        record = self.reconciliation()
        record.update(
            {
                "package": package,
                "task_ref": task_ref,
                "worktree": str(repo),
                "branch": branch,
                "source_checkpoint": source,
                "target_main": target,
                "authoritative_claim_sha256": LIFECYCLE._canonical_json_sha256(claim),
                "allowed_conflict_paths": [],
                "preoperation_tree": git(repo, "rev-parse", f"{source}^{{tree}}"),
                "preoperation_ref": source,
                "phase": "prepared",
                "expected_tree": None,
                "result_sha": None,
                "remote_before": source,
                "history": [{"phase": "prepared", "at": "2026-09-13T00:00:00Z"}],
            }
        )
        registry = self.registry()
        registry["worktrees"] = [{
            "path": str(repo), "kind": "durable", "state": "active",
            "package": package, "task_ref": task_ref, "branch": branch,
            "head": source, "updated_at": "2026-09-13T00:00:00Z",
        }]
        registry["safe_custody"]["reconciliations"] = [record]
        registry["safe_custody"]["package_blocks"] = {
            package.casefold(): {
                "kind": "reconcile_main", "operation_id": record["operation_id"]
            }
        }
        return repo, publisher, context, registry, record, claim, source, target, branch

    def test_schema_one_remains_readable_but_new_operations_are_fenced(self):
        registry = {
            "schema_version": 1,
            "initialized_at": "2026-09-13T00:00:00Z",
            "managed_root": str(ROOT),
            "evidence_root": str(ROOT.parent),
            "worktrees": [],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "registry.json"
            path.write_text(json.dumps(registry), encoding="utf-8")
            loaded = LIFECYCLE._load_registry(path)
        self.assertEqual(1, loaded["schema_version"])
        with self.assertRaisesRegex(LIFECYCLE.Refusal, "require registry schema 2"):
            LIFECYCLE.validate_safe_custody_registry(loaded)

    def test_schema_one_cli_refuses_new_operations_before_registry_mutation(self):
        fixture = RepositoryFixture()
        self.addCleanup(fixture.temporary.cleanup)
        fixture.initialize()
        before = fixture.registry_path.read_bytes()
        for arguments in (
            (
                "scope-release", "prepare", "--package", fixture.package,
                "--task-ref", fixture.writer, "--execute",
            ),
            (
                "reconcile-main", "start", "--package", fixture.package,
                "--task-ref", fixture.writer, "--execute",
            ),
            ):
            code, payload = fixture.run(
                *arguments,
                environment_overrides={"PEERSLATE_CALLER_REF": fixture.writer},
            )
            self.assertEqual(LIFECYCLE.REFUSAL_EXIT, code, payload)
            self.assertIn("registry schema 2", payload["error"])
            self.assertEqual(before, fixture.registry_path.read_bytes())

    def test_registry_migration_preserves_inventory_and_exact_backup(self):
        fixture = RepositoryFixture()
        self.addCleanup(fixture.temporary.cleanup)
        self.install_accepted_safe_custody_tools(fixture)
        fixture.initialize()
        code, payload = fixture.run(
            "ensure", "--package", fixture.package,
            "--task-ref", fixture.writer, "--execute",
        )
        self.assertEqual(0, code, payload)
        ensured_record = next(
            record
            for record in LIFECYCLE._load_registry(fixture.registry_path)["worktrees"]
            if record.get("kind") == "durable"
            and record.get("package") == fixture.package
        )
        git(
            Path(ensured_record["path"]),
            "push", "origin", f"HEAD:refs/heads/{fixture.branch}",
        )
        before_bytes = fixture.registry_path.read_bytes()
        before = json.loads(before_bytes)
        durable = [
            record for record in before["worktrees"]
            if record.get("kind") == "durable" and record.get("state") == "active"
        ]
        qualification = {
            "schema_version": 1,
            "owner_authorization_ref": "task:owner/migrate-safe-custody",
            "qualified_at": "2026-09-13T00:00:00Z",
            "writers": [
                {
                    "package": record["package"],
                    "task_ref": record["task_ref"],
                    "branch": record["branch"],
                    "head": record["head"],
                    "quiescence_ref": "task:writer/quiescent",
                }
                for record in durable
            ],
        }
        qualification_path = fixture.base / "qualification.json"
        qualification_path.write_text(json.dumps(qualification), encoding="utf-8")
        code, payload = fixture.run(
            "migrate-registry-v2",
            "--task-ref", "task:migration-owner",
            "--qualification-file", str(qualification_path),
            "--execute",
            environment_overrides={"PEERSLATE_CALLER_REF": "task:migration-owner"},
        )
        self.assertEqual(0, code, payload)
        after = json.loads(fixture.registry_path.read_text(encoding="utf-8"))
        self.assertEqual(2, after["schema_version"])
        preserved_after = copy.deepcopy(after)
        preserved_before = copy.deepcopy(before)
        preserved_after.pop("safe_custody")
        preserved_after["schema_version"] = 1
        self.assertEqual(preserved_before, preserved_after)
        backup = Path(payload["backup"])
        self.assertEqual(before_bytes, backup.read_bytes())
        self.assertEqual(hashlib.sha256(before_bytes).hexdigest(), payload["before_sha256"])
        LIFECYCLE.validate_safe_custody_registry(after)
        exact_backup = backup.read_bytes()
        backup.unlink()
        migrated_bytes_for_recovery = fixture.registry_path.read_bytes()
        code, missing_backup = fixture.run(
            "migrate-registry-v2",
            "--task-ref", "task:migration-owner",
            "--qualification-file", str(qualification_path),
            "--execute",
            environment_overrides={"PEERSLATE_CALLER_REF": "task:migration-owner"},
        )
        self.assertEqual(LIFECYCLE.REFUSAL_EXIT, code, missing_backup)
        self.assertIn("exact deterministic schema-1 backup", missing_backup["error"])
        self.assertEqual(migrated_bytes_for_recovery, fixture.registry_path.read_bytes())
        backup.write_bytes(exact_backup + b"tampered")
        code, changed_backup = fixture.run(
            "migrate-registry-v2",
            "--task-ref", "task:migration-owner",
            "--qualification-file", str(qualification_path),
            "--execute",
            environment_overrides={"PEERSLATE_CALLER_REF": "task:migration-owner"},
        )
        self.assertEqual(LIFECYCLE.REFUSAL_EXIT, code, changed_backup)
        self.assertIn("exact deterministic schema-1 backup", changed_backup["error"])
        self.assertEqual(migrated_bytes_for_recovery, fixture.registry_path.read_bytes())
        backup.write_bytes(exact_backup)
        old_script = fixture.base / "pre_safe_custody_lifecycle.py"
        old_script.write_text(
            git(
                ROOT,
                "show",
                f"{PRE_SAFE_CUSTODY_REF}:{COMPAT_FIXTURE['clients']['lifecycle']['path']}",
            ),
            encoding="utf-8",
        )
        migrated_bytes = fixture.registry_path.read_bytes()
        durable_record = durable[0]
        historical_path = fixture.base / "historical-compatibility-target"
        entrypoints = {
            "init": (
                "init", "--task-ref", fixture.writer,
                "--managed-root", str(fixture.managed),
                "--evidence-root", str(fixture.evidence), "--execute",
            ),
            "adopt": (
                "adopt", "--package", fixture.package,
                "--path", durable_record["path"],
                "--task-ref", fixture.writer, "--execute",
            ),
            "ensure": (
                "ensure", "--package", fixture.package,
                "--task-ref", fixture.writer, "--execute",
            ),
            "control": (
                "control", "--task-ref", fixture.writer,
                "--package", fixture.package, "--execute",
            ),
            "caller-context": (
                "caller-context", "register", "--task-ref", fixture.writer,
                "--package", fixture.package, "--receiver-ref", "task:receiver",
                "--owner-authorization-ref", "task:owner", "--lease-token", "token",
                "--execute",
            ),
            "control-custody": (
                "control-custody", "propose", "--task-ref", fixture.writer,
                "--execute",
            ),
            "control-run": (
                "control-run", "--task-ref", fixture.writer,
                "--lease-token", "token", "--execute", "--",
                sys.executable, "-c", "pass",
            ),
            "prepare-owner-reassignment": (
                "prepare-owner-reassignment", "--package", fixture.package,
                "--task-ref", "task:successor",
                "--successor-branch", "work/2026-09-13-compat-successor",
                "--expected-checkpoint", durable_record["head"],
                "--owner-authorization-ref", "task:owner", "--execute",
            ),
            "verify": (
                "verify", "--package", fixture.package,
                "--candidate-sha", durable_record["head"],
                "--task-ref", fixture.writer, "--runtime-required", "--ephemeral",
                "--", sys.executable, "-c", "pass",
            ),
            "retire": (
                "retire", "--path", durable_record["path"],
                "--task-ref", fixture.writer,
                "--expected-head", durable_record["head"], "--execute",
            ),
            "retire-closed-custody": (
                "retire-closed-custody", "--cleanup-package", "PS-CLEANUP-001",
                "--task-ref", "task:cleanup", "--target-package", fixture.package,
                "--path", durable_record["path"], "--branch", fixture.branch,
                "--source-task-ref", fixture.writer,
                "--expected-head", durable_record["head"],
                "--owner-authorization-ref", "task:owner",
                "--source-unavailable-ref", "task:unavailable", "--execute",
            ),
            "retire-historical": (
                "retire-historical", "--cleanup-package", "PS-CLEANUP-001",
                "--task-ref", "task:cleanup", "--path", str(historical_path),
                "--branch", "work/2026-09-13-historical-compat",
                "--expected-head", fixture.main_sha,
                "--owner-authorization-ref", "task:owner", "--execute",
            ),
            "finalize-task": (
                "finalize-task", "--task-ref", fixture.writer, "--execute",
            ),
            "evidence-path": (
                "evidence-path", "--package", fixture.package,
                "--task-ref", fixture.writer,
                "--storage-class", "ephemeral_same_task",
                "--byte-budget", "1", "--label", "compatibility", "--execute",
            ),
        }
        for name, arguments in entrypoints.items():
            with self.subTest(entrypoint=name):
                result = subprocess.run(
                    [
                        sys.executable, "-B", str(old_script),
                        "--repo", str(fixture.repo), *arguments,
                    ],
                    text=True,
                    encoding="utf-8",
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                )
                self.assertEqual(
                    LIFECYCLE.REFUSAL_EXIT, result.returncode,
                    result.stdout or result.stderr,
                )
                self.assertIn(
                    COMPAT_FIXTURE["clients"]["lifecycle"]["expected_error"],
                    result.stdout,
                )
                self.assertEqual(migrated_bytes, fixture.registry_path.read_bytes())

    def test_exact_schema_two_state_and_package_block_pass(self):
        registry = self.registry()
        record = self.reconciliation()
        registry["safe_custody"]["reconciliations"].append(record)
        registry["safe_custody"]["package_blocks"]["ps-test-001"] = {
            "kind": "reconcile_main",
            "operation_id": record["operation_id"],
        }
        self.seal(registry)
        LIFECYCLE.validate_safe_custody_registry(registry)
        with self.assertRaisesRegex(LIFECYCLE.Refusal, "blocked by safe-custody"):
            LIFECYCLE.require_package_mutation_unblocked(
                registry, "PS-TEST-001", operation="ordinary write"
            )
        LIFECYCLE.require_package_mutation_unblocked(
            registry,
            "PS-TEST-001",
            operation="exact continuation",
            allowed_operation_id=record["operation_id"],
        )

    def test_registry_rejects_tampered_after_digest(self):
        registry = self.registry()
        registry["safe_custody"]["migration"]["after_sha256"] = "f" * 64
        with self.assertRaisesRegex(LIFECYCLE.Refusal, "does not match registry bytes"):
            LIFECYCLE.validate_safe_custody_registry(registry)

    def test_candidate_lifecycle_cannot_migrate_or_create_backup(self):
        fixture = RepositoryFixture()
        self.addCleanup(fixture.temporary.cleanup)
        self.install_accepted_safe_custody_tools(
            fixture, lifecycle_bytes=b"# accepted lifecycle bytes\n"
        )
        fixture.initialize()
        qualification_path = fixture.base / "qualification.json"
        qualification_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "owner_authorization_ref": "task:owner",
                    "qualified_at": "2026-09-13T00:00:00Z",
                    "writers": [],
                }
            ),
            encoding="utf-8",
        )
        before = fixture.registry_path.read_bytes()
        backups_before = sorted(fixture.registry_path.parent.glob("worktree_registry.schema1.*.json"))
        code, payload = fixture.run(
            "migrate-registry-v2",
            "--task-ref", "task:migration-owner",
            "--qualification-file", str(qualification_path),
            "--execute",
            environment_overrides={"PEERSLATE_CALLER_REF": "task:migration-owner"},
        )
        self.assertEqual(LIFECYCLE.REFUSAL_EXIT, code, payload)
        self.assertIn("accepted origin/main scripts/worktree_lifecycle.py bytes", payload["error"])
        self.assertEqual(before, fixture.registry_path.read_bytes())
        self.assertEqual(
            backups_before,
            sorted(fixture.registry_path.parent.glob("worktree_registry.schema1.*.json")),
        )

    def test_safe_custody_commands_reject_native_identity_mismatch_before_effects(self):
        fixture = RepositoryFixture()
        self.addCleanup(fixture.temporary.cleanup)
        fixture.initialize()
        before = fixture.registry_path.read_bytes()
        commands = (
            ("scope-release", "prepare", "--package", fixture.package, "--task-ref", fixture.writer),
            ("reconcile-main", "start", "--package", fixture.package, "--task-ref", fixture.writer),
            ("migrate-registry-v2", "--task-ref", fixture.writer, "--qualification-file", str(fixture.base / "absent.json")),
        )
        for command in commands:
            with self.subTest(command=command[0]):
                code, payload = fixture.run(
                    *command,
                    "--execute",
                    environment_overrides={
                        "PEERSLATE_CALLER_REF": "",
                        "CODEX_THREAD_ID": "11111111-1111-4111-8111-111111111111",
                    },
                )
                self.assertEqual(LIFECYCLE.REFUSAL_EXIT, code, payload)
                self.assertIn("claimed task differs from resolved caller", payload["error"])
                self.assertEqual(before, fixture.registry_path.read_bytes())
        self.assertEqual([], list(fixture.registry_path.parent.glob("worktree_registry.schema1.*.json")))

    def test_safe_custody_commands_reject_registered_context_mismatch_before_effects(self):
        fixture = RepositoryFixture()
        self.addCleanup(fixture.temporary.cleanup)
        fixture.initialize()
        context = LIFECYCLE._repo_context(fixture.repo)
        registry = json.loads(fixture.registry_path.read_text(encoding="utf-8"))
        context_id = "b" * 32
        registry.setdefault("caller_contexts", []).append(
            {
                "id": context_id,
                "state": "active",
                "repository_common_dir": str(context.common_dir),
                "receiver_ref": "task:different-writer",
                "package": fixture.package,
                "registered_by": "task:registrar",
                "owner_authorization_ref": "task:owner",
                "registered_at": "2026-09-13T00:00:00Z",
                "revoked_at": None,
                "revoked_by": None,
                "revocation_authorization_ref": None,
            }
        )
        fixture.registry_path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")
        before = fixture.registry_path.read_bytes()
        commands = (
            ("scope-release", "prepare", "--package", fixture.package, "--task-ref", fixture.writer),
            ("reconcile-main", "start", "--package", fixture.package, "--task-ref", fixture.writer),
            ("migrate-registry-v2", "--task-ref", fixture.writer, "--qualification-file", str(fixture.base / "absent.json")),
        )
        for command in commands:
            with self.subTest(command=command[0]):
                code, payload = fixture.run(
                    *command,
                    "--caller-context", context_id,
                    "--execute",
                    environment_overrides={"PEERSLATE_CALLER_REF": "", "CODEX_THREAD_ID": ""},
                )
                self.assertEqual(LIFECYCLE.REFUSAL_EXIT, code, payload)
                self.assertIn("claimed task differs from resolved caller", payload["error"])
                self.assertEqual(before, fixture.registry_path.read_bytes())
        self.assertEqual([], list(fixture.registry_path.parent.glob("worktree_registry.schema1.*.json")))

    def test_registry_rejects_block_mismatch_and_nonmonotonic_replay(self):
        registry = self.registry()
        record = self.reconciliation(phase="resolved")
        registry["safe_custody"]["reconciliations"].append(record)
        registry["safe_custody"]["package_blocks"]["ps-test-001"] = {
            "kind": "reconcile_main",
            "operation_id": "f" * 64,
        }
        self.seal(registry)
        with self.assertRaisesRegex(LIFECYCLE.Refusal, "package_blocks"):
            LIFECYCLE.validate_safe_custody_registry(registry)
        registry["safe_custody"]["package_blocks"]["ps-test-001"]["operation_id"] = record["operation_id"]
        record["history"].append(
            {"phase": "merging", "at": "2026-09-13T00:00:00Z"}
        )
        record["phase"] = "merging"
        record["expected_tree"] = None
        record["nonconflicted_index_sha256"] = None
        self.seal(registry)
        with self.assertRaisesRegex(LIFECYCLE.Refusal, "not monotonic"):
            LIFECYCLE.validate_safe_custody_registry(registry)

    def test_refresh_required_is_durable_and_may_only_transition_to_completed(self):
        registry = self.registry()
        record = self.reconciliation(phase="refresh_required")
        registry["safe_custody"]["reconciliations"].append(record)
        registry["safe_custody"]["package_blocks"]["ps-test-001"] = {
            "kind": "refresh_required",
            "operation_id": record["operation_id"],
        }
        self.seal(registry)
        LIFECYCLE.validate_safe_custody_registry(registry)
        record["phase"] = "completed"
        record["history"].append(
            {"phase": "completed", "at": "2026-09-13T00:00:00Z"}
        )
        registry["safe_custody"]["package_blocks"] = {}
        self.seal(registry)
        LIFECYCLE.validate_safe_custody_registry(registry)

    def test_reconciliation_imports_unowned_main_and_pushes_exact_two_parent_merge(self):
        repo, _publisher, context, registry, record, claim, source, target, branch = (
            self.reconciliation_git_fixture()
        )
        with patch.object(LIFECYCLE, "_atomic_write"):
            result = LIFECYCLE._complete_reconciliation(
                context, registry, record, claim
            )
        self.assertEqual("completed", result["status"])
        merged = git(repo, "rev-parse", "HEAD")
        self.assertEqual([source, target], git(repo, "show", "-s", "--format=%P", merged).split())
        self.assertEqual("main change", (repo / "unowned.txt").read_text(encoding="utf-8").strip())
        self.assertEqual(merged, git(repo, "ls-remote", "origin", f"refs/heads/{branch}").split()[0])
        self.assertEqual({}, registry["safe_custody"]["package_blocks"])

    def test_reconciliation_aborts_unowned_conflict_and_restores_exact_checkpoint(self):
        repo, _publisher, context, registry, record, claim, source, _target, _branch = (
            self.reconciliation_git_fixture(unowned_conflict=True)
        )
        with (
            patch.object(LIFECYCLE, "_atomic_write"),
            self.assertRaisesRegex(LIFECYCLE.Refusal, "unowned conflict"),
        ):
            LIFECYCLE._complete_reconciliation(context, registry, record, claim)
        self.assertEqual(source, git(repo, "rev-parse", "HEAD"))
        self.assertEqual("", git(repo, "status", "--porcelain=v1"))
        self.assertEqual("aborted", record["phase"])
        self.assertEqual({}, registry["safe_custody"]["package_blocks"])

    def test_reconciliation_refuses_owned_nonconflicted_resolution_edit(self):
        repo, _publisher, context, registry, record, claim, source, _target, branch = (
            self.reconciliation_git_fixture(owned_conflict=True)
        )
        with patch.object(LIFECYCLE, "_atomic_write"):
            result = LIFECYCLE._complete_reconciliation(
                context, registry, record, claim
            )
        self.assertEqual("resolution_required", result["status"])
        self.assertEqual(["owned.txt"], record["allowed_conflict_paths"])
        self.assertRegex(record["nonconflicted_index_sha256"], r"^[0-9a-f]{64}$")
        (repo / "owned.txt").write_text("resolved\n", encoding="utf-8")
        (repo / "owned-stable.txt").write_text("unauthorized edit\n", encoding="utf-8")
        git(repo, "add", "owned.txt", "owned-stable.txt")
        with (
            patch.object(LIFECYCLE, "_atomic_write"),
            self.assertRaisesRegex(LIFECYCLE.Refusal, "non-conflicted index path"),
        ):
            LIFECYCLE._complete_reconciliation(context, registry, record, claim)
        self.assertEqual(source, git(repo, "rev-parse", "HEAD"))
        self.assertEqual(source, git(repo, "ls-remote", "origin", f"refs/heads/{branch}").split()[0])
        self.assertEqual("merging", record["phase"])

    def test_scope_release_refuses_rewritten_non_ancestral_main(self):
        fixture = RepositoryFixture()
        self.addCleanup(fixture.temporary.cleanup)
        prepared = fixture.main_sha
        prior = json.loads(
            git(
                fixture.repo,
                "show",
                f"{prepared}:docs/governance/lane_claims/{fixture.package}.json",
            )
        )
        intended = copy.deepcopy(prior)
        intended["surfaces"] = ["sample.txt"]
        claim_path = fixture.repo / "docs" / "governance" / "lane_claims" / f"{fixture.package}.json"
        claim_path.write_text(json.dumps(intended, indent=2) + "\n", encoding="utf-8")
        git(fixture.repo, "add", str(claim_path.relative_to(fixture.repo)))
        git(fixture.repo, "commit", "-m", "accepted scope release")
        accepted = git(fixture.repo, "rev-parse", "HEAD")
        context = LIFECYCLE._repo_context(fixture.repo)
        LIFECYCLE._scope_release_transition_is_accepted(
            context,
            package=fixture.package,
            prepared_main=prepared,
            current_main=accepted,
            prior_claim_sha256=LIFECYCLE._canonical_json_sha256(prior),
            intended_claim_sha256=LIFECYCLE._canonical_json_sha256(intended),
        )
        rewritten = git(
            fixture.repo,
            "commit-tree",
            git(fixture.repo, "rev-parse", f"{accepted}^{{tree}}"),
            "-m",
            "rewritten main",
        )
        with self.assertRaisesRegex(LIFECYCLE.Refusal, "not an ancestor"):
            LIFECYCLE._scope_release_transition_is_accepted(
                context,
                package=fixture.package,
                prepared_main=prepared,
                current_main=rewritten,
                prior_claim_sha256=LIFECYCLE._canonical_json_sha256(prior),
                intended_claim_sha256=LIFECYCLE._canonical_json_sha256(intended),
            )

    def test_reconciliation_preserves_exact_result_when_main_drifts(self):
        repo, publisher, context, registry, record, claim, source, target, branch = (
            self.reconciliation_git_fixture()
        )
        (publisher / "later.txt").write_text("later main\n", encoding="utf-8")
        git(publisher, "add", "later.txt")
        git(publisher, "commit", "-m", "advance main again")
        later_main = git(publisher, "rev-parse", "HEAD")
        git(publisher, "push", "origin", "main")
        with patch.object(LIFECYCLE, "_atomic_write"):
            result = LIFECYCLE._complete_reconciliation(
                context, registry, record, claim
            )
        self.assertEqual("refresh_required", result["status"])
        merged = git(repo, "rev-parse", "HEAD")
        self.assertEqual([source, target], git(repo, "show", "-s", "--format=%P", merged).split())
        self.assertEqual(merged, git(repo, "ls-remote", "origin", f"refs/heads/{branch}").split()[0])
        self.assertEqual(later_main, git(repo, "rev-parse", "origin/main"))
        self.assertEqual(
            {"kind": "refresh_required", "operation_id": record["operation_id"]},
            registry["safe_custody"]["package_blocks"][claim["package"].casefold()],
        )

    def test_reconciliation_preserves_resolved_merge_when_authority_changes(self):
        repo, publisher, context, registry, record, claim, source, _target, branch = (
            self.reconciliation_git_fixture()
        )
        claim_path = (
            publisher / "docs" / "governance" / "lane_claims"
            / f"{claim['package']}.json"
        )
        changed_claim = json.loads(claim_path.read_text(encoding="utf-8"))
        changed_claim["writer_ref"] = "task:replacement-writer"
        claim_path.write_text(json.dumps(changed_claim) + "\n", encoding="utf-8")
        git(publisher, "add", str(claim_path.relative_to(publisher)))
        git(publisher, "commit", "-m", "change package authority")
        git(publisher, "push", "origin", "main")
        with (
            patch.object(LIFECYCLE, "_atomic_write"),
            self.assertRaisesRegex(LIFECYCLE.Refusal, "authority changed"),
        ):
            LIFECYCLE._complete_reconciliation(context, registry, record, claim)
        self.assertEqual("resolved", record["phase"])
        self.assertEqual(source, git(repo, "rev-parse", "HEAD"))
        self.assertTrue(git(repo, "rev-parse", "-q", "--verify", "MERGE_HEAD"))
        self.assertEqual(source, git(repo, "ls-remote", "origin", f"refs/heads/{branch}").split()[0])


if __name__ == "__main__":
    unittest.main()
