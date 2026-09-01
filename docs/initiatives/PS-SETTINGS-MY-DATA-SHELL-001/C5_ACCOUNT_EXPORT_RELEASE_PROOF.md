# C5 account export release and operational proof

**Package:** `PS-SETTINGS-ACCOUNT-EXPORT-RELEASE-PROOF-001`
**Position:** This is C0's **C4 child** (`C4
PS-SETTINGS-ACCOUNT-EXPORT-RELEASE-PROOF-001` in
`C0_ACCOUNT_EXPORT_ARCHITECTURE.md`'s Protected child sequence). It uses
`C5_*` filenames because the `C4_*` filenames belong to the closed
domain-ledger package (`PS-SETTINGS-ACCOUNT-EXPORT-DOMAIN-LEDGER-WRITER-001`);
reusing them would overwrite a closed package's record.
**Owner authorization:** `pete-chat-2026-09-01/five-through-nine`
(production gates 6-9). **Gate 10 — feature enablement and live member
proof — is NOT authorized here**: `PEERSLATE_ACCOUNT_EXPORT_ENABLED` is
never set anywhere by this package.
**Status:** Gates 6-9 executed and proven. Both owner-executed role
grants (worker AcrPull; web-app Storage Blob Data Reader) landed
2026-09-01 and are verified live; no pending-owner item remains.

Truthful-state rule used throughout: **merged is not deployed; deployed
dark is not enabled.** After gate 9 the export code is live but every
export route returns 404 because the flag is absent. Run 2221 is the
current live release, re-verified at re-freeze (see Gate 9).

## Gate ledger

| Gate | What | State | Evidence |
| --- | --- | --- | --- |
| 5a | EXPORT-010 disposable-gate proof | Done before this package (coordinator) | `SQL FIles/Migrations/registry.json` on main: gated 2026-09-01T10:29:04Z, db `ps-export-c4-gate-20260901-a4`, verified=1 |
| 5b | EXPORT-010 production apply | Done before this package (coordinator) | Pipeline run 2212 (source main 13de7eb2); `usp_CompleteAccountExportWithDomains` present in `peerslate-database`; this package regenerated `docs/governance/PRODUCTION_SCHEMA_STATE.md` from a live governed read (below) |
| 6 | Worker SQL identity grants | **Done** 2026-09-01 | §Gate 6 |
| 7 | Worker host + scheduler | **Done** 2026-09-01 (both jobs proven live) | §Gate 7 |
| 8 | Storage container verification | **Done** 2026-09-01 (web Reader grant landed same day; verified live) | §Gate 8 |
| 9 | Production web deploy (dark) | **Done** 2026-09-01, run 2221, live dark (re-verified at re-freeze) | §Gate 9 |
| 10 | Enablement + live member proof | **Not authorized; not performed** | §Gate 10 checklist |

## Gate 6 — worker SQL authority

Script: `scripts/configure_account_export_worker_sql_authority.py`
(plan|apply|verify, ActiveDirectoryDefault, content-free JSON, SID computed
from the identity's client ID via `UUID.bytes_le` — never transcribed).
Independent pre-execution review preceded any production apply:
- CLEAR on `ad1d8e344ef6104a09b08b46aebaa7f54fa246ee`
  (`agent:review-ps-settings-account-export-release-proof-001:ad1d8e34:sql-authority-grant`);
- three low findings taken (tripwire pins, callerless-grant drop,
  stale-SID note), delta re-CLEAR on
  `f591be378e840fc1b555811c03d1ec4524361701`
  (`agent:review-ps-settings-account-export-release-proof-001:f591be37:sql-authority-grant-delta`);
- apply executed from the reviewed tree at exactly `f591be37`.

Grant model (exact set, verified by set equality, not subset):

- Contained `EXTERNAL_USER` `peerslate-account-export-worker` (UAMI client
  ID `b84a0485-0d6f-4338-9575-5250faac934b`), **zero** database role
  memberships.
- 5 lifecycle EXECUTEs: claim, complete-with-domains, fail, expire,
  cleanup. C1's original `usp_CompleteAccountExportJob` is deliberately
  NOT granted (pre-execution review finding, 2026-09-01): zero callers
  anywhere; least privilege wins over reserve; one-line re-add if a
  caller ever ships.
- 31 domain-reader EXECUTEs, enumerated at runtime from
  `services/account_export_domain_readers.py` (the worker's own module),
  never hand-typed.
- 3 column-scoped SELECTs — the sanctioned interim direct reads (recorded
  C1->C2 obligation; a later slice may formalize them as procedures):
  `app_users(id, user_key, active)`,
  `member_profiles(profile_id, user_id, active)`,
  `account_export_jobs(account_export_job_id, attempt_count,
  cleanup_state, job_key, requested_at_utc, state)`.

**Recorded deviation from the C4 scout runbook:** the runbook listed
`account_export_jobs(job_key, requested_at_utc)` only. Worker-ops
(`PS-SETTINGS-ACCOUNT-EXPORT-WORKER-OPS-001`) merged after that scout; its
maintenance sweep also reads `state`, `attempt_count`, filters on
`cleanup_state`, and orders by `account_export_job_id`, and SQL Server
column-level SELECT must cover predicate and ordering columns. The
six-column grant is the shipped worker's minimum. This is an accepted
interim deviation from a pure EXECUTE-only posture, stated here exactly as
the worker's own docstrings state it — the community-maintenance precedent
has zero table grants; this worker cannot.

Stale-principal remediation (reviewer operational note): if the worker
user pre-exists with a stale SID (identity recreated), the guarded
CREATE USER is a no-op and verify fails closed on the SID check; the
remediation is a deliberate manual `DROP USER` by the Entra admin, then
rerun apply. The script never drops a principal on its own.

Firewall window: transient rule `c4-operator-20260901` for the verified
operator egress IP, created 2026-09-01T13:38:28Z, deleted
2026-09-01T13:40:39Z (rule list re-confirmed back to exactly
`AllowAllWindowsAzureIps` + `Home Internet Address`). SQL work in this
package happened only inside that ~2-minute window.

- Plan (before apply), 2026-09-01: connectivity proven, exit 0 —
  `{"column_grant_count":12,"database":"peerslate-database","database_name_matches":true,"domain_reader_count":31,"expected_grant_count":49,"grants_missing":49,"grants_present":0,"grants_unexpected":0,"lifecycle_procedure_count":5,"principal":"peerslate-account-export-worker","principal_exists":false,"principal_sid_matches":null,"principal_type_external_user":null,"role_memberships":0,"status":"planned","target_objects_missing":0}`
  (`target_objects_missing: 0` independently confirms every granted
  procedure — including EXPORT-010's — and every granted column exists.)
- Apply + in-transaction impersonated exact-set verify,
  2026-09-01T13:39:20Z, exit 0 —
  `{"column_grant_count":12,"database":"peerslate-database","domain_reader_count":31,"lifecycle_procedure_count":5,"principal":"peerslate-account-export-worker","status":"verified"}`
- Plan (after apply, idempotence), exit 0 —
  `{"...":"...","expected_grant_count":49,"grants_missing":0,"grants_present":49,"grants_unexpected":0,"principal_exists":true,"principal_sid_matches":true,"principal_type_external_user":true,"role_memberships":0,"status":"planned","target_objects_missing":0}`
- Standalone `verify` from the operator shell refused with
  `{"error_type":"RuntimeError","status":"failed"}` — **by design, not a
  defect**: standalone verify is defined (like its community-maintenance
  precedent) to run under the worker principal's own runtime identity and
  refuses admin impersonation outside apply. The as-the-principal runtime
  proof is gate 7's first job execution; the in-transaction impersonated
  verify plus the exact plan-after counts above stand as the gate-6 grant
  proof.

## Gate 7 — worker host and scheduler

Host decision (scout options matrix, coordinator-approved option B cost):
**Azure Container Apps Jobs**, two jobs from one image pinned by digest.

- ACR (Basic): `peerslateacr` (admin user disabled; passwordless only),
  created 2026-09-01. Resource providers `Microsoft.ContainerRegistry`,
  `Microsoft.App`, and `Microsoft.OperationalInsights` were registered on
  the subscription first (free, mechanical prerequisite of the approved
  resource creation; first container workload in this subscription).
  Image `peerslate-account-export-worker:main-672d122855b2103fdfdd2257ed5e63e57f47944f`
  built by `az acr build` (run cj1, 1m51s) from a `git archive` of exactly
  main `672d1228` plus the Dockerfile (python:3.12-slim, matching CI's
  pinned Python; requirements-first layer; non-root user; no ENTRYPOINT —
  each job supplies its command). First build digest
  `sha256:b53f1bd4fb4684d63b2c2dbc0e823d675ada702d1bc80e32f39f3e054c4dc714`
  — later proven defective (missing `libltdl7`; see the defect bullet
  below) and superseded by the fixed digest both jobs pin.
  Worker UAMI `AcrPull` on the registry: **pending-owner** (verified
  absent including inherited; role grants are blocked for the agent by
  design) — job creation paused on it:

      az role assignment create \
        --assignee-object-id e6a73ef9-8b70-4920-8726-cbf64ea21563 \
        --assignee-principal-type ServicePrincipal \
        --role AcrPull \
        --scope /subscriptions/bd0ecf48-6940-4fd3-9687-3eaf72469d67/resourceGroups/peerslate/providers/Microsoft.ContainerRegistry/registries/peerslateacr

- Container Apps environment: `peerslate-jobs-env` (centralus),
  provisioning `Succeeded`.
- **AcrPull resolution:** the owner clicked the reported grant; verified
  live before job creation (exactly `AcrPull` for the worker UAMI on
  `peerslateacr`, including inherited). Pending-owner item resolved.
- Export worker job `peerslate-account-export-worker`: cron
  `*/5 * * * *`, command `python` + args array
  `[scripts/run_account_export_worker.py, --expect-database,
  peerslate-database]`, `--replica-retry-limit 0` (retry is the ledger's
  job: three bounded attempts, 15-minute lease; platform retry would
  double-count), replica timeout 600, parallelism 1, user-assigned
  identity with `AZURE_CLIENT_ID` env selector, secretless MSI SQL
  connection string carrying `Uid=<client-id>` (mssql-python's
  documented UAMI selector — recorded deviation from the scout
  runbook's Uid-less string), registry pull via the same UAMI.
- Retention maintenance job `peerslate-export-maintenance` (28-char
  name; the natural name exceeds the 32-char job-name limit): same
  digest-pinned image, args + `--maintenance`, cron `0 3 * * *`
  (daily 03:00 UTC). **Cadence decision recorded here:** CR11
  deliberately names no cadence (the runtime home was a separately
  gated owner decision); daily 03:00 UTC chosen under this package's
  gates authorization — expiry tolerance is day-granular (7-day ready
  window), one daily sweep keeps the retention promise while staying
  off peak hours.
- **Image defect found and fixed during proof (recorded honestly):**
  the first image (digest `sha256:b53f1bd4...`) failed at SQL connect
  with the driver's "Failed to load the driver" — `python:3.12-slim`
  lacks `libltdl.so.7`, which mssql-python's vendored Debian
  `libmsodbcsql-18.6` requires (proved by an in-container `ldd` probe;
  managed-identity token acquisition had already succeeded, isolating
  the failure to the native driver load). Fix: add `libltdl7` to the
  Dockerfile apt set and rebuild from the same `git archive` of main
  `672d1228` (ACR run cj2). Both jobs repinned to the fixed digest
  `sha256:cee2a4cc0b03659dd7c6a19251b2e6c53a6724d0c2c8bcb273affcceab8b1eb2`.
  Executions before the repin (two scheduled ticks and the first
  manual start, plus two read-only diagnostic overrides) are recorded
  in the execution history; the scheduled ticks at 15:10/15:15/15:20Z
  failed on the old digest and the first tick after the repin
  (execution `...29804605`, 15:25:00Z) succeeded — proving the cron
  trigger itself on the fixed image, not only manual starts.
- Manual execution proof (fixed image), execution
  `peerslate-account-export-worker-4t7mbua`, status Succeeded with
  `--replica-retry-limit 0` (single attempt, exit 0): console stream
  shows managed-identity token success for the exact client id, then
  `{"stage": "claim", "state": "idle"}` and `{"outcome": "idle"}` —
  the worker authenticated to SQL **as the worker principal**, which is
  also the standalone as-the-principal verification the gate-6 section
  defers here.
- Maintenance execution proof, `peerslate-export-maintenance-mqlxz3o`,
  Succeeded: `{"expired_count": 0, "stage": "maintenance_expired"}`
  then `{"cleaned_count": 0, "cleanup_failed_count": 0,
  "expired_count": 0, "outcome": "completed"}` — expire procedure,
  sweep read, and both grants proven live under the UAMI.
- Log Analytics content-free check (workspace `ce54504b`,
  `ContainerAppConsoleLogs_CL`): every line across both proofs is
  either azure-identity plumbing with values REDACTED by the SDK, or
  the worker's own allowlisted JSON (stage/state/outcome/counts only).
  No member content, object name, container name, connection string,
  or account URL appears.

## Gate 8 — storage container verification

Provisioned by C2 (assembly package); this gate re-verifies, read-only:

- Container `peerslate-private-account-export` on `peerslatecapturemedia`
  private: verified 2026-09-01, `publicAccess: null`.
- Account: verified `allowBlobPublicAccess: false`, HTTPS-only,
  `minimumTlsVersion: TLS1_2`.
- Worker identity: verified exactly one assignment even with
  `--include-inherited` — `Storage Blob Data Contributor` at exactly the
  container scope
  (`.../storageAccounts/peerslatecapturemedia/blobServices/default/containers/peerslate-private-account-export`),
  nothing broader.

**Web-app read grant: owner-executed and verified live.** The C3
download proxy runs under `peerslate-pete`'s system-assigned identity
(`bded56df-a087-4331-95b7-ee99c713ed35`). At gate-8 verification time it
held **zero** role assignments at the container scope even with
`--include-inherited`, and the exact grant command (Storage Blob Data
**Reader** — read-only by design; the web path must never write or
delete an export artifact) was reported to the owner, since role grants
are blocked for the agent by design. The owner executed it at
**2026-09-01T14:59:37Z** (16 seconds after the AcrPull grant). Live
re-verification confirms exactly one direct ServicePrincipal assignment,
`Storage Blob Data Reader`, at exactly the container scope.
**Recorded honestly:** the first frozen candidate still called this
grant pending-owner — the check was ~46 minutes stale by freeze time and
the independent reviewer caught it; this correction re-verified the
grant live before re-freeze.

## Gate 9 — production web deploy (dark)

- Deployed main SHA: `672d122855b2103fdfdd2257ed5e63e57f47944f`
  (re-fetched tip at queue time; identical to the gate-7 image SHA and
  the claim's activation base — no divergence to reconcile).
- Pipeline run: **2221**, queued 2026-09-01 with exact template
  parameters `forceProductionDeploy=true`,
  `manualProductionSourceVersion=672d1228...44f`,
  `productionAuthorizationReference=pete-chat-2026-09-01/five-through-nine`,
  `schemaAction=none` (schemaMigrationId/schemaRollbackConfirm empty),
  verified via the runs REST record.
  **Operational incident, recorded:** the first queue command exited
  nonzero on a client-side JSON parse (the CLI returns `state`, not
  `status`) after the POST had already succeeded, and a second identical
  run (2222) was queued before the first was noticed. 2222 was cancelled
  within one minute; 2221 proceeded alone. The serialization guard was
  never tested by two concurrently *executing* production stages, but
  the near-miss and its cause are recorded so the next operator parses
  before retrying.
- Environment approval: **none was requested.** The approval check
  guards the `peerslate-database-schema` environment only; this run had
  `schemaAction=none`, every schema stage skipped, and the run proceeded
  Build -> ValidateProductionOperationRequest -> Community-schema
  prerequisite -> DeployWebApp -> Finalize without pausing
  (13:59:55Z -> 14:18:00Z, result `succeeded`; timeline record kept).
- `scripts/verify_deployment_smoke.py`: **passed** —
  `/healthz` release identity verified for source
  `672d1228...44f` + build `2221`, plus `/`, `/interview-studio`
  (signed-out redirect verified), `/robots.txt`, `/sitemap.xml`.
  Operator note: the first local run failed with
  `SSL: CERTIFICATE_VERIFY_FAILED` — the known local Python 3.14
  trust-store trap already recorded in `CURRENT_BASELINE.yaml`
  (`local_python_tls_trust_store_refusal`), not a production issue; the
  rerun supplied the certifi CA bundle via `SSL_CERT_FILE` and passed.
  The pipeline's own in-run smoke had already passed server-side.
- App settings `EXPORT_BLOB_ACCOUNT_URL` / `EXPORT_BLOB_CONTAINER` set
  2026-09-01 with `--output none` (the appsettings response returns the
  full secret-bearing collection; it was never read or printed).
- `PEERSLATE_ACCOUNT_EXPORT_ENABLED` proven ABSENT by names-only listing
  (`--query "[].name"`, 41 settings): both `EXPORT_BLOB_*` names
  present, the enablement flag absent.
- Export routes signed-out on https://peerslate.com, post-deploy:
  `/app/settings/export` -> 404, `/app/settings/export/probe-key` ->
  404, `/app/settings/export/probe-key/download` -> 404.
- Re-verified current at re-freeze, 2026-09-01T16:03:32Z: live
  `/healthz` returned release `b6cdfc83bc4884521465da78`, which equals
  the writer's own recomputation
  `sha256(b"peerslate-release-v1" + b"\x00" + b"672d122855b2103fdfdd2257ed5e63e57f47944f" + b"\x00" + b"2221").hexdigest()[:24]`
  — run 2221 remains the exact live release; no later production deploy
  has occurred. (An earlier reviewer inference that the release had
  moved was retracted after this recomputation.)

## Production schema state regeneration

`docs/governance/PRODUCTION_SCHEMA_STATE.md` regenerated by
`python scripts/govern_sql_migrations.py report --expect-database
peerslate-database --write-state` from a live ledger read at
2026-09-01T13:40:32Z (same firewall window): ledger 39 -> 40 applied,
`PS-SETTINGS-EXPORT-010` applied 2026-09-01T12:57:35.9905208 (run 2212's
apply), pending 10 -> 9. The pipeline source/build header lines are
absent because this was a governed operator-shell read, not a pipeline
artifact copy; the tool's own stale-record warning named exactly the
EXPORT-010 delta and nothing else.

## Disclosures (C0 proof-plan item 7: provider/backup limitations)

- **7-day blob soft-delete.** `peerslatecapturemedia` has 7-day blob
  soft-delete and container soft-delete enabled. `cleanup_staging` /
  `cleanup_final` therefore do **not** immediately destroy bytes: deleted
  export artifacts remain provider-recoverable for up to 7 days after
  deletion. The cleanup proof asserts ledger-truthful deletion, not
  immediate physical erasure.
- **EXPORT-010 rollback window.** The migration's rollback (DROP of
  `usp_CompleteAccountExportWithDomains`) is available only until the
  first real export completes: completion populates
  `account_export_job_domains`, and C1 rollback is then permanently
  blocked (domain-ledger package, decision 4, accepted). While the flag
  stays off no real export can complete, so the window is open through
  gate 9 and closes at first member use after gate-10 enablement.
- **Failed-job invisible leftovers (CR11 residue).** No C1 procedure sets
  `cleanup_state='pending'` on a failed row today, so a failed job whose
  best-effort staging cleanup also failed is invisible to the ledger
  sweep until a future procedure change; bounded residue is never
  downloadable. Disposition: recorded here as an accepted open item owned
  by a future SQL slice; the sweep already handles such rows the moment
  they can exist.

## Preapproved disable / rollback plan (not a merge revert)

1. Unset `PEERSLATE_ACCOUNT_EXPORT_ENABLED` (or never set it — current
   state): every export route 404s.
2. `az containerapp job stop` / delete both jobs: no further worker or
   maintenance executions.
3. Revoke identity authority: `az role assignment delete` for the worker
   (and web Reader if granted) on the export container; drop the
   database user or its grants via the authority script's exact set.
4. Redeploy the prior main SHA through the same three-parameter manual
   pipeline path.

## Gate 10 enablement checklist (future owner decision; NOT this package)

1. Web-app `Storage Blob Data Reader` on the export container: already
   granted (2026-09-01T14:59:37Z) and verified live — re-verify at
   enablement time.
2. **The `--maintenance` job MUST be scheduled and healthy before or with
   flag-on.** Enabling exports without scheduled maintenance reopens the
   "expiry is not deletion" retention gap CR11 closed in code — CR11
   states this warning belongs in this checklist.
3. Set `PEERSLATE_ACCOUNT_EXPORT_ENABLED=true` on the web app (separate
   owner authorization required).
4. Live two-member isolation proof and download/expiry proof with
   disposable synthetic members; note the EXPORT-010 rollback window
   closes at the first real completed export.
5. Verify content-free logging end to end under real load.

## Honest limitations

- **No live member proof, by design.** Gate 10 is not authorized; no
  synthetic or real member exercised the export end to end. The idle
  worker proof exercises claim/connect/blob-credential paths only up to
  an empty queue.
- **The web-app Reader grant was mis-stated as pending in the first
  frozen candidate** — it had landed 46 minutes earlier; the independent
  reviewer caught the stale check and this record now carries the
  verified grant. No open pending-owner item remains.
- **Cleanup is not immediate byte destruction** (7-day soft-delete
  disclosure above).
- **Log Analytics is a new evidence surface** for this repo; the
  content-free check covers the executions run here, not a standing
  guarantee — CR11's allowlist test remains the code-side guarantee.
- **Five worker executions failed on the defective first image** before
  the repin (the 15:04:47Z manual start and the 15:05/15:10/15:15/15:20Z
  scheduled ticks; recorded above). No data was touched; every failure
  was a pre-SQL native-driver-load error.
- **The standalone `verify` mode refuses from an admin shell by
  design**; as-the-principal verification is delegated to the jobs'
  own executions (proven) rather than an operator-run verify.
- **A duplicate deploy run was queued and cancelled within a minute**
  (gate-9 incident note) — recorded so the CLI parse trap is known.
