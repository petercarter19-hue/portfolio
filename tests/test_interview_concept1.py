import json
import unittest

from app import (
    app,
    validate_interview_review,
    _extract_json_object,
    INTERVIEW_SLATE_EVIDENCE,
)


def _valid_review(answer='I led a cross-functional team.'):
    """A minimal review payload shaped like the model contract."""
    return {
        'overallScore': 82,
        'verdict': 'Strong foundation',
        'encouragement': 'Clear leadership and sound actions.',
        'dimensions': [
            {'key': key, 'score': 80, 'rationale': 'Reason.', 'nextAction': 'Do this.'}
            for key in ('relevance', 'structure', 'specificity', 'evidence', 'impact')
        ],
        'strengths': ['Clear ownership.'],
        'improvements': ['Quantify the result.'],
        'missingEvidence': [
            {'opportunity': 'Cite the 70% metric.', 'suggestedUse': 'Close with it.', 'evidenceId': 'ev-70-repair'}
        ],
        'annotations': [
            {'start': 0, 'end': 5, 'type': 'strong', 'label': 'Ownership', 'explanation': 'Names your role.'}
        ],
        'improvedAnswer': 'I led a cross-functional team and cut repair time 70%.',
        'changesExplained': ['Added a verified metric.'],
    }


class Concept1RouteTests(unittest.TestCase):
    """The Concept 1 workspace runs behind a flag on the same route."""

    def setUp(self):
        self.client = app.test_client()

    def test_default_still_serves_classic_workspace(self):
        response = self.client.get('/petec/interview-me', base_url='http://localhost')
        html = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('data-ivw', html)
        self.assertNotIn('data-ic1', html)

    def test_concept1_query_serves_new_workspace(self):
        response = self.client.get('/petec/interview-me?concept1=1', base_url='http://localhost')
        html = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('data-ic1', html)
        self.assertNotIn('data-ivw', html)

    def test_concept1_has_exactly_one_mode_selector(self):
        html = self.client.get(
            '/petec/interview-me?concept1=1', base_url='http://localhost'
        ).get_data(as_text=True)
        self.assertEqual(html.count('data-ic1-mode="me"'), 1)
        self.assertEqual(html.count('data-ic1-mode="you"'), 1)
        self.assertEqual(html.count('data-ic1-mode="video"'), 1)
        # The classic page's second selector never renders here.
        self.assertNotIn('iv-dir-ai', html)

    def test_concept1_renders_question_once_with_shared_bank(self):
        html = self.client.get(
            '/petec/interview-me?concept1=1', base_url='http://localhost'
        ).get_data(as_text=True)
        # The visible stage renders the question once; the hidden shared
        # data island contains the same text once more.
        question = 'Tell me about a time you led a project from start to finish.'
        self.assertEqual(html.count(question), 2)
        self.assertIn('iv-qbank', html)
        self.assertGreaterEqual(html.count('iq-item'), 60)

    def test_concept1_ships_coaching_loop_and_verified_evidence(self):
        html = self.client.get(
            '/petec/interview-me?concept1=1', base_url='http://localhost'
        ).get_data(as_text=True)
        for step in ('Choose focus', 'Answer naturally', 'Get transparent review',
                     'Improve with coach', 'Retry and measure'):
            self.assertIn(step, html)
        for item in INTERVIEW_SLATE_EVIDENCE:
            self.assertIn(item['id'], html)

    def test_classic_page_keeps_the_shared_question_bank(self):
        html = self.client.get('/petec/interview-me', base_url='http://localhost').get_data(as_text=True)
        self.assertGreaterEqual(html.count('iq-item'), 60)


class ReviewValidationTests(unittest.TestCase):
    """The structured review is validated before the browser sees it."""

    def test_valid_review_passes_and_is_normalized(self):
        answer = 'I led a cross-functional team.'
        review = validate_interview_review(_valid_review(), len(answer))
        self.assertEqual(review['overallScore'], 82)
        self.assertEqual(len(review['dimensions']), 5)
        self.assertEqual(review['dimensions'][0]['key'], 'relevance')
        self.assertEqual(len(review['annotations']), 1)

    def test_missing_dimension_is_rejected(self):
        raw = _valid_review()
        raw['dimensions'] = raw['dimensions'][:4]
        with self.assertRaises(ValueError):
            validate_interview_review(raw, 100)

    def test_score_out_of_range_is_rejected(self):
        raw = _valid_review()
        raw['overallScore'] = 140
        with self.assertRaises(ValueError):
            validate_interview_review(raw, 100)

    def test_invalid_annotation_offsets_are_dropped_not_fatal(self):
        raw = _valid_review()
        raw['annotations'] = [
            {'start': 90, 'end': 500, 'type': 'strong', 'label': 'x', 'explanation': 'x'},
            {'start': 5, 'end': 2, 'type': 'clarity', 'label': 'x', 'explanation': 'x'},
            {'start': 0, 'end': 4, 'type': 'not-a-type', 'label': 'x', 'explanation': 'x'},
        ]
        review = validate_interview_review(raw, 30)
        self.assertEqual(review['annotations'], [])

    def test_verdict_required(self):
        raw = _valid_review()
        raw['verdict'] = '  '
        with self.assertRaises(ValueError):
            validate_interview_review(raw, 100)

    def test_extract_json_tolerates_code_fences(self):
        wrapped = '```json\n' + json.dumps({'a': 1}) + '\n```'
        self.assertEqual(_extract_json_object(wrapped), {'a': 1})

    def test_extract_json_rejects_prose(self):
        with self.assertRaises(ValueError):
            _extract_json_object('The candidate did well overall.')


class ReviewEndpointGuardTests(unittest.TestCase):
    """Bad input is rejected before any AI call is made."""

    def setUp(self):
        self.client = app.test_client()

    def _post(self, payload):
        return self.client.post(
            '/api/interview/review', json=payload, base_url='http://localhost'
        )

    def test_missing_answer_is_a_400(self):
        response = self._post({'question': 'Tell me about a project.'})
        self.assertEqual(response.status_code, 400)

    def test_missing_question_is_a_400(self):
        response = self._post({'answer': 'I led a team.'})
        self.assertEqual(response.status_code, 400)

    def test_oversized_answer_is_a_400(self):
        response = self._post({'question': 'Q?', 'answer': 'x' * 5001})
        self.assertEqual(response.status_code, 400)

    def test_coach_requires_a_message(self):
        response = self.client.post(
            '/api/interview/coach',
            json={'question': 'Q?', 'answer': 'A.'},
            base_url='http://localhost',
        )
        self.assertEqual(response.status_code, 400)

    def test_coach_requires_context(self):
        response = self.client.post(
            '/api/interview/coach',
            json={'message': 'Why did I lose points?'},
            base_url='http://localhost',
        )
        self.assertEqual(response.status_code, 400)


if __name__ == '__main__':
    unittest.main()
