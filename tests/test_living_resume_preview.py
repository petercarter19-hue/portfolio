import unittest
from pathlib import Path

from app import app


class LivingResumePreviewTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_preview_renders_real_resume_data_and_both_approved_sections(self):
        response = self.client.get('/_internal/living-resume-v2', base_url='http://localhost')

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Pete Carter', response.data)
        self.assertIn(b'Living R\xc3\xa9sum\xc3\xa9', response.data)
        self.assertIn(b'Department of Defense / U.S. Air Force', response.data)
        self.assertIn(b'See how the work became the story.', response.data)
        self.assertIn(b'files/pete-carter-resume.pdf', response.data)

    def test_preview_remains_hidden_from_nonlocal_hosts(self):
        response = self.client.get('/_internal/living-resume-v2', base_url='https://peerslate.com')

        self.assertEqual(response.status_code, 404)

    def test_public_resume_routes_render_living_resume_in_quiet_preview_mode(self):
        response = self.client.get('/petec/resume', base_url='http://localhost')
        legacy_response = self.client.get(
            '/petec/resume2',
            base_url='http://localhost',
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(legacy_response.status_code, (301, 302, 307, 308))
        self.assertEqual(legacy_response.headers['Location'], '/petec/resume')
        self.assertIn(b'Living R\xc3\xa9sum\xc3\xa9', response.data)
        self.assertIn(b'See how the work became the story.', response.data)
        self.assertNotIn(b'Internal preview', response.data)
        self.assertIn(
            b'<meta name="robots" '
            b'content="noindex, nofollow, noarchive, noimageindex">',
            response.data,
        )

    def test_preview_defines_reduced_motion_fallbacks(self):
        project_root = Path(__file__).resolve().parents[1]
        css = (project_root / 'static/css/living-resume-v2.css').read_text(encoding='utf-8')
        javascript = (project_root / 'static/js/living-resume-v2.js').read_text(encoding='utf-8')

        self.assertIn('@media (prefers-reduced-motion: reduce)', css)
        self.assertIn("reducedMotion.matches ? 'auto' : 'smooth'", javascript)

    def test_preview_keeps_ai_and_section_navigation_persistent(self):
        response = self.client.get('/_internal/living-resume-v2', base_url='http://localhost')
        project_root = Path(__file__).resolve().parents[1]
        css = (project_root / 'static/css/living-resume-v2.css').read_text(encoding='utf-8')
        javascript = (project_root / 'static/js/living-resume-v2.js').read_text(encoding='utf-8')

        for section_id in (
            'overview',
            'impact',
            'skills',
            'experience',
            'credentials',
        ):
            self.assertIn(f'id="{section_id}"'.encode(), response.data)
            self.assertIn(f'href="#{section_id}"'.encode(), response.data)

        ordered_sections = [
            response.data.index(f'id="{section_id}"'.encode())
            for section_id in (
                'overview',
                'impact',
                'skills',
                'experience',
                'credentials',
            )
        ]
        self.assertEqual(ordered_sections, sorted(ordered_sections))
        self.assertGreater(response.data.index(b'id="constellation"'), ordered_sections[-1])

        for legacy_alias in (
            'resume-overview',
            'resume-experience',
            'resume-skills',
            'resume-education',
            'resume-development',
            'resume-certifications',
            'resume-achievements',
            'ledger',
            'ledger-timeline',
        ):
            self.assertIn(f'id="{legacy_alias}"'.encode(), response.data)

        self.assertIn(b'r2-overview-ai-rail', response.data)
        self.assertIn(b'resume-ai-panel', response.data)
        self.assertGreaterEqual(response.data.count(b'data-chat-open'), 3)
        self.assertIn('.living-resume-v2-page #chat-toggle', css)
        self.assertIn('updatePersistentNavigation', javascript)


if __name__ == '__main__':
    unittest.main()
