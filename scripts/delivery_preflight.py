#!/usr/bin/env python3
"""Fail-fast PeerSlate lane and checkout preflight.

The script is intentionally dependency-free. It reports local Git facts and
applies the current machine-readable lane policy before a write or release.
Read-only work remains available during a delivery reset.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
LEDGER_PATH = ROOT / "docs" / "governance" / "CURRENT_LANES.json"
BASELINE_PATH = ROOT / "docs" / "governance" / "CURRENT_BASELINE.yaml"
SCRIPT_PATH = ROOT / "scripts" / "delivery_preflight.py"

# Activation controls two companion records.  The lane ledger reserves the
# writer; this narrow projection keeps the baseline's governing authority from
# being quietly rewritten on the same activation branch.  This is deliberately
# not a general YAML parser: the control file has a fixed, single-line-scalar
# format and activation permits only the limited delta below.
BASELINE_TOP_LEVEL_SECTIONS = (
    "schema_version",
    "updated_at",
    "authority",
    "manager",
    "governing_documents",
    "theme",
    "active_packages",
    "scoped_findings",
    "completed_packages",
    "retired_packages",
    "public_safe_slices",
    "next_gate",
    "superseded_documents",
)
BASELINE_MUTABLE_SECTIONS = frozenset(
    {"manager", "active_packages", "next_gate"}
)
BASELINE_TOP_LEVEL = re.compile(r"([a-z][a-z0-9_]*):(.*)")
BASELINE_MANAGER_FIELD = re.compile(r"  ([a-z][a-z0-9_]*): (.+)")
BASELINE_ACTIVE_PACKAGE_ID = re.compile(r"  - id: (.+)")
BASELINE_ACTIVE_PACKAGE_FIELD = re.compile(r"    (status|scope): (.+)")
# The few unquoted values the controlled projection needs are identifiers and
# status tokens.  Do not accept general YAML plain scalars: whitespace,
# comments, colons, quotes, and escape syntax would make the control format
# ambiguous without a YAML parser.
BASELINE_SAFE_PLAIN_SCALAR = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")

# This is deliberately code-controlled rather than candidate-controlled.  It
# is the sole exception that can widen the normal activation control surfaces
# while repairing this validator.  Once origin/main no longer equals the fixed
# source SHA, the exception cannot match.
BOOTSTRAP_CONTROL_REPAIR = {
    "status": "one_time_owner_authorized_repair",
    "package": "PS-DELIVERY-CONTROL-001",
    "branch": "work/2026-08-10-delivery-activation-three-lane-control-repair",
    "origin_main": "b79bc72a581971a3108a5d8d27732d3dfd596eeb",
    "allowed_surfaces": [
        "AGENTS.md",
        "CLAUDE.md",
        "START_HERE.md",
        "docs/governance/AGENT_STARTUP_CHECKLIST.md",
        "docs/governance/CURRENT_BASELINE.yaml",
        "docs/governance/CURRENT_LANES.json",
        "docs/governance/PEERSLATE_OWNER_DELIVERY_GUIDE.md",
        "scripts/delivery_preflight.py",
        "tests/test_delivery_preflight.py",
        "tests/test_governance_pointers.py",
    ],
    "reason": (
        "Pete explicitly authorized this one-time PS-DELIVERY-CONTROL-001 "
        "three-lane lifecycle repair on 2026-08-10. He approved a third lane "
        "while requiring the most efficient process and preservation of each "
        "lane's integrity. The repair makes active mean actively writing, "
        "moves the abandoned external handoff and preserved Workshop package "
        "out of writer capacity, and permits at most two implementation lanes "
        "plus one direction/authority lane with path and logical-domain "
        "collision checks. The validator, not this candidate record, hard-"
        "codes the fixed package, branch, origin/main base, and ten permitted "
        "surfaces. It changes no product code, schema, pipeline, deployment, "
        "production configuration, or live behavior."
    ),
    "verification_contract": (
        "This is audit evidence, not self-granted authority. The preflight "
        "recognizes it only when this entire record equals the validator's "
        "hard-coded owner-authorized record and command facts prove the exact "
        "branch and exact origin/main base above. A later branch, base, or "
        "altered record cannot use this exception."
    ),
}

# Pete explicitly authorized this one-time validator repair on 2026-08-11
# after the Opportunity Slate writer-transfer branch proved that the standing
# preflight had no safe representation for an in-place writer handoff.  Like
# the earlier bootstrap repair, this exception is code-controlled and expires
# as soon as origin/main moves away from the pinned source SHA.
WRITER_TRANSFER_PREFLIGHT_REPAIR = {
    "status": "one_time_owner_authorized_repair",
    "package": "PS-DELIVERY-CONTROL-001",
    "branch": "work/2026-08-11-delivery-activation-writer-transfer-preflight-repair",
    "origin_main": "65651b417d4e824211b00639aabd4e9d29838b73",
    "allowed_surfaces": [
        "AGENTS.md",
        "START_HERE.md",
        "docs/AI_WORKFLOW.md",
        "docs/governance/AGENT_STARTUP_CHECKLIST.md",
        "docs/governance/CURRENT_LANES.json",
        "docs/governance/MANAGER_SESSION_HANDOFF.md",
        "scripts/delivery_preflight.py",
        "tests/test_delivery_preflight.py",
    ],
    "reason": (
        "Pete explicitly authorized Codex on 2026-08-11 to make the one-time "
        "writer-transfer preflight repair after the mandated Opportunity Slate "
        "governance transfer branch failed closed because the validator only "
        "recognized the implementation branch. The repair adds a dedicated, "
        "fail-closed transfer intent without changing active-lane capacity, "
        "product code, schema, pipeline, deployment, production configuration, "
        "or live behavior."
    ),
    "verification_contract": (
        "This is audit evidence, not self-granted authority. The preflight "
        "recognizes this repair only when the entire record equals the "
        "validator's hard-coded owner-authorized record and command facts prove "
        "the exact branch and origin/main base above. A later branch, base, or "
        "altered record cannot reuse the exception."
    ),
}

# Pete's 2026-08-11 end-to-end Profile direction assignment exposed a narrow
# lifecycle gap: a completed, independently reviewed direction-authority lane
# had no fail-closed way to receive merge authority or to close after its exact
# package tree entered main.  This one-time bootstrap installs those controls;
# it does not itself grant any package merge, release, cleanup, schema, runtime,
# deployment, or production authority.  Like the earlier repairs, every fact
# is code-controlled and the exception expires as soon as origin/main moves.
GRANT_CLOSE_PREFLIGHT_REPAIR = {
    "status": "one_time_owner_authorized_repair",
    "package": "PS-DELIVERY-CONTROL-001",
    "branch": "work/2026-08-11-delivery-activation-grant-close-preflight-repair",
    "origin_main": "f745b39b72d2c8e5a3595f88d7f9524d8d8e41cf",
    "allowed_surfaces": [
        "AGENTS.md",
        "CLAUDE.md",
        "START_HERE.md",
        "docs/AI_WORKFLOW.md",
        "docs/governance/AGENT_STARTUP_CHECKLIST.md",
        "docs/governance/CURRENT_LANES.json",
        "docs/governance/PEERSLATE_OWNER_DELIVERY_GUIDE.md",
        "scripts/delivery_preflight.py",
        "tests/test_delivery_preflight.py",
        "tests/test_governance_pointers.py",
    ],
    "reason": (
        "Pete assigned Codex end-to-end Profile ownership through merge and "
        "dark deployment on 2026-08-11, while retaining a separate explicit "
        "pre-enable decision. The completed non-production direction-authority "
        "package then proved the standing control plane lacked safe grant and "
        "close transitions. This repair adds exact-review-bound grant, merge, "
        "and close preflights only for non-production direction-authority "
        "lanes. It changes no active lane, authority list, baseline, product "
        "code, schema, pipeline, deployment, configuration, or live behavior."
    ),
    "verification_contract": (
        "This is audit evidence, not self-granted package authority. The "
        "preflight recognizes it only when the entire record equals the "
        "validator's hard-coded record and Git proves the exact branch, exact "
        "origin/main base, and exact ten changed paths. A later branch, base, "
        "altered record, or product-authority change cannot reuse it."
    ),
}

MAX_ACTIVE_LANES = 3
MAX_IMPLEMENTATION_LANES = 2
MAX_DIRECTION_AUTHORITY_LANES = 1
MAX_SHARED_FOUNDATION_LANES = 1
MAX_PRODUCTION_CAPABLE_LANES = 1
VALID_LANE_CLASSES = frozenset(
    {"implementation", "shared_foundation", "direction_authority"}
)
IMPLEMENTATION_LANE_CLASSES = frozenset(
    {"implementation", "shared_foundation"}
)
DIRECTION_AUTHORITY_ALLOWED_ROOTS = (
    "docs/initiatives",
    "artifacts",
)
EXCLUSIVE_DOMAIN = re.compile(
    r"[a-z][a-z0-9-]*(?::[a-z0-9][a-z0-9-]*)+"
)
BOOTSTRAP_BASELINE_UPDATED_AT = "2026-08-10"
BOOTSTRAP_BASELINE_MANAGER_ASSIGNMENTS = "No active writer lanes. Program Review and visual concept work may continue read-only; activate an exact implementation or direction/authority outcome before repository writes."
BOOTSTRAP_BASELINE_NEXT_GATE = "Use the three-lane control: at most two non-overlapping implementation lanes plus one non-overlapping direction/authority lane. Paused packages remain preserved and consume no writer capacity."
BOOTSTRAP_EXIT_AUTHORITY = "No package currently owns a mutable surface. PS-EXTERNAL-VISUAL-REVIEW-HANDOFF-001 is preserved after PR 360 was abandoned; PS-WORKSHOP-EXPERIENCE-001 is paused and preserved. Either may resume only through a fresh activation that passes current branch, path, class, and exclusive-domain checks."
BOOTSTRAP_ORIGIN_ACTIVE_PACKAGES = frozenset(
    {
        "PS-EXTERNAL-VISUAL-REVIEW-HANDOFF-001",
        "PS-WORKSHOP-EXPERIENCE-001",
    }
)
ACTIVATION_POLICY_INSTRUCTION = "Create a clean activation branch from current origin/main, run delivery_preflight.py with --intent activate, and append exactly one selected outcome with a new implementation branch, lane_class, production_capable flag, exclusive_domains, writable surfaces, exclusions, and completion evidence. At most two implementation/shared-foundation lanes, one direction/authority lane, and one production-capable lane may be active, with three writers total. Direction/authority surfaces are restricted to docs/initiatives and artifacts. A logical domain or path collision is a stop. Read-only research consumes no lane. Paused work consumes no lane and may resume only through a fresh activation."
EXPECTED_ACTIVATION_POLICY = {
    "enabled": True,
    "package": "PS-DELIVERY-CONTROL-001",
    "branch_pattern": (
        r"work/[0-9]{4}-[0-9]{2}-[0-9]{2}-delivery-activation-[a-z0-9-]+"
    ),
    "intent": "activate",
    "requires_explicit_owner_outcome": True,
    "max_active_lanes": MAX_ACTIVE_LANES,
    "max_implementation_lanes": MAX_IMPLEMENTATION_LANES,
    "max_direction_authority_lanes": MAX_DIRECTION_AUTHORITY_LANES,
    "max_shared_foundation_lanes": MAX_SHARED_FOUNDATION_LANES,
    "max_production_capable_lanes": MAX_PRODUCTION_CAPABLE_LANES,
    "allowed_lane_classes": [
        "implementation",
        "shared_foundation",
        "direction_authority",
    ],
    "allowed_operating_states": ["controlled_idle", "active_delivery"],
    "allowed_surfaces": [
        "docs/governance/CURRENT_LANES.json",
        "docs/governance/CURRENT_BASELINE.yaml",
    ],
    "instruction": ACTIVATION_POLICY_INSTRUCTION,
}
PAUSE_ALLOWED_SURFACES = frozenset(
    {
        "docs/governance/CURRENT_BASELINE.yaml",
        "docs/governance/CURRENT_LANES.json",
    }
)
PAUSE_BRANCH_PATTERN = re.compile(
    r"work/[0-9]{4}-[0-9]{2}-[0-9]{2}-delivery-pause-[a-z0-9-]+"
)
TRANSFER_ALLOWED_SURFACES = frozenset(
    {"docs/governance/CURRENT_LANES.json"}
)
TRANSFER_BRANCH_PATTERN = re.compile(
    r"work/[0-9]{4}-[0-9]{2}-[0-9]{2}-[a-z0-9-]+-transfer"
)
GRANT_ALLOWED_SURFACES = frozenset(
    {"docs/governance/CURRENT_LANES.json"}
)
GRANT_BRANCH_PATTERN = re.compile(
    r"work/[0-9]{4}-[0-9]{2}-[0-9]{2}-delivery-grant-[a-z0-9-]+"
)
CLOSE_ALLOWED_SURFACES = frozenset(
    {
        "docs/governance/CURRENT_BASELINE.yaml",
        "docs/governance/CURRENT_LANES.json",
    }
)
CLOSE_BRANCH_PATTERN = re.compile(
    r"work/[0-9]{4}-[0-9]{2}-[0-9]{2}-delivery-close-[a-z0-9-]+"
)
FULL_GIT_SHA = re.compile(r"[0-9a-f]{40}")
UTC_TIMESTAMP = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z"
)
BASELINE_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")

# A direction candidate may remain on its independently reviewed SHA while a
# small control sequence reaches main.  The sequence is intentionally not a
# generic "non-overlap" allowance: only these code-reviewed control files can
# intervene, and grant/merge additionally prove the exact commit counts and
# pinned endpoints.
DIRECTION_MERGE_CONTROL_PATHS = frozenset(GRANT_CLOSE_PREFLIGHT_REPAIR["allowed_surfaces"])

PROFILE_DIRECTION_OWNER_DECISION_SHA256 = (
    "b4fe6dc59e5eef85b6beb9c6c08e22736876ab78aa134eb4512ae1260c3c36c8"
)

PROFILE_DIRECTION_REVIEW_ATTESTATION = {
    "reviewer_task": "/root/profile_exact_package_review",
    "reviewer_mode": "independent_read_only_non_writer",
    "reviewed_sha": "7790e2684ad5a65a0371338f8b94f878276f36c7",
    "reviewed_branch": "work/2026-08-11-profile-experience-direction-001",
    "verdict": "PASS",
    "verdict_text": (
        "PASS — exact-SHA final Protected review passed for "
        "7790e2684ad5a65a0371338f8b94f878276f36c7, branch-equal to "
        "origin/work/2026-08-11-profile-experience-direction-001 and clean."
    ),
    "verdict_sha256": "c7bc10cdd23dfe6af42b69f193d0931ebd0410ff5f2421f953d85ed46013e145",
    "basis": [
        "full_tree_at_35cab0d6167b7cf2006d7a8652105bce9cf683cd",
        "complete_diff_35cab0d6167b7cf2006d7a8652105bce9cf683cd_to_7790e2684ad5a65a0371338f8b94f878276f36c7",
    ],
    "scope": "direction_package_acceptance_and_merge_only",
    "exclusions": "runtime_schema_deployment_enablement",
    "evidence_path": "docs/initiatives/PS-PROFILE-EXPERIENCE-001/16_VERIFICATION_AND_COMPLETION_RECORD.md",
    "evidence_git_blob_sha": "8de83fb9e28b2e38f736a361fb4dd9bfc26198da",
    "evidence_bytes_sha256": "ac1ff17fc49dbe6594b2c15014efde3283258e6f3259cf8be0ed78b78b17dbc3",
    "received_by": "Root Codex program manager",
    "received_date": "2026-08-11",
}
PROFILE_DIRECTION_REVIEW_ATTESTATION["attestation_sha256"] = (
    "573a2827e4d4a639f40f5d7e70d81165f5ec35c08b8d74fd24728e2bfb5f5ead"
)

DIRECTION_REVIEW_ATTESTATION_FIELDS = frozenset(
    PROFILE_DIRECTION_REVIEW_ATTESTATION
)

VALID_DELIVERY_PATHS = frozenset({"Routine", "Bounded", "Protected"})
EXACT_CONTROL_FETCH_INTENTS = frozenset(
    {"activate", "pause", "transfer", "grant", "close"}
)
CANONICAL_PACKAGE_ID = re.compile(r"PS-[A-Z0-9]+(?:-[A-Z0-9]+)*")
GIT_REF_FORBIDDEN_CHARACTERS = frozenset(
    {"~", "^", ":", "?", "*", "[", "\\"}
)
WINDOWS_INVALID_PATH_CHARACTERS = frozenset({"<", ">", '"', "|"})
WINDOWS_RESERVED_DEVICE_COMPONENTS = frozenset(
    {
        "con",
        "prn",
        "aux",
        "nul",
        "conin$",
        "conout$",
    }
    | {f"com{number}" for number in range(1, 10)}
    | {f"lpt{number}" for number in range(1, 10)}
    | {
        f"com{number}"
        for number in (chr(0x00B9), chr(0x00B2), chr(0x00B3))
    }
    | {
        f"lpt{number}"
        for number in (chr(0x00B9), chr(0x00B2), chr(0x00B3))
    }
)


def _git(*args: str, check: bool = True) -> str:
    return _git_at(ROOT, *args, check=check)


def _git_environment() -> dict[str, str]:
    """Return a process environment that cannot redirect Git outside -C."""
    environment = os.environ.copy()
    for name in (
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_COMMON_DIR",
        "GIT_INDEX_FILE",
        "GIT_OBJECT_DIRECTORY",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_NAMESPACE",
        "GIT_PREFIX",
        "GIT_CONFIG_PARAMETERS",
        "GIT_CONFIG_COUNT",
        "GIT_SHALLOW_FILE",
        "GIT_REPLACE_REF_BASE",
    ):
        environment.pop(name, None)
    for name in list(environment):
        if re.fullmatch(r"GIT_CONFIG_(KEY|VALUE)_\d+", name):
            environment.pop(name, None)
    environment["GIT_OPTIONAL_LOCKS"] = "0"
    environment["GIT_TERMINAL_PROMPT"] = "0"
    environment["GIT_NO_REPLACE_OBJECTS"] = "1"
    return environment


def _git_at(repository: Path, *args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", "-C", str(repository), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=_git_environment(),
        check=False,
    )
    if check and result.returncode:
        raise RuntimeError(result.stderr.strip() or "git command failed")
    return result.stdout.strip()


def _git_returncode_at(repository: Path, *args: str) -> int:
    """Run a Git predicate with the same redirect-resistant environment."""
    return subprocess.run(
        ["git", "-C", str(repository), *args],
        capture_output=True,
        env=_git_environment(),
        check=False,
    ).returncode


def _git_bytes(*args: str) -> bytes:
    """Read an exact Git blob without normalizing its trailing bytes."""
    return _git_bytes_at(ROOT, *args)


def _git_bytes_at(repository: Path, *args: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(repository), *args],
        capture_output=True,
        env=_git_environment(),
        check=False,
    )
    if result.returncode:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(stderr or "git command failed")
    return result.stdout


def _git_nul_at(repository: Path, *args: str) -> list[str]:
    raw = _git_bytes_at(repository, *args)
    return [
        value.decode("utf-8", errors="surrogateescape")
        for value in raw.split(b"\0")
        if value
    ]


def _git_nul(*args: str) -> list[str]:
    return _git_nul_at(ROOT, *args)


def _clean_status_entries(repository: Path = ROOT) -> list[str]:
    """Return every change even when local config hides untracked files."""
    arguments = (
        "-c",
        "core.fsmonitor=false",
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
    )
    return (
        _git_nul(*arguments)
        if repository.resolve() == ROOT.resolve()
        else _git_nul_at(repository, *arguments)
    )


def _git_object_exists(ref: str, path: str) -> bool:
    result = subprocess.run(
        ["git", "-C", str(ROOT), "cat-file", "-e", f"{ref}:{path}"],
        capture_output=True,
        env=_git_environment(),
        check=False,
    )
    return result.returncode == 0


def _git_object_type(ref: str, path: str) -> str:
    return _git("cat-file", "-t", f"{ref}:{path}", check=False)


def _git_blob_sha(ref: str, path: str) -> str:
    return _git("rev-parse", f"{ref}:{path}", check=False)


def _git_object_mode(ref: str, path: str) -> str:
    line = _git("ls-tree", ref, "--", path, check=False)
    return line.split(maxsplit=1)[0] if line else ""


def _canonical_sha256(value: object) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _valid_utc_timestamp(value: object) -> bool:
    if not isinstance(value, str) or not UTC_TIMESTAMP.fullmatch(value):
        return False
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return False
    return True


def _utc_timestamp_strictly_advances(value: object, prior: object) -> bool:
    """Require two real UTC timestamps and a strictly later candidate value."""
    if not _valid_utc_timestamp(value) or not _valid_utc_timestamp(prior):
        return False
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ") > datetime.strptime(
        prior, "%Y-%m-%dT%H:%M:%SZ"
    )


def _valid_baseline_date(value: object) -> bool:
    if not isinstance(value, str) or not BASELINE_DATE.fullmatch(value):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def load_ledger(path: Path = LEDGER_PATH) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        ledger = json.load(handle)
    if not isinstance(ledger, dict):
        raise ValueError(f"lane ledger {path} must contain a JSON object")
    return ledger


def load_ledger_at_ref(ref: str = "origin/main") -> dict:
    """Load the lane ledger at a Git ref without changing the checkout."""
    relative_path = LEDGER_PATH.relative_to(ROOT).as_posix()
    try:
        ledger = json.loads(_git("show", f"{ref}:{relative_path}"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"lane ledger at {ref} is not valid JSON") from exc
    if not isinstance(ledger, dict):
        raise ValueError(f"lane ledger at {ref} must contain a JSON object")
    return ledger


def load_baseline_bytes(path: Path = BASELINE_PATH) -> bytes:
    """Load the candidate baseline exactly as it is checked out."""
    return path.read_bytes()


def load_baseline_bytes_at_ref(ref: str = "origin/main") -> bytes:
    """Load the baseline blob at an exact Git ref without changing checkout."""
    relative_path = BASELINE_PATH.relative_to(ROOT).as_posix()
    return _git_bytes("show", f"{ref}:{relative_path}")


def _strip_line_ending(line: str) -> str:
    return line[:-2] if line.endswith("\r\n") else line[:-1] if line.endswith("\n") else line


def _baseline_scalar(
    raw_value: str,
    label: str,
    errors: list[str],
) -> str | None:
    """Validate the controlled one-line YAML scalar shape we actually use."""
    if not raw_value or raw_value != raw_value.strip():
        errors.append(f"{label} must be a non-empty YAML scalar")
        return None
    value = raw_value
    if value.startswith('"') or value.endswith('"'):
        if len(value) < 2 or not (value.startswith('"') and value.endswith('"')):
            errors.append(f"{label} must use a complete JSON double-quoted scalar")
            return None
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            errors.append(f"{label} must use a valid JSON double-quoted scalar")
            return None
        if not isinstance(decoded, str) or not decoded.strip():
            errors.append(f"{label} must be a non-empty YAML scalar")
            return None
        if any(
            ord(character) < 0x20
            or 0x7F <= ord(character) <= 0x9F
            or 0xD800 <= ord(character) <= 0xDFFF
            for character in decoded
        ):
            errors.append(
                f"{label} must not decode to control characters or surrogate code points"
            )
            return None
        return decoded
    if not BASELINE_SAFE_PLAIN_SCALAR.fullmatch(value):
        errors.append(f"{label} must use a safe plain scalar or JSON double-quoted scalar")
        return None
    return value


def _project_baseline(
    raw: object,
    label: str,
    errors: list[str],
) -> dict[str, object] | None:
    """Project the fixed baseline format without importing a YAML parser.

    The baseline is a controlled repository record, not user-provided YAML.
    Treating it as a narrow projection means a novel top-level block, duplicate
    section, multiline scalar, or structurally ambiguous indentation fails
    closed rather than acquiring accidental activation semantics.
    """
    start_errors = len(errors)
    if not isinstance(raw, (bytes, bytearray)):
        errors.append(f"{label} baseline bytes are required")
        return None
    try:
        text = bytes(raw).decode("utf-8")
    except UnicodeDecodeError:
        errors.append(f"{label} baseline must be valid UTF-8")
        return None

    lines = text.splitlines(keepends=True)
    if not lines:
        errors.append(f"{label} baseline must not be empty")
        return None

    preamble: list[str] = []
    blocks: dict[str, str] = {}
    order: list[str] = []
    current_key: str | None = None
    current_lines: list[str] = []

    def finish_current() -> None:
        nonlocal current_key, current_lines
        if current_key is not None:
            blocks[current_key] = "".join(current_lines)
        current_key = None
        current_lines = []

    for line_number, line in enumerate(lines, start=1):
        content = _strip_line_ending(line)
        match = BASELINE_TOP_LEVEL.fullmatch(content)
        if match:
            finish_current()
            key = match.group(1)
            if key in blocks or key in order:
                errors.append(f"{label} baseline contains duplicate top-level section {key}")
                continue
            order.append(key)
            current_key = key
            current_lines = [line]
            continue

        if current_key is None:
            if not content.strip() or content.startswith("#"):
                preamble.append(line)
                continue
            errors.append(
                f"{label} baseline line {line_number} is outside a controlled top-level section"
            )
            continue

        if content and not content.startswith((" ", "\t")):
            errors.append(
                f"{label} baseline line {line_number} is not valid controlled YAML"
            )
        current_lines.append(line)

    finish_current()
    expected = list(BASELINE_TOP_LEVEL_SECTIONS)
    if order != expected:
        errors.append(
            f"{label} baseline must contain exactly the controlled top-level sections in order"
        )
    if set(blocks) != set(expected):
        missing = sorted(set(expected) - set(blocks))
        unexpected = sorted(set(blocks) - set(expected))
        if missing:
            errors.append(
                f"{label} baseline is missing controlled top-level sections: "
                + ", ".join(missing)
            )
        if unexpected:
            errors.append(
                f"{label} baseline has unsupported top-level sections: "
                + ", ".join(unexpected)
            )
    if len(errors) != start_errors:
        return None
    return {
        "raw": bytes(raw),
        "preamble": "".join(preamble),
        "blocks": blocks,
        "order": tuple(order),
    }


def _single_scalar_block(
    block: str,
    key: str,
    label: str,
    errors: list[str],
) -> tuple[str, list[str]] | None:
    lines = block.splitlines(keepends=True)
    if not lines:
        errors.append(f"{label} baseline {key} block must not be empty")
        return None
    first = _strip_line_ending(lines[0])
    match = re.fullmatch(rf"{re.escape(key)}: (.+)", first)
    if not match:
        errors.append(f"{label} baseline {key} must be a controlled one-line scalar")
        return None
    scalar = _baseline_scalar(match.group(1), f"{label} baseline {key}", errors)
    if any(_strip_line_ending(line).strip() for line in lines[1:]):
        errors.append(f"{label} baseline {key} must not contain continuation lines")
    if scalar is None:
        return None
    return scalar, lines[1:]


def _parse_manager_block(
    block: str,
    label: str,
    errors: list[str],
) -> tuple[str, str] | None:
    lines = block.splitlines(keepends=True)
    if not lines or _strip_line_ending(lines[0]) != "manager:":
        errors.append(f"{label} baseline manager must use the controlled mapping form")
        return None
    current_assignment_index: int | None = None
    seen: set[str] = set()
    for index, line in enumerate(lines[1:], start=1):
        content = _strip_line_ending(line)
        if not content:
            continue
        match = BASELINE_MANAGER_FIELD.fullmatch(content)
        if not match:
            errors.append(f"{label} baseline manager has malformed field at line {index + 1}")
            continue
        field, raw_value = match.groups()
        if field in seen:
            errors.append(f"{label} baseline manager contains duplicate field {field}")
            continue
        seen.add(field)
        value = _baseline_scalar(raw_value, f"{label} baseline manager.{field}", errors)
        if field == "current_assignments":
            current_assignment_index = index
            current_assignments = value
    if current_assignment_index is None:
        errors.append(f"{label} baseline manager must contain current_assignments")
        return None
    if "current_assignments" not in seen:
        return None
    # All manager bytes except the one approved scalar must remain identical.
    masked = list(lines)
    ending = "\r\n" if lines[current_assignment_index].endswith("\r\n") else "\n" if lines[current_assignment_index].endswith("\n") else ""
    masked[current_assignment_index] = "  current_assignments: <activation-mutable>" + ending
    if current_assignments is None:
        return None
    return "".join(masked), current_assignments


def _parse_active_packages_block(
    block: str,
    label: str,
    errors: list[str],
) -> list[dict[str, str]] | None:
    start_errors = len(errors)
    lines = block.splitlines(keepends=True)
    if not lines or _strip_line_ending(lines[0]) != "active_packages:":
        errors.append(f"{label} baseline active_packages must use the controlled list form")
        return None
    items: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    index = 1
    while index < len(lines):
        content = _strip_line_ending(lines[index])
        if not content:
            errors.append(f"{label} baseline active_packages must not contain blank entries")
            index += 1
            continue
        id_match = BASELINE_ACTIVE_PACKAGE_ID.fullmatch(content)
        if not id_match or index + 2 >= len(lines):
            errors.append(f"{label} baseline active_packages has malformed item at line {index + 1}")
            break
        raw_id = id_match.group(1)
        item_errors: list[str] = []
        package = _canonical_package_id(
            raw_id,
            f"{label} baseline active_packages item id",
            item_errors,
        )
        errors.extend(item_errors)
        fields: dict[str, str] = {}
        for field_line in lines[index + 1 : index + 3]:
            field_match = BASELINE_ACTIVE_PACKAGE_FIELD.fullmatch(
                _strip_line_ending(field_line)
            )
            if not field_match:
                errors.append(
                    f"{label} baseline active_packages has malformed item field at line {index + 1}"
                )
                continue
            field, raw_value = field_match.groups()
            if field in fields:
                errors.append(
                    f"{label} baseline active_packages item repeats field {field}"
                )
                continue
            value = _baseline_scalar(
                raw_value,
                f"{label} baseline active_packages.{field}",
                errors,
            )
            if value is not None:
                fields[field] = value
        if package is not None:
            key = package.casefold()
            if key in seen_ids:
                errors.append(
                    f"{label} baseline active_packages contains duplicate id {package}"
                )
            seen_ids.add(key)
        if fields.get("status") != "active_delivery":
            errors.append(
                f"{label} baseline active_packages item status must be active_delivery"
            )
        if "scope" not in fields:
            errors.append(f"{label} baseline active_packages item must contain scope")
        if package is not None and "scope" in fields:
            items.append(
                {
                    "id": package,
                    "status": fields.get("status", ""),
                    "scope": fields["scope"],
                }
            )
        index += 3
    return None if len(errors) != start_errors else items


def _validate_baseline_activation_delta(
    candidate_baseline: object,
    origin_baseline: object,
    *,
    bootstrap_matches: bool,
    added_package: str | None,
    added_branch: str | None,
    errors: list[str],
) -> None:
    """Fail closed unless baseline changes are the exact activation delta."""
    if candidate_baseline is None:
        errors.append("activation requires candidate CURRENT_BASELINE.yaml bytes")
    if origin_baseline is None:
        errors.append("activation requires the fetched origin/main CURRENT_BASELINE.yaml bytes")
    if candidate_baseline is None or origin_baseline is None:
        return
    if bootstrap_matches:
        candidate = _project_baseline(candidate_baseline, "candidate", errors)
        origin = _project_baseline(origin_baseline, "origin/main", errors)
        if candidate is None or origin is None:
            return
        candidate_blocks = candidate["blocks"]
        origin_blocks = origin["blocks"]
        assert isinstance(candidate_blocks, dict)
        assert isinstance(origin_blocks, dict)
        if candidate["preamble"] != origin["preamble"]:
            errors.append("bootstrap control repair may not change the baseline preamble")
        if candidate["order"] != origin["order"]:
            errors.append("bootstrap control repair may not reorder baseline sections")
        allowed_blocks = {"updated_at", "manager", "active_packages", "next_gate"}
        for key in BASELINE_TOP_LEVEL_SECTIONS:
            if key not in allowed_blocks and candidate_blocks[key] != origin_blocks[key]:
                errors.append(
                    f"bootstrap control repair may not change baseline section {key}"
                )

        updated_at = _single_scalar_block(
            candidate_blocks["updated_at"], "updated_at", "candidate", errors
        )
        if updated_at is not None and updated_at[0] != BOOTSTRAP_BASELINE_UPDATED_AT:
            errors.append(
                "bootstrap control repair baseline updated_at is not the exact owner-authorized date"
            )

        origin_manager = _parse_manager_block(
            origin_blocks["manager"], "origin/main", errors
        )
        candidate_manager = _parse_manager_block(
            candidate_blocks["manager"], "candidate", errors
        )
        if origin_manager is not None and candidate_manager is not None:
            if origin_manager[0] != candidate_manager[0]:
                errors.append(
                    "bootstrap control repair may only change baseline manager.current_assignments"
                )
            if candidate_manager[1] != BOOTSTRAP_BASELINE_MANAGER_ASSIGNMENTS:
                errors.append(
                    "bootstrap control repair baseline manager assignment is not exact"
                )

        candidate_packages = _parse_active_packages_block(
            candidate_blocks["active_packages"], "candidate", errors
        )
        if candidate_packages is not None and candidate_packages:
            errors.append(
                "bootstrap control repair baseline active_packages must be empty"
            )

        candidate_gate = _single_scalar_block(
            candidate_blocks["next_gate"], "next_gate", "candidate", errors
        )
        if candidate_gate is not None and candidate_gate[0] != BOOTSTRAP_BASELINE_NEXT_GATE:
            errors.append("bootstrap control repair baseline next_gate is not exact")
        return

    candidate = _project_baseline(candidate_baseline, "candidate", errors)
    origin = _project_baseline(origin_baseline, "origin/main", errors)
    if candidate is None or origin is None:
        return
    candidate_blocks = candidate["blocks"]
    origin_blocks = origin["blocks"]
    assert isinstance(candidate_blocks, dict)
    assert isinstance(origin_blocks, dict)
    if candidate["preamble"] != origin["preamble"]:
        errors.append("activation may not change the baseline preamble")
    if candidate["order"] != origin["order"]:
        errors.append("activation may not reorder baseline top-level sections")

    for key in BASELINE_TOP_LEVEL_SECTIONS:
        if key not in BASELINE_MUTABLE_SECTIONS and candidate_blocks[key] != origin_blocks[key]:
            errors.append(f"activation may not change baseline section {key}")

    origin_manager = _parse_manager_block(origin_blocks["manager"], "origin/main", errors)
    candidate_manager = _parse_manager_block(candidate_blocks["manager"], "candidate", errors)
    if origin_manager is not None and candidate_manager is not None:
        if origin_manager[0] != candidate_manager[0]:
            errors.append(
                "activation may only change baseline manager.current_assignments"
            )
        if added_package is None or added_branch is None:
            errors.append("activation baseline requires one validated added lane")
        elif (
            added_package not in candidate_manager[1]
            or added_branch not in candidate_manager[1]
        ):
            errors.append(
                "activation baseline manager.current_assignments must mention the newly activated package and implementation branch"
            )

    origin_packages = _parse_active_packages_block(
        origin_blocks["active_packages"], "origin/main", errors
    )
    candidate_packages = _parse_active_packages_block(
        candidate_blocks["active_packages"], "candidate", errors
    )
    if origin_packages is not None and candidate_packages is not None:
        if not candidate_blocks["active_packages"].startswith(origin_blocks["active_packages"]):
            errors.append(
                "activation baseline active_packages must preserve origin/main entries byte-for-byte and append one item"
            )
        if len(candidate_packages) != len(origin_packages) + 1:
            errors.append(
                "activation baseline active_packages must append exactly one item"
            )
        elif added_package is not None:
            added = candidate_packages[-1]
            if added["id"] != added_package:
                errors.append(
                    "activation baseline active_packages appended id must match the newly activated package"
                )
            if added["status"] != "active_delivery" or not added["scope"].strip():
                errors.append(
                    "activation baseline active_packages appended item must contain active_delivery and a non-empty scope"
                )

    origin_gate = _single_scalar_block(
        origin_blocks["next_gate"], "next_gate", "origin/main", errors
    )
    candidate_gate = _single_scalar_block(
        candidate_blocks["next_gate"], "next_gate", "candidate", errors
    )
    if origin_gate is not None and candidate_gate is not None:
        if origin_gate[1] != candidate_gate[1]:
            errors.append("activation may only change the baseline next_gate scalar")
        if added_package is None or added_package not in candidate_gate[0]:
            errors.append(
                "activation baseline next_gate must mention the newly activated package"
            )


def _validate_baseline_unchanged(
    candidate_baseline: object,
    origin_baseline: object,
    *,
    label: str,
    errors: list[str],
) -> None:
    """Fail closed unless a control-only operation leaves the baseline exact."""
    if not isinstance(candidate_baseline, (bytes, bytearray)):
        errors.append(f"{label} requires candidate CURRENT_BASELINE.yaml bytes")
        return
    if not isinstance(origin_baseline, (bytes, bytearray)):
        errors.append(
            f"{label} requires fetched origin/main CURRENT_BASELINE.yaml bytes"
        )
        return
    if bytes(candidate_baseline) != bytes(origin_baseline):
        errors.append(f"{label} may not change CURRENT_BASELINE.yaml")


def _remaining_package_ids(remaining_lanes: list[dict]) -> list[str]:
    return [
        package.strip()
        for lane in remaining_lanes
        if isinstance((package := lane.get("package")), str) and package.strip()
    ]


def _expected_pause_manager_assignment(
    paused_package: str,
    remaining_lanes: list[dict],
) -> str:
    remaining = _remaining_package_ids(remaining_lanes)
    if remaining:
        return (
            "Active writer lanes: "
            + ", ".join(remaining)
            + f". {paused_package} is paused and preserved; it may resume only "
            "through fresh activation."
        )
    return (
        f"No active writer lanes. {paused_package} is paused and preserved; "
        "activate an exact implementation or direction/authority outcome before "
        "repository writes."
    )


def _expected_pause_next_gate(
    paused_package: str,
    remaining_lanes: list[dict],
) -> str:
    remaining = _remaining_package_ids(remaining_lanes)
    if remaining:
        return (
            "Continue only the active writer packages: "
            + ", ".join(remaining)
            + f". {paused_package} remains paused; use fresh activation to resume it."
        )
    return (
        "No active writer lanes. Select and activate the next exact outcome under "
        "the three-lane class, path, and exclusive-domain rules."
    )


def _validate_baseline_pause_delta(
    candidate_baseline: object,
    origin_baseline: object,
    *,
    paused_package: str,
    remaining_lanes: list[dict],
    action: str = "pause",
    errors: list[str],
) -> None:
    """Fail closed unless baseline removes exactly the relinquished package."""
    label = "close" if action == "close" else "pause"
    candidate = _project_baseline(candidate_baseline, "candidate", errors)
    origin = _project_baseline(origin_baseline, "origin/main", errors)
    if candidate is None or origin is None:
        return
    candidate_blocks = candidate["blocks"]
    origin_blocks = origin["blocks"]
    assert isinstance(candidate_blocks, dict)
    assert isinstance(origin_blocks, dict)
    if candidate["preamble"] != origin["preamble"]:
        errors.append(f"{label} may not change the baseline preamble")
    if candidate["order"] != origin["order"]:
        errors.append(f"{label} may not reorder baseline sections")
    allowed_blocks = {"updated_at", "manager", "active_packages", "next_gate"}
    if action == "close":
        allowed_blocks.add("completed_packages")
    for key in BASELINE_TOP_LEVEL_SECTIONS:
        if key not in allowed_blocks and candidate_blocks[key] != origin_blocks[key]:
            errors.append(f"{label} may not change baseline section {key}")

    if action == "close":
        origin_updated = _single_scalar_block(
            origin_blocks["updated_at"], "updated_at", "origin/main", errors
        )
        candidate_updated = _single_scalar_block(
            candidate_blocks["updated_at"], "updated_at", "candidate", errors
        )
        if origin_updated is not None and candidate_updated is not None:
            if not _valid_baseline_date(candidate_updated[0]):
                errors.append(
                    f"{label} baseline updated_at must be a real YYYY-MM-DD date"
                )

    origin_manager = _parse_manager_block(origin_blocks["manager"], "origin/main", errors)
    candidate_manager = _parse_manager_block(candidate_blocks["manager"], "candidate", errors)
    if origin_manager is not None and candidate_manager is not None:
        if origin_manager[0] != candidate_manager[0]:
            errors.append(f"{label} may only change baseline manager.current_assignments")
        if action == "close":
            remaining = _remaining_package_ids(remaining_lanes)
            expected_assignment = (
                "Active writer lanes: " + ", ".join(remaining) +
                f". {paused_package} is closed and archived."
                if remaining else
                f"No active writer lanes. {paused_package} is closed and archived; "
                "activate an exact implementation or direction/authority outcome "
                "before repository writes."
            )
        else:
            expected_assignment = _expected_pause_manager_assignment(
                paused_package, remaining_lanes
            )
        if candidate_manager[1] != expected_assignment:
            errors.append(
                f"{label} baseline manager assignment must equal: "
                + expected_assignment
            )

    origin_packages = _parse_active_packages_block(
        origin_blocks["active_packages"], "origin/main", errors
    )
    candidate_packages = _parse_active_packages_block(
        candidate_blocks["active_packages"], "candidate", errors
    )
    if origin_packages is not None and candidate_packages is not None:
        expected = [
            package for package in origin_packages if package["id"] != paused_package
        ]
        if candidate_packages != expected:
            errors.append(
                f"{label} baseline active_packages must remove exactly the target package"
            )

    if action == "close":
        def completed_ids(block: str, source_label: str) -> list[str] | None:
            lines = block.splitlines()
            if not lines or lines[0] != "completed_packages:":
                errors.append(
                    f"{source_label} baseline completed_packages must use the controlled list form"
                )
                return None
            values: list[str] = []
            for index, line in enumerate(lines[1:], start=2):
                if not line:
                    continue
                match = re.fullmatch(r"  - (PS-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)", line)
                if not match:
                    errors.append(
                        f"{source_label} baseline completed_packages line {index} is invalid"
                    )
                    continue
                values.append(match.group(1))
            if len({value.casefold() for value in values}) != len(values):
                errors.append(
                    f"{source_label} baseline completed_packages must not contain duplicates"
                )
            return values

        origin_completed = completed_ids(
            origin_blocks["completed_packages"], "origin/main"
        )
        candidate_completed = completed_ids(
            candidate_blocks["completed_packages"], "candidate"
        )
        if (
            origin_completed is not None
            and candidate_completed is not None
            and candidate_completed != [*origin_completed, paused_package]
        ):
            errors.append(
                "close baseline completed_packages must append exactly the target package once"
            )

    candidate_gate = _single_scalar_block(
        candidate_blocks["next_gate"], "next_gate", "candidate", errors
    )
    if candidate_gate is not None:
        expected_gate = (
            _expected_pause_next_gate(paused_package, remaining_lanes)
            if action != "close"
            else (
                "Continue only the active writer packages: "
                + ", ".join(_remaining_package_ids(remaining_lanes))
                + f". {paused_package} is closed and archived."
                if remaining_lanes
                else "No active writer lanes. Select and activate the next exact outcome under the three-lane class, path, and exclusive-domain rules."
            )
        )
        if candidate_gate[0] != expected_gate:
            errors.append(f"{label} baseline next_gate must equal: " + expected_gate)


def _activation_snapshot(
    ledger: dict,
    label: str,
    errors: list[str],
) -> tuple[dict, dict, list[dict], dict[str, dict]]:
    """Validate and return the activation-relevant portion of a ledger."""
    mode = ledger.get("operating_mode")
    if not isinstance(mode, dict):
        errors.append(f"{label} operating_mode must be an object")
        mode = {}

    policy = ledger.get("activation_policy")
    if not isinstance(policy, dict):
        errors.append(f"{label} activation_policy must be an object")
        policy = {}

    raw_lanes = ledger.get("active_lanes")
    lanes: list[dict] = []
    lanes_by_package: dict[str, dict] = {}
    if not isinstance(raw_lanes, list):
        errors.append(f"{label} active_lanes must be a list")
    else:
        for index, lane in enumerate(raw_lanes):
            if not isinstance(lane, dict):
                errors.append(
                    f"{label} active_lanes[{index}] must be an object"
                )
                continue
            package = _canonical_package_id(
                lane.get("package"),
                f"{label} active_lanes[{index}] package",
                errors,
            )
            if package is None:
                continue
            package_key = package.casefold()
            if package_key in lanes_by_package:
                errors.append(
                    f"{label} active_lanes contains duplicate package {package}"
                )
                continue
            lanes.append(lane)
            lanes_by_package[package_key] = lane

    state = mode.get("state")
    if not isinstance(state, str):
        errors.append(f"{label} operating_mode.state must be a string")
    elif state == "controlled_idle" and lanes:
        errors.append(f"{label} controlled_idle cannot contain active lanes")
    elif state == "active_delivery" and not lanes:
        errors.append(
            f"{label} active_delivery must contain an existing active lane"
        )

    return mode, policy, lanes, lanes_by_package


def _nonempty_string(
    value: object,
    label: str,
    errors: list[str],
) -> str | None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label} must be a non-empty string")
        return None
    return value.strip()


def _canonical_package_id(
    value: object,
    label: str,
    errors: list[str],
) -> str | None:
    """Return a package ID only when its stored form is canonical."""
    package = _nonempty_string(value, label, errors)
    if package is not None and value != package:
        errors.append(f"{label} must not contain leading or trailing whitespace")
    if package is not None and not CANONICAL_PACKAGE_ID.fullmatch(package):
        errors.append(f"{label} must be a canonical PS-... package ID")
    return package


def _contains_ascii_control_character(value: str) -> bool:
    return any(
        ord(character) < 32 or ord(character) == 127 for character in value
    )


def _contains_utf16_surrogate(value: str) -> bool:
    """Reject JSON-legal surrogate code points that Windows/Git cannot name."""
    return any(0xD800 <= ord(character) <= 0xDFFF for character in value)


def _is_valid_implementation_branch(branch: str) -> bool:
    """Apply Git-ref-safe rules to a future implementation work branch."""
    if (
        not branch.startswith("work/")
        or branch == "work/"
        or branch.endswith(("/", "."))
        or branch == "@"
        or ".." in branch
        or "@{" in branch
        or _contains_ascii_control_character(branch)
        or _contains_utf16_surrogate(branch)
        or any(character.isspace() for character in branch)
        or any(character in GIT_REF_FORBIDDEN_CHARACTERS for character in branch)
    ):
        return False
    components = branch.split("/")
    return not any(
        not component
        or component.startswith(".")
        or component.casefold().endswith(".lock")
        or not _is_windows_safe_component(component)
        for component in components
    )


def _is_windows_reserved_device_component(component: str) -> bool:
    """Return whether a component resolves to a reserved Windows device name."""
    return component.casefold().split(".", 1)[0] in WINDOWS_RESERVED_DEVICE_COMPONENTS


def _is_windows_safe_component(component: str) -> bool:
    """Return whether a path-like component is safe on a Windows filesystem."""
    return (
        bool(component)
        and not _contains_ascii_control_character(component)
        and not _contains_utf16_surrogate(component)
        and not any(character.isspace() for character in component)
        and not any(
            character in WINDOWS_INVALID_PATH_CHARACTERS
            for character in component
        )
        and not component.endswith((" ", "."))
        and not _is_windows_reserved_device_component(component)
    )


def _normalize_repo_surface(
    value: object,
    label: str,
    errors: list[str],
) -> str | None:
    """Return a safe, normalized repo-relative comparison path.

    Surface records intentionally support both file and directory paths.  A
    directory's trailing slash is presentation only, so overlap checks compare
    the canonical path without it.
    """
    raw = _nonempty_string(value, label, errors)
    if raw is None:
        return None
    if not isinstance(value, str) or value != raw:
        errors.append(
            f"{label} must not contain leading or trailing whitespace"
        )
        return None
    normalized = raw.replace("\\", "/")
    if (
        normalized.startswith(("/", "~"))
        # Windows can resolve an otherwise unrelated-looking component such as
        # GIT~1 or TEMPLA~1 through its legacy 8.3 short-name aliases.  Reject
        # every tilde, rather than just a leading one, so the literal .git and
        # casefolded surface-overlap protections cannot be bypassed.
        or "~" in normalized
        or re.match(r"^[A-Za-z]:", normalized)
        or ":" in normalized
        or _contains_ascii_control_character(normalized)
        or _contains_utf16_surrogate(normalized)
        or any(
            character in WINDOWS_INVALID_PATH_CHARACTERS
            for character in normalized
        )
    ):
        errors.append(
            f"{label} must be a safe Windows repository-relative path"
        )
        return None
    if any(character in normalized for character in "*?[]{}"):
        errors.append(f"{label} must not contain wildcard or glob characters")
        return None
    comparison_path = normalized[:-1] if normalized.endswith("/") else normalized
    parts = comparison_path.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        errors.append(f"{label} must be a normalized repository-relative path")
        return None
    for part in parts:
        if part.endswith((" ", ".")):
            errors.append(
                f"{label} must not contain Windows-trailing spaces or dots"
            )
            return None
        if part.casefold() == ".git":
            errors.append(f"{label} must not include a .git path component")
            return None
        if _is_windows_reserved_device_component(part):
            errors.append(
                f"{label} must not include a reserved Windows device component"
            )
            return None
    return "/".join(parts)


def _surfaces_overlap(left: str, right: str) -> bool:
    """Compare repo surfaces with Windows-safe case-insensitive semantics."""
    left_folded = left.casefold()
    right_folded = right.casefold()
    return (
        left_folded == right_folded
        or left_folded.startswith(f"{right_folded}/")
        or right_folded.startswith(f"{left_folded}/")
    )


def _path_is_within_surface(path: str, surface: str) -> bool:
    """Return whether a normalized path belongs to a normalized surface."""
    path_folded = path.casefold()
    surface_folded = surface.casefold()
    return path_folded == surface_folded or path_folded.startswith(
        surface_folded + "/"
    )


def _validate_direction_authority_surfaces(
    lane: dict,
    label: str,
    errors: list[str],
) -> None:
    """Keep the third lane documentation/evidence-only by construction."""
    if lane.get("lane_class") != "direction_authority":
        return
    raw_surfaces = lane.get("writable_surfaces")
    if not isinstance(raw_surfaces, list):
        return
    for index, surface in enumerate(raw_surfaces):
        normalized = _normalize_repo_surface(
            surface,
            f"{label} writable_surfaces[{index}]",
            errors,
        )
        if normalized is None:
            continue
        if not any(
            _path_is_within_surface(normalized, root)
            for root in DIRECTION_AUTHORITY_ALLOWED_ROOTS
        ):
            errors.append(
                f"{label} direction_authority surface must remain under "
                "docs/initiatives or artifacts; runtime, shared-governance, "
                f"script, and test paths are forbidden: {normalized}"
            )


def _validate_changed_paths_within_lane(
    lane: dict,
    facts: dict,
    intent: str,
    errors: list[str],
) -> None:
    """Reject branch changes outside the lane's declared mutable surfaces."""
    raw_changed_paths = facts.get("changed_paths")
    if not isinstance(raw_changed_paths, list) or not all(
        isinstance(path, str) and path for path in raw_changed_paths
    ):
        errors.append(f"{intent} changed_paths must be a list of non-empty strings")
        return
    if not raw_changed_paths:
        return

    raw_surfaces = lane.get("writable_surfaces")
    if not isinstance(raw_surfaces, list) or not raw_surfaces:
        errors.append(f"{intent} active lane writable_surfaces must be a non-empty list")
        return
    normalized_surfaces = [
        normalized
        for index, surface in enumerate(raw_surfaces)
        if (
            normalized := _normalize_repo_surface(
                surface,
                f"{intent} active lane writable_surfaces[{index}]",
                errors,
            )
        )
        is not None
    ]
    for index, path in enumerate(raw_changed_paths):
        normalized = _normalize_repo_surface(
            path,
            f"{intent} changed_paths[{index}]",
            errors,
        )
        if normalized is None:
            continue
        if not any(
            _path_is_within_surface(normalized, surface)
            for surface in normalized_surfaces
        ):
            errors.append(
                f"{intent} branch contains path outside active lane surfaces: {normalized}"
            )


def _validate_added_branch_uniqueness(
    branch: str | None,
    origin_lanes: list[dict],
    origin: dict,
    errors: list[str],
) -> None:
    """Reject branch collisions across every retained origin/main lane.

    Branch names are case-insensitive on the Windows worktrees this control
    plane protects.  Active and closing lanes always reserve their branch;
    paused lanes reserve one only when their record explicitly carries a
    ``branch`` field, because legacy paused records do not all have one.
    """
    if branch is None:
        return

    lane_groups: tuple[tuple[str, object, bool], ...] = (
        ("active", origin_lanes, True),
        ("closing", origin.get("closing_lanes"), True),
        ("paused", origin.get("paused_lanes"), False),
    )
    for lane_kind, raw_lanes, branch_required in lane_groups:
        if not isinstance(raw_lanes, list):
            # Other activation validators report malformed closing and paused
            # sections.  Do not mistake an uninspectable section for a vacant
            # branch namespace here.
            continue
        for index, origin_lane in enumerate(raw_lanes):
            if not isinstance(origin_lane, dict):
                continue
            if not branch_required and "branch" not in origin_lane:
                continue

            raw_package = origin_lane.get("package")
            package_label = (
                raw_package.strip()
                if isinstance(raw_package, str) and raw_package.strip()
                else "(unknown)"
            )
            origin_branch = _nonempty_string(
                origin_lane.get("branch"),
                f"origin/main {lane_kind} lane {package_label} branch",
                errors,
            )
            if (
                origin_branch is not None
                and origin_branch.casefold() == branch.casefold()
            ):
                errors.append(
                    "new active lane branch must be unique; it matches origin/main "
                    f"{lane_kind} lane {package_label}"
                )


def _validate_lane_coordination(
    lane: dict,
    label: str,
    errors: list[str],
) -> tuple[str | None, list[str]]:
    """Validate the lane class and its logical ownership locks."""
    lane_class = _nonempty_string(lane.get("lane_class"), f"{label} lane_class", errors)
    if lane_class is not None and lane_class not in VALID_LANE_CLASSES:
        errors.append(
            f"{label} lane_class must be one of: "
            + ", ".join(sorted(VALID_LANE_CLASSES))
        )

    production_capable = lane.get("production_capable")
    if not isinstance(production_capable, bool):
        errors.append(f"{label} production_capable must be a boolean")
    if lane_class == "direction_authority" and production_capable is not False:
        errors.append(
            f"{label} direction_authority must use production_capable false"
        )

    raw_domains = lane.get("exclusive_domains")
    domains: list[str] = []
    if not isinstance(raw_domains, list) or not raw_domains:
        errors.append(f"{label} exclusive_domains must be a non-empty list")
    else:
        for index, raw_domain in enumerate(raw_domains):
            domain = _nonempty_string(
                raw_domain,
                f"{label} exclusive_domains[{index}]",
                errors,
            )
            if domain is None:
                continue
            if raw_domain != domain or not EXCLUSIVE_DOMAIN.fullmatch(domain):
                errors.append(
                    f"{label} exclusive_domains[{index}] must use a canonical "
                    "lowercase namespace such as product:profile or shared:auth"
                )
                continue
            domains.append(domain)
        if len({domain.casefold() for domain in domains}) != len(domains):
            errors.append(f"{label} exclusive_domains must not repeat a domain")
    _validate_direction_authority_surfaces(lane, label, errors)
    return lane_class, domains


def _domains_overlap(left: str, right: str) -> bool:
    """Treat a domain and any more-specific child namespace as one lock."""
    left_folded = left.casefold()
    right_folded = right.casefold()
    return (
        left_folded == right_folded
        or left_folded.startswith(right_folded + ":")
        or right_folded.startswith(left_folded + ":")
    )


def _validate_lane_mix(lanes: list[dict], label: str, errors: list[str]) -> None:
    """Enforce two implementation lanes plus one direction/authority lane."""
    classes: list[str] = []
    domain_owners: list[tuple[str, str]] = []
    production_capable_count = 0
    for index, lane in enumerate(lanes):
        package = lane.get("package")
        package_label = (
            package.strip()
            if isinstance(package, str) and package.strip()
            else f"index {index}"
        )
        lane_class, domains = _validate_lane_coordination(
            lane,
            f"{label} active lane {package_label}",
            errors,
        )
        if lane_class is not None:
            classes.append(lane_class)
        if lane.get("production_capable") is True:
            production_capable_count += 1
        for domain in domains:
            collision = next(
                (
                    (owned_domain, owner)
                    for owned_domain, owner in domain_owners
                    if _domains_overlap(domain, owned_domain)
                ),
                None,
            )
            if collision is not None:
                owned_domain, owner = collision
                errors.append(
                    f"{label} active lanes have an exclusive-domain collision "
                    f"for {domain} and {owned_domain}: {owner} <> {package_label}"
                )
            else:
                domain_owners.append((domain, package_label))

    implementation_count = sum(
        lane_class in IMPLEMENTATION_LANE_CLASSES for lane_class in classes
    )
    direction_count = classes.count("direction_authority")
    shared_count = classes.count("shared_foundation")
    if implementation_count > MAX_IMPLEMENTATION_LANES:
        errors.append(
            f"{label} exceeds the {MAX_IMPLEMENTATION_LANES}-implementation-lane limit"
        )
    if direction_count > MAX_DIRECTION_AUTHORITY_LANES:
        errors.append(
            f"{label} exceeds the {MAX_DIRECTION_AUTHORITY_LANES}-direction-authority-lane limit"
        )
    if shared_count > MAX_SHARED_FOUNDATION_LANES:
        errors.append(
            f"{label} exceeds the {MAX_SHARED_FOUNDATION_LANES}-shared-foundation-lane limit"
        )
    if production_capable_count > MAX_PRODUCTION_CAPABLE_LANES:
        errors.append(
            f"{label} exceeds the {MAX_PRODUCTION_CAPABLE_LANES}-production-capable-lane limit"
        )


def _validate_added_lane(
    lane: dict,
    origin_lanes: list[dict],
    origin: dict,
    activation_branch: str | None,
    errors: list[str],
) -> str | None:
    """Validate a new lane and reject conflicts with the existing writers."""
    package = _canonical_package_id(
        lane.get("package"),
        "new active lane package",
        errors,
    )
    _, normalized_domains = _validate_lane_coordination(
        lane,
        "new active lane",
        errors,
    )
    _nonempty_string(lane.get("outcome"), "new active lane outcome", errors)
    raw_branch = lane.get("branch")
    branch = _nonempty_string(raw_branch, "new active lane branch", errors)
    if branch is not None:
        if (
            not isinstance(raw_branch, str)
            or not _is_valid_implementation_branch(raw_branch)
        ):
            errors.append(
                "new active lane branch must be a future non-main work/... branch"
            )
        if (
            activation_branch is not None
            and branch.casefold() == activation_branch.casefold()
        ):
            errors.append(
                "new active lane branch must differ from the activation branch"
            )
    _nonempty_string(lane.get("writer"), "new active lane writer", errors)
    delivery_path = _nonempty_string(
        lane.get("delivery_path"), "new active lane delivery_path", errors
    )
    if (
        delivery_path is not None
        and delivery_path not in VALID_DELIVERY_PATHS
    ):
        errors.append(
            "new active lane delivery_path must be one of: "
            + ", ".join(sorted(VALID_DELIVERY_PATHS))
        )

    completion_evidence = lane.get("completion_evidence")
    if not isinstance(completion_evidence, list) or not completion_evidence:
        errors.append(
            "new active lane completion_evidence must be a non-empty list"
        )
    else:
        for index, evidence in enumerate(completion_evidence):
            _nonempty_string(
                evidence,
                f"new active lane completion_evidence[{index}]",
                errors,
            )

    raw_surfaces = lane.get("writable_surfaces")
    normalized_surfaces: list[str] = []
    if not isinstance(raw_surfaces, list) or not raw_surfaces:
        errors.append("new active lane writable_surfaces must be a non-empty list")
    else:
        for index, surface in enumerate(raw_surfaces):
            normalized = _normalize_repo_surface(
                surface,
                f"new active lane writable_surfaces[{index}]",
                errors,
            )
            if normalized is not None:
                normalized_surfaces.append(normalized)
        if (
            len({surface.casefold() for surface in normalized_surfaces})
            != len(normalized_surfaces)
        ):
            errors.append("new active lane writable_surfaces must not repeat a path")

    exclusions = lane.get("exclusions")
    if not isinstance(exclusions, list) or not exclusions:
        errors.append("new active lane exclusions must be a non-empty list")
    else:
        for index, exclusion in enumerate(exclusions):
            _nonempty_string(
                exclusion,
                f"new active lane exclusions[{index}]",
                errors,
            )

    for origin_lane in origin_lanes:
        origin_package = _nonempty_string(
            origin_lane.get("package"),
            "origin/main active lane package",
            errors,
        )
        origin_raw_surfaces = origin_lane.get("writable_surfaces")
        if not isinstance(origin_raw_surfaces, list) or not origin_raw_surfaces:
            errors.append(
                "origin/main active lane "
                f"{origin_package or '(unknown)'} writable_surfaces must be a "
                "non-empty list"
            )
            continue
        origin_surfaces: list[str] = []
        for index, surface in enumerate(origin_raw_surfaces):
            normalized = _normalize_repo_surface(
                surface,
                "origin/main active lane "
                f"{origin_package or '(unknown)'} writable_surfaces[{index}]",
                errors,
            )
            if normalized is not None:
                origin_surfaces.append(normalized)
        for candidate_surface in normalized_surfaces:
            for origin_surface in origin_surfaces:
                if _surfaces_overlap(candidate_surface, origin_surface):
                    errors.append(
                        "new active lane writable surface overlaps origin/main "
                        f"active lane {origin_package or '(unknown)'}: "
                        f"{candidate_surface} <> {origin_surface}"
                    )
        _, origin_domains = _validate_lane_coordination(
            origin_lane,
            f"origin/main active lane {origin_package or '(unknown)'}",
            errors,
        )
        for domain in normalized_domains:
            if any(
                _domains_overlap(domain, origin_domain)
                for origin_domain in origin_domains
            ):
                errors.append(
                    "new active lane exclusive domain overlaps origin/main "
                    f"active lane {origin_package or '(unknown)'}: {domain}"
                )
    _validate_added_branch_uniqueness(
        branch,
        origin_lanes,
        origin,
        errors,
    )
    return package


def _root_changes(
    candidate: dict,
    origin: dict,
) -> set[str]:
    marker = object()
    return {
        key
        for key in set(candidate) | set(origin)
        if candidate.get(key, marker) != origin.get(key, marker)
    }


def _validate_paused_lane_delta(
    candidate: dict,
    origin: dict,
    added_package: str,
    errors: list[str],
) -> None:
    origin_paused = origin.get("paused_lanes")
    candidate_paused = candidate.get("paused_lanes")
    if not isinstance(origin_paused, list) or not isinstance(candidate_paused, list):
        errors.append("activation paused_lanes must remain a list")
        return
    matching_indexes = [
        index
        for index, lane in enumerate(origin_paused)
        if (
            isinstance(lane, dict)
            and isinstance(lane.get("package"), str)
            and lane["package"].casefold() == added_package.casefold()
        )
    ]
    if len(matching_indexes) == 1:
        expected = [
            lane
            for index, lane in enumerate(origin_paused)
            if index != matching_indexes[0]
        ]
        if candidate_paused != expected:
            errors.append(
                "activation must remove exactly the newly activated package from "
                "paused_lanes"
            )
    elif not matching_indexes:
        if candidate_paused != origin_paused:
            errors.append(
                "activation may not change paused_lanes when the newly activated "
                "package is not paused"
            )
    else:
        errors.append(
            "origin/main paused_lanes contains duplicate newly activated package "
            f"{added_package}"
        )


def _validate_added_package_not_closing(
    origin: dict,
    added_package: str,
    errors: list[str],
) -> None:
    """Prevent activation from implicitly reopening an existing closing lane."""
    closing_lanes = origin.get("closing_lanes")
    if not isinstance(closing_lanes, list):
        errors.append("origin/main closing_lanes must be a list")
        return
    for index, lane in enumerate(closing_lanes):
        if not isinstance(lane, dict):
            errors.append(
                f"origin/main closing_lanes[{index}] must be an object"
            )
            continue
        package = _canonical_package_id(
            lane.get("package"),
            f"origin/main closing_lanes[{index}] package",
            errors,
        )
        if package is not None and package.casefold() == added_package.casefold():
            errors.append(
                "activation may not reopen origin/main closing lane "
                f"{added_package}; use its authorized merge or cleanup path"
            )


def _validate_closing_lanes_retain_no_authority(
    origin: dict,
    origin_mode: dict,
    errors: list[str],
) -> None:
    """Closing records are history; any retained mutation grant blocks activation."""
    closing_lanes = origin.get("closing_lanes")
    if not isinstance(closing_lanes, list):
        errors.append("origin/main closing_lanes must be a list")
        return
    closing_packages = {
        package.casefold()
        for lane in closing_lanes
        if isinstance(lane, dict)
        and isinstance((package := lane.get("package")), str)
        and package.strip()
    }
    for field in (
        "writes_allowed_for",
        "merge_allowed_for",
        "cleanup_allowed_for",
        "release_allowed_for",
    ):
        values = origin_mode.get(field)
        if not isinstance(values, list):
            errors.append(f"origin/main operating_mode.{field} must be a list")
            continue
        retained = sorted(
            value
            for value in values
            if isinstance(value, str) and value.casefold() in closing_packages
        )
        if retained:
            errors.append(
                "origin/main closing lanes retain mutation authority in "
                f"{field}: " + ", ".join(retained)
            )


def _validate_operating_mode_delta(
    candidate_mode: dict,
    origin_mode: dict,
    added_package: str,
    errors: list[str],
) -> None:
    allowed_changes = {"state", "writes_allowed_for", "exit_authority"}
    marker = object()
    changed_fields = {
        key
        for key in set(candidate_mode) | set(origin_mode)
        if candidate_mode.get(key, marker) != origin_mode.get(key, marker)
    }
    unexpected = sorted(changed_fields - allowed_changes)
    if unexpected:
        errors.append(
            "activation may not change operating_mode fields: "
            + ", ".join(unexpected)
        )

    if candidate_mode.get("state") != "active_delivery":
        errors.append("activation candidate must use active_delivery")

    origin_writes = origin_mode.get("writes_allowed_for")
    candidate_writes = candidate_mode.get("writes_allowed_for")
    if not isinstance(origin_writes, list) or not all(
        isinstance(value, str) and value for value in origin_writes
    ):
        errors.append("origin/main writes_allowed_for must be a list of strings")
    elif candidate_writes != [*origin_writes, added_package]:
        errors.append(
            "activation writes_allowed_for must preserve existing writers and "
            "append exactly the newly activated package"
        )

    if candidate_mode.get("exit_authority") != origin_mode.get("exit_authority"):
        exit_authority = _nonempty_string(
            candidate_mode.get("exit_authority"),
            "activation operating_mode.exit_authority",
            errors,
        )
        if exit_authority is not None and added_package not in exit_authority:
            errors.append(
                "activation operating_mode.exit_authority must identify the "
                "newly activated package when it changes"
            )


def _exact_bootstrap_matches(
    ledger: dict,
    facts: dict,
    package_id: str,
) -> bool:
    return (
        ledger.get("bootstrap_control_repair") == BOOTSTRAP_CONTROL_REPAIR
        and package_id == BOOTSTRAP_CONTROL_REPAIR["package"]
        and facts.get("branch") == BOOTSTRAP_CONTROL_REPAIR["branch"]
        and facts.get("origin_main")
        == BOOTSTRAP_CONTROL_REPAIR["origin_main"]
    )


def _exact_writer_transfer_preflight_repair_matches(
    ledger: dict,
    facts: dict,
    package_id: str,
) -> bool:
    return (
        ledger.get("writer_transfer_preflight_repair")
        == WRITER_TRANSFER_PREFLIGHT_REPAIR
        and package_id == WRITER_TRANSFER_PREFLIGHT_REPAIR["package"]
        and facts.get("branch") == WRITER_TRANSFER_PREFLIGHT_REPAIR["branch"]
        and facts.get("origin_main")
        == WRITER_TRANSFER_PREFLIGHT_REPAIR["origin_main"]
    )


def _exact_grant_close_preflight_repair_matches(
    ledger: dict,
    facts: dict,
    package_id: str,
) -> bool:
    return (
        ledger.get("grant_close_preflight_repair")
        == GRANT_CLOSE_PREFLIGHT_REPAIR
        and package_id == GRANT_CLOSE_PREFLIGHT_REPAIR["package"]
        and facts.get("branch") == GRANT_CLOSE_PREFLIGHT_REPAIR["branch"]
        and facts.get("origin_main")
        == GRANT_CLOSE_PREFLIGHT_REPAIR["origin_main"]
        and facts.get("ahead") == 1
        and facts.get("behind") == 0
    )


def _affirmative_merge_decision(decision: object, package_id: object) -> bool:
    """Accept pinned Profile authority or an exact machine-readable decision."""
    if package_id == "PS-PROFILE-EXPERIENCE-001":
        return (
            isinstance(decision, dict)
            and set(decision) == {"date", "decision"}
            and _canonical_sha256(decision)
            == PROFILE_DIRECTION_OWNER_DECISION_SHA256
        )
    expected_fields = {
        "date",
        "decision",
        "authorized_by",
        "action",
        "status",
        "scope",
        "package",
    }
    return bool(
        isinstance(decision, dict)
        and set(decision) == expected_fields
        and _valid_baseline_date(decision.get("date"))
        and decision.get("decision") == "direction_package_merge_authority"
        and decision.get("authorized_by") == "Pete"
        and decision.get("action") == "merge"
        and decision.get("status") == "authorized"
        and decision.get("scope") == "direction_package_only"
        and decision.get("package") == package_id
    )


def _direction_merge_grant(
    lane: object,
    label: str,
    errors: list[str],
) -> dict | None:
    """Validate an exact-review-bound merge grant on a direction lane."""
    if not isinstance(lane, dict):
        errors.append(f"{label} must be an object")
        return None
    if lane.get("lane_class") != "direction_authority":
        errors.append(f"{label} is available only to direction_authority lanes")
    if lane.get("production_capable") is not False:
        errors.append(f"{label} requires production_capable false")
    grant = lane.get("merge_grant")
    if not isinstance(grant, dict):
        errors.append(f"{label} merge_grant must be an object")
        return None
    expected_fields = {
        "authorized_by",
        "authority_decision_index",
        "authority_decision_sha256",
        "independent_review",
        "reviewed_remote_sha",
        "granted_at",
        "review_result",
        "review_evidence_paths",
    }
    if set(grant) != expected_fields:
        errors.append(
            f"{label} merge_grant must contain exactly: "
            + ", ".join(sorted(expected_fields))
        )
    if grant.get("authorized_by") != "Pete":
        errors.append(f"{label} merge_grant authorized_by must be Pete")
    index = grant.get("authority_decision_index")
    decisions = lane.get("owner_decisions")
    if not isinstance(index, int) or isinstance(index, bool) or index < 0:
        errors.append(
            f"{label} merge_grant authority_decision_index must be a non-negative integer"
        )
    elif not isinstance(decisions, list) or index >= len(decisions):
        errors.append(
            f"{label} merge_grant authority_decision_index is outside owner_decisions"
        )
    else:
        decision = decisions[index]
        if not _affirmative_merge_decision(decision, lane.get("package")):
            errors.append(
                f"{label} referenced pre-existing owner decision must be an unambiguous affirmative merge assignment"
            )
        if grant.get("authority_decision_sha256") != _canonical_sha256(decision):
            errors.append(
                f"{label} authority_decision_sha256 must bind the exact referenced owner decision"
            )
    reviewed_sha = grant.get("reviewed_remote_sha")
    if not isinstance(reviewed_sha, str) or not FULL_GIT_SHA.fullmatch(reviewed_sha):
        errors.append(f"{label} merge_grant reviewed_remote_sha must be a full Git SHA")
    review = grant.get("independent_review")
    independent_sha: str | None = None
    if not isinstance(review, dict):
        errors.append(f"{label} independent_review must be an object")
    else:
        if set(review) != DIRECTION_REVIEW_ATTESTATION_FIELDS:
            errors.append(
                f"{label} independent_review must contain exactly the controlled attestation fields"
            )
        expected_review = (
            PROFILE_DIRECTION_REVIEW_ATTESTATION
            if lane.get("package") == "PS-PROFILE-EXPERIENCE-001"
            else None
        )
        if expected_review is None:
            errors.append(
                f"{label} no code-controlled independent review attestation "
                f"is registered for {lane.get('package')}"
            )
        if expected_review is not None and review != expected_review:
            errors.append(
                f"{label} independent_review must equal a code-controlled attestation"
            )
        independent_sha = review.get("reviewed_sha")
        if not isinstance(independent_sha, str) or not FULL_GIT_SHA.fullmatch(independent_sha):
            errors.append(f"{label} independent_review reviewed_sha must be a full Git SHA")
        if review.get("reviewer_mode") != "independent_read_only_non_writer":
            errors.append(f"{label} independent_review reviewer_mode is invalid")
        if review.get("reviewed_branch") != lane.get("branch"):
            errors.append(f"{label} independent_review reviewed_branch must equal the lane branch")
        if independent_sha != reviewed_sha:
            errors.append(
                f"{label} independent_review reviewed_sha must equal reviewed_remote_sha"
            )
        if review.get("verdict") != "PASS" or review.get("scope") != "direction_package_acceptance_and_merge_only":
            errors.append(f"{label} independent_review scope or verdict is invalid")
        reviewer_task = review.get("reviewer_task")
        if not isinstance(reviewer_task, str) or not re.fullmatch(
            r"/root(?:/[a-z0-9_]+)+", reviewer_task
        ):
            errors.append(f"{label} independent_review reviewer_task is invalid")
        if review.get("exclusions") != "runtime_schema_deployment_enablement":
            errors.append(f"{label} independent_review exclusions are invalid")
        if review.get("received_by") != "Root Codex program manager":
            errors.append(f"{label} independent_review received_by is invalid")
        if not _valid_baseline_date(review.get("received_date")):
            errors.append(f"{label} independent_review received_date is invalid")
        evidence_path = review.get("evidence_path")
        if not isinstance(evidence_path, str) or not evidence_path.casefold().endswith(".md"):
            errors.append(f"{label} independent_review evidence_path must be Markdown")
        if not isinstance(review.get("evidence_git_blob_sha"), str) or not re.fullmatch(
            r"[0-9a-f]{40}", review.get("evidence_git_blob_sha", "")
        ):
            errors.append(f"{label} independent_review evidence_git_blob_sha is invalid")
        if not isinstance(review.get("evidence_bytes_sha256"), str) or not re.fullmatch(
            r"[0-9a-f]{64}", review.get("evidence_bytes_sha256", "")
        ):
            errors.append(f"{label} independent_review evidence_bytes_sha256 is invalid")
        basis = review.get("basis")
        if (
            not isinstance(basis, list)
            or len(basis) < 2
            or not all(isinstance(item, str) and item for item in basis)
            or len(set(basis)) != len(basis)
            or not isinstance(independent_sha, str)
            or not any(independent_sha in item for item in basis)
            or not any("complete_diff" in item and independent_sha in item for item in basis)
        ):
            errors.append(
                f"{label} independent_review basis must bind full-tree and complete-diff review to the SHA"
            )
        if review.get("evidence_path") not in (grant.get("review_evidence_paths") or []):
            errors.append(f"{label} independent_review evidence_path must be in review_evidence_paths")
        verdict_text = review.get("verdict_text")
        expected_verdict = (
            f"PASS — exact-SHA final Protected review passed for {independent_sha}, "
            f"branch-equal to origin/{lane.get('branch')} and clean."
        )
        if (
            not isinstance(verdict_text, str)
            or verdict_text != expected_verdict
        ):
            errors.append(
                f"{label} independent_review verdict_text must equal the exact SHA/branch PASS statement"
            )
        elif hashlib.sha256(verdict_text.encode("utf-8")).hexdigest() != review.get(
            "verdict_sha256"
        ):
            errors.append(
                f"{label} independent_review verdict_sha256 must bind the exact verdict text"
            )
        attestation = dict(review)
        supplied_digest = attestation.pop("attestation_sha256", None)
        if supplied_digest != _canonical_sha256(attestation):
            errors.append(f"{label} independent_review attestation_sha256 is invalid")
    if (
        lane.get("package") == "PS-PROFILE-EXPERIENCE-001"
        and grant.get("authority_decision_sha256")
        != PROFILE_DIRECTION_OWNER_DECISION_SHA256
    ):
        errors.append(
            f"{label} authority_decision_sha256 must equal the pinned Profile owner decision digest"
        )
    granted_at = grant.get("granted_at")
    if not _valid_utc_timestamp(granted_at):
        errors.append(f"{label} merge_grant granted_at must be a UTC timestamp")
    if grant.get("review_result") != "pass":
        errors.append(f"{label} merge_grant review_result must be pass")
    paths = grant.get("review_evidence_paths")
    if not isinstance(paths, list) or not paths:
        errors.append(f"{label} merge_grant review_evidence_paths must be non-empty")
    elif not all(isinstance(path, str) and path.strip() for path in paths):
        errors.append(
            f"{label} merge_grant review_evidence_paths must contain non-empty strings"
        )
    elif len({path.casefold() for path in paths}) != len(paths):
        errors.append(f"{label} merge_grant review_evidence_paths must be unique")
    return grant


def _exact_direction_grant_delta(
    parent_ledger: object,
    granted_ledger: object,
    package_id: str,
) -> bool:
    """Prove one main commit is only the target's validated grant transition."""
    if not isinstance(parent_ledger, dict) or not isinstance(granted_ledger, dict):
        return False
    errors: list[str] = []
    parent_mode, parent_policy, parent_lanes, parent_by_package = (
        _activation_snapshot(parent_ledger, "grant parent", errors)
    )
    granted_mode, granted_policy, granted_lanes, granted_by_package = (
        _activation_snapshot(granted_ledger, "grant result", errors)
    )
    parent_target = parent_by_package.get(package_id.casefold())
    granted_target = granted_by_package.get(package_id.casefold())
    if not isinstance(parent_target, dict) or not isinstance(granted_target, dict):
        return False
    if parent_policy != granted_policy or len(parent_lanes) != len(granted_lanes):
        return False
    if [lane.get("package") for lane in parent_lanes] != [
        lane.get("package") for lane in granted_lanes
    ]:
        return False
    for before, after in zip(parent_lanes, granted_lanes, strict=True):
        if before.get("package") == package_id:
            expected = dict(before)
            expected["merge_grant"] = after.get("merge_grant")
            if after != expected or "merge_grant" in before:
                return False
            _direction_merge_grant(after, "main grant", errors)
        elif after != before:
            return False
    parent_allowed = parent_mode.get("merge_allowed_for")
    if not isinstance(parent_allowed, list) or package_id in parent_allowed:
        return False
    expected_mode = dict(parent_mode)
    expected_mode["merge_allowed_for"] = [*parent_allowed, package_id]
    if granted_mode != expected_mode:
        return False
    if _root_changes(granted_ledger, parent_ledger) != {
        "updated_at", "operating_mode", "active_lanes"
    }:
        return False
    granted_at = granted_ledger.get("updated_at")
    if not _utc_timestamp_strictly_advances(
        granted_at, parent_ledger.get("updated_at")
    ):
        return False
    if granted_target.get("merge_grant", {}).get("granted_at") != granted_at:
        return False
    return not errors


def _direction_control_path_sequence_valid(
    commit_paths: object,
) -> bool:
    """Accept only repair+grant or post-repair grant, with exact file sets."""
    if not isinstance(commit_paths, list) or not all(
        isinstance(paths, set) and all(isinstance(path, str) for path in paths)
        for paths in commit_paths
    ):
        return False
    if len(commit_paths) == 1:
        return commit_paths[0] == set(GRANT_ALLOWED_SURFACES)
    if len(commit_paths) == 2:
        return (
            commit_paths[0] == set(DIRECTION_MERGE_CONTROL_PATHS)
            and commit_paths[1] == set(GRANT_ALLOWED_SURFACES)
        )
    return False


def _paths_within_lane(
    paths: object,
    lane: dict,
    label: str,
    errors: list[str],
) -> list[str]:
    if not isinstance(paths, list):
        errors.append(f"{label} must be a list")
        return []
    raw_surfaces = lane.get("writable_surfaces")
    if not isinstance(raw_surfaces, list) or not raw_surfaces:
        errors.append(f"{label} lane writable_surfaces must be non-empty")
        return []
    surfaces = [
        normalized
        for index, value in enumerate(raw_surfaces)
        if (
            normalized := _normalize_repo_surface(
                value, f"{label} lane writable_surfaces[{index}]", errors
            )
        )
        is not None
    ]
    normalized_paths: list[str] = []
    for index, value in enumerate(paths):
        path = _normalize_repo_surface(value, f"{label}[{index}]", errors)
        if path is None:
            continue
        normalized_paths.append(path)
        if not any(_path_is_within_surface(path, surface) for surface in surfaces):
            errors.append(f"{label} path is outside target writable surfaces: {path}")
    return normalized_paths


def collect_facts(
    fetch: bool = False,
    include_changed_paths: bool = False,
) -> dict:
    if fetch:
        _git("fetch", "origin", "--prune")

    # Capture both refs once after the optional fetch.  All activation path
    # comparisons below use these immutable object IDs rather than a moving
    # origin/main name.
    head = _git("rev-parse", "HEAD")
    origin_main = _git("rev-parse", "origin/main")
    status_lines = _clean_status_entries(ROOT)
    tracked = [line for line in status_lines if not line.startswith("??")]
    untracked = [line for line in status_lines if line.startswith("??")]
    origin_url = _git("config", "--get", "remote.origin.url")
    facts = {
        "repository": str(ROOT),
        "branch": _git("symbolic-ref", "--quiet", "--short", "HEAD", check=False),
        "head": head,
        "origin_main": origin_main,
        "ahead": int(_git("rev-list", "--count", f"{origin_main}..{head}")),
        "behind": int(_git("rev-list", "--count", f"{head}..{origin_main}")),
        "tracked_changes": len(tracked),
        "untracked_changes": len(untracked),
        "fetched": fetch,
        "origin_url": origin_url,
        "origin_is_azure": "dev.azure.com" in origin_url.lower(),
    }
    if include_changed_paths:
        facts["changed_paths"] = sorted(
            {
                path
                for command in (
                    # The merge-base range must remain tied to the exact
                    # post-fetch refs captured above, not to a moving remote
                    # name that can change while preflight is running.
                    ("diff", "--name-only", "-z", f"{origin_main}...{head}"),
                    ("diff", "--name-only", "-z"),
                    ("diff", "--cached", "--name-only", "-z"),
                    ("ls-files", "--others", "--exclude-standard", "-z"),
                )
                for path in _git_nul(*command)
                if path
            }
        )
    return facts


def _absolute_git_common_dir(repository: Path) -> Path:
    raw = Path(_git_at(repository, "rev-parse", "--git-common-dir"))
    return (raw if raw.is_absolute() else repository / raw).resolve()


def _normalized_origin(repository: Path) -> str:
    raw = _git_at(repository, "remote", "get-url", "origin")
    return raw.replace("\\", "/").rstrip("/").casefold()


def _authoritative_azure_origin(repository: Path) -> str:
    """Return the exact PeerSlate Azure origin, rejecting URL indirection."""
    configured = _git_at(repository, "config", "--get", "remote.origin.url")
    effective = _git_at(repository, "remote", "get-url", "origin")
    normalized_configured = configured.replace("\\", "/").rstrip("/").casefold()
    normalized_effective = effective.replace("\\", "/").rstrip("/").casefold()
    if normalized_configured != normalized_effective:
        raise RuntimeError("origin URL rewrite or indirection is not allowed")
    parsed = urlparse(effective)
    try:
        port = parsed.port
    except ValueError as exc:
        raise RuntimeError("origin contains an invalid port") from exc
    expected_path = "/peerslate19/portfolio-site/_git/portfolio-site"
    if (
        parsed.scheme.casefold() != "https"
        or (parsed.hostname or "").casefold() != "dev.azure.com"
        or parsed.password is not None
        or (parsed.username or "peerslate19").casefold() != "peerslate19"
        or port not in (None, 443)
        or parsed.path.rstrip("/").casefold() != expected_path
        or parsed.params
        or parsed.query
        or parsed.fragment
    ):
        raise RuntimeError(
            "origin must be the exact PeerSlate Azure DevOps repository"
        )
    return normalized_effective


def _fetch_exact_origin_refs(repository: Path, branches: list[str]) -> dict[str, str]:
    """Fetch named heads explicitly and bind local refs to advertised remote OIDs."""
    if not branches or len(set(branches)) != len(branches):
        raise RuntimeError("exact origin fetch requires unique branch names")
    for branch in branches:
        if _git_at(repository, "check-ref-format", "--branch", branch, check=False) != branch:
            raise RuntimeError("exact origin fetch received an invalid branch name")
    refspecs = [
        f"+refs/heads/{branch}:refs/remotes/origin/{branch}"
        for branch in branches
    ]
    _git_at(repository, "fetch", "--prune", "origin", *refspecs)
    advertised = _git_at(
        repository,
        "ls-remote",
        "--refs",
        "origin",
        *(f"refs/heads/{branch}" for branch in branches),
    )
    remote_oids: dict[str, str] = {}
    for line in advertised.splitlines():
        parts = line.split("\t", 1)
        if len(parts) != 2 or not FULL_GIT_SHA.fullmatch(parts[0]):
            raise RuntimeError("origin advertised an invalid branch object")
        prefix = "refs/heads/"
        if not parts[1].startswith(prefix):
            raise RuntimeError("origin advertised an unexpected ref")
        branch = parts[1][len(prefix):]
        if branch in remote_oids:
            raise RuntimeError("origin advertised a duplicate branch ref")
        remote_oids[branch] = parts[0]
    if set(remote_oids) != set(branches):
        raise RuntimeError("origin did not advertise every required branch exactly once")
    for branch, oid in remote_oids.items():
        local = _git_at(
            repository,
            "rev-parse",
            "--verify",
            f"refs/remotes/origin/{branch}",
            check=False,
        )
        if local != oid:
            raise RuntimeError("fetched origin ref does not equal the advertised branch object")
    return remote_oids


def _authoritative_ref_snapshot(
    repository: Path,
    branches: list[str],
    *,
    expected_origin: str | None = None,
) -> tuple[str, dict[str, str]]:
    """Fetch exact named refs while proving the Azure endpoint stayed fixed."""
    before = _authoritative_azure_origin(repository)
    if expected_origin is not None and before != expected_origin:
        raise RuntimeError("authoritative Azure origin changed during preflight")
    refs = _fetch_exact_origin_refs(repository, branches)
    after = _authoritative_azure_origin(repository)
    if after != before:
        raise RuntimeError("authoritative Azure origin changed during preflight")
    return before, refs


def _registered_worktrees(repository: Path) -> list[Path]:
    return [
        Path(field.removeprefix("worktree ")).resolve()
        for field in _git_nul_at(
            repository, "worktree", "list", "--porcelain", "-z"
        )
        if field.startswith("worktree ")
    ]


def _direction_main_sequence_facts(
    origin_ledger: dict,
    package_id: str,
    candidate_sha: str,
    origin_main: str,
) -> tuple[list[str], bool, int]:
    base = _git("merge-base", candidate_sha, origin_main)
    main_paths = sorted(
        _git_nul("diff", "--name-only", "-z", f"{base}..{origin_main}")
    )
    main_commits = [
        sha for sha in _git(
            "rev-list", "--reverse", f"{base}..{origin_main}"
        ).splitlines() if sha
    ]
    commit_paths = [
        set(
            _git_nul(
                "diff-tree", "--no-commit-id", "--name-only", "-r", "-z", sha
            )
        )
        for sha in main_commits
    ]
    path_sequence_valid = _direction_control_path_sequence_valid(commit_paths)
    semantic_sequence_valid = False
    if path_sequence_valid:
        grant_sha = main_commits[-1]
        grant_parent_sha = _git("rev-parse", f"{grant_sha}^")
        grant_parent_ledger = load_ledger_at_ref(grant_parent_sha)
        final_target = next(
            (
                item for item in origin_ledger.get("active_lanes", [])
                if isinstance(item, dict) and item.get("package") == package_id
            ),
            None,
        )
        grant_delta_valid = _exact_direction_grant_delta(
            grant_parent_ledger, origin_ledger, package_id
        )
        if len(main_commits) == 1:
            semantic_sequence_valid = (
                grant_parent_sha == base
                and grant_parent_ledger.get("grant_close_preflight_repair")
                == GRANT_CLOSE_PREFLIGHT_REPAIR
                and grant_delta_valid
            )
        else:
            repair_sha = main_commits[0]
            repair_parent = _git("rev-parse", f"{repair_sha}^")
            repair_ledger = load_ledger_at_ref(repair_sha)
            semantic_sequence_valid = (
                base == GRANT_CLOSE_PREFLIGHT_REPAIR["origin_main"]
                and repair_parent == base
                and grant_parent_sha == repair_sha
                and repair_ledger.get("grant_close_preflight_repair")
                == GRANT_CLOSE_PREFLIGHT_REPAIR
                and grant_delta_valid
            )
        semantic_sequence_valid = bool(
            semantic_sequence_valid
            and isinstance(final_target, dict)
            and isinstance(final_target.get("merge_grant"), dict)
            and final_target["merge_grant"].get("reviewed_remote_sha")
            == candidate_sha
        )
    return (
        main_paths,
        path_sequence_valid and semantic_sequence_valid,
        len(main_commits),
    )


def _collect_direction_candidate_merge(
    package_id: str,
    candidate_worktree: str,
) -> tuple[dict, dict]:
    """Verify a frozen candidate with the freshly fetched main control code."""
    raw_candidate = Path(candidate_worktree)
    if not raw_candidate.is_absolute():
        raise ValueError("--candidate-worktree must be an absolute path")
    candidate = raw_candidate.resolve(strict=True)
    if str(raw_candidate) != str(candidate):
        raise ValueError("--candidate-worktree must be the exact worktree top-level path")
    candidate_top = Path(
        _git_at(candidate, "rev-parse", "--show-toplevel")
    ).resolve()
    if candidate_top != candidate:
        raise ValueError("--candidate-worktree must name the exact Git worktree top level")
    if candidate == ROOT.resolve():
        raise ValueError("candidate worktree must differ from the verifier worktree")
    registered = _registered_worktrees(ROOT)
    if registered.count(ROOT.resolve()) != 1 or registered.count(candidate) != 1:
        raise RuntimeError(
            "candidate and verifier must be exactly registered Git worktrees"
        )

    verifier_origin = _authoritative_azure_origin(ROOT)
    candidate_origin = _authoritative_azure_origin(candidate)
    if candidate_origin != verifier_origin:
        raise RuntimeError("candidate and verifier must share the authoritative Azure origin")
    _, initial_refs = _authoritative_ref_snapshot(
        ROOT, ["main"], expected_origin=verifier_origin
    )
    verifier = collect_facts(fetch=False, include_changed_paths=False)
    verifier["fetched"] = True
    verifier["origin_url"] = verifier_origin
    verifier["origin_is_azure"] = True
    if verifier["origin_main"] != initial_refs["main"]:
        raise RuntimeError("captured origin/main does not equal the advertised main branch")
    if verifier["head"] != verifier["origin_main"]:
        raise RuntimeError("direction verifier HEAD must equal freshly fetched origin/main")
    if verifier["tracked_changes"] or verifier["untracked_changes"]:
        raise RuntimeError("direction verifier worktree must be clean")
    script_relative = SCRIPT_PATH.relative_to(ROOT).as_posix()
    if SCRIPT_PATH.read_bytes() != _git_bytes_at(
        ROOT, "show", f"{verifier['origin_main']}:{script_relative}"
    ):
        raise RuntimeError("direction verifier script must equal origin/main")
    if _absolute_git_common_dir(candidate) != _absolute_git_common_dir(ROOT):
        raise RuntimeError("candidate must share the verifier Git common directory")
    origin_main = verifier["origin_main"]
    origin_ledger = load_ledger_at_ref(origin_main)
    lanes = origin_ledger.get("active_lanes")
    target = next(
        (
            lane for lane in lanes
            if isinstance(lane, dict) and lane.get("package") == package_id
        ),
        None,
    ) if isinstance(lanes, list) else None
    if not isinstance(target, dict):
        raise RuntimeError("direction candidate package is not active on origin/main")
    if target.get("lane_class") != "direction_authority" or target.get("production_capable") is not False:
        raise RuntimeError("--candidate-worktree is only for non-production direction lanes")
    target_branch = target.get("branch")
    if not isinstance(target_branch, str) or not _is_valid_implementation_branch(target_branch):
        raise RuntimeError("direction lane has no safe candidate branch")
    _, fetched_refs = _authoritative_ref_snapshot(
        ROOT, ["main", target_branch], expected_origin=verifier_origin
    )
    if fetched_refs["main"] != origin_main:
        raise RuntimeError("origin/main moved while direction authority was being loaded")
    grant_errors: list[str] = []
    grant = _direction_merge_grant(target, "merge target", grant_errors)
    if grant_errors or grant is None:
        raise RuntimeError("direction lane has no valid merge grant: " + "; ".join(grant_errors))
    remote_ref = f"refs/remotes/origin/{target_branch}"
    remote_sha = fetched_refs[target_branch]
    if not FULL_GIT_SHA.fullmatch(remote_sha):
        raise RuntimeError("authorized direction candidate remote branch is missing")
    candidate_branch = _git_at(
        candidate, "symbolic-ref", "--quiet", "--short", "HEAD", check=False
    )
    candidate_head = _git_at(candidate, "rev-parse", "HEAD")
    if candidate_branch != target_branch:
        raise RuntimeError("candidate worktree branch must equal the lane branch")
    if candidate_head != remote_sha or remote_sha != grant.get("reviewed_remote_sha"):
        raise RuntimeError("candidate HEAD, remote tip, and reviewed SHA must match exactly")
    if _git_at(
        candidate, "rev-parse", "--verify", f"refs/heads/{target_branch}",
        check=False,
    ) != candidate_head:
        raise RuntimeError("candidate local branch ref must equal candidate HEAD")
    if _clean_status_entries(candidate):
        raise RuntimeError("candidate worktree must be clean")

    main_paths, sequence_valid, behind = _direction_main_sequence_facts(
        origin_ledger, package_id, candidate_head, origin_main
    )
    facts = {
        **verifier,
        "branch": target_branch,
        "head": candidate_head,
        "ahead": int(_git("rev-list", "--count", f"{origin_main}..{candidate_head}")),
        "behind": behind,
        "tracked_changes": 0,
        "untracked_changes": 0,
        "changed_paths": sorted(
            _git_nul(
                "diff", "--name-only", "-z", f"{origin_main}...{candidate_head}"
            )
        ),
        "merge_target_remote_sha": remote_sha,
        "merge_main_changed_paths": main_paths,
        "merge_main_control_commits_valid": sequence_valid,
        "direction_candidate_verified_from_main": True,
        "verifier_repository": str(ROOT.resolve()),
        "verifier_branch": verifier["branch"],
        "verifier_head": origin_main,
        "candidate_repository": str(candidate),
        "candidate_branch": candidate_branch,
        "candidate_head": candidate_head,
        "candidate_remote_ref": remote_ref,
    }

    # Refresh once more and prove no authority or candidate endpoint moved
    # while the facts were being assembled.
    _, final_refs = _authoritative_ref_snapshot(
        ROOT, ["main", target_branch], expected_origin=verifier_origin
    )
    if final_refs != fetched_refs:
        raise RuntimeError("origin authority refs moved during direction validation")
    if _git("rev-parse", "HEAD") != origin_main or _git("rev-parse", "origin/main") != origin_main:
        raise RuntimeError("verifier or origin/main moved during direction validation")
    if _git("rev-parse", "--verify", remote_ref, check=False) != remote_sha:
        raise RuntimeError("candidate remote branch moved during direction validation")
    if _git_at(candidate, "rev-parse", "HEAD") != candidate_head:
        raise RuntimeError("candidate HEAD moved during direction validation")
    if _git_at(
        candidate, "symbolic-ref", "--quiet", "--short", "HEAD", check=False
    ) != target_branch:
        raise RuntimeError("candidate branch moved during direction validation")
    if _git_at(
        candidate, "rev-parse", "--verify", f"refs/heads/{target_branch}",
        check=False,
    ) != candidate_head:
        raise RuntimeError("candidate local branch ref moved during validation")
    if _clean_status_entries(candidate):
        raise RuntimeError("candidate worktree changed during direction validation")
    if (
        _absolute_git_common_dir(candidate) != _absolute_git_common_dir(ROOT)
        or _authoritative_azure_origin(candidate) != verifier_origin
        or _authoritative_azure_origin(ROOT) != verifier_origin
        or _registered_worktrees(ROOT).count(candidate) != 1
    ):
        raise RuntimeError("candidate worktree identity changed during validation")
    if SCRIPT_PATH.read_bytes() != _git_bytes_at(
        ROOT, "show", f"{origin_main}:{script_relative}"
    ):
        raise RuntimeError("verifier script changed during direction validation")
    return origin_ledger, facts


def evaluate_policy(
    ledger: dict,
    facts: dict,
    package_id: str,
    intent: str,
    require_clean: bool = False,
    origin_ledger: dict | None = None,
    candidate_baseline: bytes | None = None,
    origin_baseline: bytes | None = None,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    raw_mode = ledger.get("operating_mode")
    mode = raw_mode if isinstance(raw_mode, dict) else {}
    if intent != "activate" and not isinstance(raw_mode, dict):
        errors.append("lane ledger operating_mode must be an object")

    if not facts.get("origin_is_azure"):
        errors.append("origin is not the authoritative Azure DevOps remote")
    if not facts.get("branch"):
        errors.append("detached HEAD is not an authorized write lane")
    if facts.get("branch") == "main" and intent != "read":
        errors.append("writes and releases may not run directly from main")
    if facts.get("behind", 0) and intent != "merge":
        errors.append(f"checkout is {facts['behind']} commit(s) behind origin/main")
    if require_clean and (
        facts.get("tracked_changes", 0) or facts.get("untracked_changes", 0)
    ):
        errors.append("checkout is not clean")

    if intent == "read":
        if not mode.get("read_only_work_allowed", False):
            errors.append("the current operating mode disallows read-only work")
        return errors, warnings

    if intent == "merge":
        target: dict | None = None
        origin_mode: dict = {}
        if origin_ledger is None or not isinstance(origin_ledger, dict):
            # Preserve the standing generic active/closing-lane merge contract
            # for all lanes that are not the special reviewed direction flow.
            pass
        else:
            origin_mode, _, _, origin_by_package = _activation_snapshot(
                origin_ledger, "origin/main", errors
            )
            target = origin_by_package.get(package_id.casefold())
            is_direction_target = bool(
                isinstance(target, dict)
                and target.get("lane_class") == "direction_authority"
                and target.get("production_capable") is False
            )
            if not is_direction_target:
                target = None
            else:
                if not facts.get("fetched"):
                    errors.append("direction merge requires --fetch")
                if not require_clean:
                    errors.append("direction merge requires --require-clean")
        if origin_ledger is None or not isinstance(origin_ledger, dict) or target is None:
            # Fall through to the legacy generic merge evaluation below.
            pass
        else:
            grant = _direction_merge_grant(target, "merge target", errors)
            allowed = origin_mode.get("merge_allowed_for")
            if not isinstance(allowed, list) or package_id not in allowed:
                errors.append(f"merge is blocked for {package_id} on origin/main")
            if facts.get("branch") != target.get("branch"):
                errors.append("merge branch must equal the active target branch")
            reviewed_sha = grant.get("reviewed_remote_sha") if grant else None
            if facts.get("head") != reviewed_sha:
                errors.append("merge HEAD must equal the reviewed_remote_sha")
            if facts.get("merge_target_remote_sha") != reviewed_sha:
                errors.append("merge target remote tip must equal the reviewed_remote_sha")
            _validate_changed_paths_within_lane(target, facts, "merge", errors)
            main_paths = facts.get("merge_main_changed_paths")
            expected_behind = (
                2 if package_id == "PS-PROFILE-EXPERIENCE-001" else 1
            )
            expected_main_paths = (
                DIRECTION_MERGE_CONTROL_PATHS
                if expected_behind == 2 else set(GRANT_ALLOWED_SURFACES)
            )
            if facts.get("behind") != expected_behind:
                errors.append(
                    "direction merge requires exactly "
                    f"{expected_behind} verified main control commit(s)"
                )
            if not isinstance(main_paths, list) or not all(
                isinstance(path, str) and path for path in main_paths
            ):
                errors.append("merge requires main-side changed path evidence")
            else:
                normalized_main: list[str] = []
                for index, raw_path in enumerate(main_paths):
                    path = _normalize_repo_surface(
                        raw_path, f"merge main_changed_paths[{index}]", errors
                    )
                    if path is not None:
                        normalized_main.append(path)
                if set(normalized_main) != expected_main_paths:
                    errors.append(
                        "direction merge requires the exact reviewed control paths"
                    )
                if facts.get("merge_main_control_commits_valid") is not True:
                    errors.append(
                        "direction merge requires the exact repair-plus-target-grant main commit sequence"
                    )
            if facts.get("behind") == expected_behind:
                warnings.append(
                    f"merge candidate is {facts['behind']} commit(s) behind origin/main; "
                    "only the exact verified control sequence is tolerated"
                )
            return errors, warnings

    if intent == "grant":
        if not facts.get("fetched"):
            errors.append("grant requires --fetch")
        if not require_clean:
            errors.append("grant requires --require-clean")
        if origin_ledger is None or not isinstance(origin_ledger, dict):
            errors.append("grant requires the fetched origin/main lane ledger")
            return errors, warnings
        if facts.get("ahead") != 1 or facts.get("behind") != 0:
            errors.append("grant control branch must be exactly one commit ahead of origin/main")
        if not _valid_utc_timestamp(ledger.get("updated_at")):
            errors.append("grant ledger updated_at must be a real UTC timestamp")
        elif not _valid_utc_timestamp(origin_ledger.get("updated_at")):
            errors.append("origin/main ledger updated_at must be a real UTC timestamp")
        elif not _utc_timestamp_strictly_advances(
            ledger.get("updated_at"), origin_ledger.get("updated_at")
        ):
            errors.append("grant ledger updated_at must strictly advance origin/main")
        candidate_mode, candidate_policy, candidate_lanes, candidate_by_package = (
            _activation_snapshot(ledger, "candidate", errors)
        )
        origin_mode, origin_policy, origin_lanes, origin_by_package = (
            _activation_snapshot(origin_ledger, "origin/main", errors)
        )
        target = origin_by_package.get(package_id.casefold())
        candidate_target = candidate_by_package.get(package_id.casefold())
        if target is None or candidate_target is None:
            errors.append(f"grant requires {package_id} to remain active")
            return errors, warnings
        branch = facts.get("branch")
        if not isinstance(branch, str) or not GRANT_BRANCH_PATTERN.fullmatch(branch):
            errors.append(
                "grant must run from a dedicated control-only branch matching "
                f"{GRANT_BRANCH_PATTERN.pattern!r}"
            )
        if candidate_policy != origin_policy:
            errors.append("grant may not change activation_policy")
        if list(candidate_by_package) != list(origin_by_package):
            errors.append("grant must preserve active package set and order")
        if len(candidate_lanes) != len(origin_lanes):
            errors.append("grant may not change active-lane capacity")
        for origin_lane, candidate_lane in zip(
            origin_lanes, candidate_lanes, strict=False
        ):
            if origin_lane.get("package") != package_id:
                if candidate_lane != origin_lane:
                    errors.append(
                        "grant may not change another active lane: "
                        f"{origin_lane.get('package', '(unknown)')}"
                    )
                continue
            expected_lane = dict(origin_lane)
            expected_lane["merge_grant"] = candidate_lane.get("merge_grant")
            if candidate_lane != expected_lane:
                errors.append("grant may only add merge_grant to the target lane")
            grant = _direction_merge_grant(candidate_lane, "grant target", errors)
            if "merge_grant" in origin_lane:
                errors.append("grant target already has a merge_grant")
            if candidate_lane.get("owner_decisions") != origin_lane.get("owner_decisions"):
                errors.append("grant may not append or change owner_decisions")
            if grant is not None:
                if grant.get("granted_at") != ledger.get("updated_at"):
                    errors.append(
                        "grant merge_grant.granted_at must equal ledger updated_at"
                    )
                reviewed_sha = grant.get("reviewed_remote_sha")
                remote_sha = facts.get("grant_target_remote_sha")
                if reviewed_sha != remote_sha:
                    errors.append(
                        "grant reviewed_remote_sha must equal the fetched target branch tip"
                    )
                evidence_paths = _paths_within_lane(
                    grant.get("review_evidence_paths"), candidate_lane,
                    "grant review_evidence_paths", errors,
                )
                existing = facts.get("grant_review_evidence_existing")
                if existing != evidence_paths:
                    errors.append(
                        "grant requires every review evidence path to exist at reviewed_remote_sha"
                    )
                evidence = facts.get("grant_review_evidence")
                if not isinstance(evidence, list) or len(evidence) != len(evidence_paths):
                    errors.append("grant requires exact review evidence content for every path")
                else:
                    review = grant.get("independent_review")
                    independent_sha = review.get("reviewed_sha") if isinstance(review, dict) else None
                    for item, path in zip(evidence, evidence_paths, strict=True):
                        if not isinstance(item, dict) or item.get("path") != path:
                            errors.append("grant review evidence content/path binding is invalid")
                            continue
                        if (
                            item.get("object_type") != "blob"
                            or item.get("object_mode") != "100644"
                            or not path.casefold().endswith(".md")
                        ):
                            errors.append("grant review evidence must be regular Markdown blob files")
                        content = item.get("content")
                        if not isinstance(content, str) or not content:
                            errors.append(
                                "grant review evidence content must be non-empty UTF-8 text"
                            )
                            continue
                        if item.get("git_blob_sha") != review.get("evidence_git_blob_sha"):
                            errors.append("grant review evidence Git blob SHA is not attested")
                        if item.get("bytes_sha256") != review.get("evidence_bytes_sha256"):
                            errors.append("grant review evidence bytes SHA-256 is not attested")
        expected_mode = dict(origin_mode)
        origin_merge = origin_mode.get("merge_allowed_for")
        if not isinstance(origin_merge, list):
            errors.append("origin/main merge_allowed_for must be a list")
        else:
            expected_mode = dict(origin_mode)
            expected_mode["merge_allowed_for"] = [*origin_merge, package_id]
            if candidate_mode != expected_mode:
                errors.append(
                    "grant operating_mode may only append target to merge_allowed_for"
                )
        if _root_changes(ledger, origin_ledger) != {
            "updated_at", "operating_mode", "active_lanes"
        }:
            errors.append(
                "grant must change exactly updated_at, operating_mode, and active_lanes"
            )
        _validate_baseline_unchanged(
            candidate_baseline, origin_baseline, label="grant", errors=errors
        )
        if set(facts.get("changed_paths") or []) != set(GRANT_ALLOWED_SURFACES):
            errors.append(
                "grant control branch must change exactly: "
                + ", ".join(sorted(GRANT_ALLOWED_SURFACES))
            )
        return errors, warnings

    if intent == "close":
        if not facts.get("fetched"):
            errors.append("close requires --fetch")
        if not require_clean:
            errors.append("close requires --require-clean")
        if origin_ledger is None or not isinstance(origin_ledger, dict):
            errors.append("close requires the fetched origin/main lane ledger")
            return errors, warnings
        if facts.get("ahead") != 1 or facts.get("behind") != 0:
            errors.append("close control branch must be exactly one commit ahead of origin/main")
        if not _valid_utc_timestamp(ledger.get("updated_at")):
            errors.append("close ledger updated_at must be a real UTC timestamp")
        elif not _valid_utc_timestamp(origin_ledger.get("updated_at")):
            errors.append("origin/main ledger updated_at must be a real UTC timestamp")
        elif not _utc_timestamp_strictly_advances(
            ledger.get("updated_at"), origin_ledger.get("updated_at")
        ):
            errors.append("close ledger updated_at must strictly advance origin/main")
        candidate_mode, candidate_policy, candidate_lanes, _ = _activation_snapshot(
            ledger, "candidate", errors
        )
        origin_mode, origin_policy, origin_lanes, origin_by_package = _activation_snapshot(
            origin_ledger, "origin/main", errors
        )
        target = origin_by_package.get(package_id.casefold())
        if target is None:
            errors.append(f"close requires {package_id} to be active on origin/main")
            return errors, warnings
        _direction_merge_grant(target, "close target", errors)
        origin_merge_allowed = origin_mode.get("merge_allowed_for")
        if not isinstance(origin_merge_allowed, list) or package_id not in origin_merge_allowed:
            errors.append("close requires target merge permission on origin/main")
        branch = facts.get("branch")
        if not isinstance(branch, str) or not CLOSE_BRANCH_PATTERN.fullmatch(branch):
            errors.append(
                "close must run from a dedicated control-only branch matching "
                f"{CLOSE_BRANCH_PATTERN.pattern!r}"
            )
        if candidate_policy != origin_policy:
            errors.append("close may not change activation_policy")
        remaining = [lane for lane in origin_lanes if lane.get("package") != package_id]
        if candidate_lanes != remaining:
            errors.append("close must remove exactly its target active lane")
        expected_state = "active_delivery" if remaining else "controlled_idle"
        expected_mode = dict(origin_mode)
        expected_mode["state"] = expected_state
        for field in (
            "writes_allowed_for", "merge_allowed_for", "cleanup_allowed_for",
            "release_allowed_for",
        ):
            values = origin_mode.get(field)
            if not isinstance(values, list):
                errors.append(f"origin/main operating_mode.{field} must be a list")
            else:
                expected_mode[field] = [value for value in values if value != package_id]
        remaining_ids = _remaining_package_ids(remaining)
        expected_exit_authority = (
            "Active writer lanes: " + ", ".join(remaining_ids)
            + f". {package_id} is merged_closed and retains no authority."
            if remaining_ids
            else f"No active writer lanes. {package_id} is merged_closed and retains no authority."
        )
        expected_mode["exit_authority"] = expected_exit_authority
        if candidate_mode != expected_mode:
            errors.append("close may only remove the target package's authority")
        if candidate_mode.get("exit_authority") != expected_exit_authority:
            errors.append("close exit_authority must equal the deterministic inert value")
        origin_closing = origin_ledger.get("closing_lanes")
        candidate_closing = ledger.get("closing_lanes")
        if not isinstance(origin_closing, list) or not isinstance(candidate_closing, list):
            errors.append("close closing_lanes must remain lists")
        elif any(
            isinstance(item, dict) and item.get("package") == package_id
            for item in origin_closing
        ):
            errors.append("close target already exists in closing_lanes")
        elif candidate_closing[:-1] != origin_closing or len(candidate_closing) != len(origin_closing) + 1:
            errors.append("close must append exactly one closing record")
        else:
            closing = candidate_closing[-1]
            expected_keys = set(target) | {
                "disposition", "closed_at", "reviewed_remote_sha",
                "merged_main_sha", "package_merge_sha", "close_evidence_paths",
            }
            if not isinstance(closing, dict) or set(closing) != expected_keys:
                errors.append("close record must preserve target and add exact close fields")
            elif any(closing.get(key) != value for key, value in target.items()):
                errors.append("close record must preserve the exact active lane")
            else:
                if closing.get("disposition") != "merged_closed":
                    errors.append("close disposition must be merged_closed")
                if not _valid_utc_timestamp(closing.get("closed_at")):
                    errors.append("close closed_at must be a UTC timestamp")
                elif closing.get("closed_at") != ledger.get("updated_at"):
                    errors.append("close closed_at must equal ledger updated_at")
                if closing.get("reviewed_remote_sha") != target.get("merge_grant", {}).get("reviewed_remote_sha"):
                    errors.append("close reviewed_remote_sha must preserve the granted candidate")
                if closing.get("merged_main_sha") != facts.get("origin_main"):
                    errors.append("close merged_main_sha must equal fetched origin/main")
                if closing.get("package_merge_sha") != facts.get("close_package_merge_sha"):
                    errors.append("close package_merge_sha must equal the verified merge commit")
                evidence = _paths_within_lane(
                    closing.get("close_evidence_paths"), target,
                    "close close_evidence_paths", errors,
                )
                if evidence != facts.get("close_evidence_existing"):
                    errors.append("close requires every bounded evidence path at package merge SHA")
        if facts.get("close_target_remote_sha") != target.get("merge_grant", {}).get("reviewed_remote_sha"):
            errors.append("close requires target remote tip to remain the reviewed SHA")
        if facts.get("close_surface_tree_equal") is not True:
            errors.append(
                "close requires reviewed candidate, package merge, and captured main "
                "writable-surface tree equivalence"
            )
        if facts.get("close_package_merge_ancestor") is not True:
            errors.append("close package_merge_sha must be an ancestor of captured origin/main")
        if facts.get("close_package_merge_introduced_candidate") is not True:
            errors.append(
                "close package_merge_sha must be the commit that introduced the reviewed candidate surfaces"
            )
        if _root_changes(ledger, origin_ledger) != {
            "updated_at", "operating_mode", "active_lanes", "closing_lanes"
        }:
            errors.append(
                "close must change exactly updated_at, operating_mode, active_lanes, and closing_lanes"
            )
        _validate_baseline_pause_delta(
            candidate_baseline, origin_baseline, paused_package=package_id,
            remaining_lanes=remaining, action="close", errors=errors,
        )
        if set(facts.get("changed_paths") or []) != set(CLOSE_ALLOWED_SURFACES):
            errors.append(
                "close control branch must change exactly: "
                + ", ".join(sorted(CLOSE_ALLOWED_SURFACES))
            )
        return errors, warnings

    if intent == "transfer":
        if not facts.get("fetched"):
            errors.append("writer transfer requires --fetch")
        if not require_clean:
            errors.append("writer transfer requires --require-clean")
        if origin_ledger is None or not isinstance(origin_ledger, dict):
            errors.append(
                "writer transfer requires the fetched origin/main lane ledger"
            )
            return errors, warnings

        (
            candidate_mode,
            candidate_policy,
            candidate_lanes,
            candidate_by_package,
        ) = _activation_snapshot(ledger, "candidate", errors)
        (
            origin_mode,
            origin_policy,
            origin_lanes,
            origin_by_package,
        ) = _activation_snapshot(origin_ledger, "origin/main", errors)

        package_key = package_id.casefold()
        origin_lane = origin_by_package.get(package_key)
        candidate_lane = candidate_by_package.get(package_key)
        if origin_lane is None:
            errors.append(
                f"writer transfer requires {package_id} to be active on origin/main"
            )
        if candidate_lane is None:
            errors.append(
                f"writer transfer candidate must retain active lane {package_id}"
            )

        branch = facts.get("branch")
        if not isinstance(branch, str) or not TRANSFER_BRANCH_PATTERN.fullmatch(
            branch
        ):
            errors.append(
                "writer transfer must run from a dedicated control-only branch "
                f"matching {TRANSFER_BRANCH_PATTERN.pattern!r}"
            )
        if isinstance(origin_lane, dict) and branch == origin_lane.get("branch"):
            errors.append(
                "writer transfer control branch must differ from the active lane branch"
            )

        if candidate_mode != origin_mode:
            errors.append("writer transfer may not change operating_mode")
        elif package_id not in candidate_mode.get("writes_allowed_for", []):
            errors.append(
                "writer transfer package must remain authorized in writes_allowed_for"
            )
        if candidate_policy != origin_policy:
            errors.append("writer transfer may not change activation_policy")

        if list(candidate_by_package) != list(origin_by_package):
            errors.append(
                "writer transfer must preserve the active package set and order"
            )
        if len(candidate_lanes) != len(origin_lanes):
            errors.append("writer transfer may not change active-lane capacity")
        else:
            for origin_item, candidate_item in zip(
                origin_lanes, candidate_lanes, strict=True
            ):
                if origin_item.get("package") != package_id:
                    if candidate_item != origin_item:
                        errors.append(
                            "writer transfer may not change another active lane: "
                            f"{origin_item.get('package', '(unknown)')}"
                        )
                elif candidate_item.get("package") != package_id:
                    errors.append(
                        "writer transfer must preserve the target lane position"
                    )

        if isinstance(origin_lane, dict) and isinstance(candidate_lane, dict):
            allowed_lane_changes = {
                "writer",
                "owner_decisions",
                "completion_evidence",
                "model_routing",
                "sequence",
            }
            lane_changes = {
                key
                for key in set(origin_lane) | set(candidate_lane)
                if origin_lane.get(key) != candidate_lane.get(key)
            }
            required_lane_changes = {"writer", "owner_decisions"}
            if not required_lane_changes.issubset(lane_changes):
                errors.append(
                    "writer transfer must change writer and append one owner decision"
                )
            unexpected_lane_changes = sorted(lane_changes - allowed_lane_changes)
            if unexpected_lane_changes:
                errors.append(
                    "writer transfer may not change lane fields: "
                    + ", ".join(unexpected_lane_changes)
                )

            origin_writer = origin_lane.get("writer")
            candidate_writer = candidate_lane.get("writer")
            if (
                not isinstance(candidate_writer, str)
                or not candidate_writer.strip()
                or candidate_writer == origin_writer
            ):
                errors.append(
                    "writer transfer requires a non-empty replacement writer"
                )

            origin_decisions = origin_lane.get("owner_decisions")
            candidate_decisions = candidate_lane.get("owner_decisions")
            appended_decision: dict | None = None
            if (
                not isinstance(origin_decisions, list)
                or not isinstance(candidate_decisions, list)
                or candidate_decisions[:-1] != origin_decisions
                or len(candidate_decisions) != len(origin_decisions) + 1
            ):
                errors.append(
                    "writer transfer must preserve owner decisions and append exactly one"
                )
            elif isinstance(candidate_decisions[-1], dict):
                appended_decision = candidate_decisions[-1]
                if set(appended_decision) != {"date", "decision"} or not all(
                    isinstance(appended_decision.get(field), str)
                    and appended_decision[field].strip()
                    for field in ("date", "decision")
                ):
                    errors.append(
                        "writer transfer owner decision must contain non-empty date and decision"
                    )
            else:
                errors.append("writer transfer appended owner decision must be an object")

            remote_sha = facts.get("transfer_target_remote_sha")
            if not isinstance(remote_sha, str) or not FULL_GIT_SHA.fullmatch(
                remote_sha
            ):
                errors.append(
                    "writer transfer requires the active lane branch to be pushed to origin"
                )
            elif (
                appended_decision is not None
                and remote_sha not in appended_decision.get("decision", "")
            ):
                errors.append(
                    "writer transfer owner decision must name the exact pushed handoff SHA"
                )

            if "completion_evidence" in lane_changes:
                origin_evidence = origin_lane.get("completion_evidence")
                candidate_evidence = candidate_lane.get("completion_evidence")
                if (
                    not isinstance(origin_evidence, list)
                    or not isinstance(candidate_evidence, list)
                    or len(candidate_evidence) != len(origin_evidence)
                    or not all(
                        isinstance(item, str) and item.strip()
                        for item in candidate_evidence
                    )
                ):
                    errors.append(
                        "writer transfer completion_evidence must preserve its string-list shape"
                    )

            if "model_routing" in lane_changes:
                origin_routing = origin_lane.get("model_routing")
                candidate_routing = candidate_lane.get("model_routing")
                if (
                    not isinstance(origin_routing, dict)
                    or not isinstance(candidate_routing, dict)
                    or candidate_routing.get("decided_by")
                    != origin_routing.get("decided_by")
                    or candidate_routing.get("date") != origin_routing.get("date")
                    or not all(
                        isinstance(value, str) and value.strip()
                        for value in candidate_routing.values()
                    )
                ):
                    errors.append(
                        "writer transfer model_routing must preserve owner/date and non-empty values"
                    )

            if "sequence" in lane_changes and (
                not isinstance(candidate_lane.get("sequence"), str)
                or not candidate_lane["sequence"].strip()
            ):
                errors.append("writer transfer sequence must remain non-empty")

        if _root_changes(ledger, origin_ledger) != {"updated_at", "active_lanes"}:
            errors.append(
                "writer transfer must change exactly updated_at and active_lanes"
            )
        _validate_baseline_unchanged(
            candidate_baseline,
            origin_baseline,
            label="writer transfer",
            errors=errors,
        )

        raw_changed_paths = facts.get("changed_paths")
        if not isinstance(raw_changed_paths, list) or set(raw_changed_paths) != set(
            TRANSFER_ALLOWED_SURFACES
        ):
            errors.append(
                "writer transfer control branch must change exactly: "
                + ", ".join(sorted(TRANSFER_ALLOWED_SURFACES))
            )
        return errors, warnings

    if intent == "pause":
        if not facts.get("fetched"):
            errors.append("pause requires --fetch")
        if not require_clean:
            errors.append("pause requires --require-clean")
        if origin_ledger is None or not isinstance(origin_ledger, dict):
            errors.append("pause requires the fetched origin/main lane ledger")
            return errors, warnings

        candidate_mode, candidate_policy, candidate_lanes, _ = _activation_snapshot(
            ledger, "candidate", errors
        )
        origin_mode, origin_policy, origin_lanes, origin_by_package = _activation_snapshot(
            origin_ledger, "origin/main", errors
        )
        target = origin_by_package.get(package_id.casefold())
        if target is None:
            errors.append(f"pause requires {package_id} to be active on origin/main")
            return errors, warnings
        pause_branch = facts.get("branch")
        if not isinstance(pause_branch, str) or not PAUSE_BRANCH_PATTERN.fullmatch(
            pause_branch
        ):
            errors.append(
                "pause must run from a dedicated control-only branch matching "
                f"{PAUSE_BRANCH_PATTERN.pattern!r}"
            )
        if pause_branch == target.get("branch"):
            errors.append("pause control branch must differ from the active lane branch")
        if candidate_policy != origin_policy:
            errors.append("pause may not change activation_policy")

        remaining_lanes = [
            lane for lane in origin_lanes if lane.get("package") != package_id
        ]
        if candidate_lanes != remaining_lanes:
            errors.append("pause must remove exactly its own active lane")
        _validate_lane_mix(remaining_lanes, "pause candidate", errors)

        expected_state = "active_delivery" if remaining_lanes else "controlled_idle"
        if candidate_mode.get("state") != expected_state:
            errors.append(f"pause candidate must use {expected_state}")
        if candidate_mode.get("writes_allowed_for") != [
            lane.get("package") for lane in remaining_lanes
        ]:
            errors.append("pause writes_allowed_for must equal the remaining active lanes")
        for field in ("merge_allowed_for", "cleanup_allowed_for", "release_allowed_for"):
            origin_values = origin_mode.get(field)
            expected_values = (
                [value for value in origin_values if value != package_id]
                if isinstance(origin_values, list)
                else origin_values
            )
            if candidate_mode.get(field) != expected_values:
                errors.append(f"pause operating_mode.{field} may only drop {package_id}")
        allowed_mode_changes = {
            "state",
            "writes_allowed_for",
            "merge_allowed_for",
            "cleanup_allowed_for",
            "release_allowed_for",
            "exit_authority",
        }
        marker = object()
        unexpected_mode_changes = {
            key
            for key in set(candidate_mode) | set(origin_mode)
            if candidate_mode.get(key, marker) != origin_mode.get(key, marker)
        } - allowed_mode_changes
        if unexpected_mode_changes:
            errors.append(
                "pause may not change operating_mode fields: "
                + ", ".join(sorted(unexpected_mode_changes))
            )
        exit_authority = candidate_mode.get("exit_authority")
        if not isinstance(exit_authority, str) or (
            package_id not in exit_authority or "paused" not in exit_authority.lower()
        ):
            errors.append("pause exit_authority must identify the paused package")

        origin_paused = origin_ledger.get("paused_lanes")
        candidate_paused = ledger.get("paused_lanes")
        if not isinstance(origin_paused, list) or not isinstance(candidate_paused, list):
            errors.append("pause paused_lanes must remain lists")
        elif len(candidate_paused) != len(origin_paused) + 1 or candidate_paused[:-1] != origin_paused:
            errors.append("pause must append exactly one preserved paused-lane record")
        else:
            paused_record = candidate_paused[-1]
            if not isinstance(paused_record, dict):
                errors.append("pause appended record must be an object")
            else:
                expected_keys = set(target) | {
                    "disposition",
                    "paused_at",
                    "pause_reason",
                    "resume_contract",
                    "preserved_head_sha",
                }
                if set(paused_record) != expected_keys or any(
                    paused_record.get(key) != value for key, value in target.items()
                ):
                    errors.append("pause must preserve the exact active-lane record")
                if paused_record.get("disposition") != "paused_preserved":
                    errors.append("pause disposition must be paused_preserved")
                for field in ("paused_at", "pause_reason", "resume_contract"):
                    _nonempty_string(
                        paused_record.get(field), f"pause record {field}", errors
                    )
                preserved_head_sha = paused_record.get("preserved_head_sha")
                remote_head_sha = facts.get("pause_target_remote_sha")
                if (
                    not isinstance(preserved_head_sha, str)
                    or not FULL_GIT_SHA.fullmatch(preserved_head_sha)
                ):
                    errors.append("pause record preserved_head_sha must be a full Git SHA")
                if (
                    not isinstance(remote_head_sha, str)
                    or not FULL_GIT_SHA.fullmatch(remote_head_sha)
                ):
                    errors.append(
                        "pause requires the active lane branch to be pushed to origin"
                    )
                elif preserved_head_sha != remote_head_sha:
                    errors.append(
                        "pause record preserved_head_sha must equal the fetched "
                        "origin branch tip"
                    )

        expected_root_changes = {
            "updated_at",
            "operating_mode",
            "active_lanes",
            "paused_lanes",
        }
        if _root_changes(ledger, origin_ledger) != expected_root_changes:
            errors.append(
                "pause must change exactly updated_at, operating_mode, active_lanes, and paused_lanes"
            )

        _validate_baseline_pause_delta(
            candidate_baseline,
            origin_baseline,
            paused_package=package_id,
            remaining_lanes=remaining_lanes,
            errors=errors,
        )
        raw_changed_paths = facts.get("changed_paths")
        if not isinstance(raw_changed_paths, list) or not all(
            isinstance(path, str) and path for path in raw_changed_paths
        ):
            errors.append("pause changed_paths must be a list of non-empty strings")
        else:
            changed_paths = set(raw_changed_paths)
            if changed_paths != set(PAUSE_ALLOWED_SURFACES):
                errors.append(
                    "pause control branch must change exactly: "
                    + ", ".join(sorted(PAUSE_ALLOWED_SURFACES))
                )
        return errors, warnings

    if intent == "activate":
        added_package: str | None = None
        added_branch: str | None = None
        if not facts.get("fetched"):
            errors.append("activation requires --fetch")
        if not require_clean:
            errors.append("activation requires --require-clean")
        _nonempty_string(
            facts.get("head"), "activation captured HEAD SHA", errors
        )
        _nonempty_string(
            facts.get("origin_main"), "activation captured origin/main SHA", errors
        )
        mode, policy, active_lanes, candidate_by_package = _activation_snapshot(
            ledger,
            "candidate",
            errors,
        )
        state = mode.get("state")
        raw_allowed_states = policy.get("allowed_operating_states")
        if not isinstance(raw_allowed_states, list) or not all(
            isinstance(value, str) for value in raw_allowed_states
        ):
            errors.append(
                "activation policy allowed_operating_states must be a list of strings"
            )
            allowed_states: set[str] = set()
        else:
            allowed_states = set(raw_allowed_states)
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

        branch = facts.get("branch")
        branch_pattern = policy.get("branch_pattern")
        if not isinstance(branch, str) or not branch:
            errors.append("activation checkout branch must be a non-empty string")
        elif not isinstance(branch_pattern, str) or not branch_pattern:
            errors.append(
                "activation policy branch_pattern must be a non-empty string"
            )
        else:
            try:
                branch_matches = re.fullmatch(branch_pattern, branch)
            except re.error as exc:
                errors.append(
                    "activation policy branch_pattern is invalid: "
                    f"{exc}"
                )
            else:
                if not branch_matches:
                    errors.append(
                        f"activation branch does not match {branch_pattern!r}"
                    )

        lane_limit = policy.get("max_active_lanes")
        if lane_limit != MAX_ACTIVE_LANES:
            errors.append(
                f"activation policy must retain the {MAX_ACTIVE_LANES}-lane limit"
            )
        if policy.get("max_implementation_lanes") != MAX_IMPLEMENTATION_LANES:
            errors.append(
                "activation policy must retain the two-implementation-lane limit"
            )
        if (
            policy.get("max_direction_authority_lanes")
            != MAX_DIRECTION_AUTHORITY_LANES
        ):
            errors.append(
                "activation policy must retain the one-direction-authority-lane limit"
            )
        if policy.get("max_shared_foundation_lanes") != MAX_SHARED_FOUNDATION_LANES:
            errors.append(
                "activation policy must retain the one-shared-foundation-lane limit"
            )
        if (
            policy.get("max_production_capable_lanes")
            != MAX_PRODUCTION_CAPABLE_LANES
        ):
            errors.append(
                "activation policy must retain the one-production-capable-lane limit"
            )
        if set(policy.get("allowed_lane_classes") or []) != set(VALID_LANE_CLASSES):
            errors.append("activation policy allowed_lane_classes is not canonical")
        raw_allowed_surfaces = policy.get("allowed_surfaces")
        if not isinstance(raw_allowed_surfaces, list) or not all(
            isinstance(surface, str) and surface for surface in raw_allowed_surfaces
        ):
            errors.append(
                "activation policy allowed_surfaces must be a list of non-empty "
                "strings"
            )
            allowed_surfaces: set[str] = set()
        else:
            allowed_surfaces = set(raw_allowed_surfaces)

        bootstrap_matches = _exact_bootstrap_matches(ledger, facts, package_id)
        writer_transfer_repair_matches = (
            _exact_writer_transfer_preflight_repair_matches(
                ledger, facts, package_id
            )
        )
        grant_close_repair_matches = _exact_grant_close_preflight_repair_matches(
            ledger, facts, package_id
        )
        if bootstrap_matches:
            allowed_surfaces = set(BOOTSTRAP_CONTROL_REPAIR["allowed_surfaces"])
            warnings.append(
                "using the exact one-time bootstrap control-repair boundary"
            )
        elif writer_transfer_repair_matches:
            allowed_surfaces = set(
                WRITER_TRANSFER_PREFLIGHT_REPAIR["allowed_surfaces"]
            )
            warnings.append(
                "using the exact one-time writer-transfer preflight-repair boundary"
            )
        elif grant_close_repair_matches:
            allowed_surfaces = set(
                GRANT_CLOSE_PREFLIGHT_REPAIR["allowed_surfaces"]
            )
            warnings.append(
                "using the exact one-time grant-close preflight-repair boundary"
            )

        if origin_ledger is None:
            errors.append(
                "activation requires the fetched origin/main lane ledger"
            )
        elif not isinstance(origin_ledger, dict):
            errors.append("activation requires an origin/main lane ledger object")
        else:
            (
                origin_mode,
                origin_policy,
                origin_lanes,
                origin_by_package,
            ) = _activation_snapshot(origin_ledger, "origin/main", errors)

            if origin_mode.get("state") not in expected_states:
                errors.append(
                    "origin/main activation is allowed only from "
                    "controlled_idle or active_delivery"
                )

            if (
                not bootstrap_matches
                and not writer_transfer_repair_matches
                and not grant_close_repair_matches
                and origin_policy != policy
            ):
                errors.append(
                    "activation may not change activation_policy"
                )

            if lane_limit == MAX_ACTIVE_LANES and len(active_lanes) > lane_limit:
                errors.append(
                    f"activation candidate exceeds the {MAX_ACTIVE_LANES}-lane limit"
                )

            if grant_close_repair_matches:
                candidate_updated_at = ledger.get("updated_at")
                origin_updated_at = origin_ledger.get("updated_at")
                if not _valid_utc_timestamp(candidate_updated_at):
                    errors.append(
                        "grant-close preflight repair updated_at must be a real UTC timestamp"
                    )
                if not _valid_utc_timestamp(origin_updated_at):
                    errors.append(
                        "origin/main ledger updated_at must be a real UTC timestamp"
                    )
                elif not _utc_timestamp_strictly_advances(
                    candidate_updated_at, origin_updated_at
                ):
                    errors.append(
                        "grant-close preflight repair updated_at must strictly advance origin/main"
                    )
                if origin_policy != policy:
                    errors.append(
                        "grant-close preflight repair may not change activation_policy"
                    )
                if _root_changes(ledger, origin_ledger) != {
                    "updated_at", "grant_close_preflight_repair"
                }:
                    errors.append(
                        "grant-close preflight repair must change exactly updated_at "
                        "and grant_close_preflight_repair"
                    )
                if origin_ledger.get("grant_close_preflight_repair") is not None:
                    errors.append(
                        "grant-close preflight repair is one-time and already recorded"
                    )
                if ledger.get("grant_close_preflight_repair") != GRANT_CLOSE_PREFLIGHT_REPAIR:
                    errors.append("grant-close preflight repair record is not exact")
                _validate_baseline_unchanged(
                    candidate_baseline, origin_baseline,
                    label="grant-close preflight repair", errors=errors,
                )
            elif writer_transfer_repair_matches:
                if origin_policy != policy:
                    errors.append(
                        "writer-transfer preflight repair may not change activation_policy"
                    )
                root_changes = _root_changes(ledger, origin_ledger)
                expected_root_changes = {
                    "updated_at",
                    "writer_transfer_preflight_repair",
                }
                if root_changes != expected_root_changes:
                    errors.append(
                        "writer-transfer preflight repair must change exactly "
                        "updated_at and writer_transfer_preflight_repair"
                    )
                if origin_ledger.get("writer_transfer_preflight_repair") is not None:
                    errors.append(
                        "writer-transfer preflight repair is one-time and already recorded"
                    )
                if (
                    ledger.get("writer_transfer_preflight_repair")
                    != WRITER_TRANSFER_PREFLIGHT_REPAIR
                ):
                    errors.append(
                        "writer-transfer preflight repair record is not exact"
                    )
                _validate_baseline_unchanged(
                    candidate_baseline,
                    origin_baseline,
                    label="writer-transfer preflight repair",
                    errors=errors,
                )
            elif bootstrap_matches:
                if policy != EXPECTED_ACTIVATION_POLICY:
                    errors.append(
                        "bootstrap control repair activation_policy must match the exact code-controlled policy"
                    )
                root_changes = _root_changes(ledger, origin_ledger)
                expected_root_changes = {
                    "schema_version",
                    "updated_at",
                    "operating_mode",
                    "activation_policy",
                    "bootstrap_control_repair",
                    "bootstrap_control_repair_history",
                    "active_lanes",
                    "paused_lanes",
                }
                if root_changes != expected_root_changes:
                    errors.append(
                        "bootstrap control repair must change exactly the owner-authorized "
                        "ledger sections: "
                        + ", ".join(sorted(expected_root_changes))
                    )
                if ledger.get("schema_version") != 2:
                    errors.append("bootstrap control repair must set schema_version 2")
                if active_lanes:
                    errors.append(
                        "bootstrap control repair must leave no active writer lanes"
                    )
                if mode.get("state") != "controlled_idle":
                    errors.append(
                        "bootstrap control repair must enter controlled_idle"
                    )
                if mode.get("writes_allowed_for") != []:
                    errors.append(
                        "bootstrap control repair must clear writes_allowed_for"
                    )
                if mode.get("authorized_by") != "Pete" or mode.get(
                    "authorized_at"
                ) != "2026-08-10":
                    errors.append(
                        "bootstrap control repair must retain the exact owner authorization"
                    )
                if mode.get("exit_authority") != BOOTSTRAP_EXIT_AUTHORITY:
                    errors.append(
                        "bootstrap control repair exit_authority is not exact"
                    )
                for field in (
                    "read_only_work_allowed",
                    "release_allowed_for",
                    "blocked_actions",
                ):
                    if mode.get(field) != origin_mode.get(field):
                        errors.append(
                            f"bootstrap control repair may not change operating_mode.{field}"
                        )
                for field in ("merge_allowed_for", "cleanup_allowed_for"):
                    if mode.get(field) != []:
                        errors.append(
                            f"bootstrap control repair must clear stale operating_mode.{field}"
                        )
                history = ledger.get("bootstrap_control_repair_history")
                if history != [origin_ledger.get("bootstrap_control_repair")]:
                    errors.append(
                        "bootstrap control repair history must preserve the exact prior record"
                    )
                if ledger.get("closing_lanes") != origin_ledger.get("closing_lanes"):
                    errors.append("bootstrap control repair may not change closing_lanes")
                origin_paused = origin_ledger.get("paused_lanes")
                candidate_paused = ledger.get("paused_lanes")
                if not isinstance(origin_paused, list) or not isinstance(
                    candidate_paused, list
                ):
                    errors.append("bootstrap control repair paused_lanes must be lists")
                else:
                    if {
                        lane.get("package") for lane in origin_lanes
                    } != set(BOOTSTRAP_ORIGIN_ACTIVE_PACKAGES):
                        errors.append(
                            "bootstrap control repair origin/main active package set is not exact"
                        )
                    for paused in origin_paused:
                        if paused not in candidate_paused:
                            errors.append(
                                "bootstrap control repair must preserve every prior paused lane"
                            )
                    for origin_lane in origin_lanes:
                        matches = [
                            paused
                            for paused in candidate_paused
                            if isinstance(paused, dict)
                            and paused.get("package") == origin_lane.get("package")
                        ]
                        if len(matches) != 1 or any(
                            matches[0].get(key) != value
                            for key, value in origin_lane.items()
                        ):
                            errors.append(
                                "bootstrap control repair must preserve origin/main active lane "
                                f"{origin_lane.get('package', '(unknown)')} exactly when pausing it"
                            )
                        elif (
                            matches[0].get("disposition") != "paused_preserved"
                            or not all(
                                isinstance(matches[0].get(field), str)
                                and matches[0][field].strip()
                                for field in (
                                    "paused_at",
                                    "pause_reason",
                                    "resume_contract",
                                )
                            )
                        ):
                            errors.append(
                                "bootstrap control repair must record a complete preserved pause for "
                                f"{origin_lane.get('package', '(unknown)')}"
                            )
                    if len(candidate_paused) != len(origin_paused) + len(origin_lanes):
                        errors.append(
                            "bootstrap control repair may not add unrelated paused lanes"
                        )
            else:
                if (
                    ledger.get("bootstrap_control_repair")
                    != origin_ledger.get("bootstrap_control_repair")
                ):
                    errors.append(
                        "bootstrap control repair record does not match the "
                        "exact owner-authorized record"
                    )
                _validate_lane_mix(origin_lanes, "origin/main", errors)
                _validate_lane_mix(active_lanes, "candidate", errors)
                _validate_closing_lanes_retain_no_authority(
                    origin_ledger,
                    origin_mode,
                    errors,
                )
                if (
                    lane_limit == MAX_ACTIVE_LANES
                    and len(origin_lanes) >= lane_limit
                ):
                    errors.append(
                        "activation refused because the lane limit is full"
                    )

                origin_packages = set(origin_by_package)
                candidate_packages = set(candidate_by_package)
                removed_packages = sorted(
                    origin_packages - candidate_packages
                )
                if removed_packages:
                    errors.append(
                        "activation may not remove active lanes: "
                        + ", ".join(removed_packages)
                    )

                changed_packages = sorted(
                    package
                    for package in origin_packages & candidate_packages
                    if origin_by_package[package]
                    != candidate_by_package[package]
                )
                if changed_packages:
                    errors.append(
                        "activation may not modify existing active lanes: "
                        + ", ".join(changed_packages)
                    )

                added_packages = sorted(
                    candidate_packages - origin_packages
                )
                if len(added_packages) != 1:
                    errors.append(
                        "activation must add exactly one active lane"
                    )
                else:
                    added_package_key = added_packages[0]
                    added_lane = candidate_by_package[added_package_key]
                    raw_origin_lanes = origin_ledger.get("active_lanes")
                    raw_candidate_lanes = ledger.get("active_lanes")
                    if (
                        isinstance(raw_origin_lanes, list)
                        and isinstance(raw_candidate_lanes, list)
                        and raw_candidate_lanes
                        != [*raw_origin_lanes, added_lane]
                    ):
                        errors.append(
                            "activation must preserve existing active lanes and "
                            "append exactly one new active lane"
                        )
                    added_package = _validate_added_lane(
                        added_lane,
                        origin_lanes,
                        origin_ledger,
                        branch if isinstance(branch, str) else None,
                        errors,
                    ) or added_package_key
                    raw_added_branch = added_lane.get("branch")
                    if (
                        isinstance(raw_added_branch, str)
                        and raw_added_branch == raw_added_branch.strip()
                        and raw_added_branch
                    ):
                        added_branch = raw_added_branch
                    _validate_added_package_not_closing(
                        origin_ledger,
                        added_package,
                        errors,
                    )
                    _validate_operating_mode_delta(
                        mode,
                        origin_mode,
                        added_package,
                        errors,
                    )
                    _validate_paused_lane_delta(
                        ledger,
                        origin_ledger,
                        added_package,
                        errors,
                    )
                if len(added_packages) != 1 and state != "active_delivery":
                    errors.append("activation candidate must use active_delivery")
                root_changes = _root_changes(ledger, origin_ledger)
                unexpected_root_changes = sorted(
                    root_changes
                    - {
                        "updated_at",
                        "active_lanes",
                        "operating_mode",
                        "paused_lanes",
                    }
                )
                if unexpected_root_changes:
                    errors.append(
                        "activation may not change unrelated ledger sections: "
                        + ", ".join(unexpected_root_changes)
                    )
        if not writer_transfer_repair_matches and not grant_close_repair_matches:
            _validate_baseline_activation_delta(
                candidate_baseline,
                origin_baseline,
                bootstrap_matches=bootstrap_matches,
                added_package=added_package,
                added_branch=added_branch,
                errors=errors,
            )
        raw_changed_paths = facts.get("changed_paths")
        if not isinstance(raw_changed_paths, list) or not all(
            isinstance(path, str) and path for path in raw_changed_paths
        ):
            errors.append("activation changed_paths must be a list of non-empty strings")
        else:
            changed_paths = set(raw_changed_paths)
            if bootstrap_matches and changed_paths != allowed_surfaces:
                errors.append(
                    "bootstrap control repair must change exactly the "
                    "owner-authorized surfaces: "
                    + ", ".join(sorted(allowed_surfaces))
                )
            if (
                writer_transfer_repair_matches
                and changed_paths != allowed_surfaces
            ):
                errors.append(
                    "writer-transfer preflight repair must change exactly the "
                    "owner-authorized surfaces: "
                    + ", ".join(sorted(allowed_surfaces))
                )
            if grant_close_repair_matches and changed_paths != allowed_surfaces:
                errors.append(
                    "grant-close preflight repair must change exactly the "
                    "owner-authorized surfaces: "
                    + ", ".join(sorted(allowed_surfaces))
                )
            unexpected_paths = sorted(changed_paths - allowed_surfaces)
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
    elif intent in {"write", "merge", "release"}:
        _validate_changed_paths_within_lane(active_lane, facts, intent, errors)

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
            "pause",
            "transfer",
            "grant",
            "close",
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
    parser.add_argument(
        "--candidate-worktree",
        help=(
            "absolute frozen direction-candidate worktree path; valid only for "
            "merge with --fetch --require-clean from trusted origin/main"
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    activation_argument_errors: list[str] = []
    if args.candidate_worktree and (
        args.intent != "merge" or not args.fetch or not args.require_clean
    ):
        activation_argument_errors.append(
            "--candidate-worktree requires --intent merge --fetch --require-clean"
        )
    control_label = {
        "activate": "activation",
        "pause": "pause",
        "transfer": "writer transfer",
        "grant": "merge grant",
        "close": "close",
    }.get(args.intent)
    if control_label is not None and not args.fetch:
        activation_argument_errors.append(f"{control_label} requires --fetch")
    if control_label is not None and not args.require_clean:
        activation_argument_errors.append(
            f"{control_label} requires --require-clean"
        )
    if activation_argument_errors:
        print(
            json.dumps(
                {
                    "result": "fail",
                    "package": args.package,
                    "intent": args.intent,
                    "errors": activation_argument_errors,
                },
                indent=2,
            )
        )
        return 2
    try:
        exact_control_origin: str | None = None
        exact_control_refs: dict[str, str] | None = None
        exact_control_branches: list[str] = []
        if args.candidate_worktree:
            ledger, facts = _collect_direction_candidate_merge(
                args.package, args.candidate_worktree
            )
        else:
            ledger = load_ledger()
            if args.fetch and args.intent in EXACT_CONTROL_FETCH_INTENTS:
                exact_control_branches = ["main"]
                exact_control_origin, exact_control_refs = (
                    _authoritative_ref_snapshot(ROOT, exact_control_branches)
                )
            facts = collect_facts(
                fetch=(
                    args.fetch
                    and args.intent not in EXACT_CONTROL_FETCH_INTENTS
                ),
                include_changed_paths=args.intent in {
                "activate",
                "pause",
                "transfer",
                "grant",
                "close",
                "write",
                "merge",
                "release",
                },
            )
            if exact_control_refs is not None:
                facts["fetched"] = True
                facts["origin_url"] = exact_control_origin
                facts["origin_is_azure"] = True
                if facts["origin_main"] != exact_control_refs["main"]:
                    raise RuntimeError(
                        "captured origin/main does not equal advertised main"
                    )
        if args.intent in {"activate", "pause", "transfer", "grant", "close", "merge"}:
            # The exact SHA captured with the Git facts is the authority for
            # both records, preventing a later remote movement from changing
            # what the candidate was compared against mid-preflight.
            origin_ledger = load_ledger_at_ref(facts["origin_main"])
            candidate_baseline = (
                load_baseline_bytes_at_ref(facts["origin_main"])
                if args.candidate_worktree else load_baseline_bytes()
            )
            origin_baseline = load_baseline_bytes_at_ref(facts["origin_main"])
            if args.intent in {"pause", "transfer", "grant", "close", "merge"}:
                origin_lanes = origin_ledger.get("active_lanes")
                target = next(
                    (
                        lane
                        for lane in origin_lanes
                        if isinstance(lane, dict)
                        and lane.get("package") == args.package
                    ),
                    None,
                ) if isinstance(origin_lanes, list) else None
                target_branch = target.get("branch") if isinstance(target, dict) else None
                if (
                    args.intent == "merge"
                    and not args.candidate_worktree
                    and isinstance(target, dict)
                    and target.get("lane_class") == "direction_authority"
                ):
                    raise RuntimeError(
                        "direction-authority merge requires --candidate-worktree "
                        "from a trusted current-main verifier"
                    )
                if (
                    isinstance(target_branch, str)
                    and target_branch
                    and args.fetch
                    and args.intent in EXACT_CONTROL_FETCH_INTENTS
                ):
                    if not _is_valid_implementation_branch(target_branch):
                        raise RuntimeError("active lane has no safe target branch")
                    exact_control_branches = ["main", target_branch]
                    _, refreshed_refs = _authoritative_ref_snapshot(
                        ROOT,
                        exact_control_branches,
                        expected_origin=exact_control_origin,
                    )
                    if refreshed_refs["main"] != facts["origin_main"]:
                        raise RuntimeError(
                            "origin/main moved while control authority was loaded"
                        )
                    exact_control_refs = refreshed_refs
                    remote_sha = refreshed_refs[target_branch]
                    remote_fact = (
                        remote_sha if FULL_GIT_SHA.fullmatch(remote_sha) else None
                    )
                elif isinstance(target_branch, str) and target_branch:
                    remote_sha = _git(
                        "rev-parse", "--verify",
                        f"refs/remotes/origin/{target_branch}", check=False,
                    )
                    remote_fact = (
                        remote_sha if FULL_GIT_SHA.fullmatch(remote_sha) else None
                    )
                else:
                    remote_fact = None
                if args.intent == "pause":
                    facts["pause_target_remote_sha"] = remote_fact
                elif args.intent == "transfer":
                    facts["transfer_target_remote_sha"] = remote_fact
                elif args.intent == "grant":
                    facts["grant_target_remote_sha"] = remote_fact
                    grant = next(
                        (
                            lane.get("merge_grant")
                            for lane in ledger.get("active_lanes", [])
                            if isinstance(lane, dict)
                            and lane.get("package") == args.package
                        ),
                        None,
                    )
                    evidence = (
                        grant.get("review_evidence_paths")
                        if isinstance(grant, dict) else []
                    )
                    evidence_items = []
                    for path in evidence:
                        if not isinstance(path, str) or not remote_fact:
                            continue
                        object_type = _git_object_type(remote_fact, path)
                        if not object_type:
                            continue
                        content: str | None = None
                        raw_content = b""
                        if object_type == "blob":
                            raw_content = _git_bytes("show", f"{remote_fact}:{path}")
                            try:
                                content = raw_content.decode("utf-8")
                            except UnicodeDecodeError:
                                content = None
                        evidence_items.append(
                            {
                                "path": path,
                                "object_type": object_type,
                                "object_mode": _git_object_mode(remote_fact, path),
                                "content": content,
                                "git_blob_sha": _git_blob_sha(remote_fact, path),
                                "bytes_sha256": hashlib.sha256(raw_content).hexdigest()
                                if object_type == "blob" else None,
                            }
                        )
                    facts["grant_review_evidence_existing"] = [
                        item["path"] for item in evidence_items
                    ]
                    facts["grant_review_evidence"] = evidence_items
                elif args.intent == "close":
                    facts["close_target_remote_sha"] = remote_fact
                    closing = next(
                        (
                            item
                            for item in ledger.get("closing_lanes", [])
                            if isinstance(item, dict)
                            and item.get("package") == args.package
                        ),
                        None,
                    )
                    package_merge_sha = (
                        closing.get("package_merge_sha")
                        if isinstance(closing, dict) else None
                    )
                    facts["close_package_merge_sha"] = package_merge_sha
                    ancestor_returncode = _git_returncode_at(
                        ROOT,
                        "merge-base", "--is-ancestor",
                        package_merge_sha or "", facts["origin_main"],
                    ) if isinstance(package_merge_sha, str) else None
                    facts["close_package_merge_ancestor"] = bool(
                        isinstance(package_merge_sha, str)
                        and FULL_GIT_SHA.fullmatch(package_merge_sha)
                        and ancestor_returncode == 0
                    )
                    close_evidence = (
                        closing.get("close_evidence_paths")
                        if isinstance(closing, dict) else []
                    )
                    facts["close_evidence_existing"] = [
                        path for path in close_evidence
                        if isinstance(path, str) and package_merge_sha
                        and _git_object_type(package_merge_sha, path) == "blob"
                    ]
                    surfaces = target.get("writable_surfaces", []) if isinstance(target, dict) else []
                    comparisons = []
                    introduction_checks = []
                    for surface in surfaces:
                        if not isinstance(surface, str) or not remote_fact:
                            comparisons.append(False)
                            continue
                        candidate_tree = _git(
                            "rev-parse", f"{remote_fact}:{surface.rstrip('/')}",
                            check=False,
                        )
                        merge_tree = _git(
                            "rev-parse", f"{package_merge_sha}:{surface.rstrip('/')}",
                            check=False,
                        )
                        main_tree = _git(
                            "rev-parse", f"{facts['origin_main']}:{surface.rstrip('/')}",
                            check=False,
                        )
                        comparisons.append(
                            bool(candidate_tree)
                            and candidate_tree == merge_tree == main_tree
                        )
                        merge_parent_tree = _git(
                            "rev-parse", f"{package_merge_sha}^:{surface.rstrip('/')}",
                            check=False,
                        )
                        introduction_checks.append(
                            bool(candidate_tree)
                            and candidate_tree == merge_tree
                            and merge_parent_tree != merge_tree
                        )
                    facts["close_surface_tree_equal"] = bool(comparisons) and all(comparisons)
                    facts["close_package_merge_introduced_candidate"] = (
                        bool(introduction_checks) and all(introduction_checks)
                    )
                elif not args.candidate_worktree:
                    facts["merge_target_remote_sha"] = remote_fact
                    (
                        facts["merge_main_changed_paths"],
                        facts["merge_main_control_commits_valid"],
                        _,
                    ) = _direction_main_sequence_facts(
                        origin_ledger, args.package, facts["head"], facts["origin_main"]
                    )
        else:
            origin_ledger = None
            candidate_baseline = None
            origin_baseline = None
        errors, warnings = evaluate_policy(
            ledger,
            facts,
            args.package,
            args.intent,
            require_clean=args.require_clean,
            origin_ledger=origin_ledger,
            candidate_baseline=candidate_baseline,
            origin_baseline=origin_baseline,
        )
        if exact_control_refs is not None:
            _, final_refs = _authoritative_ref_snapshot(
                ROOT,
                exact_control_branches,
                expected_origin=exact_control_origin,
            )
            if final_refs != exact_control_refs:
                raise RuntimeError(
                    "origin authority refs moved during control preflight"
                )
            if facts["origin_main"] != final_refs["main"]:
                raise RuntimeError(
                    "captured origin/main changed during control preflight"
                )
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(json.dumps({"result": "fail", "errors": [str(exc)]}, indent=2))
        return 2

    payload_mode = ledger.get("operating_mode")
    payload = {
        "result": "pass" if not errors else "fail",
        "package": args.package,
        "intent": args.intent,
        "operating_mode": (
            payload_mode.get("state")
            if isinstance(payload_mode, dict)
            else None
        ),
        "facts": facts,
        "warnings": warnings,
        "errors": errors,
    }
    print(json.dumps(payload, indent=2))
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
