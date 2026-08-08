import copy
import json
import re
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.delivery_preflight import (
    BOOTSTRAP_CONTROL_REPAIR,
    _baseline_scalar,
    collect_facts,
    evaluate_policy,
    load_baseline_bytes,
    load_ledger,
    load_ledger_at_ref,
    main,
)


ROOT = Path(__file__).resolve().parents[1]


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

    def _baseline_for_origin(self, origin: dict) -> bytes:
        """Return a baseline whose active packages match a real origin fixture.

        A checked-in activation candidate can contain the lane that a 1->2
        transition test is trying to add.  Keep the fixture independent from
        that transient repository state by retaining only packages present in
        the synthetic origin.  Synthetic package names used by other tests do
        not appear in the real baseline, so those fixtures intentionally keep
        the checked-in bytes unchanged.
        """
        packages = {
            lane["package"]
            for lane in origin.get("active_lanes", [])
            if isinstance(lane, dict) and isinstance(lane.get("package"), str)
        }
        source = self.baseline.decode("utf-8")
        section = re.search(
            r"(?ms)^active_packages:\n(?P<body>.*?)(?=^scoped_findings:\n)",
            source,
        )
        if section is None:
            return self.baseline
        blocks = list(
            re.finditer(
                r"(?ms)^  - id: (?P<id>[^\n]+)\n.*?(?=^  - id: |\Z)",
                section.group("body"),
            )
        )
        recorded = {block.group("id") for block in blocks}
        if not packages:
            return self.baseline
        if packages.issubset(recorded):
            retained = "".join(
                block.group(0)
                for block in blocks
                if block.group("id") in packages
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
            return self.baseline
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

    def _one_lane_origin(self) -> dict:
        """Build the stable one-lane origin required by 1->2 tests.

        These transition tests validate the standing one-to-two activation
        contract.  They must not inherit a second lane that happens to be
        recorded in the checked-in repository while an unrelated activation
        PR is under review.
        """
        origin = copy.deepcopy(self.ledger)
        active_lanes = list(origin.get("active_lanes") or [])
        target_package = self._interview_lane()["package"]
        retained = next(
            (
                lane
                for lane in active_lanes
                if lane.get("package") != target_package
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
            "production_capable": False,
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

    def test_lane_ledger_has_a_valid_operating_state(self):
        parsed = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(1, parsed["schema_version"])
        mode = parsed["operating_mode"]
        active = parsed["active_lanes"]
        closing = parsed["closing_lanes"]
        active_packages = {lane["package"] for lane in active}
        closable_packages = active_packages | {
            lane["package"] for lane in closing
        }
        self.assertIn(mode["state"], {"controlled_idle", "active_delivery"})
        self.assertLessEqual(len(active), 2)
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
        self.assertTrue(parsed["workspace_snapshot"]["cleanup_authorized"])

    def test_closing_lanes_are_merge_and_cleanup_only(self):
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
            self.assertEqual([], merge_errors)
            cleanup_errors, _ = evaluate_policy(
                self.ledger, lane_facts, lane["package"], "cleanup"
            )
            self.assertEqual([], cleanup_errors)

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

        busy = self._activation_candidate(
            active_delivery,
            "PS-THIRD-001",
        )
        busy_errors, _ = evaluate_policy(
            busy,
            activation_facts,
            "PS-DELIVERY-CONTROL-001",
            "activate",
            origin_ledger=active_delivery,
        )
        self.assertIn(
            "activation refused because the lane limit is full",
            busy_errors,
        )

        full_unchanged_errors, _ = evaluate_policy(
            copy.deepcopy(active_delivery),
            activation_facts,
            "PS-DELIVERY-CONTROL-001",
            "activate",
            origin_ledger=active_delivery,
        )
        self.assertIn(
            "activation refused because the lane limit is full",
            full_unchanged_errors,
        )

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
            "activation candidate exceeds the two-lane limit",
            two_addition_errors,
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
        policy_mutation["activation_policy"]["max_active_lanes"] = 3
        policy_errors, _ = evaluate_policy(
            policy_mutation,
            activation_facts,
            "PS-DELIVERY-CONTROL-001",
            "activate",
            origin_ledger=origin_one,
        )
        self.assertIn("activation may not change activation_policy", policy_errors)
        self.assertIn(
            "activation policy must retain the two-lane limit",
            policy_errors,
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
                approved_text.replace(
                    'updated_at: "2026-08-07"',
                    'updated_at: "2099-01-01"',
                    1,
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
                ("status", "--porcelain=v1"): "?? output/",
                ("remote", "get-url", "origin"): (
                    "https://dev.azure.com/peerslate19/portfolio-site/_git/portfolio-site"
                ),
                ("branch", "--show-current"): "main",
                ("rev-parse", "HEAD"): "abc",
                ("rev-parse", "origin/main"): "abc",
                ("rev-list", "--count", "abc..abc"): "0",
            }
            if command not in outputs:
                raise AssertionError(f"unexpected changed-path command: {command}")
            return outputs[command]

        with patch("scripts.delivery_preflight._git", side_effect=fake_git):
            collected = collect_facts()

        self.assertNotIn("changed_paths", collected)
        self.assertEqual(1, collected["untracked_changes"])

    def test_activation_fact_collection_includes_changed_paths(self):
        def fake_git(*args, **_kwargs):
            outputs = {
                ("status", "--porcelain=v1"): " M scripts/delivery_preflight.py",
                ("remote", "get-url", "origin"): (
                    "https://dev.azure.com/peerslate19/portfolio-site/_git/portfolio-site"
                ),
                ("branch", "--show-current"): (
                    "work/2026-08-04-delivery-activation-preflight-output"
                ),
                ("rev-parse", "HEAD"): "abc",
                ("rev-parse", "origin/main"): "abc",
                ("rev-list", "--count", "abc..abc"): "0",
                ("diff", "--name-only", "abc...abc"): "",
                ("diff", "--name-only"): "scripts/delivery_preflight.py",
                ("diff", "--cached", "--name-only"): "",
                ("ls-files", "--others", "--exclude-standard"): "output/note.txt",
            }
            return outputs[tuple(args)]

        with patch("scripts.delivery_preflight._git", side_effect=fake_git):
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
                (
                    "facts",
                    {"fetch": True, "include_changed_paths": True},
                ),
                ("origin", facts()["origin_main"]),
                ("candidate_baseline",),
                ("origin_baseline", facts()["origin_main"]),
            ],
            call_order,
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

    def test_bootstrap_control_repair_is_exact_and_one_time(self):
        repair_ledger = copy.deepcopy(self.ledger)
        origin_ledger = copy.deepcopy(repair_ledger)
        origin_ledger["bootstrap_control_repair"] = {
            "status": "previous_control_record"
        }
        bootstrap = repair_ledger["bootstrap_control_repair"]
        self.assertEqual(BOOTSTRAP_CONTROL_REPAIR, bootstrap)
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
            candidate_baseline=self.baseline + b"# forged activation baseline\n",
            origin_baseline=self.baseline,
        )
        self.assertIn(
            "bootstrap control repair must keep CURRENT_BASELINE.yaml byte-identical to exact origin/main",
            altered_baseline_errors,
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
        )
        self.assertIn(
            "bootstrap control repair may not change active lanes",
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
        )
        self.assertIn(
            "bootstrap control repair may not change operating_mode",
            mode_errors,
        )

        changed_policy = copy.deepcopy(repair_ledger)
        changed_policy["activation_policy"]["max_active_lanes"] = 3
        policy_errors, _ = evaluate_policy(
            changed_policy,
            exact,
            "PS-DELIVERY-CONTROL-001",
            "activate",
            require_clean=True,
            origin_ledger=origin_ledger,
        )
        self.assertIn(
            "activation may not change activation_policy",
            policy_errors,
        )

        stale_errors, _ = evaluate_policy(
            repair_ledger,
            {**exact, "origin_main": "new-main-after-merge"},
            "PS-DELIVERY-CONTROL-001",
            "activate",
            require_clean=True,
            origin_ledger=origin_ledger,
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
