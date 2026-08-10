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
BASELINE_PATH = ROOT / "docs" / "governance" / "CURRENT_BASELINE.yaml"

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
FULL_GIT_SHA = re.compile(r"[0-9a-f]{40}")

VALID_DELIVERY_PATHS = frozenset({"Routine", "Bounded", "Protected"})
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
    result = subprocess.run(
        ["git", "-C", str(ROOT), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if check and result.returncode:
        raise RuntimeError(result.stderr.strip() or "git command failed")
    return result.stdout.strip()


def _git_bytes(*args: str) -> bytes:
    """Read an exact Git blob without normalizing its trailing bytes."""
    result = subprocess.run(
        ["git", "-C", str(ROOT), *args],
        capture_output=True,
        check=False,
    )
    if result.returncode:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(stderr or "git command failed")
    return result.stdout


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
    errors: list[str],
) -> None:
    """Fail closed unless baseline removes exactly the relinquished package."""
    candidate = _project_baseline(candidate_baseline, "candidate", errors)
    origin = _project_baseline(origin_baseline, "origin/main", errors)
    if candidate is None or origin is None:
        return
    candidate_blocks = candidate["blocks"]
    origin_blocks = origin["blocks"]
    assert isinstance(candidate_blocks, dict)
    assert isinstance(origin_blocks, dict)
    if candidate["preamble"] != origin["preamble"]:
        errors.append("pause may not change the baseline preamble")
    if candidate["order"] != origin["order"]:
        errors.append("pause may not reorder baseline sections")
    allowed_blocks = {"updated_at", "manager", "active_packages", "next_gate"}
    for key in BASELINE_TOP_LEVEL_SECTIONS:
        if key not in allowed_blocks and candidate_blocks[key] != origin_blocks[key]:
            errors.append(f"pause may not change baseline section {key}")

    origin_manager = _parse_manager_block(origin_blocks["manager"], "origin/main", errors)
    candidate_manager = _parse_manager_block(candidate_blocks["manager"], "candidate", errors)
    if origin_manager is not None and candidate_manager is not None:
        if origin_manager[0] != candidate_manager[0]:
            errors.append("pause may only change baseline manager.current_assignments")
        expected_assignment = _expected_pause_manager_assignment(
            paused_package, remaining_lanes
        )
        if candidate_manager[1] != expected_assignment:
            errors.append(
                "pause baseline manager assignment must equal: "
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
                "pause baseline active_packages must remove exactly the paused package"
            )

    candidate_gate = _single_scalar_block(
        candidate_blocks["next_gate"], "next_gate", "candidate", errors
    )
    if candidate_gate is not None:
        expected_gate = _expected_pause_next_gate(paused_package, remaining_lanes)
        if candidate_gate[0] != expected_gate:
            errors.append("pause baseline next_gate must equal: " + expected_gate)


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
    status_lines = [
        line for line in _git("status", "--porcelain=v1").splitlines() if line
    ]
    tracked = [line for line in status_lines if not line.startswith("??")]
    untracked = [line for line in status_lines if line.startswith("??")]
    origin_url = _git("remote", "get-url", "origin")
    facts = {
        "repository": str(ROOT),
        "branch": _git("branch", "--show-current"),
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
                    ("diff", "--name-only", f"{origin_main}...{head}"),
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
        if bootstrap_matches:
            allowed_surfaces = set(BOOTSTRAP_CONTROL_REPAIR["allowed_surfaces"])
            warnings.append(
                "using the exact one-time bootstrap control-repair boundary"
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

            if not bootstrap_matches and origin_policy != policy:
                errors.append(
                    "activation may not change activation_policy"
                )

            if lane_limit == MAX_ACTIVE_LANES and len(active_lanes) > lane_limit:
                errors.append(
                    f"activation candidate exceeds the {MAX_ACTIVE_LANES}-lane limit"
                )

            if bootstrap_matches:
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
    activation_argument_errors: list[str] = []
    if args.intent == "activate" and not args.fetch:
        activation_argument_errors.append("activation requires --fetch")
    if args.intent == "activate" and not args.require_clean:
        activation_argument_errors.append("activation requires --require-clean")
    if args.intent == "pause" and not args.fetch:
        activation_argument_errors.append("pause requires --fetch")
    if args.intent == "pause" and not args.require_clean:
        activation_argument_errors.append("pause requires --require-clean")
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
        ledger = load_ledger()
        facts = collect_facts(
            fetch=args.fetch,
            include_changed_paths=args.intent in {
                "activate",
                "pause",
                "write",
                "merge",
                "release",
            },
        )
        if args.intent in {"activate", "pause"}:
            # The exact SHA captured with the Git facts is the authority for
            # both records, preventing a later remote movement from changing
            # what the candidate was compared against mid-preflight.
            origin_ledger = load_ledger_at_ref(facts["origin_main"])
            candidate_baseline = load_baseline_bytes()
            origin_baseline = load_baseline_bytes_at_ref(facts["origin_main"])
            if args.intent == "pause":
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
                if isinstance(target_branch, str) and target_branch:
                    remote_sha = _git(
                        "rev-parse",
                        "--verify",
                        f"refs/remotes/origin/{target_branch}",
                        check=False,
                    )
                    facts["pause_target_remote_sha"] = (
                        remote_sha if FULL_GIT_SHA.fullmatch(remote_sha) else None
                    )
                else:
                    facts["pause_target_remote_sha"] = None
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
