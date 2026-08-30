"""Bounded, proposal-only interpretation seam for My Opportunities criteria.

This module deliberately owns no persistence.  A provider may propose a
structured draft, but :mod:`criteria_service` validates ownership and performs
every state change, token rotation, and terminal transition deterministically.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol, Sequence


MAX_REQUEST_TEXT_UTF16_UNITS = 4_000
MAX_LOCALE_UNITS = 64
MAX_TIMEZONE_UNITS = 128
MAX_CRITERIA = 64
MAX_DIRECT_FILTERS = 32

_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_-]{0,79}$")
_KIND_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_VERIFICATION_SCOPES = frozenset({"fully_verified", "not_fully_verified", "both"})


def utf16_units(value: str) -> int:
    return len(value.encode("utf-16-le")) // 2


class InterpretationUnavailable(RuntimeError):
    """The optional interpretation provider is unavailable."""


class InterpretationContractError(ValueError):
    """A request or provider proposal violates the bounded C3 contract."""


@dataclass(frozen=True)
class ProposedCriterion:
    kind: str
    display_label: str
    value: str


@dataclass(frozen=True)
class ProposedClarificationOption:
    option_key: str
    display_label: str
    criteria: tuple[ProposedCriterion, ...] = ()


@dataclass(frozen=True)
class ProposedClarification:
    clarification_key: str
    question: str
    options: tuple[ProposedClarificationOption, ...]
    scope: str


@dataclass(frozen=True)
class InterpretationProposal:
    criteria: tuple[ProposedCriterion, ...] = ()
    verification_scope: str = "both"
    direct_filters: tuple[tuple[str, str], ...] = ()
    clarification: ProposedClarification | None = None


@dataclass(frozen=True)
class InterpretationResult:
    proposal: InterpretationProposal
    interpretation_provenance: str


class InterpretationProvider(Protocol):
    def interpret(
        self,
        request_text: str,
        *,
        locale: str,
        timezone: str,
    ) -> InterpretationProposal: ...


class UnavailableInterpretationProvider:
    """Default provider: truthful manual fallback, never an invented AI result."""

    def interpret(
        self,
        request_text: str,
        *,
        locale: str,
        timezone: str,
    ) -> InterpretationProposal:
        del request_text, locale, timezone
        raise InterpretationUnavailable("interpretation_unavailable")


class InterpretationService:
    def __init__(self, provider: InterpretationProvider | None = None) -> None:
        self._provider = provider or UnavailableInterpretationProvider()

    def propose(self, request_text: str, *, locale: str, timezone: str) -> InterpretationResult:
        request_text = _bounded_text(
            request_text,
            "request_text",
            MAX_REQUEST_TEXT_UTF16_UNITS,
            allow_empty=False,
        )
        locale = _bounded_text(locale, "locale", MAX_LOCALE_UNITS, allow_empty=False)
        timezone = _bounded_text(
            timezone,
            "timezone",
            MAX_TIMEZONE_UNITS,
            allow_empty=False,
        )
        try:
            raw = self._provider.interpret(
                request_text,
                locale=locale,
                timezone=timezone,
            )
        except InterpretationUnavailable:
            return InterpretationResult(InterpretationProposal(), "manual_required")
        return InterpretationResult(_validate_proposal(raw), "ai_interpreted")


def _bounded_text(value: object, label: str, maximum: int, *, allow_empty: bool) -> str:
    if not isinstance(value, str):
        raise InterpretationContractError(f"{label}_invalid")
    normalized = value.strip()
    if not allow_empty and not normalized:
        raise InterpretationContractError(f"{label}_required")
    if utf16_units(normalized) > maximum:
        raise InterpretationContractError(f"{label}_too_long")
    return normalized


def _criterion(value: object) -> ProposedCriterion:
    if not isinstance(value, ProposedCriterion):
        raise InterpretationContractError("criterion_invalid")
    kind = _bounded_text(value.kind, "criterion_kind", 64, allow_empty=False)
    if not _KIND_PATTERN.fullmatch(kind):
        raise InterpretationContractError("criterion_kind_invalid")
    return ProposedCriterion(
        kind=kind,
        display_label=_bounded_text(
            value.display_label, "criterion_display_label", 200, allow_empty=False
        ),
        value=_bounded_text(value.value, "criterion_value", 1_000, allow_empty=False),
    )


def _bounded_sequence(
    value: object,
    label: str,
    maximum: int,
    *,
    minimum: int = 0,
) -> Sequence[object]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise InterpretationContractError(f"{label}_invalid")
    if not minimum <= len(value) <= maximum:
        raise InterpretationContractError(f"{label}_invalid")
    return value


def _clarification(value: object) -> ProposedClarification:
    if not isinstance(value, ProposedClarification):
        raise InterpretationContractError("clarification_invalid")
    key = _bounded_text(value.clarification_key, "clarification_key", 80, allow_empty=False)
    if not _KEY_PATTERN.fullmatch(key):
        raise InterpretationContractError("clarification_key_invalid")
    raw_options = _bounded_sequence(
        value.options,
        "clarification_options",
        8,
        minimum=2,
    )
    seen: set[str] = set()
    options: list[ProposedClarificationOption] = []
    proposed_criteria_count = 0
    for option in raw_options:
        if not isinstance(option, ProposedClarificationOption):
            raise InterpretationContractError("clarification_option_invalid")
        option_key = _bounded_text(option.option_key, "option_key", 80, allow_empty=False)
        if not _KEY_PATTERN.fullmatch(option_key) or option_key in seen:
            raise InterpretationContractError("option_key_invalid")
        seen.add(option_key)
        option_criteria = _bounded_sequence(
            option.criteria,
            "clarification_option_criteria",
            MAX_CRITERIA,
        )
        proposed_criteria_count += len(option_criteria)
        if proposed_criteria_count > MAX_CRITERIA:
            raise InterpretationContractError("too_many_clarification_criteria")
        options.append(
            ProposedClarificationOption(
                option_key=option_key,
                display_label=_bounded_text(
                    option.display_label, "option_display_label", 200, allow_empty=False
                ),
                criteria=tuple(_criterion(item) for item in option_criteria),
            )
        )
    return ProposedClarification(
        clarification_key=key,
        question=_bounded_text(value.question, "clarification_question", 500, allow_empty=False),
        options=tuple(options),
        scope=_bounded_text(value.scope, "clarification_scope", 80, allow_empty=False),
    )


def _validate_proposal(value: object) -> InterpretationProposal:
    if not isinstance(value, InterpretationProposal):
        raise InterpretationContractError("proposal_invalid")
    raw_criteria = _bounded_sequence(value.criteria, "proposal_criteria", MAX_CRITERIA)
    if value.verification_scope not in _VERIFICATION_SCOPES:
        raise InterpretationContractError("verification_scope_invalid")
    raw_filters = _bounded_sequence(
        value.direct_filters,
        "proposal_direct_filters",
        MAX_DIRECT_FILTERS,
    )
    filters: list[tuple[str, str]] = []
    seen_filters: set[str] = set()
    for pair in raw_filters:
        if not isinstance(pair, Sequence) or isinstance(pair, (str, bytes)) or len(pair) != 2:
            raise InterpretationContractError("direct_filter_invalid")
        key = _bounded_text(pair[0], "direct_filter_key", 80, allow_empty=False)
        filter_value = _bounded_text(pair[1], "direct_filter_value", 500, allow_empty=False)
        if not _KEY_PATTERN.fullmatch(key) or key in seen_filters:
            raise InterpretationContractError("direct_filter_key_invalid")
        seen_filters.add(key)
        filters.append((key, filter_value))
    return InterpretationProposal(
        criteria=tuple(_criterion(item) for item in raw_criteria),
        verification_scope=value.verification_scope,
        direct_filters=tuple(filters),
        clarification=None if value.clarification is None else _clarification(value.clarification),
    )


__all__ = [
    "InterpretationContractError",
    "InterpretationProposal",
    "InterpretationProvider",
    "InterpretationResult",
    "InterpretationService",
    "InterpretationUnavailable",
    "ProposedClarification",
    "ProposedClarificationOption",
    "ProposedCriterion",
    "UnavailableInterpretationProvider",
    "utf16_units",
]
