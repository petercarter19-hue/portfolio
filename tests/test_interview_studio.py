import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from app import (
    app,
    _load_interview_model_context,
    _sign_interview_model_context,
    validate_interview_improvement,
    validate_interview_model_answer,
    validate_interview_review,
    _extract_json_object,
)


DIMENSIONS = ('relevance', 'structure', 'specificity', 'evidence', 'impact')


def valid_review():
    scores = (17, 16, 16, 16, 17)
    return {
        'overallScore': sum(scores),
        'verdict': 'Strong foundation',
        'encouragement': 'Clear ownership and a useful result.',
        'dimensions': [
            {
                'key': key,
                'score': score,
                'rationale': f'{key.title()} is specific.',
                'nextAction': f'Strengthen {key}.',
            }
            for key, score in zip(DIMENSIONS, scores)
        ],
        'star': {
            'situation': {'status': 'present', 'reason': 'The context is clear.'},
            'task': {'status': 'partial', 'reason': 'The responsibility needs detail.'},
            'action': {'status': 'strong', 'reason': 'The candidate owns the action.'},
            'result': {'status': 'present', 'reason': 'A result is included.'},
        },
        'strengths': ['Clear ownership.', 'Professional judgment.'],
        'improvements': ['Clarify the task.', 'Quantify the result.'],
        'evidenceSuggestions': [
            {
                'opportunity': 'Approved impact evidence could sharpen the result.',
                'suggestedUse': 'Connect the approved metric after confirming relevance.',
                'evidenceId': 'modernization',
            }
        ],
    }


class InterviewStudioRouteTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def html(self, path='/interview-studio'):
        response = self.client.get(path, base_url='http://localhost')
        self.assertEqual(response.status_code, 200)
        return response.get_data(as_text=True)

    def test_canonical_route_and_legacy_redirects(self):
        self.assertIn('data-interview-studio', self.html())
        for path in ('/interview-me', '/petec/interview-me', '/petec/interview-studio'):
            with self.subTest(path=path):
                response = self.client.get(path, base_url='http://localhost')
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.headers['Location'], '/interview-studio')

    def test_platform_legacy_redirect_preserves_an_enabled_mode(self):
        response = self.client.get(
            '/interview-me?mode=video',
            base_url='https://peerslate.com',
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers['Location'], '/interview-studio?mode=video')

    def test_direct_mode_urls_restore_the_selected_mode(self):
        for mode in ('me', 'ai', 'video'):
            with self.subTest(mode=mode):
                html = self.html(f'/interview-studio?mode={mode}')
                self.assertIn(f'data-is-mode="{mode}"', html)
                selected = html.split(f'data-is-mode="{mode}"', 1)[0].rsplit('<a', 1)[-1]
                self.assertIn('aria-selected="true"', selected)

    def test_one_three_mode_selector_and_separate_history_destination(self):
        html = self.html()
        self.assertEqual(html.count('data-is-mode="me"'), 1)
        self.assertEqual(html.count('data-is-mode="ai"'), 1)
        self.assertEqual(html.count('data-is-mode="video"'), 1)
        self.assertNotIn('data-is-mode="history"', html)
        self.assertIn('href="/interview-studio/history"', html)
        self.assertIn('data-is-panel="history"', html)

    def test_history_route_is_active_without_selecting_a_practice_mode(self):
        html = self.html('/interview-studio/history')
        self.assertIn('data-is-history-link', html)
        self.assertIn('aria-current="page"', html)
        self.assertIn('data-initial-view="history"', html)
        mode_nav = html.split('class="is__modes"', 1)[1].split('</nav>', 1)[0]
        self.assertNotIn('role="tablist"', mode_nav)
        self.assertNotIn('tabindex="-1"', mode_nav)

    def test_ready_state_has_real_question_and_required_terminology(self):
        html = self.html()
        for value in (
            'Tell me about a time you disagreed with a supervisor.',
            'Question 1 of 5',
            'Behavioral',
            'Competency: Conflict',
            'STAR recommended',
            'Submit answer',
            'New Question',
            'Up next:',
        ):
            self.assertIn(value, html)
        self.assertIn('data-is-mic="answer"', html)
        self.assertIn('data-is-answer-form', html)

    def test_answer_submission_and_feature_workspaces_are_visible_upfront(self):
        html = self.html()
        self.assertIn('type="submit" data-is-review disabled', html)
        self.assertIn('Ctrl/Command + Enter to submit', html)
        self.assertNotIn('data-is-feedback hidden', html)
        self.assertNotIn('data-is-improve-panel hidden', html)
        self.assertNotIn('data-is-ai-answer hidden', html)
        self.assertNotIn('data-is-video-result hidden', html)
        self.assertIn('data-is-feedback-empty', html)
        self.assertIn('data-is-improve-empty', html)
        self.assertIn('data-is-ai-answer-empty', html)
        self.assertIn('data-is-video-result-empty', html)
        self.assertIn('data-is-video-transcript-form', html)
        self.assertIn('data-is-mic="video"', html)

    def test_client_submission_accepts_any_nonempty_answer_and_uses_a_real_form(self):
        script = (Path(__file__).parents[1] / 'static' / 'js' / 'interview-studio.js').read_text(encoding='utf-8')
        self.assertIn("answerForm.addEventListener('submit'", script)
        self.assertIn("if (!responseText)", script)
        self.assertNotIn('responseText.length < 8', script)
        self.assertIn("event.ctrlKey && !event.metaKey", script)

    def test_question_bank_uses_family_and_competency_taxonomy(self):
        html = self.html()
        self.assertEqual(html.count('class="iq-item"'), 60)
        self.assertEqual(html.count('data-family="behavioral"'), 30)
        self.assertEqual(html.count('data-family="situational"'), 30)
        self.assertNotIn('data-mode="star"', html)
        self.assertNotIn('data-topic=', html)

    def test_retired_controls_and_names_are_absent(self):
        html = self.html()
        for retired in (
            'Interview You',
            'Save Draft',
            'Open in Review Room',
            'Evidence Drawer',
            'Start Mock Interview',
            'Practice It',
            'data-ic1',
            'data-ivw',
        ):
            self.assertNotIn(retired, html)

    def test_all_seven_reference_states_are_real_regions(self):
        html = self.html()
        for region in (
            'data-is-answering',
            'data-is-queue',
            'data-is-feedback',
            'data-is-improve-panel',
            'data-is-ai-answer',
            'data-is-camera',
            'data-is-panel="history"',
        ):
            self.assertIn(region, html)

    def test_video_copy_is_honest_about_current_capability(self):
        html = self.html('/interview-studio?mode=video')
        self.assertIn('Nothing is uploaded', html)
        self.assertIn('Delivery analysis is not enabled yet', html)
        self.assertIn('not uploaded, analyzed, or retained', html)
        self.assertIn('data-is-video-question-position', html)
        self.assertIn('data-is-video-transcript', html)
        self.assertIn('same evidence-backed content review as Interview Me', html)
        self.assertNotIn('fake replay', html.lower())

    def test_history_supports_real_session_detail_and_deletion(self):
        html = self.html('/interview-studio/history')
        self.assertIn('data-is-history-detail', html)
        self.assertIn('data-is-history-detail-answer', html)
        self.assertIn('data-is-history-detail-review', html)
        self.assertIn('data-is-history-detail-delete', html)

    def test_server_capabilities_are_exposed_to_the_shell(self):
        html = self.html()
        self.assertIn('data-written-practice="enabled"', html)
        self.assertIn('data-model-answers="enabled"', html)
        self.assertIn('data-video-capability="preview"', html)
        self.assertIn('data-history-capability="browser"', html)

    def test_disabled_capabilities_govern_direct_routes_and_controls(self):
        with patch.dict(os.environ, {
            'INTERVIEW_VIDEO_STUDIO': 'locked',
            'INTERVIEW_PROGRESS_HISTORY': 'locked',
        }):
            video = self.client.get('/interview-studio?mode=video', base_url='http://localhost')
            self.assertEqual(video.status_code, 302)
            self.assertEqual(video.headers['Location'], '/interview-studio')
            video_html = self.html()
            video_tab = video_html.split('data-is-mode="video"', 1)[0].rsplit('<a', 1)[-1]
            self.assertIn('aria-disabled="true"', video_tab)
            self.assertIn('data-initial-mode="me"', video_html)

            history = self.client.get('/interview-studio/history', base_url='http://localhost')
            self.assertEqual(history.status_code, 302)
            self.assertEqual(history.headers['Location'], '/interview-studio')

    def test_legacy_enabled_entitlements_remain_available(self):
        with patch.dict(os.environ, {
            'INTERVIEW_VIDEO_STUDIO': 'enabled',
            'INTERVIEW_PROGRESS_HISTORY': 'enabled',
        }):
            video_html = self.html('/interview-studio?mode=video')
            self.assertIn('data-video-capability="preview"', video_html)
            self.assertIn('data-initial-mode="video"', video_html)
            self.assertIn('data-history-capability="browser"', self.html('/interview-studio/history'))

    def test_profile_context_and_evidence_are_server_derived(self):
        html = self.html()
        self.assertIn('data-profile-slug="petec"', html)
        self.assertIn('Preparing as <strong>Pete Carter</strong>', html)
        evidence_json = html.split('<script id="is-evidence-data" type="application/json">', 1)[1].split('</script>', 1)[0]
        evidence = json.loads(evidence_json)
        self.assertGreaterEqual(len(evidence), 3)
        self.assertNotIn('micap', json.dumps(evidence).lower())


class ReviewSchemaTests(unittest.TestCase):
    def test_valid_review_is_consistent_and_normalized(self):
        review = validate_interview_review(
            valid_review(),
            answer_length=100,
            allowed_evidence_ids={'modernization'},
        )
        self.assertEqual(review['overallScore'], 82)
        self.assertEqual(sum(item['score'] for item in review['dimensions']), 82)
        self.assertEqual(review['star']['action']['status'], 'strong')

    def test_inconsistent_overall_score_is_rejected(self):
        raw = valid_review()
        raw['overallScore'] = 90
        with self.assertRaisesRegex(ValueError, 'dimension total'):
            validate_interview_review(raw, 100, {'modernization'})

    def test_dimension_over_twenty_is_rejected(self):
        raw = valid_review()
        raw['dimensions'][0]['score'] = 21
        with self.assertRaisesRegex(ValueError, 'dimension score'):
            validate_interview_review(raw, 100, {'modernization'})

    def test_blank_dimension_explanation_is_rejected(self):
        raw = valid_review()
        raw['dimensions'][0]['rationale'] = ''
        with self.assertRaisesRegex(ValueError, 'dimension explanation'):
            validate_interview_review(raw, 100, {'modernization'})

    def test_invalid_star_status_is_rejected(self):
        raw = valid_review()
        raw['star']['task']['status'] = 'perfect'
        with self.assertRaisesRegex(ValueError, 'STAR'):
            validate_interview_review(raw, 100, {'modernization'})

    def test_unapproved_evidence_suggestion_is_rejected(self):
        raw = valid_review()
        raw['evidenceSuggestions'][0]['evidenceId'] = 'private-record'
        with self.assertRaisesRegex(ValueError, 'unauthorized evidence'):
            validate_interview_review(raw, 100, {'modernization'})

    def test_evidence_suggestion_is_rejected_when_profile_has_no_approved_evidence(self):
        with self.assertRaisesRegex(ValueError, 'unauthorized evidence'):
            validate_interview_review(valid_review(), 100, set())

    def test_model_answer_has_no_score_and_only_allowed_evidence(self):
        evidence = {'metric-one': {'id': 'metric-one', 'metric': '42%', 'label': 'Approved result'}}
        answer = validate_interview_model_answer(
            {'status': 'answered', 'answer': 'I improved the result by 42%.', 'whyItWorks': ['Specific result'], 'evidenceIds': ['metric-one']},
            evidence,
        )
        self.assertNotIn('score', answer)
        self.assertEqual(answer['evidenceUsed'][0]['id'], 'metric-one')

    def test_model_answer_rejects_unknown_evidence(self):
        with self.assertRaisesRegex(ValueError, 'unauthorized evidence'):
            validate_interview_model_answer(
                {'status': 'answered', 'answer': 'Answer', 'whyItWorks': ['Clear'], 'evidenceIds': ['unknown']},
                {},
            )

    def test_model_answer_requires_an_approved_evidence_reference(self):
        with self.assertRaisesRegex(ValueError, 'no approved evidence'):
            validate_interview_model_answer(
                {'status': 'answered', 'answer': 'A polished but unsupported answer.', 'whyItWorks': ['Clear'], 'evidenceIds': []},
                {'approved': {'id': 'approved', 'metric': '42%', 'label': 'Approved result'}},
            )

    def test_model_answer_has_a_safe_insufficient_evidence_state(self):
        answer = validate_interview_model_answer(
            {
                'status': 'insufficient',
                'answer': 'An invented claim that must be ignored.',
                'whyItWorks': ['Invented rationale'],
                'evidenceIds': [],
            },
            {'approved': {'id': 'approved', 'metric': '42%', 'label': 'Approved result'}},
        )
        self.assertEqual(answer['status'], 'insufficient')
        self.assertIn('without guessing', answer['answer'])
        self.assertEqual(answer['evidenceUsed'], [])

    def test_model_answer_context_is_server_signed_and_round_trips(self):
        token = _sign_interview_model_context(
            'petec',
            'Tell me about a project.',
            'experienced',
            'behavioral',
            {
                'answer': 'I delivered the approved result.',
                'evidenceUsed': [{'id': 'approved'}],
            },
        )
        context = _load_interview_model_context(token)
        self.assertEqual(context['question'], 'Tell me about a project.')
        self.assertEqual(context['answer'], 'I delivered the approved result.')
        self.assertEqual(context['evidence_ids'], ['approved'])

    def test_improved_draft_uses_selected_evidence_only(self):
        evidence = {'selected': {'id': 'selected', 'metric': '20%', 'label': 'Approved'}}
        improvement = validate_interview_improvement(
            {'draft': 'I improved the result.', 'changes': ['Clarified the action'], 'evidenceIds': ['selected']},
            evidence,
        )
        self.assertEqual(improvement['evidenceUsed'][0]['id'], 'selected')

    def test_extract_json_tolerates_code_fences(self):
        wrapped = '```json\n' + json.dumps({'a': 1}) + '\n```'
        self.assertEqual(_extract_json_object(wrapped), {'a': 1})


class InterviewEndpointGuardTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_review_requires_json_and_complete_content(self):
        response = self.client.post('/api/interview/review', data='question=x', base_url='http://localhost')
        self.assertEqual(response.status_code, 415)
        response = self.client.post('/api/interview/review', json={'question': 'Q?'}, base_url='http://localhost')
        self.assertEqual(response.status_code, 400)

    def test_cross_site_review_is_rejected_before_ai(self):
        response = self.client.post(
            '/api/interview/review',
            json={'question': 'Q?', 'answer': 'A complete answer.'},
            headers={'Origin': 'https://attacker.example'},
            base_url='http://localhost',
        )
        self.assertEqual(response.status_code, 403)

    def test_improve_rejects_unapproved_evidence_before_ai(self):
        response = self.client.post(
            '/api/interview/improve',
            json={
                'profile_slug': 'petec',
                'question': 'Tell me about a project.',
                'answer': 'I led the project and delivered it.',
                'improvements': ['Add evidence.'],
                'evidence_ids': ['private-record'],
            },
            base_url='http://localhost',
        )
        self.assertEqual(response.status_code, 403)

    def test_model_answer_requires_a_question(self):
        response = self.client.post('/api/interview/model-answer', json={}, base_url='http://localhost')
        self.assertEqual(response.status_code, 400)

    def test_model_answer_follow_up_requires_server_signed_context(self):
        response = self.client.post(
            '/api/interview/model-answer',
            json={
                'question': 'Tell me about a project.',
                'follow_up': 'What happened next?',
                'context_token': 'tampered-client-context',
            },
            base_url='http://localhost',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('invalid or expired', response.get_json()['error'])

    def test_interview_endpoints_reject_scalar_and_wrong_shaped_json(self):
        for path in (
            '/api/interview/review',
            '/api/interview/improve',
            '/api/interview/model-answer',
        ):
            with self.subTest(path=path):
                response = self.client.post(
                    path,
                    data=json.dumps('not-an-object'),
                    content_type='application/json',
                    base_url='http://localhost',
                )
                self.assertEqual(response.status_code, 400)

        response = self.client.post(
            '/api/interview/improve',
            json={
                'question': 'Tell me about a project.',
                'answer': 'I delivered it.',
                'improvements': 'add evidence',
                'evidence_ids': {'not': 'a list'},
            },
            base_url='http://localhost',
        )
        self.assertEqual(response.status_code, 400)

    def test_legacy_freeform_coach_endpoint_is_retired(self):
        response = self.client.post('/api/interview/coach', json={}, base_url='http://localhost')
        self.assertEqual(response.status_code, 410)


class InterviewStudioAssetTests(unittest.TestCase):
    def test_client_uses_url_state_autosave_media_and_local_history(self):
        source = Path('static/js/interview-studio.js').read_text(encoding='utf-8')
        for contract in (
            'window.history.pushState',
            'window.localStorage',
            'showModal',
            'SpeechRecognition',
            'getUserMedia',
            'MediaRecorder',
            '/api/interview/review',
            '/api/interview/improve',
            '/api/interview/model-answer',
            'cancelPendingReview',
            'cancelPendingAi',
            'historyDetailUrl',
            'updateHistoryRecord',
            "family === 'mixed'",
            'context_token',
        ):
            self.assertIn(contract, source)
        self.assertNotIn('prior_answer', source)

    def test_responsive_and_accessibility_contracts_are_present(self):
        css = Path('static/css/interview-studio.css').read_text(encoding='utf-8')
        self.assertIn('@media (max-width: 48rem)', css)
        self.assertIn('@media (prefers-reduced-motion: reduce)', css)
        self.assertIn('@media (forced-colors: active)', css)
        self.assertIn('min-height: 2.85rem', css)


if __name__ == '__main__':
    unittest.main()
