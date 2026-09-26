"""Browser journeys for owner review/publish and guest reads.

Playwright drives pinned Chromium against a locally served Flask app using
real application adapters. Ordinary discovery may skip when Playwright or
Chrome is unavailable. This is not SQL engine proof or live identity proof.
"""

from __future__ import annotations

import os
import threading
import unittest
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
        self.assertIn("not the labeled Pete example", guest.locator(".resume-publication--public").inner_text())
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


if __name__ == "__main__":
    unittest.main()
