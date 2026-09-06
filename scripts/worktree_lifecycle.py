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
from datetime import datetime, timezone, timedelta
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
DELIVERY_REF_RE = re.compile(r"^(?:task|session|agent|role):[A-Za-z0-9._:/-]{3,180}$")
OWNER_REASSIGNMENT_CONTROL_BRANCH_RE = re.compile(
    r"^work/[0-9]{4}-[0-9]{2}-[0-9]{2}-delivery-owner-reassignment-[a-z0-9-]+$"
)
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
OWNER_REASSIGNMENT_HANDOFF_FIELDS = {
    "type",
    "from_ref",
    "to_ref",
    "from_branch",
    "to_branch",
    "checkpoint_sha",
    "owner_authorization_ref",
}
OWNER_REASSIGNMENT_PREPARATION_IMMUTABLE_FIELDS = {
    "schema_version",
    "package",
    "owner_authorization_ref",
    "from_ref",
    "to_ref",
    "from_branch",
    "to_branch",
    "checkpoint_sha",
    "control_branch",
    "prepared_from_main",
    "new_branch_response",
    "source_snapshot",
    "prepared_at",
}
OWNER_REASSIGNMENT_PREPARATION_STATE_FIELDS = {
    "completed": set(),
    "consuming": {
        "consuming_at",
        "consuming_on_main",
        "consuming_receiver_path",
    },
    "consumed": {"consumed_at", "consumed_on_main"},
}
OWNER_REASSIGNMENT_SOURCE_SNAPSHOT_FIELDS = {
    "local_branch_sha",
    "worktrees",
    "durable_records",
}
OWNER_REASSIGNMENT_HEAD_RECONCILIATION_FIELDS = {
    "package",
    "from_ref",
    "from_branch",
    "previous_head",
    "checkpoint_sha",
    "owner_authorization_ref",
    "source_unavailable_ref",
    "reconciled_at",
}
CLOSED_CUSTODY_RETIREMENT_FIELDS = {
    "schema_version",
    "cleanup_package",
    "cleanup_task_ref",
    "cleanup_path",
    "cleanup_branch",
    "cleanup_head",
    "reviewed_candidate",
    "reviewer_ref",
    "lifecycle_script_blob",
    "owner_authorization_ref",
    "source_unavailable_ref",
    "target_package",
    "source_task_ref",
    "target_path",
    "target_branch",
    "registry_previous_head",
    "expected_head",
    "authoritative_main",
    "target_server_head",
    "recorded_at",
}
CLOSED_CUSTODY_REQUIRED_DOMAINS = {
    "governance:delivery:closed-custody-retirement",
    "tooling:worktree-lifecycle:closed-custody-retirement",
}
CLOSED_CUSTODY_REQUIRED_SURFACES = {
    "AGENTS.md",
    "START_HERE.md",
    "docs/governance/WORKTREE_LIFECYCLE.md",
    "scripts/worktree_lifecycle.py",
    "tests/test_worktree_lifecycle.py",
}


def _owner_reassignment_preparation_immutable_fields(
    record: dict[str, Any],
) -> set[str]:
    fields = set(OWNER_REASSIGNMENT_PREPARATION_IMMUTABLE_FIELDS)
    if "source_head_reconciliation" in record:
        fields.add("source_head_reconciliation")
    return fields


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


def _remote_branch_tuple(
    context: RepoContext, branches: Sequence[str]
) -> dict[str, str]:
    """Read one exact server advertisement for a complete branch tuple."""

    normalized = [
        branch if branch == "main" else _validate_work_branch(branch)
        for branch in branches
    ]
    if len(normalized) != len(set(normalized)):
        raise Refusal("remote branch tuple contains duplicate names")
    result = _git_result(
        context.root,
        "ls-remote",
        "--heads",
        "origin",
        *(f"refs/heads/{branch}" for branch in normalized),
    )
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip() or "git ls-remote failed"
        raise Refusal("could not confirm remote branch tuple: " + detail)
    expected_refs = {f"refs/heads/{branch}": branch for branch in normalized}
    observed: dict[str, str] = {}
    for line in result.stdout.splitlines():
        columns = line.split()
        if len(columns) != 2 or columns[1] not in expected_refs:
            raise Refusal("remote branch tuple lookup was ambiguous")
        branch = expected_refs[columns[1]]
        sha = columns[0].casefold()
        if branch in observed or not SHA_RE.fullmatch(sha):
            raise Refusal("remote branch tuple lookup was ambiguous")
        observed[branch] = sha
    if set(observed) != set(normalized):
        raise Refusal("remote branch tuple is incomplete")
    return observed


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
    confirmed_tip = _remote_branch_tip(context, branch)
    if fetched_tip != observed_tip or confirmed_tip != observed_tip:
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


def _validate_package(package: Any) -> str:
    if not isinstance(package, str) or not PACKAGE_RE.fullmatch(package):
        raise Refusal(f"invalid package identifier: {package!r}")
    return package


def _validate_task_ref(task_ref: Any) -> str:
    if (
        not isinstance(task_ref, str)
        or not task_ref
        or task_ref != task_ref.strip()
        or len(task_ref) > 240
        or ":" not in task_ref
        or any(ord(character) < 32 for character in task_ref)
    ):
        raise Refusal("task-ref must be a bounded opaque reference containing ':'")
    return task_ref


def _validate_delivery_ref(value: str) -> str:
    if not isinstance(value, str) or not DELIVERY_REF_RE.fullmatch(value):
        raise Refusal(
            "owner-reassignment references must be normalized opaque "
            "task/session/agent/role references"
        )
    return value


def _validate_sha(sha: str) -> str:
    normalized = sha.casefold()
    if not SHA_RE.fullmatch(normalized):
        raise Refusal("expected an exact 40-character commit SHA")
    return normalized


def _validate_work_branch(branch: str) -> str:
    components = branch.split("/") if isinstance(branch, str) else []
    if (
        not isinstance(branch, str)
        or branch != branch.strip()
        or not WORK_BRANCH_RE.fullmatch(branch)
        or branch.endswith("/main")
        or any(
            component in {"", ".", ".."}
            or component.endswith((".", ".lock"))
            or ".." in component
            for component in components
        )
    ):
        raise Refusal(f"branch must be a normalized non-main work branch: {branch!r}")
    return branch


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


def _validate_utc_timestamp(value: Any, *, field: str) -> str:
    if not isinstance(value, str):
        raise Refusal(f"owner-reassignment {field} must be an exact UTC timestamp")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as error:
        raise Refusal(
            f"owner-reassignment {field} must be an exact UTC timestamp"
        ) from error
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        raise Refusal(f"owner-reassignment {field} must be an exact UTC timestamp")
    return value


def validate_owner_reassignment_control_lease(
    lease: Any, *, task_ref: Any, package: Any
) -> None:
    """Require the exact control lease shape issued by this lifecycle tool."""

    expected_task_ref = _validate_delivery_ref(_validate_task_ref(task_ref))
    expected_package = _validate_package(package)
    if (
        not isinstance(lease, dict)
        or set(lease) != {"task_ref", "purpose", "package", "acquired_at"}
        or (
            lease.get("task_ref"),
            lease.get("purpose"),
            lease.get("package"),
        )
        != (expected_task_ref, "control", expected_package)
    ):
        raise Refusal("owner reassignment requires an exact lifecycle control lease")
    _validate_utc_timestamp(lease.get("acquired_at"), field="control acquired_at")


def _validate_preparation_sha(value: Any, *, field: str) -> str:
    if not isinstance(value, str):
        raise Refusal(f"owner-reassignment {field} must be an exact SHA string")
    try:
        return _validate_sha(value)
    except Refusal as error:
        raise Refusal(
            f"owner-reassignment {field} must be an exact SHA string"
        ) from error


def _validate_preparation_path(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not Path(value).is_absolute():
        raise Refusal(f"owner-reassignment {field} must be an absolute path")
    canonical = str(_canonical(value))
    if value != canonical:
        raise Refusal(f"owner-reassignment {field} must be canonical")
    return canonical


def _validate_owner_reassignment_source_snapshot(
    preparation: dict[str, Any],
) -> None:
    snapshot = preparation.get("source_snapshot")
    if not isinstance(snapshot, dict) or set(snapshot) != (
        OWNER_REASSIGNMENT_SOURCE_SNAPSHOT_FIELDS
    ):
        raise Refusal("owner-reassignment preparation source snapshot is inexact")

    checkpoint = preparation["checkpoint_sha"]
    from_branch = preparation["from_branch"]
    local_branch_sha = snapshot.get("local_branch_sha")
    if local_branch_sha is not None and _validate_preparation_sha(
        local_branch_sha, field="source local branch SHA"
    ) != checkpoint:
        raise Refusal(
            "owner-reassignment source local branch differs from the checkpoint"
        )

    worktrees = snapshot.get("worktrees")
    if not isinstance(worktrees, list):
        raise Refusal("owner-reassignment source worktree snapshots must be a list")
    worktree_paths: list[str] = []
    for item in worktrees:
        if not isinstance(item, dict) or set(item) != {"path", "branch", "head"}:
            raise Refusal("owner-reassignment source worktree snapshot is inexact")
        path = _validate_preparation_path(item.get("path"), field="source path")
        head = _validate_preparation_sha(
            item.get("head"), field="source worktree HEAD"
        )
        if item.get("branch") != from_branch or head != checkpoint:
            raise Refusal(
                "owner-reassignment source worktree snapshot changed identity"
            )
        worktree_paths.append(path)
    if worktree_paths and local_branch_sha != checkpoint:
        raise Refusal(
            "owner-reassignment source worktrees require the checkpoint local ref"
        )
    if len(worktree_paths) != len(
        set(map(_path_key, worktree_paths))
    ) or worktrees != sorted(
        worktrees,
        key=lambda item: _path_key(item["path"]),
    ):
        raise Refusal(
            "owner-reassignment source worktree snapshots are duplicate or unsorted"
        )

    durable_records = snapshot.get("durable_records")
    if not isinstance(durable_records, list) or len(durable_records) > 1:
        raise Refusal(
            "owner-reassignment durable source snapshot is duplicate or ambiguous"
        )
    durable_paths: list[str] = []
    for item in durable_records:
        expected_fields = {"path", "package", "task_ref", "branch", "head"}
        if not isinstance(item, dict) or set(item) != expected_fields:
            raise Refusal("owner-reassignment durable source snapshot is inexact")
        path = _validate_preparation_path(
            item.get("path"), field="durable source path"
        )
        head = _validate_preparation_sha(
            item.get("head"), field="durable source HEAD"
        )
        if (
            item.get("package") != preparation["package"]
            or item.get("task_ref") != preparation["from_ref"]
            or item.get("branch") != from_branch
            or head != checkpoint
        ):
            raise Refusal(
                "owner-reassignment durable source snapshot changed identity"
            )
        if _path_key(path) not in {_path_key(candidate) for candidate in worktree_paths}:
            raise Refusal(
                "owner-reassignment durable source is absent from its worktree snapshot"
            )
        durable_paths.append(path)
    if len(durable_paths) != len(set(map(_path_key, durable_paths))):
        raise Refusal("owner-reassignment durable source snapshot is duplicated")


def _expected_owner_reassignment_handoff(
    preparation: dict[str, Any],
) -> dict[str, Any]:
    return {
        "type": "owner_reassignment",
        "from_ref": preparation["from_ref"],
        "to_ref": preparation["to_ref"],
        "from_branch": preparation["from_branch"],
        "to_branch": preparation["to_branch"],
        "checkpoint_sha": preparation["checkpoint_sha"],
        "owner_authorization_ref": preparation["owner_authorization_ref"],
    }


def _validate_consuming_preparation_transition(
    registry: dict[str, Any], preparation: dict[str, Any]
) -> None:
    pending = registry.get("pending")
    if not isinstance(pending, dict) or pending.get("operation") != "create":
        raise Refusal(
            "owner-reassignment consuming preparation has no pending receiver creation"
        )
    if set(pending) != {
        "operation",
        "path",
        "record",
        "started_at",
        "owner_reassignment",
    }:
        raise Refusal(
            "owner-reassignment pending receiver creation has an inexact field set"
        )
    _validate_utc_timestamp(pending.get("started_at"), field="pending started_at")
    transition = pending.get("owner_reassignment")
    expected_transition_fields = {
        "preparation_id",
        "receiver_path",
        "origin_main",
        "source_before",
        "handoff",
    }
    if not isinstance(transition, dict) or set(transition) != expected_transition_fields:
        raise Refusal(
            "owner-reassignment consuming preparation has an inexact pending transition"
        )
    receiver_path = _validate_preparation_path(
        transition.get("receiver_path"), field="receiver path"
    )
    if (
        transition.get("preparation_id") != preparation["preparation_id"]
        or transition.get("origin_main") != preparation["consuming_on_main"]
        or receiver_path != preparation["consuming_receiver_path"]
        or _path_key(str(pending.get("path", ""))) != _path_key(receiver_path)
        or transition.get("handoff")
        != _expected_owner_reassignment_handoff(preparation)
    ):
        raise Refusal(
            "owner-reassignment pending receiver transition does not match its preparation"
        )

    pending_record = pending.get("record")
    if not isinstance(pending_record, dict):
        raise Refusal("owner-reassignment pending receiver record is missing")
    matching_targets = [
        record
        for record in registry["worktrees"]
        if isinstance(record, dict)
        and _path_key(str(record.get("path", ""))) == _path_key(receiver_path)
    ]
    if len(matching_targets) != 1 or matching_targets[0] != pending_record:
        raise Refusal(
            "owner-reassignment pending receiver registry custody is ambiguous"
        )
    target = matching_targets[0]
    if (
        target.get("kind") != "durable"
        or target.get("state") != "pending"
        or target.get("package") != preparation["package"]
        or target.get("task_ref") != preparation["to_ref"]
        or target.get("branch") != preparation["to_branch"]
        or target.get("head") != preparation["checkpoint_sha"]
        or target.get("owner_reassignment_preparation_id")
        != preparation["preparation_id"]
    ):
        raise Refusal(
            "owner-reassignment pending receiver record changed identity"
        )

    durable_snapshots = preparation["source_snapshot"]["durable_records"]
    source_before = transition.get("source_before")
    if not durable_snapshots:
        if source_before is not None:
            raise Refusal(
                "owner-reassignment pending source exists without prepared custody"
            )
        return
    if not isinstance(source_before, dict):
        raise Refusal("owner-reassignment pending source record is missing")
    durable_snapshot = durable_snapshots[0]
    if (
        any(
            source_before.get(field) != durable_snapshot[field]
            for field in ("path", "package", "task_ref", "branch", "head")
        )
        or source_before.get("kind") != "durable"
        or source_before.get("state") != "active"
    ):
        raise Refusal(
            "owner-reassignment pending source differs from prepared custody"
        )
    matching_sources = [
        record
        for record in registry["worktrees"]
        if isinstance(record, dict)
        and _path_key(str(record.get("path", "")))
        == _path_key(durable_snapshot["path"])
    ]
    if len(matching_sources) != 1 or matching_sources[0] != source_before:
        raise Refusal(
            "owner-reassignment pending source registry custody is ambiguous"
        )


def _validate_owner_reassignment_preparations(registry: dict[str, Any]) -> None:
    preparations = registry.get("owner_reassignment_preparations")
    if not isinstance(preparations, list):
        raise Refusal("registry owner-reassignment preparations must be a list")

    preparation_ids: set[str] = set()
    immutable_tuples: set[str] = set()
    handoff_tuples: set[tuple[Any, ...]] = set()
    successor_branches: set[str] = set()
    nonterminal_packages: set[str] = set()
    consuming: list[dict[str, Any]] = []
    by_status: dict[str, list[dict[str, Any]]] = {
        status: [] for status in OWNER_REASSIGNMENT_PREPARATION_STATE_FIELDS
    }
    package_positions: dict[str, list[int]] = {}
    for index, preparation in enumerate(preparations):
        if not isinstance(preparation, dict):
            raise Refusal("owner-reassignment preparation must be an object")
        status = preparation.get("status")
        if (
            not isinstance(status, str)
            or status not in OWNER_REASSIGNMENT_PREPARATION_STATE_FIELDS
        ):
            raise Refusal("owner-reassignment preparation state is invalid")
        expected_fields = (
            _owner_reassignment_preparation_immutable_fields(preparation)
            | {"status", "preparation_id"}
            | OWNER_REASSIGNMENT_PREPARATION_STATE_FIELDS[status]
        )
        if set(preparation) != expected_fields:
            raise Refusal("owner-reassignment preparation has an inexact field set")
        if type(preparation.get("schema_version")) is not int or preparation.get(
            "schema_version"
        ) != 1:
            raise Refusal("owner-reassignment preparation schema is unsupported")

        required_string_fields = {
            "package",
            "owner_authorization_ref",
            "from_ref",
            "to_ref",
            "from_branch",
            "to_branch",
            "control_branch",
            "new_branch_response",
        }
        if any(
            not isinstance(preparation.get(field), str)
            for field in required_string_fields
        ):
            raise Refusal(
                "owner-reassignment preparation string field has an invalid type"
            )
        package = _validate_package(preparation["package"])
        from_ref = _validate_delivery_ref(preparation["from_ref"])
        to_ref = _validate_delivery_ref(preparation["to_ref"])
        owner_ref = _validate_delivery_ref(preparation["owner_authorization_ref"])
        from_branch = _validate_work_branch(preparation["from_branch"])
        to_branch = _validate_work_branch(preparation["to_branch"])
        control_branch = _validate_work_branch(preparation["control_branch"])
        if not OWNER_REASSIGNMENT_CONTROL_BRANCH_RE.fullmatch(control_branch):
            raise Refusal(
                "owner-reassignment preparation control branch is invalid"
            )
        if from_ref == to_ref or len({from_branch, to_branch, control_branch}) != 3:
            raise Refusal(
                "owner-reassignment preparation must change writer and use distinct branches"
            )
        checkpoint = _validate_preparation_sha(
            preparation.get("checkpoint_sha"), field="checkpoint_sha"
        )
        _validate_preparation_sha(
            preparation.get("prepared_from_main"), field="prepared_from_main"
        )
        _validate_utc_timestamp(preparation.get("prepared_at"), field="prepared_at")
        response = preparation.get("new_branch_response")
        if response != f"*\t{checkpoint}:refs/heads/{to_branch}\t[new branch]":
            raise Refusal(
                "owner-reassignment preparation lacks the exact new-branch response"
            )
        _validate_owner_reassignment_source_snapshot(preparation)
        _validate_preparation_head_reconciliation(preparation)

        preparation_id = preparation.get("preparation_id")
        if (
            not isinstance(preparation_id, str)
            or not re.fullmatch(r"[0-9a-f]{64}", preparation_id)
            or preparation_id != _preparation_digest(preparation)
        ):
            raise Refusal("owner-reassignment preparation identity digest is invalid")
        immutable_key = json.dumps(
            {
                field: preparation[field]
                for field in sorted(
                    _owner_reassignment_preparation_immutable_fields(
                        preparation
                    )
                )
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        if preparation_id in preparation_ids or immutable_key in immutable_tuples:
            raise Refusal("owner-reassignment preparation is duplicated")
        preparation_ids.add(preparation_id)
        immutable_tuples.add(immutable_key)
        handoff_key = (
            package.casefold(),
            owner_ref,
            from_ref,
            to_ref,
            from_branch,
            to_branch,
            checkpoint,
        )
        if handoff_key in handoff_tuples:
            raise Refusal("owner-reassignment handoff tuple is replayed")
        handoff_tuples.add(handoff_key)
        if to_branch in successor_branches:
            raise Refusal("owner-reassignment successor branch proof is reused")
        successor_branches.add(to_branch)
        package_positions.setdefault(package.casefold(), []).append(index)
        by_status[status].append(preparation)

        if status in {"completed", "consuming"}:
            package_key = package.casefold()
            if package_key in nonterminal_packages:
                raise Refusal(
                    "package has incompatible nonterminal owner-reassignment preparations"
                )
            nonterminal_packages.add(package_key)
        if status == "consuming":
            _validate_utc_timestamp(
                preparation.get("consuming_at"), field="consuming_at"
            )
            consuming_on_main = _validate_preparation_sha(
                preparation.get("consuming_on_main"), field="consuming_on_main"
            )
            receiver_path = _validate_preparation_path(
                preparation.get("consuming_receiver_path"),
                field="consuming receiver path",
            )
            if not consuming_on_main or not receiver_path:
                raise Refusal("owner-reassignment consuming state is invalid")
            consuming.append(preparation)
        elif status == "consumed":
            _validate_utc_timestamp(
                preparation.get("consumed_at"), field="consumed_at"
            )
            _validate_preparation_sha(
                preparation.get("consumed_on_main"), field="consumed_on_main"
            )

    for positions in package_positions.values():
        package_history = [preparations[index] for index in positions]
        for previous, current in zip(package_history, package_history[1:]):
            if (
                current["from_ref"] != previous["to_ref"]
                or current["from_branch"] != previous["to_branch"]
            ):
                raise Refusal(
                    "package owner-reassignment preparation history is incompatible"
                )
        nonterminal_positions = [
            index
            for index in positions
            if preparations[index]["status"] in {"completed", "consuming"}
        ]
        if nonterminal_positions and nonterminal_positions[0] != positions[-1]:
            raise Refusal(
                "package nonterminal owner-reassignment preparation is not final"
            )

    pending = registry.get("pending")
    pending_transition = (
        pending.get("owner_reassignment") if isinstance(pending, dict) else None
    )
    if len(consuming) > 1:
        raise Refusal("registry has ambiguous consuming owner-reassignment custody")
    if consuming:
        _validate_consuming_preparation_transition(registry, consuming[0])
    elif pending_transition is not None:
        raise Refusal(
            "pending owner-reassignment receiver transition has no consuming preparation"
        )
    if isinstance(pending, dict) and pending.get("operation") == (
        "owner_reassignment_branch_create"
    ):
        pending_package = str(pending.get("package", "")).casefold()
        if pending_package in nonterminal_packages:
            raise Refusal(
                "pending owner-reassignment branch creation conflicts with prepared state"
            )

    for preparation in by_status["completed"]:
        preparation_id = preparation["preparation_id"]
        if any(
            isinstance(record, dict)
            and record.get("owner_reassignment_preparation_id") == preparation_id
            for record in registry["worktrees"]
        ):
            raise Refusal(
                "completed owner-reassignment preparation already has receiver custody"
            )
    for preparation in by_status["consumed"]:
        preparation_id = preparation["preparation_id"]
        receivers = [
            record
            for record in registry["worktrees"]
            if isinstance(record, dict)
            and record.get("owner_reassignment_preparation_id") == preparation_id
        ]
        if len(receivers) != 1:
            raise Refusal(
                "consumed owner-reassignment preparation has ambiguous receiver custody"
            )
        receiver = receivers[0]
        if (
            receiver.get("kind") not in {"durable", "reassignment_source"}
            or receiver.get("state") not in {"active", "retired"}
            or receiver.get("package") != preparation["package"]
            or receiver.get("task_ref") != preparation["to_ref"]
            or receiver.get("branch") != preparation["to_branch"]
            or not isinstance(receiver.get("head"), str)
            or not SHA_RE.fullmatch(receiver["head"])
        ):
            raise Refusal(
                "consumed owner-reassignment receiver custody changed identity"
            )
        durable_snapshots = preparation["source_snapshot"]["durable_records"]
        if durable_snapshots:
            source_snapshot = durable_snapshots[0]
            preserved_sources = [
                record
                for record in registry["worktrees"]
                if isinstance(record, dict)
                and _path_key(str(record.get("path", "")))
                == _path_key(source_snapshot["path"])
            ]
            if len(preserved_sources) != 1:
                raise Refusal(
                    "consumed owner-reassignment source custody is ambiguous"
                )
            source = preserved_sources[0]
            if (
                source.get("kind") != "reassignment_source"
                or source.get("state") not in {"active", "retired"}
                or any(
                    source.get(field) != source_snapshot[field]
                    for field in ("package", "task_ref", "branch", "head")
                )
                or source.get("preserved_by_owner_reassignment")
                != _expected_owner_reassignment_handoff(preparation)
            ):
                raise Refusal(
                    "consumed owner-reassignment source custody changed identity"
                )


def _pending_record_custody(
    registry: dict[str, Any],
    pending: dict[str, Any],
    *,
    expected_state: str,
    allowed_kinds: set[str] | None = None,
) -> dict[str, Any]:
    path = _validate_preparation_path(pending.get("path"), field="pending path")
    pending_record = pending.get("record")
    if not isinstance(pending_record, dict):
        raise Refusal("pending lifecycle operation has no exact record snapshot")
    matches = [
        record
        for record in registry.get("worktrees", [])
        if isinstance(record, dict)
        and _path_key(str(record.get("path", ""))) == _path_key(path)
    ]
    if len(matches) != 1 or matches[0] != pending_record:
        raise Refusal("pending lifecycle operation has ambiguous registry custody")
    record = matches[0]
    if record.get("state") != expected_state:
        raise Refusal("pending lifecycle record has an incompatible state")
    if allowed_kinds is not None and record.get("kind") not in allowed_kinds:
        raise Refusal("pending lifecycle record has an incompatible kind")
    return record


def _validate_pending_create(registry: dict[str, Any], pending: dict[str, Any]) -> None:
    expected_fields = {"operation", "path", "record", "started_at"}
    if "owner_reassignment" in pending:
        expected_fields.add("owner_reassignment")
    if set(pending) != expected_fields:
        raise Refusal("pending create has an inexact field set")
    record = _pending_record_custody(
        registry,
        pending,
        expected_state="pending",
        allowed_kinds={"control_singleton", "durable", "ephemeral"},
    )
    pending_records = [
        item
        for item in registry["worktrees"]
        if isinstance(item, dict) and item.get("state") == "pending"
    ]
    if pending_records != [record]:
        raise Refusal("pending create does not have one exact pending record")
    if "owner_reassignment" in pending:
        transition = pending.get("owner_reassignment")
        if not isinstance(transition, dict):
            raise Refusal("pending owner-reassignment create transition is invalid")


def _validate_pending_retire(registry: dict[str, Any], pending: dict[str, Any]) -> None:
    if set(pending) != {"operation", "path", "record", "started_at"}:
        raise Refusal("pending retirement has an inexact field set")
    _pending_record_custody(
        registry,
        pending,
        expected_state="active",
        allowed_kinds={"durable", "ephemeral"},
    )


def _validate_closed_custody_retirement(
    proof: Any, *, record: dict[str, Any] | None = None
) -> dict[str, Any]:
    if not isinstance(proof, dict) or set(proof) != CLOSED_CUSTODY_RETIREMENT_FIELDS:
        raise Refusal("closed-custody retirement proof has an inexact field set")
    if proof.get("schema_version") != 1:
        raise Refusal("closed-custody retirement proof schema is unsupported")
    for field in ("cleanup_package", "target_package"):
        _validate_package(proof.get(field))
    for field in (
        "cleanup_task_ref",
        "reviewer_ref",
        "owner_authorization_ref",
        "source_unavailable_ref",
        "source_task_ref",
    ):
        _validate_delivery_ref(str(proof.get(field, "")))
    if len(
        {
            proof["cleanup_task_ref"],
            proof["owner_authorization_ref"],
            proof["source_unavailable_ref"],
            proof["source_task_ref"],
        }
    ) != 4:
        raise Refusal(
            "closed-custody caller, owner, source, and source-unavailability "
            "references must be distinct"
        )
    if proof["reviewer_ref"] == proof["cleanup_task_ref"]:
        raise Refusal("closed-custody reviewer must be independent of the cleanup caller")
    for field in ("cleanup_branch", "target_branch"):
        _validate_work_branch(str(proof.get(field, "")))
    for field in (
        "cleanup_head",
        "reviewed_candidate",
        "lifecycle_script_blob",
        "registry_previous_head",
        "expected_head",
        "authoritative_main",
        "target_server_head",
    ):
        _validate_sha(str(proof.get(field, "")))
    for field in ("cleanup_path", "target_path"):
        value = proof.get(field)
        if (
            not isinstance(value, str)
            or not Path(value).is_absolute()
            or str(_canonical(value)) != value
        ):
            raise Refusal(f"closed-custody {field} is not exact and canonical")
    _validate_utc_timestamp(proof.get("recorded_at"), field="recorded_at")
    if proof["target_server_head"] != proof["expected_head"]:
        raise Refusal("closed-custody server proof does not equal expected HEAD")
    if record is not None and (
        record.get("state") != "retired"
        or record.get("kind") != "durable"
        or record.get("package") != proof["target_package"]
        or record.get("task_ref") != proof["source_task_ref"]
        or record.get("branch") != proof["target_branch"]
        or record.get("head") != proof["expected_head"]
        or record.get("path") != proof["target_path"]
        or record.get("retired_at") != proof["recorded_at"]
        or record.get("lease") is not None
    ):
        raise Refusal("closed-custody retirement proof lost target record custody")
    return proof


def _closed_custody_after_record(
    before: dict[str, Any], proof: dict[str, Any]
) -> dict[str, Any]:
    after = json.loads(json.dumps(before, sort_keys=True))
    after.update(
        {
            "state": "retired",
            "head": proof["expected_head"],
            "lease": None,
            "retired_at": proof["recorded_at"],
            "updated_at": proof["recorded_at"],
            "closed_custody_retirement": proof,
        }
    )
    return after


def _validate_pending_closed_custody(
    registry: dict[str, Any], pending: dict[str, Any]
) -> None:
    if set(pending) != {
        "operation",
        "path",
        "before_record",
        "after_record",
        "started_at",
    }:
        raise Refusal("pending closed-custody retirement has an inexact field set")
    _validate_utc_timestamp(pending.get("started_at"), field="pending started_at")
    path = _validate_preparation_path(pending.get("path"), field="pending path")
    before = pending.get("before_record")
    after = pending.get("after_record")
    if not isinstance(before, dict) or not isinstance(after, dict):
        raise Refusal("pending closed-custody record snapshots are missing")
    matches = [
        record
        for record in registry.get("worktrees", [])
        if isinstance(record, dict)
        and _path_key(str(record.get("path", ""))) == _path_key(path)
    ]
    if matches != [before]:
        raise Refusal("pending closed-custody retirement lost exact registry custody")
    proof = _validate_closed_custody_retirement(
        after.get("closed_custody_retirement"), record=after
    )
    if (
        before.get("state") != "active"
        or before.get("kind") != "durable"
        or before.get("lease") is not None
        or before.get("path") != path
        or "closed_custody_retirement" in before
        or proof["registry_previous_head"] != before.get("head")
        or proof["target_package"] != before.get("package")
        or proof["source_task_ref"] != before.get("task_ref")
        or proof["target_branch"] != before.get("branch")
        or proof["target_path"] != before.get("path")
    ):
        raise Refusal("pending closed-custody source record is incompatible")
    if after != _closed_custody_after_record(before, proof):
        raise Refusal("pending closed-custody target record changed unrelated fields")


def _validate_closed_custody_registry(registry: dict[str, Any]) -> None:
    seen_unavailability: set[str] = set()
    for record in registry.get("worktrees", []):
        if not isinstance(record, dict):
            continue
        proof = record.get("closed_custody_retirement")
        if proof is None:
            continue
        validated = _validate_closed_custody_retirement(proof, record=record)
        source_ref = validated["source_unavailable_ref"]
        if source_ref in seen_unavailability:
            raise Refusal("closed-custody source-unavailability proof is duplicated")
        seen_unavailability.add(source_ref)
    pending = registry.get("pending")
    if isinstance(pending, dict) and pending.get("operation") == "retire_closed_custody":
        after = pending.get("after_record")
        if isinstance(after, dict):
            proof = after.get("closed_custody_retirement")
            if (
                isinstance(proof, dict)
                and proof.get("source_unavailable_ref") in seen_unavailability
            ):
                raise Refusal(
                    "pending closed-custody source-unavailability proof is duplicated"
                )


def _validate_optional_control_identity(
    value: Any, *, field: str
) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise Refusal(f"pending control {field} has an invalid type")
    if field == "package":
        return _validate_package(value)
    if field == "task_ref":
        return _validate_task_ref(value)
    if field == "branch":
        return _validate_work_branch(value)
    raise AssertionError(field)


def _validate_pending_control_repoint(
    registry: dict[str, Any], pending: dict[str, Any]
) -> None:
    if set(pending) != {
        "operation",
        "path",
        "record",
        "before",
        "target",
        "started_at",
    }:
        raise Refusal("pending control repoint has an inexact field set")
    path = _validate_preparation_path(pending.get("path"), field="pending path")
    matches = [
        record
        for record in registry["worktrees"]
        if isinstance(record, dict)
        and _path_key(str(record.get("path", ""))) == _path_key(path)
    ]
    if len(matches) != 1:
        raise Refusal("pending control repoint has ambiguous registry custody")
    record = matches[0]
    projection = {
        "kind": record.get("kind"),
        "state": record.get("state"),
        "package": record.get("package"),
        "task_ref": record.get("task_ref"),
    }
    if (
        record.get("kind") != "control_singleton"
        or record.get("state") != "active"
        or pending.get("record") != projection
    ):
        raise Refusal("pending control repoint does not own the active singleton")
    before = pending.get("before")
    target = pending.get("target")
    if not isinstance(before, dict) or set(before) != {
        "package",
        "branch",
        "head",
        "task_ref",
        "lease",
        "sparse_paths",
    }:
        raise Refusal("pending control repoint before-state is inexact")
    if not isinstance(target, dict) or set(target) != {
        "package",
        "branch",
        "head",
        "task_ref",
        "lease",
        "sparse_paths",
        "base",
        "allow_current_moved",
    }:
        raise Refusal("pending control repoint target-state is inexact")
    if any(
        before.get(field) != record.get(field)
        for field in ("package", "branch", "head", "task_ref", "lease", "sparse_paths")
    ):
        raise Refusal("pending control repoint before-state lost registry custody")
    _validate_optional_control_identity(before.get("package"), field="package")
    _validate_optional_control_identity(before.get("branch"), field="branch")
    _validate_optional_control_identity(before.get("task_ref"), field="task_ref")
    _validate_preparation_sha(before.get("head"), field="pending control before HEAD")
    if before.get("lease") is not None and not isinstance(before.get("lease"), dict):
        raise Refusal("pending control repoint before-lease is invalid")
    if not isinstance(before.get("sparse_paths"), list) or not all(
        isinstance(item, str) for item in before["sparse_paths"]
    ):
        raise Refusal("pending control repoint before sparse paths are invalid")

    package = _validate_optional_control_identity(target.get("package"), field="package")
    branch = _validate_optional_control_identity(target.get("branch"), field="branch")
    task_ref = _validate_optional_control_identity(target.get("task_ref"), field="task_ref")
    head = _validate_preparation_sha(target.get("head"), field="pending control target HEAD")
    if target.get("base") != head or type(target.get("allow_current_moved")) is not bool:
        raise Refusal("pending control repoint target commit metadata is invalid")
    sparse_paths = target.get("sparse_paths")
    if not isinstance(sparse_paths, list) or sparse_paths != sorted(set(sparse_paths)):
        raise Refusal("pending control repoint target sparse paths are invalid")
    lease = target.get("lease")
    if not isinstance(lease, dict) or set(lease) != {
        "task_ref",
        "purpose",
        "package",
        "acquired_at",
    }:
        raise Refusal("pending control repoint target lease is inexact")
    if (
        lease.get("task_ref") != task_ref
        or lease.get("package") != package
        or not isinstance(lease.get("purpose"), str)
        or not lease.get("purpose")
    ):
        raise Refusal("pending control repoint target lease changed identity")
    _validate_utc_timestamp(lease.get("acquired_at"), field="control acquired_at")
    if branch is None and target.get("branch") is not None:
        raise Refusal("pending control repoint target branch is invalid")


def _validate_owner_reassignment_head_reconciliation_record(
    record: dict[str, Any],
) -> None:
    if "owner_reassignment_head_reconciliation" not in record:
        return
    proof = record.get("owner_reassignment_head_reconciliation")
    if not isinstance(proof, dict) or set(proof) != (
        OWNER_REASSIGNMENT_HEAD_RECONCILIATION_FIELDS
    ):
        raise Refusal("owner-reassignment source HEAD reconciliation proof is inexact")
    package = _validate_package(proof.get("package"))
    from_ref = _validate_delivery_ref(proof.get("from_ref"))
    from_branch = _validate_work_branch(proof.get("from_branch"))
    previous_head = _validate_preparation_sha(
        proof.get("previous_head"), field="source previous registry HEAD"
    )
    checkpoint = _validate_preparation_sha(
        proof.get("checkpoint_sha"), field="source reconciled registry HEAD"
    )
    owner_authorization_ref = _validate_delivery_ref(
        proof.get("owner_authorization_ref")
    )
    source_unavailable_ref = _validate_delivery_ref(
        proof.get("source_unavailable_ref")
    )
    if source_unavailable_ref in {from_ref, owner_authorization_ref}:
        raise Refusal(
            "source-unavailability evidence must be separate from source and "
            "owner-authorization references"
        )
    reconciled_at = _validate_utc_timestamp(
        proof.get("reconciled_at"), field="source HEAD reconciled_at"
    )
    if (
        previous_head == checkpoint
        or record.get("package") != package
        or record.get("task_ref") != from_ref
        or record.get("branch") != from_branch
        or record.get("previous_head") != previous_head
        or record.get("head") != checkpoint
        or record.get("head_reconciled_at") != reconciled_at
        or record.get("remote_branch_tip") != checkpoint
        or record.get("remote_branch_status") != "fetched"
    ):
        raise Refusal("owner-reassignment source HEAD reconciliation changed identity")


def _validate_preparation_head_reconciliation(
    preparation: dict[str, Any],
) -> None:
    if "source_head_reconciliation" not in preparation:
        return
    proof = preparation.get("source_head_reconciliation")
    if not isinstance(proof, dict):
        raise Refusal("source HEAD reconciliation preparation proof is invalid")
    durable = preparation.get("source_snapshot", {}).get("durable_records")
    if not isinstance(durable, list) or len(durable) != 1:
        raise Refusal(
            "source HEAD reconciliation requires one prepared durable source"
        )
    snapshot = durable[0]
    if not isinstance(snapshot, dict):
        raise Refusal("source HEAD reconciliation durable source is invalid")
    synthetic_record = {
        **snapshot,
        "previous_head": proof.get("previous_head")
        if isinstance(proof, dict)
        else None,
        "head_reconciled_at": proof.get("reconciled_at")
        if isinstance(proof, dict)
        else None,
        "remote_branch_tip": snapshot.get("head"),
        "remote_branch_status": "fetched",
        "owner_reassignment_head_reconciliation": proof,
    }
    _validate_owner_reassignment_head_reconciliation_record(synthetic_record)
    if (
        proof.get("owner_authorization_ref")
        != preparation.get("owner_authorization_ref")
        or proof.get("checkpoint_sha") != preparation.get("checkpoint_sha")
    ):
        raise Refusal(
            "source HEAD reconciliation is not bound to its preparation"
        )


def _pending_source_registry_reconciliation(
    registry: dict[str, Any], pending: dict[str, Any]
) -> dict[str, Any] | None:
    if "source_registry_reconciliation" not in pending:
        return None
    reconciliation = pending.get("source_registry_reconciliation")
    if not isinstance(reconciliation, dict) or set(reconciliation) != {
        "before",
        "after",
    }:
        raise Refusal("pending source registry reconciliation is inexact")
    before = reconciliation.get("before")
    after = reconciliation.get("after")
    required = {
        "path",
        "kind",
        "state",
        "package",
        "branch",
        "head",
        "task_ref",
        "lease",
    }
    if (
        not isinstance(before, dict)
        or not isinstance(after, dict)
        or not required.issubset(before)
        or not required.issubset(after)
    ):
        raise Refusal("pending source registry reconciliation record is incomplete")
    added = {
        "previous_head",
        "head_reconciled_at",
        "owner_reassignment_head_reconciliation",
    }
    if added & set(before) or set(after) != set(before) | added:
        raise Refusal("pending source registry reconciliation field set is invalid")
    proof = after.get("owner_reassignment_head_reconciliation")
    _validate_owner_reassignment_head_reconciliation_record(after)
    expected_after = json.loads(json.dumps(before, sort_keys=True))
    expected_after.update(
        {
            "previous_head": proof["previous_head"],
            "head": proof["checkpoint_sha"],
            "head_reconciled_at": proof["reconciled_at"],
            "updated_at": proof["reconciled_at"],
            "remote_branch_tip": proof["checkpoint_sha"],
            "remote_branch_status": "fetched",
            "owner_reassignment_head_reconciliation": proof,
        }
    )
    if after != expected_after:
        raise Refusal("pending source registry reconciliation changed unrelated fields")
    if (
        before.get("head") != proof.get("previous_head")
        or proof.get("owner_authorization_ref")
        != pending.get("owner_authorization_ref")
        or after.get("package") != pending.get("package")
        or after.get("task_ref") != pending.get("from_ref")
        or after.get("branch") != pending.get("from_branch")
        or after.get("head") != pending.get("checkpoint_sha")
        or after.get("kind") != "durable"
        or after.get("state") != "active"
        or after.get("lease") is not None
    ):
        raise Refusal("pending source registry reconciliation lost source custody")
    matches = [
        record
        for record in registry["worktrees"]
        if _path_key(str(record.get("path", "")))
        == _path_key(str(after.get("path", "")))
    ]
    if len(matches) != 1 or matches[0] != after:
        raise Refusal("pending source registry reconciliation is not registry-custodied")
    return reconciliation


def _validate_pending_branch_source_snapshots(
    registry: dict[str, Any], pending: dict[str, Any]
) -> None:
    checkpoint = pending["checkpoint_sha"]
    from_branch = pending["from_branch"]
    source_worktrees = pending.get("source_worktrees")
    if not isinstance(source_worktrees, list):
        raise Refusal("pending owner-reassignment source worktrees are invalid")
    paths: list[str] = []
    for item in source_worktrees:
        if not isinstance(item, dict) or set(item) != {"path", "branch", "head"}:
            raise Refusal("pending owner-reassignment source worktree is inexact")
        item_path = _validate_preparation_path(
            item.get("path"), field="pending source worktree path"
        )
        if (
            item.get("branch") != from_branch
            or _validate_preparation_sha(
                item.get("head"), field="pending source worktree HEAD"
            )
            != checkpoint
        ):
            raise Refusal("pending owner-reassignment source worktree changed identity")
        paths.append(item_path)
    if len(paths) != len(set(map(_path_key, paths))) or source_worktrees != sorted(
        source_worktrees, key=lambda item: _path_key(item["path"])
    ):
        raise Refusal("pending owner-reassignment source worktrees are ambiguous")

    durable = pending.get("source_durable_records")
    if not isinstance(durable, list) or len(durable) > 1:
        raise Refusal("pending owner-reassignment durable source is ambiguous")
    registry_candidates = [
        record
        for record in registry["worktrees"]
        if isinstance(record, dict)
        and record.get("state") == "active"
        and record.get("kind") == "durable"
        and (
            str(record.get("package", "")).casefold()
            == pending["package"].casefold()
            or record.get("branch") == from_branch
        )
    ]
    registry_snapshots = [
        {
            "path": record.get("path"),
            "package": record.get("package"),
            "task_ref": record.get("task_ref"),
            "branch": record.get("branch"),
            "head": record.get("head"),
        }
        for record in registry_candidates
    ]
    if len(registry_candidates) > 1 or durable != registry_snapshots:
        raise Refusal("pending owner-reassignment durable source lost registry custody")
    for item in durable:
        if not isinstance(item, dict) or set(item) != {
            "path",
            "package",
            "task_ref",
            "branch",
            "head",
        }:
            raise Refusal("pending owner-reassignment durable source is inexact")
        item_path = _validate_preparation_path(
            item.get("path"), field="pending durable source path"
        )
        if (
            item_path not in paths
            or item.get("package") != pending["package"]
            or item.get("task_ref") != pending["from_ref"]
            or item.get("branch") != from_branch
            or _validate_preparation_sha(
                item.get("head"), field="pending durable source HEAD"
            )
            != checkpoint
        ):
            raise Refusal("pending owner-reassignment durable source changed identity")
    _pending_source_registry_reconciliation(registry, pending)


def _validate_pending_owner_reassignment_branch_create(
    registry: dict[str, Any], pending: dict[str, Any]
) -> None:
    base_fields = {
        "operation",
        "package",
        "task_ref",
        "from_ref",
        "from_branch",
        "successor_branch",
        "checkpoint_sha",
        "owner_authorization_ref",
        "old_local_ref",
        "source_worktrees",
        "source_durable_records",
        "control_branch",
        "prepared_from_main",
        "live_claims_snapshot",
        "push_proven_new",
        "started_at",
    }
    push_proven = pending.get("push_proven_new")
    expected_fields = set(base_fields)
    if "source_registry_reconciliation" in pending:
        expected_fields.add("source_registry_reconciliation")
    if push_proven is True:
        expected_fields |= {"new_branch_response", "push_proven_at"}
    if type(push_proven) is not bool or set(pending) != expected_fields:
        raise Refusal("pending owner-reassignment branch creation is inexact")
    package = _validate_package(pending.get("package"))
    task_ref = _validate_delivery_ref(pending.get("task_ref"))
    from_ref = _validate_delivery_ref(pending.get("from_ref"))
    owner_ref = _validate_delivery_ref(pending.get("owner_authorization_ref"))
    from_branch = _validate_work_branch(pending.get("from_branch"))
    successor = _validate_work_branch(pending.get("successor_branch"))
    control_branch = _validate_work_branch(pending.get("control_branch"))
    checkpoint = _validate_preparation_sha(
        pending.get("checkpoint_sha"), field="pending checkpoint_sha"
    )
    _validate_preparation_sha(
        pending.get("prepared_from_main"), field="pending prepared_from_main"
    )
    _validate_utc_timestamp(pending.get("started_at"), field="pending started_at")
    if (
        task_ref == from_ref
        or len({from_branch, successor, control_branch}) != 3
        or not OWNER_REASSIGNMENT_CONTROL_BRANCH_RE.fullmatch(control_branch)
        or not owner_ref
        or not package
    ):
        raise Refusal("pending owner-reassignment branch identity is invalid")
    old_local_ref = pending.get("old_local_ref")
    if old_local_ref is not None and _validate_preparation_sha(
        old_local_ref, field="pending source local ref"
    ) != checkpoint:
        raise Refusal("pending owner-reassignment local source ref changed")
    _validate_pending_branch_source_snapshots(registry, pending)
    claims = pending.get("live_claims_snapshot")
    if not isinstance(claims, list) or not all(isinstance(item, dict) for item in claims):
        raise Refusal("pending owner-reassignment live claims snapshot is invalid")
    claim_packages: list[str] = []
    for claim in claims:
        claim_package = _validate_package(claim.get("package"))
        if claim.get("state") not in {"active", "paused"}:
            raise Refusal("pending owner-reassignment live claim state is invalid")
        _validate_work_branch(claim.get("branch"))
        claim_packages.append(claim_package.casefold())
    if len(claim_packages) != len(set(claim_packages)):
        raise Refusal("pending owner-reassignment live claims are duplicated")
    controls = [
        record
        for record in registry["worktrees"]
        if isinstance(record, dict) and record.get("kind") == "control_singleton"
    ]
    if len(controls) != 1:
        raise Refusal("pending owner reassignment lost its control singleton")
    control = controls[0]
    lease = control.get("lease")
    if (
        control.get("state") != "active"
        or control.get("package") != package
        or control.get("task_ref") != task_ref
        or control.get("branch") != control_branch
        or not isinstance(lease, dict)
        or (
            lease.get("task_ref"),
            lease.get("purpose"),
            lease.get("package"),
        )
        != (task_ref, "control", package)
    ):
        raise Refusal("pending owner reassignment lost exact control custody")
    if push_proven:
        response = pending.get("new_branch_response")
        if response != f"*\t{checkpoint}:refs/heads/{successor}\t[new branch]":
            raise Refusal("pending owner reassignment has an invalid new-branch proof")
        _validate_utc_timestamp(
            pending.get("push_proven_at"), field="pending push_proven_at"
        )


def _validate_pending_operation(registry: dict[str, Any]) -> None:
    pending = registry.get("pending")
    pending_records = [
        record
        for record in registry.get("worktrees", [])
        if isinstance(record, dict) and record.get("state") == "pending"
    ]
    if pending is None:
        if pending_records:
            raise Refusal("registry has a pending record without an operation journal")
        return
    if not isinstance(pending, dict):
        raise Refusal("registry pending operation must be an object or null")
    operation = pending.get("operation")
    validators = {
        "create": _validate_pending_create,
        "retire": _validate_pending_retire,
        "retire_closed_custody": _validate_pending_closed_custody,
        "control_repoint": _validate_pending_control_repoint,
        "owner_reassignment_branch_create": (
            _validate_pending_owner_reassignment_branch_create
        ),
    }
    validator = validators.get(operation)
    if validator is None:
        raise Refusal("registry contains an unknown pending operation")
    if operation != "create" and pending_records:
        raise Refusal("non-create journal has an orphan pending worktree record")
    if operation != "owner_reassignment_branch_create":
        _validate_utc_timestamp(pending.get("started_at"), field="pending started_at")
    validator(registry, pending)


def _validate_head_reconciliation_custody(registry: dict[str, Any]) -> None:
    """Require one immutable journal or preparation for every custody proof."""

    links: list[tuple[str, dict[str, Any]]] = []
    pending = registry.get("pending")
    if (
        isinstance(pending, dict)
        and pending.get("operation") == "owner_reassignment_branch_create"
        and "source_registry_reconciliation" in pending
    ):
        reconciliation = pending["source_registry_reconciliation"]
        links.append((reconciliation["after"]["path"], reconciliation["after"]))

    for preparation in registry.get("owner_reassignment_preparations", []):
        proof = preparation.get("source_head_reconciliation")
        if proof is None:
            continue
        durable = preparation["source_snapshot"]["durable_records"]
        source = durable[0]
        links.append(
            (
                source["path"],
                {
                    **source,
                    "owner_reassignment_head_reconciliation": proof,
                },
            )
        )

    records = [
        record
        for record in registry.get("worktrees", [])
        if isinstance(record, dict)
        and record.get("owner_reassignment_head_reconciliation") is not None
    ]
    for record in records:
        matches = [
            linked
            for path, linked in links
            if _path_key(path) == _path_key(str(record.get("path", "")))
            and linked.get("package") == record.get("package")
            and linked.get("task_ref") == record.get("task_ref")
            and linked.get("branch") == record.get("branch")
            and linked.get("head") == record.get("head")
            and linked.get("owner_reassignment_head_reconciliation")
            == record.get("owner_reassignment_head_reconciliation")
        ]
        if len(matches) != 1:
            raise Refusal(
                "source HEAD reconciliation lacks one exact journal or "
                "preparation custody link"
            )
    for path, linked in links:
        matches = [
            record
            for record in records
            if _path_key(str(record.get("path", ""))) == _path_key(path)
            and record.get("package") == linked.get("package")
            and record.get("task_ref") == linked.get("task_ref")
            and record.get("branch") == linked.get("branch")
            and record.get("head") == linked.get("head")
            and record.get("owner_reassignment_head_reconciliation")
            == linked.get("owner_reassignment_head_reconciliation")
        ]
        if len(matches) != 1:
            raise Refusal(
                "source HEAD reconciliation custody link has no exact record"
            )


def validate_owner_reassignment_registry(registry: dict[str, Any]) -> None:
    """Validate preparation history and every transient registry operation.

    Delivery admission imports this exact validator so the lifecycle writer and
    its read-only gate cannot drift on JSON types, history, replay, or custody.
    """

    worktrees = registry.get("worktrees", [])
    if not isinstance(worktrees, list):
        raise Refusal("registry worktrees must be a list")
    for record in worktrees:
        if isinstance(record, dict):
            _validate_owner_reassignment_head_reconciliation_record(record)
    _validate_owner_reassignment_preparations(registry)
    _validate_pending_operation(registry)
    _validate_head_reconciliation_custody(registry)
    _validate_closed_custody_registry(registry)
    validate_control_custody_registry(registry)


# Custody receipts are local operational attestations, not identity credentials.
CONTROL_CUSTODY_FIELDS = {
    "id", "state", "path", "package", "branch", "head", "from_ref", "to_ref",
    "old_lease", "old_token", "new_lease", "owner_ref", "review_ref", "quiescence_ref",
    "source_liveness", "owner_revocation", "acceptance_ref", "accepted_by", "supersedes",
}


def _custody_generation_time(registry: dict[str, Any]) -> str:
    # Whole-second schema retained; monotonic logical lease clock avoids replay.
    previous = [r.get("lease", {}).get("acquired_at") for r in registry.get("worktrees", []) if r.get("lease")]
    previous += [t["new_lease"]["acquired_at"] for t in registry.get("control_custody_transitions", [])]
    last_issued = registry.get("control_lease_clock")
    if last_issued is not None:
        _validate_utc_timestamp(last_issued, field="control lease clock")
        previous.append(last_issued)
    now = datetime.now(timezone.utc).replace(microsecond=0)
    for value in previous:
        if value:
            now = max(now, datetime.fromisoformat(value.replace("Z", "+00:00")) + timedelta(seconds=1))
    generation = now.isoformat().replace("+00:00", "Z")
    registry["control_lease_clock"] = generation
    return generation


def control_lease_token(record: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(
        {"path": record.get("path"), "lease": record.get("lease")},
        sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()


def control_custody_caller() -> str:
    # An orchestrator may inject a real task identity. Never relabel another task.
    actual = os.environ.get("PEERSLATE_CALLER_REF")
    if not actual:
        raise Refusal("caller identity unavailable; trusted launcher must supply PEERSLATE_CALLER_REF")
    return _validate_delivery_ref(actual)


def validate_control_custody_registry(registry: dict[str, Any]) -> None:
    if "control_lease_clock" in registry:
        _validate_utc_timestamp(registry["control_lease_clock"], field="control lease clock")
    failure = registry.get("control_guard_failure")
    if failure is not None:
        fields = {"path", "lease_token", "expected_branch", "expected_head", "observed_branch", "observed_head", "returncode"}
        if not isinstance(failure, dict) or set(failure) != fields:
            raise Refusal("control guard failure record is malformed")
        if not isinstance(failure["path"], str) or not Path(failure["path"]).is_absolute():
            raise Refusal("control guard failure path is invalid")
        if not isinstance(failure["lease_token"], str) or not re.fullmatch(r"[a-f0-9]{64}", failure["lease_token"]):
            raise Refusal("control guard failure token is invalid")
        for key in ("expected_branch", "observed_branch"):
            if failure[key] is not None and (not isinstance(failure[key], str) or not failure[key]):
                raise Refusal("control guard failure branch is invalid")
        for key in ("expected_head", "observed_head"):
            if failure[key] is not None and (not isinstance(failure[key], str) or not SHA_RE.fullmatch(failure[key])):
                raise Refusal("control guard failure HEAD is invalid")
        if type(failure["returncode"]) is not int:
            raise Refusal("control guard failure exit status is invalid")
    history = registry.get("control_custody_transitions", [])
    if not isinstance(history, list):
        raise Refusal("control custody history must be a list")
    ids: set[str] = set()
    active = 0
    generations: dict[str, dict[str, Any]] = {}
    spent: set[str] = set()
    issued: set[str] = set()
    revoked: set[str] = set()
    for item in history:
        if not isinstance(item, dict) or set(item) != CONTROL_CUSTODY_FIELDS:
            raise Refusal("control custody transition fields are malformed")
        if not isinstance(item["id"], str) or not re.fullmatch(r"[a-f0-9]{32}", item["id"]) or item["id"] in ids:
            raise Refusal("control custody transition id is invalid or duplicated")
        ids.add(item["id"])
        if not isinstance(item["state"], str) or item["state"] not in {"proposed", "accepted", "completed", "superseded"}:
            raise Refusal("control custody state is invalid")
        for key in ("from_ref", "to_ref", "owner_ref", "review_ref", "quiescence_ref"):
            if not isinstance(item[key], str):
                raise Refusal("control custody reference must be text")
            _validate_delivery_ref(item[key])
        if item["from_ref"] == item["to_ref"] or item["review_ref"] in {item["from_ref"], item["to_ref"]}:
            raise Refusal("control custody requires a distinct receiver and independent reviewer")
        proofs = [item[k] for k in ("owner_ref", "review_ref", "quiescence_ref")]
        if len(set(proofs)) != 3:
            raise Refusal("control custody proof references must be distinct")
        _validate_package(item["package"])
        if not isinstance(item["path"], str) or not Path(item["path"]).is_absolute():
            raise Refusal("control custody path must be absolute")
        if item["branch"] is not None and (not isinstance(item["branch"], str) or not WORK_BRANCH_RE.fullmatch(item["branch"])):
            raise Refusal("control custody branch is invalid")
        if not isinstance(item["head"], str) or not SHA_RE.fullmatch(item["head"]):
            raise Refusal("control custody HEAD is invalid")
        if not isinstance(item["source_liveness"], str) or item["source_liveness"] not in {"QUIESCENT", "UNKNOWN"} or type(item["owner_revocation"]) is not bool:
            raise Refusal("control custody source status is invalid")
        if item["source_liveness"] == "UNKNOWN" and not item["owner_revocation"]:
            raise Refusal("unknown source requires explicit owner revocation")
        for key, who in (("old_lease", "from_ref"), ("new_lease", "to_ref")):
            validate_owner_reassignment_control_lease(item[key], task_ref=item[who], package=item["package"])
        if item["old_token"] != control_lease_token({"path": item["path"], "lease": item["old_lease"]}):
            raise Refusal("control custody old lease token mismatch")
        if item["old_lease"]["acquired_at"] >= item["new_lease"]["acquired_at"]:
            raise Refusal("control custody generation did not advance")
        path_key = _path_key(item["path"])
        previous = generations.get(path_key)
        new_token = control_lease_token({"path": item["path"], "lease": item["new_lease"]})
        if item["old_token"] in spent or new_token in issued or new_token in spent:
            raise Refusal("control custody generation is duplicated or replayed")
        if item["from_ref"] in revoked:
            raise Refusal("control custody source identity remains revoked")
        if item["supersedes"] is not None:
            if not previous or previous["state"] != "superseded" or item["supersedes"] != previous["id"]:
                raise Refusal("custody supersession does not match prior pending target")
            if any(item[k] != previous[k] for k in ("path", "package", "branch", "head", "from_ref", "old_lease", "old_token")):
                raise Refusal("custody supersession changed the exact source tuple")
            if item["to_ref"] == previous["to_ref"] or not item["owner_revocation"]:
                raise Refusal("custody supersession requires a different receiver and owner revocation")
            old_refs = {previous[k] for k in ("owner_ref", "review_ref", "quiescence_ref")}
            if any(item[k] in old_refs for k in ("owner_ref", "review_ref", "quiescence_ref")):
                raise Refusal("custody supersession requires fresh evidence references")
            if item["new_lease"]["acquired_at"] <= previous["new_lease"]["acquired_at"]:
                raise Refusal("custody supersession generation did not advance")
        elif previous and previous["state"] == "superseded":
            raise Refusal("superseded custody requires its exact successor link")
        elif previous:
            prior_lease = previous["new_lease"]
            old_time = item["old_lease"]["acquired_at"]
            if previous["state"] != "completed" or old_time < prior_lease["acquired_at"] or (
                old_time == prior_lease["acquired_at"] and item["old_lease"] != prior_lease
            ):
                raise Refusal("control custody generation chain is inconsistent")
        generations[path_key] = item
        issued.add(new_token)
        if item["state"] == "completed":
            spent.add(item["old_token"])
            revoked.add(item["from_ref"])
            revoked.discard(item["to_ref"])
        if item["state"] == "proposed" or (item["state"] == "superseded" and item["accepted_by"] is None):
            if item["acceptance_ref"] is not None or item["accepted_by"] is not None:
                raise Refusal("unaccepted custody contains an acceptance")
        else:
            if not isinstance(item["acceptance_ref"], str):
                raise Refusal("control custody acceptance is missing")
            _validate_delivery_ref(item["acceptance_ref"])
            if item["accepted_by"] != item["to_ref"] or item["acceptance_ref"] in proofs:
                raise Refusal("control custody acceptance mismatch")
        if item["state"] in {"proposed", "accepted"}:
            active += 1
            record = _record_by_path(registry, item["path"])
            if not record or record.get("kind") != "control_singleton" or record.get("state") != "active" or any(
                record.get(k) != item[k] for k in ("package", "branch", "head")
            ) or record.get("task_ref") != item["from_ref"] or record.get("lease") != item["old_lease"]:
                raise Refusal("pending custody no longer matches exact source record")
    if any(t["state"] == "superseded" for t in generations.values()):
        raise Refusal("superseded custody has no replacement proposal")
    for record in registry.get("worktrees", []):
        if record.get("kind") != "control_singleton" or not record.get("lease"):
            continue
        lease = record["lease"]
        latest = generations.get(_path_key(record["path"]))
        if not latest or latest["state"] != "completed":
            continue
        if not isinstance(lease, dict):
            raise Refusal("current control lease is malformed")
        _validate_utc_timestamp(lease.get("acquired_at"), field="current control generation")
        if control_lease_token(record) in spent or lease.get("task_ref") in revoked:
            raise Refusal("current control lease replays a revoked generation or identity")
        if record.get("task_ref") != lease.get("task_ref") or record.get("package") != lease.get("package"):
            raise Refusal("current control record and lease identity differ")
        latest_lease = latest["new_lease"]
        if lease["acquired_at"] < latest_lease["acquired_at"] or (
            lease["acquired_at"] == latest_lease["acquired_at"] and lease != latest_lease
        ):
            raise Refusal("current control lease predates or conflicts with completed custody")
    if active > 1 or (active and registry.get("pending") is not None):
        raise Refusal("overlapping custody or lifecycle transition")


def _custody_pending(registry: dict[str, Any]) -> bool:
    return registry.get("control_guard_failure") is not None or any(t["state"] in {"proposed", "accepted"} for t in registry.get("control_custody_transitions", []))


def require_control_custody_fence(registry: dict[str, Any], record: dict[str, Any], *, task_ref: str, lease_token: str) -> None:
    validate_control_custody_registry(registry)
    if _custody_pending(registry):
        raise Refusal("control custody transition is pending; writers are fenced")
    if not record.get("lease") or record["lease"].get("task_ref") != task_ref or record.get("task_ref") != task_ref:
        raise Refusal("caller does not hold the current control lease")
    if not lease_token and not registry.get("control_custody_transitions"):
        return
    if not lease_token or lease_token != control_lease_token(record):
        raise Refusal("stale or missing control lease token")


def _custody_existing_guard(registry: dict[str, Any], task_ref: str) -> None:
    if _custody_pending(registry):
        raise Refusal("control custody transition is pending")
    history = registry.get("control_custody_transitions", [])
    if history:
        if task_ref != control_custody_caller():
            raise Refusal("claimed task differs from launcher caller")
        for r in registry["worktrees"]:
            if r.get("kind") == "control_singleton" and r.get("lease"):
                if task_ref != control_custody_caller():
                    raise Refusal("claimed task differs from launcher caller")
                require_control_custody_fence(registry, r, task_ref=task_ref,
                    lease_token=os.environ.get("PEERSLATE_CONTROL_LEASE_TOKEN", ""))
    revoked = set()
    for transition in history:
        if transition["state"] == "completed":
            revoked.add(transition["from_ref"])
            revoked.discard(transition["to_ref"])
    if task_ref in revoked:
        controls = [r for r in registry["worktrees"] if r.get("kind") == "control_singleton"]
        if not any(r.get("lease") and r["lease"].get("task_ref") == task_ref for r in controls):
            raise Refusal("revoked task cannot reacquire control; use explicit custody transfer")


def command_control_custody(context: RepoContext, args: argparse.Namespace) -> dict[str, Any]:
    _require_execute(args.execute)
    caller = control_custody_caller()
    if caller != args.task_ref:
        raise Refusal("claimed task differs from launcher caller")
    with _registry_lock(context.registry_path):
        registry = _load_registry(context.registry_path)
        assert registry is not None
        _assert_registry_identity(context, registry)
        if registry.get("pending") or registry.get("control_guard_failure"):
            raise Refusal("reconcile existing lifecycle operation or guarded branch failure before custody")
        record = _control_record(context, registry)
        if record is None:
            raise Refusal("active control record required")
        history = registry.setdefault("control_custody_transitions", [])
        if args.action == "propose":
            if not args.proof_file:
                raise Refusal("propose requires exact proof file")
            try:
                proof = json.loads(Path(args.proof_file).read_text(encoding="utf-8"))
            except (OSError, ValueError) as error:
                raise Refusal("unreadable custody proof") from error
            required = {"path", "package", "branch", "head", "from_ref", "to_ref", "old_lease", "old_token", "owner_ref", "review_ref", "quiescence_ref", "source_liveness", "owner_revocation"}
            if not isinstance(proof, dict) or set(proof) not in (required, required | {"supersedes"}):
                raise Refusal("custody proof requires exact fields")
            proof.setdefault("supersedes", None)
            for key in ("from_ref", "to_ref"):
                if not isinstance(proof[key], str):
                    raise Refusal("custody participant reference must be text")
                _validate_delivery_ref(proof[key])
            if caller not in {proof["from_ref"], proof["to_ref"]}:
                raise Refusal("proposal caller must be a named participant")
            existing = next((t for t in history if all(t[k] == v for k, v in proof.items())), None)
            if existing:
                return {"status": existing["state"], "transition": existing}
            pending_target = next((t for t in history if t["state"] in {"proposed", "accepted"}), None)
            if pending_target:
                if proof["supersedes"] != pending_target["id"]:
                    raise Refusal("another custody transition is pending; exact supersedes id required")
                pending_target["state"] = "superseded"
            elif proof["supersedes"] is not None:
                raise Refusal("no matching pending custody target to supersede")
            item = dict(proof, id=secrets.token_hex(16), state="proposed", acceptance_ref=None, accepted_by=None,
                new_lease={"task_ref": proof["to_ref"], "purpose": "control", "package": proof["package"],
                           "acquired_at": _custody_generation_time(registry)})
            history.append(item)
        else:
            item = next((t for t in history if t["id"] == args.transition), None)
            if item is None:
                raise Refusal("unknown custody transition")
            if caller != item["to_ref"]:
                raise Refusal("only actual receiving caller can accept or complete custody")
            if item["state"] == "superseded":
                raise Refusal("receiver custody proposal was superseded")
            if item["state"] == "completed":
                if args.action == "accept" and args.acceptance_ref != item["acceptance_ref"]:
                    raise Refusal("acceptance replay differs")
                return {"status": "completed", "transition": item, "lease_token": control_lease_token({"path": item["path"], "lease": item["new_lease"]})}
            if args.action == "accept":
                if item["state"] == "accepted" and args.acceptance_ref != item["acceptance_ref"]:
                    raise Refusal("acceptance replay differs")
                item.update(state="accepted", accepted_by=caller, acceptance_ref=args.acceptance_ref)
            elif item["state"] != "accepted":
                raise Refusal("receiver acceptance required before completion")
        validate_control_custody_registry(registry)
        if _path_key(record["path"]) != _path_key(item["path"]):
            raise Refusal("custody path differs from control singleton")
        live = _worktree_at(context.root, _canonical(record["path"]))
        if live is None or (live.get("branch"), live.get("head")) != (item["branch"], item["head"]):
            raise Refusal("custody live branch/HEAD compare-and-swap failed")
        pristine, residue = _is_pristine(_canonical(record["path"]))
        if not pristine:
            raise Refusal("custody requires quiescent pristine checkout", blockers=residue)
        if args.action == "complete":
            # One atomic replacement commits both ownership and completed journal.
            record.update(task_ref=item["to_ref"], lease=item["new_lease"], updated_at=_utc_now())
            item["state"] = "completed"
        _atomic_write(context.registry_path, registry)
        return {"status": item["state"], "transition": item, "lease_token": control_lease_token(record)}


def command_control_run(context: RepoContext, args: argparse.Namespace) -> dict[str, Any]:
    _require_execute(args.execute)
    caller = control_custody_caller()
    if caller != args.task_ref:
        raise Refusal("claimed task differs from launcher caller")
    command = list(args.command)
    if command and command[0] == "--":
        command.pop(0)
    if not command:
        raise Refusal("guarded subprocess command required")
    with _registry_lock(context.registry_path):
        registry = _load_registry(context.registry_path)
        assert registry is not None
        _assert_registry_identity(context, registry)
        if registry.get("pending"):
            raise Refusal("lifecycle operation pending")
        record = _control_record(context, registry)
        if record is None:
            raise Refusal("control singleton unavailable")
        require_control_custody_fence(registry, record, task_ref=caller, lease_token=args.lease_token)
        before = _worktree_at(context.root, _canonical(record["path"]))
        if before is None or (before.get("branch"), before.get("head")) != (record.get("branch"), record.get("head")):
            raise Refusal("guarded starting branch/HEAD differs from registry; owner-manifest reconciliation required")
        environment = dict(os.environ, PEERSLATE_CONTROL_LEASE_TOKEN=args.lease_token)
        result = subprocess.run(command, cwd=record["path"], env=environment, check=False)
        # A nonzero child can still commit. Observe under the same lock before
        # releasing custody, and never silently authorize a branch switch.
        live = _worktree_at(context.root, _canonical(record["path"]))
        if live is None or live.get("branch") != record.get("branch"):
            registry["control_guard_failure"] = {
                "path": record["path"], "lease_token": args.lease_token,
                "expected_branch": record.get("branch"), "expected_head": record.get("head"),
                "observed_branch": live.get("branch") if live else None,
                "observed_head": live.get("head") if live else None,
                "returncode": result.returncode,
            }
            _atomic_write(context.registry_path, registry)
            raise Refusal("guarded command changed branch or removed checkout; owner-manifest reconciliation required")
        record["head"] = live.get("head")
        record["updated_at"] = _utc_now()
        _atomic_write(context.registry_path, registry)
        return {"status": "command_completed", "returncode": result.returncode, "lease_token": args.lease_token,
                "head": record["head"], "branch": record["branch"]}


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
    if (
        not isinstance(data, dict)
        or type(data.get("schema_version")) is not int
        or data.get("schema_version") != SCHEMA_VERSION
    ):
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
    data.setdefault("owner_reassignment_preparations", [])
    validate_owner_reassignment_registry(data)
    return data


def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
    if payload.get("schema_version") == SCHEMA_VERSION and isinstance(
        payload.get("worktrees"), list
    ):
        payload.setdefault("owner_reassignment_preparations", [])
        validate_owner_reassignment_registry(payload)
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


def _owner_reassignment_handoff(
    claim: dict[str, Any], *, receiving_ref: str, receiving_branch: str
) -> dict[str, Any] | None:
    """Return an exact merged owner-reassignment record, if present."""

    handoff = claim.get("handoff")
    if not isinstance(handoff, dict) or handoff.get("type") != "owner_reassignment":
        return None
    if set(handoff) != OWNER_REASSIGNMENT_HANDOFF_FIELDS:
        raise Refusal("owner reassignment handoff has an inexact field set")
    if "relinquished" in handoff:
        raise Refusal("owner reassignment may not assert prior-writer relinquishment")
    from_ref = _validate_delivery_ref(str(handoff.get("from_ref", "")))
    to_ref = _validate_delivery_ref(str(handoff.get("to_ref", "")))
    from_branch = _validate_work_branch(str(handoff.get("from_branch", "")))
    to_branch = _validate_work_branch(str(handoff.get("to_branch", "")))
    checkpoint = _validate_sha(str(handoff.get("checkpoint_sha", "")))
    _validate_delivery_ref(str(handoff.get("owner_authorization_ref", "")))
    if from_ref == to_ref or from_branch == to_branch:
        raise Refusal("owner reassignment must change both writer and branch")
    if to_ref != receiving_ref or to_branch != receiving_branch:
        raise Refusal("owner reassignment does not match the receiving claim identity")
    if claim.get("writer_ref") != to_ref or claim.get("branch") != to_branch:
        raise Refusal("merged claim identity differs from its owner reassignment record")
    if not checkpoint:
        raise Refusal("owner reassignment is missing its exact checkpoint")
    return handoff


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
    metadata: dict[str, Any] | None = None,
) -> None:
    pending = {
        "operation": operation,
        "path": str(_canonical(path)),
        "record": record,
        "started_at": _utc_now(),
    }
    if metadata:
        overlap = set(pending) & set(metadata)
        if overlap:
            raise Refusal(
                "pending operation metadata overlaps reserved fields: "
                + ", ".join(sorted(overlap))
            )
        pending.update(metadata)
    registry["pending"] = pending
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


def _reprove_owner_reassignment_branch_completion(
    context: RepoContext,
    registry: dict[str, Any],
    pending: dict[str, Any],
) -> None:
    """Reprove the complete remote/local tuple at the commit boundary."""

    _validate_pending_owner_reassignment_branch_create(registry, pending)
    if pending.get("push_proven_new") is not True:
        raise Refusal("owner-reassignment successor creation is not push-proven")
    package = pending["package"]
    from_branch = pending["from_branch"]
    successor_branch = pending["successor_branch"]
    checkpoint = pending["checkpoint_sha"]
    prepared_from_main = pending["prepared_from_main"]
    live_claims_snapshot = pending["live_claims_snapshot"]

    if _remote_branch_tip(context, "main") != prepared_from_main:
        raise Refusal("origin/main moved during successor final proof")
    if _strict_live_claims(context) != live_claims_snapshot:
        raise Refusal("live claims changed during successor final proof")
    if _fetch_origin_branch(context, from_branch) != checkpoint:
        raise Refusal("source branch moved during owner-reassignment final proof")
    if _fetch_origin_branch(context, successor_branch) != checkpoint:
        raise Refusal("successor branch moved during owner-reassignment final proof")
    if _ref_sha(context, f"refs/heads/{from_branch}") != pending.get(
        "old_local_ref"
    ):
        raise Refusal("local source branch changed during owner-reassignment final proof")
    if _snapshot_branch_worktrees(context, from_branch, checkpoint) != pending.get(
        "source_worktrees"
    ):
        raise Refusal("source worktree identity changed during final proof")
    if _source_durable_registry_snapshot(
        context,
        registry,
        package=package,
        from_ref=pending["from_ref"],
        from_branch=from_branch,
        checkpoint=checkpoint,
    ) != pending.get("source_durable_records"):
        raise Refusal("durable source identity changed during final proof")
    reconciliation = _pending_source_registry_reconciliation(registry, pending)
    if reconciliation is not None:
        previous_head = reconciliation["before"]["head"]
        if not _is_ancestor(context, previous_head, checkpoint):
            raise Refusal(
                "reconciled source registry HEAD is no longer an ancestor of "
                "the checkpoint"
            )
    if _ref_sha(context, f"refs/heads/{successor_branch}") is not None:
        raise Refusal("successor creation unexpectedly created a local branch")
    _assert_successor_namespace_available(
        context,
        registry,
        successor_branch,
        live_claims_snapshot,
        allow_exact_successor_remote=True,
    )

    # Reconfirm the server tuple after every other slow proof.  Only local
    # preparation persistence follows these reads.
    if _strict_live_claims(context) != live_claims_snapshot:
        raise Refusal("live claims changed at owner-reassignment commit boundary")
    # One server advertisement avoids a symmetric race between sequential
    # main/source/successor reads.  No further remote or claim operation may
    # occur before the preparation is persisted.
    remote_tuple = _remote_branch_tuple(
        context, ("main", from_branch, successor_branch)
    )
    if remote_tuple != {
        "main": prepared_from_main,
        from_branch: checkpoint,
        successor_branch: checkpoint,
    }:
        raise Refusal("remote branch tuple moved at owner-reassignment commit boundary")


def _rollback_source_registry_reconciliation(
    registry: dict[str, Any], pending: dict[str, Any]
) -> None:
    reconciliation = _pending_source_registry_reconciliation(registry, pending)
    if reconciliation is None:
        return
    before = reconciliation["before"]
    after = reconciliation["after"]
    matches = [
        (index, record)
        for index, record in enumerate(registry["worktrees"])
        if _path_key(str(record.get("path", "")))
        == _path_key(str(after.get("path", "")))
    ]
    if len(matches) != 1 or matches[0][1] != after:
        raise Refusal("source registry reconciliation cannot be rolled back exactly")
    registry["worktrees"][matches[0][0]] = json.loads(
        json.dumps(before, sort_keys=True)
    )


def _reconcile_owner_reassignment_branch_create(
    context: RepoContext,
    registry: dict[str, Any],
    pending: dict[str, Any],
) -> dict[str, Any]:
    """Reconcile only a provably new successor-branch creation.

    If a process died before it recorded Git's ``[new branch]`` response, an
    exact remote ref is still ambiguous: another actor could have won the
    race.  The pending record is preserved for explicit investigation rather
    than converting ambiguity into authority.
    """

    validate_owner_reassignment_registry(registry)
    package = _validate_package(str(pending.get("package", "")))
    task_ref = _validate_task_ref(str(pending.get("task_ref", "")))
    from_branch = _validate_work_branch(str(pending.get("from_branch", "")))
    successor_branch = _validate_work_branch(
        str(pending.get("successor_branch", ""))
    )
    checkpoint = _validate_sha(str(pending.get("checkpoint_sha", "")))
    _validate_delivery_ref(str(pending.get("from_ref", "")))
    _validate_delivery_ref(task_ref)
    _validate_delivery_ref(str(pending.get("owner_authorization_ref", "")))
    if pending.get("push_proven_new") not in {True, False}:
        raise Refusal("pending owner reassignment has an invalid push-proof state")
    if from_branch == successor_branch:
        raise Refusal("pending owner reassignment reuses the old branch")

    successor_tip = _fetch_origin_branch(context, successor_branch)
    if successor_tip is None:
        if pending.get("push_proven_new"):
            raise Refusal(
                "proven successor branch disappeared; pending recovery is preserved"
            )
        _rollback_source_registry_reconciliation(registry, pending)
        registry["pending"] = None
        _atomic_write(context.registry_path, registry)
        return {
            "operation": "owner_reassignment_branch_create",
            "outcome": "rolled_back",
            "package": package,
            "task_ref": task_ref,
            "successor_branch": successor_branch,
        }
    old_tip = _fetch_origin_branch(context, from_branch)
    if old_tip != checkpoint:
        raise Refusal(
            "pending owner reassignment old branch no longer equals its checkpoint"
        )
    if successor_tip != checkpoint:
        raise Refusal(
            "pending owner reassignment successor branch has an unexpected tip"
        )
    if pending.get("push_proven_new") is not True:
        raise Refusal(
            "successor branch exists without a recorded new-branch response; "
            "creation provenance is ambiguous and pending recovery is preserved"
        )
    _reprove_owner_reassignment_branch_completion(context, registry, pending)
    _append_completed_preparation(registry, pending)
    registry["pending"] = None
    _atomic_write(context.registry_path, registry)
    return {
        "operation": "owner_reassignment_branch_create",
        "outcome": "completed",
        "package": package,
        "task_ref": task_ref,
        "from_branch": from_branch,
        "successor_branch": successor_branch,
        "checkpoint_sha": checkpoint,
    }


def _reconcile_closed_custody_retirement(
    context: RepoContext,
    registry: dict[str, Any],
    pending: dict[str, Any],
    *,
    on_disk: bool,
) -> dict[str, Any]:
    """Reconcile an exact closed-custody journal without retrying removal."""

    _validate_pending_closed_custody(registry, pending)
    path = _canonical(pending["path"])
    before = pending["before_record"]
    after = pending["after_record"]
    if on_disk:
        proof = after["closed_custody_retirement"]
        all_worktrees = _closed_custody_worktree_proof(
            context,
            registry,
            before,
            path=path,
            branch=proof["target_branch"],
            expected_head=proof["expected_head"],
            label="pending closed-custody target",
        )
        nested = [
            str(entry.get("worktree"))
            for entry in all_worktrees
            if _path_key(str(entry.get("worktree", ""))) != _path_key(path)
            and _is_strictly_within(str(entry.get("worktree", "")), path)
        ]
        if nested:
            raise Refusal(
                "pending closed-custody target contains a nested Git worktree",
                blockers=nested,
            )
        registry["pending"] = None
        _atomic_write(context.registry_path, registry)
        return {
            "operation": "retire_closed_custody",
            "outcome": "preserved",
            "path": str(path),
            "proof": after["closed_custody_retirement"],
        }
    matches = [
        (index, record)
        for index, record in enumerate(registry["worktrees"])
        if _path_key(str(record.get("path", ""))) == _path_key(path)
    ]
    if len(matches) != 1 or matches[0][1] != before:
        raise Refusal("pending closed-custody retirement cannot publish exact custody")
    registry["worktrees"][matches[0][0]] = after
    registry["pending"] = None
    _atomic_write(context.registry_path, registry)
    return {
        "operation": "retire_closed_custody",
        "outcome": "completed",
        "path": str(path),
        "proof": after["closed_custody_retirement"],
    }


def _reconcile_pending(
    context: RepoContext, registry: dict[str, Any]
) -> dict[str, Any] | None:
    # Reconciliation is itself a mutation boundary.  Validate the complete
    # journal/record/preparation graph even when an internal caller supplied a
    # dictionary without going through ``_load_registry``.
    validate_owner_reassignment_registry(registry)
    if _custody_pending(registry):
        raise Refusal("control custody transition pending; use receiver completion")
    pending = registry.get("pending")
    if not pending:
        return None
    if not isinstance(pending, dict) or pending.get("operation") not in {
        "create",
        "retire",
        "retire_closed_custody",
        "control_repoint",
        "owner_reassignment_branch_create",
    }:
        raise Refusal("registry contains an unknown pending operation")
    if pending.get("operation") == "owner_reassignment_branch_create":
        return _reconcile_owner_reassignment_branch_create(
            context, registry, pending
        )
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
    if operation == "retire_closed_custody":
        return _reconcile_closed_custody_retirement(
            context, registry, pending, on_disk=on_disk
        )
    record = _record_by_path(registry, path)
    if operation == "create":
        if not on_disk:
            if record and record.get("state") == "pending":
                registry["worktrees"].remove(record)
            _finalize_owner_reassignment_worktree_create(
                context, registry, pending, completed=False
            )
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
        _finalize_owner_reassignment_worktree_create(
            context, registry, pending, completed=True
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
    owner_reassignment: dict[str, Any] | None = None,
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
    pending_metadata: dict[str, Any] | None = None
    if owner_reassignment is not None:
        preparation = owner_reassignment.get("preparation")
        source_record = owner_reassignment.get("source_record")
        handoff = owner_reassignment.get("handoff")
        origin_main = owner_reassignment.get("origin_main")
        if (
            not isinstance(preparation, dict)
            or source_record is not None and not isinstance(source_record, dict)
            or not isinstance(handoff, dict)
            or not isinstance(origin_main, str)
        ):
            raise Refusal("owner-reassignment worktree transition is invalid")
        transition = _begin_owner_reassignment_worktree_create(
            preparation=preparation,
            source_record=source_record,
            handoff=handoff,
            receiver_path=path,
            origin_main=origin_main,
        )
        record["owner_reassignment_preparation_id"] = transition["preparation_id"]
        pending_metadata = {"owner_reassignment": transition}
    _write_pending(
        context,
        registry,
        operation="create",
        path=path,
        record=record.copy(),
        metadata=pending_metadata,
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
    pending = registry.get("pending")
    if not isinstance(pending, dict):
        raise Refusal("registered worktree creation lost its pending journal")
    _finalize_owner_reassignment_worktree_create(
        context, registry, pending, completed=True
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
            "owner_reassignment_preparations": [],
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
    reassignment = _owner_reassignment_handoff(
        claim, receiving_ref=task_ref, receiving_branch=branch
    )
    fetched_branch_tip = _fetch_origin_branch(context, branch)
    reassignment_checkpoint: str | None = None
    if reassignment is not None:
        reassignment_checkpoint = _validate_sha(reassignment["checkpoint_sha"])
        if fetched_branch_tip is None:
            raise Refusal(
                "owner-reassignment successor branch is absent from origin"
            )
        old_tip = _fetch_origin_branch(context, reassignment["from_branch"])
        if old_tip != reassignment_checkpoint:
            raise Refusal(
                "owner-reassignment source branch is absent or moved from its "
                "authorized checkpoint"
            )
    with _registry_lock(context.registry_path):
        registry = _load_registry(context.registry_path)
        assert registry is not None
        _assert_registry_identity(context, registry)
        recovered = _reconcile_pending(context, registry)
        durable = _existing_durable(registry, package)
        if len(durable) > 1:
            raise Refusal("registry has duplicate durable worktrees for the package")
        receiver_durable_exists = bool(
            durable
            and durable[0].get("task_ref") == task_ref
            and durable[0].get("branch") == claim["branch"]
        )
        preparation: dict[str, Any] | None = None
        source_record_to_preserve: dict[str, Any] | None = None
        if reassignment is not None:
            preparation = _matching_owner_reassignment_preparation(
                registry, claim, reassignment
            )
            expected_preparation_status = (
                "consumed" if receiver_durable_exists else "completed"
            )
            if preparation.get("status") != expected_preparation_status:
                raise Refusal(
                    "owner-reassignment preparation is not in the exact expected state"
                )
            if _fetch_origin_branch(
                context, reassignment["from_branch"]
            ) != reassignment_checkpoint:
                raise Refusal(
                    "owner-reassignment source branch moved during durable-worktree proof"
                )
            if not receiver_durable_exists and (
                fetched_branch_tip != reassignment_checkpoint
                or _fetch_origin_branch(context, branch) != reassignment_checkpoint
            ):
                raise Refusal(
                    "owner-reassignment successor branch moved before its first "
                    "durable worktree was created"
                )
            old_local_ref = _ref_sha(
                context, f"refs/heads/{reassignment['from_branch']}"
            )
            if old_local_ref not in {None, reassignment_checkpoint}:
                raise Refusal(
                    "owner-reassignment source local branch differs from its checkpoint"
                )
            current_source_worktrees = _snapshot_branch_worktrees(
                context, reassignment["from_branch"], reassignment_checkpoint
            )
            source_snapshot = preparation.get("source_snapshot")
            if not isinstance(source_snapshot, dict):
                raise Refusal("owner-reassignment preparation source snapshot is invalid")
            if not receiver_durable_exists:
                current_source_durable = _source_durable_registry_snapshot(
                    context,
                    registry,
                    package=package,
                    from_ref=reassignment["from_ref"],
                    from_branch=reassignment["from_branch"],
                    checkpoint=reassignment_checkpoint,
                )
                if source_snapshot != {
                    "local_branch_sha": old_local_ref,
                    "worktrees": current_source_worktrees,
                    "durable_records": current_source_durable,
                }:
                    raise Refusal(
                        "owner-reassignment preparation source snapshot changed before use"
                    )
            else:
                if (
                    source_snapshot.get("local_branch_sha") != old_local_ref
                    or source_snapshot.get("worktrees") != current_source_worktrees
                ):
                    raise Refusal(
                        "consumed owner-reassignment source Git identity changed"
                    )
                prepared_durable = source_snapshot.get("durable_records")
                if not isinstance(prepared_durable, list) or len(prepared_durable) > 1:
                    raise Refusal(
                        "consumed owner-reassignment durable source proof is invalid"
                    )
                preserved_sources = [
                    source
                    for source in registry["worktrees"]
                    if source.get("state") == "active"
                    and source.get("kind") == "reassignment_source"
                    and source.get("package") == package
                    and source.get("preserved_by_owner_reassignment") == reassignment
                ]
                if len(preserved_sources) != len(prepared_durable):
                    raise Refusal(
                        "consumed owner-reassignment source registry custody changed"
                    )
                for expected_source, preserved_source in zip(
                    prepared_durable, preserved_sources, strict=True
                ):
                    if not isinstance(expected_source, dict) or (
                        _path_key(str(preserved_source.get("path", "")))
                        != _path_key(str(expected_source.get("path", "")))
                        or preserved_source.get("task_ref")
                        != expected_source.get("task_ref")
                        or preserved_source.get("branch")
                        != expected_source.get("branch")
                        or preserved_source.get("head")
                        != expected_source.get("head")
                    ):
                        raise Refusal(
                            "consumed owner-reassignment preserved source changed"
                        )
        if durable:
            record = durable[0]
            if record.get("task_ref") != task_ref or record.get("branch") != claim["branch"]:
                if reassignment is None:
                    raise Refusal("registered durable worktree identity does not match claim")
                if (
                    record.get("task_ref") != reassignment["from_ref"]
                    or record.get("branch") != reassignment["from_branch"]
                ):
                    raise Refusal(
                        "registered durable worktree does not match the preserved "
                        "owner-reassignment source"
                    )
                source_path = _canonical(record["path"])
                source_entry = _worktree_at(context.root, source_path)
                if source_entry is None:
                    raise Refusal(
                        "owner-reassignment source worktree is no longer registered in Git"
                    )
                if record.get("outside_managed_root"):
                    if _is_strictly_within(source_path, registry["managed_root"]):
                        raise Refusal(
                            "legacy containment marker no longer matches its path"
                        )
                    if _has_reparse_component(source_path):
                        raise Refusal("reassignment source path crosses a reparse point")
                else:
                    _assert_managed_target(registry, source_path)
                source_pristine, source_residue = _is_pristine(source_path)
                if (
                    source_entry.get("branch") != reassignment["from_branch"]
                    or source_entry.get("head") != reassignment_checkpoint
                    or not source_pristine
                ):
                    raise Refusal(
                        "owner-reassignment source worktree is not pristine at the "
                        "authorized checkpoint",
                        blockers=source_residue,
                    )
                source_record_to_preserve = record
                durable = []
            else:
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
                if record.get("owner_reassignment_head_reconciliation") is not None and (
                    live_head != record.get("head")
                    or fetched_branch_tip != record.get("head")
                ):
                    raise Refusal(
                        "owner-reassignment reconciled source moved after preparation; "
                        "preserve its recorded custody for investigation"
                    )
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

        sources = [
            record
            for record in registry["worktrees"]
            if record.get("state") == "active"
            and record.get("kind") == "reassignment_source"
            and record.get("package") == package
        ]
        if sources:
            if reassignment is None:
                raise Refusal("preserved reassignment source has no merged claim provenance")
            # During a successive reassignment the current source is still the
            # active durable record until receiver creation commits.  Older
            # reassignment_source records belong to earlier consumed
            # preparations and must remain intact, not masquerade as the
            # current source.  Once the current preparation is consumed, bind
            # only its own durable snapshot path and handoff.
            prepared_sources = (
                preparation.get("source_snapshot", {}).get("durable_records", [])
                if isinstance(preparation, dict)
                else []
            )
            if receiver_durable_exists and prepared_sources:
                current_source_path = _path_key(prepared_sources[0]["path"])
                matching_sources = [
                    source
                    for source in sources
                    if _path_key(str(source.get("path", ""))) == current_source_path
                    and source.get("task_ref") == reassignment["from_ref"]
                    and source.get("branch") == reassignment["from_branch"]
                    and source.get("head") == reassignment_checkpoint
                    and source.get("preserved_by_owner_reassignment") == reassignment
                ]
                if len(matching_sources) != 1:
                    raise Refusal(
                        "registry does not have the current preparation's exact "
                        "preserved reassignment source"
                    )
                source = matching_sources[0]
                source_path = _canonical(source["path"])
                source_entry = _worktree_at(context.root, source_path)
                if source_entry is None:
                    raise Refusal(
                        "preserved owner-reassignment source is no longer registered in Git"
                    )
                source_pristine, source_residue = _is_pristine(source_path)
                if (
                    source_entry.get("branch") != reassignment["from_branch"]
                    or source_entry.get("head") != reassignment_checkpoint
                    or not source_pristine
                ):
                    raise Refusal(
                        "preserved owner-reassignment source no longer has its exact identity",
                        blockers=source_residue,
                    )

        branch_users = [
            entry for entry in _worktrees(context.root) if entry.get("branch") == branch
        ]
        if branch_users:
            raise Refusal(
                "claim branch already exists in another worktree; use exact adopt: "
                + branch_users[0]["worktree"]
            )
        managed_root = _canonical(registry["managed_root"])
        path = (
            managed_root
            / f"{package}--recovery-{hashlib.sha256(branch.encode('utf-8')).hexdigest()[:12]}"
            if reassignment is not None
            else managed_root / package
        )
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
            owner_reassignment=(
                {
                    "preparation": preparation,
                    "source_record": source_record_to_preserve,
                    "handoff": reassignment,
                    "origin_main": origin_main,
                }
                if preparation is not None and reassignment is not None
                else None
            ),
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


def _owner_reassignment_control_admission(
    context: RepoContext,
    registry: dict[str, Any],
    *,
    task_ref: str,
    package: str,
    require_no_pending: bool,
) -> dict[str, Any]:
    """Validate the complete initialized registry before branch preparation."""

    required_registry_fields = {
        "schema_version",
        "repository_common_dir",
        "repository_primary_root",
        "initialized_at",
        "initialized_by",
        "managed_root",
        "evidence_root",
        "policy_activation_worktree_count",
        "worktrees",
        "pending",
        "evidence_allocations",
        "owner_reassignment_preparations",
    }
    if not required_registry_fields.issubset(registry):
        raise Refusal(
            "owner reassignment requires a complete initialized lifecycle registry"
        )
    if type(registry.get("schema_version")) is not int or registry.get(
        "schema_version"
    ) != SCHEMA_VERSION:
        raise Refusal("owner reassignment requires exact registry schema 1")
    _validate_utc_timestamp(registry.get("initialized_at"), field="initialized_at")
    initialized_by = registry.get("initialized_by")
    if not isinstance(initialized_by, str):
        raise Refusal("owner-reassignment registry initializer reference is invalid")
    _validate_task_ref(initialized_by)
    if (
        type(registry.get("policy_activation_worktree_count")) is not int
        or registry["policy_activation_worktree_count"] < 0
        or not isinstance(registry.get("evidence_allocations"), list)
        or (
            registry.get("pending") is not None
            and not isinstance(registry.get("pending"), dict)
        )
    ):
        raise Refusal(
            "owner reassignment requires a structurally complete lifecycle registry"
        )
    if require_no_pending and registry.get("pending") is not None:
        raise Refusal("owner reassignment requires no pending lifecycle operation")

    identity_fields = {
        "repository_common_dir": context.common_dir,
        "repository_primary_root": context.primary_root,
    }
    for field, expected_path in identity_fields.items():
        raw_path = registry.get(field)
        if (
            not isinstance(raw_path, str)
            or not Path(raw_path).is_absolute()
            or raw_path != str(_canonical(raw_path))
            or _path_key(raw_path) != _path_key(expected_path)
        ):
            raise Refusal(
                "owner-reassignment registry repository identity is incomplete or changed"
            )
    roots: dict[str, Path] = {}
    for field in ("managed_root", "evidence_root"):
        raw_path = registry.get(field)
        if not isinstance(raw_path, str) or not Path(raw_path).is_absolute():
            raise Refusal(f"owner-reassignment registry {field} is not absolute")
        canonical = _canonical(raw_path)
        if raw_path != str(canonical) or not canonical.is_dir():
            raise Refusal(
                f"owner-reassignment registry {field} is missing or noncanonical"
            )
        roots[field] = canonical
    if _is_within(roots["managed_root"], roots["evidence_root"]) or _is_within(
        roots["evidence_root"], roots["managed_root"]
    ):
        raise Refusal("owner-reassignment registry roots overlap")

    records = registry.get("worktrees")
    if not isinstance(records, list):
        raise Refusal("owner-reassignment registry worktrees must be a list")
    known_kinds = {
        "control_singleton",
        "durable",
        "ephemeral",
        "grandfathered_observation",
        "reassignment_source",
    }
    known_states = {"active", "pending", "retired"}
    path_keys: set[str] = set()
    controls: list[dict[str, Any]] = []
    pending_records: list[dict[str, Any]] = []
    for record in records:
        required_record_fields = {
            "path",
            "kind",
            "state",
            "package",
            "branch",
            "head",
            "task_ref",
            "lease",
        }
        if not isinstance(record, dict) or not required_record_fields.issubset(record):
            raise Refusal("owner-reassignment registry worktree record is incomplete")
        path = _validate_preparation_path(
            record.get("path"), field="registry worktree path"
        )
        key = _path_key(path)
        if key in path_keys:
            raise Refusal("owner-reassignment registry has duplicate worktree paths")
        path_keys.add(key)
        kind = record.get("kind")
        state = record.get("state")
        if (
            not isinstance(kind, str)
            or kind not in known_kinds
            or not isinstance(state, str)
            or state not in known_states
        ):
            raise Refusal("owner-reassignment registry worktree role is invalid")
        record_package = record.get("package")
        if record_package is not None:
            if not isinstance(record_package, str):
                raise Refusal(
                    "owner-reassignment registry worktree package is invalid"
                )
            _validate_package(record_package)
        record_task = record.get("task_ref")
        if record_task is not None:
            if not isinstance(record_task, str):
                raise Refusal(
                    "owner-reassignment registry worktree task reference is invalid"
                )
            _validate_task_ref(record_task)
        branch = record.get("branch")
        if branch is not None and (
            not isinstance(branch, str)
            or branch != branch.strip()
            or not branch
            or branch.startswith("refs/")
            or any(ord(character) < 32 for character in branch)
        ):
            raise Refusal("owner-reassignment registry worktree branch is invalid")
        head = record.get("head")
        if head is not None and (
            not isinstance(head, str) or not SHA_RE.fullmatch(head)
        ):
            raise Refusal("owner-reassignment registry worktree HEAD is invalid")
        if record.get("lease") is not None and not isinstance(record.get("lease"), dict):
            raise Refusal("owner-reassignment registry worktree lease is invalid")
        _validate_owner_reassignment_head_reconciliation_record(record)
        if kind == "control_singleton":
            controls.append(record)
        if state == "pending":
            pending_records.append(record)

    pending = registry.get("pending")
    if pending_records:
        if (
            not isinstance(pending, dict)
            or pending.get("operation") != "create"
            or len(pending_records) != 1
            or pending.get("record") != pending_records[0]
            or _path_key(str(pending.get("path", "")))
            != _path_key(pending_records[0]["path"])
        ):
            raise Refusal(
                "owner-reassignment registry has orphan or ambiguous pending worktree records"
            )
    elif isinstance(pending, dict) and pending.get("operation") == "create":
        raise Refusal(
            "owner-reassignment registry pending create has no pending worktree record"
        )

    if len(controls) != 1:
        raise Refusal(
            "owner reassignment requires exactly one initialized control_singleton record"
        )
    control = controls[0]
    expected_control_path = roots["managed_root"] / "_control"
    if (
        control.get("state") != "active"
        or _path_key(control["path"]) != _path_key(expected_control_path)
        or control["path"] != str(expected_control_path)
        or control.get("package") != package
        or control.get("task_ref") != task_ref
    ):
        raise Refusal(
            "owner reassignment requires the exact active leased control singleton"
        )
    validate_owner_reassignment_control_lease(
        control.get("lease"), task_ref=task_ref, package=package
    )
    return control


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
    _custody_existing_guard(registry, task_ref)
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
            "acquired_at": _custody_generation_time(registry),
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
            lease.get("acquired_at") if same_lease and lease else _custody_generation_time(registry)
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
            "updated_at": _custody_generation_time(registry),
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
            _custody_existing_guard(registry, task_ref)
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
        "lease_token": control_lease_token(record),
        "recovered_pending": recovered,
    }


def _snapshot_branch_worktrees(
    context: RepoContext, branch: str, checkpoint: str
) -> list[dict[str, Any]]:
    """Prove and snapshot every checkout of the preserved source branch."""

    snapshots: list[dict[str, Any]] = []
    for entry in _worktrees(context.root):
        if entry.get("branch") != branch:
            continue
        path = _canonical(entry["worktree"])
        pristine, residue = _is_pristine(path)
        if entry.get("head") != checkpoint or not pristine:
            raise Refusal(
                "source-branch worktree is not pristine at the authorized checkpoint",
                blockers=[str(path), *residue],
            )
        snapshots.append(
            {
                "path": str(path),
                "branch": branch,
                "head": checkpoint,
            }
        )
    return sorted(snapshots, key=lambda item: _path_key(item["path"]))


def _branches_namespace_collide(left: str, right: str) -> bool:
    return left == right or left.startswith(right + "/") or right.startswith(left + "/")


def _ref_branch_names(context: RepoContext, prefix: str) -> list[str]:
    names = _git(
        context.root,
        "for-each-ref",
        "--format=%(refname)",
        prefix,
    )
    normalized: list[str] = []
    for refname in names.splitlines():
        if not refname:
            continue
        if not refname.startswith(prefix + "/"):
            raise Refusal(f"Git returned an ambiguous ref namespace entry: {refname}")
        normalized.append(refname[len(prefix) + 1 :])
    return normalized


def _assert_successor_namespace_available(
    context: RepoContext,
    registry: dict[str, Any],
    successor_branch: str,
    live_claims: Sequence[dict[str, Any]],
    *,
    allow_exact_successor_remote: bool = False,
) -> None:
    collisions: list[str] = []
    for branch in _ref_branch_names(context, "refs/heads"):
        if _branches_namespace_collide(successor_branch, branch):
            collisions.append(f"local head:{branch}")
    for branch in _ref_branch_names(context, "refs/remotes/origin"):
        if branch == "HEAD":
            continue
        if allow_exact_successor_remote and branch == successor_branch:
            continue
        if _branches_namespace_collide(successor_branch, branch):
            collisions.append(f"origin tracking ref:{branch}")
    for claim in live_claims:
        branch = str(claim.get("branch", ""))
        if _branches_namespace_collide(successor_branch, branch):
            collisions.append(f"live claim:{claim.get('package')}:{branch}")
    for entry in _worktrees(context.root):
        branch = entry.get("branch")
        if isinstance(branch, str) and _branches_namespace_collide(
            successor_branch, branch
        ):
            collisions.append(f"worktree:{entry.get('worktree')}:{branch}")
    for record in registry["worktrees"]:
        if record.get("state") != "active":
            continue
        for field in ("branch", "source_branch"):
            branch = record.get(field)
            if isinstance(branch, str) and _branches_namespace_collide(
                successor_branch, branch
            ):
                collisions.append(
                    f"registry:{record.get('path')}:{field}:{branch}"
                )
    if collisions:
        raise Refusal(
            "successor branch has an exact or namespace ancestor/descendant collision",
            blockers=sorted(set(collisions)),
        )


def _prepare_source_registry_head_reconciliation(
    context: RepoContext,
    registry: dict[str, Any],
    *,
    package: str,
    from_ref: str,
    from_branch: str,
    checkpoint: str,
    owner_authorization_ref: str,
    source_unavailable_ref: str | None,
) -> dict[str, Any] | None:
    """Journal an exact stale active-durable HEAD correction in memory.

    The caller persists this only together with the owner-reassignment branch
    creation journal.  Recovery either restores ``before`` when the successor
    is still absent or commits ``after`` with the completed preparation.
    """

    candidates = [
        record
        for record in registry["worktrees"]
        if record.get("state") == "active"
        and record.get("kind") == "durable"
        and (
            str(record.get("package", "")).casefold() == package.casefold()
            or record.get("branch") == from_branch
        )
    ]
    if len(candidates) > 1:
        raise Refusal(
            "owner reassignment has duplicate or ambiguous target/source durable records"
        )
    if not candidates:
        return None
    record = candidates[0]
    if (
        record.get("package") != package
        or record.get("task_ref") != from_ref
        or record.get("branch") != from_branch
    ):
        raise Refusal(
            "target/source durable registry record does not match the exact "
            "source package, task, and branch"
        )
    recorded_head = _validate_sha(str(record.get("head", "")))
    if recorded_head == checkpoint:
        return None
    if source_unavailable_ref is None:
        raise Refusal(
            "stale active durable custody requires a bounded source-unavailability "
            "evidence reference"
        )
    source_unavailable_ref = _validate_delivery_ref(source_unavailable_ref)
    if source_unavailable_ref in {from_ref, owner_authorization_ref}:
        raise Refusal(
            "source-unavailability evidence must be separate from source and "
            "owner-authorization references"
        )
    if record.get("lease") is not None:
        raise Refusal("stale active durable custody cannot have an active task lease")
    forbidden_existing = {
        "previous_head",
        "head_reconciled_at",
        "owner_reassignment_head_reconciliation",
    }
    if forbidden_existing & set(record):
        raise Refusal("active durable custody already carries HEAD reconciliation state")
    raw_path = record.get("path")
    if not isinstance(raw_path, str) or not Path(raw_path).is_absolute():
        raise Refusal("target/source durable registry path is not exact and absolute")
    path = _canonical(raw_path)
    if raw_path != str(path):
        raise Refusal("target/source durable registry path is not canonical")
    live = _worktree_at(context.root, path)
    pristine, residue = _is_pristine(path) if live is not None else (False, [])
    if (
        live is None
        or live.get("detached")
        or live.get("branch") != from_branch
        or live.get("head") != checkpoint
        or not pristine
    ):
        raise Refusal(
            "stale active durable custody does not match a pristine source "
            "worktree at the fetched checkpoint",
            blockers=[str(path), *residue],
        )
    if _ref_sha(context, f"refs/heads/{from_branch}") != checkpoint:
        raise Refusal("source local branch does not equal the fetched checkpoint")
    if not _is_ancestor(context, recorded_head, checkpoint):
        raise Refusal(
            "recorded durable HEAD is not an ancestor of the fetched checkpoint"
        )

    before = json.loads(json.dumps(record, sort_keys=True))
    reconciled_at = _utc_now()
    proof = {
        "package": package,
        "from_ref": from_ref,
        "from_branch": from_branch,
        "previous_head": recorded_head,
        "checkpoint_sha": checkpoint,
        "owner_authorization_ref": owner_authorization_ref,
        "source_unavailable_ref": source_unavailable_ref,
        "reconciled_at": reconciled_at,
    }
    after = json.loads(json.dumps(before, sort_keys=True))
    after.update(
        {
            "previous_head": recorded_head,
            "head": checkpoint,
            "head_reconciled_at": reconciled_at,
            "updated_at": reconciled_at,
            "remote_branch_tip": checkpoint,
            "remote_branch_status": "fetched",
            "owner_reassignment_head_reconciliation": proof,
        }
    )
    record.clear()
    record.update(after)
    reconciliation = {"before": before, "after": after}
    _validate_owner_reassignment_head_reconciliation_record(record)
    return reconciliation


def _source_durable_registry_snapshot(
    context: RepoContext,
    registry: dict[str, Any],
    *,
    package: str,
    from_ref: str,
    from_branch: str,
    checkpoint: str,
) -> list[dict[str, Any]]:
    candidates = [
        record
        for record in registry["worktrees"]
        if record.get("state") == "active"
        and record.get("kind") == "durable"
        and (
            str(record.get("package", "")).casefold() == package.casefold()
            or record.get("branch") == from_branch
        )
    ]
    path_keys = [_path_key(str(record.get("path", ""))) for record in candidates]
    if len(candidates) > 1 or len(path_keys) != len(set(path_keys)):
        raise Refusal(
            "owner reassignment has duplicate or ambiguous target/source durable records"
        )
    snapshots: list[dict[str, Any]] = []
    for record in candidates:
        raw_path = record.get("path")
        if not isinstance(raw_path, str) or not Path(raw_path).is_absolute():
            raise Refusal(
                "target/source durable registry path is not exact and absolute"
            )
        path = _canonical(raw_path)
        if raw_path != str(path):
            raise Refusal(
                "target/source durable registry path is not its exact canonical path"
            )
        if (
            record.get("package") != package
            or record.get("task_ref") != from_ref
            or record.get("branch") != from_branch
            or record.get("head") != checkpoint
        ):
            raise Refusal(
                "target/source durable registry record does not match the exact "
                "source package, task, branch, and checkpoint"
            )
        live = _worktree_at(context.root, path)
        if live is None:
            raise Refusal("target/source durable worktree is missing from Git")
        if live.get("detached") or live.get("branch") != from_branch:
            raise Refusal("target/source durable worktree is detached or switched")
        if live.get("head") != checkpoint:
            raise Refusal("target/source durable worktree HEAD differs from checkpoint")
        pristine, residue = _is_pristine(path)
        if not pristine:
            raise Refusal(
                "target/source durable worktree is not pristine",
                blockers=[str(path), *residue],
            )
        snapshots.append(
            {
                "path": str(path),
                "package": package,
                "task_ref": from_ref,
                "branch": from_branch,
                "head": checkpoint,
            }
        )
    return snapshots


def _preparation_digest(record: dict[str, Any]) -> str:
    immutable = {
        field: record.get(field)
        for field in sorted(
            _owner_reassignment_preparation_immutable_fields(record)
        )
    }
    payload = json.dumps(
        immutable, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _completed_preparation_from_pending(pending: dict[str, Any]) -> dict[str, Any]:
    source_snapshot = {
        "local_branch_sha": pending.get("old_local_ref"),
        "worktrees": pending.get("source_worktrees"),
        "durable_records": pending.get("source_durable_records"),
    }
    record = {
        "schema_version": 1,
        "status": "completed",
        "package": pending.get("package"),
        "owner_authorization_ref": pending.get("owner_authorization_ref"),
        "from_ref": pending.get("from_ref"),
        "to_ref": pending.get("task_ref"),
        "from_branch": pending.get("from_branch"),
        "to_branch": pending.get("successor_branch"),
        "checkpoint_sha": pending.get("checkpoint_sha"),
        "control_branch": pending.get("control_branch"),
        "prepared_from_main": pending.get("prepared_from_main"),
        "new_branch_response": pending.get("new_branch_response"),
        "source_snapshot": source_snapshot,
        "prepared_at": pending.get("push_proven_at"),
    }
    reconciliation = pending.get("source_registry_reconciliation")
    if reconciliation is not None:
        record["source_head_reconciliation"] = json.loads(
            json.dumps(
                reconciliation["after"][
                    "owner_reassignment_head_reconciliation"
                ],
                sort_keys=True,
            )
        )
    response = record["new_branch_response"]
    columns = response.split("\t") if isinstance(response, str) else []
    if (
        len(columns) != 3
        or columns[0] != "*"
        or columns[1].rpartition(":")[0] != record["checkpoint_sha"]
        or columns[1].rpartition(":")[2] != f"refs/heads/{record['to_branch']}"
        or columns[2] != "[new branch]"
    ):
        raise Refusal("completed preparation lacks the exact new-branch response")
    if not isinstance(record["prepared_at"], str) or not record["prepared_at"]:
        raise Refusal("completed preparation lacks its proof timestamp")
    record["preparation_id"] = _preparation_digest(record)
    return record


def _append_completed_preparation(
    registry: dict[str, Any], pending: dict[str, Any]
) -> dict[str, Any]:
    preparation = _completed_preparation_from_pending(pending)
    completed = [
        item
        for item in registry["owner_reassignment_preparations"]
        if isinstance(item, dict)
        and str(item.get("package", "")).casefold()
        == str(preparation["package"]).casefold()
        and item.get("status") == "completed"
    ]
    if completed:
        raise Refusal(
            "package already has an unconsumed owner-reassignment preparation"
        )
    registry["owner_reassignment_preparations"].append(preparation)
    return preparation


def _matching_owner_reassignment_preparation(
    registry: dict[str, Any], claim: dict[str, Any], handoff: dict[str, Any]
) -> dict[str, Any]:
    expected = {
        "package": claim.get("package"),
        "owner_authorization_ref": handoff.get("owner_authorization_ref"),
        "from_ref": handoff.get("from_ref"),
        "to_ref": handoff.get("to_ref"),
        "from_branch": handoff.get("from_branch"),
        "to_branch": handoff.get("to_branch"),
        "checkpoint_sha": handoff.get("checkpoint_sha"),
    }
    matches = [
        item
        for item in registry["owner_reassignment_preparations"]
        if isinstance(item, dict)
        and str(item.get("package", "")).casefold()
        == str(expected["package"]).casefold()
        and all(
            item.get(field) == value
            for field, value in expected.items()
            if field != "package"
        )
    ]
    if len(matches) != 1:
        raise Refusal("claim does not have one exact owner-reassignment preparation")
    preparation = matches[0]
    expected_fields = (
        _owner_reassignment_preparation_immutable_fields(preparation)
        | {"status", "preparation_id"}
    )
    if preparation.get("status") == "consumed":
        expected_fields |= {"consumed_at", "consumed_on_main"}
    if set(preparation) != expected_fields:
        raise Refusal("owner-reassignment preparation has an inexact field set")
    if preparation.get("preparation_id") != _preparation_digest(preparation):
        raise Refusal("owner-reassignment preparation identity digest is invalid")
    if preparation.get("schema_version") != 1 or preparation.get("status") not in {
        "completed",
        "consumed",
    }:
        raise Refusal("owner-reassignment preparation state is invalid")
    if (
        not isinstance(preparation.get("prepared_at"), str)
        or not preparation["prepared_at"]
        or not OWNER_REASSIGNMENT_CONTROL_BRANCH_RE.fullmatch(
            str(preparation.get("control_branch", ""))
        )
    ):
        raise Refusal("owner-reassignment preparation provenance is invalid")
    _validate_sha(str(preparation.get("prepared_from_main", "")))
    response = preparation.get("new_branch_response")
    if not isinstance(response, str):
        raise Refusal("owner-reassignment preparation lacks a new-branch response")
    columns = response.split("\t")
    if (
        len(columns) != 3
        or columns[0] != "*"
        or columns[1].rpartition(":")[0] != handoff.get("checkpoint_sha")
        or columns[1].rpartition(":")[2] != f"refs/heads/{handoff.get('to_branch')}"
        or columns[2] != "[new branch]"
    ):
        raise Refusal("owner-reassignment preparation new-branch response is invalid")
    return preparation


def _begin_owner_reassignment_worktree_create(
    *,
    preparation: dict[str, Any],
    source_record: dict[str, Any] | None,
    handoff: dict[str, Any],
    receiver_path: Path,
    origin_main: str,
) -> dict[str, Any]:
    if preparation.get("status") != "completed":
        raise Refusal("owner-reassignment preparation is not available to consume")
    if preparation.get("preparation_id") != _preparation_digest(preparation):
        raise Refusal("owner-reassignment preparation identity digest is invalid")
    origin_main = _validate_sha(origin_main)
    canonical_receiver = _canonical(receiver_path)
    source_before = (
        json.loads(json.dumps(source_record, sort_keys=True))
        if source_record is not None
        else None
    )
    transition = {
        "preparation_id": preparation["preparation_id"],
        "receiver_path": str(canonical_receiver),
        "origin_main": origin_main,
        "source_before": source_before,
        "handoff": dict(handoff),
    }
    preparation["status"] = "consuming"
    preparation["consuming_at"] = _utc_now()
    preparation["consuming_on_main"] = origin_main
    preparation["consuming_receiver_path"] = str(canonical_receiver)
    return transition


def _require_pristine_owner_reassignment_receiver(receiver_path: Path) -> None:
    pristine, residue = _is_pristine(receiver_path)
    if not pristine:
        raise Refusal(
            "owner-reassignment receiver worktree is not pristine; "
            "preparation consumption remains pending",
            blockers=[str(receiver_path), *residue],
        )


def _finalize_owner_reassignment_worktree_create(
    context: RepoContext,
    registry: dict[str, Any],
    pending: dict[str, Any],
    *,
    completed: bool,
) -> None:
    transition = pending.get("owner_reassignment")
    if transition is None:
        return
    expected_transition_fields = {
        "preparation_id",
        "receiver_path",
        "origin_main",
        "source_before",
        "handoff",
    }
    if not isinstance(transition, dict) or set(transition) != expected_transition_fields:
        raise Refusal("pending owner-reassignment worktree transition is invalid")
    preparation_id = transition.get("preparation_id")
    preparations = [
        item
        for item in registry["owner_reassignment_preparations"]
        if isinstance(item, dict)
        and item.get("preparation_id") == preparation_id
    ]
    if len(preparations) != 1:
        raise Refusal("pending worktree creation has ambiguous preparation custody")
    preparation = preparations[0]
    receiver_path = _canonical(str(transition.get("receiver_path", "")))
    if (
        preparation.get("status") != "consuming"
        or preparation.get("preparation_id") != _preparation_digest(preparation)
        or preparation.get("consuming_on_main") != transition.get("origin_main")
        or preparation.get("consuming_receiver_path") != str(receiver_path)
        or not isinstance(preparation.get("consuming_at"), str)
    ):
        raise Refusal("pending owner-reassignment preparation consumption changed")
    if _path_key(str(pending.get("path", ""))) != _path_key(receiver_path):
        raise Refusal("pending receiver path differs from preparation consumption")
    if completed:
        _require_pristine_owner_reassignment_receiver(receiver_path)
    handoff = transition.get("handoff")
    if not isinstance(handoff, dict) or set(handoff) != OWNER_REASSIGNMENT_HANDOFF_FIELDS:
        raise Refusal("pending owner-reassignment handoff is invalid")
    expected_handoff = {
        "type": "owner_reassignment",
        "from_ref": preparation.get("from_ref"),
        "to_ref": preparation.get("to_ref"),
        "from_branch": preparation.get("from_branch"),
        "to_branch": preparation.get("to_branch"),
        "checkpoint_sha": preparation.get("checkpoint_sha"),
        "owner_authorization_ref": preparation.get("owner_authorization_ref"),
    }
    if handoff != expected_handoff:
        raise Refusal("pending owner-reassignment handoff changed")

    source_before = transition.get("source_before")
    if source_before is not None:
        if not isinstance(source_before, dict):
            raise Refusal("pending owner-reassignment source record is invalid")
        source_path = _canonical(str(source_before.get("path", "")))
        matching_sources = [
            record
            for record in registry["worktrees"]
            if _path_key(str(record.get("path", ""))) == _path_key(source_path)
        ]
        if len(matching_sources) != 1 or matching_sources[0] != source_before:
            raise Refusal("pending owner-reassignment source registry record changed")
        source_record = matching_sources[0]
    else:
        source_record = None

    checkpoint = _validate_sha(str(preparation.get("checkpoint_sha", "")))
    old_local_ref = _ref_sha(
        context, f"refs/heads/{preparation.get('from_branch')}"
    )
    current_source_snapshot = {
        "local_branch_sha": old_local_ref,
        "worktrees": _snapshot_branch_worktrees(
            context, str(preparation.get("from_branch")), checkpoint
        ),
        "durable_records": _source_durable_registry_snapshot(
            context,
            registry,
            package=str(preparation.get("package")),
            from_ref=str(preparation.get("from_ref")),
            from_branch=str(preparation.get("from_branch")),
            checkpoint=checkpoint,
        ),
    }
    if current_source_snapshot != preparation.get("source_snapshot"):
        raise Refusal("pending owner-reassignment source snapshot changed")

    if completed:
        if (
            _fetch_origin_branch(context, str(preparation.get("from_branch")))
            != checkpoint
            or _fetch_origin_branch(context, str(preparation.get("to_branch")))
            != checkpoint
        ):
            raise Refusal(
                "pending owner-reassignment remote branches changed before consume"
            )
        _fetch_origin_main(context)
        if _ref_sha(context, "refs/remotes/origin/main") != transition["origin_main"]:
            raise Refusal(
                "origin/main moved during owner-reassignment receiver creation"
            )
        matching_claims = [
            claim
            for claim in _strict_live_claims(context)
            if claim.get("package") == preparation.get("package")
        ]
        if len(matching_claims) != 1:
            raise Refusal(
                "pending owner-reassignment claim custody is missing or ambiguous"
            )
        live_claim = matching_claims[0]
        if (
            live_claim.get("state") != "active"
            or live_claim.get("writer_ref") != preparation.get("to_ref")
            or live_claim.get("branch") != preparation.get("to_branch")
            or live_claim.get("handoff") != handoff
        ):
            raise Refusal(
                "pending owner-reassignment claim no longer authorizes receiver creation"
            )
        _require_pristine_owner_reassignment_receiver(receiver_path)

    preparation.pop("consuming_at", None)
    preparation.pop("consuming_on_main", None)
    preparation.pop("consuming_receiver_path", None)
    if not completed:
        preparation["status"] = "completed"
        return

    if source_record is not None:
        source_record.update(
            {
                "kind": "reassignment_source",
                "head": checkpoint,
                "lease": None,
                "preserved_at": _utc_now(),
                "preserved_by_owner_reassignment": dict(handoff),
                "updated_at": _utc_now(),
            }
        )
    preparation["status"] = "consumed"
    preparation["consumed_at"] = _utc_now()
    preparation["consumed_on_main"] = transition["origin_main"]


def _strict_live_claims(context: RepoContext) -> list[dict[str, Any]]:
    names = _git_optional(
        context.root,
        "ls-tree",
        "-r",
        "--name-only",
        "origin/main",
        "docs/governance/lane_claims",
    )
    if names is None:
        raise Refusal("could not enumerate authoritative lane claims")
    claims: list[dict[str, Any]] = []
    prefix = "docs/governance/lane_claims/"
    for name in names.splitlines():
        if not name.startswith(prefix) or "/" in name[len(prefix) :] or not name.endswith(
            ".json"
        ):
            continue
        raw = _git_optional(context.root, "show", f"origin/main:{name}")
        if raw is None:
            raise Refusal(f"could not read authoritative claim: {name}")
        try:
            claim = json.loads(raw)
        except json.JSONDecodeError as error:
            raise Refusal(f"authoritative claim is invalid JSON: {name}") from error
        if not isinstance(claim, dict):
            raise Refusal(f"authoritative claim is not an object: {name}")
        package = claim.get("package")
        state = claim.get("state")
        if not isinstance(package, str) or not PACKAGE_RE.fullmatch(package):
            raise Refusal(f"authoritative claim has an invalid package: {name}")
        if state not in {"active", "paused", "closed", "superseded"}:
            raise Refusal(f"authoritative claim has an invalid state: {name}")
        if state in {"active", "paused"}:
            _validate_work_branch(str(claim.get("branch", "")))
            claims.append(claim)
    return claims


def command_prepare_owner_reassignment(
    context: RepoContext, args: argparse.Namespace
) -> dict[str, Any]:
    """Create one absent successor branch without adopting old-writer authority."""

    _require_execute(args.execute)
    package = _validate_package(args.package)
    task_ref = _validate_task_ref(args.task_ref)
    _validate_delivery_ref(task_ref)
    successor_branch = _validate_work_branch(args.successor_branch)
    checkpoint = _validate_sha(args.expected_checkpoint)
    owner_authorization_ref = _validate_delivery_ref(args.owner_authorization_ref)
    raw_source_unavailable_ref = getattr(args, "source_unavailable_ref", None)
    source_unavailable_ref = (
        _validate_delivery_ref(raw_source_unavailable_ref)
        if raw_source_unavailable_ref is not None
        else None
    )

    _fetch_origin_main(context)
    claim = _claim_from_origin_main(context, package)
    if claim.get("state") != "active":
        raise Refusal("owner reassignment requires an active authoritative claim")
    from_ref = _validate_delivery_ref(str(claim.get("writer_ref", "")))
    from_branch = _validate_work_branch(str(claim.get("branch", "")))
    if from_ref == task_ref:
        raise Refusal("owner reassignment must change the writer reference")
    if from_branch == successor_branch:
        raise Refusal("owner reassignment requires a distinct successor branch")

    old_tip = _fetch_origin_branch(context, from_branch)
    if old_tip != checkpoint:
        raise Refusal(
            "expected checkpoint must equal the exact fetched source-branch tip"
        )
    if _fetch_origin_branch(context, successor_branch) is not None:
        raise Refusal("successor branch already exists on origin")
    if _ref_sha(context, f"refs/heads/{successor_branch}") is not None:
        raise Refusal("successor branch already exists as a local branch")
    if _ref_sha(context, f"refs/remotes/origin/{successor_branch}") is not None:
        raise Refusal("successor branch has a stale or ambiguous remote-tracking ref")
    live_claims_snapshot = _strict_live_claims(context)
    for other_claim in live_claims_snapshot:
        if (
            other_claim.get("package") != package
            and other_claim.get("branch") == successor_branch
        ):
            raise Refusal(
                "successor branch is already claimed by another live package"
            )

    with _registry_lock(context.registry_path):
        registry = _load_registry(context.registry_path)
        assert registry is not None
        control = _owner_reassignment_control_admission(
            context,
            registry,
            task_ref=task_ref,
            package=package,
            require_no_pending=False,
        )
        recovered = _reconcile_pending(context, registry)
        if recovered is not None:
            raise Refusal(
                "a prior pending operation was reconciled; rerun from freshly verified state"
            )
        control = _owner_reassignment_control_admission(
            context,
            registry,
            task_ref=task_ref,
            package=package,
            require_no_pending=True,
        )
        control_path = _canonical(control["path"])
        lease = control.get("lease")
        live_control = _worktree_at(context.root, control_path)
        pristine_control, control_residue = _is_pristine(control_path)
        origin_main = _ref_sha(context, "refs/remotes/origin/main")
        control_branch = _current_branch(control_path)
        if _path_key(Path.cwd()) != _path_key(control_path):
            raise Refusal("prepare-owner-reassignment must run from the leased _control path")
        if not isinstance(lease, dict) or (
            lease.get("task_ref"), lease.get("purpose"), lease.get("package")
        ) != (task_ref, "control", package):
            raise Refusal("control lease does not match the receiving task and package")
        if control_branch == from_branch:
            raise Refusal("owner-reassignment control branch cannot be the source branch")
        if (
            live_control is None
            or control_branch is None
            or not OWNER_REASSIGNMENT_CONTROL_BRANCH_RE.fullmatch(control_branch)
            or control.get("branch") != control_branch
            or live_control.get("branch") != control_branch
            or origin_main is None
            or live_control.get("head") != origin_main
            or control.get("head") != origin_main
            or not pristine_control
        ):
            raise Refusal(
                "control singleton must be pristine on an exact current-main "
                "delivery-owner-reassignment branch",
                blockers=control_residue,
            )

        _assert_successor_namespace_available(
            context, registry, successor_branch, live_claims_snapshot
        )

        existing_completed = [
            item
            for item in registry["owner_reassignment_preparations"]
            if isinstance(item, dict)
            and str(item.get("package", "")).casefold() == package.casefold()
            and item.get("status") == "completed"
        ]
        if existing_completed:
            raise Refusal(
                "package already has an unconsumed owner-reassignment preparation"
            )

        if _remote_branch_tip(context, "main") != origin_main:
            raise Refusal("origin/main moved during owner-reassignment preparation")
        if _fetch_origin_branch(context, from_branch) != checkpoint:
            raise Refusal("source branch moved before successor creation")
        if _remote_branch_tip(context, successor_branch) is not None:
            raise Refusal("successor branch appeared before guarded creation")

        old_local_ref = _ref_sha(context, f"refs/heads/{from_branch}")
        if old_local_ref not in {None, checkpoint}:
            raise Refusal(
                "local source branch differs from the authorized remote checkpoint"
            )
        source_worktrees = _snapshot_branch_worktrees(
            context, from_branch, checkpoint
        )
        source_registry_reconciliation = (
            _prepare_source_registry_head_reconciliation(
                context,
                registry,
                package=package,
                from_ref=from_ref,
                from_branch=from_branch,
                checkpoint=checkpoint,
                owner_authorization_ref=owner_authorization_ref,
                source_unavailable_ref=source_unavailable_ref,
            )
        )
        source_durable_records = _source_durable_registry_snapshot(
            context,
            registry,
            package=package,
            from_ref=from_ref,
            from_branch=from_branch,
            checkpoint=checkpoint,
        )
        pending = {
            "operation": "owner_reassignment_branch_create",
            "package": package,
            "task_ref": task_ref,
            "from_ref": from_ref,
            "from_branch": from_branch,
            "successor_branch": successor_branch,
            "checkpoint_sha": checkpoint,
            "owner_authorization_ref": owner_authorization_ref,
            "old_local_ref": old_local_ref,
            "source_worktrees": source_worktrees,
            "source_durable_records": source_durable_records,
            "control_branch": control_branch,
            "prepared_from_main": origin_main,
            "live_claims_snapshot": live_claims_snapshot,
            "push_proven_new": False,
            "started_at": _utc_now(),
        }
        if source_registry_reconciliation is not None:
            pending["source_registry_reconciliation"] = (
                source_registry_reconciliation
            )
        registry["pending"] = pending
        _validate_pending_owner_reassignment_branch_create(registry, pending)
        _atomic_write(context.registry_path, registry)

        # The empty expected value is an absent-ref compare-and-set.  Although
        # Git exposes that guard through force-with-lease, no existing ref can
        # satisfy it, the refspec has no leading '+', and no force update is
        # possible: this invocation can only create a previously absent ref.
        push = _git_result(
            context.root,
            "push",
            "--porcelain",
            f"--force-with-lease=refs/heads/{successor_branch}:",
            "origin",
            f"{checkpoint}:refs/heads/{successor_branch}",
        )
        if push.returncode:
            if _remote_branch_tip(context, successor_branch) is None:
                _rollback_source_registry_reconciliation(registry, pending)
                registry["pending"] = None
                _atomic_write(context.registry_path, registry)
            detail = push.stderr.strip() or push.stdout.strip() or "git push failed"
            raise Refusal(
                "guarded absent-ref successor creation failed; old branch was preserved: "
                + detail
            )
        expected_target = f"refs/heads/{successor_branch}"
        new_branch_proofs = []
        for line in push.stdout.splitlines():
            columns = line.split("\t")
            if len(columns) != 3:
                continue
            status, mapping, summary = columns
            source, separator, target = mapping.rpartition(":")
            if (
                status == "*"
                and separator
                and source == checkpoint
                and target == expected_target
                and summary == "[new branch]"
            ):
                new_branch_proofs.append(line)
        if len(new_branch_proofs) != 1:
            raise Refusal(
                "push succeeded without an exact new-branch proof; pending state is preserved"
            )
        pending["new_branch_response"] = new_branch_proofs[0]
        pending["push_proven_new"] = True
        pending["push_proven_at"] = _utc_now()
        _atomic_write(context.registry_path, registry)

        expected_preparation_id = _completed_preparation_from_pending(pending)[
            "preparation_id"
        ]
        # Normal completion deliberately uses the same final-boundary recovery
        # path.  This keeps exact server reproof and crash behavior identical.
        _reconcile_owner_reassignment_branch_create(context, registry, pending)
        matches = [
            item
            for item in registry["owner_reassignment_preparations"]
            if item.get("preparation_id") == expected_preparation_id
        ]
        if len(matches) != 1:
            raise Refusal("completed preparation lost its exact registry identity")
        preparation = matches[0]
    return {
        "status": "successor_prepared",
        "package": package,
        "from_ref": from_ref,
        "to_ref": task_ref,
        "from_branch": from_branch,
        "successor_branch": successor_branch,
        "checkpoint_sha": checkpoint,
        "owner_authorization_ref": owner_authorization_ref,
        "source_unavailable_ref": source_unavailable_ref,
        "source_registry_head_reconciled": (
            source_registry_reconciliation is not None
        ),
        "preparation_id": preparation["preparation_id"],
        "old_branch_preserved": True,
        "old_worktrees_preserved": [item["path"] for item in source_worktrees],
        "local_successor_created": False,
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


def _ordinary_worktree_remove(context: RepoContext, path: Path) -> None:
    """Use Git's sole non-force removal primitive for an exact guarded path."""

    _git(context.root, "worktree", "remove", str(path))


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
    _ordinary_worktree_remove(context, path)
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


def _exact_canonical_argument_path(value: Any) -> Path:
    if not isinstance(value, str) or not Path(value).is_absolute():
        raise Refusal("closed-custody path must be exact, absolute, and canonical")
    path = _canonical(value)
    if str(path) != value:
        raise Refusal("closed-custody path must be exact, absolute, and canonical")
    return path


def _closed_custody_cleanup_claim(
    context: RepoContext,
    *,
    package: str,
    task_ref: str,
    owner_authorization_ref: str,
) -> dict[str, Any]:
    claim = _active_claim(context, package, task_ref)
    evidence = f"docs/governance/lane_claims/evidence/{package}.md"
    receipt = f"docs/governance/lane_claims/receipts/{package}.json"
    claim_path = f"docs/governance/lane_claims/{package}.json"
    required_surfaces = CLOSED_CUSTODY_REQUIRED_SURFACES | {
        claim_path,
        evidence,
        receipt,
    }
    surfaces = claim.get("surfaces")
    domains = claim.get("domains")
    if (
        claim.get("assignment") != "implementation"
        or claim.get("delivery_path") != "Protected"
        or claim.get("repository_authority") != "through_merge"
        or claim.get("production_authority") != "withheld"
        or claim.get("review_requirement") != "independent"
        or claim.get("owner_outcome_ref") != owner_authorization_ref
        or not isinstance(surfaces, list)
        or not required_surfaces.issubset(set(surfaces))
        or not isinstance(domains, list)
        or not CLOSED_CUSTODY_REQUIRED_DOMAINS.issubset(set(domains))
    ):
        raise Refusal(
            "active cleanup claim does not grant exact Protected closed-custody authority"
        )
    evidence_surfaces = claim.get("evidence_surfaces")
    if not isinstance(evidence_surfaces, list) or evidence not in evidence_surfaces:
        raise Refusal("active cleanup claim lacks its exact evidence surface")
    return claim


def _git_blob_sha(context: RepoContext, ref: str, path: str) -> str | None:
    value = _git_optional(context.root, "rev-parse", "--verify", f"{ref}:{path}")
    return value.casefold() if value and SHA_RE.fullmatch(value.casefold()) else None


def _accepted_closed_custody_review(
    context: RepoContext,
    *,
    package: str,
    cleanup_task_ref: str,
    cleanup_head: str,
) -> tuple[dict[str, Any], str]:
    receipt_path = f"docs/governance/lane_claims/receipts/{package}.json"
    raw = _git_optional(context.root, "show", f"origin/main:{receipt_path}")
    if raw is None:
        raise Refusal("accepted closed-custody review receipt is absent from fetched main")
    try:
        receipt = json.loads(raw)
    except json.JSONDecodeError as error:
        raise Refusal("closed-custody review receipt is invalid JSON") from error
    if not isinstance(receipt, dict):
        raise Refusal("closed-custody review receipt is not an object")
    expected_fields = {
        "schema_version",
        "package",
        "candidate_sha",
        "review_type",
        "reviewer_ref",
        "result",
        "reviewed_at",
        "findings",
        "evidence_ref",
    }
    candidate = _validate_sha(str(receipt.get("candidate_sha", "")))
    reviewer_ref = _validate_delivery_ref(str(receipt.get("reviewer_ref", "")))
    findings = receipt.get("findings")
    if (
        set(receipt) != expected_fields
        or receipt.get("schema_version") != 1
        or receipt.get("package") != package
        or receipt.get("review_type") != "independent"
        or receipt.get("result") != "pass"
        or reviewer_ref == cleanup_task_ref
        or not isinstance(findings, list)
        or any(
            not isinstance(finding, dict)
            or finding.get("status") not in {"resolved", "informational"}
            for finding in findings
        )
        or receipt.get("evidence_ref")
        != f"docs/governance/lane_claims/evidence/{package}.md"
    ):
        raise Refusal("closed-custody review receipt is not an exact independent pass")
    if _git_blob_sha(context, "origin/main", str(receipt["evidence_ref"])) is None:
        raise Refusal("accepted closed-custody review evidence is absent from fetched main")
    _validate_utc_timestamp(receipt.get("reviewed_at"), field="reviewed_at")
    _exact_commit(context, candidate)
    if not _is_ancestor(context, candidate, cleanup_head):
        raise Refusal("reviewed closed-custody candidate is not in the cleanup branch")
    for path in CLOSED_CUSTODY_REQUIRED_SURFACES:
        candidate_blob = _git_blob_sha(context, candidate, path)
        main_blob = _git_blob_sha(context, "origin/main", path)
        cleanup_blob = _git_blob_sha(context, cleanup_head, path)
        if candidate_blob is None or not (
            candidate_blob == main_blob == cleanup_blob
        ):
            raise Refusal(
                f"reviewed closed-custody surface is not exact on fetched main: {path}"
            )
    script_blob = _git_blob_sha(
        context, "origin/main", "scripts/worktree_lifecycle.py"
    )
    executing_blob = _git(
        context.root, "hash-object", str(_canonical(Path(__file__)))
    ).casefold()
    if script_blob is None or executing_blob != script_blob:
        raise Refusal(
            "executing lifecycle script is not the reviewed implementation on fetched main"
        )
    return receipt, script_blob


def _unique_active_durable_record(
    registry: dict[str, Any],
    *,
    package: str,
    path: Path,
    branch: str,
    task_ref: str,
    label: str,
) -> dict[str, Any]:
    matches = [
        record
        for record in registry["worktrees"]
        if isinstance(record, dict)
        and record.get("state") == "active"
        and record.get("kind") == "durable"
        and (
            record.get("package") == package
            or record.get("branch") == branch
            or _path_key(str(record.get("path", ""))) == _path_key(path)
        )
    ]
    if len(matches) != 1:
        raise Refusal(f"{label} registry custody is missing, duplicated, or ambiguous")
    record = matches[0]
    if (
        record.get("package") != package
        or record.get("branch") != branch
        or record.get("task_ref") != task_ref
        or record.get("path") != str(path)
        or record.get("lease") is not None
    ):
        raise Refusal(f"{label} registry identity or lease is not exact")
    all_path_matches = [
        item
        for item in registry["worktrees"]
        if isinstance(item, dict)
        and _path_key(str(item.get("path", ""))) == _path_key(path)
    ]
    if all_path_matches != [record]:
        raise Refusal(f"{label} registry path custody is duplicated or ambiguous")
    return record


def _closed_custody_worktree_proof(
    context: RepoContext,
    registry: dict[str, Any],
    record: dict[str, Any],
    *,
    path: Path,
    branch: str,
    expected_head: str,
    label: str,
) -> list[dict[str, Any]]:
    _assert_managed_target(registry, path)
    if not path.exists():
        raise Refusal(f"{label} path is absent")
    _assert_same_repository(context, path)
    all_worktrees = _worktrees(context.root)
    entries = [
        entry
        for entry in all_worktrees
        if _path_key(str(entry.get("worktree", ""))) == _path_key(path)
    ]
    if len(entries) != 1:
        raise Refusal(f"{label} Git worktree identity is missing or ambiguous")
    entry = entries[0]
    local_head = _ref_sha(context, f"refs/heads/{branch}")
    current_branch = _current_branch(path)
    live_head = _validate_sha(_git(path, "rev-parse", "HEAD"))
    if (
        entry.get("branch") != branch
        or entry.get("head") != expected_head
        or current_branch != branch
        or local_head != expected_head
        or live_head != expected_head
    ):
        raise Refusal(f"{label} live, branch, or local HEAD is not exact")
    pristine, residue = _is_pristine(path)
    if not pristine:
        raise Refusal(
            f"{label} contains tracked, untracked, or ignored residue",
            blockers=residue,
        )
    if record.get("path") != str(path):
        raise Refusal(f"{label} registry path is not canonical")
    return all_worktrees


def _closed_custody_pending_matches(
    pending: dict[str, Any],
    *,
    cleanup_package: str,
    cleanup_task_ref: str,
    target_package: str,
    target_path: Path,
    target_branch: str,
    source_task_ref: str,
    expected_head: str,
    owner_authorization_ref: str,
    source_unavailable_ref: str,
) -> bool:
    after = pending.get("after_record")
    proof = after.get("closed_custody_retirement") if isinstance(after, dict) else None
    return bool(
        isinstance(proof, dict)
        and pending.get("operation") == "retire_closed_custody"
        and proof.get("cleanup_package") == cleanup_package
        and proof.get("cleanup_task_ref") == cleanup_task_ref
        and proof.get("target_package") == target_package
        and proof.get("target_path") == str(target_path)
        and proof.get("target_branch") == target_branch
        and proof.get("source_task_ref") == source_task_ref
        and proof.get("expected_head") == expected_head
        and proof.get("owner_authorization_ref") == owner_authorization_ref
        and proof.get("source_unavailable_ref") == source_unavailable_ref
    )


def command_retire_closed_custody(
    context: RepoContext, args: argparse.Namespace
) -> dict[str, Any]:
    """Retire one closed-claim durable worktree under successor custody."""

    _require_execute(args.execute)
    cleanup_package = _validate_package(args.cleanup_package)
    cleanup_task_ref = _validate_task_ref(args.task_ref)
    _validate_delivery_ref(cleanup_task_ref)
    target_package = _validate_package(args.target_package)
    target_path = _exact_canonical_argument_path(args.path)
    target_branch = _validate_work_branch(args.branch)
    source_task_ref = _validate_delivery_ref(args.source_task_ref)
    expected_head = _validate_sha(args.expected_head)
    owner_authorization_ref = _validate_delivery_ref(args.owner_authorization_ref)
    source_unavailable_ref = _validate_delivery_ref(args.source_unavailable_ref)
    if len(
        {
            cleanup_task_ref,
            source_task_ref,
            owner_authorization_ref,
            source_unavailable_ref,
        }
    ) != 4:
        raise Refusal(
            "cleanup caller, source task, owner authorization, and source-unavailability "
            "references must be distinct"
        )

    recovered_pending: dict[str, Any] | None = None
    with _registry_lock(context.registry_path):
        registry = _load_registry(context.registry_path)
        assert registry is not None
        _assert_registry_identity(context, registry)
        pending = registry.get("pending")
        if pending is not None:
            if not isinstance(pending, dict) or not _closed_custody_pending_matches(
                pending,
                cleanup_package=cleanup_package,
                cleanup_task_ref=cleanup_task_ref,
                target_package=target_package,
                target_path=target_path,
                target_branch=target_branch,
                source_task_ref=source_task_ref,
                expected_head=expected_head,
                owner_authorization_ref=owner_authorization_ref,
                source_unavailable_ref=source_unavailable_ref,
            ):
                raise Refusal(
                    "an unresolved lifecycle journal is not this exact closed-custody request"
                )
            recovered_pending = _reconcile_pending(context, registry)
            if recovered_pending and recovered_pending.get("outcome") == "completed":
                return {
                    "status": "retired_recovered",
                    "path": str(target_path),
                    "head": expected_head,
                    "source_task_ref": source_task_ref,
                    "cleanup_task_ref": cleanup_task_ref,
                    "custody_proof": recovered_pending["proof"],
                    "recovered_pending": recovered_pending,
                }

    _fetch_origin_main(context)
    authoritative_main = _ref_sha(context, "refs/remotes/origin/main")
    if authoritative_main is None:
        raise Refusal("fetched origin/main has no exact commit")
    cleanup_claim = _closed_custody_cleanup_claim(
        context,
        package=cleanup_package,
        task_ref=cleanup_task_ref,
        owner_authorization_ref=owner_authorization_ref,
    )
    cleanup_branch = _validate_work_branch(str(cleanup_claim.get("branch", "")))
    target_claim = _claim_from_origin_main(context, target_package)
    if (
        target_claim.get("state") != "closed"
        or target_claim.get("writer_ref") != source_task_ref
        or target_claim.get("branch") != target_branch
    ):
        raise Refusal(
            "target claim is not exactly closed for its original task and branch"
        )
    cleanup_path = _canonical(Path.cwd())
    if _path_key(target_path) == _path_key(cleanup_path):
        raise Refusal("cleanup caller worktree cannot be its own retirement target")
    cleanup_remote = _remote_branch_tip(context, cleanup_branch)
    target_remote = _remote_branch_tip(context, target_branch)
    if cleanup_remote is None or target_remote is None:
        raise Refusal("cleanup or target branch is absent from the server")

    with _registry_lock(context.registry_path):
        registry = _load_registry(context.registry_path)
        assert registry is not None
        _assert_registry_identity(context, registry)
        if registry.get("pending") is not None:
            raise Refusal("lifecycle journal changed before closed-custody commit")
        cleanup_record = _unique_active_durable_record(
            registry,
            package=cleanup_package,
            path=cleanup_path,
            branch=cleanup_branch,
            task_ref=cleanup_task_ref,
            label="cleanup caller",
        )
        cleanup_local_head = _ref_sha(context, f"refs/heads/{cleanup_branch}")
        if cleanup_local_head is None:
            raise Refusal("cleanup caller local branch is absent")
        _closed_custody_worktree_proof(
            context,
            registry,
            cleanup_record,
            path=cleanup_path,
            branch=cleanup_branch,
            expected_head=cleanup_local_head,
            label="cleanup caller",
        )
        review_receipt, lifecycle_script_blob = _accepted_closed_custody_review(
            context,
            package=cleanup_package,
            cleanup_task_ref=cleanup_task_ref,
            cleanup_head=cleanup_local_head,
        )
        target_record = _unique_active_durable_record(
            registry,
            package=target_package,
            path=target_path,
            branch=target_branch,
            task_ref=source_task_ref,
            label="closed-custody target",
        )
        all_worktrees = _closed_custody_worktree_proof(
            context,
            registry,
            target_record,
            path=target_path,
            branch=target_branch,
            expected_head=expected_head,
            label="closed-custody target",
        )
        if _path_key(target_path) == _path_key(context.primary_root):
            raise Refusal("primary worktree closed-custody retirement is prohibited")
        nested = [
            str(entry.get("worktree"))
            for entry in all_worktrees
            if _path_key(str(entry.get("worktree", ""))) != _path_key(target_path)
            and _is_strictly_within(str(entry.get("worktree", "")), target_path)
        ]
        if nested:
            raise Refusal(
                "nested Git worktree exists inside the closed-custody target",
                blockers=nested,
            )
        previous_head = _validate_sha(str(target_record.get("head", "")))
        _exact_commit(context, previous_head)
        if not _is_ancestor(context, previous_head, expected_head):
            raise Refusal(
                "target registry HEAD is neither equal to nor an ancestor of expected HEAD"
            )
        for record in registry["worktrees"]:
            proof = record.get("closed_custody_retirement") if isinstance(record, dict) else None
            if (
                isinstance(proof, dict)
                and proof.get("source_unavailable_ref") == source_unavailable_ref
            ):
                raise Refusal("source-unavailability evidence reference was already used")

        if _ref_sha(context, "refs/remotes/origin/main") != authoritative_main:
            raise Refusal("fetched origin/main moved before closed-custody commit")
        if _closed_custody_cleanup_claim(
            context,
            package=cleanup_package,
            task_ref=cleanup_task_ref,
            owner_authorization_ref=owner_authorization_ref,
        ) != cleanup_claim:
            raise Refusal("cleanup claim changed before closed-custody commit")
        if _claim_from_origin_main(context, target_package) != target_claim:
            raise Refusal("target claim changed before closed-custody commit")
        terminal = _remote_branch_tuple(
            context, ("main", cleanup_branch, target_branch)
        )
        if terminal != {
            "main": authoritative_main,
            cleanup_branch: cleanup_local_head,
            target_branch: expected_head,
        } or cleanup_remote != cleanup_local_head or target_remote != expected_head:
            raise Refusal("main, cleanup branch, or target branch moved at commit boundary")
        terminal_registry = _load_registry(context.registry_path)
        if terminal_registry != registry:
            raise Refusal("registry changed at closed-custody commit boundary")
        _closed_custody_worktree_proof(
            context,
            registry,
            cleanup_record,
            path=cleanup_path,
            branch=cleanup_branch,
            expected_head=cleanup_local_head,
            label="cleanup caller",
        )
        _closed_custody_worktree_proof(
            context,
            registry,
            target_record,
            path=target_path,
            branch=target_branch,
            expected_head=expected_head,
            label="closed-custody target",
        )

        recorded_at = _utc_now()
        proof = {
            "schema_version": 1,
            "cleanup_package": cleanup_package,
            "cleanup_task_ref": cleanup_task_ref,
            "cleanup_path": str(cleanup_path),
            "cleanup_branch": cleanup_branch,
            "cleanup_head": cleanup_local_head,
            "reviewed_candidate": review_receipt["candidate_sha"],
            "reviewer_ref": review_receipt["reviewer_ref"],
            "lifecycle_script_blob": lifecycle_script_blob,
            "owner_authorization_ref": owner_authorization_ref,
            "source_unavailable_ref": source_unavailable_ref,
            "target_package": target_package,
            "source_task_ref": source_task_ref,
            "target_path": str(target_path),
            "target_branch": target_branch,
            "registry_previous_head": previous_head,
            "expected_head": expected_head,
            "authoritative_main": authoritative_main,
            "target_server_head": expected_head,
            "recorded_at": recorded_at,
        }
        _validate_closed_custody_retirement(proof)
        before = json.loads(json.dumps(target_record, sort_keys=True))
        after = _closed_custody_after_record(before, proof)
        registry["pending"] = {
            "operation": "retire_closed_custody",
            "path": str(target_path),
            "before_record": before,
            "after_record": after,
            "started_at": recorded_at,
        }
        _atomic_write(context.registry_path, registry)
        _closed_custody_worktree_proof(
            context,
            registry,
            target_record,
            path=target_path,
            branch=target_branch,
            expected_head=expected_head,
            label="closed-custody target",
        )
        _ordinary_worktree_remove(context, target_path)
        if target_path.exists() or _worktree_at(context.root, target_path) is not None:
            raise Refusal(
                "ordinary Git removal did not fully retire the closed-custody target"
            )
        matches = [
            (index, record)
            for index, record in enumerate(registry["worktrees"])
            if _path_key(str(record.get("path", ""))) == _path_key(target_path)
        ]
        if len(matches) != 1 or matches[0][1] != before:
            raise Refusal("closed-custody target lost exact registry custody")
        registry["worktrees"][matches[0][0]] = after
        registry["pending"] = None
        _atomic_write(context.registry_path, registry)
    return {
        "status": "retired_closed_custody",
        "path": str(target_path),
        "head": expected_head,
        "source_task_ref": source_task_ref,
        "cleanup_task_ref": cleanup_task_ref,
        "server_branch": target_branch,
        "server_tip": expected_head,
        "custody_proof": proof,
        "recovered_pending": recovered_pending,
    }


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
                _custody_existing_guard(registry, task_ref)
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
            entry.get("kind")
            in {"durable", "grandfathered_observation", "reassignment_source"}
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

    custody = subparsers.add_parser("control-custody", help="journal owner-authorized custody recovery")
    custody.add_argument("action", choices=["propose", "accept", "complete"])
    custody.add_argument("--task-ref", required=True)
    custody.add_argument("--proof-file")
    custody.add_argument("--transition")
    custody.add_argument("--acceptance-ref")
    custody.add_argument("--execute", action="store_true")
    guarded = subparsers.add_parser("control-run", help="run one current-lease guarded command")
    guarded.add_argument("--task-ref", required=True)
    guarded.add_argument("--lease-token", required=True)
    guarded.add_argument("--execute", action="store_true")
    guarded.add_argument("command", nargs=argparse.REMAINDER)

    owner_reassignment = subparsers.add_parser(
        "prepare-owner-reassignment",
        help="guard and create one exact owner-authorized successor branch",
    )
    owner_reassignment.add_argument("--package", required=True)
    owner_reassignment.add_argument("--task-ref", required=True)
    owner_reassignment.add_argument("--successor-branch", required=True)
    owner_reassignment.add_argument("--expected-checkpoint", required=True)
    owner_reassignment.add_argument("--owner-authorization-ref", required=True)
    owner_reassignment.add_argument(
        "--source-unavailable-ref",
        help=(
            "bounded orchestrator/lifecycle evidence reference; required only "
            "when the active durable registry HEAD must be reconciled"
        ),
    )
    owner_reassignment.add_argument("--execute", action="store_true")

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

    retire_closed_custody = subparsers.add_parser(
        "retire-closed-custody",
        help="retire one exact closed-claim durable worktree under successor custody",
    )
    retire_closed_custody.add_argument("--cleanup-package", required=True)
    retire_closed_custody.add_argument("--task-ref", required=True)
    retire_closed_custody.add_argument("--target-package", required=True)
    retire_closed_custody.add_argument("--path", required=True)
    retire_closed_custody.add_argument("--branch", required=True)
    retire_closed_custody.add_argument("--source-task-ref", required=True)
    retire_closed_custody.add_argument("--expected-head", required=True)
    retire_closed_custody.add_argument(
        "--owner-authorization-ref", required=True
    )
    retire_closed_custody.add_argument(
        "--source-unavailable-ref", required=True
    )
    retire_closed_custody.add_argument("--execute", action="store_true")

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
        elif args.subcommand == "control-custody":
            payload, code = command_control_custody(context, args), 0
        elif args.subcommand == "control-run":
            payload = command_control_run(context, args)
            code = payload["returncode"]
        elif args.subcommand == "prepare-owner-reassignment":
            payload, code = command_prepare_owner_reassignment(context, args), 0
        elif args.subcommand == "verify":
            payload, code = command_verify(context, args)
        elif args.subcommand == "retire":
            payload, code = command_retire(context, args), 0
        elif args.subcommand == "retire-closed-custody":
            payload, code = command_retire_closed_custody(context, args), 0
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
