import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "agent_environment_readiness.py"
SPEC = importlib.util.spec_from_file_location("agent_environment_readiness", SCRIPT)
readiness = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = readiness
SPEC.loader.exec_module(readiness)


PACKAGE = "PS-AGENT-WORKFLOW-EFFICIENCY-001"
TASK_REF = "session:11111111-1111-4111-8111-111111111111"
SHA = "a" * 40
TOKEN = "".join(("ZXQ", "_", "REDACT", "_", "TEST"))


class FakeRunner:
    def __init__(self, repo, *, origin=None, sparse_supported=True, az_ok=True, dirty=False):
        self.repo = str(repo)
        self.origin = origin or (
            "https://peerslate19@dev.azure.com/peerslate19/portfolio-site/"
            "_git/portfolio-site"
        )
        self.sparse_supported = sparse_supported
        self.az_ok = az_ok
        self.dirty = dirty
        self.calls = []

    @staticmethod
    def completed(args, returncode=0, stdout="", stderr=""):
        return subprocess.CompletedProcess(args, returncode, stdout, stderr)

    def __call__(self, args, **kwargs):
        del kwargs
        self.calls.append(list(args))
        joined = " ".join(str(item) for item in args)
        if args[0] == "az":
            if self.az_ok:
                return self.completed(args, stdout=TOKEN + "\n")
            return self.completed(args, returncode=1, stderr="do-not-leak-auth-error")
        if "worktree_lifecycle.py" in joined:
            return self.completed(
                args,
                stdout=json.dumps(
                    {
                        "ok": True,
                        "status": "ok",
                        "current_worktree_count": 3,
                        "registered_active_count": 2,
                        "lock_present": False,
                        "pending": None,
                        "registry": "C:/private/path/registry.json",
                    }
                ),
            )
        if "delivery_preflight.py" in joined:
            return self.completed(
                args,
                stdout=json.dumps(
                    {
                        "result": "pass",
                        "warnings": [],
                        "errors": [],
                        "facts": {"private_path": "C:/do-not-emit"},
                    }
                ),
            )
        if args[-2:] == ["rev-parse", "--show-toplevel"]:
            return self.completed(args, stdout=self.repo + "\n")
        if args[-3:] == ["remote", "get-url", "origin"]:
            return self.completed(args, stdout=self.origin + "\n")
        if args[-4:] == ["ls-remote", "--exit-code", "origin", "refs/heads/main"]:
            return self.completed(args, stdout=f"{SHA}\trefs/heads/main\n")
        if args[-3:] == ["rev-parse", "--verify", "refs/remotes/origin/main"]:
            return self.completed(args, stdout=SHA + "\n")
        if args[-2:] == ["branch", "--show-current"]:
            return self.completed(args, stdout="work/2026-09-06-agent-workflow-efficiency-001\n")
        if args[-2:] == ["status", "--porcelain=v1"]:
            return self.completed(args, stdout=" M private-name.txt\n" if self.dirty else "")
        if args[-3:] == ["config", "--bool", "core.sparseCheckout"]:
            return self.completed(args, returncode=1)
        if args[-3:] == ["config", "--bool", "index.sparse"]:
            return self.completed(args, returncode=1)
        if args[-2:] == ["add", "-h"]:
            help_text = (
                "--[no-]sparse allow updating outside cone"
                if self.sparse_supported
                else "usage: git add"
            )
            return self.completed(args, returncode=129, stderr=help_text)
        raise AssertionError(f"unexpected command shape: {args!r}")


def good_http(url, token):
    if token != TOKEN:
        raise AssertionError("wrong token")
    if "/_apis/projects/" in url:
        return {"id": readiness.AZURE_PROJECT_ID, "name": "portfolio-site"}
    if "/pullrequests/" in url:
        return {
            "pullRequestId": 940,
            "repository": {"id": readiness.AZURE_REPOSITORY_ID},
            "status": "active",
            "mergeStatus": None,
            "completionOptions": None,
        }
    return {
        "id": readiness.AZURE_REPOSITORY_ID,
        "project": {"id": readiness.AZURE_PROJECT_ID},
    }


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name).resolve()
        (self.repo / "scripts").mkdir()
        (self.repo / "docs" / "governance" / "lane_claims").mkdir(parents=True)
        (self.repo / "scripts" / "worktree_lifecycle.py").write_text("", encoding="utf-8")
        (self.repo / "scripts" / "delivery_preflight.py").write_text("", encoding="utf-8")
        (self.repo / "docs" / "governance" / "lane_claims" / f"{PACKAGE}.json").write_text(
            json.dumps(
                {
                    "package": PACKAGE,
                    "state": "active",
                    "writer_ref": TASK_REF,
                    "branch": "work/2026-09-06-agent-workflow-efficiency-001",
                    "production_authority": "withheld",
                }
            ),
            encoding="utf-8",
        )

    def tearDown(self):
        self.temp.cleanup()

    def collect(self, **overrides):
        runner = overrides.pop("runner", FakeRunner(self.repo))
        return readiness.collect_readiness(
            repo=self.repo,
            package=PACKAGE,
            task_ref=TASK_REF,
            operation="merge",
            pull_request_id=940,
            runner=runner,
            http_fetcher=overrides.pop("http_fetcher", good_http),
            executable_finder=overrides.pop("executable_finder", lambda name: "az"),
            **overrides,
        )

    def test_complete_read_only_environment_check_passes_without_authority_claim(self):
        runner = FakeRunner(self.repo)
        report = self.collect(runner=runner)
        self.assertEqual("pass", report["environment_status"])
        self.assertEqual("unproven", report["operation_authority"])
        self.assertIn("does not prove write permission", report["interpretation"])
        encoded = json.dumps(report)
        self.assertNotIn(TOKEN, encoded)
        self.assertNotIn(str(self.repo), encoded)
        self.assertFalse(
            any(call[-2:] == ["add", "."] for call in runner.calls),
            "the sparse probe must never stage",
        )
        pull_request = next(
            item for item in report["checks"] if item["name"] == "azure_pull_request_get"
        )
        self.assertEqual("unavailable", pull_request["details"]["merge_status"])
        self.assertFalse(pull_request["details"]["completion_options_present"])

    def test_missing_azure_cli_is_classified_without_running_http(self):
        called = False

        def no_http(url, token):
            nonlocal called
            called = True
            raise AssertionError((url, token))

        report = self.collect(
            executable_finder=lambda name: None,
            http_fetcher=no_http,
        )
        self.assertEqual("unavailable", report["environment_status"])
        self.assertFalse(called)
        token_check = next(item for item in report["checks"] if item["name"] == "azure_token")
        self.assertEqual("azure_cli_missing", token_check["code"])

    def test_wrong_origin_is_a_closed_failure(self):
        runner = FakeRunner(self.repo, origin="https://example.invalid/repository")
        http_called = False

        def forbidden_http(url, token):
            nonlocal http_called
            http_called = True
            raise AssertionError((url, token))

        report = self.collect(runner=runner, http_fetcher=forbidden_http)
        origin = next(item for item in report["checks"] if item["name"] == "git_origin")
        self.assertEqual("fail", origin["status"])
        self.assertEqual("azure_origin_mismatch", origin["code"])
        self.assertNotIn("not-a-port", json.dumps(report))
        self.assertFalse(any(call[0] == "az" for call in runner.calls))
        self.assertFalse(any("ls-remote" in call for call in runner.calls))
        self.assertFalse(
            any(
                "worktree_lifecycle.py" in " ".join(call)
                or "delivery_preflight.py" in " ".join(call)
                for call in runner.calls
            )
        )
        self.assertFalse(http_called)
        token = next(item for item in report["checks"] if item["name"] == "azure_token")
        self.assertEqual("repository_identity_unverified", token["code"])

    def test_malformed_origin_port_is_a_closed_failure(self):
        runner = FakeRunner(
            self.repo,
            origin=(
                "https://dev.azure.com:not-a-port/peerslate19/portfolio-site/"
                "_git/portfolio-site"
            ),
        )

        report = self.collect(
            runner=runner,
            http_fetcher=lambda *_args: self.fail("HTTP must remain unreachable"),
        )

        origin = next(item for item in report["checks"] if item["name"] == "git_origin")
        self.assertEqual("fail", origin["status"])
        self.assertEqual("azure_origin_mismatch", origin["code"])
        self.assertFalse(any(call[0] == "az" for call in runner.calls))
        self.assertFalse(any("ls-remote" in call for call in runner.calls))

    def test_wrong_azure_repository_payload_is_a_closed_failure(self):
        def wrong_repo(url, token):
            payload = good_http(url, token)
            if "/repositories/" in url and "/pullrequests/" not in url:
                payload["id"] = "ffffffff-ffff-ffff-ffff-ffffffffffff"
            return payload

        report = self.collect(http_fetcher=wrong_repo)
        repository = next(
            item for item in report["checks"] if item["name"] == "azure_repository_get"
        )
        self.assertEqual("fail", repository["status"])
        self.assertEqual("azure_repository_mismatch", repository["code"])

    def test_http_403_is_reported_without_response_body(self):
        def forbidden(url, token):
            del url, token
            raise readiness.ReadinessError("azure_auth_refused")

        report = self.collect(http_fetcher=forbidden)
        self.assertNotIn(TOKEN, json.dumps(report))
        self.assertTrue(
            any(item["code"] == "azure_auth_refused" for item in report["checks"])
        )

    def test_auth_failure_and_raw_error_are_redacted(self):
        sentinel = "REDACT-ME"

        def hostile_http(url, token):
            raise RuntimeError(sentinel + url + token)

        report = self.collect(http_fetcher=hostile_http)
        encoded = json.dumps(report)
        self.assertNotIn(sentinel, encoded)
        self.assertNotIn(TOKEN, encoded)
        azure_checks = [item for item in report["checks"] if item["name"].startswith("azure_")]
        self.assertTrue(any(item["code"] == "azure_get_failed" for item in azure_checks))

    def test_sparse_support_is_checked_from_help_without_staging(self):
        runner = FakeRunner(self.repo, sparse_supported=False)
        report = self.collect(runner=runner)
        sparse = next(item for item in report["checks"] if item["name"] == "git_sparse_capability")
        self.assertEqual("fail", sparse["status"])
        self.assertFalse(sparse["details"]["staging_probe_performed"])

    def test_dirty_checkout_fails_a_mutating_operation_without_listing_paths(self):
        runner = FakeRunner(self.repo, dirty=True)
        report = self.collect(runner=runner)
        checkout = next(item for item in report["checks"] if item["name"] == "checkout")
        self.assertEqual("fail", checkout["status"])
        self.assertEqual("checkout_dirty_for_operation", checkout["code"])
        self.assertNotIn("private-name.txt", json.dumps(report))

    def test_fixed_get_refuses_redirect_before_parsing_body(self):
        class Response:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def geturl(self):
                return "https://evil.invalid/capture"

            def read(self, limit):
                del limit
                return b'{"id":"ignored"}'

        class Opener:
            def open(self, request, timeout):
                del request, timeout
                return Response()

        url = readiness._azure_urls(None)[0][1]
        with mock.patch.object(readiness.urllib.request, "build_opener", return_value=Opener()):
            with self.assertRaisesRegex(readiness.ReadinessError, "azure_redirect_refused"):
                readiness._fixed_https_json_get(url, TOKEN)


if __name__ == "__main__":
    unittest.main()
