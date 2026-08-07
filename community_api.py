"""Public reads and site-owner commands for the Community public pilot."""

from __future__ import annotations

import re
import unicodedata
from urllib.parse import quote

from flask import Blueprint, Response, current_app, jsonify, request
from flask_limiter.errors import RateLimitExceeded
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.http import dump_options_header

from identity import AuthenticationRequired, get_current_identity, get_optional_identity
from owner_authorization import is_owner
from services.community_command_service import community_command_service
from services.community_contracts import (
    CommunityConflictError,
    CommunityNotFoundError,
    CommunityUnavailableError,
    CommunityValidationError,
)
from services.community_feed_service import community_feed_service
from services.community_demo_feed import (
    demo_feed_page,
    demo_post_detail,
    demo_search,
    demo_selected_contribution,
    demo_shelf_page,
)
from services.community_media_service import community_media_service
from services.community_voice_service import (
    CommunityVoiceError,
    community_voice_service,
)
from services.database_service import DatabaseServiceError
from services.voice_capture_service import MAX_VOICE_BYTES


community_api = Blueprint("community_api", __name__, url_prefix="/api/v1/community")

VOICE_TRANSCRIPTION_ENDPOINT = "community_api.transcribe_voice"
VOICE_MULTIPART_LIMIT = MAX_VOICE_BYTES + 64 * 1024


def _json_body():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise CommunityValidationError("The request body must be a JSON object.")
    return body


def _owner_identity():
    try:
        identity = get_current_identity()
    except AuthenticationRequired:
        return None, (jsonify(success=False, message="Sign in is required."), 401)
    if not is_owner(identity):
        return None, (jsonify(success=False, message="This action is not available."), 403)
    return identity, None


def _voice_failure(status, code, message, *, retryable):
    return jsonify(
        success=False, code=code, message=message, retryable=retryable
    ), status


def _voice_owner_identity():
    try:
        identity = get_current_identity()
    except AuthenticationRequired:
        return None, _voice_failure(
            401, "authentication_required", "Sign in is required.", retryable=False
        )
    if not is_owner(identity):
        return None, _voice_failure(
            403,
            "action_unavailable",
            "This action is not available.",
            retryable=False,
        )
    return identity, None


def _idempotency_header():
    return request.headers.get("Idempotency-Key")


@community_api.before_request
def protect_public_pilot():
    if not current_app.config.get("PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED", False):
        if request.endpoint == VOICE_TRANSCRIPTION_ENDPOINT:
            return _voice_failure(404, "not_found", "Not found.", retryable=False)
        return jsonify(success=False, message="Not found."), 404
    if request.endpoint == VOICE_TRANSCRIPTION_ENDPOINT:
        request.max_content_length = VOICE_MULTIPART_LIMIT
    if request.endpoint == "community_api.upload_attachment":
        # Flask allows a route-specific override. Keep the application's
        # existing 2 MiB ceiling intact for every unrelated endpoint.
        request.max_content_length = 10 * 1024 * 1024 + 64 * 1024
    if request.method not in {"POST", "PATCH", "PUT", "DELETE"}:
        return None
    if request.headers.get("X-PeerSlate-Request") != "same-origin":
        if request.endpoint == VOICE_TRANSCRIPTION_ENDPOINT:
            return _voice_failure(
                403,
                "same_origin_required",
                "A same-origin request header is required.",
                retryable=False,
            )
        return jsonify(success=False, message="A same-origin request header is required."), 403
    origin = request.headers.get("Origin")
    if origin and origin.rstrip("/") != request.host_url.rstrip("/"):
        if request.endpoint == VOICE_TRANSCRIPTION_ENDPOINT:
            return _voice_failure(
                403,
                "same_origin_required",
                "Cross-origin writes are not allowed.",
                retryable=False,
            )
        return jsonify(success=False, message="Cross-origin writes are not allowed."), 403
    fetch_site = request.headers.get("Sec-Fetch-Site")
    if fetch_site and fetch_site not in {"same-origin", "none"}:
        if request.endpoint == VOICE_TRANSCRIPTION_ENDPOINT:
            return _voice_failure(
                403,
                "same_origin_required",
                "Cross-site writes are not allowed.",
                retryable=False,
            )
        return jsonify(success=False, message="Cross-site writes are not allowed."), 403
    if request.endpoint not in {
        "community_api.upload_attachment", VOICE_TRANSCRIPTION_ENDPOINT
    } and not request.is_json:
        return jsonify(success=False, message="Write requests must use JSON."), 415
    return None


@community_api.after_request
def secure_community_response(response):
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response


@community_api.errorhandler(CommunityValidationError)
def validation_error(error):
    return jsonify(success=False, message=str(error), retryable=False), 422


@community_api.errorhandler(CommunityConflictError)
def conflict_error(error):
    return jsonify(success=False, message=str(error)), 409


@community_api.errorhandler(CommunityNotFoundError)
def missing_error(error):
    return jsonify(success=False, message="Not found."), 404


@community_api.errorhandler(CommunityUnavailableError)
def unavailable_error(error):
    current_app.logger.error("Community dependency request failed.")
    return jsonify(success=False, message=str(error)), 503


@community_api.errorhandler(DatabaseServiceError)
def identity_database_error(error):
    current_app.logger.error("Community identity resolution failed.")
    return jsonify(success=False, message="Community unavailable."), 503


@community_api.errorhandler(RequestEntityTooLarge)
def request_too_large(error):
    if request.endpoint == VOICE_TRANSCRIPTION_ENDPOINT:
        return _voice_failure(
            413,
            "recording_too_large",
            "This recording is too large. Record a shorter clip.",
            retryable=False,
        )
    return jsonify(success=False, message="Request is too large."), 413


@community_api.errorhandler(RateLimitExceeded)
def community_rate_limited(error):
    if request.endpoint == VOICE_TRANSCRIPTION_ENDPOINT:
        return _voice_failure(
            429,
            "voice_rate_limited",
            "Voice transcription is temporarily busy. Try again later.",
            retryable=True,
        )
    return jsonify(success=False, message="Too many requests."), 429


@community_api.get("/feed")
def feed():
    identity = get_optional_identity()
    cursor = request.args.get("cursor")
    page = community_feed_service.feed_page(
        cursor,
        page_size=12,
        viewer_user_key=(
            identity.user_key if identity and is_owner(identity) else None
        ),
    )
    if not cursor and not page.get("items"):
        page = demo_feed_page()
    return jsonify(success=True, **page)


@community_api.get("/posts/<string:post_key>")
def post_detail(post_key):
    identity = get_optional_identity()
    try:
        detail = community_feed_service.post_detail(
            post_key,
            viewer_user_key=identity.user_key if identity and is_owner(identity) else None,
            contribution_cursor=request.args.get("cursor"),
        )
    except CommunityNotFoundError:
        detail = demo_post_detail(post_key)
    return jsonify(success=True, post=detail)


@community_api.get("/posts/<string:post_key>/shelf")
def contribution_shelf(post_key):
    identity = get_optional_identity()
    cursor = request.args.get("cursor")
    try:
        page = community_feed_service.shelf_page(
            post_key,
            cursor,
            viewer_user_key=(
                identity.user_key if identity and is_owner(identity) else None
            ),
        )
    except CommunityNotFoundError:
        page = demo_shelf_page(post_key, cursor)
    return jsonify(success=True, **page)


@community_api.get(
    "/posts/<string:post_key>/contributions/<string:contribution_key>"
)
def selected_contribution(post_key, contribution_key):
    identity = get_optional_identity()
    try:
        detail = community_feed_service.selected_contribution(
            post_key,
            contribution_key,
            viewer_user_key=(
                identity.user_key if identity and is_owner(identity) else None
            ),
        )
    except CommunityNotFoundError:
        detail = demo_selected_contribution(post_key, contribution_key)
    return jsonify(success=True, **detail)


@community_api.post("/search")
def search():
    identity = get_optional_identity()
    query = _json_body().get("query")
    viewer_user_key = (
        identity.user_key if identity and is_owner(identity) else None
    )
    items = community_feed_service.search(
        query,
        viewer_user_key=viewer_user_key,
    )
    demo_mode = False
    if not items:
        first_page = community_feed_service.feed_page(
            None, page_size=1, viewer_user_key=viewer_user_key
        )
        if not first_page.get("items"):
            demo_mode = True
            items = demo_search(query)
    return jsonify(
        success=True,
        items=items,
        demo_mode=demo_mode,
    )


@community_api.post("/voice/transcriptions")
def transcribe_voice():
    """Return one reviewable transcript without creating durable state."""
    identity, failure = _voice_owner_identity()
    if failure:
        return failure
    if request.mimetype != "multipart/form-data":
        return _voice_failure(
            415,
            "multipart_required",
            "Voice transcription requires a recording form upload.",
            retryable=False,
        )
    if request.content_length and request.content_length > VOICE_MULTIPART_LIMIT:
        return _voice_failure(
            413,
            "recording_too_large",
            "This recording is too large. Record a shorter clip.",
            retryable=False,
        )
    form_fields = set(request.form)
    file_fields = set(request.files)
    if (
        form_fields - {"duration_seconds", "composer_context"}
        or file_fields - {"audio"}
        or len(request.form.getlist("duration_seconds")) > 1
        or len(request.form.getlist("composer_context")) > 1
    ):
        return _voice_failure(
            422,
            "invalid_context",
            "This Voice request has unsupported fields.",
            retryable=False,
        )
    if "composer_context" not in form_fields:
        return _voice_failure(
            422,
            "invalid_context",
            "Choose an available Voice composer context.",
            retryable=False,
        )
    if "duration_seconds" not in form_fields:
        return _voice_failure(
            422,
            "invalid_duration",
            "The recording duration is invalid.",
            retryable=False,
        )
    audio_parts = request.files.getlist("audio")
    if not audio_parts:
        return _voice_failure(
            422,
            "recording_required",
            "Choose a recording before transcribing.",
            retryable=False,
        )
    if len(audio_parts) != 1:
        return _voice_failure(
            422,
            "invalid_context",
            "This Voice request has unsupported fields.",
            retryable=False,
        )
    try:
        proposal = community_voice_service.transcribe(
            request.files["audio"],
            request.form["duration_seconds"],
            request.form["composer_context"],
        )
    except CommunityVoiceError as error:
        details = {
            "invalid-context": ("invalid_context", "Choose an available Voice composer context."),
            "recording-required": ("recording_required", "Choose a recording before transcribing."),
            "invalid-duration": ("invalid_duration", "The recording duration is invalid."),
            "recording-too-long": ("recording_too_long", "Recordings are limited to three minutes."),
            "recording-too-large": ("recording_too_large", "This recording is too large. Record a shorter clip."),
            "unsupported-recording": ("unsupported_recording", "This recording format is not supported."),
            "transcript-empty": ("transcript_empty", "No reviewable speech was detected."),
            "transcript-too-long": ("transcript_too_long", "Speech returned a transcript that is too long for this comment. Record a shorter clip or keep typing."),
            "transcription-unavailable": ("transcription_unavailable", "Voice transcription is unavailable. You can keep typing and try again later."),
        }
        code, message = details.get(error.code, details["transcription-unavailable"])
        status = {
            "transcription_unavailable": 503,
            "recording_too_large": 413,
        }.get(code, 422)
        if status == 503:
            current_app.logger.warning("Community Voice transcription unavailable.")
        return _voice_failure(
            status, code, message, retryable=status == 503
        )
    return jsonify(success=True, proposal=proposal)


@community_api.post("/posts")
def publish_post():
    identity, failure = _owner_identity()
    if failure:
        return failure
    result = community_command_service.publish_post(identity.user_key, _json_body(), _idempotency_header())
    return jsonify(success=True, result=result), 201


@community_api.patch("/posts/<string:post_key>")
def edit_post(post_key):
    identity, failure = _owner_identity()
    if failure:
        return failure
    body = _json_body()
    expected = body.pop("expected_revision", None)
    result = community_command_service.edit_post(identity.user_key, post_key, body, expected)
    return jsonify(success=True, result=result)


@community_api.delete("/posts/<string:post_key>")
def delete_post(post_key):
    identity, failure = _owner_identity()
    if failure:
        return failure
    result = community_command_service.delete_post(
        identity.user_key, post_key, _json_body().get("expected_revision")
    )
    return jsonify(success=True, result=result)


@community_api.post("/posts/<string:post_key>/contributions")
def add_contribution(post_key):
    identity, failure = _owner_identity()
    if failure:
        return failure
    result = community_command_service.add_contribution(
        identity.user_key, post_key, _json_body(), _idempotency_header()
    )
    return jsonify(success=True, result=result), 201


@community_api.patch("/contributions/<string:contribution_key>")
def edit_contribution(contribution_key):
    identity, failure = _owner_identity()
    if failure:
        return failure
    body = _json_body()
    result = community_command_service.edit_contribution(
        identity.user_key,
        contribution_key,
        body.get("body"),
        body.get("expected_revision"),
    )
    return jsonify(success=True, result=result)


@community_api.delete("/contributions/<string:contribution_key>")
def delete_contribution(contribution_key):
    identity, failure = _owner_identity()
    if failure:
        return failure
    result = community_command_service.delete_contribution(
        identity.user_key, contribution_key, _json_body().get("expected_revision")
    )
    return jsonify(success=True, result=result)


@community_api.put("/posts/<string:post_key>/response")
def set_response(post_key):
    identity, failure = _owner_identity()
    if failure:
        return failure
    result = community_command_service.set_response(
        identity.user_key, post_key, _json_body().get("intention")
    )
    return jsonify(success=True, result=result)


@community_api.delete("/posts/<string:post_key>/response")
def remove_response(post_key):
    identity, failure = _owner_identity()
    if failure:
        return failure
    result = community_command_service.remove_response(identity.user_key, post_key)
    return jsonify(success=True, result=result)


@community_api.put("/posts/<string:post_key>/save")
def save_post(post_key):
    identity, failure = _owner_identity()
    if failure:
        return failure
    result = community_command_service.set_save(identity.user_key, post_key, True)
    return jsonify(success=True, result=result)


@community_api.delete("/posts/<string:post_key>/save")
def unsave_post(post_key):
    identity, failure = _owner_identity()
    if failure:
        return failure
    result = community_command_service.set_save(identity.user_key, post_key, False)
    return jsonify(success=True, result=result)


@community_api.put("/contributions/<string:contribution_key>/save")
def save_contribution(contribution_key):
    identity, failure = _owner_identity()
    if failure:
        return failure
    result = community_command_service.set_contribution_save(
        identity.user_key, contribution_key, True
    )
    return jsonify(success=True, result=result)


@community_api.delete("/contributions/<string:contribution_key>/save")
def unsave_contribution(contribution_key):
    identity, failure = _owner_identity()
    if failure:
        return failure
    result = community_command_service.set_contribution_save(
        identity.user_key, contribution_key, False
    )
    return jsonify(success=True, result=result)


@community_api.post("/attachments")
def upload_attachment():
    identity, failure = _owner_identity()
    if failure:
        return failure
    if request.content_length and request.content_length > 10 * 1024 * 1024 + 64 * 1024:
        raise CommunityValidationError("Attachments are limited to 10 MiB.")
    result = community_media_service.reserve_and_upload(identity.user_key, request.files.get("file"))
    return jsonify(success=True, attachment=result), 202


@community_api.post("/attachments/<string:media_key>/status")
def attachment_status(media_key):
    identity, failure = _owner_identity()
    if failure:
        return failure
    result = community_media_service.reconcile(identity.user_key, media_key)
    return jsonify(success=True, attachment=result)


@community_api.delete("/attachments/<string:media_key>")
def delete_attachment(media_key):
    identity, failure = _owner_identity()
    if failure:
        return failure
    community_media_service.remove(identity.user_key, media_key)
    return jsonify(success=True)


def _attachment_response(media_key, *, preview):
    item = community_media_service.public_file(media_key, preview=preview)
    response = Response(
        item["data"],
        status=200,
        mimetype=item["content_type"],
    )
    response.content_length = len(item["data"])
    display_name = str(item["display_name"])
    ascii_name = unicodedata.normalize("NFKD", display_name).encode(
        "ascii", "ignore"
    ).decode("ascii")
    ascii_name = re.sub(r"[^A-Za-z0-9._ -]", "", ascii_name).strip(" .")
    extension = display_name.rsplit(".", 1)[-1].lower()
    if not ascii_name or (
        extension in {"jpg", "png", "pdf", "xlsx"} and "." not in ascii_name
    ):
        ascii_name = (
            f"attachment.{extension}"
            if extension in {"jpg", "png", "pdf", "xlsx"}
            else "attachment"
        )
    disposition = dump_options_header(
        "inline" if item["inline"] else "attachment",
        {"filename": ascii_name[:180]},
    )
    response.headers["Content-Disposition"] = (
        disposition
        + "; filename*=UTF-8''"
        + quote(display_name, safe="!#$&+-.^_`|~")
    )
    return response


@community_api.get("/attachments/<string:media_key>/preview")
def preview_attachment(media_key):
    return _attachment_response(media_key, preview=True)


@community_api.get("/attachments/<string:media_key>/download")
def download_attachment(media_key):
    return _attachment_response(media_key, preview=False)
