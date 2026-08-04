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
improvement proposal was ever accepted; audit fix F2 (2026-08-04) grew it to
7 to remember the visitor's own opening thought. ``read_state`` degrades a
stale 4- or 6-element bucket gracefully rather than discarding the session —
see its own docstring:

    [door_code, question_index, answer_text, context_mask, ai_call_count,
     ai_assisted, opening_thought]

- ``door_code``: one of DOOR_CONTINUE / DOOR_BROUGHT / DOOR_SOMETHING /
  DOOR_SPARK (single-character strings; a distinct namespace from
  workshop_demo_library's own status/classification codes — the two never
  appear in the same JSON key, so there is no collision risk, but codes are
  kept single-character here purely for byte-budget parity).
- ``question_index``: index into QUESTION_SETS[door_code]. Audit fix F2
  (2026-08-04): chosen with fresh entropy at session start so two people
  starting side by side are not asked the identical question, and STORED
  rather than re-derived so the choice cannot change under the member on a
  re-render — see question_for_door. It was hardcoded to 0, which made
  every curated question but the first unreachable.
- ``opening_thought``: up to MAX_OPENING_THOUGHT_UNITS characters of what
  the visitor actually typed to begin, echoed back on the session screen as
  their own words. Optional by design: it is dropped rather than allowed to
  cost the member their session when the cookie is tight.
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

import hashlib
import json
import secrets

from flask import current_app

from services.workshop_demo_library import (
    MAX_PREVIEW_WORDING_UNITS,
    MAX_SESSION_BYTES,
    SESSION_KEY,
)


# ---------------------------------------------------------------------------
# Doors
# ---------------------------------------------------------------------------

DOOR_CONTINUE = "c"
DOOR_BROUGHT = "b"
DOOR_SOMETHING = "s"
DOOR_SPARK = "k"

ALL_DOORS = (DOOR_CONTINUE, DOOR_BROUGHT, DOOR_SOMETHING, DOOR_SPARK)
# PS-WORKSHOP-001 W2c added DOOR_SPARK here: "Work on this" on a rendered
# Spark begins a real session (architecture doc 17 section 10's first
# transition, "opening | Spark `Work on this` ... | session | no"). "I
# brought something" still has no intake path (doc 13's door-purpose ruling:
# "starts an honest handoff or explains unavailable intake") and stays inert.
#
# DOOR_SPARK is startable but NOT self-service: the route only accepts it
# alongside a Spark that this process generated and validated this visit, so
# a hand-rolled POST cannot use it to seed a session with arbitrary text and
# have that text carry a Spark's provenance.
STARTABLE_DOORS = (DOOR_CONTINUE, DOOR_SOMETHING, DOOR_SPARK)

# Audit fix F1 (2026-08-04): DEFINED AS the anonymous preview's own wording
# cap rather than as its own literal. These two numbers are the invited
# length and the accepted length of the same piece of text — the session
# screen's answer field is what the save screen's final-wording field is
# pre-filled from — so a difference between them is never a policy, only a
# bug. It was one: this was 1000 while the preview cap was 400, the save
# screen pre-filled the full answer into a box it would then refuse, and the
# guided session could not be completed at all. Binding them here means the
# only way to change one is to change both. See
# workshop_demo_library.MAX_PREVIEW_WORDING_UNITS for the full reasoning and
# the re-measured cookie budget.
MAX_ANSWER_UNITS = MAX_PREVIEW_WORDING_UNITS
MAX_CONTEXT_ITEMS = 8

# Audit fix F2 (2026-08-04): how much of the visitor's own opening thought
# the session screen remembers in order to show it back to them.
#
# A short reminder, not a second copy of the content — the thought's full
# text is already the working answer, and the answer is what the member
# edits. This exists so the session screen can say "you started with THIS,
# and here is what PeerSlate asked in response", which is the connection the
# screen previously left the visitor to guess at.
#
# Deliberately small because it is spending the SHARED cookie budget on a
# convenience: at the tightest legitimate worst case the whole cookie has
# only tens of bytes spare, so the echo is written best-effort (see
# start_session) and simply omitted when the member's own words need the
# room. It never displaces content, only itself.
MAX_OPENING_THOUGHT_UNITS = 160

# PS-WORKSHOP-001 W2c: defensive re-caps for the cached Spark text. These
# mirror services/workshop_review_service.py's MAX_SPARK_SUGGESTION_CHARS /
# MAX_SPARK_FOCUS_SEED_CHARS but are declared locally rather than imported,
# because that module constructs an Anthropic client at import time and this
# one has no business depending on an AI SDK to read a cookie. Nothing
# reaching this module is unvalidated — the service already applied these
# exact caps — so a drift between the two can only ever make the cookie
# smaller, never let unbounded text through.
MAX_SPARK_SUGGESTION_UNITS = 220
MAX_SPARK_FOCUS_SEED_UNITS = 160

CAP_ANSWER_MESSAGE = (
    f"This session's answer is limited to {MAX_ANSWER_UNITS} characters — "
    "shorten it and try again. Nothing above has been lost."
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
    # PS-WORKSHOP-001 W2c. A Spark already names the specific thing worth
    # doing, so this door's focused question deliberately does NOT re-ask
    # what the Spark just said. It asks for the evidence the Spark pointed
    # at — which is the member's own to supply, and the part no suggestion
    # can invent for them.
    DOOR_SPARK: (
        "What actually happened here — what changed because of it?",
        "What's the concrete result this produced?",
        "What would someone who was there say about your part in it?",
        "What detail would make this real for someone reading it cold?",
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


def question_for_door(door, *, entropy=None):
    """Choose ONE of this door's curated focused questions.

    Returns ``(question_index, question_text)``, or ``(None, None)`` for a
    door with no question set — which in practice is only DOOR_BROUGHT,
    rejected before this is ever consulted (see workshop_work_routes.py).

    Audit fix F2 (2026-08-04). This used to be ``return 0, questions[0]``,
    which made all six curated questions but the first dead code and meant
    two people starting a session side by side were asked the identical
    thing — the opposite of the personal, responsive product the screen
    claims to be. The questions were always there; nothing ever reached
    them.

    **Varied across sessions, fixed within one.** The index is chosen here,
    once, at session start, and then STORED in the session bucket; every
    later render calls ``question_text_for`` with that stored index rather
    than calling this again. So a session's question cannot change under the
    member between re-renders, a reload, or a validation failure — the
    stability comes from persisting the choice, not from the choice being
    reproducible.

    ``entropy`` exists so a test can pin a selection. Left unset it is fresh
    random bytes per call: deliberately NOT module-level ``random``, which
    would make every worker process pick the same question after a deploy
    and reintroduce this bug in a subtler form.
    """
    questions = QUESTION_SETS.get(door)
    if not questions:
        return None, None
    if entropy is None:
        entropy = secrets.token_bytes(16)
    if not isinstance(entropy, bytes):
        entropy = str(entropy).encode("utf-8")
    index = int.from_bytes(hashlib.sha256(entropy).digest()[:8], "big") % len(questions)
    return index, questions[index]


def question_text_for(door, question_index):
    """Re-derive the exact question text for a stored (door, index) pair.

    Never trusts a stale or out-of-range index (e.g. a future question-set
    edit shrinking a list): falls back to the door's FIRST question rather
    than raising, so an old signed cookie from before a copy change degrades
    gracefully instead of crashing the session screen.

    Audit fix F2: the fallback is the literal first entry, NOT
    ``question_for_door``. Now that selection is varied, routing the
    fallback through it would hand a member a different question every time
    a stale index was re-rendered — turning one graceful degradation into a
    question that visibly changes under them mid-session.
    """
    questions = QUESTION_SETS.get(door) or ()
    if isinstance(question_index, int) and 0 <= question_index < len(questions):
        return questions[question_index]
    return questions[0] if questions else None


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
    if not isinstance(bucket, list) or len(bucket) not in (4, 6, 7):
        return None
    opening_thought = ""
    if len(bucket) == 4:
        door, question_index, answer, context_mask = bucket
        ai_call_count, ai_assisted = 0, 0
    else:
        door, question_index, answer, context_mask, ai_call_count, ai_assisted = bucket[:6]
        # Audit fix F2 (2026-08-04) grew the bucket to 7. A 6-element bucket
        # from a cookie written before this slice is NOT "no session" — it is
        # a member mid-answer who simply has no remembered opening thought.
        if len(bucket) == 7 and isinstance(bucket[6], str):
            opening_thought = bucket[6][:MAX_OPENING_THOUGHT_UNITS]
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
        "opening_thought": opening_thought,
    }


def _would_fit(session, candidate_bucket, key="w", also=None):
    """True if writing ``candidate_bucket`` under ``key`` keeps the fully
    signed, encoded session cookie at or under the SHARED MAX_SESSION_BYTES
    ceiling (library delta, work-session state, and Spark memory combined).
    Mirrors workshop_demo_library._would_fit's technique exactly.

    ``key`` defaults to the Work on Something bucket ("w") so every W2a/W2b
    call site reads unchanged; PS-WORKSHOP-001 W2c passes SPARK_KEY for the
    Spark memory bucket. Measuring the whole cookie rather than one bucket
    is the point: the three features share one byte budget, so a Spark write
    must be refused when a maximal library delta plus a maximal answer has
    already consumed the room, not merely when the Spark itself is large.
    """
    raw = session.get(SESSION_KEY)
    existing = dict(raw) if isinstance(raw, dict) else {}
    trial_value = dict(existing)
    trial_value[key] = candidate_bucket
    if also:
        trial_value.update(also)
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


def _fits_after_evicting_spark_cache(session, bucket):
    """True if this Work on Something write fits — reclaiming bytes from
    Spark memory, in a fixed priority order, if that is what makes room.

    **Why this exists.** The pre-W2c worst case (a maximal 4-item/400-char
    library delta plus a maximal 1000-unit answer) already sat within about
    14 bytes of the shared ceiling. Fourteen bytes is less than ONE
    fingerprint, so there is no size of durable dismissal memory that fits
    alongside it. Adding Spark naively would therefore have taken a
    capability away: a visitor with a full library would be told their
    session is full and be unable to start work at all — a real regression,
    caused entirely by a feature they may not even be using.

    **The priority order, and what it costs.** Highest first:

      1. The member's own words. Never sacrificed. They are the product.
      2. The dismissal record (``offered``). Sacrificed only after the cache,
         oldest first — losing an old fingerprint means a long-ago dismissed
         idea could theoretically be offered again, which is the documented
         cap the brief allows.
      3. The grounding-exclusion hints (``used``). Sacrificed before the
         dismissal record, because they only steer a prompt; nothing is
         promised about them.
      4. The cached Spark (``current``). Sacrificed first. It is a cost
         optimization and can be regenerated on demand.

    Reaching step 2 at all requires an adversarial combination — four
    library items at both caps, a full-length answer, and a long dismissal
    history in one anonymous visit. Everything is measured against the real
    signed cookie, and nothing is committed unless it actually makes the
    write fit: a write that would fail anyway leaves Spark memory untouched.
    """
    if _would_fit(session, bucket):
        return True

    state = read_spark_state(session)
    trial = {"current": None, "offered": list(state["offered"]), "used": list(state["used"])}

    def _commit_if_it_fits():
        candidate = _spark_bucket(trial)
        if _would_fit(session, bucket, also={SPARK_KEY: candidate}):
            _write_bucket(session, candidate, SPARK_KEY)
            return True
        return False

    if state["current"] is not None and _commit_if_it_fits():
        return True

    while trial["used"] or trial["offered"]:
        if trial["used"]:
            trial["used"] = trial["used"][1:]
        else:
            trial["offered"] = trial["offered"][1:]
        if _commit_if_it_fits():
            return True

    # Nothing left to reclaim. Drop the empty bucket entirely and make one
    # last check before refusing honestly.
    raw = session.get(SESSION_KEY)
    if isinstance(raw, dict) and SPARK_KEY in raw:
        without_spark = {
            key: value for key, value in raw.items() if key != SPARK_KEY
        }
        trial_session = dict(session)
        trial_session[SESSION_KEY] = dict(without_spark, w=bucket)
        try:
            serializer = current_app.session_interface.get_signing_serializer(current_app)
            token = serializer.dumps(trial_session)
            size = len(token.encode("utf-8")) if isinstance(token, str) else len(token)
        except Exception:
            size = len(
                json.dumps(trial_session, separators=(",", ":"), default=str).encode("utf-8")
            )
        if size <= MAX_SESSION_BYTES:
            session[SESSION_KEY] = without_spark
            session.modified = True
            return True
    return False


def shed_spark_memory_until_fits(session, fits):
    """Reclaim bytes from Spark memory, in this module's documented priority
    order, until the caller's own ``fits()`` check passes. Returns True when
    something was reclaimed that actually made it fit.

    Audit fix F1 (2026-08-04). ``_fits_after_evicting_spark_cache`` above
    does exactly this for a Work on Something write, but its shape is
    hard-wired to a single sub-key of the shared cookie, and the anonymous
    library's delta is four TOP-LEVEL keys rather than one bucket — so
    services/workshop_demo_library.py could not reuse it and had no shed
    order at all. A visitor could therefore be told their preview session
    was full while ~460 bytes of a cached Spark suggestion they never asked
    to keep sat in the cookie. ``fits`` is a zero-argument callable so the
    caller keeps ownership of what "fits" means for its own write.

    Priority is unchanged and non-negotiable (see
    ``_fits_after_evicting_spark_cache``'s docstring): the member's own words
    are never sacrificed; the regenerable ``current`` cache goes first, then
    the grounding hints, then the oldest dismissal records. Every step is
    measured against the real signed cookie, and if nothing reclaimable makes
    the write fit, the ORIGINAL Spark memory is restored untouched and the
    caller refuses honestly — a failed write never costs the visitor their
    dismissal record as a side effect.
    """
    raw = session.get(SESSION_KEY)
    original_bucket = raw.get(SPARK_KEY) if isinstance(raw, dict) else None
    if original_bucket is None:
        return False

    state = read_spark_state(session)
    trial = {"current": None, "offered": list(state["offered"]), "used": list(state["used"])}

    def _commit_if_it_fits():
        _write_bucket(session, _spark_bucket(trial), SPARK_KEY)
        return bool(fits())

    if state["current"] is not None and _commit_if_it_fits():
        return True

    while trial["used"] or trial["offered"]:
        if trial["used"]:
            trial["used"] = trial["used"][1:]
        else:
            trial["offered"] = trial["offered"][1:]
        if _commit_if_it_fits():
            return True

    # Nothing left to reclaim inside the bucket — try dropping it entirely.
    clear_spark_memory(session)
    if fits():
        return True

    _write_bucket(session, original_bucket, SPARK_KEY)
    return False


def _write_bucket(session, bucket, key="w"):
    raw = session.get(SESSION_KEY)
    merged = dict(raw) if isinstance(raw, dict) else {}
    merged[key] = bucket
    session[SESSION_KEY] = merged
    session.modified = True


def _bucket_from(state, *, answer=None, context_mask=None, ai_call_count=None, ai_assisted=None):
    """The 7-element bucket for ``state``, with selected fields overridden.

    Audit fix F2 (2026-08-04) added the trailing opening-thought element.
    Four separate call sites each rebuilt the bucket by hand from
    ``read_state``'s dict, so growing it meant editing the same literal in
    four places and silently dropping the new field anywhere that was
    missed — which is exactly how a member's remembered opening thought
    would disappear the first time they pressed Improve with AI. One
    builder, so a field added to the bucket is carried by every write that
    is not deliberately changing it.
    """
    return [
        state["door"],
        state["question_index"],
        state["answer"] if answer is None else answer,
        state["context_mask"] if context_mask is None else context_mask,
        state["ai_call_count"] if ai_call_count is None else ai_call_count,
        (1 if state["ai_assisted"] else 0) if ai_assisted is None else ai_assisted,
        state["opening_thought"],
    ]


def start_session(session, *, door, answer, opening_thought=""):
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

    echo = " ".join(str(opening_thought or "").split())[:MAX_OPENING_THOUGHT_UNITS]
    bucket = [door, question_index, answer, 0, 0, 0, echo]
    if not _fits_after_evicting_spark_cache(session, bucket):
        # Audit fix F2: the echo is the ONLY thing here that is optional, so
        # it is also the only thing dropped. Retry without it before
        # refusing, so remembering a convenience can never be the reason a
        # member cannot start writing.
        bucket = [door, question_index, answer, 0, 0, 0, ""]
        if not _fits_after_evicting_spark_cache(session, bucket):
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

    bucket = _bucket_from(
        state, answer=answer, context_mask=int(context_mask) & _context_full_mask()
    )
    if not _fits_after_evicting_spark_cache(session, bucket):
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

    bucket = _bucket_from(state, ai_call_count=state["ai_call_count"] + 1)
    if not _fits_after_evicting_spark_cache(session, bucket):
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

    bucket = _bucket_from(state, ai_assisted=1)
    if not _fits_after_evicting_spark_cache(session, bucket):
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


def take_session_bucket(session):
    """Remove the raw work-session bucket and hand it back to the caller,
    so it can be restored verbatim if what follows fails.

    Audit fix F1 (2026-08-04). A final save writes the working answer into
    the library and then clears this bucket — but it cleared it AFTER the
    add, so the byte guard measured the same text twice: once as the
    library item being written and once as the answer still sitting in a
    bucket this very request was about to delete. On a long answer that
    phantom copy is the difference between saving and being told the
    session is full. Callers now take the bucket first, attempt the write
    against the cookie as it will ACTUALLY look afterwards, and restore on
    failure so a refused save leaves the member's session exactly as it
    was.

    Returns the bucket (or ``None`` when no session is active), which is
    the only value ``restore_session_bucket`` accepts.
    """
    raw = session.get(SESSION_KEY)
    if not isinstance(raw, dict) or "w" not in raw:
        return None
    bucket = raw["w"]
    clear_session(session)
    return bucket


def restore_session_bucket(session, bucket):
    """Put back a bucket taken by ``take_session_bucket``. A ``None`` bucket
    means there was nothing to take, so there is nothing to restore."""
    if bucket is None:
        return
    _write_bucket(session, bucket)


# ---------------------------------------------------------------------------
# Spark memory — PS-WORKSHOP-001 W2c
#
# **What this bucket has to guarantee, and why it is shaped like this.**
# Three requirements pull in different directions:
#
#   1. A dismissed Spark must NEVER come back. That is durable state.
#   2. "Show another idea" must not re-offer something already shown.
#   3. The whole ``workshop_preview`` cookie — the library delta, the Work
#      on Something answer, and this — shares ONE ~3KB budget whose
#      documented worst case already leaves only a handful of bytes spare.
#
# So nothing here stores a Spark's identity as its text. A Spark is
# identified by a short hash of its normalized suggestion, and a cited item
# by a short hash of its item key. Requirements 1 and 2 then collapse into a
# single list: ``offered`` is every Spark hash this visitor has already been
# shown, and a newly generated Spark whose hash is already in it is never
# rendered. A Spark is therefore un-repeatable from the moment it is first
# shown, which makes dismissal durable BY CONSTRUCTION rather than by a
# second mechanism that could drift from the first.
#
# ``current`` caches the Spark actually on screen so that reloading the
# opening re-renders it instead of billing another provider call. That cache
# is the only large thing here (a 220-character suggestion and a
# 160-character seed), and it is also the only OPTIONAL thing: when the
# cookie is too full to hold it the Spark is still shown for that request
# and simply is not remembered.
#
# **Members.** A signed-in member's dismissals live here too, exactly as
# their Work on Something session state does (see this module's header). That
# means a member's dismissals are session-scoped today. Durable per-member
# dismissal belongs in the PS-WORKSHOP-002 migration alongside
# ``knowledge_item_sources``, once member authentication is fully wired
# through Workshop; it is a disclosed W2c scope limit, not an oversight.
# ---------------------------------------------------------------------------

SPARK_KEY = "k"

# Ceilings on the two lists. MAX_OFFERED_SPARKS is the documented cap the
# brief allows if memory would not otherwise fit the budget: past this many
# Sparks in ONE anonymous visit, the OLDEST hash rotates out and that Spark
# becomes theoretically re-offerable. Reaching it requires 12 explicit "Show
# another idea"/dismiss actions in a single visit against a library of at
# most MAX_CONTEXT_ITEMS confirmed items — by which point ``used`` has long
# since saturated and the honest "no further grounded idea" state is what
# renders anyway. The cap is a byte-budget backstop, not a behaviour anyone
# is expected to reach.
MAX_OFFERED_SPARKS = 12
MAX_USED_CONTEXT_HASHES = MAX_CONTEXT_ITEMS

_HASH_CHARS = 10
_ITEM_HASH_CHARS = 8


def spark_fingerprint(suggestion):
    """A short, stable fingerprint for one Spark suggestion.

    Normalized (case-folded, whitespace-collapsed) before hashing so that a
    model returning the same idea with cosmetically different spacing or
    capitalization is still recognized as the same Spark and stays
    dismissed. This is a de-duplication key, never a security boundary:
    truncation is fine, and nothing authorizes anything on the strength of
    it.
    """
    normalized = " ".join(str(suggestion or "").lower().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:_HASH_CHARS]


def item_fingerprint(item_key):
    """A short fingerprint for one confirmed item key.

    Stored instead of the 36-character key itself purely for the byte
    budget. Citations are re-resolved by comparing this against the
    fingerprints of the items CURRENTLY visible to this viewer, so an item
    that has since been archived or deleted simply stops resolving — the
    same "never name an id that no longer resolves" discipline the review
    screen's cited-context disclosure already follows.
    """
    return hashlib.sha256(str(item_key or "").encode("utf-8")).hexdigest()[:_ITEM_HASH_CHARS]


def _string_list_of(value, max_items, max_chars):
    if not isinstance(value, list):
        return []
    return [item[:max_chars] for item in value if isinstance(item, str) and item][:max_items]


def read_spark_state(session):
    """This visitor's Spark memory. Always returns the full shape — an
    absent or malformed bucket degrades to "nothing shown, nothing
    dismissed" rather than raising, matching read_state's own defensive
    reshape discipline.

    ``current`` is ``None`` when no Spark is on screen; otherwise a dict of
    ``{"fingerprint", "suggestion", "focus_seed", "cited_fingerprints"}``.
    """
    raw = session.get(SESSION_KEY)
    bucket = raw.get(SPARK_KEY) if isinstance(raw, dict) else None
    if not isinstance(bucket, list) or len(bucket) != 3:
        return {"current": None, "offered": [], "used": []}

    raw_current, raw_offered, raw_used = bucket
    current = None
    if isinstance(raw_current, list) and len(raw_current) == 4:
        fingerprint, suggestion, focus_seed, cited = raw_current
        if (
            isinstance(fingerprint, str)
            and isinstance(suggestion, str)
            and suggestion
            and isinstance(focus_seed, str)
        ):
            current = {
                "fingerprint": fingerprint[:_HASH_CHARS],
                "suggestion": suggestion[:MAX_SPARK_SUGGESTION_UNITS],
                "focus_seed": focus_seed[:MAX_SPARK_FOCUS_SEED_UNITS],
                "cited_fingerprints": _string_list_of(
                    cited, MAX_USED_CONTEXT_HASHES, _ITEM_HASH_CHARS
                ),
            }

    return {
        "current": current,
        "offered": _string_list_of(raw_offered, MAX_OFFERED_SPARKS, _HASH_CHARS),
        "used": _string_list_of(raw_used, MAX_USED_CONTEXT_HASHES, _ITEM_HASH_CHARS),
    }


def _spark_bucket(state):
    current = state["current"]
    return [
        [
            current["fingerprint"],
            current["suggestion"],
            current["focus_seed"],
            list(current["cited_fingerprints"]),
        ]
        if current
        else 0,
        list(state["offered"]),
        list(state["used"]),
    ]


def already_offered(state, fingerprint):
    """True when this exact Spark has already been shown to this visitor
    during this visit — which is also what makes a dismissal permanent."""
    return fingerprint in state["offered"]


def excluded_item_keys(state, visible_item_keys):
    """Which of the CURRENTLY visible confirmed items have already prompted a
    Spark this visit. Re-derived fresh from today's visible list every call,
    so a fingerprint for an item that is gone simply drops out."""
    used = set(state["used"])
    return [key for key in visible_item_keys if item_fingerprint(key) in used]


def record_spark(session, *, suggestion, focus_seed, cited_item_keys):
    """Remember a freshly generated Spark as the current one, mark it
    offered, and record the confirmed items it drew on.

    Returns ``(ok, remembered)``. ``ok`` is False only when the visitor's
    cookie cannot even hold the small ``offered``/``used`` lists; in that
    case NOTHING was written. ``remembered`` is False when the lists were
    written but the larger ``current`` cache did not fit — the caller still
    renders the Spark, it just will not survive a reload. That split matters:
    the offered list is the dismissal guarantee and must be written if at all
    possible, while the cache is a cost optimization that may be dropped.
    """
    state = read_spark_state(session)
    fingerprint = spark_fingerprint(suggestion)

    offered = [item for item in state["offered"] if item != fingerprint]
    offered.append(fingerprint)
    offered = offered[-MAX_OFFERED_SPARKS:]

    used = list(state["used"])
    for key in cited_item_keys:
        digest = item_fingerprint(key)
        if digest not in used:
            used.append(digest)
    used = used[-MAX_USED_CONTEXT_HASHES:]

    full = {
        "current": {
            "fingerprint": fingerprint,
            "suggestion": suggestion[:MAX_SPARK_SUGGESTION_UNITS],
            "focus_seed": focus_seed[:MAX_SPARK_FOCUS_SEED_UNITS],
            "cited_fingerprints": [item_fingerprint(key) for key in cited_item_keys],
        },
        "offered": offered,
        "used": used,
    }
    bucket = _spark_bucket(full)
    if _would_fit(session, bucket, SPARK_KEY):
        _write_bucket(session, bucket, SPARK_KEY)
        return True, True

    # The cache did not fit. Write the guarantee without it rather than
    # losing the dismissal record to a byte budget.
    lean = {"current": None, "offered": offered, "used": used}
    lean_bucket = _spark_bucket(lean)
    if _would_fit(session, lean_bucket, SPARK_KEY):
        _write_bucket(session, lean_bucket, SPARK_KEY)
        return True, False
    return False, False


def clear_current_spark(session):
    """Drop the cached on-screen Spark, leaving ``offered`` and ``used``
    intact — so the Spark is gone from the screen and can never be offered
    again. This is the whole of what both "Show another idea" and "Do not
    suggest this again" need to do to the PREVIOUS Spark; they differ only
    in what happens next (a new AI call, or nothing).

    Always fits by construction: the resulting bucket is strictly smaller
    than the one already stored, so a dismissal can never be refused for
    want of cookie space.
    """
    state = read_spark_state(session)
    if state["current"] is None and not state["offered"] and not state["used"]:
        return
    state["current"] = None
    _write_bucket(session, _spark_bucket(state), SPARK_KEY)


def dismiss_spark(session, fingerprint):
    """Record an explicit "do not suggest this again" for ``fingerprint``.

    In the common case the Spark being dismissed is the one on screen, which
    ``record_spark`` already added to ``offered`` — so this is usually just
    ``clear_current_spark``. The explicit add covers the case where the
    offered list rotated (MAX_OFFERED_SPARKS) or was never written because
    the cookie was full at generation time: an explicit dismissal is the one
    signal worth spending bytes on, so it is re-asserted here.
    """
    state = read_spark_state(session)
    state["current"] = None
    if fingerprint:
        offered = [item for item in state["offered"] if item != fingerprint]
        offered.append(fingerprint)
        state["offered"] = offered[-MAX_OFFERED_SPARKS:]
    bucket = _spark_bucket(state)
    if _would_fit(session, bucket, SPARK_KEY):
        _write_bucket(session, bucket, SPARK_KEY)
        return True
    # Should be unreachable: this bucket has no ``current`` and at most
    # MAX_OFFERED_SPARKS short hashes, so it is smaller than anything that
    # already fit. Fail honestly rather than silently claiming a dismissal
    # that was not recorded.
    return False


def clear_spark_memory(session):
    """Remove the whole Spark bucket. Used only by "Start fresh", which
    already clears the entire ``workshop_preview`` key — this exists so a
    future caller that wants to reset Spark alone has one honest way to."""
    raw = session.get(SESSION_KEY)
    if not isinstance(raw, dict) or SPARK_KEY not in raw:
        return
    merged = dict(raw)
    merged.pop(SPARK_KEY, None)
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
