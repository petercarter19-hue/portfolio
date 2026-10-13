"""Owner resume page (PS-RESUME-PAGE-OWNER-001, D1): real browser journeys.

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

    # rail_ask_grow
    def test_rail_ask_grows_smoothly_when_the_main_card_scrolls_away(self):
        page = self.open(1440, 900)
        rail = page.locator("#resume-page-ask-rail")
        self.assertEqual(rail.get_attribute("data-state"), "compact")
        self.assertTrue(page.evaluate("document.querySelector('#resume-page-ask-rail [data-rp-ask-more]').inert"))
        duration = page.eval_on_selector("#resume-page-ask-rail .rp-ask__more", "e => getComputedStyle(e).transitionDuration")
        self.assertNotEqual(duration.split(",")[0].strip(), "0s")
        page.evaluate("document.getElementById('rp-skills').scrollIntoView()")
        page.wait_for_function("document.getElementById('resume-page-ask-rail').dataset.state === 'grown'")
        self.assertFalse(page.evaluate("document.querySelector('#resume-page-ask-rail [data-rp-ask-more]').inert"))
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_function("document.getElementById('resume-page-ask-rail').dataset.state === 'compact'")

    def test_rail_ask_change_is_instant_with_reduced_motion(self):
        page = self.open(1440, 900, reduced=True)
        duration = page.eval_on_selector("#resume-page-ask-rail .rp-ask__more", "e => getComputedStyle(e).transitionDuration")
        # The site's own reduced-motion rule may leave a 0.01ms duration; anything under 1ms is instant.
        seconds = [float(part.strip()[:-1]) for part in duration.split(",")]
        self.assertTrue(all(value < 0.001 for value in seconds), duration)
        page.evaluate("document.getElementById('rp-skills').scrollIntoView()")
        page.wait_for_function("document.getElementById('resume-page-ask-rail').dataset.state === 'grown'")

    def test_rail_ask_stays_compact_when_the_window_is_too_short(self):
        page = self.open(1440, 560)
        page.evaluate("document.getElementById('rp-credentials').scrollIntoView()")
        page.wait_for_timeout(300)
        self.assertEqual(page.get_attribute("#resume-page-ask-rail", "data-state"), "compact")

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

    def test_empty_resume_shows_one_honest_empty_state(self):
        self.workspaces[OWNER] = {"draft_version": 0, "items": [], "capabilities": {"canonical_read": "ok"}}
        page = self.open()
        self.assertIn("Your resume is empty so far", page.inner_text("#resume-page-sections"))
        self.assertTrue(page.locator("#resume-page-glance").is_hidden())
        self.assertEqual(page.eval_on_selector_all("#resume-page-secnav a", "els => els.length"), 1)


if __name__ == "__main__":
    unittest.main()
