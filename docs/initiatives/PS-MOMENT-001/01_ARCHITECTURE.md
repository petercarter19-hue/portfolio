# PS-MOMENT-001 — Architecture and State Contract

## Canonical boundary

`dbo.captures` and `dbo.capture_revisions` remain the immutable/revisioned source layer. PS-MOMENT-001 adds a separate member-reviewed canonical layer. The proposal is not authoritative until explicit confirmation.

The implementation should use three logical records, whether represented by exactly three tables or an equivalent normalized design:

1. **Moment aggregate:** opaque key, owner profile, private visibility, lifecycle state, timestamps, row version, and pointers to current proposal/confirmed versions.
2. **Moment version:** monotonically increasing member-editable proposal versions containing canonical fields such as kind, title, occurred date/precision, member-approved narrative, and optional “why it matters” context. These fields are proposals until confirmed.
3. **Moment source:** an owner-scoped link to one exact Capture source version, including a body-free opaque source key/version marker and a deterministic deleted-source state.

Do not store a second hidden copy of the raw Capture original merely for convenience. During review, read the pinned Capture source through owner-resolving SQL and display it separately from editable proposed fields. A proposed canonical narrative is a reviewable derived/member-edited value, not a replacement for the source.

## Minimum states

- **Proposal:** private, editable, unconfirmed, not retrievable as canonical truth by downstream experiences.
- **Confirmed:** private canonical Moment with one explicitly confirmed Moment version and one source link.
- **Discarded:** unconfirmed proposal and its proposed content are removed; body-free audit metadata may remain.
- **Source deleted:** relationship retains only body-free provenance/tombstone metadata. An unconfirmed proposal cannot be confirmed after losing its only source. A confirmed Moment remains the member-approved canonical record but must report that its source was deleted.

Archive/export/full confirmed-Moment deletion may be designed for later data-rights work unless required for safe source-deletion propagation. Do not silently invent broader lifecycle behavior in this package.

## Source pinning

Revision 0 means the immutable `dbo.captures.body`. A positive revision identifies one exact `dbo.capture_revisions` row/version. Creating a proposal resolves the selected source under the current owner in SQL and records that exact source version.

If Capture receives a later correction:

- the proposal/confirmed Moment continues to use its pinned version;
- the protected review response may report that a newer source version exists;
- changing the source requires a deliberate new proposal/review action;
- no automatic overwrite or reconfirmation occurs.

## Stored-procedure boundary

Use owner-resolving procedures. Final names may follow repository conventions, but the package needs operations equivalent to:

- create/reopen proposal from one Capture source version;
- get proposal/Moment plus pinned source for owner;
- save a new proposal version with expected row version;
- discard an unconfirmed proposal;
- confirm the selected proposal version explicitly;
- list minimal owner Moments/proposals only if needed for the protected flow;
- propagate Capture deletion to Moment source state without retaining body text.

Every procedure accepts `@UserKey` plus opaque entity keys. Writes also accept an expected row-version token. SQL resolves the active owner/profile and entity in the same predicate and returns a generic not-found/changed result for foreign, missing, deleted, or stale records.

## Protected HTTP boundary

Recommended focused routes:

- `POST /app/capture/<capture_key>/moment-proposal`
- `GET /app/moments/<moment_key>/review`
- `POST /app/moments/<moment_key>/save`
- `POST /app/moments/<moment_key>/confirm`
- `POST /app/moments/<moment_key>/discard`

Use the existing trusted owner identity and same-origin protection. Keep the new review UI minimal: read-only source, editable proposal, private status, save, confirm, and discard. Do not add global navigation or a Journal-like Moment browser.

## Migration and rollback

The forward migration must verify PS-AUTH-001, PS-CAPTURE-001, and PS-CAPTURE-002 ledger/state prerequisites. Foreign keys and deletion behavior must preserve Capture's explicit aggregate deletion contract while enforcing body-free source tombstones.

The guarded rollback restores any changed Capture lifecycle procedure to its exact PS-CAPTURE-002 definition and removes only PS-MOMENT-001 objects. It must stop when any Moment/proposal/version/source data or later dependency exists; it may never silently discard member content.
