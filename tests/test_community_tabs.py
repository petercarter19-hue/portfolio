"""PS-COMMUNITY-TABS-001 — Community tab shell (Feed / The Break / Saved).

Owner decision, 2026-07-21: the People & Interests board retires as the
/the-slate landing in favor of the LIVE Interview Studio tab pattern — every
panel's full markup renders in one response and static/js/community-tabs.js
swaps which one is visible with no page reload. These tests pin: the three
real routes and the retired board's redirect, correct initial-tab state
(hidden attributes + ARIA) per route, valid unique tab-semantics markup,
honest sample-data labeling, the Saved tab's fixture content, and that The
Break's own accepted content is unchanged and reachable inside the shell.
"""

import os
import re
import unittest

from app import app


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class CommunityTabRouteTests(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_all_three_tab_routes_are_public(self):
        for path in ("/the-slate", "/the-slate/break", "/the-slate/saved"):
            with self.subTest(path=path):
                response = self.client.get(path, base_url="https://peerslate.com")
                self.assertEqual(response.status_code, 200)

    def test_retired_board_address_still_redirects(self):
        response = self.client.get("/the-slate/people-interests")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/the-slate"))

    def test_untouched_neighboring_slate_routes_still_work(self):
        for path in ("/the-slate/my-slate", "/the-slate/daily", "/the-slate/pulse"):
            response = self.client.get(path, base_url="http://localhost")
            self.assertEqual(response.status_code, 200, path)

    def test_sitemap_includes_the_new_saved_tab_url(self):
        response = self.client.get("/sitemap.xml", base_url="https://peerslate.com")
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("https://peerslate.com/the-slate/saved", body)
        self.assertIn("https://peerslate.com/the-slate/break", body)


class CommunityTabInitialStateTests(unittest.TestCase):
    """Each route answers with all three panels present (seamless-switch
    requires every panel's markup up front) but only its own panel visible
    and selected — matching the exact mechanism interview_studio.html uses
    for its mode panels (server-computed initial `hidden`/`aria-selected`,
    then JavaScript takes over)."""

    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def _get(self, path):
        return self.client.get(path).get_data(as_text=True)

    def test_feed_route_starts_on_the_feed_panel(self):
        html = self._get("/the-slate")
        self.assertRegex(html, r'id="mainInner"[^>]*data-tab-panel="feed"(?![^>]*hidden)[^>]*>')
        self.assertRegex(html, r'id="panel-break"[^>]*hidden')
        self.assertRegex(html, r'id="panel-saved"[^>]*hidden')
        self.assertIn('id="tab-feed"', html)
        self.assertIn('aria-selected="true"', html)
        # The active tab is the Feed one specifically.
        feed_tab = re.search(r'<a[^>]*id="tab-feed"[^>]*>', html).group(0)
        self.assertIn('aria-selected="true"', feed_tab)
        break_tab = re.search(r'<a[^>]*id="tab-break"[^>]*>', html).group(0)
        self.assertIn('aria-selected="false"', break_tab)

    def test_break_route_starts_on_the_break_panel(self):
        html = self._get("/the-slate/break")
        self.assertRegex(html, r'id="mainInner"[^>]*data-tab-panel="feed"[^>]*hidden')
        self.assertRegex(html, r'id="panel-break"[^>]*data-tab-panel="break"(?![^>]*hidden)')
        self.assertRegex(html, r'id="panel-saved"[^>]*hidden')
        break_tab = re.search(r'<a[^>]*id="tab-break"[^>]*>', html).group(0)
        self.assertIn('aria-selected="true"', break_tab)
        feed_tab = re.search(r'<a[^>]*id="tab-feed"[^>]*>', html).group(0)
        self.assertIn('aria-selected="false"', feed_tab)

    def test_saved_route_starts_on_the_saved_panel(self):
        html = self._get("/the-slate/saved")
        self.assertRegex(html, r'id="mainInner"[^>]*data-tab-panel="feed"[^>]*hidden')
        self.assertRegex(html, r'id="panel-break"[^>]*hidden')
        self.assertRegex(html, r'id="panel-saved"[^>]*data-tab-panel="saved"(?![^>]*hidden)')
        saved_tab = re.search(r'<a[^>]*id="tab-saved"[^>]*>', html).group(0)
        self.assertIn('aria-selected="true"', saved_tab)


class CommunityTabAriaSemanticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        cls.html = app.test_client().get("/the-slate").get_data(as_text=True)

    def test_tablist_and_tabs_present_with_unique_ids(self):
        self.assertIn('role="tablist"', self.html)
        self.assertIn('aria-label="Community views"', self.html)
        for tab_id in ("tab-feed", "tab-break", "tab-saved"):
            # Every id in this document must be unique — the panels are
            # only distinguished by data-tab-panel, and the single shared
            # switcher (not one per panel) is what keeps these ids from
            # colliding.
            self.assertEqual(
                self.html.count(f'id="{tab_id}"'), 1,
                f'{tab_id} must appear exactly once (a real, unique id)'
            )

    def test_tabs_reference_real_panel_ids_via_aria_controls(self):
        for tab_id, panel_id in (
            ("tab-feed", "mainInner"),
            ("tab-break", "panel-break"),
            ("tab-saved", "panel-saved"),
        ):
            tab = re.search(rf'<a[^>]*id="{tab_id}"[^>]*>', self.html).group(0)
            self.assertIn(f'aria-controls="{panel_id}"', tab)
            self.assertIn(f'id="{panel_id}"', self.html)

    def test_panels_are_labelled_by_their_tab(self):
        for panel_id, tab_id in (
            ("mainInner", "tab-feed"),
            ("panel-break", "tab-break"),
            ("panel-saved", "tab-saved"),
        ):
            self.assertIn(f'aria-labelledby="{tab_id}"', self.html)

    def test_keyboard_and_focus_support_present(self):
        # A roving tabindex (one 0, the rest -1) is how interview-studio.js
        # already does keyboard tab support — the same contract here.
        self.assertIn('tabindex="0"', self.html)
        self.assertIn('tabindex="-1"', self.html)


class CommunityTabHonestyTests(unittest.TestCase):
    """The mockup's own honesty line and the shared sample-community note
    pattern must appear on every tab (docs/initiatives/PS-COMMUNITY-TABS-001
    boundary: 'Honest sample-data labeling stays')."""

    def test_sample_data_line_and_sample_community_note_on_every_tab(self):
        client = app.test_client()
        for path in ("/the-slate", "/the-slate/break", "/the-slate/saved"):
            with self.subTest(path=path):
                html = client.get(path).get_data(as_text=True)
                self.assertIn(
                    "Sample data — nothing on this page is saved or shared.",
                    html,
                )
                self.assertIn('class="ps-sample-note"', html)
                self.assertIn("Sample community.", html)

    def test_composer_never_claims_a_fake_post_reached_a_real_write_api(self):
        # The Feed composer's simulated publish flow is a fixture/demo
        # (matches the existing PS-FEED-001 preview, unchanged) — it must
        # never call the real, identity-gated write API
        # (people_interests_api / /api/feed/posts) and must never be wired
        # to invent a fake success against it.
        js_path = os.path.join(ROOT, "static", "js", "feed-living-stream.js")
        with open(js_path, "r", encoding="utf-8") as f:
            js = f.read()
        self.assertNotIn("/api/feed/posts", js)


class CommunitySharedHeaderNotClobberedByFeedScriptTests(unittest.TestCase):
    """Regression guard (found during self-review, 2026-07-21): #pageTitle and
    #pageSubtitle are the ONE header the whole comm-shell shares across all
    three panels, but static/js/feed-living-stream.js's render() — reused
    verbatim from the standalone /feed-living-stream preview, where it is
    always "the" page — unconditionally wrote pageTitle.textContent = 'Feed'
    (and the matching default subtitle) on its own initial-load render.

    On a direct full-page load of /the-slate/break or /the-slate/saved this
    silently overwrote the correct server-rendered "The Break"/"Saved"
    heading back to "Feed" a few hundred ms after load (confirmed with
    Playwright + system Chrome: correct SSR text, then the delayed
    loading-state re-render inside feed-living-stream.js's
    applyInitialState() stomped it) — even though the active tab pill and
    panel content stayed correct throughout. The bookmarkable <title> tag
    was unaffected (Jinja-only, never touched by this script); only the
    visible on-page H1/subtitle were wrong. The fix is feedTabIsActive() in
    feed-living-stream.js, which reads the shared shell's live/initial
    active tab and only lets render() touch the shared header when Feed
    really is that tab — a no-op (always true) on the standalone preview,
    which carries no data-community-tabs attribute at all."""

    @classmethod
    def setUpClass(cls):
        js_path = os.path.join(ROOT, "static", "js", "feed-living-stream.js")
        with open(js_path, "r", encoding="utf-8") as f:
            cls.js = f.read()

    def test_feed_script_gates_header_writes_on_the_active_community_tab(self):
        self.assertIn("function feedTabIsActive()", self.js)
        # Every one of the 5 header-mutating statements inside render() (the
        # loading, detail, default-title, error, and default-subtitle
        # branches) must be gated — an ungated one is exactly how this bug
        # shipped the first time.
        self.assertEqual(self.js.count("headerIsFeeds"), 6)  # 1 assignment + 5 guarded uses

    def test_standalone_preview_is_unaffected_by_the_guard(self):
        # templates/feed_living_stream.html's #feed-app carries no
        # data-community-tabs attribute, so feedTabIsActive() must default to
        # true there — the guard must never require that attribute to exist.
        html_path = os.path.join(ROOT, "templates", "feed_living_stream.html")
        with open(html_path, "r", encoding="utf-8") as f:
            standalone_html = f.read()
        self.assertNotIn("data-community-tabs", standalone_html)
        self.assertIn(
            "if (!APP_ROOT || !APP_ROOT.hasAttribute('data-community-tabs')) { return true; }",
            self.js,
        )


class CommunitySavedTabContentTests(unittest.TestCase):
    """Saved folds the retired board's real 'Saved notes' fixture value in
    (services/people_interests_feed.py, read-only — not modified by this
    package) with honest labeling, per the package boundary."""

    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_saved_tab_renders_the_fixture_saved_notes(self):
        from services.people_interests_feed import people_interests_feed
        html = self.client.get("/the-slate/saved").get_data(as_text=True)
        for note in people_interests_feed.left_rail.get("saved_notes", []):
            with self.subTest(note=note["title"]):
                self.assertIn(note["title"], html)
                self.assertIn(note["preview"], html)

    def test_saved_tab_has_no_write_action(self):
        # Fixture data only, per the package boundary — no Save/Add control
        # is wired here (there is no backend to save anything yet).
        html = self.client.get("/the-slate/saved").get_data(as_text=True)
        saved_panel = html[html.index('data-tab-panel="saved"'):]
        self.assertNotIn("<form", saved_panel)
        self.assertNotIn("<button", saved_panel)


class CommunityBreakContentUnchangedTests(unittest.TestCase):
    """The Break's own accepted bento content is unredesigned — only its
    surrounding chrome (standalone page-head/switch, community sidebar)
    moved into the shared tab shell, per the package boundary ('Break =
    the existing accepted Break experience presented inside the tab shell;
    do not redesign its content')."""

    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        cls.html = app.test_client().get("/the-slate/break").get_data(as_text=True)

    def test_every_break_module_present(self):
        for text in (
            "Good break. Better you.",
            "Transformation",
            "Weekend Challenge",
            "Community Poll",
            "Local Discovery",
            "Save to Board",
            "Mood Switch",
            "Today's Pick-Me-Up",
            "Share something good",
            "Break well. Come back better.",
        ):
            self.assertIn(text, self.html)

    def test_back_to_the_feed_link_switches_the_seamless_tab(self):
        # Previously pointed at the separate /feed-living-stream preview;
        # Break and the real Feed now share one shell, so this must switch
        # tabs in place rather than leaving the shell.
        match = re.search(r'<a class="bk-btn bk-btn--outline"[^>]*>', self.html)
        self.assertIsNotNone(match)
        link = match.group(0)
        self.assertIn('data-comm-tab="feed"', link)
        self.assertIn('href="/the-slate"', link)


class CommunityTabAssetTests(unittest.TestCase):
    def test_static_files_exist(self):
        for rel in (
            "static/css/community-tabs.css",
            "static/js/community-tabs.js",
            "templates/the_slate.html",
        ):
            self.assertTrue(os.path.isfile(os.path.join(ROOT, rel)), rel)

    def test_new_page_links_its_own_stylesheet_and_script(self):
        html = app.test_client().get("/the-slate").get_data(as_text=True)
        self.assertIn("css/community-tabs.css", html)
        self.assertIn("js/community-tabs.js", html)
        self.assertIn("js/feed-living-stream.js", html)
        self.assertIn("js/break-database.js", html)


if __name__ == "__main__":
    unittest.main()
