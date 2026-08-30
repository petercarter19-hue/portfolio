# CR7 owner technical completion report

## Core record

- **Task/package and delivery path:**
  `PS-SETTINGS-ACCOUNT-EXPORT-PREFERENCES-CONSENT-READER-001`, Protected.
  Executes the owner's accepted 2026-08-30 "Paper 2" and "Paper 3"
  rulings: read-only, owner-scoped account-export readers for the
  member's own preference and consent records.
- **Outcome and candidate scope:** Read-only, owner-scoped account-export
  readers for `dbo.connection_preferences`, `dbo.notification_preferences`,
  and `dbo.user_consents` -- three `usp_ReadAccountExport<Table>ForOwner`
  procedures in one additive migration (`PS-SETTINGS-EXPORT-008`); a
  data-safe rollback; a registry entry authored with `gate: null` (no
  gate has been run by this writer -- see "Gate state" below;
  `requires: ["PS-AUTH-001", "PS-PLAT-004"]`); an isolation-verification
  script whose fixtures satisfy every `NOT NULL`/`CHECK`/`FOREIGN KEY`
  constraint on all three touched tables and populate every
  directive-excluded and disclosed-unverified column with a real,
  genuinely-excluded canary value; updates to the shared `services/
  account_export_domain_readers.py` adapter (three new reader functions,
  `connection_preferences`/`notification_preferences`/`consent_history`
  flipped from `excluded` to `included`); and offline tests pinning
  every field allowlist, every forbidden-field exclusion (including the
  one directive category and the one disclosed-but-non-directive
  column), the owner predicate on every table, the dormant-feature
  disclosure label's presence on both preference readers and its
  absence from the consent reader, and every structural safety property.
  No table, trigger, index, container, worker wiring, route, or UI is
  added or changed. No schema apply, database connection, or Azure call
  was made by this writer.

  **The central finding of this package**, recorded in full in
  `CR7_ACCOUNT_EXPORT_PREFERENCES_CONSENT_READER.md`: all three tables
  key on `dbo.app_users.id` (`user_id`), not `owner_profile_id` -- the
  second, third, and fourth readers in this program to do so
  (`usp_ReadAccountExportAccountForOwner` was the first). Every reader
  still resolves the full, byte-identical identity header used
  program-wide, including the otherwise-unused `@ProfileId`, before
  filtering on `user_id = @UserId` -- preserving one identity contract
  program-wide rather than creating a second, weaker one for exactly
  these three readers. The single largest, most review-worthy judgment
  call is `source_context`'s exclusion: unlike every prior "trace the
  actual procedure body" finding in this program, no procedure anywhere
  writes `dbo.user_consents` at all today, so the column was excluded on
  an **absence** of evidence rather than a positive trace -- see
  "Design decisions" item 2 below and the contract document's own
  "Why `source_context` is excluded" section for the full reasoning.
- **Package manager and writer:** Sole writer
  `agent:claude-code/settings-pc-reader-writer`, working only in the
  worktree
  `C:\Users\peter\Documents\PeerSlateWorktrees\PS-SETTINGS-ACCOUNT-EXPORT-PREFERENCES-CONSENT-READER-001`
  on branch
  `work/2026-08-30-settings-account-export-preferences-consent-reader-001`.
  The lane claim's `surfaces` list names twelve paths per this program's
  own established pattern (matching every prior package); three of them
  (the claim JSON itself, its evidence file, and its receipts file) are
  reserved for the manager's gate/review stage and were never created or
  touched. This writer created six new files and modified three claimed
  files (`SQL FIles/Migrations/registry.json`, `services/
  account_export_domain_readers.py`, `tests/test_account_export_integration.py`
  -- the third IS a claimed surface for this package per the writer
  brief, "learned from the prior package"), confirmed by `git status
  --short` before staging.
- **Base SHA and branch:** Activated from `origin/main` at
  `0a5438db2153b4390ba7c802846898ae20956919` per the writer brief ("cut
  from main 0a5438db"); worktree `HEAD` confirmed at exactly this SHA
  before any write (`git rev-parse HEAD`), matching the tip commit's own
  description ("Merge pull request 762 from
  work/2026-08-30-delivery-activation-settings-account-export-preferences-consent-reader-001
  into main [skip ci]") -- the delivery-activation merge for this exact
  package, the identical "base main is the activation commit itself"
  pattern `PS-SETTINGS-EXPORT-007`'s own report recorded when its base
  was one commit after `origin/main`'s prior tip rather than that tip
  directly.
- **Final SHA:** This report is authored, per house convention, at the
  point every deliverable file is complete and self-reviewed but
  **before** the final commit(s) exist on this branch -- it cannot
  record a final SHA it has not yet produced. The exact value is in the
  writer's chat-turn final message and in `git log` on the pushed
  branch, not in this file.
- **Candidate changed paths** (six new, three modified; nothing else in
  the worktree was touched -- confirmed by `git status --short` before
  staging):
  - `SQL FIles/Migrations/PS-SETTINGS-EXPORT-008_preferences_consent_reader.sql` (new, 411 lines -- counts on this list corrected in the independent-review round; several were stale or off by a few lines)
  - `SQL FIles/Migrations/PS-SETTINGS-EXPORT-008_preferences_consent_reader_rollback.sql` (new, 42 lines)
  - `SQL FIles/Migrations/registry.json` (modified -- one entry appended; +34 lines after the manager's gate seal, +11 at writer time)
  - `SQL FIles/Verification/PS-SETTINGS-EXPORT-008_preferences_consent_reader_isolation_verify.sql` (new, 595 lines)
  - `services/account_export_domain_readers.py` (modified -- docstring addition, three new reader functions, three DOMAINS entries flipped; +84/-9 lines)
  - `tests/test_settings_export_preferences_consent_reader.py` (new, 1007 lines after the manager's placeholder replacement; 1030 at writer time)
  - `docs/initiatives/PS-SETTINGS-MY-DATA-SHELL-001/CR7_ACCOUNT_EXPORT_PREFERENCES_CONSENT_READER.md` (new, 448 lines)
  - `docs/initiatives/PS-SETTINGS-MY-DATA-SHELL-001/CR7_OWNER_TECHNICAL_COMPLETION_REPORT.md` (this file, new)
  - `tests/test_account_export_integration.py` (modified -- four snapshot constants bumped, +13/-10 lines; explicitly a claimed surface for this package per the writer brief)
- **Excluded actions and paths:**
  `docs/governance/lane_claims/PS-SETTINGS-ACCOUNT-EXPORT-PREFERENCES-CONSENT-READER-001.json`,
  its `evidence/*.md`, and its `receipts/*.json` were not created or
  modified -- reserved for the manager's gate/review stage.
  `docs/governance/*` outside the lane-claims evidence/receipts pair was
  never touched (the three docs/governance surfaces the brief names as
  reserved). No sibling export test file
  (`tests/test_settings_export_core_readers.py`,
  `tests/test_settings_export_capture_moment_readers.py`,
  `tests/test_settings_export_workshop_reader.py`,
  `tests/test_settings_export_oppslate_reader.py`,
  `tests/test_settings_export_media_transcript_reader.py`,
  `tests/test_settings_account_export_migration.py`,
  `tests/test_account_export_assembly.py`,
  `tests/test_account_export_storage.py`) was found to pin any of this
  package's three domains as excluded -- a repository-wide grep for
  `connection_preferences`/`notification_preferences`/`consent_history`/
  `user_consents` across every file under `tests/` found matches only in
  `tests/test_account_export_integration.py` (this package's own claimed
  surface, updated) and `tests/test_sql_foundation.py` (an unrelated
  schema-text assertion against `PS-PLAT-004`'s own backfill `INSERT`,
  not a `DOMAINS` disposition pin). No cross-package tripwire fired this
  time, unlike `PS-SETTINGS-EXPORT-007`'s own `voice_photo` precedent --
  none of the sibling test files needed a surface extension. No route,
  template, worker wiring, scheduler, container, workload identity,
  grant, `.env.example` entry, dependency, or production operation
  changed. No database connection, Azure call, or network call of any
  kind was made by this writer or by any test in this candidate. `git
  fetch` confirmed the worktree's `HEAD` already matched `origin/main`
  (the branch was cut from the activation commit per the writer brief).

## Design decisions worth the reviewer's attention

Full field-by-field reasoning lives in
`CR7_ACCOUNT_EXPORT_PREFERENCES_CONSENT_READER.md`; this section lists
only the decisions with the widest blast radius.

1. **All three readers filter by `user_id = @UserId` while still
   resolving the full, byte-identical identity header, including the
   otherwise-unused `@ProfileId`.** Confirmed by reading `PS-PLAT-004`'s
   own DDL: all three tables carry `user_id int NOT NULL REFERENCES
   dbo.app_users(id)` and no `owner_profile_id` column at all. This is
   not a new pattern for the program -- `usp_ReadAccountExportAccountForOwner`
   (`PS-SETTINGS-EXPORT-003`) already filters on `@UserId` for the
   identical reason -- and preserving the full header (rather than a
   shortened one that skips the `member_profiles` join) keeps this
   program's one identity contract intact: a member without an active
   profile gets nothing from any reader, including these three. Pinned
   by a dedicated cross-file test extending the program's own
   byte-consistency check
   (`test_identity_header_is_byte_identical_across_every_account_export_reader_in_the_program`,
   scanning `PS-SETTINGS-EXPORT-003` through this package's own file and
   asserting exactly one distinct header variant exists).
2. **`source_context`'s exclusion required concluding an ABSENCE of
   evidence, not tracing a positive procedure body.** A repository-wide
   search for any `INSERT`/`UPDATE`/`DELETE` against `dbo.user_consents`
   returns zero results anywhere in this worktree's `SQL FIles/` tree;
   `PS-ASK-PETE-DIRECT-001`'s own consent value has its own,
   entirely separate storage contract and never touches this table.
   This program's own "trace actual writes" discipline
   (`PS-SETTINGS-EXPORT-007`'s classification of
   `deletion_capture_row_version`/`scan_result`) therefore supplies no
   evidence in either direction for this column; per the writer brief's
   own "if in doubt, EXCLUDE with a reason" instruction, `source_context`
   is excluded as its own disclosed, non-directive-category reason
   (matching `PS-SETTINGS-EXPORT-006`'s `idempotency_key` precedent for
   a program-discipline exclusion rather than an owner-named category),
   explicitly flagged as provisional and re-judgeable the moment a
   future package adds this table's first real writer. This is the
   single decision in this package most likely to draw
   independent-review scrutiny, because a reviewer could reasonably
   argue the column's bounded length and name are themselves sufficient
   evidence to include it -- the contract document's own "Why
   `source_context` is excluded" section gives the full reasoning a
   reviewer would need to independently re-verify or overturn it.
3. **Both preference readers emit an explicit dormant-feature disclosure
   constant (`feature_status = 'dormant_not_yet_enforced'`), confirmed
   against a repository-wide grep for any writer of either table.**
   `dbo.notification_preferences` has no writer anywhere (a real export
   legitimately returns zero rows for it); `dbo.connection_preferences`
   is auto-seeded, all-defaults, by `PS-PLAT-004`'s own backfill and
   `PS-AUTH-001`'s per-signup `usp_UpsertAppUserFromAuth` call, with no
   writer beyond that seed ever setting a non-default value. The label
   is a projection-truth statement about the FEATURE (no runtime path
   consults either table today), never stored member data -- this
   distinction is recorded explicitly in both the contract document and
   the adapter module's own docstring so a future reader does not
   mistake the constant for content needing its own privacy review. The
   consent reader carries no such label: a `dbo.user_consents` row, if
   one exists, is never an unconfigured default (the table has no
   `DEFAULT` on any of its three content columns), so labeling it
   dormant would be false. Pinned by dedicated tests on both sides
   (presence on the two preference readers' actual SQL text and decoded
   adapter output; absence, by name, from the consent reader's).
4. **A deliberate same-timestamp tie in the consent verification
   fixture.** `IX_user_consents_history (user_id, consent_code,
   recorded_at_utc DESC)` is confirmed, by reading `PS-PLAT-004`'s own
   DDL, to be a plain (non-unique) index -- `consent_code +
   recorded_at_utc` is not provably collision-free. Rather than merely
   arguing this from the DDL, the verification script's own fixture
   inserts owner A's accepted-then-withdrawn pair for one `consent_code`
   against the identical captured `recorded_at_utc` variable on purpose,
   exercising the reader's own trailing `user_consent_id` tiebreak
   against a real potential collision. Both rows are proven present and
   individually correct in the captured output.
5. **The consent reader includes every status, including `withdrawn`,
   for every consent code -- the central Paper 3 proof.** Confirmed
   against `CK_user_consents_status`'s own three-value vocabulary
   (`accepted`, `declined`, `withdrawn`) and
   `B0_PREFERENCES_CONSENTS_TAXONOMY_SCHEMA_FIT.md`'s own
   "withdrawn... is a new ledger event, never an update or deletion"
   rule. Pinned by a dedicated test and canary-proven in the
   verification script against a real accepted-then-withdrawn history.
6. **No third-party consent is read**, stated explicitly rather than
   merely true by omission: `dbo.recruiter_questions` is confirmed
   absent from every reader procedure body (a dedicated test) and from
   the verification script's executable body (a dedicated test scoped
   past the header comment's own explanatory mention of the table, via
   `scripts.migration_registry.executable_body`).
7. **Every reader's total `JOIN dbo.` count is exactly 1** -- the
   identity header's own join to `dbo.app_users`, with no content-level
   join at all, since none of the three claimed tables has a parent to
   join in this package's scope.

## Validation and self-review

- **This package's own test file**, run alone first:
  ```
  ANTHROPIC_API_KEY=placeholder "C:\Users\peter\Documents\portfolio\venv\Scripts\python.exe" -m pytest -q tests/test_settings_export_preferences_consent_reader.py
  ..............................................................                                                              [100%]
  62 passed, 453 subtests passed in 0.14s
  ```
  (Two real defects in the TEST FILE ITSELF were found and fixed during
  self-review before this clean run -- see "Real defects found and
  fixed" below; no defect was found in the shipped SQL or adapter
  Python.) This file (three test classes) pins: migration/rollback/
  verify file shape (single guarded batch, balanced parens/comments, no
  `\nGO`); THROW-number uniqueness within the forward and rollback files
  (59000-59099) and the verify file's own numbers confirmed inside its
  reserved 59100-59199 block, plus a repository-wide scan confirming no
  sibling `.sql` file anywhere under `SQL FIles/` reuses either range
  (highest prior use anywhere was 58953 before this package); exactly
  the three claimed procedures created and no table/trigger/index; never
  redefines another migration's procedure; the forward file's guard
  checks `PS-PLAT-004` and never `PS-AUTH-001`/any sibling
  `PS-SETTINGS-EXPORT-*`; no reader references `dbo.recruiter_questions`;
  every signature is exactly `@UserKey nvarchar(300)`; every procedure
  shares the byte-identical identity-resolution header, confirmed not
  merely within this file but **byte-identical across all six prior
  account-export forward migrations plus this package's own** (scanning
  `PS-SETTINGS-EXPORT-003` through `PS-SETTINGS-EXPORT-007` and this
  package's own file, asserting exactly one distinct header variant
  exists) -- the specific cross-file byte-consistency proof the writer
  brief named explicitly; every procedure filters by its own owner
  predicate (`user_id = @UserId`) and has a `JOIN dbo.` count of exactly
  1; deterministic `ORDER BY` present, checked precisely per reader
  (the connection-preference reader's own excluded `user_id`; the
  notification-preference reader's `notification_type`; the
  user-consent reader's `consent_code`, `recorded_at_utc`,
  `user_consent_id` in that position order); no `SELECT *`; every
  procedure returns the two read-window trailing columns with exactly
  two `SELECT` keywords; no procedure contains any transaction control,
  write, or nested `EXEC`; no procedure accepts a caller-selected
  owner/target parameter; no `GRANT`/role/user creation; forbidden
  fields (full-name sets) absent from every reader's actual output
  columns; **the one directive-category column (`evidence_json`, under
  `UNCONSTRAINED_EVIDENCE`) AND the one disclosed-but-non-directive
  column (`source_context`) are both a documented subset of the
  forbidden-field sets AND independently confirmed absent from every
  reader's actual output** (four separate tests, matching the "belt and
  suspenders" design this program's prior packages established); both
  preference readers' dormant-feature label is present in their actual
  SQL text and output columns, and confirmed absent from the consent
  reader's; `DOMAINS`' field-allowlist tuples equal the actual SQL
  output column list exactly, in order, for all three; the ledger
  description measured at 438 of 450 budgeted characters; the rollback
  drops exactly the three claimed procedures and removes only this
  migration's ledger row; the registry entry pins `requires` exactly
  (`["PS-AUTH-001", "PS-PLAT-004"]`) and, at authoring time, asserted
  `gate is None` with an explicit, pre-scripted lockstep docstring
  naming all five steps the manager's gate commit must take (modeled
  verbatim on the pre-gate version of `PS-SETTINGS-EXPORT-007`'s own
  placeholder test, recovered from that package's own pre-gate writer
  commit `b8e73d90` via `git show`, since every currently-merged sibling
  has since had its own placeholder replaced); the verify script
  provisions three synthetic owners including one deactivated, never
  commits, always reaches `ROLLBACK TRANSACTION;` before its report
  `SELECT`, invokes all three procedures via both a genuinely bare
  `EXEC` and an `INSERT ... EXEC`, and its fixture is confirmed (by
  dedicated tests) to actually write a real value into the one
  directive-excluded column and the one disclosed-unverified column, so
  the exclusion proof is genuine rather than vacuous, marks every
  consent evidence canary "must never be readable" (confirmed at least
  four such markers present), proves the connection-preferences
  auto-seed precondition (an `UPDATE`, never an `INSERT`, with a
  dedicated `@@ROWCOUNT` check), and proves the withdrawn-after-accepted
  consent history explicitly; adapter offline tests using fake cursors/
  connections confirm all three new domain functions are independently
  callable, decode every field correctly (including the
  notification-preference reader's quiet-hours pair and both preference
  readers' own dormant-feature label, and the consent reader's own
  absence of one), return empty rows (never an error) for an unresolved
  identity AND for `notification_preferences`' own legitimately-empty
  real-owner case (a dedicated test distinct from the generic
  unresolved-identity case), never call `commit`/`rollback`/`close` on
  the caller's connection, and bind `@UserKey` as a driver parameter;
  and the `DOMAINS` registry has exactly three domains flipped
  (`connection_preferences`, `notification_preferences`,
  `consent_history`, all EXISTING keys, scoped comparison) each with
  exactly one reader, and no reason string leaks a forbidden field name.
- **The full ten-file export battery** (this package's own file plus the
  nine existing export/reader/assembly/integration/migration files), run
  via pytest, output redirected to a file and its exit code read
  directly (never through a pipe):
  ```
  ANTHROPIC_API_KEY=placeholder "C:\Users\peter\Documents\portfolio\venv\Scripts\python.exe" -m pytest -q tests/test_settings_export_preferences_consent_reader.py tests/test_settings_export_media_transcript_reader.py tests/test_settings_export_oppslate_reader.py tests/test_settings_export_core_readers.py tests/test_settings_export_capture_moment_readers.py tests/test_settings_export_workshop_reader.py tests/test_settings_account_export_migration.py tests/test_account_export_assembly.py tests/test_account_export_storage.py tests/test_account_export_integration.py
  458 passed, 3385 subtests passed in 87.45s (0:01:27)
  PYTEST_EXIT_CODE_IS=0
  ```
  Clean on the first battery run against the finished candidate -- no
  sibling file needed any change beyond `tests/test_account_export_integration.py`'s
  own four snapshot constants (`EXPECTED_INCLUDED_DOMAIN_COUNT` 8->11,
  `EXPECTED_READER_COUNT` 27->30, `EXPECTED_NON_INCLUDED_DOMAIN_COUNT`
  22->19; `EXPECTED_TOTAL_DOMAIN_COUNT` stayed 30, since no domain KEY
  was added or removed), that file's own comment explicitly naming this
  as the expected, routine action every prior flip package has
  performed on this specific file.
- **Also run via `python -m unittest`** (the actual CI mechanism, not
  just pytest), same ten files, output redirected to a file and its exit
  code read directly:
  ```
  ANTHROPIC_API_KEY=placeholder "C:\Users\peter\Documents\portfolio\venv\Scripts\python.exe" -m unittest tests.test_settings_export_preferences_consent_reader tests.test_settings_export_media_transcript_reader tests.test_settings_export_oppslate_reader tests.test_settings_export_core_readers tests.test_settings_export_capture_moment_readers tests.test_settings_export_workshop_reader tests.test_settings_account_export_migration tests.test_account_export_assembly tests.test_account_export_storage tests.test_account_export_integration
  Ran 458 tests in 87.014s
  OK
  UNITTEST_EXIT_CODE_IS=0
  ```
  Confirms the suite's state is consistent under both runners.
- **A full collect-only pass of the entire repository test suite**
  (`pytest --collect-only -q tests/`): 1,655 tests collected, 95 errors,
  exit code 2. This sparse checkout materializes only a fraction of
  tracked files, and every one of the 95 collection errors is in a file
  this package never touched -- confirmed directly by grepping the
  `ERROR` lines specifically (not the full collected-test listing, which
  trivially contains this package's own test names) for any mention of
  `preferences_consent`, `account_export`, or `EXPORT-008`: zero matches.
  Per the writer brief's own guidance and this repository's own recorded
  precedent for this exact count (~95, matching `PS-SETTINGS-EXPORT-007`'s
  own report), this was noted honestly rather than chased, since none of
  it implicates this candidate.
- **`scripts/migration_registry.load_registry()`** (the registry's own
  offline, no-connection validator), invoked directly in Python: loads
  all 44 entries without error, `PS-SETTINGS-EXPORT-008`'s `requires`
  resolve to `('PS-AUTH-001', 'PS-PLAT-004')`, `gate` was `None` at
  authoring time, both the forward and rollback files resolve and exist,
  and `executable_sha256(forward)` computes cleanly
  (`b92a301e0d3616b3baedb1236eedea4d45a74430c84ad5e2e9b3adfde5eccd94`
  at authoring time; the same value is now the SEALED digest, pinned in
  "Gate state" below and in the replaced registry test -- the forward
  file never changed between authoring and the first-run seal).
- **Structural cross-validation beyond the shipped test file**, performed
  during authoring: a repository-wide Python scan confirmed the highest
  prior `THROW` number anywhere under `SQL FIles/` (before this package)
  was 58953, before claiming the `59000-59099`/`59100-59199` ranges, and
  a follow-up scan confirmed zero collisions after; a paren/comment
  balance check confirmed all three new `.sql` files end balanced
  (migration 108/108 parens, 4/4 comments; rollback 8/8 parens, 1/1
  comments; verify 226/226 parens, 8/8 comments); the registry's own
  `requires` ordering was confirmed against the actual migration array
  (`PS-AUTH-001` at index 8, `PS-PLAT-004` at index 4, this package's own
  entry appended last at index 43 of 44).
- **Real defects found and fixed during self-review, before the shipped
  test suite was finalized** (both in the NEW test file itself, not in
  the shipped SQL or adapter Python):
  1. `test_no_reader_references_recruiter_questions` initially checked
     `executable_body(self.forward)` as a whole, which correctly strips
     only the migration's own LEADING header comment -- but the
     migration's ledger-description string literal (part of the real
     `INSERT` statement, not a comment) also names `recruiter_questions`
     by design, to document the boundary explicitly in the registry
     (the identical "name the excluded table in the summary" precedent
     `PS-SETTINGS-EXPORT-004`'s own registry entry set for
     `target_entity_id`/`dbo.slate_entities`). The first-pass test
     therefore failed against CORRECT shipped SQL. Corrected by scoping
     the check to the three reader procedure bodies (`self.procedures`)
     specifically, where the table genuinely must never appear, rather
     than the whole executable text.
  2. The analogous `test_verify_never_references_recruiter_questions`
     initially checked the verify script's raw text as a whole, which
     also failed against the verify script's own header comment (which
     explains the "NO THIRD-PARTY CONSENT" boundary by naming the table)
     -- corrected identically, by scoping the check through
     `executable_body(self.verify)`, which correctly strips that
     single leading comment block (confirmed it is one continuous
     `/* ... */` spanning the mention) and leaves the real fixture/
     capture/assertion text, where the table is genuinely absent.

## Gate state

**Gate proof: SEALED -- first-run full pass** (manager, 2026-08-30, in
the same lockstep commit that writes this section -- registry + test +
report, the standing rule executed complete). The governed gate ran on
disposable `ps-migration-path-20260830-pc` (created for the proof,
deleted after): prerequisite chain replayed, forward apply created
exactly three reader procedures, idempotent re-apply changed nothing,
the isolation verification -- the first INSERT exercise of
`notification_preferences`' and `user_consents`' constraint sets
anywhere in this reader program -- executed and returned
`verified = 1`, the rollback rehearsed and the forward re-applied. The
proof is sealed in the registry with digest
`b92a301e0d3616b3baedb1236eedea4d45a74430c84ad5e2e9b3adfde5eccd94`
(`gated_at_utc 2026-08-30T09:36:34Z`), identical to the writer's
authoring-time computation (the forward file never changed). This same
commit replaced the pre-scripted placeholder test with
`test_registry_entry_pins_the_sealed_gate` implementing all five
prescribed steps (literal digest, recomputed-file check, three objects
with the `usp_ReadAccountExport` prefix, the exact verification
string). The writer's DEFAULT-vs-NULL fixture sweep -- the named lesson
from `PS-SETTINGS-EXPORT-007`'s own gate round -- held: no fixture
defect surfaced, making this the program's fourth first-run gate pass
in six gated reader packages.

The writer authored this candidate with `gate: null` and no database
access; earlier writer-voice passages saying so describe the authoring
state and this section records the sealed result.

Because this package touches three tables with **zero** prior gate
history of their own in this reader program (no reader before this one
has ever selected from `dbo.connection_preferences`, `dbo.
notification_preferences`, or `dbo.user_consents`), the manager's gate
run carried first-time proof weight for all three -- and has since
executed it: the run above was the first time any of their constraints
were actually exercised by an `INSERT` from this reader program. Two
were already known to be genuinely exercised in production
(`connection_preferences`'s auto-seed, `PS-PLAT-004`'s own original
platform verification script); `notification_preferences` and `user_
consents` had no prior `INSERT`/`UPDATE` proof anywhere this writer
could find, so their `CHECK` constraints (`CK_notification_preferences_quiet_pair`,
`CK_user_consents_status`, `CK_user_consents_evidence`) were genuinely
exercised by a real engine for the first time during the sealed
first-run pass recorded above.

## Independent-review correction round (manager, 2026-08-30)

The independent review of candidate `8913ca55` returned **PASS** with
four LOW documentation/test-fidelity findings, none blocking and none
touching the sealed digest's inputs. The reviewer independently
reproduced every gate fact (digest recomputed offline; forward file
proven single-commit and byte-identical to HEAD), audited every column
of all three tables against the DDL (included ⊎ excluded = the DDL
exactly), verified exactly one identity-header variant across all 30
program readers, closed the adversarial identity question negative (an
app_user without an active member_profile is not reachable — signup
creates both atomically and no deactivation path exists), confirmed the
dormant label truthful over the full tracked tree (no runtime path
reads either preferences table), and **independently ruled the
`source_context` exclusion CORRECT** ("a disclosure decision should be
made against real content, not a column name"), endorsing its
provisional shape and re-judgment trigger. Ten of eleven mutation
probes were caught offline; the eleventh (deleting a verify-fixture
INSERT post-seal) is catchable only by a gate re-run — a disclosed
program-wide property of unpinned verification scripts, moot here
because the verify file has one commit, unchanged since the gate.

The four findings, corrected in this round in one commit:

1. **F1:** the legitimately-empty notification-preferences test modeled
   the description-less unresolved-identity cursor shape, so it
   duplicated the adjacent test instead of exercising the
   resolved-owner-with-empty-table shape the contract claimed. It now
   drives the adapter with a real nine-column description and zero
   rows; the contract paragraph records the correction.
2. **F2:** the gate narrative's tally corrected — fourth first-run pass
   in SIX gated reader packages, not five.
3. **F3:** five stale or off-by-a-few line counts in the changed-paths
   list corrected (the registry and test-file counts had been
   invalidated by this manager's own gate commit; three others were
   writer-side miscounts).
4. **F4:** three pre-gate passages sitting after the rewritten Gate
   state section (first-time-proof paragraph, database-contact bullet,
   static-proof limitation) were reconciled to the sealed truth — each
   had understated what was proven.

## Protected and release state

- **Independent review:** Required for this Protected package per the
  lane claim's own `review_requirement: "independent"` field and this
  program's own standing pattern; not yet performed. This report does
  not claim a review occurred.
- **Repository state:** Candidate on the claimed branch, to be pushed
  per the writer brief (writer pushes and stops; no PR, no merge).
- **Deployment/schema state:** Withheld entirely. No database was
  contacted by this writer or by any test -- every SQL assertion in this
  candidate is a static read of the committed `.sql` text (including via
  `scripts/migration_registry.load_registry()`, which itself opens no
  connection), and every Python adapter test uses a fake cursor/
  connection double. The only database contact in this package's whole
  history is the manager's governed gate run against its disposable
  throwaway (created for the proof, deleted after -- see "Gate state");
  no production or shared database was ever touched.
- **Least-privilege SQL grant:** Design documented only (see
  `CR7_ACCOUNT_EXPORT_PREFERENCES_CONSENT_READER.md`'s "Grant model"
  section, identical to every prior package's own recorded model).
  Nothing applied -- the governed apply identity holds `db_ddladmin`
  only and this migration contains no `GRANT` statement of any kind.
- **Current product truth:** Account-wide export remains unavailable
  today. This candidate adds three more read-only reader procedures and
  three more adapter functions that nothing calls yet. No member-visible
  behavior changed. Connections, Notifications, and Consent themselves
  are unaffected by and unrelated to this package (this package never
  writes to any of the three tables it reads, or to any of `PS-PLAT-004`'s
  five sibling tables).

## Limitations, rollback, and next action

- **No live database proof of any kind from this writer.** Every SQL
  assertion in this candidate is a static text read; every Python test
  uses a fake cursor. All three procedures' actual runtime correctness
  against a real SQL Server engine -- including every `CHECK`/`FOREIGN
  KEY` constraint the verification script's fixture data must clear, two
  of which (`notification_preferences`, `user_consents`) had no prior
  `INSERT`/`UPDATE` proof anywhere in this reader program -- was
  unproven until the manager's gate run executed it (first-run full
  pass; see "Gate state" above).
- **Gate proof: SEALED.** See "Gate state" above.
- **No reader is wired to anything.** Nothing in this candidate connects
  a domain reader to any worker or route; `services/
  account_export_domain_readers.py`'s three new functions exist and are
  fully tested offline, but nothing calls them yet.
- **`source_context`'s exclusion is provisional by its own stated
  nature.** It rests on the current absence of any writer to `dbo.
  user_consents`; the moment a future package adds one, this column
  should be re-judged against that writer's actual procedure body,
  exactly as this program's own "trace actual writes" discipline
  requires. Disclosed as a deliberate, re-judgeable choice under "Design
  decisions" item 2 above and the contract document's own "Why
  `source_context` is excluded" section, not a settled permanent
  boundary.
- **No sibling test file needed a surface extension this time.** A
  repository-wide grep for this package's three domain names and
  `user_consents` across every file under `tests/` found no pin on any
  of them as excluded anywhere outside this package's own two claimed
  test surfaces (`tests/test_settings_export_preferences_consent_reader.py`,
  new, and `tests/test_account_export_integration.py`, modified).
  Unlike `PS-SETTINGS-EXPORT-007`'s own `voice_photo` tripwire, this
  candidate required no manager-side repoint.
- **Deviations from the brief:** None. Every deliverable path the brief
  names (migration, rollback, registry entry, verification script,
  adapter update, this package's own test file, both docs, and the
  explicitly-claimed `tests/test_account_export_integration.py`) was
  created or modified at its exact claimed location; no other unclaimed
  path was touched, confirmed by `git status --short` before staging.
  The dormant-feature label's exact wording and `source_context`'s
  exclusion were both judgment calls the brief explicitly left open, not
  deviations from an explicit instruction -- see "Design decisions"
  items 2-3 above and the contract document's own reasoning for each.
- **THROW ranges claimed:** `59000-59099` for the forward/rollback pair
  (forward uses 59000-59007; rollback continues at 59008) and
  `59100-59199` for the verification script (59100-59152 actually used).
  Both ranges were selected after a repository-wide scan (via a small
  Python script over every `.sql` file under `SQL FIles/`) confirmed the
  highest THROW number anywhere in the repository, before this package,
  was 58953 (`PS-SETTINGS-EXPORT-007_media_transcript_reader_isolation_verify.sql`).
  No other `.sql` file under `SQL FIles/` was found to reuse either
  reserved range (asserted by a dedicated repository-wide test).
- **What the manager's gate and any future package must know:**
  - The gate-pin lockstep PRE-SCRIPTED by this writer (matching the
    recovered pre-gate text of `PS-SETTINGS-EXPORT-007`'s own
    placeholder, via `git show b8e73d90`) has since been EXECUTED
    exactly as scripted: one commit updated the registry's `gate`
    block, replaced the placeholder with
    `test_registry_entry_pins_the_sealed_gate`, and rewrote this
    report's "Gate state" section together -- first-run full pass, see
    "Gate state" above.
  - `services/account_export_domain_readers.py`'s `DOMAINS` registry now
    has eleven included domains totalling thirty readers (ten from
    package 1, six from package 2, two from package 3, four from package
    4, five from package 6, and three from this package -- twenty-seven
    plus this package's three). `connection_preferences`,
    `notification_preferences`, and `consent_history` are EXISTING keys
    flipped to `included`, not new keys -- a future package should not
    expect to find "new domain" diffs here.
  - `notification_preferences` legitimately returns zero rows for every
    member today, and `connection_preferences` legitimately returns
    exactly one all-defaults row for every member today -- both facts
    disclosed via the `feature_status` dormant-feature label, not hidden
    behind a plain empty/default read. A future package that ever adds
    real enforcement to either table should retire that label for the
    newly-live table, not merely leave it in place.
  - `dbo.user_consents.source_context`'s exclusion should be the FIRST
    thing re-judged by whatever future package adds this table's first
    real writer -- see "Limitations" above.
