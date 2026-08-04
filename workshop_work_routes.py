"""Work on Something routes — PS-WORKSHOP-001 W2a + W2b.

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

**W2b: the real AI review loop.** ``POST /app/workshop/work/session/review``
replaces W2a's honest "AI review arrives next" holding card with a real,
validated model call (services/workshop_review_service.py), a follow-up
loop (answering the review's one useful question re-reviews; "Improve with
AI" proposes a labeled rewording the member accepts/edits/discards), and a
"Review final wording" handoff into the EXISTING W1 save path
(_review_response / save_item's underlying primitives, reused directly —
see work_session_finalize/work_session_save below). The review payload is
never stored server-side: it round-trips through the browser as a signed,
size-capped, 30-minute-expiring token (_sign_workshop_review_context /
_load_workshop_review_context below), mirroring app.py's
_sign_interview_model_context / _load_interview_model_context exactly
(architecture doc 17 section 4.2).

**Bounding AI spend (two different controls).** A per-session cap
(wws.MAX_AI_CALLS_PER_SESSION) is the courtesy budget for one honest visit;
it lives in the visitor's own cookie, so clearing that cookie resets it and
it is not a control against anyone who does not want to be bounded. The
durable ceilings live in services/workshop_spend_guard.py (F2 correction,
independent Opus review): a per-day cap per client address and, crucially, a
per-day cap across everyone combined, reserved server-side immediately
before each provider call. Reaching EITHER renders an honest cap state with
its own distinct copy, never an error — Save unfinished, Stop for now, Edit
myself, and Review final wording keep working regardless.

**Anonymous vs member.** Both share the SAME session-cookie work-state
mechanism (services/workshop_work_session.py). Where they differ: the
"Related confirmed information" rail, "Continue where I left off" list, and
AI grounding all read from workshop_demo_library's session-layered sample
library for an anonymous visitor, and from the real owner-scoped store
(services/knowledge_service.py) for a signed-in member — and every save
(Save unfinished, the W2b final Save privately/unfinished) writes to
whichever of those the identity resolves to, via the SAME existing save
primitives workshop_routes.py's direct-entry flow already uses
(workshop_demo_library.add_item / knowledge_service.
save_knowledge_item_for_owner). No ``*_for_owner`` service method is ever
called for an anonymous caller.
"""

import hashlib
import json
import os
from uuid import uuid4

from flask import (
    abort,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from itsdangerous import BadData, URLSafeTimedSerializer

from identity import AuthenticationRequired, get_current_identity
from services import workshop_demo_library
from services import workshop_review_service
from services import workshop_spend_guard
from services import workshop_voice_service
from services import workshop_work_session as wws
from services.database_service import DatabaseServiceError
from services.knowledge_service import (
    MAX_TITLE_UNITS,
    KnowledgeServiceError,
    knowledge_service,
    validate_knowledge_item_input,
)
from workshop_routes import (
    DEFAULT_FIELD_ERROR,
    FIELD_ERROR_MESSAGES,
    SOURCE_LABELS,
    UNAVAILABLE_FORM_MESSAGE,
    WORKSHOP_SUCCESS_MESSAGES,
    _is_same_origin_write,
    _normalize_item_key,
    _render_anonymous_preview_saved,
    _render_workshop_unavailable,
    _review_response,
    _safe_return_path,
    _workshop_voice_enabled,
    workshop,
)


RESET_VALIDATION_MESSAGES = {
    "confirm-reset": "Confirm before starting fresh.",
}

MAX_UNFINISHED_LIST = 5

# ---------------------------------------------------------------------------
# W2b: the signed, expiring review-context token (architecture doc 17
# section 4.2). Mirrors app.py's _sign_interview_model_context /
# _load_interview_model_context / interview_context_serializer exactly:
# URLSafeTimedSerializer, a 30-minute max age, and a size cap checked
# before any deserialization is attempted. The review payload is NEVER
# written to a database or to the session cookie — it exists only inside
# this token, which round-trips through a hidden form field in the
# browser. A tampered or expired token is never trusted; every caller
# treats a load failure as an honest "this review has expired" prompt to
# get a fresh one, never a 500 and never invented content.
#
# Signing key: same fallback idiom as app.py's INTERVIEW_CONTEXT_SIGNING_KEY
# / PEERSLATE_SESSION_SECRET_KEY — a dedicated env var if set, else a value
# deterministically derived from the already-required ANTHROPIC_API_KEY, so
# every worker/process signs and verifies the same token without a new
# mandatory production secret. This module (imported at app.py's line ~35,
# before app.py constructs its own `client`/serializers around line ~511)
# cannot import those app.py-level objects without a circular/ordering
# problem — see services/workshop_review_service.py's docstring for the
# identical reasoning about the Anthropic client.
#
# F6 correction (independent Opus review): if BOTH WORKSHOP_REVIEW_SIGNING_KEY
# and ANTHROPIC_API_KEY are unset/empty, the old code silently fell back to
# ``hashlib.sha256("peerslate-workshop-review-context-v1:")`` — a fixed
# constant fully computable by anyone who can read this source file, which
# would let that someone forge a signed review-context token. The key is
# now resolved lazily, at first actual sign/verify use, and raises a clear
# RuntimeError instead of ever falling back to that known constant.
# ---------------------------------------------------------------------------

MAX_REVIEW_TOKEN_CHARS = 12000
WORKSHOP_REVIEW_CONTEXT_MAX_AGE_SECONDS = 30 * 60


def _resolve_workshop_review_signing_key():
    """The signing key for the workshop review-context token, resolved
    fresh on every call (cheap: an env var read plus, at most, one SHA-256)
    so a test can freely patch ``os.environ`` between calls without needing
    to reimport this module.

    Prefers the dedicated ``WORKSHOP_REVIEW_SIGNING_KEY`` env var. Falls
    back to a value derived from ``ANTHROPIC_API_KEY`` when that dedicated
    key is not set (see module docstring above). Raises ``RuntimeError``
    rather than ever falling back to a fixed, source-derivable constant
    when BOTH are unset/empty — signing every token with a value anyone
    reading this file could compute would make the token's whole signature
    guarantee meaningless.
    """
    dedicated_key = os.environ.get("WORKSHOP_REVIEW_SIGNING_KEY")
    if dedicated_key:
        return dedicated_key
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    if not anthropic_key:
        raise RuntimeError(
            "Cannot sign or verify a Workshop review-context token: neither "
            "WORKSHOP_REVIEW_SIGNING_KEY nor ANTHROPIC_API_KEY is set. "
            "Refusing to fall back to a fixed, source-derivable signing key."
        )
    return hashlib.sha256(
        ("peerslate-workshop-review-context-v1:" + anthropic_key).encode("utf-8")
    ).hexdigest()


def _workshop_review_context_serializer():
    """A fresh ``URLSafeTimedSerializer`` built from the current signing
    key on every call. Raises ``RuntimeError`` (via
    ``_resolve_workshop_review_signing_key``) rather than constructing a
    serializer around a known-fallback key."""
    return URLSafeTimedSerializer(
        _resolve_workshop_review_signing_key(),
        salt="peerslate-workshop-review-context-v1",
    )

AI_UNAVAILABLE_MESSAGE = (
    "PeerSlate's review is unavailable right now. Your words are safe — "
    "save unfinished to keep them, or try Review what I shared again in a "
    "moment."
)
EXPIRED_REVIEW_MESSAGE = (
    "This review has expired. Choose Review what I shared again for a "
    "fresh one — nothing you wrote has been lost."
)


def _owner_key(identity):
    """The identity a review token is bound to: a member's own
    ``user_key``, or ``None`` for an anonymous visitor. One helper, used at
    every sign and every verify site, so the two can never drift apart."""
    return identity.user_key if identity is not None else None


def _sign_workshop_review_context(
    *, question_text, answer_snapshot, context_ids, review, owner_key=None
):
    """Sign one validated review (plus the inputs it was generated from)
    into an expiring token. ``review`` is the exact dict
    ``validate_workshop_review`` returned — already type/length-capped, so
    this token can never carry more than that validation already allows.

    ``owner_key`` binds the token to the identity it was issued to. The
    signing key is process-wide, so without this the token is a pure bearer
    token: presented from ANY session it would verify, and one member's
    review — derived from their answer and their own confirmed private
    items — would render beside a different member's working answer.
    ``_review_from_token`` compares this on every load, so a member's token
    is inert in anyone else's session.

    **Why identity and not a per-browser-session nonce.** A random nonce in
    the session cookie is the more thorough binding (it would separate two
    anonymous previews too), and it does not fit: the shared
    ``workshop_preview`` cookie budget (workshop_demo_library.
    MAX_SESSION_BYTES, an owner-instructed defensive ceiling) is already
    within a handful of bytes of its documented worst case — 4 library
    items at the 400-character cap plus a full 1000-unit answer — so adding
    even a 4-character nonce would push a legitimate maximal session over
    and get it refused as "full". Identity is derived server-side from the
    auth cookie and costs the session budget nothing.

    The residual, disclosed rather than hidden: two ANONYMOUS previews are
    bound only to each other's shared ``None``, so an anonymous token
    replays in another anonymous session. That is accepted here because an
    anonymous preview's content is the labelled sample library rather than
    anyone's private information; because every route that accepts a token
    requires a same-origin write, so a third party cannot inject one into a
    visitor's session; and because the token payload is signed, not
    encrypted, so whoever holds a token can already read the review it
    carries — replaying it reveals nothing they did not have. Closing that
    last gap needs headroom in the cookie budget or work-session state kept
    server-side; see the completion record.
    """
    context = {
        "question_text": question_text,
        "answer_snapshot": answer_snapshot,
        "context_ids": list(context_ids or []),
        "owner_key": owner_key,
        # F5 correction (independent Opus review): which items the review
        # actually DREW ON, as opposed to which were merely offered to it.
        # validate_workshop_review already computes and allow-list-checks
        # this, but nothing carried it forward, so the member could never
        # find out what their private information had been used for. Signed
        # into the token like every other field here, so a re-render after
        # Improve/accept/discard still tells them the same truth.
        "cited_context_ids": list(review.get("cited_context_ids") or []),
        "interpretation": review["interpretation"],
        "strong": list(review["strong"]),
        "standout": review["standout"],
        "strengthen": review["strengthen"],
        "question": review["question"],
    }
    return _workshop_review_context_serializer().dumps(context)


def _load_workshop_review_context(token):
    """The inverse of ``_sign_workshop_review_context``. Returns ``None``
    for anything missing, oversized, tampered, expired, or malformed —
    never raises for any of THOSE cases — so every caller can treat "no
    context" and "this review expired" identically: an honest re-review
    prompt, never a 500.

    F6 exception (independent Opus review): a misconfigured deployment
    missing BOTH signing-key env vars is not a user-influenced case like a
    tampered or expired token — it is an operator error that must be loud,
    not silently downgraded to an honest "expired" prompt (which would hide
    the misconfiguration indefinitely). ``RuntimeError`` from
    ``_resolve_workshop_review_signing_key`` is deliberately NOT caught
    here and propagates to the caller.
    """
    if not isinstance(token, str) or not token or len(token) > MAX_REVIEW_TOKEN_CHARS:
        return None
    try:
        context = _workshop_review_context_serializer().loads(
            token, max_age=WORKSHOP_REVIEW_CONTEXT_MAX_AGE_SECONDS
        )
    except BadData:
        return None
    if not isinstance(context, dict):
        return None
    required_text = ("question_text", "answer_snapshot", "interpretation", "standout", "strengthen", "question")
    if any(not isinstance(context.get(key), str) for key in required_text):
        return None
    if not isinstance(context.get("strong"), list) or any(
        not isinstance(item, str) for item in context["strong"]
    ):
        return None
    if not isinstance(context.get("context_ids"), list) or any(
        not isinstance(item, str) for item in context["context_ids"]
    ):
        return None
    cited = context.get("cited_context_ids", [])
    if not isinstance(cited, list) or any(not isinstance(item, str) for item in cited):
        return None
    owner_key = context.get("owner_key")
    if owner_key is not None and not isinstance(owner_key, str):
        return None
    context["owner_key"] = owner_key
    # Normalized rather than required, so a token signed before this field
    # existed still loads as an honest "nothing cited" instead of failing
    # shut and telling the member their review had expired when it had not.
    context["cited_context_ids"] = cited
    return context


def _review_from_token(token, owner_key=None):
    """The review dict (interpretation/strong/standout/strengthen/question)
    embedded in a signed token, or ``(None, None, None)`` if the token
    cannot be trusted.

    ``owner_key`` is the PRESENTING caller's identity (``identity.user_key``,
    or ``None`` for an anonymous visitor). It is compared, always and
    unconditionally, against the identity the token was signed for: one
    member's review can never render in another member's session, and a
    member's token is inert anonymously and vice versa. The comparison has
    no "skip when absent" branch — a caller that omits the argument
    compares against ``None``, which only matches a token signed
    anonymously. See ``_sign_workshop_review_context`` for why this is
    identity rather than a per-browser-session nonce, and what that leaves
    open between two anonymous previews.

    Returns the review dict alongside the ORIGINAL token
    string (unchanged, so a caller that only wants to re-render can pass the
    same token straight back into the hidden field without re-signing
    anything) and the ``answer_snapshot`` the review was actually generated
    from — the caller compares that snapshot against the CURRENT working
    answer (see ``_render_review_screen``'s ``is_stale_review`` computation)
    so a review re-rendered after the working answer has since changed
    (e.g. an accepted AI proposal) is never mislabeled as describing the
    member's current wording. (F1 correction, independent Opus review.)
    """
    context = _load_workshop_review_context(token)
    if context is None:
        return None, None, None
    if context["owner_key"] != owner_key:
        return None, None, None
    review = {
        "interpretation": context["interpretation"],
        "strong": context["strong"],
        "standout": context["standout"],
        "strengthen": context["strengthen"],
        "question": context["question"],
        "cited_context_ids": context["cited_context_ids"],
    }
    return review, token, context["answer_snapshot"]


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


def _grounding_items(identity, selected_ids):
    """The full {id, title, wording} rows for the CURRENTLY selected "Use
    as context" ids — architecture doc 17 section 9.1's bounded,
    id-addressable grounding set. ``selected_ids`` is already validated
    against the visible confirmed-item allow-list by the caller
    (context_mask_from_ids/context_ids_from_mask never surface a foreign
    id), and already bounded to wws.MAX_CONTEXT_ITEMS (8), itself under
    workshop_review_service.MAX_CONTEXT_ITEMS (10) — so this never needs a
    second cap. Grounding is state-filtered here too: only a CONFIRMED,
    non-archived row is ever included, even if a stale selection somehow
    pointed at an item that has since been archived/deleted. Wording is
    always the plain-text ``approved_wording`` (architecture section 8's
    "AI grounding uses the plain-text projection, never the markup").

    May raise KnowledgeServiceError/DatabaseServiceError for a member
    (never for a not_found single item, which is silently skipped, mirroring
    _lookup_unfinished_row's "never confirm/deny a foreign id" discipline)
    — callers treat any other failure as real, same discipline as
    _confirmed_rows.
    """
    items = []
    if identity is None:
        delta = workshop_demo_library.read_session_delta(session)
        for item_id in selected_ids:
            row = workshop_demo_library.get_row(item_id, delta)
            if row and row["status"] == "confirmed":
                items.append(
                    {"id": row["item_key"], "title": row["title"], "wording": row["approved_wording"]}
                )
        return items

    for item_id in selected_ids:
        try:
            row = knowledge_service.get_knowledge_item_for_owner(identity.user_key, item_id)
        except KnowledgeServiceError as error:
            if error.code == "not_found":
                continue
            raise
        if row["status"] == "confirmed":
            items.append(
                {"id": row["item_key"], "title": row["title"], "wording": row["approved_wording"]}
            )
    return items


# ---------------------------------------------------------------------------
# Spark — PS-WORKSHOP-001 W2c
#
# **The rule the whole slice turns on: a Spark that cannot be grounded is
# not shown.** There is no ungrounded, no partially-grounded, and no
# "PeerSlate thought you might like" Spark anywhere below. A visitor with no
# confirmed information gets the ordinary first-run opening and NO provider
# call is made — not a call whose result is discarded, no call at all.
#
# **How often a Spark costs money.** Once per visit, automatically, and
# after that only when the visitor explicitly asks. The opening caches the
# Spark it generated (services/workshop_work_session.py's Spark bucket), so
# reloading, navigating back, or being redirected here after Stop for now
# re-renders the SAME Spark for free. Without that cache every landing on
# this page would bill a call and a visitor could exhaust their own daily
# allowance — and therefore their AI review allowance too — by refreshing.
# Once a Spark has been offered this visit, the opening never auto-generates
# another; "Show another idea" and the "Give me a spark" door are how a
# visitor asks, and both are rate-limited and spend-guarded.
#
# **What Spark is NOT bounded by.** The per-session AI call cap
# (wws.MAX_AI_CALLS_PER_SESSION) lives in the Work on Something session
# bucket, which usually does not exist on the opening — there is no session
# yet. Spark is therefore bounded by the rate limit (4/min, app.py) and by
# the durable daily ceilings in services/workshop_spend_guard.py, which are
# the controls that actually bound a bill. Every Spark provider call
# reserves through the guard immediately before it is made.
# ---------------------------------------------------------------------------

SPARK_NO_IDEA_NOTE = (
    "No Spark right now. Choose “Give me a spark” whenever you want a "
    "new idea grounded in the information you have confirmed."
)
SPARK_UNAVAILABLE_NOTE = (
    "PeerSlate could not offer a grounded suggestion just now. Everything "
    "else on this screen works as usual, and you can try again in a moment."
)
SPARK_DAILY_CAP_NOTE = (
    "PeerSlate has reached today's limit for AI suggestions across the whole "
    "preview. This is a daily limit, not something you did wrong — everything "
    "else on this screen works as usual."
)
SPARK_EXHAUSTED_NOTE = (
    "PeerSlate has offered every grounded idea it can draw from your "
    "confirmed information this visit. Adding or confirming something new "
    "gives it more to work from."
)


def _spark_view(spark_state_current, confirmed_rows):
    """The template's view-model for the Spark currently on screen, or None.

    The cited items are re-resolved from the rows this viewer can see RIGHT
    NOW rather than from anything stored with the Spark. An item confirmed
    when the Spark was generated but archived or deleted since simply stops
    appearing in "Prompted by confirmed information" — the same discipline
    the review screen's cited-context disclosure follows. A Spark whose
    citations ALL stop resolving is dropped entirely: its grounding claim is
    the only thing that makes it honest, and a Spark that cannot show what
    prompted it is exactly what this slice refuses to render.
    """
    if not spark_state_current:
        return None
    cited = set(spark_state_current["cited_fingerprints"])
    cited_titles = [
        row["title"] for row in confirmed_rows if wws.item_fingerprint(row["item_key"]) in cited
    ]
    if not cited_titles:
        return None
    return {
        "suggestion": spark_state_current["suggestion"],
        "focus_seed": spark_state_current["focus_seed"],
        "fingerprint": spark_state_current["fingerprint"],
        "cited_titles": cited_titles,
    }


def _generate_spark(identity, confirmed_rows):
    """Generate, validate, and remember ONE Spark. Returns
    ``(spark_view_or_None, note_or_None)`` and never raises: every failure
    path here degrades to "no Spark plus an honest note", because a Spark
    failure must never take the opening down with it.
    """
    if not confirmed_rows:
        return None, None

    spark_state = wws.read_spark_state(session)
    visible_ids = [row["item_key"] for row in confirmed_rows]

    try:
        context_items = _grounding_items(identity, visible_ids)
    except (KnowledgeServiceError, DatabaseServiceError):
        current_app.logger.error("PeerSlate Workshop Spark grounding is unavailable.")
        return None, SPARK_UNAVAILABLE_NOTE
    if not context_items:
        # Every confirmed row disappeared between the list read and the
        # per-item read. Honest no-Spark, and crucially no provider call.
        return None, None

    allowed_ids = [item["id"] for item in context_items]
    exclude_ids = wws.excluded_item_keys(spark_state, allowed_ids)
    if len(exclude_ids) >= len(allowed_ids):
        # Every item this viewer has confirmed already prompted a Spark this
        # visit. Saying so honestly is both truthful and free; asking the
        # model for a "different" idea from exhausted material would just
        # bill a call to produce a near-repeat that the offered-fingerprint
        # check would then reject anyway.
        return None, SPARK_EXHAUSTED_NOTE

    refusal_note = _reserve_daily_spark_spend()
    if refusal_note is not None:
        return None, refusal_note

    raw_reply, stop_reason = "", ""
    try:
        raw_json, raw_reply, stop_reason = workshop_review_service.generate_spark(
            context_items, exclude_ids
        )
        spark = workshop_review_service.validate_workshop_spark(
            raw_json, allowed_context_ids=allowed_ids
        )
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        workshop_review_service._log_workshop_failure(
            current_app.logger, "Workshop spark validation error", error, stop_reason, len(raw_reply)
        )
        return None, SPARK_UNAVAILABLE_NOTE
    except Exception as error:  # noqa: BLE001 - provider/network failure
        workshop_review_service._log_workshop_failure(
            current_app.logger, "Workshop spark API error", error, stop_reason, len(raw_reply)
        )
        return None, SPARK_UNAVAILABLE_NOTE

    fingerprint = wws.spark_fingerprint(spark["suggestion"])
    if wws.already_offered(spark_state, fingerprint):
        # The model repeated something this visitor has already seen or
        # dismissed. This is the hard guarantee behind "a dismissed Spark
        # never returns": it does not depend on the model cooperating with
        # the exclusion hint, and it never retries — a retry loop would turn
        # one click into an unbounded number of billed calls.
        current_app.logger.info(
            "Workshop spark suppressed: reason=already_offered"
        )
        return None, SPARK_EXHAUSTED_NOTE

    wws.record_spark(
        session,
        suggestion=spark["suggestion"],
        focus_seed=spark["focus_seed"],
        cited_item_keys=spark["cited_context_ids"],
    )
    return (
        _spark_view(
            {
                "fingerprint": fingerprint,
                "suggestion": spark["suggestion"],
                "focus_seed": spark["focus_seed"],
                "cited_fingerprints": [
                    wws.item_fingerprint(key) for key in spark["cited_context_ids"]
                ],
            },
            confirmed_rows,
        ),
        None,
    )


def _reserve_daily_spark_spend():
    """Reserve one Spark call against the durable daily ceilings. Returns
    ``None`` when the call may proceed, or an honest note when it may not.

    Deliberately returns a NOTE rather than a rendered response (unlike
    ``_reserve_daily_ai_spend``, its review-loop sibling): a refused review
    is the whole point of the screen the member asked for, while a refused
    Spark is one quiet absence on an opening screen whose doors, composer,
    and library links must all keep working regardless.
    """
    outcome = workshop_spend_guard.reserve(workshop_spend_guard.client_ip())
    if outcome == workshop_spend_guard.RESERVE_OK:
        return None
    current_app.logger.warning(
        "Workshop Spark daily spend ceiling refused a call: outcome=%s", outcome
    )
    return SPARK_DAILY_CAP_NOTE


def _resolve_opening_spark(identity, confirmed_rows):
    """What the opening should show in the Spark position, and whether that
    costs a provider call. Returns ``(spark_view_or_None, note_or_None)``.
    """
    if _ai_unavailable_test_seam_requested():
        return None, None

    spark_state = wws.read_spark_state(session)

    cached = _spark_view(spark_state["current"], confirmed_rows)
    if cached is not None:
        return cached, None

    if not confirmed_rows:
        # The R05/R06 first-run composition says this honestly on its own —
        # no note needed, and no AI call is made.
        return None, None

    if spark_state["offered"]:
        # A Spark has already been offered this visit and is no longer on
        # screen (dismissed, replaced, or its cited items are gone). The
        # opening never silently generates another; the visitor asks.
        return None, SPARK_NO_IDEA_NOTE

    return _generate_spark(identity, confirmed_rows)


def _door_view_model(*, unfinished_rows, ai_unavailable, spark_available):
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
        # PS-WORKSHOP-001 W2c: the Spark door is real now, but only for a
        # viewer who actually has confirmed information for it to draw on.
        # With nothing confirmed it stays inert and says why, rather than
        # offering a button whose only possible outcome is a refusal.
        "spark": {
            "available": spark_available,
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
    generate_spark=False,
    spark=None,
    spark_note=None,
):
    """Render the Work on Something opening.

    ``generate_spark`` is opt-in, and only ``work_opening`` (the GET) passes
    it. Every other caller here is re-rendering the opening to show an error
    or a confirmation, and none of them should bill a provider call to do
    it — a failed session start must not also spend money. Those callers
    still show a Spark if one is already cached, because
    ``_resolve_opening_spark`` returns the cache before it considers
    generating anything.
    """
    unfinished_rows = _unfinished_rows(identity)
    related_rows = _confirmed_rows(identity)
    ai_unavailable = _ai_unavailable_test_seam_requested()

    if spark is None and spark_note is None:
        if generate_spark:
            spark, spark_note = _resolve_opening_spark(identity, related_rows)
        else:
            spark = _spark_view(wws.read_spark_state(session)["current"], related_rows)

    return (
        render_template(
            "workshop_work.html",
            page_title="Work on Something — Workshop",
            active_workshop_mode="work",
            anonymous_preview=(identity is None),
            ai_unavailable=ai_unavailable,
            doors=_door_view_model(
                unfinished_rows=unfinished_rows,
                ai_unavailable=ai_unavailable,
                spark_available=bool(related_rows) and not ai_unavailable,
            ),
            spark=spark,
            spark_note=spark_note,
            spark_another_url=url_for("workshop.work_spark_another"),
            spark_dismiss_url=url_for("workshop.work_spark_dismiss"),
            door_spark=wws.DOOR_SPARK,
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
            generate_spark=True,
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
    elif door == wws.DOOR_SPARK:
        # "Work on this". The seed comes from the Spark THIS PROCESS
        # generated and validated, read back from the session — never from
        # the form. A hand-rolled POST therefore cannot seed a session with
        # arbitrary text and have it carry a Spark's provenance, and the
        # seeded text can never be anything the Spark validator did not
        # already cap and strip.
        spark_state = wws.read_spark_state(session)
        if not spark_state["current"]:
            # Neutral fallback, matching the resume path above: never
            # confirms or denies why a Spark is not there.
            return redirect(url_for("workshop.work_opening"))
        seed = spark_state["current"]["focus_seed"]
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

    if door == wws.DOOR_SPARK:
        # The Spark has been taken up, so it leaves the opening — while
        # staying in the offered list, so it is never suggested again.
        wws.clear_current_spark(session)
        # The working answer starts as PeerSlate's words, not the member's.
        # Marking the session AI-assisted now means that if they save it
        # barely changed, it is labelled honestly ("Your words, refined with
        # AI assistance") rather than as something they typed unaided. A
        # Spark seed is a starting thought and never confirmed information:
        # nothing has been written to any library by this point.
        wws.mark_ai_assisted(session)

    return redirect(url_for("workshop.work_session_screen"))


# ---------------------------------------------------------------------------
# Spark endpoints. Both are same-origin-only and rate-limited (app.py, 4/min
# — the brief's explicit "spark 4/min"). Only "another" costs a provider
# call; dismissal is pure local memory and deliberately never generates a
# replacement, because immediately answering "do not suggest this again"
# with another suggestion is the nagging the brief rules out.
# ---------------------------------------------------------------------------


@workshop.post("/app/workshop/work/spark/another")
def work_spark_another():
    """"Show another idea", and the "Give me a spark" door — one endpoint,
    because they are the same request: retire whatever Spark is on screen
    and ask for one grounded somewhere the visitor has not been offered yet.
    """
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

    # Retire the current Spark BEFORE generating: it stays in the offered
    # list, so the replacement can never be the same one.
    wws.clear_current_spark(session)

    try:
        confirmed_rows = _confirmed_rows(identity)
        spark, spark_note = _generate_spark(identity, confirmed_rows)
        return _render_opening(identity=identity, spark=spark, spark_note=spark_note)
    except (KnowledgeServiceError, DatabaseServiceError):
        current_app.logger.error("PeerSlate Work on Something opening is unavailable.")
        return _render_workshop_unavailable()


@workshop.post("/app/workshop/work/spark/dismiss")
def work_spark_dismiss():
    """"Do not suggest this again." Records the dismissal and shows the
    opening without a Spark. No provider call, and no replacement.

    The fingerprint is read from the form and cross-checked against the
    Spark actually on screen. A forged value can only ever suppress a
    suggestion in the forger's own session, so it is accepted rather than
    rejected — but the on-screen Spark is dismissed regardless, so the
    button always does what it says even if the field is missing or stale.
    """
    if not _work_flag_gate():
        abort(404)
    if not _is_same_origin_write():
        return "Cross-site Workshop requests are not allowed.", 403

    try:
        get_current_identity()
    except AuthenticationRequired:
        pass
    except DatabaseServiceError:
        current_app.logger.error("PeerSlate Workshop identity lookup failed.")
        return _render_workshop_unavailable()

    spark_state = wws.read_spark_state(session)
    current = spark_state["current"]
    submitted = (request.form.get("spark_fingerprint") or "").strip()[:32]
    fingerprint = current["fingerprint"] if current else submitted

    wws.dismiss_spark(session, fingerprint)
    if submitted and current and submitted != current["fingerprint"]:
        # A stale form (the Spark changed in another tab). Both are barred.
        wws.dismiss_spark(session, submitted)

    return redirect(url_for("workshop.work_opening", changed="spark-dismissed"))


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
            # F9 correction: the field accepts wws.MAX_ANSWER_UNITS, but an
            # anonymous preview SAVE keeps only this many — the template
            # states the difference up front, and only for a visitor it
            # actually applies to.
            preview_wording_units=workshop_demo_library.MAX_PREVIEW_WORDING_UNITS,
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
            review_url=url_for("workshop.work_session_review"),
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

    return _render_session_screen(
        identity=identity,
        state=state,
        answer_override=answer,
        selected_ids_override=set(valid_selected_ids),
        error_message=DEFAULT_FIELD_ERROR,
        status_code=400,
    )


@workshop.get("/app/workshop/work/session/review")
def work_session_review_redirect():
    """GET on this path is superseded by the real POST AI-review flow
    below (PS-WORKSHOP-001 W2b — "replaces the holding state", see this
    module's own docstring). Nothing useful can be shown from a bare GET:
    the review itself is never stored server-side, only inside a signed
    token the browser already holds (or does not). This neutrally sends
    the visitor to the session screen, which itself redirects to the
    opening when no session is active — never a Werkzeug 405, so flag-off
    still 404s here exactly like every other /work/* route.
    """
    if not _work_flag_gate():
        abort(404)
    return redirect(url_for("workshop.work_session_screen"))


def _review_screen_related_items(identity, state):
    """The "Related information" rail's view-model for the review screen —
    same rows/order as the session screen's own rail, but read-only here
    (this slice does not rebuild an interactive "Use as context" control a
    second time on the review screen; the session screen remains the one
    place selection changes, and the review screen's forms carry the
    CURRENT selection forward as hidden fields — see
    workshop_work_review.html's own comment). May raise
    KnowledgeServiceError/DatabaseServiceError for a member; callers treat
    that as a real failure, same discipline as _confirmed_rows.
    """
    related_rows = _confirmed_rows(identity)
    visible_ids = [row["item_key"] for row in related_rows]
    selected_ids = set(wws.context_ids_from_mask(state["context_mask"], visible_ids))
    return [
        {"item_key": row["item_key"], "title": row["title"], "selected": row["item_key"] in selected_ids}
        for row in related_rows
    ]


def _render_review_screen(
    *,
    identity,
    state,
    screen_state,
    review=None,
    review_token=None,
    answer_snapshot=None,
    proposal=None,
    followup_answer_value="",
    error_message=None,
    cap_message=None,
    cap_title=None,
    status_code=200,
):
    """Render the real AI review screen (workshop_work_review.html),
    branching on an explicit ``screen_state`` field — the "server-rendered
    state panels branching on an explicit state field" pattern architecture
    doc 17 section 7 calls for:

    - "review": the full R09/R10 composition (interpretation, strong,
      standout, strengthen, one useful question, an optional pending
      Improve-with-AI proposal).
    - "cap_reached": an honest AI-call-cap message — Save unfinished, Stop
      for now, Edit myself, and Review final wording all still work; only
      Improve and a fresh review are unavailable. Two DIFFERENT caps render
      through this one state, and ``cap_message``/``cap_title`` say which:
      the per-visit session cap (wws.AI_CALL_CAP_MESSAGE, the default) and
      the durable daily ceiling (workshop_spend_guard.DAILY_CAP_MESSAGE,
      F2 correction). They are not the same fact — starting fresh clears
      the first and does nothing at all to the second — so they must never
      render as the same sentence.
    - "unavailable": a real provider/validation failure — same actions
      still available, architecture section 9.3's "never a skeleton loader
      that implies a pending result."
    - "expired": the signed review token was missing, tampered, or past its
      30-minute age — an honest prompt to get a fresh review, member text
      untouched.

    Every state shows the member's current working answer
    (``state["answer"]``) intact — no state here ever discards it.

    ``answer_snapshot`` (F1 correction, independent Opus review): the
    ``answer_snapshot`` recovered from ``review_token`` via
    ``_review_from_token``, when this call is re-rendering an EXISTING
    review rather than one freshly generated this request. A fresh review
    just generated from the current answer has no reason to pass this (it
    is trivially never stale). When it IS passed and no longer matches
    ``state["answer"]`` — the working answer has moved on since this review
    was generated, most commonly because an AI improvement proposal was
    just accepted into it — the template must not label that text "Your
    original wording": it may now be entirely AI-authored, not the
    member's own original words. The template instead labels the block
    "Your current wording" and shows an honest note that the review below
    describes the member's earlier wording.
    """
    # Every call site below (including several inside try/except blocks
    # that also guard OTHER calls) relies on this function never raising
    # KnowledgeServiceError/DatabaseServiceError itself — centralizing the
    # guard here, rather than repeating it at every one of this function's
    # many call sites, is what makes that safe by construction.
    try:
        related_items = _review_screen_related_items(identity, state)
    except (KnowledgeServiceError, DatabaseServiceError):
        current_app.logger.error("PeerSlate Work on Something review is unavailable.")
        return _render_workshop_unavailable()
    is_stale_review = (
        screen_state == "review"
        and review is not None
        and answer_snapshot is not None
        and answer_snapshot != state["answer"]
    )
    # F5 correction: name the private items this review actually drew on.
    # Only an item still visible on this member's own rail can be named —
    # an id that no longer resolves is silently omitted rather than shown as
    # a bare identifier, which would be noise rather than an answer, and
    # would confirm the existence of something no longer theirs to see.
    cited_ids = set((review or {}).get("cited_context_ids") or [])
    cited_context_titles = [
        item["title"] for item in related_items if item["item_key"] in cited_ids
    ]
    return (
        render_template(
            "workshop_work_review.html",
            page_title="Here's what PeerSlate heard — Workshop",
            active_workshop_mode="work",
            anonymous_preview=(identity is None),
            screen_state=screen_state,
            question_text=state["question_text"],
            answer_value=state["answer"],
            review=review,
            review_token=review_token or "",
            is_stale_review=is_stale_review,
            cited_context_titles=cited_context_titles,
            proposal=proposal,
            followup_answer_value=followup_answer_value,
            related_items=related_items,
            error_message=error_message,
            ai_unavailable_message=AI_UNAVAILABLE_MESSAGE,
            cap_message=cap_message or wws.AI_CALL_CAP_MESSAGE,
            cap_title=cap_title or "Preview limit reached",
            expired_message=EXPIRED_REVIEW_MESSAGE,
            review_url=url_for("workshop.work_session_review"),
            improve_url=url_for("workshop.work_session_improve"),
            finalize_url=url_for("workshop.work_session_finalize"),
            update_url=url_for("workshop.update_work_session"),
            back_url=url_for("workshop.work_session_screen"),
        ),
        status_code,
    )


def _reserve_daily_ai_spend(identity, state):
    """Reserve one call against the durable daily ceilings (F2 correction,
    independent Opus review) immediately before a provider call.

    Returns ``None`` when the call may proceed, or an already-rendered
    honest "today's preview limit" response when it may not. The refusal
    reuses the EXISTING cap_reached composition — the member's words stay on
    screen, and Save unfinished, Stop for now, Edit myself, and Review final
    wording all keep working — with copy that names the DAILY limit rather
    than the per-visit session cap, because telling someone to "start fresh"
    would be a false promise against a ceiling starting fresh cannot lift.

    Every call site places this as late as possible, immediately before
    ``client.messages.create``, so a request that is going to fail for some
    unrelated reason first (a grounding lookup, a session write) never
    consumes a slot from the day's global budget without a provider call
    actually being attempted.
    """
    outcome = workshop_spend_guard.reserve(workshop_spend_guard.client_ip())
    if outcome == workshop_spend_guard.RESERVE_OK:
        return None
    # Low-cardinality and privacy-safe: an outcome label only, never the
    # address, the member's text, or any count.
    current_app.logger.warning(
        "Workshop AI daily spend ceiling refused a call: outcome=%s", outcome
    )
    return _render_review_screen(
        identity=identity,
        state=state,
        screen_state="cap_reached",
        cap_message=workshop_spend_guard.DAILY_CAP_MESSAGE,
        cap_title=workshop_spend_guard.DAILY_CAP_TITLE,
    )


@workshop.post("/app/workshop/work/session/review")
def work_session_review():
    """The real AI review loop's main endpoint (PS-WORKSHOP-001 W2b).

    Three sub-actions share this one endpoint because all three need the
    SAME "load state, load any incoming review token" preamble, and only
    the first ever calls the model:

    1. Normal submission (no ``discard_proposal``/``accept_proposal``
       field): persists the current answer/context — optionally with a
       follow-up-question answer appended (capped, honest message at cap)
       — then calls the AI for a fresh review, counted against the
       per-session cap.
    2. ``accept_proposal=1``: replaces the working answer with the
       (possibly member-edited) proposed wording, marks the session
       ai_assisted, and re-renders the EXISTING review from its token —
       no new AI call.
    3. ``discard_proposal=1``: re-renders the EXISTING review from its
       token, dropping the proposal — no new AI call, no session change.
    """
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

    incoming_token = request.form.get("review_token")

    if request.form.get("discard_proposal") == "1":
        review, token, answer_snapshot = _review_from_token(incoming_token, _owner_key(identity))
        try:
            if review is None:
                return _render_review_screen(identity=identity, state=state, screen_state="expired")
            return _render_review_screen(
                identity=identity,
                state=state,
                screen_state="review",
                review=review,
                review_token=token,
                answer_snapshot=answer_snapshot,
            )
        except (KnowledgeServiceError, DatabaseServiceError):
            current_app.logger.error("PeerSlate Work on Something review is unavailable.")
            return _render_workshop_unavailable()

    if request.form.get("accept_proposal") == "1":
        proposed_wording = request.form.get("proposed_wording", "")
        review, token, answer_snapshot = _review_from_token(incoming_token, _owner_key(identity))
        try:
            if review is None:
                return _render_review_screen(identity=identity, state=state, screen_state="expired")
            ok, update_error = wws.update_session(
                session, answer=proposed_wording, context_mask=state["context_mask"]
            )
            if ok:
                wws.mark_ai_assisted(session)
                state = wws.read_state(session)
            return _render_review_screen(
                identity=identity,
                state=state,
                screen_state="review",
                review=review,
                review_token=token,
                answer_snapshot=answer_snapshot,
                error_message=None if ok else (update_error or DEFAULT_FIELD_ERROR),
                status_code=200 if ok else 400,
            )
        except (KnowledgeServiceError, DatabaseServiceError):
            current_app.logger.error("PeerSlate Work on Something review is unavailable.")
            return _render_workshop_unavailable()

    # Normal path: persist the current answer/context (optionally with a
    # follow-up-question answer appended), then call the AI for a fresh
    # review.
    answer = request.form.get("answer", state["answer"])
    followup = request.form.get("followup_answer", "").strip()
    if followup:
        answer = (answer.rstrip() + "\n\n" + followup).strip() if answer.strip() else followup

    try:
        related_rows = _confirmed_rows(identity)
    except (KnowledgeServiceError, DatabaseServiceError):
        current_app.logger.error("PeerSlate Work on Something review is unavailable.")
        return _render_workshop_unavailable()
    visible_ids = [row["item_key"] for row in related_rows]
    submitted_ids = request.form.getlist("context")
    valid_selected_ids = [item_id for item_id in submitted_ids if item_id in visible_ids]
    context_mask = wws.context_mask_from_ids(valid_selected_ids, visible_ids)

    ok, update_error = wws.update_session(session, answer=answer, context_mask=context_mask)
    if not ok:
        if incoming_token:
            try:
                previous_review, previous_token, previous_answer_snapshot = _review_from_token(
                    incoming_token, _owner_key(identity)
                )
            except Exception:  # noqa: BLE001 - defensive; token loading itself never raises
                previous_review, previous_token, previous_answer_snapshot = None, None, None
            if previous_review is None:
                return _render_review_screen(identity=identity, state=state, screen_state="expired")
            return _render_review_screen(
                identity=identity,
                state=state,
                screen_state="review",
                review=previous_review,
                review_token=previous_token,
                answer_snapshot=previous_answer_snapshot,
                followup_answer_value=followup,
                error_message=update_error or DEFAULT_FIELD_ERROR,
                status_code=400,
            )
        return _render_session_screen(
            identity=identity,
            state=state,
            answer_override=answer,
            selected_ids_override=set(valid_selected_ids),
            error_message=update_error or DEFAULT_FIELD_ERROR,
            status_code=400,
        )
    state = wws.read_state(session)

    if wws.at_ai_call_cap(state):
        return _render_review_screen(identity=identity, state=state, screen_state="cap_reached")
    reserved_ok, _reserve_error = wws.increment_ai_calls(session)
    if not reserved_ok:
        return _render_review_screen(identity=identity, state=state, screen_state="cap_reached")
    state = wws.read_state(session)

    try:
        context_items = _grounding_items(identity, valid_selected_ids)
    except (KnowledgeServiceError, DatabaseServiceError):
        current_app.logger.error("PeerSlate Work on Something grounding is unavailable.")
        return _render_workshop_unavailable()

    refusal = _reserve_daily_ai_spend(identity, state)
    if refusal is not None:
        return refusal

    raw_reply, stop_reason = "", ""
    try:
        raw_json, raw_reply, stop_reason = workshop_review_service.generate_review(
            answer, state["question_text"], context_items
        )
        review = workshop_review_service.validate_workshop_review(
            raw_json, allowed_context_ids=[item["id"] for item in context_items]
        )
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        workshop_review_service._log_workshop_failure(
            current_app.logger, "Workshop review validation error", error, stop_reason, len(raw_reply)
        )
        return _render_review_screen(identity=identity, state=state, screen_state="unavailable")
    except Exception as error:  # noqa: BLE001 - provider/network failure, see module docstring
        workshop_review_service._log_workshop_failure(
            current_app.logger, "Workshop review API error", error, stop_reason, len(raw_reply)
        )
        return _render_review_screen(identity=identity, state=state, screen_state="unavailable")

    review_token = _sign_workshop_review_context(
        question_text=state["question_text"],
        answer_snapshot=answer,
        context_ids=valid_selected_ids,
        review=review,
        owner_key=_owner_key(identity),
    )
    return _render_review_screen(
        identity=identity, state=state, screen_state="review", review=review, review_token=review_token
    )


@workshop.post("/app/workshop/work/session/improve")
def work_session_improve():
    """"Improve with AI": one labeled proposal beside the member's own
    text, generated from the review context already shown (never new
    grounding). Never overwrites the working answer itself — only
    ``accept_proposal`` (handled in ``work_session_review`` above) does
    that, and only on the member's explicit choice."""
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

    incoming_token = request.form.get("review_token")
    try:
        review, token, answer_snapshot = _review_from_token(incoming_token, _owner_key(identity))
        if review is None:
            return _render_review_screen(identity=identity, state=state, screen_state="expired")

        answer = request.form.get("answer", state["answer"])
        ok, update_error = wws.update_session(session, answer=answer, context_mask=state["context_mask"])
        if not ok:
            return _render_review_screen(
                identity=identity,
                state=state,
                screen_state="review",
                review=review,
                review_token=token,
                answer_snapshot=answer_snapshot,
                error_message=update_error or DEFAULT_FIELD_ERROR,
                status_code=400,
            )
        state = wws.read_state(session)

        if wws.at_ai_call_cap(state):
            return _render_review_screen(identity=identity, state=state, screen_state="cap_reached")
        reserved_ok, _reserve_error = wws.increment_ai_calls(session)
        if not reserved_ok:
            return _render_review_screen(identity=identity, state=state, screen_state="cap_reached")
        state = wws.read_state(session)
    except (KnowledgeServiceError, DatabaseServiceError):
        current_app.logger.error("PeerSlate Work on Something improve is unavailable.")
        return _render_workshop_unavailable()

    refusal = _reserve_daily_ai_spend(identity, state)
    if refusal is not None:
        return refusal

    raw_reply, stop_reason = "", ""
    try:
        raw_json, raw_reply, stop_reason = workshop_review_service.generate_improvement(answer, review)
        proposal = workshop_review_service.validate_workshop_improvement(raw_json)
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        workshop_review_service._log_workshop_failure(
            current_app.logger, "Workshop improve validation error", error, stop_reason, len(raw_reply)
        )
        return _render_review_screen(identity=identity, state=state, screen_state="unavailable")
    except Exception as error:  # noqa: BLE001 - provider/network failure, see module docstring
        workshop_review_service._log_workshop_failure(
            current_app.logger, "Workshop improve API error", error, stop_reason, len(raw_reply)
        )
        return _render_review_screen(identity=identity, state=state, screen_state="unavailable")

    return _render_review_screen(
        identity=identity,
        state=state,
        screen_state="review",
        review=review,
        review_token=token,
        answer_snapshot=answer_snapshot,
        proposal=proposal,
    )


@workshop.post("/app/workshop/work/session/edit")
def work_session_keep_working():
    """"Keep working" from the final-wording review screen
    (workshop_review.html, reused unchanged from W1) — returns to the
    session/answer screen with the submitted wording preserved as the
    current working answer, exactly like workshop_routes.py's
    keep_working_add does for direct entry. No AI call, no validation
    error state: this is a pure "let me keep typing" action, so a rare
    over-cap edit here is silently kept at its prior value rather than
    shown as a scary error banner on what is meant to be a simple back
    button — the member sees and can fix it on the session screen's own
    (already-validating) field instead.
    """
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

    answer = request.form.get("wording", state["answer"])
    wws.update_session(session, answer=answer, context_mask=state["context_mask"])
    return redirect(url_for("workshop.work_session_screen"))


@workshop.post("/app/workshop/work/session/finalize")
def work_session_finalize():
    """"Review final wording" — the primary action out of the AI review
    loop. Renders the EXISTING W1 "Review what will be saved" screen
    (workshop_review.html via workshop_routes._review_response, reused
    unchanged) seeded with the working answer and a title derived from the
    focused question, per the brief's "title from a required title field
    on that screen." No AI call happens here; this works identically
    whether or not any AI review ever ran (architecture section 9.3)."""
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

    answer = request.form.get("answer", state["answer"])
    try:
        ok, update_error = wws.update_session(session, answer=answer, context_mask=state["context_mask"])
        if not ok:
            incoming_token = request.form.get("review_token")
            if incoming_token:
                review, token, answer_snapshot = _review_from_token(incoming_token, _owner_key(identity))
                if review is not None:
                    return _render_review_screen(
                        identity=identity,
                        state=state,
                        screen_state="review",
                        review=review,
                        review_token=token,
                        answer_snapshot=answer_snapshot,
                        error_message=update_error or DEFAULT_FIELD_ERROR,
                        status_code=400,
                    )
            return _render_session_screen(
                identity=identity,
                state=state,
                answer_override=answer,
                error_message=update_error or DEFAULT_FIELD_ERROR,
                status_code=400,
            )
        state = wws.read_state(session)
    except (KnowledgeServiceError, DatabaseServiceError):
        current_app.logger.error("PeerSlate Work on Something review is unavailable.")
        return _render_workshop_unavailable()

    title_default = _title_from_question(state["question_text"])
    authored_via = "ai_assisted_approved" if state["ai_assisted"] else "typed"
    source_label = SOURCE_LABELS.get(authored_via, "Your words")

    return _review_response(
        mode="work",
        values={"title": title_default, "wording": state["answer"], "classification": "unclassified"},
        idempotency_key=str(uuid4()),
        item_key=None,
        expected_version_token=None,
        error_message=None,
        save_url=url_for("workshop.work_session_save"),
        keep_working_url=url_for("workshop.work_session_keep_working"),
        anonymous_preview=(identity is None),
        source_label=source_label,
    )


@workshop.post("/app/workshop/work/session/save")
def work_session_save():
    """The confirming save out of the Work on Something flow — flows into
    the EXISTING save primitives (workshop_demo_library.add_item /
    knowledge_service.save_knowledge_item_for_owner) unchanged, exactly
    like workshop_routes.save_item does for direct entry, with one
    difference save_item has no reason to have: authored_via reflects
    whether an AI improvement proposal was ever accepted into the working
    answer this session (wws state's ai_assisted flag), and the active
    Work on Something session is cleared on success — direct entry has no
    such session to clear.
    """
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

    idempotency_key = request.form.get("idempotency_key") or str(uuid4())
    raw = {
        "title": request.form.get("title", ""),
        "wording": request.form.get("wording", ""),
        "classification": request.form.get("classification", ""),
    }
    save_action = request.form.get("save_action")
    authored_via = "ai_assisted_approved" if state["ai_assisted"] else "typed"
    source_label = SOURCE_LABELS.get(authored_via, "Your words")

    def _rerender(error_message, status_code=400):
        return _review_response(
            mode="work",
            values=raw,
            idempotency_key=idempotency_key,
            item_key=None,
            expected_version_token=None,
            error_message=error_message,
            save_url=url_for("workshop.work_session_save"),
            keep_working_url=url_for("workshop.work_session_keep_working"),
            anonymous_preview=(identity is None),
            source_label=source_label,
            status_code=status_code,
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
        if len(wording) > workshop_demo_library.MAX_PREVIEW_WORDING_UNITS:
            return _rerender(workshop_demo_library.CAP_WORDING_MESSAGE)

        status = "confirmed" if save_action == "confirm" else "unfinished"
        new_item_key, add_error = workshop_demo_library.add_item(
            session,
            title=title,
            wording=wording,
            classification=classification,
            status=status,
            authored_via=authored_via,
        )
        if new_item_key is None:
            return _rerender(add_error)

        wws.clear_session(session)
        if save_action == "unfinished":
            return redirect(url_for("workshop.work_opening", changed="unfinished-preview"))
        return _render_anonymous_preview_saved(
            item_key=new_item_key,
            title=title,
            wording=wording,
            classification=classification,
            authored_via=authored_via,
        )

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
                "authored_via": authored_via,
                "confirm": save_action == "confirm",
            },
        )
    except KnowledgeServiceError as error:
        return _rerender(FIELD_ERROR_MESSAGES.get(error.code, DEFAULT_FIELD_ERROR))
    except DatabaseServiceError:
        current_app.logger.error("PeerSlate Work on Something save is unavailable.")
        return _rerender(UNAVAILABLE_FORM_MESSAGE)

    wws.clear_session(session)
    item_key = result["item_key"]
    if save_action == "confirm":
        return redirect(url_for("workshop.saved_item", item_key=item_key))
    return redirect(url_for("workshop.my_information", item=item_key, changed="unfinished"))


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


# ---------------------------------------------------------------------------
# PS-WORKSHOP-001 W2d — voice input.
#
# One endpoint, one job: turn a short recording into a transcript string and
# hand it straight back to the browser that made it. It reads nothing, writes
# nothing, and stores nothing — not a row, not a blob, not a session key — so
# there is deliberately no identity resolution here at all. An anonymous
# visitor and a signed-in member get the identical code path, and no
# ``*_for_owner`` service method is reachable from it, because none is
# imported into the call.
#
# The transcript is a PROPOSAL. It travels to the browser, is inserted into a
# field the member can read and correct, and becomes their words only when
# they submit that field themselves (R17 state 4). This route never submits,
# saves, or makes anything canonical.
# ---------------------------------------------------------------------------


def _voice_flag_gate():
    """True only when Workshop, the session sub-flag, AND voice are all on.

    Voice gets its OWN sub-flag rather than riding the session flag that is
    already live in production. W2a-W2c are on for real visitors right now;
    merging this slice must not silently put a microphone in front of them
    the moment it deploys. Azure Speech has to be configured and reachable
    for the App Service identity before a mic is anything but a false
    promise, and that is an operational fact a deploy cannot assert for
    itself. So this ships dark, exactly as the session flag did, and the
    owner turns it on once the provider is confirmed. With the flag off the
    endpoint 404s and the templates render the same honest inert mic they
    render in production today.
    """
    return _work_flag_gate() and _workshop_voice_enabled()


@workshop.before_request
def _allow_bounded_workshop_voice_upload():
    """Raise the global 2 MB body limit for the one route that takes audio.

    Mirrors owner_routes._allow_bounded_voice_upload: the app-wide
    MAX_CONTENT_LENGTH is a small-form limit, and a 90-second recording is
    legitimately larger than a form post. The raised ceiling applies to this
    endpoint alone and stays close to the service's own byte cap, so the
    audio bound is enforced twice — once by Werkzeug before the body is
    read, and once by validate_audio on the bytes themselves.
    """
    if request.endpoint == "workshop.transcribe_voice":
        request.max_content_length = (
            workshop_voice_service.MAX_WORKSHOP_VOICE_BYTES + (64 * 1024)
        )


# Outcomes that are the provider's condition rather than the caller's
# request, and so answer 503 rather than 400.
_PROVIDER_FAILURE_CODES = {"speech-unavailable", "transcription-failed"}


def _voice_error(code, status):
    return (
        jsonify({"error": code, "message": workshop_voice_service.message_for(code)}),
        status,
    )


@workshop.post("/app/workshop/voice/transcribe")
def transcribe_voice():
    """Transcribe one short recording and return the text, nothing else."""
    if not _voice_flag_gate():
        abort(404)
    if not _is_same_origin_write():
        return "Cross-site Workshop requests are not allowed.", 403

    # Reserve BEFORE the provider call, never after: an attempted
    # transcription is what Azure bills, so one that then fails still counts.
    # Voice has its own daily ceilings (workshop_spend_guard.reserve_voice) —
    # a different vendor and a different bill from the Anthropic review
    # calls, so dictating a lot must never exhaust AI review, or vice versa.
    reservation = workshop_spend_guard.reserve_voice(workshop_spend_guard.client_ip())
    if reservation != workshop_spend_guard.RESERVE_OK:
        return (
            jsonify(
                {
                    "error": "voice-daily-limit",
                    "message": (
                        "Voice input has reached today's limit. This is a daily "
                        "limit, not something you did wrong — your words are "
                        "still here, and you can keep typing."
                    ),
                }
            ),
            429,
        )

    try:
        transcript = workshop_voice_service.transcribe_recording(
            request.files.get("audio"),
            request.form.get("duration_seconds"),
        )
    except workshop_voice_service.WorkshopVoiceError as error:
        # 503 when the provider is the problem, 400 only when the upload
        # itself is. A recording Azure refused or could not process is NOT a
        # malformed request from the browser, so calling it a 400 would put
        # the blame in the wrong place in the logs and in anything that
        # monitors them. "speech-empty" stays a 400 because it is a true
        # fact about the recording that was sent. Neither shape ever returns
        # a provider payload, and neither touches the member's own text.
        status = 503 if error.code in _PROVIDER_FAILURE_CODES else 400
        if status == 503:
            current_app.logger.error(
                "PeerSlate Workshop voice transcription is unavailable."
            )
        return _voice_error(error.code, status)

    response = jsonify({"transcript": transcript})
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response, 200
