# Final Overview architecture contract — 2026-07-26

## 1. Status, authority, and boundary

**Architecture status:** Complete for the `PS-OVERVIEW-001` direction and
implementation-planning gate.

This record incorporates Pete's final visual-review decisions on 2026-07-26
and controls over earlier package language where that language treated the
current right-side résumé ribbon, the future left Context Rail, or Ask AI as
separate unresolved questions.

This is architecture, not implementation. It changes no route, template,
stylesheet, JavaScript, API, schema, migration, feature flag, deployment
configuration, public page, or AI behavior.

The architecture is intentionally complete at the product, logical-record,
service-responsibility, rendering, interaction, authorization, publication,
responsive, and delivery-boundary levels. Exact physical database objects,
HTTP route names, payload shapes, and deployment topology remain the
responsibility of their later activated implementation packages after current
code inspection. Deferring those physical names does not reopen the product
architecture below.

## 2. System purpose

The Overview gives a visitor a fast, polished, member-approved introduction to
the person, their work, and the supporting professional record. It is the
bottom line up front above the detailed résumé.

It is:

- one configurable Overview system;
- a governed projection over eligible member records plus bounded authored
  presentation content;
- manually complete without AI;
- available in **Story & Career** and **Work & Impact** presentation styles;
- published as one exact revision at the existing public résumé audience; and
- integrated with the detailed résumé rather than duplicating it.

It is not:

- a second résumé or canonical fact store;
- a freeform page builder;
- an AI-authored public identity;
- a fixed Pete-specific card sequence;
- a public style switcher;
- a source-verification system for first-release proof points; or
- permission to redesign other PeerSlate rooms.

## 3. End-to-end architecture

```text
eligible profile / résumé / public Story / media records
                     +
bounded member-authored Overview content
                     |
                     v
authorized private Overview draft
  - chosen style and manifest version
  - ordered block placements
  - visibility and emphasis
  - typed destinations
  - media presentation metadata
  - accepted member edits
                     |
        +------------+-------------+
        |                          |
        v                          v
exact visitor preview        separate AI proposals
        |                     - contextual
        |                     - reviewable
        |                     - never auto-applied
        |                          |
        +------------+-------------+
                     |
             explicit member review
                     |
                     v
atomic publication revision
                     |
                     v
public résumé opening slot
  - published Overview, or
  - existing Summary fallback
                     |
                     v
detailed Impact / Skills / Experience / Credentials
```

Application code, not the model or browser, controls identity, authorization,
record eligibility, validation, concurrency, publication, unpublication,
restore, and public retrieval.

## 4. Logical records and ownership

The later physical design must preserve these logical responsibilities without
creating a second source of truth:

| Logical record | Responsibility | Ownership / visibility |
| --- | --- | --- |
| Overview draft | Current private composition and revision state | Owner-only until publication |
| Block placement | Type/version, semantic order, visibility, emphasis, bounded presentation fields | Owner-scoped draft/publication input |
| Record reference | Exact eligible record/projection and reviewed version | Server-authorized reference, not copied fact |
| Authored proof point | Exact member-supplied value, accepted label, icon, optional typed destination | Overview claim; not PeerSlate verification |
| Destination reference | Stable typed section/route/record target | Validated against the public representation |
| Media reference | Eligible media/version, focal data, alt/decorative state, consent and truth label | Never duplicate raw media bytes |
| Style manifest | Versioned renderer and compatibility rules | System-owned presentation authority |
| Block definition | Versioned fields, budgets, validation, renderer, and accessibility rules | System-owned finite contract |
| AI proposal | Proposed operation, context/source set, output, decision state, model/program provenance | Separate from accepted draft state |
| Publication revision | Exact pinned visitor-result inputs, audience, versions, and timestamp | Immutable historical public revision |
| Current-public pointer | The one active publication for a member/profile | Server-controlled and concurrency-protected |

One member/profile has at most one current public Overview in the first
release. Private drafts and retained publication history do not create
additional public Overviews.

## 5. One opening, then the real résumé

The combined page has exactly one opening slot:

1. If a current Overview publication exists, render the Overview.
2. Otherwise, render the existing résumé Summary.
3. Never render both openings.
4. A published Overview ends at **RÉSUMÉ BEGINS HERE**.
5. The existing detailed Impact, Skills, Experience, and Credentials content
   follows directly below and remains authoritative.
6. The Overview never renders the concepts' duplicate “Full Résumé” summary.
7. Unpublishing atomically restores the Summary fallback without deleting
   Overview history or silently applying newer draft content.

The public résumé route remains the stable visitor destination. Exact route
integration is activated only in the later publication/public-integration
slice.

## 6. Desktop shell: three distinct regions

The final wide-desktop composition has three distinct regions:

1. **Left Context Rail** — member identity plus local résumé section depth.
2. **Center stage** — the Overview followed by the detailed résumé.
3. **Right contextual AI rail** — Ask [Name] AI publicly or Ask Slate AI in an
   authorized private workspace.

The rails are shell/context components. They are not Overview blocks, do not
consume the Overview block budget, and do not create a second content canvas.

On a sufficiently wide viewport, both rails may remain sticky while the center
stage scrolls. Sticky behavior must respect the global header, viewport height,
keyboard focus, zoom, and reduced-motion preferences. Neither rail may trap
page scrolling.

The center stage remains visually dominant. A rail must undock before it
squeezes the center below the accepted readable composition. The exact
implementation breakpoint is determined from measured available width rather
than monitor inches.

### Geometry invariants

- The Overview root fills 100 percent of the resolved center stage.
- The center stage has no nested arbitrary page-level `max-width` copied from
  the 864- or 941-pixel source boards.
- The center stage may cap at the accepted wide composition; unused space
  becomes intentional outer gutter, not enlarged body-copy measure.
- Major media, proof bands, rules, and count-aware grids may use the stage.
- Prose retains an approximately 55–70-character readable measure.
- Primary body copy is at least 16 CSS pixels at normal scale.
- The fitting chain uses computed `zoom: 1` and `transform: none`.
- At implementation, the center and Overview edges must agree within two CSS
  pixels after normal layout rounding.

The earlier `min(92vw, 90rem)` amendment remains the starting center-stage
candidate when the shell has sufficient space. With both rails docked, the
center resolves from the available shell width rather than shrinking all three
regions to preserve that number. If the center cannot retain the accepted
composition, the right AI rail becomes a drawer first.

## 7. Left Context Rail

The left rail deliberately replaces the weaker current right-side section
ribbon when the Overview/public-résumé integration slice is activated.

### Contents

- Member portrait and display name.
- Small room label: **RÉSUMÉ SECTIONS**.
- **Overview** when a publication renders, otherwise **Summary**.
- **Impact**.
- **Skills**.
- **Experience**.
- **Credentials**.
- Divider.
- **Résumé PDF** as the existing document action.

My Story, Work, Slate Board, Community, Interview Studio, and other route-level
destinations remain in the existing global/profile navigation. They are not
duplicated in the rail.

### Behavior

- Every section entry stays within the current résumé page, satisfying Context
  Rail Law 1.
- Activation moves to a stable anchor, accounts for sticky offsets, updates
  the URL fragment without unnecessary history spam, and places focus on the
  destination heading when the user invoked navigation.
- Scroll-following active state uses the section most meaningfully in view.
- Exactly one entry has `aria-current="location"` or the equivalent current
  state.
- Hidden/absent sections have no rail entry.
- The first entry changes atomically with the rendered opening:
  `Overview`/`#overview` or `Summary`/`#summary`.
- Compatibility aliases such as the existing `#resume-overview` may resolve to
  the current opening, but the rendered rail exposes only one first entry.
- `View Résumé`, `View detailed experience`, `View all skills`, `View
  education`, `View certifications`, and `View awards` use the same typed
  destination system.

The PDF entry is a page-local résumé tool allowed by the Context Rail Standard;
it is separated visually from section destinations and appears only once.

## 8. Right contextual AI rail

The right rail is a distinct contextual-assistance region, not navigation and
not an Overview content block.

### Public member pages

- Product name: **Ask [Name] AI**; Pete's fixture is **Ask Pete AI**.
- Suggested introduction:
  “Ask about [Name]’s work, experience, skills, or professional story.”
- Grounding is limited to the member's approved public representation and
  other explicitly eligible public sources.
- It cannot access private Slate, drafts, unpublished content, private
  messages, hidden records, or another member's data.
- It may follow the section the visitor is exploring and disclose that context.

### Signed-in private workspaces

- Product name: **Ask Slate AI**.
- It may use only the authenticated member's authorized private workspace
  context for the current task.
- In the Overview editor it may help choose a style, suggest eligible sections,
  review a draft, identify repetition, propose wording, or explain a blocker.
- It cannot save, reorder, hide, remove, accept, publish, unpublish, restore,
  send, or otherwise mutate content without the member's explicit
  deterministic action.

### Cross-product boundary

Pete's direction is to use this contextual AI-rail pattern broadly across
eligible Slate/Studio surfaces, including résumé, Workshop, Slate Board, and
Interview Studio where purposeful. This Overview package records the shared
direction and dependency only.

It does not authorize changes to those other surfaces. Each adoption must:

- pass the applicable page-purpose/non-redundancy test;
- use Ask [Name] AI for public member context or Ask Slate AI for authorized
  private workspace context;
- define exact permitted data and actions;
- preserve the room's purpose and visual authority;
- satisfy privacy, accessibility, failure, and responsive requirements; and
- obtain its own activated package and owner acceptance.

### Responsive behavior

- Wide desktop: docked/sticky when the center retains accepted width.
- Intermediate desktop/tablet: closes into a labeled drawer or side sheet.
- Mobile: remains first-class through a prominent **Ask [Name] AI** or
  **Ask Slate AI** action; it is not buried in an unrelated hamburger menu.
- Closing the rail never loses unsent text without warning.
- Opening/closing returns focus predictably and uses a proper dialog/sheet
  pattern when modal.

## 9. Responsive composition

Responsive behavior is recomposition, not proportional shrinking.

| Mode | Local sections | AI assistance | Center |
| --- | --- | --- | --- |
| Wide desktop with sufficient center width | Sticky left rail | Sticky right rail | Full dominant stage |
| Standard/narrow desktop | Sticky or compact left rail | Drawer/side sheet when docking would squeeze center | Full available stage |
| Tablet / 200% reflow | Compact labeled Sections control or chip row | Drawer/sheet | One semantic content column |
| Mobile | Member-context row plus Sections control/chip row | Prominent contextual action and sheet | Stacked hero, 2×2 proof grid when valid, single-column blocks |

On mobile:

- the public Story & Career hero stacks portrait/media, identity, contact, hero
  actions, then proof items;
- editor side panels become full-width sheets or dedicated steps;
- reorder controls have touch and structured alternatives;
- sticky actions must not cover fields or destination content;
- no horizontal page scrolling or two-dimensional content scrolling is
  permitted; and
- the desktop rails are not rendered as skinny columns.

## 10. Finite block and layout model

The member chooses content, order, visibility, approved emphasis, media, and
truthful destinations. PeerSlate chooses geometry, typography, spacing,
count-aware arrangements, responsive reflow, and accessibility.

The first-release library remains finite:

- Profile Hero.
- Proof Band.
- Story Spotlight.
- Career Arc / Career Focus.
- Impact Highlights.
- Skills Preview.
- Education Preview.
- Certifications Preview.
- Awards Preview.
- Story Chapters.
- Quote.
- Philosophy.
- Flexible Text + Media.
- Highlights List.
- Proof Cards.
- Custom Section using a supported content layout, never arbitrary HTML/CSS.
- Résumé Transition / Closing invitation.

An empty, hidden, unauthorized, invalid, or removed block emits no public
wrapper, margin, grid track, destination, or rail entry.

Count-aware behavior handles zero, one, or many truthful records:

- zero items omit the block;
- one proof point receives a deliberate feature treatment;
- one role becomes Career Focus rather than a fake timeline;
- one degree renders as confident Education rather than filler;
- credentials appear only when present;
- Skills precedes Education, Certifications, and Awards; and
- four to six major content bands is normal, with eight the absolute
  first-release maximum. Hero and optional proof band do not count.

Longer canonical sections remain in the detailed résumé. Overview previews
show bounded selected items and a specific destination such as **View all
skills**, never generic “More,” clipping, internal card scrolling, or hidden
overflow.

## 11. First-time setup and self-service editor

The owner begins with two explicit choices:

1. Choose **Story & Career** or **Work & Impact**.
2. Choose **Build it myself** or **Create a draft with AI**.

Story & Career is recommended, not silently selected as permanent public
truth. Both paths create a private draft. Neither publishes.

The manual editor supports:

- edit hero and contact fields;
- create, select, edit, hide, remove, and reorder supported sections;
- edit exact proof values and labels;
- select typed destinations;
- choose eligible media, focal point, alt/decorative state, and required truth
  or consent information;
- preview desktop/mobile and exact public output;
- save private progress;
- recover from save failure or stale revision;
- review all changes; and
- explicitly publish, unpublish, or restore.

Desktop edit controls may use an adjacent inspector. Mobile uses a full-width
sheet or focused editing step. Drag handles are convenience only; every
reorder action has keyboard, button, and structured-list equivalents.

## 12. Proof-point contract

A first-release proof point contains only:

- exact member-supplied display value;
- short member-authored or member-accepted label;
- optional supporting text within the block definition;
- optional icon;
- optional validated public destination;
- placement/order; and
- visibility.

It contains no source selector, evidence attachment, verification badge,
confidence, “source-backed,” “member-confirmed,” or unsupported/provenance
state.

AI may preserve the exact value and propose label/supporting wording. Numeric
tokens remain immutable unless the member explicitly supplies a replacement.
If a request lacks the exact value, AI leaves the value unchanged and asks the
member.

## 13. Destination resolution

Destinations are typed references resolved by the server. They are not
arbitrary member-entered URLs or owner IDs.

Before publication, a destination must:

- exist;
- be public to the same audience;
- belong to the correct member/profile;
- resolve to a stable route/anchor or eligible public record;
- remain meaningful when optional blocks are absent; and
- expose no private data in markup, preload, metadata, or error states.

If a destination becomes invalid, the system removes or blocks the action
according to the block contract. It never renders a dead generic button.

## 14. Draft, preview, publication, and restore

Draft save and public publication are separate operations.

### Draft

- Owner identity is server-derived.
- Saves use optimistic concurrency/version protection.
- Autosave may update private draft state only.
- A stale editor never overwrites a newer draft.
- Save failure preserves local edits and provides retry/reload/compare choices.

### Preview

- Exact visitor preview uses the same projection and renderer versions as
  publication.
- Editing furniture, private sources, AI metadata, hidden blocks, and owner
  controls are absent.
- Desktop, mobile, large-text, and missing-content states are reviewable.

### Review and publish

The review screen explicitly states:

- the Overview will replace the current Summary opening;
- detailed Impact, Skills, Experience, and Credentials remain below;
- no detailed résumé content is deleted or rewritten;
- the public destination;
- included and omitted sections;
- omitted sections leave no empty space; and
- publication is an explicit immediate public action.

Publishing validates authorization, expected versions, audience, block/style
compatibility, destinations, media, and public projection; creates one
immutable publication revision; and atomically moves the current-public
pointer. The prior publication remains active on failure.

### Unpublish and restore

- Unpublish previews the Summary fallback and acts atomically.
- Restore revalidates an older revision and republishes it as a new current
  revision; it never rewinds history silently.
- Publication, unpublication, and restore compare the expected current
  revision to prevent lost updates.

## 15. Source change and fail-closed behavior

- Benign evolution may leave a pinned publication stable; a new publish
  requires review.
- Revoked, deleted, audience-narrowed, or known-invalid content is never
  silently replaced with AI wording.
- An invalid optional block may be omitted if the remaining publication stays
  coherent and the member receives a review/recovery path.
- If corrective omission makes the opening incoherent, public rendering fails
  closed to the existing Summary fallback.
- Failure does not leak the invalid private record or explanation publicly.

## 16. AI proposal architecture

AI operations are separate proposal records. A proposal identifies:

- requested operation and target field/block;
- authorized context/source set;
- exact member-supplied locked values;
- output;
- material uncertainty or missing context;
- model/program version and timestamp;
- decision state: pending, accepted, edited, dismissed, or superseded; and
- the draft version against which it was created.

Using a suggestion fills the appropriate editor state for review. It does not
save or publish. Accepted wording becomes ordinary private draft content only
after the member's deterministic action.

AI provider failure leaves the complete manual workflow available. The product
does not claim that an unavailable suggestion is required to finish.

## 17. Logical service boundaries

Exact endpoint names remain deferred, but a later implementation must preserve
these responsibilities:

- **Overview authorization service** — derives owner/profile and enforces
  owner/public access before retrieval.
- **Eligible-content resolver** — returns only records/media/destinations the
  owner may use for the intended audience.
- **Draft command service** — creates, edits, reorders, hides, removes, and
  saves with concurrency protection.
- **Projection builder** — produces a generic, serializable, style-neutral
  semantic read model.
- **Manifest renderer** — renders Story & Career or Work & Impact
  deterministically from the projection.
- **Preview service** — returns the exact visitor representation without
  publishing.
- **Proposal service** — creates and decides separate AI proposals.
- **Publication service** — validates and atomically publishes, unpublishes, or
  restores.
- **Public integration adapter** — selects Overview or Summary for the résumé
  opening and supplies local section state.
- **Contextual AI adapter** — supplies only the public or private authorized
  context appropriate to the current rail.

The browser cannot declare ownership, public eligibility, rendered HTML,
publication state, or valid destinations.

## 18. Security, privacy, and caching

- Authorization occurs before protected retrieval, not through client
  filtering.
- Public and owner representations are separate payloads.
- Public output contains no draft text, hidden blocks, private source IDs,
  owner controls, AI metadata, readiness state, or unauthorized media URLs.
- Cross-member references are rejected even when identifiers are guessed.
- Owner draft/editor responses use private/no-store caching as appropriate.
- Public publication caching keys include the exact current revision and are
  invalidated atomically on publish, unpublish, restore, or corrective
  supersession.
- Logs contain identifiers and state transitions needed for diagnosis, not
  private bodies, prompts, media contents, or public contact values.

## 19. Accessibility requirements

The implementation must meet WCAG 2.2 AA and prove:

- semantic headings and landmarks;
- labeled local-section navigation;
- keyboard and assistive-technology operation;
- visible focus and correct current states;
- no drag-only action;
- focus management for anchors, inspectors, drawers, sheets, confirmation, and
  errors;
- mobile touch targets;
- 200-percent reflow without horizontal page scrolling;
- reduced-motion behavior;
- forced-colors support;
- meaningful image alt text or explicit decorative treatment;
- no essential meaning conveyed only by position, animation, icon, or color;
- no fixed text-height clipping; and
- no-JavaScript public meaning for the rendered Overview and résumé.

## 20. Failure and recovery states

The later implementation must explicitly handle:

- no draft;
- empty/sparse draft;
- draft loading;
- draft unavailable;
- saving;
- saved;
- save failed;
- stale draft conflict;
- invalid block;
- unavailable/ineligible media;
- missing destination;
- AI unavailable;
- proposal stale after draft change;
- publish blocked;
- publishing;
- publish failed;
- current-public conflict;
- unpublishing;
- unpublish failed;
- restored publication;
- corrective omission; and
- Summary fallback.

No failure may partially publish, silently discard member work, expose private
content, or present fixture behavior as stored/live behavior.

## 21. Delivery sequence

Architecture completion does not activate all slices at once.

1. **Visual-authority package:** preserve approved files, final decisions,
   architecture, and evidence; no runtime.
2. **Slice 1 — generic projection/renderer foundation:** internal-only,
   multi-fixture, no persistence or public-route change.
3. **Slice 2 — private manual composer/draft lifecycle:** authenticated,
   owner-only, no publication.
4. **Slice 3 — exact preview and publication lifecycle:** publish, unpublish,
   restore, history, concurrency, audience, and fail-closed behavior.
5. **Slice 4 — public résumé integration and Context Rail migration:** one
   opening, detailed résumé preserved, stable destinations, homepage parity.
6. **Slice 5 — optional Overview AI proposals:** only after the manual
   workflow and proposal/privacy evaluation pass.
7. **Separate cross-product AI-rail package(s):** evaluate and adopt the shared
   contextual rail in other eligible Slate/Studio rooms without expanding this
   package.

Every runtime slice uses a fresh branch from current Azure `origin/main`,
explicit writable files, generic/multi-owner fixtures, focused tests,
complete-diff self-review, risk-triggered independent review, Pete's
corrected-real-build visual acceptance where material, Azure PR/squash,
pipeline evidence, and honest live verification.

## 22. Architecture acceptance and stop conditions

The architecture is complete when the package:

- records one system/two styles;
- specifies the one-opening résumé relationship;
- defines the finite content/reflow model;
- defines manual editor, AI proposal, preview, publication, and recovery
  boundaries;
- defines left local-section rail and right contextual AI rail responsibilities;
- defines public versus private AI grounding;
- defines mobile/intermediate/wide behavior;
- defines logical records and service responsibilities;
- preserves multi-user authorization and canonical-truth boundaries;
- sequences runtime work without authorizing it; and
- names superseded earlier assumptions.

Those conditions are satisfied by this record and the linked package contracts.

Stop and return to Pete before implementation if a later writer proposes:

- a second résumé/profile truth store;
- first-release proof verification/provenance;
- AI-derived numeric values;
- a public style switcher;
- an independent Overview audience;
- a rail entry that leaves the résumé room;
- private context in public Ask [Name] AI;
- automatic AI save/apply/publish;
- arbitrary HTML/CSS or coordinate placement;
- a narrower material composition than the locked visual authority;
- a route/schema/API change outside an activated slice; or
- cross-product AI-rail implementation without its own package.

## 23. Superseded package assumptions

| Earlier assumption | Final controlling architecture |
| --- | --- |
| Current right ribbon remains while left Context Rail is separately deferred | Public-integration slice replaces the weaker right ribbon with the approved left local-section rail |
| Right rail contains duplicate section links | Right rail is contextual AI; section navigation is left only |
| Left rail repeats My Story, Work, or Slate Board | Those stay in global/profile navigation; left rail contains résumé depth only |
| Ask AI is a small optional link | Contextual AI remains prominent: docked on wide screens, drawer/sheet when narrower, first-class action on mobile |
| Ask Pete AI and Ask Slate AI are interchangeable | Ask [Name] AI is public and public-grounded; Ask Slate AI is signed-in and authorized-private |
| Both rails must remain docked at every desktop width | Center readability controls; AI undocks before the center becomes cramped |
| Physical schema/API/route names are part of this visual branch | Logical contracts are complete here; physical names require later activated implementation packages |
| The early generated `*-wide-standard*` pair controls the final shell | Those files are superseded visual-generation history; the owner-approved rich, sparse, narrow, mobile, editor, review/publish, and AI-context references control |

## 24. Deliberately deferred decisions

The following require later explicit packages and do not make this architecture
incomplete:

- physical database schema and migration design;
- exact production endpoint and payload names;
- source-backed/evidence-linked proof points;
- PeerSlate verification badges or metric provenance states;
- an independent Overview audience;
- public visitor style switching;
- cross-product rollout of the contextual AI rail;
- final model/provider/prompt/evaluation selection;
- enablement/deployment sequencing;
- homepage projection implementation; and
- changes learned from real-member usability testing.

Each deferred item may refine implementation detail, but it may not silently
reverse the architecture above.
