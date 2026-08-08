"""The paid Ask Pete call must give up before the browser does.

static/js/chatbot.js aborts its fetch after 45 s. Anything the server is
still doing after that is invisible to the visitor and still billable, so
the provider call carries its own bound and a timeout degrades into the
honest "unavailable" answer rather than a retry storm.
"""

import inspect
import json
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase

import anthropic
import httpx

from services.ai_foundation import AIRequest, Audience, Purpose, SourceVersion
from services.ai_foundation.errors import ProviderUnavailableError
from services.ask_pete.manifest import load_public_source_catalog
from services.ask_pete.provider import (
    PROVIDER_MAX_RETRIES,
    PROVIDER_TIMEOUT_SECONDS,
    AnthropicGroundedProvider,
)
from services.ask_pete.service import AskPeteService


ROOT = Path(__file__).resolve().parents[2]
PROMPT_PATH = ROOT / "prompts" / "ask_pete" / "grounded_public_v1.md"

# static/js/chatbot.js: setTimeout(controller.abort, 45000).
BROWSER_ABORT_SECONDS = 45.0


def timeout_error() -> anthropic.APITimeoutError:
    return anthropic.APITimeoutError(
        request=httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    )


class RecordingMessages:
    """A messages resource that records every create call it receives."""

    def __init__(self, text: str | None = None, error: Exception | None = None) -> None:
        self.text = text
        self.error = error
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return SimpleNamespace(content=[SimpleNamespace(text=self.text)])


class OptionsAwareClient:
    """A client shaped like the SDK's: with_options returns a bounded copy."""

    def __init__(self, messages: RecordingMessages) -> None:
        self.messages = RecordingMessages(text="unbounded copy must not be used")
        self._bounded_messages = messages
        self.with_options_calls: list[dict] = []

    def with_options(self, **kwargs):
        self.with_options_calls.append(kwargs)
        return SimpleNamespace(messages=self._bounded_messages)


def public_request() -> AIRequest:
    return AIRequest(
        request_id="timeout-request-1",
        product="ask_pete",
        purpose=Purpose.PUBLIC_PROFILE_ANSWER,
        audience=Audience.PUBLIC,
        subject_key="petec",
        question="Tell me about Pete.",
    )


def public_source() -> SourceVersion:
    return SourceVersion.approved(
        source_version_key="source:v1",
        source_key="source",
        version=1,
        subject_key="petec",
        title="Approved source",
        content="Approved public evidence text.",
        allowed_audiences=frozenset({Audience.PUBLIC}),
        allowed_purposes=frozenset({Purpose.PUBLIC_PROFILE_ANSWER}),
    )


def provider_for(client) -> AnthropicGroundedProvider:
    return AnthropicGroundedProvider(
        client,
        model_name="configured-model",
        subject_display_name="Pete Carter",
        prompt_path=PROMPT_PATH,
    )


def not_established_payload() -> str:
    return json.dumps(
        {
            "state": "not_established",
            "summary": "That is not established in Pete's approved public information.",
            "claims": [],
            "follow_up_questions": [],
            "handoff": None,
        }
    )


class ProviderCallBoundsTests(TestCase):
    def test_the_server_bound_is_shorter_than_the_browser_abort(self) -> None:
        self.assertLess(PROVIDER_TIMEOUT_SECONDS, BROWSER_ABORT_SECONDS)
        self.assertGreater(PROVIDER_TIMEOUT_SECONDS, 0)
        self.assertEqual(PROVIDER_MAX_RETRIES, 0)

    def test_create_carries_the_bounded_timeout(self) -> None:
        messages = RecordingMessages(not_established_payload())

        provider_for(SimpleNamespace(messages=messages)).answer(
            public_request(),
            (public_source(),),
        )

        self.assertEqual(len(messages.calls), 1)
        self.assertEqual(messages.calls[0]["timeout"], PROVIDER_TIMEOUT_SECONDS)

    def test_client_options_bound_the_timeout_and_disable_sdk_retries(self) -> None:
        bounded = RecordingMessages(not_established_payload())
        client = OptionsAwareClient(bounded)

        provider_for(client).answer(public_request(), (public_source(),))

        self.assertEqual(
            client.with_options_calls,
            [
                {
                    "timeout": PROVIDER_TIMEOUT_SECONDS,
                    "max_retries": PROVIDER_MAX_RETRIES,
                }
            ],
        )
        # The call went to the bounded copy, not to the unbounded client.
        self.assertEqual(len(bounded.calls), 1)
        self.assertEqual(client.messages.calls, [])

    def test_a_client_without_options_support_still_gets_the_timeout(self) -> None:
        messages = RecordingMessages(not_established_payload())
        client = SimpleNamespace(messages=messages)

        self.assertFalse(hasattr(client, "with_options"))
        provider_for(client).answer(public_request(), (public_source(),))

        self.assertEqual(messages.calls[0]["timeout"], PROVIDER_TIMEOUT_SECONDS)

    def test_a_timeout_is_classified_without_leaking_transport_detail(self) -> None:
        messages = RecordingMessages(error=timeout_error())

        with self.assertRaisesRegex(
            ProviderUnavailableError,
            "configured provider call failed",
        ) as raised:
            provider_for(SimpleNamespace(messages=messages)).answer(
                public_request(),
                (public_source(),),
            )

        self.assertNotIn("api.anthropic.com", str(raised.exception))
        # One attempt only: the adapter never retries a timed-out call itself.
        self.assertEqual(len(messages.calls), 1)


class ProviderTimeoutDegradationTests(TestCase):
    def test_a_timed_out_call_degrades_to_the_honest_unavailable_answer(self) -> None:
        messages = RecordingMessages(error=timeout_error())
        catalog = load_public_source_catalog(
            manifest_path=ROOT / "data" / "ai_sources" / "ask_pete_public_v1.json",
            resume_path=ROOT / "static" / "data" / "resume_data.json",
        )
        service = AskPeteService(
            catalog=catalog,
            provider=provider_for(SimpleNamespace(messages=messages)),
        )

        result = service.answer(
            "Tell me about Pete's leadership.",
            request_id="request-timeout-1",
        )

        self.assertEqual(result.payload["state"], "unavailable")
        self.assertEqual(result.payload["claims"], [])
        self.assertEqual(result.payload["support_label"], "Temporarily unavailable")
        # Legacy clients read data.response; an unavailable answer still has one.
        self.assertTrue(result.payload["response"].strip())
        self.assertEqual(result.diagnostic.outcome, "degraded")
        self.assertEqual(result.diagnostic.error_category, "provider_unavailable")
        self.assertEqual(len(messages.calls), 1)


class InstalledSdkContractTests(TestCase):
    """Pin the SDK mechanics the bound depends on.

    If an upgrade moves `timeout` off `messages.create` or changes
    `with_options`, the bound would silently stop applying. This fails first.
    """

    def test_create_accepts_a_per_request_timeout_but_not_max_retries(self) -> None:
        parameters = inspect.signature(
            anthropic.resources.messages.Messages.create
        ).parameters

        self.assertIn("timeout", parameters)
        self.assertNotIn("max_retries", parameters)

    def test_with_options_returns_a_bounded_copy_and_leaves_the_client_alone(
        self,
    ) -> None:
        client = anthropic.Anthropic(api_key="ask-pete-provider-bounds-test-key")
        original_retries = client.max_retries

        bounded = client.with_options(
            timeout=PROVIDER_TIMEOUT_SECONDS,
            max_retries=PROVIDER_MAX_RETRIES,
        )

        self.assertIsNot(bounded, client)
        self.assertEqual(bounded.timeout, PROVIDER_TIMEOUT_SECONDS)
        self.assertEqual(bounded.max_retries, PROVIDER_MAX_RETRIES)
        self.assertEqual(client.max_retries, original_retries)
        # The copy reuses the connection pool, so bounding costs no sockets.
        self.assertIs(bounded._client, client._client)

    def test_the_sdk_would_retry_a_timeout_if_it_were_not_bounded(self) -> None:
        client = anthropic.Anthropic(api_key="ask-pete-provider-bounds-test-key")

        should_retry, _response = client._should_retry_exception(timeout_error())

        self.assertTrue(should_retry)
        self.assertGreater(client.max_retries, PROVIDER_MAX_RETRIES)
