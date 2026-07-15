import unittest

from app import app


class AtriumRetirementTests(unittest.TestCase):
    """Retired Atrium URLs resolve directly to the platform homepage."""

    def setUp(self):
        self.client = app.test_client()

    def assert_direct_redirect(self, path, base_url, expected_location):
        response = self.client.get(path, base_url=base_url)
        self.assertIn(response.status_code, (301, 302, 307, 308))
        self.assertEqual(response.headers['Location'], expected_location)

    def test_atrium_aliases_redirect_directly_on_local_and_platform_hosts(self):
        for base_url in ('http://localhost', 'https://peerslate.com'):
            for path in ('/atrium', '/petec/atrium'):
                with self.subTest(base_url=base_url, path=path):
                    self.assert_direct_redirect(path, base_url, '/')

    def test_atrium_aliases_avoid_redirect_chains_on_the_old_profile_host(self):
        for path in ('/atrium', '/petec/atrium'):
            with self.subTest(path=path):
                self.assert_direct_redirect(
                    path,
                    'https://pete.peerslate.com',
                    'https://peerslate.com/',
                )


if __name__ == '__main__':
    unittest.main()
