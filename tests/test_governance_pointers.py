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
    def test_repository_agent_rules_are_short_and_link_to_current_authority(self):
        body = _read("AGENTS.md")
        self.assertLess(len(body.split()), 750)
        for target in re.findall(r"\]\(([^)#]+)(?:#[^)]+)?\)", body):
            with self.subTest(target=target):
                self.assertTrue(os.path.isfile(_path(*target.split("/"))), target)
        for term in (
            "delivery_preflight.py", "WORKTREE_LIFECYCLE.md",
            "AI_MODEL_AND_ROLE_ROUTING.md", "DOCUMENT_CONTROL.md",
            "OWNER_TECHNICAL_COMPLETION_REPORT.md", "PS-OPS-001",
            "claim never grants them", "session-health advisory",
            "non-gating context evidence", "agent-executed acceptance check",
        ):
            self.assertIn(term, body)

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
        self.assertEqual("4", governing["current_lanes"]["version"])
        self.assertEqual(
            "docs/governance/CURRENT_LANES.json",
            governing["current_lanes"]["path"],
        )
        self.assertEqual(
            "docs/governance/PEERSLATE_OWNER_DELIVERY_GUIDE.md",
            governing["owner_delivery_guide"]["path"],
        )
        ledger = json.loads(_read("docs", "governance", "CURRENT_LANES.json"))
        self.assertEqual(4, ledger["schema_version"])
        self.assertEqual(
            {
                "scope_release": "safe_custody_v1",
                "main_reconciliation": "safe_custody_v1",
                "registry_schema": 2,
            },
            ledger["capabilities"],
        )
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
            "Visual assignment does not make the designer the package manager",
            "claims carry no manager field",
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

    def test_pete_chooses_material_visual_creator(self):
        for parts in (
            ("AGENTS.md",),
            ("docs", "AI_WORKFLOW.md"),
            ("docs", "AI_MODEL_AND_ROLE_ROUTING.md"),
            ("docs", "governance", "OWNER_VISUAL_INTEGRITY_STANDARD.md"),
            ("docs", "governance", "OWNER_STORY_COMPOSITION_STANDARD.md"),
            ("docs", "templates", "PAGE_PURPOSE_AND_NON_REDUNDANCY_INVENTORY.md"),
        ):
            with self.subTest(parts=parts):
                body = " ".join(_read(*parts).split())
                self.assertRegex(
                    body, r"designer (Pete|he) chooses|Pete chooses who creates")
                for exclusive in (
                    "sole creator",
                    "sole visual-creation surface",
                    "ChatGPT creates",
                    "ChatGPT-created",
                    "ChatGPT Work design approval",
                    "Original ChatGPT",
                ):
                    self.assertNotIn(exclusive, body)
        self.assertIn("@AGENTS.md", _read("CLAUDE.md"))
        authority = " ".join(
            _read("docs", "AI_MODEL_AND_ROLE_ROUTING.md").split()
        )
        self.assertIn(
            "Pete chooses who creates new or materially revised production-intent visual authority, and Pete approves the images",
            authority,
        )
        self.assertIn(
            "only the designer Pete chooses may originate material visual direction",
            authority,
        )
        self.assertIn(
            "An agent that Pete has not chosen as the designer may not originate or substitute the visual authority",
            authority,
        )

    def test_visual_routing_matches_the_visual_standard(self):
        authority = " ".join(
            _read("docs", "AI_MODEL_AND_ROLE_ROUTING.md").split()
        )
        standard = " ".join(
            _read("docs", "governance", "OWNER_VISUAL_INTEGRITY_STANDARD.md").split()
        )
        self.assertIn("no mandatory pass count or separate mismatch ledger", standard)
        self.assertIn("no mandatory pass count or separate mismatch ledger", authority)
        for stale in ("empty mismatch register", "compare-refine loop"):
            self.assertNotIn(stale, authority)
        self.assertIn(
            "Pete reviews the corrected real build for final visual acceptance",
            authority,
        )

    def test_no_colour_or_palette_rule_in_current_authority(self):
        baseline = _read("docs", "governance", "CURRENT_BASELINE.yaml")
        self.assertNotRegex(baseline, r"(?m)^theme:")
        site_rules = " ".join(_read("docs", "PEERSLATE_SITE_RULES.md").split())
        self.assertNotIn("Deep Navy Gold", site_rules)
        self.assertNotIn("competing room themes", site_rules)
        self.assertIn("there is no separate colour or palette rule", site_rules)
        self.assertIn("Never recolor or alter member imagery", site_rules)
        rail = " ".join(
            _read("docs", "governance", "OWNER_CONTEXT_RAIL_STANDARD.md").split()
        )
        self.assertNotIn("Deep Navy Gold tokens only", rail)
        self.assertNotIn("exactly one gold active state", rail)
        self.assertIn("There is no palette mandate", rail)

    def test_equal_platform_standing_without_supervisor(self):
        agents = " ".join(_read("AGENTS.md").split())
        claude = " ".join(_read("CLAUDE.md").split())
        routing = " ".join(_read("docs", "AI_MODEL_AND_ROLE_ROUTING.md").split())
        self.assertIn(
            "Any assigned, access-verified capable platform has equal standing",
            agents,
        )
        self.assertIn("No platform needs another's supervision", agents)
        self.assertIn(
            "Claude has the same standing as any other assigned platform", claude)
        self.assertIn("without a Codex supervisor", claude)
        self.assertIn("There is no platform-exclusive gate", routing)
        self.assertIn("Codex remains the overall coordinator for now", routing)
        self.assertIn("no provider pairing is required", routing)
        self.assertIn("risk-based independent review still applies", routing)
        for parts in (("AGENTS.md",), ("START_HERE.md",)):
            with self.subTest(parts=parts):
                body = " ".join(_read(*parts).split())
                self.assertNotIn("unrevoked standing", body)
                self.assertRegex(
                    body,
                    r"standing bounded Workshop .{0,120}?expired when its parent claim closed",
                )

    def test_browser_changes_are_load_tested_before_pr(self):
        agents = " ".join(_read("AGENTS.md").split())
        for term in (
            "run the affected browser suite normally and once under load",
            "Rely on Playwright actionability",
            "never fixed sleeps",
            "Fix flaky tests or slow product paths instead of re-queueing",
            "must also skip cleanly when Playwright is unavailable",
            "Documentation-only and control-only changes keep their existing shortcuts",
        ):
            with self.subTest(term=term):
                self.assertIn(term, agents)

    def test_release_approval_is_case_by_case_with_exact_mechanics(self):
        for parts in (
            ("docs", "AI_WORKFLOW.md"),
            ("START_HERE.md",),
            ("docs", "governance", "PEERSLATE_OWNER_DELIVERY_GUIDE.md"),
        ):
            with self.subTest(parts=parts):
                body = " ".join(_read(*parts).split())
                self.assertIn("There is no blanket per-release approval", body)
                self.assertIn(
                    "says case by case when he must approve it himself", body)
        start = " ".join(_read("START_HERE.md").split())
        self.assertIn(
            "manualProductionSourceVersion=<exact 40-character main SHA>", start)
        self.assertIn("productionAuthorizationReference=", start)

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
        for route in (
            "Site management | **GPT-6.1 Sol, Extra High**",
            "Package management | **GPT-6.1 Sol, Extra High**",
            "Known-cause implementation | **GPT-6.1 Sol, High**",
            "Bounded supporting work | **GPT-6.1 Sol, Medium**",
            "Consequential architecture or cross-package decision | **GPT-6.1 Sol, High**",
            "Difficult unresolved debugging or integration | **GPT-6.1 Sol, Medium or High**",
            "Consequential independent security, privacy or architecture review | **Fresh GPT-6.1 Sol, Extra High**",
            "Final independent review when one is assigned, including a routine bounded final review | **Fresh GPT-6.1 Sol, Extra High**",
            "Other independent reviews | **Fresh GPT-6.1 Sol, Extra High**",
            "Routine release or closeout execution | **GPT-6.1 Sol, High**",
            "Demanding well-bounded implementation | **GPT-6.1 Sol, Extra High**",
        ):
            with self.subTest(route=route):
                self.assertIn(route, body)
        self.assertNotIn("Site or package management", body)
        self.assertIn(
            "Site and package managers use GPT-6.1 Sol Extra High",
            body,
        )
        self.assertNotIn("current central manager has Pete's explicit", body)
        self.assertNotIn("Independent reviewer | **Fresh GPT-6 Astra, High**", body)
        self.assertIn("verify the effective runtime setting", body)
        self.assertIn("inherited parent setting", body)
        self.assertIn("do not churn a setting", body)
        self.assertIn("A title alone never increases effort", body)
        self.assertIn("There is no mandatory architect or premium reviewer", body)
        self.assertIn("Explain the concrete reason before changing the implementation model", body)
        self.assertIn("new assignment or natural work boundary", body)
        self.assertIn("do not switch an active Navigation task or frozen reviewer", body)
        self.assertIn("None of them creates a review requirement", body)

    def test_claude_routing_is_current_and_excludes_haiku(self):
        body = " ".join(_read("docs", "AI_MODEL_AND_ROLE_ROUTING.md").split())
        for route in (
            "Architecture or independent review | **Claude Opus 5.5, Extra High**",
            "Management or known-cause implementation | **Claude Opus 5.5, High**",
            "Small or routine change | **Claude Sonnet 5.5, Medium**",
            "Claude assignments use Claude Opus 5.5 or Claude Sonnet 5.5 only",
            "Never use Claude Haiku",
            "Use Claude Fable only when Pete explicitly asks for it",
        ):
            with self.subTest(route=route):
                self.assertIn(route, body)
        for stale in ("**Claude Fable 5**", "**Claude Sonnet 5**", "**Claude Opus 5**"):
            self.assertNotIn(stale, body)
        claude = " ".join(_read("CLAUDE.md").split())
        self.assertIn(
            "Use Claude Opus 5.5 or Claude Sonnet 5.5 only. Never use Haiku.", claude)
        self.assertIn("Use Fable only when Pete explicitly asks", claude)

    def test_product_ai_direction_is_direction_only(self):
        raw = _read("docs", "AI_MODEL_AND_ROLE_ROUTING.md")
        body = " ".join(raw.split())
        self.assertIn("## Product AI direction", raw)
        self.assertIn("routine product AI features use Microsoft Foundry models", body)
        self.assertIn("the onboarding Guide and Ask Member AI", body)
        self.assertIn("New product work selects no Haiku model", body)
        self.assertIn("this document changes no runtime model", body)

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
        self.assertIn("send the central manager only an actionable cross-package blocker", normalized)
        self.assertIn("coordinate ordinary dependencies with the affected owner", normalized)
        self.assertIn("central may end its turn and react to the next callback", normalized)
        self.assertIn("do not add central polling or duplicate result collection", normalized)
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
