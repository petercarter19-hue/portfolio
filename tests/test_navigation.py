import json
import re
import unittest
import xml.etree.ElementTree as ET
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

        if tag == 'nav' and 'platform-nav' in classes:
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

    def search_records(self, path='/', base_url='http://localhost'):
        response = self.client.get(path, base_url=base_url)
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        match = re.search(
            r'<script id="nav-search-data" type="application/json">(.*?)</script>',
            html,
            re.DOTALL,
        )
        self.assertIsNotNone(match)
        return json.loads(match.group(1))

    def test_petes_slate_opens_the_canonical_resume_and_redundant_home_is_omitted(self):
        for path in ('/', '/petec/resume'):
            with self.subTest(path=path):
                links = self.parse_platform_links(path)
                links_by_text = {link['text']: link for link in links}

                self.assertNotIn('Atrium', links_by_text)
                self.assertEqual(
                    links_by_text["Pete's Slate"]['attributes']['href'],
                    '/petec/resume#overview',
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
            homepage_links["Pete's Slate"]['attributes'],
        )
        self.assertEqual(
            resume_links["Pete's Slate"]['attributes'].get('aria-current'),
            'page',
        )
        self.assertNotIn('Home', resume_links)

    def test_header_search_omits_retired_overview_and_projects_records(self):
        records = self.search_records()
        titles = [record['title'] for record in records]

        self.assertNotIn('Overview', titles)
        self.assertNotIn('Projects', titles)
        self.assertIn('Résumé', titles)
        resume = next(record for record in records if record['title'] == 'Résumé')
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
        links = {
            link['text']: link
            for link in self.parse_platform_links('/interview-studio')
        }
        self.assertEqual(links['Community']['attributes']['href'], '/the-slate')
        self.assertEqual(links['Interview Studio']['attributes']['href'], '/interview-studio')
        # v1.2 (PS-BRAND-NAV-001): About left the header; the footer link
        # 'Why PeerSlate' points at the same route instead.
        self.assertNotIn('About PeerSlate', links)
        self.assertEqual(
            links['Interview Studio']['attributes'].get('aria-current'),
            'page',
        )
        self.assertNotIn('The Slate', links)
        self.assertNotIn('Interview Me', links)
        self.assertNotIn('About', links)

        records = self.search_records('/interview-studio')
        records_by_title = {record['title']: record for record in records}
        # PS-COMMUNITY-AUTH-WALL-001: the search entry is simply "Community"
        # and is honest about its members-only audience.
        self.assertEqual(records_by_title['Community']['href'], '/the-slate')
        self.assertEqual(
            records_by_title['Community']['sub'],
            'Visible to signed-in PeerSlate members',
        )
        self.assertNotIn('Community Feed', records_by_title)
        self.assertEqual(records_by_title['Interview Studio']['href'], '/interview-studio')
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
        response = self.client.get('/interview-studio', base_url='http://localhost')
        html = response.get_data(as_text=True)

        self.assertIn('data-platform-menu-toggle', html)
        self.assertIn('id="platform-mobile-menu"', html)
        menu = html.split('id="platform-mobile-menu"', 1)[1].split('</nav>', 1)[0]
        for label in ("Pete's Slate", 'Community', 'Interview Studio'):
            self.assertEqual(menu.count(f'>{label}</a>'), 1)
        self.assertIn('id="nav-search-input-mobile"', menu)

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

            # The legacy /app workspace is deliberately unchanged.
            legacy = self.client.get('/app', base_url='http://localhost')
            self.assertEqual(legacy.status_code, 200)
            self.assertIn(b'class="profile-tabs', legacy.data)
        finally:
            for key, value in originals.items():
                if value is None:
                    app.config.pop(key, None)
                else:
                    app.config[key] = value

    def test_public_search_is_navigation_only_without_an_ai_fallback(self):
        source = Path('static/js/public-site-search.js').read_text(encoding='utf-8')
        self.assertIn('No matching public destination', source)
        self.assertNotIn('Ask Pete', source)
        self.assertNotIn('data-ask-url', self.client.get('/').get_data(as_text=True))

    def test_opportunity_slate_link_sits_next_to_workshop_in_both_menus(self):
        """PS-OPPORTUNITY-SLATE-001 leg 7 (Pete's 2026-08-05 order): the link
        is unconditional, unlike Workshop's flag-gated entry beside it."""
        homepage_links = {
            link['text']: link for link in self.parse_platform_links('/')
        }
        self.assertIn('Opportunity Slate', homepage_links)
        self.assertEqual(
            homepage_links['Opportunity Slate']['attributes']['href'],
            '/opportunity-slate',
        )
        self.assertNotIn(
            'aria-current', homepage_links['Opportunity Slate']['attributes']
        )

        mobile_menu = self.client.get('/', base_url='http://localhost').get_data(
            as_text=True
        )
        menu = mobile_menu.split('id="platform-mobile-menu"', 1)[1].split(
            '</nav>', 1
        )[0]
        self.assertEqual(menu.count('>Opportunity Slate</a>'), 1)

    def test_opportunity_slate_link_shows_aria_current_on_its_own_room(self):
        original_flag = app.config.get('PEERSLATE_OPPORTUNITY_SLATE_ENABLED')
        app.config['PEERSLATE_OPPORTUNITY_SLATE_ENABLED'] = True
        try:
            links = {
                link['text']: link
                for link in self.parse_platform_links('/opportunity-slate')
            }
        finally:
            app.config['PEERSLATE_OPPORTUNITY_SLATE_ENABLED'] = original_flag
        self.assertIn('Opportunity Slate', links)
        self.assertEqual(
            links['Opportunity Slate']['attributes'].get('aria-current'), 'page'
        )

    def test_header_search_json_parses_with_opportunity_slate_in_both_workshop_states(self):
        """The Opportunity Slate record sits after Workshop's
        ``{% if workshop_nav_enabled %}...{% endif %}`` block, so the JSON
        must stay valid whether or not that flag is on."""
        original_workshop_flag = app.config.get('PEERSLATE_WORKSHOP_ENABLED')
        try:
            for workshop_enabled in (True, False):
                with self.subTest(workshop_nav_enabled=workshop_enabled):
                    app.config['PEERSLATE_WORKSHOP_ENABLED'] = workshop_enabled
                    records = self.search_records()
                    titles = [record['title'] for record in records]
                    self.assertIn('Opportunity Slate', titles)
                    self.assertEqual(
                        titles.count('Opportunity Slate'), 1
                    )
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
                    self.assertEqual('Workshop' in titles, workshop_enabled)
        finally:
            app.config['PEERSLATE_WORKSHOP_ENABLED'] = original_workshop_flag

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
            '/petec/slate-board',
            '/interview-studio',
            '/peerslate',
            '/petec/about',
            '/petec/hobbies',
            '/petec/contact',
            # PS-COMMUNITY-AUTH-WALL-001: no members-only /the-slate route
            # belongs in the public sitemap.
            '/career-search',
            '/my-network',
            '/explore-profiles',
            '/for-recruiters',
        ]
        self.assertEqual(
            locations,
            [f'https://peerslate.com{path}' for path in expected_paths],
        )


if __name__ == '__main__':
    unittest.main()
