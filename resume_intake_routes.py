"""Private composer intake API for MVP1 increment C.

REGISTERED, AND OFF. ``app.py`` registers this blueprint unconditionally and
the gate is ``PEERSLATE_RESUME_INTAKE_ENABLED`` read with ``is True``; off is a
neutral 404 before any identity or storage work.

The owner-selected policy is independent of feature enablement. Explicit
synthetic fixture policies still require the separate fixture flag and never
qualify durable production storage. The hosted factory requires applied SQL
and fails closed when storage or processing capabilities are unavailable.

Identity is server-derived. Client owner ids, table names and permission
bypass fields are refused. Responses are private, no-store.
"""

from __future__ import annotations

import json
from io import BytesIO
from types import MappingProxyType

from flask import Blueprint, abort, current_app, jsonify, request, send_file

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
        "resume_intake.post_private_synthesis": "10 per hour",
        "resume_intake.post_private_synthesis_confirmation": "30 per hour",
        "resume_intake.post_private_interview": "20 per hour",
        "resume_intake.get_original_files": "60 per minute",
        "resume_intake.get_original_file": "30 per hour",
        "resume_intake.delete_original_file": "30 per hour",
        "resume_intake.get_intake_workspace": "60 per minute",
        "resume_intake.get_guide_state": "60 per minute",
        "resume_intake.get_guide_working_set": "60 per minute",
        "resume_intake.post_submission": "30 per hour",
        "resume_intake.post_recording": "20 per hour",
        "resume_intake.post_proposal_decision": "60 per hour",
        "resume_intake.post_saved_choice_review": "30 per hour",
        "resume_intake.post_excluded_detail_review": "30 per hour",
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


def _first_arrival(owner):
    return _guide_service().get_first_arrival(owner, read_content=_service().has_private_resume_content)


@resume_intake.before_request
def gate_and_protect_writes():
    if request.path.startswith("/api/"):
        if not _enabled():
            return jsonify({"success": False, "message": "Not found."}), 404
    elif not _enabled():
        abort(404)
    private_kind = {
        "resume_intake.post_private_synthesis": "SYNTHESIS",
        "resume_intake.post_private_synthesis_confirmation": "SYNTHESIS",
        "resume_intake.post_private_interview": "INTERVIEW",
    }.get(request.endpoint)
    if private_kind and (current_app.config.get("PEERSLATE_RESUME_EDITOR_ENABLED") is not True
            or current_app.config.get("PEERSLATE_RESUME_" + private_kind + "_ENABLED") is not True):
        return jsonify({"success": False, "message": "Not found."}), 404
    # Override the application two-MB ceiling only for these bounded private
    # multipart endpoints. File bytes, parser text and audio remain separate.
    if request.endpoint == "resume_intake.post_submission":
        policy = _service().policy()
        request.max_content_length = policy.max_documents_per_submission * policy.max_document_bytes + 256_000
    elif request.endpoint == "resume_intake.post_recording":
        request.max_content_length = _service().policy().max_recording_bytes + 256_000
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


def _guide_validation_payload(error):
    payload = {"success": False, "code": getattr(error, "code", "invalid"), "message": str(error)}
    for name in ("missing_required_fields", "actual_count", "limit"):
        if hasattr(error, name):
            payload[name] = getattr(error, name)
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


@resume_intake.post('/api/resume-intake/me/saved-choices/review')
def post_saved_choice_review():
    identity = _identity_or_not_found()
    if identity is None:
        return jsonify({'success': False, 'message': 'Not found.'}), 404
    try:
        result = _service().review_resume_history(identity.user_key, _json_body(),
            allow_fixture_policy=_fixture_policy_enabled())
    except ResumeIntakeValidationError as error:
        return jsonify({'success': False, 'code': 'invalid', 'message': str(error)}), 400
    except ResumeIntakePolicyError as error:
        return _policy_response(error)
    except ResumeIntakeNotFoundError:
        return jsonify({'success': False, 'message': 'Not found.'}), 404
    except ResumeIntakeConflictError as error:
        return jsonify({'success': False, 'code': error.error_code, 'message': str(error)}), 409
    except ResumeIntakeUnavailableError:
        return jsonify({'success': False, 'code': 'unavailable',
            'message': 'Saved-choice review is unavailable. Your approved information is kept.'}), 503
    return jsonify({'success': True, **result})


@resume_intake.post('/api/resume-intake/me/excluded-details/review')
def post_excluded_detail_review():
    identity = _identity_or_not_found()
    if identity is None:
        return jsonify({'success': False, 'message': 'Not found.'}), 404
    try:
        result = _service().review_excluded_details(identity.user_key, _json_body(),
            allow_fixture_policy=_fixture_policy_enabled())
    except ResumeIntakeValidationError as error:
        return jsonify({'success': False, 'code': 'invalid', 'message': str(error)}), 400
    except ResumeIntakePolicyError as error:
        return _policy_response(error)
    except ResumeIntakeNotFoundError:
        return jsonify({'success': False, 'message': 'Not found.'}), 404
    except ResumeIntakeConflictError as error:
        return jsonify({'success': False, 'code': error.error_code, 'message': str(error)}), 409
    except ResumeIntakeUnavailableError:
        return jsonify({'success': False, 'code': 'unavailable',
            'message': 'Excluded-detail review is unavailable. Your current information is kept.'}), 503
    return jsonify({'success': True, **result})


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
        return jsonify(_guide_validation_payload(error)), 400
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


@resume_intake.post("/api/resume-intake/me/sources/organize")
def post_source_organize():
    identity = _identity_or_not_found()
    if identity is None:
        return jsonify({"success": False, "message": "Not found."}), 404
    try:
        result = _service().organize_source(
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
    if request.args:
        return jsonify({"success": False, "code": "invalid", "message": "Invalid request."}), 400
    try:
        result = _guide_service().get_state(identity.user_key)
    except GuideUnavailableError as error:
        # A read failure is not a new member and not "nothing saved".
        state = _guide_service().unavailable_state()
        return jsonify({"success": False, "code": "unavailable", **state}), 503
    return jsonify({"success": True, **result, "first_arrival": _first_arrival(identity.user_key)})


@resume_intake.get("/api/resume-intake/me/guide/working-set")
def get_guide_working_set():
    identity = _identity_or_not_found()
    if identity is None:
        return jsonify({"success":False,"message":"Not found."}),404
    if request.args:
        return jsonify({"success":False,"code":"invalid","message":"Invalid request."}),400
    try:
        result = _service().working_set(identity.user_key)
    except ResumeIntakeUnavailableError as error:
        return jsonify({**_unavailable(error,"The Guide is unavailable right now."),"load_state":"unavailable"}),503
    return jsonify({"success":True,**_complete_guide_working_set(identity.user_key, result)})


def _complete_guide_working_set(owner, result):
    from services.resume_publication_service import ResumePublicationService
    basis = ResumePublicationService._unavailable_basis()
    publication = current_app.config.get("RESUME_PUBLICATION_SERVICE")
    if publication is not None:
        try:
            basis = _service().guide_publication_basis(owner,result,publication)
        except Exception:
            basis = ResumePublicationService._unavailable_basis()
    try:
        references = _service().guide_reference_view(owner,result)
    except Exception:
        references = {"read_state":"unavailable","skill_evidence":None,"highlight_tiles":None,"needs_recheck":None}
    result["references"] = references
    result["publication"] = basis
    result["publication_state"] = basis["publication_state"]
    per_item = {item["item_ref"]: item for item in basis.get("items") or []}
    def annotate(items):
        for item in items:
            detail = per_item.get(item["item_ref"])
            for key in ("published_display","published_visitor_ai","proposed_display","proposed_visitor_ai"):
                item[key] = detail.get(key) if detail is not None else (False if basis["read_state"] == "current" else None)
            annotate(item["children"])
    annotate([*(row for section in result["sections"] for row in section["items"]),
        *result["unplaced"],*result["non_tab_items"]])
    from services.resume_guide_contract import refresh_working_set_token
    result["first_arrival"] = _first_arrival(owner)
    refresh_working_set_token(owner,result)
    return result


@resume_intake.post("/api/resume-intake/me/guide/visibility")
def post_guide_visibility():
    identity = _identity_or_not_found()
    if identity is None:
        return jsonify({"success":False,"message":"Not found."}),404
    try:
        result = _service().set_guide_visibility(identity.user_key, request.get_json(silent=True),
            read_working_set=lambda owner: _complete_guide_working_set(owner, _service().working_set(owner)))
    except ResumeIntakeValidationError as error:
        return jsonify({"success":False,"code":"invalid","message":str(error)}),400
    except ResumeIntakeNotFoundError:
        return jsonify({"success":False,"message":"Not found."}),404
    except ResumeIntakeConflictError as error:
        return jsonify({"success":False,"code":error.error_code,"message":str(error)}),409
    except ResumeIntakeUnavailableError as error:
        return jsonify(_unavailable(error,"The Guide is unavailable right now.")),503
    return jsonify(result)


@resume_intake.post("/api/resume-intake/me/guide/references")
def post_guide_references():
    identity = _identity_or_not_found()
    if identity is None:
        return jsonify({"success":False,"message":"Not found."}),404
    try:
        result = _service().set_guide_references(identity.user_key,request.get_json(silent=True),
            read_working_set=lambda owner: _complete_guide_working_set(owner,_service().working_set(owner)))
    except ResumeIntakeValidationError as error:
        return jsonify({"success":False,"code":"invalid","message":str(error)}),400
    except ResumeIntakeNotFoundError:
        return jsonify({"success":False,"message":"Not found."}),404
    except ResumeIntakeConflictError as error:
        return jsonify({"success":False,"code":error.error_code,"message":str(error)}),409
    except ResumeIntakeUnavailableError as error:
        return jsonify(_unavailable(error,"The Guide is unavailable right now.")),503
    return jsonify(result)


@resume_intake.post("/api/resume-intake/me/guide/status")
def post_guide_status():
    identity = _identity_or_not_found()
    if identity is None:
        return jsonify({"success": False, "message": "Not found."}), 404
    try:
        payload = request.get_json(silent=True)
        if isinstance(payload, dict) and "first_arrival_action" in payload:
            result = _guide_service().acknowledge_first_arrival(identity.user_key, payload,
                read_content=_service().has_private_resume_content)
        else:
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


def _original_files_service():
    service = _service()
    files = getattr(service, "original_files", None)
    if files is None:
        raise ResumeIntakeUnavailableError()
    if hasattr(service, "_require_schema"):
        service._require_schema()
    return files


def _original_error(error):
    from services.resume_original_file_repository import OriginalFileConflict, OriginalFileNotFound
    if isinstance(error, OriginalFileNotFound):
        return jsonify({"success": False, "code": "not_found", "message": "Not found."}), 404
    if isinstance(error, OriginalFileConflict):
        return jsonify({"success": False, "code": "changed", "message": "That original changed. Refresh and try again."}), 409
    return jsonify({"success": False, "code": "unavailable", "message": "Original files are unavailable right now."}), 503


@resume_intake.get("/api/resume-intake/me/originals")
def get_original_files():
    identity = _identity_or_not_found()
    if identity is None:
        return jsonify({"success": False, "message": "Not found."}), 404
    from services.resume_original_file_repository import OriginalFileUnavailable
    try:
        files = _original_files_service().list(identity.user_key)
    except (OriginalFileUnavailable, ResumeIntakeUnavailableError) as error:
        return _original_error(error)
    return jsonify({"success": True, "originals": files})


@resume_intake.get("/api/resume-intake/me/originals/<uuid:original_key>")
def get_original_file(original_key):
    identity = _identity_or_not_found()
    if identity is None:
        return jsonify({"success": False, "message": "Not found."}), 404
    from services.resume_original_file_repository import OriginalFileNotFound, OriginalFileUnavailable
    try:
        data, content_type = _original_files_service().download(identity.user_key, str(original_key))
    except (OriginalFileNotFound, OriginalFileUnavailable, ResumeIntakeUnavailableError) as error:
        return _original_error(error)
    extension = {"application/pdf": "pdf", "text/plain": "txt",
                 "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx"}[content_type]
    return send_file(BytesIO(data), mimetype=content_type, as_attachment=True,
                     download_name="resume-original." + extension, max_age=0)


@resume_intake.delete("/api/resume-intake/me/originals/<uuid:original_key>")
def delete_original_file(original_key):
    identity = _identity_or_not_found()
    if identity is None:
        return jsonify({"success": False, "message": "Not found."}), 404
    from services.resume_original_file_repository import OriginalFileConflict, OriginalFileNotFound, OriginalFileUnavailable
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or set(payload) != {"expected_version", "request_id"}:
        return jsonify({"success": False, "code": "invalid", "message": "Invalid original file request."}), 400
    try:
        result = _original_files_service().delete(identity.user_key, str(original_key),
            expected_version=payload["expected_version"], request_id=payload["request_id"])
    except ValueError:
        return jsonify({"success": False, "code": "invalid", "message": "Invalid original file request."}), 400
    except (OriginalFileConflict, OriginalFileNotFound, OriginalFileUnavailable, ResumeIntakeUnavailableError) as error:
        return _original_error(error)
    return jsonify(result), 202 if result["outcome"] == "delete_pending" else 200


# What a member is told when private assistance refuses before or after the model: the reason and what to do.
_ASSISTANCE_MESSAGES = {
    'input_too_large': 'There is too much to read at once, so I did not send this. Nothing was changed and nothing was spent. '
                       'Finish or set aside some earlier items, or use the manual editor. Your words are kept.',
    'changed': 'Your résumé changed while I was working, so I stopped. Nothing was saved. Try again. Your words are kept.',
    'no_eligible_sources': 'There is nothing saved yet for me to work from. Add a detail first, or use the manual editor.',
    'target_locked': 'That part cannot be changed here right now. Use the manual editor. Your words are kept.',
    'not_found': 'That item is no longer there. Reload the page to see what is current. Your words are kept.',
    'unavailable': 'Private assistance is unavailable right now. Nothing was changed. Try again shortly, or use the manual editor.',
}


# When the model's answer is refused by the server's own checks, say what that means and what to do next.
_REJECTION_MESSAGES = {
    None: 'I could not turn that message into résumé details this time. Nothing was changed and your words are kept. '
          'Try again, say it a little differently, or use the manual editor.',
    'literal_size': 'That message is too long for me to organize in one piece. Send it in smaller parts, for example one job '
                    'at a time. Nothing was changed and your words are kept.',
    'command_as_new_content': 'That read like an instruction rather than new résumé content, so I did not add it. Say what you '
                              'would like added or changed. Nothing was changed.',
    'control_as_new_content': 'That read like an instruction rather than new résumé content, so I did not add it. Say what you '
                              'would like added or changed. Nothing was changed.',
}


def _private_assistance(kind, method):
    # Flag off is neutral before identity, parsing, signing, SQL or provider I/O.
    if (current_app.config.get('PEERSLATE_RESUME_EDITOR_ENABLED') is not True
            or current_app.config.get('PEERSLATE_RESUME_' + kind.upper() + '_ENABLED') is not True):
        return jsonify({'success': False, 'message': 'Not found.'}), 404
    identity = _identity_or_not_found()
    if identity is None:
        return jsonify({'success': False, 'message': 'Not found.'}), 404
    service = current_app.config.get('RESUME_PRIVATE_ASSISTANCE_SERVICE')
    if service is None:
        return jsonify({'success': False, 'code': 'unavailable',
            'message': 'Private assistance is unavailable. Your manual editor remains available.'}), 503
    # Private owner/body limits are independent of provider complete-wire limits.
    if request.content_length is not None and request.content_length > 100000:
        return jsonify({'success': False, 'code': 'invalid', 'message': 'Request too large.'}), 413
    raw = request.stream.read(100001)
    if len(raw) > 100000:
        return jsonify({'success': False, 'code': 'invalid', 'message': 'Request too large.'}), 413
    from services.resume_intake_runtime import SynthesisError, conversation_failure_diagnostic
    from services.ai_foundation.errors import ProviderUnavailableError, ExecutionLimitError
    from services.resume_draft_service import (
        ResumeDraftConflictError, ResumeDraftValidationError, ResumeDraftUnavailableError,
    )
    from services.my_data_extraction_adapter import ExtractionError
    try:
        def closed_pairs(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError('duplicate field')
                result[key] = value
            return result
        payload = json.loads(raw, object_pairs_hook=closed_pairs)
        if method == 'interview' and callable(getattr(type(service), 'conversation', None)):
            result = _service().converse(identity.user_key, payload, assistance=service,
                allow_fixture_policy=_fixture_policy_enabled())
        elif method == 'interview' and isinstance(payload, dict) and 'proposal_key' in payload:
            proposal_key = payload.pop('proposal_key')
            workspace = _service().get_workspace(identity.user_key)
            proposal = next((row for row in workspace.get('pending_proposals', [])
                             if row.get('proposal_key') == proposal_key and row.get('state') == 'pending'), None)
            if proposal is None:
                raise SynthesisError('not_found')
            result = service.interview(identity.user_key, payload, review_proposal=proposal)
            fresh = _service().get_workspace(identity.user_key)
            current = next((row for row in fresh.get('pending_proposals', [])
                            if row.get('proposal_key') == proposal_key), None)
            if current != proposal:
                raise SynthesisError('changed')
        else:
            result = getattr(service, method)(identity.user_key, payload)
    except ResumeDraftConflictError as error:
        return jsonify({'success': False, 'code': 'changed', 'message': str(error),
                        'proposed_values': error.proposed}), 409
    except ResumeIntakeConflictError as error:
        return jsonify({'success': False, 'code': 'changed', 'message': str(error)}), 409
    except ResumeIntakeNotFoundError:
        return jsonify({'success': False, 'code': 'not_found', 'message': 'Not found.'}), 404
    except ResumeIntakePolicyError as error:
        return _policy_response(error)
    except SynthesisError as error:
        code = error.code
        status = 404 if code == 'not_found' else 409 if code == 'changed' else 503 if code == 'unavailable' else 400
        diagnostic = conversation_failure_diagnostic(error)
        message = _ASSISTANCE_MESSAGES.get(code)
        if code == 'invalid_output':
            message = _REJECTION_MESSAGES.get((diagnostic or {}).get('reason')) or _REJECTION_MESSAGES[None]
        body = {'success': False, 'code': code,
            'message': message or 'Private assistance could not complete. Your words and manual editor remain available.'}
        if diagnostic is not None:
            body['diagnostic'] = diagnostic
        return jsonify(body), status
    except (ProviderUnavailableError, ExecutionLimitError, TimeoutError, ResumeDraftUnavailableError,
            ResumeIntakeUnavailableError):
        return jsonify({'success': False, 'code': 'unavailable',
            'message': 'Private assistance is unavailable. Your manual editor remains available.'}), 503
    except (ValueError, TypeError, KeyError, ResumeDraftValidationError, ResumeIntakeValidationError, ExtractionError):
        return jsonify({'success': False, 'code': 'invalid',
                        'message': 'Review the request and try again. Your words are preserved.'}), 400
    return jsonify({'success': True, **result})


@resume_intake.post('/api/resume-synthesis/me/proposals')
def post_private_synthesis():
    return _private_assistance('synthesis', 'generate')


@resume_intake.post('/api/resume-synthesis/me/confirm')
def post_private_synthesis_confirmation():
    return _private_assistance('synthesis', 'confirm')


@resume_intake.post('/api/resume-interview/me/turn')
def post_private_interview():
    return _private_assistance('interview', 'interview')
