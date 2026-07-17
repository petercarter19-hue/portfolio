"""Protected owner-only routes for the PeerSlate application."""

from flask import Blueprint, current_app, redirect, render_template, request, url_for

from identity import AuthenticationRequired, get_current_identity
from services.database_service import DatabaseServiceError, database_service


owner = Blueprint("owner", __name__)
MAX_CAPTURE_BODY_LENGTH = 8000
CAPTURE_VALIDATION_MESSAGES = {
    "required": "Write something before saving your capture.",
    "too-long": f"Keep your capture to {MAX_CAPTURE_BODY_LENGTH:,} characters or fewer.",
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

        captures = database_service.first_result(
            "usp_ListCapturesForOwner",
            [
                ("@UserKey", identity.user_key),
                ("@Take", 50),
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
        captures=captures,
        validation_message=CAPTURE_VALIDATION_MESSAGES.get(request.args.get("error")),
        saved=request.args.get("saved") == "1",
        max_body_length=MAX_CAPTURE_BODY_LENGTH,
    )
