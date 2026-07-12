import unittest
from html.parser import HTMLParser
from pathlib import Path

from app import app


class ResumeHeaderTabsParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_resume_tabs = False
        self.current_link = None
        self.links = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        classes = attributes.get('class', '').split()
        if tag == 'nav' and 'profile-tabs--resume' in classes:
            self.in_resume_tabs = True
        elif self.in_resume_tabs and tag == 'a':
            self.current_link = {'attributes': attributes, 'text': ''}

    def handle_data(self, data):
        if self.current_link is not None:
            self.current_link['text'] += data

    def handle_endtag(self, tag):
        if self.current_link is not None and tag == 'a':
            self.current_link['text'] = self.current_link['text'].strip()
            self.links.append(self.current_link)
            self.current_link = None
        elif self.in_resume_tabs and tag == 'nav':
            self.in_resume_tabs = False


def constellation_fragment(response_data):
    start_marker = b'<!-- shared-career-constellation:start -->'
    end_marker = b'<!-- shared-career-constellation:end -->'
    start = response_data.index(start_marker) + len(start_marker)
    end = response_data.index(end_marker, start)
    return response_data[start:end].strip()


class Resume2Tests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_legacy_resume_routes_redirect_to_the_canonical_living_resume(self):
        for path in ('/resume', '/petec/resume'):
            with self.subTest(path=path):
                response = self.client.get(path, base_url='http://localhost')
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response.location.endswith('/petec/resume2'))

        canonical = self.client.get('/petec/resume2', base_url='http://localhost')
        self.assertEqual(canonical.status_code, 200)
        self.assertIn(b'class="lr-page resume-v2"', canonical.data)
        self.assertIn(b'css/resume2.css', canonical.data)

    def test_resume_header_tabs_include_one_canonical_resume_link(self):
        response = self.client.get('/petec/resume2', base_url='http://localhost')
        response_text = response.get_data(as_text=True)
        parser = ResumeHeaderTabsParser()
        parser.feed(response_text)

        self.assertEqual(len(parser.links), 6)
        self.assertEqual(
            [link['text'] for link in parser.links],
            ['Overview', 'My Story', 'Evidence', 'Projects', 'Slate Board', 'Resume'],
        )
        current_links = [
            link
            for link in parser.links
            if link['attributes'].get('aria-current') == 'page'
        ]
        self.assertEqual(len(current_links), 1)
        self.assertEqual(current_links[0]['attributes']['href'], '/petec/resume2')
        self.assertNotIn('Resume 1', response_text)

        header_start = response_text.index('<header class="global-header">')
        header_end = response_text.index('</header>', header_start)
        tabs_start = response_text.index('profile-tabs--resume')
        self.assertLess(header_start, tabs_start)
        self.assertLess(tabs_start, header_end)

    def test_profile_slug_routes_do_not_fall_back_to_pete(self):
        adapter = app.url_map.bind('localhost')
        endpoint, view_args = adapter.match('/petec/resume2')

        self.assertEqual(endpoint, 'profile_resume2')
        self.assertEqual(view_args, {'profile_slug': 'petec'})
        self.assertEqual(
            self.client.get('/another-profile/resume').status_code,
            404,
        )
        self.assertEqual(
            self.client.get('/another-profile/resume2').status_code,
            404,
        )

    def test_public_and_internal_routes_render_the_exact_shared_constellation(self):
        preview = self.client.get('/_internal/living-resume-v2', base_url='http://localhost')
        resume2 = self.client.get('/petec/resume2', base_url='http://localhost')

        self.assertEqual(
            constellation_fragment(preview.data),
            constellation_fragment(resume2.data),
        )

        project_root = Path(__file__).resolve().parents[1]
        template = (project_root / 'templates' / 'resume2.html').read_text(encoding='utf-8')
        self.assertIn('{% include "partials/career_constellation.html" %}', template)
        self.assertFalse((project_root / 'templates' / 'living_resume_v2.html').exists())

    def test_resume2_omits_the_retired_micap_example(self):
        response = self.client.get('/petec/resume2', base_url='http://localhost')

        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b'micap', response.data.lower())

    def test_resume2_uses_optimized_background_assets(self):
        project_root = Path(__file__).resolve().parents[1]
        source = project_root / 'static/images/background-templates/mountains.png'
        asset_dir = project_root / 'static/images/mockups/resume2'

        for filename in (
            'resume2-blue-mountain-background.avif',
            'resume2-blue-mountain-background.webp',
            'resume2-blue-mountain-background-mobile.avif',
            'resume2-blue-mountain-background-mobile.webp',
        ):
            asset = asset_dir / filename
            self.assertTrue(asset.is_file())
            self.assertLess(asset.stat().st_size, source.stat().st_size)

    def test_vertical_composition_preserves_semantic_section_order(self):
        response = self.client.get('/petec/resume2', base_url='http://localhost')
        response_text = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('class="r2-vertical-composition"', response_text)
        self.assertIn('css/resume2.css?v=resume2-refine-6', response_text)

        section_positions = [
            response_text.index(f'id="{section_id}"')
            for section_id in (
                'resume-experience',
                'resume-education',
                'resume-skills',
                'resume-development',
            )
        ]
        constellation_position = response_text.index(
            '<!-- shared-career-constellation:start -->'
        )

        self.assertEqual(section_positions, sorted(section_positions))
        self.assertLess(section_positions[-1], constellation_position)

    def test_resume2_renders_twenty_evidence_backed_skill_flip_cards(self):
        response = self.client.get('/petec/resume2', base_url='http://localhost')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data.count(b'class="lr-skill-flip r2-skill-card"'),
            20,
        )
        self.assertIn(b'r2-skill-card__front', response.data)
        self.assertIn(b'r2-skill-card__back', response.data)
        self.assertIn(b'one or two factual examples', response.data)

    def test_profile_tabs_render_everywhere_except_the_root_landing_page(self):
        root = self.client.get('/', base_url='http://localhost')
        self.assertNotIn(b'class="profile-tabs', root.data)

        for path in ('/petec', '/petec/my-story', '/the-slate', '/experience'):
            with self.subTest(path=path):
                response = self.client.get(path, base_url='http://localhost')
                self.assertEqual(response.status_code, 200)
                self.assertIn(b'class="profile-tabs', response.data)
                self.assertNotIn(b'>Experience</a>', response.data)


if __name__ == '__main__':
    unittest.main()
