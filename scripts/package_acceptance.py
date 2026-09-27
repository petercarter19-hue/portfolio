"""Agent-invoked, candidate-bound acceptance check for one claimed package.

This reads the package's existing fixed evidence file. It does not grant
repository authority or replace delivery_preflight, review, or CI.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path


BLOCK = re.compile(r"(?ms)^```package-acceptance-json\n(.*?)\n```$")
PACKAGE = re.compile(r"^PS-[A-Z0-9]+(?:-[A-Z0-9]+)*$")
SHA = re.compile(r"^[0-9a-f]{40}$")
GENERIC_OBSERVATIONS = {"pass", "passed", "ok", "exit 0", "exit code 0", "tests passed"}


class AcceptanceError(ValueError):
    """The completion evidence cannot support a pass."""


def _need(condition: bool, message: str) -> None:
    if not condition:
        raise AcceptanceError(message)


def _text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _unique_pairs(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        _need(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _record(body: str) -> dict:
    blocks = BLOCK.findall(body)
    _need(len(blocks) == 1, "exactly one package-acceptance-json block is required")
    try:
        data = json.loads(blocks[0], object_pairs_hook=_unique_pairs)
    except json.JSONDecodeError as exc:
        raise AcceptanceError(f"invalid acceptance JSON: {exc.msg}") from exc
    _need(isinstance(data, dict), "acceptance record must be an object")
    return data


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    _need(result.returncode == 0, f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def _at(repo: Path, rev: str, path: str) -> dict:
    return _record(_git(repo, "show", f"{rev}:{path}"))


def _criteria(record: dict, package: str) -> list[str]:
    _need(record.get("schema_version") == 1, "schema_version must be 1")
    _need(record.get("package") == package, "package does not match the requested claim")
    baseline = record.get("baseline")
    _need(isinstance(baseline, list) and baseline, "focused baseline is missing")
    for row in baseline:
        _need(isinstance(row, dict), "baseline entry must be an object")
        command, result = row.get("command"), row.get("exit_code")
        _need(_text(command) and isinstance(result, int) and not isinstance(result, bool),
              "baseline requires a command and integer exit_code")
        _need(_text(row.get("observation")), "baseline observation is missing")

    criteria = record.get("criteria")
    _need(isinstance(criteria, list) and criteria, "predefined criteria are missing")
    ids = []
    for row in criteria:
        _need(isinstance(row, dict), "criterion must be an object")
        criterion_id = row.get("id")
        _need(_text(criterion_id) and _text(row.get("expected"))
              and _text(row.get("verification")), "criterion is incomplete")
        _need(re.fullmatch(r"[a-z][a-z0-9-]*", criterion_id) is not None,
              f"invalid criterion id: {criterion_id}")
        _need(criterion_id not in ids, f"duplicate criterion id: {criterion_id}")
        ids.append(criterion_id)
    return ids


def _unresolved_baseline(record: dict) -> set[str]:
    latest = {row["command"]: row["exit_code"] for row in record["baseline"]}
    return {command for command, code in latest.items() if code != 0}


def validate(repo: Path, package: str, candidate: str) -> dict:
    """Check the committed evidence and return a small PASS summary or raise."""
    repo = repo.resolve()
    _need(PACKAGE.fullmatch(package) is not None, "invalid package id")
    _need(SHA.fullmatch(candidate) is not None, "candidate must be an exact commit SHA")
    path = f"docs/governance/lane_claims/evidence/{package}.md"
    evidence = repo / path
    _need(evidence.is_file(), f"missing acceptance record: {path}")
    _need(not _git(repo, "status", "--porcelain"), "worktree must be clean for completion")
    current = _record(evidence.read_text(encoding="utf-8"))
    ids = _criteria(current, package)
    plan = current.get("plan_sha")
    _need(isinstance(plan, str) and SHA.fullmatch(plan) is not None,
          "exact pre-implementation plan SHA is missing")
    _need(current.get("candidate_sha") == candidate,
          "record candidate SHA is missing or stale")
    _git(repo, "cat-file", "-e", f"{plan}^{{commit}}")
    _git(repo, "cat-file", "-e", f"{candidate}^{{commit}}")
    _git(repo, "merge-base", "--is-ancestor", plan, candidate)
    _git(repo, "merge-base", "--is-ancestor", candidate, "HEAD")
    plan_line = _git(repo, "rev-list", "--parents", "-n", "1", plan).split()
    _need(len(plan_line) == 2, "pre-implementation plan must have one parent")
    plan_parent = plan_line[1]
    _need(
        subprocess.run(
            ["git", "-C", str(repo), "merge-base", "--is-ancestor",
             plan_parent, "origin/main"],
            capture_output=True, check=False,
        ).returncode == 0,
        "pre-implementation plan parent must be on authoritative main",
    )
    plan_paths = set(_git(repo, "diff", "--name-only", plan_parent, plan).splitlines())
    _need(plan_paths == {path},
          "pre-implementation plan commit must change only its fixed evidence file")

    planned = _at(repo, plan, path)
    reviewed = _at(repo, candidate, path)
    _need(_criteria(planned, package) == ids and _criteria(reviewed, package) == ids,
          "criterion identifiers changed after the plan")
    for field in ("baseline", "criteria"):
        _need(current[field] == planned[field] == reviewed[field],
              f"{field} changed after the pre-implementation plan")
    _need(reviewed.get("plan_sha") == plan,
          "reviewed candidate does not name the pre-implementation plan")
    tail = set(_git(repo, "diff", "--name-only", candidate, "HEAD").splitlines())
    allowed = {path, f"docs/governance/lane_claims/receipts/{package}.json"}
    _need(tail <= allowed, "implementation changed after the reviewed candidate")

    checks = current.get("checks")
    _need(isinstance(checks, list) and checks, "candidate-bound checks are missing")
    covered = set()
    unresolved = _unresolved_baseline(current)
    resolved = set()
    for check in checks:
        _need(isinstance(check, dict), "check must be an object")
        criterion_id = check.get("criterion_id")
        _need(criterion_id in ids, f"check maps to unknown criterion: {criterion_id}")
        _need(check.get("result") == "pass",
              f"check for {criterion_id} is failed, blocked, or missing")
        _need(check.get("candidate_sha") == candidate,
              f"check for {criterion_id} has stale candidate proof")
        kind = check.get("kind")
        _need(kind in ("automated", "manual", "browser"),
              f"check for {criterion_id} has invalid kind")
        _need(_text(check.get("source_ref")), f"check for {criterion_id} lacks a source")
        observed = check.get("observed")
        _need(_text(observed) and observed.strip().lower() not in GENERIC_OBSERVATIONS,
              f"check for {criterion_id} lacks a semantic observation")
        baseline_command = check.get("resolves_baseline_command")
        if baseline_command is not None:
            _need(kind == "automated" and baseline_command in unresolved,
                  f"check for {criterion_id} does not resolve an exact failed baseline command")
            resolved.add(baseline_command)
        if kind in ("manual", "browser"):
            provenance = check.get("provenance")
            _need(isinstance(provenance, dict)
                  and all(_text(provenance.get(key))
                          for key in ("observer_ref", "captured_at", "source_ref")),
                  f"{kind} check for {criterion_id} lacks exact provenance")
            _need(provenance["source_ref"] == check["source_ref"]
                  and ":" in provenance["source_ref"],
                  f"{kind} check for {criterion_id} has inconsistent source provenance")
            try:
                captured = datetime.fromisoformat(
                    provenance["captured_at"].replace("Z", "+00:00")
                )
            except ValueError as exc:
                raise AcceptanceError(
                    f"{kind} check for {criterion_id} has invalid capture time"
                ) from exc
            _need(captured.tzinfo is not None,
                  f"{kind} check for {criterion_id} lacks capture timezone")
        covered.add(criterion_id)
    _need(covered == set(ids), f"criteria without candidate proof: {sorted(set(ids)-covered)}")
    _need(resolved == unresolved,
          f"unresolved baseline commands lack candidate-bound passing proof: {sorted(unresolved-resolved)}")
    return {"result": "pass", "package": package, "candidate_sha": candidate,
            "criteria": len(ids), "checks": len(checks)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check",))
    parser.add_argument("--package", required=True)
    parser.add_argument("--candidate")
    parser.add_argument("--read-only", action="store_true")
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    if args.read_only:
        print(json.dumps({"result": "skip", "reason": "read-only work has no completion write"}))
        return 0
    try:
        _need(_text(args.candidate), "--candidate is required for writable completion")
        print(json.dumps(validate(args.repo, args.package, args.candidate), sort_keys=True))
        return 0
    except AcceptanceError as exc:
        print(json.dumps({"result": "incomplete", "reason": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
