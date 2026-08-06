#!/usr/bin/env python3
"""Fail-fast PeerSlate lane and checkout preflight.

The script is intentionally dependency-free. It reports local Git facts and
applies the current machine-readable lane policy before a write or release.
Read-only work remains available during a delivery reset.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LEDGER_PATH = ROOT / "docs" / "governance" / "CURRENT_LANES.json"


def _git(*args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", "-C", str(ROOT), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if check and result.returncode:
        raise RuntimeError(result.stderr.strip() or "git command failed")
    return result.stdout.strip()


def load_ledger(path: Path = LEDGER_PATH) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def collect_facts(
    fetch: bool = False,
    include_changed_paths: bool = False,
) -> dict:
    if fetch:
        _git("fetch", "origin", "--prune")

    status_lines = [line for line in _git("status", "--porcelain=v1").splitlines() if line]
    tracked = [line for line in status_lines if not line.startswith("??")]
    untracked = [line for line in status_lines if line.startswith("??")]
    origin_url = _git("remote", "get-url", "origin")
    facts = {
        "repository": str(ROOT),
        "branch": _git("branch", "--show-current"),
        "head": _git("rev-parse", "HEAD"),
        "origin_main": _git("rev-parse", "origin/main"),
        "ahead": int(_git("rev-list", "--count", "origin/main..HEAD")),
        "behind": int(_git("rev-list", "--count", "HEAD..origin/main")),
        "tracked_changes": len(tracked),
        "untracked_changes": len(untracked),
        "origin_url": origin_url,
        "origin_is_azure": "dev.azure.com" in origin_url.lower(),
    }
    if include_changed_paths:
        facts["changed_paths"] = sorted(
            {
                path
                for command in (
                    ("diff", "--name-only", "origin/main...HEAD"),
                    ("diff", "--name-only"),
                    ("diff", "--cached", "--name-only"),
                    ("ls-files", "--others", "--exclude-standard"),
                )
                for path in _git(*command).splitlines()
                if path
            }
        )
    return facts


def evaluate_policy(
    ledger: dict,
    facts: dict,
    package_id: str,
    intent: str,
    require_clean: bool = False,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    mode = ledger.get("operating_mode") or {}

    if not facts.get("origin_is_azure"):
        errors.append("origin is not the authoritative Azure DevOps remote")
    if not facts.get("branch"):
        errors.append("detached HEAD is not an authorized write lane")
    if facts.get("branch") == "main" and intent != "read":
        errors.append("writes and releases may not run directly from main")
    if facts.get("behind", 0):
        errors.append(f"checkout is {facts['behind']} commit(s) behind origin/main")
    if require_clean and (
        facts.get("tracked_changes", 0) or facts.get("untracked_changes", 0)
    ):
        errors.append("checkout is not clean")

    if intent == "read":
        if not mode.get("read_only_work_allowed", False):
            errors.append("the current operating mode disallows read-only work")
        return errors, warnings

    if intent == "activate":
        policy = ledger.get("activation_policy") or {}
        state = mode.get("state")
        allowed_states = set(
            policy.get("allowed_operating_states") or ["controlled_idle"]
        )
        expected_states = {"controlled_idle", "active_delivery"}
        if allowed_states != expected_states:
            errors.append(
                "activation policy operating states must be controlled_idle "
                "and active_delivery"
            )
        elif state not in allowed_states:
            errors.append(
                "activation is allowed only from controlled_idle or "
                "active_delivery"
            )
        if not policy.get("enabled", False):
            errors.append("the lane activation policy is disabled")
        if package_id != policy.get("package"):
            errors.append(
                "activation must use the standing control package "
                f"{policy.get('package', '(unset)')}"
            )
        branch_pattern = policy.get("branch_pattern") or r"(?!)"
        if not re.fullmatch(branch_pattern, facts.get("branch") or ""):
            errors.append(
                f"activation branch does not match {branch_pattern!r}"
            )
        active_lanes = list(ledger.get("active_lanes") or [])
        if state == "controlled_idle" and active_lanes:
            errors.append("controlled_idle cannot contain active lanes")
        elif state == "active_delivery" and not active_lanes:
            errors.append("active_delivery must contain an existing active lane")

        lane_limit = policy.get("max_active_lanes")
        if lane_limit != 2:
            errors.append("activation policy must retain the two-lane limit")
        elif len(active_lanes) >= lane_limit:
            errors.append("activation refused because the lane limit is full")
        allowed_surfaces = set(policy.get("allowed_surfaces") or [])
        bootstrap = ledger.get("bootstrap_control_repair") or {}
        bootstrap_matches = all(
            (
                bootstrap.get("status")
                in {"one_time_closeout", "one_time_owner_authorized_repair"},
                bootstrap.get("package") == package_id,
                bootstrap.get("branch") == facts.get("branch"),
                bootstrap.get("origin_main") == facts.get("origin_main"),
            )
        )
        if bootstrap_matches:
            allowed_surfaces = set(bootstrap.get("allowed_surfaces") or [])
            warnings.append(
                "using the exact one-time bootstrap control-repair boundary"
            )
        unexpected_paths = sorted(
            set(facts.get("changed_paths") or []) - allowed_surfaces
        )
        if unexpected_paths:
            errors.append(
                "activation branch contains non-control paths: "
                + ", ".join(unexpected_paths)
            )
        return errors, warnings

    allowed_key = {
        "write": "writes_allowed_for",
        "merge": "merge_allowed_for",
        "cleanup": "cleanup_allowed_for",
        "release": "release_allowed_for",
    }[intent]
    allowed = mode.get(allowed_key) or []
    if package_id not in allowed:
        errors.append(
            f"{intent} is blocked for {package_id} while operating mode is "
            f"{mode.get('state', 'unknown')}"
        )

    active_lane = next(
        (
            lane
            for lane in (
                list(ledger.get("active_lanes") or [])
                + (
                    list(ledger.get("closing_lanes") or [])
                    if intent in {"merge", "cleanup"}
                    else []
                )
            )
            if lane.get("package") == package_id
        ),
        None,
    )
    if not active_lane:
        errors.append(f"{package_id} is not an active lane")
    elif active_lane.get("branch") != facts.get("branch"):
        errors.append(
            f"branch {facts.get('branch')} does not match active lane branch "
            f"{active_lane.get('branch')}"
        )

    if facts.get("ahead", 0):
        warnings.append(
            f"checkout is {facts['ahead']} commit(s) ahead of origin/main; "
            "verify the intended package lineage"
        )
    return errors, warnings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", required=True, help="authoritative package ID")
    parser.add_argument(
        "--intent",
        choices=(
            "read",
            "activate",
            "write",
            "merge",
            "cleanup",
            "release",
        ),
        default="read",
        help="operation being preflighted",
    )
    parser.add_argument(
        "--fetch",
        action="store_true",
        help="fetch and prune origin before collecting facts",
    )
    parser.add_argument(
        "--require-clean",
        action="store_true",
        help="fail when tracked or untracked changes exist",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        ledger = load_ledger()
        facts = collect_facts(
            fetch=args.fetch,
            include_changed_paths=args.intent == "activate",
        )
        errors, warnings = evaluate_policy(
            ledger,
            facts,
            args.package,
            args.intent,
            require_clean=args.require_clean,
        )
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(json.dumps({"result": "fail", "errors": [str(exc)]}, indent=2))
        return 2

    payload = {
        "result": "pass" if not errors else "fail",
        "package": args.package,
        "intent": args.intent,
        "operating_mode": (ledger.get("operating_mode") or {}).get("state"),
        "facts": facts,
        "warnings": warnings,
        "errors": errors,
    }
    print(json.dumps(payload, indent=2))
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
