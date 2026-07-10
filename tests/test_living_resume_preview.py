import unittest
from app import app

class LivingResumePreviewTests(unittest.TestCase):
    def test_preview_renders_default_fixture_locally(self):
        response = app.test_client().get('/_internal/living-resume-v2', base_url='http://localhost')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Living R\xc3\xa9sum\xc3\xa9 Ledger', response.data)

    def test_preview_selects_each_stress_profile(self):
        response = app.test_client().get('/_internal/living-resume-v2?profile=freelancer', base_url='http://localhost')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Independent Product Strategist', response.data)

if __name__ == '__main__': unittest.main()
