# PS-ASK-PETE-AI-RELEASE-001 — Completion Record

Implementation-end record. Merge, pipeline, and live facts are deliberately
absent because none has occurred; the orchestrator fills them into
`README.md`'s RELEASE EVIDENCE section.

## Core record

- **Task/package and delivery path:** PS-ASK-PETE-AI-RELEASE-001 — **Bounded**.
  An established seam inside `app.py`'s existing error-handler and rate-limit
  architecture. Protected triggers were checked individually and none is
  crossed; the reasoning is in `README.md` under "Why this is not Protected".

- **Outcome and member/site effect:** `app.py` now registers a `429` error
  handler, so a rate-limited caller on any limited route receives
  `{"error": "Too many requests. Please wait a moment and try again."}` as
  `application/json` with a `Retry-After` header carrying the real remaining
  wait, instead of werkzeug's HTML page with no `Retry-After` and the limit
  string in its body. `PEERSLATE_ASK_PETE_GROUNDED_ENABLED=false` is now
  documented in `.env.example`. **Site effect today:** the refusal shape change
  is flag-independent and would apply on release; every route it can reach is
  either fetch-driven or behind a default-off flag, and
  `static/js/chatbot.js` keys its own `429` sentence on `response.status`, so
  no visitor-facing text changes. Nothing else in `app.py` moved — the grounded
  branch of `/api/chat` is byte-identical to `origin/main`.

- **Branch, base SHA, final SHA, and changed paths:**
  - Branch: `work/2026-08-08-ask-pete-release-001`
  - Base SHA: `f30996b033dfa261f0d3bfd14dcce0869203dffc` (branch point, equal
    to `origin/main` at implementation end)
  - Commits: `2142554` (429 JSON handler and its test), and a second carrying
    `.env.example` and this package record. The final SHA is recorded by the
    orchestrator at merge; it cannot name itself here.
  - Changed paths:
    - `app.py`
    - `tests/ask_pete/test_app_compatibility.py`
    - `.env.example`
    - `docs/initiatives/PS-ASK-PETE-AI-RELEASE-001/README.md` (new)
    - `docs/initiatives/PS-ASK-PETE-AI-RELEASE-001/COMPLETION_REPORT.md` (new)
  - Not touched: `services/`, `prompts/`, `templates/`, `static/`,
    `azure-pipelines.yml`, SQL, governance files, `workshop_*`, and every test
    outside `tests/ask_pete/`.

- **Verification performed and result:**

  | Command | Result |
  |---|---|
  | `python -m pytest tests/ask_pete/ -q` | **58 passed, 26 subtests passed** (same count as before: one characterization test was rewritten, none added or removed) |
  | `python -m pytest tests/test_http_edge_security.py tests/test_governance_pointers.py tests/ai_foundation/ -q` | **97 passed, 201 subtests passed** |
  | `python -m pytest tests/test_workshop_flows.py tests/test_workshop_work_session.py tests/test_workshop_review.py tests/test_workshop_voice.py tests/test_community_voice.py tests/test_opportunity_slate_ai.py -q` | **509 passed, 533 subtests passed** — every other module in the repository that asserts a `429` |
  | `python -m pytest tests/ -q` | **2929 passed, 5 skipped, 3647 subtests passed** (77 s) |

  Run from the package worktree with the primary checkout's interpreter. No
  existing test was deleted, skipped, or weakened.

  The `Retry-After` value was verified empirically rather than assumed: a live
  refusal returned `60`, and a second refusal three seconds later returned
  `57`, proving the header tracks the limiter's real window and is not the
  static fallback. The library mechanics it rests on were read in the installed
  `flask-limiter 4.1.1` before the code relied on them —
  `LimiterContext.view_rate_limit` is assigned before `raise RateLimitExceeded`,
  and `RateLimitExceeded.__init__` never passes `retry_after` to werkzeug's
  `_RetryAfter`, so `e.retry_after` is always `None`.

  Routes that build their own `429` payload return a response rather than
  raising, so Flask never invokes an error handler for them; their tests were
  run explicitly (row three) and are unchanged.

- **Release state:** **local only** — committed on the package branch, not
  pushed, no PR, no pipeline run, not merged, not deployed, not enabled. No
  live behavior is claimed.

- **Known limits, deferred work, or owner decision needed:**
  1. **One brief slice was stopped, not implemented.** The brief's second
     correction rested on the premise that `PublicSourceManifestError` is not
     an `AIFoundationError` and therefore produced a generic `500`. The class
     hierarchy is `PublicSourceManifestError -> AskPeteError ->
     AIFoundationError`, so the existing clause already returns a payload-free
     `502`. The slice was stopped and reported rather than improvised. The
     residual improvement — a distinct sentence for source-integrity failure at
     the same status — is an orchestrator decision. Detail and the observed
     current response are in `README.md` under "The correction that was
     stopped".
  2. **The `429` handler is app-wide by design.** A refused ordinary browser
     form post to a Workshop or Opportunity Slate route now renders JSON where
     it previously rendered werkzeug's HTML page. Both surfaces are default-off
     and fetch-driven, and the brief specified one app-wide JSON contract, so
     no negotiation on `Accept` or path prefix was added. This is the one
     change a reviewer should confirm they accept rather than a narrower,
     `/api/`-only handler.
  3. **A one-minute fallback exists and is untested end to end.** If
     `limiter.current_limit` is ever `None` or raises, the header falls back to
     `60` and the failure is logged. That branch is defensive; no test forces
     it, because forcing it means breaking the extension's own contract.
  4. **One flaky unrelated test.** The first full-suite run failed
     `tests/test_journal_frontend.py::JournalBrowserBehaviorTests::test_context_rail_has_honest_timeline_manage_empty_and_detail_behavior`,
     a browser-driven Journal test with no connection to rate limiting. It
     passed in isolation and the full suite passed clean on re-run
     (2929 passed). Recorded as observed flakiness, not fixed here — it is
     outside this package's writable surface.
  5. **`Retry-After` for long windows is honest, not capped.** Community
     publish/contribution limits are per hour, so a refusal there can return a
     header of up to ~3600 seconds. That is the true wait; capping it at 60
     would have told a caller to retry sooner than the limiter allows.

- **Next action:** Orchestrator review of the branch, a decision on the stopped
  slice, then an Azure DevOps PR. `README.md`'s RELEASE EVIDENCE section
  carries the inherited deployment finding — no automatic `batchedCI` run had
  fired for any `main` merge since pipeline 610 — which must be resolved before
  any deploy is claimed. Enablement of
  `PEERSLATE_ASK_PETE_GROUNDED_ENABLED` remains a separate Protected release
  decision under `PS-OPS-001` and is not requested here.

## Protected additions

Not applicable. No identity, authorization, privacy, canonical-truth,
migration, deletion, publication, shared-infrastructure, or material-visual
boundary was crossed. Privacy is narrowly improved: the refusal body no longer
carries the rate-limit string, and a test asserts the visitor's question is not
echoed. The `Limiter` instance is read and never mutated — no limit value,
storage backend, or key function changed — and no AI path, prompt, source
manifest, or validation rule was touched.
