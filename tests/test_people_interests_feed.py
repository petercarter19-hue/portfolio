"""Retirement guards for the removed colorful Community board."""

import os
import unittest

from app import app


class RetiredCommunitySurfaceTests(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_old_page_address_redirects_to_canonical_community(self):
        response = self.client.get('/the-slate/people-interests')
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith('/the-slate'))

    def test_old_people_api_is_no_longer_registered(self):
        for path in ('/api/feed/people-interests', '/api/feed/posts/pi-example'):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 404)

    def test_retired_planning_routes_redirect_to_board_sections(self):
        expectations = {
            '/the-slate/my-slate': '/petec/slate-board#paths-and-milestones',
            '/the-slate/daily': '/petec/slate-board#daily-check-in',
            '/the-slate/paths': '/petec/slate-board#paths-and-milestones',
        }
        for path, destination in expectations.items():
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response.location.endswith(destination))

    def test_retired_feed_layers_redirect_in_one_hop(self):
        for path in ('/the-slate/progress', '/the-slate/pulse', '/the-slate/break',
                     '/slate-feed', '/slate-feed/pulse', '/slate-feed/break', '/slate-feed/people'):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response.location.endswith('/the-slate'))

    def test_retired_source_files_are_removed(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for rel in (
            'people_interests_api.py',
            'services/people_interests_feed.py',
            'templates/the_slate_people_interests.html',
            'static/js/people-interests.js',
            'static/css/people-interests.css',
            'static/data/people_interests_feed.json',
        ):
            self.assertFalse(os.path.exists(os.path.join(root, rel)), rel)


if __name__ == '__main__':
    unittest.main()
