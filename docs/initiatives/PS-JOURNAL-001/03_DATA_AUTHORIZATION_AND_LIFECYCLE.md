# PS-JOURNAL-001 — Data, Authorization, and Lifecycle Architecture

## Architectural principle

Journal is a read/write experience over canonical Moments; it is not a second
canonical content object. The database may contain Journal presentation,
curation, and publication metadata, but never another authoritative narrative
body that can drift from the Moment.

## Logical record allocation

| Logical record | Owns | Must not own |
|---|---|---|
| Capture source/revision | Original typed input, retained voice/media source references, correction/version evidence, processing/lifecycle | Public audience, Story layout, résumé copy, Journal membership |
| Moment | Member-approved canonical meaning/content, versions, owner, lifecycle, provenance | Public publication by implication, room-specific layout, AI interpretation as fact |
| Journal presentation metadata | Pin/emphasis, curated inclusion/order, section/chapter/display treatment, short presentation-only curation annotation, purpose/audience projection state | Copied Moment body/source; substantive event, claim, reflection, or narrative; independent facts. Substantive new text must be a Moment or governed projection. |
| Placement/reference | Exact eligible Moment version relationship to a downstream domain | Destination content copy, authorization grant, automatic publication |
| Projection | Purpose-specific wording/selection/layout and its audience/lifecycle, all linked to canonical versions | Silent mutation of canonical Moment, inferred audience |
| Insight/observation | Private source-linked interpretation, confidence/uncertainty, lifecycle and feedback | Canonical fact, public claim by default, diagnosis |
| Share/access grant | Exact subject, grantee/audience, purpose, state, expiry/revocation | Content copy or ownership transfer |

## Derived Journal membership

The owner Journal query includes each eligible Moment where:

- `moment.owner_id` resolves from the trusted session;
- the Moment is in a member-saved/active lifecycle state appropriate to the
  requested owner view;
- source deletion/restriction policy permits the selected fields; and
- archive/delete filters are applied explicitly.

No `moment_placement(destination='journal')` and no `journal_entry.body` is
created. Optional presentation metadata is left-joined by owner and Moment key.
Absence of metadata means default chronological presentation, not absence from
Journal.

## Save Moment application operation

The target service boundary accepts trusted-session owner, client idempotency
key, input/source reference or content, accepted member text, origin context,
and explicitly selected metadata. It performs:

1. validate identity, ownership, limits, type, and accepted content;
2. create/pin the source or source revision;
3. create the canonical Moment and first member-saved version, or complete the
   approved compatibility transition from an existing source/proposal;
4. record safe audit metadata and commit;
5. return Moment identity/version plus truthful saved state;
6. schedule optional enrichment after commit; and
7. allow the derived Journal query to return it immediately.

The operation does not publish, create a Placement, write a downstream
projection, create a message, or broaden access. If orchestration cannot be one
database transaction, the package must define idempotent state transitions and
compensation so the member cannot receive a false successful save.

## Suggested logical lifecycle

Exact database enums remain an implementation decision, but the behavior must
distinguish:

```text
source: draft | processing | ready | failed | archived | deletion_pending | deleted
moment: saving | active | archived | deletion_pending | deleted | invalidated
version: member_saved | proposed | accepted | superseded | invalidated
projection: draft | previewable | published | revoked | archived | deleted
insight: proposed | confirmed | corrected | dismissed | too_personal |
         expired | invalidated | deleted
```

`saving` must not be exposed as a committed Journal Moment. `member_saved`
means the owner explicitly saved that content; it does not mean AI verified the
facts. Labels in the UI should use plain language.

## Authorization-before-retrieval

Every Journal query receives a server-resolved viewer context:

- viewer identity or logged-out state;
- owner identity resolved from canonical route/record, never trusted from a
  browser claim;
- relationship, selected-person grant, block, and revocation state;
- requested audience/purpose;
- publication and lifecycle state;
- permitted field/source/media scopes.

The repository/service builds the authorized predicate before retrieving
records. A serializer removes fields only as a second defense, not the primary
authorization mechanism. Search, counts, pagination, facets, comparisons,
media tokens, and AI grounding use the same predicate.

## Viewer-mode retrieval matrix

| Data class | Owner | Selected person | Connection | Member | Public |
|---|---:|---:|---:|---:|---:|
| Complete active Moments | Yes | No | No | No | No |
| Exact granted/published Moment fields | Yes | Grant only | Audience only | Audience only | Public only |
| Original private source/transcript/audio | Policy | Only explicit separate grant if ever supported | No by default | No | No |
| Drafts/proposals/private versions | Yes | No | No | No | No |
| Private insights/Noticed/Mirror | Yes | No by default | No | No | No |
| Curation/presentation selected for viewer | Yes | Applicable | Applicable | Applicable | Public |
| Hidden-item counts/search facets | Yes | No | No | No | No |
| Owner edit/lifecycle controls | Yes | No | No | No | No |

Any exception requires a separately governed feature and explicit owner grant.

## Audience and publication model

Visibility, access grant, and publication are deterministic application state.
AI may suggest copy or an audience explanation but may not set them. Publishing
a public Journal item pins the exact Moment/projection version and exact
presentation state the owner previewed. A later Moment edit does not silently
change an existing public claim; the owner sees whether to update, preserve, or
revoke the projection.

## Curation model

Journal curation may include:

- feature/hide from this curated view;
- curated order or section/chapter assignment;
- a selected display date when truthful and distinguishable from occurrence
  and save times;
- purpose/audience-specific title or framing in a projection record;
- media treatment reference;
- short presentation-only curation annotation constrained by
  `PS-JRN-JRN-004` (substantive owner text must be a Moment or governed
  projection); and
- exact publication/grant reference.

It may not change the underlying fact, source, owner, or canonical chronology.
Removing curation restores default behavior; it does not delete the Moment.

## Propagation rules

| Trigger | Required propagation |
|---|---|
| Moment edit/new accepted version | Journal owner view updates; pinned downstream/public versions remain stable until explicit update; stale projections become reviewable |
| Archive/restore | Default owner view changes; public/projection behavior follows explicit policy, never implied |
| Delete/deletion request | Stop new retrieval; invalidate tokens/indexes/insights; process sources/media/projections/references under policy; expose retry/audit state |
| Source revoked/deleted | Moment shows truthful provenance/tombstone state; dependent insights/projections are invalidated or reviewed |
| Audience change/unpublish | Revoke affected retrieval, cache, search, AI grounding, media authorization, comparison, and notification paths |
| Block/relationship removal | Recompute selected/Connection access and messaging references before further retrieval |
| Insight corrected/dismissed/too personal | Suppress/recompute according to feedback; never mutate source Moments |

## Search, indexing, and AI grounding

- Owner search indexes only owner-authorized fields.
- Viewer search indexes/query results use audience-specific permitted material;
  no post-filtered global index response is acceptable.
- Index entries contain minimum necessary derived fields and lifecycle/version
  pointers, not raw private sources unless explicitly required and protected.
- Semantic embeddings, if introduced, are private derived data with owner,
  source/version, model, retention, deletion, and invalidation state.
- Ask Slate and return-value jobs receive already-authorized record sets or
  constrained retrieval handles; models do not decide authorization.
- Logs and telemetry never contain private content or embedding payloads.

## Migration and compatibility

Before changing runtime behavior, the implementation package shall inventory:

- released `dbo.captures`, revisions, Moment, Placement, Voice/media, and owner
  stored procedures/tables;
- `/app/capture`, protected review routes, `/api/journal/today`,
  `/api/journal/history`, `/api/journal/responses`, and any fixtures;
- owner Home payload contracts and shell file reservations;
- feature flags, indexes, queues, exports, deletion jobs, audit events, and
  production migration history.

Migration shall:

- preserve existing source/Moment ownership and exact versions;
- avoid inventing Moments from unreviewed legacy prompt responses without an
  explicit owner review path;
- derive Journal membership from existing eligible Moments rather than create
  copies;
- identify any legacy Journal content with no canonical Moment and provide a
  one-time private reconciliation workflow;
- make legacy route/API retirement or compatibility observable and reversible;
- perform two-owner and guessed-ID verification on disposable/synthetic data;
  and
- include a guarded rollback that cannot delete member data created after the
  migration boundary.

## Failure and concurrency contracts

- client idempotency key plus server uniqueness prevents duplicate save;
- optimistic version token prevents stale edit/curation overwrite;
- transaction/compensation distinguishes source safe, Moment safe, enrichment
  failed, and downstream use failed;
- provider callback state is replay-safe;
- queue jobs verify owner, source/version, lifecycle, and permission again;
- partial list/search/source/media failure does not expose another viewer's
  data or replace real rows with fabricated fixtures;
- rate limits do not cause data loss and are scoped to trusted identity/action;
  and
- monitoring uses synthetic identifiers/statuses, never member content.
