"""Server-owned classification for the bounded public Ask Pete jobs."""

from __future__ import annotations

from services.ai_foundation import Purpose


# Every purpose in this map carries a stricter product quality contract than
# the general public answer (services/ask_pete/quality.py), so each one is a
# deliberate request from an interface that understands that contract — never
# an inference from a visitor's wording.
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
    """Map an explicit quick-action name into the public purpose allowlist.

    A purpose is a server-side decision about which approved public sources
    reach the model and which quality contract the answer must satisfy. Only
    an explicit, recognized action can select one. No action, an unrecognized
    action, or wording that merely sounds like a quick action all answer under
    the general public-profile purpose. A caller still never supplies an
    authorization enum; unknown values are ignored rather than rejected.

    Keyword matching used to escalate here, and that was the bug. The legacy
    chat surface (static/js/chatbot.js) posts only {"message": ...}, so a
    visitor who happened to type "60-second recruiter brief" was escalated
    into the flagship recruiter contract — four claims, three citations, a
    100-140 word summary, a boundary and a handoff. A shortfall then failed
    the whole request with a 502 instead of answering the question. The
    resume evidence companion always sends a recognized action, so its
    experience is unchanged.

    `question` stays in the signature because classification is the server's
    decision to make about this request; the caller's seam does not change.
    """

    if isinstance(requested_action, str):
        action = ACTION_PURPOSES.get(requested_action.strip().lower())
        if action is not None:
            return action
    return Purpose.PUBLIC_PROFILE_ANSWER
