# Implementation information and acceptance plan

## 1. Purpose and boundary

This record gives a future architect/writer enough product information to
prepare a bounded implementation package. It does not authorize schema, API,
route, template, service, feature flag, or deployment work.

Exact technical names and storage choices remain subject to current-main
inspection, accepted visual authority, privacy/authorization review, and an
activated package.

## 2. Conceptual records

The future architecture needs the equivalent responsibilities below without
creating a second résumé or Story store.

| Concept | Responsibility | Must not contain |
| --- | --- | --- |
| Overview draft | Current private composition and revision state for one owner/profile | Public authority, copied private source bodies |
| Block placement | Block type/version, semantic order, visibility, emphasis, bounded projection fields | Arbitrary HTML/CSS/coordinates |
| Source reference | Exact eligible canonical/projection record and reviewed version for record-linked/hybrid content | Duplicated authoritative fact or a hidden first-release proof-metric source relation |
| Authored proof metric | Member-supplied exact value, short accepted label, optional validated destination, and normal draft/publication lifecycle | Canonical-fact status, source/evidence/provenance relation, verification claim, or AI-derived value |
| Destination reference | Stable typed route/section/public record target | Unvalidated arbitrary owner ID or private URL |
| Media reference | Eligible media ID/version, focal data, alt/decorative state, consent/provenance | Duplicated raw media bytes |
| AI proposal | Proposed change, sources, model/program provenance, decision state | Canonical fact or publication authority |
| Publication revision | Exact pinned visitor result inputs and audience at publish time | Mutable pointer to whatever is latest |
| Style manifest | Versioned rendering/compatibility rules for one style | Member content or Pete fixture values |
| Block definition | Versioned content, validation, accessibility, and renderer contract | A new truth store |

One member/profile has at most one current public Overview in the first release,
plus private draft and version history according to retention policy.

## 3. Truth relationships

```text
eligible canonical/public records
            ↓ exact authorized references
private Overview draft + member projection wording
            ← member-supplied proof values (no first-release source relation)
            ↓ validation and exact visitor preview
explicit atomic publication revision
            ↓ audience-authorized public representation
one Overview above the actual résumé
```

Style switching changes the draft's presentation selection and bounded
style-specific presentation metadata. It does not fork content records.

## 4. Server responsibilities

The server must:

- derive the authenticated owner and target profile;
- authorize before returning draft/source/media/version data;
- return only eligible source choices;
- validate source versions, audience, destinations, media, block definitions,
  style compatibility, and authored proof-metric field rules without requiring
  metric provenance;
- prevent cross-member references;
- save drafts with revision/concurrency protection;
- store AI proposals separately from accepted draft state;
- generate the same public representation used by exact visitor preview;
- publish all selected state atomically;
- serve only the current authorized published projection to visitors;
- fail closed on deletion, revocation, or audience narrowing;
- distinguish benign source evolution from corrective supersession and remove a
  known invalid public claim without silently publishing replacement wording;
- support restore as a new reviewed publication revision;
- support owner-controlled atomic unpublish with Summary fallback, retained
  history, concurrency protection, and failure recovery;
- provide audit/observability without logging private bodies or sensitive media;
  and
- preserve useful manual behavior when AI is unavailable.

The client must not be trusted to declare ownership, public eligibility,
publication state, or valid rendered HTML.

## 5. Deterministic rendering pipeline

A future renderer should conceptually:

1. load an authorized publication or owner draft;
2. resolve its pinned style and block-definition versions;
3. resolve eligible public source projections without leaking ineligible data;
4. validate each block and destination;
5. omit invalid/empty/hidden blocks according to the fail-closed contract;
6. select declared zero/one/many and responsive treatments;
7. emit one semantic order;
8. add actions only for valid destinations;
9. emit no owner-only metadata in public output; and
10. produce a stable result suitable for exact preview and caching.

Count-aware layout is a renderer responsibility, not a set of Pete-specific
template branches.

For the current `/petec/resume` fixture, the renderer has one opening slot:
published Overview or existing Summary fallback. It never emits both. The
public-integration slice replaces the current right ribbon with the approved
left Context Rail. Its first entry follows the actual opening state. The right
region is contextual AI, not duplicate section navigation.

## 6. Style and block version compatibility

- New draft work uses a currently supported style/block definition.
- A publication pins the definitions it was previewed with.
- A later definition release does not unexpectedly rearrange existing public
  content.
- Central security, privacy, authorization, accessibility, or truth corrections
  may supersede an old renderer when necessary; the release record must explain
  the change.
- A deprecated definition must have an explicit preview/migration path, not a
  silent public conversion.
- Switching styles shows any incompatible/hidden content and requires a member
  decision before publication.

## 7. Recommended delivery sequence

### Gate 0 — approved inventory and exact visual authority

- Pete approved the page-purpose inventory and six first-release decisions on
  2026-07-26.
- Pete approved the public style, sparse/narrow/mobile, editor,
  consolidated-rail/public-AI, and Review & Publish directions registered in
  `10_VISUAL_AUTHORITY_LOCK_2026-07-26.md`.
- Pete explicitly approved the corrected mobile proof-point editor on
  2026-07-26. Its durable file, dimensions, and SHA-256 are hash-locked in
  `10_VISUAL_AUTHORITY_LOCK_2026-07-26.md`.
- The product/logical architecture is complete in
  `11_FINAL_ARCHITECTURE_CONTRACT_2026-07-26.md`.
- The implementation package names writable/forbidden files, routes,
  authorization, data, migrations, rollback, evidence, and homepage parity.

### Slice 1 — projection/read model and generic renderer fixtures

- Define the minimal source-eligibility and projection contracts.
- Define the authored proof-metric contract without source, evidence,
  verification, or provenance-state plumbing.
- Define versioned block/style manifests.
- Prove sparse, standard, rich, no-media, one-degree, one-role, and generic
  multi-member rendering without a public mutation path.
- Preserve current public résumé behavior.

### Slice 2 — manual private composer

- Add authenticated owner-only draft editing.
- Implement record selection, bounded authored fields, order, visibility,
  emphasis, destinations, media metadata, validation, autosave, and exact
  preview.
- Let members manually enter, edit, hide, reorder, and remove exact metric
  values and labels.
- The manual path is complete before AI is required.

### Slice 3 — exact preview, publication, and restore

- Add atomic publish, prior-publication stability, version history, restore,
  unpublish, benign-source review, corrective-supersession propagation,
  revocation fail-closed behavior, and the exact public projection.

### Slice 4 — public résumé integration and Context Rail migration

- Integrate the published projection above the actual résumé behind the exact
  approved release boundary.
  Pete's acceptance fixture remains `/petec/resume`; reusable routing and
  authorization must be member-derived and preserve current canonical,
  redirect, and download behavior.
- Replace/absorb the current Summary only when an Overview is published;
  preserve Summary as the no-publication/unpublish fallback, replace the
  current right ribbon with the final left local-section Context Rail, use
  Connect and View résumé in the hero, place Résumé PDF once in the left rail,
  and preserve public Ask [Name] AI once in the right contextual rail.
- Prove the AI rail becomes a drawer/sheet/action before the center becomes
  materially cramped.

### Slice 5 — optional Overview AI proposals

- Add scoped, authorized proposal actions inside the working composer and
  private Ask Slate AI context.
- Prove proposal provenance where applicable, accept/edit/reject, failure
  fallback, no canonical mutation, and no publication authority.
- For metrics, accept only an exact value explicitly supplied by the member,
  treat it as immutable during AI label editing, and prove AI cannot invent,
  retrieve, infer, calculate, round, embellish, change, or silently substitute
  a value.
- AI can follow the manual release if separating it reduces risk; the product
  remains complete without it.

### Slice 6 — enablement and public parity

- Complete independent review and Pete/designated-manager acceptance.
- Complete homepage product-projection parity or an exact authorized downstream
  parity package if the homepage presents the résumé/Slate capability.
- Release through Azure, verify the exact pipeline and live member/public
  boundaries, and keep a rollback/disable path.

### Separate cross-product AI-rail adoption

Workshop, Slate Board, Interview Studio, Community, Story, Journal, and other
rooms are outside this package. A future shared component or room adoption
requires its own page-purpose decision, permitted-context contract, visual
authority, activated files, tests, and acceptance.

Slices are planning units, not activated packages. A later owner decision may
combine or subdivide them after current-code inspection.

## 8. Required generic fixtures

Pete may remain an acceptance example, but reusable behavior needs at least:

1. early-career member: one role, one degree, no metrics, no awards, no images;
2. career changer: multiple roles, transferable skills, authored future
   direction, no public Story;
3. experienced leader: four member-authored proof metrics, four roles, impacts,
   credentials, multiple eligible images;
4. independent/creative professional: projects/skills/story emphasis with no
   conventional corporate metrics;
5. privacy-restricted member: some selected sources/media later become private;
6. no-Overview member: current résumé begins directly; and
7. withdrawn-Overview member: prior history exists but current Summary is the
   public opening;
8. corrected-source member: one previously published claim is marked invalid
   and fails closed without auto-publishing corrected wording; and
9. two separate owners: cross-member IDs and sources are rejected before
   retrieval.

No reusable test should require Pete's employers, dates, degrees, metrics, or
images.

## 9. Functional acceptance matrix

| Area | Minimum acceptance |
| --- | --- |
| Manual creation | Member completes, previews, and publishes without AI |
| AI creation | Proposal uses eligible sources where applicable, is reviewable, and never saves/publishes itself |
| Manual proof metrics | Member enters/edits/removes exact values and labels with no source/provenance requirement |
| AI proof-metric value lock | AI can preserve an explicitly member-supplied value and edit its label but cannot generate, retrieve, infer, calculate, round, embellish, alter, or substitute the value |
| Metric data boundary | Public/draft metric contract contains no source, evidence, verification, or provenance-state field in the first release |
| Style switch | No content loss; draft only until publish; prior public revision unchanged |
| Sparse content | Deliberate result with no gaps or public setup prompts |
| Rich content | Readable, bounded, non-repetitive result; eight major bands maximum, excluding hero and proof band |
| Missing media | Text-led reflow, no broken/stock placeholder |
| One proof item | Feature treatment; no forced second claim |
| One role | Career Focus; no fake timeline |
| One degree | Honest compact Education; no filler |
| Missing credentials | Groups/band reflow or disappear |
| Deep links | Real stable anchors, correct disclosure, URL, focus, sticky offset, reduced motion |
| Source edit | Owner review required before new publication wording |
| Source deletion/privacy | Public item/action fails closed without leak or gap |
| Draft save failure | Public revision unchanged; recoverable retry state |
| Publish failure | No partial publication; prior revision stays active |
| Concurrency | Stale draft cannot overwrite newer work |
| Restore | Previewed prior content is revalidated and republished as a new revision |
| Unpublish | Explicit, authorized, concurrency-checked withdrawal restores Summary atomically and preserves history |
| Unpublish failure | Current Overview remains active; no partial fallback or cache split |
| Benign source evolution | Existing still-valid claim stays pinned; draft requires review for new source version |
| Corrective supersession | Known invalid claim/block fails closed immediately; no corrected wording auto-publishes |
| Summary integration | Published Overview and current Summary never render as two openings; Summary returns when Overview is absent |
| Contextual navigation | Final left rail contains only local résumé depth, first entry is Overview or Summary according to the actual opening, hidden sections have no entry, and route-level navigation is not duplicated |
| Contextual AI | Right rail is public Ask [Name] AI over public context or private Ask Slate AI over authorized owner context; it never becomes duplicate navigation |
| Wide-desktop canvas | Overview root aligns to the resolved résumé content-column edges; no undocumented nested page stage |
| Wide-desktop text measure | Bands/media/grids use the canvas while representative body copy retains the Pete-locked readable measure |
| Approved actions | Connect and View résumé appear in the hero; Résumé PDF appears once in the left rail; Ask [Name] AI/Ask Slate AI appears once in the right context without duplication |
| Public response | No drafts, private sources, edit metadata, or AI proposal state |
| Cross-member isolation | Owner A cannot retrieve/reference/publish Owner B data |
| No JavaScript | Public meaning and real destinations remain usable |

## 10. Visual and accessibility acceptance

For both styles, compare the real implementation with the exact locked
authority at:

- full-browser 1440 × 900, 1920 × 1080, 2560 × 1440, and 3840 × 2160
  CSS-pixel desktop;
- at least 390 × 844 mobile;
- intermediate reflow widths;
- 200% zoom/large text;
- keyboard-only navigation and editing;
- visible focus and same-page destination arrival;
- screen-reader landmarks, headings, labels, state announcements, and semantic
  order;
- reduced motion;
- text-only/missing-media;
- sparse and maximum-content states;
- validation, save, AI, preview, publish, conflict, and failure states; and
- unpublish and Summary-fallback states;
- current-right-ribbon replacement by the final left Context Rail;
- public Ask [Name] AI versus private Ask Slate AI rail/drawer/mobile-action
  behavior and grounding;
- corrective-source block omission and whole-Overview fallback;
- both generic and Pete acceptance profiles.

For each desktop frame, record `window.innerWidth`, `window.innerHeight`,
device-pixel ratio, browser zoom, and the computed rectangles for the shared
shell, resolved résumé content column, external contextual control, and
Overview root.

The future browser acceptance test must:

1. compare the Overview root and resolved content-column inline edges using
   `getBoundingClientRect()` and allow no more than two CSS pixels of expected
   layout rounding;
2. detect an undocumented descendant acting as a second page-level
   `max-width`;
3. record outer gutters and compare them with the exact Pete-locked visual;
4. confirm computed CSS `zoom: 1` and `transform: none` on the future Overview
   fitting chain at 100-percent browser zoom;
5. confirm primary body copy is at least 16 CSS pixels and measure
   representative line length separately from canvas occupancy;
6. test sparse, standard, rich, missing-media, and missing-optional-section
   states at wide desktop;
7. fail on horizontal overflow, clipping, or two-dimensional scrolling; and
8. repeat reflow checks at 200 percent zoom and supported intermediate/mobile
   widths.

Pete approved the first ChatGPT visual candidate starting with the Studio-aligned
`min(92vw, 90rem)` shell at normal scale. The current zoomed résumé geometry is
reference evidence, not automatic acceptance of the future shared shell. The
older `PS-SHELL-001` 1120–1200-pixel estimate does not narrow or block Overview
visual creation. Complete 2560- and 3840-pixel frames may lead Pete to adjust
the exact stage. Implementation may match only the resulting exact Pete-locked
Overview authority reconciled with the shared shell.

WCAG 2.2 AA is the minimum target. Automated checks supplement but do not
replace keyboard, reading-order, responsive, content, and owner visual review.

## 11. Security, privacy, and AI review

A fresh independent reviewer is mandatory because the future implementation
touches:

- owner authorization and cross-member data;
- public audience/publication;
- deletion/revocation behavior;
- private media/source relationships; and
- consequential AI proposals that affect public professional claims.

The reviewer receives the exact package, branch, SHA, complete diff, migrations,
tests, visual evidence, failure evidence, and production boundary. Findings are
Pass, Conditional, or Fail. The same writer corrects accepted findings and
refreshes affected evidence.

## 12. Pre-merge and release evidence

An activated writer must provide:

- exact current Azure base and final source SHA;
- complete-diff self-review;
- focused block/style/editor/publication/AI tests;
- explicit first-release proof-metric tests with no source/provenance plumbing
  and with immutable member-supplied values in AI label proposals;
- full configured repository suite;
- migration and rollback evidence when storage changes;
- authorization-before-retrieval and two-owner isolation evidence;
- source revocation/deletion/audience evidence;
- benign-versus-corrective source-change evidence;
- publish/unpublish/restore concurrency and cache evidence;
- Summary absorption/fallback, first-section-entry, existing `#summary` and
  `#resume-overview` compatibility aliases, left Context Rail, public Ask
  [Name] AI, private Ask Slate AI, PDF, and current-route compatibility
  evidence;
- responsive/accessibility/visual comparison set;
- captured wide-desktop shell/content/Overview geometry at
  1440/1920/2560/3840 CSS-pixel viewports;
- exact Pete-locked Overview/shared-shell width reconciliation before runtime;
- homepage parity assessment/evidence;
- independent-review result and corrections;
- Pete's corrected-real-build visual acceptance;
- Azure PR squash merge and exact pipeline;
- production route/public/owner verification; and
- honest implemented, default-off, enabled, deferred, and unavailable labels.

## 13. Stop conditions

Stop rather than improvise if an implementation would:

- start before the exact visual/state set is Pete-locked;
- duplicate résumé, Story, Journal, Project, or media truth;
- use client filtering as a privacy boundary;
- permit arbitrary layout or unreviewed custom HTML;
- publish an AI proposal or source change silently;
- add metric source-backing/provenance or permit AI-derived proof values without
  a new owner-approved enhancement package;
- expose private Journal/Goal/source content;
- implement only Pete's rich profile without sparse/generic fixtures;
- create a dead destination or public empty slot;
- preserve a concept-image or stale shared-shell width that conflicts with the
  exact wide-desktop visual lock;
- change shared navigation, homepage, or résumé behavior outside the activated
  package;
- adopt the contextual AI rail in another Slate/Studio room without that
  room's own activated package and permitted-context contract;
- add a schema, migration, service, flag, or provider without documented need
  and authority; or
- describe fixture/default-off/planned behavior as live.
