# PeerSlate Community Feed implementation architecture

## 1. Status, authority, and purpose

This document converts Pete's 2026-07-31 six-screen visual lock and the
owner-approved SAR-01 through SAR-06 direction into a refined implementation
architecture. It was reviewed against every locked screen and the current
repository integration seams. The review record is
`07_ARCHITECTURE_REVIEW_AND_REFINEMENT.md`.

This is a logical implementation contract. It is not runtime authority, an
approved physical schema, or an approved public API.

- **Primary visual source:**
  `visual-authority/2026-07-31-pete-lock/MANIFEST.md`
- **Owner correction source:**
  `03_OWNER_VISUAL_LOCK_AND_SUPERSESSION.md`
- **Package-local owner decisions:**
  `06_SHARED_AUTHORITY_RECONCILIATION_PROPOSAL.md`
- **Current product truth:** the released Community is still sample/browser-
  local. None of the objects, APIs, interactions, or states below is claimed
  live.
- **Route truth:** the accepted mockups use illustrative browser and shell
  labels. Current authority keeps `Community` at `/the-slate`, with
  `/the-slate/break` as the separate second view.
- **Authority truth:** Pete approved SAR-01 through SAR-06 inside this package.
  Constitution v3.0, Roadmap v3.0, the lean site rules, and
  `CURRENT_BASELINE.yaml` now control. Only a narrow clarification of
  Constitution rule 7 remains a possible shared-authority change; the prior
  multi-document activation map is superseded.
- **Implementation gate:** closed until section 18 and
  `05_VISUAL_STATE_GAP_AND_IMPLEMENTATION_GATE.md` are satisfied.

The words **locked**, **required**, and **recommended** are used deliberately:

- **Locked** means Pete's exact visual or product decision already controls.
- **Required** means a technical or trust invariant must be satisfied by any
  lawful implementation.
- **Recommended** means the runtime initiative should adopt the stated
  implementation choice or record a safer equivalent before code begins.

## 2. Architecture principles

1. **One social truth.** One Community Post owns one authoritative Community
   conversation. Feed cards, Replies & updates cards, selected detail, full
   conversation, catch-up, rails, search results, and counts are projections,
   not editable copies.
2. **Two lawful post origins.** A post is either Community-native social truth
   or an explicit projection/reference to a canonical Slate record. The two
   origins share one publication envelope but never copy Slate source truth
   into Community storage.
3. **Authorization before projection.** The server resolves identity,
   audience, relationship, block/mute, lifecycle, moderation, and attachment
   access before returning content, excerpts, filenames, counts, or existence.
4. **Private before publish.** Composer state is private. Publication requires
   an explicit, server-validated audience. Client-supplied owner, tenant,
   community, or capability fields are never trusted.
5. **AI proposes; people decide.** Feed, catch-up, Spark, ordering, safety, and
   recovery remain usable without generative AI. AI cannot post, reply,
   message, publish, save, delete, link records, or widen audience silently.
6. **Finite by design.** A Feed session has a signed stable window, explicit
   pagination, deterministic seen state, and a real caught-up boundary. New
   arrivals do not move the finish line invisibly.
7. **Horizontal means one post's contributions.** Replies & updates is one
   non-wrapping row. It is not a workflow, project timeline, stage system,
   global popularity shelf, or second Feed.
8. **Visual authority is a dependency.** Each state is compared to its matching
   exact lock. Missing states are not left for a runtime writer to design.
9. **Partial failure is local.** Feed, return context, Pulse, Questions, Spark,
   selected detail, conversation pages, and attachment processing have
   explicit availability boundaries; one failure does not fabricate or erase
   unrelated truth.
10. **Two first-class Community views only.** Feed and The Break remain the
    only first-class Community views. Deep links, dialogs, sheets, filters, and
    search results do not silently create a third navigation destination.
11. **Communication is separate.** `Message` remains a deferred integration
    seam until its own authority, safety, and visual contracts pass.

## 3. Canonical domain model

The names below are logical. A later runtime initiative may adapt them to
repository conventions without changing the ownership, provenance, or trust
boundaries.

### 3.1 `CommunityPost`

The first-class social publication envelope and root of one conversation.

Required concepts:

- opaque public post key plus a non-public internal key;
- server-derived author/member identity;
- one explicit Community scope established by runtime authority rather than an
  undefined client-provided tenant identifier;
- `origin_kind`: `community_native` or `slate_projection`;
- `intent`: ordinary post, question, or small win, all within the same post
  model rather than separate truth stores;
- question state, valid only for question intent: open, resolved, or closed;
- optional response posture such as just sharing, ideas welcome, or could use
  help;
- explicit audience policy and publication timestamp;
- optional future author-supplied subject/conversation label, not exposed in
  the first slice without additional composer visual authority;
- orthogonal publication, moderation, and deletion state;
- immutable revision number plus `edited_at` rather than treating `edited` as
  a mutually exclusive lifecycle;
- idempotency key scoped to the author and command;
- source revision or row-version token used to prevent lost-update races; and
- zero or more authorized attachments.

For `community_native`:

- the member-authored body is canonical social content; and
- no Journal, Moment, Story, Project, Work, résumé, or other Slate record is
  created automatically.

For `slate_projection`:

- the post stores an exact governed source type, opaque source key, and source
  revision/reference policy;
- any optional member-authored social caption remains Community social truth;
- the projected Slate body, title, evidence, and attachments are rendered from
  the authorized source by reference and are not copied into Community fields;
  and
- source revocation, deletion, or audience loss removes the projection from
  every Community read model without erasing valid Community audit evidence.

The published projection pins an exact authorized source revision. A later
source edit does not silently rewrite an existing social publication. The
member may explicitly refresh/re-publish the projection under the later
runtime contract. If the pinned source revision becomes unavailable, revoked,
or unauthorized, Community shows no copied snapshot fallback.

Recommended first-slice boundary: members create Community-native posts only.
The discriminated Slate-projection architecture remains mandatory so it cannot
be retrofitted as copied content later, but source selection, pinned-revision
preview, projection publication, refresh, and revoked-source composer states
belong to a later owner/visual/runtime package unless Pete explicitly adds
them to the first slice before implementation.

The first-slice conversation label is derived deterministically at read time
from a safely clamped plain-text post excerpt; its composer has no unseen
subject field. An optional member-authored subject is deferred until it has
explicit composer visual authority. Generative AI must not silently name or
rename a conversation.

Recommended V1 state model:

- composer state remains client-private until explicit publish;
- a successful publish transaction creates a `published` row only after all
  required attachments are clean and authorized;
- publication state is `published` or `revoked` for persisted V1 rows;
- moderation state is `clear`, `held`, `removed`, or `restored`;
- deletion state is `active`, `deletion_pending`, or `deleted`;
- the immutable revision increases on every material edit or state change; and
- durable server drafts or a persisted `publishing` limbo state are added only
  if a later contract defines retention, recovery, device sync, and deletion.

### 3.2 `CommunityContribution`

One canonical contribution to a post conversation.

Required concepts:

- opaque contribution key and parent post key;
- server-derived author and Community scope;
- type: reply/comment or author update;
- optional parent contribution key constrained to the same post;
- plain-text or separately approved versioned body format;
- zero or more authorized attachments;
- orthogonal moderation and deletion state plus created/edited/state-change
  timestamps;
- audience ceiling inherited from the post;
- stable per-conversation ordering key;
- idempotency key scoped to the author and command; and
- source revision or row-version token.

Only the post author may create an `author_update`, and the server derives that
capability. Nested replies remain part of the same conversation. A compact
Replies & updates card may summarize nesting, but the selected and full
conversation views preserve the real relationship.

The runtime package must adopt a finite nesting/write policy and a separate
accessible display policy. It may visually indent only the depth that remains
legible on the narrowest locked viewport while preserving the real parent key
for labels, navigation, and assistive technology; it must not silently rewrite
deep parents into root replies.

### 3.3 `CommunityAttachmentReservation` and `CommunityAttachment`

An upload exists before it can safely belong to published content. The
architecture therefore separates an uploader-owned reservation from an
authorized attachment projection.

Required concepts:

- opaque reservation/attachment key and server-derived uploader;
- exactly one eventual post or contribution owner;
- original safe display name and opaque storage name;
- detected, not merely declared, media type;
- allowed kind: image, gallery item, video, PDF, spreadsheet, or another
  explicitly authorized document type;
- byte size, hash, scan state, processing state, derivative state, and optional
  dimensions/duration;
- caption or accessibility description where applicable;
- quarantine, ready, rejected, expired, removed, and revoked states;
- expiration and cleanup for abandoned reservations; and
- no permanent or public storage URL.

Only `ready` reservations owned by the publishing member may be attached in
the final publish transaction. Opening or downloading an attachment performs
a fresh source authorization check.

Recommended V1 ingress avoids the current Flask-wide 2 MB request cap and
JSON-only API guard:

1. a JSON reservation command returns a one-use, write-only, short-lived Blob
   action scoped to one generated storage object, exact maximum bytes/type,
   and no list/read/overwrite permission;
2. the client transfers bytes directly to quarantine and then submits the
   reservation key plus ETag/hash to the JSON finalize endpoint;
3. finalization uses trusted storage metadata to revalidate ownership, object
   key, length, hash, detected type, and reservation expiry before queuing
   processing; and
4. authenticated replay-safe scan/derivative callbacks advance state
   monotonically with compare-and-set/idempotency. Only this trusted path may
   produce `ready`.

Failed/retried transfers cannot overwrite a finalized object; expired and
abandoned reservations are cleaned automatically. The later runtime must own
the required Blob CORS/managed-identity configuration without exposing
account credentials.

V1 preview and download use a reauthorizing application proxy or equivalently
revocable opaque handle that does not disclose an independently usable Blob
SAS. This permits immediate audience/source/block/moderation revocation. The
proxy returns separate preview and safe download dispositions, applies
`nosniff`, private/no-store and referrer protections, and rechecks access on
every request/range. If a later design uses a non-revocable token, its maximum
residual-access window requires a new explicit owner/security decision and
honest deletion wording.

Office documents and PDFs download rather than render active content. Video
is included only if the runtime package fully owns safe derivatives and
authorized range delivery through this boundary; otherwise its visual state
must truthfully show unavailable/deferred support.

### 3.4 `CommunityAudience`

The post's publication policy is explicit, visible to the author, and checked
on every projection. The mockup label `Community` is not proof of public-
internet visibility or of a particular membership tier.

The runtime package must adopt an exact audience vocabulary and Community
membership source. It must choose one coherent V1 model rather than adding an
undefined `tenant_id`:

- the single authenticated PeerSlate Community with one explicit published
  audience; or
- a real Community-space/membership domain with server-derived membership.

Relationship-scoped or selected-member audiences may be added only when their
membership, revocation, reply visibility, count privacy, and participant-
protection rules are specified and tested.

The lowest-risk V1 recommendation is private local composer state plus one
publishable authenticated `Community members` audience, with connection-
scoped, selected-person, and public-internet audiences deferred. This is a
recommendation, not activated product authority; the runtime package still
needs Pete's exact audience decision and membership source.

Required rules:

- missing or invalid audience is rejected;
- audience never defaults to public;
- a contribution cannot exceed its parent post's audience;
- changing audience reauthorizes every projection and attachment; and
- audience broadening after contributions is prohibited in V1 unless a later
  owner-approved participant-consent/version policy explicitly permits it.

### 3.5 `CommunityResponse`

`Respond` is a purposeful, reversible lightweight response, not a generic
reaction counter.

Required concepts:

- post key and server-derived responding member;
- exactly one current intention per member and post;
- intention vocabulary: `celebrate`, `support`, `i_relate`, `ask`, or
  `offer_help`;
- created/updated/removed timestamps; and
- audience, block, lifecycle, and moderation checks identical to the source
  post.

The member can replace or remove their own intention. Public score contests,
leaderboards, responder rankings, and engagement-based Feed order are
forbidden. Aggregate disclosure is allowed only under an explicit
privacy-threshold rule. `Offer help` may contribute to a truthful Pulse or
catch-up projection, but it creates no obligation, assignment, or message.

The five-intention vocabulary is approved in this owner-directed package and
page-purpose inventory; the lean shared site rules neither enumerate nor
conflict with it. Its exact tray, selected/replaced/removed state, loading,
failure, keyboard, and mobile presentation are not in the six-screen lock and
must be added to the visual-completion set before this capability ships. If
that state set does not retain Respond, the first runtime slice hides/defers it
rather than inventing the interaction.

Response posture is a member-visible tone signal, not authorization. The
lowest-risk first-slice recommendation is display-only: it does not silently
disable Respond, Comment, or Reply, and edits do not revoke existing
participation. If Pete wants posture to change capabilities or notification
behavior, that semantics and its visual states become a separate pre-runtime
decision; the client may never infer capability from the label.

### 3.6 Member relationships, private state, and safety state

- `CommunityPostSave` and `CommunityContributionSave`: private member-to-source
  references, modeled with strong target constraints and deterministic
  `PUT`/`DELETE`, never a toggle or public count.
- `CommunityFeedSeen`: per-member, per-window visible-post acknowledgement.
- `CommunityConversationSeen`: per-member last authorized contribution order
  for deterministic `updated` and resume labels.
- relationship/follow state: only the established server-authoritative source
  selected by the runtime package.
- existing block state: the strong bilateral visibility boundary where
  authorized by current platform rules.
- Community mute state: a weaker member-specific projection preference,
  separately recorded from block.
- report/moderation state: content-safe records that never expose reporter
  identity or moderation internals to participants.

A private save ceases to expose content when source authorization ends. It may
retain a non-revealing unavailable reference only if the retention contract
expressly permits it.

### 3.7 Member summary, activity reference, and catch-up snapshot

`CommunityMemberSummary` is the minimum authorized identity projection needed
by a card or conversation: display name, avatar derivative, role/badge truth,
and an optional authorized profile reference. It is not a join that retrieves
or serializes the member's full private profile.

`CommunityActivityReference` is a source-referential, body-free event used to
derive return context. It records event type, canonical post/contribution key,
stable server sequence, event time, and source revision. It is not editable
content and is discarded or suppressed whenever its source is no longer
authorized.

`CatchUpSnapshot` is an immutable viewer-bound read boundary containing:

- `as_of` watermark and expiry;
- distinct authorized activity references and their type/count;
- one deterministic canonical destination per reference;
- placement priority and module assignment; and
- current seen/attention state.

Fetching a snapshot never marks an event seen. An event becomes seen only
after the tested exposure threshold or an explicit open/acknowledgement, and
updates are monotonic and idempotent. A catch-up reference may point to a post
that also remains in the canonical Feed; this is intentional navigation, not
a copied second truth. The same event/excerpt must not be repeated within or
across modules merely to manufacture density.

### 3.8 `CommunitySparkDefinition`

Spark is bounded editorial configuration, not a member post and not AI output
presented as member activity.

Required concepts:

- opaque definition and version key;
- prompt copy and accessibility label;
- active window and deterministic rotation policy;
- editorial/source attribution when needed;
- enabled/disabled state; and
- locale or Community eligibility if later required.

`Use this Spark` opens the composer with a visible removable reference. It
creates no draft, post, save, notification, or canonical record until the
member explicitly publishes. `Another Spark` changes only the displayed
definition.

### 3.9 Derived projections, never independent truth

The following are rebuildable read models over authorized canonical sources:

- Feed item;
- Replies & updates card and shelf;
- selected contribution;
- full conversation;
- search result;
- Since you were here item;
- Continue the conversation item;
- Community Pulse row;
- Active Question row;
- caught-up state; and
- attachment preview/ribbon.

No derived record stores editable post/contribution bodies. A persisted index
or activity table, if query evidence later requires one, must retain exact
source references, be body-free where possible, be safely rebuildable, and
reauthorize against canonical state before display.

## 4. Locked-screen contract map

The architecture must be able to render each exact locked state from canonical
truth without special fixture-only branches.

| Locked file | Required contract |
| --- | --- |
| `00-desktop-community-feed.jpg` | Signed-in Community shell; quick composer; full-size Feed image/file/gallery projections; post actions; one post-local Replies & updates row; left return rail; right Pulse/Questions rail; finite caught-up ending. |
| `01-desktop-selected-motion-contribution.jpg` | One authorized parent-post context plus one selected contribution; full attachment projection; contribution actions; `View full conversation`; modal focus/inertness; exact Feed, shelf, and focus restoration. |
| `02-desktop-view-all-conversation.jpg` | One derived conversation label; root post; nested/paginated contributions; author-update truth; full attachments; permitted menus; sticky reply composer; same canonical conversation. |
| `03-mobile-community-feed.jpg` | True single-column Feed; Catch up entry; mobile composer entry; full Feed media; one compact shelf with three complete cards plus a visible partial fourth; no persistent rails. |
| `04-mobile-catch-up-spark-sheet.jpg` | Owner-specific catch-up projection; Continue item; one current Spark; independent empty/error boundaries; no Break content; close/focus restoration. |
| `05-mobile-selected-motion-contribution.jpg` | Full-screen selected contribution; collapsible parent context and `View original`; full attachment; contribution actions; `View all`; sticky reply composer; browser Back restoration. |

The first review found one important correction to the prior architecture:
Feed post attachments are **full visual/file/gallery projections** as shown in
the desktop and mobile Feed locks. Only attachments inside compact Replies &
updates cards use the icon/thumbnail plus truncated name and `+N` treatment.

## 5. Read models and response shapes

### 5.1 Signed-in bootstrap

Recommended bootstrap:

`GET /api/v1/community/bootstrap?mode={mode}&filter={filter}&modules={set}`

It returns one schema-versioned, private/no-store response containing:

- viewer display projection and server-derived capabilities;
- active Feed mode/filter after validation;
- a signed stable Feed-window token;
- the first authorized Feed page;
- caught-up metadata and new-content status;
- only the route/device-state modules requested and permitted by the completed
  visual/capability contract, each with its own `ready`, `empty`,
  `unavailable`, or `retryable_error` status; and
- feature/capability truth needed to hide unavailable actions.

Separate module endpoints remain useful for pagination, refresh, and local
retry. The bootstrap establishes one deduplicated session boundary so parallel
module calls cannot disagree about the caught-up window.

The module request is payload-minimization, not authorization. Desktop may
request the locked return, Spark, Pulse, and Questions modules. Mobile must not
receive unused Pulse/Questions payloads if their completed visual disposition
is desktop-only. The server still authorizes every requested module and may
omit it regardless of the client request.

No protected Feed, rail, count, avatar, filename, or excerpt is embedded in
anonymous HTML. A signed-out page may render only the separately locked
truthful sign-in/unavailable treatment.

### 5.2 Feed item

Each authorized Feed item contains:

- canonical post key, origin kind, intent/posture, author projection,
  timestamps, lifecycle label, and audience label appropriate for the viewer;
- Community-native body or an authorized Slate-source projection by exact
  reference, never both as copied source truth;
- the complete permitted Feed attachment projection: file tile, image,
  gallery, or other supported media treatment shown by the lock;
- viewer-specific `permitted_actions` and current private save/response state;
- Replies & updates metadata only when the shelf is eligible;
- source/profile/deep-link actions only when the separate destination is
  authorized; and
- no hidden counts or fields the viewer cannot access.

### 5.3 Replies & updates shelf

For an eligible post, the shelf projection contains:

- total **authorized** contribution count or a privacy-safe qualitative label;
- an ordered slice of compact contribution summaries;
- stable contribution keys for selection and focus restoration;
- author name/avatar projection, timestamp, optional `Author update` label,
  clamped text, compact attachment cue, and only approved response metadata;
- opaque cursor for further horizontal traversal; and
- the viewer's last-seen contribution marker.

The server may page as the member traverses, but the client preserves one
continuous row, ordering, shelf offset, selected card, and de-duplication. It
must not wrap, reset, duplicate, or imply workflow stage progression.

### 5.4 Compact and full attachment projections

Compact Replies & updates card:

- kind icon or tiny authorized thumbnail;
- first safe display name clamped by the client;
- additional attachment count as `+N`;
- fixed-height reserved geometry; and
- no permanent URL or oversized metadata tile.

Full Feed, selected-contribution, or conversation projection, according to the
matching locked state:

- complete safe display name;
- type, size, dimensions/duration where useful;
- processing/unavailable status;
- authorized preview derivative or gallery list; and
- separate viewer-specific `preview/open` and `download` capabilities when
  permitted, each with exact label, disposition, expiry/handle semantics, and
  unavailable state.

The selected-detail locks distinguish `Open file` from a download icon; those
controls must not share an ambiguous mutation. Whether a Feed image/gallery
opens a focused viewer or remains noninteractive is a missing visual decision.
Runtime must not invent a lightbox, gallery route, or media viewer.

### 5.5 Selected contribution

The selected-contribution read model contains:

- authorized root-post context sufficient to understand the contribution;
- selected contribution with `Reply to …`, authorized parent-chain, nesting,
  author-update, and current revision truth;
- full attachment projection;
- permitted `Reply`, `Save`, menu, `View original`, and `View full
  conversation` actions;
- truthful Message capability state without a message payload; and
- a restoration token held in `history.state`, not private content in the URL.

Desktop presents this model in the locked modal. Mobile presents it as a
full-screen route/view. Direct entry repeats authorization and returns a
neutral unavailable state if the source is inaccessible.

### 5.6 Full conversation

The full-conversation read model contains:

- derived conversation label;
- authorized root post and its full attachments;
- a stable, nested contribution page;
- parent keys, author/update badges, current revisions, and a selected/unread
  anchor when entry came from return context or selected detail;
- full permitted actions and synchronized private save state per post and
  contribution;
- edit/deletion/held tombstones only when structure requires them;
- pagination cursors that cannot cross the conversation boundary;
- current private save/seen state; and
- sticky composer capability and reply target.

It never creates a second thread or loses the invoking Feed context.
Transition from selected detail to full conversation replaces the detail
presentation rather than stacking dialogs, while preserving one return token.

### 5.7 Return context, Pulse, Questions, and Spark

These are independently bounded queries over the same authorized sources.
Recommended initial content budgets:

- Since you were here: at most three unseen direct items;
- Continue the conversation: at most one resumable conversation;
- Spark: exactly zero or one current prompt;
- Community Pulse: at most three truthful rows; and
- Active Questions: at most three authorized question posts.

Every row carries its exact source key and permitted action. The same source is
not repeated across the visible Feed and both rails merely to create density.
Counts are real, reproducible, privacy-safe, and reauthorized at read time.

Active Questions derives only from authorized posts whose intent is question
and whose question state is open. Resolved, closed, held, revoked, blocked, or
otherwise inaccessible questions do not appear or contribute to counts.

Every Pulse metric names a canonical source event, a fixed reproducible time
window, expiry, viewer authorization rule, and minimum privacy cohort. For
example, `Members offering help` may derive from active `offer_help` responses,
and `Wins shared recently` may derive from small-win posts. A metric is
suppressed when its canonical source or privacy threshold is unavailable; the
server never infers it from generic engagement.

The later runtime contract must define the source-event priority and
deduplication table explicitly. A recommendation is: direct reply/update for
the viewer first, then a resumable conversation, then authorized community
summary; never engagement rank. A return reference may link to a canonical
Feed item that is also visible, but the event body is not copied into a second
truth or duplicated in multiple summary modules.

### 5.8 Search and shell controls

The locked Feed visually includes `Search Community`, `New post`, and a member
menu. `New post` is a second entry to the same composer, and the member menu
must reuse server-derived shell identity.

`Search Community` is not present in the owner-approved page-purpose inventory
and therefore is **not yet authorized as a meaningful V1 control**. Before
runtime, Pete must lock one of two truthful outcomes:

1. add Community-local authorized search to the inventory and missing-state
   visual set, including loading, no-result, failure, permission, and mobile
   access; or
2. remove or truthfully defer the control through a ChatGPT-created state
   adaptation that Pete locks.

If adopted, search is source-authorized before indexing/result disclosure,
bounded and paginated, resistant to existence leakage, and remains an overlay,
sheet, or subordinate Feed state rather than a third first-class view.

The mockup shell labels do not authorize renaming current global navigation or
editing shared `base.html`. The runtime initiative must preserve the current
`Community` destination and explicitly reserve any shared-shell file it truly
needs.

### 5.9 Server-returned capabilities

Every object returns only the actions the current viewer may actually perform.
The client never infers ownership or moderation authority from names, keys, or
DOM state. Each action projection carries an explicit strongly typed target,
opaque target key, current viewer state, source revision, and permitted
operation. A generic unconstrained client-supplied `object_type/object_id`
pair is not authorization.

| Visible action | Canonical target and effect | Presentation / return contract |
| --- | --- | --- |
| `Search Community` / mobile search | Conditional authorized query; no write. | Feed-local overlay/sheet or subordinate result state only if separately approved and locked; Back/close restores launcher focus. |
| `New post`, mobile `+`, composer prompt | The same private post composer; no record on open. | Opens the locked desktop/mobile composer and restores the invoking Feed state on cancel. |
| `Ask`, `Small win`, Spark use | Sets a removable composer intent/reference; no record on open. | Opens the same composer; the member may change it before explicit publish. |
| `Respond` | Current post; deterministic create/replace/remove of one of five intentions. | Opens the compact tray; keeps post focus; no public popularity score. |
| `Comment` | Current post. | Opens the authoritative full conversation with the post reply composer targeted. |
| `Reply` | Exact post or contribution target. | Opens/focuses the contribution composer and preserves parent relationship. |
| `Save` / `Saved` / bookmark | Explicit post or contribution target; private deterministic save/remove. | Every duplicate control for the same target updates atomically; different targets use distinct accessible names. |
| Post/contribution ellipsis | Server-returned author or viewer capabilities only. | Edit/remove/report/mute/block/copy-link items appear only when permitted; closing restores the invoking control. |
| Profile identity | Minimum member summary and separately authorized profile reference. | Opens only that external authorized destination; this package defines no profile layout or route. |
| `View original` | Root Community post/context for the selected contribution. | Always opens the authorized parent Community post; neutral unavailable when access has ended. |
| Separately named Slate-source action | Exact pinned Slate source, only for a Slate-projected post. | Requires its own approved label and visual contract; never overloads selected-detail `View original`. |
| Attachment `Open file` / preview | Exact attachment preview target. | Uses the separately authorized preview capability and locked focused/unavailable treatment. |
| Attachment download icon/action | Exact attachment download target. | Uses a distinct authorized attachment disposition and accessible filename/type label. |
| Motion-card selection | Exact contribution. | Desktop modal or phone full-screen detail; exact Feed/shelf/focus restoration. |
| `View all Replies & Updates` / mobile `View all` | Current post's one conversation. | Opens the same complete conversation; the semantic accessible name remains `View all Replies & Updates`. |
| `Pick this back up` | Exact resumable conversation reference. | Opens the canonical conversation at the unread/resume anchor; return preserves Catch up/Feed state. |
| Personal `See all activity` | Current viewer's bounded catch-up snapshot. | Existing Catch up sheet/subordinate state; never a third Community view. |
| Pulse `See all activity` | Bounded authorized Community activity query. | Exact later-locked overlay/sheet or removal; never `/the-slate/pulse` by implication. |
| `See all questions` | Authorized open-question filter/query. | Exact later-locked Feed-local state; never another canonical Feed. |
| `Another Spark` | Current Spark projection only. | Replaces the prompt in place; writes nothing and preserves focus. |
| `Revisit saved posts` | Viewer-private authorized saved-post query. | Requires a later-locked subordinate state because `/the-slate/saved` remains redirect-only. |
| `See what changed` | Viewer-bound catch-up snapshot/new-content action. | Opens Catch up or explicitly refreshes the Feed window as later locked; never marks unseen content merely on fetch. |
| `Ask the community` | Same post composer with question intent. | Explicit publish still required. |
| `Message` | No V1 Community mutation. | Hidden or truthfully unavailable until the messaging package passes. |

## 6. Candidate page, service, and API boundaries

The following are recommended runtime boundaries, not approved route or API
authority.

### 6.1 Page and deep-link routes

| Candidate route | Purpose |
| --- | --- |
| `GET /the-slate` | Existing first-class Community Feed landing. |
| `GET /the-slate/break` | Existing separate Break view; unchanged. |
| `GET /the-slate/posts/{post_key}` | Non-navigation deep link to the full authorized conversation. |
| `GET /the-slate/posts/{post_key}/contributions/{contribution_key}` | Non-navigation deep link to one selected authorized contribution. |

Opaque keys only appear in URLs. No names, audience values, attachment names,
or private content appear there. Desktop may enhance a deep link into a modal;
phone may use a full page. Direct entry, Back, reload, and unavailable-source
fallback all reauthorize.

`See all activity` and `See all questions`, if retained by the completed
visual lock, must use a bounded overlay/sheet or another approved subordinate
state. `/the-slate/pulse` or an equivalent permanent third view is forbidden
without new route authority.

### 6.2 API candidates

| Method and candidate route | Purpose |
| --- | --- |
| `GET /api/v1/community/bootstrap` | Stable Feed window plus independently statused initial modules. |
| `GET /api/v1/community/feed` | Page within the signed active window. |
| `POST /api/v1/community/posts` | Explicit transactional publish. |
| `GET /api/v1/community/posts/{post_key}` | Authorized root/full-conversation projection. |
| `PATCH /api/v1/community/posts/{post_key}` | Author edit with revision precondition. |
| `DELETE /api/v1/community/posts/{post_key}` | Author removal with revision precondition. |
| `GET /api/v1/community/posts/{post_key}/contributions` | Page one authoritative conversation. |
| `POST /api/v1/community/posts/{post_key}/contributions` | Explicit reply or server-valid author update. |
| `GET /api/v1/community/contributions/{contribution_key}` | Selected authorized contribution plus parent context. |
| `PATCH /api/v1/community/contributions/{contribution_key}` | Author edit with revision precondition. |
| `DELETE /api/v1/community/contributions/{contribution_key}` | Author removal with revision precondition. |
| `PUT /api/v1/community/posts/{post_key}/response` | Create or replace the viewer's purposeful response. |
| `DELETE /api/v1/community/posts/{post_key}/response` | Remove the viewer's response. |
| `PUT /api/v1/community/posts/{post_key}/save` | Save one post privately. |
| `DELETE /api/v1/community/posts/{post_key}/save` | Remove one post save. |
| `PUT /api/v1/community/contributions/{contribution_key}/save` | Save one contribution privately. |
| `DELETE /api/v1/community/contributions/{contribution_key}/save` | Remove one contribution save. |
| `POST /api/v1/community/feed-seen` | Idempotently acknowledge Feed-post keys proven by a signed page receipt. |
| `POST /api/v1/community/activity-seen` | Acknowledge typed catch-up/activity references returned in the viewer's snapshot. |
| `POST /api/v1/community/posts/{post_key}/conversation-seen` | Advance the viewer's authorized contribution sequence monotonically. |
| `GET /api/v1/community/catch-up` | Retry/refresh owner-specific return context. |
| `GET /api/v1/community/pulse` | Retry/refresh bounded authorized Pulse. |
| `GET /api/v1/community/questions` | Retry/refresh bounded authorized Questions. |
| `GET /api/v1/community/sparks/current` | Return the current truthful Spark. |
| `POST /api/v1/community/uploads` | Reserve an uploader-owned quarantined upload. |
| `POST /api/v1/community/uploads/{upload_key}/finalize` | Revalidate the completed write and begin trusted scan/derivative processing. |
| `GET /api/v1/community/uploads/{upload_key}/status` | Poll scan/processing state without exposing storage. |
| `DELETE /api/v1/community/uploads/{upload_key}` | Remove an unused owned reservation. |
| `GET /api/v1/community/attachments/{attachment_key}/preview` | Reauthorize and serve/resolve the permitted preview through a revocable application handle. |
| `GET /api/v1/community/attachments/{attachment_key}/download` | Reauthorize and stream the permitted attachment disposition separately. |
| `POST /api/v1/community/reports` | Submit a content-safe report. |
| `GET /api/v1/community/search` | Conditional on explicit search approval and visual lock. |

Mute/block mutations should reuse or deliberately extend the platform trust
domain only if the runtime package owns those exact flows. Do not create a
parallel weaker block store for convenience.

### 6.3 Mutation protocol

Every mutation requires:

- trusted server-derived member identity and active-account status;
- same-origin/CSRF protection using the repository's approved pattern;
- strict content type, vocabulary, length, key, and attachment validation;
- an `Idempotency-Key` for publish/reply/report/upload commands susceptible to
  double submission;
- `If-Match` or an equivalent opaque revision precondition for edits/removals;
- authorization again inside the database transaction;
- content-free immutable audit evidence in the same transaction;
- a durable content-minimal outbox event in the same transaction for any
  later notification/index/projection work;
- neutral missing/unauthorized/blocked/held behavior; and
- a private/no-store response.

Toggle endpoints are prohibited because retrying them can invert state. Use
deterministic `PUT` and `DELETE` commands. A safe retry returns the original
result and cannot create another post, contribution, response, count, return
event, upload binding, or notification. A stale authorized mutation returns
`409` without disclosing the protected current body.

Input parsers use explicit allowed-field lists to prevent mass assignment.
The runtime package must standardize at least: `401` for a whole-surface absent
identity, neutral `404` for object-level absence/inaccessibility, `409` for an
authorized stale revision/idempotency conflict, `413` for size limit, `415`
for unsupported media type, `422` for safe validation failure, `429` for rate
limit, and `503` for retryable identity/storage dependency failure. Protected
responses use private/no-store, `nosniff`, current CSP/frame protections, no
private CORS, and no protected value in an error, redirect, or cursor.

### 6.4 Recommended code ownership boundaries

Backend:

- `community_routes.py`: thin page/deep-link rendering and auth boundary;
- `community_api.py`: `/api/v1/community` transport, parsing, status mapping,
  and same-origin checks only;
- `services/community_contracts.py`: vocabularies, limits, opaque key/revision
  validation, and serializers;
- `services/community_cursor.py`: signed user-bound window/page tokens using a
  dedicated configured signing key;
- `services/community_feed_service.py`: bootstrap, Feed, selected/full
  conversation, rails, and conditional search reads;
- `services/community_command_service.py`: publish/edit/remove, contribution,
  response, save, seen, and report commands;
- `services/community_media_service.py`: upload state orchestration; and
- `services/community_media_storage.py`: Community-only managed-identity Blob
  adapter and short-lived authorized access.

Frontend:

- keep existing `app.py` Community endpoint names as thin compatibility
  wrappers where current `url_for` usage requires them;
- make `templates/the_slate.html` a thin two-view shell and isolate the
  unchanged Break markup in its own partial;
- use Community-specific partials for Feed, composer, post, shelf, return rail,
  right rail, selected detail, conversation, Catch up sheet, and state panel;
- use small modules for API transport, finite Feed state, composer, Feed,
  conversation/restoration, and Catch up behavior; and
- scope new styles to a new root such as `.community-feed-v1`; do not layer
  production rules over the historical `#feed-app` prototype selectors.

Database:

- create a new Community-specific migration plus guarded rollback and
  multi-member authorization verification;
- use strong foreign keys/check constraints rather than unconstrained
  `object_type`/`object_id` polymorphism;
- add every new stored procedure to the repository allowlist intentionally;
  and
- keep post, contribution, attachment, response, save, seen, mute/report, and
  Spark tables source-referential and free of presentation-only fixture fields.

The runtime initiative must name exact filenames and reservations. These
boundaries are not permission for this direction branch to create them.

## 7. Feed ordering, modes, cursors, and caught-up

### 7.1 Mode decision still required

FD-15 and the approved inventory retain `Following`, transparent `Recent`, and
`Questions` as a filter. The six locked screens show no mode/filter control.
Implementation must not guess its placement or silently collapse the product
decision.

Before runtime, owner/visual authority must choose and lock one outcome:

1. retain `Following` and `Recent`, identify the default, and place an exact
   accessible mode/filter control in the completed state set; or
2. amend the inventory to one explainable V1 Feed and defer the absent modes.

`Questions` remains a filter/shortcut over authorized posts, not another
canonical Feed or first-class view.

### 7.2 Explainable order

Within the adopted mode, order uses only documented factors:

- relationship/mode eligibility;
- publication recency;
- unseen direct relevance such as a reply to the viewer or an update in a
  joined conversation; and
- a stable opaque-key tie-breaker.

Engagement totals, outrage, dwell time, paid placement, opaque virality, and
response counts do not drive V1 order.

Every factor, including unseen direct relevance, is evaluated and frozen when
the Feed window is created. Later replies, seen changes, relationship changes,
or new posts do not reorder or add candidates inside that window. New lawful
activity produces `new_content_available`; revocation can only remove an item.

### 7.3 Stable signed window

Recommended V1 uses an expiring server-side immutable `CommunityFeedWindow`
that materializes a finite ordered candidate-key set up to an explicit maximum
cardinality. The signed window token references:

- schema/token version;
- viewer key binding;
- adopted mode and filter;
- high- and low-water boundaries plus the fixed candidate-set/window key;
- stable ordering-version identifier;
- frozen as-of ranking inputs; and
- expiry and nonce/key version.

Page position is a separate opaque cursor. Every page response also returns a
signed, viewer/window/page-bound receipt that commits to the exact typed keys
actually returned. Neither token contains readable content or authorization
claims that bypass current database checks.

Newly arriving posts or post-window contribution activity do not move or
reorder the active candidate set. The server may return
`new_content_available`; the member explicitly refreshes into a new window.
Revocation removes a candidate immediately and does not pull an unseen older
replacement into the window. Window expiry requires a new authorized snapshot.

### 7.4 Seen and caught-up

`POST /feed-seen` accepts only post keys proven by a signed page receipt. The
server validates viewer, window, page, and key membership; reauthorizes every
key; records the tested visible threshold idempotently; and cannot advance
hidden or merely candidate items.

`POST /activity-seen` accepts a discriminated catch-up/activity-reference key
proven by the viewer's `CatchUpSnapshot`. A fetch never marks it. An explicit
open/acknowledgement or tested accessible exposure advances it monotonically.
`POST /posts/{post_key}/conversation-seen` can advance only to a contribution
sequence actually returned to that viewer in the authorized conversation.

The member is caught up when every still-authorized candidate in the finite
active window meets the Feed threshold. Revoked candidates cease to count but
do not admit replacements. Earlier content requires an explicit action and a
new bounded window/page request. The caught-up panel never triggers automatic
refill.

## 8. Replies & updates interaction contract

### 8.1 Eligibility

Do not show an empty shelf. A post is eligible when it has authorized reply or
author-update activity worth previewing under one deterministic runtime rule.
Responses alone are insufficient.

### 8.2 One-row invariant

- one shelf header;
- one non-wrapping horizontal list;
- equal-height compact cards;
- approximately three to four complete cards in the accepted desktop Feed;
- three complete cards plus a visible partial fourth in the accepted phone
  composition;
- up to one previous and one next control when content exists in that
  direction, with the unavailable boundary control hidden;
- no second row, grid, masonry, connectors, stage line, progress meter,
  automatic carousel, or visual scrollbar that changes the locked design; and
- persistent View all action outside the scroller: full visible label
  `View all Replies & Updates` on desktop and the locked compact `View all` on
  mobile, both with semantic name `View all Replies & Updates`.

Responsive card width is computed to preserve the locked density. Attachment
content cannot change compact-card height.

The small speech-bubble number on a compact card, if retained, is an
authorized child/nested-reply count for that contribution. It is not a generic
reaction or engagement score. If that meaning cannot be proved and locked,
the count is omitted rather than reinterpreted.

### 8.3 Selection, history, and restoration

Selecting a card records in `history.state`:

- Feed window and page cursor;
- vertical scroll position;
- post key;
- shelf offset and selected contribution key; and
- invoking focus target.

Desktop opens a centered named modal with a focus trap, Escape/close, and an
inert background. Phone opens the full-screen selected-detail route/view and
supports browser Back. Close/back restores exact Feed scroll, shelf offset,
selection, and keyboard focus. Reload/direct entry reauthorizes and degrades
to a truthful unavailable state without exposing private state in the URL.

### 8.4 Full conversation

`View all Replies & Updates` opens the complete traditional vertical
conversation from the same post/contribution source. It supports nesting,
full media, stable pagination, edit/removed/held truth, loading/retry, and a
sticky reply composer. Closing preserves the invoking Feed context.

## 9. Composer and publication contract

### 9.1 Post composer

`Ask`, `Small win`, Spark, and ordinary wording are composer entry intents in
the same post model. `Ask` sets question intent so Active Questions can be
derived without text inference. The member can change or clear the starter
before publishing.

Before publication the member can:

- see and choose the permitted audience;
- inspect the exact destination and response posture;
- remove/change a Spark reference or starter;
- prepare supported media/documents;
- understand scan/processing state;
- retry or remove a failed attachment;
- retain text through recoverable errors;
- cancel without publishing; and
- perform one explicit final publish action.

### 9.2 Contribution composer

The selected-contribution and full-conversation locks show a distinct reply
composer. It requires:

- one explicit post target and optional parent contribution target;
- the inherited audience ceiling and fresh server authorization;
- server-derived author identity;
- validated body plus uploader-owned ready attachments;
- authorization-filtered mention suggestions if mentions are adopted;
- emoji as ordinary text insertion rather than a separate truth object;
- disabled empty submission;
- one explicit idempotent `Reply` action;
- preserved body/attachments after a recoverable failure; and
- no silent autosave, publication, audience change, notification, or message.

Mention behavior is not implicitly authorized by the visible icon. The
runtime package must either adopt an exact private suggestion/notification
contract and lock its states, or hide/defer the control truthfully.

### 9.3 Recommended first-slice publication transaction

1. keep text and UI state local/private;
2. reserve and process uploads under the current member;
3. reject publish unless the audience and every referenced upload are valid,
   clean, ready, unexpired, and owned by that member;
4. insert the post, attach reservations, append content-free audit evidence,
   and commit atomically using the idempotency key; and
5. return the canonical authorized projection or a neutral recoverable error.

Exact body limits, edit window, deletion policy, audience changes, mention
behavior, durable drafts, and notification side effects are runtime-package
contracts. Nothing authorizes silent autosave, silent notification, or
public-by-default publication.

## 10. Lifecycle, moderation, and projection consistency

Every source state has one consistent effect across Feed, rails, search,
Replies & updates, selected detail, conversation, saves, attachments, and
counts.

| Source state | Required projection behavior |
| --- | --- |
| Published and authorized | Render only permitted fields/actions. |
| Edited | Render current authorized revision plus the locked truthful edited label; stale mutations fail after authorization. |
| Removed by author | Omit unless a restrained tombstone is necessary to preserve authorized conversation structure. |
| Held / removed by moderation | Neutral unavailable or locked moderation state; no reason/report identity leakage. |
| Audience revoked | Disappear from every projection and attachment open; private save cannot preserve content. |
| Blocked | Apply the platform's bilateral boundary before result, count, search, notification, or media disclosure. |
| Muted | Exclude or de-prioritize only under the exact weaker mute contract; never bypass authorization. |
| Attachment pending/rejected/revoked | Show only the matching locked processing/unavailable treatment; never expose raw storage. |
| Deleted parent with surviving authorized replies | Use only the later locked structural tombstone policy; never reconstruct deleted text. |
| Pinned Slate source edited | Existing projection stays on its exact authorized revision until explicit refresh; never mutates silently. |
| Pinned Slate source revoked/deleted/unavailable | Remove every source field/media projection immediately; no copied snapshot fallback. |
| Relationship removed | Recompute every relationship-scoped read, count, search/index, notification, cache, save, cursor, and media access. |
| Account suspended/deleted | Deny new access/mutations and apply the separately adopted identity, retention, authorship, moderation, and legal-hold policy. |
| Moderation restored | Reauthorize and re-index only the current allowed revision; do not replay duplicate counts or notifications. |

Report, moderation, and deletion audit records retain content-free source keys,
actor/action metadata, and timestamps as policy permits; ordinary operational
logs do not contain bodies, filenames, report details, or access URLs.

The runtime package must convert this table into an executable propagation
matrix covering Feed, selected/full conversation, catch-up, Pulse, Questions,
search/index, cache, cursor, count, save, notification/outbox, attachment
derivative, and already-issued media-token behavior. Deletion wording must be
honest about moderation/legal-hold exceptions and actual storage cleanup.

## 11. Trust, privacy, caching, and abuse resistance

### 11.1 Viewer and surface matrix

Until a separately approved audience matrix says otherwise, real Community V1
data is deny-by-default and authenticated-active-member-only.

| Viewer/surface condition | Required behavior |
| --- | --- |
| Signed out on `/the-slate` | Public payload-free shell with the later locked truthful sign-in treatment; no member data in HTML. |
| Trusted identity unavailable | Private unavailable/retry state; no fallback fixture activity represented as real. |
| Signed in but inactive/suspended/deleted | No Community retrieval or mutation; truthful account/support state under platform authority. |
| Active identity but not an authorized Community member | Neutral unavailable/permission state; no counts, autocomplete, avatars, filenames, or source existence. |
| Active authorized member | Only content passing the effective-visibility predicate and viewer-specific capabilities. |
| Author | Same read authorization plus server-returned author actions; ownership never inferred client-side. |
| Moderator/support role | Separate least-privilege surface and purpose-bound access; no moderation authority in ordinary Feed payloads. |

### 11.2 One effective-visibility predicate

Every SQL read, search/index result, count, rail, notification, cache entry,
deep link, and media open applies the same effective-visibility intersection:

1. trusted active viewer and authorized Community membership;
2. post publication audience;
3. current relationship/grant where the selected audience requires it;
4. block and applicable mute rules;
5. post/contribution publication, moderation, and deletion state;
6. for a Slate projection, current source permission and the pinned source
   revision's availability; and
7. attachment lifecycle and open permission for media fields.

Fail any term and the protected object is indistinguishable from absent,
except for an explicitly authorized private author/moderator status surface.

### 11.3 Request and data-handling requirements

- Use the repository's trusted Easy Auth identity path and active-account
  checks. Ignore client author/member/community identifiers.
- Resolve authorization inside database reads and writes, not only in Flask
  or JavaScript.
- Return the same neutral `404` for object-level missing, unauthorized,
  blocked, removed, or held cases unless a safer authorized tombstone applies.
- A whole-surface missing identity may use a truthful `401`/sign-in flow;
  identity or storage unavailability may use a private `503` with retry.
- Mark protected HTML and JSON `private, no-store` and ensure shared caches,
  error telemetry, and analytics never key or carry protected excerpts/counts.
- Sanitize any approved formatted text and links; recommended V1 is plain text
  rendered with safe text APIs, not stored/rendered arbitrary HTML.
- Apply request, publish, contribution, response, search, report, and upload
  rate limits appropriate to abuse risk.
- Scan uploads, verify signatures/container structure, bound decoded image
  dimensions and archive expansion, strip sensitive metadata, and generate
  safe derivatives.
- Reauthorize before every thumbnail, preview, open, download, count, or
  search result.
- Do not reveal hidden participation through aggregates. Define privacy
  thresholds and suppress or generalize low-cardinality Pulse rows.
- Preserve provenance among member content, canonical Slate sources,
  moderation actions, editorial Spark definitions, and any later AI proposal.

### 11.4 Block, mute, report, and moderation

- Block is enforced server-side before interaction, member summary, search,
  rails, catch-up, counts, notifications, deep links, and media. The runtime
  package must adopt and test the exact reciprocal visibility behavior.
- Mute is a private viewer preference; it never grants or revokes source
  authorization and never tells the muted member.
- Report is private, idempotent, rate-limited, and returns a receipt without
  moderation internals. An explicit local hide may accompany it; reporting
  alone does not fabricate removal.
- Moderators operate under a distinct least-privilege role. Protected-content
  access and decisions record actor, purpose, target, prior/new state, and
  policy version without copying content into ordinary logs.
- Held content is absent from other-member projections. The author receives
  only the separately locked truthful private status and support/appeal path.
- Generative AI does not make final moderation decisions.

Before a member pilot or release, the runtime/release package must own spam,
harassment, impersonation, copyright/takedown, account suspension, evidence or
legal hold, appeal/support, incident response, and operational escalation.

## 12. Semantic structure, accessibility, reflow, and theme

Recommended semantic order is the primary Feed `<main>` first, then
supplemental return and Community-context regions with accessible labels. CSS
grid may place the return rail visually left on desktop without making screen
reader users traverse it before the page purpose and composer. Mobile removes
persistent rails and exposes only the locked Catch up entry/sheet.

The Replies & updates row is a labeled horizontal collection with:

- semantic list/card structure;
- keyboard access without trapping Tab;
- visible focus matching the product system;
- at least 44 by 44 CSS-pixel pointer targets for exposed controls;
- touch, trackpad, mouse, and keyboard traversal;
- a non-noisy announced position/count strategy;
- persistent non-gesture `View all Replies & Updates`; and
- no auto-rotation.

Dialogs and sheets require an accessible name, focus containment where
appropriate, Escape/close, inert background, logical reading order, and exact
focus restoration. Status changes use appropriate live-region behavior
without announcing every Feed scroll.

At 200% zoom and large text, the composition may reflow but preserves full
access and the single horizontal row. Phone landscape, narrow/wide desktop,
reduced motion, forced colors, and exact comparison viewports require the
completed visual-state lock.

The current product supports theme behavior, while the six-screen lock covers
only light presentation. Runtime must not silently disable or degrade the
shared theme. The missing-state round must lock dark Community treatment or an
explicit owner-authorized first-slice theme boundary with a safe shell plan.

Before runtime, the completed visual manifest must include a comparison matrix
for every locked file naming CSS viewport, device-pixel ratio, route, scroll
position, shell variant, overlay/sheet state, rail state, composer variant,
and initial focus. Raster dimensions are evidence identifiers, not CSS
viewports. The different shell detail visible behind the mobile Catch up sheet
is one complete sheet-state composition; it is not permission to invent a
second mobile rest shell.

## 13. Mobile disposition and no-new-navigation rule

Locked mobile behavior includes the Feed, Catch up/Spark sheet, selected
contribution, and no persistent rails. Mobile access to Community Pulse and
Active Questions is not locked.

Before implementation, the visual-completion round must choose one truthful
outcome:

- place those functions in a bounded existing sheet/subordinate state; or
- make them desktop-only for the first slice with an explicit owner decision.

It may not add a bottom bar, permanent tab, third Community view, or hidden
mini-Feed. The same requirement applies to conditional search and any
`See all` action.

### 13.1 Catch up sheet interaction

The locked Catch up surface is a modal bottom sheet:

- a scrim and inert background isolate the sheet;
- opening moves focus to the sheet heading or close control;
- close, Escape, and browser Back dismiss it consistently;
- the drag indicator is decorative unless a fully accessible non-gesture
  control exposes the same behavior;
- internal scrolling does not move the underlying Feed;
- safe-area insets protect controls and the final content; and
- dismissal restores focus to the Catch up launcher plus exact Feed and shelf
  state.

The sheet owns independent loading, long-content, partial-failure, empty, and
Spark-unavailable states in the completed visual lock.

## 14. Messaging seam

Until the separately authorized messaging initiative is implemented:

- do not send a message;
- do not show a fake success state;
- do not create browser-local messages that appear real;
- hide the action or render the later Pete-locked truthful unavailable state;
  and
- preserve only an integration input of authorized recipient identity plus an
  optional opaque contribution reference.

When separately authorized, the composer must make recipient and source
context explicit, keep the message private, require a distinct send action,
and use its own moderation, blocking, retention, and delivery contracts.

## 15. Repository integration and reuse boundaries

The runtime initiative should reuse proven repository seams where their
contracts fit:

- trusted Easy Auth decoding and server-derived `user_key` from `identity.py`;
- truthful sign-in and identity-storage-unavailable patterns;
- allowlisted parameterized stored-procedure access in
  `services/database_service.py` and `db.py`;
- existing same-origin JSON mutation and neutral-error patterns;
- platform user, profile, connection, block, and immutable audit primitives;
- managed-identity Blob access plus Capture's byte/signature validation,
  metadata stripping, bounded decode, quarantine, and Defender-tag patterns;
- `community-focus-lifecycle.js` focus capture/restoration concepts; and
- the existing two-view Community route/history behavior, while preserving The
  Break unchanged.

Do **not** reuse the following as a real Community backend:

- `services/people_interests_feed.py` or `people_interests_api.py`;
- `static/data/people_interests_feed.json`;
- `SQL Files/Migrations/proposed/PS-PLAT-008_people_interests_feed.sql`;
- the fixture `/api/slate-feed` payload;
- browser-local post/comment/save state from
  `static/js/feed-living-stream.js`; or
- prototype `#feed-app` CSS as the production style foundation.

Those surfaces are fixture/prototype history and lack the new audience,
contribution, attachment, seen, moderation, and authorization contracts. The
runtime package **must**, before real-member cutover, unregister/neutral-404
the legacy mutable People & Interests API or isolate it as immutable,
unambiguously labeled fixture-only behavior under explicitly reserved scope.
Regression tests must prove anonymous users cannot retrieve a private overlay
post and one signed-in member cannot comment, respond, or save against another
member's inaccessible source. A second public mutable Feed surface may not
survive beside the protected Community domain.

The current template returns Feed and Break markup together. Protected member
data must be fetched only through signed-in, private/no-store APIs or another
equally strong server-authorized boundary. Never serialize private Feed/rail
payloads into a publicly cacheable Break or anonymous shell response.

The future runtime reservation must also own two current shared integration
seams if the chosen implementation requires them:

- `templates/base.html` currently forces a desktop-width viewport on some
  touch tablets unless a route opts into native responsiveness. Community must
  receive an explicitly reserved route-specific/native-responsive treatment
  so tablet, zoom, and reflow evidence tests the real device behavior; and
- the app's private/no-store response policy currently recognizes specific
  blueprint names. The new Community blueprint must be added to that policy or
  own an equivalent `after_request` guard so early `401`, `404`, `409`, `413`,
  `415`, `422`, `429`, and `503` responses are also private/no-store.

The runtime package must own an explicit sample-to-real cutover. A default-off
release flag is acceptable only with a documented safety/rollback reason and
one truthful flag-off state. Real and fixture posts, counts, comments, saves,
or identities must never be mixed in one Feed. No browser-local sample object
is migrated into canonical Community data. Rollback disables the new surface
without deleting member content and preserves The Break plus current redirects.

## 16. Observability and product measurement

Operational evidence is separated into access-controlled streams:

- immutable audit: publication, revision, audience, revocation, deletion,
  moderation, privileged access, and policy version;
- security: authentication/authorization failures, guessed-key patterns,
  abuse/rate-limit signals, and suspicious upload activity;
- reliability: request correlation, latency/error rate, cursor failures,
  scan/derivative callbacks, outbox lag, duplicate suppression, cache/index
  invalidation, and deletion propagation; and
- product measurement: the bounded interaction events below.

The runtime initiative must assign owners, alerts, service objectives,
retention, access controls, and tamper protection. Correlation identifiers are
opaque; logs exclude raw session identifiers and protected cursor contents.

Instrument only events required to validate usefulness, accessibility, and
reliability, such as:

- Feed bootstrap/page loaded or failed;
- caught-up reached and explicit new/earlier-content request;
- Replies & updates shelf exposed, traversed, selected, or View all chosen;
- post/contribution created after explicit publication;
- purposeful response added/changed/removed;
- Spark opened, changed, removed, or used to begin a composer session;
- attachment processing/open failure;
- catch-up item resumed; and
- permission/error state rendered.

Do not create public leaderboards or reward loops from telemetry. Ordinary
logs and analytics exclude post bodies, message text, report text, sensitive
filenames, private audience details, **all raw Community search strings**, and
short-lived media actions/URLs. Search may emit only coarse non-content
metrics unless a separate approved purpose, access, and retention contract
expressly permits more.
Evaluation favors useful replies, successful return/resume, finite-session
completion, authorization correctness, accessibility, and low failure/abuse
rates over time spent or scroll depth.

### 16.1 Explicit V1 AI and external-readiness boundary

V1 invokes no generative AI or external model on Community posts,
contributions, attachments, search, ordering, catch-up, Spark, or moderation.
Spark is human-controlled versioned editorial configuration. Community
content is not used for model training through this architecture.

Any later classifier, assistant, summarizer, or model use requires a separate
package covering member notice, provider/data flow, retention, evaluation,
appeal, failure behavior, and human decision ownership.

Before a real member pilot or release, the release package must verify the
applicable data inventory/retention schedule, Terms/Privacy/Acceptable Use,
upload ownership and confidentiality language, copyright/takedown and
impersonation/harassment contacts, age/minors position, privacy-request path,
moderation/support ownership, incident path, and deletion semantics. A build
may remain default-off while external review is pending; it may not represent
those release gates as passed merely because code or architecture exists.

## 17. Implementation sequence after every gate passes

1. **Resolve the narrow constitutional boundary**
   - use a separately reserved Protected documentation initiative to decide
     whether Constitution rule 7 must explicitly recognize deliberate
     Community-native social speech beside selected-output projections;
   - preserve private-before-public, one canonical fact body, and current
     live/sample truth; and
   - do not edit the current Roadmap, lean site rules, Context Rail standard,
     or archived state records when no current conflict exists.
2. **Complete visual authority**
   - ChatGPT creates only the missing states in document 05;
   - resolve search, Feed modes, mobile Pulse/Questions, theme, Message, and
     signed-out shell treatment without redesigning the six locked screens;
   - Pete locks exact files, hashes, component inventory, state mapping, and
     comparison viewports.
3. **Create the runtime initiative**
   - start from newly fetched authoritative `origin/main`;
   - name manager, sole writer, exact files, migration ownership, rollout,
     tests, and release gates;
   - confirm that no current scoped repository finding applies; and
   - adopt exact audience/community/mode/moderation/attachment contracts.
4. **Domain and trust foundation**
   - add the Community-specific migration, guarded rollback, stored-procedure
     allowlist, services, contracts, cursor signer, and generic multi-member
     fixtures;
   - prove authorization, block/mute, neutral failure, audit, idempotency, and
     concurrency before UI work.
5. **Text-first canonical vertical flow**
   - publish/edit/remove posts and contributions;
   - implement purposeful response and private saves;
   - render full conversation and exact action capabilities.
6. **Finite Feed and restoration**
   - implement stable modes/window/cursors, seen/caught-up, new-content notice,
     one-row shelf, selected detail, deep links, and exact restoration.
7. **Return and Community context**
   - implement catch-up, Continue, Pulse, Questions, Spark, deduplication,
     independent failures, and locked mobile disposition.
8. **Attachments**
   - implement reservation, scanning, derivatives, publication ownership,
     revocation, open/download, cleanup, and locked recovery states.
9. **Exact frontend and release evidence**
   - compare every locked state at its exact viewport;
   - test 320/390/tablet/landscape/wide, large text, 200% zoom, keyboard,
     reduced motion, forced colors, and theme;
   - prove Break, homepage, shared-shell, redirects, and historical-preview
     regressions;
   - complete independent review, Pete acceptance, Azure PR/squash, pipeline,
     production multi-member smoke, rollback, and branch cleanup when release
     is authorized.

## 18. Entry and completion gates

### Runtime entry gate

Runtime work may begin only when all are true:

- the Constitution rule 7 decision is resolved on authoritative `origin/main`
  if the Protected documentation review confirms a clarification is required;
- ChatGPT creates and Pete locks the complete missing V1 state set;
- Search, Feed modes/default, mobile Pulse/Questions, theme, signed-out shell,
  and pre-messaging treatment have exact owner/visual disposition;
- a dedicated implementation initiative names scope, manager, sole writer,
  base SHA, files, migration, tests, rollout, and release gate;
- current Azure `origin/main`, live routes, active initiatives, and collision
  boundaries are reverified;
- exact identity/community, audience, moderation, attachment, edit/delete,
  notification, and data-retention contracts are adopted; and
- current scoped holds are checked and none applies to the selected slice.

As of 2026-07-31 the combined runtime entry gate is not satisfied. This package
may refine documentation only; it may not start application, SQL, test, flag,
or deployment work.

### Implementation completion gate

Implementation is not complete until:

- every required state has exact comparable evidence with no unexplained
  mismatch;
- desktop, phone, landscape, keyboard, large text, 200% zoom, reduced motion,
  forced colors, loading, empty, error, unavailable, permission, moderation,
  deletion, long-content, processing, and recovery states pass;
- multi-member authorization, revocation, concurrency, idempotency, block,
  mute, report, privacy-count, and neutral-error tests pass;
- file security, scan, cleanup, revocation, and open/download tests pass;
- finite-window, deduplication, caught-up, direct-link, and restoration tests
  pass;
- Break, homepage, shared shell, redirects, and unrelated routes remain
  unchanged unless explicitly owned;
- complete-diff self-review and risk-based independent review pass;
- Pete gives final product and visual acceptance; and
- Azure merge, exact deployment pipeline, independent production smoke, and
  cleanup are separately verified when release is authorized.

## 19. Open decisions and current blockers

| ID | Decision or blocker | Required resolution before runtime |
| --- | --- | --- |
| AR-01 | Constitution v3.0 rule 7 says Community connects selected output, while this package also permits deliberate Community-native social truth. | Resolve the narrow durable-boundary wording in a separate Protected documentation change without weakening private-before-public or duplicating Slate truth. |
| AR-02 | The current `PS-AI-OPS-CHECKPOINT-001` findings do not apply to Community and create no global hold. | Recheck scoped holds at runtime-package start; act only if a then-current finding actually overlaps the slice. |
| AR-03 | Missing V1 state boards are not created or Pete-locked. | ChatGPT visual-completion round plus exact Pete lock. |
| AR-04 | Community scope and audience vocabulary are undefined. | Adopt one exact server-derived membership/audience contract and revocation rules. |
| AR-05 | Following/Recent/Questions remain in the inventory but have no locked control/default. | Owner/visual resolution under section 7.1. |
| AR-06 | `Search Community` is visible but absent from the approved inventory. | Add and fully contract it, or lock truthful removal/deferment. |
| AR-07 | Mobile Pulse/Questions access is not locked. | Lock bounded placement or explicit desktop-only V1. |
| AR-08 | Dark theme, signed-out shell, and pre-message truth states are missing. | Lock exact treatments without breaking the shared shell. |
| AR-09 | Exact edit/delete, moderation, notification, response-posture confirmation, attachment formats/sizes/quotas, and retention rules remain open. | Runtime initiative adopts and tests exact contracts; posture is display-only unless separately changed. |
| AR-10 | No runtime initiative, writer reservation, migration ownership, rollout, or release authority exists. | Create it only after prior gates pass and branch from fresh authoritative main. |
| AR-11 | Respond is product-approved but its exact tray and interaction states are not in the six-screen visual lock. | Add the complete visual state family or defer/hide Respond in the first runtime slice. |
| AR-12 | Feed media open/viewer behavior and subordinate See-all/Saved/menu outcomes are not visually locked. | Complete the bounded action-state family in document 05; do not invent new routes or viewers. |

These are explicit gates, not invitations for an implementer to invent product
behavior. The architecture is **review-complete; runtime entry blocked**. Its
technical shape is coherent, while implementation remains prohibited until
every authority and visual decision above is closed.
