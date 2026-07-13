import unittest
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

    def parse_platform_links(self, path):
        response = self.client.get(path, base_url='http://localhost')
        self.assertEqual(response.status_code, 200)
        parser = PlatformNavigationParser()
        parser.feed(response.get_data(as_text=True))
        return parser.links

    def test_home_and_example_slate_are_distinct_destinations(self):
        homepage_links = self.parse_platform_links('/')
        profile_links = self.parse_platform_links('/petec')

        homepage_by_text = {link['text']: link for link in homepage_links}
        profile_by_text = {link['text']: link for link in profile_links}

        self.assertEqual(homepage_by_text["Pete's Slate"]['attributes']['href'], '/')
        self.assertEqual(profile_by_text["Pete's Slate"]['attributes']['href'], '/')
        self.assertEqual(homepage_by_text['Example Slate']['attributes']['href'], '/petec')
        self.assertEqual(profile_by_text['Example Slate']['attributes']['href'], '/petec')
        self.assertEqual(
            homepage_by_text["Pete's Slate"]['attributes'].get('aria-current'),
            'page',
        )
        self.assertNotIn('aria-current', homepage_by_text['Example Slate']['attributes'])
        self.assertEqual(
            profile_by_text['Example Slate']['attributes'].get('aria-current'),
            'page',
        )
        self.assertNotIn(
            'aria-current',
            profile_by_text["Pete's Slate"]['attributes'],
        )

    def test_overview_renders_the_progressive_subheader_ai_field(self):
        overview = self.client.get('/petec', base_url='http://localhost')
        resume = self.client.get('/petec/resume2', base_url='http://localhost')

        self.assertIn(b'data-overview-subheader-ask', overview.data)
        self.assertIn(b'id="overview-subheader-ai-input"', overview.data)
        self.assertNotIn(b'data-resume-subheader-ask', overview.data)
        self.assertIn(b'data-resume-subheader-ask', resume.data)
        self.assertIn(b'id="subheader-ai-input"', resume.data)


if __name__ == '__main__':
    unittest.main()
