"""Real browser -> Flask -> service journeys for private resume onboarding.

Playwright drives a real headless Chrome against a locally served Flask app.
The parser and transcription seams are in-process deterministic stubs that
record the exact bytes they received, so the browser evidence is real
(page -> event -> request -> view -> service -> seam -> response -> DOM) while
the provider boundary stays synthetic. Recovery fault cases first execute the
actual backend request, then simulate a lost response before its browser acknowledgement.

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
from services.resume_onboarding_document_reader import inventory_source

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
            for _ in range(12):
                if page.locator('#resume-intake-input').is_visible():break
                if page.locator('#resume-intake-welcome').is_visible():
                    page.locator('#resume-intake-start-type').click();break
                page.locator('#resume-intake-back').click()

    def finish_input(self, page):
        # An untouched first input has no question/section bookkeeping.
        # Once an answer is started the member can leave it unsent.
        button=page.locator('#resume-intake-input-finish')
        if not button.is_visible():page.locator('#resume-intake-text').fill('An unfinished answer kept for later.')
        button.click()

    def manual(self, page):
        if page.locator('#resume-intake[open]').count():
            page.locator('#resume-intake-skip').click()
            page.locator('#resume-intake').wait_for(state='hidden')
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

    def conversation_service(self, service, behavior):
        from services.resume_intake_runtime import PrivateResumeAssistanceService
        from tests.test_resume_onboarding_conversation import ContextPorts
        from itsdangerous import URLSafeTimedSerializer
        ports = ContextPorts(self.catalog)
        assistance = PrivateResumeAssistanceService(draft_service=self.draft_service,
            catalog=ports, policy_repository=ports, providers={'interview': lambda **kw: behavior(kw['context'])},
            signer=URLSafeTimedSerializer('browser-conversation-fixture-' * 3),
            limits={'maximum_task_bytes': 20000, 'maximum_input_bytes': 65536,
                'maximum_output_bytes': 100000, 'maximum_field_bytes': 8000, 'proof_max_age_seconds': 900})
        app.config.update(PEERSLATE_RESUME_INTERVIEW_ENABLED=True,
            RESUME_PRIVATE_ASSISTANCE_SERVICE=assistance, RESUME_INTAKE_SERVICE=service)
        return assistance

    def pending_conversation_page(self, service, behavior, *, mobile=False):
        from tests.test_my_data_intake_ai import add_request
        service.submit(self.owner, add_request(text='Original private role source.'))
        self.conversation_service(service, behavior)
        return self.page(390,844) if mobile else self.page()

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
            # Viewport captures keep the guide readable on a phone.
            page.screenshot(path=str(Path(directory) / (name.removesuffix('.png') + '.png')), full_page=False)

    def conflicting_composer(self, *, missing=False):
        from uuid import uuid4
        page = self.page(); self.input(page)
        with page.expect_response(lambda response: response.url.endswith('/draft') and response.request.method == 'PUT' and response.status == 200):
            page.locator('#resume-intake-text').fill('Local first copy')
        service = app.config['RESUME_INTAKE_SERVICE']; first = service.get_draft(self.owner)['draft']
        if missing: service.discard_draft(self.owner, {'request_id':str(uuid4()), 'expected_version':first['version']})
        else: service.save_draft(self.owner, {'request_id':str(uuid4()), 'expected_version':first['version'], 'text':'Other device current copy'})
        page.locator('#resume-intake-text').fill('Local newer words')
        page.locator('#resume-intake-draft-recovery').wait_for(state='visible')
        page.wait_for_function("() => !document.querySelector('#resume-intake-draft-recovery-keep').disabled")
        return page, service, first

    def undispatched_conflicting_turn(self):
        calls, puts = [], []
        service = self.typed_service([])
        self.conversation_service(service, lambda context: calls.append(context) or
            {'response': 'Your question is kept private.', 'next_question': '', 'operations': []})
        first, page = self.page(), self.page()
        self.input(first)
        with first.expect_response(lambda response: response.url.endswith('/draft') and
                response.request.method == 'PUT' and response.status == 200):
            first.locator('#resume-intake-text').fill('Device A saved wording with an important qualifier.')
        self.input(page)
        page.on('request', lambda request: puts.append(request.post_data_json)
            if request.url.endswith('/draft') and request.method == 'PUT' else None)
        page.locator('#resume-intake-text').fill('Device B local words which I may choose not to keep.')
        page.locator('#resume-intake-add').click()
        page.wait_for_function("() => !document.querySelector('#resume-intake-add').disabled && "
            "!document.querySelector('#resume-intake-draft-recovery-use').disabled")
        self.assertEqual(calls, [])
        self.assertIsNotNone(puts[-1]['guide_state']['pending_conversation'])
        return page, service, calls, puts

    def test_saved_copy_abandons_only_undispatched_turn_and_retains_returnable_words(self):
        page, service, calls, puts = self.undispatched_conflicting_turn()
        abandoned = puts[-1]['guide_state']['pending_conversation']['request_id']
        before = service.get_draft(self.owner)['draft']
        page.locator('#resume-intake-draft-recovery-use').click()
        page.locator('#resume-intake-status').get_by_text('Using the saved draft.', exact=False).wait_for()
        self.assertEqual(page.locator('#resume-intake-text').input_value(), before['text'])
        self.assertEqual(service.get_draft(self.owner)['draft'], before)
        self.assertEqual(calls, [])
        self.assertEqual(page.locator('#resume-intake-add-label').text_content(), 'Continue')
        self.assertEqual(page.locator('#resume-intake-draft-recovery-earlier').text_content(),
            'Device B local words which I may choose not to keep.')
        self.capture(page, 'r13-saved-choice-retains-undispatched-words')
        page.locator('#resume-intake-draft-recovery-held > summary').click()
        page.locator('#resume-intake-draft-recovery-return').click()
        page.wait_for_function("() => !document.querySelector('#resume-intake-draft-recovery-keep').disabled")
        self.assertEqual(page.locator('#resume-intake-text').input_value(),
            'Device B local words which I may choose not to keep.')
        self.assertEqual(service.get_draft(self.owner)['draft'], before)
        page.locator('#resume-intake-draft-recovery-keep').click()
        page.locator('#resume-intake-status').get_by_text('Your page copy is saved privately.', exact=True).wait_for()
        page.locator('#resume-intake-add').click()
        page.wait_for_function("() => !document.querySelector('#resume-intake-add').disabled && "
            "document.querySelector('#resume-intake-add-label').textContent === 'Continue'")
        self.assertEqual(len(calls), 1)
        keys = [p['guide_state']['pending_conversation']['request_id'] for p in puts
            if p['guide_state']['pending_conversation']]
        self.assertNotEqual(keys[-1], abandoned)
        self.assertEqual(' '.join(unit['text'] for unit in calls[0]['current_turn']['units']),
            'Device B local words which I may choose not to keep.')
        self.assertEqual(self.catalog.list_items(self.owner), [])
        self.assertEqual(self.errors, [])

    def test_saved_choice_rechecks_submission_and_navigation_after_delayed_read(self):
        page, service, calls, puts = self.undispatched_conflicting_turn()
        before = service.get_draft(self.owner)['draft']
        held = []
        def hold(route):
            if route.request.method == 'GET': held.append((route, route.fetch())); return
            route.continue_()
        page.route('**/api/resume-intake/me/draft', hold)
        page.locator('#resume-intake-draft-recovery-use').click()
        for _ in range(100):
            if held: break
            page.wait_for_timeout(20)
        self.assertEqual(len(held), 1)
        # A new explicit submission can return to the same visible state and
        # immutable preparation; it still supersedes the earlier choice.
        page.locator('#resume-intake-add').click()
        page.wait_for_function("() => !document.querySelector('#resume-intake-add').disabled")
        route, response = held.pop(); route.fulfill(response=response)
        page.locator('#resume-intake-draft-recovery-message').get_by_text('Review the copies again', exact=False).wait_for()
        self.assertEqual(page.locator('#resume-intake-text').input_value(),
            'Device B local words which I may choose not to keep.')
        self.assertEqual(calls, []); self.assertEqual(service.get_draft(self.owner)['draft'], before)
        page.locator('#resume-intake-draft-recovery-use').click()
        for _ in range(100):
            if held: break
            page.wait_for_timeout(20)
        self.assertEqual(len(held), 1)
        # Leave and return during the read, preserving the member's navigation.
        page.locator('#resume-intake-skip').click()
        page.locator('#resume-intake-reopen').click()
        route, response = held.pop(); route.fulfill(response=response)
        page.locator('#resume-intake-draft-recovery-message').get_by_text('Review the copies again', exact=False).wait_for()
        self.assertEqual(page.locator('#resume-intake-text').input_value(),
            'Device B local words which I may choose not to keep.')
        self.assertEqual(calls, []); self.assertEqual(service.get_draft(self.owner)['draft'], before)
        page.unroute('**/api/resume-intake/me/draft', hold)
        page.locator('#resume-intake-draft-recovery-use').click()
        page.locator('#resume-intake-status').get_by_text('Using the saved draft.', exact=False).wait_for()
        self.assertEqual(self.errors, [])

    def test_failed_saved_copy_reads_are_unknown_until_fresh_read_confirms_presence_or_absence(self):
        from uuid import uuid4
        original_owner = self.owner
        for failure in ('503', 'network'):
            with self.subTest(failure=failure):
                self.owner = original_owner + '-' + failure
                app.config['PEERSLATE_DEV_USER_KEY'] = self.owner
                page = self.page(); self.input(page)
                with page.expect_response(lambda response: response.url.endswith('/draft') and
                        response.request.method == 'PUT' and response.status == 200):
                    page.locator('#resume-intake-text').fill('This device first copy')
                service = app.config['RESUME_INTAKE_SERVICE']; current = service.get_draft(self.owner)['draft']
                service.save_draft(self.owner, {'request_id': str(uuid4()), 'expected_version': current['version'],
                    'text': 'The saved copy still exists'})
                puts = []
                def unavailable(route):
                    if route.request.method == 'GET':
                        if failure == '503': route.fulfill(status=503, content_type='application/json', body='{"success":false}')
                        else: route.abort()
                    else: puts.append(route.request.post_data_json); route.continue_()
                page.route('**/api/resume-intake/me/draft', unavailable)
                page.locator('#resume-intake-text').fill('This device current words')
                page.locator('#resume-intake-draft-recovery').wait_for(state='visible')
                page.wait_for_function("() => !document.querySelector('#resume-intake-draft-recovery-keep').disabled")
                message = page.locator('#resume-intake-draft-recovery-message').inner_text()
                self.assertIn('unavailable', message)
                self.assertNotIn('gone', message); self.assertNotIn('new draft', message)
                self.assertEqual(page.locator('#resume-intake-draft-recovery-keep').inner_text(), 'Retry reading the saved draft')
                self.assertTrue(page.locator('#resume-intake-draft-recovery-use').is_disabled())
                page.locator('#resume-intake-draft-recovery-keep').click()
                page.wait_for_function("() => !document.querySelector('#resume-intake-draft-recovery-keep').disabled")
                self.assertEqual(len(puts), 1)
                self.assertEqual(service.get_draft(self.owner)['draft']['text'], 'The saved copy still exists')
                self.assertEqual(page.locator('#resume-intake-text').input_value(), 'This device current words')
                self.capture(page, 'r14-unknown-' + failure)
                page.unroute('**/api/resume-intake/me/draft', unavailable)
                if failure == '503':
                    before = service.get_draft(self.owner)['draft']
                    page.locator('#resume-intake-draft-recovery-keep').click()
                    page.locator('#resume-intake-draft-recovery-message').get_by_text('Review the copies again', exact=False).wait_for()
                    self.assertEqual(service.get_draft(self.owner)['draft'], before)
                    page.locator('#resume-intake-draft-recovery-use').click()
                    page.locator('#resume-intake-status').get_by_text('Using the saved draft.', exact=False).wait_for()
                    self.assertEqual(page.locator('#resume-intake-text').input_value(), before['text'])
                    self.assertEqual(service.get_draft(self.owner)['draft'], before)
                    self.assertEqual(page.locator('#resume-intake-draft-recovery-earlier').text_content(), 'This device current words')
                    self.assertEqual(self.errors, [])
                    continue
                # A successful null read, rather than an outage, establishes absence.
                current = service.get_draft(self.owner)['draft']
                service.discard_draft(self.owner, {'request_id': str(uuid4()), 'expected_version': current['version']})
                page.locator('#resume-intake-draft-recovery-keep').click()
                page.locator('#resume-intake-draft-recovery-message').get_by_text('Review the copies again', exact=False).wait_for()
                self.assertIn('No saved draft remains.', page.locator('#resume-intake-draft-recovery-saved').text_content())
                self.assertIsNone(service.get_draft(self.owner)['draft'])
                page.locator('#resume-intake-draft-recovery-keep').click()
                page.locator('#resume-intake-status').get_by_text('Your page copy is saved privately.', exact=True).wait_for()
                self.assertEqual(service.get_draft(self.owner)['draft']['text'], 'This device current words')
                self.assertEqual(self.errors, [])

    def test_delayed_saved_choice_cannot_replace_new_unknown_manual_submission(self):
        page, service, first = self.conflicting_composer()
        self.manual(page); self.queue(page, 'skill', name='A manually queued skill')
        self.input(page)
        before = service.get_draft(self.owner)['draft']
        held, adds = [], []
        def hold(route):
            if route.request.method == 'GET': held.append((route, route.fetch())); return
            route.continue_()
        def lose(route):
            adds.append(route.request.post_data)
            response = route.fetch()
            self.assertEqual(response.status, 200)
            route.fulfill(status=503, content_type='application/json', body='{"message":"Synthetic lost manual acknowledgement"}')
        page.route('**/api/resume-intake/me/draft', hold)
        page.route('**/api/resume-intake/me/submissions', lose)
        page.locator('#resume-intake-draft-recovery-use').click()
        for _ in range(100):
            if held: break
            page.wait_for_timeout(20)
        self.assertEqual(len(held), 1)
        self.manual(page); page.locator('#resume-intake-manual-save').click()
        page.locator('#resume-intake-manual-status').get_by_text('Synthetic lost manual acknowledgement', exact=False).wait_for()
        route, response = held.pop(); route.fulfill(response=response)
        page.locator('#resume-intake-manual-status').get_by_text('Recover the unfinished operation', exact=False).wait_for()
        self.assertEqual(page.locator('#resume-intake-text').input_value(), 'Local newer words')
        self.assertEqual(service.get_draft(self.owner)['draft'], before)
        self.assertEqual(len(adds), 1)
        self.assertEqual(len(self.catalog.list_items(self.owner)), 1)
        page.unroute('**/api/resume-intake/me/submissions', lose)
        # Explicitly recover the existing manual request; it must not duplicate
        # the canonical item or submit the unrelated guide words.
        page.locator('#resume-intake-manual-save').click()
        page.wait_for_function("() => !document.querySelector('#resume-intake-manual-save').disabled")
        self.assertEqual(len(self.catalog.list_items(self.owner)), 1)
        self.assertEqual(page.locator('#resume-intake-text').input_value(), 'Local newer words')
        self.assertEqual(self.errors, [])

    def test_dispatched_lost_turn_cannot_be_replaced_and_replays_exactly_after_explicit_draft_choice(self):
        from uuid import uuid4
        for reload_pending in (False, True):
            with self.subTest(reload_pending=reload_pending):
                self.owner = 'lost-turn-' + self._testMethodName + str(reload_pending)
                app.config['PEERSLATE_DEV_USER_KEY'] = self.owner
                calls, attempts = [], []
                service = self.typed_service([])
                self.conversation_service(service, lambda context: calls.append(context) or
                    {'response': 'The private turn completed.', 'next_question': '', 'operations': []})
                page = self.page(); self.input(page)
                def lose_once(route):
                    attempts.append(route.request.post_data_json)
                    response = route.fetch()
                    if len(attempts) == 1:
                        self.assertEqual(response.status, 200)
                        route.fulfill(status=503, content_type='application/json', body='{"message":"Synthetic lost turn reply"}')
                    else: route.fulfill(response=response)
                page.route('**/api/resume-interview/me/turn', lose_once)
                page.locator('#resume-intake-text').fill('A qualified turn: I was not their line manager.')
                page.locator('#resume-intake-add').click()
                page.locator('#resume-intake-status').get_by_text('Synthetic lost turn reply', exact=False).wait_for()
                page.wait_for_function("() => !document.querySelector('#resume-intake-add').disabled")
                if reload_pending:
                    # The immutable descriptor is already saved before dispatch;
                    # after reload its outcome must be treated conservatively.
                    page.reload(); page.locator('#resume-intake-input:visible').wait_for()
                    page.wait_for_function("() => document.querySelector('#resume-intake-text').value.includes('qualified turn')")
                current = service.get_draft(self.owner)['draft']
                service.save_draft(self.owner, {'request_id': str(uuid4()), 'expected_version': current['version'],
                    'text': 'Other device wording remains authoritative until a choice'})
                page.locator('#resume-intake-text').fill('Newer local words must also survive.')
                page.locator('#resume-intake-draft-recovery').wait_for(state='visible')
                page.wait_for_function("() => !document.querySelector('#resume-intake-draft-recovery-use').disabled")
                page.locator('#resume-intake-draft-recovery-use').click()
                page.locator('#resume-intake-status').get_by_text('Recover the unfinished operation', exact=False).wait_for()
                self.assertEqual(service.get_draft(self.owner)['draft']['text'],
                    'Other device wording remains authoritative until a choice')
                self.assertEqual(page.locator('#resume-intake-text').input_value(), 'Newer local words must also survive.')
                self.assertEqual(len(calls), 1); self.assertEqual(len(attempts), 1)
                page.locator('#resume-intake-draft-recovery-keep').click()
                page.locator('#resume-intake-status').get_by_text('Your page copy is saved privately.', exact=True).wait_for()
                page.locator('#resume-intake-add').click()
                page.wait_for_function("() => !document.querySelector('#resume-intake-add').disabled && "
                    "document.querySelector('#resume-intake-add-label').textContent === 'Continue'")
                self.assertEqual(len(attempts), 2); self.assertEqual(attempts[0], attempts[1])
                self.assertEqual(len(calls), 1)
                self.assertEqual(page.locator('#resume-intake-text').input_value(), 'Newer local words must also survive.')
                self.assertEqual(self.catalog.list_items(self.owner), [])
                self.assertEqual(self.errors, [])

    def test_changed_composer_explicit_fresh_choice_and_second_race_conflict(self):
        from uuid import uuid4
        page, service, first = self.conflicting_composer()
        self.assertEqual(page.locator('#resume-intake-text').input_value(), 'Local newer words')
        self.assertEqual(page.locator('#resume-intake-draft-recovery-saved').text_content(), 'Other device current copy')
        self.capture(page,'ci-draft-conflict-choice')
        page.set_viewport_size({'width':320,'height':900})
        self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth'),320)
        attempts = []
        def race(route):
            if route.request.method == 'PUT':
                attempts.append(route.request.post_data_json)
                if len(attempts) == 1:
                    current = service.get_draft(self.owner)['draft']
                    service.save_draft(self.owner, {'request_id':str(uuid4()), 'expected_version':current['version'], 'text':'Another race won'})
            route.continue_()
        page.route('**/api/resume-intake/me/draft', race)
        page.locator('#resume-intake-draft-recovery-keep').click()
        page.wait_for_function("() => document.querySelector('#resume-intake-draft-recovery-saved').textContent === 'Another race won'")
        self.assertEqual(len(attempts),1)
        self.assertEqual(page.locator('#resume-intake-text').input_value(),'Local newer words')
        page.locator('#resume-intake-text').fill('Local latest words after race')
        page.locator('#resume-intake-draft-recovery-keep').click()
        page.locator('#resume-intake-status').get_by_text('Your page copy is saved privately.',exact=True).wait_for()
        self.assertEqual(len(attempts),2); self.assertNotEqual(attempts[0]['request_id'],attempts[1]['request_id'])
        self.assertGreater(attempts[1]['expected_version'],attempts[0]['expected_version'])
        self.assertEqual(service.get_draft(self.owner)['draft']['text'],'Local latest words after race')
        self.assertEqual(page.locator('#resume-intake-draft-recovery-earlier').text_content(),'Another race won')
        self.capture(page,'ci-draft-changed-recovered'); self.assertEqual(self.errors,[])

    def test_missing_composer_explicit_recreate_preserves_monotonic_fence(self):
        page, service, first = self.conflicting_composer(missing=True)
        self.assertTrue(page.locator('#resume-intake-draft-recovery-use').is_disabled())
        self.assertIsNone(service.get_draft(self.owner)['draft'])
        page.locator('#resume-intake-draft-recovery-keep').click()
        page.locator('#resume-intake-status').get_by_text('Your page copy is saved privately.',exact=True).wait_for()
        current = service.get_draft(self.owner)['draft']
        self.assertGreater(current['version'],first['version']);self.assertEqual(current['text'],'Local newer words')
        self.capture(page,'ci-draft-missing-recreated'); self.assertEqual(self.errors,[])

    def test_draft_choice_delayed_read_keeps_latest_words_and_requires_new_review(self):
        from uuid import uuid4
        page, service, first = self.conflicting_composer()
        held = []
        def hold(route):
            if route.request.method == 'GET': held.append((route,route.fetch())); return
            route.continue_()
        page.route('**/api/resume-intake/me/draft',hold)
        page.locator('#resume-intake-draft-recovery-use').click()
        for _ in range(100):
            if held: break
            page.wait_for_timeout(20)
        self.assertEqual(len(held),1)
        page.locator('#resume-intake-text').fill('Typed while recovery read was delayed')
        held[0][0].fulfill(response=held[0][1]);page.unroute('**/api/resume-intake/me/draft',hold)
        page.locator('#resume-intake-draft-recovery-message').get_by_text('Review the copies again',exact=False).wait_for()
        self.assertEqual(page.locator('#resume-intake-text').input_value(),'Typed while recovery read was delayed')
        self.assertEqual(service.get_draft(self.owner)['draft']['text'],'Other device current copy')
        page.locator('#resume-intake-draft-recovery-use').click()
        page.locator('#resume-intake-status').get_by_text('Using the saved draft.',exact=False).wait_for()
        self.assertEqual(page.locator('#resume-intake-text').input_value(),'Other device current copy')
        self.assertEqual(page.locator('#resume-intake-draft-recovery-earlier').text_content(),'Typed while recovery read was delayed')
        page.locator('#resume-intake-draft-recovery-held > summary').click()
        page.locator('#resume-intake-draft-recovery-return').click()
        page.wait_for_function("() => !document.querySelector('#resume-intake-draft-recovery-keep').disabled")
        self.assertEqual(page.locator('#resume-intake-text').input_value(),'Typed while recovery read was delayed')
        self.assertEqual(service.get_draft(self.owner)['draft']['text'],'Other device current copy')
        page.locator('#resume-intake-draft-recovery-keep').click()
        page.locator('#resume-intake-status').get_by_text('Your page copy is saved privately.',exact=True).wait_for()
        page.reload();page.locator('#resume-intake[open]').wait_for()
        page.wait_for_function("() => document.querySelector('#resume-intake-text').value === 'Typed while recovery read was delayed'")
        self.assertEqual(page.locator('#resume-intake-text').input_value(),'Typed while recovery read was delayed')
        self.assertEqual(self.errors,[])

    def shared_projection(self, *, media=False):
        from tests.mvp1_acceptance_support import SharedMvp1Fixture
        shared = SharedMvp1Fixture()
        keys = ('RESUME_PUBLICATION_SERVICE', 'PEERSLATE_RESUME_PUBLICATION_ENABLED',
                'ENTRY_POLICY_SERVICE', 'PEERSLATE_RESUME_MEDIA_ENABLED', 'RESUME_MEDIA_SERVICE')
        old = {key: app.config.get(key) for key in keys}
        self.addCleanup(app.config.update, old)
        self.catalog = shared.canonical; self.draft_service = shared.draft
        app.config.update(RESUME_DRAFT_SERVICE=shared.draft, ENTRY_POLICY_SERVICE=shared.policy,
            RESUME_PUBLICATION_SERVICE=shared.publication, PEERSLATE_RESUME_PUBLICATION_ENABLED=True,
            PEERSLATE_RESUME_MEDIA_ENABLED=media, RESUME_MEDIA_SERVICE=shared.media if media else None)
        self.typed_service([])
        return shared

    def seed_story(self, shared):
        from uuid import uuid4
        return shared.draft.commit(self.owner, {'type': 'create_private_item',
            'request_id': str(uuid4()), 'record_key': str(uuid4()), 'record_type': 'knowledge',
            'values': {'title': 'A quiet craft', 'wording': 'I enjoy woodworking and informal mentoring.',
                       'classification': 'personal'}})['item']['record_key']

    def unfinished_impact(self, *, media=False):
        from tests.test_my_data_intake_ai import add_request
        shared = self.shared_projection(media=media)
        keys = []
        for title in ('Engineer', 'Designer'):
            saved = app.config['RESUME_INTAKE_SERVICE'].submit(self.owner, add_request(items=[{
                'client_key': title, 'record_type': 'role', 'values': {
                    'role_title': title, 'employer_name': 'Example Labs',
                    'summary': 'Original qualified wording.', 'date_precision': 'unknown',
                    'current_role': True}, 'explicit_clears': []}]))
            keys.append(saved['results'][0]['record_key'])
        story = self.seed_story(shared)
        if media: shared.seed_photo(self.owner)
        page = self.page(expect_guide=False); page.locator('#resume-intake[open]').wait_for()
        self.input(page); page.locator('#resume-intake-text').fill('Keep this unsubmitted guide answer.')
        self.manual(page)
        page.locator('#resume-intake-type').select_option('accomplishment')
        page.locator('#resume-intake-wording').fill('Built a prototype; result not independently verified.')
        page.locator('#resume-intake-parent').select_option(keys[0])
        return shared, page, keys, story

    def assert_unfinished_impact(self, page, parent):
        self.assertEqual(page.locator('#resume-intake-parent').input_value(), parent)
        self.assertEqual(page.locator('#resume-intake-wording').input_value(),
                         'Built a prototype; result not independently verified.')
        self.assertEqual(page.locator('#resume-intake-text').input_value(),
                         'Keep this unsubmitted guide answer.')
        self.assertEqual(page.locator('#resume-intake-queued > li').count(), 0)

    def test_pending_impact_parent_survives_story_manual_and_media_refreshes(self):
        shared, page, keys, story = self.unfinished_impact(media=True)
        page.locator('#resume-story-choice').select_option(story)
        page.locator('#resume-story-select').click()
        page.wait_for_function("() => document.querySelector('#resume-intake-document-content').textContent.includes('A quiet craft')")
        self.assert_unfinished_impact(page, keys[0])
        card = page.locator('.resume-editor__card').filter(has=page.get_by_role('heading', name='Engineer', exact=True))
        card.locator('summary').click()
        card.locator('textarea[name="summary"]').fill('Manual revision; result not independently verified.')
        card.get_by_role('button', name='Save draft', exact=True).click()
        page.wait_for_function("() => document.querySelector('#resume-intake-document-content').textContent.includes('Manual revision;')")
        self.assert_unfinished_impact(page, keys[0])
        page.locator('#resume-media-photos > li').first.get_by_role('button', name='Use for My Story banner', exact=True).click()
        page.locator('#resume-media-preview-placement').click(); page.locator('#resume-media-add').click()
        page.wait_for_function("() => document.querySelector('#resume-intake-document-content .resume-publication__crop--story_banner img')")
        self.assert_unfinished_impact(page, keys[0])
        page.locator('#resume-media-change-photos').click()
        page.locator('#resume-media-slot-story_banner-remove').click()
        page.wait_for_function("() => !document.querySelector('#resume-intake-document-content .resume-publication__crop--story_banner img') && document.querySelector('#resume-intake-document-content .resume-publication--public')")
        self.assert_unfinished_impact(page, keys[0])
        page.locator('#resume-story-choice').select_option(''); page.locator('#resume-story-select').click()
        page.wait_for_function("() => !document.querySelector('#resume-intake-document-content').textContent.includes('A quiet craft') && document.querySelector('#resume-intake-document').getAttribute('aria-busy') === 'false'")
        self.assert_unfinished_impact(page, keys[0])
        self.assertFalse(any(row['record_type'] == 'accomplishment' for row in shared.canonical.list_items(self.owner)))
        self.capture(page, 'r12-impact-parent-preserved')
        self.assertEqual(self.errors, [])

    def test_media_editor_refresh_preserves_crop_caption_and_newer_choice(self):
        shared, page, keys, story = self.unfinished_impact(media=True)
        second = shared.seed_photo(self.owner, color=(130, 40, 80))
        page.locator('#resume-story-choice').select_option(story); page.locator('#resume-story-select').click()
        page.wait_for_function("() => document.querySelector('#resume-intake-document-content').textContent.includes('A quiet craft')")
        page.locator('#resume-media-photos > li').first.get_by_role('button', name='Use for My Story banner', exact=True).click()
        page.locator('#resume-media-caption').fill('My unfinished photo caption.')
        page.locator('#resume-media-preview-placement').click()
        page.locator('#resume-media-crop-story_banner').click()
        page.locator('#resume-media-crop-story_banner-x').fill('0.13')
        # A real manual commit must not overwrite either unsent media field.
        card = page.locator('.resume-editor__card').filter(has=page.get_by_role('heading', name='Engineer', exact=True))
        card.locator('summary').click(); card.locator('textarea[name="summary"]').fill('A separately saved manual revision.')
        card.get_by_role('button', name='Save draft', exact=True).click()
        page.wait_for_function("() => document.querySelector('#resume-intake-document-content').textContent.includes('A separately saved manual revision.')")
        page.wait_for_timeout(75)
        self.assertEqual(page.locator('#resume-media-caption').input_value(), 'My unfinished photo caption.')
        self.assertEqual(page.locator('#resume-media-crop-story_banner-x').input_value(), '0.13')
        self.assert_unfinished_impact(page, keys[0])
        held = []
        def hold_first(route):
            if not held: held.append((route, route.fetch())); return
            route.continue_()
        workspace = page.locator('#resume-media').get_attribute('data-media-workspace-url')
        page.route('**' + workspace, hold_first)
        # The notification/read seam is held after a saved editor change. Then
        # a later explicit photo choice owns a newer workspace generation.
        page.evaluate("document.dispatchEvent(new Event('resume-private-draft-changed'))")
        for _ in range(100):
            if held: break
            page.wait_for_timeout(20)
        self.assertEqual(len(held), 1)
        page.locator('#resume-media-preview-back').click()
        chosen = page.locator('#resume-media-photos > li[data-source-id="' + second.source_id + '"]')
        chosen.get_by_role('button', name='Use for My Story banner', exact=True).click()
        page.wait_for_function("key => document.querySelector('#resume-media-photos > li[data-source-id=\"' + key + '\"]').getAttribute('data-selected') === 'true'", arg=second.source_id)
        held[0][0].fulfill(response=held[0][1]); page.wait_for_timeout(75)
        self.assertEqual(chosen.get_attribute('data-selected'), 'true')
        self.assertEqual(page.locator('#resume-media-caption').input_value(), 'My unfinished photo caption.')
        self.assert_unfinished_impact(page, keys[0])
        page.locator('#resume-media-preview-placement').click(); page.locator('#resume-media-add').click()
        page.locator('#resume-media-status').get_by_text('Added 1 photo', exact=False).wait_for()
        saved = shared.media.workspace(owner_id=self.owner)['slots']['story_banner']
        self.assertEqual(saved['asset_id'], second.source_id)
        self.assertEqual(saved['caption'], 'My unfinished photo caption.')
        self.assertEqual(self.errors, [])

    def test_media_genuine_concurrent_conflict_does_not_replay_and_keeps_pending_inputs(self):
        from uuid import uuid4
        shared, page, keys, story = self.unfinished_impact(media=True)
        page.locator('#resume-story-choice').select_option(story); page.locator('#resume-story-select').click()
        page.wait_for_function("() => document.querySelector('#resume-intake-document-content').textContent.includes('A quiet craft')")
        photo = page.locator('#resume-media-photos > li').first
        photo.get_by_role('button', name='Use for My Story banner', exact=True).click()
        page.locator('#resume-media-caption').fill('My reviewed caption remains unsent.')
        page.locator('#resume-media-preview-placement').click()
        seen = []
        def concurrent_change(route):
            command = json.loads(route.request.post_data)
            # Another accepted canonical operation advances the actual shared
            # draft after this Add was constructed, before it reaches the server.
            target = shared.canonical.get_item(self.owner, keys[1])
            shared.draft.commit(self.owner, {'type': 'save_item', 'request_id': str(uuid4()),
                'record_key': keys[1], 'record_type': 'role',
                'expected_draft_version': shared.draft.get_workspace(self.owner)['draft_version'],
                'expected_content_token': target['content_token'], 'expected_access_revision': target['access_revision'],
                'values': {'summary': 'An actual concurrent text-draft revision.'}})
            response = route.fetch()
            seen.append({'command': command, 'status': response.status, 'payload': response.json()})
            route.fulfill(response=response)
        commands = page.locator('#resume-media').get_attribute('data-media-commands-url')
        page.route('**' + commands, concurrent_change)
        page.locator('#resume-media-add').click()
        page.locator('#resume-media-status[data-kind="error"]').wait_for()
        page.wait_for_timeout(100)
        self.assertEqual(len(seen), 1)
        self.assertEqual(seen[0]['status'], 409)
        self.assertTrue(seen[0]['payload'].get('message'))
        self.assertIsNone(shared.media.workspace(owner_id=self.owner)['slots']['story_banner'])
        self.assertEqual(page.locator('#resume-media-caption').input_value(), 'My reviewed caption remains unsent.')
        self.assert_unfinished_impact(page, keys[0])
        self.assertIn('Not added yet', page.locator('#resume-media-preview-count').inner_text())
        page.unroute('**' + commands, concurrent_change)
        # Recovery is a fresh explicit choice and Add; the refused mutation is
        # never automatically retried with a changed version or request body.
        page.locator('#resume-media-preview-back').click()
        photo.get_by_role('button', name='Use for My Story banner', exact=True).click()
        page.locator('#resume-media-preview-placement').click(); page.locator('#resume-media-add').click()
        page.locator('#resume-media-status').get_by_text('Added 1 photo', exact=False).wait_for()
        self.assertEqual(shared.media.workspace(owner_id=self.owner)['slots']['story_banner']['caption'],
                         'My reviewed caption remains unsent.')
        self.assert_unfinished_impact(page, keys[0])
        # The text editor had a different baseline because of that concurrent
        # revision. A media receipt must not silently realign it across the gap.
        editor_commands = page.locator('#resume-editor-lists').get_attribute('data-commands-url')
        page.locator('#resume-story-choice').select_option('')
        with page.expect_response(lambda response: response.url.endswith(editor_commands) and response.request.method == 'POST') as observed:
            page.locator('#resume-story-select').click()
        self.assertEqual(observed.value.status, 409)
        self.assertEqual(shared.draft.get_workspace(self.owner)['story_entry_key'], story)
        self.assert_unfinished_impact(page, keys[0])
        self.assertEqual(self.errors, [])

    def test_pending_impact_respects_latest_choice_and_newest_catalog_response(self):
        shared, page, keys, story = self.unfinished_impact()
        held = []
        def hold(route):
            response = route.fetch(); payload = response.json()
            if not held:
                # An older catalog snapshot where Engineer was unavailable.
                for item in payload['items']:
                    if item['record_key'] == keys[0]: item['editable'] = False
            held.append((route, response, payload))
        workspace = page.locator('#resume-editor-lists').get_attribute('data-workspace-url')
        page.route('**' + workspace, hold)
        # Isolate delayed catalog delivery from the editor's own workspace read.
        # Actual successful command triggers are exercised in the preceding test.
        page.evaluate("document.dispatchEvent(new Event('resume-private-draft-changed'))")
        for _ in range(100):
            if held: break
            page.wait_for_timeout(20)
        self.assertEqual(len(held), 1)
        page.locator('#resume-intake-parent').select_option(keys[1])
        page.evaluate("document.dispatchEvent(new Event('resume-private-draft-changed'))")
        for _ in range(100):
            if len(held) == 2: break
            page.wait_for_timeout(20)
        self.assertEqual(len(held), 2)
        held[1][0].fulfill(response=held[1][1], json=held[1][2]); page.wait_for_timeout(75)
        self.assert_unfinished_impact(page, keys[1])
        page.locator('#resume-intake-parent').select_option(keys[0])
        held[0][0].fulfill(response=held[0][1], json=held[0][2]); page.wait_for_timeout(75)
        self.assert_unfinished_impact(page, keys[0])
        self.assertEqual(page.locator('#resume-intake-parent option').count(), 3)
        self.assertEqual(self.errors, [])

    def test_pending_impact_catalog_outage_recovers_and_removed_parent_requires_choice(self):
        from uuid import uuid4
        shared, page, keys, story = self.unfinished_impact()
        workspace = page.locator('#resume-editor-lists').get_attribute('data-workspace-url')
        fail = lambda route: route.fulfill(status=503, content_type='application/json', body='{"success":false}')
        page.route('**' + workspace, fail)
        page.evaluate("document.dispatchEvent(new Event('resume-private-draft-changed'))")
        page.locator('#resume-intake-manual-status').get_by_text('Roles are unavailable', exact=False).wait_for()
        self.assert_unfinished_impact(page, keys[0])
        self.assertTrue(page.locator('#resume-intake-parent').is_disabled())
        page.locator('#resume-intake-add-fact').click()
        self.assertEqual(page.locator('#resume-intake-queued > li').count(), 0)
        page.unroute('**' + workspace, fail)
        page.locator('#resume-intake-type').select_option('role')
        page.locator('#resume-intake-type').select_option('accomplishment')
        page.wait_for_function("() => !document.querySelector('#resume-intake-parent').disabled")
        self.assert_unfinished_impact(page, keys[0])
        row = next(row for row in shared.policy.list_entries(self.owner)['entries'] if row['entry_key'] == keys[0])
        shared.policy.commit(self.owner, {'type': 'delete', 'request_id': str(uuid4()), 'entry_key': keys[0],
            'expected_content_version': row['content_version'], 'expected_access_revision': row['access_revision'],
            'dependent_keys': []})
        page.locator('#resume-story-choice').select_option(story); page.locator('#resume-story-select').click()
        page.locator('#resume-intake-manual-status').get_by_text('no longer available', exact=False).wait_for()
        self.assert_unfinished_impact(page, '')
        self.assertEqual(page.locator('#resume-intake-parent option[value="' + keys[0] + '"]').count(), 0)
        page.locator('#resume-intake-add-fact').click()
        self.assertEqual(page.locator('#resume-intake-queued > li').count(), 0)
        # A different eligible role requires the member's explicit choice.
        page.locator('#resume-intake-parent').select_option(keys[1])
        page.locator('#resume-intake-add-fact').click(); self.save_manual(page, 1)
        child = next(row for row in shared.policy.list_entries(self.owner)['entries'] if row['canonical_type'] == 'achievement')
        self.assertEqual(child['parent_key'], keys[1])
        self.assertEqual(child['values']['wording'], 'Built a prototype; result not independently verified.')
        self.assertEqual(page.locator('#resume-intake-text').input_value(), 'Keep this unsubmitted guide answer.')
        self.assertEqual(self.errors, [])

    def test_story_invitation_precedes_confirmation_and_decline_survives_reentry_without_ai(self):
        from tests.test_resume_onboarding_conversation import operation
        shared = self.shared_projection(); service = self.typed_service([]); calls = []
        question = 'What do you enjoy about helping someone learn woodworking?'
        def behavior(context):
            calls.append(context)
            return {'response': 'Review your optional Story.', 'next_question': question, 'operations': [
                operation(context, op='add_content', record_type='knowledge', values={
                    'title': 'Woodworking', 'classification': 'personal'}, section='My Story')]}
        self.conversation_service(service, behavior)
        page = self.page(); self.submit(page, 'I enjoy woodworking and informal mentoring.')
        self.assertTrue(page.locator('[data-optional-invitation]').is_visible())
        self.assertIn(question, page.locator('[data-optional-invitation]').inner_text())
        self.assertTrue(page.get_by_role('button', name='Confirm details', exact=True).is_visible())
        self.assertEqual(shared.policy.list_entries(self.owner)['entries'], [])
        with page.expect_response(lambda response: response.request.method == 'PUT'
                and response.url.endswith('/draft') and question in (response.request.post_data or '')):
            page.get_by_role('button', name='Keep these details', exact=True).click()
        page.wait_for_function("() => !document.querySelector('[data-optional-invitation]')")
        page.reload()
        page.wait_for_function("() => !document.querySelector('[data-optional-invitation]') && document.querySelector('#resume-intake-review').offsetParent !== null")
        self.assertEqual(page.locator('[data-optional-invitation]').count(), 0)
        self.confirm(page)
        self.assertTrue(page.locator('#resume-intake-optional').is_visible())
        entry = shared.policy.list_entries(self.owner)['entries'][0]
        self.assertEqual(entry['values']['wording'], 'I enjoy woodworking and informal mentoring.')
        self.assertEqual(len(calls), 1); self.assertEqual(self.errors, [])

    def _stop_exchange_fixture(self):
        from uuid import uuid4
        from tests.test_resume_onboarding_conversation import operation
        from tests.test_my_data_intake_ai import add_request
        shared = self.shared_projection(); story = self.seed_story(shared)
        service = self.typed_service([]); calls, action = [], []
        def behavior(context):
            calls.append(context)
            return {'response': 'Your earlier details are kept.', 'next_question': '', 'operations': [action[0](context)]}
        assistance = self.conversation_service(service, behavior)
        role = service.submit(self.owner, add_request(items=[{'client_key': 'seed', 'record_type': 'role',
            'values': {'role_title': 'Engineer', 'employer_name': 'Example Labs',
                'summary': 'Keep my contribution.\nRetain this exact limitation.'},
            'explicit_clears': []}]))['results'][0]['record_key']
        def turn(statement, ref, produce):
            action[:] = [produce]
            return service.converse(self.owner, {'request_id': str(uuid4()),
                'expected_draft_version': self.draft_service.get_workspace(self.owner)['draft_version'],
                'statement': statement, 'selected_target': ref, 'source_keys': []}, assistance=assistance)['proposals'][0]
        excluded = turn('Exclude the second bullet.', 'record:' + role, lambda ctx: operation(ctx, ref='record:' + role,
            bullets=[{'action': 'exclude', 'field': 'summary', 'index': 1,
                'expected_text': 'Retain this exact limitation.', 'replacement': None}]))
        service.decide(self.owner, {'request_id': str(uuid4()), 'proposal_key': excluded['proposal_key'], 'decision': 'accept'})
        row = service.get_workspace(self.owner)['resume_recoverable_details'][0]
        restoration = service.review_excluded_details(self.owner, {'request_id': str(uuid4()),
            'recovery_key': row['recovery_key'], 'recovery_token': row['recovery_token']})['proposals'][0]
        ordinary = turn('Add that I enjoy learning techniques.', 'record:' + story, lambda ctx: operation(ctx,
            ref='record:' + story, record_type='knowledge', values={'wording': 'I enjoy sketches and learning techniques.'}, section='My Story'))
        def stop(ctx):
            control = operation(ctx, op='skip_topic'); control['source_refs'] = []
            return control
        action[:] = [stop]
        return service, calls, action, ordinary, restoration

    def test_stop_correction_preserves_restoration_and_releases_target_after_reload(self):
        from tests.test_resume_onboarding_conversation import operation
        service, calls, action, ordinary, restoration = self._stop_exchange_fixture()
        pending = service.get_workspace(self.owner)['pending_proposals']
        draft = self.draft_service.get_workspace(self.owner)
        page = self.page(expect_guide=False)
        page.locator('#resume-intake[open]').wait_for()
        if not page.locator('#resume-intake[open]').count(): page.locator('#resume-intake-reopen').click()
        page.locator('[data-suggestion-key="' + ordinary['proposal_key'] + '"]').click()
        page.get_by_role('button', name='Change something', exact=True).click()
        page.locator('#resume-intake-text').fill("Don't worry about it.")
        with page.expect_response(lambda response: response.request.method == 'PUT' and response.url.endswith('/draft')
                and response.request.post_data_json['guide_state']['correction_target_key'] is None
                and response.request.post_data_json['guide_state']['pending_conversation'] is None):
            page.locator('#resume-intake-add').click()
        self.assertEqual(service.get_workspace(self.owner)['pending_proposals'], pending)
        self.assertEqual(self.draft_service.get_workspace(self.owner), draft)
        self.assertEqual(len(calls), 3)
        self.assertEqual(calls[-1]['selected_target'], 'proposal:' + ordinary['proposal_key'])
        self.assertIsNone(service.get_draft(self.owner)['draft']['guide_state']['correction_target_key'])
        page.reload()
        page.locator('#resume-intake-text').wait_for(state='visible')
        self.assertEqual(page.locator('#resume-intake-question').inner_text(), 'What would you like to add or change?')
        action[:] = [lambda ctx: {**operation(ctx, op='clarify'), 'source_refs': []}]
        page.locator('#resume-intake-text').fill('Where can I add another detail?')
        with page.expect_response(lambda response: response.request.method == 'POST' and response.url.endswith('/api/resume-interview/me/turn')):
            page.locator('#resume-intake-add').click()
        self.assertIsNone(calls[-1]['selected_target'])
        self.assertEqual(service.get_workspace(self.owner)['pending_proposals'], pending)
        page.wait_for_function("() => !document.querySelector('#resume-intake-add').disabled")
        page.locator('#resume-intake-review-pending').click()
        page.locator('[data-suggestion-key="' + restoration['proposal_key'] + '"]').click()
        self.assertFalse(page.get_by_role('button', name='Change something', exact=True).is_visible())
        self.confirm(page)
        page.locator('[data-suggestion-key="' + ordinary['proposal_key'] + '"]').click()
        self.confirm(page)
        self.assertEqual(service.get_workspace(self.owner)['pending_proposals'], [])
        self.assertEqual(len(calls), 4); self.assertEqual(self.errors, [])

    def test_lost_stop_response_replays_once_and_preserves_newer_words_without_target(self):
        service, calls, _, ordinary, _ = self._stop_exchange_fixture()
        pending = service.get_workspace(self.owner)['pending_proposals']
        page = self.page(expect_guide=False)
        page.locator('#resume-intake[open]').wait_for()
        if not page.locator('#resume-intake[open]').count(): page.locator('#resume-intake-reopen').click()
        page.locator('[data-suggestion-key="' + ordinary['proposal_key'] + '"]').click()
        page.get_by_role('button', name='Change something', exact=True).click()
        commands = []
        def lost(route):
            commands.append(route.request.post_data_json)
            response = route.fetch()
            if len(commands) == 1: route.abort()
            else: route.fulfill(response=response)
        page.route('**/api/resume-interview/me/turn', lost)
        page.locator('#resume-intake-text').fill("Don't worry about it.")
        page.locator('#resume-intake-add').click()
        page.locator('#resume-intake-status[data-kind=error]').wait_for()
        newer = 'Newer unrelated words typed while recovering the response.'
        page.locator('#resume-intake-text').fill(newer)
        with page.expect_response(lambda response: response.request.method == 'PUT' and response.url.endswith('/draft')
                and response.request.post_data_json['guide_state']['correction_target_key'] is None
                and response.request.post_data_json['text'] == newer):
            page.locator('#resume-intake-add').click()
        self.assertEqual(commands[0], commands[1])
        self.assertEqual(len(calls), 3)
        self.assertEqual(page.locator('#resume-intake-text').input_value(), newer)
        self.assertEqual(service.get_workspace(self.owner)['pending_proposals'], pending)
        self.assertIsNone(service.get_draft(self.owner)['draft']['guide_state']['correction_target_key'])
        page.reload(); page.locator('#resume-intake-text').wait_for(state='visible')
        self.assertEqual(page.locator('#resume-intake-text').input_value(), newer)
        self.assertEqual(page.locator('#resume-intake-question').inner_text(), 'What would you like to add or change?')
        self.assertEqual(self.errors, [])

    def test_old_stop_retry_preserves_new_correction_target_prompt_and_reload(self):
        from uuid import uuid4
        from tests.test_resume_onboarding_conversation import operation
        from tests.test_my_data_intake_ai import add_request
        service, calls, action, ordinary, _ = self._stop_exchange_fixture()
        role = service.submit(self.owner, add_request(items=[{'client_key': 'other-role', 'record_type': 'role',
            'values': {'role_title': 'Designer', 'employer_name': 'Other Company'},
            'explicit_clears': []}]))['results'][0]['record_key']
        action[:] = [lambda ctx: operation(ctx, ref='record:' + role, values={'location_text': 'Chicago'})]
        second = service.converse(self.owner, {'request_id': str(uuid4()),
            'expected_draft_version': self.draft_service.get_workspace(self.owner)['draft_version'],
            'statement': 'Change the other role location to Chicago.', 'selected_target': 'record:' + role,
            'source_keys': []}, assistance=app.config['RESUME_PRIVATE_ASSISTANCE_SERVICE'])['proposals'][0]
        action[:] = [lambda ctx: {**operation(ctx, op='skip_topic'), 'source_refs': []}]
        pending = service.get_workspace(self.owner)['pending_proposals']
        page = self.page(expect_guide=False)
        page.locator('#resume-intake[open]').wait_for()
        if not page.locator('#resume-intake[open]').count(): page.locator('#resume-intake-reopen').click()
        page.locator('[data-suggestion-key="' + ordinary['proposal_key'] + '"]').click()
        page.get_by_role('button', name='Change something', exact=True).click()
        commands = []
        def lost(route):
            commands.append(route.request.post_data_json)
            response = route.fetch()
            if len(commands) == 1: route.abort()
            else: route.fulfill(response=response)
        page.route('**/api/resume-interview/me/turn', lost)
        page.locator('#resume-intake-text').fill("Don't worry about it.")
        page.locator('#resume-intake-add').click()
        page.locator('#resume-intake-status[data-kind=error]').wait_for()
        page.wait_for_function("() => !document.querySelector('#resume-intake-add').disabled")
        page.locator('#resume-intake-review-pending').click()
        page.locator('[data-suggestion-key="' + second['proposal_key'] + '"]').click()
        page.get_by_role('button', name='Change something', exact=True).click()
        prompt = page.locator('#resume-intake-question').inner_text()
        context = page.locator('#resume-intake-context').inner_text()
        newer = 'For this different role, keep Chicago and change the employer to Other Studio.'
        page.locator('#resume-intake-text').fill(newer)
        with page.expect_response(lambda response: response.request.method == 'PUT' and response.url.endswith('/draft')
                and response.request.post_data_json['guide_state']['pending_conversation'] is None):
            page.locator('#resume-intake-add').click()
        state = service.get_draft(self.owner)['draft']['guide_state']
        self.assertEqual(commands[0], commands[1]); self.assertEqual(len(calls), 4)
        self.assertEqual(state['correction_target_key'], second['proposal_key'])
        self.assertEqual(page.locator('#resume-intake-question').inner_text(), prompt)
        self.assertEqual(page.locator('#resume-intake-context').inner_text(), context)
        self.assertEqual(page.locator('#resume-intake-text').input_value(), newer)
        self.assertEqual(service.get_workspace(self.owner)['pending_proposals'], pending)
        page.reload(); page.locator('#resume-intake-text').wait_for(state='visible')
        self.assertEqual(service.get_draft(self.owner)['draft']['guide_state']['correction_target_key'], second['proposal_key'])
        self.assertEqual(page.locator('#resume-intake-question').inner_text(), prompt)
        self.assertEqual(page.locator('#resume-intake-text').input_value(), newer)
        action[:] = [lambda ctx: {**operation(ctx, op='clarify'), 'source_refs': []}]
        with page.expect_response(lambda response: response.request.method == 'POST' and response.url.endswith('/api/resume-interview/me/turn')):
            page.locator('#resume-intake-add').click()
        self.assertEqual(calls[-1]['selected_target'], 'proposal:' + second['proposal_key'])
        self.assertEqual(len(calls), 5); self.assertEqual(self.errors, [])

    def test_optional_detail_skip_keeps_unfinished_answer_and_pending_story_without_ai(self):
        from tests.test_resume_onboarding_conversation import operation
        shared = self.shared_projection(); service = self.typed_service([]); calls = []
        def behavior(context):
            calls.append(context)
            return {'response': 'Review your Story.', 'next_question': 'What matters to you about repairing radios?',
                'operations': [operation(context, op='add_content', record_type='knowledge',
                    values={'title': 'Radio repair', 'classification': 'personal'}, section='My Story')]}
        self.conversation_service(service, behavior)
        page = self.page(); self.submit(page, 'I repair radios outside work.')
        page.get_by_role('button', name='Add a detail', exact=True).click()
        page.locator('#resume-intake-text').fill('An unfinished optional answer.')
        page.locator('#resume-intake-skip-question').click()
        page.get_by_role('button', name='Confirm details', exact=True).wait_for()
        page.locator('#resume-intake-hide').click(); page.locator('#resume-intake-reopen').click()
        self.assertEqual(len(service.get_workspace(self.owner)['pending_proposals']), 1)
        self.assertEqual(shared.policy.list_entries(self.owner)['entries'], [])
        self.assertEqual(len(calls), 1); self.assertEqual(self.errors, [])

    def test_existing_story_amendment_without_returned_question_offers_optional_detail_before_confirm(self):
        from tests.test_resume_onboarding_conversation import operation
        shared = self.shared_projection(); key = self.seed_story(shared)
        service = self.typed_service([]); calls = []
        wording = 'I enjoy woodworking and informal mentoring because explaining a new skill matters to me.'
        def behavior(context):
            calls.append(context)
            return {'response': 'Review your amended Story.', 'next_question': '', 'operations': [
                operation(context, ref='record:' + key, record_type='knowledge', values={'wording': wording}, section='My Story')]}
        self.conversation_service(service, behavior)
        page = self.page(expect_guide=False)
        page.locator('#resume-intake[open]').wait_for()
        self.submit(page, wording)
        page.locator('[data-optional-invitation]').wait_for()
        self.assertIn('A quiet craft', page.locator('[data-optional-invitation]').inner_text())
        self.assertTrue(page.get_by_role('button', name='Confirm details', exact=True).is_visible())
        self.assertEqual(shared.canonical.get_item(self.owner, key)['values']['wording'], 'I enjoy woodworking and informal mentoring.')
        page.get_by_role('button', name='Keep these details', exact=True).click()
        self.confirm(page)
        self.assertEqual(shared.draft.get_workspace(self.owner)['items'][0]['proposed_values']['wording'], wording)
        self.assertEqual(shared.canonical.get_item(self.owner, key)['values']['wording'], 'I enjoy woodworking and informal mentoring.')
        self.assertEqual(len(shared.policy.list_entries(self.owner)['entries']), 1)
        self.assertEqual(len(calls), 1); self.assertEqual(self.errors, [])

    def test_answering_optional_story_detail_revises_same_pending_story_before_confirmation(self):
        from tests.test_resume_onboarding_conversation import operation
        shared = self.shared_projection(); service = self.typed_service([]); calls = []
        first_words = 'I repair radios outside work.'
        extra_words = 'I like learning how older circuits work.'
        def behavior(context):
            calls.append(context)
            if len(calls) == 1:
                return {'response': 'Review your Story.', 'next_question': 'What do you enjoy about repairing radios?',
                    'operations': [operation(context, op='add_content', record_type='knowledge',
                        values={'title': 'Radio repair', 'classification': 'personal'}, section='My Story')]}
            return {'response': 'Review both of your details.', 'next_question': '', 'operations': [
                operation(context, ref=context['selected_target'], record_type='knowledge',
                    values={'wording': first_words + '\n' + extra_words}, section='My Story')]}
        self.conversation_service(service, behavior)
        page = self.page(); self.submit(page, first_words)
        page.get_by_role('button', name='Add a detail', exact=True).click()
        page.locator('#resume-intake-text').fill(extra_words); page.locator('#resume-intake-add').click()
        page.locator('#resume-intake-review:visible').wait_for()
        self.assertEqual(len(service.get_workspace(self.owner)['pending_proposals']), 1)
        self.assertEqual(shared.policy.list_entries(self.owner)['entries'], [])
        self.assertTrue(calls[-1]['selected_target'].startswith('proposal:'))
        self.confirm(page)
        self.assertEqual(shared.policy.list_entries(self.owner)['entries'][0]['values']['wording'], first_words + '\n' + extra_words)
        self.assertEqual(len(calls), 2); self.assertEqual(self.errors, [])

    def test_career_answer_offers_grounded_optional_detail_before_direct_confirmation(self):
        from tests.test_resume_onboarding_conversation import operation
        service = self.typed_service([]); calls = []
        def behavior(context):
            calls.append(context)
            return {'response': 'Review your role.', 'next_question': '', 'operations': [
                operation(context, op='add_content', values={'role_title': 'Engineer', 'employer_name': 'Example Labs'})]}
        self.conversation_service(service, behavior)
        page = self.page(); self.submit(page, 'I was an Engineer at Example Labs.')
        self.assertIn('Engineer', page.locator('[data-optional-invitation]').inner_text())
        self.confirm(page)
        self.assertEqual(len(self.catalog.list_items(self.owner)), 1)
        self.assertEqual(len(calls), 1); self.assertEqual(self.errors, [])

    def test_rejected_suggestion_review_returns_pending_then_saves_once_without_provider(self):
        service = self.typed_service([{'kind': 'inferred_wording', 'record_type': 'role',
            'confidence': 'certain', 'values': {'role_title': 'Engineer', 'employer_name': 'Example Labs'}}])
        page = self.page(); self.submit(page, 'Engineer at Example Labs. Original source words.')
        page.get_by_role('button', name='Leave this out', exact=True).click()
        page.locator('#resume-intake-excluded-review:visible').wait_for()
        page.locator('#resume-intake-excluded-review > summary').click()
        page.get_by_role('button', name='Review these details', exact=True).click()
        page.get_by_role('button', name='Confirm details', exact=True).wait_for()
        self.assertEqual(self.catalog.list_items(self.owner), [])
        self.assertEqual(len(service.get_workspace(self.owner)['pending_proposals']), 1)
        self.confirm(page)
        self.assertEqual(len(self.catalog.list_items(self.owner)), 1)
        self.assertEqual(service.get_workspace(self.owner)['resume_recoverable_details'], [])
        self.assertEqual(self.errors, [])

    def test_pending_exclusion_undo_restores_original_review_without_extra_ai_or_canonical_write(self):
        from tests.test_resume_onboarding_conversation import operation
        service = self.typed_service([{'kind': 'inferred_wording', 'record_type': 'role',
            'confidence': 'certain', 'values': {'role_title': 'Engineer', 'employer_name': 'Example Labs'}}])
        calls = []
        from tests.test_my_data_intake_ai import add_request
        service.submit(self.owner, add_request(text='Engineer at Example Labs. Original source words.'))
        def behavior(context):
            calls.append(context)
            return {'response': 'Review exclusion.', 'next_question': '', 'operations': [
                operation(context, op='exclude_content', ref=context['selected_target'])]}
        self.conversation_service(service, behavior)
        page = self.page()
        page.get_by_role('button', name='Change something', exact=True).click()
        page.locator('#resume-intake-text').fill('Exclude this role.'); page.locator('#resume-intake-add').click()
        page.get_by_role('button', name='Undo exclusion', exact=True).click()
        page.locator('#resume-intake-status').get_by_text('Exclusion undone.', exact=False).wait_for()
        page.get_by_role('button', name='Confirm details', exact=True).wait_for()
        self.assertEqual(len(service.get_workspace(self.owner)['pending_proposals']), 1)
        self.assertEqual(self.catalog.list_items(self.owner), [])
        self.assertEqual(len(calls), 1)
        self.confirm(page); self.assertEqual(len(self.catalog.list_items(self.owner)), 1)
        self.assertEqual(self.errors, [])

    def test_pending_saved_role_bullet_exclusion_undo_retains_checklist_and_manual_review_without_extra_ai(self):
        from tests.test_my_data_intake_ai import add_request
        from tests.test_resume_onboarding_conversation import operation
        service = self.typed_service([]); calls = []
        baseline = 'Keep my contribution.\nRetain this exact limitation.'
        summary = baseline + '\nI wrote a review checklist.'
        key = service.submit(self.owner, add_request(items=[{'client_key': 'role', 'record_type': 'role',
            'values': {'role_title': 'Engineer', 'employer_name': 'Example Labs', 'summary': baseline},
            'explicit_clears': []}]))['results'][0]['record_key']
        before = self.draft_service.get_workspace(self.owner)
        def behavior(context):
            calls.append(context)
            edit = [{'action': 'exclude', 'field': 'summary', 'index': 1,
                'expected_text': 'Retain this exact limitation.', 'replacement': None}]
            return {'response': 'Review these details.', 'next_question': '', 'operations': [
                operation(context, ref='record:' + key, values={'summary': summary}) if len(calls) == 1 else
                operation(context, ref=context['selected_target'], bullets=edit)]}
        self.conversation_service(service, behavior)
        page = self.page(expect_guide=False)
        page.locator('#resume-intake[open]').wait_for()
        self.submit(page, 'I wrote a review checklist.')
        page.get_by_role('button', name='Change something', exact=True).click()
        page.locator('#resume-intake-text').fill('Exclude the limitation.'); page.locator('#resume-intake-add').click()
        page.get_by_role('button', name='Undo exclusion', exact=True).click()
        page.locator('#resume-intake-status').get_by_text('Exclusion undone.', exact=False).wait_for()
        page.get_by_role('button', name='Confirm details', exact=True).wait_for()
        self.assertTrue(page.get_by_role('button', name='Change something', exact=True).is_visible())
        self.assertTrue(page.get_by_role('button', name='Edit fields manually', exact=True).is_visible())
        pending = service.get_workspace(self.owner)['pending_proposals']
        self.assertEqual(len(pending), 1); self.assertEqual(pending[0]['target_key'], key)
        self.assertEqual(pending[0]['proposed_values']['summary'], summary)
        self.assertEqual(self.draft_service.get_workspace(self.owner), before)
        self.assertEqual(len(calls), 2)
        self.confirm(page)
        items = self.draft_service.get_workspace(self.owner)['items']
        self.assertEqual(len(items), 1); self.assertEqual(items[0]['record_key'], key)
        self.assertEqual(items[0]['proposed_values']['summary'], summary)
        self.assertEqual(items[0]['values']['summary'], baseline)
        self.assertEqual(len(calls), 2); self.assertEqual(self.errors, [])

    def saved_excluded_detail_browser(self, *, bullet=False):
        from tests.test_my_data_intake_ai import add_request
        from tests.test_resume_onboarding_conversation import operation
        service = self.typed_service([]); calls = []
        key = service.submit(self.owner, add_request(items=[{'client_key': 'role', 'record_type': 'role',
            'values': {'role_title': 'Engineer', 'employer_name': 'Example Labs',
                'summary': 'Keep my contribution.\nRetain this exact limitation.'}, 'explicit_clears': []}]))['results'][0]['record_key']
        def behavior(context):
            calls.append(context)
            edit = [{'action': 'exclude', 'field': 'summary', 'index': 1,
                'expected_text': 'Retain this exact limitation.', 'replacement': None}] if bullet else []
            return {'response': 'Review this exclusion.', 'next_question': '', 'operations': [
                operation(context, op='revise_content' if bullet else 'exclude_content', ref='record:' + key, bullets=edit)]}
        self.conversation_service(service, behavior)
        page = self.page(320, 800, expect_guide=False)
        page.locator('#resume-intake[open]').wait_for()
        self.submit(page, 'Exclude the limitation.' if bullet else 'Exclude this role.')
        with page.expect_response(lambda r: r.url.endswith('/proposals/decision') and r.request.method == 'POST'):
            page.get_by_role('button', name='Confirm details', exact=True).click()
        page.locator('#resume-intake-excluded-review:visible').wait_for()
        page.locator('#resume-intake-excluded-review > summary').click()
        page.get_by_role('button', name='Review these details', exact=True).click()
        page.get_by_role('button', name='Confirm details', exact=True).wait_for()
        self.assertFalse(page.get_by_role('button', name='Change something', exact=True).is_visible())
        self.assertFalse(page.get_by_role('button', name='Edit fields manually', exact=True).is_visible())
        self.assertEqual(len(calls), 1)
        self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth'), 320)
        if not bullet: self.assertTrue(dict(service.get_workspace(self.owner)['resume_excluded_records'])[key])
        before = self.draft_service.get_workspace(self.owner)
        with page.expect_response(lambda r: r.url.endswith('/proposals/decision') and r.request.method == 'POST'):
            page.get_by_role('button', name='Confirm details', exact=True).click()
        page.locator('#resume-intake-excluded-review').wait_for(state='hidden')
        after = self.draft_service.get_workspace(self.owner)
        if bullet: self.assertEqual(after['items'][0]['proposed_values']['summary'], 'Keep my contribution.\nRetain this exact limitation.')
        else:
            self.assertFalse(dict(service.get_workspace(self.owner)['resume_excluded_records'])[key])
            self.assertEqual(after, before)
        self.assertEqual(len(self.catalog.list_items(self.owner)), 1)
        self.assertEqual(len(calls), 1); self.assertEqual(self.errors, [])

    def test_saved_record_review_restores_same_projection_only_after_confirmation(self):
        self.saved_excluded_detail_browser()

    def test_saved_bullet_review_restores_exact_literal_at_320_after_confirmation(self):
        self.saved_excluded_detail_browser(bullet=True)

    def test_story_review_labels_and_hidden_classification_preserve_approved_truth(self):
        from tests.test_resume_onboarding_conversation import operation
        shared = self.shared_projection()
        service = self.typed_service([])
        self.conversation_service(service, lambda context: {'response': 'Review your optional Story.',
            'next_question': '', 'operations': [operation(context, op='add_content', record_type='knowledge',
                values={'title': 'A quiet craft', 'wording': 'I enjoy woodworking and informal mentoring.',
                        'classification': 'personal'}, section='My Story')]})
        page = self.page(); self.submit(page, 'I enjoy woodworking and informal mentoring.')
        facts = page.locator('.resume-intake__review-facts').inner_text()
        self.assertIn('Story title', facts); self.assertIn('Story text', facts)
        self.assertNotIn('personal', facts); self.assertNotIn('Contribution', facts)
        page.get_by_role('button', name='Edit fields manually', exact=True).click()
        self.assertEqual(page.locator('label[for="resume-proposal-title"]').inner_text(), 'Story title')
        self.assertEqual(page.locator('label[for="resume-proposal-wording"]').inner_text(), 'Story text')
        self.assertTrue(self.field(page, 'classification').is_hidden())
        self.assertEqual(self.field(page, 'classification').input_value(), 'personal')
        self.field(page, 'wording').fill('I enjoy woodworking; informal mentoring is optional.')
        self.capture(page, 'final-story-review-labels')
        self.confirm(page)
        entry = shared.policy.list_entries(self.owner)['entries'][0]
        self.assertEqual(entry['values']['classification'], 'personal')
        self.assertEqual(entry['values']['wording'], 'I enjoy woodworking; informal mentoring is optional.')
        self.assertFalse(entry['resume_display']); self.assertFalse(entry['visitor_ai'])
        self.assertEqual(self.errors, [])

    def test_destination_selected_story_has_context_labels_without_classification_control(self):
        shared = self.shared_projection()
        self.typed_service([{'kind': 'inferred_wording', 'record_type': 'unspecified',
                            'values': {'wording': 'I repair radios outside work.'}}])
        page = self.page(); self.submit(page, 'I repair radios outside work.')
        page.locator('[data-proposal-type]').select_option('knowledge')
        self.assertEqual(page.locator('label[for="resume-proposal-wording"]').inner_text(), 'Story text')
        self.assertTrue(self.field(page, 'classification').is_hidden())
        self.assertEqual(self.field(page, 'classification').input_value(), 'personal')
        self.confirm(page)
        self.assertEqual(shared.policy.list_entries(self.owner)['entries'][0]['values']['classification'], 'personal')

    def test_hidden_work_knowledge_classification_stays_work_and_outside_story(self):
        from tests.test_resume_onboarding_conversation import operation
        shared = self.shared_projection(); service = self.typed_service([])
        self.conversation_service(service, lambda context: {'response': 'Review your professional summary.',
            'next_question': '', 'operations': [operation(context, op='add_content', record_type='knowledge',
                values={'title': 'Professional summary', 'wording': 'I build prototypes; outcomes are not independently verified.',
                        'classification': 'work'}, section='Professional summary')]})
        page = self.page(); self.submit(page, 'I build prototypes; outcomes are not independently verified.')
        self.assertNotIn('classification', page.locator('.resume-intake__review-facts').inner_text())
        page.get_by_role('button', name='Edit fields manually', exact=True).click()
        self.assertTrue(self.field(page, 'classification').is_hidden())
        self.assertEqual(self.field(page, 'classification').input_value(), 'work')
        self.confirm(page)
        entry = shared.policy.list_entries(self.owner)['entries'][0]
        self.assertEqual(entry['values']['classification'], 'work')
        page.wait_for_function("() => document.querySelector('#resume-intake-document-content').textContent.includes('outcomes are not independently verified')")
        self.assertEqual(page.locator('#resume-intake-document-content #resume-story').count(), 0)
        self.assertFalse(entry['visitor_ai']); self.assertFalse(entry['resume_display'])
        self.assertEqual(self.errors, [])

    def test_review_actions_are_separate_in_reflow_and_manual_action_matches_mode(self):
        self.typed_service([self.role_proposal()])
        page = self.page(device_scale_factor=2); self.submit(page, 'My current role is Product designer at Northstar Studio.')
        self.assertEqual(page.evaluate('devicePixelRatio'), 2)
        first = page.get_by_role('button', name='Edit fields manually', exact=True)
        second = page.get_by_role('button', name='Leave this out', exact=True)
        for width, height in [(1440, 1000), (390, 844), (320, 700), (640, 480)]:
            page.set_viewport_size({'width': width, 'height': height})
            page.wait_for_function("""() => {const d=document.querySelector('#resume-intake'),s=d.querySelector('.resume-intake__surface'),r=d.getBoundingClientRect();return r.left>=-1 && r.right<=innerWidth+1 && s.scrollWidth<=s.clientWidth+1;}""")
            first.scroll_into_view_if_needed()
            one, two = first.bounding_box(), second.bounding_box()
            self.assertTrue(two['x'] - (one['x'] + one['width']) >= 12 or
                            two['y'] - (one['y'] + one['height']) >= 3, (one, two))
            self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth - innerWidth'), 1)
            self.capture(page, 'final-review-actions-' + str(width))
        first.click()
        self.assertTrue(first.is_hidden()); self.assertTrue(second.is_visible())
        self.field(page, 'role_title').press('Tab')
        self.confirm(page)

    def test_library_blank_catalog_search_loading_and_unavailable_have_truthful_states(self):
        from unittest.mock import patch
        self.shared_projection(media=True)
        page = self.page(); self.manual(page)
        page.locator('#resume-media-tab-library').click()
        empty = page.locator('#resume-media-library-empty'); empty.wait_for(state='visible')
        self.assertNotIn('search', empty.inner_text().lower())
        self.capture(page, 'final-library-before-search')
        search = page.locator('#resume-media-library-search')
        search.fill('zz-no-match')
        page.wait_for_function("() => document.querySelector('#resume-media-library-empty').textContent.includes('match that search')")
        # Hold a real route response to prove stale no-match copy disappears
        # while the next query loads, then cannot overwrite a newer query.
        held = []
        def hold(route):
            if 'query=slow-empty' in route.request.url:
                held.append((route, route.fetch())); return
            route.continue_()
        page.route('**/api/resume-media/me/library**', hold)
        search.fill('slow-empty')
        page.wait_for_timeout(350)
        self.assertEqual(len(held), 1); self.assertTrue(empty.is_hidden())
        self.assertIn('Loading', page.locator('#resume-media-library-loading').inner_text())
        self.assertEqual(page.locator('#resume-media-library-results').get_attribute('aria-busy'), 'true')
        search.fill('')
        page.wait_for_function("() => !document.querySelector('#resume-media-library-empty').hidden && document.querySelector('#resume-media-library-empty').textContent.includes('available right now') && document.querySelector('#resume-media-library-results').getAttribute('aria-busy') === 'false'")
        held[0][0].fulfill(response=held[0][1])
        page.wait_for_timeout(100)
        self.assertNotIn('search', empty.inner_text().lower())
        page.unroute('**/api/resume-media/me/library**', hold)
        from services.resume_media_application import ResumeMediaApplicationUnavailable
        with patch.object(app.config['RESUME_MEDIA_SERVICE'], 'library', side_effect=ResumeMediaApplicationUnavailable('Synthetic library unavailable')):
            search.fill('unavailable')
            page.locator('#resume-media-library-error').wait_for(state='visible')
            self.assertTrue(empty.is_hidden())
        self.assertEqual(self.errors, [])

    def test_actual_resume_refreshes_manual_story_bind_clear_and_guide_return_without_reload(self):
        shared = self.shared_projection(); key = self.seed_story(shared)
        page = self.page(expect_guide=False); page.locator('#resume-intake[open]').wait_for(); self.input(page)
        page.locator('#resume-intake-text').fill('Keep this unfinished answer.')
        self.manual(page)
        content = page.locator('#resume-intake-document-content')
        page.locator('#resume-story-choice').select_option(key)
        page.locator('#resume-story-select').click()
        page.locator('#resume-story-status').get_by_text('Selected for your private Resume draft.', exact=False).wait_for()
        page.wait_for_function("() => document.querySelector('#resume-intake-document-content').textContent.includes('A quiet craft')")
        self.assertIn('informal mentoring', content.inner_text())
        page.locator('#resume-intake-reopen').click()
        self.assertEqual(page.locator('#resume-intake-text').input_value(), 'Keep this unfinished answer.')
        page.locator('#resume-intake-hide').click()
        page.locator('#resume-story-choice').select_option('')
        page.locator('#resume-story-select').click()
        page.locator('#resume-story-status').get_by_text('Removed from your private Resume draft.', exact=False).wait_for()
        page.wait_for_function("() => !document.querySelector('#resume-intake-document-content').textContent.includes('A quiet craft') && document.querySelector('#resume-intake-document-content .resume-publication--public')")
        page.locator('#resume-intake-reopen').click()
        self.assertEqual(page.locator('#resume-intake-text').input_value(), 'Keep this unfinished answer.')
        page.wait_for_function("() => !document.querySelector('#resume-intake-document-status').textContent.includes('Refreshing')")
        self.assertNotIn('A quiet craft', content.inner_text())
        page.locator('#resume-intake-hide').click(); self.capture(page, 'final-actual-preview-cleared-story')
        self.assertEqual(len(shared.policy.list_entries(self.owner)['entries']), 1)
        self.assertFalse(shared.policy.list_entries(self.owner)['entries'][0]['visitor_ai'])
        self.assertEqual(self.errors, [])

    def test_actual_resume_refreshes_manual_save_discard_without_submitting_guide_words(self):
        from tests.test_my_data_intake_ai import add_request
        shared = self.shared_projection()
        app.config['RESUME_INTAKE_SERVICE'].submit(self.owner, add_request(items=[{
            'client_key': 'role', 'record_type': 'role', 'values': {
                'role_title': 'Engineer', 'employer_name': 'Example Labs', 'summary': 'Original qualified wording.',
                'date_precision': 'unknown', 'current_role': True}, 'explicit_clears': []}]))
        page = self.page(expect_guide=False); page.locator('#resume-intake[open]').wait_for(); self.input(page)
        page.locator('#resume-intake-text').fill('Unsubmitted guide words.')
        self.manual(page)
        card = page.locator('.resume-editor__card').filter(has=page.get_by_role('heading', name='Engineer', exact=True))
        card.locator('summary').click()
        card.locator('textarea[name="summary"]').fill('Revised wording; result not independently verified.')
        card.get_by_role('button', name='Save draft', exact=True).click()
        page.locator('#resume-editor-status').get_by_text('Draft saved.', exact=False).wait_for()
        page.wait_for_function("() => document.querySelector('#resume-intake-document-content').textContent.includes('Revised wording; result not independently verified.')")
        card.locator('summary').click()
        card.get_by_role('button', name='Discard draft', exact=True).click()
        page.locator('#resume-editor-status').get_by_text('Draft discarded.', exact=False).wait_for()
        page.wait_for_function("() => document.querySelector('#resume-intake-document-content').textContent.includes('Original qualified wording.') && !document.querySelector('#resume-intake-document-content').textContent.includes('Revised wording;')")
        page.locator('#resume-intake-reopen').click()
        self.assertEqual(page.locator('#resume-intake-text').input_value(), 'Unsubmitted guide words.')
        self.assertNotIn('Unsubmitted guide words.', page.locator('#resume-intake-document-content').inner_text())
        self.assertEqual(self.errors, [])

    def test_old_preview_response_cannot_restore_cleared_story_and_failure_keeps_unsaved_inputs(self):
        from uuid import uuid4
        shared = self.shared_projection(); key = self.seed_story(shared)
        row = shared.canonical.get_item(self.owner, key)
        shared.draft.commit(self.owner, {'type': 'bind_story', 'request_id': str(uuid4()),
            'record_key': key, 'expected_draft_version': shared.draft.get_workspace(self.owner)['draft_version'],
            'expected_content_token': row['content_token'], 'expected_access_revision': row['access_revision']})
        page = self.page(expect_guide=False); page.locator('#resume-intake[open]').wait_for()
        page.wait_for_function("() => document.querySelector('#resume-intake-document-content').textContent.includes('A quiet craft')")
        self.input(page); page.locator('#resume-intake-text').fill('My unfinished guide answer.')
        self.manual(page)
        story_words = page.locator('#resume-story-wording')
        page.locator('#resume-editor-story-controls details summary').click()
        story_words.fill('My unsaved manual Story words.')
        held = []
        def hold_first(route):
            if not held:
                held.append((route, route.fetch())); return
            route.continue_()
        preview_url = page.locator('#resume-intake').get_attribute('data-preview-url')
        page.route('**' + preview_url, hold_first)
        # Guide return is a refresh even when no mutation was made in this tab.
        page.locator('#resume-intake-reopen').click()
        for _ in range(100):
            if held: break
            page.wait_for_timeout(50)
        self.assertEqual(len(held), 1)
        self.assertIn('earlier saved preview', page.locator('#resume-intake-document-status').inner_text())
        page.locator('#resume-intake-hide').click()
        page.locator('#resume-story-choice').select_option(''); page.locator('#resume-story-select').click()
        page.wait_for_function("() => !document.querySelector('#resume-intake-document-content').textContent.includes('A quiet craft') && document.querySelector('#resume-intake-document-content .resume-publication--public')")
        held[0][0].fulfill(response=held[0][1]); page.wait_for_timeout(100)
        self.assertNotIn('A quiet craft', page.locator('#resume-intake-document-content').inner_text())
        page.unroute('**' + preview_url, hold_first)
        # A failed saved-preview read cannot erase or submit either editor.
        story_words.fill('Still unsaved manual words.')
        page.route('**' + preview_url, lambda route: route.fulfill(
            status=503, content_type='application/json', body='{"success":false,"message":"Synthetic preview outage."}'))
        page.locator('#resume-intake-reopen').click()
        page.wait_for_function("() => document.querySelector('#resume-intake-document-status').textContent.includes('unavailable')")
        self.assertEqual(page.locator('#resume-intake-text').input_value(), 'My unfinished guide answer.')
        page.locator('#resume-intake-hide').click()
        self.assertEqual(story_words.input_value(), 'Still unsaved manual words.')
        self.assertEqual(len(shared.policy.list_entries(self.owner)['entries']), 1)
        self.assertEqual(self.errors, [])

    def test_actual_resume_refreshes_saved_media_add_remove_and_words_only_without_reload(self):
        from uuid import uuid4
        shared = self.shared_projection(media=True); photo = shared.seed_photo(self.owner)
        key = self.seed_story(shared); row = shared.canonical.get_item(self.owner, key)
        shared.draft.commit(self.owner, {'type': 'bind_story', 'request_id': str(uuid4()),
            'record_key': key, 'expected_draft_version': shared.draft.get_workspace(self.owner)['draft_version'],
            'expected_content_token': row['content_token'], 'expected_access_revision': row['access_revision']})
        page = self.page(expect_guide=False); page.locator('#resume-intake[open]').wait_for(); self.manual(page)
        card = page.locator('#resume-media-photos > li').first
        card.get_by_role('button', name='Use for My Story banner', exact=True).click()
        page.locator('#resume-media-preview-placement').click()
        page.locator('#resume-media-add').click()
        page.locator('#resume-media-status').get_by_text('Added 1 photo', exact=False).wait_for()
        page.wait_for_function("() => document.querySelector('#resume-intake-document-content .resume-publication__crop--story_banner img')")
        image = page.locator('#resume-intake-document-content .resume-publication__crop--story_banner img')
        self.assertTrue(image.get_attribute('src'))
        page.locator('#resume-media-change-photos').click()
        page.locator('#resume-media-keep-words').click()
        page.locator('#resume-media-status').get_by_text('Kept your words.', exact=False).wait_for()
        page.wait_for_function("() => document.querySelector('#resume-intake-document').getAttribute('aria-busy') === 'false'")
        self.assertEqual(image.count(), 1)
        page.locator('#resume-media-slot-story_banner-remove').click()
        page.locator('#resume-media-status').get_by_text('My Story banner removed', exact=False).wait_for()
        page.wait_for_function("() => !document.querySelector('#resume-intake-document-content .resume-publication__crop--story_banner img') && document.querySelector('#resume-intake-document-content .resume-publication--public')")
        self.assertEqual(shared.media.workspace(owner_id=self.owner)['slots']['story_banner'], None)
        self.assertIsNotNone(shared.media_sources.get_owner_photo(owner_id=self.owner, source_id=photo.source_id))
        self.assertEqual(self.errors, [])

    def test_initial_controls_and_immediate_grounded_followup_need_no_provider_click(self):
        service=self.typed_service([self.role_proposal()]);calls=[]
        page=self.page();self.input(page)
        for name in ('draft-state','new-question','skip-question','input-finish'):
            self.assertFalse(page.locator('#resume-intake-'+name).is_visible())
        self.submit(page,'My role.')
        self.conversation_service(service,lambda context:calls.append(context))
        page.reload();page.get_by_role('button',name='Confirm details',exact=True).wait_for();self.confirm(page)
        self.assertIn('Product designer',page.locator('#resume-intake-followup').inner_text())
        self.assertIn('contribution or result',page.locator('#resume-intake-followup').inner_text())
        self.assertEqual(calls,[])
        self.capture(page,'correction-immediate-followup.png')

    def test_real_history_returns_to_optional_after_story_and_reload_keeps_answer(self):
        self.typed_service([self.role_proposal()])
        page=self.page(390,844);self.submit(page,'My role.');self.confirm(page)
        page.locator('#resume-intake-next-finish').click();page.locator('#resume-intake-add-story').click()
        with page.expect_response(lambda response:response.url.endswith('/draft') and response.request.method=='PUT' and response.status==200):
            page.locator('#resume-intake-text').fill('I enjoy mentoring; an optional personal detail.')
        page.reload();page.locator('#resume-intake-input:visible').wait_for()
        self.assertIn('outside work',page.locator('#resume-intake-question').inner_text())
        page.locator('#resume-intake-back').click();page.locator('#resume-intake-optional:visible').wait_for()
        page.locator('#resume-intake-add-story').click()
        self.assertEqual(page.locator('#resume-intake-text').input_value(),'I enjoy mentoring; an optional personal detail.')
        self.assertEqual(len(self.catalog.list_items(self.owner)),1)
        self.capture(page,'correction-story-history-phone.png')

    def test_section_record_selector_keeps_keyboard_focus_and_clear_uses_existing_identity(self):
        from tests.test_my_data_intake_ai import add_request
        from tests.test_resume_onboarding_conversation import operation
        service=self.typed_service([])
        key=service.submit(self.owner,add_request(items=[{'client_key':'role','record_type':'role','values':{
            'role_title':'Engineer','employer_name':'Example Labs','location_text':'Denver'},'explicit_clears':[]}]))['results'][0]['record_key']
        self.conversation_service(service,lambda ctx:{'response':'Review both.', 'next_question':'','operations':[
            operation(ctx,ref='record:'+key,clears=['location_text']),
            operation(ctx,op='add_content',record_type='skill',values={'name':'Systems thinking'},section='Skills')]})
        page=self.page(expect_guide=False);page.locator('#resume-intake[open]').wait_for();self.input(page);page.locator('#resume-intake-text').fill('Clear the location and add Systems thinking.');page.locator('#resume-intake-add').click()
        page.get_by_role('button',name='Confirm details',exact=True).wait_for()
        overview=page.locator('#resume-intake-suggestion-overview')
        self.assertEqual(overview.get_by_role('heading').all_text_contents(),['Experience','Skills'])
        choice=overview.get_by_role('button',name='Systems thinking',exact=True);choice.focus();page.keyboard.press('Enter')
        self.assertEqual(page.evaluate('document.activeElement.textContent'),'Systems thinking')
        choice=overview.get_by_role('button',name='Engineer · Example Labs',exact=True);choice.focus();page.keyboard.press('Enter')
        self.assertEqual(page.evaluate('document.activeElement.textContent'),'Engineer · Example Labs')
        self.assertNotIn('New: Your words',overview.inner_text())
        self.capture(page,'correction-grouped-clear-review.png')

    def test_existing_record_can_be_revised_twice_then_confirmed_through_actual_routes(self):
        from tests.test_my_data_intake_ai import add_request
        from tests.test_resume_onboarding_conversation import operation
        service=self.typed_service([])
        key=service.submit(self.owner,add_request(items=[{'client_key':'role','record_type':'role','values':{
            'role_title':'Engineer','employer_name':'Example Labs','location_text':'Denver',
            'summary':'Coordinated ten people; I was not their manager.'},'explicit_clears':[]}]))['results'][0]['record_key']
        def provider(ctx):
            words=' '.join(unit['text'] for unit in ctx['current_turn']['units'])
            return {'response':'Review the new location.', 'next_question':'','operations':[
                operation(ctx,ref=ctx['selected_target'] or 'record:'+key,values={'location_text':'Fort Collins' if 'Fort Collins' in words else 'Boulder'})]}
        self.conversation_service(service,provider)
        page=self.page(expect_guide=False);page.locator('#resume-intake[open]').wait_for();self.input(page);page.locator('#resume-intake-text').fill('Change location to Boulder.');page.locator('#resume-intake-add').click()
        page.get_by_role('button',name='Change something',exact=True).click()
        page.locator('#resume-intake-text').fill('Actually use Fort Collins.');page.locator('#resume-intake-add').click()
        page.get_by_role('button',name='Confirm details',exact=True).wait_for();self.confirm(page)
        item=self.draft_service.get_workspace(self.owner)['items'][0]
        self.assertEqual(item['proposed_values']['location_text'],'Fort Collins')
        self.assertIn('not their manager',item['proposed_values']['summary'])

    def test_descriptive_voice_targets_cancel_duplicate_and_edit_fences(self):
        context=self.browser.new_context(viewport={'width':1440,'height':1000});self.addCleanup(context.close)
        context.add_init_script("""window.__resumeSpeech=[];window.__voiceTracks=0;
            navigator.mediaDevices.getUserMedia=()=>Promise.resolve({getTracks:()=>[{stop:()=>window.__voiceTracks++}]});
            window.SpeechRecognition=class {constructor(){window.__resumeSpeech.push(this)}start(){}abort(){this.aborted=true}};
            window.emitResumeSpeech=(index,words)=>{const result=[{transcript:words}];result.isFinal=true;
                window.__resumeSpeech[index].onresult({resultIndex:0,results:[result]})};""")
        page=context.new_page();page.set_default_timeout(7000);page.goto(self.base_url+'/app/resume')
        page.locator('#resume-intake[open]').wait_for();self.manual(page)
        page.locator('#resume-editor-story-controls details summary').click()
        words=page.locator('#resume-story-wording');words.fill('Original story.');words.focus();words.press('End')
        page.get_by_role('button',name='Dictate My Story words',exact=True).click()
        page.wait_for_function('window.__resumeSpeech.length===1')
        page.evaluate("emitResumeSpeech(0,'A turning point.')");page.evaluate("emitResumeSpeech(0,'A turning point.')")
        self.assertEqual(words.input_value(),'Original story. A turning point.')
        page.get_by_role('button',name='Cancel dictation',exact=True).click();page.evaluate("emitResumeSpeech(0,'Late words.')")
        self.assertNotIn('Late',words.input_value())
        page.locator('#resume-intake-type').select_option('role')
        description=page.locator('#resume-intake-role-summary');description.fill('Qualified work.');description.focus();description.press('End')
        page.get_by_role('button',name='Dictate Responsibilities and results (optional)',exact=True).click()
        page.wait_for_function('window.__resumeSpeech.length===2')
        words.focus();page.evaluate("emitResumeSpeech(1,'Wrong target.')")
        self.assertEqual(description.input_value(),'Qualified work.');self.assertNotIn('Wrong target',words.input_value())
        page.get_by_role('button',name='Dictate Responsibilities and results (optional)',exact=True).click()
        page.wait_for_function('window.__resumeSpeech.length===3');description.fill('New typed revision.')
        page.evaluate("emitResumeSpeech(2,'Old transcript.')");self.assertEqual(description.input_value(),'New typed revision.')
        self.assertEqual(self.catalog.list_items(self.owner),[])
        self.assertEqual(page.evaluate('window.__voiceTracks'),3)
        # A delayed permission response owns only its original session. Cancel
        # and edit before permission resolves; returned tracks are still reaped.
        page.evaluate("() => {navigator.mediaDevices.getUserMedia=()=>new Promise(resolve=>window.__resolveVoicePermission=resolve)}")
        page.get_by_role('button',name='Dictate Responsibilities and results (optional)',exact=True).click()
        page.get_by_role('button',name='Cancel dictation',exact=True).click()
        page.evaluate("window.__resolveVoicePermission({getTracks:()=>[{stop:()=>window.__voiceTracks++}]})")
        page.wait_for_function('window.__voiceTracks===4')
        self.assertEqual(page.evaluate('window.__resumeSpeech.length'),3)
        self.assertEqual(description.input_value(),'New typed revision.')
        self.capture(page,'correction-manual-story-dictation.png')

    def test_review_field_dictation_is_capability_aware_and_fenced_when_selection_changes(self):
        self.typed_service([self.role_proposal(),{'kind':'inferred_wording','record_type':'skill',
            'values':{'name':'Systems thinking','summary':'Qualified skill.'}}])
        context=self.browser.new_context();self.addCleanup(context.close)
        context.add_init_script("""window.__reviewSpeech=[];
            navigator.mediaDevices.getUserMedia=()=>Promise.resolve({getTracks:()=>[{stop(){}}]});
            window.SpeechRecognition=class{constructor(){window.__reviewSpeech.push(this)}start(){}abort(){}};""")
        page=context.new_page();page.set_default_timeout(7000);page.goto(self.base_url+'/app/resume')
        page.locator('#resume-intake[open]').wait_for();self.submit(page,'A role and a skill.')
        page.get_by_role('button',name='Edit fields manually',exact=True).click()
        field=self.field(page,'summary');field.fill('Literal responsibilities.');field.focus();field.press('End')
        page.get_by_role('button',name='Dictate Description',exact=True).click()
        page.wait_for_function('window.__reviewSpeech.length===1')
        event="{resultIndex:0,results:[Object.assign([{transcript:'I was not their manager.'}],{isFinal:true})]}"
        page.evaluate('window.__reviewSpeech[0].onresult('+event+')')
        self.assertIn('not their manager',field.input_value())
        page.locator('#resume-intake-suggestion-overview').get_by_role('button',name='Systems thinking',exact=True).click()
        page.evaluate('window.__reviewSpeech[0].onresult('+event+')')
        page.get_by_role('button',name='Edit fields manually',exact=True).click()
        self.assertEqual(self.field(page,'summary').input_value(),'Qualified skill.')
        self.assertEqual(self.catalog.list_items(self.owner),[])

    def test_legacy_manual_story_dictation_loads_when_intake_feature_is_off(self):
        app.config['PEERSLATE_RESUME_INTAKE_ENABLED']=False
        context=self.browser.new_context();self.addCleanup(context.close)
        context.add_init_script("""window.__manualSpeech=null;
            navigator.mediaDevices.getUserMedia=()=>Promise.resolve({getTracks:()=>[{stop(){}}]});
            window.SpeechRecognition=class{constructor(){window.__manualSpeech=this}start(){}abort(){}};""")
        page=context.new_page();page.set_default_timeout(7000);page.goto(self.base_url+'/app/resume')
        page.locator('#resume-editor-story-controls details summary').click()
        field=page.locator('#resume-story-wording');field.fill('Original words.');field.focus();field.press('End')
        page.get_by_role('button',name='Dictate My Story words',exact=True).click()
        page.wait_for_function('window.__manualSpeech!==null')
        page.evaluate("window.__manualSpeech.onresult({resultIndex:0,results:[Object.assign([{transcript:'An optional personal detail.'}],{isFinal:true})]})")
        self.assertEqual(field.input_value(),'Original words. An optional personal detail.')
        self.assertEqual(self.catalog.list_items(self.owner),[])

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
        page.get_by_role('button', name='Edit fields manually').click()
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
        page.locator('#resume-intake').wait_for(state='hidden')  # pause saves first
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
        self.finish_input(page)
        page.locator('#resume-intake-optional-next').click()
        self.assertIn('does not publish', page.locator('#resume-intake-sharing').inner_text())
        page.locator('#resume-intake-complete').click()
        page.locator('#resume-intake-finish:visible').wait_for()
        self.assertEqual(self.repository.load_owner(self.owner)['guide']['status'], 'completed')
        self.assertEqual(len(self.catalog.list_items(self.owner)), 0)
        self.assertEqual(page.locator('#resume-intake-text').input_value(), 'Not submitted')
        self.assertTrue(page.locator('#resume-intake-finish-unsent').is_visible())
        page.locator('#resume-intake-view').click()
        page.locator('#resume-intake').wait_for(state='hidden')
        self.assertFalse(page.locator('#resume-intake').is_visible())
        page.reload(); self.assertFalse(page.locator('#resume-intake').is_visible())

    def test_finish_without_unsent_input_has_no_false_reminder(self):
        self.conversation_service(self.typed_service([]),lambda context:{'response':'You can start anywhere.',
            'next_question':'Which experience would you like to start with?','operations':[]})
        page = self.page(); self.input(page)
        page.locator('#resume-intake-text').fill('Help me get started.');page.locator('#resume-intake-add').click()
        page.locator('#resume-intake-question').get_by_text('Which experience would you like to start with?',exact=True).wait_for()
        self.finish_input(page)
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
        page.get_by_role('button', name='Edit fields manually').click()
        self.assertEqual(self.field(page, 'date_precision').input_value(), 'approximate')
        self.confirm(page)
        self.assertNotIn('2019-02-03', page.locator('.resume-intake__review-facts').inner_text())
        self.assertIn('Date unknown', page.locator('.resume-intake__review-facts').inner_text())
        page.get_by_role('button', name='Edit fields manually').click()
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
        page.get_by_role('button', name='Edit fields manually').click()
        page.locator('#resume-proposal-parent').select_option(role['record_key'])
        self.field(page, 'wording').fill('Simplified customer onboarding')
        page.locator('#resume-intake-back').click()
        page.locator('#resume-intake-review:visible').wait_for()
        page.get_by_role('button', name='Edit fields manually').click()
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
        page.get_by_role('button',name='Edit fields manually').click()
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
        self.finish_input(page); page.locator('#resume-intake-optional-next').click()
        page.locator('#resume-intake-complete').click()
        page.locator('#resume-intake-status[data-kind=error]').wait_for()
        self.assertFalse(page.locator('#resume-intake-finish').is_visible())
        page.locator('#resume-intake-complete').click(); page.locator('#resume-intake-finish:visible').wait_for()
        self.assertEqual(calls[0],calls[1]); self.assertEqual(calls[0]['status'],'completed')

    def test_contextual_question_is_explicit_revision_bound_and_never_saved(self):
        calls=[]
        service=self.typed_service([self.role_proposal()])
        def provider(context):
            calls.append(context)
            self.assertEqual(context['canonical']['draft_version'],self.draft_service.get_workspace(self.owner)['draft_version'])
            return {'next_question':'What changed for your customers?',
                'response':'Let’s explore the result of your work.','operations':[]}
        page=self.pending_conversation_page(service,provider);self.assertEqual(calls,[])
        self.confirm(page);self.assertEqual(calls,[])
        page.locator('#resume-intake-next-question').click()
        self.assertIn('Product designer',page.locator('#resume-intake-question').inner_text())
        self.assertEqual(calls,[])
        page.locator('#resume-intake-new-question').click()
        page.locator('#resume-intake-question').get_by_text('What changed for your customers?',exact=True).wait_for()
        self.assertEqual(len(calls),1);self.assertEqual(len(self.catalog.list_items(self.owner)),1)
        self.assertIn('Northstar Studio',str(calls[0]['canonical']['sources']))
        page.locator('#resume-intake-skip-question').click()
        self.assertNotEqual(self.repository.load_owner(self.owner)['guide'].get('status'),'completed')

    def test_ai_unavailable_keeps_words_and_no_fake_progress(self):
        from tests.test_my_data_intake_ai import add_request
        service=self.typed_service([self.role_proposal()])
        service.submit(self.owner,add_request(text='My role.'))
        app.config.update(PEERSLATE_RESUME_INTERVIEW_ENABLED=True,RESUME_PRIVATE_ASSISTANCE_SERVICE=None)
        page=self.page();self.confirm(page)
        page.locator('#resume-intake-next-question').click()
        page.locator('#resume-intake-new-question').click()
        page.locator('#resume-intake-status').get_by_text('unavailable',exact=False).wait_for()
        page.locator('#resume-intake-text').fill('My next thought.')
        self.assertFalse(page.locator('#resume-intake-activity').is_visible())
        self.assertEqual(len(self.catalog.list_items(self.owner)),1)
        page.locator('#resume-intake-skip').click()
        page.locator('#resume-intake').wait_for(state='hidden')  # pause saves first
        self.assertFalse(page.locator('#resume-intake').is_visible())
        self.assertEqual(page.locator('#resume-intake-text').input_value(),'My next thought.')

    def test_optional_topic_question_uses_current_story_or_project_without_old_role_target(self):
        calls=[]
        def provider(context):
            calls.append(context)
            return {'next_question':'What would you like people to understand about this '+context['guide_control']['intent']+'?',
                'response':'This detail is optional.', 'operations':[]}
        service=self.typed_service([self.role_proposal()])
        page=self.pending_conversation_page(service,provider);self.confirm(page)
        original=self.catalog.list_items(self.owner)
        page.locator('#resume-intake-next-finish').click()
        for topic,button,section in [('story','add-story','My Story'),('project','add-example','Projects')]:
            with self.subTest(topic=topic):
                page.locator('#resume-intake-'+button).click()
                page.locator('#resume-intake-new-question').click()
                page.locator('#resume-intake-question').get_by_text('What would you like people to understand about this '+topic+'?',exact=True).wait_for()
                context=calls[-1]
                self.assertEqual(context['guide_control']['intent'],topic)
                self.assertEqual(context['guide_control']['section'],section)
                self.assertIsNone(context['selected_target'])
                self.assertNotIn('selected_target',context['guide_control'])
                statement=context['current_turn']['units'][0]['text']
                self.assertIn('personal story' if topic=='story' else 'about a project',statement)
                self.assertNotIn('gap in my supplied work',statement)
                self.assertEqual(service.get_workspace(self.owner)['pending_proposals'],[])
                self.assertEqual(self.catalog.list_items(self.owner),original)
                page.locator('#resume-intake-input-finish').click()
        self.assertEqual(len(calls),2);self.assertEqual(self.errors,[])

    def test_bounded_history_accounts_for_unicode_and_keeps_live_answer_on_reload(self):
        self.typed_service([])
        page=self.page();self.input(page)
        words='我的经历' * 750
        page.locator('#resume-intake-text').fill(words)
        for button in ('add-story','add-example','add-story'):
            page.locator('#resume-intake-input-finish').click()
            page.locator('#resume-intake-'+button).click()
        with page.expect_response(lambda response: response.url.endswith('/draft') and response.request.method=='PUT' and response.status==200):
            page.locator('#resume-intake-text').fill(words+'。')
        draft=self.repository.load_owner(self.owner)['drafts']['composer']
        self.assertEqual(draft['text'],words+'。')
        self.assertLessEqual(len(json.dumps(draft['guide_state']['navigation_history']).encode('utf-8')),40000)
        self.assertTrue(draft['guide_state']['navigation_history'])
        page.reload();page.locator('#resume-intake-input:visible').wait_for()
        self.assertEqual(page.locator('#resume-intake-text').input_value(),words+'。')
        page.locator('#resume-intake-back').click()
        page.locator('#resume-intake-optional:visible').wait_for()
        self.assertEqual(page.locator('#resume-intake-text').input_value(),words+'。')
        self.assertEqual(self.catalog.list_items(self.owner),[]);self.assertEqual(self.errors,[])

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
        page.get_by_role('button',name='Edit fields manually').click()
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
        self.finish_input(page);page.locator('#resume-intake-add-story').click()
        self.assertTrue(page.locator('#resume-intake-input').is_visible())
        self.assertIn('outside work',page.locator('#resume-intake-question').inner_text())
        page.locator('#resume-intake-skip').click()
        page.locator('#resume-intake').wait_for(state='hidden')  # pause saves first
        self.assertFalse(page.locator('#resume-intake').is_visible())
        self.input(page)
        self.assertFalse(page.locator('#resume-intake-new-question').is_visible())
        self.assertEqual(page.locator('#resume-intake-text').input_value(),'An unfinished answer kept for later.')
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
        page.get_by_role('button',name='Edit fields manually').click();self.field(page,'start_date').fill('2021')
        page.locator('#resume-intake-back').click();page.locator('#resume-intake-review:visible').wait_for()
        page.get_by_role('button',name='Edit fields manually').click()
        self.assertEqual(self.field(page,'start_date').input_value(),'2021')
        page.locator('#resume-intake-hide').click();page.locator('#resume-intake-reopen').click()
        self.assertEqual(self.field(page,'start_date').input_value(),'2021')
        self.assertEqual(len(self.catalog.list_items(self.owner)),0)
        self.confirm(page)

    def test_repeated_question_is_suppressed_in_active_flow(self):
        calls=[]
        def provider(context):
            calls.append(context)
            return {'next_question':'What outcome mattered?', 'response':'One useful follow-up.', 'operations':[]}
        self.conversation_service(self.typed_service([]), provider)
        page=self.page();self.input(page)
        page.locator('#resume-intake-text').fill('What useful outcome could I add?');page.locator('#resume-intake-add').click()
        page.locator('#resume-intake-question').get_by_text('What outcome mattered?',exact=True).wait_for()
        page.locator('#resume-intake-skip-question').click()
        page.locator('#resume-intake-optional:visible').wait_for()
        self.assertIn('already covered',page.locator('#resume-intake-status').inner_text())
        self.assertEqual(len(calls),2);self.assertEqual(len(self.catalog.list_items(self.owner)),0)

    def test_latest_answer_is_acknowledged_and_old_suggestions_remain_selectable(self):
        service=self.typed_service([self.role_proposal()])
        page=self.page();self.submit(page,'My first role.')
        service._interpreter=lambda text,kind: [{'kind':'inferred_wording','record_type':'skill',
            'values':{'name':'Systems thinking','summary':'I connect complex systems.'}}]
        self.submit(page,'My new strength.')
        self.assertIn('Systems thinking',page.locator('#resume-intake-proposals').inner_text())
        self.assertIn('I received your answer',page.locator('#resume-intake-suggestion-overview').inner_text())
        page.locator('#resume-intake-suggestion-overview').get_by_role('button',name='Product designer · Northstar Studio',exact=True).click()
        self.assertIn('Northstar Studio',page.locator('#resume-intake-proposals').inner_text())
        self.assertEqual(len(self.catalog.list_items(self.owner)),0)
        page.locator('#resume-intake-suggestion-overview').get_by_role('button',name='Systems thinking',exact=True).click()
        self.confirm(page)
        self.assertEqual(self.catalog.list_items(self.owner)[0]['values']['name'],'Systems thinking')
        self.assertEqual(len(service.get_workspace(self.owner)['pending_proposals']),1)
        self.assertEqual(self.errors,[])

    def test_conversational_correction_proposes_partial_changes_before_confirmation(self):
        from tests.test_resume_onboarding_conversation import operation
        calls=[]
        def provider(context):
            calls.append(context)
            return {'next_question':'', 'response':'I changed the start year.', 'operations':[
                operation(context,ref=context['selected_target'], values={'start_date':'2021-01-01','date_precision':'year'})]}
        service=self.typed_service([self.role_proposal()])
        page=self.pending_conversation_page(service,provider)
        old=service.get_workspace(self.owner)['pending_proposals'][0]
        page.get_by_role('button',name='Change something',exact=True).click()
        page.locator('#resume-intake-text').fill('I started in 2021, not 2022.')
        page.locator('#resume-intake-add').click()
        page.locator('#resume-intake-review:visible').wait_for()
        current=service.get_workspace(self.owner)['pending_proposals'][0]
        self.assertNotEqual(current['proposal_key'],old['proposal_key'])
        self.assertEqual(current['proposed_values']['start_date'],'2021-01-01')
        self.assertEqual(calls[0]['selected_target'],'proposal:'+old['proposal_key'])
        self.assertEqual(len(self.catalog.list_items(self.owner)),0)
        page.reload();page.locator('#resume-intake-review:visible').wait_for()
        self.assertIn('2021',page.locator('#resume-intake-proposals').inner_text())
        self.confirm(page)
        values=self.catalog.list_items(self.owner)[0]['values']
        self.assertEqual((values['start_date'],values['date_precision']),('2021-01-01','year'))
        self.assertEqual(values['employer_name'],'Northstar Studio');self.assertEqual(self.errors,[])

    def test_guided_personal_story_stays_private_and_keeps_canonical_type_unspecified_until_confirmed(self):
        from tests.mvp1_acceptance_support import SharedMvp1Fixture
        shared=SharedMvp1Fixture()
        old=app.config.get('ENTRY_POLICY_SERVICE');self.addCleanup(app.config.__setitem__,'ENTRY_POLICY_SERVICE',old)
        self.catalog=shared.canonical;self.draft_service=shared.draft
        app.config.update(RESUME_DRAFT_SERVICE=shared.draft,ENTRY_POLICY_SERVICE=shared.policy)
        self.typed_service([{'kind':'inferred_wording','record_type':'unspecified',
            'values':{'wording':'I help at a radio repair café outside work.'}}])
        page=self.page();self.input(page)
        self.finish_input(page);page.locator('#resume-intake-add-story').click()
        page.locator('#resume-intake-text').fill('I help at a radio repair café outside work.')
        page.locator('#resume-intake-add').click()
        self.field(page,'wording').wait_for(state='visible')
        self.assertEqual(page.locator('[data-proposal-type]').input_value(),'knowledge')
        self.assertEqual(self.field(page,'classification').input_value(),'personal')
        proposal=app.config['RESUME_INTAKE_SERVICE'].get_workspace(self.owner)['pending_proposals'][0]
        self.assertEqual(proposal['record_type'],'unspecified')
        self.assertEqual(self.catalog.list_items(self.owner),[])
        self.confirm(page)
        item=self.catalog.list_items(self.owner)[0]
        self.assertEqual(item['record_type'],'knowledge')
        self.assertIn('radio repair',item['values']['wording'])
        self.assertFalse(item['resume_display']);self.assertFalse(item['visitor_ai'])
        entry=shared.policy.list_entries(self.owner)['entries'][0]
        self.assertEqual(entry['canonical_type'],'knowledge')
        self.assertEqual(entry['values']['classification'],'personal')
        self.assertFalse(entry['resume_display']);self.assertFalse(entry['visitor_ai'])
        self.assertEqual(self.errors,[])

    def test_correction_failure_retains_words_and_retry_identity_with_newer_input(self):
        from tests.test_resume_onboarding_conversation import operation
        calls=[]
        def provider(context):
            calls.append(context)
            return {'next_question':'','response':'Proposed the year.','operations':[
                operation(context,ref=context['selected_target'],values={'start_date':'2021-01-01','date_precision':'year'})]}
        service=self.typed_service([self.role_proposal()]);page=self.pending_conversation_page(service,provider)
        page.get_by_role('button',name='Change something',exact=True).click()
        def lose_first_response(route):
            page.unroute('**/api/resume-interview/me/turn',lose_first_response)
            response=route.fetch()
            self.assertEqual(response.status,200)
            route.fulfill(status=503,content_type='application/json',body='{"message":"Synthetic response lost after completion."}')
        page.route('**/api/resume-interview/me/turn',lose_first_response)
        original='The start year was 2021.'
        page.locator('#resume-intake-text').fill(original);page.locator('#resume-intake-add').click()
        page.locator('#resume-intake-status').get_by_text('Synthetic response lost',exact=False).wait_for()
        self.assertEqual(page.locator('#resume-intake-text').input_value(),original)
        newer=original+' Keep this later thought too.'
        page.locator('#resume-intake-text').fill(newer);page.locator('#resume-intake-add').click()
        page.wait_for_function("() => document.querySelector('#resume-intake-add-label').textContent === 'Continue'")
        self.assertEqual(len(calls),1)
        self.assertEqual(page.locator('#resume-intake-text').input_value(),newer)
        self.assertEqual(self.catalog.list_items(self.owner),[])
        page.locator('#resume-intake-review-pending').click()
        self.confirm(page)
        self.assertEqual(page.locator('#resume-intake-text').input_value(),newer)
        self.assertEqual(self.catalog.list_items(self.owner)[0]['values']['start_date'],'2021-01-01')

    def test_dictated_correction_uses_the_same_review_and_confirmation_boundary(self):
        from tests.test_resume_onboarding_conversation import operation
        calls=[]
        def provider(context):
            calls.append(context)
            return {'next_question':'','response':'Proposed your contribution.','operations':[
                operation(context,ref=context['selected_target'],values={'summary':'I led a cross-team migration.'})]}
        service=self.typed_service([self.role_proposal()],transcription_adapter=ResumeTranscriptionAdapter(service=self.transcriber))
        page=self.pending_conversation_page(service,provider,mobile=True)
        page.get_by_role('button',name='Change something',exact=True).click()
        self.record(page);page.locator('#resume-intake-mic').click()
        page.wait_for_function("() => document.querySelector('#resume-intake-text').value.includes('cross-team migration')")
        self.assertEqual(self.catalog.list_items(self.owner),[])
        page.locator('#resume-intake-add').click();page.locator('#resume-intake-review:visible').wait_for()
        self.assertIn('cross-team migration',page.locator('#resume-intake-proposals').inner_text())
        self.assertIn(TRANSCRIPT,calls[0]['current_turn']['units'][0]['text'])
        self.assertEqual(self.catalog.list_items(self.owner),[])
        self.confirm(page)
        self.assertEqual(self.catalog.list_items(self.owner)[0]['values']['summary'],'I led a cross-team migration.')
        self.assertEqual(self.errors,[])

    def test_failed_correction_then_manual_confirmation_preserves_newer_words_and_allows_next_correction(self):
        from services.resume_intake_runtime import SynthesisError
        from tests.test_resume_onboarding_conversation import operation
        calls=[]
        def provider(context):
            calls.append(context)
            if len(calls)==1: raise SynthesisError('unavailable')
            return {'next_question':'','response':'Proposed the second year.','operations':[
                operation(context,ref=context['selected_target'],values={'start_date':'2020-01-01','date_precision':'year'})]}
        second=self.role_proposal();second['values']=dict(second['values'],employer_name='Atlas Lab')
        service=self.typed_service([self.role_proposal(),second]);page=self.pending_conversation_page(service,provider)
        page.get_by_role('button',name='Change something',exact=True).click()
        original='The first role started in 2021.'
        page.locator('#resume-intake-text').fill(original);page.locator('#resume-intake-add').click()
        page.locator('#resume-intake-status').get_by_text('could not complete',exact=False).wait_for()
        newer=original+' Keep this later thought too.'
        page.locator('#resume-intake-text').fill(newer);page.locator('#resume-intake-back').click()
        page.get_by_role('button',name='Edit fields manually',exact=True).click()
        self.field(page,'start_date').fill('2021');self.confirm(page)
        self.assertEqual(page.locator('#resume-intake-text').input_value(),newer)
        page.get_by_role('button',name='Continue your unfinished answer',exact=True).click();page.locator('#resume-intake-text').fill('')
        page.locator('#resume-intake-review-pending').click()
        page.get_by_role('button',name='Change something',exact=True).click()
        page.locator('#resume-intake-text').fill('The Atlas role started in 2020.')
        page.locator('#resume-intake-add').click();page.locator('#resume-intake-review:visible').wait_for()
        self.assertIn('2020',page.locator('#resume-intake-proposals').inner_text())
        self.assertNotEqual(calls[0]['selected_target'],calls[1]['selected_target'])
        self.assertEqual(len(self.catalog.list_items(self.owner)),1);self.confirm(page)
        self.assertEqual(len(self.catalog.list_items(self.owner)),2);self.assertEqual(self.errors,[])

    def test_back_from_correction_restores_its_words_when_resumed(self):
        self.typed_service([self.role_proposal()])
        page=self.page();self.submit(page,'Original role.')
        page.get_by_role('button',name='Change something',exact=True).click()
        page.locator('#resume-intake-text').fill('A correction I have not sent.')
        page.locator('#resume-intake-back').click()
        page.get_by_role('button',name='Change something',exact=True).click()
        self.assertEqual(page.locator('#resume-intake-text').input_value(),'A correction I have not sent.')
        self.assertEqual(self.catalog.list_items(self.owner),[])

    def test_reload_recovers_unsent_correction_without_provider_or_canonical_write(self):
        service=self.typed_service([self.role_proposal()])
        calls=[]
        page=self.pending_conversation_page(service,lambda context: calls.append(context))
        page.get_by_role('button',name='Change something',exact=True).click()
        wording='An unsent correction with a limitation: I was not their manager.'
        with page.expect_response(lambda response: response.url.endswith('/draft') and response.request.method=='PUT' and response.status==200):
            page.locator('#resume-intake-text').fill(wording)
        page.reload();page.locator('#resume-intake-input:visible').wait_for()
        self.assertEqual(page.locator('#resume-intake-text').input_value(),wording)
        self.assertIn('change',page.locator('#resume-intake-question').inner_text().lower())
        self.assertEqual(calls,[]);self.assertEqual(self.catalog.list_items(self.owner),[])

    def test_lost_old_draft_acknowledgement_persists_current_turn_key_before_dispatch(self):
        service=self.typed_service([self.role_proposal()]);calls=[];puts=[]
        def provider(context):
            calls.append(context)
            snapshot=self.repository.load_owner(self.owner)
            pending=snapshot['drafts']['composer']['guide_state']['pending_conversation']
            reserved=snapshot['sources'][context['current_turn']['source_key']]['structured_values']['resume_conversation_v1']
            self.assertIsNotNone(pending)
            self.assertEqual(pending['request_id'],reserved['request_id'])
            return {'response':'Which detail should change?','next_question':'','operations':[]}
        page=self.pending_conversation_page(service,provider)
        page.get_by_role('button',name='Change something',exact=True).click()
        def lost_once(route):
            if route.request.method!='PUT': route.continue_();return
            puts.append(route.request.post_data_json)
            response=route.fetch()
            if len(puts)==1:
                route.fulfill(status=503,content_type='application/json',body='{"success":false}')
            else: route.fulfill(response=response)
        page.route('**/api/resume-intake/me/draft',lost_once)
        # Drain the last autosave handler before page()'s context.close cleanup.
        # Preserve handler exceptions rather than leaking them to the next test.
        self.addCleanup(page.unroute_all, behavior='wait')
        page.locator('#resume-intake-text').fill('Which detail should I change?')
        page.locator('#resume-intake-status[data-kind=error]').wait_for()
        page.locator('#resume-intake-add').click()
        page.locator('#resume-intake-question').get_by_text('What would you like to add or change?',exact=True).wait_for()
        self.assertEqual(len(calls),1)
        self.assertEqual(puts[0],puts[1])
        self.assertTrue(any(p['guide_state']['pending_conversation'] is not None for p in puts[2:]))
        self.assertEqual(self.catalog.list_items(self.owner),[])

    def test_asked_question_history_survives_reload_and_suppresses_an_exact_repeat(self):
        service=self.typed_service([self.role_proposal()]);calls=[]
        def provider(context):
            calls.append(context)
            return {'response':'Consider one useful result.','next_question':'What changed for your customers?','operations':[]}
        page=self.pending_conversation_page(service,provider);self.confirm(page)
        page.locator('#resume-intake-next-question').click()
        with page.expect_response(lambda response:response.url.endswith('/draft') and response.request.method=='PUT'
                and 'What changed for your customers?' in (response.request.post_data_json.get('guide_state',{}).get('seen_questions') or [])):
            page.locator('#resume-intake-new-question').click()
            page.locator('#resume-intake-question').get_by_text('What changed for your customers?',exact=True).wait_for()
        page.reload();page.locator('#resume-intake-input:visible').wait_for()
        page.locator('#resume-intake-new-question').click()
        page.locator('#resume-intake-optional:visible').wait_for()
        self.assertEqual(len(calls),2)
        self.assertEqual(len(self.catalog.list_items(self.owner)),1)

    def test_reload_recovers_manual_fields_and_file_descriptor_with_truthful_reattachment(self):
        service=self.typed_service([]);page=self.page();self.input(page)
        with page.expect_response(lambda response: response.url.endswith('/draft') and response.request.method=='PUT' and response.status==200):
            page.locator('#resume-intake-file').set_input_files({'name':'synthetic-resume.txt','mimeType':'text/plain','buffer':b'Skills\nSQL.'})
        self.manual(page)
        page.locator('#resume-intake-type').select_option('role')
        page.locator('#resume-intake-role-title').fill('Engineer')
        page.locator('#resume-intake-employer').fill('Synthetic Labs')
        with page.expect_response(lambda response: response.url.endswith('/draft') and response.request.method=='PUT' and response.status==200):
            page.locator('#resume-intake-role-summary').fill('Coordinated eight people; I was not their manager.')
        page.reload();page.locator('#resume-intake-reopen').wait_for()
        self.manual(page)
        self.assertEqual(page.locator('#resume-intake-role-summary').input_value(),'Coordinated eight people; I was not their manager.')
        self.assertEqual(page.locator('#resume-intake-employer').input_value(),'Synthetic Labs')
        page.locator('#resume-intake-reopen').click()
        self.assertIn('Choose the original file again',page.locator('#resume-intake-attachments').inner_text())
        page.locator('#resume-intake-file').set_input_files({'name':'synthetic-resume.txt','mimeType':'text/plain','buffer':b'Skills\nSQL.'})
        self.assertEqual(page.locator('#resume-intake-attachments > li').count(),1)
        self.assertNotIn('Choose the original file again',page.locator('#resume-intake-attachments').inner_text())
        self.assertEqual(service.get_workspace(self.owner)['source_accounting'],[])
        self.assertEqual(self.catalog.list_items(self.owner),[])

    def test_source_named_project_suggests_the_only_eligible_role_for_explicit_confirmation(self):
        self.typed_service([])
        page=self.page();self.manual(page)
        self.queue(page,'role',role_title='Designer',employer_name='Halcyon Studio')
        self.save_manual(page,1)
        role=self.catalog.list_items(self.owner)[0]
        text='At Halcyon Studio I led the Beacon pilot, reducing review time by 12 percent.'
        from unittest.mock import patch
        create_patch=patch.object(self.catalog,'create_private',wraps=self.catalog.create_private)
        create=create_patch.start();self.addCleanup(create_patch.stop)
        self.typed_service([{'kind':'inferred_wording','record_type':'accomplishment','quote':text,
            'values':{'wording':'Led the Beacon pilot, reducing review time by 12 percent.'}}])
        self.submit(page,text)
        page.wait_for_function("key => document.querySelector('#resume-proposal-parent').value === key",arg=role['record_key'])
        self.assertEqual(len(self.catalog.list_items(self.owner)),1)
        page.get_by_role('button',name='Edit fields manually',exact=True).click()
        self.assertEqual(page.locator('#resume-proposal-parent').input_value(),role['record_key'])
        self.confirm(page)
        contribution=next(row for row in self.catalog.list_items(self.owner) if row['record_type']=='accomplishment')
        self.assertEqual(create.call_args.args[1]['parent_key'],role['record_key'])
        self.assertFalse(contribution['resume_display']);self.assertFalse(contribution['visitor_ai'])

    def test_new_optional_screen_clears_old_validation_and_distinguishes_next_question_from_finish(self):
        self.typed_service([self.role_proposal()])
        page=self.page();self.submit(page,'Original role.')
        page.get_by_role('button',name='Edit fields manually',exact=True).click()
        self.field(page,'employer_name').fill('');page.get_by_role('button',name='Confirm details',exact=True).click()
        self.assertIn('employer',page.locator('#resume-intake-status').inner_text())
        self.input(page);self.finish_input(page)
        self.assertEqual(page.locator('#resume-intake-status').inner_text(),'')
        page.locator('#resume-intake-add-story').click()
        self.assertIn('outside work',page.locator('#resume-intake-question').inner_text())
        self.assertFalse(page.locator('#resume-intake-new-question').is_visible())
        self.assertTrue(page.locator('#resume-intake-input').is_visible())
        self.finish_input(page)
        self.assertTrue(page.locator('#resume-intake-optional').is_visible())
        self.assertEqual(self.catalog.list_items(self.owner),[])

    def test_private_local_credential_months_survive_confirmation_editor_and_direct_preview(self):
        import copy
        from tests.mvp1_acceptance_support import SharedMvp1Fixture
        shared=SharedMvp1Fixture()
        keys=('RESUME_PUBLICATION_SERVICE','PEERSLATE_RESUME_PUBLICATION_ENABLED','ENTRY_POLICY_SERVICE')
        old={key:app.config.get(key) for key in keys};self.addCleanup(app.config.update,old)
        self.catalog=shared.canonical;self.draft_service=shared.draft
        app.config.update(RESUME_DRAFT_SERVICE=shared.draft,RESUME_PUBLICATION_SERVICE=shared.publication,
            PEERSLATE_RESUME_PUBLICATION_ENABLED=True,ENTRY_POLICY_SERVICE=shared.policy)
        values={'name':'Service Design Practitioner','issuer':'Example Institute','completion_status':'completed',
            'issue_date':'2022-06-01','issue_date_precision':'month',
            'expiration_date':'2027-06-01','expiration_date_precision':'month'}
        self.typed_service([{'kind':'inferred_wording','record_type':'credential','values':values}])
        page=self.page();self.submit(page,'My credential was issued June 2022 and expires June 2027.')
        self.assertIn('2022-06',page.locator('#resume-intake-proposals').inner_text())
        self.assertNotIn('2022-06-01',page.locator('#resume-intake-proposals').inner_text())
        self.assertEqual(shared.policy.list_entries(self.owner)['entries'],[])
        page.get_by_role('button',name='Edit fields manually',exact=True).click()
        self.assertEqual(self.field(page,'issue_date').input_value(),'2022-06')
        self.assertEqual(self.field(page,'expiration_date').input_value(),'2027-06')
        self.confirm(page)
        item=self.catalog.list_items(self.owner)[0]
        self.assertEqual((item['values']['issue_date_precision'],item['values']['expiration_date_precision']),('month','month'))
        before=copy.deepcopy(shared.policy.repository.load_owner(self.owner))
        page.locator('#resume-intake-next-finish').click();page.locator('#resume-intake-optional-next').click()
        page.locator('#resume-intake-complete').click()
        page.locator('#resume-intake-view').click()
        # View keeps the earlier composition until its checkpoint and refresh
        # complete. Sample both visible boxes from that completed DOM together.
        geometry=page.wait_for_function("""() => {
            const guide=document.querySelector('#resume-intake');
            const region=document.querySelector('#resume-intake-document');
            const guest=region.querySelector('.resume-publication__guest');
            const status=document.querySelector('#resume-intake-document-status');
            if (guide.open || !guide.hidden || region.hidden ||
                region.getAttribute('aria-busy')!=='false' || !guest ||
                !status.textContent.startsWith('Your actual private Resume preview.') ||
                !region.getClientRects().length || !guest.getClientRects().length ||
                getComputedStyle(region).visibility!=='visible' ||
                getComputedStyle(guest).visibility!=='visible') return null;
            return {document_width:region.getBoundingClientRect().width,
                guest_width:guest.getBoundingClientRect().width};
        }""").json_value()
        content=page.locator('#resume-intake-document-content').inner_text()
        self.assertIn('Issued 2022-06',content);self.assertIn('Expires 2027-06',content)
        self.assertNotIn('2022-06-01',content);self.assertNotIn('2027-06-01',content)
        self.assertGreater(geometry['document_width'],850)
        self.assertGreater(geometry['guest_width'],500)
        for width,height in [(390,844),(320,700),(640,500)]:
            page.set_viewport_size({'width':width,'height':height})
            self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth-innerWidth'),1)
        page.set_viewport_size({'width':1440,'height':1000})
        page.locator('#resume-intake-document').scroll_into_view_if_needed()
        self.capture(page,'runtime-actual-private-credential-preview')
        self.assertEqual(shared.policy.repository.load_owner(self.owner),before)
        self.assertEqual(self.errors,[])

    def test_legacy_resume_choice_has_visible_review_confirmation_and_actual_preview_after_reload(self):
        import copy,json
        from uuid import uuid4
        from tests.mvp1_acceptance_support import SharedMvp1Fixture
        from tests.test_my_data_intake_ai import add_request
        from tests.test_resume_onboarding_conversation import operation
        shared=SharedMvp1Fixture()
        keys=('RESUME_PUBLICATION_SERVICE','PEERSLATE_RESUME_PUBLICATION_ENABLED','ENTRY_POLICY_SERVICE')
        old={key:app.config.get(key) for key in keys};self.addCleanup(app.config.update,old)
        self.catalog=shared.canonical;self.draft_service=shared.draft
        app.config.update(RESUME_DRAFT_SERVICE=shared.draft,RESUME_PUBLICATION_SERVICE=shared.publication,
            PEERSLATE_RESUME_PUBLICATION_ENABLED=True,ENTRY_POLICY_SERVICE=shared.policy)
        service=self.typed_service([])
        added=service.submit(self.owner,add_request(items=[{'client_key':'role','record_type':'role',
            'values':{'role_title':'Engineer','employer_name':'Example Labs',
                'summary':'Coordinated ten people; I was not their manager.\nThe pilot was not independently verified.'},
            'explicit_clears':[]}]))
        key=added['results'][0]['record_key']
        for op in ('exclude_content','restore_content'):
            assistance=self.conversation_service(service,lambda ctx,op=op:{'response':'Review the choice.','next_question':'',
                'operations':[operation(ctx,op=op,ref='record:'+key)]})
            turn=service.converse(self.owner,{'request_id':str(uuid4()),
                'expected_draft_version':shared.draft.get_workspace(self.owner)['draft_version'],
                'statement':'Choose whether to include this entry.','selected_target':'record:'+key,'source_keys':[]},
                assistance=assistance)
            service.decide(self.owner,{'request_id':str(uuid4()),'proposal_key':turn['proposals'][0]['proposal_key'],'decision':'accept'})
        snapshot=service.repository.load_owner(self.owner)
        for row in snapshot['proposals'].values():
            row['resume_conversation_v1'].pop('decision_order');row['decided_at']=None;row['created_at']=None
        snapshot['proposals']=dict(reversed(list(snapshot['proposals'].items())))
        service.repository.save_owner(self.owner,snapshot)
        before=copy.deepcopy(self.catalog.list_items(self.owner))
        page=self.page(expect_guide=False);page.locator('#resume-intake[open]').wait_for()
        page.locator('#resume-intake-history-review').get_by_role('button',name='Include this entry',exact=True).wait_for()
        page.locator('#resume-intake-document-status').get_by_text('Review the saved Resume choices',exact=False).wait_for()
        self.capture(page,'runtime-legacy-choice-needs-review')
        page.locator('#resume-intake-history-review').get_by_role('button',name='Include this entry',exact=True).click()
        page.locator('#resume-intake-review:visible').wait_for()
        self.assertIn('I was not their manager.',page.locator('#resume-intake-proposals').inner_text())
        self.assertIn('not independently verified.',page.locator('#resume-intake-proposals').inner_text())
        self.assertEqual(self.catalog.list_items(self.owner),before)
        page.get_by_role('button',name='Confirm details',exact=True).click()
        page.locator('#resume-intake-status').get_by_text('Saved your current Resume choice.',exact=False).wait_for()
        page.wait_for_function("() => document.querySelector('#resume-intake-history-review').hidden")
        page.locator('#resume-intake-document-content .resume-publication__guest').wait_for(state='attached')
        durable=json.loads(json.dumps(service.repository.load_owner(self.owner),sort_keys=True))
        durable['proposals']=dict(reversed(list(durable['proposals'].items())))
        service.repository.save_owner(self.owner,durable)
        page.reload();page.locator('#resume-intake[open]').wait_for()
        page.locator('#resume-intake-document-content .resume-publication__guest').wait_for(state='attached')
        self.assertTrue(page.locator('#resume-intake-history-review').is_hidden())
        actual=page.locator('#resume-intake-document-content').inner_text()
        self.assertIn('Engineer',actual);self.assertIn('I was not their manager.',actual)
        self.assertIn('not independently verified.',actual)
        self.assertFalse(dict(service.get_workspace(self.owner)['resume_excluded_records'])[key])
        self.assertEqual(self.catalog.list_items(self.owner),before)
        page.locator('#resume-intake-hide').click()
        page.locator('#resume-intake-document').scroll_into_view_if_needed()
        self.capture(page,'runtime-legacy-choice-review-after-reload')
        self.assertEqual(self.errors,[])


    def test_uncertain_words_require_member_type_choice(self):
        page=self.page();self.submit(page,'My unclassified words.')
        self.assertEqual(page.locator('[data-proposal-type]').input_value(),'')
        page.get_by_role('button',name='Confirm details',exact=True).click()
        page.locator('#resume-intake-status').get_by_text('Choose where these words belong',exact=False).wait_for()
        self.assertEqual(len(self.catalog.list_items(self.owner)),0)
        page.locator('[data-proposal-type]').select_option('skill')
        self.field(page,'name').fill('Systems thinking');self.confirm(page)
        self.assertEqual(self.catalog.list_items(self.owner)[0]['values']['name'],'Systems thinking')

    def test_unsorted_words_do_not_become_a_skill_summary_without_member_wording(self):
        source='Explicit document contribution: coordinating a workshop.'
        self.typed_service([{'kind':'inferred_wording','record_type':'unspecified','values':{'text':source}}])
        page=self.page();self.submit(page,source)
        page.locator('[data-proposal-type]').select_option('skill')
        self.field(page,'name').fill('Workshop coordination')
        self.assertEqual(self.field(page,'summary').input_value(),'')
        self.assertIn(source,page.locator('#resume-intake-proposals').inner_text())
        self.confirm(page)
        item=self.catalog.list_items(self.owner)[0]
        self.assertEqual(item['values']['name'],'Workshop coordination')
        self.assertFalse(item['values'].get('summary'))
        self.assertFalse(item['resume_display']);self.assertFalse(item['visitor_ai'])

    BATCH_TEXT = ('Experience\nEngineer, Alpha Labs.\nBuilt data pipelines.\nLed a team of four.\n'
            'Analyst, Beta Corp.\nWrote weekly reports.\nSkills\nSQL.\nPython.')

    # -- fixtures -------------------------------------------------------------

    def batch_payload(self, *, flawed=False):
        from tests.test_resume_onboarding_coverage import complete_resume_candidate
        units = [u for u in inventory_source(self.BATCH_TEXT, document=True) if u['kind'] == 'content']
        by_text = {u['text']: u for u in units}
        def pick(*texts):
            return [by_text[t] for t in texts]
        role_a = pick('Engineer, Alpha Labs.', 'Built data pipelines.', 'Led a team of four.')
        role_b = pick('Analyst, Beta Corp.', 'Wrote weekly reports.')
        candidates = [
            complete_resume_candidate('role', {'role_title': 'Engineer', 'employer_name': 'Alpha Labs'}, role_a[0]['text'], role_a, 'Experience'),
            complete_resume_candidate('role', {'role_title': 'Analyst', 'employer_name': 'Beta Corp'}, role_b[0]['text'], role_b, 'Experience'),
            complete_resume_candidate('skill', {'name': 'SQL'}, 'SQL.', pick('SQL.'), 'Skills'),
            complete_resume_candidate('skill', {'name': 'Python'}, 'Python.', pick('Python.'), 'Skills'),
        ]
        if flawed:
            candidates[3]['quote'] = 'A passage the source never contains.'
        return {'candidates': candidates}

    def batch_service(self, provider=None):
        from services.my_data_extraction_adapter import MyDataExtractionAdapter
        from tests.test_my_data_intake_sources import extracted_pipeline
        service = ResumeIntakeService(
            repository=self.repository, draft_service=self.draft_service, policy=selected_policy_for_tests(),
            document_adapter=ResumeDocumentAdapter(), document_pipeline=extracted_pipeline(self.BATCH_TEXT),
            extraction_adapter=MyDataExtractionAdapter(provider=provider))
        app.config['RESUME_INTAKE_SERVICE'] = service
        self.calls = []
        return service

    def batch_upload(self, service):
        from tests.test_my_data_intake_ai import add_request
        from tests.test_my_data_intake_sources import FakeUpload
        return service.submit(self.owner, add_request(attachments=[{'client_key': 'doc', 'kind': 'document',
            'declared_content_type': 'text/plain', 'filename': 'resume.txt'}]),
            files={'doc': FakeUpload('text/plain', self.BATCH_TEXT.encode())})

    def batch_counting(self, payload):
        def provider(request, **options):
            self.calls.append(request)
            return payload
        return provider

    # -- the batch ----------------------------------------------------------------

    CONTRAST_SCRIPT = """(selector) => {
        const parse = (value) => value.match(/[0-9.]+/g).map(Number);
        const luminance = ([r, g, b]) => {
            const f = (c) => { c /= 255; return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); };
            return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
        };
        const ratio = (a, b) => { const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x); return (hi + 0.05) / (lo + 0.05); };
        const element = document.querySelector(selector);
        const ink = parse(getComputedStyle(element).color).slice(0, 3);
        // The guide's surfaces are white or ivory; the darkest of them is the honest worst case.
        return Math.min(ratio(ink, [255, 255, 255]), ratio(ink, [251, 248, 241]), ratio(ink, [255, 253, 248]));
    }"""

    def assert_contrast(self, page, selector):
        self.assertGreaterEqual(page.evaluate(self.CONTRAST_SCRIPT, selector), 4.5, selector)

    def test_overview_counts_one_complete_role_and_the_details_it_could_not_place(self):
        service = self.batch_service(self.batch_counting(self.batch_payload(flawed=True)))
        self.batch_upload(service)
        page = self.page()
        page.locator('#resume-intake-review:visible').wait_for()
        batch = page.locator('#resume-intake-batch')
        batch.wait_for()
        text = batch.inner_text()
        self.assertIn('I organized your résumé: 2 roles · 1 skill.', text)
        self.assertIn('1 detail I couldn’t place', text)
        self.assertNotIn('groups to review', page.locator('#resume-intake-review-position').inner_text())
        self.assertEqual(page.locator('#resume-intake-review-position').inner_text(), 'Experience · 1 of 2')
        lines = page.locator('.resume-intake__lines li')
        lines.nth(2).wait_for()
        self.assertEqual(lines.count(), 3)
        self.assertIn('resume-intake__line--header', lines.nth(0).get_attribute('class'))
        self.assertEqual(lines.nth(2).inner_text(), 'Led a team of four.')
        self.assertEqual(page.get_by_role('button', name='Confirm details', exact=True).count(), 1)
        self.assertEqual(self.catalog.list_items(self.owner), [])
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.errors, [])
        for selector in ('.resume-intake__quiet', '.resume-intake__proposal-source', '.resume-intake__footer p'):
            self.assert_contrast(page, selector)

    def test_loose_details_open_one_at_a_time_and_earlier_work_stays_behind_its_own_link(self):
        service = self.batch_service(self.batch_counting(self.batch_payload(flawed=True)))
        from tests.test_my_data_intake_ai import add_request
        service.submit(self.owner, add_request(text='An older note from an earlier visit.'))
        self.batch_upload(service)
        page = self.page()
        page.locator('#resume-intake-batch').wait_for()
        self.assertEqual(page.locator('[data-earlier-items]').inner_text(), 'Earlier unfinished items (1)')
        self.assertNotIn('older note', page.locator('#resume-intake-proposals').inner_text())
        page.locator('.resume-intake__loose summary').click()
        self.assertEqual(page.locator('[data-loose-key]').count(), 1)
        page.locator('[data-loose-key]').click()
        page.locator('#resume-intake-proposals').get_by_text('Python.', exact=False).first.wait_for()
        page.locator('[data-earlier-items]').click()
        page.locator('#resume-intake-batch').get_by_text('Earlier unfinished items', exact=True).wait_for()
        self.assertIn('older note', page.locator('#resume-intake-proposals').inner_text())
        page.get_by_role('button', name='Back to your uploaded résumé', exact=True).click()
        page.locator('#resume-intake-batch').get_by_text('Your uploaded résumé', exact=True).wait_for()
        self.assertEqual(self.catalog.list_items(self.owner), [])

    def test_unavailable_organizer_offers_retry_and_a_retry_regroups_the_stored_source(self):
        service = self.batch_service(None)
        self.batch_upload(service)
        page = self.page()
        page.locator('#resume-intake-review:visible').wait_for()
        card = page.locator('#resume-intake-batch')
        card.get_by_text('I read your résumé but couldn’t organize it right now. Nothing is lost.').wait_for()
        self.assertEqual(page.locator('#resume-intake-proposals li').count(), 0)
        service._extraction_adapter._provider = self.batch_counting(self.batch_payload())
        page.get_by_role('button', name='Try organizing again', exact=True).click()
        card.get_by_text('I organized your résumé: 2 roles · 2 skills.').wait_for()
        self.assertEqual(len(self.calls), 1)
        page.locator('.resume-intake__lines li').nth(2).wait_for()
        self.assertEqual(page.locator('.resume-intake__lines li').count(), 3)
        self.assertEqual(page.get_by_role('button', name='Try organizing again').count(), 0)
        self.assertEqual(self.catalog.list_items(self.owner), [])

    def test_the_same_file_is_not_stored_or_dispatched_twice(self):
        service = self.batch_service(self.batch_counting(self.batch_payload()))
        self.batch_upload(service)
        page = self.page()
        page.locator('#resume-intake-review:visible').wait_for()
        page.locator('[data-add-more]').click()
        page.locator('#resume-intake-input:visible').wait_for()
        page.locator('#resume-intake-file').set_input_files(
            {'name': 'resume.txt', 'mimeType': 'text/plain', 'buffer': self.BATCH_TEXT.encode()})
        page.locator('#resume-intake-add').click()
        page.locator('#resume-intake-review').get_by_text('You’ve already uploaded this file.', exact=False).wait_for()
        self.assertEqual(len(self.calls), 1)
        snapshot = self.repository.load_owner(self.owner)
        self.assertEqual(len([s for s in snapshot['sources'].values() if s['kind'] == 'document']), 1)

    # -- pause ------------------------------------------------------------------------

    def test_pause_waits_for_the_save_and_the_status_and_says_only_what_happened(self):
        service = self.batch_service(self.batch_counting(self.batch_payload()))
        self.batch_upload(service)
        page = self.page()
        page.locator('#resume-intake-review:visible').wait_for()
        notice = page.locator('#resume-intake-pause-notice')
        # Unsent words make the checkpoint real. The draft cannot be saved: the dialog stays,
        # the failure is visible, and nothing says paused.
        page.evaluate("() => { const box = document.getElementById('resume-intake-text'); box.value = 'Words not sent yet.'; box.dispatchEvent(new Event('input', {bubbles: true})); }")
        page.route('**/api/resume-intake/me/draft', lambda route: route.abort() if route.request.method == 'PUT' else route.continue_())
        page.get_by_role('button', name='Pause', exact=True).click()
        page.locator('#resume-intake-pause-failure').wait_for()
        self.assertTrue(page.locator('#resume-intake[open]').count())
        self.assertEqual(page.locator('#resume-intake-pause-notice').count(), 0)
        page.unroute('**/api/resume-intake/me/draft')
        # The draft saves but the pause is not recorded: say exactly that, and retry works.
        page.route('**/api/resume-intake/me/guide/status', lambda route: route.fulfill(status=503, body='{}', content_type='application/json'))
        page.get_by_role('button', name='Try again', exact=True).click()
        notice.wait_for()
        notice.get_by_text('Draft saved, but pausing wasn’t recorded.', exact=False).wait_for()
        self.assertNotIn('Paused.', notice.inner_text())
        page.unroute('**/api/resume-intake/me/guide/status')
        notice.get_by_role('button', name='Retry', exact=True).click()
        notice.get_by_text('Paused. Your draft is saved privately.', exact=True).wait_for()
        self.assertFalse(page.locator('#resume-intake[open]').count())

    def test_escape_and_the_close_button_are_the_same_truthful_pause(self):
        service = self.batch_service(self.batch_counting(self.batch_payload()))
        self.batch_upload(service)
        page = self.page()
        page.locator('#resume-intake-review:visible').wait_for()
        page.keyboard.press('Escape')
        notice = page.locator('#resume-intake-pause-notice')
        notice.get_by_text('Paused. Your draft is saved privately.', exact=True).wait_for()
        # The notice floats: it neither shifts the fixed reopen button nor blocks the page beneath it.
        self.assertEqual(notice.evaluate("el => [getComputedStyle(el).position, getComputedStyle(el).pointerEvents]"),
                         ['absolute', 'none'])
        page.locator('#resume-intake-reopen').click()
        page.locator('#resume-intake[open]').wait_for()
        page.locator('#resume-intake-hide').click()
        page.locator('#resume-intake-pause-notice').get_by_text('Paused. Your draft is saved privately.', exact=True).wait_for()

    @staticmethod
    def boxes_overlap(first, second):
        return not (first['x'] + first['width'] <= second['x'] or second['x'] + second['width'] <= first['x']
                    or first['y'] + first['height'] <= second['y'] or second['y'] + second['height'] <= first['y'])

    def batch_clocked_page(self, width, height):
        """A page whose timers can be fast-forwarded, so a 15 second clear needs no real wait."""
        context = self.browser.new_context(viewport={'width': width, 'height': height})
        self.addCleanup(context.close)
        page = context.new_page()
        page.set_default_timeout(7000)
        page.route('https://fonts.**', lambda route: route.abort())
        page.clock.install()
        self.errors = []
        page.on('pageerror', lambda error: self.errors.append(str(error)))
        page.goto(self.base_url + '/app/resume')
        page.locator('#resume-intake[open]').wait_for()
        return page

    def test_pause_notice_never_covers_the_reopen_or_photo_buttons_and_retry_is_reachable(self):
        for width, height in ((1440, 1000), (390, 844)):
            self.owner = 'notice-%d-%s' % (width, self._testMethodName)
            app.config.update(PEERSLATE_DEV_USER_KEY=self.owner)
            service = self.batch_service(self.batch_counting(self.batch_payload()))
            self.batch_upload(service)
            page = self.page(width, height)
            page.locator('#resume-intake-review:visible').wait_for()
            page.route('**/api/resume-intake/me/guide/status',
                       lambda route: route.fulfill(status=503, body='{}', content_type='application/json'))
            page.get_by_role('button', name='Pause', exact=True).click()
            notice = page.locator('#resume-intake-pause-notice')
            notice.get_by_text('Draft saved, but pausing wasn’t recorded.', exact=False).wait_for()
            self.assertEqual(notice.get_attribute('role'), 'status')
            box = notice.bounding_box()
            self.assertFalse(self.boxes_overlap(box, page.locator('#resume-intake-reopen').bounding_box()), (width, 'reopen'))
            media = page.locator('#resume-media button:visible')
            for index in range(media.count()):
                self.assertFalse(self.boxes_overlap(box, media.nth(index).bounding_box()), (width, 'photo button', index))
            retry = notice.get_by_role('button', name='Retry', exact=True)
            retry.focus(); page.keyboard.press('Shift+Tab'); page.keyboard.press('Tab')
            self.assertEqual(page.evaluate('document.activeElement.textContent'), 'Retry')
            style, thickness = retry.evaluate("el => [getComputedStyle(el).outlineStyle, parseFloat(getComputedStyle(el).outlineWidth)]")
            self.assertNotEqual(style, 'none')
            self.assertGreaterEqual(thickness, 2)
            where = retry.bounding_box()
            self.assertTrue(where['x'] >= 0 and where['x'] + where['width'] <= width, width)
            self.assertEqual(retry.evaluate("el => getComputedStyle(el).pointerEvents"), 'auto')
            self.assertEqual(self.errors, [])

    def test_only_a_fully_successful_pause_notice_clears_itself(self):
        service = self.batch_service(self.batch_counting(self.batch_payload()))
        self.batch_upload(service)
        page = self.batch_clocked_page(1440, 1000)
        page.locator('#resume-intake-review:visible').wait_for()
        notice = page.locator('#resume-intake-pause-notice')
        page.keyboard.press('Escape')
        notice.get_by_text('Paused. Your draft is saved privately.', exact=True).wait_for()
        page.clock.fast_forward(16000)
        notice.wait_for(state='hidden')
        # A save that fails and is closed anyway leaves a notice about unsaved changes: it must stay.
        page.locator('#resume-intake-reopen').click()
        page.locator('#resume-intake[open]').wait_for()
        page.evaluate("() => { const box = document.getElementById('resume-intake-text'); box.value = 'Words not saved.'; box.dispatchEvent(new Event('input', {bubbles: true})); }")
        page.route('**/api/resume-intake/me/draft', lambda route: route.abort() if route.request.method == 'PUT' else route.continue_())
        page.get_by_role('button', name='Pause', exact=True).click()
        page.get_by_role('button', name='Close anyway', exact=True).click()
        notice.get_by_text('Closed. Your last saved draft is kept', exact=False).wait_for()
        page.clock.fast_forward(60000)
        self.assertTrue(notice.is_visible())
        self.assertIn('Closed. Your last saved draft is kept', notice.inner_text())

    # -- phone --------------------------------------------------------------------------

    def test_phone_sheet_fills_the_screen_and_the_last_action_stays_reachable(self):
        service = self.batch_service(self.batch_counting(self.batch_payload()))
        self.batch_upload(service)
        page = self.page(390, 844)
        page.locator('#resume-intake-review:visible').wait_for()
        box = page.locator('#resume-intake').bounding_box()
        self.assertEqual((round(box['x']), round(box['y']), round(box['width']), round(box['height'])), (0, 0, 390, 844))
        self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth'), 390)
        page.locator('#resume-intake-guide').evaluate('el => { el.scrollTop = el.scrollHeight; }')
        confirm = page.get_by_role('button', name='Confirm details', exact=True)
        confirm.scroll_into_view_if_needed()
        action = confirm.bounding_box()
        self.assertGreaterEqual(action['y'], 0)
        self.assertLessEqual(action['y'] + action['height'], 844)
        pause = page.get_by_role('button', name='Pause', exact=True).bounding_box()
        self.assertGreaterEqual(pause['height'], 44)
        self.assertEqual(self.errors, [])


if __name__ == '__main__':
    unittest.main()
