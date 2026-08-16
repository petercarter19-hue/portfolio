import copy
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from scripts.delivery_preflight import (
    BOOTSTRAP_CONTROL_REPAIR,
    CLEANUP_BRANCH_PATTERN,
    DIRECTION_MERGE_CONTROL_PATHS,
    DIRECTION_MERGE_FOLLOWUP_PATHS,
    GRANT_ALLOWED_SURFACES,
    IMPLEMENTATION_RELEASE_PREFLIGHT_REPAIR,
    OPPORTUNITY_SCHEMA_REPAIR_RELEASE_REFRESH,
    OPPORTUNITY_SLATE_BRANCH,
    OPPORTUNITY_SLATE_PACKAGE,
    OPPORTUNITY_SLATE_RELEASE_SCOPE,
    OPPORTUNITY_SLATE_REVIEWED_SHA,
    OPPORTUNITY_SLATE_REVIEW_ATTESTATION,
    OPPORTUNITY_LIFECYCLE_FIXTURE_REPAIR,
    OPPORTUNITY_RESUME_FIXTURE_REPAIR,
    OPPORTUNITY_CLOSE_INTRODUCTION_REPAIR,
    WRITER_TRANSFER_PREFLIGHT_REPAIR,
    GRANT_CLOSE_PREFLIGHT_REPAIR,
    GRANT_CLOSE_FIXTURE_FOLLOWUP,
    PROFILE_CLOSE_FIXTURE_FOLLOWUP,
    PROFILE_CLOSE_BASELINE_FIXTURE_FOLLOWUP,
    PROFILE_CLOSE_ABSENT_SURFACE_REPAIR,
    PROFILE_CLOSE_OBJECT_ID_REPAIR,
    PROFILE_DIRECTION_OWNER_DECISION_SHA256,
    PROFILE_DIRECTION_REVIEW_ATTESTATION,
    PROFILE_CORE_INTEGRATION_BRANCH,
    PROFILE_CORE_INTEGRATION_OWNER_DECISION_SHA256,
    PROFILE_CORE_INTEGRATION_PACKAGE,
    PROFILE_CORE_INTEGRATION_REVIEW_ATTESTATION,
    PROFILE_CORE_INTEGRATION_REVIEWED_SHA,
    PROFILE_CORE_GRANT_ANCHOR_FOLLOWUP,
    PROFILE_CORE_GRANT_ANCHOR_PATHS,
    PROFILE_CORE_GRANT_ANCHOR_FOLLOWUP_MAIN,
    PROFILE_CORE_GRANT_FIXTURE_FOLLOWUP,
    PROFILE_CORE_GRANT_FOLLOWUP_PATHS,
    PROFILE_CORE_GRANT_FIXTURE_FOLLOWUP_MAIN,
    PROFILE_CORE_LEDGER_GRANT_MAIN,
    PROFILE_CORE_MERGE_CONTROL_PATHS,
    PROFILE_CORE_MERGE_PREFLIGHT_REPAIR,
    PROFILE_CORE_MERGE_REPAIR_MAIN,
    PROFILE_CORE_POST_GRANT_REGISTRY_FIXTURE_REPAIR,
    PROFILE_CORE_POST_GRANT_REGISTRY_FIXTURE_PATHS,
    CONNECT_002_BRANCH,
    CONNECT_002_GRANT_FIXTURE_FOLLOWUP_R3,
    CONNECT_002_GRANT_FIXTURE_FOLLOWUP_PATHS,
    CONNECT_002_MERGE_ADMISSION_ANCHOR_FOLLOWUP,
    CONNECT_002_MERGE_ADMISSION_ANCHOR_MAIN,
    CONNECT_002_MERGE_ADMISSION_ANCHOR_PATHS,
    CONNECT_002_MERGE_ADMISSION_ANCHOR_SOURCE,
    CONNECT_002_MERGE_ADMISSION_REPAIR_MAIN,
    CONNECT_002_MERGE_ADMISSION_REPAIR,
    CONNECT_002_MERGE_ADMISSION_REPAIR_PATHS,
    CONNECT_002_MERGE_CANDIDATE_CONTRACT,
    CONNECT_002_OWNER_DECISION_SHA256,
    CONNECT_002_PACKAGE,
    CONNECT_002_RECONCILED_BRANCH,
    CONNECT_002_RECONCILED_CANDIDATE_CONTRACT,
    CONNECT_002_RECONCILED_OWNER_DECISION_SHA256,
    CONNECT_002_RECONCILED_REVIEW_ATTESTATION,
    CONNECT_002_RECONCILED_REVIEWED_SHA,
    CONNECT_002_REVIEW_ATTESTATION,
    CONNECT_002_REVIEWED_SHA,
    SHELL_BRANCH,
    SHELL_DELIVERY_PATH,
    SHELL_LANE_CLASS,
    SHELL_MERGE_CONTROL_PATHS,
    SHELL_MERGE_PREFLIGHT_REPAIR,
    SHELL_PACKAGE,
    INTERVIEW_AI_ARCHITECTURE_BRANCH,
    INTERVIEW_AI_ARCHITECTURE_PACKAGE,
    INTERVIEW_AI_BASE_REGISTRY_SHA256,
    INTERVIEW_AI_D13_ADMISSION_REPAIR,
    INTERVIEW_AI_D13_CONTROL_PATHS,
    INTERVIEW_AI_D13_ATTESTATION_BASE,
    INTERVIEW_AI_D13_ATTESTATION_BRANCH,
    INTERVIEW_AI_D13_ATTESTATION_PATHS,
    INTERVIEW_AI_D13_ATTESTATION_REGISTRATION,
    INTERVIEW_AI_D13_LIFECYCLE_FIXTURE_BASE,
    INTERVIEW_AI_D13_LIFECYCLE_FIXTURE_FOLLOWUP,
    INTERVIEW_AI_D13_LIFECYCLE_FIXTURE_PATHS,
    INTERVIEW_AI_D13_OWNER_DECISION,
    INTERVIEW_AI_D13_OWNER_DECISION_SHA256,
    INTERVIEW_AI_D13_REVIEW_ATTESTATION,
    INTERVIEW_AI_D13_REVIEWED_SHA,
    INTERVIEW_AI_PACKAGE_FILES,
    INTERVIEW_AI_RECONCILED_LANE_SHA256,
    INTERVIEW_AI_REGISTRY_PATH,
    INTERVIEW_AI_RELOCATED_REGISTRY_SHA256,
    INTERVIEW_AI_SOURCE_PATHS,
    INTERVIEW_AI_SOURCE_ROOT,
    INTERVIEW_AI_SOURCE_SHA,
    INTERVIEW_AI_SOURCE_TREE,
    INTERVIEW_AI_TARGET_PATHS,
    INTERVIEW_AI_TARGET_ROOT,
    _affirmative_merge_decision,
    _authoritative_azure_origin,
    _canonical_sha256,
    _candidate_surface_introduction_proven,
    _close_surface_tree_equivalent,
    _direction_main_sequence_facts,
    _direction_control_path_sequence_valid,
    _direction_merge_grant,
    _exact_direction_grant_delta,
    _exact_grant_close_fixture_followup_delta,
    _exact_implementation_release_preflight_repair_matches,
    _exact_profile_core_grant_anchor_followup_delta,
    _exact_profile_core_grant_anchor_followup_matches,
    _exact_profile_core_grant_fixture_followup_delta,
    _exact_profile_core_grant_fixture_followup_matches,
    _exact_profile_core_merge_preflight_repair_matches,
    _exact_profile_core_post_grant_registry_fixture_repair_delta,
    _exact_profile_core_post_grant_registry_fixture_repair_matches,
    _is_profile_core_reviewed_implementation_lane,
    _exact_shell_merge_preflight_repair_delta,
    _exact_shell_merge_preflight_repair_matches,
    _exact_interview_ai_d13_admission_repair_delta,
    _exact_interview_ai_d13_admission_repair_matches,
    _exact_interview_ai_d13_attestation_registration_delta,
    _exact_interview_ai_d13_attestation_registration_matches,
    _exact_interview_ai_d13_lifecycle_fixture_followup_delta,
    _exact_interview_ai_d13_lifecycle_fixture_followup_matches,
    _exact_interview_ai_relocation_write,
    _is_shell_reviewed_shared_foundation_lane,
    _exact_connect_002_merge_admission_repair_delta,
    _exact_connect_002_merge_admission_repair_matches,
    _exact_connect_002_merge_admission_anchor_followup_delta,
    _exact_connect_002_merge_admission_anchor_followup_matches,
    _exact_connect_002_grant_fixture_followup_delta,
    _exact_connect_002_grant_fixture_followup_matches,
    _connect_002_main_sequence_facts,
    _is_connect_002_reviewed_implementation_lane,
    _profile_core_main_sequence_facts,
    _exact_opportunity_schema_repair_release_refresh_matches,
    _exact_opportunity_lifecycle_fixture_repair_delta,
    _exact_opportunity_resume_fixture_repair_delta,
    _exact_opportunity_close_introduction_repair_delta,
    _exact_profile_close_fixture_followup_delta,
    _exact_profile_close_baseline_fixture_followup_delta,
    _exact_profile_close_absent_surface_repair_delta,
    _exact_profile_close_absent_surface_repair_matches,
    _exact_profile_close_object_id_repair_delta,
    _exact_profile_close_object_id_repair_matches,
    _fetch_exact_origin_refs,
    _git_environment,
    _git_object_id_at,
    _baseline_scalar,
    _expected_pause_manager_assignment,
    _expected_pause_next_gate,
    collect_facts,
    evaluate_policy,
    load_baseline_bytes,
    load_baseline_bytes_at_ref,
    load_ledger,
    load_ledger_at_ref,
    main,
)


ROOT = Path(__file__).resolve().parents[1]

# Exact main merge that carried the one-time three-lane control repair. The
# bootstrap replay test pins its candidate state to this commit so the
# historical exception stays verifiable after later activations move the live
# control-plane files (the state-coupling class already fixed by
# PS-DELIVERY-PREFLIGHT-CLOSEOUT-FIXTURE-001 and the Workshop closeout
# fixture correction).
BOOTSTRAP_MERGED_MAIN = "ace996cd32612cfa62ae51b4b4f28158e41c6b23"
PROFILE_DIRECTION_PRE_CLOSE_MAIN = (
    "476c641f32b88caac448f6351b731eb36dff6e53"
)


def facts(**overrides):
    value = {
        "branch": "work/2026-08-04-delivery-reset-001",
        "head": "candidate-head",
        "ahead": 0,
        "behind": 0,
        "tracked_changes": 0,
        "untracked_changes": 0,
        "changed_paths": [],
        "origin_main": "b86053df749287d9dc4cdece0dbf4ad9a682283a",
        "origin_is_azure": True,
        "fetched": True,
    }
    value.update(overrides)
    return value


class DeliveryPreflightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = ROOT / "docs" / "governance" / "CURRENT_LANES.json"
        cls.ledger = load_ledger(cls.path)
        cls.baseline = load_baseline_bytes()

    def _baseline_for_origin(
        self,
        origin: dict,
        source_baseline: bytes | None = None,
    ) -> bytes:
        """Return a baseline whose active packages match a real origin fixture.

        A checked-in activation candidate can contain the lane that a 1->2
        transition test is trying to add. Keep the fixture independent from
        that transient repository state by retaining only packages present in
        the synthetic origin. When controlled idle leaves no recorded package
        block, synthesize the one normal package required by a one-lane origin.
        Other incompatible synthetic combinations keep the checked-in bytes.
        """
        packages = {
            lane["package"]
            for lane in origin.get("active_lanes", [])
            if isinstance(lane, dict) and isinstance(lane.get("package"), str)
        }
        baseline = self.baseline if source_baseline is None else source_baseline
        source = baseline.decode("utf-8")
        section = re.search(
            r"(?ms)^active_packages:\n(?P<body>.*?)(?=^scoped_findings:\n)",
            source,
        )
        if section is None:
            return baseline
        blocks = list(
            re.finditer(
                r"(?ms)^  - id: (?P<id>[^\n]+)\n.*?(?=^  - id: |\Z)",
                section.group("body"),
            )
        )
        recorded = {block.group("id") for block in blocks}
        if not packages:
            return baseline
        if packages.issubset(recorded):
            retained = "".join(
                block.group(0)
                for block in blocks
                if block.group("id") in packages
            )
        elif len(packages) == 1 and not blocks:
            package = next(iter(packages))
            retained = (
                f"  - id: {package}\n"
                "    status: active_delivery\n"
                '    scope: "Synthetic active-package fixture."\n'
            )
        elif len(packages) == 1 and len(blocks) == 1:
            package = next(iter(packages))
            retained = re.sub(
                r"^  - id: [^\n]+$",
                f"  - id: {package}",
                blocks[0].group(0),
                count=1,
                flags=re.MULTILINE,
            )
        else:
            return baseline
        candidate = (
            source[: section.start()]
            + "active_packages:\n"
            + retained
            + source[section.end() :]
        )
        return candidate.encode("utf-8")

    def _activation_baselines(
        self,
        origin: dict,
        candidate: dict,
    ) -> tuple[bytes, bytes]:
        """Build the only baseline delta ordinary activation may make.

        Existing lane-control tests use synthetic ledgers.  Their companion
        baseline still needs to carry the same semantic one-lane addition that
        a real activation carries, while bootstrap remains byte-identical.
        """
        if (
            candidate.get("bootstrap_control_repair") == BOOTSTRAP_CONTROL_REPAIR
            and candidate.get("active_lanes") == origin.get("active_lanes")
        ):
            return self.baseline, self.baseline

        origin_baseline = self._baseline_for_origin(origin)

        origin_packages = {
            lane["package"].casefold()
            for lane in origin.get("active_lanes", [])
            if isinstance(lane, dict) and isinstance(lane.get("package"), str)
        }
        added_lanes = [
            lane
            for lane in candidate.get("active_lanes", [])
            if isinstance(lane, dict)
            and isinstance(lane.get("package"), str)
            and lane["package"].casefold() not in origin_packages
        ]
        if len(added_lanes) != 1:
            return origin_baseline, origin_baseline

        lane = added_lanes[0]
        package = lane["package"]
        branch = lane.get("branch", "work/test-implementation")
        source = origin_baseline.decode("utf-8")
        candidate_text = re.sub(
            r'^  current_assignments: .+$',
            (
                '  current_assignments: "Activation assigns '
                f'{package} to {branch}."'
            ),
            source,
            count=1,
            flags=re.MULTILINE,
        )
        candidate_text = candidate_text.replace(
            "\nscoped_findings:\n",
            (
                f"\n  - id: {package}\n"
                "    status: active_delivery\n"
                f'    scope: "Controlled activation scope for {package}."\n'
                "scoped_findings:\n"
            ),
            1,
        )
        candidate_text = re.sub(
            r'^next_gate: .+$',
            f'next_gate: "Continue {package} on {branch}."',
            candidate_text,
            count=1,
            flags=re.MULTILINE,
        )
        return origin_baseline, candidate_text.encode("utf-8")

    def _actual_pr316_baselines(
        self,
        origin: dict,
        candidate: dict,
    ) -> tuple[bytes, bytes]:
        """A stable fixture for the approved Interview Studio 1->2 delta.

        It carries the real package, branch, and baseline wording shape from
        PR 316, but is built from the checked-in origin fixture so the test is
        portable and does not depend on a sibling activation worktree.
        """
        lane = next(
            lane
            for lane in candidate["active_lanes"]
            if lane["package"] == "PS-INTERVIEW-STUDIO-CALIBRATION-001"
        )
        origin_baseline = self._baseline_for_origin(origin)
        source = origin_baseline.decode("utf-8")
        candidate_text = re.sub(
            r'^  current_assignments: .+$',
            (
                '  current_assignments: "Two disjoint non-production lanes are '
                "active: PS-ASK-PETE-AI-001 visual/runtime on "
                "work/2026-08-06-ask-pete-recruiter-evidence-runtime-v1 and "
                "public Interview Studio PS-INTERVIEW-STUDIO-CALIBRATION-001 on "
                "work/2026-08-06-interview-studio-calibration-001.\""
            ),
            source,
            count=1,
            flags=re.MULTILINE,
        )
        candidate_text = candidate_text.replace(
            "\nscoped_findings:\n",
            (
                f"\n  - id: {lane['package']}\n"
                "    status: active_delivery\n"
                '    scope: "Visual-only calibration of the existing public '
                "Interview Studio within four runtime/test files plus one package "
                'folder; no behavior, backend, schema, private-member, merge, '
                'deployment, or production change."\n'
                "scoped_findings:\n"
            ),
            1,
        )
        candidate_text = re.sub(
            r'^next_gate: .+$',
            (
                'next_gate: "PS-ASK-PETE-AI-001 continues its recorded Concept H '
                "V2 visual/runtime sequence. "
                "PS-INTERVIEW-STUDIO-CALIBRATION-001 may begin only after this "
                "activation merges and its dedicated worktree passes the write "
                'preflight."'
            ),
            candidate_text,
            count=1,
            flags=re.MULTILINE,
        )
        return origin_baseline, candidate_text.encode("utf-8")

    def _evaluate_activation(
        self,
        candidate: dict,
        activation_facts: dict,
        package: str = "PS-DELIVERY-CONTROL-001",
        *,
        require_clean: bool = False,
        origin: dict | None = None,
        candidate_baseline: bytes | None = None,
        origin_baseline: bytes | None = None,
    ) -> tuple[list[str], list[str]]:
        origin = self.ledger if origin is None else origin
        if candidate_baseline is None and origin_baseline is None:
            origin_baseline, candidate_baseline = self._activation_baselines(
                origin,
                candidate,
            )
        return evaluate_policy(
            candidate,
            activation_facts,
            package,
            "activate",
            require_clean=require_clean,
            origin_ledger=origin,
            candidate_baseline=candidate_baseline,
            origin_baseline=origin_baseline,
        )

    def _idle_ledger(self) -> dict:
        """The current ledger as it looks from controlled idle."""
        idle = copy.deepcopy(self.ledger)
        idle["operating_mode"]["state"] = "controlled_idle"
        idle["operating_mode"]["writes_allowed_for"] = []
        idle["operating_mode"]["release_allowed_for"] = []
        idle["active_lanes"] = []
        return idle

    def _direction_origin(self) -> tuple[dict, dict]:
        # Direction grant/close tests exercise the immutable pre-close state.
        # The checked-in ledger is intentionally mutable and no longer retains
        # Profile in active_lanes after a successful close.
        origin = load_ledger_at_ref(PROFILE_DIRECTION_PRE_CLOSE_MAIN)
        lane = next(
            copy.deepcopy(item)
            for item in origin["active_lanes"]
            if item.get("lane_class") == "direction_authority"
        )
        lane["owner_decisions"] = [
            {
                "date": "2026-08-11",
                "decision": (
                    "Pete withdrew the earlier Claude Profile assignment and assigned "
                    "Codex end-to-end ownership through architecture, implementation, "
                    "validation, review, merge, default-off deployment, and dark live "
                    "verification. Pete will review the exact deployed candidate "
                    "immediately before it goes live; public enablement remains a "
                    "separate explicit decision."
                ),
            }
        ]
        lane.pop("merge_grant", None)
        origin["active_lanes"] = [lane]
        origin["operating_mode"]["state"] = "active_delivery"
        origin["operating_mode"]["writes_allowed_for"] = [lane["package"]]
        origin["operating_mode"]["merge_allowed_for"] = []
        origin["operating_mode"]["cleanup_allowed_for"] = []
        origin["operating_mode"]["release_allowed_for"] = []
        origin["updated_at"] = "2026-08-12T02:00:00Z"
        return origin, lane

    def _grant_record(
        self, lane: dict, reviewed: str, independent: str | None = None
    ) -> dict:
        independent = reviewed if independent is None else independent
        decision = lane["owner_decisions"][0]
        digest = hashlib.sha256(
            json.dumps(
                decision, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            ).encode("utf-8")
        ).hexdigest()
        path = (
            lane["writable_surfaces"][0].rstrip("/")
            + "/16_VERIFICATION_AND_COMPLETION_RECORD.md"
        )
        review = copy.deepcopy(PROFILE_DIRECTION_REVIEW_ATTESTATION)
        return {
            "authorized_by": "Pete",
            "authority_decision_index": 0,
            "authority_decision_sha256": digest,
            "independent_review": review,
            "reviewed_remote_sha": reviewed,
            "granted_at": "2026-08-12T03:00:00Z",
            "review_result": "pass",
            "review_evidence_paths": [path],
        }

    def _profile_core_origin(self) -> tuple[dict, dict]:
        """Return the exact pre-repair Profile Core ledger and active lane."""
        origin = load_ledger_at_ref(
            PROFILE_CORE_MERGE_PREFLIGHT_REPAIR["origin_main"]
        )
        lane = next(
            item
            for item in origin["active_lanes"]
            if item.get("package") == PROFILE_CORE_INTEGRATION_PACKAGE
        )
        self.assertEqual(PROFILE_CORE_INTEGRATION_BRANCH, lane["branch"])
        self.assertNotIn("merge_grant", lane)
        return origin, lane

    def _profile_core_grant_record(self, lane: dict, granted_at: str) -> dict:
        decision = lane["owner_decisions"][0]
        self.assertEqual(
            PROFILE_CORE_INTEGRATION_OWNER_DECISION_SHA256,
            _canonical_sha256(decision),
        )
        return {
            "authorized_by": "Pete",
            "authority_decision_index": 0,
            "authority_decision_sha256": _canonical_sha256(decision),
            "independent_review": copy.deepcopy(
                PROFILE_CORE_INTEGRATION_REVIEW_ATTESTATION
            ),
            "reviewed_remote_sha": PROFILE_CORE_INTEGRATION_REVIEWED_SHA,
            "granted_at": granted_at,
            "review_result": "pass",
            "review_evidence_paths": [
                PROFILE_CORE_INTEGRATION_REVIEW_ATTESTATION["evidence_path"]
            ],
        }

    def _connect_002_origin(self) -> tuple[dict, dict]:
        """Return the exact pre-repair PS-CONNECT-002 ledger and lane."""
        origin = load_ledger_at_ref(
            CONNECT_002_MERGE_ADMISSION_REPAIR["origin_main"]
        )
        lane = next(
            item
            for item in origin["active_lanes"]
            if item.get("package") == CONNECT_002_PACKAGE
        )
        self.assertEqual(CONNECT_002_BRANCH, lane["branch"])
        self.assertNotIn("merge_grant", lane)
        self.assertNotIn("connect_002_merge_admission_repair", origin)
        return origin, lane

    def _connect_002_repair_candidate(
        self,
        origin: dict,
        *,
        repaired_at: str = "2026-08-13T07:54:08Z",
    ) -> dict:
        candidate = copy.deepcopy(origin)
        candidate["updated_at"] = repaired_at
        candidate["connect_002_merge_admission_repair"] = copy.deepcopy(
            CONNECT_002_MERGE_ADMISSION_REPAIR
        )
        return candidate

    def _connect_002_anchor_origin(self) -> tuple[dict, dict]:
        """Return the exact current-main ledger before the anchor follow-up."""
        origin = load_ledger_at_ref(
            CONNECT_002_MERGE_ADMISSION_ANCHOR_FOLLOWUP["origin_main"]
        )
        lane = next(
            item
            for item in origin["active_lanes"]
            if item.get("package") == CONNECT_002_PACKAGE
        )
        self.assertEqual(CONNECT_002_RECONCILED_BRANCH, lane["branch"])
        self.assertNotIn("merge_grant", lane)
        self.assertEqual(
            CONNECT_002_MERGE_ADMISSION_REPAIR,
            origin.get("connect_002_merge_admission_repair"),
        )
        self.assertNotIn("connect_002_merge_admission_anchor_followup_r2", origin)
        return origin, lane

    def _connect_002_anchor_candidate(
        self,
        origin: dict,
        *,
        anchored_at: str = "2026-08-13T18:47:00Z",
    ) -> dict:
        candidate = copy.deepcopy(origin)
        candidate["updated_at"] = anchored_at
        candidate["connect_002_merge_admission_anchor_followup_r2"] = copy.deepcopy(
            CONNECT_002_MERGE_ADMISSION_ANCHOR_FOLLOWUP
        )
        return candidate

    def _connect_002_grant_fixture_origin(self) -> tuple[dict, dict]:
        """Return exact main after the pinned anchor and before fixture repair."""
        origin = load_ledger_at_ref(
            CONNECT_002_GRANT_FIXTURE_FOLLOWUP_R3["origin_main"]
        )
        lane = next(
            item
            for item in origin["active_lanes"]
            if item.get("package") == CONNECT_002_PACKAGE
        )
        self.assertEqual(CONNECT_002_RECONCILED_BRANCH, lane["branch"])
        self.assertNotIn("merge_grant", lane)
        self.assertEqual(
            CONNECT_002_MERGE_ADMISSION_ANCHOR_FOLLOWUP,
            origin.get("connect_002_merge_admission_anchor_followup_r2"),
        )
        self.assertNotIn("connect_002_grant_fixture_followup_r3", origin)
        return origin, lane

    def _connect_002_grant_fixture_candidate(
        self,
        origin: dict,
        *,
        repaired_at: str = "2026-08-13T19:31:00Z",
    ) -> dict:
        candidate = copy.deepcopy(origin)
        candidate["updated_at"] = repaired_at
        candidate["connect_002_grant_fixture_followup_r3"] = copy.deepcopy(
            CONNECT_002_GRANT_FIXTURE_FOLLOWUP_R3
        )
        return candidate

    def _connect_002_grant_record(self, lane: dict, granted_at: str) -> dict:
        decision = lane["owner_decisions"][0]
        self.assertEqual(
            CONNECT_002_RECONCILED_OWNER_DECISION_SHA256,
            _canonical_sha256(decision),
        )
        return {
            "authorized_by": "Pete",
            "authority_decision_index": 0,
            "authority_decision_sha256": _canonical_sha256(decision),
            "independent_review": copy.deepcopy(
                CONNECT_002_RECONCILED_REVIEW_ATTESTATION
            ),
            "reviewed_remote_sha": CONNECT_002_RECONCILED_REVIEWED_SHA,
            "granted_at": granted_at,
            "review_result": "pass",
            "review_evidence_paths": [
                CONNECT_002_RECONCILED_REVIEW_ATTESTATION["evidence_path"]
            ],
        }

    def _opportunity_origin(self) -> tuple[dict, dict]:
        origin = copy.deepcopy(self.ledger)
        candidates = [
            item
            for collection in (
                origin.get("active_lanes", []),
                reversed(origin.get("paused_lanes", [])),
                reversed(origin.get("closing_lanes", [])),
            )
            for item in collection
            if item.get("package") == OPPORTUNITY_SLATE_PACKAGE
        ]
        self.assertTrue(candidates)
        lifecycle_fields = {
            "disposition",
            "paused_at",
            "pause_reason",
            "resume_contract",
            "preserved_head_sha",
            "closed_at",
            "reviewed_remote_sha",
            "merged_main_sha",
            "package_merge_sha",
            "close_evidence_paths",
        }
        lane = {
            key: value
            for key, value in copy.deepcopy(candidates[0]).items()
            if key not in lifecycle_fields
        }
        # The mutable ledger may now contain a legitimate resumed repair lane.
        # This helper exercises the immutable PR-375 release controls, so keep
        # its synthetic historical lane bound to that exact reviewed branch.
        lane["branch"] = OPPORTUNITY_SLATE_BRANCH
        lane.pop("merge_grant", None)
        origin["active_lanes"] = [lane]
        origin["paused_lanes"] = [
            item for item in origin.get("paused_lanes", [])
            if item.get("package") != OPPORTUNITY_SLATE_PACKAGE
        ]
        origin["closing_lanes"] = [
            item for item in origin.get("closing_lanes", [])
            if item.get("package") != OPPORTUNITY_SLATE_PACKAGE
        ]
        origin["operating_mode"]["state"] = "active_delivery"
        origin["operating_mode"]["writes_allowed_for"] = [
            OPPORTUNITY_SLATE_PACKAGE
        ]
        origin["operating_mode"]["merge_allowed_for"] = []
        origin["operating_mode"]["cleanup_allowed_for"] = []
        origin["operating_mode"]["release_allowed_for"] = []
        origin["operating_mode"]["exit_authority"] = (
            "Active writer lanes: PS-OPPORTUNITY-SLATE-002."
        )
        origin["updated_at"] = "2026-08-12T11:35:08Z"
        return origin, lane

    def _opportunity_decision(self) -> dict:
        return {
            "date": "2026-08-12",
            "decision": "dark_implementation_merge_and_release_authority",
            "authorized_by": "Pete",
            "action": "merge_deploy_apply_additive_schema",
            "status": "authorized",
            "scope": "dark_R1_and_PS-OPPSLATE-004_only",
            "package": OPPORTUNITY_SLATE_PACKAGE,
            "reviewed_remote_sha": OPPORTUNITY_SLATE_REVIEWED_SHA,
            "pull_request": OPPORTUNITY_SLATE_RELEASE_SCOPE["pull_request"],
            "ci_build": OPPORTUNITY_SLATE_RELEASE_SCOPE["ci_build"],
            "public_enablement": "excluded",
            "verbatim_approval": "You're approved.",
        }

    def _opportunity_grant_record(
        self, lane: dict, decision_index: int, granted_at: str
    ) -> dict:
        decision = lane["owner_decisions"][decision_index]
        return {
            "authorized_by": "Pete",
            "authority_decision_index": decision_index,
            "authority_decision_sha256": _canonical_sha256(decision),
            "independent_review": copy.deepcopy(
                OPPORTUNITY_SLATE_REVIEW_ATTESTATION
            ),
            "reviewed_remote_sha": OPPORTUNITY_SLATE_REVIEWED_SHA,
            "granted_at": granted_at,
            "review_result": "pass",
            "review_evidence_paths": [
                OPPORTUNITY_SLATE_REVIEW_ATTESTATION["evidence_path"]
            ],
            "release_scope": copy.deepcopy(OPPORTUNITY_SLATE_RELEASE_SCOPE),
        }

    def _review_evidence_facts(self, grant: dict) -> dict:
        independent = grant["independent_review"]["reviewed_sha"]
        path = grant["review_evidence_paths"][0]
        return {
            "grant_review_evidence_existing": [path],
            "grant_review_evidence": [{
                "path": path,
                "object_type": "blob",
                "object_mode": "100644",
                "content": "Frozen package completion evidence.",
                "git_blob_sha": grant["independent_review"]["evidence_git_blob_sha"],
                "bytes_sha256": grant["independent_review"]["evidence_bytes_sha256"],
            }],
        }

    def _future_direction_origin(self) -> tuple[dict, dict, str]:
        origin, profile = self._direction_origin()
        lane = copy.deepcopy(profile)
        lane["package"] = "PS-FUTURE-DIRECTION-001"
        lane["branch"] = "work/2026-09-01-future-direction-001"
        lane["writable_surfaces"] = [
            "docs/initiatives/PS-FUTURE-DIRECTION-001/"
        ]
        lane["exclusive_domains"] = ["product:future-direction"]
        lane["owner_decisions"] = [{
            "date": "2026-09-01",
            "decision": "direction_package_merge_authority",
            "authorized_by": "Pete",
            "action": "merge",
            "status": "authorized",
            "scope": "direction_package_only",
            "package": lane["package"],
        }]
        origin["active_lanes"] = [lane]
        for field in ("writes_allowed_for",):
            origin["operating_mode"][field] = [lane["package"]]
        for field in ("merge_allowed_for", "cleanup_allowed_for", "release_allowed_for"):
            origin["operating_mode"][field] = []
        reviewed = "a" * 40
        return origin, lane, reviewed

    def _future_grant_record(self, lane: dict, reviewed: str) -> dict:
        evidence_path = (
            lane["writable_surfaces"][0].rstrip("/")
            + "/16_VERIFICATION_AND_COMPLETION_RECORD.md"
        )
        verdict = (
            "PASS — exact-SHA final Protected review passed for "
            f"{reviewed}, branch-equal to origin/{lane['branch']} and clean."
        )
        review = {
            "reviewer_task": "/root/future_direction_exact_review",
            "reviewer_mode": "independent_read_only_non_writer",
            "reviewed_sha": reviewed,
            "reviewed_branch": lane["branch"],
            "verdict": "PASS",
            "verdict_text": verdict,
            "verdict_sha256": hashlib.sha256(verdict.encode("utf-8")).hexdigest(),
            "basis": [
                "full_tree_at_" + reviewed,
                "complete_diff_" + ("b" * 40) + "_to_" + reviewed,
            ],
            "scope": "direction_package_acceptance_and_merge_only",
            "exclusions": "runtime_schema_deployment_enablement",
            "evidence_path": evidence_path,
            "evidence_git_blob_sha": "c" * 40,
            "evidence_bytes_sha256": "d" * 64,
            "received_by": "Root Codex program manager",
            "received_date": "2026-09-01",
        }
        review["attestation_sha256"] = _canonical_sha256(review)
        decision = lane["owner_decisions"][0]
        return {
            "authorized_by": "Pete",
            "authority_decision_index": 0,
            "authority_decision_sha256": _canonical_sha256(decision),
            "independent_review": review,
            "reviewed_remote_sha": reviewed,
            "granted_at": "2026-09-01T20:00:00Z",
            "review_result": "pass",
            "review_evidence_paths": [evidence_path],
        }

    def test_grant_binds_existing_authority_review_and_exact_remote(self):
        origin, lane = self._direction_origin()
        candidate = copy.deepcopy(origin)
        reviewed = PROFILE_DIRECTION_REVIEW_ATTESTATION["reviewed_sha"]
        candidate_lane = candidate["active_lanes"][0]
        candidate_lane["merge_grant"] = self._grant_record(lane, reviewed)
        candidate["operating_mode"]["merge_allowed_for"] = [lane["package"]]
        candidate["updated_at"] = "2026-08-12T03:00:00Z"
        grant_facts = facts(
            branch="work/2026-08-12-delivery-grant-profile-direction",
            ahead=1,
            changed_paths=["docs/governance/CURRENT_LANES.json"],
            grant_target_remote_sha=reviewed,
            **self._review_evidence_facts(candidate_lane["merge_grant"]),
        )
        errors, _ = evaluate_policy(
            candidate, grant_facts, lane["package"], "grant",
            require_clean=True, origin_ledger=origin,
            candidate_baseline=self.baseline, origin_baseline=self.baseline,
        )
        self.assertEqual([], errors)

        for stale_timestamp in (
            origin["updated_at"],
            "2026-08-12T01:59:59Z",
        ):
            with self.subTest(grant_timestamp=stale_timestamp):
                stale = copy.deepcopy(candidate)
                stale["updated_at"] = stale_timestamp
                stale["active_lanes"][0]["merge_grant"]["granted_at"] = (
                    stale_timestamp
                )
                stale_errors, _ = evaluate_policy(
                    stale, grant_facts, lane["package"], "grant",
                    require_clean=True, origin_ledger=origin,
                    candidate_baseline=self.baseline,
                    origin_baseline=self.baseline,
                )
                self.assertTrue(
                    any(
                        "updated_at" in error and "strictly advance" in error
                        for error in stale_errors
                    )
                )

        mismatched_grant_time = copy.deepcopy(candidate)
        mismatched_grant_time["active_lanes"][0]["merge_grant"][
            "granted_at"
        ] = "2026-08-12T03:00:01Z"
        mismatch_errors, _ = evaluate_policy(
            mismatched_grant_time, grant_facts, lane["package"], "grant",
            require_clean=True, origin_ledger=origin,
            candidate_baseline=self.baseline, origin_baseline=self.baseline,
        )
        self.assertTrue(
            any(
                "granted_at" in error and "ledger updated_at" in error
                for error in mismatch_errors
            )
        )

        forged = copy.deepcopy(candidate)
        forged["active_lanes"][0]["owner_decisions"].append(
            {"date": "2026-08-12", "decision": "grant"}
        )
        forged_errors, _ = evaluate_policy(
            forged, grant_facts, lane["package"], "grant",
            require_clean=True, origin_ledger=origin,
            candidate_baseline=self.baseline, origin_baseline=self.baseline,
        )
        self.assertTrue(any("owner_decisions" in error for error in forged_errors))

        production = copy.deepcopy(candidate)
        production["active_lanes"][0]["production_capable"] = True
        production_errors, _ = evaluate_policy(
            production, grant_facts, lane["package"], "grant",
            require_clean=True, origin_ledger=origin,
            candidate_baseline=self.baseline, origin_baseline=self.baseline,
        )
        self.assertTrue(any("production_capable false" in error for error in production_errors))

        implementation = copy.deepcopy(candidate)
        implementation["active_lanes"][0]["lane_class"] = "implementation"
        implementation_errors, _ = evaluate_policy(
            implementation, grant_facts, lane["package"], "grant",
            require_clean=True, origin_ledger=origin,
            candidate_baseline=self.baseline, origin_baseline=self.baseline,
        )
        self.assertTrue(
            any("direction_authority" in error for error in implementation_errors)
        )

        missing_errors, _ = evaluate_policy(
            candidate, {**grant_facts, "grant_review_evidence_existing": []},
            lane["package"], "grant", require_clean=True, origin_ledger=origin,
            candidate_baseline=self.baseline, origin_baseline=self.baseline,
        )
        self.assertTrue(any("evidence path" in error for error in missing_errors))

    def test_opportunity_grant_binds_owner_review_ci_and_dark_release(self):
        origin, lane = self._opportunity_origin()
        candidate = copy.deepcopy(origin)
        candidate_lane = next(
            item for item in candidate["active_lanes"]
            if item.get("package") == OPPORTUNITY_SLATE_PACKAGE
        )
        candidate_lane["owner_decisions"].append(self._opportunity_decision())
        decision_index = len(candidate_lane["owner_decisions"]) - 1
        granted_at = "2026-08-12T12:00:00Z"
        candidate_lane["merge_grant"] = self._opportunity_grant_record(
            candidate_lane, decision_index, granted_at
        )
        candidate["operating_mode"]["merge_allowed_for"] = [
            OPPORTUNITY_SLATE_PACKAGE
        ]
        candidate["operating_mode"]["release_allowed_for"] = [
            OPPORTUNITY_SLATE_PACKAGE
        ]
        candidate["updated_at"] = granted_at
        grant_facts = facts(
            branch="work/2026-08-12-delivery-grant-oppslate-r1",
            ahead=1,
            changed_paths=["docs/governance/CURRENT_LANES.json"],
            grant_target_remote_sha=OPPORTUNITY_SLATE_REVIEWED_SHA,
            **self._review_evidence_facts(candidate_lane["merge_grant"]),
        )
        errors, _ = evaluate_policy(
            candidate, grant_facts, OPPORTUNITY_SLATE_PACKAGE, "grant",
            require_clean=True, origin_ledger=origin,
            candidate_baseline=self.baseline, origin_baseline=self.baseline,
        )
        self.assertEqual([], errors)
        self.assertTrue(
            _exact_direction_grant_delta(
                origin, candidate, OPPORTUNITY_SLATE_PACKAGE
            )
        )

        widened = copy.deepcopy(candidate)
        widened_lane = next(
            item for item in widened["active_lanes"]
            if item.get("package") == OPPORTUNITY_SLATE_PACKAGE
        )
        widened_lane["merge_grant"]["release_scope"][
            "public_enablement"
        ] = True
        widened_errors, _ = evaluate_policy(
            widened, grant_facts, OPPORTUNITY_SLATE_PACKAGE, "grant",
            require_clean=True, origin_ledger=origin,
            candidate_baseline=self.baseline, origin_baseline=self.baseline,
        )
        self.assertTrue(
            any("release_scope" in error for error in widened_errors)
        )

        occupied = copy.deepcopy(origin)
        occupied["operating_mode"]["release_allowed_for"] = [
            "PS-INTERVIEW-STUDIO-AUTHENTICATED-EXPERIENCE-001"
        ]
        occupied_errors, _ = evaluate_policy(
            candidate, grant_facts, OPPORTUNITY_SLATE_PACKAGE, "grant",
            require_clean=True, origin_ledger=occupied,
            candidate_baseline=self.baseline, origin_baseline=self.baseline,
        )
        self.assertTrue(
            any("serialized release slot" in error for error in occupied_errors)
        )

    def test_merge_requires_origin_grant_exact_head_remote_and_nonoverlap(self):
        origin, lane = self._direction_origin()
        reviewed = PROFILE_DIRECTION_REVIEW_ATTESTATION["reviewed_sha"]
        lane["merge_grant"] = self._grant_record(lane, reviewed)
        origin["active_lanes"] = [lane]
        origin["operating_mode"]["merge_allowed_for"] = [lane["package"]]
        merge_facts = facts(
            branch=lane["branch"], head=reviewed, behind=3,
            merge_target_remote_sha=reviewed,
            changed_paths=[lane["writable_surfaces"][0].rstrip("/") + "/README.md"],
            merge_main_changed_paths=sorted(
                DIRECTION_MERGE_CONTROL_PATHS
                | DIRECTION_MERGE_FOLLOWUP_PATHS
                | {"docs/governance/CURRENT_LANES.json"}
            ),
            merge_main_control_commits_valid=True,
        )
        errors, warnings = evaluate_policy(
            origin, merge_facts, lane["package"], "merge",
            require_clean=True, origin_ledger=origin,
        )
        self.assertEqual([], errors)
        self.assertTrue(any("exact verified control" in warning for warning in warnings))
        overlap, _ = evaluate_policy(
            origin, {**merge_facts, "merge_main_changed_paths": [lane["writable_surfaces"][0].rstrip("/") + "/README.md"]},
            lane["package"], "merge", require_clean=True, origin_ledger=origin,
        )
        self.assertTrue(any("control paths" in error for error in overlap))
        wrong_head, _ = evaluate_policy(
            origin, {**merge_facts, "head": "3" * 40}, lane["package"], "merge",
            require_clean=True, origin_ledger=origin,
        )
        self.assertTrue(any("HEAD" in error for error in wrong_head))

        app_movement, _ = evaluate_policy(
            origin, {**merge_facts, "merge_main_changed_paths": ["app.py"]},
            lane["package"], "merge", require_clean=True, origin_ledger=origin,
        )
        self.assertTrue(any("exact reviewed control paths" in error for error in app_movement))

        for invalid_behind in (0, 1, 2, 4):
            with self.subTest(invalid_behind=invalid_behind):
                count_errors, _ = evaluate_policy(
                    origin, {**merge_facts, "behind": invalid_behind},
                    lane["package"], "merge", require_clean=True,
                    origin_ledger=origin,
                )
                self.assertTrue(
                    any("exactly 3 verified main control" in error for error in count_errors)
                )

    def test_frozen_direction_candidate_is_verified_by_trusted_current_main_cli(self):
        """Exercise the real repair -> grant -> frozen-candidate merge path.

        The candidate intentionally keeps the pre-repair validator at its
        independently reviewed SHA.  A separate clean verifier worktree runs
        the current script from origin/main without rebasing, overlaying, or
        otherwise changing the candidate.
        """

        package = "PS-PROFILE-EXPERIENCE-001"
        candidate_branch = "work/2026-08-11-profile-experience-direction-001"
        candidate_sha = PROFILE_DIRECTION_REVIEW_ATTESTATION["reviewed_sha"]
        repair_base = GRANT_CLOSE_PREFLIGHT_REPAIR["origin_main"]

        def run(
            *args: str,
            cwd: Path | None = None,
            check: bool = True,
        ) -> subprocess.CompletedProcess[str]:
            result = subprocess.run(
                [str(arg) for arg in args],
                cwd=str(cwd) if cwd is not None else None,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            if check and result.returncode:
                self.fail(
                    f"command failed ({result.returncode}): {' '.join(args)}\n"
                    f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
                )
            return result

        def git(repository: Path, *args: str, check: bool = True):
            return run("git", "-C", str(repository), *args, check=check)

        def invoke(verifier: Path, candidate: Path, *extra: str):
            fixture_identity = (
                "https://dev.azure.com/peerslate-test/direction-fixture/_git/portfolio"
            )
            bootstrap = f"""
import importlib.util
import sys
from unittest.mock import patch
script = {str(verifier / "scripts" / "delivery_preflight.py")!r}
spec = importlib.util.spec_from_file_location("delivery_preflight_fixture", script)
delivery_preflight = importlib.util.module_from_spec(spec)
spec.loader.exec_module(delivery_preflight)
with patch.object(
    delivery_preflight,
    "_authoritative_azure_origin",
    return_value={fixture_identity!r},
):
    raise SystemExit(delivery_preflight.main())
"""
            return run(
                sys.executable,
                "-I",
                "-c",
                bootstrap,
                "--package",
                package,
                "--intent",
                "merge",
                "--fetch",
                "--require-clean",
                "--candidate-worktree",
                str(candidate.resolve()),
                *extra,
                cwd=verifier,
                check=False,
            )

        with tempfile.TemporaryDirectory(prefix="ps-direction-candidate-") as raw:
            fixture = Path(raw).resolve()
            seed = fixture / "seed"
            origin = fixture / "dev.azure.com-direction-origin.git"
            verifier = fixture / "verifier"
            candidate = fixture / "candidate"
            outsider = fixture / "outsider"

            # Reuse the repository's immutable objects, but construct a new
            # local Azure-shaped origin so the CLI performs real fetches.
            run("git", "clone", "--shared", str(ROOT), str(seed))
            git(seed, "config", "user.name", "PeerSlate Test")
            git(seed, "config", "user.email", "peerslate-test@example.invalid")
            repair_result = GRANT_CLOSE_FIXTURE_FOLLOWUP["origin_main"]
            git(seed, "checkout", "-B", "repair-fixture", repair_result)
            repair_sha = git(seed, "rev-parse", "HEAD").stdout.strip()
            self.assertEqual(repair_result, repair_sha)
            self.assertEqual(
                repair_base,
                git(seed, "rev-parse", f"{repair_sha}^").stdout.strip(),
            )
            repaired_ledger = json.loads(
                (seed / "docs" / "governance" / "CURRENT_LANES.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(
                GRANT_CLOSE_PREFLIGHT_REPAIR,
                repaired_ledger["grant_close_preflight_repair"],
            )

            ledger_path = seed / "docs" / "governance" / "CURRENT_LANES.json"
            # Recreate the exact inert follow-up from immutable repair state.
            # Only the validated script/test implementation bytes come from
            # this running revision; the mutable checked-in ledger never does.
            for relative in (
                "scripts/delivery_preflight.py",
                "tests/test_delivery_preflight.py",
            ):
                source = ROOT / relative
                destination = seed / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
            followup_ledger = copy.deepcopy(repaired_ledger)
            followup_ledger["updated_at"] = "2026-08-12T07:55:42Z"
            followup_ledger["grant_close_fixture_followup"] = copy.deepcopy(
                GRANT_CLOSE_FIXTURE_FOLLOWUP
            )
            self.assertTrue(
                _exact_grant_close_fixture_followup_delta(
                    repaired_ledger, followup_ledger
                )
            )
            ledger_path.write_text(
                json.dumps(followup_ledger, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            git(seed, "add", "--", *GRANT_CLOSE_FIXTURE_FOLLOWUP["allowed_surfaces"])
            followup_paths = {
                line for line in git(
                    seed, "diff", "--cached", "--name-only"
                ).stdout.splitlines() if line
            }
            self.assertEqual(
                set(GRANT_CLOSE_FIXTURE_FOLLOWUP["allowed_surfaces"]),
                followup_paths,
            )
            git(seed, "commit", "-m", "Stabilize grant-close validation fixtures")
            followup_sha = git(seed, "rev-parse", "HEAD").stdout.strip()
            self.assertEqual(repair_sha, git(seed, "rev-parse", f"{followup_sha}^").stdout.strip())

            # The grant is a distinct, ledger-only commit after the follow-up.
            ledger_path = seed / "docs" / "governance" / "CURRENT_LANES.json"
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            lane = next(
                item for item in ledger["active_lanes"]
                if item.get("package") == package
            )
            lane["merge_grant"] = self._grant_record(lane, candidate_sha)
            lane["merge_grant"]["granted_at"] = "2026-08-12T08:00:00Z"
            ledger["operating_mode"]["merge_allowed_for"] = [
                *ledger["operating_mode"].get("merge_allowed_for", []),
                package,
            ]
            ledger["updated_at"] = "2026-08-12T08:00:00Z"
            ledger_path.write_text(
                json.dumps(ledger, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            git(seed, "add", "--", "docs/governance/CURRENT_LANES.json")
            git(seed, "commit", "-m", "Grant exact Profile direction merge")
            grant_sha = git(seed, "rev-parse", "HEAD").stdout.strip()
            self.assertEqual(
                followup_sha,
                git(seed, "rev-parse", f"{grant_sha}^").stdout.strip(),
            )

            run("git", "init", "--bare", str(origin))
            git(seed, "remote", "add", "fixture-origin", str(origin))
            git(seed, "push", "fixture-origin", "HEAD:refs/heads/main")
            git(
                seed,
                "push",
                "fixture-origin",
                f"{candidate_sha}:refs/heads/{candidate_branch}",
            )
            run(
                "git", "--git-dir", str(origin), "symbolic-ref", "HEAD", "refs/heads/main"
            )

            run("git", "clone", str(origin), str(verifier))
            git(verifier, "worktree", "add", "-b", candidate_branch,
                str(candidate), f"origin/{candidate_branch}")
            self.assertEqual(
                repair_base,
                git(verifier, "merge-base", candidate_sha, "origin/main")
                .stdout.strip(),
            )

            # The frozen candidate proves why current-main verification is
            # required: its old parser cannot understand candidate mode.
            old_script = run(
                sys.executable,
                str(candidate / "scripts" / "delivery_preflight.py"),
                "--package",
                package,
                "--intent",
                "merge",
                "--fetch",
                "--require-clean",
                "--candidate-worktree",
                str(candidate),
                cwd=candidate,
                check=False,
            )
            self.assertNotEqual(0, old_script.returncode)

            passed = invoke(verifier, candidate)
            self.assertEqual(0, passed.returncode, passed.stdout + passed.stderr)
            payload = json.loads(passed.stdout)
            self.assertEqual("pass", payload["result"])
            self.assertTrue(payload["facts"]["direction_candidate_verified_from_main"])
            self.assertEqual(candidate_sha, payload["facts"]["candidate_head"])
            self.assertEqual(3, payload["facts"]["behind"])
            self.assertEqual(
                candidate_sha,
                git(candidate, "rev-parse", "HEAD").stdout.strip(),
            )

            git(candidate, "config", "status.showUntrackedFiles", "no")
            (candidate / "untracked-proof.txt").write_text("dirty", encoding="utf-8")
            dirty = invoke(verifier, candidate)
            self.assertEqual(2, dirty.returncode)
            self.assertIn("candidate worktree must be clean", dirty.stdout)
            (candidate / "untracked-proof.txt").unlink()
            git(candidate, "config", "--unset", "status.showUntrackedFiles")

            git(candidate, "checkout", "--detach", candidate_sha)
            detached = invoke(verifier, candidate)
            self.assertEqual(2, detached.returncode)
            self.assertIn("branch must equal the lane branch", detached.stdout)
            git(candidate, "checkout", candidate_branch)

            # A clone with the same commit and origin text is still a
            # different repository/common-dir and cannot impersonate the
            # registered candidate worktree.
            run(
                "git", "clone", "--branch", candidate_branch,
                str(origin), str(outsider)
            )
            foreign = invoke(verifier, outsider)
            self.assertEqual(2, foreign.returncode)
            self.assertIn("exactly registered Git worktrees", foreign.stdout)

            misuse = invoke(verifier, verifier)
            self.assertEqual(2, misuse.returncode)
            self.assertIn("must differ from the verifier worktree", misuse.stdout)

            missing_contract = run(
                sys.executable,
                str(verifier / "scripts" / "delivery_preflight.py"),
                "--package",
                package,
                "--intent",
                "merge",
                "--candidate-worktree",
                str(candidate),
                cwd=verifier,
                check=False,
            )
            self.assertEqual(2, missing_contract.returncode)
            self.assertIn(
                "requires --intent merge --fetch --require-clean",
                missing_contract.stdout,
            )

    def test_authoritative_origin_rejects_instead_of_redirection(self):
        configured = (
            "https://dev.azure.com/peerslate19/portfolio-site/_git/portfolio-site"
        )
        redirected = "file:///tmp/attacker-controlled-origin.git"

        def fake_git_at(_repository: Path, *args: str, **_kwargs) -> str:
            if args == ("config", "--get", "remote.origin.url"):
                return configured
            if args == ("remote", "get-url", "origin"):
                return redirected
            self.fail(f"unexpected git command: {args}")

        with patch(
            "scripts.delivery_preflight._git_at", side_effect=fake_git_at
        ):
            with self.assertRaisesRegex(RuntimeError, "rewrite or indirection"):
                _authoritative_azure_origin(ROOT)

    def test_git_environment_disables_object_and_worktree_redirection(self):
        injected = {
            "GIT_DIR": "C:/attacker/repo.git",
            "GIT_WORK_TREE": "C:/attacker/tree",
            "GIT_SHALLOW_FILE": "C:/attacker/shallow",
            "GIT_REPLACE_REF_BASE": "refs/replace/attacker",
            "GIT_NO_REPLACE_OBJECTS": "0",
        }
        with patch.dict(os.environ, injected, clear=False):
            environment = _git_environment()

        for name in (
            "GIT_DIR",
            "GIT_WORK_TREE",
            "GIT_SHALLOW_FILE",
            "GIT_REPLACE_REF_BASE",
        ):
            self.assertNotIn(name, environment)
        self.assertEqual("1", environment["GIT_NO_REPLACE_OBJECTS"])

    def test_authoritative_origin_is_pinned_to_peerslate_repository(self):
        accepted = (
            "https://peerslate19@dev.azure.com/peerslate19/"
            "portfolio-site/_git/portfolio-site"
        )

        def result_for(url: str):
            def fake_git_at(_repository: Path, *args: str, **_kwargs) -> str:
                if args in (
                    ("config", "--get", "remote.origin.url"),
                    ("remote", "get-url", "origin"),
                ):
                    return url
                self.fail(f"unexpected git command: {args}")

            return fake_git_at

        with patch(
            "scripts.delivery_preflight._git_at", side_effect=result_for(accepted)
        ):
            self.assertEqual(accepted.casefold(), _authoritative_azure_origin(ROOT))

        rejected = (
            "https://dev.azure.com/wrong/portfolio-site/_git/portfolio-site",
            "https://dev.azure.com/peerslate19/wrong/_git/portfolio-site",
            "https://dev.azure.com/peerslate19/portfolio-site/_git/wrong",
            (
                "https://user:secret@dev.azure.com/peerslate19/portfolio-site/"
                "_git/portfolio-site"
            ),
            (
                "https://dev.azure.com:8443/peerslate19/portfolio-site/"
                "_git/portfolio-site"
            ),
            (
                "https://dev.azure.com/peerslate19/portfolio-site/"
                "_git/portfolio-site?redirect=1"
            ),
            (
                "https://dev.azure.com/peerslate19/portfolio-site/"
                "_git/portfolio-site#other"
            ),
        )
        for url in rejected:
            with self.subTest(url=url), patch(
                "scripts.delivery_preflight._git_at", side_effect=result_for(url)
            ):
                with self.assertRaisesRegex(RuntimeError, "exact PeerSlate"):
                    _authoritative_azure_origin(ROOT)

    def test_exact_fetch_defeats_narrow_or_missing_configured_refspec(self):
        def git(repository: Path, *args: str, check: bool = True) -> str:
            result = subprocess.run(
                ["git", "-C", str(repository), *args],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            if check and result.returncode:
                self.fail(result.stderr or "fixture git command failed")
            return result.stdout.strip()

        with tempfile.TemporaryDirectory(prefix="ps-exact-ref-fetch-") as raw:
            fixture = Path(raw).resolve()
            origin = fixture / "origin.git"
            seed = fixture / "seed"
            verifier = fixture / "verifier"
            subprocess.run(
                ["git", "init", "--bare", str(origin)],
                capture_output=True,
                check=True,
            )
            subprocess.run(
                ["git", "init", "-b", "main", str(seed)],
                capture_output=True,
                check=True,
            )
            git(seed, "config", "user.name", "PeerSlate Test")
            git(seed, "config", "user.email", "test@example.invalid")
            (seed / "proof.txt").write_text("one\n", encoding="utf-8")
            git(seed, "add", "proof.txt")
            git(seed, "commit", "-m", "Fixture endpoint")
            expected = git(seed, "rev-parse", "HEAD")
            git(seed, "branch", "candidate")
            git(seed, "remote", "add", "origin", str(origin))
            git(seed, "push", "origin", "main", "candidate")
            subprocess.run(
                [
                    "git", "--git-dir", str(origin), "symbolic-ref", "HEAD",
                    "refs/heads/main",
                ],
                capture_output=True,
                check=True,
            )
            subprocess.run(
                ["git", "clone", str(origin), str(verifier)],
                capture_output=True,
                check=True,
            )

            for label, configured_refspec in (
                ("narrow", "+refs/heads/unrelated:refs/remotes/origin/unrelated"),
                ("missing", None),
            ):
                with self.subTest(configured_refspec=label):
                    git(
                        verifier, "config", "--unset-all", "remote.origin.fetch",
                        check=False,
                    )
                    if configured_refspec is not None:
                        git(
                            verifier, "config", "--add", "remote.origin.fetch",
                            configured_refspec,
                        )
                    git(verifier, "update-ref", "-d", "refs/remotes/origin/main")
                    git(
                        verifier, "update-ref", "-d",
                        "refs/remotes/origin/candidate",
                    )
                    fetched = _fetch_exact_origin_refs(
                        verifier, ["main", "candidate"]
                    )
                    self.assertEqual(
                        {"main": expected, "candidate": expected}, fetched
                    )
                    self.assertEqual(
                        expected,
                        git(verifier, "rev-parse", "refs/remotes/origin/main"),
                    )
                    self.assertEqual(
                        expected,
                        git(
                            verifier, "rev-parse",
                            "refs/remotes/origin/candidate",
                        ),
                    )

    def test_generic_active_and_closing_non_direction_merges_still_work(self):
        for state in ("active", "closing"):
            with self.subTest(state=state):
                ledger = copy.deepcopy(self.ledger)
                if state == "active":
                    lane = self._lane_fixture(ledger)
                else:
                    lane = next(
                        item
                        for item in ledger["closing_lanes"]
                        if item.get("branch")
                    )
                # Profile Core and Connect 002 are intentionally not generic
                # implementation fixtures: each exact package name is reserved
                # for its frozen review-bound candidate path exercised above.
                if lane["package"] in {
                    PROFILE_CORE_INTEGRATION_PACKAGE,
                    CONNECT_002_PACKAGE,
                }:
                    lane["package"] = "PS-GENERIC-IMPLEMENTATION-001"
                    lane["branch"] = "work/2026-08-13-generic-implementation-001"
                lane["lane_class"] = "implementation"
                lane["production_capable"] = True
                package = lane["package"]
                ledger["operating_mode"]["merge_allowed_for"] = [package]
                if state == "active":
                    ledger["active_lanes"] = [lane]
                    ledger["operating_mode"]["state"] = "active_delivery"
                else:
                    ledger["active_lanes"] = []
                    ledger["closing_lanes"] = [lane]
                    ledger["operating_mode"]["state"] = "controlled_idle"
                generic_facts = facts(
                    branch=lane["branch"], ahead=1,
                    changed_paths=[lane["writable_surfaces"][0]],
                )
                errors, _ = evaluate_policy(
                    ledger, generic_facts, package, "merge",
                    require_clean=True, origin_ledger=ledger,
                )
                self.assertEqual([], errors)

    def test_close_requires_tree_equivalence_and_removes_all_authority(self):
        origin, lane = self._direction_origin()
        reviewed = PROFILE_DIRECTION_REVIEW_ATTESTATION["reviewed_sha"]
        lane["merge_grant"] = self._grant_record(lane, reviewed)
        origin["active_lanes"] = [lane]
        for field in ("writes_allowed_for", "merge_allowed_for"):
            origin["operating_mode"][field] = [lane["package"]]
        candidate = copy.deepcopy(origin)
        candidate["active_lanes"] = []
        candidate["operating_mode"]["state"] = "controlled_idle"
        candidate["operating_mode"]["writes_allowed_for"] = []
        candidate["operating_mode"]["merge_allowed_for"] = []
        candidate["operating_mode"]["exit_authority"] = (
            "No active writer lanes. " + lane["package"]
            + " is merged_closed and retains no authority."
        )
        candidate["updated_at"] = "2026-08-12T04:00:00Z"
        closing = copy.deepcopy(lane)
        evidence_path = lane["merge_grant"]["review_evidence_paths"][0]
        closing.update({
            "disposition": "merged_closed",
            "closed_at": "2026-08-12T04:00:00Z",
            "reviewed_remote_sha": reviewed,
            "merged_main_sha": facts()["origin_main"],
            "package_merge_sha": "5" * 40,
            "close_evidence_paths": [evidence_path],
        })
        candidate["closing_lanes"] = [*origin.get("closing_lanes", []), closing]
        origin_baseline = self._baseline_for_origin(
            origin,
            load_baseline_bytes_at_ref(PROFILE_DIRECTION_PRE_CLOSE_MAIN),
        )
        source = origin_baseline.decode("utf-8")
        candidate_baseline = re.sub(
            r'^  current_assignments: .+$',
            f'  current_assignments: "No active writer lanes. {lane["package"]} is closed and archived; activate an exact implementation or direction/authority outcome before repository writes."',
            source, count=1, flags=re.MULTILINE,
        )
        section = re.search(r"(?ms)^active_packages:\n(?P<body>.*?)(?=^scoped_findings:\n)", candidate_baseline)
        candidate_baseline = candidate_baseline[:section.start()] + "active_packages:\n" + candidate_baseline[section.end():]
        candidate_baseline = re.sub(
            r'^next_gate: .+$',
            'next_gate: "No active writer lanes. Select and activate the next exact outcome under the three-lane class, path, and exclusive-domain rules."',
            candidate_baseline, count=1, flags=re.MULTILINE,
        )
        candidate_baseline = candidate_baseline.replace(
            "\nretired_packages:\n",
            f"  - {lane['package']}\nretired_packages:\n",
            1,
        ).encode("utf-8")
        close_facts = facts(
            branch="work/2026-08-12-delivery-close-profile-direction",
            ahead=1,
            changed_paths=sorted(["docs/governance/CURRENT_BASELINE.yaml", "docs/governance/CURRENT_LANES.json"]),
            close_target_remote_sha=reviewed, close_surface_tree_equal=True,
            close_package_merge_sha="5" * 40,
            close_package_merge_ancestor=True,
            close_package_merge_introduced_candidate=True,
            close_evidence_existing=[evidence_path],
        )
        errors, _ = evaluate_policy(
            candidate, close_facts, lane["package"], "close", require_clean=True,
            origin_ledger=origin, candidate_baseline=candidate_baseline,
            origin_baseline=origin_baseline,
        )
        self.assertEqual([], errors)

        for stale_timestamp in (
            origin["updated_at"],
            "2026-08-12T01:59:59Z",
        ):
            with self.subTest(close_timestamp=stale_timestamp):
                stale = copy.deepcopy(candidate)
                stale["updated_at"] = stale_timestamp
                stale["closing_lanes"][-1]["closed_at"] = stale_timestamp
                stale_errors, _ = evaluate_policy(
                    stale, close_facts, lane["package"], "close",
                    require_clean=True, origin_ledger=origin,
                    candidate_baseline=candidate_baseline,
                    origin_baseline=origin_baseline,
                )
                self.assertTrue(
                    any(
                        "updated_at" in error and "strictly advance" in error
                        for error in stale_errors
                    )
                )

        mismatched_close_time = copy.deepcopy(candidate)
        mismatched_close_time["closing_lanes"][-1]["closed_at"] = (
            "2026-08-12T04:00:01Z"
        )
        mismatch_errors, _ = evaluate_policy(
            mismatched_close_time, close_facts, lane["package"], "close",
            require_clean=True, origin_ledger=origin,
            candidate_baseline=candidate_baseline,
            origin_baseline=origin_baseline,
        )
        self.assertTrue(
            any(
                "closed_at" in error and "ledger updated_at" in error
                for error in mismatch_errors
            )
        )
        unequal, _ = evaluate_policy(
            candidate, {**close_facts, "close_surface_tree_equal": False},
            lane["package"], "close", require_clean=True, origin_ledger=origin,
            candidate_baseline=candidate_baseline, origin_baseline=origin_baseline,
        )
        self.assertTrue(any("tree equivalence" in error for error in unequal))

        for mutation, expected in (
            ({"ahead": 0}, "exactly one commit"),
            ({"ahead": 2}, "exactly one commit"),
            ({"close_package_merge_ancestor": False}, "must be an ancestor"),
            ({"close_package_merge_introduced_candidate": False}, "introduced the reviewed"),
            ({"close_surface_tree_equal": False}, "tree equivalence"),
            ({"close_target_remote_sha": "e" * 40}, "remain the reviewed SHA"),
            ({"close_evidence_existing": []}, "bounded evidence path"),
        ):
            with self.subTest(mutation=mutation):
                mutated_errors, _ = evaluate_policy(
                    candidate, {**close_facts, **mutation}, lane["package"], "close",
                    require_clean=True, origin_ledger=origin,
                    candidate_baseline=candidate_baseline,
                    origin_baseline=origin_baseline,
                )
                self.assertTrue(any(expected in error for error in mutated_errors))

        no_permission = copy.deepcopy(origin)
        no_permission["operating_mode"]["merge_allowed_for"] = []
        permission_errors, _ = evaluate_policy(
            candidate, close_facts, lane["package"], "close",
            require_clean=True, origin_ledger=no_permission,
            candidate_baseline=candidate_baseline, origin_baseline=origin_baseline,
        )
        self.assertTrue(any("merge permission" in error for error in permission_errors))

        invalid_time = copy.deepcopy(candidate)
        invalid_time["updated_at"] = "2026-02-30T04:00:00Z"
        invalid_time["closing_lanes"][-1]["closed_at"] = "2026-02-30T04:00:00Z"
        time_errors, _ = evaluate_policy(
            invalid_time, close_facts, lane["package"], "close",
            require_clean=True, origin_ledger=origin,
            candidate_baseline=candidate_baseline, origin_baseline=origin_baseline,
        )
        self.assertTrue(any("real UTC timestamp" in error for error in time_errors))
        self.assertTrue(any("closed_at" in error for error in time_errors))

        smuggled_baseline = candidate_baseline.decode("utf-8").replace(
            f"  - {lane['package']}\nretired_packages:",
            f"  - PS-SMUGGLED-001\n  - {lane['package']}\nretired_packages:",
        ).encode("utf-8")
        smuggle_errors, _ = evaluate_policy(
            candidate, close_facts, lane["package"], "close",
            require_clean=True, origin_ledger=origin,
            candidate_baseline=smuggled_baseline, origin_baseline=origin_baseline,
        )
        self.assertTrue(any("append exactly" in error for error in smuggle_errors))

    def test_grant_close_bootstrap_is_exact_and_grants_nothing(self):
        origin = load_ledger_at_ref(GRANT_CLOSE_PREFLIGHT_REPAIR["origin_main"])
        candidate = copy.deepcopy(origin)
        candidate["grant_close_preflight_repair"] = copy.deepcopy(
            GRANT_CLOSE_PREFLIGHT_REPAIR
        )
        candidate["updated_at"] = "2026-08-12T05:00:00Z"
        immutable_baseline = load_baseline_bytes_at_ref(
            GRANT_CLOSE_PREFLIGHT_REPAIR["origin_main"]
        )
        self.assertEqual([], candidate["operating_mode"]["merge_allowed_for"])
        exact = facts(
            branch=GRANT_CLOSE_PREFLIGHT_REPAIR["branch"],
            origin_main=GRANT_CLOSE_PREFLIGHT_REPAIR["origin_main"],
            ahead=1,
            changed_paths=GRANT_CLOSE_PREFLIGHT_REPAIR["allowed_surfaces"],
        )
        errors, warnings = self._evaluate_activation(
            candidate, exact, require_clean=True, origin=origin,
            candidate_baseline=immutable_baseline, origin_baseline=immutable_baseline,
        )
        self.assertEqual([], errors)
        self.assertTrue(any("grant-close" in warning for warning in warnings))
        forged = copy.deepcopy(candidate)
        forged["grant_close_preflight_repair"]["branch"] = "work/forged"
        forged_errors, _ = self._evaluate_activation(
            forged, exact, require_clean=True, origin=origin,
            candidate_baseline=immutable_baseline, origin_baseline=immutable_baseline,
        )
        self.assertTrue(forged_errors)

        for invalid_time in (
            origin["updated_at"],
            "not-a-timestamp",
        ):
            with self.subTest(invalid_repair_time=invalid_time):
                stale = copy.deepcopy(candidate)
                stale["updated_at"] = invalid_time
                stale_errors, _ = self._evaluate_activation(
                    stale, exact, require_clean=True, origin=origin,
                    candidate_baseline=immutable_baseline,
                    origin_baseline=immutable_baseline,
                )
                self.assertTrue(
                    any("updated_at" in error for error in stale_errors)
                )

    def test_implementation_release_repair_is_exact_and_grants_nothing(self):
        repair = IMPLEMENTATION_RELEASE_PREFLIGHT_REPAIR
        origin = load_ledger_at_ref(repair["origin_main"])
        candidate = copy.deepcopy(origin)
        candidate["updated_at"] = "2026-08-12T11:35:08Z"
        candidate["implementation_release_preflight_repair"] = copy.deepcopy(
            repair
        )
        baseline = load_baseline_bytes_at_ref(repair["origin_main"])
        exact_facts = facts(
            branch=repair["branch"],
            origin_main=repair["origin_main"],
            ahead=1,
            behind=0,
            changed_paths=repair["allowed_surfaces"],
        )
        self.assertTrue(
            _exact_implementation_release_preflight_repair_matches(
                candidate, exact_facts, repair["package"]
            )
        )
        errors, warnings = self._evaluate_activation(
            candidate, exact_facts, require_clean=True, origin=origin,
            candidate_baseline=baseline, origin_baseline=baseline,
        )
        self.assertEqual([], errors)
        self.assertTrue(
            any("implementation-release" in warning for warning in warnings)
        )
        self.assertEqual(
            origin["operating_mode"], candidate["operating_mode"]
        )
        self.assertEqual(origin["active_lanes"], candidate["active_lanes"])

        forged = copy.deepcopy(candidate)
        forged["implementation_release_preflight_repair"][
            "origin_main"
        ] = "0" * 40
        forged_errors, _ = self._evaluate_activation(
            forged, exact_facts, require_clean=True, origin=origin,
            candidate_baseline=baseline, origin_baseline=baseline,
        )
        self.assertTrue(forged_errors)

    def test_profile_core_merge_repair_is_exact_and_grants_nothing(self):
        repair = PROFILE_CORE_MERGE_PREFLIGHT_REPAIR
        origin, _ = self._profile_core_origin()
        candidate = copy.deepcopy(origin)
        candidate["updated_at"] = "2026-08-13T02:15:00Z"
        candidate["profile_core_merge_preflight_repair"] = copy.deepcopy(repair)
        baseline = load_baseline_bytes_at_ref(repair["origin_main"])
        exact_facts = facts(
            branch=repair["branch"],
            origin_main=repair["origin_main"],
            ahead=1,
            behind=0,
            changed_paths=repair["allowed_surfaces"],
        )
        self.assertTrue(
            _exact_profile_core_merge_preflight_repair_matches(
                candidate, exact_facts, repair["package"]
            )
        )
        errors, warnings = self._evaluate_activation(
            candidate,
            exact_facts,
            require_clean=True,
            origin=origin,
            candidate_baseline=baseline,
            origin_baseline=baseline,
        )
        self.assertEqual([], errors)
        self.assertTrue(any("Profile Core merge-preflight" in item for item in warnings))
        self.assertEqual(origin["operating_mode"], candidate["operating_mode"])
        self.assertEqual(origin["active_lanes"], candidate["active_lanes"])
        self.assertEqual([], candidate["operating_mode"]["merge_allowed_for"])

        for label, mutate, altered_facts in (
            (
                "wrong-reviewed-sha",
                lambda value: value["candidate_contract"].__setitem__(
                    "reviewed_remote_sha", "0" * 40
                ),
                exact_facts,
            ),
            (
                "wrong-owner-digest",
                lambda value: value["candidate_contract"].__setitem__(
                    "owner_decision_sha256", "0" * 64
                ),
                exact_facts,
            ),
            (
                "wrong-control-path",
                lambda _value: None,
                {**exact_facts, "changed_paths": ["app.py"]},
            ),
        ):
            with self.subTest(label=label):
                forged = copy.deepcopy(candidate)
                mutate(forged["profile_core_merge_preflight_repair"])
                forged_errors, _ = self._evaluate_activation(
                    forged,
                    altered_facts,
                    require_clean=True,
                    origin=origin,
                    candidate_baseline=baseline,
                    origin_baseline=baseline,
                )
                self.assertTrue(forged_errors)

    def _shell_repair_fixture(self):
        """Origin at the pinned base plus the exact validated candidate."""
        repair = SHELL_MERGE_PREFLIGHT_REPAIR
        origin = load_ledger_at_ref(repair["origin_main"])
        self.assertNotIn("shell_merge_preflight_repair", origin)
        candidate = copy.deepcopy(origin)
        candidate["updated_at"] = "2026-08-13T08:31:00Z"
        candidate["shell_merge_preflight_repair"] = copy.deepcopy(repair)
        shell_lanes = [
            lane
            for lane in candidate["active_lanes"]
            if lane.get("package") == SHELL_PACKAGE
        ]
        self.assertEqual(1, len(shell_lanes))
        self.assertIs(True, shell_lanes[0]["production_capable"])
        shell_lanes[0]["production_capable"] = False
        baseline = load_baseline_bytes_at_ref(repair["origin_main"])
        exact_facts = facts(
            branch=repair["branch"],
            origin_main=repair["origin_main"],
            ahead=1,
            behind=0,
            changed_paths=repair["allowed_surfaces"],
        )
        return repair, origin, candidate, baseline, exact_facts

    def _interview_ai_d13_fixture(self):
        repair = INTERVIEW_AI_D13_ADMISSION_REPAIR
        origin = load_ledger_at_ref(repair["origin_main"])
        self.assertNotIn("interview_ai_d13_admission_repair", origin)
        candidate = copy.deepcopy(origin)
        candidate["updated_at"] = "2026-08-16T21:20:00Z"
        candidate["interview_ai_d13_admission_repair"] = copy.deepcopy(repair)
        reconciled = next(
            copy.deepcopy(lane)
            for lane in self.ledger["active_lanes"]
            if lane.get("package") == INTERVIEW_AI_ARCHITECTURE_PACKAGE
        )
        if reconciled.get("owner_decisions", [])[-1:] == [
            INTERVIEW_AI_D13_OWNER_DECISION
        ]:
            reconciled["owner_decisions"].pop()
        reconciled.pop("merge_grant", None)
        self.assertEqual(
            INTERVIEW_AI_RECONCILED_LANE_SHA256,
            _canonical_sha256(reconciled),
        )
        lane_index = next(
            index
            for index, lane in enumerate(candidate["active_lanes"])
            if lane.get("package") == INTERVIEW_AI_ARCHITECTURE_PACKAGE
        )
        candidate["active_lanes"][lane_index] = copy.deepcopy(reconciled)
        baseline = load_baseline_bytes_at_ref(repair["origin_main"])
        exact_facts = facts(
            branch=repair["branch"],
            origin_main=repair["origin_main"],
            ahead=1,
            behind=0,
            changed_paths=repair["allowed_surfaces"],
        )
        return repair, origin, candidate, baseline, exact_facts

    def test_interview_ai_d13_admission_is_exact_and_authority_neutral(self):
        repair, origin, candidate, baseline, exact_facts = (
            self._interview_ai_d13_fixture()
        )
        self.assertTrue(
            _exact_interview_ai_d13_admission_repair_matches(
                candidate, exact_facts, repair["package"]
            )
        )
        self.assertTrue(
            _exact_interview_ai_d13_admission_repair_delta(origin, candidate)
        )
        errors, warnings = self._evaluate_activation(
            candidate,
            exact_facts,
            require_clean=True,
            origin=origin,
            candidate_baseline=baseline,
            origin_baseline=baseline,
        )
        self.assertEqual([], errors)
        self.assertTrue(any("Interview AI D13" in item for item in warnings))
        self.assertEqual(origin["operating_mode"], candidate["operating_mode"])
        self.assertEqual([], candidate["operating_mode"]["merge_allowed_for"])
        self.assertEqual([], candidate["operating_mode"]["release_allowed_for"])
        portable_before = next(
            lane
            for lane in origin["active_lanes"]
            if lane.get("package") == "PS-PORTABLE-SESSION-MANAGER-002"
        )
        portable_after = next(
            lane
            for lane in candidate["active_lanes"]
            if lane.get("package") == "PS-PORTABLE-SESSION-MANAGER-002"
        )
        self.assertEqual(portable_before, portable_after)
        target = next(
            lane
            for lane in candidate["active_lanes"]
            if lane.get("package") == INTERVIEW_AI_ARCHITECTURE_PACKAGE
        )
        self.assertNotIn("merge_grant", target)
        self.assertIn("retain Compare", target["owner_decisions"][-1]["decision"])
        self.assertIn(
            "never treat it as code or deployment rollback",
            target["owner_decisions"][-1]["decision"],
        )
        self.assertIn(
            "member choose the specialist",
            target["owner_decisions"][-1]["decision"],
        )
        self.assertEqual(
            repair, self.ledger["interview_ai_d13_admission_repair"]
        )

    def test_interview_ai_d13_admission_mutations_fail_closed(self):
        repair, origin, candidate, baseline, exact_facts = (
            self._interview_ai_d13_fixture()
        )
        cases = (
            ("branch", None, {**exact_facts, "branch": "work/wrong"}, baseline),
            ("base", None, {**exact_facts, "origin_main": "0" * 40}, baseline),
            ("ahead", None, {**exact_facts, "ahead": 2}, baseline),
            ("behind", None, {**exact_facts, "behind": 1}, baseline),
            ("paths", None, {**exact_facts, "changed_paths": ["app.py"]}, baseline),
            (
                "record",
                lambda value: value["interview_ai_d13_admission_repair"].__setitem__(
                    "reason", "forged"
                ),
                exact_facts,
                baseline,
            ),
            (
                "merge-authority",
                lambda value: value["operating_mode"]["merge_allowed_for"].append(
                    INTERVIEW_AI_ARCHITECTURE_PACKAGE
                ),
                exact_facts,
                baseline,
            ),
            (
                "portable",
                lambda value: next(
                    lane
                    for lane in value["active_lanes"]
                    if lane.get("package") == "PS-PORTABLE-SESSION-MANAGER-002"
                ).__setitem__("writer", "forged"),
                exact_facts,
                baseline,
            ),
            (
                "target-grant",
                lambda value: next(
                    lane
                    for lane in value["active_lanes"]
                    if lane.get("package") == INTERVIEW_AI_ARCHITECTURE_PACKAGE
                ).__setitem__("merge_grant", {}),
                exact_facts,
                baseline,
            ),
            ("baseline", None, exact_facts, baseline + b"\nforged"),
        )
        for label, mutate, altered_facts, candidate_baseline in cases:
            with self.subTest(label=label):
                forged = copy.deepcopy(candidate)
                if mutate:
                    mutate(forged)
                errors, _ = self._evaluate_activation(
                    forged,
                    altered_facts,
                    require_clean=True,
                    origin=origin,
                    candidate_baseline=candidate_baseline,
                    origin_baseline=baseline,
                )
                self.assertTrue(errors)

        replay_origin = copy.deepcopy(candidate)
        replay = copy.deepcopy(candidate)
        replay["updated_at"] = "2026-08-16T21:21:00Z"
        replay_errors, _ = self._evaluate_activation(
            replay,
            exact_facts,
            require_clean=True,
            origin=replay_origin,
            candidate_baseline=baseline,
            origin_baseline=baseline,
        )
        self.assertTrue(
            any("one-time and already recorded" in item for item in replay_errors)
        )

    def _interview_ai_relocation_facts(self, *, relocated=False):
        changed_paths = (
            sorted(INTERVIEW_AI_TARGET_PATHS | {INTERVIEW_AI_REGISTRY_PATH})
            if relocated
            else sorted(INTERVIEW_AI_SOURCE_PATHS)
        )
        return facts(
            branch=INTERVIEW_AI_ARCHITECTURE_BRANCH,
            ahead=1,
            behind=0,
            changed_paths=changed_paths,
            interview_ai_source_sha=INTERVIEW_AI_SOURCE_SHA,
            interview_ai_source_parent=INTERVIEW_AI_D13_ADMISSION_REPAIR[
                "origin_main"
            ],
            interview_ai_source_reference_tree=INTERVIEW_AI_SOURCE_TREE,
            interview_ai_origin_main_is_ancestor=True,
            interview_ai_origin_main_has_exact_admission=True,
            interview_ai_ledger_matches_origin_main=True,
            interview_ai_relocation_phase=(
                "relocated" if relocated else "source_ready"
            ),
            interview_ai_source_tree=("" if relocated else INTERVIEW_AI_SOURCE_TREE),
            interview_ai_target_tree=("candidate-tree" if relocated else ""),
            interview_ai_target_files=(
                sorted(INTERVIEW_AI_TARGET_PATHS) if relocated else []
            ),
            interview_ai_target_files_regular=relocated,
            interview_ai_registry_sha256=(
                INTERVIEW_AI_RELOCATED_REGISTRY_SHA256
                if relocated
                else INTERVIEW_AI_BASE_REGISTRY_SHA256
            ),
        )

    def _interview_ai_d13_attestation_fixture(self):
        origin = load_ledger_at_ref(INTERVIEW_AI_D13_ATTESTATION_BASE)
        candidate = load_ledger_at_ref(INTERVIEW_AI_D13_LIFECYCLE_FIXTURE_BASE)
        baseline = load_baseline_bytes_at_ref(INTERVIEW_AI_D13_ATTESTATION_BASE)
        exact_facts = facts(
            branch=INTERVIEW_AI_D13_ATTESTATION_BRANCH,
            origin_main=INTERVIEW_AI_D13_ATTESTATION_BASE,
            ahead=1,
            behind=0,
            changed_paths=sorted(INTERVIEW_AI_D13_ATTESTATION_PATHS),
        )
        return origin, candidate, baseline, exact_facts

    def test_interview_ai_d13_lifecycle_fixture_followup_is_exact_and_inert(self):
        origin = load_ledger_at_ref(INTERVIEW_AI_D13_LIFECYCLE_FIXTURE_BASE)
        candidate = copy.deepcopy(origin)
        candidate["updated_at"] = "2026-08-16T23:20:24Z"
        candidate["interview_ai_d13_lifecycle_fixture_followup"] = copy.deepcopy(
            INTERVIEW_AI_D13_LIFECYCLE_FIXTURE_FOLLOWUP
        )
        baseline = load_baseline_bytes_at_ref(
            INTERVIEW_AI_D13_LIFECYCLE_FIXTURE_BASE
        )
        exact_facts = facts(
            branch=INTERVIEW_AI_D13_LIFECYCLE_FIXTURE_FOLLOWUP["branch"],
            origin_main=INTERVIEW_AI_D13_LIFECYCLE_FIXTURE_BASE,
            ahead=1,
            behind=0,
            changed_paths=sorted(INTERVIEW_AI_D13_LIFECYCLE_FIXTURE_PATHS),
        )
        self.assertTrue(
            _exact_interview_ai_d13_lifecycle_fixture_followup_matches(
                candidate, exact_facts, "PS-DELIVERY-CONTROL-001"
            )
        )
        self.assertTrue(
            _exact_interview_ai_d13_lifecycle_fixture_followup_delta(
                origin, candidate
            )
        )
        errors, warnings = self._evaluate_activation(
            candidate,
            exact_facts,
            require_clean=True,
            origin=origin,
            candidate_baseline=baseline,
            origin_baseline=baseline,
        )
        self.assertEqual([], errors)
        self.assertTrue(any("lifecycle-fixture" in item for item in warnings))
        self.assertEqual(origin["operating_mode"], candidate["operating_mode"])
        self.assertEqual(origin["active_lanes"], candidate["active_lanes"])

        forged = copy.deepcopy(candidate)
        forged["operating_mode"]["merge_allowed_for"].append(
            INTERVIEW_AI_ARCHITECTURE_PACKAGE
        )
        forged_errors, _ = self._evaluate_activation(
            forged,
            exact_facts,
            require_clean=True,
            origin=origin,
            candidate_baseline=baseline,
            origin_baseline=baseline,
        )
        self.assertTrue(forged_errors)

    def test_interview_ai_d13_attestation_is_exact_inert_and_grant_ready(self):
        origin, candidate, baseline, exact_facts = (
            self._interview_ai_d13_attestation_fixture()
        )
        self.assertTrue(
            _exact_interview_ai_d13_attestation_registration_matches(
                candidate, exact_facts, "PS-DELIVERY-CONTROL-001"
            )
        )
        self.assertTrue(
            _exact_interview_ai_d13_attestation_registration_delta(
                origin, candidate
            )
        )
        errors, warnings = self._evaluate_activation(
            candidate,
            exact_facts,
            require_clean=True,
            origin=origin,
            candidate_baseline=baseline,
            origin_baseline=baseline,
        )
        self.assertEqual([], errors)
        self.assertTrue(any("review-attestation" in item for item in warnings))
        self.assertEqual(origin["operating_mode"], candidate["operating_mode"])
        portable_before = next(
            lane for lane in origin["active_lanes"]
            if lane.get("package") == "PS-PORTABLE-SESSION-MANAGER-002"
        )
        portable_after = next(
            lane for lane in candidate["active_lanes"]
            if lane.get("package") == "PS-PORTABLE-SESSION-MANAGER-002"
        )
        self.assertEqual(portable_before, portable_after)

        lane = next(
            copy.deepcopy(item) for item in candidate["active_lanes"]
            if item.get("package") == INTERVIEW_AI_ARCHITECTURE_PACKAGE
        )
        self.assertEqual(INTERVIEW_AI_D13_OWNER_DECISION, lane["owner_decisions"][-1])
        index = len(lane["owner_decisions"]) - 1
        lane["merge_grant"] = {
            "authorized_by": "Pete",
            "authority_decision_index": index,
            "authority_decision_sha256": INTERVIEW_AI_D13_OWNER_DECISION_SHA256,
            "independent_review": copy.deepcopy(
                INTERVIEW_AI_D13_REVIEW_ATTESTATION
            ),
            "reviewed_remote_sha": INTERVIEW_AI_D13_REVIEWED_SHA,
            "granted_at": "2026-08-16T23:00:00Z",
            "review_result": "pass",
            "review_evidence_paths": [
                INTERVIEW_AI_D13_REVIEW_ATTESTATION["evidence_path"]
            ],
        }
        grant_errors = []
        self.assertIsNotNone(_direction_merge_grant(lane, "Interview", grant_errors))
        self.assertEqual([], grant_errors)

    def test_interview_ai_d13_attestation_mutations_fail_closed(self):
        origin, candidate, baseline, exact_facts = (
            self._interview_ai_d13_attestation_fixture()
        )
        for label, mutation in (
            (
                "record",
                lambda value: value[
                    "interview_ai_d13_attestation_registration"
                ]["candidate_contract"].__setitem__(
                    "reviewed_remote_sha", "0" * 40
                ),
            ),
            (
                "decision",
                lambda value: next(
                    lane for lane in value["active_lanes"]
                    if lane.get("package") == INTERVIEW_AI_ARCHITECTURE_PACKAGE
                )["owner_decisions"][-1].__setitem__("conditions", "forged"),
            ),
            (
                "authority",
                lambda value: value["operating_mode"][
                    "merge_allowed_for"
                ].append(INTERVIEW_AI_ARCHITECTURE_PACKAGE),
            ),
        ):
            with self.subTest(label=label):
                forged = copy.deepcopy(candidate)
                mutation(forged)
                errors, _ = self._evaluate_activation(
                    forged,
                    exact_facts,
                    require_clean=True,
                    origin=origin,
                    candidate_baseline=baseline,
                    origin_baseline=baseline,
                )
                self.assertTrue(errors)

        lane = next(
            copy.deepcopy(item) for item in candidate["active_lanes"]
            if item.get("package") == INTERVIEW_AI_ARCHITECTURE_PACKAGE
        )
        lane["merge_grant"] = {
            "authorized_by": "Pete",
            "authority_decision_index": len(lane["owner_decisions"]) - 1,
            "authority_decision_sha256": INTERVIEW_AI_D13_OWNER_DECISION_SHA256,
            "independent_review": copy.deepcopy(
                INTERVIEW_AI_D13_REVIEW_ATTESTATION
            ),
            "reviewed_remote_sha": INTERVIEW_AI_D13_REVIEWED_SHA,
            "granted_at": "2026-08-16T23:00:00Z",
            "review_result": "pass",
            "review_evidence_paths": [
                INTERVIEW_AI_D13_REVIEW_ATTESTATION["evidence_path"]
            ],
        }
        lane["merge_grant"]["independent_review"]["verdict"] = "PASS"
        forged_errors = []
        _direction_merge_grant(lane, "Interview", forged_errors)
        self.assertTrue(
            any("code-controlled attestation" in item for item in forged_errors)
        )

    def test_interview_ai_relocation_write_is_exact_and_fail_closed(self):
        _, _, candidate, _, _ = self._interview_ai_d13_fixture()
        for relocated in (False, True):
            with self.subTest(phase="relocated" if relocated else "source_ready"):
                exact_facts = self._interview_ai_relocation_facts(
                    relocated=relocated
                )
                self.assertTrue(
                    _exact_interview_ai_relocation_write(
                        candidate,
                        exact_facts,
                        INTERVIEW_AI_ARCHITECTURE_PACKAGE,
                    )
                )
                errors, warnings = evaluate_policy(
                    candidate,
                    exact_facts,
                    INTERVIEW_AI_ARCHITECTURE_PACKAGE,
                    "write",
                    require_clean=True,
                )
                self.assertEqual([], errors)
                self.assertTrue(any("D13 relocation" in item for item in warnings))

        exact_relocated = self._interview_ai_relocation_facts(relocated=True)
        for label, mutate_ledger, altered_facts in (
            (
                "record",
                lambda value: value["interview_ai_d13_admission_repair"].__setitem__(
                    "reason", "forged"
                ),
                exact_relocated,
            ),
            (
                "branch",
                None,
                {**exact_relocated, "branch": "work/wrong"},
            ),
            (
                "source-reference",
                None,
                {**exact_relocated, "interview_ai_source_reference_tree": "0" * 40},
            ),
            (
                "main-lineage",
                None,
                {**exact_relocated, "interview_ai_origin_main_is_ancestor": False},
            ),
            (
                "target-file",
                None,
                {
                    **exact_relocated,
                    "interview_ai_target_files": sorted(INTERVIEW_AI_TARGET_PATHS)[:-1],
                },
            ),
            (
                "registry",
                None,
                {**exact_relocated, "interview_ai_registry_sha256": "0" * 64},
            ),
            (
                "unrelated-path",
                None,
                {
                    **exact_relocated,
                    "changed_paths": exact_relocated["changed_paths"] + ["app.py"],
                },
            ),
        ):
            with self.subTest(label=label):
                forged = copy.deepcopy(candidate)
                if mutate_ledger:
                    mutate_ledger(forged)
                self.assertFalse(
                    _exact_interview_ai_relocation_write(
                        forged,
                        altered_facts,
                        INTERVIEW_AI_ARCHITECTURE_PACKAGE,
                    )
                )
                errors, _ = evaluate_policy(
                    forged,
                    altered_facts,
                    INTERVIEW_AI_ARCHITECTURE_PACKAGE,
                    "write",
                    require_clean=True,
                )
                self.assertTrue(errors)

    def test_shell_merge_repair_is_exact_and_grants_nothing(self):
        repair, origin, candidate, baseline, exact_facts = (
            self._shell_repair_fixture()
        )
        self.assertTrue(
            _exact_shell_merge_preflight_repair_matches(
                candidate, exact_facts, repair["package"]
            )
        )
        self.assertTrue(
            _exact_shell_merge_preflight_repair_delta(origin, candidate)
        )
        errors, warnings = self._evaluate_activation(
            candidate,
            exact_facts,
            require_clean=True,
            origin=origin,
            candidate_baseline=baseline,
            origin_baseline=baseline,
        )
        self.assertEqual([], errors)
        self.assertTrue(
            any("Shell merge-preflight" in item for item in warnings)
        )
        # The repair opens the merge gate only: it hands out no merge, release,
        # cleanup, or write authority, and it moves no other lane.
        self.assertEqual(origin["operating_mode"], candidate["operating_mode"])
        self.assertEqual([], candidate["operating_mode"]["merge_allowed_for"])
        self.assertEqual([], candidate["operating_mode"]["release_allowed_for"])
        self.assertEqual(
            [lane["package"] for lane in origin["active_lanes"]],
            [lane["package"] for lane in candidate["active_lanes"]],
        )
        for before, after in zip(
            origin["active_lanes"], candidate["active_lanes"], strict=True
        ):
            expected = dict(before)
            if before["package"] == SHELL_PACKAGE:
                expected["production_capable"] = False
            self.assertEqual(expected, after)
        # PR 444's PS-CONNECT-002 merge-admission record is carried untouched.
        self.assertEqual(
            origin.get("connect_002_merge_admission_repair"),
            candidate.get("connect_002_merge_admission_repair"),
        )
        # The checked-in ledger carries the validator's exact record.
        self.assertEqual(
            SHELL_MERGE_PREFLIGHT_REPAIR,
            self.ledger.get("shell_merge_preflight_repair"),
        )

    def test_shell_merge_repair_refuses_wrong_branch_base_or_record(self):
        repair, origin, candidate, baseline, exact_facts = (
            self._shell_repair_fixture()
        )
        for label, forge, altered_facts in (
            # A later branch cannot reuse the exception.
            (
                "different-branch",
                lambda ledger: None,
                {
                    **exact_facts,
                    "branch": (
                        "work/2026-08-14-delivery-activation-shell-merge-"
                        "preflight-repair-v2"
                    ),
                },
            ),
            # A different base cannot reuse the exception.
            (
                "different-base",
                lambda ledger: None,
                {**exact_facts, "origin_main": "0" * 40},
            ),
            # The superseded base cannot reuse it either.
            (
                "stale-base",
                lambda ledger: None,
                {
                    **exact_facts,
                    "origin_main": "68d14a44de4007f8643396833a481601d5dbb4a3",
                },
            ),
            # Any edit to the record breaks the hard-coded equality.
            (
                "altered-reason",
                lambda ledger: ledger["shell_merge_preflight_repair"].__setitem__(
                    "reason", "shortened"
                ),
                exact_facts,
            ),
            (
                "altered-corrected-lane",
                lambda ledger: ledger["shell_merge_preflight_repair"][
                    "corrected_lane"
                ].__setitem__("to", True),
                exact_facts,
            ),
            (
                "altered-allowed-surfaces",
                lambda ledger: ledger["shell_merge_preflight_repair"].__setitem__(
                    "allowed_surfaces", ["app.py"]
                ),
                exact_facts,
            ),
            (
                "altered-origin-main",
                lambda ledger: ledger["shell_merge_preflight_repair"].__setitem__(
                    "origin_main", "68d14a44de4007f8643396833a481601d5dbb4a3"
                ),
                exact_facts,
            ),
            # The three-path control boundary holds.
            (
                "non-control-path",
                lambda ledger: None,
                {**exact_facts, "changed_paths": ["app.py"]},
            ),
        ):
            with self.subTest(label=label):
                forged = copy.deepcopy(candidate)
                forge(forged)
                self.assertFalse(
                    _exact_shell_merge_preflight_repair_matches(
                        forged, altered_facts, repair["package"]
                    )
                )
                forged_errors, _ = self._evaluate_activation(
                    forged,
                    altered_facts,
                    require_clean=True,
                    origin=origin,
                    candidate_baseline=baseline,
                    origin_baseline=baseline,
                )
                self.assertTrue(forged_errors)

    def test_shell_merge_repair_refuses_any_wider_ledger_delta(self):
        """The only tolerated lane edit is the one pinned production_capable."""
        repair, origin, candidate, baseline, exact_facts = (
            self._shell_repair_fixture()
        )

        def shell_lane(ledger):
            return next(
                lane
                for lane in ledger["active_lanes"]
                if lane.get("package") == SHELL_PACKAGE
            )

        def other_lane(ledger):
            return next(
                lane
                for lane in ledger["active_lanes"]
                if lane.get("package") != SHELL_PACKAGE
            )

        for label, forge in (
            # Smuggling merge authority alongside the correction.
            (
                "grants-merge",
                lambda ledger: ledger["operating_mode"]["merge_allowed_for"].append(
                    SHELL_PACKAGE
                ),
            ),
            # Smuggling release authority alongside the correction.
            (
                "grants-release",
                lambda ledger: ledger["operating_mode"][
                    "release_allowed_for"
                ].append(SHELL_PACKAGE),
            ),
            # A second field on the corrected lane.
            (
                "widens-surfaces",
                lambda ledger: shell_lane(ledger)["writable_surfaces"].append(
                    "app.py"
                ),
            ),
            (
                "changes-branch",
                lambda ledger: shell_lane(ledger).__setitem__(
                    "branch", "work/2026-08-13-shell-elsewhere"
                ),
            ),
            (
                "adds-merge-grant",
                lambda ledger: shell_lane(ledger).__setitem__("merge_grant", {}),
            ),
            (
                "drops-an-exclusion",
                lambda ledger: shell_lane(ledger)["exclusions"].pop(),
            ),
            # Any other lane, including PS-CONNECT-002.
            (
                "touches-another-lane",
                lambda ledger: other_lane(ledger).__setitem__(
                    "production_capable", True
                ),
            ),
            # PR 444's record must survive untouched.
            (
                "drops-connect-002-record",
                lambda ledger: ledger.pop("connect_002_merge_admission_repair"),
            ),
            # Capacity and policy stay frozen.
            (
                "raises-capacity",
                lambda ledger: ledger["activation_policy"].__setitem__(
                    "max_production_capable_lanes", 2
                ),
            ),
        ):
            with self.subTest(label=label):
                forged = copy.deepcopy(candidate)
                forge(forged)
                self.assertFalse(
                    _exact_shell_merge_preflight_repair_delta(origin, forged)
                )
                forged_errors, _ = self._evaluate_activation(
                    forged,
                    exact_facts,
                    require_clean=True,
                    origin=origin,
                    candidate_baseline=baseline,
                    origin_baseline=baseline,
                )
                self.assertTrue(forged_errors)

    def test_shell_merge_repair_is_one_time_only(self):
        repair, origin, candidate, baseline, exact_facts = (
            self._shell_repair_fixture()
        )
        # Replaying it against an origin that already carries it must refuse:
        # the parent pre-state no longer matches and the record already exists.
        replayed_origin = copy.deepcopy(candidate)
        self.assertFalse(
            _exact_shell_merge_preflight_repair_delta(replayed_origin, candidate)
        )
        replay = copy.deepcopy(candidate)
        replay["updated_at"] = "2026-08-13T09:00:00Z"
        errors, _ = self._evaluate_activation(
            replay,
            exact_facts,
            require_clean=True,
            origin=replayed_origin,
            candidate_baseline=baseline,
            origin_baseline=baseline,
        )
        self.assertTrue(
            any("one-time and already recorded" in item for item in errors)
        )

    def test_shell_grant_still_refuses_a_production_capable_lane(self):
        """The load-bearing refusal: merge must not be able to deploy.

        The exception is pinned to production_capable false, so a
        shared_foundation lane that still holds the production slot is refused a
        merge grant outright.  Merging the shell therefore cannot also release
        it; reclaiming a production slot stays a separate, deliberate step.
        """
        _, origin, _, _, _ = self._shell_repair_fixture()
        corrected = copy.deepcopy(
            next(
                lane
                for lane in origin["active_lanes"]
                if lane.get("package") == SHELL_PACKAGE
            )
        )
        corrected["production_capable"] = False
        self.assertTrue(_is_shell_reviewed_shared_foundation_lane(corrected))

        production_capable = copy.deepcopy(corrected)
        production_capable["production_capable"] = True
        self.assertFalse(
            _is_shell_reviewed_shared_foundation_lane(production_capable)
        )
        errors: list[str] = []
        _direction_merge_grant(production_capable, "grant target", errors)
        self.assertTrue(
            any("requires production_capable false" in item for item in errors)
        )
        self.assertTrue(
            any(
                "available only to direction_authority lanes" in item
                for item in errors
            )
        )

    def test_shell_lane_predicate_is_pinned_to_one_exact_lane(self):
        _, origin, _, _, _ = self._shell_repair_fixture()
        corrected = copy.deepcopy(
            next(
                lane
                for lane in origin["active_lanes"]
                if lane.get("package") == SHELL_PACKAGE
            )
        )
        corrected["production_capable"] = False
        self.assertTrue(_is_shell_reviewed_shared_foundation_lane(corrected))
        self.assertEqual(SHELL_BRANCH, corrected["branch"])
        self.assertEqual(SHELL_LANE_CLASS, corrected["lane_class"])
        self.assertEqual(SHELL_DELIVERY_PATH, corrected["delivery_path"])

        for field, value in (
            ("package", "PS-SHELL-002"),
            ("branch", "work/2026-08-14-shell-editorial-top-bar-002"),
            ("lane_class", "implementation"),
            ("delivery_path", "Bounded"),
            ("production_capable", True),
        ):
            with self.subTest(field=field):
                impostor = copy.deepcopy(corrected)
                impostor[field] = value
                self.assertFalse(
                    _is_shell_reviewed_shared_foundation_lane(impostor)
                )
                grant_errors: list[str] = []
                _direction_merge_grant(impostor, "grant target", grant_errors)
                self.assertTrue(grant_errors)
        for non_lane in (None, "PS-SHELL-001", [], 0):
            self.assertFalse(_is_shell_reviewed_shared_foundation_lane(non_lane))
        # The shell predicate must not widen any neighbouring exception.
        self.assertFalse(
            _is_profile_core_reviewed_implementation_lane(corrected)
        )
        self.assertFalse(_is_connect_002_reviewed_implementation_lane(corrected))

    def test_shell_repair_control_paths_are_the_three_control_surfaces(self):
        self.assertEqual(
            {
                "docs/governance/CURRENT_LANES.json",
                "scripts/delivery_preflight.py",
                "tests/test_delivery_preflight.py",
            },
            set(SHELL_MERGE_CONTROL_PATHS),
        )
        self.assertEqual(
            "PS-DELIVERY-CONTROL-001", SHELL_MERGE_PREFLIGHT_REPAIR["package"]
        )
        self.assertEqual(
            "one_time_owner_authorized_repair",
            SHELL_MERGE_PREFLIGHT_REPAIR["status"],
        )
        correction = SHELL_MERGE_PREFLIGHT_REPAIR["corrected_lane"]
        self.assertEqual(SHELL_PACKAGE, correction["package"])
        self.assertEqual("production_capable", correction["field"])
        self.assertIs(True, correction["from"])
        self.assertIs(False, correction["to"])

    def test_profile_core_grant_fixture_followup_is_exact_and_inert(self):
        repair = PROFILE_CORE_MERGE_PREFLIGHT_REPAIR
        followup = PROFILE_CORE_GRANT_FIXTURE_FOLLOWUP
        origin = load_ledger_at_ref(followup["origin_main"])
        self.assertEqual(
            repair, origin.get("profile_core_merge_preflight_repair")
        )
        self.assertNotIn("profile_core_grant_fixture_followup", origin)
        candidate = copy.deepcopy(origin)
        candidate["updated_at"] = "2026-08-13T03:36:53Z"
        candidate["profile_core_grant_fixture_followup"] = copy.deepcopy(
            followup
        )
        baseline = load_baseline_bytes_at_ref(followup["origin_main"])
        exact_facts = facts(
            branch=followup["branch"],
            origin_main=followup["origin_main"],
            ahead=1,
            behind=0,
            changed_paths=followup["allowed_surfaces"],
        )
        self.assertTrue(
            _exact_profile_core_grant_fixture_followup_matches(
                candidate, exact_facts, followup["package"]
            )
        )
        self.assertTrue(
            _exact_profile_core_grant_fixture_followup_delta(origin, candidate)
        )
        errors, warnings = self._evaluate_activation(
            candidate,
            exact_facts,
            require_clean=True,
            origin=origin,
            candidate_baseline=baseline,
            origin_baseline=baseline,
        )
        self.assertEqual([], errors)
        self.assertTrue(
            any("Profile Core grant-fixture" in item for item in warnings)
        )
        self.assertEqual(origin["operating_mode"], candidate["operating_mode"])
        self.assertEqual(origin["active_lanes"], candidate["active_lanes"])
        self.assertEqual([], candidate["operating_mode"]["merge_allowed_for"])
        self.assertEqual([], candidate["operating_mode"]["release_allowed_for"])

        for label, mutate, altered_facts in (
            (
                "wrong-origin",
                lambda _value: None,
                {**exact_facts, "origin_main": "0" * 40},
            ),
            (
                "wrong-path",
                lambda _value: None,
                {**exact_facts, "changed_paths": ["app.py"]},
            ),
            (
                "forged-record",
                lambda value: value.__setitem__("origin_main", "0" * 40),
                exact_facts,
            ),
            (
                "authority-smuggling",
                lambda _value: candidate["operating_mode"][
                    "merge_allowed_for"
                ].append(PROFILE_CORE_INTEGRATION_PACKAGE),
                exact_facts,
            ),
        ):
            with self.subTest(label=label):
                forged = copy.deepcopy(candidate)
                if label == "authority-smuggling":
                    forged["operating_mode"]["merge_allowed_for"].append(
                        PROFILE_CORE_INTEGRATION_PACKAGE
                    )
                else:
                    mutate(forged["profile_core_grant_fixture_followup"])
                forged_errors, _ = self._evaluate_activation(
                    forged,
                    altered_facts,
                    require_clean=True,
                    origin=origin,
                    candidate_baseline=baseline,
                    origin_baseline=baseline,
                )
                self.assertTrue(forged_errors)

    def test_profile_core_grant_anchor_followup_is_exact_and_inert(self):
        followup = PROFILE_CORE_GRANT_ANCHOR_FOLLOWUP
        origin = load_ledger_at_ref(followup["origin_main"])
        self.assertEqual(
            PROFILE_CORE_MERGE_PREFLIGHT_REPAIR,
            origin.get("profile_core_merge_preflight_repair"),
        )
        self.assertEqual(
            PROFILE_CORE_GRANT_FIXTURE_FOLLOWUP,
            origin.get("profile_core_grant_fixture_followup"),
        )
        self.assertNotIn("profile_core_grant_anchor_followup", origin)
        candidate = copy.deepcopy(origin)
        candidate["updated_at"] = "2026-08-13T03:56:56Z"
        candidate["profile_core_grant_anchor_followup"] = copy.deepcopy(
            followup
        )
        baseline = load_baseline_bytes_at_ref(followup["origin_main"])
        exact_facts = facts(
            branch=followup["branch"],
            origin_main=followup["origin_main"],
            ahead=1,
            behind=0,
            changed_paths=followup["allowed_surfaces"],
        )
        self.assertTrue(
            _exact_profile_core_grant_anchor_followup_matches(
                candidate, exact_facts, followup["package"]
            )
        )
        self.assertTrue(
            _exact_profile_core_grant_anchor_followup_delta(origin, candidate)
        )
        errors, warnings = self._evaluate_activation(
            candidate,
            exact_facts,
            require_clean=True,
            origin=origin,
            candidate_baseline=baseline,
            origin_baseline=baseline,
        )
        self.assertEqual([], errors)
        self.assertTrue(
            any("Profile Core grant-anchor" in item for item in warnings)
        )
        self.assertEqual(origin["operating_mode"], candidate["operating_mode"])
        self.assertEqual(origin["active_lanes"], candidate["active_lanes"])
        self.assertEqual([], candidate["operating_mode"]["merge_allowed_for"])
        self.assertEqual([], candidate["operating_mode"]["release_allowed_for"])

        forged = copy.deepcopy(candidate)
        forged["operating_mode"]["merge_allowed_for"].append(
            PROFILE_CORE_INTEGRATION_PACKAGE
        )
        forged_errors, _ = self._evaluate_activation(
            forged,
            exact_facts,
            require_clean=True,
            origin=origin,
            candidate_baseline=baseline,
            origin_baseline=baseline,
        )
        self.assertTrue(forged_errors)

    def test_profile_core_post_grant_registry_fixture_repair_is_exact_and_inert(
        self,
    ):
        repair = PROFILE_CORE_POST_GRANT_REGISTRY_FIXTURE_REPAIR
        origin = load_ledger_at_ref(repair["origin_main"])
        self.assertEqual(
            PROFILE_CORE_MERGE_PREFLIGHT_REPAIR,
            origin.get("profile_core_merge_preflight_repair"),
        )
        self.assertEqual(
            PROFILE_CORE_GRANT_FIXTURE_FOLLOWUP,
            origin.get("profile_core_grant_fixture_followup"),
        )
        self.assertEqual(
            PROFILE_CORE_GRANT_ANCHOR_FOLLOWUP,
            origin.get("profile_core_grant_anchor_followup"),
        )
        self.assertNotIn("profile_core_post_grant_registry_fixture_repair", origin)
        candidate = copy.deepcopy(origin)
        candidate["updated_at"] = "2026-08-13T04:21:00Z"
        candidate["profile_core_post_grant_registry_fixture_repair"] = (
            copy.deepcopy(repair)
        )
        baseline = load_baseline_bytes_at_ref(repair["origin_main"])
        exact_facts = facts(
            branch=repair["branch"],
            origin_main=repair["origin_main"],
            ahead=1,
            behind=0,
            changed_paths=repair["allowed_surfaces"],
        )
        self.assertTrue(
            _exact_profile_core_post_grant_registry_fixture_repair_matches(
                candidate, exact_facts, repair["package"]
            )
        )
        self.assertTrue(
            _exact_profile_core_post_grant_registry_fixture_repair_delta(
                origin, candidate
            )
        )
        errors, warnings = self._evaluate_activation(
            candidate,
            exact_facts,
            require_clean=True,
            origin=origin,
            candidate_baseline=baseline,
            origin_baseline=baseline,
        )
        self.assertEqual([], errors)
        self.assertTrue(
            any("post-grant registry-fixture" in item for item in warnings)
        )
        self.assertEqual(origin["operating_mode"], candidate["operating_mode"])
        self.assertEqual(origin["active_lanes"], candidate["active_lanes"])
        self.assertEqual(
            {
                "merge_preflight_repair": PROFILE_CORE_MERGE_REPAIR_MAIN,
                "grant_fixture_followup": PROFILE_CORE_GRANT_FIXTURE_FOLLOWUP_MAIN,
                "grant_anchor_followup": PROFILE_CORE_GRANT_ANCHOR_FOLLOWUP_MAIN,
                "ledger_only_grant": PROFILE_CORE_LEDGER_GRANT_MAIN,
            },
            repair["existing_main_chain"],
        )

        for label, mutate, altered_facts in (
            (
                "wrong-origin",
                lambda _value: None,
                {**exact_facts, "origin_main": "0" * 40},
            ),
            (
                "ahead-zero",
                lambda _value: None,
                {**exact_facts, "ahead": 0},
            ),
            (
                "ahead-two",
                lambda _value: None,
                {**exact_facts, "ahead": 2},
            ),
            (
                "behind-one",
                lambda _value: None,
                {**exact_facts, "behind": 1},
            ),
            (
                "missing-approved-path",
                lambda _value: None,
                {
                    **exact_facts,
                    "changed_paths": repair["allowed_surfaces"][:-1],
                },
            ),
            (
                "extra-unapproved-path",
                lambda _value: None,
                {
                    **exact_facts,
                    "changed_paths": [
                        *repair["allowed_surfaces"],
                        "app.py",
                    ],
                },
            ),
            (
                "forged-chain",
                lambda value: value["existing_main_chain"].__setitem__(
                    "ledger_only_grant", "0" * 40
                ),
                exact_facts,
            ),
        ):
            with self.subTest(label=label):
                forged = copy.deepcopy(candidate)
                mutate(forged["profile_core_post_grant_registry_fixture_repair"])
                forged_errors, _ = self._evaluate_activation(
                    forged,
                    altered_facts,
                    require_clean=True,
                    origin=origin,
                    candidate_baseline=baseline,
                    origin_baseline=baseline,
                )
                self.assertTrue(forged_errors)

        for label, mutate in (
            (
                "authority-smuggling",
                lambda value: value["operating_mode"][
                    "release_allowed_for"
                ].append(PROFILE_CORE_INTEGRATION_PACKAGE),
            ),
            (
                "active-lane-mutation",
                lambda value: next(
                    item
                    for item in value["active_lanes"]
                    if item.get("package") == PROFILE_CORE_INTEGRATION_PACKAGE
                ).__setitem__("branch", "work/forged-profile-core"),
            ),
        ):
            with self.subTest(label=label):
                forged = copy.deepcopy(candidate)
                mutate(forged)
                forged_errors, _ = self._evaluate_activation(
                    forged,
                    exact_facts,
                    require_clean=True,
                    origin=origin,
                    candidate_baseline=baseline,
                    origin_baseline=baseline,
                )
                self.assertTrue(forged_errors)

        for label, updated_at in (
            ("equal-timestamp", origin["updated_at"]),
            ("earlier-timestamp", "2026-08-13T04:12:01Z"),
            ("malformed-timestamp", "not-a-timestamp"),
        ):
            with self.subTest(label=label):
                forged = copy.deepcopy(candidate)
                forged["updated_at"] = updated_at
                forged_errors, _ = self._evaluate_activation(
                    forged,
                    exact_facts,
                    require_clean=True,
                    origin=origin,
                    candidate_baseline=baseline,
                    origin_baseline=baseline,
                )
                self.assertTrue(forged_errors)

        baseline_errors, _ = self._evaluate_activation(
            candidate,
            exact_facts,
            require_clean=True,
            origin=origin,
            candidate_baseline=baseline + b"\nfixture baseline mutation",
            origin_baseline=baseline,
        )
        self.assertTrue(baseline_errors)

        preexisting_origin = copy.deepcopy(origin)
        preexisting_origin["updated_at"] = "2026-08-13T04:21:00Z"
        preexisting_origin["profile_core_post_grant_registry_fixture_repair"] = (
            copy.deepcopy(repair)
        )
        reused = copy.deepcopy(preexisting_origin)
        reused["updated_at"] = "2026-08-13T04:22:00Z"
        preexisting_errors, _ = self._evaluate_activation(
            reused,
            exact_facts,
            require_clean=True,
            origin=preexisting_origin,
            candidate_baseline=baseline,
            origin_baseline=baseline,
        )
        self.assertTrue(preexisting_errors)

    def test_profile_core_grant_and_merge_are_exact_candidate_only(self):
        origin, lane = self._profile_core_origin()
        repaired = copy.deepcopy(origin)
        repaired["updated_at"] = "2026-08-13T02:15:00Z"
        repaired["profile_core_merge_preflight_repair"] = copy.deepcopy(
            PROFILE_CORE_MERGE_PREFLIGHT_REPAIR
        )
        followed = copy.deepcopy(repaired)
        followed["updated_at"] = "2026-08-13T03:36:53Z"
        followed["profile_core_grant_fixture_followup"] = copy.deepcopy(
            PROFILE_CORE_GRANT_FIXTURE_FOLLOWUP
        )
        self.assertTrue(
            _exact_profile_core_grant_fixture_followup_delta(repaired, followed)
        )
        anchored = copy.deepcopy(followed)
        anchored["updated_at"] = "2026-08-13T03:56:56Z"
        anchored["profile_core_grant_anchor_followup"] = copy.deepcopy(
            PROFILE_CORE_GRANT_ANCHOR_FOLLOWUP
        )
        self.assertTrue(
            _exact_profile_core_grant_anchor_followup_delta(followed, anchored)
        )
        candidate = copy.deepcopy(anchored)
        granted_at = "2026-08-13T03:57:30Z"
        candidate_lane = next(
            item
            for item in candidate["active_lanes"]
            if item.get("package") == PROFILE_CORE_INTEGRATION_PACKAGE
        )
        candidate_lane["merge_grant"] = self._profile_core_grant_record(
            candidate_lane, granted_at
        )
        candidate["operating_mode"]["merge_allowed_for"] = [
            *anchored["operating_mode"]["merge_allowed_for"],
            PROFILE_CORE_INTEGRATION_PACKAGE,
        ]
        candidate["updated_at"] = granted_at
        grant_facts = facts(
            branch="work/2026-08-13-delivery-grant-profile-core-exact",
            origin_main="1" * 40,
            ahead=1,
            behind=0,
            changed_paths=["docs/governance/CURRENT_LANES.json"],
            grant_target_remote_sha=PROFILE_CORE_INTEGRATION_REVIEWED_SHA,
            **self._review_evidence_facts(candidate_lane["merge_grant"]),
        )
        errors, _ = evaluate_policy(
            candidate,
            grant_facts,
            PROFILE_CORE_INTEGRATION_PACKAGE,
            "grant",
            require_clean=True,
            origin_ledger=anchored,
            candidate_baseline=self.baseline,
            origin_baseline=self.baseline,
        )
        self.assertEqual([], errors)
        self.assertTrue(
            _exact_direction_grant_delta(
                anchored, candidate, PROFILE_CORE_INTEGRATION_PACKAGE
            )
        )
        self._assert_valid_merge_authorities(candidate)
        self.assertEqual([], candidate["operating_mode"]["release_allowed_for"])

        post_grant = copy.deepcopy(candidate)
        post_grant["updated_at"] = "2026-08-13T04:21:00Z"
        post_grant["profile_core_post_grant_registry_fixture_repair"] = (
            copy.deepcopy(PROFILE_CORE_POST_GRANT_REGISTRY_FIXTURE_REPAIR)
        )
        self.assertTrue(
            _exact_profile_core_post_grant_registry_fixture_repair_delta(
                candidate, post_grant
            )
        )

        wrong_sha = copy.deepcopy(candidate)
        wrong_sha["active_lanes"][0]["merge_grant"]["reviewed_remote_sha"] = "0" * 40
        wrong_sha_errors, _ = evaluate_policy(
            wrong_sha, grant_facts, PROFILE_CORE_INTEGRATION_PACKAGE, "grant",
            require_clean=True, origin_ledger=anchored,
            candidate_baseline=self.baseline, origin_baseline=self.baseline,
        )
        self.assertTrue(any("accepted Profile Core SHA" in item for item in wrong_sha_errors))

        wrong_review = copy.deepcopy(candidate)
        wrong_review["active_lanes"][0]["merge_grant"]["independent_review"][
            "reviewer_task"
        ] = "/root/forged_profile_review"
        wrong_review_errors, _ = evaluate_policy(
            wrong_review, grant_facts, PROFILE_CORE_INTEGRATION_PACKAGE, "grant",
            require_clean=True, origin_ledger=anchored,
            candidate_baseline=self.baseline, origin_baseline=self.baseline,
        )
        self.assertTrue(any("code-controlled attestation" in item for item in wrong_review_errors))

        wrong_digest = copy.deepcopy(candidate)
        wrong_digest["active_lanes"][0]["merge_grant"][
            "authority_decision_sha256"
        ] = "0" * 64
        wrong_digest_errors, _ = evaluate_policy(
            wrong_digest, grant_facts, PROFILE_CORE_INTEGRATION_PACKAGE, "grant",
            require_clean=True, origin_ledger=anchored,
            candidate_baseline=self.baseline, origin_baseline=self.baseline,
        )
        self.assertTrue(any("pinned Profile Core owner" in item for item in wrong_digest_errors))

        wrong_path_errors, _ = evaluate_policy(
            candidate,
            {**grant_facts, "changed_paths": ["app.py"]},
            PROFILE_CORE_INTEGRATION_PACKAGE,
            "grant",
            require_clean=True,
            origin_ledger=anchored,
            candidate_baseline=self.baseline,
            origin_baseline=self.baseline,
        )
        self.assertTrue(any("control branch must change exactly" in item for item in wrong_path_errors))

        unknown = copy.deepcopy(candidate_lane)
        unknown["package"] = "PS-UNKNOWN-IMPLEMENTATION-001"
        unknown["branch"] = "work/2026-08-13-unknown-implementation-001"
        unknown_errors: list[str] = []
        _direction_merge_grant(unknown, "unknown implementation", unknown_errors)
        self.assertTrue(any("code-controlled" in item for item in unknown_errors))

        merge_facts = facts(
            branch=PROFILE_CORE_INTEGRATION_BRANCH,
            head=PROFILE_CORE_INTEGRATION_REVIEWED_SHA,
            origin_main="2" * 40,
            behind=5,
            merge_target_remote_sha=PROFILE_CORE_INTEGRATION_REVIEWED_SHA,
            changed_paths=["profile_routes.py"],
            merge_main_changed_paths=sorted(
                set(PROFILE_CORE_MERGE_CONTROL_PATHS)
                | set(PROFILE_CORE_GRANT_FOLLOWUP_PATHS)
                | set(PROFILE_CORE_GRANT_ANCHOR_PATHS)
                | {"docs/governance/CURRENT_LANES.json"}
                | set(PROFILE_CORE_POST_GRANT_REGISTRY_FIXTURE_PATHS)
            ),
            merge_main_control_commits_valid=True,
            merge_main_control_commit_count=5,
        )
        merge_errors, merge_warnings = evaluate_policy(
            post_grant,
            merge_facts,
            PROFILE_CORE_INTEGRATION_PACKAGE,
            "merge",
            require_clean=True,
            origin_ledger=post_grant,
        )
        self.assertEqual([], merge_errors)
        self.assertTrue(any("ledger-only grant" in item for item in merge_warnings))

        extra_main_errors, _ = evaluate_policy(
            post_grant,
            {
                **merge_facts,
                "behind": 6,
                "merge_main_control_commit_count": 6,
                "merge_main_control_commits_valid": False,
            },
            PROFILE_CORE_INTEGRATION_PACKAGE,
            "merge",
            require_clean=True,
            origin_ledger=post_grant,
        )
        self.assertTrue(any("exactly five verified" in item for item in extra_main_errors))
        self.assertTrue(any("exact repair-plus-target-grant" in item for item in extra_main_errors))

        malformed_profile = copy.deepcopy(post_grant)
        malformed_lane = next(
            item
            for item in malformed_profile["active_lanes"]
            if item.get("package") == PROFILE_CORE_INTEGRATION_PACKAGE
        )
        malformed_lane["branch"] = "work/2026-08-13-unknown-implementation-001"
        malformed_errors, _ = evaluate_policy(
            malformed_profile,
            {
                **merge_facts,
                "branch": malformed_lane["branch"],
            },
            PROFILE_CORE_INTEGRATION_PACKAGE,
            "merge",
            require_clean=True,
            origin_ledger=malformed_profile,
        )
        self.assertTrue(
            any("exact code-controlled" in item for item in malformed_errors)
        )

    def test_connect_002_merge_admission_repair_is_exact_and_fails_closed(self):
        expected_review = {
            "reviewer_task": "/root/profile_descendant_exact_review",
            "reviewer_mode": "independent_read_only_non_writer",
            "reviewed_sha": "db20e2285f82c0f61baa73c49cd6f0bee0771620",
            "reviewed_branch": "work/2026-08-13-connect-002-profile-relationships",
            "verdict": "PASS",
            "verdict_text": (
                "PASS - exact-tree mechanical re-review passed for "
                "db20e2285f82c0f61baa73c49cd6f0bee0771620, branch-equal to "
                "origin/work/2026-08-13-connect-002-profile-relationships and "
                "clean; the 03ab-to-db20 delta is exactly three files and five "
                "semantics-preserving keyword-unpack call-site rewrites; normalized "
                "ASTs are identical; focused Connect tests pass; Gitleaks 8.30.1 "
                "full-history scan exited 0 with no leaks."
            ),
            "verdict_sha256": (
                "a6650dcf13e0b94e3f7f09f8e22daad3c57edcaa6eccfac74aa42bee4ab8ecca"
            ),
            "basis": [
                "full_tree_at_db20e2285f82c0f61baa73c49cd6f0bee0771620",
                "complete_diff_03abfa777160e4e7293f2a89c3ce76fba22872ce_to_"
                "db20e2285f82c0f61baa73c49cd6f0bee0771620_exact_3_files_5_"
                "callsite_rewrites_normalized_ast_equal",
                "connect_focused_unittest_31_of_31_pycompile_diff_check_pass",
                "gitleaks_8_30_1_full_history_exit_0_1255_commits_no_leaks",
                "prior_semantic_lifecycle_sql_provider_review_at_"
                "03abfa777160e4e7293f2a89c3ce76fba22872ce_unchanged",
            ],
            "scope": "protected_connect_002_non_production_provider_merge_only",
            "exclusions": "schema_apply_deployment_profile_integration_enablement",
            "evidence_path": (
                "artifacts/2026-08-13-connect-002/IMPLEMENTATION_CHECKPOINT.md"
            ),
            "evidence_git_blob_sha": "c43fdb404aed9aa5293b745c3c3918245be0d056",
            "evidence_bytes_sha256": (
                "993380d46f760eb90172a774031ede66e19861d6487757612ef31ae54e32891e"
            ),
            "received_by": "Root Codex program manager",
            "received_date": "2026-08-13",
            "attestation_sha256": (
                "d07748edb202c4d7a0e5e7a26a0eb86b53d5449fa13f3597fa03525ba5573aa4"
            ),
        }
        self.assertEqual(expected_review, CONNECT_002_REVIEW_ATTESTATION)
        expected_contract = {
            "package": CONNECT_002_PACKAGE,
            "branch": CONNECT_002_BRANCH,
            "reviewed_remote_sha": "db20e2285f82c0f61baa73c49cd6f0bee0771620",
            "owner_decision_sha256": (
                "fa9ecd740f844e833c50d97f86c413996fbb324edb56ce02422408182e062f96"
            ),
            "reviewer_task": "/root/profile_descendant_exact_review",
            "review_attestation_sha256": expected_review["attestation_sha256"],
            "review_evidence_path": expected_review["evidence_path"],
            "review_evidence_git_blob_sha": expected_review["evidence_git_blob_sha"],
            "review_evidence_bytes_sha256": expected_review[
                "evidence_bytes_sha256"
            ],
        }
        self.assertEqual(expected_contract, CONNECT_002_MERGE_CANDIDATE_CONTRACT)
        self.assertEqual(
            expected_contract,
            CONNECT_002_MERGE_ADMISSION_REPAIR["candidate_contract"],
        )
        supplied_attestation = dict(CONNECT_002_REVIEW_ATTESTATION)
        supplied_digest = supplied_attestation.pop("attestation_sha256")
        self.assertEqual(supplied_digest, _canonical_sha256(supplied_attestation))
        origin, original_lane = self._connect_002_origin()
        candidate = self._connect_002_repair_candidate(origin)
        baseline = load_baseline_bytes_at_ref(
            CONNECT_002_MERGE_ADMISSION_REPAIR["origin_main"]
        )
        exact_facts = facts(
            branch=CONNECT_002_MERGE_ADMISSION_REPAIR["branch"],
            origin_main=CONNECT_002_MERGE_ADMISSION_REPAIR["origin_main"],
            ahead=1,
            behind=0,
            changed_paths=CONNECT_002_MERGE_ADMISSION_REPAIR["allowed_surfaces"],
        )
        self.assertTrue(
            _exact_connect_002_merge_admission_repair_matches(
                candidate,
                exact_facts,
                CONNECT_002_MERGE_ADMISSION_REPAIR["package"],
            )
        )
        self.assertTrue(
            _exact_connect_002_merge_admission_repair_delta(origin, candidate)
        )
        errors, warnings = self._evaluate_activation(
            candidate,
            exact_facts,
            require_clean=True,
            origin=origin,
            candidate_baseline=baseline,
            origin_baseline=baseline,
        )
        self.assertEqual([], errors)
        self.assertTrue(any("authority-neutral" in item for item in warnings))
        self.assertEqual(origin["operating_mode"], candidate["operating_mode"])
        self.assertEqual(origin["active_lanes"], candidate["active_lanes"])
        target = next(
            lane
            for lane in candidate["active_lanes"]
            if lane["package"] == CONNECT_002_PACKAGE
        )
        self.assertEqual(original_lane, target)
        self.assertNotIn("merge_grant", target)
        self.assertNotIn(
            CONNECT_002_PACKAGE,
            candidate["operating_mode"]["merge_allowed_for"],
        )
        self.assertEqual([], candidate["operating_mode"]["release_allowed_for"])
        self.assertEqual([], candidate["operating_mode"]["cleanup_allowed_for"])
        self.assertEqual(
            CONNECT_002_OWNER_DECISION_SHA256,
            _canonical_sha256(target["owner_decisions"][0]),
        )
        self.assertTrue(
            _affirmative_merge_decision(
                target["owner_decisions"][0], CONNECT_002_PACKAGE
            )
        )

        def activation_errors(
            altered: dict,
            altered_facts: dict = exact_facts,
            *,
            altered_origin: dict = origin,
            altered_baseline: bytes = baseline,
        ) -> list[str]:
            result, _ = self._evaluate_activation(
                altered,
                altered_facts,
                require_clean=True,
                origin=altered_origin,
                candidate_baseline=altered_baseline,
                origin_baseline=baseline,
            )
            return result

        for label, altered_facts in (
            ("wrong-branch", {**exact_facts, "branch": "work/2026-08-13-delivery-activation-forged"}),
            ("wrong-base", {**exact_facts, "origin_main": "0" * 40}),
            ("ahead-zero", {**exact_facts, "ahead": 0}),
            ("ahead-two", {**exact_facts, "ahead": 2}),
            ("behind-one", {**exact_facts, "behind": 1}),
            ("wrong-path", {**exact_facts, "changed_paths": ["app.py"]}),
            (
                "missing-path",
                {**exact_facts, "changed_paths": [
                    "docs/governance/CURRENT_LANES.json",
                    "scripts/delivery_preflight.py",
                ]},
            ),
            (
                "extra-path",
                {**exact_facts, "changed_paths": [
                    *CONNECT_002_MERGE_ADMISSION_REPAIR["allowed_surfaces"],
                    "README.md",
                ]},
            ),
        ):
            with self.subTest(label=label):
                self.assertTrue(activation_errors(copy.deepcopy(candidate), altered_facts))

        self.assertTrue(
            activation_errors(
                copy.deepcopy(candidate),
                altered_baseline=baseline + b"\nforged baseline mutation",
            )
        )
        for label, mutate in (
            (
                "lane",
                lambda value: next(
                    lane for lane in value["active_lanes"]
                    if lane["package"] == CONNECT_002_PACKAGE
                ).__setitem__("branch", "work/2026-08-13-connect-002-forged"),
            ),
            (
                "authority",
                lambda value: value["operating_mode"]["writes_allowed_for"].append(
                    "PS-FORGED-001"
                ),
            ),
            (
                "merge",
                lambda value: value["operating_mode"]["merge_allowed_for"].append(
                    CONNECT_002_PACKAGE
                ),
            ),
            (
                "release",
                lambda value: value["operating_mode"]["release_allowed_for"].append(
                    CONNECT_002_PACKAGE
                ),
            ),
            (
                "cleanup",
                lambda value: value["operating_mode"]["cleanup_allowed_for"].append(
                    CONNECT_002_PACKAGE
                ),
            ),
            (
                "record",
                lambda value: value["connect_002_merge_admission_repair"]["candidate_contract"].__setitem__(
                    "reviewed_remote_sha", "0" * 40
                ),
            ),
        ):
            with self.subTest(label=label):
                altered = copy.deepcopy(candidate)
                mutate(altered)
                self.assertTrue(activation_errors(altered))

        for label, repaired_at in (
            ("equal", origin["updated_at"]),
            ("earlier", "2026-08-13T06:52:51Z"),
            ("malformed", "not-a-timestamp"),
        ):
            with self.subTest(label=label):
                self.assertTrue(
                    activation_errors(
                        self._connect_002_repair_candidate(
                            origin, repaired_at=repaired_at
                        )
                    )
                )

        preexisting_origin = copy.deepcopy(origin)
        preexisting_origin["updated_at"] = "2026-08-13T07:00:00Z"
        preexisting_origin["connect_002_merge_admission_repair"] = copy.deepcopy(
            CONNECT_002_MERGE_ADMISSION_REPAIR
        )
        self.assertTrue(
            activation_errors(
                self._connect_002_repair_candidate(preexisting_origin),
                altered_origin=preexisting_origin,
            )
        )

        grant_errors, _ = evaluate_policy(
            candidate,
            exact_facts,
            CONNECT_002_PACKAGE,
            "grant",
            require_clean=True,
            origin_ledger=origin,
            candidate_baseline=baseline,
            origin_baseline=baseline,
        )
        self.assertTrue(any("anchored follow-up" in item for item in grant_errors))

        exact_merge_errors, _ = evaluate_policy(
            origin,
            {**exact_facts, "branch": CONNECT_002_BRANCH, "fetched": True},
            CONNECT_002_PACKAGE,
            "merge",
            require_clean=True,
            origin_ledger=origin,
        )
        self.assertTrue(
            any("anchored follow-up" in item for item in exact_merge_errors)
        )

        malformed = copy.deepcopy(origin)
        malformed_target = next(
            lane for lane in malformed["active_lanes"]
            if lane["package"] == CONNECT_002_PACKAGE
        )
        malformed_target["branch"] = "work/2026-08-13-connect-002-forged"
        merge_errors, _ = evaluate_policy(
            malformed,
            {**exact_facts, "branch": malformed_target["branch"], "fetched": True},
            CONNECT_002_PACKAGE,
            "merge",
            require_clean=True,
            origin_ledger=malformed,
        )
        self.assertTrue(any("exact code-controlled" in item for item in merge_errors))

    def test_connect_002_candidate_merge_stays_blocked_until_anchored(self):
        """The repair must not recognize a reconstructable merge sequence."""
        self.assertEqual(
            ([], False, 0),
            _direction_main_sequence_facts(
                {}, CONNECT_002_PACKAGE, CONNECT_002_REVIEWED_SHA, "0" * 40
            ),
        )

    def test_connect_002_merge_admission_anchor_is_exact_and_review_bound(self):
        """Only the pinned merged repair can unlock the reconciled candidate."""
        anchor = CONNECT_002_MERGE_ADMISSION_ANCHOR_FOLLOWUP
        origin, original_lane = self._connect_002_anchor_origin()
        candidate = self._connect_002_anchor_candidate(origin)
        baseline = load_baseline_bytes_at_ref(anchor["origin_main"])
        exact_facts = facts(
            branch=anchor["branch"],
            origin_main=anchor["origin_main"],
            ahead=1,
            behind=0,
            changed_paths=anchor["allowed_surfaces"],
        )
        self.assertEqual(
            CONNECT_002_MERGE_ADMISSION_REPAIR_MAIN,
            anchor["existing_main_chain"]["merge_admission_repair_main"],
        )
        self.assertEqual(
            CONNECT_002_RECONCILED_CANDIDATE_CONTRACT,
            anchor["candidate_contract"],
        )
        supplied_attestation = dict(CONNECT_002_RECONCILED_REVIEW_ATTESTATION)
        supplied_digest = supplied_attestation.pop("attestation_sha256")
        self.assertEqual(supplied_digest, _canonical_sha256(supplied_attestation))
        self.assertTrue(
            _exact_connect_002_merge_admission_anchor_followup_matches(
                candidate, exact_facts, anchor["package"]
            )
        )
        self.assertTrue(
            _exact_connect_002_merge_admission_anchor_followup_delta(
                origin, candidate
            )
        )
        errors, warnings = self._evaluate_activation(
            candidate,
            exact_facts,
            require_clean=True,
            origin=origin,
            candidate_baseline=baseline,
            origin_baseline=baseline,
        )
        self.assertEqual([], errors)
        self.assertTrue(any("merged-repair anchor" in item for item in warnings))
        self.assertEqual(origin["operating_mode"], candidate["operating_mode"])
        self.assertEqual(origin["active_lanes"], candidate["active_lanes"])
        self.assertEqual(
            original_lane,
            next(
                lane
                for lane in candidate["active_lanes"]
                if lane["package"] == CONNECT_002_PACKAGE
            ),
        )

        for label, altered_facts in (
            ("wrong-branch", {**exact_facts, "branch": "work/2026-08-13-delivery-activation-forged"}),
            ("wrong-base", {**exact_facts, "origin_main": "0" * 40}),
            ("wrong-ahead", {**exact_facts, "ahead": 2}),
            ("wrong-path", {**exact_facts, "changed_paths": ["app.py"]}),
        ):
            with self.subTest(label=label):
                altered_errors, _ = self._evaluate_activation(
                    copy.deepcopy(candidate),
                    altered_facts,
                    require_clean=True,
                    origin=origin,
                    candidate_baseline=baseline,
                    origin_baseline=baseline,
                )
                self.assertTrue(altered_errors)

        forged = copy.deepcopy(candidate)
        forged["operating_mode"]["merge_allowed_for"].append(
            CONNECT_002_PACKAGE
        )
        forged_errors, _ = self._evaluate_activation(
            forged,
            exact_facts,
            require_clean=True,
            origin=origin,
            candidate_baseline=baseline,
            origin_baseline=baseline,
        )
        self.assertTrue(forged_errors)

    def test_connect_002_grant_fixture_followup_is_exact_and_preserves_grant(self):
        """The fixture repair is inert and comes before the exact grant."""
        fixture = CONNECT_002_GRANT_FIXTURE_FOLLOWUP_R3
        origin, original_lane = self._connect_002_grant_fixture_origin()
        candidate = self._connect_002_grant_fixture_candidate(origin)
        baseline = load_baseline_bytes_at_ref(fixture["origin_main"])
        exact_facts = facts(
            branch=fixture["branch"],
            origin_main=fixture["origin_main"],
            ahead=1,
            behind=0,
            changed_paths=fixture["allowed_surfaces"],
        )
        self.assertEqual(
            CONNECT_002_MERGE_ADMISSION_ANCHOR_MAIN,
            fixture["existing_main_chain"]["merge_admission_anchor_main"],
        )
        self.assertEqual(
            CONNECT_002_MERGE_ADMISSION_ANCHOR_SOURCE,
            fixture["existing_main_chain"]["merge_admission_anchor_source"],
        )
        self.assertTrue(
            _exact_connect_002_grant_fixture_followup_matches(
                candidate, exact_facts, fixture["package"]
            )
        )
        self.assertTrue(
            _exact_connect_002_grant_fixture_followup_delta(origin, candidate)
        )
        errors, warnings = self._evaluate_activation(
            candidate,
            exact_facts,
            require_clean=True,
            origin=origin,
            candidate_baseline=baseline,
            origin_baseline=baseline,
        )
        self.assertEqual([], errors)
        self.assertTrue(any("grant-fixture" in item for item in warnings))
        self.assertEqual(origin["operating_mode"], candidate["operating_mode"])
        self.assertEqual(origin["active_lanes"], candidate["active_lanes"])
        self.assertEqual(
            original_lane,
            next(
                lane
                for lane in candidate["active_lanes"]
                if lane["package"] == CONNECT_002_PACKAGE
            ),
        )

        for label, altered_facts in (
            (
                "wrong-branch",
                {**exact_facts, "branch": "work/2026-08-13-delivery-activation-forged"},
            ),
            ("wrong-base", {**exact_facts, "origin_main": "0" * 40}),
            ("wrong-ahead", {**exact_facts, "ahead": 2}),
            ("wrong-path", {**exact_facts, "changed_paths": ["app.py"]}),
        ):
            with self.subTest(label=label):
                altered_errors, _ = self._evaluate_activation(
                    copy.deepcopy(candidate),
                    altered_facts,
                    require_clean=True,
                    origin=origin,
                    candidate_baseline=baseline,
                    origin_baseline=baseline,
                )
                self.assertTrue(altered_errors)

        granted = copy.deepcopy(candidate)
        granted_at = "2026-08-13T19:32:00Z"
        target = next(
            lane
            for lane in granted["active_lanes"]
            if lane["package"] == CONNECT_002_PACKAGE
        )
        target["merge_grant"] = self._connect_002_grant_record(target, granted_at)
        granted["operating_mode"]["merge_allowed_for"] = [
            *candidate["operating_mode"]["merge_allowed_for"],
            CONNECT_002_PACKAGE,
        ]
        granted["updated_at"] = granted_at
        grant_facts = facts(
            branch="work/2026-08-13-delivery-grant-connect-002-exact-r3",
            origin_main="1" * 40,
            ahead=1,
            behind=0,
            changed_paths=["docs/governance/CURRENT_LANES.json"],
            grant_target_remote_sha=CONNECT_002_RECONCILED_REVIEWED_SHA,
            **self._review_evidence_facts(target["merge_grant"]),
        )
        grant_errors, _ = evaluate_policy(
            granted,
            grant_facts,
            CONNECT_002_PACKAGE,
            "grant",
            require_clean=True,
            origin_ledger=candidate,
            candidate_baseline=baseline,
            origin_baseline=baseline,
        )
        self.assertEqual([], grant_errors)
        self.assertTrue(
            _exact_direction_grant_delta(
                candidate, granted, CONNECT_002_PACKAGE
            )
        )

        merge_facts = facts(
            branch=CONNECT_002_RECONCILED_BRANCH,
            head=CONNECT_002_RECONCILED_REVIEWED_SHA,
            origin_main="2" * 40,
            behind=3,
            merge_target_remote_sha=CONNECT_002_RECONCILED_REVIEWED_SHA,
            changed_paths=["services/connection_foundation_service.py"],
            merge_main_changed_paths=sorted(
                set(CONNECT_002_MERGE_ADMISSION_ANCHOR_PATHS)
                | set(CONNECT_002_GRANT_FIXTURE_FOLLOWUP_PATHS)
                | set(GRANT_ALLOWED_SURFACES)
            ),
            merge_main_control_commits_valid=True,
            merge_main_control_commit_count=3,
        )
        merge_errors, merge_warnings = evaluate_policy(
            granted,
            merge_facts,
            CONNECT_002_PACKAGE,
            "merge",
            require_clean=True,
            origin_ledger=granted,
        )
        self.assertEqual([], merge_errors)
        self.assertTrue(any("merged-repair anchor" in item for item in merge_warnings))

        wrong_review = copy.deepcopy(granted)
        wrong_target = next(
            lane
            for lane in wrong_review["active_lanes"]
            if lane["package"] == CONNECT_002_PACKAGE
        )
        wrong_target["merge_grant"]["reviewed_remote_sha"] = "0" * 40
        wrong_errors, _ = evaluate_policy(
            wrong_review,
            grant_facts,
            CONNECT_002_PACKAGE,
            "grant",
            require_clean=True,
            origin_ledger=candidate,
            candidate_baseline=baseline,
            origin_baseline=baseline,
        )
        self.assertTrue(any("reconciled PS-CONNECT-002 SHA" in item for item in wrong_errors))

    def test_connect_002_main_sequence_requires_pinned_repair_anchor_fixture_and_grant(self):
        """The candidate path admits no reconstructable control shortcut."""
        control_base = CONNECT_002_MERGE_ADMISSION_ANCHOR_FOLLOWUP["origin_main"]
        repair_base, _ = self._connect_002_origin()
        repair = self._connect_002_repair_candidate(repair_base)
        base, _ = self._connect_002_anchor_origin()
        anchor = self._connect_002_anchor_candidate(base)
        fixture = self._connect_002_grant_fixture_candidate(anchor)
        granted = copy.deepcopy(fixture)
        granted_at = "2026-08-13T19:32:00Z"
        target = next(
            lane
            for lane in granted["active_lanes"]
            if lane["package"] == CONNECT_002_PACKAGE
        )
        target["merge_grant"] = self._connect_002_grant_record(target, granted_at)
        granted["operating_mode"]["merge_allowed_for"] = [
            *fixture["operating_mode"]["merge_allowed_for"],
            CONNECT_002_PACKAGE,
        ]
        granted["updated_at"] = granted_at
        anchor_sha = CONNECT_002_MERGE_ADMISSION_ANCHOR_MAIN
        fixture_sha = "b" * 40
        grant_sha = "c" * 40
        origin_main = "d" * 40

        def sequence(
            repair_source_tree: str = "repair-tree",
            anchor_source_tree: str = "anchor-tree",
        ) -> tuple[list[str], bool, int]:
            ledgers = {
                CONNECT_002_MERGE_ADMISSION_REPAIR["origin_main"]: repair_base,
                CONNECT_002_MERGE_ADMISSION_REPAIR_MAIN: repair,
                control_base: base,
                anchor_sha: anchor,
                fixture_sha: fixture,
            }

            def fake_git(*args: str, **_kwargs: object) -> str:
                if args[:2] == ("rev-list", "--reverse"):
                    return f"{anchor_sha}\n{fixture_sha}\n{grant_sha}\n"
                if args[0] == "rev-parse":
                    values = {
                        f"{anchor_sha}^": control_base,
                        f"{fixture_sha}^": anchor_sha,
                        f"{grant_sha}^": fixture_sha,
                        f"{CONNECT_002_MERGE_ADMISSION_REPAIR_MAIN}^": (
                            CONNECT_002_MERGE_ADMISSION_REPAIR["origin_main"]
                        ),
                        f"{CONNECT_002_MERGE_ADMISSION_REPAIR_MAIN}^{{tree}}": (
                            "repair-tree"
                        ),
                        "edfa9af025cf8b473bd8c59cfb240b786ddb3ef5^{tree}": (
                            repair_source_tree
                        ),
                        f"{anchor_sha}^{{tree}}": "anchor-tree",
                        f"{CONNECT_002_MERGE_ADMISSION_ANCHOR_SOURCE}^{{tree}}": (
                            anchor_source_tree
                        ),
                    }
                    return values[args[-1]]
                if args[0] == "merge-base":
                    return control_base
                raise AssertionError(args)

            def fake_git_nul(*args: str, **_kwargs: object) -> list[str]:
                if args[0] == "diff-tree":
                    paths = {
                        anchor_sha: CONNECT_002_MERGE_ADMISSION_ANCHOR_PATHS,
                        fixture_sha: CONNECT_002_GRANT_FIXTURE_FOLLOWUP_PATHS,
                        grant_sha: GRANT_ALLOWED_SURFACES,
                        CONNECT_002_MERGE_ADMISSION_REPAIR_MAIN: (
                            CONNECT_002_MERGE_ADMISSION_REPAIR_PATHS
                        ),
                    }
                    return sorted(paths[args[-1]])
                if args[0] == "diff" and args[-1] == f"{control_base}..{origin_main}":
                    return sorted(
                        set(CONNECT_002_MERGE_ADMISSION_ANCHOR_PATHS)
                        | set(CONNECT_002_GRANT_FIXTURE_FOLLOWUP_PATHS)
                        | set(GRANT_ALLOWED_SURFACES)
                    )
                if args[0] == "diff" and args[-1] == (
                    f"{control_base}..{CONNECT_002_RECONCILED_REVIEWED_SHA}"
                ):
                    return ["services/connection_foundation_service.py"]
                raise AssertionError(args)

            with (
                patch("scripts.delivery_preflight._git", side_effect=fake_git),
                patch("scripts.delivery_preflight._git_nul", side_effect=fake_git_nul),
                patch(
                    "scripts.delivery_preflight.load_ledger_at_ref",
                    side_effect=lambda ref: copy.deepcopy(ledgers[ref]),
                ),
                patch("scripts.delivery_preflight._git_returncode_at", return_value=0),
            ):
                return _connect_002_main_sequence_facts(
                    granted,
                    CONNECT_002_PACKAGE,
                    CONNECT_002_RECONCILED_REVIEWED_SHA,
                    origin_main,
                )

        paths, valid, count = sequence()
        self.assertEqual(
            sorted(
                set(CONNECT_002_MERGE_ADMISSION_ANCHOR_PATHS)
                | set(CONNECT_002_GRANT_FIXTURE_FOLLOWUP_PATHS)
                | set(GRANT_ALLOWED_SURFACES)
            ),
            paths,
        )
        self.assertTrue(valid)
        self.assertEqual(3, count)

        _, invalid, count = sequence(anchor_source_tree="forged-tree")
        self.assertFalse(invalid)
        self.assertEqual(3, count)

    def test_profile_core_main_sequence_rejects_bad_repair_timestamps(self):
        """The inert repair must advance a valid timestamp before its grant."""
        package = PROFILE_CORE_INTEGRATION_PACKAGE
        candidate_sha = PROFILE_CORE_INTEGRATION_REVIEWED_SHA
        control_base = PROFILE_CORE_MERGE_PREFLIGHT_REPAIR["origin_main"]
        repair_sha = PROFILE_CORE_MERGE_REPAIR_MAIN
        fixture_sha = PROFILE_CORE_GRANT_FIXTURE_FOLLOWUP_MAIN
        anchor_sha = PROFILE_CORE_GRANT_ANCHOR_FOLLOWUP_MAIN
        grant_sha = PROFILE_CORE_LEDGER_GRANT_MAIN
        post_grant_repair_sha = "d" * 40
        origin_main = "e" * 40

        def ledgers(
            *,
            base_updated_at: str = "2026-08-13T02:13:14Z",
            repair_updated_at: str = "2026-08-13T02:15:00Z",
            post_grant_updated_at: str = "2026-08-13T04:21:00Z",
        ) -> tuple[dict, dict, dict, dict, dict, dict]:
            base, _ = self._profile_core_origin()
            base["updated_at"] = base_updated_at
            repair = copy.deepcopy(base)
            repair["updated_at"] = repair_updated_at
            repair["profile_core_merge_preflight_repair"] = copy.deepcopy(
                PROFILE_CORE_MERGE_PREFLIGHT_REPAIR
            )
            followed = copy.deepcopy(repair)
            followed["updated_at"] = "2026-08-13T03:36:53Z"
            followed["profile_core_grant_fixture_followup"] = copy.deepcopy(
                PROFILE_CORE_GRANT_FIXTURE_FOLLOWUP
            )
            anchored = copy.deepcopy(followed)
            anchored["updated_at"] = "2026-08-13T03:56:56Z"
            anchored["profile_core_grant_anchor_followup"] = copy.deepcopy(
                PROFILE_CORE_GRANT_ANCHOR_FOLLOWUP
            )
            granted = copy.deepcopy(anchored)
            granted_at = "2026-08-13T03:57:30Z"
            lane = next(
                item
                for item in granted["active_lanes"]
                if item.get("package") == package
            )
            lane["merge_grant"] = self._profile_core_grant_record(lane, granted_at)
            granted["operating_mode"]["merge_allowed_for"] = [
                *anchored["operating_mode"]["merge_allowed_for"], package
            ]
            granted["updated_at"] = granted_at
            post_grant = copy.deepcopy(granted)
            post_grant["updated_at"] = post_grant_updated_at
            post_grant["profile_core_post_grant_registry_fixture_repair"] = (
                copy.deepcopy(PROFILE_CORE_POST_GRANT_REGISTRY_FIXTURE_REPAIR)
            )
            return base, repair, followed, anchored, granted, post_grant

        def sequence_valid(
            base: dict,
            repair: dict,
            followed: dict,
            anchored: dict,
            granted: dict,
            post_grant: dict,
            *,
            recorded_repair_sha: str = repair_sha,
            recorded_fixture_sha: str = fixture_sha,
            recorded_anchor_sha: str = anchor_sha,
            recorded_grant_sha: str = grant_sha,
            recorded_post_grant_repair_sha: str = post_grant_repair_sha,
            include_sixth: bool = False,
        ) -> tuple[list[str], bool, int]:
            chain = [
                recorded_repair_sha,
                recorded_fixture_sha,
                recorded_anchor_sha,
                recorded_grant_sha,
                recorded_post_grant_repair_sha,
            ]
            if include_sixth:
                chain.append("f" * 40)
            parents = {
                chain[0]: control_base,
                chain[1]: chain[0],
                chain[2]: chain[1],
                chain[3]: chain[2],
                chain[4]: chain[3],
            }
            ledgers_by_ref = {
                control_base: base,
                chain[0]: repair,
                chain[1]: followed,
                chain[2]: anchored,
                chain[3]: granted,
            }

            def fake_git(*args: str, **_kwargs: object) -> str:
                if args[:2] == ("rev-list", "--reverse"):
                    return "\n".join(chain)
                if args[:1] == ("rev-parse",) and len(args) == 2:
                    raw = args[1]
                    if raw.endswith("^") and raw[:-1] in parents:
                        return parents[raw[:-1]]
                if args == ("merge-base", candidate_sha, origin_main):
                    return control_base
                self.fail(f"unexpected git command: {args}")

            def fake_git_nul(*args: str, **_kwargs: object) -> list[str]:
                if args[0] == "diff-tree":
                    paths_by_sha = {
                        chain[0]: PROFILE_CORE_MERGE_CONTROL_PATHS,
                        chain[1]: PROFILE_CORE_GRANT_FOLLOWUP_PATHS,
                        chain[2]: PROFILE_CORE_GRANT_ANCHOR_PATHS,
                        chain[3]: GRANT_ALLOWED_SURFACES,
                        chain[4]: PROFILE_CORE_POST_GRANT_REGISTRY_FIXTURE_PATHS,
                    }
                    return sorted(paths_by_sha[args[-1]])
                if args[0] == "diff":
                    return (
                        sorted(
                            set(PROFILE_CORE_MERGE_CONTROL_PATHS)
                            | set(PROFILE_CORE_GRANT_FOLLOWUP_PATHS)
                            | set(PROFILE_CORE_GRANT_ANCHOR_PATHS)
                            | set(GRANT_ALLOWED_SURFACES)
                            | set(PROFILE_CORE_POST_GRANT_REGISTRY_FIXTURE_PATHS)
                        )
                        if args[-1] == f"{control_base}..{origin_main}"
                        else ["profile_routes.py"]
                    )
                self.fail(f"unexpected nul git command: {args}")

            def ledger_for_ref(ref: str) -> dict:
                if ref not in ledgers_by_ref:
                    self.fail(f"unexpected ledger ref: {ref}")
                return ledgers_by_ref[ref]

            with patch("scripts.delivery_preflight._git", side_effect=fake_git), patch(
                "scripts.delivery_preflight._git_nul", side_effect=fake_git_nul
            ), patch(
                "scripts.delivery_preflight.load_ledger_at_ref",
                side_effect=ledger_for_ref,
            ):
                return _profile_core_main_sequence_facts(
                    post_grant, package, candidate_sha, origin_main
                )

        base, repair, followed, anchored, granted, post_grant = ledgers()
        _, valid, count = sequence_valid(
            base, repair, followed, anchored, granted, post_grant
        )
        self.assertTrue(valid)
        self.assertEqual(5, count)

        _, valid, count = sequence_valid(
            base,
            repair,
            followed,
            anchored,
            granted,
            post_grant,
            recorded_grant_sha="a" * 40,
        )
        self.assertFalse(valid)
        self.assertEqual(5, count)

        _, valid, count = sequence_valid(
            base,
            repair,
            followed,
            anchored,
            granted,
            post_grant,
            include_sixth=True,
        )
        self.assertFalse(valid)
        self.assertEqual(6, count)

        for label, base_time, repair_time, post_time in (
            ("equal", "2026-08-13T02:13:14Z", "2026-08-13T02:13:14Z", "2026-08-13T04:21:00Z"),
            ("earlier", "2026-08-13T02:13:14Z", "2026-08-13T02:12:59Z", "2026-08-13T04:21:00Z"),
            ("malformed-repair", "2026-08-13T02:13:14Z", "not-a-timestamp", "2026-08-13T04:21:00Z"),
            ("invalid-base", "not-a-timestamp", "2026-08-13T02:15:00Z", "2026-08-13T04:21:00Z"),
            ("post-grant-equal", "2026-08-13T02:13:14Z", "2026-08-13T02:15:00Z", "2026-08-13T03:57:30Z"),
            ("post-grant-earlier", "2026-08-13T02:13:14Z", "2026-08-13T02:15:00Z", "2026-08-13T03:57:29Z"),
            ("post-grant-malformed", "2026-08-13T02:13:14Z", "2026-08-13T02:15:00Z", "not-a-timestamp"),
        ):
            with self.subTest(label=label):
                base, repair, followed, anchored, granted, post_grant = ledgers(
                    base_updated_at=base_time,
                    repair_updated_at=repair_time,
                    post_grant_updated_at=post_time,
                )
                _, valid, count = sequence_valid(
                    base, repair, followed, anchored, granted, post_grant
                )
                self.assertFalse(valid)
                self.assertEqual(5, count)

    def test_profile_core_frozen_candidate_uses_exact_post_grant_fixture_repo(self):
        """Exercise only the immutable main chain plus the fifth inert repair."""
        package = PROFILE_CORE_INTEGRATION_PACKAGE
        candidate_branch = PROFILE_CORE_INTEGRATION_BRANCH
        candidate_sha = PROFILE_CORE_INTEGRATION_REVIEWED_SHA
        repair_base = PROFILE_CORE_MERGE_PREFLIGHT_REPAIR["origin_main"]
        grant_main = PROFILE_CORE_LEDGER_GRANT_MAIN

        def run(
            *args: str,
            cwd: Path | None = None,
            check: bool = True,
        ) -> subprocess.CompletedProcess[str]:
            result = subprocess.run(
                [str(arg) for arg in args],
                cwd=str(cwd) if cwd is not None else None,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            if check and result.returncode:
                self.fail(
                    f"command failed ({result.returncode}): {' '.join(args)}\n"
                    f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
                )
            return result

        def git(repository: Path, *args: str, check: bool = True):
            return run("git", "-C", str(repository), *args, check=check)

        def invoke(verifier: Path, candidate: Path):
            fixture_identity = (
                "https://dev.azure.com/peerslate-test/profile-core-fixture/_git/portfolio"
            )
            bootstrap = f"""
import importlib.util
from unittest.mock import patch
script = {str(verifier / 'scripts' / 'delivery_preflight.py')!r}
spec = importlib.util.spec_from_file_location('delivery_preflight_fixture', script)
delivery_preflight = importlib.util.module_from_spec(spec)
spec.loader.exec_module(delivery_preflight)
with patch.object(
    delivery_preflight,
    '_authoritative_azure_origin',
    return_value={fixture_identity!r},
):
    raise SystemExit(delivery_preflight.main())
"""
            return run(
                sys.executable,
                "-I",
                "-c",
                bootstrap,
                "--package",
                package,
                "--intent",
                "merge",
                "--fetch",
                "--require-clean",
                "--candidate-worktree",
                str(candidate.resolve()),
                cwd=verifier,
                check=False,
            )

        with tempfile.TemporaryDirectory(prefix="ps-profile-core-candidate-") as raw:
            fixture = Path(raw).resolve()
            seed = fixture / "seed"
            origin = fixture / "profile-core-origin.git"
            verifier = fixture / "verifier"
            candidate = fixture / "candidate"
            run("git", "clone", "--shared", str(ROOT), str(seed))
            git(seed, "config", "user.name", "PeerSlate Test")
            git(seed, "config", "user.email", "peerslate-test@example.invalid")
            git(seed, "checkout", "-B", "profile-core-repair-fixture", grant_main)
            self.assertEqual(
                [
                    PROFILE_CORE_MERGE_REPAIR_MAIN,
                    PROFILE_CORE_GRANT_FIXTURE_FOLLOWUP_MAIN,
                    PROFILE_CORE_GRANT_ANCHOR_FOLLOWUP_MAIN,
                    PROFILE_CORE_LEDGER_GRANT_MAIN,
                ],
                git(
                    seed, "rev-list", "--reverse", f"{repair_base}..{grant_main}"
                ).stdout.split(),
            )
            self.assertEqual(
                PROFILE_CORE_GRANT_ANCHOR_FOLLOWUP_MAIN,
                git(seed, "rev-parse", f"{grant_main}^").stdout.strip(),
            )

            for relative in (
                "scripts/delivery_preflight.py",
                "tests/test_delivery_preflight.py",
                "tests/test_opportunity_slate_v2_migration.py",
            ):
                source = ROOT / relative
                destination = seed / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
                self.assertEqual(source.read_bytes(), destination.read_bytes())

            ledger_path = seed / "docs" / "governance" / "CURRENT_LANES.json"
            grant_ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            self.assertEqual(
                PROFILE_CORE_MERGE_PREFLIGHT_REPAIR,
                grant_ledger.get("profile_core_merge_preflight_repair"),
            )
            self.assertEqual(
                PROFILE_CORE_GRANT_FIXTURE_FOLLOWUP,
                grant_ledger.get("profile_core_grant_fixture_followup"),
            )
            self.assertEqual(
                PROFILE_CORE_GRANT_ANCHOR_FOLLOWUP,
                grant_ledger.get("profile_core_grant_anchor_followup"),
            )
            self.assertNotIn(
                "profile_core_post_grant_registry_fixture_repair", grant_ledger
            )
            post_grant_ledger = copy.deepcopy(grant_ledger)
            post_grant_ledger["updated_at"] = "2026-08-13T04:21:00Z"
            post_grant_ledger["profile_core_post_grant_registry_fixture_repair"] = (
                copy.deepcopy(PROFILE_CORE_POST_GRANT_REGISTRY_FIXTURE_REPAIR)
            )
            self.assertTrue(
                _exact_profile_core_post_grant_registry_fixture_repair_delta(
                    grant_ledger, post_grant_ledger
                )
            )
            ledger_path.write_text(
                json.dumps(post_grant_ledger, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            git(seed, "add", "--", *PROFILE_CORE_POST_GRANT_REGISTRY_FIXTURE_PATHS)
            self.assertEqual(
                set(PROFILE_CORE_POST_GRANT_REGISTRY_FIXTURE_PATHS),
                set(git(seed, "diff", "--cached", "--name-only").stdout.split()),
            )
            git(seed, "commit", "-m", "Repair post-grant registry fixture")
            post_grant_sha = git(seed, "rev-parse", "HEAD").stdout.strip()
            self.assertEqual(
                grant_main,
                git(seed, "rev-parse", f"{post_grant_sha}^").stdout.strip(),
            )

            run("git", "init", "--bare", str(origin))
            git(seed, "remote", "add", "fixture-origin", str(origin))
            git(seed, "push", "fixture-origin", "HEAD:refs/heads/main")
            git(
                seed,
                "push",
                "fixture-origin",
                f"{candidate_sha}:refs/heads/{candidate_branch}",
            )
            run(
                "git", "--git-dir", str(origin), "symbolic-ref", "HEAD",
                "refs/heads/main",
            )

            run("git", "clone", str(origin), str(verifier))
            git(
                verifier,
                "worktree",
                "add",
                "-b",
                candidate_branch,
                str(candidate),
                f"origin/{candidate_branch}",
            )
            self.assertEqual(
                repair_base,
                git(verifier, "merge-base", candidate_sha, "origin/main").stdout.strip(),
            )

            passed = invoke(verifier, candidate)
            self.assertEqual(0, passed.returncode, passed.stdout + passed.stderr)
            payload = json.loads(passed.stdout)
            self.assertEqual("pass", payload["result"])
            self.assertTrue(payload["facts"]["direction_candidate_verified_from_main"])
            self.assertEqual(candidate_sha, payload["facts"]["candidate_head"])
            self.assertEqual(5, payload["facts"]["behind"])
            self.assertEqual(candidate_sha, git(candidate, "rev-parse", "HEAD").stdout.strip())

            # A sixth, otherwise harmless main control commit is enough to
            # invalidate this expired one-time sequence.
            with (seed / "tests" / "test_delivery_preflight.py").open(
                "a", encoding="utf-8"
            ) as handle:
                handle.write("\n# fixture extra main commit\n")
            git(seed, "add", "--", "tests/test_delivery_preflight.py")
            git(seed, "commit", "-m", "Fixture extra main control commit")
            git(seed, "push", "fixture-origin", "HEAD:refs/heads/main")
            git(verifier, "fetch", "origin")
            git(verifier, "merge", "--ff-only", "origin/main")
            extra_main = invoke(verifier, candidate)
            self.assertEqual(2, extra_main.returncode)
            self.assertIn("exactly five verified main control commits", extra_main.stdout)

    def test_opportunity_schema_repair_release_refresh_is_exact_and_grants_nothing(self):
        repair = OPPORTUNITY_SCHEMA_REPAIR_RELEASE_REFRESH
        origin = load_ledger_at_ref(repair["origin_main"])
        candidate = copy.deepcopy(origin)
        candidate["updated_at"] = "2026-08-12T18:00:00Z"
        candidate["opportunity_schema_repair_release_refresh"] = copy.deepcopy(
            repair
        )
        baseline = load_baseline_bytes_at_ref(repair["origin_main"])
        exact_facts = facts(
            branch=repair["branch"],
            origin_main=repair["origin_main"],
            ahead=1,
            behind=0,
            changed_paths=repair["allowed_surfaces"],
        )
        self.assertTrue(
            _exact_opportunity_schema_repair_release_refresh_matches(
                candidate, exact_facts, repair["package"]
            )
        )
        errors, warnings = self._evaluate_activation(
            candidate,
            exact_facts,
            require_clean=True,
            origin=origin,
            candidate_baseline=baseline,
            origin_baseline=baseline,
        )
        self.assertEqual([], errors)
        self.assertTrue(
            any("schema-repair release" in warning for warning in warnings)
        )
        self.assertEqual(origin["operating_mode"], candidate["operating_mode"])
        self.assertEqual(origin["active_lanes"], candidate["active_lanes"])

        forged = copy.deepcopy(candidate)
        forged["opportunity_schema_repair_release_refresh"][
            "origin_main"
        ] = "0" * 40
        forged_errors, _ = self._evaluate_activation(
            forged,
            exact_facts,
            require_clean=True,
            origin=origin,
            candidate_baseline=baseline,
            origin_baseline=baseline,
        )
        self.assertTrue(forged_errors)

    def test_future_direction_requires_registered_independent_review(self):
        origin, lane, reviewed = self._future_direction_origin()
        candidate = copy.deepcopy(origin)
        candidate_lane = candidate["active_lanes"][0]
        candidate_lane["merge_grant"] = self._future_grant_record(lane, reviewed)
        candidate["operating_mode"]["merge_allowed_for"] = [lane["package"]]
        candidate["updated_at"] = "2026-09-01T20:00:00Z"
        grant_facts = facts(
            branch="work/2026-09-01-delivery-grant-future-direction",
            ahead=1,
            changed_paths=["docs/governance/CURRENT_LANES.json"],
            grant_target_remote_sha=reviewed,
            **self._review_evidence_facts(candidate_lane["merge_grant"]),
        )
        errors, _ = evaluate_policy(
            candidate, grant_facts, lane["package"], "grant",
            require_clean=True, origin_ledger=origin,
            candidate_baseline=self.baseline, origin_baseline=self.baseline,
        )
        self.assertTrue(
            any("no code-controlled independent review attestation" in error
                for error in errors)
        )
        self.assertFalse(
            _exact_direction_grant_delta(origin, candidate, lane["package"])
        )

        self.assertTrue(
            _direction_control_path_sequence_valid([
                {"docs/governance/CURRENT_LANES.json"}
            ])
        )
        self.assertTrue(
            _direction_control_path_sequence_valid([
                set(GRANT_CLOSE_PREFLIGHT_REPAIR["allowed_surfaces"]),
                set(GRANT_CLOSE_FIXTURE_FOLLOWUP["allowed_surfaces"]),
                {"docs/governance/CURRENT_LANES.json"},
            ])
        )
        self.assertTrue(
            _direction_control_path_sequence_valid([
                set(GRANT_CLOSE_FIXTURE_FOLLOWUP["allowed_surfaces"]),
                {"docs/governance/CURRENT_LANES.json"},
            ])
        )
        self.assertFalse(
            _direction_control_path_sequence_valid([
                {"docs/governance/CURRENT_LANES.json", "START_HERE.md"}
            ])
        )
        self.assertFalse(
            _direction_control_path_sequence_valid([
                set(GRANT_CLOSE_PREFLIGHT_REPAIR["allowed_surfaces"])
                - {"START_HERE.md"},
                set(GRANT_CLOSE_FIXTURE_FOLLOWUP["allowed_surfaces"]),
                {"docs/governance/CURRENT_LANES.json"},
            ])
        )
        self.assertFalse(
            _direction_control_path_sequence_valid([
                set(GRANT_CLOSE_PREFLIGHT_REPAIR["allowed_surfaces"]),
                set(GRANT_CLOSE_FIXTURE_FOLLOWUP["allowed_surfaces"])
                - {"tests/test_delivery_preflight.py"},
                {"docs/governance/CURRENT_LANES.json"},
            ])
        )
        self.assertFalse(
            _direction_control_path_sequence_valid([
                set(GRANT_CLOSE_FIXTURE_FOLLOWUP["allowed_surfaces"]),
                set(GRANT_CLOSE_PREFLIGHT_REPAIR["allowed_surfaces"]),
                {"docs/governance/CURRENT_LANES.json"},
            ])
        )

    def test_grant_close_fixture_followup_is_exact_and_inert(self):
        origin = load_ledger_at_ref(GRANT_CLOSE_FIXTURE_FOLLOWUP["origin_main"])
        candidate = copy.deepcopy(origin)
        candidate["updated_at"] = "2026-08-12T07:55:42Z"
        candidate["grant_close_fixture_followup"] = copy.deepcopy(
            GRANT_CLOSE_FIXTURE_FOLLOWUP
        )
        self.assertTrue(
            _exact_grant_close_fixture_followup_delta(origin, candidate)
        )
        immutable_baseline = load_baseline_bytes_at_ref(
            GRANT_CLOSE_FIXTURE_FOLLOWUP["origin_main"]
        )
        exact_facts = facts(
            branch=GRANT_CLOSE_FIXTURE_FOLLOWUP["branch"],
            origin_main=GRANT_CLOSE_FIXTURE_FOLLOWUP["origin_main"],
            ahead=1,
            changed_paths=GRANT_CLOSE_FIXTURE_FOLLOWUP["allowed_surfaces"],
        )
        errors, warnings = self._evaluate_activation(
            candidate, exact_facts, require_clean=True, origin=origin,
            candidate_baseline=immutable_baseline,
            origin_baseline=immutable_baseline,
        )
        self.assertEqual([], errors)
        self.assertTrue(any("fixture-followup" in item for item in warnings))
        forged_authority = copy.deepcopy(candidate)
        forged_authority["operating_mode"]["merge_allowed_for"] = [
            "PS-PROFILE-EXPERIENCE-001"
        ]
        self.assertFalse(
            _exact_grant_close_fixture_followup_delta(origin, forged_authority)
        )
        forged_record = copy.deepcopy(candidate)
        forged_record["grant_close_fixture_followup"]["branch"] = "work/forged"
        self.assertFalse(
            _exact_grant_close_fixture_followup_delta(origin, forged_record)
        )
        stale = copy.deepcopy(candidate)
        stale["updated_at"] = origin["updated_at"]
        self.assertFalse(_exact_grant_close_fixture_followup_delta(origin, stale))

    def test_profile_close_fixture_followup_is_exact_inert_and_fail_closed(self):
        repair = PROFILE_CLOSE_FIXTURE_FOLLOWUP
        origin = load_ledger_at_ref(repair["origin_main"])
        baseline = load_baseline_bytes_at_ref(repair["origin_main"])
        candidate = copy.deepcopy(origin)
        candidate["updated_at"] = "2026-08-12T09:10:06Z"
        candidate["profile_close_fixture_followup"] = copy.deepcopy(repair)
        exact_facts = facts(
            branch=repair["branch"],
            origin_main=repair["origin_main"],
            ahead=1,
            behind=0,
            changed_paths=repair["allowed_surfaces"],
        )

        self.assertTrue(
            _exact_profile_close_fixture_followup_delta(origin, candidate)
        )
        errors, warnings = self._evaluate_activation(
            candidate,
            exact_facts,
            require_clean=True,
            origin=origin,
            candidate_baseline=baseline,
            origin_baseline=baseline,
        )
        self.assertEqual([], errors)
        self.assertTrue(any("Profile close" in item for item in warnings))

        mutations = (
            {"branch": "work/2026-08-12-delivery-activation-wrong"},
            {"origin_main": "f" * 40},
            {"ahead": 0},
            {"ahead": 2},
            {"behind": 1},
            {"changed_paths": repair["allowed_surfaces"][:-1]},
            {"changed_paths": [*repair["allowed_surfaces"], "app.py"]},
        )
        for fact_mutation in mutations:
            with self.subTest(facts=fact_mutation):
                altered = copy.deepcopy(candidate)
                altered_errors, _ = self._evaluate_activation(
                    altered,
                    {**exact_facts, **fact_mutation},
                    require_clean=True,
                    origin=origin,
                    candidate_baseline=baseline,
                    origin_baseline=baseline,
                )
                self.assertTrue(altered_errors)

        def assert_inert_rejected(mutator):
            altered = copy.deepcopy(candidate)
            mutator(altered)
            self.assertFalse(
                _exact_profile_close_fixture_followup_delta(origin, altered)
            )
            altered_errors, _ = self._evaluate_activation(
                altered,
                exact_facts,
                require_clean=True,
                origin=origin,
                candidate_baseline=baseline,
                origin_baseline=baseline,
            )
            self.assertTrue(altered_errors)

        assert_inert_rejected(
            lambda value: value["profile_close_fixture_followup"].__setitem__(
                "branch", "work/forged"
            )
        )
        assert_inert_rejected(
            lambda value: value.__setitem__("updated_at", origin["updated_at"])
        )
        assert_inert_rejected(
            lambda value: value.__setitem__("updated_at", "2026-02-30T09:10:06Z")
        )
        assert_inert_rejected(
            lambda value: value["operating_mode"]["merge_allowed_for"].append(
                "PS-DELIVERY-CONTROL-001"
            )
        )
        assert_inert_rejected(
            lambda value: value["active_lanes"].pop()
        )

        baseline_errors, _ = self._evaluate_activation(
            candidate,
            exact_facts,
            require_clean=True,
            origin=origin,
            candidate_baseline=baseline + b"\n# forged baseline\n",
            origin_baseline=baseline,
        )
        self.assertTrue(
            any("may not change CURRENT_BASELINE" in error for error in baseline_errors)
        )

    def test_profile_close_baseline_fixture_followup_is_exact_and_inert(self):
        repair = PROFILE_CLOSE_BASELINE_FIXTURE_FOLLOWUP
        origin = load_ledger_at_ref(repair["origin_main"])
        baseline = load_baseline_bytes_at_ref(repair["origin_main"])
        candidate = copy.deepcopy(origin)
        candidate["updated_at"] = "2026-08-12T10:06:05Z"
        candidate["profile_close_baseline_fixture_followup"] = copy.deepcopy(
            repair
        )
        exact_facts = facts(
            branch=repair["branch"],
            origin_main=repair["origin_main"],
            ahead=1,
            behind=0,
            changed_paths=repair["allowed_surfaces"],
        )

        self.assertEqual(PROFILE_CLOSE_FIXTURE_FOLLOWUP, origin.get(
            "profile_close_fixture_followup"
        ))
        self.assertTrue(
            _exact_profile_close_baseline_fixture_followup_delta(origin, candidate)
        )
        errors, warnings = self._evaluate_activation(
            candidate,
            exact_facts,
            require_clean=True,
            origin=origin,
            candidate_baseline=baseline,
            origin_baseline=baseline,
        )
        self.assertEqual([], errors)
        self.assertTrue(any("baseline-fixture" in item for item in warnings))

        for fact_mutation in (
            {"branch": "work/forged"},
            {"origin_main": "f" * 40},
            {"ahead": 0},
            {"ahead": 2},
            {"behind": 1},
            {"changed_paths": repair["allowed_surfaces"][:-1]},
            {"changed_paths": [*repair["allowed_surfaces"], "app.py"]},
        ):
            with self.subTest(facts=fact_mutation):
                altered_errors, _ = self._evaluate_activation(
                    candidate,
                    {**exact_facts, **fact_mutation},
                    require_clean=True,
                    origin=origin,
                    candidate_baseline=baseline,
                    origin_baseline=baseline,
                )
                self.assertTrue(altered_errors)

        def assert_inert_rejected(mutator):
            altered = copy.deepcopy(candidate)
            mutator(altered)
            self.assertFalse(
                _exact_profile_close_baseline_fixture_followup_delta(
                    origin, altered
                )
            )
            altered_errors, _ = self._evaluate_activation(
                altered,
                exact_facts,
                require_clean=True,
                origin=origin,
                candidate_baseline=baseline,
                origin_baseline=baseline,
            )
            self.assertTrue(altered_errors)

        assert_inert_rejected(
            lambda value: value[
                "profile_close_baseline_fixture_followup"
            ].__setitem__("branch", "work/forged")
        )
        assert_inert_rejected(
            lambda value: value.__setitem__("updated_at", origin["updated_at"])
        )
        assert_inert_rejected(
            lambda value: value.__setitem__(
                "updated_at", "2026-02-30T10:06:05Z"
            )
        )
        assert_inert_rejected(
            lambda value: value["operating_mode"]["merge_allowed_for"].append(
                "PS-DELIVERY-CONTROL-001"
            )
        )
        assert_inert_rejected(lambda value: value["active_lanes"].pop())

        missing_prior = copy.deepcopy(origin)
        missing_prior.pop("profile_close_fixture_followup")
        self.assertFalse(
            _exact_profile_close_baseline_fixture_followup_delta(
                missing_prior, candidate
            )
        )

        baseline_errors, _ = self._evaluate_activation(
            candidate,
            exact_facts,
            require_clean=True,
            origin=origin,
            candidate_baseline=baseline + b"\n# forged baseline\n",
            origin_baseline=baseline,
        )
        self.assertTrue(
            any("may not change CURRENT_BASELINE" in error for error in baseline_errors)
        )

    def test_opportunity_lifecycle_fixture_repair_is_exact_and_inert(self):
        repair = OPPORTUNITY_LIFECYCLE_FIXTURE_REPAIR
        origin = load_ledger_at_ref(repair["origin_main"])
        baseline = load_baseline_bytes_at_ref(repair["origin_main"])
        candidate = copy.deepcopy(origin)
        candidate["updated_at"] = "2026-08-12T16:20:00Z"
        candidate["opportunity_lifecycle_fixture_repair"] = copy.deepcopy(
            repair
        )
        exact_facts = facts(
            branch=repair["branch"],
            origin_main=repair["origin_main"],
            ahead=1,
            behind=0,
            changed_paths=repair["allowed_surfaces"],
        )

        self.assertTrue(
            _exact_opportunity_lifecycle_fixture_repair_delta(origin, candidate)
        )
        errors, warnings = self._evaluate_activation(
            candidate,
            exact_facts,
            require_clean=True,
            origin=origin,
            candidate_baseline=baseline,
            origin_baseline=baseline,
        )
        self.assertEqual([], errors)
        self.assertTrue(any("Opportunity lifecycle" in item for item in warnings))

        for fact_mutation in (
            {"branch": "work/forged"},
            {"origin_main": "f" * 40},
            {"ahead": 0},
            {"ahead": 2},
            {"behind": 1},
            {"changed_paths": repair["allowed_surfaces"][:-1]},
            {"changed_paths": [*repair["allowed_surfaces"], "app.py"]},
        ):
            with self.subTest(facts=fact_mutation):
                altered_errors, _ = self._evaluate_activation(
                    candidate,
                    {**exact_facts, **fact_mutation},
                    require_clean=True,
                    origin=origin,
                    candidate_baseline=baseline,
                    origin_baseline=baseline,
                )
                self.assertTrue(altered_errors)

        for mutator in (
            lambda value: value[
                "opportunity_lifecycle_fixture_repair"
            ].__setitem__("branch", "work/forged"),
            lambda value: value.__setitem__("updated_at", origin["updated_at"]),
            lambda value: value["operating_mode"]["merge_allowed_for"].append(
                "PS-DELIVERY-CONTROL-001"
            ),
        ):
            altered = copy.deepcopy(candidate)
            mutator(altered)
            self.assertFalse(
                _exact_opportunity_lifecycle_fixture_repair_delta(origin, altered)
            )
            altered_errors, _ = self._evaluate_activation(
                altered,
                exact_facts,
                require_clean=True,
                origin=origin,
                candidate_baseline=baseline,
                origin_baseline=baseline,
            )
            self.assertTrue(altered_errors)

        baseline_errors, _ = self._evaluate_activation(
            candidate,
            exact_facts,
            require_clean=True,
            origin=origin,
            candidate_baseline=baseline + b"\n# forged baseline\n",
            origin_baseline=baseline,
        )
        self.assertTrue(
            any("may not change CURRENT_BASELINE" in error for error in baseline_errors)
        )

    def test_opportunity_resume_fixture_repair_is_exact_and_inert(self):
        repair = OPPORTUNITY_RESUME_FIXTURE_REPAIR
        origin = load_ledger_at_ref(repair["origin_main"])
        baseline = load_baseline_bytes_at_ref(repair["origin_main"])
        candidate = copy.deepcopy(origin)
        candidate["updated_at"] = "2026-08-12T16:50:00Z"
        candidate["opportunity_resume_fixture_repair"] = copy.deepcopy(repair)
        exact_facts = facts(
            branch=repair["branch"],
            origin_main=repair["origin_main"],
            ahead=1,
            behind=0,
            changed_paths=repair["allowed_surfaces"],
        )

        self.assertTrue(
            _exact_opportunity_resume_fixture_repair_delta(origin, candidate)
        )
        errors, warnings = self._evaluate_activation(
            candidate,
            exact_facts,
            require_clean=True,
            origin=origin,
            candidate_baseline=baseline,
            origin_baseline=baseline,
        )
        self.assertEqual([], errors)
        self.assertTrue(any("Opportunity resume" in item for item in warnings))

        for fact_mutation in (
            {"branch": "work/forged"},
            {"origin_main": "f" * 40},
            {"ahead": 0},
            {"ahead": 2},
            {"behind": 1},
            {"changed_paths": repair["allowed_surfaces"][:-1]},
            {"changed_paths": [*repair["allowed_surfaces"], "app.py"]},
        ):
            with self.subTest(facts=fact_mutation):
                altered_errors, _ = self._evaluate_activation(
                    candidate,
                    {**exact_facts, **fact_mutation},
                    require_clean=True,
                    origin=origin,
                    candidate_baseline=baseline,
                    origin_baseline=baseline,
                )
                self.assertTrue(altered_errors)

        altered = copy.deepcopy(candidate)
        altered["operating_mode"]["merge_allowed_for"].append(
            "PS-DELIVERY-CONTROL-001"
        )
        self.assertFalse(
            _exact_opportunity_resume_fixture_repair_delta(origin, altered)
        )
        altered_errors, _ = self._evaluate_activation(
            altered,
            exact_facts,
            require_clean=True,
            origin=origin,
            candidate_baseline=baseline,
            origin_baseline=baseline,
        )
        self.assertTrue(altered_errors)

        baseline_errors, _ = self._evaluate_activation(
            candidate,
            exact_facts,
            require_clean=True,
            origin=origin,
            candidate_baseline=baseline + b"\n# forged baseline\n",
            origin_baseline=baseline,
        )
        self.assertTrue(
            any("may not change CURRENT_BASELINE" in error for error in baseline_errors)
        )

    def test_opportunity_close_introduction_repair_is_exact_and_inert(self):
        repair = OPPORTUNITY_CLOSE_INTRODUCTION_REPAIR
        origin = load_ledger_at_ref(repair["origin_main"])
        baseline = load_baseline_bytes_at_ref(repair["origin_main"])
        candidate = copy.deepcopy(origin)
        candidate["updated_at"] = "2026-08-12T19:02:00Z"
        candidate["opportunity_close_introduction_repair"] = copy.deepcopy(repair)
        exact_facts = facts(
            branch=repair["branch"],
            origin_main=repair["origin_main"],
            ahead=1,
            behind=0,
            changed_paths=repair["allowed_surfaces"],
        )

        self.assertTrue(
            _exact_opportunity_close_introduction_repair_delta(origin, candidate)
        )
        errors, warnings = self._evaluate_activation(
            candidate,
            exact_facts,
            require_clean=True,
            origin=origin,
            candidate_baseline=baseline,
            origin_baseline=baseline,
        )
        self.assertEqual([], errors)
        self.assertTrue(any("close-introduction" in item for item in warnings))

        for fact_mutation in (
            {"branch": "work/forged"},
            {"origin_main": "f" * 40},
            {"ahead": 0},
            {"ahead": 2},
            {"behind": 1},
            {"changed_paths": repair["allowed_surfaces"][:-1]},
            {"changed_paths": [*repair["allowed_surfaces"], "app.py"]},
        ):
            with self.subTest(facts=fact_mutation):
                altered_errors, _ = self._evaluate_activation(
                    candidate,
                    {**exact_facts, **fact_mutation},
                    require_clean=True,
                    origin=origin,
                    candidate_baseline=baseline,
                    origin_baseline=baseline,
                )
                self.assertTrue(altered_errors)

        altered = copy.deepcopy(candidate)
        altered["operating_mode"]["merge_allowed_for"].append(
            "PS-DELIVERY-CONTROL-001"
        )
        self.assertFalse(
            _exact_opportunity_close_introduction_repair_delta(origin, altered)
        )
        altered_errors, _ = self._evaluate_activation(
            altered,
            exact_facts,
            require_clean=True,
            origin=origin,
            candidate_baseline=baseline,
            origin_baseline=baseline,
        )
        self.assertTrue(altered_errors)

        baseline_errors, _ = self._evaluate_activation(
            candidate,
            exact_facts,
            require_clean=True,
            origin=origin,
            candidate_baseline=baseline + b"\n# forged baseline\n",
            origin_baseline=baseline,
        )
        self.assertTrue(
            any("may not change CURRENT_BASELINE" in error for error in baseline_errors)
        )

    def test_profile_close_absent_surface_repair_is_exact_and_inert(self):
        repair = PROFILE_CLOSE_ABSENT_SURFACE_REPAIR
        origin = load_ledger_at_ref(repair["origin_main"])
        baseline = load_baseline_bytes_at_ref(repair["origin_main"])
        self.assertNotIn("profile_close_absent_surface_repair", origin)
        candidate = copy.deepcopy(origin)
        candidate["updated_at"] = "2026-08-13T05:34:44Z"
        candidate["profile_close_absent_surface_repair"] = copy.deepcopy(repair)
        exact_facts = facts(
            branch=repair["branch"],
            origin_main=repair["origin_main"],
            ahead=1,
            behind=0,
            changed_paths=repair["allowed_surfaces"],
        )
        self.assertTrue(
            _exact_profile_close_absent_surface_repair_matches(
                candidate, exact_facts, repair["package"]
            )
        )
        self.assertTrue(
            _exact_profile_close_absent_surface_repair_delta(origin, candidate)
        )
        errors, warnings = self._evaluate_activation(
            candidate,
            exact_facts,
            require_clean=True,
            origin=origin,
            candidate_baseline=baseline,
            origin_baseline=baseline,
        )
        self.assertEqual([], errors)
        self.assertTrue(any("absent-surface repair" in item for item in warnings))
        self.assertEqual(origin["operating_mode"], candidate["operating_mode"])
        self.assertEqual(origin["active_lanes"], candidate["active_lanes"])

        for fact_mutation in (
            {"branch": "work/forged"},
            {"origin_main": "f" * 40},
            {"ahead": 0},
            {"ahead": 2},
            {"behind": 1},
            {"changed_paths": repair["allowed_surfaces"][:-1]},
            {"changed_paths": [*repair["allowed_surfaces"], "app.py"]},
        ):
            with self.subTest(facts=fact_mutation):
                altered_errors, _ = self._evaluate_activation(
                    candidate,
                    {**exact_facts, **fact_mutation},
                    require_clean=True,
                    origin=origin,
                    candidate_baseline=baseline,
                    origin_baseline=baseline,
                )
                self.assertTrue(altered_errors)

        for timestamp in (
            origin["updated_at"],
            "2026-08-13T04:20:59Z",
            "not-a-timestamp",
        ):
            with self.subTest(timestamp=timestamp):
                altered = copy.deepcopy(candidate)
                altered["updated_at"] = timestamp
                altered_errors, _ = self._evaluate_activation(
                    altered,
                    exact_facts,
                    require_clean=True,
                    origin=origin,
                    candidate_baseline=baseline,
                    origin_baseline=baseline,
                )
                self.assertTrue(altered_errors)

        for label, mutate in (
            (
                "authority-smuggling",
                lambda value: value["operating_mode"]["release_allowed_for"].append(
                    PROFILE_CORE_INTEGRATION_PACKAGE
                ),
            ),
            (
                "active-lane-mutation",
                lambda value: value["active_lanes"][0].__setitem__(
                    "branch", "work/forged-shell"
                ),
            ),
        ):
            with self.subTest(label=label):
                altered = copy.deepcopy(candidate)
                mutate(altered)
                altered_errors, _ = self._evaluate_activation(
                    altered,
                    exact_facts,
                    require_clean=True,
                    origin=origin,
                    candidate_baseline=baseline,
                    origin_baseline=baseline,
                )
                self.assertTrue(altered_errors)

        baseline_errors, _ = self._evaluate_activation(
            candidate,
            exact_facts,
            require_clean=True,
            origin=origin,
            candidate_baseline=baseline + b"\n# forged baseline\n",
            origin_baseline=baseline,
        )
        self.assertTrue(baseline_errors)

        preexisting_origin = copy.deepcopy(candidate)
        preexisting_origin["updated_at"] = "2026-08-13T05:35:00Z"
        reused = copy.deepcopy(preexisting_origin)
        reused["updated_at"] = "2026-08-13T05:36:00Z"
        reused_errors, _ = self._evaluate_activation(
            reused,
            exact_facts,
            require_clean=True,
            origin=preexisting_origin,
            candidate_baseline=baseline,
            origin_baseline=baseline,
        )
        self.assertTrue(reused_errors)

    def test_profile_close_object_id_repair_is_exact_and_inert(self):
        repair = PROFILE_CLOSE_OBJECT_ID_REPAIR
        origin = load_ledger_at_ref(repair["origin_main"])
        baseline = load_baseline_bytes_at_ref(repair["origin_main"])
        self.assertEqual(
            PROFILE_CLOSE_ABSENT_SURFACE_REPAIR,
            origin.get("profile_close_absent_surface_repair"),
        )
        self.assertNotIn("profile_close_object_id_repair", origin)
        self.assertEqual(
            repair, self.ledger.get("profile_close_object_id_repair")
        )
        candidate = copy.deepcopy(origin)
        candidate["updated_at"] = "2026-08-13T06:07:18Z"
        candidate["profile_close_object_id_repair"] = copy.deepcopy(repair)
        exact_facts = facts(
            branch=repair["branch"],
            origin_main=repair["origin_main"],
            ahead=1,
            behind=0,
            changed_paths=repair["allowed_surfaces"],
        )
        self.assertTrue(
            _exact_profile_close_object_id_repair_matches(
                candidate, exact_facts, repair["package"]
            )
        )
        self.assertTrue(
            _exact_profile_close_object_id_repair_delta(origin, candidate)
        )
        errors, warnings = self._evaluate_activation(
            candidate,
            exact_facts,
            require_clean=True,
            origin=origin,
            candidate_baseline=baseline,
            origin_baseline=baseline,
        )
        self.assertEqual([], errors)
        self.assertTrue(any("object-ID repair" in item for item in warnings))
        self.assertEqual(origin["operating_mode"], candidate["operating_mode"])
        self.assertEqual(origin["active_lanes"], candidate["active_lanes"])

        for fact_mutation in (
            {"branch": "work/forged"},
            {"origin_main": "f" * 40},
            {"ahead": 0},
            {"ahead": 2},
            {"behind": 1},
            {"changed_paths": repair["allowed_surfaces"][:-1]},
            {"changed_paths": [*repair["allowed_surfaces"], "app.py"]},
        ):
            with self.subTest(facts=fact_mutation):
                altered_errors, _ = self._evaluate_activation(
                    candidate,
                    {**exact_facts, **fact_mutation},
                    require_clean=True,
                    origin=origin,
                    candidate_baseline=baseline,
                    origin_baseline=baseline,
                )
                self.assertTrue(altered_errors)

        for timestamp in (
            origin["updated_at"],
            "2026-08-13T05:34:43Z",
            "not-a-timestamp",
        ):
            with self.subTest(timestamp=timestamp):
                altered = copy.deepcopy(candidate)
                altered["updated_at"] = timestamp
                altered_errors, _ = self._evaluate_activation(
                    altered,
                    exact_facts,
                    require_clean=True,
                    origin=origin,
                    candidate_baseline=baseline,
                    origin_baseline=baseline,
                )
                self.assertTrue(altered_errors)

        altered = copy.deepcopy(candidate)
        altered["operating_mode"]["release_allowed_for"].append(
            PROFILE_CORE_INTEGRATION_PACKAGE
        )
        altered_errors, _ = self._evaluate_activation(
            altered,
            exact_facts,
            require_clean=True,
            origin=origin,
            candidate_baseline=baseline,
            origin_baseline=baseline,
        )
        self.assertTrue(altered_errors)

        baseline_errors, _ = self._evaluate_activation(
            candidate,
            exact_facts,
            require_clean=True,
            origin=origin,
            candidate_baseline=baseline + b"\n# forged baseline\n",
            origin_baseline=baseline,
        )
        self.assertTrue(baseline_errors)

        replay_parent = copy.deepcopy(candidate)
        replay_parent["updated_at"] = "2026-08-13T06:08:00Z"
        replay = copy.deepcopy(replay_parent)
        replay["updated_at"] = "2026-08-13T06:09:00Z"
        replay_errors, _ = self._evaluate_activation(
            replay,
            exact_facts,
            require_clean=True,
            origin=replay_parent,
            candidate_baseline=baseline,
            origin_baseline=baseline,
        )
        self.assertTrue(replay_errors)

    def test_profile_close_object_ids_normalize_real_absence_before_close_facts(self):
        reviewed = PROFILE_CORE_INTEGRATION_REVIEWED_SHA
        package_merge = "f0fe066751a83fc7c0ba32a88d55b1d42a3a46f2"
        captured_main = PROFILE_CLOSE_OBJECT_ID_REPAIR["origin_main"]
        lane = next(
            item
            for item in load_ledger_at_ref(captured_main)["active_lanes"]
            if item.get("package") == PROFILE_CORE_INTEGRATION_PACKAGE
        )
        missing = "docs/initiatives/PS-PROFILE-CORE-INTEGRATION-001/"
        self.assertIn(missing, lane["writable_surfaces"])
        existing_ids = (
            _git_object_id_at(reviewed, "profile_routes.py"),
            _git_object_id_at(package_merge, "profile_routes.py"),
            _git_object_id_at(captured_main, "profile_routes.py"),
        )
        self.assertEqual(
            ("1fb2ded672800866ad63e165024f16a22bab5114",) * 3,
            existing_ids,
        )
        missing_ids = (
            _git_object_id_at(reviewed, missing),
            _git_object_id_at(package_merge, missing),
            _git_object_id_at(captured_main, missing),
        )
        self.assertEqual(("", "", ""), missing_ids)
        self.assertTrue(_close_surface_tree_equivalent(*missing_ids))

        comparisons = []
        introduction_checks = []
        for surface in lane["writable_surfaces"]:
            candidate_id = _git_object_id_at(reviewed, surface)
            merge_id = _git_object_id_at(package_merge, surface)
            main_id = _git_object_id_at(captured_main, surface)
            comparisons.append(
                _close_surface_tree_equivalent(candidate_id, merge_id, main_id)
            )
            parent_id = _git_object_id_at(f"{package_merge}^", surface)
            introduction_checks.append(
                bool(candidate_id)
                and candidate_id == merge_id
                and parent_id != merge_id
            )
        self.assertTrue(all(comparisons))
        self.assertTrue(_candidate_surface_introduction_proven(introduction_checks))

    def test_close_surface_tree_equivalence_accepts_only_exact_three_way_state(self):
        self.assertTrue(_close_surface_tree_equivalent("tree-a", "tree-a", "tree-a"))
        self.assertTrue(_close_surface_tree_equivalent("", "", ""))
        for values in (
            ("", "tree-a", "tree-a"),
            ("tree-a", "", "tree-a"),
            ("tree-a", "tree-a", ""),
            ("tree-a", "tree-b", "tree-a"),
            (None, None, None),
            ("", None, ""),
        ):
            with self.subTest(values=values):
                self.assertFalse(_close_surface_tree_equivalent(*values))

    def test_profile_close_real_merge_surface_reproduces_equivalence_and_introduction(self):
        reviewed = PROFILE_CORE_INTEGRATION_REVIEWED_SHA
        merged = "f0fe066751a83fc7c0ba32a88d55b1d42a3a46f2"
        lane = next(
            item
            for item in load_ledger_at_ref(merged)["active_lanes"]
            if item.get("package") == PROFILE_CORE_INTEGRATION_PACKAGE
        )
        missing = "docs/initiatives/PS-PROFILE-CORE-INTEGRATION-001/"
        self.assertIn(missing, lane["writable_surfaces"])
        self.assertEqual(reviewed, lane["merge_grant"]["reviewed_remote_sha"])

        def read_tree(ref: str, surface: str) -> str:
            result = subprocess.run(
                ["git", "-C", str(ROOT), "rev-parse", f"{ref}:{surface.rstrip('/')}"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            return result.stdout.strip() if result.returncode == 0 else ""

        merge_tree = read_tree(merged, missing)
        main_tree = read_tree(merged, missing)
        self.assertEqual("", merge_tree)
        self.assertEqual("", main_tree)
        self.assertTrue(
            _close_surface_tree_equivalent("", merge_tree, main_tree)
        )

        # Azure's squash merge may leave a main-only checkout without the
        # source-branch commit object. The actual close command exact-fetches
        # `reviewed`; this repository fixture uses the verified candidate-
        # equivalent package-merge objects so it remains independent of that
        # checkout detail while reproducing the real missing directory.
        comparisons = []
        introduction_checks = []
        for surface in lane["writable_surfaces"]:
            merge_tree = read_tree(merged, surface)
            main_tree = read_tree(merged, surface)
            parent_tree = read_tree(f"{merged}^", surface)
            comparisons.append(
                _close_surface_tree_equivalent(
                    merge_tree, merge_tree, main_tree
                )
            )
            introduction_checks.append(
                bool(merge_tree)
                and parent_tree != merge_tree
            )
        self.assertTrue(all(comparisons))
        self.assertTrue(_candidate_surface_introduction_proven(introduction_checks))
        self.assertFalse(_candidate_surface_introduction_proven([False]))

    def test_close_introduction_requires_at_least_one_changed_surface(self):
        self.assertTrue(_candidate_surface_introduction_proven([False, True]))
        self.assertTrue(_candidate_surface_introduction_proven([True, True]))
        self.assertFalse(_candidate_surface_introduction_proven([False, False]))
        self.assertFalse(_candidate_surface_introduction_proven([]))
        self.assertFalse(_candidate_surface_introduction_proven([True, 1]))

    def test_grant_rejects_negation_weak_or_forged_review_and_bad_commit_count(self):
        origin, lane = self._direction_origin()
        reviewed = PROFILE_DIRECTION_REVIEW_ATTESTATION["reviewed_sha"]
        candidate = copy.deepcopy(origin)
        candidate_lane = candidate["active_lanes"][0]
        candidate_lane["merge_grant"] = self._grant_record(lane, reviewed)
        candidate["operating_mode"]["merge_allowed_for"] = [lane["package"]]
        candidate["updated_at"] = "2026-08-12T03:00:00Z"
        base_facts = facts(
            branch="work/2026-08-12-delivery-grant-profile-direction",
            ahead=1,
            changed_paths=["docs/governance/CURRENT_LANES.json"],
            grant_target_remote_sha=reviewed,
            **self._review_evidence_facts(candidate_lane["merge_grant"]),
        )

        negated_origin = copy.deepcopy(origin)
        negated_origin["active_lanes"][0]["owner_decisions"][0]["decision"] = (
            "Pete does not authorize this package to merge."
        )
        negated = copy.deepcopy(candidate)
        negated["active_lanes"][0]["owner_decisions"] = copy.deepcopy(
            negated_origin["active_lanes"][0]["owner_decisions"]
        )
        negated["active_lanes"][0]["merge_grant"]["authority_decision_sha256"] = (
            _canonical_sha256(negated["active_lanes"][0]["owner_decisions"][0])
        )
        negated_errors, _ = evaluate_policy(
            negated, base_facts, lane["package"], "grant",
            require_clean=True, origin_ledger=negated_origin,
            candidate_baseline=self.baseline, origin_baseline=self.baseline,
        )
        self.assertTrue(any("affirmative merge" in error for error in negated_errors))

        for mutation, expected in (
            ({"ahead": 0}, "exactly one commit"),
            ({"ahead": 2}, "exactly one commit"),
            ({"grant_target_remote_sha": "f" * 40}, "fetched target branch tip"),
            ({"grant_review_evidence": [{
                **base_facts["grant_review_evidence"][0], "object_mode": "120000"
            }]}, "regular Markdown blob"),
            ({"grant_review_evidence": [{
                **base_facts["grant_review_evidence"][0], "content": ""
            }]}, "non-empty UTF-8"),
        ):
            with self.subTest(mutation=mutation):
                mutated_errors, _ = evaluate_policy(
                    candidate, {**base_facts, **mutation}, lane["package"], "grant",
                    require_clean=True, origin_ledger=origin,
                    candidate_baseline=self.baseline, origin_baseline=self.baseline,
                )
                self.assertTrue(any(expected in error for error in mutated_errors))

        forged = copy.deepcopy(candidate)
        forged_review = forged["active_lanes"][0]["merge_grant"]["independent_review"]
        forged_review["reviewer_task"] = "/root/candidate_writer_claim"
        attestation = dict(forged_review)
        attestation.pop("attestation_sha256")
        forged_review["attestation_sha256"] = _canonical_sha256(attestation)
        forged_errors, _ = evaluate_policy(
            forged, base_facts, lane["package"], "grant",
            require_clean=True, origin_ledger=origin,
            candidate_baseline=self.baseline, origin_baseline=self.baseline,
        )
        self.assertTrue(any("code-controlled attestation" in error for error in forged_errors))

        traversal = copy.deepcopy(candidate)
        traversal["active_lanes"][0]["merge_grant"]["review_evidence_paths"] = [
            "docs/initiatives/PS-PROFILE-EXPERIENCE-001/../secret.md"
        ]
        traversal_errors, _ = evaluate_policy(
            traversal, base_facts, lane["package"], "grant",
            require_clean=True, origin_ledger=origin,
            candidate_baseline=self.baseline, origin_baseline=self.baseline,
        )
        self.assertTrue(any("normalized repository-relative" in error for error in traversal_errors))

    def test_merge_authority_rejects_free_prose_and_requires_exact_structure(self):
        origin, lane = self._direction_origin()
        self.assertTrue(
            _affirmative_merge_decision(
                lane["owner_decisions"][0], lane["package"]
            )
        )
        for prose in (
            "Pete will authorize merge after review passes",
            "Pete might authorize merge",
            "Pete discussed whether to authorize merge",
            "Pete authorized merge if architecture changes later",
            "Pete formerly authorized merge, but withdrew it",
        ):
            with self.subTest(prose=prose):
                self.assertFalse(
                    _affirmative_merge_decision(
                        {"date": "2026-09-01", "decision": prose},
                        "PS-FUTURE-DIRECTION-001",
                    )
                )
        future_origin, future_lane, _ = self._future_direction_origin()
        self.assertTrue(
            _affirmative_merge_decision(
                future_origin["active_lanes"][0]["owner_decisions"][0],
                future_lane["package"],
            )
        )

    def _one_lane_origin(self) -> dict:
        """Build the stable one-lane origin required by 1->2 tests.

        These transition tests validate the standing one-to-two activation
        contract.  They must not inherit a second lane that happens to be
        recorded in the checked-in repository while an unrelated activation
        PR is under review.
        """
        origin = copy.deepcopy(self.ledger)
        active_lanes = list(origin.get("active_lanes") or [])
        target_lane = self._interview_lane()
        target_package = target_lane["package"]
        target_surfaces = {
            surface.replace("\\", "/").rstrip("/").casefold()
            for surface in target_lane["writable_surfaces"]
        }

        def is_disjoint(lane: dict) -> bool:
            lane_surfaces = {
                surface.replace("\\", "/").rstrip("/").casefold()
                for surface in lane.get("writable_surfaces", [])
            }
            return not any(
                left == right
                or left.startswith(right + "/")
                or right.startswith(left + "/")
                for left in lane_surfaces
                for right in target_surfaces
            )

        retained = next(
            (
                lane
                for lane in active_lanes
                if lane.get("package") != target_package and is_disjoint(lane)
            ),
            None,
        )
        if retained is None:
            retained = self._lane("PS-DELIVERY-PREFLIGHT-ORIGIN-001")
        origin["active_lanes"] = [copy.deepcopy(retained)]
        retained_package = retained["package"]
        origin["operating_mode"]["state"] = "active_delivery"
        origin["operating_mode"]["writes_allowed_for"] = [retained_package]
        origin["operating_mode"]["release_allowed_for"] = [
            package
            for package in origin["operating_mode"].get(
                "release_allowed_for", []
            )
            if package == retained_package
        ]
        return origin

    def _inactive_package(self) -> str:
        """A package the current ledger does not permit writes for."""
        engaged = {
            lane["package"]
            for lane in list(self.ledger.get("active_lanes") or [])
            + list(self.ledger.get("closing_lanes") or [])
        }
        for lane in self.ledger.get("paused_lanes") or []:
            if lane["package"] not in engaged:
                return lane["package"]
        return "PS-NOT-AN-ACTIVE-LANE-001"

    @staticmethod
    def _lane(package: str) -> dict:
        return {
            "package": package,
            "outcome": f"Deliver the bounded {package} outcome.",
            "branch": f"work/{package.lower()}",
            "writer": "Test writer",
            "delivery_path": "Bounded",
            "lane_class": "implementation",
            "production_capable": False,
            "exclusive_domains": [f"product:{package.lower()}"],
            "writable_surfaces": [f"docs/initiatives/{package}/"],
            "exclusions": ["no outside writes"],
            "completion_evidence": ["Focused package verification passes"],
        }

    def _activation_candidate(self, origin: dict, package: str) -> dict:
        candidate = copy.deepcopy(origin)
        candidate["active_lanes"].append(self._lane(package))
        candidate["operating_mode"]["state"] = "active_delivery"
        candidate["operating_mode"]["writes_allowed_for"] = [
            lane["package"] for lane in candidate["active_lanes"]
        ]
        return candidate

    def _pause_candidate(self, origin: dict, package: str) -> dict:
        candidate = copy.deepcopy(origin)
        target = next(
            lane for lane in origin["active_lanes"] if lane["package"] == package
        )
        candidate["updated_at"] = "2026-08-10T18:00:00Z"
        candidate["active_lanes"] = [
            lane for lane in origin["active_lanes"] if lane["package"] != package
        ]
        candidate["operating_mode"]["state"] = (
            "active_delivery" if candidate["active_lanes"] else "controlled_idle"
        )
        candidate["operating_mode"]["writes_allowed_for"] = [
            lane["package"] for lane in candidate["active_lanes"]
        ]
        for field in ("merge_allowed_for", "cleanup_allowed_for", "release_allowed_for"):
            candidate["operating_mode"][field] = [
                value
                for value in candidate["operating_mode"].get(field, [])
                if value != package
            ]
        candidate["operating_mode"]["exit_authority"] = (
            f"{package} is paused and preserved; resume requires fresh activation."
        )
        candidate["paused_lanes"].append(
            {
                **copy.deepcopy(target),
                "disposition": "paused_preserved",
                "paused_at": "2026-08-10T18:00:00Z",
                "pause_reason": "The writer is waiting and relinquished capacity.",
                "resume_contract": "Resume through a fresh activation and collision check.",
                "preserved_head_sha": "a" * 40,
            }
        )
        return candidate

    def _pause_baselines(self, origin: dict, package: str) -> tuple[bytes, bytes]:
        origin_baseline = self._baseline_for_origin(origin)
        source = origin_baseline.decode("utf-8")
        remaining = [
            lane for lane in origin["active_lanes"] if lane["package"] != package
        ]
        assignment = _expected_pause_manager_assignment(package, remaining)
        next_gate = _expected_pause_next_gate(package, remaining)
        candidate = re.sub(
            r'^  current_assignments: .+$',
            f'  current_assignments: {json.dumps(assignment)}',
            source,
            count=1,
            flags=re.MULTILINE,
        )
        candidate = re.sub(
            rf"(?ms)^  - id: {re.escape(package)}\n.*?(?=^  - id: |^scoped_findings:\n)",
            "",
            candidate,
            count=1,
        )
        candidate = re.sub(
            r'^next_gate: .+$',
            f'next_gate: {json.dumps(next_gate)}',
            candidate,
            count=1,
            flags=re.MULTILINE,
        )
        candidate = re.sub(
            r'^updated_at: .+$',
            'updated_at: "2026-08-10"',
            candidate,
            count=1,
            flags=re.MULTILINE,
        )
        return origin_baseline, candidate.encode("utf-8")

    @staticmethod
    def _interview_lane() -> dict:
        """The actual approved 1->2 Interview Studio activation record shape."""
        return {
            "package": "PS-INTERVIEW-STUDIO-CALIBRATION-001",
            "outcome": (
                "Calibrate the released public Interview Studio visual system "
                "without changing behavior."
            ),
            "branch": "work/2026-08-06-interview-studio-calibration-001",
            "writer": "Terra in the dedicated clean worktree",
            "delivery_path": "Protected",
            "lane_class": "implementation",
            "production_capable": False,
            "exclusive_domains": ["product:interview-studio"],
            "source_checkpoint": "Locked owner visual authority.",
            "writable_surfaces": [
                "templates/interview_studio.html",
                "static/css/interview-studio.css",
                "static/js/interview-studio.js",
                "tests/test_interview_studio.py",
                "docs/initiatives/PS-INTERVIEW-STUDIO-CALIBRATION-001/",
            ],
            "exclusions": [
                "no route, backend, schema, storage, authentication, or deployment change",
                "no work outside the five listed surfaces",
            ],
            "completion_evidence": [
                "write preflight and visual-integrity validation pass"
            ],
        }

    def _interview_activation_candidate(self, origin: dict) -> dict:
        candidate = copy.deepcopy(origin)
        lane = self._interview_lane()
        candidate["active_lanes"].append(lane)
        candidate["operating_mode"]["state"] = "active_delivery"
        candidate["operating_mode"]["writes_allowed_for"] = [
            *origin["operating_mode"]["writes_allowed_for"],
            lane["package"],
        ]
        candidate["operating_mode"]["exit_authority"] = (
            "Two bounded non-production lanes include "
            "PS-INTERVIEW-STUDIO-CALIBRATION-001; neither may merge or deploy."
        )
        return candidate

    @staticmethod
    def _has_affirmative_owner_merge_decision(lane: dict, package: str) -> bool:
        decisions = lane.get("owner_decisions")
        if not isinstance(decisions, list):
            return False
        for decision in decisions:
            if not isinstance(decision, dict):
                continue
            text = decision.get("decision")
            if not isinstance(text, str):
                continue
            normalized = " ".join(text.casefold().split())
            normalized_words = " ".join(
                part for part in re.split(r"[^a-z0-9]+", text.casefold()) if part
            )
            negated = any(
                phrase in normalized_words
                for phrase in (
                    "does not authorize",
                    "not authorized",
                    "not grant",
                    "no merge",
                    "merge denied",
                    "merge rejected",
                    "merge withdrawn",
                )
            )
            structured_grant = bool(
                not negated
                and decision.get("authorized_by") == "Pete"
                and decision.get("status") == "authorized"
                and decision.get("package") == package
                and isinstance(decision.get("action"), str)
                and decision["action"].casefold().startswith("merge")
                and "merge" in normalized_words
                and "authority" in normalized_words
            )
            recorded_grant = bool(
                normalized.startswith("merge grant")
                and "authorizes adding the package to merge_allowed_for"
                in normalized
            )
            if structured_grant or recorded_grant:
                return True
        return False

    def _lane_fixture(self, parsed: dict, lane_class: str = "implementation") -> dict:
        """Return a real recorded lane to use as a fixture template.

        These tests need a lane shaped like a production one and then replace
        ``active_lanes`` with their own mutated copy. ``controlled_idle`` is a
        supported operating state with no active lanes, so search the
        preserved and closed records too instead of depending on a lane being
        active at the moment the suite runs.
        """
        for key in ("active_lanes", "paused_lanes", "closing_lanes"):
            for lane in parsed.get(key) or []:
                if not isinstance(lane, dict):
                    continue
                if lane.get("lane_class") != lane_class:
                    continue
                if lane.get("branch") and lane.get("writable_surfaces"):
                    return lane
        raise AssertionError(f"the ledger records no {lane_class} lane fixture")

    def _assert_valid_merge_authorities(self, parsed: dict) -> None:
        mode = parsed["operating_mode"]
        active_by_package = {
            lane["package"]: lane for lane in parsed["active_lanes"]
        }
        self.assertEqual(
            len(mode["merge_allowed_for"]),
            len(set(mode["merge_allowed_for"])),
        )
        for package in mode["merge_allowed_for"]:
            lane = active_by_package.get(package)
            self.assertIsNotNone(lane)
            lane_class = lane.get("lane_class")
            if (
                lane_class == "direction_authority"
                or _is_profile_core_reviewed_implementation_lane(lane)
                or _is_connect_002_reviewed_implementation_lane(lane)
                or _is_shell_reviewed_shared_foundation_lane(lane)
            ):
                self.assertFalse(lane.get("production_capable"))
                grant = lane.get("merge_grant")
                self.assertIsInstance(grant, dict)
                grant_errors: list[str] = []
                self.assertIsNotNone(
                    _direction_merge_grant(
                        lane, "checked-in temporary merge authority", grant_errors
                    )
                )
                self.assertEqual([], grant_errors)
                ledger_updated = datetime.strptime(
                    parsed["updated_at"], "%Y-%m-%dT%H:%M:%SZ"
                )
                grant_created = datetime.strptime(
                    grant["granted_at"], "%Y-%m-%dT%H:%M:%SZ"
                )
                self.assertLessEqual(grant_created, ledger_updated)
            else:
                self.assertIn(lane_class, {"implementation", "shared_foundation"})
                self.assertTrue(
                    self._has_affirmative_owner_merge_decision(lane, package)
                )

    def test_lane_ledger_has_a_valid_operating_state(self):
        parsed = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(2, parsed["schema_version"])
        mode = parsed["operating_mode"]
        active = parsed["active_lanes"]
        closing = parsed["closing_lanes"]
        active_packages = {lane["package"] for lane in active}
        closable_packages = active_packages | {
            lane["package"] for lane in closing
        }
        self.assertIn(mode["state"], {"controlled_idle", "active_delivery"})
        self.assertLessEqual(len(active), 3)
        self.assertEqual(set(mode["writes_allowed_for"]), active_packages)
        self.assertLessEqual(set(mode["merge_allowed_for"]), closable_packages)
        self.assertLessEqual(set(mode["cleanup_allowed_for"]), closable_packages)
        release_packages = set(mode["release_allowed_for"])
        self.assertLessEqual(release_packages, active_packages)
        self.assertLessEqual(len(release_packages), 1)
        if mode["state"] == "controlled_idle":
            self.assertEqual([], active)
            self.assertEqual([], mode["writes_allowed_for"])
            self.assertEqual(set(), release_packages)
        else:
            self.assertTrue(active)
        self.assertTrue(parsed["activation_policy"]["enabled"])
        self.assertEqual(
            {"controlled_idle", "active_delivery"},
            set(parsed["activation_policy"]["allowed_operating_states"]),
        )
        self.assertEqual(3, parsed["activation_policy"]["max_active_lanes"])
        self.assertEqual(
            2, parsed["activation_policy"]["max_implementation_lanes"]
        )
        self.assertEqual(
            1, parsed["activation_policy"]["max_direction_authority_lanes"]
        )
        self.assertEqual(
            1, parsed["activation_policy"]["max_production_capable_lanes"]
        )
        self._assert_valid_merge_authorities(parsed)
        self.assertEqual([], mode["cleanup_allowed_for"])
        self.assertTrue(parsed["workspace_snapshot"]["cleanup_authorized"])

    def test_merge_authority_accepts_recorded_implementation_owner_grant(self):
        parsed = json.loads(self.path.read_text(encoding="utf-8"))
        implementation = copy.deepcopy(self._lane_fixture(parsed))
        implementation["lane_class"] = "implementation"
        implementation["production_capable"] = True
        implementation["owner_decisions"] = [
            {
                "authorized_by": "Pete",
                "status": "authorized",
                "package": implementation["package"],
                "action": "merge the verified implementation candidate",
                "decision": (
                    "Merge authority is recorded for this implementation lane."
                ),
            }
        ]
        parsed["active_lanes"] = [implementation]
        parsed["operating_mode"]["merge_allowed_for"] = [
            implementation["package"]
        ]
        self._assert_valid_merge_authorities(parsed)

    def test_merge_authority_accepts_opportunity_under_general_class_rule(self):
        parsed = json.loads(self.path.read_text(encoding="utf-8"))
        opportunity = copy.deepcopy(
            next(
                lane
                for lane in parsed["closing_lanes"]
                if lane.get("package") == OPPORTUNITY_SLATE_PACKAGE
            )
        )
        parsed["active_lanes"] = [opportunity]
        parsed["operating_mode"]["merge_allowed_for"] = [
            OPPORTUNITY_SLATE_PACKAGE
        ]
        self._assert_valid_merge_authorities(parsed)

    def test_merge_authority_rejects_implementation_without_owner_grant(self):
        parsed = json.loads(self.path.read_text(encoding="utf-8"))
        implementation = copy.deepcopy(self._lane_fixture(parsed))
        implementation["lane_class"] = "implementation"
        implementation["production_capable"] = True
        implementation["owner_decisions"] = [
            {"date": "2026-08-12", "decision": "Review is complete."}
        ]
        parsed["active_lanes"] = [implementation]
        parsed["operating_mode"]["merge_allowed_for"] = [
            implementation["package"]
        ]
        with self.assertRaises(AssertionError):
            self._assert_valid_merge_authorities(parsed)

    def test_merge_authority_keeps_direction_grant_contract_strict(self):
        parsed = json.loads(self.path.read_text(encoding="utf-8"))
        direction = copy.deepcopy(self._lane_fixture(parsed))
        direction["lane_class"] = "direction_authority"
        direction["production_capable"] = False
        parsed["active_lanes"] = [direction]
        parsed["operating_mode"]["merge_allowed_for"] = [direction["package"]]

        direction.pop("merge_grant", None)
        with self.assertRaises(AssertionError):
            self._assert_valid_merge_authorities(parsed)

        direction["merge_grant"] = {}
        with self.assertRaises(AssertionError):
            self._assert_valid_merge_authorities(parsed)

    def test_merge_authority_rejects_package_without_matching_lane(self):
        parsed = json.loads(self.path.read_text(encoding="utf-8"))
        parsed["operating_mode"]["merge_allowed_for"] = ["PS-MISSING-LANE-001"]
        with self.assertRaises(AssertionError):
            self._assert_valid_merge_authorities(parsed)

    def test_closing_lanes_are_historical_and_retain_no_product_authority(self):
        for lane in self.ledger["closing_lanes"]:
            lane_facts = facts(branch=lane["branch"])
            write_errors, _ = evaluate_policy(
                self.ledger, lane_facts, lane["package"], "write"
            )
            self.assertTrue(
                any("write is blocked" in error for error in write_errors)
            )
            merge_errors, _ = evaluate_policy(
                self.ledger,
                lane_facts,
                lane["package"],
                "merge",
                require_clean=True,
            )
            self.assertTrue(
                any("merge is blocked" in error for error in merge_errors)
            )

    def test_paused_package_cleanup_uses_its_recorded_contract_without_a_lane(self):
        package = "PS-OPPORTUNITY-SLATE-R1-LAUNCH-001"
        origin_main = "a" * 40
        cleanup_facts = facts(
            branch="work/2026-08-12-delivery-cleanup-opportunity-slate-r1",
            head=origin_main,
            origin_main=origin_main,
            fetched=True,
        )
        errors, warnings = evaluate_policy(
            self.ledger,
            cleanup_facts,
            package,
            "cleanup",
            require_clean=True,
            origin_ledger=self.ledger,
        )
        self.assertEqual([], errors)
        self.assertEqual([], warnings)

    def test_closed_package_cleanup_uses_its_recorded_contract_without_a_lane(self):
        lane = next(
            item
            for item in self.ledger["closing_lanes"]
            if isinstance(item.get("cleanup_contract"), str)
            and item["cleanup_contract"].strip()
        )
        origin_main = "b" * 40
        cleanup_facts = facts(
            branch="work/2026-08-12-delivery-cleanup-closed-package",
            head=origin_main,
            origin_main=origin_main,
            fetched=True,
        )
        errors, _ = evaluate_policy(
            self.ledger,
            cleanup_facts,
            lane["package"],
            "cleanup",
            require_clean=True,
            origin_ledger=self.ledger,
        )
        self.assertEqual([], errors)

    def test_workspace_cleanup_accepts_only_verified_unowned_recoverable_targets(self):
        origin_main = "9" * 40
        target = {
            "path": r"C:\finished-worktree",
            "head": "8" * 40,
            "branch": "work/2026-08-12-finished-control",
            "integrated": True,
            "remote_branch_absent": True,
            "lifecycle_unowned": True,
            "clean": True,
            "registered": True,
            "recovery_tag": (
                "archive/2026-08-12/workspace-housekeeping/"
                "finished-worktree-888888888888"
            ),
            "recovery_tag_local_and_remote": True,
        }
        cleanup_facts = facts(
            branch="work/2026-08-12-delivery-cleanup-workspace-housekeeping",
            head=origin_main,
            origin_main=origin_main,
            fetched=True,
            workspace_cleanup_targets=[target],
        )
        errors, warnings = evaluate_policy(
            self.ledger,
            cleanup_facts,
            None,
            "cleanup",
            require_clean=True,
            origin_ledger=self.ledger,
            workspace_cleanup=True,
        )
        self.assertEqual([], errors)
        self.assertEqual([], warnings)

        for field in (
            "integrated",
            "remote_branch_absent",
            "lifecycle_unowned",
            "clean",
            "registered",
            "recovery_tag_local_and_remote",
        ):
            with self.subTest(field=field):
                invalid = copy.deepcopy(cleanup_facts)
                invalid["workspace_cleanup_targets"][0][field] = False
                invalid_errors, _ = evaluate_policy(
                    self.ledger,
                    invalid,
                    None,
                    "cleanup",
                    require_clean=True,
                    origin_ledger=self.ledger,
                    workspace_cleanup=True,
                )
                self.assertTrue(
                    any(field in error for error in invalid_errors),
                    invalid_errors,
                )

    def test_workspace_cleanup_does_not_claim_package_or_accept_empty_targets(self):
        origin_main = "7" * 40
        cleanup_facts = facts(
            branch="work/2026-08-12-delivery-cleanup-workspace-housekeeping",
            head=origin_main,
            origin_main=origin_main,
            fetched=True,
            workspace_cleanup_targets=[],
        )
        errors, _ = evaluate_policy(
            self.ledger,
            cleanup_facts,
            "PS-NOT-A-WORKSPACE-SCOPE-001",
            "cleanup",
            require_clean=True,
            origin_ledger=self.ledger,
            workspace_cleanup=True,
        )
        self.assertIn("workspace cleanup must not claim a package", errors)
        self.assertIn("workspace cleanup requires verified target worktrees", errors)

    def test_workspace_cleanup_cli_arguments_fail_closed(self):
        common = ["--intent", "cleanup", "--fetch", "--require-clean"]
        with patch("builtins.print"):
            self.assertEqual(2, main(common))
            self.assertEqual(
                2,
                main(
                    common
                    + [
                        "--workspace-cleanup",
                        "--package",
                        "PS-INVALID-001",
                        "--cleanup-target-worktree",
                        r"C:\finished-worktree",
                    ]
                ),
            )
            self.assertEqual(
                2,
                main(
                    common
                    + [
                        "--package",
                        "PS-INVALID-001",
                        "--cleanup-target-worktree",
                        r"C:\finished-worktree",
                    ]
                ),
            )

    def test_paused_cleanup_fails_closed_without_contract_or_exact_verifier(self):
        package = "PS-OPPORTUNITY-SLATE-R1-LAUNCH-001"
        origin = copy.deepcopy(self.ledger)
        target = next(
            item for item in origin["paused_lanes"] if item.get("package") == package
        )
        target.pop("cleanup_contract")
        origin_main = "c" * 40
        invalid_facts = facts(
            branch="work/not-a-cleanup-verifier",
            head="d" * 40,
            origin_main=origin_main,
            ahead=1,
            tracked_changes=1,
            fetched=False,
        )
        errors, _ = evaluate_policy(
            origin,
            invalid_facts,
            package,
            "cleanup",
            require_clean=False,
            origin_ledger=origin,
        )
        self.assertIn("cleanup requires --fetch", errors)
        self.assertIn("cleanup requires --require-clean", errors)
        self.assertIn("cleanup verifier must be exactly at fetched origin/main", errors)
        self.assertIn("cleanup verifier HEAD must equal fetched origin/main", errors)
        self.assertTrue(any("dedicated verifier branch" in error for error in errors))
        self.assertIn(
            "paused_lanes cleanup requires a non-empty cleanup_contract", errors
        )

    def test_cleanup_rejects_active_missing_and_stale_authority_targets(self):
        origin_main = "e" * 40
        cleanup_facts = facts(
            branch="work/2026-08-12-delivery-cleanup-lifecycle-tests",
            head=origin_main,
            origin_main=origin_main,
            fetched=True,
        )
        # This case asserts that cleanup REFUSES a target that is still active,
        # so it needs an active lane to point at. Reading one out of the live
        # ledger coupled the test to whatever happened to be open: the moment the
        # last writer paused — the ordinary end of a delivered package, and a
        # legal state — active_lanes went empty and this raised IndexError,
        # turning main red for everyone.
        #
        # Synthesise the active lane instead. A paused record promoted back into
        # active_lanes is a faithful stand-in, and the assertion now depends only
        # on the preflight's own rule rather than on live delivery state.
        active_ledger = copy.deepcopy(self.ledger)
        if not active_ledger["active_lanes"]:
            active_ledger["active_lanes"] = [
                copy.deepcopy(active_ledger["paused_lanes"][-1])
            ]
        active_package = active_ledger["active_lanes"][0]["package"]
        active_errors, _ = evaluate_policy(
            active_ledger,
            cleanup_facts,
            active_package,
            "cleanup",
            require_clean=True,
            origin_ledger=active_ledger,
        )
        self.assertTrue(any("not active" in error for error in active_errors))

        missing_errors, _ = evaluate_policy(
            self.ledger,
            cleanup_facts,
            "PS-MISSING-CLEANUP-001",
            "cleanup",
            require_clean=True,
            origin_ledger=self.ledger,
        )
        self.assertTrue(
            any("exactly one paused or closed record" in error for error in missing_errors)
        )

        stale = copy.deepcopy(self.ledger)
        package = "PS-OPPORTUNITY-SLATE-R1-LAUNCH-001"
        stale["operating_mode"]["cleanup_allowed_for"] = [package]
        stale_errors, _ = evaluate_policy(
            stale,
            cleanup_facts,
            package,
            "cleanup",
            require_clean=True,
            origin_ledger=stale,
        )
        self.assertTrue(
            any("retains mutation authority" in error for error in stale_errors)
        )

    def test_cleanup_branch_pattern_is_narrow(self):
        self.assertIsNotNone(
            CLEANUP_BRANCH_PATTERN.fullmatch(
                "work/2026-08-12-delivery-cleanup-opportunity-slate-r1"
            )
        )
        self.assertIsNone(CLEANUP_BRANCH_PATTERN.fullmatch("work/cleanup-anything"))

    def test_baseline_for_origin_synthesizes_one_package_from_idle(self):
        source = self.baseline.decode("utf-8")
        idle_baseline = re.sub(
            r"(?ms)^active_packages:\n.*?(?=^scoped_findings:\n)",
            "active_packages:\n",
            source,
            count=1,
        ).encode("utf-8")
        origin = self._idle_ledger()
        origin["active_lanes"] = [self._lane("PS-SYNTHETIC-001")]

        with patch.object(self, "baseline", idle_baseline):
            actual = self._baseline_for_origin(origin).decode("utf-8")

        self.assertIn(
            "active_packages:\n"
            "  - id: PS-SYNTHETIC-001\n"
            "    status: active_delivery\n"
            '    scope: "Synthetic active-package fixture."\n',
            actual,
        )

    def test_baseline_for_origin_uses_supplied_immutable_source(self):
        origin, lane = self._direction_origin()
        immutable = load_baseline_bytes_at_ref(PROFILE_DIRECTION_PRE_CLOSE_MAIN)
        mutable_closed = re.sub(
            rf"(?ms)^  - id: {re.escape(lane['package'])}\n.*?(?=^  - id: |^scoped_findings:\n)",
            "",
            immutable.decode("utf-8"),
            count=1,
        ).encode("utf-8")

        with patch.object(self, "baseline", mutable_closed):
            actual = self._baseline_for_origin(
                origin,
                source_baseline=immutable,
            )

        self.assertIn(
            f"  - id: {lane['package']}\n",
            actual.decode("utf-8"),
        )
        completed = re.search(
            r"(?ms)^completed_packages:\n(?P<body>.*?)(?=^retired_packages:\n)",
            actual.decode("utf-8"),
        )
        self.assertIsNotNone(completed)
        self.assertNotIn(
            f"  - {lane['package']}\n",
            completed.group("body"),
        )

    def test_activation_requires_exact_package_branch_and_capacity(self):
        activation_facts = facts(
            branch="work/2026-08-05-delivery-activation-opportunity-slate"
        )
        origin_idle = self._idle_ledger()
        activation_ledger = self._activation_candidate(
            origin_idle,
            "PS-FIRST-001",
        )
        errors, _ = self._evaluate_activation(
            activation_ledger,
            activation_facts,
            require_clean=True,
            origin=origin_idle,
        )
        self.assertEqual([], errors)

        wrong_package, _ = evaluate_policy(
            activation_ledger,
            activation_facts,
            "PS-OPPORTUNITY-SLATE-001",
            "activate",
            origin_ledger=origin_idle,
        )
        self.assertTrue(
            any("standing control package" in error for error in wrong_package)
        )

        wrong_branch, _ = evaluate_policy(
            activation_ledger,
            facts(branch="work/feature-direct"),
            "PS-DELIVERY-CONTROL-001",
            "activate",
            origin_ledger=origin_idle,
        )
        self.assertTrue(
            any("branch does not match" in error for error in wrong_branch)
        )

        active_delivery = self._activation_candidate(
            activation_ledger,
            "PS-SECOND-001",
        )
        active_errors, _ = self._evaluate_activation(
            active_delivery,
            activation_facts,
            require_clean=True,
            origin=activation_ledger,
        )
        self.assertEqual([], active_errors)

        third_lane = self._activation_candidate(
            active_delivery,
            "PS-THIRD-001",
        )
        third_lane["active_lanes"][-1]["lane_class"] = "direction_authority"
        third_lane["active_lanes"][-1]["exclusive_domains"] = [
            "direction:third-package"
        ]
        third_errors, _ = self._evaluate_activation(
            third_lane,
            activation_facts,
            require_clean=True,
            origin=active_delivery,
        )
        self.assertEqual([], third_errors)

        fourth_lane = self._activation_candidate(third_lane, "PS-FOURTH-001")
        fourth_errors, _ = self._evaluate_activation(
            fourth_lane,
            activation_facts,
            require_clean=True,
            origin=third_lane,
        )
        self.assertIn("activation refused because the lane limit is full", fourth_errors)

        full_unchanged_errors, _ = evaluate_policy(
            copy.deepcopy(third_lane),
            activation_facts,
            "PS-DELIVERY-CONTROL-001",
            "activate",
            origin_ledger=third_lane,
        )
        self.assertIn("activation refused because the lane limit is full", full_unchanged_errors)

        inconsistent_idle = copy.deepcopy(activation_ledger)
        inconsistent_idle["operating_mode"]["state"] = "controlled_idle"
        inconsistent_errors, _ = evaluate_policy(
            inconsistent_idle,
            activation_facts,
            "PS-DELIVERY-CONTROL-001",
            "activate",
            origin_ledger=origin_idle,
        )
        self.assertIn(
            "candidate controlled_idle cannot contain active lanes",
            inconsistent_errors,
        )

        inconsistent_active = copy.deepcopy(origin_idle)
        inconsistent_active["operating_mode"]["state"] = "active_delivery"
        inconsistent_active["active_lanes"] = []
        empty_active_errors, _ = evaluate_policy(
            activation_ledger,
            activation_facts,
            "PS-DELIVERY-CONTROL-001",
            "activate",
            origin_ledger=inconsistent_active,
        )
        self.assertIn(
            "origin/main active_delivery must contain an existing active lane",
            empty_active_errors,
        )

        unsupported = copy.deepcopy(activation_ledger)
        unsupported["operating_mode"]["state"] = "paused"
        unsupported_errors, _ = evaluate_policy(
            unsupported,
            activation_facts,
            "PS-DELIVERY-CONTROL-001",
            "activate",
            origin_ledger=origin_idle,
        )
        self.assertIn(
            "activation is allowed only from controlled_idle or active_delivery",
            unsupported_errors,
        )

        product_change, _ = evaluate_policy(
            activation_ledger,
            facts(
                branch=(
                    "work/2026-08-05-delivery-activation-opportunity-slate"
                ),
                changed_paths=["app.py"],
            ),
            "PS-DELIVERY-CONTROL-001",
            "activate",
            origin_ledger=origin_idle,
        )
        self.assertTrue(
            any("non-control paths" in error for error in product_change)
        )

    def test_activation_rejects_lane_replacement_mutation_and_ambiguous_delta(self):
        activation_facts = facts(
            branch="work/2026-08-05-delivery-activation-opportunity-slate"
        )
        origin_idle = self._idle_ledger()
        origin_one = self._activation_candidate(origin_idle, "PS-FIRST-001")

        no_addition = copy.deepcopy(origin_one)
        no_addition_errors, _ = evaluate_policy(
            no_addition,
            activation_facts,
            "PS-DELIVERY-CONTROL-001",
            "activate",
            origin_ledger=origin_one,
        )
        self.assertIn(
            "activation must add exactly one active lane",
            no_addition_errors,
        )

        two_additions = self._activation_candidate(origin_one, "PS-SECOND-001")
        two_additions["active_lanes"].append(self._lane("PS-THIRD-001"))
        two_addition_errors, _ = evaluate_policy(
            two_additions,
            activation_facts,
            "PS-DELIVERY-CONTROL-001",
            "activate",
            origin_ledger=origin_one,
        )
        self.assertIn(
            "activation must add exactly one active lane",
            two_addition_errors,
        )

        replacement = copy.deepcopy(origin_one)
        replacement["active_lanes"] = [self._lane("PS-SECOND-001")]
        replacement_errors, _ = evaluate_policy(
            replacement,
            activation_facts,
            "PS-DELIVERY-CONTROL-001",
            "activate",
            origin_ledger=origin_one,
        )
        self.assertTrue(
            any("may not remove active lanes" in error for error in replacement_errors)
        )

        mutation = self._activation_candidate(origin_one, "PS-SECOND-001")
        mutation["active_lanes"][0]["branch"] = "work/replaced-writer"
        mutation_errors, _ = evaluate_policy(
            mutation,
            activation_facts,
            "PS-DELIVERY-CONTROL-001",
            "activate",
            origin_ledger=origin_one,
        )
        self.assertTrue(
            any(
                "may not modify existing active lanes" in error
                for error in mutation_errors
            )
        )

        policy_mutation = self._activation_candidate(
            origin_one,
            "PS-SECOND-001",
        )
        policy_mutation["activation_policy"]["max_active_lanes"] = 4
        policy_errors, _ = evaluate_policy(
            policy_mutation,
            activation_facts,
            "PS-DELIVERY-CONTROL-001",
            "activate",
            origin_ledger=origin_one,
        )
        self.assertIn("activation may not change activation_policy", policy_errors)
        self.assertIn(
            "activation policy must retain the 3-lane limit",
            policy_errors,
        )

    def test_three_lane_model_enforces_class_and_domain_integrity(self):
        activation_facts = facts(
            branch="work/2026-08-10-delivery-activation-three-lane-test"
        )
        idle = self._idle_ledger()
        first = self._activation_candidate(idle, "PS-FIRST-001")
        second = self._activation_candidate(first, "PS-SECOND-001")

        third_implementation = self._activation_candidate(second, "PS-THIRD-001")
        implementation_errors, _ = self._evaluate_activation(
            third_implementation,
            activation_facts,
            require_clean=True,
            origin=second,
        )
        self.assertTrue(
            any("2-implementation-lane limit" in error for error in implementation_errors)
        )

        direction_origin = self._activation_candidate(idle, "PS-DIRECTION-ONE-001")
        direction_origin["active_lanes"][-1]["lane_class"] = "direction_authority"
        direction_origin["active_lanes"][-1]["exclusive_domains"] = [
            "direction:first"
        ]
        second_direction = self._activation_candidate(
            direction_origin, "PS-DIRECTION-TWO-001"
        )
        second_direction["active_lanes"][-1]["lane_class"] = "direction_authority"
        second_direction["active_lanes"][-1]["exclusive_domains"] = [
            "direction:second"
        ]
        direction_errors, _ = self._evaluate_activation(
            second_direction,
            activation_facts,
            require_clean=True,
            origin=direction_origin,
        )
        self.assertTrue(
            any(
                "1-direction-authority-lane limit" in error
                for error in direction_errors
            )
        )

        collision = self._activation_candidate(first, "PS-SECOND-001")
        collision["active_lanes"][-1]["exclusive_domains"] = [
            first["active_lanes"][0]["exclusive_domains"][0]
        ]
        collision_errors, _ = self._evaluate_activation(
            collision,
            activation_facts,
            require_clean=True,
            origin=first,
        )
        self.assertTrue(
            any("exclusive-domain collision" in error for error in collision_errors)
        )

        hierarchical_collision = self._activation_candidate(first, "PS-SECOND-001")
        hierarchical_collision["active_lanes"][-1]["exclusive_domains"] = [
            first["active_lanes"][0]["exclusive_domains"][0] + ":public"
        ]
        hierarchical_errors, _ = self._evaluate_activation(
            hierarchical_collision,
            activation_facts,
            require_clean=True,
            origin=first,
        )
        self.assertTrue(
            any("exclusive-domain collision" in error for error in hierarchical_errors)
        )

        disguised_runtime = self._activation_candidate(idle, "PS-DIRECTION-001")
        disguised_runtime["active_lanes"][-1]["lane_class"] = "direction_authority"
        disguised_runtime["active_lanes"][-1]["exclusive_domains"] = [
            "product:profile"
        ]
        disguised_runtime["active_lanes"][-1]["writable_surfaces"] = [
            "templates/profile.html"
        ]
        disguised_errors, _ = self._evaluate_activation(
            disguised_runtime,
            activation_facts,
            require_clean=True,
            origin=idle,
        )
        self.assertTrue(
            any(
                "direction_authority surface must remain under docs/initiatives or artifacts"
                in error
                for error in disguised_errors
            )
        )

        production_first = self._activation_candidate(idle, "PS-PROD-FIRST-001")
        production_first["active_lanes"][-1]["production_capable"] = True
        production_second = self._activation_candidate(
            production_first, "PS-PROD-SECOND-001"
        )
        production_second["active_lanes"][-1]["production_capable"] = True
        production_errors, _ = self._evaluate_activation(
            production_second,
            activation_facts,
            require_clean=True,
            origin=production_first,
        )
        self.assertTrue(
            any(
                "1-production-capable-lane limit" in error
                for error in production_errors
            )
        )

    def test_branch_diff_must_stay_inside_declared_lane_surfaces(self):
        package = "PS-SCOPED-001"
        ledger = self._activation_candidate(self._idle_ledger(), package)
        lane = ledger["active_lanes"][0]
        inside, _ = evaluate_policy(
            ledger,
            facts(
                branch=lane["branch"],
                changed_paths=[f"docs/initiatives/{package}/README.md"],
            ),
            package,
            "write",
            require_clean=True,
        )
        self.assertEqual([], inside)

        outside, _ = evaluate_policy(
            ledger,
            facts(branch=lane["branch"], changed_paths=["templates/base.html"]),
            package,
            "write",
            require_clean=True,
        )
        self.assertIn(
            "write branch contains path outside active lane surfaces: templates/base.html",
            outside,
        )

    def test_pause_relinquishes_capacity_without_rewriting_the_lane(self):
        package = "PS-PAUSE-001"
        origin = self._activation_candidate(self._idle_ledger(), package)
        candidate = self._pause_candidate(origin, package)
        origin_baseline, candidate_baseline = self._pause_baselines(origin, package)
        lane = origin["active_lanes"][0]
        pause_facts = facts(
            branch="work/2026-08-10-delivery-pause-ps-pause-001",
            pause_target_remote_sha="a" * 40,
            changed_paths=sorted(
                {
                    "docs/governance/CURRENT_BASELINE.yaml",
                    "docs/governance/CURRENT_LANES.json",
                }
            ),
        )
        errors, _ = evaluate_policy(
            candidate,
            pause_facts,
            package,
            "pause",
            require_clean=True,
            origin_ledger=origin,
            candidate_baseline=candidate_baseline,
            origin_baseline=origin_baseline,
        )
        self.assertEqual([], errors)

        mutated = copy.deepcopy(candidate)
        mutated["paused_lanes"][-1]["branch"] = "work/replaced"
        mutation_errors, _ = evaluate_policy(
            mutated,
            pause_facts,
            package,
            "pause",
            require_clean=True,
            origin_ledger=origin,
            candidate_baseline=candidate_baseline,
            origin_baseline=origin_baseline,
        )
        self.assertIn("pause must preserve the exact active-lane record", mutation_errors)

        out_of_scope_facts = copy.deepcopy(pause_facts)
        out_of_scope_facts["changed_paths"].append(
            f"docs/initiatives/{package}/README.md"
        )
        out_of_scope_errors, _ = evaluate_policy(
            candidate,
            out_of_scope_facts,
            package,
            "pause",
            require_clean=True,
            origin_ledger=origin,
            candidate_baseline=candidate_baseline,
            origin_baseline=origin_baseline,
        )
        self.assertIn(
            "pause control branch must change exactly: docs/governance/CURRENT_BASELINE.yaml, docs/governance/CURRENT_LANES.json",
            out_of_scope_errors,
        )

        not_pushed_facts = copy.deepcopy(pause_facts)
        not_pushed_facts["pause_target_remote_sha"] = None
        not_pushed_errors, _ = evaluate_policy(
            candidate,
            not_pushed_facts,
            package,
            "pause",
            require_clean=True,
            origin_ledger=origin,
            candidate_baseline=candidate_baseline,
            origin_baseline=origin_baseline,
        )
        self.assertIn(
            "pause requires the active lane branch to be pushed to origin",
            not_pushed_errors,
        )

        wrong_checkpoint = copy.deepcopy(candidate)
        wrong_checkpoint["paused_lanes"][-1]["preserved_head_sha"] = "b" * 40
        wrong_checkpoint_errors, _ = evaluate_policy(
            wrong_checkpoint,
            pause_facts,
            package,
            "pause",
            require_clean=True,
            origin_ledger=origin,
            candidate_baseline=candidate_baseline,
            origin_baseline=origin_baseline,
        )
        self.assertIn(
            "pause record preserved_head_sha must equal the fetched origin branch tip",
            wrong_checkpoint_errors,
        )

        smuggled_baseline = candidate_baseline.replace(
            _expected_pause_next_gate(package, []).encode("utf-8"),
            b"PS-UNRELATED-999 should start immediately.",
        )
        baseline_errors, _ = evaluate_policy(
            candidate,
            pause_facts,
            package,
            "pause",
            require_clean=True,
            origin_ledger=origin,
            candidate_baseline=smuggled_baseline,
            origin_baseline=origin_baseline,
        )
        self.assertTrue(
            any("pause baseline next_gate must equal" in error for error in baseline_errors)
        )

    def test_actual_interview_one_to_two_activation_delta_is_permitted(self):
        origin = self._one_lane_origin()
        candidate = self._interview_activation_candidate(origin)
        origin_baseline, candidate_baseline = self._actual_pr316_baselines(
            origin,
            candidate,
        )
        activation_facts = facts(
            branch=(
                "work/2026-08-06-delivery-activation-"
                "interview-studio-calibration-001"
            ),
            changed_paths=["docs/governance/CURRENT_LANES.json"],
        )

        errors, _ = self._evaluate_activation(
            candidate,
            activation_facts,
            require_clean=True,
            origin=origin,
            candidate_baseline=candidate_baseline,
            origin_baseline=origin_baseline,
        )

        self.assertEqual([], errors)

    def test_activation_baseline_allows_only_the_recorded_pr316_delta(self):
        """Changing an activation's companion baseline cannot smuggle policy edits."""
        origin = self._one_lane_origin()
        candidate = self._interview_activation_candidate(origin)
        origin_baseline, approved_baseline = self._actual_pr316_baselines(
            origin,
            candidate,
        )
        activation_facts = facts(
            branch=(
                "work/2026-08-06-delivery-activation-"
                "interview-studio-calibration-001"
            ),
            changed_paths=[
                "docs/governance/CURRENT_LANES.json",
                "docs/governance/CURRENT_BASELINE.yaml",
            ],
        )
        approved_text = approved_baseline.decode("utf-8")
        existing_package = origin["active_lanes"][0]["package"]
        added_package = self._interview_lane()["package"]
        self.assertNotEqual(existing_package, added_package)
        mutations = {
            "updated_at": (
                re.sub(
                    r'^updated_at: "[^"\r\n]+"$',
                    'updated_at: "2099-01-01"',
                    approved_text,
                    count=1,
                    flags=re.MULTILINE,
                ).encode("utf-8"),
                "activation may not change baseline section updated_at",
            ),
            "authority": (
                approved_text.replace(
                    "  remote: origin",
                    "  remote: forged-origin",
                    1,
                ).encode("utf-8"),
                "activation may not change baseline section authority",
            ),
            "governing bible": (
                approved_text.replace(
                    '    path: "docs/governance/PeerSlate_Constitution_v3.0.md"',
                    '    path: "docs/governance/Forged_Constitution.md"',
                    1,
                ).encode("utf-8"),
                "activation may not change baseline section governing_documents",
            ),
            "governing roadmap": (
                approved_text.replace(
                    '    path: "docs/governance/PeerSlate_Roadmap_v3.0.md"',
                    '    path: "docs/governance/Forged_Roadmap.md"',
                    1,
                ).encode("utf-8"),
                "activation may not change baseline section governing_documents",
            ),
            "manager role": (
                approved_text.replace(
                    '  role: "package_designated_session_manager"',
                    '  role: "forged_manager"',
                    1,
                ).encode("utf-8"),
                "activation may only change baseline manager.current_assignments",
            ),
            "scoped finding": (
                approved_text.replace(
                    "  - id: candidate_admission",
                    "  - id: forged_admission",
                    1,
                ).encode("utf-8"),
                "activation may not change baseline section scoped_findings",
            ),
            "existing active package": (
                approved_text.replace(
                    f"  - id: {existing_package}",
                    "  - id: PS-FORGED-001",
                    1,
                ).encode("utf-8"),
                "activation baseline active_packages must preserve origin/main entries byte-for-byte and append one item",
            ),
            "appended active package": (
                approved_text.replace(
                    f"  - id: {added_package}",
                    "  - id: PS-FORGED-001",
                    1,
                ).encode("utf-8"),
                "activation baseline active_packages appended id must match the newly activated package",
            ),
            "next gate": (
                re.sub(
                    r'^next_gate: .+$',
                    'next_gate: "Do not name the activated package."',
                    approved_text,
                    count=1,
                    flags=re.MULTILINE,
                ).encode("utf-8"),
                "activation baseline next_gate must mention the newly activated package",
            ),
        }

        for label, (forged_baseline, expected_error) in mutations.items():
            with self.subTest(label=label):
                errors, _ = self._evaluate_activation(
                    candidate,
                    activation_facts,
                    require_clean=True,
                    origin=origin,
                    candidate_baseline=forged_baseline,
                    origin_baseline=origin_baseline,
                )
                self.assertIn(expected_error, errors)

    def test_controlled_baseline_scalars_accept_current_and_valid_json_quote_escapes(self):
        current_assignment_match = re.search(
            r"^  current_assignments: (.+)$",
            self.baseline.decode("utf-8"),
            flags=re.MULTILINE,
        )
        self.assertIsNotNone(current_assignment_match)
        assert current_assignment_match is not None

        errors: list[str] = []
        self.assertEqual(
            "active_delivery",
            _baseline_scalar("active_delivery", "test status", errors),
        )
        self.assertEqual(
            'A valid "quoted" assignment.',
            _baseline_scalar(
                r'"A valid \"quoted\" assignment."',
                "test quoted assignment",
                errors,
            ),
        )
        self.assertIsNotNone(
            _baseline_scalar(
                current_assignment_match.group(1),
                "current baseline manager.current_assignments",
                errors,
            )
        )
        self.assertEqual([], errors)

    def test_activation_baseline_rejects_ambiguous_and_unsafe_scalars(self):
        origin = self._one_lane_origin()
        candidate = self._interview_activation_candidate(origin)
        origin_baseline, approved_baseline = self._actual_pr316_baselines(
            origin,
            candidate,
        )
        activation_facts = facts(
            branch=(
                "work/2026-08-06-delivery-activation-"
                "interview-studio-calibration-001"
            ),
            changed_paths=[
                "docs/governance/CURRENT_LANES.json",
                "docs/governance/CURRENT_BASELINE.yaml",
            ],
        )
        approved_text = approved_baseline.decode("utf-8")

        def replace_line(pattern: str, replacement: str) -> bytes:
            changed, replacements = re.subn(
                pattern,
                lambda _match: replacement,
                approved_text,
                count=1,
                flags=re.MULTILINE,
            )
            self.assertEqual(1, replacements, pattern)
            return changed.encode("utf-8")

        mutations = {
            "colon-space plain status": (
                replace_line(
                    r"^    status: active_delivery$",
                    "    status: active_delivery: unsafe",
                ),
                "safe plain scalar",
            ),
            "manager unknown escape": (
                replace_line(
                    r"^  current_assignments: .+$",
                    '  current_assignments: "Broken\\q"',
                ),
                "valid JSON double-quoted scalar",
            ),
            "scope unknown escape": (
                replace_line(
                    r'^    scope: "Visual-only.*$',
                    '    scope: "Broken\\q"',
                ),
                "valid JSON double-quoted scalar",
            ),
            "next gate unknown escape": (
                replace_line(
                    r"^next_gate: .+$",
                    'next_gate: "Broken\\q"',
                ),
                "valid JSON double-quoted scalar",
            ),
            "unmatched quote": (
                replace_line(
                    r"^  current_assignments: .+$",
                    '  current_assignments: "unterminated',
                ),
                "complete JSON double-quoted scalar",
            ),
            "internal plain quote": (
                replace_line(
                    r"^  current_assignments: .+$",
                    '  current_assignments: internal"quote',
                ),
                "safe plain scalar",
            ),
            "surrogate escape": (
                replace_line(
                    r"^next_gate: .+$",
                    'next_gate: "Broken\\uD800"',
                ),
                "control characters or surrogate code points",
            ),
            "control escape": (
                replace_line(
                    r"^next_gate: .+$",
                    'next_gate: "Broken\\u0001"',
                ),
                "control characters or surrogate code points",
            ),
        }

        for label, (forged_baseline, expected_error) in mutations.items():
            with self.subTest(label=label):
                errors, _ = self._evaluate_activation(
                    candidate,
                    activation_facts,
                    require_clean=True,
                    origin=origin,
                    candidate_baseline=forged_baseline,
                    origin_baseline=origin_baseline,
                )
                self.assertTrue(
                    any(expected_error in error for error in errors),
                    errors,
                )

    def test_activation_baseline_fails_closed_for_missing_or_malformed_bytes(self):
        origin = self._one_lane_origin()
        candidate = self._interview_activation_candidate(origin)
        origin_baseline, approved_baseline = self._actual_pr316_baselines(
            origin,
            candidate,
        )
        activation_facts = facts(
            branch=(
                "work/2026-08-06-delivery-activation-"
                "interview-studio-calibration-001"
            ),
            changed_paths=["docs/governance/CURRENT_LANES.json"],
        )

        missing_candidate, _ = evaluate_policy(
            candidate,
            activation_facts,
            "PS-DELIVERY-CONTROL-001",
            "activate",
            require_clean=True,
            origin_ledger=origin,
            origin_baseline=origin_baseline,
        )
        self.assertIn(
            "activation requires candidate CURRENT_BASELINE.yaml bytes",
            missing_candidate,
        )

        missing_origin, _ = evaluate_policy(
            candidate,
            activation_facts,
            "PS-DELIVERY-CONTROL-001",
            "activate",
            require_clean=True,
            origin_ledger=origin,
            candidate_baseline=approved_baseline,
        )
        self.assertIn(
            "activation requires the fetched origin/main CURRENT_BASELINE.yaml bytes",
            missing_origin,
        )

        malformed, _ = self._evaluate_activation(
            candidate,
            activation_facts,
            require_clean=True,
            origin=origin,
            candidate_baseline=b"manager:\n",
            origin_baseline=origin_baseline,
        )
        self.assertTrue(
            any("baseline must contain exactly the controlled" in error for error in malformed)
        )

        duplicate, _ = self._evaluate_activation(
            candidate,
            activation_facts,
            require_clean=True,
            origin=origin,
            candidate_baseline=approved_baseline + b"\nauthority:\n",
            origin_baseline=origin_baseline,
        )
        self.assertTrue(
            any("duplicate top-level section authority" in error for error in duplicate)
        )

    def test_activation_validates_new_lane_required_fields_paths_and_overlap(self):
        origin = self._activation_candidate(self._idle_ledger(), "PS-FIRST-001")
        activation_facts = facts(
            branch="work/2026-08-05-delivery-activation-opportunity-slate"
        )

        missing = self._activation_candidate(origin, "PS-SECOND-001")
        missing_lane = missing["active_lanes"][-1]
        missing_lane["outcome"] = ""
        missing_lane["writer"] = ""
        missing_lane["delivery_path"] = None
        missing_lane["writable_surfaces"] = []
        missing_lane["exclusions"] = []
        missing_lane["completion_evidence"] = []
        missing_errors, _ = evaluate_policy(
            missing,
            activation_facts,
            "PS-DELIVERY-CONTROL-001",
            "activate",
            require_clean=True,
            origin_ledger=origin,
        )
        self.assertIn("new active lane outcome must be a non-empty string", missing_errors)
        self.assertIn("new active lane writer must be a non-empty string", missing_errors)
        self.assertIn(
            "new active lane delivery_path must be a non-empty string",
            missing_errors,
        )
        self.assertIn(
            "new active lane writable_surfaces must be a non-empty list",
            missing_errors,
        )
        self.assertIn(
            "new active lane exclusions must be a non-empty list",
            missing_errors,
        )
        self.assertIn(
            "new active lane completion_evidence must be a non-empty list",
            missing_errors,
        )

        collision = self._activation_candidate(origin, "PS-SECOND-001")
        collision_lane = collision["active_lanes"][-1]
        collision_lane["branch"] = origin["active_lanes"][0]["branch"]
        collision_lane["writable_surfaces"] = [
            "docs\\initiatives\\PS-FIRST-001\\nested\\"
        ]
        collision_errors, _ = evaluate_policy(
            collision,
            activation_facts,
            "PS-DELIVERY-CONTROL-001",
            "activate",
            require_clean=True,
            origin_ledger=origin,
        )
        self.assertTrue(
            any("branch must be unique" in error for error in collision_errors)
        )
        self.assertTrue(
            any("writable surface overlaps" in error for error in collision_errors)
        )

        casefold_branch_collision = self._activation_candidate(
            origin,
            "PS-SECOND-001",
        )
        casefold_branch_collision["active_lanes"][-1]["branch"] = (
            "work/PS-FIRST-001"
        )
        casefold_branch_errors, _ = evaluate_policy(
            casefold_branch_collision,
            activation_facts,
            "PS-DELIVERY-CONTROL-001",
            "activate",
            require_clean=True,
            origin_ledger=origin,
        )
        self.assertTrue(
            any(
                "branch must be unique" in error
                for error in casefold_branch_errors
            )
        )

        casefold_collision_origin = copy.deepcopy(origin)
        casefold_collision_origin["active_lanes"][0]["writable_surfaces"] = [
            "templates/interview_studio.html"
        ]
        casefold_collision = self._activation_candidate(
            casefold_collision_origin,
            "PS-SECOND-001",
        )
        casefold_collision["active_lanes"][-1]["writable_surfaces"] = [
            "TEMPLATES/INTERVIEW_STUDIO.HTML"
        ]
        casefold_errors, _ = evaluate_policy(
            casefold_collision,
            activation_facts,
            "PS-DELIVERY-CONTROL-001",
            "activate",
            require_clean=True,
            origin_ledger=casefold_collision_origin,
        )
        self.assertTrue(
            any("writable surface overlaps" in error for error in casefold_errors)
        )

        unsafe = self._activation_candidate(origin, "PS-SECOND-001")
        unsafe["active_lanes"][-1]["writable_surfaces"] = ["../outside/"]
        unsafe_errors, _ = evaluate_policy(
            unsafe,
            activation_facts,
            "PS-DELIVERY-CONTROL-001",
            "activate",
            require_clean=True,
            origin_ledger=origin,
        )
        self.assertTrue(
            any("normalized repository-relative path" in error for error in unsafe_errors)
        )

        for glob_surface in (
            "templates/*.html",
            "templates/?.html",
            "templates/[ab].html",
            "templates/{one,two}.html",
        ):
            with self.subTest(glob_surface=glob_surface):
                glob = self._activation_candidate(origin, "PS-SECOND-001")
                glob["active_lanes"][-1]["writable_surfaces"] = [
                    glob_surface
                ]
                glob_errors, _ = evaluate_policy(
                    glob,
                    activation_facts,
                    "PS-DELIVERY-CONTROL-001",
                    "activate",
                    require_clean=True,
                    origin_ledger=origin,
                )
                self.assertTrue(
                    any(
                        "wildcard or glob characters" in error
                        for error in glob_errors
                    )
                )

    def test_activation_rejects_short_name_surface_aliases_but_allows_near_names(self):
        """Do not let Windows 8.3 aliases bypass surface isolation."""
        activation_facts = facts(
            branch="work/2026-08-05-delivery-activation-opportunity-slate"
        )
        origin = self._activation_candidate(self._idle_ledger(), "PS-FIRST-001")

        git_alias = self._activation_candidate(origin, "PS-SECOND-001")
        git_alias["active_lanes"][-1]["writable_surfaces"] = ["GIT~1/config"]
        git_alias_errors, _ = evaluate_policy(
            git_alias,
            activation_facts,
            "PS-DELIVERY-CONTROL-001",
            "activate",
            require_clean=True,
            origin_ledger=origin,
        )
        self.assertTrue(
            any("safe Windows repository-relative path" in error for error in git_alias_errors)
        )

        templates_origin = copy.deepcopy(origin)
        templates_origin["active_lanes"][0]["writable_surfaces"] = ["templates/"]
        templates_alias = self._activation_candidate(
            templates_origin,
            "PS-SECOND-001",
        )
        templates_alias["active_lanes"][-1]["writable_surfaces"] = [
            "TEMPLA~1/interview_studio.html"
        ]
        templates_alias_errors, _ = evaluate_policy(
            templates_alias,
            activation_facts,
            "PS-DELIVERY-CONTROL-001",
            "activate",
            require_clean=True,
            origin_ledger=templates_origin,
        )
        self.assertTrue(
            any(
                "safe Windows repository-relative path" in error
                for error in templates_alias_errors
            )
        )

        near_name = self._activation_candidate(templates_origin, "PS-SECOND-001")
        near_name["active_lanes"][-1]["writable_surfaces"] = [
            "templates-next/interview_studio.html"
        ]
        near_name_errors, _ = self._evaluate_activation(
            near_name,
            activation_facts,
            require_clean=True,
            origin=templates_origin,
        )
        self.assertEqual([], near_name_errors)

    def test_activation_reserves_casefolded_branches_across_all_lane_states(self):
        """Active, closing, and explicit paused branches share one namespace."""
        activation_facts = facts(
            branch="work/2026-08-05-delivery-activation-opportunity-slate"
        )
        origin = self._one_lane_origin()

        active_branch = origin["active_lanes"][0]["branch"]
        active_candidate = self._activation_candidate(origin, "PS-SECOND-001")
        active_candidate["active_lanes"][-1]["branch"] = (
            active_branch[:5] + active_branch[5:].upper()
        )
        active_errors, _ = evaluate_policy(
            active_candidate,
            activation_facts,
            "PS-DELIVERY-CONTROL-001",
            "activate",
            require_clean=True,
            origin_ledger=origin,
        )
        self.assertIn(
            "new active lane branch must be unique; it matches origin/main "
            f"active lane {origin['active_lanes'][0]['package']}",
            active_errors,
        )

        closing_branch = origin["closing_lanes"][0]["branch"]
        closing_package = origin["closing_lanes"][0]["package"]
        for candidate_branch in (
            closing_branch,
            closing_branch[:5] + closing_branch[5:].upper(),
        ):
            with self.subTest(candidate_branch=candidate_branch):
                closing_candidate = self._activation_candidate(
                    origin,
                    "PS-SECOND-001",
                )
                closing_candidate["active_lanes"][-1]["branch"] = candidate_branch
                closing_errors, _ = evaluate_policy(
                    closing_candidate,
                    activation_facts,
                    "PS-DELIVERY-CONTROL-001",
                    "activate",
                    require_clean=True,
                    origin_ledger=origin,
                )
                self.assertIn(
                    "new active lane branch must be unique; it matches origin/main "
                    f"closing lane {closing_package}",
                    closing_errors,
                )

        no_branch_paused_candidate = self._activation_candidate(
            origin,
            "PS-SECOND-001",
        )
        no_branch_paused_candidate["active_lanes"][-1]["branch"] = (
            "work/2026-08-06-no-paused-branch-collision"
        )
        no_branch_paused_errors, _ = self._evaluate_activation(
            no_branch_paused_candidate,
            activation_facts,
            require_clean=True,
            origin=origin,
        )
        self.assertEqual([], no_branch_paused_errors)

        paused_origin = copy.deepcopy(origin)
        paused_branch = "work/2026-08-06-paused-implementation"
        paused_origin["paused_lanes"].append(
            {
                "package": "PS-PAUSED-BRANCH-001",
                "branch": paused_branch,
                "reason": "reserved while awaiting owner direction",
            }
        )
        paused_candidate = self._activation_candidate(
            paused_origin,
            "PS-SECOND-001",
        )
        paused_candidate["active_lanes"][-1]["branch"] = (
            paused_branch[:5] + paused_branch[5:].upper()
        )
        paused_errors, _ = evaluate_policy(
            paused_candidate,
            activation_facts,
            "PS-DELIVERY-CONTROL-001",
            "activate",
            require_clean=True,
            origin_ledger=paused_origin,
        )
        self.assertIn(
            "new active lane branch must be unique; it matches origin/main "
            "paused lane PS-PAUSED-BRANCH-001",
            paused_errors,
        )

    def test_activation_rejects_invalid_new_lane_contract_values(self):
        origin = self._activation_candidate(self._idle_ledger(), "PS-FIRST-001")
        activation_facts = facts(
            branch="work/2026-08-05-delivery-activation-opportunity-slate"
        )

        invalid = self._activation_candidate(origin, "PS-SECOND-001")
        invalid_lane = invalid["active_lanes"][-1]
        invalid_lane["branch"] = "main"
        invalid_lane["delivery_path"] = "Experimental"
        invalid_lane["completion_evidence"] = [""]
        invalid_errors, _ = evaluate_policy(
            invalid,
            activation_facts,
            "PS-DELIVERY-CONTROL-001",
            "activate",
            require_clean=True,
            origin_ledger=origin,
        )
        self.assertIn(
            "new active lane branch must be a future non-main work/... branch",
            invalid_errors,
        )
        self.assertIn(
            "new active lane delivery_path must be one of: Bounded, Protected, Routine",
            invalid_errors,
        )
        self.assertIn(
            "new active lane completion_evidence[0] must be a non-empty string",
            invalid_errors,
        )

        same_as_activation = self._activation_candidate(origin, "PS-SECOND-001")
        same_as_activation["active_lanes"][-1]["branch"] = (
            "work/2026-08-05-delivery-activation-OPPORTUNITY-SLATE"
        )
        same_branch_errors, _ = evaluate_policy(
            same_as_activation,
            activation_facts,
            "PS-DELIVERY-CONTROL-001",
            "activate",
            require_clean=True,
            origin_ledger=origin,
        )
        self.assertIn(
            "new active lane branch must differ from the activation branch",
            same_branch_errors,
        )

        non_string_evidence = self._activation_candidate(origin, "PS-SECOND-001")
        non_string_evidence["active_lanes"][-1]["completion_evidence"] = [7]
        non_string_evidence_errors, _ = evaluate_policy(
            non_string_evidence,
            activation_facts,
            "PS-DELIVERY-CONTROL-001",
            "activate",
            require_clean=True,
            origin_ledger=origin,
        )
        self.assertIn(
            "new active lane completion_evidence[0] must be a non-empty string",
            non_string_evidence_errors,
        )

        duplicate_surface = self._activation_candidate(origin, "PS-SECOND-001")
        duplicate_surface["active_lanes"][-1]["writable_surfaces"] = [
            "app.py",
            "APP.PY",
        ]
        duplicate_surface_errors, _ = evaluate_policy(
            duplicate_surface,
            activation_facts,
            "PS-DELIVERY-CONTROL-001",
            "activate",
            require_clean=True,
            origin_ledger=origin,
        )
        self.assertIn(
            "new active lane writable_surfaces must not repeat a path",
            duplicate_surface_errors,
        )

    def test_activation_rejects_invalid_git_ref_implementation_branches(self):
        origin = self._activation_candidate(self._idle_ledger(), "PS-FIRST-001")
        activation_facts = facts(
            branch="work/2026-08-05-delivery-activation-opportunity-slate"
        )
        invalid_branches = (
            "work/..",
            "work/foo..bar",
            "work/foo@{bar",
            "work/foo bar",
            "work/foo\tbar",
            "work/foo\x7fbar",
            "work/foo~bar",
            "work/foo^bar",
            "work/foo:bar",
            "work/foo?bar",
            "work/foo*bar",
            "work/foo[bar",
            "work/foo\\bar",
            f"work/unsafe{chr(0xD800)}branch",
            "work/CON",
            "work/PRN.txt",
            "work/CONIN$.txt",
            f"work/COM{chr(0x00B9)}",
            "work/foo./bar",
            "work/foo /bar",
            "work/foo<bar",
            "work/foo>bar",
            'work/foo"bar',
            "work/foo|bar",
            "work/foo//bar",
            "work/.hidden",
            "work/foo.lock",
            "work/foo.LOCK",
            "work/foo.",
            "work/foo/",
            "work/",
        )

        for invalid_branch in invalid_branches:
            with self.subTest(invalid_branch=repr(invalid_branch)):
                candidate = self._activation_candidate(origin, "PS-SECOND-001")
                candidate["active_lanes"][-1]["branch"] = invalid_branch
                errors, _ = evaluate_policy(
                    candidate,
                    activation_facts,
                    "PS-DELIVERY-CONTROL-001",
                    "activate",
                    require_clean=True,
                    origin_ledger=origin,
                )
                self.assertIn(
                    "new active lane branch must be a future non-main work/... branch",
                    errors,
                )

        for valid_branch in (
            "work/2026-08-06-safe-implementation",
            "work/2026-08-06-naïve-資料",
        ):
            with self.subTest(valid_branch=valid_branch):
                valid = self._activation_candidate(origin, "PS-SECOND-001")
                valid["active_lanes"][-1]["branch"] = valid_branch
                valid_errors, _ = self._evaluate_activation(
                    valid,
                    activation_facts,
                    require_clean=True,
                    origin=origin,
                )
                self.assertEqual([], valid_errors)

    def test_activation_rejects_windows_unsafe_surfaces(self):
        origin = self._activation_candidate(self._idle_ledger(), "PS-FIRST-001")
        activation_facts = facts(
            branch="work/2026-08-05-delivery-activation-opportunity-slate"
        )
        unsafe_surfaces = (
            (".git/config", ".git path component"),
            ("docs/.GIT/HEAD", ".git path component"),
            ("docs/file:alternate-stream", "safe Windows"),
            ("docs/control\x1f.txt", "safe Windows"),
            ("docs/delete\x7f.txt", "safe Windows"),
            ("docs/<invalid>.txt", "safe Windows"),
            ("docs/invalid>.txt", "safe Windows"),
            ('docs/"invalid".txt', "safe Windows"),
            ("docs/invalid|name.txt", "safe Windows"),
            ("docs/trailing./file.txt", "Windows-trailing spaces or dots"),
            ("docs/trailing /file.txt", "Windows-trailing spaces or dots"),
            ("docs/file.txt ", "leading or trailing whitespace"),
            ("CON", "reserved Windows device component"),
            ("docs/PRN.txt", "reserved Windows device component"),
            ("docs/AUX/file.txt", "reserved Windows device component"),
            ("docs/NUL.txt", "reserved Windows device component"),
            ("docs/COM1/file.txt", "reserved Windows device component"),
            ("docs/COM9.txt", "reserved Windows device component"),
            ("docs/LPT1/file.txt", "reserved Windows device component"),
            ("docs/LPT9.txt", "reserved Windows device component"),
            ("docs/cOnIn$.json", "reserved Windows device component"),
            ("docs/CONOUT$.log", "reserved Windows device component"),
            (
                f"docs/coM{chr(0x00B9)}/file.txt",
                "reserved Windows device component",
            ),
            (
                f"docs/COM{chr(0x00B2)}.txt",
                "reserved Windows device component",
            ),
            (
                f"docs/Com{chr(0x00B3)}.txt",
                "reserved Windows device component",
            ),
            (
                f"docs/lPt{chr(0x00B9)}/file.txt",
                "reserved Windows device component",
            ),
            (
                f"docs/LPT{chr(0x00B2)}.txt",
                "reserved Windows device component",
            ),
            (
                f"docs/Lpt{chr(0x00B3)}.txt",
                "reserved Windows device component",
            ),
            (f"docs/{chr(0xD800)}.txt", "safe Windows"),
        )

        for surface, error_fragment in unsafe_surfaces:
            with self.subTest(surface=repr(surface)):
                candidate = self._activation_candidate(origin, "PS-SECOND-001")
                candidate["active_lanes"][-1]["writable_surfaces"] = [surface]
                errors, _ = evaluate_policy(
                    candidate,
                    activation_facts,
                    "PS-DELIVERY-CONTROL-001",
                    "activate",
                    require_clean=True,
                    origin_ledger=origin,
                )
                self.assertTrue(
                    any(error_fragment in error for error in errors)
                )

        valid = self._activation_candidate(origin, "PS-SECOND-001")
        valid["active_lanes"][-1]["writable_surfaces"] = [
            ".github/workflows/validate.yml",
            "docs/initiatives/PS-SECOND-001/",
            "templates/interview_studio.html",
            "docs/ordinary$.txt",
            "docs/naïve/資料.txt",
        ]
        valid_errors, _ = self._evaluate_activation(
            valid,
            activation_facts,
            require_clean=True,
            origin=origin,
        )
        self.assertEqual([], valid_errors)

    def test_activation_rejects_noncanonical_active_lane_package_ids(self):
        origin = self._activation_candidate(self._idle_ledger(), "PS-FIRST-001")
        activation_facts = facts(
            branch="work/2026-08-05-delivery-activation-opportunity-slate"
        )

        padded_origin = copy.deepcopy(origin)
        padded_origin["active_lanes"][0]["package"] = " PS-FIRST-001 "
        padded_origin_errors, _ = evaluate_policy(
            self._activation_candidate(padded_origin, "PS-SECOND-001"),
            activation_facts,
            "PS-DELIVERY-CONTROL-001",
            "activate",
            require_clean=True,
            origin_ledger=padded_origin,
        )
        self.assertIn(
            "origin/main active_lanes[0] package must not contain leading or "
            "trailing whitespace",
            padded_origin_errors,
        )

        padded_added = self._activation_candidate(origin, " PS-SECOND-001 ")
        padded_added_errors, _ = evaluate_policy(
            padded_added,
            activation_facts,
            "PS-DELIVERY-CONTROL-001",
            "activate",
            require_clean=True,
            origin_ledger=origin,
        )
        self.assertIn(
            "candidate active_lanes[1] package must not contain leading or "
            "trailing whitespace",
            padded_added_errors,
        )
        self.assertIn(
            "new active lane package must not contain leading or trailing "
            "whitespace",
            padded_added_errors,
        )

        lowercase_added = self._activation_candidate(origin, "ps-second-001")
        lowercase_added_errors, _ = evaluate_policy(
            lowercase_added,
            activation_facts,
            "PS-DELIVERY-CONTROL-001",
            "activate",
            require_clean=True,
            origin_ledger=origin,
        )
        self.assertIn(
            "candidate active_lanes[1] package must be a canonical PS-... "
            "package ID",
            lowercase_added_errors,
        )
        self.assertIn(
            "new active lane package must be a canonical PS-... package ID",
            lowercase_added_errors,
        )

        duplicate = self._activation_candidate(origin, " PS-FIRST-001 ")
        duplicate_errors, _ = evaluate_policy(
            duplicate,
            activation_facts,
            "PS-DELIVERY-CONTROL-001",
            "activate",
            require_clean=True,
            origin_ledger=origin,
        )
        self.assertTrue(
            any(
                "duplicate package PS-FIRST-001" in error
                for error in duplicate_errors
            )
        )

        casefold_duplicate = self._activation_candidate(origin, "ps-first-001")
        casefold_duplicate_errors, _ = evaluate_policy(
            casefold_duplicate,
            activation_facts,
            "PS-DELIVERY-CONTROL-001",
            "activate",
            require_clean=True,
            origin_ledger=origin,
        )
        self.assertTrue(
            any(
                "duplicate package ps-first-001" in error
                for error in casefold_duplicate_errors
            )
        )

    def test_activation_matches_case_only_closing_and_paused_package_ids(self):
        activation_facts = facts(
            branch="work/2026-08-05-delivery-activation-opportunity-slate"
        )
        closing_origin = self._idle_ledger()
        closing_package = closing_origin["closing_lanes"][0]["package"]
        closing_candidate = self._activation_candidate(
            closing_origin,
            closing_package.casefold(),
        )
        closing_errors, _ = evaluate_policy(
            closing_candidate,
            activation_facts,
            "PS-DELIVERY-CONTROL-001",
            "activate",
            require_clean=True,
            origin_ledger=closing_origin,
        )
        self.assertIn(
            "activation may not reopen origin/main closing lane "
            f"{closing_package.casefold()}; use its authorized merge or "
            "cleanup path",
            closing_errors,
        )

        paused_origin = self._idle_ledger()
        paused_origin["paused_lanes"].append(
            {
                "package": "ps-first-001",
                "reason": "case-only paused alias",
            }
        )
        paused_candidate = self._activation_candidate(
            paused_origin,
            "PS-FIRST-001",
        )
        paused_candidate["paused_lanes"] = [
            lane
            for lane in paused_origin["paused_lanes"]
            if lane.get("package", "").casefold() != "ps-first-001"
        ]
        paused_errors, _ = self._evaluate_activation(
            paused_candidate,
            activation_facts,
            require_clean=True,
            origin=paused_origin,
        )
        self.assertEqual([], paused_errors)

    def test_activation_paused_lane_transition_is_exact(self):
        activation_facts = facts(
            branch="work/2026-08-05-delivery-activation-opportunity-slate"
        )
        added_package = "PS-FIRST-001"
        origin = self._idle_ledger()
        paused_record = {
            "package": added_package,
            "reason": "awaiting owner activation",
        }
        other_paused_record = {
            "package": "PS-OTHER-PAUSED-001",
            "reason": "separate owner decision",
        }
        origin["paused_lanes"] = [paused_record, other_paused_record]

        exact = self._activation_candidate(origin, added_package)
        exact["paused_lanes"] = [other_paused_record]
        exact_errors, _ = self._evaluate_activation(
            exact,
            activation_facts,
            require_clean=True,
            origin=origin,
        )
        self.assertEqual([], exact_errors)

        retained = self._activation_candidate(origin, added_package)
        retained_errors, _ = evaluate_policy(
            retained,
            activation_facts,
            "PS-DELIVERY-CONTROL-001",
            "activate",
            require_clean=True,
            origin_ledger=origin,
        )
        self.assertIn(
            "activation must remove exactly the newly activated package from "
            "paused_lanes",
            retained_errors,
        )

        altered = copy.deepcopy(exact)
        altered["paused_lanes"][0]["reason"] = "mutated without authority"
        altered_errors, _ = evaluate_policy(
            altered,
            activation_facts,
            "PS-DELIVERY-CONTROL-001",
            "activate",
            require_clean=True,
            origin_ledger=origin,
        )
        self.assertIn(
            "activation must remove exactly the newly activated package from "
            "paused_lanes",
            altered_errors,
        )

        absent_origin = self._idle_ledger()
        absent = self._activation_candidate(absent_origin, "PS-NOT-PAUSED-001")
        absent["paused_lanes"] = []
        absent_errors, _ = evaluate_policy(
            absent,
            activation_facts,
            "PS-DELIVERY-CONTROL-001",
            "activate",
            require_clean=True,
            origin_ledger=absent_origin,
        )
        self.assertIn(
            "activation may not change paused_lanes when the newly activated "
            "package is not paused",
            absent_errors,
        )

        duplicate_origin = self._idle_ledger()
        duplicate_origin["paused_lanes"] = [
            {"package": added_package, "reason": "first duplicate"},
            {"package": added_package, "reason": "second duplicate"},
        ]
        duplicate = self._activation_candidate(duplicate_origin, added_package)
        duplicate["paused_lanes"] = []
        duplicate_errors, _ = evaluate_policy(
            duplicate,
            activation_facts,
            "PS-DELIVERY-CONTROL-001",
            "activate",
            require_clean=True,
            origin_ledger=duplicate_origin,
        )
        self.assertIn(
            "origin/main paused_lanes contains duplicate newly activated package "
            f"{added_package}",
            duplicate_errors,
        )

    def test_activation_refuses_implicit_closing_lane_reopen(self):
        origin = self._idle_ledger()
        closing_package = origin["closing_lanes"][0]["package"]
        candidate = self._activation_candidate(origin, closing_package)
        activation_facts = facts(
            branch="work/2026-08-05-delivery-activation-opportunity-slate"
        )

        errors, _ = evaluate_policy(
            candidate,
            activation_facts,
            "PS-DELIVERY-CONTROL-001",
            "activate",
            require_clean=True,
            origin_ledger=origin,
        )

        self.assertIn(
            "activation may not reopen origin/main closing lane "
            f"{closing_package}; use its authorized merge or cleanup path",
            errors,
        )

    def test_activation_refuses_any_closing_lane_with_retained_authority(self):
        origin = self._idle_ledger()
        closing_package = origin["closing_lanes"][0]["package"]
        origin["operating_mode"]["merge_allowed_for"] = [closing_package]
        candidate = self._activation_candidate(origin, "PS-UNRELATED-NEW-001")
        activation_facts = facts(
            branch="work/2026-08-10-delivery-activation-closing-authority"
        )

        errors, _ = self._evaluate_activation(
            candidate,
            activation_facts,
            require_clean=True,
            origin=origin,
        )
        self.assertIn(
            "origin/main closing lanes retain mutation authority in merge_allowed_for: "
            + closing_package,
            errors,
        )

    def test_activation_preserves_non_lane_authority_and_paused_lanes(self):
        origin = self._one_lane_origin()
        candidate = self._interview_activation_candidate(origin)
        activation_facts = facts(
            branch=(
                "work/2026-08-06-delivery-activation-"
                "interview-studio-calibration-001"
            ),
            changed_paths=["docs/governance/CURRENT_LANES.json"],
        )

        altered_root = copy.deepcopy(candidate)
        altered_root["closing_lanes"] = []
        root_errors, _ = evaluate_policy(
            altered_root,
            activation_facts,
            "PS-DELIVERY-CONTROL-001",
            "activate",
            require_clean=True,
            origin_ledger=origin,
        )
        self.assertTrue(
            any("unrelated ledger sections: closing_lanes" in error for error in root_errors)
        )

        altered_mode = copy.deepcopy(candidate)
        altered_mode["operating_mode"]["blocked_actions"] = []
        altered_mode["operating_mode"]["merge_allowed_for"].append(
            "PS-INTERVIEW-STUDIO-CALIBRATION-001"
        )
        mode_errors, _ = evaluate_policy(
            altered_mode,
            activation_facts,
            "PS-DELIVERY-CONTROL-001",
            "activate",
            require_clean=True,
            origin_ledger=origin,
        )
        self.assertTrue(
            any("operating_mode fields" in error for error in mode_errors)
        )

        altered_paused = copy.deepcopy(candidate)
        altered_paused["paused_lanes"] = []
        paused_errors, _ = evaluate_policy(
            altered_paused,
            activation_facts,
            "PS-DELIVERY-CONTROL-001",
            "activate",
            require_clean=True,
            origin_ledger=origin,
        )
        self.assertIn(
            "activation may not change paused_lanes when the newly activated "
            "package is not paused",
            paused_errors,
        )

    def test_activation_branch_pattern_validation_fails_closed_without_throwing(self):
        origin = self._idle_ledger()
        candidate = self._activation_candidate(origin, "PS-FIRST-001")
        activation_facts = facts(
            branch="work/2026-08-05-delivery-activation-opportunity-slate"
        )

        non_string_pattern = copy.deepcopy(candidate)
        non_string_pattern["activation_policy"]["branch_pattern"] = 7
        non_string_errors, _ = evaluate_policy(
            non_string_pattern,
            activation_facts,
            "PS-DELIVERY-CONTROL-001",
            "activate",
            require_clean=True,
            origin_ledger=origin,
        )
        self.assertIn(
            "activation policy branch_pattern must be a non-empty string",
            non_string_errors,
        )

        invalid_pattern = copy.deepcopy(candidate)
        invalid_pattern["activation_policy"]["branch_pattern"] = "["
        invalid_errors, _ = evaluate_policy(
            invalid_pattern,
            activation_facts,
            "PS-DELIVERY-CONTROL-001",
            "activate",
            require_clean=True,
            origin_ledger=origin,
        )
        self.assertTrue(
            any("branch_pattern is invalid" in error for error in invalid_errors)
        )

        non_string_branch_errors, _ = evaluate_policy(
            candidate,
            facts(branch=7),
            "PS-DELIVERY-CONTROL-001",
            "activate",
            require_clean=True,
            origin_ledger=origin,
        )
        self.assertIn(
            "activation checkout branch must be a non-empty string",
            non_string_branch_errors,
        )

    def test_activation_fails_closed_for_missing_or_malformed_origin_ledger(self):
        activation_facts = facts(
            branch="work/2026-08-05-delivery-activation-opportunity-slate"
        )
        origin_idle = self._idle_ledger()
        candidate = self._activation_candidate(origin_idle, "PS-FIRST-001")

        missing_errors, _ = evaluate_policy(
            candidate,
            activation_facts,
            "PS-DELIVERY-CONTROL-001",
            "activate",
        )
        self.assertIn(
            "activation requires the fetched origin/main lane ledger",
            missing_errors,
        )

        malformed_origin = copy.deepcopy(origin_idle)
        malformed_origin["active_lanes"] = "not-a-list"
        malformed_errors, _ = evaluate_policy(
            candidate,
            activation_facts,
            "PS-DELIVERY-CONTROL-001",
            "activate",
            origin_ledger=malformed_origin,
        )
        self.assertIn(
            "origin/main active_lanes must be a list",
            malformed_errors,
        )

        duplicate_candidate = self._activation_candidate(
            origin_one := self._activation_candidate(
                origin_idle,
                "PS-FIRST-001",
            ),
            "PS-SECOND-001",
        )
        duplicate_candidate["active_lanes"].append(
            copy.deepcopy(duplicate_candidate["active_lanes"][0])
        )
        duplicate_errors, _ = evaluate_policy(
            duplicate_candidate,
            activation_facts,
            "PS-DELIVERY-CONTROL-001",
            "activate",
            origin_ledger=origin_one,
        )
        self.assertTrue(
            any("duplicate package" in error for error in duplicate_errors)
        )

        malformed_candidate = copy.deepcopy(candidate)
        malformed_candidate["active_lanes"] = ["not-an-object"]
        malformed_candidate_errors, _ = evaluate_policy(
            malformed_candidate,
            activation_facts,
            "PS-DELIVERY-CONTROL-001",
            "activate",
            origin_ledger=origin_idle,
        )
        self.assertIn(
            "candidate active_lanes[0] must be an object",
            malformed_candidate_errors,
        )

    def test_non_object_operating_mode_fails_closed_for_each_intent(self):
        malformed = copy.deepcopy(self._idle_ledger())
        malformed["operating_mode"] = "not-an-object"
        activation_facts = facts(
            branch="work/2026-08-05-delivery-activation-opportunity-slate"
        )

        read_errors, _ = evaluate_policy(
            malformed,
            activation_facts,
            "PS-DELIVERY-CONTROL-001",
            "read",
        )
        self.assertIn("lane ledger operating_mode must be an object", read_errors)

        write_errors, _ = evaluate_policy(
            malformed,
            activation_facts,
            "PS-DELIVERY-CONTROL-001",
            "write",
        )
        self.assertIn("lane ledger operating_mode must be an object", write_errors)

        activate_errors, _ = evaluate_policy(
            malformed,
            activation_facts,
            "PS-DELIVERY-CONTROL-001",
            "activate",
            require_clean=True,
            origin_ledger=self._idle_ledger(),
        )
        self.assertIn(
            "candidate operating_mode must be an object",
            activate_errors,
        )

    def test_main_reports_non_object_operating_mode_without_throwing(self):
        malformed = copy.deepcopy(self._idle_ledger())
        malformed["operating_mode"] = "not-an-object"
        with (
            patch("scripts.delivery_preflight.load_ledger", return_value=malformed),
            patch("scripts.delivery_preflight.collect_facts", return_value=facts()),
            patch("builtins.print") as printed,
        ):
            result = main(
                [
                    "--package",
                    "PS-DELIVERY-CONTROL-001",
                    "--intent",
                    "write",
                ]
            )

        self.assertEqual(2, result)
        payload = json.loads(printed.call_args.args[0])
        self.assertIsNone(payload["operating_mode"])
        self.assertIn("lane ledger operating_mode must be an object", payload["errors"])

    def test_ordinary_fact_collection_skips_changed_path_inventory(self):
        def fake_git(*args, **_kwargs):
            command = tuple(args)
            outputs = {
                ("config", "--get", "remote.origin.url"): (
                    "https://dev.azure.com/peerslate19/portfolio-site/_git/portfolio-site"
                ),
                ("symbolic-ref", "--quiet", "--short", "HEAD"): "main",
                ("rev-parse", "HEAD"): "abc",
                ("rev-parse", "origin/main"): "abc",
                ("rev-list", "--count", "abc..abc"): "0",
            }
            if command not in outputs:
                raise AssertionError(f"unexpected changed-path command: {command}")
            return outputs[command]

        with patch("scripts.delivery_preflight._git", side_effect=fake_git), patch(
            "scripts.delivery_preflight._git_nul", return_value=["?? output/"]
        ):
            collected = collect_facts()

        self.assertNotIn("changed_paths", collected)
        self.assertEqual(1, collected["untracked_changes"])

    def test_activation_fact_collection_includes_changed_paths(self):
        def fake_git(*args, **_kwargs):
            outputs = {
                ("config", "--get", "remote.origin.url"): (
                    "https://dev.azure.com/peerslate19/portfolio-site/_git/portfolio-site"
                ),
                ("symbolic-ref", "--quiet", "--short", "HEAD"): (
                    "work/2026-08-04-delivery-activation-preflight-output"
                ),
                ("rev-parse", "HEAD"): "abc",
                ("rev-parse", "origin/main"): "abc",
                ("rev-list", "--count", "abc..abc"): "0",
            }
            return outputs[tuple(args)]

        def fake_git_nul(*args):
            outputs = {
                (
                    "-c", "core.fsmonitor=false", "status",
                    "--porcelain=v1", "-z", "--untracked-files=all",
                ): [
                    " M scripts/delivery_preflight.py"
                ],
                ("diff", "--name-only", "-z", "abc...abc"): [],
                ("diff", "--name-only", "-z"): [
                    "scripts/delivery_preflight.py"
                ],
                ("diff", "--cached", "--name-only", "-z"): [],
                ("ls-files", "--others", "--exclude-standard", "-z"): [
                    "output/note.txt"
                ],
            }
            return outputs[tuple(args)]

        with patch("scripts.delivery_preflight._git", side_effect=fake_git), patch(
            "scripts.delivery_preflight._git_nul", side_effect=fake_git_nul
        ):
            collected = collect_facts(include_changed_paths=True)

        self.assertEqual(
            ["output/note.txt", "scripts/delivery_preflight.py"],
            collected["changed_paths"],
        )

    def test_origin_ledger_loader_is_read_only_and_fails_closed(self):
        payload = {"active_lanes": [], "operating_mode": {"state": "controlled_idle"}}
        with patch(
            "scripts.delivery_preflight._git",
            return_value=json.dumps(payload),
        ) as git_call:
            loaded = load_ledger_at_ref("origin/main")
        self.assertEqual(payload, loaded)
        git_call.assert_called_once_with(
            "show",
            "origin/main:docs/governance/CURRENT_LANES.json",
        )

        with patch("scripts.delivery_preflight._git", return_value="not-json"):
            with self.assertRaisesRegex(ValueError, "not valid JSON"):
                load_ledger_at_ref("origin/main")

        with patch("scripts.delivery_preflight._git", return_value="[]"):
            with self.assertRaisesRegex(ValueError, "must contain a JSON object"):
                load_ledger_at_ref("origin/main")

    def test_activate_main_collects_fetched_facts_before_loading_origin_ledger(self):
        call_order = []
        origin_idle = self._idle_ledger()
        candidate = self._activation_candidate(origin_idle, "PS-FIRST-001")

        def fake_facts(**kwargs):
            call_order.append(("facts", kwargs))
            return facts(
                branch="work/2026-08-05-delivery-activation-opportunity-slate"
            )

        def fake_origin(ref):
            call_order.append(("origin", ref))
            return origin_idle

        def fake_snapshot(_repository, branches, *, expected_origin=None):
            call_order.append(("snapshot", tuple(branches), expected_origin))
            return (
                "https://dev.azure.com/peerslate19/portfolio-site/_git/portfolio-site",
                {"main": facts()["origin_main"]},
            )

        origin_baseline, candidate_baseline = self._activation_baselines(
            origin_idle,
            candidate,
        )

        def fake_candidate_baseline():
            call_order.append(("candidate_baseline",))
            return candidate_baseline

        def fake_origin_baseline(ref):
            call_order.append(("origin_baseline", ref))
            return origin_baseline

        with (
            patch("scripts.delivery_preflight.load_ledger", return_value=candidate),
            patch("scripts.delivery_preflight.collect_facts", side_effect=fake_facts),
            patch(
                "scripts.delivery_preflight._authoritative_ref_snapshot",
                side_effect=fake_snapshot,
            ),
            patch(
                "scripts.delivery_preflight.load_ledger_at_ref",
                side_effect=fake_origin,
            ),
            patch(
                "scripts.delivery_preflight.load_baseline_bytes",
                side_effect=fake_candidate_baseline,
            ),
            patch(
                "scripts.delivery_preflight.load_baseline_bytes_at_ref",
                side_effect=fake_origin_baseline,
            ),
            patch("builtins.print"),
        ):
            result = main(
                [
                    "--package",
                    "PS-DELIVERY-CONTROL-001",
                    "--intent",
                    "activate",
                    "--fetch",
                    "--require-clean",
                ]
            )

        self.assertEqual(0, result)
        self.assertEqual(
            [
                ("snapshot", ("main",), None),
                (
                    "facts",
                    {"fetch": False, "include_changed_paths": True},
                ),
                ("origin", facts()["origin_main"]),
                ("candidate_baseline",),
                ("origin_baseline", facts()["origin_main"]),
                (
                    "snapshot",
                    ("main",),
                    "https://dev.azure.com/peerslate19/portfolio-site/_git/portfolio-site",
                ),
            ],
            call_order,
        )

    def test_exact_control_fails_when_advertised_main_moves(self):
        origin_idle = self._idle_ledger()
        candidate = self._activation_candidate(origin_idle, "PS-FIRST-001")
        origin_baseline, candidate_baseline = self._activation_baselines(
            origin_idle, candidate,
        )
        initial = facts()["origin_main"]
        moved = "f" * 40
        origin_url = (
            "https://dev.azure.com/peerslate19/portfolio-site/_git/portfolio-site"
        )

        with (
            patch("scripts.delivery_preflight.load_ledger", return_value=candidate),
            patch(
                "scripts.delivery_preflight.collect_facts",
                return_value=facts(
                    branch="work/2026-08-05-delivery-activation-opportunity-slate"
                ),
            ),
            patch(
                "scripts.delivery_preflight._authoritative_ref_snapshot",
                side_effect=[
                    (origin_url, {"main": initial}),
                    (origin_url, {"main": moved}),
                ],
            ),
            patch(
                "scripts.delivery_preflight.load_ledger_at_ref",
                return_value=origin_idle,
            ),
            patch(
                "scripts.delivery_preflight.load_baseline_bytes",
                return_value=candidate_baseline,
            ),
            patch(
                "scripts.delivery_preflight.load_baseline_bytes_at_ref",
                return_value=origin_baseline,
            ),
            patch("builtins.print") as printed,
        ):
            result = main([
                "--package", "PS-DELIVERY-CONTROL-001",
                "--intent", "activate", "--fetch", "--require-clean",
            ])

        self.assertEqual(2, result)
        self.assertIn("moved", printed.call_args.args[0])

    def test_direction_merge_requires_frozen_candidate_worktree(self):
        origin, lane = self._direction_origin()
        reviewed = PROFILE_DIRECTION_REVIEW_ATTESTATION["reviewed_sha"]
        lane["merge_grant"] = self._grant_record(lane, reviewed)
        origin["active_lanes"] = [lane]
        origin["operating_mode"]["merge_allowed_for"] = [lane["package"]]

        with (
            patch("scripts.delivery_preflight.load_ledger", return_value=origin),
            patch(
                "scripts.delivery_preflight.collect_facts",
                return_value=facts(
                    branch=lane["branch"], head=reviewed, behind=2,
                ),
            ),
            patch(
                "scripts.delivery_preflight.load_ledger_at_ref",
                return_value=origin,
            ),
            patch(
                "scripts.delivery_preflight.load_baseline_bytes",
                return_value=self.baseline,
            ),
            patch(
                "scripts.delivery_preflight.load_baseline_bytes_at_ref",
                return_value=self.baseline,
            ),
            patch("builtins.print") as printed,
        ):
            result = main([
                "--package", lane["package"], "--intent", "merge",
                "--fetch", "--require-clean",
            ])

        self.assertEqual(2, result)
        self.assertIn(
            "direction-authority merge requires --candidate-worktree",
            printed.call_args.args[0],
        )

    def test_activate_main_requires_fetch_and_clean_arguments(self):
        with patch("scripts.delivery_preflight.load_ledger") as loader, patch(
            "builtins.print"
        ):
            missing_both = main(
                [
                    "--package",
                    "PS-DELIVERY-CONTROL-001",
                    "--intent",
                    "activate",
                ]
            )
        self.assertEqual(2, missing_both)
        loader.assert_not_called()

        with patch("scripts.delivery_preflight.load_ledger") as loader, patch(
            "builtins.print"
        ):
            missing_clean = main(
                [
                    "--package",
                    "PS-DELIVERY-CONTROL-001",
                    "--intent",
                    "activate",
                    "--fetch",
                ]
            )
        self.assertEqual(2, missing_clean)
        loader.assert_not_called()

    def test_transfer_main_requires_fetch_and_clean_arguments(self):
        with patch("scripts.delivery_preflight.load_ledger") as loader, patch(
            "builtins.print"
        ):
            missing_both = main(
                [
                    "--package",
                    "PS-OPPORTUNITY-SLATE-002",
                    "--intent",
                    "transfer",
                ]
            )
        self.assertEqual(2, missing_both)
        loader.assert_not_called()

        with patch("scripts.delivery_preflight.load_ledger") as loader, patch(
            "builtins.print"
        ):
            missing_clean = main(
                [
                    "--package",
                    "PS-OPPORTUNITY-SLATE-002",
                    "--intent",
                    "transfer",
                    "--fetch",
                ]
            )
        self.assertEqual(2, missing_clean)
        loader.assert_not_called()

    def test_writer_transfer_is_exact_and_fail_closed(self):
        origin, _ = self._opportunity_origin()
        candidate = copy.deepcopy(origin)
        candidate["updated_at"] = "2026-08-12T01:45:00Z"
        handoff_sha = "3fb657456fef757c70292cf20217f567c477f733"
        target = next(
            lane
            for lane in candidate["active_lanes"]
            if lane["package"] == "PS-OPPORTUNITY-SLATE-002"
        )
        target["writer"] = "Root Codex session /root is the replacement writer"
        target["owner_decisions"].append(
            {
                "date": "2026-08-11",
                "decision": (
                    "Pete transferred the lane after the prior writer pushed and "
                    f"relinquished exact SHA {handoff_sha}."
                ),
            }
        )
        transfer_facts = facts(
            branch="work/2026-08-11-opportunity-slate-v2-codex-transfer",
            changed_paths=["docs/governance/CURRENT_LANES.json"],
            transfer_target_remote_sha=handoff_sha,
        )
        errors, warnings = evaluate_policy(
            candidate,
            transfer_facts,
            "PS-OPPORTUNITY-SLATE-002",
            "transfer",
            require_clean=True,
            origin_ledger=origin,
            candidate_baseline=self.baseline,
            origin_baseline=self.baseline,
        )
        self.assertEqual([], errors)
        self.assertEqual([], warnings)

        wrong_path = copy.deepcopy(transfer_facts)
        wrong_path["changed_paths"] = [
            "docs/governance/CURRENT_LANES.json",
            "scripts/delivery_preflight.py",
        ]
        path_errors, _ = evaluate_policy(
            candidate,
            wrong_path,
            "PS-OPPORTUNITY-SLATE-002",
            "transfer",
            require_clean=True,
            origin_ledger=origin,
            candidate_baseline=self.baseline,
            origin_baseline=self.baseline,
        )
        self.assertTrue(any("change exactly" in error for error in path_errors))

        altered_lane = copy.deepcopy(candidate)
        target = next(
            lane
            for lane in altered_lane["active_lanes"]
            if lane["package"] == "PS-OPPORTUNITY-SLATE-002"
        )
        target["writable_surfaces"].append("app.py")
        lane_errors, _ = evaluate_policy(
            altered_lane,
            transfer_facts,
            "PS-OPPORTUNITY-SLATE-002",
            "transfer",
            require_clean=True,
            origin_ledger=origin,
            candidate_baseline=self.baseline,
            origin_baseline=self.baseline,
        )
        self.assertTrue(any("lane fields" in error for error in lane_errors))

        baseline_errors, _ = evaluate_policy(
            candidate,
            transfer_facts,
            "PS-OPPORTUNITY-SLATE-002",
            "transfer",
            require_clean=True,
            origin_ledger=origin,
            candidate_baseline=self.baseline + b"\n# changed\n",
            origin_baseline=self.baseline,
        )
        self.assertTrue(
            any("may not change CURRENT_BASELINE" in error for error in baseline_errors)
        )

    def test_writer_transfer_preflight_repair_is_exact_and_one_time(self):
        repair = WRITER_TRANSFER_PREFLIGHT_REPAIR
        origin_ledger = load_ledger_at_ref(repair["origin_main"])
        origin_baseline = load_baseline_bytes_at_ref(repair["origin_main"])
        candidate = copy.deepcopy(origin_ledger)
        candidate["updated_at"] = "2026-08-12T01:36:38Z"
        candidate["writer_transfer_preflight_repair"] = copy.deepcopy(repair)
        exact = facts(
            branch=repair["branch"],
            origin_main=repair["origin_main"],
            changed_paths=repair["allowed_surfaces"],
        )
        exact_errors, exact_warnings = self._evaluate_activation(
            candidate,
            exact,
            require_clean=True,
            origin=origin_ledger,
            candidate_baseline=origin_baseline,
            origin_baseline=origin_baseline,
        )
        self.assertEqual([], exact_errors)
        self.assertTrue(
            any("writer-transfer" in warning for warning in exact_warnings)
        )

        altered = copy.deepcopy(exact)
        altered["branch"] = "work/2026-08-11-delivery-activation-other"
        altered_errors, _ = self._evaluate_activation(
            candidate,
            altered,
            require_clean=True,
            origin=origin_ledger,
            candidate_baseline=origin_baseline,
            origin_baseline=origin_baseline,
        )
        self.assertTrue(altered_errors)

    def test_bootstrap_control_repair_is_exact_and_one_time(self):
        # Replay the historical one-time exception against the exact merged
        # repair state, not the live checked-in ledger/baseline: a later
        # activation changes the live files and must not retroactively fail
        # this replay. Owner-approved fixture repair, 2026-08-11.
        repair_ledger = load_ledger_at_ref(BOOTSTRAP_MERGED_MAIN)
        repair_baseline = load_baseline_bytes_at_ref(BOOTSTRAP_MERGED_MAIN)
        bootstrap = repair_ledger["bootstrap_control_repair"]
        self.assertEqual(BOOTSTRAP_CONTROL_REPAIR, bootstrap)
        origin_ledger = load_ledger_at_ref(bootstrap["origin_main"])
        origin_baseline = load_baseline_bytes_at_ref(bootstrap["origin_main"])
        standing = set(repair_ledger["activation_policy"]["allowed_surfaces"])
        # A surface the exception widens to, so losing the exception is visible.
        widened = sorted(set(bootstrap["allowed_surfaces"]) - standing)
        self.assertTrue(widened, "the one-time repair must widen some surface")
        exact = facts(
            branch=bootstrap["branch"],
            origin_main=bootstrap["origin_main"],
            changed_paths=bootstrap["allowed_surfaces"],
        )
        exact_errors, exact_warnings = self._evaluate_activation(
            repair_ledger,
            exact,
            require_clean=True,
            origin=origin_ledger,
            candidate_baseline=repair_baseline,
            origin_baseline=origin_baseline,
        )
        self.assertEqual([], exact_errors)
        self.assertTrue(any("one-time" in warning for warning in exact_warnings))

        altered_baseline_errors, _ = evaluate_policy(
            repair_ledger,
            exact,
            "PS-DELIVERY-CONTROL-001",
            "activate",
            require_clean=True,
            origin_ledger=origin_ledger,
            candidate_baseline=repair_baseline + b"# forged activation baseline\n",
            origin_baseline=origin_baseline,
        )
        self.assertTrue(
            any("candidate baseline line" in error for error in altered_baseline_errors)
        )

        outside_errors, _ = evaluate_policy(
            repair_ledger,
            {**exact, "changed_paths": ["app.py"]},
            "PS-DELIVERY-CONTROL-001",
            "activate",
            require_clean=True,
            origin_ledger=origin_ledger,
        )
        self.assertTrue(
            any("non-control paths" in error for error in outside_errors)
        )

        changed_lanes = copy.deepcopy(repair_ledger)
        changed_lanes["active_lanes"].append(self._lane("PS-UNAUTHORIZED-001"))
        lane_errors, _ = evaluate_policy(
            changed_lanes,
            exact,
            "PS-DELIVERY-CONTROL-001",
            "activate",
            require_clean=True,
            origin_ledger=origin_ledger,
            candidate_baseline=repair_baseline,
            origin_baseline=origin_baseline,
        )
        self.assertIn(
            "bootstrap control repair must leave no active writer lanes",
            lane_errors,
        )

        changed_mode = copy.deepcopy(repair_ledger)
        changed_mode["operating_mode"]["exit_authority"] = "broadened"
        mode_errors, _ = evaluate_policy(
            changed_mode,
            exact,
            "PS-DELIVERY-CONTROL-001",
            "activate",
            require_clean=True,
            origin_ledger=origin_ledger,
            candidate_baseline=repair_baseline,
            origin_baseline=origin_baseline,
        )
        self.assertIn(
            "bootstrap control repair exit_authority is not exact",
            mode_errors,
        )

        changed_policy = copy.deepcopy(repair_ledger)
        changed_policy["activation_policy"]["max_active_lanes"] = 4
        policy_errors, _ = evaluate_policy(
            changed_policy,
            exact,
            "PS-DELIVERY-CONTROL-001",
            "activate",
            require_clean=True,
            origin_ledger=origin_ledger,
            candidate_baseline=repair_baseline,
            origin_baseline=origin_baseline,
        )
        self.assertIn(
            "bootstrap control repair activation_policy must match the exact code-controlled policy",
            policy_errors,
        )

        stale_errors, _ = evaluate_policy(
            repair_ledger,
            {**exact, "origin_main": "new-main-after-merge"},
            "PS-DELIVERY-CONTROL-001",
            "activate",
            require_clean=True,
            origin_ledger=origin_ledger,
            candidate_baseline=repair_baseline,
            origin_baseline=origin_baseline,
        )
        self.assertTrue(
            any("non-control paths" in error for error in stale_errors)
        )

        forged = copy.deepcopy(repair_ledger)
        forged["bootstrap_control_repair"]["reason"] = "candidate-forged"
        forged_errors, forged_warnings = evaluate_policy(
            forged,
            exact,
            "PS-DELIVERY-CONTROL-001",
            "activate",
            require_clean=True,
            origin_ledger=origin_ledger,
            candidate_baseline=repair_baseline,
            origin_baseline=origin_baseline,
        )
        self.assertIn(
            "bootstrap control repair record does not match the "
            "exact owner-authorized record",
            forged_errors,
        )
        self.assertFalse(
            any("one-time" in warning for warning in forged_warnings)
        )

    def test_other_lane_write_is_blocked_but_read_is_allowed(self):
        # Pick a package that is genuinely not an active or closing lane, so
        # this keeps testing the block whichever lane the owner activates.
        inactive_package = self._inactive_package()
        errors, _ = evaluate_policy(
            self.ledger,
            facts(branch="work/other"),
            inactive_package,
            "write",
        )
        self.assertTrue(any("blocked" in error for error in errors))

        read_errors, _ = evaluate_policy(
            self.ledger,
            facts(branch="work/other", behind=40),
            inactive_package,
            "read",
        )
        self.assertTrue(any("behind" in error for error in read_errors))

        current_read_errors, _ = evaluate_policy(
            self.ledger,
            facts(branch="work/other"),
            inactive_package,
            "read",
        )
        self.assertEqual([], current_read_errors)

    def test_release_and_direct_main_writes_are_blocked(self):
        release_errors, _ = evaluate_policy(
            self.ledger,
            facts(),
            "PS-DELIVERY-RESET-001",
            "release",
        )
        self.assertTrue(any("release is blocked" in error for error in release_errors))

        main_errors, _ = evaluate_policy(
            self.ledger,
            facts(branch="main"),
            "PS-DELIVERY-RESET-001",
            "write",
        )
        self.assertTrue(any("directly from main" in error for error in main_errors))

    def test_clean_and_azure_requirements_fail_closed(self):
        dirty_errors, _ = evaluate_policy(
            self.ledger,
            facts(untracked_changes=1),
            "PS-DELIVERY-RESET-001",
            "write",
            require_clean=True,
        )
        self.assertIn("checkout is not clean", dirty_errors)

        remote_errors, _ = evaluate_policy(
            self.ledger,
            facts(origin_is_azure=False),
            "PS-DELIVERY-RESET-001",
            "write",
        )
        self.assertTrue(any("Azure DevOps" in error for error in remote_errors))


if __name__ == "__main__":
    unittest.main()
