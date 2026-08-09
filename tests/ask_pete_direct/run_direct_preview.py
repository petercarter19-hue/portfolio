"""Local visual preview for PS-ASK-PETE-DIRECT-001. Fixture-backed, no provider.

USAGE
-----

    /Users/petercarter/portfolio/venv/bin/python \
        tests/ask_pete_direct/run_direct_preview.py

    # boot, exercise both pages headlessly, print the result, exit
    /Users/petercarter/portfolio/venv/bin/python \
        tests/ask_pete_direct/run_direct_preview.py --check

Run from the repository root or a linked worktree with the project virtual
environment. The harness picks a free port on 127.0.0.1 and prints the two
URLs. It never uses port 5000 — macOS AirPlay Receiver squats it — and it
binds 127.0.0.1 rather than "localhost" for the same reason.

WHAT IT RENDERS
---------------

* ``/petec/resume`` — the real resume with the Ask Pete companion. Ask
  anything in the composer: ``/api/chat`` is served by a deterministic local
  fixture that always returns a grounded answer carrying a **handoff**, so the
  gold "Ask Pete directly" card appears with the consent-first private
  question form inside it. Filling it in and choosing "Send to Pete" performs
  a real POST to ``/api/ask-pete/direct-question``.
* ``/owner/ask-pete-inbox`` — the owner inbox, already holding two fixture
  questions (one unread, one read). Anything sent from the resume page shows
  up here on refresh, and Mark read / Archive / Restore all work against the
  in-memory store with the same version fencing the real procedures use.

IT WAS THE REGISTRATION LEG'S REHEARSAL, AND IT STILL GUARDS IT
--------------------------------------------------------------

This harness existed before the registration leg and registered the blueprint
on the REAL application object with exactly the line ``app.py`` now carries::

    app.register_blueprint(ask_pete_direct)

That was the cheap proof the registration would compose. Since the leg ran
(2026-08-08) ``app.py`` does it, so ``configure_preview_app()`` finds the
blueprint already registered and skips its own call — see the guard there. The
harness's job is unchanged: it is still the only way to see and click these
two surfaces, because production keeps the flag off and this turns it on
in-process.

WHAT IS FIXTURE, AND HOW YOU CAN TELL
--------------------------------------

Everything below the service seam. There is no database, no Azure SQL
connection, and no migration applied anywhere; ``InMemoryRecruiterQuestions``
answers the three stored procedures from a Python list that dies with the
process. No AI provider is called either — ``answer_public_question`` is
replaced by a fixed payload, so ``ANTHROPIC_API_KEY`` is never used and no
spend occurs.

Every response the harness serves carries ``X-PeerSlate-Preview:
fixture-in-memory``, and the banner is printed on start. The HTML itself is
the real production markup, deliberately unmodified — a preview that decorated
the page would not be a preview of the page.

Two configuration values are set here that production does NOT set:
``PEERSLATE_ALLOW_DEV_IDENTITY`` (so there is a signed-in owner without an
identity database) and ``PEERSLATE_OWNER_USER_KEYS`` pointing at that dev key
(so the inbox is reachable and the question has a recipient).
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import socket
import sys
import threading
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# app.py reads this at import time. The preview never calls a provider, so any
# non-empty placeholder is correct here — and using a placeholder rather than a
# real key is what guarantees a stray call would fail loudly instead of billing.
os.environ.setdefault("ANTHROPIC_API_KEY", "ask-pete-direct-preview-placeholder")

import app as app_module  # noqa: E402  (must follow the environment default)
import ask_pete_direct_routes  # noqa: E402
from services.ask_pete_direct_service import (  # noqa: E402
    CONSENT_VERSION,
    AskPeteDirectService,
)


PREVIEW_OWNER_USER_KEY = "preview-owner-user-key"
PREVIEW_HEADER = "X-PeerSlate-Preview"
PREVIEW_HEADER_VALUE = "fixture-in-memory"
RESUME_PATH = "/petec/resume"
INBOX_PATH = ask_pete_direct_routes.OWNER_INBOX_PATH
DIRECT_PATH = ask_pete_direct_routes.DIRECT_QUESTION_PATH


# ---------------------------------------------------------------------------
# The fixture store. It answers the three stored procedures by contract, so the
# service above it is the real one, unmodified, running its real validation.
# ---------------------------------------------------------------------------


class InMemoryRecruiterQuestions:
    """A Python stand-in for dbo.recruiter_questions and its ledger.

    It implements the same outcomes the procedures return - including the
    per-recipient idempotency namespace and the row_version fence - so the
    service's guards are genuinely exercised rather than bypassed. It is NOT a
    substitute for the migration's own proof: that is the disposable-database
    gate (see SCHEMA_GATE_RUNBOOK.md).
    """

    def __init__(self, recipient_user_key: str) -> None:
        self.recipient_user_key = recipient_user_key
        self.rows: list[dict] = []
        self.ledger: dict[tuple[str, str], int] = {}
        self._version = 0x4D2
        self._seed()

    # -- helpers ---------------------------------------------------------

    def _next_version(self) -> bytes:
        self._version += 1
        return self._version.to_bytes(8, "big")

    def _add(
        self,
        question: str,
        contact: str | None,
        *,
        status: str = "new",
        age_hours: int = 0,
    ) -> dict:
        now = datetime.now(timezone.utc) - timedelta(hours=age_hours)
        row = {
            "recruiter_question_key": str(uuid4()),
            "question_status": status,
            "question_text": question,
            "contact_text": contact,
            "consent_version": CONSENT_VERSION,
            "created_at_utc": now,
            "status_changed_at_utc": None if status == "new" else now,
            "row_version": self._next_version(),
        }
        self.rows.append(row)
        return row

    def _seed(self) -> None:
        """Two questions shaped like the real thing: one unread with contact
        details, one already read with none, so the empty-contact state and the
        status chips are both visible without sending anything."""
        self._add(
            "Ask Pete could not tell me whether Pete has personally owned a "
            "supplier integration end to end. Has he, and roughly what scale?",
            "Dana Reyes, Northwind Talent - dana@example.com - 555 0163",
            status="new",
            age_hours=3,
        )
        self._add(
            "We are hiring a systems lead in Denver. Would Pete consider "
            "relocating, and what would he want to know first?",
            None,
            status="read",
            age_hours=52,
        )

    def _find(self, question_key: str) -> dict | None:
        for row in self.rows:
            if row["recruiter_question_key"] == question_key:
                return row
        return None

    # -- the database_service surface the service calls ------------------

    def execute_procedure(self, procedure_name, parameters=None):
        bound = dict(parameters or [])
        if procedure_name == "usp_ListRecruiterQuestionsForOwner":
            if bound.get("@UserKey") != self.recipient_user_key:
                return [[], [{"total_count": 0, "new_count": 0}]]
            include_archived = bound.get("@IncludeArchived") == 1
            rows = [
                row
                for row in self.rows
                if include_archived or row["question_status"] != "archived"
            ]
            rows.sort(key=lambda row: row["created_at_utc"], reverse=True)
            counts = {
                "total_count": len(rows),
                "new_count": sum(1 for row in rows if row["question_status"] == "new"),
            }
            return [[dict(row) for row in rows[:200]], [counts]]
        row = self.first_row(procedure_name, parameters)
        return [[row]] if row else [[]]

    def first_row(self, procedure_name, parameters=None):
        bound = dict(parameters or [])

        if procedure_name == "usp_SubmitRecruiterQuestion":
            if bound.get("@ConsentGiven") != 1:
                raise AssertionError(
                    "The procedure THROWs without consent; the service should "
                    "never have reached it."
                )
            if bound.get("@OwnerUserKey") != self.recipient_user_key:
                return {"outcome": "not_found"}
            key = (bound["@OwnerUserKey"], bound["@IdempotencyKey"])
            if key in self.ledger:
                return {"outcome": "existing"}
            row = self._add(bound["@QuestionText"], bound.get("@ContactText"))
            self.ledger[key] = len(self.rows) - 1
            return {"outcome": "success"}

        if procedure_name == "usp_SetRecruiterQuestionStatusForOwner":
            if bound.get("@UserKey") != self.recipient_user_key:
                return {
                    "outcome": "changed",
                    "question_status": None,
                    "row_version": None,
                }
            row = self._find(str(bound.get("@RecruiterQuestionKey")))
            if row is None or row["row_version"] != bound.get("@ExpectedRowVersion"):
                return {
                    "outcome": "changed",
                    "question_status": None,
                    "row_version": None,
                }
            row["question_status"] = bound["@Status"]
            row["status_changed_at_utc"] = datetime.now(timezone.utc)
            row["row_version"] = self._next_version()
            return {
                "outcome": "success",
                "question_status": row["question_status"],
                "row_version": row["row_version"],
            }

        raise AssertionError(f"The preview does not stub {procedure_name}.")


# ---------------------------------------------------------------------------
# The deterministic grounded answer. Same schema the real runtime returns, with
# handoff.available true so the private question form is reachable.
# ---------------------------------------------------------------------------


def _locator(section, anchor, record_kind, record_id):
    return {
        "section": section,
        "anchor": anchor,
        "record_kind": record_kind,
        "record_id": record_id,
        "highlight_key": f"{record_kind}:{record_id}",
    }


def preview_answer_payload(question: str) -> dict:
    """The fixture answer is deliberately shaped like the live recruiter
    brief that motivated the 2026-08-09 redesign - several claims, multiple
    citations, one partially-supported nuance, one boundary - so the folded
    layout is reviewed against a realistic answer, not a two-claim stub."""
    role = _locator("experience", "r2-exp-card-northrop", "career_role", "northrop")

    def _evidence(text, excerpt, source_title):
        return {
            "kind": "evidence",
            "state": "supported",
            "support_label": "Supported",
            "text": text,
            "limitation": None,
            "citations": [
                {"excerpt": excerpt, "source_title": source_title, "locator": role}
            ],
        }

    return {
        "schema_version": "ask-pete-public-answer.v1",
        "answer_id": "preview-fixture-answer",
        "purpose": "recruiter_brief",
        "state": "partially_supported",
        "support_label": "Partially supported",
        # The question is echoed into the summary so two answers in a row are
        # visibly different - which is what makes "Back to previous answer"
        # reviewable by eye, and checkable by the browser assertions below.
        "summary": (
            "LOCAL PREVIEW FIXTURE, not a real answer, so the folded answer, "
            "the private question form, and the answer ordering can be "
            f"reviewed without calling a provider. You asked: {question}"
        ),
        "claims": [
            _evidence(
                "Pete led cross-functional systems work across product, "
                "hardware, and software teams.",
                "Brought product, hardware, and software teams together to "
                "define a system architecture.",
                "Systems engineering experience",
            ),
            _evidence(
                "Pete has run supplier and integration programmes at "
                "organisational scale.",
                "Coordinated supplier deliverables and integration "
                "milestones across the programme.",
                "Systems engineering experience",
            ),
            _evidence(
                "Pete has owned requirements and verification through full "
                "delivery cycles.",
                "Owned requirements decomposition and verification closure "
                "for the delivered system.",
                "Systems engineering experience",
            ),
            _evidence(
                "Pete has led reviews and design decisions with senior "
                "stakeholders.",
                "Presented design decisions and trade studies at "
                "programme-level reviews.",
                "Systems engineering experience",
            ),
            {
                "kind": "interpretation",
                "state": "supported",
                "support_label": "Supported",
                "text": (
                    "Taken together, the records read as a systems leader "
                    "comfortable owning ambiguity across team boundaries."
                ),
                "limitation": None,
                "citations": [
                    {
                        "excerpt": (
                            "Brought product, hardware, and software teams "
                            "together to define a system architecture."
                        ),
                        "source_title": "Systems engineering experience",
                        "locator": role,
                    }
                ],
            },
            {
                "kind": "evidence",
                "state": "partially_supported",
                "support_label": "Partially supported",
                "text": (
                    "Pete's records show programme-level financial exposure, "
                    "though not direct budget ownership."
                ),
                "limitation": (
                    "The approved records name contract figures Pete worked "
                    "within; they do not establish direct P&L ownership."
                ),
                "citations": [
                    {
                        "excerpt": (
                            "Coordinated supplier deliverables and "
                            "integration milestones across the programme."
                        ),
                        "source_title": "Systems engineering experience",
                        "locator": role,
                    }
                ],
            },
            {
                "kind": "boundary",
                "state": "not_established",
                "support_label": "Not established publicly",
                "text": (
                    "Pete's approved public information does not answer this "
                    "part of the question."
                ),
                "limitation": None,
                "citations": [],
            },
        ],
        "follow_up_questions": [
            "What did Pete own personally on that programme?",
            "Which parts would he want to talk through directly?",
        ],
        "handoff": {
            "available": True,
            "reason": "not_established",
            # The companion prefills the private form's textarea with this.
            "question": question,
            "private": True,
            "label": "Contact Pete directly",
            "href": "/petec/contact",
            "delivery_note": (
                "Nothing is sent automatically. This opens Pete's current "
                "contact options; on-platform private messaging is not live."
            ),
        },
        "sources_used": [
            {
                "source_version_key": "preview-fixture-source",
                "source_key": "preview-fixture-source",
                "title": "Systems engineering experience",
                "locator": role,
            }
        ],
        "source_summary": {
            "used_count": 1,
            "label": "Used in this answer: 1 public record",
            "show_all_on_resume": True,
        },
        "context": {"context_key": None, "manifest_id": "preview-fixture"},
    }


def _preview_answer(**kwargs):
    """Stands in for services.ask_pete.runtime.answer_public_question.

    app.py calls it and returns ``result.payload``, so a SimpleNamespace with
    that one attribute is the whole contract. No provider, no network, no
    spend - and because ANTHROPIC_API_KEY is a placeholder, a real call could
    not succeed even if one were attempted.
    """
    question = kwargs.get("question") or "Ask Pete directly about this."
    return SimpleNamespace(payload=preview_answer_payload(question))


# ---------------------------------------------------------------------------
# Wiring
# ---------------------------------------------------------------------------


def configure_preview_app(owner_user_key: str = PREVIEW_OWNER_USER_KEY):
    """Return ``(app, store)`` with the blueprint registered and the flag on."""
    app = app_module.app

    # --- THE REGISTRATION, AND THE FLAG --------------------------------
    # Since the registration leg (2026-08-08) app.py already does the first
    # line, so this is now a no-op in practice - and the guard is what lets
    # this harness go on working either way rather than raising on a second
    # registration of the same blueprint name. It is kept rather than deleted
    # so the harness still stands alone if it is ever pointed at an
    # application that has not registered the blueprint.
    #
    # The flag is the part that matters here now: production leaves it off,
    # and this preview turns it on in-process only.
    if "ask_pete_direct" not in app.blueprints:
        app.register_blueprint(ask_pete_direct_routes.ask_pete_direct)
    app.config["PEERSLATE_ASK_PETE_DIRECT_ENABLED"] = True
    # -------------------------------------------------------------------

    app.config.update(
        PEERSLATE_ASK_PETE_GROUNDED_ENABLED=True,
        # Preview-only: a signed-in owner without an identity database.
        PEERSLATE_ALLOW_DEV_IDENTITY=True,
        PEERSLATE_DEV_USER_KEY=owner_user_key,
        PEERSLATE_OWNER_USER_KEYS=owner_user_key,
        PEERSLATE_OWNER_EMAILS="",
        # Keep the preview quiet and predictable.
        PEERSLATE_TRUST_EASYAUTH_HEADERS=False,
    )

    store = InMemoryRecruiterQuestions(owner_user_key)
    ask_pete_direct_routes.ask_pete_direct_service = AskPeteDirectService(
        database=store
    )
    app_module.answer_public_question = _preview_answer

    if not getattr(app, "_ask_pete_direct_preview_marked", False):
        @app.after_request
        def _mark_preview(response):  # noqa: ANN001
            response.headers[PREVIEW_HEADER] = PREVIEW_HEADER_VALUE
            return response

        app._ask_pete_direct_preview_marked = True

    return app, store


def choose_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def banner(base_url: str) -> str:
    return "\n".join(
        (
            "",
            "=" * 72,
            "  PS-ASK-PETE-DIRECT-001 LOCAL PREVIEW - FIXTURE DATA, NO PROVIDER",
            "=" * 72,
            "  Recruiter view : " + base_url + RESUME_PATH,
            "                   Ask anything, then open 'Send this question to",
            "                   Pete privately' inside the gold handoff card.",
            "  Owner inbox    : " + base_url + INBOX_PATH,
            "                   Two fixture questions; anything you send from",
            "                   the resume page appears here on refresh.",
            "",
            "  No database. No migration applied. No AI provider called.",
            "  Every response carries " + PREVIEW_HEADER + ": " + PREVIEW_HEADER_VALUE + ".",
            "  State lives in this process only and dies with it.",
            "",
            "  Ctrl-C to stop.",
            "=" * 72,
            "",
        )
    )


# ---------------------------------------------------------------------------
# --check: prove it boots and both surfaces answer, headlessly
# ---------------------------------------------------------------------------


def _get(url: str) -> tuple[int, str, dict]:
    request = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return (
                response.status,
                response.read().decode("utf-8", errors="replace"),
                dict(response.headers),
            )
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8", errors="replace"), dict(error.headers)


def _post_json(url: str, payload: dict, headers: dict) -> tuple[int, str]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8", errors="replace")


def run_check(base_url: str, store: InMemoryRecruiterQuestions) -> int:
    checks: list[tuple[str, bool, str]] = []

    def check(label: str, ok: bool, detail: str = "") -> None:
        checks.append((label, bool(ok), detail))

    status, html, headers = _get(base_url + RESUME_PATH)
    check("resume answers 200", status == 200, f"status={status}")
    check(
        "companion is rendered",
        "data-ask-pete-companion" in html,
        "the grounded flag is on",
    )
    check(
        "the private path is advertised to the client",
        "data-ask-pete-direct-config" in html,
        "flag-on template block",
    )
    check(
        "the advertised endpoint matches the blueprint",
        f'data-ask-pete-direct-endpoint="{DIRECT_PATH}"' in html,
        DIRECT_PATH,
    )
    check(
        "the companion script and stylesheet are linked",
        "ask-pete-evidence-companion.js" in html
        and "ask-pete-resume-evidence.css" in html,
    )
    check(
        "preview marker header is present",
        headers.get(PREVIEW_HEADER) == PREVIEW_HEADER_VALUE,
    )

    status, body = _post_json(
        base_url + "/api/chat",
        {"message": "Has Pete owned a supplier integration end to end?"},
        {},
    )
    answer = json.loads(body) if status == 200 else {}
    check("/api/chat answers 200 from the fixture", status == 200, f"status={status}")
    check(
        "the answer carries a handoff, so the form is reachable",
        bool(answer.get("handoff", {}).get("available")),
    )

    before = len(store.rows)
    idempotency_key = str(uuid4())
    status, body = _post_json(
        base_url + DIRECT_PATH,
        {
            "question": "Preview check: can Pete talk through the Denver role?",
            "contact": "Preview Check <check@example.invalid>",
            "consent": True,
        },
        {
            "X-PeerSlate-Request": "same-origin",
            "Origin": base_url,
            "Sec-Fetch-Site": "same-origin",
            "Idempotency-Key": idempotency_key,
        },
    )
    check("a consented question is stored (201)", status == 201, f"status={status}")
    check("exactly one question was added", len(store.rows) == before + 1)

    status, replay = _post_json(
        base_url + DIRECT_PATH,
        {
            "question": "Preview check: can Pete talk through the Denver role?",
            "contact": "Preview Check <check@example.invalid>",
            "consent": True,
        },
        {
            "X-PeerSlate-Request": "same-origin",
            "Origin": base_url,
            "Sec-Fetch-Site": "same-origin",
            "Idempotency-Key": idempotency_key,
        },
    )
    check("a replayed key reports already_sent (200)", status == 200, f"status={status}")
    check(
        "the replay stored nothing extra",
        len(store.rows) == before + 1,
        json.loads(replay).get("state", "") if replay else "",
    )

    status, body = _post_json(
        base_url + DIRECT_PATH,
        {"question": "Refused: no consent given.", "consent": False},
        {
            "X-PeerSlate-Request": "same-origin",
            "Origin": base_url,
            "Sec-Fetch-Site": "same-origin",
            "Idempotency-Key": str(uuid4()),
        },
    )
    check("consent is required (422)", status == 422, f"status={status}")
    check("the refusal stored nothing", len(store.rows) == before + 1)

    status, inbox, headers = _get(base_url + INBOX_PATH)
    check("owner inbox answers 200", status == 200, f"status={status}")
    check(
        "both fixture questions are shown",
        "Northwind Talent" in inbox and "hiring a systems lead in Denver" in inbox,
    )
    check("the sent question arrived in the inbox", "Denver role?" in inbox)
    check(
        "the inbox is hardened",
        headers.get("Cache-Control") == "private, no-store"
        and headers.get("X-Robots-Tag") == "noindex, nofollow, noarchive",
    )
    check("the inbox offers no delete control", 'value="delete"' not in inbox)

    browser_checks, browser_note = run_browser_checks(base_url)
    checks.extend(browser_checks)

    print("\nPS-ASK-PETE-DIRECT-001 preview check\n" + "-" * 44)
    for label, ok, detail in checks:
        mark = "PASS" if ok else "FAIL"
        suffix = f"  ({detail})" if detail else ""
        print(f"  [{mark}] {label}{suffix}")
    failed = [label for label, ok, _ in checks if not ok]
    print("-" * 44)
    if browser_note:
        print(browser_note)
    if failed:
        print(f"{len(failed)} check(s) FAILED: {', '.join(failed)}")
        return 1
    print(f"All {len(checks)} checks passed. No provider call, no database.")
    return 0


# ---------------------------------------------------------------------------
# Browser checks. These are the only way to verify the two things Pete
# reported, because both are client behaviour: where the rail is scrolled after
# an answer arrives, and whether a previous answer can be returned to. Skipped
# with an honest note when Playwright is not installed - never silently.
# ---------------------------------------------------------------------------

FIRST_QUESTION = "Give me Pete's 60-second recruiter brief."
SECOND_QUESTION = "Which parts of that programme did Pete own personally?"

# How far the answer's top may sit from the rail's top and still count as "the
# recruiter is looking at the answer". A few pixels of sub-pixel rounding and
# smooth-scroll settling, not a whole heading.
ANSWER_TOP_TOLERANCE_PX = 6

RAIL_GEOMETRY_SCRIPT = """() => {
    const scroller = document.querySelector('.ask-pete-evidence-companion__scroll');
    const companion = document.querySelector('[data-ask-pete-companion]');
    const answer = document.querySelector('[data-ask-pete-answer]');
    const summary = document.querySelector('.ask-pete-evidence-answer__summary');
    const fold = document.querySelector('.ask-pete-evidence-fold');
    const foldBody = document.querySelector('.ask-pete-evidence-fold__body');
    const handoff = document.querySelector('.ask-pete-evidence-handoff');
    const input = document.querySelector('[data-ask-pete-input]');
    const box = (element) => (element ? element.getBoundingClientRect() : null);
    const scrollerBox = box(scroller);
    const answerBox = box(answer);
    const summaryBox = box(summary);
    const companionBox = box(companion);
    const inputBox = box(input);
    return {
        scrollTop: scroller ? scroller.scrollTop : null,
        scrollable: Boolean(scroller && scroller.scrollHeight > scroller.clientHeight + 1),
        answerOffset: scrollerBox && answerBox ? answerBox.top - scrollerBox.top : null,
        summaryOffset: scrollerBox && summaryBox ? summaryBox.top - scrollerBox.top : null,
        summaryVisible: Boolean(
            scrollerBox && summaryBox
            && summaryBox.top >= scrollerBox.top - 1
            && summaryBox.top < scrollerBox.bottom
        ),
        summaryBeforeFold: Boolean(
            summaryBox && box(fold) && summaryBox.top < box(fold).top
        ),
        summaryBeforeHandoff: Boolean(
            summaryBox && box(handoff) && summaryBox.top < box(handoff).top
        ),
        summaryText: summary ? summary.textContent : '',
        backCount: document.querySelectorAll('[data-ask-pete-back]').length,
        foldCollapsed: Boolean(foldBody && foldBody.hidden),
        metaBadgeCount: document.querySelectorAll('.ask-pete-evidence-answer__meta .ask-pete-support-badge').length,
        supportedCardBadgeCount: document.querySelectorAll('.ask-pete-evidence-claim--supported .ask-pete-support-badge').length,
        boundaryCardCount: document.querySelectorAll('.ask-pete-evidence-claim--boundary').length,
        composerDocked: Boolean(
            companionBox && inputBox
            && inputBox.top >= companionBox.top
            && inputBox.bottom <= companionBox.bottom + 1
        ),
    };
}"""


def run_browser_checks(base_url: str):
    """Return ``(checks, note)``. Never raises for a missing browser."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return [], (
            "  NOTE: Playwright is not installed, so the two CLIENT-side\n"
            "        behaviours Pete reported (answer-first scroll, back to\n"
            "        previous answer) were NOT verified by this run."
        )

    checks: list[tuple[str, bool, str]] = []

    def check(label: str, ok: bool, detail: str = "") -> None:
        checks.append((label, bool(ok), detail))

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            try:
                # Wide enough for the flagship rail (the narrow sheet begins at
                # 90rem = 1440px), and deliberately SHORT enough that the rail
                # must scroll. A tall viewport fits the whole compact answer and
                # would make the scroll assertions vacuous - it is exactly the
                # laptop-height case where Pete hit the problem.
                page = browser.new_page(viewport={"width": 1600, "height": 720})
                errors: list[str] = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(base_url + RESUME_PATH, wait_until="domcontentloaded")
                page.locator("[data-ask-pete-companion]").wait_for(state="attached")

                # --- first answer, from a starter -------------------------
                page.locator('[data-ask-pete-starter="recruiter_brief"]').click()
                summary = page.locator(".ask-pete-evidence-answer__summary")
                summary.wait_for(state="visible", timeout=10_000)
                page.wait_for_timeout(700)  # let a smooth scroll settle

                first = page.evaluate(RAIL_GEOMETRY_SCRIPT)
                check(
                    "the rail actually scrolls at this viewport",
                    first["scrollable"],
                    "otherwise the scroll assertions below prove nothing",
                )
                check(
                    "after an answer the rail is scrolled to the answer",
                    first["answerOffset"] is not None
                    and abs(first["answerOffset"]) <= ANSWER_TOP_TOLERANCE_PX,
                    f"answer top {first['answerOffset']}px from rail top",
                )
                check("the summary is in view", first["summaryVisible"])
                check(
                    "the summary precedes the folded evidence and the contact entry",
                    first["summaryBeforeFold"] and first["summaryBeforeHandoff"],
                )
                # Pete's 2026-08-09 redesign, verified in a real browser.
                check("the evidence is folded until asked for", first["foldCollapsed"])
                check(
                    "one trust line; no badge on an established claim",
                    first["metaBadgeCount"] == 1
                    and first["supportedCardBadgeCount"] == 0,
                )
                check("no boundary card is rendered", first["boundaryCardCount"] == 0)
                check(
                    "the ask box stays on screen below the answer",
                    first["composerDocked"],
                )
                check(
                    "no back control before there is anything to go back to",
                    first["backCount"] == 0,
                )

                # --- second answer, from the bottom of a scrolled rail -----
                # This reproduces exactly what Pete hit: type in the composer
                # (which puts the rail at its bottom), then ask.
                page.locator("[data-ask-pete-input]").fill(SECOND_QUESTION)
                page.evaluate(
                    """() => {
                        const scroller = document.querySelector('.ask-pete-evidence-companion__scroll');
                        scroller.scrollTop = scroller.scrollHeight;
                    }"""
                )
                before = page.evaluate(RAIL_GEOMETRY_SCRIPT)
                check(
                    "the reproduction starts from a rail scrolled to its bottom",
                    (before["scrollTop"] or 0) > 0,
                    f"scrollTop={before['scrollTop']}",
                )
                # Scoped to the composer: the private question form reuses the
                # same attribute as a styling hook.
                page.locator("[data-ask-pete-form] [data-ask-pete-submit]").click()
                page.wait_for_function(
                    """expected => {
                        const summary = document.querySelector('.ask-pete-evidence-answer__summary');
                        return Boolean(summary && summary.textContent.includes(expected));
                    }""",
                    arg=SECOND_QUESTION,
                    timeout=10_000,
                )
                page.wait_for_timeout(700)

                second = page.evaluate(RAIL_GEOMETRY_SCRIPT)
                check(
                    "a second answer also reads from the top, not its tail",
                    second["answerOffset"] is not None
                    and abs(second["answerOffset"]) <= ANSWER_TOP_TOLERANCE_PX,
                    f"answer top {second['answerOffset']}px from rail top",
                )
                check("the second summary is in view", second["summaryVisible"])
                check(
                    "the back control appears once a prior answer exists",
                    second["backCount"] == 1,
                )

                # --- back, and back again ---------------------------------
                page.locator("[data-ask-pete-back]").click()
                page.wait_for_function(
                    """expected => {
                        const summary = document.querySelector('.ask-pete-evidence-answer__summary');
                        return Boolean(summary && summary.textContent.includes(expected));
                    }""",
                    arg=FIRST_QUESTION,
                    timeout=5_000,
                )
                restored = page.evaluate(RAIL_GEOMETRY_SCRIPT)
                check(
                    "the back control restores the previous answer",
                    FIRST_QUESTION in restored["summaryText"],
                )
                check(
                    "the restored answer also reads from the top",
                    restored["answerOffset"] is not None
                    and abs(restored["answerOffset"]) <= ANSWER_TOP_TOLERANCE_PX,
                    f"answer top {restored['answerOffset']}px from rail top",
                )
                check(
                    "using it never destroys the newer answer",
                    restored["backCount"] == 1,
                )

                page.locator("[data-ask-pete-back]").click()
                page.wait_for_function(
                    """expected => {
                        const summary = document.querySelector('.ask-pete-evidence-answer__summary');
                        return Boolean(summary && summary.textContent.includes(expected));
                    }""",
                    arg=SECOND_QUESTION,
                    timeout=5_000,
                )
                check("it returns to the newer answer as well", True)
                check("no page error was raised", not errors, "; ".join(errors[:2]))
            finally:
                browser.close()
    except Exception as error:  # noqa: BLE001 - reported, never swallowed
        checks.append(("browser checks completed", False, f"{type(error).__name__}: {error}"))

    return checks, ""


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="Boot, exercise both surfaces headlessly, print the result, exit.",
    )
    parser.add_argument(
        "--port", type=int, default=0, help="Bind a specific port instead of a free one."
    )
    arguments = parser.parse_args(argv)

    app, store = configure_preview_app()
    port = arguments.port or choose_port()
    base_url = f"http://127.0.0.1:{port}"

    from werkzeug.serving import make_server

    server = make_server("127.0.0.1", port, app, threaded=True)

    if not arguments.check:
        print(banner(base_url))
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nPreview stopped. Nothing was persisted.")
        finally:
            server.server_close()
        return 0

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        return run_check(base_url, store)
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


if __name__ == "__main__":
    raise SystemExit(main())
