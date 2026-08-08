"""The two shapes a real provider reply arrived in, and where the line is.

The first real-provider run failed 502 on every grounded question. Two causes,
both in the reply rather than in the answer's substance:

1. The model wrapped its object in a ```json fence, so json.loads refused it.
2. The reply stopped at the 1,600-token output ceiling mid-claims-array, and
   the truncated text then failed as unparseable JSON — reporting the symptom
   and hiding the cause.

Fixing those loosens transport formatting only. These tests hold that line:
exactly one well-formed outer fence is unwrapped, a truncated reply is named
as truncated, and everything else is still refused without being repaired,
mined, or guessed at.
"""

import json
from pathlib import Path
from types import SimpleNamespace
from typing import get_args
from unittest import TestCase

from anthropic.types import Message

from services.ai_foundation import AIRequest, Audience, Purpose, SourceVersion
from services.ai_foundation.errors import AnswerContractError
from services.ask_pete.provider import (
    DEFAULT_MAXIMUM_OUTPUT_TOKENS,
    MAXIMUM_PROVIDER_CALLS,
    TRUNCATED_STOP_REASON,
    AnthropicGroundedProvider,
)


ROOT = Path(__file__).resolve().parents[2]
PROMPT_PATH = ROOT / "prompts" / "ask_pete" / "grounded_public_v1.md"

# The ceiling the first real-provider run truncated at.
OBSERVED_TRUNCATING_CEILING = 1_600


class StopReasonMessages:
    """A messages resource that reports a stop reason, as the SDK does."""

    def __init__(self, text: str, *, stop_reason: str = "end_turn") -> None:
        self.text = text
        self.stop_reason = stop_reason
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            content=[SimpleNamespace(text=self.text)],
            stop_reason=self.stop_reason,
        )


def public_request() -> AIRequest:
    return AIRequest(
        request_id="shape-request-1",
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


def acceptable_payload() -> dict:
    return {
        "state": "not_established",
        "summary": "That is not established in Pete's approved public information.",
        "claims": [],
        "follow_up_questions": [],
        "handoff": None,
    }


def provider_for(messages: StopReasonMessages) -> AnthropicGroundedProvider:
    return AnthropicGroundedProvider(
        SimpleNamespace(messages=messages),
        model_name="configured-model",
        subject_display_name="Pete Carter",
        prompt_path=PROMPT_PATH,
    )


class TruncationIsNamedTruncationTests(TestCase):
    def test_a_truncated_reply_fails_as_truncation_within_the_call_bound(self) -> None:
        # The captured live shape: a fenced object cut off mid-array.
        truncated = '```json\n{\n  "state": "supported",\n  "claims": [\n    {\n'
        messages = StopReasonMessages(truncated, stop_reason="max_tokens")

        with self.assertRaisesRegex(
            AnswerContractError,
            "truncated before completion",
        ):
            provider_for(messages).answer(public_request(), (public_source(),))

        # Truncation is model behavior, so it gets the one corrective attempt
        # every contract refusal gets — the correction asks for an object
        # compact enough to finish. This double truncates again, so the second
        # failure is final and the category is still the honest one. The bound
        # is what matters here: two paid calls, never a third.
        self.assertEqual(len(messages.calls), MAXIMUM_PROVIDER_CALLS)

    def test_the_stop_reason_is_read_before_anything_tries_to_parse(self) -> None:
        # Even when the text would parse, a reply the provider reports as cut
        # off is refused: the ordering is what turns a misleading JSON error
        # into an honest one, so it is pinned rather than left incidental.
        messages = StopReasonMessages(
            json.dumps(acceptable_payload()),
            stop_reason="max_tokens",
        )

        with self.assertRaisesRegex(
            AnswerContractError,
            "truncated before completion",
        ):
            provider_for(messages).answer(public_request(), (public_source(),))

    def test_an_ordinary_stop_reason_still_answers(self) -> None:
        for stop_reason in ("end_turn", "stop_sequence", None):
            with self.subTest(stop_reason=stop_reason):
                messages = StopReasonMessages(
                    json.dumps(acceptable_payload()),
                    stop_reason=stop_reason,
                )

                answer = provider_for(messages).answer(
                    public_request(),
                    (public_source(),),
                )

                self.assertEqual(answer["state"], "not_established")


class OutputCeilingHeadroomTests(TestCase):
    def test_the_default_ceiling_clears_the_one_that_truncated(self) -> None:
        self.assertEqual(DEFAULT_MAXIMUM_OUTPUT_TOKENS, 3_000)
        self.assertGreater(DEFAULT_MAXIMUM_OUTPUT_TOKENS, OBSERVED_TRUNCATING_CEILING)

    def test_the_call_carries_the_default_ceiling(self) -> None:
        messages = StopReasonMessages(json.dumps(acceptable_payload()))

        provider_for(messages).answer(public_request(), (public_source(),))

        self.assertEqual(
            messages.calls[0]["max_tokens"],
            DEFAULT_MAXIMUM_OUTPUT_TOKENS,
        )


class SingleFenceToleranceTests(TestCase):
    def test_the_tolerated_shapes_are_a_bare_object_or_one_outer_fence(self) -> None:
        body = json.dumps(acceptable_payload())
        for description, text in (
            ("bare object", body),
            ("json fence", f"```json\n{body}\n```"),
            ("bare fence", f"```\n{body}\n```"),
            ("uppercase info string", f"```JSON\n{body}\n```"),
            ("surrounding whitespace", f"\n\n```json\n{body}\n```\n\n"),
            ("indented interior", f"```json\n  {body}\n```"),
        ):
            with self.subTest(description):
                messages = StopReasonMessages(text)

                answer = provider_for(messages).answer(
                    public_request(),
                    (public_source(),),
                )

                self.assertEqual(answer["state"], "not_established")

    def test_an_object_embedded_in_prose_is_never_extracted(self) -> None:
        # A regression guard against a future "helpful" repair step. Unwrapping
        # a fence is removing packaging; finding an object inside commentary is
        # guessing which part of an off-contract reply was meant as the answer.
        body = json.dumps(acceptable_payload())
        for description, text in (
            ("prose around a bare object", f"Sure! Here it is: {body} Hope that helps."),
            ("prose before a fence", f"Here is the JSON:\n\n```json\n{body}\n```"),
            ("commentary after a fence", f"```json\n{body}\n```\n\nLet me know if that helps."),
            ("second fenced block", f"```json\n{body}\n```\n\n```json\n{body}\n```"),
            ("unclosed fence", f"```json\n{body}"),
            ("unopened fence", f"{body}\n```"),
            ("unrecognized info string", f"```python\n{body}\n```"),
            ("closing fence not on its own line", f"```json\n{body}```"),
        ):
            with self.subTest(description):
                messages = StopReasonMessages(text)

                with self.assertRaisesRegex(AnswerContractError, "not strict JSON"):
                    provider_for(messages).answer(public_request(), (public_source(),))

    def test_a_fenced_interior_gets_no_other_leniency(self) -> None:
        # The fence is the only thing removed. A malformed or non-object
        # interior fails exactly as it would have unfenced.
        for description, interior, expected in (
            ("trailing comma", '{"state": "supported",}', "not strict JSON"),
            ("single quotes", "{'state': 'supported'}", "not strict JSON"),
            ("array, not an object", '[{"state": "supported"}]', "must be an object"),
            ("empty interior", "", "not strict JSON"),
        ):
            with self.subTest(description):
                messages = StopReasonMessages(f"```json\n{interior}\n```")

                with self.assertRaisesRegex(AnswerContractError, expected):
                    provider_for(messages).answer(public_request(), (public_source(),))


class InstalledSdkContractTests(TestCase):
    """Pin the SDK mechanic the truncation check depends on.

    If an upgrade moves or renames the stop reason, or drops the value that
    means "cut off at the ceiling", the check would silently stop firing and
    truncation would go back to reporting itself as bad JSON. This fails first.
    """

    def test_the_response_reports_a_top_level_stop_reason(self) -> None:
        self.assertIn("stop_reason", Message.model_fields)

    def test_max_tokens_is_still_a_stop_reason_the_sdk_can_report(self) -> None:
        annotation = Message.model_fields["stop_reason"].annotation
        reported: set[object] = set()
        for member in get_args(annotation):
            reported.update(get_args(member))

        self.assertIn(TRUNCATED_STOP_REASON, reported)
