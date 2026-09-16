#!/usr/bin/env python3
"""Generic, fail-closed delivery admission for PeerSlate repository work.

The active control plane is deliberately small: one index, one claim per
unresolved package, and one exact-candidate review receipt before merge. Claims
reserve branches, mutable paths, and logical domains. They never authorize a
production operation; that boundary is enforced by
``production_operation_preflight.py`` and the Azure pipeline.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import unicodedata
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Iterable
from urllib.parse import urlparse

try:
    from scripts import worktree_lifecycle as lifecycle_registry
except ModuleNotFoundError:  # Direct ``python scripts/delivery_preflight.py`` use.
    import worktree_lifecycle as lifecycle_registry


ROOT = Path(__file__).resolve().parents[1]
INDEX_REL = "docs/governance/CURRENT_LANES.json"
INDEX_PATH = ROOT / INDEX_REL
CLAIMS_REL = "docs/governance/lane_claims"
RECEIPTS_REL = f"{CLAIMS_REL}/receipts"
EVIDENCE_REL = f"{CLAIMS_REL}/evidence"
AZURE_ORIGIN_PATH = "/peerslate19/portfolio-site/_git/portfolio-site"

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
PACKAGE_RE = re.compile(r"^PS-[A-Z0-9]+(?:-[A-Z0-9]+)*$")
BRANCH_RE = re.compile(r"^(?:work|codex)/[a-z0-9][a-z0-9._/-]*$")
ACTIVATION_BRANCH_RE = re.compile(
    r"^work/[0-9]{4}-[0-9]{2}-[0-9]{2}-delivery-activation-[a-z0-9-]+$"
)
CONTROL_BRANCH_RE = re.compile(
    r"^work/[0-9]{4}-[0-9]{2}-[0-9]{2}-delivery-"
    r"(?:authorize|extend-surfaces|release-surfaces|transfer|owner-reassignment|pause|resume|close|supersede)-[a-z0-9-]+$"
)
OWNER_REASSIGNMENT_CONTROL_BRANCH_RE = re.compile(
    r"^work/[0-9]{4}-[0-9]{2}-[0-9]{2}-delivery-owner-reassignment-[a-z0-9-]+$"
)
EVIDENCE_ERRATA_BRANCH_RE = re.compile(
    r"^work/[0-9]{4}-[0-9]{2}-[0-9]{2}-delivery-evidence-errata-[a-z0-9-]+$"
)
REF_RE = re.compile(r"^(?:task|session|agent|role):[A-Za-z0-9._:/-]{3,180}$")
DOMAIN_PART_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
ISO_UTC_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"
)
LEGACY_UUID_RE = re.compile(
    r"(?<![0-9a-f])[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
    r"[0-9a-f]{4}-[0-9a-f]{12}(?![0-9a-f])",
    re.IGNORECASE,
)
LEGACY_CURRENT_WRITER_RE = re.compile(
    r"\b(?:task|session)\s+(" + LEGACY_UUID_RE.pattern + r")",
    re.IGNORECASE,
)

ACTIVE_STATE = "active"
STATES = {"active", "paused", "closed", "superseded"}
DELIVERY_PATHS = {"Routine", "Bounded", "Protected"}
ASSIGNMENTS = {"implementation"}
REPOSITORY_AUTHORITIES = {"through_merge", "write_only"}
REVIEW_REQUIREMENTS = {"self", "independent"}
MUTATING_INTENTS = {
    "repair-activate", "repair-merge",
    "activate", "authorize", "extend-surfaces", "write", "transfer",
    "owner-reassignment", "pause", "resume", "merge", "close", "supersede",
    "evidence-errata", "release-surfaces",
}
# evidence-errata is a control-style transition: it runs from the leased
# sparse _control singleton and its claim is read from the branch copy, but
# unlike the lifecycle transitions it must leave every claim byte-identical.
CONTROL_INTENTS = {
    "repair-activate", "repair-merge",
    "activate", "authorize", "extend-surfaces", "transfer",
    "owner-reassignment", "pause", "resume", "close", "supersede",
    "evidence-errata", "release-surfaces",
}
REPAIR_INTENTS = {"repair-activate", "repair-merge"}
REPAIR_SURFACES = frozenset({
    ".gitleaks.toml", "scripts/worktree_lifecycle.py",
    "scripts/delivery_preflight.py", "tests/test_worktree_lifecycle.py",
    "tests/test_delivery_preflight.py", "tests/test_control_custody_recovery.py",
    "tests/test_repair_admission.py", "tests/test_operational_readiness.py",
    "AGENTS.md", "START_HERE.md", "docs/AI_WORKFLOW.md",
    "docs/governance/WORKTREE_LIFECYCLE.md",
})
# PS-DELIVERY-SIMPLIFICATION-CLOSE-REPAIR-001: the delivery-control
# simplification bootstrap introduced the per-package claim model itself, so
# its independently reviewed candidate necessarily carried the two legacy
# Synthetic bootstrap records outside its own claim. Close scope validation
# tolerates exactly this one already-reviewed, already-merged historical
# tuple; the tolerated paths stay subject to every other close proof (byte
# identity, merged-path introduction, receipt and branch verification), and
# every other package, candidate, merge, and path keeps strict behavior.
HISTORICAL_BOOTSTRAP_CLOSE_TOLERATED_PATHS: dict[
    tuple[str, str, str], frozenset[str]
] = {
    (
        "PS-DELIVERY-CONTROL-SIMPLIFICATION-001",
        "ff3959815f3e4a9ca4dc5dd404a42a5e11ec462a",
        "1b6b5d4905af32edfee43c02d6e2bdb58d31898c",
    ): frozenset(
        {
            "docs/governance/lane_claims/PS-SYNTHETIC-MULTI-MEMBER-QA-001.json",
            "docs/governance/lane_claims/receipts/PS-SYNTHETIC-MULTI-MEMBER-QA-001.json",
        }
    ),
}
VOLUNTARY_HANDOFF_FIELDS = {
    "from_ref", "to_ref", "checkpoint_sha", "relinquished"
}
OWNER_REASSIGNMENT_FIELDS = {
    "type",
    "from_ref",
    "to_ref",
    "from_branch",
    "to_branch",
    "checkpoint_sha",
    "owner_authorization_ref",
}
WORKTREE_REGISTRY_REL = Path("peerslate") / "worktree_registry.json"
WORKTREE_LOCK_DIRECTORY_NAME = "worktree_registry.lock"
CI_ENVIRONMENT_KEYS = ("TF_BUILD", "CI", "GITHUB_ACTIONS", "BUILD_BUILDID")
ACTIVE_INDEX_SCHEMA = 3
SAFE_CUSTODY_INDEX_SCHEMA = 4
SAFE_CUSTODY_REGISTRY_SCHEMA = 2
SAFE_CUSTODY_CAPABILITIES = {
    "scope_release": "safe_custody_v1",
    "main_reconciliation": "safe_custody_v1",
    "registry_schema": SAFE_CUSTODY_REGISTRY_SCHEMA,
}
SCOPE_RELEASE_FIELDS = {
    "schema_version",
    "operation_id",
    "control_branch",
    "control_lease_sha256",
    "quiescence_ref",
    "prior_claim_sha256",
    "reduction_sha256",
    "checkpoint_sha",
    "prepared_from_main",
    "released_surfaces",
    "released_file_proofs",
    "prior_domains",
    "new_domains",
    "retained_responsibilities",
    "release_rationale",
    "fixed_evidence_ref",
    "registry_schema",
    "index_schema",
}


class PreflightError(RuntimeError):
    """The repository state cannot be evaluated safely."""


@dataclass(frozen=True)
class RepoFacts:
    repository: str
    branch: str
    head: str
    origin_main: str
    ahead: int
    behind: int
    clean: bool
    branch_paths: tuple[str, ...]
    main_paths: tuple[str, ...]
    worktree_paths: tuple[str, ...]
    fetched: bool
    origin_url: str


def _git_result(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-c", "core.quotepath=false", *args],
        cwd=root,
        text=True,
        encoding="utf-8",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def _git(root: Path, *args: str) -> str:
    result = _git_result(root, *args)
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip() or "git failed"
        raise PreflightError(f"git {' '.join(args)}: {detail}")
    return result.stdout.strip()


def _git_nul(root: Path, *args: str) -> list[str]:
    result = _git_result(root, *args)
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip() or "git failed"
        raise PreflightError(f"git {' '.join(args)}: {detail}")
    return [item for item in result.stdout.split("\0") if item]


def _is_normalized_work_branch(branch: object) -> bool:
    if not isinstance(branch, str) or not BRANCH_RE.fullmatch(branch):
        return False
    components = branch.split("/")
    return bool(
        len(components) >= 2
        and all(
            component not in {"", ".", ".."}
            and not component.endswith((".", ".lock"))
            and ".." not in component
            for component in components
        )
    )


def _remote_branch_tip(root: Path, branch: str) -> str | None:
    """Return one exact server-side branch tip, or confirmed absence.

    ``ls-remote`` is used instead of trusting a remote-tracking ref.  Exit 2
    with no output is Git's explicit no-match result; every other failure or
    ambiguous response is a hard error.
    """

    if branch != "main" and not _is_normalized_work_branch(branch):
        raise PreflightError(f"invalid work branch: {branch!r}")
    result = _git_result(
        root,
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
        raise PreflightError(f"could not confirm remote branch {branch!r}: {detail}")
    matches = [line.split() for line in result.stdout.splitlines() if line.strip()]
    expected_ref = f"refs/heads/{branch}"
    if len(matches) != 1 or len(matches[0]) != 2 or matches[0][1] != expected_ref:
        raise PreflightError(f"remote branch lookup was ambiguous: {branch!r}")
    sha = matches[0][0].casefold()
    if not SHA_RE.fullmatch(sha):
        raise PreflightError(f"remote branch returned an invalid commit: {branch!r}")
    return sha


def _remote_branch_tuple(root: Path, branches: Iterable[str]) -> dict[str, str]:
    """Read one exact server advertisement for a complete branch tuple."""

    normalized = list(branches)
    if any(
        branch != "main" and not _is_normalized_work_branch(branch)
        for branch in normalized
    ) or len(normalized) != len(set(normalized)):
        raise PreflightError("remote branch tuple contains invalid or duplicate names")
    result = _git_result(
        root,
        "ls-remote",
        "--heads",
        "origin",
        *(f"refs/heads/{branch}" for branch in normalized),
    )
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip() or "git ls-remote failed"
        raise PreflightError("could not confirm remote branch tuple: " + detail)
    expected_refs = {f"refs/heads/{branch}": branch for branch in normalized}
    observed: dict[str, str] = {}
    for line in result.stdout.splitlines():
        columns = line.split()
        if len(columns) != 2 or columns[1] not in expected_refs:
            raise PreflightError("remote branch tuple lookup was ambiguous")
        branch = expected_refs[columns[1]]
        sha = columns[0].casefold()
        if branch in observed or not SHA_RE.fullmatch(sha):
            raise PreflightError("remote branch tuple lookup was ambiguous")
        observed[branch] = sha
    if set(observed) != set(normalized):
        raise PreflightError("remote branch tuple is incomplete")
    return observed


def _exact_fetch_origin_branch(root: Path, branch: str) -> str | None:
    """Fetch one branch without pruning and prove it did not move mid-fetch."""

    observed_tip = _remote_branch_tip(root, branch)
    if observed_tip is None:
        return None
    _git(
        root,
        "fetch",
        "--no-prune",
        "--no-tags",
        "origin",
        f"+refs/heads/{branch}:refs/remotes/origin/{branch}",
    )
    fetched_tip = _git(root, "rev-parse", f"refs/remotes/origin/{branch}").casefold()
    confirmed_tip = _remote_branch_tip(root, branch)
    if fetched_tip != observed_tip or confirmed_tip != observed_tip:
        raise PreflightError(
            f"remote branch moved during exact fetch; retry from a stable tip: {branch!r}"
        )
    return fetched_tip


def _is_ancestor(root: Path, older: str, newer: str) -> bool:
    return _git_result(root, "merge-base", "--is-ancestor", older, newer).returncode == 0


def _git_common_dir(root: Path) -> Path:
    value = Path(_git(root, "rev-parse", "--git-common-dir"))
    return (value if value.is_absolute() else root / value).resolve()


def _canonical_local_path(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("registry worktree path must be a non-empty string")
    path = Path(value)
    if not path.is_absolute():
        raise ValueError("registry worktree path must be absolute")
    return os.path.normcase(str(path.resolve(strict=False))).casefold()


def _is_ci_environment() -> bool:
    return any(os.environ.get(key) for key in CI_ENVIRONMENT_KEYS)


def _parse_live_worktrees(root: Path) -> list[dict]:
    payload = _git(root, "worktree", "list", "--porcelain", "-z")
    records: list[dict] = []
    current: dict = {}
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
        record.setdefault("branch", None)
        record.setdefault("head", None)
        record["detached"] = bool(record.get("detached"))
        if "worktree" in record:
            record["worktree"] = str(Path(record["worktree"]).resolve(strict=False))
    return records


def _optional_local_branch_sha(root: Path, branch: str) -> str | None:
    expected_ref = f"refs/heads/{branch}"
    result = _git_result(
        root,
        "for-each-ref",
        "--format=%(objectname)%00%(objecttype)%00%(refname)",
        expected_ref,
    )
    if result.returncode:
        detail = (
            result.stderr.strip()
            or result.stdout.strip()
            or "for-each-ref failed"
        )
        raise PreflightError(f"could not inspect local source branch: {detail}")

    exact_matches: list[tuple[str, str]] = []
    for line in result.stdout.splitlines():
        parts = line.split("\0")
        if len(parts) != 3:
            raise PreflightError("local source branch proof is malformed")
        object_name, object_type, refname = parts
        if refname != expected_ref:
            if not refname.startswith(expected_ref + "/"):
                raise PreflightError("local source branch proof is ambiguous")
            continue
        exact_matches.append((object_name.casefold(), object_type))
    if not exact_matches:
        return None
    if len(exact_matches) != 1:
        raise PreflightError("local source branch proof is ambiguous")
    object_name, object_type = exact_matches[0]
    if not SHA_RE.fullmatch(object_name) or object_type != "commit":
        raise PreflightError("local source branch does not name one commit")
    return object_name


def _claim_blob_at_commit(root: Path, commit: str, package: object) -> str:
    if not isinstance(commit, str) or not SHA_RE.fullmatch(commit):
        raise PreflightError("owner-reassignment claim proof has an invalid commit")
    if not isinstance(package, str) or not PACKAGE_RE.fullmatch(package):
        raise PreflightError("owner-reassignment claim proof has an invalid package")
    path = claim_relative_path(package)
    result = _git_result(root, "ls-tree", "-z", commit, "--", path)
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip() or "claim blob missing"
        raise PreflightError(
            f"could not inspect authoritative claim at {commit}: {detail}"
        )
    rows = [row for row in result.stdout.split("\0") if row]
    if len(rows) != 1:
        raise PreflightError("authoritative claim blob proof is missing or ambiguous")
    metadata, separator, observed_path = rows[0].partition("\t")
    columns = metadata.split()
    if (
        not separator
        or observed_path != path
        or len(columns) != 3
        or columns[0] != "100644"
        or columns[1] != "blob"
        or not SHA_RE.fullmatch(columns[2].casefold())
    ):
        raise PreflightError("authoritative claim blob proof is malformed")
    blob = columns[2].casefold()
    return blob


def _owner_reassignment_continuity_errors(
    *, root: Path, claim: dict, facts: RepoFacts, preparation: dict
) -> list[str]:
    prepared_main = preparation.get("prepared_from_main")
    prepared_control = preparation.get("control_branch")
    if prepared_main == facts.origin_main and prepared_control == facts.branch:
        return []

    errors: list[str] = []
    if prepared_control == facts.branch:
        errors.append(
            "owner-reassignment continuity requires a distinct fresh control branch"
        )
    if not OWNER_REASSIGNMENT_CONTROL_BRANCH_RE.fullmatch(facts.branch):
        errors.append(
            "owner-reassignment continuity requires an exact owner-reassignment control branch"
        )
    if facts.behind:
        errors.append(
            "owner-reassignment continuity requires a control branch from current main"
        )
    if (
        not isinstance(prepared_main, str)
        or not SHA_RE.fullmatch(prepared_main)
        or prepared_main == facts.origin_main
        or not _is_ancestor(root, prepared_main, facts.origin_main)
    ):
        errors.append(
            "owner-reassignment continuity requires current main to be a strict descendant of prepared main"
        )
        return errors

    try:
        prepared_blob = _claim_blob_at_commit(root, prepared_main, claim.get("package"))
        current_blob = _claim_blob_at_commit(
            root, facts.origin_main, claim.get("package")
        )
    except PreflightError as exc:
        errors.append("owner-reassignment continuity claim proof failed: " + str(exc))
    else:
        if prepared_blob != current_blob:
            errors.append(
                "owner-reassignment continuity requires a byte-identical authoritative target claim"
            )
    return errors


def _path_is_pristine(path: Path) -> bool:
    payload = _git(
        path,
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
        "--ignored=matching",
    )
    return not payload


def _live_preparation_source_snapshot(
    root: Path, registry: dict, handoff: dict
) -> dict:
    package = str(handoff.get("package", ""))
    from_ref = str(handoff.get("from_ref", ""))
    from_branch = str(handoff.get("from_branch", ""))
    checkpoint = str(handoff.get("checkpoint_sha", ""))
    worktrees = _parse_live_worktrees(root)
    snapshots: list[dict] = []
    for entry in worktrees:
        if entry.get("branch") != from_branch:
            continue
        path = Path(str(entry.get("worktree", ""))).resolve(strict=False)
        if entry.get("detached") or entry.get("head") != checkpoint:
            raise PreflightError(
                "prepared source worktree is detached, switched, or moved"
            )
        if not _path_is_pristine(path):
            raise PreflightError("prepared source worktree is no longer pristine")
        snapshots.append(
            {"path": str(path), "branch": from_branch, "head": checkpoint}
        )
    snapshots.sort(key=lambda item: os.path.normcase(item["path"]).casefold())

    durable = [
        record
        for record in registry.get("worktrees", [])
        if isinstance(record, dict)
        and record.get("state") == "active"
        and record.get("kind") == "durable"
        and (
            str(record.get("package", "")).casefold() == package.casefold()
            or record.get("branch") == from_branch
        )
    ]
    path_keys = [
        _canonical_local_path(record.get("path")) for record in durable
    ]
    if len(durable) > 1 or len(path_keys) != len(set(path_keys)):
        raise PreflightError("prepared source durable registry custody is ambiguous")
    durable_snapshots: list[dict] = []
    for record in durable:
        if (
            record.get("package") != package
            or record.get("task_ref") != from_ref
            or record.get("branch") != from_branch
            or record.get("head") != checkpoint
        ):
            raise PreflightError("prepared source durable registry identity changed")
        path = Path(str(record.get("path"))).resolve(strict=False)
        matches = [
            entry
            for entry in worktrees
            if os.path.normcase(str(entry.get("worktree", ""))).casefold()
            == os.path.normcase(str(path)).casefold()
        ]
        if len(matches) != 1:
            raise PreflightError("prepared source durable worktree is missing or ambiguous")
        live = matches[0]
        if (
            live.get("detached")
            or live.get("branch") != from_branch
            or live.get("head") != checkpoint
            or not _path_is_pristine(path)
        ):
            raise PreflightError("prepared source durable worktree identity changed")
        durable_snapshots.append(
            {
                "path": str(path),
                "package": package,
                "task_ref": from_ref,
                "branch": from_branch,
                "head": checkpoint,
            }
        )
    return {
        "local_branch_sha": _optional_local_branch_sha(root, from_branch),
        "worktrees": snapshots,
        "durable_records": durable_snapshots,
    }


def _branch_names_at_ref_prefix(root: Path, prefix: str) -> list[str]:
    names = _git(root, "for-each-ref", "--format=%(refname)", prefix)
    result: list[str] = []
    for refname in names.splitlines():
        if not refname.startswith(prefix + "/"):
            raise PreflightError(f"ambiguous Git ref namespace entry: {refname}")
        result.append(refname[len(prefix) + 1 :])
    return result


def _branches_namespace_collide(left: str, right: str) -> bool:
    return left == right or left.startswith(right + "/") or right.startswith(left + "/")


def _owner_reassignment_namespace_errors(
    root: Path, registry: dict, claim: dict
) -> list[str]:
    handoff = claim.get("handoff")
    if not isinstance(handoff, dict) or not isinstance(handoff.get("to_branch"), str):
        return ["owner-reassignment successor namespace cannot be proved"]
    successor = handoff["to_branch"]
    collisions: list[str] = []
    for branch in _branch_names_at_ref_prefix(root, "refs/heads"):
        if _branches_namespace_collide(successor, branch):
            collisions.append(f"local head:{branch}")
    for branch in _branch_names_at_ref_prefix(root, "refs/remotes/origin"):
        if branch == "HEAD" or branch == successor:
            continue
        if _branches_namespace_collide(successor, branch):
            collisions.append(f"origin tracking ref:{branch}")
    for entry in _parse_live_worktrees(root):
        branch = entry.get("branch")
        if isinstance(branch, str) and _branches_namespace_collide(
            successor, branch
        ):
            collisions.append(f"worktree:{entry.get('worktree')}:{branch}")
    for record in registry.get("worktrees", []):
        if not isinstance(record, dict) or record.get("state") != "active":
            continue
        for field in ("branch", "source_branch"):
            branch = record.get(field)
            if isinstance(branch, str) and _branches_namespace_collide(
                successor, branch
            ):
                collisions.append(f"registry:{record.get('path')}:{field}:{branch}")
    for live_claim in load_claims_at_ref(root, "origin/main").values():
        if live_claim.get("state") not in {"active", "paused"}:
            continue
        branch = live_claim.get("branch")
        if isinstance(branch, str) and _branches_namespace_collide(
            successor, branch
        ):
            collisions.append(f"live claim:{live_claim.get('package')}:{branch}")
    return (
        [
            "owner-reassignment successor namespace changed after preparation: "
            + repr(sorted(set(collisions)))
        ]
        if collisions
        else []
    )


def _owner_reassignment_preparation_errors(
    *,
    root: Path,
    registry: dict,
    claim: dict,
    facts: RepoFacts,
) -> list[str]:
    errors: list[str] = []
    handoff = claim.get("handoff")
    if not isinstance(handoff, dict):
        return ["owner reassignment requires preparation matching its handoff"]
    expected = {
        "package": claim.get("package"),
        "owner_authorization_ref": handoff.get("owner_authorization_ref"),
        "from_ref": handoff.get("from_ref"),
        "to_ref": handoff.get("to_ref"),
        "from_branch": handoff.get("from_branch"),
        "to_branch": handoff.get("to_branch"),
        "checkpoint_sha": handoff.get("checkpoint_sha"),
    }
    preparations = registry.get("owner_reassignment_preparations")
    try:
        lifecycle_registry.validate_owner_reassignment_registry(registry)
    except lifecycle_registry.Refusal as exc:
        return ["registry owner-reassignment preparation history is invalid: " + str(exc)]
    assert isinstance(preparations, list)
    package_completed = [
        item
        for item in preparations
        if isinstance(item, dict)
        and str(item.get("package", "")).casefold()
        == str(claim.get("package", "")).casefold()
        and item.get("status") == "completed"
    ]
    matches = [
        item
        for item in package_completed
        if all(item.get(field) == value for field, value in expected.items())
    ]
    tuple_matches = [
        item
        for item in preparations
        if isinstance(item, dict)
        and str(item.get("package", "")).casefold()
        == str(expected["package"]).casefold()
        and all(
            item.get(field) == value
            for field, value in expected.items()
            if field != "package"
        )
    ]
    if (
        len(package_completed) != 1
        or len(matches) != 1
        or len(tuple_matches) != 1
    ):
        return [
            *errors,
            "owner reassignment requires one exact, unconsumed completed preparation tuple",
        ]
    preparation = matches[0]
    errors.extend(
        _owner_reassignment_continuity_errors(
            root=root,
            claim=claim,
            facts=facts,
            preparation=preparation,
        )
    )
    source_handoff = dict(handoff)
    source_handoff["package"] = claim.get("package")
    try:
        current_snapshot = _live_preparation_source_snapshot(
            root, registry, source_handoff
        )
    except (PreflightError, ValueError) as exc:
        errors.append("owner-reassignment preparation source proof failed: " + str(exc))
    else:
        if preparation.get("source_snapshot") != current_snapshot:
            errors.append("owner-reassignment preparation source snapshot no longer matches")
    try:
        errors.extend(_owner_reassignment_namespace_errors(root, registry, claim))
    except (PreflightError, ValueError) as exc:
        errors.append("owner-reassignment successor namespace proof failed: " + str(exc))
    return errors


def evaluate_local_worktree_context(
    *,
    root: Path,
    args: argparse.Namespace,
    claim: dict,
    facts: RepoFacts,
) -> tuple[dict, list[str], list[str]]:
    """Enforce the initialized machine-local registry for this workspace only.

    The registry is operational inventory, not repository authority. Except
    for owner reassignment's mandatory local preparation proof, CI and a
    machine that has not initialized it remain valid. Once initialized, a new
    unregistered mutating workspace fails without making unrelated historical
    worktrees a global blocker.
    """

    context = {
        "enforced": False,
        "registry": "not_checked",
        "current_kind": None,
        "owner_reassignment_preparation_valid": False,
    }
    errors: list[str] = []
    warnings: list[str] = []
    caller_context = getattr(args, "caller_context", "")
    try:
        context_id = lifecycle_registry._caller_context_identifier(caller_context)
    except lifecycle_registry.Refusal as exc:
        errors.append("caller identity: " + str(exc))
        return context, errors, warnings
    if not context_id and lifecycle_registry._caller_identity_supplied(
        caller_context
    ):
        try:
            lifecycle_registry.resolve_caller_ref(
                task_ref=getattr(args, "task_ref", "") or None
            )
        except lifecycle_registry.Refusal as exc:
            errors.append("caller identity: " + str(exc))
            return context, errors, warnings
    if args.intent not in MUTATING_INTENTS:
        if context_id:
            common_dir = _git_common_dir(root)
            registry_path = common_dir / WORKTREE_REGISTRY_REL
            context["path"] = str(registry_path)
            if not registry_path.exists():
                context["registry"] = "not_initialized"
                errors.append("caller context requires the initialized repository registry")
                return context, errors, warnings
            try:
                registry = _read_json(registry_path)
                recorded_common = _canonical_local_path(
                    registry.get("repository_common_dir")
                )
                actual_common = _canonical_local_path(str(common_dir))
                if recorded_common != actual_common:
                    raise ValueError(
                        "machine-local worktree registry belongs to a different Git common directory"
                    )
                lifecycle_registry.resolve_caller_ref(
                    registry=registry,
                    repository_common_dir=common_dir,
                    caller_context=context_id,
                    task_ref=getattr(args, "task_ref", "") or None,
                    package=str(claim.get("package", "")),
                )
            except (PreflightError, ValueError, lifecycle_registry.Refusal) as exc:
                context["registry"] = "invalid"
                errors.append("caller identity: " + str(exc))
                return context, errors, warnings
            context.update(enforced=True, registry="initialized")
        return context, errors, warnings
    if _is_ci_environment() and not context_id:
        context["registry"] = "ci_skipped"
        if args.intent == "owner-reassignment":
            errors.append(
                "owner reassignment cannot bypass local preparation proof in CI"
            )
        else:
            warnings.append("machine-local worktree registry enforcement is skipped in CI")
        return context, errors, warnings

    common_dir = _git_common_dir(root)
    registry_path = common_dir / WORKTREE_REGISTRY_REL
    lock_path = registry_path.parent / WORKTREE_LOCK_DIRECTORY_NAME
    context["path"] = str(registry_path)
    if not registry_path.is_file():
        context["registry"] = "not_initialized"
        if context_id:
            errors.append(
                "caller context requires the initialized repository registry"
            )
            return context, errors, warnings
        message = (
            "machine-local worktree registry is not initialized; "
            "run worktree_lifecycle.py init on this machine"
        )
        if args.intent == "owner-reassignment":
            errors.append("owner reassignment requires an initialized registry")
        else:
            warnings.append(message)
        return context, errors, warnings
    if args.intent == "owner-reassignment" and os.path.lexists(lock_path):
        context["registry"] = "locked"
        errors.append("owner reassignment refuses an active registry lock")
        return context, errors, warnings

    try:
        registry = _read_json(registry_path)
    except PreflightError as exc:
        context["registry"] = "invalid"
        errors.append(str(exc))
        return context, errors, warnings
    if args.intent == "owner-reassignment":
        # Kept private and removed by the terminal owner-reassignment boundary.
        # It binds the earlier source/preparation proof to the later claim and
        # remote proof without exposing machine-local registry data in output.
        context["_owner_reassignment_registry_snapshot"] = registry
    registry_schema = registry.get("schema_version")
    if (
        registry_schema not in {
            lifecycle_registry.SCHEMA_VERSION,
            lifecycle_registry.SAFE_CUSTODY_SCHEMA_VERSION,
        }
        or not registry.get("initialized_at")
    ):
        context["registry"] = "invalid"
        errors.append("machine-local worktree registry has an unsupported schema")
        return context, errors, warnings
    try:
        if registry_schema == lifecycle_registry.SAFE_CUSTODY_SCHEMA_VERSION:
            lifecycle_registry.validate_owner_reassignment_registry(registry)
            lifecycle_registry.validate_safe_custody_registry(registry)
    except lifecycle_registry.Refusal as exc:
        context["registry"] = "invalid"
        errors.append("machine-local worktree registry is invalid: " + str(exc))
        return context, errors, warnings
    context["schema_version"] = registry_schema
    if registry_schema == lifecycle_registry.SAFE_CUSTODY_SCHEMA_VERSION:
        context["_safe_custody_registry_snapshot"] = registry
    if args.intent == "owner-reassignment" and (
        "pending" not in registry or registry.get("pending") is not None
    ):
        context["registry"] = "pending"
        errors.append("owner reassignment refuses pending registry ambiguity")
        return context, errors, warnings
    try:
        recorded_common = _canonical_local_path(registry.get("repository_common_dir"))
        actual_common = _canonical_local_path(str(common_dir))
    except ValueError as exc:
        context["registry"] = "invalid"
        errors.append(str(exc))
        return context, errors, warnings
    if recorded_common != actual_common:
        context["registry"] = "wrong_repository"
        errors.append("machine-local worktree registry belongs to a different Git common directory")
        return context, errors, warnings

    records = registry.get("worktrees")
    if not isinstance(records, list):
        context["registry"] = "invalid"
        errors.append("machine-local worktree registry worktrees must be a list")
        return context, errors, warnings
    try:
        current_path = _canonical_local_path(facts.repository)
    except ValueError as exc:
        errors.append(str(exc))
        return context, errors, warnings

    package = str(claim.get("package", ""))
    if registry_schema == lifecycle_registry.SAFE_CUSTODY_SCHEMA_VERSION:
        block = lifecycle_registry.safe_custody_block_for_package(registry, package)
        if block is not None:
            context["safe_custody_block"] = block
            permitted = (
                args.intent == "release-surfaces"
                and block.get("kind") == "scope_release"
                and isinstance(claim.get("scope_release"), dict)
                and claim["scope_release"].get("operation_id")
                == block.get("operation_id")
            )
            if not permitted:
                errors.append(
                    "package mutation is blocked by safe-custody "
                    f"{block.get('kind')} operation {block.get('operation_id')}"
                )
    try:
        if registry.get(
            "control_custody_transitions"
        ) or lifecycle_registry._caller_identity_supplied(caller_context):
            lifecycle_registry.resolve_caller_ref(
                registry=registry,
                repository_common_dir=common_dir,
                caller_context=context_id,
                task_ref=getattr(args, "task_ref", "") or None,
                package=package,
            )
    except lifecycle_registry.Refusal as exc:
        errors.append("caller identity: " + str(exc))

    matches: list[dict] = []
    grandfathered_other = 0
    seen_paths: set[str] = set()
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            errors.append(f"machine-local worktree registry record {index} must be an object")
            continue
        try:
            record_path = _canonical_local_path(record.get("path"))
        except ValueError as exc:
            errors.append(f"machine-local worktree registry record {index}: {exc}")
            continue
        if record_path in seen_paths:
            errors.append(f"machine-local worktree registry repeats path {record.get('path')}")
        seen_paths.add(record_path)
        if record_path == current_path:
            matches.append(record)
        elif (
            record.get("kind") == "grandfathered_observation"
            and record.get("state") == "active"
        ):
            grandfathered_other += 1
    if grandfathered_other:
        warnings.append(
            f"{grandfathered_other} unrelated grandfathered worktree(s) remain observational only"
        )
    if len(matches) != 1:
        context["registry"] = "unregistered" if not matches else "ambiguous"
        errors.append(
            "current mutating workspace is not one exact active registry record; "
            "do not create an ad hoc worktree"
        )
        return context, errors, warnings

    record = matches[0]
    if record.get("kind") == "control_singleton":
        try:
            if args.intent in REPAIR_INTENTS and not registry.get(
                "control_custody_transitions"
            ):
                lifecycle_registry.resolve_caller_ref(
                    registry=registry,
                    repository_common_dir=common_dir,
                    caller_context=context_id,
                    task_ref=getattr(args, "task_ref", "") or None,
                    package=package,
                )
            lifecycle_registry.require_control_custody_fence(
                registry, record, task_ref=getattr(args, "task_ref", ""),
                lease_token=getattr(args, "lease_token", ""),
            )
        except lifecycle_registry.Refusal as exc:
            errors.append("control custody fence: " + str(exc))
    context.update(
        {
            "enforced": True,
            "registry": "initialized",
            "current_kind": record.get("kind"),
            "current_path": record.get("path"),
        }
    )
    if record.get("state") != "active":
        errors.append("current mutating workspace registry record is not active")
        return context, errors, warnings
    if args.intent == "owner-reassignment":
        control_records = [
            item
            for item in records
            if isinstance(item, dict)
            and item.get("kind") == "control_singleton"
        ]
        try:
            managed_root_value = registry.get("managed_root")
            _canonical_local_path(managed_root_value)
            assert isinstance(managed_root_value, str)
            expected_control_path = _canonical_local_path(
                str(Path(managed_root_value) / "_control")
            )
        except ValueError as exc:
            errors.append(str(exc))
        else:
            if (
                len(control_records) != 1
                or control_records[0] is not record
                or control_records[0].get("state") != "active"
                or current_path != expected_control_path
            ):
                errors.append(
                    "owner reassignment requires one exact deterministic active "
                    "control singleton"
                )
    task_ref = getattr(args, "task_ref", "")
    if not task_ref:
        errors.append("initialized worktree registry requires --task-ref for mutating intents")
        return context, errors, warnings
    if record.get("branch") != facts.branch:
        errors.append("current worktree branch does not match its registry record")

    if args.intent in {"write", "merge"}:
        if record.get("kind") != "durable":
            errors.append("write and merge require the package durable worktree")
        if str(record.get("package", "")).casefold() != package.casefold():
            errors.append("durable worktree registry package does not match the claim")
        if record.get("task_ref") != task_ref or task_ref != claim.get("writer_ref"):
            errors.append("durable worktree task context must equal the claim writer_ref")
        if record.get("branch") != claim.get("branch"):
            errors.append("durable worktree branch does not match the claimed implementation branch")
    elif args.intent in CONTROL_INTENTS:
        if record.get("kind") != "control_singleton":
            errors.append("control transitions require the reusable sparse control singleton")
        lease = record.get("lease")
        if args.intent == "owner-reassignment":
            try:
                lifecycle_registry.validate_owner_reassignment_control_lease(
                    lease, task_ref=task_ref, package=package
                )
            except lifecycle_registry.Refusal as exc:
                errors.append("owner-reassignment control lease is invalid: " + str(exc))
        elif not isinstance(lease, dict):
            errors.append("control singleton requires an active lease")
        else:
            if lease.get("purpose") != "control":
                errors.append("control singleton lease purpose must be control")
            if lease.get("task_ref") != task_ref:
                errors.append("control singleton lease belongs to another task")
            if str(lease.get("package", "")).casefold() != package.casefold():
                errors.append("control singleton lease package does not match the claim")
    if args.intent == "owner-reassignment":
        preparation_errors = _owner_reassignment_preparation_errors(
            root=root,
            registry=registry,
            claim=claim,
            facts=facts,
        )
        errors.extend(preparation_errors)
        registry_after: dict | None = None
        try:
            registry_after = _read_json(registry_path)
        except PreflightError as exc:
            errors.append(str(exc))
        else:
            if registry_after != registry:
                errors.append("owner-reassignment registry changed during preparation proof")
        if os.path.lexists(lock_path):
            errors.append("owner-reassignment registry lock appeared during proof")
        if (
            not preparation_errors
            and registry_after is not None
            and registry_after == registry
        ):
            final_preparation_errors = _owner_reassignment_preparation_errors(
                root=root,
                registry=registry_after,
                claim=claim,
                facts=facts,
            )
            errors.extend(
                "owner-reassignment final preparation proof: " + item
                for item in final_preparation_errors
            )
        final_registry: dict | None = None
        final_lock_acquired = False
        try:
            os.mkdir(lock_path)
            final_lock_acquired = True
        except FileExistsError:
            errors.append(
                "owner-reassignment registry lock appeared during final live proof"
            )
        except OSError as exc:
            errors.append(
                "owner-reassignment final registry lock could not be acquired: "
                + str(exc)
            )
        if final_lock_acquired:
            try:
                try:
                    final_registry = _read_json(registry_path)
                except PreflightError as exc:
                    errors.append(
                        "owner-reassignment final registry snapshot failed: "
                        + str(exc)
                    )
                if final_registry is not None and final_registry != registry:
                    errors.append(
                        "owner-reassignment registry changed during final live proof"
                    )
                if final_registry is not None and (
                    "pending" not in final_registry
                    or final_registry.get("pending") is not None
                ):
                    errors.append(
                        "owner-reassignment final registry snapshot has pending ambiguity"
                    )
                final_records = (
                    final_registry.get("worktrees")
                    if final_registry is not None
                    else None
                )
                final_matches: list[dict] = []
                final_controls: list[dict] = []
                if isinstance(final_records, list):
                    for final_record in final_records:
                        if not isinstance(final_record, dict):
                            continue
                        try:
                            final_record_path = _canonical_local_path(
                                final_record.get("path")
                            )
                        except ValueError:
                            continue
                        if final_record_path == current_path:
                            final_matches.append(final_record)
                        if final_record.get("kind") == "control_singleton":
                            final_controls.append(final_record)
                final_lease = (
                    final_matches[0].get("lease")
                    if len(final_matches) == 1
                    else None
                )
                final_lease_valid = False
                try:
                    lifecycle_registry.validate_owner_reassignment_control_lease(
                        final_lease, task_ref=task_ref, package=package
                    )
                    final_lease_valid = True
                except lifecycle_registry.Refusal as exc:
                    errors.append(
                        "owner-reassignment final control lease is invalid: "
                        + str(exc)
                    )
                if (
                    len(final_matches) != 1
                    or len(final_controls) != 1
                    or final_controls[0] != final_matches[0]
                    or final_matches[0].get("state") != "active"
                    or final_matches[0] != record
                    or not final_lease_valid
                ):
                    errors.append(
                        "owner-reassignment final registry snapshot lost its exact "
                        "active leased control singleton"
                    )
                context["owner_reassignment_preparation_valid"] = not errors
            finally:
                try:
                    os.rmdir(lock_path)
                except OSError as exc:
                    errors.append(
                        "owner-reassignment final registry lock could not be released: "
                        + str(exc)
                    )
                    context["owner_reassignment_preparation_valid"] = False
        else:
            context["owner_reassignment_preparation_valid"] = False
    return context, errors, warnings


def _final_owner_reassignment_boundary_errors(
    *,
    root: Path,
    args: argparse.Namespace,
    claim: dict,
    facts: RepoFacts,
    authority_claims: dict[str, dict],
    registry_context: dict,
) -> list[str]:
    """Reprove the complete owner transition under the lifecycle mutex."""

    errors: list[str] = []
    expected_registry = registry_context.pop(
        "_owner_reassignment_registry_snapshot", None
    )
    if not isinstance(expected_registry, dict):
        registry_context["owner_reassignment_preparation_valid"] = False
        return ["owner-reassignment terminal registry snapshot is unavailable"]
    registry_path = Path(str(registry_context.get("path", "")))
    lock_path = registry_path.parent / WORKTREE_LOCK_DIRECTORY_NAME
    acquired = False
    try:
        try:
            os.mkdir(lock_path)
            acquired = True
        except FileExistsError:
            return ["owner-reassignment registry lock appeared before terminal proof"]
        except OSError as exc:
            return [
                "owner-reassignment terminal registry lock could not be acquired: "
                + str(exc)
            ]

        try:
            locked_registry = _read_json(registry_path)
        except PreflightError as exc:
            return ["owner-reassignment terminal registry read failed: " + str(exc)]
        if locked_registry != expected_registry:
            errors.append(
                "owner-reassignment registry changed before terminal owner proof"
            )
        try:
            lifecycle_registry.validate_owner_reassignment_registry(locked_registry)
        except lifecycle_registry.Refusal as exc:
            errors.append(
                "owner-reassignment terminal registry schema is invalid: " + str(exc)
            )
        if locked_registry.get("pending") is not None:
            errors.append("owner-reassignment terminal registry has pending ambiguity")

        records = locked_registry.get("worktrees")
        controls = (
            [
                record
                for record in records
                if isinstance(record, dict)
                and record.get("kind") == "control_singleton"
            ]
            if isinstance(records, list)
            else []
        )
        current_path = _canonical_local_path(facts.repository)
        matching_controls: list[dict] = []
        for control in controls:
            try:
                control_path = _canonical_local_path(control.get("path"))
            except ValueError:
                continue
            if control_path == current_path:
                matching_controls.append(control)
        lease = matching_controls[0].get("lease") if len(matching_controls) == 1 else None
        terminal_lease_valid = False
        try:
            lifecycle_registry.validate_owner_reassignment_control_lease(
                lease,
                task_ref=args.task_ref,
                package=claim.get("package"),
            )
            terminal_lease_valid = True
        except lifecycle_registry.Refusal as exc:
            errors.append(
                "owner-reassignment terminal control lease is invalid: " + str(exc)
            )
        if (
            len(controls) != 1
            or len(matching_controls) != 1
            or matching_controls[0].get("state") != "active"
            or matching_controls[0].get("branch") != facts.branch
            or not terminal_lease_valid
        ):
            errors.append(
                "owner-reassignment terminal registry lost exact leased control custody"
            )

        handoff = claim.get("handoff")
        if not isinstance(handoff, dict):
            errors.append("owner-reassignment terminal handoff is invalid")
        else:
            checkpoint = handoff.get("checkpoint_sha")
            from_branch = handoff.get("from_branch")
            to_branch = handoff.get("to_branch")
            try:
                main_tip = _exact_fetch_origin_branch(root, "main")
                old_tip = _exact_fetch_origin_branch(root, str(from_branch))
                successor_tip = _exact_fetch_origin_branch(root, str(to_branch))
            except PreflightError as exc:
                errors.append(
                    "owner-reassignment terminal remote proof failed: " + str(exc)
                )
            else:
                if main_tip != facts.origin_main:
                    errors.append(
                        "origin/main moved before owner-reassignment terminal proof"
                    )
                if old_tip != checkpoint or successor_tip != checkpoint:
                    errors.append(
                        "owner-reassignment terminal branch tuple changed"
                    )
                final_authority_claims = load_claims_at_ref(root, "origin/main")
                if final_authority_claims != authority_claims:
                    errors.append(
                        "authoritative claims changed during owner-reassignment proof"
                    )
                final_branch_claim = load_claims(root).get(
                    str(claim.get("package", "")).casefold()
                )
                if final_branch_claim != claim:
                    errors.append(
                        "owner-reassignment branch claim changed during terminal proof"
                    )

        errors.extend(
            "owner-reassignment terminal preparation proof: " + item
            for item in _owner_reassignment_preparation_errors(
                root=root,
                registry=locked_registry,
                claim=claim,
                facts=facts,
            )
        )

        # The final reads occur after the source/pristine/namespace proof while
        # the lifecycle mutex is still held. Claims are read first, then one
        # server advertisement binds the complete remote tuple without a
        # sequential main/source/successor race.
        final_authority_claims = load_claims_at_ref(root, "origin/main")
        if final_authority_claims != authority_claims:
            errors.append(
                "authoritative claims changed at terminal boundary"
            )
        final_branch_claim = load_claims(root).get(
            str(claim.get("package", "")).casefold()
        )
        if final_branch_claim != claim:
            errors.append(
                "owner-reassignment branch claim changed at terminal boundary"
            )
        try:
            from_branch = str(
                claim.get("handoff", {}).get("from_branch", "")
            )
            to_branch = str(claim.get("handoff", {}).get("to_branch", ""))
            final_remote_tuple = _remote_branch_tuple(
                root, ("main", from_branch, to_branch)
            )
        except PreflightError as exc:
            errors.append(
                "owner-reassignment final coherent remote proof failed: " + str(exc)
            )
        else:
            checkpoint = claim.get("handoff", {}).get("checkpoint_sha")
            if final_remote_tuple != {
                "main": facts.origin_main,
                from_branch: checkpoint,
                to_branch: checkpoint,
            }:
                errors.append(
                    "owner-reassignment remote or claim state changed at terminal boundary"
                )
        try:
            registry_after = _read_json(registry_path)
        except PreflightError as exc:
            errors.append(
                "owner-reassignment terminal registry reread failed: " + str(exc)
            )
        else:
            if registry_after != locked_registry:
                errors.append(
                    "owner-reassignment registry changed during terminal owner proof"
                )
            try:
                lifecycle_registry.validate_owner_reassignment_registry(registry_after)
            except lifecycle_registry.Refusal as exc:
                errors.append(
                    "owner-reassignment final registry schema is invalid: " + str(exc)
                )
    finally:
        if acquired:
            try:
                os.rmdir(lock_path)
            except OSError as exc:
                errors.append(
                    "owner-reassignment terminal registry lock could not be released: "
                    + str(exc)
                )
        registry_context["owner_reassignment_preparation_valid"] = (
            registry_context.get("owner_reassignment_preparation_valid") is True
            and not errors
        )
    return errors


def normalize_path(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("path must be a string")
    raw = value.strip()
    if raw != value or not raw or "\\" in raw or raw.startswith("/") or re.match(r"^[A-Za-z]:", raw):
        raise ValueError(f"path must be repository-relative: {value!r}")
    parts = PurePosixPath(raw).parts
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise ValueError(f"path is not normalized: {value!r}")
    normalized_parts = [unicodedata.normalize("NFC", part) for part in parts]
    reserved = {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)), *(f"lpt{i}" for i in range(1, 10))}
    for part in normalized_parts:
        if part.casefold() == ".git" or part.endswith((".", " ")):
            raise ValueError(f"unsafe path component: {part!r}")
        if part.split(".", 1)[0].casefold() in reserved:
            raise ValueError(f"Windows-reserved path component: {part!r}")
        if any(ord(char) < 32 or char in '<>:"|?*[]' for char in part):
            raise ValueError(f"unsafe path character in: {part!r}")
    normalized = "/".join(normalized_parts)
    if normalized != raw:
        raise ValueError(f"path is not normalized: {value!r}")
    return normalized


def paths_overlap(left: str, right: str) -> bool:
    a = normalize_path(left).casefold()
    b = normalize_path(right).casefold()
    return a == b or a.startswith(b + "/") or b.startswith(a + "/")


def extension_surface_is_broad(root: Path, ref: str, path: str) -> bool:
    """Return whether an appended surface is a directory-like reservation.

    Surface extension is for a newly discovered exact tracked file, not a late
    claim over a directory or an unproved future path. The authoritative ref
    must therefore identify the addition as a Git blob.
    """

    try:
        normalized = normalize_path(path)
    except ValueError:
        return True
    result = _git_result(root, "cat-file", "-t", f"{ref}:{normalized}")
    return result.returncode != 0 or result.stdout.strip() != "blob"


def path_is_claimed(path: str, surfaces: Iterable[str]) -> bool:
    normalized = normalize_path(path).casefold()
    return any(
        normalized == normalize_path(surface).casefold()
        or normalized.startswith(normalize_path(surface).casefold() + "/")
        for surface in surfaces
    )


def normalize_domain(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("domain must be a string")
    normalized = value.strip().casefold()
    parts = normalized.split(":")
    if not parts or any(not DOMAIN_PART_RE.fullmatch(part) for part in parts):
        raise ValueError(f"invalid hierarchical domain: {value!r}")
    return ":".join(parts)


def domains_overlap(left: str, right: str) -> bool:
    a = normalize_domain(left)
    b = normalize_domain(right)
    return a == b or a.startswith(b + ":") or b.startswith(a + ":")


def colliding_paths(left: Iterable[str], right: Iterable[str]) -> list[tuple[str, str]]:
    return sorted(
        (a, b)
        for a in left
        for b in right
        if paths_overlap(a, b)
    )


def colliding_domains(
    left: Iterable[str], right: Iterable[str]
) -> list[tuple[str, str]]:
    return sorted(
        (a, b)
        for a in left
        for b in right
        if domains_overlap(a, b)
    )


def colliding_movement_paths(
    branch_paths: Iterable[str],
    main_paths: Iterable[str],
    claimed_surfaces: Iterable[str],
) -> list[tuple[str, str]]:
    """Return branch/main pairs that touch the same claimed surface.

    Two sibling files under a directory claim are intentionally a collision:
    that directory is the declared unit of ownership. Disjoint exact-file
    claims remain independently movable.
    """

    surfaces = tuple(claimed_surfaces)
    return sorted(
        (branch_path, main_path)
        for branch_path in branch_paths
        for main_path in main_paths
        if paths_overlap(branch_path, main_path)
        or any(
            path_is_claimed(branch_path, (surface,))
            and path_is_claimed(main_path, (surface,))
            for surface in surfaces
        )
    )


def _read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PreflightError(f"cannot read valid JSON from {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise PreflightError(f"{path} must contain a JSON object")
    return value


def _json_at_ref(root: Path, ref: str, relative_path: str) -> dict:
    raw = _git(root, "show", f"{ref}:{relative_path}")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise PreflightError(
            f"{ref}:{relative_path} is not valid JSON: {exc}"
        ) from exc
    if not isinstance(value, dict):
        raise PreflightError(f"{ref}:{relative_path} must contain an object")
    return value


def load_index(root: Path = ROOT) -> dict:
    return _read_json(root / INDEX_REL)


def load_index_at_ref(root: Path, ref: str) -> dict:
    return _json_at_ref(root, ref, INDEX_REL)


def claim_relative_path(package: str) -> str:
    return f"{CLAIMS_REL}/{package}.json"


def receipt_relative_path(package: str) -> str:
    return f"{RECEIPTS_REL}/{package}.json"


def evidence_relative_path(package: str) -> str:
    return f"{EVIDENCE_REL}/{package}.md"


def _tracked_regular_blob(root: Path, ref: str, path: str) -> bool:
    """True when ``path`` at ``ref`` is exactly one ordinary tracked blob.

    Symlinks (120000), gitlinks/submodules (160000), executables (100755),
    and missing or ambiguous entries all return False: an evidence errata
    may amend one plain committed file and nothing else.
    """
    result = _git_result(root, "ls-tree", "-z", ref, "--", path)
    if result.returncode:
        return False
    entries = [item for item in result.stdout.split("\0") if item]
    if len(entries) != 1:
        return False
    meta = entries[0].split("\t", 1)[0].split(" ")
    return len(meta) >= 2 and meta[0] == "100644" and meta[1] == "blob"


def control_relative_paths(package: str) -> tuple[str, str, str]:
    return (
        claim_relative_path(package),
        receipt_relative_path(package),
        evidence_relative_path(package),
    )


def is_valid_utc_timestamp(value: object) -> bool:
    if not isinstance(value, str) or not ISO_UTC_RE.fullmatch(value):
        return False
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return False
    return True


def legacy_repository_authority(origin_index: dict, lane: dict) -> str:
    """Conservatively translate one pinned schema-v2 lane's merge boundary."""
    outcome = str(lane.get("outcome", ""))
    exclusions = lane.get("exclusions")
    boundary_text = ". ".join(
        [outcome]
        + ([str(item) for item in exclusions] if isinstance(exclusions, list) else [])
    )
    if re.search(
        r"\b(?:stop before|no)\b[^.]{0,500}\bmerge\b",
        boundary_text,
        re.IGNORECASE,
    ):
        return "write_only"
    operating_mode = origin_index.get("operating_mode")
    merge_allowed = (
        operating_mode.get("merge_allowed_for", [])
        if isinstance(operating_mode, dict)
        else []
    )
    if lane.get("package") in merge_allowed:
        return "through_merge"
    if re.search(r"\bmerge (?:the )?accepted\b", outcome, re.IGNORECASE):
        return "through_merge"
    return "write_only"


def load_claims(root: Path = ROOT) -> dict[str, dict]:
    directory = root / CLAIMS_REL
    if not directory.is_dir():
        raise PreflightError(f"claim directory is missing: {directory}")
    claims: dict[str, dict] = {}
    for path in sorted(directory.glob("PS-*.json")):
        claim = _read_json(path)
        package = claim.get("package")
        key = package.casefold() if isinstance(package, str) else path.stem.casefold()
        if key in claims:
            raise PreflightError(f"duplicate package claim: {package or path.stem}")
        claim["_relative_path"] = path.relative_to(root).as_posix()
        claims[key] = claim
    return claims


def load_claims_at_ref(root: Path, ref: str) -> dict[str, dict]:
    paths = _git(root, "ls-tree", "-r", "--name-only", ref, CLAIMS_REL).splitlines()
    claims: dict[str, dict] = {}
    for relative in sorted(paths):
        pure = PurePosixPath(relative)
        if pure.parent.as_posix() != CLAIMS_REL or not pure.name.startswith("PS-"):
            continue
        claim = _json_at_ref(root, ref, relative)
        package = claim.get("package")
        key = package.casefold() if isinstance(package, str) else pure.stem.casefold()
        if key in claims:
            raise PreflightError(f"duplicate package claim at {ref}: {package or pure.stem}")
        claim["_relative_path"] = relative
        claims[key] = claim
    return claims


def load_receipt(package: str, root: Path = ROOT) -> dict | None:
    path = root / receipt_relative_path(package)
    return _read_json(path) if path.is_file() else None


def load_receipt_at_ref(root: Path, ref: str, package: str) -> dict | None:
    relative = receipt_relative_path(package)
    result = _git_result(root, "cat-file", "-e", f"{ref}:{relative}")
    return _json_at_ref(root, ref, relative) if result.returncode == 0 else None


def validate_index(index: dict) -> list[str]:
    errors: list[str] = []
    schema_version = index.get("schema_version")
    if schema_version not in {ACTIVE_INDEX_SCHEMA, SAFE_CUSTODY_INDEX_SCHEMA}:
        errors.append(
            "CURRENT_LANES.json schema_version must be a supported version "
            f"({ACTIVE_INDEX_SCHEMA} or {SAFE_CUSTODY_INDEX_SCHEMA})"
        )
    if index.get("model") != "generic_package_claims_v1":
        errors.append("CURRENT_LANES.json model must be generic_package_claims_v1")
    if index.get("claims_path") != CLAIMS_REL:
        errors.append(f"claims_path must be {CLAIMS_REL}")
    rules = index.get("rules")
    expected_rules = {
        "writer_capacity": "unbounded_while_disjoint",
        "reviewers_consume_writer_claim": False,
        "assigned_repository_authority": "through_merge_unless_explicitly_write_only",
        "production_operations": "manual_exact_main_sha_plus_owner_reference",
    }
    if rules != expected_rules:
        errors.append("CURRENT_LANES.json rules do not match the generic model")
    capabilities = index.get("capabilities")
    if schema_version == ACTIVE_INDEX_SCHEMA:
        if capabilities is not None:
            errors.append(
                "CURRENT_LANES.json schema 3 must not advertise safe-custody capabilities"
            )
    elif capabilities != SAFE_CUSTODY_CAPABILITIES:
        errors.append(
            "CURRENT_LANES.json schema 4 capabilities do not match safe_custody_v1"
        )
    expected_fields = {
        "schema_version", "updated_at", "model", "claims_path", "rules", "legacy_snapshot"
    }
    if schema_version == SAFE_CUSTODY_INDEX_SCHEMA:
        expected_fields.add("capabilities")
    unknown = sorted(set(index) - expected_fields)
    missing = sorted(expected_fields - set(index))
    if schema_version in {ACTIVE_INDEX_SCHEMA, SAFE_CUSTODY_INDEX_SCHEMA} and (
        unknown or missing
    ):
        errors.append(
            "CURRENT_LANES.json has an unsupported field set"
            + (f"; missing={missing}" if missing else "")
            + (f"; unknown={unknown}" if unknown else "")
        )
    legacy = index.get("legacy_snapshot")
    if not isinstance(legacy, dict):
        errors.append("legacy_snapshot must be an object")
    else:
        if not SHA_RE.fullmatch(str(legacy.get("commit", ""))):
            errors.append("legacy_snapshot.commit must be a full SHA")
        if legacy.get("path") != INDEX_REL:
            errors.append(f"legacy_snapshot.path must be {INDEX_REL}")
        if not re.fullmatch(r"^[0-9a-f]{40}$", str(legacy.get("blob", ""))):
            errors.append("legacy_snapshot.blob must be a full Git blob id")
    return errors


def canonical_claim_sha256(claim: dict, *, omit_scope_release: bool = False) -> str:
    """Return the stable digest used by machine-local custody proofs."""

    payload = {
        key: value
        for key, value in claim.items()
        if key != "_relative_path" and not (omit_scope_release and key == "scope_release")
    }
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()


def _domain_is_equal_or_descendant(candidate: str, ancestor: str) -> bool:
    return candidate == ancestor or candidate.startswith(ancestor + ":")


def _domain_coverage_is_subset(candidate: list, ancestor: list) -> bool:
    """Compare the authority covered by domain unions, independent of order."""

    if not all(isinstance(domain, str) for domain in [*candidate, *ancestor]):
        return False
    return all(
        any(_domain_is_equal_or_descendant(domain, old) for old in ancestor)
        for domain in candidate
    )


def validate_scope_release_proof(proof: object) -> list[str]:
    """Validate the strict, runtime-inert proof carried by a reduced claim."""

    if proof is None:
        return []
    if not isinstance(proof, dict):
        return ["claim scope_release must be null or an object"]
    errors: list[str] = []
    if set(proof) != SCOPE_RELEASE_FIELDS:
        errors.append(
            "scope_release must use the exact safe_custody_v1 field set"
        )
    if proof.get("schema_version") != 1:
        errors.append("scope_release schema_version must be 1")
    if proof.get("registry_schema") != SAFE_CUSTODY_REGISTRY_SCHEMA:
        errors.append("scope_release registry_schema must be 2")
    if proof.get("index_schema") != SAFE_CUSTODY_INDEX_SCHEMA:
        errors.append("scope_release index_schema must be 4")
    operation_id = proof.get("operation_id")
    if not isinstance(operation_id, str) or not re.fullmatch(r"[0-9a-f]{64}", operation_id):
        errors.append("scope_release operation_id must be a lowercase SHA-256")
    control_branch = proof.get("control_branch")
    if (
        not isinstance(control_branch, str)
        or not CONTROL_BRANCH_RE.fullmatch(control_branch)
        or "-release-surfaces-" not in control_branch
    ):
        errors.append("scope_release control_branch must be a release-surfaces control branch")
    if not re.fullmatch(r"[0-9a-f]{64}", str(proof.get("control_lease_sha256", ""))):
        errors.append("scope_release control_lease_sha256 must be a lowercase SHA-256")
    quiescence_ref = proof.get("quiescence_ref")
    if not isinstance(quiescence_ref, str) or not REF_RE.fullmatch(quiescence_ref):
        errors.append("scope_release quiescence_ref must be an opaque authority reference")
    for field in ("prior_claim_sha256", "reduction_sha256"):
        if not re.fullmatch(r"[0-9a-f]{64}", str(proof.get(field, ""))):
            errors.append(f"scope_release {field} must be a lowercase SHA-256")
    for field in ("checkpoint_sha", "prepared_from_main"):
        if not SHA_RE.fullmatch(str(proof.get(field, ""))):
            errors.append(f"scope_release {field} must be a full SHA")
    for field, normalizer in (
        ("released_surfaces", normalize_path),
        ("prior_domains", normalize_domain),
        ("new_domains", normalize_domain),
    ):
        values = proof.get(field)
        if not isinstance(values, list) or (field in {"prior_domains", "new_domains"} and not values):
            errors.append(
                f"scope_release {field} must be "
                + ("a non-empty list" if field == "prior_domains" else "a list")
            )
            continue
        normalized: list[str] = []
        for value in values:
            try:
                normalized.append(normalizer(value))
            except ValueError as exc:
                errors.append(f"scope_release {field}: {exc}")
        if normalized != values or len(normalized) != len(set(normalized)):
            errors.append(f"scope_release {field} must contain unique normalized values")
    file_proofs = proof.get("released_file_proofs")
    if not isinstance(file_proofs, list):
        errors.append("scope_release released_file_proofs must be a list")
    else:
        seen_paths: set[str] = set()
        for item in file_proofs:
            if not isinstance(item, dict) or set(item) != {
                "path", "main_mode", "main_blob", "checkpoint_mode",
                "checkpoint_blob", "unpublished_delta", "accepted_introduction",
            }:
                errors.append("each released file proof must use the exact field set")
                continue
            try:
                path = normalize_path(item.get("path"))
            except ValueError as exc:
                errors.append(f"scope_release released file path: {exc}")
                continue
            if path != item.get("path") or path in seen_paths:
                errors.append("scope_release released file paths must be unique and normalized")
            seen_paths.add(path)
            for prefix in ("main", "checkpoint"):
                mode = item.get(f"{prefix}_mode")
                blob = item.get(f"{prefix}_blob")
                if (mode is None) != (blob is None):
                    errors.append(
                        f"scope_release {prefix} mode/blob must both be present or absent"
                    )
                elif mode is not None and (
                    mode not in {"100644", "100755"}
                    or not isinstance(blob, str)
                    or not SHA_RE.fullmatch(blob)
                ):
                    errors.append(
                        f"scope_release {prefix} mode/blob must identify one regular Git blob"
                    )
            if type(item.get("unpublished_delta")) is not bool:
                errors.append("scope_release unpublished_delta must be a boolean")
            introduction = item.get("accepted_introduction")
            if introduction is not None:
                if not isinstance(introduction, dict) or set(introduction) != {
                    "package", "candidate_sha", "merged_sha", "receipt_ref"
                }:
                    errors.append("scope_release accepted_introduction has an unsupported field set")
                else:
                    if not PACKAGE_RE.fullmatch(str(introduction.get("package", ""))):
                        errors.append("scope_release accepted introduction package is invalid")
                    for field in ("candidate_sha", "merged_sha"):
                        if not SHA_RE.fullmatch(str(introduction.get(field, ""))):
                            errors.append(
                                f"scope_release accepted introduction {field} must be a full SHA"
                            )
                    package = str(introduction.get("package", ""))
                    expected_receipt = (
                        receipt_relative_path(package)
                        if PACKAGE_RE.fullmatch(package)
                        else ""
                    )
                    if introduction.get("receipt_ref") != expected_receipt:
                        errors.append(
                            "scope_release accepted introduction must name its fixed receipt"
                        )
            if item.get("unpublished_delta") is False and introduction is not None:
                errors.append(
                    "scope_release unchanged released file must not assert accepted introduction"
                )
            if item.get("unpublished_delta") is True and introduction is None:
                errors.append(
                    "scope_release unpublished released file requires accepted introduction"
                )
    responsibilities = proof.get("retained_responsibilities")
    if not isinstance(responsibilities, list) or not responsibilities:
        errors.append("scope_release retained_responsibilities must be a non-empty list")
    else:
        seen: set[tuple[str, str]] = set()
        for item in responsibilities:
            if not isinstance(item, dict) or set(item) != {"responsibility", "domain"}:
                errors.append(
                    "each retained responsibility must contain exactly responsibility and domain"
                )
                continue
            responsibility = item.get("responsibility")
            if (
                not isinstance(responsibility, str)
                or responsibility != responsibility.strip()
                or not responsibility
                or len(responsibility) > 500
                or "\n" in responsibility
                or "\r" in responsibility
            ):
                errors.append("scope_release responsibility must be bounded and single-line")
            try:
                domain = normalize_domain(item.get("domain"))
            except ValueError as exc:
                errors.append(f"scope_release responsibility domain: {exc}")
                continue
            if domain != item.get("domain"):
                errors.append("scope_release responsibility domain must be normalized")
            key = (str(responsibility), domain)
            if key in seen:
                errors.append("scope_release retained_responsibilities contains a duplicate")
            seen.add(key)
    rationale = proof.get("release_rationale")
    if (
        not isinstance(rationale, str)
        or rationale != rationale.strip()
        or not rationale
        or len(rationale) > 1200
        or "\n" in rationale
        or "\r" in rationale
    ):
        errors.append("scope_release release_rationale must be bounded and single-line")
    package = proof.get("fixed_evidence_ref")
    if (
        not isinstance(package, str)
        or package != package.strip()
        or not package.startswith(EVIDENCE_REL + "/")
        or not package.endswith(".md")
    ):
        errors.append("scope_release fixed_evidence_ref must name one fixed evidence path")
    return errors


def _scope_release_tree_entry(root: Path, ref: str, path: str) -> dict[str, str | None]:
    """Return an exact regular-file mode/blob tuple, or explicit absence."""

    result = _git_result(root, "ls-tree", "-z", ref, "--", path)
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip() or "ls-tree failed"
        raise PreflightError(f"could not inspect released path {path} at {ref}: {detail}")
    rows = [row for row in result.stdout.split("\0") if row]
    if not rows:
        return {"mode": None, "blob": None}
    if len(rows) != 1:
        raise PreflightError(f"released path proof is ambiguous at {ref}: {path}")
    metadata, separator, observed_path = rows[0].partition("\t")
    columns = metadata.split()
    if (
        not separator
        or observed_path != path
        or len(columns) != 3
        or columns[0] not in {"100644", "100755"}
        or columns[1] != "blob"
        or not SHA_RE.fullmatch(columns[2].casefold())
    ):
        raise PreflightError(
            f"released path must be one exact regular Git blob or absent: {path}"
        )
    return {"mode": columns[0], "blob": columns[2].casefold()}


def build_scope_release_file_proofs(
    *,
    root: Path,
    before_surfaces: list[str],
    after_surfaces: list[str],
    checkpoint_sha: str,
    prepared_from_main: str,
    accepted_introductions: list[dict],
) -> list[dict]:
    """Construct exact C/M/base proof for every released file."""

    if not isinstance(accepted_introductions, list):
        raise PreflightError("accepted_introductions must be a list")
    introduction_by_path: dict[str, dict] = {}
    for introduction in accepted_introductions:
        if not isinstance(introduction, dict) or set(introduction) != {
            "path", "package", "candidate_sha", "merged_sha", "receipt_ref"
        }:
            raise PreflightError("accepted introduction proposal has an unsupported field set")
        try:
            path = normalize_path(introduction.get("path"))
        except ValueError as exc:
            raise PreflightError(f"accepted introduction path is invalid: {exc}") from exc
        if path in introduction_by_path:
            raise PreflightError("accepted introduction path is duplicated")
        introduction_by_path[path] = {
            key: introduction[key]
            for key in ("package", "candidate_sha", "merged_sha", "receipt_ref")
        }
    released = [path for path in before_surfaces if path not in set(after_surfaces)]
    unexpected = sorted(set(introduction_by_path) - set(released))
    if unexpected:
        raise PreflightError(
            "accepted introductions name paths that are not released: " + repr(unexpected)
        )
    merge_base = _git(root, "merge-base", checkpoint_sha, prepared_from_main)
    proofs: list[dict] = []
    for path in released:
        main = _scope_release_tree_entry(root, prepared_from_main, path)
        checkpoint = _scope_release_tree_entry(root, checkpoint_sha, path)
        if main != checkpoint:
            raise PreflightError(
                f"released path mode/blob differs between checkpoint C and prepared main M: {path}"
            )
        base = _scope_release_tree_entry(root, merge_base, path)
        unpublished_delta = base != checkpoint
        introduction = introduction_by_path.get(path)
        if unpublished_delta and introduction is None:
            raise PreflightError(
                f"released path has net branch delta without accepted introduction proof: {path}"
            )
        if not unpublished_delta and introduction is not None:
            raise PreflightError(
                f"released path has no net branch delta but asserts accepted introduction: {path}"
            )
        proofs.append(
            {
                "path": path,
                "main_mode": main["mode"],
                "main_blob": main["blob"],
                "checkpoint_mode": checkpoint["mode"],
                "checkpoint_blob": checkpoint["blob"],
                "unpublished_delta": unpublished_delta,
                "accepted_introduction": introduction,
            }
        )
    return proofs


def _scope_release_git_errors(
    root: Path, before: dict, after: dict, proof: dict
) -> list[str]:
    """Recompute file evidence and accepted-main lineage from Git objects."""

    errors: list[str] = []
    file_proofs = proof.get("released_file_proofs")
    if not isinstance(file_proofs, list):
        return ["scope_release released file proofs are unavailable"]
    accepted = []
    for item in file_proofs:
        if isinstance(item, dict) and isinstance(item.get("accepted_introduction"), dict):
            accepted.append({"path": item.get("path"), **item["accepted_introduction"]})
    try:
        expected = build_scope_release_file_proofs(
            root=root,
            before_surfaces=before.get("surfaces", []),
            after_surfaces=after.get("surfaces", []),
            checkpoint_sha=str(proof.get("checkpoint_sha", "")),
            prepared_from_main=str(proof.get("prepared_from_main", "")),
            accepted_introductions=accepted,
        )
    except (PreflightError, TypeError, KeyError) as exc:
        return ["scope_release Git path proof failed: " + str(exc)]
    if file_proofs != expected:
        errors.append("scope_release released file proofs do not match exact Git objects")

    package = str(before.get("package", ""))
    fixed = set(control_relative_paths(package))
    released_with_accepted = {
        item["path"]
        for item in expected
        if item.get("accepted_introduction") is not None
    }
    try:
        merge_base = _git(
            root,
            "merge-base",
            str(proof.get("checkpoint_sha", "")),
            str(proof.get("prepared_from_main", "")),
        )
        raw_delta = _git(
            root,
            "diff",
            "--name-only",
            "-z",
            merge_base,
            str(proof.get("checkpoint_sha", "")),
        )
    except PreflightError as exc:
        errors.append("scope_release candidate delta proof failed: " + str(exc))
        raw_delta = ""
    candidate_paths = [path for path in raw_delta.split("\0") if path]
    outside = sorted(
        path
        for path in candidate_paths
        if path not in fixed
        and path not in released_with_accepted
        and not path_is_claimed(path, after.get("surfaces", []))
    )
    if outside:
        errors.append(
            "scope_release candidate delta escapes retained surfaces: " + repr(outside)
        )

    for item in expected:
        introduction = item.get("accepted_introduction")
        if not isinstance(introduction, dict):
            continue
        intro_package = str(introduction.get("package", ""))
        candidate = str(introduction.get("candidate_sha", ""))
        merged = str(introduction.get("merged_sha", ""))
        main = str(proof.get("prepared_from_main", ""))
        path = str(item.get("path", ""))
        try:
            if not _is_ancestor(root, merged, main):
                raise ValueError("accepted main commit is not in prepared-main history")
            receipt = load_receipt_at_ref(root, merged, intro_package)
            historical_claim = _json_at_ref(
                root, merged, claim_relative_path(intro_package)
            )
            if (
                receipt is None
                or validate_receipt(receipt, historical_claim)
                or receipt.get("candidate_sha") != candidate
                or receipt.get("evidence_ref") != evidence_relative_path(intro_package)
                or introduction.get("receipt_ref") != receipt_relative_path(intro_package)
            ):
                raise ValueError("accepted introduction lacks its exact review receipt")
            for ref in (candidate, merged, main, str(proof.get("checkpoint_sha", ""))):
                if _scope_release_tree_entry(root, ref, path) != {
                    "mode": item.get("checkpoint_mode"),
                    "blob": item.get("checkpoint_blob"),
                }:
                    raise ValueError("accepted introduction bytes are not exact across history")
            parent = _git(root, "rev-parse", f"{merged}^1")
            if _scope_release_tree_entry(root, parent, path) == _scope_release_tree_entry(
                root, merged, path
            ):
                raise ValueError("accepted main commit did not introduce the released bytes")
            candidate_base = _git(root, "merge-base", candidate, merged)
            if _scope_release_tree_entry(
                root, candidate_base, path
            ) == _scope_release_tree_entry(root, candidate, path):
                raise ValueError("reviewed candidate did not introduce the released bytes")
            if not _tracked_regular_blob(
                root, merged, evidence_relative_path(intro_package)
            ):
                raise ValueError("accepted introduction evidence is unavailable")
        except (PreflightError, ValueError, KeyError, TypeError) as exc:
            errors.append(f"scope_release accepted introduction for {path}: {exc}")
    return errors


def scope_reduction_sha256(
    *,
    before_surfaces: list[str],
    after_surfaces: list[str],
    before_domains: list[str],
    after_domains: list[str],
    retained_responsibilities: list[dict],
    release_rationale: str,
    released_file_proofs: list[dict],
    fixed_evidence_ref: str,
) -> str:
    return hashlib.sha256(
        json.dumps(
            {
                "before_surfaces": before_surfaces,
                "after_surfaces": after_surfaces,
                "before_domains": before_domains,
                "after_domains": after_domains,
                "retained_responsibilities": retained_responsibilities,
                "release_rationale": release_rationale,
                "released_file_proofs": released_file_proofs,
                "fixed_evidence_ref": fixed_evidence_ref,
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()


def validate_scope_release_transition(
    before: dict,
    after: dict,
    *,
    registry: dict | None = None,
    root: Path | None = None,
) -> list[str]:
    """Prove one monotonic claim reduction and its durable freeze linkage."""

    errors = validate_scope_release_proof(after.get("scope_release"))
    proof = after.get("scope_release")
    if not isinstance(proof, dict):
        return [*errors, "release-surfaces requires a scope_release proof"]
    changed = _changed_fields(before, after)
    if (
        "scope_release" not in changed
        or not changed.intersection({"surfaces", "domains"})
        or not changed <= {"surfaces", "domains", "scope_release"}
    ):
        errors.append(
            "release-surfaces may change only surfaces, domains, and scope_release, "
            "and must reduce at least one scope field"
        )
    before_surfaces = before.get("surfaces")
    after_surfaces = after.get("surfaces")
    before_domains = before.get("domains")
    after_domains = after.get("domains")
    if not all(
        isinstance(value, list)
        for value in (before_surfaces, after_surfaces, before_domains, after_domains)
    ):
        return [*errors, "release-surfaces requires valid surface and domain lists"]
    retained = [path for path in before_surfaces if path in set(after_surfaces)]
    released = [path for path in before_surfaces if path not in set(after_surfaces)]
    if retained != after_surfaces:
        errors.append(
            "release-surfaces must preserve the relative order of retained paths"
        )
    if any(path not in before_surfaces for path in after_surfaces):
        errors.append("release-surfaces cannot add paths")
    fixed = set(control_relative_paths(str(before.get("package", ""))))
    if fixed - set(after_surfaces):
        errors.append("release-surfaces cannot remove fixed claim, receipt, or evidence paths")
    if proof.get("released_surfaces") != released:
        errors.append("scope_release released_surfaces does not match the exact removed paths")
    if proof.get("prior_domains") != before_domains:
        errors.append("scope_release prior_domains does not match the authoritative claim")
    if proof.get("new_domains") != after_domains:
        errors.append("scope_release new_domains does not match the reduced claim")
    if not after_domains:
        errors.append("release-surfaces must retain at least one responsibility domain")
    if not released and after_domains == before_domains:
        errors.append("release-surfaces must reduce at least one path or domain")
    new_coverage_is_subset = _domain_coverage_is_subset(
        after_domains, before_domains
    )
    for domain in after_domains:
        if not any(_domain_is_equal_or_descendant(domain, old) for old in before_domains):
            errors.append(f"release-surfaces domain expands or moves scope: {domain}")
    if (
        after_domains != before_domains
        and new_coverage_is_subset
        and _domain_coverage_is_subset(before_domains, after_domains)
    ):
        errors.append(
            "release-surfaces changed domains must strictly reduce semantic authority coverage"
        )
    responsibilities = proof.get("retained_responsibilities")
    if isinstance(responsibilities, list):
        for item in responsibilities:
            if isinstance(item, dict) and item.get("domain") not in after_domains:
                errors.append(
                    "each retained responsibility must map to one exact retained domain"
                )
    if proof.get("prior_claim_sha256") != canonical_claim_sha256(before):
        errors.append("scope_release prior_claim_sha256 does not match origin/main")
    expected_evidence = evidence_relative_path(str(before.get("package", "")))
    if proof.get("fixed_evidence_ref") != expected_evidence:
        errors.append("scope_release fixed_evidence_ref does not match the package evidence path")
    file_proofs = proof.get("released_file_proofs")
    released_proof_paths = (
        [item.get("path") for item in file_proofs if isinstance(item, dict)]
        if isinstance(file_proofs, list)
        else []
    )
    if released_proof_paths != released:
        errors.append("scope_release released file proofs do not match removed path order")
    expected_reduction = scope_reduction_sha256(
        before_surfaces=before_surfaces,
        after_surfaces=after_surfaces,
        before_domains=before_domains,
        after_domains=after_domains,
        retained_responsibilities=responsibilities if isinstance(responsibilities, list) else [],
        release_rationale=str(proof.get("release_rationale", "")),
        released_file_proofs=file_proofs if isinstance(file_proofs, list) else [],
        fixed_evidence_ref=str(proof.get("fixed_evidence_ref", "")),
    )
    if proof.get("reduction_sha256") != expected_reduction:
        errors.append("scope_release reduction_sha256 does not match the exact reduction")
    if root is not None:
        errors.extend(_scope_release_git_errors(root, before, after, proof))
    if registry is not None:
        try:
            lifecycle_registry.validate_safe_custody_registry(registry)
        except lifecycle_registry.Refusal as exc:
            errors.append("scope_release registry proof is invalid: " + str(exc))
        else:
            matches = [
                record
                for record in registry["safe_custody"]["scope_releases"]
                if record.get("operation_id") == proof.get("operation_id")
            ]
            if len(matches) != 1:
                errors.append("scope_release requires one exact lifecycle freeze record")
            else:
                record = matches[0]
                expected = {
                    "package": after.get("package"),
                    "task_ref": after.get("writer_ref"),
                    "branch": after.get("branch"),
                    "control_branch": proof.get("control_branch"),
                    "control_lease_sha256": proof.get("control_lease_sha256"),
                    "quiescence_ref": proof.get("quiescence_ref"),
                    "checkpoint_sha": proof.get("checkpoint_sha"),
                    "prior_claim_sha256": proof.get("prior_claim_sha256"),
                    "reduction_sha256": proof.get("reduction_sha256"),
                    "intended_claim_sha256": canonical_claim_sha256(after),
                    "prepared_from_main": proof.get("prepared_from_main"),
                    "state": "pending",
                }
                if any(record.get(key) != value for key, value in expected.items()):
                    errors.append("scope_release claim and lifecycle freeze tuple differ")
    return errors


def _string_field(
    claim: dict, field: str, errors: list[str], *, maximum: int = 1000
) -> str:
    value = claim.get(field)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"claim {field} must be a non-empty string")
        return ""
    if value != value.strip() or "\n" in value or "\r" in value or len(value) > maximum:
        errors.append(f"claim {field} must be bounded, trimmed, and single-line")
    return value


def _normalized_string_list(
    claim: dict, field: str, errors: list[str], normalizer
) -> list[str]:
    values = claim.get(field)
    if not isinstance(values, list) or not values:
        errors.append(f"claim {field} must be a non-empty list")
        return []
    normalized: list[str] = []
    for value in values:
        try:
            item = normalizer(value)
        except ValueError as exc:
            errors.append(f"claim {field}: {exc}")
            continue
        if item in normalized:
            errors.append(f"claim {field} contains duplicate {item}")
        normalized.append(item)
    if normalized != values:
        errors.append(f"claim {field} must contain normalized values")
    return normalized


def _validate_handoff(handoff: object) -> list[str]:
    """Validate durable transfer or owner-reassignment provenance.

    Voluntary transfer and owner-directed recovery are intentionally different
    record shapes.  In particular, an owner reassignment has no
    ``relinquished`` field and can never be mistaken for consent from the prior
    writer.
    """

    if handoff is None:
        return []
    if not isinstance(handoff, dict):
        return ["claim handoff must be null or an object"]

    errors: list[str] = []
    if set(handoff) == VOLUNTARY_HANDOFF_FIELDS:
        refs = (handoff.get("from_ref"), handoff.get("to_ref"))
        if handoff.get("relinquished") is not True:
            errors.append("voluntary handoff requires explicit relinquishment")
        if not all(isinstance(ref, str) and REF_RE.fullmatch(ref) for ref in refs):
            errors.append("voluntary handoff references must be opaque task/session/agent/role refs")
        if refs[0] == refs[1]:
            errors.append("voluntary handoff must change the writer reference")
        if not SHA_RE.fullmatch(str(handoff.get("checkpoint_sha", ""))):
            errors.append("voluntary handoff checkpoint_sha must be a full SHA")
        return errors

    if set(handoff) != OWNER_REASSIGNMENT_FIELDS:
        return [
            "claim handoff must be either the exact voluntary-transfer shape "
            "or the exact owner_reassignment shape"
        ]
    if handoff.get("type") != "owner_reassignment":
        errors.append("owner reassignment handoff type must be owner_reassignment")
    refs = (handoff.get("from_ref"), handoff.get("to_ref"))
    if not all(isinstance(ref, str) and REF_RE.fullmatch(ref) for ref in refs):
        errors.append("owner reassignment references must be opaque task/session/agent/role refs")
    if refs[0] == refs[1]:
        errors.append("owner reassignment must change the writer reference")
    for field in ("from_branch", "to_branch"):
        branch = handoff.get(field)
        if not _is_normalized_work_branch(branch):
            errors.append(f"owner reassignment {field} must be a normalized work branch")
    if handoff.get("from_branch") == handoff.get("to_branch"):
        errors.append("owner reassignment must use a distinct successor branch")
    if not SHA_RE.fullmatch(str(handoff.get("checkpoint_sha", ""))):
        errors.append("owner reassignment checkpoint_sha must be a full SHA")
    owner_ref = handoff.get("owner_authorization_ref")
    if not isinstance(owner_ref, str) or not REF_RE.fullmatch(owner_ref):
        errors.append(
            "owner reassignment owner_authorization_ref must be an opaque "
            "task/session/agent/role reference"
        )
    if "relinquished" in handoff:
        errors.append("owner reassignment may not assert relinquishment")
    return errors


def validate_claim(claim: dict, *, expected_package: str | None = None) -> list[str]:
    errors: list[str] = []
    if claim.get("schema_version") != 1:
        errors.append("claim schema_version must be 1")
    package = _string_field(claim, "package", errors, maximum=120)
    if package and not PACKAGE_RE.fullmatch(package):
        errors.append("claim package must be a canonical PS-* identifier")
    if expected_package and package != expected_package:
        errors.append(f"claim filename must match package {expected_package}")
    state = claim.get("state")
    if state not in STATES:
        errors.append(
            "claim state must be active, paused, closed, or superseded"
        )
    _string_field(claim, "outcome", errors, maximum=1200)
    assignment = claim.get("assignment")
    if assignment not in ASSIGNMENTS:
        errors.append("claims are for implementation writers; reviewers are read-only and claim-free")
    writer_ref = _string_field(claim, "writer_ref", errors, maximum=185)
    if writer_ref and not REF_RE.fullmatch(writer_ref):
        errors.append("writer_ref must be an opaque task/session/agent/role reference")
    branch = _string_field(claim, "branch", errors, maximum=200)
    if branch and (
        not _is_normalized_work_branch(branch) or branch.endswith("/main")
    ):
        errors.append("claim branch must be a non-main work/ or codex/ branch")
    if claim.get("delivery_path") not in DELIVERY_PATHS:
        errors.append("claim delivery_path must be Routine, Bounded, or Protected")
    authority = claim.get("repository_authority")
    if authority not in REPOSITORY_AUTHORITIES:
        errors.append("repository_authority must be through_merge or explicitly narrower write_only")
    if claim.get("production_authority") != "withheld":
        errors.append("repository claims may not grant production authority")
    if not SHA_RE.fullmatch(str(claim.get("activated_from_main", ""))):
        errors.append("activated_from_main must be a full SHA")
    _string_field(claim, "owner_outcome_ref", errors, maximum=240)
    surfaces = _normalized_string_list(claim, "surfaces", errors, normalize_path)
    evidence = _normalized_string_list(
        claim, "evidence_surfaces", errors, normalize_path
    )
    expected_evidence = evidence_relative_path(package) if package else ""
    expected_controls = set(control_relative_paths(package)) if package else set()
    if evidence != [expected_evidence]:
        errors.append("evidence_surfaces must be the package's fixed runtime-inert evidence file")
    missing_controls = sorted(expected_controls - set(surfaces))
    if missing_controls:
        errors.append(
            "surfaces must reserve the package's exact claim, receipt, and evidence paths: "
            + ", ".join(missing_controls)
        )
    forbidden_controls = sorted(
        path
        for path in surfaces
        if paths_overlap(path, CLAIMS_REL) and path not in expected_controls
    )
    if forbidden_controls:
        errors.append(
            "a package may not claim a broad or cross-package control path: "
            + ", ".join(forbidden_controls)
        )
    for path in evidence:
        if surfaces and not path_is_claimed(path, surfaces):
            errors.append(f"evidence surface is outside the claim: {path}")
    _normalized_string_list(claim, "domains", errors, normalize_domain)
    review = claim.get("review_requirement")
    if review not in REVIEW_REQUIREMENTS:
        errors.append("review_requirement must be self or independent")
    if claim.get("delivery_path") == "Protected" and review != "independent":
        errors.append("Protected claims require independent review")
    if state == "paused" and not SHA_RE.fullmatch(str(claim.get("checkpoint_sha", ""))):
        errors.append("paused claims require checkpoint_sha")
    if state == "closed":
        if not SHA_RE.fullmatch(str(claim.get("merged_sha", ""))):
            errors.append("closed claims require merged_sha")
        if not is_valid_utc_timestamp(claim.get("closed_at")):
            errors.append("closed claims require a UTC closed_at timestamp")
    # PS-DELIVERY-SUPERSEDE-DISPOSITION-001: superseded is the terminal
    # disposition for an activated-but-unmerged package that was rejected and
    # replaced or withdrawn. It is semantically distinct from closed: nothing
    # was delivered, so it must never carry merged_sha or closed_at, and it
    # must preserve the pushed checkpoint whose bytes exist only on the
    # reserved claim branch.
    if state == "superseded":
        if not SHA_RE.fullmatch(str(claim.get("checkpoint_sha", ""))):
            errors.append("superseded claims require the preserved checkpoint_sha")
        if not is_valid_utc_timestamp(claim.get("superseded_at")):
            errors.append("superseded claims require a UTC superseded_at timestamp")
        if claim.get("merged_sha") is not None:
            errors.append("superseded claims must not record a merged_sha")
        if claim.get("closed_at") is not None:
            errors.append("superseded claims must not record closed_at")
        supersession = claim.get("supersession")
        if not isinstance(supersession, dict):
            errors.append("superseded claims require a supersession record")
        else:
            unknown = sorted(
                set(supersession)
                - {"owner_authorization_ref", "superseded_by", "withdrawal_reason"}
            )
            if unknown:
                errors.append(
                    "supersession admits only owner_authorization_ref, "
                    "superseded_by, and withdrawal_reason: " + ", ".join(unknown)
                )
            owner_ref = supersession.get("owner_authorization_ref")
            if not isinstance(owner_ref, str) or not REF_RE.fullmatch(owner_ref):
                errors.append(
                    "supersession requires an opaque owner_authorization_ref"
                )
            superseded_by = supersession.get("superseded_by")
            reason = supersession.get("withdrawal_reason")
            has_replacements = (
                isinstance(superseded_by, list)
                and bool(superseded_by)
                and all(
                    isinstance(item, str) and PACKAGE_RE.fullmatch(item)
                    for item in superseded_by
                )
            )
            has_reason = (
                isinstance(reason, str) and 0 < len(reason.strip()) <= 1200
            )
            if not has_replacements and not has_reason:
                errors.append(
                    "supersession requires exact replacement package references "
                    "or an exact withdrawal reason"
                )
    elif "supersession" in claim or "superseded_at" in claim:
        errors.append("only superseded claims may carry supersession fields")
    handoff = claim.get("handoff")
    errors.extend(_validate_handoff(handoff))
    if isinstance(handoff, dict):
        if handoff.get("to_ref") != claim.get("writer_ref"):
            errors.append("claim handoff to_ref must equal the current writer_ref")
        if (
            handoff.get("type") == "owner_reassignment"
            and handoff.get("to_branch") != claim.get("branch")
        ):
            errors.append(
                "owner reassignment handoff to_branch must equal the current claim branch"
            )
    scope_release = claim.get("scope_release")
    errors.extend(validate_scope_release_proof(scope_release))
    if scope_release is not None and state != ACTIVE_STATE:
        errors.append("only active claims may carry a scope_release proof")
    return errors


def _claim_set_error_components(
    claims: dict[str, dict],
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    collisions: list[str] = []
    active: list[dict] = []
    unresolved: list[dict] = []
    for claim in claims.values():
        package = str(claim.get("package", ""))
        errors.extend(
            f"{package or '<unknown>'}: {error}"
            for error in validate_claim(claim, expected_package=package or None)
        )
        expected_path = claim_relative_path(package) if package else ""
        if claim.get("_relative_path") != expected_path:
            errors.append(f"{package}: claim path must be {expected_path}")
        if claim.get("state") == ACTIVE_STATE:
            active.append(claim)
        if claim.get("state") in {"active", "paused", "superseded"}:
            # A superseded claim keeps its branch name reserved: the unmerged
            # bytes exist only on that preserved remote branch.
            unresolved.append(claim)

    for index, left in enumerate(unresolved):
        for right in unresolved[index + 1 :]:
            if left.get("branch", "").casefold() == right.get("branch", "").casefold():
                errors.append(
                    f"branch collision: {left.get('package')} and {right.get('package')}"
                )

    for index, left in enumerate(active):
        for right in active[index + 1 :]:
            for a, b in colliding_paths(
                left.get("surfaces", []), right.get("surfaces", [])
            ):
                collisions.append(
                    f"path collision: {left.get('package')}:{a} and "
                    f"{right.get('package')}:{b}"
                )
            for a, b in colliding_domains(
                left.get("domains", []), right.get("domains", [])
            ):
                collisions.append(
                    f"domain collision: {left.get('package')}:{a} and "
                    f"{right.get('package')}:{b}"
                )
    return errors, collisions


def validate_claim_set(claims: dict[str, dict]) -> list[str]:
    errors, collisions = _claim_set_error_components(claims)
    return [*errors, *collisions]


def split_claim_set_errors(
    claims: dict[str, dict],
) -> tuple[list[str], list[str]]:
    """Separate active path/domain collisions from every other claim defect.

    A read may report an already-existing active ownership collision without
    authorizing work.  All structural claim defects and unresolved-branch
    collisions remain fatal, so the split is intentionally limited to the two
    collision classes that pausing or closing an active claim can remove.
    """

    return _claim_set_error_components(claims)


def validate_claim_set_admission(
    *,
    intent: str,
    candidate_claims: dict[str, dict],
    authority_claims: dict[str, dict] | None = None,
) -> tuple[list[str], list[str], dict[str, object]]:
    """Apply the non-authorizing read and collision-removal admission rules."""

    errors, candidate_collisions = split_claim_set_errors(candidate_claims)
    warnings: list[str] = []
    diagnostics: dict[str, object] = {}

    if intent == "read":
        if candidate_collisions:
            diagnostics["claim_collisions"] = candidate_collisions
            warnings.extend(
                "read-only diagnostic (non-authorizing): " + collision
                for collision in candidate_collisions
            )
        return errors, warnings, diagnostics

    if candidate_collisions:
        diagnostics["candidate_claim_collisions"] = candidate_collisions
        errors.extend(candidate_collisions)

    if authority_claims is None:
        return errors, warnings, diagnostics

    authority_errors, authority_collisions = split_claim_set_errors(
        authority_claims
    )
    errors.extend(authority_errors)
    if not authority_collisions:
        return errors, warnings, diagnostics

    diagnostics["authority_claim_collisions"] = authority_collisions
    exact_candidate_set_removes_collisions = (
        set(candidate_claims) == set(authority_claims)
        and not candidate_collisions
    )
    if exact_candidate_set_removes_collisions:
        warnings.extend(
            "pre-transition collision removed by exact candidate claim set: "
            + collision
            for collision in authority_collisions
        )
    else:
        errors.extend(
            collision
            for collision in authority_collisions
            if collision not in candidate_collisions
        )
    return errors, warnings, diagnostics


def validate_legacy_bootstrap(
    candidate_index: dict,
    candidate_claims: dict[str, dict],
    origin_index: dict,
    origin_main: str,
) -> list[str]:
    """Bound the one-time schema-v2 to schema-v3 cutover to origin/main."""
    errors: list[str] = []
    legacy = candidate_index.get("legacy_snapshot", {})
    if origin_index.get("schema_version") != 2:
        errors.append("origin claim model is neither schema 3 nor the schema 2 bootstrap")
        return errors
    if legacy.get("commit") != origin_main:
        errors.append("legacy bootstrap must pin the current fetched origin/main")
    active = origin_index.get("active_lanes")
    if not isinstance(active, list):
        errors.append("legacy bootstrap requires the schema-v2 active_lanes list")
        return errors
    old_by_package = {
        item.get("package", "").casefold(): item
        for item in active
        if isinstance(item, dict) and isinstance(item.get("package"), str)
    }
    if set(candidate_claims) != set(old_by_package):
        errors.append("legacy bootstrap must map every active package exactly once")
        return errors
    for key, new in candidate_claims.items():
        old = old_by_package[key]
        label = new.get("package", key)
        if new.get("state") != "active":
            errors.append(f"{label}: legacy active package must remain active")
        for new_field, old_field in (
            ("branch", "branch"),
            ("delivery_path", "delivery_path"),
        ):
            if new.get(new_field) != old.get(old_field):
                errors.append(f"{label}: legacy {new_field} changed during bootstrap")
        expected_authority = legacy_repository_authority(origin_index, old)
        if new.get("repository_authority") != expected_authority:
            errors.append(
                f"{label}: bootstrap repository_authority must preserve the "
                f"legacy boundary as {expected_authority}"
            )
        try:
            old_surfaces = [normalize_path(path.rstrip("/")) for path in old["writable_surfaces"]]
            old_domains = sorted(normalize_domain(value) for value in old["exclusive_domains"])
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"{label}: malformed legacy scope: {exc}")
            continue
        bootstrap_controls = set(control_relative_paths(str(label)))
        if any(
            path not in bootstrap_controls and not path_is_claimed(path, old_surfaces)
            for path in new.get("surfaces", [])
        ):
            errors.append(f"{label}: bootstrap claim widens legacy writable surfaces")
        if sorted(new.get("domains", [])) != old_domains:
            errors.append(f"{label}: bootstrap claim changes legacy collision domains")
        writer_token = str(new.get("writer_ref", "")).split(":", 1)[-1]
        current_assignment = str(old.get("writer", "")).split(".", 1)[0]
        legacy_writer_ids = LEGACY_CURRENT_WRITER_RE.findall(current_assignment)
        if (
            not LEGACY_UUID_RE.fullmatch(writer_token)
            or len(legacy_writer_ids) != 1
            or writer_token.casefold() != legacy_writer_ids[0].casefold()
        ):
            errors.append(
                f"{label}: bootstrap writer_ref is not the sole current writer "
                "in the legacy assignment sentence"
            )
        if new.get("activated_from_main") != origin_main:
            errors.append(f"{label}: activated_from_main is not current origin/main")
    return errors


def validate_receipt(receipt: dict, claim: dict) -> list[str]:
    errors: list[str] = []
    package = claim.get("package")
    if receipt.get("schema_version") != 1:
        errors.append("review receipt schema_version must be 1")
    if receipt.get("package") != package:
        errors.append("review receipt package does not match the claim")
    if not SHA_RE.fullmatch(str(receipt.get("candidate_sha", ""))):
        errors.append("review receipt candidate_sha must be a full SHA")
    review_type = receipt.get("review_type")
    if review_type != claim.get("review_requirement"):
        errors.append("review receipt type does not match the claim")
    reviewer_ref = receipt.get("reviewer_ref")
    if not isinstance(reviewer_ref, str) or not REF_RE.fullmatch(reviewer_ref):
        errors.append("reviewer_ref must be an opaque task/session/agent/role reference")
    if review_type == "independent" and reviewer_ref == claim.get("writer_ref"):
        errors.append("independent reviewer must differ from the writer_ref")
    if review_type == "self" and reviewer_ref != claim.get("writer_ref"):
        errors.append("self-review reviewer_ref must equal the writer_ref")
    if receipt.get("result") != "pass":
        errors.append("review receipt result must be pass")
    if not is_valid_utc_timestamp(receipt.get("reviewed_at")):
        errors.append("reviewed_at must be a UTC timestamp")
    findings = receipt.get("findings")
    if not isinstance(findings, list):
        errors.append("review receipt findings must be a list")
    else:
        unresolved = [
            item
            for item in findings
            if not isinstance(item, dict)
            or item.get("status") not in {"resolved", "informational"}
        ]
        if unresolved:
            errors.append("review receipt contains unresolved findings")
    evidence_ref = receipt.get("evidence_ref")
    if not isinstance(evidence_ref, str) or not evidence_ref.strip() or len(evidence_ref) > 300:
        errors.append("review receipt requires a bounded evidence_ref")
    return errors


def _status_paths(root: Path) -> tuple[str, ...]:
    tokens = _git_nul(root, "status", "--porcelain=v1", "-z", "--untracked-files=all")
    paths: list[str] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        index += 1
        if len(token) < 4:
            continue
        status = token[:2]
        path = token[3:]
        paths.append(normalize_path(path))
        if ("R" in status or "C" in status) and index < len(tokens):
            source = normalize_path(tokens[index])
            if "R" in status:
                paths.append(source)
            index += 1
    return tuple(sorted(set(paths)))


def _diff_paths(root: Path, range_spec: str) -> tuple[str, ...]:
    tokens = _git_nul(root, "diff", "--name-status", "-z", range_spec)
    paths: list[str] = []
    index = 0
    while index < len(tokens):
        status = tokens[index]
        index += 1
        if status.startswith(("R", "C")):
            if index + 1 >= len(tokens):
                raise PreflightError("git diff returned malformed name-status data")
            source = normalize_path(tokens[index])
            destination = normalize_path(tokens[index + 1])
            index += 2
            if status.startswith("R"):
                paths.append(source)
            paths.append(destination)
        else:
            if index >= len(tokens):
                raise PreflightError("git diff returned malformed name-status data")
            paths.append(normalize_path(tokens[index]))
            index += 1
    return tuple(sorted(set(paths)))


def collect_repo_facts(root: Path, *, fetch: bool) -> RepoFacts:
    if fetch:
        _git(root, "fetch", "--prune", "origin", "main")
    repository = Path(_git(root, "rev-parse", "--show-toplevel")).resolve()
    branch = _git(root, "branch", "--show-current")
    head = _git(root, "rev-parse", "HEAD")
    origin_main = _git(root, "rev-parse", "refs/remotes/origin/main")
    counts = _git(root, "rev-list", "--left-right", "--count", "origin/main...HEAD")
    behind_text, ahead_text = counts.split()
    merge_base = _git(root, "merge-base", "origin/main", "HEAD")
    worktree_paths = _status_paths(root)
    return RepoFacts(
        repository=str(repository),
        branch=branch,
        head=head,
        origin_main=origin_main,
        ahead=int(ahead_text),
        behind=int(behind_text),
        clean=not worktree_paths,
        branch_paths=_diff_paths(root, f"{merge_base}..HEAD"),
        main_paths=_diff_paths(root, f"{merge_base}..origin/main"),
        worktree_paths=worktree_paths,
        fetched=fetch,
        origin_url=_git(root, "remote", "get-url", "origin"),
    )


def _changed_fields(before: dict, after: dict) -> set[str]:
    keys = set(before) | set(after)
    missing = object()
    return {
        key
        for key in keys
        if key != "_relative_path"
        and before.get(key, missing) != after.get(key, missing)
    }


def _scope_errors(paths: Iterable[str], surfaces: Iterable[str]) -> list[str]:
    return [path for path in paths if not path_is_claimed(path, surfaces)]


def _verify_legacy_snapshot(root: Path, index: dict, errors: list[str]) -> None:
    legacy = index.get("legacy_snapshot")
    if not isinstance(legacy, dict):
        return
    commit = str(legacy.get("commit", ""))
    path = str(legacy.get("path", ""))
    expected_blob = str(legacy.get("blob", ""))
    if not SHA_RE.fullmatch(commit) or not path or not expected_blob:
        return
    result = _git_result(root, "rev-parse", f"{commit}:{path}")
    if result.returncode:
        errors.append("legacy snapshot commit/path is not available in Git")
    elif result.stdout.strip() != expected_blob:
        errors.append("legacy snapshot blob does not match its pinned Git object")


def _origin_claim(root: Path, package: str) -> dict:
    return _json_at_ref(root, "origin/main", claim_relative_path(package))


def _operations_only_close_errors(
    root: Path, claim: dict, receipt: dict, candidate: str, merged: str,
    remote_tip: str, merged_paths: Iterable[str],
) -> list[str]:
    """Admit reviewed, immutable completed custody evidence, never an empty audit.

    This local-operation exception needs the originating machine's registry;
    unlike ordinary close, neither CI nor an uninitialized host can attest it.
    It grants no retirement permission and never reconciles or changes custody.
    """
    lifecycle = lifecycle_registry
    try:
        if _is_ci_environment():
            raise ValueError("operations completion requires local custody, not CI")
        package = claim["package"]
        evidence_path = evidence_relative_path(package)
        receipt_path = receipt_relative_path(package)
        if validate_receipt(receipt, claim) or receipt.get("review_type") != "independent":
            raise ValueError("operations completion requires an independent pass")
        if receipt.get("evidence_ref") != evidence_path:
            raise ValueError("completion receipt must name the fixed evidence file")
        if evidence_path not in merged_paths:
            raise ValueError("merged_sha must introduce the reviewed completion evidence")
        context = lifecycle._repo_context(root)
        # A mutex-held read binds evidence to completed local custody. There is
        # intentionally no CI/missing-registry fallback for this exception.
        with lifecycle._registry_lock(context.registry_path):
            registry = lifecycle._load_registry(context.registry_path)
            if registry is None:
                raise ValueError("operations completion requires an initialized registry")
            lifecycle._assert_registry_identity(context, registry)
            if registry.get("pending") is not None:
                raise ValueError("operations completion refuses pending custody")
            if not all(isinstance(item, dict) for item in registry["worktrees"]):
                raise ValueError("operations completion refuses malformed registry custody")
            lifecycle._closed_custody_cleanup_claim(
                context, package=package, task_ref=claim["writer_ref"],
                owner_authorization_ref=claim["owner_outcome_ref"],
            )
            lifecycle._validate_closed_custody_registry(registry)
            # The evidence itself is reviewed: the ordinary evidence-tail
            # allowance cannot change it after this completion candidate.
            def exact_blob(path: str, refs: Iterable[str]) -> str:
                blobs = []
                for ref in refs:
                    if not _tracked_regular_blob(root, ref, path):
                        raise ValueError(f"completion requires ordinary Git blob: {path}")
                    blobs.append(_git(root, "rev-parse", f"{ref}:{path}"))
                if len(set(blobs)) != 1:
                    raise ValueError(f"completion bytes changed: {path}")
                return blobs[0]

            exact_blob(evidence_path, (candidate, merged, "origin/main", remote_tip))
            exact_blob(receipt_path, (merged, "origin/main", remote_tip))
            raw = _git(root, "show", f"{candidate}:{evidence_path}")
            blocks = re.findall(
                r"^```peerslate-closed-custody-completion\s*\n(.*?)\n```[ \t]*$",
                raw, flags=re.MULTILINE | re.DOTALL,
            )
            if len(blocks) != 1:
                raise ValueError("one closed-custody completion JSON block is required")

            def unique_object(pairs):
                value = {}
                for key, item in pairs:
                    if key in value:
                        raise ValueError("duplicate completion JSON key")
                    value[key] = item
                return value

            completion = json.loads(blocks[0], object_pairs_hook=unique_object)
            if (
                not isinstance(completion, dict)
                or set(completion) != {"schema_version", "package", "retirements"}
                or type(completion["schema_version"]) is not int
                or completion["schema_version"] != 1
                or completion["package"] != package
                or not isinstance(completion["retirements"], list)
                or not completion["retirements"]
            ):
                raise ValueError("completion must contain non-empty exact custody evidence")
            records = [
                item for item in registry["worktrees"]
                if isinstance(item.get("closed_custody_retirement"), dict)
                and item["closed_custody_retirement"].get("cleanup_package") == package
            ]
            proofs = [item["closed_custody_retirement"] for item in records]
            stable = lambda value: json.dumps(value, sort_keys=True)
            if sorted(map(stable, proofs)) != sorted(map(stable, completion["retirements"])):
                raise ValueError("completion evidence does not equal all recorded package retirements")
            mechanisms = lifecycle.CLOSED_CUSTODY_REQUIRED_SURFACES | {
                "scripts/delivery_preflight.py", "tests/test_delivery_preflight.py",
            }
            for record in records:
                proof = lifecycle._validate_closed_custody_retirement(
                    record["closed_custody_retirement"], record=record,
                )
                if sum(item.get("path") == proof["target_path"] for item in registry["worktrees"]) != 1:
                    raise ValueError("completed target has duplicate registry custody")
                lifecycle._unique_active_durable_record(
                    registry, package=package, path=Path(proof["cleanup_path"]),
                    branch=claim["branch"], task_ref=claim["writer_ref"], label="cleanup",
                )
                if (
                    proof["cleanup_task_ref"] != claim["writer_ref"]
                    or proof["cleanup_branch"] != claim["branch"]
                    or proof["owner_authorization_ref"] != claim["owner_outcome_ref"]
                ):
                    raise ValueError("completed operation lost current cleanup authority")
                authority = proof["authoritative_main"]
                historical_claim = _json_at_ref(root, authority, claim_relative_path(package))
                if _changed_fields(historical_claim, claim):
                    raise ValueError("operation claim differs from current cleanup authority")
                accepted = load_receipt_at_ref(root, authority, package)
                if (
                    accepted is None or validate_receipt(accepted, claim)
                    or accepted.get("review_type") != "independent"
                    or accepted.get("candidate_sha") != proof["reviewed_candidate"]
                    or accepted.get("reviewer_ref") != proof["reviewer_ref"]
                    or accepted.get("evidence_ref") != evidence_path
                    or not _tracked_regular_blob(root, authority, evidence_path)
                ):
                    raise ValueError("operation lacks its accepted exact mechanism review")
                for older, newer in (
                    (authority, merged),
                    (proof["reviewed_candidate"], proof["cleanup_head"]),
                    (proof["cleanup_head"], candidate),
                ):
                    if not _is_ancestor(root, older, newer):
                        raise ValueError("operation mechanism is not in accepted completion history")
                for path in mechanisms:
                    blob = exact_blob(path, (
                        proof["reviewed_candidate"], authority, proof["cleanup_head"],
                        candidate, merged, "origin/main", remote_tip,
                    ))
                    if path == "scripts/worktree_lifecycle.py" and blob != proof["lifecycle_script_blob"]:
                        raise ValueError("operation lifecycle blob differs from accepted mechanism")
                for ref in (authority, "origin/main"):
                    target = _json_at_ref(root, ref, claim_relative_path(proof["target_package"]))
                    if (
                        target.get("state") != "closed"
                        or target.get("writer_ref") != proof["source_task_ref"]
                        or target.get("branch") != proof["target_branch"]
                    ):
                        raise ValueError("completed target lost its closed original custody")
                path = Path(proof["target_path"])
                if os.path.lexists(path) or lifecycle._worktree_at(root, path):
                    raise ValueError("completed target is still present or registered")
                if lifecycle._remote_branch_tip(context, proof["target_branch"]) != proof["expected_head"]:
                    raise ValueError("completed target recovery branch no longer equals expected HEAD")
        return []
    except (lifecycle.Refusal, PreflightError, ValueError, KeyError, TypeError, OSError) as exc:
        return ["close requires a non-empty reviewed candidate or valid operations completion: " + str(exc)]


def _reconciled_product_close_errors(
    root: Path, claim: dict, receipt: dict, candidate: str, merged: str,
    remote_tip: str, pinned_main: str,
) -> list[str] | None:
    """Verify a reviewed product introduced on main by a content-equivalent merge.

    ``None`` means this is not a synchronization-merge candidate; an invalid
    recognized graph returns its own refusal and cannot use operations-only.
    Git history and attributed receipts are operational attestations, not
    cryptographic authentication of the historical reviewer or proof that the
    historical receipt was accepted on main.
    """
    def parents(commit: str) -> list[str]:
        values = _git(root, "rev-list", "--parents", "-n", "1", commit).split()
        if not values or values[0] != commit:
            raise ValueError("missing or ambiguous reconciliation commit")
        return values[1:]

    try:
        sync_parents = parents(candidate)
    except (PreflightError, ValueError) as exc:
        return ["reconciled-product close: " + str(exc)]
    if len(sync_parents) < 2:
        return None

    def raw_delta(old: str, new: str) -> dict[str, tuple[str, str, str, str, str, str]]:
        raw = _git(root, "diff-tree", "-r", "--raw", "-z", "--no-renames",
                   "--abbrev=40", "--no-commit-id", old, new)
        tokens = [token for token in raw.split("\0") if token]
        result: dict[str, tuple[str, str, str, str, str, str]] = {}
        if len(tokens) % 2:
            raise ValueError("malformed raw product delta")
        for header, path in zip(tokens[::2], tokens[1::2]):
            fields = header.split()
            if len(fields) != 5 or not fields[0].startswith(":"):
                raise ValueError("malformed raw product tuple")
            old_mode, new_mode = fields[0][1:], fields[1]
            old_blob, new_blob, status = fields[2:]
            if status not in {"A", "D", "M", "T"}:
                raise ValueError("raw product delta contains unexpected status")
            if (old_mode not in {"000000", "100644", "100755"}
                    or new_mode not in {"000000", "100644", "100755"}):
                raise ValueError("raw product delta contains non-regular mode")
            if path in result:
                raise ValueError("duplicate raw product path")
            result[path] = (path, path, old_mode, new_mode, old_blob, new_blob)
        return result

    def strict_receipt(ref: str) -> dict:
        path = receipt_relative_path(package)
        raw = _git(root, "show", f"{ref}:{path}")
        def unique_pairs(pairs):
            value = {}
            for key, item in pairs:
                if key in value:
                    raise ValueError("duplicate review receipt JSON key")
                value[key] = item
            return value
        try:
            value = json.loads(raw, object_pairs_hook=unique_pairs)
        except json.JSONDecodeError as exc:
            raise ValueError("malformed review receipt JSON") from exc
        if not isinstance(value, dict):
            raise ValueError("review receipt must be an object")
        return value

    def regular_record(ref: str, path: str) -> tuple[str, str]:
        raw = _git(root, "ls-tree", "-z", ref, "--", path)
        entries = [entry for entry in raw.split("\0") if entry]
        if len(entries) != 1:
            raise ValueError("fixed record is missing or ambiguous: " + path)
        metadata, separator, actual_path = entries[0].partition("\t")
        fields = metadata.split()
        if (not separator or actual_path != path or len(fields) != 3
                or fields[0] not in {"100644", "100755"}
                or fields[1] != "blob" or not SHA_RE.fullmatch(fields[2])):
            raise ValueError("fixed record must be a regular Git blob: " + path)
        return fields[0], fields[2]

    try:
        package = claim["package"]
        fixed = {receipt_relative_path(package), evidence_relative_path(package)}
        if len(sync_parents) != 2:
            raise ValueError("S must have exactly two ordered parents C,M")
        original, introduced = sync_parents
        merged_parents = parents(merged)
        if introduced != merged or len(merged_parents) != 1:
            raise ValueError("S parents must be C,M and M must have one parent")
        pre_merge = merged_parents[0]
        if _git(root, "rev-parse", f"{candidate}^{{tree}}") != _git(
            root, "rev-parse", f"{merged}^{{tree}}"
        ):
            raise ValueError("S tree must equal M tree")
        bases = _git(root, "merge-base", "--all", original, pre_merge).splitlines()
        if len(bases) != 1 or not SHA_RE.fullmatch(bases[0]):
            raise ValueError("C and M^1 require one unambiguous derived base")
        original_delta = raw_delta(bases[0], original)
        introduced_delta = raw_delta(pre_merge, merged)
        if fixed & set(original_delta) or fixed & set(introduced_delta):
            # Fixed records are excluded from the *product* comparison only.
            original_delta = {k: v for k, v in original_delta.items() if k not in fixed}
            introduced_delta = {k: v for k, v in introduced_delta.items() if k not in fixed}
        if not original_delta or original_delta != introduced_delta:
            raise ValueError("nonempty exact B..C and M^1..M product tuples must match")
        outside = _scope_errors(original_delta, claim.get("surfaces", []))
        if outside:
            raise ValueError("reconciled product is outside its claim: " + ", ".join(outside))
        if not _is_ancestor(root, merged, pinned_main):
            raise ValueError("M is not on pinned main")

        # Find the one main commit that first introduces both accepted records.
        introductions = []
        for state in _git(root, "rev-list", "--reverse", "--ancestry-path",
                          f"{merged}..{pinned_main}").splitlines():
            ps = parents(state)
            if len(ps) != 1 or not _is_ancestor(root, merged, ps[0]):
                continue
            paths = set(_git_nul(
                root, "diff-tree", "-r", "--name-only", "-z", "--no-renames",
                "--no-commit-id", ps[0], state,
            ))
            if fixed <= paths and all(
                _git_result(root, "cat-file", "-e", f"{ps[0]}:{path}").returncode
                for path in fixed
            ):
                introductions.append((state, ps[0]))
        if len(introductions) != 1:
            raise ValueError("accepted receipt/evidence introduction E is not unique")
        evidence_commit, evidence_parent = introductions[0]
        evidence_delta = raw_delta(evidence_parent, evidence_commit)
        if set(evidence_delta) != fixed:
            raise ValueError("E must introduce only fixed receipt/evidence files")
        for path in fixed:
            if evidence_delta[path][3] not in {"100644", "100755"}:
                raise ValueError("E records must be regular files")
            expected = regular_record(evidence_commit, path)
            for ref in (pinned_main, remote_tip):
                if regular_record(ref, path) != expected:
                    raise ValueError("accepted fixed record bytes changed")

        if not _is_ancestor(root, candidate, remote_tip):
            raise ValueError("S is not on preserved remote implementation branch")
        tail = []
        state = remote_tip
        while state != candidate:
            ps = parents(state)
            if len(ps) != 1:
                raise ValueError("S..R tail must be linear")
            edge = raw_delta(ps[0], state)
            if set(edge) - fixed:
                raise ValueError("S..R tail changes non-fixed files")
            tail.append(state)
            state = ps[0]
        historical = []
        intermediate_final = []
        for state in reversed(tail):
            if _git_result(root, "cat-file", "-e", f"{state}:{receipt_relative_path(package)}").returncode:
                continue
            record = strict_receipt(state)
            if record.get("candidate_sha") == original:
                historical.append((state, record))
            elif record.get("candidate_sha") == candidate:
                intermediate_final.append((state, record))
            else:
                raise ValueError("S..R contains an unexpected review receipt state")
        if len(historical) != 1:
            raise ValueError("exactly one historical C review state H is required")
        original_review = historical[0][1]
        final_review = strict_receipt(remote_tip)
        if final_review != receipt or final_review.get("candidate_sha") != candidate:
            raise ValueError("final accepted S receipt does not match remote tip")
        for label, record in (("historical", original_review), ("final", final_review)):
            failures = validate_receipt(record, claim)
            if (failures or type(record.get("schema_version")) is not int
                    or record.get("review_type") != "independent"
                    or record.get("evidence_ref") != evidence_relative_path(package)):
                raise ValueError(label + " independent PASS is invalid: " + "; ".join(failures))
        if original_review.get("reviewer_ref") != final_review.get("reviewer_ref"):
            raise ValueError("historical and final reviewers differ")
        for _, record in intermediate_final:
            failures = validate_receipt(record, claim)
            if (failures or type(record.get("schema_version")) is not int
                    or record.get("review_type") != "independent"
                    or record.get("evidence_ref") != evidence_relative_path(package)
                    or record.get("reviewer_ref") != final_review.get("reviewer_ref")):
                raise ValueError("intermediate S review receipt is invalid")
        if _git(root, "rev-parse", "origin/main") != pinned_main:
            raise ValueError("pinned main moved during reconciliation")
        if _remote_branch_tip(root, "main") != pinned_main or _remote_branch_tip(
            root, claim["branch"]
        ) != remote_tip:
            raise ValueError("remote main or implementation tip moved during reconciliation")
        return []
    except (PreflightError, ValueError, KeyError, TypeError) as exc:
        return ["reconciled-product close: " + str(exc)]


def _require_control_delta(
    *,
    root: Path,
    claim: dict,
    facts: RepoFacts,
    allowed_fields: set[str],
    errors: list[str],
) -> dict | None:
    package = str(claim.get("package", ""))
    expected_path = claim_relative_path(package)
    if set(facts.branch_paths) != {expected_path}:
        errors.append(f"control transition must change only {expected_path}")
    try:
        before = _origin_claim(root, package)
    except PreflightError as exc:
        errors.append(str(exc))
        return None
    changed = _changed_fields(before, claim)
    if not changed or not changed <= allowed_fields:
        errors.append(
            "control transition changed fields outside: "
            + ", ".join(sorted(allowed_fields))
        )
    return before


def validate_repair_admission(
    root: Path, args: argparse.Namespace, facts: RepoFacts, claim: dict
) -> tuple[dict, list[str]]:
    """Hash-bound exception to claim-only ordering, never a CI/policy waiver.

    References are auditable owner/reviewer attestations, as elsewhere in this
    tool, not cryptographic identity proof. The normal PR policies remain the
    actual server-side merge gate. No network setting or ref is changed here.
    """
    errors: list[str] = []
    result = {"server_ci": "required; not verified by local admission",
              "ordinary_activation": False}
    if facts.main_paths or getattr(facts, "behind", 0):
        errors.append("repair must start from current main without divergent main changes")
    if getattr(args, "candidate_worktree", ""):
        return result, ["repair cannot substitute another candidate worktree"]
    manifest_path = getattr(args, "repair_manifest", "")
    if not manifest_path:
        return result, ["repair requires an external approval manifest"]
    try:
        path = Path(manifest_path).resolve(strict=True)
        if path.is_relative_to(root.resolve()):
            return result, ["repair approval manifest must be outside the candidate tree"]
        manifest = _read_json(path)
    except (OSError, ValueError, PreflightError) as exc:
        return result, ["repair approval manifest cannot be read: " + str(exc)]
    if not isinstance(manifest, dict) or set(manifest) != {
        "authorization", "precommit_review", "merge_review"
    }:
        return result, ["repair approval manifest has an inexact schema"]
    authorization = manifest["authorization"]
    required = {"schema_version", "package", "writer_ref", "owner_authorization_ref",
                "failure_evidence_ref", "base_sha", "branch", "files"}
    if not isinstance(authorization, dict) or set(authorization) != required:
        return result, ["repair authorization has an inexact schema"]
    if authorization["schema_version"] != 1:
        errors.append("repair authorization schema_version must be 1")
    for field in ("writer_ref", "owner_authorization_ref", "failure_evidence_ref"):
        if not isinstance(authorization[field], str) or not REF_RE.fullmatch(authorization[field]):
            errors.append("repair authorization has invalid " + field)
    for field, expected in {
        "package": args.package, "writer_ref": args.task_ref,
        "owner_authorization_ref": getattr(args, "owner_authorization_ref", ""),
        "base_sha": facts.origin_main, "branch": facts.branch,
    }.items():
        if authorization[field] != expected:
            errors.append("repair authorization does not match " + field)
    if not SHA_RE.fullmatch(str(authorization["base_sha"])):
        errors.append("repair base must be an exact Git commit")
    if authorization["owner_authorization_ref"] == authorization["writer_ref"]:
        errors.append("repair owner authorization must be distinct from the writer")
    allowed_repository_authorities = ("through_merge",)
    if args.intent == "repair-activate":
        allowed_repository_authorities += ("write_only",)
    if (claim.get("writer_ref") != args.task_ref
            or claim.get("owner_outcome_ref") != authorization["owner_authorization_ref"]
            or claim.get("delivery_path") != "Protected"
            or claim.get("review_requirement") != "independent"
            or claim.get("repository_authority") not in allowed_repository_authorities
            or claim.get("production_authority") != "withheld"):
        errors.append("repair requires the exact owner-selected Protected independent claim")
    files = authorization["files"]
    expected_claim = claim_relative_path(args.package)
    if not isinstance(files, dict) or not files:
        return result, errors + ["repair files must be an exact nonempty blob map"]
    if expected_claim not in files or not (set(files) - {expected_claim}):
        errors.append("repair must contain its own activation claim and a gate correction")
    if set(files) - (REPAIR_SURFACES | {expected_claim}):
        errors.append("repair contains an unsupported surface; pipeline and product changes are prohibited")
    if set(facts.branch_paths) != set(files) or facts.worktree_paths:
        errors.append("repair candidate paths differ from the approved clean tree")
    if _scope_errors(files, claim.get("surfaces", [])):
        errors.append("repair files exceed the declared claim surfaces")
    if set(claim.get("surfaces", [])) != set(files) | set(control_relative_paths(args.package)):
        errors.append("repair claim must reserve exactly approved files and fixed control surfaces")
    for filename, blob in files.items():
        try:
            canonical = normalize_path(filename) if isinstance(filename, str) else None
        except ValueError:
            canonical = None
        if (canonical != filename
                or not isinstance(blob, str) or not SHA_RE.fullmatch(blob)):
            errors.append("repair file mapping must use canonical paths and exact Git blob IDs")
            continue
        try:
            actual = _git(root, "rev-parse", f"{facts.head}:{filename}")
            mode = _git(root, "ls-tree", facts.head, "--", filename).split()[0]
        except (PreflightError, IndexError):
            errors.append("repair file cannot be resolved: " + filename)
            continue
        if actual != blob or mode != "100644":
            errors.append("repair blob or regular-file mode changed: " + filename)
    digest = hashlib.sha256(json.dumps(authorization, sort_keys=True,
        separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()
    result["authorization_sha256"] = digest
    precommit = manifest["precommit_review"]
    if not isinstance(precommit, dict) or set(precommit) != {
        "reviewer_ref", "review_ref", "result", "authorization_sha256"
    }:
        errors.append("repair requires an exact precommit review record")
    else:
        if (precommit["result"] != "pass" or precommit["authorization_sha256"] != digest
                or precommit["reviewer_ref"] in {args.task_ref, authorization["owner_authorization_ref"]}
                or not all(isinstance(precommit[k], str) and REF_RE.fullmatch(precommit[k])
                           for k in ("reviewer_ref", "review_ref"))):
            errors.append("repair precommit review must independently approve this exact manifest")
    if args.intent == "repair-merge":
        review = manifest["merge_review"]
        if not isinstance(review, dict):
            errors.append("repair merge requires the exact independent candidate receipt")
        else:
            errors.extend(validate_receipt(review, claim))
            if (review.get("candidate_sha") != facts.head
                    or getattr(args, "candidate_sha", "") != facts.head):
                errors.append("repair merge review must match exact HEAD without a post-review tail")
    elif manifest["merge_review"] is not None:
        errors.append("repair activation manifest must not preseed a merge receipt")
    return result, errors


def evaluate(
    args: argparse.Namespace, *, root: Path = ROOT
) -> tuple[dict, list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if args.intent not in REPAIR_INTENTS and getattr(args, "repair_manifest", ""):
        errors.append("repair manifest is valid only for repair admission")
    work_root = root
    if args.intent == "merge" and args.candidate_worktree:
        work_root = Path(args.candidate_worktree).resolve()
        if not work_root.is_dir():
            raise PreflightError("candidate worktree does not exist")
        verifier_common = _git_common_dir(root)
        candidate_common = _git_common_dir(work_root)
        if verifier_common != candidate_common:
            raise PreflightError("candidate worktree belongs to a different repository")

    facts = collect_repo_facts(work_root, fetch=args.fetch)
    control_root = root if args.candidate_worktree else work_root
    candidate_index = load_index(control_root)
    candidate_claims = load_claims(control_root)
    errors.extend(validate_index(candidate_index))
    _verify_legacy_snapshot(control_root, candidate_index, errors)
    package_key = args.package.casefold()
    branch_claim = candidate_claims.get(package_key)
    bootstrap = False
    authority_claims_for_validation: dict[str, dict] | None = None
    if args.intent == "read":
        authority_claims = candidate_claims
    else:
        origin_index = load_index_at_ref(control_root, "origin/main")
        if origin_index.get("schema_version") in {
            ACTIVE_INDEX_SCHEMA,
            SAFE_CUSTODY_INDEX_SCHEMA,
        }:
            errors.extend(validate_index(origin_index))
            authority_claims = load_claims_at_ref(control_root, "origin/main")
            authority_claims_for_validation = authority_claims
            _verify_legacy_snapshot(control_root, origin_index, errors)
        else:
            bootstrap = True
            authority_claims = candidate_claims
            errors.extend(
                validate_legacy_bootstrap(
                    candidate_index, candidate_claims, origin_index, facts.origin_main
                )
            )
            for mapped_claim in candidate_claims.values():
                mapped_package = str(mapped_claim.get("package", ""))
                mapped_receipt = load_receipt(mapped_package, control_root)
                if mapped_receipt is not None:
                    errors.extend(
                        f"{mapped_package}: {error}"
                        for error in validate_receipt(mapped_receipt, mapped_claim)
                    )
            if args.intent != "merge":
                errors.append("legacy bootstrap authority is valid only for its reviewed merge")
    authority_claim = authority_claims.get(package_key)
    payload = asdict(facts)
    payload["changed_paths"] = sorted(
        set(facts.branch_paths) | set(facts.worktree_paths)
    )
    claim_set_errors, claim_set_warnings, claim_set_diagnostics = (
        validate_claim_set_admission(
            intent=args.intent,
            candidate_claims=candidate_claims,
            authority_claims=authority_claims_for_validation,
        )
    )
    errors.extend(claim_set_errors)
    warnings.extend(claim_set_warnings)
    payload.update(claim_set_diagnostics)

    parsed_origin = urlparse(facts.origin_url)
    if not (
        parsed_origin.scheme == "https"
        and parsed_origin.hostname == "dev.azure.com"
        and parsed_origin.path.rstrip("/").casefold() == AZURE_ORIGIN_PATH.casefold()
        and not parsed_origin.query
        and not parsed_origin.fragment
    ):
        errors.append("origin is not the authoritative Azure DevOps remote")
    if args.intent in MUTATING_INTENTS and not facts.branch:
        errors.append("mutating intents require an attached branch")
    if args.intent in MUTATING_INTENTS and not args.fetch:
        errors.append(f"{args.intent} requires --fetch")
    if args.intent in MUTATING_INTENTS and not args.require_clean:
        errors.append(f"{args.intent} requires --require-clean")
    if args.require_clean and not facts.clean:
        errors.append("checkout is not clean")
    owner_authorization_ref = getattr(args, "owner_authorization_ref", "")
    if owner_authorization_ref and args.intent not in {
        "evidence-errata",
        "owner-reassignment",
        "supersede",
        *REPAIR_INTENTS,
    }:
        errors.append(
            "--owner-authorization-ref is valid only for evidence-errata, "
            "owner-reassignment, supersede, or repair admission"
        )

    if args.intent == "read":
        try:
            context_id = lifecycle_registry._caller_context_identifier(
                getattr(args, "caller_context", "")
            )
        except lifecycle_registry.Refusal as exc:
            errors.append("caller identity: " + str(exc))
            context_id = ""
        if context_id:
            registry_context, registry_errors, registry_warnings = (
                evaluate_local_worktree_context(
                    root=work_root,
                    args=args,
                    claim=branch_claim
                    or authority_claim
                    or {"package": args.package},
                    facts=facts,
                )
            )
            payload["worktree_registry"] = registry_context
            errors.extend(registry_errors)
            warnings.extend(registry_warnings)
        return payload, errors, warnings
    if args.intent == "grant":
        errors.append(
            "grant is retired: an implementation claim already carries repository "
            "authority through merge; Protected review is proved by its receipt"
        )
        return payload, errors, warnings
    if args.intent == "release":
        errors.append(
            "repository claims cannot authorize production; use the manual exact-SHA "
            "production operation preflight with an owner authorization reference"
        )
        return payload, errors, warnings
    if authority_claim is None and args.intent not in CONTROL_INTENTS:
        errors.append(f"no claim exists for {args.package}")
        return payload, errors, warnings

    claim = branch_claim if args.intent in CONTROL_INTENTS else authority_claim
    if claim is None:
        errors.append(f"no branch claim exists for {args.package}")
        return payload, errors, warnings
    if args.intent in {"write", "merge"} and not bootstrap:
        if branch_claim is None or _changed_fields(authority_claim, branch_claim):
            errors.append("branch claim differs from authoritative origin/main")

    registry_context, registry_errors, registry_warnings = (
        evaluate_local_worktree_context(
            root=work_root,
            args=args,
            claim=claim,
            facts=facts,
        )
    )
    payload["worktree_registry"] = registry_context
    errors.extend(registry_errors)
    warnings.extend(registry_warnings)
    safe_custody_registry = registry_context.pop(
        "_safe_custody_registry_snapshot", None
    )
    if args.intent == "extend-surfaces" and (
        registry_context.get("registry") != "initialized"
        or registry_context.get("enforced") is not True
        or registry_context.get("current_kind") != "control_singleton"
    ):
        errors.append("surface extension requires a proved leased _control singleton")
    if args.intent == "owner-reassignment" and (
        registry_context.get("registry") != "initialized"
        or registry_context.get("enforced") is not True
        or registry_context.get("current_kind") != "control_singleton"
        or registry_context.get("owner_reassignment_preparation_valid") is not True
    ):
        errors.append(
            "owner reassignment requires an initialized leased control singleton "
            "and exact completed preparation proof"
        )

    if args.intent == "activate" or args.intent in REPAIR_INTENTS:
        if not ACTIVATION_BRANCH_RE.fullmatch(facts.branch):
            errors.append("activation requires the delivery-activation branch pattern")
        if claim.get("state") != "active":
            errors.append("activation must create a fresh active claim")
        seeded_history = [
            field
            for field in ("checkpoint_sha", "merged_sha", "closed_at", "handoff")
            if claim.get(field) is not None
        ]
        if seeded_history:
            errors.append(
                "activation may not preseed lifecycle history: "
                + ", ".join(seeded_history)
            )
        origin_claims = authority_claims
        added = sorted(set(candidate_claims) - set(origin_claims))
        removed = sorted(set(origin_claims) - set(candidate_claims))
        changed = sorted(
            key
            for key in set(origin_claims) & set(candidate_claims)
            if _changed_fields(origin_claims[key], candidate_claims[key])
        )
        if added != [package_key] or removed or changed:
            errors.append("activation must add exactly one claim and preserve all others")
        expected = claim_relative_path(args.package)
        if args.intent == "activate" and set(facts.branch_paths) != {expected}:
            errors.append(f"activation must change only {expected}")
        if claim.get("activated_from_main") != facts.origin_main:
            errors.append("new claim activated_from_main must equal current origin/main")
        if claim.get("branch") == facts.branch:
            errors.append("activation and implementation branches must differ")
        if args.intent in REPAIR_INTENTS:
            if registry_context.get("registry") != "initialized":
                errors.append("repair requires the initialized receiver-leased control singleton")
            if not getattr(args, "lease_token", ""):
                errors.append("repair requires an explicit current lease token")
            repair_facts, repair_errors = validate_repair_admission(
                work_root, args, facts, claim
            )
            payload["repair_admission"] = repair_facts
            errors.extend(repair_errors)

    elif args.intent == "authorize":
        if (
            not CONTROL_BRANCH_RE.fullmatch(facts.branch)
            or "-authorize-" not in facts.branch
        ):
            errors.append("authority transition requires a delivery-authorize control branch")
        before = _require_control_delta(
            root=root,
            claim=claim,
            facts=facts,
            allowed_fields={"repository_authority", "owner_outcome_ref"},
            errors=errors,
        )
        if before and before.get("state") != "active":
            errors.append("authority transition requires an active origin claim")
        if before and before.get("repository_authority") != "write_only":
            errors.append("authority transition requires an explicitly narrowed write_only claim")
        if claim.get("repository_authority") != "through_merge":
            errors.append("authority transition must set repository_authority to through_merge")
        owner_ref = claim.get("owner_outcome_ref")
        if before and owner_ref == before.get("owner_outcome_ref"):
            errors.append("authority transition requires a new owner_outcome_ref")
        if not isinstance(owner_ref, str) or not REF_RE.fullmatch(owner_ref):
            errors.append(
                "authority transition owner_outcome_ref must be an opaque "
                "task/session/agent/role reference"
            )

    elif args.intent == "extend-surfaces":
        if (
            not CONTROL_BRANCH_RE.fullmatch(facts.branch)
            or "-extend-surfaces-" not in facts.branch
        ):
            errors.append(
                "surface extension requires a delivery-extend-surfaces control branch"
            )
        before = _require_control_delta(
            root=root,
            claim=claim,
            facts=facts,
            allowed_fields={"surfaces"},
            errors=errors,
        )
        if facts.behind:
            errors.append("surface extension requires a branch from current origin/main")
        if before and before.get("state") != "active":
            errors.append("surface extension requires an active origin claim")
        if before and (
            not args.task_ref
            or args.task_ref != before.get("writer_ref")
            or claim.get("writer_ref") != before.get("writer_ref")
        ):
            errors.append(
                "surface extension task context must equal the target claim writer_ref"
            )

        before_surfaces = before.get("surfaces") if before else None
        after_surfaces = claim.get("surfaces")
        additions: list[str] = []
        if not isinstance(before_surfaces, list) or not isinstance(after_surfaces, list):
            errors.append("surface extension requires valid surface lists")
        elif (
            len(after_surfaces) <= len(before_surfaces)
            or after_surfaces[: len(before_surfaces)] != before_surfaces
        ):
            errors.append(
                "surface extension must append to surfaces without removal, replacement, or reorder"
            )
        else:
            additions = after_surfaces[len(before_surfaces) :]

        broad = [
            path
            for path in additions
            if extension_surface_is_broad(root, "origin/main", path)
        ]
        if broad:
            errors.append(
                "surface extension additions must be exact file paths, not broad paths: "
                + ", ".join(repr(path) for path in broad)
            )

        same_claim_collisions: list[tuple[str, str]] = []
        for index, addition in enumerate(additions):
            for existing in [*before_surfaces, *additions[:index]]:
                try:
                    overlaps = paths_overlap(addition, existing)
                except ValueError:
                    continue
                if overlaps:
                    same_claim_collisions.append((addition, existing))
        if same_claim_collisions:
            errors.append(
                "surface extension additions overlap the target claim: "
                + repr(same_claim_collisions)
            )

        prospective_claims = dict(authority_claims)
        prospective_claims[package_key] = claim
        errors.extend(
            "surface extension prospective state: " + error
            for error in validate_claim_set(prospective_claims)
        )

    elif args.intent == "release-surfaces":
        if (
            not CONTROL_BRANCH_RE.fullmatch(facts.branch)
            or "-release-surfaces-" not in facts.branch
        ):
            errors.append(
                "scope release requires a delivery-release-surfaces control branch"
            )
        before = _require_control_delta(
            root=root,
            claim=claim,
            facts=facts,
            allowed_fields={"surfaces", "domains", "scope_release"},
            errors=errors,
        )
        if candidate_index.get("schema_version") != SAFE_CUSTODY_INDEX_SCHEMA:
            errors.append("scope release remains disabled before index schema 4")
        if registry_context.get("schema_version") != SAFE_CUSTODY_REGISTRY_SCHEMA:
            errors.append("scope release remains disabled before registry schema 2")
        if facts.behind:
            errors.append("scope release requires a branch from current origin/main")
        if before and before.get("state") != ACTIVE_STATE:
            errors.append("scope release requires an active origin claim")
        if before and (
            not args.task_ref
            or args.task_ref != before.get("writer_ref")
            or claim.get("writer_ref") != before.get("writer_ref")
        ):
            errors.append("scope release task context must equal the active writer_ref")
        if before:
            errors.extend(
                validate_scope_release_transition(
                    before,
                    claim,
                    registry=safe_custody_registry
                    if isinstance(safe_custody_registry, dict)
                    else None,
                    root=root,
                )
            )
        prospective_claims = dict(authority_claims)
        prospective_claims[package_key] = claim
        errors.extend(
            "scope release prospective state: " + error
            for error in validate_claim_set(prospective_claims)
        )

    elif args.intent == "write":
        if claim.get("state") != ACTIVE_STATE:
            errors.append("write requires an active claim")
        if claim.get("assignment") != "implementation":
            errors.append("review-only claims cannot write implementation surfaces")
        if claim.get("repository_authority") not in REPOSITORY_AUTHORITIES:
            errors.append("claim does not carry repository write authority")
        if facts.branch != claim.get("branch"):
            errors.append("checkout branch does not match the package claim")
        outside = _scope_errors(payload["changed_paths"], claim.get("surfaces", []))
        if outside:
            errors.append("branch changes paths outside the claim: " + ", ".join(outside))
        collisions = colliding_movement_paths(
            facts.branch_paths, facts.main_paths, claim.get("surfaces", [])
        )
        if collisions:
            errors.append("current main moved across a branch path: " + repr(collisions))

    elif args.intent == "transfer":
        if not CONTROL_BRANCH_RE.fullmatch(facts.branch) or "-transfer-" not in facts.branch:
            errors.append("transfer requires a delivery-transfer control branch")
        before = _require_control_delta(
            root=root,
            claim=claim,
            facts=facts,
            allowed_fields={"writer_ref", "handoff"},
            errors=errors,
        )
        handoff = claim.get("handoff")
        if before and before.get("state") != "active":
            errors.append("only an active claim can transfer")
        expected_handoff_fields = {
            "from_ref", "to_ref", "checkpoint_sha", "relinquished"
        }
        if not isinstance(handoff, dict) or set(handoff) != expected_handoff_fields:
            errors.append("transfer requires only from_ref, to_ref, checkpoint_sha, and relinquished")
        elif before:
            from_ref = handoff.get("from_ref")
            to_ref = handoff.get("to_ref")
            if handoff.get("relinquished") is not True:
                errors.append("transfer requires explicit relinquishment")
            if from_ref != before.get("writer_ref") or to_ref != claim.get("writer_ref"):
                errors.append("handoff from_ref/to_ref must match the writer transition")
            if from_ref == to_ref:
                errors.append("transfer must change the writer_ref")
            if not all(isinstance(ref, str) and REF_RE.fullmatch(ref) for ref in (from_ref, to_ref)):
                errors.append("handoff references must be opaque task/session/agent/role refs")
            branch = str(before.get("branch", ""))
            _git(root, "fetch", "origin", f"+refs/heads/{branch}:refs/remotes/origin/{branch}")
            remote_tip = _git(root, "rev-parse", f"refs/remotes/origin/{branch}")
            if handoff.get("checkpoint_sha") != remote_tip:
                errors.append("transfer checkpoint_sha must equal the fetched branch tip")

    elif args.intent == "owner-reassignment":
        if not OWNER_REASSIGNMENT_CONTROL_BRANCH_RE.fullmatch(facts.branch):
            errors.append(
                "owner reassignment requires a delivery-owner-reassignment control branch"
            )
        before = _require_control_delta(
            root=root,
            claim=claim,
            facts=facts,
            allowed_fields={"writer_ref", "branch", "handoff"},
            errors=errors,
        )
        if facts.behind:
            errors.append("owner reassignment requires a branch from current origin/main")
        if before and before.get("state") != "active":
            errors.append("owner reassignment requires an active origin claim")
        if before and _changed_fields(before, claim) != {
            "writer_ref",
            "branch",
            "handoff",
        }:
            errors.append(
                "owner reassignment must change exactly writer_ref, branch, and handoff"
            )

        handoff = claim.get("handoff")
        if not isinstance(handoff, dict) or set(handoff) != OWNER_REASSIGNMENT_FIELDS:
            errors.append("owner reassignment requires the exact owner_reassignment handoff")
        elif before:
            from_ref = handoff.get("from_ref")
            to_ref = handoff.get("to_ref")
            from_branch = handoff.get("from_branch")
            to_branch = handoff.get("to_branch")
            checkpoint = str(handoff.get("checkpoint_sha", ""))
            owner_ref = handoff.get("owner_authorization_ref")

            if handoff.get("type") != "owner_reassignment":
                errors.append("owner reassignment handoff type must be owner_reassignment")
            if "relinquished" in handoff:
                errors.append("owner reassignment may not assert relinquishment")
            if from_ref != before.get("writer_ref") or to_ref != claim.get("writer_ref"):
                errors.append(
                    "owner reassignment from_ref/to_ref must match the writer transition"
                )
            if from_ref == to_ref:
                errors.append("owner reassignment must change the writer_ref")
            if from_branch != before.get("branch") or to_branch != claim.get("branch"):
                errors.append(
                    "owner reassignment from_branch/to_branch must match the branch transition"
                )
            if from_branch == to_branch:
                errors.append("owner reassignment requires a distinct successor branch")
            if not args.task_ref or args.task_ref != to_ref:
                errors.append(
                    "owner reassignment task context must equal the receiving writer_ref"
                )
            if not owner_authorization_ref or owner_authorization_ref != owner_ref:
                errors.append(
                    "owner reassignment requires the exact recorded owner authorization reference"
                )

            old_tip: str | None = None
            successor_tip: str | None = None
            try:
                old_tip = _exact_fetch_origin_branch(root, str(from_branch))
            except PreflightError as exc:
                errors.append("owner reassignment old-branch proof failed: " + str(exc))
            if old_tip is None:
                errors.append("owner reassignment requires the preserved old remote branch")
            elif old_tip != checkpoint:
                errors.append(
                    "owner reassignment checkpoint_sha must equal the exact fetched old branch tip"
                )

            try:
                successor_tip = _exact_fetch_origin_branch(root, str(to_branch))
            except PreflightError as exc:
                errors.append("owner reassignment successor-branch proof failed: " + str(exc))
            if successor_tip is None:
                errors.append(
                    "owner reassignment requires the prepared successor remote branch"
                )
            elif successor_tip != checkpoint:
                errors.append(
                    "owner reassignment successor branch must equal the recorded checkpoint"
                )

            try:
                final_old_tip = _exact_fetch_origin_branch(root, str(from_branch))
            except PreflightError as exc:
                errors.append(
                    "owner reassignment final old-branch proof failed: " + str(exc)
                )
            else:
                if final_old_tip != checkpoint:
                    errors.append(
                        "owner reassignment old branch moved during successor proof"
                    )

        prospective_claims = dict(authority_claims)
        prospective_claims[package_key] = claim
        errors.extend(
            "owner reassignment prospective state: " + error
            for error in validate_claim_set(prospective_claims)
        )

    elif args.intent == "pause":
        if not CONTROL_BRANCH_RE.fullmatch(facts.branch) or "-pause-" not in facts.branch:
            errors.append("pause requires a delivery-pause control branch")
        before = _require_control_delta(
            root=root,
            claim=claim,
            facts=facts,
            allowed_fields={"state", "checkpoint_sha"},
            errors=errors,
        )
        if before and before.get("state") != "active":
            errors.append("pause requires an active origin claim")
        if claim.get("state") != "paused":
            errors.append("pause must set state to paused")
        branch = str(claim.get("branch", ""))
        if branch:
            _git(root, "fetch", "origin", f"+refs/heads/{branch}:refs/remotes/origin/{branch}")
            remote_tip = _git(root, "rev-parse", f"refs/remotes/origin/{branch}")
            if claim.get("checkpoint_sha") != remote_tip:
                errors.append("pause checkpoint_sha must equal the fetched branch tip")

    elif args.intent == "resume":
        if not CONTROL_BRANCH_RE.fullmatch(facts.branch) or "-resume-" not in facts.branch:
            errors.append("resume requires a delivery-resume control branch")
        before = _require_control_delta(
            root=root,
            claim=claim,
            facts=facts,
            allowed_fields={"state"},
            errors=errors,
        )
        if before and before.get("state") != "paused":
            errors.append("resume requires a paused origin claim")
        if claim.get("state") != "active":
            errors.append("resume must set state to active")
        prospective_claims = dict(authority_claims)
        prospective_claims[package_key] = claim
        errors.extend(
            "resume prospective state: " + error
            for error in validate_claim_set(prospective_claims)
        )
        branch = str(claim.get("branch", ""))
        if before and branch:
            try:
                _git(
                    root,
                    "fetch",
                    "origin",
                    f"+refs/heads/{branch}:refs/remotes/origin/{branch}",
                )
                remote_tip = _git(root, "rev-parse", f"refs/remotes/origin/{branch}")
            except PreflightError as exc:
                errors.append(
                    "resume requires the preserved remote checkpoint branch: "
                    + str(exc)
                )
            else:
                if before.get("checkpoint_sha") != remote_tip:
                    errors.append(
                        "resume checkpoint_sha must equal the fetched branch tip"
                    )

    elif args.intent == "close":
        if not CONTROL_BRANCH_RE.fullmatch(facts.branch) or "-close-" not in facts.branch:
            errors.append("close requires a delivery-close control branch")
        before = _require_control_delta(
            root=root,
            claim=claim,
            facts=facts,
            allowed_fields={"state", "merged_sha", "closed_at"},
            errors=errors,
        )
        if before and before.get("state") not in {"active", "paused"}:
            errors.append("close requires an active or paused origin claim")
        if claim.get("state") != "closed":
            errors.append("close must set state to closed")
        merged_sha = str(claim.get("merged_sha", ""))
        if SHA_RE.fullmatch(merged_sha) and not _is_ancestor(root, merged_sha, facts.origin_main):
            errors.append("closed claim merged_sha is not on current origin/main")
        if before and SHA_RE.fullmatch(merged_sha):
            receipt = load_receipt_at_ref(root, "origin/main", args.package)
            if receipt is None:
                errors.append("close requires the merged package review receipt on origin/main")
            else:
                errors.extend(validate_receipt(receipt, before))
                candidate_sha = str(receipt.get("candidate_sha", ""))
                if SHA_RE.fullmatch(candidate_sha):
                    branch = str(before.get("branch", ""))
                    remote_tip = ""
                    try:
                        _git(
                            root,
                            "fetch",
                            "origin",
                            f"+refs/heads/{branch}:refs/remotes/origin/{branch}",
                        )
                        remote_tip = _git(
                            root, "rev-parse", f"refs/remotes/origin/{branch}"
                        )
                    except PreflightError as exc:
                        errors.append(
                            "close requires the preserved remote implementation "
                            "branch; re-push the exact reviewed branch, then retry: "
                            + str(exc)
                        )
                    candidate_on_remote = bool(remote_tip) and _is_ancestor(
                        root, candidate_sha, remote_tip
                    )
                    if remote_tip and not candidate_on_remote:
                        errors.append(
                            "preserved remote branch does not contain the reviewed "
                            "candidate"
                        )
                    if candidate_on_remote:
                        base = _git(root, "merge-base", candidate_sha, merged_sha)
                        candidate_paths = _diff_paths(
                            root, f"{base}..{candidate_sha}"
                        )
                        review_tail_paths = {
                            *before.get("evidence_surfaces", []),
                            receipt_relative_path(args.package),
                        }
                        candidate_paths = tuple(
                            path
                            for path in candidate_paths
                            if path not in review_tail_paths
                        )
                        merged_paths = _diff_paths(
                            root, f"{merged_sha}^..{merged_sha}"
                        )
                        if not candidate_paths:
                            reconciled = _reconciled_product_close_errors(
                                root, before, receipt, candidate_sha, merged_sha,
                                remote_tip, facts.origin_main,
                            )
                            if reconciled is None:
                                errors.extend(_operations_only_close_errors(
                                    root, before, receipt, candidate_sha, merged_sha,
                                    remote_tip, merged_paths,
                                ))
                            else:
                                errors.extend(reconciled)
                        outside = _scope_errors(
                            candidate_paths, before.get("surfaces", [])
                        )
                        tolerated = HISTORICAL_BOOTSTRAP_CLOSE_TOLERATED_PATHS.get(
                            (
                                str(before.get("package", "")),
                                candidate_sha,
                                merged_sha,
                            ),
                            frozenset(),
                        )
                        outside = [
                            path for path in outside if path not in tolerated
                        ]
                        if outside:
                            errors.append(
                                "reviewed close candidate is outside its claim: "
                                + ", ".join(outside)
                            )
                        if not set(candidate_paths) <= set(merged_paths):
                            errors.append(
                                "merged_sha did not introduce every reviewed candidate path"
                            )
                        mismatched = [
                            path
                            for path in candidate_paths
                            if _git_result(
                                root,
                                "diff",
                                "--quiet",
                                candidate_sha,
                                merged_sha,
                                "--",
                                path,
                            ).returncode
                        ]
                        if mismatched:
                            errors.append(
                                "merged_sha does not contain reviewed candidate bytes: "
                                + ", ".join(mismatched)
                            )

    elif args.intent == "supersede":
        # PS-DELIVERY-SUPERSEDE-DISPOSITION-001: terminal unmerged
        # disposition. Only a paused claim with a preserved pushed checkpoint,
        # no accepted review receipt on origin/main, and no merged history may
        # take it, and only with the owner's explicit authorization reference.
        if (
            not CONTROL_BRANCH_RE.fullmatch(facts.branch)
            or "-supersede-" not in facts.branch
        ):
            errors.append("supersede requires a delivery-supersede control branch")
        if not isinstance(owner_authorization_ref, str) or not REF_RE.fullmatch(
            owner_authorization_ref
        ):
            errors.append(
                "supersede requires --owner-authorization-ref as an opaque "
                "task/session/agent/role reference"
            )
        before = _require_control_delta(
            root=root,
            claim=claim,
            facts=facts,
            allowed_fields={"state", "superseded_at", "supersession"},
            errors=errors,
        )
        if before and before.get("state") != "paused":
            errors.append(
                "supersede requires a paused origin claim with a preserved "
                "checkpoint"
            )
        if claim.get("state") != "superseded":
            errors.append("supersede must set state to superseded")
        supersession = claim.get("supersession")
        if (
            isinstance(supersession, dict)
            and isinstance(owner_authorization_ref, str)
            and REF_RE.fullmatch(owner_authorization_ref)
            and supersession.get("owner_authorization_ref")
            != owner_authorization_ref
        ):
            errors.append(
                "supersession owner_authorization_ref must equal "
                "--owner-authorization-ref"
            )
        if load_receipt_at_ref(root, "origin/main", args.package) is not None:
            errors.append(
                "supersede refuses a package with an accepted review receipt; "
                "a reviewed package uses the ordinary merge and close path"
            )
        if isinstance(supersession, dict):
            for replacement in supersession.get("superseded_by") or []:
                target = authority_claims.get(str(replacement).casefold())
                if not isinstance(target, dict) or target.get("state") != "closed":
                    errors.append(
                        "supersession replacement must be a closed claim on "
                        f"origin/main: {replacement}"
                    )
        checkpoint = str(before.get("checkpoint_sha", "")) if before else ""
        branch = str(before.get("branch", "")) if before else ""
        if before and branch and SHA_RE.fullmatch(checkpoint):
            try:
                _git(
                    root,
                    "fetch",
                    "origin",
                    f"+refs/heads/{branch}:refs/remotes/origin/{branch}",
                )
                remote_tip = _git(
                    root, "rev-parse", f"refs/remotes/origin/{branch}"
                )
            except PreflightError as exc:
                errors.append(
                    "supersede requires the preserved remote checkpoint branch: "
                    + str(exc)
                )
            else:
                if checkpoint != remote_tip:
                    errors.append(
                        "supersede checkpoint_sha must equal the fetched branch tip"
                    )
                if _is_ancestor(root, checkpoint, facts.origin_main):
                    errors.append(
                        "supersede refuses a checkpoint already reachable from "
                        "origin/main; a merged package uses the ordinary close path"
                    )
        prospective_claims = dict(authority_claims)
        prospective_claims[package_key] = claim
        errors.extend(
            "supersede prospective state: " + error
            for error in validate_claim_set(prospective_claims)
        )

    elif args.intent == "evidence-errata":
        # PS-CLOSED-CLAIM-EVIDENCE-ERRATA-001: owner-authorized amendment of
        # the one fixed runtime-inert evidence file of an already CLOSED
        # package, without reopening or mutating any claim. Every gate fails
        # closed. Admitting the evidence-only PR is ALL this intent grants:
        # it never deploys, never changes claim state, and confers no
        # repository or production authority beyond that single admission.
        if not EVIDENCE_ERRATA_BRANCH_RE.fullmatch(facts.branch):
            errors.append(
                "evidence errata requires the delivery-evidence-errata "
                "control branch pattern"
            )
        if not isinstance(owner_authorization_ref, str) or not REF_RE.fullmatch(
            owner_authorization_ref
        ):
            errors.append(
                "evidence errata requires --owner-authorization-ref as an "
                "opaque task/session/agent/role reference"
            )
        if authority_claim is None:
            errors.append(
                f"no authoritative claim exists on origin/main for {args.package}"
            )
            return payload, errors, warnings
        if authority_claim.get("state") != "closed":
            errors.append("evidence errata applies only to a closed claim")
        if branch_claim is None or _changed_fields(authority_claim, branch_claim):
            errors.append(
                "evidence errata must not reopen or mutate the closed claim"
            )
        added = sorted(set(candidate_claims) - set(authority_claims))
        removed = sorted(set(authority_claims) - set(candidate_claims))
        changed = sorted(
            key
            for key in set(authority_claims) & set(candidate_claims)
            if _changed_fields(authority_claims[key], candidate_claims[key])
        )
        if added or removed or changed:
            errors.append("evidence errata must not add, remove, or change any claim")
        expected = evidence_relative_path(args.package)
        evidence_surfaces = authority_claim.get("evidence_surfaces")
        fixed_surface = None
        if isinstance(evidence_surfaces, list) and len(evidence_surfaces) == 1:
            try:
                fixed_surface = normalize_path(str(evidence_surfaces[0]))
            except ValueError:
                fixed_surface = None
        if fixed_surface != expected:
            errors.append(
                "evidence errata requires the claim's single fixed evidence "
                f"surface to be exactly {expected}"
            )
            return payload, errors, warnings
        if set(facts.branch_paths) != {expected}:
            errors.append(f"evidence errata must change only {expected}")
        if facts.ahead != 1 or facts.behind != 0:
            errors.append(
                "evidence errata must be exactly one commit ahead of current "
                "origin/main and zero behind"
            )
        for ref, label in (
            ("origin/main", "origin/main"),
            (facts.head, "the candidate"),
        ):
            if not _tracked_regular_blob(work_root, ref, expected):
                errors.append(
                    f"evidence path is not one ordinary tracked file at {label}"
                )
        marker = (
            f"<!-- evidence-errata-authorization: {owner_authorization_ref} -->"
        )
        head_show = _git_result(work_root, "show", f"{facts.head}:{expected}")
        origin_show = _git_result(work_root, "show", f"origin/main:{expected}")
        if head_show.returncode or marker not in head_show.stdout:
            errors.append(
                "amended evidence must contain the exact evidence-errata "
                "authorization marker for the supplied owner reference"
            )
        if not origin_show.returncode and marker in origin_show.stdout:
            errors.append(
                "origin/main already contains this exact authorization marker"
            )

    elif args.intent == "merge":
        if claim.get("state") != ACTIVE_STATE:
            errors.append("merge requires an active claim")
        if claim.get("assignment") != "implementation":
            errors.append("review-only claims cannot merge implementation work")
        if claim.get("repository_authority") != "through_merge":
            errors.append("claim does not carry repository authority through merge")
        if facts.branch != claim.get("branch"):
            errors.append("candidate branch does not match the package claim")
        branch = str(claim.get("branch", ""))
        _git(work_root, "fetch", "origin", f"+refs/heads/{branch}:refs/remotes/origin/{branch}")
        remote_tip = _git(work_root, "rev-parse", f"refs/remotes/origin/{branch}")
        if facts.head != remote_tip:
            errors.append("candidate worktree HEAD must equal the fetched remote branch tip")

        receipt = load_receipt(args.package, work_root)
        if receipt is None and args.candidate_worktree:
            receipt = load_receipt(args.package, root)
        if receipt is None:
            errors.append("merge requires the package review receipt")
            candidate_sha = args.candidate_sha or ""
        else:
            errors.extend(validate_receipt(receipt, claim))
            candidate_sha = args.candidate_sha or str(receipt.get("candidate_sha", ""))
            if candidate_sha != receipt.get("candidate_sha"):
                errors.append("requested candidate SHA does not match the review receipt")
        if SHA_RE.fullmatch(candidate_sha):
            if not _is_ancestor(work_root, candidate_sha, facts.head):
                errors.append("reviewed candidate SHA is not an ancestor of branch HEAD")
            else:
                base = _git(work_root, "merge-base", candidate_sha, facts.origin_main)
                candidate_paths = _diff_paths(work_root, f"{base}..{candidate_sha}")
                post_review_paths = _diff_paths(
                    work_root, f"{candidate_sha}..{facts.head}"
                )
                main_paths = _diff_paths(work_root, f"{base}..{facts.origin_main}")
                payload["candidate_sha"] = candidate_sha
                payload["candidate_base_sha"] = base
                payload["candidate_paths"] = list(candidate_paths)
                payload["post_review_paths"] = list(post_review_paths)
                payload["main_movement_paths"] = list(main_paths)
                candidate_surfaces = list(claim.get("surfaces", []))
                if bootstrap:
                    for item in candidate_claims.values():
                        mapped_package = str(item.get("package", ""))
                        candidate_surfaces.extend(
                            (
                                claim_relative_path(mapped_package),
                                receipt_relative_path(mapped_package),
                            )
                        )
                outside = _scope_errors(candidate_paths, candidate_surfaces)
                if outside:
                    errors.append(
                        "reviewed candidate changes paths outside the claim: "
                        + ", ".join(outside)
                    )
                evidence_allowed = [
                    *claim.get("evidence_surfaces", []),
                    receipt_relative_path(args.package),
                ]
                post_outside = _scope_errors(post_review_paths, evidence_allowed)
                if post_outside:
                    errors.append(
                        "post-review changes are not evidence-only: "
                        + ", ".join(post_outside)
                    )
                collisions = colliding_movement_paths(
                    candidate_paths, main_paths, claim.get("surfaces", [])
                )
                if collisions:
                    errors.append(
                        "current main moved across reviewed candidate paths: "
                        + repr(collisions)
                    )
        else:
            errors.append("merge requires one full reviewed candidate SHA")

        if args.candidate_worktree:
            verifier_facts = collect_repo_facts(root, fetch=False)
            if not verifier_facts.clean or verifier_facts.head != verifier_facts.origin_main:
                errors.append(
                    "candidate-worktree mode requires a clean verifier at current origin/main"
                )
    else:
        errors.append(f"unsupported intent {args.intent}")

    if args.intent == "owner-reassignment" and (
        "_owner_reassignment_registry_snapshot" in registry_context
    ):
        terminal_errors = _final_owner_reassignment_boundary_errors(
            root=work_root,
            args=args,
            claim=claim,
            facts=facts,
            authority_claims=authority_claims,
            registry_context=registry_context,
        )
        errors.extend(terminal_errors)
        if registry_context.get("owner_reassignment_preparation_valid") is not True:
            errors.append(
                "owner reassignment requires a coherent terminal registry, lease, "
                "preparation, claim, and remote proof"
            )

    return payload, errors, warnings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default="", help="repository checkout to validate; defaults to this script's checkout")
    parser.add_argument("--package", required=True)
    parser.add_argument(
        "--intent",
        required=True,
        choices=[
            "read",
            "activate",
            "repair-activate",
            "repair-merge",
            "authorize",
            "extend-surfaces",
            "release-surfaces",
            "write",
            "transfer",
            "owner-reassignment",
            "pause",
            "resume",
            "grant",
            "merge",
            "close",
            "supersede",
            "evidence-errata",
            "release",
        ],
    )
    parser.add_argument("--fetch", action="store_true")
    parser.add_argument("--require-clean", action="store_true")
    parser.add_argument("--candidate-sha", default="")
    parser.add_argument("--candidate-worktree", default="")
    parser.add_argument("--repair-manifest", default="",
                        help="external hash-bound owner and review manifest for repair admission")
    parser.add_argument("--lease-token", default="",
                        help="current lifecycle generation token; required after custody recovery")
    parser.add_argument(
        "--task-ref",
        default="",
        help="opaque task/session ref required by an initialized local worktree registry",
    )
    parser.add_argument(
        "--caller-context",
        default="",
        help="registered scoped external caller context; guarded children inherit it",
    )
    parser.add_argument(
        "--owner-authorization-ref",
        default="",
        help=(
            "opaque owner reference required by evidence-errata, "
            "owner-reassignment, supersede, and repair admission"
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        facts, errors, warnings = evaluate(args, root=Path(args.repo).resolve() if args.repo else ROOT)
    except (PreflightError, ValueError) as exc:
        facts = {}
        errors = [str(exc)]
        warnings = []
    result = {
        "result": "fail" if errors else "pass",
        "model": "generic_package_claims_v1",
        "package": args.package,
        "intent": args.intent,
        "facts": facts,
        "authority": {
            "repository": "through_merge_when_claimed_and_validated",
            "production": "withheld_requires_separate_manual_exact_sha_authorization",
        },
        "warnings": warnings,
        "errors": errors,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 2 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
