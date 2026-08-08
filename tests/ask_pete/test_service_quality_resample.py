"""One fresh sample when the product quality contract refuses an answer.

The live recruiter_brief failure was `boundary_claim_required`: a grounded,
citation-clean answer that simply did not contain the boundary claim the
flagship contract requires. That refusal comes from
`services/ask_pete/quality.py`, which runs *after* the gateway has finished, so
the provider's corrective retry could never see it — the visitor got a 502 for
a recoverable shortfall.

The service now takes exactly one more sample. It is a resample, not a
correction: `AIRequest` has no feedback field, `services/ai_foundation/` is not
this package's to change, and writing the complaint into `question` would
corrupt the record of what the visitor actually asked. So this is a bet on
sampling variance, worth taking once and never twice. These tests hold the
bound in both directions — a recoverable shortfall is recovered, and a
persistent one still fails closed at two rounds.
"""

from pathlib import Path
from unittest import TestCase

from services.ai_foundation import (
    AnswerClaim,
    AnswerKind,
    AnswerState,
    Citation,
    GroundedAnswer,
    HandoffProposal,
    HandoffReason,
)
from services.ai_foundation.errors import (
    AnswerContractError,
    ExecutionLimitError,
    GroundingValidationError,
    ProviderUnavailableError,
    SourceAuthorizationError,
)
from services.ask_pete.errors import AskPeteResponseError, PublicSourceManifestError
from services.ask_pete.manifest import load_public_source_catalog
from services.ask_pete.service import (
    MAXIMUM_QUALITY_ROUNDS,
    RESAMPLED_REFUSALS,
    AskPeteService,
)


ROOT = Path(__file__).resolve().parents[2]

BRIEF_QUESTION = "Give me Pete's 60-second recruiter brief."


def catalog():
    return load_public_source_catalog(
        manifest_path=ROOT / "data" / "ai_sources" / "ask_pete_public_v1.json",
        resume_path=ROOT / "static" / "data" / "resume_data.json",
    )


def citation_for(source, *, claim_id: str, needle: str) -> Citation:
    start = source.content.index(needle)
    return Citation(
        claim_id=claim_id,
        source_version_key=source.source_version_key,
        start=start,
        end=start + len(needle),
        excerpt=needle,
    )


class UnscriptedRound(BaseException):
    """Raised past every handler in the chain, so a third round cannot hide."""


class ScriptedProvider:
    """A provider that answers each gateway round from a fixed script."""

    def __init__(self, *factories) -> None:
        self._factories = list(factories)
        self.calls: list[tuple] = []

    def answer(self, request, sources):
        self.calls.append((request, sources))
        if not self._factories:
            raise UnscriptedRound(
                f"the service opened gateway round {len(self.calls)}; "
                f"at most {MAXIMUM_QUALITY_ROUNDS} are allowed"
            )
        return self._factories.pop(0)(request, sources)


def brief_without_a_boundary_claim(request, sources):
    """The live shape: grounded and cited, but missing the boundary claim.

    Everything the grounding validator checks passes — this is a well-formed
    partially supported answer with real spans — and everything the recruiter
    contract checks passes except `requires_boundary`. That is precisely the
    answer the live run produced and the service turned into a 502.
    """

    claims = []
    for index, (source, needle) in enumerate(
        zip(sources[:3], ("Pete Carter", "Employer:", "Employer:")), 1
    ):
        claim_id = f"evidence-{index}"
        claims.append(
            AnswerClaim(
                claim_id=claim_id,
                text=f"Consequential evidence claim {index}.",
                kind=AnswerKind.EVIDENCE,
                state=AnswerState.SUPPORTED,
                citations=(citation_for(source, claim_id=claim_id, needle=needle),),
            )
        )
    claims.append(
        AnswerClaim(
            claim_id="partial-1",
            text="One documented result is reported without its full context.",
            kind=AnswerKind.EVIDENCE,
            state=AnswerState.PARTIALLY_SUPPORTED,
            citations=(
                citation_for(sources[0], claim_id="partial-1", needle="Pete Carter"),
            ),
            limitation="The approved public record does not state the team size.",
        )
    )
    return GroundedAnswer(
        answer_id="brief-no-boundary",
        state=AnswerState.PARTIALLY_SUPPORTED,
        summary=" ".join(["documented"] * 100),
        claims=tuple(claims),
        follow_up_questions=(
            "How does Pete connect requirements and architecture?",
            "How does Pete lead across organizational boundaries?",
        ),
        handoff=HandoffProposal(
            reason=HandoffReason.HUMAN_JUDGMENT,
            question=request.question,
        ),
    )


def complete_brief(request, sources):
    answer = brief_without_a_boundary_claim(request, sources)
    return GroundedAnswer(
        answer_id="brief-complete",
        state=answer.state,
        summary=answer.summary,
        claims=answer.claims
        + (
            AnswerClaim(
                claim_id="boundary-1",
                text="A specific opening has not been evaluated.",
                kind=AnswerKind.BOUNDARY,
                state=AnswerState.NOT_ESTABLISHED,
                limitation="No role requirements were supplied.",
            ),
        ),
        follow_up_questions=answer.follow_up_questions,
        handoff=answer.handoff,
    )


def ungrounded_answer(_request, _sources):
    return GroundedAnswer(
        answer_id="ungrounded",
        state=AnswerState.SUPPORTED,
        summary="A claim citing a source that was never supplied.",
        claims=(
            AnswerClaim(
                claim_id="bad-1",
                text="A claim.",
                kind=AnswerKind.EVIDENCE,
                state=AnswerState.SUPPORTED,
                citations=(
                    Citation(
                        claim_id="bad-1",
                        source_version_key="private-source:v1",
                        start=0,
                        end=4,
                        excerpt="nope",
                    ),
                ),
            ),
        ),
    )


def supported_answer(_request, sources):
    source = sources[0]
    return GroundedAnswer(
        answer_id="supported",
        state=AnswerState.SUPPORTED,
        summary="The approved public record documents this.",
        claims=(
            AnswerClaim(
                claim_id="supported-1",
                text="A documented claim.",
                kind=AnswerKind.EVIDENCE,
                state=AnswerState.SUPPORTED,
                citations=(
                    citation_for(source, claim_id="supported-1", needle="Pete Carter"),
                ),
            ),
        ),
    )


def undecodable_payload(_request, _sources):
    """A mapping the gateway's decoder refuses, not a GroundedAnswer."""

    return {
        "answer_id": "undecodable",
        "state": "not_established",
        "summary": "That is not established in Pete's approved public information.",
        "claims": [],
        "follow_up_questions": ["Why? " + "x" * 296],
        "handoff": None,
    }


def decodable_payload(_request, _sources):
    return {
        "answer_id": "decodable",
        "state": "not_established",
        "summary": "That is not established in Pete's approved public information.",
        "claims": [],
        "follow_up_questions": [],
        "handoff": None,
    }


def unavailable_provider(_request, _sources):
    raise ProviderUnavailableError("provider unavailable")


def service_for(provider, *, traces: list | None = None) -> AskPeteService:
    return AskPeteService(
        catalog=catalog(),
        provider=provider,
        trace_sink=(traces.append if traces is not None else None),
    )


class OneQualityResampleTests(TestCase):
    def test_a_recoverable_shortfall_is_recovered_on_the_second_round(self) -> None:
        provider = ScriptedProvider(brief_without_a_boundary_claim, complete_brief)
        traces: list = []

        result = service_for(provider, traces=traces).answer(
            BRIEF_QUESTION,
            requested_action="recruiter_brief",
            request_id="request-resample-1",
        )

        self.assertEqual(len(provider.calls), MAXIMUM_QUALITY_ROUNDS)
        self.assertEqual(result.payload["purpose"], "recruiter_brief")
        self.assertEqual(result.payload["state"], "partially_supported")
        self.assertEqual(result.diagnostic.outcome, "completed")
        # The delivered answer is the second sample, not the refused one: it
        # carries the boundary claim the first sample was missing.
        self.assertEqual(len(result.payload["claims"]), 5)
        self.assertIn(
            "not_established",
            [claim["state"] for claim in result.payload["claims"]],
        )
        # Both rounds are traced. The diagnostic describes the one delivered.
        self.assertEqual(len(traces), MAXIMUM_QUALITY_ROUNDS)
        self.assertEqual([trace.outcome for trace in traces], ["completed"] * 2)

    def test_a_persistent_shortfall_fails_closed_after_two_rounds(self) -> None:
        provider = ScriptedProvider(
            brief_without_a_boundary_claim,
            brief_without_a_boundary_claim,
        )

        with self.assertRaisesRegex(
            AskPeteResponseError,
            "boundary_claim_required",
        ):
            service_for(provider).answer(
                BRIEF_QUESTION,
                requested_action="recruiter_brief",
                request_id="request-resample-2",
            )

        self.assertEqual(len(provider.calls), MAXIMUM_QUALITY_ROUNDS)

    def test_an_answer_that_passes_first_time_costs_one_round(self) -> None:
        provider = ScriptedProvider(complete_brief)

        result = service_for(provider).answer(
            BRIEF_QUESTION,
            requested_action="recruiter_brief",
            request_id="request-resample-3",
        )

        self.assertEqual(len(provider.calls), 1)
        self.assertEqual(result.payload["purpose"], "recruiter_brief")

    def test_the_resample_asks_the_same_authorized_question_of_the_same_sources(
        self,
    ) -> None:
        # A resample is a second sample of one request, not a second request.
        # If either the question or the authorized source set moved between
        # rounds, this would be a quiet re-scoping rather than a retry.
        provider = ScriptedProvider(brief_without_a_boundary_claim, complete_brief)

        service_for(provider).answer(
            BRIEF_QUESTION,
            requested_action="recruiter_brief",
            request_id="request-resample-4",
        )
        (first_request, first_sources), (second_request, second_sources) = provider.calls

        self.assertEqual(first_request, second_request)
        self.assertEqual(first_sources, second_sources)


class EveryModelOutputRefusalIsResampledTests(TestCase):
    """Round 4's failures were grounding, not quality.

    `interpretations must state their inferential boundary` and `a supported
    answer may contain only supported claims` are raised by
    `validate_grounded_answer` inside `AIFoundationGateway.answer` — past the
    provider's corrective retry, and not an `AskPeteResponseError`, so the
    first version of this resample did not cover them. All three layers that
    judge the model's own output now share the one resample.
    """

    def test_a_grounding_failure_is_resampled_once(self) -> None:
        provider = ScriptedProvider(ungrounded_answer, supported_answer)
        traces: list = []

        result = service_for(provider, traces=traces).answer(
            "What supports this?",
            request_id="request-resample-8",
        )

        self.assertEqual(len(provider.calls), MAXIMUM_QUALITY_ROUNDS)
        self.assertEqual(result.payload["state"], "supported")
        # The refused round is traced as failed, the delivered one as completed.
        self.assertEqual([trace.outcome for trace in traces], ["failed", "completed"])
        self.assertEqual(traces[0].error_category, "grounding_validation")

    def test_a_persistent_grounding_failure_fails_closed(self) -> None:
        provider = ScriptedProvider(ungrounded_answer, ungrounded_answer)

        with self.assertRaisesRegex(GroundingValidationError, "not supplied"):
            service_for(provider).answer(
                "What supports this?",
                request_id="request-resample-9",
            )

        self.assertEqual(len(provider.calls), MAXIMUM_QUALITY_ROUNDS)

    def test_a_decoder_refusal_escaping_the_gateway_is_resampled_once(self) -> None:
        # A provider adapter may return a plain mapping, which the gateway
        # decodes itself. The shipped adapter now decodes its own answer and
        # corrects it, but nothing in the contract requires that, so the
        # service still covers a decoder refusal arriving from a round.
        provider = ScriptedProvider(undecodable_payload, decodable_payload)

        result = service_for(provider).answer(
            "What is documented?",
            request_id="request-resample-10",
        )

        self.assertEqual(len(provider.calls), MAXIMUM_QUALITY_ROUNDS)
        self.assertEqual(result.payload["state"], "not_established")

    def test_a_persistent_decoder_refusal_fails_closed(self) -> None:
        provider = ScriptedProvider(undecodable_payload, undecodable_payload)

        with self.assertRaisesRegex(
            AnswerContractError,
            "answer.follow_up_question exceeds 300 characters",
        ):
            service_for(provider).answer(
                "What is documented?",
                request_id="request-resample-11",
            )

        self.assertEqual(len(provider.calls), MAXIMUM_QUALITY_ROUNDS)


class WhatIsNeverResampledTests(TestCase):
    def test_the_resampled_classes_are_exactly_the_model_output_ones(self) -> None:
        # The taxonomy, pinned. A refusal that is deterministic in the request
        # or the sources fails identically on a second sample, so paying for
        # one would be pure loss.
        self.assertEqual(
            set(RESAMPLED_REFUSALS),
            {AskPeteResponseError, GroundingValidationError, AnswerContractError},
        )
        for excluded in (
            ProviderUnavailableError,
            SourceAuthorizationError,
            ExecutionLimitError,
            PublicSourceManifestError,
        ):
            with self.subTest(excluded.__name__):
                self.assertFalse(issubclass(excluded, RESAMPLED_REFUSALS))

    def test_an_execution_limit_is_not_resampled(self) -> None:
        # Deterministic in the request: the question is too long on the second
        # round for exactly the reason it was too long on the first. Counted by
        # traces rather than provider calls, because this refusal happens
        # before the round ever reaches the provider.
        provider = ScriptedProvider(supported_answer)
        traces: list = []

        with self.assertRaisesRegex(ExecutionLimitError, "question exceeds"):
            service_for(provider, traces=traces).answer(
                "x" * 1_001,
                request_id="request-resample-12",
            )

        self.assertEqual(len(traces), 1)
        self.assertEqual(traces[0].error_category, "execution_limit")
        self.assertEqual(provider.calls, [])

    def test_an_unavailable_provider_is_not_resampled(self) -> None:
        # The gateway degrades this to the honest unavailable answer, which
        # `validate_product_quality` passes over, so no resample is triggered
        # and a paid call is not spent on a provider that just failed.
        provider = ScriptedProvider(unavailable_provider)

        result = service_for(provider).answer(
            BRIEF_QUESTION,
            requested_action="recruiter_brief",
            request_id="request-resample-6",
        )

        self.assertEqual(result.payload["state"], "unavailable")
        self.assertEqual(result.diagnostic.outcome, "degraded")
        self.assertEqual(len(provider.calls), 1)

    def test_a_purpose_with_no_quality_contract_is_never_resampled(self) -> None:
        # The same answer that fails the recruiter contract is a perfectly good
        # general answer. Nothing about a general question can trigger a
        # resample, because nothing about it can raise AskPeteResponseError.
        provider = ScriptedProvider(brief_without_a_boundary_claim)

        result = service_for(provider).answer(
            BRIEF_QUESTION,
            request_id="request-resample-7",
        )

        self.assertEqual(result.payload["purpose"], "public_profile_answer")
        self.assertEqual(len(provider.calls), 1)
