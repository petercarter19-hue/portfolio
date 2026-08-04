# Production evidence - August 4, 2026

All times are UTC. This file distinguishes observed runtime/configuration facts
from inference.

## Incident and recovery timeline

| Time | Evidence | Meaning |
|---|---|---|
| 15:09:52-15:12:48 | Automatic build 480 deployed source `3f8a6e7e215424a7aa239da59f3a799b1ba727cf` | Normal main release |
| 15:24:43-15:26:44 | Forced manual build 482 deployed the same source | Redundant production recycle |
| 15:39:59 | First slow-response alert resolved | Latency temporarily cleared |
| 15:57:52 | Azure activity log: successful `Microsoft.Web/sites/config/write` for app settings | Production configuration changed; the event does not expose which key changed |
| 15:59:19 | Azure activity log: successful `Microsoft.Web/sites/restart/action` | Sole App Service instance explicitly recycled |
| 16:02:46 | SQL login-triggered auto-resume began; duration 44.882 seconds | Paused database woke on demand |
| 16:02:57 | `/healthz` availability execution began and took 40.993 seconds, recorded as Passed | Sixty-second synthetic timeout hid a user-visible hang |
| 16:05 | App metrics: 23 requests, 65.215-second average, 190.879-second maximum, 0 HTTP 5xx | Real outage without server-error status |
| 16:08:37 | `peerslate-prod-slow-response` fired | Existing 15-minute-average alert finally detected latency |
| 16:15:53 | Emergency app-setting rollback completed | Community public-pilot flag returned to `false`; no separate restart was issued |
| 16:21:54 | Documentation-only source `9ee551b0...` queued build 484 | Missing `[skip ci]` caused another release |
| 16:25:51-16:30:19 | Build 484 ZipDeploy | Another in-place recycle; run was not interrupted after deployment began |
| 16:33:25 | Build 484 succeeded | Exact then-current main deployed |
| 16:33:34 | Slow-response alert resolved | Recovery alert gate passed |
| 16:42-16:44 | Repeated root checks 0.34-0.38 seconds; App Service average 0.045-0.059 seconds; zero 5xx | Clean post-release window |
| 16:53-16:54 | SQL auto-resumed again; two failed system connections and 0 percent availability points | Serverless wake risk remained current |
| 16:55 onward | SQL availability returned to 100 percent | Wake failure was transient |
| Approximately 17:00 | Passwordless read-only `SELECT 1` passed in 3.243 seconds | SQL was accepting connections |
| 17:46:40 | Automatic main run 490 queued for `98d15656...` | Trigger was active even though normal listing visibility was delayed |
| 17:48:15 | Manual forced same-SHA run 491 queued | Premature fallback overlapped automatic run 490 |
| 18:00:33 | Run 491 canceled before deployment | Duplicate was safely removed; automatic run continued |
| 18:01:44 | Run 490 succeeded | Live release became `37a56fbb12beab7db90b18da` |
| Approximately 18:05-18:07 | App Service plan changed B1 to P0v3, one App Service instance | Brief recycle/timeouts occurred during the move; routes recovered |
| 18:06:50-18:16:25 | Automatic run 496 deployed `d3af4793...` | Build and production smoke succeeded; release `2c09c350ac8238dc104704cc` |
| 18:14:59 | Azure activity log: successful explicit App Service restart during run 496's AzureWebApp deployment task | Deploy task ran 18:13:59-18:15:47; smoke continued to 18:16:22; overlapping recycle was unnecessary release risk |
| 18:19:33-18:20:29 | Manual schema run 497 entered the protected environment and failed | Registry passed; `apply` failed in `argparse` before any DB connection/SQL |
| 18:19:49-18:27:07 | Automatic run 499 deployed `2b0246c8...` | Build and production release succeeded; exact live release `b7f3c4727a7ed7c7cc790095` |
| 18:28:30 | App Service Health Check configured as `/healthz` | Ten subsequent probes passed with the same release identity |
| 18:30:04 | SQL operation `b36bb117-4d1a-4cad-838a-d4812fcf12a3` began | In-place conversion to Standard S0 |
| 18:31:16 | ARM first observed current/requested `S0`, `Online`, 250 GB | S0 cutover completed; health remained HTTP 200 |
| 18:32:48 | Azure DevOps production Exclusive Lock check 14 created | Environment-level concurrency defense added |
| 18:35:16 | PR 276 squash-merged as `304a5ec...` with `[skip ci]` | Schema CLI order fixed without recycling production |
| 18:43:32-18:49:55 | Corrected manual schema run 501 used `304a5ec...` and requested `PS-OPPSLATE-001` | Build/checks passed and production skipped; schema failed before connection because the hosted agent had no usable Azure credential |
| After run 501 | Passwordless read-only schema inventory and ledger query | `PS-OPPSLATE-001` was already ledgered at the older OS-2 shape; all eight OS-3 target table/procedure additions were absent |
| 18:58:30 | Contained external SQL user `peerslate-ado-schema` created by the separate schema lane | Narrow pipeline data-plane principal provisioned; end-to-end hosted report still unproved |
| 19:03:01 | PR 278 squash-merged as `f59dd9a...` after blocking build 503 passed | Connected schema commands now use `AzureCLI@2`; its handoff still named the reused migration ID |
| 19:03:35-19:10:26 | Manual run 506 requested `apply` for already-ledgered `PS-OPPSLATE-001` | Canceled during Build; governed-schema stage skipped and no SQL ran |
| 19:04:04 | Active review thread 363 recorded the reused-ID blocker | Review became visible after PR 278 had already merged |
| 19:04:37-19:13:22 | Automatic run 505 deployed `f59dd9a...` | Build and production release succeeded; `schemaAction=none` skipped schema; exact live release `21a77fc14df89aa4f4397f2d` |
| 19:13:51-19:23:15 | Manual run 507 repeated `apply` for ledgered `PS-OPPSLATE-001`; shared Azure account approved its check at 19:17:31 | Schema job canceled at 19:18:14 before tasks/SQL started; run finalized Canceled |
| 19:15:44-19:15:45 | Azure DevOps branch policies 2 and 3 created on `main` | Unresolved comments must be resolved; only squash merge is allowed |
| Approximately 19:19 | Pipeline 1 authorization removed from schema environment 3 | Reversible freeze prevents another apply from entering the protected environment |
| After 19:23:15 | Fresh passwordless ledger/object inventory | Original OS-1/OS-2 ledger row unchanged; all eight OS-3 additions still absent |
| 19:24:06-19:28:04 | Manual run 508 again requested `apply` for ledgered `PS-OPPSLATE-001` after schema authorization was removed | Canceled after Build; schema stage canceled before a deployment job/SQL |
| 19:28:09 | PR 278 thread 363 received a post-merge stop notice | Records runs 506/507/508, unchanged SQL, authorization freeze, and re-enable conditions |

## Runtime configuration and code evidence

- Before rollback:
  `PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED=true`.
- After rollback and after every later application deployment:
  `PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED=false`.
- `app.py` lines 685-698 at the incident source register an app-wide
  `before_request` hook that, when the flag is on and the endpoint is not
  health/static, calls both Community maintenance runners synchronously.
- `services/community_media_service.py` starts its first media sweep
  immediately because `_next_run` starts at zero.
- `services/community_retention_service.py` explicitly states that the
  triggering request waits for inline maintenance.
- `db.py` permits two 60-second connection attempts with a one-second retry
  delay.
- Flask-Limiter uses in-memory storage. Workshop's spend ledger declares itself
  one-instance-only, and Opportunity Slate has another per-process budget guard.
  These are the evidence-backed reason production remains at one App Service
  instance.

## Current deployment and capacity evidence

- App Service plan: `ASP-peerslate-9377`, Linux Premium P0v3, capacity 1.
- Web App: `peerslate-pete`, Always On, HTTP/2 enabled.
- App Service Health Check path: `/healthz`.
- Deployment slot: supported by P0v3 but not provisioned; deployment remains
  in-place and no slot-swap path is configured.
- Ten probes from 18:28:38 through 18:29:24 returned HTTP 200 in
  0.075-0.255 seconds and exact release `b7f3c4727a7ed7c7cc790095`.
- No second instance was added because doing so would multiply per-process
  product and rate-limit budgets.
- P0v3 list-price snapshot: $0.085/hour, approximately $62.05/month for one
  continuously provisioned App Service instance.

## Current SQL evidence

- Database: `peerslate-database` on server `peerslate`.
- ARM state after conversion: `Online`; current/requested objective `S0`; SKU
  Standard, capacity 10; max size 268,435,456,000 bytes (250 GB).
- Operation `b36bb117-4d1a-4cad-838a-d4812fcf12a3` reports
  `UpdateLogicalDatabase`, `Succeeded`, 100 percent, with no error.
- Passwordless Entra SQL query returned:
  `DB_NAME=peerslate-database`, `Status=ONLINE`, `Edition=Standard`,
  `ServiceObjective=S0`.
- TDE, seven-day PITR, and geo-redundant backup configuration were retained.
- Pre-cutover size was approximately 29 MB; no elastic pool, replica, failover
  group, memory-optimized table, or columnstore index blocked the move.
- All 48 sampled system connection failures in the preceding 24 hours were SQL
  error 40613, database unavailable; there were no user/login-error series.
- Free compute still had 59,866 of 100,000 vCore-seconds remaining, proving
  exhaustion was not the outage cause.
- The conversion permanently forfeited free-offer eligibility with Pete's
  explicit approval. S0 list price was $0.4839/day, approximately $14.72/month.
- Production's `dbo.schema_migrations` contains `PS-OPPSLATE-001`, while the
  live Opportunity schema remains the earlier OS-2 shape: 8 tables and 13
  procedures. None of OS-3's 4 target tables or 4 target procedures exists.
  Against the current 186-object gated registry proof, 125 expected objects are
  present and 61 are missing. Existing Opportunity foreign keys and CHECK
  constraints were enabled and trusted.
- Exact ledger metadata: applied at `2026-08-04T00:39:49.985480` by
  `live.com#peerslate19@gmail.com`; application version
  `PeerSlate Bible and Roadmap v3.0`; notes `NULL`; description limited to the
  OS-1/OS-2 eight-table/thirteen-owner-procedure shape plus purge procedure.
- Git history records OS-2's production application, then later materially
  expands the same `PS-OPPSLATE-001` migration file for OS-3. The ledger is
  ID-based, so the current planner cannot treat those later bytes as pending.
  OS-3 requires a new additive migration from the actual OS-2 baseline; the
  current ID must not be replayed or its ledger row altered to force execution.
- `Registry.pending()` excludes an ID already in the ledger. Supplying
  `--expect PS-OPPSLATE-001` would therefore fail closed because the computed
  plan does not contain that ID; it would not execute the later OS-3 bytes.
- `peerslate-prod-sql-free-compute-low` is disabled after conversion. Existing
  availability, system-connection-failure, Resource Health, and diagnostic
  coverage remains enabled.
- Contained user `peerslate-ado-schema` exists as `EXTERNAL_USER`, default
  schema `dbo`, created/modified `2026-08-04T18:58:30.420000`. Its SID maps to
  service-principal application/client ID
  `8948ceff-6f5c-4f88-91cd-aefc6e99fc32` (the enterprise object ID is a
  different value).
- The user's only database-role membership is `db_ddladmin`. Direct grants are
  database `CONNECT`, database `VIEW DEFINITION`, ledger-only
  `SELECT/INSERT/UPDATE/DELETE`, and `EXECUTE` on
  `dbo.usp_AppendAuditEvent`. It is not in `db_owner`, `db_datareader`, or
  `db_datawriter`; no broader direct grant was observed.
- As of the post-cutover checks, Azure still advertised the old serverless
  metric catalog and rejected `dtu_consumption_percent`. No alert was created
  with validation bypassed; add it after metric propagation.

## `www` DNS, binding, and TLS evidence

- Porkbun authoritative TXT:
  `asuid.www=DEC6E5DCE81B0D3BF414CCDC154AF1E5B7F4CB9B57A1552DFC01ED8DCD801CF7`,
  TTL 600.
- Porkbun authoritative CNAME:
  `www` to
  `peerslate-pete-d9hhdeerd7frg2gc.centralus-01.azurewebsites.net`, TTL 600.
- Azure hostname binding: `www.peerslate.com`, SSL state `SniEnabled`.
- Azure-managed certificate thumbprint:
  `7BEAA0D90BCCFEE7502D2F9032C8CDD37DC61D72`; issuer GeoTrust TLS RSA CA G1;
  expiry February 4, 2027.
- Command-line verification returned a 308 from the `www` path to the same apex
  path/query, followed by HTTP 200.
- In-app-browser verification navigated through
  `www.peerslate.com/interview-studio?source=www-browser-check` and ended at the
  apex Interview Studio with the expected title.

## Pipeline and protected-environment evidence

- Run 490: automatic build `20260804.49`, source `98d15656...`, succeeded.
- Run 491: manual forced duplicate for the same SHA, canceled before deployment.
- Run 496: automatic build `20260804.53`, source `d3af4793...`, succeeded.
- Run 497: manual build `20260804.54`, source `d3af4793...`, `schemaAction=apply`,
  migration `PS-OPPSLATE-001`, failed before DB access because `--print-state`
  followed the subcommand. Evidence artifact publication processed zero files.
- Run 499: automatic build `20260804.56`, source
  `2b0246c8d968d7e49b0762a0129aab4e6d99392b`, succeeded. Build and
  ProductionRelease passed with zero warnings/errors; exact live release is
  `b7f3c4727a7ed7c7cc790095`.
- PR 276 blocking build 500 (`20260804.57`) passed. Independent review repeated
  45 focused tests, 1 expected credentialed-live skip, 3 subtests, registry
  validation of 23 entries/11 gated hashes, and `git diff --check`.
- PR 276 squash merge `304a5ecdd49afc52f7496440b1afdfa64593639e`
  used `[skip ci]`; no production release was queued by the merge.
- Run 501: manual build `20260804.58`, source `304a5ec...`,
  `forceProductionDeploy=false`, `schemaAction=apply`, migration
  `PS-OPPSLATE-001`. The protected checks passed. The apply task then exhausted
  `EnvironmentCredential`, workload identity, managed identity, shared cache,
  CLI, PowerShell, developer CLI, and broker credential options and reported
  that Azure SQL did not accept a connection after three attempts. No SQL
  connection or migration execution occurred.
- PR 278 moved connected schema commands into `AzureCLI@2` under the existing
  service connection. Blocking build 503 passed and it squash-merged as
  `f59dd9adb8d3da3e6faaae6691ecad1f801b0c2d`. Review thread 363 was posted
  after the merge and remains active because the handoff still named the reused
  `PS-OPPSLATE-001` ID.
- Run 506: manual build `20260804.63`, source `f59dd9a...`,
  `forceProductionDeploy=false`, `schemaAction=apply`, migration
  `PS-OPPSLATE-001`. It was canceled during Build at 19:10:26. Production and
  governed-schema stages were skipped; no database connection or SQL occurred.
- Run 505: automatic build `20260804.62`, source
  `f59dd9adb8d3da3e6faaae6691ecad1f801b0c2d`, succeeded. Build and
  ProductionRelease passed; governed schema was skipped under the default
  `schemaAction=none`. Exact live release is `21a77fc14df89aa4f4397f2d`.
- Run 507: manual build `20260804.64`, source `f59dd9a...`, repeated
  `schemaAction=apply` for `PS-OPPSLATE-001`. Build passed and production was
  skipped. The shared Azure account approved the environment check at 19:17:31.
  Cancellation at 19:18:14 canceled the schema job before any schema task,
  database connection, or SQL started; the run finalized Canceled at 19:23:15.
  Its eventual job record was Abandoned with zero duration, no log, and no child
  task records.
  Azure's account record cannot identify which human or agent using that account
  queued or approved the run.
- Run 508: manual build `20260804.65`, source `f59dd9a...`, again requested
  `schemaAction=apply` for `PS-OPPSLATE-001` after environment authorization had
  been removed. It was canceled after Build; ProductionRelease was skipped and
  SchemaMigration canceled before a deployment job or SQL began.
- Production environment `peerslate-pete` has Exclusive Lock check 14, timeout
  43,200 seconds.
- Schema environment `peerslate-database-schema` has Pete-only approval check
  11. Pipeline 1 authorization was temporarily removed after run 507; the
  permission query now returns no authorized pipelines.
- These controls are on different environments and did not prevent run 506 from
  being queued while run 505 was active. Cross-environment app/schema exclusion
  therefore remains procedural and needs one shared orchestration gate.
- Main branch policies now include blocking CI policy 1, unresolved-comment
  policy 2, and squash-only merge policy 3.

## Recovery verification matrix

| Check | Result |
|---|---|
| `https://peerslate.com/` | HTTP 200 after run 499 and after capacity/config/SQL changes |
| `https://peerslate.com/interview-studio` | HTTP 200 after final application release |
| `https://www.peerslate.com/interview-studio?...` | One canonical 308 preserving path/query, then apex HTTP 200 |
| Supplied Azure HTTP URL | Successful canonical redirect chain to apex |
| `/healthz` | HTTP 200 with release `21a77fc14df89aa4f4397f2d` |
| Application build/source | Run 505 / build `20260804.62` / `f59dd9adb8d3da3e6faaae6691ecad1f801b0c2d` |
| Repository main | `f59dd9adb8d3da3e6faaae6691ecad1f801b0c2d`, exact source deployed |
| App Service Health Check | `/healthz`, Always On |
| Production SQL | Direct passwordless query: Online / Standard / S0 |
| Opportunity Slate schema | OS-1/OS-2 present under ledger ID `PS-OPPSLATE-001`; OS-3 absent and requires a new additive ID |
| Post-cancel SQL verification | Ledger row unchanged; all four OS-3 tables and four OS-3 procedures absent |
| Community | Intentionally flag-disabled; no live Community claim |
| Active pipelines after final release | No in-progress runs listed after run 505 succeeded and runs 506/507/508 were canceled |

## Monitoring changes verified live

| Azure resource | Configuration |
|---|---|
| `peerslate-prod-hung-response` | Maximum `HttpResponseTime > 10` over 5 minutes; evaluate every minute; severity 1 |
| `peerslate-prod-5xx` | Total `Http5xx > 0` over 5 minutes; evaluate every minute; severity 1 |
| `peerslate-prod-plan-high-cpu` | Average plan CPU >85 percent over 5 minutes; evaluate every minute |
| `peerslate-prod-plan-high-memory` | Average plan memory >85 percent over 5 minutes; evaluate every minute |
| `peerslate-prod-sql-unavailable` | Average SQL availability <100 percent over 5 minutes |
| `peerslate-prod-sql-system-connection-failed` | Any system connection failure over 5 minutes |
| `peerslate-prod-sql-free-compute-low` | Disabled after S0 conversion |
| `peerslate-prod-resource-health` | Active Resource Health event for App Service or SQL |
| `peerslate-prod-app-settings-changed` | Successful App Service config write |
| `peerslate-prod-restarted` | Successful explicit App Service restart |
| `peerslate-availability` | `/healthz`, one location, five-minute frequency, 10-second timeout, retry, HTTP/TLS/content validation |
| `peerslate-prod-sql-observability` | SQL Insights, errors, timeouts, blocks, deadlocks, and basic metrics to `peerslate-logs` |

## Evidence limitations

- Azure activity logs identify the account and client, not the human or AI
  controlling the client.
- The setting activity proves a write occurred, while a direct read proved the
  Community flag was `true`; the activity event does not prove that write first
  enabled that exact key.
- Signed-out external verification does not prove every signed-in member path.
  The database itself was verified through passwordless SQL.
- Community is not verified live because it is intentionally disabled.
- Azure metric-definition propagation prevented creation of a validated S0 DTU
  alert during the immediate cutover window.
- The protected schema environment and approval were functional. A narrow SQL
  principal and PR 278's hosted AzureCLI identity binding now exist, but the
  end-to-end report path remains unproved. Schema pipeline authorization is
  temporarily suspended, blocking another governed apply until corrected and
  verified.
- A migration ID/file was reused and expanded after production had ledgered an
  earlier slice. The current ledger lacks enough immutable-byte identity to make
  that later expansion pending. This is a separate governance defect from run
  501's authentication failure.
- No configuration can promise zero future outages; evidence supports reduced
  wake/recycle risk and faster detection.
