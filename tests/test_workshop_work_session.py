"""Contract tests for Work on Something — PS-WORKSHOP-001 W2a.

Controlling brief: docs/initiatives/PS-SLATE-STUDIO-IA-001/
22_W2_IMPLEMENTATION_BRIEF.md. Covers the opening (four doors), the
focused-question session round trip, the honest "AI review arrives next"
holding state, "Start fresh", the shared byte budget with
services/workshop_demo_library.py, and owner isolation. Every behavioral
test uses a generic fixture member key, never a Pete-specific identifier.
"""

import random
import re
import string
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app import app, limiter
from identity import AuthenticationRequired
from services import workshop_demo_library as wdl
from services import workshop_work_session as wws
from services.database_service import DatabaseServiceError
from services.knowledge_service import KnowledgeItemListResult, KnowledgeServiceError


SAME_ORIGIN_HEADERS = {"Origin": "http://localhost", "Sec-Fetch-Site": "same-origin"}

CONFIRMED_ROW = {
    "item_key": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
    "status": "confirmed",
    "classification": "work",
    "title": "Led systems work end to end",
    "current_version": 1,
    "confirmed_version": 1,
    "confirmed_at": "2026-01-01T00:00:00Z",
    "archived_at": None,
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z",
    "version_token": "0000000000000001",
    "body_format": "plain",
    "authored_via": "typed",
}


def member(name, user_key):
    return SimpleNamespace(display_name=name, user_key=user_key)


def _find_all(pattern, body):
    return re.findall(pattern, body)


class WorkOnSomethingTestCase(unittest.TestCase):
    """Shared setUp: both flags on, limiter disabled, fresh client."""

    def setUp(self):
        self.client = app.test_client()
        self.original_flag = app.config.get("PEERSLATE_WORKSHOP_ENABLED")
        self.original_session_flag = app.config.get("PEERSLATE_WORKSHOP_SESSION_ENABLED")
        self.original_dev_identity_flag = app.config.get("PEERSLATE_ALLOW_DEV_IDENTITY")
        app.config["PEERSLATE_WORKSHOP_ENABLED"] = True
        app.config["PEERSLATE_WORKSHOP_SESSION_ENABLED"] = True
        self._limiter_enabled = limiter.enabled
        limiter.enabled = False

    def tearDown(self):
        limiter.enabled = self._limiter_enabled
        app.config["PEERSLATE_WORKSHOP_ENABLED"] = self.original_flag
        app.config["PEERSLATE_WORKSHOP_SESSION_ENABLED"] = self.original_session_flag
        app.config["PEERSLATE_ALLOW_DEV_IDENTITY"] = self.original_dev_identity_flag

    def _start(self, **form):
        return self.client.post(
            "/app/workshop/work/start", data=form, headers=SAME_ORIGIN_HEADERS
        )

    def _update(self, **form):
        return self.client.post(
            "/app/workshop/work/session", data=form, headers=SAME_ORIGIN_HEADERS
        )


# ---------------------------------------------------------------------------
# Flag-off: every /work/* route 404s neutrally, before any identity
# resolution, and the mode tab stays "Coming later" everywhere.
# ---------------------------------------------------------------------------


class FlagOffTests(WorkOnSomethingTestCase):
    def test_all_work_routes_404_with_both_flags_off(self):
        app.config["PEERSLATE_WORKSHOP_ENABLED"] = False
        app.config["PEERSLATE_WORKSHOP_SESSION_ENABLED"] = False

        self.assertEqual(self.client.get("/app/workshop/work").status_code, 404)
        self.assertEqual(self.client.get("/app/workshop/work/session").status_code, 404)
        self.assertEqual(
            self.client.get("/app/workshop/work/session/review").status_code, 404
        )
        self.assertEqual(self._start(door="s").status_code, 404)
        self.assertEqual(self._update(answer="x").status_code, 404)

    def test_work_routes_404_with_outer_flag_on_but_session_flag_off(self):
        app.config["PEERSLATE_WORKSHOP_ENABLED"] = True
        app.config["PEERSLATE_WORKSHOP_SESSION_ENABLED"] = False

        self.assertEqual(self.client.get("/app/workshop/work").status_code, 404)
        self.assertEqual(self._start(door="s").status_code, 404)

    def test_tab_stays_coming_later_with_session_flag_off(self):
        app.config["PEERSLATE_WORKSHOP_ENABLED"] = True
        app.config["PEERSLATE_WORKSHOP_SESSION_ENABLED"] = False

        body = self.client.get("/app/workshop").data.decode("utf-8")
        self.assertIn(
            '<span class="wk-pill wk-pill--coming-later">Coming later</span>', body
        )
        self.assertNotIn('href="/app/workshop/work"', body)

    def test_tab_becomes_a_real_link_with_session_flag_on(self):
        body = self.client.get("/app/workshop").data.decode("utf-8")
        self.assertIn('href="/app/workshop/work"', body)
        self.assertNotIn("Coming later", body)

    def test_zero_identity_resolution_when_flags_are_off(self):
        app.config["PEERSLATE_WORKSHOP_ENABLED"] = False
        app.config["PEERSLATE_WORKSHOP_SESSION_ENABLED"] = False

        def boom(*_a, **_k):
            raise AssertionError("identity must never be resolved when flags are off")

        with patch("workshop_work_routes.get_current_identity", side_effect=boom):
            self.client.get("/app/workshop/work")
            self.client.get("/app/workshop/work/session")
            self.client.get("/app/workshop/work/session/review")
            self._start(door="s")
            self._update(answer="x")
            # Also outer-on/session-off.
            app.config["PEERSLATE_WORKSHOP_ENABLED"] = True
            self.client.get("/app/workshop/work")

    def test_reset_is_independent_of_the_session_sub_flag(self):
        """The brief: Start fresh "works regardless of the session
        sub-flag" — only the outer PEERSLATE_WORKSHOP_ENABLED flag gates
        it."""
        app.config["PEERSLATE_WORKSHOP_ENABLED"] = True
        app.config["PEERSLATE_WORKSHOP_SESSION_ENABLED"] = False

        self.assertEqual(self.client.get("/app/workshop/preview/reset").status_code, 200)

        app.config["PEERSLATE_WORKSHOP_ENABLED"] = False
        self.assertEqual(self.client.get("/app/workshop/preview/reset").status_code, 404)


# ---------------------------------------------------------------------------
# Opening
# ---------------------------------------------------------------------------


class OpeningRenderTests(WorkOnSomethingTestCase):
    def test_opening_renders_all_four_doors_and_composer(self):
        body = self.client.get("/app/workshop/work").data.decode("utf-8")
        self.assertIn("Continue where I left off", body)
        self.assertIn("I brought something", body)
        self.assertIn("Work on something", body)
        self.assertIn("Give me a spark", body)
        self.assertIn('name="thought"', body)
        # Two doors are honestly inert in this slice.
        self.assertIn("Not available yet", body)

    def test_fresh_anonymous_visitor_sees_the_librarys_two_base_unfinished_items(self):
        body = self.client.get("/app/workshop/work").data.decode("utf-8")
        self.assertIn("wk-door--continue-active", body)
        self.assertIn("Something about the 2023 reorganization", body)
        self.assertIn("Learning to say no to good projects", body)

    def test_ai_unavailable_test_seam_renders_r07_composition(self):
        app.config["PEERSLATE_ALLOW_DEV_IDENTITY"] = True
        body = self.client.get(
            "/app/workshop/work?_dev_ai_state=unavailable"
        ).data.decode("utf-8")
        self.assertIn("Spark is unavailable right now", body)
        self.assertIn("No suggestion is shown without a grounded result", body)
        # Honest: no AI concept ever claimed to have run.
        self.assertNotIn("AI reviewed", body)
        self.assertNotIn("AI proposal", body)

    def test_ai_unavailable_seam_inert_without_dev_identity_flag(self):
        app.config["PEERSLATE_ALLOW_DEV_IDENTITY"] = False
        body = self.client.get(
            "/app/workshop/work?_dev_ai_state=unavailable"
        ).data.decode("utf-8")
        self.assertNotIn("Spark is unavailable right now", body)

    def test_no_ai_concept_anywhere_on_the_opening(self):
        body = self.client.get("/app/workshop/work").data.decode("utf-8")
        self.assertNotIn("AI review", body)
        self.assertNotIn("AI proposal", body)


# ---------------------------------------------------------------------------
# Session round trip
# ---------------------------------------------------------------------------


class SessionRoundTripTests(WorkOnSomethingTestCase):
    def test_start_then_session_preserves_the_seed_thought(self):
        response = self._start(door=wws.DOOR_SOMETHING, thought="I led a big migration.")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/app/workshop/work/session", response.headers["Location"])

        body = self.client.get("/app/workshop/work/session").data.decode("utf-8")
        self.assertIn("I led a big migration.", body)

    def test_question_selection_is_deterministic_per_door(self):
        first_index, first_text = wws.question_for_door(wws.DOOR_SOMETHING)
        second_index, second_text = wws.question_for_door(wws.DOOR_SOMETHING)
        self.assertEqual(first_index, second_index)
        self.assertEqual(first_text, second_text)

        self._start(door=wws.DOOR_SOMETHING, thought="thought one")
        body1 = self.client.get("/app/workshop/work/session").data.decode("utf-8")

        client2 = app.test_client()
        client2.post(
            "/app/workshop/work/start",
            data={"door": wws.DOOR_SOMETHING, "thought": "thought two"},
            headers=SAME_ORIGIN_HEADERS,
        )
        body2 = client2.get("/app/workshop/work/session").data.decode("utf-8")

        m1 = re.search(r'wk-session-question">(.*?)</h1>', body1)
        m2 = re.search(r'wk-session-question">(.*?)</h1>', body2)
        self.assertIsNotNone(m1)
        self.assertIsNotNone(m2)
        self.assertEqual(m1.group(1), m2.group(1))

    def test_unavailable_doors_cannot_start_a_session(self):
        response = self._start(door=wws.DOOR_BROUGHT)
        self.assertEqual(response.status_code, 400)
        body = response.data.decode("utf-8")
        self.assertIn("not available yet", body)

        response = self._start(door=wws.DOOR_SPARK)
        self.assertEqual(response.status_code, 400)

    def test_resuming_an_unfinished_item_seeds_its_current_wording(self):
        unfinished = next(
            item for item in wdl.BASE_ITEMS if item["status"] == "unfinished"
        )
        response = self._start(door=wws.DOOR_CONTINUE, resume_item=unfinished["item_key"])
        self.assertEqual(response.status_code, 302)

        body = self.client.get("/app/workshop/work/session").data.decode("utf-8")
        self.assertIn(unfinished["wording"][:30], body)

    def test_resuming_a_foreign_or_unknown_item_key_is_a_neutral_redirect(self):
        response = self._start(
            door=wws.DOOR_CONTINUE,
            resume_item="99999999-9999-9999-9999-999999999999",
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/app/workshop/work", response.headers["Location"])
        self.assertNotIn("/session", response.headers["Location"])

    def test_answer_cap_is_enforced_with_an_honest_message_and_no_lost_text(self):
        self._start(door=wws.DOOR_SOMETHING, thought="seed")
        over_cap = "x" * (wws.MAX_ANSWER_UNITS + 1)

        response = self._update(answer=over_cap, wk_action="save_unfinished")

        self.assertEqual(response.status_code, 400)
        body = response.data.decode("utf-8")
        self.assertIn("limited to 1000 characters", body)
        self.assertIn(over_cap, body)

    def test_stop_for_now_clears_the_session_without_saving(self):
        self._start(door=wws.DOOR_SOMETHING, thought="seed")
        response = self._update(answer="not saved", wk_action="stop")
        self.assertEqual(response.status_code, 302)
        self.assertIn("session-stopped", response.headers["Location"])

        # The session is gone; re-visiting the session screen bounces to
        # the opening, and nothing was added to the library.
        follow = self.client.get("/app/workshop/work/session")
        self.assertEqual(follow.status_code, 302)
        opening_body = self.client.get("/app/workshop").data.decode("utf-8")
        self.assertNotIn("not saved", opening_body)


# ---------------------------------------------------------------------------
# Use as context
# ---------------------------------------------------------------------------


class UseAsContextTests(WorkOnSomethingTestCase):
    def test_context_ids_are_validated_against_the_visible_set(self):
        self._start(door=wws.DOOR_SOMETHING, thought="seed")
        body = self.client.get("/app/workshop/work/session").data.decode("utf-8")
        visible_ids = _find_all(r'name="context"\s+value="([^"]+)"', body)
        self.assertGreater(len(visible_ids), 0)

        foreign_id = "12345678-1234-1234-1234-123456789012"
        self.assertNotIn(foreign_id, visible_ids)

        response = self._update(
            answer="answer text",
            context=[visible_ids[0], foreign_id],
            wk_action="review",
        )
        self.assertEqual(response.status_code, 302)

        state = None
        with self.client.session_transaction() as sess:
            raw = sess.get(wdl.SESSION_KEY)
            state = raw.get("w") if isinstance(raw, dict) else None
        self.assertIsNotNone(state)
        # Only bit 0 (the first visible item) may be set; the foreign id
        # contributes nothing, and no bit beyond the visible set's length
        # is ever set from this submission.
        context_mask = state[3]
        self.assertEqual(context_mask & 1, 1)
        self.assertEqual(context_mask & ~((1 << len(visible_ids)) - 1), 0)

    def test_selection_survives_a_round_trip_through_the_holding_state(self):
        self._start(door=wws.DOOR_SOMETHING, thought="seed")
        body = self.client.get("/app/workshop/work/session").data.decode("utf-8")
        visible_ids = _find_all(r'name="context"\s+value="([^"]+)"', body)

        self._update(answer="answer text", context=[visible_ids[0]], wk_action="review")
        self.client.get("/app/workshop/work/session/review")

        return_body = self.client.get("/app/workshop/work/session").data.decode("utf-8")
        self.assertRegex(
            return_body,
            r'value="' + re.escape(visible_ids[0]) + r'"\s+checked',
        )


# ---------------------------------------------------------------------------
# Holding state
# ---------------------------------------------------------------------------


class HoldingStateTests(WorkOnSomethingTestCase):
    def test_holding_state_never_claims_ai_ran(self):
        self._start(door=wws.DOOR_SOMETHING, thought="seed")
        self._update(answer="my shared answer", wk_action="review")

        body = self.client.get("/app/workshop/work/session/review").data.decode("utf-8")
        self.assertIn("AI review step is coming next", body)
        self.assertIn("my shared answer", body)
        self.assertNotIn("AI reviewed", body)
        self.assertNotIn("interpretation", body)
        self.assertNotIn("strong[", body)

    def test_holding_state_without_an_active_session_redirects_to_opening(self):
        response = self.client.get("/app/workshop/work/session/review")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/app/workshop/work", response.headers["Location"])


# ---------------------------------------------------------------------------
# Save unfinished — anonymous (session library) and member (real store, mocked)
# ---------------------------------------------------------------------------


class SaveUnfinishedTests(WorkOnSomethingTestCase):
    def test_anonymous_save_unfinished_lands_in_the_session_library(self):
        self._start(door=wws.DOOR_SOMETHING, thought="seed")
        response = self._update(
            answer="A concrete answer worth keeping.", wk_action="save_unfinished"
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("unfinished-preview", response.headers["Location"])

        opening_body = self.client.get(response.headers["Location"]).data.decode("utf-8")
        # Body text is never in the list view (title-only list read, by
        # design — see workshop_routes.py/_filter_library_rows).
        self.assertNotIn("A concrete answer worth keeping.", opening_body)
        self.assertIn("Kept as unfinished in this preview session", opening_body)
        self.assertIn("wk-door--continue-active", opening_body)

        # Confirm it actually landed as a session item (title-only list
        # read carries no body text, but the item must be present, titled
        # from the focused question, and marked unfinished).
        with self.client.session_transaction() as sess:
            delta = wdl.read_session_delta(sess)
        self.assertEqual(len(delta["a"]), 1)
        added_title = delta["a"][0][1]
        self.assertIn("did that mattered", added_title)
        self.assertEqual(delta["a"][0][4], "f")  # status code "f" == unfinished

    def test_anonymous_save_unfinished_clears_the_active_session(self):
        self._start(door=wws.DOOR_SOMETHING, thought="seed")
        self._update(answer="answer", wk_action="save_unfinished")

        with self.client.session_transaction() as sess:
            raw = sess.get(wdl.SESSION_KEY)
        self.assertNotIn("w", raw or {})

    def test_member_save_unfinished_uses_the_real_owner_scoped_save_path(self):
        test_member = member("Test Member", "member-w2a-1")
        with patch(
            "workshop_work_routes.get_current_identity", return_value=test_member
        ), patch(
            "workshop_work_routes.knowledge_service.list_knowledge_items_for_owner",
            return_value=KnowledgeItemListResult(items=[CONFIRMED_ROW], total_count=1),
        ), patch(
            "workshop_work_routes.knowledge_service.save_knowledge_item_for_owner"
        ) as mock_save:
            mock_save.return_value = {
                "item_key": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                "saved": True,
            }
            self._start(door=wws.DOOR_SOMETHING, thought="member seed")
            response = self._update(answer="member answer", wk_action="save_unfinished")

        self.assertEqual(response.status_code, 302)
        self.assertIn("changed=unfinished", response.headers["Location"])
        self.assertNotIn("preview", response.headers["Location"])
        mock_save.assert_called_once()
        args, _kwargs = mock_save.call_args
        self.assertEqual(args[0], "member-w2a-1")
        fields = args[2]
        self.assertEqual(fields["approved_wording"], "member answer")
        self.assertIs(fields["confirm"], False)

    def test_member_save_unfinished_preserves_text_on_a_database_failure(self):
        test_member = member("Test Member", "member-w2a-2")
        with patch(
            "workshop_work_routes.get_current_identity", return_value=test_member
        ), patch(
            "workshop_work_routes.knowledge_service.list_knowledge_items_for_owner",
            return_value=KnowledgeItemListResult(items=[], total_count=0),
        ), patch(
            "workshop_work_routes.knowledge_service.save_knowledge_item_for_owner",
            side_effect=DatabaseServiceError("db down"),
        ):
            self._start(door=wws.DOOR_SOMETHING, thought="member seed")
            response = self._update(
                answer="do not lose this text", wk_action="save_unfinished"
            )

        self.assertEqual(response.status_code, 400)
        self.assertIn("do not lose this text", response.data.decode("utf-8"))

    def test_no_for_owner_call_is_reachable_anonymously(self):
        def boom(*_a, **_k):
            raise AssertionError("a *_for_owner call must never happen anonymously")

        with patch(
            "workshop_work_routes.knowledge_service.list_knowledge_items_for_owner",
            side_effect=boom,
        ), patch(
            "workshop_work_routes.knowledge_service.get_knowledge_item_for_owner",
            side_effect=boom,
        ), patch(
            "workshop_work_routes.knowledge_service.save_knowledge_item_for_owner",
            side_effect=boom,
        ):
            self.client.get("/app/workshop/work")
            self._start(door=wws.DOOR_SOMETHING, thought="anon")
            self.client.get("/app/workshop/work/session")
            self._update(answer="anon answer", wk_action="review")
            self.client.get("/app/workshop/work/session/review")
            self._update(answer="anon answer 2", wk_action="save_unfinished")
            self.client.get("/app/workshop/preview/reset")
            self.client.post(
                "/app/workshop/preview/reset",
                data={"confirm_reset": "reset"},
                headers=SAME_ORIGIN_HEADERS,
            )


# ---------------------------------------------------------------------------
# Start fresh
# ---------------------------------------------------------------------------


class StartFreshTests(WorkOnSomethingTestCase):
    def test_reset_requires_confirmation(self):
        response = self.client.post(
            "/app/workshop/preview/reset", data={}, headers=SAME_ORIGIN_HEADERS
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("error=confirm-reset", response.headers["Location"])

    def test_reset_requires_same_origin(self):
        response = self.client.post("/app/workshop/preview/reset", data={"confirm_reset": "reset"})
        self.assertEqual(response.status_code, 403)

    def test_reset_clears_both_the_library_delta_and_the_session_state(self):
        wdl_client = self.client
        wdl_client.post(
            "/app/workshop/items",
            data={
                "title": "My own item",
                "wording": "Something I added.",
                "classification": "work",
                "save_action": "confirm",
            },
            headers=SAME_ORIGIN_HEADERS,
        )
        self._start(door=wws.DOOR_SOMETHING, thought="in-progress session")

        with self.client.session_transaction() as sess:
            raw = sess.get(wdl.SESSION_KEY)
        self.assertTrue(raw.get("a"))
        self.assertIn("w", raw)

        response = self.client.post(
            "/app/workshop/preview/reset",
            data={"confirm_reset": "reset"},
            headers=SAME_ORIGIN_HEADERS,
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("reset-preview", response.headers["Location"])

        with self.client.session_transaction() as sess:
            self.assertNotIn(wdl.SESSION_KEY, sess)

        # Library-after-reset is pristine: 17 base items, no visitor deltas.
        library_body = self.client.get("/app/workshop").data.decode("utf-8")
        self.assertNotIn("My own item", library_body)
        self.assertIn(">17 items<", library_body)
        session_body = self.client.get("/app/workshop/work/session")
        self.assertEqual(session_body.status_code, 302)  # no active session anymore

    def test_reset_works_with_the_session_sub_flag_off(self):
        app.config["PEERSLATE_WORKSHOP_SESSION_ENABLED"] = False
        response = self.client.post(
            "/app/workshop/preview/reset",
            data={"confirm_reset": "reset"},
            headers=SAME_ORIGIN_HEADERS,
        )
        self.assertEqual(response.status_code, 302)


class StartFreshRateLimitTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.original_flag = app.config.get("PEERSLATE_WORKSHOP_ENABLED")
        app.config["PEERSLATE_WORKSHOP_ENABLED"] = True
        self._limiter_enabled = limiter.enabled
        limiter.enabled = True
        limiter.reset()

    def tearDown(self):
        limiter.reset()
        limiter.enabled = self._limiter_enabled
        app.config["PEERSLATE_WORKSHOP_ENABLED"] = self.original_flag

    def test_reset_returns_429_after_the_per_minute_limit(self):
        statuses = [
            self.client.post(
                "/app/workshop/preview/reset",
                data={"confirm_reset": "reset"},
                headers=SAME_ORIGIN_HEADERS,
            ).status_code
            for _ in range(9)
        ]
        self.assertIn(429, statuses)
        self.assertEqual(statuses[-1], 429)

    def test_start_session_returns_429_after_the_per_minute_limit(self):
        statuses = [
            self.client.post(
                "/app/workshop/work/start",
                data={"door": wws.DOOR_SOMETHING, "thought": "x"},
                headers=SAME_ORIGIN_HEADERS,
            ).status_code
            for _ in range(13)
        ]
        self.assertIn(429, statuses)


class SameOriginTests(WorkOnSomethingTestCase):
    def test_start_rejects_cross_site_requests(self):
        response = self.client.post(
            "/app/workshop/work/start", data={"door": wws.DOOR_SOMETHING}
        )
        self.assertEqual(response.status_code, 403)

    def test_update_session_rejects_cross_site_requests(self):
        self._start(door=wws.DOOR_SOMETHING, thought="seed")
        response = self.client.post(
            "/app/workshop/work/session", data={"answer": "x"}
        )
        self.assertEqual(response.status_code, 403)


# ---------------------------------------------------------------------------
# Shared byte budget with services/workshop_demo_library.py
# ---------------------------------------------------------------------------


class SessionByteBudgetTests(WorkOnSomethingTestCase):
    """Combined workshop_preview cookie (library delta + Work on Something
    session state) stays within the shared MAX_SESSION_BYTES ceiling,
    matching the brief's "measure in a test" instruction.

    Measured (real HTTP flow, see the docstring note below):
    - Realistic worst case (2 moderate confirmed items + a full 1000-unit
      answer, full context selection): ~1.7KB.
    - TRUE adversarial worst case (the library's own full 4-item/400-char
      cap AND a full 1000-unit answer AND a full context selection, all at
      once): ~3.06KB — still fits under the ~3.07KB (3072 byte) shared
      ceiling, with roughly 14 bytes to spare. The session legitimately
      starts; nothing is rejected.
    - A genuinely-impossible combination (one more maxed library item than
      the cap actually allows, simulated directly) is used to prove the
      SESSION_FULL_MESSAGE guard actually engages and fails closed —
      rather than ever writing a cookie that could exceed one browser's
      ~4KB per-cookie limit — when the true worst case is pushed past it.

    Deliberately drives every write through REAL HTTP requests
    (self.client.post/get), not direct service-function calls inside
    ``session_transaction()``. ``services/workshop_demo_library.py`` and
    ``services/workshop_work_session.py``'s own byte-budget guards
    (_would_fit) read ``flask.current_app``, which is only bound during a
    real request/app context — Flask's test client keeps one live for the
    full duration of a dispatched request (exactly how production behaves),
    but a bare ``with client.session_transaction() as sess: wws.start_session(sess, ...)``
    call has NO app context at all in this Flask version, silently
    diverting the guard to a cruder raw-JSON size estimate instead of
    measuring the real signed cookie. Routing every write through the
    actual endpoints, as a real browser would, sidesteps that pitfall
    entirely and gives an honest measurement of what a visitor's browser
    actually receives.
    """

    def setUp(self):
        super().setUp()
        self.rng = random.Random(20260802)
        self.alphabet = string.ascii_letters + string.digits + " "

    def _measure_cookie_bytes(self):
        with self.client.session_transaction() as sess:
            serializer = app.session_interface.get_signing_serializer(app)
            token = serializer.dumps(dict(sess))
        return len(token.encode("utf-8")) if isinstance(token, str) else len(token)

    def _add_library_item(self, *, title, wording):
        return self.client.post(
            "/app/workshop/items",
            data={
                "title": title,
                "wording": wording,
                "classification": "work",
                "save_action": "confirm",
            },
            headers=SAME_ORIGIN_HEADERS,
        )

    def test_realistic_combined_worst_case_fits_the_shared_ceiling(self):
        for i in range(2):
            wording = "".join(self.rng.choices(self.alphabet, k=200))
            response = self._add_library_item(title=f"A real demo item {i}", wording=wording)
            self.assertEqual(response.status_code, 200)

        answer = "".join(self.rng.choices(self.alphabet, k=wws.MAX_ANSWER_UNITS))
        start_response = self._start(door=wws.DOOR_SOMETHING, thought=answer)
        self.assertEqual(start_response.status_code, 302)

        session_body = self.client.get("/app/workshop/work/session").data.decode("utf-8")
        context_ids = _find_all(r'name="context"\s+value="([^"]+)"', session_body)

        # "review" persists the full answer + full context selection without
        # clearing the session (unlike save_unfinished/stop), so the
        # measurement below reflects the session at its fullest.
        review_response = self._update(
            answer=answer, context=context_ids, wk_action="review"
        )
        self.assertEqual(review_response.status_code, 302)

        size = self._measure_cookie_bytes()
        self.assertLess(
            size, wdl.MAX_SESSION_BYTES, f"combined session payload was {size} bytes"
        )

    def test_true_adversarial_worst_case_still_fits_the_shared_ceiling(self):
        """The library's OWN full 4-item/400-char cap, combined with a
        full-length Work on Something session (1000-unit answer, full
        context selection) — the actual worst case a real visitor could
        reach through the product's own caps. It fits comfortably; the
        session legitimately starts rather than being refused."""
        for i in range(wdl.MAX_ADDED_ITEMS):
            title = (f"Sample demo title number {i} " * 6)[:160]
            wording = "".join(
                self.rng.choices(self.alphabet, k=wdl.MAX_PREVIEW_WORDING_UNITS)
            )
            response = self._add_library_item(title=title, wording=wording)
            self.assertEqual(response.status_code, 200)

        answer = "".join(self.rng.choices(self.alphabet, k=wws.MAX_ANSWER_UNITS))
        start_response = self._start(door=wws.DOOR_SOMETHING, thought=answer)
        self.assertEqual(start_response.status_code, 302)

        session_body = self.client.get("/app/workshop/work/session").data.decode("utf-8")
        context_ids = _find_all(r'name="context"\s+value="([^"]+)"', session_body)
        review_response = self._update(
            answer=answer, context=context_ids, wk_action="review"
        )
        self.assertEqual(review_response.status_code, 302)

        size = self._measure_cookie_bytes()
        self.assertLess(
            size, wdl.MAX_SESSION_BYTES, f"true worst-case payload was {size} bytes"
        )
        self.assertLess(
            size,
            4096,
            f"session payload was {size} bytes — must stay under one browser cookie's ~4KB limit",
        )

    def test_guard_fails_closed_with_an_honest_message_when_truly_over_budget(self):
        """A combination that genuinely exceeds the shared ceiling — beyond
        what the product's own caps let a real visitor reach (the prior
        test proves the actual worst case still fits) — is refused with
        SESSION_FULL_MESSAGE, never silently written. Constructed directly
        with one extra synthetic library item beyond MAX_ADDED_ITEMS
        (impossible via the real, capped form fields) specifically to push
        the payload past MAX_SESSION_BYTES and exercise the guard's refusal
        path. Run inside a real app context (app.test_request_context) so
        _would_fit's current_app-based measurement behaves exactly as it
        does for a genuine dispatched request (see class docstring) rather
        than silently degrading to the cruder fallback estimate.
        """
        with self.client.session_transaction() as sess:
            with app.test_request_context():
                # One more item than the real cap allows, purely to
                # guarantee this exceeds the shared ceiling — proving the
                # guard itself, not the product's own (already-proven-
                # sufficient) caps.
                for i in range(wdl.MAX_ADDED_ITEMS + 1):
                    title = (f"Sample demo title number {i} " * 6)[:160]
                    wording = "".join(
                        self.rng.choices(self.alphabet, k=wdl.MAX_PREVIEW_WORDING_UNITS)
                    )
                    delta = wdl.read_session_delta(sess)
                    delta["a"].append(
                        [f"synthetic-{i}", title, wording, "w", "c"]
                    )
                    wdl.write_session_delta(sess, delta)

                answer = "".join(
                    self.rng.choices(self.alphabet, k=wws.MAX_ANSWER_UNITS)
                )
                ok, error, state = wws.start_session(
                    sess, door=wws.DOOR_SOMETHING, answer=answer
                )

        self.assertFalse(ok)
        self.assertEqual(error, wws.SESSION_FULL_MESSAGE)
        self.assertIsNone(state)
        # Never partially written: no "w" key landed in the session.
        with self.client.session_transaction() as sess:
            raw = sess.get(wdl.SESSION_KEY)
        self.assertNotIn("w", raw or {})


if __name__ == "__main__":
    unittest.main()
