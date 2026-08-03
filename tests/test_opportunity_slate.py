"""Contract tests for Opportunity Slate — PS-OPPSLATE-001, slice OS-1.

Covers the flag gate, the two modes (signed-in private workbench and the
anonymous public session), the owner-only mutation boundary, the same-origin
write guard, the failure contracts, and the unlisted/no-store header
posture. Everything is mocked at the
``services/opportunity_slate_service.py`` boundary, so no database is
required.

Every behavioural test uses a generic fixture member key, never a
Pete-specific identifier (tests/test_site_rules.py's OwnershipGuardrailTests
enforces that separately for reusable service/route code).
"""

import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app import app, limiter
from services.database_service import DatabaseServiceError
from services.opportunity_slate_service import (
    MAX_SOURCE_TEXT_UNITS,
    OpportunitySlateServiceError,
    WorkingSourceView,
)


SESSION_KEY = "11111111-1111-1111-1111-111111111111"
SOURCE_KEY = "22222222-2222-2222-2222-222222222222"
SESSION_TOKEN = "0000000000000001"
SOURCE_TOKEN = "0000000000000002"
SAME_ORIGIN_HEADERS = {"Origin": "http://localhost", "Sec-Fetch-Site": "same-origin"}

ROLE_TEXT = (
    "Overview\n\n"
    "We design and sustain complex systems.\n\n"
    "Required qualifications\n\n"
    "- Bachelor's degree in Engineering\n"
    "- 3 years of relevant experience\n"
)

# Every route this slice adds, with the method it answers. Used by the
# flag-off and header tests so a future route cannot be added without being
# covered by both.
ROOM_GET = "/opportunity-slate"
MEMBER_POSTS = (
    "/opportunity-slate/source",
    "/opportunity-slate/source/corrections",
    "/opportunity-slate/source/confirm",
    "/opportunity-slate/source/delete",
)
PUBLIC_POST = "/opportunity-slate/public-session"


def member(name="Opportunity Slate Test Member", user_key="member-oppslate-1"):
    return SimpleNamespace(display_name=name, user_key=user_key)


def working_view(**overrides):
    fields = {
        "working_session_key": SESSION_KEY,
        "session_version_token": SESSION_TOKEN,
        "workbench_state": "review_source",
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=48),
        "source_key": SOURCE_KEY,
        "source_version_token": SOURCE_TOKEN,
        "version_number": 1,
        "confirmed_version_number": None,
        "confirmed_at": None,
        "capture_method": "pasted",
        "original_text": ROLE_TEXT,
        "member_corrected_text": None,
        "corrected_at": None,
        "captured_at": datetime.now(timezone.utc),
    }
    fields.update(overrides)
    return WorkingSourceView(**fields)


class OpportunitySlateTestCase(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.original_flag = app.config.get("PEERSLATE_OPPORTUNITY_SLATE_ENABLED")
        app.config["PEERSLATE_OPPORTUNITY_SLATE_ENABLED"] = True
        # These functional tests repeatedly POST to the same rate-limited
        # routes; the limiter's counter is process-wide and would otherwise
        # accumulate across unrelated tests and spuriously 429 them.
        # Disabled here (the test_workshop_flows.py pattern); the dedicated
        # rate-limit registration test below does not need it enabled.
        self._limiter_enabled = limiter.enabled
        limiter.enabled = False

    def tearDown(self):
        limiter.enabled = self._limiter_enabled
        app.config["PEERSLATE_OPPORTUNITY_SLATE_ENABLED"] = self.original_flag

    def anonymous(self):
        return patch(
            "opportunity_slate_routes.get_optional_identity", return_value=None
        )

    def signed_in(self, identity=None):
        return patch(
            "opportunity_slate_routes.get_optional_identity",
            return_value=identity or member(),
        )

    def service(self):
        return patch("opportunity_slate_routes.opportunity_slate_service")


class FlagGateTests(OpportunitySlateTestCase):
    def test_flag_off_returns_404_on_every_route(self):
        app.config["PEERSLATE_OPPORTUNITY_SLATE_ENABLED"] = False
        self.assertEqual(self.client.get(ROOM_GET).status_code, 404)
        for path in MEMBER_POSTS + (PUBLIC_POST,):
            with self.subTest(path=path):
                response = self.client.post(path, headers=SAME_ORIGIN_HEADERS)
                self.assertEqual(response.status_code, 404)

    def test_flag_check_runs_before_any_identity_resolution(self):
        """Flag-off must be indistinguishable from not-found, which means it
        cannot depend on resolving who is asking first."""
        app.config["PEERSLATE_OPPORTUNITY_SLATE_ENABLED"] = False
        with patch("opportunity_slate_routes.get_optional_identity") as resolve:
            self.client.get(ROOM_GET)
            for path in MEMBER_POSTS + (PUBLIC_POST,):
                self.client.post(path, headers=SAME_ORIGIN_HEADERS)
        resolve.assert_not_called()


class HeaderPostureTests(OpportunitySlateTestCase):
    def test_room_is_noindex_and_unstorable_in_public_mode(self):
        with self.anonymous():
            response = self.client.get(ROOM_GET)
        self.assertEqual(response.status_code, 200)
        self.assertIn("noindex", response.headers["X-Robots-Tag"])
        self.assertIn("nofollow", response.headers["X-Robots-Tag"])
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")

    def test_room_is_noindex_and_unstorable_in_member_mode(self):
        with self.signed_in(), self.service() as service:
            service.get_working_session_for_owner.return_value = None
            response = self.client.get(ROOM_GET)
        self.assertEqual(response.status_code, 200)
        self.assertIn("noindex", response.headers["X-Robots-Tag"])
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")

    def test_meta_robots_accompanies_the_header(self):
        """The route is top-level, so robots.txt's "Disallow: /app" umbrella
        does not cover it. Handoff section 18 safeguard 4 requires both the
        header and the meta tag."""
        with self.anonymous():
            body = self.client.get(ROOM_GET).data.decode("utf-8")
        self.assertIn('<meta name="robots" content="noindex, nofollow, noarchive">', body)

    def test_the_room_is_not_in_the_sitemap_and_not_in_navigation(self):
        sitemap = self.client.get("/sitemap.xml").data.decode("utf-8")
        self.assertNotIn("opportunity-slate", sitemap)
        home = self.client.get("/").data.decode("utf-8")
        self.assertNotIn("/opportunity-slate", home)

    def test_no_route_path_looks_like_a_job_surface(self):
        """Rule 34 / handoff section 1: not a job board. Guarded globally by
        tests/test_site_rules.py; asserted here too so this package owns its
        own boundary."""
        for rule in app.url_map.iter_rules():
            if "opportunity" not in rule.rule:
                continue
            path = rule.rule.lower()
            for banned in ("/job", "/jobs", "/hiring", "/listing"):
                self.assertNotIn(banned, path, f"{rule.rule} looks like a job surface")


class AnonymousPublicSessionTests(OpportunitySlateTestCase):
    def test_room_serves_the_public_session_to_a_signed_out_visitor(self):
        with self.anonymous():
            response = self.client.get(ROOM_GET)
        body = response.data.decode("utf-8")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Public session", body)
        self.assertIn("Nothing is stored on PeerSlate", body)
        self.assertIn("Bring a role", body)

    def test_the_public_truth_copy_separates_transit_from_storage(self):
        """Independent review, MAJOR 2: the room said "Your text stays in
        this browser tab."

        It does not. Every anonymous action POSTs that text to
        /opportunity-slate/public-session, and the server signs it into the
        context token it hands back. Nothing is *stored*, which is the
        promise that matters — but the sentence as written claimed the text
        never leaves the tab, and a visitor deciding whether to paste a
        confidential role posting was entitled to know it does. The
        corrected copy states both truths separately.

        Focused recheck, residual finding: the role="status" banner at the top
        of every anonymous screen was left telling the old story ("keeps your
        role text in your own browser for this visit only"), so the loudest,
        first-read sentence on the surface still produced the inference MAJOR 2
        rejected while the truth card below it told the corrected one. The
        banner now names the transit before it claims the locality, and both
        halves are asserted here so a future edit cannot quietly restore the
        locality-only shape on either element.
        """
        with self.anonymous():
            body = self.client.get(ROOM_GET).data.decode("utf-8")
        text = " ".join(body.split())

        self.assertIn(
            "Your text is sent to PeerSlate to draw this screen, and never stored.",
            text,
        )
        self.assertIn("The only copy kept is in this browser tab.", text)
        self.assertIn(
            "Sent to PeerSlate to draw this screen, and never stored there. "
            "The only copy kept is in this browser tab.",
            text,
        )
        self.assertIn(
            "This preview sends your role text to PeerSlate to draw each screen. "
            "The only copy kept is in your own browser, for this visit only.",
            text,
        )
        self.assertIn(
            "Nothing is stored on PeerSlate, nothing is analyzed, and nothing is "
            "shared or sent to an employer.",
            text,
        )
        for false_claim in (
            "Your text stays in this browser tab",
            "It is never sent to PeerSlate storage",
            "never leaves this browser",
            # The superseded banner sentence, in whole and in the fragment
            # that carried the false inference. Deliberately narrower than
            # the <noscript> wording ("keeps your role text in your browser,
            # which needs JavaScript"), which stays accurate: with JavaScript
            # off nothing is ever sent.
            "This preview keeps your role text in your own browser",
            "keeps your role text in your own browser for this visit only",
        ):
            self.assertNotIn(false_claim, text)

    def test_the_step_handler_cannot_swallow_every_click_in_the_room(self):
        """Found while re-capturing evidence, outside the accepted finding
        list: the room container carries data-os-step as STATE, and the
        delegated click handler looked it up with a bare '[data-os-step]'.
        closest() therefore matched the container from any click in the
        public session — including the "Review source" submit button — so
        the handler called preventDefault() and posted a no-op step
        re-render instead. The visitor's typed text was discarded and the
        anonymous flow could not get past intake.

        The handler now matches anchors only, which is what every real step
        control is. The browser evidence for the public review screen is the
        end-to-end proof; this holds the contract in the ordinary test run.
        """
        script = (
            Path(app.root_path) / "static" / "js" / "opportunity-slate.js"
        ).read_text(encoding="utf-8")
        self.assertIn("closestFrom(event.target, 'a[data-os-step]')", script)
        self.assertNotIn("closestFrom(event.target, '[data-os-step]')", script)

        with self.anonymous():
            body = self.client.get(ROOM_GET).data.decode("utf-8")
        # The container still carries the state attribute — that is the
        # ambiguity the selector above has to tolerate, not remove.
        self.assertIn('data-os-step="role"', body)
        for control in ("data-os-primary", 'data-os-form="source"'):
            self.assertIn(control, body)

    def test_public_room_states_its_javascript_requirement(self):
        with self.anonymous():
            body = self.client.get(ROOM_GET).data.decode("utf-8")
        self.assertIn("<noscript>", body)
        self.assertIn("JavaScript is off", body)

    def test_public_intake_renders_upload_and_import_as_honest_states(self):
        """Handoff section 18 safeguard 1: upload and import stay off the
        anonymous route entirely. They render as a stated unavailable state,
        never as a control that pretends to work."""
        with self.anonymous():
            body = self.client.get(ROOM_GET).data.decode("utf-8")
        self.assertIn("Upload document", body)
        self.assertIn("Import public link", body)
        self.assertEqual(body.count("Available with membership"), 2)
        self.assertNotIn('type="file"', body)

    def test_microphone_is_present_but_honestly_inert(self):
        with self.anonymous():
            body = self.client.get(ROOM_GET).data.decode("utf-8")
        self.assertIn('data-os-inert-mic', body)
        self.assertIn('aria-disabled="true"', body)
        self.assertIn("Dictation arrives in a later update", body)

    def test_public_flow_captures_reviews_and_confirms_a_role(self):
        with self.anonymous():
            captured = self.client.post(
                PUBLIC_POST,
                json={"action": "source", "source_text": ROLE_TEXT, "step": "review"},
                headers=SAME_ORIGIN_HEADERS,
            ).get_json()
            self.assertTrue(captured["success"])
            self.assertEqual(captured["step"], "review")
            self.assertTrue(captured["context_token"])
            self.assertIn("Reviewed source", captured["html"])
            self.assertIn("Source Version 1", captured["html"])

            confirmed = self.client.post(
                PUBLIC_POST,
                json={
                    "action": "confirm",
                    "context_token": captured["context_token"],
                    "step": "review",
                },
                headers=SAME_ORIGIN_HEADERS,
            ).get_json()
        self.assertIn("You confirmed Source Version 1", confirmed["html"])
        self.assertIn("is not built yet", confirmed["html"])

    def test_public_correction_keeps_the_original_wording(self):
        with self.anonymous():
            captured = self.client.post(
                PUBLIC_POST,
                json={"action": "source", "source_text": ROLE_TEXT, "step": "review"},
                headers=SAME_ORIGIN_HEADERS,
            ).get_json()
            corrected = self.client.post(
                PUBLIC_POST,
                json={
                    "action": "correct",
                    "context_token": captured["context_token"],
                    "corrected_text": "Corrected employer wording.",
                    "step": "review",
                },
                headers=SAME_ORIGIN_HEADERS,
            ).get_json()
        self.assertTrue(corrected["success"])
        self.assertIn("Corrected employer wording.", corrected["html"])
        # The verbatim original is still on the screen, in the correction
        # pairing and the compare view.
        self.assertIn("We design and sustain complex systems.", corrected["html"])
        self.assertIn("Compare with original", corrected["html"])

    def test_a_tampered_or_missing_token_resets_honestly(self):
        for token in (None, "", "not-a-real-token", "x" * 500):
            with self.subTest(token=token), self.anonymous():
                payload = self.client.post(
                    PUBLIC_POST,
                    json={"action": "confirm", "context_token": token},
                    headers=SAME_ORIGIN_HEADERS,
                ).get_json()
            self.assertTrue(payload["reset"])
            self.assertIsNone(payload["context_token"])
            self.assertIn("Bring a role", payload["html"])
            self.assertIn("Nothing was stored", payload["message"])

    def test_discard_clears_the_public_session(self):
        with self.anonymous():
            captured = self.client.post(
                PUBLIC_POST,
                json={"action": "source", "source_text": ROLE_TEXT, "step": "review"},
                headers=SAME_ORIGIN_HEADERS,
            ).get_json()
            discarded = self.client.post(
                PUBLIC_POST,
                json={"action": "discard", "context_token": captured["context_token"]},
                headers=SAME_ORIGIN_HEADERS,
            ).get_json()
        self.assertTrue(discarded["reset"])
        self.assertIsNone(discarded["context_token"])
        self.assertNotIn("Reviewed source", discarded["html"])

    def test_oversize_public_input_is_named_and_preserves_the_text(self):
        oversize = "x" * (MAX_SOURCE_TEXT_UNITS + 1)
        with self.anonymous():
            response = self.client.post(
                PUBLIC_POST,
                json={"action": "source", "source_text": oversize, "step": "review"},
                headers=SAME_ORIGIN_HEADERS,
            )
        payload = response.get_json()
        self.assertEqual(response.status_code, 400)
        self.assertFalse(payload["success"])
        self.assertIn("longer than", payload["html"])
        self.assertIn(oversize, payload["html"])

    def test_public_session_rejects_a_cross_site_post(self):
        with self.anonymous():
            response = self.client.post(
                PUBLIC_POST, json={"action": "render"}
            )
        self.assertEqual(response.status_code, 403)

    def test_public_session_is_not_offered_to_a_signed_in_member(self):
        with self.signed_in():
            response = self.client.post(
                PUBLIC_POST, json={"action": "render"}, headers=SAME_ORIGIN_HEADERS
            )
        self.assertEqual(response.status_code, 404)

    def test_an_unknown_action_is_refused(self):
        with self.anonymous():
            response = self.client.post(
                PUBLIC_POST, json={"action": "save"}, headers=SAME_ORIGIN_HEADERS
            )
        self.assertEqual(response.status_code, 400)

    def test_anonymous_mode_never_reaches_the_database_service(self):
        """Handoff section 18: the public session touches no stored
        procedure, in any of its actions.

        Asserted against BOTH seams — the Opportunity Slate service singleton
        the routes hold, and the shared database_service the service module
        itself would call — so neither a route change nor a service change
        can quietly open a path.
        """
        service_mock = MagicMock()
        database_mock = MagicMock()
        with self.anonymous(), patch(
            "opportunity_slate_routes.opportunity_slate_service", service_mock
        ), patch(
            "services.opportunity_slate_service.database_service", database_mock
        ):
            self.client.get(ROOM_GET)
            captured = self.client.post(
                PUBLIC_POST,
                json={"action": "source", "source_text": ROLE_TEXT, "step": "review"},
                headers=SAME_ORIGIN_HEADERS,
            ).get_json()
            token = captured["context_token"]
            for payload in (
                {"action": "render", "context_token": token},
                {"action": "step", "context_token": token, "step": "role"},
                {
                    "action": "correct",
                    "context_token": token,
                    "corrected_text": "Corrected.",
                },
                {"action": "confirm", "context_token": token},
                {"action": "discard", "context_token": token},
            ):
                self.client.post(
                    PUBLIC_POST, json=payload, headers=SAME_ORIGIN_HEADERS
                )

        self.assertEqual(service_mock.method_calls, [])
        self.assertEqual(database_mock.method_calls, [])


class OwnerOnlyBoundaryTests(OpportunitySlateTestCase):
    def test_member_posts_are_neutral_404_when_signed_out(self):
        """A signed-out caller cannot tell "not signed in" from "not found"
        from "flag off" (require_identity_or_not_found semantics)."""
        with self.anonymous():
            for path in MEMBER_POSTS:
                with self.subTest(path=path):
                    response = self.client.post(path, headers=SAME_ORIGIN_HEADERS)
                    self.assertEqual(response.status_code, 404)

    def test_member_posts_reject_a_cross_site_request(self):
        with self.signed_in(), self.service():
            for path in MEMBER_POSTS:
                with self.subTest(path=path):
                    self.assertEqual(self.client.post(path).status_code, 403)
                    self.assertEqual(
                        self.client.post(
                            path, headers={"Sec-Fetch-Site": "cross-site"}
                        ).status_code,
                        403,
                    )
                    self.assertEqual(
                        self.client.post(
                            path, headers={"Origin": "https://evil.example"}
                        ).status_code,
                        403,
                    )

    def test_a_signed_out_post_never_reaches_the_service(self):
        service_mock = MagicMock()
        with self.anonymous(), patch(
            "opportunity_slate_routes.opportunity_slate_service", service_mock
        ):
            for path in MEMBER_POSTS:
                self.client.post(path, headers=SAME_ORIGIN_HEADERS)
        self.assertEqual(service_mock.method_calls, [])


class MemberFlowTests(OpportunitySlateTestCase):
    def test_a_member_with_no_working_session_lands_on_role_intake(self):
        with self.signed_in(), self.service() as service:
            service.get_working_session_for_owner.return_value = None
            body = self.client.get(ROOM_GET).data.decode("utf-8")
        self.assertIn("Bring a role", body)
        self.assertIn("Session private", body)
        self.assertIn("Nothing is saved yet.", body)
        self.assertNotIn("Public session", body)

    def test_the_room_purges_this_owners_expired_working_data(self):
        identity = member()
        with self.signed_in(identity), self.service() as service:
            service.get_working_session_for_owner.return_value = None
            self.client.get(ROOM_GET)
        service.purge_expired_working_data_for_owner.assert_called_once_with(
            identity.user_key
        )

    def test_a_purge_failure_never_denies_the_member_their_room(self):
        with self.signed_in(), self.service() as service:
            service.purge_expired_working_data_for_owner.side_effect = (
                DatabaseServiceError("purge failed")
            )
            service.get_working_session_for_owner.return_value = None
            response = self.client.get(ROOM_GET)
        self.assertEqual(response.status_code, 200)

    def test_capturing_a_role_redirects_into_review_source(self):
        identity = member()
        with self.signed_in(identity), self.service() as service:
            response = self.client.post(
                "/opportunity-slate/source",
                data={"source_text": ROLE_TEXT, "idempotency_key": "fixture-key-1"},
                headers=SAME_ORIGIN_HEADERS,
            )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], ROOM_GET)
        service.save_source_for_owner.assert_called_once()
        args = service.save_source_for_owner.call_args[0]
        self.assertEqual(args[0], identity.user_key)
        self.assertEqual(args[1], "fixture-key-1")
        self.assertEqual(args[2], ROLE_TEXT.strip())

    def test_review_source_renders_the_verbatim_text_and_checkpoint(self):
        with self.signed_in(), self.service() as service:
            service.get_working_session_for_owner.return_value = working_view()
            body = self.client.get(ROOM_GET).data.decode("utf-8")
        self.assertIn("Reviewed source", body)
        self.assertIn("Checkpoint 1 of 2", body)
        self.assertIn("Source Version 1", body)
        self.assertIn("Bachelor&#39;s degree in Engineering", body)
        self.assertIn("Return to role input", body)
        self.assertIn("Replace source", body)
        self.assertIn("Delete source", body)
        self.assertIn("Confirm source", body)
        self.assertIn("nothing was added, removed, or reworded", body)

    def test_the_extraction_concern_card_never_claims_a_concern(self):
        """Owner visual-parity pass, 2026-08-03 (finding V13).

        The locked authority's extraction-concern card is a structural part
        of Review Source, so its placement, geometry and styling ship now.
        Its CONTENT is an AI proposal and arrives with slice OS-2. This
        slice runs no AI, so the card must render an empty state that says
        so: nothing flagged, nothing proposed, no claim that any analysis
        has run. If a future change wires real content in here, it has to
        break this test deliberately rather than drift past it.
        """
        with self.signed_in(), self.service() as service:
            service.get_working_session_for_owner.return_value = working_view()
            body = self.client.get(ROOM_GET).data.decode("utf-8")
        self.assertIn("Extraction concerns", body)
        self.assertIn("None flagged", body)
        self.assertIn("PeerSlate has not read or", body)
        for fabricated in (
            "flagged this phrase",
            "potentially extracted incorrectly",
            "1 extraction concern",
            "Extraction details",
        ):
            with self.subTest(fabricated=fabricated):
                self.assertNotIn(fabricated, body)

        # Third parity round, 2026-08-03. The card was given real substance
        # because its empty state left a visible void in the margin beside
        # it. The substance is what the MEMBER is being asked to check, in
        # the present tense. The obvious wrong way to fill that space is a
        # promise about what PeerSlate will detect once OS-2 lands, which
        # would be a specification invented at the stylesheet level and
        # would read, to a member, as a capability that exists. Both the
        # honest framing and the absence of the dishonest one are asserted.
        self.assertIn("What to look for as you read", body)
        for invented_capability in (
            "PeerSlate will check",
            "PeerSlate will flag",
            "PeerSlate checks",
            "we will check",
            "we checked",
            "has been checked",
        ):
            with self.subTest(invented_capability=invented_capability):
                self.assertNotIn(invented_capability, body)

    def test_the_extraction_concern_card_is_tied_to_the_source_it_describes(self):
        """Owner visual-parity pass, second round, 2026-08-03.

        Image 02 draws a dashed leader from this card to the phrase it
        flags. Handoff section 14-M10 replaces that with adjacency, a
        shared accent, and programmatic association, and the empty state
        forces the issue: with nothing flagged there is no phrase to point
        at, so the association has to be carried by structure.

        The card therefore lives in a named <aside> whose accessible name
        is the card's own heading, and that heading is a real heading in
        the document outline rather than a styled paragraph. Both are what
        make the card announceable and navigable as a note about this
        source instead of an unlabelled box floating in the margin, so
        both are asserted here rather than left to the stylesheet.
        """
        with self.signed_in(), self.service() as service:
            service.get_working_session_for_owner.return_value = working_view()
            body = self.client.get(ROOM_GET).data.decode("utf-8")
        aside = body.split("<aside", 1)[1].split(">", 1)[0]
        self.assertIn("os-review__aside", aside)
        self.assertIn('aria-labelledby="os-concern-title"', aside)
        # The element carrying that id has to be a heading, not a styled <p>:
        # a name alone does not put the card in the document outline.
        titled = body.split('id="os-concern-title"')[0].rsplit("<", 1)[1]
        self.assertTrue(
            titled.startswith("h3"),
            f"the concern card's title must be a real heading, not <{titled.strip()}",
        )

    def test_the_decorative_props_are_never_content(self):
        """Owner decision 2026-08-03 (finding V3) restored the locked set's
        illustrations, overriding handoff §14-M5. They are ambient material:
        every one carries an empty alt and aria-hidden, so no assistive
        technology user is read a decoration and nothing about them can be
        mistaken for product state."""
        with self.signed_in(), self.service() as service:
            service.get_working_session_for_owner.return_value = None
            body = self.client.get(ROOM_GET).data.decode("utf-8")
        self.assertIn("images/opportunity-slate/prop-source-review.png", body)
        self.assertIn("images/opportunity-slate/prop-ambient-stone.png", body)
        prop_tags = [
            fragment.split(">")[0]
            for fragment in body.split("<img")[1:]
            if "images/opportunity-slate/" in fragment.split(">")[0]
        ]
        self.assertEqual(len(prop_tags), 2)
        for tag in prop_tags:
            with self.subTest(tag=tag[:80]):
                self.assertIn('alt=""', tag)
                self.assertIn('aria-hidden="true"', tag)

    def test_no_ai_processing_stage_rail_is_rendered(self):
        """There is no AI call in this slice, so there are no stages to
        show. Rendering "Extracting employer wording..." would be theatre."""
        with self.signed_in(), self.service() as service:
            service.get_working_session_for_owner.return_value = working_view()
            body = self.client.get(ROOM_GET).data.decode("utf-8")
        for invented in (
            "os-stage-rail",
            "Extracting employer wording",
            "Preparing source review",
            "Analyzing",
        ):
            self.assertNotIn(invented, body)

    def test_a_correction_keeps_the_original_and_flags_the_change(self):
        with self.signed_in(), self.service() as service:
            service.get_working_session_for_owner.return_value = working_view(
                member_corrected_text="Corrected employer wording.",
                corrected_at=datetime.now(timezone.utc),
            )
            body = self.client.get(ROOM_GET).data.decode("utf-8")
        self.assertIn("Corrected employer wording.", body)
        self.assertIn("We design and sustain complex systems.", body)
        self.assertIn("Compare with original", body)
        self.assertIn("The wording you", body)

    def test_confirming_the_source_shows_an_honest_next_step(self):
        with self.signed_in(), self.service() as service:
            service.get_working_session_for_owner.return_value = working_view(
                confirmed_version_number=1,
                confirmed_at=datetime.now(timezone.utc),
                workbench_state="source_confirmed",
            )
            body = self.client.get(ROOM_GET).data.decode("utf-8")
        self.assertIn("You confirmed Source Version 1", body)
        self.assertIn("Source confirmed", body)
        self.assertIn("is not built yet", body)
        self.assertIn("data-os-inert-next", body)
        # The confirm form is gone, replaced by the honestly inert control.
        # Asserted against the form, not the button's text node: the owner
        # visual-parity pass (2026-08-03) gave the primary the authority's
        # trailing arrow, so the button no longer ends "Confirm source</button>"
        # in any state and a text-node assertion would pass vacuously.
        self.assertNotIn('data-os-form="confirm"', body)
        self.assertNotIn("Confirm source", body)

    def test_the_concern_card_is_announced_before_the_source_it_annotates(self):
        """Third owner visual-parity round, 2026-08-03.

        On the desktop composition the card and the document share one grid
        cell, so source order changes nothing visible. Below a 700px
        workbench the card stacks — and a note saying what has and has not
        been checked belongs in front of two thousand words of the member's
        own text, not behind them. That is also the order a screen-reader
        user gets at every width.

        Asserted on the markup rather than left to the stylesheet, because
        the ordering is a source-order property: no CSS `order` value can
        deliver it without decoupling the visual and reading orders, which
        is the thing being avoided.
        """
        with self.signed_in(), self.service() as service:
            service.get_working_session_for_owner.return_value = working_view()
            body = self.client.get(ROOM_GET).data.decode("utf-8")
        review = body.split('class="os-review"', 1)[1]
        self.assertLess(
            review.index("os-review__aside"),
            review.index("os-source-doc"),
            "the extraction-concern aside must precede the source document "
            "in source order, so it is read and stacked before it",
        )

    def test_each_screen_carries_its_own_layout_proportion(self):
        """Third owner visual-parity round, 2026-08-03 (owner gap 1).

        The locked set does not use one workbench proportion for both
        screens: image 01 holds 53.2% of the frame and image 02 holds
        64.6%, because one is an intake form and the other is a reading
        document. A single shared compromise matched neither, which is the
        finding this round was opened to resolve.

        The review geometry rides on a modifier class gated by exactly the
        condition that selects the review partial. This asserts the two
        cannot come apart — a review screen without the modifier would
        silently render at the intake screen's proportions.
        """
        with self.signed_in(), self.service() as service:
            service.get_working_session_for_owner.return_value = working_view()
            review = self.client.get(ROOM_GET).data.decode("utf-8")
            service.get_working_session_for_owner.return_value = None
            intake = self.client.get(ROOM_GET).data.decode("utf-8")
        self.assertIn("Reviewed source", review)
        self.assertIn("os-layout os-layout--review", review)
        self.assertIn("Bring a role", intake)
        self.assertIn('class="os-layout"', intake)
        self.assertNotIn("os-layout--review", intake)

    def test_return_to_role_input_prefills_and_replace_starts_empty(self):
        with self.signed_in(), self.service() as service:
            service.get_working_session_for_owner.return_value = working_view()
            prefilled = self.client.get(f"{ROOM_GET}?step=role").data.decode("utf-8")
            replacing = self.client.get(f"{ROOM_GET}?step=replace").data.decode("utf-8")
        self.assertIn("We design and sustain complex systems.", prefilled)
        self.assertIn("Bring a role", prefilled)
        self.assertIn("This replaces the role you", replacing)
        self.assertNotIn("We design and sustain complex systems.", replacing)

    def test_an_unrecognized_step_falls_back_neutrally(self):
        with self.signed_in(), self.service() as service:
            service.get_working_session_for_owner.return_value = working_view()
            body = self.client.get(f"{ROOM_GET}?step=alignment").data.decode("utf-8")
        self.assertIn("Reviewed source", body)


class ReviewSourceStructureTests(OpportunitySlateTestCase):
    """Structure and affordance corrections from independent review."""

    def _review_body(self, **view_overrides):
        with self.signed_in(), self.service() as service:
            service.get_working_session_for_owner.return_value = working_view(
                **view_overrides
            )
            return self.client.get(ROOM_GET).data.decode("utf-8")

    def test_review_actions_address_the_disclosure_not_its_hidden_body(self):
        """Independent review, MINOR 3: the rail and footer actions pointed
        at #os-compare-body and #os-delete-body — ids on divs inside a
        collapsed <details>, so the fragment target was display:none and
        clicking the action visibly did nothing.

        They now address the <details> element itself, which at least
        scrolls to the control with JavaScript off, and carry data-os-reveal
        so the room script opens the disclosure and moves focus to its
        summary.
        """
        body = self._review_body(
            member_corrected_text="Corrected wording.",
            corrected_at=datetime.now(timezone.utc),
        )
        for dead_target in ('href="#os-compare-body"', 'href="#os-delete-body"'):
            self.assertNotIn(dead_target, body)
        self.assertIn('href="#os-compare" data-os-reveal="os-compare"', body)
        # The rail action and the footer action both reveal the same
        # disclosure.
        self.assertEqual(body.count('data-os-reveal="os-delete"'), 2)
        self.assertIn('id="os-compare"', body)
        self.assertIn('id="os-delete"', body)

    def test_the_original_wording_container_is_a_labelled_region(self):
        """Independent review, MINOR 5: role="group" announces a set of
        related controls. This is a scrollable read-only block of the
        employer's own wording — a labelled region. The label and the
        keyboard-scrollable tabindex are unchanged."""
        body = self._review_body()
        self.assertIn(
            '<div class="os-pair__original" role="region" '
            'aria-labelledby="os-original-label" tabindex="0">',
            body,
        )
        self.assertNotIn('class="os-pair__original" role="group"', body)

    def test_each_room_state_renders_exactly_one_h1(self):
        with self.signed_in(), self.service() as service:
            service.get_working_session_for_owner.return_value = None
            intake = self.client.get(ROOM_GET).data.decode("utf-8")
        review = self._review_body()
        with self.anonymous():
            public = self.client.get(ROOM_GET).data.decode("utf-8")
        for state, body in (
            ("intake", intake),
            ("review", review),
            ("public intake", public),
        ):
            with self.subTest(state=state):
                self.assertEqual(body.count("<h1"), 1)

    def test_the_review_h1_is_tied_to_the_source_not_only_the_step(self):
        """A latent structural issue rather than a live defect: the
        left-rail h1 rendered on step == 'review' alone, while the workbench
        chose between the review and intake partials on
        step == 'review' AND room.source. No route produces that combination
        today, so this is checked against the template directly — if one
        ever did, the room would have printed the rail's h1 above the intake
        partial's own."""
        from flask import render_template

        import opportunity_slate_routes as routes

        with app.test_request_context(ROOM_GET):
            room = routes._intake_room("member")
            room["step"] = "review"
            html = render_template(
                "partials/opportunity_slate/_room.html",
                room=room,
                context_token=None,
            )
        self.assertEqual(html.count("<h1"), 1)
        self.assertIn("Bring a role", html)
        self.assertNotIn("Checkpoint 1 of 2", html)


class MemberFailureContractTests(OpportunitySlateTestCase):
    def test_a_storage_failure_on_the_room_is_a_truthful_503(self):
        with self.signed_in(), self.service() as service:
            service.get_working_session_for_owner.side_effect = DatabaseServiceError(
                "read failed"
            )
            response = self.client.get(ROOM_GET)
        body = response.data.decode("utf-8")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.headers["Retry-After"], "5")
        self.assertIn("We couldn&#39;t open your Opportunity Slate.", body)
        self.assertIn("Nothing was saved", body)

    def test_a_storage_failure_on_capture_preserves_the_members_text(self):
        with self.signed_in(), self.service() as service:
            service.save_source_for_owner.side_effect = DatabaseServiceError(
                "write failed"
            )
            response = self.client.post(
                "/opportunity-slate/source",
                data={"source_text": ROLE_TEXT, "idempotency_key": "fixture-key-2"},
                headers=SAME_ORIGIN_HEADERS,
            )
        body = response.data.decode("utf-8")
        self.assertEqual(response.status_code, 503)
        self.assertIn("We design and sustain complex systems.", body)

    def test_oversize_input_is_refused_by_name_with_the_text_preserved(self):
        oversize = "x" * (MAX_SOURCE_TEXT_UNITS + 1)
        service_mock = MagicMock()
        with self.signed_in(), patch(
            "opportunity_slate_routes.opportunity_slate_service", service_mock
        ):
            response = self.client.post(
                "/opportunity-slate/source",
                data={"source_text": oversize, "idempotency_key": "fixture-key-3"},
                headers=SAME_ORIGIN_HEADERS,
            )
        body = response.data.decode("utf-8")
        self.assertEqual(response.status_code, 400)
        self.assertIn(f"longer than {MAX_SOURCE_TEXT_UNITS:,} characters", body)
        self.assertIn(oversize, body)
        # Rejected before any round trip.
        service_mock.save_source_for_owner.assert_not_called()

    def test_the_failure_card_and_the_field_marker_say_different_things(self):
        """The card carries the full explanation and the field carries the
        short, specific instruction it is programmatically described by —
        repeating one sentence twice would be noise, not redundancy."""
        with self.signed_in(), self.service():
            body = self.client.post(
                "/opportunity-slate/source",
                data={
                    "source_text": "x" * (MAX_SOURCE_TEXT_UNITS + 1),
                    "idempotency_key": "fixture-key-5",
                },
                headers=SAME_ORIGIN_HEADERS,
            ).data.decode("utf-8")
        self.assertIn(
            f"That role text is longer than {MAX_SOURCE_TEXT_UNITS:,} characters", body
        )
        self.assertIn(f"Shorten this to {MAX_SOURCE_TEXT_UNITS:,} characters or fewer.", body)
        self.assertIn('aria-describedby="os-source-help os-source-error"', body)
        self.assertIn('aria-invalid="true"', body)

    def test_empty_input_is_refused_by_name(self):
        with self.signed_in(), self.service() as service:
            response = self.client.post(
                "/opportunity-slate/source",
                data={"source_text": "   ", "idempotency_key": "fixture-key-4"},
                headers=SAME_ORIGIN_HEADERS,
            )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Add the role text before continuing.", response.data.decode("utf-8"))
        service.save_source_for_owner.assert_not_called()

    def test_an_optimistic_concurrency_conflict_keeps_the_member_wording(self):
        with self.signed_in(), self.service() as service:
            service.correct_source_for_owner.side_effect = OpportunitySlateServiceError(
                "changed", code="changed"
            )
            service.get_working_session_for_owner.return_value = working_view()
            response = self.client.post(
                "/opportunity-slate/source/corrections",
                data={
                    "source_key": SOURCE_KEY,
                    "version_token": SOURCE_TOKEN,
                    "corrected_text": "My careful correction.",
                },
                headers=SAME_ORIGIN_HEADERS,
            )
        body = response.data.decode("utf-8")
        self.assertEqual(response.status_code, 409)
        self.assertIn("This role source changed.", body)
        self.assertIn("My careful correction.", body)

    def test_a_failed_delete_leaves_the_source_visibly_intact(self):
        with self.signed_in(), self.service() as service:
            service.delete_working_session_for_owner.side_effect = DatabaseServiceError(
                "delete failed"
            )
            service.get_working_session_for_owner.return_value = working_view()
            response = self.client.post(
                "/opportunity-slate/source/delete",
                data={
                    "session_key": SESSION_KEY,
                    "session_version_token": SESSION_TOKEN,
                },
                headers=SAME_ORIGIN_HEADERS,
            )
        body = response.data.decode("utf-8")
        self.assertEqual(response.status_code, 503)
        self.assertIn("Nothing was removed.", body)
        self.assertIn("We design and sustain complex systems.", body)


class TruthLabelingTests(OpportunitySlateTestCase):
    def test_no_subheader_assistant_affordance_ships(self):
        """Owner decision, handoff section 17-Q1 / register M7: the generated
        set's "Ask Slate AI" chrome is image artifact."""
        with self.anonymous():
            public_body = self.client.get(ROOM_GET).data.decode("utf-8")
        with self.signed_in(), self.service() as service:
            service.get_working_session_for_owner.return_value = working_view()
            member_body = self.client.get(ROOM_GET).data.decode("utf-8")
        for body in (public_body, member_body):
            self.assertNotIn("Ask Slate AI", body)

    def test_no_aggregate_score_or_verdict_language_anywhere(self):
        with self.signed_in(), self.service() as service:
            service.get_working_session_for_owner.return_value = working_view()
            body = self.client.get(ROOM_GET).data.decode("utf-8")
        for banned in ("Match score", "match score", "% match", "Overall score", "Recommended"):
            self.assertNotIn(banned, body)

    def test_the_public_session_never_claims_persistence(self):
        with self.anonymous():
            body = self.client.get(ROOM_GET).data.decode("utf-8")
        self.assertIn("Nothing is stored on PeerSlate", body)
        self.assertNotIn("Save privately", body)
        self.assertNotIn("Saved privately", body)

    def test_the_member_session_never_claims_a_save(self):
        with self.signed_in(), self.service() as service:
            service.get_working_session_for_owner.return_value = working_view()
            body = self.client.get(ROOM_GET).data.decode("utf-8")
        self.assertIn("Nothing is saved yet", body)
        self.assertIn(
            "Confirming the source does not save the slate or produce qualification",
            body,
        )
        self.assertNotIn("Save privately", body)


class RateLimitRegistrationTests(unittest.TestCase):
    def test_every_state_changing_route_is_rate_limited(self):
        source = (
            __import__("pathlib").Path(__file__).resolve().parents[1] / "app.py"
        ).read_text(encoding="utf-8")
        for endpoint in (
            "opportunity_slate.set_source",
            "opportunity_slate.correct_source",
            "opportunity_slate.confirm_source",
            "opportunity_slate.delete_source",
            "opportunity_slate.public_session",
        ):
            self.assertIn(f"'{endpoint}'", source)

    def test_the_blueprint_is_in_the_private_cache_set(self):
        source = (
            __import__("pathlib").Path(__file__).resolve().parents[1] / "app.py"
        ).read_text(encoding="utf-8")
        self.assertIn("'opportunity_slate',", source)

    def test_the_flag_is_documented_and_defaults_off(self):
        root = __import__("pathlib").Path(__file__).resolve().parents[1]
        env_example = (root / ".env.example").read_text(encoding="utf-8")
        app_source = (root / "app.py").read_text(encoding="utf-8")
        self.assertIn("PEERSLATE_OPPORTUNITY_SLATE_ENABLED=false", env_example)
        self.assertIn(
            "os.environ.get('PEERSLATE_OPPORTUNITY_SLATE_ENABLED', 'false')",
            app_source,
        )

    def test_the_spend_guard_is_plumbed_and_honestly_labelled_as_unused(self):
        """Handoff section 18 safeguard 3. Slice OS-1 has no AI endpoint, so
        the ceiling is config-only — and must say so, rather than reading as
        a live control."""
        root = __import__("pathlib").Path(__file__).resolve().parents[1]
        app_source = (root / "app.py").read_text(encoding="utf-8")
        env_example = (root / ".env.example").read_text(encoding="utf-8")
        self.assertIn("PEERSLATE_OPPSLATE_DAILY_AI_CEILING", app_source)
        self.assertIn("CONFIG ONLY IN SLICE", app_source)
        self.assertIn("PEERSLATE_OPPSLATE_DAILY_AI_CEILING=0", env_example)
        self.assertIn("CONFIG ONLY TODAY", env_example)


class NoAiCallTests(unittest.TestCase):
    def test_the_slice_imports_no_ai_client(self):
        """Slice OS-1 makes no AI call. Asserted as a literal absence across
        the route and service modules so it cannot drift in unnoticed."""
        root = __import__("pathlib").Path(__file__).resolve().parents[1]
        for relative in (
            "opportunity_slate_routes.py",
            "services/opportunity_slate_service.py",
        ):
            source = (root / relative).read_text(encoding="utf-8")
            with self.subTest(module=relative):
                self.assertNotIn("import anthropic", source)
                self.assertNotIn("messages.create", source)
                self.assertNotIn("ANTHROPIC_API_KEY", source)

    def test_no_secret_names_reach_the_room_script(self):
        root = __import__("pathlib").Path(__file__).resolve().parents[1]
        script = (root / "static" / "js" / "opportunity-slate.js").read_text(
            encoding="utf-8"
        )
        for secret in (
            "ANTHROPIC_API_KEY",
            "AZURE_CLIENT_SECRET",
            "CONNECTION_STRING",
            "PUBLISH_PROFILE",
            "SECRET_KEY",
        ):
            self.assertNotIn(secret, script)


class ServiceDisciplineTests(unittest.TestCase):
    """The service layer's own contract, exercised directly against a mocked
    database so the row discipline, bounds, and outcome handling are held in
    place independently of the routes."""

    def setUp(self):
        from services.opportunity_slate_service import OpportunitySlateService

        self.database = MagicMock()
        self.service = OpportunitySlateService(database=self.database)

    def get_row(self, **overrides):
        row = {
            "working_session_key": SESSION_KEY,
            "workbench_state": "review_source",
            "expires_at_utc": datetime.now(timezone.utc) + timedelta(hours=48),
            "session_row_version": bytes.fromhex(SESSION_TOKEN),
            "source_key": SOURCE_KEY,
            "current_version_number": 1,
            "confirmed_version_number": None,
            "confirmed_at_utc": None,
            "source_row_version": bytes.fromhex(SOURCE_TOKEN),
            "capture_method": "pasted",
            "original_text": ROLE_TEXT,
            "member_corrected_text": None,
            "corrected_at_utc": None,
            "captured_at_utc": datetime.now(timezone.utc),
        }
        row.update(overrides)
        return row

    def test_the_input_cap_is_one_function_shared_by_both_modes(self):
        from services.opportunity_slate_service import validate_source_text

        with self.assertRaises(OpportunitySlateServiceError) as empty:
            validate_source_text("   ")
        self.assertEqual(empty.exception.code, "required")

        with self.assertRaises(OpportunitySlateServiceError) as long:
            validate_source_text("x" * (MAX_SOURCE_TEXT_UNITS + 1))
        self.assertEqual(long.exception.code, "too_long")

        # Exactly at the bound is accepted; interior blank lines survive,
        # because this is the employer's text and not ours to reflow.
        self.assertEqual(len(validate_source_text("x" * MAX_SOURCE_TEXT_UNITS)), MAX_SOURCE_TEXT_UNITS)
        self.assertEqual(validate_source_text("  a\n\nb  "), "a\n\nb")

    def test_the_cap_counts_utf16_code_units_like_sql_server(self):
        from services.opportunity_slate_service import validate_source_text

        # An astral character is two UTF-16 code units, which is what the
        # migration's DATALENGTH/2 CHECK counts. Python's len() would
        # undercount it as one and let an over-length value through.
        astral = "\U0001f600" * (MAX_SOURCE_TEXT_UNITS // 2 + 1)
        with self.assertRaises(OpportunitySlateServiceError) as error:
            validate_source_text(astral)
        self.assertEqual(error.exception.code, "too_long")

    def test_a_read_row_of_the_wrong_shape_is_rejected(self):
        row = self.get_row()
        row["unexpected_column"] = "surprise"
        self.database.first_row.return_value = row
        with self.assertRaises(OpportunitySlateServiceError) as error:
            self.service.get_working_session_for_owner("member-oppslate-1")
        self.assertEqual(error.exception.code, "invalid")

        missing = self.get_row()
        del missing["original_text"]
        self.database.first_row.return_value = missing
        with self.assertRaises(OpportunitySlateServiceError):
            self.service.get_working_session_for_owner("member-oppslate-1")

    def test_an_expired_row_is_inaccessible_even_if_the_read_returned_it(self):
        """Expiry is enforced twice — in the procedure and again here — so a
        clock skew or a future procedure edit cannot resurrect a session."""
        self.database.first_row.return_value = self.get_row(
            expires_at_utc=datetime.now(timezone.utc) - timedelta(minutes=1)
        )
        self.assertIsNone(
            self.service.get_working_session_for_owner("member-oppslate-1")
        )

    def test_no_working_session_reads_as_none_not_an_error(self):
        self.database.first_row.return_value = None
        self.assertIsNone(
            self.service.get_working_session_for_owner("member-oppslate-1")
        )

    def test_display_text_prefers_the_correction_and_keeps_the_original(self):
        self.database.first_row.return_value = self.get_row(
            member_corrected_text="Corrected wording.",
            corrected_at_utc=datetime.now(timezone.utc),
        )
        view = self.service.get_working_session_for_owner("member-oppslate-1")
        self.assertEqual(view.display_text, "Corrected wording.")
        self.assertEqual(view.original_text, ROLE_TEXT)
        self.assertTrue(view.has_correction)
        self.assertFalse(view.is_confirmed)

    def test_save_refuses_a_capture_method_this_slice_cannot_honestly_record(self):
        for method in ("dictated", "uploaded", "imported", "typed", None):
            with self.subTest(method=method):
                with self.assertRaises(OpportunitySlateServiceError) as error:
                    self.service.save_source_for_owner(
                        "member-oppslate-1", "key", ROLE_TEXT, capture_method=method
                    )
                self.assertEqual(error.exception.code, "invalid")
        self.database.first_row.assert_not_called()

    def test_save_requires_a_bounded_idempotency_key(self):
        for key, code in ((None, "required"), ("  ", "required"), ("k" * 201, "too_long")):
            with self.subTest(key=key):
                with self.assertRaises(OpportunitySlateServiceError) as error:
                    self.service.save_source_for_owner("member-oppslate-1", key, ROLE_TEXT)
                self.assertEqual(error.exception.code, code)

    def test_save_never_reports_success_without_an_exact_key(self):
        self.database.first_row.return_value = {
            "outcome": "success",
            "working_session_key": SESSION_KEY,
            "source_key": None,
            "version_number": 1,
            "workbench_state": "review_source",
            "session_row_version": bytes.fromhex(SESSION_TOKEN),
            "source_row_version": bytes.fromhex(SOURCE_TOKEN),
        }
        with self.assertRaises(OpportunitySlateServiceError) as error:
            self.service.save_source_for_owner("member-oppslate-1", "key", ROLE_TEXT)
        self.assertEqual(error.exception.code, "not_found")

    def test_save_accepts_the_three_honest_outcomes(self):
        for outcome in ("success", "existing", "unchanged"):
            with self.subTest(outcome=outcome):
                self.database.first_row.return_value = {
                    "outcome": outcome,
                    "working_session_key": SESSION_KEY,
                    "source_key": SOURCE_KEY,
                    "version_number": 1,
                    "workbench_state": "review_source",
                    "session_row_version": bytes.fromhex(SESSION_TOKEN),
                    "source_row_version": bytes.fromhex(SOURCE_TOKEN),
                }
                result = self.service.save_source_for_owner(
                    "member-oppslate-1", "key", ROLE_TEXT
                )
                self.assertEqual(result["outcome"], outcome)
                self.assertEqual(result["source_key"], SOURCE_KEY)

    def test_a_changed_outcome_is_raised_never_reported_as_success(self):
        self.database.first_row.return_value = {
            "outcome": "changed",
            "source_row_version": None,
            "version_number": None,
        }
        with self.assertRaises(OpportunitySlateServiceError) as error:
            self.service.correct_source_for_owner(
                "member-oppslate-1", SOURCE_KEY, SOURCE_TOKEN, "Corrected."
            )
        self.assertEqual(error.exception.code, "changed")

    def test_an_unrecognized_outcome_fails_closed(self):
        self.database.first_row.return_value = {
            "outcome": "probably_fine",
            "source_row_version": None,
            "confirmed_version_number": None,
        }
        with self.assertRaises(OpportunitySlateServiceError) as error:
            self.service.confirm_source_for_owner(
                "member-oppslate-1", SOURCE_KEY, SOURCE_TOKEN
            )
        self.assertEqual(error.exception.code, "not_found")

    def test_a_malformed_version_token_reads_as_changed_not_as_a_hint(self):
        """A caller is told the record changed, never that their token was
        malformed in a way that would help them craft a better one."""
        for token in (None, "", "zz", "0" * 15, 12345):
            with self.subTest(token=token):
                with self.assertRaises(OpportunitySlateServiceError) as error:
                    self.service.confirm_source_for_owner(
                        "member-oppslate-1", SOURCE_KEY, token
                    )
                self.assertEqual(error.exception.code, "changed")
        self.database.first_row.assert_not_called()

    def test_a_malformed_source_key_never_reaches_a_procedure(self):
        with self.assertRaises(OpportunitySlateServiceError) as error:
            self.service.correct_source_for_owner(
                "member-oppslate-1", "not-a-uuid", SOURCE_TOKEN, "Corrected."
            )
        self.assertEqual(error.exception.code, "invalid")
        self.database.first_row.assert_not_called()

    def test_the_purge_tolerates_an_owner_with_nothing_to_purge(self):
        self.database.first_row.return_value = None
        self.assertEqual(
            self.service.purge_expired_working_data_for_owner("member-oppslate-1"),
            {"purged_sessions": 0, "purged_versions": 0},
        )

    def test_every_procedure_call_passes_the_server_derived_user_key(self):
        """No method accepts, derives, or trusts an owner id from a caller —
        the only owner input is the server-resolved user key."""
        self.database.first_row.return_value = {
            "outcome": "success",
            "source_row_version": bytes.fromhex(SOURCE_TOKEN),
            "confirmed_version_number": 1,
        }
        self.service.confirm_source_for_owner(
            "member-oppslate-1", SOURCE_KEY, SOURCE_TOKEN
        )
        parameters = dict(self.database.first_row.call_args[0][1])
        self.assertEqual(parameters["@UserKey"], "member-oppslate-1")
        self.assertNotIn("@OwnerProfileId", parameters)
        self.assertNotIn("@ProfileId", parameters)


if __name__ == "__main__":
    unittest.main()
