"""Real browser -> Flask -> service journeys for the My Data first slice.

Playwright drives a real headless Chrome against a locally served Flask app.
Entry-policy writes go through the real service backed by the in-memory
repository; the composer intake path uses the same deterministic stub seams
as the intake browser proof (stub transcription, stub document pipeline) so
the provider boundary stays synthetic. The application's own HTTP responses
are never intercepted, except for capturing the single proposal-decision
payload to assert the exact submitted field values (the request still
continues to the server).

Ordinary unittest discovery may skip when Playwright or Chrome is unavailable.
This is not SQL engine proof, live identity proof or live provider proof.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
import unittest
from uuid import uuid4

from werkzeug.serving import make_server

from app import app, limiter
from services.entry_policy_repository import InMemoryEntryPolicyRepository
from services.entry_policy_service import EntryPolicyService
from services.resume_intake_proposals import (
    ProposalSpec,
    create as create_intake_proposal,
    present as present_intake_proposal,
)
from services.resume_draft_repository import (
    InMemoryCanonicalCatalog,
    InMemoryResumeDraftRepository,
)
from services.resume_draft_service import ResumeDraftService
from services.resume_guide_service import ResumeGuideService
from services.resume_intake_document_adapter import ResumeDocumentAdapter
from services.my_data_extraction_adapter import DeterministicFakeExtractionAdapter
from services.resume_intake_policy import selected_policy_for_tests
from services.resume_intake_repository import InMemoryResumeIntakeRepository
from services.resume_intake_service import ResumeIntakeService
from services.resume_intake_transcription_adapter import ResumeTranscriptionAdapter

try:
    from playwright.sync_api import sync_playwright
except ModuleNotFoundError:  # pragma: no cover - environment capability gate
    sync_playwright = None

try:
    from scripts.capture_ps_journal_j1_evidence import _resolve_chrome

    CHROME_EXECUTABLE = _resolve_chrome()
except Exception:  # pragma: no cover - optional local browser helper
    CHROME_EXECUTABLE = None


CONFIG_KEYS = (
    "TESTING",
    "PEERSLATE_ALLOW_DEV_IDENTITY",
    "PEERSLATE_DEV_USER_KEY",
    "PEERSLATE_TRUST_EASYAUTH_HEADERS",
    "PEERSLATE_MY_DATA_ENABLED",
    "PEERSLATE_ENTRY_POLICY_ENABLED",
    "PEERSLATE_RESUME_INTAKE_ENABLED",
    "PEERSLATE_RESUME_INTAKE_FIXTURE_POLICY_ENABLED",
    "ENTRY_POLICY_SERVICE",
    "RESUME_INTAKE_SERVICE",
    "RESUME_GUIDE_SERVICE",
)

BROWSER_MEMBER = "my-data-browser-member"


class _SilentTranscriber:
    def transcribe(self, audio_bytes, content_type, locale="en-US"):
        return {
            "provider_transcript": "Browser journey transcript.",
            "provider_request_id": "my-data-stub-1",
            "duration_seconds": 1.0,
        }


def _new_entry_service():
    return EntryPolicyService(repository=InMemoryEntryPolicyRepository())


def install_my_data_runtime_fixtures(cls):
    """Install isolated Flask/service fixtures, registering cleanup on acquire."""

    snapshot = {
        "config": {key: app.config.get(key) for key in CONFIG_KEYS},
        "limiter_enabled": limiter.enabled,
        "werkzeug_level": logging.getLogger("werkzeug").level,
    }

    def restore():
        app.config.update(snapshot["config"])
        limiter.enabled = snapshot["limiter_enabled"]
        logging.getLogger("werkzeug").setLevel(snapshot["werkzeug_level"])

    cls.addClassCleanup(restore)

    cls.catalog = InMemoryCanonicalCatalog()
    cls.draft_service = ResumeDraftService(
        repository=InMemoryResumeDraftRepository(), catalog=cls.catalog
    )
    cls.intake_repository = InMemoryResumeIntakeRepository()

    def pipeline(user_key, import_key, content_type, admitted, *, limits, now):
        from services.my_opportunities.member_import_service import ImportStageOutcome

        return (
            "Uploaded note text: member supplied background.",
            "extracted",
            None,
            False,
            (
                ImportStageOutcome(
                    import_key=import_key,
                    user_key=user_key,
                    outcome="extracted",
                    reason_code=None,
                    occurred_at=now,
                ),
            ),
        )

    cls.intake_service = ResumeIntakeService(
        repository=cls.intake_repository,
        draft_service=cls.draft_service,
        document_adapter=ResumeDocumentAdapter(),
        transcription_adapter=ResumeTranscriptionAdapter(service=_SilentTranscriber()),
        policy=selected_policy_for_tests(),
        document_pipeline=pipeline,
    )
    app.config.update(
        TESTING=True,
        PEERSLATE_ALLOW_DEV_IDENTITY=True,
        PEERSLATE_DEV_USER_KEY=BROWSER_MEMBER,
        PEERSLATE_TRUST_EASYAUTH_HEADERS=False,
        PEERSLATE_MY_DATA_ENABLED=True,
        PEERSLATE_ENTRY_POLICY_ENABLED=True,
        PEERSLATE_RESUME_INTAKE_ENABLED=True,
        PEERSLATE_RESUME_INTAKE_FIXTURE_POLICY_ENABLED=True,
        ENTRY_POLICY_SERVICE=_new_entry_service(),
        RESUME_INTAKE_SERVICE=cls.intake_service,
        RESUME_GUIDE_SERVICE=ResumeGuideService(repository=cls.intake_repository),
    )
    limiter.enabled = False
    logging.getLogger("werkzeug").setLevel(logging.ERROR)

    server = make_server("127.0.0.1", 0, app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    cls.addClassCleanup(_shutdown_server, server, thread)
    thread.start()
    cls.server = server
    cls.server_thread = thread
    cls.base_url = f"http://127.0.0.1:{server.server_port}"


def _shutdown_server(server, thread):
    try:
        if thread.is_alive():
            server.shutdown()
            thread.join(timeout=5)
    finally:
        server.server_close()


def _close_browser(browser):
    browser.close()


def _stop_playwright(runtime):
    runtime.stop()


def start_browser(cls):
    runtime = sync_playwright().start()
    cls.addClassCleanup(_stop_playwright, runtime)
    cls.playwright = runtime
    browser = runtime.chromium.launch(
        executable_path=CHROME_EXECUTABLE,
        headless=True,
        args=["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"],
    )
    cls.addClassCleanup(_close_browser, browser)
    cls.browser = browser


@unittest.skipUnless(
    sync_playwright is not None and CHROME_EXECUTABLE,
    "Playwright and Google Chrome are required for the My Data browser proof",
)
class MyDataBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        install_my_data_runtime_fixtures(cls)
        start_browser(cls)

    def setUp(self):
        # Each journey gets a pristine entry store so card counts are exact.
        self.entry_service = _new_entry_service()
        original = app.config.get("ENTRY_POLICY_SERVICE")
        app.config["ENTRY_POLICY_SERVICE"] = self.entry_service
        self.addCleanup(app.config.update, {"ENTRY_POLICY_SERVICE": original})
        # Composer drafts persist server-side across page loads, so each
        # journey starts with a pristine draft slate instead of inheriting
        # another journey's unsent words or version conflicts.
        try:
            snapshot = self.intake_repository.load_owner(BROWSER_MEMBER)
            snapshot["drafts"] = {}
            self.intake_repository.save_owner(BROWSER_MEMBER, snapshot)
        except Exception:
            pass

    def _seed(self, canonical_type, values, *, entry_key=None):
        payload = {
            "request_id": str(uuid4()),
            "type": "create",
            "entry_key": entry_key or str(uuid4()),
            "canonical_type": canonical_type,
            "values": values,
        }
        return self.entry_service.commit(BROWSER_MEMBER, payload)["entries"][0]

    def _seed_proposal(self, proposed_values, *, kind="new_fact",
                       record_type="role"):
        """Seed one pending multi-field proposal for the browser member.

        Free-text composer submits only ever yield single-field proposals,
        so the white-box seed is what lets the proposal editor prove field
        boundaries; the test merges the seeded row into the real submit
        response because that response only carries its own new proposals.
        The seeded proposal is removed during cleanup so later journeys
        start pristine.
        """
        snapshot = self.intake_repository.load_owner(BROWSER_MEMBER)
        quote = "Seeded browser proposal."
        spec = ProposalSpec(
            source_key="browser-seed",
            source_version=1,
            submission_key="browser-seed-submission",
            submission_version=1,
            kind=kind,
            record_type=record_type,
            quote=quote,
            span_start=0,
            span_end=len(quote),
            proposed_values=dict(proposed_values),
        )
        proposal = create_intake_proposal(snapshot, spec)
        self.intake_repository.save_owner(BROWSER_MEMBER, snapshot)
        key = proposal["proposal_key"]
        presented = present_intake_proposal(
            self.intake_repository.load_owner(BROWSER_MEMBER)["proposals"][key]
        )

        def _remove():
            try:
                current = self.intake_repository.load_owner(BROWSER_MEMBER)
                current.get("proposals", {}).pop(key, None)
                self.intake_repository.save_owner(BROWSER_MEMBER, current)
            except Exception:  # pragma: no cover - best-effort cleanup
                pass

        self.addCleanup(_remove)
        proposal["presented"] = presented
        return proposal

    def _new_page(self, **context_kwargs):
        context = self.browser.new_context(**context_kwargs)
        self.addCleanup(context.close)
        page = context.new_page()
        page.route("https://fonts.**", lambda route: route.abort())
        return page

    def _entry_cards(self, page):
        return page.locator(".my-data__entry")

    def test_inventory_groups_seeded_entries_and_search_narrows(self):
        self._seed(
            "role",
            {"role_title": "Browser Engineer", "employer_name": "Northwind"},
        )
        self._seed(
            "skill",
            {"skill_name": "Browser Python", "skill_summary": "Automation scripts."},
        )
        page = self._new_page(viewport={"width": 1440, "height": 1000})
        page.goto(f"{self.base_url}/app/settings/my-data", wait_until="load")
        page.locator("[data-my-data-groups]").wait_for(timeout=15000)

        groups = page.locator("[data-my-data-groups]").inner_text()
        self.assertIn("Work history", groups)
        self.assertIn("Skills", groups)
        self.assertIn("Browser Engineer at Northwind", groups)
        self.assertIn("Browser Python", groups)

        page.locator("[data-my-data-search]").fill("python")
        page.wait_for_function(
            "document.querySelectorAll('.my-data__entry').length === 1",
            timeout=10000,
        )
        narrowed = page.locator("[data-my-data-groups]").inner_text()
        self.assertIn("Browser Python", narrowed)
        self.assertNotIn("Browser Engineer", narrowed)

        page.locator("[data-my-data-search]").fill("")
        page.wait_for_function(
            "document.querySelectorAll('.my-data__entry').length === 2",
            timeout=10000,
        )

    def test_sharing_change_marks_resume_flag(self):
        created = self._seed(
            "skill",
            {"skill_name": "Browser Sharing", "skill_summary": "Flag journey."},
        )
        page = self._new_page(viewport={"width": 1440, "height": 1000})
        page.goto(f"{self.base_url}/app/settings/my-data", wait_until="load")
        card = page.locator(
            f'.my-data__entry[data-entry-key="{created["entry_key"]}"]'
        )
        card.wait_for(timeout=15000)

        card.get_by_role("button", name="Sharing").click()
        card.locator('[data-permission="resume_display"]').check()
        card.get_by_role("button", name="Save sharing").click()
        key = created['entry_key']
        selector = (
            '.my-data__entry[data-entry-key="%s"]'
            ' [data-entry-flag="resume"]'
        ) % key
        page.wait_for_function(
            "document.querySelector('" + selector + "').hidden === false",
            timeout=15000,
        )

        page.locator("[data-my-data-permission]").select_option("resume")
        page.wait_for_function(
            "document.querySelectorAll('.my-data__entry').length === 1",
            timeout=10000,
        )
        self.assertIn(
            "Browser Sharing", page.locator("[data-my-data-groups]").inner_text()
        )

    def test_delete_moves_to_recently_deleted_and_restore_returns(self):
        created = self._seed(
            "skill",
            {"skill_name": "Browser Ephemeral", "skill_summary": "Delete journey."},
        )
        page = self._new_page(viewport={"width": 1440, "height": 1000})
        page.goto(f"{self.base_url}/app/settings/my-data", wait_until="load")
        card = page.locator(
            f'.my-data__entry[data-entry-key="{created["entry_key"]}"]'
        )
        card.wait_for(timeout=15000)

        card.get_by_role("button", name="Delete", exact=True).click()
        card.locator(".my-data__confirm").get_by_role(
            "button", name="Delete", exact=True
        ).click()
        page.wait_for_function(
            "document.querySelectorAll('.my-data__entry').length === 0",
            timeout=15000,
        )
        self.assertIn("Deleted", page.locator("[data-my-data-status]").inner_text())

        page.locator("[data-my-data-permission]").select_option("recently_deleted")
        restored_card = page.locator(
            f'.my-data__entry[data-entry-key="{created["entry_key"]}"]'
        )
        restored_card.wait_for(timeout=15000)
        restored_card.get_by_role("button", name="Restore").click()
        page.locator("[data-my-data-permission]").select_option("all")
        page.wait_for_function(
            "document.querySelectorAll('.my-data__entry').length === 1",
            timeout=15000,
        )
        self.assertIn(
            "Browser Ephemeral", page.locator("[data-my-data-groups]").inner_text()
        )

    def test_composer_add_captures_text_and_routes_proposals(self):
        page = self._new_page(viewport={"width": 1440, "height": 1000})
        page.goto(f"{self.base_url}/app/settings/my-data", wait_until="load")
        page.locator("[data-my-data-groups]").wait_for(timeout=15000)

        page.locator("[data-my-data-open]").click()
        page.locator("[data-my-data-overlay]").wait_for(timeout=10000)
        page.locator("[data-my-data-text]").fill(
            "I led a quixotic-migration project across two teams in 2024."
        )
        fixture = os.path.join(
            os.path.dirname(__file__), "fixtures", "my_data", "sample-note.txt"
        )
        page.locator("[data-my-data-file]").set_input_files(fixture)
        page.wait_for_function(
            "document.querySelector('[data-my-data-attachments]').textContent"
            ".indexOf('sample-note.txt') !== -1",
            timeout=10000,
        )
        page.locator("[data-my-data-add]").click()

        # The composer captures the member's own words as reviewable
        # proposals; nothing is silently written to the inventory.
        page.wait_for_selector(".my-data__proposal", timeout=20000)
        quote = page.locator("[data-my-data-proposals]").inner_text()
        self.assertIn("quixotic-migration", quote)
        receipt = page.locator("[data-my-data-receipt]").inner_text()
        self.assertTrue(receipt.strip())
        self.assertEqual(self._entry_cards(page).count(), 0)

        # Dismissing a proposal is deterministic: no policy-gated write,
        # the proposal leaves, and the inventory stays exactly as it was.
        page.locator(".my-data__proposal").first.get_by_role(
            "button", name="Dismiss", exact=True
        ).click()
        page.wait_for_function(
            "document.querySelectorAll('.my-data__proposal').length === 0",
            timeout=20000,
        )
        self.assertEqual(self._entry_cards(page).count(), 0)

    def test_mobile_composer_opens_reachable_add(self):
        self._seed(
            "skill",
            {"skill_name": "Browser Mobile", "skill_summary": "Small viewport."},
        )
        page = self._new_page(
            viewport={"width": 390, "height": 844},
            user_agent=(
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
                "Mobile/15E148 Safari/604.1"
            ),
            has_touch=True,
            is_mobile=True,
        )
        page.goto(f"{self.base_url}/app/settings/my-data", wait_until="load")
        page.locator("[data-my-data-groups]").wait_for(timeout=15000)

        page.locator("[data-my-data-open]").click()
        overlay = page.locator("[data-my-data-overlay]")
        overlay.wait_for(timeout=10000)
        add_button = page.locator("[data-my-data-add]")
        self.assertTrue(add_button.is_visible())
        page.locator("[data-my-data-text]").fill("Mobile draft stays reachable.")
        self.assertEqual(
            page.locator("[data-my-data-text]").input_value(),
            "Mobile draft stays reachable.",
        )

    def test_view_tabs_support_arrow_key_selection(self):
        self._seed(
            "skill",
            {"skill_name": "Browser Tabs", "skill_summary": "Keyboard journey."},
        )
        page = self._new_page(viewport={"width": 1440, "height": 1000})
        page.goto(f"{self.base_url}/app/settings/my-data", wait_until="load")
        page.locator("[data-my-data-groups]").wait_for(timeout=15000)

        category_tab = page.locator('[data-my-data-view="category"]')
        activity_tab = page.locator('[data-my-data-view="activity"]')
        self.assertEqual(category_tab.get_attribute("aria-selected"), "true")
        category_tab.focus()
        page.keyboard.press("ArrowRight")

        page.wait_for_function(
            "document.querySelector('[data-my-data-view=\"activity\"]')"
            ".getAttribute('aria-selected') === 'true'",
            timeout=10000,
        )
        self.assertEqual(
            page.evaluate("() => document.activeElement.textContent.trim()"),
            "Activity",
        )
        self.assertEqual(activity_tab.get_attribute("tabindex"), "0")
        self.assertEqual(category_tab.get_attribute("tabindex"), "-1")
        self.assertTrue(
            page.locator('[data-my-data-panel="activity"]').is_visible()
        )

        page.keyboard.press("ArrowLeft")
        page.wait_for_function(
            "document.querySelector('[data-my-data-view=\"category\"]')"
            ".getAttribute('aria-selected') === 'true'",
            timeout=10000,
        )
        self.assertEqual(
            page.evaluate("() => document.activeElement.textContent.trim()"),
            "By category",
        )

    def test_composer_traps_focus_and_restores_opener(self):
        page = self._new_page(viewport={"width": 1440, "height": 1000})
        page.goto(f"{self.base_url}/app/settings/my-data", wait_until="load")
        page.locator("[data-my-data-groups]").wait_for(timeout=15000)

        opener = page.locator("[data-my-data-open]")
        opener.click()
        page.locator("[data-my-data-overlay]").wait_for(timeout=10000)

        def focused_label():
            return page.evaluate(
                "() => { const a = document.activeElement;"
                " if (!a) { return 'none'; }"
                " const labelled = a.labels && a.labels.length"
                " ? a.labels[0].textContent : null;"
                " return (labelled || a.getAttribute('aria-label')"
                " || a.textContent || a.value || a.tagName).trim()"
                " .slice(0, 40); }"
            )

        # Initial focus lands in the composer text field.
        self.assertEqual(focused_label(), "Details")
        page.locator("[data-my-data-text]").fill("Trap draft stays.")

        # No background chrome (footer, tab bar) may intercept taps on
        # the composer: the top hit over Add must sit inside the overlay.
        top_hit_inside = page.evaluate(
            "() => { const add = document.querySelector('[data-my-data-add]');"
            " const box = add.getBoundingClientRect();"
            " const top = document.elementFromPoint("
            " box.x + box.width / 2, box.y + box.height / 2);"
            " return !!top && !!top.closest('[data-my-data-overlay]'); }"
        )
        self.assertTrue(top_hit_inside)

        # Backward wrap: text field -> Close -> last control in the dialog.
        page.keyboard.press("Shift+Tab")
        self.assertEqual(focused_label(), "Close and keep draft")
        page.keyboard.press("Shift+Tab")
        wrapped = focused_label()
        self.assertNotEqual(wrapped, "Close")
        inside = page.evaluate(
            "() => document.querySelector('[data-my-data-overlay]')"
            ".contains(document.activeElement)"
        )
        self.assertTrue(inside)

        # Forward wrap returns to the first control.
        page.keyboard.press("Tab")
        self.assertEqual(focused_label(), "Close and keep draft")

        # Dynamically staged controls join the trap order.
        fixture = os.path.join(
            os.path.dirname(__file__), "fixtures", "my_data", "sample-note.txt"
        )
        page.locator("[data-my-data-file]").set_input_files(fixture)
        page.locator("[data-my-data-attachments]").get_by_text(
            "sample-note.txt"
        ).wait_for(timeout=10000)
        found_remove = False
        for _ in range(20):
            if focused_label() == "Remove":
                found_remove = True
                break
            page.keyboard.press("Tab")
        self.assertTrue(found_remove)

        # Escape closes and returns focus to the opener; the draft stays.
        page.keyboard.press("Escape")
        page.wait_for_function(
            "document.querySelector('[data-my-data-overlay]').hidden === true",
            timeout=10000,
        )
        self.assertEqual(
            page.evaluate(
                "() => (document.activeElement.textContent || '').trim()"
            ),
            "Add information",
        )
        page.locator("[data-my-data-open]").click()
        page.locator("[data-my-data-overlay]").wait_for(timeout=10000)
        self.assertEqual(
            page.locator("[data-my-data-text]").input_value(), "Trap draft stays."
        )

    def test_sharing_badges_and_filters_render_each_permission(self):
        self._seed(
            "skill",
            {"skill_name": "DualShare Skill", "skill_summary": "Both flags."},
        )
        self._seed(
            "skill",
            {"skill_name": "Quiet Skill", "skill_summary": "Stays private."},
        )
        page = self._new_page(viewport={"width": 1440, "height": 1000})
        page.goto(f"{self.base_url}/app/settings/my-data", wait_until="load")
        page.locator("[data-my-data-groups]").wait_for(timeout=15000)

        dual = page.locator(".my-data__entry").filter(
            has_text="DualShare Skill"
        )
        quiet = page.locator(".my-data__entry").filter(has_text="Quiet Skill")

        # A private entry shows only the Private badge.
        self.assertTrue(
            quiet.locator('[data-entry-flag="private"]').is_visible()
        )

        # Grant résumé, visitor AI, and assistance exclusion together.
        dual.get_by_role("button", name="Sharing", exact=True).click()
        form = dual.locator("[data-entry-permissions-form]")
        form.locator('[data-permission="resume_display"]').check()
        form.locator('[data-permission="visitor_ai"]').check()
        form.get_by_text("Additional settings").click()
        form.locator('[data-permission="private_assistance_excluded"]').check()
        form.get_by_role("button", name="Save sharing").click()
        for flag in ("resume", "visitor_ai", "excluded"):
            dual.locator(f'[data-entry-flag="{flag}"]').wait_for(
                state="visible", timeout=15000
            )
        # The Private badge is gone; each permission renders on its own.
        self.assertFalse(
            dual.locator('[data-entry-flag="private"]').is_visible()
        )
        self.assertFalse(
            dual.locator('[data-entry-flag="deleted"]').is_visible()
        )

        permission = page.locator("[data-my-data-permission]")
        permission.select_option("resume")
        self.assertTrue(dual.is_visible())
        self.assertFalse(quiet.is_visible())
        permission.select_option("visitor_ai")
        self.assertTrue(dual.is_visible())
        self.assertFalse(quiet.is_visible())
        permission.select_option("excluded")
        self.assertTrue(dual.is_visible())
        self.assertFalse(quiet.is_visible())
        permission.select_option("private")
        self.assertTrue(quiet.is_visible())
        self.assertFalse(dual.is_visible())

        # Delete clears sharing flags and reports the lifecycle.
        permission.select_option("all")
        dual.get_by_role("button", name="Delete", exact=True).click()
        dual.locator(".my-data__confirm").get_by_role(
            "button", name="Delete", exact=True
        ).click()
        permission.select_option("recently_deleted")
        dual.locator('[data-entry-flag="deleted"]').wait_for(
            state="visible", timeout=15000
        )

        # Restore returns a private entry; the exclusion choice survives.
        dual.get_by_role("button", name="Restore", exact=True).click()
        permission.select_option("all")
        dual.locator('[data-entry-flag="private"]').wait_for(
            state="visible", timeout=15000
        )
        self.assertTrue(
            dual.locator('[data-entry-flag="excluded"]').is_visible()
        )
        self.assertFalse(
            dual.locator('[data-entry-flag="resume"]').is_visible()
        )

    def test_proposal_wording_keeps_field_boundaries(self):
        seeded = self._seed_proposal({
            "role_title": "Senior Engineer",
            "employer_name": "Acme",
            "location_text": "Chicago",
        })
        page = self._new_page(viewport={"width": 1440, "height": 1000})
        page.goto(f"{self.base_url}/app/settings/my-data", wait_until="load")
        page.locator("[data-my-data-groups]").wait_for(timeout=15000)
        # The composer response only carries its own new proposals, so the
        # seeded row joins the real server response on its way through.
        submit_url = page.get_attribute(
            "#my-data", "data-my-data-intake-submit-url"
        )

        def _with_seeded(route):
            response = route.fetch()
            body = response.json()
            body["proposals"] = body.get("proposals", []) + [
                seeded["presented"]
            ]
            route.fulfill(response=response, json=body)

        page.route("**" + submit_url, _with_seeded)
        page.locator("[data-my-data-open]").click()
        page.locator("[data-my-data-text]").fill("Seed trigger note.")
        page.locator("[data-my-data-add]").click()
        card = page.locator(".my-data__proposal").filter(
            has_text="Seeded browser proposal."
        )
        card.wait_for(timeout=20000)

        # No combined sentence box: one editor per proposed field, each
        # prefilled with that field's own value.
        self.assertEqual(card.locator("textarea").count(), 0)
        rendered = card.evaluate(
            "(node) => { const out = {};"
            " node.querySelectorAll('input').forEach("
            "(field) => { out[field.name] = field.type === 'checkbox'"
            " ? field.checked : field.value; }); return out; }"
        )
        self.assertEqual(rendered, {
            "role_title": "Senior Engineer",
            "employer_name": "Acme",
            "location_text": "Chicago",
        })

        # Editing one field submits every field with its own value.
        card.locator('input[name="employer_name"]').fill("Globex")
        decision_url = page.get_attribute(
            "#my-data", "data-my-data-intake-decision-url"
        )
        captured = {}

        def _capture(route):
            captured.update(route.request.post_data_json or {})
            route.continue_()

        page.route("**" + decision_url, _capture)
        card.get_by_role("button", name="Use my wording").click()
        deadline = time.time() + 15
        while "confirmed_values" not in captured and time.time() < deadline:
            time.sleep(0.1)
        self.assertEqual(captured.get("decision"), "edit")
        self.assertEqual(captured.get("confirmed_values"), {
            "role_title": "Senior Engineer",
            "employer_name": "Globex",
            "location_text": "Chicago",
        })

        # Leave no pending proposals behind for later journeys.
        for _ in range(5):
            if not page.locator(".my-data__proposal").count():
                break
            page.locator(".my-data__proposal").first.get_by_role(
                "button", name="Dismiss"
            ).click()
            page.wait_for_timeout(500)
        self.assertEqual(page.locator(".my-data__proposal").count(), 0)

    def test_role_correction_preserves_current_role_flag(self):
        self._seed("role", {
            "role_title": "Engineer", "employer_name": "Acme",
            "current_role": True,
        })
        self._seed("role", {
            "role_title": "Analyst", "employer_name": "Beta",
            "current_role": False,
        })
        page = self._new_page(viewport={"width": 1440, "height": 1000})
        page.goto(f"{self.base_url}/app/settings/my-data", wait_until="load")
        page.locator("[data-my-data-groups]").wait_for(timeout=15000)

        def correct_title(card_text, field, value):
            card = page.locator(".my-data__entry").filter(has_text=card_text)
            card.get_by_role("button", name="Edit", exact=True).click()
            editor = card.locator(".my-data__editor")
            editor.locator(f'input[name="{field}"]').fill(value)
            editor.get_by_role("button", name="Save correction").click()
            page.wait_for_function(
                "document.querySelector('[data-my-data-status]')"
                ".textContent.includes('Correction saved')",
                timeout=15000,
            )

        def flag_checked(card_text):
            card = page.locator(".my-data__entry").filter(has_text=card_text)
            card.get_by_role("button", name="Edit", exact=True).click()
            editor = card.locator(".my-data__editor")
            checked = editor.locator(
                'input[name="current_role"]'
            ).is_checked()
            editor.get_by_role("button", name="Cancel").click()
            return checked

        def set_flag(card_text, checked):
            card = page.locator(".my-data__entry").filter(has_text=card_text)
            card.get_by_role("button", name="Edit", exact=True).click()
            editor = card.locator(".my-data__editor")
            box = editor.locator('input[name="current_role"]')
            if checked:
                box.check()
            else:
                box.uncheck()
            editor.get_by_role("button", name="Save correction").click()
            page.wait_for_function(
                "document.querySelector('[data-my-data-status]')"
                ".textContent.includes('Correction saved')",
                timeout=15000,
            )

        # A title-only correction keeps current_role=true and still saves.
        correct_title("Engineer", "role_title", "Senior Engineer")
        self.assertTrue(flag_checked("Senior Engineer"))
        # Toggling the flag persists false.
        set_flag("Senior Engineer", False)
        self.assertFalse(flag_checked("Senior Engineer"))
        # And a false flag can be corrected back to true.
        self.assertFalse(flag_checked("Analyst"))
        set_flag("Analyst", True)
        self.assertTrue(flag_checked("Analyst"))

    def test_deleted_activity_uses_the_lifecycle_timestamp(self):
        self._seed("skill", {"skill_name": "Dated Skill"})
        page = self._new_page(viewport={"width": 1440, "height": 1000})
        page.goto(f"{self.base_url}/app/settings/my-data", wait_until="load")
        page.locator("[data-my-data-groups]").wait_for(timeout=15000)

        # Correct first so the content timestamp moves before the deletion.
        card = page.locator(".my-data__entry").filter(has_text="Dated Skill")
        card.get_by_role("button", name="Edit", exact=True).click()
        card.locator(".my-data__editor").locator(
            'input[name="skill_name"]'
        ).fill("Dated Skill v2")
        card.locator(".my-data__editor").get_by_role(
            "button", name="Save correction"
        ).click()
        page.wait_for_function(
            "document.querySelector('[data-my-data-status]')"
            ".textContent.includes('Correction saved')",
            timeout=15000,
        )

        card = page.locator(".my-data__entry").filter(
            has_text="Dated Skill v2"
        )
        card.get_by_role("button", name="Delete", exact=True).click()
        card.locator(".my-data__confirm").get_by_role(
            "button", name="Delete", exact=True
        ).click()
        permission = page.locator("[data-my-data-permission]")
        permission.select_option("recently_deleted")
        card.locator('[data-entry-flag="deleted"]').wait_for(
            state="visible", timeout=15000
        )

        entries_url = page.get_attribute(
            "#my-data", "data-my-data-entries-url"
        )
        data = page.evaluate(
            "(url) => fetch(url, {credentials: 'same-origin'})"
            ".then((response) => response.json())",
            entries_url,
        )
        matches = [
            item for item in data["entries"]
            if (item.get("values") or {}).get("skill_name") == "Dated Skill v2"
        ]
        self.assertEqual(len(matches), 1)
        deleted_at = matches[0]["deleted_at"]
        self.assertTrue(deleted_at)
        self.assertNotEqual(deleted_at, matches[0]["updated_at"])

        # Refreshed Activity renders the lifecycle timestamp, not the
        # content timestamp. The timeline lives on the Activity tab.
        # (Client-refreshed entry events carry the timestamp but no
        # server text, so the datetime attribute is the assertion.)
        page.locator('[data-my-data-view="activity"]').click()
        moment = page.locator(
            f'[data-my-data-activity] time[datetime="{deleted_at}"]'
        )
        moment.wait_for(timeout=15000)

        # Initial rendering carries the same timestamp from bootstrap.
        page.reload(wait_until="load")
        page.locator("[data-my-data-groups]").wait_for(timeout=15000)
        bootstrap = json.loads(
            page.locator("#my-data-bootstrap").inner_text()
        )
        deletions = [
            event for event in bootstrap["activity"]
            if event["kind"] == "entry_deleted"
        ]
        matches = [event for event in deletions if event["at"] == deleted_at]
        self.assertTrue(matches)
        self.assertEqual(
            matches[0]["text"], "Information moved to Recently deleted."
        )

    def test_touch_targets_measure_44px_at_390px(self):
        self._seed(
            "skill",
            {"skill_name": "Browser Measure", "skill_summary": "Target journey."},
        )
        page = self._new_page(
            viewport={"width": 390, "height": 844},
            has_touch=True,
            is_mobile=True,
        )
        page.goto(f"{self.base_url}/app/settings/my-data", wait_until="load")
        page.locator("[data-my-data-groups]").wait_for(timeout=15000)

        def height_of(locator):
            box = locator.bounding_box()
            self.assertIsNotNone(box)
            return box["height"]

        # Toolbar, tabs, and inline entry controls.
        self.assertGreaterEqual(
            height_of(page.locator('[data-my-data-view="category"]')), 44
        )
        self.assertGreaterEqual(
            height_of(page.locator("[data-my-data-search]")), 44
        )
        self.assertGreaterEqual(
            height_of(page.locator("[data-my-data-permission]")), 44
        )
        card = page.locator(".my-data__entry").first
        for name in ("Edit", "Sharing", "Delete"):
            self.assertGreaterEqual(
                height_of(card.get_by_role("button", name=name)), 44
            )
        self.assertGreaterEqual(
            height_of(card.locator(".my-data__select")), 44
        )

        # Composer controls, including the file label target.
        page.locator("[data-my-data-open]").click()
        page.locator("[data-my-data-overlay]").wait_for(timeout=10000)
        for selector in (
            "[data-my-data-close]",
            "[data-my-data-mic]",
            "[data-my-data-add]",
            "[data-my-data-discard]",
        ):
            self.assertGreaterEqual(height_of(page.locator(selector)), 44)
        self.assertGreaterEqual(
            height_of(page.locator(".my-data__file")), 44
        )
        self.assertGreaterEqual(
            height_of(page.locator(".my-data__guide summary")), 44
        )

        # Dynamically rendered attachment and proposal controls.
        fixture = os.path.join(
            os.path.dirname(__file__), "fixtures", "my_data", "sample-note.txt"
        )
        page.locator("[data-my-data-file]").set_input_files(fixture)
        remove = page.locator("[data-my-data-attachments]").get_by_role(
            "button", name="Remove"
        )
        remove.wait_for(timeout=10000)
        self.assertGreaterEqual(height_of(remove), 44)

        page.locator("[data-my-data-text]").fill(
            "Measuring quixotic-migration proposal controls."
        )
        page.locator("[data-my-data-add]").click()
        page.wait_for_selector(".my-data__proposal", timeout=20000)
        proposal = page.locator(".my-data__proposal").first
        text_inputs = proposal.locator('input[type="text"]')
        self.assertGreater(text_inputs.count(), 0)
        for index in range(text_inputs.count()):
            self.assertGreaterEqual(height_of(text_inputs.nth(index)), 44)
        for name in ("Save", "Use my wording", "Dismiss"):
            self.assertGreaterEqual(
                height_of(
                    proposal.get_by_role(
                        "button", name=name, exact=True
                    )
                ),
                44,
            )
        page.keyboard.press("Escape")

        # Dynamically rendered delete confirmation controls.
        card.get_by_role("button", name="Delete", exact=True).click()
        confirm = card.locator(".my-data__confirm")
        confirm.wait_for(timeout=10000)
        for name in ("Delete", "Keep"):
            self.assertGreaterEqual(
                height_of(
                    confirm.get_by_role("button", name=name, exact=True)
                ),
                44,
            )

    def _swap_intake_service(self, service):
        original = app.config.get("RESUME_INTAKE_SERVICE")
        app.config["RESUME_INTAKE_SERVICE"] = service
        self.addCleanup(app.config.update, {"RESUME_INTAKE_SERVICE": original})

    def _intake_service_with_adapter(self, adapter):
        return ResumeIntakeService(
            repository=self.intake_repository,
            draft_service=self.draft_service,
            document_adapter=ResumeDocumentAdapter(),
            transcription_adapter=ResumeTranscriptionAdapter(
                service=_SilentTranscriber()
            ),
            policy=selected_policy_for_tests(),
            extraction_adapter=adapter,
            matching_exclusions=lambda owner: set(),
        )

    def _open_composer(self, page):
        page.locator("[data-my-data-open]").click()
        page.locator("[data-my-data-overlay]").wait_for(timeout=10000)

    def test_draft_recovers_text_after_reload(self):
        page = self._new_page(viewport={"width": 1440, "height": 1000})
        page.goto(f"{self.base_url}/app/settings/my-data", wait_until="load")
        page.locator("[data-my-data-groups]").wait_for(timeout=15000)
        self._open_composer(page)
        page.locator("[data-my-data-text]").fill("Cross device draft words here")
        # The debounced server save fires while the member keeps reading.
        page.wait_for_timeout(2000)
        page.reload(wait_until="load")
        page.locator("[data-my-data-groups]").wait_for(timeout=15000)
        self._open_composer(page)
        page.wait_for_function(
            "document.querySelector('[data-my-data-text]').value"
            ".indexOf('Cross device draft words here') !== -1",
            timeout=15000,
        )
        note = page.locator("[data-my-data-draft]").inner_text()
        self.assertIn("other device", note)
        page.locator("[data-my-data-discard]").click()
        page.wait_for_function(
            "document.querySelector('[data-my-data-text]').value === ''",
            timeout=10000,
        )

    def test_add_result_survives_debounced_draft_autosave(self):
        page = self._new_page(viewport={"width": 1440, "height": 1000})
        page.goto(f"{self.base_url}/app/settings/my-data", wait_until="load")
        page.locator("[data-my-data-groups]").wait_for(timeout=15000)
        self._open_composer(page)
        page.locator("[data-my-data-text]").fill(
            "I led a quixotic-migration project across two teams in 2024."
        )
        page.locator("[data-my-data-add]").click()
        page.wait_for_selector(".my-data__proposal", timeout=20000)
        quote = page.locator("[data-my-data-proposals]").inner_text()
        self.assertIn("quixotic-migration", quote)
        self.assertGreater(page.locator(".my-data__proposal button").count(), 0)
        # Unresolved Add schedules a debounced draft PUT. That save must
        # keep the review card, not empty the shared proposal host.
        page.wait_for_timeout(2000)
        self.assertIn(
            "quixotic-migration",
            page.locator("[data-my-data-proposals]").inner_text(),
        )
        self.assertGreater(page.locator(".my-data__proposal button").count(), 0)
        page.locator("[data-my-data-text]").fill(
            "I led a quixotic-migration project across two teams in 2024. More words."
        )
        page.wait_for_timeout(2000)
        self.assertIn(
            "quixotic-migration",
            page.locator("[data-my-data-proposals]").inner_text(),
        )
        self.assertGreater(page.locator(".my-data__proposal button").count(), 0)
        page.locator("[data-my-data-discard]").click()

    def test_draft_conflict_offers_recovery_choice(self):
        page = self._new_page(viewport={"width": 1440, "height": 1000})
        page.goto(f"{self.base_url}/app/settings/my-data", wait_until="load")
        page.locator("[data-my-data-groups]").wait_for(timeout=15000)
        self._open_composer(page)
        page.locator("[data-my-data-text]").fill("Device one words")
        page.wait_for_timeout(2000)
        acknowledged = self.intake_service.get_draft(BROWSER_MEMBER)["draft"]
        self.assertEqual(acknowledged["text"], "Device one words")
        # Another device saves a newer version behind this page's back.
        saved = self.intake_service.save_draft(
            BROWSER_MEMBER,
            {"request_id": str(uuid4()), "text": "Device two words",
             "expected_version": acknowledged["version"]},
        )
        self.assertGreater(saved["draft"]["version"], acknowledged["version"])
        page.locator("[data-my-data-text]").fill("Device one words plus more")
        page.wait_for_function(
            "Array.from(document.querySelectorAll('.my-data__proposal h4'))"
            ".some((node) => node.textContent.indexOf('Two versions') !== -1)",
            timeout=15000,
        )
        cards = page.locator("[data-my-data-proposals]").inner_text()
        self.assertIn("Device one words plus more", cards)
        self.assertIn("Device two words", cards)
        self.assertGreater(
            page.get_by_role("button", name="Keep my words", exact=True).count(),
            0,
        )
        # A later ordinary draft save must not erase the recovery choice.
        page.wait_for_timeout(2000)
        self.assertGreater(
            page.get_by_role("button", name="Keep my words", exact=True).count(),
            0,
        )
        self.assertGreater(
            page.get_by_role("button", name="Use other version", exact=True).count(),
            0,
        )
        # The member's unsaved words survive the choice either way.
        page.get_by_role("button", name="Use other version", exact=True).click()
        page.wait_for_function(
            "document.querySelector('[data-my-data-text]').value"
            ".indexOf('Device two words') !== -1",
            timeout=10000,
        )
        page.locator("[data-my-data-discard]").click()

    def test_reopen_after_other_device_save_shows_conflict(self):
        self._assert_reopen_conflict(viewport={"width": 1440, "height": 1000})

    def test_mobile_reopen_after_other_device_save_shows_conflict(self):
        self._assert_reopen_conflict(viewport={"width": 390, "height": 844})

    def _assert_reopen_conflict(self, *, viewport):
        page = self._new_page(viewport=viewport)
        page.goto(f"{self.base_url}/app/settings/my-data", wait_until="load")
        page.locator("[data-my-data-groups]").wait_for(timeout=15000)
        self._open_composer(page)
        page.locator("[data-my-data-text]").fill("Device A stale words")
        page.wait_for_timeout(2000)
        acknowledged = self.intake_service.get_draft(BROWSER_MEMBER)["draft"]
        self.assertEqual(acknowledged["text"], "Device A stale words")
        saved = self.intake_service.save_draft(
            BROWSER_MEMBER,
            {"request_id": str(uuid4()), "text": "Device B newer words",
             "expected_version": acknowledged["version"]},
        )
        self.assertGreater(saved["draft"]["version"], acknowledged["version"])
        page.locator("[data-my-data-close]").click()
        page.wait_for_function(
            "document.querySelector('[data-my-data-overlay]').hidden === true",
            timeout=10000,
        )
        self._open_composer(page)
        page.wait_for_function(
            "Array.from(document.querySelectorAll('.my-data__proposal h4'))"
            ".some((node) => node.textContent.indexOf('Two versions') !== -1)",
            timeout=15000,
        )
        self.assertIn(
            "Device A stale words",
            page.locator("[data-my-data-text]").input_value(),
        )
        self.assertEqual(
            self.intake_service.get_draft(BROWSER_MEMBER)["draft"]["text"],
            "Device B newer words",
        )
        page.wait_for_timeout(2000)
        self.assertEqual(
            self.intake_service.get_draft(BROWSER_MEMBER)["draft"]["text"],
            "Device B newer words",
        )
        self.assertGreater(
            page.get_by_role("button", name="Keep my words", exact=True).count(),
            0,
        )
        page.locator("[data-my-data-discard]").click()

    def test_delayed_draft_get_after_typing_shows_conflict(self):
        retained_revision = self.intake_repository.load_owner(BROWSER_MEMBER).get("draft_revision", 0)
        seeded = self.intake_service.save_draft(
            BROWSER_MEMBER,
            {"request_id": str(uuid4()), "text": "Server device words"},
        )
        self.assertGreater(seeded["draft"]["version"], retained_revision)
        page = self._new_page(viewport={"width": 1440, "height": 1000})
        pending_gets = []

        def hold_draft_get(route):
            if route.request.method == "GET":
                pending_gets.append(route)
                return
            route.continue_()

        page.route("**/api/resume-intake/me/draft", hold_draft_get)
        page.goto(f"{self.base_url}/app/settings/my-data", wait_until="load")
        page.locator("[data-my-data-groups]").wait_for(timeout=15000)
        self._open_composer(page)
        page.locator("[data-my-data-text]").fill("Local typing after open")
        deadline = time.time() + 5
        while not pending_gets and time.time() < deadline:
            page.wait_for_timeout(50)
        self.assertEqual(len(pending_gets), 1)
        pending_gets[0].continue_()
        page.wait_for_function(
            "Array.from(document.querySelectorAll('.my-data__proposal h4'))"
            ".some((node) => node.textContent.indexOf('Two versions') !== -1)",
            timeout=20000,
        )
        self.assertIn(
            "Local typing after open",
            page.locator("[data-my-data-text]").input_value(),
        )
        self.assertEqual(
            self.intake_service.get_draft(BROWSER_MEMBER)["draft"]["text"],
            "Server device words",
        )
        page.wait_for_timeout(2000)
        self.assertEqual(
            self.intake_service.get_draft(BROWSER_MEMBER)["draft"]["text"],
            "Server device words",
        )
        self.assertGreater(
            page.get_by_role("button", name="Keep my words", exact=True).count(),
            0,
        )
        page.locator("[data-my-data-discard]").click()

    def test_extracted_duplicate_offers_keep_as_separate(self):
        text = "Browser Duplicate works at Northwind Traders"
        fake = DeterministicFakeExtractionAdapter()
        service = self._intake_service_with_adapter(fake)
        self._swap_intake_service(service)
        created = service.submit(
            BROWSER_MEMBER,
            {
                "type": "add_submission",
                "request_id": str(uuid4()),
                "items": [{
                    "client_key": "dup-seed",
                    "record_type": "role",
                    "values": {
                        "role_title": "Browser Duplicate",
                        "employer_name": "Northwind Traders",
                    },
                }],
            },
        )
        record_key = created["saved_items"][0]["record_key"]
        fake.scripted.append({
            "record_type": "role",
            "values": {
                "role_title": "Browser Duplicate",
                "employer_name": "Northwind Traders",
            },
            "outcome": "equivalent",
            "quote": text,
            "match_reference": record_key,
            "confidence": "certain",
        })
        page = self._new_page(viewport={"width": 1440, "height": 1000})
        page.goto(f"{self.base_url}/app/settings/my-data", wait_until="load")
        page.locator("[data-my-data-groups]").wait_for(timeout=15000)
        self._open_composer(page)
        page.locator("[data-my-data-text]").fill(text)
        page.locator("[data-my-data-add]").click()
        page.wait_for_function(
            "document.querySelector('[data-my-data-receipt]').textContent"
            ".indexOf('Already saved') !== -1",
            timeout=20000,
        )
        keep = page.get_by_role("button", name="Keep as separate", exact=True)
        self.assertEqual(keep.count(), 1)
        before = len(service._canonical_items(BROWSER_MEMBER))
        keep.click()
        page.wait_for_function(
            "document.querySelector('[data-my-data-receipt]').textContent"
            ".indexOf('Saved privately') !== -1",
            timeout=20000,
        )
        self.assertEqual(
            len(service._canonical_items(BROWSER_MEMBER)),
            before + 1,
        )
        page.locator("[data-my-data-discard]").click()

    def test_every_extracted_equivalent_renders_its_own_bound_action(self):
        role_quote = "Browser Multi Role at Contoso"
        skill_quote = "Browser Multi Skill"
        fake = DeterministicFakeExtractionAdapter()
        service = self._intake_service_with_adapter(fake)
        self._swap_intake_service(service)
        seeded = service.submit(
            BROWSER_MEMBER,
            {
                "type": "add_submission",
                "request_id": str(uuid4()),
                "items": [
                    {
                        "client_key": "multi-role", "record_type": "role",
                        "values": {"role_title": "Browser Multi Role", "employer_name": "Contoso"},
                    },
                    {
                        "client_key": "multi-skill", "record_type": "skill",
                        "values": {"name": skill_quote},
                    },
                ],
            },
        )
        role_key, skill_key = [item["record_key"] for item in seeded["saved_items"]]
        fake.scripted.extend([
            {
                "record_type": "role",
                "values": {"role_title": "Browser Multi Role", "employer_name": "Contoso"},
                "outcome": "equivalent", "quote": role_quote,
                "match_reference": role_key, "confidence": "certain",
            },
            {
                "record_type": "skill", "values": {"name": skill_quote},
                "outcome": "equivalent", "quote": skill_quote,
                "match_reference": skill_key, "confidence": "certain",
            },
        ])
        page = self._new_page(viewport={"width": 1440, "height": 1000})
        page.goto(f"{self.base_url}/app/settings/my-data", wait_until="load")
        page.locator("[data-my-data-groups]").wait_for(timeout=15000)
        self._open_composer(page)
        page.locator("[data-my-data-text]").fill(f"{role_quote}. {skill_quote}.")
        page.locator("[data-my-data-add]").click()
        page.wait_for_function(
            "document.querySelector('[data-my-data-receipt]').textContent"
            ".indexOf('Already saved') !== -1",
            timeout=20000,
        )
        keep = page.get_by_role("button", name="Keep as separate", exact=True)
        self.assertEqual(keep.count(), 2)
        action_text = page.locator(".my-data__proposal-action").all_inner_texts()
        self.assertEqual(len(action_text), 2)
        self.assertIn("Equivalent 1: role", action_text[0])
        self.assertIn("Equivalent 2: skill", action_text[1])
        before = len(service._canonical_items(BROWSER_MEMBER))
        keep.nth(1).click()
        page.wait_for_function(
            "document.querySelector('[data-my-data-receipt]').textContent"
            ".indexOf('Saved privately') !== -1",
            timeout=20000,
        )
        current = service._canonical_items(BROWSER_MEMBER)
        self.assertEqual(len(current), before + 1)
        self.assertEqual(current[-1]["record_type"], "skill")
        self.assertEqual(current[-1]["values"]["name"], skill_quote)
        page.locator("[data-my-data-discard]").click()

    def _assert_mixed_actions_survive_sequential_acceptance(self, viewport, label):
        role_quote = f"{label} Sequential Role at Contoso"
        skill_quote = f"{label} Sequential Skill"
        new_quote = f"{label} Remaining Proposal"
        unfinished = f"{label} unfinished draft stays here"
        fake = DeterministicFakeExtractionAdapter()
        service = self._intake_service_with_adapter(fake)
        self._swap_intake_service(service)
        seeded = service.submit(
            BROWSER_MEMBER,
            {
                "type": "add_submission",
                "request_id": str(uuid4()),
                "items": [
                    {
                        "client_key": f"{label}-role", "record_type": "role",
                        "values": {"role_title": f"{label} Sequential Role", "employer_name": "Contoso"},
                    },
                    {
                        "client_key": f"{label}-skill", "record_type": "skill",
                        "values": {"name": skill_quote},
                    },
                ],
            },
        )
        role_key, skill_key = [item["record_key"] for item in seeded["saved_items"]]
        fake.scripted.extend([
            {
                "record_type": "role",
                "values": {"role_title": f"{label} Sequential Role", "employer_name": "Contoso"},
                "outcome": "equivalent", "quote": role_quote,
                "match_reference": role_key, "confidence": "certain",
            },
            {
                "record_type": "skill", "values": {"name": skill_quote},
                "outcome": "equivalent", "quote": skill_quote,
                "match_reference": skill_key, "confidence": "certain",
            },
            {
                "record_type": "skill", "values": {"name": new_quote},
                "outcome": "new", "quote": new_quote, "confidence": "certain",
            },
        ])
        page = self._new_page(viewport=viewport)
        page.goto(f"{self.base_url}/app/settings/my-data", wait_until="load")
        page.locator("[data-my-data-groups]").wait_for(timeout=15000)
        self._open_composer(page)
        page.locator("[data-my-data-text]").fill(
            ". ".join((role_quote, skill_quote, new_quote))
        )
        page.locator("[data-my-data-add]").click()
        keep = page.get_by_role("button", name="Keep as separate", exact=True)
        save = page.get_by_role("button", name="Save", exact=True)
        page.wait_for_function(
            "document.querySelectorAll('.my-data__proposal-action button').length === 2",
            timeout=20000,
        )
        self.assertEqual(keep.count(), 2)
        self.assertEqual(save.count(), 1)

        page.locator("[data-my-data-text]").fill(unfinished)
        page.wait_for_timeout(2000)
        self.assertEqual(
            service.get_draft(BROWSER_MEMBER)["draft"]["text"], unfinished
        )
        before = len(service._canonical_items(BROWSER_MEMBER))
        keep.nth(0).click()
        page.wait_for_function(
            "document.querySelectorAll('.my-data__proposal-action button').length === 1",
            timeout=20000,
        )
        self.assertEqual(keep.count(), 1)
        self.assertEqual(save.count(), 1)
        self.assertEqual(page.locator("[data-my-data-text]").input_value(), unfinished)
        self.assertEqual(service.get_draft(BROWSER_MEMBER)["draft"]["text"], unfinished)
        self.assertEqual(len(service._canonical_items(BROWSER_MEMBER)), before + 1)

        keep.nth(0).click()
        page.wait_for_function(
            "document.querySelectorAll('.my-data__proposal-action button').length === 0",
            timeout=20000,
        )
        self.assertEqual(keep.count(), 0)
        self.assertEqual(save.count(), 1)
        self.assertEqual(page.locator("[data-my-data-text]").input_value(), unfinished)
        self.assertEqual(service.get_draft(BROWSER_MEMBER)["draft"]["text"], unfinished)
        self.assertEqual(len(service._canonical_items(BROWSER_MEMBER)), before + 2)

        save.click()
        page.wait_for_function(
            "document.querySelectorAll('[data-my-data-proposals] button').length === 0",
            timeout=20000,
        )
        self.assertEqual(len(service._canonical_items(BROWSER_MEMBER)), before + 3)
        self.assertEqual(page.locator("[data-my-data-text]").input_value(), unfinished)
        self.assertEqual(service.get_draft(BROWSER_MEMBER)["draft"]["text"], unfinished)
        page.locator("[data-my-data-discard]").click()

    def test_desktop_keeps_mixed_actions_draft_and_proposal(self):
        self._assert_mixed_actions_survive_sequential_acceptance(
            {"width": 1440, "height": 1000}, "Desktop"
        )

    def test_mobile_keeps_mixed_actions_draft_and_proposal(self):
        self._assert_mixed_actions_survive_sequential_acceptance(
            {"width": 390, "height": 844}, "Mobile"
        )

    def test_provider_failure_keeps_manual_path(self):
        fake = DeterministicFakeExtractionAdapter()
        fake.fail_with = "provider_unavailable"
        self._swap_intake_service(self._intake_service_with_adapter(fake))
        page = self._new_page(viewport={"width": 1440, "height": 1000})
        page.goto(f"{self.base_url}/app/settings/my-data", wait_until="load")
        page.locator("[data-my-data-groups]").wait_for(timeout=15000)
        self._open_composer(page)
        page.locator("[data-my-data-text]").fill(
            "Provider outage journey words stay reviewable"
        )
        page.locator("[data-my-data-add]").click()
        page.wait_for_selector(".my-data__proposal", timeout=20000)
        receipt = page.locator("[data-my-data-receipt]").inner_text()
        self.assertIn("unavailable right now", receipt)
        proposals = page.locator("[data-my-data-proposals]").inner_text()
        self.assertIn("Provider outage journey words", proposals)
        # Exactly one provider attempt: no silent second try hides anywhere.
        self.assertEqual(len(fake.calls), 1)
        self.assertGreater(page.locator(".my-data__proposal button").count(), 0)
        page.wait_for_timeout(2000)
        still = page.locator("[data-my-data-proposals]").inner_text()
        self.assertIn("Provider outage journey words", still)
        self.assertGreater(page.locator(".my-data__proposal button").count(), 0)
        page.locator("[data-my-data-discard]").click()

    def test_oversize_file_refused_before_attach(self):
        page = self._new_page(viewport={"width": 1440, "height": 1000})
        page.goto(f"{self.base_url}/app/settings/my-data", wait_until="load")
        page.locator("[data-my-data-groups]").wait_for(timeout=15000)
        self._open_composer(page)
        page.locator("[data-my-data-file]").set_input_files({
            "name": "too-big.bin",
            "mimeType": "application/pdf",
            "buffer": bytes(10_000_001),
        })
        page.wait_for_function(
            "document.querySelector('[data-my-data-draft]').textContent"
            ".indexOf('over 10 MB') !== -1",
            timeout=10000,
        )
        self.assertEqual(
            page.locator("[data-my-data-attachments] li").count(), 0
        )


if __name__ == "__main__":
    unittest.main()
