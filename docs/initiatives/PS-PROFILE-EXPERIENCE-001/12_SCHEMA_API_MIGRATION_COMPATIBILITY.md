# Schema, API, Migration, and Compatibility Architecture

## Current schema foundation

Registered migrations already provide:

- `PS-PLAT-002`: `member_profiles`, `slate_entities`, entity relations, access
  grants, and generic entity publication versions; and
- `PS-PLAT-004`: connection preferences/requests, member connections, blocks,
  reports, notifications, consents, and related foundations.

Applied migration files are immutable. Existing generic
`entity_publication_versions.snapshot_json` remains compatibility data; it is
not the new Profile authority.

## Candidate additive migrations

Names remain architecture candidates until the later implementation lane runs
a fresh registry collision check. Neither `PS-CONNECT-002` nor
`PS-PROFILE-002` is currently registered, reserved, applied, or production
authority. Historical `PS-CONNECT-001` and `PS-PROFILE-001` names are feature
package evidence, not permission to reuse or skip migration registration.

### `PS-CONNECT-002` — relationship lifecycle hardening

Dependency: `PS-PLAT-004`.

Add version/epoch and idempotent atomic commands around request, accept,
decline, cancel, disconnect, block, and unblock. Add an append-only relationship
event record. Enforce unique active unordered pair, owner/actor constraints,
expected version, request replay fencing, block precedence, and atomic
authorization-epoch invalidation. Never rewrite `PS-PLAT-004`.

Current-state storage must prevent reciprocal pending requests, preserve every
reconnect as new append-only history, and expose an opaque row/version token.
Atomic commands bump relationship and bidirectional-block epochs used by the
authorization fence in document 04.

### `PS-PROFILE-002` — governed Profile publication

Dependencies: `PS-PLAT-002`, `PS-PLAT-005`, `PS-AUTH-001`, and
`PS-CONNECT-002` for Connections activation.

Candidate normalized tables:

```text
profile_content_items
profile_content_versions
profile_projection_versions
profile_publications
profile_publication_revisions
profile_publication_revision_items
profile_draft_placements
profile_slug_history
profile_relationship_events      only if not owned by PS-CONNECT-002
```

Store references, versions, hashes, approved projection bodies/metadata,
audience manifests, and placement truth. Do not duplicate large source blobs,
Community threads, Project records, Story/Resume truth, or private knowledge.
Published placement truth lives immutably on publication-revision items;
`profile_draft_placements` is private mutable working state only.

## Integrity constraints

- Every row is owner/profile scoped and server commands derive that owner.
- Projection source owner must equal Profile subject owner.
- Composite owner/profile/audience foreign keys prevent cross-subject and
  cross-audience references.
- Unique current publication per `(profile_id, audience)`.
- Unique monotonic revision per publication root.
- Immutable revision items and projection versions after commit.
- Placement destination/region/type allowlists and deterministic rank.
- Unique published `(revision, destination, region, rank)` and opaque,
  nonsequential projection/route keys.
- Foreign/reference validation to exact source adapter and source version.
- Row/version concurrency plus application locks where a multi-row audience
  revision must commit atomically.
- Idempotency record binds actor, command, request digest, result, and bounded
  retention; a key cannot replay different content.
- Audience tokens are a closed allowlist. No auto-mapping from legacy values.
- Normalized and reserved Profile slug uniqueness spans current and historical
  slug rows. A historical slug is never reassigned cross-Profile. Redirect is
  permitted only to the same active Profile with a current Public publication;
  otherwise lookup returns the neutral unavailable response.

## Service boundaries

```text
ProfileIdentityService       slug and owner resolution
ProfileViewerService         immutable viewer context
ProfileRelationshipService   hardened connection/block state
ProfileSourceAdapterRegistry exact cross-room reference validation
ProfileDraftService          private draft/proposal operations
ProfilePublicationService    preview, publish, withdraw, rollback
ProfileReaderService         Public/Connections/Owner HTML/API read models
ProfileMediaService          authorized derivatives/playback
ProfileSearchService         revision-bound authorized index
```

Services, not templates/routes, enforce ownership, authorization, versioning,
idempotency, and publication atomics.

## HTML and JSON contracts

Recommended JSON namespaces:

```text
GET  /api/v1/profiles/<slug>/public/<destination>
GET  /api/v1/profiles/<slug>/connections/<destination>
GET  /api/v1/profile/draft
GET  /api/v1/profile/preview/public
GET  /api/v1/profile/preview/connections
POST /api/v1/profile/draft/items              Profile-native content or existing-source reference only
PATCH /api/v1/profile/draft/items/<opaque_key>
POST /api/v1/profile/publications/<audience>/review
POST /api/v1/profile/publications/<audience>/publish
POST /api/v1/profile/publications/<audience>/withdraw
GET  /api/v1/profile/commands/<idempotency_key>
GET  /api/v1/profiles/<slug>/media/<projection_key>/<derivative>
GET  /api/v1/profiles/<slug>/voice/<projection_key>/audio
```

Exact paths may be refined in implementation, but Public, Connections, Owner,
preview, command, and byte retrieval contracts remain separate. Commands use
same-origin proof, expected version, idempotency key, and typed envelopes.

Every state-changing endpoint also requires anti-CSRF proof. Public endpoints
never accept a caller-supplied actor/audience override. Connections endpoints
require authenticated active-relationship authorization. Owner endpoints
derive ownership server-side. Command-status lookup is owner/key scoped.

Stable response semantics are:

- `400` malformed/unsupported input with no protected state;
- `401` no valid authenticated actor where authentication is required;
- neutral `404` for unknown, unpublished, unauthorized, blocked, or
  audience-ineligible visitor objects;
- `409` stale expected version, digest mismatch, or lifecycle conflict;
- `410` only for an owner-authorized, deliberately exposed retired command or
  draft resource where existence is safe to disclose; and
- `503` bounded dependency unavailable, with no fixture or broader fallback.

Database access uses an explicit procedure/operation allowlist. Routes and
templates do not issue arbitrary publication, relationship, search, media, or
Voice queries.

Common response fields include schema version, profile slug, resolved mode,
publication revision/version where applicable, destination, projection key,
and content. They never include private source keys, internal owner IDs,
storage URLs, provider proposals, other audience state, or hidden counts.

## Migration and verification

1. Re-fetch current main and registry; prove the candidate IDs do not collide.
2. Register and reserve exact IDs through the Protected schema path before
   apply; record dependencies, forward/verify/rollback/reapply commands and
   the exact starting ledger state.
3. Add idempotent forward migrations and registry entries; never edit applied
   files.
4. Deploy schema through its protected schema gate before code that requires it.
5. Verify schema objects, constraints, procedures, permissions, registry order,
   owner isolation, concurrency, idempotency, and rollback against a clean
   database and production-like staging.
6. Backfill only deterministic identity/slug anchors. Do not auto-publish or
   infer audiences from historical rows.
7. Quarantine ambiguous legacy rows for owner review.
8. Prove rollback, then reapply and reverify to the exact expected ledger
   state before any dependent runtime release.
9. Keep the Profile runtime flag off through schema and code deployment.

Migration rollback removes only newly introduced runtime dependencies/data as
the exact plan permits; it never rewrites applied history or drops shared
foundations. Flag rollback is primary. Destructive schema rollback requires a
separate exact, tested authority.

## Compatibility and cutover

While the feature flag is false, new services may be initialized but cannot
change `/petec`, `/app`, public navigation, sitemap, metadata, Resume, My Story,
Ask Pete, or other product behavior. A failed Profile read never falls through
to a broader/private legacy snapshot.

At cutover, only members with a valid current Public publication receive a
Public Profile root. Compatibility redirects and slug history are explicit,
audited, and reversible. Pete fixture content is imported through the same
member commands and validations as every other member; it is never hard-coded
product logic.
