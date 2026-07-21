import ast
import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from app import (
    app,
    limiter,
    INTERVIEW_FAILURE_REASONS,
    INTERVIEW_UNCLASSIFIED_REASON,
    _interview_failure_reason,
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
        html = self.html('/interview-studio?mode=me')
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
        self.assertIn('data-is-mic-error="answer" hidden', html)

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
        self.assertIn('data-is-mic-error="video" hidden', html)
        self.assertIn('data-is-mic="ai"', html)
        self.assertIn('data-is-mic-error="ai" hidden', html)

    def test_client_submission_accepts_any_nonempty_answer_and_uses_a_real_form(self):
        script = (Path(__file__).parents[1] / 'static' / 'js' / 'interview-studio.js').read_text(encoding='utf-8')
        self.assertIn("answerForm.addEventListener('submit'", script)
        self.assertIn("if (!responseText)", script)
        self.assertNotIn('responseText.length < 8', script)
        self.assertIn("event.ctrlKey && !event.metaKey", script)

    def test_dictation_failures_are_shown_visibly_not_only_announced(self):
        script = (Path(__file__).parents[1] / 'static' / 'js' / 'interview-studio.js').read_text(encoding='utf-8')
        self.assertIn('function friendlySpeechError', script)
        self.assertIn('function showMicError', script)
        self.assertIn("data-is-mic-error", script)
        self.assertIn("code === 'aborted'", script)
        self.assertIn("code === 'not-allowed'", script)
        self.assertIn("code === 'no-speech'", script)
        self.assertIn("code === 'audio-capture'", script)
        self.assertIn("code === 'network'", script)

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
            'Video Me',
            'Preparing as',
            'Design authority',
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
        self.assertIn('same content review as Interview Me, grounded in the approved history', html)
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
        self.assertIn('Public demo profile', html)
        self.assertIn('<strong>Pete Carter</strong>', html)
        self.assertIn('You are not signed in as Pete.', html)
        self.assertNotIn('Preparing as', html)
        evidence_json = html.split('<script id="is-evidence-data" type="application/json">', 1)[1].split('</script>', 1)[0]
        evidence = json.loads(evidence_json)
        self.assertGreaterEqual(len(evidence), 3)
        self.assertNotIn('micap', json.dumps(evidence).lower())


class InterviewStudioRealStudioTests(unittest.TestCase):
    """PS-INTERVIEW-PUBLIC-GATE-001: 5A-light/5C-dark real Studio (orientation
    view, stage rail, truth strip, and theme no-state-loss guardrails)."""

    def setUp(self):
        self.client = app.test_client()

    def html(self, path='/interview-studio'):
        response = self.client.get(path, base_url='http://localhost')
        self.assertEqual(response.status_code, 200)
        return response.get_data(as_text=True)

    def test_bare_route_shows_orientation_with_practice_panel_hidden(self):
        html = self.html()
        orientation = html.split('data-is-panel="orientation"', 1)[1].split('>', 1)[0]
        self.assertNotIn('hidden', orientation)
        me_panel = html.split('data-is-panel="me"', 1)[1].split('>', 1)[0]
        self.assertIn('hidden', me_panel)
        self.assertIn('Start Interview Me', html)
        self.assertIn('data-is-orientation-link="me"', html)
        self.assertIn('data-is-orientation-link="ai"', html)
        self.assertIn('data-is-orientation-link="video"', html)
        self.assertIn('data-is-orientation-link="history"', html)

    def test_explicit_mode_param_bypasses_orientation(self):
        for mode in ('me', 'ai', 'video'):
            with self.subTest(mode=mode):
                html = self.html(f'/interview-studio?mode={mode}')
                orientation = html.split('data-is-panel="orientation"', 1)[1].split('>', 1)[0]
                self.assertIn('hidden', orientation)

    def test_history_route_does_not_show_orientation(self):
        html = self.html('/interview-studio/history')
        orientation = html.split('data-is-panel="orientation"', 1)[1].split('>', 1)[0]
        self.assertIn('hidden', orientation)

    def test_orientation_links_are_real_links_without_javascript(self):
        html = self.html()
        self.assertIn('href="/interview-studio?mode=me"', html)
        self.assertIn('href="/interview-studio?mode=ai"', html)
        self.assertIn('href="/interview-studio?mode=video"', html)
        self.assertIn('href="/interview-studio/history"', html)
        self.assertIn('<noscript>', html)
        self.assertIn('Interactive practice needs JavaScript.', html)

    def test_truth_strip_present_on_every_view(self):
        for path in ('/interview-studio', '/interview-studio?mode=video', '/interview-studio/history'):
            with self.subTest(path=path):
                html = self.html(path)
                self.assertEqual(html.count('data-is-truth-strip'), 1)
                for value in (
                    'sent to PeerSlate only when you submit for coaching',
                    'saved only in this browser',
                    'Video Practice remains local',
                    'practice signals, not employer predictions',
                ):
                    self.assertIn(value, html)

    def test_stage_rail_has_five_steps(self):
        html = self.html('/interview-studio?mode=me')
        rail = html.split('data-is-stage-rail', 1)[1].split('</ol>', 1)[0]
        self.assertEqual(rail.count('data-is-stage='), 5)

    def test_ai_grounding_uses_public_history_label(self):
        html = self.html('/interview-studio?mode=ai')
        self.assertIn('Use Pete&rsquo;s public history', html)

    def test_score_ring_carries_practice_signal_label(self):
        html = self.html('/interview-studio?mode=me')
        ring_block = html.split('data-is-score-ring', 1)[1][:400]
        self.assertIn('Practice signal', ring_block)
        self.assertIn('not an employer prediction', ring_block)

    def test_v01_and_v02_failure_recovery_controls_present(self):
        html = self.html('/interview-studio?mode=me')
        self.assertIn('data-is-keep-editing', html)
        self.assertIn('data-is-retry-coaching', html)
        self.assertIn('Coaching could not be completed.', html)
        video_html = self.html('/interview-studio?mode=video')
        self.assertIn('data-is-camera-enable', video_html)
        self.assertIn('not uploaded, analyzed, or retained', video_html)

    def test_history_storage_unavailable_hook_present(self):
        html = self.html('/interview-studio/history')
        self.assertIn('data-is-storage-note', html)
        self.assertIn('data-is-storage-ok', html)

    def test_coaching_status_rows_start_pending_not_prematurely_done(self):
        # Regression: the coaching-status card must not claim "Answer
        # received" before any answer has been submitted (architecture
        # section 5.3 — the three rows must reflect real request lifecycle,
        # not a hardcoded default).
        html = self.html('/interview-studio?mode=me')
        for row in ('1', '2', '3'):
            block = html.split(f'data-is-coaching-row="{row}"', 1)[0].rsplit('<div', 1)[-1]
            self.assertNotIn('is-done', block, f'row {row} must not be server-rendered as done')
        self.assertIn('data-is-coaching-row="1"', html)
        self.assertIn('data-is-coaching-row="2"', html)
        self.assertIn('data-is-coaching-row="3"', html)

    def test_coaching_status_wiring_present_in_js(self):
        source = Path('static/js/interview-studio.js').read_text(encoding='utf-8')
        self.assertIn('function setCoachingStatus', source)
        self.assertIn('data-is-coaching-row', source)
        self.assertIn('setCoachingStatus(stage)', source)

    def test_mobile_history_link_can_wrap_below_mode_row(self):
        css = Path('static/css/interview-studio.css').read_text(encoding='utf-8')
        mobile_block = css.split('@media (max-width: 48rem) {', 1)[1].split('\n}\n', 1)[0]
        self.assertIn('.is__navigation { flex-wrap: wrap', mobile_block)

    def test_clear_local_hook_is_not_duplicated(self):
        html = self.html('/interview-studio/history')
        self.assertEqual(html.count('data-is-clear-local'), 1)
        self.assertEqual(html.count('data-is-history-clear-local'), 1)

    def test_star_renderer_emits_the_classes_the_css_styles(self):
        # Codex correction 1: the STAR renderer previously created bare
        # <li> elements with no is__star-* classes, so the four STAR areas
        # ran together instead of rendering as the four framework tiles.
        source = Path('static/js/interview-studio.js').read_text(encoding='utf-8')
        star_block = source.split("var starList = one('[data-is-star]')", 1)[1].split('var dimensions', 1)[0]
        self.assertIn("'is__star-item'", star_block)
        self.assertIn("'is__star-letter'", star_block)
        self.assertIn("'is__star-label'", star_block)
        self.assertIn("setAttribute('data-status'", star_block)
        # The accessible reason text must still be conveyed, not dropped.
        self.assertIn("is__sr-only", star_block)

    def test_star_grid_is_a_real_list_matching_the_renderer(self):
        html = self.html('/interview-studio?mode=me')
        grid = html.split('data-is-star', 1)[0].rsplit('<', 1)[-1]
        self.assertTrue(grid.startswith('ul'), f'STAR container should be a <ul>, got: {grid[:20]}')
        css = Path('static/css/interview-studio.css').read_text(encoding='utf-8')
        self.assertIn('.is__star-item', css)
        self.assertIn('.is__star-letter', css)
        self.assertIn('.is__star-label', css)

    def test_stage_rail_marks_exactly_one_current_step_initially(self):
        # Codex correction 2: aria-current="step" must identify the current
        # stage, on exactly one item, in the server-rendered initial state.
        html = self.html('/interview-studio?mode=me')
        rail = html.split('data-is-stage-rail', 1)[1].split('</ol>', 1)[0]
        self.assertEqual(rail.count('aria-current="step"'), 1)
        first_item = rail.split('data-is-stage="1"', 1)[1].split('>', 1)[0]
        self.assertIn('aria-current="step"', first_item)

    def test_stage_transitions_keep_aria_current_synchronized(self):
        source = Path('static/js/interview-studio.js').read_text(encoding='utf-8')
        stage_block = source.split('function setStage(stage)', 1)[1].split('function setCoachingStatus', 1)[0]
        self.assertIn("setAttribute('aria-current', 'step')", stage_block)
        self.assertIn("removeAttribute('aria-current')", stage_block)
        self.assertIn("classList.toggle('is-current', current)", stage_block)

    def test_interview_ai_answer_basis_label_is_truthful(self):
        # Codex correction 3: "My History" implied the visitor's own or
        # account-backed history on a public demo route.
        source = Path('static/js/interview-studio.js').read_text(encoding='utf-8')
        self.assertNotIn('My History', source)
        self.assertNotIn('my-history', source)
        self.assertIn('Approved public résumé history', source)
        for forbidden in ('your private history', 'saved to your account', 'account history'):
            self.assertNotIn(forbidden.lower(), source.lower())

    def test_session_setup_is_a_quiet_disclosure(self):
        html = self.html('/interview-studio?mode=me')
        before = html.split('data-is-session-setup', 1)[0]
        tag = before.rsplit('<', 1)[-1].split(None, 1)[0]
        self.assertEqual(tag, 'details')
        self.assertIn('data-is-level', html)
        self.assertIn('data-is-settings-open', html)

    def test_theme_guardrail_js_never_observes_theme(self):
        source = Path('static/js/interview-studio.js').read_text(encoding='utf-8')
        for forbidden in ('ps-theme', 'data-theme', 'theme-toggle', 'prefers-color-scheme'):
            self.assertNotIn(forbidden, source)

    def test_modal_dialogs_expose_synced_theme_controls(self):
        html = self.html('/interview-studio?mode=me')
        self.assertEqual(html.count('data-theme-toggle-proxy'), 3)
        source = Path('static/js/theme-toggle.js').read_text(encoding='utf-8')
        self.assertIn("querySelectorAll('[data-theme-toggle-proxy]')", source)
        self.assertIn("toggle.setAttribute('aria-checked'", source)
        self.assertIn("toggle.addEventListener('click'", source)
        self.assertIn('toggles.forEach', source)

    def test_theme_guardrail_css_has_one_dark_token_block(self):
        css = Path('static/css/interview-studio.css').read_text(encoding='utf-8')
        # The full token redefinition (--is-canvas etc.) must appear exactly
        # once; a separate single-property @media (prefers-contrast: more)
        # override is legitimate and not a competing theme system.
        self.assertEqual(css.count('--is-canvas: #03101d;'), 1)
        self.assertEqual(css.count('body[data-theme="dark"] .is {'), 2)
        self.assertNotIn('background-templates', css)
        self.assertNotIn('nth-child(n+5)', css)

    def test_theme_guardrail_light_gold_text_is_accessible(self):
        css = Path('static/css/interview-studio.css').read_text(encoding='utf-8')
        self.assertIn('#8A5A00', css)
        light_block = css.split('body[data-theme="dark"] .is {', 1)[0]
        self.assertNotIn('--is-gold-text: #b87900', light_block.lower())
        self.assertNotIn('--is-gold-text: #B87900', light_block)


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

    def test_illustrative_answer_may_cite_no_evidence(self):
        """A generic best-practice example is not anyone's real history.

        Its own system prompt instructs the model to return `"evidenceIds": []`,
        so zero citations is the correct result rather than a rejection.
        """
        answer = validate_interview_model_answer(
            {
                'status': 'answered',
                'answer': 'On a cross-functional project at a previous employer, I...',
                'whyItWorks': ['Clear situation, task, action, and result.'],
                'evidenceIds': [],
            },
            {},
            require_evidence=False,
        )
        self.assertEqual(answer['status'], 'answered')
        self.assertEqual(answer['evidenceUsed'], [])

    def test_illustrative_answer_still_may_not_cite_anything(self):
        """Relaxing the citation requirement must not authorize a citation."""
        with self.assertRaisesRegex(ValueError, 'unauthorized evidence'):
            validate_interview_model_answer(
                {
                    'status': 'answered',
                    'answer': 'A generic example that wrongly claims profile evidence.',
                    'whyItWorks': ['Structured'],
                    'evidenceIds': ['modernization'],
                },
                {},
                require_evidence=False,
            )

    def test_grounded_answer_requires_evidence_by_default(self):
        """The grounded path must not be weakened by the illustrative fix."""
        with self.assertRaisesRegex(ValueError, 'no approved evidence'):
            validate_interview_model_answer(
                {'status': 'answered', 'answer': 'Unsupported.', 'whyItWorks': ['Clear'], 'evidenceIds': []},
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


class InterviewV12ModeTests(unittest.TestCase):
    """PS-INTERVIEW-002: grounding-mode control and v1.2 language."""

    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        cls.html = app.test_client().get(
            '/interview-studio').get_data(as_text=True)

    def test_mode_control_present(self):
        self.assertIn('data-is-ai-mode-group', self.html)
        for value in ('best_practice', 'member_history', 'compare'):
            self.assertIn(f'value="{value}"', self.html)

    def test_generic_example_is_labeled(self):
        self.assertIn('Illustrative best-practice example', self.html)
        self.assertIn('data-is-ai-generic', self.html)

    def test_v12_language(self):
        self.assertIn('Relevant history you may have missed', self.html)
        self.assertNotIn('Proof you may have missed', self.html)
        self.assertNotIn('approved evidence for your next draft', self.html)
        self.assertNotIn('model-answer reference', self.html)


# ---------------------------------------------------------------------------
# Interview coaching provider-reliability path.
#
# Every provider interaction below is a fake. These tests must never make a
# live AI call. They lock in the honest behavior: when the model returns a
# reply the server cannot fully validate, the request fails with 502 and the
# response body carries no coaching content whatsoever.
# ---------------------------------------------------------------------------

class _FakeContentBlock:
    def __init__(self, text):
        self.text = text


class _FakeProviderResponse:
    """Minimal stand-in for anthropic Message (text block + stop_reason)."""

    def __init__(self, text, stop_reason='end_turn'):
        self.content = [_FakeContentBlock(text)]
        self.stop_reason = stop_reason


def review_payload(**overrides):
    """A model reply that would validate, before any override is applied."""
    scores = (12, 12, 12, 12, 12)
    payload = {
        'overallScore': sum(scores),
        'verdict': 'Solid but thin',
        'encouragement': 'You have a real example here worth expanding.',
        'dimensions': [
            {
                'key': key,
                'score': score,
                'rationale': f'{key} is present but brief.',
                'nextAction': f'Add one concrete detail to {key}.',
            }
            for key, score in zip(DIMENSIONS, scores)
        ],
        'star': {
            part: {'status': 'partial', 'reason': 'Only lightly covered.'}
            for part in ('situation', 'task', 'action', 'result')
        },
        'strengths': ['You gave a real example.'],
        'improvements': ['Name the measurable result.'],
        'evidenceSuggestions': [],
    }
    payload.update(overrides)
    return payload


class InterviewCoachingFailurePathTests(unittest.TestCase):
    """Characterize and lock the validated-502 coaching failure path."""

    REVIEW_ERROR = 'The coach returned an unreadable review. Please try again.'

    def setUp(self):
        self.client = app.test_client()
        # The route carries a 6/minute cap; several requests per test would
        # otherwise turn into 429s and hide the behavior under test.
        self._limiter_enabled = limiter.enabled
        limiter.enabled = False

    def tearDown(self):
        limiter.enabled = self._limiter_enabled

    def post_review(self, reply_text, stop_reason='end_turn', answer='I led a small migration and it shipped on time.'):
        with patch('app.client') as fake_client:
            fake_client.messages.create.return_value = _FakeProviderResponse(
                reply_text, stop_reason,
            )
            return self.client.post(
                '/api/interview/review',
                json={
                    'profile_slug': 'petec',
                    'question': 'Tell me about a time you led a change.',
                    'answer': answer,
                    'level': 'experienced',
                    'family': 'behavioral',
                    'competency': 'Leadership',
                },
                base_url='http://localhost',
            )

    # -- the recorded production symptom ---------------------------------

    def test_empty_strengths_is_delivered_rather_than_discarded(self):
        """Owner decision (2026-07-20), Option B: the honest option.

        A candidate answer weak enough that the coach honestly finds nothing to
        praise produces a well-formed reply with an empty `strengths` array.
        The system prompt sets a MAXIMUM of four bullets and never a minimum, so
        zero strengths is correct model behavior. The server must deliver that
        review rather than throw it away as a 502 or pressure the model into
        manufacturing praise. PeerSlate preserves rather than manufactures.
        """
        response = self.post_review(json.dumps(review_payload(strengths=[])))
        self.assertEqual(response.status_code, 200)
        review = response.get_json()['review']
        self.assertEqual(review['strengths'], [])
        # The rest of the review is still real coaching, not a degraded stub.
        self.assertEqual(review['verdict'], 'Solid but thin')
        self.assertEqual(len(review['dimensions']), 5)
        self.assertEqual(review['improvements'], ['Name the measurable result.'])

    # -- the genuinely essential fields are still required ----------------

    def test_empty_improvements_is_rejected(self):
        """Owner decision (2026-07-20): improvements is NOT optional.

        Pete: "There should never be a blank, but there can be something to
        encourage to do better." An empty strengths list is legitimate -- a weak
        answer may genuinely have nothing to praise. An empty improvements list
        is not plausible coaching: if the coach found no way to improve a weak
        answer, that is a degraded response we should not render. The page header
        promises "what is missing, and the clearest next improvement", so that
        column is the actual deliverable.
        """
        response = self.post_review(json.dumps(review_payload(improvements=[])))
        self.assertEqual(response.status_code, 502)
        body = response.get_json()
        self.assertEqual(body['error'], self.REVIEW_ERROR)
        self.assertNotIn('review', body)

    def test_empty_improvements_is_rejected_even_when_strengths_are_present(self):
        response = self.post_review(json.dumps(review_payload(
            strengths=['You gave a real example.'], improvements=[],
        )))
        self.assertEqual(response.status_code, 502)
        self.assertNotIn('review', response.get_json())

    def test_empty_strengths_alone_still_returns_the_review(self):
        """The two lists are deliberately asymmetric; guard against a regression
        that quietly makes strengths required again alongside improvements."""
        response = self.post_review(json.dumps(review_payload(
            strengths=[], improvements=['Name the measurable result.'],
        )))
        self.assertEqual(response.status_code, 200)
        review = response.get_json()['review']
        self.assertEqual(review['strengths'], [])
        self.assertEqual(review['improvements'], ['Name the measurable result.'])

    def test_empty_improvements_is_logged_as_an_empty_required_field(self):
        """The rejection must stay attributable in the logs."""
        with self.assertLogs(app.logger, level='WARNING') as logged:
            self.post_review(json.dumps(review_payload(improvements=[])))
        line = '\n'.join(logged.output)
        self.assertIn('reason=empty_required_field', line)
        self.assertIn('provider_stop_reason=end_turn', line)

    def test_a_review_missing_its_verdict_is_still_rejected(self):
        response = self.post_review(json.dumps(review_payload(verdict='')))
        self.assertEqual(response.status_code, 502)
        body = response.get_json()
        self.assertEqual(body['error'], self.REVIEW_ERROR)
        self.assertNotIn('review', body)

    def test_a_review_missing_its_encouragement_is_still_rejected(self):
        response = self.post_review(json.dumps(review_payload(encouragement='')))
        self.assertEqual(response.status_code, 502)
        self.assertNotIn('review', response.get_json())

    def test_a_missing_verdict_is_logged_as_an_empty_required_field(self):
        with self.assertLogs(app.logger, level='WARNING') as logged:
            self.post_review(json.dumps(review_payload(verdict='')))
        line = '\n'.join(logged.output)
        self.assertIn('reason=empty_required_field', line)
        self.assertIn('provider_stop_reason=end_turn', line)

    # -- truncation is a different cause and must look different ---------

    def test_truncated_reply_is_logged_as_unparseable_with_its_stop_reason(self):
        truncated = json.dumps(review_payload())[:400]
        with self.assertLogs(app.logger, level='WARNING') as logged:
            response = self.post_review(truncated, stop_reason='max_tokens')
        self.assertEqual(response.status_code, 502)
        line = '\n'.join(logged.output)
        self.assertIn('reason=unparseable_json', line)
        self.assertIn('provider_stop_reason=max_tokens', line)
        self.assertIn('reply_chars=400', line)

    def test_prose_only_reply_is_logged_as_no_json_object(self):
        with self.assertLogs(app.logger, level='WARNING') as logged:
            response = self.post_review('I am sorry, I cannot score that answer.')
        self.assertEqual(response.status_code, 502)
        self.assertIn('reason=no_json_object', '\n'.join(logged.output))

    def test_score_arithmetic_mismatch_is_its_own_distinguishable_cause(self):
        """Dimension scores that do not sum to overallScore.

        This one is genuinely stochastic, unlike the empty-field cause, so the
        two must not be conflated in the logs.
        """
        with self.assertLogs(app.logger, level='WARNING') as logged:
            response = self.post_review(json.dumps(review_payload(overallScore=77)))
        self.assertEqual(response.status_code, 502)
        self.assertIn('reason=score_arithmetic_mismatch', '\n'.join(logged.output))

    def test_the_distinct_causes_produce_distinct_labels(self):
        seen = set()
        for reply, stop_reason in (
            (json.dumps(review_payload(verdict='')), 'end_turn'),
            (json.dumps(review_payload(overallScore=77)), 'end_turn'),
            (json.dumps(review_payload())[:400], 'max_tokens'),
            ('no json here at all', 'end_turn'),
        ):
            with self.assertLogs(app.logger, level='WARNING') as logged:
                self.post_review(reply, stop_reason)
            for entry in logged.output:
                for token in entry.split():
                    if token.startswith('reason='):
                        seen.add(token)
        self.assertEqual(len(seen), 4, f'causes were conflated: {sorted(seen)}')

    # -- privacy -----------------------------------------------------------

    def test_failure_log_never_contains_candidate_or_model_text(self):
        answer_sentinel = 'CANDIDATEANSWERSENTINEL confidential career detail'
        model_sentinel = 'MODELREPLYSENTINEL'
        with self.assertLogs(app.logger, level='WARNING') as logged:
            self.post_review(
                json.dumps(review_payload(verdict=model_sentinel, overallScore=77)),
                answer=answer_sentinel,
            )
        line = '\n'.join(logged.output)
        self.assertNotIn('CANDIDATEANSWERSENTINEL', line)
        self.assertNotIn('MODELREPLYSENTINEL', line)

    # -- the success path must be untouched --------------------------------

    def test_a_valid_reply_still_returns_the_review(self):
        response = self.post_review(json.dumps(review_payload()))
        self.assertEqual(response.status_code, 200)
        review = response.get_json()['review']
        self.assertEqual(review['overallScore'], 60)
        self.assertEqual(len(review['dimensions']), 5)

    def test_a_valid_reply_wrapped_in_code_fences_still_returns_the_review(self):
        fenced = '```json\n' + json.dumps(review_payload()) + '\n```'
        response = self.post_review(fenced)
        self.assertEqual(response.status_code, 200)

    # -- the sibling AI routes share the architecture ----------------------

    def test_improve_failure_is_labelled_and_returns_no_draft(self):
        with patch('app.client') as fake_client:
            fake_client.messages.create.return_value = _FakeProviderResponse(
                json.dumps({'draft': '', 'changes': [], 'evidenceIds': []}),
                'max_tokens',
            )
            with self.assertLogs(app.logger, level='WARNING') as logged:
                response = self.client.post(
                    '/api/interview/improve',
                    json={
                        'profile_slug': 'petec',
                        'question': 'Tell me about a time you led a change.',
                        'answer': 'I led a small migration and it shipped.',
                        'improvements': ['Name the measurable result.'],
                        'evidence_ids': [],
                    },
                    base_url='http://localhost',
                )
        self.assertEqual(response.status_code, 502)
        self.assertNotIn('improvement', response.get_json())
        line = '\n'.join(logged.output)
        self.assertIn('reason=empty_required_field', line)
        self.assertIn('provider_stop_reason=max_tokens', line)

    def test_model_answer_failure_is_labelled_and_returns_no_answer(self):
        with patch('app.client') as fake_client:
            fake_client.messages.create.return_value = _FakeProviderResponse(
                json.dumps({'status': 'maybe'}), 'end_turn',
            )
            with self.assertLogs(app.logger, level='WARNING') as logged:
                response = self.client.post(
                    '/api/interview/model-answer',
                    json={
                        'profile_slug': 'petec',
                        'question': 'Tell me about a time you led a change.',
                    },
                    base_url='http://localhost',
                )
        self.assertEqual(response.status_code, 502)
        self.assertNotIn('modelAnswer', response.get_json())
        self.assertIn('reason=invalid_status', '\n'.join(logged.output))


class InterviewEmptyReviewListRenderingTests(unittest.TestCase):
    """A zero-strengths review must read as a truthful absence, not an empty box."""

    def source(self, path):
        return Path(path).read_text(encoding='utf-8')

    def test_empty_review_lists_state_the_absence(self):
        js = self.source('static/js/interview-studio.js')
        # renderList must accept and render an explicit empty message.
        self.assertIn('function renderList(element, items, emptyMessage)', js)
        self.assertIn('is__bullets-empty', js)
        self.assertIn('EMPTY_STRENGTHS_MESSAGE', js)
        self.assertIn('EMPTY_IMPROVEMENTS_MESSAGE', js)
        # Both the live review and the history detail use it.
        self.assertEqual(js.count('EMPTY_STRENGTHS_MESSAGE'), 3)

    def test_the_empty_strengths_wording_lives_in_exactly_one_place(self):
        """Pete is still choosing the wording, so it must stay a one-line edit.

        The literal may appear only on the constant's own declaration; every
        consumer must reference the constant instead of repeating the string.
        """
        js = self.source('static/js/interview-studio.js')
        literal = 'No clear strength stood out yet — start with the improvements.'
        self.assertEqual(js.count(literal), 1)
        declarations = [
            row for row in js.splitlines()
            if 'EMPTY_STRENGTHS_MESSAGE =' in row
        ]
        self.assertEqual(len(declarations), 1)
        self.assertIn(literal, declarations[0])

    def test_the_absence_message_does_not_manufacture_praise(self):
        js = self.source('static/js/interview-studio.js')
        line = [
            row for row in js.splitlines()
            if 'EMPTY_STRENGTHS_MESSAGE =' in row
        ][0]
        # Assert the property, not one phrasing: the message must state an
        # absence. Pinning a specific wording made this test fail the first
        # time the owner exercised the single-edit-point it is meant to protect.
        self.assertRegex(
            line.lower(),
            r"did not find|no clear strength|nothing stood out|did not list",
        )
        for forbidden in ('great job', 'well done', 'nice work', 'strong answer'):
            self.assertNotIn(forbidden, line.lower())

    def test_the_empty_state_is_styled_in_both_themes(self):
        css = self.source('static/css/interview-studio.css')
        self.assertIn('.is__bullets-empty', css)
        # Theme-value-only token, so 5A light and 5C dark both carry it without
        # a second component rule branching on theme.
        self.assertIn('.is__bullets-empty { list-style: none; color: var(--is-text-muted)', css)
        # The gold finding-marker must not appear beside a statement of absence.
        self.assertIn('.is__bullets li.is__bullets-empty::before { content: none; }', css)

    def test_studio_asset_version_was_bumped_for_the_changed_bytes(self):
        html = self.source('templates/interview_studio.html')
        self.assertEqual(html.count('?v=studio-5a5c-3'), 2)
        self.assertNotIn('?v=studio-5a5c-2', html)


class InterviewGroundingModeGenerationTests(unittest.TestCase):
    """The grounding modes must actually be reachable.

    Before the fix, `best_practice` and `compare` could never succeed. The
    best-practice system prompt instructs the model to return
    `"evidenceIds": []`, but the generator validated that reply against an EMPTY
    evidence map while the validator unconditionally rejected an empty citation
    list. Obeying the prompt raised 'no approved evidence references'; citing
    anything instead raised 'unauthorized evidence' because nothing was in the
    map. Both branches raised, so every request to those two modes returned 502.

    Every provider interaction here is a fake. No live AI call is made.
    """

    QUESTION = 'Tell me about a time you led a change.'

    def setUp(self):
        self.client = app.test_client()
        self._limiter_enabled = limiter.enabled
        limiter.enabled = False

    def tearDown(self):
        limiter.enabled = self._limiter_enabled

    @staticmethod
    def illustrative_reply():
        return json.dumps({
            'status': 'answered',
            'answer': 'On a cross-functional project at a previous employer, I led the change.',
            'whyItWorks': ['Situation, task, action, and result are all present.'],
            'evidenceIds': [],
        })

    @staticmethod
    def grounded_reply(evidence_id='modernization'):
        return json.dumps({
            'status': 'answered',
            'answer': 'I led the approved modernization and it shipped.',
            'whyItWorks': ['Anchored in an approved result.'],
            'evidenceIds': [evidence_id],
        })

    def post_mode(self, mode, replies):
        with patch('app.client') as fake_client:
            fake_client.messages.create.side_effect = [
                _FakeProviderResponse(reply) for reply in replies
            ]
            return self.client.post(
                '/api/interview/model-answer',
                json={
                    'profile_slug': 'petec',
                    'question': self.QUESTION,
                    'mode': mode,
                },
                base_url='http://localhost',
            )

    def test_best_practice_succeeds_with_empty_evidence_ids(self):
        response = self.post_mode('best_practice', [self.illustrative_reply()])
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload['mode'], 'best_practice')
        self.assertEqual(payload['modelAnswer']['status'], 'answered')
        self.assertEqual(payload['modelAnswer']['evidenceUsed'], [])
        # The generic example must stay labeled as illustrative.
        self.assertTrue(payload['modelAnswer']['generic'])

    def test_compare_returns_both_a_grounded_and_an_illustrative_answer(self):
        response = self.post_mode(
            'compare', [self.grounded_reply(), self.illustrative_reply()],
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload['mode'], 'compare')
        # The grounded half still cites approved evidence.
        self.assertEqual(
            [item['id'] for item in payload['modelAnswer']['evidenceUsed']],
            ['modernization'],
        )
        # The illustrative half legitimately cites nothing.
        self.assertEqual(payload['bestPractice']['evidenceUsed'], [])
        self.assertTrue(payload['bestPractice']['generic'])

    def test_illustrative_answer_citing_evidence_is_still_rejected(self):
        """The relaxed requirement must not become a grounding loophole."""
        leaking = json.dumps({
            'status': 'answered',
            'answer': 'A generic example that wrongly claims profile evidence.',
            'whyItWorks': ['Structured'],
            'evidenceIds': ['modernization'],
        })
        with self.assertLogs(app.logger, level='WARNING') as logged:
            response = self.post_mode('best_practice', [leaking])
        self.assertEqual(response.status_code, 502)
        self.assertNotIn('modelAnswer', response.get_json())
        self.assertIn('reason=unauthorized_evidence', '\n'.join(logged.output))

    # -- the grounded path must be unchanged -------------------------------

    def test_grounded_mode_still_requires_a_citation(self):
        with self.assertLogs(app.logger, level='WARNING') as logged:
            response = self.post_mode('member_history', [self.illustrative_reply()])
        self.assertEqual(response.status_code, 502)
        self.assertNotIn('modelAnswer', response.get_json())
        self.assertIn('reason=no_evidence_reference', '\n'.join(logged.output))

    def test_grounded_mode_still_rejects_unauthorized_evidence(self):
        with self.assertLogs(app.logger, level='WARNING') as logged:
            response = self.post_mode(
                'member_history', [self.grounded_reply('private-record')],
            )
        self.assertEqual(response.status_code, 502)
        self.assertNotIn('modelAnswer', response.get_json())
        self.assertIn('reason=unauthorized_evidence', '\n'.join(logged.output))

    def test_grounded_mode_still_succeeds_on_approved_evidence(self):
        response = self.post_mode('member_history', [self.grounded_reply()])
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(
            [item['id'] for item in payload['modelAnswer']['evidenceUsed']],
            ['modernization'],
        )
        self.assertNotIn('generic', payload['modelAnswer'])

    def test_compare_still_fails_when_the_grounded_half_is_unsupported(self):
        """Compare must not launder an ungrounded member answer."""
        response = self.post_mode(
            'compare', [self.illustrative_reply(), self.illustrative_reply()],
        )
        self.assertEqual(response.status_code, 502)
        self.assertNotIn('modelAnswer', response.get_json())


class InterviewFailureReasonTests(unittest.TestCase):
    """Unit-level guarantees for the cause classifier."""

    def test_parse_and_shape_failures_map_to_their_own_labels(self):
        try:
            json.loads('{"a":')
        except json.JSONDecodeError as error:
            self.assertEqual(_interview_failure_reason(error), 'unparseable_json')
        self.assertEqual(_interview_failure_reason(TypeError('x')), 'unexpected_shape')
        self.assertEqual(_interview_failure_reason(KeyError('x')), 'unexpected_shape')

    def test_an_unknown_message_is_reported_rather_than_silently_grouped(self):
        self.assertEqual(
            _interview_failure_reason(ValueError('brand new failure mode')),
            INTERVIEW_UNCLASSIFIED_REASON,
        )

    def test_every_validator_rejection_message_has_a_cause_label(self):
        """Drift guard.

        Any new `raise ValueError(...)` added to the interview validators must
        also be classified, or coaching failures silently become unattributable
        again.
        """
        source = (Path(__file__).parents[1] / 'app.py').read_text(encoding='utf-8')
        tree = ast.parse(source)
        watched = {
            '_clamp_score',
            '_dimension_score',
            '_string_list',
            '_extract_json_object',
            'validate_interview_review',
            'validate_interview_model_answer',
            'validate_interview_improvement',
        }
        messages = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef) or node.name not in watched:
                continue
            for inner in ast.walk(node):
                if (
                    isinstance(inner, ast.Raise)
                    and isinstance(inner.exc, ast.Call)
                    and getattr(inner.exc.func, 'id', '') == 'ValueError'
                    and inner.exc.args
                    and isinstance(inner.exc.args[0], ast.Constant)
                ):
                    messages.append(inner.exc.args[0].value)

        self.assertGreaterEqual(len(messages), 15, 'validator messages not found')
        unclassified = sorted({
            message for message in messages
            if INTERVIEW_FAILURE_REASONS.get(message, INTERVIEW_UNCLASSIFIED_REASON)
            == INTERVIEW_UNCLASSIFIED_REASON
        })
        self.assertEqual(
            unclassified, [],
            'add these to INTERVIEW_FAILURE_REASONS in app.py: %s' % unclassified,
        )
