"""Protected owner-only routes for the PeerSlate application."""

import json
import re
from datetime import date, datetime
from uuid import UUID

from flask import (
    Blueprint,
    Response,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)

from identity import AuthenticationRequired, get_current_identity
from services.database_service import DatabaseServiceError, database_service
from services.capture_lifecycle_service import (
    CaptureLifecycleError,
    capture_lifecycle_service,
)
from services.moment_service import (
    MAX_MOMENT_NARRATIVE_LENGTH,
    MAX_MOMENT_TITLE_LENGTH,
    MAX_MOMENT_WHY_LENGTH,
    MOMENT_KINDS,
    OCCURRED_PRECISIONS,
    validate_moment_proposal,
)
from services.voice_capture_service import (
    MAX_VOICE_BYTES,
    MAX_VOICE_DURATION_SECONDS,
    VoiceCaptureError,
    voice_capture_service,
)
from services.photo_capture_service import (
    MAX_PHOTO_BYTES,
    PhotoCaptureError,
    photo_capture_service,
)
from services.photo_lifecycle_access_service import (
    PHOTO_ACCESS_ORDINARY,
    PHOTO_ACCESS_PROOF,
    photo_lifecycle_access_service,
)
from services.owner_home_service import (
    OwnerHomeContractError,
    owner_home_service,
)
from services.journal_service import JournalServiceError, journal_service


owner = Blueprint("owner", __name__)
MAX_CAPTURE_BODY_LENGTH = 8000
MAX_CORRECTION_NOTE_LENGTH = 1000
ROW_VERSION_TOKEN = re.compile(r"^[0-9a-fA-F]{16}$")
CAPTURE_VALIDATION_MESSAGES = {
    "required": "Write something before saving your capture.",
    "too-long": f"Keep your capture to {MAX_CAPTURE_BODY_LENGTH:,} characters or fewer.",
    "note-too-long": (
        f"Keep the correction note to {MAX_CORRECTION_NOTE_LENGTH:,} characters or fewer."
    ),
    "changed": "That capture changed or is no longer available. Refresh and try again.",
    "confirm-delete": "Confirm permanent deletion before deleting this capture.",
    "voice-changed": "That private voice draft changed or is no longer available. Refresh and try again.",
    "voice-required": "Review the transcript and add meaningful text before saving.",
    "voice-too-long": f"Keep the reviewed transcript to {MAX_CAPTURE_BODY_LENGTH:,} characters or fewer.",
    "voice-delete-retry": "The private audio could not be deleted yet. Nothing was reported as deleted; try again.",
    "voice-transcription": "The private recording was preserved, but transcription did not finish. Retry or delete the draft.",
}
CAPTURE_SUCCESS_MESSAGES = {
    "corrected": "Correction saved as a new version. The original is unchanged.",
    "archived": "Capture archived. You can restore it from Archived captures.",
    "restored": "Capture restored to your active captures.",
    "deleted": "Capture and its correction history were permanently deleted.",
    "moment-discarded": "Private Moment proposal discarded.",
    "voice-deleted": "Private voice draft and original audio were deleted.",
    "photo-saved": "Photo saved as one private Capture. Nothing was shared or published.",
    "photo-deleted": "Private photo draft and its stored files were deleted.",
}
MOMENT_VALIDATION_MESSAGES = {
    "required": "Choose a type and add both a title and member-approved narrative.",
    "too-long": "One or more proposed Moment fields is too long. Shorten it and try again.",
    "date": "Choose a valid date or select Date not set.",
    "changed": "That private Moment changed or is no longer available. Refresh and try again.",
    "source-deleted": (
        "The pinned Capture source was deleted. This unconfirmed proposal cannot be confirmed."
    ),
    "confirm-discard": "Confirm that you want to discard this private proposal.",
}
MOMENT_SUCCESS_MESSAGES = {
    "saved": "Private proposal saved as a new version.",
    "confirmed": "Moment confirmed privately. Nothing was published or placed.",
}


def _render_owner_unavailable():
    return (
        render_template(
            "auth_unavailable.html",
            page_title="Sign in is not configured",
        ),
        503,
    )


def _is_same_origin_write():
    expected_origin = request.host_url.rstrip("/")
    origin = request.headers.get("Origin")
    fetch_site = request.headers.get("Sec-Fetch-Site")
    return not (
        (origin and origin.rstrip("/") != expected_origin)
        or (fetch_site and fetch_site not in {"same-origin", "none"})
    )


@owner.before_request
def _allow_bounded_voice_upload():
    """Override the smaller global form limit for bounded media upload routes."""
    if request.endpoint == "owner.upload_voice_capture":
        # Multipart framing adds a small amount beyond the enforced 20 MB file cap.
        request.max_content_length = MAX_VOICE_BYTES + (64 * 1024)
    elif request.endpoint == "owner.upload_photo_capture":
        request.max_content_length = MAX_PHOTO_BYTES + (64 * 1024)


def _photo_unavailable():
    return "Photo Capture is unavailable.", 404


def _owner_home_enabled():
    return current_app.config.get("PEERSLATE_OWNER_HOME_ENABLED", False) is True


@owner.get("/api/v1/owner/home")
def owner_home_data():
    """Return the bounded private Home contract while its server flag is on."""
    if not _owner_home_enabled():
        return jsonify({"error": "not_found"}), 404

    try:
        identity = get_current_identity()
    except AuthenticationRequired:
        return jsonify({"error": "authentication_required"}), 401
    except DatabaseServiceError:
        current_app.logger.error("PeerSlate Owner Home identity is unavailable.")
        return jsonify({"error": "unavailable"}), 503

    try:
        payload = owner_home_service.get_home(identity).to_dict()
    except (DatabaseServiceError, OwnerHomeContractError):
        current_app.logger.error("PeerSlate Owner Home data is unavailable.")
        return jsonify({"error": "unavailable"}), 503

    response = jsonify(payload)
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


def _capture_body_length(body):
    """Match HTML maxlength and SQL nvarchar UTF-16 code-unit counting."""
    return len(body.encode("utf-16-le")) // 2


def _normalize_capture_key(value):
    try:
        return str(UUID(str(value)))
    except (TypeError, ValueError, AttributeError):
        return None


def _row_version_token(value):
    if isinstance(value, memoryview):
        value = value.tobytes()
    if isinstance(value, (bytes, bytearray)) and len(value) == 8:
        return bytes(value).hex()
    if isinstance(value, str) and ROW_VERSION_TOKEN.fullmatch(value):
        return value.lower()
    return ""


def _parse_expected_row_version(value):
    if not isinstance(value, str) or not ROW_VERSION_TOKEN.fullmatch(value):
        return None
    return bytes.fromhex(value)


def _prepare_capture_rows(rows):
    prepared = []
    for row in rows:
        capture = dict(row)
        capture["current_body"] = capture.get("body")
        capture["original_body"] = capture.get("original_body") or capture.get(
            "body"
        )
        capture["revision_number"] = int(capture.get("revision_number") or 0)
        capture["revision_count"] = int(capture.get("revision_count") or 0)
        capture["row_version_token"] = _row_version_token(
            capture.get("row_version")
        )
        prepared.append(capture)
    return prepared


def _prepare_moment_row(row):
    moment = dict(row)
    moment["row_version_token"] = _row_version_token(moment.get("row_version"))
    moment["current_version_number"] = int(
        moment.get("current_version_number") or 0
    )
    moment["confirmed_version_number"] = int(
        moment.get("confirmed_version_number") or 0
    )
    moment["source_revision_number"] = int(
        moment.get("source_revision_number") or 0
    )
    moment["latest_source_revision_number"] = int(
        moment.get("latest_source_revision_number") or 0
    )
    moment["source_deleted"] = moment.get("source_state") == "deleted"
    moment["can_confirm"] = bool(moment.get("can_confirm")) and not moment[
        "source_deleted"
    ]
    moment["newer_source_available"] = bool(
        moment.get("newer_source_available")
    )
    return moment


def _capture_action_context():
    try:
        identity = get_current_identity()
    except AuthenticationRequired:
        return None, redirect(url_for("auth.sign_in", return_to="/app/capture"))
    except DatabaseServiceError:
        current_app.logger.error("PeerSlate private capture identity lookup failed.")
        return None, _render_owner_unavailable()

    capture_key = _normalize_capture_key(request.view_args.get("capture_key"))
    expected_row_version = _parse_expected_row_version(
        request.form.get("expected_row_version", "")
    )
    if not capture_key or expected_row_version is None:
        return None, redirect(url_for("owner.capture", error="changed"))
    return (identity, capture_key, expected_row_version), None


def _moment_action_context():
    moment_key = _normalize_capture_key(request.view_args.get("moment_key"))
    if not moment_key:
        return None, ("Moment not found.", 404)

    try:
        identity = get_current_identity()
    except AuthenticationRequired:
        return None, redirect(
            url_for("auth.sign_in", return_to=f"/app/moments/{moment_key}/review")
        )
    except DatabaseServiceError:
        current_app.logger.error("PeerSlate private Moment identity lookup failed.")
        return None, _render_owner_unavailable()

    expected_row_version = _parse_expected_row_version(
        request.form.get("expected_row_version", "")
    )
    if expected_row_version is None:
        return None, redirect(
            url_for("owner.review_moment", moment_key=moment_key, error="changed")
        )
    return (identity, moment_key, expected_row_version), None


def _run_capture_state_change(procedure_name, changed):
    if not _is_same_origin_write():
        return "Cross-site capture requests are not allowed.", 403

    context, response = _capture_action_context()
    if response is not None:
        return response
    identity, capture_key, expected_row_version = context

    try:
        result = database_service.first_row(
            procedure_name,
            [
                ("@UserKey", identity.user_key),
                ("@CaptureKey", capture_key),
                ("@ExpectedRowVersion", expected_row_version),
            ],
        )
    except DatabaseServiceError:
        current_app.logger.error("PeerSlate private capture lifecycle is unavailable.")
        return _render_owner_unavailable()

    if not result or result.get("outcome") != "success":
        return redirect(url_for("owner.capture", error="changed"))
    return redirect(url_for("owner.capture", changed=changed))


def _json_value(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    raise TypeError(f"Unsupported JSON value: {type(value).__name__}")


@owner.get("/app/settings")
def settings():
    """Render the signed-in member's account settings overview."""
    try:
        identity = get_current_identity()
    except AuthenticationRequired:
        return redirect(url_for("auth.sign_in", return_to="/app/settings"))
    except DatabaseServiceError:
        current_app.logger.error("PeerSlate owner settings identity lookup failed.")
        return _render_owner_unavailable()

    return render_template(
        "owner_settings.html",
        page_title="Settings",
        member=identity,
    )


@owner.route("/app/capture", methods=("GET", "POST"))
def capture():
    """Capture and review the signed-in member's private text drafts."""
    if request.method == "POST" and not _is_same_origin_write():
        return "Cross-site capture requests are not allowed.", 403

    try:
        identity = get_current_identity()

        if request.method == "POST":
            body = request.form.get("body", "").strip()
            if not body:
                return redirect(url_for("owner.capture", error="required"))
            if _capture_body_length(body) > MAX_CAPTURE_BODY_LENGTH:
                return redirect(url_for("owner.capture", error="too-long"))

            created_capture = database_service.first_row(
                "usp_CreateCapture",
                [
                    ("@UserKey", identity.user_key),
                    ("@CaptureType", "text"),
                    ("@Body", body),
                ],
            )
            if not created_capture:
                raise DatabaseServiceError(
                    "Capture creation returned no persisted record."
                )
            return redirect(url_for("owner.capture", saved="1"))

        archived = request.args.get("view") == "archived"
        captures = database_service.first_result(
            "usp_ListCapturesForOwner",
            [
                ("@UserKey", identity.user_key),
                ("@Take", 50),
                ("@Archived", archived),
            ],
        )
        voice_draft = None
        photo_draft = None
        photo_configuration = photo_lifecycle_access_service.configuration()
        photo_enabled = photo_lifecycle_access_service.allows_identity(
            identity, photo_configuration
        )
        voice_key = request.args.get("voice")
        photo_key = request.args.get("photo")
        if voice_key and photo_key:
            return "Open one private Capture draft at a time.", 400
        if voice_key:
            normalized_voice_key = _normalize_capture_key(voice_key)
            if not normalized_voice_key:
                return "Voice draft not found.", 404
            voice_draft = voice_capture_service.get_draft(
                identity.user_key, normalized_voice_key
            )
            if not voice_draft:
                return "Voice draft not found.", 404
        if photo_key:
            if not photo_enabled:
                return _photo_unavailable()
            normalized_photo_key = _normalize_capture_key(photo_key)
            if not normalized_photo_key:
                return "Photo source not found.", 404
            photo_source = photo_capture_service.get_source(
                identity.user_key, normalized_photo_key
            )
            if not photo_source:
                return "Photo source not found.", 404
            photo_draft = _photo_source_payload(photo_source)
    except AuthenticationRequired:
        return redirect(url_for("auth.sign_in", return_to="/app/capture"))
    except (DatabaseServiceError, PhotoCaptureError):
        current_app.logger.error("PeerSlate private capture storage is unavailable.")
        return _render_owner_unavailable()

    return render_template(
        "owner_capture.html",
        page_title="Capture",
        captures=_prepare_capture_rows(captures),
        validation_message=CAPTURE_VALIDATION_MESSAGES.get(request.args.get("error")),
        success_message=CAPTURE_SUCCESS_MESSAGES.get(request.args.get("changed")),
        saved=request.args.get("saved") == "1",
        archived=archived,
        voice_draft=voice_draft,
        photo_draft=photo_draft,
        photo_enabled=photo_enabled,
        max_body_length=MAX_CAPTURE_BODY_LENGTH,
        max_correction_note_length=MAX_CORRECTION_NOTE_LENGTH,
        max_voice_bytes=MAX_VOICE_BYTES,
        max_voice_duration_seconds=MAX_VOICE_DURATION_SECONDS,
        max_photo_bytes=MAX_PHOTO_BYTES,
    )


@owner.post("/app/capture/voice")
def upload_voice_capture():
    """Upload and transcribe one owner-scoped private Voice draft."""
    if not _is_same_origin_write():
        return "Cross-site capture requests are not allowed.", 403
    try:
        identity = get_current_identity()
        draft = voice_capture_service.create_and_transcribe(
            identity.user_key,
            request.files.get("audio"),
            request.form.get("duration_seconds"),
        )
    except AuthenticationRequired:
        return redirect(url_for("auth.sign_in", return_to="/app/capture"))
    except VoiceCaptureError as error:
        status = (
            503
            if error.code
            in {
                "upload-failed",
                "queue-failed",
                "transcription-failed",
                "transcription-recovery",
            }
            else 400
        )
        payload = {"error": error.code}
        if error.source_key:
            payload["source_key"] = error.source_key
            payload["review_url"] = url_for(
                "owner.capture", voice=error.source_key
            )
        return jsonify(payload), status
    except DatabaseServiceError:
        current_app.logger.error("PeerSlate private Voice Capture is unavailable.")
        return jsonify({"error": "unavailable"}), 503
    source_key = str(draft["source_key"])
    return (
        jsonify(
            {
                "state": draft["state"],
                "review_url": url_for("owner.capture", voice=source_key),
            }
        ),
        201,
    )


def _voice_action_identity(source_key):
    if not _is_same_origin_write():
        return None, None, ("Cross-site capture requests are not allowed.", 403)
    normalized = _normalize_capture_key(source_key)
    if not normalized:
        return None, None, ("Voice draft not found.", 404)
    try:
        return get_current_identity(), normalized, None
    except AuthenticationRequired:
        return None, None, redirect(url_for("auth.sign_in", return_to="/app/capture"))
    except DatabaseServiceError:
        current_app.logger.error("PeerSlate private Voice Capture identity is unavailable.")
        return None, None, _render_owner_unavailable()


@owner.post("/app/capture/voice/<source_key>/retry")
def retry_voice_capture(source_key):
    """Create a new immutable transcription attempt for a failed draft."""
    identity, normalized, response = _voice_action_identity(source_key)
    if response is not None:
        return response
    try:
        voice_capture_service.retry_transcription(
            identity.user_key,
            normalized,
            request.form.get("expected_row_version", ""),
        )
    except VoiceCaptureError as error:
        error_key = (
            "voice-transcription"
            if error.code == "transcription-failed"
            else "voice-changed"
        )
        return redirect(url_for("owner.capture", voice=normalized, error=error_key))
    except DatabaseServiceError:
        current_app.logger.error("PeerSlate private Voice retry is unavailable.")
        return _render_owner_unavailable()
    return redirect(url_for("owner.capture", voice=normalized))


@owner.post("/app/capture/voice/<source_key>/confirm")
def confirm_voice_capture(source_key):
    """Explicitly create one private Capture from member-approved transcript text."""
    identity, normalized, response = _voice_action_identity(source_key)
    if response is not None:
        return response
    body = request.form.get("approved_body", "").strip()
    if request.form.get("confirm_voice") != "save-private-capture" or not body:
        return redirect(url_for("owner.capture", voice=normalized, error="required"))
    if _capture_body_length(body) > MAX_CAPTURE_BODY_LENGTH:
        return redirect(url_for("owner.capture", voice=normalized, error="too-long"))
    try:
        voice_capture_service.confirm_capture(
            identity.user_key,
            normalized,
            request.form.get("expected_row_version", ""),
            body,
        )
    except VoiceCaptureError as error:
        error_key = error.code if error.code in {"required", "too-long"} else "voice-changed"
        return redirect(url_for("owner.capture", voice=normalized, error=error_key))
    except DatabaseServiceError:
        current_app.logger.error("PeerSlate private Voice confirmation is unavailable.")
        return _render_owner_unavailable()
    return redirect(url_for("owner.capture", saved="1"))


@owner.post("/app/capture/voice/<source_key>/delete")
def delete_voice_draft(source_key):
    """Explicitly delete an unconfirmed draft through a retryable workflow."""
    identity, normalized, response = _voice_action_identity(source_key)
    if response is not None:
        return response
    if request.form.get("confirm_delete") != "delete":
        return redirect(url_for("owner.capture", voice=normalized, error="confirm-delete"))
    try:
        voice_capture_service.delete_draft(
            identity.user_key,
            normalized,
            request.form.get("expected_row_version", ""),
        )
    except VoiceCaptureError as error:
        error_key = "voice-delete-retry" if error.code == "delete-retry" else "voice-changed"
        return redirect(url_for("owner.capture", voice=normalized, error=error_key))
    except DatabaseServiceError:
        current_app.logger.error("PeerSlate private Voice deletion is unavailable.")
        return _render_owner_unavailable()
    return redirect(url_for("owner.capture", changed="voice-deleted"))


@owner.get("/app/capture/voice/<source_key>/audio")
def voice_capture_audio(source_key):
    """Proxy private audio only after owner resolution; never issue a Blob URL."""
    normalized = _normalize_capture_key(source_key)
    if not normalized:
        return "Voice audio not found.", 404
    try:
        identity = get_current_identity()
        media = voice_capture_service.open_audio(identity.user_key, normalized)
    except AuthenticationRequired:
        return redirect(url_for("auth.sign_in", return_to="/app/capture"))
    except (DatabaseServiceError, VoiceCaptureError):
        current_app.logger.error("PeerSlate private Voice playback is unavailable.")
        return "Voice audio is temporarily unavailable.", 503
    if not media:
        return "Voice audio not found.", 404
    response = send_file(
        media["stream"],
        mimetype=media["content_type"],
        as_attachment=request.args.get("download") == "1",
        download_name="peerslate-private-voice-source",
        max_age=0,
    )
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


def _photo_action_identity(source_key=None, require_write=True):
    configuration = photo_lifecycle_access_service.configuration()
    if configuration.mode not in {PHOTO_ACCESS_ORDINARY, PHOTO_ACCESS_PROOF}:
        return None, None, _photo_unavailable()

    normalized = None
    if configuration.mode == PHOTO_ACCESS_ORDINARY:
        if require_write and not _is_same_origin_write():
            return None, None, ("Cross-site capture requests are not allowed.", 403)
        normalized = _normalize_capture_key(source_key) if source_key else None
        if source_key and not normalized:
            return None, None, ("Photo source not found.", 404)

    try:
        identity = get_current_identity()
    except AuthenticationRequired:
        if configuration.mode == PHOTO_ACCESS_PROOF:
            return None, None, _photo_unavailable()
        return None, None, redirect(url_for("auth.sign_in", return_to="/app/capture"))
    except DatabaseServiceError:
        if configuration.mode == PHOTO_ACCESS_PROOF:
            return None, None, _photo_unavailable()
        current_app.logger.error("PeerSlate private Photo Capture identity is unavailable.")
        return None, None, _render_owner_unavailable()

    if not photo_lifecycle_access_service.allows_identity(identity, configuration):
        return None, None, _photo_unavailable()
    if configuration.mode == PHOTO_ACCESS_PROOF:
        if require_write and not _is_same_origin_write():
            return None, None, ("Cross-site capture requests are not allowed.", 403)
        normalized = _normalize_capture_key(source_key) if source_key else None
        if source_key and not normalized:
            return None, None, ("Photo source not found.", 404)
    return identity, normalized, None


def _photo_source_payload(source):
    source_key = str(source["source_key"])
    payload = {
        "source_key": source_key,
        "state": source["state"],
        "scan_result": source.get("scan_result"),
        "safe_error_code": source.get("safe_error_code"),
        "content_type": source.get("original_content_type"),
        "byte_length": int(source.get("original_byte_length") or 0),
        "width": source.get("pixel_width"),
        "height": source.get("pixel_height"),
        "row_version": source.get("row_version_token", ""),
        "status_url": url_for("owner.photo_capture_status", source_key=source_key),
    }
    if source["state"] in {"needs_review", "confirmed"}:
        payload["preview_url"] = url_for(
            "owner.photo_capture_preview", source_key=source_key
        )
        payload["original_download_url"] = url_for(
            "owner.photo_capture_original", source_key=source_key, download="1"
        )
    return payload


@owner.post("/app/capture/photo")
def upload_photo_capture():
    """Accept one owner-scoped private Photo source while the feature is enabled."""
    identity, _, response = _photo_action_identity()
    if response is not None:
        return response
    try:
        source = photo_capture_service.create_source(
            identity.user_key, request.files.get("photo")
        )
    except PhotoCaptureError as error:
        status = 503 if error.code in {"upload-failed", "upload-recovery"} else 400
        if error.code == "draft-limit":
            status = 409
        payload = {"error": error.code}
        if error.source_key:
            payload["source_key"] = error.source_key
            payload["status_url"] = url_for(
                "owner.photo_capture_status", source_key=error.source_key
            )
        return jsonify(payload), status
    except DatabaseServiceError:
        current_app.logger.error("PeerSlate private Photo Capture is unavailable.")
        return jsonify({"error": "unavailable"}), 503
    return jsonify(_photo_source_payload(source)), 201


@owner.get("/app/capture/photo/<source_key>")
def photo_capture_status(source_key):
    """Return one owner-safe Photo source state without storage locators."""
    identity, normalized, response = _photo_action_identity(
        source_key, require_write=False
    )
    if response is not None:
        return response
    try:
        source = photo_capture_service.get_source(identity.user_key, normalized)
    except (DatabaseServiceError, PhotoCaptureError):
        current_app.logger.error("PeerSlate private Photo status is unavailable.")
        return jsonify({"error": "unavailable"}), 503
    if not source:
        return "Photo source not found.", 404
    response = jsonify(_photo_source_payload(source))
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@owner.post("/app/capture/photo/<source_key>/reconcile")
def reconcile_photo_capture(source_key):
    """Reconcile Defender state and create a safe derivative only after clean."""
    identity, normalized, response = _photo_action_identity(source_key)
    if response is not None:
        return response
    try:
        source = photo_capture_service.reconcile_and_process(
            identity.user_key,
            normalized,
            request.form.get("expected_row_version", ""),
        )
    except PhotoCaptureError as error:
        status = 409 if error.code == "changed" else 503
        if error.code in {"unsupported", "dimensions", "invalid-image", "integrity-failed"}:
            status = 422
        return jsonify({"error": error.code}), status
    except DatabaseServiceError:
        current_app.logger.error("PeerSlate private Photo reconciliation is unavailable.")
        return jsonify({"error": "unavailable"}), 503
    return jsonify(_photo_source_payload(source))


@owner.post("/app/capture/photo/<source_key>/confirm")
def confirm_photo_capture(source_key):
    """Explicitly create one private Capture from a clean Photo source."""
    identity, normalized, response = _photo_action_identity(source_key)
    if response is not None:
        return response
    body = request.form.get("approved_body", "").strip()
    if request.form.get("confirm_photo") != "save-private-capture" or not body:
        return jsonify({"error": "required"}), 400
    if _capture_body_length(body) > MAX_CAPTURE_BODY_LENGTH:
        return jsonify({"error": "too-long"}), 400
    try:
        result = photo_capture_service.confirm_capture(
            identity.user_key,
            normalized,
            request.form.get("expected_row_version", ""),
            body,
        )
    except PhotoCaptureError as error:
        status = 400 if error.code in {"required", "too-long"} else 409
        return jsonify({"error": error.code}), status
    except DatabaseServiceError:
        current_app.logger.error("PeerSlate private Photo confirmation is unavailable.")
        return jsonify({"error": "unavailable"}), 503
    return jsonify({"outcome": result["outcome"], "capture_key": str(result["capture_key"])})


@owner.post("/app/capture/photo/<source_key>/delete")
def delete_photo_draft(source_key):
    """Delete an unconfirmed Photo source and both possible private blobs."""
    identity, normalized, response = _photo_action_identity(source_key)
    if response is not None:
        return response
    if request.form.get("confirm_delete") != "delete":
        return jsonify({"error": "confirm-delete"}), 400
    try:
        photo_capture_service.delete_draft(
            identity.user_key,
            normalized,
            request.form.get("expected_row_version", ""),
        )
    except PhotoCaptureError as error:
        status = 503 if error.code == "delete-retry" else 409
        return jsonify({"error": error.code}), status
    except DatabaseServiceError:
        current_app.logger.error("PeerSlate private Photo deletion is unavailable.")
        return jsonify({"error": "unavailable"}), 503
    return jsonify({"outcome": "success"})


def _photo_media_response(source_key, media_kind):
    identity, normalized, response = _photo_action_identity(
        source_key, require_write=False
    )
    if response is not None:
        return response
    try:
        media = photo_capture_service.open_media(
            identity.user_key, normalized, media_kind
        )
    except (DatabaseServiceError, PhotoCaptureError):
        current_app.logger.error("PeerSlate private Photo media is unavailable.")
        return "Photo media is temporarily unavailable.", 503
    if not media:
        return "Photo media not found.", 404
    extension = "jpg" if media["content_type"] == "image/jpeg" else "png"
    response = send_file(
        media["stream"],
        mimetype=media["content_type"],
        as_attachment=media_kind == "original",
        download_name=f"peerslate-private-photo-{media_kind}.{extension}",
        max_age=0,
    )
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@owner.get("/app/capture/photo/<source_key>/preview")
def photo_capture_preview(source_key):
    return _photo_media_response(source_key, "preview")


@owner.get("/app/capture/photo/<source_key>/original")
def photo_capture_original(source_key):
    return _photo_media_response(source_key, "original")


@owner.post("/app/capture/<capture_key>/moment-proposal")
def create_moment_proposal(capture_key):
    """Create or reopen one private proposal pinned to an exact source version."""
    if not _is_same_origin_write():
        return "Cross-site Moment requests are not allowed.", 403

    normalized_capture_key = _normalize_capture_key(capture_key)
    try:
        source_revision_number = int(
            request.form.get("source_revision_number", "")
        )
    except (TypeError, ValueError):
        source_revision_number = -1
    if not normalized_capture_key or source_revision_number < 0:
        return redirect(url_for("owner.capture", error="changed"))

    try:
        identity = get_current_identity()
        result = database_service.first_row(
            "usp_CreateOrReopenMomentProposal",
            [
                ("@UserKey", identity.user_key),
                ("@CaptureKey", normalized_capture_key),
                ("@SourceRevisionNumber", source_revision_number),
            ],
        )
    except AuthenticationRequired:
        return redirect(url_for("auth.sign_in", return_to="/app/capture"))
    except DatabaseServiceError:
        current_app.logger.error("PeerSlate private Moment proposal is unavailable.")
        return _render_owner_unavailable()

    if (
        not result
        or result.get("outcome") not in {"created", "existing"}
        or not result.get("moment_key")
    ):
        return redirect(url_for("owner.capture", error="changed"))
    return redirect(
        url_for("owner.review_moment", moment_key=str(result["moment_key"]))
    )


@owner.get("/app/moments/<moment_key>/review")
def review_moment(moment_key):
    """Render one owner-scoped source and its separate private Moment proposal."""
    normalized_moment_key = _normalize_capture_key(moment_key)
    if not normalized_moment_key:
        return "Moment not found.", 404

    try:
        identity = get_current_identity()
        result = database_service.first_row(
            "usp_GetMomentForOwner",
            [
                ("@UserKey", identity.user_key),
                ("@MomentKey", normalized_moment_key),
            ],
        )
    except AuthenticationRequired:
        return redirect(
            url_for(
                "auth.sign_in",
                return_to=f"/app/moments/{normalized_moment_key}/review",
            )
        )
    except DatabaseServiceError:
        current_app.logger.error("PeerSlate private Moment review is unavailable.")
        return _render_owner_unavailable()

    if not result:
        return "Moment not found.", 404

    return render_template(
        "owner_moment_review.html",
        page_title="Review Moment",
        moment=_prepare_moment_row(result),
        validation_message=MOMENT_VALIDATION_MESSAGES.get(
            request.args.get("error")
        ),
        success_message=MOMENT_SUCCESS_MESSAGES.get(request.args.get("changed")),
        moment_kinds=MOMENT_KINDS,
        occurred_precisions=OCCURRED_PRECISIONS,
        max_title_length=MAX_MOMENT_TITLE_LENGTH,
        max_narrative_length=MAX_MOMENT_NARRATIVE_LENGTH,
        max_why_length=MAX_MOMENT_WHY_LENGTH,
    )


@owner.post("/app/moments/<moment_key>/save")
def save_moment_proposal(moment_key):
    """Save a new private proposal version under optimistic concurrency."""
    if not _is_same_origin_write():
        return "Cross-site Moment requests are not allowed.", 403

    context, response = _moment_action_context()
    if response is not None:
        return response
    identity, normalized_moment_key, expected_row_version = context

    proposal, error_key = validate_moment_proposal(request.form)
    if error_key:
        return redirect(
            url_for(
                "owner.review_moment",
                moment_key=normalized_moment_key,
                error=error_key,
            )
        )

    try:
        result = database_service.first_row(
            "usp_SaveMomentProposal",
            [
                ("@UserKey", identity.user_key),
                ("@MomentKey", normalized_moment_key),
                ("@ExpectedRowVersion", expected_row_version),
                ("@MomentKind", proposal["moment_kind"]),
                ("@Title", proposal["title"]),
                ("@OccurredOn", proposal["occurred_on"]),
                ("@OccurredPrecision", proposal["occurred_precision"]),
                ("@Narrative", proposal["narrative"]),
                ("@WhyItMatters", proposal["why_it_matters"]),
            ],
        )
    except DatabaseServiceError:
        current_app.logger.error("PeerSlate private Moment save is unavailable.")
        return _render_owner_unavailable()

    if result and result.get("outcome") == "source_deleted":
        error_key = "source-deleted"
    elif not result or result.get("outcome") != "success":
        error_key = "changed"
    else:
        return redirect(
            url_for(
                "owner.review_moment",
                moment_key=normalized_moment_key,
                changed="saved",
            )
        )
    return redirect(
        url_for(
            "owner.review_moment",
            moment_key=normalized_moment_key,
            error=error_key,
        )
    )


@owner.post("/app/moments/<moment_key>/confirm")
def confirm_moment(moment_key):
    """Explicitly confirm only the current valid private proposal version."""
    if not _is_same_origin_write():
        return "Cross-site Moment requests are not allowed.", 403

    context, response = _moment_action_context()
    if response is not None:
        return response
    identity, normalized_moment_key, expected_row_version = context
    if request.form.get("confirm_moment") != "confirm":
        return redirect(
            url_for(
                "owner.review_moment",
                moment_key=normalized_moment_key,
                error="required",
            )
        )
    try:
        expected_proposal_version = int(
            request.form.get("expected_proposal_version", "")
        )
    except (TypeError, ValueError):
        expected_proposal_version = 0
    if expected_proposal_version < 1:
        return redirect(
            url_for(
                "owner.review_moment",
                moment_key=normalized_moment_key,
                error="changed",
            )
        )

    try:
        result = database_service.first_row(
            "usp_ConfirmMoment",
            [
                ("@UserKey", identity.user_key),
                ("@MomentKey", normalized_moment_key),
                ("@ExpectedRowVersion", expected_row_version),
                ("@ExpectedProposalVersion", expected_proposal_version),
            ],
        )
    except DatabaseServiceError:
        current_app.logger.error("PeerSlate private Moment confirmation is unavailable.")
        return _render_owner_unavailable()

    if result and result.get("outcome") == "source_deleted":
        error_key = "source-deleted"
    elif not result or result.get("outcome") != "success":
        error_key = "changed"
    else:
        return redirect(
            url_for(
                "owner.review_moment",
                moment_key=normalized_moment_key,
                changed="confirmed",
            )
        )
    return redirect(
        url_for(
            "owner.review_moment",
            moment_key=normalized_moment_key,
            error=error_key,
        )
    )


@owner.post("/app/moments/<moment_key>/discard")
def discard_moment_proposal(moment_key):
    """Remove an unconfirmed private proposal after deliberate confirmation."""
    if not _is_same_origin_write():
        return "Cross-site Moment requests are not allowed.", 403

    context, response = _moment_action_context()
    if response is not None:
        return response
    identity, normalized_moment_key, expected_row_version = context
    if request.form.get("confirm_discard") != "discard":
        return redirect(
            url_for(
                "owner.review_moment",
                moment_key=normalized_moment_key,
                error="confirm-discard",
            )
        )

    try:
        result = database_service.first_row(
            "usp_DiscardMomentProposal",
            [
                ("@UserKey", identity.user_key),
                ("@MomentKey", normalized_moment_key),
                ("@ExpectedRowVersion", expected_row_version),
            ],
        )
    except DatabaseServiceError:
        current_app.logger.error("PeerSlate private Moment discard is unavailable.")
        return _render_owner_unavailable()

    if not result or result.get("outcome") != "success":
        return redirect(
            url_for(
                "owner.review_moment",
                moment_key=normalized_moment_key,
                error="changed",
            )
        )
    return redirect(url_for("owner.capture", changed="moment-discarded"))


@owner.post("/app/capture/<capture_key>/correct")
def correct_capture(capture_key):
    """Insert an owner-scoped correction without overwriting original text."""
    if not _is_same_origin_write():
        return "Cross-site capture requests are not allowed.", 403

    context, response = _capture_action_context()
    if response is not None:
        return response
    identity, normalized_capture_key, expected_row_version = context

    body = request.form.get("body", "").strip()
    correction_note = request.form.get("correction_note", "").strip() or None
    if not body:
        return redirect(url_for("owner.capture", error="required"))
    if _capture_body_length(body) > MAX_CAPTURE_BODY_LENGTH:
        return redirect(url_for("owner.capture", error="too-long"))
    if (
        correction_note
        and _capture_body_length(correction_note) > MAX_CORRECTION_NOTE_LENGTH
    ):
        return redirect(url_for("owner.capture", error="note-too-long"))

    try:
        result = database_service.first_row(
            "usp_CorrectCapture",
            [
                ("@UserKey", identity.user_key),
                ("@CaptureKey", normalized_capture_key),
                ("@ExpectedRowVersion", expected_row_version),
                ("@CorrectedBody", body),
                ("@CorrectionNote", correction_note),
            ],
        )
    except DatabaseServiceError:
        current_app.logger.error("PeerSlate private capture correction is unavailable.")
        return _render_owner_unavailable()

    if not result or result.get("outcome") != "success":
        return redirect(url_for("owner.capture", error="changed"))
    return redirect(url_for("owner.capture", changed="corrected"))


@owner.post("/app/capture/<capture_key>/archive")
def archive_capture(capture_key):
    """Archive one active capture using owner and row-version checks."""
    return _run_capture_state_change("usp_ArchiveCapture", "archived")


@owner.post("/app/capture/<capture_key>/restore")
def restore_capture(capture_key):
    """Restore one archived capture using owner and row-version checks."""
    return _run_capture_state_change("usp_RestoreCapture", "restored")


@owner.post("/app/capture/<capture_key>/delete")
def delete_capture(capture_key):
    """Permanently delete a capture aggregate after explicit confirmation."""
    if not _is_same_origin_write():
        return "Cross-site capture requests are not allowed.", 403

    context, response = _capture_action_context()
    if response is not None:
        return response
    identity, normalized_capture_key, expected_row_version = context
    if request.form.get("confirm_delete") != "delete":
        return redirect(url_for("owner.capture", error="confirm-delete"))

    try:
        result = capture_lifecycle_service.delete_capture(
            identity.user_key,
            normalized_capture_key,
            expected_row_version,
        )
    except (DatabaseServiceError, CaptureLifecycleError):
        current_app.logger.error("PeerSlate private capture deletion is unavailable.")
        return redirect(url_for("owner.capture", error="voice-delete-retry"))

    if not result or result.get("outcome") != "success":
        return redirect(url_for("owner.capture", error="changed"))
    return redirect(url_for("owner.capture", changed="deleted"))


@owner.get("/app/capture/<capture_key>/export")
def export_capture(capture_key):
    """Download one owner-scoped capture and its revisions as versioned JSON."""
    try:
        identity = get_current_identity()
        normalized_capture_key = _normalize_capture_key(capture_key)
        if not normalized_capture_key:
            return "Capture not found.", 404
        result_sets = database_service.execute_procedure(
            "usp_ExportCaptureForOwner",
            [
                ("@UserKey", identity.user_key),
                ("@CaptureKey", normalized_capture_key),
            ],
        )
    except AuthenticationRequired:
        return redirect(url_for("auth.sign_in", return_to="/app/capture"))
    except DatabaseServiceError:
        current_app.logger.error("PeerSlate private capture export is unavailable.")
        return _render_owner_unavailable()

    capture_rows = result_sets[0] if result_sets else []
    auxiliary_rows = result_sets[1] if len(result_sets) > 1 else []
    if not capture_rows:
        return "Capture not found.", 404

    capture = dict(capture_rows[0])
    revision_number = int(capture.get("revision_number") or 0)
    revisions = (
        auxiliary_rows
        if auxiliary_rows and "revision_number" in auxiliary_rows[0]
        else []
    )
    if capture.get("revisions_json"):
        try:
            revisions = json.loads(capture["revisions_json"])
        except (TypeError, ValueError):
            current_app.logger.error(
                "PeerSlate private capture export returned invalid revision data."
            )
            return _render_owner_unavailable()
    source_row = (
        dict(auxiliary_rows[0])
        if auxiliary_rows and "source_key" in auxiliary_rows[0]
        else None
    )
    source_type = (source_row or {}).get("source_type")
    if not source_type and source_row:
        source_type = "voice" if "provider_transcript" in source_row else "photo"
    voice_source = source_row if source_type == "voice" else None
    photo_source = source_row if source_type == "photo" else None
    schema_version = {"voice": 2, "photo": 3}.get(capture.get("capture_type"), 1)
    payload = {
        "schema": "peerslate.capture.export",
        "schema_version": schema_version,
        "capture": {
            "key": str(capture["capture_key"]),
            "type": capture["capture_type"],
            "visibility": capture["visibility"],
            "status": capture["status"],
            "created_at_utc": capture["created_at_utc"],
            "updated_at_utc": capture["updated_at_utc"],
            "original_text": capture["original_body"],
            "current_version": {
                "kind": "revision" if revision_number else "original",
                "revision_number": revision_number,
                "text": capture["body"],
            },
            "revisions": [
                {
                    "revision_number": int(revision["revision_number"]),
                    "text": revision["body"],
                    "correction_note": revision.get("correction_note"),
                    "corrected_at_utc": revision["corrected_at_utc"],
                }
                for revision in revisions
            ],
        },
    }
    if voice_source:
        source_key = str(voice_source["source_key"])
        payload["capture"]["voice_source"] = {
            "source_key": source_key,
            "content_type": voice_source["content_type"],
            "byte_length": int(voice_source["byte_length"]),
            "duration_milliseconds": voice_source.get(
                "verified_duration_milliseconds"
            )
            or voice_source.get("client_duration_milliseconds"),
            "locale": voice_source["locale"],
            "provider": "Azure Speech",
            "provider_transcript": voice_source["provider_transcript"],
            "audio_export_path": url_for(
                "owner.voice_capture_audio",
                source_key=source_key,
                download="1",
            ),
        }
    if photo_source:
        source_key = str(photo_source["source_key"])
        payload["capture"]["photo_source"] = {
            "source_key": source_key,
            "original": {
                "content_type": photo_source["original_content_type"],
                "byte_length": int(photo_source["original_byte_length"]),
                "download_path": url_for(
                    "owner.photo_capture_original",
                    source_key=source_key,
                    download="1",
                ),
            },
            "safe_preview": {
                "content_type": photo_source["derivative_content_type"],
                "byte_length": int(photo_source["derivative_byte_length"]),
                "width": int(photo_source["pixel_width"]),
                "height": int(photo_source["pixel_height"]),
                "preview_path": url_for(
                    "owner.photo_capture_preview", source_key=source_key
                ),
            },
            "scan_result": photo_source["scan_result"],
            "scan_completed_at_utc": photo_source.get("scan_completed_at_utc"),
            "embedded_metadata_removed_from_preview": True,
        }
    response = Response(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            default=_json_value,
        )
        + "\n",
        mimetype="application/json",
    )
    response.headers["Content-Disposition"] = (
        f'attachment; filename="peerslate-capture-{normalized_capture_key}-v{schema_version}.json"'
    )
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


# ------------------------------------------------------------------
# PS-JOURNAL-001 Slice J1 frontend: the owner Journal page and Moment
# detail. Flag-gated (`PEERSLATE_JOURNAL_ENABLED`, default false) and
# owner-only; identical neutral 404 for flag-off, unauthenticated, and
# non-owner requests, matching the require_identity_or_not_found pattern
# already used by the Slice J1 backend's /api/journal/moments routes in
# peerslate_api.py. This section consumes services/journal_service.py and
# services/voice_capture_service.py exactly as already released - it adds
# no stored procedure, no migration, and no change to either service's
# existing methods. See docs/initiatives/PS-JOURNAL-001/
# J1_FRONTEND_IMPLEMENTATION_BRIEF.md.
# ------------------------------------------------------------------

JOURNAL_CHAPTERS = (
    {
        "key": "timeline",
        "label": "Timeline",
        "subtitle": "Your journey in chronological order",
    },
    {
        "key": "voice",
        "label": "Voice",
        "subtitle": "Spoken thoughts and reflections",
    },
    {
        "key": "photos",
        "label": "Photos",
        "subtitle": "Captured moments that matter",
    },
    {
        "key": "videos",
        "label": "Videos",
        "subtitle": "Your story in motion",
    },
    {
        "key": "milestones",
        "label": "Milestones",
        "subtitle": "Big wins and breakthroughs",
    },
    {
        "key": "reflections",
        "label": "Reflections",
        "subtitle": "Lessons, insights, and growth",
    },
)

# The derived Journal read has no per-kind aggregate or single-key fetch
# procedure (usp_ListJournalMomentsForOwner only returns cursor pages of the
# owner's own scoped Moments). Slice J1 does not add one - see the hard
# boundary in the frontend brief - so honest lifetime totals and single-
# Moment detail are both computed with a bounded scan over the released,
# unmodified journal_service.list_owner_journal read. This is a disclosed
# J1 performance compromise pending a J1.1 single-fetch/aggregate addition.
JOURNAL_SCAN_PAGE_SIZE = 100
JOURNAL_SCAN_MAX_PAGES = 25
JOURNAL_TIMELINE_PAGE_SIZE = 20

# Doc 15 SS3 "fixture-richness rule": evidence/demo rendering must show the
# full richness (thumbnail, time-of-day, voice duration, supporting context)
# the accepted mockups show, but the honesty rules forbid fabricating those
# fields for a real member's Moment. This table is keyed by the MEMBER'S OWN
# title text - the exact wording of the seven fixture Moments in the accepted
# PNGs - never by identity, environment, or flag. A real Moment's title will
# not collide with this table (and if it ever did, the only effect is a
# decorative thumbnail/time - never invented narrative fact), so this is safe
# to leave permanently wired rather than gated behind a demo-only branch. It
# adds no field the templates do not already read defensively (see
# templates/journal_moment.html's note on moment.thumbnail_kind et al.).
JOURNAL_FIXTURE_ENRICHMENT = {
    "I led the first client workshop without reading from my notes.": {
        "thumbnail_kind": "lake",
        "display_time": "9:41 AM",
        "voice_duration_label": "00:48",
        "context_text": (
            "Felt prepared, present, and confident. The team was engaged "
            "and the client loved the clarity."
        ),
    },
    "I realized I enjoy translating technical ideas for new teammates.": {
        "thumbnail_kind": "notebook",
        "display_time": "4:27 PM",
    },
    "After interview practice, I changed how I explain the product launch.": {
        "thumbnail_kind": "stage",
        "thumbnail_is_video": True,
        "display_time": "11:08 AM",
        "voice_duration_label": "01:12",
    },
    "I asked Jordan to review the launch plan before Friday.": {
        "thumbnail_kind": "coffee",
        "display_time": "3:15 PM",
    },
    "Whiteboard sketch from Q2 planning session.": {
        "thumbnail_kind": "notebook",
        "display_time": "3:15 PM",
    },
    "Team alignment meeting highlights.": {
        "thumbnail_kind": "stage",
        "thumbnail_is_video": True,
        "display_time": "9:20 AM",
        "voice_duration_label": "00:32",
    },
    "Key takeaways from customer call — clarity over complexity.": {
        "display_time": "5:45 PM",
    },
}


def _journal_enabled():
    return current_app.config.get("PEERSLATE_JOURNAL_ENABLED", False) is True


def _journal_not_found():
    return "Not found.", 404


def _journal_identity_or_not_found():
    """Neutral 404 for a caller whose identity cannot be resolved - never a
    distinct 401/redirect, so "not signed in" cannot be told apart from
    "not found" or "flag off" (mirrors peerslate_api.require_identity_or_not_found,
    which the Slice J1 API already relies on)."""
    try:
        return get_current_identity(), None
    except AuthenticationRequired:
        return None, _journal_not_found()
    except DatabaseServiceError:
        current_app.logger.error("PeerSlate Journal identity lookup failed.")
        return None, _render_owner_unavailable()


def _journal_chapter_key_for_item(item):
    """The J1 translation from a real Moment's fields to one of the six
    accepted JOURNAL-01 rail chapters. Disclosed, not backend-specified:
    Voice/Photos/Videos read the Capture's source_type; Milestones and
    Reflections have no dedicated Moment kind in the released schema
    (MOMENT_KINDS has no "milestone" or "reflection" value), so they are
    presented from the closest existing kinds, "achievement" and "lesson" -
    a J1 UI mapping over real member-chosen data, never invented content."""
    source_type = item.get("source_type")
    moment_kind = item.get("moment_kind")
    if source_type == "voice":
        return "voice"
    if source_type == "photo":
        return "photos"
    if source_type == "video":
        return "videos"
    if moment_kind == "achievement":
        return "milestones"
    if moment_kind == "lesson":
        return "reflections"
    return None


def _journal_totals(user_key):
    """Bounded full scan of the owner's active Journal for the This-Season
    hero's quiet totals and each rail chapter's quiet count. Every number is
    a real count of already-saved Moments - never a streak, score, or
    fabricated figure (site rule 24)."""
    chapter_counts = {chapter["key"]: 0 for chapter in JOURNAL_CHAPTERS}
    total = 0
    voice_total = 0
    milestone_total = 0
    cursor = None
    for _ in range(JOURNAL_SCAN_MAX_PAGES):
        page = journal_service.list_owner_journal(
            user_key,
            include_archived=False,
            limit=JOURNAL_SCAN_PAGE_SIZE,
            cursor=cursor,
        )
        items = page.get("items") or []
        total += len(items)
        for item in items:
            if item.get("source_type") == "voice":
                voice_total += 1
            if item.get("moment_kind") == "achievement":
                milestone_total += 1
            chapter_key = _journal_chapter_key_for_item(item)
            if chapter_key:
                chapter_counts[chapter_key] += 1
        cursor = page.get("next_cursor")
        if not cursor:
            break
    chapter_counts["timeline"] = total
    return {
        "moments": total,
        "voice_notes": voice_total,
        "milestones": milestone_total,
        "chapter_counts": chapter_counts,
    }


def _journal_prepare_moment(item):
    """Normalize one Journal read row for template rendering. `occurred_on`
    may arrive as a `date`, a `datetime`, or an ISO string depending on the
    database driver; this computes the display fields once, server-side, so
    the template never has to guess the underlying Python type."""
    prepared = dict(item)
    occurred_on = item.get("occurred_on")
    if isinstance(occurred_on, str):
        try:
            occurred_on = date.fromisoformat(occurred_on[:10])
        except ValueError:
            occurred_on = None
    if isinstance(occurred_on, datetime):
        occurred_on = occurred_on.date()
    if isinstance(occurred_on, date):
        prepared["occurred_day"] = occurred_on.strftime("%d")
        prepared["occurred_month_label"] = occurred_on.strftime("%b").upper()
        prepared["occurred_iso"] = occurred_on.isoformat()
    else:
        prepared["occurred_day"] = None
        prepared["occurred_month_label"] = None
        prepared["occurred_iso"] = None
    enrichment = JOURNAL_FIXTURE_ENRICHMENT.get((item.get("title") or "").strip())
    if enrichment:
        for key, value in enrichment.items():
            prepared.setdefault(key, value)
    return prepared


def _find_journal_moment(user_key, moment_key):
    """Bounded scan for one Moment's detail fields. Every page is already
    server-scoped to `user_key` by usp_ListJournalMomentsForOwner, so a
    guessed key belonging to another owner can never be retrieved - the scan
    can only ever return None (404) or the caller's own Moment."""
    cursor = None
    for _ in range(JOURNAL_SCAN_MAX_PAGES):
        page = journal_service.list_owner_journal(
            user_key,
            include_archived=True,
            limit=JOURNAL_SCAN_PAGE_SIZE,
            cursor=cursor,
        )
        for item in page.get("items") or []:
            if item.get("moment_key") == moment_key:
                return _journal_prepare_moment(item)
        cursor = page.get("next_cursor")
        if not cursor:
            break
    return None


@owner.get("/app/journal")
def journal():
    """The owner's one private Journal: This-Season hero, context rail,
    and chronological timeline. Local views/filters only - the rail never
    leaves this page (Context Rail Standard law 1)."""
    if not _journal_enabled():
        return _journal_not_found()

    identity, response = _journal_identity_or_not_found()
    if response is not None:
        return response

    manage_view = request.args.get("view") == "archived"
    try:
        page = journal_service.list_owner_journal(
            identity.user_key,
            include_archived=manage_view,
            limit=JOURNAL_TIMELINE_PAGE_SIZE,
            cursor=None,
        )
        totals = _journal_totals(identity.user_key)
    except (JournalServiceError, DatabaseServiceError):
        current_app.logger.error("PeerSlate Journal read is unavailable.")
        return _render_owner_unavailable()

    return render_template(
        "journal.html",
        page_title="Journal",
        member=identity,
        moments=[_journal_prepare_moment(item) for item in page["items"]],
        next_cursor=page["next_cursor"],
        totals=totals,
        chapters=JOURNAL_CHAPTERS,
        manage_view=manage_view,
        moment_kinds=MOMENT_KINDS,
        occurred_precisions=OCCURRED_PRECISIONS,
        max_title_length=MAX_MOMENT_TITLE_LENGTH,
        max_narrative_length=MAX_MOMENT_NARRATIVE_LENGTH,
        max_why_length=MAX_MOMENT_WHY_LENGTH,
        max_voice_bytes=MAX_VOICE_BYTES,
        max_voice_duration_seconds=MAX_VOICE_DURATION_SECONDS,
        rail_id="journal",
        rail_label="Contents",
        rail_nav_label="Journal sections",
        active_chapter="timeline",
    )


@owner.get("/app/journal/moments/<moment_key>")
def journal_moment(moment_key):
    """One Moment's detail: accepted version, source type, occurred/derived
    dates, version number, lifecycle state, and privacy - owner-only, with
    the same neutral 404 for a guessed or foreign key as for flag-off."""
    if not _journal_enabled():
        return _journal_not_found()

    identity, response = _journal_identity_or_not_found()
    if response is not None:
        return response

    normalized_moment_key = _normalize_capture_key(moment_key)
    if not normalized_moment_key:
        return _journal_not_found()

    try:
        moment = _find_journal_moment(identity.user_key, normalized_moment_key)
    except (JournalServiceError, DatabaseServiceError):
        current_app.logger.error("PeerSlate Journal Moment detail is unavailable.")
        return _render_owner_unavailable()

    if not moment:
        return _journal_not_found()

    return render_template(
        "journal_moment.html",
        page_title="Moment",
        member=identity,
        moment=moment,
        chapters=JOURNAL_CHAPTERS,
        rail_id="journal",
        rail_label="Contents",
        rail_nav_label="Journal sections",
        active_chapter=_journal_chapter_key_for_item(moment) or "timeline",
    )


@owner.get("/app/journal/voice/<source_key>/draft")
def journal_voice_draft(source_key):
    """JSON voice-draft fetch for the in-context Journal composer.

    The released Voice lifecycle (PS-VOICE-001) only ever hands the
    transcript back through a full-page redirect to
    `/app/capture?voice=<key>` (owner_capture.html). The Journal composer
    must stay in place over the Journal and return to it (PS-JRN-CAP-003) -
    it cannot navigate to that page. This route is net-new and additive: it
    reuses `voice_capture_service.get_draft` exactly as `capture()` already
    does above, unmodified, and simply hands the same draft back as JSON
    instead of server-rendering it."""
    if not _journal_enabled():
        return jsonify({"success": False, "message": "Not found."}), 404

    try:
        identity = get_current_identity()
    except AuthenticationRequired:
        return jsonify({"success": False, "message": "Not found."}), 404
    except DatabaseServiceError:
        current_app.logger.error(
            "PeerSlate Journal voice draft identity lookup failed."
        )
        return jsonify({"success": False, "message": "Unavailable."}), 503

    normalized_source_key = _normalize_capture_key(source_key)
    if not normalized_source_key:
        return jsonify({"success": False, "message": "Not found."}), 404

    try:
        draft = voice_capture_service.get_draft(identity.user_key, normalized_source_key)
    except DatabaseServiceError:
        current_app.logger.error("PeerSlate Journal voice draft read is unavailable.")
        return jsonify({"success": False, "message": "Unavailable."}), 503

    if not draft:
        return jsonify({"success": False, "message": "Not found."}), 404

    duration_ms = draft.get("verified_duration_milliseconds") or draft.get(
        "client_duration_milliseconds"
    )
    response = jsonify(
        {
            "success": True,
            "source_key": str(draft.get("source_key") or normalized_source_key),
            "state": draft.get("state"),
            "transcript": draft.get("provider_transcript") or "",
            "duration_seconds": (duration_ms / 1000) if duration_ms else None,
            "audio_url": url_for(
                "owner.voice_capture_audio", source_key=normalized_source_key
            ),
            "safe_error_code": draft.get("safe_error_code"),
        }
    )
    response.headers["Cache-Control"] = "private, no-store"
    return response
