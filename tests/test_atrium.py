import json
import unittest
from html.parser import HTMLParser
from pathlib import Path

from app import app


class AtriumMarkupParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.slabs = []
        self.selectors = []
        self.enter_links = []
        self.h1_count = 0
        self.story_images = []
        self.in_story_slab = False
        self.story_depth = 0

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        classes = attributes.get('class', '').split()

        if tag == 'h1':
            self.h1_count += 1

        if tag == 'article' and 'triptych-slab' in classes:
            self.slabs.append(attributes)
            if attributes.get('data-triptych-panel') == 'story':
                self.in_story_slab = True
                self.story_depth = 1
            return

        if self.in_story_slab:
            self.story_depth += 1
            if tag == 'img':
                self.story_images.append(attributes)

        if tag == 'button' and 'data-triptych-selector' in attributes:
            self.selectors.append(attributes)

        if tag == 'a' and 'triptych-slab__enter' in classes:
            self.enter_links.append(attributes)

    def handle_endtag(self, tag):
        if not self.in_story_slab:
            return
        self.story_depth -= 1
        if tag == 'article' or self.story_depth <= 0:
            self.in_story_slab = False
            self.story_depth = 0


class AtriumTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project_root = Path(__file__).resolve().parents[1]
        cls.resume = json.loads(
            (cls.project_root / 'static' / 'data' / 'resume_data.json').read_text(
                encoding='utf-8'
            )
        )
        cls.story = json.loads(
            (cls.project_root / 'static' / 'data' / 'story_data.json').read_text(
                encoding='utf-8'
            )
        )

    def setUp(self):
        self.client = app.test_client()

    def render_atrium(self, path='/petec/atrium'):
        response = self.client.get(path, base_url='http://localhost')
        parser = AtriumMarkupParser()
        parser.feed(response.get_data(as_text=True))
        return response, parser

    def test_atrium_routes_render_without_replacing_overview(self):
        for path in ('/atrium', '/petec/atrium'):
            with self.subTest(path=path):
                response, _ = self.render_atrium(path)
                self.assertEqual(response.status_code, 200)
                self.assertIn(b'data-triptych', response.data)
                self.assertIn(b'css/living-triptych.css?v=arrival-1', response.data)
                self.assertIn(b'js/living-triptych.js?v=arrival-1', response.data)

        overview = self.client.get('/petec', base_url='http://localhost')
        self.assertEqual(overview.status_code, 200)
        self.assertNotIn(b'data-triptych', overview.data)

    def test_production_alias_canonicalizes_to_profile_atrium(self):
        response = self.client.get('/atrium', base_url='https://peerslate.com')
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith('/petec/atrium'))

    def test_arrival_has_three_semantic_selectable_slabs_and_destinations(self):
        response, parser = self.render_atrium()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(parser.h1_count, 1)
        self.assertEqual(
            [slab['data-triptych-panel'] for slab in parser.slabs],
            ['story', 'projects', 'resume'],
        )
        self.assertEqual(
            [selector['data-triptych-selector'] for selector in parser.selectors],
            ['story', 'projects', 'resume'],
        )
        self.assertTrue(
            all(selector.get('aria-pressed') == 'false' for selector in parser.selectors)
        )
        self.assertEqual(
            [link['href'] for link in parser.enter_links],
            ['/petec/my-story', '/petec/work', '/petec/resume2'],
        )

    def test_arrival_uses_authentic_profile_story_and_resume_content(self):
        response, parser = self.render_atrium()
        markup = response.get_data(as_text=True)

        self.assertIn(self.resume['profile']['name'], markup)
        for value in self.story['closing_values'][:3]:
            self.assertIn(value['label'], markup)
        for role in self.resume['career_roles']:
            self.assertIn(role['employer'], markup)
            self.assertIn(role['title'], markup)
        self.assertNotIn('MICAP', markup.upper())

        self.assertEqual(len(parser.story_images), 4)
        self.assertTrue(all(image.get('alt', '').strip() for image in parser.story_images))
        for image in parser.story_images:
            source_path = image['src'].split('/static/', 1)[1]
            self.assertTrue((self.project_root / 'static' / source_path).is_file())

    def test_atrium_header_link_and_experimental_metadata_are_unambiguous(self):
        response, _ = self.render_atrium()
        markup = response.get_data(as_text=True)

        self.assertIn('<a href="/petec/atrium" aria-current="page">Atrium</a>', markup)
        self.assertNotIn('aria-label="Pete Carter profile tabs"', markup)
        self.assertIn('<meta name="robots" content="noindex, nofollow">', markup)
        self.assertIn('id="atrium-ai-input"', markup)
        self.assertIn('aria-label="Ask the Slate"', markup)

    def test_arrival_sources_include_accessibility_and_responsive_fallbacks(self):
        css = (
            self.project_root / 'static' / 'css' / 'living-triptych.css'
        ).read_text(encoding='utf-8')
        script = (
            self.project_root / 'static' / 'js' / 'living-triptych.js'
        ).read_text(encoding='utf-8')

        self.assertIn('@media (max-width: 47.9rem)', css)
        self.assertIn('@media (prefers-reduced-motion: reduce)', css)
        self.assertIn('@media (forced-colors: active)', css)
        self.assertIn('min-height: 44px;', css)
        self.assertIn("event.key !== 'Escape'", script)
        self.assertIn("event.key === 'ArrowRight'", script)
        self.assertIn("reducedMotion.addEventListener('change'", script)


if __name__ == '__main__':
    unittest.main()
