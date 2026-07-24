"""PeerSlate sign-in entry points and the protected owner workspace."""

import re
from urllib.parse import urlencode, urlsplit

from flask import (
    Blueprint,
    current_app,
    g,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    url_for,
)

from identity import AuthenticationRequired, get_current_identity, get_optional_identity
from services.database_service import DatabaseServiceError
from services.owner_home_service import OwnerHomeContractError, owner_home_service


auth = Blueprint("auth", __name__)
AUTH_PROVIDER_NAME = re.compile(r"^[A-Za-z0-9._-]{1,50}$")


def _auth_enabled():
    return current_app.config.get("PEERSLATE_TRUST_EASYAUTH_HEADERS", False) is True


def _safe_return_path(candidate, default="/app"):
    if not candidate or not isinstance(candidate, str):
        return default
    parsed = urlsplit(candidate)
    if parsed.scheme or parsed.netloc or not candidate.startswith("/"):
        return default
    if candidate.startswith("//") or "\\" in candidate:
        return default
    return candidate


def _easy_auth_path(action, return_path):
    provider = current_app.config.get("PEERSLATE_AUTH_PROVIDER_NAME", "aad")
    if not isinstance(provider, str) or not AUTH_PROVIDER_NAME.fullmatch(provider):
        current_app.logger.error("PeerSlate authentication provider is invalid.")
        return None

    if action == "login":
        query = urlencode({"post_login_redirect_uri": return_path})
        return f"/.auth/login/{provider}?{query}"

    query = urlencode({"post_logout_redirect_uri": return_path})
    return f"/.auth/logout?{query}"


def _render_auth_unavailable():
    return (
        render_template(
            "auth_unavailable.html",
            page_title="Sign in is not configured",
        ),
        503,
    )


def _render_identity_storage_unavailable():
    # Rendering base.html normally resolves the navigation identity again. The
    # request has already proved that the trusted principal reached Flask and
    # that only identity storage failed, so prevent a duplicate SQL wake-up
    # attempt while building this truthful recovery state.
    g.peerslate_identity_storage_unavailable = True
    response = make_response(
        render_template(
            "identity_storage_unavailable.html",
            page_title="Your workspace is waking up",
            retry_path=url_for("auth.owner_workspace"),
        ),
        503,
    )
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["Retry-After"] = "5"
    return response


@auth.get("/auth/sign-in")
def sign_in():
    return_path = _safe_return_path(request.args.get("return_to"))
    if not _auth_enabled():
        return _render_auth_unavailable()

    login_path = _easy_auth_path("login", return_path)
    if login_path is None:
        return _render_auth_unavailable()
    return redirect(login_path)


@auth.post("/auth/sign-out")
def sign_out():
    if not _auth_enabled():
        return _render_auth_unavailable()

    expected_origin = request.host_url.rstrip("/")
    origin = request.headers.get("Origin")
    fetch_site = request.headers.get("Sec-Fetch-Site")
    if (origin and origin.rstrip("/") != expected_origin) or (
        fetch_site and fetch_site not in {"same-origin", "none"}
    ):
        return jsonify({"success": False, "message": "Cross-site sign out denied."}), 403

    logout_path = _easy_auth_path("logout", "/")
    if logout_path is None:
        return _render_auth_unavailable()
    return redirect(logout_path)


@auth.get("/auth/session")
def session_status():
    try:
        identity = get_optional_identity()
    except DatabaseServiceError:
        current_app.logger.error("PeerSlate identity storage is unavailable.")
        response = jsonify(
            {
                "signed_in": True,
                "available": False,
                "state": "workspace_unavailable",
            }
        )
        response.status_code = 503
        response.headers["Cache-Control"] = "private, no-store"
        response.headers["Retry-After"] = "5"
        return response

    if identity is None:
        return jsonify({"signed_in": False, "available": _auth_enabled()})
    return jsonify(
        {
            "signed_in": True,
            "available": True,
            "display_name": identity.display_name or "PeerSlate member",
        }
    )


def _owner_home_enabled():
    return current_app.config.get("PEERSLATE_OWNER_HOME_ENABLED", False) is True


@auth.get("/app")
def owner_workspace():
    try:
        identity = get_current_identity()
    except AuthenticationRequired:
        return_path = _safe_return_path(request.full_path.rstrip("?"))
        return redirect(url_for("auth.sign_in", return_to=return_path))
    except DatabaseServiceError:
        current_app.logger.error("PeerSlate owner workspace identity lookup failed.")
        return _render_identity_storage_unavailable()

    # PS-HOME-FRONTEND-001: with the flag off, /app is byte-identical to the
    # released owner workspace fallback below (PEERSLATE_OWNER_HOME_ENABLED
    # defaults false, so this branch is never taken in current production).
    if not _owner_home_enabled():
        return render_template(
            "owner_workspace.html",
            page_title="My PeerSlate",
            member=identity,
        )

    # Flag on: render the finite Owner Home from the real owner-home.v1 view
    # model. A contract/database failure still renders the private shell with
    # an honest complete-failure state and a real safe Capture destination —
    # it never falls back to the legacy workspace or fabricates data.
    try:
        home = owner_home_service.get_home(identity).to_dict()
        home_failed = False
    except (DatabaseServiceError, OwnerHomeContractError):
        current_app.logger.error("PeerSlate Owner Home data is unavailable.")
        home = None
        home_failed = True

    # This private owner-specific render must never be stored by a browser or
    # intermediary.  app.py preserves an explicit response policy while it
    # continues to provide the legacy no-cache policy for ordinary HTML.
    return render_template(
        "owner_home.html",
        page_title="Owner Home",
        member=identity,
        home=home,
        home_failed=home_failed,
        standalone_owner_shell=True,
    ), (503 if home_failed else 200), {"Cache-Control": "private, no-store"}


@auth.app_context_processor
def shared_authentication_state():
    if getattr(g, "peerslate_identity_storage_unavailable", False):
        identity = None
        identity_storage_available = False
    else:
        try:
            identity = get_optional_identity()
            identity_storage_available = True
        except DatabaseServiceError:
            current_app.logger.error("PeerSlate navigation identity lookup failed.")
            identity = None
            identity_storage_available = False

    return {
        "current_member": identity,
        "auth_enabled": _auth_enabled(),
        "identity_storage_available": identity_storage_available,
        "auth_sign_in_url": url_for("auth.sign_in", return_to="/app"),
        "auth_sign_out_url": url_for("auth.sign_out"),
        "owner_workspace_url": url_for("auth.owner_workspace"),
        # Default off for every route. Only the flag-on Owner Home render
        # (PS-HOME-FRONTEND-001) passes standalone_owner_shell=True to
        # render_template, which overrides this context-processor default
        # (Flask applies explicit render_template kwargs last). base.html
        # uses it to bypass the public chrome for that render only.
        "standalone_owner_shell": False,
    }
