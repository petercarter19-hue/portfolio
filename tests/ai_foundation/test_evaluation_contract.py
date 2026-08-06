from unittest import TestCase

from services.ai_foundation import (
    AnswerClaim,
    AnswerExpectation,
    AnswerKind,
    AnswerState,
    Citation,
    GroundedAnswer,
    HandoffProposal,
    HandoffReason,
    evaluate_answer,
)


def recruiter_brief() -> GroundedAnswer:
    return GroundedAnswer(
        answer_id="brief-1",
        state=AnswerState.PARTIALLY_SUPPORTED,
        summary=" ".join(["documented"] * 100),
        claims=(
            AnswerClaim(
                claim_id="evidence-1",
                text="Pete has documented engineering leadership.",
                kind=AnswerKind.EVIDENCE,
                state=AnswerState.SUPPORTED,
                citations=(
                    Citation(
                        claim_id="evidence-1",
                        source_version_key="role:v1",
                        start=0,
                        end=10,
                        excerpt="documented",
                    ),
                ),
            ),
            AnswerClaim(
                claim_id="boundary-1",
                text="A specific opening has not been evaluated.",
                kind=AnswerKind.BOUNDARY,
                state=AnswerState.NOT_ESTABLISHED,
                limitation="No role requirements were provided.",
            ),
        ),
        follow_up_questions=("Ask about leadership.", "Ask about MBSE."),
        handoff=HandoffProposal(
            reason=HandoffReason.HUMAN_JUDGMENT,
            question="What should the recruiter clarify with Pete?",
        ),
    )


def expectation() -> AnswerExpectation:
    return AnswerExpectation(
        allowed_states=frozenset(
            {AnswerState.SUPPORTED, AnswerState.PARTIALLY_SUPPORTED}
        ),
        minimum_claims=2,
        minimum_citations=1,
        minimum_follow_ups=2,
        minimum_summary_words=100,
        maximum_summary_words=140,
        requires_boundary=True,
        requires_handoff=True,
    )


class EvaluationContractTests(TestCase):
    def test_recruiter_brief_quality_contract_passes(self):
        result = evaluate_answer(
            case_id="recruiter-brief-happy-path",
            answer=recruiter_brief(),
            expectation=expectation(),
        )
        self.assertTrue(result.passed)
        self.assertEqual((), result.failures)

    def test_failures_are_deterministic_and_payload_free(self):
        answer = GroundedAnswer(
            answer_id="brief-incomplete",
            state=AnswerState.NOT_ESTABLISHED,
            summary="Too short.",
        )
        result = evaluate_answer(
            case_id="recruiter-brief-incomplete",
            answer=answer,
            expectation=expectation(),
        )
        self.assertFalse(result.passed)
        self.assertEqual(
            (
                "state_not_allowed",
                "claim_count_below_minimum",
                "citation_count_below_minimum",
                "follow_up_count_below_minimum",
                "summary_below_minimum_words",
                "boundary_claim_required",
                "private_handoff_required",
            ),
            result.failures,
        )
        self.assertNotIn(answer.summary, repr(result))

    def test_invalid_word_range_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "word limits are reversed"):
            AnswerExpectation(
                allowed_states=frozenset({AnswerState.SUPPORTED}),
                minimum_summary_words=140,
                maximum_summary_words=100,
            )
