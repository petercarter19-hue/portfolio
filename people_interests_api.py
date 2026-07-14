"""People & Interests living-board feed APIs (PS-FEAT-002).

Reads are public (the board is a public preview, like /api/slate-feed).
Writes require the server-side identity and the same same-origin
protections as the rest of the PeerSlate API — the browser never supplies
or overrides user_key. Storage is the fixture-backed feed service until
the PS-PLAT-008 stored procedures are approved (see SQL FIles/Migrations).
"""

from functools import wraps

from flask import Blueprint, jsonify, request

from identity import AuthenticationRequired, get_current_identity
from services.people_interests_feed import (
    COMMENT_BODY_MAX,
    CONTENT_TYPES,
    FeedNotFoundError,
    FeedValidationError,
    PAGE_LIMIT_DEFAULT,
    POST_BODY_MAX,
    people_interests_feed,
)


people_interests_api = Blueprint(
    "people_interests_api", __name__, url_prefix="/api/feed"
)


def require_identity(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        try:
            get_current_identity()
        except AuthenticationRequired as error:
            return jsonify({"success": False, "message": str(error)}), 401
        return view(*args, **kwargs)

    return wrapped


@people_interests_api.before_request
def protect_json_writes():
    # Same write protections as peerslate_api: a custom header (which forces
    # a CORS preflight cross-origin) plus Origin/Sec-Fetch-Site checks.
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

    fetch_site = request.headers.get("Sec-Fetch-Site")
    if fetch_site and fetch_site not in {"same-origin", "none"}:
        return jsonify(
            {"success": False, "message": "Cross-site writes are not allowed."}
        ), 403

    if request.content_length and not request.is_json:
        return jsonify(
            {"success": False, "message": "Write requests must use JSON."}
        ), 415

    return None


@people_interests_api.errorhandler(FeedValidationError)
def handle_validation_error(error):
    return jsonify({"success": False, "message": str(error)}), 400


@people_interests_api.errorhandler(FeedNotFoundError)
def handle_not_found(error):
    return jsonify({"success": False, "message": "Post not found."}), 404


def _json_body():
    body = request.get_json(silent=True)
    if body is None:
        return {}
    if not isinstance(body, dict):
        raise FeedValidationError("The JSON request body must be an object.")
    return body


def _optional_viewer_key():
    """The viewer's user_key when a trusted identity exists, else None.

    Reads stay public, but a signed-in (or local-dev) viewer gets their own
    reaction/save state echoed back.
    """
    try:
        return get_current_identity().user_key
    except AuthenticationRequired:
        return None


@people_interests_api.get("/people-interests")
def get_people_interests_feed():
    cursor = request.args.get("cursor") or None
    try:
        limit = int(request.args.get("limit", str(PAGE_LIMIT_DEFAULT)))
    except ValueError as error:
        raise FeedValidationError("limit must be a whole number.") from error
    page = people_interests_feed.get_page(
        cursor=cursor, limit=limit, user_key=_optional_viewer_key()
    )
    return jsonify({"success": True, **page})


@people_interests_api.get("/posts/<string:post_id>")
def get_post_detail(post_id):
    detail = people_interests_feed.get_post_detail(
        post_id[:64], user_key=_optional_viewer_key()
    )
    return jsonify({"success": True, "post": detail})


@people_interests_api.post("/posts")
@require_identity
def create_post():
    identity = get_current_identity()
    body = _json_body()
    text = body.get("body")
    if text is not None and not isinstance(text, str):
        raise FeedValidationError("body must be text.")
    content_type = body.get("content_type")
    if not isinstance(content_type, str) or content_type not in CONTENT_TYPES:
        raise FeedValidationError("content_type has an unsupported value.")
    post = people_interests_feed.create_post(
        identity.user_key,
        {"display_name": identity.display_name},
        text,
        content_type,
    )
    return jsonify({"success": True, "post": post}), 201


@people_interests_api.post("/posts/<string:post_id>/comments")
@require_identity
def add_comment(post_id):
    identity = get_current_identity()
    body = _json_body()
    text = body.get("body")
    if text is not None and not isinstance(text, str):
        raise FeedValidationError("body must be text.")
    comment = people_interests_feed.add_comment(
        identity.user_key,
        {"display_name": identity.display_name},
        post_id[:64],
        text,
    )
    return jsonify({"success": True, "comment": comment}), 201


@people_interests_api.post("/posts/<string:post_id>/reactions")
@require_identity
def add_reaction(post_id):
    identity = get_current_identity()
    body = _json_body()
    reaction_type = body.get("reaction_type")
    if not isinstance(reaction_type, str):
        raise FeedValidationError("reaction_type must be text.")
    result = people_interests_feed.add_reaction(
        identity.user_key, post_id[:64], reaction_type
    )
    return jsonify({"success": True, **result})


@people_interests_api.delete("/posts/<string:post_id>/reactions/<string:reaction_type>")
@require_identity
def remove_reaction(post_id, reaction_type):
    identity = get_current_identity()
    result = people_interests_feed.remove_reaction(
        identity.user_key, post_id[:64], reaction_type[:32]
    )
    return jsonify({"success": True, **result})


@people_interests_api.post("/posts/<string:post_id>/save")
@require_identity
def toggle_save(post_id):
    identity = get_current_identity()
    result = people_interests_feed.toggle_save(identity.user_key, post_id[:64])
    return jsonify({"success": True, **result})
