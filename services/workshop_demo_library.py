"""Public Workshop demo library — PS-WORKSHOP-001 (owner instruction 2026-08-02).

Owner instruction, 2026-08-02: the public preview's sample library was four
thin items (``services/knowledge_service.py``'s checkpoint fixture). Pete
wants anyone opening Workshop with no account to see a rich, realistic
library AND be able to genuinely add, edit, archive, and restore items and
watch the change persist across requests — without a database, an account,
or touching any real member's data.

This module is deliberately separate from ``services/knowledge_service.py``'s
``get_my_information_checkpoint`` dev-fixture seam: that seam stays exactly
as it is, still backs ``PEERSLATE_WORKSHOP_DEV_FIXTURE``, and is untouched by
this file. This module backs a different, always-available code path used
only for the anonymous/signed-out public preview.

**The persona.** Jordan Ellis, a fictional healthcare-technology
professional — deliberately not Pete and not any real person, in a
different field, so nobody mistakes it for a real profile. The 17 items
mirror the real knowledge-base categories in ``docs/knowledge/``
(accomplishments, career history, skills evidence, technical skills,
personal story, portfolio projects) and exercise every Area/Status filter,
long and short wording, and one item with real edit history — all fixed,
deterministic content (stable UUID keys, fixed literal timestamps), so the
page renders identically on every request and is cache-friendly.

**Session play (Chunk B).** A visitor's own add/edit/archive/restore/delete
actions are stored ONLY in the Flask signed-cookie session, namespaced under
one key (``SESSION_KEY``), layered over the static base library above. This
is never written to a database and never shared between visitors — two
different browser sessions never see each other's changes (each cookie is
independently signed and read back only for its own browser). Hard caps
(``MAX_ADDED_ITEMS``, ``MAX_PREVIEW_WORDING_UNITS``) and a defensive total
byte-size ceiling (``MAX_SESSION_BYTES``) keep the signed cookie well under
the ~4KB a browser allows, because the whole session delta round-trips on
every request as part of the cookie itself. Every rejected action returns an
honest, specific message rather than silently truncating or dropping the
visitor's text.

**Row shape parity.** Every row this module produces uses the exact same key
set as ``services/knowledge_service.py``'s real serialized rows (see
``service_list_row``/``service_get_row`` in
``tests/test_workshop_checkpoint.py``), so ``workshop_routes.py``'s existing
``_real_item_view``/``_real_detail_view``/``_filter_library_rows``/
``_resolve_selected_item_key`` — the same view-model functions that already
render one signed-in owner's real store rows — consume these rows
unchanged. No second, parallel view-model exists for the anonymous path.

**Compact session encoding.** The stored delta uses short top-level keys and
positional (list, not dict) entries for visitor-added items specifically to
keep the signed, base64-encoded cookie small: measured worst-case (4 added
items at the full title/wording caps, near-random-content wording) is well
under 3KB end to end (see ``tests/test_workshop_demo_library.py``).
"""

import hashlib
import json
from uuid import NAMESPACE_URL, uuid4, uuid5

from flask import current_app


# ---------------------------------------------------------------------------
# Persona and constants
# ---------------------------------------------------------------------------

PERSONA_DISPLAY_NAME = "Jordan Ellis"

SESSION_KEY = "workshop_preview"

# Hard caps (owner instruction 2026-08-02): a signed cookie is ~4KB, so a
# visitor's own additions are capped both in count and in per-item wording
# length. Enforced server-side in add_item/edit_item below — never only in
# the browser's maxlength attribute.
MAX_ADDED_ITEMS = 4
# "Characters" here means Python string length (Unicode code points), the
# plain-language reading of the owner's "400 characters" instruction — not
# the UTF-16 code-unit convention services/knowledge_service.py uses for its
# own (much larger) 8000-unit bound.
MAX_PREVIEW_WORDING_UNITS = 400
# Defensive ceiling on the fully-encoded, signed session cookie value.
# Measured worst case (4 items at both caps, near-random wording) is ~2KB;
# this ~3KB ceiling is a belt-and-suspenders guard against an unanticipated
# encoding regression, not a limit any caller should expect to reach.
MAX_SESSION_BYTES = 3072

CAP_ITEMS_MESSAGE = (
    "Preview holds up to 4 added items — sign in for an unlimited private "
    "library."
)
CAP_WORDING_MESSAGE = (
    "Preview wording is limited to 400 characters for this sample session "
    "— shorten it and try again."
)
SESSION_FULL_MESSAGE = (
    "This preview session is full — sign in for an unlimited private "
    "library."
)

_CLASS_CODE = {"work": "w", "personal": "p", "both": "b", "unclassified": "u"}
_CLASS_CODE_REV = {v: k for k, v in _CLASS_CODE.items()}
_STATUS_CODE = {"confirmed": "c", "suggested": "s", "unfinished": "f", "archived": "a"}
_STATUS_CODE_REV = {v: k for k, v in _STATUS_CODE.items()}

_LIST_ROW_KEYS = (
    "item_key",
    "status",
    "classification",
    "current_version",
    "confirmed_version",
    "confirmed_at",
    "archived_at",
    "created_at",
    "updated_at",
    "version_token",
    "title",
    "body_format",
    "authored_via",
)
_GET_ROW_EXTRA_KEYS = (
    "version",
    "approved_wording",
    "original_member_wording",
    "saved_at",
    "history",
)

# Visitor-added items carry fixed, deterministic timestamps rather than
# datetime.now() — nothing in the current templates renders created_at /
# updated_at (workshop_routes.py's _real_item_view/_real_detail_view never
# read them), so a fixed literal keeps this module free of wall-clock state
# without losing anything a visitor can actually see.
_ADDED_ITEM_TIMESTAMP = "2026-08-02T00:00:00Z"


def _demo_key(slug):
    """A stable, deterministic UUID for one base-library item.

    Mirrors services/knowledge_service.py's _fixture_key idiom (uuid5 over a
    namespaced slug) but under this module's own namespace string, so a demo
    library key can never collide with the checkpoint dev-fixture's keys.
    """
    return str(uuid5(NAMESPACE_URL, f"peerslate:workshop-demo-library:{slug}"))


def _demo_token(slug):
    """A stable 16-hex-character token, shaped like a real row_version."""
    return hashlib.sha256(
        f"peerslate:workshop-demo-library-token:{slug}".encode("utf-8")
    ).hexdigest()[:16]


def _base_item(
    slug,
    title,
    classification,
    status,
    wording,
    *,
    created_at,
    updated_at=None,
    confirmed_at=None,
    archived_at=None,
    current_version=1,
    confirmed_version=None,
    history=(),
):
    restore_status = "confirmed" if status == "archived" else status
    return {
        "item_key": _demo_key(slug),
        "title": title,
        "wording": wording,
        "classification": classification,
        "status": status,
        "status_code": _STATUS_CODE[status],
        "restore_status": restore_status,
        "restore_status_code": _STATUS_CODE[restore_status],
        "current_version": current_version,
        "confirmed_version": confirmed_version,
        "confirmed_at": confirmed_at,
        "archived_at": archived_at,
        "created_at": created_at,
        "updated_at": updated_at or created_at,
        "version_token": _demo_token(slug),
        "history": tuple(history),
    }


# ---------------------------------------------------------------------------
# The 17-item base library (Jordan Ellis, fictional persona)
#
# Content spec: coverage requires every Area (Work/Personal/Both/Not set)
# and every Status (Confirmed majority, Suggested x2, Unfinished x2,
# Archived x2), long and short wording, and one item (#1) with real edit
# history. All content, classifications, and statuses below are authored
# verbatim from the approved content spec.
# ---------------------------------------------------------------------------

BASE_ITEMS = (
    _base_item(
        "rebuilt-patient-intake",
        "Rebuilt patient intake from 40 minutes to 9",
        "work",
        "confirmed",
        "I mapped every step of a paper intake process, found four duplicate "
        "data-entry points, and redesigned the flow around a single shared "
        "record. Average intake dropped from about 40 minutes to 9, and "
        "front-desk overtime fell with it.",
        created_at="2025-01-10T14:20:00Z",
        updated_at="2025-09-18T16:40:00Z",
        confirmed_at="2025-09-18T16:40:00Z",
        current_version=3,
        confirmed_version=3,
        history=(
            {
                "version": 1,
                "title": "Rebuilt patient intake from 40 minutes to 9",
                "body_format": "plain",
                "authored_via": "typed",
                "saved_at": "2025-01-10T14:20:00Z",
            },
            {
                "version": 2,
                "title": "Rebuilt patient intake from 40 minutes to 9",
                "body_format": "plain",
                "authored_via": "typed",
                "saved_at": "2025-04-02T09:15:00Z",
            },
            {
                "version": 3,
                "title": "Rebuilt patient intake from 40 minutes to 9",
                "body_format": "plain",
                "authored_via": "typed",
                "saved_at": "2025-09-18T16:40:00Z",
            },
        ),
    ),
    _base_item(
        "scheduling-systems-consolidation",
        "Led the move from three scheduling systems to one",
        "work",
        "confirmed",
        "Three clinics each ran their own scheduler. I ran the selection, "
        "migrated 60,000 historical appointments, and trained 80 staff over "
        "six weeks. We cut double-bookings to near zero and retired two "
        "vendor contracts.",
        created_at="2025-02-05T11:00:00Z",
        confirmed_at="2025-02-05T11:00:00Z",
        confirmed_version=1,
    ),
    _base_item(
        "requirements-gathering-shadowing",
        "Requirements gathering with people who hate meetings",
        "work",
        "confirmed",
        "I stopped asking clinical staff to attend requirements workshops "
        "and started shadowing them for half-days instead. The specs got "
        "sharper because I watched what people actually did rather than "
        "what they remembered doing.",
        created_at="2025-03-12T10:00:00Z",
        confirmed_at="2025-03-12T10:00:00Z",
        confirmed_version=1,
    ),
    _base_item(
        "clinician-engineer-translation",
        "Translating between clinicians and engineers",
        "both",
        "confirmed",
        "I spend most of my time turning \"this screen fights me\" into a "
        "specific, buildable change — and turning \"that's a schema "
        "constraint\" into something a nurse manager can weigh. It is the "
        "part of the job I am best at.",
        created_at="2025-03-20T08:30:00Z",
        confirmed_at="2025-03-20T08:30:00Z",
        confirmed_version=1,
    ),
    _base_item(
        "data-migration-without-losing-history",
        "Data migration without losing history",
        "work",
        "confirmed",
        "Two records-system migrations, both with zero unrecoverable data "
        "loss. The trick was insisting on a read-only rehearsal environment "
        "and a rollback plan nobody expected to need.",
        created_at="2025-04-18T13:00:00Z",
        confirmed_at="2025-04-18T13:00:00Z",
        confirmed_version=1,
    ),
    _base_item(
        "mentoring-analysts-into-product",
        "Mentoring analysts into product roles",
        "both",
        "confirmed",
        "Four people I mentored moved from analyst work into product or "
        "clinical-informatics roles. I meet them monthly, and I mostly ask "
        "questions rather than give answers.",
        created_at="2025-05-02T09:45:00Z",
        confirmed_at="2025-05-02T09:45:00Z",
        confirmed_version=1,
    ),
    _base_item(
        "public-speaking-preparation",
        "Public speaking still takes preparation",
        "personal",
        "confirmed",
        "I present well now, but only because I over-prepare. I write the "
        "first two minutes word for word and improvise the rest. Worth "
        "remembering when I coach someone who says they are \"just not a "
        "natural.\"",
        created_at="2025-05-15T19:00:00Z",
        confirmed_at="2025-05-15T19:00:00Z",
        confirmed_version=1,
    ),
    _base_item(
        "trail-running-long-distance-thinking",
        "Trail running and long-distance thinking",
        "personal",
        "confirmed",
        "I run trails four mornings a week. Most of my clearest work "
        "thinking happens somewhere in the second hour.",
        created_at="2025-05-16T06:30:00Z",
        confirmed_at="2025-05-16T06:30:00Z",
        confirmed_version=1,
    ),
    _base_item(
        "teaching-myself-sql-at-34",
        "Teaching myself SQL at 34",
        "both",
        "confirmed",
        "I learned SQL because I was tired of waiting two weeks for a "
        "report. It changed what I could ask on my own, and it is the "
        "single skill that most changed my career trajectory.",
        created_at="2025-06-01T12:00:00Z",
        confirmed_at="2025-06-01T12:00:00Z",
        confirmed_version=1,
    ),
    _base_item(
        "volunteer-coordination-community-clinic",
        "Volunteer coordination at the community clinic",
        "personal",
        "confirmed",
        "I schedule and onboard weekend volunteers at a free clinic. It is "
        "unglamorous logistics work and I find it steadying.",
        created_at="2025-06-10T17:20:00Z",
        confirmed_at="2025-06-10T17:20:00Z",
        confirmed_version=1,
    ),
    _base_item(
        "grant-reporting-outcome-measurement",
        "Grant reporting and outcome measurement",
        "work",
        "confirmed",
        "I built the outcome-tracking spreadsheet three grant cycles ran "
        "on. Not sophisticated, but it survived audit twice and told the "
        "truth about what we could and could not measure.",
        created_at="2025-06-22T10:10:00Z",
        confirmed_at="2025-06-22T10:10:00Z",
        confirmed_version=1,
    ),
    _base_item(
        "learning-to-say-no-to-good-projects",
        "Learning to say no to good projects",
        "both",
        "unfinished",
        "Still working out how to write this one. The short version is "
        "that saying yes to everything made me mediocre at all of it, and "
        "the fix was harder than it sounds.",
        created_at="2025-11-05T21:00:00Z",
    ),
    _base_item(
        "2023-reorganization-draft",
        "Something about the 2023 reorganization",
        "work",
        "unfinished",
        "Started this and stopped — need to think about what is actually "
        "mine to tell here versus what belongs to other people.",
        created_at="2025-11-10T21:30:00Z",
    ),
    _base_item(
        "cross-functional-facilitation-suggestion",
        "Cross-functional facilitation",
        "work",
        "suggested",
        "PeerSlate noticed you describe running sessions between clinical "
        "and technical groups in several confirmed items. Would you like "
        "to make that a distinct skill?",
        created_at="2026-01-15T08:00:00Z",
    ),
    _base_item(
        "process-redesign-suggestion",
        "Process redesign",
        "work",
        "suggested",
        "Two of your confirmed items describe redesigning a workflow end "
        "to end. That may be worth naming on its own.",
        created_at="2026-01-15T08:00:00Z",
    ),
    _base_item(
        "early-bookkeeping-role",
        "Early bookkeeping role",
        "work",
        "archived",
        "Two years doing small-business bookkeeping before healthcare. "
        "True, but no longer part of the story I am telling.",
        created_at="2024-08-01T09:00:00Z",
        confirmed_at="2024-08-01T09:00:00Z",
        archived_at="2025-01-05T00:00:00Z",
        updated_at="2025-01-05T00:00:00Z",
        confirmed_version=1,
    ),
    _base_item(
        "draft-bio-2024",
        "Draft bio from 2024",
        "unclassified",
        "archived",
        "An older personal summary. Superseded by better wording, kept in "
        "case a phrase is worth reusing.",
        created_at="2024-05-10T09:00:00Z",
        confirmed_at="2024-05-10T09:00:00Z",
        archived_at="2025-02-14T00:00:00Z",
        updated_at="2025-02-14T00:00:00Z",
        confirmed_version=1,
    ),
)

BASE_ITEMS_BY_KEY = {item["item_key"]: item for item in BASE_ITEMS}


# ---------------------------------------------------------------------------
# Row shaping — matches services/knowledge_service.py's serialized row keys
# exactly (service_list_row / service_get_row in
# tests/test_workshop_checkpoint.py), so workshop_routes.py's real view-model
# functions consume these rows unchanged.
# ---------------------------------------------------------------------------


def _list_row(*, item_key, title, classification, status, base):
    return {
        "item_key": item_key,
        "status": status,
        "classification": classification,
        "current_version": base["current_version"],
        "confirmed_version": base["confirmed_version"],
        "confirmed_at": base["confirmed_at"],
        "archived_at": base["archived_at"],
        "created_at": base["created_at"],
        "updated_at": base["updated_at"],
        "version_token": base["version_token"],
        "title": title,
        "body_format": "plain",
        "authored_via": "typed",
    }


def _get_row(*, item_key, title, wording, classification, status, base):
    row = _list_row(
        item_key=item_key,
        title=title,
        classification=classification,
        status=status,
        base=base,
    )
    row.update(
        {
            "version": base["current_version"],
            "approved_wording": wording,
            "original_member_wording": wording,
            "saved_at": base["updated_at"],
            "history": [dict(entry) for entry in base["history"]],
        }
    )
    return row


def _added_base(item_key, status_code):
    """A synthetic ``base``-shaped dict for a visitor-added item, so
    ``_list_row``/``_get_row`` above can build its view without a second,
    forked set of field-building functions."""
    status = _STATUS_CODE_REV.get(status_code, "confirmed")
    confirmed_version = 1 if status in ("confirmed", "archived") else None
    confirmed_at = _ADDED_ITEM_TIMESTAMP if status in ("confirmed", "archived") else None
    archived_at = _ADDED_ITEM_TIMESTAMP if status == "archived" else None
    return {
        "current_version": 1,
        "confirmed_version": confirmed_version,
        "confirmed_at": confirmed_at,
        "archived_at": archived_at,
        "created_at": _ADDED_ITEM_TIMESTAMP,
        "updated_at": _ADDED_ITEM_TIMESTAMP,
        "version_token": hashlib.sha256(item_key.encode("utf-8")).hexdigest()[:16],
        "history": (),
    }


# ---------------------------------------------------------------------------
# Session delta: read/write/parse
#
# Stored under session[SESSION_KEY] as a compact dict with short keys:
#   "a": [[item_key, title, wording, class_code, status_code], ...]  (added)
#   "e": {item_key: {"t": title, "w": wording, "c": class_code}}     (edits)
#   "s": {item_key: status_code}                                     (status
#        overrides from archive/restore/edit-confirm actions — "last action
#        wins", mirroring the real store's single-valued status field)
#   "d": [item_key, ...]  (deleted BASE item keys; a deleted ADDED item is
#        simply removed from "a" instead, freeing its add-cap slot)
# ---------------------------------------------------------------------------


def empty_delta():
    return {"a": [], "e": {}, "s": {}, "d": []}


def read_session_delta(session):
    """Read this visitor's own preview delta back from their session cookie.

    Defensively re-shapes anything malformed (a tampered-but-still-validly-
    signed cookie should not be possible via itsdangerous, but a stale shape
    from a future schema change should degrade to empty rather than crash).
    """
    raw = session.get(SESSION_KEY)
    if not isinstance(raw, dict):
        return empty_delta()
    added = raw.get("a")
    edits = raw.get("e")
    overrides = raw.get("s")
    deleted = raw.get("d")
    return {
        "a": [
            list(entry)
            for entry in (added if isinstance(added, list) else [])
            if isinstance(entry, (list, tuple)) and len(entry) == 5
        ][:MAX_ADDED_ITEMS],
        "e": {
            key: dict(value)
            for key, value in (edits.items() if isinstance(edits, dict) else [])
            if isinstance(value, dict)
        },
        "s": dict(overrides) if isinstance(overrides, dict) else {},
        "d": list(deleted) if isinstance(deleted, list) else [],
    }


def write_session_delta(session, delta):
    session[SESSION_KEY] = delta
    session.modified = True


def _would_fit(session, candidate_delta):
    """True if replacing this visitor's delta with ``candidate_delta`` keeps
    the fully signed, encoded session cookie at or under MAX_SESSION_BYTES.

    Measures the actual signed token Flask would emit (not just a raw JSON
    proxy), so this reflects the real Set-Cookie payload a visitor's browser
    would receive.
    """
    trial = dict(session)
    trial[SESSION_KEY] = candidate_delta
    try:
        serializer = current_app.session_interface.get_signing_serializer(current_app)
        token = serializer.dumps(trial)
        size = len(token.encode("utf-8")) if isinstance(token, str) else len(token)
    except Exception:
        raw = json.dumps(trial, separators=(",", ":"), default=str)
        size = len(raw.encode("utf-8"))
    return size <= MAX_SESSION_BYTES


# ---------------------------------------------------------------------------
# Reads: merge base library + session delta into real-row-shaped output
# ---------------------------------------------------------------------------


def list_rows(delta):
    """Every visible row (base + visitor-added, minus deleted), list-row
    shaped, with edits/status overrides applied. Order: base library first
    (in its authored order), then the visitor's own added items."""
    rows = []
    deleted = set(delta.get("d", []))
    edits = delta.get("e", {})
    overrides = delta.get("s", {})

    for base in BASE_ITEMS:
        key = base["item_key"]
        if key in deleted:
            continue
        title = base["title"]
        classification = base["classification"]
        patch = edits.get(key)
        if patch:
            title = patch.get("t", title)
            if "c" in patch:
                classification = _CLASS_CODE_REV.get(patch["c"], classification)
        status = _STATUS_CODE_REV.get(overrides.get(key, base["status_code"]), base["status"])
        rows.append(_list_row(item_key=key, title=title, classification=classification, status=status, base=base))

    for entry in delta.get("a", []):
        key, a_title, _a_wording, a_class_code, a_status_code = entry
        title = a_title
        classification = _CLASS_CODE_REV.get(a_class_code, "unclassified")
        patch = edits.get(key)
        if patch:
            title = patch.get("t", title)
            if "c" in patch:
                classification = _CLASS_CODE_REV.get(patch["c"], classification)
        status_code = overrides.get(key, a_status_code)
        status = _STATUS_CODE_REV.get(status_code, "confirmed")
        added_base = _added_base(key, status_code=a_status_code)
        rows.append(_list_row(item_key=key, title=title, classification=classification, status=status, base=added_base))

    return rows


def get_row(item_key, delta):
    """The single merged get-row for ``item_key``, or ``None`` if it is not
    part of this visitor's effective library (deleted, or never existed)."""
    deleted = set(delta.get("d", []))
    if item_key in deleted:
        return None
    edits = delta.get("e", {})
    overrides = delta.get("s", {})

    base = BASE_ITEMS_BY_KEY.get(item_key)
    if base is not None:
        title, wording, classification = base["title"], base["wording"], base["classification"]
        patch = edits.get(item_key)
        if patch:
            title = patch.get("t", title)
            wording = patch.get("w", wording)
            if "c" in patch:
                classification = _CLASS_CODE_REV.get(patch["c"], classification)
        status = _STATUS_CODE_REV.get(overrides.get(item_key, base["status_code"]), base["status"])
        return _get_row(item_key=item_key, title=title, wording=wording, classification=classification, status=status, base=base)

    for entry in delta.get("a", []):
        key, a_title, a_wording, a_class_code, a_status_code = entry
        if key != item_key:
            continue
        title, wording = a_title, a_wording
        classification = _CLASS_CODE_REV.get(a_class_code, "unclassified")
        patch = edits.get(item_key)
        if patch:
            title = patch.get("t", title)
            wording = patch.get("w", wording)
            if "c" in patch:
                classification = _CLASS_CODE_REV.get(patch["c"], classification)
        status_code = overrides.get(item_key, a_status_code)
        status = _STATUS_CODE_REV.get(status_code, "confirmed")
        added_base = _added_base(item_key, status_code=a_status_code)
        return _get_row(item_key=item_key, title=title, wording=wording, classification=classification, status=status, base=added_base)

    return None


# ---------------------------------------------------------------------------
# Writes: add / edit / archive / restore / delete, all session-only
# ---------------------------------------------------------------------------


def add_item(session, *, title, wording, classification, status):
    """Add one visitor-authored item to this session's preview library.

    Returns ``(item_key, error_message)``: on success ``error_message`` is
    ``None``; on a cap violation ``item_key`` is ``None`` and
    ``error_message`` is the honest, specific reason (never a silent drop).
    """
    delta = read_session_delta(session)
    if len(delta["a"]) >= MAX_ADDED_ITEMS:
        return None, CAP_ITEMS_MESSAGE
    if len(wording) > MAX_PREVIEW_WORDING_UNITS:
        return None, CAP_WORDING_MESSAGE

    item_key = str(uuid4())
    class_code = _CLASS_CODE.get(classification, "u")
    status_code = _STATUS_CODE.get(status, "c")

    candidate = {
        "a": delta["a"] + [[item_key, title, wording, class_code, status_code]],
        "e": delta["e"],
        "s": delta["s"],
        "d": delta["d"],
    }
    if not _would_fit(session, candidate):
        return None, SESSION_FULL_MESSAGE

    write_session_delta(session, candidate)
    return item_key, None


def edit_item(session, item_key, *, title, wording, classification, status):
    """Edit an item (base or visitor-added) already in this session's
    effective library. Returns ``(ok, error_message)``; ``ok`` is ``False``
    with ``error_message`` ``None`` when the item is not part of this
    visitor's library at all (never confirms or denies why)."""
    delta = read_session_delta(session)
    if get_row(item_key, delta) is None:
        return False, None
    if len(wording) > MAX_PREVIEW_WORDING_UNITS:
        return False, CAP_WORDING_MESSAGE

    edits = dict(delta["e"])
    edits[item_key] = {"t": title, "w": wording, "c": _CLASS_CODE.get(classification, "u")}
    overrides = dict(delta["s"])
    overrides[item_key] = _STATUS_CODE.get(status, "c")

    candidate = {"a": delta["a"], "e": edits, "s": overrides, "d": delta["d"]}
    if not _would_fit(session, candidate):
        return False, SESSION_FULL_MESSAGE

    write_session_delta(session, candidate)
    return True, None


def archive_item(session, item_key):
    """Archive an item in this session's preview library. Returns
    ``(ok, error_message)``."""
    delta = read_session_delta(session)
    if get_row(item_key, delta) is None:
        return False, None

    overrides = dict(delta["s"])
    overrides[item_key] = _STATUS_CODE["archived"]
    candidate = {"a": delta["a"], "e": delta["e"], "s": overrides, "d": delta["d"]}
    if not _would_fit(session, candidate):
        return False, SESSION_FULL_MESSAGE

    write_session_delta(session, candidate)
    return True, None


def restore_item(session, item_key):
    """Restore an archived item back to its natural (pre-archive) status —
    the base item's own status if it is not natively archived, else
    "confirmed" for the two natively-archived base items; the visitor's own
    original choice for an added item. Returns ``(ok, error_message)``."""
    delta = read_session_delta(session)
    if get_row(item_key, delta) is None:
        return False, None

    base = BASE_ITEMS_BY_KEY.get(item_key)
    if base is not None:
        target_code = base["restore_status_code"]
    else:
        target_code = "c"
        for entry in delta["a"]:
            if entry[0] == item_key:
                target_code = entry[4]
                break

    overrides = dict(delta["s"])
    overrides[item_key] = target_code
    candidate = {"a": delta["a"], "e": delta["e"], "s": overrides, "d": delta["d"]}
    if not _would_fit(session, candidate):
        return False, SESSION_FULL_MESSAGE

    write_session_delta(session, candidate)
    return True, None


def delete_item(session, item_key):
    """Permanently remove an item from this session's preview library
    (never the database — there is no database here). A deleted
    visitor-added item is dropped from the add list entirely, freeing its
    add-cap slot. Returns ``(ok, error_message)``."""
    delta = read_session_delta(session)
    if get_row(item_key, delta) is None:
        return False, None

    edits = dict(delta["e"])
    edits.pop(item_key, None)
    overrides = dict(delta["s"])
    overrides.pop(item_key, None)

    if item_key in BASE_ITEMS_BY_KEY:
        deleted = list(delta["d"])
        if item_key not in deleted:
            deleted.append(item_key)
        candidate = {"a": delta["a"], "e": edits, "s": overrides, "d": deleted}
    else:
        added = [entry for entry in delta["a"] if entry[0] != item_key]
        candidate = {"a": added, "e": edits, "s": overrides, "d": delta["d"]}

    if not _would_fit(session, candidate):
        return False, SESSION_FULL_MESSAGE

    write_session_delta(session, candidate)
    return True, None
