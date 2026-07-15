import json
import unittest
from pathlib import Path

from app import app, _load_project_board, _normalize_board_project


class ProjectsBoardTests(unittest.TestCase):
    """Preserve project records while retiring their standalone public pages."""

    def setUp(self):
        self.client = app.test_client()

    def assert_direct_redirect(self, path, base_url, expected_location):
        response = self.client.get(path, base_url=base_url)
        self.assertIn(response.status_code, (301, 302, 307, 308))
        self.assertEqual(response.headers['Location'], expected_location)

    # ---- preserved board data -----------------------------------------

    def _board(self):
        fixture = (
            Path(__file__).resolve().parents[1]
            / 'static'
            / 'data'
            / 'projects_board.json'
        )
        return json.loads(fixture.read_text(encoding='utf-8'))

    def test_board_data_is_profile_scoped_and_loads(self):
        data = _load_project_board('petec')
        self.assertIsNotNone(data)
        self.assertEqual(data['profile_slug'], 'petec')
        self.assertEqual(len(data['projects']), 6)

    def test_unknown_profile_board_fails_safely(self):
        self.assertIsNone(_load_project_board('nobody'))

    def test_partial_project_is_normalized_for_future_reuse(self):
        bare = {'slug': 'wip', 'status': 'on-deck'}
        _normalize_board_project(bare)
        detail = bare['detail']

        self.assertEqual(detail['actions']['view_live']['enabled'], False)
        self.assertIn('category', detail['info'])
        self.assertIn('note', detail['info']['team'])
        for key in (
            'updates',
            'milestones',
            'media',
            'links',
            'notes',
            'key_features',
            'tech_stack',
        ):
            self.assertEqual(detail[key], [])
        self.assertEqual(bare['status_label'], 'On Deck')

    def test_every_project_keeps_the_fields_reusable_views_need(self):
        for project in self._board()['projects']:
            for key in (
                'id',
                'slug',
                'title',
                'summary',
                'status',
                'status_label',
                'tags',
                'card_image',
                'detail',
            ):
                self.assertIn(key, project, f"{project.get('slug')} missing {key}")
            self.assertIn(project['status'], ('active', 'completed', 'on-deck'))
            for key in (
                'about',
                'info',
                'actions',
                'updates',
                'milestones',
                'links',
                'notes',
                'key_features',
            ):
                self.assertIn(
                    key,
                    project['detail'],
                    f"{project['slug']}.detail missing {key}",
                )

    def test_project_fixture_does_not_overclaim_enforced_privacy(self):
        serialized = json.dumps(self._board()).lower()
        self.assertNotIn('only you can see these', serialized)

    # ---- retired project routes ---------------------------------------

    def test_project_index_aliases_redirect_directly_to_resume_experience(self):
        for base_url in ('http://localhost', 'https://peerslate.com'):
            for path in ('/work', '/petec/work', '/projects', '/petec/projects'):
                with self.subTest(base_url=base_url, path=path):
                    self.assert_direct_redirect(
                        path,
                        base_url,
                        '/petec/resume#experience',
                    )

    def test_project_aliases_avoid_redirect_chains_on_the_old_profile_host(self):
        for path in ('/work', '/petec/work', '/projects', '/petec/projects'):
            with self.subTest(path=path):
                self.assert_direct_redirect(
                    path,
                    'https://pete.peerslate.com',
                    'https://peerslate.com/petec/resume#experience',
                )

    def test_unknown_profile_project_routes_remain_404(self):
        for path in ('/nobody/work', '/nobody/projects'):
            with self.subTest(path=path):
                response = self.client.get(path, base_url='http://localhost')
                self.assertEqual(response.status_code, 404)

    # ---- preserved case-study records ---------------------------------

    def _case_study_projects(self):
        fixture = (
            Path(__file__).resolve().parents[1]
            / 'static'
            / 'data'
            / 'resume_data.json'
        )
        return json.loads(fixture.read_text(encoding='utf-8'))['projects']

    def test_case_study_projects_are_ordered_and_profile_scoped(self):
        projects = self._case_study_projects()
        orders = [project['display_order'] for project in projects]
        self.assertEqual(orders, sorted(orders))
        self.assertEqual(projects[0]['slug'], 'interactive-resume')
        self.assertTrue(projects[0]['is_featured'])

    def test_case_study_demo_project_is_flagged_and_never_publishable(self):
        demo = next(
            project for project in self._case_study_projects()
            if project['is_demo']
        )
        self.assertEqual(demo['slug'], 'sample-home-build')
        self.assertFalse(demo['publish_detail'])
        self.assertFalse(demo['details_ready'])

    def test_published_case_study_redirects_to_resume_experience(self):
        path = '/petec/work/interactive-resume'
        for base_url, expected in (
            ('http://localhost', '/petec/resume#experience'),
            ('https://peerslate.com', '/petec/resume#experience'),
            (
                'https://pete.peerslate.com',
                'https://peerslate.com/petec/resume#experience',
            ),
        ):
            with self.subTest(base_url=base_url):
                self.assert_direct_redirect(path, base_url, expected)

    def test_unpublished_and_unknown_projects_have_no_public_route(self):
        for base_url in ('http://localhost', 'https://peerslate.com'):
            for slug in ('senior-project', 'sample-home-build', 'does-not-exist'):
                with self.subTest(base_url=base_url, slug=slug):
                    response = self.client.get(
                        f'/petec/work/{slug}',
                        base_url=base_url,
                    )
                    self.assertEqual(response.status_code, 404)


if __name__ == '__main__':
    unittest.main()
