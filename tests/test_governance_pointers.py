"""Dependency-free guardrails for PeerSlate's repository authority chain."""

import hashlib
import os
import re
import unittest
import zipfile


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
                self.assertIn("Claude Co-Work", body)
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
        ("docs", "governance", "EARLY_LEGAL_AND_SITE_READINESS_STANDARD.md"),
        ("docs", "governance", "MANAGER_SESSION_HANDOFF.md"),
        ("docs", "governance", "AI_DELIVERY_AUDIT_REGISTER.md"),
        ("docs", "AI_MODEL_AND_ROLE_ROUTING.md"),
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
        ("docs", "initiatives", "PS-INTERVIEW-PUBLIC-GATE-001", "07_GATE_24_SESSION_REVIEW.md"),
        ("docs", "initiatives", "PS-INTERVIEW-PUBLIC-GATE-001", "16_MANAGER_IMPLEMENTATION_ACCEPTANCE.md"),
        ("docs", "initiatives", "PS-INTERVIEW-PUBLIC-GATE-001", "COMPLETION_REPORT.md"),
        ("docs", "initiatives", "PS-HOME-INTERVIEW-PARITY-001", "README.md"),
        ("docs", "initiatives", "PS-HOME-INTERVIEW-PARITY-001", "01_CLAUDE_ARCHITECTURE_AND_IMPLEMENTATION_BRIEF.md"),
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
        ("docs", "initiatives", "PS-AI-OPS-LEAN-001", "README.md"),
        ("docs", "initiatives", "PS-AI-OPS-LEAN-001", "COMPLETION_REPORT.md"),
        ("docs", "initiatives", "PS-PORTABLE-SESSION-MANAGER-001", "README.md"),
        ("docs", "initiatives", "PS-PORTABLE-SESSION-MANAGER-001", "COMPLETION_REPORT.md"),
        ("docs", "initiatives", "PS-CAPTURE-MEDIA-001", "README.md"),
        ("docs", "initiatives", "PS-CAPTURE-MEDIA-001", "COMPLETION_REPORT.md"),
        ("docs", "initiatives", "PS-CAPTURE-MEDIA-001", "PHOTO_EXPERIENCE_COMPLETION_REPORT.md"),
        ("docs", "initiatives", "PS-NEXT-WAVE-MANAGER-001", "README.md"),
        ("docs", "initiatives", "PS-NEXT-WAVE-MANAGER-001", "COMPLETION_REPORT.md"),
        ("docs", "initiatives", "PS-VISUAL-INTEGRITY-GOV-001", "README.md"),
        ("docs", "initiatives", "PS-VISUAL-INTEGRITY-GOV-001", "COMPLETION_REPORT.md"),
        ("docs", "initiatives", "PS-STORY-COMPOSER-DIRECTION-001", "README.md"),
        ("docs", "initiatives", "PS-STORY-COMPOSER-DIRECTION-001", "COMPLETION_REPORT.md"),
        ("docs", "initiatives", "PS-ASK-PETE-AI-001", "README.md"),
        ("docs", "initiatives", "PS-ASK-PETE-AI-001", "01_DISCOVERY_AGENDA.md"),
        ("docs", "initiatives", "PS-ASK-PETE-AI-001", "COMPLETION_REPORT.md"),
        ("docs", "initiatives", "PS-PROJECTS-001", "README.md"),
        ("docs", "initiatives", "PS-PROJECTS-001", "01_REQUIREMENTS.md"),
        ("docs", "initiatives", "PS-PROJECTS-001", "02_EXPERIENCE_AND_VISUAL_DIRECTION.md"),
        ("docs", "initiatives", "PS-PROJECTS-001", "03_ARCHITECTURE_AND_DATA.md"),
        ("docs", "initiatives", "PS-PROJECTS-001", "04_TRACEABILITY_AND_SLICE_PLAN.md"),
        ("docs", "initiatives", "PS-PROJECTS-001", "05_TEST_VALIDATION_RELEASE_PLAN.md"),
        ("docs", "initiatives", "PS-PROJECTS-001", "COMPLETION_REPORT.md"),
        ("docs", "initiatives", "PS-OWNER-HOME-VIEWER-GATE-001", "README.md"),
        ("docs", "initiatives", "PS-OWNER-HOME-VIEWER-GATE-001", "FABLE_COMPLETION_REPORT.md"),
        ("docs", "initiatives", "PS-OWNER-HOME-VIEWER-GATE-001", "11_MANAGER_ACCEPTANCE_AND_ACTIVATION.md"),
        ("docs", "initiatives", "PS-HOME-BACKEND-001", "README.md"),
        ("docs", "initiatives", "PS-HOME-BACKEND-001", "COMPLETION_REPORT.md"),
        ("docs", "initiatives", "PS-HOME-FRONTEND-001", "README.md"),
        ("docs", "initiatives", "PS-HOME-FRONTEND-001", "01_MANAGER_ACTIVATION_AND_EVIDENCE_DISPOSITION.md"),
        ("docs", "initiatives", "PS-HOME-FRONTEND-001", "COMPLETION_REPORT.md"),
        ("docs", "initiatives", "PS-JOURNAL-001", "README.md"),
        ("docs", "initiatives", "PS-JOURNAL-001", "00_OWNER_RESTART_AND_V151_RECONCILIATION.md"),
        ("docs", "initiatives", "PS-JOURNAL-001", "01_REQUIREMENTS_AND_ARCHITECTURE_GATE.md"),
        ("docs", "initiatives", "PS-JOURNAL-001", "02_EXPERIENCE_AND_INFORMATION_ARCHITECTURE.md"),
        ("docs", "initiatives", "PS-JOURNAL-001", "03_DATA_AUTHORIZATION_AND_LIFECYCLE.md"),
        ("docs", "initiatives", "PS-JOURNAL-001", "04_JOURNAL_MY_STORY_AND_PROJECTION_BOUNDARY.md"),
        ("docs", "initiatives", "PS-JOURNAL-001", "05_IMPLEMENTATION_TEST_AND_RELEASE_SEQUENCE.md"),
        ("docs", "initiatives", "PS-JOURNAL-001", "COMPLETION_REPORT.md"),
        ("docs", "initiatives", "PS-JOURNAL-001", "source", "PeerSlate_Company_and_Product_Bible_v1.5.1.docx"),
        ("docs", "governance", "PeerSlate_Company_and_Product_Bible_v2.9.docx"),
        ("docs", "governance", "PeerSlate_Product_Strategy_and_Architecture_Roadmap_v2.8.docx"),
        ("docs", "initiatives", "PS-GOV-CONNECTED-SYSTEM-001", "README.md"),
        ("docs", "initiatives", "PS-GOV-CONNECTED-SYSTEM-001", "10_ACTIVATION_CHECKLIST.md"),
        ("docs", "initiatives", "PS-GOV-CONNECTED-SYSTEM-001", "11_OWNER_APPROVAL_AND_ACTIVATION.md"),
        ("docs", "initiatives", "PS-GOV-CONNECTED-SYSTEM-001", "ACTIVATION_COMPLETION_REPORT.md"),
        ("docs", "initiatives", "PS-GOV-CONNECTED-SYSTEM-001", "12_SUPERSESSION_AND_CONTINUATION.md"),
        ("docs", "initiatives", "PS-GOV-JOURNAL-SYSTEM-001", "README.md"),
        ("docs", "initiatives", "PS-GOV-JOURNAL-SYSTEM-001", "00_OWNER_DECISION_AND_SUPERSESSION.md"),
        ("docs", "initiatives", "PS-GOV-JOURNAL-SYSTEM-001", "01_SYSTEM_TRACEABILITY_MATRIX.md"),
        ("docs", "initiatives", "PS-GOV-JOURNAL-SYSTEM-001", "02_BIBLE_V2_8_AMENDMENT_SOURCE.md"),
        ("docs", "initiatives", "PS-GOV-JOURNAL-SYSTEM-001", "03_ROADMAP_V2_7_AMENDMENT_SOURCE.md"),
        ("docs", "initiatives", "PS-GOV-JOURNAL-SYSTEM-001", "04_ACTIVE_LANE_COMPATIBILITY_AND_TRANSITION.md"),
        ("docs", "initiatives", "PS-GOV-JOURNAL-SYSTEM-001", "05_AUTHORITY_ACTIVATION_AND_TRACEABILITY.md"),
        ("docs", "initiatives", "PS-GOV-JOURNAL-SYSTEM-001", "COMPLETION_REPORT.md"),
        ("docs", "initiatives", "PS-GOV-JOURNAL-SYSTEM-001", "build_authority_documents.py"),
        ("docs", "initiatives", "PS-GOV-JOURNAL-SYSTEM-001", "evidence", "BIBLE_V2_7_TEMPLATE_DISTILLATION.md"),
        ("docs", "initiatives", "PS-GOV-JOURNAL-SYSTEM-001", "evidence", "ROADMAP_V2_6_TEMPLATE_DISTILLATION.md"),
        ("docs", "initiatives", "PS-GOV-JOURNAL-SYSTEM-001", "evidence", "DOCX_RENDER_AND_ACCESSIBILITY_VERIFICATION.md"),
        ("docs", "initiatives", "PS-GOV-JOURNAL-SYSTEM-001", "source", "README.md"),
        ("docs", "initiatives", "PS-GOV-JOURNAL-SYSTEM-001", "source", "1-PeerSlate-Hooks-and-Connected-Site-Research-Report-2.docx"),
        ("docs", "initiatives", "PS-GOV-JOURNAL-SYSTEM-001", "source", "2-PeerSlate_Product_Strategy_and_Architecture_Roadmap_v2.5.docx"),
        ("docs", "initiatives", "PS-GOV-JOURNAL-SYSTEM-001", "source", "3-Deep-Research-Report-on-Hooks-for-a-Voice-First-Journaling-and-Growth-Website-2.docx"),
        ("docs", "initiatives", "PS-RETURN-VALUE-001", "README.md"),
        ("docs", "initiatives", "PS-RETURN-VALUE-001", "01_REQUIREMENTS_AND_EXPERIENCE_ARCHITECTURE.md"),
        ("docs", "initiatives", "PS-RETURN-VALUE-001", "02_SERVICE_DATA_AND_ROLLOUT_ARCHITECTURE.md"),
        ("docs", "initiatives", "PS-RETURN-VALUE-001", "03_REVISIT_REGISTER.md"),
        ("docs", "initiatives", "PS-ASK-SLATE-AI-001", "README.md"),
        ("docs", "initiatives", "PS-ASK-SLATE-AI-001", "01_ARCHITECTURE.md"),
        ("docs", "initiatives", "PS-MESSAGING-001", "README.md"),
        ("docs", "initiatives", "PS-MESSAGING-001", "01_ARCHITECTURE_AND_SAFETY.md"),
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


class LeanDeliveryPolicyTests(unittest.TestCase):
    """The lean delivery decision must stay central and testable."""

    def test_central_policy_preserves_risk_controls_and_audit_cadence(self):
        workflow = _read("docs", "AI_WORKFLOW.md")
        routing = _read("docs", "AI_MODEL_AND_ROLE_ROUTING.md")
        for required in (
            "one pass for each distinct",
            "A fresh independent reviewer is mandatory only for",
            "Every four completed runtime implementation slices",
            "default-off feature",
            "Quarterly or before a major launch",
            "Pete gives final visual acceptance on the corrected real build",
        ):
            self.assertIn(required, workflow)
        for required in (
            "GPT-5.6 Sol, Extra High",
            "GPT-5.6 Terra, Extra High",
            "Fresh GPT-5.6 Sol, High",
            "Claude Fable 5",
            "Claude Sonnet 5",
            "Claude Opus 4.8",
            "Packages name roles, not model versions",
        ):
            self.assertIn(required, routing)

    def test_claude_inherits_current_baseline_and_lean_policy(self):
        claude = _read("CLAUDE.md")
        self.assertIn("the Bible and\nRoadmap paths it names", claude)
        self.assertIn("lean delivery route", claude)
        self.assertNotIn("currently Bible", claude)
        self.assertNotIn("Bible v2.8 / Roadmap v2.7", claude)

    def test_audit_register_and_active_protected_slice_use_the_central_route(self):
        workflow = _read("docs", "AI_WORKFLOW.md")
        register = _read("docs", "governance", "AI_DELIVERY_AUDIT_REGISTER.md")
        handoff = _read("docs", "governance", "MANAGER_SESSION_HANDOFF.md")
        report = _read(
            "docs", "initiatives", "PS-AI-OPS-LEAN-001", "COMPLETION_REPORT.md"
        )
        slice_readme = _read("docs", "initiatives", "PS-SLATE-STUDIO-IA-001", "README.md")
        activation = _read(
            "docs",
            "initiatives",
            "PS-SLATE-STUDIO-IA-001",
            "11_OWNER_ACTIVATION_AND_CODEX_MANAGER_GATE.md",
        )
        proposal = _read(
            "docs",
            "initiatives",
            "PS-SLATE-STUDIO-IA-001",
            "08_D6_SLICE_1_ACTIVATION_PROPOSAL.md",
        )

        for required in (
            "AI_DELIVERY_AUDIT_REGISTER.md",
            "does **not** start\nanother audit",
            "normal runtime\nslice closeout",
        ):
            self.assertIn(required, workflow)
        for required in (
            "Register owner",
            "completed runtime implementation slice",
            "1 of 4 since policy start",
            "2026-10-24",
            "Do not recursively create a\n   new audit",
            "Focused targeted audit",
            "`Pass` - 36/36 focused tests",
            "does not\n  increment or reset",
            "PS-SLATE-STUDIO-SLICE-1-001",
            "Azure PR 171",
            "Pipeline:** automatic run 233",
            "default-off 404",
        ):
            self.assertIn(required, register)
        for required in (
            "do not hardcode their versions",
            "no pointer update was needed",
        ):
            self.assertIn(required, handoff)
        for required in (
            "37c921f2e09e81ad8a98f145138692c31b77b7e1",
            "40464edbea5c9ff75a6f6969419fc5099542fa6e",
            "**Conditional**",
            "**Pass**",
            "Azure PR 170 open and not merged",
        ):
            self.assertIn(required, report)
        for document_name, body in (
            ("slice readme", slice_readme),
            ("activation gate", activation),
            ("activation proposal", proposal),
        ):
            with self.subTest(document=document_name):
                self.assertIn("central Terra", body)
                self.assertIn("central Sol High", body)
                self.assertRegex(body, r"corrected\s+candidate")

    def test_studio_slice1_release_closeout_supports_the_runtime_counter(self):
        completion = _read(
            "docs",
            "initiatives",
            "PS-SLATE-STUDIO-SLICE-1-001",
            "OWNER_TECHNICAL_COMPLETION_REPORT.md",
        )
        state = _read("docs", "governance", "CURRENT_STATE.md")
        active = _read("docs", "governance", "ACTIVE_INITIATIVES.md")
        baseline = _read("docs", "governance", "CURRENT_BASELINE.yaml")

        for document_name, body in (
            ("completion", completion),
            ("current state", state),
            ("active initiatives", active),
            ("current baseline", baseline),
        ):
            with self.subTest(document=document_name):
                self.assertIn(
                    "43d415cfb50717d94b69c07d7be648a12691f1f8",
                    body,
                )
                self.assertIn("PR 171", body)
                self.assertIn("pipeline 233", body)
                self.assertRegex(body, r"(?i)default-off")

        self.assertIn("Released Pass", completion)
        self.assertNotIn("No PR opened", completion)
        self.assertNotIn("Not deployed", completion)
        self.assertNotIn("No Slice 1 runtime branch exists yet", active)
        self.assertNotIn("| Slate Studio Slice 1 |", active)
        self.assertNotIn("assigned after governance merge", active)
        self.assertNotIn(
            "later the default-off protected Build Your Future shell/frame",
            active,
        )
        self.assertIn("slate_studio_slice1_pr: 171", baseline)
        self.assertIn("slate_studio_slice1_pipeline: 233", baseline)


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
        self.assertIn("Bible_v2.9", self.baseline)
        self.assertIn("Roadmap_v2.8", self.baseline)
        self.assertIn('role: "package_designated_session_manager"', self.baseline)
        self.assertIn(
            'eligible_tools: "ChatGPT Work/Codex manager session or Claude Co-Work"',
            self.baseline,
        )
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
        # Deliberately not a literal pipeline number. Pinning one here is the
        # same mistake that let the asset-signature collision form: the rule is
        # "the baseline states which commit and pipeline define current
        # application behaviour", not "that value is exactly N". Pinning it
        # guarantees this assertion goes stale on the next release and blocks
        # the correction, which is what PS-GOV-TRUTH-RECONCILIATION-001 found.
        self.assertRegex(self.baseline, r"(?m)^  application_behavior_commit: \"[0-9a-f]{40}\"$")
        self.assertRegex(self.baseline, r"(?m)^  application_behavior_pipeline: \d+$")
        self.assertRegex(self.baseline, r"(?m)^  deployed_main_commit: \"[0-9a-f]{40}\"$")
        self.assertRegex(self.baseline, r"(?m)^  deployed_pipeline: \d+$")
        self.assertIn("interview_studio_pipeline: 149", self.baseline)
        self.assertIn("interview_release_closeout_pipeline: 150", self.baseline)
        self.assertIn("39002f5130a1766d2090007c16582e0dbe07226c", self.baseline)
        self.assertIn("capture_photo_experience_pipeline: 143", self.baseline)
        self.assertIn("owner_home_backend_pipeline: 145", self.baseline)
        self.assertIn("a98cced519a1f853ad9f4462fd438efa67d6f260", self.baseline)
        self.assertIn("voice_visual_release_pipeline: 113", self.baseline)
        self.assertIn("864a79d1bc1fc61e62f2d2a544dd54a01ebdcb82", self.baseline)
        self.assertIn("PS-HOME-INTERVIEW-DEMO-001", self.baseline)
        self.assertIn("OWNER_VISUAL_INTEGRITY_STANDARD.md", self.baseline)
        self.assertIn("OWNER_STORY_COMPOSITION_STANDARD.md", self.baseline)
        self.assertIn("MANAGER_SESSION_HANDOFF.md", self.baseline)
        self.assertIn(
            'delivery_model: "portable_session_manager_with_self_managed_writers"',
            self.baseline,
        )
        self.assertIn("voice_release_pipeline: 105", self.baseline)
        self.assertIn("eede8565d703a466bd788962d494e8b385b53409", self.baseline)
        self.assertIn("voice_visual_release_pipeline: 113", self.baseline)
        self.assertIn("voice_visual_release_pr: 80", self.baseline)
        self.assertIn("voice_governance_closeout_pipeline: 115", self.baseline)
        self.assertIn("5cc5b69346ee354bcc36248f7ee5724ce13c9d08", self.baseline)
        self.assertIn("connected_system_candidate_pipeline: 162", self.baseline)
        self.assertIn("journal_restart_pipeline: 168", self.baseline)
        self.assertIn('journal_system_authority_source_commit: "578081f5191dd74daa154941604a2b199c5fed58"', self.baseline)
        self.assertIn('journal_system_authority_merge_commit: "3d7c9e10811dcbcc763d965d7770bd0d35e51d4b"', self.baseline)
        self.assertIn("journal_system_authority_pr: 118", self.baseline)
        self.assertIn("journal_system_authority_pipeline: 171", self.baseline)
        self.assertIn('journal_system_authority_pipeline_build: "20260721.1"', self.baseline)
        self.assertIn("journal_system_authority_redundant_pipeline: 172", self.baseline)
        self.assertIn("PS-GOV-CONNECTED-SYSTEM-001", self.baseline)
        self.assertIn("PS-GOV-JOURNAL-SYSTEM-001", self.baseline)
        self.assertIn("EARLY_LEGAL_AND_SITE_READINESS_STANDARD.md", self.baseline)
        self.assertIn("AI_MODEL_AND_ROLE_ROUTING.md", self.baseline)

    def test_journal_system_authority_is_current_traceable_and_runtime_honest(self):
        expected = {
            "PeerSlate_Company_and_Product_Bible_v2.9.docx": (
                "1bb3df535b2a7478d36c539521d64e452a01b163febe367615a96f345459224f",
                "CURRENT AND LOCKED - APPROVED BY THE OWNER ON JULY 24, 2026; SUPERSEDES v2.8",
                "Authority: v2.9 is CURRENT and controlling.",
                "Version 2.9 Work-first Slate Studio and one-Journal authority",
                "CURRENT BIBLE v2.9 • JULY 24, 2026",
            ),
            "PeerSlate_Product_Strategy_and_Architecture_Roadmap_v2.8.docx": (
                "612c23cf21cba4a58905e77b067adb82ff8a7bea5a24a107742c973fe48495a1",
                "CURRENT AND LOCKED - APPROVED BY THE OWNER ON JULY 24, 2026; SUPERSEDES v2.7",
                "Roadmap authority: v2.8 is CURRENT and controlling.",
                "Version 2.8 Work-first Slate Studio activation sequence",
                "CURRENT ROADMAP v2.8 • JULY 24, 2026",
            ),
        }
        for filename, (
            digest,
            status_text,
            authority_text,
            header_text,
            footer_text,
        ) in expected.items():
            path = os.path.join(ROOT, "docs", "governance", filename)
            with self.subTest(document=filename), open(path, "rb") as document:
                self.assertEqual(digest, hashlib.sha256(document.read()).hexdigest())
                self.assertIn(f'sha256: "{digest.upper()}"', self.baseline)
                document.seek(0)
                with zipfile.ZipFile(document) as archive:
                    xml = "\n".join(
                        archive.read(name).decode("utf-8")
                        for name in archive.namelist()
                        if name.endswith(".xml")
                    )
                self.assertIn(status_text, xml)
                self.assertIn(authority_text, xml)
                self.assertIn(header_text, xml)
                self.assertIn(footer_text, xml)
                self.assertNotIn("CANDIDATE AWAITING OWNER APPROVAL", xml)
                self.assertNotIn("JULY 19, 2026", xml)
                self.assertIn("Save Moment", xml)
                self.assertNotIn("Journal UI remains on hold", xml)
                self.assertIn("derived", xml.lower())
                self.assertIn("complete accessible chooser", xml)
                self.assertIn("every currently supported and authorized", xml)
                for stale_gate in (
                    "After a member reviews a Moment",
                    "owner-scoped private draft before placement",
                    "owner-scoped private draft before publication",
                    "The member can connect the reviewed Moment",
                    "Private draft, review, promotion",
                    "1Capture",
                    "confirmed text Moments",
                    "same review and lifecycle architecture as text",
                    "Figure N-1. Voice to value: retained audio becomes",
                ):
                    self.assertNotIn(stale_gate, xml)
                if "Bible" in filename:
                    self.assertIn("Ask Slate AI", xml)
                    self.assertIn("PS-CORE-USE-002", xml)
                else:
                    self.assertIn("PS-GOV-JOURNAL-SYSTEM-001", xml)
                    self.assertIn("PS-ASK-SLATE-AI-001", xml)
                    self.assertIn("does not wait for", xml)
                    self.assertIn("public Journal", xml)

        source_hashes = {
            "1-PeerSlate-Hooks-and-Connected-Site-Research-Report-2.docx":
                "1cf16a02a33a6b73be13ad60361a4ddf3ffef5d33c3f7cc7af2b4ee54f4aa63f",
            "2-PeerSlate_Product_Strategy_and_Architecture_Roadmap_v2.5.docx":
                "e9c8b8102c6416ac9739da427726cf09907142f34082ea1930d621446ec003e6",
            "3-Deep-Research-Report-on-Hooks-for-a-Voice-First-Journaling-and-Growth-Website-2.docx":
                "9c485b71906fb643d1f418478d21ca4c3e19a41b74c1fef770a57437c76cfce6",
        }
        source_readme = _read(
            "docs", "initiatives", "PS-GOV-JOURNAL-SYSTEM-001",
            "source", "README.md",
        )
        for filename, digest in source_hashes.items():
            path = os.path.join(
                ROOT, "docs", "initiatives", "PS-GOV-JOURNAL-SYSTEM-001",
                "source", filename,
            )
            with self.subTest(source=filename), open(path, "rb") as source:
                self.assertEqual(digest, hashlib.sha256(source.read()).hexdigest())
                self.assertIn(filename, source_readme)
                self.assertIn(digest.upper(), source_readme)

        for candidate_id in ("PS-PUBLIC-CONNECTIVE-001", "PS-CONNECTIVE-COMPONENT-001"):
            self.assertIn(candidate_id, self.baseline)
        for committed_id in ("PS-RETURN-VALUE-001", "PS-ASK-SLATE-AI-001", "PS-MESSAGING-001"):
            self.assertIn(committed_id, self.baseline)
            self.assertIn(committed_id, self.initiatives)
            self.assertIn(committed_id, self.state)
        self.assertIn("committed_architecture_planned_not_active", self.baseline)
        self.assertIn("changes no current route", self.state)
        self.assertIn("changes governance only", self.initiatives)

    def test_active_package_paths_and_coordination_agree(self):
        active_block = re.search(
            r"(?ms)^active_packages:\s*$\n(.*?)(?=^[a-z_]+:|\Z)", self.baseline
        )
        self.assertIsNotNone(active_block)
        active_ids = re.findall(r"(?m)^\s+- id:\s+([A-Z0-9-]+)\s*$", active_block.group(1))
        package_paths = re.findall(r'package_path:\s*"([^"]+)"', active_block.group(1))
        self.assertEqual(
            [
                "PS-CAPTURE-MEDIA-001",
                "PS-COMMUNITY-TABS-001",
                "PS-GOV-TRUTH-RECONCILIATION-001",
                "PS-HOME-FRONTEND-001",
                "PS-JOURNAL-001",
                "PS-SLATE-STUDIO-IA-001",
            ],
            active_ids,
        )
        self.assertEqual(len(active_ids), len(package_paths))
        for package_id, relative_path in zip(active_ids, package_paths):
            with self.subTest(package=package_id):
                self.assertTrue(_exists(*relative_path.split("/")))
                self.assertIn(package_id, self.initiatives)
                self.assertIn(package_id, self.state)

    def test_active_packages_are_not_already_closed(self):
        """An active package may not already be recorded as released and live.

        Added by PS-GOV-TRUTH-RECONCILIATION-001. On 2026-07-21 the pointers
        listed PS-HOME-INTERVIEW-PARITY-001 as awaiting manager review while its
        own completion report read "Complete, released, and verified live" and
        the converged assets were serving in production. Nothing caught it,
        because the guardrails asserted a snapshot instead of an invariant.

        Two invariants close that gap:

        1. No id may appear in both `active_packages` and `completed_packages`.
        2. No id in `active_packages` may have a package completion report whose
           status claims the package is released or verified live.
        """
        active_block = re.search(
            r"(?ms)^active_packages:\s*$\n(.*?)(?=^[a-z_]+:|\Z)", self.baseline
        )
        completed_block = re.search(
            r"(?ms)^completed_packages:\s*$\n(.*?)(?=^[a-z_]+:|\Z)", self.baseline
        )
        self.assertIsNotNone(active_block)
        self.assertIsNotNone(completed_block)

        active_ids = re.findall(
            r"(?m)^\s+- id:\s+([A-Z0-9-]+)\s*$", active_block.group(1)
        )
        completed_ids = re.findall(
            r"(?m)^\s+- ([A-Z0-9-]+)\s*$", completed_block.group(1)
        )
        self.assertTrue(active_ids)
        self.assertTrue(completed_ids)

        both = sorted(set(active_ids) & set(completed_ids))
        self.assertEqual(
            [],
            both,
            f"Packages recorded as active and completed at once: {both}",
        )

        # Phrases that assert a finished, shipped, member-visible package. These
        # are deliberately narrow so that a legitimately partial status such as
        # "Complete for the restart checkpoint; product implementation remains
        # gated" does not trip the check.
        closed_claims = (
            r"complete,\s*released",
            r"released,?\s*and\s*verified\s*live",
            r"released\s*and\s*live",
        )
        contradictions = []
        for package_id in active_ids:
            report_parts = ("docs", "initiatives", package_id, "COMPLETION_REPORT.md")
            if not _exists(*report_parts):
                continue
            status_section = re.search(
                r"(?ms)^## A\.\s.*?(?=^## B\.|\Z)", _read(*report_parts)
            )
            if status_section is None:
                continue
            status_text = status_section.group(0).lower()
            for pattern in closed_claims:
                if re.search(pattern, status_text):
                    contradictions.append((package_id, pattern))
                    break
        self.assertEqual(
            [],
            contradictions,
            "Packages listed as active whose completion report says they "
            f"already shipped: {contradictions}",
        )

    def test_journal_architecture_is_controlling_preserved_and_runtime_honest(self):
        readme = _read("docs", "initiatives", "PS-JOURNAL-001", "README.md")
        reconciliation = _read(
            "docs",
            "initiatives",
            "PS-JOURNAL-001",
            "00_OWNER_RESTART_AND_V151_RECONCILIATION.md",
        )
        architecture = _read(
            "docs",
            "initiatives",
            "PS-JOURNAL-001",
            "01_REQUIREMENTS_AND_ARCHITECTURE_GATE.md",
        )
        source_path = os.path.join(
            ROOT,
            "docs",
            "initiatives",
            "PS-JOURNAL-001",
            "source",
            "PeerSlate_Company_and_Product_Bible_v1.5.1.docx",
        )
        with open(source_path, "rb") as source_file:
            digest = hashlib.sha256(source_file.read()).hexdigest()

        self.assertIn("holds: []", self.baseline)
        self.assertIn("journal_memory_profile_and_activation", self.baseline)
        self.assertIn(
            "architecture_current_private_core_entry_gate_unassigned",
            self.baseline,
        )
        self.assertEqual(
            "01848a19271942780f740f5220bf48816f664fe134236e28da4a61d49bf3626b",
            digest,
        )
        self.assertIn("Capture is an action, not a place", readme)
        self.assertIn("Save Moment is the single member commit", readme)
        self.assertIn("Journal membership is derived", readme)
        self.assertIn("The issue was therefore not wholesale loss", reconciliation)
        self.assertIn("controlling architecture, not evidence of runtime", architecture)
        self.assertIn("It is not a destination", architecture)
        self.assertIn("complete accessible", architecture)
        self.assertIn("not a fact-bearing body table", architecture)
        self.assertIn("no target Journal UI is live", self.state)
        for current_record in (
            self.baseline,
            self.state,
            self.initiatives,
            _read("docs", "governance", "DOCUMENT_CONTROL.md"),
            _read("docs", "PEERSLATE_SITE_RULES.md"),
        ):
            self.assertNotIn("Journal UI remains on hold", current_record)

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
            "Claude Co-Work",
            "Capture Media manager planning",
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
        self.assertIn("Pete / designated session manager visual acceptance", report)

    def test_interview_dual_theme_authority_and_live_release_state_are_explicit(self):
        brief = _read(
            "docs",
            "initiatives",
            "PS-INTERVIEW-PUBLIC-GATE-001",
            "09_DUAL_THEME_VISUAL_AUTHORITY_AND_CLAUDE_BRIEF.md",
        )
        standard = _read("docs", "governance", "OWNER_VISUAL_INTEGRITY_STANDARD.md")
        review = _read(
            "docs",
            "initiatives",
            "PS-INTERVIEW-PUBLIC-GATE-001",
            "07_GATE_24_SESSION_REVIEW.md",
        )
        for expected in (
            "ChatGPT Image Jul 19, 2026, 12_09_58 PM (5).png",
            "7A03EE1F4569478F067EE2996C575B130077633CB6C2AAA36A058EFE772467DD",
            "Concept A",
            "Concept C",
            "Image 1A and Image 2A",
            "one DOM, one state machine",
            "18 primary exports",
            "ps-theme",
            "no-state-loss",
            "Product implementation: **Not authorized**",
            "Design and feasibility only; product implementation has not started",
        ):
            self.assertIn(expected, brief)
        for expected in (
            "Editorial Studio Ledger",
            "Cinematic Studio",
            "same public Studio",
            "Changing theme must not reset",
        ):
            self.assertIn(expected, standard)
        self.assertIn("18 primary exports", review)
        self.assertIn("Concept A default/light and Concept C optional dark", self.state)
        self.assertIn("released and verified live", self.state)
        self.assertIn("39002f5130a1766d2090007c16582e0dbe07226c", self.state)
        self.assertIn("pipeline 149", self.state)
        self.assertIn("5A-light/5C-dark", self.baseline)
        # The homepage Interview parity lane is closed, not pending. It released
        # through PR 105 at 4deb0a0 with pipeline 154 and closed out through
        # PR 106 with pipeline 156. These assertions previously required the
        # stale "architecture_checkpoint_pushed_manager_review_pending" status
        # and so blocked the correction; see PS-GOV-TRUTH-RECONCILIATION-001.
        self.assertIn("home_interview_parity_pr: 105", self.baseline)
        self.assertIn("home_interview_parity_pipeline: 154", self.baseline)
        self.assertIn(
            'home_interview_parity_merge_commit: "4deb0a07b6faf2d93d445e212207aeb84b1a71c4"',
            self.baseline,
        )
        self.assertIn("home_interview_parity_closeout_pr: 106", self.baseline)
        # The architecture checkpoint remains recorded as lineage.
        self.assertIn(
            "353a5810b18e7db22f35319fbecc9c2fa97d8b72",
            self.baseline,
        )
        self.assertIn(
            "PS-HOME-INTERVIEW-PARITY-001 - complete, released, and verified live",
            self.initiatives,
        )
        self.assertNotIn(
            'status: "architecture_checkpoint_pushed_manager_review_pending"',
            self.baseline,
        )

    def test_portable_manager_and_gate_24_handoffs_are_explicit(self):
        workflow = _read("docs", "AI_WORKFLOW.md")
        handoff = _read("docs", "governance", "MANAGER_SESSION_HANDOFF.md")
        interview_review = _read(
            "docs",
            "initiatives",
            "PS-INTERVIEW-PUBLIC-GATE-001",
            "07_GATE_24_SESSION_REVIEW.md",
        )
        capture = _read(
            "docs", "initiatives", "PS-CAPTURE-MEDIA-001", "README.md"
        )

        for expected in (
            "Portable session management",
            "exactly one designated session manager",
            "Claude Co-Work management is",
            "distinct from Claude Code implementation ownership",
        ):
            self.assertIn(expected, workflow)
        for expected in (
            "package-designated role",
            "Claude Co-Work management is distinct",
            "PS-CAPTURE-MEDIA-001",
            "implementation, complete-diff review",
        ):
            self.assertIn(expected, handoff)
        for expected in (
            "Review-only",
            "nine",
            "truth/accessibility",
            "Claude Co-Work",
            "does not edit Interview Studio product code",
        ):
            self.assertIn(expected, interview_review)
        for expected in (
            "experience are released",
            "Current writer: Unassigned",
            "Photo code is deployed with the flag off",
            "Voice",
        ):
            self.assertIn(expected, capture)

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

    def test_public_ask_pete_and_private_ask_slate_are_separate(self):
        ask_pete = _read(
            "docs", "initiatives", "PS-ASK-PETE-AI-001", "README.md"
        )
        agenda = _read(
            "docs", "initiatives", "PS-ASK-PETE-AI-001",
            "01_DISCOVERY_AGENDA.md",
        )
        ask_slate = _read(
            "docs", "initiatives", "PS-ASK-SLATE-AI-001", "README.md"
        )
        ask_slate_architecture = _read(
            "docs", "initiatives", "PS-ASK-SLATE-AI-001", "01_ARCHITECTURE.md"
        )
        visual_standard = _read(
            "docs", "governance", "OWNER_VISUAL_INTEGRITY_STANDARD.md"
        )

        for expected in (
            "PS-ASK-PETE-AI-001",
            "public_typed_slice_live_future_refinement_not_active",
            "PS-ASK-SLATE-AI-001",
            "committed_architecture_planned_not_active",
            "homepage_product_projection",
        ):
            self.assertIn(expected, self.baseline)

        for expected in (
            "Public typed assistant live",
            "approved public Pete sources only",
            "Ask [Name] AI",
            "Private member intelligence: `PS-ASK-SLATE-AI-001`",
            "No private uploads",
        ):
            self.assertIn(expected, ask_pete)

        for expected in (
            "future public-profile assistance only",
            "authorization before retrieval",
            "no private counts",
            "no new implementation",
        ):
            self.assertIn(expected, agenda)

        for expected in (
            "Ask Slate AI",
            "Ask My Slate",
            "Ask [Name] AI",
            "Ashley AI is retired",
            "Qualification Alignment",
            "No signed-in Ask Slate AI product is claimed live",
        ):
            self.assertIn(expected, ask_slate)
        for expected in (
            "constrain retrieval before",
            "shall never send a message",
            "shall not create/edit a Moment",
            "private",
        ):
            self.assertIn(expected, ask_slate_architecture)

        for expected in (
            "Cross-product homepage projection parity",
            "real product is upstream authority",
            "same release wave",
            "showcase-quality",
            "Voice Capture",
            "Interview Studio",
        ):
            self.assertIn(expected, visual_standard)

        self.assertIn("PS-ASK-PETE-AI-001", self.state)
        self.assertIn("PS-ASK-PETE-AI-001", self.initiatives)

        for relative_path in (
            "AGENTS.md",
            "CLAUDE.md",
            "docs/AI_WORKFLOW.md",
            "docs/templates/OWNER_TECHNICAL_COMPLETION_REPORT.md",
        ):
            with self.subTest(path=relative_path):
                body = _read(*relative_path.split("/"))
                self.assertRegex(body, r"(?i)homepage.*parity")

    def test_journal_projection_return_and_revisit_contracts_are_complete(self):
        bible_amendment = _read(
            "docs", "initiatives", "PS-GOV-JOURNAL-SYSTEM-001",
            "02_BIBLE_V2_8_AMENDMENT_SOURCE.md",
        )
        roadmap_amendment = _read(
            "docs", "initiatives", "PS-GOV-JOURNAL-SYSTEM-001",
            "03_ROADMAP_V2_7_AMENDMENT_SOURCE.md",
        )
        transition = _read(
            "docs", "initiatives", "PS-GOV-JOURNAL-SYSTEM-001",
            "04_ACTIVE_LANE_COMPATIBILITY_AND_TRANSITION.md",
        )
        requirements = _read(
            "docs", "initiatives", "PS-JOURNAL-001",
            "01_REQUIREMENTS_AND_ARCHITECTURE_GATE.md",
        )
        data = _read(
            "docs", "initiatives", "PS-JOURNAL-001",
            "03_DATA_AUTHORIZATION_AND_LIFECYCLE.md",
        )
        story = _read(
            "docs", "initiatives", "PS-JOURNAL-001",
            "04_JOURNAL_MY_STORY_AND_PROJECTION_BOUNDARY.md",
        )
        sequence = _read(
            "docs", "initiatives", "PS-JOURNAL-001",
            "05_IMPLEMENTATION_TEST_AND_RELEASE_SEQUENCE.md",
        )
        return_requirements = _read(
            "docs", "initiatives", "PS-RETURN-VALUE-001",
            "01_REQUIREMENTS_AND_EXPERIENCE_ARCHITECTURE.md",
        )
        return_service = _read(
            "docs", "initiatives", "PS-RETURN-VALUE-001",
            "02_SERVICE_DATA_AND_ROLLOUT_ARCHITECTURE.md",
        )
        revisit = _read(
            "docs", "initiatives", "PS-RETURN-VALUE-001", "03_REVISIT_REGISTER.md",
        )

        for expected in (
            "It is not a destination",
            "Save Moment shall explicitly create or confirm exactly one",
            "membership shall be derived",
            "complete accessible",
            "every currently supported and authorized destination",
            "shall never hide an",
        ):
            self.assertIn(expected, requirements)
        self.assertIn("authorized predicate before retrieving", data.lower())
        self.assertIn("Substantive new text must be a Moment", data)
        self.assertIn("should Journal and My Story become one?", story)
        self.assertIn("Removing the chapter from Story keeps the Moment in Journal", story)
        self.assertIn("default-off internal/owner pilot", sequence)
        self.assertIn("does not satisfy the universal-anywhere promise by itself", sequence)
        self.assertIn("J-labels allocate scope; they do not impose one serial train", sequence)
        self.assertIn("Neither waits for J3 public", sequence)

        self.assertIn("PS-CORE-USE-002", bible_amendment)
        self.assertIn("complete keyboard- and screen-reader-accessible chooser", bible_amendment)
        self.assertIn("complete accessible chooser", roadmap_amendment)
        self.assertIn("neither waits for public Journal", roadmap_amendment)
        for expected in (
            "`/app/capture` link only as a truthful temporary",
            "default-off compatibility bridge",
            "explicit owner-approved temporary exception",
            "Projects itself is not activated",
            "Journal architecture is active",
        ):
            self.assertIn(expected, transition)
        for expected in (
            "without waiting for public Journal",
            "temporary default-off compatibility, not target IA",
            "Save Moment/derived-Journal integration",
        ):
            self.assertIn(expected, self.baseline)

        for expected in (
            "including day, week, month",
            "daily rhythm is optional and member-chosen",
            "Purposeful acknowledgements/badges",
            "What PeerSlate Noticed and Slate Mirror",
            "not a persona, diagnosis",
        ):
            self.assertIn(expected, return_requirements)
        self.assertIn("without punitive reset/loss framing", return_service)
        self.assertIn("PS-LEGAL-018", return_service)
        for expected in (
            "Chaptered Audio Journal",
            "Guided Journeys",
            "Open to Mic",
            "Life Constellation",
            "synthetic",
        ):
            self.assertIn(expected, revisit)

    def test_messaging_legal_and_model_routing_gates_are_durable(self):
        messaging = _read(
            "docs", "initiatives", "PS-MESSAGING-001",
            "01_ARCHITECTURE_AND_SAFETY.md",
        )
        legal = _read(
            "docs", "governance", "EARLY_LEGAL_AND_SITE_READINESS_STANDARD.md",
        )
        routing = _read("docs", "AI_MODEL_AND_ROLE_ROUTING.md")

        for expected in (
            "relationship/consent state",
            "shall not authorize a DM",
            "Mute",
            "Block",
            "Report",
            "AI shall never\n  press Send",
            "Formal counsel",
            "Two-member validation",
        ):
            self.assertIn(expected, messaging)
        for expected in (
            "does not mean counsel approved",
            "Public/permissioned Journal shall not release",
            "Messaging shall not pilot",
            "PS-LEGAL-018",
            "security/threat-model",
        ):
            self.assertIn(expected, legal)
        for expected in (
            "exactly one manager and one active writer",
            "governance-only package",
            "independent reviewer",
            "Verify the available model",
            "exact branch/SHA",
            "do not send it to another premium model",
        ):
            self.assertIn(expected, routing)

    def test_chatgpt_is_the_sole_visual_authority_creation_lane(self):
        routing = _read("docs", "AI_MODEL_AND_ROLE_ROUTING.md")
        visual_standard = _read(
            "docs", "governance", "OWNER_VISUAL_INTEGRITY_STANDARD.md"
        )
        decision_log = _read("docs", "governance", "DECISIONS.md")
        package = _read(
            "docs", "initiatives", "PS-AI-OPS-VISUAL-AUTHORITY-001",
            "README.md"
        )

        for relative_path in (
            "AGENTS.md",
            "CLAUDE.md",
            "docs/AI_WORKFLOW.md",
            "docs/AI_MODEL_AND_ROLE_ROUTING.md",
            "docs/governance/OWNER_VISUAL_INTEGRITY_STANDARD.md",
        ):
            with self.subTest(path=relative_path):
                body = _read(*relative_path.split("/"))
                self.assertIn("ChatGPT", body)
                self.assertRegex(body, r"(?i)sole (creator|creation lane)")

        controlling_surfaces = (
            routing, visual_standard, decision_log, package,
            _read("docs", "AI_WORKFLOW.md"),
            _read("AGENTS.md"),
            _read("CLAUDE.md"),
        )
        for body in controlling_surfaces:
            self.assertRegex(
                body, r"(?i)(existing Pete-locked|authorities Pete locked)"
            )
            self.assertRegex(body, r"(?i)implement")
            self.assertRegex(body, r"(?i)evidence|screenshot")
            self.assertRegex(body, r"(?i)non-material")
            self.assertRegex(
                body,
                r"(?is)return(?:s|ed)?.{0,120}?"
                r"\bto\s+(?:the\s+)?ChatGPT",
            )
            self.assertIn("Pete", body)

    def test_projects_is_planned_connected_and_not_claimed_live(self):
        package = _read(
            "docs", "initiatives", "PS-PROJECTS-001", "README.md"
        )
        architecture = _read(
            "docs", "initiatives", "PS-PROJECTS-001", "03_ARCHITECTURE_AND_DATA.md"
        )
        requirements = _read(
            "docs", "initiatives", "PS-PROJECTS-001", "01_REQUIREMENTS.md"
        )

        for expected in (
            "PS-PROJECTS-001",
            'status: "planned_not_active"',
            "Phase 10 - Moment Lab, Story, Work, Projects, and connected views",
        ):
            self.assertIn(expected, self.baseline)

        for expected in (
            "Planned - not active",
            "Private Project Workspace",
            "Project Projection",
            "Projects are not a task-management suite",
            "No authenticated Project create/edit route",
            "one exact confirmed Moment",
        ):
            self.assertIn(expected, package)

        for expected in (
            "Canonical Project aggregate",
            "opaque Project key",
            "slate_entities",
            "moment_placements",
            "row-version concurrency token",
            "cross-owner",
            "no-text-copy",
        ):
            self.assertIn(expected, architecture)

        for expected in (
            "AI may propose Project titles",
            "and publication as separate explicit actions",
            "Slate Board",
            "shall not require or imitate sprint planning",
        ):
            self.assertIn(expected, requirements)

        self.assertIn("PS-PROJECTS-001", self.state)
        self.assertIn("planned Phase 10 expansion", self.initiatives)
        self.assertIn("no authenticated canonical Projects product is live", self.state)

    def test_owner_home_frontend_activation_preserves_the_finite_backend(self):
        decision = _read(
            "docs", "initiatives", "PS-OWNER-HOME-VIEWER-GATE-001",
            "11_MANAGER_ACCEPTANCE_AND_ACTIVATION.md",
        )
        backend = _read(
            "docs", "initiatives", "PS-HOME-BACKEND-001", "README.md"
        )
        brief = _read(
            "docs", "initiatives", "PS-OWNER-HOME-VIEWER-GATE-001",
            "CODEX_BACKEND_IMPLEMENTATION_BRIEF.md",
        )
        frontend = _read(
            "docs", "initiatives", "PS-HOME-FRONTEND-001", "README.md"
        )
        activation = _read(
            "docs", "initiatives", "PS-HOME-FRONTEND-001",
            "01_MANAGER_ACTIVATION_AND_EVIDENCE_DISPOSITION.md",
        )

        for expected in (
            "PS-OWNER-HOME-VIEWER-GATE-001",
            "PS-HOME-BACKEND-001",
            "PS-HOME-FRONTEND-001",
            'status: "activated_writer_branch_pending"',
            "interview_studio_pipeline: 149",
            "capture_photo_closeout_pipeline: 140",
            "capture_photo_experience_pipeline: 143",
            "owner_home_backend_pipeline: 145",
        ):
            self.assertIn(expected, self.baseline)

        for expected in (
            "U1",
            "U6",
            "standalone_owner_shell",
            "voice_draft_failed",
            "moment_proposal_pending",
            "voice_draft_ready",
            "modify `auth_routes.py`",
            "PS-CAPTURE-PHOTO-BACKEND-001",
            "not implemented, deployed, enabled, or live",
        ):
            self.assertIn(expected, decision)

        for body in (backend, brief):
            self.assertIn("PEERSLATE_OWNER_HOME_ENABLED", body)
            self.assertIn("neutral", body)
            self.assertIn("404", body)
            self.assertIn("does not edit `auth_routes.py`", body)

        self.assertIn("PS-HOME-BACKEND-001", self.state)
        self.assertIn("PS-HOME-BACKEND-001", self.initiatives)
        self.assertIn("PS-HOME-FRONTEND-001` is activated", self.initiatives)

        for expected in (
            "work/2026-07-20-home-frontend-001",
            "separately assigned Codex frontend task",
            "owner-home.v1",
            "templates/owner_workspace.html",
            "PEERSLATE_OWNER_HOME_ENABLED=false",
            "Partial category failure",
            "stale/`409 state_changed`",
            "restricted runtime",
            "may not be simulated",
            "visual-product acceptance before opening",
        ):
            self.assertIn(expected, frontend)

        for expected in (
            "HFA1",
            "HFA7",
            "Evidence mismatch resolved by narrowing",
            "first-release runtime rows",
            "Default-off release",
            "No production enablement occurs",
        ):
            self.assertIn(expected, activation)

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

    def test_voice_visual_correction_is_truthful_and_closed(self):
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
        self.assertIn("PS-VOICE-VISUAL-PARITY-001", self.baseline)
        self.assertIn("  - PS-VOICE-001", self.baseline)
        self.assertIn("pipeline 105", self.state)
        self.assertIn("withdrew Voice visual acceptance", self.state)
        self.assertIn("pipeline 113", self.state)
        self.assertIn("functionally deployed, visually accepted, and closed", self.state)


if __name__ == "__main__":
    unittest.main()
