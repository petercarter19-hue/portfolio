"""Deterministic local browser evidence for PS-ASK-PETE-AI-001.

Run from the repository root or a linked worktree with a configured project Python environment.

The package README documents the local-venv-first interpreter discovery command.

The harness starts a local flag-gated Flask process, intercepts only POST
/api/chat with synthetic schema-valid responses, writes package-local browser
evidence, and terminates the local process in all cases. It never calls an AI
provider, production endpoint, or persistent store.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from copy import deepcopy
from pathlib import Path
from typing import Any

from playwright.sync_api import Browser, Page, Route, sync_playwright


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_DIR = ROOT / "docs" / "initiatives" / "PS-ASK-PETE-AI-001" / "browser-evidence"
CHROME_PATH = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
READY_TIMEOUT_SECONDS = 25


def locator(
    section: str,
    anchor: str,
    record_kind: str,
    record_id: str,
    highlight_key: str,
) -> dict[str, str]:
    return {
        "section": section,
        "anchor": anchor,
        "record_kind": record_kind,
        "record_id": record_id,
        "highlight_key": highlight_key,
    }


ROLE_LOCATOR = locator(
    "experience",
    "r2-exp-card-northrop",
    "career_role",
    "northrop",
    "career_role:northrop",
)
SKILL_LOCATOR = locator(
    "skills",
    "r2-skill-panel-mbse",
    "skill",
    "mbse",
    "skill:mbse",
)
ACHIEVEMENT_LOCATOR = locator(
    "credentials",
    "r2-credential-record-achievement-burdick",
    "achievement",
    "burdick",
    "achievement:burdick",
)


def structured_payload(context_key: str | None = None) -> dict[str, Any]:
    """Return a browser-only payload that satisfies the public JS contract."""

    return {
        "schema_version": "ask-pete-public-answer.v1",
        "purpose": "recruiter_brief",
        "state": "partially_supported",
        "support_label": "Supported by approved public information",
        "summary": (
            "This synthetic local brief demonstrates the public evidence "
            "companion without representing a provider or live answer."
        ),
        "claims": [
            {
                "kind": "evidence",
                "state": "supported",
                "support_label": "Supported",
                "text": "Public evidence identifies systems-engineering work in the current role.",
                "limitation": None,
                "citations": [
                    {
                        "source_title": "Northrop Grumman systems engineering role",
                        "excerpt": "Requirements decomposition, traceability, and systems engineering execution.",
                        "locator": ROLE_LOCATOR,
                    }
                ],
            },
            {
                "kind": "evidence",
                "state": "supported",
                "support_label": "Supported",
                "text": "Public evidence documents applied MBSE and requirements traceability.",
                "limitation": None,
                "citations": [
                    {
                        "source_title": "MBSE public skill evidence",
                        "excerpt": "Model-based systems engineering and architecture alignment.",
                        "locator": SKILL_LOCATOR,
                    }
                ],
            },
            {
                "kind": "boundary",
                "state": "not_established",
                "support_label": "Not established publicly",
                "text": "Current classified and proprietary program details are not public.",
                "limitation": "The approved public record does not establish those details.",
                "citations": [
                    {
                        "source_title": "Public recognition evidence",
                        "excerpt": "Recognition is available as an exact approved public record.",
                        "locator": ACHIEVEMENT_LOCATOR,
                    }
                ],
            },
        ],
        "source_summary": {
            "label": "Used in this answer: 3 approved public records",
            "used_count": 3,
            "show_all_on_resume": True,
        },
        "sources_used": [
            {
                "title": "Northrop Grumman systems engineering role",
                "locator": ROLE_LOCATOR,
            },
            {
                "title": "MBSE public skill evidence",
                "locator": SKILL_LOCATOR,
            },
            {
                "title": "Public recognition evidence",
                "locator": ACHIEVEMENT_LOCATOR,
            },
        ],
        "follow_up_questions": [
            "How does Pete connect requirements and architecture?",
            "How has Pete led across technical stakeholders?",
        ],
        "handoff": {
            "available": True,
            "question": "Can Pete discuss details that are not public?",
            "label": "Contact Pete directly",
        },
        "context": {"context_key": context_key} if context_key else None,
    }


def unavailable_payload() -> dict[str, Any]:
    payload = structured_payload()
    payload.update(
        {
            "state": "unavailable",
            "support_label": "Temporarily unavailable",
            "summary": "The synthetic provider response is unavailable.",
            "claims": [],
            "follow_up_questions": [],
            "sources_used": [],
            "source_summary": {
                "label": "No approved records were used",
                "used_count": 0,
                "show_all_on_resume": False,
            },
            "handoff": None,
        }
    )
    return payload


def critical_states_payload() -> dict[str, Any]:
    """Return a synthetic answer that exercises non-success answer treatments."""

    return {
        "schema_version": "ask-pete-public-answer.v1",
        "purpose": "evidence_finder",
        "state": "partially_supported",
        "support_label": "Partially supported by approved public information",
        "summary": "A local-only state fixture for deterministic visual evidence.",
        "claims": [
            {
                "kind": "interpretation",
                "state": "partially_supported",
                "support_label": "Partially supported",
                "text": "Public evidence supports related systems-engineering work.",
                "limitation": "The public record does not establish the exact program scope.",
                "citations": [
                    {
                        "source_title": "Northrop Grumman systems engineering role",
                        "excerpt": "Approved public systems-engineering evidence.",
                        "locator": ROLE_LOCATOR,
                    }
                ],
            },
            {
                "kind": "boundary",
                "state": "not_established",
                "support_label": "Not established publicly",
                "text": "The requested proprietary detail is not established publicly.",
                "limitation": "Ask Pete does not infer an answer from related experience.",
                "citations": [
                    {
                        "source_title": "MBSE public skill evidence",
                        "excerpt": "Approved public MBSE evidence.",
                        "locator": SKILL_LOCATOR,
                    }
                ],
            },
            {
                "kind": "interpretation",
                "state": "ambiguous",
                "support_label": "Needs clarification",
                "text": "The question could mean people, technical, or program leadership.",
                "limitation": "Ask Pete should clarify the recruiter's intended leadership lens.",
                "citations": [],
            },
        ],
        "source_summary": {
            "label": "Used in this answer: 2 approved public records",
            "used_count": 2,
            "show_all_on_resume": True,
        },
        "sources_used": [
            {"title": "Northrop Grumman systems engineering role", "locator": ROLE_LOCATOR},
            {"title": "MBSE public skill evidence", "locator": SKILL_LOCATOR},
        ],
        "follow_up_questions": [],
        "handoff": {
            "available": True,
            "question": "Can Pete clarify the public boundary directly?",
            "label": "Contact Pete directly",
        },
        "context": None,
    }


class ApiStub:
    """Provider-free response switch used by every browser assertion."""

    def __init__(self) -> None:
        self.mode = "success"
        self.post_bodies: list[dict[str, Any]] = []
        self.modes_served: list[str] = []
        self.page_errors: list[str] = []

    def handler(self, route: Route) -> None:
        if route.request.method != "POST":
            route.continue_()
            return

        body = json.loads(route.request.post_data or "{}")
        self.post_bodies.append(body)
        self.modes_served.append(self.mode)
        context_key = body.get("context_key")
        if self.mode == "success":
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(structured_payload(context_key)),
            )
            return
        if self.mode == "rate_limited":
            route.fulfill(
                status=429,
                content_type="application/json",
                body=json.dumps({"error": "Synthetic rate limit"}),
            )
            return
        if self.mode == "critical_states":
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(critical_states_payload()),
            )
            return
        if self.mode == "unverifiable":
            route.fulfill(
                status=502,
                content_type="application/json",
                body=json.dumps({"error": "Synthetic source verification failure"}),
            )
            return
        if self.mode == "malformed":
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({"response": "This payload intentionally lacks the public schema."}),
            )
            return
        if self.mode == "network":
            route.abort("failed")
            return
        if self.mode == "structured_unavailable":
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(unavailable_payload()),
            )
            return
        if self.mode == "validation":
            route.fulfill(
                status=400,
                content_type="application/json",
                body=json.dumps({"error": "Synthetic request validation failure"}),
            )
            return
        if self.mode == "context_mismatch":
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(structured_payload("skill:systems-engineering")),
            )
            return
        raise AssertionError(f"Unhandled synthetic browser mode: {self.mode}")


def choose_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def start_server() -> tuple[subprocess.Popen[bytes], str]:
    port = choose_port()
    environment = os.environ.copy()
    environment.update(
        {
            "PORT": str(port),
            "FLASK_DEBUG": "false",
            "PEERSLATE_ASK_PETE_GROUNDED_ENABLED": "true",
            "PEERSLATE_JOURNAL_ENABLED": "0",
            "ANTHROPIC_API_KEY": "browser-evidence-placeholder",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    process = subprocess.Popen(
        [sys.executable, "app.py"],
        cwd=ROOT,
        env=environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        creationflags=creationflags,
    )
    base_url = f"http://127.0.0.1:{port}"
    deadline = time.monotonic() + READY_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if process.poll() is not None:
            stderr = process.stderr.read().decode("utf-8", errors="replace") if process.stderr else ""
            raise RuntimeError(f"Local evidence server exited early: {stderr}")
        try:
            with urllib.request.urlopen(f"{base_url}/petec/resume", timeout=1) as response:
                if response.status == 200:
                    return process, base_url
        except OSError:
            time.sleep(0.2)
    process.terminate()
    raise TimeoutError("Local Ask Pete evidence server did not become ready.")


def stop_server(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=8)


def new_page(browser: Browser, base_url: str, stub: ApiStub, width: int, height: int) -> Page:
    page = browser.new_page(viewport={"width": width, "height": height})
    page.on("pageerror", lambda error: stub.page_errors.append(str(error)))
    page.route("**/api/chat", stub.handler)
    page.goto(f"{base_url}/petec/resume", wait_until="commit")
    page.locator("[data-ask-pete-companion]").wait_for(state="attached")
    page.locator("[data-ask-pete-capability]").wait_for(state="visible")
    return page


def assert_target_size(page: Page, selector: str, label: str) -> None:
    box = page.locator(selector).first.bounding_box()
    assert box is not None, f"{label} does not have a layout box"
    assert box["width"] >= 43 and box["height"] >= 43, (
        f"{label} must offer a 44px target; got {box}"
    )


def assert_resume_target_visible(page: Page, selector: str) -> None:
    target = page.locator(selector)
    target.wait_for(state="visible")
    visible = False
    for _ in range(16):
        visible = page.evaluate(
            """selector => {
                const target = document.querySelector(selector);
                const header = document.querySelector('.global-header');
                if (!target) return false;
                const rect = target.getBoundingClientRect();
                const headerHeight = header ? header.getBoundingClientRect().height : 0;
                return rect.bottom > headerHeight && rect.top < window.innerHeight;
            }""",
            selector,
        )
        if visible:
            break
        page.wait_for_timeout(120)
    assert visible, f"{selector} should be visible below the sticky header"
    assert page.evaluate("selector => document.activeElement.matches(selector)", selector), (
        f"{selector} should receive focus after source navigation"
    )


def assert_recovery_links(page: Page, *, expect_stable_answer: bool = True) -> None:
    recovery = page.locator("[data-ask-pete-recovery]")
    recovery.wait_for(state="visible")
    answer = page.locator("[data-ask-pete-answer]")
    if expect_stable_answer:
        assert answer.is_visible()
    else:
        assert answer.is_hidden()
    links = {
        link.inner_text(): link.get_attribute("href")
        for link in recovery.locator("a").all()
    }
    assert links["Continue reviewing the resume"] == "/petec/resume#resume-start"
    assert links["Open resume PDF"].startswith("/static/files/pete-carter-resume.pdf")
    assert links["Contact Pete directly"] == "/petec/contact"


def assert_flagship_answer_fits_one_wide_rail(page: Page) -> None:
    answer = page.locator("[data-ask-pete-answer]")
    assert answer.is_visible()
    assert page.locator(".ask-pete-evidence-claim").count() == 3
    assert page.locator(".ask-pete-evidence-claim--not-established").count() == 1
    assert page.locator("[data-ask-pete-followup]").count() == 2
    assert page.locator(".ask-pete-evidence-handoff a").is_visible()
    assert page.locator("[data-ask-pete-form]").is_visible()
    dimensions = page.evaluate(
        """() => {
            const scroll = document.querySelector(".ask-pete-evidence-companion__scroll");
            const composer = document.querySelector("[data-ask-pete-form]");
            const scrollRect = scroll.getBoundingClientRect();
            const composerRect = composer.getBoundingClientRect();
            return {
                clientHeight: scroll.clientHeight,
                scrollHeight: scroll.scrollHeight,
                scrollTop: scroll.scrollTop,
                composerBottom: composerRect.bottom,
                scrollBottom: scrollRect.bottom,
                children: Array.from(scroll.children).map((element) => ({
                    tag: element.tagName,
                    className: element.className,
                    height: Math.round(element.getBoundingClientRect().height),
                })),
                answerChildren: Array.from(document.querySelector("[data-ask-pete-answer]").children).map((element) => ({
                    tag: element.tagName,
                    className: element.className,
                    height: Math.round(element.getBoundingClientRect().height),
                })),
            };
        }"""
    )
    assert dimensions["scrollHeight"] <= dimensions["clientHeight"] + 1, dimensions
    assert dimensions["scrollTop"] == 0, dimensions
    assert dimensions["composerBottom"] <= dimensions["scrollBottom"] + 1, dimensions


def assert_runtime_status_visible(page: Page, phase: str, expected_text: str) -> None:
    """Prove the live, sighted request treatment before evidence-board cloning."""

    companion = page.locator("[data-ask-pete-companion]")
    status = page.locator("[data-ask-pete-status]")
    status.wait_for(state="visible")
    assert companion.get_attribute("data-ask-pete-phase") == phase
    assert status.get_attribute("role") == "status"
    assert status.get_attribute("aria-live") == "polite"
    assert expected_text in status.inner_text()
    dimensions = page.evaluate(
        """() => {
            const companion = document.querySelector("[data-ask-pete-companion]");
            const scroll = document.querySelector(".ask-pete-evidence-companion__scroll");
            const status = document.querySelector("[data-ask-pete-status]");
            if (!companion || !scroll || !status) return null;
            const companionRect = companion.getBoundingClientRect();
            const statusRect = status.getBoundingClientRect();
            const style = getComputedStyle(status);
            return {
                clientHeight: scroll.clientHeight,
                scrollHeight: scroll.scrollHeight,
                scrollTop: scroll.scrollTop,
                companion: {
                    top: companionRect.top,
                    bottom: companionRect.bottom,
                    width: companionRect.width,
                },
                status: {
                    top: statusRect.top,
                    bottom: statusRect.bottom,
                    width: statusRect.width,
                    height: statusRect.height,
                    display: style.display,
                    position: style.position,
                    overflow: style.overflow,
                    visibility: style.visibility,
                },
            };
        }"""
    )
    assert dimensions is not None
    status_dimensions = dimensions["status"]
    assert status_dimensions["width"] >= 180, dimensions
    assert status_dimensions["height"] >= 22, dimensions
    assert status_dimensions["position"] == "static", dimensions
    assert status_dimensions["overflow"] == "visible", dimensions
    assert status_dimensions["visibility"] == "visible", dimensions
    assert status_dimensions["top"] >= dimensions["companion"]["top"] - 1, dimensions
    assert status_dimensions["bottom"] <= dimensions["companion"]["bottom"] + 1, dimensions


def request_custom_question(page: Page, question: str) -> None:
    field = page.locator("[data-ask-pete-input]")
    field.fill(question)
    page.locator("[data-ask-pete-submit]").click()


def inject_contextual_request_proof(page: Page, post_count: int) -> None:
    page.evaluate(
        """count => {
            document.querySelector("[data-ask-pete-test-proof]")?.remove();
            const context = document.querySelector("[data-ask-pete-context]");
            const proof = document.createElement("p");
            proof.dataset.askPeteTestProof = "contextual-request-count";
            proof.setAttribute("aria-hidden", "true");
            proof.textContent = "Local harness proof: " + count + " POST /api/chat requests";
            Object.assign(proof.style, {
                margin: "0",
                padding: ".38rem .54rem",
                border: "1px dashed #31516a",
                borderRadius: ".45rem",
                background: "#f1f6f8",
                color: "#173f53",
                fontSize: ".72rem",
                fontWeight: "800",
            });
            context?.after(proof);
        }""",
        post_count,
    )


def check_contextual_prefill(page: Page, stub: ApiStub) -> None:
    initial_post_count = len(stub.post_bodies)
    assert initial_post_count == 0
    assert page.locator('[data-ask-pete-starter="recruiter_brief"]').is_visible()
    page.locator('[data-r2-skill-toggle="mbse"]').click()
    context_button = page.locator(
        '[data-ask-pete-context-action][data-ask-pete-context-key="skill:mbse"]'
    )
    context_button.wait_for(state="visible")
    context_button.click()
    context = page.locator("[data-ask-pete-context]")
    context.wait_for(state="visible")
    context_label = context.locator("[data-ask-pete-context-label]").inner_text()
    assert "Skills" in context_label and "MBSE" in context_label
    assert context.locator("[data-ask-pete-context-count]").inner_text() == "3 approved evidence items"
    assert page.locator("[data-ask-pete-input]").input_value().startswith("Show evidence")
    assert page.locator("[data-ask-pete-companion]").get_attribute("data-ask-pete-phase") == "context_ready"
    assert context_button.get_attribute("aria-expanded") == "true"
    assert len(stub.post_bodies) == initial_post_count
    assert page.locator("[data-ask-pete-answer]").is_hidden()
    page.locator(".ask-pete-evidence-companion__scroll").evaluate("element => { element.scrollTop = 0; }")
    page.locator("[data-ask-pete-input]").wait_for(state="visible")
    inject_contextual_request_proof(page, len(stub.post_bodies))
    proof = page.locator("[data-ask-pete-test-proof]")
    assert proof.inner_text() == "Local harness proof: 0 POST /api/chat requests"
    page.screenshot(path=EVIDENCE_DIR / "contextual-mbse.png", full_page=False)
    proof.evaluate("element => element.remove()")

    stub.mode = "context_mismatch"
    request_custom_question(page, "Confirm the selected MBSE context.")
    page.locator("[data-ask-pete-answer]").wait_for(state="visible")
    assert page.locator("[data-ask-pete-context]").is_hidden()


def check_master_source_contextual(
    browser: Browser, base_url: str, stub: ApiStub
) -> Page:
    page = new_page(browser, base_url, stub, 1536, 1024)
    try:
        check_contextual_prefill(page, stub)
        page.locator("#r2-skill-panel-mbse [data-r2-skill-close]").evaluate("element => element.click()")
        page.locator("#r2-skill-panel-mbse").wait_for(state="hidden")
        page.evaluate(
            "() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)))"
        )
        page.evaluate("window.scrollTo({ top: 0, behavior: 'auto' })")
        page.wait_for_function("window.scrollY <= 2")
        primary_starter = page.locator('[data-ask-pete-starter="recruiter_brief"]')
        assert primary_starter.is_hidden()
        stub.mode = "success"
        primary_starter.evaluate("element => element.click()")
        page.locator("[data-ask-pete-answer]").wait_for(state="visible")
        assert page.locator("[data-ask-pete-context]").is_hidden()
        assert page.locator("#r2-skill-panel-mbse").is_hidden()
        assert page.evaluate("window.scrollY") <= 2
        assert stub.post_bodies[-1] == {
            "message": "Give me Pete's 60-second recruiter brief.",
            "action": "recruiter_brief",
            "context_key": None,
        }
        companion = page.locator("[data-ask-pete-companion]")
        assert companion.get_attribute("data-ask-pete-layout") == "wide_rail"
        assert page.locator("[data-ask-pete-capability]").is_hidden()
        heading_id = page.locator(".ask-pete-evidence-answer__heading").get_attribute("id")
        assert heading_id and page.locator("[data-ask-pete-answer]").get_attribute(
            "aria-labelledby"
        ) == heading_id
        page.screenshot(path=EVIDENCE_DIR / "master-answer.png", full_page=False)
        assert_flagship_answer_fits_one_wide_rail(page)

        assert_target_size(page, "[data-ask-pete-show-all]", "Show all on resume")
        assert_target_size(page, "[data-ask-pete-followup]", "follow-up question")
        assert_target_size(page, ".ask-pete-evidence-handoff a", "human handoff")
        toggle = page.locator("[data-ask-pete-citation-toggle]").first
        assert_target_size(page, "[data-ask-pete-citation-toggle]", "citation toggle")
        toggle.click()
        assert toggle.get_attribute("aria-expanded") == "true"
        source = page.locator(".ask-pete-evidence-citation.is-expanded [data-ask-pete-source]")
        assert_target_size(page, ".ask-pete-evidence-citation.is-expanded [data-ask-pete-source]", "source open")
        source.click()
        page.locator("#r2-exp-card-northrop.ask-pete-evidence-source-selected").wait_for(
            state="visible"
        )
        assert_resume_target_visible(page, "#r2-exp-card-northrop")
        assert page.locator("[data-ask-pete-evidence-marker]").count() == 1
        page.screenshot(path=EVIDENCE_DIR / "source-open.png", full_page=False)

        request_custom_question(page, "Show another public evidence summary.")
        page.locator("[data-ask-pete-answer]").wait_for(state="visible")
        assert page.locator("[data-ask-pete-evidence-marker]").count() == 0
        page.locator("[data-ask-pete-show-all]").click()
        page.wait_for_timeout(160)
        assert page.locator("[data-ask-pete-evidence-marker]").count() == 0
        assert not page.locator("#skills").evaluate(
            "(element) => element.classList.contains('ask-pete-evidence-highlight')"
        )
        assert not page.locator("#credentials").evaluate(
            "(element) => element.classList.contains('ask-pete-evidence-highlight')"
        )


        return page
    except Exception:
        page.close()
        raise

def capture_critical_state_board(page: Page) -> None:
    """Capture asserted state treatments without representing one product state."""

    page.evaluate(
        """() => {
            const clones = window.__askPeteCriticalClones;
            if (!clones) throw new Error("Missing critical-state runtime clones.");
            document.querySelector("[data-ask-pete-test-board]")?.remove();

            const board = document.createElement("section");
            board.dataset.askPeteTestBoard = "critical-states";
            board.setAttribute("aria-hidden", "true");
            const style = document.createElement("style");
            style.textContent = [
                "[data-ask-pete-test-board] { position: fixed; inset: 0; z-index: 9999; overflow: auto; box-sizing: border-box; padding: 1.25rem; background: #dbe7df; color: #102c20; font-family: Inter, ui-sans-serif, system-ui, sans-serif; }",
                "[data-ask-pete-test-board] * { box-sizing: border-box; }",
                "[data-ask-pete-test-board] h1 { margin: 0; font-family: Newsreader, Georgia, serif; font-size: 1.9rem; }",
                "[data-ask-pete-test-board] > p { margin: .3rem 0 1rem; color: #365247; font-size: .78rem; }",
                "[data-ask-pete-test-board] .ape-test-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: .72rem; }",
                "[data-ask-pete-test-board] .ape-test-tile { min-width: 0; border: 1px solid rgba(18, 67, 48, .2); border-radius: .8rem; background: #fffefa; box-shadow: 0 .5rem 1.2rem rgba(25, 52, 42, .16); padding: .62rem; }",
                "[data-ask-pete-test-board] .ape-test-tile h2 { margin: 0 0 .45rem; color: #07513a; font-size: .72rem; letter-spacing: .08em; text-transform: uppercase; }",
                "[data-ask-pete-test-board] .ape-test-tile > p { margin: 0 0 .5rem; color: #52685d; font-size: .67rem; line-height: 1.3; }",
                "[data-ask-pete-test-board] .ask-pete-evidence-claim { padding: .48rem; }",
                "[data-ask-pete-test-board] .ask-pete-evidence-recovery { padding: .55rem; }",
                "[data-ask-pete-test-board] .ask-pete-evidence-recovery__actions a { min-height: 2rem; }",
                "[data-ask-pete-test-board] .ask-pete-evidence-handoff { padding: .5rem; }",
                "@media (max-width: 900px) { [data-ask-pete-test-board] .ape-test-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }",
            ].join("");

            const title = document.createElement("h1");
            title.textContent = "Ask Pete AI - verified critical-state treatments";
            const note = document.createElement("p");
            note.textContent = "Local deterministic evidence board. Each tile copies an asserted runtime treatment; the board is not a simultaneous production interface.";
            const grid = document.createElement("div");
            grid.className = "ape-test-grid";
            const addTile = (label, detail, node) => {
                const tile = document.createElement("article");
                tile.className = "ape-test-tile";
                const heading = document.createElement("h2");
                heading.textContent = label;
                const description = document.createElement("p");
                description.textContent = detail;
                const copy = node.cloneNode(true);
                copy.removeAttribute?.("id");
                copy.querySelectorAll?.("[id]").forEach((element) => element.removeAttribute("id"));
                tile.append(heading, description, copy);
                grid.appendChild(tile);
            };

            addTile("Loading", "A request is reviewing approved information.", clones.loading);
            addTile("Partially supported", "The supported portion and boundary remain separate.", clones.partial);
            addTile("Not established", "The assistant states what the public record cannot establish.", clones.unknown);
            addTile("Needs clarification", "An ambiguous question is not silently guessed.", clones.ambiguous);
            addTile("Temporarily unavailable", "The recruiter receives recovery paths instead of a fabricated answer.", clones.unavailable);
            addTile("Human handoff", "The existing contact path remains visible when a human answer matters.", clones.handoff);
            addTile("Source focus", "Opening a citation leaves a visible, exact evidence marker.", clones.focus);

            board.append(style, title, note, grid);
            document.body.appendChild(board);
        }"""
    )
    page.locator("[data-ask-pete-test-board]").wait_for(state="visible")
    page.screenshot(path=EVIDENCE_DIR / "critical-states.png", full_page=False)
    page.evaluate("document.querySelector('[data-ask-pete-test-board]')?.remove()")




def wait_for_layout(page: Page, layout: str) -> None:
    page.locator(f'[data-ask-pete-layout="{layout}"]').wait_for(state="attached")


def close_sheet_if_open(page: Page) -> None:
    companion = page.locator("[data-ask-pete-companion]")
    if not companion.is_hidden():
        page.locator("[data-ask-pete-close]").click()
        companion.wait_for(state="hidden")


def check_narrow_and_mobile(page: Page, stub: ApiStub) -> None:
    page.set_viewport_size({"width": 1435, "height": 1096})
    wait_for_layout(page, "narrow_sheet")
    close_sheet_if_open(page)
    trigger = page.locator(".profile-tabs__ask-btn--resume")
    trigger.click()
    page.locator("[data-ask-pete-companion]").wait_for(state="visible")
    companion = page.locator("[data-ask-pete-companion]")
    assert companion.get_attribute("data-ask-pete-layout") == "narrow_sheet"
    assert companion.get_attribute("aria-modal") is None
    page.screenshot(path=EVIDENCE_DIR / "narrow-side-sheet.png", full_page=False)
    page.keyboard.press("Escape")
    companion.wait_for(state="hidden")
    page.wait_for_function(
        "selector => document.activeElement === document.querySelector(selector)",
        arg=".profile-tabs__ask-btn--resume",
    )
    assert page.evaluate(
        "selector => document.activeElement === document.querySelector(selector)",
        ".profile-tabs__ask-btn--resume",
    )

    page.set_viewport_size({"width": 390, "height": 844})
    wait_for_layout(page, "mobile_sheet")

    trigger = page.locator(".r2-overview-mobile-ask-pete")
    trigger.click()
    assert companion.get_attribute("data-ask-pete-layout") == "mobile_sheet"
    page.screenshot(path=EVIDENCE_DIR / "mobile-bottom-sheet.png", full_page=False)
    page.locator("[data-ask-pete-citation-toggle]").first.click()
    page.locator(".ask-pete-evidence-citation.is-expanded [data-ask-pete-source]").click()
    companion.wait_for(state="hidden")
    page.locator("#r2-exp-card-northrop.ask-pete-evidence-source-selected").wait_for(
        state="visible"
    )
    assert_resume_target_visible(page, "#r2-exp-card-northrop")


def set_fetch_override(page: Page, script: str, argument: Any | None = None) -> None:
    if argument is None:
        page.evaluate(script)
    else:
        page.evaluate(script, argument)


def restore_fetch_override(page: Page) -> None:
    page.evaluate(
        """() => {
            if (window.__askPeteNativeFetch) window.fetch = window.__askPeteNativeFetch;
            if (window.__askPeteNativeTimeout) window.setTimeout = window.__askPeteNativeTimeout;
            delete window.__askPeteNativeFetch;
            delete window.__askPeteNativeTimeout;
        }"""
    )


def check_recovery_and_request_lifecycle(page: Page, stub: ApiStub) -> None:
    page.set_viewport_size({"width": 1536, "height": 1024})
    wait_for_layout(page, "wide_rail")
    expanded_citation = page.locator(
        ".ask-pete-evidence-citation.is-expanded [data-ask-pete-citation-toggle]"
    )
    if expanded_citation.count():
        expanded_citation.first.evaluate("element => element.click()")
    assert page.locator(".ask-pete-evidence-citation.is-expanded").count() == 0
    page.evaluate(
        """() => {
            window.scrollTo({ top: 0, behavior: "auto" });
            document.querySelector(".ask-pete-evidence-companion__scroll").scrollTop = 0;
        }"""
    )
    page.wait_for_function("window.scrollY <= 2")
    for mode, phase in (
        ("rate_limited", "rate_limited"),
        ("unverifiable", "unverifiable"),
        ("malformed", "unverifiable"),
        ("network", "network_error"),
        ("structured_unavailable", "unavailable"),
        ("validation", "validation_error"),
    ):
        stub.mode = mode
        request_custom_question(page, f"Exercise synthetic {mode} recovery.")
        page.locator(f'[data-ask-pete-phase="{phase}"]').wait_for(state="visible")
        assert_recovery_links(page)
        assert page.locator("[data-ask-pete-capability]").is_hidden()

    stable_answer_text = page.locator("[data-ask-pete-answer]").inner_text()
    post_count_before_client_validation = len(stub.post_bodies)
    input_field = page.locator("[data-ask-pete-input]")
    input_field.fill("")
    page.locator("[data-ask-pete-form]").evaluate("form => form.requestSubmit()")
    page.locator('[data-ask-pete-phase="validation_error"]').wait_for(state="visible")
    assert_recovery_links(page)
    assert "clearer question" in page.locator("[data-ask-pete-recovery-title]").inner_text().lower()
    assert len(stub.post_bodies) == post_count_before_client_validation
    assert page.locator("[data-ask-pete-answer]").inner_text() == stable_answer_text
    assert page.evaluate("document.activeElement === document.querySelector('[data-ask-pete-input]')")
    input_field.evaluate(
        "element => { element.value = 'x'.repeat(1001); element.dispatchEvent(new Event('input', { bubbles: true })); }"
    )
    page.locator("[data-ask-pete-form]").evaluate("form => form.requestSubmit()")
    page.locator('[data-ask-pete-phase="validation_error"]').wait_for(state="visible")
    assert_recovery_links(page)
    assert "1,000 characters" in page.locator("[data-ask-pete-recovery-message]").inner_text()
    assert len(stub.post_bodies) == post_count_before_client_validation
    assert page.locator("[data-ask-pete-answer]").inner_text() == stable_answer_text

    # These are the real companion treatments at 1536 x 1024. Assert both
    # before creating any test-only evidence-board clone so a board snapshot
    # can never conceal a visually clipped runtime status.
    set_fetch_override(
        page,
        """() => {
            window.__askPeteNativeFetch = window.fetch.bind(window);
            window.fetch = () => new Promise(() => {});
        }""",
    )
    try:
        request_custom_question(page, "Capture the live loading treatment.")
        page.locator('[data-ask-pete-phase="loading"]').wait_for(state="visible")
        assert_runtime_status_visible(
            page,
            "loading",
            "Reviewing Pete-approved public information...",
        )
        loading_status_markup = page.locator("[data-ask-pete-status]").evaluate(
            "element => element.outerHTML"
        )
        page.locator("[data-ask-pete-cancel]").click()
        page.locator('[data-ask-pete-phase="answered"]').wait_for(state="visible")
    finally:
        restore_fetch_override(page)

    stub.mode = "success"
    set_fetch_override(
        page,
        """() => {
            window.__askPeteNativeFetch = window.fetch.bind(window);
            window.fetch = (...args) => new Promise((resolve, reject) => {
                window.setTimeout(() => window.__askPeteNativeFetch(...args).then(resolve, reject), 2050);
            });
        }""",
    )
    try:
        stable_answer_text = page.locator("[data-ask-pete-answer]").inner_text()
        request_custom_question(page, "Exercise slow and cancel controls.")
        assert page.locator("[data-ask-pete-answer]").inner_text() == stable_answer_text
        page.locator('[data-ask-pete-phase="slow"]').wait_for(state="visible")
        assert_runtime_status_visible(
            page,
            "slow",
            "This is taking longer than expected.",
        )
        assert_target_size(page, "[data-ask-pete-cancel]", "cancel request")
        page.locator("[data-ask-pete-cancel]").click()
        page.locator('[data-ask-pete-phase="answered"]').wait_for(state="visible")
        restored_answer_text = page.locator("[data-ask-pete-answer]").inner_text()
        assert restored_answer_text == stable_answer_text
        page.wait_for_timeout(2200)
        assert page.locator("[data-ask-pete-answer]").inner_text() == stable_answer_text
    finally:
        restore_fetch_override(page)

    stub.mode = "critical_states"
    request_custom_question(page, "Render the critical-state evidence board.")
    page.locator('[data-ask-pete-phase="answered"]').wait_for(state="visible")
    assert page.locator(".ask-pete-evidence-claim--partially-supported").count() == 1
    assert page.locator(".ask-pete-evidence-claim--not-established").count() == 1
    assert page.locator(".ask-pete-evidence-claim--ambiguous").count() == 1
    critical_toggle = page.locator("[data-ask-pete-citation-toggle]").first
    critical_toggle.click()
    critical_source = page.locator(
        ".ask-pete-evidence-citation.is-expanded [data-ask-pete-source]"
    )
    critical_source.click()
    page.locator("[data-ask-pete-evidence-marker]").wait_for(state="visible")
    page.evaluate(
        """loading_status_markup => {
            const answer = document.querySelector("[data-ask-pete-answer]");
            const loadingTemplate = document.createElement("template");
            loadingTemplate.innerHTML = loading_status_markup;
            const loading = loadingTemplate.content.firstElementChild;
            if (!loading) throw new Error("Missing asserted live loading treatment.");
            const take = (selector) => {
                const element = document.querySelector(selector);
                if (!element) throw new Error("Missing critical-state treatment: " + selector);
                return element.cloneNode(true);
            };
            window.__askPeteCriticalClones = {
                loading,
                partial: take(".ask-pete-evidence-claim--partially-supported"),
                unknown: take(".ask-pete-evidence-claim--not-established"),
                ambiguous: take(".ask-pete-evidence-claim--ambiguous"),
                handoff: take(".ask-pete-evidence-handoff"),
                focus: take("[data-ask-pete-evidence-marker]"),
            };
            if (!answer) throw new Error("Missing critical-state answer.");
        }""",
        loading_status_markup,
    )

    stub.mode = "structured_unavailable"
    request_custom_question(page, "Capture the unavailable recovery treatment.")
    page.locator('[data-ask-pete-phase="unavailable"]').wait_for(state="visible")
    assert_recovery_links(page)
    page.evaluate(
        """() => {
            const recovery = document.querySelector("[data-ask-pete-recovery]");
            if (!recovery) throw new Error("Missing unavailable recovery.");
            window.__askPeteCriticalClones.unavailable = recovery.cloneNode(true);
        }"""
    )
    capture_critical_state_board(page)

    set_fetch_override(
        page,
        """() => {
            window.__askPeteNativeFetch = window.fetch.bind(window);
            window.__askPeteNativeTimeout = window.setTimeout.bind(window);
            window.setTimeout = (callback, delay, ...args) => window.__askPeteNativeTimeout(
                callback, delay === 45000 ? 45 : delay, ...args
            );
            window.fetch = () => new Promise(() => {});
        }""",
    )
    try:
        request_custom_question(page, "Exercise a bounded timeout recovery.")
        page.locator('[data-ask-pete-phase="timeout"]').wait_for(state="visible")
        assert_recovery_links(page)
    finally:
        restore_fetch_override(page)

    set_fetch_override(
        page,
            """payload => {
                const originalFetch = window.fetch.bind(window);
                window.fetch = (url, options) => {
                    const message = JSON.parse(options.body).message;
                    const delay = message.includes('first stale') ? 120 : 10;
                    return new Promise((resolve) => {
                        window.setTimeout(() => {
                            const result = structuredClone(payload);
                            result.summary = `Synthetic answer for ${message}.`;
                            resolve(new Response(JSON.stringify(result), {
                                status: 200,
                                headers: {'Content-Type': 'application/json'},
                            }));
                        }, delay);
                    });
                };
                window.__askPeteNativeFetch = originalFetch;
            }""",
            structured_payload(),
    )
    try:
        request_custom_question(page, "first stale answer")
        page.locator("[data-ask-pete-input]").fill("second current answer")
        page.locator("[data-ask-pete-form]").evaluate("form => form.requestSubmit()")
        page.locator("[data-ask-pete-answer]").wait_for(state="visible")
        page.wait_for_timeout(180)
        answer_text = page.locator("[data-ask-pete-answer]").inner_text().lower()
        assert "second current answer" in answer_text
        assert "first stale answer" not in answer_text
        assert page.locator("[data-ask-pete-answer]").is_visible()
    finally:
        restore_fetch_override(page)

def main() -> None:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    process, base_url = start_server()
    try:
        with sync_playwright() as playwright:
            launch_options: dict[str, Any] = {"headless": True}
            if CHROME_PATH.exists():
                launch_options["executable_path"] = str(CHROME_PATH)
            browser = playwright.chromium.launch(**launch_options)
            try:
                stub = ApiStub()
                page = check_master_source_contextual(browser, base_url, stub)
                try:
                    check_narrow_and_mobile(page, stub)
                    check_recovery_and_request_lifecycle(page, stub)
                finally:
                    page.close()
            finally:
                browser.close()
    finally:
        stop_server(process)

    print("Ask Pete deterministic browser evidence passed.")
    for name in (
        "master-answer.png",
        "source-open.png",
        "contextual-mbse.png",
        "narrow-side-sheet.png",
        "mobile-bottom-sheet.png",
        "critical-states.png",
    ):
        path = EVIDENCE_DIR / name
        assert path.is_file() and path.stat().st_size > 0, f"Missing evidence: {path}"
        print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
