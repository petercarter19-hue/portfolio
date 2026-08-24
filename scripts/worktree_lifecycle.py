#!/usr/bin/env python3
"""Guard PeerSlate's machine-local Git worktree lifecycle.

The registry written by this module is operational inventory.  It is stored in
the repository's Git common directory and is deliberately not repository,
delivery, or production authority.  The only checkout-removal primitive used
here is ordinary (non-force) ``git worktree remove`` after fail-closed checks.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import re
import secrets
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterator, Sequence


SCHEMA_VERSION = 1
REGISTRY_RELATIVE_PATH = Path("peerslate") / "worktree_registry.json"
LOCK_DIRECTORY_NAME = "worktree_registry.lock"
REFUSAL_EXIT = 2
GIB = 1024**3

PACKAGE_RE = re.compile(r"^PS-[A-Z0-9]+(?:-[A-Z0-9]+)*$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,79}$")
WORK_BRANCH_RE = re.compile(r"^(?:work|codex)/[a-z0-9][a-z0-9._/-]*$")
REPARSE_POINT = 0x400

CONTROL_SPARSE_PATHS = (
    "AGENTS.md",
    "START_HERE.md",
    "docs/AI_WORKFLOW.md",
    "docs/governance",
    "docs/initiatives/PS-AI-OPS-CHECKPOINT-001",
    "docs/initiatives/PS-OPS-001",
    "docs/initiatives/PS-INTERVIEW-STUDIO-VISUAL-FACELIFT-001",
    "docs/templates",
    "scripts",
    "tests",
)
STORAGE_CLASSES = {
    "repo_canonical",
    "azure_artifact",
    "x_maintenance",
    "ephemeral_same_task",
}


class Refusal(RuntimeError):
    """A requested operation did not satisfy a fail-closed guard."""

    def __init__(self, message: str, *, blockers: Sequence[str] | None = None):
        super().__init__(message)
        self.blockers = list(blockers or ())


@dataclass(frozen=True)
class RepoContext:
    root: Path
    common_dir: Path
    primary_root: Path

    @property
    def registry_path(self) -> Path:
        return self.common_dir / REGISTRY_RELATIVE_PATH


@dataclass(frozen=True)
class ServerBranchProof:
    package: str
    branch: str
    sha: str


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _canonical(path: str | os.PathLike[str]) -> Path:
    return Path(path).expanduser().resolve(strict=False)


def _path_key(path: str | os.PathLike[str]) -> str:
    return os.path.normcase(str(_canonical(path))).casefold()


def _is_within(path: str | os.PathLike[str], parent: str | os.PathLike[str]) -> bool:
    child_key = _path_key(path)
    parent_key = _path_key(parent)
    try:
        return os.path.commonpath([child_key, parent_key]) == parent_key
    except ValueError:
        return False


def _is_strictly_within(
    path: str | os.PathLike[str], parent: str | os.PathLike[str]
) -> bool:
    return _path_key(path) != _path_key(parent) and _is_within(path, parent)


def _has_reparse_component(
    path: str | os.PathLike[str], *, floor: str | os.PathLike[str] | None = None
) -> bool:
    """Return True for a symlink/junction in the checked path segment."""

    candidate = Path(path).expanduser().absolute()
    floor_path = Path(floor).expanduser().absolute() if floor is not None else None
    parts: list[Path] = []
    cursor = candidate
    while True:
        parts.append(cursor)
        if floor_path is not None and _path_key(cursor) == _path_key(floor_path):
            break
        if cursor.parent == cursor:
            break
        cursor = cursor.parent
    for item in reversed(parts):
        if not item.exists() and not item.is_symlink():
            continue
        try:
            stat = item.lstat()
        except OSError:
            return True
        attributes = getattr(stat, "st_file_attributes", 0)
        if item.is_symlink() or bool(attributes & REPARSE_POINT):
            return True
    return False


def _git_result(root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-c", "core.quotepath=false", *arguments],
        cwd=root,
        text=True,
        encoding="utf-8",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def _git(root: Path, *arguments: str) -> str:
    result = _git_result(root, *arguments)
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip() or "git failed"
        raise Refusal(f"git {' '.join(arguments)} refused: {detail}")
    return result.stdout.strip()


def _git_optional(root: Path, *arguments: str) -> str | None:
    result = _git_result(root, *arguments)
    return result.stdout.strip() if result.returncode == 0 else None


def _fetch_origin_main(context: RepoContext) -> None:
    """Refresh main without pruning worktrees, branches, remote refs, or tags."""

    _git(
        context.root,
        "fetch",
        "--no-prune",
        "--no-tags",
        "origin",
        "refs/heads/main:refs/remotes/origin/main",
    )


def _remote_branch_tip(context: RepoContext, branch: str) -> str | None:
    """Read the exact server-side branch tip, distinguishing absence from failure."""

    result = _git_result(
        context.root,
        "ls-remote",
        "--exit-code",
        "--heads",
        "origin",
        f"refs/heads/{branch}",
    )
    if result.returncode == 2 and not result.stdout.strip():
        return None
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip() or "git ls-remote failed"
        raise Refusal(f"could not confirm remote branch {branch!r}: {detail}")
    matches = [line.split() for line in result.stdout.splitlines() if line.strip()]
    expected_ref = f"refs/heads/{branch}"
    if len(matches) != 1 or len(matches[0]) != 2 or matches[0][1] != expected_ref:
        raise Refusal(f"remote branch lookup was ambiguous: {branch!r}")
    sha = matches[0][0].casefold()
    if not SHA_RE.fullmatch(sha):
        raise Refusal(f"remote branch returned an invalid commit identity: {branch!r}")
    return sha


def _fetch_origin_branch(context: RepoContext, branch: str) -> str | None:
    """Non-pruning exact-fetch of one branch, or confirmed server-side absence."""

    observed_tip = _remote_branch_tip(context, branch)
    if observed_tip is None:
        return None
    result = _git_result(
        context.root,
        "fetch",
        "--no-prune",
        "--no-tags",
        "origin",
        f"+refs/heads/{branch}:refs/remotes/origin/{branch}",
    )
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip() or "git fetch failed"
        raise Refusal(f"could not exact-fetch remote branch {branch!r}: {detail}")
    fetched_tip = _ref_sha(context, f"refs/remotes/origin/{branch}")
    if fetched_tip != observed_tip:
        raise Refusal(
            f"remote branch moved during exact fetch; retry from a stable tip: {branch!r}"
        )
    return fetched_tip


def _is_ancestor(context: RepoContext, older: str, newer: str) -> bool:
    return (
        _git_result(context.root, "merge-base", "--is-ancestor", older, newer).returncode
        == 0
    )


def _parse_worktree_porcelain(payload: str) -> list[dict[str, Any]]:
    """Parse ``git worktree list --porcelain -z`` without path splitting."""

    records: list[dict[str, Any]] = []
    current: dict[str, Any] = {}
    for field in payload.split("\0"):
        if not field:
            if current:
                records.append(current)
                current = {}
            continue
        key, separator, value = field.partition(" ")
        if key == "HEAD":
            key = "head"
        if key in {"bare", "detached", "locked", "prunable"} and not separator:
            current[key] = True
        elif key == "branch":
            current[key] = (
                value[len("refs/heads/") :]
                if value.startswith("refs/heads/")
                else value
            )
        else:
            current[key] = value if separator else True
    if current:
        records.append(current)
    for record in records:
        if "worktree" in record:
            record["worktree"] = str(_canonical(str(record["worktree"])))
        record.setdefault("branch", None)
        record.setdefault("head", None)
        record["detached"] = bool(record.get("detached"))
    return records


def _worktrees(root: Path) -> list[dict[str, Any]]:
    return _parse_worktree_porcelain(
        _git(root, "worktree", "list", "--porcelain", "-z")
    )


def _repo_context(repo: str | os.PathLike[str] | None = None) -> RepoContext:
    start = _canonical(repo or Path.cwd())
    top = _canonical(_git(start, "rev-parse", "--show-toplevel"))
    common_value = Path(_git(top, "rev-parse", "--git-common-dir"))
    common = _canonical(common_value if common_value.is_absolute() else top / common_value)
    listed = _worktrees(top)
    if not listed or "worktree" not in listed[0]:
        raise Refusal("repository has no identifiable primary worktree")
    return RepoContext(top, common, _canonical(listed[0]["worktree"]))


def _worktree_at(root: Path, path: Path) -> dict[str, Any] | None:
    key = _path_key(path)
    return next(
        (entry for entry in _worktrees(root) if _path_key(entry["worktree"]) == key),
        None,
    )


def _validate_package(package: str) -> str:
    if not PACKAGE_RE.fullmatch(package):
        raise Refusal(f"invalid package identifier: {package!r}")
    return package


def _validate_task_ref(task_ref: str) -> str:
    if (
        not task_ref
        or task_ref != task_ref.strip()
        or len(task_ref) > 240
        or ":" not in task_ref
        or any(ord(character) < 32 for character in task_ref)
    ):
        raise Refusal("task-ref must be a bounded opaque reference containing ':'")
    return task_ref


def _validate_sha(sha: str) -> str:
    normalized = sha.casefold()
    if not SHA_RE.fullmatch(normalized):
        raise Refusal("expected an exact 40-character commit SHA")
    return normalized


def _normalize_include(value: str) -> str:
    raw = value.strip().replace("\\", "/")
    if raw != value or not raw or raw.startswith("/") or re.match(r"^[A-Za-z]:", raw):
        raise Refusal(f"include must be repository-relative: {value!r}")
    parts = PurePosixPath(raw).parts
    if any(part in {"", ".", "..", ".git"} for part in parts):
        raise Refusal(f"unsafe sparse include: {value!r}")
    return "/".join(parts)


def _require_execute(execute: bool) -> None:
    if not execute:
        raise Refusal("mutation requires explicit --execute")


def _load_registry(path: Path, *, required: bool = True) -> dict[str, Any] | None:
    if not path.exists():
        if required:
            raise Refusal(
                "machine-local worktree registry is not initialized; run init first"
            )
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise Refusal(f"registry is unreadable or corrupt: {error}") from error
    if not isinstance(data, dict) or data.get("schema_version") != SCHEMA_VERSION:
        raise Refusal("registry schema is missing or unsupported")
    required_keys = {
        "initialized_at",
        "managed_root",
        "evidence_root",
        "worktrees",
    }
    if not required_keys.issubset(data) or not isinstance(data["worktrees"], list):
        raise Refusal("registry is structurally incomplete")
    data.setdefault("pending", None)
    data.setdefault("evidence_allocations", [])
    return data


def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=path.name + ".", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(payload, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        try:
            directory_fd = os.open(path.parent, os.O_RDONLY)
        except OSError:
            directory_fd = None
        if directory_fd is not None:
            try:
                os.fsync(directory_fd)
            except OSError:
                pass
            finally:
                os.close(directory_fd)
    finally:
        if temporary.exists():
            temporary.unlink()


@contextlib.contextmanager
def _registry_lock(registry_path: Path) -> Iterator[None]:
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = registry_path.parent / LOCK_DIRECTORY_NAME
    try:
        os.mkdir(lock_path)
    except FileExistsError as error:
        raise Refusal(f"registry lock is held: {lock_path}") from error
    owner_path = lock_path / "owner.json"
    try:
        owner_path.write_text(
            json.dumps(
                {"pid": os.getpid(), "acquired_at": _utc_now()}, sort_keys=True
            )
            + "\n",
            encoding="utf-8",
        )
        yield
    finally:
        try:
            owner_path.unlink(missing_ok=True)
            os.rmdir(lock_path)
        except OSError:
            # A leftover lock fails closed on the next mutation.
            pass


def _record_by_path(
    registry: dict[str, Any], path: str | os.PathLike[str]
) -> dict[str, Any] | None:
    key = _path_key(path)
    return next(
        (
            record
            for record in registry["worktrees"]
            if _path_key(record.get("path", "")) == key
        ),
        None,
    )


def _new_record(
    *,
    path: Path,
    kind: str,
    state: str,
    package: str | None,
    branch: str | None,
    head: str | None,
    task_ref: str | None,
    lease: dict[str, Any] | None = None,
    sparse_paths: Sequence[str] | None = None,
) -> dict[str, Any]:
    now = _utc_now()
    return {
        "path": str(_canonical(path)),
        "kind": kind,
        "state": state,
        "package": package,
        "branch": branch,
        "head": head,
        "task_ref": task_ref,
        "lease": lease,
        "sparse_paths": list(sparse_paths or ()),
        "created_at": now,
        "updated_at": now,
    }


def _new_ephemeral_verification_lease(
    *,
    task_ref: str,
    package: str,
    path: Path,
    head: str,
    source_branch: str,
) -> dict[str, Any]:
    return {
        "kind": "ephemeral_verification",
        "purpose": "runtime_verify",
        "token": secrets.token_hex(16),
        "pid": os.getpid(),
        "task_ref": task_ref,
        "package": package,
        "path": str(_canonical(path)),
        "head": head,
        "source_branch": source_branch,
        "acquired_at": _utc_now(),
    }


def _ephemeral_lease_matches(
    record: dict[str, Any],
    token: str,
    *,
    task_ref: str,
    package: str,
    path: Path,
    head: str,
    source_branch: str,
) -> bool:
    lease = record.get("lease")
    return bool(
        isinstance(lease, dict)
        and lease.get("kind") == "ephemeral_verification"
        and lease.get("purpose") == "runtime_verify"
        and lease.get("token") == token
        and isinstance(lease.get("pid"), int)
        and lease.get("pid") == os.getpid()
        and lease.get("task_ref") == task_ref
        and lease.get("package") == package
        and _path_key(str(lease.get("path", ""))) == _path_key(path)
        and lease.get("head") == head
        and lease.get("source_branch") == source_branch
        and record.get("kind") == "ephemeral"
        and record.get("state") == "active"
        and record.get("task_ref") == task_ref
        and record.get("package") == package
        and _path_key(str(record.get("path", ""))) == _path_key(path)
        and record.get("head") == head
        and record.get("source_branch") == source_branch
    )


def _require_ephemeral_lease(
    record: dict[str, Any],
    token: str,
    *,
    task_ref: str,
    package: str,
    path: Path,
    head: str,
    source_branch: str,
) -> None:
    if not _ephemeral_lease_matches(
        record,
        token,
        task_ref=task_ref,
        package=package,
        path=path,
        head=head,
        source_branch=source_branch,
    ):
        raise Refusal(
            "ephemeral verification lease or exact invocation identity changed; "
            "the worktree and lease were preserved"
        )


def _clear_ephemeral_lease_locked(
    context: RepoContext,
    registry: dict[str, Any],
    record: dict[str, Any],
    token: str,
    *,
    task_ref: str,
    package: str,
    path: Path,
    head: str,
    source_branch: str,
) -> None:
    _require_ephemeral_lease(
        record,
        token,
        task_ref=task_ref,
        package=package,
        path=path,
        head=head,
        source_branch=source_branch,
    )
    record["lease"] = None
    record["verification_released_at"] = _utc_now()
    record["updated_at"] = record["verification_released_at"]
    _atomic_write(context.registry_path, registry)


def _pending_retirement_has_ephemeral_lease(
    registry: dict[str, Any], path: Path, token: str
) -> bool:
    pending = registry.get("pending")
    if not isinstance(pending, dict):
        return False
    pending_record = pending.get("record")
    lease = pending_record.get("lease") if isinstance(pending_record, dict) else None
    return bool(
        pending.get("operation") == "retire"
        and _path_key(str(pending.get("path", ""))) == _path_key(path)
        and isinstance(lease, dict)
        and lease.get("kind") == "ephemeral_verification"
        and lease.get("purpose") == "runtime_verify"
        and lease.get("token") == token
    )


def _assert_registry_identity(context: RepoContext, registry: dict[str, Any]) -> None:
    registered_common = registry.get("repository_common_dir")
    if registered_common and _path_key(registered_common) != _path_key(context.common_dir):
        raise Refusal("registry belongs to a different Git common directory")
    registered_primary = registry.get("repository_primary_root")
    if registered_primary and _path_key(registered_primary) != _path_key(
        context.primary_root
    ):
        raise Refusal("registry primary-worktree identity does not match Git")


def _assert_managed_target(registry: dict[str, Any], path: Path) -> None:
    managed_root = _canonical(registry["managed_root"])
    target = _canonical(path)
    if not _is_strictly_within(target, managed_root):
        raise Refusal(f"target is outside the managed root: {target}")
    if _has_reparse_component(managed_root) or _has_reparse_component(
        target, floor=managed_root
    ):
        raise Refusal(f"managed target crosses a reparse point: {target}")


def _assert_same_repository(context: RepoContext, worktree: Path) -> None:
    value = Path(_git(worktree, "rev-parse", "--git-common-dir"))
    common = _canonical(value if value.is_absolute() else worktree / value)
    if _path_key(common) != _path_key(context.common_dir):
        raise Refusal(f"worktree belongs to another repository: {worktree}")


def _claim_from_origin_main(context: RepoContext, package: str) -> dict[str, Any]:
    _validate_package(package)
    path = f"docs/governance/lane_claims/{package}.json"
    raw = _git_optional(context.root, "show", f"origin/main:{path}")
    if raw is None:
        raise Refusal(f"active claim is missing from fetched origin/main: {package}")
    try:
        claim = json.loads(raw)
    except json.JSONDecodeError as error:
        raise Refusal(f"claim on origin/main is invalid JSON: {package}") from error
    if claim.get("package") != package:
        raise Refusal("claim package identity does not match its filename")
    return claim


def _active_claim(
    context: RepoContext, package: str, task_ref: str
) -> dict[str, Any]:
    claim = _claim_from_origin_main(context, package)
    if claim.get("state") != "active":
        raise Refusal(f"claim is not active: {package}")
    if claim.get("writer_ref") != task_ref:
        raise Refusal("task-ref does not match the active claim writer_ref")
    branch = claim.get("branch")
    if not isinstance(branch, str) or not WORK_BRANCH_RE.fullmatch(branch):
        raise Refusal("active claim has an invalid work branch")
    return claim


def _claim_branch_proof(
    context: RepoContext,
    package: str,
    expected_head: str,
    *,
    required_state: str | None = None,
) -> ServerBranchProof:
    """Bind a package and HEAD to the exact current server-side claim branch."""

    claim = _claim_from_origin_main(context, package)
    if required_state is not None and claim.get("state") != required_state:
        raise Refusal(
            f"claim state must be {required_state!r} for server branch proof"
        )
    branch = claim.get("branch")
    if not isinstance(branch, str) or not WORK_BRANCH_RE.fullmatch(branch):
        raise Refusal("claim has an invalid work branch for server proof")
    fetched_tip = _fetch_origin_branch(context, branch)
    if fetched_tip is None:
        raise Refusal(f"claimed branch is absent from the server: {branch}")
    if fetched_tip != expected_head:
        raise Refusal(
            "server-verified claimed-branch tip does not equal the retirement HEAD"
        )
    return ServerBranchProof(package=package, branch=branch, sha=fetched_tip)


def _ref_sha(context: RepoContext, ref: str) -> str | None:
    value = _git_optional(context.root, "rev-parse", "--verify", f"{ref}^{{commit}}")
    return value.casefold() if value and SHA_RE.fullmatch(value.casefold()) else None


def _exact_commit(context: RepoContext, value: str) -> str:
    sha = _validate_sha(value)
    resolved = _ref_sha(context, sha)
    if resolved != sha:
        raise Refusal(f"commit object is not available: {sha}")
    return sha


def _is_pristine(path: Path) -> tuple[bool, list[str]]:
    payload = _git(
        path,
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
        "--ignored=matching",
    )
    entries = [entry for entry in payload.split("\0") if entry]
    return not entries, entries


def _current_branch(path: Path) -> str | None:
    value = _git_optional(path, "symbolic-ref", "--quiet", "--short", "HEAD")
    return value or None


def _normalized_sparse_paths(includes: Sequence[str]) -> list[str]:
    return sorted(
        set(CONTROL_SPARSE_PATHS) | {_normalize_include(item) for item in includes}
    )


def _configure_sparse(path: Path, includes: Sequence[str]) -> list[str]:
    normalized = _normalized_sparse_paths(includes)
    _git(path, "sparse-checkout", "init", "--no-cone")
    _git(path, "sparse-checkout", "set", "--no-cone", *normalized)
    return normalized


def _live_sparse_paths(path: Path) -> list[str]:
    enabled = _git_optional(
        path, "config", "--worktree", "--bool", "core.sparseCheckout"
    )
    cone = _git_optional(
        path, "config", "--worktree", "--bool", "core.sparseCheckoutCone"
    )
    if enabled != "true" or cone != "false":
        raise Refusal("active ephemeral worktree is not in exact non-cone sparse mode")
    output = _git(path, "sparse-checkout", "list")
    return sorted(
        {_normalize_include(line) for line in output.splitlines() if line}
    )


def _write_pending(
    context: RepoContext,
    registry: dict[str, Any],
    *,
    operation: str,
    path: Path,
    record: dict[str, Any],
) -> None:
    registry["pending"] = {
        "operation": operation,
        "path": str(_canonical(path)),
        "record": record,
        "started_at": _utc_now(),
    }
    _atomic_write(context.registry_path, registry)


def _write_control_repoint_pending(
    context: RepoContext,
    registry: dict[str, Any],
    *,
    record: dict[str, Any],
    before: dict[str, Any],
    target: dict[str, Any],
) -> None:
    registry["pending"] = {
        "operation": "control_repoint",
        "path": str(_canonical(record["path"])),
        "record": {
            "kind": record.get("kind"),
            "state": record.get("state"),
            "package": record.get("package"),
            "task_ref": record.get("task_ref"),
        },
        "before": before,
        "target": target,
        "started_at": _utc_now(),
    }
    _atomic_write(context.registry_path, registry)


def _reconcile_control_repoint(
    context: RepoContext,
    registry: dict[str, Any],
    pending: dict[str, Any],
) -> dict[str, Any]:
    path = _canonical(str(pending.get("path", "")))
    record = _record_by_path(registry, path)
    before = pending.get("before")
    target = pending.get("target")
    if (
        record is None
        or record.get("state") != "active"
        or record.get("kind") != "control_singleton"
        or not isinstance(before, dict)
        or not isinstance(target, dict)
    ):
        raise Refusal("pending control transition has no exact active singleton record")
    _assert_managed_target(registry, path)
    _assert_same_repository(context, path)
    live = _worktree_at(context.root, path)
    if live is None:
        raise Refusal("pending control singleton is not registered in Git")
    pristine, residue = _is_pristine(path)
    if not pristine:
        raise Refusal(
            "pending control transition contains residue and cannot be reconciled",
            blockers=residue,
        )
    live_identity = (live.get("branch"), live.get("head"))
    before_identity = (before.get("branch"), before.get("head"))
    target_identity = (target.get("branch"), target.get("head"))
    if live_identity not in {before_identity, target_identity}:
        raise Refusal(
            "pending control transition live branch/HEAD matches neither before nor target"
        )
    target_head = target.get("head")
    target_base = target.get("base")
    if (
        not isinstance(target_head, str)
        or not SHA_RE.fullmatch(target_head)
        or target_base != target_head
    ):
        raise Refusal("pending control transition target SHA is not exact")
    sparse_paths = target.get("sparse_paths")
    lease = target.get("lease")
    if not isinstance(sparse_paths, list) or not isinstance(lease, dict):
        raise Refusal("pending control transition target is structurally incomplete")
    normalized = _normalized_sparse_paths(sparse_paths)
    if normalized != sorted(set(sparse_paths)):
        raise Refusal("pending control sparse target is not normalized")
    _configure_sparse(path, normalized)
    _switch_control(
        context,
        path,
        base=target_head,
        branch=target.get("branch"),
        allow_current_moved=bool(target.get("allow_current_moved")),
    )
    completed = _worktree_at(context.root, path)
    if completed is None or (
        completed.get("branch"), completed.get("head")
    ) != target_identity:
        raise Refusal("pending control transition did not reach its exact target")
    record.update(
        {
            "state": "active",
            "package": target.get("package"),
            "branch": completed.get("branch"),
            "head": completed.get("head"),
            "task_ref": target.get("task_ref"),
            "lease": lease,
            "sparse_paths": normalized,
            "updated_at": _utc_now(),
        }
    )
    registry["pending"] = None
    _atomic_write(context.registry_path, registry)
    return {
        "operation": "control_repoint",
        "outcome": "completed",
        "path": str(path),
    }


def _reconcile_pending(
    context: RepoContext, registry: dict[str, Any]
) -> dict[str, Any] | None:
    pending = registry.get("pending")
    if not pending:
        return None
    if not isinstance(pending, dict) or pending.get("operation") not in {
        "create",
        "retire",
        "control_repoint",
    }:
        raise Refusal("registry contains an unknown pending operation")
    path = _canonical(str(pending.get("path", "")))
    on_disk = path.exists()
    listed = _worktree_at(context.root, path) is not None
    operation = pending["operation"]
    if on_disk != listed:
        raise Refusal(
            f"pending operation is ambiguous (filesystem/Git mismatch): {path}"
        )
    if operation == "control_repoint" and not on_disk:
        raise Refusal(
            "pending control singleton is absent from both filesystem and Git; "
            "registry and pending state were preserved"
        )
    if operation == "control_repoint":
        return _reconcile_control_repoint(context, registry, pending)
    record = _record_by_path(registry, path)
    if operation == "create":
        if not on_disk:
            if record and record.get("state") == "pending":
                registry["worktrees"].remove(record)
            registry["pending"] = None
            _atomic_write(context.registry_path, registry)
            return {"operation": operation, "outcome": "rolled_back", "path": str(path)}
        if record is None or record.get("state") != "pending":
            raise Refusal(f"pending create has no matching pending record: {path}")
        actual = _worktree_at(context.root, path)
        if actual is None or (
            actual.get("head"), actual.get("branch")
        ) != (record.get("head"), record.get("branch")):
            raise Refusal(f"pending create identity cannot be reconciled: {path}")
        if record.get("kind") in {"control_singleton", "ephemeral"}:
            pristine, residue = _is_pristine(path)
            if not pristine:
                raise Refusal(
                    f"pending sparse worktree contains residue: {path}", blockers=residue
                )
            record["sparse_paths"] = _configure_sparse(
                path, record.get("sparse_paths", ())
            )
        record["state"] = "active"
        record["updated_at"] = _utc_now()
        registry["pending"] = None
        _atomic_write(context.registry_path, registry)
        return {"operation": operation, "outcome": "completed", "path": str(path)}

    if on_disk:
        # Mutation either never began or ordinary Git removal refused.  Preserve it.
        registry["pending"] = None
        _atomic_write(context.registry_path, registry)
        return {"operation": operation, "outcome": "preserved", "path": str(path)}
    if record is None:
        raise Refusal(f"pending retirement has no matching registry record: {path}")
    record["state"] = "retired"
    record["retired_at"] = record.get("retired_at") or _utc_now()
    record["updated_at"] = _utc_now()
    record["lease"] = None
    registry["pending"] = None
    _atomic_write(context.registry_path, registry)
    return {"operation": operation, "outcome": "completed", "path": str(path)}


def _create_registered_worktree(
    context: RepoContext,
    registry: dict[str, Any],
    *,
    record: dict[str, Any],
    git_arguments: Sequence[str],
    sparse_paths: Sequence[str] = (),
) -> dict[str, Any]:
    path = _canonical(record["path"])
    if path.exists() or _worktree_at(context.root, path):
        raise Refusal(f"managed target is already occupied: {path}")
    _assert_managed_target(registry, path)
    path.parent.mkdir(parents=True, exist_ok=True)
    record["state"] = "pending"
    path_records = [
        existing
        for existing in registry["worktrees"]
        if _path_key(existing.get("path", "")) == _path_key(path)
    ]
    if not path_records:
        registry["worktrees"].append(record)
    elif len(path_records) != 1 or path_records[0] is not record:
        raise Refusal("deterministic managed path has conflicting registry history")
    _write_pending(
        context, registry, operation="create", path=path, record=record.copy()
    )
    arguments = list(git_arguments)
    if arguments[:1] == ["-b"] and len(arguments) == 3:
        add_arguments = ["-b", arguments[1], str(path), arguments[2]]
    elif arguments[:1] == ["--detach"] and len(arguments) == 2:
        add_arguments = ["--detach", str(path), arguments[1]]
    elif len(arguments) == 1:
        add_arguments = [str(path), arguments[0]]
    else:  # Internal callers must never construct an ambiguous Git invocation.
        raise Refusal("invalid guarded worktree creation arguments")
    _git(context.root, "worktree", "add", *add_arguments)
    if sparse_paths:
        record["sparse_paths"] = _configure_sparse(path, sparse_paths)
    actual = _worktree_at(context.root, path)
    if actual is None:
        raise Refusal(f"Git did not register the created worktree: {path}")
    if actual.get("head") != record.get("head"):
        raise Refusal(
            "created worktree HEAD differs from the journaled expected HEAD; "
            "pending state was preserved"
        )
    if actual.get("branch") != record.get("branch"):
        raise Refusal(
            "created worktree branch differs from the journaled expected branch; "
            "pending state was preserved"
        )
    record["state"] = "active"
    record["updated_at"] = _utc_now()
    registry["pending"] = None
    _atomic_write(context.registry_path, registry)
    return record


def command_init(context: RepoContext, args: argparse.Namespace) -> dict[str, Any]:
    _require_execute(args.execute)
    task_ref = _validate_task_ref(args.task_ref)
    managed_root = _canonical(
        args.managed_root
        or os.environ.get("PEERSLATE_WORKTREE_ROOT")
        or (Path.home() / "Documents" / "PeerSlateWorktrees")
    )
    evidence_root = _canonical(args.evidence_root)
    current = _worktrees(context.root)
    for root in (managed_root, evidence_root):
        if any(_is_within(root, entry["worktree"]) for entry in current):
            raise Refusal(f"configured root is inside a Git worktree: {root}")
        if _has_reparse_component(root):
            raise Refusal(f"configured root crosses a reparse point: {root}")
    if _is_within(evidence_root, managed_root) or _is_within(managed_root, evidence_root):
        raise Refusal("evidence root and managed root must be separate")
    managed_root.mkdir(parents=True, exist_ok=True)
    evidence_root.mkdir(parents=True, exist_ok=True)

    with _registry_lock(context.registry_path):
        existing = _load_registry(context.registry_path, required=False)
        if existing is not None:
            _assert_registry_identity(context, existing)
            if _path_key(existing["managed_root"]) != _path_key(managed_root) or _path_key(
                existing["evidence_root"]
            ) != _path_key(evidence_root):
                raise Refusal("registry is already initialized with different roots")
            return {
                "status": "already_initialized",
                "registry": str(context.registry_path),
                "worktree_count": len(existing["worktrees"]),
            }

        control_path = managed_root / "_control"
        records: list[dict[str, Any]] = []
        for entry in current:
            path = _canonical(entry["worktree"])
            is_control = _path_key(path) == _path_key(control_path)
            records.append(
                _new_record(
                    path=path,
                    kind="control_singleton" if is_control else "grandfathered_observation",
                    state="active",
                    package=None,
                    branch=entry.get("branch"),
                    head=entry.get("head"),
                    task_ref=task_ref if is_control else None,
                    lease=None,
                    sparse_paths=CONTROL_SPARSE_PATHS if is_control else (),
                )
            )
        registry = {
            "schema_version": SCHEMA_VERSION,
            "repository_common_dir": str(context.common_dir),
            "repository_primary_root": str(context.primary_root),
            "initialized_at": _utc_now(),
            "initialized_by": task_ref,
            "managed_root": str(managed_root),
            "evidence_root": str(evidence_root),
            "policy_activation_worktree_count": len(current),
            "worktrees": records,
            "pending": None,
            "evidence_allocations": [],
        }
        _atomic_write(context.registry_path, registry)
    return {
        "status": "initialized",
        "registry": str(context.registry_path),
        "managed_root": str(managed_root),
        "evidence_root": str(evidence_root),
        "grandfathered_count": sum(
            record["kind"] == "grandfathered_observation" for record in records
        ),
        "control_singleton_recognized": any(
            record["kind"] == "control_singleton" for record in records
        ),
    }


def command_adopt(context: RepoContext, args: argparse.Namespace) -> dict[str, Any]:
    _require_execute(args.execute)
    package = _validate_package(args.package)
    task_ref = _validate_task_ref(args.task_ref)
    _fetch_origin_main(context)
    claim = _active_claim(context, package, task_ref)
    path = _canonical(args.path)
    with _registry_lock(context.registry_path):
        registry = _load_registry(context.registry_path)
        assert registry is not None
        _assert_registry_identity(context, registry)
        recovered = _reconcile_pending(context, registry)
        if _path_key(path) == _path_key(context.primary_root):
            raise Refusal("the primary worktree cannot be adopted as package-durable")
        entry = _worktree_at(context.root, path)
        if entry is None:
            raise Refusal(f"path is not an exact registered Git worktree: {path}")
        _assert_same_repository(context, path)
        if entry.get("branch") != claim["branch"]:
            raise Refusal("worktree branch does not match the active claim")
        duplicates = [
            record
            for record in registry["worktrees"]
            if record.get("state") == "active"
            and record.get("kind") == "durable"
            and record.get("package") == package
            and _path_key(record["path"]) != _path_key(path)
        ]
        if duplicates:
            raise Refusal(
                f"package already has a durable worktree: {duplicates[0]['path']}"
            )
        record = _record_by_path(registry, path)
        inside_managed_root = _is_strictly_within(path, registry["managed_root"])
        if inside_managed_root:
            _assert_managed_target(registry, path)
        elif record is None or record.get("kind") != "grandfathered_observation":
            raise Refusal(
                "outside-root adoption is limited to an exact init-grandfathered record"
            )
        elif _has_reparse_component(path):
            raise Refusal("grandfathered adoption path crosses a reparse point")
        if record and record.get("kind") not in {
            "grandfathered_observation",
            "durable",
        }:
            raise Refusal("registry path has a non-durable managed role")
        if record is None:
            record = _new_record(
                path=path,
                kind="durable",
                state="active",
                package=package,
                branch=entry.get("branch"),
                head=entry.get("head"),
                task_ref=task_ref,
            )
            registry["worktrees"].append(record)
        else:
            record.update(
                {
                    "kind": "durable",
                    "state": "active",
                    "package": package,
                    "branch": entry.get("branch"),
                    "head": entry.get("head"),
                    "task_ref": task_ref,
                    "lease": None,
                    "outside_managed_root": not inside_managed_root,
                    "retirement_eligible": inside_managed_root,
                    "updated_at": _utc_now(),
                }
            )
        _atomic_write(context.registry_path, registry)
    return {
        "status": "adopted",
        "package": package,
        "path": str(path),
        "head": record["head"],
        "dirty_preserved": not _is_pristine(path)[0],
        "recovered_pending": recovered,
    }


def _existing_durable(
    registry: dict[str, Any], package: str
) -> list[dict[str, Any]]:
    return [
        record
        for record in registry["worktrees"]
        if record.get("state") == "active"
        and record.get("kind") == "durable"
        and record.get("package") == package
    ]


def command_ensure(context: RepoContext, args: argparse.Namespace) -> dict[str, Any]:
    _require_execute(args.execute)
    package = _validate_package(args.package)
    task_ref = _validate_task_ref(args.task_ref)
    _fetch_origin_main(context)
    claim = _active_claim(context, package, task_ref)
    branch = claim["branch"]
    fetched_branch_tip = _fetch_origin_branch(context, branch)
    with _registry_lock(context.registry_path):
        registry = _load_registry(context.registry_path)
        assert registry is not None
        _assert_registry_identity(context, registry)
        recovered = _reconcile_pending(context, registry)
        durable = _existing_durable(registry, package)
        if len(durable) > 1:
            raise Refusal("registry has duplicate durable worktrees for the package")
        if durable:
            record = durable[0]
            if record.get("task_ref") != task_ref or record.get("branch") != claim["branch"]:
                raise Refusal("registered durable worktree identity does not match claim")
            path = _canonical(record["path"])
            if record.get("outside_managed_root"):
                if _is_strictly_within(path, registry["managed_root"]):
                    raise Refusal("legacy containment marker no longer matches its path")
                if _has_reparse_component(path):
                    raise Refusal("grandfathered durable path crosses a reparse point")
            else:
                _assert_managed_target(registry, path)
            entry = _worktree_at(context.root, path)
            if entry is None or entry.get("branch") != claim["branch"]:
                raise Refusal("registered durable worktree is missing or mismatched")
            live_head = entry.get("head")
            if fetched_branch_tip and live_head != fetched_branch_tip:
                if _is_ancestor(context, str(live_head), fetched_branch_tip):
                    raise Refusal(
                        "registered durable branch is behind its exact fetched remote tip"
                    )
                if not _is_ancestor(context, fetched_branch_tip, str(live_head)):
                    raise Refusal(
                        "registered durable branch diverges from its exact fetched remote tip"
                    )
            record["head"] = entry.get("head")
            record["remote_branch_tip"] = fetched_branch_tip
            record["remote_branch_status"] = (
                "fetched" if fetched_branch_tip else "confirmed_absent"
            )
            record["updated_at"] = _utc_now()
            _atomic_write(context.registry_path, registry)
            return {
                "status": "reused",
                "package": package,
                "path": str(path),
                "head": record["head"],
                "recovered_pending": recovered,
            }

        branch_users = [
            entry for entry in _worktrees(context.root) if entry.get("branch") == branch
        ]
        if branch_users:
            raise Refusal(
                "claim branch already exists in another worktree; use exact adopt: "
                + branch_users[0]["worktree"]
            )
        managed_root = _canonical(registry["managed_root"])
        path = managed_root / package
        _assert_managed_target(registry, path)
        existing_path_record = _record_by_path(registry, path)
        if existing_path_record:
            if existing_path_record.get("state") == "active":
                raise Refusal("deterministic package path is already registered")
            if (
                existing_path_record.get("kind") != "durable"
                or existing_path_record.get("package") not in {None, package}
            ):
                raise Refusal("retired deterministic path has another registry identity")
        if path.exists() or _worktree_at(context.root, path):
            raise Refusal("deterministic package path is already occupied")

        local_ref = f"refs/heads/{branch}"
        local_sha = _ref_sha(context, local_ref)
        remote_sha = fetched_branch_tip
        origin_main = _ref_sha(context, "refs/remotes/origin/main")
        if origin_main is None:
            raise Refusal("fetched origin/main is unavailable")
        if local_sha and remote_sha and local_sha != remote_sha:
            if _is_ancestor(context, local_sha, remote_sha):
                relationship = "behind"
            elif _is_ancestor(context, remote_sha, local_sha):
                relationship = "ahead"
            else:
                relationship = "divergent"
            raise Refusal(
                "existing local claim branch is "
                f"{relationship}; creation must use the exact fetched remote tip"
            )
        if local_sha and not remote_sha and local_sha != origin_main:
            raise Refusal("existing unpushed claim branch is not at origin/main")
        if local_sha:
            git_arguments = (branch,)
            expected_head = local_sha
        elif remote_sha:
            git_arguments = ("-b", branch, remote_sha)
            expected_head = remote_sha
        else:
            git_arguments = ("-b", branch, origin_main)
            expected_head = origin_main
        if existing_path_record:
            record = existing_path_record
            if record.get("retired_at"):
                record["previous_retired_at"] = record.pop("retired_at")
            record.update(
                {
                    "kind": "durable",
                    "state": "pending",
                    "package": package,
                    "branch": branch,
                    "head": expected_head,
                    "task_ref": task_ref,
                    "lease": None,
                    "remote_branch_tip": remote_sha,
                    "remote_branch_status": (
                        "fetched" if remote_sha else "confirmed_absent"
                    ),
                    "reactivated_at": _utc_now(),
                    "updated_at": _utc_now(),
                }
            )
        else:
            record = _new_record(
                path=path,
                kind="durable",
                state="pending",
                package=package,
                branch=branch,
                head=expected_head,
                task_ref=task_ref,
            )
            record["remote_branch_tip"] = remote_sha
            record["remote_branch_status"] = (
                "fetched" if remote_sha else "confirmed_absent"
            )
        record = _create_registered_worktree(
            context,
            registry,
            record=record,
            git_arguments=git_arguments,
        )
    return {
        "status": "created",
        "package": package,
        "path": record["path"],
        "branch": record["branch"],
        "head": record["head"],
        "recovered_pending": recovered,
    }


def _control_record(
    context: RepoContext, registry: dict[str, Any]
) -> dict[str, Any] | None:
    path = _canonical(registry["managed_root"]) / "_control"
    record = _record_by_path(registry, path)
    if record and record.get("state") == "active":
        if record.get("kind") != "control_singleton":
            raise Refusal("deterministic control path has another registry role")
        return record
    return None


def _switch_control(
    context: RepoContext,
    path: Path,
    *,
    base: str,
    branch: str | None,
    allow_current_moved: bool = False,
) -> None:
    resolved_base = _ref_sha(context, base)
    if resolved_base is None:
        raise Refusal(f"control base is not a commit: {base}")
    current = _current_branch(path)
    current_head = _git(path, "rev-parse", "HEAD").casefold()
    if branch is None:
        if current is not None or current_head != resolved_base:
            _git(path, "switch", "--detach", resolved_base)
        return
    if not WORK_BRANCH_RE.fullmatch(branch):
        raise Refusal("control branch must be a normalized work/ or codex/ branch")
    other_users = [
        entry
        for entry in _worktrees(context.root)
        if entry.get("branch") == branch
        and _path_key(entry["worktree"]) != _path_key(path)
    ]
    if other_users:
        raise Refusal(f"control branch is checked out elsewhere: {other_users[0]['worktree']}")
    if current == branch:
        if current_head != resolved_base and not allow_current_moved:
            raise Refusal(
                "existing control branch moved beyond the requested base without the same lease"
            )
        return
    branch_sha = _ref_sha(context, f"refs/heads/{branch}")
    if branch_sha is not None:
        if branch_sha != resolved_base:
            raise Refusal("existing control branch is not at the requested base")
        _git(path, "switch", branch)
    else:
        _git(path, "switch", "-c", branch, resolved_base)


def _acquire_control_locked(
    context: RepoContext,
    registry: dict[str, Any],
    *,
    task_ref: str,
    purpose: str,
    package: str | None,
    base: str,
    branch: str | None,
    includes: Sequence[str],
) -> tuple[dict[str, Any], bool]:
    managed_root = _canonical(registry["managed_root"])
    path = managed_root / "_control"
    _assert_managed_target(registry, path)
    record = _control_record(context, registry)
    created = False
    same_lease = False
    if record is None:
        if _record_by_path(registry, path) is not None:
            raise Refusal("inactive control record requires manual reconciliation")
        if path.exists() or _worktree_at(context.root, path):
            raise Refusal("unregistered deterministic control worktree exists")
        head = _ref_sha(context, base)
        if head is None:
            raise Refusal(f"control base is not a commit: {base}")
        lease = {
            "task_ref": task_ref,
            "purpose": purpose,
            "package": package,
            "acquired_at": _utc_now(),
        }
        record = _new_record(
            path=path,
            kind="control_singleton",
            state="pending",
            package=package,
            branch=None,
            head=head,
            task_ref=task_ref,
            lease=lease,
            sparse_paths=includes,
        )
        record = _create_registered_worktree(
            context,
            registry,
            record=record,
            git_arguments=("--detach", head),
            sparse_paths=includes,
        )
        created = True
    path = _canonical(record["path"])
    _assert_same_repository(context, path)
    lease = record.get("lease")
    if lease and lease.get("task_ref") != task_ref:
        raise Refusal(
            f"control singleton is leased by another task: {lease.get('task_ref')}"
        )
    same_lease = bool(
        lease
        and lease.get("task_ref") == task_ref
        and lease.get("purpose") == purpose
        and lease.get("package") == package
    )
    if lease and not same_lease:
        raise Refusal("task already holds the singleton for a different purpose")
    requested_head = _ref_sha(context, base)
    if requested_head is None:
        raise Refusal(f"control base is not a commit: {base}")
    pristine, residue = _is_pristine(path)
    current_branch = _current_branch(path)
    current_head = _git(path, "rev-parse", "HEAD").casefold()
    sparse_paths = _normalized_sparse_paths(includes)
    repoint_needed = (
        (branch is None and (current_head != requested_head or current_branch is not None))
        or (
            branch is not None
            and (
                current_branch != branch
                or (not same_lease and current_head != requested_head)
            )
        )
    )
    sparse_needed = sparse_paths != sorted(set(record.get("sparse_paths", ())))
    lease_needed = not same_lease
    if not pristine:
        if repoint_needed or sparse_needed or lease_needed:
            raise Refusal(
                f"control singleton has residue and cannot be mutated: {path}",
                blockers=residue,
            )
        # The same task may rerun a command to resolve its own retained residue;
        # no singleton metadata or checkout mutation occurs on this path.
        return record, created

    if branch is not None:
        if not WORK_BRANCH_RE.fullmatch(branch):
            raise Refusal("control branch must be a normalized work/ or codex/ branch")
        other_users = [
            entry
            for entry in _worktrees(context.root)
            if entry.get("branch") == branch
            and _path_key(entry["worktree"]) != _path_key(path)
        ]
        if other_users:
            raise Refusal(
                f"control branch is checked out elsewhere: {other_users[0]['worktree']}"
            )
        branch_sha = _ref_sha(context, f"refs/heads/{branch}")
        if current_branch == branch and current_head != requested_head and not same_lease:
            raise Refusal("existing control branch moved beyond the requested base")
        if current_branch != branch and branch_sha not in {None, requested_head}:
            raise Refusal("existing control branch is not at the requested base")

    target_head = (
        current_head
        if branch is not None and current_branch == branch and same_lease
        else requested_head
    )
    target_lease = {
        "task_ref": task_ref,
        "purpose": purpose,
        "package": package,
        "acquired_at": (
            lease.get("acquired_at") if same_lease and lease else _utc_now()
        ),
    }
    before = {
        "package": record.get("package"),
        "branch": current_branch,
        "head": current_head,
        "task_ref": record.get("task_ref"),
        "lease": lease,
        "sparse_paths": list(record.get("sparse_paths", ())),
    }
    target = {
        "package": package,
        "branch": branch,
        "head": target_head,
        "task_ref": task_ref,
        "lease": target_lease,
        "sparse_paths": sparse_paths,
        "base": target_head,
        "allow_current_moved": same_lease,
    }
    _write_control_repoint_pending(
        context,
        registry,
        record=record,
        before=before,
        target=target,
    )
    _configure_sparse(path, sparse_paths)
    _switch_control(
        context,
        path,
        base=target_head,
        branch=branch,
        allow_current_moved=same_lease,
    )
    entry = _worktree_at(context.root, path)
    if entry is None:
        raise Refusal("control singleton disappeared during acquisition")
    if (entry.get("branch"), entry.get("head")) != (branch, target_head):
        raise Refusal("control singleton did not reach the journaled branch/HEAD")
    record.update(
        {
            "state": "active",
            "package": package,
            "branch": entry.get("branch"),
            "head": entry.get("head"),
            "task_ref": task_ref,
            "lease": target_lease,
            "sparse_paths": sparse_paths,
            "updated_at": _utc_now(),
        }
    )
    registry["pending"] = None
    _atomic_write(context.registry_path, registry)
    return record, created


def command_control(context: RepoContext, args: argparse.Namespace) -> dict[str, Any]:
    _require_execute(args.execute)
    task_ref = _validate_task_ref(args.task_ref)
    package = _validate_package(args.package) if args.package else None
    if args.base in {"origin/main", "refs/remotes/origin/main"}:
        _fetch_origin_main(context)
    with _registry_lock(context.registry_path):
        registry = _load_registry(context.registry_path)
        assert registry is not None
        _assert_registry_identity(context, registry)
        recovered = _reconcile_pending(context, registry)
        record = _control_record(context, registry)
        if args.release:
            if record is None or not record.get("lease"):
                raise Refusal("control singleton has no active lease")
            if record["lease"].get("task_ref") != task_ref:
                raise Refusal("only the leasing task may release the singleton")
            pristine, residue = _is_pristine(_canonical(record["path"]))
            if not pristine:
                raise Refusal("control singleton has residue", blockers=residue)
            live = _worktree_at(context.root, _canonical(record["path"]))
            if live is None:
                raise Refusal("control singleton is no longer registered in Git")
            record["branch"] = live.get("branch")
            record["head"] = live.get("head")
            record["lease"] = None
            record["updated_at"] = _utc_now()
            _atomic_write(context.registry_path, registry)
            return {
                "status": "released",
                "path": record["path"],
                "task_ref": task_ref,
                "recovered_pending": recovered,
            }
        record, created = _acquire_control_locked(
            context,
            registry,
            task_ref=task_ref,
            purpose=args.purpose,
            package=package,
            base=args.base,
            branch=args.branch,
            includes=args.include,
        )
    return {
        "status": "created_and_leased" if created else "leased",
        "path": record["path"],
        "branch": record["branch"],
        "head": record["head"],
        "lease": record["lease"],
        "recovered_pending": recovered,
    }


def _command_environment(context: RepoContext, task_ref: str) -> dict[str, str]:
    digest = hashlib.sha256(task_ref.encode("utf-8")).hexdigest()[:16]
    runtime = context.common_dir / "peerslate" / "runtime" / digest
    runtime.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    environment.update(
        {
            "TEMP": str(runtime),
            "TMP": str(runtime),
            "TMPDIR": str(runtime),
            "XDG_CACHE_HOME": str(runtime / "cache"),
            "PYTHONPYCACHEPREFIX": str(runtime / "pycache"),
        }
    )
    return environment


def _run_verification(
    context: RepoContext, path: Path, task_ref: str, command: Sequence[str]
) -> subprocess.CompletedProcess[str]:
    if not command:
        raise Refusal("runtime-required verification needs a command after '--'")
    return subprocess.run(
        list(command),
        cwd=path,
        env=_command_environment(context, task_ref),
        text=True,
        encoding="utf-8",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def _retirement_blockers(
    context: RepoContext,
    registry: dict[str, Any],
    record: dict[str, Any],
    *,
    task_ref: str,
    expected_head: str,
    server_proof: ServerBranchProof | None,
    ephemeral_lease_token: str | None,
) -> list[str]:
    blockers: list[str] = []
    path = _canonical(record.get("path", ""))
    if record.get("state") != "active":
        blockers.append("registry record is not active")
    if record.get("kind") not in {"durable", "ephemeral"}:
        blockers.append("only durable or ephemeral managed worktrees may be retired")
    if record.get("task_ref") != task_ref:
        blockers.append("task-ref does not own this managed worktree")
    if record.get("head") != expected_head:
        blockers.append("expected HEAD does not equal the registry record")
    if record.get("kind") == "ephemeral":
        lease = record.get("lease")
        if lease is not None:
            if ephemeral_lease_token is None:
                blockers.append(
                    "ephemeral worktree has an active verification invocation lease"
                )
            elif not _ephemeral_lease_matches(
                record,
                ephemeral_lease_token,
                task_ref=task_ref,
                package=str(record.get("package")),
                path=path,
                head=expected_head,
                source_branch=str(record.get("source_branch")),
            ):
                blockers.append(
                    "ephemeral verification lease token or invocation identity does not match"
                )
        elif ephemeral_lease_token is not None:
            blockers.append("ephemeral verification lease is no longer active")
    elif ephemeral_lease_token is not None:
        blockers.append("an ephemeral lease token cannot authorize durable retirement")
    if server_proof is None:
        blockers.append("exact server-verified claim branch proof is missing")
    else:
        if server_proof.package != record.get("package"):
            blockers.append("server proof package does not match the registry record")
        if server_proof.sha != expected_head:
            blockers.append("server proof SHA does not equal expected HEAD")
        if record.get("kind") == "durable" and server_proof.branch != record.get(
            "branch"
        ):
            blockers.append("server proof branch does not match the durable branch")
        if record.get("kind") == "ephemeral" and server_proof.branch != record.get(
            "source_branch"
        ):
            blockers.append("server proof branch does not match the ephemeral source branch")
    try:
        _assert_managed_target(registry, path)
    except Refusal as error:
        blockers.append(str(error))
    if _path_key(path) == _path_key(context.primary_root):
        blockers.append("primary worktree retirement is prohibited")
    if _is_within(Path.cwd(), path):
        blockers.append("current process working directory is inside the target")
    all_worktrees = _worktrees(context.root)
    entry = next(
        (
            item
            for item in all_worktrees
            if _path_key(item.get("worktree", "")) == _path_key(path)
        ),
        None,
    )
    if entry is None:
        blockers.append("target is not an exact registered Git worktree")
    else:
        if entry.get("head") != expected_head:
            blockers.append("live worktree HEAD does not equal expected HEAD")
        if record.get("kind") == "ephemeral" and not entry.get("detached"):
            blockers.append("ephemeral worktree is not detached")
        if record.get("kind") == "durable" and entry.get("branch") != record.get(
            "branch"
        ):
            blockers.append("durable worktree branch does not match its record")
    nested = [
        item["worktree"]
        for item in all_worktrees
        if _path_key(item.get("worktree", "")) != _path_key(path)
        and _is_strictly_within(item.get("worktree", ""), path)
    ]
    if nested:
        blockers.append("nested Git worktree exists: " + ", ".join(nested))
    if path.exists():
        try:
            _assert_same_repository(context, path)
            pristine, residue = _is_pristine(path)
            if not pristine:
                blockers.append("worktree contains tracked, untracked, or ignored residue: " + repr(residue))
        except Refusal as error:
            blockers.append(str(error))
    if record.get("kind") == "durable":
        package = record.get("package")
        try:
            claim = _claim_from_origin_main(context, str(package))
            if claim.get("state") != "closed":
                blockers.append("durable package claim is not closed on origin/main")
            if claim.get("branch") != record.get("branch"):
                blockers.append("closed claim branch does not match the registry")
        except Refusal as error:
            blockers.append(str(error))
    return blockers


def _retire_record_locked(
    context: RepoContext,
    registry: dict[str, Any],
    record: dict[str, Any],
    *,
    task_ref: str,
    expected_head: str,
    server_proof: ServerBranchProof | None,
    ephemeral_lease_token: str | None = None,
) -> dict[str, Any]:
    blockers = _retirement_blockers(
        context,
        registry,
        record,
        task_ref=task_ref,
        expected_head=expected_head,
        server_proof=server_proof,
        ephemeral_lease_token=ephemeral_lease_token,
    )
    path = _canonical(record["path"])
    if blockers:
        raise Refusal(f"retirement refused for {path}", blockers=blockers)
    pending_record = dict(record)
    _write_pending(
        context,
        registry,
        operation="retire",
        path=path,
        record=pending_record,
    )
    # This is intentionally the only removal primitive in the module.
    _git(context.root, "worktree", "remove", str(path))
    if path.exists() or _worktree_at(context.root, path) is not None:
        raise Refusal("ordinary Git removal did not fully retire the exact worktree")
    record["state"] = "retired"
    record["retired_at"] = _utc_now()
    record["updated_at"] = record["retired_at"]
    record["lease"] = None
    registry["pending"] = None
    _atomic_write(context.registry_path, registry)
    return {
        "path": str(path),
        "head": expected_head,
        "server_branch": server_proof.branch if server_proof else None,
        "server_tip": server_proof.sha if server_proof else None,
    }


def command_retire(context: RepoContext, args: argparse.Namespace) -> dict[str, Any]:
    _require_execute(args.execute)
    task_ref = _validate_task_ref(args.task_ref)
    expected_head = _validate_sha(args.expected_head)
    path = _canonical(args.path)
    # Resolve the branch from a read-only snapshot so network refresh is never
    # performed while the machine-local mutation lock is held.  The locked
    # reload and exact record checks below catch any intervening local change.
    snapshot = _load_registry(context.registry_path)
    assert snapshot is not None
    snapshot_record = _record_by_path(snapshot, path)
    if snapshot_record is None:
        raise Refusal("retirement target is not an exact managed registry entry")
    if snapshot_record.get("kind") not in {"durable", "ephemeral"}:
        raise Refusal("retirement target does not have a removable managed kind")
    if snapshot_record.get("task_ref") != task_ref:
        raise Refusal("task-ref does not own this managed worktree")
    if (
        snapshot_record.get("kind") == "ephemeral"
        and snapshot_record.get("lease") is not None
    ):
        raise Refusal(
            "direct retirement is prohibited while an ephemeral verification "
            "invocation lease is active",
            blockers=[str(path)],
        )
    package = _validate_package(str(snapshot_record.get("package")))
    _fetch_origin_main(context)
    server_proof = _claim_branch_proof(
        context,
        package,
        expected_head,
        required_state="closed"
        if snapshot_record.get("kind") == "durable"
        else None,
    )
    with _registry_lock(context.registry_path):
        registry = _load_registry(context.registry_path)
        assert registry is not None
        _assert_registry_identity(context, registry)
        recovered = _reconcile_pending(context, registry)
        record = _record_by_path(registry, path)
        if record is None:
            raise Refusal("retirement target is not an exact managed registry entry")
        if record.get("kind") == "durable" and record.get("head") != expected_head:
            # A writer legitimately advances HEAD after ensure/adopt.  Reconcile
            # operational inventory only when every deletion-independent fact is
            # exact and the new tip is already durable; otherwise preserve it.
            live = _worktree_at(context.root, path)
            pristine, residue = _is_pristine(path) if path.exists() else (False, [])
            claim = _claim_from_origin_main(context, str(record.get("package")))
            reconcilable = (
                record.get("state") == "active"
                and record.get("task_ref") == task_ref
                and live is not None
                and live.get("branch") == record.get("branch")
                and live.get("head") == expected_head
                and pristine
                and claim.get("state") == "closed"
                and claim.get("branch") == record.get("branch")
                and server_proof.package == record.get("package")
                and server_proof.branch == record.get("branch")
                and server_proof.sha == expected_head
            )
            if not reconcilable:
                details = residue or [
                    "live/task/branch/closed-claim/server-tip facts did not all match"
                ]
                raise Refusal(
                    "durable HEAD moved and cannot be safely reconciled",
                    blockers=details,
                )
            record["previous_head"] = record.get("head")
            record["head"] = expected_head
            record["head_reconciled_at"] = _utc_now()
            record["updated_at"] = record["head_reconciled_at"]
            _atomic_write(context.registry_path, registry)
        result = _retire_record_locked(
            context,
            registry,
            record,
            task_ref=task_ref,
            expected_head=expected_head,
            server_proof=server_proof,
        )
    return {"status": "retired", **result, "recovered_pending": recovered}


def command_verify(
    context: RepoContext, args: argparse.Namespace
) -> tuple[dict[str, Any], int]:
    package = _validate_package(args.package)
    task_ref = _validate_task_ref(args.task_ref)
    _fetch_origin_main(context)
    claim = _claim_from_origin_main(context, package)
    if claim.get("state") != "active":
        raise Refusal("verification package claim is not active")
    branch = claim.get("branch")
    if not isinstance(branch, str) or not WORK_BRANCH_RE.fullmatch(branch):
        raise Refusal("verification claim has an invalid work branch")
    fetched_branch_tip = _fetch_origin_branch(context, branch)
    if fetched_branch_tip is None:
        raise Refusal("claimed branch is confirmed absent from origin")
    candidate = _exact_commit(context, args.candidate_sha)
    if candidate != fetched_branch_tip:
        raise Refusal(
            "candidate SHA must equal the exact fetched claimed-branch tip"
        )
    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    if not args.runtime_required:
        if args.ephemeral or args.include or command:
            raise Refusal("runtime options require explicit --runtime-required")
        return (
            {
                "status": "diff_only",
                "package": package,
                "candidate_sha": candidate,
                "server_branch": branch,
                "server_tip": fetched_branch_tip,
                "worktrees_created": 0,
            },
            0,
        )
    if not command:
        raise Refusal("runtime-required verification needs a nonempty command after '--'")
    surfaces = claim.get("surfaces", [])
    if not isinstance(surfaces, list) or not all(
        isinstance(surface, str) for surface in surfaces
    ):
        raise Refusal("verification claim surfaces must be a list of repository paths")
    includes = _normalized_sparse_paths([*args.include, *surfaces])
    if args.ephemeral:
        with _registry_lock(context.registry_path):
            registry = _load_registry(context.registry_path)
            assert registry is not None
            _assert_registry_identity(context, registry)
            recovered = _reconcile_pending(context, registry)
            path_token = hashlib.sha256(task_ref.encode("utf-8")).hexdigest()[:12]
            path = (
                _canonical(registry["managed_root"])
                / "_ephemeral"
                / f"{path_token}-{candidate[:12]}"
            )
            invocation_lease = _new_ephemeral_verification_lease(
                task_ref=task_ref,
                package=package,
                path=path,
                head=candidate,
                source_branch=branch,
            )
            lease_token = invocation_lease["token"]
            existing = _record_by_path(registry, path)
            if existing and existing.get("state") == "active":
                if (
                    existing.get("kind") != "ephemeral"
                    or existing.get("task_ref") != task_ref
                    or existing.get("head") != candidate
                    or existing.get("package") != package
                    or existing.get("source_branch") != branch
                ):
                    raise Refusal("deterministic ephemeral path has another owner")
                if existing.get("sparse_paths") != includes:
                    raise Refusal(
                        "active ephemeral sparse scope differs from the normalized "
                        "requested scope; reuse cannot mutate sparse checkout"
                    )
                if existing.get("lease") is not None:
                    raise Refusal(
                        "ephemeral worktree is leased by another verification invocation",
                        blockers=[str(path)],
                    )
                _assert_managed_target(registry, path)
                _assert_same_repository(context, path)
                live = _worktree_at(context.root, path)
                if (
                    live is None
                    or live.get("head") != candidate
                    or not live.get("detached")
                ):
                    raise Refusal(
                        "active ephemeral worktree does not have its exact detached Git identity"
                    )
                pristine, prior_residue = _is_pristine(path)
                if not pristine:
                    raise Refusal(
                        "active ephemeral worktree has tracked, untracked, or ignored "
                        "residue and cannot accept another verifier lease",
                        blockers=prior_residue,
                    )
                if _live_sparse_paths(path) != includes:
                    raise Refusal(
                        "active ephemeral live sparse scope differs from the normalized "
                        "requested scope; reuse was preserved without mutation"
                    )
                record = existing
                record["lease"] = invocation_lease
                record["verification_started_at"] = invocation_lease["acquired_at"]
                record["updated_at"] = record["verification_started_at"]
                _atomic_write(context.registry_path, registry)
            else:
                if path.exists() or _worktree_at(context.root, path):
                    raise Refusal("deterministic ephemeral path is occupied")
                if existing:
                    if (
                        existing.get("state") != "retired"
                        or existing.get("kind") != "ephemeral"
                        or existing.get("package") != package
                        or existing.get("task_ref") != task_ref
                        or existing.get("head") != candidate
                        or existing.get("source_branch") not in {None, branch}
                        or existing.get("lease") is not None
                    ):
                        raise Refusal(
                            "retired deterministic ephemeral record has another identity"
                        )
                    record = existing
                    if record.get("retired_at"):
                        record["previous_retired_at"] = record.pop("retired_at")
                    record.update(
                        {
                            "state": "pending",
                            "branch": None,
                            "source_branch": branch,
                            "lease": invocation_lease,
                            "sparse_paths": list(includes),
                            "reactivated_at": _utc_now(),
                            "verification_started_at": invocation_lease["acquired_at"],
                            "updated_at": _utc_now(),
                        }
                    )
                else:
                    record = _new_record(
                        path=path,
                        kind="ephemeral",
                        state="pending",
                        package=package,
                        branch=None,
                        head=candidate,
                        task_ref=task_ref,
                        lease=invocation_lease,
                        sparse_paths=includes,
                    )
                    record["source_branch"] = branch
                    record["verification_started_at"] = invocation_lease["acquired_at"]
                record = _create_registered_worktree(
                    context,
                    registry,
                    record=record,
                    git_arguments=("--detach", candidate),
                    sparse_paths=includes,
                )
        # Arbitrary verification never runs while the machine-local registry
        # lock is held.  Retirement requires a fresh post-command server proof.
        try:
            result = _run_verification(context, path, task_ref, command)
        except OSError as error:
            command_error = f"{type(error).__name__}: {error}"
            with _registry_lock(context.registry_path):
                registry = _load_registry(context.registry_path)
                assert registry is not None
                _assert_registry_identity(context, registry)
                recovered_after_command = _reconcile_pending(context, registry)
                record = _record_by_path(registry, path)
                if record is None:
                    raise Refusal(
                        "ephemeral registry record disappeared after command-start failure"
                    ) from error
                pristine, residue = _is_pristine(path)
                _clear_ephemeral_lease_locked(
                    context,
                    registry,
                    record,
                    lease_token,
                    task_ref=task_ref,
                    package=package,
                    path=path,
                    head=candidate,
                    source_branch=branch,
                )
            return (
                {
                    "status": "retained",
                    "package": package,
                    "candidate_sha": candidate,
                    "path": str(path),
                    "command_exit_code": None,
                    "command_start_error": command_error,
                    "stdout": "",
                    "stderr": "",
                    "residue": residue,
                    "proof_blockers": [],
                    "retirement": None,
                    "lease_released": True,
                    "recovered_pending": recovered or recovered_after_command,
                },
                REFUSAL_EXIT,
            )
        post_proof: ServerBranchProof | None = None
        proof_error: Refusal | None = None
        try:
            _fetch_origin_main(context)
            post_proof = _claim_branch_proof(
                context,
                package,
                candidate,
                required_state="active",
            )
        except Refusal as error:
            proof_error = error
        with _registry_lock(context.registry_path):
            registry = _load_registry(context.registry_path)
            assert registry is not None
            _assert_registry_identity(context, registry)
            recovered_after_command = _reconcile_pending(context, registry)
            record = _record_by_path(registry, path)
            if record is None:
                raise Refusal(
                    "ephemeral registry record disappeared while verification was running"
                )
            _require_ephemeral_lease(
                record,
                lease_token,
                task_ref=task_ref,
                package=package,
                path=path,
                head=candidate,
                source_branch=branch,
            )
            pristine, residue = _is_pristine(path)
            retired = False
            lease_released = False
            retire_result: dict[str, Any] | None = None
            retirement_error: Refusal | None = None
            if result.returncode == 0 and pristine and post_proof is not None:
                try:
                    retire_result = _retire_record_locked(
                        context,
                        registry,
                        record,
                        task_ref=task_ref,
                        expected_head=candidate,
                        server_proof=post_proof,
                        ephemeral_lease_token=lease_token,
                    )
                    retired = True
                except Refusal as error:
                    if not _pending_retirement_has_ephemeral_lease(
                        registry, path, lease_token
                    ):
                        _clear_ephemeral_lease_locked(
                            context,
                            registry,
                            record,
                            lease_token,
                            task_ref=task_ref,
                            package=package,
                            path=path,
                            head=candidate,
                            source_branch=branch,
                        )
                        retirement_error = error
                        lease_released = True
                    else:
                        on_disk = path.exists()
                        live = _worktree_at(context.root, path)
                        if on_disk != (live is not None):
                            raise Refusal(
                                "ordinary verifier retirement left filesystem/Git "
                                "ambiguity; pending state and lease were preserved",
                                blockers=[str(error)],
                            ) from error
                        _require_ephemeral_lease(
                            record,
                            lease_token,
                            task_ref=task_ref,
                            package=package,
                            path=path,
                            head=candidate,
                            source_branch=branch,
                        )
                        if not on_disk:
                            record["state"] = "retired"
                            record["retired_at"] = _utc_now()
                            record["updated_at"] = record["retired_at"]
                            record["lease"] = None
                            registry["pending"] = None
                            _atomic_write(context.registry_path, registry)
                            retire_result = {
                                "path": str(path),
                                "head": candidate,
                                "server_branch": post_proof.branch,
                                "server_tip": post_proof.sha,
                                "reconciled_after_git_refusal": True,
                            }
                            retired = True
                        else:
                            assert live is not None
                            still_pristine, removal_residue = _is_pristine(path)
                            if (
                                live.get("head") != candidate
                                or not live.get("detached")
                                or not still_pristine
                            ):
                                raise Refusal(
                                    "ordinary verifier retirement failure no longer has "
                                    "an exact pristine worktree; pending state and lease "
                                    "were preserved",
                                    blockers=removal_residue or [str(error)],
                                ) from error
                            registry["pending"] = None
                            record["lease"] = None
                            record["verification_released_at"] = _utc_now()
                            record["updated_at"] = record[
                                "verification_released_at"
                            ]
                            _atomic_write(context.registry_path, registry)
                            retirement_error = error
                            lease_released = True
            else:
                _clear_ephemeral_lease_locked(
                    context,
                    registry,
                    record,
                    lease_token,
                    task_ref=task_ref,
                    package=package,
                    path=path,
                    head=candidate,
                    source_branch=branch,
                )
                lease_released = True
        if retired:
            code = 0
        elif proof_error is not None or retirement_error is not None:
            code = REFUSAL_EXIT
        else:
            code = result.returncode if result.returncode not in {0, 2} else 1
        return (
            {
                "status": "passed_and_retired" if retired else "retained",
                "package": package,
                "candidate_sha": candidate,
                "path": str(path),
                "command_exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "residue": residue,
                "proof_blockers": [str(proof_error)] if proof_error else [],
                "retirement_blockers": (
                    [str(retirement_error)] if retirement_error else []
                ),
                "retirement": retire_result,
                "lease_released": retired or lease_released,
                "recovered_pending": recovered or recovered_after_command,
            },
            code,
        )

    with _registry_lock(context.registry_path):
        registry = _load_registry(context.registry_path)
        assert registry is not None
        _assert_registry_identity(context, registry)
        recovered = _reconcile_pending(context, registry)
        record, created = _acquire_control_locked(
            context,
            registry,
            task_ref=task_ref,
            purpose="verify",
            package=package,
            base=candidate,
            branch=None,
            includes=includes,
        )
        path = _canonical(record["path"])
        result = _run_verification(context, path, task_ref, command)
        pristine, residue = _is_pristine(path)
        released = result.returncode == 0 and pristine
        if released:
            record["lease"] = None
            record["updated_at"] = _utc_now()
            _atomic_write(context.registry_path, registry)
    code = 0 if released else (result.returncode if result.returncode not in {0, 2} else 1)
    return (
        {
            "status": "passed_and_released" if released else "retained_lease",
            "package": package,
            "candidate_sha": candidate,
            "path": str(path),
            "singleton_created": created,
            "command_exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "residue": residue,
            "recovered_pending": recovered,
        },
        code,
    )


def command_finalize_task(
    context: RepoContext, args: argparse.Namespace
) -> tuple[dict[str, Any], int]:
    _require_execute(args.execute)
    task_ref = _validate_task_ref(args.task_ref)
    retired: list[dict[str, Any]] = []
    released: list[str] = []
    retained: list[dict[str, Any]] = []
    snapshot = _load_registry(context.registry_path)
    assert snapshot is not None
    _assert_registry_identity(context, snapshot)
    snapshot_ephemeral = [
        record
        for record in snapshot["worktrees"]
        if record.get("state") == "active"
        and record.get("kind") == "ephemeral"
        and record.get("task_ref") == task_ref
    ]
    snapshot_leased = [
        record
        for record in snapshot_ephemeral
        if record.get("lease") is not None
    ]
    if snapshot_leased:
        raise Refusal(
            "finalize-task is prohibited while an ephemeral verification "
            "invocation lease is active",
            blockers=[str(record.get("path")) for record in snapshot_leased],
        )
    server_proofs: dict[str, ServerBranchProof] = {}
    proof_errors: dict[str, str] = {}
    if snapshot_ephemeral:
        try:
            _fetch_origin_main(context)
        except Refusal as error:
            for record in snapshot_ephemeral:
                proof_errors[_path_key(record["path"])] = str(error)
        else:
            for record in snapshot_ephemeral:
                key = _path_key(record["path"])
                try:
                    package = _validate_package(str(record.get("package")))
                    server_proofs[key] = _claim_branch_proof(
                        context,
                        package,
                        _validate_sha(str(record.get("head"))),
                    )
                except Refusal as error:
                    proof_errors[key] = str(error)
    with _registry_lock(context.registry_path):
        registry = _load_registry(context.registry_path)
        assert registry is not None
        _assert_registry_identity(context, registry)
        recovered = _reconcile_pending(context, registry)
        locked_leased = [
            record
            for record in registry["worktrees"]
            if record.get("state") == "active"
            and record.get("kind") == "ephemeral"
            and record.get("task_ref") == task_ref
            and record.get("lease") is not None
        ]
        if locked_leased:
            raise Refusal(
                "finalize-task is prohibited while an ephemeral verification "
                "invocation lease is active",
                blockers=[str(record.get("path")) for record in locked_leased],
            )
        for record in list(registry["worktrees"]):
            if record.get("state") != "active":
                continue
            if record.get("kind") == "control_singleton":
                lease = record.get("lease")
                if not lease or lease.get("task_ref") != task_ref:
                    continue
                pristine, residue = _is_pristine(_canonical(record["path"]))
                if pristine:
                    live = _worktree_at(context.root, _canonical(record["path"]))
                    if live is None:
                        retained.append(
                            {
                                "path": record["path"],
                                "blockers": ["control singleton is no longer registered in Git"],
                            }
                        )
                        continue
                    record["branch"] = live.get("branch")
                    record["head"] = live.get("head")
                    record["lease"] = None
                    record["updated_at"] = _utc_now()
                    released.append(record["path"])
                    _atomic_write(context.registry_path, registry)
                else:
                    retained.append({"path": record["path"], "blockers": residue})
            elif record.get("kind") == "ephemeral" and record.get("task_ref") == task_ref:
                proof_key = _path_key(record["path"])
                proof_error = proof_errors.get(proof_key)
                server_proof = server_proofs.get(proof_key)
                if proof_error or server_proof is None:
                    retained.append(
                        {
                            "path": record["path"],
                            "blockers": [
                                proof_error
                                or "no pre-lock exact server branch proof was available"
                            ],
                        }
                    )
                    continue
                try:
                    retired.append(
                        _retire_record_locked(
                            context,
                            registry,
                            record,
                            task_ref=task_ref,
                            expected_head=record["head"],
                            server_proof=server_proof,
                        )
                    )
                except Refusal as error:
                    retained.append(
                        {"path": record["path"], "blockers": error.blockers or [str(error)]}
                    )
    return (
        {
            "status": "complete" if not retained else "incomplete",
            "task_ref": task_ref,
            "released_singletons": released,
            "retired_ephemeral": retired,
            "retained": retained,
            "recovered_pending": recovered,
        },
        0 if not retained else REFUSAL_EXIT,
    )


def _all_claims(context: RepoContext) -> list[dict[str, Any]]:
    names = _git_optional(
        context.root,
        "ls-tree",
        "-r",
        "--name-only",
        "origin/main",
        "docs/governance/lane_claims",
    )
    if names is None:
        return []
    claims: list[dict[str, Any]] = []
    prefix = "docs/governance/lane_claims/"
    for name in names.splitlines():
        if not name.startswith(prefix) or "/" in name[len(prefix) :] or not name.endswith(
            ".json"
        ):
            continue
        raw = _git_optional(context.root, "show", f"origin/main:{name}")
        if raw is None:
            continue
        try:
            claim = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(claim, dict):
            claims.append(claim)
    return claims


def _audit_without_tokens(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _audit_without_tokens(item)
            for key, item in value.items()
            if key != "token"
        }
    if isinstance(value, list):
        return [_audit_without_tokens(item) for item in value]
    return value


def command_audit(context: RepoContext, args: argparse.Namespace) -> dict[str, Any]:
    del args
    current = _worktrees(context.root)
    registry = _load_registry(context.registry_path, required=False)
    if registry is None:
        return {
            "status": "uninitialized",
            "registry": str(context.registry_path),
            "current_worktree_count": len(current),
            "mutation_performed": False,
        }
    _assert_registry_identity(context, registry)
    current_by_path = {_path_key(entry["worktree"]): entry for entry in current}
    active = [record for record in registry["worktrees"] if record.get("state") == "active"]
    active_records_by_path: dict[str, list[dict[str, Any]]] = {}
    active_canonical_paths: set[str] = set()
    for record in active:
        key = _path_key(record.get("path", ""))
        active_records_by_path.setdefault(key, []).append(record)
        active_canonical_paths.add(key)
    unregistered = [
        entry
        for entry in current
        if _path_key(entry["worktree"]) not in active_canonical_paths
    ]
    mismatches: list[dict[str, Any]] = []
    for record in registry["worktrees"]:
        if record.get("state") != "active":
            continue
        live = current_by_path.get(_path_key(record.get("path", "")))
        if live is None:
            mismatches.append({"path": record.get("path"), "reason": "not_registered_in_git"})
            continue
        differences = [
            field
            for field in ("branch", "head")
            if record.get(field) != live.get(field)
        ]
        if differences:
            mismatches.append(
                {
                    "path": record.get("path"),
                    "reason": "live_identity_mismatch",
                    "fields": differences,
                    "live": {field: live.get(field) for field in differences},
                    "recorded": {field: record.get(field) for field in differences},
                }
            )
    duplicate_paths = [
        records[0].get("path")
        for records in active_records_by_path.values()
        if len(records) > 1
    ]
    duplicate_packages = sorted(
        package
        for package in {record.get("package") for record in active if record.get("package")}
        if sum(
            record.get("kind") == "durable" and record.get("package") == package
            for record in active
        )
        > 1
    )
    duplicate_branches = sorted(
        branch
        for branch in {record.get("branch") for record in active if record.get("branch")}
        if sum(record.get("branch") == branch for record in active) > 1
    )
    durable_packages = {
        record.get("package")
        for record in active
        if record.get("kind") == "durable"
    }
    missing_durable = sorted(
        claim.get("package")
        for claim in _all_claims(context)
        if claim.get("state") == "active"
        and claim.get("package") not in durable_packages
    )
    kinds: dict[str, list[str]] = {}
    for record in active:
        kinds.setdefault(record.get("kind", "unknown"), []).append(record.get("path"))
    active_ephemeral_leases = [
        {
            "path": record.get("path"),
            "package": record.get("package"),
            "task_ref": record.get("task_ref"),
            "head": record.get("head"),
            "source_branch": record.get("source_branch"),
            "lease": {
                "purpose": record["lease"].get("purpose"),
                "pid": record["lease"].get("pid"),
                "acquired_at": record["lease"].get("acquired_at"),
            }
            if isinstance(record.get("lease"), dict)
            else {"status": "malformed"},
        }
        for record in active
        if record.get("kind") == "ephemeral" and record.get("lease") is not None
    ]
    lock_present = (context.registry_path.parent / LOCK_DIRECTORY_NAME).exists()
    return {
        "status": "ok"
        if not (
            unregistered
            or mismatches
            or duplicate_paths
            or duplicate_packages
            or duplicate_branches
            or missing_durable
            or registry.get("pending")
            or active_ephemeral_leases
            or lock_present
        )
        else "attention",
        "registry": str(context.registry_path),
        "initialized_at": registry["initialized_at"],
        "managed_root": registry["managed_root"],
        "current_worktree_count": len(current),
        "registered_active_count": len(active),
        "by_kind": {key: sorted(value) for key, value in sorted(kinds.items())},
        "unregistered_post_policy_growth": unregistered,
        "mismatches": mismatches,
        "duplicates": {
            "paths": duplicate_paths,
            "packages": duplicate_packages,
            "branches": duplicate_branches,
        },
        "active_claims_without_durable_worktree": missing_durable,
        "active_ephemeral_invocation_leases": active_ephemeral_leases,
        "pending": _audit_without_tokens(registry.get("pending")),
        "lock_present": lock_present,
        "mutation_performed": False,
    }


def command_evidence_path(
    context: RepoContext, args: argparse.Namespace
) -> dict[str, Any]:
    _require_execute(args.execute)
    package = _validate_package(args.package)
    task_ref = _validate_task_ref(args.task_ref)
    if args.storage_class not in STORAGE_CLASSES:
        raise Refusal("unknown evidence storage class")
    if args.byte_budget < 0:
        raise Refusal("byte-budget must be zero or positive")
    if not SLUG_RE.fullmatch(args.label):
        raise Refusal("label must be a lowercase filesystem-safe slug")
    with _registry_lock(context.registry_path):
        registry = _load_registry(context.registry_path)
        assert registry is not None
        _assert_registry_identity(context, registry)
        recovered = _reconcile_pending(context, registry)
        evidence_root = _canonical(registry["evidence_root"])
        current = _worktrees(context.root)
        if any(_is_within(evidence_root, entry["worktree"]) for entry in current):
            raise Refusal("registered evidence root is now inside a Git worktree")
        if _has_reparse_component(evidence_root):
            raise Refusal("registered evidence root crosses a reparse point")
        task_token = hashlib.sha256(task_ref.encode("utf-8")).hexdigest()[:12]
        path = evidence_root / args.storage_class / package / args.label / task_token
        if _has_reparse_component(path, floor=evidence_root):
            raise Refusal("evidence allocation path crosses a reparse point")
        active_full_count = sum(
            entry.get("kind") in {"durable", "grandfathered_observation"}
            and entry.get("state") == "active"
            for entry in registry["worktrees"]
        )
        projected = args.byte_budget * active_full_count
        allocation_id = hashlib.sha256(
            f"{package}\0{task_ref}\0{args.storage_class}\0{args.label}".encode("utf-8")
        ).hexdigest()[:24]
        existing = next(
            (
                item
                for item in registry["evidence_allocations"]
                if item.get("allocation_id") == allocation_id
            ),
            None,
        )
        values = {
            "allocation_id": allocation_id,
            "package": package,
            "task_ref": task_ref,
            "storage_class": args.storage_class,
            "byte_budget": args.byte_budget,
            "label": args.label,
            "path": str(path),
            "retention_reason": args.retention_reason,
            "close_condition": args.close_condition,
            "projected_worktree_replication_bytes": projected,
            "external_storage_recommended": projected >= GIB,
        }
        if existing:
            comparable = {key: existing.get(key) for key in values}
            if comparable != values:
                raise Refusal("deterministic evidence allocation conflicts with its record")
            status = "reused"
        else:
            values["created_at"] = _utc_now()
            registry["evidence_allocations"].append(values)
            status = "created"
        path.mkdir(parents=True, exist_ok=True)
        _atomic_write(context.registry_path, registry)
    return {
        "status": status,
        **values,
        "recovered_pending": recovered,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo",
        help="repository worktree used to locate the shared Git common directory",
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    audit = subparsers.add_parser("audit", help="read-only registry/Git reconciliation")
    audit.add_argument("--json", action="store_true", help="accepted for compatibility; JSON is always emitted")

    init = subparsers.add_parser("init", help="initialize machine-local inventory")
    init.add_argument("--task-ref", required=True)
    init.add_argument("--evidence-root", required=True)
    init.add_argument("--managed-root")
    init.add_argument("--execute", action="store_true")

    adopt = subparsers.add_parser("adopt", help="adopt an exact existing worktree")
    adopt.add_argument("--package", required=True)
    adopt.add_argument("--path", required=True)
    adopt.add_argument("--task-ref", required=True)
    adopt.add_argument("--execute", action="store_true")

    ensure = subparsers.add_parser("ensure", help="create/reuse one durable package worktree")
    ensure.add_argument("--package", required=True)
    ensure.add_argument("--task-ref", required=True)
    ensure.add_argument("--execute", action="store_true")

    control = subparsers.add_parser("control", help="lease the reusable sparse control singleton")
    control.add_argument("--task-ref", required=True)
    control.add_argument("--purpose", default="control")
    control.add_argument("--package")
    control.add_argument("--base", default="origin/main")
    control.add_argument("--branch")
    control.add_argument("--include", action="append", default=[])
    control.add_argument("--release", action="store_true")
    control.add_argument("--execute", action="store_true")

    verify = subparsers.add_parser("verify", help="diff-only or runnable exact-SHA verification")
    verify.add_argument("--package", required=True)
    verify.add_argument("--candidate-sha", required=True)
    verify.add_argument("--task-ref", required=True)
    verify.add_argument("--runtime-required", action="store_true")
    verify.add_argument("--include", action="append", default=[])
    verify.add_argument("--ephemeral", action="store_true")
    verify.add_argument("command", nargs=argparse.REMAINDER)

    retire = subparsers.add_parser("retire", help="retire one exact managed worktree")
    retire.add_argument("--path", required=True)
    retire.add_argument("--task-ref", required=True)
    retire.add_argument("--expected-head", required=True)
    retire.add_argument("--execute", action="store_true")

    finalize = subparsers.add_parser("finalize-task", help="release/retire this task's temporary resources")
    finalize.add_argument("--task-ref", required=True)
    finalize.add_argument("--execute", action="store_true")

    evidence = subparsers.add_parser("evidence-path", help="allocate a bounded external evidence path")
    evidence.add_argument("--package", required=True)
    evidence.add_argument("--task-ref", required=True)
    evidence.add_argument("--storage-class", choices=sorted(STORAGE_CLASSES), required=True)
    evidence.add_argument("--byte-budget", type=int, required=True)
    evidence.add_argument("--label", required=True)
    evidence.add_argument("--retention-reason", default="package evidence")
    evidence.add_argument("--close-condition", default="package close and custody verification")
    evidence.add_argument("--execute", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    try:
        args = parser.parse_args(argv)
        context = _repo_context(args.repo)
        if args.subcommand == "audit":
            payload, code = command_audit(context, args), 0
        elif args.subcommand == "init":
            payload, code = command_init(context, args), 0
        elif args.subcommand == "adopt":
            payload, code = command_adopt(context, args), 0
        elif args.subcommand == "ensure":
            payload, code = command_ensure(context, args), 0
        elif args.subcommand == "control":
            payload, code = command_control(context, args), 0
        elif args.subcommand == "verify":
            payload, code = command_verify(context, args)
        elif args.subcommand == "retire":
            payload, code = command_retire(context, args), 0
        elif args.subcommand == "finalize-task":
            payload, code = command_finalize_task(context, args)
        elif args.subcommand == "evidence-path":
            payload, code = command_evidence_path(context, args), 0
        else:  # pragma: no cover - argparse guarantees this
            raise Refusal("unknown subcommand")
        print(json.dumps({"ok": code == 0, **payload}, indent=2, sort_keys=True))
        return code
    except Refusal as error:
        print(
            json.dumps(
                {
                    "ok": False,
                    "status": "refused",
                    "error": str(error),
                    "blockers": error.blockers,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return REFUSAL_EXIT
    except KeyboardInterrupt:
        print(json.dumps({"ok": False, "status": "interrupted"}, sort_keys=True))
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
