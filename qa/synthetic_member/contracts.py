"""Fail-closed contracts for reusable synthetic multi-member QA.

This module deliberately has no HTTP, browser, database, identity-provider, or
credential integration.  It creates a neutral attended-proof plan and retains
only structural outcomes.  Pete performs identity provisioning, login, and MFA
outside this tooling.
"""

from __future__ import annotations

import copy
import datetime as dt
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable, Mapping, MutableMapping


PACKAGE_ID = "PS-SYNTHETIC-MULTI-MEMBER-QA-001"
SCHEMA_VERSION = 1

RUN_ID_PATTERN = re.compile(r"^qa-[a-z0-9](?:[a-z0-9._-]{0,31})$")
SURFACE_CODE_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,31}$")
RELEASE_ID_PATTERN = re.compile(r"^(?:not_recorded|[0-9a-f]{7,64})$")
BROWSER_VERSION_PATTERN = re.compile(
    r"^(?:not_recorded|[0-9]{1,4}(?:\.[0-9A-Za-z-]{1,16}){0,5})$"
)
COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
UTC_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
EMAIL_PATTERN = re.compile(r"\b[^\s@]+@[^\s@]+\.[^\s@]+\b")
URL_PATTERN = re.compile(r"https?://", re.IGNORECASE)
UUID_PATTERN = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-"
    r"[89ab][0-9a-f]{3}-[0-9a-f]{12}\b",
    re.IGNORECASE,
)
JWT_PATTERN = re.compile(
    r"\b[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}\b"
)

FORBIDDEN_KEY_PARTS = frozenset(
    {
        "access_token",
        "account_key",
        "authorization",
        "claim",
        "cookie",
        "credential",
        "display_name",
        "email",
        "entity_id",
        "header",
        "id_token",
        "mfa",
        "oid",
        "password",
        "profile_path",
        "provider_subject",
        "record_id",
        "recovery_code",
        "refresh_token",
        "screenshot",
        "secret",
        "session_file",
        "storage_state",
        "token",
        "upn",
        "url",
        "user_key",
        "username",
    }
)

RUN_MODES = frozenset({"local_contract", "candidate_attended", "deployed_attended"})
BROWSERS = frozenset({"chrome", "edge", "firefox", "safari", "other"})
STATUSES = frozenset({"pending", "pass", "conditional", "fail"})
NOTE_CODES = frozenset(
    {
        "none",
        "cleanup_residue_present",
        "cleanup_retention_unverified",
        "cross_tab_signout_unreconciled",
        "feature_surface_unavailable",
        "mapping_not_distinct",
        "neutral_denial_not_distinguishable",
        "operator_stopped_for_safety",
        "private_state_exposed",
        "session_expiry_not_controllable",
        "unexpected_authenticated_state",
    }
)
SAFETY_FAILURE_NOTE_CODES = frozenset(
    {
        "cleanup_residue_present",
        "mapping_not_distinct",
        "operator_stopped_for_safety",
        "private_state_exposed",
        "unexpected_authenticated_state",
    }
)
RETENTION_DISCLOSURES = frozenset(
    {
        "unknown",
        "not_applicable",
        "soft_delete_disclosed",
        "retention_disclosed",
        "application_delete_completed_retention_unverified",
    }
)


class ContractError(ValueError):
    """The plan or retained evidence violates the bounded QA contract."""


class MemberAlias(str, Enum):
    MEMBER_A = "member_a"
    MEMBER_B = "member_b"


@dataclass(frozen=True)
class JourneyDefinition:
    journey_id: str
    actor: str
    peer: str
    client: str
    category: str
    expected_outcome: str
    critical: bool = True

    def record(self) -> dict[str, Any]:
        return {
            "journey_id": self.journey_id,
            "actor": self.actor,
            "peer": self.peer,
            "client": self.client,
            "category": self.category,
            "expected_outcome": self.expected_outcome,
            "critical": self.critical,
            "status": "pending",
            "observed_outcome": "not_recorded",
            "note_code": "none",
        }


def _journey(
    journey_id: str,
    actor: str,
    peer: str,
    client: str,
    category: str,
    expected_outcome: str,
    *,
    critical: bool = True,
) -> JourneyDefinition:
    return JourneyDefinition(
        journey_id,
        actor,
        peer,
        client,
        category,
        expected_outcome,
        critical,
    )


def _build_journeys() -> tuple[JourneyDefinition, ...]:
    journeys = [
        _journey(
            "clean_client_a_start",
            "member_a",
            "none",
            "client_a",
            "clean_client",
            "clean_state_confirmed",
        ),
        _journey(
            "clean_client_b_start",
            "member_b",
            "none",
            "client_b",
            "clean_client",
            "clean_state_confirmed",
        ),
        _journey(
            "clean_signed_out_control_start",
            "signed_out",
            "none",
            "signed_out_control",
            "clean_client",
            "clean_state_confirmed",
        ),
        _journey(
            "signed_out_private_baseline",
            "signed_out",
            "none",
            "signed_out_control",
            "authentication",
            "private_data_absent",
        ),
        _journey(
            "member_a_first_arrival",
            "member_a",
            "none",
            "client_a",
            "identity",
            "private_default_confirmed",
        ),
        _journey(
            "member_b_first_arrival",
            "member_b",
            "none",
            "client_b",
            "identity",
            "private_default_confirmed",
        ),
        _journey(
            "member_pair_distinct_mapping",
            "attended_operator",
            "none",
            "paired_clients",
            "identity",
            "distinct_mapping_confirmed",
        ),
        _journey(
            "simultaneous_member_a_owner_visibility",
            "member_a",
            "member_b",
            "paired_clients",
            "simultaneous_isolation",
            "owner_only_visible",
        ),
        _journey(
            "simultaneous_member_b_owner_visibility",
            "member_b",
            "member_a",
            "paired_clients",
            "simultaneous_isolation",
            "owner_only_visible",
        ),
    ]

    for actor, peer, client in (
        ("member_a", "member_b", "client_a"),
        ("member_b", "member_a", "client_b"),
    ):
        for operation in ("list", "read", "update", "delete", "export"):
            journeys.append(
                _journey(
                    f"{actor}_cannot_{operation}_{peer}",
                    actor,
                    peer,
                    client,
                    "authorization_denial",
                    "neutral_denial",
                )
            )
        journeys.append(
            _journey(
                f"{actor}_forged_reference_denied",
                actor,
                peer,
                client,
                "authorization_denial",
                "neutral_denial",
            )
        )

    journeys.extend(
        [
            _journey(
                "browser_state_member_a_isolated",
                "member_a",
                "member_b",
                "client_a",
                "browser_state",
                "browser_state_isolated",
            ),
            _journey(
                "browser_state_member_b_isolated",
                "member_b",
                "member_a",
                "client_b",
                "browser_state",
                "browser_state_isolated",
            ),
            _journey(
                "account_switch_member_a_to_member_b",
                "member_b",
                "member_a",
                "switch_client",
                "account_switch",
                "prior_member_state_absent",
            ),
            _journey(
                "account_switch_member_b_to_member_a",
                "member_a",
                "member_b",
                "switch_client",
                "account_switch",
                "prior_member_state_absent",
            ),
        ]
    )

    for actor, client in (
        ("member_a", "client_a"),
        ("member_b", "client_b"),
    ):
        journeys.extend(
            [
                _journey(
                    f"{actor}_refresh_owner_only",
                    actor,
                    "none",
                    client,
                    "session_behavior",
                    "owner_only_visible",
                ),
                _journey(
                    f"{actor}_second_tab_owner_only",
                    actor,
                    "none",
                    client,
                    "session_behavior",
                    "owner_only_visible",
                ),
                _journey(
                    f"{actor}_public_return_owner_only",
                    actor,
                    "none",
                    client,
                    "session_behavior",
                    "owner_only_visible",
                ),
                _journey(
                    f"{actor}_sign_out_private_absent",
                    actor,
                    "none",
                    client,
                    "session_behavior",
                    "private_data_absent",
                ),
                _journey(
                    f"{actor}_cross_tab_signout_safe",
                    actor,
                    "none",
                    client,
                    "session_behavior",
                    "private_data_absent",
                    critical=False,
                ),
                _journey(
                    f"{actor}_expired_session_safe",
                    actor,
                    "none",
                    client,
                    "session_behavior",
                    "safe_reauthentication_required",
                    critical=False,
                ),
            ]
        )

    journeys.append(
        _journey(
            "repeat_run_clean_start",
            "attended_operator",
            "none",
            "all_clients",
            "repeatability",
            "clean_state_confirmed",
        )
    )
    return tuple(journeys)


JOURNEYS = _build_journeys()
JOURNEY_BY_ID = {journey.journey_id: journey for journey in JOURNEYS}


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def _require_exact_keys(
    value: Mapping[str, Any], expected: Iterable[str], label: str
) -> None:
    actual = set(value)
    expected_set = set(expected)
    if actual != expected_set:
        raise ContractError(f"{label} keys differ from the exact contract")


def _require_safe_code(value: Any, label: str, pattern: re.Pattern[str]) -> str:
    if not isinstance(value, str):
        raise ContractError(f"{label} must be a string")
    if EMAIL_PATTERN.search(value) or URL_PATTERN.search(value):
        raise ContractError(f"{label} must not contain an email address or URL")
    if UUID_PATTERN.search(value) or JWT_PATTERN.search(value):
        raise ContractError(f"{label} must not contain a private identifier or token")
    if not pattern.fullmatch(value):
        raise ContractError(f"{label} must be a bounded neutral code")
    return value


def _require_utc_timestamp(value: Any, label: str) -> str:
    if not isinstance(value, str) or not UTC_PATTERN.fullmatch(value):
        raise ContractError(f"{label} must be second-precision UTC")
    try:
        dt.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise ContractError(f"{label} must be a real second-precision UTC time") from exc
    return value


def _scan_forbidden_keys(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str):
                raise ContractError("manifest contains a non-string key")
            lowered = key.lower()
            if any(part in lowered for part in FORBIDDEN_KEY_PARTS):
                raise ContractError("manifest contains a forbidden evidence field")
            _scan_forbidden_keys(child)
    elif isinstance(value, list):
        for child in value:
            _scan_forbidden_keys(child)


def create_manifest(
    *,
    run_id: str,
    source_commit: str,
    mode: str,
    browser: str,
    browser_version: str,
    surface_code: str = "foundation",
    release_id: str = "not_recorded",
    created_at: str | None = None,
) -> dict[str, Any]:
    """Create a sanitized pending manifest with the complete journey matrix."""

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "package": PACKAGE_ID,
        "run": {
            "run_id": run_id,
            "created_at": created_at or _utc_now(),
            "mode": mode,
            "surface_code": surface_code,
        },
        "source": {
            "commit": source_commit,
            "release_id": release_id,
        },
        "browser": {
            "name": browser,
            "version": browser_version,
        },
        "identity_aliases": [
            MemberAlias.MEMBER_A.value,
            MemberAlias.MEMBER_B.value,
        ],
        "journeys": [journey.record() for journey in JOURNEYS],
        "cleanup": {
            "pre_run_baseline": "pending",
            "created_item_counts": {
                MemberAlias.MEMBER_A.value: 0,
                MemberAlias.MEMBER_B.value: 0,
            },
            "active_residue_counts": {
                MemberAlias.MEMBER_A.value: None,
                MemberAlias.MEMBER_B.value: None,
            },
            "retention_disclosure": "unknown",
            "client_a_destroyed": "pending",
            "client_b_destroyed": "pending",
            "signed_out_control_destroyed": "pending",
            "switch_client_destroyed": "pending",
            "status": "pending",
        },
        "result": "pending",
    }
    validate_manifest(manifest)
    return manifest


def _validate_status(value: Any, label: str) -> str:
    if value not in STATUSES:
        raise ContractError(f"{label} must be one of {sorted(STATUSES)}")
    return value


def _validate_count(value: Any, label: str, *, allow_none: bool) -> int | None:
    if value is None and allow_none:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 100:
        raise ContractError(f"{label} must be an integer from 0 through 100")
    return value


def _cleanup_result(cleanup: Mapping[str, Any]) -> str:
    statuses = [
        cleanup["pre_run_baseline"],
        cleanup["client_a_destroyed"],
        cleanup["client_b_destroyed"],
        cleanup["signed_out_control_destroyed"],
        cleanup["switch_client_destroyed"],
    ]
    residues = cleanup["active_residue_counts"]
    if any(status == "fail" for status in statuses):
        return "fail"
    if any(isinstance(count, int) and count > 0 for count in residues.values()):
        return "fail"
    if any(status == "pending" for status in statuses):
        return "pending"
    if any(count is None for count in residues.values()):
        return "pending"
    if any(status == "conditional" for status in statuses):
        return "conditional"
    created_counts = cleanup["created_item_counts"]
    disclosure = cleanup["retention_disclosure"]
    if any(created_counts[alias.value] < 1 for alias in MemberAlias):
        return "conditional"
    if disclosure in {"soft_delete_disclosed", "retention_disclosed"}:
        return "pass"
    return "conditional"


def compute_result(manifest: Mapping[str, Any]) -> str:
    """Compute the truthful overall result without trusting a stored claim."""

    journey_statuses = [record["status"] for record in manifest["journeys"]]
    cleanup_status = _cleanup_result(manifest["cleanup"])
    if "fail" in journey_statuses or cleanup_status == "fail":
        return "fail"
    if "pending" in journey_statuses or cleanup_status == "pending":
        return "pending"
    if "conditional" in journey_statuses or cleanup_status == "conditional":
        return "conditional"
    return "pass"


def _validate_journey_records(records: Any) -> None:
    if not isinstance(records, list) or len(records) != len(JOURNEYS):
        raise ContractError("journeys must contain the complete canonical matrix")
    for index, (record, definition) in enumerate(zip(records, JOURNEYS)):
        label = f"journeys[{index}]"
        if not isinstance(record, Mapping):
            raise ContractError(f"{label} must be an object")
        _require_exact_keys(
            record,
            {
                "journey_id",
                "actor",
                "peer",
                "client",
                "category",
                "expected_outcome",
                "critical",
                "status",
                "observed_outcome",
                "note_code",
            },
            label,
        )
        expected = definition.record()
        for key in (
            "journey_id",
            "actor",
            "peer",
            "client",
            "category",
            "expected_outcome",
            "critical",
        ):
            if record[key] != expected[key]:
                raise ContractError(f"{label}.{key} differs from the canonical plan")
        status = _validate_status(record["status"], f"{label}.status")
        note_code = record["note_code"]
        if note_code not in NOTE_CODES:
            raise ContractError(f"{label}.note_code is not approved")
        if status == "pending":
            if record["observed_outcome"] != "not_recorded" or note_code != "none":
                raise ContractError(f"{label} pending evidence must be empty")
        elif status == "pass":
            if record["observed_outcome"] != definition.expected_outcome:
                raise ContractError(f"{label} Pass must record the expected outcome")
            if note_code != "none":
                raise ContractError(f"{label} Pass must not carry a limitation code")
        elif status == "conditional":
            if record["observed_outcome"] != "limitation_recorded":
                raise ContractError(f"{label} Conditional must record a limitation")
            if note_code == "none":
                raise ContractError(f"{label} Conditional requires a note code")
            if note_code in SAFETY_FAILURE_NOTE_CODES:
                raise ContractError(f"{label} safety note code requires Fail")
        elif status == "fail":
            if record["observed_outcome"] != "safety_failure":
                raise ContractError(f"{label} Fail must record a safety failure")
            if note_code not in SAFETY_FAILURE_NOTE_CODES:
                raise ContractError(f"{label} Fail requires a safety note code")


def _validate_cleanup(cleanup: Any) -> None:
    if not isinstance(cleanup, Mapping):
        raise ContractError("cleanup must be an object")
    _require_exact_keys(
        cleanup,
        {
            "pre_run_baseline",
            "created_item_counts",
            "active_residue_counts",
            "retention_disclosure",
            "client_a_destroyed",
            "client_b_destroyed",
            "signed_out_control_destroyed",
            "switch_client_destroyed",
            "status",
        },
        "cleanup",
    )
    for field_name in (
        "pre_run_baseline",
        "client_a_destroyed",
        "client_b_destroyed",
        "signed_out_control_destroyed",
        "switch_client_destroyed",
        "status",
    ):
        _validate_status(cleanup[field_name], f"cleanup.{field_name}")
    aliases = {MemberAlias.MEMBER_A.value, MemberAlias.MEMBER_B.value}
    for field_name, allow_none in (
        ("created_item_counts", False),
        ("active_residue_counts", True),
    ):
        counts = cleanup[field_name]
        if not isinstance(counts, Mapping):
            raise ContractError(f"cleanup.{field_name} must be an object")
        _require_exact_keys(counts, aliases, f"cleanup.{field_name}")
        for alias, value in counts.items():
            _validate_count(
                value,
                f"cleanup.{field_name}.{alias}",
                allow_none=allow_none,
            )
    if cleanup["retention_disclosure"] not in RETENTION_DISCLOSURES:
        raise ContractError("cleanup.retention_disclosure is not approved")
    expected = _cleanup_result(cleanup)
    if cleanup["status"] != expected:
        raise ContractError(f"cleanup.status must be computed as {expected}")


def validate_manifest(manifest: Any, *, final: bool = False) -> Mapping[str, Any]:
    """Validate exact shape, minimization, and truthful result calculation."""

    if not isinstance(manifest, Mapping):
        raise ContractError("manifest must be an object")
    _scan_forbidden_keys(manifest)
    _require_exact_keys(
        manifest,
        {
            "schema_version",
            "package",
            "run",
            "source",
            "browser",
            "identity_aliases",
            "journeys",
            "cleanup",
            "result",
        },
        "manifest",
    )
    if manifest["schema_version"] != SCHEMA_VERSION:
        raise ContractError("unsupported schema_version")
    if manifest["package"] != PACKAGE_ID:
        raise ContractError("manifest package differs from the QA foundation")

    run = manifest["run"]
    if not isinstance(run, Mapping):
        raise ContractError("run must be an object")
    _require_exact_keys(run, {"run_id", "created_at", "mode", "surface_code"}, "run")
    _require_safe_code(run["run_id"], "run.run_id", RUN_ID_PATTERN)
    _require_utc_timestamp(run["created_at"], "run.created_at")
    if run["mode"] not in RUN_MODES:
        raise ContractError("run.mode is not approved")
    _require_safe_code(run["surface_code"], "run.surface_code", SURFACE_CODE_PATTERN)

    source = manifest["source"]
    if not isinstance(source, Mapping):
        raise ContractError("source must be an object")
    _require_exact_keys(source, {"commit", "release_id"}, "source")
    if not isinstance(source["commit"], str) or not COMMIT_PATTERN.fullmatch(
        source["commit"]
    ):
        raise ContractError("source.commit must be a full lower-case Git SHA")
    _require_safe_code(source["release_id"], "source.release_id", RELEASE_ID_PATTERN)

    browser = manifest["browser"]
    if not isinstance(browser, Mapping):
        raise ContractError("browser must be an object")
    _require_exact_keys(browser, {"name", "version"}, "browser")
    if browser["name"] not in BROWSERS:
        raise ContractError("browser.name is not approved")
    _require_safe_code(
        browser["version"], "browser.version", BROWSER_VERSION_PATTERN
    )
    if run["mode"] == "deployed_attended":
        if source["release_id"] == "not_recorded":
            raise ContractError("deployed evidence requires a recorded release")
        if browser["version"] == "not_recorded":
            raise ContractError("deployed evidence requires a recorded browser version")

    if manifest["identity_aliases"] != [
        MemberAlias.MEMBER_A.value,
        MemberAlias.MEMBER_B.value,
    ]:
        raise ContractError("identity_aliases must be exactly member_a and member_b")

    _validate_journey_records(manifest["journeys"])
    _validate_cleanup(manifest["cleanup"])
    expected_result = compute_result(manifest)
    _validate_status(manifest["result"], "manifest.result")
    if manifest["result"] != expected_result:
        raise ContractError(f"manifest.result must be computed as {expected_result}")
    if final and expected_result == "pending":
        raise ContractError("final evidence cannot contain pending journeys or cleanup")
    return manifest


def record_journey(
    manifest: Mapping[str, Any],
    *,
    journey_id: str,
    status: str,
    note_code: str = "none",
) -> dict[str, Any]:
    """Return a validated copy with one sanitized journey result recorded."""

    validate_manifest(manifest)
    if journey_id not in JOURNEY_BY_ID:
        raise ContractError("journey_id is not part of the canonical matrix")
    if status not in {"pass", "conditional", "fail"}:
        raise ContractError("recorded journey status must be pass, conditional, or fail")
    if note_code not in NOTE_CODES:
        raise ContractError("note_code is not approved")
    if status == "pass" and note_code != "none":
        raise ContractError("Pass must not carry a limitation code")
    if status != "pass" and note_code == "none":
        raise ContractError("Conditional or Fail requires a note code")
    if status == "conditional" and note_code in SAFETY_FAILURE_NOTE_CODES:
        raise ContractError("a safety note code requires Fail")
    if status == "fail" and note_code not in SAFETY_FAILURE_NOTE_CODES:
        raise ContractError("Fail requires a safety note code")

    updated = copy.deepcopy(manifest)
    definition = JOURNEY_BY_ID[journey_id]
    record = next(
        item for item in updated["journeys"] if item["journey_id"] == journey_id
    )
    record["status"] = status
    record["note_code"] = note_code
    if status == "pass":
        record["observed_outcome"] = definition.expected_outcome
    elif status == "conditional":
        record["observed_outcome"] = "limitation_recorded"
    else:
        record["observed_outcome"] = "safety_failure"
    updated["result"] = compute_result(updated)
    validate_manifest(updated)
    return updated


def record_cleanup(
    manifest: Mapping[str, Any],
    *,
    pre_run_baseline: str,
    created_member_a: int,
    created_member_b: int,
    residue_member_a: int,
    residue_member_b: int,
    retention_disclosure: str,
    client_a_destroyed: str,
    client_b_destroyed: str,
    signed_out_control_destroyed: str,
    switch_client_destroyed: str,
) -> dict[str, Any]:
    """Return a validated copy with count-only cleanup evidence recorded."""

    validate_manifest(manifest)
    updated = copy.deepcopy(manifest)
    cleanup = updated["cleanup"]
    cleanup.update(
        {
            "pre_run_baseline": pre_run_baseline,
            "created_item_counts": {
                MemberAlias.MEMBER_A.value: created_member_a,
                MemberAlias.MEMBER_B.value: created_member_b,
            },
            "active_residue_counts": {
                MemberAlias.MEMBER_A.value: residue_member_a,
                MemberAlias.MEMBER_B.value: residue_member_b,
            },
            "retention_disclosure": retention_disclosure,
            "client_a_destroyed": client_a_destroyed,
            "client_b_destroyed": client_b_destroyed,
            "signed_out_control_destroyed": signed_out_control_destroyed,
            "switch_client_destroyed": switch_client_destroyed,
        }
    )
    cleanup["status"] = _cleanup_result(cleanup)
    updated["result"] = compute_result(updated)
    validate_manifest(updated)
    return updated


@dataclass
class EphemeralCleanupLedger:
    """In-process item handles that can never enter retained evidence."""

    _handles: MutableMapping[MemberAlias, set[str]] = field(
        default_factory=lambda: {
            MemberAlias.MEMBER_A: set(),
            MemberAlias.MEMBER_B: set(),
        },
        repr=False,
    )

    def add(self, alias: MemberAlias, handle: str) -> None:
        if not isinstance(alias, MemberAlias):
            raise ContractError("cleanup ledger alias must be MemberAlias")
        if not isinstance(handle, str) or not 1 <= len(handle) <= 256:
            raise ContractError("cleanup ledger handle must be bounded")
        self._handles[alias].add(handle)

    def created_counts(self) -> dict[str, int]:
        return {alias.value: len(self._handles[alias]) for alias in MemberAlias}

    def clear(self) -> None:
        for handles in self._handles.values():
            handles.clear()

    def __repr__(self) -> str:
        total = sum(len(handles) for handles in self._handles.values())
        return f"EphemeralCleanupLedger(handle_count={total}, handles=redacted)"
