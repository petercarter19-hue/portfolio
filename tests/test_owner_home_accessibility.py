"""PS-HOME-FRONTEND-001 static/DOM accessibility assertions for the flag-on
Owner Home render (templates/owner_home.html and its partials).

These are structural, framework-free checks against the actual server-
rendered bytes (html.parser, following the pattern already used by
tests/test_my_story.py) so they run in the standard suite without adding a
new dependency. They cover EXPERIENCE_ACCESSIBILITY_REQUIREMENTS.md items
that are verifiable from static markup: one <h1>, no nested <main>, real
links vs. genuinely disabled Coming-later text, visible (not icon/color-only)
status and Coming-later labels, decorative SVGs hidden from assistive tech,
a single accessible live region, and the page-scoped bottom nav shape.
Browser-driven NVDA/keyboard/zoom/forced-colors/reduced-motion/screenshot
evidence is separate manual and visual evidence recorded in the completion
report; this file cannot substitute for it.
"""

import re
import unittest
from datetime import datetime, timezone
from html.parser import HTMLParser
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app import app
from services.owner_home_service import OwnerHomeContractError, OwnerHomeService


OWNER_A_PROFILE = "11111111-1111-1111-1111-111111111111"
FAILED_A = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
PROPOSAL_A = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
READY_A = "cccccccc-cccc-cccc-cccc-cccccccccccc"
MOMENT_A = "dddddddd-dddd-dddd-dddd-dddddddddddd"

VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "param", "source", "track", "wbr",
}


class OwnerHomeDomParser(HTMLParser):
    """Builds a flat, order-preserving element list with a simple parent
    stack so assertions can check ancestry (e.g. "this <a> is inside
    .oh-bottomnav") without a real DOM library."""

    def __init__(self):
        super().__init__()
        self.elements = []
        self._stack = []
        self._text_stack = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        node = {
            "tag": tag,
            "attrs": attributes,
            "classes": attributes.get("class", "").split(),
            "text": "",
            "parent_classes": list(self._stack[-1]["classes"]) if self._stack else [],
        }
        self.elements.append(node)
        if tag not in VOID_TAGS:
            self._stack.append(node)
        self._text_stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        for index in range(len(self._stack) - 1, -1, -1):
            if self._stack[index]["tag"] == tag:
                del self._stack[index:]
                break

    def handle_data(self, data):
        for node in self._stack:
            node["text"] += data

    def by_tag(self, tag):
        return [element for element in self.elements if element["tag"] == tag]

    def with_class(self, class_name):
        return [e for e in self.elements if class_name in e["classes"]]


def owner_row(display_name="Owner A"):
    return {
        "profile_key": OWNER_A_PROFILE,
        "display_name": display_name,
        "profile_row_version": "01" * 8,
    }


def review_row(item_key, kind, status, minute, token):
    return {
        "item_key": item_key,
        "review_kind": kind,
        "created_at_utc": f"2026-07-20T10:{minute:02d}:00",
        "updated_at_utc": f"2026-07-20T10:{minute + 1:02d}:00",
        "version_token": token * 8,
        "status": status,
    }


def moment_row():
    return {
        "moment_key": MOMENT_A,
        "confirmed_version": 2,
        "title": "A real confirmed Moment",
        "occurred_on": "2026-07-19",
        "updated_at_utc": "2026-07-20T10:40:00",
        "version_token": "05" * 8,
        "status": "confirmed",
    }


def populated_result_sets():
    return [
        [owner_row()],
        [
            review_row(FAILED_A, "voice_draft_failed", "failed", 1, "02"),
            review_row(PROPOSAL_A, "moment_proposal_pending", "proposal", 2, "03"),
            review_row(READY_A, "voice_draft_ready", "needs_review", 3, "04"),
        ],
        [moment_row()],
    ]


def empty_result_sets():
    return [[owner_row()], [], []]


class OwnerHomeAccessibilityTestCase(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self._originals = {
            key: app.config.get(key)
            for key in (
                "PEERSLATE_OWNER_HOME_ENABLED",
                "PEERSLATE_DEV_USER_KEY",
                "PEERSLATE_ALLOW_DEV_IDENTITY",
            )
        }
        app.config["PEERSLATE_OWNER_HOME_ENABLED"] = True
        app.config["PEERSLATE_DEV_USER_KEY"] = "owner-a"
        app.config["PEERSLATE_ALLOW_DEV_IDENTITY"] = True

    def tearDown(self):
        app.config.update(self._originals)

    def render(self, result_sets):
        database = Mock()
        database.execute_procedure.return_value = result_sets
        service = OwnerHomeService(
            database=database,
            clock=lambda: datetime(2026, 7, 20, 11, 0, tzinfo=timezone.utc),
        )
        with patch("auth_routes.owner_home_service") as home_service:
            home_service.get_home.return_value = service.get_home(
                SimpleNamespace(user_key="owner-a")
            )
            response = self.client.get("/app")
        html = response.get_data(as_text=True)
        parser = OwnerHomeDomParser()
        parser.feed(html)
        return response, html, parser

    def render_failure(self):
        with patch("auth_routes.owner_home_service") as home_service:
            home_service.get_home.side_effect = OwnerHomeContractError("x")
            response = self.client.get("/app")
        html = response.get_data(as_text=True)
        parser = OwnerHomeDomParser()
        parser.feed(html)
        return response, html, parser

    # ---- one <h1>, single <main>, skip link ----------------------------

    def assert_single_heading_and_main(self, html, parser):
        self.assertEqual(len(parser.by_tag("h1")), 1, "exactly one <h1> per page")
        main_tags = parser.by_tag("main")
        self.assertEqual(len(main_tags), 1, "no nested <main> (owner_workspace.html defect)")
        self.assertEqual(main_tags[0]["attrs"].get("id"), "main-content")
        self.assertIn('class="skip-link"', html)
        self.assertIn('href="#main-content"', html)

    def test_populated_home_single_heading_and_main(self):
        _, html, parser = self.render(populated_result_sets())
        self.assert_single_heading_and_main(html, parser)

    def test_empty_home_single_heading_and_main(self):
        _, html, parser = self.render(empty_result_sets())
        self.assert_single_heading_and_main(html, parser)

    def test_complete_failure_single_heading_and_main(self):
        _, html, parser = self.render_failure()
        self.assert_single_heading_and_main(html, parser)

    # ---- Coming-later semantics: text, not a link/route -----------------

    def test_coming_later_nav_items_are_not_links(self):
        _, html, parser = self.render(populated_result_sets())

        soon_nav = parser.with_class("oh__nav-item--soon")
        self.assertEqual(len(soon_nav), 4, "Journal / My Slate / Connections / More")
        for node in soon_nav:
            self.assertNotEqual(node["tag"], "a", "a Coming later nav item must not be a link")
            self.assertNotIn("href", node["attrs"])
            self.assertIn("Coming later", node["text"])

        current_nav = parser.with_class("oh__nav-item--current")
        self.assertEqual(len(current_nav), 1)
        self.assertEqual(current_nav[0]["tag"], "a")
        self.assertEqual(current_nav[0]["attrs"].get("aria-current"), "page")

    def test_audience_rail_modes_are_shell_context_not_links(self):
        _, html, parser = self.render(populated_result_sets())

        soon_modes = parser.with_class("oh__mode--soon")
        self.assertEqual(len(soon_modes), 4)
        for node in soon_modes:
            self.assertNotEqual(node["tag"], "a")
            self.assertNotIn("href", node["attrs"])
            self.assertIn("Coming later", node["text"])

    def test_dormant_categories_have_visible_coming_later_text(self):
        _, html, parser = self.render(populated_result_sets())

        for feature in (
            "Resurfaced Moment",
            "What PeerSlate noticed",
            "Connections",
        ):
            self.assertIn(f"{feature}</strong> &mdash; coming later. Not yet available.", html)

        # No fabricated content anywhere in a dormant preview.
        for forbidden in ("Inspect support", "Correct", "Dismiss", "Review permitted update"):
            self.assertNotIn(forbidden, html)

    def test_no_dead_hash_links_and_every_link_has_accessible_text(self):
        _, html, parser = self.render(populated_result_sets())

        for link in parser.by_tag("a"):
            href = link["attrs"].get("href")
            self.assertIsNotNone(href, "every <a> has a real href")
            self.assertNotEqual(href, "#")
            has_label = bool(link["text"].strip()) or bool(
                link["attrs"].get("aria-label")
            )
            self.assertTrue(has_label, f"link to {href} has no accessible name")

    # ---- decorative SVGs are hidden from assistive tech ------------------

    def test_decorative_svgs_are_aria_hidden(self):
        _, html, parser = self.render(populated_result_sets())

        svgs = parser.by_tag("svg")
        self.assertGreater(len(svgs), 0)
        for svg in svgs:
            self.assertEqual(
                svg["attrs"].get("aria-hidden"),
                "true",
                "every decorative <svg> must be aria-hidden",
            )

    # ---- live region + failure alert -------------------------------------

    def test_single_polite_live_region_present(self):
        _, html, parser = self.render(populated_result_sets())

        regions = [n for n in parser.elements if n["attrs"].get("id") == "oh-live-region"]
        self.assertEqual(len(regions), 1)
        self.assertEqual(regions[0]["attrs"].get("role"), "status")
        self.assertEqual(regions[0]["attrs"].get("aria-live"), "polite")

    def test_complete_failure_uses_alert_role_and_keeps_capture(self):
        response, html, parser = self.render_failure()

        self.assertEqual(response.status_code, 503)
        alerts = parser.with_class("oh__failure")
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["attrs"].get("role"), "alert")

        capture_links = [
            a for a in parser.by_tag("a") if a["attrs"].get("href") == "/app/capture"
        ]
        self.assertTrue(capture_links, "Capture stays reachable during complete failure")

        retry_links = [a for a in parser.by_tag("a") if "data-oh-retry" in a["attrs"]]
        self.assertEqual(len(retry_links), 1)
        self.assertTrue(retry_links[0]["text"].strip())

    # ---- status pills / labels are text, never color-only ---------------

    def test_status_pills_carry_visible_text(self):
        _, html, parser = self.render(populated_result_sets())

        pills = [
            e
            for e in parser.elements
            if any(c.startswith("oh__status-pill") for c in e["classes"])
        ]
        self.assertGreaterEqual(len(pills), 3)
        for pill in pills:
            self.assertTrue(pill["text"].strip(), "status pill must carry visible text")

    # ---- Needs Review uses a real list when order/grouping matters ------

    def test_review_items_render_as_an_ordered_list(self):
        _, html, parser = self.render(populated_result_sets())

        lists = parser.with_class("oh__review-list")
        self.assertEqual(len(lists), 1)
        self.assertEqual(lists[0]["tag"], "ol")
        items = parser.with_class("oh__review-item")
        self.assertEqual(len(items), 3, "bounded to the three returned review_items")

    # ---- page-scoped mobile bottom nav (U3) ------------------------------

    def test_mobile_bottom_nav_shape_two_real_three_disabled(self):
        _, html, parser = self.render(populated_result_sets())

        navs = parser.with_class("oh-bottomnav")
        self.assertEqual(len(navs), 1, "exactly one page-scoped bottom nav")

        items = [
            e for e in parser.elements if "oh-bottomnav__item" in e["classes"]
        ]
        self.assertEqual(len(items), 5, "Home, Journal, Capture, Slate, More")
        real = [i for i in items if i["tag"] == "a"]
        soon = [i for i in items if i["tag"] != "a"]
        self.assertEqual(len(real), 2, "Home and Capture are real links")
        self.assertEqual(len(soon), 3, "Journal, Slate, More are disabled text")
        for node in soon:
            self.assertNotIn("href", node["attrs"])
            self.assertIn("Coming later", node["text"])

    # ---- sign-out stays a real POST form, not a bare GET link -----------

    def test_sign_out_is_a_post_form_not_a_link(self):
        _, html, parser = self.render(populated_result_sets())

        forms = parser.with_class("oh__signout")
        self.assertEqual(len(forms), 1)
        self.assertEqual(forms[0]["tag"], "form")
        self.assertEqual(forms[0]["attrs"].get("method"), "post")
        sign_out_links = [
            a for a in parser.by_tag("a") if "sign-out" in (a["attrs"].get("href") or "")
        ]
        self.assertEqual(sign_out_links, [])

    # ---- forced-colors / reduced-motion / focus-visible exist in CSS ----

    def test_stylesheet_declares_required_media_and_focus_rules(self):
        with open("static/css/owner-home.css", encoding="utf-8") as handle:
            css = handle.read()

        self.assertIn("@media (forced-colors: active)", css)
        self.assertIn("@media (prefers-reduced-motion: reduce)", css)
        self.assertIn(":focus-visible", css)
        # 844/540/400(320px reflow correction) breakpoints are present as
        # documented in the frontend architecture (no shared repository
        # breakpoint exists at these widths).
        for width in ("844px", "540px", "400px"):
            self.assertIn(f"max-width: {width}", css)

    def test_forced_colors_block_resets_every_element_not_just_a_few(self):
        # Regression guard: setting `forced-color-adjust: none` on a
        # container class disables the browser's automatic forced-colors
        # text-color correction for its whole subtree (the property is
        # inherited), so every author `color: var(--oh-*)` declared outside
        # the media query (headings, nav, pills, buttons...) must be reset
        # inside it too, or that text renders illegibly (e.g. white-on-white)
        # under Windows High Contrast / forced-colors. The reset must use a
        # selector whose specificity is at least (element + one class) so it
        # beats every single-class `.oh__*` rule above it regardless of
        # source order.
        with open("static/css/owner-home.css", encoding="utf-8") as handle:
            css = handle.read()

        forced_colors_block = css.split("@media (forced-colors: active) {", 1)[1]
        self.assertIn("body.owner-home-shell * {", forced_colors_block[:1200])
        self.assertIn("color: CanvasText;", forced_colors_block[:1200])

    def test_stylesheet_is_route_scoped_under_owner_home_shell(self):
        with open("static/css/owner-home.css", encoding="utf-8") as handle:
            css = handle.read()

        # Deviation D6: every rule lives under the route-scoped body class or
        # a bare --oh-* token; the file never redefines a shared --ps-*/--pv-*
        # token or a bare global selector like `html {` / `body {`.
        self.assertNotRegex(css, r"(?m)^body\s*\{")
        self.assertNotRegex(css, r"--ps-[a-z-]+\s*:")
        self.assertIn("body.owner-home-shell", css)


if __name__ == "__main__":
    unittest.main()
