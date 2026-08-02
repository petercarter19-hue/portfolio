"""Protected Workshop routes — PS-WORKSHOP-001.

Slice W1 (owner checkpoint passed 2026-08-01, doc 20 section 6b): this module
renders the My Information main page from the real owner-scoped knowledge
store and adds direct entry (add / edit / archive / restore / delete). No
"Work on Something" session, AI call, or voice capture exists yet — those are
later slices. The route stays behind ``PEERSLATE_WORKSHOP_ENABLED``, default
off, and fails closed to a neutral 404 before any identity resolution when the
flag is off.

**Public preview mode (owner decision 2026-08-02, doc 20 section 6d).** Before
this decision, "flag off," "signed out," and "does not exist" were meant to
look identical from the outside (architecture doc 17 section 6) — a
signed-out visitor was redirected to sign-in exactly like flag-off resolved to
404. The owner has now explicitly overridden that for three routes only —
``GET /app/workshop``, ``GET /app/workshop/add`` (and its review step), and
``POST /app/workshop/items`` — so Workshop is fully explorable before sign-in
exists. Flag-off still 404s before any identity resolution on every route,
unchanged. A signed-out visitor to those three routes now sees the real page
rendered over honestly-labeled SAMPLE content (the library) or their own
typed text (the add/review/save flow) instead of a sign-in redirect. This
never reuses the dev-fixture seam below: it is a separate, always-available
code path (``_build_preview_view``, ``_render_anonymous_preview_saved``, the
module-level ``_PREVIEW_IDENTITY``) that never depends on
``PEERSLATE_WORKSHOP_DEV_FIXTURE`` or ``PEERSLATE_ALLOW_DEV_IDENTITY``, never
calls an ``*_for_owner`` service method, and never reaches the database. A
signed-out POST to ``/app/workshop/items`` never writes and never claims a
save happened — see ``_render_anonymous_preview_saved``. Edit / archive /
restore / delete stay behind sign-in: the library's sample items simply carry
no edit/archive/restore/delete URL (mirroring the existing dev-fixture inert-
row treatment), so those controls render visibly inert rather than either
pretending to mutate or opening a fake edit flow for a sample item. A
``DatabaseServiceError`` while resolving identity is never treated as "just
signed out" — that is a real failure and still renders the truthful 503
(``_render_workshop_unavailable``), on every route, unchanged.

``PEERSLATE_WORKSHOP_DEV_FIXTURE`` (default off, local-preview-only) makes
``GET /app/workshop`` render the fixed checkpoint fixture from
``services/knowledge_service.py`` instead of the real store, optionally with
``?_dev_state=empty`` to preview the first-run empty state — neither query
parameter nor flag is consulted anywhere on the production write path, and
neither is consulted by the public preview path above.

``_safe_return_path`` mirrors ``auth_routes._safe_return_path`` exactly. It
is duplicated locally rather than imported so this module has no edit-time
dependency on auth_routes.py, which is reserved by another lane's file
ownership boundary for this task. ``_is_same_origin_write`` similarly
mirrors ``owner_routes._is_same_origin_write`` for the same reason.

**Public demo library and session play (owner instruction 2026-08-02, doc
20 section 6e).** The three-route relaxation above has been extended: the
anonymous library now renders a rich, realistic 17-item sample library
(``services/workshop_demo_library.py``, the fictional "Jordan Ellis"
persona) instead of the four-item checkpoint fixture, and a signed-out
visitor's own Add/Edit/Archive/Restore/Delete actions are now real *within
their own browser session* — stored only in the signed Flask session
cookie (never a database, never shared between visitors, never permanent).
Every route below that used to sign-in-redirect a signed-out caller
(``edit_information``, ``keep_working_edit``, ``review_edit``,
``update_item``, ``archive_item``/``restore_item`` via
``_run_item_state_change``, ``delete_confirm``, ``delete_item``) now treats
``AuthenticationRequired`` the same way ``my_information``/``add_information``
already did: as a legitimate anonymous caller, handled by a session-backed
branch that never calls a ``*_for_owner`` service method and never reaches
the database. A signed-in member's behavior on every one of these routes is
completely unchanged — the session-delta branch is reached only when
identity resolution raises ``AuthenticationRequired``.
"""

from urllib.parse import urlsplit
from uuid import UUID, uuid4

from flask import (
    Blueprint,
    abort,
    current_app,
    make_response,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from identity import AuthenticationRequired, get_current_identity
from services import workshop_demo_library
from services.database_service import DatabaseServiceError
from services.knowledge_service import (
    AREA_FILTERS,
    MAX_LIST_ITEMS,
    MAX_TITLE_UNITS,
    MAX_WORDING_UNITS,
    SCHEMA_VERSION,
    STATUS_FILTERS,
    KnowledgeServiceError,
    knowledge_service,
    validate_knowledge_item_input,
)


workshop = Blueprint("workshop", __name__)

# Presentation-only mappings (raw enum -> member-facing label). The service
# layer returns validated enum values; labels are a template/view concern,
# kept here rather than in services/knowledge_service.py.
STATUS_LABELS = {
    "confirmed": "Confirmed",
    "suggested": "Suggested",
    "unfinished": "Unfinished",
    "archived": "Archived",
}
CLASSIFICATION_LABELS = {
    "work": "Work",
    "personal": "Personal",
    "both": "Both",
    "unclassified": "Unclassified",
}
# Direct entry (this slice) always writes authored_via="typed". The other two
# values cannot occur yet (no voice capture, no AI-assisted session), but the
# mapping stays complete and honest for when W2 starts writing them.
SOURCE_LABELS = {
    "typed": "Your words, added directly",
    "spoken": "Your words, spoken and reviewed",
    "ai_assisted_approved": "Your words, refined with AI assistance",
}
# W1 has no knowledge_item_uses table (architecture doc 17 section 5.4/5.5;
# doc 18 slice W4). Every real item is honestly "not used elsewhere" until
# that slice exists.
NOT_USED_ELSEWHERE = "Not used elsewhere"

# MINOR 7 correction: the composer/review classification control is four
# radio-style chips, including an explicit "Not set" option for
# "unclassified" (architecture doc 17 section 5.1 already allows this
# value; routes/validation already accepted it). An implicit, all-unchecked
# "unclassified" state was ambiguous/inaccessible — a member (or a screen
# reader) could not tell "nothing selected yet" from "deliberately marked
# unclassified." Leaving the group entirely unselected still submits
# "unclassified" as a fallback (see review_add/review_edit's
# ``raw["classification"] or "unclassified"``), but the explicit chip is
# now the honest way to state that choice.
CLASSIFICATION_CHOICES = (
    ("work", "Work"),
    ("personal", "Personal"),
    ("both", "Both"),
    ("unclassified", "Not set"),
)

WORKSHOP_SUCCESS_MESSAGES = {
    "unfinished": "Saved as unfinished. Resume anytime from My Information.",
    "archived": "Item archived. It no longer grounds AI suggestions.",
    "restored": "Item restored to your active information.",
    "deleted": "Item and its version history were permanently deleted.",
    # Anonymous preview session equivalents (owner instruction 2026-08-02,
    # doc 20 section 6e): distinct keys so the signed-in messages above stay
    # byte-for-byte unchanged. Every preview message names "this preview
    # session" and points at sign-in — never implying a real, permanent save.
    "unfinished-preview": "Kept as unfinished in this preview session. Sign in to save it for real.",
    "updated-preview": "Updated in this preview session. Sign in to make this permanent.",
    "archived-preview": "Archived in this preview session. Sign in to keep your own permanent library.",
    "restored-preview": "Restored in this preview session. Sign in to keep changes permanently.",
    "deleted-preview": "Removed from this preview session.",
}
WORKSHOP_VALIDATION_MESSAGES = {
    "changed": "That item changed or is no longer available. Refresh and try again.",
    "confirm-delete": "Confirm permanent deletion before deleting this item.",
}
# Field-level errors shown inline on the composer/review form itself (never a
# redirect, so the member's typed text is never lost) — the
# owner_routes.py message-dict convention, keyed on KnowledgeServiceError.code.
FIELD_ERROR_MESSAGES = {
    "required": "Add both a title and wording before continuing.",
    "invalid": "Choose Work, Personal, or Both, or leave it unclassified, and try again.",
    "too_long": "Shorten the title or wording and try again.",
}
DEFAULT_FIELD_ERROR = "Something went wrong. Review your entry and try again."
CONFLICT_MESSAGE = (
    "This item changed elsewhere. Your edits are shown below — review them "
    "and save again to apply them."
)
# MINOR/gap 6 correction: a database failure during Save/Update must never
# lose the member's typed text (architecture rule, same principle as
# CONFLICT_MESSAGE above) — the review/composer form re-renders with the
# submitted values instead of the bare payload-free unavailable page.
UNAVAILABLE_FORM_MESSAGE = (
    "We couldn't save this right now. Nothing has been lost — your entry "
    "below is exactly as you left it. Try again shortly."
)


def _workshop_enabled():
    return current_app.config.get("PEERSLATE_WORKSHOP_ENABLED", False) is True


def _workshop_dev_fixture_enabled():
    """Local-preview-only seam, gated on TWO independent flags.

    MAJOR 3 correction (independent review): ``PEERSLATE_WORKSHOP_DEV_FIXTURE``
    alone was not a sufficient guard. ``current_app.debug`` cannot be the
    compound condition either — the local preview this seam exists for
    deliberately runs with debug off. Instead this also requires
    ``PEERSLATE_ALLOW_DEV_IDENTITY`` (identity.py's own pre-existing
    local-preview-only dev-identity flag; production never sets it). A
    deployment that somehow left ``PEERSLATE_WORKSHOP_DEV_FIXTURE`` on
    still fails closed to the real store unless this separate,
    independently-owned flag is ALSO on.
    """
    return (
        current_app.config.get("PEERSLATE_WORKSHOP_DEV_FIXTURE", False) is True
        and current_app.config.get("PEERSLATE_ALLOW_DEV_IDENTITY", False) is True
    )


def _safe_return_path(candidate, default="/app/workshop"):
    if not candidate or not isinstance(candidate, str):
        return default
    parsed = urlsplit(candidate)
    if parsed.scheme or parsed.netloc or not candidate.startswith("/"):
        return default
    if candidate.startswith("//") or "\\" in candidate:
        return default
    return candidate


def _is_same_origin_write():
    """Allow a state-changing Workshop request only when it proves same origin.

    Mirrors ``owner_routes._is_same_origin_write`` exactly (see that
    function's docstring for the fail-closed rationale): a request carrying
    neither ``Origin`` nor ``Sec-Fetch-Site`` is treated as untrusted rather
    than allowed, because these routes include real no-JS HTML form posts.
    """
    expected_origin = request.host_url.rstrip("/")
    origin = request.headers.get("Origin")
    fetch_site = request.headers.get("Sec-Fetch-Site")
    if origin and origin.rstrip("/") != expected_origin:
        return False
    if fetch_site and fetch_site not in {"same-origin", "none"}:
        return False
    return bool(origin or fetch_site)


def _normalize_item_key(value):
    try:
        return str(UUID(str(value)))
    except (TypeError, ValueError, AttributeError):
        return None


def _owner_display_name(identity):
    display_name = getattr(identity, "display_name", None)
    if isinstance(display_name, str) and display_name.strip():
        return display_name.strip()
    return "PeerSlate member"


def _render_workshop_unavailable():
    """A private, payload-free Workshop recovery render.

    The trusted principal reached Flask, but identity storage (or the
    knowledge read/write) did not. This never falls back to fixture identity
    or fabricates a knowledge result.
    """
    response = make_response(
        render_template(
            "workshop.html",
            page_title="Workshop",
            checkpoint_unavailable=True,
            workshop=None,
        ),
        503,
    )
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["Retry-After"] = "5"
    return response


_AREA_FILTER_KEYS = frozenset(f["key"] for f in AREA_FILTERS)
_STATUS_FILTER_KEYS = frozenset(f["key"] for f in STATUS_FILTERS)


def _selected_filter_key(requested, allowed_keys):
    """Validate an ``?area=``/``?status=`` query value against its allowlist.

    A missing, malformed, or unrecognized value neutrally falls back to
    ``"all"`` — never a KeyError, never a guess about what the member meant.
    """
    return requested if requested in allowed_keys else "all"


def _filter_library_rows(rows, *, area, status, search):
    """Server-side Area/Status/search filtering over one owner's already
    materialized, already owner-scoped row list — no second database round
    trip. Mirrors ``_resolve_selected_item_key``'s existing "already-filtered
    row list" docstring, which anticipated exactly this.

    Archived items are excluded from every status selection except
    ``"archived"`` itself: "All statuses" means all active statuses, the
    same hidden-unless-asked-for convention a private archive uses elsewhere
    in the product. ``search`` matches the title only (case-insensitive) —
    the list read does not carry each item's wording text (by design, see
    _library.html), so wording is not part of the search surface in this
    slice.
    """
    filtered = rows
    if status == "archived":
        filtered = [row for row in filtered if row["status"] == "archived"]
    else:
        filtered = [row for row in filtered if row["status"] != "archived"]
        if status != "all":
            filtered = [row for row in filtered if row["status"] == status]
    if area != "all":
        filtered = [row for row in filtered if row["classification"] == area]
    if search:
        needle = search.casefold()
        filtered = [row for row in filtered if needle in row["title"].casefold()]
    return filtered


def _resolve_selected_item_key(requested, rows):
    """Resolve ``?item=`` against one owner's already-filtered row list.

    - No request -> neutral fallback to the first item (or ``None`` if the
      library is empty).
    - Malformed (non-UUID) request -> the same neutral fallback, treating a
      garbled query string as though it were absent.
    - Well-formed but foreign/unknown key (not in this owner's rows) -> no
      selection at all. This never falls back to another item and never
      renders an error, so the response cannot be used to confirm or deny
      whether that key exists for someone else.
    """
    if not rows:
        return None
    if not requested:
        return rows[0]["item_key"]
    normalized = _normalize_item_key(requested)
    if not normalized:
        return rows[0]["item_key"]
    if any(row["item_key"] == normalized for row in rows):
        return normalized
    return None


def _real_item_view(row, *, selected_key):
    item_key = row["item_key"]
    return {
        "item_key": item_key,
        "title": row["title"],
        "status": row["status"],
        "status_label": STATUS_LABELS.get(row["status"], row["status"].title()),
        "classification": row["classification"],
        "classification_label": CLASSIFICATION_LABELS.get(
            row["classification"], row["classification"].title()
        ),
        "downstream_use_label": NOT_USED_ELSEWHERE,
        "selected": item_key == selected_key,
        "select_url": url_for("workshop.my_information", item=item_key),
    }


def _real_detail_view(row):
    item_key = row["item_key"]
    return {
        "item_key": item_key,
        "title": row["title"],
        "status": row["status"],
        "status_label": STATUS_LABELS.get(row["status"], row["status"].title()),
        "classification": row["classification"],
        "classification_label": CLASSIFICATION_LABELS.get(
            row["classification"], row["classification"].title()
        ),
        "downstream_use_label": NOT_USED_ELSEWHERE,
        "body": row["approved_wording"],
        "source_label": SOURCE_LABELS.get(row["authored_via"], "Your words"),
        "version_token": row["version_token"],
        "edit_url": url_for("workshop.edit_information", item_key=item_key),
        "archive_url": url_for("workshop.archive_item", item_key=item_key),
        "restore_url": url_for("workshop.restore_item", item_key=item_key),
        "delete_url": url_for("workshop.delete_confirm", item_key=item_key),
    }


def _fixture_item_view(fixture_item):
    # Fixture rows have no backing database item, so there is nothing to
    # navigate into — select_url stays None and the template renders an
    # inert row, exactly as the checkpoint did before direct entry existed.
    return {
        "item_key": fixture_item.item_key,
        "title": fixture_item.title,
        "status": fixture_item.status,
        "status_label": fixture_item.status_label,
        "classification": fixture_item.classification,
        "classification_label": fixture_item.classification_label,
        "downstream_use_label": fixture_item.downstream_use_label,
        "selected": fixture_item.selected,
        "select_url": None,
    }


def _fixture_detail_view(fixture_item):
    return {
        "item_key": fixture_item.item_key,
        "title": fixture_item.title,
        "status": fixture_item.status,
        "status_label": fixture_item.status_label,
        "classification": fixture_item.classification,
        "classification_label": fixture_item.classification_label,
        "downstream_use_label": fixture_item.downstream_use_label,
        "body": fixture_item.body,
        "source_label": fixture_item.source_label,
        "version_token": None,
        "edit_url": None,
        "archive_url": None,
        "restore_url": None,
        "delete_url": None,
    }


def _fixture_view(checkpoint):
    items = [_fixture_item_view(item) for item in checkpoint.items]
    selected_fixture = next((item for item in checkpoint.items if item.selected), None)
    detail = _fixture_detail_view(selected_fixture) if selected_fixture else None
    return {
        "schema_version": checkpoint.schema_version,
        "owner_display_name": checkpoint.owner_display_name,
        "library_items": items,
        "detail": detail,
        "area_filters": checkpoint.area_filters,
        "status_filters": checkpoint.status_filters,
        "selected_area": checkpoint.selected_area,
        "selected_status": checkpoint.selected_status,
        "search_query": "",
        "clear_filters_url": url_for("workshop.my_information"),
        "total_item_count": checkpoint.total_item_count,
        "list_truncated": False,
        "suggestion": checkpoint.suggestion,
        "availability": checkpoint.availability,
        "add_information_url": url_for("workshop.add_information"),
    }


# ---------------------------------------------------------------------------
# Public demo library and session play (owner decision 2026-08-02, doc 20
# section 6e; supersedes the four-item checkpoint-fixture-based preview from
# section 6d)
#
# A signed-out visitor to the library, add, edit, archive, restore, and
# delete routes gets the real page rendered over the honestly-labeled Jordan
# Ellis sample library (services/workshop_demo_library.py) layered with the
# visitor's own session-only changes, instead of a sign-in redirect. This
# reuses the SAME view-model functions the real signed-in path uses
# (_real_item_view, _real_detail_view, _filter_library_rows,
# _resolve_selected_item_key) because workshop_demo_library's rows are
# shaped exactly like a real owner-scoped store read — no second, forked
# view-model exists for the anonymous path. Nothing here calls a
# ``*_for_owner`` service method or reaches the database.
# ---------------------------------------------------------------------------


def _build_demo_library_view(*, area, status, search, item_param):
    delta = workshop_demo_library.read_session_delta(session)
    rows = workshop_demo_library.list_rows(delta)

    selected_area = _selected_filter_key(area, _AREA_FILTER_KEYS)
    selected_status = _selected_filter_key(status, _STATUS_FILTER_KEYS)
    search_query = (search or "").strip()
    filtered_rows = _filter_library_rows(
        rows, area=selected_area, status=selected_status, search=search_query
    )

    selected_key = _resolve_selected_item_key(item_param, filtered_rows)
    detail = None
    if selected_key:
        detail_row = workshop_demo_library.get_row(selected_key, delta)
        if detail_row:
            detail = _real_detail_view(detail_row)

    return {
        "schema_version": SCHEMA_VERSION,
        "owner_display_name": workshop_demo_library.PERSONA_DISPLAY_NAME,
        "library_items": [
            _real_item_view(row, selected_key=selected_key) for row in filtered_rows
        ],
        "detail": detail,
        "area_filters": AREA_FILTERS,
        "status_filters": STATUS_FILTERS,
        "selected_area": selected_area,
        "selected_status": selected_status,
        "search_query": search_query,
        "clear_filters_url": url_for("workshop.my_information"),
        "total_item_count": len(rows),
        "list_truncated": False,
        # The sample library already carries real Suggested-status items
        # (filterable via Status), so no separate fabricated suggestion
        # nudge card is shown here — the same honest "no fabricated
        # suggestion" principle the real signed-in path applies below.
        "suggestion": None,
        "availability": {
            "direct_entry": {"state": "available"},
            "work_on_something": {"state": "coming_later"},
            "destination_use": {"state": "coming_later"},
        },
        "add_information_url": url_for("workshop.add_information"),
    }


@workshop.get("/app/workshop")
def my_information():
    # Flag check first, before any identity resolution, so flag-off is
    # indistinguishable from "does not exist" (architecture doc 17 section 6).
    if not _workshop_enabled():
        abort(404)

    try:
        identity = get_current_identity()
    except AuthenticationRequired:
        # Public preview mode (owner decision 2026-08-02): no redirect. A
        # signed-out visitor is a legitimate anonymous caller now, not an
        # error — handled entirely below, never touching the real store.
        identity = None
    except DatabaseServiceError:
        current_app.logger.error("PeerSlate Workshop identity lookup failed.")
        return _render_workshop_unavailable()

    if identity is None:
        view = _build_demo_library_view(
            area=request.args.get("area"),
            status=request.args.get("status"),
            search=request.args.get("q"),
            item_param=request.args.get("item"),
        )
        return render_template(
            "workshop.html",
            page_title="Workshop",
            checkpoint_unavailable=False,
            workshop=view,
            success_message=WORKSHOP_SUCCESS_MESSAGES.get(request.args.get("changed")),
            validation_message=WORKSHOP_VALIDATION_MESSAGES.get(request.args.get("error")),
            dev_preview=False,
            anonymous_preview=True,
            sign_in_url=url_for(
                "auth.sign_in",
                return_to=_safe_return_path(request.full_path.rstrip("?")),
            ),
        )

    dev_preview = _workshop_dev_fixture_enabled()
    if dev_preview:
        try:
            checkpoint = knowledge_service.get_my_information_checkpoint(
                identity, empty=(request.args.get("_dev_state") == "empty")
            )
        except KnowledgeServiceError:
            current_app.logger.error("PeerSlate Workshop checkpoint fixture failed to build.")
            return _render_workshop_unavailable()
        view = _fixture_view(checkpoint)
    else:
        try:
            list_result = knowledge_service.list_knowledge_items_for_owner(
                identity.user_key, include_archived=True
            )
        except KnowledgeServiceError:
            current_app.logger.error("PeerSlate Workshop library is unavailable.")
            return _render_workshop_unavailable()
        except DatabaseServiceError:
            current_app.logger.error("PeerSlate Workshop library is unavailable.")
            return _render_workshop_unavailable()

        rows = list_result.items
        total_item_count = list_result.total_count
        # True only when the owner's real total exceeds the TOP (200) cap
        # this read enforces — never when an owner happens to have exactly
        # 200 items and nothing more.
        list_truncated = total_item_count > MAX_LIST_ITEMS

        selected_area = _selected_filter_key(request.args.get("area"), _AREA_FILTER_KEYS)
        selected_status = _selected_filter_key(request.args.get("status"), _STATUS_FILTER_KEYS)
        search_query = (request.args.get("q") or "").strip()
        filtered_rows = _filter_library_rows(
            rows, area=selected_area, status=selected_status, search=search_query
        )

        selected_key = _resolve_selected_item_key(request.args.get("item"), filtered_rows)
        detail = None
        if selected_key:
            try:
                detail = _real_detail_view(
                    knowledge_service.get_knowledge_item_for_owner(
                        identity.user_key, selected_key
                    )
                )
            except KnowledgeServiceError as error:
                if error.code != "not_found":
                    current_app.logger.error("PeerSlate Workshop item detail is unavailable.")
                    return _render_workshop_unavailable()
                # Selected between list and get (e.g. deleted in another
                # tab); fall back to no detail rather than an error.
                selected_key = None
            except DatabaseServiceError:
                current_app.logger.error("PeerSlate Workshop item detail is unavailable.")
                return _render_workshop_unavailable()

        view = {
            "schema_version": SCHEMA_VERSION,
            "owner_display_name": _owner_display_name(identity),
            "library_items": [
                _real_item_view(row, selected_key=selected_key) for row in filtered_rows
            ],
            "detail": detail,
            "area_filters": AREA_FILTERS,
            "status_filters": STATUS_FILTERS,
            "selected_area": selected_area,
            "selected_status": selected_status,
            "search_query": search_query,
            "clear_filters_url": url_for("workshop.my_information"),
            "total_item_count": total_item_count,
            "list_truncated": list_truncated,
            # W1 has no Spark/suggestion generation (that is slice W3); a
            # real member never sees a fabricated suggestion.
            "suggestion": None,
            # Direct entry is real as of this slice; the other two remain a
            # later slice (doc 18 W2/W4) — declared honestly rather than
            # omitted, per the availability-registry idiom this mirrors.
            "availability": {
                "direct_entry": {"state": "available"},
                "work_on_something": {"state": "coming_later"},
                "destination_use": {"state": "coming_later"},
            },
            "add_information_url": url_for("workshop.add_information"),
        }

    return render_template(
        "workshop.html",
        page_title="Workshop",
        checkpoint_unavailable=False,
        workshop=view,
        success_message=WORKSHOP_SUCCESS_MESSAGES.get(request.args.get("changed")),
        validation_message=WORKSHOP_VALIDATION_MESSAGES.get(request.args.get("error")),
        dev_preview=dev_preview,
        anonymous_preview=False,
    )


# ---------------------------------------------------------------------------
# Direct entry — Add Information (new item)
# ---------------------------------------------------------------------------


def _composer_response(
    *,
    mode,
    values,
    idempotency_key,
    item_key,
    expected_version_token,
    error_message,
    form_action,
    status_code=200,
    anonymous_preview=False,
):
    return (
        render_template(
            "workshop_add.html",
            page_title=("Edit information" if mode == "edit" else "Add information")
            + " — Workshop",
            mode=mode,
            values=values,
            idempotency_key=idempotency_key,
            item_key=item_key,
            expected_version_token=expected_version_token,
            error_message=error_message,
            form_action=form_action,
            max_title_units=MAX_TITLE_UNITS,
            # Public preview mode (owner instruction 2026-08-02, doc 20
            # section 6e): every preview surface — add AND edit alike, since
            # Edit is now anonymous-capable too — hints the tighter 400-char
            # preview wording cap in the browser's own maxlength attribute.
            # The real, authoritative enforcement happens server-side in
            # save_item/update_item regardless of this attribute.
            max_wording_units=(
                workshop_demo_library.MAX_PREVIEW_WORDING_UNITS
                if anonymous_preview
                else MAX_WORDING_UNITS
            ),
            classification_choices=CLASSIFICATION_CHOICES,
            anonymous_preview=anonymous_preview,
        ),
        status_code,
    )


def _review_response(
    *,
    mode,
    values,
    idempotency_key,
    item_key,
    expected_version_token,
    error_message,
    save_url,
    keep_working_url,
    status_code=200,
    anonymous_preview=False,
):
    return (
        render_template(
            "workshop_review.html",
            page_title="Review what will be saved — Workshop",
            mode=mode,
            values=values,
            idempotency_key=idempotency_key,
            item_key=item_key,
            expected_version_token=expected_version_token,
            error_message=error_message,
            save_url=save_url,
            keep_working_url=keep_working_url,
            source_label="Your words, added directly",
            max_title_units=MAX_TITLE_UNITS,
            max_wording_units=(
                workshop_demo_library.MAX_PREVIEW_WORDING_UNITS
                if anonymous_preview
                else MAX_WORDING_UNITS
            ),
            classification_choices=CLASSIFICATION_CHOICES,
            anonymous_preview=anonymous_preview,
        ),
        status_code,
    )


def _render_anonymous_preview_saved(*, item_key, title, wording, classification):
    """The honest confirming-save render for a signed-out visitor (owner
    instruction 2026-08-02, doc 20 section 6e): no ``*_for_owner`` service
    call, no database row, and no "Saved privately" heading or copy — that
    phrase describes a real confirmed save, which never happens here. The
    item HAS just been added to this visitor's own session-only preview
    library (``item_key`` is the new session-scoped key), so the copy says
    exactly that — added for this browser session, gone when it ends, sign
    in to keep it permanently — and links back to the library to prove it.
    Distinct from the ``PEERSLATE_WORKSHOP_DEV_FIXTURE`` dev-preview render
    above (different template context flag, different banner class,
    different copy) — this path is reachable in production any time a
    visitor is signed out.
    """
    return render_template(
        "workshop_saved.html",
        page_title="Added to this preview — Workshop",
        item={
            "item_key": item_key,
            "title": title,
            "body": wording,
            "classification": classification,
            "classification_label": CLASSIFICATION_LABELS.get(
                classification, classification.title()
            ),
            "source_label": SOURCE_LABELS.get("typed", "Your words"),
        },
        dev_preview=False,
        anonymous_preview=True,
        saved_title="Added to this preview session",
        saved_subtitle=(
            "This now appears in the sample library — but only for this "
            "browser session. It disappears when the session ends. Sign in "
            "to save it to a permanent private library."
        ),
        sign_in_url=url_for("auth.sign_in", return_to="/app/workshop/add"),
        add_something_else_url=url_for("workshop.add_information"),
        view_in_my_information_url=url_for("workshop.my_information", item=item_key),
    )


@workshop.get("/app/workshop/add")
def add_information():
    if not _workshop_enabled():
        abort(404)
    is_anonymous = False
    try:
        get_current_identity()
    except AuthenticationRequired:
        # Public preview mode (owner decision 2026-08-02): openable
        # signed-out. The composer is a pure form render with no owner-scoped
        # read, so there is nothing here that needs a real identity.
        is_anonymous = True
    except DatabaseServiceError:
        current_app.logger.error("PeerSlate Workshop identity lookup failed.")
        return _render_workshop_unavailable()

    return _composer_response(
        mode="add",
        values={"title": "", "wording": "", "classification": ""},
        idempotency_key=str(uuid4()),
        item_key=None,
        expected_version_token=None,
        error_message=None,
        form_action=url_for("workshop.review_add"),
        anonymous_preview=is_anonymous,
    )


@workshop.post("/app/workshop/add")
def keep_working_add():
    """Return to the composer with the member's in-progress text preserved."""
    if not _workshop_enabled():
        abort(404)
    if not _is_same_origin_write():
        return "Cross-site Workshop requests are not allowed.", 403
    is_anonymous = False
    try:
        get_current_identity()
    except AuthenticationRequired:
        # Public preview mode (owner decision 2026-08-02): the "Keep working"
        # round trip is part of the same signed-out-openable add/review flow.
        is_anonymous = True
    except DatabaseServiceError:
        current_app.logger.error("PeerSlate Workshop identity lookup failed.")
        return _render_workshop_unavailable()

    return _composer_response(
        mode="add",
        values={
            "title": request.form.get("title", ""),
            "wording": request.form.get("wording", ""),
            "classification": request.form.get("classification", ""),
        },
        idempotency_key=request.form.get("idempotency_key") or str(uuid4()),
        item_key=None,
        expected_version_token=None,
        error_message=None,
        form_action=url_for("workshop.review_add"),
        anonymous_preview=is_anonymous,
    )


@workshop.post("/app/workshop/add/review")
def review_add():
    if not _workshop_enabled():
        abort(404)
    if not _is_same_origin_write():
        return "Cross-site Workshop requests are not allowed.", 403
    is_anonymous = False
    try:
        get_current_identity()
    except AuthenticationRequired:
        # Public preview mode (owner decision 2026-08-02): reaching the
        # review screen with the member's own typed text intact is openable
        # signed-out. Nothing here reads or writes owner-scoped data — the
        # write itself is gated separately, at save_item.
        is_anonymous = True
    except DatabaseServiceError:
        current_app.logger.error("PeerSlate Workshop identity lookup failed.")
        return _render_workshop_unavailable()

    idempotency_key = request.form.get("idempotency_key") or str(uuid4())
    raw = {
        "title": request.form.get("title", ""),
        "wording": request.form.get("wording", ""),
        "classification": request.form.get("classification", ""),
    }

    try:
        title, wording, classification = validate_knowledge_item_input(
            raw["title"], raw["wording"], raw["classification"] or "unclassified"
        )
    except KnowledgeServiceError as error:
        return _composer_response(
            mode="add",
            values=raw,
            idempotency_key=idempotency_key,
            item_key=None,
            expected_version_token=None,
            error_message=FIELD_ERROR_MESSAGES.get(error.code, DEFAULT_FIELD_ERROR),
            form_action=url_for("workshop.review_add"),
            anonymous_preview=is_anonymous,
        )

    # Preview-only wording cap (owner instruction 2026-08-02, doc 20 section
    # 6e): checked here too (not only at save_item) so an anonymous visitor
    # gets the honest, specific message before advancing to Review, with
    # their typed text fully preserved either way.
    if is_anonymous and len(wording) > workshop_demo_library.MAX_PREVIEW_WORDING_UNITS:
        return _composer_response(
            mode="add",
            values=raw,
            idempotency_key=idempotency_key,
            item_key=None,
            expected_version_token=None,
            error_message=workshop_demo_library.CAP_WORDING_MESSAGE,
            form_action=url_for("workshop.review_add"),
            anonymous_preview=True,
        )

    return _review_response(
        mode="add",
        values={"title": title, "wording": wording, "classification": classification},
        idempotency_key=idempotency_key,
        item_key=None,
        expected_version_token=None,
        error_message=None,
        save_url=url_for("workshop.save_item"),
        keep_working_url=url_for("workshop.keep_working_add"),
        anonymous_preview=is_anonymous,
    )


@workshop.post("/app/workshop/items")
def save_item():
    """The confirming save for a brand-new item (Save privately / Save unfinished)."""
    if not _workshop_enabled():
        abort(404)
    if not _is_same_origin_write():
        return "Cross-site Workshop requests are not allowed.", 403
    try:
        identity = get_current_identity()
    except AuthenticationRequired:
        # Public preview mode (owner decision 2026-08-02): a signed-out
        # confirming save never writes and never claims a save happened —
        # handled below, once the submission is validated, by
        # _render_anonymous_preview_saved. identity stays None as the
        # signal that no *_for_owner service call may run for this request.
        identity = None
    except DatabaseServiceError:
        current_app.logger.error("PeerSlate Workshop identity lookup failed.")
        return _render_workshop_unavailable()

    idempotency_key = request.form.get("idempotency_key") or str(uuid4())
    raw = {
        "title": request.form.get("title", ""),
        "wording": request.form.get("wording", ""),
        "classification": request.form.get("classification", ""),
    }
    save_action = request.form.get("save_action")

    def _rerender(error_message):
        return _review_response(
            mode="add",
            values=raw,
            idempotency_key=idempotency_key,
            item_key=None,
            expected_version_token=None,
            error_message=error_message,
            save_url=url_for("workshop.save_item"),
            keep_working_url=url_for("workshop.keep_working_add"),
            anonymous_preview=identity is None,
        )

    if save_action not in {"confirm", "unfinished"}:
        return _rerender(DEFAULT_FIELD_ERROR)

    try:
        title, wording, classification = validate_knowledge_item_input(
            raw["title"], raw["wording"], raw["classification"] or "unclassified"
        )
    except KnowledgeServiceError as error:
        return _rerender(FIELD_ERROR_MESSAGES.get(error.code, DEFAULT_FIELD_ERROR))

    if identity is None:
        # Owner instruction 2026-08-02 (doc 20 section 6e): a signed-out
        # visitor's add now really persists — but only to their own session,
        # never the database, never via save_knowledge_item_for_owner. Caps
        # are enforced server-side with an honest, specific message; nothing
        # is ever silently dropped.
        if len(wording) > workshop_demo_library.MAX_PREVIEW_WORDING_UNITS:
            return _rerender(workshop_demo_library.CAP_WORDING_MESSAGE)

        status = "confirmed" if save_action == "confirm" else "unfinished"
        new_item_key, error_message = workshop_demo_library.add_item(
            session,
            title=title,
            wording=wording,
            classification=classification,
            status=status,
        )
        if new_item_key is None:
            return _rerender(error_message)

        if save_action == "unfinished":
            return redirect(
                url_for(
                    "workshop.my_information",
                    item=new_item_key,
                    changed="unfinished-preview",
                )
            )
        return _render_anonymous_preview_saved(
            item_key=new_item_key,
            title=title,
            wording=wording,
            classification=classification,
        )

    if _workshop_dev_fixture_enabled():
        # Dev-preview seam only (PEERSLATE_WORKSHOP_DEV_FIXTURE, default off,
        # asserted off-by-default in tests): the local owner preview has no
        # database, so the confirmation renders from the validated submission
        # without persisting anything. Production never reaches this branch.
        if save_action == "confirm":
            return render_template(
                "workshop_saved.html",
                page_title="Saved privately — Workshop",
                item={
                    "item_key": None,
                    "title": title,
                    "body": wording,
                    "classification": classification,
                    "classification_label": CLASSIFICATION_LABELS.get(
                        classification, classification.title()
                    ),
                    "source_label": SOURCE_LABELS.get("typed", "Your words"),
                },
                view_in_my_information_url=url_for("workshop.my_information"),
                add_something_else_url=url_for("workshop.add_information"),
                close_for_now_url=url_for("workshop.my_information"),
                dev_preview=True,
            )
        return redirect(url_for("workshop.my_information", changed="unfinished"))

    try:
        result = knowledge_service.save_knowledge_item_for_owner(
            identity.user_key,
            idempotency_key,
            {
                "title": title,
                "approved_wording": wording,
                "original_wording": wording,
                "body_format": "plain",
                "classification": classification,
                "authored_via": "typed",
                "confirm": save_action == "confirm",
            },
        )
    except KnowledgeServiceError as error:
        return _rerender(FIELD_ERROR_MESSAGES.get(error.code, DEFAULT_FIELD_ERROR))
    except DatabaseServiceError:
        current_app.logger.error("PeerSlate Workshop save is unavailable.")
        return _rerender(UNAVAILABLE_FORM_MESSAGE)

    item_key = result["item_key"]
    if save_action == "confirm":
        return redirect(url_for("workshop.saved_item", item_key=item_key))
    return redirect(url_for("workshop.my_information", item=item_key, changed="unfinished"))


# ---------------------------------------------------------------------------
# Direct entry — Edit an existing item
# ---------------------------------------------------------------------------


@workshop.get("/app/workshop/items/<item_key>/edit")
def edit_information(item_key):
    if not _workshop_enabled():
        abort(404)
    normalized_item_key = _normalize_item_key(item_key)
    if not normalized_item_key:
        return redirect(url_for("workshop.my_information"))

    try:
        identity = get_current_identity()
    except AuthenticationRequired:
        # Owner instruction 2026-08-02 (doc 20 section 6e): Edit is now
        # real, session-scoped, and anonymous-capable — no sign-in redirect.
        identity = None
    except DatabaseServiceError:
        current_app.logger.error("PeerSlate Workshop identity lookup failed.")
        return _render_workshop_unavailable()

    if identity is None:
        delta = workshop_demo_library.read_session_delta(session)
        row = workshop_demo_library.get_row(normalized_item_key, delta)
        if row is None:
            # Never confirm or deny existence for an unrecognized key.
            return redirect(url_for("workshop.my_information"))
        return _composer_response(
            mode="edit",
            values={
                "title": row["title"],
                "wording": row["approved_wording"],
                "classification": row["classification"],
            },
            idempotency_key=None,
            item_key=normalized_item_key,
            expected_version_token=row["version_token"],
            error_message=None,
            form_action=url_for("workshop.review_edit", item_key=normalized_item_key),
            anonymous_preview=True,
        )

    try:
        item = knowledge_service.get_knowledge_item_for_owner(
            identity.user_key, normalized_item_key
        )
    except KnowledgeServiceError as error:
        if error.code == "not_found":
            # Never confirm or deny existence for a foreign/unknown key.
            return redirect(url_for("workshop.my_information"))
        current_app.logger.error("PeerSlate Workshop item edit lookup failed.")
        return _render_workshop_unavailable()
    except DatabaseServiceError:
        current_app.logger.error("PeerSlate Workshop item edit lookup failed.")
        return _render_workshop_unavailable()

    return _composer_response(
        mode="edit",
        values={
            "title": item["title"],
            "wording": item["approved_wording"],
            # MINOR 7 correction: "unclassified" now has its own explicit
            # "Not set" radio, so it is passed through directly rather than
            # converted to "" (which used to mean "leave the group
            # unselected" — now redundant with the explicit chip).
            "classification": item["classification"],
        },
        idempotency_key=None,
        item_key=normalized_item_key,
        expected_version_token=item["version_token"],
        error_message=None,
        form_action=url_for("workshop.review_edit", item_key=normalized_item_key),
    )


@workshop.post("/app/workshop/items/<item_key>/edit")
def keep_working_edit(item_key):
    if not _workshop_enabled():
        abort(404)
    if not _is_same_origin_write():
        return "Cross-site Workshop requests are not allowed.", 403
    normalized_item_key = _normalize_item_key(item_key)
    if not normalized_item_key:
        return redirect(url_for("workshop.my_information"))

    try:
        identity = get_current_identity()
    except AuthenticationRequired:
        identity = None
    except DatabaseServiceError:
        current_app.logger.error("PeerSlate Workshop identity lookup failed.")
        return _render_workshop_unavailable()

    return _composer_response(
        mode="edit",
        values={
            "title": request.form.get("title", ""),
            "wording": request.form.get("wording", ""),
            "classification": request.form.get("classification", ""),
        },
        idempotency_key=None,
        item_key=normalized_item_key,
        expected_version_token=request.form.get("expected_row_version", ""),
        error_message=None,
        form_action=url_for("workshop.review_edit", item_key=normalized_item_key),
        anonymous_preview=identity is None,
    )


@workshop.post("/app/workshop/items/<item_key>/edit/review")
def review_edit(item_key):
    if not _workshop_enabled():
        abort(404)
    if not _is_same_origin_write():
        return "Cross-site Workshop requests are not allowed.", 403
    normalized_item_key = _normalize_item_key(item_key)
    if not normalized_item_key:
        return redirect(url_for("workshop.my_information"))

    try:
        identity = get_current_identity()
    except AuthenticationRequired:
        identity = None
    except DatabaseServiceError:
        current_app.logger.error("PeerSlate Workshop identity lookup failed.")
        return _render_workshop_unavailable()

    is_anonymous = identity is None
    expected_version_token = request.form.get("expected_row_version", "")
    raw = {
        "title": request.form.get("title", ""),
        "wording": request.form.get("wording", ""),
        "classification": request.form.get("classification", ""),
    }

    try:
        title, wording, classification = validate_knowledge_item_input(
            raw["title"], raw["wording"], raw["classification"] or "unclassified"
        )
    except KnowledgeServiceError as error:
        return _composer_response(
            mode="edit",
            values=raw,
            idempotency_key=None,
            item_key=normalized_item_key,
            expected_version_token=expected_version_token,
            error_message=FIELD_ERROR_MESSAGES.get(error.code, DEFAULT_FIELD_ERROR),
            form_action=url_for("workshop.review_edit", item_key=normalized_item_key),
            anonymous_preview=is_anonymous,
        )

    if is_anonymous and len(wording) > workshop_demo_library.MAX_PREVIEW_WORDING_UNITS:
        return _composer_response(
            mode="edit",
            values=raw,
            idempotency_key=None,
            item_key=normalized_item_key,
            expected_version_token=expected_version_token,
            error_message=workshop_demo_library.CAP_WORDING_MESSAGE,
            form_action=url_for("workshop.review_edit", item_key=normalized_item_key),
            anonymous_preview=True,
        )

    return _review_response(
        mode="edit",
        values={"title": title, "wording": wording, "classification": classification},
        idempotency_key=None,
        item_key=normalized_item_key,
        expected_version_token=expected_version_token,
        error_message=None,
        save_url=url_for("workshop.update_item", item_key=normalized_item_key),
        keep_working_url=url_for("workshop.keep_working_edit", item_key=normalized_item_key),
        anonymous_preview=is_anonymous,
    )


@workshop.post("/app/workshop/items/<item_key>")
def update_item(item_key):
    """The confirming save for an edit (Save privately / Save unfinished)."""
    if not _workshop_enabled():
        abort(404)
    if not _is_same_origin_write():
        return "Cross-site Workshop requests are not allowed.", 403
    normalized_item_key = _normalize_item_key(item_key)
    if not normalized_item_key:
        return redirect(url_for("workshop.my_information"))

    try:
        identity = get_current_identity()
    except AuthenticationRequired:
        identity = None
    except DatabaseServiceError:
        current_app.logger.error("PeerSlate Workshop identity lookup failed.")
        return _render_workshop_unavailable()

    is_anonymous = identity is None
    expected_version_token = request.form.get("expected_row_version", "")
    raw = {
        "title": request.form.get("title", ""),
        "wording": request.form.get("wording", ""),
        "classification": request.form.get("classification", ""),
    }
    save_action = request.form.get("save_action")

    def _rerender(error_message, *, version_token=None):
        return _review_response(
            mode="edit",
            values=raw,
            idempotency_key=None,
            item_key=normalized_item_key,
            expected_version_token=version_token or expected_version_token,
            error_message=error_message,
            save_url=url_for("workshop.update_item", item_key=normalized_item_key),
            keep_working_url=url_for(
                "workshop.keep_working_edit", item_key=normalized_item_key
            ),
            anonymous_preview=is_anonymous,
        )

    if save_action not in {"confirm", "unfinished"}:
        return _rerender(DEFAULT_FIELD_ERROR)

    try:
        title, wording, classification = validate_knowledge_item_input(
            raw["title"], raw["wording"], raw["classification"] or "unclassified"
        )
    except KnowledgeServiceError as error:
        return _rerender(FIELD_ERROR_MESSAGES.get(error.code, DEFAULT_FIELD_ERROR))

    if is_anonymous:
        # Owner instruction 2026-08-02 (doc 20 section 6e): edit-confirm is
        # real within this visitor's own session — never
        # update_knowledge_item_for_owner, never the database.
        if len(wording) > workshop_demo_library.MAX_PREVIEW_WORDING_UNITS:
            return _rerender(workshop_demo_library.CAP_WORDING_MESSAGE)

        status = "confirmed" if save_action == "confirm" else "unfinished"
        ok, error_message = workshop_demo_library.edit_item(
            session,
            normalized_item_key,
            title=title,
            wording=wording,
            classification=classification,
            status=status,
        )
        if not ok:
            if error_message:
                return _rerender(error_message)
            # Item no longer in this visitor's session library (e.g.
            # deleted in another tab) — neutral fallback, never an error.
            return redirect(url_for("workshop.my_information"))

        changed = "updated-preview" if save_action == "confirm" else "unfinished-preview"
        return redirect(
            url_for("workshop.my_information", item=normalized_item_key, changed=changed)
        )

    try:
        knowledge_service.update_knowledge_item_for_owner(
            identity.user_key,
            normalized_item_key,
            expected_version_token,
            {
                "title": title,
                "approved_wording": wording,
                "body_format": "plain",
                "classification": classification,
                "confirm": save_action == "confirm",
            },
        )
    except KnowledgeServiceError as error:
        if error.code == "changed":
            # Member-safe conflict: never lose the member's submitted text,
            # and re-fetch a fresh version token so a retry can succeed.
            try:
                fresh = knowledge_service.get_knowledge_item_for_owner(
                    identity.user_key, normalized_item_key
                )
                fresh_token = fresh["version_token"]
            except (KnowledgeServiceError, DatabaseServiceError):
                fresh_token = expected_version_token
            return _rerender(CONFLICT_MESSAGE, version_token=fresh_token)
        return _rerender(FIELD_ERROR_MESSAGES.get(error.code, DEFAULT_FIELD_ERROR))
    except DatabaseServiceError:
        current_app.logger.error("PeerSlate Workshop update is unavailable.")
        return _rerender(UNAVAILABLE_FORM_MESSAGE)

    if save_action == "confirm":
        return redirect(url_for("workshop.saved_item", item_key=normalized_item_key))
    return redirect(
        url_for("workshop.my_information", item=normalized_item_key, changed="unfinished")
    )


# ---------------------------------------------------------------------------
# Saved confirmation
# ---------------------------------------------------------------------------


@workshop.get("/app/workshop/items/<item_key>/saved")
def saved_item(item_key):
    if not _workshop_enabled():
        abort(404)
    normalized_item_key = _normalize_item_key(item_key)
    if not normalized_item_key:
        return redirect(url_for("workshop.my_information"))

    try:
        identity = get_current_identity()
    except AuthenticationRequired:
        return_path = _safe_return_path(request.full_path.rstrip("?"))
        return redirect(url_for("auth.sign_in", return_to=return_path))
    except DatabaseServiceError:
        current_app.logger.error("PeerSlate Workshop identity lookup failed.")
        return _render_workshop_unavailable()

    try:
        item = knowledge_service.get_knowledge_item_for_owner(
            identity.user_key, normalized_item_key
        )
    except KnowledgeServiceError as error:
        if error.code == "not_found":
            return redirect(url_for("workshop.my_information"))
        current_app.logger.error("PeerSlate Workshop saved-confirmation lookup failed.")
        return _render_workshop_unavailable()
    except DatabaseServiceError:
        current_app.logger.error("PeerSlate Workshop saved-confirmation lookup failed.")
        return _render_workshop_unavailable()

    if item["status"] != "confirmed":
        # Never show "Saved privately" for an item that is not (or is no
        # longer) actually confirmed.
        return redirect(url_for("workshop.my_information", item=normalized_item_key))

    return render_template(
        "workshop_saved.html",
        page_title="Saved privately — Workshop",
        item={
            "item_key": normalized_item_key,
            "title": item["title"],
            "body": item["approved_wording"],
            "classification": item["classification"],
            "classification_label": CLASSIFICATION_LABELS.get(
                item["classification"], item["classification"].title()
            ),
            "source_label": SOURCE_LABELS.get(item["authored_via"], "Your words"),
        },
        view_in_my_information_url=url_for(
            "workshop.my_information", item=normalized_item_key
        ),
        add_something_else_url=url_for("workshop.add_information"),
        close_for_now_url=url_for("workshop.my_information"),
    )


# ---------------------------------------------------------------------------
# Archive / restore / delete
# ---------------------------------------------------------------------------


def _run_item_state_change(item_key, action):
    if not _workshop_enabled():
        abort(404)
    if not _is_same_origin_write():
        return "Cross-site Workshop requests are not allowed.", 403
    normalized_item_key = _normalize_item_key(item_key)
    if not normalized_item_key:
        return redirect(url_for("workshop.my_information"))

    try:
        identity = get_current_identity()
    except AuthenticationRequired:
        # Owner instruction 2026-08-02 (doc 20 section 6e): Archive/Restore
        # are now real, session-scoped, and anonymous-capable.
        identity = None
    except DatabaseServiceError:
        current_app.logger.error("PeerSlate Workshop identity lookup failed.")
        return _render_workshop_unavailable()

    if identity is None:
        mutator = (
            workshop_demo_library.archive_item
            if action == "archive"
            else workshop_demo_library.restore_item
        )
        ok, _error_message = mutator(session, normalized_item_key)
        if not ok:
            # Not part of this visitor's session library — never confirm or
            # deny why; a size-budget failure is vanishingly unlikely for
            # this tiny a mutation, so it gets the same neutral treatment.
            return redirect(url_for("workshop.my_information"))
        changed = "archived-preview" if action == "archive" else "restored-preview"
        return redirect(
            url_for("workshop.my_information", item=normalized_item_key, changed=changed)
        )

    expected_version_token = request.form.get("expected_row_version", "")
    method = (
        knowledge_service.archive_knowledge_item_for_owner
        if action == "archive"
        else knowledge_service.restore_knowledge_item_for_owner
    )
    try:
        method(identity.user_key, normalized_item_key, expected_version_token)
    except KnowledgeServiceError as error:
        if error.code in {"changed", "invalid"}:
            return redirect(
                url_for("workshop.my_information", item=normalized_item_key, error="changed")
            )
        current_app.logger.error("PeerSlate Workshop %s is unavailable.", action)
        return _render_workshop_unavailable()
    except DatabaseServiceError:
        current_app.logger.error("PeerSlate Workshop %s is unavailable.", action)
        return _render_workshop_unavailable()

    changed = "archived" if action == "archive" else "restored"
    return redirect(
        url_for("workshop.my_information", item=normalized_item_key, changed=changed)
    )


@workshop.post("/app/workshop/items/<item_key>/archive")
def archive_item(item_key):
    return _run_item_state_change(item_key, "archive")


@workshop.post("/app/workshop/items/<item_key>/restore")
def restore_item(item_key):
    return _run_item_state_change(item_key, "restore")


@workshop.get("/app/workshop/items/<item_key>/delete")
def delete_confirm(item_key):
    if not _workshop_enabled():
        abort(404)
    normalized_item_key = _normalize_item_key(item_key)
    if not normalized_item_key:
        return redirect(url_for("workshop.my_information"))

    try:
        identity = get_current_identity()
    except AuthenticationRequired:
        # Owner instruction 2026-08-02 (doc 20 section 6e): Delete is now
        # real, session-scoped, and anonymous-capable.
        identity = None
    except DatabaseServiceError:
        current_app.logger.error("PeerSlate Workshop identity lookup failed.")
        return _render_workshop_unavailable()

    if identity is None:
        delta = workshop_demo_library.read_session_delta(session)
        row = workshop_demo_library.get_row(normalized_item_key, delta)
        if row is None:
            return redirect(url_for("workshop.my_information"))
        return render_template(
            "workshop_delete_confirm.html",
            page_title="Delete information — Workshop",
            item_key=normalized_item_key,
            item_title=row["title"],
            expected_version_token=row["version_token"],
            cancel_url=url_for("workshop.my_information", item=normalized_item_key),
            delete_url=url_for("workshop.delete_item", item_key=normalized_item_key),
            error_message=WORKSHOP_VALIDATION_MESSAGES.get(request.args.get("error")),
            anonymous_preview=True,
        )

    try:
        item = knowledge_service.get_knowledge_item_for_owner(
            identity.user_key, normalized_item_key
        )
    except KnowledgeServiceError as error:
        if error.code == "not_found":
            return redirect(url_for("workshop.my_information"))
        current_app.logger.error("PeerSlate Workshop delete lookup failed.")
        return _render_workshop_unavailable()
    except DatabaseServiceError:
        current_app.logger.error("PeerSlate Workshop delete lookup failed.")
        return _render_workshop_unavailable()

    return render_template(
        "workshop_delete_confirm.html",
        page_title="Delete information — Workshop",
        item_key=normalized_item_key,
        item_title=item["title"],
        expected_version_token=item["version_token"],
        cancel_url=url_for("workshop.my_information", item=normalized_item_key),
        delete_url=url_for("workshop.delete_item", item_key=normalized_item_key),
        error_message=WORKSHOP_VALIDATION_MESSAGES.get(request.args.get("error")),
    )


@workshop.post("/app/workshop/items/<item_key>/delete")
def delete_item(item_key):
    if not _workshop_enabled():
        abort(404)
    if not _is_same_origin_write():
        return "Cross-site Workshop requests are not allowed.", 403
    normalized_item_key = _normalize_item_key(item_key)
    if not normalized_item_key:
        return redirect(url_for("workshop.my_information"))

    try:
        identity = get_current_identity()
    except AuthenticationRequired:
        identity = None
    except DatabaseServiceError:
        current_app.logger.error("PeerSlate Workshop identity lookup failed.")
        return _render_workshop_unavailable()

    if identity is None:
        if request.form.get("confirm_delete") != "delete":
            return redirect(
                url_for(
                    "workshop.delete_confirm",
                    item_key=normalized_item_key,
                    error="confirm-delete",
                )
            )
        ok, _error_message = workshop_demo_library.delete_item(session, normalized_item_key)
        if not ok:
            return redirect(url_for("workshop.my_information"))
        return redirect(url_for("workshop.my_information", changed="deleted-preview"))

    if request.form.get("confirm_delete") != "delete":
        return redirect(
            url_for(
                "workshop.delete_confirm",
                item_key=normalized_item_key,
                error="confirm-delete",
            )
        )

    expected_version_token = request.form.get("expected_row_version", "")
    try:
        knowledge_service.delete_knowledge_item_for_owner(
            identity.user_key, normalized_item_key, expected_version_token
        )
    except KnowledgeServiceError as error:
        if error.code in {"changed", "invalid"}:
            return redirect(
                url_for("workshop.my_information", item=normalized_item_key, error="changed")
            )
        current_app.logger.error("PeerSlate Workshop delete is unavailable.")
        return _render_workshop_unavailable()
    except DatabaseServiceError:
        current_app.logger.error("PeerSlate Workshop delete is unavailable.")
        return _render_workshop_unavailable()

    return redirect(url_for("workshop.my_information", changed="deleted"))


@workshop.after_request
def _keep_private_workshop_responses_out_of_caches(response):
    """Default every Workshop response to a private, non-stored policy.

    Mirrors owner_routes.py's ``_keep_private_owner_responses_out_of_caches``.
    Every route on this blueprint returns one signed-in member's own private
    library, so it must never be stored by a shared cache or replayed from
    the back/forward cache after sign-out.
    """
    response.headers.setdefault("Cache-Control", "private, no-store")
    return response


@workshop.app_context_processor
def workshop_navigation_state():
    """Expose the flag state and URL globally so base.html's nav can gate on it.

    Registered with ``app_context_processor`` (not ``context_processor``) so
    it runs for every template render in the app, not only Workshop's own
    routes — the same mechanism auth_routes.py's shared_authentication_state
    uses for ``current_member``. This does no identity lookup itself; the
    nav combines this flag with the already-injected ``current_member``.
    """
    return {
        "workshop_nav_enabled": _workshop_enabled(),
        "workshop_url": url_for("workshop.my_information"),
    }
