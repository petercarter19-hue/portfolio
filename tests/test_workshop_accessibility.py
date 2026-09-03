"""Workshop accessibility, reflow, and deterministic local-browser contracts.

The ordinary suite exercises rendered HTML without importing Playwright. The
explicit browser proof runs this file in a child process, so optional browser
modules cannot leak into later sealed/runtime tests. Set
``PEERSLATE_RUN_WORKSHOP_BROWSER=1`` and provide a lifecycle-allocated external
``PEERSLATE_WORKSHOP_EVIDENCE_DIR`` to run it. No live URL, identity, provider,
or credential is used.
"""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from werkzeug.serving import make_server

from app import app, limiter
from services import workshop_work_session as wws


SAME_ORIGIN_HEADERS = {
    "Origin": "http://localhost",
    "Sec-Fetch-Site": "same-origin",
}
WORKSHOP_VIEWPORTS = (
    ("desktop-1440", 1440, 1000),
    ("tablet-1024", 1024, 900),
    ("tablet-768", 768, 900),
    ("zoom-200-640", 640, 900),
    ("phone-390", 390, 844),
    ("zoom-400-320", 320, 800),
)


class _OutlineParser(HTMLParser):
    """Collect structural landmarks/headings without a third-party parser."""

    def __init__(self):
        super().__init__()
        self.main_ids = []
        self.heading_classes = {"h1": [], "h2": []}

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "main":
            self.main_ids.append(attributes.get("id"))
        if tag in self.heading_classes:
            self.heading_classes[tag].append(attributes.get("class", ""))


class RenderedWorkshopOutlineTests(unittest.TestCase):
    """The canonical shared main and Workshop hero own each rendered view."""

    MISSING = object()
    CONFIG_KEYS = (
        "TESTING",
        "PEERSLATE_ALLOW_DEV_IDENTITY",
        "PEERSLATE_DEV_USER_KEY",
        "PEERSLATE_WORKSHOP_ENABLED",
        "PEERSLATE_WORKSHOP_SESSION_ENABLED",
        "PEERSLATE_WORKSHOP_DEV_FIXTURE",
    )

    def setUp(self):
        self.original = {
            key: app.config[key] if key in app.config else self.MISSING
            for key in self.CONFIG_KEYS
        }
        app.config.update(
            TESTING=True,
            PEERSLATE_ALLOW_DEV_IDENTITY=False,
            PEERSLATE_DEV_USER_KEY=None,
            PEERSLATE_WORKSHOP_ENABLED=True,
            PEERSLATE_WORKSHOP_SESSION_ENABLED=True,
            PEERSLATE_WORKSHOP_DEV_FIXTURE=False,
        )
        self.original_limiter = limiter.enabled
        limiter.enabled = False
        self.original_instance_path = app.instance_path
        self.instance_dir = tempfile.mkdtemp(prefix="ps-workshop-a11y-")
        app.instance_path = self.instance_dir
        self.spark_patch = patch(
            "workshop_work_routes._resolve_opening_spark",
            return_value=(None, None),
        )
        self.spark_patch.start()
        self.client = app.test_client()

    def tearDown(self):
        self.spark_patch.stop()
        app.instance_path = self.original_instance_path
        shutil.rmtree(self.instance_dir, ignore_errors=True)
        limiter.enabled = self.original_limiter
        for key, value in self.original.items():
            if value is self.MISSING:
                app.config.pop(key, None)
            else:
                app.config[key] = value

    def assert_outline(self, response, local_h2=None):
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")
        parser = _OutlineParser()
        parser.feed(response.get_data(as_text=True))
        self.assertEqual(parser.main_ids, ["main-content"])
        self.assertEqual(parser.heading_classes["h1"], ["wk-hero__title"])
        if local_h2:
            self.assertIn(local_h2, parser.heading_classes["h2"])

    def test_library_and_work_opening_have_one_main_and_one_h1(self):
        self.assert_outline(self.client.get("/app/workshop"))
        self.assert_outline(
            self.client.get("/app/workshop/work"),
            "wk-work-composer__title",
        )

    def test_session_and_review_keep_the_same_heading_ownership(self):
        started = self.client.post(
            "/app/workshop/work/start",
            data={"door": wws.DOOR_SOMETHING, "thought": "A local fixture thought."},
            headers=SAME_ORIGIN_HEADERS,
        )
        self.assertEqual(started.status_code, 302)
        self.assert_outline(
            self.client.get("/app/workshop/work/session"),
            "wk-session-question",
        )

        review = {
            "interpretation": "A local interpretation.",
            "strong": ["Clear ownership"],
            "standout": "One grounded detail.",
            "strengthen": "Add a measurable result.",
            "question": "What changed afterward?",
        }
        with patch(
            "workshop_work_routes.workshop_review_service.generate_review",
            return_value=(review, "{}", "end_turn"),
        ):
            response = self.client.post(
                "/app/workshop/work/session/review",
                data={"answer": "A local fixture answer."},
                headers=SAME_ORIGIN_HEADERS,
            )
        self.assert_outline(response, "wk-flow-title")

    def test_rendered_fixture_suggestion_actions_use_the_hidden_css_contract(self):
        """The unclaimed fixture partial still emits three dead anchors.

        The claimed Workshop stylesheet must remove that exact rendered shape
        from presentation and focus until the future suggestion capability is
        real; broad aria-disabled suppression would hide legitimate states.
        """
        app.config.update(
            PEERSLATE_ALLOW_DEV_IDENTITY=True,
            PEERSLATE_DEV_USER_KEY="workshop-accessibility-fixture",
            PEERSLATE_WORKSHOP_DEV_FIXTURE=True,
        )
        response = self.client.get("/app/workshop")
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        suggestion = body.split('<section class="wk-suggestion"', 1)[1].split(
            "</section>", 1
        )[0]
        self.assertEqual(suggestion.count("<a "), 3)
        self.assertEqual(suggestion.count('href="#" aria-disabled="true"'), 3)

        css = (ROOT / "static/css/workshop.css").read_text(encoding="utf-8")
        selector = '.wk-suggestion > a[href="#"][aria-disabled="true"] {'
        start = css.index(selector)
        rule = css[start : css.index("}", start)]
        self.assertIn("display: none;", rule)


def _resolve_chrome():
    candidates = (
        shutil.which("google-chrome"),
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
    )
    return next((path for path in candidates if path and Path(path).is_file()), None)


def _browser_check(page, label, *, expect_fixture_suggestion=False):
    """Fail on structural, reflow, or active-target regressions."""

    result = page.evaluate(
        """() => {
            const visible = (element) => {
                const style = getComputedStyle(element);
                const rect = element.getBoundingClientRect();
                return style.display !== 'none' && style.visibility !== 'hidden' &&
                    rect.width > 0 && rect.height > 0;
            };
            const selector = [
                '.wk a[href]:not([aria-disabled="true"])',
                '.wk button:not(:disabled)',
                '.wk summary',
                '.wk input:not([type="hidden"]):not([type="checkbox"]):not([type="radio"])',
                '.wk textarea',
                '.wk label.wk-choice',
                '.wk label.wk-context-item__body'
            ].join(',');
            const targetViolations = [...document.querySelectorAll(selector)]
                .filter(visible)
                .map((element) => {
                    const rect = element.getBoundingClientRect();
                    return {
                        tag: element.tagName,
                        className: element.className,
                        width: rect.width,
                        height: rect.height,
                    };
                })
                .filter((item) => item.width < 43.5 || item.height < 43.5);
            const deadSuggestionActions = [...document.querySelectorAll(
                '.wk-suggestion > a[href="#"][aria-disabled="true"]'
            )];
            const deadSuggestionStates = deadSuggestionActions.map((element) => ({
                display: getComputedStyle(element).display,
                visible: visible(element),
                sequentiallyFocusable: visible(element) && !element.disabled &&
                    element.tabIndex >= 0,
            }));
            const eyebrow = document.querySelector('.wk-suggestion__eyebrow');
            const fragmentedEyebrowWords = [];
            if (eyebrow && eyebrow.firstChild && eyebrow.firstChild.nodeType === Node.TEXT_NODE) {
                const node = eyebrow.firstChild;
                for (const match of node.textContent.matchAll(/\\S+/g)) {
                    const range = document.createRange();
                    range.setStart(node, match.index);
                    range.setEnd(node, match.index + match[0].length);
                    if (range.getClientRects().length > 1) {
                        fragmentedEyebrowWords.push(match[0]);
                    }
                }
            }
            return {
                mains: document.querySelectorAll('main#main-content').length,
                h1s: document.querySelectorAll('main#main-content h1').length,
                workshopH1s: document.querySelectorAll('.wk h1.wk-hero__title').length,
                scrollWidth: document.documentElement.scrollWidth,
                clientWidth: document.documentElement.clientWidth,
                targetViolations,
                deadSuggestionActions: {
                    count: deadSuggestionActions.length,
                    states: deadSuggestionStates,
                },
                fragmentedEyebrowWords,
            };
        }"""
    )
    if result["mains"] != 1 or result["h1s"] != 1 or result["workshopH1s"] != 1:
        raise AssertionError(f"{label}: invalid main/H1 structure: {result}")
    if result["scrollWidth"] > result["clientWidth"] + 1:
        raise AssertionError(f"{label}: horizontal overflow: {result}")
    if result["targetViolations"]:
        raise AssertionError(f"{label}: sub-44px active targets: {result['targetViolations']}")
    dead = result["deadSuggestionActions"]
    if expect_fixture_suggestion and dead["count"] != 3:
        raise AssertionError(f"{label}: expected three fixture suggestion actions: {dead}")
    if any(item["visible"] or item["sequentiallyFocusable"] for item in dead["states"]):
        raise AssertionError(f"{label}: dead suggestion action remained exposed: {dead}")
    if result["fragmentedEyebrowWords"]:
        raise AssertionError(
            f"{label}: suggestion eyebrow split words: {result['fragmentedEyebrowWords']}"
        )
    return result


def _keyboard_sequence_check(page, label):
    """Traverse every Workshop tab stop and prove focus is visible/uncovered."""

    # Exercise the worst case: both shared-shell sticky surfaces stay visible
    # while focus moves through Workshop. This changes proof presentation only;
    # it does not change application state or click/submit any control.
    page.add_style_tag(
        content="#mobile-tabbar { transform: none !important; transition: none !important; }"
    )
    expected = page.evaluate(
        """() => [...document.querySelectorAll(
            '.wk a[href], .wk button, .wk summary, .wk input, .wk textarea, '
            + '.wk select, .wk [tabindex]'
        )].filter((element) => {
            const style = getComputedStyle(element);
            const rect = element.getBoundingClientRect();
            return !element.disabled && element.tabIndex >= 0 &&
                style.display !== 'none' && style.visibility !== 'hidden' &&
                rect.width > 0 && rect.height > 0;
        }).map((element) => [...document.querySelectorAll('*')].indexOf(element))"""
    )
    if not expected:
        raise AssertionError(f"{label}: no Workshop keyboard stops found")

    page.evaluate(
        """() => {
            if (document.activeElement instanceof HTMLElement) {
                document.activeElement.blur();
            }
            window.scrollTo(0, 0);
        }"""
    )

    visited = []
    violations = []
    first_document_index = None
    # Shared header and phone-bar stops are deliberately included in the Tab
    # cycle but not judged by Workshop-local CSS. Two full-document cycles is
    # ample even when both menus expose their server-rendered fallback links.
    for _ in range(max(80, len(expected) * 4)):
        page.keyboard.press("Tab")
        result = page.evaluate(
            """() => {
                const active = document.activeElement;
                if (!(active instanceof HTMLElement)) return null;
                const all = [...document.querySelectorAll('*')];
                const documentIndex = all.indexOf(active);
                const inWorkshop = Boolean(active.closest('.wk'));
                if (!inWorkshop) return {documentIndex, inWorkshop};

                const candidates = [active];
                if (active.labels) candidates.push(...active.labels);
                const containingLabel = active.closest('label');
                if (containingLabel) candidates.push(containingLabel);
                const ring = candidates.find((element) => {
                    const style = getComputedStyle(element);
                    return style.outlineStyle !== 'none' &&
                        parseFloat(style.outlineWidth || '0') >= 2;
                });
                const target = ring || active;
                const rect = target.getBoundingClientRect();
                const header = document.querySelector('.global-header');
                const bar = document.querySelector('#mobile-tabbar');
                const headerRect = header ? header.getBoundingClientRect() : null;
                const barRect = bar ? bar.getBoundingClientRect() : null;
                const headerVisible = headerRect && headerRect.bottom > 0 &&
                    headerRect.top < innerHeight && getComputedStyle(header).display !== 'none';
                const barVisible = barRect && barRect.bottom > 0 &&
                    barRect.top < innerHeight && getComputedStyle(bar).display !== 'none';
                const topLimit = headerVisible ? Math.max(0, headerRect.bottom) : 0;
                const bottomLimit = barVisible ? Math.min(innerHeight, barRect.top) : innerHeight;
                return {
                    documentIndex,
                    inWorkshop,
                    tag: active.tagName,
                    id: active.id,
                    className: active.className,
                    ring: Boolean(ring),
                    outlineWidth: ring ? getComputedStyle(ring).outlineWidth : '0px',
                    top: rect.top,
                    bottom: rect.bottom,
                    topLimit,
                    bottomLimit,
                    obscured: rect.top < topLimit - 0.5 || rect.bottom > bottomLimit + 0.5,
                };
            }"""
        )
        if result is None:
            continue
        document_index = result["documentIndex"]
        if first_document_index is None:
            first_document_index = document_index
        elif document_index == first_document_index:
            break
        if not result["inWorkshop"]:
            continue
        visited.append(document_index)
        if not result["ring"] or result["obscured"]:
            violations.append(result)
    else:
        raise AssertionError(f"{label}: keyboard sequence did not wrap")

    missing = sorted(set(expected) - set(visited))
    if missing or violations:
        raise AssertionError(
            f"{label}: missing stops={missing}; focus violations={violations}"
        )
    return {
        "expectedStops": len(set(expected)),
        "visitedStops": len(set(visited)),
        "violations": violations,
    }


def _new_page(browser, *, width, height, java_script_enabled=True):
    context = browser.new_context(
        viewport={"width": width, "height": height},
        java_script_enabled=java_script_enabled,
        reduced_motion="reduce",
    )
    page = context.new_page()
    page.route("https://fonts.**", lambda route: route.abort())
    return context, page


def _goto(page, base_url, route):
    response = page.goto(f"{base_url}{route}", wait_until="load")
    if response is None or response.status != 200:
        status = None if response is None else response.status
        raise AssertionError(f"{route}: expected local 200, got {status}")


def _capture(page, evidence_dir, name):
    output = evidence_dir / name
    page.screenshot(path=str(output), full_page=True)
    return output.name


def _run_browser_worker(evidence_value):
    """Run only in the short-lived child process used for explicit proof."""

    from playwright.sync_api import sync_playwright

    evidence_dir = Path(evidence_value).resolve()
    if not evidence_dir.is_dir():
        raise AssertionError("the lifecycle-allocated evidence directory must exist")
    if evidence_dir == ROOT or ROOT in evidence_dir.parents:
        raise AssertionError("browser evidence must be outside the repository")

    config_keys = (
        "TESTING",
        "PEERSLATE_ALLOW_DEV_IDENTITY",
        "PEERSLATE_DEV_USER_KEY",
        "PEERSLATE_WORKSHOP_ENABLED",
        "PEERSLATE_WORKSHOP_SESSION_ENABLED",
        "PEERSLATE_WORKSHOP_DEV_FIXTURE",
    )
    missing = object()
    original = {
        key: app.config[key] if key in app.config else missing for key in config_keys
    }
    original_limiter = limiter.enabled
    original_instance_path = app.instance_path
    instance_dir = tempfile.mkdtemp(prefix="ps-workshop-browser-")
    app.instance_path = instance_dir
    limiter.enabled = False
    app.config.update(
        TESTING=True,
        PEERSLATE_WORKSHOP_ENABLED=True,
        PEERSLATE_WORKSHOP_SESSION_ENABLED=True,
        PEERSLATE_WORKSHOP_DEV_FIXTURE=False,
        PEERSLATE_ALLOW_DEV_IDENTITY=False,
        PEERSLATE_DEV_USER_KEY=None,
    )

    review = {
        "interpretation": "A deterministic local interpretation.",
        "strong": ["Clear ownership"],
        "standout": "One grounded detail.",
        "strengthen": "Add a measurable result.",
        "question": "What changed afterward?",
    }
    spark_patch = patch(
        "workshop_work_routes._resolve_opening_spark", return_value=(None, None)
    )
    review_patch = patch(
        "workshop_work_routes.workshop_review_service.generate_review",
        return_value=(review, "{}", "end_turn"),
    )
    server = make_server("127.0.0.1", 0, app)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}"
    captures = []
    checks = []

    try:
        spark_patch.start()
        review_patch.start()
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                executable_path=_resolve_chrome(),
                headless=True,
            )
            try:
                # Signed-out shared-shell baseline.
                context, page = _new_page(browser, width=1440, height=1000)
                try:
                    _goto(page, base_url, "/app/workshop")
                    checks.append(_browser_check(page, "signed-out-shell"))
                    captures.append(_capture(page, evidence_dir, "signed-out-shell-1440.png"))
                finally:
                    context.close()

                # Local generic authenticated fixture: no identity/provider service.
                app.config.update(
                    PEERSLATE_ALLOW_DEV_IDENTITY=True,
                    PEERSLATE_DEV_USER_KEY="workshop-accessibility-fixture",
                    PEERSLATE_WORKSHOP_DEV_FIXTURE=True,
                )
                for name, width, height in WORKSHOP_VIEWPORTS:
                    context, page = _new_page(browser, width=width, height=height)
                    try:
                        _goto(page, base_url, "/app/workshop")
                        checks.append(
                            _browser_check(
                                page,
                                name,
                                expect_fixture_suggestion=True,
                            )
                        )
                        captures.append(
                            _capture(page, evidence_dir, f"populated-library-{name}.png")
                        )
                    finally:
                        context.close()

                context, page = _new_page(browser, width=768, height=900)
                try:
                    _goto(page, base_url, "/app/workshop?_dev_state=empty")
                    checks.append(_browser_check(page, "empty-library"))
                    captures.append(_capture(page, evidence_dir, "empty-library-768.png"))
                finally:
                    context.close()

                # Return to the anonymous session-only flow for form and W2 proof.
                app.config.update(
                    PEERSLATE_ALLOW_DEV_IDENTITY=False,
                    PEERSLATE_DEV_USER_KEY=None,
                    PEERSLATE_WORKSHOP_DEV_FIXTURE=False,
                )
                context, page = _new_page(browser, width=768, height=900)
                try:
                    _goto(page, base_url, "/app/workshop/add")
                    checks.append(_browser_check(page, "add"))
                    captures.append(_capture(page, evidence_dir, "add-768.png"))
                    page.locator("#wk-title").fill("A deterministic local title")
                    page.locator("#wk-wording").fill(
                        "A deterministic local wording used only in this browser session."
                    )
                    page.get_by_role("button", name="Continue").click()
                    page.wait_for_load_state("load")
                    checks.append(_browser_check(page, "review"))
                    captures.append(_capture(page, evidence_dir, "review-768.png"))
                    page.get_by_role("button", name="Save privately").click()
                    page.wait_for_load_state("load")
                    checks.append(_browser_check(page, "saved"))
                    captures.append(_capture(page, evidence_dir, "saved-detail-768.png"))
                finally:
                    context.close()

                context, page = _new_page(browser, width=390, height=844)
                try:
                    _goto(page, base_url, "/app/workshop/work")
                    checks.append(_browser_check(page, "work-opening"))
                    captures.append(_capture(page, evidence_dir, "work-opening-390.png"))
                    page.locator("#wk-work-thought").fill("A local W2 starting thought.")
                    page.locator(".wk-work-composer__submit").click()
                    page.wait_for_load_state("load")
                    checks.append(_browser_check(page, "work-session"))
                    captures.append(_capture(page, evidence_dir, "work-session-390.png"))
                    page.locator("#wk-session-answer").fill("A local W2 answer.")
                    page.get_by_role("button", name="Review what I shared").click()
                    page.wait_for_load_state("load")
                    checks.append(_browser_check(page, "work-review"))
                    captures.append(_capture(page, evidence_dir, "work-review-390.png"))
                finally:
                    context.close()

                context, page = _new_page(browser, width=390, height=844)
                try:
                    page.emulate_media(forced_colors="active")
                    _goto(page, base_url, "/app/workshop")
                    checks.append(_browser_check(page, "forced-colors"))
                    captures.append(_capture(page, evidence_dir, "forced-colors-390.png"))
                finally:
                    context.close()

                context, page = _new_page(
                    browser,
                    width=390,
                    height=844,
                    java_script_enabled=False,
                )
                try:
                    _goto(page, base_url, "/app/workshop/work")
                    page.locator("#wk-work-thought").fill("A no-JavaScript local thought.")
                    page.locator(".wk-work-composer__submit").click()
                    page.wait_for_load_state("load")
                    if not page.url.endswith("/app/workshop/work/session"):
                        raise AssertionError("the no-JavaScript core POST did not reach session")
                    if page.locator(".wk-mic-btn:not(:disabled)").count():
                        raise AssertionError("an unavailable no-JavaScript mic remained active")
                    checks.append(_browser_check(page, "javascript-off"))
                    captures.append(
                        _capture(page, evidence_dir, "javascript-off-session-390.png")
                    )
                finally:
                    context.close()

                app.config.update(
                    PEERSLATE_ALLOW_DEV_IDENTITY=True,
                    PEERSLATE_DEV_USER_KEY="workshop-accessibility-fixture",
                    PEERSLATE_WORKSHOP_DEV_FIXTURE=True,
                )
                context, page = _new_page(browser, width=390, height=844)
                try:
                    _goto(page, base_url, "/app/workshop")
                    page.locator("#wk-search-input").focus()
                    focus = page.locator("#wk-search-input").evaluate(
                        """element => {
                            const style = getComputedStyle(element);
                            const rect = element.getBoundingClientRect();
                            return {width: style.outlineWidth, style: style.outlineStyle,
                                    top: rect.top, bottom: rect.bottom,
                                    viewport: window.innerHeight};
                        }"""
                    )
                    if focus["style"] == "none" or float(focus["width"].rstrip("px")) < 3:
                        raise AssertionError(f"search focus ring is not visible: {focus}")
                    if focus["top"] < 0 or focus["bottom"] > focus["viewport"]:
                        raise AssertionError(f"focused search is obscured: {focus}")
                    captures.append(_capture(page, evidence_dir, "keyboard-focus-390.png"))
                    checks.append(
                        _keyboard_sequence_check(page, "keyboard-sequence-library")
                    )

                    page.set_viewport_size({"width": 320, "height": 800})
                    page.evaluate(
                        """() => {
                            const longText = 'Long local fixture wording '.repeat(18);
                            document.querySelectorAll('.wk-list__item-title, .wk-detail__title, .wk-detail__body')
                                .forEach((element) => { element.textContent = longText; });
                            const root = document.querySelector('.wk');
                            root.style.lineHeight = '1.5';
                            root.style.letterSpacing = '0.12em';
                            root.style.wordSpacing = '0.16em';
                        }"""
                    )
                    checks.append(
                        _browser_check(
                            page,
                            "long-text-spacing",
                            expect_fixture_suggestion=True,
                        )
                    )
                    captures.append(
                        _capture(page, evidence_dir, "long-text-spacing-320.png")
                    )
                finally:
                    context.close()
            finally:
                browser.close()
    finally:
        review_patch.stop()
        spark_patch.stop()
        server.shutdown()
        server_thread.join(timeout=5)
        app.instance_path = original_instance_path
        shutil.rmtree(instance_dir, ignore_errors=True)
        limiter.enabled = original_limiter
        for key, value in original.items():
            if value is missing:
                app.config.pop(key, None)
            else:
                app.config[key] = value

    return {"captures": captures, "capture_count": len(captures), "check_count": len(checks)}


@unittest.skipUnless(
    os.environ.get("PEERSLATE_RUN_WORKSHOP_BROWSER") == "1",
    "set PEERSLATE_RUN_WORKSHOP_BROWSER=1 for the isolated local browser proof",
)
class IsolatedWorkshopBrowserProofTests(unittest.TestCase):
    def test_reflow_focus_targets_forced_colours_and_no_js_capture_matrix(self):
        if importlib.util.find_spec("playwright") is None or _resolve_chrome() is None:
            self.skipTest("Playwright and Chrome are required for Workshop browser proof")
        evidence = os.environ.get("PEERSLATE_WORKSHOP_EVIDENCE_DIR")
        self.assertTrue(evidence, "a lifecycle-allocated external evidence path is required")
        evidence_path = Path(evidence).resolve()
        self.assertTrue(evidence_path.is_dir())
        self.assertNotEqual(evidence_path, ROOT)
        self.assertNotIn(ROOT, evidence_path.parents)

        environment = dict(os.environ)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        result = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "--browser-worker", evidence],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        summary = json.loads(result.stdout.strip().splitlines()[-1])
        self.assertEqual(summary["capture_count"], 18)
        self.assertEqual(summary["check_count"], 18)


if __name__ == "__main__" and len(sys.argv) == 3 and sys.argv[1] == "--browser-worker":
    print(json.dumps(_run_browser_worker(sys.argv[2]), sort_keys=True))
elif __name__ == "__main__":
    unittest.main()
