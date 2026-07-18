# PS-PLACEMENT-001 — Architecture Contract

## 1. Architectural purpose

PS-PLACEMENT-001 makes a confirmed Moment reusable without turning downstream domains into copies of it. A placement is a private association, not content, publication, projection, or a destination record.

The required chain is:

`Capture source version → confirmed Moment version → placement reference → existing Slate destination`

Every arrow is explicit and owner-scoped. The placement arrow is the only new behavior in this package.

## 2. Reuse the existing canonical foundations

- `dbo.moments` owns canonical Moment lifecycle and confirmation state.
- `dbo.moment_versions` owns immutable Moment versions; the placement must pin `confirmed_version_number` to its exact version row.
- `dbo.moment_sources` preserves source provenance or a deleted-source tombstone. Placement does not reproduce it.
- `dbo.slate_entities` is the existing owner-scoped destination registry. PS-PLACEMENT-001 references an existing target row and does not create or edit one.
- `dbo.audit_events` records privacy-safe lifecycle evidence through `dbo.usp_AppendAuditEvent`.

Do not create a parallel destination registry, a second Moment table, or a generic JSON snapshot.

## 3. Required placement model

Create `dbo.moment_placements` with a narrow lifecycle-aware reference shape. Exact SQL naming may follow repository conventions, but the model must include:

- opaque placement key;
- owner profile ID;
- Moment ID;
- exact confirmed Moment-version ID and/or version number with relational enforcement that the version belongs to that Moment;
- target `slate_entities` ID with relational enforcement that the target belongs to the same owner;
- lifecycle state limited to `active` or `removed`;
- created/reactivated/removed actor and UTC timestamps as appropriate;
- row-version concurrency token;
- a deterministic uniqueness rule allowing at most one active logical reference for the same owner + Moment + confirmed version + target.

The table must not contain free-text content or JSON. In particular, it must not contain Capture body, Moment title, narrative, why-it-matters, target content, label, display copy, audience, generated answer, prompt, or publication snapshot.

Add only the minimum supporting unique constraints/indexes required for composite tenant-safe foreign keys and exact Moment-version pinning. Do not relax or rewrite existing Moment, entity, audience, or publication constraints.

## 4. Required stored-procedure contract

Implement owner-resolving procedures with repository-standard return outcomes:

1. `usp_CreateOrReactivateMomentPlacement`
   - accepts server-derived user identity, Moment key, target entity key, expected Moment row version, and any required expected placement token;
   - resolves owner once and verifies the Moment, exact confirmed version, and target all belong to that owner;
   - requires Moment `confirmed` and `private`;
   - requires target active, approved, private, unpublished, and not soft-deleted;
   - serializes duplicate concurrent requests and returns one placement;
   - creates or reactivates only after all checks pass.
2. `usp_ListMomentPlacementsForOwner`
   - returns reference/lifecycle metadata only;
   - returns no Capture or Moment text and no protected row from another owner;
   - reports target state honestly if it later becomes unavailable.
3. `usp_RemoveMomentPlacement`
   - requires owner, placement key, and current placement row-version token;
   - changes only the placement lifecycle to `removed`;
   - is deterministic for stale, absent, already-removed, and cross-owner requests.

If names differ, document the mapping and preserve these semantics.

## 5. Transaction and concurrency rules

- Resolve identity and acquire all decision-driving Moment/version/target/placement rows inside one transaction.
- Use update/serializable locking or an equivalent database-enforced uniqueness strategy so two create calls cannot produce duplicate active references.
- Lock in one documented order to avoid deadlocks.
- Treat row-version mismatch as a stale request, not a retryable success.
- Append one privacy-safe audit success event only for a real create, reactivation, or removal. Idempotent reads/replays do not create duplicate success events.
- Audit metadata may contain opaque keys, numeric version/state codes, and event type only; never content.

## 6. Destination and consumer boundary

The destination must already exist in `dbo.slate_entities`. Placement creation may not:

- insert or update the target entity;
- create `dbo.slate_entity_relations`;
- write an access grant or publication version;
- change audience, visibility, approval, publication, active, or deletion state;
- create a Journal/Story/Work/Project/résumé/Studio/Feed record;
- make any current public or protected page consume the placement.

A later domain package may read placement references and create purpose-specific projections under its own approval, privacy, wording, and publication contract.

## 7. Source-deletion behavior

A confirmed Moment whose source link is a deleted-source tombstone remains a member-approved canonical record and may be placed. Placement list/create procedures must not attempt to retrieve deleted Capture text. A proposal cannot be placed, whether its source is available or deleted.

## 8. Migration and rollback

The forward migration must be versioned, idempotent, dependency-checked, and registered in the migration runner. The rollback must run its refusal guards before dropping any placement procedure, table, constraint, or index. It must refuse when:

- any placement row exists;
- a later migration is present;
- a later dependency references the placement model; or
- a protected procedure/definition differs from the fingerprint recorded by the forward migration.

Normal rollback on an empty isolated database must remove only PS-PLACEMENT-001 artifacts and leave Capture, Moment, entity, audit, access, and publication foundations unchanged.
