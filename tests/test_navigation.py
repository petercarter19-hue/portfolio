import json
import re
import unittest
import xml.etree.ElementTree as ET
from contextlib import contextmanager
from html.parser import HTMLParser
from pathlib import Path

from app import app


class PlatformNavigationParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_platform_nav = False
        self.current_link = None
        self.links = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        classes = attributes.get('class', '').split()

        if tag == 'nav' and 'ps-top__nav' in classes:
            self.in_platform_nav = True
        elif self.in_platform_nav and tag == 'a':
            self.current_link = {'attributes': attributes, 'text': ''}

    def handle_data(self, data):
        if self.current_link is not None:
            self.current_link['text'] += data

    def handle_endtag(self, tag):
        if self.current_link is not None and tag == 'a':
            self.current_link['text'] = self.current_link['text'].strip()
            self.links.append(self.current_link)
            self.current_link = None
        elif self.in_platform_nav and tag == 'nav':
            self.in_platform_nav = False


class NavigationTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def parse_platform_links(self, path, base_url='http://localhost'):
        response = self.client.get(path, base_url=base_url)
        self.assertEqual(response.status_code, 200)
        parser = PlatformNavigationParser()
        parser.feed(response.get_data(as_text=True))
        return parser.links

    def search_records(self, path='/', base_url='http://localhost', client=None):
        response = (client or self.client).get(path, base_url=base_url)
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        match = re.search(
            r'<script id="nav-search-data" type="application/json">(.*?)</script>',
            html,
            re.DOTALL,
        )
        self.assertIsNotNone(match)
        return json.loads(match.group(1))

    @contextmanager
    def destination_flags(self, *, community=False, workshop=False, opportunity=False):
        values = {
            'PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED': community,
            'PEERSLATE_WORKSHOP_ENABLED': workshop,
            'PEERSLATE_OPPORTUNITY_SLATE_ENABLED': opportunity,
            'PEERSLATE_OPPORTUNITY_SLATE_V2_ENABLED': opportunity,
        }
        originals = {key: app.config.get(key) for key in values}
        app.config.update(values)
        try:
            yield
        finally:
            for key, value in originals.items():
                if value is None:
                    app.config.pop(key, None)
                else:
                    app.config[key] = value

    def test_public_resume_link_targets_the_selected_published_resume(self):
        for path in ('/', '/petec/resume'):
            with self.subTest(path=path):
                links = self.parse_platform_links(path)
                links_by_text = {link['text']: link for link in links}

                self.assertNotIn('Atrium', links_by_text)
                self.assertEqual(
                    links_by_text["My Resume"]['attributes']['href'],
                    '/petec/resume#resume-start',
                )
                self.assertNotIn('Home', links_by_text)

        homepage_links = {
            link['text']: link for link in self.parse_platform_links('/')
        }
        resume_links = {
            link['text']: link
            for link in self.parse_platform_links('/petec/resume')
        }
        self.assertNotIn(
            'aria-current',
            homepage_links["My Resume"]['attributes'],
        )
        self.assertEqual(
            resume_links["My Resume"]['attributes'].get('aria-current'),
            'page',
        )
        self.assertNotIn('Home', resume_links)

    def test_header_search_omits_retired_overview_and_projects_records(self):
        records = self.search_records()
        titles = [record['title'] for record in records]

        self.assertNotIn('Overview', titles)
        self.assertNotIn('Projects', titles)
        self.assertIn('My Resume', titles)
        resume = next(record for record in records if record['title'] == 'My Resume')
        self.assertEqual(resume['href'], '/petec/resume#resume-start')
        for retired in (
            'Community · My Slate',
            'Community · Daily Slate',
            'Community · My Paths',
            'Feed · Pulse',
            'Feed Preview · Living Stream',
        ):
            self.assertNotIn(retired, titles)

    def test_global_product_names_and_links_use_the_new_information_architecture(self):
        # PS-SITE-SHELL-ROUND5-001 (Pete, 2026-10-13): the public bar opens
        # My Resume and My Story; Interview Studio and the rest are Soon.
        with self.destination_flags(community=True):
            links = {
                link['text']: link
                for link in self.parse_platform_links('/interview-studio')
            }
            html = self.client.get(
                '/interview-studio', base_url='http://localhost'
            ).get_data(as_text=True)
            records = self.search_records('/interview-studio')
        self.assertEqual(['My Resume', 'My Story'], list(links))
        self.assertEqual(links['My Story']['attributes']['href'], '/petec/my-story')
        for absent in ('Community', 'Opportunity Slate', 'About PeerSlate', 'Interview AI',
                       'Interview Studio', 'The Slate', 'Interview Me', 'About'):
            self.assertNotIn(absent, links)
        bar = html.split('<nav class="ps-top__nav"', 1)[1].split('</nav>', 1)[0]
        self.assertIn('<span class="ps-top__soon">Interview Studio</span>', bar)

        # The header search field is gone; its server index is unchanged.
        records_by_title = {record['title']: record for record in records}
        self.assertNotIn('Community', records_by_title)
        self.assertNotIn('Opportunity Slate', records_by_title)
        self.assertNotIn('Community Feed', records_by_title)
        self.assertEqual(records_by_title['Interview AI']['href'], '/interview-studio?mode=ai')
        self.assertNotIn('The Slate', records_by_title)

    def test_resume_subheader_ai_field_replaces_the_retired_overview_field(self):
        resume = self.client.get('/petec/resume', base_url='http://localhost')

        self.assertEqual(resume.status_code, 200)
        self.assertIn(b'data-resume-subheader-ask', resume.data)
        self.assertIn(b'id="subheader-ai-input"', resume.data)
        self.assertNotIn(b'data-overview-subheader-ask', resume.data)
        self.assertNotIn(b'id="overview-subheader-ai-input"', resume.data)

    def test_community_routes_do_not_inherit_petes_profile_subheader(self):
        # PS-COMMUNITY-AUTH-WALL-001: the legacy subviews forward to the one
        # real Community in every flag state, and Community itself is
        # members-only — flag off is a neutral 404, signed out goes through
        # sign-in. None of these responses carries Pete's profile subheader.
        original_flag = app.config.get('PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED')
        try:
            for flag in (False, True):
                app.config['PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED'] = flag
                for path in (
                    '/the-slate/my-slate',
                    '/the-slate/daily',
                    '/the-slate/pulse',
                    '/the-slate/break',
                ):
                    with self.subTest(path=path, flag=flag):
                        response = self.client.get(path, base_url='http://localhost')
                        self.assertEqual(response.status_code, 302)
                        self.assertTrue(
                            response.headers['Location'].endswith('/the-slate')
                        )
                        self.assertNotIn(b'class="profile-tabs', response.data)

            app.config['PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED'] = False
            flag_off = self.client.get('/the-slate', base_url='http://localhost')
            self.assertEqual(flag_off.status_code, 404)
            self.assertNotIn(b'class="profile-tabs', flag_off.data)
            self.assertNotIn(b'id="chat-toggle"', flag_off.data)

            app.config['PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED'] = True
            signed_out = self.client.get('/the-slate', base_url='http://localhost')
            self.assertEqual(signed_out.status_code, 302)
            self.assertEqual(
                signed_out.headers['Location'],
                '/auth/sign-in?return_to=/the-slate',
            )
        finally:
            app.config['PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED'] = original_flag

        homepage = self.client.get('/', base_url='http://localhost')
        self.assertNotIn(b'the-slate-page', homepage.data)

    def test_public_mobile_menu_has_one_complete_global_destination_set(self):
        with self.destination_flags(community=True):
            response = self.client.get(
                '/interview-studio', base_url='http://localhost'
            )
        html = response.get_data(as_text=True)

        self.assertIn('data-platform-menu-toggle', html)
        self.assertIn('id="platform-mobile-menu"', html)
        menu = html.split('id="platform-mobile-menu"', 1)[1].split('</header>', 1)[0]
        for label in ('My Resume', 'My Story'):
            self.assertEqual(menu.count(f'>{label}</a>'), 1)
        for soon in ('Interview Studio', 'Community', 'Opportunity Slate', 'My Opportunities'):
            self.assertNotIn(f'>{soon}</a>', menu)
            self.assertIn(f'<li>{soon}</li>', menu)
        # Round 5 has no header search field, in the bar or in the sheet.
        self.assertNotIn('id="nav-search-input-mobile"', menu)
        self.assertEqual(html.count('class="nav-search__input"'), 0)

    def test_member_specific_ai_is_scoped_to_petes_public_slate(self):
        for path in (
            '/',
            '/the-slate',
            '/interview-studio',
            '/peerslate',
            '/experience',
        ):
            with self.subTest(path=path):
                response = self.client.get(path, base_url='http://localhost')
                self.assertNotIn(b'id="chat-toggle"', response.data)
                self.assertNotIn(b'class="profile-tabs', response.data)

        for path in (
            '/petec/resume',
            '/petec/my-story',
            '/petec/slate-board',
        ):
            with self.subTest(path=path):
                response = self.client.get(path, base_url='http://localhost')
                self.assertIn(b'id="chat-toggle"', response.data)
                self.assertIn(b'class="profile-tabs', response.data)

    def test_private_owner_surfaces_do_not_inherit_petes_public_profile_tabs(self):
        """Pete's public tab strip is fixture content; a member's private
        owner pages must not publish it above their own workspace.

        PS-PUBLIC-NAV-001 set the contract ("Pete's profile navigation
        renders only on Pete profile routes") but the base.html condition
        still admitted every `/app` path, so Capture, Settings and Moment
        review each rendered My Story / Work / Slate Board / Resume plus a
        second Ask Pete AI control. Corrected 2026-08-03 (site visual parity
        audit, finding 10). `/app` itself is excluded from this test on
        purpose: it is the deferred legacy owner workspace that
        PS-HOME-FRONTEND-001 replaces, and its flag-off render is byte-locked
        by tests/test_owner_home.py.
        """
        originals = {
            key: app.config.get(key)
            for key in ('PEERSLATE_ALLOW_DEV_IDENTITY', 'PEERSLATE_DEV_USER_KEY')
        }
        app.config['PEERSLATE_ALLOW_DEV_IDENTITY'] = True
        app.config['PEERSLATE_DEV_USER_KEY'] = 'navigation-test-owner'
        try:
            for path in ('/app/capture', '/app/settings'):
                with self.subTest(path=path):
                    response = self.client.get(path, base_url='http://localhost')
                    # 200 with a database, 503 on the honest unavailable
                    # render without one; both use this shared shell.
                    self.assertIn(response.status_code, (200, 503))
                    self.assertNotIn(b'class="profile-tabs', response.data)
                    self.assertNotIn(b'profile-tabs__ask-btn', response.data)

            # The neutral /app launchpad uses the same protected shell rule.
            launchpad = self.client.get('/app', base_url='http://localhost')
            self.assertEqual(launchpad.status_code, 200)
            self.assertNotIn(b'class="profile-tabs', launchpad.data)
            self.assertNotIn(b'profile-tabs__ask-btn', launchpad.data)
        finally:
            for key, value in originals.items():
                if value is None:
                    app.config.pop(key, None)
                else:
                    app.config[key] = value

    def test_public_search_is_navigation_only_without_an_ai_fallback(self):
        source = Path('static/js/public-site-search.js').read_text(encoding='utf-8')
        self.assertIn('No matching destination', source)
        self.assertNotIn('Ask Pete', source)
        self.assertNotIn('data-ask-url', self.client.get('/').get_data(as_text=True))

    def test_opportunity_slate_is_not_promoted_from_public_shell(self):
        """Availability does not make an unfinished room a public link."""
        for enabled in (False, True):
            with self.subTest(opportunity_enabled=enabled), self.destination_flags(
                workshop=True, opportunity=enabled
            ):
                html = self.client.get(
                    '/', base_url='http://localhost'
                ).get_data(as_text=True)
                links = {
                    link['text']: link for link in self.parse_platform_links('/')
                }
                menu = html.split('id="platform-mobile-menu"', 1)[1].split(
                    '</nav>', 1
                )[0]
                self.assertNotIn('Opportunity Slate', links)
                self.assertNotIn('>Opportunity Slate</a>', menu)
                if enabled:
                    self.assertNotIn('>Workshop</a>', menu)

    def test_opportunity_slate_is_soon_even_inside_its_own_room(self):
        # Round 5 (Pete, 2026-10-13): everything but My Resume is Soon, on
        # every page, including the room itself.
        with self.destination_flags(opportunity=True):
            client = self.signed_in_client()
            response = client.get('/opportunity-slate', base_url='http://localhost')
            self.assertIn(response.status_code, (200, 503))
            html = response.get_data(as_text=True)
            parser = PlatformNavigationParser()
            parser.feed(html)
            links = {link['text']: link for link in parser.links}
        self.assertNotIn('Opportunity Slate', links)
        bar = html.split('<nav class="ps-top__nav"', 1)[1].split('</nav>', 1)[0]
        self.assertIn('<span class="ps-top__soon">Opportunity Slate</span>', bar)

    def test_header_search_json_ignores_workshop_navigation_flag(self):
        """Member search keeps the available room without offering Workshop."""
        for workshop_enabled in (True, False):
            with self.subTest(workshop_nav_enabled=workshop_enabled), self.destination_flags(
                workshop=workshop_enabled, opportunity=True
            ):
                records = self.search_records('/app', client=self.signed_in_client())
                titles = [record['title'] for record in records]
                self.assertIn('Opportunity Slate', titles)
                self.assertEqual(titles.count('Opportunity Slate'), 1)
                entry = next(
                    record
                    for record in records
                    if record['title'] == 'Opportunity Slate'
                )
                self.assertEqual(entry['href'], '/opportunity-slate')
                self.assertEqual(
                    entry['sub'],
                    'See how your evidence lines up with a role',
                )
                self.assertIn('role', entry['keys'])
                self.assertNotIn('Workshop', titles)

    # ------------------------------------------------------------------
    # PS-SHELL-001 — the Editorial Top Bar
    # ------------------------------------------------------------------

    def signed_in_client(self):
        """A client whose SERVER render is authenticated, via the existing
        development-identity path. The shell's signed-in markup is
        server-derived, so it cannot be exercised any other way."""
        originals = {
            key: app.config.get(key)
            for key in ('PEERSLATE_ALLOW_DEV_IDENTITY', 'PEERSLATE_DEV_USER_KEY')
        }
        app.config['PEERSLATE_ALLOW_DEV_IDENTITY'] = True
        app.config['PEERSLATE_DEV_USER_KEY'] = 'shell-test-member'
        self.addCleanup(self._restore_config, originals)
        return app.test_client()

    def _restore_config(self, originals):
        for key, value in originals.items():
            if value is None:
                app.config.pop(key, None)
            else:
                app.config[key] = value

    def test_round_five_bar_has_no_room_switcher(self):
        """Round 5 has no medium-width room switcher; the bar's own links and
        the Menu sheet are the only representations."""
        for path in ('/', '/interview-studio'):
            with self.subTest(path=path):
                html = self.client.get(path, base_url='http://localhost').get_data(as_text=True)
                for removed in ('platform-roomswitcher', 'Browse destinations',
                                'data-platform-roomswitcher-trigger'):
                    self.assertNotIn(removed, html)

    def test_the_logo_is_revealed_at_every_width_in_every_auth_state(self):
        """Owner direction, 2026-08-13: "logo should always be revealed".
        Round 5's Cairn lockup is in every render, and no rule in the bar's
        stylesheet hides it at any width."""
        stylesheet = Path('static/css/site-header.css').read_text(encoding='utf-8')
        declarations = re.sub(r'/\*.*?\*/', '', stylesheet, flags=re.S)
        blocks = re.findall(
            r'([^{}]*ps-top__(?:lockup|stones|word)[^{}]*)\{([^{}]*)\}', declarations
        )
        self.assertTrue(blocks, 'expected the bar to style the Cairn lockup')
        for selector, body in blocks:
            with self.subTest(selector=' '.join(selector.split())[-80:]):
                self.assertNotRegex(body, r'display\s*:\s*none')
                self.assertNotRegex(body, r'visibility\s*:\s*hidden')
                self.assertNotRegex(body, r'\bcontent-visibility\s*:\s*hidden')

        paths = ('/', '/interview-studio', '/opportunity-slate', '/petec/resume')
        opportunity_is_private = (
            'opportunity_slate_v2.room' in app.view_functions
        )
        # Anonymous first: signed_in_client() flips application config.
        anonymous = {
            path: self.client.get(path, base_url='http://localhost').get_data(
                as_text=True
            )
            for path in paths
            if not (opportunity_is_private and path == '/opportunity-slate')
        }
        if opportunity_is_private:
            gated = self.client.get(
                '/opportunity-slate', base_url='http://localhost'
            )
            self.assertEqual(302, gated.status_code)
            self.assertEqual(
                '/auth/sign-in?return_to=/opportunity-slate',
                gated.headers['Location'],
            )
        signed_in = self.signed_in_client()
        for path in paths:
            with self.subTest(path=path):
                renders = [signed_in.get(
                    path, base_url='http://localhost'
                ).get_data(as_text=True)]
                if path in anonymous:
                    renders.insert(0, anonymous[path])
                for html in renders:
                    self.assertIn('<a class="ps-top__lockup" href="/"', html)
                    self.assertIn('class="ps-top__stones"', html)
                    self.assertIn('<span class="ps-top__word">PeerSlate</span>', html)

    def test_round_five_bar_names_no_room_beside_the_logo(self):
        """Round 5 draws the lockup alone; the earlier signed-in room title
        beside the logo is not part of the approved bar."""
        signed_in = self.signed_in_client()
        for path in ('/interview-studio', '/app', '/'):
            with self.subTest(path=path):
                html = signed_in.get(path, base_url='http://localhost').get_data(as_text=True)
                self.assertNotIn('data-ps-shell-room-title', html)
                self.assertNotIn('platform-room-title', html)
                self.assertIn('class="ps-top__lockup"', html)

    def test_no_global_phone_bar_in_either_auth_state(self):
        """PS-SITE-SHELL-ROUND5-001 (manager ruling 2026-10-15): the signed-in
        global phone bottom bar is retired so phones match the round-5 bar and
        nothing points at a Soon room. The header Menu is the one phone
        navigation affordance, signed out and signed in."""
        # Anonymous first: signed_in_client() flips application config.
        anonymous = self.client.get('/', base_url='http://localhost').get_data(
            as_text=True
        )
        signed_in = self.signed_in_client().get(
            '/', base_url='http://localhost'
        ).get_data(as_text=True)
        for html in (anonymous, signed_in):
            self.assertNotIn('data-global-tabsource', html)
            self.assertNotIn('data-global-more', html)
            self.assertIn('data-platform-menu-toggle', html)

    def test_more_sheet_offers_settings_and_omits_a_help_route_that_does_not_exist(self):
        """The direction's More list names Help, but no Help route is
        registered anywhere in the application. Navigation gains no
        destination that lacks a real page, so Help is not offered."""
        with self.destination_flags(
            community=True, workshop=True, opportunity=True
        ):
            html = self.client.get(
                '/interview-studio', base_url='http://localhost'
            ).get_data(as_text=True)
        menu = html.split('id="platform-mobile-menu"', 1)[1].split('</header>', 1)[0]

        self.assertIn('>Settings</a>', menu)
        self.assertIn('href="/app/settings"', menu)
        self.assertNotIn('>Help<', menu)
        # Every open destination is reachable from the sheet; Soon names are not links.
        for label in ('My Resume', 'My Story'):
            self.assertEqual(menu.count(f'>{label}</a>'), 1)
        self.assertNotIn('>Community</a>', menu)
        self.assertNotIn('>Opportunity Slate</a>', menu)
        self.assertNotIn('>Workshop</a>', menu)

    def test_shell_offers_no_notification_or_add_control(self):
        """Neither has a real backing contract: no notification route, model
        or service exists, and /app/capture is owner-gated behind a
        fail-closed allowlist. The Add position is reserved in comment only,
        so a future member contract is an insertion, not a re-layout."""
        for path in ('/', '/interview-studio', '/petec/resume'):
            with self.subTest(path=path):
                html = self.client.get(
                    path, base_url='http://localhost'
                ).get_data(as_text=True)
                header = html.split('<div class="ps-shell" id="site-header">', 1)[1].split(
                    '</header>', 1
                )[0]
                for banned in ('notification', 'data-ps-notifications',
                               'data-ps-add', 'href="/app/capture"'):
                    self.assertNotIn(banned, header)

        # The reservation is a template marker, so it ships zero bytes and
        # cannot become a false affordance.
        template = Path('templates/partials/site_header.html').read_text(encoding='utf-8')
        self.assertIn('PS-SHELL-001 reserved Add slot', template)
        self.assertLess(
            template.index('PS-SHELL-001 reserved Add slot'),
            template.index('class="platform-account ps-top__account"'),
        )

    def test_owner_workspace_uses_the_shared_shell_without_profile_tabs(self):
        """The retired standalone and legacy branches converge on one shell."""
        originals = {
            key: app.config.get(key)
            for key in ('PEERSLATE_ALLOW_DEV_IDENTITY', 'PEERSLATE_DEV_USER_KEY')
        }
        app.config['PEERSLATE_ALLOW_DEV_IDENTITY'] = True
        app.config['PEERSLATE_DEV_USER_KEY'] = 'shell-test-owner'
        try:
            legacy = self.client.get('/app', base_url='http://localhost')
        finally:
            for key, value in originals.items():
                if value is None:
                    app.config.pop(key, None)
                else:
                    app.config[key] = value

        self.assertEqual(legacy.status_code, 200)
        body = legacy.get_data(as_text=True)
        self.assertEqual(body.count('public-navigation.css'), 1)
        self.assertEqual(body.count('site-header.css'), 1)
        self.assertIn('<div class="ps-shell" id="site-header">', body)
        # Round 5, review of 37ab31c2 (F3): signed in, My PeerSlate is the
        # member's working account link, so the bar neither links it nor
        # lists it as Soon; each destination appears once.
        bar = body.split('<nav class="ps-top__nav"', 1)[1].split('</nav>', 1)[0]
        self.assertNotIn('My PeerSlate', bar)
        self.assertIn('>My PeerSlate</a>', body)
        self.assertNotIn('class="profile-tabs', body)
        self.assertNotIn('owner-home-shell', body)
        self.assertEqual(body.count('js/public-site-search.js'), 1)
        self.assertEqual(body.count('js/public-mobile-nav.js'), 1)
        self.assertNotIn('js/site-search.js', body)
        self.assertNotIn('js/mobile-nav.js', body)
        self.assertIn('platform-account', body)
        for retired in ('platform-roomswitcher', 'data-global-tabsource'):
            self.assertNotIn(retired, body)

    def test_sitemap_contains_only_current_canonical_public_routes(self):
        response = self.client.get(
            '/sitemap.xml',
            base_url='https://peerslate.com',
        )
        self.assertEqual(response.status_code, 200)
        root = ET.fromstring(response.get_data(as_text=True))
        namespace = {'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        locations = [
            item.text
            for item in root.findall('sitemap:url/sitemap:loc', namespace)
        ]
        expected_paths = [
            '/',
            '/experience',
            '/petec/my-story',
            '/petec/skills',
            '/petec/resume',
            '/peerslate',
            '/petec/about',
            '/petec/hobbies',
            '/petec/contact',
            # PS-COMMUNITY-AUTH-WALL-001: no members-only /the-slate route
            # belongs in the public sitemap.
            # PS-INTERVIEW-STUDIO-AUTHENTICATED-EXPERIENCE-001: sign-in is
            # required for Interview Studio (architecture 04 section 1), so
            # /interview-studio is unconditionally removed from the public
            # sitemap -- see tests/test_search_visibility.py for the
            # matching robots.txt Disallow coverage.
            '/career-search',
            '/my-network',
            '/explore-profiles',
            '/for-recruiters',
        ]
        self.assertEqual(
            locations,
            [],
        )


if __name__ == '__main__':
    unittest.main()
