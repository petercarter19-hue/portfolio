# CR4 owner technical completion report

## Core record

- **Task/package and delivery path:**
  `PS-SETTINGS-ACCOUNT-EXPORT-OPPSLATE-READER-001`, Protected, replacement
  package 4 -- the FINAL content reader of the accepted 2026-08-29 reader
  topology -- after `PS-SETTINGS-ACCOUNT-EXPORT-CORE-READERS-001`
  (replacement package 1, main `cc5174da`),
  `PS-SETTINGS-ACCOUNT-EXPORT-CAPTURE-MOMENT-READERS-001` (replacement
  package 2, main `1f701263`), and
  `PS-SETTINGS-ACCOUNT-EXPORT-WORKSHOP-READER-001` (replacement package 3,
  main `7d6b0ea1`) were all independently reviewed and merged.
- **Outcome and candidate scope:** Read-only, owner-scoped account-export
  readers for the member's own **durable** Opportunity Slate records --
  `dbo.opportunity_slates`, `dbo.opportunity_saved_results`,
  `dbo.opportunity_saved_qualifications`, `dbo.opportunity_saved_evidence`
  -- as four `usp_ReadAccountExport<Table>ForOwner` procedures in one
  additive migration (`PS-SETTINGS-EXPORT-006`); a data-safe rollback; a
  registry entry (authored with `gate: null`; no gate has been run by this
  writer -- see "Gate state" below) (`requires: ["PS-AUTH-001",
  "PS-OPPSLATE-001", "PS-OPPSLATE-002", "PS-OPPSLATE-003"]` -- the full
  direct ancestor chain, matching the in-family precedent
  `PS-OPPSLATE-003`/`PS-OPPSLATE-004` themselves already set); an
  isolation-verification script whose fixtures satisfy every `NOT
  NULL`/`CHECK`/`FOREIGN KEY` constraint on all four touched tables and
  populate every directive-excluded column with a real, genuinely-excluded
  value; updates to the shared
  `services/account_export_domain_readers.py` adapter (four new reader
  functions, `opportunity_slate` flipped from `excluded` to `included`,
  `my_opportunities` re-verified and left `unavailable`); and offline
  tests pinning every field allowlist, every forbidden-field exclusion
  (including a directive-category cross-check), the owner predicate on
  every table of a four-level join chain, and every structural safety
  property. No table, trigger, index, container, worker wiring, route, or
  UI is added or changed. No schema apply, database connection, or Azure
  call was made by this writer.

  **The central finding of this package**, recorded in full in
  `CR4_ACCOUNT_EXPORT_OPPSLATE_READER.md`: of the fifteen tables created
  across `PS-OPPSLATE-001`/`002`/`004`, none is durable. All fifteen are
  ephemeral working-session state, cascade-deleted by the same
  `usp_PurgeExpiredOpportunityWorkingData`/
  `usp_DeleteOpportunityWorkingSessionForOwner` calls -- including the two
  tables (`opportunity_requirement_review_events`,
  `opportunity_member_takes`) the writer brief's own "expect" framing
  named as `PS-OPPSLATE-004`'s durable member tables. Only
  `PS-OPPSLATE-003`'s four OS-4 tables are durable, and only those four
  are read here. This directly overturned the brief's own naming at write
  time; see "Design decisions" item 1 below for the full proof trail.

- **Package manager and writer:** Sole writer
  `agent:claude-code/settings-os-reader-writer`, working only in the
  durable worktree
  `C:\Users\peter\Documents\PeerSlateWorktrees\PS-SETTINGS-ACCOUNT-EXPORT-OPPSLATE-READER-001`
  on branch `work/2026-08-29-settings-account-export-oppslate-reader-001`.
  The lane claim's `surfaces` list names eleven paths; three of them (the
  claim JSON itself, its evidence file, and its receipts file) are
  reserved for the manager's gate/review stage, matching every prior
  package's identical exclusion -- this writer created or modified the
  other eight, confirmed by `git status --short` before staging (six new
  files, two modified: `SQL FIles/Migrations/registry.json` and
  `services/account_export_domain_readers.py`). No file outside the
  claim's eleven surfaces was touched.
- **Base SHA and branch:** Activated from `origin/main` `5d433cc3` per the
  lane claim (`activated_from_main`); worktree `HEAD` confirmed at exactly
  `c2b03489f6b399123fff416ff9a2bba9a482f4f4` (`git rev-parse HEAD`) before
  any write, one commit ahead of the claim's activation SHA on `main`
  (`c2b03489` is PR 720, the delivery-activation merge for this exact
  package) -- the identical "base main, or the one delivery-activation
  commit after it" pattern every prior package in this program recorded.
  No other commit had landed on this branch before this candidate.
- **Final SHA:** This report is authored, per the writer brief, **before**
  the final commit(s) exist on
  `work/2026-08-29-settings-account-export-oppslate-reader-001` -- it
  cannot record a final SHA it has not yet produced. The exact value is
  in the writer's chat-turn final message and in `git log` on the pushed
  branch, not in this file.
- **Candidate changed paths** (six new, two modified; nothing else in the
  worktree was touched -- confirmed by `git status --short` before
  staging):
  - `SQL FIles/Migrations/PS-SETTINGS-EXPORT-006_oppslate_reader.sql` (new, 614 lines)
  - `SQL FIles/Migrations/PS-SETTINGS-EXPORT-006_oppslate_reader_rollback.sql` (new, 44 lines)
  - `SQL FIles/Migrations/registry.json` (modified -- one entry appended, +13 lines)
  - `SQL FIles/Verification/PS-SETTINGS-EXPORT-006_oppslate_reader_isolation_verify.sql` (new, 753 lines)
  - `services/account_export_domain_readers.py` (modified -- +112/-4 lines; see "Design decisions" below)
  - `tests/test_settings_export_oppslate_reader.py` (new, 1020 lines)
  - `docs/initiatives/PS-SETTINGS-MY-DATA-SHELL-001/CR4_ACCOUNT_EXPORT_OPPSLATE_READER.md` (new, 514 lines)
  - `docs/initiatives/PS-SETTINGS-MY-DATA-SHELL-001/CR4_OWNER_TECHNICAL_COMPLETION_REPORT.md` (this file, new)
- **Excluded actions and paths:**
  `docs/governance/lane_claims/PS-SETTINGS-ACCOUNT-EXPORT-OPPSLATE-READER-001.json`,
  its `evidence/*.md`, and its `receipts/*.json` were not created or
  modified -- all three are reserved for the manager's gate/review stage.
  `tests/test_settings_export_core_readers.py`,
  `tests/test_settings_export_capture_moment_readers.py`, and
  `tests/test_settings_export_workshop_reader.py` were run, all three
  green **unmodified** -- see "Validation and self-review" below; no
  narrow scope correction was needed in any sibling test file. No route,
  template, worker wiring, scheduler, container, workload identity,
  grant, `.env.example` entry, dependency, or production operation
  changed. No database connection, Azure call, or network call of any
  kind was made by this writer or by any test in this candidate. `git
  fetch` was never run, per the writer brief.

## Design decisions worth the reviewer's attention

Full field-by-field reasoning lives in
`CR4_ACCOUNT_EXPORT_OPPSLATE_READER.md`; this section lists only the
decisions with the widest blast radius.

1. **The writer brief's own "expect" framing for `PS-OPPSLATE-004`'s
   three new tables was overturned by reading the schema, not trusted.**
   The brief named `opportunity_source_identities`,
   `opportunity_requirement_review_events`, and `opportunity_member_takes`
   as "the 004 replacement's durable member tables," while also
   explicitly instructing that each table be judged against the real
   schema. Reading `PS-OPPSLATE-004_opportunity_slate_replacement.sql` in
   full shows all three are cascade-deleted by that same migration's own
   takeover of `usp_PurgeExpiredOpportunityWorkingData` -- the literal
   `DELETE ... FROM ... JOIN ... JOIN @ExpiredSessions ...` statements
   against all three tables, at the same purge call every OS-1/OS-2 table
   already goes through, with the migration's own comments naming the
   reason ("`opportunity_member_takes` and
   `opportunity_requirement_review_events` both hang off
   `opportunity_requirement_statements`, so both have to go before it
   does"; "`opportunity_source_identities` hangs off
   `opportunity_source_versions`, so it has to go before the version
   delete below"). Two of the three
   (`opportunity_requirement_review_events`, `opportunity_member_takes`)
   are additionally **shape only** -- no procedure has ever been created
   to write to either, per that migration's own header, so no row can
   exist in either table under any real database today. This is the one
   decision in this package most likely to draw independent-review
   scrutiny, precisely because it contradicts a sentence in the writer's
   own brief rather than merely filling a gap the brief left open. It is
   pinned by a dedicated test
   (`test_no_reader_references_any_ephemeral_working_session_table`) that
   asserts the negative space explicitly across all fifteen excluded
   table names, not merely that four readers happen to exist.
2. **`requires` names the full `PS-OPPSLATE-001/002/003` chain, not
   merely `PS-OPPSLATE-003`.** None of the four tables this package reads
   carries a foreign key into any OS-1/OS-2 table (confirmed by reading
   `PS-OPPSLATE-003`'s own DDL: every FK on the four durable tables
   targets only `dbo.member_profiles`, `dbo.app_users`, or another one of
   the same four tables), so checking only `PS-OPPSLATE-003`'s ledger row
   would have been technically sufficient. The full chain is required and
   guarded anyway, following the in-family precedent `PS-OPPSLATE-003`
   and `PS-OPPSLATE-004` themselves already set: each checks/requires its
   own complete ancestor chain by ledger row explicitly, never relying on
   transitivity alone. The identical class of conservative, disclosed
   choice `PS-SETTINGS-EXPORT-005`'s own header recorded for including
   `PS-WORKSHOP-002` in its own `requires`.
3. **`opportunity_saved_qualifications` and `opportunity_saved_evidence`
   have no opaque key column of their own**, matching
   `dbo.knowledge_item_versions`' precedent from package 3. Their exported
   identifying tuples -- `(saved_result_key, ordinal)` and
   `(saved_result_key, saved_qualification_ordinal, ordinal)` -- are
   derived from their own `UNIQUE` constraints
   (`UQ_opportunity_saved_qualifications_ordinal`,
   `UQ_opportunity_saved_evidence_ordinal`). No surrogate key is
   manufactured for a column the schema does not have.
4. **Every reader asserts the owner predicate on every table it joins,
   not merely the leaf** -- a four-level extension of the "owner
   predicate on both sides" defense in depth `PS-SETTINGS-EXPORT-004`/`005`
   introduced, made necessary because all four tables independently carry
   their own `owner_profile_id` (confirmed by DDL, not assumed). The
   `opportunity_saved_evidence` reader accordingly carries **four**
   `owner_profile_id = @ProfileId` predicates and **three** `JOIN`s beyond
   the identity header's own -- the deepest chain any reader in this
   program has needed.
5. **Two counts were deliberately kept despite sitting next to AI
   output**: `opportunity_saved_results.evidence_considered_count` and
   `opportunity_saved_qualifications.citation_count` (paired with
   `derived_status`). Both are plain counts, not names/ids/prompts/
   scores/confidence values, and the schema's own comments frame both as
   member-input/application-computed facts, never a model opinion. Full
   reasoning in `CR4_ACCOUNT_EXPORT_OPPSLATE_READER.md`'s
   "C0-versus-directive supersession" section; recorded here because
   excluding either would have been the more conservative-looking but
   less textually-supported choice.
6. **`idempotency_key` is excluded by extending a program precedent, not
   by any of the four directive categories.** `opportunity_saved_results`
   is otherwise a fully legitimate content table; only this one column is
   dropped, on the strength of the migration's own header calling it "the
   idempotency ledger" -- the same word this program already uses for the
   whole-table exclusions of `knowledge_item_save_requests`/
   `recruiter_question_save_requests`/`moment_save_requests`. Disclosed
   explicitly as a judgment call, not a directive requirement, so a
   reviewer can evaluate it independently.
7. **`opportunity_saved_evidence`'s reader is built despite losing nearly
   all of its column payload** to `THIRD_PARTY_POSTING_TEXT` and
   `EVIDENCE_LINKS` (only `ordinal`/`clause_ordinal` survive). Built per
   the writer brief's explicit instruction for a half-excluded table
   rather than reclassifying the domain as excluded; recorded as an
   honest limitation in "Limitations" below, not hidden.
8. **`my_opportunities` was re-verified, not left untouched by
   assumption.** `PS-MYOPP-001` (the only applied My Opportunities
   migration) was read directly; its own registry summary confirms "No
   member-side objects," so the existing exclusion reason remains
   factual. The `DOMAINS` reason string is lightly extended to record
   this recheck, not changed in disposition or substance.

## Validation and self-review

- **Verbatim final run** (checked by exit code directly, output
  redirected to a file rather than piped, never through a second command
  that would report ITS OWN exit code instead):
  ```
  ANTHROPIC_API_KEY=placeholder "C:\Users\peter\Documents\portfolio\venv\Scripts\python.exe" -m pytest -q tests/test_settings_export_oppslate_reader.py tests/test_settings_export_core_readers.py tests/test_settings_export_capture_moment_readers.py tests/test_settings_export_workshop_reader.py tests/test_settings_account_export_migration.py tests/test_account_export_assembly.py tests/test_account_export_storage.py
  ............... [  5%]
  ............................................................... [ 27%]
  .................................................................................. [ 55%]
  ............................... [ 66%]
  ....................................... [ 79%]
  ................................................ [ 96%]
  ..........                                                           [100%]
  288 passed, 2102 subtests passed in 90.71s (0:01:30)
  PYTEST_EXIT_CODE_IS=0
  ```
  (Figures are from the independent-review correction round's rerun of the
  identical command; the pre-correction candidate's run was `288 passed,
  2101 subtests` — the delta is the one new `saved_analysis_key` subtest
  in the fixture-population check.)
  - `tests/test_settings_export_oppslate_reader.py` (this package's own
    file, 55 tests / 530 subtests): migration/rollback/verify file shape
    (single guarded batch, balanced parens/comments, no `\nGO`);
    THROW-number uniqueness within the forward and rollback files
    (58600-58699) and the verify file's own numbers confirmed inside its
    reserved 58700-58799 block (uniqueness NOT asserted there, matching
    every prior package's own verify-file test, since section 0's
    structural loop deliberately reuses a handful of numbers once per
    procedure iteration), plus a repository-wide scan confirming no
    sibling `.sql` file anywhere under `SQL FIles/` reuses either range
    (highest prior use anywhere was 58553 before this package); exactly
    the four claimed procedures created and no table/trigger/index; never
    redefines another migration's procedure; the forward file's guards
    check exactly `PS-OPPSLATE-001`/`002`/`003` and never `PS-AUTH-001`/
    `PS-OPPSLATE-004`/any `PS-WORKSHOP-*`/any sibling
    `PS-SETTINGS-EXPORT-*`; **no reader body references any of the
    fifteen ephemeral table names**, asserted individually per table per
    procedure (60 assertions); every signature is exactly `@UserKey
    nvarchar(300)`; every procedure shares the byte-identical
    identity-resolution header; every procedure filters by every owner
    predicate its own chain depth needs (1/2/3/4 respectively) and
    asserts the joined `opportunity_slates.visibility = 'private'`
    predicate; join counts match chain depth exactly (1/2/3/4), and every
    descendant reader joins every ancestor by its exact aliased name;
    deterministic `ORDER BY` present with parent-then-sequence grouping
    checked precisely at every level via position comparison; no `SELECT
    *`; no reader references a soft-delete column of any kind (none of
    the four tables has one); every procedure returns the two
    read-window trailing columns with exactly two `SELECT` keywords; no
    procedure contains any transaction control, write, or nested `EXEC`;
    no procedure accepts a caller-selected owner/target parameter; no
    `GRANT`/role/user creation; forbidden fields (full-name sets) absent
    from every reader's actual output columns; **every directive-category
    column is both a documented subset of the forbidden-field sets AND
    independently confirmed absent from every reader's actual output**
    (two separate tests, matching the "belt and suspenders" design);
    `DOMAINS`' field-allowlist tuples equal the actual SQL output column
    list exactly, in order, for all four (as a subset check against the
    shared dict); the ledger description measured at 441 of 450 budgeted
    characters; the rollback drops exactly the four procedures and
    removes only this migration's ledger row; the registry entry pins
    `requires` exactly and, at authoring time, asserted `gate is None`
    with an explicit, pre-scripted lockstep docstring naming all five
    steps the manager's gate commit must take (that placeholder has since
    been replaced by `test_registry_entry_pins_the_sealed_gate`, executed
    in the gate commit exactly as scripted -- see "Gate state" below),
    plus the "registry + test + report" lockstep-set note every package
    since package 2's own gate round has carried forward; the verify
    script provisions three synthetic owners
    including one deactivated, never commits, always reaches `ROLLBACK
    TRANSACTION;` before its report `SELECT`, invokes all four procedures
    via both a genuinely bare `EXEC` and an `INSERT ... EXEC`, and its
    fixture is confirmed (by a dedicated test) to actually write a real
    value into every one of the sixteen directive-excluded columns, so the
    exclusion proof is genuine rather than vacuous; adapter offline tests
    using fake cursors/connections confirm all four new domain functions
    are independently callable, decode parent-linkage keys correctly at
    every chain depth, return empty rows (never an error) for an
    unresolved identity, never call `commit`/`rollback`/`close` on the
    caller's connection, and bind `@UserKey` as a driver parameter; and
    the `DOMAINS` registry has exactly one new included domain
    (`opportunity_slate`, scoped comparison) with exactly four readers in
    source order, `my_opportunities` confirmed still `unavailable` with a
    reason naming both "Opportunity Slate" and "PS-MYOPP-001", and no
    reason string leaks a forbidden field name.
  - `tests/test_settings_export_core_readers.py` (package 1, 42 tests),
    `tests/test_settings_export_capture_moment_readers.py` (package 2, 52
    tests), and `tests/test_settings_export_workshop_reader.py` (package
    3, 48 tests): **all three run and green unmodified.** Read in full
    before this package touched `services/account_export_domain_
    readers.py`, to confirm which assertions were already properly
    scoped to their own package's domains/procedures versus which walked
    the whole `DOMAINS` dict unconditionally (a genuine cross-package
    invariant, e.g. `test_included_domains_have_no_reason_others_have_a_
    stable_reason`). This package's own additions satisfy every such
    invariant without modification to any sibling file.
  - `tests/test_settings_account_export_migration.py`,
    `tests/test_account_export_assembly.py`,
    `tests/test_account_export_storage.py`: unchanged, still green --
    confirms this candidate did not disturb the accepted C1/C2 migration,
    assembly, or storage code.
- **Also run via `python -m unittest`** (the actual CI mechanism, not just
  pytest), output redirected to a file and its exit code read directly
  (never through a pipe): `Ran 288 tests ... OK`, exit code `0` -- confirms
  the suite is green under both runners.
- **A full collect-only pass of the entire repository test suite**
  (`pytest --collect-only -q tests/`): 4,539 tests collected, exit code 0,
  no collection error -- confirms these new/changed files do not break
  import/discovery anywhere else in the repository.
- **`scripts/migration_registry.load_registry()`** (the registry's own
  offline, no-connection validator), invoked directly in Python: loads
  all 41 entries without error, `PS-SETTINGS-EXPORT-006`'s `requires`
  resolve to `('PS-AUTH-001', 'PS-OPPSLATE-001', 'PS-OPPSLATE-002',
  'PS-OPPSLATE-003')`, `gate` was `None` at authoring time (the standing
  sealed digest `3db5eff2…` from gate run 2 is now pinned in "Gate state"
  below and in the replaced registry test; run 1's `f283c79f…` sealed the
  pre-correction file), both the forward and rollback files resolve
  and exist, and `executable_sha256(forward)` computes cleanly.
- **Structural cross-validation beyond the shipped test file**, performed
  during authoring, before the corresponding test assertions were
  written: a Python pass extracted and decoded all four `EXEC(N'...');`
  dynamic-SQL batches (properly unescaping `''`) and confirmed each
  decoded procedure body contains exactly two `SELECT` keywords and the
  expected `JOIN dbo.` count; a paren-balance check across all three
  `.sql` files; a character-by-character string-literal balance scan
  (treating `''` as an escaped quote, and correctly treating `--` as a
  line comment ONLY when encountered outside an open string literal, so a
  prose em dash inside a quoted message is never mistaken for a comment
  start) confirmed every `.sql` file in this candidate ends outside any
  open string literal; a THROW-number scan across every `.sql` file under
  `SQL FIles/` confirmed the highest prior number anywhere was 58553
  before claiming the 58600-58699/58700-58799 ranges, and confirmed zero
  collisions after; a direct simulation of the test file's own
  `content_select_columns` extraction against the actual migration text
  confirmed every `DOMAINS` field tuple matches the real SQL output
  before the corresponding test was even run.
- **Real defects found and fixed during self-review, before the shipped
  test suite was finalized:**
  1. The migration file's first draft left one parenthesis unclosed in a
     header comment (`READER 4: dbo.opportunity_saved_evidence (2 content
     columns -- ordinal, clause_ordinal -- plus...`, opening a paren the
     sentence never closed). Caught by an automated paren-balance scan
     (`text.count("(") == text.count(")")`) that reported the exact
     unmatched-open location by line number; corrected by restructuring
     the sentence to close the parenthetical properly, then re-verified.
  2. The ledger description's first draft measured 480 of the budgeted
     450 characters -- `PS-SETTINGS-EXPORT-003`'s own gate round failed on
     an identical class of overrun. Caught by the same character-count
     script this package's own test later formalizes; trimmed to 441
     characters by removing redundant phrasing ("2026-08-29 topology",
     "member", "table") without losing any load-bearing fact.
  3. A first-pass diagnostic script for the string-literal balance scan
     produced a false positive on the verification file (naively cutting
     each line at its first `--`, which incorrectly truncated a THROW
     message string that legitimately contains `--` as a prose em dash
     inside its own quoted text, e.g. "...dynamic SQL -- it is not a
     plain read-only SELECT."). Corrected the scan itself to track
     in-string state properly and only treat `--` as a comment start
     outside an open string literal, at which point the file re-confirmed
     as properly balanced. Recorded here because it is a real lesson about
     writing verification tooling, not a defect in the shipped SQL.

## Gate state

**Gate proof: SEALED — two full-pass runs, the second the standing seal.**

- **Run 1 (manager, 2026-08-29, first-run full pass)** on disposable
  `ps-migration-path-20260829-os` (created for the proof, deleted after):
  prerequisite chain replayed, forward apply created exactly four reader
  procedures, idempotent re-apply changed nothing, the isolation
  verification — the first INSERT exercise of these four tables'
  constraint sets anywhere in this program — executed and returned
  `verified = 1`, the rollback rehearsed and the forward re-applied.
  Sealed as digest `f283c79f9423892f4987fe88a6a01f642030a7e327a7719a7a88ca9b45eae8f7`
  in the manager lockstep commit `7426af65`, which also replaced the
  pre-scripted placeholder test with
  `test_registry_entry_pins_the_sealed_gate` implementing all five
  prescribed steps (literal digest, recomputed-file check, four objects
  with the prefix check, the exact verification string).
- **Run 2 (manager, 2026-08-29, independent-review correction round,
  full pass; the seal now standing in the registry)** on disposable
  `ps-migration-path-20260829-os2` (created for the proof, deleted
  after): the same complete sequence re-executed against the amended
  forward file after the review-directed `saved_analysis_key` exclusion
  (see "Independent-review correction round" below). Sealed as digest
  `3db5eff29654109f35e3c5a8ef1df0d442a316258d82b41fe1fff1868be2ed80`,
  `gated_at_utc: 2026-08-29T18:21:30Z`, verification
  `PS-SETTINGS-EXPORT-006_oppslate_reader_isolation_verify.sql returned
  verified = 1`; the same commit moved the test's literal pin and this
  section — registry + test + report, the standing rule executed
  complete both times. Run 1's digest is superseded, not erased: it
  remains true of the pre-correction file content it sealed.

The writer authored this candidate with `gate: null` and no database
access; earlier writer-voice passages saying so describe the authoring
state and this section records the sealed result.

Because this package's fixture is unusually deep (a four-level join chain
with every `NOT NULL`/`CHECK`/`FOREIGN KEY` on all four tables
hand-traced against `PS-OPPSLATE-003_opportunity_slate_os4.sql`, not run
against an engine), the manager's gate run carries more first-time proof
weight here than for a shallower sibling package: this is the first time
any of these four tables' constraints will actually be exercised by an
`INSERT` anywhere in this reader program.

## Independent-review correction round (manager, 2026-08-29)

The independent review of candidate `7426af65` returned **CONDITIONAL**:
no correctness, isolation, privacy, or release-safety defect; the
durability judgment independently re-derived and confirmed from the
migration files; all eight mutation probes caught. Five findings were
corrected in this round, in one commit together with gate run 2's seal:

1. **F1 (MEDIUM, records):** four passages of this report still described
   the gate as not run after "Gate state" was sealed. All four now state
   the sealed truth (this round's edits at the registry-validator bullet,
   the static-proof limitation, the "Gate proof" bullet, and the
   pre-scripted-lockstep note).
2. **F2 (MEDIUM, the one substantive change):** `saved_analysis_key` is
   now **EXCLUDED** from the saved-result reader as `AI_MODEL_PROVENANCE`.
   The original keep rested on the premise that it is not an id; the
   review showed it IS an id — a `uniqueidentifier` naming which AI
   analysis run produced the save, inside the directive category's own
   "Model names/ids" definition — and that its member-readable export
   value is nil (the run it names is ephemeral and already purged). This
   is directive execution, not a fresh owner decision: the owner's
   accepted 2026-08-29 topology directive excludes AI/model provenance
   from this reader. The exclusion changed the forward migration's
   executable content, so the gate was re-run in full (run 2 above) and
   re-sealed; the adapter tuple, forbidden-field pins, directive-category
   pins, verify-script scan and capture shape, and both package documents
   moved in the same commit.
3. **F3 (LOW/MEDIUM, records):** two misquotations of schema-author
   intent corrected — "a sentence about the **member**" (not "model"),
   and the "[the AI]" gloss removed from the evidence_considered_count
   quote — in the contract document and the migration header. The
   substantive inclusion argument for `derived_status`/`citation_count`
   was found accurate and stands.
4. **F4 (LOW, records):** the verification detail string overclaimed
   "every response-shape branch"; it now states "three of the four".
   Corrected before gate run 2, so the standing seal executed the
   corrected script.
5. **F5 (LOW, records):** the directive-excluded column count in this
   report corrected (now sixteen, including `saved_analysis_key`).

**Acknowledged, unchanged by design:** F6 (INFO) — fixture saved-result
A1 declares `qualification_count = 2` / `evidence_considered_count = 3`
with no child qualification rows of its own (all children hang off A2).
This violates no constraint and breaks no assertion (the declared counts
are what the reader must export, and the export-value assertions test
exactly that); left as-is per the reviewer's own no-change-requested
finding, recorded here so it is not mistaken for an oversight. The
reviewer's forward observation about the `visibility = 'private'`
predicate cutting the opposite way in an export reader is already
recorded as the contract document's own forward note.

## Protected and release state

- **Independent review:** Required (`review_requirement: "independent"` on
  the lane claim) and not yet performed. This report does not claim a
  review occurred.
- **Repository state:** Candidate on the claimed branch, pushed per the
  writer brief (writer pushes and stops; no PR, no merge).
- **Deployment/schema state:** Withheld entirely
  (`production_authority: "withheld"` on the lane claim). No database was
  contacted by this writer or by any test -- every SQL assertion in this
  candidate is a static read of the committed `.sql` text (including via
  `scripts/migration_registry.load_registry()`, which itself opens no
  connection), and every Python adapter test uses a fake cursor/
  connection double.
- **Least-privilege SQL grant:** Design documented only (see
  `CR4_ACCOUNT_EXPORT_OPPSLATE_READER.md`'s "Grant model" section,
  identical to every prior package's own recorded model). Nothing
  applied -- the governed apply identity holds `db_ddladmin` only and
  this migration contains no `GRANT` statement of any kind. This is a
  paper design for the manager's future, separately authorized
  administrator-run grant operation, not a change made or proposed to any
  live permission.
- **Current product truth:** Account-wide export remains unavailable
  today. This candidate adds four more read-only reader procedures and
  four more adapter functions that nothing calls yet. No member-visible
  behavior changed. The Opportunity Slate room itself remains flag-off
  (`PEERSLATE_OPPORTUNITY_SLATE_ENABLED` unset per `PS-OPPSLATE-001`'s own
  header), unaffected by and unrelated to this package.

## Limitations, rollback, and next action

- **No live database proof of any kind from this writer.** Every SQL
  assertion in this candidate is a static text read; every Python test
  uses a fake cursor. All four procedures' actual runtime correctness
  against a real SQL Server engine -- including every hand-satisfied
  `CHECK`/`FOREIGN KEY` constraint the verification script's fixture data
  must clear across a four-table chain -- was unproven until the manager's
  gate runs executed it (both have since done so; see "Gate state"
  above). Self-review traced every `NOT NULL`/`CHECK`/
  `FOREIGN KEY` constraint on all four touched tables against the fixture
  `INSERT`s by re-reading `PS-OPPSLATE-003_opportunity_slate_os4.sql`
  before writing them, but this remains a static trace, not an actual
  engine run.
- **Gate proof: SEALED.** See "Gate state" above.
- **No reader is wired to anything.** Nothing in this candidate connects a
  domain reader to any worker or route; `services/account_export_domain_
  readers.py`'s four new functions exist and are fully tested offline,
  but nothing calls them yet.
- **`opportunity_saved_evidence`'s reader carries almost no informational
  content today.** Only `ordinal`/`clause_ordinal` survive the directive's
  two broadest exclusion categories landing on the same table; a member
  reading this reader's export output learns positional counts with no
  indication of what evidence they refer to. This is a disclosed, direct
  consequence of the current directive, not an implementation gap -- a
  future, separately reviewed relaxation of the evidence-linkage
  boundary would need to revisit this table specifically.
- **Deviations from the brief:**
  1. **`PS-OPPSLATE-004`'s `opportunity_source_identities`,
     `opportunity_requirement_review_events`, and
     `opportunity_member_takes` are excluded, not read**, directly
     contradicting the writer brief's own "expect" framing that named
     the latter two as "the 004 replacement's durable member tables."
     This is not a deviation from an explicit instruction -- the brief
     explicitly required judging each table against the schema rather
     than trusting the "expect" framing -- but it is the single largest
     substantive finding in this package, fully reasoned in "Design
     decisions" item 1 above and in
     `CR4_ACCOUNT_EXPORT_OPPSLATE_READER.md`'s durability-judgment
     section, with the exact DELETE-statement citations a reviewer would
     need to re-verify it independently.
  2. **`requires` includes the full `PS-OPPSLATE-001/002/003` chain**
     even though this migration's own guards do not strictly need
     `PS-OPPSLATE-001`/`002`'s ledger rows for any column or table they
     created (all four tables this migration reads are created solely by
     `PS-OPPSLATE-003`). Disclosed in "Design decisions" item 2 above: a
     conservative, in-family-precedent choice, not a discovered technical
     necessity.
  3. **`idempotency_key` is excluded even though it is not named by any
     of the four directive categories.** Disclosed in "Design decisions"
     item 6 above as an extension of an existing program precedent
     (machinery, not content) applied at column rather than table
     granularity for the first time in this program.
  4. **No other deviation.** Every deliverable path the brief names
     (migration, rollback, registry entry, verification script, adapter
     update, this package's own test file, both docs) was created at its
     exact claimed location; no other unclaimed path was touched,
     confirmed by `git status --short` before staging; no sibling test
     file needed a scope correction (see "Excluded actions and paths"
     above).
- **What the manager's gate and any future package must know:**
  - The gate-pin lockstep PRE-SCRIPTED by this writer has since been
    EXECUTED, twice and completely: the manager's gate commit (`7426af65`)
    replaced the placeholder test, sealed the registry, and rewrote "Gate
    state" as one commit, and the independent-review correction round
    re-ran the gate after the `saved_analysis_key` exclusion and moved
    all three artifacts again in its own single commit -- registry + test
    + report, both times.
  - `services/account_export_domain_readers.py`'s `DOMAINS` registry now
    has seven included domains totalling twenty-two readers (ten from
    package 1, six from package 2, two from package 3, four from this
    package). This is the FINAL content reader of the accepted topology
    per the lane claim's own framing; a future package adding a further
    domain should still apply the same scoping discipline every test file
    in this program has used since package 1's own retroactive fix --
    scope new/changed assertions to the domains a package actually owns.
  - **`PS-OPPSLATE-004` remains a live, separate R1 shell architecture**
    with its own future R2+ work (its own header names eight deferred
    procedures: `usp_SaveOpportunityRequirementReviewForOwner`,
    `usp_ConfirmOpportunityRequirementsForOwnerR`,
    `usp_ReviseOpportunityRequirementsForOwner`,
    `usp_SaveOpportunityMemberTakeForOwner`,
    `usp_ReviewOpportunityMemberResponseForOwner`,
    `usp_ContinueOpportunityQualificationForOwner`,
    `usp_SaveOpportunityAnalysisForOwnerR`,
    `usp_GetOpportunityRoomForOwnerR`). If a future R2+ package ever
    introduces the replacement architecture's OWN durable save mechanism
    (distinct from OS-4's legacy one), that would be a NEW durable table
    group this package's own table-by-table judgment did not anticipate
    and does not cover -- a future account-export package would need to
    re-run the same durability judgment this package performed, not
    assume today's `opportunity_slate` domain already covers it.
  - Every table this package excludes is recorded with its exact
    reasoning in `services/account_export_domain_readers.py`'s module
    docstring and in `CR4_ACCOUNT_EXPORT_OPPSLATE_READER.md`; a future
    reader of either should not need to re-derive the ephemeral/durable
    split from scratch, only re-verify it still holds if any
    `PS-OPPSLATE-*` migration changes.
