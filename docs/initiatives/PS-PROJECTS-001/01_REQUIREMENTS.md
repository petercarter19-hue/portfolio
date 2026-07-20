# PS-PROJECTS-001 - Requirements baseline

## Status and use

This is a direction-level baseline for future design and architecture work. It
does not authorize implementation. Mandatory requirements must be refined,
allocated to exact architecture, and approved at the future entry gate.

## Member value and boundaries

- **PS-PROJ-VAL-001** - PeerSlate shall help a member remember, understand,
  explain, and reuse meaningful project work without requiring a separate copy
  of the underlying Moments, sources, roles, decisions, or outcomes.
- **PS-PROJ-VAL-002** - The Projects experience shall remain useful to a member
  who never publishes a Project and has no collaborators or public audience.
- **PS-PROJ-VAL-003** - Projects shall not require or imitate sprint planning,
  task assignment, timesheets, procurement, resource leveling, or enterprise
  project-delivery administration.

## Functional requirements

- **PS-PROJ-FR-001** - An authenticated member shall be able to create a
  private owner-scoped Project with a title, purpose, type, lifecycle status,
  dates when known, and optional governed relationships.
- **PS-PROJ-FR-002** - A member shall be able to link an exact confirmed Moment
  version to an eligible Project through an explicit action that reuses the
  released Placement contract and copies no authoritative text.
- **PS-PROJ-FR-003** - The Project Workspace shall present purpose, status,
  recent movement, linked Moments, decisions, milestones/outcomes, sources,
  relationships, and one safe next action through progressive depth.
- **PS-PROJ-FR-004** - A member shall be able to edit Project metadata with
  stale-write protection and shall be able to pause, resume, complete, archive,
  restore, and delete or revoke a Project according to an approved lifecycle.
- **PS-PROJ-FR-005** - A member shall be able to remove a Moment placement from
  a Project without deleting or editing the Moment, its source, the Project, or
  another placement.
- **PS-PROJ-FR-006** - A Project shall be able to relate to one or more roles,
  goals, skills in practice, people, outcomes, and sources without requiring
  those relationships to be stored as free-text duplicates.
- **PS-PROJ-FR-007** - PeerSlate shall keep Project Workspace edits, Project
  Projection drafts, and publication as separate explicit actions and states.
- **PS-PROJ-FR-008** - A future Project Projection shall let the member select,
  order, edit purpose-specific wording, preview the exact audience result, save
  a private draft, publish explicitly, revoke, and inspect source lineage.
- **PS-PROJ-FR-009** - Project context reused in Work, Story, Living Resume,
  Studio/Moment Lab, Replay, or export shall remain a reviewable projection or
  draft linked to the same canonical Project and supporting records.
- **PS-PROJ-FR-010** - A Slate Board note, Capture proposal, imported document,
  or AI suggestion shall not create or change a canonical Project until the
  member reviews and explicitly confirms the action.

## Data, provenance, and lifecycle

- **PS-PROJ-DATA-001** - Project records shall use opaque identifiers,
  server-resolved owner scope, tenant-safe relational constraints, explicit
  lifecycle state, timestamps, actor metadata, and concurrency tokens.
- **PS-PROJ-DATA-002** - Canonical Project metadata, linked canonical records,
  AI proposals, workspace presentation, and audience-specific Project
  Projections shall remain distinct data layers.
- **PS-PROJ-DATA-003** - A Project relationship shall reference exact governed
  records or versions when factual consistency requires it and shall never
  store copied Capture bodies, Moment narratives, source bytes, or publication
  snapshots as the relationship itself.
- **PS-PROJ-DATA-004** - Project correction, archive, deletion, source deletion,
  Moment revocation, audience change, and publication revocation shall have
  defined propagation behavior across placements, projections, indexes, caches,
  exports, and future AI retrieval.
- **PS-PROJ-DATA-005** - Publication shall pin the exact approved Project
  projection revision and exact canonical content versions that the member
  previewed.
- **PS-PROJ-DATA-006** - Historical public Project fixtures shall not be
  promoted to canonical multi-user records without explicit owner review,
  provenance, audience, and migration rules.

## Authorization and privacy

- **PS-PROJ-SEC-001** - The server shall resolve trusted owner/viewer identity,
  relationship, audience, purpose, and permitted source scope before retrieving
  Project metadata, placements, sources, media, projections, exports, or AI
  context.
- **PS-PROJ-SEC-002** - New Projects, relationships, summaries, AI proposals,
  and projection drafts shall be private by default.
- **PS-PROJ-SEC-003** - Cross-owner Project, Moment, placement, source, media,
  projection, and concurrency identifiers shall return no protected data and
  perform no write.
- **PS-PROJ-SEC-004** - Project publication shall require deterministic
  validation, exact audience preview, explicit confirmation, and a recorded
  reversible state transition.
- **PS-PROJ-SEC-005** - Collaboration, co-ownership, shared editing, or member
  invitations shall remain unavailable until a separate requirements and
  authorization package defines roles, grants, conflicts, revocation, removal,
  audit, and abuse controls.

## AI requirements

- **PS-PROJ-AI-001** - AI may propose Project titles, summaries, relationships,
  milestones, missing-context questions, patterns, retrospective prompts, and
  purpose-specific wording only from authorized context.
- **PS-PROJ-AI-002** - AI shall identify the records used, distinguish fact
  from suggestion, state uncertainty, and preserve the member's language.
- **PS-PROJ-AI-003** - AI shall not create, change status, complete, archive,
  delete, share, publish, add collaborators, or modify canonical Project facts
  without a separate explicit member action enforced by deterministic code.
- **PS-PROJ-AI-004** - Project create/edit/link/unlink/archive/export/delete and
  approved viewing shall remain safely usable when AI is unavailable.

## Experience and accessibility

- **PS-PROJ-UX-001** - The opening Project Workspace shall have one dominant
  Project object and one dominant safe action, with five-second orientation,
  approximately thirty-second understanding, and optional depth.
- **PS-PROJ-UX-002** - Mobile shall use a readable ledger/list flow; desktop may
  reveal richer relationships but shall not require a spatial graph.
- **PS-PROJ-UX-003** - Every essential Project flow shall support keyboard,
  screen reader, touch, visible focus, 200-percent zoom/reflow, reduced motion,
  long content, missing media/source, stale edits, failure, and recovery.
- **PS-PROJ-UX-004** - Status, privacy, source availability, AI involvement,
  draft, published, revoked, archived, deleted, and unavailable states shall be
  visually and verbally distinct.
- **PS-PROJ-UX-005** - A Project relationship or chronology shall have a stable
  semantic reading order and accessible structured alternative whenever a
  visual or spatial presentation is offered.

## Reliability, observability, and assurance

- **PS-PROJ-NFR-001** - Project writes and relationship changes shall be
  transactional, idempotent where retry is possible, row-version protected,
  and recoverable without duplicate relationships or silent overwrites.
- **PS-PROJ-NFR-002** - Project list/detail reads shall define measurable
  performance and degradation targets for long histories and missing sources.
- **PS-PROJ-NFR-003** - Privacy-safe observability shall record action type,
  outcome, latency, lifecycle transition, opaque identifiers, and failure class
  without logging private Project text, Moment text, source bytes, or audience
  payloads.
- **PS-PROJ-VNV-001** - Every mandatory Project requirement shall trace to
  architecture, implementation, tests, verification, validation, release, and
  rollback evidence before the first slice can be Complete.
- **PS-PROJ-VNV-002** - The first release shall prove two-owner isolation, no
  automatic publication, no canonical-text duplication, stale-write safety,
  lifecycle behavior, accessibility, migration/rollback, and production
  verification.
- **PS-PROJ-GOV-001** - Historical exhibition designs, legacy fixtures, Slate
  Board notes, and public résumé Project summaries shall be labeled accurately
  and shall not be represented as the authenticated Projects product.
