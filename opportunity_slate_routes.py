"""Opportunity Slate room routes — PS-OPPSLATE-001, slice OS-1.

Package: docs/initiatives/PS-OPPORTUNITY-SLATE-001. Controlling contract:
01_ARCHITECTURE_AND_IMPLEMENTATION_HANDOFF.md, sections 3 (shell), 5
(palette), 9 (routes), 11 (security), 12 (responsive), 13 (accessibility),
16 (slice OS-1 scope), 17-18 (owner decisions, public v1 mode).

Slice OS-1 delivers exactly two member-reachable screens — role intake and
Review Source — plus checkpoint 1 of 2. **No AI call happens anywhere in
this module or anything it imports.** Requirement interpretation is OS-2,
alignment is OS-3, saving is OS-4, dictation is OS-5, and document upload /
public-link import are OS-6. Where the locked visual set shows one of those
later capabilities, this slice renders an honest, inert state rather than a
control that pretends to work.

Because there is no AI latency in OS-1, there is also no processing stage
rail: the intake-to-review transition is an ordinary request. Rendering
fabricated "Extracting employer wording..." stages for a request that does
none of that would be theatre, so the ``os-stage-rail`` component is not
built in this slice (handoff section 7 / the truthfulness rule).

Two modes, one implementation (owner decision, handoff section 18)
-----------------------------------------------------------------
Mode is derived server-side from ``get_optional_identity`` on every
request and is never asserted by client input.

*Signed-in members* get the private workbench: an owner-scoped, expiry-
bounded working session in Azure SQL via
``services/opportunity_slate_service.py``. Their screens are ordinary
server-rendered pages driven by plain HTML form posts, so the flow works
with JavaScript disabled.

*Anonymous visitors* get a truthful public session over the SAME rendered
screens, with their working state held in their own browser: an
``itsdangerous`` ``URLSafeTimedSerializer`` context token (the verified
``interview_context_serializer`` precedent, app.py) kept in
``sessionStorage`` and posted back as a fetch JSON body. Every anonymous
interaction goes through ONE endpoint, :func:`public_session`, which
imports no write method and calls no stored procedure — "anonymous mode
never reaches a database procedure" is therefore structurally true here,
not merely a rule someone has to remember. A missing, tampered, or expired
token resets honestly to intake; it never fabricates a session.

The four member mutation routes below are owner-only and answer a
signed-out caller with a neutral 404 (``require_identity_or_not_found``
semantics, ``peerslate_api.py``), so a caller can never tell "not signed
in" from "not found" from "flag off".

Unlisted posture (handoff section 18 safeguard 4)
-------------------------------------------------
``/opportunity-slate`` is a top-level path, so it sits outside the
``Disallow: /app`` umbrella in robots.txt. ``noindex`` is therefore
mandatory, not optional: :func:`_apply_room_headers` sets ``X-Robots-Tag``
on every response from this blueprint and the template carries the
matching ``<meta name="robots">``. robots.txt is deliberately NOT given a
``Disallow`` line for this path — disallowing it would stop a crawler
fetching the page and therefore stop it ever seeing the noindex directive.
There is no sitemap entry and no navigation entry anywhere.

``_is_same_origin_write`` mirrors ``workshop_routes._is_same_origin_write``
exactly, and is duplicated locally for the same file-ownership reason that
module gives.
"""

import re
from uuid import uuid4

from flask import (
    Blueprint,
    abort,
    current_app,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    url_for,
)
from itsdangerous import BadData, URLSafeTimedSerializer

from identity import get_optional_identity
from services.database_service import DatabaseServiceError
from services.opportunity_slate_service import (
    MAX_SOURCE_TEXT_UNITS,
    OpportunitySlateServiceError,
    opportunity_slate_service,
    validate_source_text,
)


opportunity_slate = Blueprint("opportunity_slate", __name__)

ROOM_PATH = "/opportunity-slate"

# Handoff section 18: the anonymous context token is a browser-held working
# state, not a login. Eight hours is long enough that a visitor can step
# away mid-review without silently losing their pasted role text, and short
# enough that a token copied out of one browser stops working the same day.
PUBLIC_CONTEXT_MAX_AGE_SECONDS = 8 * 60 * 60
PUBLIC_CONTEXT_SALT = "peerslate-opportunity-slate-working-v1"
PUBLIC_CONTEXT_VERSION = 1
# Defensive bound on the inbound token string itself, before any signature
# work. Comfortably above a signed, compressed 20,000-unit source plus its
# correction; far below MAX_CONTENT_LENGTH.
MAX_PUBLIC_CONTEXT_TOKEN_LENGTH = 400_000
_SERIALIZER_EXTENSION_KEY = "peerslate_opportunity_slate_serializer"

# Presentation-only mappings. The service returns validated enum values;
# member-facing labels are a view concern and live here, not in the
# service (the workshop_routes.py convention).
CAPTURE_METHOD_LABELS = {
    "pasted": "Pasted or typed",
    "dictated": "Dictated",
    "uploaded": "Uploaded document",
    "imported": "Imported public link",
}

STEP_ROLE = "role"
STEP_REVIEW = "review"
# ``replace`` is a role-intake variant, not a third screen: it opens the
# intake editor empty so the member can bring in a different role.
STEP_REPLACE = "replace"
_ALLOWED_STEPS = frozenset({STEP_ROLE, STEP_REVIEW, STEP_REPLACE})

_PUBLIC_ACTIONS = frozenset({"render", "step", "source", "correct", "confirm", "discard"})

# Reproduced exactly from the locked visual set. Handoff section 14-M11
# lists the session-private / saved / failure sentences as trust-critical:
# they are quoted, never paraphrased. The rest live in the templates beside
# the markup they belong to.
TRUTH_NOTHING_SAVED = "Nothing is saved yet."

UNAVAILABLE_MESSAGE = (
    "We couldn't reach your Opportunity Slate right now. Nothing was saved "
    "or analyzed, and nothing was lost."
)
CONFLICT_MESSAGE = (
    "This role source changed somewhere else. Your wording is shown below — "
    "review it and apply it again."
)
FIELD_ERROR_MESSAGES = {
    "required": "Add the role text before continuing.",
    "too_long": (
        f"That role text is longer than {MAX_SOURCE_TEXT_UNITS:,} characters. "
        "Shorten it and try again — your text is still below."
    ),
    "invalid": "We couldn't read that entry. Review it and try again.",
}
DEFAULT_FIELD_ERROR = "Something went wrong. Review your entry and try again."
# The short marker rendered beside the field itself. The failure card above
# carries the full sentence; repeating that sentence verbatim next to the
# input would be noise, so the two say different, complementary things and
# the field's aria-describedby points at this one.
FIELD_ERROR_HINTS = {
    "required": "Add the role text to continue.",
    "too_long": f"Shorten this to {MAX_SOURCE_TEXT_UNITS:,} characters or fewer.",
    "invalid": "Check this entry and try again.",
}
DEFAULT_FIELD_HINT = "Check this entry and try again."


def _field_error(heading, code, truth):
    return {
        "kind": "field",
        "heading": heading,
        "message": FIELD_ERROR_MESSAGES.get(code, DEFAULT_FIELD_ERROR),
        "field_hint": FIELD_ERROR_HINTS.get(code, DEFAULT_FIELD_HINT),
        "truth": truth,
    }


def _opportunity_slate_enabled():
    return (
        current_app.config.get("PEERSLATE_OPPORTUNITY_SLATE_ENABLED", False) is True
    )


def _is_same_origin_write():
    """Allow a state-changing Opportunity Slate request only when it proves
    same origin.

    Mirrors ``workshop_routes._is_same_origin_write`` exactly (see that
    function's docstring for the fail-closed rationale): a request carrying
    neither ``Origin`` nor ``Sec-Fetch-Site`` is treated as untrusted rather
    than allowed, because these routes include real no-JS HTML form posts.
    Applied in BOTH modes — the public session is not the lenient one.
    """
    expected_origin = request.host_url.rstrip("/")
    origin = request.headers.get("Origin")
    fetch_site = request.headers.get("Sec-Fetch-Site")
    if origin and origin.rstrip("/") != expected_origin:
        return False
    if fetch_site and fetch_site not in {"same-origin", "none"}:
        return False
    return bool(origin or fetch_site)


def _context_serializer():
    """The signed browser-held working-state serializer, built once per app.

    Mirrors app.py's ``interview_context_serializer`` construction with its
    own dedicated salt, so a token minted for one surface can never be
    replayed against the other.
    """
    serializer = current_app.extensions.get(_SERIALIZER_EXTENSION_KEY)
    if serializer is None:
        serializer = URLSafeTimedSerializer(
            current_app.config["PEERSLATE_OPPSLATE_CONTEXT_SIGNING_KEY"],
            salt=PUBLIC_CONTEXT_SALT,
        )
        current_app.extensions[_SERIALIZER_EXTENSION_KEY] = serializer
    return serializer


@opportunity_slate.after_request
def _apply_room_headers(response):
    """Private, unstorable, and unindexed on every response.

    ``no-store`` applies in BOTH modes: an anonymous response carries the
    visitor's own pasted role text and a signed state token, neither of
    which belongs in a shared cache. The blueprint is additionally listed in
    app.py's private-cache set; this is the route-local guarantee that does
    not depend on that list staying correct.
    """
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive"
    return response


# ---------------------------------------------------------------------------
# Display normalization
#
# Slice OS-1 has no AI, so nothing here interprets, rewrites, summarizes, or
# classifies the employer's wording. This is a deterministic, presentation-
# only layout of the member's own text into blocks: blank lines separate
# blocks, bullet-marked lines become list items, and a short standalone line
# that is followed by more content is shown as a section heading. Not one
# character of the text is added, removed, or reordered, and the exact
# stored wording is always one click away in the correction editor and the
# compare view. The right rail says this in plain words on the screen.
# ---------------------------------------------------------------------------
_BULLET_LINE = re.compile(r"^\s*(?:[-–—•*·]|\d{1,2}[.)])\s+(.*)$")
_HEADING_MAX_UNITS = 80
_HEADING_TERMINATORS = ".!?,;"


def _normalize_display_blocks(text):
    """Lay the member's captured text out for reading. Presentation only."""
    raw_blocks = [
        block.strip("\n") for block in re.split(r"\n\s*\n", text.replace("\r\n", "\n"))
    ]
    blocks = []
    for raw_block in raw_blocks:
        lines = [line.rstrip() for line in raw_block.split("\n") if line.strip()]
        if not lines:
            continue
        items = []
        paragraph_lines = []
        for line in lines:
            bullet = _BULLET_LINE.match(line)
            if bullet:
                if paragraph_lines:
                    blocks.append(
                        {"kind": "paragraph", "text": " ".join(paragraph_lines)}
                    )
                    paragraph_lines = []
                items.append(bullet.group(1).strip())
                continue
            if items:
                blocks.append({"kind": "list", "items": items})
                items = []
            paragraph_lines.append(line.strip())
        if paragraph_lines:
            blocks.append({"kind": "paragraph", "text": " ".join(paragraph_lines)})
        if items:
            blocks.append({"kind": "list", "items": items})

    # Promote a short standalone paragraph that introduces following content
    # to a heading. Conservative on purpose: never the last block, never
    # long, never a sentence.
    for index, block in enumerate(blocks[:-1]):
        if block["kind"] != "paragraph":
            continue
        candidate = block["text"]
        if len(candidate.encode("utf-16-le")) // 2 > _HEADING_MAX_UNITS:
            continue
        if candidate.endswith(tuple(_HEADING_TERMINATORS)):
            continue
        blocks[index] = {"kind": "heading", "text": candidate}
    return blocks


# ---------------------------------------------------------------------------
# View models
# ---------------------------------------------------------------------------


def _base_room(mode, *, step, error=None):
    is_public = mode == "public"
    return {
        "mode": mode,
        "is_public": is_public,
        "step": step,
        "error": error,
        "max_source_units": MAX_SOURCE_TEXT_UNITS,
        "back_url": "/",
        "room_url": url_for("opportunity_slate.room"),
        "source_url": url_for("opportunity_slate.set_source"),
        "correct_url": url_for("opportunity_slate.correct_source"),
        "confirm_url": url_for("opportunity_slate.confirm_source"),
        "delete_url": url_for("opportunity_slate.delete_source"),
        "public_session_url": url_for("opportunity_slate.public_session"),
        "role_step_url": url_for("opportunity_slate.room", step=STEP_ROLE),
        "replace_step_url": url_for("opportunity_slate.room", step=STEP_REPLACE),
        "review_step_url": url_for("opportunity_slate.room"),
    }


def _intake_room(mode, *, text="", replace=False, error=None, has_source=False):
    room = _base_room(mode, step=STEP_REPLACE if replace else STEP_ROLE, error=error)
    room.update(
        {
            "state_title_lead": "Role",
            "state_title_rest": "Bring a role",
            "checkpoint_label": None,
            "source_text": text,
            "is_replace": replace,
            "has_source": has_source,
            "idempotency_key": str(uuid4()),
            "source": None,
        }
    )
    return room


def _review_room(
    mode,
    *,
    source_key,
    session_key,
    source_version_token,
    session_version_token,
    version_number,
    original_text,
    corrected_text,
    is_confirmed,
    capture_method="pasted",
    editing=False,
    editor_text=None,
    error=None,
):
    display_text = corrected_text or original_text
    room = _base_room(mode, step=STEP_REVIEW, error=error)
    room.update(
        {
            "state_title_lead": "Review",
            "state_title_rest": "Source",
            "checkpoint_label": "Checkpoint 1 of 2",
            "source_text": display_text,
            "is_replace": False,
            "has_source": True,
            "idempotency_key": str(uuid4()),
            "source": {
                "source_key": source_key,
                "session_key": session_key,
                "version_token": source_version_token,
                "session_version_token": session_version_token,
                "version_number": version_number,
                "version_label": f"Source Version {version_number}",
                "capture_method_label": CAPTURE_METHOD_LABELS.get(
                    capture_method, "Pasted or typed"
                ),
                "original_text": original_text,
                "display_text": display_text,
                "has_correction": bool(corrected_text),
                "blocks": _normalize_display_blocks(display_text),
                "original_blocks": _normalize_display_blocks(original_text),
                "is_confirmed": bool(is_confirmed),
                "editing": bool(editing),
                "editor_text": editor_text if editor_text is not None else display_text,
            },
        }
    )
    return room


def _review_room_from_view(view, mode="member", **overrides):
    return _review_room(
        mode,
        source_key=view.source_key,
        session_key=view.working_session_key,
        source_version_token=view.source_version_token,
        session_version_token=view.session_version_token,
        version_number=view.version_number,
        original_text=view.original_text,
        corrected_text=view.member_corrected_text,
        is_confirmed=view.is_confirmed,
        capture_method=view.capture_method,
        **overrides,
    )


def _review_room_from_context(context, mode="public", **overrides):
    return _review_room(
        mode,
        source_key=None,
        session_key=None,
        source_version_token=None,
        session_version_token=None,
        version_number=context["version"],
        original_text=context["text"],
        corrected_text=context.get("corrected"),
        is_confirmed=context.get("confirmed", False),
        capture_method="pasted",
        **overrides,
    )


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _render_room(room, *, status=200, context_token=None):
    response = make_response(
        render_template(
            "opportunity_slate.html",
            page_title="Opportunity Slate",
            room=room,
            context_token=context_token,
        ),
        status,
    )
    return response


def _render_unavailable(mode="member", *, text=""):
    """Truthful 503 for a real storage failure.

    Never falls back to fixture content and never claims the member has no
    working session — "we couldn't reach it" and "it does not exist" are
    different facts and are told apart here.
    """
    # Operational signal only. The message deliberately carries no member
    # wording, source key, or session key — the failure is what operations
    # needs, and the employer/member text is not.
    current_app.logger.error("PeerSlate Opportunity Slate working store is unavailable.")
    room = _intake_room(
        mode,
        text=text,
        error={
            "kind": "unavailable",
            "heading": "We couldn't open your Opportunity Slate.",
            "message": UNAVAILABLE_MESSAGE,
            "truth": "Session private • Nothing was saved or analyzed.",
        },
    )
    room["unavailable"] = True
    response = _render_room(room, status=503)
    response.headers["Retry-After"] = "5"
    return response


def _render_fragment(room, *, context_token=None):
    """The room as an HTML fragment, for the anonymous fetch transport.

    Deliberately the SAME Jinja template the signed-in page renders, so the
    public session cannot drift into a second, differently-worded surface.
    """
    return render_template(
        "partials/opportunity_slate/_room.html",
        room=room,
        context_token=context_token,
    )


# ---------------------------------------------------------------------------
# Anonymous context token (handoff section 18)
# ---------------------------------------------------------------------------


def _dump_public_context(context):
    return _context_serializer().dumps(context)


def _load_public_context(token):
    """Return a validated context dict, or ``None``.

    ``None`` is the honest-reset signal: a missing, oversized, tampered,
    unsigned, or expired token is never repaired, guessed at, or partially
    trusted — the visitor simply starts again at role intake.
    """
    if not isinstance(token, str) or not token:
        return None
    if len(token) > MAX_PUBLIC_CONTEXT_TOKEN_LENGTH:
        return None
    try:
        context = _context_serializer().loads(
            token, max_age=PUBLIC_CONTEXT_MAX_AGE_SECONDS
        )
    except BadData:
        return None
    if not isinstance(context, dict):
        return None
    if context.get("v") != PUBLIC_CONTEXT_VERSION:
        return None

    text = context.get("text")
    try:
        text = validate_source_text(text)
    except OpportunitySlateServiceError:
        return None

    corrected = context.get("corrected")
    if corrected is not None:
        try:
            corrected = validate_source_text(corrected, label="corrected wording")
        except OpportunitySlateServiceError:
            return None

    version = context.get("version")
    if not isinstance(version, int) or isinstance(version, bool) or not 1 <= version <= 50:
        return None
    confirmed = context.get("confirmed", False)
    if not isinstance(confirmed, bool):
        return None

    return {
        "v": PUBLIC_CONTEXT_VERSION,
        "text": text,
        "corrected": corrected,
        "version": version,
        "confirmed": confirmed,
    }


def _public_json_body():
    """Read the fetch JSON body under a hard size bound.

    Uses ``silent=True`` so a malformed body is a named, honest failure
    rather than a 400 HTML error page inside a fetch call.
    """
    body = request.get_json(silent=True)
    return body if isinstance(body, dict) else None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


def _resolve_identity_or_unavailable():
    """``(identity, failure_response)``.

    A ``DatabaseServiceError`` while resolving identity is never treated as
    "just signed out" — that is a real failure and gets the truthful 503
    (the workshop_routes.py rule).
    """
    try:
        return get_optional_identity(), None
    except DatabaseServiceError:
        return None, _render_unavailable()


def _requested_step():
    requested = request.args.get("step")
    return requested if requested in _ALLOWED_STEPS else None


@opportunity_slate.get(ROOM_PATH)
def room():
    # Flag check outermost, before any identity resolution: flag-off is
    # indistinguishable from not-found.
    if not _opportunity_slate_enabled():
        abort(404)

    identity, failure = _resolve_identity_or_unavailable()
    if failure is not None:
        return failure

    step = _requested_step()

    if identity is None:
        # Handoff section 18. The public room always renders intake
        # server-side; opportunity-slate.js rehydrates from the visitor's
        # own sessionStorage when it holds a token, and otherwise honestly
        # leaves them here. The ?step= hint is a signed-in navigation aid
        # and is deliberately ignored in public mode, where the browser
        # holds the only state there is.
        return _render_room(_intake_room("public"))

    # Opportunistic purge of this owner's already-expired working data
    # (handoff section 8). Maintenance only: expiry is enforced at read
    # regardless, so a purge failure must not deny the member their room.
    try:
        opportunity_slate_service.purge_expired_working_data_for_owner(
            identity.user_key
        )
    except (DatabaseServiceError, OpportunitySlateServiceError):
        pass

    try:
        working = opportunity_slate_service.get_working_session_for_owner(
            identity.user_key
        )
    except (DatabaseServiceError, OpportunitySlateServiceError):
        return _render_unavailable()

    if working is None:
        return _render_room(_intake_room("member"))
    if step == STEP_REPLACE:
        return _render_room(_intake_room("member", replace=True, has_source=True))
    if step == STEP_ROLE:
        return _render_room(
            _intake_room("member", text=working.display_text, has_source=True)
        )
    return _render_room(_review_room_from_view(working))


@opportunity_slate.post(f"{ROOM_PATH}/source")
def set_source():
    """Capture or replace the employer source (signed-in members).

    Anonymous visitors reach the same screen through
    :func:`public_session`; this route is owner-only.
    """
    if not _opportunity_slate_enabled():
        abort(404)
    if not _is_same_origin_write():
        abort(403)
    identity, failure = _resolve_identity_or_unavailable()
    if failure is not None:
        return failure
    if identity is None:
        abort(404)

    raw_text = request.form.get("source_text", "")
    idempotency_key = request.form.get("idempotency_key") or str(uuid4())
    replace = request.form.get("replace") == "1"

    try:
        clean_text = validate_source_text(raw_text)
    except OpportunitySlateServiceError as error:
        return _render_room(
            _intake_room(
                "member",
                text=raw_text if isinstance(raw_text, str) else "",
                replace=replace,
                error=_field_error(
                    "We couldn't use that role text.",
                    error.code,
                    f"Session private • {TRUTH_NOTHING_SAVED}",
                ),
            ),
            status=400,
        )

    try:
        opportunity_slate_service.save_source_for_owner(
            identity.user_key, idempotency_key, clean_text
        )
    except DatabaseServiceError:
        return _render_unavailable(text=clean_text)
    except OpportunitySlateServiceError as error:
        return _render_room(
            _intake_room(
                "member",
                text=clean_text,
                replace=replace,
                error=_field_error(
                    "We couldn't capture that role.",
                    error.code,
                    f"Session private • {TRUTH_NOTHING_SAVED}",
                ),
            ),
            status=409 if error.code == "changed" else 400,
        )

    return redirect(url_for("opportunity_slate.room"))


def _reload_review_for_error(
    identity, *, editor_text, message, heading, status, field_hint=None
):
    """Re-render Review Source with the member's own wording intact.

    A failed correction must never cost the member their typing. When the
    current server state can still be read, it is used; when it cannot, the
    truthful 503 is returned instead of a guessed page.
    """
    try:
        working = opportunity_slate_service.get_working_session_for_owner(
            identity.user_key
        )
    except (DatabaseServiceError, OpportunitySlateServiceError):
        return _render_unavailable(text=editor_text)
    if working is None:
        return _render_room(_intake_room("member", text=editor_text))
    return _render_room(
        _review_room_from_view(
            working,
            editing=True,
            editor_text=editor_text,
            error={
                "kind": "field",
                "heading": heading,
                "message": message,
                "field_hint": field_hint,
                "truth": f"Session private • {TRUTH_NOTHING_SAVED}",
            },
        ),
        status=status,
    )


@opportunity_slate.post(f"{ROOM_PATH}/source/corrections")
def correct_source():
    """Apply the member's manual correction of the captured wording."""
    if not _opportunity_slate_enabled():
        abort(404)
    if not _is_same_origin_write():
        abort(403)
    identity, failure = _resolve_identity_or_unavailable()
    if failure is not None:
        return failure
    if identity is None:
        abort(404)

    raw_text = request.form.get("corrected_text", "")
    source_key = request.form.get("source_key")
    version_token = request.form.get("version_token")
    editor_text = raw_text if isinstance(raw_text, str) else ""

    try:
        opportunity_slate_service.correct_source_for_owner(
            identity.user_key, source_key, version_token, raw_text
        )
    except DatabaseServiceError:
        return _reload_review_for_error(
            identity,
            editor_text=editor_text,
            heading="We couldn't apply that correction.",
            message=UNAVAILABLE_MESSAGE,
            status=503,
        )
    except OpportunitySlateServiceError as error:
        if error.code == "changed":
            return _reload_review_for_error(
                identity,
                editor_text=editor_text,
                heading="This role source changed.",
                message=CONFLICT_MESSAGE,
                field_hint="Review the wording below and apply it again.",
                status=409,
            )
        return _reload_review_for_error(
            identity,
            editor_text=editor_text,
            heading="We couldn't use that wording.",
            message=FIELD_ERROR_MESSAGES.get(error.code, DEFAULT_FIELD_ERROR),
            field_hint=FIELD_ERROR_HINTS.get(error.code, DEFAULT_FIELD_HINT),
            status=400,
        )

    return redirect(url_for("opportunity_slate.room"))


@opportunity_slate.post(f"{ROOM_PATH}/source/confirm")
def confirm_source():
    """Checkpoint 1 of 2. Records which source version the member accepted.

    It saves no slate, publishes nothing, and calls no AI.
    """
    if not _opportunity_slate_enabled():
        abort(404)
    if not _is_same_origin_write():
        abort(403)
    identity, failure = _resolve_identity_or_unavailable()
    if failure is not None:
        return failure
    if identity is None:
        abort(404)

    try:
        opportunity_slate_service.confirm_source_for_owner(
            identity.user_key,
            request.form.get("source_key"),
            request.form.get("version_token"),
        )
    except DatabaseServiceError:
        return _reload_review_for_error(
            identity,
            editor_text=request.form.get("display_text", ""),
            heading="We couldn't confirm this source.",
            message=UNAVAILABLE_MESSAGE,
            status=503,
        )
    except OpportunitySlateServiceError as error:
        return _reload_review_for_error(
            identity,
            editor_text=request.form.get("display_text", ""),
            heading="This role source changed.",
            message=(
                CONFLICT_MESSAGE
                if error.code == "changed"
                else FIELD_ERROR_MESSAGES.get(error.code, DEFAULT_FIELD_ERROR)
            ),
            status=409 if error.code == "changed" else 400,
        )

    return redirect(url_for("opportunity_slate.room"))


@opportunity_slate.post(f"{ROOM_PATH}/source/delete")
def delete_source():
    """The member's explicit discard of the whole working session."""
    if not _opportunity_slate_enabled():
        abort(404)
    if not _is_same_origin_write():
        abort(403)
    identity, failure = _resolve_identity_or_unavailable()
    if failure is not None:
        return failure
    if identity is None:
        abort(404)

    try:
        opportunity_slate_service.delete_working_session_for_owner(
            identity.user_key,
            request.form.get("session_key"),
            request.form.get("session_version_token"),
        )
    except DatabaseServiceError:
        return _reload_review_for_error(
            identity,
            editor_text="",
            heading="We couldn't delete this role source.",
            message=(
                "It is still here, exactly as you left it. Nothing was removed."
            ),
            status=503,
        )
    except OpportunitySlateServiceError as error:
        return _reload_review_for_error(
            identity,
            editor_text="",
            heading="We couldn't delete this role source.",
            message=(
                CONFLICT_MESSAGE
                if error.code == "changed"
                else "It is still here, exactly as you left it. Nothing was removed."
            ),
            status=409 if error.code == "changed" else 400,
        )

    return redirect(url_for("opportunity_slate.room"))


@opportunity_slate.post(f"{ROOM_PATH}/public-session")
def public_session():
    """The anonymous public session's single transport (handoff section 18).

    Reads a signed context token out of the request body, applies one
    member-directed action to it in memory, and returns the re-rendered room
    plus a fresh token. It imports no persistence method and calls no stored
    procedure, so the public boundary cannot reach member data even by
    mistake. A signed-in caller gets the neutral 404 they would get for any
    other wrong-mode request; the browser then reloads into the real
    workbench.
    """
    if not _opportunity_slate_enabled():
        abort(404)
    if not _is_same_origin_write():
        abort(403)
    identity, failure = _resolve_identity_or_unavailable()
    if failure is not None:
        return failure
    if identity is not None:
        return jsonify({"success": False, "message": "Not found."}), 404

    body = _public_json_body()
    if body is None:
        return (
            jsonify({"success": False, "message": "We couldn't read that request."}),
            400,
        )

    action = body.get("action")
    if action not in _PUBLIC_ACTIONS:
        return (
            jsonify({"success": False, "message": "We couldn't read that request."}),
            400,
        )

    requested_step = body.get("step")
    if requested_step not in _ALLOWED_STEPS:
        requested_step = None

    context = _load_public_context(body.get("context_token"))

    if action == "discard" or (action == "render" and context is None):
        room = _intake_room("public")
        return jsonify(
            {
                "success": True,
                "reset": True,
                "step": STEP_ROLE,
                "html": _render_fragment(room),
                "context_token": None,
            }
        )

    if action == "source":
        try:
            clean_text = validate_source_text(body.get("source_text"))
        except OpportunitySlateServiceError as error:
            room = _intake_room(
                "public",
                text=body.get("source_text") if isinstance(body.get("source_text"), str) else "",
                replace=requested_step == STEP_REPLACE,
                error=_field_error(
                    "We couldn't use that role text.",
                    error.code,
                    "Public session • Nothing is stored.",
                ),
            )
            return (
                jsonify(
                    {
                        "success": False,
                        "step": STEP_ROLE,
                        "html": _render_fragment(
                            room, context_token=body.get("context_token")
                        ),
                    }
                ),
                400,
            )
        version = 1
        if context is not None and context["text"] != clean_text:
            version = min(context["version"] + 1, 50)
        elif context is not None:
            version = context["version"]
        context = {
            "v": PUBLIC_CONTEXT_VERSION,
            "text": clean_text,
            "corrected": None,
            "version": version,
            "confirmed": False,
        }

    elif action == "correct":
        if context is None:
            return _public_reset_response()
        try:
            clean_text = validate_source_text(
                body.get("corrected_text"), label="corrected wording"
            )
        except OpportunitySlateServiceError as error:
            room = _review_room_from_context(
                context,
                editing=True,
                editor_text=body.get("corrected_text")
                if isinstance(body.get("corrected_text"), str)
                else "",
                error=_field_error(
                    "We couldn't use that wording.",
                    error.code,
                    "Public session • Nothing is stored.",
                ),
            )
            return (
                jsonify(
                    {
                        "success": False,
                        "step": STEP_REVIEW,
                        "html": _render_fragment(
                            room, context_token=body.get("context_token")
                        ),
                    }
                ),
                400,
            )
        context = dict(context)
        context["corrected"] = None if clean_text == context["text"] else clean_text
        context["confirmed"] = False

    elif action == "confirm":
        if context is None:
            return _public_reset_response()
        context = dict(context)
        context["confirmed"] = True

    if context is None:
        return _public_reset_response()

    if requested_step in {STEP_ROLE, STEP_REPLACE}:
        room = _intake_room(
            "public",
            text="" if requested_step == STEP_REPLACE else (context.get("corrected") or context["text"]),
            replace=requested_step == STEP_REPLACE,
            has_source=True,
        )
        step = requested_step
    else:
        room = _review_room_from_context(context)
        step = STEP_REVIEW

    token = _dump_public_context(context)
    return jsonify(
        {
            "success": True,
            "reset": False,
            "step": step,
            "html": _render_fragment(room, context_token=token),
            "context_token": token,
        }
    )


def _public_reset_response():
    """Honest reset: the held state is gone or unreadable, so the visitor
    starts again at role intake. Never a fabricated session."""
    return jsonify(
        {
            "success": True,
            "reset": True,
            "step": STEP_ROLE,
            "html": _render_fragment(_intake_room("public")),
            "context_token": None,
            "message": (
                "This public session has ended. Nothing was stored — paste the "
                "role text again to start over."
            ),
        }
    )
