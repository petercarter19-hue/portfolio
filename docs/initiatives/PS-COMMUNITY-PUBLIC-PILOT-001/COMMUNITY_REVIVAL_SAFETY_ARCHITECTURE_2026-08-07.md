# Community revival safety architecture — 2026-08-07

## Decision

Recover the existing owner-only Community pilot without changing its approved
Feed, Motion-card, Respond, comment-entry, media, or Voice direction. The
recovery changes only four operational seams that were left unsafe or
incomplete after the August 4 outage:

1. maintenance leaves every HTTP request path;
2. an hourly Azure Pipelines schedule invokes a separately default-off bounded
   maintenance command;
3. targeted media cleanup uses a new owner-scoped SQL procedure delivered by a
   new additive migration ID; and
4. Azure SQL connection waits become short and bounded for web and maintenance
   calls.

The application remains reusable and multi-user. Pete is the first-pilot
fixture and allowlisted owner, not product logic. Server-derived identity,
authorization-before-retrieval, private local drafts, explicit Public
selection, transient private dictation audio, reviewed transcript insertion,
and a separate send/publish action remain unchanged.

## Reconciled implementation map

| Locked contract | Existing implementation retained | Recovery seam |
| --- | --- | --- |
| Feed, full conversation, Motion shelf, Respond, compact comment rows | `community_routes.py`, `community_api.py`, `services/community_feed_service.py`, `templates/community_feed.html`, `templates/partials/community_v1/`, `static/css/community-v1.css`, `static/js/community-v1.js` | No visual or interaction redesign. Browser checks guard the approved result. |
| Owner-only publication and mutation; signed-out public reads | `community_api.py`, `services/community_identity.py`, Community stored procedures | No browser-supplied identity or audience is introduced. |
| Private-by-default draft; explicit Public confirmation | Browser-local composer envelope and existing publish command | No server draft or inferred audience is added. |
| Voice capture, transient audio, editable transcript proposal, explicit insertion and separate send | Existing protected Community Voice routes/services and shared Voice provider contracts | Provider/outage and browser checks only; no new Voice runtime or media type. |
| Attachment validation, private Blob access, scan state, removal and restore truth | `services/community_media_service.py`, `services/community_media_storage.py`, existing Community schema | Targeted cleanup moves to a new owner-scoped procedure. Janitor cleanup remains intentionally unscoped and concurrency-safe. |
| Approved retention and restore schedule | `services/community_retention_service.py`, `PS-COMMUNITY-RETENTION-001`, `PS-COMMUNITY-RESTORE-001` | Scheduling moves out of Flask and becomes independent of Community visibility. |

## Maintenance boundary

`app.py` must neither import nor invoke Community maintenance. There is no
`before_request` maintenance hook, with the pilot flag off or on and with
`TESTING=false`.

`scripts/run_community_maintenance.py` is the only operational entry point. It:

- reads only `PEERSLATE_COMMUNITY_MAINTENANCE_ENABLED`, default `false`;
- does not read the public-pilot visibility flag;
- skips rather than queues when its single-run lock is held;
- uses bounded media/content/daily batches and a wall-clock budget;
- logs error classes without content and returns a failing scheduler status;
- leaves failed work eligible for a later retry; and
- cannot affect an HTTP response because it is not imported by the web app.

The existing `azure-pipelines.yml` is the scheduler, but scheduled Community
maintenance never reuses the schema/deployment identity. Before maintenance can
be enabled, a dedicated workload-identity-federated service connection maps to
the external database user `peerslate-community-maintenance`. That user has no
database role and receives direct `EXECUTE` only on the five janitor procedures
through the protected, transactional SQL-authorization command. The same
dedicated identity receives `Storage Blob Data Contributor` at only the
approved private container through the protected Blob-authorization command.
The SQL verifier enumerates role membership, direct grants, and effective
database/schema/user-object authority; the Azure verifier rejects Entra group
membership and enumerates every direct or inherited role assignment. Either
refuses anything outside the exact boundary. Grant changes are verified inside
the SQL transaction and commit only
after the complete boundary passes; failure rolls back the transaction.

A dedicated service connection avoids sharing the schema principal's
`db_ddladmin` and subscription `Contributor` authority. It uses no client
secret and no copied database password: Azure workload identity supplies the
token, and the scheduled runner receives a nonsecret exact-database
`ActiveDirectoryDefault` connection string. An in-process timer or request
cadence would restore the outage blast radius. The main pipeline therefore
gains one hourly
`Schedule` path that skips Build, Candidate, web deployment, and schema
mutation stages and runs only the maintenance job from authoritative `main`.
The job receives the default-false `communityMaintenanceEnabled` setting and
non-secret `communityMediaBlobAccountUrl` / `communityMediaBlobContainer`
values, the dedicated service-connection ID and client ID, and the nonsecret SQL
connection from protected pipeline metadata. It publishes a content-free run
report. The runner checks `DB_NAME()` against the literal `schemaDatabaseName`
and performs a private-container data-plane access probe before any cleanup or
purge. Its process alarm enforces the wall-clock budget, SQL statements carry
the pinned query timeout, and Blob calls carry short connection/read/server
timeouts with no retry. It never reads App Service settings back onto a build
agent. Normal CI, PR, deploy, and governed schema behavior is unchanged for
non-scheduled runs.

Maintenance is enabled before Community visibility. Disabling visibility never
silently disables an already owed retention action. One App Service instance
remains the pilot topology; the SQL procedures retain `UPDLOCK`/`READPAST`
concurrency safety if a second scheduler process ever overlaps.

## Immutable schema correction

`PS-COMMUNITY-PUBLIC-PILOT-001` is already ledgered in production and is never
replayed or rewritten. Its repository definition is restored to the exact
pre-F14 procedure signature that production received.

A new migration, `PS-COMMUNITY-REVIVAL-001`, creates
`dbo.usp_ClaimPublicCommunityMediaCleanupForOwner`. It requires a trusted
`@UserKey`, resolves an active `dbo.app_users` row inside SQL, and restricts
every candidate to that uploader. An invalid or inactive key fails closed.
Targeted post, contribution, or attachment cleanup calls this procedure;
scheduled janitor cleanup continues to call the existing unscoped procedure.

The migration is transactional and idempotent, has an explicit verifier, and
has a rollback that drops only the new procedure and its own ledger row. It
must pass apply, idempotent reapply, verification, rollback, and forward-after-
rollback against a governed disposable database before it can enter a PR.
Production may apply only that exact new ID and digest while Community remains
off.

## Dependency wait budget

The production database is now continuously provisioned Standard S0, so the
old two 60-second serverless-wake attempts are no longer truthful. Connection
establishment keeps one bounded retry for a transient failure, but each attempt
uses a short timeout and the delay is sub-second. Each established connection
also gives runtime statements a bounded 15-second query timeout (environment
overrides are clamped to 5-30 seconds). No stored procedure or Blob mutation is
replayed. Tests pin the maximum elapsed connection budget and query bound and
prove success-after-one-failure, terminal failure, and connection cleanup.

## Release and rollback sequence

1. Prove request-path isolation, maintenance runner behavior, bounded waits,
   Community/provider failure behavior, browser flows, and the additive SQL
   migration locally and in CI.
2. Self-review the complete diff; a fresh reviewer inspects the exact candidate
   SHA for schema, identity, deletion, shared-pipeline, and outage risk.
3. Before merge, create the dedicated no-secret federated identity and service
   connection plus its nonsecret pipeline metadata, with maintenance explicitly
   false and with no SQL or Blob authority yet. A disabled schedule records its
   content-free disabled result without Azure login.
4. Prove the exact candidate branch/SHA through package-specific Candidate
   admission, then remove the temporary isolated app after evidence is kept.
5. Merge only through Azure branch policy. Keep both flags off. The automatic
   main run is expected to fail closed at `VerifyCommunitySchemaBeforeDeploy`;
   it cannot deploy while the additive ledger row/procedure are absent.
6. Apply only `PS-COMMUNITY-REVIVAL-001` through a separate manual governed
   schema run and
   verify the live ledger/procedure.
7. Apply and verify the dedicated identity's two least-privilege authorization
   plans: no SQL role, five direct SQL procedure grants, and one
   container-scoped Blob data role.
8. Deploy only the exact merged main SHA through a separate manual forced
   controlled-pipeline run and
   verify release identity and ordinary-route health with both flags off.
9. Enable maintenance only; verify one clean scheduled/manual-equivalent run,
   bounded duration, content-free logs, and no request-path invocation.
10. Enable the owner pilot; verify signed-out read/no-write and owner authoring,
   Voice, media, comments/replies, Respond, delete/restore, latency, logs, and
   rollback readiness.

Fail closed on any policy, identity, privacy, migration, provider, evidence, or
health mismatch. Application rollback is flag-off plus the prior exact release;
it preserves member data. Destructive schema rollback is not the normal
response and requires its existing break-glass controls.
