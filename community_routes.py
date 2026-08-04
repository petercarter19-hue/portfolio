"""Flagged public HTML routes for the owner-authored Community pilot."""

import hashlib
import hmac

from flask import (
    Blueprint,
    abort,
    current_app,
    redirect,
    render_template,
    request,
    url_for,
)

from identity import get_current_identity, get_optional_identity
from owner_authorization import is_owner
from services.community_contracts import (
    CommunityNotFoundError,
    CommunityUnavailableError,
    CommunityValidationError,
    opaque_key,
)
from services.community_restore_service import community_restore_service
from services.community_retention_service import CONTENT_RETENTION_DAYS
from services.database_service import DatabaseServiceError


community_routes = Blueprint("community_routes", __name__)


def enabled():
    return current_app.config.get("PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED", False)


def viewer_context():
    try:
        identity = get_optional_identity()
    except DatabaseServiceError:
        identity = None
    owner = bool(identity and is_owner(identity))
    draft_namespace = None
    if owner:
        signing_key = str(
            current_app.config.get("PEERSLATE_COMMUNITY_SIGNING_KEY") or ""
        ).encode("utf-8")
        if not signing_key:
            raise RuntimeError("Community draft isolation is unavailable.")
        draft_namespace = hmac.new(
            signing_key,
            str(identity.user_key).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
    return {
        "community_owner": owner,
        "community_signed_in": bool(identity),
        "community_display_name": getattr(identity, "display_name", None) if identity else None,
        "community_draft_namespace": draft_namespace,
    }


@community_routes.get("/the-slate/posts/<string:post_key>")
def community_post_page(post_key):
    if not enabled():
        abort(404)
    try:
        post_key = opaque_key(post_key, field="post key")
    except CommunityValidationError:
        abort(404)
    return render_template(
        "community_feed.html",
        community_post_key=post_key,
        community_contribution_key=None,
        **viewer_context(),
    )


@community_routes.get(
    "/the-slate/posts/<string:post_key>/contributions/<string:contribution_key>"
)
def community_contribution_page(post_key, contribution_key):
    if not enabled():
        abort(404)
    try:
        post_key = opaque_key(post_key, field="post key")
        contribution_key = opaque_key(
            contribution_key, field="contribution key"
        )
    except CommunityValidationError:
        abort(404)
    return render_template(
        "community_feed.html",
        community_post_key=post_key,
        community_contribution_key=contribution_key,
        **viewer_context(),
    )


@community_routes.get("/the-slate/recently-deleted")
def community_recently_deleted():
    """The author's own recovery window. Never public, never another member's."""
    if not enabled():
        abort(404)
    context = viewer_context()
    if not context["community_owner"]:
        # Neutral 404 rather than 403: the existence of someone's removed
        # content is not something a visitor should be able to probe for.
        abort(404)
    identity = get_current_identity()
    try:
        items = community_restore_service.list_restorable(identity.user_key)
        unavailable = False
    except CommunityUnavailableError:
        items = []
        unavailable = True
    return render_template(
        "community_recently_deleted.html",
        restorable_items=items,
        restore_unavailable=unavailable,
        retention_days=CONTENT_RETENTION_DAYS,
        restore_notice=request.args.get("restored"),
        **context,
    )


@community_routes.post("/the-slate/recently-deleted/restore")
def community_restore():
    if not enabled():
        abort(404)
    if not viewer_context()["community_owner"]:
        abort(404)
    identity = get_current_identity()
    kind = request.form.get("record_kind")
    key = request.form.get("record_key")
    try:
        if kind == "post":
            outcome = community_restore_service.restore_post(identity.user_key, key)
        elif kind == "contribution":
            outcome = community_restore_service.restore_contribution(
                identity.user_key, key
            )
        else:
            abort(400)
    except CommunityValidationError:
        abort(400)
    except CommunityNotFoundError:
        outcome = "not_found"
    except CommunityUnavailableError:
        outcome = "unavailable"
    return redirect(
        url_for("community_routes.community_recently_deleted", restored=outcome)
    )


@community_routes.get("/the-slate/public-pilot")
def community_pilot_policy():
    if not enabled():
        abort(404)
    return render_template("community_pilot_policy.html")


@community_routes.after_request
def keep_pilot_out_of_indexes(response):
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    response.headers["Cache-Control"] = "private, no-store"
    return response
