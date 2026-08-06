"""Deterministic product-level evaluation criteria for grounded answers.

Grounding validation establishes whether an answer is safe to present. These
checks establish whether a safe answer also satisfies a product interaction's
quality contract. Results contain only check identifiers, never answer text.
"""

from dataclasses import dataclass

from .contracts import AnswerKind, AnswerState, GroundedAnswer


@dataclass(frozen=True)
class AnswerExpectation:
    allowed_states: frozenset[AnswerState]
    minimum_claims: int = 0
    minimum_citations: int = 0
    minimum_follow_ups: int = 0
    minimum_summary_words: int | None = None
    maximum_summary_words: int | None = None
    requires_boundary: bool = False
    requires_handoff: bool = False

    def __post_init__(self) -> None:
        if not self.allowed_states:
            raise ValueError("an evaluation needs at least one allowed state")
        for label, value in (
            ("minimum_claims", self.minimum_claims),
            ("minimum_citations", self.minimum_citations),
            ("minimum_follow_ups", self.minimum_follow_ups),
        ):
            if value < 0:
                raise ValueError(f"{label} cannot be negative")
        for label, value in (
            ("minimum_summary_words", self.minimum_summary_words),
            ("maximum_summary_words", self.maximum_summary_words),
        ):
            if value is not None and value < 1:
                raise ValueError(f"{label} must be positive when supplied")
        if (
            self.minimum_summary_words is not None
            and self.maximum_summary_words is not None
            and self.minimum_summary_words > self.maximum_summary_words
        ):
            raise ValueError("summary word limits are reversed")


@dataclass(frozen=True)
class EvaluationResult:
    case_id: str
    passed: bool
    failures: tuple[str, ...]


def evaluate_answer(
    *,
    case_id: str,
    answer: GroundedAnswer,
    expectation: AnswerExpectation,
) -> EvaluationResult:
    """Evaluate structure and usefulness without retaining answer payloads."""

    if not case_id.strip():
        raise ValueError("case_id is required")

    failures: list[str] = []
    citation_count = sum(len(claim.citations) for claim in answer.claims)
    summary_words = len(answer.summary.split())

    if answer.state not in expectation.allowed_states:
        failures.append("state_not_allowed")
    if len(answer.claims) < expectation.minimum_claims:
        failures.append("claim_count_below_minimum")
    if citation_count < expectation.minimum_citations:
        failures.append("citation_count_below_minimum")
    if len(answer.follow_up_questions) < expectation.minimum_follow_ups:
        failures.append("follow_up_count_below_minimum")
    if (
        expectation.minimum_summary_words is not None
        and summary_words < expectation.minimum_summary_words
    ):
        failures.append("summary_below_minimum_words")
    if (
        expectation.maximum_summary_words is not None
        and summary_words > expectation.maximum_summary_words
    ):
        failures.append("summary_above_maximum_words")
    if expectation.requires_boundary and not any(
        claim.kind is AnswerKind.BOUNDARY for claim in answer.claims
    ):
        failures.append("boundary_claim_required")
    if expectation.requires_handoff and answer.handoff is None:
        failures.append("private_handoff_required")

    return EvaluationResult(
        case_id=case_id,
        passed=not failures,
        failures=tuple(failures),
    )
