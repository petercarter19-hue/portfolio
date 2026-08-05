"""Contract tests for Opportunity Slate — PS-OPPSLATE-001, slices OS-1
and OS-2.

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
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app import app, limiter
from services.database_service import DatabaseServiceError
from services.opportunity_slate_service import (
    MAX_SOURCE_TEXT_UNITS,
    OpportunitySlateServiceError,
    RequirementSetView,
    RequirementStatementView,
    WorkingSourceView,
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
        """The patched service module, with the two slice OS-2 lookups
        defaulted to "nothing has run yet".

        An unconfigured MagicMock attribute is TRUTHY, so without these two
        defaults every test that does not mention AI would render the room as
        though a wording review and a requirement proposal already existed —
        and a screen whose whole job is to distinguish "not checked" from
        "checked, nothing found" would be asserted in the wrong state without
        anything failing. None is also what the real service returns before
        either step has run, so this is the honest default rather than a
        convenience.
        """
        with patch("opportunity_slate_routes.opportunity_slate_service") as service:
            service.get_source_review_for_owner.return_value = None
            service.get_requirements_for_owner.return_value = None
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


if __name__ == "__main__":
    unittest.main()
