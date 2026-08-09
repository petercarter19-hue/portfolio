"""PS-HOME-STORY-001 — three-scene homepage tests.

Pins the acceptance criteria that matter most: the shared header survives,
every CTA resolves through a real route, the scene content comes from the
approved live sources, the banned mockup content never appears, and the
old homepage remains reachable at /experience for rollback.
"""

import os
import unittest
from pathlib import Path

from app import app


class HomepageSceneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        cls.client = app.test_client()
        cls.html = cls.client.get('/').get_data(as_text=True)

    # ---- shell ----

    def test_homepage_renders(self):
        self.assertEqual(self.client.get('/').status_code, 200)

    def test_single_h1(self):
        self.assertEqual(self.html.count('<h1'), 1)

    def test_shared_global_header_has_public_destinations_and_menu(self):
        for expected in ('class="global-header"', "Pete's Slate", 'Community',
                         'Interview Studio', 'Why PeerSlate',
                         'data-platform-menu-toggle', 'Sign In'):
            self.assertIn(expected, self.html)
        self.assertNotIn('Ask Pete AI', self.html)

    def test_no_mockup_only_navigation(self):
        for banned in ('How It Works', 'Explore a Slate', 'For Teams',
                       'Pricing', 'Create My Slate'):
            self.assertNotIn(banned, self.html)

    def test_old_homepage_still_reachable_for_rollback(self):
        response = self.client.get('/experience')
        self.assertEqual(response.status_code, 200)
        self.assertIn('cinematic-home-page',
                      response.get_data(as_text=True))

    # ---- scene content ----

    def test_scene_headlines_present(self):
        self.assertIn('Say what happened.', self.html)
        self.assertIn('grounded in the real thing.', self.html)
        self.assertIn('Go beyond', self.html)
        self.assertIn('Enter once. Link everywhere. Publish deliberately.',
                      self.html)

    def test_four_act_labels_match_live_story(self):
        for label in ('This is me now', 'How I became this person',
                      'The life around the work', 'Still becoming'):
            self.assertIn(label, self.html)

    def test_live_polaroid_captions_present(self):
        self.assertIn('100 miles. 10 days. One goal.', self.html)
        self.assertIn('Places that changed me.', self.html)
        self.assertIn('Always get outside.', self.html)

    def test_banned_mockup_captions_absent(self):
        for banned in ('First marathon — 2018', 'First marathon - 2018',
                       'Bali — reset &amp; refocus', 'Bali — reset & refocus',
                       'Hawaii — perspective'):
            self.assertNotIn(banned, self.html)

    def test_future_card_uses_approved_content(self):
        self.assertIn('Systems Engineering Ph.D.', self.html)
        self.assertIn('University of South Alabama', self.html)
        self.assertIn('January 2027', self.html)
        self.assertIn('Cameo Systems Modeler', self.html)
        self.assertIn('Mentoring', self.html)

    def test_no_browser_local_board_notes(self):
        lowered = self.html.lower()
        for banned in ('grocery', 'second home', 'guitar'):
            self.assertNotIn(banned, lowered)

    def test_resume_metrics_come_from_live_source(self):
        for value in ('30+', '9 / $19.2M', '$36M+', '70%', '35%'):
            self.assertIn(value, self.html)
        self.assertIn('The Career Constellation', self.html)
        self.assertIn('Northrop Grumman', self.html)

    def test_no_fabricated_trusted_by_logos(self):
        for banned in ('Google', 'Microsoft', 'NVIDIA', 'Deloitte',
                       'amazon'):
            self.assertNotIn(banned, self.html)

    # ---- links ----

    def test_ctas_resolve_to_real_routes(self):
        # PS-COMMUNITY-AUTH-WALL-001: the working Living Stream demo is
        # retired, so the hero's capture actions lead through sign-in to the
        # real private capture experience. No homepage CTA points at the
        # retired demo or legacy Slate subviews any more.
        for retired in ('/feed-living-stream', '/the-slate/my-slate',
                        '/the-slate/daily'):
            self.assertNotIn(retired, self.html)
        # Primary CTA, mic, Private Journal card, and the week link all go
        # through sign-in.
        self.assertGreaterEqual(self.html.count('href="/auth/sign-in"'), 4)
        # The ghost button explains the product instead of opening a demo.
        self.assertIn('href="/peerslate">See how it works</a>', self.html)
        for href in ('/petec/my-story', '/petec/skills', '/petec/resume',
                     '/petec/slate-board', '/petec/projects',
                     '/interview-studio'):
            self.assertIn('href="%s' % href, self.html)
            target = href.split('#')[0].split('?')[0]
            status = self.client.get(target).status_code
            self.assertIn(status, (200, 302), target)
        # The sign-in gate answers: 302 to the provider when Easy Auth is
        # configured, or the honest "not configured yet" 503 explainer in
        # this test environment. Either way it is a real route, not a 404.
        self.assertIn(self.client.get('/auth/sign-in').status_code, (302, 503))

    def test_read_the_chapters_anchor_exists_on_story_page(self):
        self.assertIn('href="/petec/my-story#act-becoming"', self.html)
        story_html = self.client.get('/petec/my-story').get_data(as_text=True)
        self.assertIn('id="act-becoming"', story_html)

    # ---- semantics ----

    def test_polaroids_are_semantic_figures(self):
        self.assertEqual(self.html.count('hv-polaroid hv-polaroid--'), 3)
        self.assertIn('<figcaption', self.html)
        self.assertIn('Pete running a 10K race wearing bib number 4465',
                      self.html)

    def test_act_index_is_an_ordered_list(self):
        self.assertIn('<ol class="hv-acts"', self.html)


class HomepageInterviewDemoTests(unittest.TestCase):
    """PS-HOME-INTERVIEW-DEMO-001 — illustrative homepage walkthrough.

    Pins placement, the four-state server-rendered contract, the
    no-input/no-request/no-storage boundary, the two owner-required copy
    corrections, and the accessibility contract that can be verified from
    server-rendered HTML and the static JS/CSS source. See
    docs/initiatives/PS-HOME-INTERVIEW-DEMO-001/ for the full architecture.
    """

    JS_PATH = os.path.join(os.path.dirname(__file__), '..', 'static', 'js',
                            'homepage-interview-demo.js')
    CSS_PATH = os.path.join(os.path.dirname(__file__), '..', 'static', 'css',
                             'homepage-scenes.css')

    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        cls.client = app.test_client()
        cls.html = cls.client.get('/').get_data(as_text=True)
        start = cls.html.index('data-home-interview-demo')
        end = cls.html.index('class="hv-story"', start)
        cls.scene = cls.html[start:end]
        with open(cls.JS_PATH, encoding='utf-8') as f:
            cls.js = f.read()
        with open(cls.CSS_PATH, encoding='utf-8') as f:
            cls.css = f.read()

    # ---- placement and structure ----

    def test_scene_present_between_resume_and_story(self):
        resume_index = self.html.index('class="hv-resume"')
        scene_index = self.html.index('data-home-interview-demo')
        story_index = self.html.index('class="hv-story"')
        self.assertLess(resume_index, scene_index)
        self.assertLess(scene_index, story_index)

    def test_four_states_server_rendered(self):
        self.assertIn('data-int-state="1"', self.scene)
        for n in (2, 3, 4):
            marker = 'data-int-state="%d"' % n
            self.assertIn(marker, self.scene)
            idx = self.scene.index(marker)
            # the section tag carries `hidden` before its closing '>'
            tag_end = self.scene.index('>', idx)
            self.assertIn('hidden', self.scene[idx:tag_end])
        state1_idx = self.scene.index('data-int-state="1"')
        state1_tag_end = self.scene.index('>', state1_idx)
        self.assertNotIn('hidden', self.scene[state1_idx:state1_tag_end])

    def test_existing_scenes_untouched(self):
        for marker in ('class="hv-hero"', 'class="hv-resume"',
                       'class="hv-story"', 'class="hv-invite"'):
            self.assertIn(marker, self.html)

    # ---- truth boundary ----

    def test_no_answer_input_in_scene(self):
        for banned in ('<form', '<textarea', '<input'):
            self.assertNotIn(banned, self.scene)

    def test_no_media_apis_in_scene_script(self):
        for banned in ('getUserMedia', 'mediaDevices', 'MediaRecorder',
                       'SpeechRecognition', 'AudioContext'):
            self.assertNotIn(banned, self.js)

    def test_no_network_apis_in_scene_script(self):
        for banned in ('fetch(', 'XMLHttpRequest', 'sendBeacon',
                       'WebSocket', 'EventSource'):
            self.assertNotIn(banned, self.js)

    def test_no_storage_apis_in_scene_script(self):
        for banned in ('localStorage', 'sessionStorage', 'indexedDB',
                       'document.cookie', 'caches.'):
            self.assertNotIn(banned, self.js)

    def test_truth_bar_server_rendered(self):
        for label in ('Fictional example', 'No visitor input',
                      'No AI request', 'No answer or practice data stored'):
            self.assertIn(label, self.scene)

    def test_no_pete_attribution_in_walkthrough(self):
        self.assertEqual(self.scene.count('Pete'), 1)
        self.assertIn('not Pete&rsquo;s and not the visitor&rsquo;s',
                      self.scene)

    def test_final_cta_resolves_to_interview_studio(self):
        self.assertIn('Practice this question in Interview Studio',
                      self.scene)
        self.assertIn('Open Interview Studio', self.scene)
        self.assertGreaterEqual(self.scene.count('href="/interview-studio"'), 2)
        self.assertEqual(self.client.get('/interview-studio').status_code, 200)

    # ---- copy corrections and banned language ----

    def test_no_internal_design_rationale_published_to_visitors(self):
        """The homepage must not publish our own design notes as visitor copy.

        This scene used to carry a sequence note explaining, to us, where the
        scene sits in the page order ("Placed after Living Résumé ... so the
        homepage moves from capture, to presentation, to practice, to what
        comes next"), and an eyebrow that named the internal artefact
        ("Homepage scene · Interview Studio") rather than the product. Both
        were removed on 2026-08-03 (site visual parity audit, finding 8).
        The earlier banned wording of that same note is still checked, so the
        original correction's intent survives its deletion.
        """
        self.assertNotIn('capture, to proof, to practice', self.html)
        self.assertNotIn('capture, to presentation, to practice', self.html)
        self.assertNotIn('Placed after Living', self.html)
        self.assertNotIn('hv-int-sequence-note', self.html)
        self.assertNotIn('Homepage scene', self.html)
        # The eyebrow still names the product, exactly as the sibling scenes
        # ("Living Résumé", "My Story + Slate") do.
        self.assertIn(
            '<p class="hv-eyebrow"><span aria-hidden="true">&#10022;</span>'
            ' Interview Studio</p>',
            self.scene)

    def test_retry_does_not_invent_outcomes(self):
        self.assertNotIn('repeatable review process', self.html)
        self.assertIn(
            'That alignment kept the transition on schedule and avoided '
            'a delivery slip.', self.scene)

    def test_no_private_history_language(self):
        for banned in ('Use my history', 'your history', 'signed in',
                       'saved to your account'):
            self.assertNotIn(banned, self.scene)

    # ---- interaction and accessibility contract ----

    def test_buttons_have_explicit_type(self):
        import re
        buttons = re.findall(r'<button\b[^>]*>', self.scene)
        self.assertGreater(len(buttons), 0)
        for button in buttons:
            self.assertIn('type="button"', button)

    def test_step_rail_semantics(self):
        self.assertEqual(self.scene.count('data-int-step="'), 4)
        self.assertEqual(self.scene.count('aria-current="step"'), 1)
        idx = self.scene.index('aria-current="step"')
        self.assertIn('data-int-step="1"', self.scene[max(0, idx - 200):idx])

    def test_live_region_present_and_empty(self):
        self.assertEqual(self.scene.count('data-int-live'), 1)
        idx = self.scene.index('role="status"')
        tag_end = self.scene.index('</p>', idx)
        self.assertNotIn('Step', self.scene[idx:tag_end])

    def test_state_headings_are_focus_targets(self):
        # each of the four modal steps leads with an <h3 class="hv-int-state__title"
        # tabindex="-1"> so a keyboard/step transition can move focus to it.
        self.assertEqual(self.scene.count('hv-int-state__title'), 4)
        self.assertEqual(self.scene.count('tabindex="-1"'), 4)

    def test_walkthrough_uses_a_modal_dialog(self):
        # The pop-out walkthrough is a labelled modal dialog that ships
        # `hidden` (closed) in server HTML — JS opens it.
        self.assertIn('data-int-overlay', self.scene)
        ov_idx = self.scene.index('data-int-overlay')
        ov_tag_end = self.scene.index('>', ov_idx)
        self.assertIn('hidden', self.scene[ov_idx:ov_tag_end])
        self.assertIn('role="dialog"', self.scene)
        self.assertIn('aria-modal="true"', self.scene)
        self.assertIn('aria-labelledby="hv-int-modal-title"', self.scene)

    def test_open_trigger_is_a_js_gated_button(self):
        idx = self.scene.index('data-int-open')
        tag = self.scene[self.scene.rfind('<', 0, idx):self.scene.index('>', idx) + 1]
        self.assertTrue(tag.startswith('<button'), tag)
        self.assertIn('type="button"', tag)
        self.assertIn('hv-int-controls', tag)

    def test_poster_carries_question_and_truth_without_js(self):
        # The always-visible poster (before the modal) holds the question and
        # the truth bar, so a no-JS visitor still sees the essentials.
        poster = self.scene[self.scene.index('hv-int-poster'):
                            self.scene.index('data-int-overlay')]
        self.assertIn('Tell me about a time you led a team through a '
                      'major change', poster)
        for label in ('Fictional example', 'No visitor input',
                      'No AI request', 'No answer or practice data stored'):
            self.assertIn(label, poster)

    def test_written_practice_replaces_voice_first_switch(self):
        self.assertIn('Write your answer in your own words', self.scene)
        self.assertIn('Dictation is optional in the real Studio', self.scene)
        for banned in ('Voice first', 'Voice is front and center',
                       'Illustrative voice transcript', 'data-int-method'):
            self.assertNotIn(banned, self.scene)

    def test_processing_status_matches_released_studio(self):
        for label in ('Answer received', 'Checking the question rubric',
                      'Preparing bottom-line feedback',
                      'The submitted text is attached to this coaching request.',
                      'Reviewing relevance, structure, specificity, and result.',
                      'Feedback appears only when the complete review is ready.'):
            self.assertIn(label, self.scene)
        self.assertEqual(self.scene.count('hv-int-status-row'), 3)
        self.assertEqual(self.scene.count('hv-int-status-row is-done'), 1)
        self.assertEqual(self.scene.count('hv-int-status-row is-current'), 1)

    def test_bottom_line_score_is_truthfully_labelled(self):
        self.assertIn('Bottom line first.', self.scene)
        self.assertIn('aria-label="Overall interview score: 72 out of 100"',
                      self.scene)
        self.assertIn('Practice signal &mdash; not an employer prediction',
                      self.scene)

    def test_modal_theme_proxy_is_dormant_while_dark_theme_is_unavailable(self):
        self.assertNotIn('data-theme-toggle-proxy', self.scene)

        source = Path(
            'templates/partials/homepage/_interview_demo_scene.html'
        ).read_text(encoding='utf-8')
        self.assertEqual(source.count('data-theme-toggle-proxy'), 1)
        self.assertIn('role="switch"', source)
        self.assertIn('hv-int-theme-label">Theme</span>', source)
        self.assertIn('theme-toggle__track', source)
        self.assertIn('theme-toggle__thumb', source)

    def test_modal_truth_is_accessible(self):
        start = self.scene.index('class="hv-int-modal__truth"')
        end = self.scene.index('>', start)
        self.assertNotIn('aria-hidden', self.scene[start:end])

    def test_controller_restores_only_inertness_it_added(self):
        self.assertIn("element.setAttribute('inert', '')", self.js)
        self.assertIn("element.removeAttribute('inert')", self.js)
        self.assertIn('inertedElements.push(element)', self.js)

    def test_cinematic_dark_tokens_are_demo_scoped(self):
        self.assertIn('body[data-theme="dark"] .hv-int-portal', self.css)
        for value in ('#03101d', '#071a2b', '#091827', '#0c2235',
                      '#f4efe6', '#f4bd58', '#f1bd5c'):
            self.assertIn(value, self.css)

    def test_nojs_fallback_present(self):
        # Without JS the modal can't open, so the poster keeps a normal anchor
        # to the real Studio (class hv-int-nojs, revealed when JS is absent).
        idx = self.scene.index('hv-int-nojs')
        tag = self.scene[self.scene.rfind('<', 0, idx):self.scene.index('>', idx) + 1]
        self.assertTrue(tag.startswith('<a'), tag)
        self.assertIn('href="/interview-studio"', tag)
        self.assertIn('Open Interview Studio', self.scene)

    def test_reduced_motion_css_covers_scene(self):
        self.assertIn('@media (prefers-reduced-motion: reduce)', self.css)
        rm_idx = self.css.index('@media (prefers-reduced-motion: reduce)')
        rm_block_end = self.css.index('}\n}', rm_idx)
        self.assertIn('.home-v3 *', self.css[rm_idx:rm_block_end])
        # the scene relies on that shared blanket rule; confirm it appears
        # before the scene's own CSS section in the file.
        scene_idx = self.css.index('PS-HOME-INTERVIEW-DEMO-001')
        self.assertLess(rm_idx, scene_idx)

    def test_no_fixed_viewport_heights_in_scene_css(self):
        # The design source squeezed the whole scene into one viewport with
        # fixed `height: calc(100vh - …)` + `overflow: hidden`. That anti-
        # pattern stays banned. The modal, however, legitimately caps its OWN
        # height to the viewport with `max-height` and scrolls internally —
        # standard dialog behavior — so max-height viewport units are allowed.
        import re
        scene_css = self.css[self.css.index('PS-HOME-INTERVIEW-DEMO-001'):]
        # Strip the modal's legitimate `max-height:` viewport caps, then any
        # remaining viewport-height unit is a fixed lock (the squeeze).
        guard = re.sub(r'max-height:[^;]*;', '', scene_css)
        for banned in ('100vh', '100svh'):
            self.assertNotIn(banned, guard)
        # the scene container itself must not lock to the viewport or clip
        scene_block = scene_css[scene_css.index('.home-v3 .hv-interview {'):]
        scene_block = scene_block[:scene_block.index('}')]
        self.assertNotIn('100vh', scene_block)
        self.assertNotIn('overflow: hidden', scene_block)
        # the modal caps with max-height (not a fixed height)
        modal_block = scene_css[scene_css.index('.home-v3 .hv-int-modal {'):]
        modal_block = modal_block[:modal_block.index('}')]
        self.assertIn('max-height', modal_block)

    def test_display_overrides_do_not_fight_the_hidden_attribute(self):
        # Regression test: `.home-v3 .hv-int-explain { display: flex; ... }`
        # is more specific than the UA `[hidden] { display: none }` rule, so
        # the server-rendered `hidden` attribute on the inactive method
        # panel was silently ignored until a matching `[hidden]` override
        # was added. Any scene selector that both (a) sets `display:` and
        # (b) targets an element the template ships with a static `hidden`
        # attribute must have a same-selector `[hidden] { display: none }`
        # companion rule. Several such elements exist: the method-explanation
        # panel (display:flex), the modal overlay (display:grid), and the
        # Back/Next/Finish controls (shared .hv-btn display:inline-flex) — all
        # of which JS toggles via the `hidden` attribute.
        for selector in ('.hv-int-overlay[hidden]', '.hv-int-back[hidden]',
                         '.hv-int-next[hidden]',
                         '.hv-int-finish[hidden]'):
            self.assertIn(selector, self.css)
            idx = self.css.index(selector)
            line_end = self.css.index('}', idx)
            self.assertIn('display: none', self.css[idx:line_end])


if __name__ == '__main__':
    unittest.main()
