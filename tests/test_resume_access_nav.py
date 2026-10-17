"""Published resume access without authentication or private-draft changes."""
import unittest
from flask import request

from app import app, shared_navigation_urls
from tests.test_shared_shell_convergence import _links, _search_records


class ResumeAccessNavigationTests(unittest.TestCase):
    def setUp(self):
        keys = ('TESTING', 'PEERSLATE_ALLOW_DEV_IDENTITY', 'PEERSLATE_DEV_USER_KEY')
        self.original = {key: app.config.get(key) for key in keys}
        app.config.update(TESTING=True, PEERSLATE_ALLOW_DEV_IDENTITY=False,
                          PEERSLATE_DEV_USER_KEY=None)
        self.client = app.test_client()

    def tearDown(self):
        app.config.update(self.original)

    def test_anonymous_representations_have_exactly_two_working_destinations(self):
        # PS-SITE-SHELL-ROUND5-001 (Pete, 2026-10-13): My Resume and My Story,
        # Pete's public demo pages; everything else is plain-text Soon.
        expected = [('My Resume', '/petec/resume#resume-start'),
                    ('My Story', '/petec/my-story')]
        for path in ('/', '/petec/resume', '/interview-studio?mode=ai'):
            response = self.client.get(path)
            self.assertEqual(200, response.status_code)
            html = response.get_data(as_text=True)
            for marker, end in (('<nav class="ps-top__nav"', '</nav>'),
                                ('<ul class="platform-menu__links"', '</ul>'),
                                ('<ul class="platform-nojs-navigation__links"', '</ul>')):
                with self.subTest(path=path, marker=marker):
                    self.assertEqual(expected, [(link['text'], link['href'])
                                               for link in _links(html, marker, end)])
            # The header search field is gone; its index keeps its own records.
            self.assertEqual([('My Resume', '/petec/resume#resume-start'),
                              ('Interview AI', '/interview-studio?mode=ai')],
                             [(item['title'], item['href']) for item in _search_records(html)])
        resume = self.client.get(expected[0][1])
        self.assertEqual(200, resume.status_code)
        self.assertIn(b'Pete Carter', resume.data)
        self.assertIn(b'id="resume-start"', resume.data)
        story = self.client.get(expected[1][1])
        self.assertEqual(200, story.status_code)
        self.assertIn(b'Pete', story.data)
        interview = self.client.get('/interview-studio?mode=ai')
        self.assertEqual(200, interview.status_code)
        self.assertIn(b'data-initial-mode="ai"', interview.data)
        self.assertIn(b'id="is-panel-ai"', interview.data)

    def test_pete_subdomain_uses_the_existing_canonical_resume(self):
        with app.test_request_context('/', base_url='https://pete.peerslate.com'):
            links = shared_navigation_urls()['shell_destinations']
            self.assertEqual('https://peerslate.com/petec/resume#resume-start', links[0]['href'])
            self.assertEqual('/interview-studio?mode=ai', links[1]['href'])

    def test_signed_in_workspace_and_account_offer_explicit_public_resume(self):
        app.config.update(PEERSLATE_ALLOW_DEV_IDENTITY=True,
                          PEERSLATE_DEV_USER_KEY='resume-access-test-member')
        response = self.client.get('/app')
        self.assertEqual(200, response.status_code)
        html = response.get_data(as_text=True)
        self.assertIn('>Public Resume</span>', html)
        public_resume = next(item for item in _search_records(html)
                             if item['title'] == 'Public Resume')
        self.assertEqual('/petec/resume#resume-start', public_resume['href'])
        self.assertEqual("Pete Carter's published career record", public_resume['sub'])
        with app.test_request_context('/app'):
            account = shared_navigation_urls()['account_destinations']
        self.assertIn(('Public Resume', '/petec/resume#resume-start'),
                      [(item['label'], item['href']) for item in account])

    def test_signed_in_phones_get_no_global_bottom_bar(self):
        # PS-SITE-SHELL-ROUND5-001 (manager ruling 2026-10-15): the signed-in
        # phone bar is retired; the header Menu carries the round-5 list.
        app.config.update(PEERSLATE_ALLOW_DEV_IDENTITY=True,
                          PEERSLATE_DEV_USER_KEY='resume-access-test-member')
        for path in ('/', '/petec/resume', '/interview-studio?mode=ai', '/app'):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(200, response.status_code)
                html = response.get_data(as_text=True)
                self.assertNotIn('data-global-tabsource', html)
                self.assertIn('data-platform-menu-toggle', html)
                soon = html.split('<ul class="platform-menu__soon">', 1)[1].split('</ul>', 1)[0]
                self.assertIn('<li>Interview Studio</li>', soon)

    def test_generic_member_navigation_has_no_pete_fixture_targets(self):
        with app.test_request_context('/another-member/resume'):
            self.assertEqual('profile_resume', request.endpoint)
            groups = shared_navigation_urls()
            for name in ('shell_destinations', 'phone_destinations',
                         'account_destinations', 'launchpad_destinations',
                         'public_search_destinations', 'member_search_destinations'):
                with self.subTest(group=name):
                    self.assertFalse(any('/petec' in item['href'] for item in groups[name]))

    def test_account_keeps_workspace_return_on_public_pages_without_private_duplicate(self):
        for path in ('/', '/petec/resume', '/interview-studio?mode=ai'):
            with self.subTest(path=path), app.test_request_context(path):
                account = shared_navigation_urls()['account_destinations']
                self.assertEqual(1, sum(item['href'] == '/app' for item in account))
        with app.test_request_context('/app'):
            groups = shared_navigation_urls()
            self.assertFalse(any(item['href'] == '/app' for item in groups['account_destinations']))
            self.assertEqual(1, sum(item['href'] == '/app' for item in groups['shell_destinations']))

    def test_private_workspace_stays_protected(self):
        response = self.client.get('/app')
        self.assertEqual(302, response.status_code)
        self.assertEqual('/auth/sign-in?return_to=/app', response.headers['Location'])
