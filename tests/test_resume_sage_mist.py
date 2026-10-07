"""Content and destination guarantees for the approved public composition."""
import copy
import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault('ANTHROPIC_API_KEY', 'sage-mist-test-only')
import app as app_module
from overview_projection_service import build_public_overview_projection

ROOT = Path(__file__).resolve().parents[1]


def public_projection():
    data = json.loads((ROOT / 'static/data/resume_data.json').read_text(encoding='utf-8'))
    return build_public_overview_projection(data)


def sparse_projection():
    projection = copy.deepcopy(public_projection())
    for key in ('story_spotlight', 'certifications', 'awards', 'story_chapters', 'philosophy', 'future_direction'):
        projection['block_by_definition'].pop(key, None)
    for block in projection['block_by_definition'].values():
        block['media'] = []
    projection['profile']['location'] = ''
    projection['profile']['intro'] = 'Long public introduction. ' * 30
    return projection


class SageMistContentTests(unittest.TestCase):
    def setUp(self):
        self.original = dict(app_module.app.config)
        app_module.app.config.update(TESTING=True, PEERSLATE_ASK_PETE_GROUNDED_ENABLED=True)
        self.client = app_module.app.test_client()

    def tearDown(self):
        app_module.app.config.clear()
        app_module.app.config.update(self.original)

    def test_real_supporting_impacts_and_existing_source_destinations_are_retained(self):
        html = self.client.get('/petec/resume').get_data(as_text=True)
        data = json.loads((ROOT / 'static/data/resume_data.json').read_text(encoding='utf-8'))
        self.assertEqual(html.count('data-sage-impact-flip '), 4)
        for metric in data['metrics']:
            if metric['value'] in ('30+', '9 / $19.2M', '35%', '70%'):
                self.assertIn(metric['context'], html)
        self.assertEqual(html.count('data-ask-pete-companion'), 1)
        self.assertNotIn('Key Impact &amp; Achievements', html)
        self.assertNotIn('ask-pete-evidence-preview', html)
        self.assertNotIn('Resume PDF', html)
        self.assertNotIn('555-', html)
        for role in ('northrop', 'l3harris', 'dod'):
            self.assertIn(f'id="r2-exp-card-{role}"', html)

    def test_optional_story_media_and_credential_groups_release_their_wrappers(self):
        with patch.object(app_module, 'build_public_overview_projection', return_value=sparse_projection()):
            response = self.client.get('/petec/resume')
        self.assertEqual(response.status_code, 200)
        opening = response.get_data(as_text=True).split('id="resume-start"')[0]
        self.assertNotIn('class="overview-story ', opening)
        self.assertNotIn('overview-hero-media', opening)
        self.assertNotIn('overview-awards-heading', opening)
        self.assertNotIn('overview-certifications-heading', opening)
        self.assertIn('overview-education-heading', opening)
        self.assertIn('Long public introduction. ' * 30, opening)
        self.assertIn('data-ask-pete-companion', opening)

    def test_work_impact_and_summary_fallback_have_one_functional_assistant(self):
        for query in ('?overviewStyle=work-impact', ''):
            with self.subTest(query=query):
                patcher = patch.object(app_module, 'build_public_overview_projection', return_value=None) if not query else patch.object(app_module, 'build_public_overview_projection', wraps=build_public_overview_projection)
                with patcher:
                    html = self.client.get('/petec/resume' + query).get_data(as_text=True)
                self.assertEqual(html.count('data-ask-pete-companion'), 1)
                self.assertIn('value="ledger-timeline"', html)
                self.assertIn('id="ledger-timeline"', html)

    def test_phone_is_optional_and_comes_only_from_the_loaded_public_record(self):
        original = app_module._load_resume_profile('petec')
        self.assertNotIn('phone', original['profile'])
        html = self.client.get('/petec/resume').get_data(as_text=True)
        self.assertNotIn('href="tel:', html)
        public = copy.deepcopy(original)
        public['profile']['phone'] = '+1 (256) 555-0198'  # Test-only public source value.
        with patch.object(app_module, '_load_resume_profile', return_value=public):
            html = self.client.get('/petec/resume').get_data(as_text=True)
        self.assertIn('href="tel:+1(256)555-0198"', html)
        self.assertIn('+1 (256) 555-0198', html)


if __name__ == '__main__':
    unittest.main()
