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
        ("docs", "initiatives", "PS-NEXT-WAVE-MANAGER-001", "README.md"),
        ("docs", "initiatives", "PS-NEXT-WAVE-MANAGER-001", "COMPLETION_REPORT.md"),
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
        self.assertGreaterEqual(len(paths), 8)
        stale = []
        for relative_path in paths:
            parts = relative_path.rstrip("/").split("/")
            if not _exists(*parts):
                stale.append(relative_path)
        self.assertEqual([], stale, f"Baseline points at missing paths: {stale}")

    def test_baseline_names_current_authority_and_manager(self):
        self.assertIn("Bible_v2.3", self.baseline)
        self.assertIn("Roadmap_v2.3", self.baseline)
        self.assertIn('tool: "ChatGPT Work"', self.baseline)
        self.assertIn("PS-GOV-001", self.baseline)
        self.assertIn("PS-BASELINE-001", self.baseline)
        self.assertIn("PS-NEXT-WAVE-MANAGER-001", self.baseline)
        self.assertIn("manager_setup_pipeline: 80", self.baseline)
        self.assertIn("application_behavior_pipeline: 85", self.baseline)

    def test_active_package_paths_and_coordination_agree(self):
        active_block = re.search(
            r"(?ms)^active_packages:\s*$\n(.*?)(?=^[a-z_]+:|\Z)", self.baseline
        )
        self.assertIsNotNone(active_block)
        active_ids = re.findall(r"(?m)^\s+- id:\s+([A-Z0-9-]+)\s*$", active_block.group(1))
        package_paths = re.findall(r'package_path:\s*"([^"]+)"', active_block.group(1))
        self.assertEqual(
            ["PS-INTERVIEW-PUBLIC-GATE-001", "PS-MOMENT-001"], active_ids
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
            "ChatGPT Work",
            "GitHub mirror is not current",
            "Capture remains text-only",
        ):
            self.assertIn(expected, self.state)


if __name__ == "__main__":
    unittest.main()
