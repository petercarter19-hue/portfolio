"""Private Resume editor and draft API for MVP1 increment B.

REGISTERED, AND OFF.
``app.py`` registers this blueprint unconditionally. The gate is
``PEERSLATE_RESUME_EDITOR_ENABLED``, read with ``is True``. Off means a
neutral 404. Schema is not applied by this package; command execution uses
the injected in-memory/test repository or fail-closed SQL.

Identity is server-derived. Client owner ids, table names, and permission
bypass flags are ignored or refused. Responses are private, no-store.
Review and preview do not publish. ``/app`` stays the neutral member
ingress; this page is a protected deep link, not a fifth launchpad tile.
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
from services.resume_draft_service import (
    ResumeDraftConflictError,
    ResumeDraftNotFoundError,
    ResumeDraftService,
    ResumeDraftUnavailableError,
    ResumeDraftValidationError,
    resume_draft_service,
)


resume_draft = Blueprint("resume_draft", __name__)

PLANNED_RATE_LIMITS = MappingProxyType(
    {
        "resume_draft.get_resume_editor_page": "60 per minute",
        "resume_draft.get_resume_draft_workspace": "60 per minute",
        "resume_draft.commit_resume_draft_command": "30 per hour",
        "resume_draft.review_resume_draft": "30 per hour",
    }
)


def _enabled() -> bool:
    return current_app.config.get("PEERSLATE_RESUME_EDITOR_ENABLED", False) is True


def _service() -> ResumeDraftService:
    return current_app.config.get("RESUME_DRAFT_SERVICE") or resume_draft_service


def _wants_json() -> bool:
    return request.path.startswith("/api/")


@resume_draft.before_request
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


@resume_draft.after_request
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
            if key not in {"owner_user_key", "user_key", "owner_profile_id"}
        }
    return payload


def _unavailable_payload(error, *, default_message):
    payload = {"success": False, "code": "unavailable", "message": default_message}
    if getattr(error, "proposed", None) is not None:
        payload["proposed_values"] = error.proposed
        payload["input_preserved"] = True
    return payload


def _validation_payload(error):
    payload = {"success": False, "code": getattr(error, "code", "invalid"), "message": str(error)}
    for field in ("missing_required_fields", "actual_count", "limit"):
        if hasattr(error, field):
            payload[field] = getattr(error, field)
    return payload


@resume_draft.get("/app/resume")
def get_resume_editor_page():
    try:
        identity = get_current_identity()
    except AuthenticationRequired:
        return redirect(url_for("auth.sign_in", return_to="/app/resume"))
    except DatabaseServiceError:
        current_app.logger.error("Resume editor identity lookup failed.")
        abort(503)
    return render_template(
        "resume_editor.html",
        page_title="Resume editor",
        member=identity,
        workspace_url="/api/resume-drafts/me",
        commands_url="/api/resume-drafts/me/commands",
        review_url="/api/resume-drafts/me/review",
    )


@resume_draft.get("/api/resume-drafts/me")
def get_resume_draft_workspace():
    identity = _identity_or_not_found()
    if identity is None:
        return jsonify({"success": False, "message": "Not found."}), 404
    try:
        result = _service().get_workspace(identity.user_key)
    except ResumeDraftUnavailableError as error:
        return jsonify(
            _unavailable_payload(error, default_message="Resume drafts are unavailable.")
        ), 503
    return jsonify({"success": True, **result})


@resume_draft.post("/api/resume-drafts/me/commands")
def commit_resume_draft_command():
    identity = _identity_or_not_found()
    if identity is None:
        return jsonify({"success": False, "message": "Not found."}), 404
    try:
        result = _service().commit(identity.user_key, _json_body())
    except ResumeDraftValidationError as error:
        return jsonify(_validation_payload(error)), 400
    except ResumeDraftNotFoundError:
        return jsonify({"success": False, "code": "not_found", "message": "Not found."}), 404
    except ResumeDraftConflictError as error:
        return jsonify(
            {
                "success": False,
                "code": error.error_code,
                "error_code": error.error_code,
                "conflicts": error.conflicts,
                "proposed_values": error.proposed,
                "input_preserved": error.proposed is not None,
                "message": str(error),
            }
        ), 409
    except ResumeDraftUnavailableError as error:
        return jsonify(
            _unavailable_payload(error, default_message="Resume drafts are unavailable.")
        ), 503
    return jsonify({"success": True, **result})


@resume_draft.post("/api/resume-drafts/me/review")
def review_resume_draft():
    identity = _identity_or_not_found()
    if identity is None:
        return jsonify({"success": False, "message": "Not found."}), 404
    payload = _json_body()
    if not isinstance(payload, dict):
        payload = {}
    payload = {**payload, "type": "review_candidate"}
    if "request_id" not in payload:
        return jsonify({"success": False, "code": "invalid", "message": "Invalid request id."}), 400
    try:
        result = _service().commit(identity.user_key, payload)
    except ResumeDraftValidationError as error:
        return jsonify(_validation_payload(error)), 400
    except ResumeDraftConflictError as error:
        return jsonify(
            {
                "success": False,
                "code": error.error_code,
                "conflicts": error.conflicts,
                "message": str(error),
            }
        ), 409
    except ResumeDraftUnavailableError as error:
        return jsonify(
            _unavailable_payload(error, default_message="Resume drafts are unavailable.")
        ), 503
    result["publishes"] = False
    return jsonify({"success": True, **result})
