"""Owner Resume publication review/publish API and private preview.

REGISTERED, AND OFF unless PEERSLATE_RESUME_PUBLICATION_ENABLED is True.
Identity is server-derived. Review does not publish. F guest endpoints have
their own default-off gate and never consult the signed-in owner's sources.
"""

from __future__ import annotations

from types import MappingProxyType
from hashlib import sha256
from uuid import uuid4

from flask import (
    Blueprint,
    abort,
    current_app,
    copy_current_request_context,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)

from identity import AuthenticationRequired, get_current_identity
from services.database_service import DatabaseServiceError
from services.resume_publication_contracts import ContractError, ReadState
from services.member_visitor_ai_sources import strict_json
from services.member_visitor_ai_service import (
    MemberVisitorAiService, MESSAGES, OperationalRefusal, ResultState, VisitorAiRuntime,
)
from services.resume_publication_service import (
    PublicationConflictError,
    PublicationDenied,
    PublicationUnavailableError,
    PublicationValidationError,
    resume_publication_service,
)


resume_publication = Blueprint("resume_publication", __name__)

PLANNED_RATE_LIMITS = MappingProxyType(
    {
        "resume_publication.get_resume_publication_page": "60 per minute",
        "resume_publication.review_resume_publication": "30 per hour",
        "resume_publication.commit_resume_publication": "30 per hour",
        "resume_publication.preview_resume_publication": "60 per minute",
    }
)


def _enabled() -> bool:
    return current_app.config.get("PEERSLATE_RESUME_PUBLICATION_ENABLED", False) is True


def _service():
    return current_app.config.get("RESUME_PUBLICATION_SERVICE") or resume_publication_service


def visitor_ai_enabled():
    return _enabled() and current_app.config.get('PEERSLATE_MEMBER_VISITOR_AI_ENABLED', False) is True


def _ai_service():
    return current_app.config.get('MEMBER_VISITOR_AI_SERVICE')


def visitor_ai_heading(slug=None):
    name = None
    service = _ai_service()
    if visitor_ai_enabled() and slug is not None and isinstance(service, MemberVisitorAiService):
        name = service.approved_guest_name(slug)
    return 'Ask ' + name + ' AI' if name else ('Ask about this Resume' if slug is not None else 'Try visitor AI')


class RequestVisitorOwner:
    def current_owner_key(self):
        return get_current_identity().user_key


def install_member_visitor_ai(app, *, database, settings=None, token_provider=None, transport=None):
    """One startup composition path, also exercised with stub transport in tests.

    Missing/invalid settings stay unavailable. Construction never acquires a
    token, invokes HTTP, or enables either independent feature flag.
    """
    from services.member_visitor_ai_repository import SqlMemberVisitorAiRepository
    from services.member_visitor_ai_service import (UnavailableVisitorProvider, build_configured_visitor_ai)
    from services.ai_foundation.gateway import AIFoundationGateway
    from services.ai_foundation.azure_foundry import FOUNDRY_TOKEN_SCOPE
    draft_service = None
    if app.config.get('PEERSLATE_RESUME_EDITOR_ENABLED'):
        from services.resume_draft_service import resume_draft_service as default_draft_service
        draft_service = app.config.get('RESUME_DRAFT_SERVICE') or default_draft_service
    repository = SqlMemberVisitorAiRepository(database, identity=RequestVisitorOwner(), draft_service=draft_service)
    service = MemberVisitorAiService(repository, repository, AIFoundationGateway(UnavailableVisitorProvider()))
    runtime = None
    configured = False
    if settings is not None:
        try:
            if type(settings) is str:
                settings = strict_json(settings)
            if token_provider is None:
                from azure.identity import DefaultAzureCredential
                credential = DefaultAzureCredential(exclude_interactive_browser_credential=True)
                token_provider = lambda: credential.get_token(FOUNDRY_TOKEN_SCOPE).token
            service, runtime = build_configured_visitor_ai(repository, settings,
                token_provider=token_provider, transport=transport,
                protections=app.config.get('MEMBER_VISITOR_AI_PROTECTIONS'))
            configured = True
        except Exception:
            app.logger.error('Visitor AI configuration is unavailable.')
    binding = app.config.get('MVP1_PROFILE_BINDING')
    if binding is not None:
        from services.mvp1_profile_binding import PinnedResumeNamePort
        from services.resume_publication_repository import SqlResumePublicationRepository
        service.names = PinnedResumeNamePort(binding, SqlResumePublicationRepository(database))
    app.config['MEMBER_VISITOR_AI_SERVICE'] = service
    app.config['MEMBER_VISITOR_AI_RUNTIME'] = runtime
    return configured


def _wants_json() -> bool:
    return request.path.startswith("/api/")


@resume_publication.before_request
def gate_and_protect_writes():
    if not _enabled():
        if _wants_json():
            return jsonify({"success": False, "message": "Not found."}), 404
        abort(404)
    if request.method not in {"POST", "PATCH", "PUT", "DELETE"}:
        return None
    if request.headers.get("X-PeerSlate-Request") != "same-origin":
        return jsonify(
            {"success": False, "message": "A same-origin request header is required."}
        ), 403
    origin = request.headers.get("Origin")
    if origin and origin.rstrip("/") != request.host_url.rstrip("/"):
        return jsonify(
            {"success": False, "message": "Cross-origin writes are not allowed."}
        ), 403
    return None


@resume_publication.after_request
def private_no_store(response):
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers['X-Robots-Tag'] = 'noindex, nofollow, noarchive'
    response.headers['Referrer-Policy'] = 'no-referrer'
    return response


def _identity_or_not_found():
    try:
        return get_current_identity()
    except AuthenticationRequired:
        return None
    except DatabaseServiceError:
        raise


def _json_body():
    payload = request.get_json(silent=True)
    if payload is None:
        payload = {}
    if isinstance(payload, dict):
        payload = {
            key: value
            for key, value in payload.items()
            if key not in {"owner_user_key", "user_key", "owner_profile_id", "bypass"}
        }
    return payload


def _onboarding_preview_sections(owner, result):
    """Owner-only presentation metadata; never changes publication authority."""
    intake = current_app.config.get('RESUME_INTAKE_SERVICE')
    if (intake is None or current_app.config.get('PEERSLATE_RESUME_INTAKE_ENABLED') is not True
            or getattr(getattr(intake, 'repository', None), 'supports_resume_conversation', False) is not True):
        return result
    from services.resume_intake_service import ResumeIntakeUnavailableError
    try:
        workspace = intake.get_workspace(owner)
    except ResumeIntakeUnavailableError as error:
        raise PublicationUnavailableError('Private Resume selections are unavailable.') from error
    if workspace.get('resume_decision_conflicts'):
        raise PublicationConflictError('history_review_required',
            'Review the saved Resume choices in the guide before previewing. Your approved information is kept.')
    excluded = {key for key, value in workspace.get('resume_excluded_records') or [] if key and value}
    bindings = workspace.get('resume_section_bindings') or {}
    credential_links = {b['credential_key']: b for b in workspace.get('resume_credential_bindings') or []
                        if b.get('owner_user_key') == owner}
    credential_notes = {b['supplement_key'] for b in credential_links.values()}
    sections = {'Awards': 'awards', 'Professional summary': 'professional_summary',
                'Contact details': 'contact_details', 'Independent Project': 'independent_projects'}
    display = {}
    for key, entry in result.get('display', {}).items():
        if key in excluded or key in credential_notes:
            continue
        wording = entry.get('wording') or {}
        if entry.get('canonical_type') == 'knowledge':
            if wording.get('classification') == 'personal' and entry.get('presentation_section') != 'story':
                continue
            if wording.get('classification') == 'work' and entry.get('presentation_section') == 'story':
                raise PublicationConflictError('stale_preview', 'Choose a personal entry for My Story.')
            # B3c m2 (D6c review): Publish keeps a placed Looking Ahead entry and a My Story entry where they are, so the
            # preview must too; an onboarding section binding only sorts the rest.
            if bindings.get(key) in sections and entry.get('presentation_section') not in {'story', 'looking_ahead'}:
                entry = {**entry, 'presentation_section': sections[bindings[key]]}
        display[key] = entry
    for key, link in credential_links.items():
        if key not in display:
            continue
        parent, note = display[key], result.get('display', {}).get(link['supplement_key'])
        if (parent.get('canonical_type') != 'credential' or note is None
                or note.get('canonical_type') != 'knowledge'
                or note.get('wording', {}).get('classification') != 'work'
                or link['supplement_key'] in excluded):
            raise PublicationConflictError('stale_preview', 'Review the credential together with its complete details and limitations.')
        display[key] = {**parent, 'credential_details': note['wording']['wording']}
    return {**result, 'display': display}


@resume_publication.get("/app/resume/publication")
def get_resume_publication_page():
    try:
        identity = get_current_identity()
    except AuthenticationRequired:
        return redirect(url_for("auth.sign_in", return_to="/app/resume/publication"))
    except DatabaseServiceError:
        current_app.logger.error("Resume publication identity lookup failed.")
        abort(503)
    return render_template(
        "resume_publication.html",
        page_title="Publish Resume",
        member=identity,
        review_url="/api/resume-publication/me/review",
        commands_url="/api/resume-publication/me/commands",
        preview_url="/api/resume-publication/me/preview",
        visitor_ai_enabled=visitor_ai_enabled(),
        visitor_ai_heading=visitor_ai_heading(),
    )


@resume_publication.route("/api/resume-publication/me/preview", methods=["GET", "POST"])
def preview_resume_publication():
    identity = _identity_or_not_found()
    if identity is None:
        return jsonify({"success": False, "message": "Not found."}), 404
    try:
        payload = _json_body() if request.method == "POST" else None
        result = _service().draft_preview(identity.user_key, payload)
        result = _onboarding_preview_sections(identity.user_key, result)
        if request.method == "POST":
            original = result
            result["html"] = render_template(
                "resume_publication.html", page_title="Private Resume preview",
                member=identity, is_public_reader=True, is_private_preview=True,
                public_publication=result, visitor_ai_enabled=False, profile_slug=None,
            )
            fresh = _onboarding_preview_sections(identity.user_key, _service().draft_preview(identity.user_key, payload))
            if fresh != {key:value for key,value in original.items() if key != 'html'}:
                raise PublicationConflictError('stale_preview', 'The private Resume changed. Review it again.')
    except (PublicationValidationError, ContractError) as error:
        return jsonify({"success": False, "code": "invalid", "message": str(error)}), 400
    except PublicationDenied:
        return jsonify({"success": False, "code": "stale_preview", "message": "The private preview changed. Review again."}), 409
    except PublicationConflictError as error:
        return jsonify({"success": False, "code": error.code, "message": str(error)}), 409
    except PublicationUnavailableError:
        return jsonify({"success": False, "code": "unavailable", "message": "Publication is unavailable."}), 503
    return jsonify({"success": True, **result, "published": False})


@resume_publication.get("/api/resume-publication/me/preview/media/<string:slot>")
def preview_resume_media(slot):
    identity = _identity_or_not_found()
    if identity is None:
        return jsonify({"success": False, "message": "Not found."}), 404
    from resume_media_routes import _media_response
    from services.resume_media_service import ResumeMediaError
    from services.resume_media_application import ResumeMediaApplicationUnavailable
    try:
        opened = _service().open_private_preview_media(identity.user_key, slot, request.args.get("expected"))
    except (PublicationDenied, PublicationUnavailableError, ResumeMediaError, ResumeMediaApplicationUnavailable):
        return jsonify({"success": False, "message": "Private preview media is unavailable. Review again."}), 404
    return _media_response(opened)


@resume_publication.post("/api/resume-publication/me/review")
def review_resume_publication():
    identity = _identity_or_not_found()
    if identity is None:
        return jsonify({"success": False, "message": "Not found."}), 404
    payload = _json_body()
    try:
        result = _service().review_for_owner(identity.user_key, payload)
    except (PublicationValidationError, ContractError) as error:
        return jsonify({"success": False, "code": "invalid", "message": str(error)}), 400
    except PublicationConflictError as error:
        return jsonify({"success": False, "code": error.code, "message": str(error)}), 409
    except PublicationUnavailableError:
        return jsonify({"success": False, "code": "unavailable", "message": "Publication is unavailable."}), 503
    if result.reviewed is None:
        refusal = {"success": False, "code": result.reason, "state": result.state.value}
        if result.blocked_items:
            refusal["blocked_items"] = [{"item_ref": ref, "reason": reason}
                                        for ref, reason in result.blocked_items]
        return jsonify(refusal), 409
    reference = result.reviewed.candidate.profile_identity
    approved_identity = None
    if reference is not None:
        binding = _service().profile_binding
        approved_identity = binding.resolve(identity.user_key, reference) if binding else None
        if approved_identity is None:
            return jsonify({"success": False, "code": "stale_identity",
                            "message": "Profile identity changed. Review it again."}), 409
    return jsonify(
        {
            "success": True,
            "state": result.state.value,
            "reason": result.reason,
            "digest": result.reviewed.digest,
            "candidate": _service().publish_candidate(result.reviewed),
            "entries": _service().review_details(result.reviewed),
            "profile_identity": reference.to_payload() if reference else None,
            "identity_display_name": approved_identity.display_name if approved_identity else None,
            "display_count": len(result.reviewed.display.entries),
            "visitor_ai_count": len(result.reviewed.visitor_ai.entries),
        }
    )


@resume_publication.post("/api/resume-publication/me/commands")
def commit_resume_publication():
    identity = _identity_or_not_found()
    if identity is None:
        return jsonify({"success": False, "message": "Not found."}), 404
    payload = _json_body()
    try:
        if payload.get('type') == 'publish':
            intake = current_app.config.get('RESUME_INTAKE_SERVICE')
            if (intake is not None and current_app.config.get('PEERSLATE_RESUME_INTAKE_ENABLED') is True
                    and getattr(getattr(intake, 'repository', None), 'supports_resume_conversation', False) is True):
                from services.resume_intake_service import ResumeIntakeUnavailableError
                try:
                    workspace = intake.get_workspace(identity.user_key)
                except ResumeIntakeUnavailableError as error:
                    raise PublicationUnavailableError('Credential selections are unavailable.') from error
                envelope = payload.get('candidate')
                rows = envelope.get('entries', []) if isinstance(envelope, dict) else []
                selected = {r.get('entry_key') for r in rows if isinstance(r, dict)
                            and (r.get('resume_display') or r.get('visitor_ai'))} if isinstance(rows, list) else set()
                for conflict in workspace.get('resume_decision_conflicts') or []:
                    affected = {conflict['record_key']}
                    if conflict['effect'] == 'credential':
                        affected.update(choice['value'].get('supplement_key') for choice in conflict['choices'])
                    if affected & selected:
                        raise PublicationConflictError('history_review_required',
                            'Review the saved Resume choices in the guide before sharing this entry.')
                if any(b.get('credential_key') in selected or b.get('supplement_key') in selected
                       for b in workspace.get('resume_credential_bindings') or []):
                    raise PublicationConflictError('credential_details_private',
                        'Complete credential details are available in your private Resume. '
                        'Public sharing of these linked records is unavailable; leave both out of this publication.')
        result = _service().commit(identity.user_key, payload)
    except (PublicationValidationError, ContractError) as error:
        return jsonify({"success": False, "code": "invalid", "message": str(error)}), 400
    except PublicationConflictError as error:
        return jsonify({"success": False, "code": error.code, "message": str(error)}), 409
    except PublicationDenied as error:
        return jsonify({"success": False, "code": error.code, "message": str(error)}), 409
    except PublicationUnavailableError:
        return jsonify({"success": False, "code": "unavailable", "message": "Publication is unavailable."}), 503
    try:
        current = _service().owner_preview(identity.user_key)
        availability = {"state": "current", "sharing_enabled": current["sharing_enabled"],
                        "publication_revision": current["publication_revision"]}
    except PublicationUnavailableError:
        availability = {"state": "unavailable"}
    return jsonify({"success": True, **result, "availability": availability})


def _ai_boundary(state=ResultState.UNAVAILABLE, *, status=503, question=''):
    response = jsonify({'state': state.value, 'question': question,
                        'text': MESSAGES[state], 'citations': []})
    if status == 429:
        runtime = current_app.config.get('MEMBER_VISITOR_AI_RUNTIME')
        if isinstance(runtime, VisitorAiRuntime):
            response.headers['Retry-After'] = str(max(1, int(runtime.limits.window_seconds)))
    return response, status


def _bounded_ai_response(callback, finalizer):
    runtime = current_app.config.get('MEMBER_VISITOR_AI_RUNTIME')
    if not isinstance(runtime, VisitorAiRuntime):
        raise OperationalRefusal(unavailable=True)
    client_key = sha256(('visitor-ai:' + (request.remote_addr or 'unknown')).encode()).hexdigest()
    return runtime.run_response(copy_current_request_context(callback),
                                copy_current_request_context(finalizer), client_key=client_key)


def _ai_request_body(runtime, *, preview):
    # Limit reads even for chunked/unknown content-length requests. Never parse
    # an unbounded body or silently truncate a question.
    maximum = runtime.limits.maximum_request_bytes
    if request.content_length is not None and request.content_length > maximum:
        raise ValueError('request too large')
    if request.mimetype != 'application/json':
        raise ValueError('JSON required')
    raw = request.stream.read(maximum + 1)
    if len(raw) > maximum:
        raise ValueError('request too large')
    body = strict_json(raw.decode('utf-8'))
    fields = {'question', 'draft_revision', 'choices'} if preview else {'question'}
    if type(body) is not dict or set(body) != fields:
        raise ValueError('closed request required')
    question = body['question']
    if (type(question) is not str or not question.strip()
            or len(question) > runtime.limits.maximum_question_characters):
        raise ValueError('question size')
    if preview:
        if type(body['draft_revision']) is not int or body['draft_revision'] < 0:
            raise ValueError('draft version')
        if type(body['choices']) is not list or len(body['choices']) > 100:
            raise ValueError('explicit choices required')
        seen = set()
        for item in body['choices']:
            if (type(item) is not dict or set(item) != {'entry_key', 'selected'}
                    or type(item['entry_key']) is not str or not item['entry_key']
                    or item['entry_key'] in seen or type(item['selected']) is not bool):
                raise ValueError('invalid choice')
            seen.add(item['entry_key'])
    return body


def _answer_question(*, slug=None, preview=False):
    if not visitor_ai_enabled():
        abort(404)
    if preview:
        try:
            if _identity_or_not_found() is None:
                abort(404)
        except DatabaseServiceError:
            return _ai_boundary()
    runtime, service = current_app.config.get('MEMBER_VISITOR_AI_RUNTIME'), _ai_service()
    if not isinstance(runtime, VisitorAiRuntime) or not isinstance(service, MemberVisitorAiService):
        return _ai_boundary()
    try:
        body = _ai_request_body(runtime, preview=preview)
    except (ValueError, UnicodeError):
        return jsonify({'state': 'invalid', 'text': 'Check your question and try again.', 'citations': []}), 400
    question = body['question']

    def ask():
        if preview:
            binding = service.sources.prepare_preview(expected_draft_revision=body['draft_revision'],
                choices=tuple((item['entry_key'], item['selected']) for item in body['choices']))
            return service.ask_preview(binding=binding, question=question, request_id=str(uuid4()))
        return service.ask_guest(slug=slug, question=question, request_id=str(uuid4()))

    def finalize(result):
        citations = []
        for item in result.citations:
            if item.handle is None:
                # HTTP composition needs independently accessible citations.
                return current_app.make_response(_ai_boundary(question=question))
            endpoint = ('resume_publication.preview_ai_citation' if preview
                        else 'resume_publication.guest_ai_citation')
            arguments = {'handle': item.handle} if preview else {'handle': item.handle, 'slug': slug}
            citations.append({'label': item.label, 'excerpt': item.excerpt,
                              'url': url_for(endpoint, **arguments)})
        response = jsonify({'state': result.state.value, 'question': result.question,
                            'text': result.text, 'citations': citations})
        if not service.release_is_current(result):
            return current_app.make_response(_ai_boundary(ResultState.RETRYABLE, question=question))
        if result.state in {ResultState.UNAVAILABLE, ResultState.RETRYABLE}:
            response.status_code = 503
        return response
    try:
        return _bounded_ai_response(ask, finalize)
    except OperationalRefusal as error:
        return _ai_boundary(ResultState.UNAVAILABLE if error.unavailable else ResultState.RETRYABLE,
                            status=503 if error.unavailable else 429, question=question)
    except Exception:
        return _ai_boundary(question=question)


@resume_publication.post('/api/public/profiles/<slug>/ai/questions')
def guest_ai_question(slug):
    if slug in current_app.config.get('PEERSLATE_RESUME_FIXTURE_SLUGS', {'petec'}):
        abort(404)
    return _answer_question(slug=slug)


@resume_publication.post('/api/resume/me/visitor-preview/questions')
def preview_ai_question():
    return _answer_question(preview=True)


@resume_publication.get('/api/resume/me/visitor-preview/sources')
def preview_ai_sources():
    if not visitor_ai_enabled():
        abort(404)
    try:
        identity = _identity_or_not_found()
    except DatabaseServiceError:
        return _ai_boundary()
    if identity is None:
        abort(404)
    try:
        service = _ai_service()
        return _bounded_ai_response(lambda:None, lambda _:jsonify(service.sources.preview_choices()))
    except Exception:
        return _ai_boundary()


def _read_ai_citation(handle, *, slug=None, preview=False):
    if not visitor_ai_enabled():
        abort(404)
    if preview:
        try:
            identity = _identity_or_not_found()
        except DatabaseServiceError:
            identity = None
        if identity is None:
            abort(404)
    service = _ai_service()
    def denied():
        return jsonify({'state': 'unavailable', 'text': 'This source excerpt is unavailable.'}), 404
    if not isinstance(service, MemberVisitorAiService):
        return denied()
    def finalize(citation):
        if citation is None:
            return current_app.make_response(denied())
        response = jsonify({'label': citation.label, 'excerpt': citation.excerpt})
        if not service.citation_is_current(citation):
            return current_app.make_response(denied())
        return response
    try:
        return _bounded_ai_response(lambda:service.read_citation(handle, slug=slug, owner_preview=preview), finalize)
    except Exception:
        return denied()


@resume_publication.get('/api/public/profiles/<slug>/ai/citations/<handle>')
def guest_ai_citation(slug, handle):
    if slug in current_app.config.get('PEERSLATE_RESUME_FIXTURE_SLUGS', {'petec'}):
        abort(404)
    return _read_ai_citation(handle, slug=slug)


@resume_publication.get('/api/resume/me/visitor-preview/citations/<handle>')
def preview_ai_citation(handle):
    return _read_ai_citation(handle, preview=True)
