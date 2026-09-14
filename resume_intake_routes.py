"""Private composer intake API for MVP1 increment C.

REGISTERED, AND OFF. ``app.py`` registers this blueprint unconditionally and
the gate is ``PEERSLATE_RESUME_INTAKE_ENABLED`` read with ``is True``; off is a
neutral 404 before any identity or storage work.

Two independent gates keep it fail-closed:

* the feature flag above, and
* ``PEERSLATE_RESUME_INTAKE_FIXTURE_POLICY_ENABLED`` -- because Resume
  onboarding's file/voice limits and retention are not selected, the composer
  refuses to run on the labelled synthetic fixture policy unless that second
  flag is explicitly on. Turning the feature flag on does not silently select
  onboarding policy.

Identity is server-derived. Client owner ids, table names and permission
bypass fields are refused. Responses are private, no-store.
"""

from __future__ import annotations

import json
from types import MappingProxyType

from flask import Blueprint, abort, current_app, jsonify, request

from identity import AuthenticationRequired, get_current_identity
from services.resume_guide_service import (
    GuideConflictError,
    GuideUnavailableError,
    GuideValidationError,
    ResumeGuideService,
)
from services.resume_intake_service import (
    ResumeIntakeConflictError,
    ResumeIntakeNotFoundError,
    ResumeIntakePolicyError,
    ResumeIntakeService,
    ResumeIntakeUnavailableError,
    ResumeIntakeValidationError,
    register_manual_edit_observer,
    resume_intake_service,
)


resume_intake = Blueprint("resume_intake", __name__)

# A committed manual editor save/discard fences that record's pending intake
# proposals. Registration is additive and inert until the composer is in use.
register_manual_edit_observer()

PLANNED_RATE_LIMITS = MappingProxyType(
    {
        "resume_intake.get_intake_workspace": "60 per minute",
        "resume_intake.get_guide_state": "60 per minute",
        "resume_intake.post_submission": "30 per hour",
        "resume_intake.post_recording": "20 per hour",
        "resume_intake.post_proposal_decision": "60 per hour",
        "resume_intake.post_source_purge": "30 per hour",
        "resume_intake.get_draft": "60 per minute",
        "resume_intake.put_draft": "60 per hour",
        "resume_intake.delete_draft": "60 per hour",
        "resume_intake.post_guide_status": "60 per hour",
    }
)


def _enabled() -> bool:
    return current_app.config.get("PEERSLATE_RESUME_INTAKE_ENABLED", False) is True


def _fixture_policy_enabled() -> bool:
    return (
        current_app.config.get("PEERSLATE_RESUME_INTAKE_FIXTURE_POLICY_ENABLED", False)
        is True
    )


def _service() -> ResumeIntakeService:
    return current_app.config.get("RESUME_INTAKE_SERVICE") or resume_intake_service


def _guide_service() -> ResumeGuideService:
    injected = current_app.config.get("RESUME_GUIDE_SERVICE")
    if injected is not None:
        return injected
    return ResumeGuideService(repository=_service().repository)


@resume_intake.before_request
def gate_and_protect_writes():
    if request.path.startswith("/api/"):
        if not _enabled():
            return jsonify({"success": False, "message": "Not found."}), 404
    elif not _enabled():
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


@resume_intake.after_request
def private_no_store(response):
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


def _identity_or_not_found():
    try:
        return get_current_identity()
    except AuthenticationRequired:
        return None


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


def _multipart_request():
    raw = request.form.get("request")
    if not raw:
        raise ResumeIntakeValidationError("Invalid request.")
    try:
        payload = json.loads(raw)
    except ValueError as error:
        raise ResumeIntakeValidationError("Invalid request.") from error
    if not isinstance(payload, dict):
        raise ResumeIntakeValidationError("Invalid request.")
    return payload


def _submitted_files():
    files = {}
    for field_name, storage in request.files.items():
        if field_name.startswith("file:"):
            files[field_name.split(":", 1)[1]] = storage
    return files


def _unavailable(error, default_message):
    payload = {"success": False, "code": "unavailable", "message": default_message}
    if getattr(error, "proposed", None) is not None:
        payload["proposed_values"] = error.proposed
        payload["input_preserved"] = True
    return payload


def _policy_response(error):
    return jsonify({
        "success": False,
        "code": "policy_not_selected",
        "message": str(error) or "Resume onboarding policy is not selected yet.",
        "policy_selected": False,
    }), 503


@resume_intake.get("/api/resume-intake/me")
def get_intake_workspace():
    identity = _identity_or_not_found()
    if identity is None:
        return jsonify({"success": False, "message": "Not found."}), 404
    try:
        result = _service().get_workspace(identity.user_key)
    except ResumeIntakeUnavailableError as error:
        return jsonify(_unavailable(error, "The composer is unavailable.")), 503
    result["fixture_policy_enabled"] = _fixture_policy_enabled()
    return jsonify({"success": True, **result})


@resume_intake.post("/api/resume-intake/me/submissions")
def post_submission():
    identity = _identity_or_not_found()
    if identity is None:
        return jsonify({"success": False, "message": "Not found."}), 404
    try:
        payload = _multipart_request()
        result = _service().submit(
            identity.user_key,
            payload,
            files=_submitted_files(),
            allow_fixture_policy=_fixture_policy_enabled(),
        )
    except ResumeIntakeValidationError as error:
        return jsonify({"success": False, "code": "invalid", "message": str(error)}), 400
    except ResumeIntakePolicyError as error:
        return _policy_response(error)
    except ResumeIntakeNotFoundError:
        return jsonify({"success": False, "code": "not_found", "message": "Not found."}), 404
    except ResumeIntakeConflictError as error:
        return jsonify({
            "success": False,
            "code": error.error_code,
            "error_code": error.error_code,
            "conflicts": error.conflicts,
            "proposed_values": error.proposed,
            "input_preserved": error.proposed is not None,
            "message": str(error),
        }), 409
    except ResumeIntakeUnavailableError as error:
        return jsonify(_unavailable(error, "The composer is unavailable.")), 503
    return jsonify(result)


@resume_intake.post("/api/resume-intake/me/recordings")
def post_recording():
    identity = _identity_or_not_found()
    if identity is None:
        return jsonify({"success": False, "message": "Not found."}), 404
    upload = request.files.get("recording")
    if upload is None:
        return jsonify({
            "success": False, "code": "invalid",
            "message": "Record something before transcribing.",
        }), 400
    try:
        payload = _multipart_request()
        result = _service().transcribe_recording(
            identity.user_key,
            upload,
            payload,
            allow_fixture_policy=_fixture_policy_enabled(),
        )
    except ResumeIntakeValidationError as error:
        return jsonify({"success": False, "code": "invalid", "message": str(error)}), 400
    except ResumeIntakePolicyError as error:
        return _policy_response(error)
    except ResumeIntakeConflictError as error:
        return jsonify({
            "success": False, "code": error.error_code, "message": str(error),
        }), 409
    except ResumeIntakeUnavailableError as error:
        return jsonify(_unavailable(error, "Transcription is unavailable.")), 503
    return jsonify(result)


@resume_intake.post("/api/resume-intake/me/proposals/decision")
def post_proposal_decision():
    identity = _identity_or_not_found()
    if identity is None:
        return jsonify({"success": False, "message": "Not found."}), 404
    try:
        result = _service().decide(
            identity.user_key,
            _json_body(),
            allow_fixture_policy=_fixture_policy_enabled(),
        )
    except ResumeIntakeValidationError as error:
        return jsonify({"success": False, "code": "invalid", "message": str(error)}), 400
    except ResumeIntakePolicyError as error:
        return _policy_response(error)
    except ResumeIntakeNotFoundError:
        return jsonify({"success": False, "code": "not_found", "message": "Not found."}), 404
    except ResumeIntakeConflictError as error:
        return jsonify({
            "success": False,
            "code": error.error_code,
            "error_code": error.error_code,
            "conflicts": error.conflicts,
            "proposed_values": error.proposed,
            "input_preserved": error.proposed is not None,
            "message": str(error),
        }), 409
    except ResumeIntakeUnavailableError as error:
        return jsonify(_unavailable(error, "The composer is unavailable.")), 503
    return jsonify(result)


@resume_intake.post("/api/resume-intake/me/sources/purge")
def post_source_purge():
    identity = _identity_or_not_found()
    if identity is None:
        return jsonify({"success": False, "message": "Not found."}), 404
    try:
        result = _service().purge_source(identity.user_key, _json_body())
    except ResumeIntakeValidationError as error:
        return jsonify({"success": False, "code": "invalid", "message": str(error)}), 400
    except ResumeIntakeNotFoundError:
        return jsonify({"success": False, "code": "not_found", "message": "Not found."}), 404
    except ResumeIntakeConflictError as error:
        return jsonify({
            "success": False, "code": error.error_code, "message": str(error),
        }), 409
    except ResumeIntakeUnavailableError as error:
        return jsonify(_unavailable(error, "The composer is unavailable.")), 503
    return jsonify(result)


@resume_intake.get("/api/resume-intake/me/draft")
def get_draft():
    identity = _identity_or_not_found()
    if identity is None:
        return jsonify({"success": False, "message": "Not found."}), 404
    try:
        result = _service().get_draft(identity.user_key)
    except ResumeIntakeUnavailableError as error:
        return jsonify({
            "success": False, "code": "unavailable", "message": str(error),
        }), 503
    return jsonify({"success": True, **result})


@resume_intake.put("/api/resume-intake/me/draft")
def put_draft():
    identity = _identity_or_not_found()
    if identity is None:
        return jsonify({"success": False, "message": "Not found."}), 404
    try:
        result = _service().save_draft(
            identity.user_key,
            _json_body(),
            allow_fixture_policy=_fixture_policy_enabled(),
        )
    except ResumeIntakeValidationError as error:
        return jsonify({"success": False, "code": "invalid", "message": str(error)}), 400
    except ResumeIntakePolicyError as error:
        return _policy_response(error)
    except ResumeIntakeConflictError as error:
        return jsonify({
            "success": False,
            "code": error.error_code,
            "error_code": error.error_code,
            "conflicts": error.conflicts,
            "proposed_values": error.proposed,
            "input_preserved": error.proposed is not None,
            "message": str(error),
        }), 409
    except ResumeIntakeUnavailableError as error:
        return jsonify({
            "success": False, "code": "unavailable", "message": str(error),
        }), 503
    return jsonify(result)


@resume_intake.delete("/api/resume-intake/me/draft")
def delete_draft():
    identity = _identity_or_not_found()
    if identity is None:
        return jsonify({"success": False, "message": "Not found."}), 404
    try:
        result = _service().discard_draft(
            identity.user_key,
            _json_body(),
            allow_fixture_policy=_fixture_policy_enabled(),
        )
    except ResumeIntakeValidationError as error:
        return jsonify({"success": False, "code": "invalid", "message": str(error)}), 400
    except ResumeIntakePolicyError as error:
        return _policy_response(error)
    except ResumeIntakeUnavailableError as error:
        return jsonify({
            "success": False, "code": "unavailable", "message": str(error),
        }), 503
    return jsonify(result)


@resume_intake.get("/api/resume-intake/me/guide")
def get_guide_state():
    identity = _identity_or_not_found()
    if identity is None:
        return jsonify({"success": False, "message": "Not found."}), 404
    try:
        result = _guide_service().get_state(identity.user_key)
    except GuideUnavailableError as error:
        # A read failure is not a new member and not "nothing saved".
        state = _guide_service().unavailable_state()
        return jsonify({"success": False, "code": "unavailable", **state}), 503
    return jsonify({"success": True, **result})


@resume_intake.post("/api/resume-intake/me/guide/status")
def post_guide_status():
    identity = _identity_or_not_found()
    if identity is None:
        return jsonify({"success": False, "message": "Not found."}), 404
    try:
        result = _guide_service().set_status(identity.user_key, _json_body())
    except GuideConflictError as error:
        return jsonify({
            "success": False, "code": error.code, "message": str(error),
        }), 409
    except GuideValidationError as error:
        return jsonify({"success": False, "code": "invalid", "message": str(error)}), 400
    except GuideUnavailableError:
        return jsonify({
            "success": False, "code": "unavailable",
            "message": "The guide is unavailable right now.",
        }), 503
    return jsonify({"success": True, **result})
