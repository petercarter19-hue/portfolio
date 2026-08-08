# PS-ASK-PETE-AI-READINESS-002 — Completion Record

Implementation-end record. Merge, pipeline, and live facts are not filled in
because none has occurred; the orchestrator completes them at merge.

## Core record

- **Task/package and delivery path:** PS-ASK-PETE-AI-READINESS-002 — **Bounded**.
  Approved package inside the established `services/ask_pete/` architecture.
  Protected triggers were checked individually and none is crossed; the reasoning
  is recorded in `README.md` under "Why this is not a Protected change".

- **Outcome and member/site effect:** Three enablement blockers in the dormant
  grounded Ask Pete path are fixed in source. (1) The paid provider call is
  bounded to one 30 s attempt so the server gives up before the browser's 45 s
  abort instead of holding a worker and paying for an invisible generation for
  up to ten minutes. (2) A stricter product quality contract can now be selected
  only by an explicit recognized `action`, so a legacy chat visitor whose wording
  merely resembled a quick action is answered rather than losing a paid answer to
  a 502. (3) The rate limit that caps anonymous AI spend, and the flag-on legacy
  seam, are now covered by tests. **Site effect today: none.** Every changed line
  is inside `services/ask_pete/`, reachable only from the flag-on branch of
  `/api/chat`, and `PEERSLATE_ASK_PETE_GROUNDED_ENABLED` still defaults to false.

- **Branch, base SHA, final SHA, and changed paths:**
  - Branch: `work/2026-08-08-ask-pete-readiness-002`
  - Base SHA: `c10f27f3f6440dea1d4ce1e1c3b069dc459b7801` (branch point, equal to
    `origin/main` at implementation end)
  - Commits: `efe8d2f` (provider bound), `124aa86` (classification hardening),
    and a third carrying the app-seam tests and this package record. The final
    SHA is recorded by the orchestrator at merge; it cannot name itself here.
  - Changed paths:
    - `services/ask_pete/provider.py`
    - `services/ask_pete/classification.py`
    - `tests/ask_pete/test_provider_timeout.py` (new)
    - `tests/ask_pete/test_provider_and_classification.py`
    - `tests/ask_pete/test_service.py`
    - `tests/ask_pete/test_public_eval_catalog.py`
    - `tests/ask_pete/public_eval_cases.json`
    - `tests/ask_pete/test_app_compatibility.py`
    - `docs/initiatives/PS-ASK-PETE-AI-READINESS-002/README.md` (new)
    - `docs/initiatives/PS-ASK-PETE-AI-READINESS-002/COMPLETION_REPORT.md` (new)
  - Not touched: `app.py`, `templates/`, `static/`, `azure-pipelines.yml`,
    `services/ai_foundation/`, `prompts/`, `data/ai_sources/`,
    `static/data/resume_data.json`, and every other lane's files.

- **Verification performed and result:**

  | Command | Before | After |
  |---|---|---|
  | `python -m pytest tests/ask_pete/ -q` | 40 passed | **58 passed, 26 subtests passed** |
  | `python -m pytest tests/ai_foundation/ -q` | 36 passed | **36 passed** (read-only dependency, unchanged) |

  Run from the package worktree with the primary checkout's interpreter and
  environment. No existing test was deleted, skipped, or weakened.

  Each fix was mutation-checked by reverting only the production change and
  confirming the new tests fail for the right reason:
  - Unbinding the provider call → 3 targeted failures on the missing `timeout`
    kwarg and the missing `with_options` bound.
  - Restoring keyword classification → 15 failures, including
    `test_the_same_wording_without_an_action_answers_instead_of_failing` and the
    end-to-end seam test, which fails with the exact production symptom
    (`Grounded Ask Pete answer failed validation`, HTTP 502).

  SDK mechanics were verified empirically against the installed anthropic
  0.112.0 before the code relied on them — `timeout` is a `messages.create`
  keyword, `max_retries` is not, `with_options` returns a copy that shares the
  HTTP connection pool and leaves the original client's `max_retries` at 2, and
  the SDK does retry `APITimeoutError`. Those facts are pinned by
  `InstalledSdkContractTests` so an SDK upgrade that changes them fails a test
  rather than silently removing the bound.

- **Release state:** **local only** — committed on the package branch, not
  pushed, no PR, no pipeline run, not merged, not deployed, not enabled. No live
  behavior is claimed.

- **Known limits, deferred work, or owner decision needed:**
  1. **The 429 body is HTML on an otherwise-JSON route.** `app.py` has no 429
     error handler, so a rate-limited `/api/chat` request returns Flask-Limiter's
     HTML page with no `Retry-After`. `chatbot.js` tolerates it, so no visitor
     sees a broken state, but a JSON client does not get the shape it expects.
     Fixing it means editing `app.py`, outside this package's writable surface.
     Pinned by a characterization test so the gap stays visible.
  2. **`PS-ASK-PETE-AI-001`'s "byte-identical when flag-off" claim is now
     narrower than it reads.** Azure PR 320's malformed-body hardening — before
     and independent of this package — turned HTML 415/400 and a 500 into JSON
     400s for malformed bodies. An improvement, recorded truthfully, not altered
     here.
  3. **Two evaluation cases were edited.** `measurable-results` and
     `mbse-and-requirements` in `tests/ask_pete/public_eval_cases.json` carried a
     `context_key` with `requested_action: null` — a shape no client sends, since
     only the resume companion sends a context and it always sends an action.
     They now name `evidence_finder`, which keeps their strict expectations
     intact rather than lowering them. A new catalog invariant prevents the drift
     from recurring. This is the one change a reviewer should confirm they accept
     as a correction rather than a relaxation.
  4. **30 s is a judgment, not a measurement.** It is bounded above by the
     browser's 45 s abort and leaves room for source assembly and serialization.
     No production latency distribution for this path exists yet, because the
     path has never been enabled. Worth revisiting with real data after any
     enablement.
  5. **The timeout is not proven end-to-end against the live API.** Tests prove
     the bound is passed and that a timeout degrades correctly; they do not
     exercise a real network stall. That is an enablement-time observation, not
     a unit test.

- **Next action:** Orchestrator review of the branch, then an Azure DevOps PR.
  Enablement of `PEERSLATE_ASK_PETE_GROUNDED_ENABLED` remains a separate
  Protected release decision under `PS-OPS-001` and is not requested here.

## Protected additions

Not applicable. No identity, authorization, privacy, canonical-truth, migration,
deletion, publication, shared-infrastructure, or material-visual boundary was
crossed. The consequential-AI surface is narrowed, not widened: less visitor text
influences a server-side contract decision, and a paid call can no longer run
past the point where anyone can see it. Source authorization is untouched, and a
test now pins that all four public purposes offer an identical approved source
set, so the classification change moved no authorization boundary.
