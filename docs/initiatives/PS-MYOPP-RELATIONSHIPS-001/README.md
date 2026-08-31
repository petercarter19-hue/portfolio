# PS-MYOPP-RELATIONSHIPS-001 — C6 owner-bound saves and Slate-link persistence

This Protected child implements the accepted My Opportunities C6 relationship
runtime: the doc 03 §7 owner-scoped save/remove/undo machine with an undo
window and terminal `removed` rows, DERIVED (never persisted) lifecycle
overlays read against canonical listing truth and the member's own
last-reviewed basis, the owner-filtered saved view with local search/filter,
the doc 03 §8 Slate-link record shape and persistence primitives (one active
link per member and opportunity), the doc 09 §4 unknown-outcome write
discipline, and the additive `PS-MYOPP-005` SQL trio.

## Outcome

- `services/my_opportunities/relationships_service.py` — the closed
  vocabulary (save states, presentation overlays, saved-view filters,
  verification filters, Slate-link states and `created_from` sources), the
  record shapes (`SavedOpportunity`, `SlateLink`, `GoverningBasis`,
  `SavedDisplayFacts`, `SavedListEntry`), the `GoverningBasisReader`/
  `VerificationReader` read seams, the `RelationshipsRepository` Protocol and
  its in-memory reference implementation with a transition-guarded save/link
  machine, the pure `derive_lifecycle_overlays` function, `RelationshipsService`
  (save/remove/undo/mark-reviewed/get/list/finalize, plus the Slate-link
  persistence primitives `record_slate_link`/`mark_slate_unlinked`/
  `list_slate_links`), and the doc 09 §4 blind-retry lockout.
- `tests/test_my_opportunities_relationships.py` — groups A-I: the save
  machine, remove/undo/window, overlay derivation and its service
  integration (including REC-03 per-member clearing), the saved view's
  local search/filter, Slate-link persistence, cross-member negative
  proofs, the unknown-outcome write discipline, contract-freeze/vocabulary-
  closure shape tests, and the SQL/registry file-content group.
- The additive, governed `PS-MYOPP-005` migration
  (`myopp_saved_opportunities`, `myopp_slate_links` and their guard
  triggers/filtered-unique-indexes/read indexes), its fail-closed rollback,
  its catalog verifier, and the repository registry entry (pre-proof,
  `"gate": null`).

## Scope exclusions (hard)

No route or UI, no C7 handoff commands (`create_slate_from_opportunity`,
`continue_slate`, `list_slate_history` are C7's — this package persists only
`slate_link`'s table, vocabulary, and primitives), no provider work, no
change to any C2 (`canonical_service.py`), C3 (`criteria_service.py`,
`interpretation_service.py`), C4 (`retrieval_service.py`,
`search_worker.py`, `index_projection.py`, `index_fence.py`), or C5
(`qualification_service.py`, `evidence_port.py`) file, no
deployment/enablement, and no production or staging schema action. A
disposable migration-gate database needs its own bounded owner
authorization and is not this file's authority. Domain:
`runtime:my-opportunities:relationships`.

## Authorities

- Doc 03 §§1-2, 7 — save/remove/undo machine, presentation overlays, saved
  view (and §§1-2 as the overlay inputs REC-03 governs)
- Doc 03 §8 — Slate-link vocabulary, table, and the "continue, don't
  duplicate" active-link invariant
- Doc 02 §§1, 4, 6 — reference-only bindings (never copies), save
  persistence surviving snapshot TTL deletion, fixture isolation
- Doc 08 §§1, 3, 4, 5, 7 — overlay derivation as the system read role,
  authorization-before-retrieval, content-free audit events, TTL discipline,
  cross-member negative proofs
- Doc 09 §§3-4 — C3-pattern idempotency, error shape, unknown-outcome write
  discipline. (Doc 09 §2, optimistic concurrency via a read token, is
  **not** implemented by this package -- see "Known limitations" item 10;
  this citation deliberately excludes §2 rather than claiming it satisfied.)
- Doc 04 §8 — stale-snapshot overlay rendering (the same pure derivation
  C8 reuses for result-time bases)
- Doc 16 rows 31, 32, 34, 35, 55, 65, 68 — every C6 traceability row
- Doc 15 §2 REC-03 (accepted 2026-08-24) — the per-member `posting_changed`
  re-admission disposition
- Doc 14 "### C6" — outcome, reservations, and the four stop controls
- Precedent mirrored throughout: C5 (`qualification_service.py`, the
  `PS-MYOPP-003` trio), C4 (`retrieval_service.py`, the `PS-MYOPP-004`
  trio), C3 (`criteria_service.py`, the `PS-MYOPP-002` trio), C2
  (`canonical_service.py`, `PS-MYOPP-001`)
- Implementation blueprint: `C6_ARCHITECTURE.md` (§0-§13), written against
  `origin/main` post-C4-merge with `PS-MYOPP-004`'s gate proven; the
  implementer made no policy decisions — every closed enum, algorithm step,
  and SQL DDL element is either quoted from the governing docs or an
  explicitly recorded mechanical/conservative consequence (see "Conservative
  resolutions" below and blueprint §11).

## Delivered files

| File | Content |
|---|---|
| `services/my_opportunities/relationships_service.py` | Closed vocabulary, error type, `RelationshipsRepository` Protocol + in-memory repo with the transition-guarded save/link machine, save/remove/undo/mark-reviewed/get/list/finalize, the pure overlay derivation, Slate-link persistence primitives, the unknown-outcome lockout |
| `tests/test_my_opportunities_relationships.py` | Groups A-I (save machine, remove/undo/window, overlays + service integration, saved-view search/filter, Slate-link persistence, cross-member negative proofs, unknown-outcome discipline, contract-freeze/vocabulary-closure, SQL/registry file-content) |
| `SQL FIles/Migrations/PS-MYOPP-005_relationships.sql` | Additive forward migration: `myopp_saved_opportunities`, `myopp_slate_links`, their guard triggers, filtered unique indexes (one active save/link per member+opportunity), and owner-scoped read indexes |
| `SQL FIles/Migrations/PS-MYOPP-005_relationships_rollback.sql` | Fail-closed rollback: refuses on a later ledger row or any C6 member data; drops triggers before tables, links before saves |
| `SQL FIles/Verification/PS-MYOPP-005_relationships_verify.sql` | Real catalog assertions: owner fencing, closed save/link/created_from/data_class vocabularies, state/timestamp pairing CHECKs, both filtered unique indexes, both guard triggers enabled, owner-safe FK census with an allowlisted-target scan, forbidden copied-content/overlay/scoring column scan, id/user/data_class composite uniqueness |
| `SQL FIles/Migrations/registry.json` | One appended `PS-MYOPP-005` entry, last in the array, `"gate": null` pre-proof — the disposable gate proof is a separate, later, bounded owner authorization, not this package's authority |
| `tests/test_my_opportunities_retrieval.py` | Claim extended (control PR 807) to include this file; one test's body rewritten (self-review IMPORTANT 5, the registry "is-last" fragility) — no other change |

`PS-MYOPP-005` adds only owner-fenced saved opportunities and owner-fenced
Slate links. Its forward migration, rollback, verifier, and registry entry
are repository candidate artifacts only; merge will not apply schema,
deploy, enable, contact a provider, or change production.

## How to run the tests

```bash
python3 -m unittest tests.test_my_opportunities_relationships -v
python3 -m unittest tests.test_my_opportunities_retrieval tests.test_my_opportunities_qualification tests.test_my_opportunities_criteria tests.test_my_opportunities_canonical tests.test_package_registry -v
```

`tests.test_my_opportunities_relationships` runs **87 tests, all green**.
The `PS-MYOPP-005` disposable-database gate proof is DONE (attempt a3,
`gate_database` `ps-myopp-c6-gate-20260831-a3`, recorded in
`SQL FIles/Migrations/registry.json`) and the package is registered in
`docs/governance/PACKAGE_REGISTRY.json`, so
`RelationshipsMigrationTests.test_c6_migration_registry_and_verifier_are_bounded_and_gate_proven`
now passes against the real, populated `"gate"` object rather than erroring
on `"gate": null` (the pre-proof phase's designed honest failure, no longer
applicable once the gate is proven).

Per-group tally (87/87 green): A Save machine 11 · B Remove/undo/window 10
· C Overlay derivation (pure) 9 · C-integration Overlay service integration
8 · D Saved-view search/filter 10 · E Slate-link persistence 7 ·
F Cross-member negative proofs 5 · G Unknown-outcome discipline 8 ·
H Contract-freeze/vocabulary-closure 5 · I SQL/registry file-content 14.

Full acceptance run across all six suites (`relationships` + `retrieval` +
`qualification` + `criteria` + `canonical` + `package_registry`): **320
tests, all green** (87 + 104 + 79 + 15 + 33 + 2).

### A regression-suite fragility this session found AND fixed (self-review IMPORTANT 5)

Appending `PS-MYOPP-005` last to the shared `registry.json` originally broke
one pre-existing C4 test:
`RetrievalMigrationTests.test_registry_entry_shape_and_requires` hard-coded
`migrations[-1] is entry` for the `PS-MYOPP-004` row -- an assumption true
only until the next package's append. This package's claim was extended
(control PR 807) to include `tests/test_my_opportunities_retrieval.py`,
which let this session fix the fragility at its root instead of only
documenting it: both that test and this package's own equivalent
(`test_every_migrations_requires_appear_earlier_in_the_array`) now assert
the durable, order-relative invariant registry.json's own `$comment`
("apply order = list order") actually needs -- every migration's
`requires` entries appear earlier in the array than the migration itself --
rather than "this one entry is literally last." That closes the fragility
class for every future package append, not only this one.
`tests.test_my_opportunities_retrieval` now runs **104/104 green**.
`tests.test_my_opportunities_qualification` (79/79),
`tests.test_my_opportunities_criteria` (15/15), and
`tests.test_my_opportunities_canonical` (33/33) remain fully green.

## Self-review corrections

A self-review scan of the frozen candidate found and fixed defects across
the SQL trio, the service module, and the test suite, each with a binding
regression test (test names in the corresponding group above):

- **BLOCKER 1 — invalid T-SQL Boolean comparison.** All three sites in
  `PS-MYOPP-005_relationships.sql`'s guard triggers wrote
  `(x IS NULL) <> (y IS NULL)` to detect a NULL/non-NULL change — this is
  not valid T-SQL (a Boolean expression cannot itself be compared with
  `<>`); the migration would have failed to apply. Replaced with the
  repo's value-level `ISNULL(i.col, N'00010101') <> ISNULL(d.col, N'00010101')`
  datetime-sentinel idiom (PS-MYOPP-001 pattern) at all three sites: the
  `removal_requested_at_utc`/`removed_at_utc` timestamp-discipline check on
  `trg_myopp_saved_opportunities_guard` (THROW 55788) and the
  `unlinked_at_utc` check on `trg_myopp_slate_links_guard` (THROW 55793).
- **BLOCKER 2 — REC-03 review dead-end.** While `basis.listing_state ==
  "changed"` (mid re-verification), `derive_lifecycle_overlays`'s rule 2
  keeps `posting_changed` live regardless of whether the submitted version
  matches the current governing head — so the original `mark_change_reviewed`
  would accept a write that could never actually clear the overlay while
  the listing stayed "changed," a silent no-op success. Adjudicated (option
  b): `mark_change_reviewed` now refuses `review_version_not_governing`
  outright whenever `basis.listing_state == "changed"`, before the
  version-comparison check, with no write/receipt/audit event on refusal.
  Version-comparison clearing is unchanged for every other listing state.
  Member-facing copy updated to "This posting is being re-verified. Review
  it again once the update is confirmed." Tests:
  `test_mark_change_reviewed_refuses_while_listing_state_is_changed_no_mutation`
  (refusal, digest/audit unchanged) and
  `test_mark_change_reviewed_succeeds_when_version_moved_and_listing_is_current`
  (the successful-clear sibling); the existing
  `test_mark_change_reviewed_clears_posting_changed_for_that_member_only`
  is unaffected (its scenario uses `listing_state="current"`).
- **IMPORTANT 3 — MERGE-unsafe erasure-block predicate.** Both guard
  triggers' DELETE-block checks used
  `EXISTS(deleted) AND NOT EXISTS(inserted)`, which a `MERGE` statement
  can defeat (it can populate both `inserted` and `deleted` in one firing
  even for rows it deletes). Adopted the MERGE-safe C4/C5 form:
  `FROM deleted d LEFT JOIN inserted i ON i.<pk> = d.<pk> WHERE i.<pk> IS NULL`,
  on both `trg_myopp_saved_opportunities_guard` (THROW 55784) and
  `trg_myopp_slate_links_guard` (THROW 55790).
- **IMPORTANT 4 — fragile `filter_definition` byte-equality.** The
  verifier compared the catalog's `filter_definition` against a literal
  string (`N'([state]<>''removed'')'`), which is not guaranteed stable
  across SQL Server versions/pretty-printing. Adopted PS-MYOPP-001's
  normalization idiom (lowercase, strip brackets/parens/whitespace via a
  `CROSS APPLY` chain, compare against a precomputed normalized literal)
  for both `UX_myopp_saved_opportunities_active` and
  `UX_myopp_slate_links_active` (THROW 55819). `test_filtered_unique_index_definitions_verbatim`
  updated to assert the normalized literals (`N'state<>''removed'''` /
  `N'state=''linked'''`) rather than the old byte-exact form.
- **IMPORTANT 5 — registry "is-last" fragility, found AND fixed.** See "A
  regression-suite fragility this session found AND fixed" above and
  "Known limitations" item 9: both this package's own registry test and
  `tests/test_my_opportunities_retrieval.py`'s equivalent (now a claimed
  surface) were rewritten from an absolute "this entry is last" assertion
  to the durable, order-relative "every `requires` id appears earlier in
  the array" invariant. New/renamed tests:
  `test_every_migrations_requires_appear_earlier_in_the_array` (this
  package) and the rewritten body of
  `RetrievalMigrationTests.test_registry_entry_shape_and_requires` (C4's
  file).
- **IMPORTANT 6 — unknown-outcome suite only covered the did-not-land
  branch.** `FailingRelationshipsRepository` only ever raised BEFORE the
  underlying write ran, so no test exercised the landed branch (write
  succeeds durably, confirmation is lost, retry must discover the landed
  row via natural idempotency rather than duplicate it). Added a
  `fail_mode` parameter (`"pre"`/`"post"`) so a `"post"` failure lets the
  write complete against the in-memory store and then raises. New test
  `test_state_reload_unlocks_retry_returns_the_landed_save_when_persist_did_land`
  proves the retry returns the SAME `save_key` with no duplicate row. The
  existing test that had incorrectly claimed to cover this branch was
  renamed to `test_state_reload_unlocks_retry_is_fresh_write_when_persist_did_not_land`
  with a corrected docstring describing what it actually tests (its
  sibling for `update_save`/`remove_saved` was renamed
  `test_state_reload_unlocks_retry_is_fresh_write_when_update_did_not_land`
  for naming consistency).
- **IMPORTANT 7 — doc 09 §2 (optimistic concurrency) was cited as if
  satisfied.** It is not implemented: no mutation takes a read token or
  version precondition, and the SQL `row_version` columns exist unread.
  The "Authorities" citation was narrowed from "Doc 09 §§2-4" to "Doc 09
  §§3-4" with an explicit note that §2 is excluded, and "Known
  limitations" item 10 records the gap honestly (last-write-wins on
  concurrent `mark_change_reviewed`/other mutations; threading a token is
  a C8-composition-era obligation) per explicit adjudication: record, do
  not implement now.
- **MINOR 8 — replay staleness.** `save_opportunity` and `remove_saved`
  previously echoed the frozen object captured at receipt time on replay.
  Per adjudication, both now re-render LIVE state on replay (through the
  same `_finalize_if_elapsed` path every other read uses) via the new
  `_replay_save` helper — the receipt still proves identity/no-duplication,
  but the returned snapshot reflects current truth (e.g. a row that has
  since finalized to `removed`, with no undo affordance). Tests:
  `test_replay_after_terminal_finalization_returns_removed_with_no_undo_affordance`
  and `test_save_opportunity_replay_re_renders_live_state_not_frozen_receipt`.
  Recorded as a deliberate divergence in "Known limitations" item 11.
- **MINOR 9 — `get_saved` didn't clear the unknown-outcome lock before its
  removed-row refusal.** A locked member whose only row was `removed`
  could not unlock via `get_saved` (the lock-clearing call ran only after
  the `not_found` raise, which never executed). Moved
  `_clear_unknown_outcomes` to run immediately after a successful owner
  load, before the removed-row check. Test:
  `test_get_saved_on_removed_row_still_clears_the_lock_minor_9`.
- **MINOR 10 — two SQL-enforced timestamp invariants were unenforced in
  Python.** `CK_myopp_saved_opportunities_removal_after_save`
  (`removal_requested_at >= saved_at`) and the `unlinked_at >= created_at`
  clause of `CK_myopp_slate_links_state_timestamps` now have matching
  `__post_init__` checks on `SavedOpportunity`/`SlateLink`. Test:
  `test_python_post_init_mirrors_the_sql_timestamp_ordering_checks`
  (including the legal `>=` boundary case).
- **MINOR 11 — weak import-fence assertion.** A plain
  `"import slate" not in source.lower()` substring search both misses
  non-substring import spellings and can false-positive on unrelated text.
  Replaced with an `ast.parse` walk collecting the module's actual
  `Import`/`ImportFrom` names and asserting none contains `"slate"`.
- **MINOR 12 — dead-code residue.** Deleted a no-op
  `x if False else y` construct in
  `test_lazy_finalization_reads_as_removed_and_excluded_from_list`.
- **MINOR 13 — FK allowlist scan lacked a schema predicate; OTCR overclaimed
  verification depth.** The verifier's owner-safe FK census compared
  `referenced_table.name` against the allowlist without qualifying by
  schema; a same-named table in a different schema could have silently
  satisfied it. Added `SCHEMA_NAME(referenced_table.schema_id) = N'dbo'`
  to the comparison. Separately, the OTCR's "checked programmatically"
  claim about verifier/forward-migration name consistency was softened to
  state plainly what was actually done (name-consistency plus Python-side
  text/byte-equality checking, not SQL execution or parsing) and that
  parseability/behavioral correctness is what the still-outstanding
  disposable-database gate proof supplies.

### Round 2 — independent review of frozen candidate `c8a304f2` (REVISE)

- **BLOCKING 1 — `save_opportunity` during the undo window silently
  no-op'd and the item still disappeared.** `save_opportunity`'s
  "already active" short-circuit (`relationships_service.py`, inside
  `save_opportunity`) admitted a `removing`-state row as "existing,"
  wrote nothing, and echoed success -- so a member who pressed Save while
  the row was mid-removal saw an apparent success, but the row still
  finalized to `removed` when the window elapsed, because nothing had
  actually cleared `removal_requested_at`. Adjudicated: a Save pressed
  during the window expresses intent to KEEP the item, so it now performs
  the doc 03 §7 `removing -> saved` UNDO transition -- structurally
  identical to `undo_remove` (only `removal_requested_at` clears) -- but
  recorded under the `save_opportunity` command's OWN idempotency receipt
  (its canonical input), with a replay routed through the established
  `_replay_save` path, and emits the same audit event class (`save_remove_undone`)
  `undo_remove` uses for this transition. Post-terminal behavior (a Save
  against an already-`saved` or already-`removed` row) is unchanged. New
  tests:
  `test_save_during_undo_window_performs_undo_and_survives_window_elapse`,
  `test_save_during_undo_window_receipt_replays_correctly`,
  `test_cross_member_save_against_removing_row_is_untouched_not_found_isolation`,
  `test_save_during_window_then_explicit_undo_remove_is_refused_sanely_no_duplicate`.
- **IMPORTANT 2 — replay staleness on `undo_remove` and
  `mark_change_reviewed`, plus a false README claim.** Both commands
  still echoed the frozen receipt object on replay (`_expect(replay,
  SavedOpportunity)`) rather than re-rendering live state, and "Known
  limitations" item 11 falsely asserted this was fine because "their
  replay paths already return...current truth in the states those
  commands reach." The reviewer's exact scenario disproved it: undo,
  re-remove, let the window elapse, then replay the ORIGINAL undo key --
  the old code returned the frozen `saved` snapshot for a row that had
  actually finalized to `removed`. Both commands now route their replay
  through `_replay_save`, exactly like `save_opportunity`/`remove_saved`
  (see "Known limitations" item 11, rewritten to state the now-true
  situation: all four state-returning commands re-render live state on
  replay). New tests:
  `test_undo_remove_replay_after_re_remove_and_window_elapse_returns_removed_not_saved`,
  `test_mark_change_reviewed_replay_after_later_removal_and_window_elapse_returns_removed`.
- **MINOR 3 — module docstring overclaimed the vocabulary-consistency
  proof.** The closed-vocabulary section header claimed the test suite
  asserts "byte-equality" between the Python vocabulary and the SQL
  CHECK constraints; what it actually does is confirm each closed literal
  appears as an `N'...'` substring in the forward migration's DDL text
  (literal-presence checking, not a full byte-equal reconstruction of
  each CHECK's value list). Softened the docstring to state this
  precisely and to name the disposable gate proof as the source of real
  catalog-shape verification.
- **MINOR 4 — `GoverningBasis` accepted internally inconsistent input.**
  Per doc 03 §9.3, `listing_state="current"` or `"changed"` both describe
  an existing, tracked governing head, so pairing either with
  `governing_source_version_key=None` is not a legitimate absence -- it
  is a C2 composition bug that would otherwise silently reach
  `derive_lifecycle_overlays` and produce a wrong overlay rather than a
  loud error. `GoverningBasis.__post_init__` now refuses this pairing
  with a clear `ValueError`. No existing fixture constructed an
  inconsistent basis (all test/harness `GoverningBasis` construction
  already paired a non-None key with `current`/`changed`), so none needed
  updating; new test:
  `test_governing_basis_refuses_current_or_changed_with_no_governing_key`.
- **MINOR 5 + OBSERVATION 6 — two structural limits recorded, not fixed
  (see "Known limitations" items 12-13):** (a) the guard triggers' DELETE
  block does not stop `TRUNCATE`/`DROP` (SQL Server never fires `AFTER
  DELETE` for `TRUNCATE`, and `DROP TABLE` removes the trigger with the
  table) -- matches the C4/C5 precedent, and the future erasure package
  must not treat the trigger as full coverage; (b) the doc 09 §4
  unknown-outcome lockout is per-process in-memory state on the service
  instance -- a multi-worker deployment needs a shared-store lockout,
  which is a C8/C9 composition-era obligation, not something this
  package's P-1 reference or SQL schema currently assumes or provides.

## Conservative resolutions (genuine ambiguities in the blueprint, resolved toward withholding)

None required an owner decision (blueprint §11: none needed); these are
narrow implementation-level fills where the blueprint's closed vocabulary or
literal step ordering left a gap, resolved toward the more conservative
(withhold/refuse) reading and recorded here for review:

1. **`save_key`/`link_key` bounds have no dedicated failure code.**
   The blueprint's §2 failure-code table is explicitly closed and has no
   `save_key_required`/`save_key_too_long`/`link_key_required`/
   `link_key_too_long` entries, even though `MAX_SAVE_KEY_UTF16_UNITS`/
   `MAX_LINK_KEY_UTF16_UNITS` are defined in the same section's bounds
   table. `_owner_key_or_not_found` (`relationships_service.py:126`)
   type/emptiness/length-guards these opaque keys and refuses `not_found`
   on any failure rather than inventing a new code — this also keeps a
   malformed key indistinguishable from a genuinely absent one (Group F's
   binding requirement). Every key this service issues is a 32-character
   `uuid4().hex`, well inside the bound, so this only ever catches
   malformed caller input, never a real key.
2. **`search_text`'s non-string case has no dedicated failure code either.**
   `list_saved` (`relationships_service.py:1205`) refuses a non-string
   `search_text` under the nearest closed code, `search_text_too_long`,
   rather than silently coercing it or inventing `search_text_invalid`.
3. **Idempotency-replay-first ordering.** Blueprint §5.2's numbered
   per-command descriptions list "resolve basis (not_found check)" before
   "idempotency `_begin`" in their prose, but every actual C3/C4/C5
   precedent method (e.g. `qualification_service.create_grant`) checks
   `_begin` FIRST, before any business-logic validation that touches
   injected readers — because a successful replay must short-circuit
   without re-validating against possibly-changed external state (§5.5's
   "byte-identical, no re-execution" rule). This implementation follows
   the precedent code shape, not the prose's literal step order: bounds
   validation is pure and happens first, then (inside the lock)
   `_check_not_locked` → `_begin`/replay-check → business logic (basis
   resolution, active-row check) → write. A refused call never records a
   receipt, so a genuinely fresh or genuinely-still-failing call always
   re-validates; only a call that previously *completed* short-circuits.
   (Self-review MINOR 8 refines what "short-circuits" returns for
   `save_opportunity`/`remove_saved` specifically — see "Known
   limitations" item 11: the receipt proves identity, but the snapshot
   returned on replay is re-read live, not echoed frozen.)
4. **`get_saved` on a `removed` row refuses `not_found`, not a rendered
   entry.** `list_saved` explicitly excludes `removed` rows (§5.4 point 2 —
   terminal history); `get_saved` follows the same exclusion for symmetry,
   rather than rendering a removed row's entry (the blueprint's per-command
   breakdown does not specify `get_saved`'s own behavior, only `list_saved`'s
   filtering rule). A member inspects removed-save history only through a
   mutating command's `current_state` refusal payload, never through a
   direct read. This also keeps `get_saved`'s cross-owner and
   removed-row-as-absent refusals byte-identical to a truly absent key.
5. **`finalize_elapsed_removals` needed a repository primitive the
   blueprint's own §4 Protocol snippet does not list.**
   `saves_with_elapsed_removals(*, now, undo_window, limit)` was added to
   both the Protocol and the in-memory repository — the same category of
   structural fill-in C4's README records as its own item 9 (a seam the
   code cannot function without, not a policy choice), mirroring
   `RetrievalRepository.purge_abandoned_executions`.
6. **Lazy finalization is best-effort against the repository, never
   raised to the caller.** If the repository write inside
   `_finalize_if_elapsed` itself fails, the service does not raise
   `save_outcome_unknown` — it uses the locally computed, correctly-timed
   `removed` state for the rest of that call's logic regardless (§12 item
   5: "truth is derived, storage catches up"). This was a deliberate
   choice to keep member-facing reads (including the very state-reload a
   locked-out member needs) robust against a system-level bookkeeping
   write hiccup that carries no member consequence of its own.
7. **Lazy-finalization audit events always use `actor="system:finalize_sweep"`**,
   whether triggered by the explicit bounded sweep or inline as a
   byproduct of any other service method's lazy-first load — the
   `RelationshipsAuditEvent.actor` vocabulary in the blueprint's own
   docstring is `"member" | "system:finalize_sweep"` and finalization is
   never member-initiated, so there is no third value to reach for.

## Known limitations and forward obligations

Recorded truthfully; none blocks this repository merge, and none may be
silently forgotten.

1. **Member-data erasure path — same gap as C5, stated, not repeated
   silently.** Both `PS-MYOPP-005` tables are delete-blocked by their guard
   triggers (THROW 55784/55790) with no erasure carve-out, while doc 08 §5
   requires member-side deletion on account deletion. This is the SAME
   recorded limitation as the C4/C5 tables and is expected to be closed by
   the same future governed erasure package before these tables hold real
   member data. C6 deliberately does not invent deletion authority.
2. **`slate_workspace_ref` is an opaque reference with no cross-domain FK**
   (blueprint §7.2): the concrete Slate target is REC-01-gated and
   selected/verified at C7 activation, so a hard FK into a specific Slate
   table would pre-commit that decision inside C6's migration. Slate-boundary
   referential truthfulness is C7's service-layer obligation.
3. **The verifier attests catalog shape, not behavior** (`verified = 1` =
   shape); behavioral proof is the P-1 suite (C4/C5 precedent, restated).
4. **Export inclusion** (doc 08 §5: saves and links in account export) is the
   settings-export family's future obligation once these tables carry real
   data; C6 provides the owner-scoped read surface (`list_saved`,
   `list_slate_links`) it will need.
5. **Lazy finalization means a `removing` row past its window may persist in
   storage until the next read/sweep**; every service read renders it as
   `removed` regardless (truth is derived, storage catches up). The
   content-blind `finalize_elapsed_removals` sweep is available for
   hygiene; C9 may schedule it.
6. **Overlay derivation reads the governing basis through an injected
   reader**; composition against the real C2-backed reader (and C5-backed
   verification reader) is wiring done by the future runtime-composition
   package (C8/C9 era), mirroring how C4's workers are composed.
7. **`DEFAULT_UNDO_WINDOW = 30s`** is a C6-owned, service-configurable
   implementation default, not an owner decision (blueprint §11 item 1):
   the docs fix the undo-window mechanism, not a duration, and no document
   names one. Changing `RelationshipsLimits.undo_window` is a limits
   change, never a migration (the schema stores timestamps, never the
   window itself). C8 may surface a different value at UI time without
   touching C6.
8. **The conservative mapping of every non-current/non-changed/non-closed
   listing state into `could_not_reverify`** (blueprint §5.3 rule 4;
   `unreachable`/`stale`/`quarantined`/`invalid`/`intake` all collapse to
   the same overlay) is the closed 3-overlay vocabulary's only truthful
   reading, recorded here for review per blueprint §11 item 2.
9. **RESOLVED (self-review IMPORTANT 5):** the original phase-1 pass of
   this package hit a pre-existing C4 regression-suite failure
   (`RetrievalMigrationTests.test_registry_entry_shape_and_requires`
   asserting `migrations[-1] is entry`) as an unavoidable side effect of
   appending to the shared registry. The claim was subsequently extended
   to include `tests/test_my_opportunities_retrieval.py`, which let this
   session fix the fragility at its root rather than merely document it:
   both that test and this package's own equivalent
   (`test_only_one_writer_claims_registry_json_entry_last_in_array`, now
   `test_every_migrations_requires_appear_earlier_in_the_array`) were
   rewritten to assert the durable, order-relative invariant registry.json
   actually needs ("every migration's `requires` entries appear earlier in
   the array than the migration itself") instead of "this entry is
   literally last" — which cannot survive any subsequent package's append.
   This closes the fragility class for every future package, not only C6.
10. **Doc 09 §2 optimistic concurrency is NOT implemented.** No member-facing
    mutation here takes a read token or version precondition; the SQL
    `row_version rowversion NOT NULL` columns on both tables exist (for a
    future consumer) but are never read or compared by this service. Two
    browser tabs (or two racing requests) calling `mark_change_reviewed` (or
    any other mutation) on the same row therefore resolve last-write-wins,
    not first-conflict-detected -- the doc 09 §2 contract the docs describe
    is a real gap, not a mechanical consequence already covered by the §3-4
    idempotency/unknown-outcome machinery this package DOES implement (those
    are about safe retries of the SAME logical write, not about detecting a
    conflicting concurrent write). Threading an actual read-token/precondition
    parameter through every mutation is recorded here as a C8-composition-era
    obligation (the UI layer is what would supply and refresh the token) and
    is deliberately not implemented now, per explicit owner/reviewer
    adjudication during self-review rather than silently assumed satisfied.
11. **Idempotent replay re-renders live state for all four state-returning
    `SavedOpportunity` commands, rather than echoing the original frozen
    response byte-for-byte (self-review MINOR 8, extended to full coverage
    by self-review IMPORTANT 2 -- deliberate divergence).** The C3
    idempotency contract's "byte-identical, no re-execution" guarantee is
    about the record's *identity* (the receipt proves this exact command
    was already accepted and will never be re-executed or duplicated) --
    it does not require the *returned snapshot* to be stale.
    `save_opportunity`, `remove_saved`, `undo_remove`, and
    `mark_change_reviewed` ALL route their replay path through the shared
    `_replay_save` helper, which re-reads the live row (through the same
    lazy-finalization path every other read uses) before returning it. A
    member who fires the same request twice, where the second reply
    arrives after the row's state has since moved on (e.g. undo, then a
    later remove finalized to `removed`; or a reviewed row later removed
    and finalized), sees that current truth rather than a frozen snapshot
    with a stale undo/review affordance that no longer describes reality.
    (An earlier version of this item incorrectly claimed only
    `save_opportunity`/`remove_saved` had this behavior and that
    `undo_remove`/`mark_change_reviewed` "already return...current truth
    in the states those commands reach" -- that claim was false; both
    commands originally echoed the frozen receipt object, which the
    reviewer's exact scenario (undo, re-remove, let the window elapse,
    replay the original undo key) proved wrong by returning a stale
    `saved` snapshot for a row that was actually `removed`. Fixed;
    binding regression tests:
    `test_undo_remove_replay_after_re_remove_and_window_elapse_returns_removed_not_saved`,
    `test_mark_change_reviewed_replay_after_later_removal_and_window_elapse_returns_removed`.)
    `record_slate_link` and `mark_slate_unlinked` (the `SlateLink`
    commands) are unaffected by this note -- they are a separate record
    type with their own, unmodified replay path, not yet extended to
    re-render live state (a link's reachable post-receipt states in this
    package are narrower: `linked`/`unlinked` only, with no window/
    finalization sweep analogous to saves').
12. **The guard triggers' DELETE-block does not stop `TRUNCATE TABLE` or
    `DROP TABLE`.** SQL Server never fires an `AFTER DELETE` trigger for
    `TRUNCATE`, and `DROP TABLE` removes the trigger along with the table --
    neither operation is something an ordinary application code path would
    ever issue, but both are available to a sufficiently privileged
    connection. This matches the C4/C5 precedent exactly (the same
    structural limit applies to their own delete-block triggers); it is
    recorded here, not newly introduced by C6, and the future governed
    erasure package (see item 1 above) must not treat "the guard trigger
    blocks DELETE" as full coverage against every possible destructive
    statement -- ordinary privilege scoping (never granting application
    connections `ALTER`/`CONTROL` on these tables) is the actual backstop,
    outside this package's schema-level authority.
13. **The doc 09 §4 unknown-outcome lockout (`_unknown_outcomes`) is
    per-process in-memory state on the `RelationshipsService` instance.**
    A single-process deployment behaves exactly as documented: a failed
    write locks that `(user_key, idempotency_key)` pair until a
    successful owner read clears it. In a multi-worker deployment (more
    than one process/instance serving the same member concurrently,
    which this package does not itself provision or assume), a lock
    armed on one worker is invisible to the others -- a retry routed to a
    different worker would not see the lockout and could proceed to
    retry blindly rather than being told to reload first. Threading a
    shared-store lockout (e.g. keyed rows in the same repository, or a
    distributed cache) through this mechanism is a C8/C9 composition-era
    obligation once a multi-worker runtime is actually chosen; nothing in
    the P-1 in-memory reference or the SQL schema assumes single-process
    today, but nothing implements the shared-store version either.
