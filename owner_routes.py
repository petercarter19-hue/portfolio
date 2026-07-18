"""Protected owner-only routes for the PeerSlate application."""

import json
import re
from datetime import date, datetime
from uuid import UUID

from flask import (
    Blueprint,
    Response,
    current_app,
    redirect,
    render_template,
    request,
    url_for,
)

from identity import AuthenticationRequired, get_current_identity
from services.database_service import DatabaseServiceError, database_service


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
}
CAPTURE_SUCCESS_MESSAGES = {
    "corrected": "Correction saved as a new version. The original is unchanged.",
    "archived": "Capture archived. You can restore it from Archived captures.",
    "restored": "Capture restored to your active captures.",
    "deleted": "Capture and its correction history were permanently deleted.",
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
        max_body_length=MAX_CAPTURE_BODY_LENGTH,
        max_correction_note_length=MAX_CORRECTION_NOTE_LENGTH,
    )


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
        result = database_service.first_row(
            "usp_DeleteCapture",
            [
                ("@UserKey", identity.user_key),
                ("@CaptureKey", normalized_capture_key),
                ("@ExpectedRowVersion", expected_row_version),
            ],
        )
    except DatabaseServiceError:
        current_app.logger.error("PeerSlate private capture deletion is unavailable.")
        return _render_owner_unavailable()

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

    named = database_service.name_result_sets(result_sets, ("capture", "revisions"))
    if not named["capture"]:
        return "Capture not found.", 404

    capture = dict(named["capture"][0])
    revision_number = int(capture.get("revision_number") or 0)
    revisions = named["revisions"]
    if not revisions and capture.get("revisions_json"):
        try:
            revisions = json.loads(capture["revisions_json"])
        except (TypeError, ValueError):
            current_app.logger.error(
                "PeerSlate private capture export returned invalid revision data."
            )
            return _render_owner_unavailable()
    payload = {
        "schema": "peerslate.capture.export",
        "schema_version": 1,
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
        f'attachment; filename="peerslate-capture-{normalized_capture_key}-v1.json"'
    )
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response
