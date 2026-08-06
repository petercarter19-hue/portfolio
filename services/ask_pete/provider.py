"""A strict Messages-API adapter for Grounded Ask Pete.

This module owns no credentials, deployment settings, or global client. The
application supplies an already-configured client and model name at runtime.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from services.ai_foundation import AIRequest, SourceVersion
from services.ai_foundation.errors import (
    AnswerContractError,
    ProviderUnavailableError,
)


PROMPT_CONTRACT_VERSION = "ask-pete-grounded-public.v1"


class AnthropicGroundedProvider:
    """Adapt an injected Anthropic-compatible Messages client."""

    def __init__(
        self,
        client: Any,
        *,
        model_name: str,
        subject_display_name: str,
        prompt_path: Path,
        maximum_output_tokens: int = 1_600,
    ) -> None:
        if not model_name.strip():
            raise ValueError("model_name is required")
        if not subject_display_name.strip():
            raise ValueError("subject_display_name is required")
        if maximum_output_tokens < 1:
            raise ValueError("maximum_output_tokens must be positive")
        try:
            prompt = prompt_path.read_text(encoding="utf-8").strip()
        except (OSError, UnicodeError) as exc:
            raise ValueError("Ask Pete prompt contract could not be read") from exc
        if not prompt:
            raise ValueError("Ask Pete prompt contract is empty")
        self._client = client
        self._model_name = model_name
        self._subject_display_name = subject_display_name
        self._prompt = prompt
        self._maximum_output_tokens = maximum_output_tokens

    @staticmethod
    def _response_text(response: Any) -> str:
        blocks = getattr(response, "content", None)
        if not isinstance(blocks, (list, tuple)) or not blocks:
            raise AnswerContractError("provider response has no text block")
        first = blocks[0]
        text = first.get("text") if isinstance(first, Mapping) else getattr(first, "text", None)
        if not isinstance(text, str) or not text.strip():
            raise AnswerContractError("provider response has no text block")
        return text

    @staticmethod
    def _exact_excerpt_matches(content: str, excerpt: str) -> list[int]:
        matches: list[int] = []
        cursor = 0
        while True:
            start = content.find(excerpt, cursor)
            if start < 0:
                return matches
            matches.append(start)
            cursor = start + 1

    @classmethod
    def _derive_citation_spans(
        cls,
        payload: Mapping[str, Any],
        sources: tuple[SourceVersion, ...],
    ) -> dict[str, Any]:
        """Add exact offsets only when an excerpt is deterministically located."""

        answer = dict(payload)
        raw_claims = answer.get("claims", [])
        if not isinstance(raw_claims, (list, tuple)):
            return answer
        source_map = {source.source_version_key: source for source in sources}
        claims: list[Any] = []
        for raw_claim in raw_claims:
            if not isinstance(raw_claim, Mapping):
                claims.append(raw_claim)
                continue
            claim = dict(raw_claim)
            raw_citations = claim.get("citations", [])
            if not isinstance(raw_citations, (list, tuple)):
                claims.append(claim)
                continue
            citations: list[Any] = []
            for raw_citation in raw_citations:
                if not isinstance(raw_citation, Mapping):
                    citations.append(raw_citation)
                    continue
                citation = dict(raw_citation)
                source_key = citation.get("source_version_key")
                excerpt = citation.get("excerpt")
                if not isinstance(source_key, str) or not isinstance(excerpt, str):
                    citations.append(citation)
                    continue
                source = source_map.get(source_key)
                if source is None:
                    raise AnswerContractError(
                        "citation names a source outside the authorized request"
                    )
                matches = cls._exact_excerpt_matches(source.content, excerpt)
                if not matches:
                    raise AnswerContractError(
                        "citation excerpt does not occur in its approved source"
                    )
                if len(matches) == 1:
                    start = matches[0]
                else:
                    proposed_start = citation.get("start")
                    proposed_end = citation.get("end")
                    if (
                        isinstance(proposed_start, bool)
                        or not isinstance(proposed_start, int)
                        or isinstance(proposed_end, bool)
                        or not isinstance(proposed_end, int)
                        or proposed_start not in matches
                        or proposed_end != proposed_start + len(excerpt)
                    ):
                        raise AnswerContractError(
                            "citation excerpt is ambiguous within its approved source"
                        )
                    start = proposed_start
                citation["start"] = start
                citation["end"] = start + len(excerpt)
                citations.append(citation)
            claim["citations"] = citations
            claims.append(claim)
        answer["claims"] = claims
        return answer

    def answer(
        self,
        request: AIRequest,
        sources: tuple[SourceVersion, ...],
    ) -> Mapping[str, Any]:
        source_records = [
            {
                "source_version_key": source.source_version_key,
                "title": source.title,
                "content": source.content,
            }
            for source in sources
        ]
        request_document = {
            "purpose": request.purpose.value,
            "subject_display_name": self._subject_display_name,
            "question": request.question,
            "context_key": request.context_key,
            "approved_source_records": source_records,
        }
        try:
            response = self._client.messages.create(
                model=self._model_name,
                max_tokens=self._maximum_output_tokens,
                system=self._prompt,
                messages=[
                    {
                        "role": "user",
                        "content": json.dumps(
                            request_document,
                            ensure_ascii=False,
                            separators=(",", ":"),
                        ),
                    }
                ],
            )
        except Exception as exc:
            raise ProviderUnavailableError("configured provider call failed") from exc

        raw_text = self._response_text(response)
        try:
            payload = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise AnswerContractError("provider response is not strict JSON") from exc
        if not isinstance(payload, Mapping):
            raise AnswerContractError("provider response must be an object")

        answer = self._derive_citation_spans(payload, sources)
        # Server-owned metadata cannot be invented or changed by model output.
        answer["answer_id"] = f"{request.request_id}:answer"
        answer["model_name"] = self._model_name
        answer["prompt_contract_version"] = PROMPT_CONTRACT_VERSION
        return answer
