"""Private Resume media chooser routes for MVP1 increment D.

REGISTERED, AND OFF.
``app.py`` registers this blueprint unconditionally. The gate is
``PEERSLATE_RESUME_MEDIA_ENABLED``, read with ``is True``. Off means a neutral
404 for both the JSON API and any media byte route.

Every route is owner-derived and application-controlled: the identity comes
from the server session, client owner/authority/publication fields are dropped
before use, writes require a same-origin request header, and every response is
private and no-store. There is no publication route here, and no public media
URL. Bytes only ever leave through an authorization that is checked before the
read and rechecked after it.
"""

from __future__ import annotations

from types import MappingProxyType

from flask import Blueprint, Response, current_app, jsonify, request

from identity import AuthenticationRequired, get_current_identity
from services.database_service import DatabaseServiceError
from services.resume_media_application import (
    CATALOG_PAGE_SIZE_DEFAULT,
    MAX_CATALOG_PAGE_SIZE,
    ResumeMediaApplicationService,
    ResumeMediaApplicationUnavailable,
    configured_resume_media_application,
)
from services.resume_media_service import (
    ResumeMediaConflict,
    ResumeMediaDenied,
    ResumeMediaError,
)


resume_media = Blueprint("resume_media", __name__)

PLANNED_RATE_LIMITS = MappingProxyType(
    {
        "resume_media.get_resume_media_workspace": "60 per minute",
        "resume_media.get_resume_media_library": "60 per minute",
        "resume_media.get_resume_media_photo_preview": "120 per minute",
        "resume_media.get_resume_media_library_thumbnail": "120 per minute",
        "resume_media.get_resume_media_placement_media": "120 per minute",
        "resume_media.get_resume_media_draft_placement_media": "120 per minute",
        "resume_media.post_resume_media_photo": "30 per hour",
        "resume_media.post_resume_media_photo_refresh": "60 per hour",
        "resume_media.post_resume_media_placement": "120 per hour",
        "resume_media.post_resume_media_placement_swap": "60 per hour",
        "resume_media.post_resume_media_command": "30 per hour",
    }
)

# Stable, content-free HTTP mapping. Nothing here echoes member data, a
# storage key, a provider locator, or another owner's existence.
_INVALID_CODES = frozenset(
    {
        "invalid-request",
        "invalid-slot",
        "invalid-source",
        "invalid-crop",
        "invalid-alt-text",
        "invalid-caption",
        "invalid-decorative",
        "invalid-limit",
        "invalid-cursor",
        "invalid-command",
        "invalid-receipt",
        "required",
        "unsupported-source",
        "source-too-large",
        "source-dimensions",
        "crop-not-finite",
        "crop-out-of-bounds",
    }
)
_UNAVAILABLE_CODES = frozenset(
    {
        "media-unavailable",
        "source-unavailable",
        "storage-unavailable",
        "readiness-unavailable",
        "upload-failed",
        "upload-recovery",
        "source-processing-failed",
        "catalog-unavailable",
    }
)
_CONFLICT_CODES = frozenset(
    {
        "source-limit",
        "catalog-changed",
        "cursor-mismatch",
    }
)


def _enabled() -> bool:
    return current_app.config.get("PEERSLATE_RESUME_MEDIA_ENABLED", False) is True


def _service() -> ResumeMediaApplicationService:
    return configured_resume_media_application(
        current_app.config.get("RESUME_MEDIA_SERVICE")
    )


@resume_media.before_request
def gate_and_protect_writes():
    if not _enabled():
        return jsonify({"success": False, "message": "Not found."}), 404
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


@resume_media.after_request
def private_no_store(response):
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@resume_media.errorhandler(DatabaseServiceError)
def handle_database_error(error):
    """Identity or storage reads that fail stay an honest, content-free 503."""

    return jsonify(
        {"success": False, "code": "unavailable", "message": "Resume media is unavailable."}
    ), 503


def _identity_or_not_found():
    try:
        return get_current_identity()
    except AuthenticationRequired:
        return None


def _owner_or_not_found():
    identity = _identity_or_not_found()
    if identity is None:
        return None
    return identity.user_key


def _json_body() -> dict:
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return {}
    return payload


def _failure(error: Exception):
    """Translate a stable media outcome into an HTTP status without leaking data."""

    if isinstance(error, ResumeMediaApplicationUnavailable):
        return jsonify(
            {"success": False, "code": "unavailable", "message": "Resume media is unavailable."}
        ), 503
    if isinstance(error, ResumeMediaDenied):
        return jsonify({"success": False, "message": "Not found."}), 404
    if isinstance(error, ResumeMediaConflict):
        code = error.code
        if code == "slot-not-allowed":
            return jsonify(
                {
                    "success": False,
                    "code": code,
                    "message": "Portrait is identity presentation, not a media slot.",
                }
            ), 409
        if code == "required":
            return jsonify(
                {
                    "success": False,
                    "code": code,
                    "message": "Choose a photo for each slot you want to add.",
                }
            ), 400
        return jsonify(
            {
                "success": False,
                "code": code,
                "error_code": code,
                "message": "That photo choice conflicts with your current private Resume.",
            }
        ), 409
    if isinstance(error, ResumeMediaError):
        code = error.code
        if code in _INVALID_CODES:
            status = 400
        elif code in _UNAVAILABLE_CODES:
            status = 503
        elif code in _CONFLICT_CODES:
            status = 409
        else:
            status = 400
        message = {
            400: "That media request was not valid.",
            409: "That media request conflicts with your current private Resume.",
            503: "Resume media is unavailable right now.",
        }[status]
        return jsonify({"success": False, "code": code, "message": message}), status
    raise error


def _media_response(opened, *, fallback_message="That media is not available."):
    if not opened:
        return jsonify({"success": False, "message": fallback_message}), 404
    response = Response(
        opened["stream"],
        mimetype=opened["content_type"],
        direct_passthrough=True,
    )
    response.headers["Content-Length"] = str(int(opened["byte_length"]))
    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    response.headers["Content-Disposition"] = "inline"
    return response


@resume_media.get("/api/resume-media/me/workspace")
def get_resume_media_workspace():
    owner = _owner_or_not_found()
    if owner is None:
        return jsonify({"success": False, "message": "Not found."}), 404
    try:
        payload = _service().workspace(owner_id=owner)
    except (ResumeMediaError, ResumeMediaApplicationUnavailable) as error:
        return _failure(error)
    return jsonify({"success": True, "publishes": False, **payload})


@resume_media.post("/api/resume-media/me/photos")
def post_resume_media_photo():
    owner = _owner_or_not_found()
    if owner is None:
        return jsonify({"success": False, "message": "Not found."}), 404
    # Only the declared file field is read. Extra multipart fields — including
    # client owner/authority fields — are ignored, never trusted, and are never
    # mutated on the parsed form.
    upload = request.files.get("photo")
    try:
        payload = _service().upload_photo(owner_id=owner, upload=upload)
    except (ResumeMediaError, ResumeMediaApplicationUnavailable) as error:
        return _failure(error)
    return jsonify({"success": True, **payload, "added_to_resume": False})


@resume_media.post("/api/resume-media/me/photos/<string:source_id>/refresh")
def post_resume_media_photo_refresh(source_id: str):
    owner = _owner_or_not_found()
    if owner is None:
        return jsonify({"success": False, "message": "Not found."}), 404
    try:
        payload = _service().refresh_photo(owner_id=owner, source_id=source_id)
    except (ResumeMediaError, ResumeMediaApplicationUnavailable) as error:
        return _failure(error)
    return jsonify({"success": True, **payload, "added_to_resume": False})


@resume_media.get("/api/resume-media/me/photos/<string:source_id>/preview")
def get_resume_media_photo_preview(source_id: str):
    owner = _owner_or_not_found()
    if owner is None:
        return jsonify({"success": False, "message": "Not found."}), 404
    try:
        opened = _service().open_photo_preview(owner_id=owner, source_id=source_id)
    except (ResumeMediaError, ResumeMediaApplicationUnavailable) as error:
        return _failure(error)
    return _media_response(opened)


@resume_media.get("/api/resume-media/me/library")
def get_resume_media_library():
    owner = _owner_or_not_found()
    if owner is None:
        return jsonify({"success": False, "message": "Not found."}), 404
    tags = request.args.getlist("tag")
    raw_limit = request.args.get("limit")
    try:
        limit = CATALOG_PAGE_SIZE_DEFAULT if raw_limit in (None, "") else int(raw_limit)
    except (TypeError, ValueError):
        return _failure(ResumeMediaError("invalid-limit"))
    try:
        page = _service().library(
            owner_id=owner,
            query=request.args.get("query"),
            category=request.args.get("category"),
            tags=tuple(tags),
            limit=min(limit, MAX_CATALOG_PAGE_SIZE),
            cursor=request.args.get("cursor"),
        )
    except (ResumeMediaError, ResumeMediaApplicationUnavailable) as error:
        return _failure(error)
    items = []
    for item in page["items"]:
        items.append(
            {
                **item,
                "thumbnail_slot": "story_banner",
                "thumbnail_url": (
                    f"/api/resume-media/me/library/{item['asset_id']}/"
                    f"{item['asset_version']}/thumbnail"
                ),
            }
        )
    return jsonify(
        {
            "success": True,
            "items": items,
            "next_cursor": page["next_cursor"],
            "total": page["total"],
            "page_size": page["page_size"],
            "catalog": page["catalog"],
        }
    )


@resume_media.get(
    "/api/resume-media/me/library/<string:asset_id>/<int:asset_version>/thumbnail"
)
def get_resume_media_library_thumbnail(asset_id: str, asset_version: int):
    owner = _owner_or_not_found()
    if owner is None:
        return jsonify({"success": False, "message": "Not found."}), 404
    try:
        opened = _service().open_library_thumbnail(
            owner_id=owner,
            asset_id=asset_id,
            asset_version=asset_version,
            slot=request.args.get("slot") or "story_banner",
        )
    except (ResumeMediaError, ResumeMediaApplicationUnavailable) as error:
        return _failure(error)
    return _media_response(opened)


@resume_media.post("/api/resume-media/me/placements")
def post_resume_media_placement():
    owner = _owner_or_not_found()
    if owner is None:
        return jsonify({"success": False, "message": "Not found."}), 404
    try:
        preview = _service().stage_placement(owner_id=owner, payload=_json_body())
    except (ResumeMediaError, ResumeMediaApplicationUnavailable) as error:
        return _failure(error)
    return jsonify(
        {
            "success": True,
            "preview": preview,
            "placement_preview_label": "Placement preview · Not added yet",
            "publishes": False,
        }
    )


@resume_media.get("/api/resume-media/me/placements/<string:slot>")
def get_resume_media_placement_preview(slot: str):
    owner = _owner_or_not_found()
    if owner is None:
        return jsonify({"success": False, "message": "Not found."}), 404
    try:
        preview = _service().preview_placement(owner_id=owner, slot=slot)
    except (ResumeMediaError, ResumeMediaApplicationUnavailable) as error:
        return _failure(error)
    return jsonify(
        {
            "success": True,
            "preview": preview,
            "placement_preview_label": "Placement preview · Not added yet",
            "publishes": False,
        }
    )


@resume_media.delete("/api/resume-media/me/placements/<string:slot>")
def delete_resume_media_placement(slot: str):
    owner = _owner_or_not_found()
    if owner is None:
        return jsonify({"success": False, "message": "Not found."}), 404
    try:
        removed = _service().clear_placement(owner_id=owner, slot=slot)
    except (ResumeMediaError, ResumeMediaApplicationUnavailable) as error:
        return _failure(error)
    return jsonify({"success": True, "removed": bool(removed), "publishes": False})


@resume_media.post("/api/resume-media/me/placement-swap")
def post_resume_media_placement_swap():
    owner = _owner_or_not_found()
    if owner is None:
        return jsonify({"success": False, "message": "Not found."}), 404
    try:
        payload = _service().swap_placements(owner_id=owner)
    except (ResumeMediaError, ResumeMediaApplicationUnavailable) as error:
        return _failure(error)
    return jsonify(
        {
            "success": True,
            "slots": payload["slots"],
            "placement_preview_label": "Placement preview · Not added yet",
            "publishes": False,
        }
    )


@resume_media.get("/api/resume-media/me/placements/<string:slot>/media")
def get_resume_media_placement_media(slot: str):
    owner = _owner_or_not_found()
    if owner is None:
        return jsonify({"success": False, "message": "Not found."}), 404
    try:
        opened = _service().open_placement_media(owner_id=owner, slot=slot)
    except (ResumeMediaError, ResumeMediaApplicationUnavailable) as error:
        return _failure(error)
    return _media_response(opened)


@resume_media.get("/api/resume-media/me/draft/placements/<string:slot>/media")
def get_resume_media_draft_placement_media(slot: str):
    """Private bytes for a placement already saved in this owner's draft."""

    owner = _owner_or_not_found()
    if owner is None:
        return jsonify({"success": False, "message": "Not found."}), 404
    try:
        opened = _service().open_draft_placement_media(owner_id=owner, slot=slot)
    except (ResumeMediaError, ResumeMediaApplicationUnavailable) as error:
        return _failure(error)
    return _media_response(opened)


@resume_media.post("/api/resume-media/me/commands")
def post_resume_media_command():
    owner = _owner_or_not_found()
    if owner is None:
        return jsonify({"success": False, "message": "Not found."}), 404
    body = _json_body()
    command = str(body.get("type") or body.get("command") or "")
    try:
        service = _service()
        if command == "add_media":
            result = service.add_media(owner_id=owner, payload=body)
        elif command == "keep_words_only":
            result = service.keep_words_only(owner_id=owner, payload=body)
        elif command == "review_media":
            result = service.review(owner_id=owner, payload=body)
        else:
            raise ResumeMediaError("invalid-command")
    except (ResumeMediaError, ResumeMediaApplicationUnavailable) as error:
        return _failure(error)
    # The command outcome above is authoritative. A failure to re-read the
    # workspace afterwards must not turn a committed command into an error the
    # member could mistake for "nothing happened": report the outcome and say
    # the refresh is unavailable so the client can retry the read instead of
    # re-issuing the command.
    try:
        workspace_payload = service.workspace(owner_id=owner)
        workspace_unavailable = False
    except (ResumeMediaError, ResumeMediaApplicationUnavailable, DatabaseServiceError):
        workspace_payload = None
        workspace_unavailable = True
    return jsonify(
        {
            "success": True,
            **result,
            "publishes": False,
            "workspace": workspace_payload,
            "workspace_unavailable": workspace_unavailable,
        }
    )
