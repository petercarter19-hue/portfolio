import json
import unittest
from pathlib import Path

from app import app


class ProjectsExhibitionTests(unittest.TestCase):
    """The cinematic Projects exhibition + case-study routes.

    Locks in the master brief's guarantees: data-driven panels, truthful
    content (no fictional mockup text), demo/incomplete gating, and the
    accessibility scaffolding.
    """

    def setUp(self):
        self.client = app.test_client()

    def _get(self, path):
        response = self.client.get(path, base_url='http://localhost')
        self.assertEqual(response.status_code, 200)
        return response.get_data(as_text=True)

    # ---- data ----------------------------------------------------------

    def _projects(self):
        fixture = Path(__file__).resolve().parents[1] / 'static/data/resume_data.json'
        return json.loads(fixture.read_text(encoding='utf-8'))['projects']

    def test_projects_are_ordered_and_profile_scoped(self):
        projects = self._projects()
        orders = [p['display_order'] for p in projects]
        self.assertEqual(orders, sorted(orders))
        self.assertEqual(projects[0]['slug'], 'interactive-resume')
        self.assertTrue(projects[0]['is_featured'])

    def test_demo_project_is_flagged_and_never_publishable(self):
        demo = next(p for p in self._projects() if p['is_demo'])
        self.assertEqual(demo['slug'], 'sample-home-build')
        self.assertFalse(demo['publish_detail'])
        self.assertFalse(demo['details_ready'])

    # ---- exhibition index ----------------------------------------------

    def test_exhibition_renders_every_panel_in_order(self):
        html = self._get('/petec/work')
        positions = [
            html.index(f'data-pjx-slug="{slug}"')
            for slug in ('interactive-resume', 'senior-project', 'sample-home-build')
        ]
        self.assertEqual(positions, sorted(positions))
        # One panel per project + a selector dot each.
        self.assertEqual(html.count('data-pjx-panel='), 3)
        self.assertEqual(html.count('data-pjx-goto='), 3)

    def test_exhibition_begins_with_the_work_not_the_profile_band(self):
        html = self._get('/petec/work')
        self.assertNotIn('profile-header', html.split('class="pjx"')[0].split('main-content')[-1])
        self.assertIn('Ideas become systems. Systems become something people can use.', html)

    def test_demo_notice_is_always_rendered(self):
        html = self._get('/petec/work')
        self.assertIn('Demonstration project', html)
        self.assertIn('Not a real portfolio project or outcome.', html)

    def test_incomplete_project_shows_documentation_message(self):
        html = self._get('/petec/work')
        self.assertIn('Case study in preparation', html)
        self.assertIn('Project details are being documented.', html)

    def test_no_fictional_mockup_content_is_published(self):
        banned = (
            'Next.js', 'Tailwind', 'OpenAI', 'Aether', 'Founder &amp; Developer',
            '10,000+', 'Mercer', 'Senior Product Designer',
        )
        for path in ('/petec/work', '/petec/work/interactive-resume'):
            html = self._get(path)
            for term in banned:
                with self.subTest(path=path, term=term):
                    self.assertNotIn(term, html)

    def test_exhibition_accessibility_scaffolding(self):
        html = self._get('/petec/work')
        self.assertIn('aria-live="polite"', html)
        self.assertIn('aria-label="Previous project"', html)
        self.assertIn('aria-label="Next project"', html)
        css = self._get('/static/css/projects-exhibition.css')
        self.assertIn('prefers-reduced-motion', css)
        self.assertIn('forced-colors', css)

    # ---- case study -----------------------------------------------------

    def test_case_study_renders_all_six_chapters_with_real_tech(self):
        html = self._get('/petec/work/interactive-resume')
        for key in ('idea', 'problem', 'role', 'build', 'decisions', 'result'):
            self.assertIn(f'id="chapter-{key}"', html)
        for tech in ('Python', 'Flask', 'Jinja', 'JavaScript', 'JSON'):
            self.assertIn(f'<li>{tech}</li>', html)
        self.assertIn('Back to Projects', html)
        self.assertIn('Open live build', html)
        self.assertIn('/petec/resume2', html)

    def test_incomplete_demo_and_unknown_projects_have_no_detail_page(self):
        for slug in ('senior-project', 'sample-home-build', 'does-not-exist'):
            with self.subTest(slug=slug):
                response = self.client.get(
                    f'/petec/work/{slug}', base_url='http://localhost'
                )
                self.assertEqual(response.status_code, 404)


if __name__ == '__main__':
    unittest.main()
