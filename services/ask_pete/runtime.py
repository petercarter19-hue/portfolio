"""Repository-path runtime assembly for the dormant Ask Pete app seam."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable
from functools import lru_cache
import os
from time import monotonic
from uuid import uuid4

from services.ai_foundation import AITrace

from .manifest import load_public_source_catalog
from .provider import AnthropicGroundedProvider
from .service import AskPeteResult, AskPeteService
from .classification import classify_public_purpose
from .diagnostics import AskPeteDiagnostic
from .errors import AskPeteRequestError
from .deadline import RequestDeadline, run_bounded
from services.ai_foundation.errors import AIFoundationError, ProviderUnavailableError


DEFAULT_MODEL_NAME = "claude-haiku-4-5-20251001"


@lru_cache(maxsize=1)
def _foundry_credential():
    from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
    if os.environ.get("WEBSITE_INSTANCE_ID"):
        # The reviewed production grant belongs to this existing system
        # identity. Do not silently select environment/user/CLI credentials.
        return ManagedIdentityCredential()
    return DefaultAzureCredential(exclude_interactive_browser_credential=True)


def _foundry_token():
    from services.ai_foundation.azure_foundry import FOUNDRY_TOKEN_SCOPE
    return _foundry_credential().get_token(FOUNDRY_TOKEN_SCOPE).token


def _catalog(root_path):
    return load_public_source_catalog(
        manifest_path=root_path / "data" / "ai_sources" / "ask_pete_public_v1.json",
        resume_path=root_path / "static" / "data" / "resume_data.json",
    )


def _unavailable(request_id, purpose, elapsed_ms):
    # No file read, model output or stale source/identity data in a timeout
    # response. This path must still finish when a worker remains blocked.
    message = "Ask Pete is temporarily unavailable. You can continue reviewing the public resume and its evidence."
    return AskPeteResult(payload={
        "schema_version": "ask-pete-public-answer.v1", "answer_id": f"{request_id}:unavailable",
        "purpose": purpose.value, "state": "unavailable", "support_label": "Temporarily unavailable",
        "summary": message, "response": message, "claims": [], "follow_up_questions": [],
        "handoff": None, "sources_used": [], "context": None,
        "source_summary": {"used_count": 0, "label": "No public records returned", "show_all_on_resume": False},
    }, diagnostic=AskPeteDiagnostic(
        request_id=request_id, manifest_id="unavailable", purpose=purpose.value,
        context_applied=False, source_count=0, source_character_count=0,
        outcome="degraded", answer_state="unavailable", claim_count=0,
        citation_count=0, provider_called=None, duration_ms=elapsed_ms,
        error_category="provider_unavailable",
    ))


def _answer_foundry(*, root_path, endpoint, question, requested_action,
                    context_key, request_id, trace_sink, execution_sink):
    from .foundry_provider import FoundryGroundedProvider
    if not isinstance(question, str) or not question.strip():
        raise AskPeteRequestError("question is required")
    purpose = classify_public_purpose(question.strip(), requested_action=requested_action)
    request_id = request_id or f"ask-pete-{uuid4().hex}"
    started = monotonic()
    deadline = RequestDeadline.start()
    def emit(event):
        if execution_sink:
            try:
                execution_sink(event)
            except Exception:
                pass
    def work():
        source_started = monotonic()
        catalog = _catalog(root_path)
        deadline.remaining()
        emit({"request_id": request_id, "phase": "sources", "source_count": len(catalog.sources),
              "source_bytes": sum(len(s.content.encode("utf-8")) for s in catalog.sources),
              "duration_ms": round((monotonic() - source_started) * 1000)})
        def current_check():
            checked = monotonic()
            deadline.remaining()
            if _catalog(root_path) != catalog:
                raise ProviderUnavailableError("Approved source catalog changed")
            deadline.remaining()
            emit({"request_id": request_id, "phase": "currentness",
                  "duration_ms": round((monotonic() - checked) * 1000)})
        provider = FoundryGroundedProvider(
            endpoint=endpoint, token_provider=_foundry_token,
            subject_display_name=catalog.subject_display_name,
            prompt_path=root_path / "prompts" / "ask_pete" / "grounded_public_v1.md",
            deadline=deadline, event_sink=emit,
        )
        service = AskPeteService(catalog=catalog, provider=provider, trace_sink=trace_sink,
                                quality_rounds=1, current_catalog_check=current_check,
                                execution_sink=emit)
        result = service.answer(question, requested_action=requested_action,
                                context_key=context_key, request_id=request_id)
        deadline.remaining()
        return result
    outcome = "unavailable"
    try:
        result = run_bounded(work, deadline)
        outcome = result.payload["state"]
        return result
    except AskPeteRequestError:
        outcome = "invalid_request"
        raise
    except (AIFoundationError, ValueError):
        return _unavailable(request_id, purpose, round((monotonic() - started) * 1000))
    finally:
        emit({"request_id": request_id, "phase": "request", "outcome": outcome,
              "duration_ms": round((monotonic() - started) * 1000),
              "deadline_seconds": 20, "quality_resamples": 0, "corrective_retries": 0})


def build_ask_pete_service(
    *,
    root_path: Path,
    client: Any,
    model_name: str = DEFAULT_MODEL_NAME,
    trace_sink: Callable[[AITrace], None] | None = None,
) -> AskPeteService:
    catalog = load_public_source_catalog(
        manifest_path=root_path / "data" / "ai_sources" / "ask_pete_public_v1.json",
        resume_path=root_path / "static" / "data" / "resume_data.json",
    )
    provider = AnthropicGroundedProvider(
        client,
        model_name=model_name,
        subject_display_name=catalog.subject_display_name,
        prompt_path=root_path / "prompts" / "ask_pete" / "grounded_public_v1.md",
    )
    return AskPeteService(
        catalog=catalog,
        provider=provider,
        trace_sink=trace_sink,
    )


def answer_public_question(
    *,
    root_path: Path,
    client: Any,
    question: str,
    requested_action: str | None = None,
    context_key: str | None = None,
    request_id: str | None = None,
    trace_sink: Callable[[AITrace], None] | None = None,
    foundry_enabled: bool = False,
    foundry_endpoint: str | None = None,
    execution_sink: Callable[[dict], None] | None = None,
) -> AskPeteResult:
    if foundry_enabled:
        return _answer_foundry(
            root_path=root_path, endpoint=foundry_endpoint or "", question=question,
            requested_action=requested_action, context_key=context_key,
            request_id=request_id, trace_sink=trace_sink, execution_sink=execution_sink,
        )
    service = build_ask_pete_service(
        root_path=root_path,
        client=client,
        trace_sink=trace_sink,
    )
    return service.answer(
        question,
        requested_action=requested_action,
        context_key=context_key,
        request_id=request_id,
    )
