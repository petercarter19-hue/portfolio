"""Strict decoder for provider-produced structured answers.

Provider adapters may return ordinary mappings. This decoder accepts only the
documented keys, types, enum values, and bounded collection sizes before the
grounding validator evaluates any claim or citation.
"""

from collections.abc import Mapping, Sequence
from typing import Any, TypeVar

from .contracts import (
    AnswerClaim,
    AnswerKind,
    AnswerState,
    Citation,
    GroundedAnswer,
    HandoffProposal,
    HandoffReason,
)
from .errors import AnswerContractError


MAX_CLAIMS = 12
MAX_CITATIONS_PER_CLAIM = 8
MAX_FOLLOW_UPS = 5
MAX_SUMMARY_CHARS = 2_000
MAX_CLAIM_CHARS = 1_000
MAX_LIMITATION_CHARS = 1_000
MAX_FOLLOW_UP_CHARS = 300
MAX_EXCERPT_CHARS = 600

EnumType = TypeVar("EnumType")


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise AnswerContractError(f"{label} must be an object")
    return value


def _sequence(value: Any, label: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise AnswerContractError(f"{label} must be an array")
    return value


def _keys(value: Mapping[str, Any], *, allowed: set[str], label: str) -> None:
    unknown = set(value) - allowed
    if unknown:
        raise AnswerContractError(
            f"{label} contains unknown fields: {', '.join(sorted(unknown))}"
        )


def _text(
    value: Any,
    label: str,
    *,
    maximum: int,
    optional: bool = False,
) -> str | None:
    if value is None and optional:
        return None
    if not isinstance(value, str) or not value.strip():
        raise AnswerContractError(f"{label} must be non-empty text")
    if len(value) > maximum:
        raise AnswerContractError(f"{label} exceeds {maximum} characters")
    return value


def _enum(enum_type: type[EnumType], value: Any, label: str) -> EnumType:
    if not isinstance(value, str):
        raise AnswerContractError(f"{label} must be text")
    try:
        return enum_type(value)
    except ValueError as exc:
        raise AnswerContractError(f"{label} has an unsupported value") from exc


def _integer(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise AnswerContractError(f"{label} must be an integer")
    return value


def _citation(payload: Any, claim_id: str) -> Citation:
    item = _mapping(payload, "citation")
    _keys(
        item,
        allowed={"claim_id", "source_version_key", "start", "end", "excerpt"},
        label="citation",
    )
    decoded_claim_id = _text(
        item.get("claim_id"),
        "citation.claim_id",
        maximum=100,
    )
    if decoded_claim_id != claim_id:
        raise AnswerContractError("citation.claim_id must match its parent claim")
    return Citation(
        claim_id=decoded_claim_id,
        source_version_key=_text(
            item.get("source_version_key"),
            "citation.source_version_key",
            maximum=200,
        ),
        start=_integer(item.get("start"), "citation.start"),
        end=_integer(item.get("end"), "citation.end"),
        excerpt=_text(
            item.get("excerpt"),
            "citation.excerpt",
            maximum=MAX_EXCERPT_CHARS,
        ),
    )


def _claim(payload: Any) -> AnswerClaim:
    item = _mapping(payload, "claim")
    _keys(
        item,
        allowed={"claim_id", "text", "kind", "state", "citations", "limitation"},
        label="claim",
    )
    claim_id = _text(item.get("claim_id"), "claim.claim_id", maximum=100)
    citation_items = _sequence(item.get("citations", []), "claim.citations")
    if len(citation_items) > MAX_CITATIONS_PER_CLAIM:
        raise AnswerContractError("claim has too many citations")
    return AnswerClaim(
        claim_id=claim_id,
        text=_text(item.get("text"), "claim.text", maximum=MAX_CLAIM_CHARS),
        kind=_enum(AnswerKind, item.get("kind"), "claim.kind"),
        state=_enum(AnswerState, item.get("state"), "claim.state"),
        citations=tuple(_citation(value, claim_id) for value in citation_items),
        limitation=_text(
            item.get("limitation"),
            "claim.limitation",
            maximum=MAX_LIMITATION_CHARS,
            optional=True,
        ),
    )


def _handoff(payload: Any) -> HandoffProposal | None:
    if payload is None:
        return None
    item = _mapping(payload, "handoff")
    _keys(item, allowed={"reason", "question", "private"}, label="handoff")
    private = item.get("private", True)
    if not isinstance(private, bool):
        raise AnswerContractError("handoff.private must be a boolean")
    if not private:
        raise AnswerContractError("human handoff proposals must remain private")
    return HandoffProposal(
        reason=_enum(HandoffReason, item.get("reason"), "handoff.reason"),
        question=_text(item.get("question"), "handoff.question", maximum=1_000),
        private=True,
    )


def parse_grounded_answer(payload: Mapping[str, Any]) -> GroundedAnswer:
    item = _mapping(payload, "answer")
    _keys(
        item,
        allowed={
            "answer_id",
            "state",
            "summary",
            "claims",
            "follow_up_questions",
            "handoff",
            "model_name",
            "prompt_contract_version",
        },
        label="answer",
    )
    claim_items = _sequence(item.get("claims", []), "answer.claims")
    if len(claim_items) > MAX_CLAIMS:
        raise AnswerContractError("answer has too many claims")
    follow_up_items = _sequence(
        item.get("follow_up_questions", []),
        "answer.follow_up_questions",
    )
    if len(follow_up_items) > MAX_FOLLOW_UPS:
        raise AnswerContractError("answer has too many follow-up questions")
    return GroundedAnswer(
        answer_id=_text(item.get("answer_id"), "answer.answer_id", maximum=200),
        state=_enum(AnswerState, item.get("state"), "answer.state"),
        summary=_text(item.get("summary"), "answer.summary", maximum=MAX_SUMMARY_CHARS),
        claims=tuple(_claim(value) for value in claim_items),
        follow_up_questions=tuple(
            _text(
                value,
                "answer.follow_up_question",
                maximum=MAX_FOLLOW_UP_CHARS,
            )
            for value in follow_up_items
        ),
        handoff=_handoff(item.get("handoff")),
        model_name=_text(
            item.get("model_name"),
            "answer.model_name",
            maximum=200,
            optional=True,
        ),
        prompt_contract_version=_text(
            item.get("prompt_contract_version"),
            "answer.prompt_contract_version",
            maximum=200,
            optional=True,
        ),
    )
