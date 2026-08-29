# CR3 owner technical completion report

## Core record

- **Task/package and delivery path:**
  `PS-SETTINGS-ACCOUNT-EXPORT-WORKSHOP-READER-001`, Protected, replacement
  package 3 of the 2026-08-29 reader topology, after
  `PS-SETTINGS-ACCOUNT-EXPORT-CORE-READERS-001` (replacement package 1,
  main `cc5174da`) and
  `PS-SETTINGS-ACCOUNT-EXPORT-CAPTURE-MOMENT-READERS-001` (replacement
  package 2, main `1f701263`) were both independently reviewed and merged.
- **Outcome and candidate scope:** Read-only, owner-scoped account-export
  readers for the Workshop / My Knowledge domain -- `dbo.knowledge_items`,
  `dbo.knowledge_item_versions` -- as two
  `usp_ReadAccountExport<Table>ForOwner` procedures in one additive
  migration (`PS-SETTINGS-EXPORT-005`); a data-safe rollback; a registry
  entry (authored with `gate: null`; no gate has been run by this writer
  -- see "Gate state" below) (`requires: ["PS-AUTH-001",
  "PS-WORKSHOP-001", "PS-WORKSHOP-002"]` -- `PS-AUTH-001` named from the
  start for the verification script's dependency, `PS-WORKSHOP-001`/`002`
  as the applied migrations whose knowledge tables this package reads);
  an isolation-verification script whose fixtures satisfy every `NOT
  NULL`/`CHECK`/`FOREIGN KEY` constraint on both touched tables; updates
  to the shared `services/account_export_domain_readers.py` adapter (two
  new reader functions, `workshop_my_knowledge` flipped from `excluded` to
  `included`, one new named excluded entry
  `workshop_knowledge_save_requests`); and offline tests pinning every
  field allowlist, every forbidden-field exclusion, the both-sided owner
  predicate on the versions reader, and every structural safety property.
  No table, trigger, index, container, worker wiring, route, or UI is
  added or changed. No schema apply, database connection, or Azure call
  was made by this writer.
- **Package manager and writer:** Sole writer
  `agent:claude-code/settings-wk-reader-writer`, working only in the
  durable worktree
  `C:\Users\peter\Documents\PeerSlateWorktrees\PS-SETTINGS-ACCOUNT-EXPORT-WORKSHOP-READER-001`
  on branch `work/2026-08-29-settings-account-export-workshop-reader-001`.
  The lane claim's `surfaces` list names eleven paths; three of them (the
  claim JSON itself, its evidence file, and its receipts file) are
  reserved for the manager's gate/review stage, matching both prior
  packages' identical exclusion -- this writer created or modified the
  other eight, confirmed by `git status --short` before staging (six new
  files, two modified: `SQL FIles/Migrations/registry.json` and
  `services/account_export_domain_readers.py`). No file outside the
  claim's eleven surfaces was touched.
- **Base SHA and branch:** Activated from `origin/main` `65c64db2` per the
  lane claim (`activated_from_main`); worktree `HEAD` confirmed at exactly
  `a56c1dd7b79dfc47993eb298c1ce90df74637f29` (`git rev-parse HEAD`) before
  any write, one commit ahead of the claim's activation SHA on `main`
  (`a56c1dd7` is PR 711, the delivery-activation merge for this exact
  package) -- the identical "base main, or the one delivery-activation
  commit after it" pattern both prior packages in this program recorded.
  No other commit had landed on this branch before this candidate.
- **Final SHA:** This report is authored, per the writer brief, **before**
  the final commit(s) exist on
  `work/2026-08-29-settings-account-export-workshop-reader-001` -- it
  cannot record a final SHA it has not yet produced. The exact value is
  in the writer's chat-turn final message and in `git log` on the pushed
  branch, not in this file.
- **Candidate changed paths** (six new, two modified; nothing else in the
  worktree was touched -- confirmed by `git status --short` before
  staging):
  - `SQL FIles/Migrations/PS-SETTINGS-EXPORT-005_workshop_reader.sql` (new)
  - `SQL FIles/Migrations/PS-SETTINGS-EXPORT-005_workshop_reader_rollback.sql` (new)
  - `SQL FIles/Migrations/registry.json` (modified -- one entry appended)
  - `SQL FIles/Verification/PS-SETTINGS-EXPORT-005_workshop_reader_isolation_verify.sql` (new)
  - `services/account_export_domain_readers.py` (modified -- see "Design
    decisions" below)
  - `tests/test_settings_export_workshop_reader.py` (new)
  - `docs/initiatives/PS-SETTINGS-MY-DATA-SHELL-001/CR3_ACCOUNT_EXPORT_WORKSHOP_READER.md` (new)
  - `docs/initiatives/PS-SETTINGS-MY-DATA-SHELL-001/CR3_OWNER_TECHNICAL_COMPLETION_REPORT.md` (this file, new)
- **Excluded actions and paths:**
  `docs/governance/lane_claims/PS-SETTINGS-ACCOUNT-EXPORT-WORKSHOP-READER-001.json`,
  its `evidence/*.md`, and its `receipts/*.json` were not created or
  modified -- all three are reserved for the manager's gate/review stage.
  `tests/test_settings_export_core_readers.py` and
  `tests/test_settings_export_capture_moment_readers.py` were run, both
  green **unmodified** -- see "Validation and self-review" below; unlike
  package 2's own experience with package 1's file, no narrow scope
  correction was needed in either sibling test file this time (package
  2's own two fixes already generalized the coupling-prone assertions).
  No route, template, worker wiring, scheduler, container, workload
  identity, grant, `.env.example` entry, dependency, or production
  operation changed. No database connection, Azure call, or network call
  of any kind was made by this writer or by any test in this candidate.
  `git fetch` was never run, per the writer brief.

## Design decisions worth the reviewer's attention

Full field-by-field reasoning lives in
`CR3_ACCOUNT_EXPORT_WORKSHOP_READER.md`; this section lists only the
decisions with the widest blast radius.

1. **`dbo.knowledge_item_versions`' owner-predicate shape was derived from
   the schema, not assumed, and differs from both sibling version-history
   tables.** The writer brief explicitly flagged this as uncertain ("via
   an owner-predicated-both-sides join if the versions table lacks its
   own owner column -- derive from schema"). Reading
   `PS-WORKSHOP-001_knowledge_items.sql` directly shows
   `dbo.knowledge_item_versions` **carries its own `owner_profile_id`
   column**, required by its composite foreign key
   `FK_knowledge_item_versions_item (knowledge_item_id, owner_profile_id)
   -> dbo.knowledge_items(knowledge_item_id, owner_profile_id)` -- the
   opposite shape from `dbo.capture_revisions`/`dbo.moment_versions`
   (`PS-SETTINGS-EXPORT-004`), which carry no such column and use a
   single, parent-only predicate. This reader therefore uses the
   **both-sided** predicate
   (`version_record.owner_profile_id = @ProfileId AND
   item.owner_profile_id = @ProfileId`) -- the shape
   `PS-SETTINGS-EXPORT-004` used for `dbo.moment_sources`/
   `dbo.moment_placements`, never the parent-only shape that same package
   used for its own version-history tables. This is the one decision in
   this package most likely to draw independent-review scrutiny, because
   it would be easy to assume "a version-history table" always means
   "parent-only" from the sibling package's precedent without re-checking
   this specific table's own DDL -- pinned by a dedicated test
   (`test_both_sided_owner_predicate_present_where_the_table_carries_its_own_owner_profile_id`)
   rather than one test silently assuming the shape is uniform across the
   whole program.
2. **`dbo.knowledge_item_versions` has no opaque key column of its own.**
   Unlike `dbo.capture_revisions.revision_key`/
   `dbo.moment_versions.moment_version_key`, this table's primary key is a
   plain, never-exposed `IDENTITY(1,1) bigint`. Its exported identifying
   tuple is `(knowledge_item_key, version_number)`, already unique per
   `UQ_knowledge_item_versions_number`. No surrogate key is manufactured
   for a column the schema does not have; the reader's output column list
   reflects that directly (`knowledge_item_key` leads, in the position the
   sibling readers use for their own opaque key, followed by
   `version_number`).
3. **`dbo.knowledge_item_save_requests` excluded as its own named
   `DOMAINS` entry.** `PS-WORKSHOP-001` creates three tables, not two;
   this idempotency ledger (an owner-scoped replay key and the resulting
   `knowledge_item_id` only, no title/wording/status) is machinery, not
   content. Recorded as `workshop_knowledge_save_requests` -- the
   identical treatment `PS-SETTINGS-EXPORT-003` gave `career_skill_links`
   and `PS-SETTINGS-EXPORT-004` gave `target_entity_id`/`dbo.slate_entities`
   -- rather than silently folded into `workshop_my_knowledge` or omitted.
4. **Ordering by `created_at_utc` ascending (creation order), not
   `usp_ListKnowledgeItemsForOwner`'s own `updated_at_utc DESC` list
   order.** The live Workshop UI's own reader orders "most recently
   edited first" -- a UX choice for that page, not a truth requirement for
   an export. This reader uses the same stable creation-chronological
   order every other top-level reader in this program already uses
   (`dbo.captures`, `dbo.moments`), so a member's Workshop items and every
   other domain in their export read in a consistent order. Not named in
   the writer brief by table; a direct, schema-scale application of the
   ordering pattern the brief does name.
5. **`item_status = 'suggested'` is not special-cased or excluded.**
   `CK_knowledge_items_status` allows it (an AI-proposed, unaccepted
   draft), but `PS-WORKSHOP-002`'s own header confirms via a full grep of
   `services/` that no production code path writes it today. This reader
   reports whatever status is actually stored, matching this program's
   "text truth only" principle, and records a forward-looking note (the
   same class `PS-SETTINGS-EXPORT-004` recorded for `PS-JOURNAL-001`'s
   future `dbo.moments.archived_at_utc`) that a future AI-suggestion write
   path must revisit whether an unaccepted `'suggested'` row belongs in an
   export at all.
6. **`requires` includes `PS-WORKSHOP-002` even though this package's own
   guards do not need a column or table it created.** `PS-WORKSHOP-002`
   added no table (only a procedure and a revised predicate). The
   `requires` list and this migration's own ledger-existence guard for
   `PS-WORKSHOP-002` are included anyway, matching the lane claim's own
   outcome framing ("the applied PS-WORKSHOP-001/002 knowledge tables" as
   the schema baseline this package targets) and the precedent
   `PS-WORKSHOP-003` itself set (guarding on `PS-WORKSHOP-002`'s ledger
   presence without needing any column it added). This is a conservative,
   disclosed choice, not a discovered necessity.

## Validation and self-review

- **Verbatim final run** (checked by exit code directly, output
  redirected to a file rather than piped, never through a second command
  that would report ITS OWN exit code instead):
  ```
  ANTHROPIC_API_KEY=placeholder "C:\Users\peter\Documents\portfolio\venv\Scripts\python.exe" -m pytest -q tests/test_settings_export_workshop_reader.py tests/test_settings_export_core_readers.py tests/test_settings_export_capture_moment_readers.py tests/test_settings_account_export_migration.py tests/test_account_export_assembly.py tests/test_account_export_storage.py
  ......................................................................................... [ 38%]
  ................................................. [ 59%]
  ............................................................. [ 85%]
  ..................................                      [100%]
  233 passed, 1546 subtests passed in 87.54s (0:01:27)
  PYTEST_EXIT_CODE_IS=0
  ```
  - `tests/test_settings_export_workshop_reader.py` (this package's own
    file, 48 tests / 347 subtests): migration/rollback/verify file shape
    (single guarded batch, balanced parens/comments, no `\nGO`);
    THROW-number uniqueness within the forward and rollback files
    (58400-58499) and the verify file's own numbers confirmed inside its
    reserved 58500-58599 block, plus a repository-wide scan confirming no
    sibling `.sql` file anywhere under `SQL FIles/` reuses either range
    (highest prior use anywhere was 58362 before this package); exactly
    the two claimed procedures created and no table/trigger/index; never
    redefines another migration's procedure; the forward file's guards
    check exactly `PS-WORKSHOP-001`/`PS-WORKSHOP-002` and never
    `PS-AUTH-001`/`PS-WORKSHOP-003`/`PS-WORKSHOP-004`; no reader body
    references `knowledge_item_save_requests`; every signature is exactly
    `@UserKey nvarchar(300)`; every procedure shares the byte-identical
    identity-resolution header; every procedure filters by its expected
    owner predicate, including the both-sided check for the versions
    reader and confirming the items reader has no content-level join at
    all; deterministic `ORDER BY` present (with the versions reader's
    parent-then-sequence grouping checked precisely) and no `SELECT *`;
    neither reader references a soft-delete column of any kind (confirmed
    against both procedure bodies, since neither table has one); every
    procedure returns the two read-window trailing columns with exactly
    two `SELECT` keywords; no procedure contains any transaction control,
    write, or nested `EXEC`; no procedure accepts a caller-selected
    owner/target parameter; no `GRANT`/role/user creation; forbidden
    fields (full-name sets) absent from every reader's actual output
    columns; `DOMAINS`' field-allowlist tuples equal the actual SQL output
    column list exactly, in order, for both (as a subset check against the
    shared dict); the ledger description measured at 430 of 450 budgeted
    characters; the rollback drops exactly the two procedures and removes
    only this migration's ledger row; the registry entry pins `requires`
    exactly and asserts `gate is None` with an explicit, pre-scripted
    lockstep docstring naming all five steps the manager's gate commit
    must take, plus the "registry + test + report" lockstep-set note
    package 2's own gate commit initially missed; the verify script
    provisions three synthetic owners including one deactivated, never
    commits, always reaches `ROLLBACK TRANSACTION;` before its report
    `SELECT`, and invokes both procedures via both a genuinely bare `EXEC`
    and an `INSERT ... EXEC`; adapter offline tests using fake
    cursors/connections confirm both new domain functions are
    independently callable, decode the parent linkage key correctly,
    return empty rows (never an error) for an unresolved identity, never
    call `commit`/`rollback`/`close` on the caller's connection, and bind
    `@UserKey` as a driver parameter; and the `DOMAINS` registry has
    exactly one new included domain (`workshop_my_knowledge`, scoped
    comparison) with exactly two readers in source order, plus the new
    named exclusion `workshop_knowledge_save_requests`, and no reason
    string leaks a forbidden field name.
  - `tests/test_settings_export_core_readers.py` (package 1's own file, 42
    tests) and `tests/test_settings_export_capture_moment_readers.py`
    (package 2's own file, 52 tests): **both run and green unmodified.**
    Read in full before this package touched `services/account_export_
    domain_readers.py`, to confirm which assertions were already properly
    scoped to their own package's domains/procedures (a subset check or an
    explicitly named-domain comprehension) versus which walked the whole
    `DOMAINS` dict unconditionally. Every unconditional, whole-dict
    assertion found (`test_included_domains_have_no_reason_others_have_a_
    stable_reason`, `test_no_domain_reason_leaks_a_forbidden_field_name`,
    `test_reader_entries_have_unique_procedures_and_schema_ids[...]`) is a
    genuine cross-package invariant (not a hardcoded count), so this
    package's additions satisfy it without modification. No narrow scope
    correction was needed in either file this time.
  - `tests/test_settings_account_export_migration.py`,
    `tests/test_account_export_assembly.py`,
    `tests/test_account_export_storage.py`: unchanged, still green --
    confirms this candidate did not disturb the accepted C1/C2 migration,
    assembly, or storage code.
- **Also run via `python -m unittest`** (the actual CI mechanism, not just
  pytest), output redirected to a file and its exit code read directly
  (never through a pipe): `Ran 233 tests ... OK`, exit code `0` -- confirms
  the suite is green under both runners.
- **A full collect-only pass of the entire repository test suite**
  (`pytest --collect-only -q tests/`): 4,480 tests collected, exit code 0,
  no collection error -- confirms these new/changed files do not break
  import/discovery anywhere else in the repository.
- **`scripts/migration_registry.load_registry()`** (the registry's own
  offline, no-connection validator), invoked directly in Python: loads
  all 40 entries without error, `PS-SETTINGS-EXPORT-005`'s `requires`
  resolve to `('PS-AUTH-001', 'PS-WORKSHOP-001', 'PS-WORKSHOP-002')`,
  `gate` was `None` at authoring time (the sealed digest `08eaa00e…` is
  now pinned in "Gate state" below and in the replaced registry test),
  both the forward and rollback files resolve and exist, and
  `executable_sha256(forward)` computes cleanly.
- **Structural cross-validation beyond the shipped test file**, performed
  during authoring, before the corresponding test assertions were
  written: a Python pass extracted and decoded both `EXEC(N'...');`
  dynamic-SQL batches (properly unescaping `''`), confirmed each decoded
  procedure body is paren-balanced with exactly one `BEGIN`/`END` pair;
  a character-by-character string-literal balance scan (treating `''` as
  an escaped quote, stripping `/*...*/` and `--` comments first) confirmed
  every `.sql` file in this candidate ends outside any open string
  literal; a THROW-number scan across every `.sql` file under
  `SQL FIles/` confirmed the highest prior number anywhere was 58362
  before claiming the 58400-58499/58500-58599 ranges, and confirmed zero
  collisions after.
- **Real defects found and fixed during self-review, before the shipped
  test suite was finalized:**
  1. The migration file's first draft double-escaped the dynamic-SQL
     string literals inside `EXEC(N'...')` (writing `N''''''''` for the
     empty-string comparison and `N''''private''''` for the visibility
     predicate, each one doubling level too many). Caught by decoding both
     batches and inspecting the resulting inner T-SQL directly rather than
     trusting the source text by eye; corrected to the single level of
     doubling every sibling migration in this program actually uses
     (`N''''` and `N''private''`), then re-verified via the same
     character-by-character balance scan.
  2. `test_knowledge_item_reader_has_no_parent_to_join`'s first draft
     asserted `assertNotIn("JOIN dbo.", body)` for the top-level items
     reader -- this false-positived on the shared identity header's own
     `JOIN dbo.app_users AS app_user`, which every reader in this program
     carries regardless of whether its content query joins anything.
     Corrected to count `JOIN dbo.` occurrences (exactly one expected,
     the identity header's own) rather than asserting total absence.
  3. `test_verify_never_references_a_soft_delete_column`'s first draft
     asserted the literal string `"deleted_at_utc"` never appears anywhere
     in the verification script -- this false-positived on the script's
     own structural `LIKE N'%deleted_at_utc%'` check (a legitimate,
     intentional reference: the search pattern for the very tripwire that
     proves neither procedure references that column). Corrected to
     assert the check pattern IS present and that no fixture/assertion
     line treats it as a presence predicate
     (`deleted_at_utc IS NULL`/`IS NOT NULL`), rather than a blanket
     substring ban that could never coexist with the check it was meant
     to confirm.

## Gate state

**Gate proof: SEALED — first-run full pass** (manager, 2026-08-29, in the
same lockstep commit that writes this section). The governed gate ran on
disposable `ps-migration-path-20260829-wk` (created for the proof, deleted
after): prerequisite chain replayed, forward apply created exactly two
reader procedures, idempotent re-apply changed nothing, the isolation
verification executed and returned `verified = 1`, the rollback rehearsed
and the forward re-applied. The proof is sealed in the registry with
digest `08eaa00e17183c0759fd8be86de96a07cf9feb5fce8f651399d6ed0bfb1c5704`,
and this same commit replaced the pre-scripted placeholder test with
`test_registry_entry_pins_the_sealed_gate` implementing all five
prescribed steps (literal digest, recomputed-file check, two objects with
the prefix check, the exact verification string). The writer authored this
candidate with `gate: null` and no database access; wherever earlier
writer-voice passages say so, they describe the authoring state and this
section records the sealed result — the lockstep set (**registry + test +
report**, the standing rule from package 2's review) is satisfied in one
commit this time.

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
  `CR3_ACCOUNT_EXPORT_WORKSHOP_READER.md`'s "Grant model" section,
  identical to `PS-SETTINGS-EXPORT-001`'s/`003`'s/`004`'s own recorded
  model). Nothing applied -- the governed apply identity holds
  `db_ddladmin` only and this migration contains no `GRANT` statement of
  any kind. This is a paper design for the manager's future, separately
  authorized administrator-run grant operation, not a change made or
  proposed to any live permission.
- **Current product truth:** Account-wide export remains unavailable
  today. This candidate adds two more read-only reader procedures and two
  more adapter functions that nothing calls yet. No member-visible
  behavior changed.

## Limitations, rollback, and next action

- **No live database proof of any kind from this writer.** Every SQL
  assertion in this candidate is a static text read; every Python test
  uses a fake cursor. Both procedures' actual runtime correctness against
  a real SQL Server engine -- including every hand-satisfied
  `CHECK`/`FOREIGN KEY` constraint the verification script's fixture data
  must clear (`CK_knowledge_items_confirmation_state`'s strict tri-state,
  `CK_knowledge_items_archive_pair`, and the composite
  `FK_knowledge_item_versions_item` foreign key) -- is unproven until the
  manager's gate run executes it. Self-review traced every `NOT
  NULL`/`CHECK`/`FOREIGN KEY` constraint on both touched tables against
  the fixture `INSERT`s by re-reading `PS-WORKSHOP-001_knowledge_items.sql`
  before writing them, but this remains a static trace, not an actual
  engine run.
- **Gate proof: NOT RUN.** See "Gate state" above.
- **No reader is wired to anything.** Nothing in this candidate connects a
  domain reader to any worker or route; `services/account_export_domain_
  readers.py`'s two new functions exist and are fully tested offline, but
  nothing calls them yet.
- **Deviations from the brief:**
  1. **`dbo.knowledge_item_versions`' both-sided (not parent-only) owner
     predicate** and its **lack of an opaque key column** are both
     interpretations of a claim that named the general pattern but not
     this specific table's exact shape; both are recorded with full
     reasoning in `CR3_ACCOUNT_EXPORT_WORKSHOP_READER.md`'s
     "Interpretation notes" and summarized in "Design decisions" above.
     Not a deviation from an explicit instruction -- the brief explicitly
     anticipated needing to "derive from schema" -- but the judgment call
     most likely to draw review attention.
  2. **`requires` includes `PS-WORKSHOP-002`** even though this
     migration's own guards do not need any column or table it created
     (`PS-WORKSHOP-002` added a procedure, not a column). Disclosed in
     "Design decisions" item 6 above: a conservative, schema-baseline
     choice consistent with the lane claim's own outcome framing and
     `PS-WORKSHOP-003`'s own precedent, not a discovered technical
     necessity.
  3. **No other deviation.** Every deliverable path the brief names
     (migration, rollback, registry entry, verification script, adapter
     update, this package's own test file, both docs) was created at its
     exact claimed location; no other unclaimed path was touched,
     confirmed by `git status --short` before staging; neither sibling
     test file needed a scope correction this time (see "Excluded actions
     and paths" above).
- **What the manager's gate and any future package must know:**
  - The gate-pin lockstep is PRE-SCRIPTED but NOT YET EXECUTED: when
    gated, `tests/test_settings_export_workshop_reader.py`'s placeholder
    test and this report's "Gate state"/"Gate proof" passages must both
    change in the SAME commit that writes the seal into the registry --
    registry + test + report, the three-element set package 2's own
    independent review had to add after the fact.
  - `services/account_export_domain_readers.py`'s `DOMAINS` registry now
    has six included domains totalling eighteen readers (ten from
    package 1, six from package 2, two from this package), plus two named
    excluded sibling entries for a table a package deliberately did not
    read (`career_skill_links` from package 1,
    `workshop_knowledge_save_requests` from this package -- package 2's
    `target_entity_id` exclusion is a field-level exclusion inside the
    `moment` domain, not a separate top-level entry, since
    `dbo.slate_entities` is not one of that package's six claimed
    tables). A future package 4 that adds its own included domain(s)
    should apply the same scoping discipline already established in both
    sibling test files -- scope new/changed assertions to the domains a
    package actually owns, never to "whatever the whole dict currently
    contains."
  - Every Workshop-program lane (`PS-WORKSHOP-PROVENANCE-001` and its
    seven siblings) is closed as of this writing; this package's own
    "Schema revalidation" section in `CR3_ACCOUNT_EXPORT_WORKSHOP_READER.md`
    records the exact recheck performed. A future package that reopens
    Workshop schema work should recheck this package's own two-table
    column enumeration again before assuming it is still current, the
    same discipline this package applied to `PS-WORKSHOP-003`/`004`.
