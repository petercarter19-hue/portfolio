"""Authenticated HTML routes for PeerSlate Community.

PS-COMMUNITY-AUTH-WALL-001: Community is served only to signed-in PeerSlate
members. Signed-out GETs go through sign-in and return to the exact page.
An identity failure is a private recovery state, never an anonymous render.
"""

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

from identity import AuthenticationRequired, get_current_identity
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


def _sign_in_redirect():
    """Send a signed-out GET through sign-in, back to this exact page."""
    return_to = request.full_path if request.query_string else request.path
    if return_to.endswith("?"):
        return_to = return_to[:-1]
    return redirect(url_for("auth.sign_in", return_to=return_to))


def require_community_member():
    """Availability, then trusted authentication, before anything else.

    Returns (identity, None) for a signed-in member, or (None, response)
    when the request must stop. An identity database failure is answered
    here as a private 503; AuthenticationPrincipalInvalid and
    IdentityMappingError deliberately propagate to the application's
    private recovery handlers. An identity failure must never be presented
    as signed out, anonymous, or demo Community.
    """
    if not enabled():
        abort(404)
    try:
        return get_current_identity(), None
    except AuthenticationRequired:
        if request.method == "GET":
            return None, _sign_in_redirect()
        # An expired-session POST must not be replayed through a redirect:
        # send the member to sign in and land on the page, not the action.
        return None, redirect(
            url_for("auth.sign_in", return_to="/the-slate/recently-deleted")
        )
    except DatabaseServiceError:
        # Identity storage failing is a service problem, not a sign-in
        # problem: a private 503, never an anonymous or demo render.
        current_app.logger.error("Community identity resolution failed.")
        abort(503)


def viewer_context(identity):
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
    identity, denied = require_community_member()
    if denied:
        return denied
    try:
        post_key = opaque_key(post_key, field="post key")
    except CommunityValidationError:
        abort(404)
    return render_template(
        "community_feed.html",
        community_post_key=post_key,
        community_contribution_key=None,
        **viewer_context(identity),
    )


@community_routes.get(
    "/the-slate/posts/<string:post_key>/contributions/<string:contribution_key>"
)
def community_contribution_page(post_key, contribution_key):
    identity, denied = require_community_member()
    if denied:
        return denied
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
        **viewer_context(identity),
    )


@community_routes.get("/the-slate/recently-deleted")
def community_recently_deleted():
    """The author's own recovery window. Never public, never another member's."""
    identity, denied = require_community_member()
    if denied:
        return denied
    context = viewer_context(identity)
    if not context["community_owner"]:
        # Neutral 404 rather than 403: the existence of someone's removed
        # content is not something a visitor should be able to probe for.
        abort(404)
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
    identity, denied = require_community_member()
    if denied:
        return denied
    if not viewer_context(identity)["community_owner"]:
        abort(404)
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


@community_routes.get("/the-slate/policy")
def community_policy():
    identity, denied = require_community_member()
    if denied:
        return denied
    return render_template("community_policy.html", **viewer_context(identity))


@community_routes.after_request
def keep_community_private(response):
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    response.headers["Cache-Control"] = "private, no-store"
    return response
