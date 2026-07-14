import json
import unittest
from pathlib import Path

from app import app, _load_project_board, _normalize_board_project


class ProjectsBoardTests(unittest.TestCase):
    """The Projects Board index (/petec/work) + the still-live case-study route.

    The page was rebuilt (2026-07-13) from the cinematic exhibition into a
    simple, data-driven card grid with a Project Detail modal. These tests lock
    in: profile-scoped data-driven rendering, the six detail tabs, the real
    PeerSlate content, truthful (non-fictional) copy, and the a11y scaffolding.
    The separate case-study route still reads the resume_data.json projects.
    """

    def setUp(self):
        self.client = app.test_client()

    def _get(self, path):
        response = self.client.get(path, base_url='http://localhost')
        self.assertEqual(response.status_code, 200)
        return response.get_data(as_text=True)

    # ---- board data ----------------------------------------------------

    def _board(self):
        fixture = Path(__file__).resolve().parents[1] / 'static/data/projects_board.json'
        return json.loads(fixture.read_text(encoding='utf-8'))

    def test_board_data_is_profile_scoped_and_loads(self):
        data = _load_project_board('petec')
        self.assertIsNotNone(data)
        self.assertEqual(data['profile_slug'], 'petec')
        self.assertEqual(len(data['projects']), 6)

    def test_unknown_profile_board_fails_safely(self):
        self.assertIsNone(_load_project_board('nobody'))

    def test_partial_project_is_normalized_and_does_not_crash_the_page(self):
        # A project captured before its detail is written must still render.
        bare = {'slug': 'wip', 'status': 'on-deck'}
        _normalize_board_project(bare)
        d = bare['detail']
        # Every nested object the template reaches into now exists.
        self.assertEqual(d['actions']['view_live']['enabled'], False)
        self.assertIn('category', d['info'])
        self.assertIn('note', d['info']['team'])
        for key in ('updates', 'milestones', 'media', 'links', 'notes',
                    'key_features', 'tech_stack'):
            self.assertEqual(d[key], [])
        self.assertEqual(bare['status_label'], 'On Deck')

    def test_multi_tenant_route_serves_petec_and_404s_unknown(self):
        self.assertEqual(
            self.client.get('/petec/work', base_url='http://localhost').status_code, 200)
        self.assertEqual(
            self.client.get('/nobody/work', base_url='http://localhost').status_code, 404)

    def test_notes_label_does_not_overclaim_enforced_privacy(self):
        # AGENTS.md: never imply production privacy the backend does not enforce.
        html = self._get('/petec/work')
        self.assertNotIn('only you can see these', html)

    def test_every_project_has_the_fields_the_template_needs(self):
        for p in self._board()['projects']:
            for key in ('id', 'slug', 'title', 'summary', 'status',
                        'status_label', 'tags', 'card_image', 'detail'):
                self.assertIn(key, p, f"{p.get('slug')} missing {key}")
            self.assertIn(p['status'], ('active', 'completed', 'on-deck'))
            d = p['detail']
            for key in ('about', 'info', 'actions', 'updates',
                        'milestones', 'links', 'notes', 'key_features'):
                self.assertIn(key, d, f"{p['slug']}.detail missing {key}")

    # ---- board index ---------------------------------------------------

    def test_board_renders_every_project_card_in_order(self):
        html = self._get('/petec/work')
        slugs = [p['slug'] for p in self._board()['projects']]
        positions = [html.index(f'data-pb-open="{slug}"') for slug in slugs]
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(html.count('data-pb-card'), len(slugs))
        # One pre-rendered detail panel per project.
        for slug in slugs:
            self.assertIn(f'data-detail="{slug}"', html)

    def test_board_begins_with_the_work_not_the_profile_band(self):
        html = self._get('/petec/work')
        before_board = html.split('data-pb')[0]
        self.assertNotIn('profile-header', before_board.split('main-content')[-1])
        self.assertIn('building, shipping, and learning from', html)

    def test_board_has_status_filters_and_search(self):
        html = self._get('/petec/work')
        for status in ('all', 'active', 'completed', 'on-deck'):
            self.assertIn(f'data-pb-filter="{status}"', html)
        self.assertIn('placeholder="Search projects..."', html)
        self.assertIn('New Project', html)

    def test_status_badges_match_the_data(self):
        html = self._get('/petec/work')
        for p in self._board()['projects']:
            self.assertIn(f'pb-badge--{p["status"]}', html)

    def test_every_detail_has_all_six_tabs(self):
        html = self._get('/petec/work')
        for tab in ('overview', 'updates', 'milestones', 'media', 'links', 'notes'):
            self.assertIn(f'data-pb-tab="{tab}"', html)
            self.assertIn(f'data-pb-panel="{tab}"', html)
        self.assertIn('View all updates', html)

    # ---- the real PeerSlate content ------------------------------------

    def test_peerslate_project_has_real_content(self):
        html = self._get('/petec/work')
        # GitHub link is live; View Live + Roadmap are intentionally disabled.
        self.assertIn('https://github.com/petercarter19-hue/portfolio', html)
        # Real milestones the owner called out.
        self.assertIn('My Story MVP', html)
        self.assertIn('Living Résumé MVP', html)
        # Real links.
        self.assertIn('peerslate.com', html)
        self.assertIn('Microsoft Azure', html)
        # Real tech stack (not the mockup's placeholder React/Node stack).
        for tech in ('Python', 'Flask', 'PostgreSQL', 'Azure'):
            self.assertIn(f'>{tech}</span>', html)

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

    # ---- accessibility scaffolding -------------------------------------

    def test_board_accessibility_scaffolding(self):
        html = self._get('/petec/work')
        self.assertIn('role="dialog"', html)
        self.assertIn('aria-modal="true"', html)
        self.assertIn('role="tablist"', html)
        self.assertIn('role="tab"', html)
        self.assertIn('role="tabpanel"', html)
        self.assertIn('aria-haspopup="dialog"', html)
        css = self._get('/static/css/projects-board.css')
        self.assertIn('prefers-reduced-motion', css)
        self.assertIn('focus-visible', css)

    # ---- case study (unchanged legacy route) ---------------------------

    def _case_study_projects(self):
        fixture = Path(__file__).resolve().parents[1] / 'static/data/resume_data.json'
        return json.loads(fixture.read_text(encoding='utf-8'))['projects']

    def test_case_study_projects_are_ordered_and_profile_scoped(self):
        projects = self._case_study_projects()
        orders = [p['display_order'] for p in projects]
        self.assertEqual(orders, sorted(orders))
        self.assertEqual(projects[0]['slug'], 'interactive-resume')
        self.assertTrue(projects[0]['is_featured'])

    def test_case_study_demo_project_is_flagged_and_never_publishable(self):
        demo = next(p for p in self._case_study_projects() if p['is_demo'])
        self.assertEqual(demo['slug'], 'sample-home-build')
        self.assertFalse(demo['publish_detail'])
        self.assertFalse(demo['details_ready'])

    def test_case_study_renders_all_six_chapters_with_real_tech(self):
        html = self._get('/petec/work/interactive-resume')
        for key in ('idea', 'problem', 'role', 'build', 'decisions', 'result'):
            self.assertIn(f'id="chapter-{key}"', html)
        for tech in ('Python', 'Flask', 'Jinja', 'JavaScript', 'JSON'):
            self.assertIn(f'<li>{tech}</li>', html)
        self.assertIn('Back to Projects', html)
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
