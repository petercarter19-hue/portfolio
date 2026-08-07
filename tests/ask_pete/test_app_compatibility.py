import os
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch


os.environ.setdefault("ANTHROPIC_API_KEY", "ask-pete-app-test-key")

import app as app_module
from services.ask_pete.errors import AskPeteRequestError, AskPeteResponseError


SAME_ORIGIN_HEADERS = {
    "Origin": "http://localhost",
    "Sec-Fetch-Site": "same-origin",
}


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
