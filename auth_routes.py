"""PeerSlate sign-in entry points and the protected owner workspace."""

import re
import threading
import time
from urllib.parse import urlencode, urlsplit

from flask import (
    Blueprint,
    abort,
    current_app,
    g,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    url_for,
)

from db import get_connection
from identity import (
    AuthenticationPrincipalInvalid,
    AuthenticationRequired,
    get_current_identity,
    get_current_principal,
    get_optional_identity,
    get_optional_principal,
)
from services.database_service import DatabaseServiceError
from services.owner_home_service import OwnerHomeContractError, owner_home_service


auth = Blueprint("auth", __name__)
AUTH_PROVIDER_NAME = re.compile(r"^[A-Za-z0-9._-]{1,50}$")

# PS-SIGNIN-EXPERIENCE-001 item 2: how long a waking surface keeps checking
# automatically before it stops and leaves the member in manual control.
WAKING_RETRY_BUDGET_SECONDS = 90
MAX_RETURN_PATH_LENGTH = 2048

# PS-SIGNIN-EXPERIENCE-001 item 2.3 (sign-in pre-warm). /auth/sign-in is a
# public, unauthenticated endpoint, so the pre-warm must never let a caller
# create work on demand: at most one attempt may be in flight, and a new one
# may not start until the interval below has passed. Everything about it is
# best effort — it can never delay, change, or fail the Easy Auth redirect.
_PREWARM_MIN_INTERVAL_SECONDS = 30.0
_prewarm_lock = threading.Lock()
_prewarm_in_flight = False
_prewarm_last_started = None


def _auth_enabled():
    return current_app.config.get("PEERSLATE_TRUST_EASYAUTH_HEADERS", False) is True


def _safe_return_path(candidate, default="/app"):
    if not candidate or not isinstance(candidate, str):
        return default
    if len(candidate) > MAX_RETURN_PATH_LENGTH:
        return default
    if any(ord(character) < 32 or ord(character) == 127 for character in candidate):
        return default
    parsed = urlsplit(candidate)
    if (
        parsed.scheme
        or parsed.netloc
        or parsed.fragment
        or not candidate.startswith("/")
    ):
        return default
    if candidate.startswith("//") or "\\" in candidate:
        return default
    if "//" in candidate:
        return default
    if parsed.path == "/auth" or parsed.path.startswith("/auth/"):
        return default
    if parsed.path == "/.auth" or parsed.path.startswith("/.auth/"):
        return default
    # PS-COMMUNITY-AUTH-WALL-001: Community lives behind sign-in, so its
    # namespace joins the private-app namespace as the only permitted
    # post-auth destinations. Every other path stays rejected.
    allowed = ("/app", "/the-slate")
    if not any(
        parsed.path == prefix or parsed.path.startswith(prefix + "/")
        for prefix in allowed
    ):
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


def _render_auth_recovery(status_code=401):
    """Render a manual, non-looping account recovery surface.

    This is also used by the completion checkpoint when no trusted principal
    arrived.  It intentionally does not launch the external provider; the
    member controls the next attempt and can sign out of a stale platform
    session first.
    """
    g.peerslate_auth_context_guard = True
    g.peerslate_auth_navigation_state = "account_issue"
    response = make_response(
        render_template(
            "auth_recovery.html",
            page_title="Account check needed",
        ),
        status_code,
    )
    response.headers["Cache-Control"] = "private, no-store"
    return response


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
            waking_budget_seconds=WAKING_RETRY_BUDGET_SECONDS,
        ),
        503,
    )
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["Retry-After"] = "5"
    return response


def _prewarm_identity_storage():
    """Open and immediately close one database connection. Never raises.

    Runs on a daemon thread so a slow or failing connection cannot outlive the
    process or hold anything open. Nothing here reads a request, a member, or
    a response; the only observable effect is that Azure SQL serverless starts
    resuming a paused database.
    """
    global _prewarm_in_flight

    try:
        connection = get_connection()
        try:
            connection.close()
        except Exception:  # noqa: BLE001 - closing is best effort by design
            pass
    except Exception:  # noqa: BLE001 - a failed wake-up is not an error here
        # Deliberately no exception detail: this path is best effort and the
        # connection string must never reach a log.
        pass
    finally:
        with _prewarm_lock:
            _prewarm_in_flight = False


def _prewarm_enabled():
    # On by default in a real deployment; off under TESTING unless a test
    # opts in, so the suite never opens a real connection as a side effect.
    default = not current_app.config.get("TESTING", False)
    return current_app.config.get("PEERSLATE_SIGN_IN_PREWARM_ENABLED", default) is True


def _start_identity_storage_prewarm():
    """Best-effort, non-blocking Azure SQL wake-up on sign-in intent.

    Azure SQL serverless auto-pauses, and resuming it takes roughly 30-60
    seconds. Starting that resume as the member leaves for the Microsoft
    sign-in page means it usually finishes before they come back. Returns
    whether a thread was started; the caller ignores the result.
    """
    global _prewarm_in_flight, _prewarm_last_started

    if not _prewarm_enabled():
        return False

    now = time.monotonic()
    with _prewarm_lock:
        if _prewarm_in_flight:
            return False
        if (
            _prewarm_last_started is not None
            and now - _prewarm_last_started < _PREWARM_MIN_INTERVAL_SECONDS
        ):
            return False
        _prewarm_in_flight = True
        _prewarm_last_started = now

    try:
        threading.Thread(
            target=_prewarm_identity_storage,
            name="peerslate-signin-prewarm",
            daemon=True,
        ).start()
    except Exception:  # noqa: BLE001 - never let this affect the redirect
        with _prewarm_lock:
            _prewarm_in_flight = False
        return False
    return True


@auth.get("/auth/sign-in")
def sign_in():
    return_path = _safe_return_path(request.args.get("return_to"))
    if not _auth_enabled():
        return _render_auth_unavailable()

    # A valid principal is already enough to reach the checkpoint.  Do not
    # resolve the database-backed identity here: it can wake Azure SQL and is
    # neither needed nor safe as a condition for deciding whether to launch
    # the external provider. Invalid principals deliberately propagate to the
    # global recovery handler instead of being treated as signed out.
    if get_optional_principal() is not None:
        return redirect(url_for("auth.complete", return_to=return_path))

    completion_path = url_for("auth.complete", return_to=return_path)
    login_path = _easy_auth_path("login", completion_path)
    if login_path is None:
        return _render_auth_unavailable()

    # PS-SIGNIN-EXPERIENCE-001 item 2.3: start the serverless database resume
    # while the member is on the Microsoft page. Fully guarded so the redirect
    # below is reached with the same timing and the same result either way.
    try:
        _start_identity_storage_prewarm()
    except Exception:  # noqa: BLE001 - sign-in must never depend on this
        current_app.logger.warning(
            "PeerSlate sign-in pre-warm could not be scheduled."
        )

    return redirect(login_path)


@auth.get("/auth/complete")
def complete():
    """Verify the provider return once, without doing an account lookup."""
    return_path = _safe_return_path(request.args.get("return_to"))
    if not _auth_enabled():
        return _render_auth_unavailable()
    try:
        get_current_principal()
    except AuthenticationRequired:
        # A platform callback without a principal must never automatically
        # start another provider redirect; that creates a browser loop that
        # hides the actual recovery choice from the member.
        return _render_auth_recovery()
    return redirect(return_path)


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
    # This endpoint is intentionally principal-only. It is used for harmless
    # client-side header reconciliation and must never wake SQL, upsert an
    # account, or expose database availability.
    if not _auth_enabled():
        response = jsonify({"state": "auth_unavailable"})
        response.status_code = 503
        response.headers["Cache-Control"] = "private, no-store"
        return response

    try:
        principal = get_optional_principal()
    except AuthenticationPrincipalInvalid:
        response = jsonify({"state": "invalid_session"})
        response.status_code = 401
    else:
        if principal is None:
            response = jsonify({"state": "signed_out"})
        else:
            response = jsonify({"state": "authenticated"})
    response.headers["Cache-Control"] = "private, no-store"
    return response


def _owner_home_enabled():
    return current_app.config.get("PEERSLATE_OWNER_HOME_ENABLED", False) is True


def _studio_slice1_enabled():
    return current_app.config.get("PEERSLATE_SLATE_STUDIO_SLICE1_ENABLED", False) is True


def _workshop_nav_enabled():
    """Mirrors ``workshop_routes._workshop_enabled()`` exactly.

    Duplicated locally rather than imported for the same file-ownership-
    boundary reason workshop_routes.py's own docstring documents for its
    ``_safe_return_path``/``_is_same_origin_write`` duplicates: this module
    has no edit-time dependency on the other lane's file. MINOR 9
    correction: the studio shell's ``navigation.workshop_url`` must not
    point at a route that 404s in a flag-off deployment.
    """
    return current_app.config.get("PEERSLATE_WORKSHOP_ENABLED", False) is True


def _studio_frame_view_model(identity=None, *, access_state="ready"):
    """Return the deliberately finite, server-owned Slice 1 frame.

    This shell has no Board, work, publication, or member-data service in its
    approved scope.  In particular, the current application cannot establish a
    member's published Slate URL without using the Pete fixture or introducing
    a new contract, so it truthfully reports that connection as unavailable.
    """
    is_ready = access_state == "ready" and identity is not None
    account_url = url_for("owner.settings") if is_ready else None
    return {
        "schema_version": "studio-frame.v1",
        "member": {
            "display_name": (
                (identity.display_name or "PeerSlate member") if is_ready else None
            ),
            "account_url": account_url,
        },
        "navigation": {
            "my_slate_url": None,
            "community_url": url_for("the_slate"),
            # PS-WORKSHOP-001: Workshop ships at its own protected route,
            # /app/workshop, not /app (architecture doc 17 section A1,
            # resolved 2026-08-01; doc 18 slice W1's "integration
            # consequence" note calls out this exact stale reference).
            # MINOR 9 correction: fall back to the owner workspace when the
            # flag is off so the studio shell never links to a route that
            # 404s in a flag-off deployment.
            "workshop_url": (
                url_for("workshop.my_information")
                if _workshop_nav_enabled()
                else url_for("auth.owner_workspace")
            ),
            "build_your_future_url": url_for("auth.studio_build_your_future"),
            "public_interview_studio_url": url_for("interview_studio"),
            "sign_out_url": url_for("auth.sign_out"),
            "retry_url": url_for("auth.studio_build_your_future"),
        },
        "workspace": {
            "access_state": access_state,
            # Slice 1 deliberately has no authorized supported-item contract.
            # It must therefore never claim the visual empty state.
            "content_state": "not_connected",
        },
        "published_slate": {
            # Do not point a reusable member experience at the existing Pete
            # fixture.  A later published-Slate contract may change this only
            # when it can resolve a member-owned route on the server.
            "state": "unavailable",
            "url": None,
        },
    }


def _render_studio_unavailable():
    """Return a private, payload-free Studio recovery frame.

    The trusted principal reached Flask, but identity storage did not.  The
    route does not fall back to fixture identity, Board data, or a public URL.
    """
    g.peerslate_identity_storage_unavailable = True
    response = make_response(
        render_template(
            "owner_studio_build_your_future.html",
            page_title="Build Your Future",
            frame=_studio_frame_view_model(access_state="unavailable"),
        ),
        503,
    )
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["Retry-After"] = "5"
    return response


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
        # The rendered bytes stay byte-identical to the released baseline;
        # only the response policy hardens. This page carries the member's
        # own workspace, so it must not be stored by a shared cache or
        # restored from the back/forward cache after sign-out.
        return render_template(
            "owner_workspace.html",
            page_title="My PeerSlate",
            member=identity,
        ), 200, {"Cache-Control": "private, no-store"}

    # Flag on: render the finite Owner Home from the real owner-home.v1 view
    # model. A contract/database failure still renders the private shell with
    # an honest state and a real safe Capture destination — it never falls
    # back to the legacy workspace or fabricates data.
    #
    # PS-SIGNIN-EXPERIENCE-001 item 2.1: the two failures are not the same
    # thing and must not read the same way. Azure SQL serverless auto-pauses,
    # so DatabaseServiceError on the first signed-in request after an idle
    # period usually means "the database is resuming" — a transient wake-up
    # that resolves itself in well under a minute. OwnerHomeContractError
    # means the data PeerSlate did receive was not a valid owner-home.v1
    # payload, which is a real failure and keeps the existing failure card.
    try:
        home = owner_home_service.get_home(identity).to_dict()
        home_failed = False
        home_waking = False
    except DatabaseServiceError:
        current_app.logger.error("PeerSlate Owner Home storage is unavailable.")
        home = None
        home_failed = False
        home_waking = True
    except OwnerHomeContractError:
        current_app.logger.error("PeerSlate Owner Home data is unavailable.")
        home = None
        home_failed = True
        home_waking = False

    # This private owner-specific render must never be stored by a browser or
    # intermediary.  app.py preserves an explicit response policy while it
    # continues to provide the legacy no-cache policy for ordinary HTML.
    response_headers = {"Cache-Control": "private, no-store"}
    if home_waking:
        # Same response policy the identity waking surface already returns.
        response_headers["Retry-After"] = "5"

    return render_template(
        "owner_home.html",
        page_title=("Your workspace is waking up" if home_waking else "Owner Home"),
        member=identity,
        home=home,
        home_failed=home_failed,
        home_waking=home_waking,
        waking_retry_path=url_for("auth.owner_workspace"),
        waking_budget_seconds=WAKING_RETRY_BUDGET_SECONDS,
        standalone_owner_shell=True,
    ), (503 if (home_failed or home_waking) else 200), response_headers


@auth.get("/app/studio/build-your-future")
def studio_build_your_future():
    """Render the default-off, protected Slice 1 Studio shell and frame."""
    # Fail before identity resolution or template rendering so the disabled
    # route exposes no Studio asset, server view-model, or private payload.
    if not _studio_slice1_enabled():
        abort(404)

    try:
        identity = get_current_identity()
    except AuthenticationRequired:
        return_path = _safe_return_path(request.full_path.rstrip("?"))
        return redirect(url_for("auth.sign_in", return_to=return_path))
    except DatabaseServiceError:
        current_app.logger.error("PeerSlate Studio identity lookup failed.")
        return _render_studio_unavailable()

    return render_template(
        "owner_studio_build_your_future.html",
        page_title="Build Your Future",
        frame=_studio_frame_view_model(identity),
    ), 200, {"Cache-Control": "private, no-store"}


@auth.app_context_processor
def shared_authentication_state():
    # Error/recovery templates extend base.html. Do not ask identity.py to
    # inspect the same bad principal again while Flask is building that page.
    if getattr(g, "peerslate_auth_context_guard", False):
        principal = None
        navigation_state = getattr(
            g, "peerslate_auth_navigation_state", "account_issue"
        )
        identity_storage_available = False
    elif getattr(g, "peerslate_identity_storage_unavailable", False):
        principal = getattr(g, "peerslate_principal", None)
        navigation_state = "workspace_waking"
        identity_storage_available = False
    else:
        # Keep global navigation out of the account-mapping path. A valid
        # Easy Auth principal is sufficient to render session controls, and
        # public pages must not trigger a SQL connection just to draw a header.
        principal = get_optional_principal()
        identity_storage_available = True
        if principal is not None:
            navigation_state = "authenticated"
        elif _auth_enabled():
            navigation_state = "signed_out"
        else:
            navigation_state = "auth_unavailable"

    return {
        "current_member": principal,
        "auth_enabled": _auth_enabled(),
        "identity_storage_available": identity_storage_available,
        "auth_navigation_state": navigation_state,
        "auth_sign_in_url": url_for("auth.sign_in", return_to="/app"),
        "auth_sign_out_url": url_for("auth.sign_out"),
        "auth_complete_url": url_for("auth.complete", return_to="/app"),
        "owner_workspace_url": url_for("auth.owner_workspace"),
        # Default off for every route. Only the flag-on Owner Home render
        # (PS-HOME-FRONTEND-001) passes standalone_owner_shell=True to
        # render_template, which overrides this context-processor default
        # (Flask applies explicit render_template kwargs last). base.html
        # uses it to bypass the public chrome for that render only.
        "standalone_owner_shell": False,
    }
