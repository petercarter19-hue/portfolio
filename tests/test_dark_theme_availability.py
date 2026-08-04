"""Owner-directed dark theme pause (Pete, 2026-08-03).

    "no dark theme for now. We are turning it off for the time being on the
     site... if it's already implemented, no problem."

A pause, not a removal. Two things must both stay true:

1. No visitor can land on, switch to, or be defaulted into dark. There were
   several independent routes into dark, and each one is closed here.
2. The dark CSS is still in the repository, dormant, so restoring the theme is
   one flag flip rather than a rebuild.

The single switch is ``PEERSLATE_DARK_THEME_ENABLED``, declared in ``app.py``
and defaulting to false.
"""

import os
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from werkzeug.serving import make_server

from app import app

try:
    from playwright.sync_api import sync_playwright
except ModuleNotFoundError:
    sync_playwright = None

try:
    from scripts.capture_ps_journal_j1_evidence import _resolve_chrome

    CHROME_EXECUTABLE = _resolve_chrome()
except Exception:  # pragma: no cover - the evidence helper is optional here
    CHROME_EXECUTABLE = None


CONFIG_KEY = 'PEERSLATE_DARK_THEME_ENABLED'
REPO_ROOT = os.path.join(os.path.dirname(__file__), '..')
STUDIO_ROUTE = '/app/studio/build-your-future'

# Every stylesheet that still carries a dormant dark rule set. The pause must
# not delete any of them: a future writer restores the theme by flipping the
# flag, not by rewriting these files.
DORMANT_DARK_STYLESHEETS = (
    'community-tabs.css',
    'editorial-glass.css',
    'feed-living-stream.css',
    'homepage-scenes.css',
    'interview-studio.css',
    'journal.css',
    'living-resume-v2.css',
    'owner-app.css',
    'owner-studio.css',
    'people-interests.css',
    'resume2.css',
    'skills-cinematic.css',
    'sky-glass.css',
    'slate-board.css',
    'story-acts.css',
    'style.css',
    'workshop.css',
)


def read_repo_file(*parts):
    with open(os.path.join(REPO_ROOT, *parts), encoding='utf-8') as handle:
        return handle.read()


class DarkThemeAvailabilityTests(unittest.TestCase):
    CONFIG_KEY = CONFIG_KEY

    def setUp(self):
        self.client = app.test_client()
        self._missing = object()
        self._original = app.config.get(self.CONFIG_KEY, self._missing)

    def tearDown(self):
        if self._original is self._missing:
            app.config.pop(self.CONFIG_KEY, None)
        else:
            app.config[self.CONFIG_KEY] = self._original

    def html(self, path):
        response = self.client.get(path, base_url='http://localhost')
        self.assertEqual(response.status_code, 200)
        return response.get_data(as_text=True)

    def test_shared_public_theme_is_unavailable_by_default(self):
        self.assertIs(app.config.get(self.CONFIG_KEY, False), False)

        for path in ('/', '/petec/resume', '/interview-studio'):
            with self.subTest(path=path):
                html = self.html(path)
                self.assertIn('data-theme="modern-blue"', html)
                self.assertNotIn('id="theme-toggle"', html)
                self.assertNotIn('data-theme-toggle-proxy', html)
                self.assertNotIn('js/theme-toggle.js', html)
                self.assertNotIn("localStorage.getItem('ps-theme')", html)

    def test_internal_override_restores_the_existing_theme_contract(self):
        app.config[self.CONFIG_KEY] = True

        homepage = self.html('/')
        self.assertEqual(homepage.count('id="theme-toggle"'), 1)
        self.assertEqual(homepage.count('data-theme-toggle-proxy'), 1)
        self.assertEqual(homepage.count('js/theme-toggle.js'), 1)
        self.assertEqual(homepage.count("localStorage.getItem('ps-theme')"), 1)

        interview = self.html('/interview-studio')
        self.assertEqual(interview.count('id="theme-toggle"'), 1)
        self.assertEqual(interview.count('data-theme-toggle-proxy'), 3)
        self.assertEqual(interview.count('js/theme-toggle.js'), 1)
        self.assertEqual(interview.count("localStorage.getItem('ps-theme')"), 1)

    def test_the_switch_has_one_declared_home(self):
        """A missing key defaults to false, but the switch is not implicit.

        Declaring it in app.py gives a future writer one obvious place to flip
        and keeps a second, competing dark-theme flag from appearing.
        """
        source = read_repo_file('app.py')
        self.assertIn('PEERSLATE_DARK_THEME_ENABLED=(', source)
        self.assertIn(
            "os.environ.get('PEERSLATE_DARK_THEME_ENABLED', 'false').lower() == 'true'",
            source,
        )
        self.assertIs(app.config[self.CONFIG_KEY], False)

    def test_no_shell_emits_the_dark_theme_gate_by_default(self):
        for path in ('/', '/petec/resume', '/interview-studio'):
            with self.subTest(path=path):
                html = self.html(path)
                self.assertNotIn('data-ps-dark-theme', html)
                self.assertNotIn('data-theme="dark"', html)

    def test_the_gate_returns_with_the_flag(self):
        app.config[self.CONFIG_KEY] = True
        self.assertIn('data-ps-dark-theme="on"', self.html('/'))


class StudioShellPauseTests(unittest.TestCase):
    """The Slate Studio shell does not extend base.html.

    It carried its own stored-preference replay and its own theme switch, so
    the public-shell gate did not reach it. A member who chose dark before the
    pause would still have landed dark here.
    """

    def setUp(self):
        self.client = app.test_client()
        self.original_studio = app.config.get(
            'PEERSLATE_SLATE_STUDIO_SLICE1_ENABLED')
        self.original_theme = app.config.get(CONFIG_KEY)
        app.config['PEERSLATE_SLATE_STUDIO_SLICE1_ENABLED'] = True

    def tearDown(self):
        app.config['PEERSLATE_SLATE_STUDIO_SLICE1_ENABLED'] = self.original_studio
        app.config[CONFIG_KEY] = self.original_theme

    def render(self):
        identity = SimpleNamespace(
            display_name='Avery Member', user_key='owner-avery')
        with patch('auth_routes.get_current_identity', return_value=identity):
            response = self.client.get(STUDIO_ROUTE)
        self.assertEqual(response.status_code, 200)
        return response.get_data(as_text=True)

    def test_studio_ships_no_theme_control_or_stored_replay_by_default(self):
        html = self.render()
        self.assertNotIn('id="theme-toggle"', html)
        self.assertNotIn('ss-theme-toggle', html)
        self.assertNotIn("localStorage.getItem('ps-theme')", html)
        self.assertNotIn('js/theme-toggle.js', html)
        self.assertNotIn('data-ps-dark-theme', html)
        self.assertIn('data-theme="modern-blue"', html)
        # The no-JavaScript promise is unchanged and now unconditionally true.
        self.assertIn(
            'Build Your Future works without JavaScript. '
            'The page remains in its default light theme.',
            html,
        )

    def test_studio_theme_contract_returns_with_the_flag(self):
        app.config[CONFIG_KEY] = True
        html = self.render()
        self.assertEqual(html.count('id="theme-toggle"'), 1)
        self.assertIn('data-theme-toggle-requires-js', html)
        self.assertEqual(html.count("localStorage.getItem('ps-theme')"), 1)
        self.assertEqual(html.count('js/theme-toggle.js'), 1)
        self.assertIn('data-ps-dark-theme="on"', html)
        self.assertIn(
            'onload="document.getElementById(\'theme-toggle\').hidden = false"',
            html,
        )


class OperatingSystemDarkPreferenceTests(unittest.TestCase):
    """prefers-color-scheme needs no user action at all.

    Hiding every switch does nothing about a visitor whose operating system is
    set to dark, so this route is closed in CSS.
    """

    def test_the_site_declares_light_behind_a_self_releasing_gate(self):
        style = read_repo_file('static', 'css', 'style.css')
        self.assertIn(
            ':root:not([data-ps-dark-theme]) {\n    color-scheme: light;\n}',
            style,
        )

    def test_the_control_rooms_os_driven_variant_is_gated(self):
        css = read_repo_file('static', 'css', 'control-room.css')
        self.assertEqual(css.count('@media (prefers-color-scheme: dark)'), 1)
        self.assertIn(
            '@media (prefers-color-scheme: dark) {\n    :root[data-ps-dark-theme] {',
            css,
        )
        self.assertIn(':root:not([data-ps-dark-theme]) {', css)

        template = read_repo_file('templates', 'control_room.html')
        self.assertIn(
            "<html lang=\"en\"{% if config.get('PEERSLATE_DARK_THEME_ENABLED', "
            'false) %} data-ps-dark-theme="on"{% endif %}>',
            template,
        )

    def test_no_other_stylesheet_reintroduces_an_os_driven_dark_variant(self):
        offenders = []
        css_dir = os.path.join(REPO_ROOT, 'static', 'css')
        for root, _dirs, files in os.walk(css_dir):
            for name in files:
                if not name.endswith('.css') or name == 'control-room.css':
                    continue
                with open(os.path.join(root, name), encoding='utf-8') as handle:
                    if 'prefers-color-scheme: dark' in handle.read():
                        offenders.append(name)
        self.assertEqual(offenders, [])

    def test_the_toggle_script_refuses_to_act_without_the_gate(self):
        """Defence in depth: a switch re-added by mistake still does nothing."""
        source = read_repo_file('static', 'js', 'theme-toggle.js')
        self.assertIn(
            "if (!document.documentElement.hasAttribute('data-ps-dark-theme')) return;",
            source,
        )


class DarkThemeIsPausedNotRemovedTests(unittest.TestCase):
    """The other half of the owner's direction: leave the work in place."""

    def test_every_dark_rule_set_is_still_in_the_repository(self):
        for name in DORMANT_DARK_STYLESHEETS:
            css = read_repo_file('static', 'css', name)
            self.assertIn('data-theme="dark"', css, name)

    def test_the_control_and_its_handler_are_still_in_the_repository(self):
        base = read_repo_file('templates', 'base.html')
        self.assertIn('class="theme-toggle"', base)
        self.assertIn('id="theme-toggle"', base)
        self.assertIn('theme-toggle__thumb', base)

        handler = read_repo_file('static', 'js', 'theme-toggle.js')
        self.assertIn("var STORAGE_KEY = 'ps-theme';", handler)
        self.assertIn("document.body.setAttribute('data-theme', next);", handler)

        self.assertIn('.theme-toggle', read_repo_file('static', 'css', 'style.css'))

    def test_the_pause_is_recorded_in_the_decision_log(self):
        log = read_repo_file('docs', 'governance', 'DECISIONS.md')
        self.assertIn('2026-08-03 - Pause the dark theme site-wide', log)
        self.assertIn('PEERSLATE_DARK_THEME_ENABLED', log)


@unittest.skipUnless(
    sync_playwright is not None and CHROME_EXECUTABLE,
    'Playwright and Google Chrome are required for dark-pause browser coverage',
)
class DarkThemeStaysLightInABrowserTests(unittest.TestCase):
    """Prove it where it matters: a real browser, both dark inputs.

    Server-rendered HTML cannot show what a dark-operating-system visitor with
    a stored "dark" preference actually sees. These contexts reproduce exactly
    that and assert the render is identical to a visitor with neither.
    """

    BROWSER_ROUTES = ('/', '/interview-studio', '/petec/resume')

    # The homepage body is deliberately transparent (the fixed .site-sky layer
    # paints behind it), so an absolute "is it bright?" check would be wrong.
    # What proves the pause is that the dark inputs change nothing.
    PROBE = """() => ({
        theme: document.body.getAttribute('data-theme'),
        gate: document.documentElement.getAttribute('data-ps-dark-theme'),
        colorScheme: getComputedStyle(document.documentElement).colorScheme,
        bodyBackground: getComputedStyle(document.body).backgroundColor,
        bodyInk: getComputedStyle(document.body).color,
        themeControls: document.querySelectorAll('.theme-toggle').length,
    })"""

    @classmethod
    def setUpClass(cls):
        cls.original_testing = app.config.get('TESTING')
        app.config['TESTING'] = True
        cls.server = make_server('127.0.0.1', 0, app)
        cls.server_thread = threading.Thread(
            target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        cls.base_url = f'http://127.0.0.1:{cls.server.server_port}'
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(
            executable_path=CHROME_EXECUTABLE, headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        cls.server.shutdown()
        cls.server_thread.join(timeout=5)
        app.config['TESTING'] = cls.original_testing

    def _page(self, seed_stored_dark=False, os_dark=False):
        context = self.browser.new_context(
            viewport={'width': 1280, 'height': 900},
            color_scheme='dark' if os_dark else 'light',
        )
        if seed_stored_dark:
            context.add_init_script("localStorage.setItem('ps-theme', 'dark');")
        self.addCleanup(context.close)
        page = context.new_page()
        # The shell links Google Fonts. This suite is about local CSS and JS,
        # and the test host has no outbound network, so stub them.
        page.route('https://fonts.**', lambda route: route.abort())
        return page

    def _probe(self, page, route):
        page.goto(f'{self.base_url}{route}', wait_until='load')
        return page.evaluate(self.PROBE)

    def _assert_light(self, page, route):
        seen = self._probe(page, route)
        self.assertEqual(seen['theme'], 'modern-blue', route)
        self.assertIsNone(seen['gate'], route)
        self.assertEqual(seen['colorScheme'], 'light', route)
        self.assertEqual(seen['themeControls'], 0, route)
        # Light-theme ink is the deep navy the shell has always used; a dark
        # render would invert this to a near-white.
        self.assertEqual(seen['bodyInk'], 'rgb(6, 26, 58)', route)
        return seen

    def _control(self, route):
        """The same route with no dark input at all."""
        return self._probe(self._page(), route)

    def test_a_stored_dark_preference_still_renders_light(self):
        page = self._page(seed_stored_dark=True)
        for route in self.BROWSER_ROUTES:
            self.assertEqual(self._assert_light(page, route),
                             self._control(route), route)
        # The stored value is intentionally preserved, not cleared, so the
        # visitor's original choice returns when the pause is lifted.
        self.assertEqual(
            page.evaluate("window.localStorage.getItem('ps-theme')"), 'dark')

    def test_a_dark_operating_system_preference_still_renders_light(self):
        page = self._page(os_dark=True)
        for route in self.BROWSER_ROUTES:
            self.assertEqual(self._assert_light(page, route),
                             self._control(route), route)

    def test_both_dark_inputs_together_still_render_light(self):
        page = self._page(seed_stored_dark=True, os_dark=True)
        for route in self.BROWSER_ROUTES:
            self.assertEqual(self._assert_light(page, route),
                             self._control(route), route)


if __name__ == '__main__':
    unittest.main()
