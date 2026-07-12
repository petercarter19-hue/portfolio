"""Authenticated PeerSlate JSON APIs backed by stored procedures."""

import json
from functools import wraps

from flask import Blueprint, current_app, jsonify, request

from identity import AuthenticationRequired, get_current_identity
from services.database_service import DatabaseServiceError, database_service


peerslate_api = Blueprint("peerslate_api", __name__, url_prefix="/api")

DASHBOARD_SECTIONS = (
    "user_summary",
    "today_break_feed",
    "today_poll_options",
    "recent_badges",
    "achievement_progress",
    "saved_boards",
    "slate_spaces",
    "challenge_progress",
)


class ApiValidationError(ValueError):
    """Raised when browser-provided API input is invalid."""


def require_identity(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        try:
            get_current_identity()
        except AuthenticationRequired as error:
            return jsonify({"success": False, "message": str(error)}), 401
        return view(*args, **kwargs)

    return wrapped


@peerslate_api.before_request
def protect_json_writes():
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


@peerslate_api.errorhandler(ApiValidationError)
def handle_validation_error(error):
    return jsonify({"success": False, "message": str(error)}), 400


@peerslate_api.errorhandler(DatabaseServiceError)
def handle_database_error(error):
    current_app.logger.error("PeerSlate database API request failed.")
    return jsonify(
        {
            "success": False,
            "message": "PeerSlate could not complete the database request.",
        }
    ), 503


def _json_body():
    body = request.get_json(silent=True)
    if body is None:
        return {}
    if not isinstance(body, dict):
        raise ApiValidationError("The JSON request body must be an object.")
    return body


def _string(body, name, *, required=False, max_length=500, choices=None):
    value = body.get(name)
    if value is None:
        if required:
            raise ApiValidationError(f"{name} is required.")
        return None
    if not isinstance(value, str):
        raise ApiValidationError(f"{name} must be text.")
    value = value.strip()
    if required and not value:
        raise ApiValidationError(f"{name} is required.")
    if len(value) > max_length:
        raise ApiValidationError(f"{name} is too long.")
    if choices and value not in choices:
        raise ApiValidationError(f"{name} has an unsupported value.")
    return value or None


def _integer(body, name, *, required=False, minimum=None, maximum=None):
    value = body.get(name)
    if value is None:
        if required:
            raise ApiValidationError(f"{name} is required.")
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ApiValidationError(f"{name} must be a whole number.")
    if minimum is not None and value < minimum:
        raise ApiValidationError(f"{name} is below the allowed minimum.")
    if maximum is not None and value > maximum:
        raise ApiValidationError(f"{name} is above the allowed maximum.")
    return value


def _result_payload(rows, key="items"):
    return jsonify({"success": True, key: rows, "count": len(rows)})


@peerslate_api.get("/dashboard")
@require_identity
def get_dashboard():
    identity = get_current_identity()
    result_sets = database_service.execute_procedure(
        "usp_GetPeerSlateUserDashboard", [("@UserKey", identity.user_key)]
    )
    dashboard = database_service.name_result_sets(result_sets, DASHBOARD_SECTIONS)
    return jsonify({"success": True, "dashboard": dashboard})


@peerslate_api.get("/feed/break")
@require_identity
def get_break_feed():
    identity = get_current_identity()
    rows = database_service.first_result(
        "usp_GetTodayBreakFeedForUser", [("@UserKey", identity.user_key)]
    )
    return _result_payload(rows, "cards")


@peerslate_api.post("/feed/interactions")
@require_identity
def record_feed_interaction():
    identity = get_current_identity()
    body = _json_body()
    metadata = body.get("metadata")
    if metadata is not None and not isinstance(metadata, (dict, list)):
        raise ApiValidationError("metadata must be an object or list.")
    rows = database_service.last_result(
        "usp_RecordFeedInteraction",
        [
            ("@UserKey", identity.user_key),
            ("@InteractionType", _string(body, "interaction_type", required=True, max_length=100)),
            ("@FeedName", _string(body, "feed_name", max_length=50) or "Break"),
            ("@CardType", _string(body, "card_type", max_length=50)),
            ("@CardPosition", _integer(body, "card_position", minimum=1)),
            ("@ContentItemId", _integer(body, "content_item_id", minimum=1)),
            ("@MetadataJson", json.dumps(metadata) if metadata is not None else None),
            ("@EvaluateAchievements", 1),
        ],
    )
    return _result_payload(rows, "interactions")


@peerslate_api.get("/saved-boards")
@require_identity
def get_saved_board_contents():
    identity = get_current_identity()
    board_name = request.args.get("board_name")
    if board_name is not None:
        board_name = board_name.strip()[:150] or None
    rows = database_service.first_result(
        "usp_GetUserBoardContents",
        [("@UserKey", identity.user_key), ("@BoardName", board_name)],
    )
    return _result_payload(rows, "saved_items")


@peerslate_api.post("/saved-boards/<string:board_name>/items/<int:content_item_id>")
@require_identity
def save_content_to_board(board_name, content_item_id):
    identity = get_current_identity()
    body = _json_body()
    rows = database_service.last_result(
        "usp_SaveContentToBoard",
        [
            ("@UserKey", identity.user_key),
            ("@BoardName", board_name[:150]),
            ("@ContentItemId", content_item_id),
            ("@Note", _string(body, "note", max_length=500)),
        ],
    )
    return _result_payload(rows, "saved_items")


@peerslate_api.delete("/saved-boards/<string:board_name>/items/<int:content_item_id>")
@require_identity
def unsave_content_from_board(board_name, content_item_id):
    identity = get_current_identity()
    rows = database_service.last_result(
        "usp_UnsaveContentFromBoard",
        [
            ("@UserKey", identity.user_key),
            ("@BoardName", board_name[:150]),
            ("@ContentItemId", content_item_id),
        ],
    )
    return _result_payload(rows, "results")


@peerslate_api.get("/polls/today/options")
@require_identity
def get_today_poll_options():
    rows = database_service.first_result("usp_GetTodayBreakPollOptions")
    return _result_payload(rows, "options")


@peerslate_api.post("/polls/<int:poll_content_item_id>/votes")
@require_identity
def submit_poll_vote(poll_content_item_id):
    identity = get_current_identity()
    body = _json_body()
    database_service.execute_procedure(
        "usp_SubmitPollVote",
        [
            ("@PollContentItemId", poll_content_item_id),
            ("@OptionPosition", _integer(body, "option_position", required=True, minimum=1)),
            ("@VoterKey", identity.user_key),
        ],
    )
    return jsonify({"success": True, "message": "Vote recorded."})


@peerslate_api.get("/challenges")
@require_identity
def get_challenges():
    identity = get_current_identity()
    progress = database_service.first_row(
        "usp_GetUserChallengeProgress", [("@UserKey", identity.user_key)]
    ) or {}
    history = database_service.first_result(
        "usp_GetUserChallengeHistory", [("@UserKey", identity.user_key)]
    )
    return jsonify({"success": True, "progress": progress, "history": history})


@peerslate_api.post("/challenges/<int:content_item_id>/complete")
@require_identity
def complete_challenge(content_item_id):
    identity = get_current_identity()
    body = _json_body()
    rows = database_service.last_result(
        "usp_CompleteChallenge",
        [
            ("@UserKey", identity.user_key),
            ("@ContentItemId", content_item_id),
            ("@Note", _string(body, "note", max_length=500)),
        ],
    )
    return _result_payload(rows, "completions")


@peerslate_api.get("/journal/today")
@require_identity
def get_today_journal():
    identity = get_current_identity()
    prompt = database_service.first_row(
        "usp_GetTodayJournalPromptForUser", [("@UserKey", identity.user_key)]
    )
    return jsonify({"success": True, "journal": prompt})


@peerslate_api.get("/journal/history")
@require_identity
def get_journal_history():
    identity = get_current_identity()
    try:
        days_back = int(request.args.get("days", "30"))
    except ValueError as error:
        raise ApiValidationError("days must be a whole number.") from error
    if days_back < 1 or days_back > 365:
        raise ApiValidationError("days must be between 1 and 365.")
    rows = database_service.first_result(
        "usp_GetUserJournalHistory",
        [("@UserKey", identity.user_key), ("@DaysBack", days_back)],
    )
    return _result_payload(rows, "entries")


@peerslate_api.post("/journal/responses")
@require_identity
def save_journal_response():
    identity = get_current_identity()
    body = _json_body()
    rows = database_service.last_result(
        "usp_SaveJournalResponse",
        [
            ("@UserKey", identity.user_key),
            ("@ContentItemId", _integer(body, "content_item_id", minimum=1)),
            ("@ResponseText", _string(body, "response_text", required=True, max_length=10000)),
            ("@ReflectionMood", _string(body, "reflection_mood", max_length=100)),
            ("@Visibility", _string(body, "visibility", max_length=50, choices={"private", "published"}) or "private"),
        ],
    )
    return _result_payload(rows, "entries")


@peerslate_api.get("/slate-spaces/<string:space_name>")
@require_identity
def get_slate_space(space_name):
    identity = get_current_identity()
    try:
        result_sets = database_service.execute_procedure(
            "usp_GetSlateSpaceForUser",
            [
                ("@UserKey", identity.user_key),
                ("@SpaceName", space_name[:150]),
                ("@SlateSpaceId", None),
            ],
        )
    except DatabaseServiceError as error:
        cause_message = str(error.__cause__ or "")
        if "Slate Space not found for this user" not in cause_message:
            raise
        result_sets = [[], [], []]

    space = database_service.name_result_sets(result_sets, ("space", "items", "links"))
    return jsonify({"success": True, "slate_space": space})


@peerslate_api.post("/slate-items")
@require_identity
def add_slate_item():
    identity = get_current_identity()
    body = _json_body()
    rows = database_service.last_result(
        "usp_AddSlateItem",
        [
            ("@UserKey", identity.user_key),
            ("@SpaceName", _string(body, "space_name", required=True, max_length=150)),
            ("@SpaceType", _string(body, "space_type", required=True, max_length=100)),
            ("@ItemType", _string(body, "item_type", required=True, max_length=100)),
            ("@Title", _string(body, "title", required=True, max_length=200)),
            ("@Body", _string(body, "body", max_length=10000)),
            ("@Category", _string(body, "category", max_length=100)),
            ("@TargetDate", _string(body, "target_date", max_length=10)),
            ("@SourceContentItemId", _integer(body, "source_content_item_id", minimum=1)),
        ],
    )
    return _result_payload(rows, "items"), 201


@peerslate_api.patch("/slate-items/<int:slate_item_id>")
@require_identity
def update_slate_item(slate_item_id):
    identity = get_current_identity()
    body = _json_body()
    rows = database_service.last_result(
        "usp_UpdateSlateItem",
        [
            ("@UserKey", identity.user_key),
            ("@SlateItemId", slate_item_id),
            ("@Title", _string(body, "title", max_length=200)),
            ("@Body", _string(body, "body", max_length=10000)),
            ("@Category", _string(body, "category", max_length=100)),
            ("@Status", _string(body, "status", max_length=50)),
            ("@Priority", _string(body, "priority", max_length=50)),
            ("@ProgressPercent", _integer(body, "progress_percent", minimum=0, maximum=100)),
            ("@TargetDate", _string(body, "target_date", max_length=10)),
            ("@EvidenceUrl", _string(body, "evidence_url", max_length=500)),
            ("@XPosition", _integer(body, "x_position")),
            ("@YPosition", _integer(body, "y_position")),
            ("@ColorLabel", _string(body, "color_label", max_length=50)),
            ("@UpdateNote", _string(body, "update_note", max_length=500)),
        ],
    )
    return _result_payload(rows, "items")


@peerslate_api.post("/slate-items/<int:from_item_id>/links")
@require_identity
def link_slate_items(from_item_id):
    identity = get_current_identity()
    body = _json_body()
    rows = database_service.last_result(
        "usp_LinkSlateItems",
        [
            ("@UserKey", identity.user_key),
            ("@FromSlateItemId", from_item_id),
            ("@ToSlateItemId", _integer(body, "to_item_id", required=True, minimum=1)),
            ("@LinkType", _string(body, "link_type", max_length=100) or "related"),
            ("@Label", _string(body, "label", max_length=150)),
        ],
    )
    return _result_payload(rows, "links")


@peerslate_api.delete("/slate-items/<int:from_item_id>/links/<int:to_item_id>")
@require_identity
def unlink_slate_items(from_item_id, to_item_id):
    identity = get_current_identity()
    link_type = (request.args.get("type") or "related")[:100]
    rows = database_service.last_result(
        "usp_UnlinkSlateItems",
        [
            ("@UserKey", identity.user_key),
            ("@FromSlateItemId", from_item_id),
            ("@ToSlateItemId", to_item_id),
            ("@LinkType", link_type),
        ],
    )
    return _result_payload(rows, "results")


def _change_archive_state(slate_item_id, procedure_name, note_parameter):
    identity = get_current_identity()
    body = _json_body()
    rows = database_service.last_result(
        procedure_name,
        [
            ("@UserKey", identity.user_key),
            ("@SlateItemId", slate_item_id),
            (note_parameter, _string(body, "note", max_length=500)),
        ],
    )
    return _result_payload(rows, "items")


@peerslate_api.post("/slate-items/<int:slate_item_id>/archive")
@require_identity
def archive_slate_item(slate_item_id):
    return _change_archive_state(slate_item_id, "usp_ArchiveSlateItem", "@ArchiveNote")


@peerslate_api.post("/slate-items/<int:slate_item_id>/restore")
@require_identity
def restore_slate_item(slate_item_id):
    return _change_archive_state(slate_item_id, "usp_RestoreSlateItem", "@RestoreNote")


@peerslate_api.get("/badges")
@require_identity
def get_badges():
    identity = get_current_identity()
    rows = database_service.first_result(
        "usp_GetUserBadges", [("@UserKey", identity.user_key)]
    )
    return _result_payload(rows, "badges")


@peerslate_api.post("/achievements/evaluate")
@require_identity
def evaluate_achievements():
    identity = get_current_identity()
    result_sets = database_service.execute_procedure(
        "usp_EvaluateUserFlatAchievements", [("@UserKey", identity.user_key)]
    )
    achievements = database_service.name_result_sets(
        result_sets, ("newly_earned", "summary", "in_progress")
    )
    return jsonify({"success": True, "achievements": achievements})
