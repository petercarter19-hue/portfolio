"""PS-SIGNIN-EXPERIENCE-001 — the stylesheet and script contracts.

Layout itself is verified in a real browser (the package's Playwright evidence
records zero overlapping header controls at 320/360/390/414 signed in and out,
and pixel-identical headers from 545px to 1440px against the origin/main
build). These tests pin the small number of declarations that result depends
on, so a later edit cannot quietly undo it.
"""

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_NAV = (ROOT / "static" / "css" / "public-navigation.css").read_text(
    encoding="utf-8"
)
STYLE = (ROOT / "static" / "css" / "style.css").read_text(encoding="utf-8")
OWNER_APP = (ROOT / "static" / "css" / "owner-app.css").read_text(encoding="utf-8")
OWNER_HOME = (ROOT / "static" / "css" / "owner-home.css").read_text(encoding="utf-8")
WAKING_JS = (ROOT / "static" / "js" / "workspace-waking.js").read_text(
    encoding="utf-8"
)


def block(css, opener):
    """Return the source of the first at-rule block introduced by ``opener``."""
    return blocks(css, opener)[0]


def blocks(css, opener):
    """Return every at-rule block introduced by ``opener``."""
    found = []
    search_from = 0
    while True:
        try:
            start = css.index(opener, search_from) + len(opener)
        except ValueError:
            break
        depth = 1
        for index in range(start, len(css)):
            if css[index] == "{":
                depth += 1
            elif css[index] == "}":
                depth -= 1
                if depth == 0:
                    found.append(css[start:index])
                    search_from = index
                    break
        else:
            raise AssertionError(f"unterminated block for {opener!r}")
    if not found:
        raise AssertionError(f"no block found for {opener!r}")
    return found


def declarations(css_block):
    """Strip comments so an assertion cannot be satisfied by prose."""
    return re.sub(r"/\*.*?\*/", "", css_block, flags=re.S)


class HeaderOverlapFixTests(unittest.TestCase):
    """Item 5 — the wordmark may never exceed the column it was given."""

    def test_public_header_wordmark_has_a_percentage_ceiling(self):
        mobile = block(PUBLIC_NAV, "@media (max-width: 64rem) {")
        self.assertIn("max-width: 100%", mobile)
        self.assertIn("object-fit: contain", mobile)
        self.assertIn("min-width: 0", mobile)

    def test_public_header_wordmark_keeps_a_definite_intrinsic_width(self):
        # A percentage max-width is ignored while the browser computes the
        # brand pill's intrinsic width, which made the pill wider than the
        # artwork inside it at every width from 545px up. The definite width
        # is what keeps 545-1024px pixel-identical to the released header.
        mobile = declarations(block(PUBLIC_NAV, "@media (max-width: 64rem) {"))
        self.assertIn("width: 7.6rem", mobile)
        self.assertNotIn("max-width: min(", mobile)

    def test_shared_mobile_header_wordmark_has_the_same_ceiling(self):
        # style.css governs the /app public-shell header, where
        # public-navigation.css is not loaded at all.
        mobile = block(STYLE, "@media (max-width: 743px) {\n    /* The header")
        self.assertIn("max-width: 100%", mobile)
        self.assertIn("object-fit: contain", mobile)

    def test_crowded_row_rules_are_scoped_to_the_widths_that_need_them(self):
        # Everything wider keeps the released header exactly, so the fix must
        # not live in the 64rem/743px mobile blocks.
        for css in (PUBLIC_NAV, STYLE):
            crowded = block(css, "@media (max-width: 34rem) {")
            self.assertIn(".nav-sign-out__btn", crowded)
        crowded_public = block(PUBLIC_NAV, "@media (max-width: 34rem) {")
        self.assertIn(":has(.nav-sign-out:not([hidden]))", crowded_public)
        crowded_shared = block(STYLE, "@media (max-width: 34rem) {")
        self.assertIn("grid-template-columns: auto minmax(0, 1fr)", crowded_shared)
        self.assertIn("flex-wrap: wrap", crowded_shared)

    def test_signed_out_header_is_untouched(self):
        # The signed-out row already fitted. The sign-out form is now always
        # in the DOM (hidden when signed out), so a bare :has(.nav-sign-out)
        # would compact the anonymous header too; every compaction rule must
        # scope to a visible sign-out control.
        crowded = block(PUBLIC_NAV, "@media (max-width: 34rem) {")
        for line in crowded.splitlines():
            stripped = line.strip()
            if not stripped.endswith("{") or stripped.startswith(("/*", "*")):
                continue
            self.assertTrue(
                ":has(.nav-sign-out:not([hidden]))" in stripped
                or ".nav-sign-out__btn" in stripped,
                f"selector not scoped to a visible sign-out control: {stripped}",
            )

    def test_no_header_control_is_removed(self):
        crowded = block(PUBLIC_NAV, "@media (max-width: 34rem) {")
        self.assertNotIn("display: none", crowded)


class WakingStyleTests(unittest.TestCase):
    """Item 2 — the waking surfaces stay quiet, visible, and stoppable."""

    def test_hidden_stop_control_really_is_hidden(self):
        # `display: inline-flex` on these classes outranks the UA
        # `[hidden] { display: none }` rule, so without an explicit guard the
        # stop control would be visible before its script ran, and would stay
        # visible with JavaScript disabled.
        self.assertIn(".oh__btn[hidden]", OWNER_HOME)
        self.assertIn(".owner-app__secondary[hidden]", OWNER_APP)

    def test_the_pulse_respects_reduced_motion(self):
        for css, selector in ((OWNER_HOME, ".oh__waking-dot"),
                              (OWNER_APP, ".owner-app__waking-dot")):
            named = [
                reduce_block
                for reduce_block in blocks(
                    css, "@media (prefers-reduced-motion: reduce) {")
                if selector in reduce_block and "animation: none" in reduce_block
            ]
            self.assertTrue(
                named,
                f"no reduced-motion rule stops the pulse on {selector}",
            )

    def test_the_dot_survives_forced_colors(self):
        for css, selector in ((OWNER_HOME, ".oh__waking-dot"),
                              (OWNER_APP, ".owner-app__waking-dot")):
            self.assertTrue(
                any(selector in forced
                    for forced in blocks(css, "@media (forced-colors: active) {")),
                f"no forced-colors rule keeps {selector} visible",
            )

    def test_owner_home_keeps_exactly_one_forced_colors_block(self):
        # tests/test_owner_home_accessibility.py inspects the first such block
        # in this file; a second one would silently change what it checks.
        self.assertEqual(OWNER_HOME.count("@media (forced-colors: active) {"), 1)

    def test_waking_panel_reuses_the_released_failure_geometry(self):
        # Not a new visual direction: the same panel, saying something true.
        # The only additions are the eyebrow dot and the status line, so the
        # modifier class must not acquire geometry, colour, or type of its own.
        self.assertNotIn(".oh__failure--waking {", OWNER_HOME)
        stage = (ROOT / "templates" / "partials" / "owner_home"
                 / "_stage.html").read_text(encoding="utf-8")
        self.assertIn('class="oh__failure oh__failure--waking"', stage)
        # The contract failure stays assertive; a transient wake-up must not.
        self.assertIn('class="oh__failure" role="alert"', stage)
        self.assertNotIn('oh__failure--waking"\n                role="alert"', stage)


class WakingScriptTests(unittest.TestCase):
    """Item 2.2 — the automatic re-check is bounded, stoppable, and quiet."""

    def test_the_retry_window_is_bounded(self):
        self.assertIn("budgetSeconds", WAKING_JS)
        self.assertIn("stopAutomaticChecking", WAKING_JS)
        # A hard ceiling even if the server ever sent something unreasonable.
        self.assertIn("budgetSeconds > 600", WAKING_JS)

    def test_the_backoff_grows_and_is_finite(self):
        delays = re.search(r"DELAYS_SECONDS = \[([^\]]+)\]", WAKING_JS)
        self.assertIsNotNone(delays)
        values = [int(value) for value in delays.group(1).split(",")]
        self.assertGreater(len(values), 1)
        self.assertEqual(values, sorted(values))
        self.assertGreaterEqual(values[0], 3)

    def test_it_only_ever_re_requests_a_same_origin_path(self):
        self.assertIn("retryUrl.charAt(0) !== '/'", WAKING_JS)
        self.assertIn("retryUrl.charAt(1) === '/'", WAKING_JS)

    def test_it_writes_no_markup_and_evaluates_nothing(self):
        for forbidden in ("innerHTML", "outerHTML", "eval(", "document.write",
                          "insertAdjacentHTML"):
            self.assertNotIn(forbidden, WAKING_JS)

    def test_it_stores_nothing_but_its_own_retry_bookkeeping(self):
        self.assertNotIn("localStorage", WAKING_JS)
        self.assertIn("sessionStorage", WAKING_JS)
        self.assertIn("ps-waking:", WAKING_JS)

    def test_it_makes_no_network_request_of_its_own(self):
        # Re-checking is a plain navigation to the same protected route; this
        # script never fetches a member payload.
        self.assertNotIn("fetch(", WAKING_JS)
        self.assertNotIn("XMLHttpRequest", WAKING_JS)

    def test_it_never_navigates_out_from_under_a_keyboard_user(self):
        self.assertIn("root.contains(document.activeElement)", WAKING_JS)


if __name__ == "__main__":
    unittest.main()
