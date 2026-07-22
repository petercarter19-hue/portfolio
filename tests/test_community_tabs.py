"""PS-COMMUNITY-TABS-001 — Community's owner-superseded two-view contract.

Feed and The Break are the only first-class Community views. The former Saved
URL survives as a compatibility redirect only; it cannot render a third panel,
tab, route claim, keyboard stop, or fixture destination.
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

    def test_two_first_class_routes_are_public(self):
        for path in ("/the-slate", "/the-slate/break"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_legacy_saved_and_retired_board_addresses_redirect_to_feed(self):
        for path in ("/the-slate/saved", "/the-slate/people-interests"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response.headers["Location"].endswith("/the-slate"))

    def test_neighboring_legacy_slate_routes_still_work(self):
        for path in ("/the-slate/my-slate", "/the-slate/daily", "/the-slate/pulse"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_sitemap_indexes_only_first_class_community_views(self):
        body = self.client.get("/sitemap.xml", base_url="https://peerslate.com").get_data(as_text=True)
        self.assertIn("https://peerslate.com/the-slate/break", body)
        self.assertNotIn("https://peerslate.com/the-slate/saved", body)


class CommunityTabInitialStateTests(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def _get(self, path):
        return self.client.get(path).get_data(as_text=True)

    def test_feed_direct_load_selects_feed_and_hides_break(self):
        html = self._get("/the-slate")
        self.assertRegex(html, r'id="mainInner"[^>]*data-tab-panel="feed"(?![^>]*hidden)[^>]*>')
        self.assertRegex(html, r'id="panel-break"[^>]*hidden')
        feed_tab = re.search(r'<a[^>]*id="tab-feed"[^>]*>', html).group(0)
        break_tab = re.search(r'<a[^>]*id="tab-break"[^>]*>', html).group(0)
        self.assertIn('aria-selected="true"', feed_tab)
        self.assertIn('aria-selected="false"', break_tab)

    def test_break_direct_load_selects_break_and_hides_feed(self):
        html = self._get("/the-slate/break")
        self.assertRegex(html, r'id="mainInner"[^>]*data-tab-panel="feed"[^>]*hidden')
        self.assertRegex(html, r'id="panel-break"[^>]*data-tab-panel="break"(?![^>]*hidden)')
        feed_tab = re.search(r'<a[^>]*id="tab-feed"[^>]*>', html).group(0)
        break_tab = re.search(r'<a[^>]*id="tab-break"[^>]*>', html).group(0)
        self.assertIn('aria-selected="false"', feed_tab)
        self.assertIn('aria-selected="true"', break_tab)


class CommunityTabAccessibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        cls.html = app.test_client().get("/the-slate").get_data(as_text=True)

    def test_two_tabs_have_unique_panel_wiring_and_roving_tabindex(self):
        self.assertIn('role="tablist"', self.html)
        self.assertIn('aria-label="Community views"', self.html)
        for tab_id, panel_id in (("tab-feed", "mainInner"), ("tab-break", "panel-break")):
            self.assertEqual(self.html.count(f'id="{tab_id}"'), 1)
            tab = re.search(rf'<a[^>]*id="{tab_id}"[^>]*>', self.html).group(0)
            self.assertIn(f'aria-controls="{panel_id}"', tab)
            self.assertIn(f'aria-labelledby="{tab_id}"', self.html)
        self.assertEqual(self.html.count('role="tab"'), 2)
        self.assertIn('tabindex="0"', self.html)
        self.assertIn('tabindex="-1"', self.html)

    def test_saved_has_no_rendered_product_surface(self):
        lowered = self.html.lower()
        for forbidden in ("tab-saved", "panel-saved", "data-saved-url", "data-comm-tab=\"saved\"", "save to board"):
            self.assertNotIn(forbidden, lowered)

    def test_per_post_save_is_an_action_not_a_community_view(self):
        """The established Feed action remains local to a post; it never
        introduces a third tab, route, or destination."""
        js_path = os.path.join(ROOT, "static", "js", "feed-living-stream.js")
        with open(js_path, encoding="utf-8") as handle:
            js = handle.read()
        self.assertIn('data-save=', js)
        self.assertIn('state.saves', js)
        self.assertNotIn('data-comm-tab="saved"', js)
        self.assertNotIn('/the-slate/saved', js)

    def test_script_supports_arrow_home_end_history_and_reduced_motion(self):
        js_path = os.path.join(ROOT, "static", "js", "community-tabs.js")
        css_path = os.path.join(ROOT, "static", "css", "community-tabs.css")
        with open(js_path, encoding="utf-8") as handle:
            js = handle.read()
        with open(css_path, encoding="utf-8") as handle:
            css = handle.read()
        self.assertIn("var TAB_KEYS = ['feed', 'break'];", js)
        for contract in ("ArrowRight", "ArrowLeft", "Home", "End", "pushState", "popstate"):
            self.assertIn(contract, js)
        self.assertIn("prefers-reduced-motion: reduce", css)

    def test_1078_feed_rail_contract_prevents_overlap_or_clipping(self):
        """At the requested 1078px regression width, Community overrides
        the inherited <1100px one-column preview rule: the rail remains a
        real grid column while the Feed column can shrink safely."""
        css_path = os.path.join(ROOT, "static", "css", "community-tabs.css")
        with open(css_path, encoding="utf-8") as handle:
            css = handle.read()
        self.assertIn("@media (min-width: 900px) and (max-width: 1120px)", css)
        self.assertIn("grid-template-columns: minmax(0, 1fr) 270px", css)
        self.assertIn("#feed-app .context-rail { display: block; }", css)

    def test_320_platform_header_keeps_the_full_interview_studio_label_gutter(self):
        """At 320px the inherited 20px link gap left only a 3px trailing
        margin after “Interview Studio.” This Community-scoped adjustment
        keeps the shared header readable without adding page overflow."""
        css_path = os.path.join(ROOT, "static", "css", "community-tabs.css")
        with open(css_path, encoding="utf-8") as handle:
            css = handle.read()
        self.assertIn("@media (max-width: 360px)", css)
        self.assertIn(
            "body.slate-light.the-slate-page .platform-nav__links { gap: 12px; }",
            css,
        )

    def test_review_modal_keeps_the_primary_action_reachable_and_traps_all_tabbables(self):
        """A 720px-tall viewport cannot strand Publish below a clipped
        modal or treat the close button as both ends of the focus trap."""
        js_path = os.path.join(ROOT, "static", "js", "feed-living-stream.js")
        css_path = os.path.join(ROOT, "static", "css", "feed-living-stream.css")
        with open(js_path, encoding="utf-8") as handle:
            js = handle.read()
        with open(css_path, encoding="utf-8") as handle:
            css = handle.read()
        for contract in (
            "function overlayFocusableItems",
            "preferred.focus({ preventScroll: true })",
            "var items = overlayFocusableItems(overlay);",
            "el.getClientRects().length > 0",
        ):
            self.assertIn(contract, js)
        self.assertNotIn("el.offsetParent !== null", js)
        for contract in (
            "max-height:calc(100dvh - 48px)",
            "display:flex; flex-direction:column",
            "flex:1 1 auto; min-height:0; overflow-y:auto",
            "position:sticky;bottom:0",
        ):
            self.assertIn(contract, css)


class CommunityTruthAndBreakTests(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_honesty_note_is_present_on_both_views(self):
        for path in ("/the-slate", "/the-slate/break"):
            with self.subTest(path=path):
                html = self.client.get(path).get_data(as_text=True)
                self.assertIn("Sample data — nothing on this page is saved or shared.", html)
                self.assertIn('class="ps-sample-note"', html)
                self.assertIn("Sample community.", html)

    def test_break_uses_supplied_photography_and_truthful_controls(self):
        html = self.client.get("/the-slate/break").get_data(as_text=True)
        for asset in (
            "images/community/break-chair-plant-640.webp",
            "images/community/break-transformation-640.webp",
            "images/community/break-bookstore-640.webp",
        ):
            self.assertIn(asset, html)
        self.assertIn('data-comm-create-post', html)
        self.assertIn('data-comm-tab="feed"', html)
        self.assertNotIn('data-break-api=', html)
        self.assertNotIn('data-db-', html)
        self.assertNotIn('Save to Board', html)
        self.assertNotIn('break-database.js', html)

    def test_break_has_no_fake_write_or_save_client_path(self):
        with open(os.path.join(ROOT, "static", "js", "community-tabs.js"), encoding="utf-8") as handle:
            js = handle.read()
        self.assertNotIn("/api/", js)
        self.assertIn("data-comm-create-post", js)

    def test_break_keeps_feed_shell_but_uses_the_authority_integrated_module_flow(self):
        """The shell retains Feed's 860px primary / 320px rail geometry, but
        the Break itself cannot strand Mood and the closing modules in a
        persistent second column. Their source order is the owner authority's
        single restorative sequence in either theme."""
        html = self.client.get("/the-slate/break").get_data(as_text=True)
        self.assertNotIn('class="bk-rail"', html)
        ordered = (
            'class="bk-hero"',
            'class="ps-card bk-card bk-transform"',
            'class="ps-card bk-card bk-challenge"',
            'class="ps-card bk-card bk-poll"',
            'class="ps-card bk-card bk-local"',
            'class="bk-flow"',
            'class="ps-card bk-mood"',
            'class="ps-card bk-quote"',
            'class="ps-card bk-pickme"',
            'class="ps-card bk-share"',
            'class="bk-band"',
        )
        positions = [html.index(token) for token in ordered]
        self.assertEqual(positions, sorted(positions))
        with open(os.path.join(ROOT, "static", "css", "community-tabs.css"), encoding="utf-8") as handle:
            css = handle.read()
        self.assertIn("grid-template-columns: minmax(0, var(--feed-w)) var(--rail-w)", css)
        self.assertIn("#feed-app .bk-flow { display: grid; gap: 16px; }", css)
        self.assertIn("#feed-app .bk-transform {\n  grid-column: 1 / -1;", css)


class CommunityAssetTests(unittest.TestCase):
    RESPONSIVE_MEDIA = {
        "static/images/community/break-chair-plant.png": (640, 1280),
        "static/images/community/break-transformation.png": (640, 1280),
        "static/images/community/break-bookstore.png": (640, 1280),
        "static/images/feed/dinner_served.jpg": (640, 1280),
        "static/images/feed/feed-workflow-whiteboard-2026-07-21.png": (640, 1280),
        "static/images/feed/feed-surf-sunrise-2026-07-21.png": (640, 1280),
        "static/images/feed/feed-team-demo-2026-07-21.png": (640, 1280),
        "static/images/feed/feed-trail-run-2026-07-21.png": (640, 1280),
        "static/images/feed/feed-coffee-notes-2026-07-21.png": (640, 1280),
        "static/images/feed/feed-keyboard-build-2026-07-21.png": (640, 1280),
        "static/images/feed/feed-keyboard-components-2026-07-21.png": (640, 1280),
        "static/images/feed/feed-mountain-hike-2026-07-21.png": (560, 1120),
        "static/images/feed/feed-prototype-table-2026-07-21.png": (640, 1280),
        "static/images/feed/feed-workflow-closeup-2026-07-21.png": (640, 1280),
        "static/images/feed/feed-workflow-corkboard-2026-07-21.png": (640, 1280),
        "static/images/feed/feed-surf-wave-2026-07-21.png": (640, 1280),
        "static/images/feed/feed-journal-notebook-2026-07-21.png": (640, 1280),
        "static/images/feed/feed-mountain-ridge-2026-07-21.png": (640, 1280),
    }

    def test_required_production_assets_and_manifest_exist(self):
        for rel in (
            "static/images/community/break-chair-plant.png",
            "static/images/community/break-transformation.png",
            "static/images/community/break-bookstore.png",
            "docs/initiatives/PS-COMMUNITY-TABS-001/visual-authority/ASSET_MANIFEST.md",
            "docs/initiatives/PS-COMMUNITY-TABS-001/01_AUTHORITY_INTEGRATION_MAP.md",
        ):
            self.assertTrue(os.path.isfile(os.path.join(ROOT, rel)), rel)

    def test_responsive_derivatives_exist_and_stay_within_transfer_budgets(self):
        """Mobile sources stay under 120 KiB and desktop sources under 250 KiB.

        The original personal dinner photo is deliberately retained; only its
        delivery derivatives are added alongside it.
        """
        for source, widths in self.RESPONSIVE_MEDIA.items():
            with self.subTest(source=source):
                self.assertTrue(os.path.isfile(os.path.join(ROOT, source)), source)
                stem = os.path.splitext(source)[0]
                mobile = os.path.join(ROOT, f"{stem}-{widths[0]}.webp")
                desktop = os.path.join(ROOT, f"{stem}-{widths[1]}.webp")
                self.assertTrue(os.path.isfile(mobile), mobile)
                self.assertTrue(os.path.isfile(desktop), desktop)
                self.assertLessEqual(os.path.getsize(mobile), 120 * 1024, mobile)
                self.assertLessEqual(os.path.getsize(desktop), 250 * 1024, desktop)


class CommunityResponsiveMediaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        client = app.test_client()
        cls.feed_html = client.get("/the-slate").get_data(as_text=True)
        cls.break_html = client.get("/the-slate/break").get_data(as_text=True)
        with open(os.path.join(ROOT, "static", "js", "feed-living-stream.js"), encoding="utf-8") as handle:
            cls.feed_js = handle.read()
        with open(os.path.join(ROOT, "static", "js", "community-tabs.js"), encoding="utf-8") as handle:
            cls.tabs_js = handle.read()

    def test_feed_defers_inactive_break_images_until_the_break_is_opened(self):
        self.assertIsNone(re.search(r'<img\b[^>]*\ssrc="/static/images/community/', self.feed_html))
        for image in ("break-chair-plant", "break-transformation", "break-bookstore"):
            self.assertIn(f'data-deferred-src="/static/images/community/{image}-640.webp"', self.feed_html)
            self.assertIn(f'data-deferred-srcset="/static/images/community/{image}-640.webp', self.feed_html)
        self.assertIn('loading="lazy"', self.feed_html)
        self.assertIn('decoding="async"', self.feed_html)
        self.assertIn('fetchpriority="low"', self.feed_html)
        for contract in (
            "function hydrateDeferredMedia",
            "setAttribute('srcset'",
            "setAttribute('sizes'",
            "setAttribute('loading', isHero ? 'eager' : 'lazy')",
            "setAttribute('fetchpriority', isHero ? 'high' : 'low')",
        ):
            self.assertIn(contract, self.tabs_js)

    def test_break_direct_load_has_full_responsive_attribute_contract(self):
        for image in ("break-chair-plant", "break-transformation", "break-bookstore"):
            self.assertIn(f'src="/static/images/community/{image}-640.webp"', self.break_html)
            self.assertIn(f'srcset="/static/images/community/{image}-640.webp 640w, /static/images/community/{image}-1280.webp 1280w"', self.break_html)
        hero = re.search(r'<img\s+class="bk-hero__image"[^>]*>', self.break_html).group(0)
        self.assertIn('sizes="(max-width: 700px) 100vw, 860px"', hero)
        self.assertIn('loading="eager"', hero)
        self.assertIn('decoding="async"', hero)
        self.assertIn('fetchpriority="high"', hero)
        self.assertGreaterEqual(self.break_html.count('fetchpriority="low"'), 2)

    def test_feed_renderer_uses_webp_srcset_and_explicit_loading_priorities(self):
        for contract in (
            "function responsiveImageHTML",
            "srcset=",
            "sizes=",
            "width=",
            "height=",
            'decoding="async"',
            'fetchpriority="',
            "priority: 'high'",
        ):
            self.assertIn(contract, self.feed_js)
        self.assertNotIn("post.image + '\" alt", self.feed_js)
        for retired in (
            "office_prototype.jpg",
            "whiteboard_close.jpg",
            "work_whiteboard.jpg",
            "surf_morning.jpg",
            "coffee_notes.jpg",
            "mountain_walk.jpg",
            "team_video.jpg",
        ):
            self.assertNotIn(retired, self.feed_js)

    def test_every_configured_feed_fixture_has_a_registered_responsive_source(self):
        dimensions = set(re.findall(r"^\s+'([^']+)': \[", self.feed_js, flags=re.MULTILINE))
        fixture_images = set(re.findall(r"\bimage:\s*'([^']+)'", self.feed_js))
        fixture_images.update(re.findall(r"\bpost\.image\s*=\s*'([^']+)'", self.feed_js))
        for gallery in re.findall(r"\bgallery:\s*\[([^]]+)\]", self.feed_js):
            fixture_images.update(re.findall(r"'([^']+)'", gallery))
        self.assertTrue(fixture_images)
        self.assertSetEqual(fixture_images, dimensions)

    def test_gallery_fixtures_do_not_reuse_a_media_path_within_a_rendered_state(self):
        gallery_state = re.search(r"var POSTS_GALLERY = \[(.*?)\n  \];", self.feed_js, re.DOTALL).group(1)
        galleries = [re.findall(r"'([^']+)'", gallery) for gallery in re.findall(r"\bgallery:\s*\[([^]]+)\]", gallery_state)]
        self.assertTrue(galleries)
        rendered_files = [file for gallery in galleries for file in gallery]
        self.assertEqual(len(rendered_files), len(set(rendered_files)), rendered_files)
        self.assertIn("feed-keyboard-components-2026-07-21.png", galleries[0])
        self.assertNotIn("feed-prototype-table-2026-07-21.png", galleries[0])

    def test_corrected_fixture_identities_are_reachable_in_the_actual_feed_states(self):
        """The review matrix can activate these through real Feed state
        paths, instead of treating the replacement rasters as loose assets."""
        gallery = re.search(r"var POSTS_GALLERY = \[(.*?)\n  \];", self.feed_js, re.DOTALL).group(1)
        video = re.search(r"var POSTS_VIDEO = \[(.*?)\n  \];", self.feed_js, re.DOTALL).group(1)
        for image in (
            "feed-prototype-table-2026-07-21.png",
            "feed-workflow-closeup-2026-07-21.png",
            "feed-workflow-corkboard-2026-07-21.png",
            "feed-journal-notebook-2026-07-21.png",
            "feed-keyboard-components-2026-07-21.png",
        ):
            self.assertIn(image, gallery)
        self.assertIn("feed-surf-wave-2026-07-21.png", video)
        self.assertIn("case 'gallery': state.composition = 'gallery';", self.feed_js)
        self.assertIn("case 'video': state.composition = 'video';", self.feed_js)
        self.assertIn("post.image = 'feed-mountain-ridge-2026-07-21.png';", self.feed_js)
        self.assertIn("if (a.photo)", self.feed_js)


if __name__ == "__main__":
    unittest.main()
