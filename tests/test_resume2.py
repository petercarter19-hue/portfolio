import json
import unittest
from html.parser import HTMLParser
from pathlib import Path

from app import app


class ProfileTabsParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_resume_tabs = False
        self.current_link = None
        self.links = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        classes = attributes.get('class', '').split()
        if tag == 'nav' and 'profile-tabs' in classes:
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

    def assert_direct_redirect(self, path, base_url, expected_location):
        response = self.client.get(path, base_url=base_url)
        self.assertIn(response.status_code, (301, 302, 307, 308))
        self.assertEqual(response.headers['Location'], expected_location)

    def test_resume_is_canonical_and_legacy_routes_redirect_directly(self):
        canonical = self.client.get('/petec/resume', base_url='http://localhost')
        self.assertEqual(canonical.status_code, 200)
        self.assertIn(
            b'class="lr-page resume-v2 resume-consolidated"',
            canonical.data,
        )
        self.assertIn(b'css/resume2.css', canonical.data)

        for base_url in ('http://localhost', 'https://peerslate.com'):
            for path, expected in (
                ('/resume', '/petec/resume'),
                ('/petec/resume2', '/petec/resume'),
                ('/petec/resume-ledger', '/petec/resume#experience'),
            ):
                with self.subTest(base_url=base_url, path=path):
                    self.assert_direct_redirect(path, base_url, expected)

    def test_old_profile_host_redirects_directly_to_canonical_resume(self):
        for path, expected in (
            ('/', 'https://peerslate.com/petec/resume'),
            ('/resume', 'https://peerslate.com/petec/resume'),
            ('/petec/resume', 'https://peerslate.com/petec/resume'),
            ('/petec/resume2', 'https://peerslate.com/petec/resume'),
            (
                '/petec/resume-ledger',
                'https://peerslate.com/petec/resume#experience',
            ),
        ):
            with self.subTest(path=path):
                self.assert_direct_redirect(
                    path,
                    'https://pete.peerslate.com',
                    expected,
                )

    def test_retired_overview_aliases_redirect_directly_to_resume(self):
        aliases = ('/petec', '/portfolio', '/pete', '/overview', '/petec/overview')
        for base_url in ('http://localhost', 'https://peerslate.com'):
            for path in aliases:
                with self.subTest(base_url=base_url, path=path):
                    self.assert_direct_redirect(
                        path,
                        base_url,
                        '/petec/resume',
                    )

        for path in aliases:
            with self.subTest(base_url='https://pete.peerslate.com', path=path):
                self.assert_direct_redirect(
                    path,
                    'https://pete.peerslate.com',
                    'https://peerslate.com/petec/resume',
                )

    def test_canonical_resume_tag_points_directly_to_the_rendered_route(self):
        for base_url, expected in (
            ('http://localhost', 'http://localhost/petec/resume'),
            ('https://peerslate.com', 'https://peerslate.com/petec/resume'),
        ):
            with self.subTest(base_url=base_url):
                response = self.client.get('/petec/resume', base_url=base_url)
                self.assertEqual(response.status_code, 200)
                self.assertIn(
                    f'<link rel="canonical" href="{expected}">'.encode(),
                    response.data,
                )

    def test_platform_experience_and_profile_evidence_routes_remain_public(self):
        for path in ('/experience', '/petec/skills'):
            with self.subTest(path=path):
                response = self.client.get(path, base_url='http://localhost')
                self.assertEqual(response.status_code, 200)

    def test_resume_header_tabs_include_one_canonical_resume_link(self):
        response = self.client.get('/petec/resume', base_url='http://localhost')
        response_text = response.get_data(as_text=True)
        parser = ProfileTabsParser()
        parser.feed(response_text)

        self.assertEqual(len(parser.links), 4)
        self.assertEqual(
            [link['text'] for link in parser.links],
            ['My Story', 'Evidence', 'Slate Board', 'Resume'],
        )
        current_links = [
            link
            for link in parser.links
            if link['attributes'].get('aria-current') == 'page'
        ]
        self.assertEqual(len(current_links), 1)
        self.assertEqual(current_links[0]['attributes']['href'], '/petec/resume')
        self.assertNotIn('Resume 1', response_text)

        header_start = response_text.index('<header class="global-header">')
        header_end = response_text.index('</header>', header_start)
        tabs_start = response_text.index('profile-tabs--resume')
        self.assertLess(header_start, tabs_start)
        self.assertLess(tabs_start, header_end)

    def test_profile_slug_routes_do_not_fall_back_to_pete(self):
        adapter = app.url_map.bind('localhost')
        endpoint, view_args = adapter.match('/petec/resume')

        self.assertEqual(endpoint, 'profile_resume')
        self.assertEqual(view_args, {'profile_slug': 'petec'})

        legacy_endpoint, legacy_args = adapter.match('/petec/resume2')
        self.assertEqual(legacy_endpoint, 'profile_resume2')
        self.assertEqual(legacy_args, {'profile_slug': 'petec'})
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
        resume2 = self.client.get('/petec/resume', base_url='http://localhost')

        self.assertEqual(
            constellation_fragment(preview.data),
            constellation_fragment(resume2.data),
        )

        project_root = Path(__file__).resolve().parents[1]
        template = (project_root / 'templates' / 'resume2.html').read_text(encoding='utf-8')
        self.assertIn('{% include "partials/career_constellation.html" %}', template)
        self.assertFalse((project_root / 'templates' / 'living_resume_v2.html').exists())

    def test_resume2_omits_the_retired_micap_example(self):
        response = self.client.get('/petec/resume', base_url='http://localhost')

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

    def test_constellation_is_full_width_without_scroll_triggered_expansion(self):
        project_root = Path(__file__).resolve().parents[1]
        resume_css = (project_root / 'static' / 'css' / 'resume2.css').read_text(
            encoding='utf-8'
        )
        resume_js = (
            project_root / 'static' / 'js' / 'living-resume-v2.js'
        ).read_text(encoding='utf-8')

        self.assertIn(
            '.resume-v2 .lr-constellation {\n    width: 100%;',
            resume_css,
        )
        self.assertNotIn('is-fullstage', resume_css)
        self.assertNotIn('is-fullstage', resume_js)
        self.assertNotIn('stageObserver', resume_js)

    def test_vertical_composition_preserves_semantic_section_order(self):
        response = self.client.get('/petec/resume', base_url='http://localhost')
        response_text = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('class="lr-page resume-v2 resume-consolidated"', response_text)
        self.assertIn(
            'css/resume2.css?v=resume-consolidated-4',
            response_text,
        )

        section_positions = [
            response_text.index(f'id="{section_id}"')
            for section_id in (
                'summary',
                'impact',
                'skills',
                'experience',
                'credentials',
            )
        ]
        constellation_position = response_text.index(
            '<!-- shared-career-constellation:start -->'
        )

        self.assertEqual(section_positions, sorted(section_positions))
        self.assertLess(section_positions[-1], constellation_position)

    def test_resume2_renders_each_configured_evidence_backed_skill_control(self):
        response = self.client.get('/petec/resume', base_url='http://localhost')
        fixture_path = (
            Path(__file__).resolve().parents[1]
            / 'static'
            / 'data'
            / 'resume_data.json'
        )
        fixture = json.loads(fixture_path.read_text(encoding='utf-8'))
        expected_skill_count = len(
            fixture['living_resume']['resume2_featured_skill_ids']
        )

        skills_by_id = {skill['id']: skill for skill in fixture['skills']}
        rendered_skill_count = 0
        for group in fixture['living_resume']['resume2_skill_categories']:
            matching_skills = [
                skills_by_id[skill_id]
                for skill_id in fixture['living_resume']['resume2_featured_skill_ids']
                if skill_id in skills_by_id
                and skills_by_id[skill_id].get('category_id')
                in group['source_category_ids']
                and any(
                    'micap' not in item['text'].lower()
                    for item in skills_by_id[skill_id].get('evidence_items', [])
                )
            ]
            rendered_skill_count += min(3, len(matching_skills))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(expected_skill_count, 16)
        self.assertEqual(
            response.data.count(b'data-r2-skill-toggle='),
            rendered_skill_count,
        )
        self.assertEqual(rendered_skill_count, 12)
        self.assertEqual(
            response.data.count(b'data-r2-skill-panel='),
            rendered_skill_count,
        )
        self.assertIn(b'data-r2-skill-overview', response.data)
        self.assertIn(b'View Full Evidence', response.data)
        self.assertIn(b'Ask Pete About This', response.data)

    def test_development_section_lists_every_forward_credential(self):
        # Skills & Evidence was moved out of the vertical composition into the
        # Experience header, so the old composition-grid guard no longer
        # applies. Development still renders its full set of credentials.
        response = self.client.get('/petec/resume', base_url='http://localhost')
        response_text = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        development_start = response_text.index(
            'data-r2-credential-panel="development"'
        )
        development_end = response_text.index(
            'data-r2-credential-panel="recognition"',
            development_start,
        )
        development_html = response_text[development_start:development_end]
        self.assertEqual(development_html.count('class="r2-credential-record"'), 3)
        self.assertIn('Microsoft Azure Fundamentals', development_html)
        self.assertIn('Microsoft Azure AI Fundamentals', development_html)
        self.assertIn('AWS Certified Cloud Practitioner', development_html)

    def test_consolidated_opening_reuses_the_professional_overview_scene(self):
        response = self.client.get('/petec/resume', base_url='http://localhost')

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'id="summary"', response.data)
        self.assertIn(b'images/story/pete-headshot.jpg', response.data)
        self.assertIn(b'Professional portrait of Pete Carter', response.data)
        self.assertIn(b'Engineer at heart. Leader in practice.', response.data)
        self.assertIn(b'Systems Engineer &amp; Technical Leader', response.data)
        self.assertIn(b'r2-ai-card resume-ai-panel', response.data)
        self.assertNotIn(b'images/story/danielle', response.data.lower())

    def test_career_impact_renders_the_five_approved_metrics_in_order(self):
        response = self.client.get('/petec/resume', base_url='http://localhost')
        response_text = response.get_data(as_text=True)
        impact_start = response_text.index('id="impact"')
        impact_end = response_text.index('id="skills"', impact_start)
        impact_html = response_text[impact_start:impact_end]

        values = ('30+', '9 / $19.2M', '$36M+', '35%', '70%')
        positions = [impact_html.index(value) for value in values]
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(impact_html.count('class="r2-impact__item"'), 5)
        self.assertNotIn('micap', impact_html.lower())

    def test_experience_uses_vertical_cards_and_inline_full_chapters(self):
        response = self.client.get('/petec/resume', base_url='http://localhost')
        response_text = response.get_data(as_text=True)
        experience_start = response_text.index('id="experience"')
        experience_end = response_text.index('id="credentials"', experience_start)
        experience_html = response_text[experience_start:experience_end]

        self.assertEqual(experience_html.count('data-r2-exp-card='), 3)
        self.assertEqual(experience_html.count('data-r2-exp-toggle'), 3)
        self.assertEqual(experience_html.count('View Full Chapter'), 3)
        self.assertEqual(experience_html.count('role="region"'), 3)
        self.assertEqual(experience_html.count('tabindex="-1"'), 3)
        self.assertIn('aria-label="View full Northrop Grumman chapter"', experience_html)
        self.assertIn('5 supporting records', experience_html)
        self.assertIn('9 supporting records', experience_html)
        self.assertIn('13 supporting records', experience_html)
        self.assertIn('data-r2-exp-card="northrop"', experience_html)
        self.assertIn('data-r2-exp-card="l3harris"', experience_html)
        self.assertIn('data-r2-exp-card="dod"', experience_html)

        northrop_start = experience_html.index('data-r2-exp-card="northrop"')
        l3_start = experience_html.index('data-r2-exp-card="l3harris"')
        dod_start = experience_html.index('data-r2-exp-card="dod"')
        northrop_html = experience_html[northrop_start:l3_start]
        l3_html = experience_html[l3_start:dod_start]
        dod_html = experience_html[dod_start:]
        self.assertIn('<strong>DOORS</strong>', northrop_html)
        self.assertIn('Bidirectional traceability', northrop_html)
        self.assertIn('<strong>MBSE</strong>', northrop_html)
        self.assertIn('Architecture alignment', northrop_html)
        self.assertIn('<strong>$9.1M</strong>', l3_html)
        self.assertIn('<strong>12</strong>', l3_html)
        self.assertIn('IPS elements', l3_html)
        self.assertIn('<strong>30+</strong>', dod_html)
        self.assertIn('<strong>35%</strong>', dod_html)
        self.assertIn('Faster issue-to-action', dod_html)

        project_root = Path(__file__).resolve().parents[1]
        javascript = (project_root / 'static/js/living-resume-v2.js').read_text(
            encoding='utf-8'
        )
        stylesheet = (project_root / 'static/css/resume2.css').read_text(
            encoding='utf-8'
        )
        self.assertIn("'Close Chapter' : 'View Full Chapter'", javascript)
        self.assertIn("cards.find((card) => card.classList.contains('is-open'))", javascript)
        self.assertIn("full.focus({ preventScroll: true })", javascript)
        self.assertIn("closeAll({ restoreFocus: true })", javascript)
        self.assertIn("activeOrigin = origin", javascript)
        self.assertIn('grid-template-columns: repeat(3, minmax(0, 1fr));', stylesheet)
        self.assertIn(
            '.resume-consolidated .r2-exp-stage.is-expanded .r2-experience-card.is-aside',
            stylesheet,
        )

    def test_credentials_render_four_categories_with_inline_details(self):
        response = self.client.get('/petec/resume', base_url='http://localhost')
        response_text = response.get_data(as_text=True)
        credentials_start = response_text.index('id="credentials"')
        credentials_end = response_text.index(
            '<!-- shared-career-constellation:start -->',
            credentials_start,
        )
        credentials_html = response_text[credentials_start:credentials_end]

        self.assertEqual(credentials_html.count('data-r2-credential-toggle='), 4)
        self.assertEqual(credentials_html.count('data-r2-credential-panel='), 4)
        self.assertIn('aria-label="Open Education category"', credentials_html)
        for heading in (
            'Education',
            'Certifications',
            'Professional Development',
            'Recognition &amp; Achievements',
        ):
            self.assertIn(heading, credentials_html)
        self.assertIn('Systems Engineering Ph.D.', credentials_html)
        self.assertIn('Expected January 2027 start', credentials_html)
        self.assertIn('Admitted', credentials_html)
        self.assertNotIn('clearance', credentials_html.lower())

    def test_profile_tabs_render_everywhere_except_the_root_landing_page(self):
        root = self.client.get('/', base_url='http://localhost')
        self.assertNotIn(b'class="profile-tabs', root.data)

        for path in (
            '/petec/resume',
            '/petec/my-story',
            '/petec/skills',
            '/petec/slate-board',
            '/the-slate',
            '/experience',
        ):
            with self.subTest(path=path):
                response = self.client.get(path, base_url='http://localhost')
                self.assertEqual(response.status_code, 200)
                self.assertIn(b'class="profile-tabs', response.data)
                parser = ProfileTabsParser()
                parser.feed(response.get_data(as_text=True))
                self.assertEqual(
                    [link['text'] for link in parser.links],
                    ['My Story', 'Evidence', 'Slate Board', 'Resume'],
                )


if __name__ == '__main__':
    unittest.main()
