from dataclasses import asdict
from unittest import TestCase

from services.ai_foundation import (
    AIFoundationGateway,
    AIRequest,
    AnswerClaim,
    AnswerKind,
    AnswerState,
    Audience,
    Citation,
    GroundedAnswer,
    Purpose,
    SourceVersion,
)
from services.ai_foundation.errors import (
    GroundingValidationError,
    ProviderUnavailableError,
    SourceAuthorizationError,
)


PUBLIC_PURPOSES = frozenset(
    {
        Purpose.PUBLIC_PROFILE_ANSWER,
        Purpose.RECRUITER_BRIEF,
        Purpose.EVIDENCE_FINDER,
        Purpose.INTERVIEW_PREPARATION,
    }
)


def request() -> AIRequest:
    return AIRequest(
        request_id="request-1",
        product="ask_pete",
        purpose=Purpose.RECRUITER_BRIEF,
        audience=Audience.PUBLIC,
        subject_key="pete",
        question="Give me Pete's recruiter brief.",
    )


def source(*, audience: Audience = Audience.PUBLIC) -> SourceVersion:
    return SourceVersion.approved(
        source_version_key="role-air-force:v3",
        source_key="role-air-force",
        version=3,
        subject_key="pete",
        title="Air Force engineering leadership",
        content="Pete led a cross-functional engineering organization.",
        allowed_audiences=frozenset({audience}),
        allowed_purposes=PUBLIC_PURPOSES,
    )


def supported_answer(item: SourceVersion) -> GroundedAnswer:
    excerpt = "cross-functional engineering"
    start = item.content.index(excerpt)
    return GroundedAnswer(
        answer_id="answer-1",
        state=AnswerState.SUPPORTED,
        summary="Pete has documented engineering leadership.",
        claims=(
            AnswerClaim(
                claim_id="claim-1",
                text="Pete led cross-functional engineering work.",
                kind=AnswerKind.EVIDENCE,
                state=AnswerState.SUPPORTED,
                citations=(
                    Citation(
                        claim_id="claim-1",
                        source_version_key=item.source_version_key,
                        start=start,
                        end=start + len(excerpt),
                        excerpt=excerpt,
                    ),
                ),
            ),
        ),
    )


class FakeProvider:
    def __init__(self, answer: GroundedAnswer) -> None:
        self.result = answer
        self.calls = 0

    def answer(self, _request, _sources):
        self.calls += 1
        return self.result


class UnavailableProvider:
    def answer(self, _request, _sources):
        raise ProviderUnavailableError("provider timeout")


class GroundingContractTests(TestCase):
    def test_exact_authorized_citation_passes(self):
        item = source()
        provider = FakeProvider(supported_answer(item))
        result = AIFoundationGateway(provider).answer(request(), (item,))
        self.assertEqual(1, provider.calls)
        self.assertEqual(AnswerState.SUPPORTED, result.answer.state)
        self.assertEqual(1, result.trace.citation_count)

    def test_unauthorized_source_is_blocked_before_provider_call(self):
        item = source(audience=Audience.OWNER)
        provider = FakeProvider(supported_answer(item))
        with self.assertRaises(SourceAuthorizationError):
            AIFoundationGateway(provider).answer(request(), (item,))
        self.assertEqual(0, provider.calls)

    def test_stale_source_digest_is_blocked_before_provider_call(self):
        item = source()
        stale = SourceVersion(
            source_version_key=item.source_version_key,
            source_key=item.source_key,
            version=item.version,
            subject_key=item.subject_key,
            title=item.title,
            content=item.content + " Changed.",
            content_sha256=item.content_sha256,
            allowed_audiences=item.allowed_audiences,
            allowed_purposes=item.allowed_purposes,
        )
        provider = FakeProvider(supported_answer(stale))
        with self.assertRaises(SourceAuthorizationError):
            AIFoundationGateway(provider).answer(request(), (stale,))
        self.assertEqual(0, provider.calls)

    def test_mismatched_excerpt_is_rejected(self):
        item = source()
        citation = supported_answer(item).claims[0].citations[0]
        bad = GroundedAnswer(
            answer_id="answer-1",
            state=AnswerState.SUPPORTED,
            summary="Unsupported assertion.",
            claims=(
                AnswerClaim(
                    claim_id="claim-1",
                    text="Pete led cross-functional engineering work.",
                    kind=AnswerKind.EVIDENCE,
                    state=AnswerState.SUPPORTED,
                    citations=(
                        Citation(
                            claim_id="claim-1",
                            source_version_key=citation.source_version_key,
                            start=citation.start,
                            end=citation.end,
                            excerpt="invented supporting text",
                        ),
                    ),
                ),
            ),
        )
        with self.assertRaises(GroundingValidationError):
            AIFoundationGateway(FakeProvider(bad)).answer(request(), (item,))

    def test_supported_claim_without_citation_is_rejected(self):
        item = source()
        answer = GroundedAnswer(
            answer_id="answer-1",
            state=AnswerState.SUPPORTED,
            summary="Unsupported assertion.",
            claims=(
                AnswerClaim(
                    claim_id="claim-1",
                    text="Pete definitely did something.",
                    kind=AnswerKind.EVIDENCE,
                    state=AnswerState.SUPPORTED,
                ),
            ),
        )
        with self.assertRaises(GroundingValidationError):
            AIFoundationGateway(FakeProvider(answer)).answer(request(), (item,))

    def test_partial_support_requires_visible_limitation(self):
        item = source()
        citations = supported_answer(item).claims[0].citations
        answer = GroundedAnswer(
            answer_id="answer-1",
            state=AnswerState.PARTIALLY_SUPPORTED,
            summary="The record supports only part of this.",
            claims=(
                AnswerClaim(
                    claim_id="claim-1",
                    text="Pete has related leadership evidence.",
                    kind=AnswerKind.INTERPRETATION,
                    state=AnswerState.PARTIALLY_SUPPORTED,
                    citations=citations,
                ),
            ),
        )
        with self.assertRaises(GroundingValidationError):
            AIFoundationGateway(FakeProvider(answer)).answer(request(), (item,))

    def test_not_established_boundary_cannot_use_a_proving_citation(self):
        item = source()
        citations = supported_answer(item).claims[0].citations
        answer = GroundedAnswer(
            answer_id="answer-1",
            state=AnswerState.NOT_ESTABLISHED,
            summary="The public record does not establish this.",
            claims=(
                AnswerClaim(
                    claim_id="claim-1",
                    text="Specific program scale is not publicly established.",
                    kind=AnswerKind.BOUNDARY,
                    state=AnswerState.NOT_ESTABLISHED,
                    citations=citations,
                    limitation="The approved source does not name that scale.",
                ),
            ),
        )
        with self.assertRaises(GroundingValidationError):
            AIFoundationGateway(FakeProvider(answer)).answer(request(), (item,))

    def test_supported_overall_state_cannot_hide_partial_claim(self):
        item = source()
        citations = supported_answer(item).claims[0].citations
        answer = GroundedAnswer(
            answer_id="answer-1",
            state=AnswerState.SUPPORTED,
            summary="Incorrectly labelled as fully supported.",
            claims=(
                AnswerClaim(
                    claim_id="claim-1",
                    text="Only part of this interpretation is established.",
                    kind=AnswerKind.INTERPRETATION,
                    state=AnswerState.PARTIALLY_SUPPORTED,
                    citations=citations,
                    limitation="The public source does not establish the full scope.",
                ),
            ),
        )
        with self.assertRaises(GroundingValidationError):
            AIFoundationGateway(FakeProvider(answer)).answer(request(), (item,))

    def test_cross_subject_source_is_blocked_before_provider_call(self):
        item = source()
        other_subject = SourceVersion(
            source_version_key=item.source_version_key,
            source_key=item.source_key,
            version=item.version,
            subject_key="another-member",
            title=item.title,
            content=item.content,
            content_sha256=item.content_sha256,
            allowed_audiences=item.allowed_audiences,
            allowed_purposes=item.allowed_purposes,
        )
        provider = FakeProvider(supported_answer(other_subject))
        with self.assertRaises(SourceAuthorizationError):
            AIFoundationGateway(provider).answer(request(), (other_subject,))
        self.assertEqual(0, provider.calls)

    def test_provider_failure_returns_useful_unavailable_state(self):
        result = AIFoundationGateway(UnavailableProvider()).answer(
            request(),
            (source(),),
        )
        self.assertEqual(AnswerState.UNAVAILABLE, result.answer.state)
        self.assertIsNotNone(result.answer.handoff)
        self.assertEqual("provider_unavailable", result.trace.error_category)

    def test_trace_contract_has_no_payload_fields_or_values(self):
        item = source()
        result = AIFoundationGateway(
            FakeProvider(supported_answer(item))
        ).answer(request(), (item,))
        trace = asdict(result.trace)
        forbidden = {"question", "prompt", "content", "excerpt", "answer", "email"}
        self.assertTrue(forbidden.isdisjoint(trace))
        serialized = repr(trace)
        self.assertNotIn(request().question, serialized)
        self.assertNotIn(item.content, serialized)
