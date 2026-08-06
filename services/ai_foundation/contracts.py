"""Provider-neutral request, source, answer, and handoff contracts.

Source text and its exact approved version, evidence-backed claims, labelled
interpretations, and unknown boundaries remain distinct. Nothing here
persists, publishes, or mutates member truth.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from hashlib import sha256


def _required_text(label: str, value: object) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} is required text")


def _bounded_identifier(label: str, value: object, *, maximum: int = 200) -> None:
    _required_text(label, value)
    if len(value) > maximum or not value.isprintable():
        raise ValueError(f"{label} is not a valid bounded identifier")


class Purpose(str, Enum):
    PUBLIC_PROFILE_ANSWER = "public_profile_answer"
    RECRUITER_BRIEF = "recruiter_brief"
    EVIDENCE_FINDER = "evidence_finder"
    INTERVIEW_PREPARATION = "interview_preparation"
    PRIVATE_COACHING = "private_coaching"


class Audience(str, Enum):
    PUBLIC = "public"
    OWNER = "owner"
    AUTHORIZED_RECRUITER = "authorized_recruiter"


class AnswerKind(str, Enum):
    EVIDENCE = "evidence"
    INTERPRETATION = "interpretation"
    BOUNDARY = "boundary"


class AnswerState(str, Enum):
    SUPPORTED = "supported"
    PARTIALLY_SUPPORTED = "partially_supported"
    NOT_ESTABLISHED = "not_established"
    AMBIGUOUS = "ambiguous"
    REFUSED = "refused"
    UNAVAILABLE = "unavailable"


class HandoffReason(str, Enum):
    MISSING_PUBLIC_EVIDENCE = "missing_public_evidence"
    AMBIGUOUS_QUESTION = "ambiguous_question"
    HUMAN_JUDGMENT = "human_judgment"
    PROVIDER_UNAVAILABLE = "provider_unavailable"


@dataclass(frozen=True)
class AIRequest:
    request_id: str
    product: str
    purpose: Purpose
    audience: Audience
    subject_key: str
    question: str = field(repr=False)
    context_key: str | None = None

    def __post_init__(self) -> None:
        _bounded_identifier("request_id", self.request_id)
        _bounded_identifier("product", self.product, maximum=100)
        _bounded_identifier("subject_key", self.subject_key)
        _required_text("question", self.question)
        if not isinstance(self.purpose, Purpose):
            raise ValueError("purpose must be a Purpose")
        if not isinstance(self.audience, Audience):
            raise ValueError("audience must be an Audience")
        if self.context_key is not None:
            _bounded_identifier("context_key", self.context_key, maximum=300)


@dataclass(frozen=True)
class SourceVersion:
    """One immutable source version already retrieved under authorization."""

    source_version_key: str
    source_key: str
    version: int
    subject_key: str
    title: str
    content: str = field(repr=False)
    content_sha256: str
    allowed_audiences: frozenset[Audience]
    allowed_purposes: frozenset[Purpose]

    def __post_init__(self) -> None:
        _bounded_identifier("source_version_key", self.source_version_key)
        _bounded_identifier("source_key", self.source_key)
        if (
            isinstance(self.version, bool)
            or not isinstance(self.version, int)
            or self.version < 1
        ):
            raise ValueError("source version must be positive")
        _bounded_identifier("subject_key", self.subject_key)
        _required_text("title", self.title)
        _required_text("content", self.content)
        _required_text("content_sha256", self.content_sha256)
        if len(self.content_sha256) != 64 or any(
            character not in "0123456789abcdefABCDEF"
            for character in self.content_sha256
        ):
            raise ValueError("content digest must be a SHA-256 hex value")
        if not isinstance(self.allowed_audiences, frozenset) or any(
            not isinstance(value, Audience) for value in self.allowed_audiences
        ):
            raise ValueError("allowed audiences must be Audience values")
        if not isinstance(self.allowed_purposes, frozenset) or any(
            not isinstance(value, Purpose) for value in self.allowed_purposes
        ):
            raise ValueError("allowed purposes must be Purpose values")
        if not self.allowed_audiences or not self.allowed_purposes:
            raise ValueError("every source version needs an explicit use scope")

    @classmethod
    def approved(
        cls,
        *,
        source_version_key: str,
        source_key: str,
        version: int,
        subject_key: str,
        title: str,
        content: str,
        allowed_audiences: frozenset[Audience],
        allowed_purposes: frozenset[Purpose],
    ) -> "SourceVersion":
        return cls(
            source_version_key=source_version_key,
            source_key=source_key,
            version=version,
            subject_key=subject_key,
            title=title,
            content=content,
            content_sha256=sha256(content.encode("utf-8")).hexdigest(),
            allowed_audiences=allowed_audiences,
            allowed_purposes=allowed_purposes,
        )

    def digest_is_current(self) -> bool:
        return sha256(self.content.encode("utf-8")).hexdigest() == self.content_sha256

    def permits(self, request: AIRequest) -> bool:
        return (
            self.subject_key == request.subject_key
            and request.audience in self.allowed_audiences
            and request.purpose in self.allowed_purposes
        )


@dataclass(frozen=True)
class Citation:
    claim_id: str
    source_version_key: str
    start: int
    end: int
    excerpt: str = field(repr=False)


@dataclass(frozen=True)
class AnswerClaim:
    claim_id: str
    text: str
    kind: AnswerKind
    state: AnswerState
    citations: tuple[Citation, ...] = ()
    limitation: str | None = None


@dataclass(frozen=True)
class HandoffProposal:
    reason: HandoffReason
    question: str = field(repr=False)
    private: bool = True


@dataclass(frozen=True)
class GroundedAnswer:
    answer_id: str
    state: AnswerState
    summary: str
    claims: tuple[AnswerClaim, ...] = ()
    follow_up_questions: tuple[str, ...] = ()
    handoff: HandoffProposal | None = None
    model_name: str | None = None
    prompt_contract_version: str | None = None

    @classmethod
    def unavailable(cls, *, answer_id: str, question: str) -> "GroundedAnswer":
        return cls(
            answer_id=answer_id,
            state=AnswerState.UNAVAILABLE,
            summary=(
                "Ask Pete is temporarily unavailable. The public resume and "
                "its evidence remain available to review."
            ),
            handoff=HandoffProposal(
                reason=HandoffReason.PROVIDER_UNAVAILABLE,
                question=question,
            ),
        )
