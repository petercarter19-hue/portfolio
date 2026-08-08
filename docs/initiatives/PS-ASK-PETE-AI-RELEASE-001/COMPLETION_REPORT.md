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

> The "Not touched" and "no AI path" statements above describe the **app-seam
> slice only**. The lane record was later amended to add `services/ask_pete/`
> and the prompt contract for the evidenced release-blocker corrections; those
> slices do change the AI path and are recorded in their own sections below and
> in `README.md`.

---

## Addendum — excerpt-discipline correction (2026-08-08)

Second evidenced release-blocker slice, after the fence/truncation slice at
`49f5d8a`. Same package, same delivery path (**Bounded** — an established seam
inside the already-amended `services/ask_pete/` surface; no new trust boundary,
and `services/ai_foundation/` remains unmodified).

- **Outcome:** With parsing fixed, two of three real-provider questions failed
  on `citation excerpt does not occur in its approved source` — the model
  copied real source words but stitched them across newlines and field labels,
  so the cited string was never a contiguous substring. Two changes: the prompt
  now states the contiguous character-for-character copying rule, and
  `AnthropicGroundedProvider.answer` makes exactly one corrective retry that
  quotes the contract error and the offending excerpts back to the model.
  **Site effect today: none.** The grounded path is held closed by
  `PEERSLATE_ASK_PETE_GROUNDED_ENABLED=false`.

- **Branch, base SHA, changed paths:**
  - Branch: `work/2026-08-08-ask-pete-release-001`
  - Base SHA for this slice: `49f5d8aa0ab6006ab686fe9e7c414f6dbe262fce`
  - Final SHA: the commit carrying this record; it cannot name itself here.
  - Changed paths:
    - `services/ask_pete/provider.py`
    - `prompts/ask_pete/grounded_public_v1.md`
    - `tests/ask_pete/test_provider_corrective_retry.py` (new)
    - `tests/ask_pete/test_provider_response_shape.py`
    - `docs/initiatives/PS-ASK-PETE-AI-RELEASE-001/README.md`
    - `docs/initiatives/PS-ASK-PETE-AI-RELEASE-001/COMPLETION_REPORT.md`
  - Not touched: `services/ai_foundation/`, `app.py`, `templates/`, `static/`,
    `azure-pipelines.yml`, SQL, governance files, and every test outside
    `tests/ask_pete/`.

- **Verification performed and result:**

  | Command | Result |
  |---|---|
  | `python -m pytest tests/ask_pete/ -q` | **82 passed, 49 subtests passed** (69 before this slice; 13 added, none deleted, skipped, or weakened) |
  | `python -m pytest tests/ -q` | **2953 passed, 5 skipped, 3670 subtests passed** (68 s) |

  Run from the package worktree with the primary checkout's interpreter and
  `ANTHROPIC_API_KEY=test-key`. **No real API call was made from this lane.**

  The four scenarios the correction turns on are asserted by call count, not by
  outcome alone: a stitched excerpt recovered on the retry (exactly two calls),
  two refusals failing closed (exactly two, and the *second* error is the one
  that propagates), a transport failure on the first call (exactly one), and a
  first-attempt success (exactly one). The provider double raises a
  `BaseException` subclass on an unscripted third call, so a third call cannot
  be swallowed by the adapter's transport handler and mis-read as an honest
  degradation.

- **Release state:** **local only** — committed on the package branch, not
  pushed, no PR, no pipeline run, not merged, not deployed, not enabled.

- **Known limits and owner decisions needed:**
  1. **Unverified against the real provider.** The tests prove the adapter asks
     correctly and stops correctly. Whether the live model actually complies
     with the correction is a real-provider question this lane cannot answer,
     and the RELEASE EVIDENCE section now has a field for it.
  2. **Wall clock.** The 30 s bound is per attempt and there may be two, so the
     worst case is 60 s against the browser's 45 s abort. It requires a
     complete-but-refused reply arriving at nearly 30 s, which is unlikely
     rather than impossible. A total wall-clock budget for the pair is the
     available mitigation and is an owner decision, not one taken here.
  3. **Cost.** A refused question can now cost two generations, and the retry
     re-sends the whole request document.
  4. **Truncation is retryable.** This deliberately revises the earlier
     one-call stance recorded in `test_provider_response_shape.py`; the
     rationale and the revised test are in `README.md`.
  5. **The trace cannot report the attempt count.** `AITrace` has no field for
     it and `services/ai_foundation/` is outside this surface, so nothing was
     added and nothing was overloaded. Recorded as a stated limitation.

- **Next action:** Fable review of the branch diff, then orchestrator review
  and an Azure DevOps PR. Real-provider verification of the grounded path,
  including whether citations resolve and whether a corrective retry was made,
  must pass before any redeploy. Enablement remains a separate Protected
  decision under `PS-OPS-001` and is not requested here.

---

## Addendum — prompt calibration to the enforced numbers (2026-08-08)

Third evidenced release-blocker slice, after the excerpt-discipline slice at
`a26ccfb`. Still **Bounded**. **Prompt and tests only — no code changed.**

- **Outcome:** Live verification of the previous slice, run by the orchestrator
  outside this lane, passed 2 of 5 real-provider cases and failed 3 on numbers
  the model was never given. `evidence_finder` (9 claims, 9 verified citations)
  and a general question (4 claims, 7 citations) confirm the excerpt discipline
  works. Two cases failed `answer.follow_up_question exceeds 300 characters` —
  a `codec.py` ceiling the prompt never stated, which no corrective retry can
  fix because the bound was still invisible on the retry. One case failed
  `summary_below_minimum_words` — that bound *was* stated, but the compactness
  paragraph never said a purpose floor outranks brevity, so the model shortened
  below it. The prompt now quotes every number `codec.py`, `quality.py`, and
  `evaluation.py` enforce, and states that compactness never overrides a
  purpose requirement. **Site effect today: none** — the flag holds the
  grounded path closed.

- **Branch, base SHA, changed paths:**
  - Branch: `work/2026-08-08-ask-pete-release-001`
  - Base SHA for this slice: `a26ccfb`
  - Final SHA: the commit carrying this record; it cannot name itself here.
  - Changed paths:
    - `prompts/ask_pete/grounded_public_v1.md`
    - `tests/ask_pete/test_prompt_states_the_enforced_numbers.py` (new)
    - `docs/initiatives/PS-ASK-PETE-AI-RELEASE-001/README.md`
    - `docs/initiatives/PS-ASK-PETE-AI-RELEASE-001/COMPLETION_REPORT.md`
  - Not touched: **all of `services/`**, `app.py`, `templates/`, `static/`,
    `azure-pipelines.yml`, SQL, governance files, and every test outside
    `tests/ask_pete/`.

- **Verification performed and result:**

  | Command | Result |
  |---|---|
  | `python -m pytest tests/ask_pete/ -q` | **93 passed, 69 subtests passed** (82 before this slice; 11 added, none deleted, skipped, or weakened) |
  | `python -m pytest tests/ -q` | **2964 passed, 5 skipped, 3690 subtests passed** |

  Run from the package worktree with the primary checkout's interpreter and
  `ANTHROPIC_API_KEY=test-key`. **No real API call was made from this lane**;
  the live results above were reported into it by the orchestrator.

  The new tests assert a correspondence rather than a wording: they build the
  exact recruiter brief the prompt now describes, assert
  `validate_product_quality` accepts it, then step one below each stated floor
  and assert the matching refusal identifier. The decoder ceilings are asserted
  against the imported `codec.py` constants. A prompt number that stops
  matching the server therefore fails in this suite, not in production.

- **Release state:** **local only** — committed on the package branch, not
  pushed, no PR, no pipeline run, not merged, not deployed, not enabled.

- **Known limits and owner decisions needed:**
  1. **Correction 5 is unverified against the real provider.** The 2/5 run
     predates it. A fresh five-case run is required, and the RELEASE EVIDENCE
     section now carries a per-purpose field for it.
  2. **The corrective retry was left generic.** It quotes the contract error
     and the offending excerpts but adds no purpose-specific coaching for a
     length or count failure. That should be unnecessary now that the first
     attempt has the numbers; if a fresh run still shows length failures
     surviving the retry, teaching the corrective message to restate the
     violated bound is the next step. Not taken here — this round was scoped to
     the prompt.
  3. **The prompt is longer.** Four additions cost input tokens on every
     grounded call. The trade is deliberate: the numbers are server-enforced,
     and a refused answer costs a full generation plus a retry.
  4. **`public_profile_answer` has no quality expectation**, and the prompt now
     says so explicitly. If a floor is ever added for that purpose in
     `quality.py`, that sentence becomes false; the new suite pins the numbers
     that are stated but cannot detect a floor nobody stated.

- **Next action:** Fable review, then a fresh five-case real-provider run
  covering all four purposes before any redeploy.

---

## Addendum — correcting the last two failures (2026-08-08)

Fourth evidenced release-blocker slice, after the prompt-calibration slice at
`1a4d667`. Still **Bounded**. Code and tests inside `services/ask_pete/`;
`services/ai_foundation/` remains unmodified.

- **Outcome:** Live round 3, reported into this lane by the orchestrator,
  passed **3 of 5** — general-1 fixed by the stated numbers (summary 114
  words), general-2 and `evidence_finder` solid. The two remaining failures had
  one shape in common: each refusal happened somewhere the correction could not
  reach. `interview_preparation` failed
  `answer.follow_up_question exceeds 300 characters`; that error is raised by
  `codec.py` inside the *gateway*, after the provider has returned, so the
  corrective retry could never address it — and the message it did send never
  named the field or the limit. `recruiter_brief` failed
  `boundary_claim_required`, raised by `quality.py` after the gateway finishes,
  past the provider entirely. The adapter now decodes its own finished answer
  so a decoder bound is refused inside the attempt, the corrective message
  restates the violated field and limit, and the service takes exactly one
  fresh sample when the product quality contract refuses. **Site effect today:
  none** — the flag holds the grounded path closed.

- **Deviation from the brief, stated plainly.** Instruction 1 asked only that
  `_corrective_message` restate a codec bound. Implemented literally that would
  have been **dead code**: no codec error can occur inside the provider,
  because `parse_grounded_answer` runs in `AIFoundationGateway.answer` after
  `AnthropicGroundedProvider.answer` returns. Making the instruction real
  required also moving *when* the decode happens, so the adapter now decodes
  its own answer before returning it. Nothing is loosened, repaired, or
  re-classified — same function, same object, same error, same message — and
  the gateway decodes again and stays the authority. This is the one judgment
  in this slice that goes beyond the brief's literal wording, and it is flagged
  rather than folded in.

- **Branch, base SHA, changed paths:**
  - Branch: `work/2026-08-08-ask-pete-release-001`
  - Base SHA for this slice: `1a4d667`
  - Final SHA: the commit carrying this record; it cannot name itself here.
  - Changed paths:
    - `services/ask_pete/provider.py`
    - `services/ask_pete/service.py`
    - `tests/ask_pete/test_provider_corrective_retry.py`
    - `tests/ask_pete/test_service_quality_resample.py` (new)
    - `docs/initiatives/PS-ASK-PETE-AI-RELEASE-001/README.md`
    - `docs/initiatives/PS-ASK-PETE-AI-RELEASE-001/COMPLETION_REPORT.md`
  - Not touched: `services/ai_foundation/`, `prompts/`, `app.py`, `templates/`,
    `static/`, `azure-pipelines.yml`, SQL, governance files, and every test
    outside `tests/ask_pete/`.

- **Verification performed and result:**

  | Command | Result |
  |---|---|
  | `python -m pytest tests/ask_pete/ -q` | **106 passed, 69 subtests passed** (93 before this slice; 13 added, none deleted, skipped, or weakened) |
  | `python -m pytest tests/ -q` | **2977 passed, 5 skipped, 3690 subtests passed** (68 s) |

  Run from the package worktree with the primary checkout's interpreter and
  `ANTHROPIC_API_KEY=test-key`. **No real API call was made from this lane.**

  The bounds are asserted by round count, with doubles that raise a
  `BaseException` subclass on an unscripted extra round so an over-run cannot
  be swallowed and mis-read as a degradation: a recoverable shortfall recovered
  in exactly 2 gateway rounds, a persistent one failing closed at exactly 2, a
  first-time pass costing exactly 1, and grounding failures, unavailable
  providers, and no-contract purposes each costing exactly 1. On the provider
  side, the restated limit is proven to come from the refusal rather than from
  a hardcoded number by refusing a 600-character excerpt bound and asserting
  the sentence says 600, not 300.

- **Release state:** **local only** — committed on the package branch, not
  pushed, no PR, no pipeline run, not merged, not deployed, not enabled.

- **Known limits and owner decisions needed:**
  1. **The quality resample is blind.** `AIRequest` has no feedback field, so
     the second sample cannot be told what was missing. It is a bet on sampling
     variance, not a correction. Whether it recovers a live
     `boundary_claim_required` is unproven; the tests prove the service asks
     once more and stops.
  2. **Four provider calls is the ceiling, 1 is typical.** Provider retry (≤2)
     × quality rounds (≤2). Documented in `_answer_and_validate`.
  3. **Worst-case latency ~120 s against a 45 s browser abort.** The server
     stays inside its own bounds but can finish an answer nobody is waiting
     for. Needs three late refusals in a row; not observed. A total wall-clock
     budget across the chain is the mitigation and is an owner decision.
  4. **The adapter decodes twice** — once itself, once in the gateway. Pure
     function, negligible cost, accepted for the retry it enables.
  5. **Still no attempt count in the trace.** A resampled question emits two
     `AITrace` records with the same `request_id`; that is the only signal an
     operator has.
  6. **Correction 6 is unverified live.** Round 3 predates it. A round 4 across
     all five cases is required before any redeploy.

- **Next action:** Fable review, then a round-4 real-provider run across all
  five cases. Enablement remains a separate Protected decision under
  `PS-OPS-001` and is not requested here.

---

## Addendum — one resample for the whole model-output class (2026-08-08)

Fifth convergence slice, after `7f14cd7`. Still **Bounded**.
`services/ai_foundation/` remains unmodified.

- **Outcome:** Live round 4 held at 3 of 5 — general-1, general-2 and
  `evidence_finder` have now passed three rounds running. The two remaining
  failures moved to a third validation layer: `recruiter_brief` on
  `interpretations must state their inferential boundary` and
  `interview_preparation` on `a supported answer may contain only supported
  claims`, both `GroundingValidationError` from `citation_validator.py` inside
  `AIFoundationGateway.answer` — past the provider's corrective retry, and not
  an `AskPeteResponseError`, so correction 6's resample missed them. The
  resample is now keyed on `RESAMPLED_REFUSALS` (`AskPeteResponseError`,
  `GroundingValidationError`, `AnswerContractError`), and the prompt states the
  grounding rules the way it already states the numbers. **Site effect today:
  none** — the flag holds the grounded path closed.

- **The taxonomy is now covered end to end.** Four rounds walked it one layer
  at a time: excerpt resolution (provider), decoder bounds (gateway, pulled
  into the provider by correction 6), product quality (service), and grounding
  (gateway). Every layer that judges the model's own output is now either
  corrected in place or resampled once. What is deliberately never resampled —
  transport, authorization, execution limits, manifest integrity — is pinned by
  a test asserting set membership rather than by comment alone.

- **Branch, base SHA, changed paths:**
  - Branch: `work/2026-08-08-ask-pete-release-001`
  - Base SHA for this slice: `7f14cd7`
  - Final SHA: the commit carrying this record; it cannot name itself here.
  - Changed paths:
    - `services/ask_pete/service.py`
    - `prompts/ask_pete/grounded_public_v1.md`
    - `tests/ask_pete/test_prompt_states_the_enforced_numbers.py`
    - `tests/ask_pete/test_service_quality_resample.py`
    - `docs/initiatives/PS-ASK-PETE-AI-RELEASE-001/README.md`
    - `docs/initiatives/PS-ASK-PETE-AI-RELEASE-001/COMPLETION_REPORT.md`
  - Not touched: `services/ai_foundation/`, `services/ask_pete/provider.py`,
    `app.py`, `templates/`, `static/`, `azure-pipelines.yml`, SQL, governance
    files, and every test outside `tests/ask_pete/`.

- **Verification performed and result:**

  | Command | Result |
  |---|---|
  | `python -m pytest tests/ask_pete/ -q` | **115 passed, 89 subtests passed** (106 before this slice; 9 added, none deleted, skipped, or weakened) |
  | `python -m pytest tests/ -q` | **2986 passed, 5 skipped, 3710 subtests passed** (73 s) |

  Run from the package worktree with the primary checkout's interpreter and
  `ANTHROPIC_API_KEY=test-key`. **No real API call was made from this lane.**

  Eleven grounding rules are each violated in turn and asserted to raise the
  exact validator message, and a well-formed mixed answer is asserted to pass,
  so the prompt's sentences are pinned to `citation_validator.py` rather than
  to their own wording. On the service side, grounding and decoder refusals are
  shown to resample once and then fail closed at exactly 2 rounds, and an
  execution-limit refusal is shown to cost exactly 1 round — counted by emitted
  traces, because that refusal never reaches the provider.

- **Release state:** **local only** — committed on the package branch, not
  pushed, no PR, no pipeline run, not merged, not deployed, not enabled.

- **Known limits and owner decisions needed:**
  1. **Correction 7 is unverified live.** Round 4 predates it; a round 5 is
     required before any redeploy.
  2. **The resample is still blind** and still bounded at 2 rounds / 4 provider
     calls, with the same ~120 s worst case against the browser's 45 s abort.
     Widening the resampled class widens how many paths can reach that ceiling,
     not the ceiling itself.
  3. **A prompt that states a rule is not a model that follows it.** Each round
     has shown a newly stated rule being obeyed in the next round; that is
     evidence, not a guarantee. If round 5 surfaces a fifth failing layer, the
     thing to examine is the validation taxonomy itself rather than another
     one-off correction.

- **Next action:** Fable review, then a round-5 real-provider run across all
  five cases. Enablement remains a separate Protected decision under
  `PS-OPS-001` and is not requested here.

## Live real-provider verification (orchestrator, 2026-08-08)

Five convergence rounds against the real provider from the exact candidate
tree, each round fixing the failure class it exposed:
1. Round 1 (deployed ee5ee842, flag briefly on): 0% — fenced JSON + 1,600-token
   truncation; flag returned off (rollback proven live).
2. Round 2: parsing fixed; excerpt stitching failed 2/3.
3. Round 3 (excerpt discipline + corrective retry): 3/5 — size/word bounds
   unknown to the model.
4. Round 4 (server numbers stated in prompt): 3/5 — grounding-layer rules
   uncovered (interpretation boundaries, state consistency).
5. Round 5 (full taxonomy covered — corrective retry + widened resample +
   stated grounding rules): **6/6 PASS**, including two recruiter briefs with
   full flagship contract (partially_supported, boundary, handoff, 100–140
   word summaries) and interview preparation.

Latency observed round 5: 6.7–28.4 s typical; 63.8 s worst (one recovered
retry chain) — beyond the 45 s browser abort, shown to the visitor as the
honest retry UI; accepted limitation, recorded. Ceiling 4 provider calls per
question; typical 1.
