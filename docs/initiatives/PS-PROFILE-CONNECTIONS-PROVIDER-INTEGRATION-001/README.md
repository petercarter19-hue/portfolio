# PS-PROFILE-CONNECTIONS-PROVIDER-INTEGRATION-001

## Outcome

Admit the closed PS-CONNECT-002 relationship provider at PeerSlate's shared
stored-procedure execution boundary. The implementation adds exactly its three
actor-scoped procedure names to `ALLOWED_PROCEDURES` and proves that every
procedure value remains parameter-bound. It does not register the provider or
connect it to Profile.

Delivery is **Protected** with repository authority through accepted merge and
production authority withheld. The governed surface extension is merged, and
this final candidate adds one locally alphabetized `current_protect` registry
row with recomputed counts. Registry classification does not register or
enable the runtime provider.

## Exact executable boundary

Only these procedures are admitted:

1. `usp_CommitConnectionRelationshipCommandForActor`
2. `usp_GetConnectionRelationshipSnapshotForActor`
3. `usp_GetConnectionRelationshipCommandForActor`

The set is byte-for-byte equal to
`CONNECTION_FOUNDATION_PROCEDURES` in the unchanged
`services/connection_foundation_repository.py`. `DatabaseService` still
rejects malformed, misspelled, case-changed, prefixed, or unknown procedure
names and invalid parameter-name fragments before opening a connection. Values
are emitted only through positional placeholders.

## Preserved provider contract

The unchanged PS-CONNECT-002 service continues to derive an actor only from an
exact `PeerSlateIdentity`; callers cannot provide an actor key to the command
facade. Its pair-scoped contract remains limited to request, accept, decline,
cancel, expire, disconnect, block, unblock, and reconnect. Existing tests keep
the reciprocal-request, compare-and-swap, replay/idempotency, append-only
history, relationship-version, block-epoch, result-shape, and cross-owner
fences intact.

`ConnectionFoundationProfileReader` remains an unregistered adapter. It maps
one exact actor/subject snapshot into Profile's existing snapshot shape while
preserving pending/disconnected state, relationship version, block epoch, and
block precedence. Invalid, self, absent, or cross-owner values remain neutral
absence; provider failure remains unavailable. Profile's unchanged reader
consumer admits only an active, unblocked `connected` snapshot.

## Schema and product state

The PS-CONNECT-002 migration, rollback, verifier, and SQL migration-registry row
are immutable inputs. The forward migration's executable SHA-256 remains
`b5a2695916d0b1b658341cd7b103894456dcc58b13db580525ed45600f315606`,
matching its historical disposable Azure AD gate. The generated production
schema record still identifies PS-CONNECT-002 as registered but not applied.

This package performs no SQL replay, apply, rollback, execute grant, schema
state refresh, identity or relationship creation, provider construction,
health probe, route/template/navigation/search/cache change, flag, deployment,
or live operation. There is no member-visible effect.

## Validation and merge admission

Validation covers the writable database/reader suites, the immutable
repository/Profile adapter suites, the static PS-CONNECT-002 migration suite,
exact digest and forbidden-path checks, `git diff --check`, the full repository
suite, and independent review of the frozen pushed SHA.

Claim-only activation merged through PR 878. After D1 closed and released the
registry, the append-only surface extension merged through PR 886 at
`d846bb265c3cd7436d9a902c4fd012a2fcda94b8`. The implementation branch was
then rebased onto that exact current main before registration and final
validation. The registry now reconciles at 72 `current_protect` entries and
140 total entries.

The earlier pre-registry review was provisional and does not authorize merge.
Only a new independent review of the frozen final SHA against the extension
base can admit the implementation merge. Evidence and receipt may bind that
accepted candidate afterward; no implementation or registry byte may change.
