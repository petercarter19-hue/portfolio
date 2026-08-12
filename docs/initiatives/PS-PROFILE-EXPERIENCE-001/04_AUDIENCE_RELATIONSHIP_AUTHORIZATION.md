# Audience, Relationship, and Authorization Contract

## Audience vocabulary

Profile v1 has two publication audiences and one working mode:

| Term | Meaning | Authentication requirement |
|---|---|---|
| `Public` | Exact material deliberately available to an anonymous visitor, on or off PeerSlate | None |
| `Connections` | Exact material deliberately available to an active, unblocked PeerSlate connection | Required |
| `Owner` | The subject member's private working mode | Required subject ownership |
| `Only me` | Private source or draft state; not a publication audience | Required subject ownership |

`Friends`, `followers`, `recruiters`, `shared`, and `members` are not aliases.
They require a later explicit product and migration decision. A Connections
publication may deliberately include a reference also present in Public, but
Connections is not a client-side layer placed over a Public response.

## Immutable viewer context

Every Profile read or command begins with a server-derived context:

```text
ProfileViewerContext
  actor_member_id        nullable for anonymous
  subject_member_id
  subject_profile_id
  resolved_profile_slug
  mode                   public | connections | owner
  publication_audience   public | connections | none
  relationship_version   nullable opaque row/version token
  profile_auth_epoch
  block_epoch
  request_purpose        html | api | preview | media | search
```

The browser may request a route or action. It may not supply or override the
actor, subject, mode, audience, relationship, or authorization epoch.

## Authorization-before-retrieval sequence

The required order is:

1. resolve and validate the subject Profile and canonical slug;
2. resolve the trusted actor from Easy Auth, if present;
3. apply block precedence in both directions;
4. resolve Owner or active Connection eligibility;
5. in the same database snapshot, fence the decision against the current
   Profile status/auth epoch, bidirectional block epoch, relationship version,
   and audience publication revision;
6. select exactly one current publication revision for the authorized
   audience;
7. retrieve only the items named by that revision;
8. authorize each selected media/audio/download byte route before storage
   access; and
9. serialize only the fields allowed for that mode and purpose.

It is forbidden to retrieve private, Owner, Connections, or other-member data
into a broad payload and filter it in Python, JavaScript, a template, an AI
prompt, or a client cache afterward. Counts, search facets, pagination totals,
empty states, metadata, filenames, and error messages follow the same rule.

## Viewer matrix

| Viewer | Public branch | Connections branch | Owner controls/private drafts |
|---|---|---|---|
| Anonymous | Yes | No | No |
| Signed-in unrelated member | Same payload as anonymous | No | No |
| Active unblocked connection | May navigate to Public preview explicitly | Yes | No |
| Subject owner | Exact Public preview; Connections preview only through an eligible-viewer workflow | No generic audience simulation | Yes |
| Either party blocked | Neutral unavailable result | No | Owner may manage their own private record only |

For the same revision and locale, anonymous and signed-in-unrelated Public
responses must be field-equivalent. Authentication alone never reveals more.

A signed-in viewer blocked in either direction receives the neutral blocked
result even when the same Profile has an anonymous Public branch. Blocking is
identity-bound: it cannot prevent a person from using an unrelated anonymous
session to view genuinely Public material. The product must disclose this
limit and must not claim that blocking erases Public internet visibility.
Public responses begin `no-store`, so no shared cache may serve a response
that bypasses the signed-in block check.

## Relationship lifecycle

Connections requires an additive, versioned service contract:

```text
none -> outbound_pending -> connected -> disconnected
   |         |                 |            |
   |         +-> declined      +-> blocked  +-> new_request_required
   +-> inbound_pending
   +-> expired
```

- Request, accept, decline, cancel, expire, disconnect, block, unblock, and a
  later reconnect request are explicit, idempotent commands.
- Reciprocal pending requests are resolved atomically into one accepted
  connection or one deterministic surviving request; two independent pending
  rows for the same unordered pair are forbidden.
- A block in either direction wins over every connection or request state.
- Blocking atomically cancels pending requests, ends active connections, and
  advances the relationship/authorization epoch.
- Unblocking never restores a request, connection, publication access, or
  cached authorization. A new request is required.
- Disconnect and block invalidate Connections reads, search, media, audio,
  downloads, preview links, and server caches immediately.
- Relationship events are append-only audit facts; current relationship state
  remains separately queryable.
- Reconnection creates new lifecycle history; it never overwrites or reuses a
  prior connection event sequence.
- Concurrency uses opaque expected-version checks and unique unordered-pair
  constraints for current request/relationship state.

Connections is a hard dependency of the complete Profile release target.
Until the hardened relationship service, authorization fence, and moderation
dependencies pass, the Connections branch, Connections preview, and Connect
control remain absent. Public plus Owner may be reviewed as an explicitly
narrower enablement slice, but it may not be called the complete Connections
release. Messaging is not Profile v1 and remains hidden.

## Connections preview

`View as public` is always available to the owner because it runs the real
anonymous Public query. A Connections preview is available only after the
relationship service is complete and the owner selects an actual active,
unblocked connection who remains eligible at retrieval time. The server uses
that viewer's real relationship/version fence to render exactly what that
viewer could retrieve; it does not grant a relationship or expose the
viewer's private data. If no eligible connection exists, the interface shows
eligibility guidance rather than a simulated Connections response. Preview
URLs remain owner-only and non-shareable.

## Concrete authorization fence

Every Connections HTML/API/search/count/byte response is authorized within a
single consistent database snapshot using all of:

- current active Profile status and `profile_auth_epoch`;
- current audience publication root and immutable revision ID;
- current unordered relationship row plus opaque version;
- current bidirectional block rows and `block_epoch`; and
- current actor/subject status.

Request, accept, decline, cancel, expire, disconnect, block, unblock, Profile
disable, audience withdrawal, and publication-root advancement atomically bump
the relevant epoch/version. The final allow decision is rechecked immediately
before returning rows or storage bytes. An application-layer cache, index, or
previous viewer context cannot replace this fence.

## Neutral failure behavior

Unavailable slug, unpublished Profile, missing destination, unauthorized
audience, blocked relationship, revoked item, and unknown projection use the
same non-enumerating response family. Public HTML normally returns neutral
404. Authenticated APIs return a stable `not_found` or `unavailable` envelope
without revealing whether the object or broader audience exists.

Owner-only validation may explain a private draft problem after ownership has
been proven. No public error exposes private IDs, audience names, source
versions, filenames, transcript proposals, relationship details, or counts.

## Cache, session, and return rules

- Owner, Connections, exact-preview, and authenticated command responses are
  `private, no-store`.
- Public Profile responses begin `no-store` in v1. Public caching may be added
  later only with an audience-safe publication revision key and immediate
  withdrawal invalidation.
- Profile API responses never use the Flask/browser-local Workshop cookie as
  identity; Easy Auth remains authoritative.
- On pageshow/visibility restoration, private shells revalidate session and
  relationship state before showing previously rendered protected content.
- Expired write requests are not automatically replayed.
- Sign-in preserves a validated same-origin Profile GET path and query. It
  never carries private content, a fragment, or a bearer preview token.

## Required security proof

Before enablement, automated tests must use at least two owners, one active
connection, one unrelated member, one pending request, and bidirectional block
states. They must prove no cross-owner retrieval or mutation through HTML,
API, search, counts, media/audio bytes, downloads, preview, cache restoration,
or direct opaque-key requests.
