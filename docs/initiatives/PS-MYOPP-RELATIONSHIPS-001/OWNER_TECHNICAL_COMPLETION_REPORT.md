# PS-MYOPP-RELATIONSHIPS-001 — technical completion record

## Core record

- **Task/package and delivery path:** `PS-MYOPP-RELATIONSHIPS-001`, Protected.
- **Outcome and member/site effect:** The doc 03 §7 owner-scoped C6
  save/remove/undo machine (undo window, terminal `removed` rows, one
  active save per member and opportunity), the pure `derive_lifecycle_overlays`
  function and its REC-03 per-member `posting_changed` disposition, the
  owner-filtered saved view with local search/filter over read-time display
  resolution, the doc 03 §8 Slate-link record shape and persistence
  primitives (one active link per member and opportunity, unlinked history
  labels, no C7 command surface), the doc 09 §4 unknown-outcome write
  discipline (blind-retry lockout + state-reload unlock), and the additive
  `PS-MYOPP-005` SQL trio are implemented at P-1/P-2 in a single
  implementation pass. There is no route, UI, or current member-visible
  site effect.
- **Package manager:** Not separately identified as a distinct role in this
  task; the same session performed the blueprint-bound implementation work.
  Repository/schema/backend truth; ChatGPT Work is not needed for this
  non-visual service slice.
- **Writer:** `session:4b21c2ac-0236-4dc0-af54-2c15e6f126ce/myopp-relationships-writer`.
- **Branch and base:** `work/2026-08-31-myopp-relationships-001`. Phase 1
  (the original implementation candidate) started this worktree's `HEAD` at
  `a9fb5f613015c82d0fe9c2e83d17c9797665975a` ("Merge pull request 806 from
  work/2026-08-31-delivery-activation-myopp-relationships-001 into main") —
  the branch's activation control commit, itself descended from the
  `activated_from_main` checkpoint (`d9506c922f30df38d3c400abf35f93977453cc59`)
  recorded in the package's lane claim. Before this self-review pass, the
  worktree was synced with `git fetch origin && git merge origin/main`,
  fast-forwarding to `53ebf7f7` ("Merge pull request 807 from
  work/2026-08-31-delivery-extend-surfaces-myopp-relationships-001 into
  main") — a control-only extend-surfaces commit that added
  `tests/test_my_opportunities_retrieval.py` to this claim's surfaces (the
  only file it touched was the lane claim JSON itself; the merge was a
  clean fast-forward with no conflict against this session's uncommitted
  work). Implementation, the self-review fix pass, and the gate proof are
  committed and pushed (implementation `9a384404`, gate proof plus the two
  gate-caught fixes `ea610d9f`, registry line and this record in the freeze
  commits).
- **Candidate SHA:** the frozen candidate is the tip of
  `work/2026-08-31-myopp-relationships-001` at review routing; its exact
  40-character SHA is recorded in the review receipt and, at close, in the
  claim's `merged_sha` lineage.
- **Changed paths (across the implementation pass, the self-review pass,
  and the proof/freeze commits):**
  - `services/my_opportunities/relationships_service.py` (new)
  - `tests/test_my_opportunities_relationships.py` (new)
  - `SQL FIles/Migrations/PS-MYOPP-005_relationships.sql` (new)
  - `SQL FIles/Migrations/PS-MYOPP-005_relationships_rollback.sql` (new)
  - `SQL FIles/Verification/PS-MYOPP-005_relationships_verify.sql` (new)
  - `SQL FIles/Migrations/registry.json` (one entry appended, last in the
    array, now carrying the recorded gate proof; nothing else in the file touched — confirmed by
    a 13-line, insertion-only `git diff`)
  - `docs/initiatives/PS-MYOPP-RELATIONSHIPS-001/README.md` (new, this
    package's directory)
  - `docs/initiatives/PS-MYOPP-RELATIONSHIPS-001/OWNER_TECHNICAL_COMPLETION_REPORT.md`
    (new, this file)
  - `tests/test_my_opportunities_retrieval.py` (self-review pass only,
    after the claim was extended to include it: IMPORTANT 5's
    registry-fragility fix — one test's body rewritten, no other change
    to this file)

  No C2 (`canonical_service.py`), C3 (`criteria_service.py`,
  `interpretation_service.py`), C4's four *other* files
  (`retrieval_service.py`, `search_worker.py`, `index_projection.py`,
  `index_fence.py`), or C5 (`qualification_service.py`,
  `evidence_port.py`) file was touched.
  `services/my_opportunities/__init__.py` was not touched.
  `docs/governance/PACKAGE_REGISTRY.json` was not touched (its extension is
  a separate, later control transition per the blueprint).
- **Verification performed and result:** `python3 -m unittest
  tests.test_my_opportunities_relationships -v` runs **80 tests: 79 pass,
  and exactly one fails honestly and as designed** —
  `RelationshipsMigrationTests.test_c6_migration_registry_and_verifier_are_bounded_and_gate_proven`
  errors with `TypeError: 'NoneType' object is not subscriptable` at
  `gate["executable_sha256"]` (at that stage the registry entry's `"gate": null` had not
  been proven yet, so nothing downstream of that line in the test ran — the
  identical honest-failure shape C4's and C5's equivalent tests showed
  before their own gate proofs were recorded). Per-group tally: A Save
  machine 7/7 · B Remove/undo/window 9/9 · C Overlay derivation (pure) 9/9
  · C-integration Overlay service integration 7/7 · D Saved-view
  search/filter 10/10 · E Slate-link persistence 7/7 · F Cross-member
  negative proofs 5/5 · G Unknown-outcome discipline 8/8 · H
  Contract-freeze/vocabulary-closure 4/4 · I SQL/registry file-content
  13/14 (the one designed failure). This count and tally reflect a
  self-review pass (this same worktree/branch) that found and fixed
  defects across the SQL trio, service module, and test suite after the
  original phase-1 candidate — see the README's "Self-review corrections"
  for the full per-finding record (2 blocker, 5 important, 6 minor); the
  original phase-1 count was 73/72+1.

  Regression: `tests.test_my_opportunities_qualification` (79/79),
  `tests.test_my_opportunities_criteria` (15/15), and
  `tests.test_my_opportunities_canonical` (33/33) are all green and
  untouched. `tests.test_my_opportunities_retrieval` runs **104/104
  green** — the original phase-1 candidate had introduced one incidental
  failure here (`RetrievalMigrationTests.test_registry_entry_shape_and_requires`
  hard-coded `migrations[-1] is entry`, an assumption that cannot survive
  any subsequent package's registry append), which the self-review pass
  fixed at its root (self-review IMPORTANT 5) once the claim was extended
  to include this file: both that test and this package's own equivalent
  now assert the durable, order-relative "every `requires` id appears
  earlier in the array" invariant instead. See the README's "A
  regression-suite fragility this session found AND fixed" section for the
  full record.

  Both new migration SQL files were checked for internal consistency:
  both tables created in the forward migration
  (`myopp_saved_opportunities`, `myopp_slate_links`) are dropped in the
  rollback in dependency order (triggers before tables, links before
  saves) and named in the verifier; every constraint/FK/trigger/index name
  the verifier references was confirmed present, byte-equal, as a literal
  string in the forward migration's DDL text (MINOR 13 self-review
  correction: this is name-consistency plus Python-side text/byte-equality
  checking only -- it does NOT execute or parse either file against a real
  SQL Server catalog, so it cannot itself prove the verifier's T-SQL is
  syntactically valid or that its predicates evaluate as intended against
  live catalog views; that proof is exactly what the disposable-database
  gate run supplies; the proof has since been recorded (attempt a3) -- see the populated gate block
  below). THROW numbers 55780-55793 (forward, within
  the reserved 55780-55799 forward slice), 55800-55802 (rollback, within
  55800-55809), and 55810-55823 (verify, within 55810-55839) were confirmed
  unique within each file and to collide with no other tracked
  migration/verification file's THROW numbers repo-wide (the reserved
  55780-55839 block was independently confirmed empty against the current
  repo-wide census before use: the highest previously allocated number is
  55778, and the next allocated block begins at 56101). Every SQL DDL
  assumption in the blueprint was verified against the applied DDL before
  use: `myopp_canonical_opportunities`'s `UQ_myopp_canonical_opportunities_id_class
  (myopp_canonical_opportunity_id, data_class)`, `myopp_source_versions`'s
  `UQ_myopp_source_versions_id_class (myopp_source_version_id, data_class)`,
  and `app_users`'s `UQ_app_users_user_key (user_key)` all exist exactly as
  the blueprint's FK targets assume. Every enum literal in
  `relationships_service.py`'s closed vocabulary (save states, link states,
  `created_from` sources, data classes) was confirmed present as an
  `N'...'` literal in the forward migration's DDL — one vocabulary,
  byte-equal between Python and SQL. `__pycache__` was cleaned after the
  final test run; `git status` at the end of this session shows only the
  claimed new/modified files listed above.

  Final tallies at freeze: relationships 80/80, retrieval 104/104,
  qualification 79/79, criteria 15/15, canonical 33/33, package_registry
  2/2 — all green with the gate proof recorded and the PACKAGE_REGISTRY
  line added.

  **Round 2 (post-freeze, this session): independent review of the frozen
  candidate `c8a304f2` returned REVISE**, with six findings (1 blocking, 1
  important named "IMPORTANT 2" affecting correctness, 4 lower-severity:
  see the README's "Round 2 — independent review of frozen candidate
  `c8a304f2` (REVISE)" for the full per-finding record). All six are fixed
  as UNCOMMITTED working-tree changes on top of `c8a304f2`, per this
  round's explicit no-commit instruction. Verification: `python3 -m
  unittest tests.test_my_opportunities_relationships -v` now runs **87
  tests, all green** (7 new tests: 4 for BLOCKING 1, 2 for IMPORTANT 2, 1
  for MINOR 4). Per-group tally: A Save machine 11/11 · B Remove/undo/
  window 10/10 · C Overlay derivation (pure) 9/9 · C-integration Overlay
  service integration 8/8 · D Saved-view search/filter 10/10 · E
  Slate-link persistence 7/7 · F Cross-member negative proofs 5/5 · G
  Unknown-outcome discipline 8/8 · H Contract-freeze/vocabulary-closure
  5/5 · I SQL/registry file-content 14/14. Full acceptance run across all
  six suites (`relationships` + `retrieval` + `qualification` + `criteria`
  + `canonical` + `package_registry`): **320 tests, all green** (87 + 104
  + 79 + 15 + 33 + 2) — the "keep all 313 green" baseline plus this
  round's 7 new tests. `__pycache__` cleaned after the final run; `git
  status` at the end of this round shows exactly four modified files
  relative to `c8a304f2`, all uncommitted:
  `services/my_opportunities/relationships_service.py` (BLOCKING 1,
  IMPORTANT 2, MINOR 3, MINOR 4),
  `tests/test_my_opportunities_relationships.py` (7 new binding tests),
  `docs/initiatives/PS-MYOPP-RELATIONSHIPS-001/README.md` (Round 2
  self-review record, item 11 rewrite, new items 12-13), and this file
  — nothing else.
- **Release state:** repository-only — `c8a304f2` (and its ancestor commits
  implementing, gate-proving, and registering this package) is committed
  and pushed, but that exact candidate's independent review returned
  REVISE; the round-2 fixes above are UNCOMMITTED per this round's
  explicit instruction. No PR completion, no merge, no deployment, no
  schema apply, no enablement, and no live verification has happened. The
  next independent review outcome, PR, and merge SHA post-date this record
  and will be recorded in the review receipt and the runtime-inert claim
  evidence file, and in the closed claim.
- **Known limits / owner decision needed:** No owner decision is
  outstanding (blueprint `C6_ARCHITECTURE.md` §11: none required; every
  vocabulary, transition, and invariant is fixed by already-accepted
  architecture). Thirteen items are flagged in the README's "Known
  limitations and forward obligations" for Pete's post-live visibility,
  not held for pre-approval (2 added this round: item 12, TRUNCATE/DROP
  not blocked by the guard triggers; item 13, the per-process in-memory
  unknown-outcome lockout), plus seven "Conservative resolutions"
  documenting every genuine ambiguity this session resolved toward
  withholding/refusing rather than disclosing/claiming, each with its
  file:line citation.
  Procedural items remain: committing the working tree, the complete-diff
  self-review, reconciling the branch against the current fetched Azure
  `origin/main` tip and rerunning collision checks, the disposable
  migration-gate proof for `PS-MYOPP-005` under the recorded C4-through-C9
  owner envelope, and the required independent exact-SHA review (Protected
  delivery path).
- **Next action (superseded by Round 2 below for the current state; kept
  for provenance of how `c8a304f2` was reached):** ~~Commit this session's
  new/modified files...~~ — this happened: implementation, gate proof,
  and PACKAGE_REGISTRY registration were committed, pushed, and frozen as
  `c8a304f2`, which was routed for independent review.
  **Round 2 next action:** the four round-2 uncommitted files (see the
  "Round 2" verification paragraph above) still need to be committed on
  `work/2026-08-31-myopp-relationships-001` (this round's instruction was
  explicitly no-commit, so that step is deliberately NOT done in this
  session); after confirming the branch is still reconciled against the
  current fetched Azure `origin/main` checkpoint and rerunning collision
  checks per `START_HERE.md`, push, complete this record's new candidate
  SHA, and route that exact SHA back for independent re-review. Do not
  open/complete a PR before that re-review pass returns non-REVISE.

## Protected additions

- **Privacy and authorization:** Every `RelationshipsService` member-facing
  method is owner-scoped (`_require_user_key` first, `_owner_key_or_not_found`
  guarding every opaque save/link key lookup); cross-owner and truly-absent
  keys return the identical `not_found` shape, field-for-field, across every
  mutating and read method (test group F, `test_direct_key_access_cross_owner_and_absent_are_not_found`
  and `test_cross_owner_and_absent_probes_execute_same_code_path_no_early_exit_oracle`).
  `VerificationReader.latest_gate_outcome` takes `user_key` first (owner-bound;
  a cross-member call cannot be expressed by construction). A repository API
  census (test group F) confirms every read method on the
  `RelationshipsRepository` Protocol takes `user_key` first and filters IN
  the query, with the one deliberate exception of the content-blind,
  system-only `saves_with_elapsed_removals` sweep primitive (never exposed
  to a member, key+age only).
- **AI / consequential automation:** None. This package makes no provider
  call, has no AI proposal seam, and injects no evidence port — it is
  route-free and provider-neutral by design (mirroring C3/C4/C5's own
  posture for their persistence layers). `derive_lifecycle_overlays` is a
  pure function over canonical/member-review truth only.
- **Migration and rollback:** `PS-MYOPP-005` is additive, depends on
  `PS-MYOPP-001` through `PS-MYOPP-004` (family serial convention), and has
  a data/later-ledger-refusing rollback (drops triggers before tables, and
  `myopp_slate_links` before `myopp_saved_opportunities`) and an exact
  verifier (owner fencing, closed save/link/created_from/data_class
  vocabularies, state/timestamp pairing CHECKs, both filtered unique
  indexes with `has_filter = 1` and their filter predicate compared via a
  normalized (lowercase, bracket/paren/whitespace-stripped) match rather
  than raw byte equality (self-review IMPORTANT 4, the PS-MYOPP-001
  idiom — SQL Server's own pretty-printing of a filtered-index predicate
  is not guaranteed byte-stable), both guard triggers present and enabled,
  an owner-safe, schema-qualified FK census (self-review MINOR 13) that
  also scans for any FK reaching outside the `{app_users,
  myopp_canonical_opportunities, myopp_source_versions}` allowlist, a
  forbidden copied-content/overlay/scoring column scan, and the
  id/user/data_class composite-uniqueness census). THROW numbers were
  confirmed unused against every other tracked
  migration before use (see "Verification performed and result" above).
  The disposable-database gate proof is DONE (attempt a3 of Pete's recorded
  C4-C9 envelope; a1 caught an over-length ledger description and a2 caught
  the verifier's missing n-prefix — both real defects fixed before success;
  all three throwaway databases deleted with ResourceNotFound confirmed,
  temporary firewall rule removed). Provenance: before the proof ran, this
  paragraph recorded the gate as not yet done with `"gate": null` in
  `SQL FIles/Migrations/registry.json`, to be completed under the recorded
  standing C4-through-C9 owner envelope before merge — which is exactly
  what then happened.
- **Status:** **Conditional, REVISE cycle in progress** — implementation,
  gate proof (attempt a3, DONE), and PACKAGE_REGISTRY activation are
  committed and frozen as `c8a304f2`; that exact candidate's independent
  review returned REVISE (six findings, all fixed in this session — see
  "Round 2" above and the README). The round-2 fixes are complete and
  fully green (320/320 across all six suites) but deliberately
  UNCOMMITTED per this round's explicit instruction. Committing the
  round-2 fixes, freezing a new candidate SHA, and routing it back for
  independent re-review are all still required before repository merge.
