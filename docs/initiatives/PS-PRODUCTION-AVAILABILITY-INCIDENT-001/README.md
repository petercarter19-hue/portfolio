# PS-PRODUCTION-AVAILABILITY-INCIDENT-001

## Authority and delivery path

- Owner authorization: Pete's August 4, 2026 request to assess the production
  outage, restore access, determine cause, apply the recommended reliability
  changes, repair `www`, and review the branch/merge process.
- Delivery path: protected emergency production recovery and bounded
  operational hardening.
- Initial incident evidence base:
  `origin/main` at `9ee551b0c21f448e5c01a843262597cf575b0d9b`.
- Current authoritative repository after the incident corrections:
  `origin/main` at `f59dd9adb8d3da3e6faaae6691ecad1f801b0c2d`.
- Working branch:
  `work/2026-08-04-production-availability-incident-001`.
- Writer boundary: this lane owns this report package and the recorded direct
  Azure operational changes. It does not own Community runtime files,
  Opportunity Slate runtime/schema work, or another writer's worktree.

## Outcome

The public site is restored and externally verified. The apex hostname,
Interview Studio, the supplied Azure hostname's canonical redirect, and the
newly repaired `www.peerslate.com` path all work. The final application release
verified during this incident is automatic run 505 / build `20260804.62`, source
`f59dd9adb8d3da3e6faaae6691ecad1f801b0c2d`, release
`21a77fc14df89aa4f4397f2d`.

PRs 276 and 278 changed pipeline, test, and operational documentation rather
than application behavior. PR 276 used `[skip ci]`; PR 278 did not, so its
automatic main run performed another in-place deployment. Run 505 succeeded,
its default `schemaAction=none` skipped the governed-schema stage, and the exact
main source is now live.

The Community public-pilot flag remains `false`. That containment is important:
the site is available, but the Community pilot is not restored. No report here
claims that Community's request-held maintenance path is safe to re-enable.

## Strongest evidence-supported incident mechanism

Request/dependency tracing was absent, so one singular root cause cannot be
proven. The strongest evidence-supported failure chain was:

1. The Community public-pilot flag was enabled in production.
2. An App Service settings write and an explicit restart recycled the only B1
   App Service instance.
3. With the flag enabled, the app-wide `before_request` hook synchronously ran
   Community media and retention maintenance for every route except
   `/healthz` and static assets.
4. The serverless production database was paused. Its login-triggered resume
   began at 16:02:46 UTC and took 44.882 seconds.
5. A request that triggered due maintenance could wait for SQL. Timing and the
   delayed `/healthz` result support worker-level head-of-line blocking or host
   pressure during the wake/recycle window, but tracing was unavailable to tie
   the 190.879-second request to one exact call. The `/healthz` synthetic took
   40.993 seconds but Azure counted it as passing because its timeout was 60
   seconds.

The outage was real even though HTTP 5xx stayed at zero. At 16:05 UTC Azure
measured 65.215-second average and 190.879-second maximum response times. The
production database connector also permitted two 60-second connection attempts
with a one-second delay, allowing a dependency problem to occupy a request for
approximately 121 seconds before higher-level work was counted.

## Contributing release and capacity conditions

At incident time production used one B1 Linux App Service instance, in-place deployment, no
slot, no App Service Health Check, and a serverless database that auto-paused
after 60 minutes. Automatic build 480 and forced manual build 482 deployed the
same source, and documentation-only build 484 recycled production again. Plan
memory remained approximately 82-86 percent after the first recovery.

The incident also exposed a coordination problem: automatic build 490 was
queued at merge time but did not appear in normal run listings during the
initial observation window. A manual forced same-SHA fallback, run 491, was
then queued while run 490 was already active. Run 491 was canceled before it
deployed; the automatic run was allowed to finish. This is delayed visibility
plus premature fallback behavior, not a disabled CI trigger.

## Live containment and reliability changes

The following are live and verified:

- Community public-pilot flag returned to `false`.
- Availability synthetic on `/healthz` reduced from a 60-second to a 10-second
  timeout and retained HTTP 200, TLS, certificate-lifetime, retry, and content
  validation.
- App Service Health Check now points to `/healthz`; Always On remains enabled.
- App Service plan upgraded from B1 to Premium P0v3. It intentionally remains
  at one App Service instance until per-process counters are replaced by
  distributed state.
- P0v3 supports deployment slots, but no staging slot or swap pipeline was
  provisioned. Releases therefore remain in-place and can still recycle the
  active instance.
- Production SQL converted from the lifetime-free General Purpose serverless
  offer to continuously provisioned Standard S0, 10 DTU, 250 GB included. The
  database stayed online and a passwordless database-level query confirmed
  `ONLINE`, `Standard`, and `S0`.
- `www.peerslate.com` now has authoritative Porkbun TXT/CNAME records, an Azure
  hostname binding, an Azure-managed TLS certificate, and the expected
  path/query-preserving canonical redirect to `https://peerslate.com`.
- Maximum-response, any-5xx, plan CPU/memory, SQL availability/connection,
  Resource Health, App Service configuration/restart, and SQL diagnostic
  monitoring added or tightened. The obsolete free-compute alert was disabled
  after S0 conversion.
- Azure DevOps production environment `peerslate-pete` now has Exclusive Lock
  check 14. The pipeline's stage-level `runLatest` lock already serialized that
  stage; the environment check is an additional defense-in-depth control.
- The schema environment retains its Pete-only approval check. Pipeline 1 was
  initially the only authorized pipeline; that authorization is now temporarily
  removed after two post-merge requests tried to replay the ledgered migration
  ID. Reauthorize only after the new additive ID and hosted report proof exist.
- Azure DevOps `main` now has blocking comment-resolution policy 2 and
  squash-only merge policy 3 in addition to blocking CI policy 1.

At the August 4 retail snapshot, current P0v3 at one App Service instance is
approximately $62.05/month and S0 is approximately $14.72/month, or about
$76.77/month combined. This is gross current list price, not the exact increase
over former B1, and it excludes a future Azure Managed Redis service and second
App Service instance. It also excludes tax, discounts, and credits. The
subscription currently uses startup credits and has spending limit `Off`; this
report cannot see the remaining startup-credit balance.

## Why the plan remains at one App Service instance

Two App Service instances would improve instance-level resilience, but the
application is not currently multi-instance safe:

- Flask-Limiter uses in-memory per-process counters.
- Workshop's spend ledger explicitly supports only one instance.
- Opportunity Slate also has a per-process budget guard.

Scaling to two instances now would silently multiply global and per-IP AI/voice
budgets. No supported shared Redis/Mongo/Memcached limiter backend is configured.
The smallest durable unlock is a protected distributed-counters package using
Azure Managed Redis, covering Flask-Limiter and the product spend guards. That
work must wait for explicit file ownership/relinquishment because current
Community and Opportunity Slate lanes overlap the required runtime files.

## Governed-schema failure and correction

Manual schema run 497 requested `apply` for `PS-OPPSLATE-001`. Registry and
gate-proof validation passed, and Pete approved the protected environment. The
apply task then failed in `argparse` because global option `--print-state` was
placed after the `apply` subcommand.

The failure occurred before the script opened a database connection, so no SQL
ran and no schema state changed. The evidence publish step processed zero files,
and the record-staging step had no commit or push capability. Run 497 is failure
evidence, not a partial migration.

PR 276 fixed the ordering for `report`, `apply`, and `rollback`, added regression
coverage, passed blocking CI build 500, and squash-merged with no application
deployment.

The owner-held lane then queued corrected manual run 501 for the same migration.
Its build passed, production deployment was correctly skipped, and the protected
schema checks passed. The schema job nevertheless failed before SQL execution:
the Microsoft-hosted agent had no usable `DefaultAzureCredential` identity and
could not open an Azure SQL connection after three attempts. This second failure
exposed a separate authentication-provisioning prerequisite. The migration
remains unapplied; another apply must not be queued until the pipeline service
identity, Azure SQL principal/permissions, and token path are proven end to end.

A direct post-run production check then exposed pre-existing migration drift.
The ledger already contains `PS-OPPSLATE-001`, applied at
`2026-08-04T00:39:49.985480` with a description limited to OS-1/OS-2, while
production has 8 Opportunity tables and 13 procedures and
none of OS-3's 4 additional tables or 4 additional procedures. Git history shows
that the same migration ID/file was materially expanded after the OS-2 production
apply. The current gate expects 186 objects; only 125 are present and 61 are
missing. Consequently, fixing authentication and blindly retrying the same ID
would not apply OS-3: the planner already treats that ID as applied. The schema
lane needs a reconciled, immutable additive migration ID plus a governed proof
against the actual OS-2 production baseline. Further OS-3 applies are frozen.

At 18:58:30 UTC, the separate schema lane provisioned contained external user
`peerslate-ado-schema`, mapped by SID to the Azure service principal's
application/client ID. Its only database role is `db_ddladmin`; narrow direct
grants cover connection, definition visibility, the migration ledger, and the
audit append procedure, with no `db_owner`, `db_datareader`, or
`db_datawriter`. PR 278 bound connected schema actions to that service
connection and squash-merged as `f59dd9a...` after blocking build 503 passed.
The merge completed at 19:03:01 UTC; active review thread 363 recorded the
reused-ID blocker at 19:04:04, after the merge. A manual run was nevertheless
queued at 19:03:35 with `schemaAction=apply` and the already-ledgered
`PS-OPPSLATE-001` ID. Run 506 was canceled during Build; the governed-schema
stage was skipped and no SQL ran. Run 507 repeated the same request after run
505 finished. The shared Azure account approved its environment check at
19:17:31 UTC, but the schema job was canceled at 19:18:14 before any task or SQL
started. Pipeline 1's schema-environment
authorization was then removed as a reversible freeze. The AzureCLI identity
binding is merged, but a read-only hosted `report` has not passed and OS-3 still
requires a new additive migration ID. Run 508 was queued after authorization
was removed; it was canceled after Build and before any schema job. A stop notice
with the containment state was added to PR 278 thread 363.

## Required durable prevention

### Before Community can be re-enabled

1. Assign one explicit writer and reconcile the conflicting Community
   ownership records.
2. Separate public-pilot visibility from maintenance activation with
   independently default-off controls.
3. Remove Community maintenance from the app-wide request path. A scheduled or
   background worker is the durable design; ordinary non-Community routes must
   never trigger it.
4. Add an outer fail-safe around each maintenance runner and regression tests
   at the actual Flask request hook with `TESTING=false`.
5. Replace the request-held two-by-60-second SQL wait with a bounded,
   user-appropriate dependency policy.
6. Add distributed counters before scaling above one App Service instance.
7. Release through one controlled pipeline and verify the exact SHA, build,
   release identity, real routes, and a clean observation window before the
   flag changes.

### Release and operations

1. Keep automatic main releases and schema operations serialized. The
   production environment lock and schema environment approval are separate and
   do not mechanically cross-lock; add a shared mutual-exclusion/orchestration
   gate. Until then, do not merge or queue another production-capable action
   until the prior exact release is live-verified.
2. Never queue a same-SHA fallback while the automatic main run is active or
   merely absent from the default listing. Query by source SHA and inspect the
   build API before concluding the trigger failed.
3. Add an exact-SHA break-glass confirmation for forced same-source redeploys.
   Manual main runs now default to no production deployment, but the additional
   exact-SHA confirmation is not yet implemented.
4. Make documentation-only deployment suppression durable. PR 276 safely used
   `[skip ci]`, but the pipeline still depends on authors applying that marker
   correctly.
5. Codify direct Azure monitoring, Health Check, DNS-adjacent binding, capacity,
   and environment-check state so configuration drift is detectable.
6. Add sustained S0 DTU-capacity monitoring after Azure's post-conversion metric
   catalog exposes `dtu_consumption_percent`; do not create it with metric
   validation bypassed while the resource still advertises serverless metrics.
7. Complete the schema authentication preflight before another apply: retain
   PR 278's merged `AzureCLI@2` binding and narrow `peerslate-ado-schema` grants,
   preferably convert the Azure Resource Manager service connection to workload
   identity federation, and first prove a read-only governed `report` from the
   same hosted task surface. Broaden permissions only when a new additive
   migration proves the exact need.
8. Enforce migration immutability. Once a migration ID is ledgered, its
   executable bytes must never be expanded for a later slice. Store/compare the
   applied hash and require every later production delta to use a new additive
   ID. Reconcile OS-3 from the live OS-2 baseline rather than editing or replaying
   `PS-OPPSLATE-001`.

## DNS and hostname truth

- `https://peerslate.com/` resolves, has a valid certificate, and is canonical.
- The supplied Azure hostname is intentionally a redirect path, not an
  independent fallback deployment.
- `www.peerslate.com` is repaired. Porkbun authoritative DNS exposes
  `asuid.www` for Azure ownership validation and a CNAME to the production Web
  App. Azure binds a managed certificate with thumbprint
  `7BEAA0D90BCCFEE7502D2F9032C8CDD37DC61D72`, expiring February 4, 2027.
- Browser and command-line checks confirmed one canonical redirect with path
  and query preserved, followed by HTTP 200 on the apex host.

## Attribution and non-causes

- Azure activity logs identify the account and Azure CLI client, not whether a
  person, Claude, or Codex controlled the client. They do not expose which
  setting key changed.
- The unmerged Opportunity Slate OS3/OS4 runtime branches did not cause the
  original outage. Run 497 was a later schema-pipeline failure and executed no
  database SQL.
- Apex DNS, TLS, access restrictions, private networking, certificate expiry,
  and exhausted free SQL compute were not the original cause.
- No configuration can promise that an Azure-hosted service will literally
  never have an outage. These controls reduce wake risk, recycle frequency,
  blast radius, and detection time.

## Honest status

- Canonical public endpoints: restored and externally verified.
- `www`: repaired and verified through the in-app browser.
- Live application source/build/release:
  `f59dd9adb8d3da3e6faaae6691ecad1f801b0c2d` / run 505
  (`20260804.62`) / `21a77fc14df89aa4f4397f2d`.
- Authoritative repository main:
  `f59dd9adb8d3da3e6faaae6691ecad1f801b0c2d`; exact main source is deployed.
- App Service: P0v3, one App Service instance, Always On, Health Check
  `/healthz`; deployment slot not provisioned.
- Production SQL: Standard S0, Online, 250 GB limit; free-offer eligibility
  forfeited with owner approval.
- Community public pilot: flag-disabled containment.
- Exclusive Lock and schema approval: active in Azure DevOps. Schema pipeline
  authorization is temporarily suspended; cross-environment app/schema
  exclusion otherwise remains procedural.
- Main branch policy: blocking CI, unresolved-comment resolution, and
  squash-only merge are active.
- Opportunity Slate OS-3 schema: not applied. Corrected run 501 failed before
  connection, production already ledgered the reused `PS-OPPSLATE-001` ID at
  the older OS-2 shape, and a new additive migration is required. The contained
  pipeline principal and PR 278 identity binding now exist; unsafe replay runs
  506, 507, and 508 were canceled without SQL, pipeline authorization is
  temporarily suspended, and a read-only hosted proof remains open.
- Monitoring hardening: live; S0 DTU alert awaiting metric-catalog propagation.
- Monitoring/configuration infrastructure-as-code: not yet implemented.
- Permanent Community/runtime and distributed-counter repair: blocked on a new
  collision-free package and explicit writer relinquishment.
- Community ownership must first reconcile `CURRENT_BASELINE.yaml`, which names
  the current Codex task as sole writer, with continuation records naming
  Claude Code as sole active writer.
