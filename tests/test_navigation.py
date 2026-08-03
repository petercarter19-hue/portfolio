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
        self.assertEqual(records_by_title['Community Feed']['href'], '/the-slate')
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
        for path in (
            '/the-slate',
            '/the-slate/my-slate',
            '/the-slate/daily',
            '/the-slate/pulse',
            '/the-slate/break',
        ):
            with self.subTest(path=path):
                response = self.client.get(path, base_url='http://localhost')
                self.assertEqual(response.status_code, 200)
                self.assertIn(b'the-slate-page', response.data)
                self.assertNotIn(b'class="profile-tabs', response.data)
                self.assertNotIn(b'id="chat-toggle"', response.data)

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
            '/the-slate',
            '/the-slate/my-slate',
            '/the-slate/daily',
            '/the-slate/pulse',
            '/the-slate/break',
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
