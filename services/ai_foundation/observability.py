"""Privacy-safe diagnostic records for AI calls.

Questions, source bodies, excerpts, prompts, model output, email addresses, and
private member content have no field in this contract.
"""

from dataclasses import dataclass
from enum import Enum

from .contracts import AIRequest, AnswerState


class TraceOutcome(str, Enum):
    COMPLETED = "completed"
    DEGRADED = "degraded"
    FAILED = "failed"


@dataclass(frozen=True)
class AITrace:
    request_id: str
    product: str
    purpose: str
    audience: str
    source_count: int
    source_character_count: int
    outcome: str
    answer_state: str | None
    claim_count: int
    citation_count: int
    provider_called: bool
    duration_ms: int
    error_category: str | None = None


def build_trace(
    *,
    request: AIRequest,
    source_count: int,
    source_character_count: int,
    outcome: TraceOutcome,
    answer_state: AnswerState | None,
    claim_count: int,
    citation_count: int,
    provider_called: bool,
    duration_ms: int,
    error_category: str | None = None,
) -> AITrace:
    return AITrace(
        request_id=request.request_id,
        product=request.product,
        purpose=request.purpose.value,
        audience=request.audience.value,
        source_count=source_count,
        source_character_count=source_character_count,
        outcome=outcome.value,
        answer_state=answer_state.value if answer_state is not None else None,
        claim_count=claim_count,
        citation_count=citation_count,
        provider_called=provider_called,
        duration_ms=max(0, duration_ms),
        error_category=error_category,
    )
