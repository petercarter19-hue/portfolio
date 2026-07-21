import json
import re
import unittest
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

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
                    '/petec/resume',
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
        self.assertIn('Resume', titles)
        resume = next(record for record in records if record['title'] == 'Resume')
        self.assertEqual(resume['href'], '/petec/resume')

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
        self.assertEqual(records_by_title['Community']['href'], '/the-slate')
        self.assertEqual(records_by_title['Interview Studio']['href'], '/interview-studio')
        self.assertNotIn('The Slate', records_by_title)

    def test_resume_subheader_ai_field_replaces_the_retired_overview_field(self):
        resume = self.client.get('/petec/resume', base_url='http://localhost')

        self.assertEqual(resume.status_code, 200)
        self.assertIn(b'data-resume-subheader-ask', resume.data)
        self.assertIn(b'id="subheader-ai-input"', resume.data)
        self.assertNotIn(b'data-overview-subheader-ask', resume.data)
        self.assertNotIn(b'id="overview-subheader-ai-input"', resume.data)

    def test_every_canonical_slate_route_uses_the_standard_subheader_scope(self):
        for path in (
            '/the-slate',
            '/the-slate/my-slate',
            '/the-slate/daily',
            '/the-slate/pulse',
            '/the-slate/break',
            '/the-slate/saved',
        ):
            with self.subTest(path=path):
                response = self.client.get(path, base_url='http://localhost')
                self.assertEqual(response.status_code, 200)
                self.assertIn(b'the-slate-page', response.data)
                self.assertIn(b'class="profile-tabs', response.data)

        homepage = self.client.get('/', base_url='http://localhost')
        self.assertNotIn(b'the-slate-page', homepage.data)

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
            '/the-slate/saved',
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
