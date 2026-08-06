"""Provider-neutral request and source budgets.

Character budgets are deterministic safeguards, not provider token estimates.
Product adapters may select stricter values without weakening authorization or
grounding validation.
"""

from dataclasses import dataclass

from .contracts import AIRequest, SourceVersion
from .errors import ExecutionLimitError


@dataclass(frozen=True)
class ExecutionLimits:
    maximum_question_characters: int = 4_000
    maximum_sources: int = 32
    maximum_single_source_characters: int = 30_000
    maximum_total_source_characters: int = 120_000

    def __post_init__(self) -> None:
        for label, value in (
            ("maximum_question_characters", self.maximum_question_characters),
            ("maximum_sources", self.maximum_sources),
            (
                "maximum_single_source_characters",
                self.maximum_single_source_characters,
            ),
            (
                "maximum_total_source_characters",
                self.maximum_total_source_characters,
            ),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"{label} must be a positive integer")
        if (
            self.maximum_single_source_characters
            > self.maximum_total_source_characters
        ):
            raise ValueError("single-source limit cannot exceed the total limit")


def enforce_execution_limits(
    request: AIRequest,
    sources: tuple[SourceVersion, ...],
    limits: ExecutionLimits,
) -> None:
    if len(request.question) > limits.maximum_question_characters:
        raise ExecutionLimitError("question exceeds the configured limit")
    if len(sources) > limits.maximum_sources:
        raise ExecutionLimitError("source count exceeds the configured limit")
    if any(
        len(source.content) > limits.maximum_single_source_characters
        for source in sources
    ):
        raise ExecutionLimitError("one source exceeds the configured limit")
    if (
        sum(len(source.content) for source in sources)
        > limits.maximum_total_source_characters
    ):
        raise ExecutionLimitError("source total exceeds the configured limit")
