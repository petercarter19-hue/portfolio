"""Deterministic usefulness gates for the bounded recruiter interactions."""

from services.ai_foundation import (
    AnswerExpectation,
    AnswerState,
    GroundedAnswer,
    Purpose,
    evaluate_answer,
)

from .errors import AskPeteResponseError


def validate_product_quality(purpose: Purpose, answer: GroundedAnswer) -> None:
    if answer.state in {AnswerState.UNAVAILABLE, AnswerState.REFUSED}:
        return

    expectation = None
    if purpose is Purpose.RECRUITER_BRIEF:
        expectation = AnswerExpectation(
            allowed_states=frozenset({AnswerState.PARTIALLY_SUPPORTED}),
            minimum_claims=4,
            minimum_citations=3,
            minimum_follow_ups=2,
            minimum_summary_words=100,
            maximum_summary_words=140,
            requires_boundary=True,
            requires_handoff=True,
        )
    elif purpose is Purpose.INTERVIEW_PREPARATION and answer.state in {
        AnswerState.SUPPORTED,
        AnswerState.PARTIALLY_SUPPORTED,
    }:
        expectation = AnswerExpectation(
            allowed_states=frozenset(
                {AnswerState.SUPPORTED, AnswerState.PARTIALLY_SUPPORTED}
            ),
            minimum_claims=1,
            minimum_citations=1,
            minimum_follow_ups=3,
        )
    elif purpose is Purpose.EVIDENCE_FINDER and answer.state in {
        AnswerState.SUPPORTED,
        AnswerState.PARTIALLY_SUPPORTED,
    }:
        expectation = AnswerExpectation(
            allowed_states=frozenset(
                {AnswerState.SUPPORTED, AnswerState.PARTIALLY_SUPPORTED}
            ),
            minimum_claims=1,
            minimum_citations=1,
        )

    if expectation is None:
        return
    result = evaluate_answer(
        case_id=f"ask-pete-runtime-{purpose.value}",
        answer=answer,
        expectation=expectation,
    )
    if not result.passed:
        # Evaluation results intentionally contain check identifiers only;
        # visitor questions, answer text, and source excerpts stay out.
        raise AskPeteResponseError(
            "grounded answer did not satisfy the product quality contract: "
            + ",".join(result.failures)
        )
