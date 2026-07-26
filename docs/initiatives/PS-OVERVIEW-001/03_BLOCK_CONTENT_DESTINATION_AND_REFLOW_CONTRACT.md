# Block, content, destination, and reflow contract

## 1. Structured composer rule

The Overview is composed from a finite block library. A member chooses the
content and sequence; the selected style manifest computes the presentation.

Every supported block has:

- one content contract;
- allowed source relationships;
- allowed emphasis variants;
- empty, one-item, and many-item behavior;
- a destination contract;
- a media contract where applicable;
- public and owner-only states;
- Story & Career and Work & Impact render treatments;
- responsive and accessibility behavior; and
- a versioned definition.

No block accepts arbitrary HTML, CSS, JavaScript, columns, widths, or pixel
coordinates.

## 2. Shared block record

The future architecture may use different names, but every placed block needs
the equivalent of:

| Field | Purpose |
| --- | --- |
| Stable block placement ID | Preserve order, revisions, and audit history |
| Block type and definition version | Select a finite content/render contract |
| Source mode | Record-linked, authored, or hybrid |
| Exact source/version references | Preserve provenance and review state |
| Authored/accepted projection fields | Store bounded member-owned presentation copy |
| Semantic order | Set the reading and keyboard order |
| Visibility | Draft-visible, hidden, or selected for publication |
| Emphasis | Feature, Standard, or Compact when the style permits it |
| Destination | Zero or one validated public continuation |
| Media references and focal data | Select eligible media without duplicating bytes |
| Style presentation overrides | Only approved focal/emphasis choices; never duplicate facts |
| Validation state | Ready, warning, or blocking reason |

The source record remains authoritative. Projection wording and layout metadata
have their own lifecycle and never overwrite it.

The optional first-release Proof Band is the deliberate exception to requiring
a source relationship. Its member-supplied value and accepted label are
authored Overview projection fields. It has no metric source, evidence,
verification, or provenance-state field. This exception does not weaken the
source contract for record-linked or hybrid blocks.

## 3. Finite block library

| Block | Source modes | Public fields | Initial visible budget | Count behavior |
| --- | --- | --- | --- | --- |
| Profile Hero | Record-linked + authored | Name, headline, intro, portrait, up to 3 contact items, up to 2 actions | Headline about 70 characters; intro 250–300 characters | One hero when Overview publishes; absorbs current Summary hero |
| Proof Band | Authored first-release metric projection | Member-supplied exact value, short member-authored/accepted label, optional icon and validated destination; no source/provenance field | 0–4 proof items; value about 12 characters; label about 30 | 0 omit; 1 feature; 2–4 equal/reflowing group |
| Story Spotlight | Hybrid over one eligible published Story projection | Eyebrow, title, grounded teaser, optional image, Story action | Summary 250–320 characters | 0 omit; 1 spotlight; unavailable without same-audience public Story |
| Career Arc | Record-linked + optional summary | 1–4 roles with organization/title/date and concise preview | 3 default, 4 maximum | 1 Career Focus; 2–4 arc/list |
| Impact Highlights | Hybrid | 1–4 outcome title/summary/icon and destinations | Title about 40; summary about 100 characters | 1 feature; 2–4 count-aware grid |
| Story Chapters | Record-linked to eligible public Story | 2–5 chapter labels and concise cues | 5 maximum | 0 omit; 1 folds into Story Spotlight; 2–5 list |
| Skills Preview | Record-linked | 4–10 selected skill labels, optional concise proof cue | 8 recommended | 1–3 compact; 4–10 standard; additional items stay below |
| Education Preview | Record-linked | 1–2 selected education records | 2 maximum | 0 omit; 1 compact/confident; 2 list |
| Certifications Preview | Record-linked | 1–3 selected certifications | 3 maximum | 0 omit; 1–3 list |
| Awards Preview | Record-linked | 1–3 selected awards | 3 maximum | 0 omit; 1–3 list |
| Quote / Principle | Authored | Quote and optional attribution/context | About 180 characters | 0 omit; 1 item |
| Flexible Spotlight | Any | Type label, member title, summary, optional 2–4 highlights, optional image, one action | Summary about 220–280 characters | 0–6 placed; 3–4 recommended |
| Philosophy / Future Banner | Authored or hybrid | Label, title, short statement, optional image/action | About 220 characters | 0 omit; 1 banner |
| Résumé Transition | System | “Résumé begins here” and semantic heading/landmark | Fixed system copy | Renders only when Overview precedes detailed Impact/Skills/Experience/Credentials |

The budgets are initial visual-design targets, not database field lengths. The
locked visual must validate them with the real type scale at desktop, mobile,
and large-text states before implementation values are finalized.

### Proof metric input and AI rule

- The member supplies the exact value by typing it in the metric field or by
  explicitly including it in the current AI request.
- AI may preserve that exact value while proposing or shortening the label.
- AI may not invent, retrieve from another record, infer, calculate, round,
  embellish, change, or silently substitute a value.
- A wording proposal treats existing numeric tokens as immutable. If the member
  wants a different value, the member must explicitly supply it.
- A metric has normal draft, preview, publish, version, hide, reorder, remove,
  and optional-destination behavior.
- The first release has no metric source selector, evidence attachment,
  verification badge, or provenance/readiness state.
- Source-backed metrics are a deferred enhancement requiring a separate product
  decision and migration treatment; they are not hidden future fields in this
  contract.

## 4. Flexible Spotlight types

The member selects a purpose so prompts and validation remain clear:

- Capability
- Leadership
- Outcome
- Specialty
- Values
- Person behind the work
- Future direction
- Custom professional spotlight

The visible title remains member-controlled. Example subjects such as Systems
Engineering, Sustainment & Lifecycle, or Data, Automation & AI are fixture
content, not hardcoded types.

A Custom professional spotlight uses the same bounded fields and renderers. It
does not create a new component definition.

## 5. Content budget behavior

### Editor feedback

Each field or collection reports:

- **Fits**
- **Approaching the recommended limit**
- **Additional items will stay in the résumé and a specific link will appear**
- **Too long / too many to publish**
- **Missing required source or destination**
- **Source changed — review required**
- **Corrective source supersession — public claim removed; replacement review
  required**
- **Source or media is not public for this audience**

The editor never blocks typing. It may block publication when the exact visitor
result would break a hard accepted limit, contain invalid/private material, or
misrepresent a source.

### What the system must not do

- shrink body text to make content fit;
- cut a sentence mid-word or mid-sentence;
- silently remove selected meaning;
- hide public content in an internal card scrollbar;
- rely on hover to reveal essential meaning;
- add an ellipsis with no destination;
- allow an unlimited number of feature blocks; or
- turn the Overview into a second complete résumé.

### Repetition feedback

The composer warns when:

- a proof item and Impact Highlight present the same claim;
- a hero intro and Executive Brief repeat the same wording;
- Career Arc summaries duplicate the full résumé descriptions;
- Story Spotlight, Story Chapters, Quote, and Philosophy repeat one theme
  without distinct purpose; or
- the same destination/action appears unnecessarily in adjacent blocks.

The member decides the final wording, but publication may be blocked when exact
duplicate blocks produce misleading or broken output.

## 6. Deterministic no-gap rules

1. **No valid public content means no wrapper.** Empty, hidden, invalid,
   unauthorized, unpublished, or unsupported blocks consume no public space.
   A claim invalidated by corrective source supersession also consumes no space
   and is never replaced with unreviewed corrected wording. Corrective-source
   behavior applies to record-linked content; a first-release authored metric
   changes only through member edit/publish or removal.
2. **No fixed public card heights.** Cards grow with accepted content and use
   style-owned minimum spacing only.
3. **No masonry.** DOM, reading, keyboard, and default visual order remain the
   same.
4. **No column balancing by padding.** A shorter column ends naturally; the
   system never inserts blank filler to match a neighbor.
5. **Missing media changes the treatment.** Text expands into an approved
   text-led variant; no empty image box or generic replacement photo appears.
6. **Counts select a declared arrangement.** One, two, three, and four items use
   explicit style rules instead of leaving orphan cells.
7. **Sparse groups remain semantically honest.** One degree is Education, not
   relabeled as generic Credentials merely to fill a box.
8. **Adjacent credential groups may share a visual band.** Their headings and
   records remain distinct; missing siblings consume no columns.
9. **Mobile is recomposed.** It becomes one meaningful reading flow rather than
   a shrunken desktop grid.
10. **Overview absent means résumé first.** There is no public setup card or
    empty Overview landmark.
11. **The outer canvas does not shrink with content count.** The Overview root
    remains 100 percent of the resolved résumé content column in sparse,
    standard, and rich states. Missing blocks collapse inside that canvas
    rather than causing a narrow nested page.

## 7. Count-aware state matrix

| Content condition | Public result |
| --- | --- |
| No portrait | Text-led hero; identity and actions use the available width |
| No hero action | Hero remains static; no empty button area |
| No proof items | Proof band omitted |
| One proof item | Featured proof integrated with or immediately after hero |
| Two proof items | Balanced pair |
| Three proof items | Three-item group at wide width; readable stack/reflow when narrow |
| Four proof items | Four-item group at wide width; 2×2 or stack when required |
| No public Story | All Story blocks omitted; no Story action |
| One Story chapter | Fold into Story Spotlight or omit chapter list |
| Standalone authored career/personal narrative | Use a Flexible Spotlight with a truthful member title; do not label it Story or link to Story without a same-audience published Story |
| No roles | Career block omitted; Overview may still use other truthful content |
| One role | Career Focus treatment, not a fake timeline |
| Two to four roles | Concise Career Arc in semantic chronological or member-approved order |
| No impact items | Impact block omitted |
| One impact item | Wide/feature treatment |
| Two to four impacts | Count-aware grid or list |
| One to three skills | Compact Skills treatment |
| Four to ten skills | Standard preview |
| More eligible skills than shown | Selected first items plus `View all N skills` when target exists |
| One education record | Confident compact Education preview |
| No education | Education omitted without affecting other credentials |
| No certification or awards | Missing groups omitted; remaining groups expand/reflow |
| No credential groups | Entire credentials band omitted |
| No images anywhere | Approved text-led composition with system-owned decoration only |
| One spotlight | Feature or full-width standard treatment |
| Consecutive text-only spotlights | Approved balanced row/list at wide width; normal semantic stack when narrow |
| Member hides every Overview block | No public Overview; résumé begins as it does today |

## 8. Outcome tile arrangement

When a Flexible Spotlight contains a group of related outcome tiles, the
renderer chooses a complete arrangement with no one-item orphan row.

| Tile count | Preferred wide arrangement |
| --- | --- |
| 2 | 2 |
| 3 | 3 |
| 4 | 4 or 2 + 2 |
| 5 | 3 + 2 |
| 6 | 3 + 3 |
| 7 | 4 + 3 |
| 8 | 4 + 4 |

At narrower widths, the style may use two columns and then one. The semantic
order never changes.

## 9. Destination contract

Every actionable block declares zero or one primary destination. Individual
proof/outcome items may have their own supporting destinations only when the
locked visual makes those distinct actions understandable.

### Allowed examples

- **View full experience**
- **See the experience behind this result**
- **View all 12 skills**
- **View education**
- **View 4 more awards**
- **Read my full story**
- **View this project**
- **Contact me**

### Requirements

- The destination exists and is authorized for the same viewer.
- The action label describes the destination; `More` is prohibited.
- Résumé section targets use stable anchors such as Experience, Skills,
  Education, Certifications, and Awards.
- A real anchor remains useful for keyboard, middle-click, copied URLs, and
  basic no-JavaScript behavior.
- Same-page activation accounts for sticky navigation and moves keyboard focus
  to the destination heading when appropriate.
- The URL reflects the destination.
- Reduced-motion preference produces an instant change rather than smooth
  scrolling.
- A collapsed résumé disclosure opens before focus is placed.
- When additional content does not exist, the count-specific link does not
  render.
- When a destination is hidden, removed, revoked, or private, the action fails
  closed and the block becomes honestly static or is removed according to its
  contract.

The whole card may share a visible action only when it has exactly the same
destination and accessible name. A visually clickable card with no destination
is prohibited.

## 10. Responsive and typography rules

- DOM order is the one semantic source of order.
- The Overview root uses the full inline size of the resolved résumé
  center-content column. It does not inherit the source images' 941- or
  864-pixel raster widths and does not add another arbitrary page-level
  `max-width`.
- Wide composition uses the available canvas through declared bands, media,
  rules, whitespace, and count-aware columns. It does not merely lengthen every
  line of text.
- Representative body copy initially targets approximately 55–70 characters
  per line, subject to validation against the locked typography and language.
  Primary body copy is at least 16 CSS pixels at normal scale. That inner
  measure never narrows the Overview root.
- The future Overview uses normal CSS scale. `zoom` or `transform` scaling may
  not be used to fit a desktop composition into the accepted shell.
- Internal band and grid changes respond to the available center container,
  not assumptions about the monitor's physical diagonal.
- Wide-screen columns collapse to the same semantic order on mobile and large
  text.
- Normal reading never requires two-dimensional scrolling at 200% zoom.
- Body text does not become smaller merely because the Overview is dense.
- All controls and public actions have visible keyboard focus.
- Text and controls meet WCAG 2.2 AA contrast in both approved style
  treatments.
- Touch targets meet the accepted minimum size and spacing.
- Essential content and navigation do not depend on animation.
- Media uses constrained aspect-ratio families and member-set focal points;
  crops cannot hide the described subject at supported breakpoints.
- The exact visual gate must include at least desktop, mobile, 200% zoom or
  equivalent large-text, keyboard/focus, reduced-motion, missing-media,
  sparse-content, and maximum-content states for both styles.
- Full-browser desktop evidence includes 1440 × 900, 1920 × 1080,
  2560 × 1440, and 3840 × 2160 CSS-pixel viewports. Physical monitor inches
  are context only.
