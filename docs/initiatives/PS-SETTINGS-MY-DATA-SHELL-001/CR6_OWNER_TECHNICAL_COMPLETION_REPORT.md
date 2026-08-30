# CR6 owner technical completion report

## Core record

- **Task/package and delivery path:**
  `PS-SETTINGS-ACCOUNT-EXPORT-MEDIA-TRANSCRIPT-READER-001`, Protected.
  Executes the owner's accepted "Paper 1" ruling: read-only, owner-scoped
  account-export readers for the member's own Voice/Photo capture facts
  and the member's own transcripts.
- **Outcome and candidate scope:** Read-only, owner-scoped account-export
  readers for the member's own Voice/Photo capture facts and OWN
  transcripts -- `dbo.voice_media_sources`, `dbo.voice_transcription_attempts`,
  `dbo.voice_capture_links`, `dbo.capture_media_sources`,
  `dbo.capture_media_links` -- as five `usp_ReadAccountExport<Table>ForOwner`
  procedures in one additive migration (`PS-SETTINGS-EXPORT-007`); a
  data-safe rollback; a registry entry authored with `gate: null` (no
  gate has been run by this writer -- see "Gate state" below;
  `requires: ["PS-AUTH-001", "PS-VOICE-001", "PS-CAPTURE-MEDIA-001"]`);
  an isolation-verification script whose fixtures satisfy every `NOT
  NULL`/`CHECK`/`FOREIGN KEY` constraint on all five touched tables and
  populate every directive-excluded and disclosed-machinery column with
  a real, genuinely-excluded canary value; updates to the shared
  `services/account_export_domain_readers.py` adapter (five new reader
  functions, `voice_photo` flipped from `excluded` to `included`); and
  offline tests pinning every field allowlist, every forbidden-field
  exclusion (including directive-category and machinery-category
  cross-checks), the owner predicate on every table of a three-level
  join chain, the deleted-row and in-flight-attempt exclusions, and
  every structural safety property. No table, trigger, index, container,
  worker wiring, route, or UI is added or changed. No schema apply,
  database connection, or Azure call was made by this writer.

  **The central finding of this package**, recorded in full in
  `CR6_ACCOUNT_EXPORT_MEDIA_TRANSCRIPT_READER.md`: this domain's own
  directive runs opposite to every prior package's -- the owner's ruling
  names `provider_transcript` as content that MUST be included, not
  trimmed. The judgment calls here are therefore about metadata
  classification (locator/digest/etag/machinery vs. plain member fact)
  and row-state settledness (deleted, in-flight) rather than
  third-party-content trimming. The single largest, most
  review-worthy judgment call is the "Transcript nuance" decision:
  `voice_transcription_attempts` is read only where `state IN
  ('succeeded', 'failed')` (every CONCLUDED attempt), excluding
  `queued`/`processing` rows, which carry no content column at all per
  `CK_voice_transcription_attempts_result`. A failed attempt still
  appears as a row -- only its `safe_error_code` is withheld. See
  "Design decisions" item 1 below for the full reasoning and the exact
  `CHECK` constraint evidence.

- **Package manager and writer:** Sole writer
  `agent:claude-code/settings-mt-reader-writer`, working only in the
  worktree
  `C:\Users\peter\Documents\PeerSlateWorktrees\PS-SETTINGS-ACCOUNT-EXPORT-MEDIA-TRANSCRIPT-READER-001`
  on branch
  `work/2026-08-30-settings-account-export-media-transcript-reader-001`.
  The lane claim's `surfaces` list is understood to name eleven paths per
  this program's own established pattern (matching every prior
  package); three of them (the claim JSON itself, its evidence file, and
  its receipts file) are reserved for the manager's gate/review stage
  and were never created or touched. This writer created six new files
  and modified two claimed files
  (`SQL FIles/Migrations/registry.json`,
  `services/account_export_domain_readers.py`), confirmed by `git status
  --short` before staging. **One additional file outside the claimed
  eight was modified** (`tests/test_account_export_integration.py`) --
  disclosed in full under "Deviations from the brief" below, not hidden.
- **Base SHA and branch:** Activated from `origin/main` at
  `5e091544aef6a0c81dffd08a892edb7da4a2243d` per the writer brief ("cut
  from main 5e091544"); worktree `HEAD` confirmed at exactly this SHA
  before any write (`git rev-parse HEAD`), matching the tip commit's own
  description ("Merge pull request 753 from
  work/2026-08-30-delivery-activation-settings-account-export-media-transcript-reader-001
  into main [skip ci]") -- the delivery-activation merge for this exact
  package, the identical "base main is the activation commit itself"
  pattern this program's prior packages recorded when their base was one
  commit after main rather than main directly.
- **Final SHA:** This report is authored, per the writer brief, **before**
  the final commit(s) exist on this branch -- it cannot record a final
  SHA it has not yet produced. The exact value is in the writer's
  chat-turn final message and in `git log` on the pushed branch, not in
  this file.
- **Candidate changed paths** (six new, three modified; nothing else in
  the worktree was touched -- confirmed by `git status --short` before
  staging):
  - `SQL FIles/Migrations/PS-SETTINGS-EXPORT-007_media_transcript_reader.sql` (new, 675 lines)
  - `SQL FIles/Migrations/PS-SETTINGS-EXPORT-007_media_transcript_reader_rollback.sql` (new, 46 lines)
  - `SQL FIles/Migrations/registry.json` (modified -- one entry appended, +12 lines)
  - `SQL FIles/Verification/PS-SETTINGS-EXPORT-007_media_transcript_reader_isolation_verify.sql` (new, 911 lines)
  - `services/account_export_domain_readers.py` (modified -- docstring addition, five new reader functions, `voice_photo` entry replaced; +113/-4 lines)
  - `tests/test_settings_export_media_transcript_reader.py` (new, 1119 lines)
  - `docs/initiatives/PS-SETTINGS-MY-DATA-SHELL-001/CR6_ACCOUNT_EXPORT_MEDIA_TRANSCRIPT_READER.md` (new, 553 lines)
  - `docs/initiatives/PS-SETTINGS-MY-DATA-SHELL-001/CR6_OWNER_TECHNICAL_COMPLETION_REPORT.md` (this file, new)
  - `tests/test_account_export_integration.py` (modified -- four snapshot constants bumped, +16/-12 lines; **not** in the claimed surfaces list -- see "Deviations from the brief")
- **Excluded actions and paths:**
  `docs/governance/lane_claims/PS-SETTINGS-ACCOUNT-EXPORT-MEDIA-TRANSCRIPT-READER-001.json`,
  its `evidence/*.md`, and its `receipts/*.json` were not created or
  modified -- reserved for the manager's gate/review stage.
  `tests/test_settings_export_core_readers.py`,
  `tests/test_settings_export_capture_moment_readers.py`,
  `tests/test_settings_export_workshop_reader.py`,
  `tests/test_settings_export_oppslate_reader.py`, and
  `tests/test_settings_account_export_migration.py` were run and are
  green, with exactly **one** known, pre-existing-package exception in
  `tests/test_settings_export_capture_moment_readers.py` -- disclosed
  fully under "Deviations from the brief" and "Limitations" below; it
  was NOT corrected by this writer because that file is not a claimed
  surface. No route, template, worker wiring, scheduler, container,
  workload identity, grant, `.env.example` entry, dependency, or
  production operation changed. No database connection, Azure call, or
  network call of any kind was made by this writer or by any test in
  this candidate. `git fetch` was not run by this writer (the branch was
  already cut from the activation commit per the writer brief).

## Design decisions worth the reviewer's attention

Full field-by-field reasoning lives in
`CR6_ACCOUNT_EXPORT_MEDIA_TRANSCRIPT_READER.md`; this section lists only
the decisions with the widest blast radius.

1. **Transcript nuance: only CONCLUDED attempts are read, and EVERY
   concluded one is, not merely the one linked to a confirmed capture.**
   `dbo.voice_transcription_attempts` is read where `state IN
   ('succeeded', 'failed')` only -- confirmed by `CK_voice_transcription_
   attempts_result`, which guarantees a `queued`/`processing` row has
   `provider_transcript`, `provider_request_id`, and `completed_at_utc`
   all `NULL`, i.e. no content exists there to export. This also reads
   as the only interpretation under which the brief's own instruction
   ("do not export failed-attempt error plumbing") is not vacuous: it
   only has force if failed rows are exported at all (which they are,
   minus `safe_error_code`). Every succeeded/failed attempt is exported,
   not narrowed to the one `dbo.voice_capture_links.successful_attempt_id`
   names, because a member may retry or record more than one successful
   attempt before confirming, and each is their own spoken words at that
   moment -- deliberately non-overlapping with `PS-SETTINGS-EXPORT-004`'s
   own `capture.body` (the confirmed, possibly-edited final text). This
   is the single decision in this package most likely to draw
   independent-review scrutiny, both because the brief's own phrasing
   ("every attempt's transcript or only completed/confirmed ones") is
   genuinely open to more than one reading and because it directly
   shapes this package's most content-bearing reader. Pinned by a
   dedicated test (`test_transcription_attempt_reader_reads_only_
   concluded_attempts`) and canary-proven in the verification script (a
   `processing` attempt is planted and proven absent while its sibling
   `succeeded`/`failed` attempts on the same source are proven present).
2. **`deletion_capture_row_version`'s MACHINERY classification required
   tracing actual procedure bodies, not just its name or type.**
   `PS-CAPTURE-MEDIA-001`'s own `usp_DeleteCapture` writes the PARENT
   CAPTURE's `row_version` into this column
   (`deletion_capture_row_version = @ExpectedRowVersion`); it names the
   capture's concurrency state, not the source row's own. This is
   exactly the "cleanup claim token" class the writer brief named by
   example, and is disclosed as an extension of this program's existing
   idempotency-ledger/machinery precedent
   (`PS-SETTINGS-EXPORT-006`'s `idempotency_key`), applied at column
   granularity to a second and third table.
3. **`capture_id` is excluded outright on both link tables, never
   resolved to `dbo.captures.capture_key`, even though every other
   ancestor-linkage column in this package IS resolved to an opaque
   key.** `dbo.captures` sits outside this package's declared five-table
   scope. The precedent cited is exact and direct:
   `PS-SETTINGS-EXPORT-004`'s own header drew the identical boundary for
   `dbo.moment_placements.target_entity_id`/`dbo.slate_entities`
   ("it does not point at one of this package's claimed tables... adds
   no dependency... precisely because it never reads that table"). This
   keeps `requires` to exactly `PS-VOICE-001`/`PS-CAPTURE-MEDIA-001`
   (plus `PS-AUTH-001` for the verification script), with no dependency
   on whatever migration creates `dbo.captures`.
4. **Every reader asserts the owner predicate on every table it joins,
   not merely the leaf** -- up to three tables for
   `usp_ReadAccountExportVoiceCaptureLinkForOwner` (`link`, `source`,
   `attempt`), all three independently carrying their own
   `owner_profile_id` (confirmed by DDL, not assumed).
5. **`voice_capture_links` and `capture_media_links` have no opaque key
   of their own** (unlike every other table in this package), matching
   `PS-SETTINGS-EXPORT-006`'s `opportunity_saved_qualifications`/
   `opportunity_saved_evidence` precedent. Their exported identifying
   tuple is the joined source's own `source_key` alone, already unique
   per `UQ_voice_capture_links_source`/`UQ_capture_media_links_source`.
6. **`deleted_at_utc` is excluded from every reader's output, but NOT
   used as the deletion filter predicate** -- `state <> 'deleted'` is
   used instead, on every reader (including both link readers and the
   attempt reader, through their own joined source). Both are
   `CHECK`-correlated by `CK_voice_media_sources_live_payload`/
   `CK_capture_media_sources_original_payload`, so either signal is
   logically sufficient; `state` was chosen as the more self-documenting
   column, consistent with this package's own extensive discussion of
   lifecycle-state truth elsewhere. `deleted_at_utc` itself is excluded
   because it is always `NULL` for any row a state-filtered reader
   returns -- dead weight, not a disclosure risk, disclosed as its own
   reasoning class distinct from the four directive categories.
7. **`source_type = 'photo'` is asserted as an explicit predicate on
   both Photo readers**, even though `CK_capture_media_sources_type`
   hard-locks every row to `'photo'` today -- the identical
   never-trust-the-default discipline `PS-SETTINGS-EXPORT-006` applied
   to `opportunity_slates.visibility`.
8. **The deleted-source-linked-to-a-link-row scenario is defended
   structurally (the join predicate is present and correct on both link
   readers) but not separately fixture-proven** in the verification
   script -- disclosed as an honest limitation under "Limitations"
   below, not a silent gap. The schema's own deletion-guard invariant
   (`usp_FinalizeVoiceDraftDeletion`/`usp_FinalizePhotoDraftDeletion`
   both require no link row exists before a source may reach `deleted`)
   makes the scenario unreachable through any real application code
   path.

## Validation and self-review

- **This package's own test file**, run alone first:
  ```
  ANTHROPIC_API_KEY=placeholder "C:\Users\peter\Documents\portfolio\venv\Scripts\python.exe" -m pytest -q tests/test_settings_export_media_transcript_reader.py
  ...............................................................                                                 [100%]
  63 passed, 537 subtests passed in 0.13s
  PYTEST_EXIT_CODE_IS=0
  ```
  (One real defect was found and fixed before this clean run reached
  63/537 -- see "Real defects found and fixed" below.)
  This file (69 test methods across three classes) pins: migration/
  rollback/verify file shape (single guarded batch, balanced
  parens/comments, no `\nGO`); THROW-number uniqueness within the
  forward and rollback files (58800-58899) and the verify file's own
  numbers confirmed inside its reserved 58900-58999 block, plus a
  repository-wide scan confirming no sibling `.sql` file anywhere under
  `SQL FIles/` reuses either range (highest prior use anywhere was 58753
  before this package); exactly the five claimed procedures created and
  no table/trigger/index; never redefines another migration's procedure;
  the forward file's guards check exactly `PS-VOICE-001`/
  `PS-CAPTURE-MEDIA-001` and never `PS-AUTH-001`/`PS-CAPTURE-001`/
  `PS-CAPTURE-002`/`PS-MOMENT-001`/`PS-PLACEMENT-001`/any sibling
  `PS-SETTINGS-EXPORT-*`; **no reader references `dbo.captures`**, the
  out-of-scope table, asserted directly against every procedure body;
  every signature is exactly `@UserKey nvarchar(300)`; every procedure
  shares the byte-identical identity-resolution header, confirmed not
  merely within this file but **byte-identical across all five prior
  account-export forward migrations in the program**
  (`test_identity_header_is_byte_identical_across_every_account_export_
  reader_in_the_program`, scanning `PS-SETTINGS-EXPORT-003` through this
  package's own file and asserting exactly one distinct header variant
  exists) -- the specific cross-file byte-consistency proof the writer
  brief named explicitly; every procedure filters by every owner
  predicate its own chain depth needs (1/2/3/1/2 respectively) and
  asserts the `state <> 'deleted'` predicate (all five) and the
  `source_type = 'photo'` predicate (both Photo readers only, confirmed
  ABSENT from all three Voice readers); the transcription-attempt
  reader's `state IN ('succeeded', 'failed')` predicate is present and
  neither `'queued'` nor `'processing'` appears anywhere in its body;
  join counts match chain depth exactly, and every descendant reader
  joins every ancestor by its exact aliased name; deterministic
  `ORDER BY` present with parent-then-sequence grouping checked
  precisely via position comparison; no `SELECT *`; every procedure
  returns the two read-window trailing columns with exactly two
  `SELECT` keywords; no procedure contains any transaction control,
  write, or nested `EXEC`; no procedure accepts a caller-selected
  owner/target parameter; no `GRANT`/role/user creation; forbidden
  fields (full-name sets) absent from every reader's actual output
  columns; **every directive-category column (STORAGE_LOCATOR,
  CONTENT_DIGEST, STORAGE_ETAG, PROVIDER_REFERENCE) AND every disclosed
  MACHINERY column (safe_error_code, scan_result, scan_completed_at_utc,
  deletion_capture_row_version) is both a documented subset of the
  forbidden-field sets AND independently confirmed absent from every
  reader's actual output** (four separate tests, matching the "belt and
  suspenders" design this program's prior packages established);
  `DOMAINS`' field-allowlist tuples equal the actual SQL output column
  list exactly, in order, for all five; the ledger description measured
  at 427 of 450 budgeted characters; the rollback drops exactly the five
  procedures and removes only this migration's ledger row; the registry
  entry pins `requires` exactly and, at authoring time, asserted `gate is
  None` with an explicit, pre-scripted lockstep docstring naming all
  five steps the manager's gate commit must take (modeled verbatim on
  the pre-gate version of `PS-SETTINGS-EXPORT-006`'s own placeholder
  test, recovered from that package's pre-gate commit `73cd267a` via
  `git show` since every currently-merged sibling has since had its own
  placeholder replaced; that placeholder has itself since been replaced
  by `test_registry_entry_pins_the_sealed_gate` in the gate commit,
  exactly as scripted -- see "Gate state" below); the verify script
  provisions three synthetic
  owners including one deactivated, never commits, always reaches
  `ROLLBACK TRANSACTION;` before its report `SELECT`, invokes all five
  procedures via both a genuinely bare `EXEC` and an `INSERT ... EXEC`,
  and its fixture is confirmed (by a dedicated test) to actually write a
  real value into every directive-excluded AND every disclosed-machinery
  column, so the exclusion proof is genuine rather than vacuous, plus
  dedicated assertions that the deleted-row and in-flight-attempt
  exclusion proofs are actually present in the script's own text; adapter
  offline tests using fake cursors/connections confirm all five new
  domain functions are independently callable, decode parent-linkage
  keys correctly at every chain depth, return empty rows (never an
  error) for an unresolved identity, never call `commit`/`rollback`/
  `close` on the caller's connection, and bind `@UserKey` as a driver
  parameter; and the `DOMAINS` registry has exactly one new included
  domain (`voice_photo`, an EXISTING key flipped from `excluded`, scoped
  comparison) with exactly five readers in source order, and no reason
  string leaks a forbidden field name.
- **The full nine-file export battery** (this package's own file plus
  the eight existing export/reader/assembly/integration/migration
  files), run via pytest, output redirected to a file and its exit code
  read directly (never through a pipe):
  ```
  ANTHROPIC_API_KEY=placeholder "C:\Users\peter\Documents\portfolio\venv\Scripts\python.exe" -m pytest -q tests/test_settings_export_media_transcript_reader.py tests/test_settings_export_oppslate_reader.py tests/test_settings_export_core_readers.py tests/test_settings_export_capture_moment_readers.py tests/test_settings_export_workshop_reader.py tests/test_settings_account_export_migration.py tests/test_account_export_assembly.py tests/test_account_export_storage.py tests/test_account_export_integration.py
  ........................................................................ [ 18%]
  ...........................................................................................................................................F................. [ 57%]
  ........................ [ 63%]
  ..................................... [ 73%]
  ................................................................................. [ 93%]
  .........................                            [100%]
  1 failed, 395 passed, 2889 subtests passed in 90.08s (0:01:30)
  ```
  The **one** failure is
  `tests/test_settings_export_capture_moment_readers.py::DomainsRegistryTests::test_voice_photo_is_excluded_with_a_stable_corrected_reason`
  -- a pre-existing sibling test (owned by the already-merged
  `PS-SETTINGS-ACCOUNT-EXPORT-CAPTURE-MOMENT-READERS-001` package, not
  then a claimed surface of this package) asserting `voice_photo` stays
  `"excluded"`. This is the DIRECT, INTENDED, brief-mandated consequence
  of flipping `voice_photo` to `"included"` -- not a defect this writer
  introduced. See "Deviations from the brief" and "Limitations" below
  for why it was disclosed and flagged rather than corrected directly.
  (Since resolved: the manager extended the claim to that file and
  repointed the pin; the identical nine-file battery now passes clean --
  `396 passed, 2889 subtests passed`, exit 0, re-run after the repoint
  and again after the gate-round fixture fix, both green under both
  runners.)
  Before this run, `tests/test_account_export_integration.py`'s own
  four snapshot constants (`EXPECTED_INCLUDED_DOMAIN_COUNT`,
  `EXPECTED_READER_COUNT`, `EXPECTED_NON_INCLUDED_DOMAIN_COUNT`) were
  updated 7->8, 22->27, 23->22 respectively
  (`EXPECTED_TOTAL_DOMAIN_COUNT` stayed 30, since no domain KEY was
  added or removed) -- that file's own comment explicitly names this as
  the expected, routine action "exactly as CR2/CR3/CR4 each did," so
  four additional failures in that file are already corrected in this
  run, not merely disclosed.
- **Also run via `python -m unittest`** (the actual CI mechanism, not
  just pytest), same nine files, output redirected to a file and its
  exit code read directly: at writer time `Ran 396 tests ... FAILED
  (failures=1)` -- the identical single known failure, confirming the
  suite's state was consistent under both runners. After the manager's
  tripwire repoint and the gate-round fixture fix: `Ran 396 tests ...
  OK`, exit 0, and pytest `396 passed, 2889 subtests passed`, exit 0 --
  both runners green on the sealed candidate.
- **A full collect-only pass of the entire repository test suite**
  (`pytest --collect-only -q tests/`): 1,593 tests collected, 95 errors,
  exit code 2. This sparse checkout materializes only 20% of tracked
  files (`git status` states this explicitly), and every one of the 95
  collection errors is in a file this package never touched (workshop,
  opportunity-slate, journal, profile, and other unrelated feature-area
  test files failing to import missing modules the sparse checkout does
  not materialize) -- confirmed directly by grepping the error list for
  this package's own five changed/added test-adjacent files
  (`account_export_domain_readers`, `media_transcript`,
  `account_export_integration`, `capture_moment_readers`) and finding
  zero matches among the `ERROR` lines. Per the writer brief's own
  guidance ("expect a handful of pre-existing unrelated collection
  errors... note, don't chase"), this count (95, more than a literal
  "handful") is noted here honestly rather than minimized, and was not
  further investigated since none of it implicates this candidate.
- **`scripts/migration_registry.load_registry()`** (the registry's own
  offline, no-connection validator), invoked directly in Python: loads
  all 43 entries without error, `PS-SETTINGS-EXPORT-007`'s `requires`
  resolve to `('PS-AUTH-001', 'PS-VOICE-001', 'PS-CAPTURE-MEDIA-001')`,
  `gate` was `None` at authoring time, both the forward and rollback
  files resolve and exist, and `executable_sha256(forward)` computes
  cleanly (`14d21bd2f4e1d88829d75cedb76b3c39ad63d80e104468c159dff3e1222c35a5`
  at authoring time; the same value is now the SEALED digest, pinned in
  "Gate state" below and in the replaced registry test -- the forward
  file never changed between authoring and the seal, because the gate
  round's one fix was fixture-only, in the verification script).
- **Structural cross-validation beyond the shipped test file**, performed
  during authoring: a Python pass extracted and decoded all five
  `EXEC(N'...');` dynamic-SQL batches (properly unescaping `''`) and
  confirmed each decoded procedure body contains exactly two `SELECT`
  keywords and the expected `JOIN dbo.` count matching the extracted
  column list; a comment-aware paren-balance and string-literal-balance
  scan (correctly skipping `/* ... */` blocks and treating `--` as a
  line comment only outside both an open string literal and an open
  block comment) confirmed all three `.sql` files in this candidate end
  balanced; a THROW-number scan across every `.sql` file under
  `SQL FIles/` confirmed the highest prior number anywhere was 58753
  before claiming the 58800-58899/58900-58999 ranges, and confirmed zero
  collisions after; every canary blob-name/derivative-blob-name pair
  used in the verification script's fixture was computed and
  length-checked in Python before being embedded as a SQL literal
  (`photo/v1/<35-char fill>.jpg` = 48 chars,
  `photo/v1/<35-char fill>-preview.jpg` = 56 chars, matching
  `CK_capture_media_sources_original_payload`'s exact length and
  derivation requirements) rather than hand-counted.
- **Real defects found and fixed during self-review, before the shipped
  test suite was finalized:**
  1. A naive, non-comment-aware paren-balance scan run against the
     forward migration file's raw text reported a mismatch (173 open vs.
     172 close). A comment-aware re-scan (correctly skipping `/* ... */`
     blocks) showed the file was actually balanced overall but pinpointed
     the true defect precisely: the READER 2 mini-header comment
     ("`READER 2: dbo.voice_transcription_attempts (8 content columns,
     plus the joined parent's source_key for linkage; owner predicate on
     both tables; ...`") opened a parenthetical after "8 content
     columns," that was never closed -- the identical class of defect
     `PS-SETTINGS-EXPORT-006`'s own self-review caught in its own
     `opportunity_saved_evidence` reader comment. Corrected by closing
     the parenthetical immediately after the intended phrase
     ("... for linkage).") and restructuring the remainder of the
     sentence; re-verified balanced (173/173) and the full test suite
     re-run clean afterward.
  2. The first-pass naive (non-comment-aware) balance scanner itself
     produced a MISLEADING "ends inside an open string literal" result
     for all three `.sql` files, purely because it did not know how to
     skip `/* ... */` block comments before applying single-quote
     toggle-state logic -- prose apostrophes and doubled quotes inside
     the long header comments were being misread as string-literal
     boundaries. A second, comment-aware scanner (tracking block-comment
     state before applying string-literal logic) confirmed all three
     files end cleanly outside any open string or comment. Recorded here
     as a lesson about writing verification tooling, matching
     `PS-SETTINGS-EXPORT-006`'s own recorded lesson about an analogous
     false positive in its own diagnostic script -- not a defect in the
     shipped SQL.

## Gate state

**Gate proof: SEALED -- two runs, the first FAILED by the engine
exactly as the gate exists to do, the second a full pass and the
standing seal.**

- **Run 1 (manager, 2026-08-30, FAILED at the verification step)** on
  disposable `ps-migration-path-20260830-mt` (deleted after):
  prerequisite chain replayed (15 migrations), forward apply created
  exactly five reader procedures, idempotent re-apply changed nothing --
  then the isolation verification's fixture violated
  `CK_capture_media_sources_original_payload`. Root cause, found by
  reading the applied DDL: `capture_media_sources.scan_result` carries
  `DEFAULT N'unknown'`, so the two deleted-state photo fixture rows that
  OMITTED the column received `'unknown'` instead of `NULL`, and the
  CHECK's deleted branch demands `NULL`. This is an engine-only defect
  class -- the writer's static constraint trace correctly read "omitted
  column" as NULL and could not see the DEFAULT fire -- and it is the
  first fixture defect any gate run has caught in this reader program.
  Fix: fixture-only, two INSERTs now name `scan_result` with an explicit
  `NULL` (commented in place). The forward migration was untouched, so
  the executable digest is identical across both runs.
- **Run 2 (manager, 2026-08-30, full pass; the standing seal)** on fresh
  disposable `ps-migration-path-20260830-mt2` (recreated per the
  clean-run rule, deleted after): the complete sequence -- prerequisites,
  forward apply (five objects), idempotent re-apply, isolation
  verification `verified = 1`, rollback rehearsed, forward re-applied.
  Sealed as digest
  `14d21bd2f4e1d88829d75cedb76b3c39ad63d80e104468c159dff3e1222c35a5`,
  `gated_at_utc: 2026-08-30T07:49:34Z`. The same commit replaced the
  pre-scripted placeholder test with
  `test_registry_entry_pins_the_sealed_gate` (literal digest,
  recomputed-file check, five objects with the shared
  `usp_ReadAccountExport` prefix, the exact verification string) and
  rewrote this section -- the "registry + test + report" lockstep this
  entire program has followed since `PS-SETTINGS-EXPORT-004`'s own
  independent-review round first established it as a standing rule.

The writer authored this candidate with `gate: null` and no database
access; earlier writer-voice passages saying so describe the authoring
state and this section records the sealed result.

Because this package's fixture is unusually broad (two independent
source-table families, a three-level join on the deepest reader, and
canary coverage for both the four directive categories and four
disclosed machinery columns, all hand-traced against
`PS-VOICE-001_voice_capture.sql`/`PS-CAPTURE-MEDIA-001_photo_sources.sql`
rather than run against an engine), the manager's gate run carries the
same first-time proof weight `PS-SETTINGS-EXPORT-006`'s own report noted
for its own package: this is the first time any of these five tables'
constraints will actually be exercised by an `INSERT` anywhere in this
reader program.

## Independent-review correction round (manager, 2026-08-30)

The independent review of candidate `d615dc43` returned **CONDITIONAL**:
no defect in any executable content — the allowlists audited
column-by-column and found complete and exact, the transcript judgment
re-derived from the schema and confirmed airtight (every transcript
that exists is exported; hard-DELETE on finalized deletions means no
orphan hides behind the deleted filter), the gate story independently
reproduced (including a five-table sweep confirming `scan_result` is
the ONLY column whose DEFAULT collides with a CHECK-required NULL),
scope exact, THROW ranges collision-free, and all ten mutation probes
behaved as expected. Three documentation-prose findings were corrected
in this round, in one commit, with NO executable change and therefore
NO re-gate (the reviewer's own probe verified header-prose edits leave
the sealed digest unchanged, and the replaced registry test's
recomputation check proves it again on every run):

1. **F1 (MEDIUM):** the migration header, this report, and the contract
   claimed a member "can already" correlate a voice/photo source to its
   Capture through EXPORT-004's capture reader. False — the two
   domains' outputs share no field. All three passages now state the
   truth: the cross-domain identity is DEFERRED, matching the
   EXPORT-004 `target_entity_id` precedent's careful wording, and
   adding it is a future package's own reviewed decision.
2. **F2 (LOW):** "never the same string" (raw transcript vs confirmed
   Capture body) was literally false — a member who accepts the
   transcript verbatim produces identical bytes. Both passages now say
   "a different fact, even when the characters coincide."
3. **F3 (LOW):** the voice-capture-links allowlist heading said "2
   content fields" above a three-field list; now "3."

## Protected and release state

- **Independent review:** Expected for a Protected package per this
  program's own standing pattern; not yet performed. This report does
  not claim a review occurred.
- **Repository state:** Candidate on the claimed branch, pushed per the
  writer brief (writer pushes and stops; no PR, no merge).
- **Deployment/schema state:** Withheld entirely. No database was
  contacted by this writer or by any test -- every SQL assertion in this
  candidate is a static read of the committed `.sql` text (including via
  `scripts/migration_registry.load_registry()`, which itself opens no
  connection), and every Python adapter test uses a fake cursor/
  connection double.
- **Least-privilege SQL grant:** Design documented only (see
  `CR6_ACCOUNT_EXPORT_MEDIA_TRANSCRIPT_READER.md`'s "Grant model"
  section, identical to every prior package's own recorded model).
  Nothing applied -- the governed apply identity holds `db_ddladmin`
  only and this migration contains no `GRANT` statement of any kind.
- **Current product truth:** Account-wide export remains unavailable
  today. This candidate adds five more read-only reader procedures and
  five more adapter functions that nothing calls yet. No member-visible
  behavior changed. Voice Capture and Photo Capture themselves are
  unaffected by and unrelated to this package (this package never writes
  to either domain's tables).

## Limitations, rollback, and next action

- **No live database proof of any kind from this writer.** Every SQL
  assertion in this candidate is a static text read; every Python test
  uses a fake cursor. All five procedures' actual runtime correctness
  against a real SQL Server engine -- including every hand-satisfied
  `CHECK`/`FOREIGN KEY` constraint the verification script's fixture data
  must clear -- was unproven until the manager's gate runs executed it
  (run 1 caught exactly one such hand-satisfied constraint being wrong;
  run 2 sealed -- see "Gate state" above).
- **Gate proof: SEALED.** See "Gate state" above.
- **No reader is wired to anything.** Nothing in this candidate connects
  a domain reader to any worker or route; `services/
  account_export_domain_readers.py`'s five new functions exist and are
  fully tested offline, but nothing calls them yet.
- **The deleted-source-linked-to-a-link-row scenario is defended but not
  fixture-proven.** Both link readers' `state <> 'deleted'` predicate on
  their joined source is present and structurally correct (asserted by
  a dedicated test), but no synthetic row bypassing the schema's own
  deletion-guard invariant was constructed to prove it in the
  verification script. Disclosed under "Design decisions" item 8 and
  "Interpretation notes" item 5 in the contract document.
- **One pre-existing sibling test went stale by design, was deliberately
  left unfixed by this writer, and has since been repointed by the
  manager under a governed surface extension.**
  `tests/test_settings_export_capture_moment_readers.py::DomainsRegistryTests::test_voice_photo_is_excluded_with_a_stable_corrected_reason`
  asserted `DOMAINS["voice_photo"]["disposition"] == "excluded"`, which
  this package's own mission (flip `voice_photo` to `"included"`) made
  false -- the cross-package tripwire firing exactly as designed. The
  writer correctly refused to touch the unclaimed file and flagged a
  follow-up instead. The manager then extended the claim (append-only,
  writer task context) to BOTH cross-package test files and repointed
  the pin to the new truth
  (`test_voice_photo_is_included_by_the_media_transcript_package`,
  asserting included / reason None / exactly five readers, with the pin's
  full history in its comment), restoring the nine-file battery to green
  in this candidate. The writer's flagged background task is thereby
  superseded.
- **Deviations from the brief:**
  1. **`tests/test_account_export_integration.py` was modified**, even
     though it is not in this package's claimed eight surfaces. Its own
     comment block explicitly names this exact action ("A future reader
     package legitimately changes these numbers -- exactly as CR2/CR3/CR4
     each did for their own package's own count in their own test
     files") as the routine, expected maintenance every prior package in
     this program has performed on this specific file. Four constants
     (`EXPECTED_INCLUDED_DOMAIN_COUNT` 7->8, `EXPECTED_READER_COUNT`
     22->27, `EXPECTED_NON_INCLUDED_DOMAIN_COUNT` 23->22,
     `EXPECTED_TOTAL_DOMAIN_COUNT` unchanged at 30) were updated, plus
     the explanatory comment. Not updating it would have left four
     additional, purely mechanical test failures for a change this
     program's own convention treats as routine per-package upkeep, not
     a narrative or scope decision.
  2. **`tests/test_settings_export_capture_moment_readers.py` was
     deliberately NOT modified**, despite carrying one now-stale,
     domain-specific assertion (see "Limitations" above) -- disclosed as
     a conscious choice to respect this package's explicit claimed-
     surfaces restriction over completing an all-green test run,
     because that file's own text carries no comparable self-invitation
     to be updated by a later package, unlike the integration file.
  3. **The transcript-nuance row filter
     (`state IN ('succeeded', 'failed')`) is a judgment call the writer
     brief left genuinely open**, not an explicit instruction followed
     to the letter -- see "Design decisions" item 1 above and
     `CR6_ACCOUNT_EXPORT_MEDIA_TRANSCRIPT_READER.md`'s "Transcript
     nuance" section for the full reasoning a reviewer would need to
     independently re-verify or overturn it.
  4. **No other deviation.** Every deliverable path the brief names
     (migration, rollback, registry entry, verification script, adapter
     update, this package's own test file, both docs) was created at its
     exact claimed location; no other unclaimed path was touched,
     confirmed by `git status --short` before staging.
- **THROW ranges claimed:** `58800-58899` for the forward/rollback pair
  (forward uses 58800-58811; rollback continues at 58812) and
  `58900-58999` for the verification script (58900-58953 actually used).
  Both ranges were selected after a repository-wide scan (via a small
  Python script over every `.sql` file under `SQL FIles/`) confirmed the
  highest THROW number anywhere in the repository, before this package,
  was 58753 (`PS-SETTINGS-EXPORT-006_oppslate_reader_isolation_verify.sql`).
  No other `.sql` file under `SQL FIles/` was found to reuse either
  reserved range (asserted by a dedicated repository-wide test).
- **What the manager's gate and any future package must know:**
  - The gate-pin lockstep PRE-SCRIPTED by this writer (matching the
    recovered pre-gate text of `PS-SETTINGS-EXPORT-006`'s own
    placeholder, via `git show 73cd267a`) has since been EXECUTED
    exactly as scripted: one commit updated the registry's `gate` block,
    replaced the placeholder with
    `test_registry_entry_pins_the_sealed_gate`, and rewrote this
    report's "Gate state" section -- after gate run 1 caught the
    fixture's DEFAULT-vs-NULL defect and run 2 sealed (see "Gate
    state") -- the standing "registry + test + report" rule this program
    has followed since `PS-SETTINGS-EXPORT-004`'s own independent-review
    round.
  - `services/account_export_domain_readers.py`'s `DOMAINS` registry now
    has eight included domains totalling twenty-seven readers (ten from
    package 1, six from package 2, two from package 3, four from
    package 4, and five from this package). `voice_photo` is an EXISTING
    key flipped to `included`, not a new key -- a future package should
    not expect to find a "new domain" diff here the way `opportunity_slate`
    was new content under an existing C0 row for `PS-SETTINGS-EXPORT-006`.
  - `tests/test_settings_export_capture_moment_readers.py`'s
    `voice_photo` pin was repointed to the included truth in this
    candidate under the extended claim (see "Limitations" above); the
    file is fully green again and the pin keeps guarding the CURRENT
    disposition against any future flip.
  - `dbo.captures` remains entirely unread by this package, by design,
    and the cross-domain source-to-Capture identity is DEFERRED
    (corrected in the independent-review round: reading EXPORT-004's
    `capture` domain output would NOT suffice -- the two domains'
    outputs share no field. A future package wanting that correlation
    must add an explicit cross-domain identity, its own reviewed
    decision, not extend this package's link readers or lean on any
    existing output).
