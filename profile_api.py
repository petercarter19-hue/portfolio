"""Unregistered Profile D0 JSON blueprint.

The API exposes contract-only endpoints for isolated tests.  It accepts no
browser actor, audience, owner, source body, or session identity.  A later
integration layer must derive the actor server-side and bind anti-CSRF and
same-origin protections before registration.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Callable, Mapping

from flask import Blueprint, Response, current_app, jsonify, request

from services.profile_core_service import (
    ProfileAuthorizationError,
    ProfileConflictError,
    ProfileCoreService,
    ProfileNotFound,
    ProfileUnavailableError,
    ProfileValidationError,
    ProfileViewerContext,
)


profile_api = Blueprint("profile_api", __name__, url_prefix="/api/v1/profile-foundation")


def _service() -> ProfileCoreService:
    provider: Callable[[], ProfileCoreService] | None = current_app.config.get(
        "PEERSLATE_PROFILE_CORE_SERVICE_PROVIDER"
    )
    if provider is None:
        raise ProfileUnavailableError("Profile foundation dependency unavailable.")
    service = provider()
    if not isinstance(service, ProfileCoreService):
        raise ProfileUnavailableError("Profile foundation dependency unavailable.")
    return service


def _owner_context() -> ProfileViewerContext:
    """Receive a *server-provided test adapter*, never client identity values.

    Production registration must replace this provider with Easy Auth identity
    resolution and a profile lookup.  The route layer intentionally rejects
    request values such as ``actor_key`` or ``audience`` rather than using
    them as a shortcut.
    """

    provider: Callable[[], ProfileViewerContext] | None = current_app.config.get(
        "PEERSLATE_PROFILE_CORE_OWNER_CONTEXT_PROVIDER"
    )
    if provider is None:
        raise ProfileUnavailableError("Profile foundation identity unavailable.")
    context = provider()
    if not isinstance(context, ProfileViewerContext):
        raise ProfileUnavailableError("Profile foundation identity unavailable.")
    return context


def _json_object() -> Mapping[str, object]:
    if not request.is_json:
        raise ProfileValidationError("Write requests must use JSON.")
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise ProfileValidationError("Write requests require an object body.")
    prohibited = {"actor_key", "owner_key", "subject_owner_key", "audience", "mode"}
    if prohibited.intersection(body):
        raise ProfileValidationError("Profile identity and audience are server-derived.")
    return body


@profile_api.before_request
def profile_api_write_fence():
    if request.method in {"POST", "PATCH", "PUT", "DELETE"}:
        if request.headers.get("X-PeerSlate-Request") != "same-origin":
            return _error("same_origin_required", 403)
        origin = request.headers.get("Origin")
        if origin and origin.rstrip("/") != request.host_url.rstrip("/"):
            return _error("same_origin_required", 403)
        fetch_site = request.headers.get("Sec-Fetch-Site")
        if fetch_site and fetch_site not in {"same-origin", "none"}:
            return _error("same_origin_required", 403)
    return None


@profile_api.get("/public/<string:profile_slug>/<string:destination>")
def public_destination(profile_slug: str, destination: str):
    try:
        model = _service().public_read(slug=profile_slug, destination=destination)
    except (ProfileNotFound, ProfileAuthorizationError):
        return _error("not_found", 404)
    except ProfileUnavailableError:
        return _error("unavailable", 503)
    return jsonify(success=True, profile=asdict(model))


@profile_api.get("/owner/state")
def owner_state():
    try:
        model = _service().owner_state(_owner_context())
    except (ProfileNotFound, ProfileAuthorizationError):
        return _error("not_found", 404)
    except ProfileUnavailableError:
        return _error("unavailable", 503)
    return jsonify(success=True, owner=asdict(model))


@profile_api.get("/owner/preview/public/<string:destination>")
def owner_public_preview(destination: str):
    try:
        model = _service().owner_preview_public(_owner_context(), destination=destination)
    except (ProfileNotFound, ProfileAuthorizationError):
        return _error("not_found", 404)
    except ProfileUnavailableError:
        return _error("unavailable", 503)
    return jsonify(success=True, profile=asdict(model))


@profile_api.patch("/owner/draft")
def update_draft():
    try:
        body = _json_object()
        draft = _service().update_native_draft(
            _owner_context(),
            expected_version=body.get("expected_version"),
            identity=body.get("identity"),
            current_chapter=body.get("current_chapter"),
            about=body.get("about"),
        )
    except ProfileValidationError as error:
        return _error("invalid_request", 400, str(error))
    except ProfileConflictError as error:
        return _error("conflict", 409, str(error))
    except (ProfileNotFound, ProfileAuthorizationError):
        return _error("not_found", 404)
    except ProfileUnavailableError:
        return _error("unavailable", 503)
    return jsonify(success=True, draft=_draft_summary(draft))


@profile_api.post("/owner/publication/review")
def review_publication():
    try:
        body = _json_object()
        review = _service().review_publication(
            _owner_context(),
            expected_draft_version=body.get("expected_draft_version"),
            expected_public_revision=body.get("expected_public_revision"),
        )
    except ProfileValidationError as error:
        return _error("invalid_request", 400, str(error))
    except ProfileConflictError as error:
        return _error("conflict", 409, str(error))
    except (ProfileNotFound, ProfileAuthorizationError):
        return _error("not_found", 404)
    except ProfileUnavailableError:
        return _error("unavailable", 503)
    return jsonify(success=True, review=review)


@profile_api.post("/owner/publication/publish")
def publish_publication():
    try:
        body = _json_object()
        command = _service().publish_publication(
            _owner_context(),
            expected_draft_version=body.get("expected_draft_version"),
            expected_public_revision=body.get("expected_public_revision"),
            candidate_digest=body.get("candidate_digest"),
            idempotency_key=request.headers.get("Idempotency-Key") or "",
            confirmed=body.get("confirmed") is True,
        )
    except ProfileValidationError as error:
        return _error("invalid_request", 400, str(error))
    except ProfileConflictError as error:
        return _error("conflict", 409, str(error))
    except (ProfileNotFound, ProfileAuthorizationError):
        return _error("not_found", 404)
    except ProfileUnavailableError:
        return _error("unavailable", 503)
    return jsonify(
        success=True,
        command_key=command.command_key,
        public_revision=command.revision.revision_key,
        candidate_digest=command.revision.digest,
    )


@profile_api.post("/owner/publication/withdraw")
def withdraw_publication():
    try:
        body = _json_object()
        command = _service().withdraw_publication(
            _owner_context(),
            expected_public_revision=body.get("expected_public_revision"),
            idempotency_key=request.headers.get("Idempotency-Key") or "",
            confirmed=body.get("confirmed") is True,
        )
    except ProfileValidationError as error:
        return _error("invalid_request", 400, str(error))
    except ProfileConflictError as error:
        return _error("conflict", 409, str(error))
    except (ProfileNotFound, ProfileAuthorizationError):
        return _error("not_found", 404)
    except ProfileUnavailableError:
        return _error("unavailable", 503)
    return jsonify(
        success=True,
        command_key=command.command_key,
        public_revision=command.revision.revision_key,
    )


def _draft_summary(draft):
    return {
        "draft_key": draft.draft_key,
        "profile_slug": draft.slug,
        "version": draft.version,
    }


def _error(code: str, status: int, detail: str | None = None):
    payload = {"success": False, "code": code}
    if detail and status in {400, 409}:
        payload["message"] = detail
    return jsonify(payload), status


@profile_api.after_request
def profile_api_headers(response: Response) -> Response:
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response
