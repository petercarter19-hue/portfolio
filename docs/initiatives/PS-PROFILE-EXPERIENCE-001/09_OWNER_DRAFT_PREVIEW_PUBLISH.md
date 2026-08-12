# Owner Draft, Preview, and Publication Lifecycle

## Working-state principle

The owner works on the same recognizable Profile body. Add and Manage open a
contextual sheet or selected-object plane; they do not replace Profile with an
admin dashboard. Private controls and data are never included in visitor HTML
or API payloads.

## State machine

```text
private source
-> private Profile draft/proposal
-> member edits and reviews
-> exact audience preview
-> explicit publish command
-> immutable current publication revision
-> later revise | withdraw | revoke | source-delete review
```

AI or source adapters may create proposals. Only the member can accept exact
wording and initiate a publication command.

## Add something

`Add something` progressively discloses Type, Speak to type, Photo, Video,
retained Voice, File, and Project only when each real dependency is available.
Every path explains retention before input. New material begins private.

Choosing an audience in the composer creates a proposed publication target; it
does not publish on save. Audience and placement remain separate choices.
The canonical save first follows the routing table in document 07; Profile
stores only its native content or an exact adapter reference.

## Manage selected object

The attached inspector shows:

- canonical source and exact source version;
- current approved projection version;
- Public and Connections publication state separately;
- placements and where used;
- featured/order state;
- source changed/stale state;
- public-AI authorization separately;
- processing, availability, retention, and deletion truth; and
- current version/conflict state.

It does not expose private source bodies in a Public/Connections preview.

## Exact preview

- `View as public` runs the real anonymous Public query and serializer in an
  owner-authenticated preview context.
- Owner controls, drafts, private counts, Connections items, source metadata,
  and public-AI controls are absent from the preview payload and DOM.
- Connections preview follows the eligible-viewer contract in document 04: a
  real active, unblocked connection is selected and reauthorized at retrieval
  time. It does not grant or alter a relationship. Without an eligible
  connection, the owner receives guidance rather than a simulated payload.
- Preview URLs are not bearer links and are not shareable.

## Review and publish

The review compares the current audience revision with the candidate draft and
shows additions, removals, reordered placements, audience changes, source
versions, where-used impact, and unavailable dependencies. The member confirms
one audience branch per command.

The Connections revision is the complete manifest a connected viewer may see,
including every Public item the owner also wants present there plus any
Connections-only item. It is not a request-time Public overlay. Connections
review shows Public placements that are included, excluded, or stale relative
to the Public branch. Publishing Public may propose corresponding Connections
changes, but the owner must review and explicitly confirm them; nothing
synchronizes or broadens automatically.

The command requires:

- same-origin proof and authenticated owner;
- anti-CSRF protection on every state-changing form or JSON command;
- idempotency key;
- opaque expected draft and current-publication version tokens;
- exact candidate revision digest;
- revalidation of every source/projection/placement;
- explicit confirmation for audience broadening; and
- atomic current-revision advancement.

A retry with the same owner-scoped idempotency key and identical request
digest returns the original result. Command-status lookup is authorized to
the owning actor and the exact key; a key cannot reveal or replay another
owner's command. A stale
version returns a conflict with no partial publication. Failure leaves the
prior publication intact.

## Consequential actions

| Action | Required outcome |
|---|---|
| Unpublish | Review affected placements; immediately remove target-audience visibility; retain private source |
| Widen audience | Exact broader-audience preview and explicit confirmation |
| Disconnect/block | Immediate Connections invalidation independent of publication editing |
| Revoke media/Voice | Create a new audience revision without affected placements and revoke byte eligibility; never mutate the current immutable revision in place |
| Delete source | Show every current use; separately confirm; revoke projections first; complete distributed deletion truthfully |
| Discard unsaved edits | Explicit confirmation; never silently lose edits on navigation, sheet close, or mobile Back |
| Reorder/feature | Version-fenced placement-only command with accessible alternatives |
| Public-AI opt in/out | Owner-only, exact Public source versions, separate from Profile visibility |

## Conflict and recovery

- Preserve unsaved edits across an expired session where safe, but obscure
  private content and require reauthentication before retrieval or submit.
- Never replay a POST after sign-in.
- On version conflict, preserve the local draft, show what changed, and let the
  member review/reapply; no last-write-wins.
- Processing/transcription failure is attached to the selected source and does
  not disable unrelated Profile content.
- Publish failure shows a stable retry reference and states that the previous
  Public/Connections revision remains visible.
- A client timeout never assumes success; it queries idempotency-command status.
- Withdrawal, revocation, and replacement each create a new immutable revision
  and atomically advance the audience root; retained historical revisions do
  not remain eligible for visitor retrieval.

## Publication history and rollback

Publication revisions are immutable and owner-inspectable. Rollback creates a
new revision from a validated prior manifest; it does not move the current
pointer backward without a new audit event. Withdrawn or deleted material is
not resurrected by rollback.
