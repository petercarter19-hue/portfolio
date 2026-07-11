import json
import re
import unittest
from pathlib import Path

from app import app


class Resume3Tests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.project_root = Path(__file__).resolve().parents[1]

    def get_resume3(self):
        return self.client.get('/petec/resume3', base_url='http://localhost')

    def test_resume3_route_is_isolated(self):
        adapter = app.url_map.bind('localhost')
        endpoint, view_args = adapter.match('/petec/resume3')

        self.assertEqual(endpoint, 'profile_resume3')
        self.assertEqual(view_args, {'profile_slug': 'petec'})

        response = self.get_resume3()
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'class="lr-page resume-v3"', response.data)
        self.assertIn(b'css/resume3.css', response.data)
        self.assertNotIn(b'css/resume2.css', response.data)
        self.assertEqual(self.client.get('/resume3').status_code, 404)
        self.assertEqual(
            self.client.get('/another-profile/resume3').status_code,
            404,
        )

    def test_resume3_uses_shared_timeline_data_and_next_three_chapters(self):
        response = self.get_resume3()
        response_text = response.get_data(as_text=True)
        data = json.loads(
            (self.project_root / 'static/data/resume_data.json').read_text(
                encoding='utf-8'
            )
        )

        expected_event_ids = [
            event['id']
            for event in data['living_resume']['events']
            if event.get('show_in_ledger')
        ]
        rendered_event_ids = re.findall(
            r'data-ledger-event="([^"]+)"',
            response_text,
        )
        self.assertEqual(rendered_event_ids, expected_event_ids)

        default_event_id = data['living_resume']['default_event_id']
        default_index = expected_event_ids.index(default_event_id)
        following_ids = (
            expected_event_ids[default_index + 1:]
            + expected_event_ids[:default_index]
        )[:3]
        self.assertEqual(
            re.findall(r'data-r3-experience-card="([^"]+)"', response_text),
            following_ids,
        )
        self.assertIn(
            f'data-featured-event="{default_event_id}"',
            response_text,
        )

    def test_resume3_preserves_accessible_ledger_relationships(self):
        response_text = self.get_resume3().get_data(as_text=True)
        data = json.loads(
            (self.project_root / 'static/data/resume_data.json').read_text(
                encoding='utf-8'
            )
        )
        expected_event_ids = [
            event['id']
            for event in data['living_resume']['events']
            if event.get('show_in_ledger')
        ]

        self.assertEqual(response_text.count('<h1'), 1)
        self.assertIn('class="r3-profile-card"', response_text)
        self.assertIn('class="lr-ledger__rail r3-ledger-nav-card"', response_text)
        self.assertIn('aria-label="Living resume sections"', response_text)
        self.assertIn('role="tablist"', response_text)
        self.assertIn('aria-live="polite"', response_text)
        self.assertIn('href="#resume-experience"', response_text)
        self.assertIn('id="resume-experience"', response_text)

        for event_id in expected_event_ids:
            self.assertIn(f'id="timeline-tab-{event_id}"', response_text)
            self.assertIn(
                f'aria-controls="ledger-panel-{event_id}"',
                response_text,
            )
            self.assertIn(f'id="ledger-panel-{event_id}"', response_text)
            self.assertIn(
                f'aria-labelledby="timeline-tab-{event_id}"',
                response_text,
            )

    def test_resume3_is_fixture_driven_and_omits_retired_content(self):
        response_text = self.get_resume3().get_data(as_text=True)
        template = (self.project_root / 'templates/resume3.html').read_text(
            encoding='utf-8'
        )

        for hardcoded_value in (
            'Pete Carter',
            'U.S. Air Force',
            'L3Harris',
            'Northrop Grumman',
            '2021-2024',
            '$36M',
        ):
            self.assertNotIn(hardcoded_value, template)

        self.assertNotIn('micap', response_text.lower())
        self.assertNotIn('Mission Highlights', response_text)
        self.assertNotIn('r3-mission-highlights', response_text)

    def test_resume3_assets_and_accessibility_styles_exist(self):
        css_path = self.project_root / 'static/css/resume3.css'
        css = css_path.read_text(encoding='utf-8')

        self.assertTrue(css_path.is_file())
        self.assertIn(':focus-visible', css)
        self.assertIn('@media (prefers-reduced-motion: reduce)', css)
        self.assertIn('@media (max-width:', css)
        self.assertIn('.r3-stage-card', css)

        asset_dir = self.project_root / 'static/images/Mockups/resume2'
        for filename in (
            'resume2-blue-mountain-background.avif',
            'resume2-blue-mountain-background.webp',
            'resume2-blue-mountain-background-mobile.avif',
            'resume2-blue-mountain-background-mobile.webp',
        ):
            asset = asset_dir / filename
            self.assertTrue(asset.is_file())
            self.assertGreater(asset.stat().st_size, 0)

    def test_resume3_keeps_the_shared_career_constellation(self):
        response_text = self.get_resume3().get_data(as_text=True)
        template = (self.project_root / 'templates/resume3.html').read_text(
            encoding='utf-8'
        )

        self.assertIn(
            '{% include "partials/career_constellation.html" %}',
            template,
        )
        self.assertIn('<!-- shared-career-constellation:start -->', response_text)
        self.assertIn('id="constellation"', response_text)


if __name__ == '__main__':
    unittest.main()
