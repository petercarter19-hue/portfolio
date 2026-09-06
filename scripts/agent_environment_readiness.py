"""Read-only, secret-safe PeerSlate agent environment readiness checks.

This utility verifies observable environment facts.  It never fetches Git refs,
stages files, mutates a claim, creates a PR, or asserts write permission.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable, Sequence


AZURE_ORGANIZATION = "peerslate19"
AZURE_PROJECT_NAME = "portfolio-site"
AZURE_PROJECT_ID = "13321071-80c4-45a5-b6db-c2841f9132da"
AZURE_REPOSITORY_NAME = "portfolio-site"
AZURE_REPOSITORY_ID = "01dd5d96-f3f4-43b3-b05d-5429f18dc2b7"
AZURE_TENANT_ID = "a4719821-fb0e-409e-9787-025f8623caaa"
AZURE_DEVOPS_RESOURCE = "499b84ac-1321-427f-aa17-267ca6975798"
EXPECTED_ORIGIN_PATH = (
    f"/{AZURE_ORGANIZATION}/{AZURE_PROJECT_NAME}/_git/{AZURE_REPOSITORY_NAME}"
)
PACKAGE_RE = re.compile(r"^PS-[A-Z0-9]+(?:-[A-Z0-9]+)*$")
TASK_REF_RE = re.compile(r"^(?:session|agent|task):[A-Za-z0-9._:/-]{1,200}$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
CommandRunner = Callable[..., subprocess.CompletedProcess[str]]
HttpFetcher = Callable[[str, str], dict[str, Any]]


class ReadinessError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        raise ReadinessError("azure_redirect_refused")


def _check(
    name: str,
    status: str,
    code: str,
    *,
    required: bool = True,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "name": name,
        "status": status,
        "code": code,
        "required": required,
    }
    if details:
        result["details"] = details
    return result


def _run(
    runner: CommandRunner,
    args: Sequence[str],
    *,
    cwd: Path,
) -> subprocess.CompletedProcess[str]:
    try:
        return runner(
            list(args),
            cwd=str(cwd),
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        raise ReadinessError("command_unavailable")


def _git(
    runner: CommandRunner, repo: Path, *args: str
) -> subprocess.CompletedProcess[str]:
    return _run(runner, ("git", "-C", str(repo), *args), cwd=repo)


def _valid_origin(url: str) -> bool:
    try:
        parsed = urllib.parse.urlsplit(url.strip())
        return (
            parsed.scheme.lower() == "https"
            and (parsed.hostname or "").lower() == "dev.azure.com"
            and parsed.path.rstrip("/") == EXPECTED_ORIGIN_PATH
            and parsed.password is None
            and parsed.port is None
            and not parsed.query
            and not parsed.fragment
        )
    except ValueError:
        return False


def _fixed_https_json_get(url: str, token: str) -> dict[str, Any]:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname != "dev.azure.com":
        raise ReadinessError("azure_endpoint_refused")
    request = urllib.request.Request(
        url,
        method="GET",
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "PeerSlate-Agent-Readiness/1",
        },
    )
    opener = urllib.request.build_opener(_NoRedirect())
    try:
        with opener.open(request, timeout=20) as response:
            if response.geturl() != url:
                raise ReadinessError("azure_redirect_refused")
            if getattr(response, "status", 200) != 200:
                raise ReadinessError("azure_http_refused")
            body = response.read(1_000_001)
            if len(body) > 1_000_000:
                raise ReadinessError("azure_response_too_large")
    except ReadinessError:
        raise
    except urllib.error.HTTPError as error:
        if error.code in {401, 403}:
            raise ReadinessError("azure_auth_refused")
        raise ReadinessError("azure_http_refused")
    except (urllib.error.URLError, OSError, TimeoutError):
        raise ReadinessError("azure_http_unavailable")
    try:
        parsed_body = json.loads(body)
    except (json.JSONDecodeError, UnicodeError):
        raise ReadinessError("azure_response_invalid")
    if not isinstance(parsed_body, dict):
        raise ReadinessError("azure_response_invalid")
    return parsed_body


def _acquire_token(
    repo: Path,
    runner: CommandRunner,
    executable_finder: Callable[[str], str | None],
) -> tuple[str | None, dict[str, Any]]:
    az = executable_finder("az")
    if not az:
        return None, _check(
            "azure_token",
            "unavailable",
            "azure_cli_missing",
        )
    completed = _run(
        runner,
        (
            az,
            "account",
            "get-access-token",
            "--tenant",
            AZURE_TENANT_ID,
            "--resource",
            AZURE_DEVOPS_RESOURCE,
            "--query",
            "accessToken",
            "--output",
            "tsv",
        ),
        cwd=repo,
    )
    token = completed.stdout.strip() if completed.returncode == 0 else ""
    if not token or any(character.isspace() for character in token):
        return None, _check(
            "azure_token",
            "unavailable",
            "azure_token_unavailable",
        )
    return token, _check("azure_token", "pass", "token_acquired_in_memory")


def _azure_urls(pull_request_id: int | None) -> list[tuple[str, str, str]]:
    base = f"https://dev.azure.com/{AZURE_ORGANIZATION}"
    urls = [
        (
            "azure_project_get",
            f"{base}/_apis/projects/{AZURE_PROJECT_ID}?api-version=7.1",
            "project",
        ),
        (
            "azure_repository_get",
            (
                f"{base}/{AZURE_PROJECT_ID}/_apis/git/repositories/"
                f"{AZURE_REPOSITORY_ID}?api-version=7.1"
            ),
            "repository",
        ),
    ]
    if pull_request_id is not None:
        urls.append(
            (
                "azure_pull_request_get",
                (
                    f"{base}/{AZURE_PROJECT_ID}/_apis/git/repositories/"
                    f"{AZURE_REPOSITORY_ID}/pullrequests/{pull_request_id}"
                    "?api-version=7.1"
                ),
                "pull_request",
            )
        )
    return urls


def _validate_azure_payload(
    kind: str, payload: dict[str, Any], pull_request_id: int | None
) -> dict[str, Any]:
    if kind == "project":
        if str(payload.get("id", "")).lower() != AZURE_PROJECT_ID:
            raise ReadinessError("azure_project_mismatch")
        return {"project_id_match": True}
    if kind == "repository":
        if str(payload.get("id", "")).lower() != AZURE_REPOSITORY_ID:
            raise ReadinessError("azure_repository_mismatch")
        project = payload.get("project")
        if not isinstance(project, dict) or str(project.get("id", "")).lower() != AZURE_PROJECT_ID:
            raise ReadinessError("azure_project_mismatch")
        return {"repository_id_match": True, "project_id_match": True}
    if payload.get("pullRequestId") != pull_request_id:
        raise ReadinessError("azure_pull_request_mismatch")
    repository = payload.get("repository")
    if not isinstance(repository, dict) or str(repository.get("id", "")).lower() != AZURE_REPOSITORY_ID:
        raise ReadinessError("azure_repository_mismatch")
    merge_status = payload.get("mergeStatus")
    completion = payload.get("completionOptions")
    return {
        "pull_request_id_match": True,
        "repository_id_match": True,
        "status": payload.get("status")
        if payload.get("status") in {"active", "abandoned", "completed", "notSet"}
        else "unavailable",
        "merge_status": merge_status
        if isinstance(merge_status, str) and len(merge_status) <= 40
        else "unavailable",
        "completion_options_present": isinstance(completion, dict),
    }


def collect_readiness(
    *,
    repo: Path,
    package: str,
    task_ref: str,
    operation: str,
    pull_request_id: int | None = None,
    runner: CommandRunner = subprocess.run,
    http_fetcher: HttpFetcher = _fixed_https_json_get,
    executable_finder: Callable[[str], str | None] = shutil.which,
) -> dict[str, Any]:
    if not PACKAGE_RE.fullmatch(package):
        raise ReadinessError("invalid_package")
    if not TASK_REF_RE.fullmatch(task_ref):
        raise ReadinessError("invalid_task_ref")
    repo = repo.resolve()
    checks: list[dict[str, Any]] = []

    try:
        root_result = _git(runner, repo, "rev-parse", "--show-toplevel")
        discovered = Path(root_result.stdout.strip()).resolve()
        root_ok = root_result.returncode == 0 and discovered == repo
    except (ReadinessError, OSError):
        root_ok = False
    checks.append(
        _check(
            "git_root",
            "pass" if root_ok else "fail",
            "exact_repository_root" if root_ok else "repository_root_mismatch",
        )
    )

    origin_result = _git(runner, repo, "remote", "get-url", "origin")
    origin_ok = origin_result.returncode == 0 and _valid_origin(origin_result.stdout)
    checks.append(
        _check(
            "git_origin",
            "pass" if origin_ok else "fail",
            "azure_origin_exact" if origin_ok else "azure_origin_mismatch",
        )
    )

    if root_ok and origin_ok:
        remote_result = _git(
            runner, repo, "ls-remote", "--exit-code", "origin", "refs/heads/main"
        )
        remote_parts = remote_result.stdout.strip().split()
        remote_sha = (
            remote_parts[0]
            if len(remote_parts) == 2 and SHA_RE.fullmatch(remote_parts[0])
            else None
        )
        remote_code = (
            "remote_main_observed_without_fetch"
            if remote_result.returncode == 0 and remote_sha
            else "remote_main_unavailable"
        )
    else:
        remote_result = None
        remote_sha = None
        remote_code = "repository_identity_unverified"
    checks.append(
        _check(
            "remote_main",
            "pass"
            if remote_result is not None and remote_result.returncode == 0 and remote_sha
            else "unavailable",
            remote_code,
        )
    )

    local_result = _git(runner, repo, "rev-parse", "--verify", "refs/remotes/origin/main")
    local_sha = local_result.stdout.strip()
    local_valid = local_result.returncode == 0 and bool(SHA_RE.fullmatch(local_sha))
    local_match = bool(remote_sha and local_valid and local_sha == remote_sha)
    checks.append(
        _check(
            "local_remote_main",
            "pass" if local_match else ("fail" if remote_sha and local_valid else "unavailable"),
            "local_origin_main_matches_server"
            if local_match
            else ("local_origin_main_diverged" if remote_sha and local_valid else "local_origin_main_unavailable"),
        )
    )

    branch_result = _git(runner, repo, "branch", "--show-current")
    branch = branch_result.stdout.strip()
    status_result = _git(runner, repo, "status", "--porcelain=v1")
    checkout_observed = branch_result.returncode == 0 and status_result.returncode == 0
    checkout_clean = checkout_observed and not bool(status_result.stdout)
    checkout_ok = checkout_observed and (
        checkout_clean or operation in {"read", "review"}
    )
    checks.append(
        _check(
            "checkout",
            "pass" if checkout_ok else ("fail" if checkout_observed else "unavailable"),
            "checkout_observed"
            if checkout_ok
            else ("checkout_dirty_for_operation" if checkout_observed else "checkout_unavailable"),
            details={"clean": checkout_clean}
            if checkout_observed
            else None,
        )
    )

    claim_path = repo / "docs" / "governance" / "lane_claims" / f"{package}.json"
    try:
        claim = json.loads(claim_path.read_text(encoding="utf-8"))
        claim_ok = (
            isinstance(claim, dict)
            and claim.get("package") == package
            and claim.get("state") == "active"
            and claim.get("writer_ref") == task_ref
            and claim.get("branch") == branch
            and claim.get("production_authority") == "withheld"
        )
    except (OSError, json.JSONDecodeError, UnicodeError):
        claim = {}
        claim_ok = False
    checks.append(
        _check(
            "package_claim",
            "pass" if claim_ok else "fail",
            "active_claim_matches_task_and_branch" if claim_ok else "claim_custody_mismatch",
        )
    )

    if root_ok and origin_ok:
        lifecycle_script = repo / "scripts" / "worktree_lifecycle.py"
        lifecycle = _run(
            runner,
            (
                sys.executable,
                "-B",
                str(lifecycle_script),
                "--repo",
                str(repo),
                "audit",
                "--json",
            ),
            cwd=repo,
        )
        try:
            lifecycle_json = json.loads(lifecycle.stdout)
            lifecycle_status = lifecycle_json.get("status")
            lifecycle_ok = lifecycle.returncode == 0 and lifecycle_status == "ok"
            lifecycle_details = {
                "status": lifecycle_status
                if lifecycle_status in {"ok", "attention", "uninitialized"}
                else "unavailable",
                "current_worktree_count": lifecycle_json.get("current_worktree_count")
                if isinstance(lifecycle_json.get("current_worktree_count"), int)
                else None,
                "registered_active_count": lifecycle_json.get("registered_active_count")
                if isinstance(lifecycle_json.get("registered_active_count"), int)
                else None,
                "lock_present": lifecycle_json.get("lock_present")
                if isinstance(lifecycle_json.get("lock_present"), bool)
                else None,
                "pending_present": bool(lifecycle_json.get("pending")),
            }
        except (json.JSONDecodeError, AttributeError):
            lifecycle_ok = False
            lifecycle_details = {"status": "unavailable"}
        lifecycle_status_value = "pass" if lifecycle_ok else "fail"
        lifecycle_code = (
            "lifecycle_audit_ok" if lifecycle_ok else "lifecycle_audit_not_ok"
        )
    else:
        lifecycle_ok = False
        lifecycle_status_value = "unavailable"
        lifecycle_code = "repository_identity_unverified"
        lifecycle_details = {"status": "unavailable"}
    checks.append(
        _check(
            "worktree_custody",
            lifecycle_status_value,
            lifecycle_code,
            details=lifecycle_details,
        )
    )

    if root_ok and origin_ok:
        preflight_script = repo / "scripts" / "delivery_preflight.py"
        preflight = _run(
            runner,
            (
                sys.executable,
                "-B",
                str(preflight_script),
                "--repo",
                str(repo),
                "--package",
                package,
                "--intent",
                "read",
                "--task-ref",
                task_ref,
            ),
            cwd=repo,
        )
        try:
            preflight_json = json.loads(preflight.stdout)
            preflight_ok = preflight.returncode == 0 and preflight_json.get("result") == "pass"
            warning_count = len(preflight_json.get("warnings", []))
            error_count = len(preflight_json.get("errors", []))
        except (json.JSONDecodeError, AttributeError, TypeError):
            preflight_ok = False
            warning_count = error_count = 0
        preflight_status_value = "pass" if preflight_ok else "fail"
        preflight_code = "read_preflight_passed" if preflight_ok else "read_preflight_failed"
    else:
        preflight_ok = False
        warning_count = error_count = 0
        preflight_status_value = "unavailable"
        preflight_code = "repository_identity_unverified"
    checks.append(
        _check(
            "delivery_read_preflight",
            preflight_status_value,
            preflight_code,
            details={"warning_count": warning_count, "error_count": error_count},
        )
    )

    sparse_checkout = _git(runner, repo, "config", "--bool", "core.sparseCheckout")
    sparse_index = _git(runner, repo, "config", "--bool", "index.sparse")
    add_help = _git(runner, repo, "add", "-h")
    help_text = add_help.stdout + add_help.stderr
    sparse_supported = any(
        marker in help_text for marker in ("--sparse", "--[no-]sparse")
    )
    checks.append(
        _check(
            "git_sparse_capability",
            "pass" if sparse_supported else "fail",
            "git_add_sparse_supported" if sparse_supported else "git_add_sparse_unsupported",
            details={
                "sparse_checkout": sparse_checkout.stdout.strip().lower() == "true",
                "sparse_index": sparse_index.stdout.strip().lower() == "true",
                "staging_probe_performed": False,
            },
        )
    )

    token: str | None = None
    if not root_ok or not origin_ok:
        checks.append(
            _check(
                "azure_token",
                "unavailable",
                "repository_identity_unverified",
            )
        )
        for name, _url, _kind in _azure_urls(pull_request_id):
            checks.append(
                _check(name, "unavailable", "repository_identity_unverified")
            )
    else:
        try:
            token, token_check = _acquire_token(repo, runner, executable_finder)
            checks.append(token_check)
            if token is None:
                for name, _url, _kind in _azure_urls(pull_request_id):
                    checks.append(_check(name, "unavailable", "azure_token_unavailable"))
            else:
                for name, url, kind in _azure_urls(pull_request_id):
                    try:
                        payload = http_fetcher(url, token)
                        details = _validate_azure_payload(kind, payload, pull_request_id)
                        checks.append(
                            _check(name, "pass", f"{kind}_get_verified", details=details)
                        )
                    except ReadinessError as error:
                        checks.append(_check(name, "fail", error.code))
                    except Exception:
                        checks.append(_check(name, "fail", "azure_get_failed"))
        finally:
            token = None

    if pull_request_id is None:
        checks.append(
            _check(
                "azure_pull_request_get",
                "unavailable",
                "pull_request_id_not_supplied",
                required=operation in {"pull-request", "merge"},
            )
        )

    required = [item for item in checks if item["required"]]
    if any(item["status"] == "fail" for item in required):
        environment_status = "fail"
    elif any(item["status"] == "unavailable" for item in required):
        environment_status = "unavailable"
    else:
        environment_status = "pass"
    return {
        "schema_version": 1,
        "environment_status": environment_status,
        "package": package,
        "task_ref": task_ref,
        "requested_operation": operation,
        "operation_authority": "unproven",
        "checks": checks,
        "interpretation": (
            "Read-only environment evidence only. Azure GET access does not prove "
            "write permission, package authority, merge readiness, or production authority."
        ),
    }


def render_text(report: dict[str, Any]) -> str:
    lines = [
        f"Agent environment: {report['environment_status']}",
        f"Package: {report['package']}",
        f"Task ref: {report['task_ref']}",
        f"Requested operation: {report['requested_operation']} (authority unproven)",
    ]
    lines.extend(
        f"- {item['name']}: {item['status']} ({item['code']})"
        for item in report["checks"]
    )
    lines.append(report["interpretation"])
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--package", required=True)
    parser.add_argument("--task-ref", required=True)
    parser.add_argument(
        "--operation",
        required=True,
        choices=("read", "review", "write", "pull-request", "merge"),
    )
    parser.add_argument("--pull-request-id", type=int)
    parser.add_argument("--format", choices=("json", "text"), default="text")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.pull_request_id is not None and args.pull_request_id < 1:
        raise SystemExit("pull request id must be positive")
    try:
        report = collect_readiness(
            repo=args.repo,
            package=args.package,
            task_ref=args.task_ref,
            operation=args.operation,
            pull_request_id=args.pull_request_id,
        )
    except ReadinessError as error:
        report = {
            "schema_version": 1,
            "environment_status": "fail",
            "package": args.package if PACKAGE_RE.fullmatch(args.package) else "invalid",
            "task_ref": args.task_ref if TASK_REF_RE.fullmatch(args.task_ref) else "invalid",
            "requested_operation": args.operation,
            "operation_authority": "unproven",
            "checks": [_check("readiness", "fail", error.code)],
            "interpretation": "Read-only readiness could not be established.",
        }
    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_text(report))
    return 0 if report["environment_status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
