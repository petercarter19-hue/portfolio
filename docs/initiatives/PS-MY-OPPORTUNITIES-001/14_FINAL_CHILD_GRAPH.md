# 14 — Final child graph

Thirteen proposed implementation children, `C1`–`C13`. `C11` is
owner/provider-rights decision-gated and required only before any Level 3
licensed-feed operation; `C12` and `C13` are owner-decision-gated and
skippable; the remaining ten (`C1`–`C10` and `C9`'s Level 1–2 scope) form
the required path. This graph is the architecture's proposal; Pete accepts
it (with the doc 15 decisions) at architecture acceptance. Children are registered just-in-time,
one claim each, only when their dependencies and owner decisions are real.
No child collapses distinct privacy, provider, schema, or release risks;
none is a mega-child.

## 1. Dependency and execution model (single authoritative rule set)

The table, diagram, prose, critical path, concurrency rules, child contracts,
and reservation index in this document all state the **same** model.

**Owner-decision gates (explicit; never assumed):**

- **REC-02 (topology)** — Pete must record the canonical-store/search-index
  topology decision **before C2 activates**. Until then, no child may select
  Azure SQL, Azure AI Search, physical schema, a migration, a projection, or
  any provider-dependent physical design. P0 and C1 are decision-free
  (logical contracts and documentation only). Every physical reservation
  below is proposed under the REC-02-recommended topology and re-derives at
  activation (a manager-signed scoping change) if Pete selects otherwise.
- **REC-01 (Slate target)** — before C7.
- **Corrected desktop/iPad visual artifacts** — before C8's visual gate
  (its functional gate is never waived, doc 10 §6).
- **Licensed feed provider/rights (Pete)** — before C11 activation, and C11
  completes before any C9 Level 3 licensed-feed operation.
- **Company-context provider/rights (Pete)** — before C12 activation; absent
  that decision C12 never activates and the product keeps the truthful
  absent-company-context state indefinitely.
- **Member URL fetching (Pete)** — before **C13**
  (`PS-MYOPP-URL-FETCH-001`) activates. Paste/upload in C10 is
  unconditional; C10 closes without any fetch scope, and C13 is a distinct
  later claim — nothing resumes inside a closed C10.

**Execution order is strictly serial** (P2-10 resolution: overlap is
removed, not managed):

```text
P0 ─▶ independent review ─▶ Pete's architecture acceptance
  C1 ─▶ [REC-02 recorded] ─▶ C2 ─▶ C3 ─▶ C5 ─▶ C4 ─▶ C6 ─▶ C10 ─▶ C7 ─▶ C8 ─▶ C11 ─▶ C12 ─▶ C9

  C13 (URL fetch; optional): activates only upon Pete's fetch decision, in
  any one-active-claim window after C10 closes; skippable forever.
```

- **Critical path:** the main chain as written. C11 is provider-rights
  decision-gated and required only before Level 3 licensed-feed operation;
  C12 and C13 are decision-gated and skippable (see gates); the remaining
  ten links are required.
- **Concurrency:** none is claimed. One child holds the active
  implementation claim at a time; the next activates only after the previous
  claim closes. This satisfies every shared-path rule by construction —
  including `SQL FIles/Migrations/registry.json` (reserved by C2, C3, C4,
  C5, C6, C10, C12, C9) and the shared sign-in surfaces (C8) — and keeps
  one writer per mutable surface with zero serialization caveats.
- **Permitted variation (explicit, bounded):** because C11 and C12 are
  owner-decision-gated, the manager may activate C9 immediately after C8 for
  **Level 1–2 scope only** while those decisions are pending, then **pause**
  C9 at a pushed checkpoint through the governed pause transition so C11
  (and C12 if decided) can activate, and **resume** C9 afterward for
  Level 3. C11 must complete before C9 performs any Level 3 licensed-feed
  operation; C12 must complete before any live company-context claim. The
  one-active-claim rule still holds at all times — pause/resume is the
  governed mechanism that preserves it.
- **Why this order:** C2 (canonical) precedes all member-side children; C3
  (criteria state) precedes C5 because C5's assessments are consumed by
  C4's execution pipeline, and C4 needs both C3's snapshots and C5's
  assessment writer; C6 (saves/overlays) needs C4's result identity; C10
  (member import) is off the search-critical path but precedes C8 so the UI
  can integrate its seams; C7 (Slate) after C6; C8 integrates everything
  member-facing; C11/C12/C9 are the operational tail.

## 2. Per-child contracts

Common to every child (binding on all): Protected delivery path;
`review_requirement: independent` with a fresh exact-SHA read-only reviewer
per the then-current `docs/AI_MODEL_AND_ROLE_ROUTING.md`; complete-diff
writer self-review before review; production authority withheld; truthful
status vocabulary; R3 child-handoff/child-return minimums verbatim; one
completed child never closes the parent; every reservation is re-normalized
and collision-checked against then-current claims at activation; every
directory marked **[parent boundary]** requires the child's activation to
enumerate its exact leaf files inside that directory before any write.

### C1 — `PS-MYOPP-SUPPLY-RIGHTS-001` (documentation only; pre-REC-02 safe)

- **Outcome:** provider comparison record; rights-ledger candidates
  (`source_policy` shape, doc 05 §§2, 10, including per-provider
  termination-survivability of minimal reference facts, doc 05 §8);
  provider-neutral connector contract text; finalized untrusted-import,
  private member-import isolation, and company-context policy (doc 06). No
  purchase, contact, or selection by inference; no physical artifact.
- **Depends on:** accepted architecture. **Gates:** none.
- **Reservations:** `docs/initiatives/PS-MYOPP-SUPPLY-RIGHTS-001/`
  **[parent boundary]**. **Domain:**
  `architecture:my-opportunities:supply-rights`.
- **Risks:** rights misstatement; provider contact by inference; scope creep.
- **Stop controls:** no external contact/spend; provider-terms statements
  cite public documentation or are marked unverified; stop on any rights
  question requiring counsel.
- **Verifier/evidence:** independent exact-SHA documentation review;
  citations ledger.
- **Completion rule:** accepted comparison + policy records naming the owner
  decisions they tee up; no runtime claim.

### C2 — `PS-MYOPP-CANONICAL-001` (first post-REC-02 child)

- **Outcome:** canonical shared-side lifecycle runtime per docs 02/03/05:
  receipts, listings, versions, canonical identity, requirement versions,
  dedupe/merge/split, governing-source selection, aggregate eligibility,
  failover, freshness, closure/outage, application-link validation
  (persisted valid/invalid/unknown state, doc 05 §5), Live Opportunity
  Gate; the provider-neutral connector interface plus the synthetic/fixture
  connector; the reusable **safe-outbound validator** (doc 05 §5 — scheme
  rules, per-connection DNS/address revalidation, deny set, redirect/fetch
  budgets, content-type/size boundaries, no credential forwarding), which
  link validation uses and C13 later reuses; the canonical physical schema
  under the recorded REC-02 topology.
- **Depends on:** C1 accepted; **REC-02 recorded**.
- **Reservations:** `services/my_opportunities/__init__.py`,
  `services/my_opportunities/canonical_service.py`,
  `services/my_opportunities/ingestion_service.py`,
  `services/my_opportunities/connectors.py`,
  `services/my_opportunities/safe_outbound.py`,
  `tests/test_my_opportunities_canonical.py`,
  `tests/test_my_opportunities_ingestion.py`,
  `tests/test_my_opportunities_safe_outbound.py`,
  `tests/fixtures/my_opportunities/` **[parent boundary]**,
  `SQL FIles/Migrations/proposed/PS-MYOPP-001_canonical_foundation.sql`,
  `SQL FIles/Migrations/proposed/PS-MYOPP-001_canonical_foundation_rollback.sql`,
  `SQL FIles/Migrations/registry.json`,
  `docs/initiatives/PS-MYOPP-CANONICAL-001/` **[parent boundary]**.
  **Domain:** `runtime:my-opportunities:canonical`.
- **Risks:** canonical-data integrity; schema; dedupe correctness;
  fixture/production isolation; **outbound request safety** (link
  validation reaches employer/ATS hosts).
- **Stop controls:** additive-only migration with verified rollback and gate
  proof before any governed apply; **no member-side table**; every outbound
  link check exclusively through `safe_outbound` with no credential/cookie
  forwarding; stop on any deny-set, rebinding, or redirect-validation gap;
  stop on any fixture/production cross-class leak.
- **Verifier/evidence:** independent review; migration gate proof (P-2);
  fixture lifecycle/governing-source/failover/merge-split suites (P-1)
  including the doc 16 failover row; the doc 16 application-link lifecycle
  row (valid→invalid per reason, recovery, unknown, gate exclusion,
  closure/outage distinction) and the outbound adversarial matrix (DNS
  rebinding, private-network/metadata denial, redirect chains,
  timeout/outage).
- **Completion rule:** doc 03 §§1, 9 machines, doc 05 §5 link-validation
  lifecycle, and doc 05 §6 gate behavior fixture-proven; the safe-outbound
  adversarial matrix green; schema gated; no ingestion scheduling enabled.

### C3 — `PS-MYOPP-CRITERIA-001`

- **Outcome:** interpretation service and the complete criteria command set
  (doc 04 §§1, 1a, and 2): visible draft, edit/clarify/dismiss, manual
  draft parity, post-result refinement, Keep current criteria, explicit
  Apply with terminal receipts; **plus the owner-scoped persistence for
  `criteria_draft` and `applied_criteria_snapshot`** (doc 02 §6).
- **Depends on:** C2.
- **Reservations:** `services/my_opportunities/criteria_service.py`,
  `services/my_opportunities/interpretation_service.py`,
  `tests/test_my_opportunities_criteria.py`,
  `SQL FIles/Migrations/proposed/PS-MYOPP-002_criteria_state.sql`,
  `SQL FIles/Migrations/proposed/PS-MYOPP-002_criteria_state_rollback.sql`,
  `SQL FIles/Migrations/registry.json`,
  `docs/initiatives/PS-MYOPP-CRITERIA-001/` **[parent boundary]**.
  **Domain:** `runtime:my-opportunities:criteria`.
- **Risks:** consequential AI (interpretation); member data (drafts contain
  member intent); silent-mutation regressions.
- **Stop controls:** AI proposes only — deterministic code owns
  draft/snapshot writes and token rotation; no execution/retrieval work;
  stop on any path where an unseen interpretation executes.
- **Verifier/evidence:** independent review; P-1 fixture + degraded-mode
  suites for every doc 16 criteria row, stale-token and idempotency cases.
- **Completion rule:** doc 03 §3 machine and every doc 04 §§1, 1a, and 2
  command proven — live token rotation, terminal receipts, and the complete
  §1a precedence table (original-receipt replay, `idempotency_mismatch`,
  `terminal_draft`, `stale_draft`, no-mutation-on-refusal) included — with
  post-result refinement leaving applied results untouched.

### C4 — `PS-MYOPP-RETRIEVAL-001`

- **Outcome:** search execution runtime under the recorded REC-02 topology:
  retrieval, ordering (doc 04 §4 total chain), pagination, ceilings,
  cancellation, degraded modes, partial executions (doc 04 §11); the
  owner-bound search worker (doc 08 §2a) invoking C5's assessment writer;
  **plus the owner-scoped persistence for `search_execution` and
  `result_snapshot`** (doc 02 §6); index projection/fence when the index
  candidate is selected; loading-copy truth binding (doc 16 §4).
- **Depends on:** C3 (snapshots) and C5 (assessment writer/service).
- **Reservations:** `services/my_opportunities/retrieval_service.py`,
  `services/my_opportunities/search_worker.py`,
  `services/my_opportunities/index_projection.py`,
  `services/my_opportunities/index_fence.py`,
  `tests/test_my_opportunities_retrieval.py`,
  `SQL FIles/Migrations/proposed/PS-MYOPP-004_search_execution_results.sql`,
  `SQL FIles/Migrations/proposed/PS-MYOPP-004_search_execution_results_rollback.sql`,
  `SQL FIles/Migrations/registry.json`,
  `docs/initiatives/PS-MYOPP-RETRIEVAL-001/` **[parent boundary]** (index
  schema documents live here). **Domain:**
  `runtime:my-opportunities:retrieval`.
- **Risks:** shared infrastructure (if index); member-data leakage into
  projections; worker authorization; ordering determinism.
- **Stop controls:** REC-05 — no member data in any projection, asserted by
  test; fence drops on canonical mismatch; a failed final doc 08 §2a
  recheck permits **no additional result_snapshot/member-result
  persistence** beyond the bounded failed execution status and content-free
  audit event, while assessment rows already durably written under prior
  successful per-write authorization remain authorized historical records
  outside this execution's results, following recompute policy; stop on
  nondeterministic ordering.
- **Verifier/evidence:** independent review; P-1 suites for every doc 16
  retrieval/partial/restoration row; P-2 disposable index proof with
  exact-target cleanup when the index candidate is selected.
- **Completion rule:** doc 04 contract (including §11) proven at P-1 (and
  P-2 where infrastructure exists), degraded paths included.

### C5 — `PS-MYOPP-QUALIFICATION-001`

- **Outcome:** requirement atomization, evidence-port binding, grants,
  four-state assessments, gate derivation, correction/revocation,
  explanation copy (doc 07); the **initial assessment writer** contract
  invoked by C4's worker (doc 08 §2a) and the recompute path; **plus the
  owner-scoped persistence for `assessment`, `evidence_grant`, and
  `practical_fit_observation`** (doc 02 §6).
- **Depends on:** C3 closed (serial order); logically C2 (requirement
  versions), the evidence-policy owner decision, and the evidence-source
  binding (doc 07 §6).
- **Reservations:** `services/my_opportunities/qualification_service.py`,
  `services/my_opportunities/evidence_port.py`,
  `tests/test_my_opportunities_qualification.py`,
  `SQL FIles/Migrations/proposed/PS-MYOPP-003_qualification.sql`,
  `SQL FIles/Migrations/proposed/PS-MYOPP-003_qualification_rollback.sql`,
  `SQL FIles/Migrations/registry.json`,
  `docs/initiatives/PS-MYOPP-QUALIFICATION-001/` **[parent boundary]**.
  **Domain:** `runtime:my-opportunities:qualification`.
- **Risks:** privacy (evidence, grants); consequential AI; gate truth.
- **Stop controls:** authorization-before-AI fence with canaries; the four
  canonical states are a closed enum; per-write grant recheck; stop if no
  truthful evidence source exists at activation (doc 07 §6 escalation).
- **Verifier/evidence:** independent review; P-1 deterministic gate
  fixtures; negative multi-member suite (doc 08 §7);
  revocation/correction/idempotent-reuse rows of doc 16.
- **Completion rule:** every doc 07 behavior proven; assessment identity
  idempotency (one current assessment per member × requirement item ×
  version) proven; no member-facing score anywhere.

### C6 — `PS-MYOPP-RELATIONSHIPS-001`

- **Outcome:** saves, lifecycle overlays, removal/undo, saved-view local
  search/filter (doc 03 §7); **plus the owner-scoped persistence for
  `saved_opportunity` and `slate_link`** (doc 02 §6; the `slate_link` table
  lands here so C7 needs no migration).
- **Depends on:** C4 (result identity).
- **Reservations:** `services/my_opportunities/relationships_service.py`,
  `tests/test_my_opportunities_relationships.py`,
  `SQL FIles/Migrations/proposed/PS-MYOPP-005_relationships.sql`,
  `SQL FIles/Migrations/proposed/PS-MYOPP-005_relationships_rollback.sql`,
  `SQL FIles/Migrations/registry.json`,
  `docs/initiatives/PS-MYOPP-RELATIONSHIPS-001/` **[parent boundary]**.
  **Domain:** `runtime:my-opportunities:relationships`.
- **Risks:** member data; undo/idempotency; overlay truthfulness.
- **Stop controls:** overlays derived, never mutating saves; unknown-outcome
  write discipline (doc 09 §4); stop on any cross-member visibility.
- **Verifier/evidence:** independent review; P-1 saved/undo/stale/overlay
  rows of doc 16 plus negative multi-member proof.
- **Completion rule:** doc 03 §7 machine and saved-view contract proven.

### C7 — `PS-MYOPP-SLATE-INTEGRATION-001` (no migration)

- **Outcome:** the doc 11 §4 create/continue/history contract into the
  accepted Slate capability target, including the one bounded Slate intake
  seam, with rights-governed handoff content.
- **Depends on:** C10 closed (serial order); logically C6 (`slate_link`
  persistence); **Pete's REC-01 decision and the required remaining Slate
  capability state (doc 11 §3 (a)/(b))**; production flag state re-verified
  at entry.
- **Reservations:** `services/my_opportunities/slate_handoff_service.py`,
  `tests/test_my_opportunities_slate_handoff.py`, and — under the REC-01
  recommended target — exactly `services/opportunity_slate_v2_service.py`
  and `tests/test_opportunity_slate_v2.py` as the claimed Slate seam (a
  different owner-selected target re-derives these two leaves at activation
  with manager sign-off). `docs/initiatives/PS-MYOPP-SLATE-INTEGRATION-001/`
  **[parent boundary]**. **Domain:**
  `runtime:my-opportunities:slate-handoff`.
- **Risks:** cross-package boundary; member data; live-Slate regression.
- **Stop controls:** atomic create (no orphan links); **direct-key
  cross-owner denial** — member B's create/continue/history against member
  A's `link_key`, workspace reference, or opportunity relationship refused
  with the not-found shape (doc 08 §7); no Slate file outside the two named
  leaves; full existing Slate suite stays green; no continuation-package
  scope.
- **Verifier/evidence:** independent review; P-1 contract suites including
  the negative multi-member/direct-key cross-owner denial suite for all
  three commands; P-3 integration proof; Slate regression results.
- **Completion rule:** doc 11 §4 commands/invariants proven; cross-owner
  denial proven for create/continue/history; Slate suite green; no
  duplicated Slate capability.

### C8 — `PS-MYOPP-UI-001` (no migration)

- **Outcome:** member-facing UI: two-row search, dossier, rail, every doc 16
  §1 state (including the mobile fully-verified functional state) and §2/§3
  scenario surfaces, alias copy table, truthful labels; route registration
  (register-always + `before_request` flag gate, REC-04) and rate-limit
  rows; **the sign-in return/private-path contract**: canonical route
  prefix `/my-opportunities`, registered as
  `ProtectedDestination("/my-opportunities",
  "PEERSLATE_MY_OPPORTUNITIES_ENABLED")` (the proposed surface flag key —
  architecture proposal, not deployed truth) in
  `safe_return.PROTECTED_DESTINATIONS`, with the same prefix-and-flag
  contract bound in **both** browser allowlists
  (`static/js/auth-state.js` private-namespace coverage and
  `static/js/easy-auth-callback.js`), each proven by tests; **the
  two-destination navigation contract**: My Opportunities is discoverable
  beside Opportunity Slate in the shared shell navigation (the two accepted
  Opportunities destinations), flag-aware, with navigation parity proof;
  **and the URL-import HTTP surface**: C8 owns and registers
  `POST /my-opportunities/import/url` (the route exists from C8 onward),
  its `app.py`/config/rate-limit rows, and the flag-gated URL affordance —
  the URL input renders only when both
  `PEERSLATE_MY_OPPORTUNITIES_ENABLED` and
  `PEERSLATE_MY_OPPORTUNITIES_URL_FETCH_ENABLED` are true — otherwise
  paste/upload UI only, no dead chrome, proven by flag-off tests. The route
  calls C10's service-level port, which answers `url_fetch_unavailable`
  behind it either way until C13 exists.
- **Depends on:** C3–C7 and C10 closed (serial order); **Pete's corrected
  desktop/iPad artifacts** for the quarantined compositions (visual gate
  only — the functional gate is never waived, doc 10 §6).
- **Reservations:** `my_opportunities_routes.py`,
  `templates/my_opportunities/` **[parent boundary]**,
  `static/css/my-opportunities.css`, `static/js/my-opportunities.js`,
  `app.py`, `templates/base.html`, `safe_return.py`,
  `static/js/auth-state.js`, `static/js/easy-auth-callback.js`,
  `tests/test_signin_member_arrival.py`, `tests/test_navigation.py`,
  `tests/test_my_opportunities_ui.py`,
  `docs/initiatives/PS-MYOPP-UI-001/` **[parent boundary]**.
  **Domain:** `runtime:my-opportunities:ui`.
- **Risks:** architecture-heavy UI; accessibility; visual drift; **seven hot
  shared files** (`app.py`, `templates/base.html`, `safe_return.py`,
  `static/js/auth-state.js`, `static/js/easy-auth-callback.js`,
  `tests/test_signin_member_arrival.py`, `tests/test_navigation.py`) — the
  highest collision-risk claim in the program.
- **Stop controls:** sole-writer collision re-check on all seven shared
  files at activation (stop, not force, on any active overlap); the
  doc 10 §6 two-gate rule; no third search row; no invented layouts; the
  `base.html` change is bounded to the navigation entry — any drift into
  shared-shell direction or material visual change stops and returns to the
  separate shell/visual authority; every `safe_return`/auth-state/
  navigation change proven by the existing member-arrival and navigation
  suites plus new round-trip and two-destination cases.
- **Verifier/evidence:** independent review plus Pete's visual acceptance;
  P-1 browser/WCAG suites at 1600×1200, 1024×768, 390×844 for every state;
  sign-in round-trip proof; navigation/parity proof; parity records per the
  visual standard.
- **Completion rule:** every doc 16 state functionally proven at every
  supported viewport; sign-in return round trip proven for
  `/my-opportunities`; the two-destination navigation proven flag-aware;
  visual gate satisfied for every composition shipped.

### C9 — `PS-MYOPP-OPERATIONS-001`

- **Outcome:** scheduling, monitoring/budgets (doc 12), telemetry landing
  (dark-first, purge discipline), licensed-feed operational activation
  mechanics, migration/cutover/rollback execution, cost evidence, live
  proof.
- **Depends on:** C8 closed; **Level 3 licensed-feed operation additionally
  requires C11 complete; any live company-context claim requires C12
  complete**; every production operation separately authorized per standing
  rules. Under the §1 permitted variation, C9 may activate for Level 1–2
  scope while C11/C12 decisions are pending.
- **Reservations:** `scripts/run_my_opportunities_refresh.py`,
  `scripts/run_my_opportunities_telemetry_purge.py`,
  `tests/test_my_opportunities_operations.py`,
  `SQL FIles/Migrations/proposed/PS-MYOPP-008_telemetry.sql`,
  `SQL FIles/Migrations/proposed/PS-MYOPP-008_telemetry_rollback.sql`,
  `SQL FIles/Migrations/registry.json`,
  `docs/initiatives/PS-MYOPP-OPERATIONS-001/` **[parent boundary]**.
  **Domain:** `operations:my-opportunities`.
- **Risks:** shared infrastructure; cost; production operations.
- **Stop controls:** budgets/ceilings pre-dispatch; exact-target cleanup
  manifests for any provisioned proof infrastructure; no member-facing
  enablement without Pete's explicit release decision; schema and web
  operations never share a run.
- **Verifier/evidence:** independent review; P-2 dark proof, then P-3/P-4 as
  authorized, P-5 only inside the owner-approved licensed pilot.
- **Completion rule:** Level 2 proven dark; Level 3/4 only at their stated
  evidence, each release state reported separately.

### C10 — `PS-MYOPP-MEMBER-IMPORT-001` (paste/upload; unconditional)

- **Outcome:** the permanent private `member_import` path: paste and
  document-upload storage, deterministic sanitization/extraction with
  explicit outcome states (doc 06 §2), provenance recording, owner-scoped
  authorization, export/delete, dual retention (member lifecycle + rights
  at point of use, doc 02 §4), the API seams and UI-seam contract C8
  integrates, schema/rollback, and negative multi-member tests. **Not
  conditional on URL fetching and never enters shared inventory** (doc 02
  invariant 8). Remote URL fetching is **not** in this child at any point:
  it is the distinct, Pete-gated future child C13, so C10 closes cleanly
  after paste/upload. C10 does, however, ship the **prebuilt disabled
  service-level fetch port** that makes C13 a service-only late integration
  (design B): a URL-import service operation inside
  `member_import_service.py` that resolves a fetch adapter through one
  fixed seam — module
  `services/my_opportunities/member_url_fetch_service.py`, callable
  `create_fetch_adapter()` — **only when both**
  `PEERSLATE_MY_OPPORTUNITIES_ENABLED` **and**
  `PEERSLATE_MY_OPPORTUNITIES_URL_FETCH_ENABLED` are true and the module is
  importable; in every other case it returns the truthful service-level
  `url_fetch_unavailable` outcome. **C10 owns no HTTP route.** The
  `POST /my-opportunities/import/url` route, its `app.py`/config/rate-limit
  rows, and the member-facing affordance are C8 surfaces — the HTTP route
  exists from **C8** onward and simply calls this port, surfacing the
  refusal with paste/upload offered inline.
- **Depends on:** C6 closed (serial order); logically only C2's conventions
  and REC-02.
- **Reservations:** `services/my_opportunities/member_import_service.py`,
  `tests/test_my_opportunities_member_import.py`,
  `SQL FIles/Migrations/proposed/PS-MYOPP-006_member_import.sql`,
  `SQL FIles/Migrations/proposed/PS-MYOPP-006_member_import_rollback.sql`,
  `SQL FIles/Migrations/registry.json`,
  `docs/initiatives/PS-MYOPP-MEMBER-IMPORT-001/` **[parent boundary]**.
  **Domain:** `runtime:my-opportunities:member-import`.
- **Risks:** member data; untrusted content parsing; retention duality.
- **Stop controls:** no promotion of any import to shared objects (tested);
  sanitizer output only; per-use rights check; stop on any cross-member
  visibility.
- **Verifier/evidence:** independent review; P-1 pipeline-outcome,
  sanitization, export/delete, dual-retention, and negative multi-member
  suites (doc 16 §3 paste/upload rows), plus the service-level port's
  flag-off/absent `url_fetch_unavailable` outcome (the HTTP surface and
  paste/upload-offering UI are proven at C8).
- **Completion rule:** every unconditional doc 16 §3 import row proven; the
  disabled service-level fetch port refuses truthfully; no HTTP route and
  no fetch capability present (the route is C8's; URL fetching is C13, a
  separate future claim).

### C11 — `PS-MYOPP-LICENSED-FEED-ADAPTER-001` (decision-gated; no migration)

- **Outcome:** the selected provider's adapter implementing C2's
  provider-neutral connector interface: `describe/acquire/normalize`
  against the real feed, rights-ledger enforcement at registration and at
  point of use, acquire→receipt→normalize handoff into C2's ingestion,
  bounded error/retry behavior, and the shutdown/termination/exit proof
  (doc 05 §§7–8). Credentials live only in deployment configuration
  (App Service settings/managed identity) — never in the repository; the
  adapter reads named settings and fails closed without them.
- **Depends on:** C8 closed (serial order); logically C2 (interface) and
  **Pete's provider/rights selection** (activation gate). Completes before
  any C9 Level 3 licensed-feed operation. No provider is selected or
  contacted in P0.
- **Reservations:** `services/my_opportunities/licensed_feed_adapter.py`,
  `tests/test_my_opportunities_licensed_feed_adapter.py`,
  `docs/initiatives/PS-MYOPP-LICENSED-FEED-ADAPTER-001/`
  **[parent boundary]**. **Domain:**
  `runtime:my-opportunities:licensed-feed-adapter`.
- **Risks:** provider rights compliance; secret handling; live-data truth.
- **Stop controls:** no live acquire in tests (recorded fixtures only until
  C9's governed operations); registration refused without a live
  `source_policy`; stop on any rights dimension the contract does not
  cover.
- **Verifier/evidence:** independent review; P-1 contract tests against
  recorded fixtures; termination/exit rehearsal evidence; P-5 behavior only
  inside C9's owner-approved pilot.
- **Completion rule:** contract-conformant adapter with rights enforcement
  and exit proof; zero repository secrets.

### C12 — `PS-MYOPP-COMPANY-CONTEXT-001` (decision-gated; skippable)

- **Outcome:** company-context runtime: `company_context_claim` ingestion
  from the owner-selected permitted sources, rights/provenance validation,
  persistence and read API, freshness/`as_of` handling, removal, and tests
  (docs 02, 06 §5). Source-linked claims only; never sentiment/reputation
  synthesis. The **absent/unavailable behavior is independent of this
  child**: C8 ships the truthful "No company context available" state
  regardless, so skipping C12 leaves a complete, honest product.
- **Depends on:** C11 closed under the default order (or per the §1
  permitted variation); **Pete's company-context provider/rights
  selection** (activation gate). Completes before any live company-context
  claim.
- **Reservations:** `services/my_opportunities/company_context_service.py`,
  `tests/test_my_opportunities_company_context.py`,
  `SQL FIles/Migrations/proposed/PS-MYOPP-007_company_context.sql`,
  `SQL FIles/Migrations/proposed/PS-MYOPP-007_company_context_rollback.sql`,
  `SQL FIles/Migrations/registry.json`,
  `docs/initiatives/PS-MYOPP-COMPANY-CONTEXT-001/` **[parent boundary]**.
  **Domain:** `runtime:my-opportunities:company-context`.
- **Risks:** rights; claim truthfulness; scope creep into company
  intelligence.
- **Stop controls:** every stored claim must complete its provenance walk or
  is refused; disagreement rendered, never synthesized; no member data ever
  feeds company context; stop on any claim class outside the owner-approved
  set.
- **Verifier/evidence:** independent review; P-1 truth/absent/stale/
  contradictory fixtures (doc 16 §3 company row); licensed proof before any
  live claim.
- **Completion rule:** doc 06 §5 boundary proven; live claims only at the
  C9 level that carries their rights evidence.

### C13 — `PS-MYOPP-URL-FETCH-001` (member URL fetch; Pete-gated; skippable; no migration)

- **Outcome — service-only late integration (design B):** the fetch adapter
  behind C10's prebuilt disabled port. C13 implements exactly the fixed
  seam C10 resolves — module
  `services/my_opportunities/member_url_fetch_service.py`, callable
  `create_fetch_adapter()` — using C2's `safe_outbound` validator for the
  complete doc 06 §1 network boundary (schemes, per-connection DNS/address
  revalidation, deny set, redirect/fetch budgets, content limits, no
  credential forwarding), handing fetched bytes to C10's deterministic
  sanitize/extract pipeline, and recording fetch provenance into the
  requesting member's `member_import` rows — never shared supply, never an
  index, never canonical (doc 02 invariant 8). **It modifies no closed
  surface**: no route, `app.py`, template, JS, or C10/C8 file changes —
  the service-level port and refusal behavior exist from C10, and the
  `POST /my-opportunities/import/url` route, flag-gated UI affordance, and
  rate-limit row exist from C8.
- **Proposed flag:** `PEERSLATE_MY_OPPORTUNITIES_URL_FETCH_ENABLED`
  (architecture proposal, not deployed truth), effective only alongside the
  parent `PEERSLATE_MY_OPPORTUNITIES_ENABLED`; flag values are deployment
  configuration, the keys are this architecture's contract.
- **Member-facing behavior:** both flags on + adapter present → URL import
  runs the doc 06 §2 outcome states; any other combination → the C10
  `url_fetch_unavailable` truthful refusal with manual paste/upload offered
  inline (the permanent fallback). **Rollback/disable:** flip
  `PEERSLATE_MY_OPPORTUNITIES_URL_FETCH_ENABLED` off (configuration-only)
  — the port refuses truthfully again; removing the adapter module has the
  identical effect.
- **Depends on:** C10 closed (the port exists); C2 closed
  (`safe_outbound`); **Pete's member-URL-fetch decision** (activation
  gate). Optional and skippable forever; activates in any one-active-claim
  window after C10 closes; nothing depends on it.
- **Reservations:** `services/my_opportunities/member_url_fetch_service.py`,
  `tests/test_my_opportunities_member_url_fetch.py`,
  `docs/initiatives/PS-MYOPP-URL-FETCH-001/` **[parent boundary]**.
  **No schema impact proposed**: C10's `member_import` schema already
  carries the fetch-provenance fields (doc 02 §1), so this child reserves
  no migration and no registry edit; if activation-time discovery shows a
  genuine schema need, that is an explicit re-scope with its own additive
  migration proposal, never a silent addition. **Domain:**
  `runtime:my-opportunities:url-fetch`.
- **Risks:** SSRF/untrusted remote content; member data; scope creep toward
  shared ingestion.
- **Stop controls:** adapter-only — stop on any edit outside the three
  reserved paths (no reopening of closed C8/C10 ownership); every doc 06 §1
  rule enforced through `safe_outbound` and proven by the §6 adversarial
  suite before any live fetch; no promotion of fetched content to any
  shared object (tested); deterministic extraction only; stop on any
  deny-set or rebinding gap.
- **Verifier/evidence:** independent review; the complete doc 06 §6
  adversarial matrix at P-1; the doc 16 §3 fetch rows; flag-off/absent
  refusal and rollback proof; negative multi-member proof (doc 08 §7).
- **Completion rule:** every doc 16 §3 fetch row proven; refusal/rollback
  behavior proven in both directions; the fetch flag remains off until
  Pete's separate enablement decision.

## 3. Reservation index (collision view; sole claiming child per path)

| Path | Sole claiming child |
|---|---|
| `services/my_opportunities/__init__.py`, `canonical_service.py`, `ingestion_service.py`, `connectors.py`, `safe_outbound.py` | C2 |
| `services/my_opportunities/criteria_service.py`, `interpretation_service.py` | C3 |
| `services/my_opportunities/retrieval_service.py`, `search_worker.py`, `index_projection.py`, `index_fence.py` | C4 |
| `services/my_opportunities/qualification_service.py`, `evidence_port.py` | C5 |
| `services/my_opportunities/relationships_service.py` | C6 |
| `services/my_opportunities/slate_handoff_service.py`; `services/opportunity_slate_v2_service.py`; `tests/test_opportunity_slate_v2.py` | C7 |
| `my_opportunities_routes.py`; `templates/my_opportunities/`; `static/css/my-opportunities.css`; `static/js/my-opportunities.js`; `app.py`; `templates/base.html`; `safe_return.py`; `static/js/auth-state.js`; `static/js/easy-auth-callback.js`; `tests/test_signin_member_arrival.py`; `tests/test_navigation.py` | C8 |
| `scripts/run_my_opportunities_refresh.py`; `scripts/run_my_opportunities_telemetry_purge.py` | C9 |
| `services/my_opportunities/member_import_service.py` | C10 |
| `services/my_opportunities/licensed_feed_adapter.py` | C11 |
| `services/my_opportunities/company_context_service.py` | C12 |
| `services/my_opportunities/member_url_fetch_service.py` | C13 |
| `SQL FIles/Migrations/proposed/PS-MYOPP-001_canonical_foundation.sql` + `PS-MYOPP-001_canonical_foundation_rollback.sql` | C2 |
| `SQL FIles/Migrations/proposed/PS-MYOPP-002_criteria_state.sql` + `PS-MYOPP-002_criteria_state_rollback.sql` | C3 |
| `SQL FIles/Migrations/proposed/PS-MYOPP-003_qualification.sql` + `PS-MYOPP-003_qualification_rollback.sql` | C5 |
| `SQL FIles/Migrations/proposed/PS-MYOPP-004_search_execution_results.sql` + `PS-MYOPP-004_search_execution_results_rollback.sql` | C4 |
| `SQL FIles/Migrations/proposed/PS-MYOPP-005_relationships.sql` + `PS-MYOPP-005_relationships_rollback.sql` | C6 |
| `SQL FIles/Migrations/proposed/PS-MYOPP-006_member_import.sql` + `PS-MYOPP-006_member_import_rollback.sql` | C10 |
| `SQL FIles/Migrations/proposed/PS-MYOPP-007_company_context.sql` + `PS-MYOPP-007_company_context_rollback.sql` | C12 |
| `SQL FIles/Migrations/proposed/PS-MYOPP-008_telemetry.sql` + `PS-MYOPP-008_telemetry_rollback.sql` | C9 |
| `SQL FIles/Migrations/registry.json` | C2, C3, C4, C5, C6, C10, C12, C9 — safe because execution is strictly serial (§1): one active claim at a time, so no two ever hold it together |
| `tests/test_my_opportunities_canonical.py`, `tests/test_my_opportunities_ingestion.py`, `tests/test_my_opportunities_safe_outbound.py` | C2 |
| `tests/test_my_opportunities_criteria.py` | C3 |
| `tests/test_my_opportunities_retrieval.py` | C4 |
| `tests/test_my_opportunities_qualification.py` | C5 |
| `tests/test_my_opportunities_relationships.py` | C6 |
| `tests/test_my_opportunities_slate_handoff.py` | C7 |
| `tests/test_my_opportunities_ui.py` | C8 |
| `tests/test_my_opportunities_operations.py` | C9 |
| `tests/test_my_opportunities_member_import.py` | C10 |
| `tests/test_my_opportunities_licensed_feed_adapter.py` | C11 |
| `tests/test_my_opportunities_company_context.py` | C12 |
| `tests/test_my_opportunities_member_url_fetch.py` | C13 |
| `docs/initiatives/PS-MYOPP-URL-FETCH-001/` | C13 **[parent boundary]** |
| `tests/fixtures/my_opportunities/` | C2 **[parent boundary]**; later children add leaves only through their own enumerated sub-paths at activation |
| `docs/initiatives/PS-MYOPP-*-001/` | each child exactly its own directory, named in its block above |

Migration IDs `PS-MYOPP-001`–`008` are proposals under the
REC-02-recommended topology; a different owner selection re-derives the
physical reservations at each activation (§1).

## 4. Decisions embedded in this graph (cross-reference doc 15)

REC-02 (topology; gates C2 and every physical artifact after it), REC-01
(gates C7), corrected visuals (gate C8's visual half; functional half never
waived), licensed feed provider/rights (gates C11; C11 before C9 Level 3),
company-context provider/rights (gates C12; C12 before live company claims),
member-URL fetching (gates C13; paste/upload in C10 unconditional),
evidence policy (gates C5), known-unmet broader treatment (open; the current
broader order is owner-neutral, doc 04 §4), freshness/closure thresholds
(C9 Live-Gate activation). None is silently treated as accepted anywhere in
this graph.
