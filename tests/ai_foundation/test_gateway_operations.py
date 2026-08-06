from unittest import TestCase

from services.ai_foundation import (
    AIFoundationGateway,
    AIRequest,
    AnswerClaim,
    AnswerKind,
    AnswerState,
    Audience,
    Citation,
    ExecutionLimits,
    GroundedAnswer,
    Purpose,
    SourceVersion,
)
from services.ai_foundation.errors import (
    AnswerContractError,
    ExecutionLimitError,
    GroundingValidationError,
    ProviderUnavailableError,
    SourceAuthorizationError,
)


def request(*, question: str = "Summarize the approved evidence.") -> AIRequest:
    return AIRequest(
        request_id="operations-request-1",
        product="ask_pete",
        purpose=Purpose.RECRUITER_BRIEF,
        audience=Audience.PUBLIC,
        subject_key="pete",
        question=question,
    )


def source(
    *,
    audience: Audience = Audience.PUBLIC,
    source_key: str = "leadership",
    content: str = "Pete led cross-functional engineering work.",
) -> SourceVersion:
    return SourceVersion.approved(
        source_version_key=f"{source_key}:v1",
        source_key=source_key,
        version=1,
        subject_key="pete",
        title="Approved leadership evidence",
        content=content,
        allowed_audiences=frozenset({audience}),
        allowed_purposes=frozenset({Purpose.RECRUITER_BRIEF}),
    )


def answer(item: SourceVersion) -> GroundedAnswer:
    excerpt = "cross-functional engineering"
    start = item.content.index(excerpt)
    return GroundedAnswer(
        answer_id="operations-answer-1",
        state=AnswerState.SUPPORTED,
        summary="Pete has approved evidence of engineering leadership.",
        claims=(
            AnswerClaim(
                claim_id="leadership-claim",
                text="Pete led cross-functional engineering work.",
                kind=AnswerKind.EVIDENCE,
                state=AnswerState.SUPPORTED,
                citations=(
                    Citation(
                        claim_id="leadership-claim",
                        source_version_key=item.source_version_key,
                        start=start,
                        end=start + len(excerpt),
                        excerpt=excerpt,
                    ),
                ),
            ),
        ),
    )


class Provider:
    def __init__(self, result) -> None:
        self.result = result
        self.calls = 0

    def answer(self, _request, _sources):
        self.calls += 1
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class GatewayOperationsTests(TestCase):
    def test_question_budget_fails_before_provider_and_emits_safe_trace(self):
        item = source()
        provider = Provider(answer(item))
        traces = []
        gateway = AIFoundationGateway(
            provider,
            limits=ExecutionLimits(maximum_question_characters=10),
            trace_sink=traces.append,
        )
        oversized_question = "private question that is intentionally too long"

        with self.assertRaises(ExecutionLimitError):
            gateway.answer(request(question=oversized_question), (item,))

        self.assertEqual(0, provider.calls)
        self.assertEqual(1, len(traces))
        self.assertEqual("failed", traces[0].outcome)
        self.assertEqual("execution_limit", traces[0].error_category)
        self.assertFalse(traces[0].provider_called)
        self.assertIsNone(traces[0].answer_state)
        self.assertNotIn(oversized_question, repr(traces[0]))
        self.assertNotIn(item.content, repr(traces[0]))

    def test_source_count_budget_fails_before_authorization_or_provider(self):
        item = source()
        provider = Provider(answer(item))
        traces = []
        gateway = AIFoundationGateway(
            provider,
            limits=ExecutionLimits(maximum_sources=1),
            trace_sink=traces.append,
        )

        with self.assertRaises(ExecutionLimitError):
            gateway.answer(request(), (item, item))

        self.assertEqual(0, provider.calls)
        self.assertEqual(0, traces[0].source_count)

    def test_single_source_character_budget_fails_before_provider(self):
        item = source(content="x" * 11)
        provider = Provider(None)

        with self.assertRaises(ExecutionLimitError):
            AIFoundationGateway(
                provider,
                limits=ExecutionLimits(
                    maximum_single_source_characters=10,
                    maximum_total_source_characters=20,
                ),
            ).answer(request(), (item,))

        self.assertEqual(0, provider.calls)

    def test_total_source_character_budget_fails_before_provider(self):
        first = source(source_key="first", content="a" * 6)
        second = source(source_key="second", content="b" * 6)
        provider = Provider(None)

        with self.assertRaises(ExecutionLimitError):
            AIFoundationGateway(
                provider,
                limits=ExecutionLimits(
                    maximum_single_source_characters=10,
                    maximum_total_source_characters=10,
                ),
            ).answer(request(), (first, second))

        self.assertEqual(0, provider.calls)

    def test_authorization_failure_is_observable_without_source_payload(self):
        item = source(audience=Audience.OWNER)
        provider = Provider(answer(item))
        traces = []

        with self.assertRaises(SourceAuthorizationError):
            AIFoundationGateway(provider, trace_sink=traces.append).answer(
                request(),
                (item,),
            )

        self.assertEqual(0, provider.calls)
        self.assertEqual("source_authorization", traces[0].error_category)
        self.assertFalse(traces[0].provider_called)
        self.assertEqual(0, traces[0].source_count)
        self.assertNotIn(item.content, repr(traces[0]))

    def test_malformed_provider_output_emits_contract_failure_trace(self):
        item = source()
        provider = Provider({"unknown": "do not retain this output"})
        traces = []

        with self.assertRaises(AnswerContractError):
            AIFoundationGateway(provider, trace_sink=traces.append).answer(
                request(),
                (item,),
            )

        self.assertEqual("answer_contract", traces[0].error_category)
        self.assertTrue(traces[0].provider_called)
        self.assertNotIn("do not retain this output", repr(traces[0]))

    def test_invalid_citation_emits_grounding_failure_trace(self):
        item = source()
        valid = answer(item)
        claim = valid.claims[0]
        bad = GroundedAnswer(
            answer_id=valid.answer_id,
            state=valid.state,
            summary=valid.summary,
            claims=(
                AnswerClaim(
                    claim_id=claim.claim_id,
                    text=claim.text,
                    kind=claim.kind,
                    state=claim.state,
                    citations=(
                        Citation(
                            claim_id=claim.claim_id,
                            source_version_key=item.source_version_key,
                            start=0,
                            end=4,
                            excerpt="fake",
                        ),
                    ),
                ),
            ),
        )
        traces = []

        with self.assertRaises(GroundingValidationError):
            AIFoundationGateway(
                Provider(bad),
                trace_sink=traces.append,
            ).answer(request(), (item,))

        self.assertEqual("grounding_validation", traces[0].error_category)
        self.assertTrue(traces[0].provider_called)

    def test_provider_unavailable_is_degraded_not_falsely_successful(self):
        traces = []
        result = AIFoundationGateway(
            Provider(ProviderUnavailableError("timeout")),
            trace_sink=traces.append,
        ).answer(request(), (source(),))

        self.assertEqual(AnswerState.UNAVAILABLE, result.answer.state)
        self.assertEqual("degraded", result.trace.outcome)
        self.assertEqual(result.trace, traces[0])

    def test_unexpected_provider_failure_is_classified_and_reraised(self):
        traces = []
        provider_message = "provider payload must not enter diagnostics"

        with self.assertRaisesRegex(ValueError, provider_message):
            AIFoundationGateway(
                Provider(ValueError(provider_message)),
                trace_sink=traces.append,
            ).answer(request(), (source(),))

        self.assertEqual(
            "unexpected_provider_failure",
            traces[0].error_category,
        )
        self.assertNotIn(provider_message, repr(traces[0]))

    def test_trace_sink_failure_does_not_change_valid_answer(self):
        item = source()

        def broken_sink(_trace):
            raise RuntimeError("diagnostic sink failed")

        result = AIFoundationGateway(
            Provider(answer(item)),
            trace_sink=broken_sink,
        ).answer(request(), (item,))

        self.assertEqual(AnswerState.SUPPORTED, result.answer.state)
        self.assertEqual("completed", result.trace.outcome)


class RuntimeContractValidationTests(TestCase):
    def test_execution_limits_reject_reversed_source_budgets(self):
        with self.assertRaisesRegex(ValueError, "cannot exceed"):
            ExecutionLimits(
                maximum_single_source_characters=20,
                maximum_total_source_characters=10,
            )

    def test_trace_identifiers_reject_control_characters(self):
        with self.assertRaisesRegex(ValueError, "bounded identifier"):
            AIRequest(
                request_id="request\nforged-trace-line",
                product="ask_pete",
                purpose=Purpose.RECRUITER_BRIEF,
                audience=Audience.PUBLIC,
                subject_key="pete",
                question="Question",
            )

    def test_request_rejects_untyped_audience_and_purpose(self):
        with self.assertRaisesRegex(ValueError, "purpose must be a Purpose"):
            AIRequest(
                request_id="bad-request",
                product="ask_pete",
                purpose="recruiter_brief",
                audience=Audience.PUBLIC,
                subject_key="pete",
                question="Question",
            )

    def test_source_rejects_untyped_permission_sets(self):
        item = source()
        with self.assertRaisesRegex(ValueError, "allowed audiences"):
            SourceVersion(
                source_version_key=item.source_version_key,
                source_key=item.source_key,
                version=item.version,
                subject_key=item.subject_key,
                title=item.title,
                content=item.content,
                content_sha256=item.content_sha256,
                allowed_audiences=frozenset({"public"}),
                allowed_purposes=item.allowed_purposes,
            )

    def test_source_rejects_malformed_content_digest(self):
        item = source()
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            SourceVersion(
                source_version_key=item.source_version_key,
                source_key=item.source_key,
                version=item.version,
                subject_key=item.subject_key,
                title=item.title,
                content=item.content,
                content_sha256="not-a-digest",
                allowed_audiences=item.allowed_audiences,
                allowed_purposes=item.allowed_purposes,
            )
