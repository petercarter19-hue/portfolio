import unittest

from app import app


class DarkThemeAvailabilityTests(unittest.TestCase):
    CONFIG_KEY = 'PEERSLATE_DARK_THEME_ENABLED'

    def setUp(self):
        self.client = app.test_client()
        self._missing = object()
        self._original = app.config.get(self.CONFIG_KEY, self._missing)

    def tearDown(self):
        if self._original is self._missing:
            app.config.pop(self.CONFIG_KEY, None)
        else:
            app.config[self.CONFIG_KEY] = self._original

    def html(self, path):
        response = self.client.get(path, base_url='http://localhost')
        self.assertEqual(response.status_code, 200)
        return response.get_data(as_text=True)

    def test_shared_public_theme_is_unavailable_by_default(self):
        self.assertIs(app.config.get(self.CONFIG_KEY, False), False)

        for path in ('/', '/petec/resume', '/interview-studio'):
            with self.subTest(path=path):
                html = self.html(path)
                self.assertIn('data-theme="modern-blue"', html)
                self.assertNotIn('id="theme-toggle"', html)
                self.assertNotIn('data-theme-toggle-proxy', html)
                self.assertNotIn('js/theme-toggle.js', html)
                self.assertNotIn("localStorage.getItem('ps-theme')", html)

    def test_internal_override_restores_the_existing_theme_contract(self):
        app.config[self.CONFIG_KEY] = True

        homepage = self.html('/')
        self.assertEqual(homepage.count('id="theme-toggle"'), 1)
        self.assertEqual(homepage.count('data-theme-toggle-proxy'), 1)
        self.assertEqual(homepage.count('js/theme-toggle.js'), 1)
        self.assertEqual(homepage.count("localStorage.getItem('ps-theme')"), 1)

        interview = self.html('/interview-studio')
        self.assertEqual(interview.count('id="theme-toggle"'), 1)
        self.assertEqual(interview.count('data-theme-toggle-proxy'), 3)
        self.assertEqual(interview.count('js/theme-toggle.js'), 1)
        self.assertEqual(interview.count("localStorage.getItem('ps-theme')"), 1)


if __name__ == '__main__':
    unittest.main()
