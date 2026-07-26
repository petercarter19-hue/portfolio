# Style manifests and visual gate

## 1. Status

Story & Career and Work & Impact are approved product directions for one
Overview system. Their supplied images are not exact production-intent visual
authority.

This record defines what a future ChatGPT visual-creation session must preserve
and what Pete must lock before implementation.

## 2. Shared style-manifest contract

Each versioned style manifest must declare:

- supported block types;
- default semantic order;
- allowed emphasis variants per block;
- wide, medium, mobile, and large-text arrangements;
- zero/one/many rules;
- media aspect-ratio and focal treatments;
- typography and spacing tokens;
- maximum recommended public density;
- destination/action presentation;
- owner-edit overlay/structured-editor relationship;
- required empty, loading, invalid, failure, and unavailable states; and
- compatibility behavior for an older published revision when the manifest
  changes.

The manifest is presentation authority. It contains no Pete-specific employers,
titles, degrees, skills, awards, metrics, family details, or block counts.

## 3. Shared content, style-specific presentation

| Shared content decision | Story & Career treatment | Work & Impact treatment |
| --- | --- | --- |
| Identity, headline, intro, portrait | Editorial, image-capable hero with generous narrative space | Work-first hero with concise brief and optional professional media |
| Proof items | Side proof stack or integrated proof band, count-aware | Horizontal or immediate proof band, count-aware |
| Roles | Career Arc with selected narrative continuity | Career Snapshot/Focus optimized for quick scope scan |
| Impacts | Key Impact highlights | Outcomes and managed-scope evidence |
| Skills | Technical Strengths/Skills preview | Skills preview before credential groups |
| Education, certifications, awards | Balanced credential band | Compact supporting groups in the center canvas |
| Story | Spotlight, chapters, quote, philosophy as optional distinct blocks | Usually one bounded person/story block when selected |
| Flexible Spotlights | Narrative/career/personal/future features | Capability, leadership, specialty, outcome, personal, or future features |
| Media | More editorial and personal when eligible | More restrained, work/context oriented when eligible |
| Résumé transition | Clear boundary | Clear boundary |

Both styles must support a valid text-only profile and every shared factual
block. A style may recommend a different block order, but it may not silently
discard selected content.

A Story Spotlight in either style requires an eligible same-audience published
Story projection. Standalone authored career origin or personal context uses a
Flexible Spotlight and cannot imply a Story destination.

## 4. Story & Career manifest

### Purpose

Create the strongest combined résumé-and-portfolio orientation: professional
credibility first, then selected human context and career narrative.

### Recommended default sequence

1. Profile Hero
2. Proof Band when present
3. Story Spotlight or Career Arc
4. Career Arc or Story Spotlight
5. Impact Highlights
6. Skills Preview
7. Optional Story Chapters, Quote, or one Flexible Spotlight
8. Education / Certifications / Awards
9. Optional Philosophy or Future Banner
10. Résumé Transition

The member may reorder optional blocks, but the visual must still preserve one
clear opening and a concise path into the résumé.

### Visual characteristics to preserve from the direction input

- editorial Deep Navy Gold character;
- strong portrait/identity opening without making portrait required;
- generous but bounded Story imagery;
- clear career timeline/arc when multiple roles exist;
- strong professional proof alongside human narrative;
- distinct but not excessive chapters/values/philosophy;
- readable typography at the real public scale; and
- intentional closing transition into the résumé.

### Corrections the production concept must make

- remove concept top navigation/footer as Overview content;
- remove the duplicate Full Résumé block;
- compose against the current right-side section ribbon outside the center
  canvas; do not depict the future left Context Rail as active without its
  separate migration authority;
- enlarge body text and reduce content instead of shrinking type;
- show sparse and text-only variants;
- avoid requiring multiple personal/family images;
- prevent Story Spotlight, chapters, quote, and philosophy from repeating one
  idea;
- show the member editor without turning the public page into a design canvas;
- absorb the current résumé Summary instead of creating a second portrait/name/
  intro opening; and
- preserve one truthful public Ask [Name] AI placement outside duplicated hero
  actions.

## 5. Work & Impact manifest

### Purpose

Give a visitor a rapid, evidence-led understanding of the member's professional
value, scope, capabilities, and supporting record.

### Recommended default sequence

1. Profile Hero / Executive Brief
2. Proof Band when present
3. Career Snapshot or Career Focus
4. Capability and Impact Spotlights
5. Skills Preview
6. Education / Certifications / Awards
7. Optional Person Behind the Work or Future Direction
8. Résumé Transition

### Visual characteristics to preserve from the direction input

- strong work-first headline and concise bottom-line statement;
- immediate proof with clear labels;
- disciplined alternating capability/evidence rhythm;
- strong professional imagery when authentic eligible media exists;
- scannable supporting records;
- compact but readable density; and
- a decisive transition into the résumé.

### Corrections the production concept must make

- treat the apparent left column as center-canvas content, not the site rail;
- compose against the current right-side section ribbon outside the center
  canvas; do not depict the future left Context Rail as active without its
  separate migration authority;
- place Skills before Education, Certifications, and Awards;
- remove the duplicate Full Résumé summary;
- replace hardcoded discipline names with member-defined bounded Spotlights;
- remove any assumption that education, certifications, awards, metrics, or
  images exist;
- provide one-degree, one-role, one-proof, no-media, and no-credential states;
- use authentic/clearly labeled media rules;
- preserve readable type instead of fitting the entire rich example at once;
- absorb the current résumé Summary and preserve Ask [Name] AI/PDF capability
  without repeating actions.

## 6. Style switching

The draft style selector must show:

- both styles using the member's real current draft;
- desktop and mobile previews;
- content retained;
- content repositioned;
- blocks unsupported by an older manifest version;
- media needing a new focal point;
- content too long for a treatment; and
- destinations or sources needing review.

Example summary:

> 8 blocks retained · 3 repositioned · 1 image needs a focal point · 1 summary
> needs shortening

Switching styles:

- changes only the private draft;
- never deletes authored or record-linked content;
- preserves style-specific focal/emphasis settings for later return;
- cannot silently hide a selected block;
- does not affect the public page until explicit whole-Overview publication;
  and
- leaves the prior public revision restorable.

## 7. Sparse, standard, and rich arrangements

These are renderer states inside each chosen style, not separate user-facing
templates:

| State | Typical content | Requirement |
| --- | --- | --- |
| Sparse | Hero plus one or two meaningful blocks; optional one proof | Deliberate text-led composition, no setup prompt, no fake empty slots |
| Standard | Hero, optional proof, three to five content bands | Recommended public density |
| Rich | Hero, proof, six to eight distinct bands | Must remain readable and non-repetitive; visual review required |

The system may warn that the content is too sparse or rich for a selected
emphasis combination. It must not silently switch the member to the other
style.

## 8. Wide-desktop geometry gate

The supplied direction images are portrait editorial boards, not
browser-shaped desktop authorities. Before Pete can lock either style, the
visual set must prove its outer silhouette in the actual shared-shell and
résumé-content relationship.

For each style, provide annotated full-browser standard-state frames at:

- 1440 × 900 CSS pixels;
- 1920 × 1080 CSS pixels;
- 2560 × 1440 CSS pixels; and
- 3840 × 2160 CSS pixels.

The first visual candidate uses a centered `min(92vw, 90rem)` shell at
100-percent browser zoom, with computed CSS `zoom: 1` and `transform: none`.
This is the Studio-aligned working target for Pete to scrutinize, not a
pre-claimed final lock.

Record the CSS viewport, device-pixel ratio, browser zoom, shell width,
Overview content-column width, external contextual-control width, column gap,
outer gutters, and representative body-copy measure. Physical monitor inches
are evidence context only.

The visual candidate must:

- make the Overview root use the full resolved résumé center-content column;
- use the wide canvas through declared media, bands, proof grouping, rules,
  whitespace, and columns while bounding readable text measure inside blocks;
- show a sparse wide state that does not collapse into one narrow centered
  card;
- preserve the external contextual control outside the Overview canvas;
- show the real résumé boundary beneath the Overview; and
- avoid horizontal overflow, clipped content, stretched billboard-length body
  copy, and filler blocks; and
- keep primary body copy at least 16 CSS pixels at normal scale and use an
  approximately 55–70-character readable measure.

At 2560 and 3840 CSS pixels, a capped stage with intentional margins may be the
correct result, but it must be shown full-frame and explicitly accepted by
Pete. Neither the concepts' 941/864-pixel widths nor the planned
`PS-SHELL-001` 1120–1200-pixel estimate is automatically binding. The final
Overview width and shared-shell width must be reconciled before visual lock;
one package may not silently clamp the other.

See `08_WIDE_DESKTOP_WIDTH_AMENDMENT.md` for current-shell reference
measurements and the durable edge-alignment invariant.

## 9. Required production-intent visual set

ChatGPT must create durable, package-copied visual authority candidates for
both styles. At minimum:

### Public visitor

- desktop standard, sparse, and rich;
- the annotated full-browser wide-desktop set in Section 8;
- 390-pixel-class mobile standard and sparse;
- text-only/no portrait/no feature media;
- one proof item and no proof items;
- one role and multiple roles;
- one degree with no other credentials;
- missing Story;
- maximum accepted content;
- long unbroken/user edge text;
- 200% zoom or equivalent large-text reflow;
- visible keyboard focus and same-page destination arrival;
- reduced-motion behavior; and
- unavailable media/destination/source fail-closed state where visible.

### Owner editor

- initial choice: build from résumé, build manually, or AI proposal;
- block catalog and record selection;
- field/item limit feedback;
- reorder with keyboard-equivalent controls;
- media focal/alt/consent state;
- source changed/private source/missing destination blockers;
- AI source comparison and accept/edit/reject;
- exact visitor preview with editing furniture absent;
- at least one 1920- or 2560-pixel-wide owner-editor/visitor-preview pair that
  preserves the same published canvas geometry;
- style-switch change summary;
- draft saving/saved/failed;
- publish confirmation/success/failure/conflict;
- unpublish confirmation/pending/success/failure with the existing Summary
  fallback shown exactly;
- corrective-source omission and whole-Overview fail-closed fallback; and
- restore prior publication.

### Shared page context

- the current right-side ribbon outside the center canvas and its separately
  gated target left Context Rail relationship;
- one dynamic first entry: Overview when published, Summary for fallback;
- existing Summary absorbed when Overview is published and restored after
  unpublish;
- one clear nonduplicative Ask [Name] AI and Résumé PDF treatment;
- existing shared shell;
- Overview above the real résumé;
- **Résumé begins here** boundary;
- no duplicate Full Résumé summary; and
- mobile navigation treatment consistent with the approved site shell.

## 10. Visual lock checklist

- [ ] Pete approves
  `02_PAGE_PURPOSE_AND_NON_REDUNDANCY_INVENTORY.md`.
- [ ] ChatGPT creates both complete visual/state sets.
- [ ] Every meaningful visible item maps to an approved inventory row.
- [ ] Story & Career remains the flagship/default recommendation.
- [ ] Work & Impact remains a style over the same content system.
- [ ] The concepts' repeated résumé/nav/footer are removed.
- [ ] Sparse and rich generic profiles look intentional.
- [ ] Full-browser 1440/1920/2560/3840 CSS-pixel frames prove the selected
  stage, content-column, rail, gutter, and text-measure relationships.
- [ ] The selected Overview is shown at normal scale without CSS `zoom` or
  transform fitting.
- [ ] The selected width is reconciled with `PS-SHELL-001`; neither package
  silently narrows the other.
- [ ] Desktop/mobile/large-text/focus/reduced-motion states pass owner scrutiny.
- [ ] Editing and visitor preview truth are visually explicit.
- [ ] Pete locks exact durable files and SHA-256 hashes.
- [ ] A separate implementation-information package names the locked files,
  authorized scope, writer, tests, and release boundary.

## 11. Owner decisions before visual lock

Pete should settle these during inventory/visual review:

1. **Audience:** Inherit the public résumé audience for the first release
   (recommended), or design an independent Overview audience now.
2. **Member-confirmed metrics:** Permit publish with clear owner-visible
   provenance, or require an eligible canonical supporting source.
3. **Public maximum:** Confirm approximately eight bands as the rich upper
   bound, with four to six recommended.
4. **Style naming:** Confirm Story & Career and Work & Impact as the
   member-facing editor labels.
5. **Hero action:** Decide whether résumé download/contact primarily belongs to
   the shared shell, the hero, or one of each only when their jobs differ.
6. **Wide stage:** After reviewing the annotated 2560- and 3840-pixel frames,
   lock the exact shared-shell/Overview width, outer gutters, and contextual
   control relationship and reconcile the older `PS-SHELL-001` estimate.

These decisions do not block merging this requirements package. They block the
exact visual lock and publication architecture.
