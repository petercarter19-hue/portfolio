"""Focused contract tests for the attended-proof browser-operator boundary."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
ROLE_GUIDANCE = (ROOT / "docs" / "AI_MODEL_AND_ROLE_ROUTING.md").read_text(
    encoding="utf-8"
)
RUNBOOK = (
    ROOT / "qa" / "synthetic_member" / "docs" / "ATTENDED_PROOF_RUNBOOK.md"
).read_text(encoding="utf-8")


class BrowserOperatorBoundaryTests(unittest.TestCase):
    def test_role_guidance_assigns_routine_browser_work_to_an_operator(self):
        required = (
            "Those retained responsibilities do not make Pete\n"
            "the routine browser operator.",
            "The assigned browser-capable operator opens pages, navigates, clicks ordinary",
            "clicks ordinary sign-out controls",
            "visible residue checks",
            "browser-capable executor within the same task",
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, ROLE_GUIDANCE)

    def test_role_guidance_preserves_credential_and_session_boundary(self):
        required = (
            "Pete alone enters passwords, MFA and verification",
            "authorizes spending, production",
            "irreversible identity deletion",
            "The operator never inspects, exports, records, or persists",
            "authentication headers, browser",
            "profiles, or private session files",
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, ROLE_GUIDANCE)

    def test_runbook_assigns_the_visible_journey_and_cleanup_to_operator(self):
        required = (
            "operator opens each sign-in flow and handles ordinary",
            "operator performs A-to-B and B-to-A switch journeys",
            "After each operator-clicked sign-out",
            "operator performs refresh, second-tab, public-return",
            "operator deletes or archives every created item",
            "operator signs out and destroys Clients A, B",
            "operator closes the\n"
            "affected view",
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, RUNBOOK)

        superseded = (
            "controls every login,",
            "Pete performs A-to-B and B-to-A switch journeys",
            "Pete performs refresh, second-tab",
            "Pete signs out. Pete destroys",
            "ask Pete to sign out and destroy",
        )
        for phrase in superseded:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, RUNBOOK)

    def test_runbook_screenshots_are_privacy_safe_and_not_retained(self):
        required = (
            "Screenshots are optional, never the default retained proof",
            "sentinel or\nprivate item content",
            "Destroy any\ntransient privacy-safe screenshot before final validation",
            "Never photograph, copy, or\nexport a suspected private exposure.",
            "Any transient privacy-safe screenshot is destroyed",
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, RUNBOOK)

    def test_identity_entry_uses_suspended_observation_and_truthful_visibility(self):
        required = (
            "operator stops issuing\nbrowser commands and suspends all capture and observation",
            "Pete controls the\nvisible input and says only `ready`",
            "ordinary UI may unavoidably render a login\nidentifier or account label",
            "Incidental visibility is not evidence",
            "must not intentionally inspect, transcribe,\n"
            "export, capture, record, or retain that detail",
            "only\nas `member_a` and `member_b`",
            "If any secret, code, or credential is rendered unmasked,\n"
            "stop without capture.",
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, RUNBOOK)

        self.assertNotIn(
            "browser-capable operator never see\nor record an address",
            RUNBOOK,
        )

    def test_dom_and_sensitive_material_cannot_be_recorded_or_retained(self):
        observation_boundary = RUNBOOK.split(
            "### Browser observation boundary", 1
        )[1].split("## Entry gate", 1)[0]
        self.assertIn(
            "never exports, records, or persists browser storage,\n"
            "private network traces, or DOM/page content",
            observation_boundary,
        )

        retained_proof = RUNBOOK.split("## Retained proof", 1)[1]
        forbidden_retention = (
            "sentinel text",
            "DOM/page content",
            "identity inventory or identifiers",
            "credentials",
            "tokens",
            "session material",
            "cookies",
            "claims",
            "browser profiles",
            "private session\nfiles",
        )
        for phrase in forbidden_retention:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, retained_proof)


if __name__ == "__main__":
    unittest.main()
