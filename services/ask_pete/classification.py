"""Server-owned classification for the bounded public Ask Pete jobs."""

from __future__ import annotations

from services.ai_foundation import Purpose


ACTION_PURPOSES = {
    "recruiter_brief": Purpose.RECRUITER_BRIEF,
    "evidence_finder": Purpose.EVIDENCE_FINDER,
    "interview_preparation": Purpose.INTERVIEW_PREPARATION,
}


def classify_public_purpose(
    question: str,
    *,
    requested_action: str | None = None,
) -> Purpose:
    """Map visitor intent into a fixed public purpose allowlist.

    A future interface may send a quick-action name, but it never supplies an
    authorization enum. Unknown values are ignored and the server classifies
    the bounded question itself.
    """

    if isinstance(requested_action, str):
        action = ACTION_PURPOSES.get(requested_action.strip().lower())
        if action is not None:
            return action

    normalized = " ".join(question.lower().split())
    if any(
        phrase in normalized
        for phrase in (
            "what should i ask",
            "questions should i ask",
            "interview question",
            "prepare for an interview",
            "first interview",
        )
    ):
        return Purpose.INTERVIEW_PREPARATION
    if any(
        phrase in normalized
        for phrase in (
            "60-second",
            "60 second",
            "recruiter brief",
            "recruiter overview",
            "professional through-line",
        )
    ):
        return Purpose.RECRUITER_BRIEF
    if any(
        phrase in normalized
        for phrase in (
            "what evidence",
            "show evidence",
            "what supports",
            "show proof",
            "where has",
            "how has",
            "measurable results",
            "quantified results",
            "source for",
            "citations for",
        )
    ):
        return Purpose.EVIDENCE_FINDER
    return Purpose.PUBLIC_PROFILE_ANSWER
