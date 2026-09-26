"""Owner Resume publication review/publish API and private preview.

REGISTERED, AND OFF unless PEERSLATE_RESUME_PUBLICATION_ENABLED is True.
Identity is server-derived. Review does not publish. Guest reads live on
public routes and never use this private blueprint.
"""

from __future__ import annotations

from types import MappingProxyType

from flask import (
    Blueprint,
    abort,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)

from identity import AuthenticationRequired, get_current_identity
from services.database_service import DatabaseServiceError
from services.resume_publication_contracts import ReadState
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
