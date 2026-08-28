# C1 owner technical completion report

## Core record

- **Task/package and delivery path:** `PS-SETTINGS-ACCOUNT-EXPORT-FOUNDATION-001`,
  C1 Protected additive database foundation.
- **Outcome and candidate scope:** Adds `dbo.account_export_jobs` and
  `dbo.account_export_job_domains`, three owner-scoped procedures
  (request/status/download-metadata) with server-derived identity, and five
  worker procedures (claim/complete/fail lease-fenced by compare-and-set;
  expire/cleanup deliberately unfenced system-wide sweeps) enforcing the
  owner-approved provisional limits (one active job per owner, one request
  per 24 hours, three bounded attempts, a seven-day ready window) plus a
  15-minute lease duration the writer chose at the scale of C0's pickup
  target (a target, never an SLA), as one additive migration with a
  data-safe rollback and one registry entry. No domain-reader procedure,
  container, workload identity, scheduler, worker runtime, route, template,
  or UI is added. No production schema apply is performed or authorized by
  this candidate.
- **Package manager and writer:** Sole writer `agent:claude-code/settings-c1-writer`,
  working only in the durable worktree
  `C:\Users\peter\Documents\PeerSlateWorktrees\PS-SETTINGS-ACCOUNT-EXPORT-FOUNDATION-001`
  on branch `work/2026-08-28-settings-account-export-foundation-001`, and
  only on the exact surfaces listed in
  `docs/governance/lane_claims/PS-SETTINGS-ACCOUNT-EXPORT-FOUNDATION-001.json`.
- **Base SHA and branch:** `origin/main`/activated-from
  `920b4dd38317487409532bc002478232c5b0b715`; write preflight passed at
  worktree head `4c1dbd7017a00a5fd4080d93e3948b750a7d7ad2` on
  `work/2026-08-28-settings-account-export-foundation-001` (confirmed by
  `git rev-parse HEAD` before writing).
- **Candidate changed paths** (original candidate plus this correction
  round; no path outside the original six was touched):
  - `SQL FIles/Migrations/PS-SETTINGS-EXPORT-001_account_export_foundation.sql`
    (new in the original candidate; corrected in this round — see
    "Correction round" below)
  - `SQL FIles/Migrations/PS-SETTINGS-EXPORT-001_account_export_foundation_rollback.sql`
    (new in the original candidate; unchanged in this round)
  - `SQL FIles/Migrations/registry.json` (one appended entry; `gate: null`
    at the end of this correction round — the gate round below later
    recorded the full proof block)
  - `tests/test_settings_account_export_migration.py` (new in the original
    candidate with 36 tests; corrected/extended to 40 in this round)
  - `docs/initiatives/PS-SETTINGS-MY-DATA-SHELL-001/C1_ACCOUNT_EXPORT_FOUNDATION.md`
    (new in the original candidate; corrected in this round)
  - `docs/initiatives/PS-SETTINGS-MY-DATA-SHELL-001/C1_OWNER_TECHNICAL_COMPLETION_REPORT.md` (this file)
- **Excluded actions and paths:** No claim, receipt, or evidence-tail file
  was created or modified (the lane claim's `evidence_surfaces` entry is
  reserved for the manager's post-review coordination per the writer
  brief). No `PACKAGE_REGISTRY.json`, runtime, route, template, service,
  pipeline, configuration, dependency, provider, resource, workload
  identity, scheduler, GRANT/role/user, data access, export generation,
  deployment, or production operation changed.

## Correction round (independent review CONDITIONAL)

The independent review of candidate `dddca9b4` returned CONDITIONAL. This
report and the six changed files below record the correcting writer's fixes,
made in the same worktree/branch by the same writer:

1. **HIGH, fixed.** `usp_RequestAccountExportForOwner`'s idempotency
   fingerprint was computed as `CONVERT(char(64), HASHBYTES(...), 2)`
   without a `LOWER()` wrap, while `CK_account_export_jobs_fingerprint`
   collates `Latin1_General_BIN2` and rejects anything outside
   `[0-9a-f]`. Every `INSERT` was at risk of failing with a CHECK
   violation (error 547), which the procedure's `2627`/`2601`
   unique-violation `CATCH` branch does not handle — export creation was
   dead on arrival. Fixed by wrapping the `CONVERT(...)` call in
   `LOWER(...)`. A new, non-vacuous test
   (`test_idempotency_fingerprint_is_lowercased_before_the_strict_check`)
   asserts `LOWER(CONVERT` opens the statement and `))` closes it — it
   would fail if the wrap were removed or left unclosed.
2. **MEDIUM, fixed.** Both C1 docs wrongly attributed the ungated-apply
   refusal to `scripts/apply_sql_migrations.py`. The refusal actually
   lives in `scripts/govern_sql_migrations.py` (`command_apply` →
   `resolve_apply_plan` → `migration_registry.gate_status`);
   `apply_sql_migrations.py` has no gate logic at all and applies only
   from its own hardcoded `MIGRATION_FILENAMES` tuple, which does not
   list this file (or several other recent migrations) — verified
   directly by grepping that tuple. Both docs corrected to name the real
   mechanism and to say the legacy applier simply does not know this
   migration exists, neither applying nor refusing it.
3. **MEDIUM, widened (manager decision).**
   `CK_account_export_jobs_time_order` forced
   `expired_at_utc >= ready_expires_at_utc`, making a future
   revocation-driven early expiry (C0's "authorization is no longer
   valid" trigger) unrepresentable. That inequality clause was removed;
   the other three orderings are unchanged. Documented in
   `C1_ACCOUNT_EXPORT_FOUNDATION.md`, and covered by a new test
   (`test_time_order_allows_revocation_driven_early_expiry`) scoped to
   the constraint's own clause text.
4. **MEDIUM, widened (manager decision).**
   `CK_account_export_jobs_cleanup_pair` forced
   `cleanup_state = 'not_required'` for a `failed` job, but a terminal
   failure can owe cleanup of a per-attempt C2 staging object. Widened to
   allow (not require) `pending`/`cleaned` for `failed`; `queued`/
   `running` remain forced to `not_required`.
   `usp_CleanupAccountExportJob`'s guard needed no functional change —
   it already refuses only `state = 'ready'` and treats any other state
   with `cleanup_state IN ('cleaned', 'not_required')` as an idempotent
   no-op, which already covers `failed` correctly for both today's
   always-`not_required` case and a future C2 worker's `pending` case.
   Its comments were expanded to say so explicitly. Documented in
   `C1_ACCOUNT_EXPORT_FOUNDATION.md` and covered by a new test
   (`test_cleanup_pair_allows_a_failed_job_a_real_cleanup_state`).
5. **MEDIUM, fixed.** This report previously said "Deviations from the
   brief: None known," but the C1 lane claim's `outcome` text names
   "least-privilege grants" as a C1 deliverable and C0 calls least-
   privilege grants "a C1 proof obligation," while this candidate ships
   the grant *model* only — no `GRANT`, `CREATE ROLE`, or `CREATE USER`
   statement, because the governed apply identity holds `db_ddladmin`
   only and cannot create a role or grant `EXECUTE`. The Limitations
   section below now records this explicitly as a deviation from the
   claim's own outcome wording, not a claim-specified exclusion, and
   `C1_ACCOUNT_EXPORT_FOUNDATION.md`'s wrong attribution to "the lane
   claim" was corrected to the actual (environmental) reason.
6. **LOW, fixed.** Four test-quality issues in
   `tests/test_settings_account_export_migration.py`: (a) a vacuous
   exact-whitespace `assertNotIn` in
   `test_only_download_metadata_procedure_ever_returns_the_artifact_reference`
   that could never match was replaced with a check against the
   procedure's actual trailing `SELECT`; (b) a state-filter check in
   `test_reauthorized_owner_may_read_truthful_expired_status` scanned
   only the pre-`SELECT` prefix, where the text it looked for could never
   appear — rescoped to the query's real `WHERE` clause; (c) a
   double-quoting bug (`f'"{forbidden}"'` applied to an already-quoted
   `"reference"` literal, producing the never-matching `""reference""`)
   in `test_audit_metadata_is_content_free` was fixed by not
   re-wrapping already-quoted forbidden strings; (d) the dynamic-SQL and
   grant guards were widened —
   `test_no_caller_selected_dynamic_table_name` now catches
   `EXEC(UTE)?\s*\(\s*@` regardless of spacing, and
   `test_no_grant_or_identity_creation_in_this_migration` now checks a
   bare `\bGRANT\b` (not only `"GRANT EXECUTE"`) scoped to the executable
   body (header comment stripped, so it does not false-positive on the
   header's own prose describing the absence of a grant) — and a new
   test, `test_forward_never_redefines_another_migrations_schema_object`,
   extends the "never redefines" check beyond procedure names to every
   table, index, and trigger this migration creates, checked for
   collision against every other registered forward migration file.

While making the cleanup-pair comment edit (finding 4) and the
`usp_CleanupAccountExportJob` guard comment (finding 6's context), the
correcting writer introduced two raw, undoubled single quotes inside two
`/* ... */` comments that live *inside* `EXEC(N'...')` dynamic-SQL blocks —
`'not_required'` and `'ready'`/`'failed'` — which would have terminated
those dynamic SQL string literals early. This was caught before committing
by re-running the same structural EXEC-block parser used during initial
implementation (parses each `EXEC(N'...')` body with quote-unescaping and
confirms it closes on `');`), not by the test suite, which does not
independently re-parse dynamic-SQL string termination. Both were fixed by
doubling the quotes (`''not_required''`, `''ready''`, `''failed''`), and
the parser was re-run clean (9/9 blocks) before any test run.

The **ADVISORY** items (deactivated-mid-session `THROW 57211` in the
request procedure; the `THROW 57256` "Unknown export job" existence
oracle in the worker-only cleanup procedure) were recorded as C2/C3
considerations in `C1_ACCOUNT_EXPORT_FOUNDATION.md` rather than changed,
per the coordinator's framing that they are the correcting writer's
judgment call and neither is a required fix.

Nothing in the six REQUIRED findings was disagreed with. The advisory
items were left as-is (see above) rather than changed, which is explicitly
within the discretion the coordinator's message granted.

## Gate round (governed migration proof)

The first governed gate run (2026-08-28, throwaway database
`ps-migration-path-20260828` on `peerslate`, created for the proof and deleted
after) failed and exposed two real defects that the offline text-scanning test
suite structurally cannot catch (items 1 and 3), plus one misdiagnosed extra
fix retained as belt-and-braces (item 2). The program manager (Claude Fable 5, who
succeeded the original writer session after it ended, under Pete's 2026-08-28
direction assigning the program end-to-end) corrected them in this same
worktree/branch and re-ran the gate to a full pass:

1. **Forward apply failure — illegal EXEC argument expression.**
   `usp_FailAccountExportJob` passed
   `@MetadataJson = N'{"failure_code":"' + @FailureCode + N'"}'` directly as a
   procedure-call argument. T-SQL forbids expressions as EXEC arguments, so the
   `CREATE PROCEDURE` inside the migration's dynamic SQL failed at apply time
   with `Incorrect syntax near '+'`. Fixed by materializing
   `@FailureMetadataJson` in a `DECLARE` immediately before the call; semantics
   unchanged.
2. **Correction of an earlier misdiagnosis, retained as belt-and-braces.**
   During gate diagnosis the manager initially concluded the rollback never
   dropped `trg_account_export_jobs_cleanup_guard` and added an explicit
   guarded `DROP TRIGGER` ahead of the dependency guards. That diagnosis
   was wrong — the rollback already dropped the trigger further down,
   before the table drops; the real rollback failure was defect 3 alone.
   The added early drop is a harmless duplicate (both drops are
   `IF OBJECT_ID … IS NOT NULL`-guarded) and is deliberately retained: the
   registry digest seals only the forward file, so editing the rollback
   after the gate would leave the rehearsed text and the shipped text
   different for no benefit.
3. **Rollback guards unpassable by construction.** The
   `sys.sql_expression_dependencies` guards counted the tables' own CHECK
   constraints (child objects) and computed columns (a table registers as its
   own parentless referencer) as "later programmable objects", so the guards
   could never pass on these tables. Both guards now exclude objects owned by
   the guarded table and the table itself. House-precedent rollbacks
   (PS-WORKSHOP-003/004, PS-OPPSLATE-USE-001) carry no such guard at all, so
   the repaired guard remains stricter than house baseline, not weaker.

Gate proof: executable SHA-256 `767e8509fcd7…`, gated `2026-08-28T18:58:43Z`,
50 objects created, prerequisites `PS-PLAT-000` through `PS-AUTH-001` replayed
onto the empty throwaway, idempotent re-apply proven, rollback rehearsed and
forward re-applied, proof written to `SQL FIles/Migrations/registry.json`
(`check`: 24 gated and matching). The offline suite (40 tests, 102 subtests)
passes unchanged after every fix. Two earlier failed gate attempts used the
same throwaway name; the database was dropped and recreated between attempts
so each proof started empty.

## Validation and self-review

- `python -m unittest -q tests.test_settings_account_export_migration` —
  **41/41 pass** (36 original + 4 added for this correction round: the
  fingerprint-lowering test, the two widened-constraint tests, and the
  generalized schema-object-collision test; + 1 added in the review
  round: the lease-duration/ready-window value pin).
- `python -m unittest -q tests.test_package_registry tests.test_governance_pointers tests.test_delivery_preflight` —
  **149/149 pass.**
- `python -m unittest -q tests.test_schema_migration_path` — **50/50
  pass** (run explicitly per the correction request; this package touches
  no file that test suite owns, and it was unaffected).
- The full `tests/test_*_migration*.py` set (16 files, including this
  package's) — **458 tests, all pass, 5 skipped** (the live-database
  two-connection gate classes in other packages' test files, gated on
  environment variables this environment does not set — expected and
  unrelated to this candidate).
- `git diff --check` — clean, no whitespace errors, re-run after every
  fix in this correction round.
- `scripts.migration_registry.load_registry()` was called directly against
  the edited `registry.json` and loaded without error; the new entry's
  `forward`/`rollback` paths were confirmed to resolve to real files.
- `scripts.migration_registry.executable_sha256()` was called directly
  against the corrected forward file. This correction round produced
  `fc3804cb…` (superseding the original candidate's `6d0ec907…`); the gate
  round below changed the forward file once more, and the current, final
  digest — the one the recorded gate proof and both C1 docs now carry — is
  `767e8509fcd7b8933157cfa331e85b3395a6043a2d4506ed0912166904b84917`.
- One complete-diff self-review was performed of every file this
  correction round touched: the EXEC-block structural parser (parenthesis
  balance, comment balance, THROW-number uniqueness, and — critically —
  quote-unescaping of every `EXEC(N'...')` block to confirm each still
  closes on `');` with no premature termination) was re-run after each
  substantive SQL edit, which is exactly how the writer's own
  self-introduced quote bug (described above) was caught before it ever
  reached a test run or a commit.

## Protected and release state

- **Independent review:** Required (`review_requirement: "independent"` on
  the lane claim) and not yet performed. This report does not claim a
  review occurred.
- **Repository state:** Candidate on the claimed branch only. Not pushed
  (per the writer brief, the manager verifies and pushes the frozen
  candidate). No PR opened, no merge.
- **Deployment/schema state:** Withheld
  (`production_authority: "withheld"` on the lane claim). The only
  database ever contacted is the disposable gate database
  `ps-migration-path-20260828` (created for the proof, deleted after);
  staging and production were never touched. The registry entry carries
  the full gate proof (`gated_at_utc 2026-08-28T18:58:43Z`, digest
  `767e8509fcd7…`), so `scripts/govern_sql_migrations.py`'s governed apply
  path (`command_apply` → `resolve_apply_plan` →
  `migration_registry.gate_status`) no longer refuses this migration for
  want of a gate — applying it anywhere real remains a separately
  authorized C4 operation. (The separate, older
  `scripts/apply_sql_migrations.py` is not gate-aware at all — it applies
  only from its own hardcoded `MIGRATION_FILENAMES` tuple, which does not
  list this or several other recent migrations. It would neither apply nor
  refuse this migration; it simply does not know it exists.)
- **Current product truth:** Account-wide export remains unavailable
  today. This candidate adds ledger schema and procedures that no route,
  UI, or scheduled worker calls; it changes no member-visible behavior.

## Limitations, rollback, and next action

- **Gate proof: executed** (see "Gate round" above): apply, idempotent
  re-apply, rollback rehearsal, and forward re-apply all passed against
  the disposable database, and the proof is recorded in the registry with
  digest `767e8509fcd7…`, matching the house pattern of PS-WORKSHOP-003/004
  and PS-OPPSLATE-USE-001.
- **Owner-isolation verification script: not written.**
  `SQL FIles/Verification/PS-SETTINGS-EXPORT-001_owner_isolation_verify.sql`
  is the house proof every other owner-scoped feature migration pairs with
  its gate, and connectivity to write and exercise one existed in the gate
  round. It was not produced because it is not in this claim's frozen
  surface list and the footprint cannot be widened after activation. The
  registry honestly records `verification: "none available"`. This is an
  explicit obligation for the next Settings export package, which must
  claim the file and pair it with a fresh gate run so the verification is
  actually exercised.
- **No live two-member isolation, lease-recovery/lock-timeout, or
  size/failure-path proof.** The gate proved apply, idempotent re-apply,
  rollback, and re-apply only; these behavioural proofs were not written
  or exercised (no verification script exists in this candidate — see the
  previous bullet), not for want of connectivity, which the gate round
  demonstrably had. `tests/test_settings_account_export_migration.py`
  proves the enforcing SQL text exists and has the shape the brief
  requires; it cannot prove the SQL runs correctly against a real SQL
  Server engine.
- **Deviations from the brief:** Every deliverable path listed in the brief
  was created at its exact claimed location; no unclaimed path was touched
  (confirmed by `git status --short` before this report, showing only the
  four SQL-and-test files plus the two new docs). One real deviation from
  the claim's own outcome wording: the C1 lane claim's `outcome` text
  names "least-privilege grants" as part of what C1 delivers, and C0 lists
  least-privilege SQL grants as "a C1 proof obligation." This candidate
  ships the grant *model* — which role gets which `EXECUTE` grant, and why
  — but applies no `GRANT`, `CREATE ROLE`, or `CREATE USER` statement at
  all, because the governed apply identity that runs this migration holds
  `db_ddladmin` only and cannot create a role or grant `EXECUTE`. This is
  the same environmental constraint every recent migration that needs a
  grant has hit (proved transactionally for
  PS-INTERVIEW-AI-EXTRACT-001 in run 1419, 2026-08-22) and follows that
  exact house pattern: the actual grants are a separate, later,
  administrator-run authority script, not something any writer's migration
  file can do under its own identity. See "Grant model" in
  `C1_ACCOUNT_EXPORT_FOUNDATION.md` for the full accounting.
- **Design decisions made without a more specific C0/brief instruction,**
  recorded here for the reviewer's benefit: the exact column set beyond
  C0's named bullets (e.g. `request_correlation_id` separate from
  `job_key`, the closed `failure_code` enum's eight values, the 15-minute
  lease duration); the choice to fence `usp_ExpireAccountExportJobs` as an
  unfenced system-wide batch (matching the existing
  `usp_PurgeInterviewAIServerCalls` convention) rather than a per-row
  transactional loop; and the choice not to add a domain-row-writing
  procedure at all in this slice, since the brief explicitly excludes
  domain-reader procedures and nothing else in C1 has a reason to populate
  `account_export_job_domains`.
- **Rollback:** `SQL FIles/Migrations/PS-SETTINGS-EXPORT-001_account_export_foundation_rollback.sql`
  refuses (throws) if either table holds any row, checks for dependent
  objects before dropping, drops the child table before the parent, and
  removes only the `PS-SETTINGS-EXPORT-001` ledger row. The rollback was
  rehearsed successfully during the gate round (drop, ledger-row removal,
  forward re-apply). Because no lasting environment carries this migration
  (only the deleted disposable gate database ever did), the practical
  rollback today is simply reverting these repository files; the SQL
  rollback itself serves whichever environment eventually applies the
  forward migration.
- **Next action:** The gate proof is recorded and the independent review
  of the exact pushed candidate is in progress. On a PASS: receipt and
  evidence-tail records, merge preflight, PR, claim close, worktree
  retirement, then C2 activation per the owner's standing sequential
  direction. The owner-isolation verification script transfers to the
  next package as an explicit obligation. Production apply remains
  deferred to C4 per C0's Protected child sequence; nothing in C1
  authorizes it.
