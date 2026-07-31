import ast
import json
import os
import re
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
    validate_interview_nudge,
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
            'Review My Answer',
            'Different question',
            'Create question',
            'Up next ·',
        ):
            self.assertIn(value, html)
        self.assertIn('data-is-mic="answer"', html)
        self.assertIn('data-is-answer-form', html)
        self.assertIn('data-is-mic-error="answer" hidden', html)

    def test_answer_submission_uses_progressive_workspaces(self):
        html = self.html()
        self.assertIn('type="submit" data-is-review disabled', html)
        self.assertIn('Ctrl/Command + Enter to submit', html)
        feedback_tag = html.split('data-is-feedback', 1)[1].split('>', 1)[0]
        improve_tag = html.split('data-is-improve-panel', 1)[1].split('>', 1)[0]
        video_result_tag = html.split('data-is-video-result ', 1)[1].split('>', 1)[0]
        self.assertIn('hidden', feedback_tag)
        self.assertIn('hidden', improve_tag)
        self.assertIn('hidden', video_result_tag)
        self.assertNotIn('data-is-ai-answer hidden', html)
        self.assertIn('data-is-feedback-empty', html)
        self.assertIn('data-is-improve-empty', html)
        self.assertIn('data-is-ai-answer-empty', html)
        self.assertIn('data-is-video-result-empty', html)
        self.assertIn('data-is-video-transcript-form', html)
        self.assertIn('data-is-mic="video"', html)
        self.assertIn('data-is-mic-error="video" hidden', html)
        self.assertIn('data-is-mic="custom"', html)
        self.assertIn('data-is-mic-error="custom" hidden', html)
        self.assertIn('data-is-mic="followup"', html)
        self.assertIn('data-is-mic-error="followup" hidden', html)

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
        # 'aborted' and 'no-speech' are emitted while a continuous session is
        # simply paused, so they stay unsurfaced and the silence deadline
        # decides when to stop. Every other code must reach the visitor.
        self.assertIn("var TRANSIENT_SPEECH_ERRORS = ['aborted', 'no-speech'];", script)
        self.assertIn('if (TRANSIENT_SPEECH_ERRORS.indexOf(code) !== -1) return;', script)
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
                    'Question text is sent only when you request coaching, a nudge, or an example',
                    'Answer text is sent only for coaching',
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

    def test_owner_question_controls_use_one_modal_and_no_legacy_new_question_row(self):
        html = self.html('/interview-studio?mode=me')
        self.assertEqual(html.count('data-is-custom-question-dialog'), 1)
        self.assertEqual(html.count('data-is-custom-question-form'), 1)
        self.assertEqual(html.count('data-is-custom-question data-is-autogrow'), 1)
        self.assertEqual(html.count('data-is-different-question'), 3)
        self.assertGreaterEqual(html.count('data-is-create-question'), 3)
        self.assertNotIn('data-is-video-new-question', html)
        self.assertNotRegex(html, r'>\s*New Question\s*<')

        source = Path('static/js/interview-studio.js').read_text(encoding='utf-8')
        custom_keydown = source.split(
            "customQuestionInput.addEventListener('keydown'", 1
        )[1].split("customQuestionForm.addEventListener('submit'", 1)[0]
        self.assertIn("event.key !== 'Enter'", custom_keydown)
        self.assertIn('event.shiftKey', custom_keydown)
        self.assertIn('event.preventDefault()', custom_keydown)
        self.assertIn('customQuestionForm.requestSubmit()', custom_keydown)

    def test_first_coaching_failure_retries_once_without_clearing_the_answer(self):
        source = Path('static/js/interview-studio.js').read_text(encoding='utf-8')
        retry = source.split('function postReviewWithOneRetry', 1)[1].split(
            'function addHistoryRecord', 1
        )[0]
        self.assertEqual(retry.count("postJSON('/api/interview/review'"), 2)
        self.assertIn('[500, 502, 503]', retry)
        self.assertIn('Retrying once', retry)
        submit = source.split('function submitReview()', 1)[1].split(
            "answerForm.addEventListener('submit'", 1
        )[0]
        self.assertIn('postReviewWithOneRetry', submit)
        self.assertIn('Your answer is still here.', submit)

    def test_question_changes_clear_stale_ai_context_and_preserve_sparse_progress(self):
        source = Path('static/js/interview-studio.js').read_text(encoding='utf-8')
        render = source.split('function renderQuestion(options)', 1)[1].split(
            'function syncAnswerState', 1
        )[0]
        self.assertIn('questionContextChanged', render)
        self.assertIn('resetAiAnswerForContextChange()', render)
        self.assertIn('question.text, session.level, question.family', render)

        advance = source.split('function advanceQuestion(mode)', 1)[1].split(
            "one('[data-is-next-question]')", 1
        )[0]
        self.assertIn('candidateIndex = (session.index + offset) % session.queue.length', advance)
        self.assertIn('session.completedSlots.indexOf(candidateIndex) === -1', advance)
        self.assertNotIn('buildQueue(', advance)
        self.assertNotIn('session.completedSlots = []', advance)
        controls = source.split('function syncQuestionChangeControls()', 1)[1].split(
            'function setStage', 1
        )[0]
        self.assertIn('[data-is-different-question], [data-is-create-question]', controls)
        self.assertIn('currentQuestionIsCompleted()', controls)
        replacement = source.split('function replaceCurrentQuestion', 1)[1].split(
            "all('[data-is-different-question]')", 1
        )[0]
        self.assertIn('if (currentQuestionIsCompleted())', replacement)

    def test_pending_and_interim_dictation_are_cleared_before_context_or_submit(self):
        source = Path('static/js/interview-studio.js').read_text(encoding='utf-8')
        close_custom = source.split('function closeCustomQuestion(options)', 1)[1].split(
            "all('[data-is-create-question]')", 1
        )[0]
        self.assertIn("stopDictation('interrupted')", close_custom)

        follow_up_submit = source.split("followUpForm.addEventListener('submit'", 1)[1].split(
            "followUpInput.addEventListener('keydown'", 1
        )[0]
        self.assertLess(
            follow_up_submit.index("stopDictation('interrupted')"),
            follow_up_submit.index('followUpInput.value.trim()'),
        )
        ai_mode_change = source.split("modeGroup.addEventListener('change'", 1)[1].split(
            'var followUpForm', 1
        )[0]
        self.assertIn("stopDictation('interrupted')", ai_mode_change)
        clear_local = source.split('function clearLocalData()', 1)[1].split(
            "all('[data-is-clear-local]", 1
        )[0]
        for cleanup in (
            "stopDictation('interrupted')",
            'cancelPendingReview()',
            'cancelPendingImprovement()',
            'cancelPendingAi(true)',
            'releaseMedia(true)',
            'resetVideoUi()',
        ):
            self.assertIn(cleanup, clear_local)

    def test_failed_improvement_and_discarded_media_do_not_create_phantom_state(self):
        source = Path('static/js/interview-studio.js').read_text(encoding='utf-8')
        improvement = source.split('function requestImprovement', 1)[1].split(
            "one('[data-is-improve]')", 1
        )[0]
        self.assertIn('var previousEditableDraft = draft.value.trim() || session.currentAnswer', improvement)
        self.assertIn('setHidden(improveError, true)', improvement)
        self.assertIn('draft.value = previousEditableDraft', improvement)
        self.assertIn("improvedDraft.value = ''", source)
        self.assertIn("answerContext.value = ''", source)

        release = source.split('function releaseMedia', 1)[1].split(
            'function setMode', 1
        )[0]
        self.assertIn('recorder.ondataavailable = null', release)
        self.assertIn('recorder.onstop = null', release)
        self.assertIn('media.recorder = null', release)
        self.assertIn('media.chunks = []', release)
        self.assertIn(
            "event.target.matches('[data-is-autogrow]')",
            source,
        )
        css = Path('static/css/interview-studio.css').read_text(encoding='utf-8')
        self.assertIn('.is__question-action:disabled', css)
        self.assertIn('cursor: not-allowed', css)

    def test_transmission_copy_names_every_explicit_question_request(self):
        html = self.html('/interview-studio?mode=me')
        source = Path('static/js/interview-studio.js').read_text(encoding='utf-8')
        self.assertIn(
            'Question text is sent only when you request coaching, a nudge, or an example.',
            html,
        )
        self.assertIn('Get 2–3 AI-generated hints', html)
        self.assertIn('AI-generated hints — use what helps', source)
        self.assertIn('answer text is sent only for coaching', html)
        self.assertIn('does not add it to PeerSlate’s question bank', html)
        self.assertIn(
            'If you later request a nudge, example, or coaching, the question text is sent',
            html,
        )

    def test_history_storage_unavailable_hook_present(self):
        html = self.html('/interview-studio/history')
        self.assertIn('data-is-storage-note', html)
        self.assertIn('data-is-storage-ok', html)

    def test_interview_me_rail_matches_the_v3_state_specific_contract(self):
        html = self.html('/interview-studio?mode=me')
        for hook in (
            'data-is-ready-rail',
            'data-is-session-level',
            'data-is-session-family',
            'data-is-session-format',
            'data-is-queue-open',
            'data-is-review-rail hidden',
            'data-is-priority-improvement',
            'data-is-review-score',
        ):
            self.assertIn(hook, html)
        self.assertNotIn('data-is-coaching-status', html)
        self.assertNotIn('aria-label="Answering aid"', html)

    def test_question_progress_and_composer_share_the_authoritative_task_stage(self):
        html = self.html('/interview-studio?mode=me')
        task_stage = html.split('class="is__main-column is__task-stage"', 1)[1].split(
            '<aside class="is__side-column"', 1
        )[0]
        self.assertIn('data-is-question', task_stage)
        self.assertIn('data-is-progress', task_stage)
        self.assertIn('data-is-answer-form', task_stage)
        self.assertIn('data-is-feedback', task_stage)
        self.assertEqual(html.count('data-is-queue aria-labelledby="is-queue-title"'), 1)
        self.assertGreaterEqual(html.count('data-is-queue-open'), 2)
        self.assertGreaterEqual(html.count('data-is-up-next-count'), 2)
        source = Path('static/js/interview-studio.js').read_text(encoding='utf-8')
        queue = source.split('/* Question queue */', 1)[1].split(
            '/* Review, feedback, retry, and improvement */', 1
        )[0]
        self.assertIn("var queueTriggers = all('[data-is-queue-open]')", queue)
        self.assertIn('queueDialog.show()', queue)
        self.assertIn("queueDialog.addEventListener('cancel'", queue)
        self.assertIn("event.key === 'Escape' && !queueUsesModalLayout()", queue)
        self.assertIn("window.matchMedia('(max-width: 72rem)')", queue)
        self.assertIn("queueLayoutQuery.addEventListener('change'", queue)
        self.assertIn('window.requestAnimationFrame(openQueueForCurrentLayout)', queue)
        self.assertIn('focusTarget.offsetParent === null', queue)
        self.assertIn('window.requestAnimationFrame(function ()', queue)
        self.assertIn('focusTarget.focus()', queue)

    def test_workspace_state_switches_the_context_rail(self):
        source = Path('static/js/interview-studio.js').read_text(encoding='utf-8')
        stage = source.split('function setStage(stage)', 1)[1].split('function syncModeControls', 1)[0]
        self.assertIn("setHidden(one('[data-is-ready-rail]'), reviewRailActive)", stage)
        self.assertIn("setHidden(one('[data-is-review-rail]'), !reviewRailActive)", stage)
        render = source.split('function renderReview(review)', 1)[1].split('function submitReview()', 1)[0]
        self.assertIn("text(one('[data-is-review-score]'), score)", render)
        self.assertIn("text(one('[data-is-priority-improvement]')", render)

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
        stage_block = source.split('function setStage(stage)', 1)[1].split('function syncModeControls', 1)[0]
        self.assertIn("setAttribute('aria-current', 'step')", stage_block)
        self.assertIn("removeAttribute('aria-current')", stage_block)
        self.assertIn("classList.toggle('is-current', current)", stage_block)

    def test_interview_ai_answer_basis_label_is_truthful(self):
        # Codex correction 3: "My History" implied the visitor's own or
        # account-backed history on a public demo route.
        source = Path('static/js/interview-studio.js').read_text(encoding='utf-8')
        self.assertNotIn('My History', source)
        self.assertNotIn('my-history', source)
        self.assertIn("setHidden(aiModeControl, mode !== 'ai')", source)
        self.assertIn('setHidden(formatControl, true)', source)
        html = self.html('/interview-studio?mode=ai')
        self.assertIn('Answer source', html)
        self.assertIn('Use Pete&rsquo;s public history', html)
        for forbidden in ('your private history', 'saved to your account', 'account history'):
            self.assertNotIn(forbidden.lower(), source.lower())

    def test_session_setup_is_a_quiet_disclosure(self):
        html = self.html('/interview-studio?mode=me')
        before = html.split('data-is-session-setup', 1)[0]
        tag = before.rsplit('<', 1)[-1].split(None, 1)[0]
        self.assertEqual(tag, 'details')
        self.assertIn('data-is-level', html)
        self.assertIn('data-is-ai-mode-group', html)
        self.assertNotIn('data-is-settings-open', html)

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
        self.assertEqual(css.count('--is-canvas: #071525;'), 1)
        self.assertEqual(css.count('body[data-theme="dark"] .is {'), 2)
        self.assertNotIn('background-templates', css)
        self.assertNotIn('nth-child(n+5)', css)

    def test_v3_light_palette_uses_cool_cobalt_and_teal_tokens(self):
        css = Path('static/css/interview-studio.css').read_text(encoding='utf-8')
        self.assertIn('--is-canvas: #f8faff', css)
        self.assertIn('--is-gold-text: #2858c7', css)
        self.assertIn('--is-text-muted: #5b6d89', css)
        self.assertIn('--is-success: #08776e', css)
        light_block = css.split('body[data-theme="dark"] .is {', 1)[0]
        for retired in ('#fbf8f2', '#fffdfa', '#fffefa', '#f7f1e7', '#8a5a00'):
            self.assertNotIn(retired, light_block.lower())

        def luminance(value):
            channels = [int(value[index:index + 2], 16) / 255 for index in (1, 3, 5)]
            linear = [
                channel / 12.92 if channel <= 0.04045
                else ((channel + 0.055) / 1.055) ** 2.4
                for channel in channels
            ]
            return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

        def contrast(foreground, background):
            first, second = luminance(foreground), luminance(background)
            return (max(first, second) + 0.05) / (min(first, second) + 0.05)

        for surface in ('#ffffff', '#f8faff', '#f3f6fc'):
            self.assertGreaterEqual(contrast('#5b6d89', surface), 4.5)
        self.assertGreaterEqual(contrast('#08776e', '#e2f3f1'), 4.5)

    def test_compact_multiline_fields_share_one_autogrow_contract(self):
        html = self.html('/interview-studio?mode=me')
        self.assertEqual(html.count('data-is-autogrow'), 6)
        self.assertRegex(html, r'id="is-answer"\s+rows="3"')
        self.assertRegex(html, r'id="is-improved-draft" rows="5"')
        self.assertRegex(html, r'id="is-video-transcript" rows="3"')
        self.assertRegex(html, r'id="is-ai-follow-up" rows="2"')
        self.assertRegex(html, r'id="is-custom-question" rows="4"')
        self.assertRegex(html, r'id="is-answer-context" rows="3"')
        css = Path('static/css/interview-studio.css').read_text(encoding='utf-8')
        self.assertIn('.is textarea[data-is-autogrow]', css)
        self.assertIn('max-height: none', css)
        self.assertIn('overflow-y: hidden', css)
        self.assertIn('min-height: 9rem', css)
        self.assertIn('min-height: 11rem', css)
        source = Path('static/js/interview-studio.js').read_text(encoding='utf-8')
        self.assertIn('function autoGrowTextarea(element)', source)
        self.assertIn("element.style.height = '0px'", source)
        self.assertIn('Math.max(element.scrollHeight, minimum)', source)
        self.assertIn("window.addEventListener('resize'", source)
        self.assertIn('if (element.offsetParent !== null) autoGrowTextarea(element)', source)
        self.assertIn('autoGrowTextarea(answer)', source)
        self.assertIn('autoGrowTextarea(draft)', source)
        self.assertIn('autoGrowTextarea(videoTranscript)', source)

    def test_progressive_review_and_improve_states_reuse_existing_lifecycle(self):
        source = Path('static/js/interview-studio.js').read_text(encoding='utf-8')
        clear_block = source.split('function clearReviewState()', 1)[1].split('function restoreDraft', 1)[0]
        self.assertIn('setHidden(feedbackBlock, true)', clear_block)
        self.assertIn('setHidden(improveBlock, true)', clear_block)
        submit_block = source.split('function submitReview()', 1)[1].split("answerForm.addEventListener", 1)[0]
        self.assertIn('setHidden(answeringBlock, true)', submit_block)
        self.assertIn('setHidden(feedbackBlock, false)', submit_block)
        failure_block = submit_block.split("}).catch(function (error)", 1)[1]
        self.assertIn('setStage(1)', failure_block)
        self.assertIn("root.setAttribute('data-is-workspace-state'", source)

    def test_interview_ai_source_dropdown_is_in_session_controls_before_generation(self):
        html = self.html('/interview-studio?mode=ai')
        form = html.split('data-is-ai-form', 1)[1].split('</form>', 1)[0]
        self.assertLess(html.index('data-is-family'), html.index('data-is-ai-mode-group'))
        self.assertLess(html.index('data-is-ai-mode-group'), html.index('data-is-format-control'))
        self.assertLess(html.index('data-is-ai-mode-group'), html.index('data-is-ai-form'))
        self.assertLess(form.index('data-is-ai-question'), form.index('Get example'))
        self.assertNotIn('<fieldset class="is__ai-grounding"', html)
        self.assertNotIn('data-is-settings-open', html)
        self.assertIn('data-is-ai-basis-label', html)
        self.assertIn('data-is-ai-basis-guidance', html)
        self.assertIn('data-is-follow-up-note', html)
        self.assertIn('data-is-follow-up-error role="alert"', html)
        self.assertIn('data-is-ai-error role="alert"', html)
        self.assertIn('its source label here for you to verify', html)

        source = Path('static/js/interview-studio.js').read_text(encoding='utf-8')
        basis_block = source.split("modeGroup.addEventListener('change'", 1)[1].split(
            'var followUpForm', 1
        )[0]
        self.assertIn('basisLabel.textContent', basis_block)
        self.assertIn('basisGuidance.textContent', basis_block)
        self.assertIn('resetAiAnswerForContextChange()', basis_block)
        self.assertIn('Ask a follow-up grounded in the current answer context.', source)
        self.assertIn('Follow-up is unavailable because no approved-history example was returned.', source)
        self.assertIn('followUpOpen.disabled = !followUpAvailable', source)
        self.assertIn("announce('Follow-up is unavailable for this answer.')", source)

        css = Path('static/css/interview-studio.css').read_text(encoding='utf-8')
        self.assertIn('"form form"\n        "main side"', css)
        self.assertIn('top: -8rem;', css)
        self.assertIn('.is__improve .is__compare [data-is-original-answer],', css)
        self.assertIn('grid-area: auto;', css)
        self.assertIn('font-size: 0.848rem;', css)

    def test_failed_follow_up_preserves_question_and_existing_answer_workspace(self):
        source = Path('static/js/interview-studio.js').read_text(encoding='utf-8')
        follow_up_submit = source.split("followUpForm.addEventListener('submit'", 1)[1].split(
            "one('[data-is-ai-new]')", 1
        )[0]
        self.assertNotIn("followUpInput.value = ''", follow_up_submit)

        request_block = source.split('function requestModelAnswer(followUp)', 1)[1].split(
            "aiForm.addEventListener('submit'", 1
        )[0]
        self.assertIn("followUpInput.value.trim() === followUp", request_block)
        self.assertIn("setAiState(currentModelAnswer ? 'ready' : 'failure')", request_block)
        self.assertIn('failureTarget = followUp && currentModelAnswer ? followUpError : aiError', request_block)
        self.assertIn('Your first answer is preserved. Edit the follow-up and try again.', request_block)
        self.assertIn('mode: selectedAiMode()', request_block)
        self.assertNotIn("followUp ? 'member_history'", request_block)

    def test_ai_loading_and_initial_failure_replace_the_same_answer_workspace(self):
        html = self.html('/interview-studio?mode=ai')
        workspace = html.index('data-is-ai-answer')
        loading = html.index('data-is-ai-loading')
        failure = html.index('data-is-ai-error')
        empty = html.index('data-is-ai-answer-empty')
        content = html.index('data-is-ai-answer-content')
        self.assertLess(workspace, loading)
        self.assertLess(loading, failure)
        self.assertLess(failure, empty)
        self.assertLess(empty, content)

        source = Path('static/js/interview-studio.js').read_text(encoding='utf-8')
        request = source.split('function requestModelAnswer(followUp)', 1)[1].split(
            "aiForm.addEventListener('submit'", 1
        )[0]
        initial = request.split('if (!followUp) {', 1)[1].split('}', 1)[0]
        self.assertIn('setHidden(aiAnswerEmpty, true)', initial)
        no_answer_failure = request.split('} else {', 1)[-1]
        self.assertIn('setHidden(aiAnswerEmpty, true)', no_answer_failure)

    def test_ai_insufficient_history_never_labels_the_empty_result_as_a_person_answer(self):
        source = Path('static/js/interview-studio.js').read_text(encoding='utf-8')
        render = source.split('function renderModelAnswer(payload)', 1)[1].split(
            'function requestModelAnswer(followUp)', 1
        )[0]
        self.assertIn("'No grounded answer available'", render)
        self.assertLess(
            render.index("'No grounded answer available'"),
            render.index("'Best-practice example'"),
        )

    def test_progressive_states_move_focus_after_the_trigger_disappears(self):
        html = self.html('/interview-studio?mode=me')
        feedback_tag = html.split('data-is-feedback ', 1)[1].split('>', 1)[0]
        improve_tag = html.split('data-is-improve-panel ', 1)[1].split('>', 1)[0]
        self.assertIn('tabindex="-1"', feedback_tag)
        self.assertIn('tabindex="-1"', improve_tag)

        source = Path('static/js/interview-studio.js').read_text(encoding='utf-8')
        self.assertIn('cancelReviewButton.focus()', source)
        self.assertIn('feedbackBlock.focus({ preventScroll: true })', source)
        self.assertIn('improveBlock.focus({ preventScroll: true })', source)
        cancel = source.split("cancelReviewButton.addEventListener('click'", 1)[1].split(
            'if (keepEditingButton)', 1
        )[0]
        self.assertIn('answer.focus()', cancel)
        out_loud = source.split("one('[data-is-retry-out-loud]').addEventListener", 1)[1].split(
            '/* ------------------------------------------------------------------', 1
        )[0]
        self.assertIn("one('[data-is-camera-enable]').focus()", out_loud)

    def test_video_controls_restore_focus_to_the_next_available_action(self):
        source = Path('static/js/interview-studio.js').read_text(encoding='utf-8')
        enable = source.split('function enableCamera()', 1)[1].split('function supportedMimeType()', 1)[0]
        self.assertIn('if (startRecord.disabled) videoTranscript.focus()', enable)
        self.assertIn('else startRecord.focus()', enable)
        self.assertIn('cameraEnable.focus()', enable)
        recording = source.split('function startRecording()', 1)[1].split('function finishRecording()', 1)[0]
        self.assertIn('stopRecord.focus()', recording)
        finish = source.split('function finishRecording()', 1)[1].split('function resetVideoUi', 1)[0]
        self.assertIn('retakeRecord.focus()', finish)
        discard = source.split("discardRecord.addEventListener('click'", 1)[1].split(
            "videoTranscript.addEventListener('input'", 1
        )[0]
        self.assertIn('cameraEnable.focus()', discard)

    def test_video_stop_exposes_an_honest_local_finalizing_state(self):
        source = Path('static/js/interview-studio.js').read_text(encoding='utf-8')
        self.assertIn("stopping: 'Finalizing this recording locally. No upload is occurring.'", source)
        stop = source.split('function stopRecording()', 1)[1].split(
            'function finishRecording()', 1
        )[0]
        self.assertLess(stop.index("setVideoState('stopping')"), stop.index('media.recorder.stop()'))
        self.assertIn("text(stopRecord, 'Finalizing locally…')", stop)
        finish = source.split('function finishRecording()', 1)[1].split(
            'function resetVideoUi', 1
        )[0]
        self.assertIn("text(stopRecord, 'Stop Recording')", finish)
        css = Path('static/css/interview-studio.css').read_text(encoding='utf-8')
        self.assertIn('.is[data-is-video-state="stopping"] .is__video-content-review', css)

    def test_completed_video_playback_requires_confirmation_before_context_reset(self):
        source = Path('static/js/interview-studio.js').read_text(encoding='utf-8')
        helper = source.split('function prepareVideoContextChange(message)', 1)[1].split(
            'function advanceQuestion', 1
        )[0]
        self.assertIn(
            'pendingRecording || hasCompletedPlayback || transcriptDraft',
            helper,
        )
        device_settings = source.split(
            "one('[data-is-device-settings]').addEventListener('click'",
            1,
        )[1].split('startRecord.addEventListener', 1)[0]
        self.assertIn('current local recording or transcript draft', device_settings)
        self.assertLess(
            device_settings.index('prepareVideoContextChange'),
            device_settings.index('resetVideoUi()'),
        )

    def test_mode_reveal_recomputes_hidden_autogrow_fields(self):
        source = Path('static/js/interview-studio.js').read_text(encoding='utf-8')
        set_mode = source.split('function setMode(mode, updateUrl)', 1)[1].split(
            '\n    modeTabs.forEach(function (tab)', 1
        )[0]
        self.assertIn("refreshAutogrow(one('[data-is-panel=\"' + mode + '\"]'))", set_mode)

    def test_question_changes_flush_dictation_and_save_under_the_old_question(self):
        source = Path('static/js/interview-studio.js').read_text(encoding='utf-8')
        helper = source.split('function prepareAnswerContextChange()', 1)[1].split(
            'function prepareVideoContextChange', 1
        )[0]
        self.assertLess(helper.index("stopDictation('interrupted')"), helper.index('persistCurrentAnswerDraft()'))
        self.assertLess(helper.index('persistCurrentAnswerDraft()'), helper.index('confirmReplace()'))
        persist = source.split('function persistCurrentAnswerDraft()', 1)[1].split(
            "answer.addEventListener('input'", 1
        )[0]
        self.assertIn('window.clearTimeout(autosaveTimer)', persist)
        self.assertIn('saveDraft(false)', persist)
        self.assertIn('removeStored(draftKey(currentQuestion().text))', persist)
        different = source.split("all('[data-is-different-question]')", 1)[1].split(
            "var customQuestionDialog", 1
        )[0]
        self.assertIn('prepareCurrentQuestionChange', different)
        self.assertIn('pickDifferentQuestion()', different)
        self.assertIn('Session progress did not change.', different)
        queue = source.split("button.addEventListener('click', function ()", 1)[1].split(
            'item.appendChild(button)', 1
        )[0]
        self.assertIn('if (!prepareCurrentQuestionChange', queue)

    def test_short_desktop_keeps_primary_answer_action_in_the_first_viewport(self):
        css = Path('static/css/interview-studio.css').read_text(encoding='utf-8')
        short_desktop = css.split(
            '@media (min-width: 64.01rem) and (max-height: 50rem)', 1
        )[1].split('/* The global dark shell', 1)[0]
        self.assertIn('min-height: 6.5rem', short_desktop)
        self.assertIn('.is__composer-actions', short_desktop)
        self.assertIn('margin-top: 0.35rem', short_desktop)

    def test_ai_and_video_submissions_stop_active_dictation_before_state_changes(self):
        source = Path('static/js/interview-studio.js').read_text(encoding='utf-8')
        ai_submit = source.split("aiForm.addEventListener('submit'", 1)[1].split(
            "followUpOpen.addEventListener('click'", 1
        )[0]
        follow_up_submit = source.split("followUpForm.addEventListener('submit'", 1)[1].split(
            "one('[data-is-ai-new]')", 1
        )[0]
        recording = source.split('function startRecording()', 1)[1].split(
            'function finishRecording()', 1
        )[0]
        self.assertIn("stopDictation('interrupted')", ai_submit)
        self.assertIn("stopDictation('interrupted')", follow_up_submit)
        self.assertIn("stopDictation('interrupted')", recording)

    def test_video_controls_stay_in_the_stage_and_device_state_uses_the_rail(self):
        html = self.html('/interview-studio?mode=video')
        camera_to_transcript = html.split('class="is__camera"', 1)[1].split(
            'data-is-video-transcript-form', 1
        )[0]
        self.assertIn('class="is__camera-controls"', camera_to_transcript)
        self.assertIn('data-is-record-start', camera_to_transcript)
        self.assertIn('data-is-record-stop', camera_to_transcript)
        self.assertIn('data-is-record-retake', camera_to_transcript)
        self.assertIn('data-is-record-discard', camera_to_transcript)
        self.assertNotIn('data-is-video-new-question', camera_to_transcript)
        video_question = html.split('data-is-video-question', 1)[1].split('class="is__camera"', 1)[0]
        self.assertIn('data-is-different-question', video_question)
        self.assertIn('data-is-create-question', video_question)
        self.assertIn('is__video-device-card', html)
        self.assertIn('data-is-video-state-copy', html)
        source = Path('static/js/interview-studio.js').read_text(encoding='utf-8')
        retake = source.split("retakeRecord.addEventListener('click'", 1)[1].split(
            "discardRecord.addEventListener('click'", 1
        )[0]
        self.assertIn('resetVideoUi({ preserveTranscript: true })', retake)
        self.assertIn('removeHistoryRecord(recordId)', retake)
        self.assertIn('enableCamera()', retake)

        css = Path('static/css/interview-studio.css').read_text(encoding='utf-8')
        self.assertIn('.is__camera-controls', css)
        self.assertIn('min-height: clamp(18rem, 26vw, 20rem)', css)

    def test_interview_mobile_uses_global_menu_without_member_ai(self):
        html = self.html('/interview-studio?mode=me')
        self.assertIn('data-platform-menu-toggle', html)
        self.assertNotIn('class="nav-ask-ai"', html)
        self.assertNotIn('data-open-chat', html)
        self.assertNotIn('data-chat-open', html)
        css = Path('static/css/interview-studio.css').read_text(encoding='utf-8')
        self.assertNotIn('body.interview-studio-page .mobile-tabbar', css)
        chat_rule = css.rsplit('body.interview-studio-page #chat-toggle', 1)[1].split('}', 1)[0]
        self.assertIn('display: none !important', chat_rule)
        self.assertIn('position: fixed', css)
        self.assertIn('minmax(0, 0.85fr)', css)
        self.assertIn('minmax(0, 1.15fr)', css)
        self.assertIn('.is__queue-mobile', css)
        compact_mobile = css.rsplit('@media (max-width: 24rem) {', 1)[1].split(
            '/* The global dark shell', 1
        )[0]
        self.assertIn('.is__dock-label-compact', compact_mobile)
        self.assertIn('.is__composer-actions [data-is-mic-label]', compact_mobile)
        self.assertNotRegex(
            css,
            r'body\.interview-studio-page \.platform-nav__links,[\s\S]{0,220}display:\s*none',
        )

    def test_ai_transfer_and_video_discard_preserve_member_work(self):
        source = Path('static/js/interview-studio.js').read_text(encoding='utf-8')
        self.assertIn('storedTargetDraft', source)
        self.assertIn('Practice transfer cancelled. The existing draft is unchanged.', source)
        self.assertIn('resetVideoUi({ preserveTranscript: true })', source)
        self.assertIn('Any transcript text will stay in the composer.', source)
        self.assertIn("if (!options.preserveTranscript) videoTranscript.value = ''", source)
        pagehide = source.split("window.addEventListener('pagehide'", 1)[1].split('/* History', 1)[0]
        self.assertIn('URL.revokeObjectURL(media.playbackUrl)', pagehide)


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

    def test_inconsistent_overall_score_is_healed_to_the_dimension_total(self):
        """A routine model arithmetic slip must not discard a complete review.

        The five dimension scores are the itemized breakdown the reader sees, and
        the prompt already requires overallScore to equal their exact sum. When a
        capable model still writes an overall that is off by a point or two, the
        review is healed to the true dimension total (here 17+16+16+16+17 = 82)
        rather than rejected as a 502. Every dimension stays clamped to 0-20, so a
        healed total is always a sane 0-100.
        """
        raw = valid_review()
        raw['overallScore'] = 90  # dimensions actually sum to 82
        review = validate_interview_review(raw, 100, {'modernization'})
        self.assertEqual(review['overallScore'], 82)
        self.assertEqual(sum(item['score'] for item in review['dimensions']), 82)

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
            'member_history',
            {
                'answer': 'I delivered the approved result.',
                'evidenceUsed': [{'id': 'approved'}],
            },
        )
        context = _load_interview_model_context(token)
        self.assertEqual(context['question'], 'Tell me about a project.')
        self.assertEqual(context['answer'], 'I delivered the approved result.')
        self.assertEqual(context['evidence_ids'], ['approved'])
        self.assertEqual(context['mode'], 'member_history')

    def test_compare_context_requires_a_signed_illustrative_branch(self):
        token = _sign_interview_model_context(
            'petec',
            'Tell me about a project.',
            'experienced',
            'behavioral',
            'compare',
            {
                'answer': 'I delivered the approved result.',
                'evidenceUsed': [{'id': 'approved'}],
            },
        )
        with self.assertRaisesRegex(ValueError, 'illustrative context is incomplete'):
            _load_interview_model_context(token)

    def test_improved_draft_uses_selected_evidence_only(self):
        evidence = {'selected': {'id': 'selected', 'metric': '20%', 'label': 'Approved'}}
        improvement = validate_interview_improvement(
            {'draft': 'I improved the result.', 'changes': ['Clarified the action'], 'evidenceIds': ['selected']},
            evidence,
        )
        self.assertEqual(improvement['evidenceUsed'][0]['id'], 'selected')

    def test_nudge_requires_two_or_three_real_hints(self):
        self.assertEqual(
            validate_interview_nudge({'hints': ['Frame the tradeoff.', 'Name the decision rule.']}),
            {'hints': ['Frame the tradeoff.', 'Name the decision rule.']},
        )
        with self.assertRaisesRegex(ValueError, 'nudge is incomplete'):
            validate_interview_nudge({'hints': ['Only one hint.']})

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

    def test_follow_up_rejects_a_client_source_mode_change(self):
        token = _sign_interview_model_context(
            'petec',
            'Tell me about a project.',
            'experienced',
            'behavioral',
            'best_practice',
            {
                'answer': 'A generic, illustrative answer.',
                'evidenceUsed': [],
            },
        )
        response = self.client.post(
            '/api/interview/model-answer',
            json={
                'follow_up': 'What happened next?',
                'context_token': token,
                'mode': 'member_history',
            },
            base_url='http://localhost',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('source no longer matches', response.get_json()['error'])

    def test_interview_endpoints_reject_scalar_and_wrong_shaped_json(self):
        for path in (
            '/api/interview/review',
            '/api/interview/improve',
            '/api/interview/nudge',
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
        self.assertIn('<select data-is-ai-mode', self.html)
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

    def test_score_arithmetic_mismatch_is_healed_rather_than_failed(self):
        """Dimension scores that do not sum to overallScore.

        This slip is genuinely stochastic, and it used to sink the entire review
        as a 502. The itemized dimension scores are the source of truth the reader
        sees, so the endpoint now heals the overall to their true sum (5 x 12 = 60)
        and delivers the coaching instead of discarding it.
        """
        response = self.post_review(json.dumps(review_payload(overallScore=77)))
        self.assertEqual(response.status_code, 200)
        review = response.get_json()['review']
        self.assertEqual(review['overallScore'], 60)
        self.assertEqual(sum(item['score'] for item in review['dimensions']), 60)

    def test_the_distinct_causes_produce_distinct_labels(self):
        seen = set()
        for reply, stop_reason in (
            (json.dumps(review_payload(verdict='')), 'end_turn'),
            (json.dumps(review_payload(star='nope')), 'end_turn'),
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
                json.dumps(review_payload(verdict=model_sentinel, improvements=[])),
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

    def test_studio_assets_are_versioned_by_content_hash(self):
        """Both Studio assets must reach the browser content-hash versioned.

        This originally pinned a hand-typed `studio-5a5c-N` signature and
        guarded two things: that the token moved when the bytes changed, and
        that two branches could not silently ship different bytes under one
        cached URL (which happened once when both bumped to `-3` identically).

        Automatic content-hash versioning makes both guarantees structural
        rather than manual: the token IS the file's hash, so it can only
        match the exact bytes being served, and CSS and JS now carry
        independent hashes derived from their own content. A silent merge can
        no longer pin stale bytes. Assert the rendered page carries a real
        content hash on each asset, and that no hand-typed token survives.
        """
        with app.test_client() as client:
            html = client.get(
                '/interview-studio', base_url='http://localhost'
            ).get_data(as_text=True)
        self.assertRegex(html, r'css/interview-studio\.css\?v=[0-9a-f]{12}')
        self.assertRegex(html, r'js/interview-studio\.js\?v=[0-9a-f]{12}')
        self.assertNotIn('studio-5a5c-', html)


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

    def test_compare_follow_up_keeps_grounded_history_out_of_generic_prompt(self):
        prior = 'I led the approved modernization and it shipped.'
        prior_illustrative = 'The illustrative candidate ranked the work and explained the tradeoff.'
        token = _sign_interview_model_context(
            'petec',
            self.QUESTION,
            'experienced',
            'behavioral',
            'compare',
            {
                'answer': prior,
                'evidenceUsed': [{'id': 'modernization'}],
            },
            {
                'answer': prior_illustrative,
                'evidenceUsed': [],
            },
        )
        with patch('app.client') as fake_client:
            fake_client.messages.create.side_effect = [
                _FakeProviderResponse(self.grounded_reply()),
                _FakeProviderResponse(self.illustrative_reply()),
            ]
            response = self.client.post(
                '/api/interview/model-answer',
                json={
                    'follow_up': 'What did you learn?',
                    'context_token': token,
                    'mode': 'compare',
                },
                base_url='http://localhost',
            )
        self.assertEqual(response.status_code, 200)
        calls = fake_client.messages.create.call_args_list
        grounded_prompt = calls[0].kwargs['messages'][0]['content']
        generic_prompt = calls[1].kwargs['messages'][0]['content']
        self.assertIn(prior, grounded_prompt)
        self.assertNotIn(prior, generic_prompt)
        self.assertIn(prior_illustrative, generic_prompt)
        self.assertIn('What did you learn?', generic_prompt)

    def test_nudge_endpoint_returns_only_validated_hints(self):
        reply = json.dumps({
            'hints': [
                'Choose one decision rule for sorting the urgent work.',
                'Explain how you communicate tradeoffs before priorities collide.',
                'Close with how you verify the highest-risk work moved first.',
            ],
        })
        with patch('app.client') as fake_client:
            fake_client.messages.create.return_value = _FakeProviderResponse(reply)
            response = self.client.post(
                '/api/interview/nudge',
                json={
                    'profile_slug': 'petec',
                    'question': 'How do you prioritize when everything feels urgent?',
                    'level': 'leadership',
                    'family': 'situational',
                    'competency': 'Pressure',
                    'practice_mode': 'video',
                },
                base_url='http://localhost',
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.get_json()['hints']), 3)
        provider_call = fake_client.messages.create.call_args
        self.assertNotIn('Approved evidence', provider_call.kwargs['system'])


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
            '_dimension_score',
            '_string_list',
            '_extract_json_object',
            'validate_interview_review',
            'validate_interview_model_answer',
            'validate_interview_improvement',
            'validate_interview_nudge',
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


class InterviewStudioDictationTests(unittest.TestCase):
    """PS-INTERVIEW-MIC-001: continuous speak-your-answer dictation.

    Pete's contract: click to start, keep listening, stop on a second click,
    and auto-stop after ten seconds of silence. Speaking is an input method for
    the same answer field the typed path uses, never a separate answer type.
    """

    maxDiff = None

    def setUp(self):
        self.client = app.test_client()

    def html(self, path='/interview-studio'):
        response = self.client.get(path, base_url='http://localhost')
        self.assertEqual(response.status_code, 200)
        return response.get_data(as_text=True)

    @property
    def script(self):
        return Path('static/js/interview-studio.js').read_text(encoding='utf-8')

    @property
    def css(self):
        return Path('static/css/interview-studio.css').read_text(encoding='utf-8')

    # -- placement -----------------------------------------------------

    def test_answer_dictation_control_sits_with_the_answer_not_in_a_side_card(self):
        """The control must be reachable where the visitor is answering.

        It previously lived in the side column, which reflows below the
        composer on narrow viewports, so a phone visitor never saw it.
        """
        html = self.html()
        actions = html.split('<div class="is__actions is__composer-actions">', 1)[1].split('</div>', 1)[0]
        self.assertIn('data-is-mic="answer"', actions)
        self.assertIn('data-is-review', actions)
        side_column = html.split('<aside class="is__side-column"', 1)[1]
        self.assertNotIn('data-is-mic="answer"', side_column)

    def test_exactly_one_dictation_control_exists_per_field(self):
        """Two controls bound to one field would desynchronise the toggle."""
        html = self.html()
        for kind in ('answer', 'custom', 'followup', 'video'):
            with self.subTest(kind=kind):
                self.assertEqual(html.count('data-is-mic="%s"' % kind), 1)

    def test_no_second_dictation_pipeline_is_introduced(self):
        """PS-VOICE-001 stays the only voice-Capture architecture.

        One shared browser helper serves every Studio text field; a parallel
        recogniser would be the forbidden second path.
        """
        script = self.script
        self.assertEqual(script.count('function startDictation'), 1)
        self.assertEqual(script.count('new Recognition()'), 1)
        # No audio ever leaves the page for a PeerSlate server: the only
        # endpoints this route calls are the text coaching ones.
        self.assertEqual(
            sorted(set(re.findall(r"'(/api/[a-z0-9/_-]+)'", script))),
            ['/api/interview/improve', '/api/interview/model-answer', '/api/interview/nudge', '/api/interview/review'],
        )
        self.assertNotIn('uploadUrl', script)
        self.assertNotIn('owner-capture-voice', script)

    # -- Pete's behaviour contract -------------------------------------

    def test_recognition_runs_continuously_with_interim_results(self):
        script = self.script
        self.assertIn('recognition.continuous = true;', script)
        self.assertIn('recognition.interimResults = true;', script)
        self.assertNotIn('recognition.continuous = false;', script)
        self.assertNotIn('recognition.interimResults = false;', script)

    def test_ten_second_silence_deadline_stops_dictation(self):
        script = self.script
        self.assertIn('var DICTATION_SILENCE_MS = 10000;', script)
        self.assertIn("stopDictation('silence');", script)
        self.assertIn('state.silenceDeadline = Date.now() + DICTATION_SILENCE_MS;', script)

    def test_any_speech_resets_the_silence_deadline(self):
        """Silence means silence, not elapsed time since the visitor began."""
        result_handler = self.script.split('recognition.onresult = function', 1)[1]
        self.assertIn('armDictationSilence(state);', result_handler.split('};', 1)[0])

    def test_second_click_stops_dictation(self):
        script = self.script
        self.assertIn('function toggleDictation', script)
        self.assertIn('if (pendingDictationPermission) {', script)
        self.assertIn('cancelPendingDictationPermission();', script)
        self.assertIn("var sameButton = activeDictation.button === button;", script)
        self.assertIn("stopDictation('manual');", script)
        self.assertIn("button.addEventListener('click', function () { toggleDictation(", script)

    def test_a_spontaneous_browser_end_restarts_instead_of_ending_the_session(self):
        """Chrome ends continuous recognition on its own; the visitor's
        intent, not the browser's timeout, decides when listening stops."""
        end_handler = self.script.split('recognition.onend = function', 1)[1]
        self.assertIn('state.restarts += 1;', end_handler)
        self.assertIn('recognition.start();', end_handler)
        self.assertIn('var DICTATION_MAX_RESTARTS = 120;', self.script)

    def test_transcript_lands_in_the_same_editable_field_as_typing(self):
        script = self.script
        self.assertIn('function appendTranscript', script)
        self.assertIn("target.dispatchEvent(new Event('input', { bubbles: true }));", script)
        # Only finalised speech is committed, so live interim text can never
        # overwrite an edit the visitor is making by hand.
        self.assertIn('if (result.isFinal) finalText', script)
        self.assertIn('state.words += appendTranscript(state.target, finalText);', script)

    def test_unfinalised_speech_is_kept_not_discarded_on_stop(self):
        """The visitor saw those words in the preview; stopping must not
        silently throw them away."""
        script = self.script
        self.assertIn('if (state.interim) {', script)
        self.assertIn('state.words += appendTranscript(state.target, state.interim);', script)
        stop_block = script.split('function stopDictation(reason)', 1)[1].split(
            'function beginDictation', 1
        )[0]
        self.assertIn('finishDictation(state);', stop_block)
        self.assertNotIn('setTimeout', stop_block)
        self.assertNotIn('DICTATION_STOP_WATCHDOG_MS', script)

    def test_video_transcript_submission_flushes_visible_dictation_before_reading(self):
        script = self.script
        submit_block = script.split(
            "videoTranscriptForm.addEventListener('submit'", 1
        )[1].split("window.addEventListener('beforeunload'", 1)[0]
        self.assertLess(
            submit_block.index("stopDictation('interrupted')"),
            submit_block.index('var transcript = videoTranscript.value.trim()'),
        )

    def test_nothing_captured_message_distinguishes_heard_from_never_heard(self):
        script = self.script
        self.assertIn('state.heardSomething', script)
        self.assertIn('Dictation stopped before any speech could be transcribed.', script)

    def test_leaving_the_field_stops_the_microphone(self):
        script = self.script
        set_mode = script.split('function setMode(mode, updateUrl)', 1)[1].split(
            'modeTabs.forEach', 1
        )[0]
        self.assertLess(
            set_mode.index("stopDictation('interrupted')"),
            set_mode.index("prepareVideoContextChange('Discard the active recording"),
        )
        self.assertIn("stopDictation('interrupted');\n        var responseText", script)
        self.assertIn("if (event.key !== 'Escape' || !activeDictation) return;", script)

    # -- truthful states -----------------------------------------------

    def test_unsupported_browser_is_declared_up_front_not_on_failure(self):
        script = self.script
        self.assertIn('function speechIsSupported', script)
        self.assertIn('if (!speechIsSupported()) {', script)
        self.assertIn("button.setAttribute('aria-disabled', 'true');", script)
        self.assertIn('Speech input is not supported in this browser. Typing works normally.', script)

    def test_every_recognition_failure_has_an_exact_visible_message(self):
        script = self.script
        for code, fragment in (
            ('not-allowed', 'Microphone permission was denied.'),
            ('audio-capture', 'No microphone was found'),
            ('network', 'Dictation lost its network connection.'),
            ('no-speech', 'No speech was detected.'),
        ):
            with self.subTest(code=code):
                self.assertIn(fragment, script)
        self.assertIn("showMicError(state.kind, message);", script)

    def test_a_dismissed_permission_prompt_is_reported_honestly_not_invented(self):
        """The Web Speech API cannot distinguish a dismissed prompt from
        silence, so the copy names it as a possible cause instead of
        fabricating a state we cannot detect."""
        script = self.script
        self.assertIn(
            'Dictation stopped without capturing any speech. If your browser asked for '
            'microphone permission and the prompt was closed, nothing was heard. '
            'You can keep typing.',
            script,
        )

    def test_the_ten_second_rule_is_discoverable_before_it_fires(self):
        html = self.html()
        self.assertIn('keeps listening until you stop it or you go quiet for 10 seconds', html)
        script = self.script
        self.assertIn('Listening. Stops after 10 seconds of silence, or press Escape.', script)
        self.assertIn("'Listening. Stopping in ' + Math.ceil(remaining / 1000) + 's unless you speak.'", script)
        self.assertIn('Dictation stopped after 10 seconds of silence.', script)

    def test_the_public_route_claims_no_server_capture_or_account_history(self):
        html = self.html()
        self.assertIn('PeerSlate does not receive or keep the audio.', html)
        for forbidden in (
            'saved to your account',
            'securely recorded',
            'synced across devices',
            'your private history',
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, html)

    # -- accessibility --------------------------------------------------

    def test_toggle_state_is_exposed_to_assistive_technology(self):
        html = self.html()
        self.assertEqual(html.count('aria-pressed="false"'), 4)
        script = self.script
        self.assertIn("button.setAttribute('aria-pressed', 'true');", script)
        self.assertIn("state.button.setAttribute('aria-pressed', 'false');", script)

    def test_state_changes_are_announced_but_interim_text_is_not_a_live_region(self):
        """Continuously changing interim text in a live region would flood a
        screen reader; discrete state changes go through the existing one."""
        script = self.script
        self.assertIn("announce('Listening. Speak your '", script)
        self.assertIn('function setDictationInterim', script)
        interim_markup = self.html().split('data-is-dictation-interim="answer"', 1)[1].split('>', 1)[0]
        self.assertNotIn('aria-live', interim_markup)
        self.assertNotIn('role="status"', interim_markup)

    def test_stopping_reports_whether_the_answer_was_updated(self):
        script = self.script
        self.assertIn("'1 word was added to your ' + noun", script)
        self.assertIn("state.words + ' words were added to your ' + noun", script)

    def test_dictation_controls_are_real_buttons_with_accessible_names(self):
        html = self.html()
        for label in (
            'aria-label="Dictate your answer"',
            'aria-label="Dictate a custom interview question"',
            'aria-label="Dictate a follow-up question"',
            'aria-label="Dictate your answer transcript"',
        ):
            with self.subTest(label=label):
                self.assertIn(label, html)
        self.assertIn('<span data-is-mic-label>Dictate</span>', html)
        self.assertIn("text(labelNode, 'Stop dictation');", self.script)

    def test_typing_remains_first_class_when_speech_is_unavailable(self):
        html = self.html()
        self.assertIn('Dictation is optional and typing works exactly the same.', html)
        self.assertNotIn('required disabled', html)

    # -- dual-theme presentation ----------------------------------------

    def test_listening_state_uses_theme_tokens_so_both_themes_render(self):
        css = self.css
        block = css.split('.is__mic.is-listening,', 1)[1].split('}', 1)[0]
        self.assertIn('var(--is-gold)', block)
        self.assertNotIn('#fff', block)
        for token in ('var(--is-text-muted)', 'var(--is-surface-2)', 'var(--is-line)'):
            with self.subTest(token=token):
                self.assertIn(token, css.split('.is__dictation-interim {', 1)[1].split('}', 1)[0]
                              + css.split('.is__dictation-note {', 1)[1].split('}', 1)[0])

    def test_listening_is_conveyed_by_text_and_colour_not_animation_alone(self):
        css = self.css
        self.assertIn('@media (prefers-reduced-motion: reduce)', css)
        self.assertIn('.is__dictation-live', css)
        self.assertIn('function setDictationStatus', self.script)

    def test_asset_changes_reach_production_via_content_hash_versioning(self):
        # Content-hash versioning guarantees a byte change reaches production:
        # the URL token is the file's own hash, so it moves automatically.
        html = self.html()
        self.assertRegex(html, r'css/interview-studio\.css\?v=[0-9a-f]{12}')
        self.assertRegex(html, r'js/interview-studio\.js\?v=[0-9a-f]{12}')
