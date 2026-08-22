"""Interview AI request-boundary contracts (guarded runtime).

The v1 family/dimension registry, the marker contract, and the request
size bounds — moved verbatim from app.py by PS-INTERVIEW-AI-EXTRACT-001
correction C1 so the guarded dependency closure actually contains them.
Values are unchanged; changing any of them is a contracts change.
"""

import re

# Interview Studio: request-size guards for the structured coaching
# endpoints. Answers are longer than chat messages by design.
MAX_INTERVIEW_ANSWER_LENGTH = 5000
MAX_INTERVIEW_QUESTION_LENGTH = 300
# Visitor-supplied opportunity text is useful tailoring context, but it is
# never fetched, stored server-side, or allowed to become an instruction.
MAX_INTERVIEW_OPPORTUNITY_CONTEXT_LENGTH = 4000

INTERVIEW_CONTEXT_MAX_AGE_SECONDS = 30 * 60

INTERVIEW_FAMILY_DIMENSIONS = {
    'professional_intro': ('identity', 'relevant_proof', 'value', 'direction'),
    'behavioral': ('situation_clarity', 'action_ownership', 'evidence', 'outcome', 'reflection'),
    'motivation_fit': ('authentic_rationale', 'specificity', 'role_connection', 'forward_direction'),
    'situational': ('problem_framing', 'judgment', 'tradeoffs', 'action_plan', 'communication'),
    'role_specific': ('relevance', 'reasoning', 'evidence', 'priorities', 'execution'),
    'technical_case': ('framing', 'assumptions', 'reasoning', 'tradeoffs', 'conclusion'),
}
INTERVIEW_FAMILIES = tuple(INTERVIEW_FAMILY_DIMENSIONS)
INTERVIEW_DIMENSION_STATUSES = ('strong', 'clear', 'developing', 'missing')


def normalize_interview_family(value):
    """Return a supported question family without widening the public API."""
    family = str(value or '').strip().lower()
    if family == 'mixed':
        # ``mixed`` was a browser-only legacy choice. The V2 client resolves it
        # locally to a concrete blueprint before requesting coaching.
        return 'behavioral'
    return family if family in INTERVIEW_FAMILY_DIMENSIONS else 'behavioral'


# PS-INTERVIEW-STUDIO-AUTHENTICATED-EXPERIENCE-001 slice 4 (architecture 03
# section 2, "Confirmation markers"). The improve system prompt instructs
# the coach to phrase every unsupported-fact placeholder as a short
# imperative sentence inside square brackets, ending in a period
# (e.g. "[Describe the specific outcome you achieved.]"). This pattern is
# deliberately narrow so it matches that shape and only that shape: a
# bracketed span opening with a capitalized word, a space, then any
# non-bracket text, ending in ".]" A candidate's own incidental bracket use
# ("[sic]", "M[1-9]") never matches (no leading capitalized word + space, or
# no closing ".]"), so it is never treated as an unresolved marker or
# rejected by the server-side re-validation.
_IMPROVEMENT_MARKER_PATTERN = re.compile(r'\[[A-Z][a-zA-Z]*\s[^\[\]]*\.\]')
