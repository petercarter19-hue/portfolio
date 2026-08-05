"""Opportunity Slate room routes — PS-OPPSLATE-001, slices OS-1 and OS-2.

Package: docs/initiatives/PS-OPPORTUNITY-SLATE-001. Controlling contract:
01_ARCHITECTURE_AND_IMPLEMENTATION_HANDOFF.md, sections 3 (shell), 5
(palette), 7 (processing/failure), 9 (routes), 10 (AI contract), 11
(security), 12 (responsive), 13 (accessibility), 16 (slice scope), 17-18
(owner decisions, public v1 mode).

Slice OS-1 delivered role intake, Review Source, and checkpoint 1 of 2.
Slice OS-2 adds the room's first two AI steps and the screen they feed:

* **AI step 1**, extraction concerns. PeerSlate proposes spans of the
  captured wording that may have come through wrong. It proposes; the member
  applies or dismisses each one.
* **AI step 2**, statement interpretation. The confirmed source is segmented
  into statements, each with a proposed class and a proposed AND/OR reading.
* **Review Requirements** (image 03) with the correction rail, and
  checkpoint 2 of 2.

**No AI client is imported here.** Both steps go through
``services/opportunity_analysis_service.py``, which owns every prompt
contract, every validator, and the only Anthropic client in this room. This
module renders proposals and records decisions; it cannot reach the provider.

Alignment analysis is OS-3, saving is OS-4, dictation is OS-5, and document
upload / public-link import are OS-6. Where the locked visual set shows one
of those, this slice renders an honest, inert state rather than a control
that pretends to work — including image 03's primary action, which reads
"Confirm requirements" here because nothing is analyzed when it is pressed.

Because slice OS-2 has real AI latency, image 07/08's bounded stage rail
becomes legitimate for the first time, and it is used for exactly the two
waits that exist: the wording review and the statement interpretation. Its
stages name real request boundaries. No stage in this room describes work
that is not happening, and there is still no rail on any transition that
merely writes a row.

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
from uuid import UUID, uuid4

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
from services.opportunity_analysis_service import (
    ANALYSED_CLASSES,
    locate_spans,
    MAX_PUBLIC_AI_SOURCE_UNITS,
    MAX_PUBLIC_ANALYSED_STATEMENTS,
    MAX_PUBLIC_CITATIONS_TOTAL,
    MAX_PUBLIC_EVIDENCE_ITEMS,
    MAX_PUBLIC_STATEMENTS,
    OpportunityAnalysisError,
    build_clause_vocabulary,
    derive_alignment,
    opportunity_analysis_service,
)
from services.opportunity_slate_service import (
    MAX_CLARIFICATION_UNITS,
    MAX_RESPONSE_TEXT_UNITS,
    MAX_SOURCE_TEXT_UNITS,
    RESPONSE_KINDS,
    STATEMENT_CLASSES,
    OpportunitySlateServiceError,
    apply_concern_correction,
    opportunity_slate_service,
    validate_source_text,
)
from services.opportunity_source_intake_service import (
    MAX_UPLOAD_BYTES,
    OpportunitySourceIntakeError,
    extract_imported_link,
    extract_uploaded_document,
)
from services.workshop_demo_library import BASE_ITEMS as WORKSHOP_DEMO_ITEMS
from services.workshop_demo_library import PERSONA_DISPLAY_NAME as DEMO_PERSONA_NAME


opportunity_slate = Blueprint("opportunity_slate", __name__)

ROOM_PATH = "/opportunity-slate"

# Handoff section 18: the anonymous context token is a browser-held working
# state, not a login. Eight hours is long enough that a visitor can step
# away mid-review without silently losing their pasted role text, and short
# enough that a token copied out of one browser stops working the same day.
PUBLIC_CONTEXT_MAX_AGE_SECONDS = 8 * 60 * 60
PUBLIC_CONTEXT_SALT = "peerslate-opportunity-slate-working-v1"
# Bumped by slice OS-2: the anonymous working state now also carries the AI
# proposals and the visitor's decisions on them. A slice OS-1 token no longer
# validates, so an in-flight visitor is reset honestly to intake rather than
# rehydrated into a half-shaped screen.
#
# Bumped again by slice OS-3, which adds the alignment result and the
# visitor's own responses. Same rule, same reason.
PUBLIC_CONTEXT_VERSION = 3
# Defensive bound on the inbound token string itself, before any signature
# work. Comfortably above a signed, compressed 20,000-unit source plus its
# correction; far below MAX_CONTENT_LENGTH.
MAX_PUBLIC_CONTEXT_TOKEN_LENGTH = 400_000
_SERIALIZER_EXTENSION_KEY = "peerslate_opportunity_slate_serializer"
# Slice OS-6, independent review (non-blocking, fixed now): the truncation
# notice must not be a bare, foreverreplayable query-string value — a
# bookmarked or history-replayed ``?notice=upload_truncated`` URL would
# otherwise resurface the banner for an event that may not have just
# happened, or may never have happened for THIS visit. The notice value is
# therefore a short-lived SIGNED token (own salt — never replayable against
# the anonymous-session serializer above) carrying only the notice kind;
# ``URLSafeTimedSerializer`` embeds and checks a timestamp natively, so
# ``max_age`` below is the whole one-time-binding mechanism.
NOTICE_TOKEN_SALT = "peerslate-opportunity-slate-notice-v1"
NOTICE_TOKEN_MAX_AGE_SECONDS = 60
_NOTICE_SERIALIZER_EXTENSION_KEY = "peerslate_opportunity_slate_notice_serializer"

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
STEP_REQUIREMENTS = "requirements"
STEP_ALIGNMENT = "alignment"
# ``replace`` is a role-intake variant, not a third screen: it opens the
# intake editor empty so the member can bring in a different role.
STEP_REPLACE = "replace"
_ALLOWED_STEPS = frozenset(
    {STEP_ROLE, STEP_REVIEW, STEP_REPLACE, STEP_REQUIREMENTS, STEP_ALIGNMENT}
)

# The anonymous session's actions, split across two endpoints for one
# reason: rate limiting. Handoff section 18 safeguard 2 sets the AI budget at
# <= 6 per minute per client, which is far too tight for ordinary typing and
# navigation. Putting the two AI actions on their own route lets each carry
# the budget that fits it, instead of one endpoint forced to choose between
# throttling a visitor's corrections and leaving the model calls unbounded.
_PUBLIC_SESSION_ACTIONS = frozenset(
    {
        "render",
        "step",
        "source",
        "correct",
        "confirm",
        "discard",
        # Slice OS-2, and none of these calls a model: they record the
        # visitor's own decisions about proposals already made.
        "resolve",
        "statement",
        "confirm_requirements",
        # Slice OS-3, and likewise no model: the visitor's own response to one
        # qualification, and selecting which qualification the rails describe.
        "respond",
        "select",
    }
)
_PUBLIC_PROPOSE_ACTIONS = frozenset({"review", "interpret", "analyze"})
_PUBLIC_ACTIONS = _PUBLIC_SESSION_ACTIONS | _PUBLIC_PROPOSE_ACTIONS

# Presentation-only. The service returns validated enum values; the member
# facing labels are a view concern and live here (the workshop_routes.py
# convention). Reproduced from image 03's group headings.
STATEMENT_CLASS_LABELS = {
    "required_qualification": "Required qualification",
    "preferred_qualification": "Preferred qualification",
    "responsibility": "Responsibility",
    "informational_statement": "Informational statement",
}
STATEMENT_GROUP_LABELS = {
    "required_qualification": "Required qualifications",
    "preferred_qualification": "Preferred qualifications",
    "responsibility": "Responsibilities",
    "informational_statement": "Informational statements",
}
# Image 03's group order. Required, Preferred, Responsibilities, and
# Informational statements are four SEPARATE cards and are never merged
# (locked rule; handoff section 14-M14).
STATEMENT_GROUP_ORDER = (
    "required_qualification",
    "preferred_qualification",
    "responsibility",
    "informational_statement",
)

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

# ---------------------------------------------------------------------------
# Slice OS-2 failure copy — image 09-b's grammar, told for the two AI steps
# this slice actually runs.
#
# Image 09-b is the analysis-failure card: heading, one sentence saying what
# is unchanged, a retry and a review-inputs action, and the truth footer
# "Results not generated | Nothing was saved." Slice OS-2 has no analysis, so
# reproducing that card verbatim would name a step that never ran. The
# grammar is reproduced exactly; the nouns are the ones true here (handoff
# section 14-M11: trust-critical sentences are quoted, the rest follow the
# images' meaning).
# ---------------------------------------------------------------------------
REVIEW_FAILURE_HEADING = "We couldn't review this wording."
REVIEW_FAILURE_MESSAGE = "Your role text is unchanged."
INTERPRET_FAILURE_HEADING = "We couldn't read the employer's statements."
INTERPRET_FAILURE_MESSAGE = "Your confirmed source is unchanged."
PROPOSAL_FAILURE_TRUTH = "Results not generated • Nothing was saved."

# The anonymous spend guard, refusing. It is a real limit on a real preview,
# so it says so plainly instead of pretending to be a transient error.
#
# TWO REFUSALS, TWO CARDS (slice OS-2 independent review, finding F2). The
# guard says no in two entirely different situations and only one of them is
# a limit anybody reached:
#
#   * ceiling_closed — PEERSLATE_OPPSLATE_DAILY_AI_CEILING is 0 or unset. That
#     is the SHIPPED DEFAULT in both app.py and .env.example, so "flag on,
#     budget never opened" is the most likely first state this feature is ever
#     seen in. Telling that visitor a daily limit "has been reached" describes
#     spending that never happened, and "can run again tomorrow" promises a
#     recovery that will not come: tomorrow the ceiling is still 0.
#   * daily_ceiling — a real ceiling was opened and today's is used up. Then
#     the original wording is exactly right, tomorrow included.
#
# Both cards keep image 09-b's grammar (heading, what is unchanged, the truth
# footer) and both keep the section 7 guarantees: the visitor's inputs are
# preserved and nothing was saved.
PUBLIC_BUDGET_HEADING = "This preview has reached its daily limit."
PUBLIC_BUDGET_MESSAGE = (
    "PeerSlate caps how much of this preview runs each day. Your role text is "
    "still here and still yours to edit — the review can run again tomorrow, "
    "and membership does not share this cap."
)
PUBLIC_BUDGET_CLOSED_HEADING = "Wording review is not available in this preview."
PUBLIC_BUDGET_CLOSED_MESSAGE = (
    "PeerSlate has not opened this preview's daily AI budget. Your role text is "
    "still here and still yours to edit."
)
PUBLIC_OVERSIZE_HEADING = "That role text is too long for this preview."
PUBLIC_OVERSIZE_MESSAGE = (
    f"The preview reads up to {MAX_PUBLIC_AI_SOURCE_UNITS:,} characters of role "
    "text. Your text is still below, exactly as you pasted it — shorten it, or "
    "bring the full role in with membership."
)
# ---------------------------------------------------------------------------
# Slice OS-6 failure copy — the two fallback contracts image 09-a defines for
# document upload and public-link import (handoff section 7's failure
# table). Both are reproduced as the single card that covers every internal
# reason a member's document or link could not become a source: neither
# route's error handling ever branches member-facing copy on which guard
# rejected the input, because a reason-specific message would help calibrate
# a probe against the SSRF/parsing guard rather than tell the member
# anything they can act on. "Try again" and "paste the role text instead"
# both work already: this card renders back on the same intake screen the
# paste box and the two tiles are already on.
# ---------------------------------------------------------------------------
UPLOAD_FAILURE_HEADING = "We couldn't read this document."
UPLOAD_FAILURE_MESSAGE = (
    "Nothing was saved or analyzed, and the file you uploaded was not kept. "
    "Try a different PDF, DOCX, or TXT file, or paste the role text instead."
)
IMPORT_FAILURE_HEADING = "We couldn't import that link."
IMPORT_FAILURE_MESSAGE = (
    "Nothing was saved or analyzed. Try a different public link, or paste "
    "the role text instead."
)
INTAKE_FAILURE_TRUTH = "Session private • Nothing was saved or analyzed."
# The one non-fatal notice this slice adds: the extracted text was longer
# than PeerSlate can review and was cut to fit, truthfully labeled rather
# than silently shortened. Never rendered for a paste/dictation version —
# those already refuse an over-limit submission outright (validate_source_
# text's "too_long" field error) instead of ever truncating the member's own
# typed wording.
UPLOAD_TRUNCATED_NOTICE = (
    f"This document was longer than PeerSlate reviews. The first "
    f"{MAX_SOURCE_TEXT_UNITS:,} characters of the extracted text were kept "
    "— nothing else was read or saved."
)
IMPORT_TRUNCATED_NOTICE = (
    f"That page was longer than PeerSlate reviews. The first "
    f"{MAX_SOURCE_TEXT_UNITS:,} characters of the extracted text were kept "
    "— nothing else was read or saved."
)

CLARIFICATION_TOO_LONG_MESSAGE = (
    f"That clarification is longer than {MAX_CLARIFICATION_UNITS:,} characters. "
    "Shorten it and try again — your text is still below."
)
RESPONSE_TOO_LONG_MESSAGE = (
    f"That response is longer than {MAX_RESPONSE_TEXT_UNITS:,} characters. "
    "Shorten it and try again — your text is still below."
)

# ---------------------------------------------------------------------------
# Slice OS-3 — image 09-b's analysis-failure card, word for word this time.
#
# Slice OS-2 reproduced image 09-b's GRAMMAR for two steps that were not the
# evidence analysis, because naming a step that never ran would have been a
# lie. This slice runs the step the card was drawn for, so the card is now
# quoted exactly as the locked authority draws it (handoff section 14-M11:
# trust-critical sentences are reproduced, never paraphrased).
# ---------------------------------------------------------------------------
ANALYSIS_FAILURE_HEADING = "We couldn't complete the evidence analysis."
ANALYSIS_FAILURE_MESSAGE = "Your confirmed source and requirements are unchanged."
ANALYSIS_FAILURE_TRUTH = "Results not generated • Nothing was saved."

# ---------------------------------------------------------------------------
# THE COMPOSITION TEMPLATES.
#
# These are the third and last author on the Alignment screen. The other two
# are the employer (their own confirmed wording) and the member (their own
# evidence and their own responses). The MODEL IS NOT AN AUTHOR HERE: it
# returns citations, and the sentences below are what turn those citations
# into English. See the composition-boundary block in
# services/opportunity_analysis_service.py for why the room is built this way
# rather than filtering a verdict out of model prose.
#
# Every string below is therefore reviewed copy, and
# tests/test_opportunity_slate_ai.py asserts statically that not one of them
# carries a score, a percentage, a ranking, a recommendation, or a judgement
# about a person — including through OS-2's own prose scan, which has no
# false-positive risk when it is pointed at a fixed set of constants instead
# of at an input.
#
# The employer's and the member's own words are interpolated into them. Those
# are deliberately NOT scanned: censoring an employer's requirement or a
# member's evidence would be the wrong failure, which is the same reasoning
# finding F3 used to keep `quote` and `text` out of the OS-2 scan.
# ---------------------------------------------------------------------------
ALIGNMENT_STATUS_LABELS = {
    "supported": "Supported",
    "partially_supported": "Partially supported",
    "not_enough_information": "Not enough information",
}
# Three named states, in the order image 04 prints them in its count
# summaries. An order of PRESENTATION, never a ranking: nothing in this module
# sums, averages, weights, or compares them.
ALIGNMENT_STATUS_ORDER = (
    "supported",
    "partially_supported",
    "not_enough_information",
)

# Terse on purpose. Image 04 holds its explanations to one or two short
# lines inside a 43%-wide cell, and the longer wording ran every supported
# row onto a second line for no extra meaning.
EXPLANATION_SUPPORTED = "Your evidence covers every part of this qualification."
EXPLANATION_PARTIAL_COVERED = "Your evidence covers {covered}."
# Finding F5's fallback. Used when every cited fragment was too short to read
# back as a phrase — the state is still true and still partial, and naming it
# plainly beats printing "Your evidence covers ." at the member.
EXPLANATION_PARTIAL_UNNAMED = "Your evidence covers part of this qualification."
EXPLANATION_PARTIAL_REMAINDER = " Not established: {remainder}."
EXPLANATION_NOT_ENOUGH = "No authorized evidence was matched to this."
EXPLANATION_NO_EVIDENCE = (
    "There was no authorized evidence to compare this against."
)

RAIL_SUPPORTS_HEADING_SUPPORTED = "Why this evidence supports the qualification"
RAIL_SUPPORTS_HEADING_PARTIAL = (
    "Why this evidence supports part of the qualification"
)
RAIL_SUPPORTS_LINE = "{title} · Version {version} is cited for {covered}."
# Finding F5's fallback, for the same reason and in the same grammar.
RAIL_SUPPORTS_LINE_UNNAMED = (
    "{title} · Version {version} is cited for part of this qualification."
)
RAIL_UNESTABLISHED_HEADING = "What remains unestablished"
RAIL_UNESTABLISHED_LINE = (
    "{remainder} — not established by the evidence you authorized."
)
RAIL_UNESTABLISHED_NONE = (
    "Every part of this qualification is covered by the evidence you "
    "authorized."
)
RAIL_NOT_ENOUGH_LINE = (
    "Nothing you authorized was matched to these words. That is a gap in the "
    "evidence PeerSlate could read, not a statement about you."
)

# The footer truth line. Image 04's own sentence describes what SAVING does,
# and saving is slice OS-4 — so the sentence that would be a promise here is
# replaced by one that is true here, in the same grammar (handoff section
# 14-M11: the trust-critical sentences are quoted, the rest follow the
# images' meaning). The first clause is image 04's, verbatim.
#
# Independent review finding F9. These three constants had ZERO references:
# the sentences shipped hardcoded in _alignment.html, and the old single
# ALIGNMENT_FOOTER_TRUTH ("Nothing is saved yet.") had already drifted away
# from the two labels that actually render. A static guard that scans
# ALIGNMENT_* was therefore partly pointed at strings no member ever saw.
# They are now the only source of those sentences, carried to the template on
# the room dict the way demo_label and demo_note already were, and
# CompositionTemplateTests asserts that every one of them still reaches the
# page.
ALIGNMENT_FOOTER_TRUTH_PRIVATE = "Session private · Nothing is saved yet"
ALIGNMENT_FOOTER_TRUTH_PUBLIC = "Public session · Nothing is stored"
ALIGNMENT_FOOTER_DETAIL = (
    "This analysis is session-private. Nothing here has been published, "
    "shared, sent to an employer, or used to alter your evidence."
)
ALIGNMENT_SAVE_NOTE = (
    "Saving this analysis privately arrives in a later update. Nothing is "
    "waiting behind this button, and nothing has been saved."
)

# The demo evidence label. Handoff section 18 safeguard 5: anonymous mode
# never claims the demo library is the visitor's own.
DEMO_EVIDENCE_LABEL = f"Demo evidence · {DEMO_PERSONA_NAME}"
DEMO_EVIDENCE_NOTE = (
    f"This preview compares the role against a sample library belonging to "
    f"{DEMO_PERSONA_NAME}, a fictional person. None of it is yours, and none "
    "of it is stored."
)


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


@opportunity_slate.before_request
def _allow_bounded_document_upload():
    """Override the small global form limit for the one route that accepts
    a file (the ``owner_routes._allow_bounded_voice_upload`` idiom).

    Every other route on this blueprint — including ``source/import``, whose
    body is a short URL string — stays under the app-wide 2 MB
    ``MAX_CONTENT_LENGTH``.
    """
    if request.endpoint == "opportunity_slate.upload_source":
        # Multipart framing (boundary markers, per-part headers) adds a
        # small amount beyond the enforced file cap.
        request.max_content_length = MAX_UPLOAD_BYTES + (64 * 1024)


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


def _notice_serializer():
    """The short-lived truncation-notice token serializer, built once per
    app. Same signing key as the anonymous context serializer, its own
    salt — a token minted for one purpose can never be replayed as the
    other."""
    serializer = current_app.extensions.get(_NOTICE_SERIALIZER_EXTENSION_KEY)
    if serializer is None:
        serializer = URLSafeTimedSerializer(
            current_app.config["PEERSLATE_OPPSLATE_CONTEXT_SIGNING_KEY"],
            salt=NOTICE_TOKEN_SALT,
        )
        current_app.extensions[_NOTICE_SERIALIZER_EXTENSION_KEY] = serializer
    return serializer


def _mint_notice_token(kind):
    return _notice_serializer().dumps(kind)


def _read_notice_token(token):
    """Return the notice kind, or ``None`` for anything missing, tampered,
    expired past :data:`NOTICE_TOKEN_MAX_AGE_SECONDS`, or simply not one of
    the two known kinds — never an error, since a stale or absent notice is
    an entirely ordinary page load, not a failure."""
    if not token:
        return None
    try:
        kind = _notice_serializer().loads(token, max_age=NOTICE_TOKEN_MAX_AGE_SECONDS)
    except BadData:
        return None
    return kind if kind in {"upload_truncated", "import_truncated"} else None


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


def _split_runs(text, marks):
    """Split one line into plain and concern-highlighted runs.

    ``marks`` is a list of ``(quote, concern_key)``. Matching is plain
    substring matching against the text being displayed, so a highlight can
    only ever appear where the exact quoted characters really are. A concern
    whose wording is no longer on screen — because the member already
    corrected it, or replaced the source — simply does not highlight, rather
    than highlighting the wrong phrase (image 02's connector is implemented as
    adjacency and a shared accent, per handoff section 14-M10).
    """
    runs = [{"text": text, "concern_key": None}]
    for quote, concern_key in marks:
        if not quote:
            continue
        rebuilt = []
        for run in runs:
            if run["concern_key"] is not None or quote not in run["text"]:
                rebuilt.append(run)
                continue
            head, _, tail = run["text"].partition(quote)
            if head:
                rebuilt.append({"text": head, "concern_key": None})
            rebuilt.append({"text": quote, "concern_key": concern_key})
            if tail:
                rebuilt.append({"text": tail, "concern_key": None})
        runs = rebuilt
    return [run for run in runs if run["text"]]


def _normalize_display_blocks(text, marks=()):
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

    # Concern highlights are attached last, so the layout above stays exactly
    # the deterministic, presentation-only pass slice OS-1 shipped. A heading
    # is never highlighted: it is a label PeerSlate promoted, not employer
    # prose the member would correct.
    marks = list(marks)
    for block in blocks:
        if block["kind"] == "list":
            block["item_runs"] = [
                _split_runs(item, marks) for item in block["items"]
            ]
        elif block["kind"] == "paragraph":
            block["runs"] = _split_runs(block["text"], marks)
        else:
            block["runs"] = [{"text": block["text"], "concern_key": None}]
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
        # Every state below is None on a plain page load and is filled in
        # only by the room builder that owns it. The stage rail and the
        # read-only correction rail are deliberately NOT in here: both are
        # client states that exist only while a request is genuinely in
        # flight, so a server-rendered page can never show a stage that is
        # not happening.
        "requirements": None,
        "alignment": None,
        "max_source_units": MAX_SOURCE_TEXT_UNITS,
        "max_response_units": MAX_RESPONSE_TEXT_UNITS,
        # Slice OS-2 independent review, finding F5. The intake textarea's
        # maxlength is the STORAGE cap in both modes, but the anonymous AI
        # cap is far tighter (8,000 vs 20,000), so a visitor could paste and
        # confirm 20,000 characters and first learn of the real limit when
        # they pressed the AI button — a refusal by surprise, after the work.
        # The server cap is correct and unchanged; what was missing was
        # telling the visitor about it up front. This is that number.
        #
        # maxlength deliberately stays at the storage cap even in public
        # mode: lowering it would silently TRUNCATE a long paste, losing the
        # visitor's employer text without a word. Disclosing the limit and
        # preserving the text is the honest pair.
        "public_ai_source_units": MAX_PUBLIC_AI_SOURCE_UNITS,
        "back_url": "/",
        "room_url": url_for("opportunity_slate.room"),
        "source_url": url_for("opportunity_slate.set_source"),
        "upload_url": url_for("opportunity_slate.upload_source"),
        "import_url": url_for("opportunity_slate.import_source"),
        "correct_url": url_for("opportunity_slate.correct_source"),
        "confirm_url": url_for("opportunity_slate.confirm_source"),
        "delete_url": url_for("opportunity_slate.delete_source"),
        "public_session_url": url_for("opportunity_slate.public_session"),
        "public_propose_url": url_for("opportunity_slate.public_propose"),
        "review_url": url_for("opportunity_slate.review_source_wording"),
        "resolve_url": url_for("opportunity_slate.resolve_source_concern"),
        "interpret_url": url_for("opportunity_slate.interpret_requirements"),
        "statement_url": url_for("opportunity_slate.correct_statement"),
        "confirm_requirements_url": url_for(
            "opportunity_slate.confirm_requirements"
        ),
        "role_step_url": url_for("opportunity_slate.room", step=STEP_ROLE),
        "replace_step_url": url_for("opportunity_slate.room", step=STEP_REPLACE),
        "review_step_url": url_for("opportunity_slate.room", step=STEP_REVIEW),
        "requirements_step_url": url_for(
            "opportunity_slate.room", step=STEP_REQUIREMENTS
        ),
        "alignment_step_url": url_for("opportunity_slate.room", step=STEP_ALIGNMENT),
        "analysis_url": url_for("opportunity_slate.run_analysis"),
        "response_url": url_for("opportunity_slate.save_response"),
        "max_clarification_units": MAX_CLARIFICATION_UNITS,
        "statement_class_options": [
            {"value": name, "label": STATEMENT_CLASS_LABELS[name]}
            for name in STATEMENT_GROUP_ORDER
        ],
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
            # Independent review (non-blocking, fixed now): the paste,
            # upload, and import forms are three separate submissions of
            # three separate intents, not three ways to re-send the same
            # one. A single shared key meant a failed-then-retried paste
            # and a subsequent upload on the same page load shared the
            # same idempotency ledger row — the ledger's unique key is
            # (owner_profile_id, idempotency_key) — so each form now gets
            # its own, freshly minted every time this room is rendered.
            "upload_idempotency_key": str(uuid4()),
            "import_idempotency_key": str(uuid4()),
            "source": None,
        }
    )
    return room


def _concern_marks(concerns):
    """The ``(quote, key)`` pairs the source document may highlight.

    Only pending concerns highlight. Once the member has applied or dismissed
    one, the highlight is gone: an applied concern's wording is no longer on
    screen, and a dismissed one is a decision the member already made.
    """
    return [
        (concern["quote"], concern["key"])
        for concern in concerns
        if concern["resolution"] == "pending"
    ]


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
    review=None,
    concerns=(),
    notice=None,
):
    display_text = corrected_text or original_text
    concerns = list(concerns)
    pending = [item for item in concerns if item["resolution"] == "pending"]
    room = _base_room(mode, step=STEP_REVIEW, error=error)
    room.update(
        {
            "state_title_lead": "Review",
            "state_title_rest": "Source",
            "checkpoint_label": "Checkpoint 1 of 2",
            # Slice OS-6. Set only by the room() GET handler immediately
            # after a successful upload/import redirect whose extraction was
            # truncated (a one-time, ephemeral, query-string-driven notice —
            # nothing about the truncation fact is stored, exactly like the
            # ``step`` query hint already is).
            "notice": notice,
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
                "blocks": _normalize_display_blocks(
                    display_text, _concern_marks(concerns)
                ),
                "original_blocks": _normalize_display_blocks(original_text),
                "is_confirmed": bool(is_confirmed),
                "editing": bool(editing),
                "editor_text": editor_text if editor_text is not None else display_text,
                # Slice OS-2. ``review`` is None until AI step 1 has run for
                # this source version. That is deliberately a different fact
                # from "it ran and found nothing", which is a review with an
                # empty concern list, and the screen says the two differently.
                "review": review,
                "concerns": concerns,
                "pending_concerns": pending,
                "pending_concern_count": len(pending),
                "concern_count": len(concerns),
            },
        }
    )
    return room


def _concerns_from_views(concerns):
    return [
        {
            "key": concern.concern_key,
            "quote": concern.quoted_text,
            "reason": concern.concern_reason,
            "resolution": concern.member_resolution,
            "corrected_text": concern.member_corrected_text,
            "version_token": concern.version_token,
        }
        for concern in concerns
    ]


def _review_summary(model_name, prompt_contract_version, concern_count):
    """What the screen may say about the proposal that produced these cards.

    The model and the prompt-contract version travel with the proposal
    everywhere (handoff section 10) so a member — and a reviewer — can always
    see which contract produced a given reading.
    """
    return {
        "model": model_name,
        "prompt_contract": prompt_contract_version,
        "concern_count": concern_count,
    }


def _statements_from_views(statements):
    return [
        {
            "key": statement.statement_key,
            "ordinal": statement.ordinal,
            "text": statement.employer_text,
            "proposed_class": statement.proposed_class,
            "proposed_class_label": STATEMENT_CLASS_LABELS[statement.proposed_class],
            "effective_class": statement.effective_class,
            "class_label": STATEMENT_CLASS_LABELS[statement.effective_class],
            "explanation": statement.proposed_explanation,
            "paths": [
                {"label": path["label"], "clauses": list(path["clauses"])}
                for path in statement.proposed_paths
            ],
            "member_class": statement.member_class,
            "member_clarification": statement.member_clarification,
            "is_reclassified": statement.is_reclassified,
            "has_member_input": statement.has_member_input,
            "version_token": statement.version_token,
        }
        for statement in statements
    ]


def _group_statements(statements):
    """Four separate groups, always, in image 03's order.

    A group with no statements still renders, with a count of zero and an
    honest empty line. Merging Responsibilities and Informational statements —
    which image 05 does — is prohibited (locked rule, handoff section 14-M14),
    and silently dropping an empty group would let the screen imply the
    employer wrote something they did not.
    """
    groups = []
    opened = False
    for name in STATEMENT_GROUP_ORDER:
        members = [
            statement
            for statement in statements
            if statement["effective_class"] == name
        ]
        # The first group that actually has statements opens. Opening an
        # empty first group would greet the member with a card that says
        # nothing while the statements sit collapsed below it.
        is_open = bool(members) and not opened
        opened = opened or is_open
        groups.append(
            {
                "class": name,
                "label": STATEMENT_GROUP_LABELS[name],
                "count": len(members),
                "statements": members,
                "is_open": is_open,
            }
        )
    return groups


def _requirements_room(
    mode,
    *,
    source_key,
    session_key,
    source_version_token,
    session_version_token,
    version_number,
    is_source_confirmed,
    requirement_set=None,
    statements=(),
    selected_key=None,
    error=None,
):
    """Review Requirements — image 03, and image 08's processing variant."""
    statements = list(statements)
    groups = _group_statements(statements)
    if statements:
        keys = [statement["key"] for statement in statements]
        if selected_key not in keys:
            # Default to the first statement in DISPLAY order, not source
            # order. The screen opens the first non-empty group, so picking
            # the first statement of that group is the one the member is
            # actually looking at — image 03 shows the selected row inside the
            # open Required qualifications card, not a row two cards below.
            selected_key = next(
                (
                    group["statements"][0]["key"]
                    for group in groups
                    if group["statements"]
                ),
                keys[0],
            )
    else:
        selected_key = None

    room = _base_room(mode, step=STEP_REQUIREMENTS, error=error)
    room.update(
        {
            "state_title_lead": "Review",
            "state_title_rest": "Requirements",
            "checkpoint_label": "Checkpoint 2 of 2",
            "source_text": "",
            "is_replace": False,
            "has_source": True,
            "idempotency_key": str(uuid4()),
            "source": None,
            "requirements": {
                "source_key": source_key,
                "session_key": session_key,
                "source_version_token": source_version_token,
                "session_version_token": session_version_token,
                "version_number": version_number,
                "version_label": f"Source Version {version_number}",
                "is_source_confirmed": bool(is_source_confirmed),
                "set": requirement_set,
                "statements": statements,
                "groups": groups,
                "selected_key": selected_key,
                "has_statements": bool(statements),
            },
        }
    )
    return room


# ---------------------------------------------------------------------------
# Slice OS-3 — composing the Alignment screen's sentences.
#
# Everything below turns validated citations plus the employer's and the
# member's own words into English. No model output passes through it: a
# `covered_text` is a verbatim span of the employer's confirmed clause and an
# `excerpt` is a verbatim span of the member's own evidence, both already
# resolved against the stored text by the analysis service.
# ---------------------------------------------------------------------------

MAX_LISTED_FRAGMENTS = 3

# Independent review finding F5. A covered fragment is a SUB-SPAN of the
# employer's clause chosen by the citation, so it can legitimately stop before
# the clause does — and run together with PeerSlate's own connecting words it
# printed as broken English on the primary member-facing surface:
#
#   Your evidence covers Bachelor's degree in, 3+ years of and a Master's
#   degree, and 1 more.
#
# Three composition changes, and NOT a change to what a citation may claim:
# the fragment is still a verbatim span of the employer's confirmed wording,
# and the coverage rule that derives the status is untouched.
#
#   1. Each phrase is QUOTED, so a reader can see where PeerSlate's sentence
#      stops and the employer's wording starts. That is the same grammar the
#      evidence rail already uses for the member's own excerpt.
#   2. A fragment that is nothing but a function word ("in", "of", "and") is
#      dropped: it carries no requirement, and a citation is not made less
#      true by PeerSlate declining to read a preposition back to the member.
#      Deliberately NOT a character minimum — "SQL", "PhD" and "AWS" are real
#      three-letter qualifications and a length rule would delete them.
#   3. When nothing survives, the sentence falls back to naming the state
#      rather than printing an empty list.
#
# Typographic quotes deliberately: a straight double quote is escaped to
# &#34; by Jinja on the way into the page.
FUNCTION_WORD_FRAGMENTS = frozenset(
    {
        "a", "an", "and", "as", "at", "by", "for", "from", "in", "into",
        "of", "on", "or", "the", "to", "with", "within",
    }
)
OPEN_QUOTE = "“"
CLOSE_QUOTE = "”"


def _join_fragments(fragments, limit=MAX_LISTED_FRAGMENTS, excerpts=False):
    """Read a list of employer phrases as a sentence, quoted and bounded.

    A qualification can carry eight clauses, and printing all eight inside a
    table cell turns the row into a paragraph. Beyond the limit the sentence
    says how many more there are rather than truncating one mid-phrase.

    ``excerpts`` marks the covered FRAGMENTS, which are sub-spans a citation
    chose. It is left False for unestablished CLAUSES, which are whole
    confirmed statements: dropping one of those would hide a requirement from
    the member.
    """
    items = []
    seen = set()
    for fragment in fragments:
        cleaned = (fragment or "").strip().strip(",;:")
        if not cleaned:
            continue
        if excerpts and cleaned.lower() in FUNCTION_WORD_FRAGMENTS:
            continue
        if cleaned.lower() in seen:
            continue
        seen.add(cleaned.lower())
        items.append(f"{OPEN_QUOTE}{cleaned}{CLOSE_QUOTE}")
    if not items:
        return ""
    shown = items[:limit]
    remaining = len(items) - len(shown)
    if len(shown) == 1:
        joined = shown[0]
    else:
        joined = ", ".join(shown[:-1]) + " and " + shown[-1]
    if remaining:
        joined += f", and {remaining} more"
    return joined


def _alignment_explanation(result, evidence_considered):
    """The sentence under the employer's wording in the table (image 04)."""
    status = result["status"]
    if status == "supported":
        return EXPLANATION_SUPPORTED
    if status == "not_enough_information":
        if not evidence_considered:
            return EXPLANATION_NO_EVIDENCE
        return EXPLANATION_NOT_ENOUGH
    covered = _join_fragments(result["covered_fragments"], excerpts=True)
    sentence = (
        EXPLANATION_PARTIAL_COVERED.format(covered=covered)
        if covered
        else EXPLANATION_PARTIAL_UNNAMED
    )
    remainder = _join_fragments(result["unestablished"])
    if remainder:
        sentence += EXPLANATION_PARTIAL_REMAINDER.format(remainder=remainder)
    return sentence


def _alignment_detail(result, evidence_considered):
    """The evidence rail's composed blocks for one selected qualification."""
    status = result["status"]
    supports_lines = []
    for reference in result["evidence_references"]:
        covered = _join_fragments(
            [item["covered_text"] for item in result["citations"]
             if item["evidence_key"] == reference["evidence_key"]
             and item["evidence_version"] == reference["evidence_version"]],
            excerpts=True,
        )
        template = RAIL_SUPPORTS_LINE if covered else RAIL_SUPPORTS_LINE_UNNAMED
        supports_lines.append(
            template.format(
                title=reference["evidence_title"],
                version=reference["evidence_version"],
                covered=covered,
            )
        )
    if status == "not_enough_information":
        supports_heading = None
        if not evidence_considered:
            unestablished_line = EXPLANATION_NO_EVIDENCE
        else:
            unestablished_line = RAIL_NOT_ENOUGH_LINE
    else:
        supports_heading = (
            RAIL_SUPPORTS_HEADING_SUPPORTED
            if status == "supported"
            else RAIL_SUPPORTS_HEADING_PARTIAL
        )
        unestablished_line = (
            RAIL_UNESTABLISHED_LINE.format(
                remainder=_join_fragments(result["unestablished"])
            )
            if result["unestablished"]
            else RAIL_UNESTABLISHED_NONE
        )
    return {
        "supports_heading": supports_heading,
        "supports_lines": supports_lines,
        "unestablished_heading": RAIL_UNESTABLISHED_HEADING,
        "unestablished_line": unestablished_line,
    }


def _qualifications_for_analysis(statements):
    """Build the grounding vocabulary AI step 3 is allowed to cite.

    Only the two qualification classes reach it (handoff: the locked
    accounting counts Required and Preferred, and every statement handed to a
    model is one a member will read a result about). A statement whose
    confirmed structure carries no clause is skipped rather than sent with an
    empty vocabulary, because a citation would have nothing to attach to.
    """
    qualifications = []
    for statement in statements:
        if statement["effective_class"] not in ANALYSED_CLASSES:
            continue
        clauses, membership = build_clause_vocabulary(statement["paths"])
        if not clauses:
            continue
        qualifications.append(
            {
                "ordinal": len(qualifications) + 1,
                "statement_key": statement["key"],
                "employer_text": statement["text"],
                "clauses": clauses,
                "paths": membership,
            }
        )
    return qualifications


def _demo_evidence_allowlist(limit=MAX_PUBLIC_EVIDENCE_ITEMS):
    """The anonymous grounding allowlist (handoff section 18).

    Reuses Workshop's own demo library — the established public-preview
    fixture pattern — rather than inventing a second one. It is a module-level
    constant belonging to a named fictional person, it imports no database,
    and every surface that shows it says whose it is.
    """
    items = []
    for item in WORKSHOP_DEMO_ITEMS:
        if item["status"] != "confirmed":
            continue
        items.append(
            {
                "id": f"e{len(items) + 1}",
                "evidence_key": item["item_key"],
                "title": item["title"],
                "version": item["current_version"],
                "body": item["wording"],
            }
        )
        if len(items) >= limit:
            break
    return items


def _evidence_allowlist(views):
    """Map the member's own confirmed evidence into the grounding vocabulary.

    The opaque short ids (``e1``…) are what the prompt sees. The real keys
    never leave the server, so a reply cannot name a record it was not given
    and a leaked prompt carries no addressable identifier.
    """
    items = []
    for index, view in enumerate(views, start=1):
        items.append(
            {
                "id": f"e{index}",
                "evidence_key": view.evidence_key,
                "title": view.title,
                "version": view.version,
                "body": view.body,
            }
        )
    return items


def _citations_for_storage(result, evidence_by_id):
    """Resolve the analysis service's citations onto real evidence records."""
    citations = []
    for citation in result["citations"]:
        item = evidence_by_id[citation["evidence_id"]]
        citations.append(
            {
                "clause_ordinal": citation["clause_ordinal"],
                "covered_text": citation["covered_text"],
                "evidence_kind": "knowledge_item",
                "evidence_key": item["evidence_key"],
                "evidence_version": item["version"],
                "evidence_title": item["title"],
                "excerpt": citation["excerpt"],
            }
        )
    return citations


def _derive_from_stored(statement, citations):
    """Re-derive one qualification's result from its stored citations.

    The citations are the fact; the status, the covered fragments and the
    remainder are all consequences of them. Re-deriving on read rather than
    trusting a stored sentence keeps ONE derivation path for the write and the
    read, so a correction to the rule cannot leave old rows describing
    themselves by the old one. (``derived_status`` is still stored: OS-4's
    saved snapshot needs it, and the database CHECK that pairs it with the
    citation count is a real guard.)
    """
    clauses, membership = build_clause_vocabulary(statement["paths"])
    resolved = []
    for citation in citations:
        index = citation["clause_ordinal"] - 1
        if not 0 <= index < len(clauses):
            continue
        spans = locate_spans(clauses[index], citation["covered_text"])
        if not spans:
            continue
        start, length = spans[0]
        resolved.append(
            {
                "clause_ordinal": citation["clause_ordinal"],
                "covered_text": citation["covered_text"],
                "covered_start": start,
                "covered_length": length,
                "evidence_id": (
                    f"{citation['evidence_key']}:{citation['evidence_version']}"
                ),
                "excerpt": citation["excerpt"],
            }
        )
    derived = derive_alignment(
        {"clauses": clauses, "paths": membership}, resolved
    )
    derived["citations"] = citations
    references = []
    seen = set()
    for citation in citations:
        key = (citation["evidence_key"], citation["evidence_version"])
        if key in seen:
            continue
        seen.add(key)
        references.append(
            {
                "evidence_key": citation["evidence_key"],
                "evidence_version": citation["evidence_version"],
                "evidence_title": citation["evidence_title"],
                "excerpt": citation["excerpt"],
            }
        )
    derived["evidence_references"] = references
    return derived


def _alignment_room(
    mode,
    *,
    version_number,
    statements,
    results,
    responses,
    evidence_choices,
    analysis,
    is_demo_evidence,
    selected_key=None,
    error=None,
):
    """The Alignment workbench — image 04, the exact geometry authority.

    Four SEPARATE cards, never merged (locked rule; handoff section 14-M14):
    Required qualifications and Preferred qualifications carry the alignment
    table and the count summaries, and Responsibilities and Informational
    statements carry the employer's wording with NO status at all, because
    they are not qualifications and PeerSlate has not compared them against
    anything. Saying otherwise on a screen whose whole subject is evidence
    would be the plainest kind of untruth available here.
    """
    statements = list(statements)
    evidence_considered = analysis["evidence_considered_count"] if analysis else 0

    prepared = []
    for statement in statements:
        entry = dict(statement)
        result = results.get(statement["key"])
        entry["is_qualification"] = statement["effective_class"] in ANALYSED_CLASSES
        entry["result"] = result
        if result:
            entry["status"] = result["status"]
            entry["status_label"] = ALIGNMENT_STATUS_LABELS[result["status"]]
            entry["explanation"] = _alignment_explanation(result, evidence_considered)
            entry["evidence_references"] = result["evidence_references"]
            entry["detail"] = _alignment_detail(result, evidence_considered)
        else:
            entry["status"] = None
            entry["status_label"] = None
            entry["explanation"] = None
            entry["evidence_references"] = []
            entry["detail"] = None
        entry["response"] = responses.get(statement["key"])
        prepared.append(entry)

    groups = []
    summaries = []
    opened = False
    for name in STATEMENT_GROUP_ORDER:
        members = [item for item in prepared if item["effective_class"] == name]
        is_qualification = name in ANALYSED_CLASSES
        # Image 04 opens the two qualification cards and leaves
        # Responsibilities and Informational statements collapsed. The first
        # non-empty qualification card opens; a card with nothing in it never
        # greets the member with an empty table.
        is_open = is_qualification and bool(members) and not opened
        opened = opened or is_open
        groups.append(
            {
                "class": name,
                "label": STATEMENT_GROUP_LABELS[name],
                "count": len(members),
                "statements": members,
                "is_open": is_open,
                "is_qualification": is_qualification,
            }
        )
        if is_qualification:
            counts = {status: 0 for status in ALIGNMENT_STATUS_ORDER}
            for item in members:
                if item["status"]:
                    counts[item["status"]] += 1
            summaries.append(
                {
                    "class": name,
                    "label": STATEMENT_GROUP_LABELS[name],
                    "count": len(members),
                    # Per-status counts only. Handoff section 1 and the locked
                    # rules: no overall score, percentage, recommendation,
                    # employer prediction, or traffic-light verdict at any
                    # layer. Three independent counts is the whole accounting
                    # image 04 performs, and this is where it is performed.
                    "counts": [
                        {
                            "status": status,
                            "label": ALIGNMENT_STATUS_LABELS[status],
                            "value": counts[status],
                        }
                        for status in ALIGNMENT_STATUS_ORDER
                    ],
                }
            )

    qualifications = [item for item in prepared if item["is_qualification"]]
    keys = [item["key"] for item in qualifications]
    if keys and selected_key not in keys:
        selected_key = next(
            (
                group["statements"][0]["key"]
                for group in groups
                if group["is_qualification"] and group["statements"]
            ),
            keys[0],
        )
    elif not keys:
        selected_key = None

    room = _base_room(mode, step=STEP_ALIGNMENT, error=error)
    room.update(
        {
            "state_title_lead": "Alignment",
            "state_title_rest": "Explore alignment",
            "checkpoint_label": None,
            "source_text": "",
            "is_replace": False,
            "has_source": True,
            "idempotency_key": str(uuid4()),
            "source": None,
            "alignment": {
                "version_label": f"Source Version {version_number}",
                "groups": groups,
                "summaries": summaries,
                "statements": prepared,
                "qualifications": qualifications,
                "selected_key": selected_key,
                "selected": next(
                    (item for item in qualifications if item["key"] == selected_key),
                    None,
                ),
                "has_qualifications": bool(qualifications),
                "has_analysis": analysis is not None,
                "analysis": analysis,
                "evidence_choices": evidence_choices,
                "evidence_considered": evidence_considered,
                "is_demo_evidence": bool(is_demo_evidence),
                "demo_label": DEMO_EVIDENCE_LABEL,
                "demo_note": DEMO_EVIDENCE_NOTE,
                # Finding F9: the footer's reviewed sentences, carried from
                # the constants above rather than retyped in the template.
                "footer_truth": (
                    ALIGNMENT_FOOTER_TRUTH_PUBLIC
                    if mode == "public"
                    else ALIGNMENT_FOOTER_TRUTH_PRIVATE
                ),
                "footer_detail": ALIGNMENT_FOOTER_DETAIL,
                "save_note": ALIGNMENT_SAVE_NOTE,
            },
        }
    )
    return room


def _requirements_room_from_views(
    working, requirement_set=None, mode="member", **overrides
):
    statements = (
        _statements_from_views(requirement_set.statements) if requirement_set else []
    )
    return _requirements_room(
        mode,
        source_key=working.source_key,
        session_key=working.working_session_key,
        source_version_token=working.source_version_token,
        session_version_token=working.session_version_token,
        version_number=working.version_number,
        is_source_confirmed=working.is_confirmed,
        requirement_set=(
            {
                "set_key": requirement_set.requirement_set_key,
                "version_token": requirement_set.version_token,
                "version_number": requirement_set.version_number,
                "model": requirement_set.model_name,
                "prompt_contract": requirement_set.prompt_contract_version,
                "is_confirmed": requirement_set.is_confirmed,
                "counts": requirement_set.counts_by_class(),
            }
            if requirement_set
            else None
        ),
        statements=statements,
        **overrides,
    )


def _alignment_room_from_views(
    working,
    requirement_set,
    analysis,
    responses,
    evidence_views,
    mode="member",
    **overrides,
):
    statements = _statements_from_views(requirement_set.statements)
    citations_by_key = {}
    if analysis is not None:
        for statement in analysis.statements:
            citations_by_key[statement.statement_key] = [
                {
                    "clause_ordinal": citation.clause_ordinal,
                    "covered_text": citation.covered_text,
                    "evidence_kind": citation.evidence_kind,
                    "evidence_key": citation.evidence_key,
                    "evidence_version": citation.evidence_version,
                    "evidence_title": citation.evidence_title,
                    "excerpt": citation.excerpt,
                }
                for citation in statement.citations
            ]
    results = {}
    for statement in statements:
        if statement["key"] in citations_by_key:
            results[statement["key"]] = _derive_from_stored(
                statement, citations_by_key[statement["key"]]
            )
    return _alignment_room(
        mode,
        version_number=working.version_number,
        statements=statements,
        results=results,
        responses={
            key: {
                "kind": view.response_kind,
                "text": view.response_text,
                "evidence_title": view.connected_evidence_title,
                "evidence_version": view.connected_evidence_version,
                "authored_via": view.authored_via,
            }
            for key, view in (responses or {}).items()
        },
        evidence_choices=[
            {
                "key": view.evidence_key,
                "title": view.title,
                "version": view.version,
            }
            for view in evidence_views
        ],
        analysis=(
            {
                "model": analysis.model_name,
                "prompt_contract": analysis.prompt_contract_version,
                "evidence_considered_count": analysis.evidence_considered_count,
                "qualification_count": analysis.qualification_count,
            }
            if analysis is not None
            else None
        ),
        is_demo_evidence=False,
        **overrides,
    )


def _alignment_room_from_context(context, mode="public", **overrides):
    statements = _public_statements(context)
    stored = context.get("alignment")
    results = {}
    if stored:
        by_key = {}
        for entry in stored["results"]:
            by_key[entry["k"]] = [
                {
                    "clause_ordinal": citation["cl"],
                    "covered_text": citation["t"],
                    "evidence_kind": "knowledge_item",
                    "evidence_key": citation["ek"],
                    "evidence_version": citation["ev"],
                    "evidence_title": citation["et"],
                    "excerpt": citation["x"],
                }
                for citation in entry["c"]
            ]
        for statement in statements:
            if statement["key"] in by_key:
                results[statement["key"]] = _derive_from_stored(
                    statement, by_key[statement["key"]]
                )
    demo = _demo_evidence_allowlist()
    return _alignment_room(
        mode,
        version_number=context["version"],
        statements=statements,
        results=results,
        responses={
            key: {
                "kind": entry["k"],
                "text": entry.get("t"),
                "evidence_title": entry.get("et"),
                "evidence_version": entry.get("ev"),
                "authored_via": "typed",
            }
            for key, entry in (context.get("responses") or {}).items()
        },
        evidence_choices=[
            {"key": item["evidence_key"], "title": item["title"], "version": item["version"]}
            for item in demo
        ],
        analysis=(
            {
                "model": stored["model"],
                "prompt_contract": stored["contract"],
                "evidence_considered_count": stored["evidence"],
                "qualification_count": len(stored["results"]),
            }
            if stored
            else None
        ),
        is_demo_evidence=True,
        **overrides,
    )


def _review_room_from_view(view, mode="member", review=None, **overrides):
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
        review=(
            _review_summary(
                review.model_name,
                review.prompt_contract_version,
                review.concern_count,
            )
            if review
            else None
        ),
        concerns=_concerns_from_views(review.concerns) if review else (),
        **overrides,
    )


def _review_room_from_context(context, mode="public", **overrides):
    stored_review = context.get("review")
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
        review=(
            _review_summary(
                stored_review["model"],
                stored_review["contract"],
                len(stored_review["concerns"]),
            )
            if stored_review
            else None
        ),
        concerns=(
            [
                {
                    "key": entry["k"],
                    "quote": entry["q"],
                    "reason": entry["r"],
                    "resolution": entry["res"],
                    "corrected_text": entry.get("c"),
                    "version_token": None,
                }
                for entry in stored_review["concerns"]
            ]
            if stored_review
            else ()
        ),
        **overrides,
    )


def _public_statements(context):
    """The anonymous session's statements, in the same shape the member path
    builds from database rows, so one set of view code serves both modes."""
    stored = context.get("requirements")
    statements = []
    if not stored:
        return statements
    for entry in stored["statements"]:
        effective = entry.get("mc") or entry["pc"]
        statements.append(
            {
                "key": entry["k"],
                "ordinal": entry["o"],
                "text": entry["t"],
                "proposed_class": entry["pc"],
                "proposed_class_label": STATEMENT_CLASS_LABELS[entry["pc"]],
                "effective_class": effective,
                "class_label": STATEMENT_CLASS_LABELS[effective],
                "explanation": entry["e"],
                "paths": [
                    {"label": path["label"], "clauses": list(path["clauses"])}
                    for path in entry["p"]
                ],
                "member_class": entry.get("mc"),
                "member_clarification": entry.get("mx"),
                "is_reclassified": bool(entry.get("mc"))
                and entry.get("mc") != entry["pc"],
                "has_member_input": bool(entry.get("mc")) or bool(entry.get("mx")),
                "version_token": None,
            }
        )
    return statements


def _requirements_room_from_context(context, mode="public", **overrides):
    stored = context.get("requirements")
    statements = _public_statements(context)
    counts = {name: 0 for name in STATEMENT_GROUP_ORDER}
    for statement in statements:
        counts[statement["effective_class"]] += 1
    return _requirements_room(
        mode,
        source_key=None,
        session_key=None,
        source_version_token=None,
        session_version_token=None,
        version_number=context["version"],
        is_source_confirmed=context.get("confirmed", False),
        requirement_set=(
            {
                "set_key": None,
                "version_token": None,
                "version_number": stored["version"],
                "model": stored["model"],
                "prompt_contract": stored["contract"],
                "is_confirmed": bool(stored.get("confirmed")),
                "counts": counts,
            }
            if stored
            else None
        ),
        statements=statements,
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

    review = _load_public_review(context.get("review"))
    if review is False:
        return None
    requirements = _load_public_requirements(context.get("requirements"))
    if requirements is False:
        return None
    statement_keys = {
        entry["k"] for entry in (requirements or {}).get("statements", ())
    }
    alignment = _load_public_alignment(context.get("alignment"), statement_keys)
    if alignment is False:
        return None
    responses = _load_public_responses(context.get("responses"), statement_keys)
    if responses is False:
        return None

    return {
        "v": PUBLIC_CONTEXT_VERSION,
        "text": text,
        "corrected": corrected,
        "version": version,
        "confirmed": confirmed,
        "review": review,
        "requirements": requirements,
        "alignment": alignment,
        "responses": responses,
    }


def _load_public_alignment(stored, statement_keys):
    """Validate the AI step-3 result carried in the visitor's own token.

    The same shape discipline the database rows get, applied to the other mode
    so neither can drift into accepting something the other would refuse — and
    with the same structural rule the validator applies: there is no free-text
    field here either. Every string is a span of the employer's clause or of
    the demo evidence, and a citation naming a statement the token does not
    carry resets the session rather than rendering half a screen.
    """
    if stored is None:
        return None
    if not isinstance(stored, dict) or set(stored) != {
        "model",
        "contract",
        "evidence",
        "results",
    }:
        return False
    model = _bounded_token_text(stored["model"], 100)
    contract = _bounded_token_text(stored["contract"], 60)
    if not model or not contract:
        return False
    evidence_count = stored["evidence"]
    if (
        not isinstance(evidence_count, int)
        or isinstance(evidence_count, bool)
        or not 0 <= evidence_count <= MAX_PUBLIC_EVIDENCE_ITEMS
    ):
        return False
    entries = stored["results"]
    if (
        not isinstance(entries, list)
        or not entries
        or len(entries) > MAX_PUBLIC_ANALYSED_STATEMENTS
    ):
        return False

    results = []
    total = 0
    seen = set()
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"k", "s", "c"}:
            return False
        key = _normalize_key(entry.get("k"))
        if not key or key not in statement_keys or key in seen:
            return False
        seen.add(key)
        if entry["s"] not in ALIGNMENT_STATUS_LABELS:
            return False
        citations = entry["c"]
        if not isinstance(citations, list):
            return False
        total += len(citations)
        if total > MAX_PUBLIC_CITATIONS_TOTAL:
            return False
        if (not citations) != (entry["s"] == "not_enough_information"):
            return False
        cleaned = []
        for citation in citations:
            if not isinstance(citation, dict) or set(citation) != {
                "cl",
                "t",
                "ek",
                "ev",
                "et",
                "x",
            }:
                return False
            clause = citation["cl"]
            version = citation["ev"]
            if (
                not isinstance(clause, int)
                or isinstance(clause, bool)
                or clause < 1
                or not isinstance(version, int)
                or isinstance(version, bool)
                or version < 1
            ):
                return False
            covered = _bounded_token_text(citation["t"], 200)
            title = _bounded_token_text(citation["et"], 200)
            excerpt = _bounded_token_text(citation["x"], 400)
            evidence_key = _normalize_key(citation["ek"])
            if not covered or not title or not excerpt or not evidence_key:
                return False
            cleaned.append(
                {
                    "cl": clause,
                    "t": covered,
                    "ek": evidence_key,
                    "ev": version,
                    "et": title,
                    "x": excerpt,
                }
            )
        results.append({"k": key, "s": entry["s"], "c": cleaned})
    return {
        "model": model,
        "contract": contract,
        "evidence": evidence_count,
        "results": results,
    }


def _load_public_responses(stored, statement_keys):
    """Validate the visitor's own responses carried in their token."""
    if stored is None:
        return None
    if not isinstance(stored, dict) or len(stored) > MAX_PUBLIC_ANALYSED_STATEMENTS:
        return False
    responses = {}
    for raw_key, entry in stored.items():
        key = _normalize_key(raw_key)
        if not key or key not in statement_keys:
            return False
        if not isinstance(entry, dict) or set(entry) - {"k", "t", "ek", "ev", "et"}:
            return False
        kind = entry.get("k")
        if kind not in RESPONSE_KINDS:
            return False
        text = entry.get("t")
        if text is not None:
            text = _bounded_token_text(text, MAX_RESPONSE_TEXT_UNITS)
            if text is None:
                return False
        title = entry.get("et")
        if title is not None:
            title = _bounded_token_text(title, 200)
            if title is None:
                return False
        version = entry.get("ev")
        if version is not None and (
            not isinstance(version, int) or isinstance(version, bool) or version < 1
        ):
            return False
        evidence_key = entry.get("ek")
        if evidence_key is not None:
            evidence_key = _normalize_key(evidence_key)
            if not evidence_key:
                return False
        # The same pairing the database CHECK enforces for a member, so the
        # public boundary cannot be the lenient one.
        if kind in {"tell_more", "real_example"} and (
            not text or evidence_key or title
        ):
            return False
        if kind == "connect_evidence" and (
            text or not evidence_key or not title or not version
        ):
            return False
        if kind in {"confirm_not_have", "skip"} and (text or evidence_key or title):
            return False
        responses[key] = {
            "k": kind,
            "t": text,
            "ek": evidence_key,
            "ev": version,
            "et": title,
        }
    return responses


def _bounded_token_text(value, max_units):
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    if not cleaned or len(cleaned.encode("utf-16-le")) // 2 > max_units:
        return None
    return cleaned


def _load_public_review(stored):
    """Validate the AI step-1 proposals carried in the visitor's own token.

    ``None`` means "step 1 has not run"; ``False`` means the stored shape is
    wrong, which resets the whole session honestly rather than rendering half
    a screen. The token is server-signed, so this is not an untrusted-input
    boundary — it is the same shape discipline the database rows get, applied
    to the other mode so neither can drift into accepting something the other
    would refuse.
    """
    if stored is None:
        return None
    if not isinstance(stored, dict) or set(stored) != {"model", "contract", "concerns"}:
        return False
    model = _bounded_token_text(stored["model"], 100)
    contract = _bounded_token_text(stored["contract"], 60)
    if not model or not contract:
        return False
    entries = stored["concerns"]
    if not isinstance(entries, list) or len(entries) > 6:
        return False
    concerns = []
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) - {"k", "q", "r", "res", "c"}:
            return False
        key = _normalize_key(entry.get("k"))
        quote = _bounded_token_text(entry.get("q"), 600)
        reason = _bounded_token_text(entry.get("r"), 240)
        resolution = entry.get("res")
        corrected = entry.get("c")
        if corrected is not None:
            corrected = _bounded_token_text(corrected, MAX_SOURCE_TEXT_UNITS)
            if corrected is None:
                return False
        if (
            not key
            or not quote
            or not reason
            or resolution not in {"pending", "applied", "dismissed"}
        ):
            return False
        concerns.append(
            {"k": key, "q": quote, "r": reason, "res": resolution, "c": corrected}
        )
    return {"model": model, "contract": contract, "concerns": concerns}


def _load_public_requirements(stored):
    """Validate the AI step-2 proposals carried in the visitor's own token."""
    if stored is None:
        return None
    if not isinstance(stored, dict) or set(stored) != {
        "model",
        "contract",
        "version",
        "source_version",
        "confirmed",
        "statements",
    }:
        return False
    model = _bounded_token_text(stored["model"], 100)
    contract = _bounded_token_text(stored["contract"], 60)
    if not model or not contract:
        return False
    for numeric in ("version", "source_version"):
        value = stored[numeric]
        if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 50:
            return False
    if not isinstance(stored["confirmed"], bool):
        return False
    entries = stored["statements"]
    if (
        not isinstance(entries, list)
        or not entries
        or len(entries) > MAX_PUBLIC_STATEMENTS
    ):
        return False

    statements = []
    for ordinal, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict) or set(entry) - {
            "k",
            "o",
            "t",
            "pc",
            "e",
            "p",
            "mc",
            "mx",
        }:
            return False
        key = _normalize_key(entry.get("k"))
        text = _bounded_token_text(entry.get("t"), 1200)
        explanation = _bounded_token_text(entry.get("e"), 400)
        if not key or not text or not explanation:
            return False
        if entry.get("o") != ordinal:
            return False
        if entry.get("pc") not in STATEMENT_CLASSES:
            return False
        member_class = entry.get("mc")
        if member_class is not None and member_class not in STATEMENT_CLASSES:
            return False
        clarification = entry.get("mx")
        if clarification is not None:
            clarification = _bounded_token_text(clarification, MAX_CLARIFICATION_UNITS)
            if clarification is None:
                return False
        paths = _load_public_paths(entry.get("p"))
        if paths is None:
            return False
        statements.append(
            {
                "k": key,
                "o": ordinal,
                "t": text,
                "pc": entry["pc"],
                "e": explanation,
                "p": paths,
                "mc": member_class,
                "mx": clarification,
            }
        )
    return {
        "model": model,
        "contract": contract,
        "version": stored["version"],
        "source_version": stored["source_version"],
        "confirmed": stored["confirmed"],
        "statements": statements,
    }


def _load_public_paths(stored):
    if not isinstance(stored, list) or not stored or len(stored) > 4:
        return None
    paths = []
    for entry in stored:
        if not isinstance(entry, dict) or set(entry) != {"label", "clauses"}:
            return None
        label = _bounded_token_text(entry["label"], 20)
        clauses = entry["clauses"]
        if not label or not isinstance(clauses, list) or not clauses or len(clauses) > 8:
            return None
        cleaned = []
        for clause in clauses:
            value = _bounded_token_text(clause, 200)
            if not value:
                return None
            cleaned.append(value)
        paths.append({"label": label, "clauses": cleaned})
    return paths


def _normalize_key(value):
    """Opaque-key normalization, null on failure (the house idiom)."""
    try:
        return str(UUID(str(value)))
    except (TypeError, ValueError, AttributeError):
        return None


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

    # A confirmed source lands on Review Requirements unless the member asked
    # for the source screen by name, so re-entering the room resumes where the
    # member actually was rather than at checkpoint 1 again. Once an analysis
    # exists it lands on the workbench for the same reason: that is where the
    # member actually was.
    if step in {STEP_REQUIREMENTS, STEP_ALIGNMENT} or (
        step is None and working.is_confirmed
    ):
        try:
            requirement_set = opportunity_slate_service.get_requirements_for_owner(
                identity.user_key
            )
        except (DatabaseServiceError, OpportunitySlateServiceError):
            return _render_unavailable()
        selected_key = _normalize_key(request.args.get("statement"))
        if requirement_set is not None and step != STEP_REQUIREMENTS:
            try:
                analysis, responses = (
                    opportunity_slate_service.get_analysis_for_owner(
                        identity.user_key
                    )
                )
            except (DatabaseServiceError, OpportunitySlateServiceError):
                return _render_unavailable()
            if analysis is not None or step == STEP_ALIGNMENT:
                try:
                    evidence = opportunity_slate_service.list_evidence_for_owner(
                        identity.user_key
                    )
                except (DatabaseServiceError, OpportunitySlateServiceError):
                    return _render_unavailable()
                return _render_room(
                    _alignment_room_from_views(
                        working,
                        requirement_set,
                        analysis,
                        responses,
                        evidence,
                        selected_key=selected_key,
                    )
                )
        return _render_room(
            _requirements_room_from_views(
                working,
                requirement_set,
                selected_key=selected_key,
            )
        )

    try:
        review = opportunity_slate_service.get_source_review_for_owner(
            identity.user_key, working.source_key
        )
    except (DatabaseServiceError, OpportunitySlateServiceError):
        return _render_unavailable()
    notice_kind = _read_notice_token(request.args.get("notice"))
    notice = (
        UPLOAD_TRUNCATED_NOTICE
        if notice_kind == "upload_truncated"
        else IMPORT_TRUNCATED_NOTICE if notice_kind == "import_truncated" else None
    )
    return _render_room(
        _review_room_from_view(working, review=review, notice=notice)
    )


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


# ---------------------------------------------------------------------------
# Slice OS-6 — document upload and public-link import
#
# Signed-in-only surfaces (handoff section 18 safeguard 1): the anonymous
# public session's intake tiles stay in their existing honest "available
# with membership" state and never reach either route below — there is no
# anonymous branch to build here, unlike every other route in this module.
# Both routes follow set_source's exact shape (flag check, same-origin
# check, owner-only identity check, then the actual work) and land on the
# same two outcomes: redirect to Review Source on success, or re-render
# intake with the one truthful failure card for that route on any failure —
# never a partial source, on any failure path, because the save only ever
# happens after extraction has already fully succeeded.
# ---------------------------------------------------------------------------


@opportunity_slate.post(f"{ROOM_PATH}/source/upload")
def upload_source():
    """Upload a PDF, DOCX, or TXT document as the employer source.

    Every failure reason — wrong declared type, spoofed magic bytes,
    oversize body, corrupt or unreadable file — renders the same "We
    couldn't read this document." card (handoff section 7 / 14-M13-f); the
    uploaded bytes are never retried, never partially saved, and are
    discarded the moment this request ends.
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

    idempotency_key = request.form.get("idempotency_key") or str(uuid4())
    replace = request.form.get("replace") == "1"

    try:
        extracted_text, truncated = extract_uploaded_document(
            request.files.get("document")
        )
        clean_text = validate_source_text(extracted_text)
    except (OpportunitySourceIntakeError, OpportunitySlateServiceError):
        return _render_room(
            _intake_room(
                "member",
                replace=replace,
                error={
                    "kind": "unavailable",
                    "heading": UPLOAD_FAILURE_HEADING,
                    "message": UPLOAD_FAILURE_MESSAGE,
                    "truth": INTAKE_FAILURE_TRUTH,
                },
            ),
            status=400,
        )

    try:
        opportunity_slate_service.save_source_for_owner(
            identity.user_key,
            idempotency_key,
            clean_text,
            capture_method="uploaded",
        )
    except DatabaseServiceError:
        return _render_unavailable()
    except OpportunitySlateServiceError:
        return _render_room(
            _intake_room(
                "member",
                replace=replace,
                error={
                    "kind": "unavailable",
                    "heading": UPLOAD_FAILURE_HEADING,
                    "message": UPLOAD_FAILURE_MESSAGE,
                    "truth": INTAKE_FAILURE_TRUTH,
                },
            ),
            status=400,
        )

    return redirect(
        url_for(
            "opportunity_slate.room",
            notice=_mint_notice_token("upload_truncated") if truncated else None,
        )
    )


@opportunity_slate.post(f"{ROOM_PATH}/source/import")
def import_source():
    """Import a public employer or ATS page as the employer source.

    The fetch itself runs entirely inside the SSRF-guarded
    ``services/opportunity_source_intake_service.guarded_fetch_html`` — this
    route never opens a socket. Every failure reason — non-https URL, a
    private/loopback/link-local/metadata address, a redirect off the
    validated boundary, an oversize or slow response, unreadable markup —
    renders the same "Nothing was saved or analyzed." card (handoff section
    7), so no response here can be used to distinguish one internal guard
    reason from another.
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

    idempotency_key = request.form.get("idempotency_key") or str(uuid4())
    replace = request.form.get("replace") == "1"
    source_url = request.form.get("source_url", "")

    try:
        extracted_text, truncated, _final_url = extract_imported_link(source_url)
        clean_text = validate_source_text(extracted_text)
    except (OpportunitySourceIntakeError, OpportunitySlateServiceError):
        return _render_room(
            _intake_room(
                "member",
                replace=replace,
                error={
                    "kind": "unavailable",
                    "heading": IMPORT_FAILURE_HEADING,
                    "message": IMPORT_FAILURE_MESSAGE,
                    "truth": INTAKE_FAILURE_TRUTH,
                },
            ),
            status=400,
        )

    try:
        opportunity_slate_service.save_source_for_owner(
            identity.user_key,
            idempotency_key,
            clean_text,
            capture_method="imported",
        )
    except DatabaseServiceError:
        return _render_unavailable()
    except OpportunitySlateServiceError:
        return _render_room(
            _intake_room(
                "member",
                replace=replace,
                error={
                    "kind": "unavailable",
                    "heading": IMPORT_FAILURE_HEADING,
                    "message": IMPORT_FAILURE_MESSAGE,
                    "truth": INTAKE_FAILURE_TRUTH,
                },
            ),
            status=400,
        )

    return redirect(
        url_for(
            "opportunity_slate.room",
            notice=_mint_notice_token("import_truncated") if truncated else None,
        )
    )


def _reload_review_for_error(
    identity,
    *,
    editor_text,
    message,
    heading,
    status,
    field_hint=None,
    kind="field",
    truth=None,
):
    """Re-render Review Source with the member's own wording intact.

    A failed correction must never cost the member their typing, and a failed
    AI step must never cost them the concerns they had already resolved — so
    the current review is read back and re-rendered alongside the failure
    card. When the current server state cannot be read at all, the truthful
    503 is returned instead of a guessed page.
    """
    try:
        working = opportunity_slate_service.get_working_session_for_owner(
            identity.user_key
        )
    except (DatabaseServiceError, OpportunitySlateServiceError):
        return _render_unavailable(text=editor_text)
    if working is None:
        return _render_room(_intake_room("member", text=editor_text))
    try:
        review = opportunity_slate_service.get_source_review_for_owner(
            identity.user_key, working.source_key
        )
    except (DatabaseServiceError, OpportunitySlateServiceError):
        review = None
    return _render_room(
        _review_room_from_view(
            working,
            review=review,
            editing=kind == "field",
            editor_text=editor_text,
            error={
                "kind": kind,
                "heading": heading,
                "message": message,
                "field_hint": field_hint,
                "truth": truth or f"Session private • {TRUTH_NOTHING_SAVED}",
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

    return redirect(url_for("opportunity_slate.room", step=STEP_REQUIREMENTS))


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


# ---------------------------------------------------------------------------
# Slice OS-2 — the two AI steps, the correction rail, and checkpoint 2
#
# Every one of these is an explicit member action on an explicit control. No
# timer, navigation, or voice event reaches them (handoff section 2's
# transition invariant 1), and each one is rate limited in app.py at the
# interview AI budget of 6 per minute per client.
# ---------------------------------------------------------------------------


def _daily_ai_ceiling():
    """The anonymous daily AI-call ceiling (handoff section 18 safeguard 3).

    Read from ``current_app.config`` on every request rather than captured in
    a module constant, so a value changed in the live config object takes
    effect on the next request.

    Slice OS-2 independent review, finding F11: that is NOT the same as
    "no restart is needed", which is what this docstring used to claim.
    ``app.py`` populates ``PEERSLATE_OPPSLATE_DAILY_AI_CEILING`` once from
    ``os.environ`` at import and nothing in the runtime mutates it
    afterwards, so changing the Azure App Service setting still requires the
    app to restart before this function sees the new number. The per-request
    read buys reload-safety and testability, not live reconfiguration.
    """
    try:
        return int(
            current_app.config.get("PEERSLATE_OPPSLATE_DAILY_AI_CEILING", 0) or 0
        )
    except (TypeError, ValueError):
        return 0


def _proposal_failure(error, heading, message, *, mode="member"):
    """Image 09-b's failure card, told for the step that actually failed."""
    if error.code == "budget":
        # Finding F2: never-opened and spent are different facts. See the
        # copy constants above for why the shipped default makes this the
        # branch that matters most.
        if error.reason == "ceiling_closed":
            heading, message = (
                PUBLIC_BUDGET_CLOSED_HEADING,
                PUBLIC_BUDGET_CLOSED_MESSAGE,
            )
        else:
            heading, message = PUBLIC_BUDGET_HEADING, PUBLIC_BUDGET_MESSAGE
    elif error.code == "too_long":
        heading = (
            PUBLIC_OVERSIZE_HEADING
            if mode == "public"
            else "That role text is too long to review."
        )
        message = (
            PUBLIC_OVERSIZE_MESSAGE
            if mode == "public"
            else str(error) + " Shorten it and try again — your text is unchanged."
        )
    return {
        "kind": "proposal",
        "heading": heading,
        "message": message,
        "truth": PROPOSAL_FAILURE_TRUTH,
    }


def _proposal_status(error):
    """A refusal we made is not a provider failure, and says so in its code."""
    if error.code == "too_long":
        return 400
    if error.code == "budget":
        # Finding F2 again, in the status line. A spent ceiling really is
        # "too many requests"; a ceiling that was never opened is not — the
        # capability is simply not turned on here, which is 503, not 429.
        # A client backing off and retrying tomorrow is correct behavior for
        # the first and pointless for the second.
        return 429 if error.reason == "daily_ceiling" else 503
    if error.code == "invalid":
        return 400
    return 502


def _reload_requirements_for_error(identity, *, error, status, selected_key=None):
    """Re-render Review Requirements with every confirmed input intact."""
    try:
        working = opportunity_slate_service.get_working_session_for_owner(
            identity.user_key
        )
        requirement_set = (
            opportunity_slate_service.get_requirements_for_owner(identity.user_key)
            if working is not None
            else None
        )
    except (DatabaseServiceError, OpportunitySlateServiceError):
        return _render_unavailable()
    if working is None:
        return _render_room(_intake_room("member"))
    return _render_room(
        _requirements_room_from_views(
            working, requirement_set, selected_key=selected_key, error=error
        ),
        status=status,
    )


@opportunity_slate.post(f"{ROOM_PATH}/source/review")
def review_source_wording():
    """AI step 1. Proposes extraction concerns on the captured wording.

    The proposals are spans of the member's own displayed text plus a reason
    to look at each one. PeerSlate never rewrites the employer's wording here:
    ``services/opportunity_analysis_service.py`` rejects any reply whose quote
    is not actually in the text it was given, so a rewritten quote fails the
    contract rather than reaching the screen.
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
        working = opportunity_slate_service.get_working_session_for_owner(
            identity.user_key
        )
    except (DatabaseServiceError, OpportunitySlateServiceError):
        return _render_unavailable()
    if working is None:
        return redirect(url_for("opportunity_slate.room"))

    try:
        proposal = opportunity_analysis_service.propose_source_concerns(
            working.display_text
        )
    except OpportunityAnalysisError as error:
        return _reload_review_for_error(
            identity,
            editor_text=working.display_text,
            heading=REVIEW_FAILURE_HEADING,
            message=REVIEW_FAILURE_MESSAGE,
            status=_proposal_status(error),
            kind="proposal",
            truth=PROPOSAL_FAILURE_TRUTH,
        )

    try:
        opportunity_slate_service.save_source_review_for_owner(
            identity.user_key,
            working.source_key,
            working.source_version_token,
            proposal["concerns"],
            proposal["model"],
            proposal["prompt_contract"],
        )
    except DatabaseServiceError:
        return _reload_review_for_error(
            identity,
            editor_text=working.display_text,
            heading=REVIEW_FAILURE_HEADING,
            message=UNAVAILABLE_MESSAGE,
            status=503,
            kind="proposal",
            truth=PROPOSAL_FAILURE_TRUTH,
        )
    except OpportunitySlateServiceError as error:
        return _reload_review_for_error(
            identity,
            editor_text=working.display_text,
            heading="This role source changed.",
            message=CONFLICT_MESSAGE
            if error.code == "changed"
            else REVIEW_FAILURE_MESSAGE,
            status=409 if error.code == "changed" else 400,
            kind="proposal",
            truth=PROPOSAL_FAILURE_TRUTH,
        )

    return redirect(url_for("opportunity_slate.room", step=STEP_REVIEW))


@opportunity_slate.post(f"{ROOM_PATH}/source/concerns")
def resolve_source_concern():
    """The member's decision on one proposed concern: apply, or dismiss.

    Applying splices their corrected wording into the displayed document;
    dismissing changes no wording at all. Both are recorded against the
    proposal so "PeerSlate flagged this and the member kept it" stays a fact
    the record can answer.
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

    concern_key = request.form.get("concern_key")
    decision = request.form.get("decision")
    corrected_text = request.form.get("corrected_text", "")
    version_token = request.form.get("concern_version_token")

    try:
        working = opportunity_slate_service.get_working_session_for_owner(
            identity.user_key
        )
        review = (
            opportunity_slate_service.get_source_review_for_owner(
                identity.user_key, working.source_key
            )
            if working is not None
            else None
        )
    except (DatabaseServiceError, OpportunitySlateServiceError):
        return _render_unavailable()
    if working is None or review is None:
        return redirect(url_for("opportunity_slate.room"))

    concern = next(
        (
            item
            for item in review.concerns
            if item.concern_key == (_normalize_key(concern_key) or "")
        ),
        None,
    )
    if concern is None or decision not in {"applied", "dismissed"}:
        return _reload_review_for_error(
            identity,
            editor_text=working.display_text,
            heading="We couldn't apply that decision.",
            message=CONFLICT_MESSAGE,
            status=409,
        )

    document_text = None
    if decision == "applied":
        try:
            document_text = apply_concern_correction(
                working.display_text, concern.quoted_text, corrected_text
            )
        except OpportunitySlateServiceError as error:
            return _reload_review_for_error(
                identity,
                editor_text=corrected_text if isinstance(corrected_text, str) else "",
                heading="We couldn't use that wording.",
                message=(
                    str(error)
                    if error.code == "changed"
                    else FIELD_ERROR_MESSAGES.get(error.code, DEFAULT_FIELD_ERROR)
                ),
                field_hint=FIELD_ERROR_HINTS.get(error.code, DEFAULT_FIELD_HINT),
                status=409 if error.code == "changed" else 400,
            )

    try:
        opportunity_slate_service.resolve_source_concern_for_owner(
            identity.user_key,
            concern_key,
            version_token,
            decision,
            corrected_span_text=corrected_text if decision == "applied" else None,
            document_text=document_text,
        )
    except DatabaseServiceError:
        return _reload_review_for_error(
            identity,
            editor_text=working.display_text,
            heading="We couldn't apply that decision.",
            message=UNAVAILABLE_MESSAGE,
            status=503,
        )
    except OpportunitySlateServiceError as error:
        return _reload_review_for_error(
            identity,
            editor_text=working.display_text,
            heading="This role source changed.",
            message=CONFLICT_MESSAGE
            if error.code == "changed"
            else FIELD_ERROR_MESSAGES.get(error.code, DEFAULT_FIELD_ERROR),
            status=409 if error.code == "changed" else 400,
        )

    return redirect(url_for("opportunity_slate.room", step=STEP_REVIEW))


@opportunity_slate.post(f"{ROOM_PATH}/requirements")
def interpret_requirements():
    """AI step 2. Segments the confirmed source and proposes each reading."""
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
        working = opportunity_slate_service.get_working_session_for_owner(
            identity.user_key
        )
    except (DatabaseServiceError, OpportunitySlateServiceError):
        return _render_unavailable()
    if working is None:
        return redirect(url_for("opportunity_slate.room"))
    if not working.is_confirmed:
        # Interpretation reads the source the member accepted. Without a
        # confirmed source there is nothing to interpret, and inventing one
        # would put words in the employer's mouth.
        return redirect(url_for("opportunity_slate.room", step=STEP_REVIEW))

    try:
        proposal = opportunity_analysis_service.propose_statement_interpretation(
            working.display_text
        )
    except OpportunityAnalysisError as error:
        return _reload_requirements_for_error(
            identity,
            error=_proposal_failure(
                error, INTERPRET_FAILURE_HEADING, INTERPRET_FAILURE_MESSAGE
            ),
            status=_proposal_status(error),
        )

    try:
        opportunity_slate_service.save_requirement_proposal_for_owner(
            identity.user_key,
            working.source_key,
            working.source_version_token,
            proposal["statements"],
            proposal["model"],
            proposal["prompt_contract"],
        )
    except DatabaseServiceError:
        return _reload_requirements_for_error(
            identity,
            error=_proposal_failure(
                OpportunityAnalysisError("unavailable"),
                INTERPRET_FAILURE_HEADING,
                UNAVAILABLE_MESSAGE,
            ),
            status=503,
        )
    except OpportunitySlateServiceError as error:
        return _reload_requirements_for_error(
            identity,
            error=_proposal_failure(
                OpportunityAnalysisError("unavailable"),
                "This role source changed."
                if error.code == "changed"
                else INTERPRET_FAILURE_HEADING,
                CONFLICT_MESSAGE
                if error.code == "changed"
                else INTERPRET_FAILURE_MESSAGE,
            ),
            status=409 if error.code == "changed" else 400,
        )

    return redirect(url_for("opportunity_slate.room", step=STEP_REQUIREMENTS))


@opportunity_slate.post(f"{ROOM_PATH}/requirements/corrections")
def correct_statement():
    """Reclassify or clarify one statement. The member's reading wins.

    The AI's proposed class and structure stay exactly where they were; the
    member's decision is stored beside them. Correcting a statement clears
    the requirement-set confirmation, because a confirmed set must never
    describe a reading the member has since changed.
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

    statement_key = _normalize_key(request.form.get("statement_key"))
    version_token = request.form.get("statement_version_token")
    member_class = request.form.get("member_class") or None
    clarification = request.form.get("member_clarification", "")

    if member_class is not None and member_class not in STATEMENT_CLASSES:
        member_class = None

    try:
        opportunity_slate_service.correct_requirement_statement_for_owner(
            identity.user_key,
            statement_key,
            version_token,
            member_class=member_class,
            member_clarification=clarification,
        )
    except DatabaseServiceError:
        return _reload_requirements_for_error(
            identity,
            error={
                "kind": "unavailable",
                "heading": "We couldn't apply that correction.",
                "message": UNAVAILABLE_MESSAGE,
                "truth": f"Session private • {TRUTH_NOTHING_SAVED}",
            },
            status=503,
            selected_key=statement_key,
        )
    except OpportunitySlateServiceError as error:
        return _reload_requirements_for_error(
            identity,
            error={
                "kind": "field",
                "heading": "This statement changed."
                if error.code == "changed"
                else "We couldn't use that correction.",
                "message": CONFLICT_MESSAGE
                if error.code == "changed"
                else (
                    CLARIFICATION_TOO_LONG_MESSAGE
                    if error.code == "too_long"
                    else FIELD_ERROR_MESSAGES.get(error.code, DEFAULT_FIELD_ERROR)
                ),
                "field_hint": FIELD_ERROR_HINTS.get(error.code, DEFAULT_FIELD_HINT),
                "truth": f"Session private • {TRUTH_NOTHING_SAVED}",
            },
            status=409 if error.code == "changed" else 400,
            selected_key=statement_key,
        )

    return redirect(
        url_for(
            "opportunity_slate.room",
            step=STEP_REQUIREMENTS,
            statement=statement_key,
        )
    )


@opportunity_slate.post(f"{ROOM_PATH}/requirements/confirm")
def confirm_requirements():
    """Checkpoint 2 of 2. Records which requirement set the member accepted.

    It saves no slate, produces no alignment result, and calls no AI. The
    evidence alignment this checkpoint precedes is slice OS-3; this slice
    stops here and the screen says so rather than showing a stage that never
    ran.
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
        opportunity_slate_service.confirm_requirements_for_owner(
            identity.user_key,
            request.form.get("requirement_set_key"),
            request.form.get("set_version_token"),
        )
    except DatabaseServiceError:
        return _reload_requirements_for_error(
            identity,
            error={
                "kind": "unavailable",
                "heading": "We couldn't confirm these requirements.",
                "message": UNAVAILABLE_MESSAGE,
                "truth": f"Session private • {TRUTH_NOTHING_SAVED}",
            },
            status=503,
        )
    except OpportunitySlateServiceError as error:
        return _reload_requirements_for_error(
            identity,
            error={
                "kind": "field",
                "heading": "These requirements changed.",
                "message": CONFLICT_MESSAGE
                if error.code == "changed"
                else FIELD_ERROR_MESSAGES.get(error.code, DEFAULT_FIELD_ERROR),
                "truth": f"Session private • {TRUTH_NOTHING_SAVED}",
            },
            status=409 if error.code == "changed" else 400,
        )

    # Image 03's primary action is "Confirm requirements and analyze", and
    # slice OS-3 is the first slice in which the second half is true. The two
    # halves stay two separately-fenced writes — checkpoint 2 is recorded
    # first and stands on its own — but they are ONE explicit member action,
    # which is exactly what image 08's processing frame draws happening on
    # this screen. A failed analysis therefore leaves a confirmed requirement
    # set behind it, which is the section 7 contract ("your confirmed source
    # and requirements are unchanged") rather than a half-applied step.
    error, status = _run_alignment_for_owner(identity)
    if error is not None:
        return _reload_requirements_for_error(identity, error=error, status=status)
    return redirect(url_for("opportunity_slate.room", step=STEP_ALIGNMENT))


# ---------------------------------------------------------------------------
# Slice OS-3 — the alignment analysis, the workbench, and member responses.
#
# This is the first step in the room that is given a fact about the member.
# Two things make that safe and both are structural rather than editorial:
#
#   * the grounding allowlist is built HERE, server-side, from the member's
#     own confirmed evidence (or, anonymously, from the labelled demo
#     fixture), and the validator refuses any reply that cites an id it was
#     not given; and
#   * the model returns citations, never prose — every sentence on the screen
#     is composed above from the employer's confirmed wording, the member's
#     own evidence, and PeerSlate's reviewed templates.
#
# See THE COMPOSITION BOUNDARY in services/opportunity_analysis_service.py.
# ---------------------------------------------------------------------------


def _reload_alignment_for_error(identity, *, error, status, selected_key=None):
    """Re-render the workbench with every confirmed input and result intact."""
    try:
        working = opportunity_slate_service.get_working_session_for_owner(
            identity.user_key
        )
        requirement_set = (
            opportunity_slate_service.get_requirements_for_owner(identity.user_key)
            if working is not None
            else None
        )
    except (DatabaseServiceError, OpportunitySlateServiceError):
        return _render_unavailable()
    if working is None:
        return _render_room(_intake_room("member"))
    if requirement_set is None:
        return _render_room(
            _requirements_room_from_views(working, None, error=error), status=status
        )
    try:
        analysis, responses = opportunity_slate_service.get_analysis_for_owner(
            identity.user_key
        )
        evidence = opportunity_slate_service.list_evidence_for_owner(
            identity.user_key
        )
    except (DatabaseServiceError, OpportunitySlateServiceError):
        analysis, responses, evidence = None, {}, ()
    return _render_room(
        _alignment_room_from_views(
            working,
            requirement_set,
            analysis,
            responses,
            evidence,
            selected_key=selected_key,
            error=error,
        ),
        status=status,
    )


def _run_alignment_for_owner(identity):
    """Run AI step 3 for this owner. ``(error_card, status)``; ``(None, None)``
    on success.

    Shared by the two explicit member actions that reach it — image 03's
    `Confirm requirements and analyze` and image 04's `Explore alignment` /
    `Run this again` — so both get identical grounding, identical validation,
    and identical failure truth. Nothing else calls it: no timer, no
    navigation, and no voice event runs an AI step in this room (handoff
    section 2, transition invariant 1).
    """
    try:
        working = opportunity_slate_service.get_working_session_for_owner(
            identity.user_key
        )
        requirement_set = (
            opportunity_slate_service.get_requirements_for_owner(identity.user_key)
            if working is not None
            else None
        )
    except (DatabaseServiceError, OpportunitySlateServiceError):
        return (
            {
                "kind": "unavailable",
                "heading": ANALYSIS_FAILURE_HEADING,
                "message": UNAVAILABLE_MESSAGE,
                "truth": ANALYSIS_FAILURE_TRUTH,
            },
            503,
        )
    if working is None or requirement_set is None or not requirement_set.is_confirmed:
        # Analysis reads the requirement set the member accepted. Without a
        # confirmed set there is nothing to compare, and inventing one would
        # put requirements in the employer's mouth.
        return (
            {
                "kind": "proposal",
                "heading": "Confirm these requirements first.",
                "message": (
                    "PeerSlate compares the qualifications you accepted. "
                    "Nothing was analyzed."
                ),
                "truth": ANALYSIS_FAILURE_TRUTH,
            },
            400,
        )

    statements = _statements_from_views(requirement_set.statements)
    qualifications = _qualifications_for_analysis(statements)
    if not qualifications:
        # No required or preferred qualification in the confirmed reading.
        # The workbench says so on its own; this is not a failure.
        return None, None

    try:
        evidence_views = opportunity_slate_service.list_evidence_for_owner(
            identity.user_key
        )
    except (DatabaseServiceError, OpportunitySlateServiceError):
        return (
            {
                "kind": "unavailable",
                "heading": ANALYSIS_FAILURE_HEADING,
                "message": UNAVAILABLE_MESSAGE,
                "truth": ANALYSIS_FAILURE_TRUTH,
            },
            503,
        )

    allowlist = _evidence_allowlist(evidence_views)
    evidence_by_id = {item["id"]: item for item in allowlist}

    try:
        proposal = opportunity_analysis_service.propose_alignment(
            qualifications, evidence_by_id
        )
    except OpportunityAnalysisError as error:
        if error.code == "no_evidence":
            # Not a failure. The member has authorized nothing yet, so every
            # qualification is honestly "not enough information" and no
            # provider call is made and no budget is spent.
            proposal = opportunity_analysis_service.empty_alignment(qualifications)
        else:
            return (
                _proposal_failure(
                    error, ANALYSIS_FAILURE_HEADING, ANALYSIS_FAILURE_MESSAGE
                ),
                _proposal_status(error),
            )

    results = [
        {
            "statement_key": result["statement_key"],
            "status": result["status"],
            "citations": _citations_for_storage(result, evidence_by_id),
        }
        for result in proposal["results"]
    ]

    try:
        opportunity_slate_service.save_analysis_for_owner(
            identity.user_key,
            requirement_set.requirement_set_key,
            requirement_set.version_token,
            results,
            proposal["model"] or "none",
            proposal["prompt_contract"],
            len(allowlist),
        )
    except DatabaseServiceError:
        return (
            _proposal_failure(
                OpportunityAnalysisError("unavailable"),
                ANALYSIS_FAILURE_HEADING,
                UNAVAILABLE_MESSAGE,
            ),
            503,
        )
    except OpportunitySlateServiceError as error:
        return (
            _proposal_failure(
                OpportunityAnalysisError("unavailable"),
                "These requirements changed."
                if error.code == "changed"
                else ANALYSIS_FAILURE_HEADING,
                CONFLICT_MESSAGE
                if error.code == "changed"
                else ANALYSIS_FAILURE_MESSAGE,
            ),
            409 if error.code == "changed" else 400,
        )
    return None, None


@opportunity_slate.post(f"{ROOM_PATH}/analysis")
def run_analysis():
    """AI step 3. Compares the confirmed qualifications with authorized evidence.

    Also the retry path: image 09-b's `Retry analysis` posts here. Running it
    again replaces the previous result for this requirement-set version and
    changes nothing else — the member's confirmed source, their confirmed
    requirements, and every response they have written are untouched, in the
    success case and in the failure case alike.
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

    error, status = _run_alignment_for_owner(identity)
    if error is not None:
        return _reload_alignment_for_error(identity, error=error, status=status)
    return redirect(url_for("opportunity_slate.room", step=STEP_ALIGNMENT))


@opportunity_slate.post(f"{ROOM_PATH}/responses")
def save_response():
    """One member response to one qualification (image 04's response rail).

    Member-attributed context, and only ever what the member chose: it never
    becomes evidence, never becomes a citation, and never changes a status.
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

    statement_key = _normalize_key(request.form.get("statement_key"))
    version_token = request.form.get("statement_version_token")
    response_kind = request.form.get("response_kind")
    response_text = request.form.get("response_text", "")
    evidence_key = request.form.get("connected_evidence_key")

    if response_kind not in RESPONSE_KINDS:
        return _reload_alignment_for_error(
            identity,
            error={
                "kind": "field",
                "heading": "We couldn't record that response.",
                "message": DEFAULT_FIELD_ERROR,
                "field_hint": DEFAULT_FIELD_HINT,
                "truth": f"Session private • {TRUTH_NOTHING_SAVED}",
            },
            status=400,
            selected_key=statement_key,
        )

    try:
        opportunity_slate_service.save_response_for_owner(
            identity.user_key,
            statement_key,
            version_token,
            response_kind,
            response_text=response_text,
            connected_evidence_key=evidence_key,
        )
    except DatabaseServiceError:
        return _reload_alignment_for_error(
            identity,
            error={
                "kind": "unavailable",
                "heading": "We couldn't record that response.",
                "message": UNAVAILABLE_MESSAGE,
                "truth": f"Session private • {TRUTH_NOTHING_SAVED}",
            },
            status=503,
            selected_key=statement_key,
        )
    except OpportunitySlateServiceError as error:
        return _reload_alignment_for_error(
            identity,
            error={
                "kind": "field",
                "heading": "This qualification changed."
                if error.code == "changed"
                else "We couldn't record that response.",
                "message": CONFLICT_MESSAGE
                if error.code == "changed"
                else (
                    RESPONSE_TOO_LONG_MESSAGE
                    if error.code == "too_long"
                    else FIELD_ERROR_MESSAGES.get(error.code, DEFAULT_FIELD_ERROR)
                ),
                "field_hint": FIELD_ERROR_HINTS.get(error.code, DEFAULT_FIELD_HINT),
                "truth": f"Session private • {TRUTH_NOTHING_SAVED}",
            },
            status=409 if error.code == "changed" else 400,
            selected_key=statement_key,
        )

    return redirect(
        url_for(
            "opportunity_slate.room",
            step=STEP_ALIGNMENT,
            statement=statement_key,
        )
    )


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
    if action not in _PUBLIC_SESSION_ACTIONS:
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
        # New employer wording invalidates every proposal made about the old
        # wording. They are dropped rather than carried forward, so the
        # visitor can never be shown a reading of text they replaced.
        context = {
            "v": PUBLIC_CONTEXT_VERSION,
            "text": clean_text,
            "corrected": None,
            "version": version,
            "confirmed": False,
            "review": None,
            "requirements": None,
            "alignment": None,
            "responses": None,
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
        context["review"] = None
        context["requirements"] = None
        context["alignment"] = None
        context["responses"] = None

    elif action == "confirm":
        if context is None:
            return _public_reset_response()
        context = dict(context)
        context["confirmed"] = True
        requested_step = STEP_REQUIREMENTS

    elif action == "resolve":
        if context is None or not context.get("review"):
            return _public_reset_response()
        concern_key = _normalize_key(body.get("concern_key"))
        decision = body.get("decision")
        concern = next(
            (
                entry
                for entry in context["review"]["concerns"]
                if entry["k"] == concern_key
            ),
            None,
        )
        if concern is None or decision not in {"applied", "dismissed"}:
            return _public_invalid_request()

        context = dict(context)
        review = {
            "model": context["review"]["model"],
            "contract": context["review"]["contract"],
            "concerns": [dict(entry) for entry in context["review"]["concerns"]],
        }
        target = next(entry for entry in review["concerns"] if entry["k"] == concern_key)

        if decision == "applied":
            try:
                document_text = apply_concern_correction(
                    _public_display_text(context),
                    target["q"],
                    body.get("corrected_text"),
                )
            except OpportunitySlateServiceError as error:
                room = _review_room_from_context(
                    context,
                    error=_field_error(
                        "We couldn't use that wording.",
                        error.code,
                        "Public session • Nothing is stored.",
                    ),
                )
                token = _dump_public_context(context)
                return (
                    jsonify(
                        {
                            "success": False,
                            "step": STEP_REVIEW,
                            "html": _render_fragment(room, context_token=token),
                            "context_token": token,
                        }
                    ),
                    409 if error.code == "changed" else 400,
                )
            target["res"] = "applied"
            target["c"] = validate_source_text(
                body.get("corrected_text"), label="corrected wording"
            )
            context["corrected"] = (
                None if document_text == context["text"] else document_text
            )
            # Changed wording is not the wording the visitor confirmed, and
            # any statements read out of it no longer describe what is on
            # screen. Both go, exactly as they do for a signed-in member —
            # and with them the analysis and the responses, which describe
            # statements that no longer exist.
            context["confirmed"] = False
            context["requirements"] = None
            context["alignment"] = None
            context["responses"] = None
        else:
            target["res"] = "dismissed"

        context["review"] = review
        requested_step = STEP_REVIEW

    elif action == "statement":
        if context is None or not context.get("requirements"):
            return _public_reset_response()
        statement_key = _normalize_key(body.get("statement_key"))
        member_class = body.get("member_class") or None
        clarification = body.get("member_clarification")
        if member_class is not None and member_class not in STATEMENT_CLASSES:
            member_class = None
        if isinstance(clarification, str):
            clarification = clarification.strip() or None
            if clarification is not None and (
                len(clarification.encode("utf-16-le")) // 2 > MAX_CLARIFICATION_UNITS
            ):
                room = _requirements_room_from_context(
                    context,
                    selected_key=statement_key,
                    error={
                        "kind": "field",
                        "heading": "We couldn't use that clarification.",
                        "message": CLARIFICATION_TOO_LONG_MESSAGE,
                        "field_hint": FIELD_ERROR_HINTS["too_long"],
                        "truth": "Public session • Nothing is stored.",
                    },
                )
                token = _dump_public_context(context)
                return (
                    jsonify(
                        {
                            "success": False,
                            "step": STEP_REQUIREMENTS,
                            "html": _render_fragment(room, context_token=token),
                            "context_token": token,
                        }
                    ),
                    400,
                )
        else:
            clarification = None

        statements = [dict(entry) for entry in context["requirements"]["statements"]]
        target = next(
            (entry for entry in statements if entry["k"] == statement_key), None
        )
        if target is None:
            return _public_invalid_request()
        target["mc"] = member_class
        target["mx"] = clarification

        context = dict(context)
        requirements = dict(context["requirements"])
        requirements["statements"] = statements
        # A corrected reading is not the reading the visitor confirmed, and an
        # analysis of it describes requirements they have just changed.
        requirements["confirmed"] = False
        context["requirements"] = requirements
        context["alignment"] = None
        requested_step = STEP_REQUIREMENTS

    elif action == "confirm_requirements":
        if context is None or not context.get("requirements"):
            return _public_reset_response()
        context = dict(context)
        requirements = dict(context["requirements"])
        requirements["confirmed"] = True
        context["requirements"] = requirements
        requested_step = STEP_REQUIREMENTS

    elif action == "select":
        # Selecting a qualification changes what the rails describe and
        # nothing else. It exists as a server action so the workbench works
        # with JavaScript off; the room script intercepts it in place.
        if context is None or not context.get("alignment"):
            return _public_reset_response()
        requested_step = STEP_ALIGNMENT

    elif action == "respond":
        if context is None or not context.get("alignment"):
            return _public_reset_response()
        updated, failure = _apply_public_response(context, body)
        if failure is not None:
            return failure
        context = updated
        requested_step = STEP_ALIGNMENT

    if context is None:
        return _public_reset_response()
    return _public_render_response(
        context, requested_step, _normalize_key(body.get("statement_key"))
    )


def _apply_public_response(context, body):
    """Record one anonymous visitor's response in their own held state.

    ``(context, None)`` on success, ``(None, response)`` when the request was
    refused. Applies exactly the pairing rules the database CHECK applies to a
    signed-in member, so the public boundary is not the lenient one.
    """
    statement_key = _normalize_key(body.get("statement_key"))
    kind = body.get("response_kind")
    keys = {
        entry["k"] for entry in (context.get("requirements") or {})["statements"]
    }
    if not statement_key or statement_key not in keys or kind not in RESPONSE_KINDS:
        return None, _public_invalid_request()

    text = None
    evidence_key = None
    evidence_title = None
    evidence_version = None

    if kind in {"tell_more", "real_example"}:
        raw = body.get("response_text")
        text = raw.strip() if isinstance(raw, str) else ""
        if not text:
            return None, _public_response_error(
                context,
                statement_key,
                "Add your response before continuing.",
                FIELD_ERROR_HINTS["required"],
            )
        if len(text.encode("utf-16-le")) // 2 > MAX_RESPONSE_TEXT_UNITS:
            return None, _public_response_error(
                context,
                statement_key,
                RESPONSE_TOO_LONG_MESSAGE,
                FIELD_ERROR_HINTS["too_long"],
            )
    elif kind == "connect_evidence":
        evidence_key = _normalize_key(body.get("connected_evidence_key"))
        match = next(
            (
                item
                for item in _demo_evidence_allowlist()
                if item["evidence_key"] == evidence_key
            ),
            None,
        )
        if match is None:
            # The demo library is the only evidence vocabulary this mode has,
            # so a key outside it is refused rather than stored as a label.
            return None, _public_invalid_request()
        evidence_title = match["title"]
        evidence_version = match["version"]

    updated = dict(context)
    responses = dict(updated.get("responses") or {})
    responses[statement_key] = {
        "k": kind,
        "t": text,
        "ek": evidence_key,
        "ev": evidence_version,
        "et": evidence_title,
    }
    updated["responses"] = responses
    return updated, None


def _public_response_error(context, statement_key, message, hint):
    room = _alignment_room_from_context(
        context,
        selected_key=statement_key,
        error={
            "kind": "field",
            "heading": "We couldn't record that response.",
            "message": message,
            "field_hint": hint,
            "truth": "Public session • Nothing is stored.",
        },
    )
    token = _dump_public_context(context)
    return (
        jsonify(
            {
                "success": False,
                "step": STEP_ALIGNMENT,
                "html": _render_fragment(room, context_token=token),
                "context_token": token,
            }
        ),
        400,
    )


@opportunity_slate.post(f"{ROOM_PATH}/public-session/propose")
def public_propose():
    """The anonymous session's two AI steps, on their own rate-limit budget.

    Split out of :func:`public_session` so handoff section 18 safeguard 2's
    <= 6/minute AI budget can apply to the model calls without also throttling
    a visitor's typing. Everything else is identical: same signed
    browser-held context, same single renderer, no persistence method
    imported and no stored procedure called.

    Both steps consume the anonymous daily AI ceiling before the provider is
    contacted, and both fail closed into the section 7 failure card with the
    visitor's held state re-signed and returned intact.
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
        return _public_invalid_request()
    action = body.get("action")
    if action not in _PUBLIC_PROPOSE_ACTIONS:
        return _public_invalid_request()

    context = _load_public_context(body.get("context_token"))
    if context is None:
        return _public_reset_response()

    if action == "review":
        try:
            proposal = opportunity_analysis_service.propose_source_concerns(
                _public_display_text(context),
                is_public=True,
                daily_ceiling=_daily_ai_ceiling(),
            )
        except OpportunityAnalysisError as error:
            return _public_proposal_failure(
                context,
                STEP_REVIEW,
                error,
                REVIEW_FAILURE_HEADING,
                REVIEW_FAILURE_MESSAGE,
            )
        context = dict(context)
        context["review"] = {
            "model": proposal["model"],
            "contract": proposal["prompt_contract"],
            "concerns": [
                {
                    "k": str(uuid4()),
                    "q": concern["quoted_text"],
                    "r": concern["reason"],
                    "res": "pending",
                    "c": None,
                }
                for concern in proposal["concerns"]
            ],
        }
        return _public_render_response(context, STEP_REVIEW)

    if action == "analyze":
        requirements = context.get("requirements")
        if not requirements or not requirements.get("confirmed"):
            # Nothing to compare without a confirmed reading, and inventing
            # one would put requirements in the employer's mouth.
            return _public_render_response(context, STEP_REQUIREMENTS)

        statements = _public_statements(context)
        qualifications = _qualifications_for_analysis(statements)
        if not qualifications:
            return _public_render_response(context, STEP_ALIGNMENT)

        allowlist = _demo_evidence_allowlist()
        evidence_by_id = {item["id"]: item for item in allowlist}
        try:
            proposal = opportunity_analysis_service.propose_alignment(
                qualifications,
                evidence_by_id,
                is_public=True,
                daily_ceiling=_daily_ai_ceiling(),
                max_citations=MAX_PUBLIC_CITATIONS_TOTAL,
            )
        except OpportunityAnalysisError as error:
            if error.code == "no_evidence":
                proposal = opportunity_analysis_service.empty_alignment(
                    qualifications
                )
            else:
                # Image 09-b promises "your confirmed source and requirements
                # are unchanged", and a screen that says so while showing
                # neither is only half honest. A first analysis therefore
                # fails back onto Review Requirements, where the visitor can
                # SEE the inputs the card is talking about and press Retry;
                # a re-run fails back onto the workbench, where the previous
                # result is still there and still theirs.
                return _public_proposal_failure(
                    context,
                    STEP_ALIGNMENT if context.get("alignment") else STEP_REQUIREMENTS,
                    error,
                    ANALYSIS_FAILURE_HEADING,
                    ANALYSIS_FAILURE_MESSAGE,
                )

        context = dict(context)
        context["alignment"] = {
            "model": proposal["model"] or "none",
            "contract": proposal["prompt_contract"],
            "evidence": len(allowlist),
            "results": [
                {
                    "k": result["statement_key"],
                    "s": result["status"],
                    "c": [
                        {
                            "cl": citation["clause_ordinal"],
                            "t": citation["covered_text"],
                            "ek": evidence_by_id[citation["evidence_id"]][
                                "evidence_key"
                            ],
                            "ev": evidence_by_id[citation["evidence_id"]]["version"],
                            "et": evidence_by_id[citation["evidence_id"]]["title"],
                            "x": citation["excerpt"],
                        }
                        for citation in result["citations"]
                    ],
                }
                for result in proposal["results"]
            ],
        }
        return _public_render_response(context, STEP_ALIGNMENT)

    if not context.get("confirmed"):
        # Nothing to interpret without a confirmed source, and inventing one
        # would put words in the employer's mouth.
        return _public_render_response(context, STEP_REVIEW)

    try:
        proposal = opportunity_analysis_service.propose_statement_interpretation(
            _public_display_text(context),
            is_public=True,
            daily_ceiling=_daily_ai_ceiling(),
        )
    except OpportunityAnalysisError as error:
        return _public_proposal_failure(
            context,
            STEP_REQUIREMENTS,
            error,
            INTERPRET_FAILURE_HEADING,
            INTERPRET_FAILURE_MESSAGE,
        )

    context = dict(context)
    previous = context.get("requirements") or {}
    context["requirements"] = {
        "model": proposal["model"],
        "contract": proposal["prompt_contract"],
        "version": min(int(previous.get("version", 0)) + 1, 50),
        "source_version": context["version"],
        "confirmed": False,
        "statements": [
            {
                "k": str(uuid4()),
                "o": statement["ordinal"],
                "t": statement["employer_text"],
                "pc": statement["proposed_class"],
                "e": statement["proposed_explanation"],
                "p": statement["proposed_paths"],
                "mc": None,
                "mx": None,
            }
            for statement in proposal["statements"]
        ],
    }
    return _public_render_response(context, STEP_REQUIREMENTS)


def _public_render_response(context, requested_step, selected_key=None):
    """Render the anonymous room from held state and re-sign it.

    One renderer for every anonymous action, on both endpoints, so the public
    session cannot drift into a second surface — the same reason both modes
    share ``partials/opportunity_slate/_room.html``.
    """
    if requested_step in {STEP_ROLE, STEP_REPLACE}:
        room = _intake_room(
            "public",
            text=""
            if requested_step == STEP_REPLACE
            else _public_display_text(context),
            replace=requested_step == STEP_REPLACE,
            has_source=True,
        )
        step = requested_step
    elif requested_step == STEP_ALIGNMENT or (
        requested_step is None and context.get("alignment")
    ):
        room = _alignment_room_from_context(context, selected_key=selected_key)
        step = STEP_ALIGNMENT
    elif requested_step == STEP_REQUIREMENTS or (
        requested_step is None and context.get("confirmed")
    ):
        room = _requirements_room_from_context(context, selected_key=selected_key)
        step = STEP_REQUIREMENTS
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


def _public_display_text(context):
    return context.get("corrected") or context["text"]


def _public_invalid_request():
    return (
        jsonify({"success": False, "message": "We couldn't read that request."}),
        400,
    )


def _public_proposal_failure(context, step, error, heading, message):
    """Image 09-b's failure card in the anonymous session.

    The visitor's held state is re-signed and returned unchanged alongside the
    card, so a failed proposal never costs them the role text they pasted or
    the decisions they already made.
    """
    error_card = _proposal_failure(error, heading, message, mode="public")
    error_card["truth"] = "Public session • Nothing was generated or stored."
    if step == STEP_ALIGNMENT:
        room = _alignment_room_from_context(context, error=error_card)
    elif step == STEP_REQUIREMENTS:
        room = _requirements_room_from_context(context, error=error_card)
    else:
        room = _review_room_from_context(context, error=error_card)
    token = _dump_public_context(context)
    return (
        jsonify(
            {
                "success": False,
                "step": step,
                "html": _render_fragment(room, context_token=token),
                "context_token": token,
            }
        ),
        _proposal_status(error),
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
