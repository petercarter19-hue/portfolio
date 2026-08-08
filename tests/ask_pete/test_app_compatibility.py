import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch


os.environ.setdefault("ANTHROPIC_API_KEY", "ask-pete-app-test-key")

import app as app_module
from services.ask_pete.errors import AskPeteRequestError, AskPeteResponseError
from services.ask_pete.provider import PROVIDER_TIMEOUT_SECONDS


SAME_ORIGIN_HEADERS = {
    "Origin": "http://localhost",
    "Sec-Fetch-Site": "same-origin",
}

# app.py: @limiter.limit('10 per minute') on /api/chat.
CHAT_REQUESTS_PER_MINUTE = 10


class RecordingMessages:
    """Stand in for the Anthropic messages resource and record every call."""

    def __init__(self, text: str) -> None:
        self.text = text
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(content=[SimpleNamespace(text=self.text)])


def modest_general_answer() -> str:
    """A correctly grounded answer that no strict quality contract accepts."""

    return json.dumps(
        {
            "state": "not_established",
            "summary": (
                "Pete's approved public information does not establish a full "
                "recruiter brief."
            ),
            "claims": [
                {
                    "claim_id": "boundary-1",
                    "text": "A complete recruiter brief is not publicly established.",
                    "kind": "boundary",
                    "state": "not_established",
                    "citations": [],
                    "limitation": (
                        "No approved public record covers this at the depth a "
                        "recruiter brief needs."
                    ),
                }
            ],
            "follow_up_questions": [],
            "handoff": None,
        }
    )


class AskPeteAppCompatibilityTests(TestCase):
    def setUp(self) -> None:
        self.original = {
            "TESTING": app_module.app.config.get("TESTING"),
            "RATELIMIT_ENABLED": app_module.app.config.get("RATELIMIT_ENABLED"),
            "PEERSLATE_ASK_PETE_GROUNDED_ENABLED": app_module.app.config.get(
                "PEERSLATE_ASK_PETE_GROUNDED_ENABLED"
            ),
        }
        self.limiter_enabled = app_module.limiter.enabled
        app_module.limiter.enabled = False
        app_module.limiter.reset()
        app_module.app.config.update(TESTING=True, RATELIMIT_ENABLED=False)
        self.client = app_module.app.test_client()

    def tearDown(self) -> None:
        app_module.limiter.reset()
        app_module.limiter.enabled = self.limiter_enabled
        app_module.app.config.update(**self.original)

    def test_grounded_path_is_default_off(self) -> None:
        source = (Path(__file__).resolve().parents[2] / "app.py").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "os.environ.get('PEERSLATE_ASK_PETE_GROUNDED_ENABLED', 'false')",
            source,
        )

    @patch("app.answer_public_question")
    @patch("app.client.messages.create")
    def test_disabled_flag_preserves_the_legacy_api_response(self, create, grounded) -> None:
        app_module.app.config["PEERSLATE_ASK_PETE_GROUNDED_ENABLED"] = False
        create.return_value.content = [SimpleNamespace(text="Legacy answer.")]

        response = self.client.post(
            "/api/chat",
            json={"message": "Tell me about Pete."},
            headers=SAME_ORIGIN_HEADERS,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"response": "Legacy answer."})
        create.assert_called_once()
        grounded.assert_not_called()

    @patch("app.answer_public_question")
    @patch("app.client.messages.create")
    def test_enabled_flag_uses_only_the_grounded_seam(self, create, grounded) -> None:
        app_module.app.config["PEERSLATE_ASK_PETE_GROUNDED_ENABLED"] = True
        payload = {
            "schema_version": "ask-pete-public-answer.v1",
            "state": "supported",
            "response": "Grounded answer.",
            "claims": [],
        }
        grounded.return_value = SimpleNamespace(payload=payload)

        response = self.client.post(
            "/api/chat",
            json={
                "message": "Show evidence of Pete's MBSE work.",
                "action": "evidence_finder",
                "context_key": "skill:mbse",
            },
            headers=SAME_ORIGIN_HEADERS,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), payload)
        create.assert_not_called()
        call = grounded.call_args.kwargs
        self.assertEqual(call["question"], "Show evidence of Pete's MBSE work.")
        self.assertEqual(call["requested_action"], "evidence_finder")
        self.assertEqual(call["context_key"], "skill:mbse")
        self.assertIs(call["client"], app_module.client)
        self.assertTrue(call["root_path"].is_dir())

    def test_flag_on_answers_a_legacy_recruiter_question_instead_of_502ing(self) -> None:
        """The whole grounded path, driven the way chatbot.js drives it.

        static/js/chatbot.js posts {"message": ...} with no action and reads
        data.response. Recruiter wording used to escalate that request into
        the flagship brief contract, and a modest answer then failed the
        request as a 502. Nothing is patched below the app seam except the
        model itself, so classification, the quality gate, serialization and
        the provider bound all run for real.
        """
        app_module.app.config["PEERSLATE_ASK_PETE_GROUNDED_ENABLED"] = True
        messages = RecordingMessages(modest_general_answer())

        with patch.object(app_module, "client", SimpleNamespace(messages=messages)):
            response = self.client.post(
                "/api/chat",
                json={"message": "Give me Pete's 60-second recruiter brief."},
                headers=SAME_ORIGIN_HEADERS,
            )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["purpose"], "public_profile_answer")
        self.assertEqual(payload["state"], "not_established")
        # Legacy clients render data.response and nothing else.
        self.assertTrue(payload["response"].strip())
        self.assertEqual(payload["response"], payload["summary"])
        self.assertEqual(len(messages.calls), 1)
        self.assertEqual(messages.calls[0]["timeout"], PROVIDER_TIMEOUT_SECONDS)

    @patch("app.answer_public_question")
    def test_invalid_public_context_returns_a_bounded_client_error(self, grounded) -> None:
        app_module.app.config["PEERSLATE_ASK_PETE_GROUNDED_ENABLED"] = True
        grounded.side_effect = AskPeteRequestError("private context details")

        response = self.client.post(
            "/api/chat",
            json={"message": "Tell me more.", "context_key": "private:record"},
            headers=SAME_ORIGIN_HEADERS,
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.get_json(),
            {"error": "Ask Pete could not use that question context."},
        )
        self.assertNotIn("private context details", response.get_data(as_text=True))

    @patch("app.answer_public_question")
    def test_grounding_failure_is_not_returned_as_a_plausible_answer(self, grounded) -> None:
        app_module.app.config["PEERSLATE_ASK_PETE_GROUNDED_ENABLED"] = True
        grounded.side_effect = AskPeteResponseError("citation mismatch details")

        response = self.client.post(
            "/api/chat",
            json={"message": "Tell me about Pete."},
            headers=SAME_ORIGIN_HEADERS,
        )

        self.assertEqual(response.status_code, 502)
        self.assertEqual(
            response.get_json(),
            {"error": "Ask Pete could not verify a grounded answer. Please try again."},
        )
        self.assertNotIn("citation mismatch details", response.get_data(as_text=True))

    @patch("app.answer_public_question")
    def test_cross_site_request_is_still_refused_before_grounded_work(self, grounded) -> None:
        app_module.app.config["PEERSLATE_ASK_PETE_GROUNDED_ENABLED"] = True

        response = self.client.post(
            "/api/chat",
            json={"message": "Tell me about Pete."},
            headers={"Sec-Fetch-Site": "cross-site"},
        )

        self.assertEqual(response.status_code, 403)
        grounded.assert_not_called()

    @patch("app.answer_public_question")
    @patch("app.client.messages.create")
    def test_malformed_or_non_text_messages_are_rejected_before_any_provider_call(
        self, create, grounded
    ) -> None:
        app_module.app.config["PEERSLATE_ASK_PETE_GROUNDED_ENABLED"] = True

        for payload in ([], {"message": None}, {"message": 42}, {"text": "missing"}):
            response = self.client.post(
                "/api/chat",
                json=payload,
                headers=SAME_ORIGIN_HEADERS,
            )
            self.assertEqual(response.status_code, 400)

        grounded.assert_not_called()
        create.assert_not_called()

    @patch("app.answer_public_question")
    @patch("app.client.messages.create")
    def test_non_json_and_malformed_json_bodies_are_json_400_before_provider_work(
        self, create, grounded
    ) -> None:
        app_module.app.config["PEERSLATE_ASK_PETE_GROUNDED_ENABLED"] = True

        for body, content_type in (
            (b"plain text", "text/plain"),
            (b'{"message":', "application/json"),
            (b'"a scalar"', "application/json"),
        ):
            response = self.client.post(
                "/api/chat",
                data=body,
                content_type=content_type,
                headers=SAME_ORIGIN_HEADERS,
            )
            self.assertEqual(response.status_code, 400)
            self.assertTrue(response.is_json)
            self.assertEqual(
                response.get_json(),
                {"error": "Request body must be a JSON object."},
            )

        grounded.assert_not_called()
        create.assert_not_called()


class AskPeteChatRateLimitTests(TestCase):
    """The 10-per-minute limit is the ceiling on anonymous AI spend.

    Every other test in this file disables the limiter so it cannot interfere.
    This one enables it, because an unverified spend ceiling is not a ceiling.
    """

    def setUp(self) -> None:
        self.original = {
            "TESTING": app_module.app.config.get("TESTING"),
            "RATELIMIT_ENABLED": app_module.app.config.get("RATELIMIT_ENABLED"),
            "PEERSLATE_ASK_PETE_GROUNDED_ENABLED": app_module.app.config.get(
                "PEERSLATE_ASK_PETE_GROUNDED_ENABLED"
            ),
        }
        self.limiter_enabled = app_module.limiter.enabled
        app_module.limiter.enabled = True
        # The default storage is in-process and shared, so start from zero.
        app_module.limiter.reset()
        app_module.app.config.update(
            TESTING=True,
            RATELIMIT_ENABLED=True,
            PEERSLATE_ASK_PETE_GROUNDED_ENABLED=True,
        )
        self.client = app_module.app.test_client()

    def tearDown(self) -> None:
        app_module.limiter.reset()
        app_module.limiter.enabled = self.limiter_enabled
        app_module.app.config.update(**self.original)

    def post_chat(self, message: str = "Tell me about Pete."):
        return self.client.post(
            "/api/chat",
            json={"message": message},
            headers=SAME_ORIGIN_HEADERS,
        )

    @patch("app.answer_public_question")
    @patch("app.client.messages.create")
    def test_one_client_is_refused_past_the_limit_without_further_provider_work(
        self, create, grounded
    ) -> None:
        grounded.return_value = SimpleNamespace(
            payload={
                "schema_version": "ask-pete-public-answer.v1",
                "state": "supported",
                "response": "Grounded answer.",
                "claims": [],
            }
        )

        statuses = [
            self.post_chat().status_code
            for _ in range(CHAT_REQUESTS_PER_MINUTE + 1)
        ]

        self.assertEqual(
            statuses[:CHAT_REQUESTS_PER_MINUTE],
            [200] * CHAT_REQUESTS_PER_MINUTE,
        )
        self.assertEqual(statuses[CHAT_REQUESTS_PER_MINUTE], 429)
        # The refused request costs nothing: no grounded work, no legacy call.
        self.assertEqual(grounded.call_count, CHAT_REQUESTS_PER_MINUTE)
        create.assert_not_called()

    @patch("app.answer_public_question")
    @patch("app.client.messages.create")
    def test_the_refused_request_is_json_with_a_retry_after_hint(
        self, create, grounded
    ) -> None:
        """The refusal contract PS-ASK-PETE-AI-RELEASE-001 put in place.

        PS-ASK-PETE-AI-READINESS-002 characterized the previous behavior: with
        no 429 error handler registered, a refused request to this otherwise
        JSON route returned Flask-Limiter's HTML page and no Retry-After, so a
        JSON client got a body it could not parse and no idea when to retry.
        That package recorded it as an open gap and said to update this test
        when an app.py handler landed. It has, so these assertions pin the new
        contract: a JSON error sentence, and a wait the caller can act on.
        """
        grounded.return_value = SimpleNamespace(payload={"response": "Answer."})
        question = "A distinctive visitor question that must not be echoed back."

        for _ in range(CHAT_REQUESTS_PER_MINUTE):
            self.post_chat(question)
        response = self.post_chat(question)

        self.assertEqual(response.status_code, 429)
        self.assertTrue(response.is_json)
        self.assertEqual(
            response.get_json(),
            {"error": "Too many requests. Please wait a moment and try again."},
        )

        retry_after = response.headers.get("Retry-After")
        self.assertIsNotNone(retry_after, "a refused caller is not told when to wait")
        # The route's window is a minute, so the reset can never be further
        # away than that (the extension's reset_at rounds one second up).
        self.assertTrue(
            1 <= int(retry_after) <= 61,
            f"Retry-After {retry_after!r} is not a usable wait for a per-minute limit",
        )

        body = response.get_data(as_text=True)
        self.assertNotIn(question, body)
        # The exception description carries the limit string; it stays internal.
        self.assertNotIn("per 1 minute", body)
        create.assert_not_called()
