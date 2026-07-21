# PS-JOURNAL-001 — Normative Requirements and Architecture Gate

## Status and interpretation

These requirements are controlling architecture, not evidence of runtime
implementation. **Shall** means required. **May** means permitted but optional.
An implementation brief may narrow a first slice but may not contradict a
requirement or silently defer a safety boundary needed by that slice.

## Definitions

- **Capture action:** a persistent entry point that opens the universal
  composer in the current context. It is not a destination.
- **Universal composer:** the responsive sheet, drawer, dialog, or inline layer
  through which a member speaks, types, or later attaches supported media and
  saves a Moment.
- **Source:** immutable or revision-preserving original input and related
  processing state, governed by retention/deletion policy.
- **Moment:** the member-owned canonical record. The first version is the exact
  member-authored or member-reviewed content explicitly accepted by Save
  Moment. Later edits and accepted proposals create versions.
- **Journal:** the complete longitudinal experience over a member's Moments and
  Journal-specific presentation metadata. It is not a fact-bearing body table.
- **Curated Journal:** an owner-selected subset/order/emphasis of eligible
  Moments for a purpose or audience. It remains a view of the one Journal.
- **Public Journal:** the logged-out audience projection of owner-selected
  eligible Moments. It may feel like a profile/timeline but is not My Story.
- **Placement:** an exact-version governed reference from a Moment to an
  eligible downstream domain. Journal membership itself is not a Placement.
- **Projection:** purpose/audience-specific presentation referencing canonical
  records and permitted wording/layout state without silently forking facts.
- **Visibility/audience:** who may retrieve a record or projection.
- **Lens:** owner organization such as Work, Personal, or Both. A lens is not an
  audience or publication state.

## Universal Capture requirements

- **PS-JRN-CAP-001:** Every eligible authenticated primary room shall expose a
  consistent Capture action without requiring navigation to another page.
- **PS-JRN-CAP-002:** Target information architecture shall not create a
  permanent Capture page, tab, room, or top-level destination.
- **PS-JRN-CAP-003:** Opening Capture shall preserve the origin route, object,
  scroll/focus context where practical, and any unsaved origin-room work.
- **PS-JRN-CAP-004:** The composer may receive a minimal purpose hint from the
  origin room, but shall not require the member to choose Journal, Story, Work,
  résumé, Feed, Project, Board, or Studio before describing the Moment.
- **PS-JRN-CAP-005:** Type and Speak shall remain first-class opening choices.
  Neither may be hidden behind the other or treated as a fallback-only path.
- **PS-JRN-CAP-006:** The primary successful commit shall be labeled **Save
  Moment**. “Save Capture,” “Add to Journal,” and equivalent two-step product
  gates shall not be the target completion language.
- **PS-JRN-CAP-007:** The member shall always see the current private default,
  source/input state, processing state when applicable, and what Save Moment
  will create.
- **PS-JRN-CAP-008:** Text shall work when microphone, speech, media processing,
  AI, queues, or external providers are unavailable.
- **PS-JRN-CAP-009:** Voice shall preserve the authorized original recording
  and editable transcript according to the released Voice lifecycle. The
  member shall be able to correct transcript text before accepting it as a
  canonical Moment version.
- **PS-JRN-CAP-010:** Later photo, video, and document inputs shall use the same
  ownership, privacy, source, processing, Save Moment, and failure architecture;
  their presence here is not runtime enablement.
- **PS-JRN-CAP-011:** Cancel, close, retry, offline/interrupted explanation,
  processing delay, and recoverable draft behavior shall be explicit and shall
  not create hidden duplicates.
- **PS-JRN-CAP-012:** After save, the composer shall return the member to the
  origin context or close in place. Opening Journal is an optional next action,
  not a mandatory route transition.
- **PS-JRN-CAP-013:** After save, the origin room may show at most one primary
  and two secondary relevant actions, including Use This Moment or View in
  Journal. These are shortcuts, not the complete destination set. Dismissal
  shall complete the flow without loss.
- **PS-JRN-CAP-014:** The Capture action and composer shall be keyboard,
  screen-reader, touch, mobile, 200%-zoom, reduced-motion, and long-content
  usable, with predictable focus restoration.
- **PS-JRN-CAP-015:** Capture telemetry shall record privacy-safe event/status
  metadata only and shall not log Moment text, transcripts, media, private
  prompts, or source content.

## Save Moment and canonical-record requirements

- **PS-JRN-MOM-001:** Save Moment shall explicitly create or confirm exactly one
  owner-scoped canonical Moment and at least one pinned source relationship.
- **PS-JRN-MOM-002:** The initial canonical version shall preserve the content
  the member explicitly authored or reviewed. AI-polished language shall not be
  substituted implicitly.
- **PS-JRN-MOM-003:** Source creation/version pinning and Moment creation shall
  be one idempotent application operation with a documented transactional or
  compensating-failure contract.
- **PS-JRN-MOM-004:** Duplicate submit, network retry, browser refresh,
  double-click, queue redelivery, and provider callback retry shall not create
  multiple Moments for one accepted save.
- **PS-JRN-MOM-005:** When nonessential enrichment fails after the Moment is
  safely saved, the member shall keep the Moment and receive a truthful,
  recoverable enrichment state rather than a false save failure.
- **PS-JRN-MOM-006:** When the canonical save fails, no UI shall claim that the
  Moment is in Journal. Recoverable source/draft state and retry behavior shall
  be explicit.
- **PS-JRN-MOM-007:** AI classification, title, summary, tags, inferred
  relationships, Work/Personal lens, importance, audience, and downstream use
  shall be proposals unless the member set them directly.
- **PS-JRN-MOM-008:** Accepted edits shall create governed versions and preserve
  author/actor, time, source relationship, reason/state, and optimistic
  concurrency. A stale client shall not overwrite newer work silently.
- **PS-JRN-MOM-009:** Correction of source material shall not silently rewrite
  an already accepted Moment version. The member shall see and approve any
  proposed reconciliation.
- **PS-JRN-MOM-010:** Moment save shall not publish, broaden audience, create a
  Feed post, change a résumé, send a message, create a Project, alter Story, or
  create another person's access.
- **PS-JRN-MOM-011:** Work, Personal, and Both shall be independent owner lenses
  that do not imply professional/public visibility or diagnose identity.
- **PS-JRN-MOM-012:** Original recording playback may be offered when a real,
  retained, authorized source exists. Synthetic or cloned own-voice playback is
  not part of this requirement set.

## One-Journal requirements

- **PS-JRN-JRN-001:** Each member shall have exactly one logical Journal over
  their canonical Moments.
- **PS-JRN-JRN-002:** Owner Journal membership shall be derived from eligible
  member-owned Moments and lifecycle state; it shall not require a Journal
  Placement, copied body, or separate member action.
- **PS-JRN-JRN-003:** A newly saved Moment shall be retrievable in the owner's
  Journal immediately after the save transaction commits, subject only to
  truthful consistency/error behavior.
- **PS-JRN-JRN-004:** Journal-specific metadata may store pinning, feature
  emphasis, curated order, section/chapter grouping, a short presentation-only
  curation annotation, display treatment, suppression from a curated view, or
  audience-purpose state. An annotation may explain selection or display; it
  shall not introduce a substantive event, claim, reflection, or narrative.
  Substantive new member text must be saved as a Moment or as a separately
  governed purpose-specific projection, never hidden in Journal metadata.
- **PS-JRN-JRN-005:** The owner Journal shall support chronological timeline,
  list/detail, search, local filters, source inspection, version history,
  relationships, visibility, curation, and lifecycle controls.
- **PS-JRN-JRN-006:** Search shall begin with deterministic structured/full-text
  owner-authorized retrieval. Semantic retrieval is optional and may not be the
  sole path to finding a Moment.
- **PS-JRN-JRN-007:** Filters may include time, Work/Personal/Both, source/input
  type, project/goal/relationship, visibility, curation, status, and member-
  approved tags. Filters shall not become top-level destinations.
- **PS-JRN-JRN-008:** Importance, lens, curation, audience, placement, and
  publication shall remain independent fields/decisions.
- **PS-JRN-JRN-009:** Archive shall remove a Moment from the default active view
  without implying deletion; the owner shall be able to inspect and restore it
  when policy permits.
- **PS-JRN-JRN-010:** Deletion shall use an explicit, retryable, observable
  lifecycle with defined propagation to search, projections, references,
  intelligence, media authorization, caches, exports, and tombstones.
- **PS-JRN-JRN-011:** Export shall clearly distinguish canonical content,
  original sources when exportable, metadata, audience/publication state,
  projections, and private intelligence.
- **PS-JRN-JRN-012:** Restricted/deleted/unavailable sources and media shall
  have truthful tombstone or recovery behavior; no broken asset may reveal a
  private path or ownership clue.
- **PS-JRN-JRN-013:** Essential owner Journal functions shall remain useful when
  AI, speech, semantic search, resurfacing, or external providers are down.
- **PS-JRN-JRN-014:** Empty, first-Moment, loading, partial, long-history,
  restricted, processing, stale, conflict, offline, error, retry, recovery,
  archived, deleted, and export states shall be designed.
- **PS-JRN-JRN-015:** Journal chronology shall use an explicit event/display
  time policy and shall not silently reorder history based only on AI inference.
- **PS-JRN-JRN-016:** A member shall be able to correct or remove curation and
  interpretation without corrupting the Moment or its source history.
- **PS-JRN-JRN-017:** Journal may provide a curated/profile-like presentation
  mode, but the functional timeline/list and accessible semantic order shall
  remain available.
- **PS-JRN-JRN-018:** No Journal count, year/month summary, search result count,
  media indicator, or insight preview may include unauthorized records for the
  current viewer.

## Use This Moment and downstream requirements

- **PS-JRN-USE-001:** Use This Moment shall be available after save and later
  from Journal/detail or an eligible consuming room.
- **PS-JRN-USE-015:** Use This Moment shall expose a complete accessible
  chooser of every currently supported and authorized destination or purpose
  for that Moment. It may explain unavailable future options as clearly
  disabled `Coming later` items only when the visual-authority package permits
  them. Suggested shortcuts may rank or prefilter, but shall never hide an
  eligible supported choice, imply an unavailable capability works, or place
  anything automatically.
- **PS-JRN-USE-002:** A downstream use shall reference an exact governed Moment
  version or create a separately governed purpose-specific projection that
  remains traceable to it.
- **PS-JRN-USE-003:** Feed, Story, Work, résumé, Project, Board, Studio, public
  Journal, and messaging shall not create independent canonical copies of the
  same facts.
- **PS-JRN-USE-004:** Direct Feed and direct résumé fact creation that bypasses
  Save Moment is not part of the target architecture.
- **PS-JRN-USE-005:** The origin room may rank suggestions using deterministic
  context and permitted intelligence, but the member chooses whether and where
  to continue.
- **PS-JRN-USE-006:** No use action shall publish, send, broaden audience, or
  overwrite destination content without a separate explicit preview/approval
  appropriate to that domain.
- **PS-JRN-USE-007:** Purpose-specific wording shall be a projection draft with
  source/version linkage, not a mutation of the canonical Moment.
- **PS-JRN-USE-008:** Removing a Moment from Story, résumé, Feed, or another
  projection shall not remove it from the owner's Journal.
- **PS-JRN-USE-009:** Deleting or revoking a Moment/source shall define how each
  reference and projection becomes removed, invalidated, tombstoned, or
  member-review-required.
- **PS-JRN-USE-010:** A consuming room shall retrieve only the minimum
  authorized context required for its purpose.
- **PS-JRN-USE-011:** A public browser-local Studio or demonstration shall not
  claim to save a cloud Moment. Authenticated Studio may save through the same
  universal composer contract.
- **PS-JRN-USE-012:** A reference sent in messaging shall remain subject to the
  message/share authorization contract; canonical Journal visibility shall not
  be inferred from thread membership.
- **PS-JRN-USE-013:** Failed downstream activation shall not roll back a safely
  saved Moment. The member shall see that the Moment is saved and the later use
  still needs attention.
- **PS-JRN-USE-014:** Homepage and public product projections shall be reviewed
  for truthful parity whenever the real Capture/Journal interaction changes.

## Audience and viewer requirements

- **PS-JRN-AUD-001:** Owner, selected-person, Connection, signed-in member, and
  Public modes shall be resolved from trusted server identity, relationship,
  grants, audience, publication, block, and lifecycle state.
- **PS-JRN-AUD-002:** Authorization shall occur before retrieval. Fetching the
  owner Journal and filtering it in the browser is prohibited.
- **PS-JRN-AUD-003:** The owner mode shall expose the complete eligible record;
  another viewer shall receive only Moments and fields explicitly permitted for
  their actual mode.
- **PS-JRN-AUD-004:** Public/permissioned Journal selection is curation and
  publication metadata referencing canonical Moments; it is not another
  content store.
- **PS-JRN-AUD-005:** New Moments and new intelligence shall default to Only Me.
- **PS-JRN-AUD-006:** A visibility/audience change shall require exact-audience
  preview and shall not be bundled invisibly into Save Moment.
- **PS-JRN-AUD-007:** Selected-person access shall identify the specific grant
  and expiry/revocation behavior; it shall not become public or Connection-wide
  by accident.
- **PS-JRN-AUD-008:** Connection access shall require an active permitted
  relationship and shall stop after revoke, block, or relationship removal.
- **PS-JRN-AUD-009:** Block, report, mute, relationship removal, unpublish,
  archive, delete, and audience change shall invalidate caches/search/indexes
  and downstream retrieval according to an observable propagation contract.
- **PS-JRN-AUD-010:** Unauthorized responses shall omit private content,
  source/media metadata, insight text, counts, relationship clues, search
  matches, and timing signals. Neutral not-found behavior shall be used where
  appropriate.
- **PS-JRN-AUD-011:** A public Journal may look like a profile/timeline, but
  shall state whose Journal it is and present only owner-approved material.
- **PS-JRN-AUD-012:** Viewer-facing comparisons, Replay, Noticed, and Then and
  Now shall compute only from the viewer-authorized projection and shall not
  reveal gaps caused by hidden Moments.
- **PS-JRN-AUD-013:** Public Ask [Name] AI may cite only records independently
  authorized for that viewer; public Journal presence does not authorize
  private source retrieval.
- **PS-JRN-AUD-014:** Audience and publication are separate from Work/Personal
  lens, importance, placement, and Story selection.
- **PS-JRN-AUD-015:** The member shall be able to preview owner, selected-person,
  Connection, member, and Public states without relying on client simulation of
  data that the target viewer could not retrieve.
- **PS-JRN-AUD-016:** No route or slug shall be treated as access authority.
- **PS-JRN-AUD-017:** Cross-owner and guessed-ID negative tests shall cover
  list, detail, search, filters, source, media, versions, relationships,
  projections, exports, and intelligence.
- **PS-JRN-AUD-018:** Public/permissioned Journal shall not ship before legal,
  moderation/contact, authorization, payload-isolation, accessibility, and
  owner-preview gates pass.

## Information-architecture requirements

- **PS-JRN-IA-001:** Journal is a core signed-in domain; Capture is a global
  action. Exact navigation labels/order/routes remain open.
- **PS-JRN-IA-002:** No implementation may lock a new production route map
  without a route-collision audit and owner-approved desktop/mobile map.
- **PS-JRN-IA-003:** Global site navigation, member/public Slate navigation,
  contextual room controls, and the Capture action shall remain distinguishable.
- **PS-JRN-IA-004:** The Slate Spine or other connective pattern shall not
  become another permanent navigation layer.
- **PS-JRN-IA-005:** Journal filters, curated views, Replay, Noticed, Mirror,
  prompts, and rituals shall not become top-level destinations by default.
- **PS-JRN-IA-006:** The legacy Capture route may temporarily deep-link to or
  open the universal composer during migration, but shall not define the target
  interaction.
- **PS-JRN-IA-007:** Public Journal and My Story may coexist in public member
  navigation only after their labels, purpose, route ownership, and empty/
  unavailable states are comprehensible in user validation.
- **PS-JRN-IA-008:** Mobile shall use readable document flow, contextual sheets,
  and appropriate navigation—not a shrunken desktop timeline or canvas.

## Explicit non-goals for the first implementation

- Public/permissioned Journal, My Story Composer, messaging, full Replay, Slate
  Mirror, Life Constellation, synthetic voice, or every media input at once.
- A new canonical Journal-entry table containing copied Moment text.
- A navigation redesign without the route-map gate.
- AI-only search, AI-controlled audience, automatic publication, automatic
  projection, or public social-growth mechanics.
- Rebuilding released source/Moment/Placement foundations when orchestration or
  bounded extension is sufficient.
