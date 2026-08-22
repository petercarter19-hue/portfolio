"""Interview AI model-output validators (guarded runtime).

Moved verbatim from app.py by PS-INTERVIEW-AI-EXTRACT-001 correction C1 —
these are genuine guardian controls (guardian-runtime-legacy@1) and the
guarded dependency closure must contain them. Behaviour is unchanged; the
parity fixtures replay byte-for-byte across the move.
"""

import json
import re

from services.interview_ai.contracts import (
    INTERVIEW_DIMENSION_STATUSES,
    INTERVIEW_FAMILY_DIMENSIONS,
    MAX_INTERVIEW_ANSWER_LENGTH,
    _IMPROVEMENT_MARKER_PATTERN,
    normalize_interview_family,
)


def _strip_md(text):
    """Remove markdown emphasis the model sometimes sneaks into plain text."""
    return re.sub(r'\*{1,2}([^*]+)\*{1,2}', r'\1', str(text)).strip()


def _string_list(value, max_items):
    """Validate a list of non-empty strings, trimmed and capped."""
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValueError('expected a list')
    items = [_strip_md(item) for item in value if _strip_md(item)]
    return items[:max_items]


def validate_interview_review(raw, family='behavioral', allowed_evidence_ids=None):
    """Validate public Interview Studio's family-aware, score-free coaching.

    A useful answer is not reducible to one total or a universal framework. The
    contract therefore accepts only the dimensions relevant to the question
    family, and expresses the observation as a qualitative coaching state.
    """
    if not isinstance(raw, dict):
        raise ValueError('review is not an object')
    if any(key in raw for key in ('overallScore', 'score', 'star', 'targetAverage')):
        raise ValueError('numeric or universal review fields are not allowed')

    # A partial or permissively-normalized provider object is unsafe here: it
    # can make a plausible-looking review from a malformed response. Require a
    # fixed contract at every object boundary instead.
    expected_fields = {
        'verdict', 'encouragement', 'whatCameThroughClearly', 'strengths',
        'improvements', 'strongerApproach', 'focusedFollowUp', 'dimensions',
        'evidenceSuggestions',
    }
    if set(raw) != expected_fields:
        raise ValueError('review fields are invalid')

    def required_text(field, maximum):
        value = raw.get(field)
        if not isinstance(value, str):
            raise ValueError('review summary is incomplete')
        value = _strip_md(value)
        if not value or len(value) > maximum:
            raise ValueError('review summary is incomplete')
        return value

    def exact_string_list(field, minimum, maximum, item_maximum):
        value = raw.get(field)
        if not isinstance(value, list) or not minimum <= len(value) <= maximum:
            raise ValueError('review summary is incomplete')
        if any(not isinstance(item, str) for item in value):
            raise ValueError('review summary is incomplete')
        cleaned = [_strip_md(item) for item in value]
        if any(not item or len(item) > item_maximum for item in cleaned):
            raise ValueError('review summary is incomplete')
        if len(cleaned) != len(set(cleaned)):
            raise ValueError('duplicate review list item')
        return cleaned

    family = normalize_interview_family(family)
    review = {
        'reviewVersion': 'v2',
        'family': family,
        'verdict': required_text('verdict', 80),
        'encouragement': required_text('encouragement', 300),
        'whatCameThroughClearly': exact_string_list('whatCameThroughClearly', 1, 4, 300),
        'strengths': exact_string_list('strengths', 0, 4, 300),
        'improvements': exact_string_list('improvements', 1, 4, 300),
        'strongerApproach': required_text('strongerApproach', 900),
        'focusedFollowUp': required_text('focusedFollowUp', 300),
    }

    allowed_dimensions = INTERVIEW_FAMILY_DIMENSIONS[family]
    dimensions = raw.get('dimensions')
    if not isinstance(dimensions, list):
        raise ValueError('dimensions missing')
    if len(dimensions) != len(allowed_dimensions):
        raise ValueError('incomplete dimensions')
    expected_dimension_fields = {'key', 'status', 'rationale', 'nextAction'}
    clean_dimensions = []
    seen_keys = set()
    for dim in dimensions:
        if not isinstance(dim, dict):
            raise ValueError('dimension is not an object')
        if 'score' in dim:
            raise ValueError('numeric dimension scores are not allowed')
        if set(dim) != expected_dimension_fields:
            raise ValueError('dimension fields are invalid')
        key = dim.get('key')
        status = dim.get('status')
        rationale = dim.get('rationale')
        next_action = dim.get('nextAction')
        if not isinstance(key, str) or key not in allowed_dimensions:
            raise ValueError('incomplete dimensions')
        if key in seen_keys:
            raise ValueError('duplicate dimensions')
        if not isinstance(status, str) or status.strip().lower() not in INTERVIEW_DIMENSION_STATUSES:
            raise ValueError('invalid dimension status')
        if not isinstance(rationale, str) or not isinstance(next_action, str):
            raise ValueError('dimension explanation is incomplete')
        rationale = _strip_md(rationale)
        next_action = _strip_md(next_action)
        if not rationale or not next_action or len(rationale) > 400 or len(next_action) > 300:
            raise ValueError('dimension explanation is incomplete')
        clean_dimensions.append({
            'key': key,
            'status': status.strip().lower(),
            'rationale': rationale,
            'nextAction': next_action,
        })
        seen_keys.add(key)
    if seen_keys != set(allowed_dimensions):
        raise ValueError('incomplete dimensions')
    order = {key: index for index, key in enumerate(allowed_dimensions)}
    review['dimensions'] = sorted(clean_dimensions, key=lambda dim: order[dim['key']])

    suggestions_raw = raw.get('evidenceSuggestions')
    if not isinstance(suggestions_raw, list) or len(suggestions_raw) > 2:
        raise ValueError('evidence suggestions are invalid')
    expected_suggestion_fields = {'opportunity', 'suggestedUse', 'evidenceId'}
    allowed_ids = set(allowed_evidence_ids or [])
    suggestions = []
    seen_evidence_ids = set()
    for item in suggestions_raw:
        if not isinstance(item, dict):
            raise ValueError('evidence suggestion is not an object')
        if set(item) != expected_suggestion_fields:
            raise ValueError('evidence suggestion fields are invalid')
        opportunity = item.get('opportunity')
        suggested_use = item.get('suggestedUse')
        evidence_id = item.get('evidenceId')
        if not all(isinstance(value, str) for value in (opportunity, suggested_use, evidence_id)):
            raise ValueError('evidence suggestions are invalid')
        opportunity = _strip_md(opportunity)
        suggested_use = _strip_md(suggested_use)
        evidence_id = evidence_id.strip()
        if (not opportunity or not suggested_use or not evidence_id
                or len(opportunity) > 400 or len(suggested_use) > 400 or len(evidence_id) > 80):
            raise ValueError('evidence suggestions are invalid')
        if evidence_id in seen_evidence_ids:
            raise ValueError('duplicate evidence suggestions')
        if evidence_id not in allowed_ids:
            raise ValueError('review referenced unauthorized evidence')
        suggestions.append({
            'opportunity': opportunity,
            'suggestedUse': suggested_use,
            'evidenceId': evidence_id,
        })
        seen_evidence_ids.add(evidence_id)
    review['evidenceSuggestions'] = suggestions
    return review


def validate_interview_model_answer(raw, evidence_by_id, require_evidence=True):
    """Validate one model answer.

    Two legitimately different kinds of answer arrive here.

    A *grounded* answer (member_history) speaks as the profile owner and must
    cite at least one approved evidence id, so `require_evidence` stays True.

    An *illustrative* answer (best_practice) is a deliberately generic example
    that is not anyone's real history. Its own system prompt instructs the model
    to return `"evidenceIds": []`, so zero citations is the correct result, not
    a validation failure. Callers pass `require_evidence=False` together with an
    empty evidence map: the unauthorized-evidence check below therefore still
    rejects an illustrative answer that tries to cite anything at all.
    """
    if not isinstance(raw, dict):
        raise ValueError('model answer is not an object')
    status = str(raw.get('status') or '').strip().lower()
    if status == 'insufficient':
        return {
            'status': 'insufficient',
            'answer': 'PeerSlate does not have enough approved profile evidence to answer this question without guessing.',
            'whyItWorks': ['Avoids unsupported claims and makes the evidence gap explicit.'],
            'evidenceUsed': [],
        }
    if status != 'answered':
        raise ValueError('model answer status is invalid')
    answer = str(raw.get('answer') or '').strip()[:MAX_INTERVIEW_ANSWER_LENGTH]
    why = _string_list(raw.get('whyItWorks', []), 4)
    raw_evidence_ids = raw.get('evidenceIds') or []
    if not isinstance(raw_evidence_ids, list):
        raise ValueError('model answer evidence is not a list')
    evidence_ids = [str(item) for item in raw_evidence_ids]
    if not answer or not why:
        raise ValueError('model answer is incomplete')
    if len(evidence_ids) != len(set(evidence_ids)):
        raise ValueError('duplicate evidence references')
    if require_evidence and not evidence_ids:
        raise ValueError('model answer has no approved evidence references')
    if any(item not in evidence_by_id for item in evidence_ids):
        raise ValueError('model answer referenced unauthorized evidence')
    return {
        'status': 'answered',
        'answer': answer,
        'whyItWorks': why,
        'evidenceUsed': [evidence_by_id[item] for item in evidence_ids],
    }


def validate_interview_nudge(raw):
    """Validate two or three short, question-specific hints."""
    if not isinstance(raw, dict):
        raise ValueError('nudge is not an object')
    hints = _string_list(raw.get('hints', []), 3)
    hints = [hint[:240] for hint in hints]
    if len(hints) < 2:
        raise ValueError('nudge is incomplete')
    return {'hints': hints}


def validate_interview_improvement(raw, evidence_by_id):
    if not isinstance(raw, dict):
        raise ValueError('improvement is not an object')
    draft = str(raw.get('draft') or '').strip()[:MAX_INTERVIEW_ANSWER_LENGTH]
    changes = _string_list(raw.get('changes', []), 4)
    raw_evidence_ids = raw.get('evidenceIds') or []
    if not isinstance(raw_evidence_ids, list) or any(not isinstance(item, str) for item in raw_evidence_ids):
        raise ValueError('improvement evidence is not a list')
    evidence_ids = raw_evidence_ids
    if not draft or not changes:
        raise ValueError('improvement is incomplete')
    if len(evidence_ids) != len(set(evidence_ids)):
        raise ValueError('duplicate evidence references')
    if any(item not in evidence_by_id for item in evidence_ids):
        raise ValueError('improvement referenced unauthorized evidence')
    # Extract the coach's bracketed confirmation prompts, order-preserving
    # and de-duplicated, so the client can gate "Review Revised Answer" on
    # the member resolving every one (architecture 03 section 2). The server
    # never invents these — it only reports what the model actually wrote.
    seen_markers = set()
    confirmations = []
    for match in _IMPROVEMENT_MARKER_PATTERN.finditer(draft):
        marker = match.group(0)
        if marker not in seen_markers:
            seen_markers.add(marker)
            confirmations.append(marker)
    return {
        'draft': draft,
        'changes': changes,
        'evidenceUsed': [evidence_by_id[item] for item in evidence_ids],
        'confirmations': confirmations,
    }


def extract_json_object(text):
    """Pull the first JSON object out of a model reply (fences tolerated)."""
    cleaned = text.strip()
    cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
    cleaned = re.sub(r'\s*```$', '', cleaned)
    start = cleaned.find('{')
    end = cleaned.rfind('}')
    if start == -1 or end <= start:
        raise ValueError('no JSON object in reply')

    def no_duplicate_fields(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('duplicate JSON field')
            result[key] = value
        return result

    return json.loads(cleaned[start:end + 1], object_pairs_hook=no_duplicate_fields)
