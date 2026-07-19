"""Dependency-free guardrails for PeerSlate's repository authority chain."""

import os
import re
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(*parts):
    with open(os.path.join(ROOT, *parts), "r", encoding="utf-8", errors="ignore") as file:
        return file.read()


def _exists(*parts):
    return os.path.exists(os.path.join(ROOT, *parts))


class StartHereEntryPointTests(unittest.TestCase):
    """Every supported tool must enter through the same controlled startup."""

    def test_start_here_exists(self):
        self.assertTrue(_exists("START_HERE.md"))

    def test_brain_files_require_start_here_and_current_authority(self):
        for filename in ("AGENTS.md", "CLAUDE.md"):
            with self.subTest(filename=filename):
                body = _read(filename)
                self.assertIn("MANDATORY PRE-WORK GATE", body)
                self.assertIn("START_HERE", body)
                self.assertIn("CURRENT_BASELINE.yaml", body)
                self.assertIn("DOCUMENT_CONTROL.md", body)
                self.assertIn("ChatGPT Work", body)
                self.assertIn("OWNER_VISUAL_INTEGRITY_STANDARD.md", body)
                self.assertIn("OWNER_STORY_COMPOSITION_STANDARD.md", body)
                self.assertNotIn("## v1.3 governance", body)

    def test_startup_inspects_before_switching(self):
        body = _read("START_HERE.md")
        self.assertLess(body.index("git status --short --branch"), body.index("git switch main"))
        self.assertIn("identify and preserve", body)


class GovernanceRecordsTests(unittest.TestCase):
    """Required state, control, package, and closeout records must exist."""

    REQUIRED = (
        ("docs", "governance", "CURRENT_BASELINE.yaml"),
        ("docs", "governance", "CURRENT_STATE.md"),
        ("docs", "governance", "ACTIVE_INITIATIVES.md"),
        ("docs", "governance", "AGENT_STARTUP_CHECKLIST.md"),
        ("docs", "governance", "DOCUMENT_CONTROL.md"),
        ("docs", "governance", "DECISIONS.md"),
        ("docs", "governance", "OWNER_VISUAL_INTEGRITY_STANDARD.md"),
        ("docs", "governance", "OWNER_STORY_COMPOSITION_STANDARD.md"),
        ("docs", "governance", "MANAGER_SESSION_HANDOFF.md"),
        ("docs", "templates", "OWNER_TECHNICAL_COMPLETION_REPORT.md"),
        ("docs", "initiatives", "PS-GOV-001", "README.md"),
        ("docs", "initiatives", "PS-GOV-001", "COMPLETION_REPORT.md"),
        ("docs", "initiatives", "PS-BASELINE-001", "README.md"),
        ("docs", "initiatives", "PS-BASELINE-001", "COMPLETION_REPORT.md"),
        ("docs", "initiatives", "PS-CAPTURE-002", "README.md"),
        ("docs", "initiatives", "PS-CAPTURE-002", "COMPLETION_REPORT.md"),
        ("docs", "initiatives", "PS-RESUME-PUBLIC-REFINE-001", "README.md"),
        ("docs", "initiatives", "PS-RESUME-PUBLIC-REFINE-001", "COMPLETION_REPORT.md"),
        ("docs", "initiatives", "PS-INTERVIEW-PUBLIC-GATE-001", "README.md"),
        ("docs", "initiatives", "PS-INTERVIEW-PUBLIC-GATE-001", "COMPLETION_REPORT.md"),
        ("docs", "initiatives", "PS-MOMENT-001", "README.md"),
        ("docs", "initiatives", "PS-MOMENT-001", "COMPLETION_REPORT.md"),
        ("docs", "initiatives", "PS-PLACEMENT-001", "README.md"),
        ("docs", "initiatives", "PS-PLACEMENT-001", "COMPLETION_REPORT.md"),
        ("docs", "initiatives", "PS-BACKEND-NEXT-GATE-MANAGER-001", "README.md"),
        ("docs", "initiatives", "PS-BACKEND-NEXT-GATE-MANAGER-001", "COMPLETION_REPORT.md"),
        ("docs", "initiatives", "PS-PLACEMENT-RELEASE-MANAGER-001", "README.md"),
        ("docs", "initiatives", "PS-PLACEMENT-RELEASE-MANAGER-001", "COMPLETION_REPORT.md"),
        ("docs", "initiatives", "PS-VOICE-CAPTURE-MANAGER-001", "README.md"),
        ("docs", "initiatives", "PS-VOICE-CAPTURE-MANAGER-001", "COMPLETION_REPORT.md"),
        ("docs", "initiatives", "PS-VOICE-001", "README.md"),
        ("docs", "initiatives", "PS-VOICE-001", "01_ARCHITECTURE.md"),
        ("docs", "initiatives", "PS-VOICE-001", "02_SECURITY_PRIVACY.md"),
        ("docs", "initiatives", "PS-VOICE-001", "03_INFRASTRUCTURE.md"),
        ("docs", "initiatives", "PS-VOICE-001", "04_TEST_RELEASE_PLAN.md"),
        ("docs", "initiatives", "PS-VOICE-001", "05_IMPLEMENTATION_PLAN.md"),
        ("docs", "initiatives", "PS-VOICE-001", "06_VISUAL_PARITY_CORRECTION.md"),
        ("docs", "initiatives", "PS-VOICE-001", "COMPLETION_REPORT.md"),
        ("docs", "initiatives", "PS-SELF-MANAGED-LANES-001", "README.md"),
        ("docs", "initiatives", "PS-SELF-MANAGED-LANES-001", "COMPLETION_REPORT.md"),
        ("docs", "initiatives", "PS-NEXT-WAVE-MANAGER-001", "README.md"),
        ("docs", "initiatives", "PS-NEXT-WAVE-MANAGER-001", "COMPLETION_REPORT.md"),
        ("docs", "initiatives", "PS-VISUAL-INTEGRITY-GOV-001", "README.md"),
        ("docs", "initiatives", "PS-VISUAL-INTEGRITY-GOV-001", "COMPLETION_REPORT.md"),
        ("docs", "initiatives", "PS-STORY-COMPOSER-DIRECTION-001", "README.md"),
        ("docs", "initiatives", "PS-STORY-COMPOSER-DIRECTION-001", "COMPLETION_REPORT.md"),
    )

    def test_required_records_exist(self):
        missing = [os.path.join(*parts) for parts in self.REQUIRED if not _exists(*parts)]
        self.assertEqual([], missing, f"Missing governance records: {missing}")

    def test_completion_reports_have_owner_template_sections(self):
        reports = [parts for parts in self.REQUIRED if parts[-1] == "COMPLETION_REPORT.md"]
        for parts in reports:
            body = _read(*parts)
            with self.subTest(report=os.path.join(*parts)):
                for letter in "ABCDEFGHI":
                    self.assertRegex(body, rf"(?m)^## {letter}\.")


class BaselineCoherenceTests(unittest.TestCase):
    """The baseline must resolve and agree with human-readable coordination."""

    @classmethod
    def setUpClass(cls):
        cls.baseline = _read("docs", "governance", "CURRENT_BASELINE.yaml")
        cls.state = _read("docs", "governance", "CURRENT_STATE.md")
        cls.initiatives = _read("docs", "governance", "ACTIVE_INITIATIVES.md")

    def test_every_baseline_path_resolves(self):
        paths = re.findall(r'path:\s*"([^"]+)"', self.baseline)
        self.assertGreaterEqual(len(paths), 10)
        stale = []
        for relative_path in paths:
            parts = relative_path.rstrip("/").split("/")
            if not _exists(*parts):
                stale.append(relative_path)
        self.assertEqual([], stale, f"Baseline points at missing paths: {stale}")

    def test_baseline_names_current_authority_and_manager(self):
        self.assertIn("Bible_v2.5", self.baseline)
        self.assertIn("Roadmap_v2.4", self.baseline)
        self.assertIn('tool: "ChatGPT Work"', self.baseline)
        self.assertIn("PS-GOV-001", self.baseline)
        self.assertIn("PS-BASELINE-001", self.baseline)
        self.assertIn("PS-NEXT-WAVE-MANAGER-001", self.baseline)
        self.assertIn("PS-SELF-MANAGED-LANES-001", self.baseline)
        self.assertIn("manager_setup_pipeline: 80", self.baseline)
        self.assertIn(
            'voice_activation_merge_commit: "5488819ad13d3f411319d7e184fde3779d62b8d2"',
            self.baseline,
        )
        self.assertIn("voice_activation_pipeline: 97", self.baseline)
        self.assertIn(
            'visual_integrity_merge_commit: "28ec01097677219bbe466ff2c731707d0e4a2b89"',
            self.baseline,
        )
        self.assertIn("visual_integrity_pipeline: 99", self.baseline)
        self.assertIn("PS-PLACEMENT-001", self.baseline)
        self.assertIn("application_behavior_pipeline: 105", self.baseline)
        self.assertIn("eede8565d703a466bd788962d494e8b385b53409", self.baseline)
        self.assertIn("OWNER_VISUAL_INTEGRITY_STANDARD.md", self.baseline)
        self.assertIn("OWNER_STORY_COMPOSITION_STANDARD.md", self.baseline)
        self.assertIn("MANAGER_SESSION_HANDOFF.md", self.baseline)
        self.assertIn('delivery_model: "self_managed_lanes"', self.baseline)
        self.assertIn("voice_release_pipeline: 105", self.baseline)
        self.assertIn("eede8565d703a466bd788962d494e8b385b53409", self.baseline)

    def test_active_package_paths_and_coordination_agree(self):
        active_block = re.search(
            r"(?ms)^active_packages:\s*$\n(.*?)(?=^[a-z_]+:|\Z)", self.baseline
        )
        self.assertIsNotNone(active_block)
        active_ids = re.findall(r"(?m)^\s+- id:\s+([A-Z0-9-]+)\s*$", active_block.group(1))
        package_paths = re.findall(r'package_path:\s*"([^"]+)"', active_block.group(1))
        self.assertEqual(
            ["PS-INTERVIEW-PUBLIC-GATE-001", "PS-VOICE-001"], active_ids
        )
        self.assertEqual(len(active_ids), len(package_paths))
        for package_id, relative_path in zip(active_ids, package_paths):
            with self.subTest(package=package_id):
                self.assertTrue(_exists(*relative_path.split("/")))
                self.assertIn(package_id, self.initiatives)
                self.assertIn(package_id, self.state)

    def test_state_records_verified_snapshot_and_honest_boundaries(self):
        for expected in (
            "d88ca480a2cfcdc697d3bfffd219268c20368520",
            "pipeline 83",
            "65c4d5a350bcaf3ea36fac55a49d14de3a7fc2fd",
            "pipeline 85",
            "43afd9353af1a0693aafab0c918f3dff92802376",
            "pipeline 91",
            "e0462a2e4683c91ebe518b6d984a2a8b973ba3d5",
            "pipeline 93",
            "ChatGPT Work",
            "GitHub mirror is not current",
            "Voice is functionally deployed",
            "self-certification",
            "Placement reference model is live",
            "no website control creates or displays placements yet",
            "pipeline 97",
            "pipeline 99",
            "binding visual minimums",
            "I went back at 36",
            "PS-STORY-COMPOSER-001",
        ):
            self.assertIn(expected, self.state)

    def test_visual_integrity_is_enforced_across_workflows(self):
        standard = _read("docs", "governance", "OWNER_VISUAL_INTEGRITY_STANDARD.md")
        self.assertIn("match or exceed", standard)
        self.assertIn("Speak and Type", standard)
        self.assertIn("Editorial Studio Ledger", standard)
        for relative_path in (
            "START_HERE.md",
            "AGENTS.md",
            "CLAUDE.md",
            "docs/AI_WORKFLOW.md",
            "docs/templates/OWNER_TECHNICAL_COMPLETION_REPORT.md",
        ):
            with self.subTest(path=relative_path):
                body = _read(*relative_path.split("/"))
                self.assertIn("OWNER_VISUAL_INTEGRITY_STANDARD.md", body)
        report = _read("docs", "templates", "OWNER_TECHNICAL_COMPLETION_REPORT.md")
        self.assertIn("Pete / ChatGPT Work visual acceptance", report)

    def test_story_composition_is_member_directed_and_not_claimed_live(self):
        standard = _read(
            "docs", "governance", "OWNER_STORY_COMPOSITION_STANDARD.md"
        )
        for expected in (
            "move and resize",
            "Dragging is never the only path",
            "Layout metadata is stored separately",
            "never silently apply, save, overwrite, or publish",
            "I went back at 36",
            "planned, not active",
        ):
            self.assertIn(expected, standard)
        for relative_path in (
            "START_HERE.md",
            "AGENTS.md",
            "CLAUDE.md",
            "docs/AI_WORKFLOW.md",
            "docs/templates/OWNER_TECHNICAL_COMPLETION_REPORT.md",
        ):
            with self.subTest(path=relative_path):
                body = _read(*relative_path.split("/"))
                self.assertIn("OWNER_STORY_COMPOSITION_STANDARD.md", body)
        self.assertIn("PS-STORY-COMPOSER-001", self.state)
        self.assertIn("not active", self.initiatives)

    def test_self_managed_delivery_is_enforced_across_agents_and_reports(self):
        workflow = _read("docs", "AI_WORKFLOW.md")
        for expected in (
            "Self-managed delivery lanes",
            "complete diff",
            "Pass`, `Conditional`, or `Fail",
            "post-acceptance release and closeout",
            "The Bible is not a changelog",
        ):
            self.assertIn(expected, workflow)

        for relative_path in (
            "START_HERE.md",
            "AGENTS.md",
            "CLAUDE.md",
            "docs/governance/CURRENT_BASELINE.yaml",
            "docs/governance/CURRENT_STATE.md",
            "docs/governance/ACTIVE_INITIATIVES.md",
            "docs/governance/MANAGER_SESSION_HANDOFF.md",
            "docs/templates/OWNER_TECHNICAL_COMPLETION_REPORT.md",
        ):
            with self.subTest(path=relative_path):
                body = _read(*relative_path.split("/"))
                self.assertRegex(body, r"(?i)self-manag")

        report = _read("docs", "templates", "OWNER_TECHNICAL_COMPLETION_REPORT.md")
        self.assertIn("Self-certification: Pass / Conditional / Fail", report)
        self.assertIn("Complete-diff review", report)

    def test_voice_visual_correction_is_truthful_and_assigned_to_claude(self):
        correction = _read(
            "docs", "initiatives", "PS-VOICE-001", "06_VISUAL_PARITY_CORRECTION.md"
        )
        for expected in (
            "Claude Code",
            "Save private Capture",
            "Coming later",
            "Frontend flags",
            "portfolio-voice-001",
            "Pass`, `Conditional`, or `Fail",
        ):
            self.assertIn(expected, correction)
        self.assertIn("Claude Code self-managed visual correction", self.baseline)
        self.assertIn("pipeline 105", self.state)
        self.assertIn("withdrew Voice visual acceptance", self.state)


if __name__ == "__main__":
    unittest.main()
