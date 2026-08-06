from copy import deepcopy
from unittest import TestCase

from services.ai_foundation import (
    AIFoundationGateway,
    AIRequest,
    AnswerState,
    Audience,
    Purpose,
    SourceVersion,
    parse_grounded_answer,
)
from services.ai_foundation.errors import AnswerContractError


def source() -> SourceVersion:
    return SourceVersion.approved(
        source_version_key="role-air-force:v3",
        source_key="role-air-force",
        version=3,
        subject_key="pete",
        title="Air Force engineering leadership",
        content="Pete led a cross-functional engineering organization.",
        allowed_audiences=frozenset({Audience.PUBLIC}),
        allowed_purposes=frozenset({Purpose.RECRUITER_BRIEF}),
    )


def request() -> AIRequest:
    return AIRequest(
        request_id="request-codec-1",
        product="ask_pete",
        purpose=Purpose.RECRUITER_BRIEF,
        audience=Audience.PUBLIC,
        subject_key="pete",
        question="Give me Pete's recruiter brief.",
    )


def payload() -> dict:
    item = source()
    excerpt = "cross-functional engineering"
    start = item.content.index(excerpt)
    return {
        "answer_id": "answer-codec-1",
        "state": "supported",
        "summary": "Pete has documented engineering leadership.",
        "claims": [
            {
                "claim_id": "claim-1",
                "text": "Pete led cross-functional engineering work.",
                "kind": "evidence",
                "state": "supported",
                "citations": [
                    {
                        "claim_id": "claim-1",
                        "source_version_key": item.source_version_key,
                        "start": start,
                        "end": start + len(excerpt),
                        "excerpt": excerpt,
                    }
                ],
                "limitation": None,
            }
        ],
        "follow_up_questions": [
            "How did Pete align the cross-functional team?"
        ],
        "handoff": None,
        "model_name": "provider-model",
        "prompt_contract_version": "ask-pete-recruiter-brief-v1",
    }


class MappingProvider:
    def __init__(self, result: dict) -> None:
        self.result = result

    def answer(self, _request, _sources):
        return self.result


class ProviderCodecTests(TestCase):
    def test_valid_mapping_is_decoded_and_grounded_by_gateway(self):
        result = AIFoundationGateway(MappingProvider(payload())).answer(
            request(),
            (source(),),
        )
        self.assertEqual(AnswerState.SUPPORTED, result.answer.state)
        self.assertEqual("claim-1", result.answer.claims[0].claim_id)
        self.assertEqual(1, result.trace.citation_count)

    def test_unknown_top_level_field_is_rejected(self):
        item = payload()
        item["unreviewed_provider_field"] = "unexpected"
        with self.assertRaisesRegex(AnswerContractError, "unknown fields"):
            parse_grounded_answer(item)

    def test_unsupported_enum_value_is_rejected(self):
        item = payload()
        item["state"] = "probably_supported"
        with self.assertRaisesRegex(AnswerContractError, "unsupported value"):
            parse_grounded_answer(item)

    def test_claim_count_is_bounded(self):
        item = payload()
        item["claims"] = [deepcopy(item["claims"][0]) for _ in range(13)]
        with self.assertRaisesRegex(AnswerContractError, "too many claims"):
            parse_grounded_answer(item)

    def test_non_private_handoff_is_rejected(self):
        item = payload()
        item["handoff"] = {
            "reason": "human_judgment",
            "question": "What context should Pete add?",
            "private": False,
        }
        with self.assertRaisesRegex(AnswerContractError, "remain private"):
            parse_grounded_answer(item)

    def test_citation_must_name_its_parent_claim(self):
        item = payload()
        item["claims"][0]["citations"][0]["claim_id"] = "other-claim"
        with self.assertRaisesRegex(AnswerContractError, "parent claim"):
            parse_grounded_answer(item)

    def test_summary_length_is_bounded(self):
        item = payload()
        item["summary"] = "x" * 2_001
        with self.assertRaisesRegex(AnswerContractError, "exceeds 2000"):
            parse_grounded_answer(item)
