# PS-PROJECTS-001 - Architecture and data direction

## Architectural purpose

Projects make the released create-once/place-many foundation visible and
useful without introducing another source of truth.

```text
Capture source version
  -> member-confirmed Moment version
  -> explicit Moment placement
  -> owner-scoped Project entity
  -> private Project Workspace read model
  -> optional purpose/audience Project Projection
```

Every arrow is explicit, owner-scoped, lifecycle-aware, and reversible where
the product contract permits. The first implementation slice ends at the
private Project Workspace.

## Reuse the released foundation

- Trusted external identity and internal owner resolution remain authoritative.
- `dbo.moments`, `dbo.moment_versions`, and `dbo.moment_sources` remain the
  canonical Moment and provenance boundary.
- `dbo.slate_entities` remains the owner-scoped registry used for eligible
  destinations and later audience/publication behavior.
- `dbo.moment_placements` remains the exact-version, no-text-copy relationship
  from a confirmed Moment to an existing private/unpublished destination.
- `dbo.slate_entity_relations` may represent approved cross-entity
  relationships when its current contract fits; the future architecture review
  must not create a competing generic relation store without evidence.
- Existing audience grants and publication-version foundations remain the
  starting point for a later Project Projection; they are not activated by the
  first slice.
- Existing Capture, Voice, private media, audit, migration, and owner Settings
  contracts are reused rather than rebuilt.

## Candidate domain model

Exact table and procedure names require Gate B approval. The intended shape is:

### Canonical Project aggregate

`projects`

- opaque Project key and internal ID;
- owner profile ID with tenant-safe constraints;
- one corresponding `slate_entities` row of type `project`;
- title, purpose, Project type, lifecycle status, optional start/end dates;
- optional structured relationships to role or goal by stable ID;
- created/updated actor and UTC timestamps;
- row-version concurrency token; and
- archive/deletion metadata required by the approved lifecycle.

The first slice should keep metadata small. It must not add free-form copies of
linked Moment text, source bytes, outcome narratives, résumé bullets, public
case-study sections, AI responses, or Slate Board note bodies.

### Project revisions

If publication, audit, or correction requirements need immutable Project
metadata history, create normalized `project_versions` or an equivalent
revision model. The future baseline must decide this before DDL. Publication
must never depend on a mutable row without an exact approved version.

### Relationships

- Moment-to-Project uses the released `moment_placements` reference.
- Role, goal, skill, person, outcome, source, and media relationships use
  tenant-safe stable references and explicit relationship types.
- Relationship rows hold identifiers, lifecycle, actor/time, and concurrency
  metadata only. They do not copy authoritative content.
- Removing a relationship changes only that relationship unless the member
  explicitly invokes a separate source, Project, or projection action.

### Workspace read model

The Project Workspace is assembled by an owner-authorized service from Project
metadata plus permitted referenced records. It may use optimized queries or a
cache, but any cache is derived, invalidatable, owner-scoped, and never a new
system of record.

The read model reports restricted, missing, revoked, or deleted-source states
without retrieving inaccessible content.

### Project Projection

Later projection records hold purpose, audience, selection, order, approved
purpose-specific wording, layout/presentation metadata when needed, revision,
and publication lifecycle. They reference exact Project/canonical versions.
They do not convert the private workspace into a public record or copy raw
sources into the publication relationship.

## Required service boundaries

### Project command service

- create private Project;
- update metadata with expected row version;
- transition lifecycle through an explicit allowed-state graph;
- archive/restore and request deletion according to policy; and
- register or retire the corresponding Slate entity transactionally.

### Project relationship service

- validate trusted owner, eligible source record, eligible Project target, and
  current versions;
- call or reuse Placement for Moment links;
- add/remove other approved relationship types through a defined contract; and
- return deterministic absent, duplicate, stale, unavailable, and cross-owner
  outcomes.

### Project query service

- list only the current owner's Projects or server-authorized projections;
- assemble the Project Ledger from permitted relationships;
- paginate or progressively load long histories without changing semantic
  order; and
- return structured tombstone/restricted states instead of leaking or failing
  on unavailable sources.

### Project projection service - later

- create and edit a private projection draft;
- preview through the same serialization/query contract used by the real
  audience;
- validate exact content versions and audience before publication;
- publish/revoke through explicit state transitions; and
- propagate correction, deletion, revocation, and audience changes.

## Lifecycle direction

Candidate Project lifecycle:

`draft -> active <-> paused -> completed -> archived`

Additional explicit transitions may include restore/reopen and deletion
request/complete. The final state graph must define:

- who can perform each transition;
- required fields and confirmations;
- whether dates are proposed or member-confirmed;
- effect on placements and projections;
- export and retention behavior;
- stale/concurrent request behavior; and
- audit-safe events.

Project lifecycle, workspace visibility, projection draft, and publication are
separate dimensions. Completing a Project does not publish it; archiving a
Project does not silently revoke a publication; those cross-effects require an
explicit approved contract and member-facing explanation.

## Authorization boundary

Every read or write resolves trusted server identity and evaluates:

- owner or authorized viewer;
- Project ownership and lifecycle;
- relationship/grant state;
- requested purpose and audience;
- permitted referenced Moment/source/media versions;
- projection and publication state; and
- sensitivity, revocation, deletion, and retention constraints.

Authorization occurs before SQL, search, cache, media, export, or AI retrieval.
A response never fetches another member's private payload and then hides it in
the browser.

## Concurrency and transactions

- Create Project and register its `slate_entities` row in one transaction.
- Use unique tenant-safe keys and deterministic duplicate handling.
- Require expected row-version tokens for metadata and lifecycle writes.
- Link/unlink operations use Placement's exact-version and idempotency rules.
- Lock records in one documented order and keep audit success events tied to
  real state changes only.
- A stale browser must receive a conflict and current safe summary; it may not
  silently overwrite a newer Project or projection revision.

## AI boundary

AI receives only the explicitly authorized Project and source set for the
current workflow. It may propose structure or language but returns a proposal
with source references, uncertainty, model/policy metadata, and member actions.
Deterministic code validates all relationship, lifecycle, audience,
publication, retention, deletion, and access decisions.

## Migration and rollback direction

The first implementation requires versioned, idempotent forward and guarded
rollback migrations. The future plan must:

1. reconcile current `slate_entities`, relation, Placement, publication, and
   fixture shapes;
2. create only the minimum Project tables, constraints, procedures, and
   indexes;
3. prove apply/verify/rollback/reapply on isolated SQL Server;
4. refuse destructive rollback when Project rows, later migrations,
   publications, or dependent objects exist;
5. preserve all existing Moment, Placement, access, publication, audit, and
   résumé data; and
6. treat fixture import as a separate reviewed migration, not automatic seed
   truth.

## Observability

Record safe metadata for create, update, lifecycle, link/unlink, query failure,
projection draft, preview, publish/revoke, export, and deletion outcomes. Use
opaque IDs, state codes, latency, error class, and version metadata. Do not log
Project purpose text, Moment text, source bytes, private filenames, projection
copy, or audience payloads.

## Architecture stop conditions

Stop the future implementation if it requires:

- copying Moment or source text into Project relationship rows;
- trusting a route slug or browser owner ID;
- creating a second audience/publication system;
- making Slate Board local state canonical without migration and ownership;
- auto-creating or publishing Projects from AI/Capture/Board notes;
- broadening the first slice to collaboration or task management; or
- weakening the released Placement, Moment, identity, or deletion contracts.
