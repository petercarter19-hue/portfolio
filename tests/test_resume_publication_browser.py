"""Browser journeys for owner review/publish and guest reads.

Playwright drives pinned Chromium against a locally served Flask app using
real application adapters. Ordinary discovery may skip when Playwright or
Chrome is unavailable. This is not SQL engine proof or live identity proof.
"""

from __future__ import annotations

import os
import threading
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from werkzeug.serving import make_server

from services.entry_policy_repository import InMemoryEntryPolicyRepository
from services.entry_policy_service import EntryPolicyService
from services.resume_media_catalog_repository import InMemoryResumeCatalogRepository
from services.resume_media_repository import CatalogAssetRecord
from services.resume_publication_service import memory_resume_publication_service

try:
    from playwright.sync_api import sync_playwright
except ModuleNotFoundError:  # pragma: no cover
    sync_playwright = None

try:
    from scripts.capture_ps_journal_j1_evidence import _resolve_chrome

    CHROME_EXECUTABLE = os.environ.get("PEERSLATE_CHROME") or _resolve_chrome()
except Exception:  # pragma: no cover
    CHROME_EXECUTABLE = os.environ.get("PEERSLATE_CHROME")


def _create_role(policy, owner, summary="Led team 0.", display=True, visitor_ai=False):
    entry_key = str(uuid4())
    policy.commit(
        owner,
        {
            "type": "create",
            "request_id": str(uuid4()),
            "entry_key": entry_key,
            "canonical_type": "role",
            "values": {
                "role_title": "Lead",
                "employer_name": "PeerSlate",
                "summary": summary,
            },
        },
    )
    listed = policy.list_entries(owner)["entries"]
    created = next(item for item in listed if item["entry_key"] == entry_key)
    policy.commit(
        owner,
        {
            "type": "change_permissions",
            "request_id": str(uuid4()),
            "entry_key": entry_key,
            "expected_access_revision": created["access_revision"],
            "permissions": {"resume_display": display, "visitor_ai": visitor_ai},
        },
    )
    return entry_key


@unittest.skipUnless(sync_playwright and CHROME_EXECUTABLE, "pinned Chromium is unavailable")
class ResumePublicationBrowserTests(unittest.TestCase):
    def test_direct_private_preview_includes_private_facts_without_permission_or_provider_mutation(self):
        import copy
        original_flag=self.app.config.get('PEERSLATE_MEMBER_VISITOR_AI_ENABLED')
        self.app.config['PEERSLATE_MEMBER_VISITOR_AI_ENABLED']=True
        self.addCleanup(self.app.config.__setitem__,'PEERSLATE_MEMBER_VISITOR_AI_ENABLED',original_flag)
        key=_create_role(self.policy,self.owner,summary='Direct private draft.',display=False,visitor_ai=False)
        before=(copy.deepcopy(self.policy.repository.load_owner(self.owner)),
                copy.deepcopy(self.service.repository.load_owner(self.owner)))
        page=self._owner_page();self.addCleanup(page.close)
        provider_requests=[]
        page.on('request',lambda request: provider_requests.append(request.url)
            if '/visitor-ai/' in request.url or '/resume-synthesis/' in request.url else None)
        page.goto(f'{self._origin()}/app/resume/publication?preview=private')
        page.locator('#resume-private-preview:not([hidden]) .resume-publication__guest').wait_for()
        self.assertIn('Direct private draft.',page.locator('#resume-private-preview-content').inner_text())
        self.assertTrue(page.locator(f'[data-entry-key="{key}"] [data-permission="resume_display"]').is_checked())
        self.assertFalse(page.locator('#resume-publication-publish-button').is_visible())
        self.assertFalse(page.locator('#visitor-ai-panel').is_visible())
        self.assertEqual(page.locator('#visitor-ai-panel,#visitor-ai-open').count(),0)
        self.assertFalse(page.locator(f'[data-entry-key="{key}"] [data-permission="visitor_ai"]').is_visible())
        self.assertEqual(provider_requests,[])
        self.assertEqual(before,(self.policy.repository.load_owner(self.owner),self.service.repository.load_owner(self.owner)))

    def test_private_composition_preview_uses_temporary_choices_and_returns_keyboard_focus(self):
        import copy
        key = _create_role(self.policy,self.owner,summary="Private preview-only wording.",display=False,visitor_ai=False)
        row=next(item for item in self.policy.list_entries(self.owner)["entries"] if item["entry_key"]==key)
        self.policy.commit(self.owner,{"type":"edit","request_id":str(uuid4()),"entry_key":key,
            "expected_content_version":row["content_version"],"expected_access_revision":row["access_revision"],
            "values":{"role_title":"Lead","employer_name":"PeerSlate","summary":"Private preview-only wording.",
                "date_precision":"month","start_date":"2022-03-01","current_role":True}})
        before = (copy.deepcopy(self.policy.repository.load_owner(self.owner)),
                  copy.deepcopy(self.service.repository.load_owner(self.owner)))
        page = self._owner_page()
        self.addCleanup(page.close)
        page.goto(f"{self._origin()}/app/resume/publication")
        page.locator("#resume-publication-review-button").click()
        page.locator("#resume-publication-digest:not([hidden])").wait_for()
        self.assertNotIn("2022-03-01",page.locator(f'[data-entry-key="{key}"]').inner_text())
        self.assertIn("2022-03",page.locator(f'[data-entry-key="{key}"]').inner_text())
        page.locator(f'[data-entry-key="{key}"] [data-permission="resume_display"]').check()
        page.locator("#resume-publication-review-button").click()
        page.locator("#resume-publication-digest:not([hidden])").wait_for()
        page.locator("#resume-publication-preview-button").focus()
        page.keyboard.press("Enter")
        page.locator("#resume-private-preview:not([hidden]) .resume-publication__guest").wait_for()
        self.assertIn("Private preview-only wording.",page.locator("#resume-private-preview-content").inner_text())
        self.assertIn("Nothing is published",page.locator("#resume-private-preview-content").inner_text())
        self.assertEqual(page.evaluate("document.activeElement.id"),"resume-preview-title")
        self.assertEqual(before,(self.policy.repository.load_owner(self.owner),self.service.repository.load_owner(self.owner)))
        # The composition occupies the page width, outside the narrow owner/AI rail.
        page.set_viewport_size({"width":320,"height":740})
        self.assertGreater(page.locator("#resume-private-preview-content .resume-publication__timeline").bounding_box()["width"],200)
        self.assertLessEqual(page.evaluate("document.documentElement.scrollWidth"),320)
        page.keyboard.press("Escape")
        self.assertFalse(page.locator("#resume-private-preview").is_visible())
        self.assertEqual(page.evaluate("document.activeElement.id"),"resume-publication-preview-button")
        page.locator(f'[data-entry-key="{key}"] [data-permission="resume_display"]').uncheck()
        self.assertFalse(page.locator("#resume-publication-preview-button").is_disabled())
        page.locator("#resume-publication-preview-button").click()
        page.locator("#resume-private-preview:not([hidden])").wait_for()
        self.assertNotIn("Private preview-only wording.",page.locator("#resume-private-preview-content").inner_text())
        self.assertEqual(before,(self.policy.repository.load_owner(self.owner),self.service.repository.load_owner(self.owner)))

    @classmethod
    def setUpClass(cls):
        from app import app

        cls.app = app
        cls.policy = EntryPolicyService(repository=InMemoryEntryPolicyRepository())
        cls.catalog = InMemoryResumeCatalogRepository()
        cls.service = memory_resume_publication_service(catalog=cls.catalog)
        cls.policy.publication_service = cls.service
        cls.service.policy_service = cls.policy
        cls.owner = "member-a"
        cls.other = "member-b"
        cls.service.bind_slug(cls.owner, "alice")
        cls.service.bind_slug(cls.other, "bob")
        cls.entry_key = _create_role(cls.policy, cls.owner)
        _create_role(cls.policy, cls.other, summary="Owner B private fact.")
        cls.original = {
            key: app.config.get(key)
            for key in (
                "TESTING",
                "PEERSLATE_ALLOW_DEV_IDENTITY",
                "PEERSLATE_DEV_USER_KEY",
                "PEERSLATE_TRUST_EASYAUTH_HEADERS",
                "PEERSLATE_RESUME_PUBLICATION_ENABLED",
                "RESUME_PUBLICATION_SERVICE",
            )
        }
        app.config.update(
            TESTING=True,
            PEERSLATE_ALLOW_DEV_IDENTITY=True,
            PEERSLATE_DEV_USER_KEY=cls.owner,
            PEERSLATE_TRUST_EASYAUTH_HEADERS=False,
            PEERSLATE_RESUME_PUBLICATION_ENABLED=True,
            RESUME_PUBLICATION_SERVICE=cls.service,
        )
        cls.server = make_server("127.0.0.1", 0, app, threaded=True)
        cls.port = cls.server.server_port
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(
            headless=True,
            executable_path=str(CHROME_EXECUTABLE),
        )

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        cls.server.shutdown()
        cls.app.config.update(cls.original)

    def _origin(self):
        return f"http://127.0.0.1:{self.port}"

    def _owner_page(self):
        return self.browser.new_page()

    def _guest_page(self):
        context = self.browser.new_context()
        return context.new_page()

    def test_owner_review_publish_guest_sees_result_and_sharing_off_denies(self):
        origin = self._origin()
        page = self._owner_page()
        page.goto(f"{origin}/app/resume/publication")
        self.assertIn("Review without publishing", page.content())
        page.fill("#resume-publication-slug", "alice")
        page.click("#resume-publication-review-button")
        page.wait_for_selector("#resume-publication-digest:not([hidden])")
        page.click("#resume-publication-publish-button")
        page.wait_for_function(
            "() => document.getElementById('resume-publication-status').textContent.includes('Published')"
        )
        guest = self._guest_page()
        guest.goto(f"{origin}/alice/resume")
        self.assertIn("Published Resume", guest.content())
        self.assertIn("Led team 0.", guest.locator(".resume-publication__guest").inner_text())
        self.assertIn("Explore the experience this member has chosen to share.", guest.locator(".resume-publication--public").inner_text())
        page.click("#resume-publication-sharing-off-button")
        page.wait_for_function(
            "() => document.getElementById('resume-publication-status').textContent.includes('Sharing is off')"
        )
        denied = self._guest_page()
        response = denied.goto(f"{origin}/alice/resume")
        self.assertEqual(response.status, 404)
        page.close()
        guest.close()
        denied.close()

    def test_keyboard_review_control_is_operable(self):
        origin = self._origin()
        page = self._owner_page()
        page.goto(f"{origin}/app/resume/publication")
        page.focus("#resume-publication-review-button")
        page.keyboard.press("Enter")
        page.wait_for_selector("#resume-publication-digest:not([hidden])")
        page.close()

    def test_owner_guest_contexts_permission_combinations_draft_isolation_and_corrections(self):
        origin = self._origin()
        owner = self._owner_page()
        guest = self._guest_page()
        combinations = (
            (True, False),
            (False, True),
            (False, False),
            (True, True),
        )
        for display, visitor_ai in combinations:
            owner.goto(f"{origin}/app/resume/publication")
            digest = owner.evaluate(
                """async ({display, visitorAi, entryKey}) => {
                    const headers = {
                        'Content-Type': 'application/json',
                        'X-PeerSlate-Request': 'same-origin',
                    };
                    const review = await (await fetch('/api/resume-publication/me/review', {
                        method: 'POST', credentials: 'same-origin', headers,
                        body: JSON.stringify({
                            entries: [{entry_key: entryKey, resume_display: display, visitor_ai: visitorAi}],
                        }),
                    })).json();
                    const published = await (await fetch('/api/resume-publication/me/commands', {
                        method: 'POST', credentials: 'same-origin', headers,
                        body: JSON.stringify({
                            type: 'publish',
                            request_id: crypto.randomUUID(),
                            reviewed_digest: review.digest,
                            slug: 'alice',
                        }),
                    })).json();
                    return {review, published};
                }""",
                {"display": display, "visitorAi": visitor_ai, "entryKey": self.entry_key},
            )
            self.assertTrue(digest["review"]["success"])
            self.assertTrue(digest["published"]["success"])
            guest_response = guest.goto(f"{origin}/alice/resume")
            text = guest.locator(".resume-publication__guest").inner_text() if guest_response.status == 200 else ""
            if display:
                self.assertEqual(guest_response.status, 200)
                self.assertIn("Led team 0.", text)
            else:
                if guest_response.status == 200:
                    self.assertNotIn("Led team 0.", text)
            api = guest.evaluate(
                """async () => {
                    const response = await fetch('/api/public/profiles/alice/living-resume');
                    return {status: response.status, body: await response.json()};
                }"""
            )
            if api["status"] == 200:
                self.assertNotIn("visitor_ai", api["body"].get("living_resume") or {})
            bob = guest.goto(f"{origin}/bob/resume")
            self.assertEqual(bob.status, 404)
        snapshot = self.service.repository.load_owner(self.owner)
        snapshot["private_draft"] = {"summary": "Owner-only draft overlay"}
        self.service.repository.save_owner(self.owner, snapshot)
        before = guest.goto(f"{origin}/alice/resume")
        self.assertEqual(before.status, 200)
        owner.evaluate(
            """async ({entryKey}) => {
                const headers = {
                    'Content-Type': 'application/json',
                    'X-PeerSlate-Request': 'same-origin',
                };
                return (await fetch('/api/resume-publication/me/commands', {
                    method: 'POST', credentials: 'same-origin', headers,
                    body: JSON.stringify({
                        type: 'correct',
                        request_id: crypto.randomUUID(),
                        entry_key: entryKey,
                        values: {summary: 'Led a larger team.'},
                        canonical_type: 'role',
                    }),
                })).json();
            }""",
            {"entryKey": self.entry_key},
        )
        guest.goto(f"{origin}/alice/resume")
        self.assertIn("Led a larger team.", guest.locator(".resume-publication__guest").inner_text())
        owner.close()
        guest.close()

    def test_stale_publish_replay_conflict_private_restore_and_media_revocation(self):
        origin = self._origin()
        owner = self._owner_page()
        guest = self._guest_page()
        owner.goto(f"{origin}/app/resume/publication")
        first = owner.evaluate(
            """async () => {
                const headers = {
                    'Content-Type': 'application/json',
                    'X-PeerSlate-Request': 'same-origin',
                };
                const review = await (await fetch('/api/resume-publication/me/review', {
                    method: 'POST', credentials: 'same-origin', headers, body: JSON.stringify({}),
                })).json();
                const requestId = crypto.randomUUID();
                const payload = {
                    type: 'publish',
                    request_id: requestId,
                    reviewed_digest: review.digest,
                    slug: 'alice',
                };
                const published = await (await fetch('/api/resume-publication/me/commands', {
                    method: 'POST', credentials: 'same-origin', headers, body: JSON.stringify(payload),
                })).json();
                const replay = await (await fetch('/api/resume-publication/me/commands', {
                    method: 'POST', credentials: 'same-origin', headers, body: JSON.stringify(payload),
                })).json();
                const conflict = await (await fetch('/api/resume-publication/me/commands', {
                    method: 'POST', credentials: 'same-origin', headers,
                    body: JSON.stringify({...payload, slug: 'changed'}),
                })).json();
                const stale = await (await fetch('/api/resume-publication/me/commands', {
                    method: 'POST', credentials: 'same-origin', headers,
                    body: JSON.stringify({
                        type: 'publish',
                        request_id: crypto.randomUUID(),
                        reviewed_digest: review.digest,
                        slug: 'alice',
                        expected_publication_revision: 0,
                    }),
                })).json();
                return {published, replay, conflict, stale};
            }"""
        )
        self.assertTrue(first["published"]["success"])
        self.assertTrue(first["replay"]["replayed"])
        self.assertFalse(first["conflict"].get("success", True))
        self.assertFalse(first["stale"].get("success", True))
        owner.evaluate(
            """async ({entryKey}) => {
                const headers = {
                    'Content-Type': 'application/json',
                    'X-PeerSlate-Request': 'same-origin',
                };
                await fetch('/api/resume-publication/me/commands', {
                    method: 'POST', credentials: 'same-origin', headers,
                    body: JSON.stringify({type: 'delete', request_id: crypto.randomUUID(), entry_key: entryKey}),
                });
                return (await fetch('/api/resume-publication/me/commands', {
                    method: 'POST', credentials: 'same-origin', headers,
                    body: JSON.stringify({type: 'restore', request_id: crypto.randomUUID(), entry_key: entryKey}),
                })).json();
            }""",
            {"entryKey": self.entry_key},
        )
        guest.goto(f"{origin}/alice/resume")
        self.assertNotIn(self.entry_key, guest.content())
        record = CatalogAssetRecord(
            "asset-1", 2, "a" * 64, "Leadership", "concept", ("Teamwork",), 1800, 600
        )
        self.catalog.put(record)
        owner.evaluate(
            """async () => {
                const headers = {
                    'Content-Type': 'application/json',
                    'X-PeerSlate-Request': 'same-origin',
                };
                await fetch('/api/resume-publication/me/commands', {
                    method: 'POST', credentials: 'same-origin', headers,
                    body: JSON.stringify({
                        type: 'catalog_withdraw',
                        request_id: crypto.randomUUID(),
                        asset_id: 'asset-1',
                        version: 2,
                    }),
                });
                return (await fetch('/api/resume-publication/me/commands', {
                    method: 'POST', credentials: 'same-origin', headers,
                    body: JSON.stringify({
                        type: 'media_restrict',
                        request_id: crypto.randomUUID(),
                        slot: 'story_banner',
                    }),
                })).json();
            }"""
        )
        media = guest.goto(f"{origin}/alice/resume/media/story_banner")
        self.assertEqual(media.status, 404)
        alias = guest.goto(f"{origin}/alice/resume2/media/story_banner")
        self.assertIn(alias.status, (302, 404))
        owner.close()
        guest.close()


    @contextmanager
    def _visitor_fixture(self):
        from flask import request
        from identity import AuthenticationRequired, PeerSlateIdentity
        from tests.test_resume_publication_routes import visitor_http_stack
        from services.member_visitor_ai_service import ApprovedMemberName
        from services.resume_publication_contracts import ReadState, UsePurpose
        db, repo, provider, service, runtime = visitor_http_stack(requests_per_client_window=100,
            aggregate_cost_units_per_window=1000, timeout_seconds=5)
        publication = memory_resume_publication_service()
        policy = EntryPolicyService(repository=InMemoryEntryPolicyRepository())
        publication.policy_service = policy
        policy.publication_service = publication
        publication.bind_slug('member-a', 'alice')
        _create_role(policy, 'member-a', summary='Public experience summary.')
        review = publication.review_for_owner('member-a', {})
        publication.commit('member-a', {'type':'publish', 'request_id':str(uuid4()),
            'reviewed_digest':review.reviewed.digest, 'slug':'alice'})
        class Names:
            def read_approved(self, context):
                return ApprovedMemberName(context.subject_key, UsePurpose.VISITOR_AI, 'María del Carmen Li', 'name-v1')
            def recheck(self, context, name): return ReadState.CURRENT
        service.names = Names()
        changes = dict(RESUME_PUBLICATION_SERVICE=publication, PEERSLATE_MEMBER_VISITOR_AI_ENABLED=True,
                       MEMBER_VISITOR_AI_SERVICE=service, MEMBER_VISITOR_AI_RUNTIME=runtime)
        original = {key:self.app.config.get(key) for key in changes}
        self.app.config.update(changes)
        def synthetic_identity():
            owner = request.cookies.get('f_synthetic_owner')
            if owner not in {'member-a', 'member-b'}: raise AuthenticationRequired('Synthetic signed out context')
            return PeerSlateIdentity(owner, 'development', 'urn:synthetic:f', owner, display_name='Private account name')
        try:
            with patch('resume_publication_routes.get_current_identity', synthetic_identity):
                yield db, repo, provider, service
        finally:
            runtime.close()
            self.app.config.update(original)

    def _f_screenshot(self, page, name):
        directory = os.environ.get('PEERSLATE_F_BROWSER_EVIDENCE')
        if directory:
            root = Path(directory)
            root.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(root / (name + '.png')), full_page=False)

    def _f_question(self, page, question):
        page.fill('#visitor-ai-question', question)
        with page.expect_response(lambda r: r.url.endswith('/questions') and r.request.method == 'POST') as received:
            page.click('#visitor-ai-ask')
        page.wait_for_function("() => !document.getElementById('visitor-ai-ask').disabled")
        return received.value

    def test_visitor_questions_sixth_answer_citation_revocation_and_failure_recovery(self):
        from tests.test_member_visitor_ai_sources import SAVED_TEXT
        from services.ai_foundation.errors import ProviderUnavailableError
        with self._visitor_fixture() as (db, repo, provider, service):
            context = self.browser.new_context(viewport={'width':1440, 'height':1000})
            try:
                page = context.new_page()
                page.goto(self._origin() + '/alice/resume')
                page.wait_for_selector('#visitor-ai-ask:not([disabled])')
                self.assertEqual(page.locator('#visitor-ai-title').inner_text(), 'Ask María del Carmen Li AI')
                self.assertNotIn(SAVED_TEXT, page.locator('.resume-publication__guest').inner_text())
                self.assertEqual(page.locator('#visitor-ai-answer').inner_text(), '')
                for i in range(6):
                    exact = f'What happened in 2021? Question {i+1}'
                    response = self._f_question(page, exact)
                    self.assertEqual(response.status, 200)
                    self.assertEqual(provider.seen[-1][0].question, exact)
                    self.assertEqual(provider.seen[-1][0].subject_key, 'member-a')
                    self.assertIn(SAVED_TEXT, page.locator('#visitor-ai-answer').inner_text())
                self.assertEqual(len(provider.seen), 6)
                page.click('.visitor-ai__citation')
                page.wait_for_function("() => document.querySelector('.visitor-ai blockquote').textContent.includes('Led a team')")
                self._f_screenshot(page, 'guest-desktop-supported')
                db.documents['member-a']['sharing_epoch'] += 1
                page.click('.visitor-ai__citation')
                page.wait_for_function("() => document.querySelector('.visitor-ai blockquote').textContent.includes('unavailable')")
                self.assertNotIn(SAVED_TEXT, page.locator('.visitor-ai blockquote').inner_text())
                def outage(): raise ProviderUnavailableError('synthetic unavailable')
                provider.hook = outage
                question = '<img src=x onerror=alert(1)> exact question'
                self.assertEqual(self._f_question(page, question).status, 503)
                self.assertEqual(page.input_value('#visitor-ai-question'), question)
                self.assertEqual(page.locator('#visitor-ai-answer').inner_text(), '')
                self.assertIn('preserved', page.locator('#visitor-ai-status').inner_text())
                provider.hook = lambda:None
                self.assertEqual(self._f_question(page, question).status, 200)
                self.assertEqual(page.locator('#visitor-ai-answer img').count(), 0)
                self.assertEqual(page.locator('#visitor-ai-answer summary').inner_text(), question)
                page.route('**/ai/questions', lambda route:route.abort())
                page.click('#visitor-ai-ask')
                page.wait_for_function("() => document.getElementById('visitor-ai-status').textContent.includes('please try again')")
                self.assertEqual(page.input_value('#visitor-ai-question'), question)
                self._f_screenshot(page, 'guest-network-recovery')
            finally: context.close()

    def test_visitor_mobile_keyboard_reflow_and_private_preview_separation(self):
        from tests.test_member_visitor_ai_sources import SAVED_TEXT
        with self._visitor_fixture() as (db, repo, provider, service):
            owner = self.browser.new_context(viewport={'width':390, 'height':844})
            guest = self.browser.new_context(viewport={'width':390, 'height':844})
            other = self.browser.new_context()
            try:
                owner.add_cookies([{'name':'f_synthetic_owner', 'value':'member-a', 'url':self._origin()}])
                other.add_cookies([{'name':'f_synthetic_owner', 'value':'member-b', 'url':self._origin()}])
                db.documents['member-a']['sharing_enabled'] = False
                db.documents['member-a']['entries'][0]['visitor_ai'] = False
                page = owner.new_page()
                page.goto(self._origin() + '/app/resume/publication')
                page.focus('#visitor-ai-open'); page.keyboard.press('Enter')
                page.wait_for_selector('#visitor-ai-panel[open]')
                page.wait_for_selector('#visitor-ai-ask:not([disabled])')
                self.assertEqual(page.locator('#visitor-ai-title').inner_text(), 'Try visitor AI')
                self.assertIn('Only you can see', page.locator('.visitor-ai__private').inner_text())
                page.click('.visitor-ai__choices > summary')
                page.check('#visitor-ai-choices input')
                self.assertEqual(self._f_question(page, 'What did I allow for this preview?').status, 200)
                self.assertEqual(provider.seen[-1][0].product, 'member_visitor_ai_preview')
                self.assertIn(SAVED_TEXT, page.locator('#visitor-ai-answer').inner_text())
                url = page.locator('.visitor-ai__citation').get_attribute('href')
                self.assertEqual(guest.request.get(url).status, 404)
                self.assertEqual(other.request.get(url).status, 404)
                self.assertEqual(owner.request.get(url).status, 200)
                page.click('.visitor-ai__choices > summary')
                self._f_screenshot(page, 'owner-mobile-preview')
                page.keyboard.press('Escape')
                self.assertFalse(page.locator('#visitor-ai-panel').is_visible())
                self.assertEqual(page.evaluate('document.activeElement.id'), 'visitor-ai-open')
                page.keyboard.press('Enter')
                self.assertEqual(page.input_value('#visitor-ai-question'), 'What did I allow for this preview?')
                page.click('.visitor-ai__choices > summary')
                page.uncheck('#visitor-ai-choices input')
                self.assertEqual(page.locator('#visitor-ai-answer').inner_text(), '')
                self.assertEqual(self._f_question(page, 'Any permitted sources?').status, 200)
                self.assertIn('does not establish', page.locator('#visitor-ai-status').inner_text())
                self.assertEqual(len(provider.seen), 1)
                db.documents['member-a']['draft_revision'] += 1
                self.assertEqual(owner.request.get(url).status, 404)
                self.assertEqual(self._f_question(page, 'Preserve this after a draft change').status, 503)
                self.assertEqual(page.input_value('#visitor-ai-question'), 'Preserve this after a draft change')
                # Responsive widths also exercise the narrow viewport produced
                # by desktop zoom. Physical device/assistive-tech proof is separate.
                public = guest.new_page()
                for width in (320, 390, 640, 768, 1024, 1440):
                    public.set_viewport_size({'width':width, 'height':900})
                    public.goto(self._origin() + '/alice/resume')
                    public.click('#visitor-ai-open')
                    self.assertFalse(public.evaluate('document.documentElement.scrollWidth > innerWidth + 1'))
                    self.assertFalse(public.locator('#visitor-ai-panel').evaluate('(n) => n.scrollWidth > n.clientWidth + 1'))
                    self._f_screenshot(public, f'guest-responsive-{width}')
            finally:
                owner.close(); guest.close(); other.close()


if __name__ == "__main__":
    unittest.main()
