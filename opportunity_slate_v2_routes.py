"""Opportunity Slate REPLACEMENT room routes — PS-OPPORTUNITY-SLATE-002,
slice R1 (shell + stage-1 intake + stage-2 captured-source review).

Package: docs/initiatives/PS-OPPORTUNITY-SLATE-002. Controlling contract:
artifacts/2026-08-11-opportunity-slate-architecture/
OPPORTUNITY_SLATE_ARCHITECTURE.md, sections 2 (product model), 3 (shell,
navigation, access), 4.1-4.2 (visual lock -> contract map), 6.1 (source
capture), 6.6 (working-opportunity lifetime), 6.10 (authorization
boundaries), 6.11 (cancellation), 9 (route contract).

**This blueprint is never registered by app.py in R1.** Section 9's
target design has app.py register exactly one of (legacy blueprint, v2
blueprint) at ``/opportunity-slate`` based on
``PEERSLATE_OPPORTUNITY_SLATE_V2_ENABLED``; wiring that in is explicitly out
of this slice's lane (another active lane owns app.py). Every route below
still re-checks the flag internally, so the module is correct and testable
standalone today and requires no route-body change when a later slice wires
the registration. Tests build their own throwaway Flask app that registers
this blueprint directly (mirrors ``tests/ask_pete_direct/support.py``, the
established pattern for a blueprint app.py does not register).

**Sign-in only, no anonymous mode.** Owner decision 2026-08-11: the
replacement drops the legacy room's dual-mode (anonymous + member) design
entirely. Every route resolves identity with ``identity.get_current_identity``;
an anonymous caller is redirected to sign-in with a return target — never a
partial page, never a 404-as-privacy-signal, on every endpoint including
mutations (architecture section 3 and section 14's R1 test plan: "anonymous
-> sign-in redirect on every v2 endpoint").

**R1 has two stages only.** Bring in a role (image 04) and Review captured
source (image 05). No requirement interpretation, no alignment, no save —
building any of those now is explicitly out of scope for this slice.

**No AI call anywhere in this file**, and no import of an AI-capable
module. ``services/opportunity_slate_v2_service`` carries the same
guardrail; the two together are why the no-AI-import test can check both
files. Upload and public-link import reuse
``services/opportunity_source_intake_service`` completely unchanged
(architecture section 9): MIME allowlist, magic bytes, bounded read,
structure-only parsing for upload; https-only, public-unicast IP pinning,
redirect re-validation, size/time caps for import.

``_is_same_origin_write`` mirrors ``opportunity_slate_routes._is_same_origin_write``
(itself mirroring ``workshop_routes._is_same_origin_write``) exactly, and is
duplicated locally for the same file-ownership reason those modules give.

Rate limiting, and why it is declared here but applied there
--------------------------------------------------------------
It cannot be wired from this file. ``app.py`` owns the ``Limiter`` instance,
and the house idiom is to wrap each view function AFTER blueprint registration
(``app.py``'s ``community_api`` / ``ask_pete_direct`` / legacy Opportunity
Slate loops). ``PLANNED_RATE_LIMITS`` below states the budget for
every mutation on this blueprint, and the future registration leg iterates
that mapping rather than restating it, so the declaration and the
application cannot drift. A test asserts the mapping covers every
state-changing endpoint here (mirrors
``tests.ask_pete_direct.test_endpoint.RateLimitPlanTests``), so a route added
later without a budget fails the suite instead of shipping unbounded the
moment a later slice wires registration. No parallel limiter is invented in
this file — a second, unrelated counter would be a different control with
different behaviour that nobody operates. Today the blueprint is both
unregistered and flag-default-false, so there is no live exposure either way
(independent review finding).
"""

from types import MappingProxyType
from uuid import uuid4

from flask import (
    Blueprint,
    abort,
    current_app,
    make_response,
    redirect,
    render_template,
    request,
    url_for,
)

from identity import AuthenticationRequired, get_current_identity
from services.database_service import DatabaseServiceError
from services.opportunity_slate_v2_service import (
    MAX_IDENTITY_FIELD_UNITS,
    MAX_SOURCE_TEXT_UNITS,
    OpportunitySlateV2ServiceError,
    opportunity_slate_v2_service,
    validate_source_text,
)
from services.opportunity_source_intake_service import (
    MAX_UPLOAD_BYTES,
    OpportunitySourceIntakeError,
    extract_imported_link,
    extract_uploaded_document,
)


opportunity_slate_v2 = Blueprint("opportunity_slate_v2", __name__)

# Section 3: "Route stays /opportunity-slate." This blueprint is not
# registered anywhere in R1, so no path collision with the live legacy
# blueprint is possible today; the name is forward-looking for R5.
ROOM_PATH = "/opportunity-slate"

STEP_REPLACE = "replace"
_ALLOWED_STEPS = frozenset({STEP_REPLACE})

TRUTH_NO_CAPTURE = "No new source was captured or analyzed."
TRUTH_ATTEMPT_UNKNOWN = (
    "We could not verify whether the last change reached storage. Your "
    "attempted values remain on this page; reload the stored version before "
    "deciding whether to retry."
)

UNAVAILABLE_MESSAGE = (
    "We couldn't reach your Opportunity Slate workroom. Its stored state "
    "could not be verified — try again in a moment."
)
CONFLICT_MESSAGE = (
    "This role source changed since you last saw it. Review the current "
    "wording and try again."
)

FIELD_ERROR_MESSAGES = {
    "required": "Add the role text before continuing.",
    "too_long": f"That text is longer than {MAX_SOURCE_TEXT_UNITS:,} characters.",
    "invalid": "That entry could not be used as written.",
}
DEFAULT_FIELD_ERROR = "That entry could not be used as written."

# save_identity()'s own error-code -> message map. It cannot share
# FIELD_ERROR_MESSAGES: that map's "too_long" names MAX_SOURCE_TEXT_UNITS
# (20,000, the captured-wording cap), but save_source_identity_for_owner
# bounds Employer/Role title at MAX_IDENTITY_FIELD_UNITS (200) — reusing
# the source-text copy there told a member "longer than 20,000 characters"
# about a 200-character field (independent review finding). Server-side
# enforcement was never affected; only the message the member reads was.
IDENTITY_FIELD_ERROR_MESSAGES = {
    "required": "Add the employer or role title before continuing.",
    "too_long": f"That text is longer than {MAX_IDENTITY_FIELD_UNITS:,} characters.",
    "invalid": "That entry could not be used as written.",
}

UPLOAD_FAILURE_HEADING = "We couldn't read this document."
UPLOAD_FAILURE_MESSAGE = (
    "The file may be an unsupported type, unreadable, or larger than the "
    "upload limit. Nothing was captured — try again or paste the wording "
    "instead."
)
IMPORT_FAILURE_HEADING = "We couldn't import that link."
IMPORT_FAILURE_MESSAGE = (
    "The page may not be publicly reachable, may be too large, or the "
    "request may have timed out. Nothing was captured — try again or paste "
    "the wording instead."
)

NOTICE_UPLOAD_TRUNCATED = "upload-truncated"
NOTICE_IMPORT_TRUNCATED = "import-truncated"
_NOTICE_COPY = {
    NOTICE_UPLOAD_TRUNCATED: (
        "The uploaded document was longer than PeerSlate can capture, so the "
        "wording below was shortened. Review it and correct anything that "
        "matters before confirming."
    ),
    NOTICE_IMPORT_TRUNCATED: (
        "The imported page was longer than PeerSlate can capture, so the "
        "wording below was shortened. Review it and correct anything that "
        "matters before confirming."
    ),
}

# The budgets the future app.py registration leg must apply with the same
# post-registration limiter-wrapper idiom app.py already uses for
# community_api / ask_pete_direct / the legacy Opportunity Slate blueprint.
# R1 has no AI-calling route (architecture section 7 is entirely R2+), so
# every mutation shares one floor: the same non-AI write budget the legacy
# room's own set_source/correct_source/confirm_source/delete_source already
# carry in app.py's PS-OPPSLATE-001 loop ("30 per minute"). Declared here,
# applied there — see the module docstring's "Rate limiting" section.
PLANNED_RATE_LIMITS = MappingProxyType(
    {
        "opportunity_slate_v2.set_source": "30 per minute",
        "opportunity_slate_v2.upload_source": "30 per minute",
        "opportunity_slate_v2.import_source": "30 per minute",
        "opportunity_slate_v2.save_identity": "30 per minute",
        "opportunity_slate_v2.correct_source": "30 per minute",
        "opportunity_slate_v2.confirm_source": "30 per minute",
        "opportunity_slate_v2.delete_source": "30 per minute",
    }
)


def _field_error(heading, code, *, truth=None, messages=None):
    lookup = messages if messages is not None else FIELD_ERROR_MESSAGES
    return {
        "kind": "field",
        "heading": heading,
        "message": lookup.get(code, DEFAULT_FIELD_ERROR),
        "truth": truth or f"Session private • {TRUTH_NO_CAPTURE}",
        "recovery_url": url_for("opportunity_slate_v2.room"),
        "recovery_label": "Reload the stored version",
    }


def _opportunity_slate_v2_enabled():
    return (
        current_app.config.get("PEERSLATE_OPPORTUNITY_SLATE_V2_ENABLED", False)
        is True
    )


@opportunity_slate_v2.before_request
def _allow_bounded_document_upload():
    """Override the small global form limit for the one route that accepts
    a file (mirrors ``opportunity_slate_routes._allow_bounded_document_upload``
    and, before it, ``owner_routes._allow_bounded_voice_upload``).

    Every other route on this blueprint stays under the app-wide 2 MB
    ``MAX_CONTENT_LENGTH``.
    """
    if request.endpoint == "opportunity_slate_v2.upload_source":
        request.max_content_length = MAX_UPLOAD_BYTES + (64 * 1024)


def _is_same_origin_write():
    """Allow a state-changing request only when it proves same origin.

    A request carrying neither ``Origin`` nor ``Sec-Fetch-Site`` is treated
    as untrusted rather than allowed, because these routes include real
    no-JS HTML form posts.
    """
    expected_origin = request.host_url.rstrip("/")
    origin = request.headers.get("Origin")
    fetch_site = request.headers.get("Sec-Fetch-Site")
    if origin and origin.rstrip("/") != expected_origin:
        return False
    if fetch_site and fetch_site not in {"same-origin", "none"}:
        return False
    return bool(origin or fetch_site)


def _safe_return_path(candidate, default=None):
    """Same-origin-only return target for the sign-in redirect.

    Mirrors ``workshop_routes._safe_return_path`` exactly: a scheme,
    host, or ``//``/backslash-prefixed candidate is never trusted, because
    an open redirect through ``return_to`` would defeat the whole point of
    a same-origin check elsewhere in this file.
    """
    fallback = default or ROOM_PATH
    if not candidate or not isinstance(candidate, str):
        return fallback
    if not candidate.startswith("/") or candidate.startswith("//"):
        return fallback
    if "\\" in candidate or "://" in candidate:
        return fallback
    return candidate


@opportunity_slate_v2.after_request
def _apply_room_headers(response):
    """Private, unstorable, and unindexed on every response.

    Retained deliberately even though R1 is never live: private workroom
    content must never be cacheable or indexable the moment it is
    (architecture section 3).
    """
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive"
    return response


def _resolve_identity_or_gate():
    """``(identity, failure_response)``.

    Every route on this blueprint calls this first (after the flag and
    same-origin checks). An anonymous caller is redirected to sign-in with
    a same-origin-only return target — never a partial page (architecture
    section 3; section 14's R1 test plan: "anonymous -> sign-in redirect on
    every v2 endpoint"). A real identity-lookup failure is a truthful 503,
    never silently treated as "signed out".

    The return target is only ever this request's own GET path. Building it
    from ``request.full_path`` on a POST-only mutation route would send a
    member who just signed in back to a GET on a path that only accepts
    POST — a 405, not the room (independent review finding). Every mutation
    on this blueprint redirects back to :data:`ROOM_PATH` on success, so
    landing there after sign-in loses nothing: the member re-submits from a
    room that is exactly as fresh as the one their expired session saw.
    """
    try:
        return get_current_identity(), None
    except AuthenticationRequired:
        if request.method == "GET":
            return_path = _safe_return_path(request.full_path.rstrip("?"))
        else:
            return_path = ROOM_PATH
        return None, redirect(url_for("auth.sign_in", return_to=return_path))
    except DatabaseServiceError:
        return None, _render_unavailable()


def _requested_step():
    requested = request.args.get("step")
    return requested if requested in _ALLOWED_STEPS else None


def _intake_context(
    *,
    error=None,
    replace=False,
    editor_text="",
    import_url="",
    open_method=None,
    recovery_only=False,
):
    # A fresh idempotency key per render (not per keystroke): a double
    # submission of the SAME rendered form reuses this value, so a stray
    # double-click or a network-level retry cannot create a second source
    # version. A genuinely new page load gets a genuinely new key.
    return {
        "stage": "intake",
        "has_source": False,
        "replace": replace,
        "error": error,
        "editor_text": editor_text or "",
        "import_url": import_url or "",
        "open_method": open_method,
        "recovery_only": recovery_only,
        "max_source_units": MAX_SOURCE_TEXT_UNITS,
        "idempotency_key": str(uuid4()),
        "upload_idempotency_key": str(uuid4()),
        "import_idempotency_key": str(uuid4()),
    }


def _source_review_context(
    working,
    identity_view,
    *,
    error=None,
    notice=None,
    identity_draft=None,
    wording_draft=None,
):
    return {
        "stage": "source_review",
        "working": working,
        "identity": identity_view,
        "error": error,
        "notice": notice,
        "identity_draft": identity_draft,
        "wording_draft": wording_draft,
        # _stage_source_review.html's three maxlength attributes (Employer,
        # Role title, Captured wording) read these two — independent review
        # finding: they were omitted here, so every maxlength rendered
        # empty and the browser silently ignored all three client-side
        # caps (server-side validation was never affected).
        "max_identity_units": MAX_IDENTITY_FIELD_UNITS,
        "max_source_units": MAX_SOURCE_TEXT_UNITS,
    }


def _source_review_recovery_context(identity_draft, wording_draft, *, error):
    """Render only the member's posted Stage 2 draft when storage cannot
    be read before a mutation.

    No stored metadata or concurrency token is guessed, and no mutation
    control is offered from this state. The member can copy the still-visible
    draft and use the recovery link to reload verified storage.
    """
    return {
        "stage": "source_review_recovery",
        "error": error,
        "notice": None,
        "identity_draft": identity_draft,
        "wording_draft": wording_draft or "",
    }


def _render_room(context, *, status=200):
    return render_template(
        "opportunity_slate_v2/room.html",
        page_title="Opportunity Slate",
        room=context,
        status=status,
    ), status


def _render_unavailable(context=None):
    """Truthful 503 for a real storage failure.

    Never falls back to fixture content and never claims the member has no
    working opportunity — "we couldn't reach it" and "it does not exist"
    are different facts and are told apart here (the legacy room's own
    rule, carried forward unchanged).
    """
    current_app.logger.error(
        "PeerSlate Opportunity Slate (replacement) working store is unavailable."
    )
    if context is None:
        context = _intake_context(
            recovery_only=True,
            error={
                "kind": "unavailable",
                "heading": "We couldn't open your Opportunity Slate.",
                "message": UNAVAILABLE_MESSAGE,
                "truth": (
                    "Session private • This request did not read or change "
                    "a current working source."
                ),
                "recovery_url": url_for("opportunity_slate_v2.room"),
                "recovery_label": "Try opening the workroom again",
            },
        )
    response = make_response(_render_room(context, status=503))
    response.headers["Retry-After"] = "5"
    return response


def _load_source_review_state(identity):
    """Load the owner's current Stage 2 state without caller-supplied keys."""
    working = opportunity_slate_v2_service.get_working_session_for_owner(
        identity.user_key
    )
    if working is None:
        return None, None
    identity_view = opportunity_slate_v2_service.get_source_identity_for_owner(
        identity.user_key, working.source_key
    )
    return working, identity_view


def _review_drafts_from_request():
    return (
        {
            "employer_name": request.form.get("employer_name", ""),
            "role_title": request.form.get("role_title", ""),
        },
        request.form.get("corrected_text", ""),
    )


def _normalized_optional_text(value):
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _normalized_line_endings(value):
    return value.replace("\r\n", "\n").replace("\r", "\n") if isinstance(value, str) else value


def _review_error(heading, message, truth, *, recovery_label="Reload the stored version"):
    return {
        "kind": "unavailable",
        "heading": heading,
        "message": message,
        "truth": f"Session private • {truth}",
        "recovery_url": url_for("opportunity_slate_v2.room"),
        "recovery_label": recovery_label,
    }


def _render_review_preload_unavailable(identity_draft, wording_draft):
    return _render_unavailable(
        _source_review_recovery_context(
            identity_draft,
            wording_draft,
            error=_review_error(
                "We couldn't verify the stored role source.",
                UNAVAILABLE_MESSAGE,
                (
                    "No save, confirmation, or deletion was attempted. "
                    "Your submitted draft remains on this page."
                ),
                recovery_label="Reload the stored version",
            ),
        )
    )


def _reload_source_review_for_error(
    identity,
    *,
    error,
    status=400,
    identity_draft=None,
    wording_draft=None,
    fallback_state=None,
):
    """Re-render stage 2 with the member's current stored state and one
    failure card. A failed correction or identity save must never cost the
    member their captured wording.

    ``status`` is the outcome's real HTTP status (400 field error, 409
    conflict, 503 unavailable) — carried through explicitly, because
    :func:`_render_room` defaults to 200 and a reload-on-failure must never
    silently read as a success to a client checking the response code.
    """
    try:
        working, identity_view = _load_source_review_state(identity)
    except (DatabaseServiceError, OpportunitySlateV2ServiceError):
        if fallback_state is None:
            return _render_unavailable()
        working, identity_view = fallback_state
    if working is None:
        return _render_room(
            _intake_context(error=error, editor_text=wording_draft or ""),
            status=status,
        )
    return _render_room(
        _source_review_context(
            working,
            identity_view,
            error=error,
            identity_draft=identity_draft,
            wording_draft=wording_draft,
        ),
        status=status,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@opportunity_slate_v2.get(ROOM_PATH)
def room():
    # Flag check outermost, before any identity resolution: flag-off is
    # indistinguishable from not-found.
    if not _opportunity_slate_v2_enabled():
        abort(404)

    identity, failure = _resolve_identity_or_gate()
    if failure is not None:
        return failure

    try:
        opportunity_slate_v2_service.purge_expired_working_data_for_owner(
            identity.user_key
        )
    except (DatabaseServiceError, OpportunitySlateV2ServiceError):
        # Maintenance only: expiry is enforced at read regardless, so a
        # purge failure must not deny the member their room.
        pass

    try:
        working = opportunity_slate_v2_service.get_working_session_for_owner(
            identity.user_key
        )
    except (DatabaseServiceError, OpportunitySlateV2ServiceError):
        return _render_unavailable()

    if working is None:
        return _render_room(_intake_context())

    if _requested_step() == STEP_REPLACE:
        # N-5's "Replace source" secondary action: the member confirmed the
        # bounded dialog and is brought back to intake to bring in a new
        # source. The existing working opportunity is untouched until the
        # member actually submits a new capture with replace=1.
        return _render_room(_intake_context(replace=True))

    try:
        identity_view = opportunity_slate_v2_service.get_source_identity_for_owner(
            identity.user_key, working.source_key
        )
    except (DatabaseServiceError, OpportunitySlateV2ServiceError):
        return _render_unavailable()

    notice = _NOTICE_COPY.get(request.args.get("notice"))
    return _render_room(
        _source_review_context(working, identity_view, notice=notice)
    )


@opportunity_slate_v2.post(f"{ROOM_PATH}/source")
def set_source():
    """Capture or replace the employer source (image 04's ``Review source``)."""
    if not _opportunity_slate_v2_enabled():
        abort(404)
    if not _is_same_origin_write():
        abort(403)
    identity, failure = _resolve_identity_or_gate()
    if failure is not None:
        return failure

    raw_text = request.form.get("source_text", "")
    idempotency_key = request.form.get("idempotency_key") or str(uuid4())
    replace = request.form.get("replace") == "1"

    editor_text = raw_text if isinstance(raw_text, str) else ""

    try:
        clean_text = validate_source_text(raw_text)
    except OpportunitySlateV2ServiceError as error:
        return _render_room(
            _intake_context(
                replace=replace,
                editor_text=editor_text,
                error=_field_error("We couldn't use that role text.", error.code),
            ),
            status=400,
        )

    try:
        opportunity_slate_v2_service.save_source_for_owner(
            identity.user_key, idempotency_key, clean_text, capture_method="pasted"
        )
    except DatabaseServiceError:
        return _render_unavailable(
            _intake_context(
                replace=replace,
                editor_text=clean_text,
                recovery_only=True,
                error=_review_error(
                    "We couldn't verify that role capture.",
                    UNAVAILABLE_MESSAGE,
                    TRUTH_ATTEMPT_UNKNOWN,
                    recovery_label="Check the stored version",
                ),
            )
        )
    except OpportunitySlateV2ServiceError as error:
        return _render_room(
            _intake_context(
                replace=replace,
                editor_text=clean_text,
                error=_field_error("We couldn't capture that role.", error.code),
            ),
            status=409 if error.code == "changed" else 400,
        )

    return redirect(url_for("opportunity_slate_v2.room"))


@opportunity_slate_v2.post(f"{ROOM_PATH}/source/upload")
def upload_source():
    """Upload a PDF, DOCX, or TXT document as the employer source.

    Every failure reason renders the same honest "We couldn't read this
    document." card; the uploaded bytes are never retried, never partially
    saved, and are discarded the moment this request ends (architecture
    section 6.11's upload contract: cancellable in flight; atomic on
    completion).
    """
    if not _opportunity_slate_v2_enabled():
        abort(404)
    if not _is_same_origin_write():
        abort(403)
    identity, failure = _resolve_identity_or_gate()
    if failure is not None:
        return failure

    idempotency_key = request.form.get("idempotency_key") or str(uuid4())
    replace = request.form.get("replace") == "1"
    editor_text = request.form.get("source_text", "")
    import_url = request.form.get("source_url", "")
    document = request.files.get("document")

    try:
        extracted_text, truncated = extract_uploaded_document(document)
        clean_text = validate_source_text(extracted_text)
    except (OpportunitySourceIntakeError, OpportunitySlateV2ServiceError):
        return _render_room(
            _intake_context(
                replace=replace,
                editor_text=editor_text,
                import_url=import_url,
                open_method="upload",
                error={
                    "kind": "unavailable",
                    "heading": UPLOAD_FAILURE_HEADING,
                    "message": UPLOAD_FAILURE_MESSAGE,
                    "truth": (
                        f"Session private • {TRUTH_NO_CAPTURE} Your typed "
                        "draft and public-link URL remain in the form."
                    ),
                    "recovery_url": url_for("opportunity_slate_v2.room"),
                    "recovery_label": "Reload the stored version",
                },
            ),
            status=400,
        )

    try:
        opportunity_slate_v2_service.save_source_for_owner(
            identity.user_key,
            idempotency_key,
            clean_text,
            capture_method="uploaded",
        )
    except DatabaseServiceError:
        return _render_unavailable(
            _intake_context(
                replace=replace,
                editor_text=editor_text,
                import_url=import_url,
                open_method="upload",
                recovery_only=True,
                error={
                    "kind": "unavailable",
                    "heading": "We couldn't verify that upload.",
                    "message": UNAVAILABLE_MESSAGE,
                    "truth": f"Session private • {TRUTH_ATTEMPT_UNKNOWN}",
                    "recovery_url": url_for("opportunity_slate_v2.room"),
                    "recovery_label": "Check the stored version",
                },
            )
        )
    except OpportunitySlateV2ServiceError:
        return _render_room(
            _intake_context(
                replace=replace,
                editor_text=editor_text,
                import_url=import_url,
                open_method="upload",
                error={
                    "kind": "unavailable",
                    "heading": UPLOAD_FAILURE_HEADING,
                    "message": UPLOAD_FAILURE_MESSAGE,
                    "truth": (
                        f"Session private • {TRUTH_NO_CAPTURE} Your typed "
                        "draft and public-link URL remain in the form."
                    ),
                    "recovery_url": url_for("opportunity_slate_v2.room"),
                    "recovery_label": "Reload the stored version",
                },
            ),
            status=400,
        )

    if truncated:
        return redirect(
            url_for(
                "opportunity_slate_v2.room", notice=NOTICE_UPLOAD_TRUNCATED
            )
        )

    return redirect(url_for("opportunity_slate_v2.room"))


@opportunity_slate_v2.post(f"{ROOM_PATH}/source/import")
def import_source():
    """Import a public employer or ATS page as the employer source.

    The fetch runs entirely inside the SSRF-guarded
    ``opportunity_source_intake_service.extract_imported_link`` — this route
    never opens a socket. Every failure reason renders the same honest
    "We couldn't import that link." card.
    """
    if not _opportunity_slate_v2_enabled():
        abort(404)
    if not _is_same_origin_write():
        abort(403)
    identity, failure = _resolve_identity_or_gate()
    if failure is not None:
        return failure

    idempotency_key = request.form.get("idempotency_key") or str(uuid4())
    replace = request.form.get("replace") == "1"
    source_url = request.form.get("source_url", "")
    editor_text = request.form.get("source_text", "")

    try:
        extracted_text, truncated, _final_url = extract_imported_link(source_url)
        clean_text = validate_source_text(extracted_text)
    except (OpportunitySourceIntakeError, OpportunitySlateV2ServiceError):
        return _render_room(
            _intake_context(
                replace=replace,
                editor_text=editor_text,
                import_url=source_url,
                open_method="import",
                error={
                    "kind": "unavailable",
                    "heading": IMPORT_FAILURE_HEADING,
                    "message": IMPORT_FAILURE_MESSAGE,
                    "truth": (
                        f"Session private • {TRUTH_NO_CAPTURE} Your typed "
                        "draft and public-link URL remain in the form."
                    ),
                    "recovery_url": url_for("opportunity_slate_v2.room"),
                    "recovery_label": "Reload the stored version",
                },
            ),
            status=400,
        )

    try:
        opportunity_slate_v2_service.save_source_for_owner(
            identity.user_key,
            idempotency_key,
            clean_text,
            capture_method="imported",
        )
    except DatabaseServiceError:
        return _render_unavailable(
            _intake_context(
                replace=replace,
                editor_text=editor_text,
                import_url=source_url,
                open_method="import",
                recovery_only=True,
                error={
                    "kind": "unavailable",
                    "heading": "We couldn't verify that import.",
                    "message": UNAVAILABLE_MESSAGE,
                    "truth": f"Session private • {TRUTH_ATTEMPT_UNKNOWN}",
                    "recovery_url": url_for("opportunity_slate_v2.room"),
                    "recovery_label": "Check the stored version",
                },
            )
        )
    except OpportunitySlateV2ServiceError:
        return _render_room(
            _intake_context(
                replace=replace,
                editor_text=editor_text,
                import_url=source_url,
                open_method="import",
                error={
                    "kind": "unavailable",
                    "heading": IMPORT_FAILURE_HEADING,
                    "message": IMPORT_FAILURE_MESSAGE,
                    "truth": (
                        f"Session private • {TRUTH_NO_CAPTURE} Your typed "
                        "draft and public-link URL remain in the form."
                    ),
                    "recovery_url": url_for("opportunity_slate_v2.room"),
                    "recovery_label": "Reload the stored version",
                },
            ),
            status=400,
        )

    if truncated:
        return redirect(
            url_for(
                "opportunity_slate_v2.room", notice=NOTICE_IMPORT_TRUNCATED
            )
        )

    return redirect(url_for("opportunity_slate_v2.room"))


@opportunity_slate_v2.post(f"{ROOM_PATH}/source/identity")
def save_identity():
    """Image 05 section A: save the member-entered employer / role title."""
    if not _opportunity_slate_v2_enabled():
        abort(404)
    if not _is_same_origin_write():
        abort(403)
    identity, failure = _resolve_identity_or_gate()
    if failure is not None:
        return failure

    source_key = request.form.get("source_key")
    version_token = request.form.get("version_token")
    identity_draft, wording_draft = _review_drafts_from_request()
    try:
        fallback_state = _load_source_review_state(identity)
    except (DatabaseServiceError, OpportunitySlateV2ServiceError):
        return _render_review_preload_unavailable(identity_draft, wording_draft)

    try:
        opportunity_slate_v2_service.save_source_identity_for_owner(
            identity.user_key,
            source_key,
            version_token,
            identity_draft["employer_name"],
            identity_draft["role_title"],
        )
    except DatabaseServiceError:
        return _reload_source_review_for_error(
            identity,
            error=_review_error(
                "We couldn't verify that identity change.",
                UNAVAILABLE_MESSAGE,
                TRUTH_ATTEMPT_UNKNOWN,
                recovery_label="Check the stored version",
            ),
            status=503,
            identity_draft=identity_draft,
            wording_draft=wording_draft,
            fallback_state=fallback_state,
        )
    except OpportunitySlateV2ServiceError as error:
        if error.code == "changed":
            return _reload_source_review_for_error(
                identity,
                error=_review_error(
                    "This role source changed.",
                    CONFLICT_MESSAGE,
                    "The stale identity write was refused. Your attempted values remain on this page.",
                ),
                status=409,
                identity_draft=identity_draft,
                wording_draft=wording_draft,
                fallback_state=fallback_state,
            )
        return _reload_source_review_for_error(
            identity,
            error=_field_error(
                "We couldn't use that employer or role title.",
                error.code,
                truth=(
                    "The stored source was not changed by this refused identity edit. "
                    "Your attempted values remain on this page."
                ),
                messages=IDENTITY_FIELD_ERROR_MESSAGES,
            ),
            status=400,
            identity_draft=identity_draft,
            wording_draft=wording_draft,
            fallback_state=fallback_state,
        )

    try:
        working, identity_view = _load_source_review_state(identity)
    except (DatabaseServiceError, OpportunitySlateV2ServiceError):
        return _reload_source_review_for_error(
            identity,
            error=_review_error(
                "The identity was submitted, but the room could not reload.",
                UNAVAILABLE_MESSAGE,
                TRUTH_ATTEMPT_UNKNOWN,
                recovery_label="Check the stored version",
            ),
            status=503,
            identity_draft=identity_draft,
            wording_draft=wording_draft,
            fallback_state=fallback_state,
        )
    unsaved_wording = (
        wording_draft
        if working is not None
        and _normalized_line_endings(wording_draft.strip())
        != _normalized_line_endings(working.display_text)
        else None
    )
    notice = "Employer and role title saved."
    if unsaved_wording is not None:
        notice += " Your visible wording edit remains unsaved."
    return _render_room(
        _source_review_context(
            working,
            identity_view,
            notice=notice,
            wording_draft=unsaved_wording,
        )
    )


@opportunity_slate_v2.post(f"{ROOM_PATH}/source/corrections")
def correct_source():
    """Apply the member's manual correction of the captured wording
    (image 05 section B)."""
    if not _opportunity_slate_v2_enabled():
        abort(404)
    if not _is_same_origin_write():
        abort(403)
    identity, failure = _resolve_identity_or_gate()
    if failure is not None:
        return failure

    identity_draft, raw_text = _review_drafts_from_request()
    source_key = request.form.get("source_key")
    version_token = request.form.get("version_token")
    try:
        fallback_state = _load_source_review_state(identity)
    except (DatabaseServiceError, OpportunitySlateV2ServiceError):
        return _render_review_preload_unavailable(identity_draft, raw_text)

    try:
        opportunity_slate_v2_service.correct_source_for_owner(
            identity.user_key, source_key, version_token, raw_text
        )
    except DatabaseServiceError:
        return _reload_source_review_for_error(
            identity,
            error=_review_error(
                "We couldn't verify that wording change.",
                UNAVAILABLE_MESSAGE,
                TRUTH_ATTEMPT_UNKNOWN,
                recovery_label="Check the stored version",
            ),
            status=503,
            identity_draft=identity_draft,
            wording_draft=raw_text,
            fallback_state=fallback_state,
        )
    except OpportunitySlateV2ServiceError as error:
        if error.code == "changed":
            return _reload_source_review_for_error(
                identity,
                error=_review_error(
                    "This role source changed.",
                    CONFLICT_MESSAGE,
                    "The stale wording write was refused. Your attempted values remain on this page.",
                ),
                status=409,
                identity_draft=identity_draft,
                wording_draft=raw_text,
                fallback_state=fallback_state,
            )
        return _reload_source_review_for_error(
            identity,
            error=_field_error(
                "We couldn't use that wording.",
                error.code,
                truth=(
                    "The stored wording was not changed by this refused edit. "
                    "Your attempted values remain on this page."
                ),
            ),
            status=400,
            identity_draft=identity_draft,
            wording_draft=raw_text,
            fallback_state=fallback_state,
        )

    try:
        working, identity_view = _load_source_review_state(identity)
    except (DatabaseServiceError, OpportunitySlateV2ServiceError):
        return _reload_source_review_for_error(
            identity,
            error=_review_error(
                "The wording was submitted, but the room could not reload.",
                UNAVAILABLE_MESSAGE,
                TRUTH_ATTEMPT_UNKNOWN,
                recovery_label="Check the stored version",
            ),
            status=503,
            identity_draft=identity_draft,
            wording_draft=raw_text,
            fallback_state=fallback_state,
        )
    stored_employer = identity_view.employer_name if identity_view else None
    stored_role = identity_view.role_title if identity_view else None
    unsaved_identity = identity_draft if (
        _normalized_optional_text(identity_draft["employer_name"]) != stored_employer
        or _normalized_optional_text(identity_draft["role_title"]) != stored_role
    ) else None
    notice = "Captured wording saved."
    if unsaved_identity is not None:
        notice += " Your visible employer or role-title edit remains unsaved."
    return _render_room(
        _source_review_context(
            working,
            identity_view,
            notice=notice,
            identity_draft=unsaved_identity,
        )
    )


@opportunity_slate_v2.post(f"{ROOM_PATH}/source/confirm")
def confirm_source():
    """Image 05's ``Confirm source``. Saves no requirement set, produces
    nothing, and calls no AI."""
    if not _opportunity_slate_v2_enabled():
        abort(404)
    if not _is_same_origin_write():
        abort(403)
    identity, failure = _resolve_identity_or_gate()
    if failure is not None:
        return failure

    identity_draft, wording_draft = _review_drafts_from_request()
    try:
        fallback_state = _load_source_review_state(identity)
    except (DatabaseServiceError, OpportunitySlateV2ServiceError):
        return _render_review_preload_unavailable(identity_draft, wording_draft)
    working, identity_view = fallback_state
    if working is None:
        return _render_room(_intake_context(), status=409)

    stored_employer = identity_view.employer_name if identity_view else None
    stored_role = identity_view.role_title if identity_view else None
    try:
        reviewed_wording = validate_source_text(
            wording_draft, label="corrected wording"
        )
    except OpportunitySlateV2ServiceError as error:
        return _reload_source_review_for_error(
            identity,
            error=_field_error(
                "We couldn't use that wording.",
                error.code,
                truth=(
                    "Nothing was confirmed. Your attempted values remain on this page."
                ),
            ),
            status=400,
            identity_draft=identity_draft,
            wording_draft=wording_draft,
            fallback_state=fallback_state,
        )

    has_visible_edits = (
        _normalized_line_endings(reviewed_wording)
        != _normalized_line_endings(working.display_text)
        or _normalized_optional_text(identity_draft["employer_name"])
        != stored_employer
        or _normalized_optional_text(identity_draft["role_title"]) != stored_role
    )
    if has_visible_edits:
        return _reload_source_review_for_error(
            identity,
            error=_review_error(
                "Save your visible edits before confirming.",
                (
                    "Confirm source was not run because the employer, role "
                    "title, or wording on screen differs from the stored source."
                ),
                "Nothing was confirmed. Your visible edits remain on this page.",
            ),
            status=409,
            identity_draft=identity_draft,
            wording_draft=wording_draft,
            fallback_state=fallback_state,
        )

    try:
        opportunity_slate_v2_service.confirm_source_for_owner(
            identity.user_key,
            request.form.get("source_key"),
            request.form.get("version_token"),
        )
    except DatabaseServiceError:
        return _reload_source_review_for_error(
            identity,
            error=_review_error(
                "We couldn't verify that confirmation.",
                UNAVAILABLE_MESSAGE,
                TRUTH_ATTEMPT_UNKNOWN,
                recovery_label="Check the stored version",
            ),
            status=503,
            identity_draft=identity_draft,
            wording_draft=wording_draft,
            fallback_state=fallback_state,
        )
    except OpportunitySlateV2ServiceError as error:
        return _reload_source_review_for_error(
            identity,
            error=_review_error(
                "This role source changed.",
                (
                    CONFLICT_MESSAGE
                    if error.code == "changed"
                    else FIELD_ERROR_MESSAGES.get(error.code, DEFAULT_FIELD_ERROR)
                ),
                "Confirmation was refused. Review the current stored version before trying again.",
            ),
            status=409 if error.code == "changed" else 400,
            identity_draft=identity_draft,
            wording_draft=wording_draft,
            fallback_state=fallback_state,
        )

    # R1 has no requirement review yet; confirming lands back on stage 2,
    # now read as "Confirmed role source · Version N" (WorkingSourceView.
    # is_confirmed). R2 will change this redirect target, not this route's
    # contract.
    return redirect(url_for("opportunity_slate_v2.room"))


@opportunity_slate_v2.post(f"{ROOM_PATH}/source/delete")
def delete_source():
    """The member's explicit discard of the whole working opportunity
    (adaptation N-5's confirmed target — the bounded dialog lives in the
    template; this route is the action it submits to)."""
    if not _opportunity_slate_v2_enabled():
        abort(404)
    if not _is_same_origin_write():
        abort(403)
    identity, failure = _resolve_identity_or_gate()
    if failure is not None:
        return failure
    identity_draft, wording_draft = _review_drafts_from_request()
    try:
        fallback_state = _load_source_review_state(identity)
    except (DatabaseServiceError, OpportunitySlateV2ServiceError):
        return _render_review_preload_unavailable(identity_draft, wording_draft)

    try:
        opportunity_slate_v2_service.delete_working_session_for_owner(
            identity.user_key,
            request.form.get("session_key"),
            request.form.get("session_version_token"),
        )
    except DatabaseServiceError:
        return _reload_source_review_for_error(
            identity,
            error=_review_error(
                "We couldn't verify that deletion.",
                UNAVAILABLE_MESSAGE,
                TRUTH_ATTEMPT_UNKNOWN,
                recovery_label="Check whether the working source still exists",
            ),
            status=503,
            identity_draft=identity_draft,
            wording_draft=wording_draft,
            fallback_state=fallback_state,
        )
    except OpportunitySlateV2ServiceError as error:
        # Section 6.9: "Failed delete leaves the object visibly intact."
        # That is true of every refusal reason on this route (a version
        # conflict included — a delete that lost a race is exactly a
        # delete that did not happen), so this is the one failure card on
        # this blueprint that does not switch to CONFLICT_MESSAGE for
        # "changed": the two facts ("it changed" and "it's still here")
        # are both true, and "still here" is the one the member needs.
        return _reload_source_review_for_error(
            identity,
            error=_review_error(
                "We couldn't delete this working opportunity.",
                "The delete request was refused because the stored version changed.",
                "No deletion was accepted by this request. The current stored state is shown.",
            ),
            status=409 if error.code == "changed" else 400,
            identity_draft=identity_draft,
            wording_draft=wording_draft,
            fallback_state=fallback_state,
        )

    return redirect(url_for("opportunity_slate_v2.room"))
