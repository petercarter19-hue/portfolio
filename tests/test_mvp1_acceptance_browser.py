"""G integrated browser journeys in progress; not the complete AC01-AC15 gate.

No application HTTP response is fulfilled or replaced. Identity and persistence
are explicit synthetic boundaries. SQL, live provider and device proof separate.
"""

import os
from pathlib import Path
import unittest
from uuid import uuid4

from tests.mvp1_acceptance_support import Mvp1AcceptanceServer

try:
    from playwright.sync_api import sync_playwright, expect
except ImportError:
    sync_playwright = None


@unittest.skipUnless(sync_playwright, "Playwright is required for G browser acceptance")
class Mvp1AcceptanceBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from scripts.capture_ps_journal_j1_evidence import _resolve_chrome
        cls.runtime = sync_playwright().start()
        cls.addClassCleanup(cls.runtime.stop)
        cls.browser = cls.runtime.chromium.launch(executable_path=_resolve_chrome(), headless=True,
            args=['--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream'])
        cls.addClassCleanup(cls.browser.close)

    def setUp(self):
        self.server = Mvp1AcceptanceServer().__enter__()
        self.addCleanup(self.server.__exit__, None, None, None)
        self.errors = []

    def page(self, owner=None, width=1440):
        context = self.browser.new_context(viewport={"width": width, "height": 1000})
        self.addCleanup(context.close)
        if owner:
            context.add_cookies([{"name": "mvp1-synthetic-owner", "value": owner, "url": self.server.url}])
        page = context.new_page()
        page.on("pageerror", lambda error: self.errors.append(str(error)))
        return page

    def intake_input(self, page, *, reopen=False):
        if reopen:
            page.locator('#resume-intake-reopen').click()
        # Fresh entry opens after workspace/guide loading; returning from manual
        # editing is an explicit action, never inferred from a transient DOM count.
        expect(page.locator('#resume-intake[open]')).to_be_visible()
        if page.locator('#resume-intake-welcome').is_visible():
            page.locator('#resume-intake-start-type').click()
        expect(page.locator('#resume-intake-input')).to_be_visible()

    def intake_manual(self, page):
        page.locator('#resume-intake-skip').click()
        page.locator('#resume-intake-manual-details > summary').click()
        expect(page.locator('#resume-intake-type')).to_be_visible()

    def seed_role(self, owner="g-member-a"):
        key = str(uuid4())
        self.server.shared.policy.commit(owner, {"type": "create", "request_id": str(uuid4()),
            "entry_key": key, "canonical_type": "role", "values": {
                "role_title": "Synthetic engineer", "employer_name": "Example workshop",
                "summary": "Built a small scheduling tool."}})
        return key

    def capture(self, page, name):
        folder = os.environ.get("PEERSLATE_MVP1_ACCEPTANCE_EVIDENCE_DIR")
        if folder:
            target = Path(folder).resolve()
            target.mkdir(parents=True, exist_ok=True)
            page.evaluate("window.scrollTo(0, 0)")
            page.screenshot(path=str(target / (name + ".png")), full_page=True)

    def publish_choices(self, page, choices, slug="g-alex"):
        page.goto(self.server.url + "/app/resume/publication")
        page.locator("#resume-publication-review-button").click()
        for key, display, ai in choices:
            row = page.locator('[data-entry-key="' + key + '"]')
            row.locator('[data-permission="resume_display"]').set_checked(display)
            row.locator('[data-permission="visitor_ai"]').set_checked(ai)
        page.locator("#resume-publication-review-button").click()
        expect(page.locator("#resume-publication-publish-button")).to_be_enabled()
        page.locator("#resume-publication-slug").fill(slug)
        page.locator("#resume-publication-publish-button").click()
        expect(page.locator("#resume-publication-status")).to_contain_text("currently shared")

    def test_profile_then_explicit_resume_permissions_and_guest_name(self):
        key = self.seed_role()
        page = self.page("g-member-a")
        page.goto(self.server.url + "/app/profile")
        page.locator('[name="slug"]').fill("g-alex")
        page.locator('[name="display_name"]').fill("Alex River")
        page.locator('[name="headline"]').fill("Builds practical tools")
        page.locator('[name="summary"]').fill("A synthetic member introduction.")
        page.get_by_role("button", name="Save privately", exact=True).click()
        expect(page.locator("#profile-status")).to_contain_text("Saved privately")
        page.locator("#profile-review").click()
        expect(page.locator("#profile-review-panel")).to_be_visible()
        page.locator("#profile-publish").click()
        expect(page.locator("#profile-status")).to_contain_text("Your introduction is public")
        page.goto(self.server.url + "/app/resume/publication")
        page.locator("#resume-publication-review-button").click()
        row = page.locator('[data-entry-key="' + key + '"]')
        expect(row).to_contain_text("Synthetic engineer")
        self.assertFalse(row.locator('[data-permission="resume_display"]').is_checked())
        row.locator('[data-permission="resume_display"]').check()
        expect(page.locator("#resume-publication-publish-button")).to_be_disabled()
        page.locator("#resume-publication-review-button").click()
        expect(page.locator("#resume-publication-publish-button")).to_be_enabled()
        page.locator("#resume-publication-slug").fill("g-alex")
        self.capture(page, "review-before-publication")
        page.locator("#resume-publication-publish-button").click()
        expect(page.locator("#resume-publication-status")).to_contain_text("currently shared")
        guest = self.page()
        guest.goto(self.server.url + "/g-alex/resume")
        expect(guest.locator("h1")).to_have_text("Alex River")
        expect(guest.locator(".resume-publication__entry")).to_contain_text("Built a small scheduling tool.")
        self.capture(guest, "published-resume")
        self.assertFalse(self.server.shared.policy.list_entries("g-member-a")["entries"][0]["visitor_ai"])
        self.assertEqual(self.errors, [])

    def test_owner_b_and_guest_cannot_read_owner_a_private_preview(self):
        self.seed_role()
        owner = self.page("g-member-a")
        response = owner.request.get(self.server.url + "/api/resume-publication/me/preview")
        self.assertEqual(response.status, 200)
        self.assertFalse(response.json()["published"])
        other = self.page("g-member-b")
        response = other.request.get(self.server.url + "/api/resume-publication/me/preview")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.json()["display"], {})
        guest = self.page()
        self.assertEqual(guest.request.get(self.server.url + "/api/resume-publication/me/preview").status, 404)
        self.assertEqual(guest.request.get(self.server.url + "/unknown-person/resume").status, 404)
        self.assertEqual(self.errors, [])

    def test_saved_draft_ai_preview_is_private_and_fenced_after_provider(self):
        import copy
        key = self.seed_role()
        owner = self.page('g-member-a')
        owner.goto(self.server.url + '/app/resume')
        owner.locator('#resume-intake-hide').click()
        owner.locator(".resume-editor__card").filter(has=owner.locator('[id="' + key + '-summary"]')).locator("summary").click()
        field = owner.locator('[id="' + key + '-summary"]')
        field.fill('My private proposed scheduling improvement.')
        owner.locator('article').filter(has=field).get_by_role('button', name='Save draft', exact=True).click()
        expect(owner.locator('#resume-editor-status')).to_contain_text('Draft saved')
        before_policy = copy.deepcopy(self.server.shared.policy.list_entries('g-member-a'))
        before_publication = copy.deepcopy(self.server.shared.publication.repository.load_owner('g-member-a'))
        owner.goto(self.server.url + '/app/resume/publication')
        expect(owner.locator('#visitor-ai-ask')).to_be_enabled()
        owner.locator('#visitor-ai-open').click()
        owner.locator('.visitor-ai__choices > summary').click()
        owner.locator('#visitor-ai-choices input[value="' + key + '"]').check()
        owner.locator('#visitor-ai-question').fill('What improvement is proposed?')
        owner.locator('#visitor-ai-ask').click()
        expect(owner.locator('#visitor-ai-answer')).to_contain_text('My private proposed scheduling improvement.')
        citation = owner.locator('.visitor-ai__citation').last
        citation_url = citation.get_attribute('href')
        citation.click()
        expect(owner.locator('#visitor-ai-answer blockquote')).to_contain_text('My private proposed scheduling improvement.')
        self.assertEqual(self.server.shared.policy.list_entries('g-member-a'), before_policy)
        self.assertEqual(self.server.shared.publication.repository.load_owner('g-member-a'), before_publication)
        other = self.page('g-member-b')
        guest = self.page()
        for page in (other, guest):
            self.assertEqual(page.request.get(citation_url).status, 404)
        self.assertEqual(guest.request.get(self.server.url + '/g-alex/resume').status, 404)
        self.server.provider.hook = lambda: self.server.shared.policy.commit('g-member-a', {
            'type': 'edit', 'request_id': str(uuid4()), 'entry_key': key,
            'expected_content_version': 1, 'expected_access_revision': 1,
            'values': {'role_title': 'Synthetic engineer', 'employer_name': 'Example workshop',
                       'summary': 'Newer canonical correction.'}})
        owner.locator('#visitor-ai-question').fill('Repeat the proposed improvement.')
        with owner.expect_response(lambda response: response.url.endswith('/visitor-preview/questions')) as refused:
            owner.locator('#visitor-ai-ask').click()
        self.assertEqual(refused.value.status, 503)
        self.assertNotIn('My private proposed scheduling improvement.', refused.value.text())
        self.assertEqual(owner.request.get(citation_url).status, 404)
        expect(owner.locator('#visitor-ai-question')).to_have_value('Repeat the proposed improvement.')
        self.assertEqual(self.errors, [])

    def test_intake_role_two_strengths_private_reload_and_guide(self):
        page = self.page("g-member-a")
        page.goto(self.server.url + "/app/resume")
        self.intake_manual(page)
        page.locator("#resume-intake-type").select_option("role")
        page.locator("#resume-intake-role-title").fill("Synthetic engineer")
        page.locator("#resume-intake-employer").fill("Example workshop")
        page.locator("#resume-intake-add-fact").click()
        for strength in ("Requirements management", "Systems thinking"):
            page.locator("#resume-intake-type").select_option("skill")
            page.locator("#resume-intake-skill").fill(strength)
            page.locator("#resume-intake-add-fact").click()
        page.locator("#resume-intake-manual-save").click()
        expect(page.locator("#resume-intake-receipt")).to_contain_text("3 saved privately")
        self.intake_input(page, reopen=True)
        page.locator("#resume-intake-text").fill("An unfinished thought about a project")
        page.locator("#resume-intake-add").click()
        expect(page.locator("#resume-intake-receipt")).to_contain_text("needs your review")
        expect(page.locator('#resume-intake-proposals > li')).to_have_count(1)
        page.locator('#resume-intake-back').click()
        rows = self.server.shared.policy.list_entries("g-member-a")["entries"]
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(not row["resume_display"] and not row["visitor_ai"] for row in rows))
        self.assertEqual(self.server.shared.publication.owner_preview("g-member-a")["current"], None)
        unfinished = "I am still typing this second thought."
        page.locator("#resume-intake-text").fill(unfinished)
        page.locator("#resume-intake-hide").click()
        expect(page.locator("#resume-intake-guide")).to_be_hidden()
        page.locator("#resume-intake-reopen").click()
        expect(page.locator("#resume-intake-text")).to_have_value(unfinished)
        page.reload()
        # Both submissions survive reload: the three explicit facts and the
        # unaccepted source. A source proposal must not become a fourth fact.
        expect(page.locator("#resume-intake-receipt")).to_contain_text("needs your review")
        self.assertEqual(len(self.server.shared.policy.list_entries("g-member-a")["entries"]), 3)
        nav = page.locator('.resume-editor__sections')
        panel = page.locator('.resume-editor__panel')
        expect(nav).to_be_visible()
        self.assertLessEqual(nav.bounding_box()['x'] + nav.bounding_box()['width'], panel.bounding_box()['x'])
        page.locator('#resume-intake-reopen').click()
        expect(page.locator('#resume-intake')).to_be_visible()
        self.assertEqual(self.server.shared.draft.repository.load_owner("g-member-a").get("media_placements", {}), {})
        panel = page.locator('.resume-editor__panel')
        nav = page.locator('.resume-editor__sections')
        guide = page.locator('#resume-intake')
        expect(nav).to_be_hidden()
        panel_box, guide_box = panel.bounding_box(), guide.bounding_box()
        self.assertLess(guide_box['x'], panel_box['x'] + panel_box['width'])
        self.assertGreater(guide_box['x'] + guide_box['width'], panel_box['x'])
        self.assertGreater(panel_box['width'], 500)
        self.assertEqual(guide.evaluate('el => el.tagName'), 'DIALOG')
        expect(page.locator('.resume-editor__card details[open]')).to_have_count(0)
        self.capture(page, "private-intake-three-facts")
        for width in (320, 390, 768, 1024):
            page.set_viewport_size({'width': width, 'height': 900})
            self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth'), width)
        page.locator('#resume-intake-hide').click()
        page.locator('#resume-editor-review').click()
        expect(page).to_have_url(self.server.url + '/app/resume/publication')
        self.assertIsNone(self.server.shared.publication.owner_preview('g-member-a')['current'])
        self.assertEqual(self.errors, [])

    def test_four_permission_combinations_guest_six_questions_and_citation_revocation(self):
        choices = []
        texts = {}
        for display, ai, label in ((False, False, "Entirely private wording"),
                                  (True, False, "Visible without AI wording"),
                                  (False, True, "AI allowed hidden wording"),
                                  (True, True, "Visible and AI allowed wording")):
            key = str(uuid4())
            texts[key] = label
            self.server.shared.policy.commit("g-member-a", {"type": "create", "request_id": str(uuid4()),
                "entry_key": key, "canonical_type": "role", "values": {
                    "role_title": label, "employer_name": "Synthetic employer", "summary": label}})
            choices.append((key, display, ai))
        self.publish_choices(self.page("g-member-a"), choices)
        guest = self.page()
        guest.goto(self.server.url + "/g-alex/resume")
        html = guest.content()
        for key, display, _ in choices:
            self.assertEqual(texts[key] in html, display)
        for number in range(6):
            guest.locator("#visitor-ai-question").fill("What experience is shared? " + str(number))
            guest.locator("#visitor-ai-ask").click()
            expect(guest.locator(".visitor-ai__citation").last).to_be_visible()
            expect(guest.locator("#visitor-ai-ask")).to_be_enabled()
        self.assertEqual(len(self.server.provider.seen), 6)
        exposed = " ".join(source.content for _, sources in self.server.provider.seen for source in sources)
        for key, _, ai in choices:
            self.assertEqual(texts[key] in exposed, ai)
        citation = guest.locator(".visitor-ai__citation").last
        with guest.expect_response(lambda response: "/ai/citations/" in response.url) as citation_response:
            citation.click()
        citation_url = citation_response.value.url
        expect(guest.locator(".visitor-ai__answer blockquote").last).to_be_visible()
        # Restrict during the provider's work. The real final fences must refuse
        # the answer and every earlier citation ticket under changed authority.
        self.server.provider.hook = lambda: self.server.shared.publication.commit("g-member-a", {
            "type": "sharing_off", "request_id": str(uuid4())})
        guest.locator("#visitor-ai-question").fill("Repeat that experience.")
        with guest.expect_response(lambda response: response.url.endswith("/ai/questions")) as pending_response:
            guest.locator("#visitor-ai-ask").click()
        response = pending_response.value
        self.assertIn(response.json()["state"], ("retryable", "unavailable"))
        self.assertNotIn("AI allowed hidden wording", response.text())
        self.assertEqual(guest.request.get(self.server.url + "/g-alex/resume").status, 404)
        self.assertEqual(guest.request.get(citation_url).status, 404)
        self.assertEqual(self.errors, [])

    def test_story_requires_deliberate_binding_and_display_does_not_grant_ai(self):
        page = self.page("g-member-a")
        page.goto(self.server.url + "/app/resume")
        page.locator("#resume-intake-hide").click()
        page.get_by_text("Write a new personal entry", exact=True).click()
        wording = "I enjoy making small tools and learning how things work."
        page.locator("#resume-story-wording").fill(wording)
        page.get_by_role("button", name="Save personal entry privately", exact=True).click()
        expect(page.locator("#resume-story-status")).to_contain_text("Saved privately")
        self.assertIsNone(self.server.shared.draft.get_workspace("g-member-a")["story_entry_key"])
        page.locator("#resume-story-choice").select_option(label="My Story")
        selected = page.locator("#resume-story-choice").input_value()
        page.locator("#resume-story-select").click()
        expect(page.locator("#resume-story-status")).to_contain_text("Selected for your private Resume draft")
        page.reload()
        expect(page.locator("#resume-story-choice")).to_have_value(selected)
        self.publish_choices(page, [(selected, False, False)])
        guest = self.page()
        guest.goto(self.server.url + "/g-alex/resume")
        self.assertNotIn(wording, guest.content())
        expect(guest.locator("#resume-story")).to_have_count(0)
        self.publish_choices(page, [(selected, True, False)])
        guest.reload()
        expect(guest.locator("#resume-story")).to_contain_text(wording)
        row = self.server.shared.policy.list_entries("g-member-a")["entries"][0]
        self.assertFalse(row["visitor_ai"])
        self.assertTrue(row["resume_display"])
        self.assertEqual(self.errors, [])

    def test_two_photo_uploads_crop_swap_private_save_publish_and_story_mask(self):
        role = self.seed_role()
        story = str(uuid4())
        owner = "g-member-a"
        self.server.shared.canonical.create_private(owner, dict(command_id=str(uuid4()), record_key=story,
            record_type="knowledge", values={"title": "A personal introduction", "wording": "I like learning new crafts."}))
        item = self.server.shared.canonical.get_item(owner, story)
        self.server.shared.draft.commit(owner, dict(request_id=str(uuid4()), type="bind_story", record_key=story,
            expected_draft_version=0, expected_content_token=item["content_token"], expected_access_revision=item["access_revision"]))
        page = self.page(owner)
        page.goto(self.server.url + "/app/resume")
        page.locator("#resume-intake-hide").click()
        photo_path = Path(__file__).parent / "fixtures/resume_media/member-photo-1200x800.jpg"
        keys = []
        for slot in ("story_banner", "experience_support"):
            before = page.locator("#resume-media-photos li").count()
            page.locator("#resume-media-upload").set_input_files(str(photo_path))
            expect(page.locator("#resume-media-photos li")).to_have_count(before + 1)
            card = page.locator("#resume-media-photos li").filter(has=page.get_by_role("button", name="Check scan"))
            card.get_by_role("button", name="Check scan").click()
            card = page.locator("#resume-media-photos li").nth(before)
            # The server may order newest photos first, so use its recorded key.
            key = list(self.server.shared.capture_procedures.created)[-1]
            keys.append(key)
            card = page.locator('[data-source-id="' + key + '"]').filter(has=page.locator('[data-action="select"]'))
            card.locator('[data-action="select"][data-slot="' + slot + '"]').click()
            expect(page.locator("#resume-media-slot-" + slot + "-value")).to_contain_text("Your photo")
        page.locator("#resume-media-preview-placement").click()
        expect(page.locator("#resume-media-preview")).to_be_visible()
        page.locator("#resume-media-swap").click()
        page.locator("#resume-media-crop-story_banner").click()
        for field, value in dict(x="0", y="0.25", width="1", height="0.5").items():
            page.locator("#resume-media-crop-story_banner-" + field).fill(value)
        page.locator("#resume-media-crop-apply-story_banner").click()
        expect(page.locator("#resume-media-status")).to_contain_text("Crop updated")
        self.assertEqual(self.server.shared.draft.get_workspace(owner)["draft_version"], 1)
        guest = self.page()
        self.assertEqual(guest.request.get(self.server.url + "/g-alex/resume").status, 404)
        page.locator("#resume-media-add").click()
        expect(page.locator("#resume-media-status")).to_contain_text("Added 2 photos")
        page.reload()
        expect(page.locator("#resume-media-slot-story_banner-value")).to_contain_text("saved privately")
        self.publish_choices(page, [(role, True, False), (story, True, False)])
        guest.goto(self.server.url + "/g-alex/resume")
        self.assertNotIn("/petec", guest.locator("#nav-search-data").text_content())
        photos = guest.locator(".resume-publication__crop img")
        expect(photos).to_have_count(2)
        for photo in photos.all():
            expect(photo).to_be_visible()
            photo.evaluate("image => image.decode()")
            self.assertGreater(photo.evaluate("image => image.naturalWidth"), 0)
        banner = guest.locator(".resume-publication__crop--story_banner img")
        self.assertEqual(banner.evaluate("image => parseFloat(image.style.height)"), 200)
        old_banner_url = banner.get_attribute("src")
        self.capture(guest, "two-photos-published")
        page.goto(self.server.url + "/app/resume")
        expect(page.locator("#resume-intake")).to_be_hidden()
        expect(page.locator("#resume-editor-story-preview")).to_have_text("I like learning new crafts.")
        for slot in ("story_banner", "experience_support"):
            expect(page.locator("#resume-media-placement-badge-" + slot)).to_have_text("Saved in your private draft")
        expect(page.locator(".resume-editor__experience-composition #resume-media-placement-image-experience_support")).to_be_visible()
        expect(page.locator(".resume-editor__story-composition #resume-media-placement-image-story_banner")).to_be_visible()
        page.locator("#resume-media-hide").click()
        for width in (1440, 390):
            page.set_viewport_size({"width": width, "height": 1000})
            self.assertFalse(page.evaluate("document.documentElement.scrollWidth > innerWidth"))
            self.capture(page, "story-photo-placement-" + str(width))
        page.set_viewport_size({"width": 1440, "height": 1000})
        self.publish_choices(page, [(role, True, False), (story, False, False)])
        guest.reload()
        expect(guest.locator(".resume-publication__crop--story_banner")).to_have_count(0)
        self.assertEqual(guest.request.get(self.server.url + old_banner_url).status, 404)
        self.assertEqual(self.errors, [])

    def test_my_data_sharing_status_on_off_and_unavailable(self):
        from unittest.mock import patch
        key = self.seed_role()
        page = self.page("g-member-a")
        page.goto(self.server.url + "/app/settings/my-data")
        expect(page.locator(".owner-app__note")).to_contain_text("Resume sharing is off")
        self.server.shared.seed_publication("g-member-a", [(key, True, True)])
        page.reload()
        expect(page.locator(".owner-app__note")).to_contain_text("Your Resume is currently shared")
        with patch.object(self.server.shared.publication, "owner_preview", side_effect=RuntimeError("Synthetic outage")):
            page.reload()
            expect(page.locator(".owner-app__note")).to_contain_text("cannot confirm")
            expect(page.locator(".owner-app__note")).not_to_contain_text("nothing is shown")
        self.server.shared.publication.commit("g-member-a", dict(type="sharing_off", request_id=str(uuid4())))
        page.reload()
        expect(page.locator(".owner-app__note")).to_contain_text("Resume sharing is off")
        self.assertEqual(self.errors, [])

    def test_my_data_correction_wins_over_stale_editor_and_restore_stays_private(self):
        key = self.seed_role()
        owner = "g-member-a"
        for version in range(1, 7):
            self.server.shared.policy.commit(owner, dict(type="edit", request_id=str(uuid4()), entry_key=key,
                expected_content_version=version, expected_access_revision=1,
                values={"role_title": "Synthetic engineer", "employer_name": "Example workshop",
                        "summary": "Confirmed version " + str(version + 1)}))
        child = str(uuid4())
        self.server.shared.policy.commit(owner, dict(type="create", request_id=str(uuid4()), entry_key=child,
            canonical_type="achievement", parent_key=key, values={"wording": "Delivered the first release."}))
        editor = self.page(owner)
        self.publish_choices(editor, [(key, True, True), (child, True, False)])
        guest = self.page()
        guest.goto(self.server.url + "/g-alex/resume")
        expect(guest.locator("main")).to_contain_text("Confirmed version 7")
        editor.goto(self.server.url + "/app/resume")
        editor.locator("#resume-intake-hide").click()
        editor.locator(".resume-editor__card").filter(has=editor.locator('[id="' + key + '-summary"]')).locator("summary").click()
        editor.locator('[id="' + key + '-summary"]').fill("My unpublished version seven proposal")
        card = editor.locator("article").filter(has=editor.locator('[id="' + key + '-summary"]'))
        card.get_by_role("button", name="Save draft", exact=True).click()
        expect(editor.locator("#resume-editor-status")).to_contain_text("Draft saved")
        guest.reload()
        self.assertNotIn("My unpublished version seven proposal", guest.content())
        editor.goto(self.server.url + "/app/resume/publication")
        editor.locator("#resume-publication-review-button").click()
        expect(editor.locator("#resume-publication-publish-button")).to_be_enabled()
        manager = self.page(owner)
        manager.goto(self.server.url + "/app/settings/my-data")
        record = manager.locator('.my-data__entry[data-entry-key="' + key + '"]')
        record.get_by_role("button", name="Edit", exact=True).click()
        record.locator('[name="summary"]').fill("My Data version eight correction")
        record.get_by_role("button", name="Save correction", exact=True).click()
        expect(manager.locator("[data-my-data-status]")).to_contain_text("Correction saved")
        guest.reload()
        expect(guest.locator("main")).to_contain_text("My Data version eight correction")
        editor.locator("#resume-publication-slug").fill("g-alex")
        with editor.expect_response(lambda response: response.url.endswith("/api/resume-publication/me/commands")) as refused:
            editor.locator("#resume-publication-publish-button").click()
        self.assertEqual(refused.value.status, 409)
        current = self.server.shared.policy.get_entry(owner, key)["entry"]
        self.assertEqual(current["content_version"], 8)
        self.assertEqual(current["values"]["summary"], "My Data version eight correction")
        record.get_by_role("button", name="Delete", exact=True).click()
        expect(record.locator(".my-data__confirm")).to_contain_text("1 linked achievement")
        record.locator(".my-data__confirm").get_by_role("button", name="Delete", exact=True).click()
        expect(manager.locator("[data-my-data-status]")).to_contain_text("Deleted")
        guest.reload()
        self.assertNotIn("My Data version eight correction", guest.content())
        self.assertNotIn("Delivered the first release", guest.content())
        manager.locator("[data-my-data-permission]").select_option("recently_deleted")
        record.get_by_role("button", name="Restore", exact=True).click()
        expect(manager.locator("[data-my-data-status]")).to_contain_text("restored privately")
        restored = self.server.shared.policy.get_entry(owner, key)["entry"]
        self.assertFalse(restored["resume_display"])
        self.assertFalse(restored["visitor_ai"])
        manager.locator('[data-my-data-permission]').select_option('all')
        manager.reload()
        before_private_correction = self.server.shared.publication.repository.load_owner(owner)
        record.get_by_role('button', name='Edit', exact=True).click()
        record.locator('[name="summary"]').fill('Corrected after private restoration.')
        record.get_by_role('button', name='Save correction', exact=True).click()
        expect(manager.locator('[data-my-data-status]')).to_contain_text('Correction saved')
        self.assertEqual(self.server.shared.policy.get_entry(owner, key)['entry']['values']['summary'],
                         'Corrected after private restoration.')
        self.assertEqual(self.server.shared.publication.repository.load_owner(owner), before_private_correction)
        guest.reload()
        self.assertNotIn('Corrected after private restoration.', guest.content())
        self.assertNotIn("My Data version eight correction", guest.content())
        self.assertEqual(self.errors, [])

    def _story_stage_fixture(self, *, display):
        owner, story = 'g-member-a', str(uuid4())
        role = self.seed_role()
        shared = self.server.shared
        shared.canonical.create_private(owner, dict(command_id=str(uuid4()), record_key=story,
            record_type='knowledge', values={'title': 'A personal introduction',
                'wording': 'Story fixture: I enjoy learning crafts.', 'classification': 'personal'}))
        item = shared.canonical.get_item(owner, story)
        shared.draft.commit(owner, dict(request_id=str(uuid4()), type='bind_story', record_key=story,
            expected_draft_version=0, expected_content_token=item['content_token'], expected_access_revision=item['access_revision']))
        shared.seed_publication(owner, [(role, True, True), (story, display, False)])
        guest = self.page()
        guest.goto(self.server.url + '/g-alex/resume')
        expect(guest.locator('#resume-story')).to_have_count(1 if display else 0)
        self.assertEqual('Story fixture:' in guest.content(), display)
        self.assertNotIn('story_banner', shared.publication.guest_read(slug='g-alex')['media'])
        guest.locator('#visitor-ai-open').click()
        guest.locator('#visitor-ai-question').fill('What experience is shared?')
        guest.locator('#visitor-ai-ask').click()
        expect(guest.locator('#visitor-ai-status')).to_have_text('Answer complete.')
        self.assertTrue(self.server.provider.seen)
        self.assertNotIn('Story fixture:', ' '.join(source.content for _, sources in self.server.provider.seen for source in sources))
        self.capture(guest, 'stage-09' if display else 'stage-07')
        self.assertEqual(self.errors, [])

    def test_separately_seeded_stage_07_story_off_ai_off(self):
        self._story_stage_fixture(display=False)

    def test_separately_seeded_stage_09_story_on_ai_off(self):
        self._story_stage_fixture(display=True)

    def _cardinality_fixture(self, roles, education, events):
        shared, owner = self.server.shared, 'g-member-a'
        choices = []
        for kind, count in [('role', roles), ('education', education), ('achievement', events)]:
            for index in range(count):
                key = str(uuid4())
                values = ({'role_title': 'Long synthetic engineering title ' + ('with multidisciplinary responsibilities ' * 4) + str(index),
                           'employer_name': 'Example organization ' + ('LongName' * 20),
                           'start_date': '2020-01-01', 'date_precision': 'year',
                           'summary': 'Reachable role wording ' + str(index)} if kind == 'role' else
                          {'title': 'Synthetic course ' + str(index), 'institution_name': 'Example institution',
                           'start_date': '2030-09-01', 'date_precision': 'month', 'education_status': 'planned',
                           'summary': 'A planned future course.'} if kind == 'education' else
                          {'wording': 'Reachable event wording ' + str(index)})
                shared.policy.commit(owner, dict(type='create', request_id=str(uuid4()), entry_key=key,
                    canonical_type=kind, values=values))
                choices.append((key, True, False))
        shared.seed_publication(owner, choices)
        page = self.page()
        page.goto(self.server.url + '/g-alex/resume')
        expect(page.locator('.resume-publication__entry')).to_have_count(roles + education + events)
        expect(page.locator('#resume-story')).to_have_count(0)
        expect(page.locator('.resume-publication__media')).to_have_count(0)
        if roles:
            self.assertNotIn('2020-01-01', page.locator('main').inner_text())
            expect(page.locator('.resume-publication__entry').filter(has_text='Reachable role wording').first.locator('.resume-publication__dates')).to_have_text('2020')
        if education:
            expect(page.locator('.resume-publication__education-status').first).to_have_text('Planned')
            self.assertNotIn('2030-09-01', page.locator('main').inner_text())
        for width in (320, 390, 768, 1024, 1440):
            page.set_viewport_size({'width': width, 'height': 900})
            self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth'), width, str(width))
            if roles + education + events:
                last = page.locator('.resume-publication__entry').last
                last.scroll_into_view_if_needed()
                expect(last).to_be_visible()
                self.assertTrue(last.evaluate('(e) => e.scrollWidth <= e.clientWidth + 1'))
        page.set_viewport_size({'width': 640, 'height': 450}) # 1280x900 at 200% equivalent CSS viewport
        self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth'), 640)
        page.evaluate('() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
        page.locator('#visitor-ai-open').focus()
        page.keyboard.press('Enter')
        expect(page.locator('#visitor-ai-question')).to_be_focused()
        page.keyboard.press('Escape')
        expect(page.locator('#visitor-ai-open')).to_be_focused()
        self.capture(page, 'cardinality-' + str(roles) + '-' + str(education) + '-' + str(events))
        self.assertEqual(self.errors, [])

    def test_cardinality_empty_resume(self):
        self._cardinality_fixture(0, 0, 0)

    def test_cardinality_one_of_each(self):
        self._cardinality_fixture(1, 1, 1)

    def test_cardinality_several_roles_events(self):
        self._cardinality_fixture(3, 0, 8)

    def test_cardinality_dense_roles_education_events(self):
        self._cardinality_fixture(12, 6, 50)

    def test_document_typed_recording_proposal_review_private_save_and_source_removal(self):
        page = self.page('g-member-a')
        page.goto(self.server.url + '/app/resume')
        self.intake_manual(page)
        page.locator('#resume-intake-type').select_option('skill')
        page.locator('#resume-intake-skill').fill('Planning')
        page.locator('#resume-intake-add-fact').click()
        page.locator('#resume-intake-manual-save').click()
        expect(page.locator('#resume-intake-receipt')).to_contain_text('1 saved privately')
        self.intake_input(page, reopen=True)
        page.locator('#resume-intake-text').fill('Typed contribution about making plans.')
        page.locator('#resume-intake-mic').click()
        page.wait_for_timeout(1500) # collect actual browser audio from the explicit synthetic device
        page.locator('#resume-intake-mic').click()
        expect(page.locator('#resume-intake-text')).to_have_value(
            __import__('re').compile('Typed contribution.*Synthetic spoken contribution', __import__('re').S), timeout=15000)
        self.assertGreater(self.server.transcriber.calls[0][0], 0)
        page.locator('#resume-intake-file').set_input_files({'name': 'synthetic-resume.txt',
            'mimeType': 'text/plain', 'buffer': b'Explicit document contribution: coordinating a workshop.'})
        page.locator('#resume-intake-add').click()
        expect(page.locator('#resume-intake-receipt')).to_contain_text('needs your review', timeout=15000)
        # The guide presents one group at a time. Explicitly leave both the
        # typed and recording source groups out before correcting the document.
        expect(page.locator('#resume-intake-proposals')).to_contain_text('Typed contribution')
        self.assertEqual(len(self.server.shared.policy.list_entries('g-member-a')['entries']), 1)
        page.get_by_role('button', name='Leave this out', exact=True).click()
        expect(page.locator('#resume-intake-proposals')).to_contain_text('Synthetic spoken contribution')
        self.assertEqual(len(self.server.shared.policy.list_entries('g-member-a')['entries']), 1)
        page.get_by_role('button', name='Leave this out', exact=True).click()
        expect(page.locator('#resume-intake-proposals')).to_contain_text('Explicit document contribution')
        self.assertEqual(len(self.server.shared.policy.list_entries('g-member-a')['entries']), 1)
        proposal = page.locator('#resume-intake-proposals > li').filter(has_text='Explicit document contribution')
        proposal.get_by_label('Save this as', exact=True).select_option('role')
        proposal.get_by_label('Employer', exact=True).fill('Example workshop')
        proposal.get_by_label('Save this as', exact=True).select_option('skill')
        proposal.locator('[data-proposal-field="name"]').fill('Workshop coordination')
        proposal.locator('[data-proposal-field="name"]').press('Tab')
        proposal.get_by_role('button', name='Confirm details', exact=True).click()
        expect(page.locator('#resume-intake-proposals')).not_to_contain_text('Explicit document contribution')
        rows = self.server.shared.policy.list_entries('g-member-a')['entries']
        accepted_key = next(row['entry_key'] for row in rows if row['values']['skill_name'] == 'Workshop coordination')
        page.reload()
        expect(page.locator('[id="' + accepted_key + '-name"]')).to_have_value('Workshop coordination')
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(not row['resume_display'] and not row['visitor_ai'] for row in rows))
        snapshot = self.server.intake.repository.load_owner('g-member-a')
        source = next(row for row in snapshot['sources'].values() if 'Explicit document contribution' in (row.get('text') or ''))
        payload = dict(request_id=str(uuid4()), source_key=source['source_key'])
        purge_url = self.server.url + '/api/resume-intake/me/sources/purge'
        headers = {'X-PeerSlate-Request': 'same-origin'}
        self.assertEqual(self.page('g-member-b').request.post(purge_url, data=payload, headers=headers).status, 404)
        response = page.request.post(purge_url, data=payload, headers=headers)
        self.assertEqual(response.status, 200)
        self.assertFalse(response.json()['source_resurrected'])
        self.assertEqual(page.request.post(purge_url, data=payload, headers=headers).status, 200)
        self.assertEqual(self.server.shared.policy.list_entries('g-member-a')['entries'], rows)
        page.reload()
        expect(page.locator('[id="' + accepted_key + '-name"]')).to_have_value('Workshop coordination')
        self.assertNotIn('Explicit document contribution', page.content())
        self.assertEqual(self.errors, [])

    def test_cancelled_late_transcription_preserves_newer_typed_input(self):
        import threading
        from unittest.mock import patch
        entered, release = threading.Event(), threading.Event()
        self.addCleanup(release.set)
        self.server.transcriber.hook = lambda: (entered.set(), release.wait(15))
        page = self.page('g-member-a')
        loading, loaded = threading.Event(), threading.Event()
        self.addCleanup(loaded.set)
        original_workspace = self.server.intake.get_workspace
        def delayed_workspace(owner):
            loading.set()
            if not loaded.wait(10):
                raise RuntimeError('Synthetic initial workspace delay was not released')
            return original_workspace(owner)
        with patch.object(self.server.intake, 'get_workspace', side_effect=delayed_workspace):
            page.goto(self.server.url + '/app/resume')
            self.assertTrue(loading.wait(5))
            self.assertEqual(page.locator('#resume-intake[open]').count(), 0)
            self.assertTrue(page.locator('#resume-intake-reopen').is_visible())
            # Exercise pending initialization through the actual service and HTTP UI.
            timer = threading.Timer(0.5, loaded.set)
            timer.start()
            try:
                self.intake_input(page)
                self.assertTrue(loaded.is_set(), 'Fresh guide entry must await its initial workspace')
            finally:
                loaded.set()
                timer.cancel()
        page.locator('#resume-intake-text').fill('Keep my original words.')
        page.locator('#resume-intake-mic').click()
        page.wait_for_timeout(1200) # actual audio from synthetic browser device
        with page.expect_response(lambda r: r.url.endswith('/recordings'), timeout=20000):
            page.locator('#resume-intake-mic').click()
            self.assertTrue(entered.wait(10))
            page.locator('#resume-intake-text').fill('Keep my newer typed words.')
            page.locator('#resume-intake-cancel-recording').click()
            expect(page.locator('#resume-intake-status')).to_contain_text('cancelled')
            release.set()
        expect(page.locator('#resume-intake-attachments')).to_contain_text('transcription cancelled')
        expect(page.locator('#resume-intake-text')).to_have_value('Keep my newer typed words.')
        self.assertEqual(self.server.shared.policy.list_entries('g-member-a')['entries'], [])
        self.assertIsNone(self.server.shared.publication.owner_preview('g-member-a')['current'])
        page.locator('#resume-intake-add').click()
        expect(page.locator('#resume-intake-receipt')).to_contain_text('needs your review')
        self.assertNotIn('Synthetic spoken contribution', page.locator('#resume-intake-proposals').inner_text())
        self.assertEqual(self.errors, [])

    def test_unsupported_document_storage_failure_and_rejected_scan_are_honest(self):
        from unittest.mock import patch
        page = self.page('g-member-a')
        page.goto(self.server.url + '/app/resume')
        self.intake_input(page)
        page.locator('#resume-intake-text').fill('Keep this recoverable thought.')
        page.locator('#resume-intake-file').set_input_files({'name': 'unsupported.exe',
            'mimeType': 'application/octet-stream', 'buffer': b'not a supported document'})
        page.locator('#resume-intake-add').click()
        expect(page.locator('#resume-intake-attachments')).to_contain_text('could not be read')
        expect(page.locator('#resume-intake-attachments')).to_contain_text('unsupported.exe')
        self.assertEqual(self.server.shared.policy.list_entries('g-member-a')['entries'], [])
        page.locator('#resume-intake-hide').click()
        photo = str(Path(__file__).parent / 'fixtures/resume_media/member-photo-1200x800.jpg')
        with patch.object(self.server.shared.capture_storage, 'upload', side_effect=RuntimeError('synthetic storage unavailable')):
            page.locator('#resume-media-upload').set_input_files(photo)
            expect(page.locator('#resume-media-status')).to_have_attribute('data-kind', 'error')
            expect(page.locator('#resume-media-photos [data-action="select"]')).to_have_count(0)
        page.get_by_role('button', name='Try upload again', exact=True).click()
        expect(page.locator('#resume-media-photos li')).to_have_count(1)
        # The synthetic procedure records a rejected scanner result; actual
        # PhotoCapture and media services carry that state through the HTTP UI.
        procedures = self.server.shared.capture_procedures
        key = list(procedures.created)[-1]
        original_row = procedures._source_row
        def source_row(source_key):
            if source_key == key:
                return dict(source_key=key, state='rejected', row_version=bytes([3])*8, pixel_width=0, pixel_height=0)
            return original_row(source_key)
        procedures.rejected = True
        with patch.object(procedures, '_source_row', side_effect=source_row):
            page.get_by_role('button', name='Check scan', exact=True).click()
            expect(page.locator('#resume-media-photos')).to_contain_text('Rejected by the scan')
            expect(page.locator('#resume-media-photos [data-action="select"]')).to_have_count(0)
        self.assertEqual(self.server.shared.draft.get_workspace('g-member-a')['draft_version'], 0)
        self.assertIsNone(self.server.shared.publication.owner_preview('g-member-a')['current'])
        self.assertEqual(self.errors, [])

    def test_library_illustration_never_becomes_biographical_ai_evidence(self):
        shared = self.server.shared
        role = self.seed_role()
        photo = (Path(__file__).parent / 'fixtures/resume_media/library-illustration-1600x900.png').read_bytes()
        stored = shared.media_storage.put('g-library', photo, content_type='image/png')
        asset = shared.media_sources.seed_catalog_asset(asset_id=str(uuid4()), label='Fictional mountain expedition',
            category='nature', tags=('climbed Everest',), width=1600, height=900, digest=stored['digest'],
            derivatives=[dict(slot='experience_support', ref='g-library', digest=stored['digest'],
                content_type='image/png', byte_length=len(photo))])
        shared.publication.catalog.put(asset)
        page = self.page('g-member-a')
        page.goto(self.server.url + '/app/resume')
        page.locator('#resume-intake-hide').click()
        page.locator('#resume-media-tab-library').click()
        card = page.locator('#resume-media-panel-library li').first
        expect(card).to_contain_text('Fictional mountain expedition')
        card.get_by_role('button', name='Use for Experience photo', exact=True).click()
        page.locator('#resume-media-preview-placement').click()
        page.locator('#resume-media-add').click()
        expect(page.locator('#resume-media-status')).to_contain_text('Added 1')
        self.publish_choices(page, [(role, True, True)])
        guest = self.page()
        guest.goto(self.server.url + '/g-alex/resume')
        expect(guest.locator('.resume-publication__crop img')).to_have_count(1)
        guest.locator('#visitor-ai-open').click()
        guest.locator('#visitor-ai-question').fill('Did this member climb Everest?')
        guest.locator('#visitor-ai-ask').click()
        expect(guest.locator('#visitor-ai-status')).to_have_text('Answer complete.')
        submitted = str(self.server.provider.seen[-1][1])
        self.assertNotIn('Fictional mountain expedition', submitted)
        self.assertNotIn('climbed Everest', submitted)
        self.assertNotIn('Fictional mountain expedition', guest.locator('#visitor-ai-answer').inner_text())
        self.assertEqual(len(shared.policy.list_entries('g-member-a')['entries']), 1)
        self.assertEqual(self.errors, [])

    def test_abuse_limit_and_provider_database_failures_preserve_question_and_publication(self):
        import copy
        from dataclasses import replace
        key = self.seed_role()
        self.server.shared.seed_publication('g-member-a', [(key, True, True)])
        guest = self.page()
        guest.goto(self.server.url + '/g-alex/resume')
        guest.locator('#visitor-ai-open').click()
        question = 'Keep this question while unavailable.'
        guest.locator('#visitor-ai-question').fill(question)
        before = copy.deepcopy(self.server.shared.publication.repository.load_owner('g-member-a'))
        self.server.ai_runtime.limits = replace(self.server.ai_runtime.limits, requests_per_client_window=1)
        guest.locator('#visitor-ai-ask').click()
        expect(guest.locator('#visitor-ai-status')).to_have_text('Answer complete.')
        with guest.expect_response(lambda r: r.url.endswith('/ai/questions')) as limited:
            guest.locator('#visitor-ai-ask').click()
        self.assertEqual(limited.value.status, 429)
        self.assertEqual(limited.value.headers['retry-after'], '60')
        self.assertNotIn('sign in', limited.value.json()['text'].lower())
        self.server.ai_runtime.limits = replace(self.server.ai_runtime.limits, requests_per_client_window=30)
        original = self.server.provider.answer
        self.server.provider.answer = lambda *args: {'malformed': 'not a validated answer'}
        with guest.expect_response(lambda r: r.url.endswith('/ai/questions')) as malformed:
            guest.locator('#visitor-ai-ask').click()
        self.assertEqual(malformed.value.status, 503)
        self.server.provider.answer = original
        self.server.ai_database.fail = True
        with guest.expect_response(lambda r: r.url.endswith('/ai/questions')) as unavailable:
            guest.locator('#visitor-ai-ask').click()
        self.assertEqual(unavailable.value.status, 503)
        expect(guest.locator('#visitor-ai-question')).to_have_value(question)
        expect(guest.locator('#visitor-ai-answer')).to_be_empty()
        self.assertEqual(self.server.shared.publication.repository.load_owner('g-member-a'), before)
        self.assertEqual(self.errors, [])

    def test_foreign_entry_parent_photo_and_invalid_cursor_are_denied(self):
        key = self.seed_role()
        photo = self.server.shared.seed_photo('g-member-a')
        other, guest = self.page('g-member-b'), self.page()
        headers = {'X-PeerSlate-Request': 'same-origin'}
        for page in (other, guest):
            self.assertEqual(page.request.get(self.server.url + '/api/resume-media/me/photos/' + photo.source_id + '/preview').status, 404)
            forged = dict(type='save_item', request_id=str(uuid4()), record_key=key, record_type='role',
                expected_content_token='1', expected_access_revision=1,
                values={'role_title': 'Foreign', 'employer_name': 'Denied'})
            self.assertIn(page.request.post(self.server.url + '/api/resume-drafts/me/commands', data=forged, headers=headers).status, (404, 409))
        forged_child = dict(type='create_private_item', request_id=str(uuid4()), record_key=str(uuid4()),
            record_type='accomplishment', parent_key=key, values={'wording': 'Foreign parent attempt.'})
        response = other.request.post(self.server.url + '/api/resume-drafts/me/commands', data=forged_child, headers=headers)
        self.assertIn(response.status, (400, 404, 409))
        cursor = other.request.get(self.server.url + '/api/resume-media/me/library?cursor=forged-owner-cursor')
        self.assertIn(cursor.status, (400, 409))
        self.assertNotIn('Synthetic engineer', cursor.text())
        self.assertEqual(self.server.shared.policy.list_entries('g-member-b')['entries'], [])
        self.assertEqual(self.errors, [])

    def test_private_assistance_exclusion_is_independent_of_visitor_permissions(self):
        key = self.seed_role()
        self.server.shared.seed_publication('g-member-a', [(key, False, True)])
        owner = self.page('g-member-a')
        owner.goto(self.server.url + '/app/settings/my-data')
        card = owner.locator('[data-entry-key="' + key + '"]')
        card.get_by_role('button', name='Sharing', exact=True).click()
        card.get_by_text('Additional settings', exact=True).click()
        card.locator('[data-permission="private_assistance_excluded"]').check()
        card.get_by_role('button', name='Save sharing', exact=True).click()
        expect(card.locator('[data-entry-flag="excluded"]')).to_be_visible()
        row = self.server.shared.policy.get_entry('g-member-a', key)['entry']
        self.assertTrue(row['private_assistance_excluded'])
        self.assertTrue(row['visitor_ai'])
        self.assertFalse(row['resume_display'])
        guest = self.page()
        guest.goto(self.server.url + '/g-alex/resume')
        self.assertNotIn('Built a small scheduling tool.', guest.content())
        guest.locator('#visitor-ai-open').click()
        guest.locator('#visitor-ai-question').fill('What did this person build?')
        guest.locator('#visitor-ai-ask').click()
        expect(guest.locator('#visitor-ai-answer')).to_contain_text('Built a small scheduling tool.')
        self.assertEqual(self.errors, [])

    def test_thirty_day_recovery_boundary_and_failed_cleanup_retry(self):
        from datetime import datetime, timedelta, timezone
        from unittest.mock import patch
        from services.entry_policy_repository import EntryPolicyStoreUnavailable
        key = self.seed_role()
        policy = self.server.shared.policy
        now = datetime(2026, 9, 1, tzinfo=timezone.utc)
        policy.clock = lambda: now
        owner = self.page('g-member-a')
        owner.goto(self.server.url + '/app/settings/my-data')
        card = owner.locator('[data-entry-key="' + key + '"]')
        card.get_by_role('button', name='Delete', exact=True).click()
        card.locator('.my-data__confirm').get_by_role('button', name='Delete', exact=True).click()
        expect(owner.locator('[data-my-data-status]')).to_contain_text('Deleted')
        now += timedelta(days=30, microseconds=-1)
        owner.locator('[data-my-data-permission]').select_option('recently_deleted')
        owner.reload()
        owner.locator('[data-my-data-permission]').select_option('recently_deleted')
        expect(card.get_by_role('button', name='Restore', exact=True)).to_be_visible()
        now += timedelta(microseconds=1)
        before = policy.repository.load_owner('g-member-a')
        with patch.object(policy.repository, 'save_owner', side_effect=EntryPolicyStoreUnavailable('Synthetic cleanup outage')):
            refused = owner.request.get(self.server.url + '/api/entry-policy/me/entries')
            self.assertEqual(refused.status, 503)
        self.assertEqual(policy.repository.load_owner('g-member-a'), before)
        retried = owner.request.get(self.server.url + '/api/entry-policy/me/entries')
        self.assertEqual(retried.status, 200)
        self.assertEqual(retried.json()['entries'], [])
        owner.reload()
        owner.locator('[data-my-data-permission]').select_option('recently_deleted')
        expect(card).to_have_count(0)
        self.assertEqual(policy.sweep_expired('g-member-a')['expired_count'], 0)
        self.assertEqual(self.errors, [])

    def test_lost_editor_save_response_retries_same_command_and_retains_words(self):
        key = self.seed_role()
        page = self.page('g-member-a')
        page.goto(self.server.url + '/app/resume')
        page.locator('#resume-intake-hide').click()
        page.locator(".resume-editor__card").filter(has=page.locator('[id="' + key + '-summary"]')).locator("summary").click()
        field = page.locator('[id="' + key + '-summary"]')
        field.fill('Recover this exact private draft.')
        card = page.locator('article').filter(has=field)
        requests = []
        def lose_once(route):
            requests.append(route.request.post_data_json)
            if len(requests) == 1:
                self.assertEqual(route.fetch().status, 200)
                route.abort('connectionfailed')
            else:
                route.continue_()
        page.route('**/api/resume-drafts/me/commands', lose_once)
        card.get_by_role('button', name='Save draft', exact=True).click()
        expect(page.locator('#resume-editor-status')).to_contain_text('response did not arrive')
        expect(field).to_have_value('Recover this exact private draft.')
        expect(field).to_be_disabled()
        card.get_by_role('button', name='Retry same save', exact=True).click()
        expect(page.locator('#resume-editor-status')).to_contain_text('Draft saved')
        self.assertEqual(requests[0], requests[1])
        draft = self.server.shared.draft.repository.load_owner('g-member-a')
        self.assertEqual(draft['draft_version'], 1)
        self.assertEqual(len(draft['receipts']), 1)
        page.reload()
        expect(field).to_have_value('Recover this exact private draft.')
        self.assertFalse(self.server.shared.policy.get_entry('g-member-a', key)['entry']['resume_display'])
        self.assertEqual(self.errors, [])

    def test_lost_publish_response_retries_exact_receipt_without_reenabling_sharing(self):
        key = self.seed_role()
        page = self.page("g-member-a")
        page.goto(self.server.url + "/app/resume/publication")
        page.locator("#resume-publication-review-button").click()
        page.locator('[data-entry-key="' + key + '"] [data-permission="resume_display"]').check()
        page.locator("#resume-publication-review-button").click()
        expect(page.locator("#resume-publication-publish-button")).to_be_enabled()
        page.locator("#resume-publication-slug").fill("g-alex")
        requests = []
        def lose_once(route):
            requests.append(route.request.post_data_json)
            if len(requests) == 1:
                # The real Flask request commits. Only its transport response
                # is dropped, modeling a disconnect after the server write.
                response = route.fetch()
                self.assertEqual(response.status, 200)
                route.abort("connectionfailed")
            else:
                route.continue_()
        page.route("**/api/resume-publication/me/commands", lose_once)
        page.locator("#resume-publication-publish-button").click()
        expect(page.locator("#resume-publication-status")).to_contain_text("response was interrupted")
        service = self.server.shared.publication
        committed = service.repository.load_owner("g-member-a")
        self.assertEqual(committed["publication_revision"], 1)
        service.commit("g-member-a", dict(type="sharing_off", request_id=str(uuid4())))
        after_off = service.repository.load_owner("g-member-a")
        page.locator("#resume-publication-publish-button").click()
        expect(page.locator("#resume-publication-status")).to_contain_text("Sharing is currently off")
        self.assertEqual(requests[0], requests[1])
        current = service.repository.load_owner("g-member-a")
        self.assertEqual(current["publication_revision"], after_off["publication_revision"])
        self.assertEqual(len(current["receipts"]), 2)
        changed = dict(requests[0], slug="different-slug")
        response = page.request.post(self.server.url + "/api/resume-publication/me/commands", data=changed,
            headers={"X-PeerSlate-Request": "same-origin"})
        self.assertEqual(response.status, 409)
        self.assertEqual(self.page().request.get(self.server.url + "/g-alex/resume").status, 404)
        self.assertEqual(self.errors, [])


if __name__ == "__main__":
    unittest.main()
