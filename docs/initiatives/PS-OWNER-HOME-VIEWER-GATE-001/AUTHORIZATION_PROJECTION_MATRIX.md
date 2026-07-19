# PS-OWNER-HOME-VIEWER-GATE-001 Authorization and Projection Matrix

## Decision

Authorization is a server decision made before content retrieval. A profile slug, entity key, relationship claim from the browser, preview control, or client-side hidden state is never authorization. Every projection request resolves an actor, a subject, a requested mode, and a purpose; rejects impossible combinations; then queries only the rows allowed for the resolved context.

Current code and schema do not provide this complete service. The matrix below is the required future contract, not a claim that the viewer modes are live.

## Shared response envelope

Successful JSON projections use one versioned, audience-safe envelope:

```json
{
  "schema_version": "slate-projection.v1",
  "subject": {"profile_key": "opaque", "profile_slug": "member-slug"},
  "viewer_mode": "public",
  "authorization_version": "opaque-version",
  "generated_at": "ISO-8601 UTC",
  "sections": [],
  "capabilities": {"can_preview": false, "can_manage": false}
}
```

Only fields authorized for the resolved mode may enter the envelope. Redaction after broad retrieval is prohibited. `capabilities` is server-derived and is not an authority input. Internal user IDs, SQL IDs, email, identity issuer/subject, Capture bodies, private notes, discarded proposals, source audio, access-grant internals, and unpublished records are never included unless a separate owner-only contract explicitly requires them.

## Matrix

| Viewer mode | Identity source | Records the server may retrieve | Records the server must not retrieve | Required server filter | Route/API behavior | Cache rule | Revocation behavior | Required negative-access tests |
|---|---|---|---|---|---|---|---|---|
| Owner | Trusted `get_current_identity()` result mapped through `identity.user_key` to one active app user/profile | The owner's bounded Home summaries; owner-manageable draft/review metadata; the owner's active canonical records; exact owned source/version references needed for management; owner preview through a separate preview purpose | Any other owner's private records; raw content not needed for the response; deleted body text; other members' identity or relationship internals | `owner_user_id = actor_user_id` and `owner_profile_id = actor_profile_id` in every procedure; active/deleted status applied in SQL; purpose limits returned columns | HTML owner routes redirect anonymous callers to sign-in. JSON owner routes return `401` when anonymous. Unknown or foreign opaque selectors return non-enumerating `404`. | `Cache-Control: private, no-store`; no shared response cache; no browser persistence of payloads | Signing out ends access immediately. Ownership does not survive account deactivation. Deletes/tombstones appear on the next read. Concurrency conflicts return a fresh version and no silent overwrite. | Cross-owner keys, sequential-user session reuse, foreign profile slug, foreign Moment/Placement/grant key, deleted Capture, inactive profile, forged capability/mode, query/body parameter pollution |
| Selected person | Trusted signed-in identity plus a current, unexpired, unrevoked `entity_access_grants` row created by the subject owner | Only the published/approved projection entity and exact referenced records covered by an active `view` grant; audience-safe subject identity | All owner drafts and review queues; Captures and source audio; unconfirmed/deleted Moments; entities outside the grant; other selected people; connection-only/member-only/public-excluded fields | Resolve grantee from actor on server; require matching entity, owner, `access_level` containing view, `revoked_at_utc IS NULL`, and unexpired time; apply block and active/publication constraints; use one authorization version | Authenticated JSON/HTML only. Missing, forged, expired, or inaccessible selector returns non-enumerating `404`. A previously issued opaque grant URL may return `410 access_changed` only when doing so cannot reveal a new subject. Never redirect to a broader public projection automatically. | `private, no-store`; grant tokens/keys must be opaque and absent from referrers/logs; do not cache by subject without actor and authorization version | Revoke/expire/block increments the subject authorization version in the same transaction. Subsequent reads fail before content retrieval. Existing pages must replace content with an access-changed state on refresh/focus/retry; no stale fallback | Grant for user A used by user B; expired/revoked grant; grant to entity X used for Y; owner deactivation; block either direction; unpublished/withdrawn version; URL/key guessing; replay after revocation; response and error body privacy |
| Connection | Trusted signed-in identity plus an active `member_connections` row between normalized user IDs | Only approved/published projection records explicitly marked for the connection audience and allowed by the current manifest | Selected-person-only items; public-excluded items not marked for connections; all private/draft/source records; inferred connection data; records of ended connections | Actor-derived normalized pair, `connection_status = active`, no block either direction, active subject/entity, current published projection, audience match; authorization and projection in one transaction/snapshot | Authenticated route. Not connected, ended, blocked, or missing subject returns the same non-enumerating `404`. No fallback to authenticated-member content inside the response; the client may make a separate public/member request after navigation. | `private, no-store`; no CDN/shared cache; authorization version includes connection and block state | End connection or block atomically invalidates connection access. Next read removes content. Open pages receive no cached content on retry and show access changed, not a partial stale view | Pending request mistaken for connection; ended pair; reversed/forged pair; connection to owner A used for B; block precedence; race between read and disconnect; stale authorization version; cross-owner payload inspection |
| Authenticated member | Trusted signed-in identity. No connection or selected-person claim is implied. | Only approved/published projection records explicitly marked for all authenticated members | Connection, selected-person, private, draft, review, Capture, source, owner-control, and unpublished content | Active actor plus active subject/entity; no block; current published manifest with authenticated-member audience; actor and subject can differ; SQL projection selects only permitted references | Authenticated route. Anonymous is `401` JSON/sign-in redirect HTML. Missing, blocked, inactive, or unavailable subject is non-enumerating `404`. | `private, no-store`; mode and actor must be part of any future cache key, but no response caching is allowed in the first release | Block, withdrawal, subject deactivation, or audience narrowing increments authorization version and removes content on next request. Never keep a cached member view as a public fallback. | Anonymous request; inactive actor; blocked actor; member-only record requested from public endpoint; audience narrowed during request; subject enumeration; owner-only fields absent from serialized bytes |
| Public | No member identity. Subject is selected by a validated public slug/key and resolved server-side. Signed-in state must not broaden a public endpoint. | Only active, approved, currently published records in the public projection manifest, at exact referenced versions, plus explicitly public profile fields | Every non-public audience; raw Capture/revision/audio; drafts/proposals; deleted content; connection/grant data; owner controls; emails and internal IDs; future scheduled versions | Subject active and public; entity active/approved/published; current non-withdrawn public manifest; exact version references; no unreferenced canonical rows | Public route returns `200` for a published projection. Unknown, private, unpublished, withdrawn, deleted, blocked-by-policy, or invalid subject returns non-enumerating `404`. Empty-but-published may return `200` with an honest bounded empty projection. | First release: `public, no-store` until atomic invalidation and cache-key verification exist. A later cache may use subject plus publication/authorization version, short TTL, purge-on-withdrawal, and never `stale-if-error`. Static assets may use normal immutable caching. | Withdrawal, deletion, visibility narrowing, or profile deactivation invalidates the publication version atomically. The next origin read is `404` or the new safe projection; no stale content may be served on error | Unpublished/withdrawn/private subject; slug case/encoding/traversal; signed-in caller cannot see more; old publication-version URL; deleted referenced Moment; cache purge; response headers/body do not expose private fields |

## Audience vocabulary gate

The current schema allows `private`, `shared`, `connections`, `recruiter`, and `public`. The current Roadmap describes owner, selected person, connection, authenticated member, and public modes. These are not interchangeable.

Before any viewer implementation, a migration and decision record must:

1. Define canonical stored audiences for `selected_person` and `authenticated_member` (or an equally explicit normalized model).
2. Decide how existing `shared` and `recruiter` rows are audited and migrated. No silent alias is allowed.
3. Keep `connection_preferences.discoverable_audience` separate from content visibility. Discovery opt-in is not permission to retrieve a Slate.
4. Add an opaque grant key and concurrency/version field if selected-person URLs or management controls need them; sequential `grant_id` is not a public selector.
5. Define one monotonically changing authorization/publication version that changes on grant, relationship, block, audience, publication, placement, deletion, and profile-status changes.

## Authorization-before-retrieval sequence

1. Parse the route and requested mode against a fixed allowlist.
2. Resolve the actor from the trusted request identity, or explicitly mark the request public.
3. Resolve the subject without loading canonical content.
4. Compute mode eligibility from ownership, current grant, active connection, block state, publication status, expiry, and purpose.
5. If unauthorized, return the mode's non-enumerating response before querying content tables.
6. Query a reference-only projection manifest and the exact approved versions through an audience-scoped stored procedure.
7. Serialize from the narrow rows returned; reject unknown fields at the boundary.
8. Recheck or bind to the authorization version before returning so a concurrent revocation cannot release a superseded response.
9. Set the required cache and content-security headers and emit privacy-safe outcome telemetry.

## Preview rule

Owner preview is not an owner-shaped payload with elements hidden in JavaScript. The owner selects a mode, and the server executes the same authorization rules, stored projection query, view model, and serializer used by that live mode. The only preview-specific fields are an outer owner-only banner and non-content metadata such as `is_preview: true`. The owner cannot select another member as a selected-person or connection viewer until a real current grant/relationship exists; an explicitly labeled eligibility explanation may be shown instead.

## Error contract

| Condition | JSON | HTML/product state | Content rule |
|---|---|---|---|
| Anonymous on protected route | `401` with stable code `authentication_required` | Sign-in redirect preserving only a validated local return path | No subject or content fields |
| Unknown or unauthorized subject | `404` with stable code `not_found` | Neutral unavailable state | Same body shape/timing class as practical; no existence hint |
| Known previously authorized grant becomes unusable | Optional `410` with `access_changed`, only for an opaque grant context already possessed by this actor | Revoked/access-changed state with safe navigation | Clear previously rendered content; never return stale payload |
| Concurrency/version changed during request | `409` with `state_changed` and a fresh opaque version | Refresh/retry state | Do not return a mixed old/new projection |
| Dependency timeout/unavailable | `503` with `temporarily_unavailable` and retry guidance | Failure state with explicit Retry | Do not substitute fixtures, last-known private data, or broader audience content |
| Malformed selector/mode | `400` with `invalid_request` | Correctable request state where applicable | Do not echo unsafe values |

## Gate outcome

**Conditional.** Owner-only reads can build on the existing identity and ownership boundaries. Selected-person, connection, authenticated-member, public, and exact preview implementation must wait for the vocabulary/migration, server authorization/projection service, publication/grant lifecycle, and design acceptance gates described in this package.
