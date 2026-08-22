"""Byte-level parity replay for PS-INTERVIEW-AI-EXTRACT-001.

Each fixture under fixtures/parity/ was recorded from the untouched legacy
Interview routes at source checkpoint 73c4e63d. This suite replays every
fixture against the extracted runtime and asserts, byte for byte: the
provider-call count and order, the exact explicit keyword set, model and
max_tokens, the exact UTF-8 system and user-message bytes, the response
body, the HTTP status, and the content type. It also asserts the two
accepted operational deltas stay outside the member-visible surface: the
telemetry append never changes a response, and no database write happens
on a pre-provider refusal.
"""

import base64
import json
import os
import unittest
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")

import anthropic
import httpx
from itsdangerous import URLSafeTimedSerializer

import app as app_module
from services import database_service as database_service_module
from services import interview_ai

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "parity"

REGISTRY = json.loads(
    (ROOT / "prompts" / "interview" / "control" / "registry.json").read_text(
        encoding="utf-8"
    )
)
RELEASE_ID = REGISTRY["active_release_set"]["interview_release_set_id"]

# The recorder's deterministic environment, reproduced without depending on
# process-level environment ordering: the signing serializer is patched
# directly and the itsdangerous clock is frozen to the recorded instant.
FIXED_SIGNING_KEY = "parity-oracle-interview-context-signing-key"
CONTEXT_SALT = "peerslate-interview-model-answer-v1"

# Expected server_call rows per fixture (across all steps): the disclosed
# operational delta, asserted so the boundary stays exactly where frozen.
EXPECTED_ROWS = {
    "coach_success_minimal": 1,
    "coach_success_with_context_and_suggestions": 1,
    "coach_success_markdown_fence": 1,
    "coach_success_family_situational": 1,
    "coach_invalid_json_502": 1,
    "coach_missing_field_502": 1,
    "coach_unauthorized_evidence_502": 1,
    "coach_provider_timeout_500": 1,
    "coach_refusal_not_json_415": 0,
    "coach_refusal_missing_answer_400": 0,
    "coach_refusal_unknown_profile_404": 0,
    "coach_refusal_long_context_400": 0,
    "revision_success_full": 1,
    "revision_success_no_selected_evidence": 1,
    "revision_refusal_unknown_evidence_403": 0,
    "revision_invalid_reply_502": 1,
    "revision_provider_rate_limited_500": 1,
    "nudge_success_two_hints": 1,
    "nudge_success_three_hints_video": 1,
    "nudge_invalid_single_hint_502": 1,
    "nudge_refusal_missing_question_400": 0,
    "grounded_success": 1,
    "grounded_insufficient_200": 1,
    "grounded_no_citation_502": 1,
    "grounded_provider_overloaded_500": 1,
    "generic_success": 1,
    "generic_cites_evidence_502": 1,
    "compare_success": 3,
    "compare_grounded_fails_short_circuit_502": 2,
    "compare_generic_fails_502": 3,
    "followup_member_history_success": 2,
    "followup_context_mismatch_400": 1,
    # Correction C10: follow-up and authenticated-context coverage.
    "followup_best_practice_success": 2,
    "followup_compare_success": 6,
    "auth_owner_review_success": 1,
    "auth_member_review_success_empty_evidence": 1,
    "auth_review_marker_gate_400": 0,
    "auth_member_grounded_insufficient": 1,
    "auth_followup_refused_400": 0,
    "auth_nudge_success": 1,
}


def make_provider_exception(spec):
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    if spec == "timeout":
        return anthropic.APITimeoutError(request=request)
    if spec == "connection":
        return anthropic.APIConnectionError(
            message="Connection error.", request=request
        )
    status_by_spec = {
        "rate_limited": 429,
        "overloaded": 529,
        "server_error": 500,
        "bad_request": 400,
    }
    status = status_by_spec[spec]
    response = httpx.Response(status, request=request, content=b"{}")
    classes = {429: anthropic.RateLimitError, 400: anthropic.BadRequestError}
    cls = classes.get(status, anthropic.InternalServerError)
    return cls("provider error", response=response, body=None)


class CaptureFake:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        if not self.replies:
            raise AssertionError("provider called more times than scripted")
        reply = self.replies.pop(0)
        if "raise" in reply:
            raise make_provider_exception(reply["raise"])

        class _Block:
            def __init__(self, text):
                self.type = "text"
                self.text = text

        class _Usage:
            def __init__(self, input_tokens, output_tokens):
                self.input_tokens = input_tokens
                self.output_tokens = output_tokens

        class _Response:
            pass

        response = _Response()
        response.content = [_Block(reply["text"])]
        response.stop_reason = reply.get("stop_reason", "end_turn")
        usage = reply.get("usage")
        if usage is not None:
            response.usage = _Usage(
                usage["input_tokens"], usage["output_tokens"]
            )
        return response


class ParityReplayTests(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        cls.fixtures = {}
        for path in sorted(FIXTURE_DIR.glob("*.json")):
            cls.fixtures[path.stem] = json.loads(
                path.read_text(encoding="utf-8")
            )

    def test_every_fixture_has_an_expected_row_count(self):
        self.assertEqual(set(self.fixtures), set(EXPECTED_ROWS))

    def test_parity_replay(self):
        for name, fixture in self.fixtures.items():
            with self.subTest(fixture=name):
                self._replay(name, fixture)

    def _replay(self, name, fixture):
        appended = []

        def record_append(procedure_name, parameters=None):
            self.assertEqual(
                procedure_name, "usp_AppendInterviewAIServerCall"
            )
            appended.append(dict(parameters))
            return []

        serializer = URLSafeTimedSerializer(
            FIXED_SIGNING_KEY, salt=CONTEXT_SALT
        )
        limiter_was_enabled = app_module.limiter.enabled
        app_module.limiter.enabled = False
        previous_config = app_module.app.config.get(
            interview_ai.ACTIVE_RELEASE_CONFIG_KEY
        )
        app_module.app.config[interview_ai.ACTIVE_RELEASE_CONFIG_KEY] = (
            RELEASE_ID
        )
        interview_ai.reset_resolution_cache()
        # B3 second round: requests never initialize; the suite performs
        # the process-boot act explicitly after its simulated restart.
        interview_ai.boot.initialize(RELEASE_ID)
        try:
            context = {}
            for step in fixture["steps"]:
                fake = CaptureFake(step["provider_replies"])
                payload = step["request"]["json"]
                if payload is not None and payload.get("context_token") == (
                    "__STEP1_CONTEXT_TOKEN__"
                ):
                    payload = dict(payload)
                    payload["context_token"] = context["context_token"]
                with ExitStack() as stack:
                    stack.enter_context(patch.object(
                        app_module.client.messages, "create", new=fake,
                    ))
                    stack.enter_context(patch.object(
                        database_service_module.database_service,
                        "execute_procedure",
                        new=record_append,
                    ))
                    stack.enter_context(patch.object(
                        app_module, "interview_context_serializer",
                        new=serializer,
                    ))
                    stack.enter_context(patch(
                        "itsdangerous.timed.time.time",
                        return_value=fixture["clock"],
                    ))
                    auth = fixture.get("auth")
                    if auth is not None:
                        identity = SimpleNamespace(**auth["identity"])
                        stack.enter_context(patch.object(
                            app_module, "get_current_identity",
                            new=lambda: identity,
                        ))
                        stack.enter_context(patch.object(
                            app_module, "is_owner",
                            new=lambda candidate: auth["owner"],
                        ))
                        stack.enter_context(patch.dict(
                            app_module.app.config,
                            {"PEERSLATE_INTERVIEW_STUDIO_AUTHENTICATED": True},
                        ))
                    test_client = app_module.app.test_client()
                    kwargs = {"base_url": "http://localhost"}
                    if payload is not None:
                        kwargs["json"] = payload
                    if step["request"].get("data") is not None:
                        kwargs["data"] = step["request"]["data"]
                    response = test_client.post(
                        step["request"]["path"], **kwargs
                    )

                expected = step["response"]
                self.assertEqual(response.status_code, expected["status"])
                self.assertEqual(
                    response.headers.get("Content-Type"),
                    expected["content_type"],
                )
                expected_body = base64.b64decode(expected["body_b64"])
                self.assertEqual(response.get_data(), expected_body)

                recorded_calls = step["provider_calls"]
                self.assertEqual(len(fake.calls), len(recorded_calls))
                self.assertEqual(
                    len(fake.replies), step["unconsumed_replies"]
                )
                for made, recorded in zip(fake.calls, recorded_calls):
                    self.assertEqual(
                        sorted(made.keys()), recorded["kwargs_keys"]
                    )
                    self.assertEqual(made["model"], recorded["model"])
                    self.assertEqual(
                        made["max_tokens"], recorded["max_tokens"]
                    )
                    self.assertEqual(
                        made["system"].encode("utf-8"),
                        base64.b64decode(recorded["system_b64"]),
                    )
                    self.assertEqual(
                        len(made["messages"]), len(recorded["messages"])
                    )
                    for made_message, recorded_message in zip(
                        made["messages"], recorded["messages"]
                    ):
                        self.assertEqual(
                            made_message["role"], recorded_message["role"]
                        )
                        self.assertEqual(
                            made_message["content"].encode("utf-8"),
                            base64.b64decode(
                                recorded_message["content_b64"]
                            ),
                        )

                if response.status_code == 200:
                    parsed = json.loads(response.get_data())
                    if isinstance(parsed, dict) and "contextToken" in parsed:
                        context["context_token"] = parsed["contextToken"]

            self.assertEqual(
                len(appended), EXPECTED_ROWS[name],
                "unexpected server_call row count for %s" % name,
            )
        finally:
            app_module.limiter.enabled = limiter_was_enabled
            app_module.app.config[interview_ai.ACTIVE_RELEASE_CONFIG_KEY] = (
                previous_config
            )
            interview_ai.reset_resolution_cache()


if __name__ == "__main__":
    unittest.main()
