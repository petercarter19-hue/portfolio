"""Repository-path runtime assembly for the dormant Ask Pete app seam."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from services.ai_foundation import AITrace

from .manifest import load_public_source_catalog
from .provider import AnthropicGroundedProvider
from .service import AskPeteResult, AskPeteService


DEFAULT_MODEL_NAME = "claude-haiku-4-5-20251001"


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
) -> AskPeteResult:
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
