"""Complete unregistered Profile-local destination integration contracts."""

from __future__ import annotations

import unittest
from flask import Flask

from profile_routes import profile_routes
from tests.test_profile_core_routes import _service


class ProfileDestinationIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app = Flask(__name__, template_folder="../templates", static_folder="../static")
        app.config.update(TESTING=True, PEERSLATE_PROFILE_CORE_SERVICE_PROVIDER=_service)
        app.register_blueprint(profile_routes)
        cls.client = app.test_client()

    def test_integrated_profile_local_destinations_render_semantic_state(self):
        expected = {
            "/avery/profile-home": "A living front room",
            "/avery/profile-posts": "Selected authored conversations",
            "/avery/profile-about": "The person behind the work",
        }
        for path, marker in expected.items():
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertIn(marker, response.get_data(as_text=True))
                self.assertEqual(response.headers["Cache-Control"], "no-store")

    def test_unintegrated_optional_destinations_are_neutrally_absent(self):
        for path in ("/avery/profile-projects", "/avery/profile-media", "/avery/profile-voice"):
            response = self.client.get(path)
            body = response.get_data(as_text=True)
            self.assertEqual(response.status_code, 404)
            self.assertNotIn("ownerAlpha_123", body)
            self.assertNotIn("source_key", body)


if __name__ == "__main__": unittest.main()
