"""The five Interview AI job cores (guarded runtime).

Everything Interview-AI-specific that used to live inside the four route
bodies in app.py — request parsing, refusal copy, release resolution,
prompt rendering, provider dispatch, validation, response assembly,
telemetry, and bounded logging — moved here by PS-INTERVIEW-AI-EXTRACT-001
correction C1 so the guarded dependency closure genuinely contains the
behaviour. Route glue in app.py keeps only the shared-site boundary
(identity, entitlements, content type, cross-site refusal, rate limits)
and passes everything else in as data.

Every core returns ``(payload_dict, http_status)``; the glue serializes
with the same ``jsonify`` it always used, so response bytes are unchanged
— proven by the parity fixtures.
"""

import hmac
import json

import anthropic

from services.interview_ai import rendering
from services.interview_ai import telemetry as tel
from services.interview_ai.constants import SERVICE_NOT_CONFIGURED_COPY
from services.interview_ai.context_tokens import (
    bounded_opportunity_context,
    load_interview_model_context,
    opportunity_context_digest,
    sign_interview_model_context,
    untrusted_opportunity_block,
)
from services.interview_ai.contracts import (
    INTERVIEW_FAMILY_DIMENSIONS,
    MAX_INTERVIEW_ANSWER_LENGTH,
    MAX_INTERVIEW_QUESTION_LENGTH,
    _IMPROVEMENT_MARKER_PATTERN,
    normalize_interview_family,
)
from services.interview_ai.validation import (
    _string_list,
    extract_json_object,
    validate_interview_improvement,
    validate_interview_model_answer,
    validate_interview_nudge,
    validate_interview_review,
)

_VALIDATION_ERRORS = (ValueError, KeyError, TypeError, json.JSONDecodeError)


class JobDeps:
    """Everything a job core needs from the application boundary.

    Shared-site services (identity, profile context, the provider client,
    the signing serializer, the logger) are passed in as data so the
    guarded closure stays closed: this package never imports them.
    """

    def __init__(self, authenticated_studio, known_profile_slugs,
                 resolve_public_context, resolve_identity_context,
                 provider_client, serializer, active_release_config, logger,
                 default_public_profile_slug):
        self.authenticated_studio = authenticated_studio
        self.known_profile_slugs = known_profile_slugs
        # The public surface's default profile slug is application-boundary
        # policy (fixture content lives with the app, never in reusable
        # product logic), so it arrives as data.
        self.default_public_profile_slug = default_public_profile_slug
        self.resolve_public_context = resolve_public_context
        self.resolve_identity_context = resolve_identity_context
        self.provider_client = provider_client
        self.serializer = serializer
        self.active_release_config = active_release_config
        self.logger = logger


def log_interview_failure(logger, label, error, stop_reason, reply_length):
    """Record why a model reply was rejected, without logging its content.

    `reply_length` is a character count only. Candidate answers, model
    text, the exception object, raw class names, and raw stop reasons
    never enter the log line (corrections C7): the reason and class come
    from the closed allowlists and the stop reason is normalized.
    """
    logger.warning(
        '%s: reason=%s error_class=%s provider_stop_reason=%s reply_chars=%d',
        label,
        tel.classify_validation_error(error)[0],
        tel.normalize_exception_class(error),
        tel.normalize_stop_reason(stop_reason),
        reply_length,
    )


def _append_event(logger, builder):
    """Assemble and append one telemetry row without touching the response."""
    try:
        event = builder()
    except Exception as error:
        logger.warning(
            'interview telemetry assembly failed: class=%s',
            tel.normalize_exception_class(error),
        )
        return
    tel.append_server_call(event)


def _release_or_refusal(deps, timer, specialist=None, composition=None):
    """Read the frozen boot state; on failure return the frozen 503 refusal.

    Consolidated correction B3 (second round): requests ONLY read. A
    process whose boot initializer never ran answers exactly like a
    failed boot — service_not_configured, zero provider dispatch, zero
    file access — and nothing on the request path can invoke
    boot.initialize or resolve release files.
    """
    from services.interview_ai import boot
    state = boot.state()
    if state is not None and state.status == boot.READY:
        return state.release, None
    event_kind = 'composition_parent' if composition else 'specialist_call'
    _append_event(
        deps.logger,
        lambda: tel.build_event(
            timer,
            event_kind,
            'failed',
            503,
            'not_applicable',
            tel.source_class_counts(),
            specialist=specialist,
            composition=composition,
            failure_state='service_not_configured',
            failure_reason='active_release_unresolved',
        ),
    )
    return None, ({'error': SERVICE_NOT_CONFIGURED_COPY}, 503)


def _finalize_specialist_row(
    logger, timer, specialist, bundle, release, outcome, http_status,
    validation_result, counts, failure_state=None, failure_reason=None,
    exception_class=None, exception_attrs=None, provider_response=None,
    parent_attempt_uuid=None,
):
    """Write one specialist server_call row after the response is decided."""
    _append_event(
        logger,
        lambda: tel.build_event(
            timer,
            'specialist_call',
            outcome,
            http_status,
            validation_result,
            counts,
            specialist=specialist,
            bundle=bundle,
            release_set_id=release.release_set_id if release else None,
            parent_attempt_uuid=parent_attempt_uuid,
            failure_state=failure_state,
            failure_reason=failure_reason,
            exception_class=exception_class,
            exception_attrs=exception_attrs,
            provider_response=provider_response,
        ),
    )


def run_review(data, deps):
    """The coach job (/api/interview/review), from parsing to payload."""
    if not isinstance(data, dict):
        return {'error': 'Send one JSON object for the interview request.'}, 400
    question = str(data.get('question') or '').strip()
    answer = str(data.get('answer') or '').strip()
    level = str(data.get('level') or 'experienced').strip()
    family = normalize_interview_family(data.get('family'))
    competency = str(data.get('competency') or 'Communication').strip()[:80]
    # Review finding P2-1: `attempt` is client-reported UX truth (which
    # submission this is), not a security boundary — the actual boundary is
    # the improve contract that produces the bracket markers in the first
    # place. Validate it as a bounded int and default to 1 (first attempt)
    # for anything missing or malformed, so a bad/absent value can only ever
    # make the gate *more* permissive (matches "first attempt"), never less.
    attempt = data.get('attempt')
    if not isinstance(attempt, int) or isinstance(attempt, bool) or attempt < 1 or attempt > 1000:
        attempt = 1
    # Slice 2: a client-supplied profile_slug is only honored on the public,
    # flag-off page. Once the flag is on, it is dropped before use — never
    # read into a variable, let alone trusted — and the profile/evidence
    # context is resolved from the server-derived identity instead.
    if not deps.authenticated_studio:
        profile_slug = str(
            data.get('profile_slug') or deps.default_public_profile_slug
        ).strip()
    try:
        opportunity_context = bounded_opportunity_context(data.get('opportunity_context'))
    except ValueError:
        return {'error': 'Please keep opportunity context under 4,000 characters.'}, 400

    if not question or not answer:
        return {'error': 'Both the question and your answer are required.'}, 400
    if len(question) > MAX_INTERVIEW_QUESTION_LENGTH:
        return {'error': 'That question is too long.'}, 400
    if len(answer) > MAX_INTERVIEW_ANSWER_LENGTH:
        return {'error': 'Please keep answers under 5,000 characters.'}, 400
    # Slice 4 marker contract (architecture 03 section 2), narrowed by review
    # finding P2-1/P2-2: defense in depth against a client-side bypass of
    # the "Review Revised Answer" disabled state applies ONLY to a revision
    # submission (attempt >= 2) — a first attempt has never been through the
    # improve flow, so a member's own incidental bracket use must pass
    # unchanged. Scoped to the authenticated surface only — the flag-off
    # public review endpoint has no bracket-marker UI.
    if deps.authenticated_studio and attempt >= 2 and _IMPROVEMENT_MARKER_PATTERN.search(answer):
        return {'error': 'Replace or remove every bracketed prompt before review.'}, 400
    if level not in ('entry', 'experienced', 'management', 'leadership', 'mixed'):
        level = 'experienced'

    timer = tel.ServerCallAttempt()
    if deps.authenticated_studio:
        with timer.phase('retrieval'):
            profile, evidence = deps.resolve_identity_context()
    else:
        if profile_slug not in deps.known_profile_slugs:
            return {'error': 'That interview profile is unavailable.'}, 404
        with timer.phase('retrieval'):
            profile, evidence = deps.resolve_public_context(profile_slug)
    evidence_by_id = {item['id']: item for item in evidence}
    evidence_lines = '\n'.join(
        '- [%s] %s — %s: %s' % (
            item['id'], item['metric'], item['label'], item['summary']
        )
        for item in evidence
    ) or '- No approved public evidence is available.'
    grounding = (
        'APPROVED PUBLIC PROFILE EVIDENCE: the ONLY evidence you may suggest is listed below. '
        'Never invent metrics, employers, titles, projects, dates, duties, or outcomes. '
        'If nothing fits, return no evidence suggestions.\n' + evidence_lines
    )

    release, refusal = _release_or_refusal(deps, timer, specialist='coach')
    if refusal:
        return refusal
    bundle = release.bundles['coach']
    allowed_dimension_keys = '|'.join(INTERVIEW_FAMILY_DIMENSIONS[family])
    with timer.phase('manifest'):
        system_prompt = rendering.render_coach_system(
            bundle, level, family, competency, grounding, allowed_dimension_keys,
        )
        user_content = rendering.render_coach_user(
            bundle,
            question,
            untrusted_opportunity_block(opportunity_context),
            answer,
        )
    counts = tel.source_class_counts(
        question=1,
        answer=1,
        role_context=1 if opportunity_context else 0,
        member_evidence=len(evidence),
    )

    raw_reply = ''
    stop_reason = ''
    provider_response = None
    try:
        with timer.phase('provider'):
            response = deps.provider_client.messages.create(
                model=bundle.model,
                max_tokens=bundle.max_tokens,
                system=system_prompt,
                messages=[{'role': 'user', 'content': user_content}],
            )
        provider_response = response
        stop_reason = getattr(response, 'stop_reason', '') or ''
        with timer.phase('validate'):
            raw_reply = response.content[0].text
            review = validate_interview_review(
                extract_json_object(raw_reply),
                family,
                allowed_evidence_ids=evidence_by_id,
            )
        with timer.phase('respond'):
            payload = {'review': review}
        _finalize_specialist_row(
            deps.logger, timer, 'coach', bundle, release, 'success', 200,
            'passed', counts, provider_response=provider_response,
        )
        return payload, 200
    except _VALIDATION_ERRORS as error:
        # Never render partial or malformed coaching as real feedback.
        log_interview_failure(
            deps.logger, 'Interview review validation error', error,
            stop_reason, len(raw_reply),
        )
        reason, exception_class = tel.classify_validation_error(error)
        _finalize_specialist_row(
            deps.logger, timer, 'coach', bundle, release, 'failed', 502,
            'rejected', counts, failure_state='invalid_output',
            failure_reason=reason, exception_class=exception_class,
            exception_attrs={
                'provider_stop_reason': tel.normalize_stop_reason(stop_reason),
                'reply_chars': len(raw_reply),
            },
            provider_response=provider_response,
        )
        return {'error': 'The coach returned an unreadable review. Please try again.'}, 502
    except anthropic.APIError as error:
        reason, exception_class, provider_status = tel.normalize_provider_error(error)
        deps.logger.error(
            'Interview review provider error: class=%s status=%s',
            exception_class,
            provider_status if provider_status is not None else 'none',
        )
        _finalize_specialist_row(
            deps.logger, timer, 'coach', bundle, release, 'failed', 500,
            'not_applicable', counts, failure_state='provider_failure',
            failure_reason=reason, exception_class=exception_class,
            exception_attrs=(
                {'status_code': provider_status}
                if provider_status is not None else {}
            ),
            provider_response=provider_response,
        )
        return {'error': 'The coach is unavailable right now. Please try again.'}, 500
    except Exception as error:
        deps.logger.error(
            'Interview review API error: class=%s',
            tel.normalize_exception_class(error),
        )
        _finalize_specialist_row(
            deps.logger, timer, 'coach', bundle, release, 'failed', 500,
            'not_applicable', counts, failure_state='internal_error',
            failure_reason='unexpected_server_fault',
            exception_class=tel.persisted_exception_class(error),
            provider_response=provider_response,
        )
        return {'error': 'The coach is unavailable right now. Please try again.'}, 500


def run_improve(data, deps):
    """The revision job (/api/interview/improve)."""
    if not isinstance(data, dict):
        return {'error': 'Send one JSON object for the interview request.'}, 400
    raw_improvements = data.get('improvements') or []
    raw_evidence_ids = data.get('evidence_ids') or []
    if (
        not isinstance(raw_improvements, list)
        or any(not isinstance(item, str) for item in raw_improvements)
        or not isinstance(raw_evidence_ids, list)
        or any(not isinstance(item, str) for item in raw_evidence_ids)
    ):
        return {'error': 'Improvements and evidence IDs must be JSON lists of text values.'}, 400
    question = str(data.get('question') or '').strip()
    answer = str(data.get('answer') or '').strip()
    additional_context = str(data.get('additional_context') or '').strip()
    family = normalize_interview_family(data.get('family'))
    # Slice 2: dropped before use once the flag is on — see run_review.
    if not deps.authenticated_studio:
        profile_slug = str(
            data.get('profile_slug') or deps.default_public_profile_slug
        ).strip()
    try:
        opportunity_context = bounded_opportunity_context(data.get('opportunity_context'))
    except ValueError:
        return {'error': 'Please keep opportunity context under 4,000 characters.'}, 400
    improvements = _string_list(raw_improvements, 4)
    selected_ids = raw_evidence_ids[:2]

    if not question or not answer:
        return {'error': 'The question and submitted answer are required.'}, 400
    if (
        len(question) > MAX_INTERVIEW_QUESTION_LENGTH
        or len(answer) > MAX_INTERVIEW_ANSWER_LENGTH
        or len(additional_context) > 1200
    ):
        return {'error': 'That interview content is too long.'}, 400

    timer = tel.ServerCallAttempt()
    if deps.authenticated_studio:
        with timer.phase('retrieval'):
            _profile, evidence = deps.resolve_identity_context()
    else:
        if profile_slug not in deps.known_profile_slugs:
            return {'error': 'That interview profile is unavailable.'}, 404
        with timer.phase('retrieval'):
            _profile, evidence = deps.resolve_public_context(profile_slug)
    all_evidence = {item['id']: item for item in evidence}
    if len(selected_ids) != len(set(selected_ids)) or any(item not in all_evidence for item in selected_ids):
        return {'error': 'One of those evidence suggestions is unavailable.'}, 403
    selected_evidence = {item: all_evidence[item] for item in selected_ids}
    evidence_lines = '\n'.join(
        '- [%s] %s — %s: %s' % (
            item['id'], item['metric'], item['label'], item['summary']
        )
        for item in selected_evidence.values()
    ) or '- No additional evidence was selected. Use only facts already present in the answer.'

    release, refusal = _release_or_refusal(deps, timer, specialist='revision')
    if refusal:
        return refusal
    bundle = release.bundles['revision']
    improvement_notes = '\n'.join('- ' + item for item in improvements) or '- Make the answer clearer and more specific.'
    confirmed_context = additional_context or 'No additional candidate-confirmed context was supplied.'
    with timer.phase('manifest'):
        system_prompt = rendering.render_revision_system(bundle, evidence_lines)
        user_content = rendering.render_revision_user(
            bundle,
            question,
            family,
            untrusted_opportunity_block(opportunity_context),
            answer,
            confirmed_context,
            improvement_notes,
        )
    counts = tel.source_class_counts(
        question=1,
        answer=1,
        role_context=1 if opportunity_context else 0,
        member_evidence=len(selected_evidence),
        confirmed_context=1 if additional_context else 0,
    )

    raw_reply = ''
    stop_reason = ''
    provider_response = None
    try:
        with timer.phase('provider'):
            response = deps.provider_client.messages.create(
                model=bundle.model,
                max_tokens=bundle.max_tokens,
                system=system_prompt,
                messages=[{'role': 'user', 'content': user_content}],
            )
        provider_response = response
        stop_reason = getattr(response, 'stop_reason', '') or ''
        with timer.phase('validate'):
            raw_reply = response.content[0].text
            improvement = validate_interview_improvement(
                extract_json_object(raw_reply),
                selected_evidence,
            )
        with timer.phase('respond'):
            payload = {'improvement': improvement}
        _finalize_specialist_row(
            deps.logger, timer, 'revision', bundle, release, 'success', 200,
            'passed', counts, provider_response=provider_response,
        )
        return payload, 200
    except _VALIDATION_ERRORS as error:
        log_interview_failure(
            deps.logger, 'Interview improvement validation error', error,
            stop_reason, len(raw_reply),
        )
        reason, exception_class = tel.classify_validation_error(error)
        _finalize_specialist_row(
            deps.logger, timer, 'revision', bundle, release, 'failed', 502,
            'rejected', counts, failure_state='invalid_output',
            failure_reason=reason, exception_class=exception_class,
            exception_attrs={
                'provider_stop_reason': tel.normalize_stop_reason(stop_reason),
                'reply_chars': len(raw_reply),
            },
            provider_response=provider_response,
        )
        return {'error': 'The coach returned an unreadable draft. Please try again.'}, 502
    except anthropic.APIError as error:
        reason, exception_class, provider_status = tel.normalize_provider_error(error)
        deps.logger.error(
            'Interview improvement provider error: class=%s status=%s',
            exception_class,
            provider_status if provider_status is not None else 'none',
        )
        _finalize_specialist_row(
            deps.logger, timer, 'revision', bundle, release, 'failed', 500,
            'not_applicable', counts, failure_state='provider_failure',
            failure_reason=reason, exception_class=exception_class,
            exception_attrs=(
                {'status_code': provider_status}
                if provider_status is not None else {}
            ),
            provider_response=provider_response,
        )
        return {'error': 'The coach is unavailable right now. Please try again.'}, 500
    except Exception as error:
        deps.logger.error(
            'Interview improvement API error: class=%s',
            tel.normalize_exception_class(error),
        )
        _finalize_specialist_row(
            deps.logger, timer, 'revision', bundle, release, 'failed', 500,
            'not_applicable', counts, failure_state='internal_error',
            failure_reason='unexpected_server_fault',
            exception_class=tel.persisted_exception_class(error),
            provider_response=provider_response,
        )
        return {'error': 'The coach is unavailable right now. Please try again.'}, 500


def run_nudge(data, deps):
    """The planning_hints job (/api/interview/nudge)."""
    if not isinstance(data, dict):
        return {'error': 'Send one JSON object for the interview request.'}, 400
    question = str(data.get('question') or '').strip()
    level = str(data.get('level') or 'experienced').strip()
    family = normalize_interview_family(data.get('family'))
    competency = str(data.get('competency') or 'Communication').strip()[:80]
    practice_mode = str(data.get('practice_mode') or 'me').strip()
    # Slice 2: dropped before use once the flag is on — see run_review.
    # Nudge never resolves profile-owned evidence, so an authenticated
    # request needs no further profile lookup at all.
    if not deps.authenticated_studio:
        profile_slug = str(
            data.get('profile_slug') or deps.default_public_profile_slug
        ).strip()
    try:
        opportunity_context = bounded_opportunity_context(data.get('opportunity_context'))
    except ValueError:
        return {'error': 'Please keep opportunity context under 4,000 characters.'}, 400

    if not question:
        return {'error': 'Choose an interview question first.'}, 400
    if len(question) > MAX_INTERVIEW_QUESTION_LENGTH:
        return {'error': 'That interview question is too long.'}, 400
    if not deps.authenticated_studio and profile_slug not in deps.known_profile_slugs:
        return {'error': 'That interview profile is unavailable.'}, 404
    if level not in ('entry', 'experienced', 'management', 'leadership', 'mixed'):
        level = 'experienced'
    if practice_mode not in ('me', 'ai', 'video'):
        practice_mode = 'me'

    timer = tel.ServerCallAttempt()
    release, refusal = _release_or_refusal(deps, timer, specialist='planning_hints')
    if refusal:
        return refusal
    bundle = release.bundles['planning_hints']
    with timer.phase('manifest'):
        system_prompt = rendering.render_planning_hints_system(bundle)
        user_content = rendering.render_planning_hints_user(
            bundle,
            question,
            level,
            family,
            competency,
            practice_mode,
            untrusted_opportunity_block(opportunity_context),
        )
    counts = tel.source_class_counts(
        question=1,
        role_context=1 if opportunity_context else 0,
    )
    raw_reply = ''
    stop_reason = ''
    provider_response = None
    try:
        with timer.phase('provider'):
            response = deps.provider_client.messages.create(
                model=bundle.model,
                max_tokens=bundle.max_tokens,
                system=system_prompt,
                messages=[{'role': 'user', 'content': user_content}],
            )
        provider_response = response
        stop_reason = getattr(response, 'stop_reason', '') or ''
        with timer.phase('validate'):
            raw_reply = response.content[0].text
            nudge = validate_interview_nudge(extract_json_object(raw_reply))
        with timer.phase('respond'):
            payload = nudge
        _finalize_specialist_row(
            deps.logger, timer, 'planning_hints', bundle, release, 'success',
            200, 'passed', counts, provider_response=provider_response,
        )
        return payload, 200
    except _VALIDATION_ERRORS as error:
        log_interview_failure(
            deps.logger, 'Interview nudge validation error', error,
            stop_reason, len(raw_reply),
        )
        reason, exception_class = tel.classify_validation_error(error)
        _finalize_specialist_row(
            deps.logger, timer, 'planning_hints', bundle, release, 'failed',
            502, 'rejected', counts, failure_state='invalid_output',
            failure_reason=reason, exception_class=exception_class,
            exception_attrs={
                'provider_stop_reason': tel.normalize_stop_reason(stop_reason),
                'reply_chars': len(raw_reply),
            },
            provider_response=provider_response,
        )
        return {'error': 'The coach returned unreadable hints. Please try again.'}, 502
    except anthropic.APIError as error:
        reason, exception_class, provider_status = tel.normalize_provider_error(error)
        deps.logger.error(
            'Interview nudge provider error: class=%s status=%s',
            exception_class,
            provider_status if provider_status is not None else 'none',
        )
        _finalize_specialist_row(
            deps.logger, timer, 'planning_hints', bundle, release, 'failed',
            500, 'not_applicable', counts, failure_state='provider_failure',
            failure_reason=reason, exception_class=exception_class,
            exception_attrs=(
                {'status_code': provider_status}
                if provider_status is not None else {}
            ),
            provider_response=provider_response,
        )
        return {'error': 'Interview hints are unavailable right now. Please try again.'}, 500
    except Exception as error:
        deps.logger.error(
            'Interview nudge API error: class=%s',
            tel.normalize_exception_class(error),
        )
        _finalize_specialist_row(
            deps.logger, timer, 'planning_hints', bundle, release, 'failed',
            500, 'not_applicable', counts, failure_state='internal_error',
            failure_reason='unexpected_server_fault',
            exception_class=tel.persisted_exception_class(error),
            provider_response=provider_response,
        )
        return {'error': 'Interview hints are unavailable right now. Please try again.'}, 500


def run_model_answer(data, deps):
    """The grounded/generic/compare job (/api/interview/model-answer)."""
    if not isinstance(data, dict):
        return {'error': 'Send one JSON object for the interview request.'}, 400
    question = str(data.get('question') or '').strip()
    # Slice 2: dropped before use once the flag is on — see run_review.
    if not deps.authenticated_studio:
        profile_slug = str(
            data.get('profile_slug') or deps.default_public_profile_slug
        ).strip()
    level = str(data.get('level') or 'experienced').strip()
    family = normalize_interview_family(data.get('family'))
    follow_up = str(data.get('follow_up') or '').strip()
    requested_mode = str(data.get('mode') or 'member_history').strip()
    if requested_mode not in ('member_history', 'best_practice', 'compare'):
        requested_mode = 'member_history'
    prior_answer = ''
    prior_illustrative_answer = ''
    try:
        opportunity_context = bounded_opportunity_context(data.get('opportunity_context'))
    except ValueError:
        return {'error': 'Please keep opportunity context under 4,000 characters.'}, 400

    # The authenticated Studio deliberately ships the follow-up control
    # disabled while interview_followup_mode_provenance is open: nothing there
    # can say which grounding mode a follow-up answer came from. The server
    # still accepted a follow-up carrying a validly signed context token, which
    # meant the only thing standing between a caller and that path was the
    # client. Refuse it here so the boundary lives on the server, where it
    # belongs. The public branch is untouched -- it still owns the working
    # follow-up affordance -- and re-opening this is a separate decision that
    # belongs to the follow-up package, not to a caller with a token.
    if follow_up and deps.authenticated_studio:
        return {'error': 'Follow-up questions are not available yet.'}, 400

    if follow_up:
        try:
            context = load_interview_model_context(
                deps.serializer, data.get('context_token'),
            )
        except ValueError as error:
            return {'error': str(error)}, 400
        if not hmac.compare_digest(
            context['opportunity_context_digest'],
            opportunity_context_digest(opportunity_context),
        ):
            return {'error': 'The follow-up opportunity context no longer matches the original answer.'}, 400
        if not deps.authenticated_studio:
            profile_slug = context['profile_slug']
        question = context['question']
        level = context['level']
        family = context['family']
        prior_answer = context['answer']
        prior_illustrative_answer = context.get('illustrative_answer', '')
        if requested_mode != context['mode']:
            return {'error': 'The follow-up answer source no longer matches the original answer.'}, 400
        mode = context['mode']
    else:
        mode = requested_mode

    if not question:
        return {'error': 'Ask an interview question first.'}, 400
    if len(question) > MAX_INTERVIEW_QUESTION_LENGTH or len(follow_up) > MAX_INTERVIEW_QUESTION_LENGTH:
        return {'error': 'That interview question is too long.'}, 400
    if level not in ('entry', 'experienced', 'management', 'leadership', 'mixed'):
        level = 'experienced'

    timer = tel.ServerCallAttempt()
    compare_mode = mode == 'compare'
    # PS-INTERVIEW-002 (v1.2): explicit grounding modes. member_history is
    # the original behavior; best_practice is a clearly generic example;
    # compare returns both so the member can study the structural lessons.
    if deps.authenticated_studio:
        with timer.phase('retrieval'):
            profile, evidence = deps.resolve_identity_context()
        # Bookkeeping only inside the signed follow-up context below — never
        # trusted as an input on the way back in (see the follow_up branch
        # above, which does not read context['profile_slug'] when the flag
        # is on).
        profile_slug = profile.get('slug') or 'member'
    else:
        if profile_slug not in deps.known_profile_slugs:
            return {'error': 'That interview profile is unavailable.'}, 404
        with timer.phase('retrieval'):
            profile, evidence = deps.resolve_public_context(profile_slug)
    evidence_by_id = {item['id']: item for item in evidence}
    evidence_lines = '\n'.join(
        '- [%s] %s — %s: %s' % (
            item['id'], item['metric'], item['label'], item['summary']
        )
        for item in evidence
    ) or '- No approved public evidence is available.'

    release, refusal = _release_or_refusal(
        deps,
        timer,
        specialist=(
            None if compare_mode
            else 'generic_example' if mode == 'best_practice'
            else 'grounded_example'
        ),
        composition='compare' if compare_mode else None,
    )
    if refusal:
        return refusal
    grounded_bundle = release.bundles['grounded_example']
    generic_bundle = release.bundles['generic_example']
    with timer.phase('manifest'):
        system_prompt = rendering.render_grounded_system(
            grounded_bundle, level, family, evidence_lines,
        )
        best_practice_system = rendering.render_generic_system(
            generic_bundle, level, family,
        )
        opportunity_block = untrusted_opportunity_block(opportunity_context)
        grounded_user_content = rendering.render_model_answer_user(
            grounded_bundle, question, opportunity_block,
        )
        illustrative_user_content = rendering.render_model_answer_user(
            generic_bundle, question, opportunity_block,
        )
        if follow_up:
            grounded_user_content += rendering.render_grounded_followup_suffix(
                grounded_bundle, prior_answer, follow_up,
            )
            # In compare mode the signed primary answer is profile-grounded. The
            # illustrative branch must not receive that history, even as conversational
            # context, or the generic example can leak or imitate profile facts.
            illustrative_user_content += rendering.render_generic_followup_suffix(
                generic_bundle, follow_up,
            )
            if mode == 'best_practice':
                illustrative_user_content += (
                    rendering.render_generic_followup_prior_best_practice(
                        generic_bundle, prior_answer,
                    )
                )
            elif mode == 'compare':
                illustrative_user_content += (
                    rendering.render_generic_followup_prior_compare(
                        generic_bundle, prior_illustrative_answer,
                    )
                )

    # Holds the most recent provider reply so a rejection can be attributed to a
    # cause. Only the stop reason and a character count are ever logged.
    last_reply = {'text': '', 'stop_reason': ''}
    call_records = []

    def _generate(system_text, user_text, illustrative=False):
        # An illustrative best-practice example is not grounded in this member's
        # approved evidence, so it is validated against an empty evidence map
        # and is not required to cite anything. It is still rejected if it cites
        # an id, because nothing is authorized for a generic example.
        bundle = generic_bundle if illustrative else grounded_bundle
        call_timer = tel.ServerCallAttempt() if compare_mode else timer
        # Correction C5: a follow-up request really sends two questions (the
        # original and the interviewer follow-up) and one prior
        # server-validated answer; the counts describe the actual provider
        # request, and this is not History.
        record = {
            'timer': call_timer,
            'specialist': 'generic_example' if illustrative else 'grounded_example',
            'bundle': bundle,
            'counts': tel.source_class_counts(
                question=2 if follow_up else 1,
                answer=1 if follow_up else 0,
                role_context=1 if opportunity_context else 0,
                member_evidence=0 if illustrative else len(evidence),
            ),
            'response': None,
            'outcome': None,
        }
        call_records.append(record)
        with call_timer.phase('provider'):
            api_response = deps.provider_client.messages.create(
                model=bundle.model,
                max_tokens=bundle.max_tokens,
                system=system_text,
                messages=[{'role': 'user', 'content': user_text}],
            )
        record['response'] = api_response
        last_reply['stop_reason'] = getattr(api_response, 'stop_reason', '') or ''
        with call_timer.phase('validate'):
            last_reply['text'] = api_response.content[0].text
            validated = validate_interview_model_answer(
                extract_json_object(last_reply['text']),
                {} if illustrative else evidence_by_id,
                require_evidence=not illustrative,
            )
        record['outcome'] = (
            'computed_outcome' if validated.get('status') == 'insufficient'
            else 'success'
        )
        return validated

    def _finalize_rows(http_status, failure_state=None, failure_reason=None,
                       exception_class=None, exception_attrs=None):
        parent_uuid = timer.attempt_uuid if compare_mode else None
        failing_record = None
        if failure_state is not None:
            for candidate_record in call_records:
                if candidate_record['outcome'] is None:
                    failing_record = candidate_record
                    break
            if failing_record is None and not compare_mode and call_records:
                # A post-validation fault on the single-specialist path still
                # belongs to its one row.
                failing_record = call_records[-1]
        child_outcomes = [
            record['outcome'] or 'failed' for record in call_records
        ]
        if compare_mode:
            # The parent row is appended first: the schema's parent/child
            # foreign key requires the parent to exist before any child row
            # referencing it (correction C3).
            if failure_state is not None:
                parent_outcome = 'failed'
            elif 'computed_outcome' in child_outcomes:
                parent_outcome = 'computed_outcome'
            else:
                parent_outcome = 'success'
            _append_event(
                deps.logger,
                lambda: tel.build_event(
                    timer,
                    'composition_parent',
                    parent_outcome,
                    http_status,
                    'not_applicable',
                    tel.source_class_counts(),
                    composition='compare',
                    release_set_id=release.release_set_id,
                    failure_state=(
                        failure_state if parent_outcome == 'failed' else None
                    ),
                    failure_reason=(
                        failure_reason if parent_outcome == 'failed' else None
                    ),
                ),
            )
        for record in call_records:
            if record is failing_record:
                outcome = 'failed'
                validation_result = (
                    'rejected' if failure_state == 'invalid_output'
                    else 'not_applicable'
                )
                row_state, row_reason = failure_state, failure_reason
                row_exception, row_attrs = exception_class, exception_attrs
            else:
                outcome = record['outcome'] or 'success'
                validation_result = 'passed'
                row_state = row_reason = row_exception = row_attrs = None
            _finalize_specialist_row(
                deps.logger, record['timer'], record['specialist'],
                record['bundle'], release, outcome, http_status,
                validation_result, record['counts'], failure_state=row_state,
                failure_reason=row_reason, exception_class=row_exception,
                exception_attrs=row_attrs,
                provider_response=record['response'],
                parent_attempt_uuid=parent_uuid,
            )

    try:
        best_practice_answer = None
        if mode == 'best_practice':
            model_answer = _generate(
                best_practice_system, illustrative_user_content, illustrative=True,
            )
            model_answer['generic'] = True
        elif mode == 'compare':
            model_answer = _generate(system_prompt, grounded_user_content)
            best_practice_answer = _generate(
                best_practice_system, illustrative_user_content, illustrative=True,
            )
            best_practice_answer['generic'] = True
        else:
            model_answer = _generate(system_prompt, grounded_user_content)
        with timer.phase('respond'):
            context_token = sign_interview_model_context(
                deps.serializer,
                profile_slug,
                question,
                level,
                family,
                mode,
                model_answer,
                best_practice_answer if mode == 'compare' else None,
                opportunity_context,
            )
            payload = {
                'mode': mode,
                'modelAnswer': model_answer,
                'contextToken': context_token,
                'profile': {
                    'displayName': profile.get('name') or 'Candidate',
                    'firstName': profile.get('first_name') or 'Candidate',
                },
            }
            if best_practice_answer is not None:
                payload['bestPractice'] = best_practice_answer
        _finalize_rows(200)
        return payload, 200
    except _VALIDATION_ERRORS as error:
        log_interview_failure(
            deps.logger,
            'Interview model-answer validation error',
            error,
            last_reply['stop_reason'],
            len(last_reply['text']),
        )
        reason, exception_class = tel.classify_validation_error(error)
        _finalize_rows(
            502, failure_state='invalid_output', failure_reason=reason,
            exception_class=exception_class,
            exception_attrs={
                'provider_stop_reason': tel.normalize_stop_reason(
                    last_reply['stop_reason']
                ),
                'reply_chars': len(last_reply['text']),
            },
        )
        return {'error': 'The answer could not be validated against the profile evidence. Please try again.'}, 502
    except anthropic.APIError as error:
        reason, exception_class, provider_status = tel.normalize_provider_error(error)
        deps.logger.error(
            'Interview model-answer provider error: class=%s status=%s',
            exception_class,
            provider_status if provider_status is not None else 'none',
        )
        _finalize_rows(
            500, failure_state='provider_failure', failure_reason=reason,
            exception_class=exception_class,
            exception_attrs=(
                {'status_code': provider_status}
                if provider_status is not None else {}
            ),
        )
        return {'error': 'Interview AI is unavailable right now. Please try again.'}, 500
    except Exception as error:
        deps.logger.error(
            'Interview model-answer API error: class=%s',
            tel.normalize_exception_class(error),
        )
        _finalize_rows(
            500, failure_state='internal_error',
            failure_reason='unexpected_server_fault',
            exception_class=tel.persisted_exception_class(error),
        )
        return {'error': 'Interview AI is unavailable right now. Please try again.'}, 500
