# PS-OPS-001 - Triggered professional readiness controls

**Current applicability:** owner-directed 2026-07-31
**Historical rollout:** the repository floor, Candidate build 256, Azure PR
189/pipeline 257, detailed evidence, and prior acceptance remain preserved in
this package's evidence files and repository history.

This package supplies controls for high-risk transitions. It is not a universal
release ceremony and does not repeat evidence already produced by a feature.

## Applicability

### Gate Candidate - Protected promotion

Gate Candidate applies to a release that materially changes at least one of:

- identity, authorization, privacy, or cross-user isolation;
- canonical data, schema, migration, retention, deletion, or publication;
- consequential AI or private retrieval;
- shared infrastructure, deployment configuration, dependency/runtime, or
  material availability/rollback risk; or
- another risk explicitly designated Protected by the owner/package.

Routine and Bounded releases use the normal PR, pipeline, and affected-route
smoke. They do not require a Candidate admission record or candidate
environment.

### Gate Launch - material audience expansion

Use Launch for public beta, broad registration, a new public/permissioned data
boundary, or another material audience expansion. It does not rerun for every
ordinary release inside an already accepted boundary.

### Gate Operate - meaningful operating milestone

Use Operate after a new or materially changed service is actually released and
its package defines a useful observation window, or in the central operational
review. Do not create a duplicate 24-72-hour or monthly audit for every slice.

### Gate Retire - shutdown/destructive removal

Use Retire before permanently removing a material service, integration,
credential set, route family, capability, or data boundary. Destructive data
deletion still needs separate explicit authority.

## Candidate minimum

A Protected Candidate record names:

- exact source SHA, immutable artifact, target environment/configuration, and
  audience/flag state;
- the applicable security/privacy/authorization, migration, dependency,
  accessibility, performance, and failure-path results;
- newly load-bearing production settings verified against the actual target;
- stop/rollback action and operator;
- accepted limitation or bounded exception; and
- `Pass`, `Conditional`, `Fail`, or `Not Assessed`.

An unresolved critical/high security, privacy, authorization, cross-user,
publication, deletion, secret, migration/rollback, artifact-identity, or
essential-accessibility issue blocks that Protected transition. A test suite or
healthy homepage cannot substitute for the missing applicable proof.

Use a production-like candidate environment or progressive exposure when the
risk analysis requires it. A bounded exception records owner, reason, expiry,
blast radius, compensating control, and stop/rollback action.

## Launch, Operate, and Retire evidence

- **Launch:** reuse applicable legal, privacy, security, accessibility,
  responsive, performance, support, monitoring, incident, backup/restore, and
  owner-audience evidence from their original sources.
- **Operate:** record the meaningful window, exact live build/flags, health and
  error signals, privacy/security events, member/support outcomes, threshold
  decisions, owner, and next review.
- **Retire:** record affected people/data/contracts, notice/export/retention,
  redirects, dependency/credential teardown order, restore window, operator,
  and final verification.

Reuse exact evidence when scope, SHA, environment, audience, reviewer, and
result match. Do not rerun it merely to populate another checklist.

## Emergency release

Emergency mode applies only when delay creates greater documented production
risk. It may shorten sequencing but never bypass exact build identity,
security/privacy/authorization blockers, approval, a tested stop/rollback, live
smoke, or honest status. Deferred non-blocking evidence gets an owner, expiry,
compensating control, and focused retrospective.

## Azure production release reliability

These rules apply to every initiative that can trigger the shared production
pipeline:

- The automatic Azure run for a merged `main` SHA is authoritative. Before
  queueing anything manually, list queued, running, and completed runs for that
  exact SHA. Do not create a same-SHA fallback while the automatic run exists.
- A manual production deployment must be an explicit false-by-default override,
  not the default effect of clicking **Run pipeline**. Use it only after current
  live identity and the automatic-run state have been inspected.
- Production deployment and its exact source/build smoke must remain in one
  locked operation. Do not split verification outside the lock or weaken the
  build-specific release identity to make an overwritten run appear green.
- Batch rapid `main` changes so a current run finishes and later cumulative
  changes enter one subsequent run. A new initiative does not need a separate
  production deployment for every intermediate merge.
- Once ZipDeploy/Oryx has begun, do not cancel casually: the App Service recycle
  can already be in progress. Let the single selected run finish, then inspect
  its exact live identity before deciding on rollback or one explicit recovery.
- Classify every red record by pipeline, branch, reason, failed stage/task, and
  production impact. A PR test, scanner, Candidate, or disposable-proof failure
  is not a failed production deployment. Do not rerun unchanged failures merely
  to replace a red icon.
- Required PR validation must describe the current target branch. Target-branch
  movement expires the prior result and queues a fresh merge-ref validation.
- `[skip ci]` for a documentation-only closeout must be in the final squash
  commit message. A PR title alone is not release control.

The pipeline protects orchestration; initiative writers still fetch current
Azure `main`, use one active writer per file, avoid overlapping release lanes,
and verify merge, automatic pipeline, live identity, and affected routes as
separate facts.

## Current scoped finding

The released pipeline's historical Candidate selector still needs auditable
package-specific exact-SHA admission. Until corrected, it blocks only a future
Protected release that elects to use Candidate. It does not block Routine or
Bounded delivery. The one-time Interview Focus alias evidence remains
historical and is not a reusable procedure.

## Database schema migrations

Schema, migration, and canonical-data changes are Protected by the Candidate
applicability list above, but until 2026-08-04 the package supplied no mechanism
for them: schema was applied by hand, directly against `peerslate-database`,
outside the Azure pipeline that `AI_WORKFLOW.md` names as the only production
deployment path.

`GOVERNED_SCHEMA_MIGRATION_PATH.md` is that mechanism. It is the only supported
way to move PeerSlate schema. Read it before proposing, gating, applying, or
rolling back a migration. In short:

- the pipeline's `SchemaMigration` stage runs only when a person queues it with
  an explicit `schemaAction` and an approver releases the
  `peerslate-database-schema` environment; merging a migration file applies
  nothing;
- a migration cannot be applied unless `SQL FIles/Migrations/registry.json`
  carries a gate proof whose digest still matches its T-SQL;
- what is pending is read from `dbo.schema_migrations`, and what production
  carries is recorded in the generated
  `docs/governance/PRODUCTION_SCHEMA_STATE.md`, not in migration header prose.

## Evidence locations

- `GOVERNED_SCHEMA_MIGRATION_PATH.md` - the governed schema migration control.
- `CANDIDATE_EVIDENCE_2026-07-27.md` - accepted build 256 record.
- `OWNER_TECHNICAL_COMPLETION_REPORT.md` - released operational floor.
- `docs/templates/PROFESSIONAL_READINESS_EVIDENCE.md` - optional full record
  for a triggered gate.
- `docs/governance/AI_DELIVERY_AUDIT_REGISTER.md` - central audit history.

The standard completion record is sufficient unless the Protected risk needs
the expanded readiness template.
