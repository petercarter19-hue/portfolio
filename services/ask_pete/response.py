"""Public response serialization with claim-level support and source locators."""

from __future__ import annotations

from services.ai_foundation import AnswerState, GroundedAnswer, Purpose

from .manifest import PublicSourceCatalog


RESPONSE_SCHEMA = "ask-pete-public-answer.v1"
SUPPORT_LABELS = {
    AnswerState.SUPPORTED: "Supported by approved public information",
    AnswerState.PARTIALLY_SUPPORTED: "Partially supported",
    AnswerState.NOT_ESTABLISHED: "Not established in approved public information",
    AnswerState.AMBIGUOUS: "Needs clarification",
    AnswerState.REFUSED: "Cannot answer this request",
    AnswerState.UNAVAILABLE: "Temporarily unavailable",
}


def _locator_payload(catalog: PublicSourceCatalog, source_version_key: str) -> dict:
    record = catalog.record_for_version(source_version_key)
    locator = record.locator
    return {
        "section": locator.section,
        "anchor": locator.anchor,
        "record_kind": locator.record_kind,
        "record_id": locator.record_id,
        "highlight_key": locator.highlight_key,
        "href": f"/{catalog.profile_slug}/resume#{locator.anchor}",
    }


def serialize_public_answer(
    *,
    answer: GroundedAnswer,
    catalog: PublicSourceCatalog,
    purpose: Purpose,
    context_key: str | None,
) -> dict:
    claims: list[dict] = []
    used_keys: list[str] = []
    for claim in answer.claims:
        citations: list[dict] = []
        for citation in claim.citations:
            record = catalog.record_for_version(citation.source_version_key)
            source = record.source
            if source.source_version_key not in used_keys:
                used_keys.append(source.source_version_key)
            citations.append(
                {
                    "claim_id": claim.claim_id,
                    "source_version_key": source.source_version_key,
                    "source_key": source.source_key,
                    "source_title": source.title,
                    "excerpt": citation.excerpt,
                    "start": citation.start,
                    "end": citation.end,
                    "locator": _locator_payload(catalog, source.source_version_key),
                }
            )
        claims.append(
            {
                "claim_id": claim.claim_id,
                "text": claim.text,
                "kind": claim.kind.value,
                "state": claim.state.value,
                "support_label": SUPPORT_LABELS[claim.state],
                "limitation": claim.limitation,
                "citations": citations,
            }
        )

    sources_used = []
    for source_version_key in used_keys:
        record = catalog.record_for_version(source_version_key)
        sources_used.append(
            {
                "source_version_key": record.source.source_version_key,
                "source_key": record.source.source_key,
                "title": record.source.title,
                "locator": _locator_payload(catalog, source_version_key),
            }
        )

    handoff = None
    if answer.handoff is not None:
        first_name = catalog.subject_display_name.split()[0]
        handoff = {
            "available": True,
            "reason": answer.handoff.reason.value,
            "question": answer.handoff.question,
            "private": answer.handoff.private,
            "label": f"Contact {first_name} directly",
            "href": f"/{catalog.profile_slug}/contact",
            "delivery_note": (
                f"Nothing is sent automatically. This opens {first_name}'s current "
                "contact options; on-platform private messaging is not live."
            ),
        }

    return {
        "schema_version": RESPONSE_SCHEMA,
        "answer_id": answer.answer_id,
        "purpose": purpose.value,
        "state": answer.state.value,
        "support_label": SUPPORT_LABELS[answer.state],
        "summary": answer.summary,
        "claims": claims,
        "follow_up_questions": list(answer.follow_up_questions),
        "handoff": handoff,
        "sources_used": sources_used,
        "source_summary": {
            "used_count": len(sources_used),
            "label": f"Used in this answer: {len(sources_used)} public records",
            "show_all_on_resume": bool(sources_used),
        },
        "context": {
            "context_key": context_key,
            "manifest_id": catalog.manifest_id,
        },
        # Legacy clients can continue rendering a single response string while
        # a future approved interface consumes the structured fields above.
        "response": answer.summary,
    }
