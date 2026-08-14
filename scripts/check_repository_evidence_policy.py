"""Validate large exact-duplicate evidence against the reviewed allowlist."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCAN_ROOTS = (ROOT / "docs" / "initiatives", ROOT / "artifacts")
ALLOWLIST_PATH = ROOT / "docs" / "governance" / "EVIDENCE_DUPLICATE_ALLOWLIST.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def repository_path(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def load_allowlist(path: Path = ALLOWLIST_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def collect_large_duplicate_groups(threshold_bytes: int) -> dict[str, dict]:
    by_hash: dict[str, list[Path]] = defaultdict(list)
    sizes: dict[str, int] = {}
    for scan_root in SCAN_ROOTS:
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
            "paths": sorted(repository_path(path) for path in paths),
        }
        for digest, paths in by_hash.items()
        if len(paths) > 1
    }


def validate_policy() -> list[str]:
    errors: list[str] = []
    allowlist = load_allowlist()
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

    actual = collect_large_duplicate_groups(threshold)
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="emit JSON")
    args = parser.parse_args()
    errors = validate_policy()
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
