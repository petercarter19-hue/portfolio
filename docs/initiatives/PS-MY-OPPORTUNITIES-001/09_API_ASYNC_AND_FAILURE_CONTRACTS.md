# 09 — API, async, and failure contracts

Cross-cutting mechanics every child implements identically. Doc 04 already
fixes the search-specific surfaces; this document fixes the shared anatomy.

## 1. Identifiers and versions

- All keys are opaque, non-enumerable strings (`_opaque_key` convention).
  Keys never encode owner identity, provider identity, or content.
- Every mutable row carries a concurrency token (rowversion pattern;
  `_version_token`/`_decode_version_token` conventions from
  `services/opportunity_slate_v2_service.py`). Immutable objects version by
  new-row-plus-chain (`previous_*_key`).
- Contract versioning: response payloads carry `contract_version`; additive
  evolution only within a major version; breaking change = new version with
  both served during migration (doc 13 §5).

## 2. Concurrency and idempotency

- **Optimistic concurrency everywhere a member edits**: writes require the
  read token; stale token ⇒ `409` with current state for truthful re-render —
  never a silent last-write-wins (v2's shared-rowversion refusal pattern).
- **Idempotency keys on every consequential mutation** (the criteria
  terminal commands Apply / Keep current criteria / discard — whose replay
  returns the same immutable terminal receipt, doc 04 §1a — plus interpret,
  save, remove, undo, grant create/revoke, Slate create): retries with the
  same key and same canonical input return the original outcome; the same
  key with a different canonical command/input is refused
  (`idempotency_mismatch`), per the doc 04 §1a precedence table.
  Idempotency records are content-free and TTL-bounded.
- **Double-submit discipline**: an in-flight consequential action blocks
  competing submits of the same action until success/failure/cancel (v2
  competing-submit pattern), with plain-HTML POST fallback still safe via
  idempotency keys.

## 3. Bounded async jobs

Search execution, ingestion runs, revocation recomputes, TTL sweeps, and
policy purges are bounded jobs: explicit deadline, bounded work set, recorded
outcome (complete / partial+reason / failed+reason / cancelled), safe to
re-run (idempotent over their inputs). No unbounded background loop; no job
both mutates member data and shared data in one transaction scope. Job
technology (queue/scheduler) is deliberately unselected (owner ledger:
candidates only); C9 proposes it with the operations design.

- **Retry**: system retries are bounded with backoff and always re-check
  authorization and policy at execution time (not enqueue time) and again
  before persistence/return (doc 08 §2a).
- **Cancel**: member-cancellable jobs (search) expose idempotent cancel;
  pipeline jobs cancel at safe boundaries only.

## 4. Failure anatomy (uniform response shape)

Every failure response carries: `{ failure_code (closed enum per surface),
member_message (truthful, specific, recovery-oriented), recoverable (bool),
retry_after? , current_state? (for 409s) }`.

Principles (binding, from the v2/continuation lessons):

- **Distinguish known refusal from unknown outcome.** A validation refusal or
  authorization denial states exactly what was refused. A timeout/storage
  failure after submit says the outcome is unknown, preserves the member's
  drafted input, and never promises the write did or did not land; immediate
  blind retry of unknown-outcome writes is locked until state is reloaded.
- **Authorization denial is truthful and dead-ended safely**: signed-out ⇒
  sign-in redirect with same-origin return (never a partial page);
  identity-lookup failure ⇒ truthful 503 (never treated as signed out);
  cross-owner key ⇒ not-found shape.
- **Partial failure is labeled, never silent**: reduced coverage names its
  unavailable checks; degraded retrieval names its mode; per-entry check
  failures degrade that entry only.
- Failure copy never blames the member, never invents system state, and
  always offers the safest next action.

## 5. Timeouts and long/missing fields

- Every remote call (provider fetch, AI, index query, evidence port) has an
  explicit timeout shorter than its caller's deadline; deadlines compose
  (job deadline > stage deadline > call timeout).
- Long fields: bounded validation at intake (`utf16_length` convention);
  bounded rendering with full text in the dossier detail; no layout-breaking
  overflow (doc 10 §5 long-content behavior).
- Missing fields: render truthful `Not stated` (or field omitted where the
  approved layouts show absence); never invented, never silently defaulted.
  Missing *required-for-identity* fields fail admission instead (doc 05 §3).

## 6. Degraded-mode matrix (contract-level)

| Dependency down | Member can still… | Surface truth |
|---|---|---|
| AI interpretation | search manually with full parity (doc 04 §1) | quiet notice; no dead AI chrome |
| Discovery index | search via bounded canonical path, or retry with truthful failure (doc 04 §9) | reduced-coverage/degraded disclosure |
| Evidence source/port | browse, save, view listings; assessments report `Review unavailable` | per-item alias copy; retry |
| Provider/source hosts | everything except fresh verification; listings age truthfully | could-not-reverify semantics |
| Slate (v2 surface) | everything except create/continue handoff | action disabled with truthful reason, retry |
| Database (member store) | nothing member-side — truthful 503 waking/unavailable page | the shared honest unavailable surface |

## 7. HTTP surface conventions

Signed-in HTML-first routes following the v2 blueprint idioms: flag gate →
same-origin write check → identity gate → validate → act → redirect-on-
success; enhanced `fetch`/`AbortController` behavior is progressive
enhancement, never load-bearing; `private, no-store` + noindex headers on
every member response; rate limits registered per endpoint in the app-level
table like the existing Slate entries; upload/import size overrides only on
their exact endpoints (`_allow_bounded_document_upload` pattern).
