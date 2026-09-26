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
from services.resume_publication_contracts import ReadState
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
    repository = SqlMemberVisitorAiRepository(database, identity=RequestVisitorOwner())
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


@resume_publication.get("/api/resume-publication/me/preview")
def preview_resume_publication():
    identity = _identity_or_not_found()
    if identity is None:
        return jsonify({"success": False, "message": "Not found."}), 404
    try:
        result = _service().owner_preview(identity.user_key)
    except PublicationUnavailableError:
        return jsonify({"success": False, "code": "unavailable", "message": "Publication is unavailable."}), 503
    return jsonify({"success": True, **result, "published": False})


@resume_publication.post("/api/resume-publication/me/review")
def review_resume_publication():
    identity = _identity_or_not_found()
    if identity is None:
        return jsonify({"success": False, "message": "Not found."}), 404
    payload = _json_body()
    try:
        result = _service().review_for_owner(identity.user_key, payload)
    except PublicationUnavailableError:
        return jsonify({"success": False, "code": "unavailable", "message": "Publication is unavailable."}), 503
    if result.reviewed is None:
        return jsonify({"success": False, "code": result.reason, "state": result.state.value}), 409
    return jsonify(
        {
            "success": True,
            "state": result.state.value,
            "reason": result.reason,
            "digest": result.reviewed.digest,
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
        result = _service().commit(identity.user_key, payload)
    except PublicationValidationError as error:
        return jsonify({"success": False, "code": "invalid", "message": str(error)}), 400
    except PublicationConflictError as error:
        return jsonify({"success": False, "code": error.code, "message": str(error)}), 409
    except PublicationDenied as error:
        return jsonify({"success": False, "code": error.code, "message": str(error)}), 409
    except PublicationUnavailableError:
        return jsonify({"success": False, "code": "unavailable", "message": "Publication is unavailable."}), 503
    return jsonify({"success": True, **result})


def _ai_boundary(state=ResultState.UNAVAILABLE, *, status=503, question=''):
    response = jsonify({'state': state.value, 'question': question,
                        'text': MESSAGES[state], 'citations': []})
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
