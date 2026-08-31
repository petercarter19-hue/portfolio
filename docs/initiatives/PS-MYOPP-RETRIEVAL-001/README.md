# PS-MYOPP-RETRIEVAL-001 — C4 owner-bound search execution and result runtime

This Protected child implements the accepted My Opportunities C4 search
execution and result-persistence runtime: the doc 08 §2a owner-bound worker
that binds solely to a registered execution record, retrieves candidates over
either an in-memory discovery-index fake (fenced back to canonical truth on
every admission) or the canonical store directly, invokes C5's own
`assess_requirements` for every admitted candidate, orders results by one
fixed deterministic chain per partition, and persists exactly one immutable,
completeness-marked result snapshot per execution — always last, in its own
write.

## Outcome

- `services/my_opportunities/retrieval_service.py` — the closed vocabulary
  (execution states, failed/partial/cancel reasons, partitions, coverage,
  loading copy bound to the accepted REC-02 topology), the record shapes
  (`SearchExecution`, `ResultSnapshot`, `ResultEntry`), the repository
  Protocol and its in-memory reference implementation with a
  transition-guarded state machine, `RetrievalService` (register/status/
  results/cancel/purge, cursor pagination, staleness), and the fenced
  result serializer that builds the browser payload field by field and never
  `asdict()`s an internal record.
- `services/my_opportunities/search_worker.py` — the doc 08 §2a owner-bound
  `SearchWorker.run(execution_key, ...)`: the start-of-run and
  before-persistence criteria rechecks, index-then-canonical-fallback
  retrieval, the deterministic criteria matcher, the two fixed ordering
  chains (qualified and broader), `spec_from_requirement_version`, and the
  snapshot-always-last write.
- `services/my_opportunities/index_projection.py` — the REC-05 projection
  document (structurally member-free; a canary test scans its full field set
  and content), the pure allowlist builder `build_projection_document`,
  `rebuild_index`, and the deterministic in-memory `InMemoryDiscoveryIndex`
  fake.
- `services/my_opportunities/index_fence.py` — the doc 04 §10 local fence:
  every index-derived candidate is re-validated against canonical truth
  before admission (five closed drop reasons); a fenced-but-tampered index
  field can never render because display always resolves from canonical at
  read time, never from the candidate document.
- `tests/test_my_opportunities_retrieval.py` — groups A–O: registration and
  cancellation, worker binding and authority, start/final rechecks, retrieval
  and matching, partial executions, degraded modes, reduced coverage,
  pagination/restoration/staleness, interrupted search (TTL), ordering
  determinism, cross-member isolation and REC-05, the index fence, truth
  bindings (loading copy, no-score serialization), the C5-integration
  contract, and the SQL/registry file-content group.
- The additive, governed `PS-MYOPP-004` migration (`myopp_search_executions`,
  `myopp_result_snapshots`, `myopp_result_entries` and their triggers/
  indexes), its fail-closed rollback, its catalog verifier, and the
  repository registry entry (pre-proof, `"gate": null`).

## Scope exclusions (hard)

No route or UI, no C6 save/apply surface, no provider integration (no
outbound network client, no Anthropic client), no discovery-index
**provisioning** (only contracts and an in-memory fake — REC-02 grants no
spend or provisioning authority at this phase), no change to any C2
(`canonical_service.py`), C3 (`criteria_service.py`,
`interpretation_service.py`), or C5 (`qualification_service.py`,
`evidence_port.py`) file, no durable audit/telemetry table (C9), no UI alias
table (C8), no deployment/enablement, and no production or staging schema
action. A disposable migration-gate database needs its own bounded owner
authorization and is not this file's authority.

## Authorities

- Doc 04 (whole) — [`04_SEARCH_CONTRACT.md`](../PS-MY-OPPORTUNITIES-001/04_SEARCH_CONTRACT.md)
- Doc 08 §2a — [`08_PRIVACY_AND_AUTHORIZATION.md`](../PS-MY-OPPORTUNITIES-001/08_PRIVACY_AND_AUTHORIZATION.md)
  (the owner-bound search worker)
- Doc 03 §4 — [`03_STATE_MACHINES.md`](../PS-MY-OPPORTUNITIES-001/03_STATE_MACHINES.md)
  (the search execution lifecycle)
- Doc 02 §§1, 6 — [`02_DOMAIN_AND_PROVENANCE_MODEL.md`](../PS-MY-OPPORTUNITIES-001/02_DOMAIN_AND_PROVENANCE_MODEL.md)
  (`result_snapshot` record shape, persistence ownership)
- Doc 09 — [`09_API_ASYNC_AND_FAILURE_CONTRACTS.md`](../PS-MY-OPPORTUNITIES-001/09_API_ASYNC_AND_FAILURE_CONTRACTS.md)
  (error shapes, 409-style refusals)
- Doc 12 — [`12_OBSERVABILITY_AND_COST.md`](../PS-MY-OPPORTUNITIES-001/12_OBSERVABILITY_AND_COST.md)
  (content-free audit event kinds)
- Doc 14 — [`14_FINAL_CHILD_GRAPH.md`](../PS-MY-OPPORTUNITIES-001/14_FINAL_CHILD_GRAPH.md)
  ### C4 (outcome, reservations, stop controls)
- Doc 15 §2 — [`15_DECISION_REGISTER.md`](../PS-MY-OPPORTUNITIES-001/15_DECISION_REGISTER.md)
  (REC-02 topology, REC-03, REC-05 member-free index, REC-07 governing-head
  semantics — all accepted; no blocking owner decision for C4)
- Doc 16 — [`16_TRACEABILITY_MATRIX.md`](../PS-MY-OPPORTUNITIES-001/16_TRACEABILITY_MATRIX.md)
  (every row naming C4)
- Precedent mirrored throughout: C5 (`qualification_service.py`,
  `evidence_port.py`, the `PS-MYOPP-003` SQL trio), C3 (`criteria_service.py`,
  the `PS-MYOPP-002` SQL trio), C2 (`canonical_service.py`, `PS-MYOPP-001`).
- Implementation blueprint: `C4_ARCHITECTURE.md` (§0–§13), written against
  `origin/main` post-C5-merge with `PS-MYOPP-003`'s gate proven; the
  implementer made no policy decisions — every closed enum, algorithm step,
  and SQL DDL element is either quoted from the governing docs or an
  explicitly recorded mechanical consequence (§11 below).

## Delivered files

| File | Content |
|---|---|
| `services/my_opportunities/retrieval_service.py` | Closed vocabulary, error type, repository Protocol + in-memory repo with the transition-guarded state machine, execution registration/status/results/cancel/purge, cursor pagination, staleness, loading-copy constants, the fenced result serializer |
| `services/my_opportunities/search_worker.py` | Owner-bound binding, start/final rechecks, index-then-canonical retrieval, the deterministic matcher, per-entry C5 invocation, the two ordering chains, snapshot-always-last assembly |
| `services/my_opportunities/index_projection.py` | REC-05 projection document, the pure allowlist builder, `rebuild_index`, the deterministic in-memory discovery-index fake |
| `services/my_opportunities/index_fence.py` | Doc 04 §10 local fence: candidate re-validation against canonical truth, five closed drop reasons |
| `tests/test_my_opportunities_retrieval.py` | Groups A–O (registration/cancellation, worker binding, rechecks, retrieval/matching, partial executions, degraded modes, reduced coverage, pagination/restoration/staleness, interrupted search, ordering determinism, cross-member isolation, the index fence, truth bindings, C5-integration contract, SQL/registry file-content) |
| `SQL FIles/Migrations/PS-MYOPP-004_search_execution_results.sql` | Additive forward migration: `myopp_search_executions`, `myopp_result_snapshots`, `myopp_result_entries`, their state-machine/immutability triggers, and owner/class-fenced indexes |
| `SQL FIles/Migrations/PS-MYOPP-004_search_execution_results_rollback.sql` | Fail-closed rollback: refuses on a later ledger row or any C4 member data; drops in dependency order (entries → snapshots → executions) |
| `SQL FIles/Verification/PS-MYOPP-004_search_execution_results_verify.sql` | Real catalog assertions: owner/class fencing, closed lifecycle vocabulary, one-snapshot-per-execution and per-partition-ordinal uniqueness, forbidden copied-content and scoring-column scans, no discovery-index/projection table |
| `SQL FIles/Migrations/registry.json` | One appended `PS-MYOPP-004` entry, `"gate": null` pre-proof — the disposable gate proof is a separate, later, bounded owner authorization, not this package's authority |

`PS-MYOPP-004` adds only owner-fenced search executions, one immutable
result snapshot per execution, and reference-only ordered result entries.
Its forward migration, rollback, verifier, and registry entry are repository
candidate artifacts only; merge will not apply schema, deploy, enable,
contact a provider, or change production.

## How to run the tests

```bash
python3 -m unittest tests.test_my_opportunities_retrieval -v
python3 -m unittest tests.test_my_opportunities_qualification tests.test_my_opportunities_criteria tests.test_my_opportunities_canonical -v
```

At the frozen candidate: `tests.test_my_opportunities_retrieval` runs 101
tests — 100 pass, and exactly one honestly fails —
`RetrievalMigrationTests.test_c4_migration_registry_and_verifier_are_bounded_and_gate_proven`
fails with `TypeError: 'NoneType' object is not subscriptable` at
`gate["executable_sha256"]`, because the registry entry's `"gate": null` has
not been proven yet (nothing downstream of that line in the test runs — the
same honest-failure shape as C5's equivalent test before its gate proof was
recorded). The C2/C3/C5 regression suites
(`test_my_opportunities_canonical`, `test_my_opportunities_criteria`,
`test_my_opportunities_qualification`) run 127/127 green; this package
touches none of their files. `docs/governance/PACKAGE_REGISTRY.json` is not
in this claim's surfaces and the test suite does not assert against it (no
package-registry-entry test exists in this file, unlike C5's).

Per-group tally (101 total, 100 green + 1 honest null-gate failure): A
Registration 15 · B Worker binding 7 · C Rechecks 5 · D Matching/scope 7 ·
E Partial executions 11 · F Degraded modes 3 · G Reduced coverage 3 ·
H Pagination/restoration 6 · I TTL 3 · J Ordering 9 · K Cross-member/REC-05
8 · L Index fence 4 · M Truth bindings 4 · N C5-integration 3 ·
O SQL/registry file-content 13. A subsequent self-review pass (this same
worktree/branch, after phase 2) fixed several correctness defects the
original phase-1/phase-2 tests did not catch and added the binding
regression test for each — see "Self-review corrections" below; group A
grew from 8 to 15 and group K from 7 to 8 as a direct result.

## Current state

Phase 2 (SQL trio, registry entry, SQL/registry file-content test group, and
these initiative docs) is complete on
`work/2026-08-31-myopp-retrieval-001`, following phase 1 (the four service
modules and test groups A–N, all green). The disposable migration-gate
proof, the package-registry activation, and the independent exact-SHA review
are still outstanding before repository merge; see the completion record.

## Self-review corrections

A follow-up execution-verified self-review found and fixed defects across
both phases in the same worktree/branch, each with a new binding regression
test (test names in the corresponding group above):

- **§2a write-ordering violation (two rounds; FINDING 3 correction below is
  accurate as of the second round).** `search_worker.py`'s write windows
  now re-read the execution immediately before every write and, if it
  already reached ANY terminal state through another path (a member cancel
  is the only concurrent writer), return that re-read record unchanged
  instead of overwriting it or raising. This is now true of **every**
  write window in `run()`: `_transition_stage` (used by the
  retrieving/assessing/ordering stage transitions), `_terminal_failed` and
  `_terminal_authorization_changed` (re-read internally, so every one of
  their call sites — the start recheck, the post-`_retrieve` failure path,
  and the final recheck's authorization-changed path — is covered
  uniformly), the post-retrieval direct write, the pre-persist-snapshot
  re-read (the snapshot is never even attempted against an
  already-terminal execution), and the final complete/partial write
  (re-read again immediately before it, since a cancel can still land in
  the narrow gap after persist_snapshot succeeds). A first round covered
  three of these windows explicitly; an independent review of the frozen
  candidate found the persist-snapshot window and two `_terminal_failed`
  call sites still unguarded (a cancel racing exactly one of those windows
  could either see a snapshot for a cancelled search, or make `run()`
  escape with an unhandled `RepositoryWriteError` when `save_execution`'s
  own transition guard refused to write a failed/complete/partial state on
  top of an already-cancelled row) — both are fixed now, with two binding
  regression tests (`RegistrationTests.
  test_cancel_racing_the_persist_write_returns_cancelled_record_with_no_snapshot`,
  `test_cancel_racing_the_retrieve_read_before_terminal_failed_write_returns_cancelled_record`)
  that inject the cancel from *inside* the persist call and *inside* the
  canonical read `_retrieve` depends on — narrower than the earlier
  `test_cancel_mid_run_writes_no_snapshot`, which only exercises the
  already-guarded per-entry checkpoint. `InMemoryRetrievalRepository.
  persist_snapshot` now backstops this exactly like SQL: it refuses
  (`RepositoryWriteError`) unless the parent execution's state is
  `ordering`/`complete`/`partial`, mirroring SQL `THROW 55731` on
  `trg_myopp_result_snapshots_immutable` (now guarding on `INSERT` too, not
  only `UPDATE`/`DELETE`) — the same invariant proven at both layers. A
  matching broadened `trg_myopp_search_executions_transition_guard`
  (`THROW 55725` fires on ANY update of an already-terminal row, not only
  one that changes `state`) gives the state-machine half of the same
  invariant its own schema-level proof.
- **Write-window basis (independent-review FINDING 7, MINOR).**
  `_transition_stage` re-read the current record to decide whether to
  short-circuit for a terminal state, but then built its update from the
  caller's stale local `execution` copy rather than that re-read record.
  Harmless whenever the two happen to agree (the only concurrent writer,
  `cancel()`, only ever produces the terminal state the short-circuit
  already catches), but not a safe assumption to build on — now every
  guarded write window builds its update from the freshly re-read record.
- **Fence exception over-catching.** `index_fence.py`'s `resolve_opportunity`
  catch narrowed to `MyOpportunitiesCanonicalError` only; a genuine
  canonical-store outage during fencing now propagates to the worker, which
  records `partial(index_failure)` with its existing disclosure instead of
  silently mis-reporting the outage as ordinary `opportunity_missing` drops
  (a complete-looking, zero-result execution).
- **Open criterion vocabulary reaching the matcher unchecked.** C3's
  `Criterion.kind` vocabulary is open by design; C4 v1 supports only
  `SUPPORTED_CRITERION_KINDS`/`SUPPORTED_STRUCTURED_CRITERION_KINDS`
  (`retrieval_service.py`). `register_execution` now refuses an unsupported
  criterion kind or direct-filter key at registration with the closed code
  `criterion_unsupported` — identical for every unsupported kind, no
  vocabulary oracle. The matcher's own fail-closed handling of an
  unrecognized kind remains as unreachable defense-in-depth.
- Duplicate fence-admitted opportunity_key slots are now deduplicated (max
  relevance, first-seen tiebreak) before the post-fence resolution loop.
- The fence now validates `retrieval_relevance` itself (finite,
  non-negative int/float) as part of its shape check, not only the
  projection document's fields.
- `_bounded_string` now raises the distinct `*_too_long` code on an
  over-length value (it previously always raised `*_required`, making
  `user_key_too_long` unreachable — the C5 precedent it was meant to
  mirror).
- `results()` with no `display_resolver` wired now raises the distinct,
  non-member-identifying `display_resolver_unavailable` rather than
  `not_found` (an integration defect is not the same fact as "nothing here").
- `rebuild_index` no longer silently swallows a `canonical_gate` exception;
  it is counted in the returned `RebuildIndexResult.skipped_gate_failures`
  so a truncated rebuild is visible to a caller (C9) rather than looking
  like ordinary non-eligibility. One opportunity's gate failure still does
  not abort indexing the others.
- Several tests admitted two "distinct" fixture candidates that actually
  shared employer/title/locations/host and so silently collapsed into ONE
  canonical opportunity (`canonical_service._match_or_create`'s exact-match
  rule keys on those fields, not `external_reference`) — several
  ceiling/precedence/partial-state tests were exercising a degenerate
  single-opportunity scenario without ever detecting it. Fixed by giving
  every such fixture a distinct title, and by adding the `final.state ==
  "partial"` assertions those tests' own names had always promised but
  never checked.
- The partial-reason precedence test now genuinely produces **both**
  `assessment_persistence_failure` and `budget_exhausted` in the same run
  (deterministically, regardless of the random opportunity_key sort order)
  and asserts both causes' disclosures are present — precedence picks the
  headline `partial_reason`, it does not erase the other cause's evidence.
  This also surfaced a real gap: `assessment_persistence_failure` was never
  named in `disclosures[]` at all (only the audit event fired) — fixed in
  `search_worker.py`.
- `test_broader_chain_uses_no_preferred_count_and_no_unmet_signal`'s
  original entry names happened to agree with both the correct
  (opportunity_key-only) order and the order a preferred-count bug would
  produce, so it could not actually catch that bug; renamed the entries so
  the two orders disagree.
- `test_ordering_uses_no_wall_clock_or_randomness` only tripwired the bare
  sort-key functions; rewritten to run the real worker end to end under the
  armed tripwires, twice, with two different injected `now` values.
- Two tests' bodies did not test what their (blueprint-bound) names and
  binding descriptions promised:
  `test_direct_filter_parity_manual_and_ai_snapshots_produce_identical_entries_and_order`
  only compared `matches_criteria()` in isolation and never built or ran
  either snapshot; `test_purge_is_content_blind_key_and_age_only`'s own
  binding description calls for "a repository stub whose content accessors
  raise" and the original body never built one. Both bodies now do what
  their names say.
- Three verifier assertions all threw `55770`; two renumbered to
  `55777`/`55778`, and the repo-wide THROW-uniqueness test now counts raw
  occurrences per file (not a deduplicated set), so intra-file reuse like
  this is itself caught by the suite going forward.
- `terminal_at_utc` is now asserted `>=` every non-null stage timestamp in
  `CK_myopp_search_executions_timestamp_order` (it was previously only
  ordered against the terminal/non-terminal state pairing, not the
  individual stage timestamps).
- The entries→snapshots and snapshot→execution FKs now additionally pair
  on `data_class` (two new class-inclusive `UNIQUE` constraints plus the
  extended composite FKs), and `trg_myopp_result_entries_immutable` gained
  the same `IF EXISTS (SELECT 1 FROM inserted)` no-op guard the snapshots
  trigger already had, for consistency.
- `register_execution`'s conflict oracle (own key/different binding vs. a
  different owner presenting the same key) was already structurally
  indistinguishable (`execution_key_conflict`, same message, in both
  cases) but had no test proving it; added one, alongside a same-key/
  same-binding idempotent-replay assertion in the same test.

## Known limitations and forward obligations

Recorded truthfully; none blocks this repository merge, and none may be
silently forgotten.

### From the blueprint's recorded mechanical consequences (§11 — not owner
decisions; REC-02/03/05/07 are already accepted, so nothing here blocks)

1. **Result-snapshot retention window.** Doc 15 §3 defers the retention
   value to C4 as persistence owner. This package ships **90 days** as an
   explicit, named configuration constant
   (`retrieval_service.DEFAULT_RESULT_RETENTION`), mechanism-independent —
   enforcement is a separate content-blind TTL job that is C9's to schedule,
   not this package's. Pete may record or amend the value at his
   convenience; nothing in C4 blocks on it.
2. **`failed(snapshot_persistence_failure)`.** Doc 03 §4's `failed(reason)`
   vocabulary is open-valued; a snapshot-write failure needs a truthful
   terminal reason (doc 09 §4 forbids inventing success or leaving an
   outcome silently unknown). This is a mechanical addition to the reason
   vocabulary, not new policy — no member truth is fabricated, and retry is
   always a new Apply.
3. **Partial-reason precedence.** When one execution hits more than one of
   the five §11 partial causes, exactly one closed reason must be stored on
   the terminal record; the deterministic order is
   `PARTIAL_REASON_PRECEDENCE` (assessment-persistence-failure highest,
   then index-failure, provider-failure, timeout, budget-exhausted lowest),
   with **every** triggered cause still named in `disclosures[]`. Pure
   determinism bookkeeping, not a policy choice about which cause "matters
   more."
4. **Spec-construction classification (C2-classification conservative
   mapping).** C2's stored `requirement_item` carries no stated
   required/preferred classification, so
   `spec_from_requirement_version` maps every item
   `requirement_class="required"`,
   `classification_basis="ambiguous_default_required"` — exactly REC-06's
   already-accepted conservative default: this can only ever *withhold*
   `Fully verified`, never overclaim it, and the flagged basis is
   member-visible truth on every entry it touches. **Forward obligation:**
   when C2 later persists a stated required/preferred classification, this
   mapping must read it instead — a C4-local code change with no schema
   impact, and no other part of this package depends on the conservative
   default remaining in place.
   **Direct consequence for ordering and display (self-review MINOR 21):**
   because every item is mapped `requirement_class="required"`, no item is
   ever classified `"preferred"` today, so every entry's `preferred_summary`
   is permanently `(verified=0, total=0)` and `qualified_sort_key`'s chain
   position 1 (`-preferred_verified`) is inert — it can never distinguish
   two qualified entries until C2 gains stated classification. This is the
   same forward obligation as above, not a separate defect: the ordering
   chain and the ranking test coverage are correct and already exercise
   this position with non-zero synthetic values; it is only C2's current
   data that makes it unreachable in a live snapshot.

### Phase 1's own notable conservative resolutions (implementation-level,
flagged here for visibility, not re-litigated)

5. **Single-basis display attribution.** `display_attribution_refs` on every
   result entry maps every display field name to the same one
   `governing_source_version_key` (`search_worker._display_attribution_refs`)
   rather than a per-field provenance map. This is correct under the current
   C2 model, where one governing source version is the sole basis for every
   displayed fact on an entry; if C2 ever admits per-field attribution across
   more than one version, this function is the one place to extend.
6. **Display compensation field is unpopulated by C2 today.** The fenced
   serializer's `display_projection.compensation` reads
   `version.fields.get("compensation")` — C2 has no named, structured
   display-compensation field yet, so this reads the same generic free-text
   `fields` bag every other unstructured display fact reads from. The field
   renders `null` (C8: "Not stated") until C2 adds a named compensation
   field; nothing in C4 assumes compensation is populated.
7. **The in-memory discovery-index fake ignores its own `filters`
   parameter.** `InMemoryDiscoveryIndex.search` explicitly discards the
   `filters` argument (`del filters`) — matching happens once, downstream,
   in the worker's own deterministic `matches_criteria` re-check
   (§5.2 step 3c), which every candidate must pass regardless of retrieval
   path. This is intentional: the fake exists to prove the retrieval-path
   plumbing and the post-fence re-check, not to prove a real index's filter
   semantics, which do not exist yet (REC-02 grants no provisioning
   authority at this phase — see "Carried forward from C5's review" below).
   The structured/free-text kind split that decides what goes into
   `filters` at all is no longer a bookkeeping-only categorization: BLOCKER
   3 (self-review) promoted it to `retrieval_service.SUPPORTED_CRITERION_KINDS`,
   a closed, registration-enforced vocabulary.
8. **The index path re-derives its canonical basis after the fence admits.**
   The post-fence resolution loop in `search_worker._retrieve` never trusts
   a fence-admitted `ProjectionDocument`'s own fields for anything beyond
   identity and `retrieval_relevance` — it calls the exact same
   `_admission_basis` the canonical path uses, resolving the real
   `SourceVersion`/`RequirementVersion` objects the matcher and C5 spec
   construction need. A canonical-store failure during that recheck is
   scoped to `partial(index_failure)` (self-review BLOCKER 2 / IMPORTANT 4),
   distinct from the canonical direct-enumeration path's
   `partial(provider_failure)` — two different mid-run failure surfaces,
   two different closed reasons.
9. **`RetrievalService.__init__` gained a `display_resolver` parameter and
   `rebuild_index` gained `canonical_service`/`now` parameters.** Neither
   is in the blueprint's own constructor/signature snippets, but §4.4's
   display-resolution and doc 02 §4's gate-eligible rebuild cannot be
   implemented at all without a canonical-read seam and a clock — these are
   structural fill-ins the code cannot function without, not policy
   choices. Any object exposing `.version(key)`/`.listing(key)` (a
   `CanonicalRepository` works directly) satisfies `display_resolver`.
10. **`results()` with both/neither of `result_key`/`execution_key`
    refuses as `not_found`, not a distinct code**, and `snapshot_key`/
    `execution_key` on `register_execution` are validated for
    presence/type only (no length ceiling) — the closed failure-code list
    has no `*_too_long` variant for either, so none is invented; a
    pathologically long opaque key still fails safely downstream as
    `not_found`.
11. **`ExecutionStatus` and `ResultsPage` are mechanical read-model
    dataclasses**, not part of the blueprint's closed §4.1 vocabulary
    (which defines the method signatures that return them but not their
    own shapes).
12. **`_admission_basis`'s `resolve_opportunity` catch is narrowed to
    `MyOpportunitiesCanonicalError`** (self-review BLOCKER 2's sibling
    fix, applied the same way in `search_worker.py`): an expected absence
    is an ordinary per-candidate drop; any other exception type (a genuine
    storage outage) is left to propagate so the canonical direct-
    enumeration path's mid-run `partial(provider_failure)` distinction
    (§5.2 3b) is reachable at all, rather than every canonical-store
    failure silently degrading to an empty drop.
13. **Cross-owner `execution_key` existence is signal-distinguishable, even
    though the refusal bytes are identical (independent-review FINDING 6).**
    `register_execution`'s "own key, different binding" and "a different
    owner holds this key" cases both raise the byte-identical
    `execution_key_conflict` (same code, same member message — see test
    group A's oracle-indistinguishability test); a truly-absent key instead
    replays idempotently or proceeds to create. An attacker who can already
    guess or observe another member's opaque `execution_key` (a random
    128-bit `uniqueidentifier`/uuid4) *can* distinguish "this exact key is
    held by someone" from "this exact key is unused" by whether they get
    `execution_key_conflict` vs. a successful registration — the response
    shape carries no member identity, but existence itself is a narrow
    signal. **Forward obligation:** an owner-scoped key namespace (deriving
    or salting `execution_key` per-owner, or requiring a matching
    `snapshot_key` before the conflict check can even run) would close this;
    not addressed here, since it is member-invisible in the normal
    application flow and the 128-bit keyspace makes guessing/enumeration
    infeasible in practice.
14. **The doc-04-mandated fence drop of a stale index document is a
    member-invisible recall gap until the next index rebuild (independent-
    review FINDING 8).** When canonical truth moves out from under a
    `ProjectionDocument` (a new governing source version, a requirement
    change), the fence correctly refuses to admit the stale document
    (`governing_version_mismatch`) rather than ever serving stale content —
    but the opportunity then simply does not appear in that search's
    results at all, with no member-visible signal that anything was
    withheld (unlike an explicit `entry_dropped`/`fence_dropped` disclosure
    for the causes members already see). This is the correct fail-closed
    choice (doc 04 §10: never surface index-only or stale data), and
    `rebuild_index` closes the gap the next time it runs — REC-02 grants no
    provisioning authority yet, so there is no live index or a scheduled
    rebuild cadence to point to today. Not addressed here; a future C9/index
    job owns deciding an acceptable staleness bound.
15. **An unexpected exception from `assess_requirements` or `index.search`
    strands an execution non-terminal until TTL abandonment (independent-
    review FINDING 9).** Every *expected* failure path the worker
    recognizes converts to a truthful terminal state (`failed`/`partial`
    with a closed reason); an exception type genuinely outside that closed
    set (a defect in a dependency, not one of the doc 04 §9 degraded modes)
    propagates out of `run()` uncaught rather than being caught and
    converted, leaving the execution in whatever non-terminal stage it was
    in. This is bounded, not unbounded: `purge_abandoned_executions`
    reclaims it after `limits.abandoned_ttl` (doc 03 §4's own TTL
    abandonment path) exactly like any other interrupted search, and no
    snapshot or member result is ever fabricated in the meantime. Noted as
    a hardening candidate — a defensive catch-all at the top of `run()`
    that converts any otherwise-unhandled exception to a truthful terminal
    `failed` state would shorten that window from "up to the TTL" to
    "immediate," but is a deliberate scope decision to make explicitly, not
    slipped in as an unreviewed catch-all; not addressed here.

### Carried forward from C5's review (respect, don't fix)

- **No erasure path yet on C5's tables; `evidence_key` is code-fenced, not
  schema-fenced.** C4 adds **no** write path that widens either exposure: C4
  stores no evidence identifier anywhere — its entries reference
  opportunity/requirement-version/source-version keys only, and any
  assessment linkage remains reachable solely through C5's own owner-scoped
  reads. C4's own three tables share the same known limitation: member
  delete/export integration for executions/snapshots/entries is the
  account-data package's future obligation, not addressed here.
- **The retention TTL job is C9's to schedule.** `purge_abandoned_executions`
  (the content-blind primitive) and `DEFAULT_RESULT_RETENTION` (the named
  constant) are both C4's; wiring either into a scheduled job is not.
- **The index P-2 disposable proof is deferred until an index is actually
  selected and provisioned** — not in this phase. REC-02 grants no
  provisioning or spend authority; `InMemoryDiscoveryIndex` is a fake for
  contract and fence testing only.
- **The C8 alias/copy rendering obligations consume, not change, C4's
  constants** — `LOADING_COPY`, the `"Not stated"`/`"unavailable_under_rights"`
  rendering rules, and the staleness disclosure text are all fixed here;
  C8's job is to render them verbatim, not to reinterpret them.
