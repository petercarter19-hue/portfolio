# PS-PROJECTS-001 - Test, validation, and release plan

## Status

Future implementation evidence plan. This direction-registration package runs
governance, document-structure, document-render, and regression checks only.

## Automated verification for the first product slice

### Data and migration

- forward apply, schema/constraint/index/procedure inspection, guarded rollback,
  reapply, and later-migration refusal;
- Project/Slate entity one-to-one registration and tenant-safe foreign keys;
- lifecycle constraint and transition coverage;
- row-version stale update and duplicate/idempotent request behavior;
- zero automatic import of historical Project fixtures; and
- zero change to existing Capture, Moment, Placement, access, publication,
  résumé, and audit row counts outside synthetic test data.

### Authorization and privacy

- two-owner create/list/detail/update/archive/delete isolation;
- cross-owner Project, Moment, placement, relation, source, media, projection,
  and row-version identifier attacks;
- owner identity derived only from the trusted server session;
- no private Project response fields on viewer/public paths;
- no client-side-only authorization;
- no automatic publication, grant, Feed item, Story item, Resume edit, Studio
  session, Slate Board edit, or collaboration; and
- no private payloads in logs, metrics, exceptions, or audit metadata.

### Canonical reuse

- Moment placement pins the exact confirmed version;
- proposal/unconfirmed Moment cannot be linked;
- link/unlink changes only the placement relationship;
- Project relationship tables contain no Capture/Moment/source/projection text;
- deleted-source confirmed Moment renders a safe tombstone path;
- source correction/revocation/deletion propagation follows the approved
  contract; and
- Project reads join authorized canonical data instead of copied fixtures.

### Functional and failure

- create, edit, pause/resume, complete/reopen, archive/restore, delete/revoke;
- empty, short, long, missing-source, restricted, partial, and unavailable
  Project reads;
- duplicate submit, retry, timeout, stale edit, lost response, and service
  failure;
- AI unavailable leaves essential behavior intact; and
- export/deletion behavior is complete and deterministic.

### Accessibility and visual integrity

- semantic heading and landmark structure;
- keyboard order, visible focus, screen-reader names/status, and no drag-only
  behavior;
- touch targets, mobile portrait/landscape, 200-percent reflow, long content,
  high contrast, reduced motion, missing media, and failure recovery;
- named desktop/mobile comparisons against the approved visual authority;
- recorded deviations and explicit Pete/designated-manager acceptance; and
- homepage impact/parity evidence when a Projects projection exists on `/`.

## Real-member validation

Pete and Danielle use separate real staging accounts and reusable product logic.
Each should:

1. create one real private Project without a product tour;
2. explain the difference among Project, Work, Slate Board note, Moment, and
   Project Projection;
3. connect one exact confirmed Moment and explain what changed and what did not;
4. find the Moment in both contexts without seeing copied or inconsistent text;
5. update Project status and recover from one stale-edit or failure state;
6. archive/restore or remove a relationship without deleting the source Moment;
7. explain who can see the Project and verify that the other account cannot;
8. complete a short Project reflection and identify one useful reuse action;
9. complete the task on mobile and through keyboard/large-text behavior; and
10. state whether the Project Workspace helps them remember, understand,
    communicate, or reuse meaningful work.

The later Project Projection slice adds exact-audience preview, publish,
viewer, revoke, and source-change validation. Collaboration requires separate
participants and a separate authorization package.

## Release gates

### Gate A - Direction

Owner-approved problem, boundaries, first scenario, and phase position.

### Gate B - Requirements and architecture

Every mandatory requirement is allocated; exact schema, APIs, lifecycle,
authorization, migration, rollback, and test ownership are approved.

### Gate C - Visual and build readiness

Complete V0/V1 Project Workspace design set and implementation mapping are
accepted. Homepage impact is recorded.

### Gate D - Implementation verification

Complete-diff self-review and all focused, guardrail, full-suite, SQL,
security/privacy, accessibility, responsive, visual, and rollback evidence pass.

### Gate E - Member validation

Pete and Danielle complete the real tasks and understand privacy, sources,
status, relationship behavior, and value.

### Gate F - Release

Azure PR, squash merge, Build and Deploy, production auth boundary, accepted
asset/version proof, monitoring, and rollback readiness pass. Public Project
routes remain unavailable unless a later Project Projection package separately
passes its gates.

## Automatic blockers

- cross-user access or ambiguous ownership;
- canonical text copied into relationship or Project rows;
- AI-created status/publication or unreviewed factual content;
- missing stale-write protection;
- destructive or unguarded migration rollback;
- Project Workspace represented as public or collaborative before enforcement;
- accessibility blocker or material visual downgrade;
- stale or false homepage projection;
- unresolved required test or validation failure; or
- missing Azure pipeline or production verification.
