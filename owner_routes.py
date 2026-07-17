"""Protected owner-only routes for the PeerSlate application."""

from flask import Blueprint, redirect, render_template, url_for

from identity import AuthenticationRequired, get_current_identity
from services.database_service import DatabaseServiceError


owner = Blueprint("owner", __name__)


@owner.get("/app/settings")
def settings():
    """Render the signed-in member's account settings overview."""
    try:
        identity = get_current_identity()
    except AuthenticationRequired:
        return redirect(url_for("auth.sign_in", return_to="/app/settings"))
    except DatabaseServiceError:
        return (
            render_template(
                "auth_unavailable.html",
                page_title="Sign in is not configured",
            ),
            503,
        )

    return render_template(
        "owner_settings.html",
        page_title="Settings",
        member=identity,
    )
