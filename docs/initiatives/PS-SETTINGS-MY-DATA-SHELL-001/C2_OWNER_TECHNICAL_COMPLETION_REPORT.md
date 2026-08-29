# C2 owner technical completion report

## Core record

- **Task/package and delivery path:** `PS-SETTINGS-ACCOUNT-EXPORT-ASSEMBLY-001`,
  C2 Protected private-artifact and workload design.
- **Outcome and candidate scope:** A private Azure Blob adapter
  (`services/account_export_storage_service.py`) with job/attempt-scoped
  staging, promotion only after an independent readback recomputes SHA-256
  and both byte-size facts, and idempotent staging/final cleanup; a
  deterministic fixture-only ZIP assembler
  (`services/account_export_assembly_service.py`) implementing C0's archive
  and consistency contract; a bounded worker entry point
  (`scripts/run_account_export_worker.py`) that claims one job, enforces
  owner-active status before any storage write, and completes or fails the
  job through the C1 lease-fenced procedures; the C1-recorded owner-isolation
  verification script; two governed documents; and four new `.env.example`
  config names. This writer's own commits made no Azure resource, workload
  identity, grant, or network call (the manager separately provisioned part
  of this after the fact — see "Provisioning state" below). No domain-reader
  procedure was added, and no route, UI, or schedule reaches any of this
  code.
- **Package manager and writer:** Sole writer `agent:claude-code/settings-c2-writer`,
  working only in the durable worktree
  `C:\Users\peter\Documents\PeerSlateWorktrees\PS-SETTINGS-ACCOUNT-EXPORT-ASSEMBLY-001`
  on branch `work/2026-08-28-settings-account-export-assembly-001`, and only
  on the surfaces named in the writer brief (a deliberate subset of the lane
  claim's full `surfaces` list — see "Excluded actions and paths" below).
- **Base SHA and branch:** Activated from `origin/main`
  `54c6a2fcd2be155c7698baddd81efef11aada6dd`; worktree head confirmed at
  `7eb29a3d71f8bbdc0b8a5be351f3e2822884caf8` (`git rev-parse HEAD`) before any
  write, matching `main` exactly (no other commits landed on this branch
  before this candidate).
- **Candidate changed paths (this writer's three commits only** — a fourth,
  the manager's own `19a8833b`, is separate and covered under "Correction
  round 2" and the next bullet):
  - `services/account_export_storage_service.py` (307 lines — includes the
    Correction round 2 fix; see below)
  - `services/account_export_assembly_service.py` (318 lines — includes the
    Correction round 2 fix)
  - `scripts/run_account_export_worker.py` (603 lines — includes the
    Correction round 2 fixes)
  - `tests/test_account_export_storage.py` (448 lines, 31 tests — includes
    the Correction round 2 additions)
  - `tests/test_account_export_assembly.py` (347 lines, 19 tests — includes
    the Correction round 2 addition)
  - `SQL FIles/Verification/PS-SETTINGS-EXPORT-001_owner_isolation_verify.sql`
    (414 lines — includes the first gate-round correction; see "Correction
    round" below. **Now SEALED** as of the manager's gate-proof commit; this
    writer's Correction round 2 work touched no line of it)
  - `docs/initiatives/PS-SETTINGS-MY-DATA-SHELL-001/C2_ACCOUNT_EXPORT_ASSEMBLY.md`
    (504 lines — includes the Correction round 2 staleness fixes)
  - `docs/initiatives/PS-SETTINGS-MY-DATA-SHELL-001/C2_OWNER_TECHNICAL_COMPLETION_REPORT.md`
    (this file)
  - `.env.example` (+22 lines: `EXPORT_BLOB_ACCOUNT_URL`, `EXPORT_BLOB_CONTAINER`,
    `ACCOUNT_EXPORT_WORKER_SQL_CONNECTIONSTRING`,
    `ACCOUNT_EXPORT_WORKER_FIXTURE_MODE_CONFIRMED`)
  - `docs/initiatives/PS-SETTINGS-MY-DATA-SHELL-001/C1_ACCOUNT_EXPORT_FOUNDATION.md`
    (+3/-1 lines: the two permitted touches only — a CommonMark blank line
    above `**Not executed:**`, and a `(fulfilled by C2: ...)` annotation on
    the transferred-obligation bullet; confirmed by `git diff --stat` against
    base `7eb29a3d`, correcting this report's own earlier, incorrect
    `+4/-1` claim)
- **The manager's commit `19a8833b`** ("Record the paired gate proof with
  verified owner isolation and the provisioning state") is a separate,
  fourth commit on this same branch, authorized under the standard
  writer/manager division of labor the brief itself specifies (the manager
  runs the gate and updates the registry; the writer does not). It changed
  `SQL FIles/Migrations/registry.json` (appending the gate-proof block with
  `verified = 1`) and this completion report (adding the "Provisioning
  state" bullet under "Limitations, rollback, and next action" — present
  below). This writer did not author that bullet or the registry change;
  both are recorded here only to keep this report internally consistent
  with itself at the current candidate SHA.
- **Excluded actions and paths (this writer's own commits):** No claim,
  receipt, or evidence-tail file was created or modified — `receipts/*.json`
  specifically records an *independent reviewer's* outcome (confirmed by
  reading the accepted C1 sibling's own receipt: `reviewer_ref`,
  `review_type: "independent"`, populated only after a real review ran);
  authoring one myself as the writer would fabricate review evidence that
  has not happened. Both are left for the manager/reviewer stage, matching
  how the writer brief's explicit "DELIVERABLES" list is a deliberate subset
  of the lane claim's full `surfaces` list (which also includes the claim
  JSON and `registry.json`, neither touched by this writer, `registry.json`
  per an explicit "DO NOT touch" instruction in the writer brief). This
  writer's own commits changed no `SQL FIles/Migrations/registry.json`,
  Azure resource, workload identity, grant, schedule, route, template, or
  production operation, and made no live database or Blob Storage call,
  including by their tests. `registry.json` and the Azure resources named
  above DID subsequently change/come into existence via the manager's own,
  separately authorized commit and provisioning actions — see the two
  bullets above and "Provisioning state" below; that is not a contradiction
  of this bullet, which is scoped to this writer's commits only.

## Design decisions worth the reviewer's attention

Recorded here because the brief left them to the writer's judgment, not
because any is a defect:

1. **`services/database_service.py` is deliberately not used by the worker.**
   Its `ALLOWED_PROCEDURES` allowlist does not list any of the eight
   account-export procedures, and that file is outside this claim's frozen
   surfaces, so it could not be extended. Reusing it would also contradict
   C1's recorded intent that the five worker procedures are reserved for "a
   future dedicated worker identity...distinct from the application and
   maintenance identities." The worker instead opens its own connection
   directly via `mssql_python.connect()`, reading a new, dedicated
   `ACCOUNT_EXPORT_WORKER_SQL_CONNECTIONSTRING` — the exact
   `scripts/interview_ai/run_interview_telemetry_purge.py` house pattern for
   a maintenance-class script owning its own connection string. This was the
   one point in the brief that read, on first pass, like a possible
   claim-scope wall; on inspection it resolves cleanly to an established
   house pattern rather than requiring a stop.
2. **Failure code for owner-inactive: `domain_unavailable`.** No code in the
   closed seven-value enum `usp_FailAccountExportJob` accepts names
   authorization directly. C0's trust boundary treats an owner whose
   authorization is no longer valid as making every domain's read contract
   unsatisfiable at once ("A domain that cannot satisfy its contract is
   unavailable or excluded before readiness"). `domain_unavailable` is the
   closest true statement among the seven; `internal_error` would misreport
   an intentional refusal as a bug, and `worker_unavailable` would misreport
   an owner-state fact as an infrastructure fault. Recorded prominently in
   `scripts/run_account_export_worker.py` and
   `C2_ACCOUNT_EXPORT_ASSEMBLY.md`.
3. **`uncompressed_size_bytes` excludes `manifest.json` itself.** Defined as
   the sum of every archive member's uncompressed size except the manifest,
   so the figure the assembler reports is exactly the figure its own
   in-progress cap check already enforced, and the figure
   `AccountExportStorageService.promote()` independently recomputes from a
   readback agrees with it exactly on the happy path. An earlier version of
   this candidate included manifest.json in the total, which a test caught
   immediately (see "Validation and self-review").
4. **The compressed cap is checked twice: incrementally and finally.** The
   in-loop check during assembly sees `buffer.tell()` before
   `zipfile.ZipFile`'s own `__exit__` appends the central directory and
   end-of-central-directory record on close, so it alone could let a result
   over the cap by that overhead through. A final check against the
   complete, closed archive's true length is the authoritative gate. Also
   caught by a test during self-review, before it could hide in an
   exact-boundary case.
5. **`requested_at_utc` is fetched with a second, direct, job_key-scoped
   `SELECT`.** `usp_ClaimAccountExportJob`'s own result columns are
   `job_key`, `owner_user_id`, `owner_profile_id`, `attempt_count`,
   `lease_token`, `lease_expires_at_utc` only. An earlier draft read this
   field from the claim result dict anyway, which silently always returned
   `None` (a real, if non-crashing, bug — every manifest would have reported
   the worker's own start time instead of the member's true request time).
   Caught during self-review by re-reading the migration's actual `SELECT`
   list against the code, not by a test (no test exercises `run_once`
   end-to-end — see "Limitations").
6. **The owner-isolation verification script never calls
   `usp_ClaimAccountExportJob`, `usp_ExpireAccountExportJobs`, or a second,
   deliberately-failing `usp_CompleteAccountExportJob`.** The first two are
   system-wide (no `@UserKey`, no owner predicate) and would interact with
   whatever real, unrelated jobs already exist in a production-safe run
   against a shared database. The third was in an earlier draft (to prove
   lease fencing directly) and was removed after tracing through T-SQL's
   transaction-nesting rules: `usp_CompleteAccountExportJob`'s own `CATCH`
   block issues an unqualified `ROLLBACK TRANSACTION` on error, which,
   called from inside this script's own still-open outer transaction, rolls
   back to the outermost `BEGIN TRANSACTION` regardless of nesting depth —
   it would have silently discarded everything the verification script had
   built so far (both synthetic owners and jobs), corrupting every
   assertion after it. All three states this script needs (`running`,
   `ready`, `expired`) are instead reached by a direct `UPDATE` scoped to
   exactly the synthetic `job_key` the script itself created, with the real
   `usp_CompleteAccountExportJob` performing the actual ready transition
   (fenced by that same job_key and a lease token the script generated, so
   it can never touch any other row).
7. **The worker makes a best-effort `cleanup_staging` call on any failure**,
   regardless of which stage failed (assembly, staging, or promotion). This
   is always safe (idempotent; absence is success) and prevents an abandoned
   attempt's bytes from lingering in the private container. No procedure in
   this claim's frozen surfaces can set `cleanup_state` for a `failed` row,
   so this is not reflected in the ledger, only in the container actually
   being clean.

## Correction round (gate finding)

The first governed gate run against the pushed candidate replayed
prerequisites and forward-applied the (unchanged, already-accepted) C1
migration cleanly, then **failed at the verification step** running
`SQL FIles/Verification/PS-SETTINGS-EXPORT-001_owner_isolation_verify.sql`:

```
[Microsoft][SQL Server]Cannot use the ROLLBACK statement within an INSERT-EXEC statement.
```

**Root cause.** T-SQL refuses `INSERT ... EXEC` against any stored procedure
that can reach a `ROLLBACK TRANSACTION` statement — this is a static
restriction the engine enforces regardless of whether that call actually
takes the failing branch. The original script used
`INSERT @Table EXEC dbo.usp_RequestAccountExportForOwner ...` (twice, for
each synthetic owner) and `INSERT @Table EXEC dbo.usp_CompleteAccountExportJob ...`
(once, to reach the `ready` state); both procedures have a `CATCH` block that
can reach `ROLLBACK TRANSACTION`, so both calls violated the restriction even
though every call in this script only ever exercises their success path.
This is a more specific instance of the same transaction-control hazard
recorded as design decision 6 above (that finding correctly predicted the
*class* of problem — a ROLLBACK-capable procedure invoked unsafely inside
this script's shared transaction — but the earlier self-review reasoned
through the *nested-rollback-scope* failure mode, not this separate,
stricter, purely syntactic `INSERT ... EXEC` restriction, which the offline
static checks available at the time had no way to catch; only an actual
engine run surfaces it).

**Fix.** Both procedures are now called **bare** (`EXEC dbo.usp_...;`, no
capturing `INSERT`); their effect is confirmed with a direct
`SELECT`/`EXISTS` against `dbo.account_export_jobs` instead of reading the
procedure's own returned result set (safe because each synthetic owner's
`profile_id`/`job_key` is guaranteed unique to this run). `INSERT ... EXEC`
remains in use only for the two procedures with no transaction control at
all (`usp_GetAccountExportStatusForOwner`,
`usp_GetAccountExportDownloadMetadataForOwner`), and the script's section 0
now greps both bodies for `ROLLBACK` and throws if either is ever found, so
a future edit cannot silently reintroduce this exact failure. THROW numbers
`57734`/`57735` were added for those two new guards (the file's full range is
now `57700`–`57735`). No other required coverage changed: forged/guessed-key
neutrality, foreign-owner refusal, ready/unexpired-only download metadata,
and reauthorized-owner expired truthfulness are all still asserted, now
against ledger state rather than a captured procedure result set. Full diff
confined to
`SQL FIles/Verification/PS-SETTINGS-EXPORT-001_owner_isolation_verify.sql`
plus this report and `C2_ACCOUNT_EXPORT_ASSEMBLY.md`.

**Confidence this specific failure is resolved:** high — the fix removes the
exact syntactic construct (`INSERT ... EXEC` against a ROLLBACK-capable
procedure) the engine named in its own error message, verified by grepping
the corrected file for every `EXEC dbo.` call site and confirming
`usp_RequestAccountExportForOwner` and `usp_CompleteAccountExportJob` no
longer appear after an `INSERT`. **Not separately verified:** whether the
gate's harness handles the now-unconsumed result sets these two bare `EXEC`
calls stream back to the client (each has its own `SELECT` at the end, no
longer captured into a table variable) — this was not something offline
static checks or the Python test suite could exercise, and remains for the
next gate run to confirm. It is not a new risk this script introduces:
`usp_UpsertAppUserFromAuth` was already called bare in the original,
never-flagged candidate and in every sibling `*_owner_isolation_verify.sql`
file, so a bare `EXEC` producing a result set inside this exact gate harness
is an already-exercised pattern, not a novel one.

## Correction round 2 (independent review)

Independent review of candidate `19a8833b` returned CONDITIONAL: engineering
judged strong and the trust boundary clean, with 8 findings requiring one
correction round. All 8 are fixed below, in this writer's subsequent
commit(s) on this same branch. The new HARD RULE for this round — the
owner-isolation verify script is now SEALED (gate-executed,
`verified = 1` recorded in the registry; editing it would desynchronize
rehearsed vs. shipped text) — was honoured: neither it, the two migration SQL
files, `SQL FIles/Migrations/registry.json`, nor the lane claim were opened
for editing. Findings that touched on the sealed script are documented, not
worked around.

1. **MODERATE — `promote()`'s staging cleanup on the critical path.**
   A transient staging-delete failure after a successful promotion was
   raising `storage_delete_failed`, which the worker would treat as a job
   failure despite the artifact already being safely committed — every
   retry of that attempt would then hit `storage_conflict` against the
   orphaned final object (`overwrite=False`) until attempts ran out.
   **Fixed:** wrapped in `try`/`except AccountExportStorageError: pass`,
   matching the worker's own best-effort cleanup-on-failure treatment.
   **Test added:** `test_promote_succeeds_even_when_staging_cleanup_fails`.
2. **MODERATE — `C2_ACCOUNT_EXPORT_ASSEMBLY.md` stale** (still said the
   verification was unexecuted and no Azure resource existed). **Fixed:**
   its Status, "Not proven", and "Azure actions" sections rewritten to match
   this report's own provisioning paragraph and the registry's
   `verified = 1` gate block — same container, same identity, same ids,
   same two pending grant layers.
3. **MODERATE — this report's own internal contradiction** (an earlier
   "nothing changed" sentence next to the manager's later, accurate
   provisioning paragraph). **Fixed:** "Excluded actions and paths" and
   "Candidate changed paths" above are now scoped explicitly to this
   writer's own commits, with the manager's commit `19a8833b` and its
   registry/report changes named and cross-referenced rather than silently
   contradicted.
4. **LOW-MODERATE — `hash_mismatch` declared and mapped but unreachable.**
   Nothing ever compared `promote()`'s independently-recomputed hash against
   the assembly service's own pre-upload hash. **Fixed:** added
   `verify_promoted_hash(assembled, promoted)`, called immediately after
   `promote()`, raising `AccountExportStorageError("hash_mismatch")` on
   disagreement. **Tests added:** `test_verify_promoted_hash_passes_when_equal`,
   `test_verify_promoted_hash_raises_hash_mismatch_on_disagreement`.
5. **LOW — `external_attr = 0` did not pin anything.** Python's `zipfile`
   silently substitutes `0o600 << 16` for any falsy `external_attr` at write
   time, so every produced archive already carried `25165824`
   (`0o600 << 16`) regardless of this code writing `0` — confirmed, not
   disputed. **Fixed:** `info.external_attr = 0o600 << 16` set explicitly,
   with the substitution explained in a comment so a future reader is not
   relying on unstated stdlib knowledge; the three "zeroed" claims (the
   module docstring, the code line's own former claim, and
   `C2_ACCOUNT_EXPORT_ASSEMBLY.md`) all corrected to "pinned". **No archive
   bytes changed** — the substitution was already happening every time.
6. **LOW — the determinism test never pinned ZIP metadata**, so it could not
   have caught finding 5. **Fixed:** added
   `test_zip_entries_carry_pinned_metadata_not_host_or_wall_clock_values`,
   asserting `date_time`, `create_system`, and `external_attr` on every
   archive member against the exact expected pinned values.
7. **LOW — (a) a fabrication risk in `requested_at_utc`; (b) a mislabeled
   post-failure log state.** **Fixed (a):** the worker now raises
   (mapping to `internal_error`) instead of silently substituting
   `assembly_started_at_utc` if `fetch_requested_at_utc` ever reads back
   `NULL` — unreachable today (the column is `NOT NULL`), but C0's
   no-false-promise rule forecloses ever fabricating a request time even
   defensively. **Fixed (b):** added `post_fail_state(attempt)`
   (`queued` while `attempt_count < 3`, `failed` once exhausted — mirroring
   `usp_FailAccountExportJob`'s own hardcoded `@MaxAttempts`), used at both
   logging call sites instead of a hardcoded `state="failed"`. **Test
   added:** `test_post_fail_state_is_queued_while_attempts_remain_else_failed`.
   **Doc sentence added** to `C2_ACCOUNT_EXPORT_ASSEMBLY.md` noting that an
   inactive owner's job burns its attempts by design — the closed procedure
   set has no separate "never retry this" signal.
8. **TRIVIAL — assorted record-accuracy items.** Per-file test counts
   corrected (the original `22`/`23` were plain miscounts, not staleness —
   actual counts were `18`/`27` before this round's additions, now
   `19`/`31`; see "Validation and self-review" below); the
   `C2_ACCOUNT_EXPORT_ASSEMBLY.md` line count refreshed; the C1-doc delta
   corrected from this report's own wrong `+4/-1` to the actual `+3/-1`
   (`git diff --stat` against base `7eb29a3d`); a doc sentence added to
   `C2_ACCOUNT_EXPORT_ASSEMBLY.md` noting the owner-active check-then-act
   race is acceptable because `usp_GetAccountExportDownloadMetadataForOwner`
   independently re-checks `active = 1` at download time, so a
   since-deactivated owner can never retrieve an artifact the race let
   through; a doc note added recording that `THROW 57724` is intentionally
   absent from the sealed script (residue of the second-completion proof
   removed in "Correction round" above) — recorded rather than renumbered,
   because the script is sealed.

## Validation and self-review

- `ANTHROPIC_API_KEY=placeholder C:\Users\peter\Documents\portfolio\venv\Scripts\python.exe -m pytest -q tests/test_account_export_assembly.py tests/test_account_export_storage.py tests/test_settings_account_export_migration.py`
  — **91 passed, 121 subtests passed** (verbatim final run, after Correction
  round 2). No skip, no xfail, no warning suppressed.
  - `tests/test_account_export_assembly.py`: 19 tests (18 original + 1 added
    this round, `test_zip_entries_carry_pinned_metadata_not_host_or_wall_clock_values`
    — finding 6) covering deterministic byte-identical assembly, manifest
    completeness/ordering/stable key order, no-unlisted-bytes and
    manifest-first archive shape, pinned ZIP member metadata
    (`date_time`/`create_system`/`external_attr`), independent SHA-256/size
    recomputation, compressed and uncompressed cap enforcement at the exact
    boundary and one byte/unit over, and the full domain-input validation
    matrix (13 subtests across shape violations, path traversal, duplicate
    paths, bad schema version/disposition).
  - `tests/test_account_export_storage.py`: 31 tests (27 original + 4 added
    this round — findings 1, 4x2, 7b:
    `test_promote_succeeds_even_when_staging_cleanup_fails`,
    `test_verify_promoted_hash_passes_when_equal`,
    `test_verify_promoted_hash_raises_hash_mismatch_on_disagreement`,
    `test_post_fail_state_is_queued_while_attempts_remain_else_failed`)
    covering create-only staging, oversize-before-upload refusal,
    independent-readback promotion and its five distinct refusal paths
    (missing object, size/property mismatch, no manifest, oversize
    uncompressed, final-object collision), promotion succeeding despite a
    staging-cleanup failure, idempotent staging/final cleanup, canonical
    job-key/attempt name validation, a static source-text grep proving no
    SAS/delegation API is ever imported plus behavioural URL-absence checks,
    error-message content-freedom, and the worker's pure helpers
    (`is_owner_active`, `normalize_job_key`, `choose_failure_code_for_error`,
    `content_free_log_fields`, `verify_promoted_hash`, `post_fail_state`)
    exercised with fake cursor doubles — never a real connection.
    (**Note:** the original candidate's reported counts of 22/23 here were
    plain miscounts at the time they were written, not staleness from later
    changes — the actual pre-round-2 counts were 18/27; see "Correction
    round 2", finding 8.)
  - `tests/test_settings_account_export_migration.py`: unchanged, still
    green (41 tests, 102 subtests) — confirms this candidate did not
    disturb the accepted C1 migration in any way.
- `python -c "import ast; ast.parse(...)"` on `scripts/run_account_export_worker.py`
  after every edit — confirms syntactic validity without importing
  `mssql_python`'s real connection path.
- A static structural check of the new SQL file (parenthesis/comment
  balance, no `GO`, unique `THROW` numbers in the `57700`–`57735` block —
  confirmed clear of every sibling verification file's range and of the
  migration's own `57200`–`57257` procedure-error range, and — critically —
  every single quote outside `/* */` comments paired, checked by stripping
  block comments first since English contractions inside prose comments
  make a naive whole-file quote-parity check produce false positives even
  on the known-good `PS-OPPSLATE-004` precedent, confirmed by running the
  same heuristic against it) — re-run after the correction round below.
  This script's *current* (corrected) text was not itself executed by this
  writer — see "Protected and release state" and "Correction round" above
  for what the manager's actual gate run against the prior candidate found.
- One complete-diff self-review of every changed file, which found and
  fixed five real issues before this report was written (items 3–5 and the
  nested-transaction hazard above; plus one initially-uncaught bug where a
  malformed non-dict list entry raised an uncontrolled `ValueError` instead
  of a controlled `AccountExportAssemblyError`, caught by the very first
  test run and fixed immediately).

## Protected and release state

- **Independent review:** Required (`review_requirement: "independent"` on
  the lane claim). Performed once against candidate `19a8833b`, returning
  **CONDITIONAL** (engineering judged strong, trust boundary clean; 8
  findings needing one correction round). All 8 are fixed in "Correction
  round 2" above. The review of the exact candidate produced by this
  correction round is still pending.
- **Repository state:** Candidate on the claimed branch, pushed through two
  correction rounds beyond the original candidate (the manager's own
  gate/provisioning commit sits between them). About to be pushed once more
  with this round's fixes, per the brief's instruction (writer pushes and
  stops; no PR, no merge).
- **Deployment/schema/resource state:** Production apply/deployment remains
  withheld (`production_authority: "withheld"` on the lane claim) — nothing
  in this candidate is deployed or live. Schema and gate state, however, have
  changed since the original candidate: the manager's paired gate run
  executed the *corrected* owner-isolation script (after the first
  "Correction round" fix above) against a disposable database and recorded
  `verified = 1` in the registry's gate block — the first gate attempt, run
  against the pre-fix script, had errored partway through at an
  `INSERT ... EXEC` call before reaching its own `ROLLBACK TRANSACTION`, so
  no synthetic or real data was left behind by that failed attempt either
  way. This writer made no database call directly in either round. Azure
  resource state has also changed: the private container and the dedicated
  workload identity now exist (manager-provisioned; see "Provisioning state"
  below) — neither existed on the original candidate. Both required grant
  layers remain pending, and every adapter method still fails closed because
  `EXPORT_BLOB_ACCOUNT_URL` is not configured; nothing in this candidate's
  code assumes otherwise.
- **Current product truth:** Account-wide export remains unavailable today.
  This candidate adds a storage adapter, an assembler, a hand-run worker
  script, and a verification script that no route, UI, scheduler, or other
  application code calls. It changes no member-visible behavior.

## Correction round 3 (secret-scanner history finding)

The PR validation build failed in "Scan full repository history for secrets":
two `generic-api-key` findings, both on the synthetic job-key fixture
`3fa85f64-…` (the standard OpenAPI example UUID — realistic enough in entropy
to trip the generic rule next to `key=`) in the two C2 test files, introduced
in the branch's first commit. Because the scanner reads history, fixing the
working tree alone cannot clear it, and fingerprint allowlists are a recorded
house anti-pattern across squash merges. Applied fix (by the manager, three
mechanical fixture lines): the synthetic job key is now the entropy-dead
`aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa` everywhere in both test files (a first
attempt, all-digit `00000000-0000-4000-8000-000000000001`, was correctly
rejected by `test_staging_and_final_names_require_a_canonical_job_key` —
its uppercase variant no longer differed — and was never shipped), and the
branch history was squashed to a single delivery commit so no historical
commit carries the old string. In a follow-up confirmation round the
independent reviewer verified the squash by git plumbing (the old string
exists in no reachable commit), reproduced the suites at exit 0, found the
delivered code unchanged since its PASS, and required exactly the record
corrections this paragraph now carries; the paired evidence file records the
full review arc. Determinism hashes recomputed by the tests changed with the
fixture, as designed.

## Limitations, rollback, and next action

- **No live database or Blob Storage proof of any kind from this writer.**
  Every test in this candidate mocks the Azure Blob SDK and fakes DB cursors.
  The corrected owner-isolation SQL script's live proof belongs entirely to
  the manager: their paired gate run of 2026-08-28 on disposable
  `ps-migration-path-20260828-c2` executed the corrected script's assertions
  against a real engine, and the registry gate block records
  `verification: PS-SETTINGS-EXPORT-001_owner_isolation_verify.sql returned
  verified = 1`. (A prior version failed structurally before any assertion
  could matter; see "Correction round".)
- **Provisioning state (manager actions, 2026-08-28, under the owner's
  recorded program authorization, ref
  `session:01a03e17-a645-7ae0-8da3-164eef90a333/owner-direction:2026-08-28/PS-SETTINGS-ACCOUNT-EXPORT-C1-C4-END-TO-END`):**
  the private container `peerslate-private-account-export` EXISTS on
  storage account `peerslatecapturemedia` (container publicAccess null;
  account allowBlobPublicAccess false — private at both levels), and the
  dedicated workload identity `peerslate-account-export-worker` EXISTS
  (clientId `b84a0485-0d6f-4338-9575-5250faac934b`, principalId
  `e6a73ef9-8b70-4920-8726-cbf64ea21563`). NOT yet granted: (a) the
  identity's container-scoped `Storage Blob Data Contributor` role — the
  manager's harness declines permission-granting actions on its own
  authority, so that one command awaits the owner; (b) the SQL-side
  contained user and least-privilege `EXECUTE` grants on the five worker
  procedures, which require the AAD-admin authority path. Every adapter
  method still fails closed (`storage_unavailable`) until
  `EXPORT_BLOB_ACCOUNT_URL` is configured; nothing in this candidate
  assumes any grant has happened, and no worker schedule exists.
- **`scripts/run_account_export_worker.py`'s full orchestration
  (`run_once`) is not covered by an automated test — only its pure helper
  functions are** (`is_owner_active`, `normalize_job_key`,
  `choose_failure_code_for_error`, `content_free_log_fields`,
  `fetch_requested_at_utc`'s SQL text pattern is not separately asserted).
  Exercising the full claim→assemble→stage→promote→complete sequence would
  need a much larger fake-connection harness than either claimed test file
  was scoped for; this candidate's confidence in that sequence rests on
  manual tracing during self-review (which is exactly how the
  `requested_at_utc` bug above was caught) rather than an automated
  end-to-end test. Flagging this honestly rather than claiming coverage
  that does not exist.
- **Fixture-only, by design and by hard rule.** No domain-reader slice
  exists. `build_fixture_domain_files()` returns obviously-synthetic
  placeholder content only. The worker refuses to run at all unless
  `ACCOUNT_EXPORT_WORKER_FIXTURE_MODE_CONFIRMED` is explicitly set, as a
  tripwire against ever pointing it at a database that could hold a real
  member's queued export request — see `C2_ACCOUNT_EXPORT_ASSEMBLY.md`,
  "What is fixture-proven vs unproven," for the full accounting.
- **Deviations from the brief:** None found beyond the design decisions
  recorded above (which the brief either left open or explicitly invited —
  "any deviation from this brief with rationale") and the two correction
  rounds' fixes, all responses to gate/review findings rather than
  independent scope changes. Every deliverable in the brief's exact list was
  created at its exact claimed location, at every commit; the claim JSON,
  evidence, and receipt files remain deliberately untouched throughout, and
  `registry.json` was touched only by the manager's own authorized commit,
  never by this writer, as reasoned under "Excluded actions and paths."
- **What C3/C4 must know:**
  - The owner-isolation script's four required proofs (forged/guessed keys,
    foreign-owner reads, ready/unexpired-only download metadata,
    reauthorized-owner expired truthfulness) have since been executed by the
    manager's paired gate run and recorded `verified = 1` — see "Provisioning
    state" above and "Correction round 2." The script is now sealed; C3/C4
    must not edit it, only read its recorded gate result.
  - `usp_ClaimAccountExportJob` still has no owner-active predicate; C2's
    worker-side check is a direct SQL read, not a procedure, because no
    procedure could be added under this claim. A future slice should
    consider formalizing it once a domain-reader or worker-identity package
    can claim `SQL FIles/Migrations/registry.json` and add one.
  - `usp_FailAccountExportJob`'s closed enum has no code for
    "owner authorization no longer valid." C3/C4 should decide whether a
    dedicated code is worth a future migration, or whether
    `domain_unavailable`'s reasoning here should simply become the
    documented house convention.
  - The manifest/adapter's `uncompressed_size_bytes` definition (excludes
    `manifest.json`) and the archive's fixed member order (manifest.json
    first, then lexical) are now load-bearing parts of the contract; a
    future domain-reader slice populating real content must not change
    either without updating both this document and
    `tests/test_account_export_assembly.py`.
- **Rollback:** Every file this candidate adds or touches is new or an
  additive documentation edit; no schema, data, resource, or configuration
  exists anywhere to roll back. Rollback is a repository revert of the
  files listed under "Candidate changed paths."
- **Next action:** Push this branch with this round's fixes (no PR, no
  merge, per the writer brief). The gate has already run and passed
  (`verified = 1`) against the sealed script, and part of C2's Azure
  provisioning already exists — neither needs repeating. What remains: the
  owner's decision on the two pending grant layers (storage RBAC, SQL
  `EXECUTE`); independent review of the exact candidate this correction
  round produces; C3 (experience) and C4 (release proof) remain separately
  claimed Protected packages, not activated by any of this.
