"""Owner resume page (PS-RESUME-PAGE-OWNER-001, round D1): server render and static contracts.

Real Flask test-client requests against the private /app/resume route with an
injected in-memory draft service. These prove the page flag, the server-side
identity boundary, the template structure and the static script/style
contracts. Browser behaviour is proven in test_resume_page_owner_browser.py.
Fixtures are fictional people.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path
from uuid import UUID

from app import app
from services.resume_draft_repository import InMemoryCanonicalCatalog, InMemoryResumeDraftRepository
from services.resume_draft_service import ResumeDraftService

ROOT = Path(__file__).resolve().parents[1]
JS = {name: (ROOT / "static" / "js" / name).read_text(encoding="utf-8")
      for name in ("resume-page.js", "resume-page-model.js", "resume-page-ask.js")}
CSS = (ROOT / "static" / "css" / "resume-page.css").read_text(encoding="utf-8")
SHARED_ORDER = ["impact_statement", "skills", "experience", "projects", "education", "certifications", "awards"]

# Every id today's editor, the Guide, media and publication scripts rely on.
LEGACY_IDS = (
    "resume-editor-title", "resume-editor-status", "resume-editor-reload", "resume-editor-review",
    "resume-editor-story-controls", "resume-story-choice", "resume-story-select", "resume-story-status",
    "resume-story-create", "resume-story-wording", "resume-editor-story-preview", "resume-editor-lists",
    "resume-editor-add-education", "new-education-title", "new-education-institution", "new-education-status",
)
CONFIG_KEYS = (
    "TESTING", "PEERSLATE_ALLOW_DEV_IDENTITY", "PEERSLATE_DEV_USER_KEY", "PEERSLATE_TRUST_EASYAUTH_HEADERS",
    "PEERSLATE_RESUME_EDITOR_ENABLED", "PEERSLATE_RESUME_PAGE_ENABLED", "RESUME_DRAFT_SERVICE",
)


def role(key, owner_label):
    return {
        "record_key": key, "record_type": "role", "content_token": "1", "access_revision": 1,
        "editable": True, "save_mode": "canonical",
        "values": {"role_title": "Field Engineer", "employer_name": owner_label, "location_text": None,
                   "summary": owner_label + " summary", "start_date": "2024-02-01", "end_date": None,
                   "date_precision": "month", "employment_type": "full_time", "current_role": True},
        "resume_display": False, "visitor_ai": False, "private_assistance_excluded": False,
    }


class OwnerResumePageRenderTests(unittest.TestCase):
    def setUp(self):
        self.original = {key: app.config.get(key) for key in CONFIG_KEYS}
        catalog = InMemoryCanonicalCatalog()
        catalog.put_item("member-river", role(str(UUID(int=71, version=4)), "Riverbend Labs"))
        catalog.put_item("member-other", role(str(UUID(int=72, version=4)), "Other Member Works"))
        self.service = ResumeDraftService(repository=InMemoryResumeDraftRepository(), catalog=catalog)
        app.config.update(TESTING=True, PEERSLATE_ALLOW_DEV_IDENTITY=True, PEERSLATE_DEV_USER_KEY="member-river",
                          PEERSLATE_TRUST_EASYAUTH_HEADERS=False, PEERSLATE_RESUME_EDITOR_ENABLED=True,
                          RESUME_DRAFT_SERVICE=self.service)
        app.config.pop("PEERSLATE_RESUME_PAGE_ENABLED", None)

    def tearDown(self):
        for key, value in self.original.items():
            if value is None:
                app.config.pop(key, None)
            else:
                app.config[key] = value

    def page(self, flag=None):
        if flag is None:
            app.config.pop("PEERSLATE_RESUME_PAGE_ENABLED", None)
        else:
            app.config["PEERSLATE_RESUME_PAGE_ENABLED"] = flag
        response = app.test_client().get("/app/resume")
        self.assertEqual(response.status_code, 200)
        return response.get_data(as_text=True)

    # --- criterion flag_off_unchanged -------------------------------------
    def test_flag_off_renders_todays_editor_only(self):
        for flag in (None, False, "true", 1):
            body = self.page(flag)
            self.assertNotIn('id="resume-page"', body)
            self.assertNotIn("resume-page.css", body)
            self.assertNotIn("resume-page.js", body)
            self.assertNotIn("rp-body", body)
            for legacy_id in LEGACY_IDS:
                self.assertEqual(body.count('id="%s"' % legacy_id), 1, legacy_id)

    def test_flag_off_output_is_independent_of_the_new_partials(self):
        self.assertEqual(self.page(None), self.page(False))

    # --- criterion page_structure -----------------------------------------
    def test_flag_on_renders_page_shell_rail_and_both_ask_panels(self):
        body = self.page(True)
        self.assertIn('id="resume-page"', body)
        self.assertIn('data-workspace-url="/api/resume-drafts/me"', body)
        self.assertRegex(body, r'<body[^>]*class="[^"]*\brp-body\b')
        for marker in ('id="resume-page-rail"', 'id="resume-page-secnav"', 'id="resume-page-glance"',
                       'id="resume-page-ask-rail"', 'id="resume-page-ask-main"', 'id="resume-page-hero"',
                       'id="resume-page-sections"', 'id="resume-page-jump"', 'id="resume-page-edit"',
                       'id="resume-page-editor"', 'id="resume-page-glance-phone"', 'id="resume-page-band"',
                       'id="resume-page-after"'):
            self.assertEqual(body.count(marker), 1, marker)
        # Rail order: section list, Credentials at a glance, Ask.
        rail = body[body.index('id="resume-page-rail"'):body.index('class="rp-content"')]
        self.assertLess(rail.index("On this resume"), rail.index("Credentials at a glance"))
        self.assertLess(rail.index("Credentials at a glance"), rail.index('data-rp-ask="rail"'))
        # Scripts load after today's editor, model before ask before page.
        order = [body.index(name) for name in ("js/resume-editor.js", "js/resume-page-model.js",
                                               "js/resume-page-ask.js", "js/resume-page.js")]
        self.assertEqual(order, sorted(order))

    def test_flag_on_keeps_todays_editor_complete_and_unique(self):
        body = self.page(True)
        for legacy_id in LEGACY_IDS:
            self.assertEqual(body.count('id="%s"' % legacy_id), 1, legacy_id)
        ids = re.findall(r'\sid="([^"]+)"', body)
        duplicates = sorted({i for i in ids if ids.count(i) > 1})
        self.assertEqual(duplicates, [])

    # --- criterion owner_identity ------------------------------------------
    def test_identity_is_server_derived_and_other_members_never_render(self):
        body = self.page(True)
        self.assertNotIn("Other Member Works", body)
        self.assertNotIn("member-other", body)
        self.assertNotIn("member-river", body)  # no owner key is written into the page
        workspace = app.test_client().get("/api/resume-drafts/me?owner=member-other").get_json()
        employers = [item["values"].get("employer_name") for item in workspace["items"]]
        self.assertEqual(employers, ["Riverbend Labs"])

    def test_signed_out_visitor_is_sent_to_sign_in(self):
        app.config.update(PEERSLATE_ALLOW_DEV_IDENTITY=False, PEERSLATE_DEV_USER_KEY=None, PEERSLATE_RESUME_PAGE_ENABLED=True)
        response = app.test_client().get("/app/resume")
        self.assertIn(response.status_code, (302, 303))
        self.assertIn("return_to=/app/resume", response.headers["Location"].replace("%2F", "/"))

    def test_member_name_is_escaped_in_every_server_rendered_slot(self):
        from identity import get_current_identity  # noqa: F401 - imported to prove the module boundary
        app.config["PEERSLATE_RESUME_PAGE_ENABLED"] = True
        hostile = '<img src=x onerror="alert(1)"> Quinn'

        class Identity:
            user_key = "member-river"
            display_name = hostile

        import resume_draft_routes
        original = resume_draft_routes.get_current_identity
        resume_draft_routes.get_current_identity = lambda: Identity()
        try:
            body = app.test_client().get("/app/resume").get_data(as_text=True)
        finally:
            resume_draft_routes.get_current_identity = original
        self.assertNotIn("<img src=x", body)
        self.assertIn("&lt;img src=x onerror=&#34;alert(1)&#34;&gt; Quinn</h1>", body)

    # --- criterion truthful_ask / safe_rendering (static) -----------------
    def test_page_scripts_only_read_the_private_workspace_and_build_no_markup_from_data(self):
        joined = "\n".join(JS.values())
        self.assertEqual(joined.count("fetch("), 1)
        self.assertNotRegex(joined, r"/api/")
        for sink in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval(", "new Function"):
            self.assertNotIn(sink, joined, sink)
        self.assertIn("Ask AI isn’t available right now.", JS["resume-page-ask.js"])

    def test_view_model_follows_the_one_shared_section_order(self):
        match = re.search(r"SECTION_ORDER = Object\.freeze\(\[(.*?)\]\)", JS["resume-page-model.js"], re.S)
        self.assertIsNotNone(match)
        order = re.findall(r"'([a-z_]+)'", match.group(1))
        self.assertEqual(order, SHARED_ORDER)
        try:
            from services.resume_guide_contract import GUIDE_SECTION_ORDER
        except ImportError:  # B1 contract not on this base yet; the literal above is the pin.
            return
        self.assertEqual(list(GUIDE_SECTION_ORDER), order)

    # --- criterion theme_tokens / phone / reduced_motion (static) ---------
    def test_locked_theme_tokens_and_layout_geometry(self):
        for token in ("--rp-backdrop: #3f6a51", "--rp-frame: #f3ece0", "--rp-rail-card: #faf6ec",
                      "--rp-rail-line: #e3d7c1", "--rp-current: #e8dfc9", "--rp-text: 12.5px",
                      "--rp-rail-width: 268px", "--rp-wrap: min(calc(100% - 32px), 1240px)",
                      "stroke-opacity='0.11'", "background-attachment: fixed"):
            self.assertIn(token, CSS, token)
        self.assertIn("@media (max-width: 959px)", CSS)
        self.assertNotIn("@media (max-width: 960px)", CSS)
        self.assertNotRegex(CSS, r"prefers-color-scheme:\s*dark|data-theme=\"?dark")

    def test_the_shared_footer_is_not_restyled_here(self):
        # The footer belongs to the trust-pages package; this page never overrides it.
        self.assertNotRegex(CSS, r"\.footer\b")

    def test_motion_is_removed_under_reduced_motion(self):
        # Every transition on the page is switched off under reduced motion (D1d: the rail Ask no longer animates).
        reduced = " ".join(re.findall(r"@media \(prefers-reduced-motion: reduce\) \{(.*?)\}\s*\}", CSS, re.S))
        animated = re.findall(r"([^{}]+)\{[^{}]*\btransition:\s*(?!none)[^;{}]+;", CSS)
        self.assertTrue(animated)
        for selector in animated:
            self.assertIn(selector.strip().splitlines()[-1].split(":")[0].strip(), reduced, selector)
        self.assertIn("transition: none", reduced)
        # Stone stacking only animates when the visitor allows motion.
        self.assertRegex(CSS, r"prefers-reduced-motion: no-preference\) \{\s*\.rp-stone \{ opacity: 0; animation")

    def test_text_colour_pairs_meet_wcag_aa(self):
        def lum(hex_colour):
            channels = [int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5)]
            lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
            return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]

        def ratio(a, b):
            la, lb = sorted((lum(a), lum(b)), reverse=True)
            return (la + 0.05) / (lb + 0.05)

        body_pairs = [("#2d3932", "#faf8f2"), ("#495a51", "#faf8f2"), ("#596860", "#faf8f2"),
                      ("#596860", "#f3ece0"), ("#495a51", "#faf6ec"), ("#1d3527", "#ece4d3"),
                      ("#2f5640", "#fffdf8"), ("#3a6a4f", "#faf6ec"), ("#7d5916", "#f3ecdd"),
                      ("#214e3c", "#f4dfa6"), ("#6e5d3b", "#fbf5e9"), ("#66716a", "#ffffff"),
                      ("#fbf6ea", "#17263f"), ("#8a2c2c", "#fdf3f2"),
                      # D1d: skill line source, Ask placeholder, tab labels on the bar and the selected pill
                      ("#596860", "#f3ecdd"), ("#5b4a2a", "#fbf5e9"), ("#2d3932", "#f7f2e6"), ("#1d3527", "#e8dfc9")]
        for fg, bg in body_pairs:
            self.assertGreaterEqual(ratio(fg, bg), 4.5, (fg, bg))
        self.assertGreaterEqual(ratio("#a8690a", "#faf8f2"), 3.0)  # 27px highlight numbers (large text)
        self.assertGreaterEqual(ratio("#a8781e", "#faf8f2"), 3.0)  # focus ring / gold edge (non-text)
        self.assertGreaterEqual(ratio("#5b7466", "#e3ebe2"), 3.0)  # the skill panel's scroll thumb on its track (non-text)

    # --- D1d: main Ask tabs, the rail Ask always expanded, skill lines, Looking Ahead picture ---
    def ask_html(self, body, variant):
        start = body.index('id="resume-page-ask-%s"' % variant)
        return body[start:body.index("</section>", start)]

    def test_main_ask_has_three_real_tabs_in_its_mountain_header(self):
        main = self.ask_html(self.page(True), "main")
        top = main[main.index('class="rp-ask__top"'):main.index('class="rp-ask__body"')]
        self.assertEqual(top.count('role="tablist"'), 1)
        tabs = re.findall(r'<button type="button" class="rp-tab" role="tab" id="([^"]+)" aria-controls="([^"]+)" '
                          r'aria-selected="(true|false)" tabindex="(0|-1)" data-rp-tab="([a-z]+)">(.*?)</button>', top)
        self.assertEqual([t[4] for t in tabs], ["ask", "highlights", "job"])
        self.assertEqual([(t[2], t[3]) for t in tabs], [("true", "0"), ("false", "-1"), ("false", "-1")])
        self.assertEqual(tabs[0][5], "Ask a question")
        self.assertEqual(tabs[1][5], "Career highlights")
        self.assertEqual(tabs[2][5], 'Compare a job <span class="rp-tab__soon">Soon</span>')
        body = main[main.index('class="rp-ask__body"'):]
        for tab_id, panel_id, selected, _, name, _ in tabs:
            panel = re.search(r'<div class="rp-ask__panel" role="tabpanel" id="%s" aria-labelledby="%s"[^>]*>' % (panel_id, tab_id), body)
            self.assertIsNotNone(panel, name)
            self.assertEqual("hidden" in panel.group(0), selected == "false", name)
        # Career highlights: a marked placeholder, never an invented story; Compare a job: Coming soon, no working control.
        highlights = body[body.index('-panel-highlights"'):body.index('-panel-job"')]
        self.assertIn("Placeholder", highlights)
        self.assertIn("The Guide will draft your career highlights from your published resume, for your OK.", highlights)
        job = body[body.index('-panel-job"'):body.index("data-rp-ask-log")]
        self.assertIn("Coming soon", job)
        self.assertNotRegex(job, r"<(button|textarea|input|select|a)\b")
        # The question box sits outside every tab panel, so it is there in every tab.
        self.assertGreater(body.index("data-rp-ask-form"), body.index('-panel-job"'))
        self.assertEqual(body.count("data-rp-ask-form"), 1)

    def test_rail_ask_is_the_full_panel_with_no_compact_or_grow_state(self):
        rail = self.ask_html(self.page(True), "rail")
        self.assertNotIn("data-rp-ask-more", rail)
        self.assertNotIn('role="tablist"', rail)
        for text in ("The person behind the experience.", "Pick a question, or type your own", "data-rp-ask-chips",
                     "data-rp-ask-form", "Answers come only from your published resume."):
            self.assertIn(text, rail)
        for gone in ("is-grown", "mainAskAway", "railHasRoom", "watchMainAsk", "data-rp-ask-more", "inert"):
            self.assertNotIn(gone, JS["resume-page.js"], gone)
        self.assertNotIn("rp-ask__more", CSS)
        self.assertNotIn("is-grown", CSS)
        self.assertNotRegex(CSS, r"\.rp-ask--rail[^{]*\{[^}]*(opacity: 0|transition)")

    def test_skill_lines_are_derived_in_the_one_adapter_capped_at_three(self):
        model = JS["resume-page-model.js"]
        self.assertIn("var MAX_SKILL_LINES = 3;", model)
        self.assertIn("skill.lines = skillLines(skill, ordered)", model)
        self.assertIn(".slice(0, MAX_SKILL_LINES)", model)
        self.assertIn(".slice(0, Model.MAX_SKILL_LINES)", JS["resume-page.js"])
        # Generic rule only: no member names or employers in the adapter.
        for specific in ("Pete", "Northrop", "L3Harris", "Air Force", "Riverbend"):
            self.assertNotIn(specific, model, specific)

    def test_skill_panel_has_one_scroll_region_and_an_always_visible_bar(self):
        self.assertIn("scrollbar-color: #5b7466 #e3ebe2", CSS)
        self.assertRegex(CSS, r"\.rp-skills__scroll \{[^}]*overflow-y: auto")
        self.assertRegex(CSS, r"\.rp-skills__in \{ margin-block: auto; \}")
        self.assertRegex(CSS, r"\.rp-scrollbar \{[^}]*background: #e3ebe2")
        self.assertRegex(CSS, r"\.rp-scrollbar__thumb \{[^}]*background: #5b7466")

    def test_looking_ahead_has_no_stock_picture(self):
        self.assertNotIn("feed-mountain-ridge", CSS)
        self.assertIn(".rp-ahead--text { grid-template-columns: minmax(0, 1fr); }", CSS)
        self.assertIn("lookingAheadPicture: null", JS["resume-page-model.js"])

    def test_every_image_source_goes_through_the_one_static_guard(self):
        page = JS["resume-page.js"]
        self.assertEqual(page.count("function staticImagePath("), 1)
        self.assertNotIn("localImage", page)
        self.assertNotRegex(page, r"/\^\\/static\\//\.test")  # no second, weaker prefix check
        # Each image source assignment uses a value returned by the guard, never the raw member string.
        assignments = re.findall(r"\b(?:img\.src|source\.srcset)\s*=\s*([A-Za-z_.]+);", page)
        self.assertEqual(sorted(assignments), ["phoneSrc", "photoSrc", "picSrc"])
        for name in ("photoSrc", "picSrc", "phoneSrc"):
            self.assertRegex(page, r"var %s = [^;]*staticImagePath\(" % name)
        for js in JS.values():
            self.assertNotRegex(js, r"style\.(?:background|backgroundImage)\s*=|\.setAttribute\('(?:src|srcset|style)'")

    def test_ask_header_art_is_a_local_asset(self):
        asset = ROOT / "static" / "images" / "resume-page" / "ask-mountains.png"
        self.assertTrue(asset.is_file())
        self.assertLess(asset.stat().st_size, 120_000)
        self.assertIn('url("../images/resume-page/ask-mountains.png")', CSS)


if __name__ == "__main__":
    unittest.main()
