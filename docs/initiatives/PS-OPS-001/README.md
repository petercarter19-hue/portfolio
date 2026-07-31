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

## Current scoped finding

The released pipeline's historical Candidate selector still needs auditable
package-specific exact-SHA admission. Until corrected, it blocks only a future
Protected release that elects to use Candidate. It does not block Routine or
Bounded delivery. The one-time Interview Focus alias evidence remains
historical and is not a reusable procedure.

## Evidence locations

- `CANDIDATE_EVIDENCE_2026-07-27.md` - accepted build 256 record.
- `OWNER_TECHNICAL_COMPLETION_REPORT.md` - released operational floor.
- `docs/templates/PROFESSIONAL_READINESS_EVIDENCE.md` - optional full record
  for a triggered gate.
- `docs/governance/AI_DELIVERY_AUDIT_REGISTER.md` - central audit history.

The standard completion record is sufficient unless the Protected risk needs
the expanded readiness template.
