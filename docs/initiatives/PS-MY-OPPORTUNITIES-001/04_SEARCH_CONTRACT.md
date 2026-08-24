# 04 — Search contract

The criteria/search contract for C3 (interpretation) and C4 (retrieval).
Field names are contract names; exact wire/storage naming is fixed by the
children under this contract. All endpoints are owner-scoped, same-origin,
`private, no-store` (doc 08; reuse the v2 route hardening patterns).

## 1. Interpret (natural language → visible draft; the only AI path)

Request: `{ request_text (bounded UTF-16 length), locale, timezone,
existing_draft_key?, existing_draft_version_token?, parent_snapshot_key?,
idempotency_key }`

Response: `{ draft_key, draft_version_token, criteria[], verification_scope,
direct_filters, interpretation_provenance, parent_snapshot_key?,
clarification? }`

- **Token rule:** interpreting **into an existing draft** requires that
  draft's current `draft_version_token` (stale ⇒ `409 stale_draft`, nothing
  mutated); creating a **new** draft requires none.
- **Post-result natural-language refinement** is this same explicit
  interpretation command with `parent_snapshot_key` set to the current
  applied snapshot: it visibly creates a **new** draft seeded from that
  snapshot, and the applied snapshot and its results remain untouched until
  a later explicit Apply (doc 03 §3). AI is used only here; every §1a
  command is deterministic.

- `criteria[]`: ordered structured criteria `{ criterion_key, kind
  (role_family | arrangement | compensation_floor | domain | location |
  free_text_term | …extensible), display_label, value, source
  (ai | member | manual) }`. The UI renders these as the visible, editable
  chips (e.g. `Product leadership +3`).
- `clarification` is present only when the request is **materially ambiguous**:
  `{ clarification_key, question, options[] (none preselected), scope }`.
  A clear request receives none. At most one focused clarification at a time.
- AI unavailable ⇒ `interpretation_provenance: manual_required` and an empty
  criteria proposal; the member builds criteria directly through the same
  surface (`Edit criteria`, `All filters`). Parity rule: everything the AI can
  set, the member can set manually, and vice versa.
- Idempotency: `interpret` carries a required `idempotency_key` whose
  identity covers the **complete canonical input** — request text,
  new-vs-existing draft, the existing draft key and its version token when
  present, `parent_snapshot_key`, locale/timezone, and every other
  interpretation input. Replaying the same key with the same canonical
  input returns the original response; identical text against a different
  snapshot (or any other input difference) is a different identity and
  must not collide — same key with different canonical input is
  `409 idempotency_mismatch`, nothing mutated (§1a precedence).

## 1a. Complete draft command set (deterministic)

Owner-scoped, one concurrency contract with two command classes:

- **Live-draft mutations** (`edit_draft`, `answer_clarification`,
  `dismiss_clarification`) consume the current `draft_version_token`,
  **rotate** it, and return the full live draft state with the new token.
- **Terminal commands** (`apply`, `keep_current_criteria`, `discard_draft`)
  consume the current token and return an **immutable terminal receipt** —
  never a new live token; the draft has no live state afterward.
- **Refusal/replay precedence (one table; evaluated top-down; no refusal
  ever mutates anything):**

| # | Condition | Outcome |
|---|---|---|
| a | Same `idempotency_key` + same canonical command and input | The **original receipt/result** is returned — even when the token has since been consumed by that very command |
| b | Same `idempotency_key` reused for a different canonical command or different canonical input | `409 idempotency_mismatch` |
| c | Consumed token (draft is terminal) with a new/different key | `409 terminal_draft`, carrying the terminal receipt/status — **not** `stale_draft`, and no "current live state" is fabricated |
| d | Stale live token on a **non-terminal** draft with a new/different key | `409 stale_draft`, carrying the current live state |
| e | Any refusal above | Nothing mutated |

- Structured refinement is deterministic; AI exists only in the §1
  interpretation path. Direct/manual parity holds: with AI unavailable,
  every §1a command works identically, and `create_draft` + `edit_draft`
  reproduce anything interpretation could set.

| Command | Class | Request | Response |
|---|---|---|---|
| `create_draft` (manual start) | creation | `{ idempotency_key }` (no token — no draft exists yet) | `{ draft_key, draft_version_token, empty criteria, verification_scope: both, provenance: manual }`; idempotent within window |
| `edit_draft` | live mutation | `{ draft_key, draft_version_token, operations[] (set/remove criterion, set verification_scope, set/clear direct filter), idempotency_key }` | full live draft + rotated token; operations validated as a set — partial application never occurs (covers `Edit criteria` and `All filters`) |
| `answer_clarification` | live mutation | `{ draft_key, draft_version_token, clarification_key, selected_option_key }` | full live draft + rotated token; clarification closed; nothing preselected; unknown/expired `clarification_key` is a refusal, not a guess |
| `dismiss_clarification` | live mutation | `{ draft_key, draft_version_token, clarification_key }` | draft unchanged except clarification closed; rotated token |
| `refine_from_results` (structured post-result) | creation | `{ snapshot_key (current applied), operations[], idempotency_key }` | **new** `{ draft_key, draft_version_token, parent_snapshot_key }` seeded from the applied snapshot; applied snapshot/results untouched. Natural-language post-result refinement is §1 `interpret` with `parent_snapshot_key` |
| `keep_current_criteria` | terminal | `{ draft_key, draft_version_token, idempotency_key }` | terminal receipt `{ draft_key, outcome: discarded, receipt_at }`; applied snapshot/results untouched |
| `discard_draft` | terminal | `{ draft_key, draft_version_token, idempotency_key }` | terminal receipt `{ draft_key, outcome: discarded, receipt_at }` (pre-search equivalent of keep-current) |
| `apply` | terminal | `{ draft_key, draft_version_token, idempotency_key }` | terminal receipt `{ draft_key, outcome: applied, snapshot_key, execution_key, receipt_at }` — §2; the only path to execution |

State-machine binding: these commands implement the doc 03 §3 transitions
one-to-one (`interpret`/`create_draft`/`refine_from_results` →
draft_visible; `answer_clarification`/`dismiss_clarification` → clarifying
exits; `edit_draft` → draft_visible loop; `keep_current_criteria`/
`discard_draft` → discarded terminal; `apply` → applied terminal). C3 owns
all of them (doc 14).

## 2. Apply (explicit; the only way search executes)

Request: `{ draft_key, draft_version_token, idempotency_key }`

Response: the immutable `apply` terminal receipt
`{ draft_key, outcome: applied, snapshot_key, execution_key, receipt_at }`
(§1a terminal class).

- Server freezes the draft into an immutable `applied_criteria_snapshot`
  (chained via `previous_snapshot_key`) and starts one `search_execution`.
- Stale `draft_version_token` ⇒ `409 stale_draft` with the current draft state;
  nothing executes. Replaying the same `idempotency_key` ⇒ the original
  receipt (same `execution_key`), not a second run.
- Pre-conditions: the member has seen the draft (Apply is only reachable from
  a rendered draft); an open clarification blocks Apply until answered or
  dismissed.

## 3. Execution status and results

`GET status(execution_key)` → `{ state (doc 03 §4), stages[], coverage
(full | reduced | degraded), unavailable_checks[], cancellable }`

`GET results(result_key | execution_key, cursor?, page_size)` →

```text
{ result_key, snapshot_key, coverage (full | reduced),
  completeness (complete | partial — §11), disclosures[],
  total_qualified, total_broader,
  entries[]: { entry_key, opportunity_key, requirement_version_key,
               governing_source_version_key (the exact result-time basis),
               display_attribution_refs (field → source_version_key
                 references per doc 03 §9.6 — references, never copied
                 source facts),
               gate_outcome (fully_verified | not_fully_verified),
               required_summary { verified, not_established, appears_unmet,
                                  review_unavailable, total },
               preferred_summary { verified, total },
               display_projection (title, employer, location, arrangement,
                                   compensation as stated, freshness — all
                                   from the governing source version with
                                   field-level attribution, doc 03 §9.6) },
  next_cursor?, previous_cursor? }
```

- **Stable result identity**: `result_key` and `entry_key` are immutable.
  Pagination and restoration read the stored snapshot; they never re-query.
  A snapshot may age (see §8) but never silently changes.
- Ordering inputs are stored on the snapshot entry server-side for
  explainability and audit; they are **excluded from serialization** to the
  browser and never rendered as any kind of score.
- `disclosures[]` carries coverage truth (`reduced coverage: <named checks>
  unavailable`, source-set limitations) for the UI to render verbatim
  (approved reduced-coverage state).
- No relevance score, match probability, percentage, or employer prediction
  appears in any response field. `ordering_inputs` is internal and excluded
  from serialization to the browser (fence-checked like the Search 3F
  serializer, which constructs public fields explicitly and never copies the
  index candidate).

## 4. Ordering and tie-breaking (one total chain; deterministic)

Two partitions, never mixed: the *qualified* set (`fully_verified`) and the
separately labeled *broader* set (`not_fully_verified`; approved
no-fully-verified states). Within each partition, **exactly one total
ordering chain** applies — every permitted signal at an exact position, with
direction and null handling; nothing else may influence order, and paid
relevance does not exist anywhere:

Qualified set:

1. verified-preferred count — descending; absent/none = 0;
2. internal retrieval relevance score — descending; **only when the index
   path served this execution** (canonical-path executions have no score);
   null/absent sorts lowest; never serialized to the browser, never
   member-facing, never purchasable;
3. governing head's `last_successfully_verified_at` (doc 03 §9.3) —
   descending; null sorts oldest;
4. posting date — descending; null sorts oldest;
5. `opportunity_key` — ascending lexicographic (total order; no ties
   remain).

Broader set (owner-neutral by construction): the broader order uses **only
already-authorized signals** —

1. internal retrieval relevance score — descending; index-path executions
   only; null/absent sorts lowest; internal-only, never member-facing,
   never purchasable;
2. governing head's `last_successfully_verified_at` — descending; null
   sorts oldest;
3. posting date — descending; null sorts oldest;
4. `opportunity_key` — ascending lexicographic (total order; no ties
   remain).

It deliberately uses **no verified-preferred count** — the accepted
preferred-qualification authority orders *qualifying* roles only, after the
required gate — and **no `appears_unmet` count or any known-unmet signal**,
because the treatment of known-unmet roles in broader views is Pete's open
owner decision (doc 15 §3); that decision, when made, may explicitly amend
this order. Nothing here hides it inside implementation.

Direct-filter parity: the chain is identical for AI-interpreted and manual
executions. Restoration renders the order frozen in the snapshot (§§3, 6);
re-ordering never happens on read.

## 5. Pagination, ceilings, cancellation

- Cursor-based (`next_cursor`/`previous_cursor` opaque, snapshot-bound).
  Page size bounded (default 20, max 50).
- Ceilings (pattern: Search 3F pre-dispatch ceilings): per-execution retrieval
  ceiling, per-member concurrent-execution ceiling (one active; a new explicit
  Apply supersedes the previous execution, cancel-and-replace), daily
  execution budget (observability, doc 12). Exceeding a ceiling is a truthful
  refusal, not silent truncation; results are never capped at a fiction
  (no `1–4 of 6`).
- `POST cancel(execution_key)`: idempotent; cancellation never yields a
  partial snapshot.

## 6. Restoration and fresh-visit rule

- A normal visit starts fresh: no applied state is restored merely because it
  existed (preserved V3 rule). Explicitly saved searches or an intentional
  resume action restore a named `snapshot_key` + `result_key` pair, rendered
  with its age (§8).
- Browser back/refresh within one session may re-render the last
  `result_key` (server-held, owner-scoped) without re-execution.

## 7. Locale and timezone

- All stored timestamps UTC. Requests carry IANA timezone for display
  computation server-side or explicit client-side formatting — one choice per
  implementation, tested both DST sides. Posting/freshness dates render
  relative + absolute; compensation renders as stated by the source with its
  currency, never converted or normalized silently.

## 8. Stale snapshots

A `result_snapshot` older than the staleness horizon (default 24h; final
threshold with the freshness owner decision) renders with an age disclosure
and an offered re-run (a *new* explicit Apply of the same snapshot criteria —
which creates a new snapshot). Individual entries whose listing left `current`
render their truthful lifecycle overlay (changed/closed/unreachable) without
being deleted from the historical snapshot. Restoration always renders each
entry from its bound result-time basis (`governing_source_version_key` +
`display_attribution_refs`, §3): a later non-requirement source change can
never rewrite an old result, and referenced content since removed under
rights renders as unavailable (doc 05 §8), never substituted with newer
facts.

## 9. Degraded modes (all leave direct/manual search usable)

| Condition | Behavior |
|---|---|
| AI interpretation unavailable | §1 manual parity; the surface, chips, scope, filters, Apply all work; no separate "AI mode" is lost because none exists. |
| Discovery index unavailable (if index topology accepted) | Bounded canonical-store retrieval path with reduced ordering richness, disclosed as reduced coverage; or truthful `failed(index_unavailable)` with retry if the bounded path is also unavailable. Canonical truth lives outside the index (Search 3F pattern), so no member data or truth is lost. |
| Non-essential per-entry check unavailable | Execution completes; affected assessments are `Review unavailable`; coverage=reduced with named checks. |
| Provider/source outage during verification | Listing-level `unreachable` handling (doc 03 §1); entries render could-not-reverify truth. |
| Interrupted search | Doc 03 §4; the member can simply Apply again. |
| Long/missing fields | Bounded rendering with truthful `not stated` for missing facts; no invented values; oversized fields truncated with full text available in the dossier detail. |

## 10. Fencing (index topology only)

Before any index-derived entry is emitted, a local fence re-validates it
against canonical truth: opportunity exists, is `current`, governing version
matches, `data_class` matches the request context (fixture vs production),
and the schema/enum shape is exactly expected — the Search 3F local-fence
census pattern. Fence failures drop the entry and emit a content-free
observability event; they never surface index-only data.

## 11. Partial executions

A `search_execution` may terminate `partial` (stage timeout, provider/index
failure mid-run, budget/ceiling exhaustion after admission began). The
contract:

- **Immutable partial snapshot.** A partial termination writes a normal
  immutable `result_snapshot` marked `completeness: partial` with a closed
  reason enum (`timeout` | `provider_failure` | `index_failure` |
  `budget_exhausted` | `assessment_persistence_failure`) and stage-level
  detail in `disclosures[]`. It contains **only fully evaluated, fully
  backed entries** — entries whose every reported per-item state is backed
  by a durable assessment row (including durable `Review unavailable`
  rows); an entry whose assessment row could not be persisted is excluded
  entirely (doc 08 §2a), and its exclusion is what makes the execution
  `partial(assessment_persistence_failure)`. Nothing half-assessed or
  unbacked is ever included.
- **Cancellation is different**: member cancellation persists no snapshot at
  all (doc 03 §4). Partial is a system outcome, not a member action.
- **Member-facing truth**: rendered with an explicit partial label, the
  reason, and count truth — totals present as "at least N"; no invented
  counts or completeness implication.
- **Pagination/restoration**: cursors and restoration work over a partial
  snapshot exactly as over a complete one (immutable, frozen order, §6
  rules; §8 staleness applies identically).
- **Retry is a new Apply**: re-running is a new explicit Apply (same or new
  criteria) creating a new execution and snapshot. A partial snapshot is
  never mutated, extended, or "resumed".
- **Idempotency**: the originating Apply's `idempotency_key` continues to
  return this execution and its partial snapshot; it never triggers a silent
  re-run.
- Observability records the partial reason content-free (doc 12); the
  assessing-stage assessments already durably written under doc 08 §2a
  remain valid member truth regardless of the execution's terminal state.
