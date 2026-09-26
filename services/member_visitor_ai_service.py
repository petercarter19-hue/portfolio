"""Buffered questions: source authorization, grounding, semantic support, final fence.

No routes, persistence, provider selection, or account quota. A support adapter
must assess the complete answer (including summary/qualifiers), not just quote
presence. Without that adapter, factual output is unavailable. Deterministic
span checks do not claim general semantic entailment.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol
from services.ai_foundation.contracts import AIRequest, AnswerState, Audience, GroundedAnswer, Purpose, SourceVersion
from services.ai_foundation.gateway import AIFoundationGateway
from services.ai_foundation.citation_validator import validate_grounded_answer
from services.member_visitor_ai_sources import CurrentnessPort, EligibleSources, EligibleSourcesPort, PreviewBinding
from services.resume_publication_contracts import ReadState, UsePurpose


class SupportVerdict(str, Enum):
    SUPPORTED = 'supported'
    UNSUPPORTED = 'unsupported'
    UNAVAILABLE = 'unavailable'


class SupportValidationPort(Protocol):
    def validate(self, request: AIRequest, sources: tuple[SourceVersion, ...],
                 answer: GroundedAnswer) -> SupportVerdict: ...


class UnavailableSupportValidator:
    def validate(self, request, sources, answer):
        return SupportVerdict.UNAVAILABLE


class ResultState(str, Enum):
    SUPPORTED = 'supported'
    UNSUPPORTED = 'unsupported'
    AMBIGUOUS = 'ambiguous'
    UNAVAILABLE = 'unavailable'
    RETRYABLE = 'retryable'


@dataclass(frozen=True)
class AnswerCitation:
    label: str
    excerpt: str


@dataclass(frozen=True)
class VisitorAnswer:
    question: str
    state: ResultState
    text: str
    citations: tuple[AnswerCitation, ...] = ()


MESSAGES = {
    ResultState.UNSUPPORTED: 'The shared information does not establish an answer to that question.',
    ResultState.AMBIGUOUS: 'Please clarify the question so it can be answered from the shared information.',
    ResultState.UNAVAILABLE: 'Answers are temporarily unavailable. Your question has been preserved.',
    ResultState.RETRYABLE: 'The answer could not be completed. Your question has been preserved; please try again.',
}


class MemberVisitorAiService:
    def __init__(self, sources: EligibleSourcesPort, currentness: CurrentnessPort,
                 gateway: AIFoundationGateway, *, support: SupportValidationPort | None = None):
        self.sources, self.currentness, self.gateway = sources, currentness, gateway
        self.support = support or UnavailableSupportValidator()

    def ask_guest(self, *, slug: str, question: str, request_id: str) -> VisitorAnswer:
        return self._ask(lambda: self.sources.load_guest(slug), question, request_id)

    def ask_preview(self, *, binding: PreviewBinding, question: str, request_id: str) -> VisitorAnswer:
        return self._ask(lambda: self.sources.load_preview(binding), question, request_id)

    def _ask(self, load, question, request_id):
        def boundary(state):
            return VisitorAnswer(question, state, MESSAGES[state])
        try:
            bundle = load()
            if type(bundle) is not EligibleSources:
                return boundary(ResultState.UNAVAILABLE)
            preview = bundle.context.purpose is UsePurpose.OWNER_VISITOR_AI_PREVIEW
            if bundle.context.purpose not in {UsePurpose.VISITOR_AI, UsePurpose.OWNER_VISITOR_AI_PREVIEW}:
                return boundary(ResultState.UNAVAILABLE)
            request = AIRequest(request_id, 'member_visitor_ai_preview' if preview else 'member_visitor_ai',
                                Purpose.PUBLIC_PROFILE_ANSWER, Audience.OWNER if preview else Audience.PUBLIC,
                                bundle.context.subject_key, question,
                                bundle.preview.candidate_digest if preview else bundle.authority_digest)
        except Exception:
            return boundary(ResultState.UNAVAILABLE)
        if not bundle.sources:
            return boundary(ResultState.UNSUPPORTED)
        try:
            answer = self.gateway.answer(request, bundle.sources).answer
            # Keep this independent check at the release boundary even when a
            # composition accidentally injects a nonstandard gateway.
            validate_grounded_answer(request, bundle.sources, answer)
            if answer.state is AnswerState.UNAVAILABLE:
                return boundary(ResultState.RETRYABLE)
            if answer.state in {AnswerState.NOT_ESTABLISHED, AnswerState.REFUSED}:
                return boundary(ResultState.UNSUPPORTED)
            if answer.state is AnswerState.AMBIGUOUS:
                return boundary(ResultState.AMBIGUOUS)
            verdict = self.support.validate(request, bundle.sources, answer)
            if verdict is SupportVerdict.UNAVAILABLE:
                return boundary(ResultState.UNAVAILABLE)
            if verdict is not SupportVerdict.SUPPORTED:
                return boundary(ResultState.UNSUPPORTED)
            # Build the entire safe public representation before the final SQL
            # read. No free-form follow-ups, model metadata, private URLs or
            # internal source IDs are exposed.
            citations = tuple(AnswerCitation('Approved saved information', citation.excerpt)
                              for claim in answer.claims for citation in claim.citations)
            result = VisitorAnswer(question, ResultState.SUPPORTED, answer.summary, citations)
            if self.currentness.recheck(bundle) is not ReadState.CURRENT:
                return boundary(ResultState.RETRYABLE)
            return result
        except Exception:
            return boundary(ResultState.RETRYABLE)
