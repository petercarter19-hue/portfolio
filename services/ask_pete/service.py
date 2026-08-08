"""Grounded Ask Pete orchestration over the shared AI foundation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable
from uuid import uuid4

from services.ai_foundation import (
    AIFoundationGateway,
    AIProvider,
    AIRequest,
    AITrace,
    Audience,
    ExecutionLimits,
    GatewayResult,
    Purpose,
    SourceVersion,
)

from services.ai_foundation.errors import (
    AnswerContractError,
    GroundingValidationError,
)

from .classification import classify_public_purpose
from .diagnostics import AskPeteDiagnostic
from .errors import AskPeteRequestError, AskPeteResponseError
from .manifest import PublicSourceCatalog
from .quality import validate_product_quality
from .response import serialize_public_answer


# One fresh sample when a round refuses the model's own output, and only one.
# `AskPeteService._answer_and_validate` explains why a resample is the only
# correction available at this layer and what it costs.
MAXIMUM_QUALITY_ROUNDS = 2

# The refusals a second sample can plausibly fix. Every one of them is a
# judgment about what the model produced — its structure, its grounding, or its
# usefulness — and a different sample can produce something different.
#
# Deliberately absent, because a resample would re-buy the identical failure:
#
# - `ProviderUnavailableError` — transport. The gateway has already turned it
#   into the honest unavailable answer before it could reach here, and a second
#   paid call on a provider that just failed buys nothing.
# - `SourceAuthorizationError` and `ExecutionLimitError` — deterministic
#   functions of the request and the approved sources. Neither changes between
#   rounds, so a resample fails identically and pays a call to do it.
# - `PublicSourceManifestError` — source integrity, raised while the catalog is
#   assembled rather than inside a round. Resampling a model cannot repair a
#   changed digest, and must not appear to.
RESAMPLED_REFUSALS = (
    AskPeteResponseError,
    GroundingValidationError,
    AnswerContractError,
)


@dataclass(frozen=True)
class AskPeteResult:
    payload: dict
    diagnostic: AskPeteDiagnostic


class AskPeteService:
    def __init__(
        self,
        *,
        catalog: PublicSourceCatalog,
        provider: AIProvider,
        trace_sink: Callable[[AITrace], None] | None = None,
    ) -> None:
        self._catalog = catalog
        self._gateway = AIFoundationGateway(
            provider,
            limits=ExecutionLimits(
                maximum_question_characters=1_000,
                maximum_sources=20,
                maximum_single_source_characters=5_000,
                maximum_total_source_characters=30_000,
            ),
            trace_sink=trace_sink,
        )

    def _validated_context(self, context_key: str | None) -> str | None:
        if context_key is None:
            return None
        if not isinstance(context_key, str) or not context_key.strip():
            raise AskPeteRequestError("context must name an approved public record")
        normalized = context_key.strip()
        if normalized not in {
            record.locator.context_key for record in self._catalog.records
        }:
            raise AskPeteRequestError("context is outside the public source manifest")
        return normalized

    def _answer_and_validate(
        self,
        request: AIRequest,
        sources: tuple[SourceVersion, ...],
        purpose: Purpose,
    ) -> GatewayResult:
        """One grounded answer that is decodable, grounded, and useful.

        **Why the resample lives here.** Model output is judged at three
        layers, and only the first is inside the provider. The provider's
        corrective retry covers what it can see itself: an unparseable reply, a
        decoder bound, a citation excerpt that does not resolve. Past that,
        `validate_grounded_answer` judges grounding and state consistency
        inside `AIFoundationGateway.answer`, and `validate_product_quality`
        judges usefulness after the gateway returns. Neither is visible to the
        provider's correction, so before this method existed both were a 502.
        Four consecutive live rounds walked exactly that path — the excerpt
        layer, then the decoder layer, then the quality layer
        (`boundary_claim_required`), then the grounding layer
        (`interpretations must state their inferential boundary`,
        `a supported answer may contain only supported claims`). Every one of
        them is the model getting its own output wrong, so all three layers now
        share one resample.

        **It is a resample, not a correction.** There is no feedback channel:
        `AIRequest` carries a request id, product, purpose, audience, subject
        key, question, and context key, and nothing else. Adding a field would
        mean changing `services/ai_foundation/`, and writing the complaint into
        `question` would corrupt the one field that records what the visitor
        actually asked. A second sample of the same request is therefore a bet
        on sampling variance and a weaker instrument than the provider's
        corrective retry. It is worth taking once because the alternative for
        the flagship recruiter brief is a 502.

        **What is not resampled** is listed on `RESAMPLED_REFUSALS` above:
        transport, authorization, execution limits, and manifest integrity all
        fail identically on a second sample, so paying for one would be pure
        loss.

        **The combined ceiling, unchanged.** The provider makes at most 2 calls
        per round and there are at most 2 rounds, so one visitor question costs
        at most **4 provider calls**. Widening which refusals resample does not
        raise that ceiling; it means more paths can reach it. The typical cost
        is still 1 — every bound here is a failure path, and each of the live
        run's passing cases took a single call. Four bounded Haiku calls is a
        price worth paying to keep the flagship recruiter brief available
        rather than returning a 502, and the ceiling is a fixed small number
        rather than a loop.

        **Latency, and who gives up first.** Each provider call is bounded at
        30 s, so the worst-case chain can run to about 120 s while
        `static/js/chatbot.js` aborts its fetch at 45 s. In that worst case the
        visitor sees the browser's own failure before the server finishes. The
        server still finishes inside its own bounds — it never runs unbounded,
        never holds a worker for the SDK's 600 s default, and stops at a fixed
        call count — but it can finish generating an answer nobody is waiting
        for any more. Reaching that worst case needs three refusals in a row,
        each arriving late; it has not been observed. Recorded as an accepted
        limitation rather than assumed away.
        """

        result = self._gateway.answer(request, sources)
        validate_product_quality(purpose, result.answer)
        return result

    def answer(
        self,
        question: str,
        *,
        requested_action: str | None = None,
        context_key: str | None = None,
        request_id: str | None = None,
    ) -> AskPeteResult:
        if not isinstance(question, str) or not question.strip():
            raise AskPeteRequestError("question is required")
        normalized_question = question.strip()
        purpose = classify_public_purpose(
            normalized_question,
            requested_action=requested_action,
        )
        context = self._validated_context(context_key)
        request = AIRequest(
            request_id=request_id or f"ask-pete-{uuid4().hex}",
            product="ask_pete",
            purpose=purpose,
            audience=Audience.PUBLIC,
            subject_key=self._catalog.subject_key,
            question=normalized_question,
            context_key=context,
        )
        sources = self._catalog.sources_for(purpose, context_key=context)

        # Exactly one resample, then the refusal stands. Building nothing in
        # the handler keeps the second failure a failure in its own right
        # rather than the tail of the first one.
        resample = False
        try:
            result = self._answer_and_validate(request, sources, purpose)
        except RESAMPLED_REFUSALS:
            resample = True
        if resample:
            result = self._answer_and_validate(request, sources, purpose)

        payload = serialize_public_answer(
            answer=result.answer,
            catalog=self._catalog,
            purpose=purpose,
            context_key=context,
        )
        diagnostic = AskPeteDiagnostic.from_trace(
            result.trace,
            manifest_id=self._catalog.manifest_id,
            context_applied=context is not None,
        )
        return AskPeteResult(payload=payload, diagnostic=diagnostic)
