"""PS-COMMUNITY-TABS-001 — Community's owner-superseded two-view contract.

PS-COMMUNITY-AUTH-WALL-001 retired the public two-view shell itself: the
Break address is a compatibility redirect, the tabbed fixture shell never
renders again in any flag state, and Community is served only to signed-in
members. Route/render tests below assert that new truth; the static-file
contracts on the archived assets, styles, and scripts are unchanged.
"""

import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import unittest
from itertools import combinations

from app import app
from PIL import Image, ImageChops, ImageOps


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def contrast_ratio(foreground, background):
    """Return the WCAG relative-luminance contrast ratio for two hex colors."""
    def luminance(color):
        channels = [int(color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
        linear = [
            channel / 12.92 if channel <= 0.04045
            else ((channel + 0.055) / 1.055) ** 2.4
            for channel in channels
        ]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    light, dark = sorted((luminance(foreground), luminance(background)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


class CommunityTabRouteTests(unittest.TestCase):
    def setUp(self):
        self.previous = dict(app.config)
        app.config.update(
            TESTING=True,
            PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED=True,
            PEERSLATE_DEV_USER_KEY=None,
        )
        self.client = app.test_client()

    def tearDown(self):
        app.config.clear()
        app.config.update(self.previous)

    def test_community_requires_sign_in_and_break_redirects_to_it(self):
        # PS-COMMUNITY-AUTH-WALL-001: no Community route is public anymore.
        signed_out = self.client.get("/the-slate")
        self.assertEqual(signed_out.status_code, 302)
        self.assertEqual(
            signed_out.headers["Location"], "/auth/sign-in?return_to=/the-slate"
        )
        break_response = self.client.get("/the-slate/break")
        self.assertEqual(break_response.status_code, 302)
        self.assertTrue(break_response.headers["Location"].endswith("/the-slate"))

    def test_legacy_saved_and_retired_board_addresses_redirect_to_feed(self):
        for path in ("/the-slate/saved", "/the-slate/people-interests"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response.headers["Location"].endswith("/the-slate"))

    def test_neighboring_legacy_slate_routes_redirect_to_community(self):
        # Their pages are retired in every flag state; the human addresses
        # forward to the one real Community.
        for path in ("/the-slate/my-slate", "/the-slate/daily", "/the-slate/pulse"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response.headers["Location"].endswith("/the-slate"))

    def test_sitemap_indexes_no_community_views_at_all(self):
        # PS-COMMUNITY-AUTH-WALL-001: the members-only namespace never
        # belongs in the public sitemap.
        body = self.client.get("/sitemap.xml", base_url="https://peerslate.com").get_data(as_text=True)
        self.assertNotIn("/the-slate", body)


class CommunityRetiredTabShellTests(unittest.TestCase):
    """The two-view tabbed fixture shell never renders again."""

    def setUp(self):
        self.previous = dict(app.config)
        app.config.update(
            TESTING=True,
            PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED=True,
            PEERSLATE_DEV_USER_KEY="tabs-member-not-owner",
            PEERSLATE_OWNER_USER_KEYS="someone-else-entirely",
            PEERSLATE_OWNER_EMAILS="",
        )
        self.client = app.test_client()

    def tearDown(self):
        app.config.clear()
        app.config.update(self.previous)

    def test_member_feed_is_the_single_community_shell_without_tabs(self):
        response = self.client.get("/the-slate")
        html = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("cv1-shell", html)
        for retired in (
            'id="tab-feed"',
            'id="tab-break"',
            'id="panel-break"',
            "data-tab-panel",
            'aria-label="Community views"',
            "community-tabs.js",
            "community-tabs.css",
            "feed-living-stream.js",
        ):
            with self.subTest(marker=retired):
                self.assertNotIn(retired, html)

    def test_break_direct_load_is_a_redirect_not_a_panel(self):
        response = self.client.get("/the-slate/break")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/the-slate"))
        self.assertNotIn(b'id="panel-break"', response.data)


class CommunityTabAccessibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # PS-COMMUNITY-AUTH-WALL-001: the page under test is the signed-in
        # member render — the only Community render that exists now.
        cls.previous_config = dict(app.config)
        app.config.update(
            TESTING=True,
            PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED=True,
            PEERSLATE_DEV_USER_KEY="tabs-a11y-member",
            PEERSLATE_OWNER_USER_KEYS="someone-else-entirely",
            PEERSLATE_OWNER_EMAILS="",
        )
        cls.html = app.test_client().get("/the-slate").get_data(as_text=True)

    @classmethod
    def tearDownClass(cls):
        app.config.clear()
        app.config.update(cls.previous_config)

    def test_the_retired_tablist_never_renders_for_a_member(self):
        # The roving-tabindex tablist belonged to the retired fixture shell.
        self.assertIn("cv1-shell", self.html)
        self.assertNotIn('aria-label="Community views"', self.html)
        self.assertEqual(self.html.count('role="tab"'), 0)
        for retired_id in ("tab-feed", "tab-break", "panel-break"):
            with self.subTest(retired_id=retired_id):
                self.assertNotIn(f'id="{retired_id}"', self.html)

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
        """A 720px-tall viewport cannot strand preview below a clipped
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

    def test_community_overlay_clears_site_chrome_and_mobile_navigation(self):
        """The modal cannot be trapped under the global header or bottom bar."""
        feed_css_path = os.path.join(ROOT, "static", "css", "feed-living-stream.css")
        site_css_path = os.path.join(ROOT, "static", "css", "style.css")
        with open(feed_css_path, encoding="utf-8") as handle:
            feed_css = handle.read()
        with open(site_css_path, encoding="utf-8") as handle:
            site_css = handle.read()

        overlay = re.search(r"\.overlay \{[^}]*z-index:(\d+)", feed_css).group(1)
        mobile_bar = re.search(r"\.mobile-bottom\{[^}]*z-index:(\d+)", feed_css).group(1)
        site_ceiling = max(int(value) for value in re.findall(r"z-index:\s*(\d+)", site_css))
        self.assertGreater(int(overlay), site_ceiling)
        self.assertGreater(int(overlay), int(mobile_bar))
        self.assertIn(
            "body.feed-preview-page .main-content:has(#overlayRoot > .overlay),\n"
            "body.community-tabs-page .main-content:has(#overlayRoot > .overlay) { isolation: auto; }",
            feed_css,
        )
        self.assertNotIn("header (z-index 1200)", feed_css)
        self.assertNotIn("overlay's own z-index (1300", feed_css)

    def test_dark_community_modal_uses_dark_surfaces_with_accessible_contrast(self):
        """Prevent the exact light-text-on-white integrated-theme regression."""
        css_path = os.path.join(ROOT, "static", "css", "feed-living-stream.css")
        with open(css_path, encoding="utf-8") as handle:
            css = handle.read()

        selector = 'body[data-theme="dark"].community-tabs-page #feed-app .voice-modal {'
        start = css.index(selector)
        end = css.index("\n}", start)
        modal_block = css[start:end]
        variables = dict(re.findall(r"--(comm-modal-[\w-]+):\s*(#[0-9a-fA-F]{6});", modal_block))

        self.assertGreater(start, css.index(".voice-modal {"))
        self.assertEqual(variables["comm-modal-surface"], "#0c1924")
        self.assertNotIn("background: #fff", modal_block)
        self.assertIn("background: linear-gradient", modal_block)
        for selector_fragment in (
            ".modal-head h2",
            ".listening-help",
            ".transcript-box",
            ".proposal",
            ".privacy-option strong",
            ".privacy-option span",
            '.chip[aria-disabled="true"]',
            ".review-footer .meta",
            ".voice-modal .btn.primary",
            ".voice-modal button:disabled",
            ".voice-modal :is(button, input, textarea, [tabindex]):focus-visible",
        ):
            self.assertIn(selector_fragment, css)

        normal_text_pairs = {
            "title on surface": (variables["comm-modal-title"], variables["comm-modal-surface"]),
            "body on surface": (variables["comm-modal-text"], variables["comm-modal-surface"]),
            "muted on surface": (variables["comm-modal-muted"], variables["comm-modal-surface"]),
            "body on side": (variables["comm-modal-text"], variables["comm-modal-raised"]),
            "muted on side": (variables["comm-modal-muted"], variables["comm-modal-raised"]),
            "body on proposal": (variables["comm-modal-text"], variables["comm-modal-soft"]),
            "muted on proposal": (variables["comm-modal-muted"], variables["comm-modal-soft"]),
            "input text": (variables["comm-modal-text"], variables["comm-modal-control"]),
            "input placeholder": (variables["comm-modal-muted"], variables["comm-modal-control"]),
            "proposal label": ("#c7e6aa", variables["comm-modal-soft"]),
            "base chip": ("#d2ded8", "#1c2b35"),
            "AI chip": ("#b7e4d6", "#163237"),
            "project chip": ("#d2deb6", "#203039"),
            "disabled control": ("#9ba9a4", "#18242d"),
        }
        for label, colors in normal_text_pairs.items():
            with self.subTest(text=label):
                self.assertGreaterEqual(contrast_ratio(*colors), 4.5)

        control_pairs = {
            "control border": (variables["comm-modal-border"], variables["comm-modal-control"]),
            "surface border": (variables["comm-modal-border"], variables["comm-modal-surface"]),
            "focus ring": (variables["comm-modal-accent"], variables["comm-modal-control"]),
            "primary action": (
                variables["comm-modal-accent-ink"], variables["comm-modal-accent"]),
        }
        for label, colors in control_pairs.items():
            with self.subTest(control=label):
                self.assertGreaterEqual(contrast_ratio(*colors), 3.0)

        # Light Community remains the established paper dialog.
        self.assertGreaterEqual(contrast_ratio("#101b30", "#ffffff"), 4.5)

    def test_polaroid_transform_overflow_is_clipped_at_its_feed_component_only(self):
        css_path = os.path.join(ROOT, "static", "css", "feed-living-stream.css")
        js_path = os.path.join(ROOT, "static", "js", "feed-living-stream.js")
        with open(css_path, encoding="utf-8") as handle:
            css = handle.read()
        with open(js_path, encoding="utf-8") as handle:
            js = handle.read()

        polaroid_branch = re.search(
            r"if \(post\.frame === 'polaroid'\) \{(.*?)\n    \}", js, re.DOTALL
        ).group(1)
        self.assertIn('<div class="polaroid-viewport"><figure class="polaroid">', polaroid_branch)
        self.assertIn("</figure></div>", polaroid_branch)
        self.assertIn(
            ".polaroid-viewport { width:100%; min-width:0; "
            "overflow-x:clip; overflow-y:visible; }",
            css,
        )
        self.assertIn("transform:rotate(-1.4deg)", css)

        # The containment belongs to the generated Feed media component. It
        # must not suppress legitimate horizontal UI globally or alter Break.
        for forbidden in (
            "html { overflow-x:hidden",
            "body { overflow-x:hidden",
            ".feed-column { overflow-x:hidden",
            ".break-inner { overflow-x:hidden",
            ".bk-page { overflow-x:hidden",
        ):
            self.assertNotIn(forbidden, css)

    def test_320_voice_player_flexes_waveform_without_hiding_controls(self):
        css_path = os.path.join(ROOT, "static", "css", "feed-living-stream.css")
        with open(css_path, encoding="utf-8") as handle:
            css = handle.read()

        self.assertIn(
            ".wave { flex:1; min-width:0; height:28px; display:flex; "
            "align-items:center; gap:3px; }",
            css,
        )
        self.assertIn(".wave span { flex:0 1 3px; width:3px;", css)
        self.assertIn(".voice-time { flex:0 0 auto;", css)
        self.assertIn(".voice-play:hover", css)
        self.assertIn("@media (max-width: 360px)", css)
        self.assertIn(".voice-player{gap:8px;padding-inline:10px}", css)
        self.assertIn(".wave{gap:2px}", css)

        # At the measured 244px player client width, the <=360px padding/gaps
        # leave positive flexible space after the fixed play and time controls.
        player_client = 244
        waveform_space = player_client - 20 - 34 - 20 - 16
        self.assertEqual(waveform_space, 154)
        self.assertGreater(waveform_space, 0)
        self.assertNotIn(".voice-time{display:none", css)
        self.assertNotIn(".voice-player{overflow:hidden", css)

    def test_focus_lifecycle_behavior_harness_passes(self):
        node = shutil.which("node")
        app_node = "/Applications/ChatGPT.app/Contents/Resources/cua_node/bin/node"
        if not node and os.path.isfile(app_node):
            node = app_node
        if not node:
            self.skipTest("Node runtime unavailable for the dependency-free focus behavior harness")
        result = subprocess.run(
            [node, os.path.join(ROOT, "tests", "community_focus_lifecycle.test.js")],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("10 behavioral checks passed", result.stdout)

    def test_bottom_break_return_reveals_focused_feed_destination_only(self):
        with open(os.path.join(ROOT, "static", "js", "community-tabs.js"), encoding="utf-8") as handle:
            js = handle.read()
        self.assertIn("var revealDestination = trigger.getAttribute('role') !== 'tab';", js)
        self.assertIn("focus: revealDestination", js)
        self.assertIn("revealFocus: revealDestination", js)
        self.assertIn("focusLifecycle.revealFocusedElement(window, nextTab);", js)
        self.assertIn(
            "setTab(next, { updateUrl: next !== currentTab(), focus: true });",
            js,
        )

    def test_every_dark_break_kicker_and_small_poll_note_meets_contrast(self):
        # PS-COMMUNITY-AUTH-WALL-001: the Break page no longer renders
        # (/the-slate/break is a redirect), so the archived template is the
        # source of the kicker copy; the CSS contract stays intact for the
        # authenticated Break's future revival.
        with open(os.path.join(ROOT, "templates", "the_slate.html"), encoding="utf-8") as handle:
            html = handle.read()
        with open(os.path.join(ROOT, "static", "css", "community-tabs.css"), encoding="utf-8") as handle:
            css = handle.read()

        fragments = re.findall(
            r'<(?:p|span) class="bk-kicker">(.*?)</(?:p|span)>', html, re.DOTALL)
        kickers = [
            re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", fragment)).strip()
            for fragment in fragments
        ]
        dark_surfaces = {
            "A restorative Community pause": "#071419",
            "Transformation": "#0e1c27",
            "Weekend Challenge": "#122c23",
            "Community Prompt": "#0e1c27",
            "Local Discovery": "#0e1c27",
        }
        self.assertEqual(kickers, list(dark_surfaces))

        kicker_rule = re.search(
            r'body\[data-theme="dark"\] #feed-app \.bk-kicker \{ color: (#[0-9a-fA-F]{6}); \}',
            css,
        )
        self.assertIsNotNone(kicker_rule)
        for label, background in dark_surfaces.items():
            with self.subTest(kicker=label):
                self.assertGreaterEqual(contrast_ratio(kicker_rule.group(1), background), 4.5)

        poll_rule = re.search(
            r'body\[data-theme="dark"\] #feed-app \.bk-poll__foot '
            r'\{ color: (#[0-9a-fA-F]{6}) !important; \}',
            css,
        )
        self.assertIsNotNone(poll_rule)
        self.assertGreaterEqual(contrast_ratio(poll_rule.group(1), "#0e1c27"), 4.5)

        local_place_rule = re.search(
            r'body\[data-theme="dark"\] #feed-app \.bk-local__place '
            r'\{ color: (#[0-9a-fA-F]{6}) !important; \}',
            css,
        )
        local_qualifier_rule = re.search(
            r'body\[data-theme="dark"\] #feed-app \.bk-local__place small '
            r'\{ color: (#[0-9a-fA-F]{6}); \}',
            css,
        )
        self.assertIsNotNone(local_place_rule)
        self.assertIsNotNone(local_qualifier_rule)
        place_ratio = contrast_ratio(local_place_rule.group(1), "#0e1c27")
        qualifier_ratio = contrast_ratio(local_qualifier_rule.group(1), "#0e1c27")
        self.assertGreaterEqual(place_ratio, 4.5)
        self.assertGreaterEqual(qualifier_ratio, 4.5)
        self.assertGreater(place_ratio, qualifier_ratio)

    def test_dark_break_muted_copy_and_focus_ring_keep_accessible_contrast(self):
        with open(os.path.join(ROOT, "static", "css", "community-tabs.css"), encoding="utf-8") as handle:
            community_css = handle.read()
        with open(os.path.join(ROOT, "static", "css", "feed-living-stream.css"), encoding="utf-8") as handle:
            feed_css = handle.read()

        self.assertIn("color: #b7c4bf", community_css)
        self.assertGreaterEqual(contrast_ratio("#b7c4bf", "#122c23"), 4.5)
        self.assertIn(
            "a:focus-visible, button:focus-visible, [tabindex]:focus-visible, "
            "input:focus-visible, textarea:focus-visible",
            feed_css,
        )
        self.assertIn("outline:2px solid var(--indigo)", feed_css)
        self.assertGreaterEqual(contrast_ratio("#96bb76", "#122c23"), 3.0)

    def test_dark_feed_action_and_listen_states_meet_normal_text_contrast(self):
        with open(os.path.join(ROOT, "static", "css", "community-tabs.css"), encoding="utf-8") as handle:
            css = handle.read()

        feed_canvas = "#06111c"
        rail_surface = "#0c1924"
        state_pairs = {
            "Comment/Save normal": ("#c3ced0", feed_canvas),
            "Comment/Save hover/focus": ("#f3efe5", feed_canvas),
            "Respond normal": ("#b3d793", feed_canvas),
            "Respond hover/focus/pressed": ("#d0e5b2", feed_canvas),
            "action disabled": ("#aeb9bb", feed_canvas),
            "respond option normal": ("#c3ced0", rail_surface),
            "respond option hover/focus": ("#f3efe5", "#132633"),
            "respond option pressed": ("#0b0c0e", "#b3d793"),
            "respond option disabled": ("#aeb9bb", rail_surface),
            "Listen normal": ("#0b0c0e", "#d8a928"),
            "Listen hover/focus": ("#0b0c0e", "#e3b83a"),
            "Listen disabled": ("#f3efe5", "#6b5a2d"),
        }
        for state, (foreground, effective_background) in state_pairs.items():
            with self.subTest(state=state):
                self.assertGreaterEqual(
                    contrast_ratio(foreground, effective_background),
                    4.5,
                    f"{state}: {foreground} on {effective_background}",
                )

        for selector_or_declaration in (
            '.community-tabs-page #feed-app .actions { color: #c3ced0; }',
            '.community-tabs-page #feed-app .action:focus-visible { color: #f3efe5; }',
            '.community-tabs-page #feed-app .action.primary-action { color: #b3d793; }',
            '.community-tabs-page #feed-app .action[aria-pressed="true"] { color: #d0e5b2; }',
            '.community-tabs-page #feed-app .action:disabled {',
            '.community-tabs-page #feed-app .respond-option:focus-visible { background: #132633; color: #f3efe5; }',
            '.community-tabs-page #feed-app .respond-option[aria-pressed="true"] { background: #b3d793; border-color: #b3d793; color: #0b0c0e; }',
            '.community-tabs-page #feed-app .respond-option:disabled { background: #0c1924; color: #aeb9bb; opacity: 1; }',
            '.community-tabs-page #feed-app .rail-cta { background: #d8a928; color: #0b0c0e; }',
            '.community-tabs-page #feed-app .rail-cta:focus-visible { background: #e3b83a; color: #0b0c0e; }',
            '.community-tabs-page #feed-app .rail-cta:disabled { background: #6b5a2d; color: #f3efe5; opacity: 1; }',
        ):
            with self.subTest(css_contract=selector_or_declaration):
                self.assertIn(selector_or_declaration, css)


class CommunityTruthAndBreakTests(unittest.TestCase):
    def setUp(self):
        self.previous = dict(app.config)
        app.config.update(
            TESTING=True,
            PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED=True,
            PEERSLATE_DEV_USER_KEY="tabs-truth-member",
            PEERSLATE_OWNER_USER_KEYS="someone-else-entirely",
            PEERSLATE_OWNER_EMAILS="",
        )
        self.client = app.test_client()

    def tearDown(self):
        app.config.clear()
        app.config.update(self.previous)

    def test_fixture_honesty_notes_retired_with_the_public_shell(self):
        # PS-COMMUNITY-AUTH-WALL-001: a member reads the real Community, so
        # the fixture "Sample data" disclaimers must never appear — and the
        # Break view no longer renders at all.
        html = self.client.get("/the-slate").get_data(as_text=True)
        for fixture_claim in (
            "Sample data — nothing on this page is saved or shared.",
            'class="ps-sample-note"',
            "Sample community.",
        ):
            with self.subTest(fixture_claim=fixture_claim):
                self.assertNotIn(fixture_claim, html)
        self.assertEqual(self.client.get("/the-slate/break").status_code, 302)

    def test_legacy_my_slate_links_never_claim_the_flagged_off_journal(self):
        # The Living Stream prototype page is retired: its address forwards
        # to the real Community and renders no legacy links at all. The
        # archived script keeps its truthful labels.
        response = self.client.get("/feed-living-stream")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/the-slate"))
        html = response.get_data(as_text=True)
        self.assertNotIn('href="/the-slate/my-slate"', html)
        self.assertNotIn('href="/app/journal"', html)
        with open(os.path.join(ROOT, "static", "js", "feed-living-stream.js"), encoding="utf-8") as handle:
            js = handle.read()
        self.assertIn('href="/the-slate/my-slate">Open My Slate', js)
        self.assertNotIn('href="/the-slate/my-slate">Open my Journal', js)
        self.assertNotIn('href="/app/journal"', js)

    def test_break_address_serves_no_photography_or_controls_anymore(self):
        # The supplied photography stays on disk (CommunityAssetTests); the
        # retired page no longer delivers it or its controls.
        response = self.client.get("/the-slate/break")
        html = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 302)
        for retired in (
            "images/community/break-chair-plant-640.webp",
            "images/community/break-transformation-640.webp",
            "images/community/break-bookstore-640.webp",
            "data-comm-create-post",
            'data-comm-tab="feed"',
            "Save to Board",
        ):
            with self.subTest(marker=retired):
                self.assertNotIn(retired, html)

    def test_break_has_no_fake_write_or_save_client_path(self):
        with open(os.path.join(ROOT, "static", "js", "community-tabs.js"), encoding="utf-8") as handle:
            js = handle.read()
        self.assertNotIn("/api/", js)
        self.assertIn("data-comm-create-post", js)

    def test_feed_composer_is_explicitly_a_local_preview(self):
        with open(os.path.join(ROOT, "static", "js", "feed-living-stream.js"), encoding="utf-8") as handle:
            js = handle.read()
        for approved in (
            "Add preview to Feed",
            "Appears in this local sample feed only. Nothing is saved, shared, or added to your Journal.",
            "Local preview · not saved",
            "Preview added to this sample feed for this browser session only. Nothing was saved or shared.",
            "My Story preview · not connected",
            "Slate Board preview · not connected",
            "Resume preview · not connected",
            "No confidentiality or safety check ran.",
        ):
            self.assertIn(approved, js)
        for forbidden in (
            "Publish update",
            "Save privately",
            "Saved privately to your Journal",
            "Appears in Feed and your public Journal",
            "Confidentiality check",
            "No employer, customer, or restricted details were detected",
            "From Pete’s Journal",
            "Published to ",
        ):
            self.assertNotIn(forbidden, js)

    def test_connection_chips_are_inert_preview_labels(self):
        with open(os.path.join(ROOT, "static", "js", "feed-living-stream.js"), encoding="utf-8") as handle:
            js = handle.read()
        chip = re.search(r"function connectChipHTML\(key\) \{(.*?)\n  \}", js, re.DOTALL).group(1)
        self.assertIn("data-connect-preview", chip)
        self.assertIn('aria-disabled="true"', chip)
        self.assertNotIn("<button", chip)
        self.assertNotIn("aria-pressed", chip)
        self.assertNotIn("data-connect=", js)

    def test_local_preview_feature_flags_remain_off_by_default(self):
        self.assertFalse(app.config["PEERSLATE_DATABASE_UI_ENABLED"])
        self.assertFalse(app.config["PEERSLATE_JOURNAL_ENABLED"])

    def test_archived_break_composition_keeps_the_authority_module_flow(self):
        """The Break page is retired from rendering (PS-COMMUNITY-AUTH-WALL-001),
        but the archived template remains the owner authority's single
        restorative sequence: no persistent second column, modules in the
        approved order, ready for an authenticated revival."""
        with open(os.path.join(ROOT, "templates", "the_slate.html"), encoding="utf-8") as handle:
            html = handle.read()
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

    def test_active_visual_matrix_contains_only_unique_feed_and_break_states(self):
        evidence_dir = os.path.join(ROOT, "artifacts", "ps-community-tabs-001")
        names = sorted(name for name in os.listdir(evidence_dir) if name.endswith(".png"))
        self.assertTrue(names)

        hashes = {}
        for name in names:
            with self.subTest(file=name):
                lowered = name.lower()
                self.assertRegex(lowered, r"(?:feed|break)")
                self.assertNotIn("saved", lowered)
                with open(os.path.join(evidence_dir, name), "rb") as handle:
                    digest = hashlib.sha256(handle.read()).hexdigest()
                self.assertNotIn(digest, hashes, f"{name} duplicates {hashes.get(digest)}")
                hashes[digest] = name

    def test_exact_sha_evidence_manifest_is_complete_and_hash_bound(self):
        evidence_dir = os.path.join(ROOT, "artifacts", "ps-community-tabs-001")
        manifest_path = os.path.join(evidence_dir, "EVIDENCE_MANIFEST.json")
        with open(manifest_path, encoding="utf-8") as handle:
            manifest = json.load(handle)

        self.assertEqual(
            manifest["capture_source"]["product_commit"],
            "8326f2c3aff483f44822ae100d3dc1aedf42d437",
        )
        captures = manifest["captures"]
        capture_count = len(captures)
        capture_method = manifest["capture_method"]
        conversion_count = capture_method["validated_source_target_pair_count"]
        conversion_count_text = re.search(
            r"All (\d+) source/target pairs", capture_method["conversion_validation"],
        )
        self.assertIsNotNone(conversion_count_text)
        self.assertEqual(int(conversion_count_text.group(1)), conversion_count)
        self.assertEqual(conversion_count, capture_count)
        self.assertEqual(manifest["exact_duplicate_audit"]["file_count"], capture_count)
        self.assertEqual(
            manifest["exact_duplicate_audit"]["unique_file_sha256_count"],
            capture_count,
        )

        listed_names = {capture["file"] for capture in captures}
        actual_names = {
            name for name in os.listdir(evidence_dir)
            if name.endswith(".png")
        }
        self.assertSetEqual(actual_names, listed_names)

        states = {
            (capture["route"], capture["viewport"], capture["theme"], capture["region"])
            for capture in captures
        }
        for state in (
            ("/the-slate", "1440x1000", "light", "top"),
            ("/the-slate", "1440x1000", "dark", "top"),
            ("/the-slate", "390x844", "light", "top"),
            ("/the-slate", "390x844", "dark", "top"),
            ("/the-slate/break", "1440x1000", "light", "top"),
            ("/the-slate/break", "1440x1000", "light", "lower"),
            ("/the-slate/break", "1440x1000", "dark", "top"),
            ("/the-slate/break", "1440x1000", "dark", "lower"),
            ("/the-slate/break", "390x844", "light", "top"),
            ("/the-slate/break", "390x844", "light", "lower"),
            ("/the-slate/break", "390x844", "dark", "top"),
            ("/the-slate/break", "390x844", "dark", "lower"),
            ("/the-slate/break", "320x800", "light", "top"),
            ("/the-slate/break", "320x800", "dark", "top"),
        ):
            self.assertIn(state, states)

        action_state = next(
            capture for capture in captures
            if capture["file"].startswith("break__route-the-slate__state-feed-keyboard-switch-focus")
        )
        self.assertIn("ArrowRight", action_state["action_sequence"])
        self.assertEqual(action_state["start_route"], "/the-slate")
        self.assertEqual(action_state["end_route"], "/the-slate/break")
        self.assertEqual(action_state["route"], "/the-slate/break")

        seen_file_hashes = set()
        for capture in captures:
            for key in (
                "route", "start_state", "action_sequence", "viewport", "theme",
                "dimensions", "file_sha256", "decoded_rgba_sha256",
                "canonical_source", "derivative_lineage",
            ):
                self.assertIn(key, capture)
            path = os.path.join(evidence_dir, capture["file"])
            with open(path, "rb") as handle:
                data = handle.read()
            self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
            file_hash = hashlib.sha256(data).hexdigest()
            self.assertEqual(file_hash, capture["file_sha256"])
            self.assertNotIn(file_hash, seen_file_hashes)
            seen_file_hashes.add(file_hash)
            with Image.open(path) as source:
                image = ImageOps.exif_transpose(source).convert("RGBA")
            self.assertEqual(f"{image.width}x{image.height}", capture["dimensions"])
            normalized = struct.pack(">II", image.width, image.height) + image.tobytes()
            self.assertEqual(
                hashlib.sha256(normalized).hexdigest(),
                capture["decoded_rgba_sha256"],
            )

        exception = manifest["perceptual_duplicate_audit"]["declared_semantic_state_exception"]
        first, second = exception["files"]
        with Image.open(os.path.join(evidence_dir, first)) as left, Image.open(os.path.join(evidence_dir, second)) as right:
            difference = ImageChops.difference(left.convert("RGB"), right.convert("RGB"))
        self.assertIsNotNone(difference.getbbox())
        self.assertTrue(exception["exact_file_hashes_differ"])

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

    def test_product_sources_have_no_duplicate_or_near_duplicate_images(self):
        """Product rasters must remain distinct; visual authorities are excluded."""
        hashes = {}
        for relative_path in self.RESPONSIVE_MEDIA:
            with Image.open(os.path.join(ROOT, relative_path)) as source:
                gray = source.convert("L").resize((9, 8))
                pixels = list(gray.getdata())
            value = 0
            for row in range(8):
                for column in range(8):
                    left = pixels[row * 9 + column]
                    right = pixels[row * 9 + column + 1]
                    value = (value << 1) | int(left > right)
            hashes[relative_path] = value

        closest = min(
            ((left ^ right).bit_count(), left_path, right_path)
            for (left_path, left), (right_path, right) in combinations(hashes.items(), 2)
        )
        self.assertGreater(closest[0], 6, closest)


class CommunityResponsiveMediaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # PS-COMMUNITY-AUTH-WALL-001: the only Community render is the
        # signed-in member Feed; the Break address answers with a redirect.
        cls.previous_config = dict(app.config)
        app.config.update(
            TESTING=True,
            PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED=True,
            PEERSLATE_DEV_USER_KEY="tabs-media-member",
            PEERSLATE_OWNER_USER_KEYS="someone-else-entirely",
            PEERSLATE_OWNER_EMAILS="",
        )
        client = app.test_client()
        cls.feed_html = client.get("/the-slate").get_data(as_text=True)
        cls.break_response = client.get("/the-slate/break")
        with open(os.path.join(ROOT, "static", "js", "feed-living-stream.js"), encoding="utf-8") as handle:
            cls.feed_js = handle.read()
        with open(os.path.join(ROOT, "static", "js", "community-tabs.js"), encoding="utf-8") as handle:
            cls.tabs_js = handle.read()

    @classmethod
    def tearDownClass(cls):
        app.config.clear()
        app.config.update(cls.previous_config)

    def test_member_feed_serves_no_retired_break_media(self):
        # The fixture Break photography and its deferred-hydration hooks
        # belong to the retired shell; the member Feed never ships them. The
        # archived hydration contract in community-tabs.js stays intact.
        self.assertIn("cv1-shell", self.feed_html)
        self.assertIsNone(re.search(r'<img\b[^>]*\ssrc="/static/images/community/', self.feed_html))
        self.assertNotIn("data-deferred-src", self.feed_html)
        self.assertNotIn("/static/images/community/", self.feed_html)
        for contract in (
            "function hydrateDeferredMedia",
            "setAttribute('srcset'",
            "setAttribute('sizes'",
            "setAttribute('loading', isHero ? 'eager' : 'lazy')",
            "setAttribute('fetchpriority', isHero ? 'high' : 'low')",
        ):
            self.assertIn(contract, self.tabs_js)

    def test_break_direct_load_redirects_without_serving_media(self):
        self.assertEqual(self.break_response.status_code, 302)
        self.assertTrue(
            self.break_response.headers["Location"].endswith("/the-slate")
        )
        body = self.break_response.get_data(as_text=True)
        self.assertNotIn("/static/images/community/", body)
        self.assertNotIn("bk-hero__image", body)

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
