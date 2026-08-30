# CR8 owner technical completion report

## Core record

- **Task/package and delivery path:**
  `PS-SETTINGS-ACCOUNT-EXPORT-EVIDENCE-RULE-READER-001`, Protected. The
  CLOSING reader package of the 2026-08-29/2026-08-30 account-export
  reader topology. Executes the owner's accepted 2026-08-30 Papers 4-7
  rulings: adopts the safe-references-only evidence rule and applies it
  now to the one reader it unblocks (`dbo.career_skill_links`), and
  records four further durable rulings (`ai_proposals`, both
  publication-adjacent domains, `community_authored_content`) as
  updated `DOMAINS` reason strings.
- **Outcome and candidate scope:** A single read-only, owner-scoped
  account-export reader, `usp_ReadAccountExportCareerSkillLinkForOwner`,
  over `dbo.career_skill_links` in one additive migration
  (`PS-SETTINGS-EXPORT-009`); a data-safe rollback; a registry entry
  authored with `gate: null` (no gate has been run by this writer -- see
  "Gate state" below; `requires: ["PS-AUTH-001", "PS-PLAT-003",
  "PS-PLAT-006"]`); an isolation-verification script whose fixtures
  satisfy every `NOT NULL`/`CHECK`/`FOREIGN KEY` constraint on
  `dbo.career_skill_links`, `dbo.career_skills`, `dbo.slate_entities`,
  and `dbo.evidence_items`, and that actually soft-deletes a fixture
  skill mid-script to prove the joined soft-delete predicate is
  load-bearing, not merely present in the procedure text; updates to
  the shared `services/account_export_domain_readers.py` adapter (one
  new reader function, the EXISTING `career_skill_links` key flipped
  from `excluded` to `included`, and five `DOMAINS` reason strings
  updated to record the owner's remaining 2026-08-30 rulings); and
  offline tests pinning the field allowlist, the resolved `skill_key`
  linkage, the derived `evidence_linked` flag, both excluded references
  (`source_entity_id`, `evidence_item_id`), the owner predicate on both
  the link and the joined skill, a join count of exactly 2, the
  soft-delete back-door predicate, and the five updated ruling reason
  strings. No table, trigger, index, container, worker wiring, route, or
  UI is added or changed. No schema apply, database connection, or
  Azure call was made by this writer.

  **The central finding of this package**, recorded in full in
  `CR8_ACCOUNT_EXPORT_EVIDENCE_RULE_READER.md`: `evidence_item_id` is
  excluded outright (never resolved, never joined -- `dbo.evidence_items`
  is not a claimed table of this package), but a derived
  `evidence_linked` bit is disclosed instead, computed entirely from
  `career_skill_links`' own nullable column with no join and no
  `evidence_items` content read. This is the writer brief's own option
  (a) implemented literally: "a link row exports as 'a link to evidence
  exists, with these member-authored facts.'" `skill_id` is resolved to
  the already-included `career_skills` domain's own `skill_key` (the
  established `chapter_id -> chapter_key` intra-linkage idiom, applied
  here to a link table for the first time), while `source_entity_id` (a
  `dbo.slate_entities` reference) is excluded outright under this
  program's older, separate "never resolve an entity_id reference"
  convention -- a different, independent boundary from the evidence
  rule itself, classified accordingly in this package's own test file.
- **Package manager and writer:** Sole writer
  `agent:claude-code/settings-er-reader-writer`, working only in the
  worktree
  `C:\Users\peter\Documents\PeerSlateWorktrees\PS-SETTINGS-ACCOUNT-EXPORT-EVIDENCE-RULE-READER-001`
  on branch
  `work/2026-08-30-settings-account-export-evidence-rule-reader-001`.
  The lane claim's `surfaces` list names thirteen paths per this
  program's own established pattern; three of them (the claim JSON
  itself, its evidence file, and its receipts file) are reserved for
  the manager's gate/review stage and were never created or touched.
  This writer created six new files and modified four claimed files
  (`SQL FIles/Migrations/registry.json`, `services/account_export_domain_readers.py`,
  `tests/test_settings_export_core_readers.py`,
  `tests/test_account_export_integration.py`), confirmed by `git status
  --short` before staging.
- **Base SHA and branch:** Activated from `origin/main` at
  `17ca74ad02eb5780f038ba8016258b82404a0e94` per the writer brief ("cut
  from main 17ca74ad"); worktree `HEAD` confirmed at exactly this SHA
  before any write (`git rev-parse HEAD`), matching the tip commit's own
  description ("Merge pull request 765 from
  work/2026-08-30-delivery-activation-settings-account-export-evidence-rule-reader-001
  into main [skip ci]") -- the delivery-activation merge for this exact
  package. `python scripts/delivery_preflight.py --package
  PS-SETTINGS-ACCOUNT-EXPORT-EVIDENCE-RULE-READER-001 --intent write
  --fetch --require-clean --task-ref agent:claude-code/settings-er-reader-writer`
  returned `"result": "pass"` before any file was written, confirming
  the worktree's registry `task_ref` matched, the branch was clean, and
  `origin/main` matched `HEAD` exactly.
- **Final SHA:** This report is authored, per house convention, at the
  point every deliverable file is complete and self-reviewed but
  **before** the final commit(s) exist on this branch -- it cannot
  record a final SHA it has not yet produced. The exact value is in the
  writer's chat-turn final message and in `git log` on the pushed
  branch, not in this file.
- **Candidate changed paths** (six new, four modified; nothing else in
  the worktree was touched -- confirmed by `git status --short` before
  staging):
  - `SQL FIles/Migrations/PS-SETTINGS-EXPORT-009_evidence_rule_reader.sql` (new, 306 lines)
  - `SQL FIles/Migrations/PS-SETTINGS-EXPORT-009_evidence_rule_reader_rollback.sql` (new, 38 lines)
  - `SQL FIles/Migrations/registry.json` (modified -- one entry appended; +34/-0 lines after the manager's gate seal, +12 at writer time; figures on this list corrected in the independent-review round for the three files the gate commit touched)
  - `SQL FIles/Verification/PS-SETTINGS-EXPORT-009_evidence_rule_reader_isolation_verify.sql` (new, 542 lines after the gate-round scan sanction; 525 at writer time)
  - `services/account_export_domain_readers.py` (modified -- docstring addition, one new reader function, one `DOMAINS` entry flipped, five `DOMAINS` reasons updated, one stale comment cross-reference corrected; +107/-23 lines)
  - `tests/test_settings_export_evidence_rule_reader.py` (new, 1,034 lines after the manager's placeholder replacement; 1,051 at writer time)
  - `tests/test_settings_export_core_readers.py` (modified -- the `career_skill_links` tripwire repointed to the flipped truth, one comment cross-reference corrected; +19/-5 lines -- an explicitly claimed surface per the writer brief, "ONLY if it pins career_skill_links' excluded disposition or reason -- it likely does")
  - `tests/test_account_export_integration.py` (modified -- four snapshot constants bumped, one comment updated; +9/-6 lines -- an explicitly claimed surface per the writer brief)
  - `docs/initiatives/PS-SETTINGS-MY-DATA-SHELL-001/CR8_ACCOUNT_EXPORT_EVIDENCE_RULE_READER.md` (new, 368 lines)
  - `docs/initiatives/PS-SETTINGS-MY-DATA-SHELL-001/CR8_OWNER_TECHNICAL_COMPLETION_REPORT.md` (this file, new)
- **Excluded actions and paths:**
  `docs/governance/lane_claims/PS-SETTINGS-ACCOUNT-EXPORT-EVIDENCE-RULE-READER-001.json`,
  its `evidence/*.md`, and its `receipts/*.json` were not created or
  modified -- reserved for the manager's gate/review stage.
  `docs/governance/*` outside that pair was never touched. A
  repository-wide grep for `career_skill_links` across every file under
  `tests/` found four sibling files with a matching substring
  (`tests/test_settings_export_capture_moment_readers.py`,
  `tests/test_settings_export_media_transcript_reader.py`,
  `tests/test_settings_export_oppslate_reader.py`,
  `tests/test_settings_export_preferences_consent_reader.py`) -- every
  one, on inspection, was either (a) a prose comment naming
  `career_skill_links` while explaining an unrelated exclusion (no
  assertion touches it), or (b) each package's own
  `test_verify_never_references_unrelated_sibling_machinery_tables`-style
  sanity check, which asserts `career_skill_links` is absent from THAT
  package's OWN isolated verify-script text (`self.verify`) -- a check
  scoped entirely to that sibling file's own content, unaffected by
  this package's `DOMAINS` flip, and never touching global disposition
  state. A separate repository-wide grep for the four other updated
  domain keys (`ai_proposals`, `profile_publication_foundation`,
  `own_publication_versions`, `community_authored_content`,
  `file_evidence_metadata`) across every file under `tests/` found zero
  matches outside this package's own new test file. No sibling file
  needed a surface extension. No route,
  template, worker wiring, scheduler, container, workload identity,
  grant, `.env.example` entry, dependency, or production operation
  changed. No database connection, Azure call, or network call of any
  kind was made by this writer or by any test in this candidate. `git
  fetch` confirmed the worktree's `HEAD` already matched `origin/main`
  (the branch was cut from the activation commit per the writer brief).

## Design decisions worth the reviewer's attention

Full field-by-field reasoning lives in
`CR8_ACCOUNT_EXPORT_EVIDENCE_RULE_READER.md`; this section lists only
the decisions with the widest blast radius.

1. **`evidence_item_id` is excluded outright; a derived `evidence_linked`
   bit is disclosed instead, computed with no join and no
   `evidence_items` read of any kind.** The writer brief explicitly
   framed the choice and its own description of option (a) ("a link
   row exports as 'a link to evidence exists, with these
   member-authored facts'") is what this package implements literally.
   `dbo.evidence_items` is never one of this migration's claimed
   tables, was never joined, and is asserted absent from the procedure
   body by a dedicated test scanning the FULL body text (not merely the
   output column list) -- a stronger proof than a column-name grep,
   since it also rules out a join that selects nothing from the table.
   This is the single decision in this package most likely to draw
   independent-review scrutiny, because a reviewer could reasonably ask
   whether disclosing ANY derived signal about evidence linkage,
   however boolean, oversteps "safe references only" -- the contract
   document's own "Why this is safe" section gives the full reasoning a
   reviewer would need to independently re-verify or overturn it.
2. **`skill_id` is resolved to the already-included `career_skills`
   domain's own `skill_key`; `source_entity_id` is excluded outright and
   never resolved.** Both are foreign keys on the same claimed table,
   but classified oppositely because their targets differ in kind:
   `dbo.career_skills` already has its own included reader and its own
   established opaque key, so resolving to it is the same
   intra-export-linkage idiom `PS-SETTINGS-EXPORT-003` already
   established for `chapter_id -> chapter_key`; `dbo.slate_entities` is
   the polymorphic identity table this WHOLE program has never once
   resolved an `entity_id` reference to, anywhere, since
   `PS-SETTINGS-EXPORT-003`'s own header forbade it program-wide. Both
   are confirmed by reading `PS-PLAT-006`'s own DDL, not assumed.
3. **The joined `dbo.career_skills` row's own `deleted_at_utc IS NULL`
   predicate is load-bearing, proven by an actual soft-delete against a
   real engine, not merely asserted from the DDL.** `dbo.career_skill_links`
   itself has neither `deleted_at_utc` nor `row_version` (confirmed by
   reading its own DDL); without the joined predicate, a soft-deleted
   skill's link would still surface -- a back door this program's own
   established "extension content must not surface if its parent was
   soft-deleted" discipline (`PS-SETTINGS-EXPORT-003`'s own chapter-joined
   readers) already anticipates for exactly this shape of table. The
   verification script's own section 4 soft-deletes a real fixture
   skill mid-script and re-invokes the reader, proving the row count
   drops and the specific link disappears while sibling links and the
   other owner's fixture are untouched.
4. **This is the first ONE-reader package in this program**, so its
   structural verification-script checks (section 0/0b) are written
   directly against the single procedure rather than through the
   generic reader-name-loop table every multi-reader sibling package
   uses -- a loop that would only ever iterate once is pure overhead,
   not a missing generalization.
5. **`requires` conservatively names `PS-PLAT-003`** even though it is
   already a transitive ancestor of `PS-PLAT-006` (`006 -> 005 -> 004 ->
   003`, confirmed by reading the registry's own existing entries),
   because this package's own verification script inserts real rows
   into `dbo.evidence_items` (created by `PS-PLAT-003`) to satisfy
   `career_skill_links`' FK -- extending the identical "a registry-level
   requirement can cover the verification script's own direct
   dependency, not merely the migration body's guard checks" reasoning
   this program already uses for `PS-AUTH-001`.
6. **Five `DOMAINS` reason strings were updated, not four, because
   "publication domains" spans two existing keys with different
   dispositions.** `profile_publication_foundation` (`unavailable`,
   schema unapplied) and `own_publication_versions` (`excluded`, schema
   applied but genuinely unwritten) are both real, distinct entries;
   applying the owner's "nothing exists to export" ruling to only one
   would leave the other stale and inconsistent. Both were re-verified
   against the real schema rather than assumed: a repository-wide check
   confirmed `dbo.entity_publication_versions` and
   `dbo.entity_access_grants` (both created by the already-applied
   `PS-PLAT-002`) have no writer anywhere in this codebase, so "nothing
   exists to export" is factually accurate for `own_publication_versions`
   as an honestly-empty-table finding, not merely an unapplied-schema
   finding.

## Validation and self-review

- **This package's own test file**, run alone first:
  ```
  ANTHROPIC_API_KEY=placeholder "C:\Users\peter\Documents\portfolio\venv\Scripts\python.exe" -m pytest -q tests/test_settings_export_evidence_rule_reader.py
  .............................................. [ 73%]
  .................                                                                    [100%]
  63 passed, 446 subtests passed in 0.13s
  ```
  (One real defect was found and fixed during self-review before this
  clean run -- see "Real defects found and fixed" below; no defect was
  found in the shipped SQL or adapter Python.) This file (three test
  classes) pins: migration/rollback/verify file shape (single guarded
  batch, balanced parens/comments, no `\nGO`); THROW-number uniqueness
  within the forward and rollback files (59200-59299) and the verify
  file's own numbers confirmed inside its reserved 59300-59399 block,
  plus a repository-wide scan confirming no sibling `.sql` file anywhere
  under `SQL FIles/` reuses either range (highest prior use anywhere was
  59152); exactly the one claimed procedure created and no
  table/trigger/index; never redefines another migration's procedure;
  the forward file's guard checks `PS-PLAT-006` and never
  `PS-AUTH-001`/`PS-PLAT-003`/any sibling `PS-SETTINGS-EXPORT-*`; no
  reader references `dbo.recruiter_questions`; the signature is exactly
  `@UserKey nvarchar(300)`; the procedure shares the byte-identical
  identity-resolution header, confirmed not merely within this file but
  **byte-identical across all seven prior/current account-export forward
  migrations** (scanning `PS-SETTINGS-EXPORT-003` through
  `PS-SETTINGS-EXPORT-008` and this package's own file, asserting
  exactly one distinct header variant exists across 31 total readers);
  the owner predicate is present on both the link and the joined skill;
  the join count is exactly 2 (the identity header's own join plus the
  `career_skills` join); deterministic `ORDER BY` present and checked
  precisely (`link.created_at_utc` before `link.skill_link_id`); no
  `SELECT *`; the procedure returns the two read-window trailing columns
  with exactly two `SELECT` keywords; no transaction control, write, or
  nested `EXEC`; no caller-selected owner/target parameter; no
  `GRANT`/role/user creation; the full forbidden-field set (`skill_link_id`,
  `owner_profile_id`, `skill_id`, `source_entity_id`, `evidence_item_id`,
  `created_by_user_id`) is absent from the actual output columns; the
  resolved `skill_key` linkage is present and `career_skills`' own
  content columns (`skill_name`, `skill_summary`, `visibility`,
  `featured`, `display_order`) are confirmed absent (no double export);
  the `evidence_linked` flag is present in the output and its `CASE
  WHEN link.evidence_item_id IS NOT NULL` computation is confirmed in
  the procedure text; the `SAFE_REFERENCES_RULE` category
  (`evidence_item_id`) is both a documented subset of the forbidden-field
  set AND independently confirmed absent from the reader's actual
  output (belt and suspenders, matching this program's own established
  design); the procedure body is confirmed to never mention
  `dbo.slate_entities` or `dbo.evidence_items` anywhere at all, not
  merely in its output columns; `DOMAINS`' field-allowlist tuple equals
  the actual SQL output column list exactly, in order; `link.deleted_at_utc`/
  `link.row_version` are confirmed absent (the table has neither) and
  `skill.deleted_at_utc IS NULL` is confirmed present; the ledger
  description measured at 434 of 450 budgeted characters; the rollback
  drops exactly the one claimed procedure and removes only this
  migration's ledger row; the registry entry pins `requires` exactly
  (`["PS-AUTH-001", "PS-PLAT-003", "PS-PLAT-006"]`) and, at authoring
  time, asserted `gate is None` with an explicit, pre-scripted
  lockstep docstring naming all five steps the manager's gate commit
  must take (that placeholder has since been replaced by
  `test_registry_entry_pins_the_sealed_gate` in the gate commit,
  exactly as scripted -- see "Gate state" below; it was modeled
  verbatim on the pre-gate version of
  `PS-SETTINGS-EXPORT-008`'s own placeholder test, recovered from that
  package's own pre-gate writer commit `050eae05` via `git show`, since
  every currently-merged sibling has since had its own placeholder
  replaced); the verify script provisions three synthetic owners
  including one deactivated, never commits, always reaches `ROLLBACK
  TRANSACTION;` before its report `SELECT`, invokes the reader via both
  a genuinely bare `EXEC` and an `INSERT ... EXEC`, and its fixture is
  confirmed (by dedicated tests) to actually write real, captured
  values into every excluded column (`skill_link_id`, `owner_profile_id`,
  `skill_id`, `source_entity_id`, `evidence_item_id`,
  `created_by_user_id`) so the exclusion proof is genuine rather than
  vacuous, marks three evidence-item canaries "must never be readable,"
  proves a genuine `evidence_linked` true/false contrast against a real
  engine, and proves the soft-delete back door is closed by actually
  soft-deleting a fixture skill and re-invoking the reader; adapter
  offline tests using fake cursors/connections confirm the new domain
  function is independently callable, decodes every field correctly
  including both `evidence_linked` states, returns empty rows (never an
  error) for an unresolved identity AND for the table's own
  legitimately-empty real-owner case (the F1-lesson-modeled resolved-owner-
  with-a-real-description-and-zero-rows shape, distinct from the
  description-less unresolved-identity case), never calls
  `commit`/`rollback`/`close` on the caller's connection, and binds
  `@UserKey` as a driver parameter; and the `DOMAINS` registry has
  exactly one domain flipped (`career_skill_links`, an EXISTING key,
  scoped comparison) with exactly one reader, five updated ruling
  reasons each pinned by a dedicated test for its own 2026-08-30 date
  stamp and key phrase, and no reason string leaks a forbidden field
  name.
- **The full eleven-file export battery** (this package's own file plus
  the ten existing export/reader/assembly/integration/migration files),
  run via pytest, output redirected to a file and its exit code read
  directly (never through a pipe):
  ```
  ANTHROPIC_API_KEY=placeholder "C:\Users\peter\Documents\portfolio\venv\Scripts\python.exe" -m pytest -q tests/test_settings_export_evidence_rule_reader.py tests/test_settings_export_preferences_consent_reader.py tests/test_settings_export_media_transcript_reader.py tests/test_settings_export_oppslate_reader.py tests/test_settings_export_core_readers.py tests/test_settings_export_capture_moment_readers.py tests/test_settings_export_workshop_reader.py tests/test_settings_account_export_migration.py tests/test_account_export_assembly.py tests/test_account_export_storage.py tests/test_account_export_integration.py
  521 passed, 3860 subtests passed in 88.46s (0:01:28)
  PYTEST_EXIT_CODE_IS=0
  ```
  Clean after one self-review correction (see below) -- no sibling file
  needed any change beyond `tests/test_settings_export_core_readers.py`'s
  own repointed tripwire and `tests/test_account_export_integration.py`'s
  own four snapshot constants (`EXPECTED_INCLUDED_DOMAIN_COUNT` 11->12,
  `EXPECTED_READER_COUNT` 30->31, `EXPECTED_NON_INCLUDED_DOMAIN_COUNT`
  19->18; `EXPECTED_TOTAL_DOMAIN_COUNT` stayed 30, since no domain KEY
  was added or removed), both explicitly claimed surfaces per the
  writer brief.
- **Also run via `python -m unittest`** (the actual CI mechanism, not
  just pytest), same eleven files, output redirected to a file and its
  exit code read directly:
  ```
  ANTHROPIC_API_KEY=placeholder "C:\Users\peter\Documents\portfolio\venv\Scripts\python.exe" -m unittest tests.test_settings_export_evidence_rule_reader tests.test_settings_export_preferences_consent_reader tests.test_settings_export_media_transcript_reader tests.test_settings_export_oppslate_reader tests.test_settings_export_core_readers tests.test_settings_export_capture_moment_readers tests.test_settings_export_workshop_reader tests.test_settings_account_export_migration tests.test_account_export_assembly tests.test_account_export_storage tests.test_account_export_integration
  Ran 521 tests in 92.593s
  OK
  UNITTEST_EXIT_CODE_IS=0
  ```
  Confirms the suite's state is consistent under both runners.
- **A full collect-only pass of the entire repository test suite**
  (`pytest --collect-only -q tests/`): 1,718 tests collected, 95 errors,
  exit code 2. This sparse checkout materializes only a fraction of
  tracked files, and every one of the 95 collection errors is in a file
  this package never touched -- confirmed directly by grepping the
  `ERROR` lines specifically (not the full collected-test listing) for
  any mention of `evidence_rule`, `career_skill`, `EXPORT-009`,
  `account_export_domain_readers`, `test_settings_export_core_readers`,
  or `test_account_export_integration`: zero matches. Per the writer
  brief's own guidance and this repository's own recorded precedent for
  this exact count (~95, matching `PS-SETTINGS-EXPORT-007`/`-008`'s own
  reports), this was noted honestly rather than chased, since none of it
  implicates this candidate.
- **`scripts/migration_registry.load_registry()`** (the registry's own
  offline, no-connection validator), invoked directly in Python: loads
  all 45 entries without error, `PS-SETTINGS-EXPORT-009`'s `requires`
  resolve to `('PS-AUTH-001', 'PS-PLAT-003', 'PS-PLAT-006')`, `gate` was
  `None` at authoring time, both the forward and rollback files resolve
  and exist, and `executable_sha256(forward)` computes cleanly
  (`09c900119191c2379007aae85eeee06523675351437fca868d35b880bdbdd678`
  at authoring time).
- **Structural cross-validation beyond the shipped test file**, performed
  during authoring: a repository-wide Python scan confirmed the highest
  prior `THROW` number anywhere under `SQL FIles/` (before this package)
  was 59152, before claiming the `59200-59299`/`59300-59399` ranges, and
  a follow-up scan confirmed zero collisions after; a paren/comment
  balance check confirmed all three new `.sql` files end balanced
  (migration 70/70 parens, 2/2 comments; rollback 7/7 parens, 1/1
  comments; verify 216/216 parens, 8/8 comments); the registry's own
  `requires` ordering was confirmed against the actual migration array
  (`PS-AUTH-001` at index 8, `PS-PLAT-003` at index 3, `PS-PLAT-006` at
  index 6, this package's own entry appended last at index 44 of 45).
- **Real defects found and fixed during self-review, before the shipped
  test suite was finalized:**
  1. An early draft of
     `test_the_five_updated_ruling_reasons_never_promise_a_forbidden_disclosure`
     (in the NEW test file itself, not in the shipped SQL or adapter
     Python) asserted that none of the five updated `DOMAINS` reasons
     contained terms like `"object key"` or `"verifier"` anywhere. This
     failed against CORRECT shipped Python: `file_evidence_metadata`'s
     own updated reason must literally NAME these forbidden categories
     to state the safe-references-only rule at all ("never storage
     locators, container names, object keys, URLs, hashes/digests, or
     verifier identity"); a bare keyword-presence check cannot
     distinguish "names a forbidden category while stating the rule"
     from "promises to export it." The test was removed rather than
     patched, since the structural SQL tests (`FORBIDDEN_FIELDS`,
     `SAFE_REFERENCES_RULE`) already prove the actual reader never
     selects any forbidden column -- a fragile prose heuristic added no
     real coverage beyond that.
  2. An early draft of the verify script's own header comment cited
     `dbo.moment_placements.target_entity_id/dbo.slate_entities` by name
     as the precedent for excluding `source_entity_id`, which then
     collided with this package's own
     `test_verify_never_references_unrelated_sibling_machinery_tables`
     sanity check (a plain `assertNotIn("moment_placements", ...)`
     against the raw verify text, matching every sibling package's own
     identical check). Corrected by rephrasing the citation to describe
     the precedent without naming the specific sibling table, since the
     full reasoning already lives in the migration file's own header and
     in this package's own contract document.

## Gate state

**Gate proof: SEALED -- two runs; run 1 was REFUSED by the verify
script's own scan, and the refusal was CORRECT.**

- **Run 1 (manager, 2026-08-30, refused at the verification step)** on
  disposable `ps-migration-path-20260830-er` (deleted after):
  prerequisites replayed, forward apply created the one reader
  procedure, idempotent re-apply changed nothing -- then the
  verification script's own forbidden-column scan threw "The
  evidence-rule reader selects a forbidden column." Root cause: the
  scan, as this writer first wrote it, contradicted the reader's own
  disclosed design -- the sanctioned `evidence_linked` derivation
  necessarily MENTIONS `link.evidence_item_id` in the select-list text
  (to test `IS NOT NULL`; the value never leaves the procedure), and
  the offline tests parse OUTPUT column names, so only the engine's
  text-level scan exposed the contradiction. The fix is scan-side and
  makes the sanction explicit: assert the exact derivation expression
  is present exactly once, neutralize exactly it, then scan strictly --
  so any OTHER appearance of the column still refuses, and deleting the
  derivation itself now also refuses. The forward migration never
  changed.
- **Run 2 (manager, 2026-08-30, full pass; the standing seal)** on
  fresh disposable `ps-migration-path-20260830-er2` (recreated per the
  clean-run rule, deleted after): the complete sequence -- including
  the FIRST rows this reader program has ever inserted into
  `dbo.career_skill_links` and `dbo.evidence_items`, exercising both
  tables' constraint sets for the first time -- `verified = 1`,
  rollback rehearsed, forward re-applied. Sealed as digest
  `09c900119191c2379007aae85eeee06523675351437fca868d35b880bdbdd678`
  (`gated_at_utc 2026-08-30T11:37:04Z`), identical to the writer's
  authoring-time computation. The same commit replaced the pre-scripted
  placeholder with `test_registry_entry_pins_the_sealed_gate` (literal
  digest, recomputed-file check, the exact single-object list, the
  exact verification string) and rewrote this section -- registry +
  test + report, the standing lockstep executed complete.

The writer authored this candidate with `gate: null` and no database
access; earlier writer-voice passages saying so describe the authoring
state and this section records the sealed result.

## Independent-review correction round (manager, 2026-08-30)

The independent review of candidate `cbde91e9` returned **CONDITIONAL**:
substance sound — the seal recomputed offline and proven stable across
every commit; included ⊎ excluded = the DDL exactly with no residue; no
double export vs the living_resume skill reader; the soft-delete back
door verified from the verify script's actual flow; all five ruling
strings pinned and their "no writer anywhere" premise re-verified by
the reviewer's own repo-wide scan; six adversarial probes against the
scan sanction. Three LOW findings and one INFO, resolved as follows in
this round (one commit; the reviewer pre-verified by recomputation that
the migration-header edit leaves the sealed digest unchanged):

1. **F1 (LOW, fixed):** three changed-path figures were stale for
   exactly the files the manager's gate commit touched (verify 542,
   test file 1,034, registry +34); corrected with vintages attributed.
2. **F2 (LOW, accepted as a carried obligation — manager decision on
   the record):** the scan sanction's neutralization marker
   `(sanctioned evidence_linked derivation)` itself contains the token
   `evidence_linked`, which makes the verify script's subsequent
   alias-presence assertion vacuous (probe (v): dropping the output
   alias passes the gate scan; two offline tests still catch it, so
   there is NO exposure). The verify script is not digest-pinned, and
   editing it post-seal would leave the recorded gate proof describing
   text that no longer ships byte-for-byte — so, per the reviewer's own
   recommendation, the marker fix (`(sanctioned derivation)`) is
   CARRIED FORWARD as a bound obligation on the next package that
   touches this scan: the first real evidence reader, which the
   `file_evidence_metadata` ruling already routes to a future package.
   Recorded in the claim evidence file as a standing forward note.
3. **F3 (LOW, fixed):** the sealed migration's header said "THE OTHER
   SIX RULINGS" above an enumeration of four (across five DOMAINS
   keys); now "FOUR." Comment-only; the digest is unchanged (proven by
   the reviewer's recomputation and re-proven by the sealed-pin test's
   own recomputation check on every run).
4. **F4 (INFO, recorded):** bracket-quoted identifiers
   (`link.[evidence_item_id]`) evade both text-level forbidden-column
   checks program-wide; they remain refused twice over (exact-order
   allowlist offline; capture-table arity at gate). Recorded as a
   shared-conventions note alongside the existing verify-scan
   completeness item from the integration package's review.

Also recorded from the review's margins: the review brief cited 14
claimed surfaces; the claim carries 13 (a manager brief slip, not a
repo defect — the changed set is a strict subset either way), and the
`own_publication_versions` ruling string's production conclusion is
drawn from a verified code scan, the one sentence of the five that
reaches past direct measurement; both noted here for the record.

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
  connection double. No production or shared database was touched.
- **Least-privilege SQL grant:** Design documented only (see
  `CR8_ACCOUNT_EXPORT_EVIDENCE_RULE_READER.md`'s "Grant model" section,
  identical to every prior package's own recorded model). Nothing
  applied -- the governed apply identity holds `db_ddladmin` only and
  this migration contains no `GRANT` statement of any kind.
- **Current product truth:** Account-wide export remains unavailable
  today. This candidate adds one more read-only reader procedure and one
  more adapter function that nothing calls yet. No member-visible
  behavior changed. `dbo.career_skill_links` itself is unaffected by and
  unrelated to this package (this package never writes to it or to any
  of its referenced tables).

## Limitations, rollback, and next action

- **No live database proof of any kind from this writer.** Every SQL
  assertion in this candidate is a static text read; every Python test
  uses a fake cursor. The procedure's actual runtime correctness against
  a real SQL Server engine -- including every `CHECK`/`FOREIGN KEY`
  constraint the verification script's fixture data must clear across
  four different tables, two of which (`dbo.career_skill_links`,
  `dbo.evidence_items` as an INSERT target) had no prior write proof
  anywhere in this reader program -- was unproven until the manager's
  gate runs executed it (run 1's refusal exposed the verify scan's own
  contradiction; run 2 sealed -- see "Gate state" above).
- **Gate proof: SEALED.** See "Gate state" above.
- **No reader is wired to anything.** Nothing in this candidate connects
  the new domain reader to any worker or route; `services/
  account_export_domain_readers.py`'s new function exists and is fully
  tested offline, but nothing calls it yet.
- **The table is practically empty in real usage.** No writer populates
  `dbo.evidence_items` anywhere in this codebase today, so every real
  member's export from this reader either returns zero rows or rows
  with `evidence_linked = 0` exclusively, until some future feature
  actually lets a member attach evidence to a skill claim. This is
  disclosed in the contract document and the adapter module's own
  docstring, not hidden.
- **No sibling test file needed a surface extension this time.** A
  repository-wide grep for this package's own domain key and the four
  other updated reason keys across every file under `tests/` found no
  pin on any of them as excluded (or on the updated reasons' prior
  text) anywhere outside this package's own two explicitly claimed test
  surfaces (`tests/test_settings_export_evidence_rule_reader.py`, new,
  and `tests/test_settings_export_core_readers.py` /
  `tests/test_account_export_integration.py`, both modified). Unlike
  `PS-SETTINGS-EXPORT-007`'s own `voice_photo` tripwire discovery round,
  this candidate's own tripwire (`career_skill_links`'s prior excluded
  pin in `tests/test_settings_export_core_readers.py`) was already
  precisely anticipated by the writer brief and repointed in the same
  session, not discovered as a surprise.
- **Deviations from the brief:** None material. Every deliverable path
  the brief names (migration, rollback, registry entry, verification
  script, adapter update, this package's own test file, both docs, and
  the two explicitly-claimed sibling test files) was created or modified
  at its exact claimed location; no other unclaimed path was touched,
  confirmed by `git status --short` before staging. The brief anticipated
  four ruling-record reason updates; this report updates five `DOMAINS`
  entries because "publication domains" genuinely spans two existing
  keys with different dispositions -- disclosed above under "Design
  decisions" item 6, not a deviation from an explicit instruction so
  much as a resolution of a plural noun phrase against the actual
  schema. `evidence_linked`'s exact name/shape and `source_entity_id`'s
  classification were both judgment calls the brief explicitly left
  open -- see "Design decisions" items 1-2 above and the contract
  document's own reasoning for each.
- **THROW ranges claimed:** `59200-59299` for the forward/rollback pair
  (forward uses 59200-59206; rollback continues at 59207) and
  `59300-59399` for the verification script (59300-59351 actually used).
  Both ranges were selected after a repository-wide scan (via a small
  Python script over every `.sql` file under `SQL FIles/`) confirmed the
  highest THROW number anywhere in the repository, before this package,
  was 59152 (`PS-SETTINGS-EXPORT-008_preferences_consent_reader_isolation_verify.sql`).
  No other `.sql` file under `SQL FIles/` was found to reuse either
  reserved range (asserted by a dedicated repository-wide test).
- **What the manager's gate and any future package must know:**
  - The gate-pin lockstep PRE-SCRIPTED by this writer (matching the
    recovered pre-gate text of `PS-SETTINGS-EXPORT-008`'s own
    placeholder, via `git show 050eae05`) has since been EXECUTED
    exactly as scripted: one commit updated the registry's `gate`
    block, replaced the placeholder with
    `test_registry_entry_pins_the_sealed_gate`, and rewrote this
    report's "Gate state" section together -- after run 1's refusal
    exposed the verify scan's contradiction of the reader's own
    disclosed design, and run 2 sealed (see "Gate state" above).
  - `services/account_export_domain_readers.py`'s `DOMAINS` registry now
    has twelve included domains totalling thirty-one readers.
    `career_skill_links` is an EXISTING key flipped to `included`, not a
    new key -- a future package should not expect to find a "new domain"
    diff here.
  - `dbo.career_skill_links` legitimately returns zero rows, or rows
    with `evidence_linked = 0` exclusively, for every member today --
    disclosed via the reader's own design and this report, not hidden
    behind a plain empty read.
  - `source_entity_id`'s exclusion is a program-wide, structural
    convention (never resolve an `entity_id` reference), not a
    provisional judgment call the way `evidence_item_id`'s handling
    partly is. A future package should not expect to ever resolve it,
    with or without a new owner ruling.
  - `ai_proposals`, `profile_publication_foundation`,
    `own_publication_versions`, and `community_authored_content` remain
    excluded/unavailable with no reader in this package; each now
    carries a durable, dated owner-ruling reason, pinned by a dedicated
    test, that a future package touching any of them should read and
    respect rather than silently overwrite.
