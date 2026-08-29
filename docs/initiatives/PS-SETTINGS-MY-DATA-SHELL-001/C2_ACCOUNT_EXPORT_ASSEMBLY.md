# C2 account export assembly

**Package:** `PS-SETTINGS-ACCOUNT-EXPORT-ASSEMBLY-001`
**Slice:** C2 — Protected, private artifact and workload design
**Depends on:** accepted C1 (`docs/initiatives/PS-SETTINGS-MY-DATA-SHELL-001/C1_ACCOUNT_EXPORT_FOUNDATION.md`,
independent review PASS,
`docs/governance/lane_claims/receipts/PS-SETTINGS-ACCOUNT-EXPORT-FOUNDATION-001.json`)
and accepted C0 (`C0_ACCOUNT_EXPORT_ARCHITECTURE.md`).
**Status:** Candidate implementation, self-reviewed by the writer, corrected
through two independent-review rounds, and gate-run by the manager. This
writer's own commits made no Azure resource, workload identity, grant,
network call, or database call directly. Since this candidate was first
pushed, the manager separately (a) ran the governed gate against the
corrected owner-isolation script, which now records `verified = 1` in
`SQL FIles/Migrations/registry.json`'s gate block, and (b) provisioned part
of C0's required C2 resources under the owner's program authorization: the
private container `peerslate-private-account-export` (on storage account
`peerslatecapturemedia`) and the dedicated workload identity
`peerslate-account-export-worker` now exist. See "Azure actions" below for
the complete provisioning state, including the two grant layers that remain
pending. Every Python-level proof in this document (assembly, storage,
worker helpers) remains a static/offline unit proof only: no adapter method
has been exercised against the real container, because
`EXPORT_BLOB_ACCOUNT_URL` is not yet configured and both required grant
layers are still pending.

## Decision

C2 builds the private-artifact adapter, the deterministic archive assembler,
and the worker entry point C0's "C2 private artifact and workload design"
section names, plus the owner-isolation verification script C1 recorded as a
transferred obligation. It creates no Azure container, workload identity,
grant, or schedule — those remain a separate, later, owner-authorized
provisioning action (see "Azure actions" below). It reads no real member
domain data: the assembler is exercised only against an injected iterable of
already-shaped fixture domain files, because no domain-reader slice has been
separately claimed or approved yet (C0's V1 domain matrix).

## Storage design (`services/account_export_storage_service.py`)

A private Azure Blob adapter, matching the existing house pattern
(`services/capture_media_storage_service.py`, `services/media_storage_service.py`,
`services/community_media_storage.py`): lazy `ContainerClient` construction,
`DefaultAzureCredential` (Microsoft Entra managed identity), no account-key
fallback, a stable `AccountExportStorageError(code)` exception carrying only a
short code, never an object name, URL, or provider response body.

**Object layout**, both paths built only from the server-issued `job_key`
(already an opaque `uniqueidentifier`) and a bounded attempt ordinal
(1–3, matching `CK_account_export_jobs_attempts`):

| Purpose | Path shape | Notes |
| --- | --- | --- |
| Staging | `export/v1/staging/<job_key>/<attempt>.zip.part` | One object per job **and** attempt. Never downloadable — nothing in this adapter or its callers ever exposes this name outside the private container. |
| Final | `export/v1/final/<job_key>.zip` | One per job, ever. Created once (`overwrite=False`) and never replaced; a second promotion attempt for the same job is refused (`storage_conflict`), matching the ledger's own "one artifact per job" shape. |

**Staging and promotion contract:**

- `stage(job_key, attempt, data)` uploads the complete archive once
  (create-only). It independently checks the compressed cap before ever
  calling the Blob SDK, so an oversize payload never reaches an upload
  attempt. Its return value (`None`) is deliberately not authoritative.
- `promote(job_key, attempt)` is the **only** source of the facts committed to
  the C1 ledger. It downloads the staged object back, cross-checks the
  downloaded length against the provider-reported size, recomputes SHA-256
  over the downloaded bytes, opens the downloaded bytes as a ZIP to confirm
  `manifest.json` is present and to recompute the uncompressed total (see
  "Determinism and the uncompressed-size definition" below), re-checks both
  caps, uploads exactly those verified bytes to the final path, and only then
  attempts to delete the staging object. There is no parameter path that lets
  a caller assert a hash or size and skip this independent recomputation —
  promotion is structurally impossible without it. **The staging-cleanup
  delete is best-effort** (`try`/`except AccountExportStorageError: pass`):
  by the point cleanup runs, the final object is already committed, so a
  transient delete failure must never be reported as a failed promotion —
  that would fail an already-`ready`-bound job, and every retry of that
  attempt would then hit `storage_conflict` against the orphaned final object
  (`overwrite=False`) until attempts ran out. Matches the worker's own
  best-effort treatment of its cleanup-on-failure call (below).
- `cleanup_staging(job_key, attempt)` and `cleanup_final(job_key)` are
  idempotent deletes (absence is success, matching every existing media
  adapter's `delete()`). This adapter has no state-machine awareness of its
  own; the caller (the worker) must only reach `cleanup_final` after the C1
  ledger has already moved the job past `ready` — exactly what
  `usp_CleanupAccountExportJob`'s own refusal-while-`ready` guard enforces on
  the database side.
- `assert_container_access()` mirrors `community_media_storage.py`'s own
  preflight (a bare `get_container_properties()` call, no content read).

**No SAS, no URL, ever.** This adapter never imports or calls
`generate_blob_sas`, `generate_container_sas`, or any user-delegation API —
verified structurally in `tests/test_account_export_storage.py` by reading
the module's own source text, not only by behavior. `final_artifact_reference`
(the value `promote()` returns as `reference`) is an opaque relative path
(e.g. `export/v1/final/<job_key>.zip`), never a URL — `CK_account_export_jobs_artifact_not_url`
enforces the same rule at the schema layer. It is a private, server-only
locator for a future internal proxy download (C3); nothing in C2 serves it to
a browser.

**Config (added to `.env.example`, mirroring the `CAPTURE_MEDIA_BLOB_*`
convention):**

| Name | Default if unset | Purpose |
| --- | --- | --- |
| `EXPORT_BLOB_ACCOUNT_URL` | `""` (adapter refuses with `storage_unavailable`) | The private export container's account URL. |
| `EXPORT_BLOB_CONTAINER` | `peerslate-private-account-export` | The dedicated private container name. Public access must be disabled at provisioning time (a manager/owner action, not something this code can assert). |

## Assembly design (`services/account_export_assembly_service.py`)

Implements C0's "Archive and consistency contract" against fixture input only.
Holds no state, performs no I/O, imports no database or storage module.

**Manifest** (`manifest.json`, always the ZIP's first physical member):

```json
{
  "format": "peerslate.account.export",
  "schema_version": 1,
  "job_key": "...",
  "requested_at_utc": "...",
  "assembly_started_at_utc": "...",
  "assembly_cutoff_at_utc": "...",
  "consistency_marker_start": "... or null",
  "consistency_marker_cutoff": "... or null",
  "files": [ { "path": "...", "domain_code": "...", "schema_id": "...",
                "schema_version": 1, "disposition": "included|excluded|unavailable",
                "byte_length": 0, "record_count": 0, "sha256": "...",
                "provenance": {}, "read_window": {}, "omission_reason": null,
                "failure_reason": null } ]
}
```

- **Key order is fixed** (the order shown above, both at the top level and
  within each file entry) via literal dict construction plus
  `json.dumps(..., separators=(",", ":"))` — no `sort_keys`, no incidental
  whitespace. `files` maps roughly 1:1 onto C1's (unpopulated)
  `dbo.account_export_job_domains` columns for a future domain-reader slice's
  benefit: `domain_code`→`domain_code`, `schema_id`→`schema_identifier`,
  `sha256`→`content_sha256`, `byte_length`→`byte_count`,
  `read_window`→`read_started_at_utc`/`read_ended_at_utc`.
- **Every domain is listed, not only included ones.** An `excluded` or
  `unavailable` entry still appears in `files` (with its reason and no
  content facts) so a future reader can tell an intentional v1 exclusion from
  a runtime failure, per C0's domain matrix note. Only `included` entries
  have a corresponding ZIP member at `path`.
- **Disposition shape is enforced exactly like C1's
  `CK_account_export_job_domains_shape`:** `included` requires `content`
  (bytes) and `record_count`, forbids either reason; `excluded` forbids
  content/record_count/`failure_reason`, requires `omission_reason`;
  `unavailable` forbids content/record_count, requires **exactly one** of
  `omission_reason`/`failure_reason`. A shape violation raises
  `AccountExportAssemblyError("invalid_domain_input")` before any bytes are
  produced.
- **SHA-256 and byte length are always recomputed** from the actual `content`
  bytes for each included file, and again for the whole archive — never
  trusted from caller input.
- **Path safety:** no leading `/`, no `..` segment, and no domain may claim
  the reserved `manifest.json` path; duplicate paths are refused.

**Determinism.** Two calls with identical input produce byte-identical
output — proved in `tests/test_account_export_assembly.py` by building twice
and comparing archive bytes, SHA-256, and the manifest dict. This requires
pinning everything a naive ZIP write would let vary: a fixed 1980-01-01
`ZipInfo.date_time` (not wall-clock time), a fixed `create_system` (not the
build host's platform), a pinned `external_attr` (`0o600 << 16` set
explicitly — writing `0` does not pin anything, since
`zipfile.ZipFile` silently substitutes that exact value for any falsy
`external_attr`), a fixed compression method,
and the JSON encoding rules above. Archive member order is manifest.json
first, then every included domain file in ascending lexical `path` order —
computed in a first pass (hashing every file's content) before any ZIP bytes
are written, specifically so manifest.json does not have to be rewritten
after the fact to be first.

**Determinism and the uncompressed-size definition.** `uncompressed_size_bytes`
is defined as the sum of every archive member's uncompressed size **except**
`manifest.json` — i.e. exactly the exported domain content total. This
matters because it is the same quantity the in-progress cap check tracks
while building (a running total of included file content lengths); if the
final figure instead included manifest.json's own (small, but
input-size-dependent) overhead, a value that passed the incremental check
during the loop and a value recomputed afterward from the finished archive
could disagree by a few bytes. `AccountExportStorageService.promote()`
recomputes this identical definition (summing every member except
`manifest.json`) from its own independent readback, so a happy-path value
this service reports and the value storage recomputes from what is actually
persisted always agree exactly.

**Caps.** Both C0 caps (100 MiB compressed, 250 MiB uncompressed) are
constructor/call-time overridable (`max_compressed_bytes`,
`max_uncompressed_bytes`) so tests can prove exact boundary behaviour without
allocating hundreds of megabytes. Compressed enforcement runs twice: once
incrementally after every ZIP write (an early, cheap abort for a clearly
oversize run) and once, authoritatively, against the complete archive's true
final length — the incremental check alone would miss an archive that only
tips over the cap once the ZIP's central directory is appended at close time,
which happens after the last incremental check point.

## Worker design (`scripts/run_account_export_worker.py`)

A bounded, hand-run script — **not wired to any scheduler, route, or UI.**
Sequence: claim exactly one job → enforce owner-active → assemble a
fixture-only archive → stage and promote it → complete or fail the job.

- **Claim:** `usp_ClaimAccountExportJob`, no parameters. When nothing is
  claimable the procedure produces no result set at all (a bare `RETURN`
  before any `SELECT` — the same shape `C1_ACCOUNT_EXPORT_FOUNDATION.md`
  records for the status procedure's unresolved-identity path); the worker
  checks `cursor.description is None` explicitly rather than calling
  `fetchone()` blind.
- **Owner-active enforcement (the C1→C2 obligation).**
  `usp_ClaimAccountExportJob` has no owner-active predicate — a job queued by
  a member later deactivated would otherwise still be assembled and stored.
  **No new procedure is possible under this claim's frozen surfaces**, so
  `is_owner_active()` runs a direct, parameterized `SELECT` against
  `dbo.app_users`/`dbo.member_profiles` (the exact `active` predicate
  `usp_RequestAccountExportForOwner` already trusts), applied to the claimed
  job's already-resolved `owner_user_id`/`owner_profile_id`. This is the
  **sanctioned interim mechanism**; a later slice may formalize it as a
  dedicated procedure once one can be claimed. On an inactive owner: the
  worker calls `usp_FailAccountExportJob` with `domain_unavailable` (see
  "Failure code choice" below) and performs **no storage write of any kind**
  — `stage()` is never called. This is by design an ordinary attempt failure,
  not a distinct "permanently blocked" outcome: `usp_FailAccountExportJob`
  requeues to `queued` while attempts remain, so a still-inactive owner's job
  is reclaimed, rechecked, and failed the same way up to three times before
  finally terminating — the closed procedure set has no separate signal for
  "never retry this."
- **The owner-active check-then-act race is acceptable.** Nothing prevents
  the owner from being deactivated in the instant between `is_owner_active()`
  succeeding and the storage write that follows it. This is tolerated because
  `usp_GetAccountExportDownloadMetadataForOwner` independently re-checks
  `app_users.active = 1 AND member_profiles.active = 1` when resolving the
  caller at download time — a since-deactivated owner can never actually
  retrieve an artifact this race let through, regardless of what the worker
  did. The worst case is wasted assembly/storage work, not a disclosure.
- **Dedicated worker SQL identity, not `services/database_service.py`.**
  That module's `ALLOWED_PROCEDURES` allowlist is outside this claim's frozen
  surfaces and does not list any of the eight account-export procedures. Even
  if it did, C1 records the five worker procedures as reserved for "a future
  dedicated worker identity...distinct from the application and maintenance
  identities" — reusing the shared application connection would contradict
  that. The worker instead opens its own connection directly via
  `mssql_python.connect()`, reading a new, dedicated
  `ACCOUNT_EXPORT_WORKER_SQL_CONNECTIONSTRING` environment variable, exactly
  the `scripts/interview_ai/run_interview_telemetry_purge.py` house pattern
  for a maintenance-class script that owns its own connection string. No SQL
  grant, role, or identity is created by this package — binding the actual
  `EXECUTE` grants for that future identity remains the same later,
  administrator-run authority operation C1 already named.
- **Consistency markers.** The worker reads `SELECT @@DBTS` on its own
  connection immediately before and after assembly and passes both values
  through to the manifest and to `usp_CompleteAccountExportJob`. This is a
  database-internal counter read, never a domain reader — it names no member
  table.
- **`requested_at_utc`.** `usp_ClaimAccountExportJob`'s own result columns
  are `job_key`, `owner_user_id`, `owner_profile_id`, `attempt_count`,
  `lease_token`, `lease_expires_at_utc` only — it does not return
  `requested_at_utc`. The worker fetches it with a second, direct,
  `job_key`-scoped `SELECT` (`fetch_requested_at_utc`), the same
  sanctioned-interim-read shape as the owner-active check: job ledger
  metadata only, no `@UserKey`, no member content.
- **Failure code choice for owner-inactive: `domain_unavailable`.**
  `usp_FailAccountExportJob`'s closed enum has no code that names
  authorization directly. C0's trust boundary treats an owner whose
  authorization is no longer valid as making every domain's read contract
  unsatisfiable at once ("A domain that cannot satisfy its contract is
  unavailable or excluded before readiness"). Among the seven codes the
  procedure accepts, `domain_unavailable` is the closest true statement:
  the owner's deactivation makes the complete requested domain set
  unavailable — it is not an internal bug (`internal_error`) and not an
  infrastructure shortage (`worker_unavailable`).
- **Staging cleanup on failure.** On any exception during assembly, staging,
  or promotion, the worker makes a best-effort `cleanup_staging(job_key,
  attempt)` call before failing the job. This is always safe to attempt
  (idempotent, absence is success) regardless of whether `stage()` was even
  reached, and it prevents an abandoned attempt's bytes from lingering in the
  private container indefinitely; no procedure in this claim's frozen
  surfaces can set `cleanup_state` for a `failed` row, so this cleanup is not
  reflected in the ledger — only in the container actually being clean. A
  cleanup failure here is logged and swallowed; it never masks the real error
  or blocks the `usp_FailAccountExportJob` call that follows.
- **Hash verification after promotion.** `verify_promoted_hash()` compares
  `promote()`'s independently-recomputed SHA-256 (from what is actually
  persisted) against the assembly service's own pre-upload SHA-256, and
  raises `AccountExportStorageError("hash_mismatch")` on any disagreement —
  a corrupted-in-transit archive is never completed as `ready`. This makes
  `hash_mismatch` actually reachable: without this comparison the code
  declared and mapped that failure code but nothing in the worker could ever
  produce it, since `promote()`'s own internal checks already guarantee
  internal self-consistency of whatever it returns, never agreement with a
  second, independently-computed value.
- **All other failures** funnel through `choose_failure_code_for_error()`,
  which preserves an adapter's own more specific code
  (`oversize_compressed`/`oversize_uncompressed`/`hash_mismatch`), maps a
  storage-unavailable condition to `worker_unavailable`, and otherwise
  defaults to `internal_error`. If the attempt whose lease has already been
  reaped by the time the worker tries to fail it (`usp_FailAccountExportJob`
  refuses with the same lease-fencing error `usp_CompleteAccountExportJob`
  uses), the worker logs that refusal and stops — there is nothing more a
  lease-less attempt can safely do.
- **Truthful post-failure logging.** `usp_FailAccountExportJob` requeues to
  `queued` (retaining the failure code) while `attempt_count` is below its
  hardcoded `@MaxAttempts = 3`, and only terminates to `failed` once attempts
  are exhausted. The worker's `post_fail_state(attempt)` reflects that
  exactly rather than logging a hardcoded `state="failed"` for every call —
  a job requeued on attempt 1 is not yet terminal, and a log claiming
  otherwise would misreport the ledger.
- **`requested_at_utc` never fabricated.** If `fetch_requested_at_utc`
  somehow reads back `NULL` (unreachable today — the column is `NOT NULL`),
  the worker fails the job loudly rather than silently substituting the
  assembly start time. C0's no-false-promise rule ("`requested_at_utc` is
  when the member asked, not a false promise") forecloses ever reporting a
  fabricated request time in the manifest, even defensively.
- **Content-free logging.** Every log line passes through
  `content_free_log_fields()`, which keeps only an explicit allowlist
  (`job_key`, `state`, `attempt`, both size counts, `file_count`,
  `failure_code`, `error_type`, `stage`) and silently drops anything else —
  so a future call site cannot leak a new field into a log line merely by
  forgetting to widen the allowlist first.
- **FIXTURE WARNING.** No domain-reader slice exists. `build_fixture_domain_files()`
  is the worker's own hardcoded, obviously-synthetic fixture set (one
  `included`, one `excluded`, one `unavailable` entry, exercising all three
  disposition shapes). Running this worker against a database that might
  hold a **real** member's queued export request would complete that request
  with fake placeholder content — a genuine trust violation, not merely an
  incomplete feature. `main()` refuses to run at all unless a new environment
  variable, `ACCOUNT_EXPORT_WORKER_FIXTURE_MODE_CONFIRMED`, is explicitly set
  to a true value, on top of the existing `--expect-database` guard. This
  worker must not be pointed at any database that could contain a real
  member-requested job until a real, separately-claimed domain-reader slice
  replaces the fixture path.

**Config added to `.env.example`:**

| Name | Default if unset | Purpose |
| --- | --- | --- |
| `ACCOUNT_EXPORT_WORKER_SQL_CONNECTIONSTRING` | unset (worker refuses to start) | The worker's own dedicated SQL connection string. Never the application's `AZURE_SQL_CONNECTIONSTRING`. |
| `ACCOUNT_EXPORT_WORKER_FIXTURE_MODE_CONFIRMED` | `false` (worker refuses to start) | Explicit tripwire acknowledging every job this worker completes today uses synthetic fixture content, never real member data. |

## Owner-isolation verification (`SQL FIles/Verification/PS-SETTINGS-EXPORT-001_owner_isolation_verify.sql`)

The C1-recorded transferred obligation. Written to the same house
structure/THROW discipline as the sibling `*_owner_isolation_verify.sql`
files (two synthetic owners via `usp_UpsertAppUserFromAuth`, one outer
always-rolled-back transaction, unique `THROW` numbers in the `57700`–`57735`
block — clear of every other verification file's range and of the migration's
own `57200`–`57257` procedure-error range). It proves: the procedure-shape
grep across all three owner procedures; that only the download-metadata
procedure ever discloses `final_artifact_reference`; forged-UserKey and
guessed/forged-JobKey neutrality; foreign-owner reads refused in both
directions while queued; download metadata refused for a not-yet-ready job;
download metadata granted only for the owner's own ready, unexpired job and
refused for the foreign owner; a reauthorized owner's truthful `expired`
status with download access revoked; and that a second owner's unrelated job
is undisturbed throughout.

**This script never calls `usp_ClaimAccountExportJob` or
`usp_ExpireAccountExportJobs`.** Both are system-wide (no `@UserKey`, no
owner predicate) and, in a production-safe run against a database that may
hold real unrelated jobs, could claim or expire a row this script did not
create. The `running` and `ready` states it needs are instead reached by a
direct `UPDATE` scoped to exactly the synthetic `job_key` just created,
followed by the real, lease-fenced `usp_CompleteAccountExportJob` (which can
only ever touch the one row matching both `job_key` and the lease token this
script itself generated); the `expired` state is reached the same
`job_key`-scoped direct-`UPDATE` way. This script also does **not** attempt
to re-call `usp_CompleteAccountExportJob` a second time to prove its own
lease fencing: that procedure's `CATCH` block issues an unqualified
`ROLLBACK TRANSACTION` on error, which — invoked from inside this script's
own still-open outer transaction — would unwind everything the script had
built so far (both synthetic owners and jobs), not only the nested call's own
scope. Lease fencing itself is already covered by
`tests/test_settings_account_export_migration.py`'s static assertions; this
script's job is owner isolation.

**Correction round (gate finding): no `INSERT ... EXEC` against a
ROLLBACK-capable procedure.** The first governed gate run against this script
failed at the verification step with `Cannot use the ROLLBACK statement
within an INSERT-EXEC statement` — T-SQL refuses to let `INSERT ... EXEC`
target any procedure that can reach a `ROLLBACK TRANSACTION` statement, even
on a call that never actually takes that branch. The original script used
`INSERT @Table EXEC ...` for `usp_RequestAccountExportForOwner` (twice) and
`usp_CompleteAccountExportJob` (once), both of which have a `CATCH` block
that can reach `ROLLBACK TRANSACTION`. Fixed by calling both **bare**
(`EXEC dbo.usp_...;` with no capturing `INSERT`) and confirming their effect
with a direct `SELECT`/`EXISTS` against `dbo.account_export_jobs` afterward
instead of reading the procedure's own returned result set — each synthetic
owner's `profile_id` is guaranteed unique for the run, so a `queued` (or
`ready`) row for that exact `profile_id`/`job_key` can only be the one this
script itself just created. `INSERT ... EXEC` remains in use only for the two
read-only procedures (`usp_GetAccountExportStatusForOwner`,
`usp_GetAccountExportDownloadMetadataForOwner`), and section 0 of the script
now also greps both bodies for `ROLLBACK` and throws if either one is ever
found — a structural guard against a future edit silently reintroducing this
exact failure by adding transaction control to either procedure.

**Not run by this package.** Per the writer brief, this candidate does not
execute this script and does not touch `SQL FIles/Migrations/registry.json`.
The manager pairs this script with a fresh `PS-SETTINGS-EXPORT-001` gate run
and records the result there.

**Since gate-executed and now SEALED.** The manager's paired gate run
executed the corrected script and recorded `verified = 1` in the registry's
gate block (see the completion report's "Correction round 2"). Because the
gate rehearsed this exact text, the file is now sealed — it may not be
edited again without desynchronizing the rehearsed text from the shipped
text, the same principle as a sealed migration file. One residue of this:
`THROW` number `57724` does not appear anywhere in the file. It was used by
a "prove lease fencing by forcing a second completion" test in an earlier
draft, removed during the first correction round (see "Correction round
(gate finding)" above) because that call pattern risked an unqualified
`ROLLBACK TRANSACTION` unwinding the script's own outer transaction. The gap
is recorded here rather than closed by renumbering, because the script is
sealed and renumbering an already gate-rehearsed file is exactly the kind of
edit sealing forecloses.

## What is fixture-proven vs unproven

**Proven (offline, this candidate):**

- Deterministic, byte-identical archive assembly for identical fixture input;
  manifest completeness, ordering, and disposition-shape discipline; cap
  enforcement at the exact boundary and one byte over, for both the
  compressed and uncompressed caps; no unlisted archive bytes.
- Storage promotion is blocked whenever an independent readback cannot verify
  the staged bytes (missing object, size mismatch, no `manifest.json`,
  uncompressed total over cap); staging and final cleanup are idempotent; no
  method can return or log a URL or SAS, checked both behaviourally and by a
  static source-text grep for SAS-issuing APIs; storage error codes never
  embed an object name, account URL, or container name.
- The worker's owner-active gate and closed failure-code mapping are pure,
  unit-tested functions exercised with fake DB cursors — never a real
  connection.
- The full `PS-SETTINGS-EXPORT-001` migration's structural contract (already
  established by C1) is unaffected and stays green.

**Not proven by this candidate:**

- **No live database call by this writer.** The owner-isolation SQL script
  has since been executed by the manager's own paired gate run, which
  recorded `verified = 1` in `SQL FIles/Migrations/registry.json`'s gate
  block — but that live proof belongs to the manager's gate, not to anything
  in this document or its offline tests, which remain static/offline only.
- **No live Blob Storage call by this writer or by any test.** Every storage
  test uses a fake container/blob double. The private container
  `peerslate-private-account-export` now exists (manager-provisioned, see
  "Azure actions" below), but no adapter method has been exercised against
  it — both required grant layers remain pending and
  `EXPORT_BLOB_ACCOUNT_URL` is not yet configured, so every adapter method
  still fails closed today.
- **No live end-to-end worker run.** `scripts/run_account_export_worker.py`
  has never been executed against a real database or container by this
  candidate — only its pure helper functions are unit-tested.
- **No real export content.** Every domain file this worker or its tests use
  is an obvious synthetic placeholder. No domain-reader slice exists; nothing
  in this package makes a real account export available, live, or usable by
  a member. There is still no route, UI, or scheduled trigger anywhere in the
  repository that could reach this code from a real request.

## Azure actions: provisioning state

This writer's own commits created **no** Azure resource, workload identity,
role assignment, or network call, and ran **no** `az` command — every
adapter method was written to fail closed (`storage_unavailable`) until
`EXPORT_BLOB_ACCOUNT_URL` is configured, and nothing in the code assumed
provisioning had happened.

Since this candidate was first pushed, the manager separately provisioned
part of C0's required C2 resources under the owner's recorded program
authorization (ref
`session:01a03e17-a645-7ae0-8da3-164eef90a333/owner-direction:2026-08-28/PS-SETTINGS-ACCOUNT-EXPORT-C1-C4-END-TO-END`):

- the private container `peerslate-private-account-export` EXISTS on storage
  account `peerslatecapturemedia` (container `publicAccess` null; account
  `allowBlobPublicAccess` false — private at both levels);
- the dedicated workload identity `peerslate-account-export-worker` EXISTS
  (clientId `b84a0485-0d6f-4338-9575-5250faac934b`, principalId
  `e6a73ef9-8b70-4920-8726-cbf64ea21563`).

**Both required grant layers remain pending**, exactly as C0 requires ("C2
requires a separate owner approval for resource, provider spend, private
container, workload identity, grants, scheduler, and cleanup"):

- the identity's container-scoped `Storage Blob Data Contributor` role — the
  manager's harness declines permission-granting actions on its own
  authority, so this awaits the owner;
- the SQL-side contained user and least-privilege `EXECUTE` grants on the
  five worker procedures, which require the AAD-admin authority path.

Nothing in this candidate's code assumes either grant has happened; every
adapter method still fails closed (`storage_unavailable`) because
`EXPORT_BLOB_ACCOUNT_URL` is not yet configured, and no worker schedule
exists.

## Protected child sequence

This package is C2 in C0's Protected child sequence
(`C0_ACCOUNT_EXPORT_ARCHITECTURE.md`, "Protected child sequence" table).
Rollback is a repository revert of the files this candidate adds; there is no
runtime, data, schema, provider, configuration, resource, schedule, or
production state to reverse, because none was created. C3 (experience) and C4
(release proof) remain separately claimed, Protected packages with their own
independent review.
