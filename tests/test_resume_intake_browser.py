"""Real browser -> Flask -> service journeys for private resume onboarding.

Playwright drives a real headless Chrome against a locally served Flask app.
The parser and transcription seams are in-process deterministic stubs that
record the exact bytes they received, so the browser evidence is real
(page -> event -> request -> view -> service -> seam -> response -> DOM) while
the provider boundary stays synthetic. The application's own HTTP responses are
never intercepted.

Ordinary unittest discovery may skip when Playwright or Chrome is unavailable.
This is not SQL engine proof, live identity proof or live provider proof.
"""

from __future__ import annotations

import logging
import json
import os
import threading
import unittest
from pathlib import Path

from werkzeug.serving import make_server

from app import app, limiter
from services.resume_draft_repository import (
    InMemoryCanonicalCatalog,
    InMemoryResumeDraftRepository,
)
from services.resume_draft_service import ResumeDraftService
from services.resume_guide_service import ResumeGuideService, GuideUnavailableError
from services.resume_intake_document_adapter import ResumeDocumentAdapter
from services.resume_intake_policy import selected_policy_for_tests
from services.resume_intake_repository import InMemoryResumeIntakeRepository
from services.resume_intake_service import ResumeIntakeService
from services.resume_intake_service import (
    ResumeIntakeUnavailableError, ResumeIntakeValidationError, ResumeIntakeConflictError,
)
from services.resume_intake_transcription_adapter import ResumeTranscriptionAdapter

try:
    from playwright.sync_api import sync_playwright
except ModuleNotFoundError:  # pragma: no cover - environment capability gate
    sync_playwright = None

try:
    from scripts.capture_ps_journal_j1_evidence import _resolve_chrome

    CHROME_EXECUTABLE = _resolve_chrome()
except Exception:  # pragma: no cover - optional local browser helper
    CHROME_EXECUTABLE = None


CONFIG_KEYS = (
    "TESTING",
    "PEERSLATE_ALLOW_DEV_IDENTITY",
    "PEERSLATE_DEV_USER_KEY",
    "PEERSLATE_TRUST_EASYAUTH_HEADERS",
    "PEERSLATE_RESUME_EDITOR_ENABLED",
    "PEERSLATE_RESUME_INTAKE_ENABLED",
    "PEERSLATE_RESUME_INTAKE_FIXTURE_POLICY_ENABLED",
    "RESUME_DRAFT_SERVICE",
    "RESUME_INTAKE_SERVICE",
    "RESUME_GUIDE_SERVICE",
    "PEERSLATE_RESUME_INTERVIEW_ENABLED",
    "RESUME_PRIVATE_ASSISTANCE_SERVICE",
)

TRANSCRIPT = "Browser journey transcript: I led a cross-team migration."


class _RecordingTranscriber:
    def __init__(self):
        self.calls = []

    def transcribe(self, audio_bytes, content_type, locale="en-US"):
        self.calls.append({"bytes": audio_bytes, "content_type": content_type})
        return {
            "provider_transcript": TRANSCRIPT,
            "provider_request_id": "browser-stub-1",
            "duration_seconds": 2.0,
        }


def _stop_patch(patcher):
    try:
        patcher.stop()
    except RuntimeError:
        return


def _shutdown_server(server, thread):
    try:
        if thread.is_alive():
            server.shutdown()
            thread.join(timeout=5)
    finally:
        server.server_close()


def _close_browser(browser):
    browser.close()


def _stop_playwright(runtime):
    runtime.stop()


def _remove_file(path):
    try:
        os.remove(path)
    except OSError:
        return


def install_intake_runtime_fixtures(cls):
    """Install isolated Flask/service fixtures, registering cleanup on acquire."""

    snapshot = {
        "config": {key: app.config.get(key) for key in CONFIG_KEYS},
        "limiter_enabled": limiter.enabled,
        "werkzeug_level": logging.getLogger("werkzeug").level,
    }

    def restore():
        app.config.update(snapshot["config"])
        limiter.enabled = snapshot["limiter_enabled"]
        logging.getLogger("werkzeug").setLevel(snapshot["werkzeug_level"])

    cls.addClassCleanup(restore)

    cls.catalog = InMemoryCanonicalCatalog()
    cls.draft_service = ResumeDraftService(
        repository=InMemoryResumeDraftRepository(), catalog=cls.catalog
    )
    cls.repository = InMemoryResumeIntakeRepository()
    cls.transcriber = _RecordingTranscriber()
    cls.received_documents = []

    def pipeline(user_key, import_key, content_type, admitted, *, limits, now):
        cls.received_documents.append({"content_type": content_type, "data": admitted})
        from services.my_opportunities.member_import_service import ImportStageOutcome

        return (
            "Uploaded resume text: Systems Engineer who supports requirements management.",
            "extracted", None, False,
            (ImportStageOutcome(import_key=import_key, user_key=user_key,
                                outcome="extracted", reason_code=None, occurred_at=now),),
        )

    cls.intake_service = ResumeIntakeService(
        repository=cls.repository,
        draft_service=cls.draft_service,
        document_adapter=ResumeDocumentAdapter(),
        transcription_adapter=ResumeTranscriptionAdapter(service=cls.transcriber),
        policy=selected_policy_for_tests(),
        document_pipeline=pipeline,
    )
    app.config.update(
        TESTING=True,
        PEERSLATE_ALLOW_DEV_IDENTITY=True,
        PEERSLATE_DEV_USER_KEY="intake-browser-member",
        PEERSLATE_TRUST_EASYAUTH_HEADERS=False,
        PEERSLATE_RESUME_EDITOR_ENABLED=True,
        PEERSLATE_RESUME_INTAKE_ENABLED=True,
        PEERSLATE_RESUME_INTAKE_FIXTURE_POLICY_ENABLED=True,
        RESUME_DRAFT_SERVICE=cls.draft_service,
        RESUME_INTAKE_SERVICE=cls.intake_service,
        RESUME_GUIDE_SERVICE=ResumeGuideService(repository=cls.repository),
    )
    limiter.enabled = False
    logging.getLogger("werkzeug").setLevel(logging.ERROR)

    server = make_server("127.0.0.1", 0, app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    cls.addClassCleanup(_shutdown_server, server, thread)
    thread.start()
    cls.server = server
    cls.server_thread = thread
    cls.base_url = f"http://127.0.0.1:{server.server_port}"


def start_browser(cls):
    runtime = sync_playwright().start()
    cls.addClassCleanup(_stop_playwright, runtime)
    cls.playwright = runtime
    browser = runtime.chromium.launch(
        executable_path=CHROME_EXECUTABLE,
        headless=True,
        args=["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"],
    )
    cls.addClassCleanup(_close_browser, browser)
    cls.browser = browser



@unittest.skipUnless(sync_playwright is not None and CHROME_EXECUTABLE,
                     "Playwright and Google Chrome are required for the browser proof")
class ResumeIntakeBrowserTests(unittest.TestCase):
    """Real page journeys through the adaptive guide and separate manual editor.

    Changed layout tests exercise the same service boundaries as the 18-test
    pre-change baseline, with stronger recovery and confirmation assertions.
    Providers, identity and persistence remain isolated test fixtures.
    """
    @classmethod
    def setUpClass(cls):
        install_intake_runtime_fixtures(cls)
        start_browser(cls)

    def setUp(self):
        self.owner = 'onboarding-' + self._testMethodName
        self.old = {key: app.config.get(key) for key in CONFIG_KEYS}
        self.addCleanup(app.config.update, self.old)
        app.config.update(PEERSLATE_DEV_USER_KEY=self.owner,
                          PEERSLATE_RESUME_INTERVIEW_ENABLED=False,
                          RESUME_PRIVATE_ASSISTANCE_SERVICE=None)

    def page(self, width=1440, height=1000, expect_guide=True, **options):
        context = self.browser.new_context(viewport={'width': width, 'height': height}, **options)
        self.addCleanup(context.close)
        page = context.new_page()
        page.set_default_timeout(7000)
        page.route('https://fonts.**', lambda route: route.abort())
        self.errors = []
        page.on('pageerror', lambda error: self.errors.append(str(error)))
        page.goto(self.base_url + '/app/resume')
        if not expect_guide:
            return page
        page.locator('#resume-intake[open]').wait_for()
        page.wait_for_function("() => getComputedStyle(document.querySelector('.resume-editor__panel')).filter === 'blur(8px)'")
        return page

    def input(self, page):
        if not page.locator('#resume-intake[open]').count():
            page.locator('#resume-intake-reopen').click()
        if page.locator('#resume-intake-welcome').is_visible():
            page.locator('#resume-intake-start-type').click()
        elif not page.locator('#resume-intake-input').is_visible():
            page.locator('#resume-intake-back').click()
            if page.locator('#resume-intake-welcome').is_visible():
                page.locator('#resume-intake-start-type').click()

    def manual(self, page):
        if page.locator('#resume-intake[open]').count():
            page.locator('#resume-intake-skip').click()
        details = page.locator('#resume-intake-manual-details')
        if details.get_attribute('open') is None:
            details.locator('summary').click()

    def queue(self, page, record_type, **values):
        page.locator('#resume-intake-type').select_option(record_type)
        ids = {
            'role_title': 'role-title', 'employer_name': 'employer', 'current_role': 'current-role',
            'date_precision': 'role-date-precision' if record_type == 'role' else 'education-date-precision',
            'start_date': 'role-start' if record_type == 'role' else 'education-start',
            'end_date': 'role-end' if record_type == 'role' else 'education-end',
            'name': 'skill' if record_type == 'skill' else 'credential', 'issuer': 'issuer',
            'title': 'education-title', 'institution_name': 'institution', 'education_status': 'education-status',
            'completion_status': 'credential-status', 'issue_date': 'credential-issue-date', 'wording': 'wording',
        }
        for key, value in values.items():
            field = page.locator('#resume-intake-' + ids[key])
            if field.evaluate('el => el.tagName') == 'SELECT':
                field.select_option(value)
            else:
                field.fill(value)
        page.locator('#resume-intake-add-fact').click()

    def save_manual(self, page, count):
        page.locator('#resume-intake-manual-save').click()
        page.wait_for_function("n => document.querySelector('#resume-intake-receipt').textContent.includes(n + ' saved privately')", arg=count)
        page.wait_for_function("() => !document.querySelector('#resume-intake-manual-save').disabled")

    def submit(self, page, words):
        self.input(page)
        page.locator('#resume-intake-text').fill(words)
        page.locator('#resume-intake-add').click()
        page.locator('#resume-intake-review:visible').wait_for()

    def field(self, page, name):
        return page.locator('[data-proposal-field="' + name + '"]')

    def typed_service(self, rows, service_class=ResumeIntakeService, **kwargs):
        service = service_class(repository=self.repository, draft_service=self.draft_service,
            policy=selected_policy_for_tests(), interpreter=lambda text, kind: rows, **kwargs)
        app.config['RESUME_INTAKE_SERVICE'] = service
        return service

    def role_proposal(self):
        return {'kind': 'inferred_wording', 'record_type': 'role', 'confidence': 'uncertain',
                'values': {'role_title': 'Product designer', 'employer_name': 'Northstar Studio',
                           'start_date': '2022-01-01', 'date_precision': 'year', 'current_role': True}}

    def confirm(self, page):
        item = page.locator('#resume-intake-proposals > li').element_handle()
        self.assertIsNotNone(item)
        page.get_by_role('button', name='Confirm details', exact=True).click()
        page.wait_for_function('(item) => !item.isConnected', arg=item)
        page.locator('#resume-intake-status').get_by_text('Saved privately. Sharing settings are unchanged.', exact=True).wait_for()

    def capture(self, page, name):
        directory = os.environ.get('PEERSLATE_ONBOARDING_CAPTURE_DIR')
        if directory:
            Path(directory).mkdir(parents=True, exist_ok=True)
            # Viewport captures keep the guide readable on a phone without a
            # long blank document/footer shrinking the image in chat.
            page.screenshot(path=str(Path(directory) / (name + '.png')), full_page=False)

    def test_welcome_has_benefits_equal_actions_real_document_and_no_provider_work(self):
        page = self.page()
        self.assertIn('more PeerSlate knows you', page.locator('#resume-intake-title').inner_text())
        self.assertIn('only what you choose to share', page.locator('#resume-intake-welcome').inner_text())
        buttons = [page.locator('#resume-intake-start-' + name).bounding_box() for name in ('upload', 'voice')]
        self.assertAlmostEqual(buttons[0]['width'], buttons[1]['width'], delta=1)
        self.assertEqual(page.locator('.resume-editor__panel').count(), 1)
        self.assertEqual(page.locator('.resume-editor__panel').evaluate('el => getComputedStyle(el).filter'), 'blur(8px)')
        self.assertEqual(len(self.repository.load_owner(self.owner)['submissions']), 0)
        self.assertEqual(len(self.catalog.list_items(self.owner)), 0)
        self.capture(page, 'runtime-welcome-desktop')
        self.assertEqual(self.errors, [])

    def test_grouped_correction_preserves_dates_and_reveals_only_after_confirmation(self):
        self.typed_service([self.role_proposal()])
        page = self.page()
        self.submit(page, 'I design products at Northstar Studio, starting in 2022.')
        self.assertEqual(len(self.catalog.list_items(self.owner)), 0)
        self.assertIn('2022', page.locator('.resume-intake__review-facts').inner_text())
        self.assertNotIn('2022-01-01', page.locator('.resume-intake__review-facts').inner_text())
        self.assertEqual(page.locator('.resume-editor__panel').evaluate('el => getComputedStyle(el).filter'), 'blur(8px)')
        page.get_by_role('button', name='Change something').click()
        self.field(page, 'start_date').fill('2021')
        self.capture(page, 'runtime-correction-desktop')
        self.confirm(page)
        values = self.catalog.list_items(self.owner)[0]['values']
        self.assertEqual(values['start_date'], '2021-01-01')
        self.assertEqual(values['date_precision'], 'year')
        self.assertIs(values['current_role'], True)
        page.wait_for_function("() => getComputedStyle(document.querySelector('.resume-editor__panel')).filter === 'blur(6px)'")
        page.locator('#resume-editor-lists').get_by_text('Product designer', exact=True).first.wait_for(state='attached')
        self.capture(page, 'runtime-reveal-desktop')
        self.assertEqual(self.errors, [])

    def test_manual_dates_currentness_reload_editor_and_privacy(self):
        page = self.page(); self.manual(page)
        for title, precision, start, end, current in [('Past position','year','1993','1996','false'),
                ('Unknown position','','','',''), ('Current position','month','2022-03','','true')]:
            self.queue(page, 'role', role_title=title, employer_name='Fictional Employer',
                       date_precision=precision, start_date=start, end_date=end, current_role=current)
        self.save_manual(page, 3)
        page.reload()
        self.assertFalse(page.locator('#resume-intake').is_visible())
        cards = page.locator('#resume-editor-lists article'); cards.first.wait_for()
        self.assertEqual(cards.locator('h3').all_text_contents(), ['Current position','Past position','Unknown position'])
        current = cards.filter(has=page.get_by_role('heading', name='Current position', exact=True))
        self.assertIn('2022-03 – Present', current.inner_text())
        self.assertNotIn('2022-03-01', current.inner_text())
        current.locator('summary').click()
        current.get_by_label('Date detail', exact=True).select_option('year')
        current.get_by_role('button', name='Save draft', exact=True).click()
        page.locator('#resume-editor-status').get_by_text('Draft saved', exact=False).wait_for()
        page.reload()
        workspace = self.draft_service.get_workspace(self.owner)
        values = {**workspace['items'][0]['values'], **(workspace['items'][0].get('proposed_values') or {})}
        self.assertEqual((values['start_date'], values['date_precision'], values['current_role']), ('2022-01-01','year',True))
        unknown = next(row for row in workspace['items'] if row['values']['role_title'] == 'Unknown position')
        self.assertIsNone(unknown['values']['start_date'])
        self.assertTrue(all(not row['resume_display'] and not row['visitor_ai'] for row in workspace['items']))

    def test_manual_save_never_submits_guide_words_or_attachment(self):
        page = self.page(390, 844); self.input(page)
        words = 'These are unfinished private words.'
        page.locator('#resume-intake-text').fill(words)
        page.locator('#resume-intake-file').set_input_files({'name':'draft.txt','mimeType':'text/plain','buffer':b'Unsubmitted bytes'})
        self.manual(page); self.queue(page, 'skill', name='Requirements management'); self.save_manual(page, 1)
        self.assertEqual(len(self.catalog.list_items(self.owner)), 1)
        self.assertEqual(len(self.repository.load_owner(self.owner)['proposals']), 0)
        page.locator('#resume-intake-reopen').click()
        self.assertEqual(page.locator('#resume-intake-text').input_value(), words)
        self.assertIn('draft.txt', page.locator('#resume-intake-attachments').inner_text())
        self.assertEqual(self.errors, [])

    def test_phone_narrow_keyboard_and_reduced_motion(self):
        page = self.page(390, 844, is_mobile=True, has_touch=True, reduced_motion='reduce')
        self.capture(page, 'runtime-welcome-phone')
        for width, height in [(390,844),(320,700),(390,480),(640,500)]:
            page.set_viewport_size({'width':width,'height':height})
            self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth - innerWidth'), 1)
            self.assertLessEqual(page.locator('.resume-intake__surface').evaluate('el => el.scrollWidth - el.clientWidth'), 1)
        self.input(page)
        page.locator('#resume-intake-text').fill('A long answer ' * 150)
        page.set_viewport_size({'width':390,'height':480})
        page.locator('#resume-intake-add').scroll_into_view_if_needed()
        box = page.locator('#resume-intake-add').bounding_box()
        self.assertLessEqual(box['y'] + box['height'], 480)
        self.assertGreaterEqual(box['y'], 0)
        self.assertEqual(page.locator('.resume-intake').evaluate('el => getComputedStyle(el).transitionDuration'), '0s')
        self.capture(page, 'runtime-keyboard-phone')
        page.keyboard.press('Escape')
        self.assertFalse(page.locator('#resume-intake').is_visible())
        self.assertEqual(page.evaluate('document.activeElement.id'), 'resume-intake-reopen')
        page.locator('#resume-intake-reopen').click()
        self.assertIn('long answer', page.locator('#resume-intake-text').input_value())
        for _ in range(24):
            page.keyboard.press('Tab')
            self.assertTrue(page.evaluate("document.activeElement === document.body || document.querySelector('#resume-intake').contains(document.activeElement)"))
        self.assertEqual(self.errors, [])

    def test_finish_is_explicit_private_and_manual_remains_available(self):
        page = self.page(); self.input(page)
        page.locator('#resume-intake-text').fill('Not submitted')
        page.locator('#resume-intake-input-finish').click()
        page.locator('#resume-intake-optional-next').click()
        self.assertIn('does not publish', page.locator('#resume-intake-sharing').inner_text())
        page.locator('#resume-intake-complete').click()
        page.locator('#resume-intake-finish:visible').wait_for()
        self.assertEqual(self.repository.load_owner(self.owner)['guide']['status'], 'completed')
        self.assertEqual(len(self.catalog.list_items(self.owner)), 0)
        self.assertEqual(page.locator('#resume-intake-text').input_value(), 'Not submitted')
        self.assertTrue(page.locator('#resume-intake-finish-unsent').is_visible())
        page.locator('#resume-intake-view').click()
        self.assertFalse(page.locator('#resume-intake').is_visible())
        page.reload(); self.assertFalse(page.locator('#resume-intake').is_visible())

    def test_finish_without_unsent_input_has_no_false_reminder(self):
        page = self.page(); self.input(page)
        page.locator('#resume-intake-input-finish').click()
        page.locator('#resume-intake-optional-next').click()
        page.locator('#resume-intake-complete').click()
        page.locator('#resume-intake-finish:visible').wait_for()
        self.assertFalse(page.locator('#resume-intake-finish-unsent').is_visible())
        self.assertEqual(len(self.catalog.list_items(self.owner)), 0)

    def test_proposals_preserve_approximate_and_unknown_date_precision(self):
        self.typed_service([
            {'kind': 'inferred_wording', 'record_type': 'education', 'confidence': 'uncertain',
             'values': {'title': 'Design studies', 'institution_name': 'Fictional College',
                        'education_status': 'completed', 'date_precision': 'approximate', 'end_date': '2018-06-15'}},
            {'kind': 'inferred_wording', 'record_type': 'role', 'confidence': 'uncertain',
             'values': {'role_title': 'Designer', 'employer_name': 'Fictional Studio',
                        'date_precision': 'unknown', 'start_date': '2019-02-03'}}])
        page = self.page(); self.submit(page, 'My education dates are approximate and my role date is unknown.')
        self.assertIn('Around 2018-06-15', page.locator('.resume-intake__review-facts').inner_text())
        page.get_by_role('button', name='Change something').click()
        self.assertEqual(self.field(page, 'date_precision').input_value(), 'approximate')
        self.confirm(page)
        self.assertNotIn('2019-02-03', page.locator('.resume-intake__review-facts').inner_text())
        self.assertIn('Date unknown', page.locator('.resume-intake__review-facts').inner_text())
        page.get_by_role('button', name='Change something').click()
        self.assertEqual(self.field(page, 'date_precision').locator('option[value="approximate"]').count(), 0)
        self.confirm(page)
        records = {row['record_type']: row['values'] for row in self.catalog.list_items(self.owner)}
        self.assertEqual((records['education']['date_precision'], records['education']['end_date']), ('approximate', '2018-06-15'))
        self.assertIsNone(records['education']['start_date'])
        self.assertEqual((records['role']['date_precision'], records['role']['start_date']), ('unknown', '2019-02-03'))
        self.assertEqual(self.errors, [])

    def test_impact_parent_choice_survives_back_review_and_reopen(self):
        page = self.page(); self.manual(page)
        self.queue(page, 'role', role_title='Designer', employer_name='Fictional Studio')
        self.save_manual(page, 1)
        role = self.catalog.list_items(self.owner)[0]
        from unittest.mock import patch
        create_patch = patch.object(self.catalog, 'create_private', wraps=self.catalog.create_private)
        create = create_patch.start(); self.addCleanup(create_patch.stop)
        self.typed_service([{'kind': 'inferred_wording', 'record_type': 'accomplishment', 'confidence': 'uncertain',
                            'values': {'wording': 'Simplified onboarding'}}])
        self.submit(page, 'I simplified onboarding.')
        page.get_by_role('button', name='Change something').click()
        page.locator('#resume-proposal-parent').select_option(role['record_key'])
        self.field(page, 'wording').fill('Simplified customer onboarding')
        page.locator('#resume-intake-back').click()
        page.locator('#resume-intake-review-pending').click()
        page.get_by_role('button', name='Change something').click()
        self.assertEqual(page.locator('#resume-proposal-parent').input_value(), role['record_key'])
        page.locator('#resume-intake-hide').click(); page.locator('#resume-intake-reopen').click()
        self.assertEqual(page.locator('#resume-proposal-parent').input_value(), role['record_key'])
        self.assertEqual(len(self.catalog.list_items(self.owner)), 1)
        self.confirm(page)
        impact = next(row for row in self.catalog.list_items(self.owner) if row['record_type'] == 'accomplishment')
        self.assertEqual(create.call_args.args[1]['parent_key'], role['record_key'])
        self.assertEqual(impact['values']['wording'], 'Simplified customer onboarding')
        self.assertEqual(self.errors, [])

    def test_clear_controls_never_offer_required_fields(self):
        page = self.page(); self.manual(page)
        page.locator('#resume-intake-type').select_option('role')
        fields = page.locator('#resume-intake-clears input').evaluate_all('els => els.map(el => el.value)')
        self.assertNotIn('role_title', fields); self.assertNotIn('employer_name', fields); self.assertIn('summary', fields)
        page.locator('#resume-intake-type').select_option('skill')
        self.assertEqual(page.locator('#resume-intake-clears input').evaluate_all('els => els.map(el => el.value)'), ['summary'])

    def test_lost_add_freezes_request_bytes_and_keeps_newer_typing(self):
        calls = []
        class LostOnce(ResumeIntakeService):
            def submit(inner, owner, payload, **kwargs):
                calls.append(json.loads(json.dumps(payload)))
                result = super().submit(owner, payload, **kwargs)
                if len(calls) == 1:
                    raise ResumeIntakeUnavailableError(proposed={'text': payload.get('text')})
                return result
        self.typed_service([], LostOnce)
        page = self.page(); self.input(page)
        page.locator('#resume-intake-text').fill('Recover this exact submission.')
        page.locator('#resume-intake-file').set_input_files({'name':'refused.bin','mimeType':'application/octet-stream','buffer':b'Keep bytes'})
        page.locator('#resume-intake-add').click()
        page.locator('#resume-intake-status[data-kind=error]').wait_for()
        self.assertTrue(page.get_by_role('button',name='Remove refused.bin',exact=True).is_disabled())
        newer = 'Newer words typed after the uncertain response.'
        page.locator('#resume-intake-text').fill(newer)
        page.locator('#resume-intake-add').click()
        page.wait_for_function("() => document.querySelector('#resume-intake-add-label').textContent === 'Continue'")
        self.assertEqual(calls[0], calls[1])
        self.assertEqual(len(self.repository.load_owner(self.owner)['submissions']), 1)
        self.assertEqual(page.locator('#resume-intake-text').input_value(), newer)
        self.assertFalse(page.get_by_role('button',name='Remove refused.bin',exact=True).is_disabled())
        self.assertFalse(page.locator('#resume-intake-activity').is_visible())

    def test_refused_add_releases_key_and_offline_keeps_input(self):
        calls = []
        class Refuse(ResumeIntakeService):
            def submit(inner, owner, payload, **kwargs):
                calls.append(payload['request_id'])
                if len(calls) == 1: raise ResumeIntakeValidationError('Please correct this input.')
                raise ResumeIntakeConflictError('conflict', message='This input conflicts.')
        self.typed_service([], Refuse)
        page = self.page(); self.input(page); page.locator('#resume-intake-text').fill('My input remains.')
        for message in ['Please correct this input.', 'This input conflicts.']:
            page.locator('#resume-intake-add').click()
            page.locator('#resume-intake-status').get_by_text(message,exact=True).wait_for()
        self.assertNotEqual(calls[0], calls[1])
        page.context.set_offline(True)
        page.locator('#resume-intake-add').click()
        page.locator('#resume-intake-status').get_by_text('connection dropped',exact=False).wait_for()
        self.assertEqual(page.locator('#resume-intake-text').input_value(), 'My input remains.')
        self.assertFalse(page.locator('#resume-intake-activity').is_visible())
        page.context.set_offline(False)

    def test_lost_decision_and_malformed_success_retry_exact_confirmation(self):
        calls = []
        class LostDecision(ResumeIntakeService):
            def decide(inner, owner, payload, **kwargs):
                calls.append(json.loads(json.dumps(payload)))
                result = super().decide(owner, payload, **kwargs)
                if len(calls) == 1: raise ResumeIntakeUnavailableError()
                if len(calls) == 2: return {'success': True}  # a malformed 200 is not acknowledgement
                return result
        self.typed_service([self.role_proposal()], LostDecision)
        page = self.page(); self.submit(page, 'My role source.')
        page.get_by_role('button',name='Change something').click()
        self.field(page,'start_date').fill('2021')
        page.get_by_role('button',name='Confirm details',exact=True).click()
        page.locator('#resume-intake-status[data-kind=error]').wait_for()
        self.assertTrue(self.field(page,'start_date').is_disabled())
        for attempt in range(2):
            page.get_by_role('button',name='Retry confirmation',exact=True).click()
            if attempt == 0:
                page.locator('#resume-intake-status').get_by_text('not acknowledged',exact=False).wait_for()
                self.assertEqual(page.locator('.resume-editor').evaluate("el => el.style.getPropertyValue('--resume-reveal-blur')"),'8px')
        page.locator('#resume-intake-next:visible').wait_for()
        self.assertEqual(calls[0],calls[1]); self.assertEqual(calls[1],calls[2])
        self.assertEqual(len(self.catalog.list_items(self.owner)),1)
        self.assertEqual(self.catalog.list_items(self.owner)[0]['values']['start_date'],'2021-01-01')

    def test_many_proposals_are_reviewed_one_group_at_a_time_and_discard_is_not_save(self):
        rows = [{'kind':'inferred_wording','record_type':'skill','confidence':'uncertain','values':{'name':'Strength ' + str(n)}} for n in range(3)]
        self.typed_service(rows)
        page = self.page(); self.submit(page,'Three strengths in the source.')
        self.assertEqual(page.locator('#resume-intake-proposals > li').count(),1)
        self.assertIn('3 groups',page.locator('#resume-intake-review-position').inner_text())
        page.get_by_role('button',name='Leave this out',exact=True).click()
        page.locator('#resume-intake-review-position').get_by_text('2 groups',exact=False).wait_for()
        self.assertEqual(len(self.catalog.list_items(self.owner)),0)
        self.confirm(page)
        self.assertIn('One group',page.locator('#resume-intake-review-position').inner_text())
        self.confirm(page)
        self.assertEqual(len(self.catalog.list_items(self.owner)),2)

    def test_real_file_bytes_mixed_review_failure_and_remove_preserve_other_input(self):
        self.received_documents.clear()
        page = self.page(); self.input(page)
        page.locator('#resume-intake-text').fill('My source words')
        page.locator('#resume-intake-file').set_input_files([
            {'name':'resume.txt','mimeType':'text/plain','buffer':b'Systems engineer source'},
            {'name':'refused.bin','mimeType':'application/octet-stream','buffer':b'Unrecognized bytes'},
            {'name':'empty.txt','mimeType':'text/plain','buffer':b''}])
        page.locator('#resume-intake-add').click()
        page.locator('#resume-intake-receipt').filter(has_text='2 needs your review').wait_for()
        self.assertEqual(page.locator('#resume-intake-text').input_value(),'')
        self.assertEqual(len(self.catalog.list_items(self.owner)),0)
        self.assertEqual(self.received_documents[-1]['data'], b'Systems engineer source')
        page.locator('#resume-intake-text').fill('New unsent words')
        page.get_by_role('button',name='Remove refused.bin',exact=True).click()
        self.assertIn('empty.txt',page.locator('#resume-intake-attachments').inner_text())
        self.assertEqual(page.locator('#resume-intake-text').input_value(),'New unsent words')
        page.get_by_role('button',name='Remove empty.txt',exact=True).click()
        page.locator('#resume-intake-review-pending').click()
        self.assertEqual(page.locator('#resume-intake-proposals > li').count(),1)
        self.assertEqual(self.errors,[])

    def test_slow_add_busy_status_follows_manual_escape_and_preserves_new_typing(self):
        started, release = threading.Event(), threading.Event(); self.addCleanup(release.set)
        calls = []
        class Slow(ResumeIntakeService):
            def submit(inner, owner, payload, **kwargs):
                calls.append(payload); started.set()
                if not release.wait(20): raise ResumeIntakeUnavailableError()
                return super().submit(owner,payload,**kwargs)
        self.typed_service([],Slow)
        page = self.page(390,844,reduced_motion='reduce'); self.input(page)
        page.locator('#resume-intake-text').fill('Original words')
        page.locator('#resume-intake-add').click(); self.assertTrue(started.wait(2))
        page.locator('#resume-intake-composer').evaluate("el => {el.dispatchEvent(new Event('submit',{cancelable:true}));}")
        page.locator('#resume-intake-text').fill('Original words and newer words')
        page.locator('#resume-intake-hide').click()
        activity = page.locator('#resume-intake-activity')
        self.assertTrue(activity.is_visible())
        self.assertEqual(activity.get_attribute('role'),'status')
        self.assertFalse(activity.evaluate("el => !!el.closest('[aria-busy=true]')"))
        self.assertEqual(activity.locator('.resume-intake__activity-mark').evaluate('el => getComputedStyle(el).animationName'),'none')
        activity.get_by_text('taking longer',exact=False).wait_for(timeout=12000)
        self.assertNotRegex(activity.inner_text(),r'\d+%|reasoning')
        self.assertEqual(len(calls),1)
        release.set(); page.wait_for_function("() => !document.querySelector('#resume-intake-add').disabled")
        page.locator('#resume-intake-reopen').click()
        # Returning to unfinished input is explicit even when review is ready.
        if not page.locator('#resume-intake-input').is_visible(): self.input(page)
        self.assertEqual(page.locator('#resume-intake-text').input_value(),'Original words and newer words')
        self.assertEqual(len(calls),1)

    def test_education_credential_statuses_are_member_choices_in_manual_and_review(self):
        page = self.page(); self.manual(page)
        self.queue(page,'education',title='Systems Engineering',institution_name='Example University',education_status='completed')
        self.queue(page,'credential',name='Architecture Certificate',issuer='Example Institute',completion_status='completed',issue_date='2026-09-01')
        self.save_manual(page,2)
        for record_type, name, detail, status in [('education','Program','Example College','in_progress'),('credential','Safety Credential','Example Board','planned')]:
            self.submit(page,'Source for '+record_type)
            page.locator('[data-proposal-type]').select_option(record_type)
            self.field(page,'title' if record_type=='education' else 'name').fill(name)
            self.field(page,'institution_name' if record_type=='education' else 'issuer').fill(detail)
            self.field(page,'education_status' if record_type=='education' else 'completion_status').select_option(status)
            self.confirm(page)
        records = self.catalog.list_items(self.owner)
        self.assertEqual(sum(row['record_type']=='education' for row in records),2)
        self.assertEqual(sum(row['record_type']=='credential' for row in records),2)
        self.assertTrue(all(not row['resume_display'] and not row['visitor_ai'] for row in records))

    def test_missing_or_unsupported_status_requires_choice_without_invention(self):
        self.typed_service([{'kind':'inferred_wording','record_type':'education','confidence':'uncertain',
                            'values':{'title':'My Program','institution_name':'Example College'}}])
        page = self.page(); self.submit(page,'My program source.')
        page.get_by_role('button',name='Confirm details',exact=True).click()
        page.locator('#resume-intake-status').get_by_text('education status',exact=False).wait_for()
        self.assertEqual(self.field(page,'education_status').input_value(),'')
        self.assertEqual(len(self.catalog.list_items(self.owner)),0)
        self.field(page,'education_status').select_option('planned'); self.confirm(page)
        self.assertEqual(self.catalog.list_items(self.owner)[0]['values']['education_status'],'planned')

    def test_impact_requires_owner_private_role_and_parent_refresh_after_confirmation(self):
        self.typed_service([self.role_proposal()])
        page = self.page(); self.submit(page,'My role.'); self.confirm(page)
        self.manual(page)
        self.queue(page,'accomplishment',wording='Simplified new customer onboarding')
        self.assertIn('Choose which entry',page.locator('#resume-intake-manual-status').inner_text())
        page.wait_for_function("() => document.querySelectorAll('#resume-intake-parent option').length > 1")
        page.locator('#resume-intake-parent').select_option(index=1)
        page.locator('#resume-intake-add-fact').click(); self.save_manual(page,1)
        records = self.catalog.list_items(self.owner)
        self.assertEqual(len(records),2)
        self.assertEqual(sum(row['record_type']=='accomplishment' for row in records),1)

    def test_lost_guide_completion_keeps_exact_choice_and_finish_is_acknowledged(self):
        calls=[]
        class LostGuide(ResumeGuideService):
            def set_status(inner, owner, payload, **kwargs):
                calls.append(dict(payload)); result=super().set_status(owner,payload,**kwargs)
                if len(calls)==1: raise GuideUnavailableError('The guide is unavailable.')
                return result
        app.config['RESUME_GUIDE_SERVICE']=LostGuide(repository=self.repository)
        page=self.page(); self.input(page)
        page.locator('#resume-intake-input-finish').click(); page.locator('#resume-intake-optional-next').click()
        page.locator('#resume-intake-complete').click()
        page.locator('#resume-intake-status[data-kind=error]').wait_for()
        self.assertFalse(page.locator('#resume-intake-finish').is_visible())
        page.locator('#resume-intake-complete').click(); page.locator('#resume-intake-finish:visible').wait_for()
        self.assertEqual(calls[0],calls[1]); self.assertEqual(calls[0]['status'],'completed')

    def test_contextual_question_is_explicit_revision_bound_and_never_saved(self):
        calls=[]; service=self.draft_service
        class Interview:
            def interview(inner,owner,payload):
                calls.append((owner,dict(payload)))
                if payload['expected_draft_version'] != service.get_workspace(owner)['draft_version']:
                    raise AssertionError('Stale context')
                return {'saved':False,'publishes':False,'next_question':'What changed for your customers?',
                        'response':'Let’s explore the result of your work.','candidates':[], 'confirmation_required':True,
                        'base_revision':payload['expected_draft_version']}
        app.config.update(PEERSLATE_RESUME_INTERVIEW_ENABLED=True,RESUME_PRIVATE_ASSISTANCE_SERVICE=Interview())
        self.typed_service([self.role_proposal()])
        page=self.page(); self.assertEqual(calls,[])
        self.submit(page,'My role.'); self.confirm(page); self.assertEqual(calls,[])
        page.locator('#resume-intake-next-question').click()
        page.locator('#resume-intake-question').get_by_text('What changed for your customers?',exact=True).wait_for()
        self.assertEqual(len(calls),1); self.assertEqual(calls[0][0],self.owner)
        self.assertEqual(len(self.catalog.list_items(self.owner)),1)
        page.locator('#resume-intake-skip-question').click()
        self.assertNotEqual(self.repository.load_owner(self.owner)['guide'].get('status'),'completed')

    def test_ai_unavailable_keeps_words_and_no_fake_progress(self):
        app.config.update(PEERSLATE_RESUME_INTERVIEW_ENABLED=True,RESUME_PRIVATE_ASSISTANCE_SERVICE=None)
        self.typed_service([self.role_proposal()])
        page=self.page(); self.submit(page,'My role.'); self.confirm(page)
        page.locator('#resume-intake-next-question').click()
        page.locator('#resume-intake-status').get_by_text('unavailable',exact=False).wait_for()
        page.locator('#resume-intake-text').fill('My next thought.')
        self.assertFalse(page.locator('#resume-intake-activity').is_visible())
        self.assertEqual(len(self.catalog.list_items(self.owner)),1)
        page.locator('#resume-intake-skip').click()
        self.assertFalse(page.locator('#resume-intake').is_visible())
        self.assertEqual(page.locator('#resume-intake-text').input_value(),'My next thought.')


    def recording_service(self, cls=ResumeIntakeService):
        service=cls(repository=self.repository,draft_service=self.draft_service,
                    transcription_adapter=ResumeTranscriptionAdapter(service=self.transcriber),
                    policy=selected_policy_for_tests())
        app.config['RESUME_INTAKE_SERVICE']=service
        return service

    def record(self,page):
        page.locator('#resume-intake-mic').click()
        page.wait_for_function("() => document.querySelector('#resume-intake-mic').getAttribute('aria-pressed') === 'true'")
        page.wait_for_timeout(350)  # collect a real browser fake-device audio chunk

    def test_leaving_recording_stops_tracks_and_holds_audio_until_explicit_transcribe(self):
        self.recording_service(); before=len(self.transcriber.calls)
        page=self.page(390,844); self.input(page)
        page.evaluate('''() => {
            const original = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
            navigator.mediaDevices.getUserMedia = async options => {
                const stream = await original(options); window.observedStream = stream; return stream;
            };
        }''')
        self.record(page)
        self.assertIn('after you stop',page.locator('#resume-intake-recording').inner_text())
        self.capture(page,'runtime-recording-phone')
        page.locator('#resume-intake-hide').click()
        page.wait_for_function("() => document.querySelector('#resume-intake-mic').getAttribute('aria-pressed') === 'false'")
        page.locator('#resume-intake-reopen').click()
        page.get_by_role('button',name='Transcribe recording',exact=True).wait_for()
        self.assertTrue(page.evaluate("window.observedStream.getTracks().every(track => track.readyState === 'ended')"))
        self.assertEqual(len(self.transcriber.calls),before)
        page.locator('#resume-intake-text').fill('Words typed after stopping.')
        page.get_by_role('button',name='Transcribe recording',exact=True).click()
        page.wait_for_function("text => document.querySelector('#resume-intake-text').value.includes(text)",arg=TRANSCRIPT)
        self.assertEqual(len(self.transcriber.calls),before+1)
        self.assertTrue(page.locator('#resume-intake-text').input_value().startswith('Words typed after stopping.'))
        self.assertFalse(page.locator('#resume-intake-recording').is_visible())
        self.assertEqual(len(self.catalog.list_items(self.owner)),0)
        self.assertEqual(self.errors,[])

    def test_cancel_fences_old_transcript_and_late_transcript_appends_new_words(self):
        first_started,second_started=threading.Event(),threading.Event()
        release_first,release_second=threading.Event(),threading.Event()
        self.addCleanup(release_first.set);self.addCleanup(release_second.set)
        calls=[]
        class SlowRecord(ResumeIntakeService):
            def transcribe_recording(inner,owner,upload,payload,**kwargs):
                calls.append(dict(payload)); first=len(calls)==1
                (first_started if first else second_started).set()
                if not (release_first if first else release_second).wait(20): raise ResumeIntakeUnavailableError()
                return super().transcribe_recording(owner,upload,payload,**kwargs)
        self.recording_service(SlowRecord)
        page=self.page();self.input(page);page.locator('#resume-intake-text').fill('Before recording.')
        try:
            self.record(page);page.locator('#resume-intake-mic').click();self.assertTrue(first_started.wait(2))
            page.locator('#resume-intake-cancel-recording').click()
            self.record(page);page.locator('#resume-intake-mic').click()
            page.locator('#resume-intake-text').fill('Before recording. Newer words.')
            release_first.set();self.assertTrue(second_started.wait(4))
            self.assertNotIn(TRANSCRIPT,page.locator('#resume-intake-text').input_value())
            self.assertTrue(page.locator('#resume-intake-cancel-recording').is_visible())
            release_second.set()
            page.wait_for_function("text => document.querySelector('#resume-intake-text').value.includes(text)",arg=TRANSCRIPT)
            self.assertEqual(page.locator('#resume-intake-text').input_value().count(TRANSCRIPT),1)
            self.assertTrue(page.locator('#resume-intake-text').input_value().startswith('Before recording. Newer words.'))
            self.assertFalse(page.locator('#resume-intake-activity').is_visible())
            self.assertEqual(page.locator('#resume-intake-composer').get_attribute('aria-busy'),'false')
            self.assertEqual(len(self.catalog.list_items(self.owner)),0)
        finally:
            release_first.set();release_second.set()

    def test_recording_retry_keeps_original_metadata_after_second_recording(self):
        calls=[];before=len(self.transcriber.calls)
        class LostAudio(ResumeIntakeService):
            def transcribe_recording(inner,owner,upload,payload,**kwargs):
                calls.append(dict(payload));result=super().transcribe_recording(owner,upload,payload,**kwargs)
                if len(calls)==1: raise ResumeIntakeUnavailableError()
                return result
        self.recording_service(LostAudio)
        page=self.page();self.input(page);self.record(page);page.locator('#resume-intake-mic').click()
        page.locator('#resume-intake-status[data-kind=error]').wait_for()
        self.assertFalse(page.locator('#resume-intake-activity').is_visible())
        self.record(page);page.locator('#resume-intake-mic').click()
        page.wait_for_function("text => document.querySelector('#resume-intake-text').value.includes(text)",arg=TRANSCRIPT)
        page.get_by_role('button',name='Try again',exact=True).click()
        page.wait_for_function("text => document.querySelector('#resume-intake-text').value.split(text).length === 3",arg=TRANSCRIPT)
        self.assertEqual(calls[0],calls[2]);self.assertNotEqual(calls[0]['request_id'],calls[1]['request_id'])
        self.assertEqual(len(self.transcriber.calls),before+2)
        self.assertFalse(page.locator('#resume-intake-activity').is_visible())

    def test_recording_recovery_required_is_terminal_and_retains_typing(self):
        class Recovery(ResumeIntakeService):
            def transcribe_recording(inner,owner,upload,payload,**kwargs):
                return {'success':False,'outcome':'pending','recovery_required':True,'input_preserved':True,
                        'message':'Recovery is required for this recording.'}
        self.recording_service(Recovery)
        page=self.page();self.input(page);page.locator('#resume-intake-text').fill('Keep my words')
        self.record(page);page.locator('#resume-intake-mic').click()
        page.locator('#resume-intake-status').get_by_text('Recovery is required',exact=False).wait_for()
        self.assertFalse(page.locator('#resume-intake-activity').is_visible())
        self.assertFalse(page.locator('#resume-intake-cancel-recording').is_visible())
        self.assertEqual(page.get_by_role('button',name='Try again',exact=True).count(),0)
        self.assertEqual(page.locator('#resume-intake-text').input_value(),'Keep my words')

    def test_microphone_permission_failure_and_pending_leave_preserve_manual_input(self):
        # Only browser device permission is stubbed; application HTTP is real.
        page=self.page();self.input(page)
        page.evaluate("() => { navigator.mediaDevices.getUserMedia = () => Promise.reject(new DOMException('Denied','NotAllowedError')); }")
        page.locator('#resume-intake-mic').click()
        page.locator('#resume-intake-status').get_by_text('permission was not granted',exact=False).wait_for()
        page.locator('#resume-intake-text').fill('Typing still works')
        page.evaluate("""() => {
            window.permissionResolve = null;
            window.stoppedTracks = 0;
            navigator.mediaDevices.getUserMedia = () => new Promise(resolve => window.permissionResolve = resolve);
        }""")
        page.locator('#resume-intake-mic').click();page.locator('#resume-intake-hide').click()
        page.evaluate("window.permissionResolve({getTracks: () => [{stop: () => window.stoppedTracks++}]})")
        page.wait_for_function('window.stoppedTracks === 1')
        self.assertEqual(page.locator('#resume-intake-text').input_value(),'Typing still works')
        self.assertEqual(len(self.catalog.list_items(self.owner)),0)

    def test_existing_entry_correction_preserves_unspecified_values_and_permissions(self):
        page=self.page();self.manual(page)
        self.queue(page,'role',role_title='Product designer',employer_name='Northstar Studio',date_precision='year',start_date='2021',current_role='true')
        self.save_manual(page,1)
        record=self.catalog.list_items(self.owner)[0]
        self.typed_service([{'kind':'additional_detail','record_type':'role','confidence':'certain',
                            'match_reference':record['record_key'],'values':{'summary':'I helped onboarding.'}}],
                           matching_exclusions=lambda owner: [])
        self.submit(page,'I helped onboarding.')
        self.assertIn('existing entry',page.locator('.resume-intake__proposal-source').inner_text())
        page.get_by_role('button',name='Change something').click()
        self.field(page,'summary').fill('I simplified new customer onboarding.')
        self.confirm(page)
        workspace=self.draft_service.get_workspace(self.owner)
        self.assertEqual(len(workspace['items']),1)
        item=workspace['items'][0];values={**item['values'],**(item.get('proposed_values') or {})}
        self.assertEqual(values['summary'],'I simplified new customer onboarding.')
        self.assertEqual(values['start_date'],'2021-01-01');self.assertEqual(values['date_precision'],'year');self.assertIs(values['current_role'],True)
        self.assertFalse(item['resume_display']);self.assertFalse(item['visitor_ai'])

    def test_story_destination_and_repeated_question_use_existing_controls(self):
        page=self.page();self.input(page)
        page.locator('#resume-intake-input-finish').click();page.locator('#resume-intake-add-story').click()
        self.assertFalse(page.locator('#resume-intake').is_visible())
        self.assertTrue(page.evaluate("document.querySelector('#resume-editor-story-controls').contains(document.activeElement)"))
        self.input(page)
        page.locator('#resume-intake-new-question').click()
        self.assertIn('AI guidance is unavailable',page.locator('#resume-intake-context').inner_text())
        self.assertEqual(len(self.catalog.list_items(self.owner)),0)


    def test_workspace_failure_is_not_treated_as_first_use(self):
        class Unavailable(ResumeIntakeService):
            def get_workspace(inner,owner,**kwargs): raise ResumeIntakeUnavailableError()
        self.typed_service([],Unavailable)
        page=self.page(expect_guide=False)
        page.locator('#resume-intake-reopen').wait_for()
        page.wait_for_function("() => document.querySelector('#resume-intake').getAttribute('data-screen') === 'input'")
        self.assertFalse(page.locator('#resume-intake').is_visible())
        page.locator('#resume-intake-reopen').click()
        self.assertTrue(page.locator('#resume-intake-input').is_visible())
        self.assertFalse(page.locator('#resume-intake-welcome').is_visible())
        page.locator('#resume-intake-text').fill('Words kept during an outage.')
        self.assertEqual(len(self.catalog.list_items(self.owner)),0)

    def test_corrections_survive_back_and_reopen_without_silent_save(self):
        self.typed_service([self.role_proposal()])
        page=self.page();self.submit(page,'Role source.')
        page.get_by_role('button',name='Change something').click();self.field(page,'start_date').fill('2021')
        page.locator('#resume-intake-back').click();page.locator('#resume-intake-review-pending').click()
        page.get_by_role('button',name='Change something').click()
        self.assertEqual(self.field(page,'start_date').input_value(),'2021')
        page.locator('#resume-intake-hide').click();page.locator('#resume-intake-reopen').click()
        self.assertEqual(self.field(page,'start_date').input_value(),'2021')
        self.assertEqual(len(self.catalog.list_items(self.owner)),0)
        self.confirm(page)

    def test_repeated_question_is_suppressed_in_active_flow(self):
        calls=[]
        class Interview:
            def interview(inner,owner,payload):
                calls.append(payload)
                return {'saved':False,'publishes':False,'next_question':'What outcome mattered?',
                        'response':'One useful follow-up.','base_revision':payload['expected_draft_version']}
        app.config.update(PEERSLATE_RESUME_INTERVIEW_ENABLED=True,RESUME_PRIVATE_ASSISTANCE_SERVICE=Interview())
        page=self.page();self.input(page)
        page.locator('#resume-intake-new-question').click()
        page.locator('#resume-intake-question').get_by_text('What outcome mattered?',exact=True).wait_for()
        page.locator('#resume-intake-skip-question').click();page.locator('#resume-intake-back').click()
        page.locator('#resume-intake-new-question').click()
        page.locator('#resume-intake-optional:visible').wait_for()
        self.assertIn('already covered',page.locator('#resume-intake-status').inner_text())
        self.assertEqual(len(calls),2);self.assertEqual(len(self.catalog.list_items(self.owner)),0)


    def test_uncertain_words_require_member_type_choice(self):
        page=self.page();self.submit(page,'My unclassified words.')
        self.assertEqual(page.locator('[data-proposal-type]').input_value(),'')
        page.get_by_role('button',name='Confirm details',exact=True).click()
        page.locator('#resume-intake-status').get_by_text('Choose where these words belong',exact=False).wait_for()
        self.assertEqual(len(self.catalog.list_items(self.owner)),0)
        page.locator('[data-proposal-type]').select_option('skill')
        self.field(page,'name').fill('Systems thinking');self.confirm(page)
        self.assertEqual(self.catalog.list_items(self.owner)[0]['values']['name'],'Systems thinking')



if __name__ == '__main__':
    unittest.main()
