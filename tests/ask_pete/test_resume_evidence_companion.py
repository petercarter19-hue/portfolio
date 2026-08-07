"""Flag-gated page-contract coverage for the Recruiter Evidence Companion."""

from __future__ import annotations

import os
import re
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch


os.environ.setdefault("ANTHROPIC_API_KEY", "ask-pete-resume-test-key")
from services.ask_pete.manifest import load_public_source_catalog

import app as app_module


class RecruiterEvidenceCompanionTemplateTests(TestCase):
    def setUp(self) -> None:
        self.original = {
            "TESTING": app_module.app.config.get("TESTING"),
            "PEERSLATE_ASK_PETE_GROUNDED_ENABLED": app_module.app.config.get(
                "PEERSLATE_ASK_PETE_GROUNDED_ENABLED"
            ),
        }
        app_module.app.config.update(TESTING=True)
        self.client = app_module.app.test_client()

    def tearDown(self) -> None:
        app_module.app.config.update(**self.original)

    def resume_html(self, enabled: bool) -> str:
        app_module.app.config["PEERSLATE_ASK_PETE_GROUNDED_ENABLED"] = enabled
        response = self.client.get("/petec/resume")
        self.assertEqual(response.status_code, 200)
        return response.get_data(as_text=True)

    def test_default_off_preserves_the_legacy_resume_assistant(self) -> None:
        html = self.resume_html(False)

        self.assertIn("r2-overview-ai-rail", html)
        self.assertIn("js/chatbot.js", html)
        self.assertIn("css/chatbot.css", html)
        self.assertNotIn("ask-pete-evidence-companion", html)
        self.assertNotIn("ask-pete-resume-evidence.css", html)

    def test_flag_on_uses_one_companion_and_omits_legacy_shared_chatbot(self) -> None:
        html = self.resume_html(True)

        self.assertIn("data-ask-pete-evidence-active", html)
        self.assertEqual(html.count("data-ask-pete-companion"), 1)
        self.assertIn("ask-pete-resume-evidence.css", html)
        self.assertIn("r2-overview-mobile-ask-pete", html)
        self.assertIn("ask-pete-evidence-companion.js", html)
        self.assertIn("data-ask-pete-context-action", html)
        self.assertNotIn("r2-overview-ai-rail", html)
        self.assertNotIn("id=\"chat-panel\"", html)
        self.assertNotIn("js/chatbot.js", html)
        self.assertNotIn("css/chatbot.css", html)

    def test_flag_on_has_exact_achievement_targets_for_citations(self) -> None:
        html = self.resume_html(True)

        for record_id in (
            "burdick",
            "engineer-of-year",
            "emerging-leader",
            "outstanding-team",
        ):
            self.assertIn(
                f'id="r2-credential-record-achievement-{record_id}"',
                html,
            )

    def test_companion_renderer_uses_safe_dom_text_apis(self) -> None:
        root = Path(__file__).resolve().parents[2]
        controller = (root / "static/js/ask-pete-evidence-companion.js").read_text(
            encoding="utf-8"
        )

        self.assertIn("textContent", controller)
        self.assertNotIn("innerHTML", controller)
        self.assertNotIn("localStorage", controller)
        self.assertNotIn("sessionStorage", controller)
        self.assertNotIn("document.cookie", controller)

    def test_preview_citation_is_derived_from_the_approved_manifest(self) -> None:
        root = Path(__file__).resolve().parents[2]
        catalog = load_public_source_catalog(
            manifest_path=root / "data" / "ai_sources" / "ask_pete_public_v1.json",
            resume_path=root / "static" / "data" / "resume_data.json",
        )
        preview_record = next(
            record
            for record in catalog.records
            if record.locator.record_kind == "career_role"
        )
        html = self.resume_html(True)
        preview_excerpt = next(
            line.removeprefix("Summary: ")
            for line in preview_record.source.content.splitlines()
            if line.startswith("Summary: ")
        )
        partial = (
            root / "templates" / "partials" / "ask_pete_evidence_companion.html"
        ).read_text(encoding="utf-8")

        self.assertIn(preview_record.source.title, html)
        self.assertIn(preview_excerpt, html)
        self.assertIn("ask_pete_evidence_preview.excerpt", partial)
        self.assertNotIn(
            "A citation identifies the approved record used for an Ask Pete answer.",
            partial,
        )
        self.assertIn(
            f'data-ask-pete-anchor="{preview_record.locator.anchor}"',
            html,
        )
        self.assertIn(
            f'data-ask-pete-record-id="{preview_record.locator.record_id}"',
            html,
        )
        self.assertNotIn("more than 30 engineers", partial)
        self.assertNotIn("r2-exp-card-dod", partial)

    def test_preview_fails_closed_when_the_approved_source_has_no_summary(self) -> None:
        record = SimpleNamespace(
            source=SimpleNamespace(title="Example approved record", content="Employer: Example"),
            locator=SimpleNamespace(
                section="experience",
                anchor="example-record",
                record_kind="career_role",
                record_id="example",
                highlight_key="career_role:example",
            ),
        )
        with patch.object(
            app_module,
            "load_public_source_catalog",
            return_value=SimpleNamespace(records=(record,)),
        ):
            data = app_module._ask_pete_evidence_companion_data("petec")

        self.assertIsNone(data["preview"])
        self.assertEqual(data["context_keys"], frozenset({"career_role:example"}))

    def test_contextual_actions_only_name_approved_manifest_records(self) -> None:
        root = Path(__file__).resolve().parents[2]
        catalog = load_public_source_catalog(
            manifest_path=root / "data" / "ai_sources" / "ask_pete_public_v1.json",
            resume_path=root / "static" / "data" / "resume_data.json",
        )
        manifest_context_keys = {
            f"{record.locator.record_kind}:{record.locator.record_id}"
            for record in catalog.records
        }
        html = self.resume_html(True)
        rendered_context_keys = set(
            re.findall(r'data-ask-pete-context-key="([^"]+)"', html)
        )

        self.assertTrue(rendered_context_keys)
        self.assertTrue(rendered_context_keys <= manifest_context_keys)
        credential_markup = html.split(
            '<div class="r2-credential-panels">', maxsplit=1
        )[1]
        self.assertNotIn("data-ask-pete-context-action", credential_markup)
        self.assertIn("data-ask-pete-open", credential_markup)

    def test_companion_accessibility_contract_is_backed_by_runtime_state(self) -> None:
        root = Path(__file__).resolve().parents[2]
        html = self.resume_html(True)
        controller = (root / "static/js/ask-pete-evidence-companion.js").read_text(
            encoding="utf-8"
        )

        self.assertIn('aria-controls="ask-pete-evidence-companion"', html)
        self.assertIn("data-ask-pete-citation-toggle", controller)
        self.assertIn("elements.answer.setAttribute('aria-labelledby', heading.id)", controller)
        self.assertIn("event.defaultPrevented", controller)
        self.assertIn("closeCompanion({ restoreFocus: false })", controller)
