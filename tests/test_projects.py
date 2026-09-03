import hashlib
import json
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlsplit

from app import app


EXPECTED_TOMBSTONE = b'{\n  "retired": true,\n  "projects": []\n}\n'
LEGACY_BOARD_SHA256 = (
    'f3e2e933146005ccb6879737cbc78b691b3411c5fbdbee5d7fbc2796c914b642'
)


class ProjectsBoardTests(unittest.TestCase):
    """Contain the retired board while preserving unrelated public behavior."""

    def setUp(self):
        self.client = app.test_client()

    def assert_direct_redirect(self, path, base_url, expected_location):
        response = self.client.get(path, base_url=base_url)
        self.assertIn(response.status_code, (301, 302, 307, 308))
        self.assertEqual(response.headers['Location'], expected_location)

    # ---- retired board payload containment ----------------------------

    def _fixture(self):
        return (
            Path(__file__).resolve().parents[1]
            / 'static'
            / 'data'
            / 'projects_board.json'
        )

    def test_retired_board_is_the_exact_inert_tombstone(self):
        payload = self._fixture().read_bytes()
        self.assertEqual(payload, EXPECTED_TOMBSTONE)
        self.assertEqual(json.loads(payload), {'retired': True, 'projects': []})
        self.assertNotEqual(
            hashlib.sha256(payload).hexdigest(), LEGACY_BOARD_SHA256
        )

    def test_get_and_query_return_only_the_tombstone(self):
        for path in (
            '/static/data/projects_board.json',
            '/static/data/projects_board.json?cache-bust=privacy-containment',
        ):
            with self.subTest(path=path):
                response = self.client.get(path, base_url='https://peerslate.com')
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.mimetype, 'application/json')
                self.assertEqual(response.data, EXPECTED_TOMBSTONE)
                self.assertNotIn('Set-Cookie', response.headers)
                response.close()

    def test_head_has_the_tombstone_length_and_no_body(self):
        response = self.client.head(
            '/static/data/projects_board.json',
            base_url='https://peerslate.com',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'application/json')
        self.assertEqual(response.data, b'')
        self.assertEqual(
            int(response.headers['Content-Length']), len(EXPECTED_TOMBSTONE)
        )
        self.assertNotIn('Set-Cookie', response.headers)
        response.close()

    def test_conditional_get_never_replays_the_retired_payload(self):
        initial = self.client.get(
            '/static/data/projects_board.json',
            base_url='https://peerslate.com',
        )
        self.assertEqual(initial.status_code, 200)
        self.assertTrue(initial.headers.get('ETag'))
        etag = initial.headers['ETag']
        initial.close()
        response = self.client.get(
            '/static/data/projects_board.json',
            base_url='https://peerslate.com',
            headers={'If-None-Match': etag},
        )
        self.assertEqual(response.status_code, 304)
        self.assertEqual(response.data, b'')
        self.assertNotIn('Set-Cookie', response.headers)
        response.close()

    def test_range_requests_can_return_only_tombstone_bytes(self):
        response = self.client.get(
            '/static/data/projects_board.json',
            base_url='https://peerslate.com',
            headers={'Range': 'bytes=0-19'},
        )
        self.assertEqual(response.status_code, 206)
        self.assertEqual(response.data, EXPECTED_TOMBSTONE[:20])
        self.assertEqual(
            response.headers.get('Content-Range'),
            f'bytes 0-19/{len(EXPECTED_TOMBSTONE)}',
        )
        self.assertNotIn('Set-Cookie', response.headers)
        response.close()

    def test_search_and_sitemap_do_not_advertise_the_retired_board(self):
        home = self.client.get('/', base_url='https://peerslate.com')
        self.assertEqual(home.status_code, 200)
        body = home.get_data(as_text=True)
        block = body.split(
            '<script id="nav-search-data" type="application/json">', 1
        )[1].split('</script>', 1)[0]
        destinations = json.loads(block)
        retired_fragments = ('projects_board.json', '/projects', '/work')
        for destination in destinations:
            href = destination['href']
            with self.subTest(href=href):
                self.assertFalse(any(part in href for part in retired_fragments))

        sitemap = self.client.get(
            '/sitemap.xml', base_url='https://peerslate.com'
        )
        self.assertEqual(sitemap.status_code, 200)
        root = ET.fromstring(sitemap.get_data(as_text=True))
        namespace = {'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        paths = [
            urlsplit(location.text).path
            for location in root.findall('sitemap:url/sitemap:loc', namespace)
        ]
        self.assertTrue(paths)
        self.assertNotIn('/projects', paths)
        self.assertNotIn('/petec/projects', paths)
        self.assertNotIn('/work', paths)
        self.assertNotIn('/petec/work', paths)
        self.assertNotIn('/static/data/projects_board.json', paths)

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
