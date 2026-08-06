"""Contract tests for Opportunity Slate — PS-OPPSLATE-001, slices OS-1
through OS-4.

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

import os
import re
import shutil
import subprocess
import unittest
from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import opportunity_slate_routes as routes
from app import app, limiter
from services.database_service import DatabaseServiceError
from services.opportunity_slate_service import (
    MAX_SOURCE_TEXT_UNITS,
    AnalysisCitationView,
    AnalysisStatementView,
    AnalysisView,
    EvidenceItemView,
    OpportunitySlateService,
    OpportunitySlateServiceError,
    RequirementSetView,
    RequirementStatementView,
    SavedEvidenceView,
    SavedQualificationView,
    SavedSlateView,
    SavedVersionView,
    WorkingSourceView,
    compute_content_digest,
    compute_input_fingerprint,
)


SESSION_KEY = "11111111-1111-1111-1111-111111111111"
SOURCE_KEY = "22222222-2222-2222-2222-222222222222"
SESSION_TOKEN = "0000000000000001"
SOURCE_TOKEN = "0000000000000002"
SAME_ORIGIN_HEADERS = {"Origin": "http://localhost", "Sec-Fetch-Site": "same-origin"}


def requirement_set(**overrides):
    """The smallest proposed requirement set that renders Review Requirements."""
    statement = RequirementStatementView(
        statement_key="44444444-4444-4444-4444-444444444444",
        ordinal=1,
        span_start=0,
        span_length=52,
        employer_text="Strong understanding of systems engineering processes.",
        proposed_class="required_qualification",
        proposed_explanation="Asks for systems engineering knowledge.",
        proposed_paths=({"label": "Path A", "clauses": ("Systems engineering",)},),
        member_class=None,
        member_clarification=None,
        member_updated_at=None,
        version_token="0000000000000004",
    )
    fields = {
        "requirement_set_key": "55555555-5555-5555-5555-555555555555",
        "version_token": "0000000000000003",
        "version_number": 1,
        "source_version_number": 1,
        "model_name": "claude-sonnet-5",
        "prompt_contract_version": "os-statements-v1",
        "proposed_at": datetime.now(timezone.utc),
        "confirmed_version_number": None,
        "confirmed_at": None,
        "statements": (statement,),
    }
    fields.update(overrides)
    return RequirementSetView(**fields)

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
    # Slice OS-2.
    "/opportunity-slate/source/review",
    "/opportunity-slate/source/concerns",
    "/opportunity-slate/requirements",
    "/opportunity-slate/requirements/corrections",
    "/opportunity-slate/requirements/confirm",
    # Slice OS-6.
    "/opportunity-slate/source/upload",
    "/opportunity-slate/source/import",
)
PUBLIC_POST = "/opportunity-slate/public-session"
PUBLIC_PROPOSE_POST = "/opportunity-slate/public-session/propose"


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

    @contextmanager
    def service(self):
        """The patched service module, with the three lookups whose absence
        is a real, meaningful state defaulted to "nothing has run yet".

        An unconfigured MagicMock attribute is TRUTHY, so without these
        defaults every test that does not mention AI would render the room as
        though a wording review and a requirement proposal already existed —
        and a screen whose whole job is to distinguish "not checked" from
        "checked, nothing found" would be asserted in the wrong state without
        anything failing. None is also what the real service returns before
        either step has run, so this is the honest default rather than a
        convenience.

        get_saved_slate_for_owner joined this list with slice OS-4: a test
        that does not mention saving must not silently exercise "this member
        has a saved slate" just because a MagicMock is truthy by default —
        `alignment_service()` below already set this explicitly per-call, but
        a route reached through the bare `service()` fixture (finding F-4's
        intake path among them) had no such guard.
        """
        with patch("opportunity_slate_routes.opportunity_slate_service") as service:
            service.get_source_review_for_owner.return_value = None
            service.get_requirements_for_owner.return_value = None
            service.get_saved_slate_for_owner.return_value = None
            yield service


class FlagGateTests(OpportunitySlateTestCase):
    def test_flag_off_returns_404_on_every_route(self):
        app.config["PEERSLATE_OPPORTUNITY_SLATE_ENABLED"] = False
        self.assertEqual(self.client.get(ROOM_GET).status_code, 404)
        for path in MEMBER_POSTS + (PUBLIC_POST, PUBLIC_PROPOSE_POST):
            with self.subTest(path=path):
                response = self.client.post(path, headers=SAME_ORIGIN_HEADERS)
                self.assertEqual(response.status_code, 404)

    def test_flag_check_runs_before_any_identity_resolution(self):
        """Flag-off must be indistinguishable from not-found, which means it
        cannot depend on resolving who is asking first."""
        app.config["PEERSLATE_OPPORTUNITY_SLATE_ENABLED"] = False
        with patch("opportunity_slate_routes.get_optional_identity") as resolve:
            self.client.get(ROOM_GET)
            for path in MEMBER_POSTS + (PUBLIC_POST, PUBLIC_PROPOSE_POST):
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

    def test_the_room_stays_out_of_the_sitemap_though_it_is_now_in_navigation(self):
        """PS-OPPORTUNITY-SLATE-001 leg 7 (Pete's 2026-08-05 order) reverses
        the earlier unlisted-by-direct-link-only posture for site-internal
        discoverability: the room now has a main-navigation link next to
        Workshop's. Search-engine indexing is unaffected — the route keeps
        its own noindex/nofollow headers (HeaderPostureTests above) and
        stays out of the sitemap; see tests/test_navigation.py for the
        navigation-link coverage this leg added."""
        sitemap = self.client.get("/sitemap.xml").data.decode("utf-8")
        self.assertNotIn("opportunity-slate", sitemap)
        home = self.client.get("/").data.decode("utf-8")
        self.assertIn("/opportunity-slate", home)

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

        Slice OS-2 independent review, finding F1: the corrected sentences then
        over-corrected in the other direction and asserted a THIRD PARTY's
        retention policy — "Never stored on either", "It is not stored there",
        "the only copy kept". PeerSlate can promise what PeerSlate does. It
        cannot promise what its AI provider retains: provider inputs are
        retained by default and zero-retention is contractual, and nothing in
        this repository establishes such an arrangement. Every retention
        promise on this surface is now scoped to PeerSlate by name, the transit
        is described without characterising the provider, and each retired
        over-claim is rejected by substring below.
        """
        with self.anonymous():
            body = self.client.get(ROOM_GET).data.decode("utf-8")
        text = " ".join(body.split())

        self.assertIn(
            "Your text is sent to PeerSlate to draw this screen, and on to its "
            "AI provider when you ask for a reading. PeerSlate stores none of it.",
            text,
        )
        self.assertIn("The copy you keep is in this browser tab.", text)
        self.assertIn(
            "Sent to PeerSlate, and on to PeerSlate's AI provider when you ask "
            "for a reading. PeerSlate stores none of it. The copy you keep is in "
            "this browser tab.",
            text,
        )
        # Slice OS-2 truth correction. "nothing is analyzed" was true in
        # slice OS-1 and is false now, so the clause is gone and the AI
        # transit is named in its place. The promise that still holds —
        # nothing stored ON PEERSLATE, nothing sent to an employer — is
        # unchanged and is asserted here so a future edit cannot quietly drop
        # it either.
        self.assertIn(
            "This preview sends your role text to PeerSlate to draw each screen, "
            "and on to PeerSlate's AI provider when you ask it to read the "
            "wording.",
            text,
        )
        self.assertIn(
            "Your own browser holds the copy you keep, for this visit only.",
            text,
        )
        self.assertIn(
            "Nothing is stored on PeerSlate, and nothing is shared or sent to an "
            "employer.",
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
            # The slice OS-1 clause this slice had to retire. An anonymous
            # visitor who presses "Check the wording" IS having their text
            # analyzed, so this sentence may never come back while that is
            # true.
            "nothing is analyzed",
            # Finding F1: the four retired third-party retention claims. Each
            # one asserted, in a member-visible sentence, what PeerSlate's AI
            # provider does with the employer's role text. None of them may
            # come back in any state of this room.
            "Never stored on either",
            "never stored on either",
            "The only copy kept is",
            "the only copy kept is",
            "It is not stored there",
            "not stored there",
        ):
            self.assertNotIn(false_claim, text)

    def test_no_surface_in_the_room_asserts_the_ai_providers_retention(self):
        """Slice OS-2 independent review, finding F1, held at the source.

        The test above can only see the states a plain room GET renders. Two
        of the four sentences F1 found live on screens that need a confirmed
        source and a completed AI step to reach, so a substring check on one
        response body would have missed them — and would miss the next one
        somebody writes on a state no test drives.

        This reads every file the room is built from instead. The rule it
        enforces is narrow and absolute: PeerSlate may describe sending the
        employer's role text ONWARD to its AI provider, and may promise what
        PeerSlate itself stores. It may not state, imply, or summarise what
        the provider retains. Provider inputs are retained by default; zero
        retention is a contractual arrangement, and nothing in this
        repository establishes one.

        If a future slice genuinely obtains a zero-retention agreement, the
        place to record it is the package, with the contract named — not a
        sentence in a template that no evidence supports.
        """
        root = Path(app.root_path)
        surfaces = sorted(
            (root / "templates" / "partials" / "opportunity_slate").glob("*.html")
        )
        surfaces += [
            root / "static" / "js" / "opportunity-slate.js",
            root / "opportunity_slate_routes.py",
        ]
        self.assertGreaterEqual(len(surfaces), 8, "the room's surfaces moved")

        # Each entry: the retired claim, and why it is not PeerSlate's to make.
        retired = {
            "Never stored on either": "asserts the provider stores nothing",
            "never stored on either": "asserts the provider stores nothing",
            "not stored there": "asserts the provider stores nothing",
            "The only copy kept": "asserts no provider-side copy exists",
            "the only copy kept": "asserts no provider-side copy exists",
            "the only retained copy": "asserts no provider-side copy exists",
            "nothing is retained anywhere": "asserts provider-side retention",
            "deleted by the provider": "asserts provider-side deletion",
            "the AI does not keep": "asserts provider-side retention",
            "the AI never keeps": "asserts provider-side retention",
        }
        for path in surfaces:
            body = path.read_text(encoding="utf-8")
            for claim, why in retired.items():
                self.assertNotIn(
                    claim,
                    body,
                    f"{path.name} {why}: {claim!r}",
                )

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

    def test_the_anonymous_supported_sources_rail_keeps_its_true_sentence(self):
        """Closing review, 2026-08-05 (B1). The "Supported sources" rail's
        anonymous sentence — upload and import are not on this screen, and
        will be for signed-in members only — was true before slice OS-6 and
        stays true after it: handoff section 18 safeguard 1 keeps uploads and
        imports off the public route permanently, not just "for now". This
        locks the untouched anonymous variant so the signed-in fix below
        cannot drift onto this branch."""
        with self.anonymous():
            body = self.client.get(ROOM_GET).data.decode("utf-8")
        text = " ".join(body.split())
        self.assertIn(
            "Document upload and public-link import are not available on "
            "this screen yet, and will be for signed-in members only.",
            text,
        )

    def test_the_role_intake_microphone_is_wired_live(self):
        """Slice OS-5: the intake mic is no longer honestly-inert placeholder
        markup (handoff section 14-M18) — it is a real, live control wired to
        the shared dictation module, and it renders identically for the
        anonymous session as for a signed-in member (handoff section 18:
        "same screens, same flow"; dictation is client-side speech-to-text
        into the textarea, so it never touches the paste-only server
        boundary and there is no reason for the two modes to differ here)."""
        with self.anonymous():
            body = self.client.get(ROOM_GET).data.decode("utf-8")
        self.assertIn('data-os-mic="role"', body)
        self.assertIn('aria-pressed="false"', body)
        self.assertIn('aria-label="Dictate the role"', body)
        self.assertNotIn("data-os-inert-mic", body)
        self.assertNotIn("Dictation arrives in a later update", body)
        self.assertNotIn("Dictation is not available yet", body)

        with self.signed_in(), self.service() as service:
            service.get_working_session_for_owner.return_value = None
            signed_in_body = self.client.get(ROOM_GET).data.decode("utf-8")
        self.assertIn('data-os-mic="role"', signed_in_body)
        self.assertIn('aria-pressed="false"', signed_in_body)
        self.assertNotIn("data-os-inert-mic", signed_in_body)

    def test_the_microphone_privacy_sentence_covers_every_mic_equipped_field(self):
        """Mirrors tests/test_interview_studio.py's
        test_the_public_route_claims_no_server_capture_or_account_history,
        which asserts this exact sentence against Interview Studio's own
        rendered page. Held here as a template-source count across the four
        partials that carry a mic, normalizing whitespace first because the
        sentence wraps across source lines in some of them — a raw assertIn
        against unrendered template text would otherwise pass or fail on
        incidental line-wrapping rather than on whether the sentence is
        actually there. Six because there are six mic-equipped fields
        (handoff section 4): role intake; the per-concern correction card
        AND the whole-document correction editor; requirement
        clarification; and the response rail's Tell-us-more and
        Provide-a-real-example fields."""
        partials_dir = (
            Path(__file__).resolve().parents[1]
            / "templates"
            / "partials"
            / "opportunity_slate"
        )
        sentence = "PeerSlate does not receive or keep the audio."
        total = 0
        for name in (
            "_intake.html",
            "_review.html",
            "_statement_rail.html",
            "_response_rail.html",
        ):
            normalized = " ".join(
                (partials_dir / name).read_text(encoding="utf-8").split()
            )
            count = normalized.count(sentence)
            with self.subTest(file=name):
                self.assertGreater(count, 0, name + " never states it")
            total += count
        self.assertEqual(total, 6)

    def test_dictation_js_loads_before_the_room_script_that_binds_it(self):
        """opportunity-slate.js reads window.PeerSlateDictation at bind time;
        both tags are deferred, so only document order — not a race —
        decides which runs first. Same requirement Interview Studio already
        holds for its own two tags."""
        with self.anonymous():
            body = self.client.get(ROOM_GET).data.decode("utf-8")
        dictation_at = body.index("js/dictation.js")
        room_script_at = body.index("js/opportunity-slate.js")
        self.assertLess(dictation_at, room_script_at)

    def test_the_room_script_wires_a_mic_for_every_dictation_surface(self):
        """The room script's own binding code, not just the template markup:
        every data-os-mic button gets registered with the shared module, and
        an unsupported browser gets a real inert state rather than a dead
        live-looking button (handoff section 6 rule 5)."""
        script = (
            Path(__file__).resolve().parents[1]
            / "static"
            / "js"
            / "opportunity-slate.js"
        ).read_text(encoding="utf-8")
        self.assertIn("window.PeerSlateDictation", script)
        self.assertIn("dictationModule.createController(", script)
        self.assertIn("node.querySelectorAll('[data-os-mic]')", script)
        self.assertIn("dictation.register(key,", script)
        self.assertIn("if (!dictationModule || !dictationModule.isSupported())", script)
        self.assertIn("disableUnsupportedMics(buttons)", script)
        self.assertIn(
            "'Speech input is not supported in this browser. Typing works normally.'",
            script,
        )

    def test_every_mic_is_bound_before_the_unsupported_check_runs(self):
        """Interview Studio's own order for its mics (bind, THEN disable if
        unsupported), not the reverse. Binding first means a button that a
        later bug — or a future lockRail-shaped one — re-enables still has
        a real click listener, so a press reaches the shared module's own
        SpeechRecognition check and reports an honest error, rather than a
        button that looks live and silently does nothing because it was
        never registered with the module in the first place."""
        script = (
            Path(__file__).resolve().parents[1]
            / "static"
            / "js"
            / "opportunity-slate.js"
        ).read_text(encoding="utf-8")
        init_dictation = script.split("function initDictation(node)", 1)[1].split(
            "\n    }\n", 1
        )[0]
        bind_at = init_dictation.index("bindMic(buttons[index]);")
        disable_check_at = init_dictation.index(
            "if (!dictationModule || !dictationModule.isSupported())"
        )
        self.assertLess(bind_at, disable_check_at)

    def test_the_submit_flush_precedes_reading_which_form_was_submitted(self):
        """Positional guard for the priority fix: the submit handler's flush
        has to be the FIRST thing it does, ahead of even
        `kind = form.getAttribute('data-os-form')` — the read every later
        branch's own field-value reads are gated behind. A flush placed
        after that line, or inside one specific branch, would still pass
        every OTHER dictation test (they only check a flush exists
        somewhere), which is exactly why this needs its own positional
        assertion rather than relying on assertIn elsewhere. Same shape as
        test_every_mic_is_bound_before_the_unsupported_check_runs above."""
        script = (
            Path(__file__).resolve().parents[1]
            / "static"
            / "js"
            / "opportunity-slate.js"
        ).read_text(encoding="utf-8")
        submit_listener = script.split(
            "document.addEventListener('submit', function (event) {", 1
        )[1].split("document.addEventListener('click', function (event) {", 1)[0]
        flush_at = submit_listener.index("stopActiveDictation(")
        kind_at = submit_listener.index("form.getAttribute('data-os-form')")
        self.assertLess(flush_at, kind_at)

    def test_switching_panels_or_swapping_the_room_flushes_active_dictation(self):
        """A statement or qualification panel is switched by toggling
        `hidden` on the client — no round trip — so a mic left listening in
        the panel a member just left would otherwise keep listening
        invisibly behind it. Held at every point that changes what is on
        screen: statement selection, alignment-row selection, EVERY rail
        request that locks (send() and beginProposal each lock their own
        rail independently — a single-occurrence .index() lookup would only
        ever see the first and silently stop covering the second the moment
        a call site like beginProposal's own lockRail(node, true) was
        added, which is exactly what happened here), and a full room swap.
        Same stale-context case Interview Studio already flushes before its
        own state changes."""
        script = (
            Path(__file__).resolve().parents[1]
            / "static"
            / "js"
            / "opportunity-slate.js"
        ).read_text(encoding="utf-8")
        self.assertGreaterEqual(script.count("stopActiveDictation("), 5)
        for site in (
            "selectStatement(node, select.getAttribute('data-os-select-statement'));",
            "selectAlignment(node, selectAlign.getAttribute('data-os-select-align'));",
            "node.outerHTML = html;",
        ):
            with self.subTest(site=site[:40]):
                marker = script.index(site)
                preceding = script[max(0, marker - 400) : marker]
                self.assertIn("stopActiveDictation(", preceding)

        # Every lockRail(node, true) call site, not just the first one a
        # plain .index() would find — send() and beginProposal each lock
        # independently and must each flush independently.
        lock_sites = list(re.finditer(r"lockRail\(node, true\);", script))
        self.assertGreaterEqual(len(lock_sites), 2)
        for match in lock_sites:
            with self.subTest(offset=match.start()):
                preceding = script[max(0, match.start() - 400) : match.start()]
                self.assertIn("stopActiveDictation(", preceding)

    def test_no_mic_click_handler_ever_submits_anything(self):
        """Handoff section 6 rule 3: voice never automatically submits,
        confirms, analyzes, saves, publishes, or navigates. The shared
        dictation.js module already asserts this for itself
        (tests/test_interview_studio.py's
        test_dictation_never_submits_confirms_or_navigates); this holds it
        for the room script's OWN mic-wiring code, which is new in OS-5 and
        is not covered by that test."""
        script = (
            Path(__file__).resolve().parents[1]
            / "static"
            / "js"
            / "opportunity-slate.js"
        ).read_text(encoding="utf-8")
        binding = script.split("function bindMic(button)", 1)[1].split(
            "function disableUnsupportedMics", 1
        )[0]
        for forbidden in (
            ".submit(",
            ".requestSubmit(",
            ".click()",
            "location.href",
            "location.assign",
        ):
            with self.subTest(call=forbidden):
                self.assertNotIn(forbidden, binding)

    def test_every_wired_mic_button_is_type_button_not_submit(self):
        """A mic that were ever type="submit" could fire a form post on
        Enter/Space from a focused button — belt-and-suspenders alongside
        the JS-level check above, held directly against the six button
        instances across the four documented surfaces (handoff section 16's
        OS-5 row; section 6's "everywhere a mic appears")."""
        partials_dir = (
            Path(__file__).resolve().parents[1]
            / "templates"
            / "partials"
            / "opportunity_slate"
        )
        for name in (
            "_intake.html",
            "_review.html",
            "_statement_rail.html",
            "_response_rail.html",
        ):
            text = (partials_dir / name).read_text(encoding="utf-8")
            mic_count = text.count("data-os-mic=")
            self.assertGreater(mic_count, 0, name + " has no wired mic")
            # Every button carrying data-os-mic is declared type="button" on
            # the same tag — a submit type is never used for a mic anywhere.
            for match in re.finditer(
                r"<button[^>]*data-os-mic=[^>]*>", text, re.S
            ):
                with self.subTest(file=name, tag=match.group(0)[:60]):
                    self.assertIn('type="button"', match.group(0))
                    self.assertNotIn('type="submit"', match.group(0))

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
        # Slice OS-2: confirming the source lands on checkpoint 2, which
        # offers to read the employer's statements and has not read them yet.
        self.assertEqual(confirmed["step"], "requirements")
        self.assertIn("Checkpoint 2 of 2", confirmed["html"])
        self.assertIn("Read the statements", confirmed["html"])

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
        # No saved slate in this fixture (the service() default) — no link
        # to one. See test_an_orphaned_saved_slate_gets_a_link_on_intake for
        # the case where one exists.
        self.assertNotIn("View saved details", body)

    def test_an_orphaned_saved_slate_gets_a_link_on_intake(self):
        """2026-08-05 independent review, finding F-4. A saved slate outlives
        the working session it was computed from — that survival is the
        whole design point of slice OS-4 (`usp_DeleteOpportunitySavedSlateForOwner`
        touches no working data, and `usp_DeleteOpportunityWorkingSessionForOwner`
        touches no saved data). A member whose working session was deleted or
        expired, but who still has a saved slate, used to land on a bare
        intake screen with no route to it anywhere on the page — the saved
        result was real and reachable only by typing the URL by hand."""
        with self.signed_in(), self.service() as service:
            service.get_working_session_for_owner.return_value = None
            service.get_saved_slate_for_owner.return_value = saved_slate()
            body = self.client.get(ROOM_GET).data.decode("utf-8")
        self.assertIn("Bring a role", body)
        self.assertIn("View saved details", body)
        self.assertIn("/opportunity-slate/saved", body)

    def test_a_saved_slate_read_failure_still_renders_the_bare_intake(self):
        """`_load_saved_slate` under-claims on a read failure (it returns
        None rather than raising) precisely so a broken read never denies the
        member their room — the same rule the working-session purge above it
        follows. A member with a genuinely unreadable saved-slate lookup sees
        the same honest intake screen as one with no saved slate at all,
        never a 503 and never a stale link."""
        with self.signed_in(), self.service() as service:
            service.get_working_session_for_owner.return_value = None
            service.get_saved_slate_for_owner.side_effect = DatabaseServiceError(
                "down"
            )
            response = self.client.get(ROOM_GET)
        self.assertEqual(response.status_code, 200)
        body = response.data.decode("utf-8")
        self.assertIn("Bring a role", body)
        self.assertNotIn("View saved details", body)

    def test_the_signed_in_supported_sources_rail_tells_the_truth(self):
        """Closing review, 2026-08-05 (B1): the final reviewer found a live
        member-facing falsehood. The "Supported sources" rail told a
        signed-in member that document upload and public-link import "are
        not available on this screen yet" — on the same intake render where
        slice OS-6's live upload and import disclosures (the "Upload
        document" / "Import public link" tiles) already sit in view.

        The corrected sentence is asserted here for the role/replace screen,
        where the tiles are literally on screen, and separately for the
        review screen (working_view()'s default state), which shares this
        same rail note but carries no upload/import tiles of its own — a
        single unconditional "available on this screen" claim would have
        been true on one and false on the other, so the fix is asserted on
        both rather than just the one the finding named."""
        with self.signed_in(), self.service() as service:
            service.get_working_session_for_owner.return_value = None
            role_body = self.client.get(ROOM_GET).data.decode("utf-8")
        role_text = " ".join(role_body.split())
        self.assertIn(
            "Document upload and public-link import are available on this "
            "screen for signed-in members.",
            role_text,
        )
        self.assertNotIn("not available on this screen yet", role_text)

        with self.signed_in(), self.service() as service:
            service.get_working_session_for_owner.return_value = working_view()
            review_body = self.client.get(ROOM_GET).data.decode("utf-8")
        review_text = " ".join(review_body.split())
        self.assertIn(
            "Document upload and public-link import are available for "
            "signed-in members, from the role screen.",
            review_text,
        )
        self.assertNotIn("not available on this screen yet", review_text)
        # The review screen carries no upload/import tiles of its own, so
        # the role/replace screen's more specific "on this screen" claim
        # must not leak onto it.
        self.assertNotIn(
            "are available on this screen for signed-in members", review_text
        )

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

        SLICE OS-2 BROKE IT DELIBERATELY, exactly as invited. The card's
        content is a real proposal now, so the state label had to move: OS-1
        printed "None flagged" because nothing COULD be flagged, and after
        OS-2 that sentence would tell a member the wording had been read and
        come back clean when it has not been read at all. The un-reviewed
        card says "Not checked yet"; "None flagged" is now reserved for the
        state where PeerSlate genuinely did read the wording and found
        nothing (asserted separately in the AI suite). Every anti-fabrication
        assertion below is unchanged and still applies before the member asks
        for a review.
        """
        with self.signed_in(), self.service() as service:
            service.get_working_session_for_owner.return_value = working_view()
            body = self.client.get(ROOM_GET).data.decode("utf-8")
        self.assertIn("Extraction concerns", body)
        self.assertIn("Not checked yet", body)
        self.assertNotIn("None flagged", body)
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

    def test_no_ai_processing_stage_rail_is_shown_before_a_request_is_made(self):
        """Slice OS-1 had no AI call at all, so it asserted the stage rail
        did not exist anywhere in the document.

        Slice OS-2 has a real call, so the rail's markup legitimately ships —
        but only inside an inert ``<template>``, cloned into place by the room
        script when a request is genuinely in flight. The guarantee this test
        protects is unchanged and is the one that matters: on a page load,
        with nothing running, the member sees no stage rail and no stage copy.
        A LIVE rail on first paint would be theatre either way.
        """
        with self.signed_in(), self.service() as service:
            service.get_working_session_for_owner.return_value = working_view()
            body = self.client.get(ROOM_GET).data.decode("utf-8")
        # The template is inert markup; nothing outside it may mention a stage.
        outside_template = re.sub(
            r"<template data-os-stage-template>.*?</template>",
            "",
            body,
            flags=re.DOTALL,
        )
        self.assertIn("<template data-os-stage-template>", body)
        for invented in (
            "os-stage-rail",
            "Extracting employer wording",
            "Preparing source review",
            "Analyzing",
        ):
            with self.subTest(invented=invented):
                self.assertNotIn(invented, outside_template)

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

    def test_confirming_the_source_leads_to_the_requirements_checkpoint(self):
        """Slice OS-1 ended here with an honestly inert control. Slice OS-2
        built the screen it pointed at, so the control is a real link now —
        and the room resumes there rather than at checkpoint 1."""
        with self.signed_in(), self.service() as service:
            service.get_working_session_for_owner.return_value = working_view(
                confirmed_version_number=1,
                confirmed_at=datetime.now(timezone.utc),
                workbench_state="source_confirmed",
            )
            service.get_requirements_for_owner.return_value = None
            body = self.client.get(
                f"{ROOM_GET}?step=review"
            ).data.decode("utf-8")
        self.assertIn("You confirmed Source Version 1", body)
        self.assertIn("Review requirements", body)
        self.assertNotIn("data-os-inert-next", body)
        # Asserted against the form, not the button's text node: slice OS-1's
        # owner visual-parity pass gave the primary the authority's trailing
        # arrow, so the button no longer ends "Confirm source</button>" in any
        # state and a text-node assertion would pass vacuously.
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

        SLICE OS-2 adds the third: image 03 measures 57.8%, between the other
        two, because Review Requirements is a table rather than a form or a
        document. Without its own modifier it inherited the intake screen's
        53.2% — which is the same defect this test was written to catch, one
        screen later.
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

        with self.signed_in(), self.service() as service:
            service.get_working_session_for_owner.return_value = working_view(
                confirmed_version_number=1,
                confirmed_at=datetime.now(timezone.utc),
                workbench_state="source_confirmed",
            )
            service.get_requirements_for_owner.return_value = None
            landed = self.client.get(ROOM_GET).data.decode("utf-8")
        self.assertIn("Checkpoint 2 of 2", landed)
        self.assertIn("Read the statements", landed)

        with self.signed_in(), self.service() as service:
            service.get_working_session_for_owner.return_value = working_view(
                confirmed_version_number=1,
                confirmed_at=datetime.now(timezone.utc),
                workbench_state="requirements_proposed",
            )
            service.get_requirements_for_owner.return_value = requirement_set()
            requirements = self.client.get(
                f"{ROOM_GET}?step=requirements"
            ).data.decode("utf-8")
        self.assertIn("Employer statements", requirements)
        self.assertIn("os-layout os-layout--requirements", requirements)
        self.assertNotIn("os-layout--review", requirements)
        # and the two screen modifiers are mutually exclusive
        self.assertNotIn("os-layout--requirements", review)

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
        """Slice OS-1 used ?step=alignment as its example of a step that does
        not exist. Slice OS-3 built it, so the example moves; the rule does
        not, and an unknown step still lands on the member's real state rather
        than on an error."""
        with self.signed_in(), self.service() as service:
            service.get_working_session_for_owner.return_value = working_view()
            body = self.client.get(f"{ROOM_GET}?step=not-a-step").data.decode("utf-8")
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
    """2026-08-05 independent review, finding F-2. The predecessor of this
    test asserted substring presence of five hardcoded OS-1 endpoint names
    against app.py's source text. It could not fail: it never enumerated the
    routes that actually exist, so a new POST route added anywhere in this
    blueprint — with or without a limiter entry — left it green. Slice OS-4
    shipped exactly that gap (finding F-1): three new state-changing routes
    with no rate-limit entry at all, silently unthrottled because
    `limiter.default_limits=[]`.

    This test enumerates every route Flask actually registered for the
    `opportunity_slate` blueprint and fails on any POST-accepting one whose
    view function was never wrapped by the limiter — structurally, not by
    name, so it also fails on a future slice's forgotten entry.
    """

    @staticmethod
    def _is_limiter_wrapped(view_func):
        """True if ``view_func`` is the closure `RouteLimit.__call__` builds
        when `limiter.limit(...)` decorates a view (flask_limiter 4.x,
        ``flask_limiter/_limits.py``). That closure is produced with
        ``functools.wraps(obj)`` and then marked with a private attribute —
        ``__wrapper-limiter-instance`` — that is NOT a legal Python
        identifier (it contains hyphens), so it can only be reached through
        ``getattr``/``setattr`` and nothing but the limiter's own decorator
        ever sets it. A bare, undecorated view function has no such
        attribute. This is the same attribute flask_limiter itself checks,
        at call time, to avoid double-counting stacked decorations from the
        same limiter instance — so it is the library's own "was this wrapped
        by a limiter" marker, not a guess at one.
        """
        return getattr(view_func, "__wrapper-limiter-instance", None) is not None

    def test_every_post_route_on_the_blueprint_is_rate_limited(self):
        post_endpoints = sorted(
            rule.endpoint
            for rule in app.url_map.iter_rules()
            if rule.endpoint.startswith("opportunity_slate.")
            and "POST" in (rule.methods or set())
        )
        # The enumeration itself must find real routes — an empty list would
        # make every assertion below vacuously true.
        self.assertGreaterEqual(len(post_endpoints), 16)
        unwrapped = [
            endpoint
            for endpoint in post_endpoints
            if not self._is_limiter_wrapped(app.view_functions[endpoint])
        ]
        self.assertEqual(
            unwrapped,
            [],
            f"POST route(s) with no rate limit: {unwrapped}. Every "
            "state-changing Opportunity Slate route must be wrapped by "
            "limiter.limit(...) in app.py's post-registration loop.",
        )

    def test_a_route_removed_from_the_limit_table_is_caught(self):
        """The mechanism proof: strip the marker from one currently-limited
        view function, the way a forgotten app.py tuple entry would leave
        it, and confirm the structural check above actually notices."""
        endpoint = "opportunity_slate.save_slate"
        view_func = app.view_functions[endpoint]
        self.assertTrue(self._is_limiter_wrapped(view_func))
        original = view_func.__dict__.pop("__wrapper-limiter-instance")
        try:
            self.assertFalse(self._is_limiter_wrapped(view_func))
        finally:
            setattr(view_func, "__wrapper-limiter-instance", original)
        self.assertTrue(self._is_limiter_wrapped(view_func))

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

    def test_the_spend_guard_is_live_and_documents_its_real_limits(self):
        """Handoff section 18 safeguard 3. Slice OS-2 turned the ceiling from
        config-only plumbing into an enforced control, so the labelling has
        to move with it — including the two honest limits an operator needs
        before choosing a number."""
        root = __import__("pathlib").Path(__file__).resolve().parents[1]
        app_source = (root / "app.py").read_text(encoding="utf-8")
        env_example = (root / ".env.example").read_text(encoding="utf-8")
        self.assertIn("PEERSLATE_OPPSLATE_DAILY_AI_CEILING", app_source)
        self.assertIn("LIVE AS OF SLICE OS-2", app_source)
        self.assertNotIn("CONFIG ONLY IN SLICE", app_source)
        self.assertIn("PEERSLATE_OPPSLATE_DAILY_AI_CEILING=0", env_example)
        self.assertNotIn("CONFIG ONLY TODAY", env_example)
        # The limits that make the control honest rather than magic.
        self.assertIn("per worker process", app_source)
        self.assertIn("PER WORKER PROCESS", env_example)
        self.assertIn("counts calls attempted", app_source)
        # Slice OS-2 independent review, finding F12: one unit of budget
        # permits two provider requests, so the worst case an operator has
        # to size against is 2 x workers x ceiling, not the ceiling. Both
        # operator-facing documents have to say so.
        self.assertIn("2 x workers x", app_source)
        self.assertIn("2 x (worker processes) x (this value)", env_example)
        # Finding F11: the value is environment-read once, so a change needs
        # a restart. Neither document may imply otherwise.
        self.assertIn("requires an app restart", env_example)
        self.assertIn("requires a restart", app_source)

    def test_the_model_and_cost_citations_resolve_to_a_real_document(self):
        """Slice OS-2 independent review, finding F10.

        Two shipped comments cite "the slice OS-2 completion report" for the
        recorded model-comparison trial and the per-call costs. No such
        report existed, so a reader following either citation — an operator
        sizing the spend ceiling, or the next writer wondering why step 2 is
        on a different model — found nothing. The report now exists and both
        citations name its path.
        """
        root = __import__("pathlib").Path(__file__).resolve().parents[1]
        report = (
            root
            / "docs"
            / "initiatives"
            / "PS-OPPORTUNITY-SLATE-001"
            / "OS-2_COMPLETION_REPORT.md"
        )
        self.assertTrue(report.is_file(), "the cited completion report is missing")
        body = report.read_text(encoding="utf-8")
        # The two things the citations promise are actually in it.
        for recorded in (
            "Sonnet",
            "adversarial",
            "US$0.04",
            "2  x  (worker processes)  x  (the configured ceiling)",
        ):
            self.assertIn(recorded, body)

        for source in (
            root / "services" / "opportunity_analysis_service.py",
            root / ".env.example",
        ):
            with self.subTest(source=source.name):
                self.assertIn(
                    "PS-OPPORTUNITY-SLATE-001/OS-2_COMPLETION_REPORT.md",
                    source.read_text(encoding="utf-8"),
                )

    def test_every_ai_endpoint_carries_the_interview_budget(self):
        """Handoff section 18 safeguard 2: <= 6/minute per client on each AI
        endpoint, in BOTH modes."""
        source = (
            __import__("pathlib").Path(__file__).resolve().parents[1] / "app.py"
        ).read_text(encoding="utf-8")
        for endpoint in (
            "opportunity_slate.review_source_wording",
            "opportunity_slate.interpret_requirements",
            "opportunity_slate.public_propose",
        ):
            with self.subTest(endpoint=endpoint):
                index = source.index(f"'{endpoint}'")
                window = source[index : index + 120]
                self.assertIn("'6 per minute'", window)


class NoAiCallTests(unittest.TestCase):
    def test_routing_and_persistence_import_no_ai_client(self):
        """Slice OS-2 introduces AI, and confines it to exactly one module.

        services/opportunity_analysis_service.py owns every prompt contract,
        every validator, and the only Anthropic client. The route module and
        the persistence module below must still hold none of it, so a
        proposal can never be made from a place nobody reviews as an AI
        surface — and a key can never reach one.
        """
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
        # Slice OS-6 extends the accepted set to "uploaded" and "imported"
        # (services/opportunity_source_intake_service.py's guarded upload
        # and public-link import). "dictated" stays refused here: it is
        # slice OS-5's own branch and this one does not carry its routes.
        for method in ("dictated", "typed", None):
            with self.subTest(method=method):
                with self.assertRaises(OpportunitySlateServiceError) as error:
                    self.service.save_source_for_owner(
                        "member-oppslate-1", "key", ROLE_TEXT, capture_method=method
                    )
                self.assertEqual(error.exception.code, "invalid")
        self.database.first_row.assert_not_called()

    def test_save_accepts_the_slice_os6_capture_methods(self):
        for method in ("uploaded", "imported"):
            with self.subTest(method=method):
                self.database.first_row.reset_mock()
                self.database.first_row.return_value = {
                    "outcome": "success",
                    "working_session_key": SESSION_KEY,
                    "source_key": SOURCE_KEY,
                    "version_number": 1,
                    "workbench_state": "review_source",
                    "session_row_version": b"\x00" * 8,
                    "source_row_version": b"\x00" * 8,
                }
                result = self.service.save_source_for_owner(
                    "member-oppslate-1", "key", ROLE_TEXT, capture_method=method
                )
                self.assertTrue(result["saved"])
                self.database.first_row.assert_called_once()
                self.assertEqual(
                    dict(self.database.first_row.call_args[0][1])["@CaptureMethod"],
                    method,
                )

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


# ---------------------------------------------------------------------------
# lockRail vs. a permanently-unavailable mic — run in Node against the real
# function, extracted straight out of the shipped file (opportunity-slate.js
# has no CommonJS export the way dictation.js and workshop-voice.js do, so
# it cannot be required() directly; see the .test.js file's own docstring).
# ---------------------------------------------------------------------------


class LockRailUnavailableMicTests(unittest.TestCase):
    """Reviewer finding: an unsupported-browser mic came back to life —
    aria-disabled cleared, native disabled cleared — the moment a member
    pressed Cancel after any locking request, because lockRail's unlock path
    unconditionally re-enabled every [data-os-rail-control] element. Driven
    from Python by subprocess the same way tests/test_workshop_voice.py
    drives tests/workshop_voice.test.js and
    tests/test_interview_studio.py now drives tests/dictation.test.js."""

    def test_an_unavailable_mic_survives_every_lock_and_unlock(self):
        node = shutil.which("node")
        app_node = "/Applications/ChatGPT.app/Contents/Resources/cua_node/bin/node"
        if not node and os.path.isfile(app_node):
            node = app_node
        if not node:
            self.skipTest("Node is not available to run the JS lockRail tests.")

        result = subprocess.run(
            [
                node,
                os.path.join(
                    str(Path(__file__).resolve().parents[1]),
                    "tests",
                    "opportunity_slate_lockrail.test.js",
                ),
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


# ===========================================================================
# SLICE OS-4 — the save lifecycle.
#
# The two truths this slice exists to keep apart are SAVEDNESS and CURRENCY,
# and most of what follows is about the difference. "Saved" is a fact about
# what PeerSlate holds; "current" is a fact about whether it still applies to
# the member's inputs. Collapsing them is the failure this slice is designed
# to make impossible, so both directions are proved rather than asserted.
# ===========================================================================

SLATE_KEY = "66666666-6666-6666-6666-666666666666"
SLATE_TOKEN = "0000000000000010"
SAVED_RESULT_KEY = "77777777-7777-7777-7777-777777777777"
ANALYSIS_KEY = "88888888-8888-8888-8888-888888888888"
EVIDENCE_KEY = "99999999-9999-9999-9999-999999999999"
STATEMENT_KEY = "44444444-4444-4444-4444-444444444444"
SET_KEY = "55555555-5555-5555-5555-555555555555"
SET_TOKEN = "0000000000000003"

_UNSET = object()


def room_markup(html):
    """The Opportunity Slate room, without the shared site shell.

    base.html carries its own long implementation comment that happens to
    contain "1180/1040/860/780px", which a no-verdict scan run over the whole
    page reads as a ratio. The rule is about what the ROOM says, so the scan
    is pointed at the room.
    """
    start = html.index("data-os-room")
    tail = html[start:]
    end = tail.find("<footer")
    return tail[:end] if end > 0 else tail


OS4_MEMBER_POSTS = (
    "/opportunity-slate/save",
    "/opportunity-slate/reanalyze",
    "/opportunity-slate/delete",
)
SAVED_GET = "/opportunity-slate/saved"


def analysis_view(**overrides):
    """One analysed qualification with one citation — the smallest shape that
    is genuinely saveable."""
    citation = AnalysisCitationView(
        ordinal=1,
        clause_ordinal=1,
        covered_text="Systems engineering",
        evidence_kind="knowledge_item",
        evidence_key=EVIDENCE_KEY,
        evidence_version=1,
        evidence_title="Systems Engineering Experience Summary",
        excerpt="Led systems-integration and verification-readiness work.",
    )
    statement = AnalysisStatementView(
        statement_key=STATEMENT_KEY,
        ordinal=1,
        status="supported",
        citation_count=1,
        citations=(citation,),
    )
    fields = {
        "analysis_key": ANALYSIS_KEY,
        "version_token": "0000000000000005",
        "source_version_number": 1,
        "requirement_version_number": 1,
        "model_name": "claude-sonnet-5",
        "prompt_contract_version": "os-alignment-v1",
        "evidence_considered_count": 1,
        "qualification_count": 1,
        "analyzed_at": datetime.now(timezone.utc),
        "statements": (statement,),
    }
    fields.update(overrides)
    return AnalysisView(**fields)


def evidence_item(**overrides):
    fields = {
        "evidence_key": EVIDENCE_KEY,
        "version": 1,
        "title": "Systems Engineering Experience Summary",
        "body": "Led systems-integration and verification-readiness work.",
        "updated_at": datetime.now(timezone.utc),
    }
    fields.update(overrides)
    return EvidenceItemView(**fields)


# The content digest of the fixtures above: `working_view()`'s displayed
# source wording, and `requirement_set()`'s single analysed statement at its
# proposed class. Computed from the same function the routes call, so a test
# cannot pass because the fixture agreed with a hand-written constant.
FIXTURE_CONTENT_DIGEST = compute_content_digest(
    ROLE_TEXT,
    (
        (
            1,
            "required_qualification",
            "Strong understanding of systems engineering processes.",
        ),
    ),
)


def saved_slate(
    *,
    pinned_evidence_version=1,
    current_evidence_version=1,
    source_version_number=1,
    requirement_version_number=1,
    analysis_key=ANALYSIS_KEY,
    version_count=1,
    total_version_count=None,
    statement_class="required_qualification",
    employer_text="Strong understanding of systems engineering processes.",
    source_text=ROLE_TEXT,
):
    """A saved slate whose stored fingerprint is genuinely the digest of its
    own pinned inputs — computed, never hand-written, so a test can never
    pass because the fixture lied about what was saved."""
    evidence = SavedEvidenceView(
        ordinal=1,
        clause_ordinal=1,
        covered_text="Systems engineering",
        evidence_kind="knowledge_item",
        evidence_key=EVIDENCE_KEY,
        evidence_version=pinned_evidence_version,
        evidence_title="Systems Engineering Experience Summary",
        excerpt="Led systems-integration and verification-readiness work.",
    )
    qualification = SavedQualificationView(
        ordinal=1,
        statement_class=statement_class,
        employer_text=employer_text,
        status="supported",
        citation_count=1,
        response_kind="tell_more",
        response_text="I ran the integration reviews for two programmes.",
        authored_via="typed",
        connected_evidence_title=None,
        connected_evidence_version=None,
        evidence=(evidence,),
    )
    now = datetime.now(timezone.utc)
    versions = tuple(
        SavedVersionView(
            saved_result_key=SAVED_RESULT_KEY if index == 1 else f"{index}" * 8
            + "-1111-1111-1111-111111111111",
            save_version_number=index,
            source_version_number=source_version_number,
            requirement_version_number=requirement_version_number,
            qualification_count=1,
            saved_at=now,
        )
        for index in range(version_count, 0, -1)
    )
    return SavedSlateView(
        slate_key=SLATE_KEY,
        version_token=SLATE_TOKEN,
        created_at=now,
        total_version_count=(
            version_count if total_version_count is None else total_version_count
        ),
        saved_result_key=SAVED_RESULT_KEY,
        save_version_number=version_count,
        source_version_number=source_version_number,
        requirement_version_number=requirement_version_number,
        saved_analysis_key=analysis_key,
        source_text=source_text,
        model_name="claude-sonnet-5",
        prompt_contract_version="os-alignment-v1",
        evidence_considered_count=1,
        qualification_count=1,
        input_fingerprint=compute_input_fingerprint(
            source_version_number,
            requirement_version_number,
            ((EVIDENCE_KEY, pinned_evidence_version),),
            content_digest=compute_content_digest(
                source_text, ((1, statement_class, employer_text),)
            ),
        ),
        saved_at=now,
        qualifications=(qualification,),
        versions=versions,
        evidence_currency=(
            (EVIDENCE_KEY, pinned_evidence_version, current_evidence_version),
        ),
    )


def fingerprint(source=1, requirements=1, evidence=((EVIDENCE_KEY, 1),),
                content=None):
    return compute_input_fingerprint(
        source,
        requirements,
        evidence,
        content_digest=FIXTURE_CONTENT_DIGEST if content is None else content,
    )


class InputFingerprintTests(unittest.TestCase):
    """The digest that decides "Saved" from "Saved, but no longer current"."""

    def test_the_same_inputs_produce_the_same_digest(self):
        self.assertEqual(fingerprint(), fingerprint())
        self.assertRegex(fingerprint(), r"^[0-9a-f]{64}$")

    def test_row_order_does_not_change_the_digest(self):
        """The two call sites read from different result sets, so a digest
        that depended on row order would report staleness that is not there."""
        other = "12121212-1212-1212-1212-121212121212"
        forward = fingerprint(evidence=((EVIDENCE_KEY, 1), (other, 2)))
        reversed_order = fingerprint(evidence=((other, 2), (EVIDENCE_KEY, 1)))
        self.assertEqual(forward, reversed_order)

    def test_each_input_moves_the_digest(self):
        base = fingerprint()
        for changed in (
            fingerprint(source=2),
            fingerprint(requirements=2),
            fingerprint(evidence=((EVIDENCE_KEY, 2),)),
            fingerprint(content=compute_content_digest("something else", ())),
        ):
            self.assertNotEqual(base, changed)

    def test_a_vanished_evidence_record_is_a_change_not_an_absence(self):
        """An archived, un-confirmed or deleted record has no current
        version. Encoding it as 0 rather than dropping it is what stops a
        vanished citation looking identical to one that was never made."""
        pinned = fingerprint(evidence=((EVIDENCE_KEY, 1),))
        gone = fingerprint(evidence=((EVIDENCE_KEY, None),))
        never_cited = fingerprint(evidence=())
        self.assertNotEqual(pinned, gone)
        self.assertNotEqual(gone, never_cited)


class ContentDigestTests(unittest.TestCase):
    """Finding F1's mechanism. The two in-place edits that move no version
    number must still move this digest, or a saved result reads "current"
    over wording the member has since changed."""

    def test_correcting_the_source_wording_moves_the_digest(self):
        statements = ((1, "required_qualification", "Systems engineering."),)
        self.assertNotEqual(
            compute_content_digest(ROLE_TEXT, statements),
            compute_content_digest(ROLE_TEXT + " Amended.", statements),
        )

    def test_reclassifying_a_statement_moves_the_digest(self):
        self.assertNotEqual(
            compute_content_digest(
                ROLE_TEXT, ((1, "required_qualification", "Systems engineering."),)
            ),
            compute_content_digest(
                ROLE_TEXT, ((1, "preferred_qualification", "Systems engineering."),)
            ),
        )

    def test_a_statement_leaving_the_analysed_set_moves_the_digest(self):
        self.assertNotEqual(
            compute_content_digest(
                ROLE_TEXT,
                (
                    (1, "required_qualification", "One."),
                    (2, "required_qualification", "Two."),
                ),
            ),
            compute_content_digest(
                ROLE_TEXT, ((1, "required_qualification", "One."),)
            ),
        )

    def test_row_order_does_not_change_the_digest(self):
        forward = compute_content_digest(
            ROLE_TEXT,
            ((1, "required_qualification", "One."),
             (2, "preferred_qualification", "Two.")),
        )
        reverse = compute_content_digest(
            ROLE_TEXT,
            ((2, "preferred_qualification", "Two."),
             (1, "required_qualification", "One.")),
        )
        self.assertEqual(forward, reverse)

    def test_statement_text_cannot_collide_through_a_delimiter(self):
        """Employer wording is hashed, not concatenated, so a statement
        containing the canonical string's own separators cannot be made to
        digest the same as a different reading."""
        self.assertNotEqual(
            compute_content_digest(
                ROLE_TEXT, ((1, "required_qualification", "A|2:required:B"),)
            ),
            compute_content_digest(
                ROLE_TEXT,
                ((1, "required_qualification", "A"),
                 (2, "required_qualification", "B")),
            ),
        )


class SavedStateResolutionTests(unittest.TestCase):
    """Which of the three states the screen is in — the one decision in this
    slice that decides what a member is told about their own data."""

    def test_no_saved_slate_is_the_unsaved_state(self):
        self.assertEqual(routes._resolve_saved_state(None, ANALYSIS_KEY, True), "unsaved")

    def test_the_saved_analysis_that_still_applies_is_the_saved_state(self):
        saved = saved_slate()
        self.assertEqual(
            routes._resolve_saved_state(saved, ANALYSIS_KEY, True), "saved"
        )

    def test_the_saved_analysis_whose_inputs_moved_is_the_stale_state(self):
        saved = saved_slate()
        self.assertEqual(
            routes._resolve_saved_state(saved, ANALYSIS_KEY, False), "saved_stale"
        )

    def test_a_newer_unsaved_analysis_on_screen_is_never_shown_as_saved(self):
        """The defect this comparison exists to prevent: a member presses
        `Run this again`, gets a different result, and is shown a green
        "Saved privately" banner over something that was never saved."""
        saved = saved_slate()
        self.assertEqual(
            routes._resolve_saved_state(saved, "different-analysis-key", True),
            "unsaved",
        )

    def test_with_no_analysis_on_screen_the_saved_result_speaks_for_itself(self):
        saved = saved_slate()
        self.assertEqual(routes._resolve_saved_state(saved, None, True), "saved")
        self.assertEqual(
            routes._resolve_saved_state(saved, None, False), "saved_stale"
        )


class CurrencyTests(unittest.TestCase):
    """Both directions, including the one the architecture calls out: an
    evidence item's version changing underneath a saved result."""

    def current(self, saved, source=1, requirements=1, content=None,
                confirmed=True):
        return saved.is_current_for(
            source,
            requirements,
            FIXTURE_CONTENT_DIGEST if content is None else content,
            inputs_confirmed=confirmed,
        )

    def test_unchanged_inputs_read_as_current(self):
        self.assertTrue(self.current(saved_slate()))

    def test_a_referenced_evidence_version_changing_underneath_reads_as_stale(self):
        saved = saved_slate(pinned_evidence_version=1, current_evidence_version=2)
        self.assertFalse(self.current(saved))

    def test_a_referenced_evidence_record_disappearing_reads_as_stale(self):
        saved = saved_slate(pinned_evidence_version=1, current_evidence_version=None)
        self.assertFalse(self.current(saved))

    def test_a_new_source_or_requirement_version_reads_as_stale(self):
        saved = saved_slate()
        self.assertFalse(self.current(saved, source=2))
        self.assertFalse(self.current(saved, requirements=2))

    def test_corrected_source_wording_reads_as_stale(self):
        """Finding F1. `usp_CorrectOpportunitySourceForOwner` rewrites the
        correction overlay IN PLACE — no version number moves — so before the
        content digest existed this read "Current for these inputs" over
        wording the member had since changed."""
        saved = saved_slate()
        corrected = compute_content_digest(
            ROLE_TEXT + "\n- Security clearance required\n",
            (
                (
                    1,
                    "required_qualification",
                    "Strong understanding of systems engineering processes.",
                ),
            ),
        )
        self.assertFalse(self.current(saved, content=corrected))

    def test_a_reclassified_statement_reads_as_stale(self):
        """Finding F1, second case. A member correction rewrites
        `member_class` in place and clears only the confirmation."""
        saved = saved_slate()
        reclassified = compute_content_digest(
            ROLE_TEXT,
            (
                (
                    1,
                    "preferred_qualification",
                    "Strong understanding of systems engineering processes.",
                ),
            ),
        )
        self.assertFalse(self.current(saved, content=reclassified))

    def test_an_unconfirmed_reading_is_never_reported_current(self):
        """The structural backstop. A member mid-edit has not confirmed the
        inputs the saved result would be current FOR, and this refusal does
        not depend on the digest having been taught about the edit."""
        saved = saved_slate()
        self.assertFalse(self.current(saved, confirmed=False))

    def test_no_working_inputs_at_all_reads_as_stale_rather_than_current(self):
        """A member who deleted their working session still has their saved
        result. It cannot be "current for these inputs" when there are no
        inputs, and the screen must not claim it is."""
        self.assertFalse(
            routes._saved_currency(saved_slate(), None, None)
        )

    def test_a_snapshot_that_disagrees_with_itself_is_never_reported_current(self):
        """The stored fingerprint and the pinned rows are two records of one
        fact. If they disagree the row is not trustworthy, and under-claiming
        is the only safe direction."""
        saved = saved_slate()
        tampered = replace(saved, input_fingerprint="0" * 64)
        self.assertFalse(self.current(tampered))

    def test_a_snapshot_whose_copied_wording_was_altered_is_never_current(self):
        """The integrity half of finding F1's fix: the pinned side of the
        content digest is rebuilt from the snapshot's own copied source text
        and qualifications, so a saved row edited underneath the stored
        fingerprint stops agreeing with itself."""
        saved = saved_slate()
        tampered = replace(saved, source_text=ROLE_TEXT + " altered")
        self.assertFalse(self.current(tampered))


class MemberSaveLifecycleTestCase(OpportunitySlateTestCase):
    def alignment_service(
        self, service, *, saved=None, analysis=_UNSET, working=None,
        requirements=None,
    ):
        service.get_working_session_for_owner.return_value = (
            working
            if working is not None
            else working_view(
                confirmed_version_number=1, confirmed_at=datetime.now(timezone.utc)
            )
        )
        service.get_requirements_for_owner.return_value = (
            requirements
            if requirements is not None
            else requirement_set(
                confirmed_version_number=1, confirmed_at=datetime.now(timezone.utc)
            )
        )
        service.get_analysis_for_owner.return_value = (
            analysis_view() if analysis is _UNSET else analysis,
            {},
        )
        service.list_evidence_for_owner.return_value = (evidence_item(),)
        service.get_saved_slate_for_owner.return_value = saved
        return service

    def workbench(self, *, saved=None, analysis=_UNSET, query="", working=None,
                  requirements=None):
        with self.signed_in(), self.service() as service:
            self.alignment_service(
                service,
                saved=saved,
                analysis=analysis,
                working=working,
                requirements=requirements,
            )
            response = self.client.get(
                f"{ROOM_GET}?step=alignment{query}"
            )
        return response

    def workbench_markup(self, **kwargs):
        return room_markup(self.workbench(**kwargs).data.decode("utf-8"))


class SavedWorkbenchRenderTests(MemberSaveLifecycleTestCase):
    def test_the_unsaved_workbench_offers_a_real_save_control(self):
        html = self.workbench().data.decode("utf-8")
        self.assertIn("Results not saved", html)
        self.assertIn("data-os-save", html)
        self.assertIn("Save privately", html)
        self.assertIn("/opportunity-slate/save", html)
        self.assertNotIn("Current for these inputs", html)

    def test_the_saved_workbench_is_image_05s_content_in_image_04s_geometry(self):
        html = self.workbench(saved=saved_slate()).data.decode("utf-8")
        # Image 05's saved content and actions.
        self.assertIn("Saved privately", html)
        self.assertIn("Current for these inputs", html)
        self.assertIn("View saved details", html)
        self.assertIn("Done for now", html)
        self.assertIn("PeerSlate retained the reviewed source version", html)
        self.assertNotIn("Results not saved", html)
        # Image 04's geometry: four separate cards, never image 05's merge.
        for label in (
            "Required qualifications",
            "Preferred qualifications",
            "Responsibilities",
            "Informational statements",
        ):
            self.assertIn(label, html)
        self.assertNotIn("Responsibilities and informational statements", html)
        # And the same table, rails and summary cards as the unsaved state —
        # saving moved nothing.
        for shared in ("os-align__row", "os-summary__counts", "Evidence review"):
            self.assertIn(shared, html)

    def test_saving_does_not_regenerate_or_close_the_workspace(self):
        """Handoff section 7: the member stays exactly where they were. The
        proof is that the saved and unsaved renders carry the same cards, the
        same table rows and the same selected qualification."""
        unsaved = self.workbench().data.decode("utf-8")
        saved = self.workbench(saved=saved_slate()).data.decode("utf-8")
        for marker in (
            'data-os-align-row="44444444-4444-4444-4444-444444444444"',
            "os-card--panel os-qual",
            "os-context-strip",
        ):
            self.assertIn(marker, unsaved)
            self.assertIn(marker, saved)
        self.assertEqual(
            unsaved.count("os-card--panel os-qual"),
            saved.count("os-card--panel os-qual"),
        )

    def test_the_stale_state_carries_image_09cs_exact_copy_and_actions(self):
        saved = saved_slate(pinned_evidence_version=1, current_evidence_version=2)
        html = self.workbench(saved=saved).data.decode("utf-8")
        self.assertIn("Saved privately", html)
        self.assertIn("Inputs changed", html)
        self.assertIn("Reanalysis required", html)
        self.assertIn(
            "The saved result remains available for Source Version 1.", html
        )
        self.assertIn("It does not apply to your changed inputs.", html)
        self.assertIn("Reanalyze", html)
        self.assertIn("View saved result", html)
        self.assertIn("Review inputs", html)
        # It never says the stale result is current.
        self.assertNotIn("Current for these inputs", html)

    def test_a_newer_unsaved_analysis_reports_itself_unsaved(self):
        saved = saved_slate(analysis_key="an-older-analysis-key")
        html = self.workbench(saved=saved).data.decode("utf-8")
        self.assertIn("Results not saved", html)
        self.assertNotIn("Current for these inputs", html)

    def test_the_reanalyzed_footer_does_not_claim_nothing_is_saved(self):
        """2026-08-05 independent review, finding F-3. This is the same
        reanalyzed screen as the test above: `saved` is not None (the member
        has a saved slate) but its `saved_analysis_key` does not match the
        analysis on screen, so `_resolve_saved_state` correctly reports
        "unsaved" and the rail correctly says a saved result remains
        available. The footer a few hundred pixels below it used to render
        ALIGNMENT_FOOTER_TRUTH_PRIVATE unconditionally — "Session private ·
        Nothing is saved yet" — directly contradicting the rail.

        The prior regression guard for this sentence
        (SaveFailureTruthTests, a different card entirely) checked for
        "Nothing is saved yet." WITH a trailing period; the real footer
        constant has none, so a check written the same way here would have
        passed while the bug shipped. This asserts the exact periodless
        string that actually ships.
        """
        saved = saved_slate(analysis_key="an-older-analysis-key")
        html = self.workbench(saved=saved).data.decode("utf-8")
        # The rail already correctly says a saved result exists elsewhere.
        self.assertIn("A saved result from", html)
        self.assertIn("Source Version 1", html)
        self.assertIn("View saved details", html)
        # The footer must not contradict it — neither spelling.
        self.assertNotIn("Session private · Nothing is saved yet", html)
        self.assertNotIn("Nothing is saved yet.", html)
        self.assertNotIn("Nothing is saved yet", html)
        # And it must say the true thing instead, in the footer's own voice.
        self.assertIn(
            "Session private · Nothing new was saved. Your saved slate is "
            "unchanged.",
            html,
        )

    def test_the_never_saved_footer_still_says_nothing_is_saved_yet(self):
        """The other direction, guarding against an over-broad fix: a member
        with genuinely no saved slate at all must still see the honest
        unsaved footer, unchanged by the F-3 conditional."""
        html = self.workbench().data.decode("utf-8")
        self.assertIn("Session private · Nothing is saved yet", html)
        self.assertNotIn("Nothing new was saved", html)

    def test_no_score_percentage_or_verdict_reaches_any_saved_surface(self):
        for saved in (
            None,
            saved_slate(),
            saved_slate(current_evidence_version=2),
        ):
            html = self.workbench_markup(saved=saved)
            with self.subTest(saved=bool(saved)):
                self.assertIsNone(
                    re.search(r"\d+\s*%|\d+\s*/\s*\d+|\d+ out of \d+", html)
                )
                for banned in (
                    "overall score",
                    "match score",
                    "percentile",
                    "ranking",
                    "we recommend",
                    "strong candidate",
                    "good fit",
                ):
                    self.assertNotIn(banned, html.lower())


class StatusFilterTests(MemberSaveLifecycleTestCase):
    """Image 05's filter row (handoff section 14-M4), in image 04's grammar."""

    def test_the_filter_row_renders_image_05s_four_tabs(self):
        html = self.workbench().data.decode("utf-8")
        self.assertIn("data-os-filters", html)
        for label in (
            ">All<",
            ">Supported<",
            ">Partially supported<",
            ">Not enough information<",
        ):
            self.assertIn(label, html)

    def test_the_filter_row_sits_between_the_summaries_and_the_first_card(self):
        """Image 05's placement exactly: below the two count summary cards,
        above the first qualification card, spanning the workbench."""
        html = self.workbench().data.decode("utf-8")
        summaries = html.index("os-summary__counts")
        filters = html.index("os-card--filters")
        first_card = html.index("os-card--panel os-qual")
        self.assertLess(summaries, filters)
        self.assertLess(filters, first_card)

    def test_a_filter_hides_the_rows_it_excludes_in_the_status_cards(self):
        html = self.workbench(query="&status=not_enough_information").data.decode(
            "utf-8"
        )
        row = html.index('data-os-align-row="44444444')
        window = html[row : row + 400]
        # The one analysed row is Supported, so this filter hides it.
        self.assertIn("hidden", window)
        self.assertIn("Showing 0 of 1", html)

    def test_the_active_filter_keeps_its_matching_rows(self):
        html = self.workbench(query="&status=supported").data.decode("utf-8")
        row = html.index('data-os-align-row="44444444')
        self.assertNotIn("hidden", html[row : row + 200])
        self.assertIn("Showing 1 of 1", html)

    def test_the_summary_totals_are_never_filtered(self):
        """They are the locked accounting. A filtered total would be a
        different number wearing the same label."""
        unfiltered = self.workbench().data.decode("utf-8")
        filtered = self.workbench(query="&status=not_enough_information").data.decode(
            "utf-8"
        )
        for html in (unfiltered, filtered):
            summary = html[
                html.index("os-summary__counts") : html.index("os-card--filters")
            ]
            self.assertIn("Supported", summary)
        self.assertEqual(
            unfiltered.count("os-summary__entry"),
            filtered.count("os-summary__entry"),
        )

    def test_the_filter_does_not_apply_to_the_cards_that_carry_no_status(self):
        """Responsibilities and Informational statements were compared
        against nothing, so they have no status to filter on — and they are
        never merged into one card (handoff section 14-M14)."""
        html = self.workbench(query="&status=supported").data.decode("utf-8")
        self.assertIn("Responsibilities", html)
        self.assertIn("Informational statements", html)
        self.assertNotIn("Responsibilities and informational statements", html)
        self.assertEqual(html.count("data-os-qual-card"), 2)

    def test_an_unknown_filter_falls_back_to_all_rather_than_an_empty_table(self):
        html = self.workbench(query="&status=excellent").data.decode("utf-8")
        row = html.index('data-os-align-row="44444444')
        self.assertNotIn("hidden", html[row : row + 200])

    def test_the_filtered_result_is_announced_politely(self):
        html = self.workbench().data.decode("utf-8")
        self.assertIn("data-os-filter-live", html)
        self.assertIn('role="status"', html)


class SaveRouteTests(MemberSaveLifecycleTestCase):
    def save(self, service_setup=None, **form):
        payload = {
            "idempotency_key": "idem-1",
            "statement_key": STATEMENT_KEY,
            "status": "all",
        }
        payload.update(form)
        with self.signed_in(), self.service() as service:
            self.alignment_service(service)
            if service_setup:
                service_setup(service)
            response = self.client.post(
                "/opportunity-slate/save",
                data=payload,
                headers=SAME_ORIGIN_HEADERS,
            )
            return response, service

    def test_a_save_passes_the_confirmed_set_its_fence_and_a_real_digest(self):
        response, service = self.save()
        self.assertEqual(response.status_code, 302)
        service.save_slate_for_owner.assert_called_once()
        args = service.save_slate_for_owner.call_args[0]
        self.assertEqual(args[0], "member-oppslate-1")
        self.assertEqual(args[1], "idem-1")
        self.assertEqual(args[2], SET_KEY)
        self.assertEqual(args[3], SET_TOKEN)
        # The digest is the one the read side will recompute, not a constant.
        self.assertEqual(
            args[4], fingerprint(1, 1, ((EVIDENCE_KEY, 1),))
        )

    def test_saving_returns_the_member_to_the_same_screen_they_were_reading(self):
        response, _ = self.save(status="supported")
        self.assertEqual(response.status_code, 302)
        self.assertIn("step=alignment", response.headers["Location"])
        self.assertIn(f"statement={STATEMENT_KEY}", response.headers["Location"])
        self.assertIn("status=supported", response.headers["Location"])

    def test_a_replayed_save_is_reported_as_existing_and_appends_nothing(self):
        def existing(service):
            service.save_slate_for_owner.return_value = {
                "outcome": "existing",
                "slate_key": SLATE_KEY,
                "saved_result_key": SAVED_RESULT_KEY,
                "save_version_number": 1,
                "qualification_count": 1,
            }

        response, service = self.save(service_setup=existing)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(service.save_slate_for_owner.call_count, 1)

    def test_saving_with_no_analysis_refuses_honestly_and_saves_nothing(self):
        def no_analysis(service):
            service.get_analysis_for_owner.return_value = (None, {})

        response, service = self.save(service_setup=no_analysis)
        self.assertEqual(response.status_code, 400)
        service.save_slate_for_owner.assert_not_called()
        body = response.data.decode("utf-8")
        self.assertIn("There is no completed analysis to save yet", body)
        self.assertIn("nothing was lost", body)

    def test_a_changed_requirement_set_refuses_with_the_members_work_intact(self):
        def conflict(service):
            service.save_slate_for_owner.side_effect = OpportunitySlateServiceError(
                "changed", code="changed"
            )

        response, _ = self.save(service_setup=conflict)
        self.assertEqual(response.status_code, 409)
        body = response.data.decode("utf-8")
        self.assertIn("Nothing was saved.", body)
        # The workbench is still there, with the employer's own wording.
        self.assertIn("Strong understanding of systems engineering", body)

    def test_a_storage_failure_is_a_truthful_503_that_saves_nothing(self):
        def unavailable(service):
            service.save_slate_for_owner.side_effect = DatabaseServiceError("down")

        response, _ = self.save(service_setup=unavailable)
        self.assertEqual(response.status_code, 503)
        self.assertIn("Nothing was saved", response.data.decode("utf-8"))


class SaveFailureTruthTests(MemberSaveLifecycleTestCase):
    """Finding F2. The failure card renders beside the saved banner, so the
    two must not contradict each other. Measured on the rendered page."""

    FAILURES = {
        503: lambda service: setattr(
            service.save_slate_for_owner, "side_effect", DatabaseServiceError("down")
        ),
        409: lambda service: setattr(
            service.save_slate_for_owner,
            "side_effect",
            OpportunitySlateServiceError("changed", code="changed"),
        ),
        400: lambda service: setattr(
            service, "get_analysis_for_owner", MagicMock(return_value=(None, {}))
        ),
    }

    def failed_save(self, status, *, saved):
        with self.signed_in(), self.service() as service:
            self.alignment_service(service, saved=saved)
            self.FAILURES[status](service)
            response = self.client.post(
                "/opportunity-slate/save",
                data={"idempotency_key": "idem-1"},
                headers=SAME_ORIGIN_HEADERS,
            )
        self.assertEqual(response.status_code, status)
        return response.data.decode("utf-8")

    def test_a_member_with_nothing_saved_is_told_nothing_is_saved(self):
        for status in self.FAILURES:
            with self.subTest(status=status):
                body = self.failed_save(status, saved=None)
                self.assertIn("Nothing is saved yet.", body)
                self.assertNotIn("Nothing new was saved", body)

    def test_a_member_with_a_saved_slate_is_never_told_nothing_is_saved(self):
        """The defect: "Saved privately", "Current for these inputs" and
        "Nothing is saved yet." all rendered on one screen."""
        for status in self.FAILURES:
            with self.subTest(status=status):
                body = self.failed_save(status, saved=saved_slate())
                self.assertIn("Saved privately", body)
                self.assertIn(
                    "Nothing new was saved. Your saved slate is unchanged.", body
                )
                self.assertNotIn("Nothing is saved yet.", body)

    def test_the_failure_still_says_plainly_that_this_attempt_stored_nothing(self):
        body = self.failed_save(503, saved=saved_slate())
        self.assertIn("Nothing new was saved", body)
        self.assertIn("Session private", body)


def corrected_source_working():
    """The working session AFTER `usp_CorrectOpportunitySourceForOwner`: the
    correction overlay is set, `current_version_number` has NOT moved, and the
    confirmation is cleared."""
    return working_view(
        member_corrected_text=ROLE_TEXT + "- Security clearance required\n",
        corrected_at=datetime.now(timezone.utc),
        confirmed_version_number=None,
        confirmed_at=None,
    )


def reclassified_requirement_set(confirmed=False):
    """The requirement set AFTER
    `usp_CorrectOpportunityRequirementStatementForOwner`: `member_class` is
    rewritten in place, `version_number` has NOT moved, and the confirmation
    is cleared. ``confirmed=True`` is the member re-confirming afterwards
    without changing anything back — the case a confirmation-only guard
    would miss."""
    base = requirement_set(
        confirmed_version_number=1 if confirmed else None,
        confirmed_at=datetime.now(timezone.utc) if confirmed else None,
    )
    statement = replace(base.statements[0], member_class="preferred_qualification")
    return replace(base, statements=(statement,))


class CurrencyRenderTests(MemberSaveLifecycleTestCase):
    """Finding F1, rendered. Both screens that report currency, over the two
    ordinary member actions that change a confirmed input without moving any
    version number. Asserted on the real rendered page rather than on the
    function, because the defect was that the screens SAID "current"."""

    def screens(self, *, saved, working=None, requirements=None):
        alignment = self.workbench(
            saved=saved,
            # A source or statement correction deletes the working analysis,
            # which is exactly why `_resolve_saved_state` falls through to the
            # saved result and why currency has to carry the truth alone.
            analysis=None,
            working=working,
            requirements=requirements,
        ).data.decode("utf-8")
        with self.signed_in(), self.service() as service:
            self.alignment_service(
                service, saved=saved, analysis=None, working=working,
                requirements=requirements,
            )
            details = self.client.get(SAVED_GET).data.decode("utf-8")
        return alignment, details

    def assert_current(self, saved, **kwargs):
        for name, html in zip(("alignment", "saved details"),
                              self.screens(saved=saved, **kwargs)):
            with self.subTest(screen=name):
                self.assertIn("Current for these inputs", html)
                self.assertNotIn("Inputs changed", html)

    def assert_stale(self, saved, **kwargs):
        for name, html in zip(("alignment", "saved details"),
                              self.screens(saved=saved, **kwargs)):
            with self.subTest(screen=name):
                self.assertIn("Inputs changed", html)
                self.assertNotIn("Current for these inputs", html)

    def test_untouched_inputs_still_read_as_current_on_both_screens(self):
        """The other direction. A fix that made everything stale would pass
        every staleness test and be useless."""
        self.assert_current(saved_slate())

    def test_corrected_source_wording_reads_as_changed_on_both_screens(self):
        self.assert_stale(saved_slate(), working=corrected_source_working())

    def test_a_reclassified_statement_reads_as_changed_on_both_screens(self):
        self.assert_stale(
            saved_slate(), requirements=reclassified_requirement_set()
        )

    def test_reconfirming_a_correction_does_not_restore_a_false_current(self):
        """The case that decided the fix. Re-confirming restores
        `confirmed_version_number = current_version_number` WITHOUT moving the
        version, so a confirmation-state guard alone would report "current"
        again over the member's changed reading. The content digest is what
        actually answers it."""
        self.assert_stale(
            saved_slate(),
            requirements=reclassified_requirement_set(confirmed=True),
        )

    def test_an_unconfirmed_reading_alone_is_enough_to_refuse_current(self):
        """The backstop, on its own: nothing about the content changed here,
        only the confirmation state."""
        self.assert_stale(
            saved_slate(),
            working=working_view(confirmed_version_number=None, confirmed_at=None),
        )


class ReanalyzeRouteTests(MemberSaveLifecycleTestCase):
    def test_reanalyze_runs_a_new_analysis_and_never_touches_the_saved_one(self):
        with self.signed_in(), self.service() as service:
            self.alignment_service(service, saved=saved_slate())
            with patch.object(
                routes, "_run_alignment_for_owner", return_value=(None, None)
            ) as run:
                response = self.client.post(
                    "/opportunity-slate/reanalyze", headers=SAME_ORIGIN_HEADERS
                )
        self.assertEqual(response.status_code, 302)
        run.assert_called_once()
        # It is a reanalysis, not a re-save and not a deletion.
        service.save_slate_for_owner.assert_not_called()
        service.delete_saved_slate_for_owner.assert_not_called()

    def test_nothing_reanalyzes_without_an_explicit_member_action(self):
        """Rendering the stale workbench must not run an AI step. The only
        thing that reanalyzes is the member pressing Reanalyze."""
        saved = saved_slate(current_evidence_version=2)
        with self.signed_in(), self.service() as service:
            self.alignment_service(service, saved=saved)
            with patch.object(routes, "_run_alignment_for_owner") as run:
                self.client.get(f"{ROOM_GET}?step=alignment")
        run.assert_not_called()


class DeleteRouteTests(MemberSaveLifecycleTestCase):
    def delete(self, service_setup=None):
        with self.signed_in(), self.service() as service:
            self.alignment_service(service, saved=saved_slate())
            if service_setup:
                service_setup(service)
            response = self.client.post(
                "/opportunity-slate/delete",
                data={
                    "slate_key": SLATE_KEY,
                    "slate_version_token": SLATE_TOKEN,
                },
                headers=SAME_ORIGIN_HEADERS,
            )
            return response, service

    def test_a_delete_is_fenced_and_owner_scoped(self):
        response, service = self.delete()
        self.assertEqual(response.status_code, 302)
        service.delete_saved_slate_for_owner.assert_called_once_with(
            "member-oppslate-1", SLATE_KEY, SLATE_TOKEN
        )

    def test_a_delete_never_touches_the_working_session(self):
        _, service = self.delete()
        service.delete_working_session_for_owner.assert_not_called()

    def test_a_failed_delete_shows_image_09d_over_a_slate_that_is_still_saved(self):
        def fails(service):
            service.delete_saved_slate_for_owner.side_effect = DatabaseServiceError(
                "down"
            )

        response, _ = self.delete(service_setup=fails)
        self.assertEqual(response.status_code, 503)
        body = response.data.decode("utf-8")
        self.assertIn("We couldn&#39;t delete this saved slate.", body)
        self.assertIn("It remains saved privately. Nothing was removed.", body)
        self.assertIn("Try again", body)
        self.assertIn("Cancel", body)
        # And the slate is visibly, completely still there underneath it.
        self.assertIn("Saved privately", body)
        self.assertIn("Systems Engineering Experience Summary", body)
        self.assertIn("Source Version 1", body)

    def test_a_conflicted_delete_also_leaves_the_slate_visibly_saved(self):
        def conflict(service):
            service.delete_saved_slate_for_owner.side_effect = (
                OpportunitySlateServiceError("changed", code="changed")
            )

        response, _ = self.delete(service_setup=conflict)
        self.assertEqual(response.status_code, 409)
        body = response.data.decode("utf-8")
        self.assertIn("It remains saved privately. Nothing was removed.", body)
        self.assertIn("Saved privately", body)

    def test_a_failed_delete_does_not_relabel_a_current_result_as_stale(self):
        """Finding F4. The error path passed `is_current=False` regardless,
        so a member whose delete failed on an unchanged result was told
        "Inputs changed · Reanalysis required" and "It does not apply to your
        changed inputs" — both false, on the one screen whose job is to be
        believed after a failure."""
        def fails(service):
            service.delete_saved_slate_for_owner.side_effect = DatabaseServiceError(
                "down"
            )

        response, _ = self.delete(service_setup=fails)
        body = response.data.decode("utf-8")
        self.assertIn("Current for these inputs", body)
        self.assertNotIn("Inputs changed", body)
        self.assertNotIn("It does not apply to your changed inputs.", body)

    def test_a_failed_delete_over_changed_inputs_still_says_so(self):
        """The other direction: preserving the real state must not turn into
        always claiming currency."""
        def fails(service):
            service.get_saved_slate_for_owner.return_value = saved_slate(
                current_evidence_version=2
            )
            service.delete_saved_slate_for_owner.side_effect = DatabaseServiceError(
                "down"
            )

        response, _ = self.delete(service_setup=fails)
        body = response.data.decode("utf-8")
        self.assertIn("Inputs changed", body)
        self.assertNotIn("Current for these inputs", body)


class SavedDetailsTests(MemberSaveLifecycleTestCase):
    def details(self, *, saved=_UNSET, query=""):
        with self.signed_in(), self.service() as service:
            self.alignment_service(
                service, saved=saved_slate() if saved is _UNSET else saved
            )
            return self.client.get(f"{SAVED_GET}{query}")

    def test_the_versions_list_names_each_version_by_source_and_save_time(self):
        response = self.details(saved=saved_slate(version_count=2))
        body = response.data.decode("utf-8")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Saved versions", body)
        self.assertIn("Source Version 1", body)
        self.assertEqual(body.count("os-saved-version__link"), 2)

    def test_every_saved_version_is_distinguishable_from_every_other(self):
        """Finding F3. Source version, save minute and qualification count are
        all shared between two saves of the same inputs, so the list rendered
        byte-identical entries and could not do the one job section 7 gives
        it — keep prior saved versions identifiable."""
        body = self.details(saved=saved_slate(version_count=3)).data.decode("utf-8")
        entries = re.findall(
            r'class="os-saved-version__label">(.*?)</span>', body, re.S
        )
        self.assertEqual(len(entries), 3)
        normalized = [" ".join(entry.split()) for entry in entries]
        self.assertEqual(len(set(normalized)), 3, normalized)
        for number in (1, 2, 3):
            self.assertIn(f"Save {number}", normalized)
        # The source version it pinned is still on every entry.
        metas = re.findall(
            r'class="os-saved-version__meta">(.*?)</span>', body, re.S
        )
        self.assertEqual(
            sum(1 for meta in metas if "Source Version 1" in meta), 3, metas
        )

    def test_the_delete_confirmation_counts_every_version_not_just_the_listed_ones(
        self,
    ):
        """Finding F5. The rail lists at most MAX_SAVED_VERSIONS_LISTED, the
        delete removes ALL of them, and nothing caps saving."""
        saved = saved_slate(version_count=50, total_version_count=64)
        body = self.details(saved=saved, query="?confirm=delete").data.decode(
            "utf-8"
        )
        self.assertIn("This removes all 64 saved versions", body)
        self.assertNotIn("This removes all 50 saved versions", body)

    def test_a_truncated_versions_list_says_it_is_truncated(self):
        saved = saved_slate(version_count=50, total_version_count=64)
        body = self.details(saved=saved).data.decode("utf-8")
        self.assertIn("Showing the 50 most recent of", body)
        self.assertIn("64 saved versions", body)

    def test_an_untruncated_versions_list_makes_no_such_claim(self):
        body = self.details(saved=saved_slate(version_count=2)).data.decode("utf-8")
        self.assertNotIn("most recent of", body)
        self.assertIn("This removes all 2 saved versions", self.details(
            saved=saved_slate(version_count=2), query="?confirm=delete"
        ).data.decode("utf-8"))

    def test_it_shows_what_the_saved_result_pinned(self):
        body = self.details().data.decode("utf-8")
        self.assertIn("Systems Engineering Experience Summary", body)
        self.assertIn("Version 1", body)
        self.assertIn("Led systems-integration", body)
        # The member's own response context is part of the snapshot.
        self.assertIn("You told us more", body)
        self.assertIn("I ran the integration reviews", body)

    def test_it_carries_the_same_per_status_accounting_and_no_aggregate(self):
        body = room_markup(self.details().data.decode("utf-8"))
        self.assertIn("os-summary__counts", body)
        for label in ("Supported", "Partially supported", "Not enough information"):
            self.assertIn(label, body)
        self.assertIsNone(re.search(r"\d+\s*%|\d+\s*/\s*\d+", body))

    def test_deleting_asks_first_and_says_exactly_what_goes(self):
        body = self.details(query="?confirm=delete").data.decode("utf-8")
        self.assertIn("Delete this saved slate?", body)
        self.assertIn("It cannot be undone.", body)
        self.assertIn("are not affected", body)
        self.assertIn("/opportunity-slate/delete", body)

    def test_no_saved_slate_returns_to_the_workbench_rather_than_a_tombstone(self):
        response = self.details(saved=None)
        self.assertEqual(response.status_code, 302)
        self.assertIn("step=alignment", response.headers["Location"])

    def test_a_version_key_that_is_not_this_members_is_indistinguishable(self):
        with self.signed_in(), self.service() as service:
            self.alignment_service(service)
            service.get_saved_slate_for_owner.return_value = None
            response = self.client.get(
                f"{SAVED_GET}?version=33333333-3333-3333-3333-333333333333"
            )
        self.assertEqual(response.status_code, 302)


class Os4BoundaryTests(OpportunitySlateTestCase):
    def test_flag_off_is_404_on_every_new_route(self):
        app.config["PEERSLATE_OPPORTUNITY_SLATE_ENABLED"] = False
        with self.signed_in(), self.service():
            self.assertEqual(self.client.get(SAVED_GET).status_code, 404)
            for path in OS4_MEMBER_POSTS:
                with self.subTest(path=path):
                    self.assertEqual(
                        self.client.post(
                            path, headers=SAME_ORIGIN_HEADERS
                        ).status_code,
                        404,
                    )

    def test_the_flag_is_checked_before_identity_is_resolved(self):
        app.config["PEERSLATE_OPPORTUNITY_SLATE_ENABLED"] = False
        with patch("opportunity_slate_routes.get_optional_identity") as identity:
            self.client.get(SAVED_GET)
            for path in OS4_MEMBER_POSTS:
                self.client.post(path, headers=SAME_ORIGIN_HEADERS)
        identity.assert_not_called()

    def test_saving_is_signed_in_only(self):
        """Handoff section 18. There is no account to save into, so these are
        not merely gated — a signed-out caller cannot tell them from a path
        that does not exist."""
        with self.anonymous():
            self.assertEqual(self.client.get(SAVED_GET).status_code, 404)
            for path in OS4_MEMBER_POSTS:
                with self.subTest(path=path):
                    self.assertEqual(
                        self.client.post(
                            path, headers=SAME_ORIGIN_HEADERS
                        ).status_code,
                        404,
                    )

    def test_a_signed_out_call_never_reaches_the_service(self):
        service_mock = MagicMock()
        with self.anonymous(), patch(
            "opportunity_slate_routes.opportunity_slate_service", service_mock
        ):
            self.client.get(SAVED_GET)
            for path in OS4_MEMBER_POSTS:
                self.client.post(path, headers=SAME_ORIGIN_HEADERS)
        self.assertEqual(service_mock.method_calls, [])

    def test_the_new_posts_reject_a_cross_site_request(self):
        with self.signed_in(), self.service():
            for path in OS4_MEMBER_POSTS:
                with self.subTest(path=path):
                    self.assertEqual(self.client.post(path).status_code, 403)
                    self.assertEqual(
                        self.client.post(
                            path, headers={"Origin": "https://evil.example"}
                        ).status_code,
                        403,
                    )

    def test_the_anonymous_transport_has_no_name_for_any_save_action(self):
        """The public session's action allowlist is the structural half of
        "anonymous mode never reaches the database": there is no word it
        accepts that could reach a saved slate."""
        for action in ("save", "reanalyze", "delete", "saved"):
            with self.subTest(action=action):
                self.assertNotIn(action, routes._PUBLIC_ACTIONS)

    def test_no_os4_path_reaches_the_database_from_the_anonymous_side(self):
        service_mock = MagicMock()
        database_mock = MagicMock()
        with self.anonymous(), patch(
            "opportunity_slate_routes.opportunity_slate_service", service_mock
        ), patch(
            "services.opportunity_slate_service.database_service", database_mock
        ):
            self.client.get(SAVED_GET)
            for path in OS4_MEMBER_POSTS:
                self.client.post(path, headers=SAME_ORIGIN_HEADERS)
            for action in ("save", "reanalyze", "delete"):
                self.client.post(
                    PUBLIC_POST,
                    json={"action": action},
                    headers=SAME_ORIGIN_HEADERS,
                )
        self.assertEqual(service_mock.method_calls, [])
        self.assertEqual(database_mock.method_calls, [])


class SavedSlateServiceTests(unittest.TestCase):
    """The persistence seam: what the service sends, and what it refuses."""

    def setUp(self):
        self.database = MagicMock()
        self.service = OpportunitySlateService(database=self.database)

    def test_a_save_sends_no_content_only_a_key_a_fence_and_a_digest(self):
        """The strongest form of the finding-F7 lesson: the procedure builds
        the snapshot from the owner's own rows, so this layer cannot choose
        what a saved result says about the member."""
        self.database.first_row.return_value = {
            "outcome": "success",
            "slate_key": SLATE_KEY,
            "saved_result_key": SAVED_RESULT_KEY,
            "save_version_number": 1,
            "qualification_count": 1,
        }
        self.service.save_slate_for_owner(
            "member-oppslate-1", "idem-1", SET_KEY, SET_TOKEN, "a" * 64
        )
        parameters = dict(self.database.first_row.call_args[0][1])
        self.assertEqual(
            set(parameters),
            {
                "@UserKey",
                "@IdempotencyKey",
                "@RequirementSetKey",
                "@ExpectedRowVersion",
                "@InputFingerprint",
            },
        )
        self.assertEqual(parameters["@UserKey"], "member-oppslate-1")
        self.assertNotIn("@OwnerProfileId", parameters)

    def test_a_malformed_digest_is_refused_before_the_round_trip(self):
        for bad in ("", "not-hex", "A" * 63, None):
            with self.subTest(fingerprint=bad):
                with self.assertRaises(OpportunitySlateServiceError):
                    self.service.save_slate_for_owner(
                        "member-oppslate-1", "idem-1", SET_KEY, SET_TOKEN, bad
                    )
        self.database.first_row.assert_not_called()

    def test_an_existing_outcome_is_a_success_not_a_second_save(self):
        self.database.first_row.return_value = {
            "outcome": "existing",
            "slate_key": SLATE_KEY,
            "saved_result_key": SAVED_RESULT_KEY,
            "save_version_number": 1,
            "qualification_count": 1,
        }
        result = self.service.save_slate_for_owner(
            "member-oppslate-1", "idem-1", SET_KEY, SET_TOKEN, "a" * 64
        )
        self.assertEqual(result["outcome"], "existing")
        self.assertEqual(result["save_version_number"], 1)

    def test_a_changed_outcome_raises_rather_than_reporting_a_save(self):
        self.database.first_row.return_value = {
            "outcome": "changed",
            "slate_key": None,
            "saved_result_key": None,
            "save_version_number": None,
            "qualification_count": None,
        }
        with self.assertRaises(OpportunitySlateServiceError) as caught:
            self.service.save_slate_for_owner(
                "member-oppslate-1", "idem-1", SET_KEY, SET_TOKEN, "a" * 64
            )
        self.assertEqual(caught.exception.code, "changed")

    def test_a_delete_is_fenced_by_the_slates_own_row_version(self):
        self.database.first_row.return_value = {
            "outcome": "success",
            "deleted_result_count": 2,
        }
        result = self.service.delete_saved_slate_for_owner(
            "member-oppslate-1", SLATE_KEY, SLATE_TOKEN
        )
        parameters = dict(self.database.first_row.call_args[0][1])
        self.assertEqual(parameters["@ExpectedRowVersion"], bytes.fromhex(SLATE_TOKEN))
        self.assertEqual(result["deleted_result_count"], 2)

    def test_a_changed_delete_raises_so_the_slate_stays_visibly_saved(self):
        self.database.first_row.return_value = {
            "outcome": "changed",
            "deleted_result_count": None,
        }
        with self.assertRaises(OpportunitySlateServiceError) as caught:
            self.service.delete_saved_slate_for_owner(
                "member-oppslate-1", SLATE_KEY, SLATE_TOKEN
            )
        self.assertEqual(caught.exception.code, "changed")

    def test_no_saved_slate_reads_as_none_rather_than_an_error(self):
        self.database.execute_procedure.return_value = []
        self.assertIsNone(
            self.service.get_saved_slate_for_owner("member-oppslate-1")
        )

    # -- the read seam -----------------------------------------------------

    def saved_result_sets(self, *, evidence_kind="knowledge_item",
                          current_save_version_number=2, listed=2):
        """The five result sets usp_GetOpportunitySavedSlateForOwner returns,
        in its own column names, so a change to either side of the contract
        breaks here rather than in production."""
        now = datetime.now(timezone.utc)
        return [
            [
                {
                    "slate_key": SLATE_KEY,
                    "slate_row_version": bytes.fromhex(SLATE_TOKEN),
                    "current_save_version_number": current_save_version_number,
                    "slate_created_at_utc": now,
                    "saved_result_key": SAVED_RESULT_KEY,
                    "save_version_number": 2,
                    "source_version_number": 1,
                    "requirement_version_number": 1,
                    "saved_analysis_key": ANALYSIS_KEY,
                    "source_text": ROLE_TEXT,
                    "model_name": "claude-sonnet-5",
                    "prompt_contract_version": "os-alignment-v1",
                    "evidence_considered_count": 1,
                    "qualification_count": 1,
                    "input_fingerprint": "a" * 64,
                    "saved_at_utc": now,
                }
            ],
            [
                {
                    "saved_result_key": SAVED_RESULT_KEY,
                    "save_version_number": number,
                    "source_version_number": 1,
                    "requirement_version_number": 1,
                    "qualification_count": 1,
                    "saved_at_utc": now,
                }
                for number in range(listed, 0, -1)
            ],
            [
                {
                    "qualification_id": 1,
                    "ordinal": 1,
                    "statement_class": "required_qualification",
                    "employer_text": "Strong understanding of systems engineering processes.",
                    "derived_status": "supported",
                    "citation_count": 1,
                    "response_kind": None,
                    "response_text": None,
                    "authored_via": None,
                    "connected_evidence_title": None,
                    "connected_evidence_version": None,
                }
            ],
            [
                {
                    "qualification_id": 1,
                    "ordinal": 1,
                    "clause_ordinal": 1,
                    "covered_text": "Systems engineering",
                    "evidence_kind": evidence_kind,
                    "evidence_key": EVIDENCE_KEY,
                    "evidence_version": 1,
                    "evidence_title": "Systems Engineering Experience Summary",
                    "excerpt": "Led systems-integration work.",
                }
            ],
            [
                {
                    "evidence_kind": evidence_kind,
                    "evidence_key": EVIDENCE_KEY,
                    "pinned_version": 1,
                    "current_version": 1,
                }
            ],
        ]

    def test_the_read_carries_the_slates_true_version_total(self):
        """Finding F5. `versions` is capped for the rail; the delete
        confirmation needs the number the member actually has."""
        self.database.execute_procedure.return_value = self.saved_result_sets(
            current_save_version_number=64, listed=2
        )
        saved = self.service.get_saved_slate_for_owner("member-oppslate-1")
        self.assertEqual(saved.total_version_count, 64)
        self.assertEqual(len(saved.versions), 2)

    def test_an_evidence_kind_this_revision_cannot_price_is_refused(self):
        """Finding F6. The currency join resolves knowledge items only, so a
        Moment citation would read permanently stale with nothing able to
        clear it. Refused loudly instead — unreachable today, and a tripwire
        for the slice that adds Moment grounding."""
        self.database.execute_procedure.return_value = self.saved_result_sets(
            evidence_kind="moment"
        )
        with self.assertRaises(OpportunitySlateServiceError) as caught:
            self.service.get_saved_slate_for_owner("member-oppslate-1")
        self.assertEqual(caught.exception.code, "invalid")

    def test_a_knowledge_item_citation_reads_normally(self):
        self.database.execute_procedure.return_value = self.saved_result_sets()
        saved = self.service.get_saved_slate_for_owner("member-oppslate-1")
        self.assertEqual(saved.evidence_currency, ((EVIDENCE_KEY, 1, 1),))


if __name__ == "__main__":
    unittest.main()
