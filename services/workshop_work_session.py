"""Work on Something session state — PS-WORKSHOP-001 W2a.

Controlling brief: docs/initiatives/PS-SLATE-STUDIO-IA-001/
22_W2_IMPLEMENTATION_BRIEF.md. Architecture: 17_WORKSHOP_PRODUCT_AND_
TECHNICAL_ARCHITECTURE.md section 10 (state machine) and section 4.2 (no AI
proposal is ever written to the database). Sequence: 18_WORKSHOP_
IMPLEMENTATION_TEST_AND_RELEASE_SEQUENCE.md slice W2.

**Scope of this slice.** The opening's four doors, a focused question chosen
from a fixed curated set (no AI call — that is W2b), the session screen's
answer field and "Use as context" selection, "Save unfinished" (which reuses
the existing save paths), and "Stop for now". No proposal, review, or save
confirmation writes here; "Review what I shared" leads to an honest holding
state built in workshop_work_routes.py, not to a real AI call.

**Anonymous vs member (brief section "Anonymous vs member session model").**
Both anonymous visitors and signed-in members use this SAME session-cookie
mechanism for their in-progress Work on Something state in W2a — door,
question, answer-so-far, and context selection are all ephemeral UI state,
never durable content. Doc 17's DB-backed ``knowledge_item_sources`` table
(PS-WORKSHOP-002) is the eventual home for a member's session provenance once
member authentication is fully wired through Workshop; until then, a signed-
in member's Work on Something session state lives in the same place an
anonymous visitor's does. This is a disclosed, deliberate W2a scope
limitation, not an oversight — a member's actual knowledge (confirmed and
unfinished library items) already lives in the real database via
services/knowledge_service.py regardless of this.

**Session state shape.** Stored at
``session[workshop_demo_library.SESSION_KEY]["w"]`` — the SAME signed cookie
key the anonymous demo library (services/workshop_demo_library.py) uses for
its own "a"/"e"/"s"/"d" delta, so "Start fresh"
(``POST /app/workshop/preview/reset``) can clear both with one action. The
value is a compact LIST (not a dict — matching workshop_demo_library's own
"compact session encoding" convention of positional entries to keep the
signed, base64-encoded cookie small). PS-WORKSHOP-001 W2b grew this from 4
to 6 elements to track the per-session AI-call cap and whether an AI
improvement proposal was ever accepted (``read_state`` degrades a stale
4-element bucket gracefully rather than discarding the session — see its
own docstring):

    [door_code, question_index, answer_text, context_mask, ai_call_count,
     ai_assisted]

- ``door_code``: one of DOOR_CONTINUE / DOOR_BROUGHT / DOOR_SOMETHING /
  DOOR_SPARK (single-character strings; a distinct namespace from
  workshop_demo_library's own status/classification codes — the two never
  appear in the same JSON key, so there is no collision risk, but codes are
  kept single-character here purely for byte-budget parity).
- ``question_index``: index into QUESTION_SETS[door_code]. Selection is
  DETERMINISTIC per door (always index 0 today) — see question_for_door.
  The index is stored, not re-derived, so a later slice can let a member
  cycle to a different curated question without changing this shape.
- ``answer_text``: the member's in-progress answer, seeded from an open
  thought at session start and updated on "Save unfinished" / "Stop for
  now" / "Review what I shared" (every one of the session screen's submit
  actions carries the current textarea value forward in the same POST, so
  no separate autosave-on-keystroke route exists in this slice). Capped at
  MAX_ANSWER_UNITS (1000) UTF-16 code units — the brief's explicit cap.
- ``context_mask``: a bitmask over the CURRENT "Related confirmed
  information" rail's visible order (capped at MAX_CONTEXT_ITEMS, 8 items).
  Bit i set means "the item currently at position i in the visible list is
  selected as context." This is a documented byte-budget tradeoff: storing
  full item-key strings for every selection would not fit the shared byte
  budget alongside a maxed-out answer and a maxed-out anonymous library
  delta (see MAX_SESSION_BYTES import below). The tradeoff's edge case: if
  the visible confirmed-item order changes mid-session (e.g. the visitor
  archives a confirmed item they had marked as context), a stored bit can
  end up pointing at a different item than the one originally selected.
  This only ever affects the SAME visitor's own already-fully-visible
  session-scoped selection — never another visitor's data, never a
  permission or privacy boundary — so it is accepted here as a disclosed
  simplification rather than built out further in this slice.
- ``ai_call_count``: how many AI calls (review + improve combined) this
  session has attempted, capped at MAX_AI_CALLS_PER_SESSION (20, the
  brief's per-session cost control). Incremented via ``increment_ai_calls``
  BEFORE each provider call is attempted, never after, so a call that
  fails mid-flight still counts.
- ``ai_assisted``: 0/1, set true by ``mark_ai_assisted`` once an AI
  improvement proposal has been accepted into the working answer. Read
  back at final save (workshop_work_routes.py) to choose
  ``authored_via='ai_assisted_approved'`` instead of ``'typed'``.

**Byte budget.** MAX_SESSION_BYTES is imported from workshop_demo_library
(not redefined) because it is now the SHARED ceiling for the whole
``workshop_preview`` cookie value, library delta and this "w" bucket
together — see that module's own updated comment. Every write here measures
the TRUE combined size (via the same signed-serializer technique
workshop_demo_library._would_fit uses) before committing, and never silently
truncates: a would-not-fit write returns an honest SESSION_FULL_MESSAGE
instead.
"""

import json

from flask import current_app

from services.workshop_demo_library import MAX_SESSION_BYTES, SESSION_KEY


# ---------------------------------------------------------------------------
# Doors
# ---------------------------------------------------------------------------

DOOR_CONTINUE = "c"
DOOR_BROUGHT = "b"
DOOR_SOMETHING = "s"
DOOR_SPARK = "k"

ALL_DOORS = (DOOR_CONTINUE, DOOR_BROUGHT, DOOR_SOMETHING, DOOR_SPARK)
# Only these two doors can actually begin a session in W2a. "I brought
# something" has no intake path yet (doc 13's door-purpose ruling: "starts an
# honest handoff or explains unavailable intake") and "Give me a spark" has
# no Spark feature yet at all (that is slice W2c/doc 18) — both render as
# honest not-available cards on the opening screen and neither is ever
# reachable via POST /app/workshop/work/start.
STARTABLE_DOORS = (DOOR_CONTINUE, DOOR_SOMETHING)

MAX_ANSWER_UNITS = 1000
MAX_CONTEXT_ITEMS = 8

CAP_ANSWER_MESSAGE = (
    "This session's answer is limited to 1000 characters — shorten it and "
    "try again. Nothing above has been lost."
)
SESSION_FULL_MESSAGE = (
    "This preview session is full — sign in for an unlimited private "
    "library, or start fresh to clear this session."
)
DOOR_UNAVAILABLE_MESSAGE = "This starting point is not available yet."


def utf16_length(value):
    """UTF-16 code units, matching the brief's explicit cap and the same
    idiom services/knowledge_service.py and its siblings each define
    locally (repo convention: no shared cross-service text-limit module)."""
    return len(value.encode("utf-16-le")) // 2


# ---------------------------------------------------------------------------
# Curated focused-question sets (module constants — no AI call in W2a)
#
# 4-6 questions per startable door, informed by the mockups' own example
# ("What changed because of the prototype or the decisions you led?", R03/
# R04) and doc 13's door-purpose rulings (doc 13 row 30: Continue "resumes
# rather than creates"; row 32: Work on something "starts a private,
# reviewable draft"). Selection is deterministic (always index 0 for now —
# see question_for_door); the remaining entries are reserved for a later
# slice's "ask a different question" affordance, not currently reachable.
# ---------------------------------------------------------------------------

QUESTION_SETS = {
    DOOR_SOMETHING: (
        "What's something you did that mattered, and what changed because "
        "of it?",
        "Tell me about a skill you use often that most people never think "
        "to ask you about.",
        "Describe a moment when a decision you made changed the outcome.",
        "What's something you built, fixed, or improved — and how did you "
        "know it worked?",
        "What do people come to you for, and why do you think that is?",
        "What's something true about you that would surprise someone who "
        "only knows you a little?",
    ),
    DOOR_CONTINUE: (
        "What's changed or become clearer since you started this?",
        "What's the one concrete detail that would make this real for "
        "someone else reading it?",
        "What actually happened because of this — what changed as a "
        "result?",
        "What's still missing before this feels finished to you?",
        "Who would vouch for this, and what would they say happened?",
    ),
}


def question_for_door(door):
    """Deterministic per-door focused-question selection.

    Returns ``(question_index, question_text)``, or ``(None, None)`` for a
    door with no question set — which in practice is only DOOR_BROUGHT and
    DOOR_SPARK, neither of which is ever passed to start_session (both are
    rejected before this is consulted; see workshop_work_routes.py).
    """
    questions = QUESTION_SETS.get(door)
    if not questions:
        return None, None
    return 0, questions[0]


def question_text_for(door, question_index):
    """Re-derive the exact question text for a stored (door, index) pair.

    Never trusts a stale or out-of-range index (e.g. a future question-set
    edit shrinking a list): falls back to the door's own deterministic
    first question rather than raising, so an old signed cookie from before
    a copy change degrades gracefully instead of crashing the session
    screen.
    """
    questions = QUESTION_SETS.get(door) or ()
    if isinstance(question_index, int) and 0 <= question_index < len(questions):
        return questions[question_index]
    _, text = question_for_door(door)
    return text


# ---------------------------------------------------------------------------
# Session state: read / start / update / clear
# ---------------------------------------------------------------------------


def read_state(session):
    """The current Work on Something session state, or ``None`` if no
    session is active. Defensively re-shapes anything malformed (a stale
    shape from a future schema change degrades to "no session" rather than
    crashing), exactly mirroring workshop_demo_library.read_session_delta's
    own defensive-reshape discipline.

    PS-WORKSHOP-001 W2b: the bucket grew from 4 to 6 elements
    (``ai_call_count``, ``ai_assisted``) to track the per-session AI-call
    cap and whether an AI improvement proposal was ever accepted into the
    working answer (drives ``authored_via`` at final save). A stale
    4-element bucket from a cookie written before this slice shipped
    degrades gracefully to ``ai_call_count=0``/``ai_assisted=False`` rather
    than being treated as "no session" — the member's in-progress door,
    question, answer, and context selection are not thrown away merely
    because this slice added two counters.
    """
    raw = session.get(SESSION_KEY)
    bucket = raw.get("w") if isinstance(raw, dict) else None
    if not isinstance(bucket, list) or len(bucket) not in (4, 6):
        return None
    if len(bucket) == 4:
        door, question_index, answer, context_mask = bucket
        ai_call_count, ai_assisted = 0, 0
    else:
        door, question_index, answer, context_mask, ai_call_count, ai_assisted = bucket
    if door not in ALL_DOORS:
        return None
    if not isinstance(question_index, int) or question_index < 0:
        question_index = 0
    if not isinstance(answer, str):
        answer = ""
    if len(answer) > MAX_ANSWER_UNITS * 2:
        # Defensive re-cap only (a tampered-but-validly-signed cookie should
        # not be possible via itsdangerous) — generous bound since this is
        # Python len(), not the UTF-16 measure enforced on write.
        answer = answer[: MAX_ANSWER_UNITS * 2]
    if not isinstance(context_mask, int) or context_mask < 0:
        context_mask = 0
    if not isinstance(ai_call_count, int) or ai_call_count < 0:
        ai_call_count = 0
    return {
        "door": door,
        "question_index": question_index,
        "question_text": question_text_for(door, question_index),
        "answer": answer,
        "context_mask": context_mask & _context_full_mask(),
        "ai_call_count": min(ai_call_count, MAX_AI_CALLS_PER_SESSION),
        "ai_assisted": bool(ai_assisted),
    }


def _would_fit(session, candidate_bucket):
    """True if writing ``candidate_bucket`` as the "w" key keeps the fully
    signed, encoded session cookie at or under the SHARED MAX_SESSION_BYTES
    ceiling (library delta and work-session state combined). Mirrors
    workshop_demo_library._would_fit's technique exactly."""
    raw = session.get(SESSION_KEY)
    existing = dict(raw) if isinstance(raw, dict) else {}
    trial_value = dict(existing)
    trial_value["w"] = candidate_bucket
    trial = dict(session)
    trial[SESSION_KEY] = trial_value
    try:
        serializer = current_app.session_interface.get_signing_serializer(current_app)
        token = serializer.dumps(trial)
        size = len(token.encode("utf-8")) if isinstance(token, str) else len(token)
    except Exception:
        raw_bytes = json.dumps(trial, separators=(",", ":"), default=str)
        size = len(raw_bytes.encode("utf-8"))
    return size <= MAX_SESSION_BYTES


def _write_bucket(session, bucket):
    raw = session.get(SESSION_KEY)
    merged = dict(raw) if isinstance(raw, dict) else {}
    merged["w"] = bucket
    session[SESSION_KEY] = merged
    session.modified = True


def start_session(session, *, door, answer):
    """Begin (replacing any prior) Work on Something session.

    Returns ``(ok, error_message, state)``. On success ``state`` is the same
    shape ``read_state`` returns; on failure ``state`` is ``None`` and
    ``error_message`` is always an honest, specific reason — a door outside
    STARTABLE_DOORS, an over-cap answer, or a full session, never a silent
    drop of the member's typed text (the caller re-renders the opening
    screen with that text intact either way).
    """
    if door not in STARTABLE_DOORS:
        return False, DOOR_UNAVAILABLE_MESSAGE, None
    if utf16_length(answer) > MAX_ANSWER_UNITS:
        return False, CAP_ANSWER_MESSAGE, None

    question_index, _text = question_for_door(door)
    if question_index is None:
        return False, DOOR_UNAVAILABLE_MESSAGE, None

    bucket = [door, question_index, answer, 0, 0, 0]
    if not _would_fit(session, bucket):
        return False, SESSION_FULL_MESSAGE, None

    _write_bucket(session, bucket)
    return True, None, read_state(session)


def update_session(session, *, answer, context_mask):
    """Update the answer text and/or context selection for the CURRENT
    active session (every session-screen submit action carries both
    forward). Returns ``(ok, error_message)``; ``ok`` is ``False`` with
    ``error_message`` ``None`` when there is no active session at all —
    never confirms or denies why, matching the repo's existing convention
    for a foreign/expired session reference.

    PS-WORKSHOP-001 W2b: preserves the current ``ai_call_count`` and
    ``ai_assisted`` counters unchanged — this function only ever touches
    the answer text and context selection, exactly as it did in W2a; the
    two AI-tracking fields are mutated only by ``increment_ai_calls`` /
    ``mark_ai_assisted`` below.
    """
    state = read_state(session)
    if state is None:
        return False, None
    if utf16_length(answer) > MAX_ANSWER_UNITS:
        return False, CAP_ANSWER_MESSAGE

    bucket = [
        state["door"],
        state["question_index"],
        answer,
        int(context_mask) & _context_full_mask(),
        state["ai_call_count"],
        1 if state["ai_assisted"] else 0,
    ]
    if not _would_fit(session, bucket):
        return False, SESSION_FULL_MESSAGE

    _write_bucket(session, bucket)
    return True, None


# ---------------------------------------------------------------------------
# AI-call accounting — PS-WORKSHOP-001 W2b (brief's "Cost controls" section).
# ---------------------------------------------------------------------------

MAX_AI_CALLS_PER_SESSION = 20
AI_CALL_CAP_MESSAGE = (
    "This preview session has reached its limit for AI review this visit — "
    "start fresh or come back later. Your answer is still here, and Save "
    "unfinished still works."
)


def at_ai_call_cap(state):
    """True when this session has reached MAX_AI_CALLS_PER_SESSION AI
    calls (review + improve combined). Checked BEFORE attempting a call —
    never after — so the cap is a hard ceiling on calls actually attempted,
    not merely on calls that succeeded."""
    return state["ai_call_count"] >= MAX_AI_CALLS_PER_SESSION


def increment_ai_calls(session):
    """Record one more AI call attempt against the active session's cap.

    Returns ``(ok, error_message)``; ``ok`` is ``False`` with
    ``error_message`` ``None`` when there is no active session (same
    "never confirm or deny" convention as ``update_session``). Callers
    must check ``at_ai_call_cap`` first and reserve the slot with this
    function BEFORE calling the model, so a request that dies mid-call
    still counts against the cap (the point of the cap is bounding actual
    provider requests attempted, not only successful ones).
    """
    state = read_state(session)
    if state is None:
        return False, None

    bucket = [
        state["door"],
        state["question_index"],
        state["answer"],
        state["context_mask"],
        state["ai_call_count"] + 1,
        1 if state["ai_assisted"] else 0,
    ]
    if not _would_fit(session, bucket):
        return False, SESSION_FULL_MESSAGE

    _write_bucket(session, bucket)
    return True, None


def mark_ai_assisted(session):
    """Flip the session's ``ai_assisted`` flag once an AI improvement
    proposal has been accepted into the working answer — read back at
    final save to set ``authored_via='ai_assisted_approved'`` instead of
    ``'typed'`` (architecture section 4.1's D1 provenance). Idempotent;
    never cleared by anything except ``clear_session``/a fresh
    ``start_session``."""
    state = read_state(session)
    if state is None:
        return False, None

    bucket = [
        state["door"],
        state["question_index"],
        state["answer"],
        state["context_mask"],
        state["ai_call_count"],
        1,
    ]
    if not _would_fit(session, bucket):
        return False, SESSION_FULL_MESSAGE

    _write_bucket(session, bucket)
    return True, None


def clear_session(session):
    """Stop for now / Save unfinished / Review what I shared all clear the
    active session once handled — this removes only the "w" key, leaving
    the anonymous library delta ("a"/"e"/"s"/"d") completely untouched."""
    raw = session.get(SESSION_KEY)
    if not isinstance(raw, dict) or "w" not in raw:
        return
    merged = dict(raw)
    merged.pop("w", None)
    session[SESSION_KEY] = merged
    session.modified = True


# ---------------------------------------------------------------------------
# "Use as context" selection <-> compact bitmask
# ---------------------------------------------------------------------------


def _context_full_mask():
    return (1 << MAX_CONTEXT_ITEMS) - 1


def context_mask_from_ids(selected_ids, visible_ids):
    """Validate submitted "Use as context" item keys against the CURRENT
    visible allow-list (order-stable, capped at MAX_CONTEXT_ITEMS) and
    return a compact positional bitmask. An id outside the visible set (or
    beyond the cap) is silently ignored — never trusted, never echoed back
    as an error, matching the repo's "never confirm or deny a foreign id"
    convention used throughout workshop_routes.py.
    """
    visible_index = {
        item_id: i for i, item_id in enumerate(visible_ids[:MAX_CONTEXT_ITEMS])
    }
    mask = 0
    for item_id in selected_ids:
        i = visible_index.get(item_id)
        if i is not None:
            mask |= 1 << i
    return mask


def context_ids_from_mask(mask, visible_ids):
    """The reverse of context_mask_from_ids: which of the CURRENT visible
    ids are selected, re-derived fresh from today's visible list every call
    (never trusts a stale id list beyond its current length)."""
    selected = []
    for i, item_id in enumerate(visible_ids[:MAX_CONTEXT_ITEMS]):
        if mask & (1 << i):
            selected.append(item_id)
    return selected
