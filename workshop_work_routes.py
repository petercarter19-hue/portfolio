"""Work on Something routes — PS-WORKSHOP-001 W2a.

Controlling brief: docs/initiatives/PS-SLATE-STUDIO-IA-001/
22_W2_IMPLEMENTATION_BRIEF.md. Adds routes to the SAME ``workshop`` Blueprint
instance workshop_routes.py defines (imported here, not re-created), so the
whole product stays one blueprint with one ``after_request``/nav-context-
processor pair. app.py imports this module (after importing ``workshop``
from workshop_routes) purely for its import-time side effect of registering
these view functions on that blueprint — mirrors how workshop_routes.py
itself is only ever imported for that side effect.

**Sub-flag.** Every route below checks BOTH ``PEERSLATE_WORKSHOP_ENABLED``
(the outermost Workshop flag) and ``PEERSLATE_WORKSHOP_SESSION_ENABLED``
(this slice's own sub-flag) before any identity resolution, exactly
mirroring workshop_routes.py's flag-then-identity ordering (architecture
doc 17 section 6, rule 1: "flag gate outermost, before identity
resolution"). When either is off, every route here 404s neutrally — "sub-
flag off", "outer flag off", "signed out", and "does not exist" all render
identically from the outside.

**No AI in this slice.** The focused question comes from a fixed curated
set (services/workshop_work_session.py's QUESTION_SETS) chosen
deterministically per door — never a model call. "Review what I shared"
leads to work_session_holding, an honest "AI review arrives next" card, not
a real AI call. The Spark door and the "AI-unavailable" opening composition
(R07/R08) both render without any AI ever having been attempted — see
_ai_unavailable_test_seam_requested's docstring.

**Anonymous vs member.** Both share the SAME session-cookie work-state
mechanism (services/workshop_work_session.py). Where they differ: the
"Related confirmed information" rail and "Continue where I left off" list
read from workshop_demo_library's session-layered sample library for an
anonymous visitor, and from the real owner-scoped store
(services/knowledge_service.py) for a signed-in member — and "Save
unfinished" writes to whichever of those the identity resolves to, via the
SAME existing save paths workshop_routes.py's direct-entry flow already
uses (workshop_demo_library.add_item / knowledge_service.
save_knowledge_item_for_owner). No ``*_for_owner`` service method is ever
called for an anonymous caller.
"""

from uuid import uuid4

from flask import (
    abort,
    current_app,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from identity import AuthenticationRequired, get_current_identity
from services import workshop_demo_library
from services import workshop_work_session as wws
from services.database_service import DatabaseServiceError
from services.knowledge_service import (
    MAX_TITLE_UNITS,
    KnowledgeServiceError,
    knowledge_service,
)
from workshop_routes import (
    DEFAULT_FIELD_ERROR,
    FIELD_ERROR_MESSAGES,
    UNAVAILABLE_FORM_MESSAGE,
    WORKSHOP_SUCCESS_MESSAGES,
    _is_same_origin_write,
    _normalize_item_key,
    _render_workshop_unavailable,
    _safe_return_path,
    workshop,
)


RESET_VALIDATION_MESSAGES = {
    "confirm-reset": "Confirm before starting fresh.",
}

# The honest holding-state copy (brief's exact wording).
HOLDING_MESSAGE = (
    "The AI review step is coming next. Your words are safe — save "
    "unfinished to keep them in this session."
)

MAX_UNFINISHED_LIST = 5


def _session_enabled():
    return current_app.config.get("PEERSLATE_WORKSHOP_SESSION_ENABLED", False) is True


def _work_flag_gate():
    """True when both flags are on. Both are checked before ANY identity
    resolution on every route in this module (architecture rule 1)."""
    return (
        current_app.config.get("PEERSLATE_WORKSHOP_ENABLED", False) is True
        and _session_enabled()
    )


def _ai_unavailable_test_seam_requested():
    """Test-only seam for the opening's honest AI-unavailable composition
    (R07/R08). No real AI call exists anywhere in W2a to actually fail —
    Spark itself is slice W2c — so this exists purely to make the
    composition buildable, testable, and screenshot-able now, and reusable
    unchanged once a later slice's real Spark/AI call can fail for real.

    Gated on PEERSLATE_ALLOW_DEV_IDENTITY (identity.py's own pre-existing
    local-preview-only flag; production never sets it — see its own
    docstring and .env.example) PLUS an explicit query parameter, mirroring
    workshop_routes.py's existing ``?_dev_state=empty`` dev-fixture seam
    idiom exactly. Never consulted when that flag is off, so this can never
    be reached by a real production request regardless of query string.
    """
    return (
        current_app.config.get("PEERSLATE_ALLOW_DEV_IDENTITY", False) is True
        and request.args.get("_dev_ai_state") == "unavailable"
    )


def _title_from_question(question_text):
    """A short, honest title for a Save-unfinished item derived from the
    session's focused question — bounded to MAX_TITLE_UNITS. Every curated
    question in workshop_work_session.QUESTION_SETS is well under this
    bound in practice; the slice is a defensive backstop only."""
    if not question_text:
        return "Work on Something"
    if wws.utf16_length(question_text) <= MAX_TITLE_UNITS:
        return question_text
    return question_text[:MAX_TITLE_UNITS]


def _confirmed_rows(identity):
    """Up to wws.MAX_CONTEXT_ITEMS confirmed items, stable order, for the
    "Related confirmed information" rail and door-availability checks.
    Anonymous: the session-layered demo library. Member: the real
    owner-scoped store. May raise KnowledgeServiceError/DatabaseServiceError
    for a member — callers treat that as a real failure, never an empty
    list (never silently hides a database problem as "no confirmed
    information yet")."""
    if identity is None:
        delta = workshop_demo_library.read_session_delta(session)
        rows = workshop_demo_library.list_rows(delta)
    else:
        list_result = knowledge_service.list_knowledge_items_for_owner(identity.user_key)
        rows = list_result.items
    return [row for row in rows if row["status"] == "confirmed"][: wws.MAX_CONTEXT_ITEMS]


def _unfinished_rows(identity):
    """Up to MAX_UNFINISHED_LIST unfinished items for "Continue where I left
    off". Same identity-branch discipline as _confirmed_rows."""
    if identity is None:
        delta = workshop_demo_library.read_session_delta(session)
        rows = workshop_demo_library.list_rows(delta)
    else:
        list_result = knowledge_service.list_knowledge_items_for_owner(identity.user_key)
        rows = list_result.items
    return [row for row in rows if row["status"] == "unfinished"][:MAX_UNFINISHED_LIST]


def _lookup_unfinished_row(identity, item_key):
    """The single unfinished row matching item_key for THIS identity, or
    None (never confirms/denies whether a foreign or expired key exists for
    someone else — same convention as workshop_routes.py's
    _resolve_selected_item_key). May raise KnowledgeServiceError (non-
    not_found codes) / DatabaseServiceError for a member; callers treat
    that as a real failure."""
    if identity is None:
        delta = workshop_demo_library.read_session_delta(session)
        row = workshop_demo_library.get_row(item_key, delta)
        return row if row and row["status"] == "unfinished" else None

    try:
        row = knowledge_service.get_knowledge_item_for_owner(identity.user_key, item_key)
    except KnowledgeServiceError as error:
        if error.code == "not_found":
            return None
        raise
    return row if row["status"] == "unfinished" else None


def _door_view_model(*, unfinished_rows, ai_unavailable):
    """The four persistent doors (doc 13's ruling), each honestly reflecting
    what actually works in this slice. "I brought something" and "Give me a
    spark" are never startable in W2a (see wws.STARTABLE_DOORS) — both
    render inert with honest copy, matching the existing "Coming later"
    inert-row convention used elsewhere on this blueprint rather than a
    disabled-but-still-announced link or button."""
    return {
        "continue": {
            "available": bool(unfinished_rows),
            # NOT "items" — Jinja's attribute-then-item lookup would find
            # dict.items (the built-in method) before falling back to a
            # dict KEY named "items", shadowing this list entirely.
            "unfinished_entries": unfinished_rows,
        },
        "brought": {"available": False},
        "something": {"available": True},
        "spark": {
            "available": False,
            "unavailable_now": ai_unavailable,
        },
    }


def _render_opening(
    *,
    identity,
    composer_value="",
    error_message=None,
    success_message=None,
    status_code=200,
):
    unfinished_rows = _unfinished_rows(identity)
    related_rows = _confirmed_rows(identity)
    ai_unavailable = _ai_unavailable_test_seam_requested()

    return (
        render_template(
            "workshop_work.html",
            page_title="Work on Something — Workshop",
            active_workshop_mode="work",
            anonymous_preview=(identity is None),
            ai_unavailable=ai_unavailable,
            doors=_door_view_model(unfinished_rows=unfinished_rows, ai_unavailable=ai_unavailable),
            related_items=related_rows[:3],
            composer_value=composer_value,
            max_thought_units=wws.MAX_ANSWER_UNITS,
            error_message=error_message,
            success_message=success_message,
            # Templates submit these as opaque hidden-field values rather
            # than hardcoding wws's single-character door codes.
            door_continue=wws.DOOR_CONTINUE,
            door_something=wws.DOOR_SOMETHING,
            start_url=url_for("workshop.start_work_session"),
            sign_in_url=url_for(
                "auth.sign_in",
                return_to=_safe_return_path(request.full_path.rstrip("?")),
            )
            if identity is None
            else None,
        ),
        status_code,
    )


@workshop.get("/app/workshop/work")
def work_opening():
    if not _work_flag_gate():
        abort(404)

    try:
        identity = get_current_identity()
    except AuthenticationRequired:
        identity = None
    except DatabaseServiceError:
        current_app.logger.error("PeerSlate Workshop identity lookup failed.")
        return _render_workshop_unavailable()

    try:
        return _render_opening(
            identity=identity,
            success_message=WORKSHOP_SUCCESS_MESSAGES.get(request.args.get("changed")),
        )
    except (KnowledgeServiceError, DatabaseServiceError):
        current_app.logger.error("PeerSlate Work on Something opening is unavailable.")
        return _render_workshop_unavailable()


@workshop.post("/app/workshop/work/start")
def start_work_session():
    if not _work_flag_gate():
        abort(404)
    if not _is_same_origin_write():
        return "Cross-site Workshop requests are not allowed.", 403

    try:
        identity = get_current_identity()
    except AuthenticationRequired:
        identity = None
    except DatabaseServiceError:
        current_app.logger.error("PeerSlate Workshop identity lookup failed.")
        return _render_workshop_unavailable()

    door = request.form.get("door") or wws.DOOR_SOMETHING
    thought = request.form.get("thought", "")

    if door == wws.DOOR_CONTINUE:
        normalized = _normalize_item_key(request.form.get("resume_item", ""))
        row = None
        if normalized:
            try:
                row = _lookup_unfinished_row(identity, normalized)
            except (KnowledgeServiceError, DatabaseServiceError):
                current_app.logger.error("PeerSlate Workshop resume lookup failed.")
                return _render_workshop_unavailable()
        if row is None:
            # Neutral fallback — never confirms or denies a foreign/expired
            # resume target.
            return redirect(url_for("workshop.work_opening"))
        seed = row["approved_wording"]
    elif door == wws.DOOR_SOMETHING:
        seed = thought
    else:
        try:
            return _render_opening(
                identity=identity,
                composer_value=thought,
                error_message=wws.DOOR_UNAVAILABLE_MESSAGE,
                status_code=400,
            )
        except (KnowledgeServiceError, DatabaseServiceError):
            current_app.logger.error("PeerSlate Work on Something opening is unavailable.")
            return _render_workshop_unavailable()

    ok, error_message, _state = wws.start_session(session, door=door, answer=seed)
    if not ok:
        try:
            return _render_opening(
                identity=identity,
                composer_value=seed if door == wws.DOOR_SOMETHING else "",
                error_message=error_message,
                status_code=400,
            )
        except (KnowledgeServiceError, DatabaseServiceError):
            current_app.logger.error("PeerSlate Work on Something opening is unavailable.")
            return _render_workshop_unavailable()

    return redirect(url_for("workshop.work_session_screen"))


def _render_session_screen(
    *,
    identity,
    state,
    answer_override=None,
    selected_ids_override=None,
    error_message=None,
    status_code=200,
):
    related_rows = _confirmed_rows(identity)
    visible_ids = [row["item_key"] for row in related_rows]
    selected_ids = (
        set(selected_ids_override)
        if selected_ids_override is not None
        else set(wws.context_ids_from_mask(state["context_mask"], visible_ids))
    )

    return (
        render_template(
            "workshop_work_session.html",
            page_title="Focused question — Workshop",
            active_workshop_mode="work",
            anonymous_preview=(identity is None),
            question_text=state["question_text"],
            answer_value=answer_override if answer_override is not None else state["answer"],
            max_answer_units=wws.MAX_ANSWER_UNITS,
            related_items=[
                {
                    "item_key": row["item_key"],
                    "title": row["title"],
                    "selected": row["item_key"] in selected_ids,
                }
                for row in related_rows
            ],
            error_message=error_message,
            update_url=url_for("workshop.update_work_session"),
            back_url=url_for("workshop.work_opening"),
        ),
        status_code,
    )


@workshop.get("/app/workshop/work/session")
def work_session_screen():
    if not _work_flag_gate():
        abort(404)

    try:
        identity = get_current_identity()
    except AuthenticationRequired:
        identity = None
    except DatabaseServiceError:
        current_app.logger.error("PeerSlate Workshop identity lookup failed.")
        return _render_workshop_unavailable()

    state = wws.read_state(session)
    if state is None:
        return redirect(url_for("workshop.work_opening"))

    try:
        return _render_session_screen(identity=identity, state=state)
    except (KnowledgeServiceError, DatabaseServiceError):
        current_app.logger.error("PeerSlate Work on Something session is unavailable.")
        return _render_workshop_unavailable()


@workshop.post("/app/workshop/work/session")
def update_work_session():
    if not _work_flag_gate():
        abort(404)
    if not _is_same_origin_write():
        return "Cross-site Workshop requests are not allowed.", 403

    try:
        identity = get_current_identity()
    except AuthenticationRequired:
        identity = None
    except DatabaseServiceError:
        current_app.logger.error("PeerSlate Workshop identity lookup failed.")
        return _render_workshop_unavailable()

    state = wws.read_state(session)
    if state is None:
        return redirect(url_for("workshop.work_opening"))

    try:
        related_rows = _confirmed_rows(identity)
    except (KnowledgeServiceError, DatabaseServiceError):
        current_app.logger.error("PeerSlate Work on Something session is unavailable.")
        return _render_workshop_unavailable()
    visible_ids = [row["item_key"] for row in related_rows]

    answer = request.form.get("answer", "")
    submitted_ids = request.form.getlist("context")
    valid_selected_ids = [item_id for item_id in submitted_ids if item_id in visible_ids]
    context_mask = wws.context_mask_from_ids(valid_selected_ids, visible_ids)
    wk_action = request.form.get("wk_action")

    ok, error_message = wws.update_session(session, answer=answer, context_mask=context_mask)
    if not ok:
        return _render_session_screen(
            identity=identity,
            state=state,
            answer_override=answer,
            selected_ids_override=set(valid_selected_ids),
            error_message=error_message or DEFAULT_FIELD_ERROR,
            status_code=400,
        )

    if wk_action == "stop":
        wws.clear_session(session)
        return redirect(url_for("workshop.work_opening", changed="session-stopped"))

    if wk_action == "save_unfinished":
        title = _title_from_question(state["question_text"])

        if identity is None:
            new_item_key, add_error = workshop_demo_library.add_item(
                session,
                title=title,
                wording=answer,
                classification="unclassified",
                status="unfinished",
            )
            if new_item_key is None:
                return _render_session_screen(
                    identity=identity,
                    state=state,
                    answer_override=answer,
                    selected_ids_override=set(valid_selected_ids),
                    error_message=add_error,
                    status_code=400,
                )
            wws.clear_session(session)
            return redirect(url_for("workshop.work_opening", changed="unfinished-preview"))

        idempotency_key = str(uuid4())
        try:
            knowledge_service.save_knowledge_item_for_owner(
                identity.user_key,
                idempotency_key,
                {
                    "title": title,
                    "approved_wording": answer,
                    "original_wording": answer,
                    "body_format": "plain",
                    "classification": "unclassified",
                    "authored_via": "typed",
                    "confirm": False,
                },
            )
        except KnowledgeServiceError as error:
            return _render_session_screen(
                identity=identity,
                state=state,
                answer_override=answer,
                selected_ids_override=set(valid_selected_ids),
                error_message=FIELD_ERROR_MESSAGES.get(error.code, DEFAULT_FIELD_ERROR),
                status_code=400,
            )
        except DatabaseServiceError:
            current_app.logger.error("PeerSlate Work on Something save is unavailable.")
            return _render_session_screen(
                identity=identity,
                state=state,
                answer_override=answer,
                selected_ids_override=set(valid_selected_ids),
                error_message=UNAVAILABLE_FORM_MESSAGE,
                status_code=400,
            )
        wws.clear_session(session)
        return redirect(url_for("workshop.work_opening", changed="unfinished"))

    if wk_action == "review":
        return redirect(url_for("workshop.work_session_holding"))

    return _render_session_screen(
        identity=identity,
        state=state,
        answer_override=answer,
        selected_ids_override=set(valid_selected_ids),
        error_message=DEFAULT_FIELD_ERROR,
        status_code=400,
    )


@workshop.get("/app/workshop/work/session/review")
def work_session_holding():
    """The honest "AI review arrives next" holding state (W2a scope note:
    no real AI call has been made or attempted — this is not an AI-failure
    state, it is the truthful stand-in for a step that does not exist yet
    in this slice; see this module's own docstring). The session state is
    left intact (not cleared) so "Back to your answer" genuinely returns to
    exactly what was there."""
    if not _work_flag_gate():
        abort(404)

    try:
        identity = get_current_identity()
    except AuthenticationRequired:
        identity = None
    except DatabaseServiceError:
        current_app.logger.error("PeerSlate Workshop identity lookup failed.")
        return _render_workshop_unavailable()

    state = wws.read_state(session)
    if state is None:
        return redirect(url_for("workshop.work_opening"))

    return render_template(
        "workshop_work_holding.html",
        page_title="Review what I shared — Workshop",
        active_workshop_mode="work",
        anonymous_preview=(identity is None),
        holding_message=HOLDING_MESSAGE,
        answer_value=state["answer"],
        back_url=url_for("workshop.work_session_screen"),
        save_unfinished_url=url_for("workshop.update_work_session"),
    )


# ---------------------------------------------------------------------------
# Start fresh — clears the ENTIRE workshop_preview session key (library
# delta AND any active Work on Something session state together). This is a
# library-demo feature, independent of the session sub-flag: it works
# whenever the outer PEERSLATE_WORKSHOP_ENABLED flag is on, per the brief's
# explicit instruction ("Works regardless of the session sub-flag").
# ---------------------------------------------------------------------------


@workshop.get("/app/workshop/preview/reset")
def reset_preview_confirm():
    if current_app.config.get("PEERSLATE_WORKSHOP_ENABLED", False) is not True:
        abort(404)

    return render_template(
        "workshop_reset_confirm.html",
        page_title="Start fresh — Workshop",
        cancel_url=url_for("workshop.my_information"),
        reset_url=url_for("workshop.reset_preview"),
        error_message=RESET_VALIDATION_MESSAGES.get(request.args.get("error")),
    )


@workshop.post("/app/workshop/preview/reset")
def reset_preview():
    if current_app.config.get("PEERSLATE_WORKSHOP_ENABLED", False) is not True:
        abort(404)
    if not _is_same_origin_write():
        return "Cross-site Workshop requests are not allowed.", 403

    if request.form.get("confirm_reset") != "reset":
        return redirect(url_for("workshop.reset_preview_confirm", error="confirm-reset"))

    session.pop(workshop_demo_library.SESSION_KEY, None)
    session.modified = True

    return redirect(url_for("workshop.my_information", changed="reset-preview"))
