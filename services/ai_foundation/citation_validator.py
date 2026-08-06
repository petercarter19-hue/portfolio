"""Deterministic claim-level citation and support-state validation.

The model may choose candidate citations. This validator proves that a link is
real only when it names an authorized source version and its excerpt exactly
matches the recorded character span. Exact linkage does not by itself prove
that the source semantically entails the model's claim; curated evaluation and
human review remain necessary for that judgment.
"""

from collections.abc import Iterable

from .contracts import AIRequest, AnswerKind, AnswerState, GroundedAnswer, SourceVersion
from .errors import GroundingValidationError, SourceAuthorizationError


def authorize_sources(
    request: AIRequest,
    sources: Iterable[SourceVersion],
) -> tuple[SourceVersion, ...]:
    authorized = tuple(sources)
    seen: set[str] = set()
    for source in authorized:
        if source.source_version_key in seen:
            raise SourceAuthorizationError("duplicate source version key")
        seen.add(source.source_version_key)
        if not source.digest_is_current():
            raise SourceAuthorizationError("source content does not match its version digest")
        if not source.permits(request):
            raise SourceAuthorizationError("source is outside the request authorization scope")
    return authorized


def validate_grounded_answer(
    request: AIRequest,
    sources: Iterable[SourceVersion],
    answer: GroundedAnswer,
) -> GroundedAnswer:
    source_map = {
        source.source_version_key: source
        for source in authorize_sources(request, sources)
    }
    claim_ids: set[str] = set()

    if not answer.answer_id.strip() or not answer.summary.strip():
        raise GroundingValidationError("answer id and summary are required")

    if answer.state in {AnswerState.REFUSED, AnswerState.UNAVAILABLE}:
        if answer.claims:
            raise GroundingValidationError(
                "refused or unavailable answers cannot contain factual claims"
            )
        return answer

    claim_states = {claim.state for claim in answer.claims}
    if answer.state is AnswerState.SUPPORTED and claim_states != {
        AnswerState.SUPPORTED
    }:
        raise GroundingValidationError(
            "a supported answer may contain only supported claims"
        )
    if answer.state is AnswerState.PARTIALLY_SUPPORTED:
        if not answer.claims or claim_states == {AnswerState.SUPPORTED}:
            raise GroundingValidationError(
                "a partially supported answer must expose a partial or unknown claim"
            )
        if not claim_states.intersection(
            {AnswerState.SUPPORTED, AnswerState.PARTIALLY_SUPPORTED}
        ):
            raise GroundingValidationError(
                "an answer with no supported portion is not partially supported"
            )
    if answer.state is AnswerState.NOT_ESTABLISHED and not claim_states.issubset(
        {AnswerState.NOT_ESTABLISHED, AnswerState.AMBIGUOUS}
    ):
        raise GroundingValidationError(
            "a not-established answer cannot contain a supported claim"
        )
    if answer.state is AnswerState.AMBIGUOUS and not claim_states.issubset(
        {AnswerState.AMBIGUOUS}
    ):
        raise GroundingValidationError(
            "an ambiguous answer may contain only ambiguity boundaries"
        )

    for claim in answer.claims:
        if not claim.claim_id.strip() or claim.claim_id in claim_ids:
            raise GroundingValidationError("claim ids must be present and unique")
        claim_ids.add(claim.claim_id)

        if claim.state is AnswerState.SUPPORTED and not claim.citations:
            raise GroundingValidationError("supported claims require a citation")
        if claim.state is AnswerState.PARTIALLY_SUPPORTED:
            if not claim.citations or not (claim.limitation or "").strip():
                raise GroundingValidationError(
                    "partially supported claims need evidence and an explicit limitation"
                )
        if claim.state is AnswerState.NOT_ESTABLISHED and claim.citations:
            raise GroundingValidationError(
                "not-established claims cannot present a citation as proof"
            )
        if claim.kind is AnswerKind.BOUNDARY:
            if claim.state not in {
                AnswerState.NOT_ESTABLISHED,
                AnswerState.AMBIGUOUS,
            }:
                raise GroundingValidationError(
                    "boundary claims must describe an unknown or ambiguity"
                )
            if not (claim.limitation or "").strip():
                raise GroundingValidationError(
                    "boundary claims need a plain-language limitation"
                )
        if claim.kind is AnswerKind.INTERPRETATION and not (
            claim.limitation or ""
        ).strip():
            raise GroundingValidationError(
                "interpretations must state their inferential boundary"
            )

        citation_keys: set[tuple[str, int, int]] = set()
        for citation in claim.citations:
            if citation.claim_id != claim.claim_id:
                raise GroundingValidationError("citation points to a different claim")
            source = source_map.get(citation.source_version_key)
            if source is None:
                raise GroundingValidationError(
                    "citation names a source version not supplied to the request"
                )
            if citation.start < 0 or citation.end <= citation.start:
                raise GroundingValidationError("citation span is invalid")
            if citation.end > len(source.content):
                raise GroundingValidationError("citation span exceeds its source")
            if source.content[citation.start : citation.end] != citation.excerpt:
                raise GroundingValidationError(
                    "citation excerpt does not exactly match its source span"
                )
            key = (citation.source_version_key, citation.start, citation.end)
            if key in citation_keys:
                raise GroundingValidationError("duplicate citation on one claim")
            citation_keys.add(key)

    return answer
