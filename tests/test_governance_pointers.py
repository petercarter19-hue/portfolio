"""Lean guardrails for PeerSlate's current authority and delivery model.

These tests protect safety and unambiguous pointers. Historical release wording
belongs to package evidence and must not be hard-coded into the startup gate.
"""

import json
import os
import re
import unittest

from control_room_projection import parse_yaml_subset


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _path(*parts):
    return os.path.join(ROOT, *parts)


def _read(*parts):
    with open(_path(*parts), "r", encoding="utf-8", errors="ignore") as handle:
        return handle.read()


class LeanStartupTests(unittest.TestCase):
    def test_supported_agents_enter_through_one_start_file(self):
        for filename in ("AGENTS.md", "CLAUDE.md"):
            body = _read(filename)
            self.assertIn("MANDATORY PRE-WORK GATE", body)
            self.assertIn("START_HERE", body)
            self.assertIn("CURRENT_BASELINE.yaml", body)
            self.assertIn("Routine", body)
            self.assertIn("Bounded", body)
            self.assertIn("Protected", body)

    def test_startup_is_safe_and_proportional(self):
        body = _read("START_HERE.md")
        self.assertIn("git status --short --branch", body)
        self.assertIn("git fetch origin --prune", body)
        self.assertIn("preserve", body.lower())
        self.assertIn("clean worktree", body)
        self.assertIn("Read only what the task needs", body)
        self.assertNotIn("CURRENT_STATE.md", body)
        self.assertNotIn("ACTIVE_INITIATIVES.md", body)
        self.assertLess(len(body.split()), 600)

    def test_workflow_has_three_paths_and_no_universal_specialist_gate(self):
        body = _read("docs", "AI_WORKFLOW.md")
        for term in ("Routine", "Bounded", "Protected"):
            self.assertIn(term, body)
        self.assertIn("unless its delivery path or package specifically triggers it", body)
        self.assertIn("None blocks unrelated Routine or Bounded work", body)
        self.assertIn("Documentation-only closeout", body)
        self.assertIn("[skip ci]", body)
        self.assertIn("Do not restart App Service merely to publish bookkeeping", body)
        self.assertLess(len(body.split()), 1100)


class ControlPlaneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.body = _read("docs", "governance", "CURRENT_BASELINE.yaml")
        cls.data = parse_yaml_subset(cls.body)

    def test_control_plane_is_current_and_concise(self):
        self.assertEqual("5", self.data.get("schema_version"))
        self.assertEqual("2026-08-08", self.data.get("updated_at"))
        self.assertLess(len(self.body.split()), 900)
        self.assertNotIn("planned_packages:", self.body)
        self.assertNotIn("holds:", self.body)

    def test_current_constitution_and_roadmap_are_v3(self):
        governing = self.data["governing_documents"]
        self.assertEqual("3.0", governing["bible"]["version"])
        self.assertEqual(
            "docs/governance/PeerSlate_Constitution_v3.0.md",
            governing["bible"]["path"],
        )
        self.assertEqual("3.0", governing["roadmap"]["version"])
        self.assertEqual(
            "docs/governance/PeerSlate_Roadmap_v3.0.md",
            governing["roadmap"]["path"],
        )

    def test_all_current_paths_exist(self):
        paths = re.findall(r'^\s+(?:path|package_path): "([^"]+)"', self.body, re.M)
        self.assertGreater(len(paths), 10)
        for rel in paths:
            with self.subTest(path=rel):
                self.assertTrue(os.path.exists(_path(*rel.split("/"))), rel)

    def test_active_packages_are_unique_and_scoped(self):
        active = self.data.get("active_packages") or []
        ids = [item["id"] for item in active]
        self.assertEqual(len(ids), len(set(ids)))
        lane_document = json.loads(
            _read("docs", "governance", "CURRENT_LANES.json")
        )
        lane_ids = [item["package"] for item in lane_document["active_lanes"]]
        self.assertEqual(set(lane_ids), set(ids))
        for item in active:
            with self.subTest(package=item["id"]):
                self.assertEqual("active_delivery", item["status"])
                self.assertTrue(item["scope"].strip())
        self.assertIn(
            "PS-DELIVERY-RESET-001",
            self.data.get("completed_packages") or [],
        )
        self.assertIn("PS-GOV-LEAN-001", self.data.get("completed_packages") or [])

    def test_current_lane_ledger_is_named_and_machine_readable(self):
        governing = self.data["governing_documents"]
        self.assertEqual("1", governing["current_lanes"]["version"])
        self.assertEqual(
            "docs/governance/CURRENT_LANES.json",
            governing["current_lanes"]["path"],
        )
        self.assertEqual(
            "docs/governance/PEERSLATE_OWNER_DELIVERY_GUIDE.md",
            governing["owner_delivery_guide"]["path"],
        )
        ledger = _read("docs", "governance", "CURRENT_LANES.json")
        # The ledger records whichever operating state the owner selected; it
        # must name one of the two valid states, not stay frozen at idle.
        self.assertTrue(
            '"controlled_idle"' in ledger or '"active_delivery"' in ledger
        )
        self.assertIn('"activation_policy"', ledger)
        self.assertIn('"PS-DELIVERY-CONTROL-001"', ledger)
        self.assertIn('"cleanup_authorized": true', ledger)
        self.assertIn('"cleanup_allowed_for"', ledger)

    def test_production_truth_is_separate_from_current_git(self):
        authority = self.data["authority"]
        self.assertEqual("origin", authority["remote"])
        self.assertEqual("azure_devops", authority["host"])
        self.assertRegex(authority["application_behavior_commit"], r"^[0-9a-f]{40}$")
        self.assertIn("not a substitute", authority["note"])

    def test_baseline_and_lane_ledger_pin_the_same_production_release(self):
        """The two live control-plane records must move in lockstep.

        This catches the exact drift that left the baseline on run 557 while
        production was already serving run 560.
        """
        authority = self.data["authority"]
        lane_document = json.loads(
            _read("docs", "governance", "CURRENT_LANES.json")
        )
        release = lane_document["release_truth"]
        for key in (
            "deployed_main_commit",
            "live_release",
            "application_behavior_commit",
        ):
            with self.subTest(key=key):
                self.assertEqual(authority[key], release[key])
        for key in ("deployed_pipeline", "application_behavior_pipeline"):
            with self.subTest(key=key):
                self.assertEqual(authority[key], str(release[key]))


class ProductTrustTests(unittest.TestCase):
    def test_constitution_retains_the_trust_contract(self):
        body = _read("docs", "governance", "PeerSlate_Constitution_v3.0.md")
        normalized = " ".join(body.split())
        for phrase in (
            "Private before public",
            "Create once, use by reference",
            "AI proposes",
            "Authorization happens before retrieval",
            "Truthful, accessible craft",
            "not a job board",
            "Save Moment creates one private canonical Moment",
        ):
            self.assertIn(phrase, normalized)
        self.assertLess(len(body.split()), 1000)

    def test_site_rules_keep_multi_user_privacy_and_ai_boundaries(self):
        body = _read("docs", "PEERSLATE_SITE_RULES.md")
        for phrase in (
            "private by default",
            "AI output remains a proposal",
            "no job posts",
            "WCAG 2.2 AA",
            "Save Moment",
        ):
            self.assertIn(phrase.lower(), body.lower())

    def test_visual_standard_is_strict_when_triggered_but_not_universal(self):
        body = _read("docs", "governance", "OWNER_VISUAL_INTEGRITY_STANDARD.md")
        normalized = " ".join(body.split())
        self.assertIn("new production page", body)
        self.assertIn("Pete locks", body)
        self.assertIn("Side-by-side screenshots", body)
        self.assertIn("representative desktop and mobile", body)
        self.assertIn("do not require a\nnew page inventory", body)
        self.assertIn("There is no mandatory pass count", body)
        self.assertIn("character and materiality pass", normalized)
        self.assertIn("design default, not an effects quota", normalized)
        self.assertIn(
            "Framework-default or visibly unfinished flatness", normalized)
        self.assertIn(
            "adds no separate gate, artifact, pass count, or retrofit backlog",
            normalized)
        self.assertLess(len(body.split()), 900)

    def test_chatgpt_remains_material_visual_creator(self):
        for parts in (
            ("AGENTS.md",),
            ("CLAUDE.md",),
            ("docs", "AI_WORKFLOW.md"),
            ("docs", "governance", "OWNER_VISUAL_INTEGRITY_STANDARD.md"),
        ):
            body = _read(*parts)
            self.assertIn("ChatGPT", body)
            self.assertRegex(body, r"(?i)creat(e|es|or)")
            self.assertRegex(body, r"(?i)material")

    def test_protected_release_controls_are_triggered(self):
        body = " ".join(_read("docs", "initiatives", "PS-OPS-001", "README.md").replace(">", "").split())
        self.assertIn("Current applicability", body)
        self.assertIn("Gate Candidate applies to a release", body)
        self.assertIn("Routine and Bounded releases", body)
        self.assertIn("do not require a Candidate admission record", body)


class NoGlobalFreezeTests(unittest.TestCase):
    def test_checkpoint_findings_are_scoped(self):
        for parts in (
            ("docs", "initiatives", "PS-AI-OPS-CHECKPOINT-001", "README.md"),
            ("docs", "governance", "AI_DELIVERY_AUDIT_REGISTER.md"),
        ):
            body = _read(*parts)
            normalized = " ".join(body.split()).lower()
            self.assertRegex(normalized, r"routine (?:or|and) bounded")
            self.assertIn("may proceed", normalized)
            self.assertNotIn("No unrelated runtime implementation slice should start", body)

    def test_old_parallel_state_files_are_archives(self):
        for filename in ("CURRENT_STATE.md", "ACTIVE_INITIATIVES.md"):
            head = "\n".join(
                _read("docs", "governance", filename).splitlines()[:12]
            )
            self.assertIn("Historical", head)
            self.assertRegex(head, r"(no longer|do not require)")

    def test_document_control_has_one_live_control_plane(self):
        body = _read("docs", "governance", "DOCUMENT_CONTROL.md")
        self.assertIn("smallest authoritative record", body)
        self.assertIn("Do not copy the same release narrative", body)
        self.assertIn("historical evidence", body)

    def test_handoff_and_completion_are_proportional(self):
        handoff = _read("docs", "governance", "MANAGER_SESSION_HANDOFF.md")
        completion = _read("docs", "templates", "OWNER_TECHNICAL_COMPLETION_REPORT.md")
        self.assertIn("Use this only when another person or agent will continue", handoff)
        self.assertIn("Protected additions - only when applicable", completion)
        self.assertLess(len(handoff.split()), 300)
        self.assertLess(len(completion.split()), 350)

    def test_historical_authorities_remain_available(self):
        for filename in (
            "PeerSlate_Company_and_Product_Bible_v2.9.md",
            "PeerSlate_Company_and_Product_Bible_v2.9.docx",
            "PeerSlate_Product_Strategy_and_Architecture_Roadmap_v2.8.md",
            "PeerSlate_Product_Strategy_and_Architecture_Roadmap_v2.8.docx",
        ):
            self.assertTrue(os.path.isfile(_path("docs", "governance", filename)), filename)


if __name__ == "__main__":
    unittest.main()
