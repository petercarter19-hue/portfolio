"""Owner resume page (PS-RESUME-PAGE-OWNER-001, D1 and D1d): real browser journeys.

Playwright drives headless Chrome against a locally served Flask app with the
page flag on. The draft workspace comes from the real ResumeDraftService over
in-memory stores, or from a recorded workspace double at the same service
boundary for layout journeys. The application's HTTP responses are never
intercepted, and no AI provider exists in this test: the page makes no AI call.
Fixtures are fictional people. Ordinary discovery skips when Playwright or
Chrome is unavailable.
"""

from __future__ import annotations

import copy
import logging
import threading
import unittest
from uuid import UUID

from werkzeug.serving import make_server

from app import app, limiter
from services.resume_draft_repository import (
    CanonicalReadUnavailable,
    InMemoryCanonicalCatalog,
    InMemoryResumeDraftRepository,
)
from services.resume_draft_service import ResumeDraftService

try:
    from playwright.sync_api import sync_playwright
except ModuleNotFoundError:  # pragma: no cover - environment capability gate
    sync_playwright = None

try:
    from scripts.capture_ps_journal_j1_evidence import _resolve_chrome

    CHROME_EXECUTABLE = _resolve_chrome()
except Exception:  # pragma: no cover - optional local browser helper
    CHROME_EXECUTABLE = None

OWNER = "resume-page-member"
OTHER = "resume-page-other-member"
CONFIG_KEYS = ("TESTING", "PEERSLATE_ALLOW_DEV_IDENTITY", "PEERSLATE_DEV_USER_KEY", "PEERSLATE_TRUST_EASYAUTH_HEADERS",
               "PEERSLATE_RESUME_EDITOR_ENABLED", "PEERSLATE_RESUME_PAGE_ENABLED", "PEERSLATE_RESUME_INTAKE_ENABLED",
               "PEERSLATE_RESUME_MEDIA_ENABLED", "PEERSLATE_RESUME_PUBLICATION_ENABLED", "RESUME_DRAFT_SERVICE")


def key(n):
    return str(UUID(int=n, version=4))


def item(n, record_type, values, **extra):
    row = {"record_key": key(n), "record_type": record_type, "content_token": "1", "access_revision": 1,
           "editable": True, "save_mode": "canonical", "has_draft": False, "orphaned": False,
           "values": values, "proposed_values": None, "resume_display": False, "visitor_ai": False}
    row.update(extra)
    return row


def role(n, employer, title, start, end=None, place=None, summary=None, current=False):
    return item(n, "role", {"role_title": title, "employer_name": employer, "location_text": place,
                            "summary": summary, "start_date": start, "end_date": end, "date_precision": "month",
                            "employment_type": "full_time", "current_role": current})


def riley_workspace():
    """A fictional member with every D1 section type."""
    items = [
        role(1, "Harbor Light Robotics", "Controls Engineer", "2023-03-01", None, "Tacoma, WA",
             "Leads controls integration for the harbor crane retrofit program.", current=True),
        role(2, "Cedar Grid Utilities", "Reliability Analyst", "2020-06-01", "2023-02-01", "Spokane, WA",
             "Built the outage-risk model used across the regional substations."),
        role(3, "North Ridge Transit", "Systems Technician", "2018-01-01", "2020-05-01", "Boise, ID",
             "Kept the light-rail signalling cabinets inspected and documented."),
        item(10, "accomplishment", {"wording": "Cut crane commissioning time by 18% across 6 berths.",
                                    "metric_value": None, "metric_label": None}, parent_key=key(1)),
        item(11, "accomplishment", {"wording": "Mentored four new technicians.", "metric_value": None,
                                    "metric_label": None}),
        item(20, "skill", {"name": "PLC programming", "summary": "Programs and validates the crane PLC logic."}),
        item(21, "skill", {"name": "Reliability modelling", "summary": "Built the substation outage-risk model."}),
        item(22, "skill", {"name": "Field safety", "summary": None}),
        item(30, "education", {"title": "M.S. Electrical Engineering", "institution_name": "Lakeview University",
                               "degree_name": None, "field_of_study": None, "education_status": "completed",
                               "grade_text": None, "location_text": None, "summary": None,
                               "start_date": None, "end_date": "2022-05-01", "date_precision": "month"}),
        item(31, "education", {"title": "Ph.D. Systems Engineering", "institution_name": "Coastline Institute",
                               "degree_name": None, "field_of_study": None, "education_status": "admitted",
                               "grade_text": None, "location_text": None, "summary": None,
                               "start_date": "2027-01-01", "end_date": None, "date_precision": "month"}),
        item(32, "education", {"title": "B.S. Mechanical Engineering", "institution_name": "Lakeview University",
                               "degree_name": None, "field_of_study": None, "education_status": "completed",
                               "grade_text": None, "location_text": None, "summary": None,
                               "start_date": None, "end_date": "2017-12-01", "date_precision": "month"}),
        item(40, "credential", {"name": "Certified Reliability Engineer", "issuer": "Quality Society",
                                "identifier": None, "issue_date": "2021-09-01", "expiration_date": None,
                                "issue_date_precision": "month", "expiration_date_precision": None,
                                "verification_url": None, "completion_status": "completed"}),
        item(50, "knowledge", {"title": "Why I build", "wording": "I grew up fixing tractors with my aunt.",
                               "classification": "personal"}),
    ]
    return {"draft_version": 3, "base_publication_version": None, "story_entry_key": key(50), "items": items,
            "capabilities": {"canonical_read": "ok", "persistence": "in_memory_not_live_db", "publishes": False}}


class SwitchableCatalog(InMemoryCanonicalCatalog):
    """The real in-memory catalog, which can be switched into the service's actual outage error."""

    outage = False

    def list_items(self, owner_user_key):
        if self.outage:
            raise CanonicalReadUnavailable()
        return super().list_items(owner_user_key)


class RecordedWorkspaceService:
    """A draft-service double at the route boundary: GET returns the owner's workspace only."""

    def __init__(self, workspaces):
        self.workspaces = workspaces

    def get_workspace(self, owner):
        return copy.deepcopy(self.workspaces.get(owner, {"draft_version": 0, "items": [],
                                                         "capabilities": {"canonical_read": "ok"}}))

    def commit(self, owner, payload):  # pragma: no cover - the page never writes
        raise AssertionError("The owner resume page must not write")


def _shutdown(server, thread):
    server.shutdown()
    thread.join(timeout=5)


@unittest.skipUnless(sync_playwright is not None and CHROME_EXECUTABLE,
                     "Playwright and Google Chrome are required for the owner resume page browser proof")
class OwnerResumePageBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = {k: app.config.get(k) for k in CONFIG_KEYS}
        cls.limiter_was_enabled = limiter.enabled
        logging.getLogger("werkzeug").setLevel(logging.ERROR)

        def restore():
            for k, v in cls.original.items():
                if v is None:
                    app.config.pop(k, None)
                else:
                    app.config[k] = v
            limiter.enabled = cls.limiter_was_enabled

        cls.addClassCleanup(restore)
        app.config.update(TESTING=True, PEERSLATE_ALLOW_DEV_IDENTITY=True, PEERSLATE_DEV_USER_KEY=OWNER,
                          PEERSLATE_TRUST_EASYAUTH_HEADERS=False, PEERSLATE_RESUME_EDITOR_ENABLED=True,
                          PEERSLATE_RESUME_PAGE_ENABLED=True, PEERSLATE_RESUME_INTAKE_ENABLED=False,
                          PEERSLATE_RESUME_MEDIA_ENABLED=False, PEERSLATE_RESUME_PUBLICATION_ENABLED=False)
        limiter.enabled = False
        server = make_server("127.0.0.1", 0, app, threaded=True)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        cls.addClassCleanup(_shutdown, server, thread)
        cls.base = "http://127.0.0.1:%d" % server.server_port
        runtime = sync_playwright().start()
        cls.addClassCleanup(runtime.stop)
        cls.browser = runtime.chromium.launch(executable_path=CHROME_EXECUTABLE, headless=True)
        cls.addClassCleanup(cls.browser.close)

    def setUp(self):
        other = {"draft_version": 1, "items": [role(90, "Other Member Works", "Analyst", "2019-01-01")],
                 "capabilities": {}}
        self.workspaces = {OWNER: riley_workspace(), OTHER: other}
        app.config.update(PEERSLATE_DEV_USER_KEY=OWNER, RESUME_DRAFT_SERVICE=RecordedWorkspaceService(self.workspaces))

    def open(self, width=1440, height=900, reduced=False):
        context = self.browser.new_context(viewport={"width": width, "height": height},
                                           reduced_motion="reduce" if reduced else "no-preference")
        self.addCleanup(context.close)
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        self.addCleanup(lambda: self.assertEqual(errors, []))
        page.goto(self.base + "/app/resume")
        page.wait_for_selector('#resume-page[data-state="ready"]')
        return page

    def no_sideways_scroll(self, page):
        return page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")

    # sections_render, rail_nav, glance
    def test_sections_render_in_the_approved_order_from_the_members_own_workspace(self):
        page = self.open()
        ids = page.eval_on_selector_all("#resume-page-sections > section", "els => els.map(e => e.id)")
        self.assertEqual(ids, ["rp-story", "rp-skills", "rp-experience", "rp-looking-ahead", "rp-credentials",
                               "rp-constellation-phone"])
        nav = page.eval_on_selector_all("#resume-page-secnav a", "els => els.map(e => e.textContent.trim())")
        self.assertEqual(nav, ["Overview", "Skills", "Experience", "Looking Ahead", "Credentials",
                               "Career constellation"])
        self.assertEqual(page.text_content("#resume-page-name"), "Local PeerSlate Test User")
        self.assertEqual(page.text_content("#resume-page-ask-main-title"), "Ask Local AI")
        self.assertEqual(page.inner_text("[data-rp-headline]").upper(), "CONTROLS ENGINEER")
        roles = page.eval_on_selector_all(".rp-role__org", "els => els.map(e => e.textContent)")
        self.assertEqual(roles, ["Harbor Light Robotics", "Cedar Grid Utilities", "North Ridge Transit"])
        self.assertIn("Mar 2023 – Present", page.inner_text(".rp-role"))
        glance = page.eval_on_selector_all("#resume-page-glance li b", "els => els.map(e => e.textContent)")
        self.assertEqual(glance, ["M.S. Electrical Engineering", "Ph.D. Systems Engineering",
                                  "Certified Reliability Engineer"])
        self.assertIn("Starting January 2027", page.inner_text("#resume-page-glance"))
        self.assertIn("I grew up fixing tractors", page.inner_text("#rp-story"))
        self.assertIn("Mentored four new technicians.", page.inner_text(".rp-unlinked"))
        self.assertNotIn("Other Member Works", page.content())
        self.assertTrue(self.no_sideways_scroll(page))
        self.assertEqual(page.eval_on_selector(".rp-role__summary", "e => getComputedStyle(e).fontSize"), "12.5px")

    def test_real_draft_service_payload_renders(self):
        catalog = InMemoryCanonicalCatalog()
        for row in riley_workspace()["items"][:3]:
            stored = {k: v for k, v in row.items() if k not in ("has_draft", "orphaned", "proposed_values")}
            catalog.put_item(OWNER, stored)
        app.config["RESUME_DRAFT_SERVICE"] = ResumeDraftService(repository=InMemoryResumeDraftRepository(),
                                                                catalog=catalog)
        page = self.open()
        self.assertEqual(page.eval_on_selector_all(".rp-role__org", "els => els.length"), 3)
        self.assertEqual(page.eval_on_selector_all("#resume-page-sections > section", "els => els.map(e => e.id)"),
                         ["rp-experience", "rp-looking-ahead", "rp-constellation-phone"])

    def test_member_text_is_never_interpreted_as_markup(self):
        hostile = '<img src=x onerror="window.__owned=1">Skill'
        self.workspaces[OWNER]["items"].append(item(60, "skill", {"name": hostile, "summary": hostile}))
        page = self.open()
        self.assertIsNone(page.evaluate("window.__owned"))
        self.assertEqual(page.eval_on_selector_all("#resume-page img[src='x']", "els => els.length"), 0)
        self.assertIn(hostile, page.inner_text("#rp-skills"))

    def test_skill_shows_its_resume_line_and_chapter_opens_in_place(self):
        page = self.open()
        page.click("button.rp-skill:has-text('Reliability modelling')")
        self.assertIn("Built the substation outage-risk model.", page.inner_text("#rp-skills-line"))
        self.assertEqual(page.get_attribute("button.rp-skill:has-text('Reliability modelling')", "aria-pressed"), "true")
        self.assertEqual(page.eval_on_selector_all("span.rp-skill--plain", "els => els.length"), 1)
        button = page.locator(".rp-role").first.locator("button.rp-link")
        button.click()
        self.assertEqual(button.get_attribute("aria-expanded"), "true")
        chapter = page.locator("#" + button.get_attribute("aria-controls"))
        self.assertTrue(chapter.is_visible())
        self.assertIn("Cut crane commissioning time by 18% across 6 berths.", chapter.inner_text())
        button.click()
        self.assertFalse(chapter.is_visible())

    # rail_ask_expanded (D1d, Pete: "I actually do want that always expanded")
    RAIL_STATE_JS = """() => { const a = document.getElementById('resume-page-ask-rail'), r = a.getBoundingClientRect();
        const vis = e => !!e && e.getClientRects().length > 0 && getComputedStyle(e).visibility !== 'hidden';
        const art = a.querySelector('.rp-ask__art');
        return {height: Math.round(r.height), title: vis(a.querySelector('.rp-ask__title')) && a.querySelector('.rp-ask__title').textContent,
            hint: vis(a.querySelector('.rp-ask__hint')) && a.querySelector('.rp-ask__hint').textContent,
            chips: [...a.querySelectorAll('[data-rp-ask-q]')].filter(vis).length, box: vis(a.querySelector('textarea')),
            note: vis(a.querySelector('.rp-ask__note')), art: getComputedStyle(art).opacity, artWidth: Math.round(art.getBoundingClientRect().width),
            inert: a.querySelectorAll('[inert]').length, state: a.dataset.state || null}; }"""

    def test_rail_ask_is_always_the_full_panel_at_1440_and_960(self):
        for width in (1440, 960):
            page = self.open(width, 900)
            first = page.evaluate(self.RAIL_STATE_JS)
            self.assertEqual(first["title"], "The person behind the experience.", width)
            self.assertEqual(first["hint"], "Pick a question, or type your own", width)
            self.assertEqual(first["chips"], 3, width)
            self.assertTrue(first["box"] and first["note"], width)
            self.assertEqual(first["art"], "1", width)
            self.assertGreater(first["artWidth"], 80, width)
            self.assertEqual((first["inert"], first["state"]), (0, None), width)
            # Scrolling the main card away changes nothing.
            page.evaluate("document.getElementById('rp-skills').scrollIntoView()")
            page.wait_for_timeout(400)
            self.assertEqual(page.evaluate(self.RAIL_STATE_JS), first, width)
            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(200)
            self.assertEqual(page.evaluate(self.RAIL_STATE_JS), first, width)

    def test_rail_ask_is_expanded_under_reduced_motion_and_in_a_short_window(self):
        page = self.open(1440, 900, reduced=True)
        state = page.evaluate(self.RAIL_STATE_JS)
        self.assertEqual((state["chips"], state["box"], state["art"]), (3, True, "1"))
        durations = page.eval_on_selector_all("#resume-page-ask-rail, #resume-page-ask-rail *",
                                              "els => els.map(e => getComputedStyle(e).transitionDuration)")
        for duration in durations:
            self.assertTrue(all(float(part.strip()[:-1]) < 0.001 for part in duration.split(",")), duration)
        # A rail taller than the window scrolls with the page, so the full Ask is still reachable.
        page = self.open(1440, 560)
        self.assertEqual(page.evaluate(self.RAIL_STATE_JS)["chips"], 3)
        self.assertTrue(page.eval_on_selector("#resume-page-rail", "e => e.classList.contains('is-tall')"))
        page.locator("#resume-page-ask-rail textarea").scroll_into_view_if_needed()
        self.assertTrue(page.evaluate("""() => { const r = document.querySelector('#resume-page-ask-rail textarea').getBoundingClientRect();
            return r.top >= 0 && r.bottom <= innerHeight; }"""))
        page = self.open(959, 900)
        self.assertFalse(page.is_visible("#resume-page-ask-rail"))

    # ask_tabs (D1d): the main card's three tabs at every width
    def tab_state(self, page):
        return page.evaluate("""() => [...document.querySelectorAll('#resume-page-ask-main [role=tab]')].map(t => ({
            name: t.textContent.replace(/\\s+/g, ' ').trim(), selected: t.getAttribute('aria-selected'), tabindex: t.tabIndex,
            panel: !document.getElementById(t.getAttribute('aria-controls')).hidden,
            labelled: document.getElementById(t.getAttribute('aria-controls')).getAttribute('aria-labelledby') === t.id,
            role: document.getElementById(t.getAttribute('aria-controls')).getAttribute('role'),
            h: t.getBoundingClientRect().height, w: t.getBoundingClientRect().width,
            inHeader: !!t.closest('.rp-ask__top'), focused: document.activeElement === t}))""")

    def test_main_ask_has_three_real_tabs_at_every_width(self):
        for width in (1440, 960, 390):
            page = self.open(width, 900)
            tabs = self.tab_state(page)
            self.assertEqual([t["name"] for t in tabs], ["Ask a question", "Career highlights", "Compare a job Soon"], width)
            self.assertEqual([t["selected"] for t in tabs], ["true", "false", "false"], width)
            self.assertEqual([t["tabindex"] for t in tabs], [0, -1, -1], width)
            self.assertEqual([t["panel"] for t in tabs], [True, False, False], width)
            self.assertTrue(all(t["labelled"] and t["role"] == "tabpanel" and t["inHeader"] for t in tabs), width)
            self.assertTrue(all(t["h"] >= 24 and t["w"] >= 24 for t in tabs), width)
            self.assertEqual(page.get_attribute("#resume-page-ask-main [role=tablist]", "aria-labelledby"),
                             "resume-page-ask-main-title")
            # Every tab is on screen inside the card (none hidden off to the side).
            self.assertTrue(page.evaluate("""() => { const card = document.getElementById('resume-page-ask-main').getBoundingClientRect();
                return [...document.querySelectorAll('#resume-page-ask-main [role=tab]')].every(t => {
                    const r = t.getBoundingClientRect(); return r.left >= card.left && r.right <= card.right + 0.5; }); }"""), width)
            self.assertTrue(self.no_sideways_scroll(page), width)
            for name, expected in (("highlights", "The Guide will draft your career highlights from your published resume, for your OK."),
                                   ("job", "Paste a job description to see where your published resume documents a match.")):
                page.click("#resume-page-ask-main-tab-" + name)
                panel = page.locator("#resume-page-ask-main-panel-" + name)
                self.assertTrue(panel.is_visible(), (width, name))
                self.assertIn(expected, panel.inner_text())
                self.assertFalse(page.is_visible("#resume-page-ask-main-panel-ask"), (width, name))
                # The question box and the lock line stay reachable in every tab.
                self.assertTrue(page.is_visible("#resume-page-ask-main-q"), (width, name))
                self.assertTrue(page.is_visible("#resume-page-ask-main .rp-ask__note"), (width, name))
            self.assertIn("Placeholder", page.text_content("#resume-page-ask-main-panel-highlights"))
            self.assertIn("Coming soon", page.inner_text("#resume-page-ask-main-panel-job"))
            # Coming soon offers nothing that pretends to work.
            self.assertEqual(page.eval_on_selector_all("#resume-page-ask-main-panel-job :is(button, a, input, textarea, select)",
                                                       "els => els.length"), 0)
            self.assertEqual(page.eval_on_selector_all("#resume-page-ask-main-panel-highlights :is(button, a, input, textarea, select)",
                                                       "els => els.length"), 0)

    def test_main_ask_tabs_follow_the_keyboard_and_asking_works_from_every_tab(self):
        page = self.open()
        page.focus("#resume-page-ask-main-tab-ask")
        steps = (("ArrowRight", 1), ("ArrowRight", 2), ("ArrowRight", 0), ("ArrowLeft", 2), ("Home", 0), ("End", 2))
        for key_name, expected in steps:
            page.keyboard.press(key_name)
            tabs = self.tab_state(page)
            self.assertEqual([t["selected"] for t in tabs].index("true"), expected, key_name)
            self.assertTrue(tabs[expected]["focused"], key_name)
            self.assertEqual([t["tabindex"] for t in tabs], [0 if i == expected else -1 for i in range(3)], key_name)
            self.assertEqual([t["panel"] for t in tabs], [i == expected for i in range(3)], key_name)
        outline = page.eval_on_selector("#resume-page-ask-main-tab-job", "e => getComputedStyle(e).outlineStyle")
        self.assertEqual(outline, "solid")
        # A question asked from any tab gets the truthful unavailable reply.
        for name in ("ask", "highlights", "job"):
            page.click("#resume-page-ask-main-tab-" + name)
            page.fill("#resume-page-ask-main-q", "A fictional question from the %s tab" % name)
            page.press("#resume-page-ask-main-q", "Enter")
            log = page.locator("#resume-page-ask-main [data-rp-ask-log]")
            log.locator(".rp-turn__ai").wait_for()
            self.assertIn("Ask AI isn\u2019t available right now.", log.inner_text())
            self.assertIn("A fictional question from the %s tab" % name, log.inner_text())
            self.assertTrue(log.is_visible())

    # skill_lines (D1d): up to three resume lines per skill, with the role's employer and dates
    def add_skill_lines(self):
        items = self.workspaces[OWNER]["items"]
        items.append(item(70, "skill", {"name": "Crane safety", "summary": "Wrote the berth lockout procedure."}))
        items.append(item(71, "accomplishment", {"wording": "Crane safety: Wrote the berth lockout procedure.",
                                                 "metric_value": None, "metric_label": None}, parent_key=key(1)))
        items.append(item(72, "accomplishment", {"wording": "Ran the crane safety audit for the substation yards.",
                                                 "metric_value": None, "metric_label": None}, parent_key=key(2)))
        items.append(item(73, "accomplishment", {"wording": "Trained crews on crane safety drills before every shift.",
                                                 "metric_value": None, "metric_label": None}, parent_key=key(3)))
        items.append(item(74, "accomplishment", {"wording": "Shared crane safety notes with the union board.",
                                                 "metric_value": None, "metric_label": None}))

    def skill_panel(self, page, skill):
        page.click("button.rp-skill:has-text('%s')" % skill)
        return page.evaluate("""() => { const scroll = document.querySelector('#rp-skills-line .rp-skills__scroll');
            const inner = scroll.querySelector('.rp-skills__in').getBoundingClientRect(), box = scroll.getBoundingClientRect();
            const pad = parseFloat(getComputedStyle(scroll).paddingTop), padB = parseFloat(getComputedStyle(scroll).paddingBottom);
            const bar = document.querySelector('#rp-skills-line .rp-scrollbar');
            const nested = [...document.querySelectorAll('#rp-skills *')].filter(e => e !== scroll &&
                /auto|scroll/.test(getComputedStyle(e).overflowY) && e.scrollHeight > e.clientHeight + 1).length;
            return {items: [...scroll.querySelectorAll('.rp-skills__item')].map(li => ({
                    text: li.querySelector('.rp-skills__quote').textContent,
                    src: li.querySelector('.rp-skills__src') ? li.querySelector('.rp-skills__src').textContent : null,
                    link: li.querySelector('a.rp-skills__role') ? [li.querySelector('a.rp-skills__role').textContent,
                        li.querySelector('a.rp-skills__role').getAttribute('href')] : null})),
                kicker: scroll.querySelector('.rp-kicker').textContent, label: scroll.getAttribute('aria-label'),
                role: scroll.getAttribute('role'), tabindex: scroll.getAttribute('tabindex'),
                over: scroll.scrollHeight > scroll.clientHeight + 1, client: scroll.clientHeight,
                above: inner.top - (box.top + pad), below: (box.top + scroll.clientHeight - padB) - inner.bottom,
                nativeBar: scroll.offsetWidth - scroll.clientWidth, drawn: !bar.hidden && bar.getBoundingClientRect().height > 0,
                thumb: bar.querySelector('.rp-scrollbar__thumb').getBoundingClientRect().height, nested: nested,
                panelH: document.getElementById('rp-skills-line').getBoundingClientRect().height,
                gridH: document.querySelector('#rp-skills .rp-skills__grid').getBoundingClientRect().height}; }""")

    def test_skill_panel_lists_up_to_three_lines_with_employer_and_dates(self):
        self.add_skill_lines()
        page = self.open()
        panel = self.skill_panel(page, "Crane safety")
        self.assertEqual(panel["kicker"], "Crane safety")
        see = ["See it in the role \u2192", "#rp-experience"]
        self.assertEqual(panel["items"], [
            {"text": "Wrote the berth lockout procedure.",
             "src": "Harbor Light Robotics \u00b7 Controls Engineer \u00b7 Mar 2023 \u2013 Present", "link": see},
            {"text": "Ran the crane safety audit for the substation yards.",
             "src": "Cedar Grid Utilities \u00b7 Reliability Analyst \u00b7 Jun 2020 \u2013 Feb 2023", "link": see},
            {"text": "Trained crews on crane safety drills before every shift.",
             "src": "North Ridge Transit \u00b7 Systems Technician \u00b7 Jan 2018 \u2013 May 2020", "link": see}])
        self.assertNotIn("union board", page.inner_text("#rp-skills"))  # a fourth match is never shown
        self.assertEqual((panel["role"], panel["label"]), ("region", "Resume lines for Crane safety"))
        # A skill line that matches no bullet is still the member's own line, shown without a role.
        # "See it in the role" is a real link: keyboard-reachable, it opens that role's chapter and moves focus there.
        role_link = page.locator("#rp-skills-line a.rp-skills__role").nth(1)
        self.assertEqual(role_link.get_attribute("aria-label"), "See it in the role: Cedar Grid Utilities, Reliability Analyst")
        role_link.focus()
        page.keyboard.press("Enter")
        page.wait_for_function("document.activeElement && document.activeElement.classList.contains('rp-chapter')")
        opened = page.evaluate("""() => { const c = document.activeElement;
            const button = document.querySelector('[aria-controls="' + c.id + '"]');
            return {head: c.querySelector('.rp-chapter__head').textContent, expanded: button.getAttribute('aria-expanded'),
                    visible: c.getClientRects().length > 0}; }""")
        self.assertTrue(opened["head"].startswith("Cedar Grid Utilities"), opened)
        self.assertEqual((opened["expanded"], opened["visible"]), ("true", True))
        panel = self.skill_panel(page, "Reliability modelling")
        self.assertEqual(panel["items"], [{"text": "Built the substation outage-risk model.", "src": None, "link": None}])
        self.assertEqual(page.eval_on_selector_all("span.rp-skill--plain", "els => els.map(e => e.textContent)"), ["Field safety"])
        # The first skill with lines is open when the page loads.
        page = self.open()
        self.assertEqual(page.get_attribute("#rp-skills button.rp-skill", "aria-pressed"), "true")
        self.assertIn("Programs and validates the crane PLC logic.", page.inner_text("#rp-skills-line"))

    def test_skill_lines_are_centred_when_they_fit_and_scroll_when_they_overflow(self):
        self.add_skill_lines()
        long = "Kept the long fictional crane safety log current, " * 6
        self.workspaces[OWNER]["items"].append(item(75, "accomplishment", {"wording": long.strip(), "metric_value": None,
                                                                             "metric_label": None}, parent_key=key(1)))
        self.workspaces[OWNER]["items"].append(item(76, "skill", {"name": "Crane logs", "summary": None}))
        self.workspaces[OWNER]["items"].append(item(77, "accomplishment", {"wording": "Kept the crane logs for 6 berths.",
                                                                             "metric_value": None, "metric_label": None}, parent_key=key(1)))
        for width in (1440, 960):
            page = self.open(width, 900)
            panel = self.skill_panel(page, "Crane logs")
            self.assertEqual(len(panel["items"]), 1, width)
            self.assertFalse(panel["over"], width)
            self.assertLessEqual(abs(panel["above"] - panel["below"]), 2, (width, panel))
            self.assertGreater(panel["above"], 8, width)  # really centred, not top-aligned
            self.assertIsNone(panel["tabindex"], width)
            self.assertFalse(panel["drawn"], width)
            # The panel is as tall as the skill grid (or its 200px floor): the empty space is the panel's own.
            self.assertAlmostEqual(panel["panelH"], max(panel["gridH"], 200), delta=2)
            panel = self.skill_panel(page, "Crane safety")
            self.assertEqual(len(panel["items"]), 3, width)
            self.assertTrue(panel["over"], width)
            self.assertLessEqual(abs(panel["above"]), 1, width)  # overflowing lines start at the top
            self.assertEqual(panel["tabindex"], "0", width)
            self.assertTrue(panel["nativeBar"] > 0 or (panel["drawn"] and panel["thumb"] >= 24), (width, panel))
            self.assertEqual(panel["nested"], 0, width)
            self.assertAlmostEqual(panel["panelH"], max(panel["gridH"], 200), delta=2)
            # Keyboard scrolling works and the drawn thumb follows.
            page.focus("#rp-skills-line .rp-skills__scroll")
            page.keyboard.press("End")
            page.wait_for_function("document.querySelector('#rp-skills-line .rp-skills__scroll').scrollTop > 0")
            if panel["drawn"]:
                page.wait_for_function("document.querySelector('#rp-skills-line .rp-scrollbar__thumb').style.transform !== 'translateY(0px)'")
                # The drawn bar works with the mouse: a click on its track pages, dragging the thumb scrolls.
                page.eval_on_selector("#rp-skills-line .rp-skills__scroll", "e => { e.scrollTop = 0; }")
                box = page.locator("#rp-skills-line .rp-scrollbar").bounding_box()
                page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] - 4)
                page.wait_for_function("document.querySelector('#rp-skills-line .rp-skills__scroll').scrollTop > 0")
                page.eval_on_selector("#rp-skills-line .rp-skills__scroll", "e => { e.scrollTop = 0; }")
                thumb = page.locator("#rp-skills-line .rp-scrollbar__thumb").bounding_box()
                page.mouse.move(thumb["x"] + thumb["width"] / 2, thumb["y"] + 5)
                page.mouse.down()
                page.mouse.move(thumb["x"] + thumb["width"] / 2, thumb["y"] + 45, steps=4)
                page.mouse.up()
                self.assertGreater(page.eval_on_selector("#rp-skills-line .rp-skills__scroll", "e => e.scrollTop"), 0)

    def test_skill_lines_follow_the_generic_rule_in_the_adapter(self):
        page = self.open()
        out = page.evaluate("""() => {
            const role = (k, org, current) => ({record_key: k, record_type: 'role', values: {employer_name: org, role_title: 'Analyst',
                start_date: '2020-01-01', end_date: current ? null : '2021-01-01', date_precision: 'month', current_role: current}});
            const b = (k, parent, wording) => ({record_key: k, record_type: 'accomplishment', parent_key: parent, values: {wording: wording}});
            const m = PeerSlateResumePageModel.fromWorkspace({story_entry_key: null, items: [
                role('r1', 'Example Works', true), role('r2', 'Sample Co', false),
                {record_key: 's1', record_type: 'skill', values: {name: 'Budgeting', summary: null}},
                {record_key: 's2', record_type: 'skill', values: {name: 'Go', summary: null}},
                b('a1', 'r2', 'Mentioned budgeting once.'), b('a2', 'r1', 'Budgeting: Ran the yearly plan.'),
                b('a3', 'r1', 'Wrote the Gopher tool and a Go service.'), b('a4', 'r1', 'Went to the go-live.'),
                b('a5', 'r1', 'Budgetings are not a word.')]}, {displayName: ''});
            return m.sections.skills.map(s => ({name: s.name, lines: s.lines.map(l => [l.text, l.employer, l.dates])})); }""")
        self.assertEqual(out[0], {"name": "Budgeting", "lines": [["Ran the yearly plan.", "Example Works", "Jan 2020 \u2013 Present"],
                                                                 ["Mentioned budgeting once.", "Sample Co", "Jan 2020 \u2013 Jan 2021"]]})
        # Whole phrases only: "Gopher" is not "Go"; a hyphenated "go-live" is.
        self.assertEqual([line[0] for line in out[1]["lines"]], ["Wrote the Gopher tool and a Go service.", "Went to the go-live."])

    def test_skill_line_text_is_never_interpreted_as_markup(self):
        hostile = '<img src=x onerror="window.__owned=1">Crane'
        self.workspaces[OWNER]["items"].append(item(80, "skill", {"name": "Crane", "summary": None}))
        self.workspaces[OWNER]["items"].append(item(81, "accomplishment", {"wording": hostile, "metric_value": None,
                                                                             "metric_label": None}, parent_key=key(1)))
        page = self.open()
        page.click("button.rp-skill:has-text('Crane')")
        self.assertIsNone(page.evaluate("window.__owned"))
        self.assertEqual(page.eval_on_selector_all("#rp-skills img", "els => els.length"), 0)
        self.assertIn(hostile, page.inner_text("#rp-skills-line"))

    # image_guard (D1d re-check F1): one guard for every image source; only a normalised /static/ path is set
    UNSAFE_IMAGE_SOURCES = ["/static/%2e%2e/healthz", "/static/%2E%2E/healthz", "/static/%252e%252e/healthz",
                            "/static/..%2fhealthz", "/static/images%2f..%2f..%2fhealthz", "/static/images\\..\\..\\healthz",
                            "/static/images%5c..%5chealthz", "//example.invalid/static/x.jpg",
                            "https://example.invalid/static/x.jpg", "/static/./images/cinematic/future-path.jpg",
                            "/static//images/cinematic/future-path.jpg", "/static/images/cinematic/future-path.jpg?x=1",
                            "/static/images/cinematic/future-path.jpg#x", "/healthz", "javascript:alert(1)",
                            " /static/images/cinematic/future-path.jpg"]
    GOOD_IMAGE = "/static/images/cinematic/future-path.jpg"
    GOOD_PHONE = "/static/images/cinematic/story-sunset-bg.jpg"

    def open_watching_requests(self, width=1440, height=900):
        page = self.open(width, height)
        requests = []
        page.on("request", lambda request: requests.append(request.url))
        return page, requests

    def test_every_image_source_rejects_traversal_and_foreign_paths(self):
        page, requests = self.open_watching_requests()
        render = """args => { const m = PeerSlateResumePage.state();
            m.lookingAheadPicture = args.ahead; m.person.photo = args.photo; PeerSlateResumePage.render(m);
            const pic = document.querySelector('#rp-looking-ahead .rp-ahead__pic'), hero = document.getElementById('resume-page-hero');
            const heroImg = hero.querySelector('[data-rp-photo] img');
            return {aheadPic: !!pic, aheadText: document.getElementById('rp-looking-ahead').classList.contains('rp-ahead--text'),
                aheadSrc: pic ? pic.querySelector('img').getAttribute('src') : null,
                phone: pic && pic.querySelector('source') ? pic.querySelector('source').getAttribute('srcset') : null,
                heroImg: heroImg ? heroImg.getAttribute('src') : null, heroPhoto: hero.dataset.hasPhoto,
                initials: !!hero.querySelector('[data-rp-photo] .rp-hero__initials')}; }"""
        for bad in self.UNSAFE_IMAGE_SOURCES:
            # A bad main picture or hero photo falls back to text and initials; nothing is requested.
            out = page.evaluate(render, {"ahead": {"src": bad, "phoneSrc": self.GOOD_PHONE, "alt": "x"},
                                         "photo": {"src": bad, "alt": "x"}})
            self.assertEqual((out["aheadPic"], out["aheadText"], out["heroImg"], out["heroPhoto"], out["initials"]),
                             (False, True, None, "false", True), bad)
            # A bad phone variant is dropped; the good main picture still renders from its normalised path.
            out = page.evaluate(render, {"ahead": {"src": self.GOOD_IMAGE, "phoneSrc": bad, "alt": "x"}, "photo": None})
            self.assertEqual((out["aheadPic"], out["aheadSrc"], out["phone"]), (True, self.GOOD_IMAGE, None), bad)
        page.wait_for_timeout(300)
        stray = [url for url in requests if "/static/" not in url or "healthz" in url or "example.invalid" in url]
        self.assertEqual(stray, [])
        # Ordinary approved /static/ images still render, and alt text stays text.
        out = page.evaluate(render, {"ahead": {"src": self.GOOD_IMAGE, "phoneSrc": self.GOOD_PHONE, "alt": '<img src=x onerror="window.__owned=1">'},
                                     "photo": {"src": self.GOOD_PHONE, "alt": "A <b>fictional</b> member"}})
        self.assertEqual((out["aheadSrc"], out["phone"], out["heroImg"], out["heroPhoto"]),
                         (self.GOOD_IMAGE, self.GOOD_PHONE, self.GOOD_PHONE, "true"))
        self.assertEqual(page.eval_on_selector("#resume-page-hero [data-rp-photo] img", "e => e.alt"), "A <b>fictional</b> member")
        self.assertIsNone(page.evaluate("window.__owned"))
        self.assertEqual(page.eval_on_selector("#rp-looking-ahead .rp-ahead__pic img", "e => e.alt"), '<img src=x onerror="window.__owned=1">')
        self.assertEqual(page.eval_on_selector_all("#resume-page img[src='x'], [data-rp-photo] b, .rp-ahead__pic img + *",
                                                   "els => els.length"), 0)

    # looking_ahead_picture (D1d): the member's own picture, or no picture box at all
    def test_looking_ahead_shows_the_members_picture_or_no_box(self):
        page = self.open(1440, 900)
        self.assertEqual(page.eval_on_selector_all("#rp-looking-ahead .rp-ahead__pic", "els => els.length"), 0)
        widths = page.evaluate("""() => { const s = document.getElementById('rp-looking-ahead');
            return [s.getBoundingClientRect().width, s.querySelector('.rp-ahead__text').getBoundingClientRect().width]; }""")
        self.assertAlmostEqual(widths[0] - 2, widths[1], delta=2)  # the text spans the card
        render = """pic => { const m = PeerSlateResumePage.state(); m.lookingAheadPicture = pic; PeerSlateResumePage.render(m); }"""
        page.evaluate(render, {"src": "https://example.invalid/x.jpg", "alt": "remote"})
        self.assertEqual(page.eval_on_selector_all("#rp-looking-ahead .rp-ahead__pic", "els => els.length"), 0)
        picture = {"src": "/static/images/cinematic/future-path.jpg", "phoneSrc": "/static/images/cinematic/story-sunset-bg.jpg",
                   "alt": "A fictional member on a ridge <b>at dawn</b>"}
        page.evaluate(render, picture)
        img = page.locator("#rp-looking-ahead .rp-ahead__pic img")
        img.wait_for()
        page.wait_for_function("document.querySelector('#rp-looking-ahead .rp-ahead__pic img').complete")
        info = page.evaluate("""() => { const i = document.querySelector('#rp-looking-ahead .rp-ahead__pic img');
            const pic = i.closest('.rp-ahead__pic').getBoundingClientRect(), text = document.querySelector('#rp-looking-ahead .rp-ahead__text').getBoundingClientRect();
            return {alt: i.alt, src: i.currentSrc, w: Math.round(pic.width), h: Math.round(pic.height), left: pic.right <= text.left + 1,
                    natural: i.naturalWidth}; }""")
        self.assertEqual(info["alt"], picture["alt"])
        self.assertTrue(info["src"].endswith("/static/images/cinematic/future-path.jpg"), info)
        self.assertTrue(info["left"] and info["w"] > 300 and info["h"] >= 180 and info["natural"] > 0, info)
        self.assertEqual(page.eval_on_selector_all("#rp-looking-ahead b", "els => els.length"), 0)
        self.assertIn("Placeholder", page.text_content("#rp-looking-ahead"))  # the layout is otherwise unchanged
        page = self.open(390, 844)
        page.evaluate(render, picture)
        page.wait_for_function("document.querySelector('#rp-looking-ahead .rp-ahead__pic img').complete")
        src = page.eval_on_selector("#rp-looking-ahead .rp-ahead__pic img", "e => e.currentSrc")
        self.assertTrue(src.endswith("/static/images/cinematic/story-sunset-bg.jpg"), src)
        self.assertTrue(self.no_sideways_scroll(page))

    # truthful_ask
    def test_ask_is_truthfully_unavailable_and_keeps_the_question(self):
        page = self.open()
        page.fill("#resume-page-ask-main-q", "What did Riley build at Harbor Light?")
        page.click("#resume-page-ask-main .rp-ask__go")
        log = page.locator("#resume-page-ask-main [data-rp-ask-log]")
        log.locator(".rp-turn__ai").wait_for()
        self.assertIn("Ask AI isn’t available right now.", log.inner_text())
        self.assertEqual(page.input_value("#resume-page-ask-main-q"), "What did Riley build at Harbor Light?")
        chips = page.eval_on_selector_all("#resume-page-ask-main [data-rp-ask-q]", "els => els.length")
        self.assertEqual(chips, 3)

    def test_thinking_stones_show_only_while_an_answer_is_pending(self):
        page = self.open()
        page.evaluate("""() => { window.__release = null;
            PeerSlateResumePageAsk.setTransport(() => new Promise(resolve => {
                window.__release = () => resolve({state: 'answer', paragraphs: ['<b>Plain</b> text answer.']}); })); }""")
        page.fill("#resume-page-ask-main-q", "Tell me about the crane retrofit")
        page.click("#resume-page-ask-main .rp-ask__go")
        stones = page.locator("#resume-page-ask-main .rp-thinking")
        stones.wait_for()
        self.assertEqual(page.eval_on_selector_all("#resume-page-ask-main .rp-stone", "els => els.length"), 3)
        page.evaluate("window.__release()")
        stones.wait_for(state="detached")
        answer = page.locator("#resume-page-ask-main .rp-turn__ai")
        self.assertEqual(answer.inner_text(), "<b>Plain</b> text answer.")
        self.assertEqual(page.input_value("#resume-page-ask-main-q"), "")

    # constellation_band (D1b: Pete kept the live constellation on the desktop resume)
    def test_desktop_constellation_is_the_live_band_built_from_the_members_own_data(self):
        page = self.open(1440, 900)
        self.assertTrue(page.is_visible("#resume-page-band #rp-constellation"))
        self.assertFalse(page.is_visible("#rp-constellation-phone"))
        band = page.locator("#rp-constellation")
        self.assertIn("See how the work became the story.", band.inner_text())
        nodes = page.eval_on_selector_all("#rp-constellation .rp-band-node", """els => els.map(e => ({
            cls: e.className, x: parseFloat(e.style.getPropertyValue('--node-x')), y: parseFloat(e.style.getPropertyValue('--node-y')),
            title: e.querySelector('strong').textContent}))""")
        titles = [n["title"] for n in nodes]
        self.assertEqual(titles, ["B.S. Mechanical Engineering", "North Ridge Transit", "Cedar Grid Utilities",
                                  "Certified Reliability Engineer", "M.S. Electrical Engineering", "Harbor Light Robotics",
                                  "Ph.D. Systems Engineering"])
        tracks = {n["title"]: n["cls"] for n in nodes}
        self.assertIn("track-pre", tracks["North Ridge Transit"])
        self.assertIn("track-main", tracks["Harbor Light Robotics"])
        self.assertIn("track-branch", tracks["M.S. Electrical Engineering"])
        self.assertIn("is-future", tracks["Ph.D. Systems Engineering"])
        self.assertIn("is-credential", tracks["Certified Reliability Engineer"])
        self.assertTrue(all(0 <= n["x"] <= 100 and 0 <= n["y"] <= 100 for n in nodes))
        # Future plans close the branch, highest on the scene.
        self.assertEqual(max(nodes, key=lambda n: n["x"])["title"], "Ph.D. Systems Engineering")
        harbor = page.locator("#rp-constellation .rp-band-node", has=page.locator("strong", has_text="Harbor Light Robotics"))
        self.assertIn("Cut crane commissioning time by 18% across 6 berths.", harbor.inner_text())
        skills = page.eval_on_selector_all("#rp-constellation .rp-band__skills span", "els => els.map(e => e.textContent)")
        self.assertEqual(skills, ["PLC programming", "Reliability modelling", "Field safety"])
        # Optional story pieces this member has not written are absent, not invented.
        for absent in (".rp-band__evolution", ".rp-band__evidence", ".rp-band__outcomes", ".rp-band__footer"):
            self.assertEqual(page.eval_on_selector_all("#rp-constellation " + absent, "els => els.length"), 0, absent)
        self.assertTrue(self.no_sideways_scroll(page))
        harbor.locator("button.rp-band-node__b").click()
        page.wait_for_function("document.activeElement && document.activeElement.classList.contains('rp-chapter')")

    def test_constellation_band_renders_member_story_pieces_as_text(self):
        page = self.open(1440, 900)
        page.evaluate("""() => { const m = PeerSlateResumePage.state();
            m.careerStory = Object.assign({}, m.careerStory, {intro: 'Intro <b>words</b>',
              evolution: {text: 'From field to fleet.', from: 'Repair', to: 'Reliability'},
              evidence: {title: 'Delivery', metrics: [{value: '6', label: 'Berths'}, {value: '18%', label: 'Faster'}]},
              outcomes: [{value: '6', label: 'Berths'}, {value: '18%', label: 'Faster commissioning'}],
              quote: 'Build it right.', traits: [{icon: 'users', label: 'Leader', detail: 'People first'}]});
            PeerSlateResumePage.render(m); }""")
        band = page.locator("#rp-constellation")
        self.assertIn("Intro <b>words</b>", band.inner_text())
        self.assertEqual(page.eval_on_selector_all("#rp-constellation .rp-band__lead b", "els => els.length"), 0)
        for selector in (".rp-band__evolution", ".rp-band__evidence", ".rp-band__outcomes", ".rp-band__footer"):
            self.assertTrue(page.is_visible("#rp-constellation " + selector), selector)
        self.assertEqual(page.eval_on_selector_all("#rp-constellation .rp-band__outcomes span", "els => els.length"), 2)

    def test_constellation_band_uses_the_live_stacked_form_at_960_and_the_phone_card_below(self):
        page = self.open(1000, 900)
        self.assertTrue(page.is_visible("#rp-constellation"))
        self.assertEqual(page.eval_on_selector(".rp-band__line", "e => getComputedStyle(e).display"), "none")
        self.assertTrue(self.no_sideways_scroll(page))
        page = self.open(390, 844)
        self.assertFalse(page.is_visible("#rp-constellation"))
        self.assertTrue(page.is_visible("#rp-constellation-phone"))
        page.select_option("#resume-page-jump", "constellation")
        page.wait_for_function("document.activeElement && document.activeElement.id === 'rp-constellation-phone'")

    # experience_cards (D1b: "a little more vertical")
    def test_experience_cards_are_portrait_and_compact(self):
        page = self.open(1440, 900)
        boxes = page.eval_on_selector_all(".rp-role", "els => els.map(e => e.getBoundingClientRect()).map(r => [r.width, r.height, r.top])")
        self.assertEqual(len(boxes), 3)
        self.assertEqual(len({round(b[2]) for b in boxes}), 1)  # three across
        for width, height, _ in boxes:
            self.assertGreaterEqual(height, 300)
            self.assertLessEqual(height, 360)
            self.assertGreater(height, width)  # portrait
        clamp = page.eval_on_selector(".rp-role__summary", "e => getComputedStyle(e).webkitLineClamp")
        self.assertEqual(clamp, "4")

    # truthful_read (D1c F1): an unreadable or incomplete read is never shown as an empty resume
    def real_service(self, outage=False):
        catalog = SwitchableCatalog()
        for row in riley_workspace()["items"][:3]:
            catalog.put_item(OWNER, {k: v for k, v in row.items() if k not in ("has_draft", "orphaned", "proposed_values")})
        catalog.outage = outage
        app.config["RESUME_DRAFT_SERVICE"] = ResumeDraftService(repository=InMemoryResumeDraftRepository(), catalog=catalog)
        return catalog

    def open_until(self, state, width=1440, height=900):
        context = self.browser.new_context(viewport={"width": width, "height": height})
        self.addCleanup(context.close)
        page = context.new_page()
        page.goto(self.base + "/app/resume")
        page.wait_for_selector('#resume-page[data-state="%s"]' % state)
        return page

    def test_canonical_outage_on_first_load_is_unavailable_not_empty(self):
        self.real_service(outage=True)
        page = self.open_until("unavailable")
        text = page.inner_text("#resume-page")
        self.assertIn("Your resume can\u2019t be shown right now", text)
        self.assertNotIn("empty", text.lower())
        self.assertEqual(page.eval_on_selector_all("#resume-page-sections .rp-role", "els => els.length"), 0)
        self.assertTrue(page.locator("#resume-page-glance").is_hidden())

    def test_canonical_outage_after_a_good_read_keeps_what_was_shown(self):
        catalog = self.real_service()
        page = self.open()
        self.assertEqual(page.eval_on_selector_all(".rp-role", "els => els.length"), 3)
        catalog.outage = True
        page.evaluate("document.dispatchEvent(new Event('resume-private-draft-changed'))")
        page.wait_for_selector('#resume-page[data-state="stale"]')
        self.assertEqual(page.eval_on_selector_all(".rp-role", "els => els.length"), 3)
        self.assertIn("You\u2019re seeing what was last loaded", page.inner_text("#resume-page-status"))
        self.assertNotIn("empty so far", page.inner_text("#resume-page"))
        catalog.outage = False
        page.evaluate("document.dispatchEvent(new Event('resume-private-draft-changed'))")
        page.wait_for_selector('#resume-page[data-state="ready"]')
        self.assertTrue(page.locator("#resume-page-status").is_hidden())

    def test_malformed_or_incomplete_responses_fail_closed(self):
        # This one test fault-injects the network response; every other journey uses the app's real HTTP.
        context = self.browser.new_context(viewport={"width": 1440, "height": 900})
        self.addCleanup(context.close)
        page = context.new_page()
        page.route("**/api/resume-drafts/me", lambda route: route.fulfill(status=200, content_type="application/json",
                                                                         body="{not json"))
        page.goto(self.base + "/app/resume")
        page.wait_for_selector('#resume-page[data-state="unavailable"]')
        self.assertNotIn("empty", page.inner_text("#resume-page").lower())
        # A readable response that does not say the saved records were fully read is not trusted either.
        self.workspaces[OWNER] = {"draft_version": 0, "items": [], "capabilities": {}}
        page = self.open_until("unavailable")
        self.assertNotIn("empty", page.inner_text("#resume-page").lower())

    # truthful_dates (D1c F2): only the member's own current flag means Present
    def test_present_comes_only_from_an_explicit_current_flag(self):
        page = self.open()
        result = page.evaluate("""() => {
            const base = {role_title: 'Analyst', employer_name: 'Example Works', location_text: null, summary: null,
                start_date: '2018-01-01', end_date: null, date_precision: 'year', employment_type: 'full_time'};
            const cases = {omitted: {}, nullish: {current_role: null}, no: {current_role: false}, yes: {current_role: true}};
            const out = {};
            for (const [name, extra] of Object.entries(cases)) {
                const values = Object.assign({}, base, extra);
                if (name === 'omitted') delete values.current_role;
                const m = PeerSlateResumePageModel.fromWorkspace({story_entry_key: null, items: [
                    {record_key: 'r-' + name, record_type: 'role', values: values},
                    {record_key: 'e1', record_type: 'education', values: {title: 'B.S. Example', institution_name: 'Example U',
                        education_status: 'completed', end_date: '2016-05-01', date_precision: 'month'}},
                    {record_key: 'e2', record_type: 'education', values: {title: 'M.S. Example', institution_name: 'Example U',
                        education_status: 'completed', end_date: '2021-05-01', date_precision: 'month'}}]}, {displayName: 'Sam Example'});
                const job = m.band.find(s => s.kind === 'experience');
                out[name] = {dates: m.sections.experience[0].dates, current: m.sections.experience[0].current,
                    band: job && job.small, headline: m.person.headline,
                    phone: m.constellation.find(s => s.kind === 'job').years};
            }
            return out; }""")
        for name in ("omitted", "nullish", "no"):
            self.assertEqual(result[name], {"dates": "2018", "current": False, "band": "2018", "headline": "",
                                            "phone": "2018"}, name)
        self.assertEqual(result["yes"], {"dates": "2018 \u2013 Present", "current": True, "band": "2018-Present",
                                         "headline": "Analyst", "phone": "2018\u2013now"})
        self.assertNotIn("Present", page.inner_text("#rp-experience .rp-role:nth-child(2)"))

    # fenced_ask (D1c F3): a late result never clears or overwrites newer typing
    def delayed_ask(self, result_js):
        page = self.open()
        page.evaluate("""() => { window.__release = null;
            PeerSlateResumePageAsk.setTransport(() => new Promise(resolve => { window.__release = resolve; })); }""")
        page.fill("#resume-page-ask-main-q", "Original fictional question")
        page.click("#resume-page-ask-main .rp-ask__go")
        page.locator("#resume-page-ask-main .rp-thinking").wait_for()
        page.fill("#resume-page-ask-main-q", "")
        page.type("#resume-page-ask-main-q", "Newer unsent fictional question")
        page.evaluate("result => window.__release(result)", result_js)
        page.locator("#resume-page-ask-main .rp-turn__ai").wait_for()
        return page

    def test_late_answer_keeps_newer_typing(self):
        page = self.delayed_ask({"state": "answer", "paragraphs": ["A fictional answer."]})
        self.assertEqual(page.input_value("#resume-page-ask-main-q"), "Newer unsent fictional question")
        self.assertIn("Original fictional question", page.inner_text("#resume-page-ask-main .rp-turn__me"))

    def test_late_unavailable_keeps_newer_typing(self):
        page = self.delayed_ask({"state": "unavailable"})
        self.assertEqual(page.input_value("#resume-page-ask-main-q"), "Newer unsent fictional question")
        self.assertIn("Ask AI isn\u2019t available right now.", page.inner_text("#resume-page-ask-main"))

    # sweep: certifications, degrees and the unlinked list say only what the data says
    def test_status_labels_follow_the_saved_status_only(self):
        page = self.open()
        out = page.evaluate("""() => {
            const m = PeerSlateResumePageModel.fromWorkspace({story_entry_key: null, items: [
                {record_key: 'c1', record_type: 'credential', values: {name: 'Unspecified Cert', issuer: 'Board'}},
                {record_key: 'c2', record_type: 'credential', values: {name: 'Done Cert', issuer: 'Board', completion_status: 'completed'}},
                {record_key: 'c3', record_type: 'credential', values: {name: 'Working Cert', issuer: 'Board', completion_status: 'in_progress'}},
                {record_key: 'e1', record_type: 'education', values: {title: 'Paused Degree', institution_name: 'U',
                    education_status: 'paused', start_date: '2019-09-01', date_precision: 'month'}},
                {record_key: 'a1', record_type: 'accomplishment', values: {wording: 'Saved highlight.'}}]}, {displayName: ''});
            return {when: m.sections.certifications.map(c => c.when), glance: m.glance.map(r => r.title),
                    empty: m.empty, phone: m.constellation.map(s => s.years)}; }""")
        self.assertEqual(out["when"], ["", "Certified", "In progress"])
        self.assertEqual(out["glance"], ["Done Cert"])
        self.assertFalse(out["empty"])
        self.assertNotIn("not linked", page.inner_text("#resume-page").lower())

    # phone
    def test_phone_layout_folds_below_960(self):
        for width in (390, 320):
            page = self.open(width, 844)
            self.assertFalse(page.is_visible("#resume-page-rail"))
            self.assertTrue(page.is_visible("#resume-page-jump"))
            self.assertTrue(page.is_visible("#resume-page-glance-phone"))
            ask_bottom = page.eval_on_selector("#resume-page-ask-main", "e => e.getBoundingClientRect().bottom")
            glance_top = page.eval_on_selector("#resume-page-glance-phone", "e => e.getBoundingClientRect().top")
            self.assertGreater(glance_top, ask_bottom)
            self.assertTrue(self.no_sideways_scroll(page), width)
        page.select_option("#resume-page-jump", "credentials")
        page.wait_for_function("document.activeElement && document.activeElement.id === 'rp-credentials'")
        page = self.open(959, 900)
        self.assertFalse(page.is_visible("#resume-page-rail"))
        page = self.open(960, 900)
        self.assertTrue(page.is_visible("#resume-page-rail"))
        self.assertFalse(page.is_visible("#resume-page-jump"))

    # left_edge
    def test_live_left_column_edge_matches_the_shared_guide_rule(self):
        for width, expected in ((960, 284), (1280, 288), (1536, 416)):
            page = self.open(width, 900)
            self.assertEqual(page.evaluate("PeerSlateResumePage.leftColumnEdge()"), expected, width)
        page = self.open(959, 900)
        self.assertEqual(page.evaluate("PeerSlateResumePage.leftColumnEdge()"), 0)

    # edit_myself, refresh
    def test_edit_myself_opens_todays_editor_and_saves_refresh_the_page(self):
        page = self.open()
        self.assertFalse(page.is_visible("#resume-editor-lists"))
        page.click("#resume-page-edit")
        self.assertEqual(page.get_attribute("#resume-page-edit", "aria-expanded"), "true")
        page.wait_for_function("document.activeElement && document.activeElement.id === 'resume-editor-title'")
        self.assertTrue(page.is_visible("#resume-editor-lists"))
        self.workspaces[OWNER]["items"].append(item(61, "skill", {"name": "Crane telemetry", "summary": None}))
        page.evaluate("document.dispatchEvent(new Event('resume-private-draft-changed'))")
        page.wait_for_selector("#rp-skills :text('Crane telemetry')")

    # keyboard / a11y
    def test_section_list_moves_focus_and_marks_the_current_section(self):
        page = self.open()
        page.focus("#resume-page-secnav a[data-target='credentials']")
        page.keyboard.press("Enter")
        page.wait_for_function("document.activeElement && document.activeElement.id === 'rp-credentials'")
        self.assertEqual(page.get_attribute("#resume-page-secnav a[data-target='credentials']", "aria-current"), "true")
        small = page.evaluate("""() => [...document.querySelectorAll('#resume-page button, #resume-page a, #resume-page select')]
            .filter(e => e.offsetParent && !e.closest('#resume-page-editor'))
            .map(e => e.getBoundingClientRect()).filter(r => r.width < 24 || r.height < 24).length""")
        self.assertEqual(small, 0)

    # ---------------- D2: Guide hook, Looking Ahead, Projects, highlight tiles ----------------
    def writable_service(self, extra=()):
        """The real draft service over in-memory stores, seeded with Riley's roles plus extra rows."""
        catalog = InMemoryCanonicalCatalog()
        for row in riley_workspace()["items"][:4] + list(extra):
            catalog.put_item(OWNER, {k: v for k, v in row.items() if k not in ("has_draft", "orphaned", "proposed_values")})
        service = ResumeDraftService(repository=InMemoryResumeDraftRepository(), catalog=catalog)
        app.config["RESUME_DRAFT_SERVICE"] = service
        return service

    def watch_posts(self, page):
        posts = []
        page.on("request", lambda r: posts.append((r.url, r.post_data)) if r.method == "POST" else None)
        return posts

    # guide_entry
    def test_continue_with_the_guide_appears_only_with_the_public_hook_and_opens_it(self):
        page = self.open()
        self.assertTrue(page.locator("#resume-page-guide").is_hidden())
        self.assertTrue(page.is_visible("#resume-page-edit"))
        context = self.browser.new_context(viewport={"width": 1440, "height": 900})
        self.addCleanup(context.close)
        context.add_init_script("window.PeerSlateGuidePanel = {calls: 0, open: function () { this.calls += 1; }};")
        page = context.new_page()
        page.goto(self.base + "/app/resume")
        page.wait_for_selector('#resume-page[data-state="ready"]')
        guide = page.locator("#resume-page-guide")
        self.assertTrue(guide.is_visible())
        self.assertEqual(guide.inner_text(), "Continue with the Guide")
        boxes = page.evaluate("""() => ['resume-page-guide', 'resume-page-edit'].map(id => {
            const r = document.getElementById(id).getBoundingClientRect(), f = document.querySelector('.rp-content').getBoundingClientRect();
            return {left: r.left, right: r.right, top: r.top, h: r.height, frameRight: f.right}; })""")
        self.assertLess(boxes[0]["right"], boxes[1]["left"])  # just left of Edit myself, top right of the frame
        self.assertGreater(boxes[1]["right"], boxes[1]["frameRight"] - 40)
        self.assertGreaterEqual(min(boxes[0]["h"], boxes[1]["h"]), 24)
        guide.click()
        self.assertEqual(page.evaluate("window.PeerSlateGuidePanel.calls"), 1)
        self.assertEqual(page.get_attribute("#resume-page-edit", "aria-expanded"), "false")  # the Guide, not the editor
        # The hook going away hides the button instead of leaving a dead control.
        page.evaluate("delete window.PeerSlateGuidePanel")
        guide.click()
        self.assertTrue(guide.is_hidden())
        # Phones (Q8): Edit myself comes first, the Guide button after it in outline style.
        phone = self.browser.new_context(viewport={"width": 390, "height": 844})
        self.addCleanup(phone.close)
        phone.add_init_script("window.PeerSlateGuidePanel = {open: function () {}};")
        page = phone.new_page()
        page.goto(self.base + "/app/resume")
        page.wait_for_selector('#resume-page[data-state="ready"]')
        order = page.evaluate("""() => ['resume-page-edit', 'resume-page-guide'].map(id => document.getElementById(id).getBoundingClientRect().left)""")
        self.assertLess(order[0], order[1])
        self.assertEqual(page.eval_on_selector("#resume-page-guide", "e => getComputedStyle(e).backgroundImage"), "none")

    # looking_ahead
    def test_looking_ahead_is_the_members_own_line_shown_once(self):
        line = "Lead a controls team that keeps every berth moving."
        self.workspaces[OWNER]["items"] += [
            item(70, "knowledge", {"title": "Looking Ahead", "wording": line, "classification": "work"}),
            item(71, "knowledge", {"title": "Looking Ahead", "wording": "A personal note, not the section.", "classification": "personal"})]
        page = self.open()
        section = page.locator("#rp-looking-ahead")
        self.assertEqual(section.locator(".rp-ahead__line").inner_text(), line)
        self.assertEqual(page.evaluate("t => document.body.innerText.split(t).length - 1", line), 1)  # once, not also in the hero
        self.assertNotIn(line, page.inner_text("#resume-page-hero"))
        self.assertEqual(section.locator(".rp-placeholder").count(), 0)
        self.assertNotIn("A personal note", page.inner_text("#resume-page"))
        self.assertEqual(section.locator("button.rp-ahead__edit").inner_text(), "Edit")
        # Without a line the owner keeps the existing placeholder, with a way to write it.
        self.workspaces[OWNER]["items"] = [i for i in self.workspaces[OWNER]["items"] if i["record_key"] != key(70)]
        page = self.open()
        self.assertIn("Your Looking Ahead line goes here", page.inner_text("#rp-looking-ahead"))
        self.assertEqual(page.inner_text("#rp-looking-ahead button.rp-ahead__edit"), "Write your line")

    def test_owner_writes_and_edits_looking_ahead_through_the_private_draft(self):
        service = self.writable_service()
        page = self.open()
        posts = self.watch_posts(page)
        page.click("#rp-looking-ahead button.rp-ahead__edit")
        field = page.locator("#resume-page-ahead-form input[name='wording']")
        field.wait_for()
        self.assertEqual(page.evaluate("document.activeElement.name"), "wording")
        self.assertEqual(field.get_attribute("maxlength"), "120")
        # An empty line is never saved, and nothing is sent.
        page.click("#resume-page-ahead-form button[type='submit']")
        self.assertIn("An empty line isn’t saved", page.inner_text("#resume-page-ahead-form .rp-form__status"))
        self.assertEqual(posts, [])
        field.fill("x" * 130)
        self.assertEqual(len(field.input_value()), 120)  # the browser's own limit, the server's 120
        field.fill("Grow into a controls lead for port automation.")
        page.click("#resume-page-ahead-form button[type='submit']")
        page.wait_for_selector("#rp-looking-ahead .rp-ahead__line")
        self.assertEqual(page.inner_text("#rp-looking-ahead .rp-ahead__line"), "Grow into a controls lead for port automation.")
        self.assertEqual([url.rsplit("/", 2)[-2:] for url, _ in posts], [["me", "commands"]])
        self.assertIn('"create_private_item"', posts[0][1])
        saved = [i for i in service.get_workspace(OWNER)["items"] if i["record_type"] == "knowledge"]
        self.assertEqual([i["values"] for i in saved],
                         [{"title": "Looking Ahead", "wording": "Grow into a controls lead for port automation.", "classification": "work"}])
        self.assertFalse(saved[0]["resume_display"] or saved[0]["visitor_ai"])  # private: nothing is shared or published
        self.assertIn("Nothing was published", page.inner_text("#resume-page-status"))
        # Edit: a private draft save of the same entry.
        page.click("#rp-looking-ahead button.rp-ahead__edit")
        field = page.locator("#resume-page-ahead-form input[name='wording']")
        self.assertEqual(field.input_value(), "Grow into a controls lead for port automation.")
        field.fill("Lead port automation controls.")
        page.click("#resume-page-ahead-form button[type='submit']")
        page.wait_for_function("document.querySelector('#rp-looking-ahead .rp-ahead__line') && document.querySelector('#rp-looking-ahead .rp-ahead__line').textContent === 'Lead port automation controls.'")
        self.assertIn('"save_item"', posts[-1][1])
        saved = [i for i in service.get_workspace(OWNER)["items"] if i["record_type"] == "knowledge"]
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0]["proposed_values"]["wording"], "Lead port automation controls.")
        # Cancel restores the line and focus.
        page.click("#rp-looking-ahead button.rp-ahead__edit")
        page.click("#resume-page-ahead-form .rp-form__cancel")
        self.assertTrue(page.is_visible("#rp-looking-ahead .rp-ahead__line"))
        self.assertEqual(page.evaluate("document.activeElement.textContent"), "Edit")

    def test_a_refused_save_keeps_the_members_words(self):
        from services.resume_draft_service import ResumeDraftUnavailableError

        class Refusing(RecordedWorkspaceService):
            def commit(self, owner, payload):
                raise ResumeDraftUnavailableError()

        app.config["RESUME_DRAFT_SERVICE"] = Refusing(self.workspaces)
        page = self.open()
        page.click("#rp-looking-ahead button.rp-ahead__edit")
        page.fill("#resume-page-ahead-form input[name='wording']", "Keep these words.")
        page.click("#resume-page-ahead-form button[type='submit']")
        page.wait_for_function("document.querySelector('#resume-page-ahead-form .rp-form__status').dataset.kind === 'error'")
        self.assertIn("still here", page.inner_text("#resume-page-ahead-form .rp-form__status"))
        self.assertEqual(page.input_value("#resume-page-ahead-form input[name='wording']"), "Keep these words.")
        # Another save elsewhere never wipes unsaved words on the page.
        page.evaluate("document.dispatchEvent(new Event('resume-private-draft-changed'))")
        page.wait_for_function("document.getElementById('resume-page-status').textContent.indexOf('kept') >= 0")
        self.assertEqual(page.input_value("#resume-page-ahead-form input[name='wording']"), "Keep these words.")

    def test_a_retry_after_an_uncertain_save_is_never_saved_twice(self):
        from services.resume_draft_service import ResumeDraftUnavailableError
        real = self.writable_service()

        class LostReply:
            """The first save commits but its reply is lost (503); later calls are the real service."""
            calls = []

            def get_workspace(self, owner):
                return real.get_workspace(owner)

            def commit(self, owner, payload):
                self.calls.append(copy.deepcopy(payload))
                result = real.commit(owner, payload)
                if len(self.calls) == 1:
                    raise ResumeDraftUnavailableError()
                return result

        service = LostReply()
        app.config["RESUME_DRAFT_SERVICE"] = service
        page = self.open()
        page.click("#rp-looking-ahead button.rp-ahead__edit")
        page.fill("#resume-page-ahead-form input[name='wording']", "Lead port automation controls.")
        page.click("#resume-page-ahead-form button[type='submit']")
        page.wait_for_function("document.querySelector('#resume-page-ahead-form .rp-form__status').dataset.kind === 'error'")
        page.click("#resume-page-ahead-form button[type='submit']")
        page.wait_for_selector("#rp-looking-ahead .rp-ahead__line")
        self.assertEqual(len(service.calls), 2)
        self.assertEqual(service.calls[0]["request_id"], service.calls[1]["request_id"])
        self.assertEqual(service.calls[0]["record_key"], service.calls[1]["record_key"])
        saved = [i for i in real.get_workspace(OWNER)["items"] if i["record_type"] == "knowledge"]
        self.assertEqual(len(saved), 1)

    def test_looking_ahead_is_found_by_its_placement_first_then_by_its_title(self):
        posts = []

        class Recording(RecordedWorkspaceService):
            def commit(self, owner, payload):
                posts.append(copy.deepcopy(payload))
                return {"outcome": "saved"}

        ws = self.workspaces[OWNER]
        ws["items"] += [
            item(72, "knowledge", {"title": "Looking Ahead", "wording": "The title-only line.", "classification": "work"}),
            item(73, "knowledge", {"title": "Where I'm Headed", "wording": "The placed line.", "classification": "work",
                                   "presentation_section": "looking_ahead"}),
            item(74, "knowledge", {"title": "Looking Ahead", "wording": "An award, not the section.", "classification": "work",
                                   "presentation_section": "awards"})]
        app.config["RESUME_DRAFT_SERVICE"] = Recording(self.workspaces)
        page = self.open()
        text = page.inner_text("#resume-page")
        self.assertEqual(page.inner_text("#rp-looking-ahead .rp-ahead__line"), "The placed line.")
        self.assertNotIn("The title-only line.", text)  # never two Looking Ahead lines
        self.assertNotIn("An award, not the section.", page.inner_text("#rp-looking-ahead"))
        # Editing a renamed entry keeps its own title.
        page.click("#rp-looking-ahead button.rp-ahead__edit")
        page.fill("#resume-page-ahead-form input[name='wording']", "The placed line, edited.")
        page.click("#resume-page-ahead-form button[type='submit']")
        page.wait_for_function("!document.getElementById('resume-page-ahead-form')")
        self.assertEqual((posts[0]["record_key"], posts[0]["values"]["title"]), (key(73), "Where I'm Headed"))
        # The label alias counts as placement too; without any placement the title is the fallback.
        ws["items"][-2]["values"]["presentation_section"] = "Looking Ahead"
        self.assertEqual(page.evaluate("ws => PeerSlateResumePageModel.fromWorkspace(ws, {}).lookingAhead", ws), "The placed line.")
        ws["items"] = [i for i in ws["items"] if i["record_key"] != key(73)]
        self.assertEqual(page.evaluate("ws => PeerSlateResumePageModel.fromWorkspace(ws, {}).lookingAhead", ws), "The title-only line.")

    # D2 re-check F1 (reviewer guide-build): the draft version is state, not a render side effect
    def open_project_edit_with_looking_ahead(self):
        service = self.writable_service([self.project(81), item(83, "knowledge", {
            "title": "Looking Ahead", "wording": "Grow into a controls lead.", "classification": "work"})])
        page = self.open()
        posts = self.watch_posts(page)
        page.click("#rp-projects .rp-project__edit")
        edit = page.locator("#rp-projects form")
        edit.locator("input[name='summary']").fill("Live sensor feed for eight harbor cranes.")
        return service, page, posts, edit

    def save_project_and_check(self, service, page, posts, edit):
        edit.locator("button[type='submit']").click()
        page.wait_for_function("!document.querySelector('#rp-projects form')")
        page.wait_for_function("document.querySelector('#rp-projects .rp-project__line').textContent.indexOf('eight') >= 0")
        project = [i for i in service.get_workspace(OWNER)["items"] if i["record_type"] == "project"][0]
        self.assertEqual(project["proposed_values"]["summary"], "Live sensor feed for eight harbor cranes.")
        ids = [__import__("json").loads(body)["request_id"] for _, body in posts]
        self.assertEqual(len(ids), len(set(ids)))  # never a reused request id across distinct commands
        return project

    def test_a_second_page_form_saves_after_another_page_form_saved(self):
        service, page, posts, edit = self.open_project_edit_with_looking_ahead()
        page.click("#rp-looking-ahead button.rp-ahead__edit")
        page.fill("#resume-page-ahead-form input[name='wording']", "Lead port automation controls.")
        page.click("#resume-page-ahead-form button[type='submit']")
        page.wait_for_function("document.querySelector('#rp-looking-ahead .rp-ahead__line') && "
                               "document.querySelector('#rp-looking-ahead .rp-ahead__line').textContent === 'Lead port automation controls.'")
        # The section that saved shows its new line and its Edit button; the other form keeps its words.
        self.assertTrue(page.is_visible("#rp-looking-ahead button.rp-ahead__edit"))
        self.assertEqual(edit.locator("input[name='summary']").input_value(), "Live sensor feed for eight harbor cranes.")
        self.save_project_and_check(service, page, posts, edit)
        self.assertEqual(len(posts), 2)  # one save each, no 409 loop

    def test_a_page_form_saves_after_todays_editor_saved_meanwhile(self):
        service, page, posts, edit = self.open_project_edit_with_looking_ahead()
        page.click("#resume-page-edit")
        page.wait_for_selector("#resume-editor-lists .resume-editor__records")
        # Today's editor saves a skill (its own send + event), while the project form stays open.
        page.evaluate("""async () => { const r = await fetch('/api/resume-drafts/me/commands', {method: 'POST',
            credentials: 'same-origin', headers: {'Content-Type': 'application/json', 'X-PeerSlate-Request': 'same-origin'},
            body: JSON.stringify({type: 'create_private_item', request_id: crypto.randomUUID(), record_key: crypto.randomUUID(),
                record_type: 'skill', values: {name: 'Crane telemetry', summary: null}})});
            document.dispatchEvent(new Event('resume-private-draft-changed')); return r.status; }""")
        page.wait_for_selector("#rp-skills :text('Crane telemetry')")
        self.assertEqual(edit.locator("input[name='summary']").input_value(), "Live sensor feed for eight harbor cranes.")
        posts.clear()
        self.save_project_and_check(service, page, posts, edit)
        self.assertEqual(len(posts), 1)

    def test_a_page_form_saves_after_a_save_it_never_heard_about(self):
        # A Guide (or another tab) save with no event: the first save gets 409, the page re-reads and
        # retries once with a fresh request id and the new version, for the same words.
        service, page, posts, edit = self.open_project_edit_with_looking_ahead()
        service.commit(OWNER, {"type": "create_private_item", "request_id": key(990), "record_key": key(991),
                               "record_type": "skill", "values": {"name": "Crane telemetry", "summary": None}})
        la = next(i for i in service.get_workspace(OWNER)["items"] if i["record_key"] == key(83))
        ws = service.get_workspace(OWNER)
        service.commit(OWNER, {"type": "save_item", "request_id": key(992), "record_key": key(83), "record_type": "knowledge",
                               "values": {"wording": "Lead port automation."}, "expected_draft_version": ws["draft_version"],
                               "expected_content_token": la["content_token"], "expected_access_revision": la["access_revision"]})
        self.save_project_and_check(service, page, posts, edit)
        self.assertEqual(len(posts), 2)  # the refused save and exactly one retry
        self.assertIn("Lead port automation.", page.inner_text("#rp-looking-ahead"))  # the re-read shows the other save

    def test_an_edit_of_the_same_item_elsewhere_stays_an_honest_conflict(self):
        service, page, posts, edit = self.open_project_edit_with_looking_ahead()
        project = next(i for i in service.get_workspace(OWNER)["items"] if i["record_type"] == "project")
        ws = service.get_workspace(OWNER)
        service.commit(OWNER, {"type": "save_item", "request_id": key(993), "record_key": project["record_key"],
                               "record_type": "project", "values": {"summary": "Changed in another tab."},
                               "expected_draft_version": ws["draft_version"], "expected_content_token": project["content_token"],
                               "expected_access_revision": project["access_revision"]})
        for _ in range(2):
            edit.locator("button[type='submit']").click()
            page.wait_for_function("document.querySelector('#rp-projects form .rp-form__status').dataset.kind === 'error'")
            self.assertIn("still here", edit.locator(".rp-form__status").inner_text())
            self.assertEqual(edit.locator("input[name='summary']").input_value(), "Live sensor feed for eight harbor cranes.")
            page.evaluate("document.querySelector('#rp-projects form .rp-form__status').dataset.kind = ''")
        stored = next(i for i in service.get_workspace(OWNER)["items"] if i["record_type"] == "project")
        self.assertEqual(stored["proposed_values"]["summary"], "Changed in another tab.")  # never overwritten
        self.assertLessEqual(len(posts), 4)  # at most one retry per click, never a loop

    def test_saved_notice_never_outlives_a_failed_reload(self):
        from services.resume_draft_service import ResumeDraftUnavailableError
        real = self.writable_service()

        class ReadFailsOnceAfterSave:
            failing = False

            def get_workspace(self, owner):
                if self.failing:
                    self.failing = False
                    raise ResumeDraftUnavailableError()
                return real.get_workspace(owner)

            def commit(self, owner, payload):
                result = real.commit(owner, payload)
                self.failing = True
                return result

        app.config["RESUME_DRAFT_SERVICE"] = ReadFailsOnceAfterSave()
        page = self.open()
        page.click("#rp-looking-ahead button.rp-ahead__edit")
        page.fill("#resume-page-ahead-form input[name='wording']", "Lead port automation controls.")
        page.click("#resume-page-ahead-form button[type='submit']")
        page.wait_for_function("document.getElementById('resume-page').dataset.state === 'stale'")
        page.evaluate("PeerSlateResumePage.reload()")
        page.wait_for_function("document.getElementById('resume-page').dataset.state === 'ready'")
        self.assertNotIn("Saved privately", page.inner_text("#resume-page-status"))

    # projects
    def project(self, n, **values):
        base = {"project_name": "Crane telemetry retrofit", "summary": "Live sensor feed for six harbor cranes."}
        base.update(values)
        return item(n, "project", base)

    def test_projects_show_only_once_added_with_their_fields_and_safe_links(self):
        page = self.open()
        self.assertEqual(page.locator("#rp-projects").count(), 0)
        self.assertNotIn("Projects", page.eval_on_selector_all("#resume-page-secnav a", "els => els.map(e => e.textContent)"))
        self.workspaces[OWNER]["items"] += [
            self.project(80, project_category="software", organization_name="Harbor Light Robotics",
                         start_date="2023-01-01", end_date="2024-01-01", date_precision="year",
                         project_url="https://github.com/riley/crane-telemetry",
                         additional_project_urls=["https://www.riley-builds.example/cranes", "https://docs.example.org/x",
                                                  "https://fourth.example.org/never"]),
            self.project(81, project_name="Signal cabinet audit", summary="Checklist every crew still uses.",
                         project_url="javascript:alert(1)", additional_project_urls=["http://plain.example.com"])]
        page, requests = self.open_watching_requests()
        ids = page.eval_on_selector_all("#resume-page-sections > section", "els => els.map(e => e.id)")
        self.assertEqual(ids.index("rp-projects"), ids.index("rp-experience") + 1)
        self.assertIn("Projects", page.eval_on_selector_all("#resume-page-secnav a", "els => els.map(e => e.textContent)"))
        first = page.locator("#rp-projects .rp-project").nth(0)
        self.assertEqual(first.locator(".rp-project__name").inner_text(), "Crane telemetry retrofit")
        self.assertEqual(first.locator(".rp-project__cat").inner_text(), "Software")
        self.assertEqual(first.locator(".rp-project__line").inner_text(), "Live sensor feed for six harbor cranes.")
        self.assertEqual(first.locator(".rp-project__meta").inner_text(), "Harbor Light Robotics · 2023 – 2024")
        links = first.locator(".rp-project__links a")
        self.assertEqual(links.evaluate_all("els => els.map(e => [e.textContent, e.getAttribute('href'), e.target, e.rel])"),
                         [["GitHub", "https://github.com/riley/crane-telemetry", "_blank", "noopener noreferrer"],
                          ["riley-builds.example", "https://www.riley-builds.example/cranes", "_blank", "noopener noreferrer"],
                          ["docs.example.org", "https://docs.example.org/x", "_blank", "noopener noreferrer"]])
        second = page.locator("#rp-projects .rp-project").nth(1)
        self.assertEqual(second.locator(".rp-project__links a").count(), 0)  # only https:// links, never javascript: or http:
        self.assertEqual(second.locator(".rp-project__cat").count(), 0)  # category is optional
        page.wait_for_timeout(300)
        self.assertEqual([u for u in requests if "example" in u or "github" in u], [])  # links are never fetched
        self.assertTrue(self.no_sideways_scroll(page))

    def test_owner_adds_and_edits_a_project_through_the_private_draft(self):
        service = self.writable_service()
        page = self.open()
        posts = self.watch_posts(page)
        self.assertTrue(page.locator("#resume-page-add-project").is_hidden())
        page.click("#resume-page-edit")
        page.click("#resume-page-add-project button:has-text('Add a project')")
        form = page.locator("#resume-page-project-new")
        form.wait_for()
        labels = form.locator("label, legend").evaluate_all("els => els.map(e => e.textContent)")
        self.assertEqual(labels, ["Project name", "CategoryOptional", "Description, in one line", "OrganizationOptional",
                                  "DatesOptional", "Links: GitHub, a websiteOptional"])
        self.assertEqual(form.locator("input[type='url']:visible").count(), 1)
        form.locator("button[type='submit']").click()
        self.assertIn("project name and a one-line description", form.locator(".rp-form__status").inner_text())
        form.locator("input[name='project_name']").fill("Crane telemetry retrofit")
        form.locator("input[name='summary']").fill("Live sensor feed for six harbor cranes.")
        form.locator("select[name='project_category']").select_option("software")
        form.locator("input[name='dates']").fill("2023 – 2024")
        form.locator("input[name='link_0']").fill("http://insecure.example.com")
        form.locator("button[type='submit']").click()
        self.assertIn("https://", form.locator(".rp-form__status").inner_text())
        self.assertEqual(posts, [])
        form.locator("input[name='link_0']").fill("https://github.com/riley/crane-telemetry")
        self.assertEqual(form.locator("input[type='url']:visible").count(), 2)  # the next box appears, up to three
        form.locator("button[type='submit']").click()
        page.wait_for_selector("#rp-projects .rp-project")
        self.assertEqual(len(posts), 1)
        saved = [i for i in service.get_workspace(OWNER)["items"] if i["record_type"] == "project"]
        self.assertEqual(saved[0]["values"]["project_name"], "Crane telemetry retrofit")
        self.assertEqual(saved[0]["values"]["project_category"], "software")
        self.assertEqual((saved[0]["values"]["start_date"], saved[0]["values"]["end_date"], saved[0]["values"]["date_precision"]),
                         ("2023-01-01", "2024-01-01", "year"))
        self.assertEqual(saved[0]["values"]["project_url"], "https://github.com/riley/crane-telemetry")
        self.assertFalse(saved[0]["resume_display"] or saved[0]["visitor_ai"])
        # Edit in place through save_item; the server's one-line rule still applies.
        page.click("#rp-projects .rp-project__edit")
        edit = page.locator("#rp-projects form")
        self.assertEqual(edit.locator("input[name='dates']").input_value(), "2023 – 2024")
        edit.locator("input[name='summary']").fill("Live sensor feed for eight harbor cranes.")
        edit.locator("button[type='submit']").click()
        page.wait_for_function("document.querySelector('#rp-projects .rp-project__line') && document.querySelector('#rp-projects .rp-project__line').textContent.indexOf('eight') >= 0")
        self.assertIn('"save_item"', posts[-1][1])
        saved = [i for i in service.get_workspace(OWNER)["items"] if i["record_type"] == "project"]
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0]["proposed_values"]["summary"], "Live sensor feed for eight harbor cranes.")
        # A server refusal (mixed date detail is caught here; a bad summary by the server) keeps the words.
        page.click("#rp-projects .rp-project__edit")
        edit = page.locator("#rp-projects form")
        edit.locator("input[name='dates']").fill("2023 – 2024-05")
        edit.locator("button[type='submit']").click()
        self.assertIn("same detail", edit.locator(".rp-form__status").inner_text())
        self.assertEqual(edit.locator("input[name='dates']").input_value(), "2023 – 2024-05")

    def test_editing_a_project_never_rewrites_its_untouched_dates(self):
        stored = self.project(82, start_date="2022-03-14", end_date="2022-09-30", date_precision="day")
        service = self.writable_service([stored])
        page = self.open()
        page.click("#rp-projects .rp-project__edit")
        edit = page.locator("#rp-projects form")
        edit.locator("input[name='summary']").fill("Live sensor feed for seven harbor cranes.")
        edit.locator("button[type='submit']").click()
        page.wait_for_function("document.querySelector('#rp-projects .rp-project__line').textContent.indexOf('seven') >= 0")
        saved = [i for i in service.get_workspace(OWNER)["items"] if i["record_type"] == "project"][0]
        merged = {**saved["values"], **(saved["proposed_values"] or {})}
        self.assertEqual((merged["start_date"], merged["end_date"], merged["date_precision"]), ("2022-03-14", "2022-09-30", "day"))

    # moved items (B3b "Move to", added to D2 by the manager)
    @staticmethod
    def moved(row, destination_type, values, parent=None, **descriptor):
        """A draft row exactly as B3b's private workspace presents a confirmed move (candidate 48ca8780)."""
        row = copy.deepcopy(row)
        conversion = {"state": "confirmed_private", "base_record_type": row["record_type"],
                      "destination_record_type": destination_type, "destination_parent_ref": parent,
                      "base_content_token": row["content_token"], "base_access_revision": row["access_revision"],
                      "conversion_op_ref": "op-" + row["record_key"][:8]}
        conversion.update(descriptor)
        row.update(has_draft=True, proposed_values={}, conversion=conversion,
                   conversion_destination={"record_type": destination_type, "values": values, "parent_key": parent})
        return row

    def test_a_confirmed_move_shows_the_item_in_its_new_place_and_type(self):
        ws = self.workspaces[OWNER]
        rows = {row["record_key"]: row for row in ws["items"]}
        # Skill "Reliability modelling" moved to a bullet of the Cedar Grid role; skill "PLC programming" moved to a Project.
        ws["items"] = [r for r in ws["items"] if r["record_key"] not in (key(21), key(20))] + [
            self.moved(rows[key(21)], "accomplishment",
                       {"wording": "Built the substation outage-risk model.", "metric_value": None, "metric_label": None},
                       parent=key(2)),
            self.moved(rows[key(20)], "project", {"project_name": "Crane PLC validation",
                                                  "summary": "Programs and validates the crane PLC logic."})]
        page = self.open()
        skills = page.eval_on_selector_all("#rp-skills .rp-skill", "els => els.map(e => e.textContent)")
        self.assertNotIn("Reliability modelling", skills)
        self.assertNotIn("PLC programming", skills)
        self.assertIn("Field safety", skills)
        cedar = page.locator(".rp-role", has_text="Cedar Grid Utilities")
        cedar.locator("button.rp-link").click()
        chapter = page.locator("#" + cedar.locator("button.rp-link").get_attribute("aria-controls"))
        self.assertIn("Built the substation outage-risk model.", chapter.inner_text())
        self.assertEqual(page.inner_text("#rp-projects .rp-project__name"), "Crane PLC validation")
        self.assertIn("Projects", page.eval_on_selector_all("#resume-page-secnav a", "els => els.map(e => e.textContent)"))
        # A malformed or unconfirmed descriptor never shows the row in its old (or any) place.
        for bad in ({"state": "staged"}, {"destination_record_type": "skill"}, {"extra": True}):
            ws["items"][-1] = self.moved(rows[key(20)], "project", {"project_name": "Crane PLC validation",
                                                                     "summary": "Programs and validates the crane PLC logic."}, **bad)
            page.evaluate("document.dispatchEvent(new Event('resume-private-draft-changed'))")
            page.wait_for_function("!document.getElementById('rp-projects')")
            self.assertNotIn("PLC programming", page.inner_text("#rp-skills"), bad)

    def test_editing_a_moved_project_saves_as_its_destination_type(self):
        posts = []

        class Recording(RecordedWorkspaceService):
            def commit(self, owner, payload):
                posts.append(copy.deepcopy(payload))
                return {"outcome": "saved"}

        ws = self.workspaces[OWNER]
        row = next(r for r in ws["items"] if r["record_key"] == key(20))
        ws["items"].remove(row)
        ws["items"].append(self.moved(row, "project", {"project_name": "Crane PLC validation", "summary": "One line."}))
        app.config["RESUME_DRAFT_SERVICE"] = Recording(self.workspaces)
        page = self.open()
        page.click("#rp-projects .rp-project__edit")
        page.fill("#rp-projects form input[name='summary']", "Validated crane PLC logic.")
        page.click("#rp-projects form button[type='submit']")
        page.wait_for_function("document.querySelectorAll('#rp-projects form').length === 0")
        self.assertEqual(len(posts), 1)
        self.assertEqual((posts[0]["type"], posts[0]["record_key"], posts[0]["record_type"]), ("save_item", key(20), "project"))
        self.assertEqual(posts[0]["values"]["summary"], "Validated crane PLC logic.")
        self.assertEqual(posts[0]["expected_content_token"], row["content_token"])

    # highlight_tiles
    def tiles(self, page):
        return page.eval_on_selector_all("#resume-page-hero [data-rp-highlights] .rp-hl", """els => els.map(e => ({
            tag: e.tagName, value: e.querySelector('strong').textContent, label: e.querySelector('.rp-hl__label').textContent,
            waiting: e.classList.contains('rp-hl--waiting'), note: e.querySelector('.rp-hl__tag') ? e.querySelector('.rp-hl__tag').textContent : null}))""")

    def bullet(self, n, wording, value, label, parent=1):
        return item(n, "accomplishment", {"wording": wording, "metric_value": value, "metric_label": label},
                    **({"parent_key": key(parent)} if parent else {}))

    def test_highlight_tiles_are_saved_bullets_resolved_by_reference(self):
        ws = self.workspaces[OWNER]
        ws["items"] += [self.bullet(90, "Cut crane commissioning time by 18%.", "18%", "faster crane commissioning"),
                        self.bullet(91, "Kept 6 berths online through the retrofit.", "6", "berths kept online", parent=2),
                        self.bullet(92, "Wrote the cabinet checklist.", None, None),
                        self.bullet(93, "Led 4 technicians.", "4", "technicians led", parent=None),
                        self.bullet(94, "Saved $1.2M in downtime.", "$1.2M", None),
                        self.bullet(95, "Trained 12 operators.", "12", "operators trained")]
        # Duplicates, missing, number-less and role-less refs never make a tile; at most four show.
        ws["highlight_refs"] = [key(90), key(90), key(99), key(92), key(93), key(91), key(94), key(95)]
        ws["highlight_refs_manual"] = True
        page = self.open()
        tiles = self.tiles(page)
        self.assertEqual([(t["value"], t["label"]) for t in tiles],
                         [("18%", "faster crane commissioning"), ("6", "berths kept online"),
                          ("$1.2M", "Saved $1.2M in downtime."), ("12", "operators trained")])
        self.assertTrue(all(t["tag"] == "BUTTON" and not t["waiting"] for t in tiles))
        page.locator("#resume-page-hero .rp-hl").nth(1).click()
        page.wait_for_function("document.querySelectorAll('.rp-role.is-open').length === 1")
        self.assertIn("Cedar Grid Utilities", page.inner_text(".rp-role.is-open"))
        # A reference follows the saved bullet: a new number shows, a cleared number drops the tile.
        bullets = {i["record_key"]: i for i in ws["items"]}
        bullets[key(90)]["values"]["metric_value"] = "21%"
        bullets[key(95)]["values"]["metric_value"] = None
        page.evaluate("document.dispatchEvent(new Event('resume-private-draft-changed'))")
        page.wait_for_function("document.querySelector('#resume-page-hero .rp-hl strong').textContent === '21%'")
        self.assertEqual([t["value"] for t in self.tiles(page)], ["21%", "6", "$1.2M"])
        self.assertEqual(page.eval_on_selector("[data-rp-highlights]", "e => getComputedStyle(e).gridTemplateColumns.split(' ').length"), 3)
        # Fewer than two tiles: no row at all (2 to 4, never one alone).
        ws["highlight_refs"] = [key(90)]
        page.evaluate("document.dispatchEvent(new Event('resume-private-draft-changed'))")
        page.wait_for_function("document.querySelector('[data-rp-highlights]').hidden")
        self.assertEqual(self.tiles(page), [])

    def test_suggested_tiles_wait_for_the_members_ok(self):
        page = self.open()
        page.evaluate("""() => { const m = PeerSlateResumePage.state(); const role = m.sections.experience[0].key;
            m.highlights = [{value: '18%', label: 'faster crane commissioning', role: role, state: 'saved'},
                            {value: '6', label: 'berths kept online', role: role, state: 'suggested'}];
            PeerSlateResumePage.render(m); }""")
        tiles = self.tiles(page)
        self.assertEqual([(t["tag"], t["waiting"], t["note"]) for t in tiles],
                         [("BUTTON", False, None), ("DIV", True, "Suggested by the Guide · waiting for your OK")])
        waiting = page.locator(".rp-hl--waiting")
        self.assertEqual(waiting.locator("em").count(), 0)  # no "See the role": it isn't saved
        self.assertEqual(waiting.evaluate("e => getComputedStyle(e).borderTopStyle"), "dashed")
        # The workspace adapter itself never invents a suggestion.
        model = page.evaluate("""() => PeerSlateResumePageModel.fromWorkspace({items: [], highlight_refs: []}, {}).highlights""")
        self.assertEqual(model, [])

    def test_empty_resume_shows_one_honest_empty_state(self):
        self.workspaces[OWNER] = {"draft_version": 0, "items": [], "capabilities": {"canonical_read": "ok"}}
        page = self.open()
        self.assertIn("Your resume is empty so far", page.inner_text("#resume-page-sections"))
        self.assertTrue(page.locator("#resume-page-glance").is_hidden())
        self.assertEqual(page.eval_on_selector_all("#resume-page-secnav a", "els => els.length"), 1)


if __name__ == "__main__":
    unittest.main()
