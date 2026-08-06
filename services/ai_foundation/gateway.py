"""One provider-neutral execution seam for PeerSlate AI products."""

from collections.abc import Mapping
from dataclasses import dataclass
from time import monotonic
from typing import Any, Callable, Protocol

from .citation_validator import authorize_sources, validate_grounded_answer
from .codec import parse_grounded_answer
from .contracts import AIRequest, GroundedAnswer, SourceVersion
from .errors import (
    AIFoundationError,
    AnswerContractError,
    ExecutionLimitError,
    GroundingValidationError,
    ProviderUnavailableError,
    SourceAuthorizationError,
)
from .limits import ExecutionLimits, enforce_execution_limits
from .observability import AITrace, TraceOutcome, build_trace


class AIProvider(Protocol):
    """A provider adapter receives only sources already authorized for use."""

    def answer(
        self,
        request: AIRequest,
        sources: tuple[SourceVersion, ...],
    ) -> GroundedAnswer | Mapping[str, Any]: ...


@dataclass(frozen=True)
class GatewayResult:
    answer: GroundedAnswer
    trace: AITrace


class AIFoundationGateway:
    def __init__(
        self,
        provider: AIProvider,
        *,
        limits: ExecutionLimits | None = None,
        trace_sink: Callable[[AITrace], None] | None = None,
    ) -> None:
        self._provider = provider
        self._limits = limits or ExecutionLimits()
        self._trace_sink = trace_sink

    def _emit_trace(self, trace: AITrace) -> None:
        if self._trace_sink is None:
            return
        try:
            self._trace_sink(trace)
        except Exception:
            # Diagnostics must never change the product answer or mask its
            # original failure. Runtime adapters own sink health monitoring.
            return

    @staticmethod
    def _error_category(error: AIFoundationError) -> str:
        if isinstance(error, SourceAuthorizationError):
            return "source_authorization"
        if isinstance(error, ExecutionLimitError):
            return "execution_limit"
        if isinstance(error, AnswerContractError):
            return "answer_contract"
        if isinstance(error, GroundingValidationError):
            return "grounding_validation"
        return "foundation_failure"

    def answer(
        self,
        request: AIRequest,
        sources: tuple[SourceVersion, ...],
    ) -> GatewayResult:
        started = monotonic()
        authorized: tuple[SourceVersion, ...] = ()
        provider_called = False

        try:
            enforce_execution_limits(request, sources, self._limits)
            # Authorization is deliberately before provider.answer. Private,
            # stale, cross-subject, or wrong-purpose material never reaches a
            # model.
            authorized = authorize_sources(request, sources)
            provider_called = True
            provider_answer = self._provider.answer(request, authorized)
            answer = (
                provider_answer
                if isinstance(provider_answer, GroundedAnswer)
                else parse_grounded_answer(provider_answer)
            )
            validated = validate_grounded_answer(request, authorized, answer)
            error_category = None
        except ProviderUnavailableError:
            validated = GroundedAnswer.unavailable(
                answer_id=f"{request.request_id}:unavailable",
                question=request.question,
            )
            error_category = "provider_unavailable"
            outcome = TraceOutcome.DEGRADED
        except AIFoundationError as error:
            trace = build_trace(
                request=request,
                source_count=len(authorized),
                source_character_count=sum(
                    len(source.content) for source in authorized
                ),
                outcome=TraceOutcome.FAILED,
                answer_state=None,
                claim_count=0,
                citation_count=0,
                provider_called=provider_called,
                duration_ms=round((monotonic() - started) * 1000),
                error_category=self._error_category(error),
            )
            self._emit_trace(trace)
            raise
        except Exception:
            trace = build_trace(
                request=request,
                source_count=len(authorized),
                source_character_count=sum(
                    len(source.content) for source in authorized
                ),
                outcome=TraceOutcome.FAILED,
                answer_state=None,
                claim_count=0,
                citation_count=0,
                provider_called=provider_called,
                duration_ms=round((monotonic() - started) * 1000),
                error_category="unexpected_provider_failure",
            )
            self._emit_trace(trace)
            raise
        else:
            outcome = TraceOutcome.COMPLETED

        trace = build_trace(
            request=request,
            source_count=len(authorized),
            source_character_count=sum(len(source.content) for source in authorized),
            outcome=outcome,
            answer_state=validated.state,
            claim_count=len(validated.claims),
            citation_count=sum(
                len(claim.citations) for claim in validated.claims
            ),
            provider_called=provider_called,
            duration_ms=round((monotonic() - started) * 1000),
            error_category=error_category,
        )
        self._emit_trace(trace)
        return GatewayResult(answer=validated, trace=trace)
