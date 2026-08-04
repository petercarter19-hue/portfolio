# PS-PRODUCTION-AVAILABILITY-INCIDENT-001 - completion record

## Core record

- **Task/package and delivery path:**
  `PS-PRODUCTION-AVAILABILITY-INCIDENT-001`, protected emergency production
  recovery, live reliability hardening, and branch/merge process audit.
- **Outcome and member/site effect:** **Pass for public availability and the
  approved infrastructure changes; Conditional for Community re-enable and
  multi-instance resilience.** The apex, Azure redirect, Interview Studio, and
  repaired `www` path are externally verified. Community remains intentionally
  flag-disabled. App Service is P0v3 with Health Check `/healthz`; production
  SQL is Standard S0 and directly verified Online.
- **Branch, base, final source, and changed paths:** branch
  `work/2026-08-04-production-availability-incident-001`; report integration
  base `f59dd9adb8d3da3e6faaae6691ecad1f801b0c2d`; the exact final report commit
  is recorded in the PR/handoff because a commit cannot embed its own hash.
  Repository changes are limited to the four files in this incident package.
  Direct Azure changes are enumerated in
  `PRODUCTION_EVIDENCE_2026-08-04.md`.
- **Verification performed and result:** repeated HTTP/TLS/redirect probes;
  in-app-browser `www` verification; DNS on authoritative and public resolvers;
  Azure hostname/certificate state; App Service plan/configuration; ten
  post-Health-Check probes; SQL ARM operation state; passwordless database-level
  query; pipeline stage/log/artifact review; Azure environment checks and
  permissions; focused PR 276 tests and registry validation; report-link and
  formatting checks. Exact results are in the evidence file.
- **Release state:** final application release is automatic run 505 / build
  `20260804.62` for source
  `f59dd9adb8d3da3e6faaae6691ecad1f801b0c2d`, live release
  `21a77fc14df89aa4f4397f2d`. This is also authoritative repository main before
  this report's documentation-only closeout. The incident report package's own
  PR, policy, merge, and cleanup state are recorded at handoff rather than
  inferred.
- **Known limits and deferred work:** Community maintenance must leave the
  request path before the pilot is re-enabled; distributed counters are needed
  before a second App Service instance; Azure's S0 DTU metric had not
  propagated, so the new
  DTU alert is deferred; direct Azure configuration is not yet infrastructure
  as code; a durable docs-only deployment rule and exact-SHA forced-redeploy
  confirmation remain open; no owner-controlled branch/worktree cleanup was
  performed. Corrected schema run 501 proved that the protected hosted job
  lacked an end-to-end Azure identity/Azure SQL principal path. A narrow
  contained SQL principal and PR 278's merged AzureCLI task binding now exist,
  but a hosted read-only report has not yet proved the complete path. An unsafe
  manual replay request in run 506 was canceled during Build. Run 507 repeated
  the request; its environment check was approved, but the schema job was
  canceled before any task or SQL started. Schema pipeline authorization is now
  temporarily suspended. Run 508 was still queueable, but it was canceled after
  Build and before any schema job; a durable queue-time retired-ID guard remains
  open.
  Production also
  already ledgered `PS-OPPSLATE-001` at the older OS-2 shape even though the same
  ID/file was later expanded for OS-3; OS-3 needs a new additive migration.
- **Next action:** keep Community disabled, wait for explicit collision-free
  runtime ownership before the maintenance/distributed-counter package, add the
  validated DTU alert after metric propagation, and introduce the live lane
  ledger plus owner-reviewed cleanup process.

## Protected additions

- **Shared infrastructure changed:** yes. Community containment, monitoring,
  availability synthetic, App Service tier/Health Check, SQL tier, `www`
  DNS/binding/certificate, Azure environment lock, schema pipeline permission
  and later safety suspension, main comment/squash policies, and the schema
  CLI-order correction are recorded with exact evidence.
- **Deployment/rollback proof:** Community flag verified false after later
  application releases. Run 505, build, source, live release identity, and route
  smokes match. The governed-schema stage was skipped. SQL
  operation `b36bb117-4d1a-4cad-838a-d4812fcf12a3` succeeded 100 percent and a
  direct query confirmed Online/S0. The SQL free-offer decision is irreversible;
  a move to another paid tier remains technically possible but does not restore
  eligibility.
- **Monitoring/operational owner:** existing action group
  `peerslate-ops-alerts` receives the production rules. Pete owns spend/tier and
  future Community-enable decisions. The subscription uses startup credits and
  has spending limit Off; remaining credit balance was not visible to this
  incident lane.
- **Independent review:** the schema fix received Azure blocking CI and a
  separate focused review. Read-only incident lanes independently audited SQL,
  Community/multi-instance safety, branch/process evidence, and report truth.
  No active writer's runtime file was edited by this lane.
- **Schema truth:** run 497 failed in argument parsing before DB connection; no
  SQL ran and no repository record was pushed. PR 276 fixed the CLI order.
  Owner-held run 501 then failed before connection because the hosted agent had
  no usable `DefaultAzureCredential` identity. Run 506 later requested the
  already-ledgered ID but was canceled during Build; its schema stage was
  skipped. Run 507 repeated the request and was canceled at the protected gate
  before schema tasks began. Run 508 repeated it after authorization was removed
  and was canceled before a schema job. None of these runs applied the
  Opportunity Slate OS-3 delta. A fresh post-cancel inventory confirmed the
  original ledger row unchanged, OS-1/OS-2 present,
  all eight OS-3 target table/procedure additions absent, and the reused ID
  already ledgered; a blind retry is forbidden.
- **Actual handoff:** exact final branch/PR/merge state, tests, live identity,
  deferred alerts, and remaining ownership blockers must accompany this record.

## Capability truth table

| Capability | Status |
|---|---|
| Apex and public routes | Implemented, deployed, live-verified |
| `www.peerslate.com` | DNS/binding/TLS implemented and live-verified |
| Community public pilot | Flag-disabled containment; not restored |
| App Service P0v3 | Provisioned and live, one App Service instance |
| Deployment slot/swap | Supported by P0v3 but not provisioned; releases remain in-place |
| App Service Health Check | Configured `/healthz` and live-verified |
| Production SQL S0 | Provisioned, backend-connected, directly verified |
| Two-instance resilience | Deferred; unsafe until distributed counters exist |
| Schema CLI/identity correction | Merged to main; automatic run 505 deployed the pipeline-only source and skipped schema |
| Opportunity Slate schema | OS-1/OS-2 present; OS-3 absent; reused ledger ID requires a new additive migration |
| Schema hosted-agent identity | Narrow SQL principal and PR 278 binding provisioned; hosted read-only proof remains open |
| Schema pipeline authorization | Temporarily suspended after unsafe replay runs 506/507/508; reauthorize only after new ID and hosted report proof |
| Applied-migration immutability | Blocked; applied hash/ID drift must fail before approval |
| S0 DTU alert | Deferred until Azure exposes the metric |
| Monitoring/configuration IaC | Deferred |
| Branch/worktree cleanup | Reported only; no user-owned cleanup performed |

## Plain-English translation

The website really did hang for minutes while Azure still recorded successful
responses. The strongest evidence is a one-instance recycle combined with
Community's synchronous request-time maintenance and a 45-second serverless SQL
wake. The site is now on stronger always-provisioned App Service and SQL tiers,
has a real Health Check, earlier alerts, a repaired `www` hostname, and stronger
same-environment deployment serialization. App/schema cross-environment
exclusion is not yet mechanical. It remains on one App Service instance because the
current in-memory usage/spend controls would be incorrect on two instances. A
P0v3 deployment slot and swap path were not provisioned, so releases remain
in-place. The permanent Community repair and distributed counters need a fresh,
explicitly owned runtime package rather than a risky incident-time edit.
