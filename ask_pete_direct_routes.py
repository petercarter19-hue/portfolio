"""The private recruiter-question path: one public write, one owner inbox.

PS-ASK-PETE-DIRECT-001.

READ THIS FIRST: REGISTERED, AND OFF.
------------------------------------
``app.py`` registers this blueprint (registration leg, 2026-08-08, after
PS-INTERVIEW-STUDIO-FUNCTIONAL-V1-001 closed and released that file). It is
registered UNCONDITIONALLY, on purpose: the gate belongs in ``before_request``
below, not in the registration. That is what makes "off" mean a neutral 404
from a route that exists — indistinguishable from any other 404, flippable
without a redeploy, and identical for a cross-site caller and a same-origin
one.

The only thing standing between this code and a visitor is now the flag:

``PEERSLATE_ASK_PETE_DIRECT_ENABLED`` defaults false and is read with
``is True`` rather than truthiness, so a stray ``"false"`` string, a ``1``, or
any other truthy object cannot open it. Turning it on additionally requires
``PEERSLATE_OWNER_USER_KEYS`` to name exactly one key and the migration to be
applied; short of that the path answers an honest 503 rather than guessing a
recipient. Enablement is the owner's decision.

Rate limiting, and why it is declared here but applied there
------------------------------------------------------------
It cannot be wired from this file. ``app.py`` owns the ``Limiter`` instance,
and the house idiom is to wrap the view function AFTER blueprint registration
(see the ``community_api`` and Opportunity Slate loops there) precisely so a
reusable blueprint never imports that module back. ``PLANNED_RATE_LIMITS``
below states the budgets, and ``app.py`` iterates that mapping rather than
restating it, so the declaration and the application cannot drift. A test
asserts the mapping covers every state-changing endpoint here, so a route
added later without a budget fails the suite instead of shipping unbounded.
No parallel limiter is invented in this file: a second, unrelated counter
would be a different control with different behaviour that nobody operates.

Trust boundaries this file keeps
--------------------------------
* The sender is anonymous. No identity is derived, stored, or inferred for
  them, and the recipient is read from server-side configuration - never from
  the request - so nobody can address a question into another member's inbox.
* Consent is required, is checked here, and is checked again by the stored
  procedure. Nothing is stored without it.
* Sending is never automatic and never replies. There is no outbound channel
  in this package at all.
* The owner inbox is ``@owner_required`` on the page AND on the action, and it
  can change a question's status but never delete one.
"""

from __future__ import annotations

from types import MappingProxyType

from flask import (
    Blueprint,
    abort,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_limiter.errors import RateLimitExceeded
from werkzeug.exceptions import RequestEntityTooLarge

from owner_authorization import owner_required, owner_user_keys, resolve_owner
from services.ask_pete_direct_service import (
    MAX_IDEMPOTENCY_UNITS,
    AskPeteDirectError,
    ask_pete_direct_service,
    utf16_length,
)
from services.database_service import DatabaseServiceError


ask_pete_direct = Blueprint("ask_pete_direct", __name__)

# Paths are written out rather than built with url_for because
# templates/partials/ask_pete_evidence_companion.html has to name the endpoint
# while the blueprint is unregistered, and url_for would raise BuildError there.
# tests/ask_pete_direct/test_endpoint.py asserts the two spellings match.
DIRECT_QUESTION_PATH = "/api/ask-pete/direct-question"
DIRECT_QUESTION_ENDPOINT = "ask_pete_direct.submit_direct_question"

# The owner inbox lives under /owner/, beside the Control Room, rather than
# under /app/ as the package brief sketched: /app/ is the per-MEMBER namespace
# (every signed-in member owns what is there), and this surface is site-owner
# only. Recorded as a deliberate deviation in the package README.
OWNER_INBOX_PATH = "/owner/ask-pete-inbox"
OWNER_INBOX_STATUS_PATH = "/owner/ask-pete-inbox/<string:question_key>/status"
OWNER_INBOX_ENDPOINT = "ask_pete_direct.owner_inbox"
OWNER_INBOX_STATUS_ENDPOINT = "ask_pete_direct.set_question_status"

# A question is 2000 UTF-16 units and a contact line 300; 16 KiB leaves room
# for the JSON envelope and multi-byte text while keeping the body bounded well
# below the application default.
MAX_DIRECT_QUESTION_BYTES = 16 * 1024

# A field no real sender ever sees: aria-hidden, out of the tab order, and
# empty. Anything in it means the submission was not made by the form.
HONEYPOT_FIELD = "company_website"

# Exactly the keys the endpoint accepts. An unexpected key is refused rather
# than ignored, the same discipline community_api applies to Voice's form
# fields: silently dropping a field a caller believed mattered is a worse
# answer than saying no.
ALLOWED_QUESTION_FIELDS = frozenset({"question", "contact", "consent", HONEYPOT_FIELD})

# The budgets the app.py registration leg must apply with the post-registration
# limiter-wrapper idiom. 30/hour per client is the house floor for a
# state-changing write endpoint (community_api.publish_post and friends).
PLANNED_RATE_LIMITS = MappingProxyType(
    {
        DIRECT_QUESTION_ENDPOINT: "30 per hour",
        # The owner's own read/archive actions. Bounded like any other write,
        # but roomier: a member working through a backlog legitimately presses
        # these many times in a row.
        OWNER_INBOX_STATUS_ENDPOINT: "60 per hour",
    }
)

# What the inbox says after an action, keyed by the state the redirect carries.
# The keys are the only values the page will echo, so nothing a caller puts in
# the query string can reach the rendered page.
INBOX_NOTICES = MappingProxyType(
    {
        "new": "Moved back to unread.",
        "read": "Marked as read.",
        "archived": "Archived. It stays here under Show archived; nothing is deleted.",
        "changed": "That question changed before your action. Nothing was altered - this is the current state.",
        "unavailable": "That action could not be completed. Nothing was altered.",
    }
)

_JSON_ENDPOINTS = frozenset({DIRECT_QUESTION_ENDPOINT})


class AskPeteDirectUnavailable(RuntimeError):
    """The path is configured on but cannot honestly accept a question."""


def _enabled():
    """``is True`` on purpose: fail closed for any non-boolean value."""
    return current_app.config.get("PEERSLATE_ASK_PETE_DIRECT_ENABLED", False) is True


def _configured_recipient_user_key():
    """The one member questions are addressed to, from server configuration.

    Reuses the Control Room owner allowlist rather than adding a second knob,
    which also guarantees the recipient of a question is exactly the identity
    that can open the inbox and read it. Fail closed on both edges: zero
    configured keys means nobody can be written to, and more than one means the
    recipient is ambiguous - and guessing which member a stranger's question
    belongs to is not a decision this code may make.

    Returns ``None`` when the path cannot honestly accept a question. An
    email-only owner allowlist is one such case, and is called out in
    .env.example: the direct path needs the opaque user key, not an address.
    """
    keys = owner_user_keys()
    if len(keys) != 1:
        return None
    return next(iter(keys))


def _not_found():
    """A neutral 404 in the shape the caller asked for."""
    if request.endpoint in _JSON_ENDPOINTS:
        return jsonify(success=False, message="Not found."), 404
    abort(404)


def _is_same_origin_write():
    """Fail-closed same-origin proof for a real HTML form post.

    Mirrors ``owner_routes._is_same_origin_write`` / the identical Workshop
    helper exactly: a browser form cannot set a custom header, so ``Origin``
    and ``Sec-Fetch-Site`` are all there is - and a request carrying NEITHER is
    treated as untrusted rather than allowed.
    """
    expected_origin = request.host_url.rstrip("/")
    origin = request.headers.get("Origin")
    fetch_site = request.headers.get("Sec-Fetch-Site")
    if origin and origin.rstrip("/") != expected_origin:
        return False
    if fetch_site and fetch_site not in {"same-origin", "none"}:
        return False
    return bool(origin or fetch_site)


@ask_pete_direct.before_request
def protect_direct_question_path():
    if not _enabled():
        return _not_found()

    if request.endpoint == DIRECT_QUESTION_ENDPOINT:
        # Flask allows a route-specific override; every unrelated endpoint in
        # the application keeps its own ceiling untouched.
        request.max_content_length = MAX_DIRECT_QUESTION_BYTES

    if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return None

    if request.endpoint in _JSON_ENDPOINTS:
        if request.headers.get("X-PeerSlate-Request") != "same-origin":
            return (
                jsonify(
                    success=False,
                    message="A same-origin request header is required.",
                ),
                403,
            )
        origin = request.headers.get("Origin")
        if origin and origin.rstrip("/") != request.host_url.rstrip("/"):
            return (
                jsonify(success=False, message="Cross-origin writes are not allowed."),
                403,
            )
        fetch_site = request.headers.get("Sec-Fetch-Site")
        if fetch_site and fetch_site not in {"same-origin", "none"}:
            return (
                jsonify(success=False, message="Cross-site writes are not allowed."),
                403,
            )
        if not request.is_json:
            return (
                jsonify(success=False, message="Write requests must use JSON."),
                415,
            )
        return None

    # HTML form post from the owner inbox.
    if not _is_same_origin_write():
        return "Cross-site requests are not allowed.", 403
    return None


@ask_pete_direct.after_request
def secure_direct_question_response(response):
    """Defence in depth. The flag, the owner check, and the same-origin proof
    are the access controls; these keep the surface out of caches and
    indexes."""
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


_VALIDATION_CODES = frozenset({"required", "too_long", "invalid", "consent_required"})


def _html_failure(error):
    """The owner inbox is a server-rendered page, not an API.

    Its two routes handle their own failures inline so they can re-render or
    redirect, and this exists only so that an unforeseen escape produces a
    plain, payload-free 503 rather than a JSON body in an HTML surface.
    """
    current_app.logger.error("Ask Pete inbox failed (code=%s).", getattr(error, "code", "unknown"))
    return "The recruiter question inbox is unavailable right now.", 503


@ask_pete_direct.errorhandler(AskPeteDirectError)
def direct_question_error(error):
    """One place maps a service code to a status and a sender-safe message.

    The service's own messages are written for a sender to read and carry no
    database, procedure, or configuration detail, so they are passed through
    for the validation codes. Everything else answers with a fixed sentence.
    """
    if request.endpoint not in _JSON_ENDPOINTS:
        return _html_failure(error)
    if error.code in _VALIDATION_CODES:
        return jsonify(success=False, code=error.code, message=str(error)), 422
    if error.code == "changed":
        return (
            jsonify(
                success=False,
                code="changed",
                message="That question changed before this update. Reload the inbox.",
            ),
            409,
        )
    # not_found here means the CONFIGURED recipient did not resolve, and
    # no_identity means no recipient is configured at all. Both are the
    # deployment's problem, not the sender's, and in both cases nothing was
    # stored - so the honest answer is "unavailable", never "sent".
    current_app.logger.error(
        "Ask Pete direct question unavailable (code=%s).", error.code
    )
    return (
        jsonify(
            success=False,
            code="unavailable",
            message="Sending a question to Pete directly is unavailable right now.",
        ),
        503,
    )


@ask_pete_direct.errorhandler(AskPeteDirectUnavailable)
def direct_question_unavailable(error):
    current_app.logger.error("Ask Pete direct question has no configured recipient.")
    return (
        jsonify(
            success=False,
            code="unavailable",
            message="Sending a question to Pete directly is unavailable right now.",
        ),
        503,
    )


@ask_pete_direct.errorhandler(DatabaseServiceError)
def direct_question_database_error(error):
    current_app.logger.error("Ask Pete direct question storage failed.")
    return (
        jsonify(
            success=False,
            code="unavailable",
            message="Sending a question to Pete directly is unavailable right now.",
        ),
        503,
    )


@ask_pete_direct.errorhandler(RequestEntityTooLarge)
def direct_question_too_large(error):
    return jsonify(success=False, code="too_long", message="That request is too large."), 413


@ask_pete_direct.errorhandler(RateLimitExceeded)
def direct_question_rate_limited(error):
    """Registered so the limit the registration leg applies answers in this
    blueprint's own shape rather than the application's HTML default."""
    return (
        jsonify(
            success=False,
            code="rate_limited",
            message="Too many questions from this connection. Try again later.",
        ),
        429,
    )


def _json_object():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise AskPeteDirectError(
            "The request body must be a JSON object.", code="invalid"
        )
    return body


def _idempotency_key():
    """Required, not optional.

    Without it a double-tapped Send would store two copies of the same
    question, which is exactly what the consent line's "you can send this once"
    reading promises it will not do. Refusing is honest; silently generating a
    server-side key would keep the request working while quietly removing the
    guarantee.
    """
    value = request.headers.get("Idempotency-Key")
    if not isinstance(value, str) or not value.strip():
        raise AskPeteDirectError(
            "This request is missing its Idempotency-Key header.", code="required"
        )
    value = value.strip()
    if utf16_length(value) > MAX_IDEMPOTENCY_UNITS:
        raise AskPeteDirectError(
            "This request's Idempotency-Key header is too long.", code="too_long"
        )
    return value


@ask_pete_direct.post(DIRECT_QUESTION_PATH)
def submit_direct_question():
    """Store one privately sent question. Never sends, replies, or publishes.

    The ladder, in order, each rung refusing before the next runs: the flag and
    the same-origin proof (``before_request``); a present, bounded
    Idempotency-Key; a JSON object body; no unexpected field; an untouched
    honeypot; a present, typed, non-empty, bounded question; a typed, bounded
    contact; and consent that is exactly ``True``. Only then is anything
    stored, and only through the allowlisted procedure.
    """
    idempotency_key = _idempotency_key()
    body = _json_object()

    unexpected = set(body) - ALLOWED_QUESTION_FIELDS
    if unexpected:
        raise AskPeteDirectError(
            "This request carries fields this form does not accept.", code="invalid"
        )

    # Honeypot. A real sender never sees this field (it is aria-hidden and out
    # of the tab order), so anything in it means the submission was not made by
    # the form. It is refused with the same generic validation answer as any
    # other malformed request rather than a silent fake success: telling a
    # sender their question was sent when it was not would be a lie even when
    # the "sender" is a script.
    if str(body.get(HONEYPOT_FIELD) or "").strip():
        current_app.logger.info("Ask Pete direct question refused by honeypot.")
        raise AskPeteDirectError(
            "This question could not be accepted as written.", code="invalid"
        )

    recipient_user_key = _configured_recipient_user_key()
    if recipient_user_key is None:
        raise AskPeteDirectUnavailable("No recipient is configured.")

    result = ask_pete_direct_service.submit_question(
        recipient_user_key,
        idempotency_key,
        body.get("question"),
        body.get("contact"),
        body.get("consent"),
    )

    already_sent = result["state"] == "already_sent"
    return (
        jsonify(
            success=True,
            state=result["state"],
            consent_version=result["consent_version"],
            message=(
                "That question was already sent. Pete reads these on his own "
                "schedule."
                if already_sent
                else "Sent to Pete privately. He reads these on his own schedule, "
                "and replies himself if he has something useful to say."
            ),
        ),
        200 if already_sent else 201,
    )


# ---------------------------------------------------------------------------
# The owner inbox. Pull-based on purpose: this package adds no outbound
# channel of any kind, so there is nothing to notify with and nothing that
# could send on the member's behalf. They come and look.
# ---------------------------------------------------------------------------


def _owner_or_404():
    """``owner_required`` has already run; this re-reads the resolved owner.

    It returns ``None`` only if identity resolution changed between the two
    calls, which cannot normally happen (the identity is cached on ``g``). It
    is handled anyway, closed, rather than assumed away.
    """
    owner = resolve_owner()
    if owner is None or not getattr(owner, "user_key", None):
        abort(404)
    return owner


def _owner_label(owner):
    return (
        getattr(owner, "display_name", None)
        or getattr(owner, "email", None)
        or "Owner"
    )


@ask_pete_direct.get(OWNER_INBOX_PATH)
@owner_required
def owner_inbox():
    """Every question sent to this member, newest first. Read-only in itself.

    ``@owner_required`` answers a bare 404 for everyone else - unauthenticated,
    authenticated non-owner, and an identity that cannot be resolved because
    storage is down. Applied here AND on the action below, never on the page
    alone.
    """
    owner = _owner_or_404()
    include_archived = request.args.get("archived") == "1"
    # Only a key of the fixed notice table can be echoed, so nothing a caller
    # puts in the query string reaches the page.
    notice = INBOX_NOTICES.get(request.args.get("state"))

    try:
        result = ask_pete_direct_service.list_questions_for_owner(
            owner.user_key, include_archived=include_archived
        )
    except AskPeteDirectError as error:
        current_app.logger.error(
            "Ask Pete inbox read failed (code=%s).", error.code
        )
        # The blueprint's own after_request hardens every response here, so
        # there is no separate _harden step to forget on one branch.
        return (
            render_template(
                "ask_pete_inbox.html",
                owner_label=_owner_label(owner),
                questions=[],
                total_count=0,
                new_count=0,
                include_archived=include_archived,
                notice=notice,
                unavailable=True,
            ),
            503,
        )

    return render_template(
        "ask_pete_inbox.html",
        owner_label=_owner_label(owner),
        questions=result.items,
        total_count=result.total_count,
        new_count=result.new_count,
        include_archived=include_archived,
        notice=notice,
        unavailable=False,
    )


@ask_pete_direct.post(OWNER_INBOX_STATUS_PATH)
@owner_required
def set_question_status(question_key):
    """Mark read, archive, or move back to unread. There is no delete action
    because there is no delete procedure: archiving is the only removal v1
    offers, and it is reversible.

    A plain HTML form post, so the same-origin proof is ``before_request``'s
    fail-closed Origin/Sec-Fetch-Site check rather than a custom header a form
    cannot send. Post/redirect/get, so a refresh never repeats the action.
    """
    owner = _owner_or_404()
    include_archived = request.form.get("archived") == "1"

    try:
        result = ask_pete_direct_service.set_question_status_for_owner(
            owner.user_key,
            question_key,
            request.form.get("status"),
            request.form.get("expected_version"),
        )
        state = result["status"]
    except AskPeteDirectError as error:
        current_app.logger.error(
            "Ask Pete inbox status change refused (code=%s).", error.code
        )
        state = "changed" if error.code == "changed" else "unavailable"

    arguments = {"state": state}
    if include_archived:
        arguments["archived"] = "1"
    return redirect(url_for(OWNER_INBOX_ENDPOINT, **arguments))
