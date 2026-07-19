# PS-OWNER-HOME-VIEWER-GATE-001 Architecture

## Status and scope

This document defines future implementation boundaries for PS-HOME-001, PS-VIEW-001, PS-PREVIEW-001, and the relevant PS-SETTINGS-001 integration. It changes no product code, schema, route, or visual composition.

The architecture has two deliberately different trust paths:

1. **Owner Home:** trusted signed-in identity to bounded owner-only summaries and actions.
2. **Slate projection:** actor plus subject plus mode plus purpose to an audience-scoped, reference-only projection.

Both reuse the current identity boundary and canonical Capture/Moment/Placement foundations. Neither uses the legacy dashboard as a shortcut or copies canonical content into a Home/viewer table.

## Architectural principles

- Authorize before retrieving content. Do not retrieve broad owner data and redact in Python or JavaScript.
- One canonical record, many governed references. Home and viewer projections point to exact source versions.
- A route selector identifies a subject; it never proves access.
- Preview executes the live viewer path. It is not a privileged payload with CSS hiding.
- Private by default. New data and new projection records begin private/unpublished.
- Finite by contract. Counts and response sizes are enforced server-side.
- Failure closes access. No fixture, stale payload, broader audience, or last-known private response is a fallback.
- Owner settings change defaults prospectively unless an explicit impact review says otherwise; they never silently republish existing content.
- Approved future capabilities remain visible through the Voice-style capability-preview pattern: production-quality silhouette, genuinely disabled control, visible **Coming later** label, no fabricated payload, and no client-side activation.

## Route boundary

The exact public/profile navigation map remains an owner/manager decision. These endpoint shapes are proposed implementation contracts and must not be treated as live routes until a later package reserves and implements them.

| Purpose | Proposed endpoint | Authentication | Contract |
|---|---|---|---|
| Owner Home HTML | `GET /app` | Required | Replace the current protected landing only when the complete Home visual/functional gate passes |
| Owner Home data | `GET /api/v1/owner/home` | Required | `owner-home.v1`, bounded by FINITE_HOME_CONTRACT.md |
| Owner My Slate preview HTML | Route-map decision required; do not reuse the public static preview silently | Required, owner only | Outer preview context plus the exact live projection result |
| Owner preview data | `GET /api/v1/owner/slate-preview?mode=<mode>&viewer_account_key=<optional>` | Required, owner only | Runs the real mode resolver/query/serializer; selected/connection preview requires a real eligible viewer |
| Authenticated viewer data | `GET /api/v1/slates/<profile_key>?mode=<selected_person|connection|authenticated_member>` | Required | Mode is a request, not authority; server may reject or resolve only the exact requested mode |
| Public viewer data | `GET /api/v1/public/slates/<profile_slug>` | None | Public published projection only; signed-in cookies do not broaden it |
| Viewer HTML | Final path deferred to route-map package | Depends on mode | Server supplies a mode-scoped bootstrap or the frontend calls the matching endpoint |

The public endpoint uses a slug because it is intended to be discoverable. Authenticated endpoints prefer an opaque profile key. Sequential database IDs and `grant_id` values never appear in routes. Existing Pete fixture routes remain distinct until a separately approved convergence/migration package proves equivalence and preserves canonical redirects.

## Application boundaries

### Request identity

Continue to use `identity.get_current_identity()` and the existing trusted Easy Auth parsing. The application maps `identity.user_key` to exactly one active user/profile. New viewer code must not parse identity headers independently or add a second session model.

### `ViewerContextResolver`

Future service responsibility:

```text
resolve(actor_identity | public, subject_selector, requested_mode, purpose, now)
  -> AuthorizedViewerContext
```

The resolver performs only identity, subject, relationship/grant/block, profile/entity status, audience, publication, expiry, and authorization-version work. It does not fetch Moment/Capture bodies. Its output contains opaque actor/subject keys, resolved mode, purpose, allowed projection entity/version, and authorization version. It is immutable for the request.

Allowed purposes are a closed enum: `live_view` and `owner_preview`. `owner_manage` is separate and cannot call viewer procedures accidentally.

### `SlateProjectionService`

Future service responsibility:

```text
get_projection(authorized_context)
  -> SlateProjectionViewModel
```

It calls one audience-scoped stored procedure using only server-resolved identifiers. The procedure joins a current reference-only projection manifest to exact approved canonical versions, validates the same authorization version, and returns only serializer-approved columns. It must never accept `owner_user_id`, `grantee_user_id`, or visibility from the request body/query.

### `OwnerHomeService`

Future service responsibility:

```text
get_home(owner_identity)
  -> OwnerHomeViewModel
```

It resolves the owner using the current identity adapter and invokes an owner-scoped stored procedure that enforces the nine-object maximum. It may call separately released insight and connection adapters, but an absent adapter yields an unavailable/omitted category, never a fabricated item.

### `PreviewService`

Future service responsibility:

```text
get_preview(owner_identity, requested_mode, optional_real_viewer_key)
  -> PreviewEnvelope(SlateProjectionViewModel)
```

It proves the requester owns the subject, then calls `ViewerContextResolver` with `owner_preview` and calls the same `SlateProjectionService` and serializer used by live viewers. Public preview uses the exact published public projection. Selected-person/connection preview requires a real grant/relationship; if none exists, it returns eligibility guidance without projection content. Preview cannot override a block, expiry, withdrawal, or missing publication.

### Serializer boundary

Separate explicit serializers produce `owner-home.v1` and `slate-projection.v1`. They use allowlisted fields and fail closed on an unexpected field/category. Templates receive view models, not database rows. Capability flags are computed server-side from context and purpose.

### Capability-preview registry

Future Home/viewer features selected for the approved composition are rendered before activation from a small versioned registry owned by the release package. Each entry contains only an allowlisted capability key, approved display label, `state = coming_later`, concise future-purpose copy, and optional documentation destination. It contains no actor/subject selector, member content, record count, result, grant, or authorization claim.

The registry follows the accepted Voice pattern. Its frontend map is presentational only. Native disabled/`aria-disabled` controls remain outside forms and make no API request. A browser flag, DOM edit, or query parameter cannot turn the capability on. Moving from `coming_later` to `available` requires the real route/service, server feature flag, authorization/lifecycle tests, deployment proof, and owner/manager acceptance.

## View models

### `OwnerHomeViewModel`

Required top-level fields and maxima are defined in FINITE_HOME_CONTRACT.md. Every object uses opaque external keys and a bounded summary. `state_version` changes when any selected owner-state input changes. The endpoint rejects a serialized body larger than 64 KiB and records a safe contract-violation metric without logging content.

The `availability` map may identify an approved category as `coming_later`. That value causes the frontend to render the category's disabled capability preview in the same one-slot budget. It never causes a category data query and never carries sample content.

### `SlateProjectionViewModel`

Required top-level fields are defined in AUTHORIZATION_PROJECTION_MATRIX.md. A section contains:

```json
{
  "section_key": "opaque",
  "kind": "moment",
  "order": 10,
  "content": {
    "moment_key": "opaque",
    "version_number": 3,
    "title": "bounded authorized text",
    "summary": "bounded authorized text"
  }
}
```

The exact section types must be allowlisted by the implementing package. Presentation metadata may include order, supported layout token, and accessibility reading order. It cannot contain a second authoritative copy of Moment/Story/resume facts. Unknown section types are excluded with an observable safe error or fail the response according to the versioned contract; they are never rendered as raw JSON.

### `PreviewEnvelope`

Adds only `is_preview`, requested/resolved mode, generated time, and a truthful context explanation outside the live `SlateProjectionViewModel`. Removing the envelope must leave byte-equivalent projection content for the same context and authorization version.

## Stored procedure/query boundary

Proposed procedure responsibilities and names, subject to the migration package's naming review:

- `sp_owner_home_get_v1(@user_key)` resolves the owner internally and returns bounded result sets for Home.
- `sp_viewer_context_resolve_v1(@actor_user_key, @public_request, @subject_key_or_slug, @requested_mode, @purpose, @now_utc)` returns no content.
- `sp_slate_projection_get_v1(@context_key, @authorization_version)` returns only exact permitted references and audience-safe projected fields.

A stronger implementation may combine context resolution and projection in one procedure/transaction to eliminate a time-of-check/time-of-use gap. If split, the context must be server-issued, short-lived, integrity-protected, actor-bound, purpose-bound, and revalidated against `authorization_version` in the projection query. A browser must never be able to manufacture it.

Database access continues through the stored-procedure allowlist in `services/database_service.py`. Dynamic SQL based on mode, client-supplied table names, or generic query endpoints is prohibited.

## Authorization-before-retrieval transaction

For viewer and preview requests:

1. Validate selector/mode syntax and resolve trusted actor/public state.
2. In one database snapshot/transaction, resolve the active subject without content.
3. Apply ownership/grant/connection/member/public rules, expiry, block precedence, publication state, entity activity, and requested purpose.
4. Return the neutral negative result before joining canonical content if authorization fails.
5. Bind to the current authorization/publication version.
6. Join only the manifest's exact references to approved source versions and select only audience-safe columns.
7. Verify the bound version remains current before commit/return.
8. Serialize through the versioned allowlist.

This sequence is required in SQL-level integration tests. A Python test that merely hides fields is insufficient.

## Canonical references and publication manifests

`moment_placements` already demonstrates the correct body-free pattern: owner-scoped reference to one exact confirmed Moment version and one eligible Slate entity. Viewer projection should extend this idea, not copy Moment bodies.

`entity_publication_versions.snapshot_json` currently accepts arbitrary valid JSON. It is not safe to treat that column as an approved content snapshot. Before use, the schema package must choose and enforce one of these approaches:

1. Convert it to a versioned **reference-only manifest** containing entity/Moment/version keys, order, permitted presentation metadata, and no canonical text; or
2. Add a normalized publication-manifest table with exact references and deprecate content-bearing snapshots.

The decision must include validation, legacy-row audit, size limits, rollback, and a test proving canonical body edits are not duplicated silently. A publication lifecycle capable of creating, publishing, withdrawing, and invalidating a manifest is future work and cannot be smuggled into the viewer route package.

## Schema and migration impact

No migration is part of this planning branch. A future reversible migration is required before non-owner viewer work and should include:

- canonical audience vocabulary for owner/private, selected person, connection, authenticated member, and public; explicit audit/mapping for legacy `shared` and `recruiter` values;
- opaque grant keys and row-version/concurrency support for `entity_access_grants` if grant management/URLs require them;
- a reference-only projection manifest with schema version and bounded ordered items;
- an authorization/publication epoch or version changed in the same transaction as grant, relationship, block, audience, publication, placement, deletion, or profile-status changes;
- supporting indexes for actor/subject/mode/status/expiry queries;
- procedures for scoped context resolution and projection retrieval;
- migration ledger entry, isolated apply/verify/rollback/reapply proof, and production post-deploy verification.

The migration must preserve tenant ownership and existing data. It must not infer that `shared` means selected person or that `recruiter` means authenticated member. Ambiguous legacy rows stay inaccessible until explicitly resolved.

Owner Home can use a smaller owner-read migration/package first, but it must not pre-create fake insight/connection data or modify publication vocabulary incidentally.

## Lifecycle and concurrency

### Owner Home

- It is a read model, not a new system of record.
- Home selections are recomputed from current owner state; no copied Home-card table.
- Actions navigate to the authoritative workflow. Any future inline mutation requires its source contract, idempotency, row version, and explicit confirmation.
- Deleted/inactive inputs disappear or use an approved tombstone. Stale versions return `409 state_changed` rather than silent action.

### Viewer projection

- Draft -> approved -> published/permissioned -> withdrawn is an explicit lifecycle owned by a future publication package.
- Grant creation/revocation/expiry, connection activation/end, block/unblock, audience changes, and deletion alter authorization version atomically.
- Projection reads bind to exact canonical versions; later canonical edits are not silently exposed. The owner must explicitly update/publish a new projection version.
- Withdrawal or revocation is deny-first. A dependency failure cannot extend access.
- Idempotent lifecycle mutations use opaque keys and expected row versions. Duplicate retries do not create duplicate grants/publications.

## Caching

- Owner Home, authenticated viewer, selected-person, connection, member, and owner-preview responses: `Cache-Control: private, no-store`.
- Public projection first release: `Cache-Control: public, no-store` until atomic invalidation and header/CDN verification are proven.
- No service worker, localStorage, IndexedDB, server response cache, or stale-on-error for projection payloads in the first release.
- Static fingerprinted assets may use normal immutable caching.
- A later public cache requires a key containing subject plus publication/authorization version, bounded TTL, purge-on-withdrawal proof, no user-varying fields, and live CDN/browser verification.
- Error responses must also avoid caching when they could freeze access state or reveal subject existence.

## Performance budgets

| Contract | Budget |
|---|---|
| Owner Home objects | Maximum 9 |
| Owner Home review items | Maximum 3 |
| JSON body | Maximum 64 KiB uncompressed for either endpoint |
| Owner Home database calls | 1 core plus at most 2 independently timed optional adapters; never per item |
| Viewer database calls | 1 combined authorization/projection call preferred; maximum 2 inside one consistent authorization boundary |
| Database p95 | <= 250 ms under founding-alpha test profile |
| Server JSON p95 | Home <= 600 ms; viewer <= 500 ms under founding-alpha test profile |
| Query growth | Constant with respect to eligible record count after applying fixed limits; no N+1 |

Implementing packages must record the dataset/load assumptions and collect p50/p95/p99 plus query count. Performance failure is a release blocker when it risks retries, timeouts, or authorization inconsistency.

## Privacy-safe telemetry

Allowed dimensions:

- route contract and schema version;
- requested and resolved mode as an enum;
- outcome code (`success`, `not_found`, `auth_required`, `access_changed`, `state_changed`, `dependency_failure`);
- duration bucket, query count, serialized size bucket, object counts by category;
- opaque request/correlation ID;
- deployment/build version.

Prohibited telemetry:

- Capture/Moment/profile text, transcript, audio URL, email, name, slug, raw user/profile/entity/grant keys, identity issuer/subject, connection graph, query strings containing selectors, or response bodies.

Security audit events for grant/publication changes may store approved opaque record keys and actor/subject account keys in the protected audit store, not general application logs. Observability access and retention follow the governance/consent package; this package creates no new analytics consent.

## Failure and recovery

- Identity unavailable: protected routes fail closed and offer sign-in/retry; no dev identity in production.
- Database unavailable/timeout: `503 temporarily_unavailable`; no fixture, cache, or public fallback.
- Authorization changes mid-read: discard result and return `409 state_changed` or rerun once within the request budget.
- Missing/deleted referenced version: omit the item only if the manifest contract explicitly allows partial projection and record a safe integrity error; otherwise fail the projection. Never substitute the newest version.
- Malformed manifest/unknown section: fail closed, alert via content-free telemetry, and do not render raw data.
- Partial Home adapter failure: return safe independent core categories plus an explicit unavailable state for that optional category.
- Client retry: safe GET only, bounded exponential backoff, user-invoked Retry available, focus/announcement managed, no duplicate mutation.
- Deployment rollback: application and migration rollback must be tested as a pair. Feature flags default off for viewer/preview. Turning a flag off returns honest unavailable/404 behavior and does not affect canonical owner data.

## Owner Settings integration

PS-SETTINGS-001 is relevant only where a future settings control changes default audience or access behavior. The current Settings route is protected but informational.

Required future rules:

- Default visibility applies only to new drafts/placements unless the owner explicitly selects and confirms existing records after an impact preview.
- Discovery/connection preferences do not publish content.
- Audience changes show affected projection, viewers, and withdrawal consequences before commit.
- Export and deletion use their own lifecycle packages and do not rely on Home/viewer payloads as complete account data.
- Settings writes require row-version concurrency, audit, CSRF protection, and two-owner isolation.

## Security controls

- CSRF protection for every mutation; GET endpoints never mutate.
- Strict selector validation, parameterized stored procedures, and allowlisted procedure calls.
- Content Security Policy and output encoding for authorized member text.
- No open redirects in sign-in return paths.
- Rate limits keyed without logging raw subject selectors; separate public and authenticated budgets.
- Constant/normalized negative response shape and practical timing to reduce enumeration.
- Block precedence and deny-first behavior are tested at SQL, service, API, and browser levels.
- Credentials, Easy Auth headers, grant secrets, and private payloads never enter HTML data attributes, URLs, referrers, client telemetry, screenshots, or logs.

## Gate decision

**Conditional.** The owner-only finite Home path can be implemented first against real owner data after its design package and bounded read contract are approved. All non-owner projections and exact preview remain blocked on the audience decision, reversible migration, authorization/projection service, real grant/publication lifecycles, route map, and visual acceptance. Existing fixture pages and schema tables are not release evidence for those capabilities.
