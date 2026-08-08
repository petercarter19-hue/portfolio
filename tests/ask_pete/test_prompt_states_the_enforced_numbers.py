"""Every number the server enforces is a number the prompt states.

Live verification with the excerpt fixes in place got two of five real-provider
cases through and failed three on numbers the model could not see:

- `answer.follow_up_question exceeds 300 characters` on two questions — a
  decoder ceiling the prompt never mentioned.
- `summary_below_minimum_words` on the recruiter brief — the prompt did state
  100 to 140 words, but the compactness paragraph read as permission to go
  shorter, and the model took it.

Both are the same defect: the model was asked to satisfy a bound it had to
guess at, or to reconcile a floor with a brevity preference that never said
which one wins. This file holds the fix from both ends — the prompt quotes the
real ceilings, and the floors it quotes are checked against what
`quality.py` and `evaluation.py` actually refuse, so the prompt and the server
cannot drift apart silently.
"""

from pathlib import Path
from unittest import TestCase

from services.ai_foundation import (
    AIRequest,
    AnswerClaim,
    AnswerKind,
    AnswerState,
    Audience,
    Citation,
    GroundedAnswer,
    HandoffProposal,
    HandoffReason,
    Purpose,
    SourceVersion,
    validate_grounded_answer,
)
from services.ai_foundation.errors import GroundingValidationError
from services.ai_foundation.codec import (
    MAX_CITATIONS_PER_CLAIM,
    MAX_CLAIM_CHARS,
    MAX_CLAIMS,
    MAX_EXCERPT_CHARS,
    MAX_FOLLOW_UP_CHARS,
    MAX_FOLLOW_UPS,
    MAX_LIMITATION_CHARS,
    MAX_SUMMARY_CHARS,
)
from services.ask_pete.errors import AskPeteResponseError
from services.ask_pete.quality import validate_product_quality


ROOT = Path(__file__).resolve().parents[2]
PROMPT_PATH = ROOT / "prompts" / "ask_pete" / "grounded_public_v1.md"

# The numbers the prompt now states for recruiter_brief.
RECRUITER_MINIMUM_SUMMARY_WORDS = 100
RECRUITER_MAXIMUM_SUMMARY_WORDS = 140
RECRUITER_MINIMUM_CLAIMS = 4
RECRUITER_MINIMUM_CITATIONS = 3
RECRUITER_MINIMUM_FOLLOW_UPS = 2

# The numbers the prompt now states for the two conditional purposes.
INTERVIEW_MINIMUM_FOLLOW_UPS = 3
CONDITIONAL_MINIMUM_CLAIMS = 1
CONDITIONAL_MINIMUM_CITATIONS = 1


def summary_of(word_count: int) -> str:
    """A summary the server will count as exactly `word_count` words.

    `evaluate_answer` counts `summary.split()`, so whitespace-separated tokens
    are the unit the prompt has to name.
    """

    return " ".join(["evidence"] * word_count)


def claim(
    claim_id: str,
    *,
    kind: AnswerKind = AnswerKind.EVIDENCE,
    state: AnswerState = AnswerState.SUPPORTED,
    citations: int = 0,
) -> AnswerClaim:
    return AnswerClaim(
        claim_id=claim_id,
        text="A documented claim about the subject's work.",
        kind=kind,
        state=state,
        citations=tuple(
            Citation(
                claim_id=claim_id,
                source_version_key="source:v1",
                start=0,
                end=14,
                excerpt="Evidence text.",
            )
            for _ in range(citations)
        ),
        limitation=None,
    )


def recruiter_answer(
    *,
    summary_words: int = RECRUITER_MINIMUM_SUMMARY_WORDS,
    claim_count: int = RECRUITER_MINIMUM_CLAIMS,
    citation_count: int = RECRUITER_MINIMUM_CITATIONS,
    follow_ups: int = RECRUITER_MINIMUM_FOLLOW_UPS,
    state: AnswerState = AnswerState.PARTIALLY_SUPPORTED,
    boundary: bool = True,
    handoff: bool = True,
) -> GroundedAnswer:
    """Exactly the brief the prompt now describes, with one dial per floor."""

    claims = [claim("claim-1", citations=citation_count)]
    while len(claims) < claim_count - (1 if boundary else 0):
        claims.append(claim(f"claim-{len(claims) + 1}"))
    if boundary:
        claims.append(
            claim(
                f"claim-{len(claims) + 1}",
                kind=AnswerKind.BOUNDARY,
                state=AnswerState.NOT_ESTABLISHED,
            )
        )
    return GroundedAnswer(
        answer_id="quality-answer",
        state=state,
        summary=summary_of(summary_words),
        claims=tuple(claims[:claim_count]) if claim_count else (),
        follow_up_questions=tuple(
            f"What did the subject own in role {index}?"
            for index in range(follow_ups)
        ),
        handoff=(
            HandoffProposal(
                reason=HandoffReason.HUMAN_JUDGMENT,
                question="Which of these results matters most to your team?",
            )
            if handoff
            else None
        ),
    )


def conditional_answer(
    *,
    purpose_follow_ups: int,
    claim_count: int = CONDITIONAL_MINIMUM_CLAIMS,
    citation_count: int = CONDITIONAL_MINIMUM_CITATIONS,
) -> GroundedAnswer:
    claims = [
        claim(f"claim-{index + 1}", citations=citation_count if index == 0 else 0)
        for index in range(claim_count)
    ]
    return GroundedAnswer(
        answer_id="quality-answer",
        state=AnswerState.SUPPORTED,
        summary="The approved public record documents the subject's work.",
        claims=tuple(claims),
        follow_up_questions=tuple(
            f"What did the subject own in role {index}?"
            for index in range(purpose_follow_ups)
        ),
    )


class TheStatedRecruiterNumbersAreTheEnforcedOnesTests(TestCase):
    def test_the_brief_the_prompt_describes_satisfies_the_quality_contract(self) -> None:
        # If this fails, the prompt is asking for an answer the server refuses.
        validate_product_quality(Purpose.RECRUITER_BRIEF, recruiter_answer())

    def test_the_summary_range_is_inclusive_at_both_ends(self) -> None:
        for word_count in (
            RECRUITER_MINIMUM_SUMMARY_WORDS,
            RECRUITER_MAXIMUM_SUMMARY_WORDS,
        ):
            with self.subTest(word_count=word_count):
                validate_product_quality(
                    Purpose.RECRUITER_BRIEF,
                    recruiter_answer(summary_words=word_count),
                )

    def test_one_step_below_each_stated_floor_is_refused(self) -> None:
        # The live failure was `summary_below_minimum_words`; the rest are
        # pinned alongside it so the next guessable number fails here first.
        for description, answer, failure in (
            (
                "summary one word short",
                recruiter_answer(summary_words=RECRUITER_MINIMUM_SUMMARY_WORDS - 1),
                "summary_below_minimum_words",
            ),
            (
                "summary one word long",
                recruiter_answer(summary_words=RECRUITER_MAXIMUM_SUMMARY_WORDS + 1),
                "summary_above_maximum_words",
            ),
            (
                "one claim short",
                recruiter_answer(claim_count=RECRUITER_MINIMUM_CLAIMS - 1),
                "claim_count_below_minimum",
            ),
            (
                "one citation short",
                recruiter_answer(citation_count=RECRUITER_MINIMUM_CITATIONS - 1),
                "citation_count_below_minimum",
            ),
            (
                "one follow-up short",
                recruiter_answer(follow_ups=RECRUITER_MINIMUM_FOLLOW_UPS - 1),
                "follow_up_count_below_minimum",
            ),
            (
                "no boundary claim",
                recruiter_answer(boundary=False),
                "boundary_claim_required",
            ),
            (
                "no private handoff",
                recruiter_answer(handoff=False),
                "private_handoff_required",
            ),
            (
                "any state but partially_supported",
                recruiter_answer(state=AnswerState.SUPPORTED),
                "state_not_allowed",
            ),
        ):
            with self.subTest(description):
                with self.assertRaises(AskPeteResponseError) as raised:
                    validate_product_quality(Purpose.RECRUITER_BRIEF, answer)
                self.assertIn(failure, str(raised.exception))

    def test_the_prompt_states_each_recruiter_number(self) -> None:
        prompt = PROMPT_PATH.read_text(encoding="utf-8")

        self.assertIn(
            f"{RECRUITER_MINIMUM_SUMMARY_WORDS} to "
            f"{RECRUITER_MAXIMUM_SUMMARY_WORDS} whitespace-separated words",
            prompt,
        )
        self.assertIn(
            f"a summary under {RECRUITER_MINIMUM_SUMMARY_WORDS} words is refused",
            prompt,
        )
        self.assertIn(f"at least {RECRUITER_MINIMUM_CLAIMS} claims in total", prompt)
        self.assertIn(
            f"at least {RECRUITER_MINIMUM_CITATIONS} citations in total",
            prompt,
        )
        self.assertIn(
            f"server minimum of {RECRUITER_MINIMUM_FOLLOW_UPS}",
            prompt,
        )


class TheConditionalPurposeNumbersTests(TestCase):
    def test_interview_preparation_needs_the_stated_three_follow_ups(self) -> None:
        validate_product_quality(
            Purpose.INTERVIEW_PREPARATION,
            conditional_answer(purpose_follow_ups=INTERVIEW_MINIMUM_FOLLOW_UPS),
        )

        with self.assertRaises(AskPeteResponseError) as raised:
            validate_product_quality(
                Purpose.INTERVIEW_PREPARATION,
                conditional_answer(
                    purpose_follow_ups=INTERVIEW_MINIMUM_FOLLOW_UPS - 1
                ),
            )
        self.assertIn("follow_up_count_below_minimum", str(raised.exception))

    def test_a_supported_answer_needs_the_stated_claim_and_citation(self) -> None:
        for purpose, follow_ups in (
            (Purpose.INTERVIEW_PREPARATION, INTERVIEW_MINIMUM_FOLLOW_UPS),
            (Purpose.EVIDENCE_FINDER, 0),
        ):
            with self.subTest(purpose=purpose.value):
                validate_product_quality(
                    purpose,
                    conditional_answer(purpose_follow_ups=follow_ups),
                )

                with self.assertRaises(AskPeteResponseError) as raised:
                    validate_product_quality(
                        purpose,
                        conditional_answer(
                            purpose_follow_ups=follow_ups,
                            claim_count=CONDITIONAL_MINIMUM_CLAIMS - 1,
                        ),
                    )
                self.assertIn("claim_count_below_minimum", str(raised.exception))

    def test_the_prompt_states_the_conditional_numbers(self) -> None:
        prompt = PROMPT_PATH.read_text(encoding="utf-8")

        self.assertIn(f"the server minimum is {INTERVIEW_MINIMUM_FOLLOW_UPS}", prompt)
        self.assertEqual(
            prompt.count(
                f"include at least {CONDITIONAL_MINIMUM_CLAIMS} claim carrying at "
                f"least {CONDITIONAL_MINIMUM_CITATIONS} citation"
            ),
            2,  # evidence_finder and interview_preparation
        )
        # public_profile_answer has no expectation in quality.py, and the
        # prompt says so rather than leaving the model to infer one.
        self.assertIn(
            "This purpose has no minimum claim, citation, follow-up, or word count.",
            prompt,
        )


def grounding_source() -> SourceVersion:
    return SourceVersion.approved(
        source_version_key="source:v1",
        source_key="source",
        version=1,
        subject_key="petec",
        title="Approved source",
        content="Evidence text.",
        allowed_audiences=frozenset({Audience.PUBLIC}),
        allowed_purposes=frozenset({Purpose.PUBLIC_PROFILE_ANSWER}),
    )


def grounding_request() -> AIRequest:
    return AIRequest(
        request_id="grounding-request",
        product="ask_pete",
        purpose=Purpose.PUBLIC_PROFILE_ANSWER,
        audience=Audience.PUBLIC,
        subject_key="petec",
        question="What is documented?",
    )


def grounded_claim(
    claim_id: str = "claim-1",
    *,
    kind: AnswerKind = AnswerKind.EVIDENCE,
    state: AnswerState = AnswerState.SUPPORTED,
    cited: bool = True,
    limitation: str | None = None,
) -> AnswerClaim:
    return AnswerClaim(
        claim_id=claim_id,
        text="A claim about the subject's documented work.",
        kind=kind,
        state=state,
        citations=(
            (
                Citation(
                    claim_id=claim_id,
                    source_version_key="source:v1",
                    start=0,
                    end=14,
                    excerpt="Evidence text.",
                ),
            )
            if cited
            else ()
        ),
        limitation=limitation,
    )


def grounded_answer(state: AnswerState, *claims: AnswerClaim) -> GroundedAnswer:
    return GroundedAnswer(
        answer_id="grounding-answer",
        state=state,
        summary="A summary of what the approved public record documents.",
        claims=claims,
    )


class TheStatedGroundingRulesAreTheEnforcedOnesTests(TestCase):
    """Round 4's two failures, and the rest of the same taxonomy.

    Live round 4 failed `interpretations must state their inferential boundary`
    and `a supported answer may contain only supported claims`. Both come from
    `services/ai_foundation/citation_validator.py`, and neither was stated in
    the prompt as something the server refuses on — rule 7 mentioned the
    interpretation limitation as guidance, and nothing described answer-state
    consistency at all. Every rule the prompt now states is checked here
    against the validator that enforces it.
    """

    def test_each_stated_rule_is_a_rule_the_validator_actually_enforces(self) -> None:
        for description, answer, message in (
            (
                "interpretation without a limitation",
                grounded_answer(
                    AnswerState.SUPPORTED,
                    grounded_claim(kind=AnswerKind.INTERPRETATION),
                ),
                "interpretations must state their inferential boundary",
            ),
            (
                "boundary without a limitation",
                grounded_answer(
                    AnswerState.NOT_ESTABLISHED,
                    grounded_claim(
                        kind=AnswerKind.BOUNDARY,
                        state=AnswerState.NOT_ESTABLISHED,
                        cited=False,
                    ),
                ),
                "boundary claims need a plain-language limitation",
            ),
            (
                "boundary that is not an unknown",
                grounded_answer(
                    AnswerState.SUPPORTED,
                    grounded_claim(kind=AnswerKind.BOUNDARY, limitation="A limit."),
                ),
                "boundary claims must describe an unknown or ambiguity",
            ),
            (
                "supported claim with no citation",
                grounded_answer(AnswerState.SUPPORTED, grounded_claim(cited=False)),
                "supported claims require a citation",
            ),
            (
                "partially supported claim with no limitation",
                grounded_answer(
                    AnswerState.PARTIALLY_SUPPORTED,
                    grounded_claim(state=AnswerState.PARTIALLY_SUPPORTED),
                ),
                "partially supported claims need evidence and an explicit limitation",
            ),
            (
                "not-established claim presenting a citation",
                grounded_answer(
                    AnswerState.NOT_ESTABLISHED,
                    grounded_claim(state=AnswerState.NOT_ESTABLISHED),
                ),
                "not-established claims cannot present a citation as proof",
            ),
            (
                "supported answer holding an unsupported claim",
                grounded_answer(
                    AnswerState.SUPPORTED,
                    grounded_claim(),
                    grounded_claim(
                        "claim-2",
                        kind=AnswerKind.BOUNDARY,
                        state=AnswerState.NOT_ESTABLISHED,
                        cited=False,
                        limitation="Not established.",
                    ),
                ),
                "a supported answer may contain only supported claims",
            ),
            (
                "partially supported answer with nothing partial",
                grounded_answer(AnswerState.PARTIALLY_SUPPORTED, grounded_claim()),
                "a partially supported answer must expose a partial or unknown claim",
            ),
            (
                "partially supported answer with no supported portion",
                grounded_answer(
                    AnswerState.PARTIALLY_SUPPORTED,
                    grounded_claim(
                        state=AnswerState.NOT_ESTABLISHED,
                        cited=False,
                        limitation="Not established.",
                    ),
                ),
                "an answer with no supported portion is not partially supported",
            ),
            (
                "not-established answer holding a supported claim",
                grounded_answer(AnswerState.NOT_ESTABLISHED, grounded_claim()),
                "a not-established answer cannot contain a supported claim",
            ),
            (
                "ambiguous answer holding a supported claim",
                grounded_answer(AnswerState.AMBIGUOUS, grounded_claim()),
                "an ambiguous answer may contain only ambiguity boundaries",
            ),
        ):
            with self.subTest(description):
                with self.assertRaises(GroundingValidationError) as raised:
                    validate_grounded_answer(
                        grounding_request(),
                        (grounding_source(),),
                        answer,
                    )
                self.assertEqual(str(raised.exception), message)

    def test_a_well_formed_mixed_answer_is_accepted(self) -> None:
        # The shape the prompt now names when evidence and an unknown appear
        # together: the state that reconciles them is partially_supported.
        validate_grounded_answer(
            grounding_request(),
            (grounding_source(),),
            grounded_answer(
                AnswerState.PARTIALLY_SUPPORTED,
                grounded_claim(),
                grounded_claim(
                    "claim-2",
                    kind=AnswerKind.INTERPRETATION,
                    state=AnswerState.PARTIALLY_SUPPORTED,
                    limitation="One documented result, not a general capability.",
                ),
                grounded_claim(
                    "claim-3",
                    kind=AnswerKind.BOUNDARY,
                    state=AnswerState.NOT_ESTABLISHED,
                    cited=False,
                    limitation="No approved public source addresses this.",
                ),
            ),
        )

    def test_the_prompt_states_the_claim_shape_rules(self) -> None:
        prompt = PROMPT_PATH.read_text(encoding="utf-8")

        self.assertIn(
            "A claim of kind interpretation must carry a limitation stating its "
            "inferential boundary.",
            prompt,
        )
        self.assertIn(
            "A claim of kind boundary must also carry a plain-language "
            "limitation, and its state must be not_established or ambiguous.",
            prompt,
        )
        self.assertIn(
            "A supported claim needs at least one citation. A partially_supported "
            "claim needs at least one citation and a limitation. A "
            "not_established claim must carry no citations.",
            prompt,
        )

    def test_the_prompt_states_the_state_consistency_rules(self) -> None:
        prompt = PROMPT_PATH.read_text(encoding="utf-8")

        for sentence in (
            "A supported answer may contain only supported claims.",
            "A partially_supported answer must contain at least one claim that "
            "is not supported, and at least one claim that is supported or "
            "partially_supported.",
            "A not_established answer may contain only not_established or "
            "ambiguous claims.",
            "An ambiguous answer may contain only ambiguous claims.",
            "whenever you mix supported evidence with a boundary or an unknown, "
            "the answer state is partially_supported",
        ):
            with self.subTest(sentence[:48]):
                self.assertIn(sentence, prompt)


class ThePromptQuotesTheDecoderCeilingsTests(TestCase):
    """The ceilings live in `codec.py`; the model can only obey what it is told."""

    def test_every_ceiling_appears_with_its_real_number(self) -> None:
        prompt = PROMPT_PATH.read_text(encoding="utf-8")

        for description, phrase in (
            ("claims", f"at most {MAX_CLAIMS} claims"),
            ("citations per claim", f"at most {MAX_CITATIONS_PER_CLAIM} citations in one claim"),
            ("follow-ups", f"at most {MAX_FOLLOW_UPS} follow_up_questions"),
            ("summary", f"summary at most {MAX_SUMMARY_CHARS} characters"),
            ("claim text", f"claim text at most {MAX_CLAIM_CHARS} characters"),
            ("limitation", f"limitation at most {MAX_LIMITATION_CHARS} characters"),
            ("follow-up text", f"follow_up_question at most {MAX_FOLLOW_UP_CHARS} characters"),
            ("excerpt", f"excerpt at most {MAX_EXCERPT_CHARS} characters"),
        ):
            with self.subTest(description):
                self.assertIn(phrase, prompt)

    def test_the_follow_up_shape_rule_names_the_observed_failure(self) -> None:
        # The live failure was a follow-up question over the ceiling, which is
        # what a multi-part question or a paragraph of setup produces.
        prompt = PROMPT_PATH.read_text(encoding="utf-8")

        self.assertIn(
            f"Each follow_up_question is one question in plain text, at most "
            f"{MAX_FOLLOW_UP_CHARS} characters.",
            prompt,
        )
        self.assertIn("Do not join several questions into one string", prompt)


class CompactnessNeverWinsAgainstAFloorTests(TestCase):
    def test_the_prompt_says_which_rule_wins(self) -> None:
        # The recruiter brief failed because the compactness paragraph read as
        # permission to shorten a summary that has a stated minimum. The
        # ordering is now stated rather than left to the model.
        prompt = PROMPT_PATH.read_text(encoding="utf-8")

        self.assertIn("Compactness never overrides a purpose requirement.", prompt)
        self.assertIn(
            "it never takes an answer below a stated minimum or outside a "
            "stated word range",
            prompt,
        )
        self.assertIn(
            f"A recruiter_brief summary under {RECRUITER_MINIMUM_SUMMARY_WORDS} "
            "words is refused",
            prompt,
        )

    def test_the_excerpt_preference_no_longer_reads_as_the_hard_limit(self) -> None:
        prompt = PROMPT_PATH.read_text(encoding="utf-8")

        self.assertIn(
            f"Prefer excerpts under 300 characters, well inside that "
            f"{MAX_EXCERPT_CHARS}-character ceiling",
            prompt,
        )
