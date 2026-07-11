import unittest
from html.parser import HTMLParser
from pathlib import Path

from app import app


class ResumeSwitchParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_switch = False
        self.links = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        classes = attributes.get('class', '').split()
        if tag == 'nav' and 'resume-version-switch' in classes:
            self.in_switch = True
        elif self.in_switch and tag == 'a':
            self.links.append(attributes)

    def handle_endtag(self, tag):
        if self.in_switch and tag == 'nav':
            self.in_switch = False


def constellation_fragment(response_data):
    start_marker = b'<!-- shared-career-constellation:start -->'
    end_marker = b'<!-- shared-career-constellation:end -->'
    start = response_data.index(start_marker) + len(start_marker)
    end = response_data.index(end_marker, start)
    return response_data[start:end].strip()


class Resume2Tests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_resume1_and_resume2_render_as_separate_compositions(self):
        resume1 = self.client.get('/petec/resume', base_url='http://localhost')
        resume2 = self.client.get('/petec/resume2', base_url='http://localhost')

        self.assertEqual(resume1.status_code, 200)
        self.assertEqual(resume2.status_code, 200)
        self.assertNotIn(b'class="lr-page resume-v2"', resume1.data)
        self.assertIn(b'class="lr-page resume-v2"', resume2.data)
        self.assertIn(b'css/resume2.css', resume2.data)

    def test_version_switch_has_one_current_link_on_each_page(self):
        for path, active_href in (
            ('/petec/resume', '/petec/resume'),
            ('/petec/resume2', '/petec/resume2'),
        ):
            with self.subTest(path=path):
                response = self.client.get(path, base_url='http://localhost')
                parser = ResumeSwitchParser()
                parser.feed(response.get_data(as_text=True))

                self.assertEqual(len(parser.links), 2)
                self.assertEqual(
                    {link['href'] for link in parser.links},
                    {'/petec/resume', '/petec/resume2'},
                )
                current_links = [
                    link for link in parser.links if link.get('aria-current') == 'page'
                ]
                self.assertEqual(len(current_links), 1)
                self.assertEqual(current_links[0]['href'], active_href)

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

    def test_both_versions_render_the_exact_shared_constellation(self):
        resume1 = self.client.get('/petec/resume', base_url='http://localhost')
        resume2 = self.client.get('/petec/resume2', base_url='http://localhost')

        self.assertEqual(
            constellation_fragment(resume1.data),
            constellation_fragment(resume2.data),
        )

        project_root = Path(__file__).resolve().parents[1]
        for template_name in ('living_resume_v2.html', 'resume2.html'):
            template = (project_root / 'templates' / template_name).read_text(
                encoding='utf-8'
            )
            self.assertIn(
                '{% include "partials/career_constellation.html" %}',
                template,
            )

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


if __name__ == '__main__':
    unittest.main()
