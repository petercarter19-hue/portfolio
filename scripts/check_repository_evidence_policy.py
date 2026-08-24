"""Validate repository evidence duplication and new generated-evidence storage."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Iterable, Sequence


ROOT = Path(__file__).resolve().parents[1]
SCAN_ROOTS = (ROOT / "docs" / "initiatives", ROOT / "artifacts")
ALLOWLIST_PATH = ROOT / "docs" / "governance" / "EVIDENCE_DUPLICATE_ALLOWLIST.json"
STORAGE_MANIFEST_NAME = "EVIDENCE_STORAGE_MANIFEST.json"
INVENTORY_THRESHOLD_BYTES = 1_000_000
EXTERNAL_STORAGE_TRIGGER_BYTES = 1024**3
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
COMMIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def repository_path(path: Path, root: Path = ROOT) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def load_allowlist(path: Path = ALLOWLIST_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def collect_large_duplicate_groups(
    threshold_bytes: int,
    scan_roots: Sequence[Path] = SCAN_ROOTS,
    root: Path = ROOT,
) -> dict[str, dict]:
    by_hash: dict[str, list[Path]] = defaultdict(list)
    sizes: dict[str, int] = {}
    for scan_root in scan_roots:
        if not scan_root.exists():
            continue
        for path in sorted(scan_root.rglob("*")):
            if not path.is_file() or path.is_symlink():
                continue
            size = path.stat().st_size
            if size < threshold_bytes:
                continue
            digest = sha256_file(path)
            by_hash[digest].append(path)
            sizes[digest] = size

    return {
        digest: {
            "bytes": sizes[digest],
            "paths": sorted(repository_path(path, root) for path in paths),
        }
        for digest, paths in by_hash.items()
        if len(paths) > 1
    }


def validate_duplicate_policy(
    root: Path = ROOT,
    scan_roots: Sequence[Path] | None = None,
    allowlist_path: Path | None = None,
) -> list[str]:
    """Preserve the reviewed exact-duplicate behavior."""

    errors: list[str] = []
    scan_roots = tuple(scan_roots or (root / "docs" / "initiatives", root / "artifacts"))
    allowlist_path = allowlist_path or (
        root / "docs" / "governance" / "EVIDENCE_DUPLICATE_ALLOWLIST.json"
    )
    allowlist = load_allowlist(allowlist_path)
    threshold = allowlist.get("threshold_bytes")
    if not isinstance(threshold, int) or threshold < 1:
        return ["allowlist threshold_bytes must be a positive integer"]

    entries = allowlist.get("entries")
    if not isinstance(entries, list):
        return ["allowlist entries must be a list"]

    expected: dict[str, dict] = {}
    for index, entry in enumerate(entries):
        label = f"allowlist entry {index}"
        if not isinstance(entry, dict):
            errors.append(f"{label} must be an object")
            continue
        digest = entry.get("sha256")
        canonical = entry.get("canonical_path")
        duplicates = entry.get("duplicate_paths")
        rationale = entry.get("rationale")
        byte_count = entry.get("bytes")
        if not isinstance(digest, str) or len(digest) != 64:
            errors.append(f"{label} requires a 64-character sha256")
            continue
        if digest in expected:
            errors.append(f"duplicate allowlist sha256: {digest}")
            continue
        if not isinstance(canonical, str) or not canonical:
            errors.append(f"{label} requires canonical_path")
            continue
        if not isinstance(duplicates, list) or not duplicates or not all(
            isinstance(path, str) and path for path in duplicates
        ):
            errors.append(f"{label} requires non-empty duplicate_paths")
            continue
        if not isinstance(rationale, str) or len(rationale.strip()) < 40:
            errors.append(f"{label} requires a meaningful rationale")
        if not isinstance(byte_count, int) or byte_count < threshold:
            errors.append(f"{label} bytes must meet threshold")
        paths = sorted([canonical, *duplicates])
        if len(paths) != len(set(paths)):
            errors.append(f"{label} repeats a path")
        expected[digest] = {"bytes": byte_count, "paths": paths}

    actual = collect_large_duplicate_groups(threshold, scan_roots, root)
    for digest in sorted(set(actual) - set(expected)):
        errors.append(
            "unapproved large exact duplicate: "
            f"{digest} -> {', '.join(actual[digest]['paths'])}"
        )
    for digest in sorted(set(expected) - set(actual)):
        errors.append(f"stale allowlist entry has no exact duplicate group: {digest}")
    for digest in sorted(set(actual) & set(expected)):
        if actual[digest] != expected[digest]:
            errors.append(
                f"allowlist group mismatch for {digest}: "
                f"expected {expected[digest]}, actual {actual[digest]}"
            )
    return errors


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _safe_relative_path(value: object, label: str, errors: list[str]) -> str | None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label} requires a non-empty relative path")
        return None
    if "\\" in value:
        errors.append(f"{label} must use repository-style forward slashes")
        return None
    parsed = PurePosixPath(value)
    if parsed.is_absolute() or ".." in parsed.parts or value.startswith("/"):
        errors.append(f"{label} must stay within its declared root")
        return None
    normalized = parsed.as_posix()
    if normalized in ("", "."):
        errors.append(f"{label} requires a file path")
        return None
    return normalized


def _normalize_input_path(value: str | Path, root: Path) -> str:
    path = Path(value)
    if path.is_absolute():
        return repository_path(path, root)
    normalized = _safe_relative_path(str(value).replace("\\", "/"), "path", [])
    if normalized is None:
        raise ValueError(f"invalid repository-relative path: {value}")
    return normalized


def _valid_utc_timestamp(value: object) -> bool:
    if not isinstance(value, str) or not value.endswith("Z"):
        return False
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() == timezone.utc.utcoffset(parsed)


def _validate_actual_file(
    root: Path,
    relative_path: str,
    expected_sha256: object,
    expected_bytes: object,
    label: str,
    errors: list[str],
) -> None:
    path = (root / Path(relative_path)).resolve()
    if not _is_relative_to(path, root):
        errors.append(f"{label} escapes the repository root")
        return
    if not path.is_file() or path.is_symlink():
        errors.append(f"{label} does not name a regular repository file: {relative_path}")
        return
    actual_bytes = path.stat().st_size
    if actual_bytes != expected_bytes:
        errors.append(
            f"{label} byte mismatch for {relative_path}: "
            f"declared {expected_bytes}, actual {actual_bytes}"
        )
    if isinstance(expected_sha256, str) and SHA256_RE.fullmatch(expected_sha256):
        actual_sha256 = sha256_file(path)
        if actual_sha256 != expected_sha256:
            errors.append(
                f"{label} sha256 mismatch for {relative_path}: "
                f"declared {expected_sha256}, actual {actual_sha256}"
            )


def _validate_storage_manifest(
    manifest_path: Path,
    root: Path,
    scan_roots: Sequence[Path],
    live_full_worktree_count: int | None,
) -> tuple[list[str], set[str]]:
    errors: list[str] = []
    covered_repository_paths: set[str] = set()
    manifest_rel = repository_path(manifest_path, root)
    label = f"storage manifest {manifest_rel}"

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return [f"{label} is not readable JSON: {exc}"], set()
    if not isinstance(manifest, dict):
        return [f"{label} must contain a JSON object"], set()
    if manifest.get("schema_version") != 1:
        errors.append(f"{label} schema_version must be 1")
    evidence_set_id = manifest.get("evidence_set_id")
    if not isinstance(evidence_set_id, str) or not evidence_set_id.strip():
        errors.append(f"{label} requires evidence_set_id")
    if manifest.get("generated") is not True:
        errors.append(f"{label} generated must be true")

    storage_mode = manifest.get("storage_mode")
    if storage_mode not in ("repo_canonical", "external"):
        errors.append(f"{label} storage_mode must be repo_canonical or external")

    for field in ("source_sha", "base_sha", "final_sha"):
        value = manifest.get(field)
        if not isinstance(value, str) or not COMMIT_SHA_RE.fullmatch(value):
            errors.append(f"{label} {field} must be a 40-character lowercase Git SHA")
    if not _valid_utc_timestamp(manifest.get("verified_at")):
        errors.append(f"{label} verified_at must be an ISO-8601 UTC timestamp ending in Z")
    for field in ("retention_owner", "recovery_owner"):
        value = manifest.get(field)
        if not isinstance(value, str) or len(value.strip()) < 3:
            errors.append(f"{label} requires {field}")
    if manifest.get("complete_verified") is not True:
        errors.append(f"{label} complete_verified must be true")

    worktree_count = manifest.get("worktree_count")
    current_full = None
    projected_full = None
    if not isinstance(worktree_count, dict):
        errors.append(f"{label} requires worktree_count")
    else:
        current_full = worktree_count.get("current_full")
        projected_full = worktree_count.get("projected_full")
        if not isinstance(current_full, int) or isinstance(current_full, bool) or current_full < 1:
            errors.append(f"{label} worktree_count.current_full must be a positive integer")
            current_full = None
        if (
            not isinstance(projected_full, int)
            or isinstance(projected_full, bool)
            or projected_full < 1
        ):
            errors.append(f"{label} worktree_count.projected_full must be a positive integer")
            projected_full = None

    declared_bytes = manifest.get("declared_set_bytes")
    declared_count = manifest.get("declared_item_count")
    if not isinstance(declared_bytes, int) or isinstance(declared_bytes, bool) or declared_bytes < 0:
        errors.append(f"{label} declared_set_bytes must be a non-negative integer")
    if not isinstance(declared_count, int) or isinstance(declared_count, bool) or declared_count < 1:
        errors.append(f"{label} declared_item_count must be a positive integer")

    items = manifest.get("items")
    item_bytes = 0
    item_records: dict[str, tuple[str, int]] = {}
    if not isinstance(items, list) or not items:
        errors.append(f"{label} items must be a non-empty list")
        items = []
    for index, item in enumerate(items):
        item_label = f"{label} item {index}"
        if not isinstance(item, dict):
            errors.append(f"{item_label} must be an object")
            continue
        item_path = _safe_relative_path(item.get("path"), f"{item_label} path", errors)
        item_sha = item.get("sha256")
        item_size = item.get("bytes")
        if not isinstance(item_sha, str) or not SHA256_RE.fullmatch(item_sha):
            errors.append(f"{item_label} sha256 must be 64 lowercase hexadecimal characters")
        if not isinstance(item_size, int) or isinstance(item_size, bool) or item_size < 0:
            errors.append(f"{item_label} bytes must be a non-negative integer")
            item_size = None
        if item_path is not None:
            if item_path in item_records:
                errors.append(f"{label} repeats item path: {item_path}")
            elif isinstance(item_sha, str) and item_size is not None:
                item_records[item_path] = (item_sha, item_size)
        if item_size is not None:
            item_bytes += item_size

    if isinstance(declared_count, int) and not isinstance(declared_count, bool):
        if declared_count != len(items):
            errors.append(
                f"{label} declared_item_count is {declared_count}, actual ledger count is {len(items)}"
            )
    if isinstance(declared_bytes, int) and not isinstance(declared_bytes, bool):
        if declared_bytes != item_bytes:
            errors.append(
                f"{label} declared_set_bytes is {declared_bytes}, "
                f"actual ledger total is {item_bytes}"
            )

    manifest_parent = manifest_path.parent.resolve()
    if storage_mode == "repo_canonical":
        for item_path, (item_sha, item_size) in item_records.items():
            absolute_item = (root / Path(item_path)).resolve()
            if not _is_relative_to(absolute_item, manifest_parent):
                errors.append(
                    f"{label} repository item must be below the manifest directory: {item_path}"
                )
                continue
            if not any(_is_relative_to(absolute_item, scan_root) for scan_root in scan_roots):
                errors.append(f"{label} repository item is outside an evidence scan root: {item_path}")
                continue
            covered_repository_paths.add(item_path)
            _validate_actual_file(root, item_path, item_sha, item_size, label, errors)

    proof = manifest.get("repository_proof")
    proof_path = None
    proof_sha = None
    proof_bytes = None
    if not isinstance(proof, dict):
        errors.append(f"{label} requires repository_proof")
    else:
        proof_path = _safe_relative_path(
            proof.get("path"), f"{label} repository_proof.path", errors
        )
        proof_sha = proof.get("sha256")
        proof_bytes = proof.get("bytes")
        if not isinstance(proof_sha, str) or not SHA256_RE.fullmatch(proof_sha):
            errors.append(
                f"{label} repository_proof.sha256 must be 64 lowercase hexadecimal characters"
            )
        if not isinstance(proof_bytes, int) or isinstance(proof_bytes, bool) or proof_bytes < 0:
            errors.append(f"{label} repository_proof.bytes must be a non-negative integer")
        if proof_path is not None:
            absolute_proof = (root / Path(proof_path)).resolve()
            if not _is_relative_to(absolute_proof, manifest_parent):
                errors.append(
                    f"{label} repository proof must be below the manifest directory: {proof_path}"
                )
            elif not any(_is_relative_to(absolute_proof, scan_root) for scan_root in scan_roots):
                errors.append(f"{label} repository proof is outside an evidence scan root")
            else:
                covered_repository_paths.add(proof_path)
                _validate_actual_file(
                    root, proof_path, proof_sha, proof_bytes, f"{label} repository proof", errors
                )
                if storage_mode == "repo_canonical":
                    ledger_record = item_records.get(proof_path)
                    if ledger_record != (proof_sha, proof_bytes):
                        errors.append(
                            f"{label} repo_canonical repository_proof must match one ledger item"
                        )

    effective_worktree_count = max(
        [
            count
            for count in (current_full, projected_full, live_full_worktree_count)
            if isinstance(count, int) and not isinstance(count, bool) and count > 0
        ]
        or [1]
    )
    replicated_bytes = (
        declared_bytes * effective_worktree_count
        if isinstance(declared_bytes, int) and not isinstance(declared_bytes, bool)
        else 0
    )
    exception = manifest.get("repository_exception")
    if storage_mode == "repo_canonical" and replicated_bytes >= EXTERNAL_STORAGE_TRIGGER_BYTES:
        if not isinstance(exception, dict):
            errors.append(
                f"{label} defaults to external storage because declared_set_bytes x "
                f"full-worktree count is {replicated_bytes} bytes; repository_exception is required"
            )
        else:
            rationale = exception.get("rationale")
            review_ref = exception.get("review_ref")
            if not isinstance(rationale, str) or len(rationale.strip()) < 40:
                errors.append(f"{label} repository_exception requires a meaningful rationale")
            if not isinstance(review_ref, str) or len(review_ref.strip()) < 8:
                errors.append(f"{label} repository_exception requires a reviewed review_ref")
    elif exception is not None and not isinstance(exception, dict):
        errors.append(f"{label} repository_exception must be an object or null")

    custody = manifest.get("external_custody")
    if storage_mode == "external":
        if not isinstance(custody, dict):
            errors.append(f"{label} external storage requires external_custody")
        else:
            provider = custody.get("provider")
            coordinate = custody.get("immutable_coordinate")
            sole_custody = custody.get("sole_custody")
            retention_pinned = custody.get("retention_pinned")
            retention_ref = custody.get("retention_policy_ref")
            if not isinstance(provider, str) or not provider.strip():
                errors.append(f"{label} external_custody requires provider")
            if (
                not isinstance(coordinate, str)
                or len(coordinate.strip()) < 12
                or any(character.isspace() for character in coordinate)
            ):
                errors.append(
                    f"{label} external_custody requires a specific immutable_coordinate"
                )
            if not isinstance(sole_custody, bool):
                errors.append(f"{label} external_custody.sole_custody must be boolean")
            if not isinstance(retention_pinned, bool):
                errors.append(f"{label} external_custody.retention_pinned must be boolean")
            provider_is_azure = isinstance(provider, str) and "azure" in provider.lower()
            if provider_is_azure and sole_custody is True:
                if retention_pinned is not True:
                    errors.append(
                        f"{label} Azure sole custody requires retention_pinned true"
                    )
                if not isinstance(retention_ref, str) or len(retention_ref.strip()) < 8:
                    errors.append(
                        f"{label} Azure sole custody requires retention_policy_ref"
                    )
        if exception is not None:
            errors.append(f"{label} external storage may not declare repository_exception")
    elif custody is not None:
        errors.append(f"{label} repo_canonical storage may not declare external_custody")

    return errors, covered_repository_paths


def _normalize_paths(
    paths: Iterable[str | Path] | None,
    root: Path,
) -> tuple[set[str], list[str]]:
    normalized: set[str] = set()
    errors: list[str] = []
    for value in paths or ():
        try:
            normalized.add(_normalize_input_path(value, root))
        except ValueError as exc:
            errors.append(str(exc))
    return normalized, errors


def _nearest_storage_manifest(path: Path, scan_roots: Sequence[Path]) -> Path | None:
    current = path.parent.resolve()
    containing_roots = [root.resolve() for root in scan_roots if _is_relative_to(path, root)]
    if not containing_roots:
        return None
    boundary = max(containing_roots, key=lambda candidate: len(candidate.parts))
    while _is_relative_to(current, boundary):
        candidate = current / STORAGE_MANIFEST_NAME
        if candidate.is_file():
            return candidate
        if current == boundary:
            break
        current = current.parent
    return None


def validate_storage_policy(
    root: Path,
    scan_roots: Sequence[Path],
    changed_paths: Iterable[str | Path] | None,
    added_paths: Iterable[str | Path] | None,
    live_full_worktree_count: int | None = None,
) -> list[str]:
    """Validate only manifests and large evidence implicated by this change."""

    errors: list[str] = []
    changed, path_errors = _normalize_paths(changed_paths, root)
    errors.extend(path_errors)
    added, path_errors = _normalize_paths(added_paths, root)
    errors.extend(path_errors)
    if not changed and not added:
        return errors

    manifest_paths: set[Path] = set()
    for relative_path in changed | added:
        absolute_path = (root / Path(relative_path)).resolve()
        if absolute_path.name == STORAGE_MANIFEST_NAME and absolute_path.is_file():
            manifest_paths.add(absolute_path)
    for relative_path in added:
        absolute_path = (root / Path(relative_path)).resolve()
        if not absolute_path.is_file() or absolute_path.is_symlink():
            continue
        nearest = _nearest_storage_manifest(absolute_path, scan_roots)
        if nearest is not None:
            manifest_paths.add(nearest)

    covered_paths: set[str] = set()
    for manifest_path in sorted(manifest_paths):
        manifest_errors, manifest_coverage = _validate_storage_manifest(
            manifest_path, root, scan_roots, live_full_worktree_count
        )
        errors.extend(manifest_errors)
        covered_paths.update(manifest_coverage)

    for relative_path in sorted(added):
        absolute_path = (root / Path(relative_path)).resolve()
        if absolute_path.name == STORAGE_MANIFEST_NAME:
            continue
        if not any(_is_relative_to(absolute_path, scan_root) for scan_root in scan_roots):
            continue
        if not absolute_path.is_file() or absolute_path.is_symlink():
            continue
        if absolute_path.stat().st_size < INVENTORY_THRESHOLD_BYTES:
            continue
        if relative_path not in covered_paths:
            errors.append(
                "new large evidence is not inventoried by an "
                f"{STORAGE_MANIFEST_NAME}: {relative_path}"
            )
    return errors


def validate_policy(
    root: Path = ROOT,
    scan_roots: Sequence[Path] | None = None,
    allowlist_path: Path | None = None,
    changed_paths: Iterable[str | Path] | None = None,
    added_paths: Iterable[str | Path] | None = None,
    live_full_worktree_count: int | None = None,
    base_ref: str | None = None,
) -> list[str]:
    """Validate exact duplicates plus the current change's storage manifests."""

    root = root.resolve()
    if base_ref is not None and changed_paths is None and added_paths is None:
        changed_paths, added_paths = discover_changed_paths(root, base_ref)
    elif changed_paths is not None and added_paths is None:
        added_paths = changed_paths
    resolved_scan_roots = tuple(
        Path(path).resolve()
        for path in (
            scan_roots or (root / "docs" / "initiatives", root / "artifacts")
        )
    )
    errors = validate_duplicate_policy(root, resolved_scan_roots, allowlist_path)
    errors.extend(
        validate_storage_policy(
            root,
            resolved_scan_roots,
            changed_paths,
            added_paths,
            live_full_worktree_count,
        )
    )
    return errors


def _git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return completed.stdout


def _default_base_ref(root: Path) -> str | None:
    azure_target = os.environ.get("SYSTEM_PULLREQUEST_TARGETBRANCH")
    candidates: list[str] = []
    if azure_target:
        if azure_target.startswith("refs/heads/"):
            candidates.append("origin/" + azure_target.removeprefix("refs/heads/"))
        candidates.append(azure_target)
    candidates.extend(("origin/main", "HEAD^"))
    for candidate in candidates:
        try:
            _git(root, "rev-parse", "--verify", "--quiet", candidate)
            return candidate
        except (OSError, subprocess.CalledProcessError):
            continue
    return None


def discover_changed_paths(
    root: Path = ROOT,
    base_ref: str | None = None,
) -> tuple[set[str], set[str]]:
    """Return existing changed paths and added paths relative to a Git base."""

    selected_base = base_ref or _default_base_ref(root)
    if selected_base is None:
        return set(), set()
    merge_base = _git(root, "merge-base", selected_base, "HEAD").strip()
    output = _git(root, "diff", "--name-status", "--find-renames", merge_base, "--")
    changed: set[str] = set()
    added: set[str] = set()
    for line in output.splitlines():
        fields = line.split("\t")
        if len(fields) < 2:
            continue
        status = fields[0]
        path = fields[-1].replace("\\", "/")
        if status.startswith("D"):
            continue
        changed.add(path)
        if status.startswith(("A", "C")):
            added.add(path)
    try:
        untracked = _git(root, "ls-files", "--others", "--exclude-standard", "-z")
    except (OSError, subprocess.CalledProcessError):
        untracked = ""
    for path in untracked.split("\0"):
        if path:
            normalized = path.replace("\\", "/")
            changed.add(normalized)
            added.add(normalized)
    return changed, added


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="emit JSON")
    parser.add_argument(
        "--base-ref",
        help="validate evidence added since this Git ref (defaults to PR target/origin/main)",
    )
    parser.add_argument(
        "--changed-path",
        action="append",
        default=[],
        help="repository-relative changed path; repeat as needed",
    )
    parser.add_argument(
        "--added-path",
        action="append",
        default=[],
        help="repository-relative newly added path; repeat as needed",
    )
    parser.add_argument(
        "--full-worktree-count",
        type=int,
        help="current observed full-worktree count used in addition to manifest counts",
    )
    args = parser.parse_args()

    if args.full_worktree_count is not None and args.full_worktree_count < 1:
        errors = ["--full-worktree-count must be a positive integer"]
    else:
        errors = []
        if args.changed_path or args.added_path:
            changed_paths = set(args.changed_path) | set(args.added_path)
            added_paths = set(args.added_path or args.changed_path)
        else:
            try:
                changed_paths, added_paths = discover_changed_paths(ROOT, args.base_ref)
            except (OSError, subprocess.CalledProcessError) as exc:
                changed_paths, added_paths = set(), set()
                errors = [f"could not determine evidence diff: {exc}"]
        errors.extend(
            validate_policy(
                changed_paths=changed_paths,
                added_paths=added_paths,
                live_full_worktree_count=args.full_worktree_count,
            )
        )

    payload = {"result": "pass" if not errors else "fail", "errors": errors}
    if args.json:
        print(json.dumps(payload, indent=2))
    elif errors:
        print("\n".join(errors))
    else:
        print("repository evidence policy: pass")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
