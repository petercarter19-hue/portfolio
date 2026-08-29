# CR1 owner technical completion report

## Core record

- **Task/package and delivery path:** `PS-SETTINGS-ACCOUNT-EXPORT-CORE-READERS-001`,
  Protected, replacement package 1 of the 2026-08-29 reader topology (after
  `PS-SETTINGS-ACCOUNT-EXPORT-DOMAIN-READERS-001`, which attempted all 13 C0
  domains at once, failed independent pre-activation review and was paused).
- **Outcome and candidate scope:** Exactly three C0 V1 domain-matrix domains —
  the member's own `dbo.app_users` row, the member's own active
  `dbo.member_profiles` row, and the eight PS-PLAT-006 Living Resume tables
  (one reader per table) — as ten read-only, owner-scoped SQL reader
  procedures in one additive migration (`PS-SETTINGS-EXPORT-003`); a
  data-safe rollback; a registry entry (authored with `gate: null` and
  `requires: ["PS-PLAT-006"]`; the manager's gate round later widened
  `requires` to add `PS-AUTH-001` and sealed the gate proof — see "Gate
  round" below); an isolation-verification script whose fixtures satisfy
  every `NOT NULL`/`CHECK`/`FOREIGN KEY` constraint on every touched table
  (`slate_entities`, `career_chapters`, `career_experiences`,
  `career_education`, `career_credentials`, `career_projects`,
  `career_achievements`, `career_skills`, `career_timeline_events`); a thin,
  connection-agnostic Python adapter with a `DOMAINS` registry covering the
  three included domains plus every other C0 matrix row (25 rows) and
  `career_skill_links` as its own excluded entry (26 non-included entries,
  29 `DOMAINS` keys total); and offline tests pinning every field allowlist,
  every forbidden-field exclusion, and every structural safety property. No
  table, trigger, index, container, worker wiring, route, or UI is added or
  changed. No schema apply, database connection, or Azure call was made by
  this writer.
- **Package manager and writer:** Sole writer
  `agent:claude-code/settings-core-readers-writer`, working only in the
  durable worktree
  `C:\Users\peter\Documents\PeerSlateWorktrees\PS-SETTINGS-ACCOUNT-EXPORT-CORE-READERS-001`
  on branch `work/2026-08-29-settings-account-export-core-readers-001`, on
  exactly the eight surfaces the lane claim's `surfaces` list and this
  package's brief both name as writer-owned (the claim JSON itself, its
  evidence file, and its receipts file are explicitly reserved for the
  manager's gate/review stage, matching the identical exclusion the paused
  DOMAIN-READERS-001 package's own writer brief recorded).
- **Base SHA and branch:** Activated from `origin/main` `7cc5789922a82b96fbcc3007ae7a48a6f84f6fce`
  per the lane claim; worktree HEAD confirmed at
  `81afdbef22b1441b151aa93686451e5889534db1` (`git rev-parse HEAD`) before any
  write — a later point on `main` than the claim's activation SHA, consistent
  with "base main 81afdbef or later." No other commit landed on this branch
  before this candidate.
- **Final SHA:** recorded in the pushed commit(s) on
  `work/2026-08-29-settings-account-export-core-readers-001`; see the
  writer's chat-turn final message for the exact value (this file is
  authored before that commit exists).
- **Candidate changed paths** (seven new, one modified; nothing else in the
  worktree was touched — confirmed by `git status --short` before staging):
  - `SQL FIles/Migrations/PS-SETTINGS-EXPORT-003_core_readers.sql` (new)
  - `SQL FIles/Migrations/PS-SETTINGS-EXPORT-003_core_readers_rollback.sql` (new)
  - `SQL FIles/Migrations/registry.json` (modified — one entry appended)
  - `SQL FIles/Verification/PS-SETTINGS-EXPORT-003_core_reader_isolation_verify.sql` (new)
  - `services/account_export_domain_readers.py` (new)
  - `tests/test_settings_export_core_readers.py` (new)
  - `docs/initiatives/PS-SETTINGS-MY-DATA-SHELL-001/CR1_ACCOUNT_EXPORT_CORE_READERS.md` (new)
  - `docs/initiatives/PS-SETTINGS-MY-DATA-SHELL-001/CR1_OWNER_TECHNICAL_COMPLETION_REPORT.md` (this file, new)
- **Excluded actions and paths:** `docs/governance/lane_claims/PS-SETTINGS-ACCOUNT-EXPORT-CORE-READERS-001.json`,
  its `evidence/*.md`, and its `receipts/*.json` were not created or
  modified — all three are reserved for the manager's gate/review stage. No
  route, template, worker wiring, scheduler, container, workload identity,
  grant, `.env.example` entry, dependency, or production operation changed.
  No database connection, Azure call, or network call of any kind was made
  by this writer or by any test in this candidate. The paused
  DOMAIN-READERS-001 branch (`work/2026-08-29-settings-account-export-domain-readers-001`,
  tip `ecfa4754`) was read only via `git show ecfa4754:<path>` as
  non-authoritative research; nothing was committed on it, merged from it, or
  checked out from it.

## Design decisions worth the reviewer's attention

Full field-by-field reasoning lives in `CR1_ACCOUNT_EXPORT_CORE_READERS.md`;
this section lists only the decisions with the widest blast radius.

1. **Read window as trailing columns on the single content result set, not a
   second result set and not OUTPUT parameters.** The lane claim names
   "columns or a second result set" as the two options and invites
   documenting the choice. A second result set was rejected because
   Microsoft's own INSERT (Transact-SQL) reference requires every result set
   an `EXEC` target returns to be column-compatible with the capturing
   table, not merely the first — confirmed via `microsoft_docs_search`
   before committing to this design, and independently confirmed as a real
   failure mode by the paused DOMAIN-READERS-001 package's own header
   comment. A second, differently-shaped result set would have made every
   reader **unsafe** to call with `INSERT ... EXEC`, directly contradicting
   the claim's own "INSERT-EXEC-safe by construction" requirement. OUTPUT
   parameters were rejected because they would add parameters beyond
   `@UserKey`, violating the pinned "`@UserKey`-only signatures" test
   requirement. Columns-on-the-content-row is the only choice compatible
   with both constraints simultaneously; its accepted cost (no SQL-sourced
   window on a genuinely zero-row result) is covered by the adapter's own
   independent `SELECT SYSUTCDATETIME()` bracketing, exactly the fallback
   `CR1_ACCOUNT_EXPORT_CORE_READERS.md`'s "Read window mechanism" section
   documents.
2. **One reader per PS-PLAT-006 table, eight total, never folded together.**
   The lane claim is explicit about this; it is also what makes every one of
   the ten procedures single-result-set and therefore genuinely
   INSERT-EXEC-safe (see above) and tractable for both the verification
   script's real-fixture-data proofs and the offline tests' exact
   column-list pinning.
3. **`requires: ["PS-PLAT-006"]` only — not `PS-AUTH-001` or
   `PS-SETTINGS-EXPORT-001`.** Every column this migration's guards check or
   its procedures select already exists as of `PS-PLAT-000` (`app_users`,
   including `auth_provider`/`profile_image_url`, both defined in the base
   table, never added later by `PS-AUTH-001`) or `PS-PLAT-002`
   (`member_profiles`) or `PS-PLAT-006` (the eight Living Resume tables).
   `PS-PLAT-006` is the single named prerequisite the linear registry chain
   (`PS-PLAT-006` requires `PS-PLAT-005` requires ... requires `PS-PLAT-000`)
   already makes sufficient — the same shorthand `PS-SETTINGS-EXPORT-001`
   itself uses by naming only `PS-AUTH-001`. This migration has no functional
   dependency on the account-export job ledger at all and does not name
   `PS-SETTINGS-EXPORT-001` as a requirement. (Superseded in one respect by
   the manager's gate round: the governed gate replays `requires` before
   running the verification script, whose fixtures provision synthetic
   owners through `usp_UpsertAppUserFromAuth` — so `PS-AUTH-001` was added
   for the PROOF's dependency, not the readers'. The reasoning above about
   the readers themselves remains correct.)
4. **Joined-chapter soft-delete widening**, applying `chapter.deleted_at_utc
   IS NULL` on every reader that joins `career_chapters` for parent linkage,
   regardless of whether the joined-from table has its own `deleted_at_utc`
   column. Recorded as this package's contract interpretation in
   `CR1_ACCOUNT_EXPORT_CORE_READERS.md`; proven at the data level (soft-
   deleting a chapter also removes its joined `career_projects` row) in the
   verification script's section 4.
5. **`chapter_type`/`event_type` included as content columns**, not treated
   as pure predicate/structural fields, because they are the categorical
   value the member chose when authoring the record and are needed to
   interpret `title`/`organization_name`/`event_label` meaningfully — the
   second contract interpretation, also recorded in the contract doc.
6. **The forbidden-field canary is a full-column-name set, matched against
   the content `SELECT` list only** (the substring of a procedure's body
   between the shared identity header's closing line and its own `FROM`
   clause), never the whole procedure body — a naive whole-body scan for
   `owner_profile_id`/`chapter_id`/`deleted_at_utc` would false-positive on
   the same tokens' entirely legitimate appearance in the `WHERE`/`JOIN`
   predicates, exactly the class of mistake the paused DOMAIN-READERS-001
   package's own design notes record having caught and fixed for a different
   substring (`credential`/`sha256_digest`).

## Validation and self-review

- **Validation history:** the writer's original run (133/664, exit 0) was
  taken at `54bd2d14`. Two manager gate-round commits and one review-round
  commit landed after it; the review round found that the gate-block commit
  had broken the then-pinned `gate is null` assertion (1 failed at
  `53d767c7`) and that this section's green claim had gone stale. The run
  below is the current one, re-taken at the final candidate after every
  correction, under both pytest and unittest (`Ran 133 tests ... OK`).
- **Verbatim final run** (checked by exit code, not piped output):
  ```
  ANTHROPIC_API_KEY=placeholder C:\Users\peter\Documents\portfolio\venv\Scripts\python.exe -m pytest -q tests/test_settings_export_core_readers.py tests/test_settings_account_export_migration.py tests/test_account_export_assembly.py tests/test_account_export_storage.py
  ................................... [ 26%]
  ..................................................................................................                                                                    [100%]
  133 passed, 664 subtests passed in 81.55s (0:01:21)
  PYTEST_EXIT_CODE_IS=0
  ```

  - `tests/test_settings_export_core_readers.py` (this package's own file):
    migration/rollback/verify file shape (single guarded batch, balanced
    parens/comments, no `\nGO`); THROW-number uniqueness within the forward
    and rollback files, the verify file's own numbers confirmed inside its
    reserved 58100-58199 block, and a repository-wide scan confirming no
    sibling `.sql` file anywhere under `SQL FIles/` reuses any number in
    either of this package's reserved ranges (58000-58099, 58100-58199);
    exactly the ten claimed procedures created and no table/trigger/index;
    never redefines another migration's procedure; every signature is
    exactly `@UserKey nvarchar(300)` and nothing else; every procedure
    shares the byte-identical identity-resolution header; every procedure
    filters by its expected owner predicate; every procedure has a
    deterministic `ORDER BY` and no `SELECT *`; own and joined-chapter
    soft-delete predicates present exactly where the design requires;
    every procedure returns the two read-window trailing columns and has
    exactly two `SELECT` keywords (identity resolution plus content, never
    a second content-shaped result set); **no procedure contains any
    transaction control, write, or nested `EXEC`** (the load-bearing
    structural tripwire); no procedure accepts a caller-selected owner/
    target parameter; no `GRANT`/role/user creation (scoped to the
    executable body so the header's own prose describing the *absence* of a
    grant cannot false-positive it); forbidden fields absent from every
    reader's actual output columns; `DOMAINS`' field-allowlist tuples equal
    the actual SQL output column list **exactly, in order**, for all ten
    (validated with an independent extraction of each procedure's content
    `SELECT` list before this was even written as a test, then re-confirmed
    by the shipped test); the rollback drops exactly the ten procedures and
    removes only this migration's ledger row; the registry entry pins the
    SEALED gate (the digest both as a literal and recomputed from the file,
    exactly ten reader objects, and the `verified = 1` verification string)
    and `requires == ["PS-PLAT-006", "PS-AUTH-001"]`, both ordered before
    this entry; the
    verify script provisions three synthetic owners including one
    deactivated, never commits, always reaches `ROLLBACK TRANSACTION;`
    before its report `SELECT`, and invokes every one of the ten
    procedures via both a genuinely bare `EXEC` (grep-tripwired) and an
    `INSERT ... EXEC` (for value-level proof); adapter offline tests using
    fake cursors/connections confirm every one of the ten domain functions
    is independently callable, decodes rows into dicts with the two
    window columns popped off and surfaced once at the top level, returns
    empty rows (never an error) for an unresolved identity, prefers the
    SQL-embedded window over the fallback whenever a row exists, never
    calls `commit`/`rollback`/`close` on the caller-supplied connection,
    binds `@UserKey` as a driver parameter rather than string-formatting it
    into the SQL text, and that the module source holds no
    `ALLOWED_PROCEDURES`/connection-factory/configuration of its own; and
    the `DOMAINS` registry has exactly three included domains
    (`account`/`profile`/`living_resume`) totalling ten readers, every
    non-included domain carries a non-empty truthful reason and no readers,
    `career_skill_links` is present with its evidence-item reason, and no
    reason string leaks a forbidden field name.
  - `tests/test_settings_account_export_migration.py`: unchanged, still
    green (41 tests) — confirms this candidate did not disturb the accepted
    C1 migration.
  - `tests/test_account_export_assembly.py` / `tests/test_account_export_storage.py`:
    unchanged, still green — confirms this candidate did not disturb the
    accepted C2 assembly/storage code.
- **Also run via `python -m unittest`** (the actual CI mechanism, not just
  pytest) against the same four modules: `Ran 133 tests ... OK`, exit code
  0 — confirms the suite is green under both runners.
- **A full collect-only pass of the entire repository test suite**
  (`pytest --collect-only -q tests/`): 4,368 tests collected, exit code 0,
  no collection error — confirms these new files do not break import/
  discovery anywhere else in the repository.
- **Structural cross-validation beyond the shipped test file**, performed
  during authoring: an independent Python script tokenizing the raw SQL
  text (respecting `/* */` and `--` comments and `''`-escaped string
  literals, distinct from either comment style) confirmed balanced
  parentheses and no unterminated string/comment in all three new `.sql`
  files; a second script located and decoded each of the ten
  `EXEC(N'...');` dynamic-SQL batches in the migration file by properly
  unescaping `''` (a naive regex non-greedily matching the first `');`
  substring is fooled by the doubled quotes inside `N''''`'s own
  empty-string escape, exactly the kind of trap this exercise was meant to
  catch) and confirmed each decoded procedure body is itself
  paren-balanced and has no unterminated string; a full column-list
  extraction (content `SELECT` text between the shared identity header and
  each procedure's `FROM` clause) was diffed against `DOMAINS`' `fields`
  tuples for all ten procedures with zero drift, before the corresponding
  test was written against it.
- **Real defects found and fixed during self-review, before the shipped
  test suite was finalized:**
  1. `microsoft_docs_search` confirmed a suspicion that a second,
     differently-shaped result set would break `INSERT ... EXEC` for every
     caller wanting reader content — this directly determined the
     read-window design (see decision 1 above) before any procedure body
     was finalized, rather than being discovered after writing 20 SQL files
     against the wrong assumption.
  2. An early test assertion (`self.assertNotIn("career_skill_links",
     self.forward)`) false-positived on this migration's own header comment
     and ledger-description string, both of which name the table in prose
     while explaining its deliberate exclusion — corrected to check each
     procedure's own body instead, matching the exact class of false
     positive `test_no_grant_or_identity_creation_in_this_migration`
     (copied from the sibling test file) already guards against via
     `executable_body()`; a second, near-identical false positive on the
     `CREATE ROLE`/`CREATE USER` check in the same test was fixed the same
     way.
  3. An early column-count assertion
     (`body.count("\n            SELECT")`, expecting exactly 2) failed for
     every reader that joins `career_chapters`, because the
     identity-resolution `SELECT` inside `IF @UserKey IS NOT NULL` is
     indented four spaces deeper than the content `SELECT` — replaced with
     a plain `body.count("SELECT")` check (verified empirically equal to 2
     for all ten procedures first), which is indentation-independent.
- `git status --short` before staging showed only the eight files listed
  above; no unrelated worktree state was touched.


## Gate round (manager, 2026-08-29)

Two governed-gate failures were corrected by the manager before the proof
sealed, each a one-change commit:

1. **Ledger self-description truncation.** The migration's own
   `schema_migrations` row description was 779 characters against the
   column's `nvarchar(500)`; the forward apply failed on insert. Shortened
   to 435 characters; semantics and all ten procedures unchanged.
2. **Verification dependency missing from `requires`.** The gate replays
   `requires` before running verification, and the verification script
   provisions its synthetic owners via `usp_UpsertAppUserFromAuth`
   (PS-AUTH-001) — absent from the throwaway under the original
   `["PS-PLAT-006"]`. Widened to `["PS-PLAT-006", "PS-AUTH-001"]` with the
   pinned test updated in the same commit and the rationale recorded there.

The third run passed in full: prerequisites replayed, ten objects created,
idempotent re-apply, `verified = 1` from the isolation script, rollback
rehearsed, forward re-applied, proof written to the registry (digest
`28678016…`). After the review round's cosmetic header fix, the gate was
re-run once more on a fresh disposable database with the same digest
(normalized executable content) and the same `verified = 1`.

## Correction round (independent review CONDITIONAL, 2026-08-29)

The fresh independent review returned CONDITIONAL with four findings, all
corrected in one lockstep round; the SQL substance passed every privacy and
correctness probe (six mutation probes, five caught — the sixth became
finding 3):

1. **CRITICAL — gate-pin lockstep miss (manager's own).** The manager's
   registry gate-block commit `53d767c7` did not update the test pinning
   `gate` as null, leaving the frozen candidate red on its own suite. The
   test now pins the sealed gate positively (digest `28678016…`, ten
   reader objects, the `verified = 1` verification string) and is renamed
   accordingly.
2. **HIGH — stale validation claim.** This report asserted a green run at a
   superseded SHA; see "Validation history" above for the honest sequence.
3. **MEDIUM — missing defense-in-depth pin.** The chapter-joined test now
   also asserts the parent chapter's own owner predicate, so the composite
   FK is no longer the only thing standing between the linkage join and a
   leak under future schema relaxation.
4. **LOW — header fragment.** A thinking-aloud false start in the
   migration's authoritative header comment was removed. Because the
   digest hashes normalized executable content, the sealed digest is
   unchanged; the gate was nonetheless re-run in full on a fresh
   disposable database after the edit and again recorded
   `verified = 1`.

## Protected and release state

- **Independent review:** Required (`review_requirement: "independent"` on
  the lane claim) and not yet performed. This report does not claim a
  review occurred.
- **Repository state:** Candidate on the claimed branch, pushed per the
  writer brief (writer pushes and stops; no PR, no merge).
- **Deployment/schema state:** Withheld entirely
  (`production_authority: "withheld"` on the lane claim). No database was
  contacted by this writer or by any test — every SQL assertion in this
  candidate is a static read of the committed `.sql` text, and every
  Python adapter test uses a fake cursor/connection double.
  `SQL FIles/Migrations/registry.json` carries this migration's entry with
  a SEALED gate proof (digest `28678016…`, gated on disposable
  `ps-migration-path-20260829-cr2`, `verified = 1` from the isolation
  script), so the governed apply path no longer refuses it for want of a
  gate. Applying it, anywhere real, remains a separately authorized, later
  action; no lasting database carries it.
- **Least-privilege SQL grant:** Design documented only (see
  `CR1_ACCOUNT_EXPORT_CORE_READERS.md`'s "Grant model" section, identical to
  `PS-SETTINGS-EXPORT-001`'s own recorded model). Nothing applied — the
  governed apply identity holds `db_ddladmin` only and this migration
  contains no `GRANT` statement of any kind.
- **Current product truth:** Account-wide export remains unavailable today.
  This candidate adds ten read-only reader procedures and an adapter that
  nothing calls yet. No member-visible behavior changed.

## Limitations, rollback, and next action

- **No live database proof of any kind from this writer.** Every SQL
  assertion in this candidate is a static text read; every Python test uses
  a fake cursor. The ten procedures' actual runtime correctness against a
  real SQL Server engine — including every hand-satisfied
  `CHECK`/`FOREIGN KEY` constraint the verification script's fixture data
  must clear across nine touched tables — is unproven until the manager's
  gate run executes it. Self-review traced every `NOT NULL`/`CHECK`/
  `FOREIGN KEY` constraint on every touched table against the fixture
  `INSERT`s by re-reading each table's actual DDL in
  `PS-PLAT-002_profiles_entities_access.sql` and
  `PS-PLAT-006_living_resume_domain.sql` before writing them (for example:
  `slate_entities` rows created and their `entity_id` captured via
  `SCOPE_IDENTITY()` before each dependent `career_chapters`/
  `career_achievements`/`career_skills`/`career_timeline_events` insert,
  satisfying the composite `(entity_id, owner_profile_id)` foreign keys;
  `career_credentials`' `issue_date <= expiration_date` CHECK satisfied with
  consistent literal dates; `career_skills`' filtered unique index on
  `(owner_profile_id, skill_name)` satisfied with distinct per-owner skill
  names) — but this remains a static trace, not an actual engine run.
- **Gate proof: SEALED** (see "Gate round"): disposable-database apply,
  idempotent re-apply, rollback rehearsal, and this candidate's own
  isolation-verification script all passed, twice (third gate run and the
  post-header-fix re-proof). The actual next steps are the independent
  review's completion and the merge; production apply stays a C4 matter.
- **No reader is wired to anything.** Nothing in this candidate connects a
  domain reader to any worker or route; `services/account_export_domain_readers.py`
  exists and is fully tested offline, but nothing calls it yet. Wiring a
  real reader into a future worker is explicitly out of scope for this
  package.
- **Deviations from the brief:** The two contract interpretations recorded
  above (joined-chapter soft-delete widening; `chapter_type`/`event_type`
  included as content) and the read-window mechanism choice (columns, not a
  second result set or OUTPUT parameters, with the Microsoft-documentation-
  backed rationale above). No other deviation: every deliverable path the
  brief names was created at its exact claimed location; no unclaimed path
  was touched, confirmed by `git status --short` before staging.
- **What the manager's gate and the next packages must know:**
  - `services/account_export_domain_readers.py`'s `DOMAINS` registry is the
    single source of truth for domain disposition/reason/allowlist. A
    future domain-population slice should render from it directly rather
    than re-deriving a second list.
  - `career_skill_links` has no reader under the current contract and will
    not automatically gain one from a future evidence-decision package
    without its own separately claimed, separately reviewed reader.
  - The two contract interpretations above are load-bearing; a future
    slice must not silently widen or narrow either without updating this
    record and its tests.
  - Every reader excludes soft-deleted content by construction; a future
    "include deleted content" requirement (if ever approved) needs new
    procedures, not a change to these.
- **Rollback:** `SQL FIles/Migrations/PS-SETTINGS-EXPORT-003_core_readers_rollback.sql`
  drops exactly the ten procedures this migration creates (guarded
  `IF OBJECT_ID(...) IS NOT NULL`) and removes only the
  `PS-SETTINGS-EXPORT-003` ledger row. No dependency guard is needed — this
  migration creates no table and holds no data, so there is nothing a later
  object could depend on and nothing to lose. Because this migration has
  never been applied anywhere, the practical rollback today is simply
  reverting these eight repository files.
- **Next action:** Push this branch (no PR, per the writer brief) and stop.
  The manager's gate run — registry gating, disposable-database apply,
  idempotent re-apply, rollback rehearsal, and executing this candidate's
  own isolation-verification script — is the next step, followed by
  independent review of the exact pushed candidate. Nothing here proceeds
  to any further child package or to any production authority without both.
