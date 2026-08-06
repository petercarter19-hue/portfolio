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
)

from .classification import classify_public_purpose
from .diagnostics import AskPeteDiagnostic
from .errors import AskPeteRequestError
from .manifest import PublicSourceCatalog
from .quality import validate_product_quality
from .response import serialize_public_answer


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
        result = self._gateway.answer(request, sources)
        validate_product_quality(purpose, result.answer)
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
