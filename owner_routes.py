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
    """Override the smaller global form limit only for the Voice upload route."""
    if request.endpoint == "owner.upload_voice_capture":
        # Multipart framing adds a small amount beyond the enforced 20 MB file cap.
        request.max_content_length = MAX_VOICE_BYTES + (64 * 1024)


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
        voice_key = request.args.get("voice")
        if voice_key:
            normalized_voice_key = _normalize_capture_key(voice_key)
            if not normalized_voice_key:
                return "Voice draft not found.", 404
            voice_draft = voice_capture_service.get_draft(
                identity.user_key, normalized_voice_key
            )
            if not voice_draft:
                return "Voice draft not found.", 404
    except AuthenticationRequired:
        return redirect(url_for("auth.sign_in", return_to="/app/capture"))
    except DatabaseServiceError:
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
        max_body_length=MAX_CAPTURE_BODY_LENGTH,
        max_correction_note_length=MAX_CORRECTION_NOTE_LENGTH,
        max_voice_bytes=MAX_VOICE_BYTES,
        max_voice_duration_seconds=MAX_VOICE_DURATION_SECONDS,
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
        status = 503 if error.code in {"upload-failed", "transcription-failed"} else 400
        payload = {"error": error.code}
        if error.source_key:
            payload["state"] = "failed"
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
        result = voice_capture_service.delete_capture(
            identity.user_key,
            normalized_capture_key,
            expected_row_version,
        )
    except (DatabaseServiceError, VoiceCaptureError):
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
    voice_source = (
        dict(auxiliary_rows[0])
        if auxiliary_rows and "source_key" in auxiliary_rows[0]
        else None
    )
    schema_version = 2 if capture.get("capture_type") == "voice" else 1
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
