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
    r"(?:authorize|transfer|pause|resume|close)-[a-z0-9-]+$"
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
STATES = {"active", "paused", "closed"}
DELIVERY_PATHS = {"Routine", "Bounded", "Protected"}
ASSIGNMENTS = {"implementation"}
REPOSITORY_AUTHORITIES = {"through_merge", "write_only"}
REVIEW_REQUIREMENTS = {"self", "independent"}
MUTATING_INTENTS = {
    "activate", "authorize", "write", "transfer", "pause", "resume", "merge", "close"
}
CONTROL_INTENTS = {"activate", "authorize", "transfer", "pause", "resume", "close"}
WORKTREE_REGISTRY_REL = Path("peerslate") / "worktree_registry.json"
CI_ENVIRONMENT_KEYS = ("TF_BUILD", "CI", "GITHUB_ACTIONS", "BUILD_BUILDID")


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


def evaluate_local_worktree_context(
    *,
    root: Path,
    args: argparse.Namespace,
    claim: dict,
    facts: RepoFacts,
) -> tuple[dict, list[str], list[str]]:
    """Enforce the initialized machine-local registry for this workspace only.

    The registry is operational inventory, not repository authority. CI and a
    machine that has not initialized it remain valid. Once initialized, a new
    unregistered mutating workspace fails without making unrelated historical
    worktrees a global blocker.
    """

    context = {
        "enforced": False,
        "registry": "not_checked",
        "current_kind": None,
    }
    errors: list[str] = []
    warnings: list[str] = []
    if args.intent not in MUTATING_INTENTS:
        return context, errors, warnings
    if _is_ci_environment():
        context["registry"] = "ci_skipped"
        warnings.append("machine-local worktree registry enforcement is skipped in CI")
        return context, errors, warnings

    common_dir = _git_common_dir(root)
    registry_path = common_dir / WORKTREE_REGISTRY_REL
    context["path"] = str(registry_path)
    if not registry_path.is_file():
        context["registry"] = "not_initialized"
        warnings.append(
            "machine-local worktree registry is not initialized; "
            "run worktree_lifecycle.py init on this machine"
        )
        return context, errors, warnings

    try:
        registry = _read_json(registry_path)
    except PreflightError as exc:
        context["registry"] = "invalid"
        errors.append(str(exc))
        return context, errors, warnings
    if registry.get("schema_version") != 1 or not registry.get("initialized_at"):
        context["registry"] = "invalid"
        errors.append("machine-local worktree registry is not an initialized schema 1 registry")
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
    task_ref = getattr(args, "task_ref", "")
    if not task_ref:
        errors.append("initialized worktree registry requires --task-ref for mutating intents")
        return context, errors, warnings
    if record.get("branch") != facts.branch:
        errors.append("current worktree branch does not match its registry record")

    package = str(claim.get("package", ""))
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
        if not isinstance(lease, dict):
            errors.append("control singleton requires an active lease")
        else:
            if lease.get("purpose") != "control":
                errors.append("control singleton lease purpose must be control")
            if lease.get("task_ref") != task_ref:
                errors.append("control singleton lease belongs to another task")
            if str(lease.get("package", "")).casefold() != package.casefold():
                errors.append("control singleton lease package does not match the claim")
    return context, errors, warnings


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
    if index.get("schema_version") != 3:
        errors.append("CURRENT_LANES.json schema_version must be 3")
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
        errors.append("claim state must be active, paused, or closed")
    _string_field(claim, "outcome", errors, maximum=1200)
    assignment = claim.get("assignment")
    if assignment not in ASSIGNMENTS:
        errors.append("claims are for implementation writers; reviewers are read-only and claim-free")
    writer_ref = _string_field(claim, "writer_ref", errors, maximum=185)
    if writer_ref and not REF_RE.fullmatch(writer_ref):
        errors.append("writer_ref must be an opaque task/session/agent/role reference")
    branch = _string_field(claim, "branch", errors, maximum=200)
    if branch and (not BRANCH_RE.fullmatch(branch) or branch.endswith("/main")):
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
    handoff = claim.get("handoff")
    if handoff is not None and not isinstance(handoff, dict):
        errors.append("claim handoff must be null or an object")
    return errors


def validate_claim_set(claims: dict[str, dict]) -> list[str]:
    errors: list[str] = []
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
        if claim.get("state") in {"active", "paused"}:
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
                errors.append(
                    f"path collision: {left.get('package')}:{a} and "
                    f"{right.get('package')}:{b}"
                )
            for a, b in colliding_domains(
                left.get("domains", []), right.get("domains", [])
            ):
                errors.append(
                    f"domain collision: {left.get('package')}:{a} and "
                    f"{right.get('package')}:{b}"
                )
    return errors


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
    return {
        key
        for key in keys
        if not key.startswith("_") and before.get(key) != after.get(key)
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


def evaluate(
    args: argparse.Namespace, *, root: Path = ROOT
) -> tuple[dict, list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
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
    errors.extend(validate_claim_set(candidate_claims))
    _verify_legacy_snapshot(control_root, candidate_index, errors)
    package_key = args.package.casefold()
    branch_claim = candidate_claims.get(package_key)
    bootstrap = False
    if args.intent == "read":
        authority_claims = candidate_claims
    else:
        origin_index = load_index_at_ref(control_root, "origin/main")
        if origin_index.get("schema_version") == 3:
            errors.extend(validate_index(origin_index))
            authority_claims = load_claims_at_ref(control_root, "origin/main")
            errors.extend(validate_claim_set(authority_claims))
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

    if args.intent == "read":
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

    if args.intent == "activate":
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
        if set(facts.branch_paths) != {expected}:
            errors.append(f"activation must change only {expected}")
        if claim.get("activated_from_main") != facts.origin_main:
            errors.append("new claim activated_from_main must equal current origin/main")
        if claim.get("branch") == facts.branch:
            errors.append("activation and implementation branches must differ")

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
                        merged_paths = _diff_paths(
                            root, f"{merged_sha}^..{merged_sha}"
                        )
                        if not candidate_paths:
                            errors.append("close requires a non-empty reviewed candidate")
                        outside = _scope_errors(
                            candidate_paths, before.get("surfaces", [])
                        )
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

    return payload, errors, warnings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", required=True)
    parser.add_argument(
        "--intent",
        required=True,
        choices=[
            "read",
            "activate",
            "authorize",
            "write",
            "transfer",
            "pause",
            "resume",
            "grant",
            "merge",
            "close",
            "release",
        ],
    )
    parser.add_argument("--fetch", action="store_true")
    parser.add_argument("--require-clean", action="store_true")
    parser.add_argument("--candidate-sha", default="")
    parser.add_argument("--candidate-worktree", default="")
    parser.add_argument(
        "--task-ref",
        default="",
        help="opaque task/session ref required by an initialized local worktree registry",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        facts, errors, warnings = evaluate(args)
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
