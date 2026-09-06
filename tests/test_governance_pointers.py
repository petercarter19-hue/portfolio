"""Lean guardrails for PeerSlate's current authority and delivery model.

These tests protect safety and unambiguous pointers. Historical release wording
belongs to package evidence and must not be hard-coded into the startup gate.
"""

import json
import os
import re
import subprocess
import unittest
from datetime import date

from control_room_projection import parse_yaml_subset


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _path(*parts):
    return os.path.join(ROOT, *parts)


def _read(*parts):
    with open(_path(*parts), "r", encoding="utf-8", errors="ignore") as handle:
        return handle.read()


class LeanStartupTests(unittest.TestCase):
    def test_supported_agents_enter_through_one_start_file(self):
        body = _read("AGENTS.md")
        self.assertIn("MANDATORY PRE-WORK GATE", body)
        self.assertIn("START_HERE", body)
        self.assertIn("CURRENT_BASELINE.yaml", body)
        for term in ("Routine", "Bounded", "Protected", "control-only"):
            self.assertIn(term, body)
        self.assertIn("--intent read", body)
        claude = _read("CLAUDE.md")
        self.assertIn("@AGENTS.md", claude)
        self.assertIn("@docs/AI_WORKFLOW.md", claude)
        self.assertIn("MANDATORY PRE-WORK GATE", claude)
        self.assertLess(len(claude.split()), 300)

    def test_manager_and_specialist_routing_is_visible_at_startup(self):
        body = _read("AGENTS.md")
        self.assertIn(
            "[AI model and role routing](docs/AI_MODEL_AND_ROLE_ROUTING.md)",
            body,
        )
        normalized = " ".join(body.split())
        self.assertIn("Overall audit manager, package manager", normalized)
        self.assertIn("no role silently inherits another", normalized)

    def test_startup_is_safe_and_proportional(self):
        body = _read("START_HERE.md")
        self.assertIn("git status --short --branch", body)
        self.assertIn("git fetch origin --prune", body)
        self.assertIn("preserve", body.lower())
        self.assertIn("clean worktree", body)
        self.assertIn("Read only what the task needs", body)
        self.assertIn("control-only", body)
        self.assertIn("matching control intent", body)
        self.assertNotIn("CURRENT_STATE.md", body)
        self.assertNotIn("ACTIVE_INITIATIVES.md", body)

    def test_workflow_has_three_paths_and_no_universal_specialist_gate(self):
        body = _read("docs", "AI_WORKFLOW.md")
        normalized = " ".join(body.split())
        for term in ("Routine", "Bounded", "Protected"):
            self.assertIn(term, body)
        self.assertIn("unless its delivery path or package specifically triggers it", normalized)
        self.assertIn("None blocks unrelated Routine or Bounded work", normalized)
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
        updated_at = self.data.get("updated_at")
        self.assertRegex(updated_at, r"^\d{4}-\d{2}-\d{2}$")
        self.assertEqual(updated_at, date.fromisoformat(updated_at).isoformat())
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

    def test_model_and_role_routing_pointer_is_canonical(self):
        governing = self.data["governing_documents"]
        self.assertEqual(
            "docs/AI_MODEL_AND_ROLE_ROUTING.md",
            governing["model_and_role_routing"]["path"],
        )

    def test_all_current_paths_exist(self):
        paths = re.findall(r'^\s+(?:path|package_path): "([^"]+)"', self.body, re.M)
        self.assertGreater(len(paths), 10)
        for rel in paths:
            with self.subTest(path=rel):
                self.assertTrue(os.path.exists(_path(*rel.split("/"))), rel)

    def test_active_claims_are_the_single_unique_scope_source(self):
        self.assertNotIn("active_packages", self.data)
        claims_root = _path("docs", "governance", "lane_claims")
        active = []
        for filename in os.listdir(claims_root):
            if not filename.startswith("PS-") or not filename.endswith(".json"):
                continue
            claim = json.loads(_read("docs", "governance", "lane_claims", filename))
            if claim["state"] == "active":
                active.append(claim)
        ids = [item["package"] for item in active]
        self.assertEqual(len(ids), len(set(ids)))
        for item in active:
            with self.subTest(package=item["package"]):
                self.assertTrue(item["outcome"].strip())
                self.assertTrue(item["surfaces"])
                self.assertTrue(item["domains"])
        self.assertIn(
            "PS-DELIVERY-RESET-001",
            self.data.get("completed_packages") or [],
        )
        self.assertIn("PS-GOV-LEAN-001", self.data.get("completed_packages") or [])

    def test_current_lane_ledger_is_named_and_machine_readable(self):
        governing = self.data["governing_documents"]
        self.assertEqual("3", governing["current_lanes"]["version"])
        self.assertEqual(
            "docs/governance/CURRENT_LANES.json",
            governing["current_lanes"]["path"],
        )
        self.assertEqual(
            "docs/governance/PEERSLATE_OWNER_DELIVERY_GUIDE.md",
            governing["owner_delivery_guide"]["path"],
        )
        ledger = json.loads(_read("docs", "governance", "CURRENT_LANES.json"))
        self.assertEqual(3, ledger["schema_version"])
        self.assertEqual("generic_package_claims_v1", ledger["model"])
        self.assertEqual("docs/governance/lane_claims", ledger["claims_path"])
        self.assertEqual("unbounded_while_disjoint", ledger["rules"]["writer_capacity"])
        self.assertFalse(ledger["rules"]["reviewers_consume_writer_claim"])
        self.assertRegex(ledger["legacy_snapshot"]["commit"], r"^[0-9a-f]{40}$")
        self.assertRegex(ledger["legacy_snapshot"]["blob"], r"^[0-9a-f]{40}$")
        self.assertLess(len(json.dumps(ledger).split()), 100)

    def test_claim_review_merge_close_is_documented_consistently(self):
        for parts in (
            ("AGENTS.md",),
            ("CLAUDE.md",),
            ("START_HERE.md",),
            ("docs", "AI_WORKFLOW.md"),
            ("docs", "governance", "AGENT_STARTUP_CHECKLIST.md"),
            ("docs", "governance", "PEERSLATE_OWNER_DELIVERY_GUIDE.md"),
        ):
            body = _read(*parts).lower()
            for term in ("claim", "merge", "close"):
                self.assertIn(term, body, f"{term} missing from {'/'.join(parts)}")
        workflow = _read("docs", "AI_WORKFLOW.md")
        self.assertIn("No separate owner merge grant is", workflow)
        self.assertIn("reviewer is read-only", workflow)
        self.assertIn("exact-SHA review", workflow)

    def test_unbounded_disjoint_writers_keep_collision_and_authority_controls(self):
        ledger = json.loads(
            _read("docs", "governance", "CURRENT_LANES.json")
        )
        rules = ledger["rules"]
        self.assertEqual("unbounded_while_disjoint", rules["writer_capacity"])
        self.assertFalse(rules["reviewers_consume_writer_claim"])
        self.assertIn("through_merge", rules["assigned_repository_authority"])
        self.assertIn("manual_exact_main_sha", rules["production_operations"])

        for parts in (
            ("AGENTS.md",),
            ("START_HERE.md",),
            ("docs", "governance", "AGENT_STARTUP_CHECKLIST.md"),
            ("docs", "governance", "PEERSLATE_OWNER_DELIVERY_GUIDE.md"),
        ):
            normalized = " ".join(
                _read(*parts).lower().replace(">", " ").split()
            )
            self.assertRegex(normalized, r"(?:no fixed|no numeric|unlimited|any number)")
            self.assertIn("collision", normalized, "/".join(parts))
            self.assertIn("production", normalized, "/".join(parts))
        self.assertIn("@AGENTS.md", _read("CLAUDE.md"))

        active_packages = []
        claims_root = _path("docs", "governance", "lane_claims")
        for filename in os.listdir(claims_root):
            if filename.startswith("PS-") and filename.endswith(".json"):
                claim = json.loads(_read("docs", "governance", "lane_claims", filename))
                if claim["state"] == "active":
                    active_packages.append(claim["package"])
        current_assignments = self.data["manager"]["current_assignments"]
        self.assertIn("docs/governance/lane_claims", current_assignments)

    def test_production_truth_is_separate_from_current_git(self):
        authority = self.data["authority"]
        self.assertEqual("origin", authority["remote"])
        self.assertEqual("azure_devops", authority["host"])
        self.assertRegex(authority["application_behavior_commit"], r"^[0-9a-f]{40}$")
        self.assertIn("not a substitute", authority["note"])

    def test_legacy_lane_ledger_is_pinned_by_git_identity(self):
        lane_document = json.loads(
            _read("docs", "governance", "CURRENT_LANES.json")
        )
        legacy = lane_document["legacy_snapshot"]
        self.assertEqual("docs/governance/CURRENT_LANES.json", legacy["path"])
        blob = subprocess.check_output(
            ["git", "rev-parse", f"{legacy['commit']}:{legacy['path']}"],
            cwd=ROOT,
            text=True,
        ).strip()
        self.assertEqual(legacy["blob"], blob)


class ProductTrustTests(unittest.TestCase):
    def test_package_manager_routing_stays_clear_and_bounded(self):
        body = " ".join(
            _read("docs", "AI_MODEL_AND_ROLE_ROUTING.md").split()
        )
        for phrase in (
            "Every package activated or transferred under this rule names exactly one package manager",
            "records its manager at its next handoff",
            "Selection is based on the package outcome and evidence needed",
            "ChatGPT Work is not mandatory for every package",
            "Assigned capable environment",
            "No hidden Codex manager or Codex supervisory approval is required",
            "Visual assignment does not make Original ChatGPT the package manager",
            "Being package manager grants no repository, writer, merge, release, deployment, credential, or production-operator authority",
            "The accepted package assigns its manager and writer explicitly",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, body)
        completion = _read(
            "docs", "templates", "OWNER_TECHNICAL_COMPLETION_REPORT.md"
        )
        self.assertIn("Package manager and why", completion)
        self.assertIn("Triggered specialists and return target", completion)

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
            ("docs", "AI_WORKFLOW.md"),
            ("docs", "AI_MODEL_AND_ROLE_ROUTING.md"),
            ("docs", "governance", "OWNER_VISUAL_INTEGRITY_STANDARD.md"),
        ):
            body = _read(*parts)
            self.assertIn("ChatGPT", body)
            self.assertRegex(body, r"(?i)creat(e|es|or)")
            self.assertRegex(body, r"(?i)material")
        self.assertIn("@AGENTS.md", _read("CLAUDE.md"))
        authority = " ".join(
            _read("docs", "AI_MODEL_AND_ROLE_ROUTING.md").split()
        )
        self.assertIn(
            "Original ChatGPT is the sole creator of new or materially revised production-intent visual authority",
            authority,
        )
        self.assertIn(
            "ChatGPT Work, Codex, Claude Chat, Co-Work, Code, and Design may not originate or substitute the visual authority",
            authority,
        )

    def test_protected_release_controls_are_triggered(self):
        body = " ".join(_read("docs", "initiatives", "PS-OPS-001", "README.md").replace(">", "").split())
        self.assertIn("Current applicability", body)
        self.assertIn("Gate Candidate applies to a release", body)
        self.assertIn("Routine and Bounded releases", body)
        self.assertIn("do not require a Candidate admission record", body)


class WorkflowEfficiencyTests(unittest.TestCase):
    def test_launcher_uses_current_gate_without_stale_friction(self):
        body = _read("CODEX_PROMPT.md")
        for stale in (
            "CURRENT_STATE.md",
            "ACTIVE_INITIATIVES.md",
            "delete the branch immediately",
            "ask before creating",
        ):
            self.assertNotIn(stale, body)
        self.assertIn("current Azure `origin/main`", body)
        self.assertIn("continue through tests", body)
        self.assertIn("eligible lifecycle", body)

    def test_openai_role_defaults_require_actual_runtime_verification(self):
        body = " ".join(_read("docs", "AI_MODEL_AND_ROLE_ROUTING.md").split())
        self.assertIn("Manager | **GPT-6 Astra, Medium**", body)
        self.assertIn("Implementer | **Sol, High**", body)
        self.assertIn("Delegated helper | **Sol, Medium**", body)
        self.assertNotIn("current central manager has Pete's explicit", body)
        self.assertIn("verify the effective runtime setting", body)
        self.assertIn("inherited parent setting", body)
        self.assertIn("do not churn a setting", body)

    def test_complete_transfer_requires_access_acceptance_without_credentials(self):
        bodies = [
            _read("docs", "AI_WORKFLOW.md"),
            _read("docs", "AI_MODEL_AND_ROLE_ROUTING.md"),
            _read("docs", "governance", "MANAGER_SESSION_HANDOFF.md"),
            _read("docs", "governance", "PEERSLATE_OWNER_DELIVERY_GUIDE.md"),
        ]
        joined = " ".join(body.lower() for body in bodies)
        self.assertIn("without a hidden codex supervisor", joined)
        self.assertIn("receiver acceptance", joined)
        self.assertIn("project/repository access", joined)
        self.assertIn("session-only authority", joined)
        self.assertIn("credentials", joined)
        manager = parse_yaml_subset(
            _read("docs", "governance", "CURRENT_BASELINE.yaml")
        )["manager"]
        self.assertIn("Any supported environment", manager["eligible_tools"])
        self.assertIn("access-verified", manager["eligible_tools"])

    def test_usage_and_completion_fields_preserve_subset_and_evidence_boundaries(self):
        completion = " ".join(
            _read(
                "docs", "templates", "OWNER_TECHNICAL_COMPLETION_REPORT.md"
            ).lower().split()
        )
        self.assertIn("cached-input subset", completion)
        self.assertIn("reasoning-output subset already included in output", completion)
        self.assertIn("never a live-usage", completion)
        self.assertIn("merge-gate claim", completion)
        self.assertIn("known waiting", completion)
        self.assertIn("never infer waiting", completion)
        for field in ("accepted outcome", "rework", "interventions"):
            self.assertIn(field, completion)

    def test_event_driven_reporting_and_single_continuity_pointer(self):
        routing = _read("docs", "AI_MODEL_AND_ROLE_ROUTING.md")
        normalized = " ".join(routing.lower().split())
        for term in (
            "acknowledgement loops",
            "periodic model turns",
            "cache warmers",
            "duplicate reviews",
            "unrelated audits",
        ):
            self.assertIn(term, normalized)
        self.assertEqual(
            routing.lower().count("session-continuity:session-continuity"), 1
        )
        self.assertIn("session-health advisories are approximate, non-gating", normalized)
        self.assertIn("continuity never transfers authorization or ownership", normalized)
        self.assertNotIn(r"c:\users", routing.lower())


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
        self.assertIn("Use this only when ownership changes", handoff)
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
