"""Payload-free operational diagnostics for the Ask Pete product adapter."""

from dataclasses import dataclass

from services.ai_foundation import AITrace


@dataclass(frozen=True)
class AskPeteDiagnostic:
    request_id: str
    manifest_id: str
    purpose: str
    context_applied: bool
    source_count: int
    source_character_count: int
    outcome: str
    answer_state: str | None
    claim_count: int
    citation_count: int
    provider_called: bool
    duration_ms: int
    error_category: str | None

    @classmethod
    def from_trace(
        cls,
        trace: AITrace,
        *,
        manifest_id: str,
        context_applied: bool,
    ) -> "AskPeteDiagnostic":
        return cls(
            request_id=trace.request_id,
            manifest_id=manifest_id,
            purpose=trace.purpose,
            context_applied=context_applied,
            source_count=trace.source_count,
            source_character_count=trace.source_character_count,
            outcome=trace.outcome,
            answer_state=trace.answer_state,
            claim_count=trace.claim_count,
            citation_count=trace.citation_count,
            provider_called=trace.provider_called,
            duration_ms=trace.duration_ms,
            error_category=trace.error_category,
        )
