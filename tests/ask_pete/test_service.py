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
    GroundingValidationError,
    ProviderUnavailableError,
)
from services.ask_pete.errors import AskPeteRequestError, AskPeteResponseError
from services.ask_pete.manifest import load_public_source_catalog
from services.ask_pete.service import AskPeteService


ROOT = Path(__file__).resolve().parents[2]


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


class StaticProvider:
    def __init__(self, factory) -> None:
        self.factory = factory
        self.calls = []

    def answer(self, request, sources):
        self.calls.append((request, sources))
        return self.factory(request, sources)


class FailingProvider:
    def answer(self, _request, _sources):
        raise ProviderUnavailableError("provider unavailable")


class AskPeteServiceTests(TestCase):
    def test_evidence_answer_serializes_exact_openable_source_locator(self) -> None:
        def factory(_request, sources):
            source = next(
                item
                for item in sources
                if item.source_version_key == "ask-pete:skill:mbse:v1"
            )
            claim_id = "mbse-1"
            needle = "model-based systems engineering"
            return GroundedAnswer(
                answer_id="evidence-1",
                state=AnswerState.SUPPORTED,
                summary="Pete has approved public evidence of applied MBSE work.",
                claims=(
                    AnswerClaim(
                        claim_id=claim_id,
                        text="Pete has documented MBSE application.",
                        kind=AnswerKind.EVIDENCE,
                        state=AnswerState.SUPPORTED,
                        citations=(citation_for(source, claim_id=claim_id, needle=needle),),
                    ),
                ),
            )

        provider = StaticProvider(factory)
        service = AskPeteService(catalog=catalog(), provider=provider)
        result = service.answer(
            "Show evidence of Pete's MBSE work.",
            context_key="skill:mbse",
            request_id="request-evidence-1",
        )

        payload = result.payload
        self.assertEqual(payload["purpose"], "evidence_finder")
        self.assertEqual(payload["response"], payload["summary"])
        self.assertEqual(payload["source_summary"]["used_count"], 1)
        self.assertEqual(
            payload["claims"][0]["support_label"],
            "Supported by approved public information",
        )
        citation = payload["claims"][0]["citations"][0]
        self.assertEqual(citation["excerpt"], "model-based systems engineering")
        self.assertEqual(citation["locator"]["anchor"], "r2-skill-panel-mbse")
        self.assertEqual(
            citation["locator"]["href"],
            "/petec/resume#r2-skill-panel-mbse",
        )
        self.assertEqual(provider.calls[0][1][0].source_version_key, "ask-pete:skill:mbse:v1")
        self.assertTrue(result.diagnostic.context_applied)

    def test_unknown_answer_exposes_honest_current_contact_handoff(self) -> None:
        def factory(request, _sources):
            return GroundedAnswer(
                answer_id="unknown-1",
                state=AnswerState.NOT_ESTABLISHED,
                summary="That experience is not established in Pete's approved public information.",
                claims=(
                    AnswerClaim(
                        claim_id="boundary-1",
                        text="The requested experience is not publicly established.",
                        kind=AnswerKind.BOUNDARY,
                        state=AnswerState.NOT_ESTABLISHED,
                        limitation="No approved public source answers this question.",
                    ),
                ),
                handoff=HandoffProposal(
                    reason=HandoffReason.MISSING_PUBLIC_EVIDENCE,
                    question=request.question,
                ),
            )

        result = AskPeteService(
            catalog=catalog(),
            provider=StaticProvider(factory),
        ).answer("Has Pete built a submarine?", request_id="request-unknown-1")

        self.assertEqual(result.payload["state"], "not_established")
        self.assertEqual(result.payload["sources_used"], [])
        self.assertEqual(result.payload["handoff"]["href"], "/petec/contact")
        self.assertIn("Nothing is sent automatically", result.payload["handoff"]["delivery_note"])
        self.assertIn("not live", result.payload["handoff"]["delivery_note"])

    def test_unknown_context_is_rejected_before_provider(self) -> None:
        provider = StaticProvider(lambda _request, _sources: None)
        service = AskPeteService(catalog=catalog(), provider=provider)

        with self.assertRaisesRegex(
            AskPeteRequestError,
            "outside the public source manifest",
        ):
            service.answer("Tell me more.", context_key="skill:classified")
        self.assertEqual(provider.calls, [])

    def test_citation_outside_supplied_manifest_is_rejected(self) -> None:
        def factory(_request, _sources):
            return GroundedAnswer(
                answer_id="bad-citation",
                state=AnswerState.SUPPORTED,
                summary="Unsupported source linkage.",
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

        service = AskPeteService(catalog=catalog(), provider=StaticProvider(factory))
        with self.assertRaisesRegex(
            GroundingValidationError,
            "not supplied",
        ):
            service.answer("What supports this?", request_id="request-bad-source")

    def test_provider_unavailable_degrades_without_source_or_question_payload(self) -> None:
        question = "A unique visitor question that must not enter diagnostics."
        service = AskPeteService(catalog=catalog(), provider=FailingProvider())
        result = service.answer(question, request_id="request-unavailable-1")

        self.assertEqual(result.payload["state"], "unavailable")
        self.assertEqual(result.payload["claims"], [])
        self.assertEqual(result.diagnostic.outcome, "degraded")
        diagnostic_text = repr(result.diagnostic)
        self.assertNotIn(question, diagnostic_text)
        self.assertNotIn("petercarter19@gmail.com", diagnostic_text)
        self.assertNotIn("Model-Based Systems Engineering", diagnostic_text)

    def test_recruiter_brief_must_meet_the_flagship_quality_contract(self) -> None:
        def factory(_request, sources):
            source = sources[0]
            return GroundedAnswer(
                answer_id="too-thin",
                state=AnswerState.SUPPORTED,
                summary="Pete is an engineer.",
                claims=(
                    AnswerClaim(
                        claim_id="thin-1",
                        text="Pete is an engineer.",
                        kind=AnswerKind.EVIDENCE,
                        state=AnswerState.SUPPORTED,
                        citations=(
                            citation_for(source, claim_id="thin-1", needle="Pete Carter"),
                        ),
                    ),
                ),
            )

        service = AskPeteService(catalog=catalog(), provider=StaticProvider(factory))
        with self.assertRaisesRegex(
            AskPeteResponseError,
            "product quality contract",
        ):
            service.answer(
                "Give me Pete's 60-second recruiter brief.",
                request_id="request-thin-brief",
            )

    def test_recruiter_brief_can_satisfy_the_complete_contract(self) -> None:
        def factory(request, sources):
            selected = sources[:3]
            claims = []
            needles = ("Pete Carter", "Employer:", "Employer:")
            for index, (source, needle) in enumerate(zip(selected, needles), 1):
                claim_id = f"evidence-{index}"
                claims.append(
                    AnswerClaim(
                        claim_id=claim_id,
                        text=f"Consequential evidence claim {index}.",
                        kind=AnswerKind.EVIDENCE,
                        state=AnswerState.SUPPORTED,
                        citations=(
                            citation_for(source, claim_id=claim_id, needle=needle),
                        ),
                    )
                )
            claims.append(
                AnswerClaim(
                    claim_id="boundary-1",
                    text="A specific opening has not been evaluated.",
                    kind=AnswerKind.BOUNDARY,
                    state=AnswerState.NOT_ESTABLISHED,
                    limitation="No role requirements were supplied.",
                )
            )
            return GroundedAnswer(
                answer_id="brief-complete",
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

        result = AskPeteService(
            catalog=catalog(),
            provider=StaticProvider(factory),
        ).answer(
            "Give me Pete's 60-second recruiter brief.",
            request_id="request-complete-brief",
        )

        self.assertEqual(result.payload["purpose"], "recruiter_brief")
        self.assertEqual(result.payload["source_summary"]["used_count"], 3)
        self.assertEqual(len(result.payload["follow_up_questions"]), 2)
        self.assertIsNotNone(result.payload["handoff"])
