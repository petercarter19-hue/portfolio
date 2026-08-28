# C1 account export foundation

**Package:** `PS-SETTINGS-ACCOUNT-EXPORT-FOUNDATION-001`
**Slice:** C1 — Protected, additive database foundation
**Depends on:** accepted C0 (`docs/initiatives/PS-SETTINGS-MY-DATA-SHELL-001/C0_ACCOUNT_EXPORT_ARCHITECTURE.md`, main `8cb633895c6df5b9b09e0e9f46922fdc60550e49`)
**Status:** Candidate migration/rollback/registry/test files, gate-proven 2026-08-28 against the disposable database `ps-migration-path-20260828` (created for the proof, deleted after). Never applied to staging or production. No production authority.

## Decision

C1 adds exactly the job/domain ledger and owner/worker procedures C0's "C1
foundation" section names, as one additive, idempotent-safe migration:
`SQL FIles/Migrations/PS-SETTINGS-EXPORT-001_account_export_foundation.sql`,
paired with a data-safe rollback and one registry entry. It creates no
domain-reader procedure, container, workload identity, scheduler, worker
runtime, route, or UI, and authorizes no production schema apply. The ledger
stores no exported member content: every column is an identifier, state,
timestamp, count, byte size, or hash about a request and its derived
artifact, never the artifact bytes or a domain record body.

## Table contracts

### `dbo.account_export_jobs`

One row per export request and its (at most one) derived artifact.

| Column | Purpose |
| --- | --- |
| `job_key` | Opaque, server-generated (`NEWID()`), the only handle ever given to an owner or the application layer. |
| `owner_user_id`, `owner_profile_id` | Server-resolved identity; never caller-selected. |
| `state` | `queued` \| `running` \| `ready` \| `failed` \| `expired`. |
| `requested_at_utc`, `started_at_utc`, `completed_at_utc`, `expired_at_utc`, `ready_expires_at_utc` | Full lifecycle timestamps. |
| `attempt_count` | 0–3, enforced by `CK_account_export_jobs_attempts`. |
| `lease_token`, `lease_expires_at_utc` | Compare-and-set worker lease; both null unless `state = 'running'` (`CK_account_export_jobs_lease_pair`). |
| `failure_code` | A closed, content-free enum (eight values); required when `state = 'failed'`, forbidden when `state IN ('ready','expired')`. |
| `idempotency_fingerprint` | `LOWER(SHA2_256(owner_profile_id \| calendar_day))`, never derived from a client-supplied secret or identity material. The explicit `LOWER()` matters: `CONVERT(char(64), HASHBYTES(...), 2)` alone is not guaranteed lowercase, and `CK_account_export_jobs_fingerprint` collates `Latin1_General_BIN2` and rejects anything outside `[0-9a-f]` — an unwrapped uppercase digest would fail every INSERT with a CHECK violation (error 547), which is not one of the errors the request procedure's `CATCH` treats as a benign race. |
| `request_correlation_id` | Content-free operational correlation, independent of `job_key`. |
| `assembly_started_at_utc`, `assembly_cutoff_at_utc`, `consistency_marker_start`, `consistency_marker_cutoff` | The assembly window and `@@DBTS`-style consistency markers C0's archive contract requires. |
| `final_artifact_reference`, `final_artifact_sha256`, `compressed_size_bytes`, `uncompressed_size_bytes` | Committed together only at `ready`/`expired`; `CK_account_export_jobs_artifact_not_url` refuses a value beginning `http://`/`https://` as defense in depth — this is a private, server-only locator, never a URL. |
| `cleanup_state` | `not_required` \| `pending` \| `cleaned`; only reachable in that order (`trg_account_export_jobs_cleanup_guard` refuses any attempt to move a `cleaned` row backward). |

Enforcement objects: `UX_account_export_jobs_owner_active` (a unique
filtered index on `owner_profile_id` where `state IN ('queued','running')`)
gives an engine-level guarantee for the two contended active states; the
third active condition — `ready` before its `ready_expires_at_utc` — depends
on the clock and cannot be a static filtered-index predicate, so it is
fenced transactionally inside `usp_RequestAccountExportForOwner` with a
locked read, exactly the alternative C0 names ("a reviewable filtered
unique constraint or transactional procedure").

Two schema invariants are deliberately widened beyond the narrowest
possible reading of C0's lifecycle table, both per manager decision on
independent review:

- **`CK_account_export_jobs_time_order` allows `expired_at_utc` earlier
  than `ready_expires_at_utc`.** C0's `expired` state covers two distinct
  triggers: "the ready window elapsed" *and* "authorization is no longer
  valid." A CHECK forcing `expired_at_utc >= ready_expires_at_utc` would
  make the second trigger — a future authorized revocation process (owner
  deletion, deactivation, a security decision) expiring a still-unexpired
  `ready` job early — structurally unrepresentable. The constraint now
  only orders `requested_at_utc` → `started_at_utc` → `completed_at_utc` →
  `ready_expires_at_utc`; nothing in this migration performs an early
  revocation-driven expiry (`usp_ExpireAccountExportJobs` still only
  expires past-deadline `ready` rows), but the schema no longer blocks a
  later, separately authorized process from doing so.
- **`CK_account_export_jobs_cleanup_pair` allows `cleanup_state` to be
  `pending`/`cleaned` for a `failed` job, not only `ready`/`expired`.** C0's
  C2 design gives every worker attempt its own staging prefix; a terminal
  failure (`usp_FailAccountExportJob`'s attempts-exhausted branch, or the
  claim procedure's stale-lease reap) can leave a per-attempt staging
  object behind even though the job never became a downloadable `ready`
  artifact. Forcing `failed` to `cleanup_state = 'not_required'` would
  make that real cleanup obligation unrepresentable. The widened
  constraint *allows* — it does not *require* — a real cleanup state on a
  `failed` row: today nothing in C1 sets a failed job's `cleanup_state`
  away from its `not_required` default (C1 has no container/staging
  concept to know whether a given failure left anything behind), so every
  `failed` row this migration can actually produce still has
  `cleanup_state = 'not_required'` in practice. The widening exists so a
  future C2 worker can record `pending` accurately once it knows better.
  `usp_CleanupAccountExportJob`'s guard is unchanged by this widening: it
  already refuses only `state = 'ready'` and treats any other state with
  `cleanup_state IN ('cleaned', 'not_required')` as an idempotent no-op —
  that logic already covers `failed` correctly for both today's
  always-`not_required` case and a future C2 worker's `pending` case,
  driven purely by `cleanup_state`, never by which terminal state produced
  it.

### `dbo.account_export_job_domains`

One row per (job, domain) pair: domain code, schema identifier/version,
disposition (`included` \| `excluded` \| `unavailable`), read window, source
change marker, record/byte counts, content hash, provenance JSON, and a
mutually exclusive omission/failure reason. `CK_account_export_job_domains_shape`
enforces the three disposition shapes exactly (an `included` row carries
every read fact and no reason; `excluded` carries only an `omission_reason`;
`unavailable` carries exactly one of `omission_reason` or `failure_reason`).
**No procedure in this migration writes to this table.** No V1 domain has an
approved field allowlist yet (C0's domain matrix), so population is deferred
to a future, separately claimed domain-reader slice — the table exists now
so C2/that slice has a stable target, not because anything reads a domain
today.

## Procedure contracts

### Owner procedures (intended grant: the existing web-app principal role)

- **`usp_RequestAccountExportForOwner(@UserKey)`** — resolves identity
  server-side; returns `created` (new `queued` row), `existing` (the
  member's current active job, no new row), or `rate_limited`
  (`retry_after_utc` = last request + 24h). A concurrent duplicate that
  races past the locked read and collides on the unique filtered index is
  caught (`ERROR_NUMBER() IN (2627, 2601)`) and resolved to the same
  `existing` outcome rather than surfaced as an engine error.
- **`usp_GetAccountExportStatusForOwner(@UserKey, @JobKey)`** — returns
  state/timestamps/attempt/failure_code/size for the caller's own job only.
  An unknown key and a foreign key fall through the same
  `owner_profile_id = @ProfileId` predicate to zero rows — no branch
  distinguishes an unknown job from a foreign job. An unresolved caller
  identity is different in shape (not in disclosure): the procedure
  `RETURN`s before any `SELECT`, producing no result set at all rather
  than an empty one. That divergence reveals only the caller's own account
  state, which the caller already knows — but C3 must handle the
  no-result-set case explicitly (a naive fetch raises), mapping it to the
  same neutral not-found experience (recorded C3 obligation). A reauthorized
  owner reading their own retained row sees a truthful `expired` state; the
  procedure has no state-based filter that would hide it.
- **`usp_GetAccountExportDownloadMetadataForOwner(@UserKey, @JobKey)`** —
  the **only** procedure that ever returns `final_artifact_reference`, and
  only for the caller's own `ready`, unexpired job. It exists for the
  trusted application server's internal proxy fetch; nothing it returns is
  a URL, container name, or SAS token, and it returns zero rows for every
  other case (unknown, foreign, not-yet-ready, or past expiry) with no
  further disclosure.

None of the three accepts `@OwnerUserId`, `@OwnerProfileId`, a table name,
or an artifact/URL parameter — verified by
`test_owner_procedures_never_accept_a_caller_selected_owner_or_artifact`.

### Worker procedures (intended grant: a future dedicated worker identity)

- **`usp_ClaimAccountExportJob`** — no parameters, no `@UserKey`. First
  reaps any `running` row whose lease has expired and whose attempts are
  exhausted into a terminal `failed` (`attempts_exhausted`); then claims one
  eligible `queued` or stale-leased `running` row with
  `WITH (ROWLOCK, UPDLOCK, READPAST)` so concurrent workers skip past rows
  already being claimed instead of blocking; issues a new lease token and a
  15-minute expiry; increments `attempt_count`.
- **`usp_CompleteAccountExportJob(@JobKey, @LeaseToken, ...)`** — validates
  the hash (64 lowercase hex), positive byte sizes, and that the artifact
  reference is not a URL; the fencing `UPDATE` requires
  `state = 'running' AND lease_token = @LeaseToken AND lease_expires_at_utc > @Now`
  together, and `IF @@ROWCOUNT <> 1` refuses a stale or foreign completion
  rather than silently accepting it. Sets the seven-day `ready_expires_at_utc`,
  clears `failure_code`, sets `cleanup_state = 'pending'`.
- **`usp_FailAccountExportJob(@JobKey, @LeaseToken, @FailureCode)`** — same
  lease/attempt fence as complete. Requeues to `queued` (retaining the
  failure code for visibility) while `attempt_count < 3`; otherwise
  terminates to `failed`.
- **`usp_ExpireAccountExportJobs(@BatchSize)`** — batched, unfenced by
  design (system-wide, not one job): flips `ready` rows whose
  `ready_expires_at_utc` has passed to `expired`. This transition alone
  blocks download, because the download-metadata procedure requires
  `state = 'ready'`; it runs strictly before any future physical deletion.
- **`usp_CleanupAccountExportJob(@JobKey)`** — refuses (`THROW 57257`) a
  job that is still `ready` (physical deletion may never precede or
  substitute for the expiry transition); is an idempotent no-op for a job
  already `cleaned` or `not_required`; otherwise moves `pending` to
  `cleaned`. The `AFTER UPDATE` trigger is the schema-level backstop that
  makes "never resurrect a delivered artifact" true even if a future
  caller bug tried.

None of the five worker procedures takes a `@UserKey`, and none of the
three owner procedures, and none of the eight combined, ever references
`dbo.account_export_job_domains`.

## Enforcement rules and where each lives

| Rule | Mechanism |
| --- | --- |
| One active job per owner (queued/running/ready-before-expiry) | Filtered unique index (queued/running) + locked transactional read (ready-before-expiry) in the request procedure. |
| Duplicate request returns the existing job | `usp_RequestAccountExportForOwner` locked read, plus the `2627`/`2601` race-catch branch. |
| One request per owner per 24 hours | Rolling-window query in the request procedure (`DATEADD(HOUR, -24, @Now)`), not a calendar day; not caller-configurable. |
| Bounded retry, three attempts | `CK_account_export_jobs_attempts` (schema) + `@MaxAttempts = 3` (claim, fail) — hardcoded, not a parameter. |
| Lease fencing, compare-and-set | `lease_token`/`lease_expires_at_utc` pair CHECK + `ROWLOCK/UPDLOCK/READPAST` claim + `state/lease_token/lease_expires_at_utc` fence on complete and fail, with `@@ROWCOUNT` verification on complete. |
| Stale completion rejected | `IF @@ROWCOUNT <> 1 THROW` in `usp_CompleteAccountExportJob`. |
| Expiry blocks download before physical deletion | `usp_ExpireAccountExportJobs` flips state before any future cleanup step can run; `usp_CleanupAccountExportJob` additionally refuses a still-`ready` job. |
| Cleanup idempotent, never resurrects | `usp_CleanupAccountExportJob`'s no-op branch + `trg_account_export_jobs_cleanup_guard`. |
| No caller-selected owner/table/URL/artifact reference | Owner procedure signatures; `CK_account_export_jobs_artifact_not_url`; the download-metadata procedure is the sole reader of the artifact reference. |
| Unknown/foreign/inactive/deleted jobs indistinguishable | Owner-predicate-only `WHERE` clauses with no branching in status/download reads. |
| No exported member content anywhere | Both tables hold only identifiers, states, timestamps, counts, sizes, and hashes; `account_export_job_domains` is written by nothing in this slice. |

## Grant model

The governed apply identity that runs `SQL FIles/Migrations/*.sql`
(`peerslate-ado-schema`) holds `db_ddladmin` only. `db_ddladmin` can create
tables, indexes, triggers, and procedures, but **cannot** create a database
role, create a login/user, or grant `EXECUTE` — this was proved
transactionally in run 1419 (2026-08-22) for the Interview AI telemetry
migration and documented there
(`SQL FIles/Migrations/proposed/PS-INTERVIEW-AI-EXTRACT-001_telemetry.sql`).
This migration follows that exact house pattern:

- **No `GRANT`, `CREATE ROLE`, `CREATE USER`, or `sp_addrolemember` appears
  anywhere in this file** (verified by
  `test_no_grant_or_identity_creation_in_this_migration`).
- The intended production grant shape — documented here, not created here —
  is: the three owner procedures grant `EXECUTE` to the existing web-app
  principal role; the five worker procedures grant `EXECUTE` to a role
  created for a future dedicated worker identity, never to the web-app
  identity and never a broad table grant. No such role or identity is
  created by this package (explicitly excluded by the C1 lane claim).
- Binding the actual grants is a separate, later, administrator-run
  authority script in the shape of
  `scripts/configure_interview_telemetry_sql_authority.py` and
  `scripts/configure_community_maintenance_sql_authority.py` — a C1
  follow-on or a C2/C4 concern, not something this migration file can do
  under its own identity.

## Proof plan: executed and unexecuted

**Executed in this candidate (offline, no database):**

- `python -m unittest -q tests.test_settings_account_export_migration` — 41
  tests (102 subtests) of static structural assertions against the actual
  SQL text: file shape and
  guarded-batch style, exactly the claimed procedures/tables/trigger and no
  others, idempotent-rerun guards, no redefinition of another migration's
  procedure, prerequisite/column checks, owner-identity resolution and
  no caller-selected owner/artifact parameters, one-active-job and
  24-hour-rate-limit and three-attempt enforcement text, lease-fencing
  text in claim/complete/fail, expire-before-cleanup and
  never-resurrect text, content-free audit metadata, no dynamic SQL/grant
  text, rollback drop-order and data-safety, and registry
  shape/prerequisite-ordering.
- `python -m unittest -q tests.test_package_registry tests.test_governance_pointers tests.test_delivery_preflight` —
  149 tests, unaffected by this package's surfaces.
- The full `tests/test_*_migration*.py` set — 454 tests (5 skipped: the
  live-database two-connection gate classes that require
  `PS_WORKSHOP_*_SQL_GATE`/`PS_OPPSLATE_*_SQL_GATE` environment variables
  this environment does not set).
- `git diff --check` — no whitespace errors.
- `scripts.migration_registry.executable_sha256` was called directly
  against the forward file to compute the exact digest the recorded gate
  proof matches:
  `767e8509fcd7b8933157cfa331e85b3395a6043a2d4506ed0912166904b84917`.
  `scripts.migration_registry.load_registry` was also called directly to
  confirm the appended entry parses and both referenced files resolve.

**Executed — governed gate proof (gate round, 2026-08-28):**

- `scripts/govern_sql_migrations.py gate` ran against the disposable
  database `ps-migration-path-20260828` on `peerslate` (created Basic-tier
  for the proof, deleted afterwards): prerequisite replay
  (PS-PLAT-000…PS-AUTH-001) onto the empty database, forward apply
  (50 objects), idempotent re-apply, rollback rehearsal, and forward
  re-apply all passed. The proof is recorded in the registry entry's
  `gate` block (`gated_at_utc 2026-08-28T18:58:43Z`), so
  `scripts/govern_sql_migrations.py`'s governed apply path
  no longer refuses this migration for want of a gate; actually applying
  it anywhere real remains separately authorized (C4). (The separate
  legacy `scripts/apply_sql_migrations.py` is not gate-aware — it applies
  only from its own hardcoded `MIGRATION_FILENAMES` tuple, which does not
  list this file; it neither applies nor refuses it, it simply does not
  know it exists.)

**Column and behavior truth notes (recorded for C2/C3):**

- `updated_at_utc` is create-time-only: no procedure or trigger ever
  rewrites it after insert. `row_version` is the real change marker; a
  future reader must not treat `updated_at_utc` as last-transition time.
- `usp_ClaimAccountExportJob` has no owner-active predicate: a job queued
  by a member who is then deactivated will still be claimed and assembled.
  C2 must honour C0's "authorization is no longer valid" expiry trigger on
  the worker side before any artifact is stored (explicit C2 obligation).
- Status reads report `state = 'ready'` for a job past
  `ready_expires_at_utc` until the expiry sweep runs; the
  `download_available` bit is already 0 in that window and agrees exactly
  with the download procedure's predicate, so no download is ever promised
  and refused — but the state string itself lags the sweep.
- In the request procedure's duplicate-race CATCH, a competing job that
  reaches `ready` between the unique-index violation and the CATCH lookup
  (which filters `queued`/`running`) leaves the race unresolved and the
  raw 2627 surfaces. Vanishingly rare; a later slice may widen the CATCH
  lookup to ready-before-expiry.
**Not executed:**

- **No two-member isolation proof, no lease-recovery/lock-timeout proof, no
  concurrent-race proof, no compressed/uncompressed size or timeout
  failure proof.** The gate proved apply, idempotent re-apply, rollback,
  and re-apply only. These behavioural proofs from C0's "exact future
  proof plan" items 1–2 were not written or exercised — no verification
  script exists in this candidate (it is outside the frozen claim
  surfaces) — not because the disposable-database infrastructure was
  unreachable; it was reached for the gate.
- **No grant apply, no role creation, no worker identity.** This is a
  deviation from the claim's own outcome wording, not an exclusion the
  claim specifies — the C1 lane claim's `outcome` text names
  "least-privilege grants" as part of what C1 delivers, and this candidate
  delivers the grant *model* (documented above) but applies no `GRANT`,
  `CREATE ROLE`, or `CREATE USER` statement anywhere. The reason is
  environmental, not a scope decision: the governed apply identity that
  runs this migration holds `db_ddladmin` only and cannot create a role or
  grant `EXECUTE` (see "Grant model" above). Binding the actual grants
  therefore requires the same separate, later, administrator-run authority
  operation the PS-INTERVIEW-AI-EXTRACT-001 house pattern uses — it could
  not be done inside this migration file under any writer's identity, not
  only this one's.

## C2/C3 considerations (advisory, not fixed in C1)

Two procedure behaviors are worth a future experience layer's attention;
neither is a C1 defect the reviewer required fixing, and both are recorded
here rather than changed, since changing either touches error-handling
behavior a future C3 experience contract should own deliberately:

- **`usp_RequestAccountExportForOwner` throws (error 57211) when a
  signed-in caller's identity cannot be resolved** — e.g. a session that
  outlives the member being deactivated or deleted mid-session. Every
  other `*ForOwner` write procedure in this repository (`usp_CreateCapture`,
  the Workshop edit procedure) throws identically on unresolved identity,
  so this matches house convention, but it does mean a deactivated-mid-
  session caller sees a raw server error from the request endpoint rather
  than a graceful "sign in again" experience. C3 should decide whether the
  application layer catches this specific case before it reaches the
  member.
- **`usp_CleanupAccountExportJob` throws (error 57256) "Unknown export
  job" for a job key that does not exist**, which is a mild existence
  oracle: a caller can distinguish "no such job" from every other refusal
  reason. This is low risk because the procedure is worker-only (no
  `@UserKey`, intended for the future dedicated worker identity, never
  exposed to a browser or a member-facing route) — unlike the owner
  procedures, which deliberately return the same neutral empty result for
  unknown/foreign/unauthorized rather than distinguishing any case.

## Production apply is deferred to C4

This migration has been applied only to the disposable gate database
`ps-migration-path-20260828` (created for the proof, deleted after); it has
never been applied to staging or production. `production_authority` on the C1 lane claim is `"withheld"`.
Per C0's Protected child sequence, C4
(`PS-SETTINGS-ACCOUNT-EXPORT-RELEASE-PROOF-001`) alone can assemble
exact-`main`/deployed-SHA release proof and separately authorized schema
apply, after C1–C3 are each independently accepted on their own merits. A
repository merge of this candidate — even after independent review — grants
no schema operation, resource creation, identity/grant, schedule, or
production deployment by itself, matching the standing rule stated in C0's
"Protected child sequence" table.
