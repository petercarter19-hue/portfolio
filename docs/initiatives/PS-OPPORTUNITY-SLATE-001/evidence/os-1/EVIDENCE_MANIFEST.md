# PS-OPPSLATE-001 slice OS-1 — committed visual evidence

Recaptured 2026-08-03 on branch `work/2026-08-02-opportunity-slate-os1`, after
the **third** owner visual-parity round recorded in
[`OWNER_VISUAL_REVIEW_2026-08-03.md`](../../OWNER_VISUAL_REVIEW_2026-08-03.md).
It replaces the two earlier same-day sets in full. Only the newest set is
evidence; the others are superseded.

The third round resolved the two gaps the second round had named honestly in
its own report, and gave the phone frames the critical read they had not had:

1. **Workbench proportion.** The locked set uses two different proportions —
   image 01 holds 53.2% of the frame, image 02 holds 64.6% — because one screen
   is an intake form and the other is a reading document. The second round
   split the difference at ~57% on both and matched neither. Each screen now
   carries its own. See `compare-01-*` and `compare-02-*`.
2. **The quiet margin below the concern card.** Fixed as composition (the
   reading measure, the card and the gap are now image 02's own ratios rather
   than a fixed 32rem) and as content (the empty state says what the *member*
   should check, in the present tense, inventing no future PeerSlate
   capability). See `detail-concern-card-in-margin.png`.
3. **The phone frames.** Paste box, import tiles, concern-card placement and
   duplicated actions all corrected. See `compare-04-*`, `compare-05-*`,
   `detail-import-row-phone-390.png`,
   `detail-concern-card-stacked-phone-390.png`.

## Capture conditions

| | |
|---|---|
| Harness | Headless Chromium via Playwright, driven from the repository `venv` |
| Server | The real Flask app served from this worktree, anonymous mode on `127.0.0.1:5411` and signed-in mode on `127.0.0.1:5412` |
| Identity | Every signed-in frame sets an explicit `X-Capture-Member` request header. A capture harness that omits it renders the anonymous room while still being named `member-*` |
| Anonymous review frames | Driven through the real public transport — type, submit, let the fetch render the fragment — **not** through the state header. The anonymous mode keeps the role text in the visitor's own browser and has no persistence layer, so the header only reaches the signed-in service stand-in; capturing `public-02-*` any other way silently produces a second copy of the intake screen. The harness now asserts "Reviewed source" is on the page before it shoots, and every committed frame in this set was checked for accidental byte-identity against every other |
| Flag | `PEERSLATE_OPPORTUNITY_SLATE_ENABLED = True` (the flag ships **default off**) |
| Templates / CSS / JS / shell | Real and unmodified, including `base.html` |
| Viewports | 1440x1040 desktop, 390x844 phone, 320x780 narrow, 640x800 at `deviceScaleFactor 2` for the 200% zoom frame |
| Theme | Light. The v1 room is `color-scheme: light` by design (handoff §14-M8) |
| Base | Captured after merging `origin/main` at `bb24472` into the branch, so the frames describe the merged code |
| Fixture role text | A generic Northwind Aero systems-engineering description with Overview / What you'll do / Required qualifications / Preferred qualifications sections, so the frames exercise every block the display normaliser produces. Unchanged from the previous two rounds, so the sheets isolate the layout change rather than a content change. Capture fixture only; nothing is seeded into the product |

### One honest limitation of these particular files

The workbench carries a procedural paper grain. Noise is incompressible by
design, so full-page PNGs of it run to 0.7–2 MB each. Every full-page frame and
parity sheet below is therefore palette-reduced to 256 adaptive colours, which
preserves every layout, type, spacing and elevation judgement but **flattens the
grain and can shift the surface tone by a step**. The detail crops marked
*unreduced* are 1:1 and full colour; `detail-workbench-paper-texture.png` is the
file to judge tone and texture from.

## Side-by-side parity sheets

| File | What it shows |
|---|---|
| `compare-01-role-intake.png` | Image 01 against the built Role · Bring a role at 1440, both normalised to one render width. Authority 53.2%, build 53.3%. |
| `compare-02-review-source.png` | Image 02 against the built Review · Source at 1440. Authority 64.6%, build 64.6%. |
| `compare-04-role-intake-phone.png` | The desktop authority beside the 390 and 320 builds at 1:1. |
| `compare-05-review-source-phone.png` | The same for Review · Source. |

**The phone sheets do not compare like with like, deliberately.** The locked set
has no mobile frame (§14-M9), so there is nothing to match. The desktop
authority sits beside the phone build so the question it answers is the one that
can be answered: does this read as the same product, composed with the same
care. Judge type scale, density, elevation, rhythm and honesty there — not
pixel correspondence.

The desktop sheets compare a full page against a page-sized render: the locked
PNGs have no browser chrome and no site footer, and the build frames carry the
real `base.html` shell above and below the room. Judge the room, not the shell.

## Files

### Anonymous public session

| File | What it shows |
|---|---|
| `public-01-role-intake-desktop-1440.png` | Role intake, anonymous. The `role="status"` truth banner, the serif state title, the decorative props, the blue-but-inert microphone, the two membership-gated tiles, the public truth card. |
| `public-01-role-intake-mobile-390.png` | The same state at 390. The compacted import rows and the shorter paste box. |
| `public-01-role-intake-narrow-320.png` | The same at the 320px floor. The banner is long; this frame is the evidence that it still wraps without horizontal overflow. |
| `public-02-review-source-desktop-1440.png` | Review Source, anonymous. The reading column at its measure, the concern card in the margin, the ruled context strip, the footer action row. |
| `public-02-review-source-mobile-390.png` | Review Source at 390. The card leaves the margin and stacks **above** the document. |
| `public-02-review-source-narrow-320.png` | Review Source at 320. |
| `public-03-noscript-javascript-off-desktop-1440.png` | JavaScript disabled at the browser context. The `noscript` alert replaces the working surface. Its wording is deliberately different from the `role="status"` banner: with JavaScript off nothing is ever sent, so "keeps your role text in your browser" is literally true there. |

### Signed-in member

| File | What it shows |
|---|---|
| `member-01-role-intake-desktop-1440.png` | Role intake, signed in. **The frame for the proportion fix on screen 1**: the workbench holds 53.3% of the viewport and the rails sit back behind a wider gap, as image 01 draws them. |
| `member-01-role-intake-mobile-390.png` | Role intake at 390. The paste box at five visible lines with a 48px mic; the import tiles as rows. |
| `member-01-role-intake-narrow-320.png` | Role intake at 320. |
| `member-02-review-source-desktop-1440.png` | Review Source, signed in. **The frame for the proportion and margin fixes on screen 2**: workbench 64.6%, reading column at 576px, the concern card 242px in the margin it leaves. |
| `member-02-review-source-mobile-390.png` | Review Source at 390. Concern card stacked before the document, footer actions de-duplicated. |
| `member-02-review-source-narrow-320.png` | Review Source at 320. |
| `member-03-correct-the-wording-desktop-1440.png` | The correction disclosure open: original wording read-only above, the member's editable wording below with the small inert microphone, Apply correction / Cancel. |
| `member-06-source-confirmed-desktop-1440.png` | Checkpoint 1 complete. The confirmation banner, the left rail's "Source confirmed" card, and the honestly inert "Review requirements" control with the sentence saying nothing is waiting behind it. |
| `member-08-review-source-200pct-zoom-640css.png` | Review Source at a 640px CSS viewport, the 1280px-at-200% equivalent required by handoff §12. Single column, everything reachable, nothing lost, no horizontal scroll. |
| `member-11-oversize-input-failure-desktop-1440.png` | The oversize-input failure card, produced through the real POST route: role text pushed past the input cap, submitted, and refused with honest copy rather than a silent truncation or a generic error. |
| `member-12-review-source-short-source-desktop-1440.png` | **A source shorter than the concern card** — document 93px, card 442px. The card takes no grid track, so this is the case that would spill out of the workbench if the margin composition had been done with absolute positioning. The workbench grows to the taller of the two instead. It is also why the card is not given a downward offset to balance the gutter: an offset that flatters the long case strands the card below the short one. |

### Detail crops

| File | What it shows | |
|---|---|---|
| `detail-concern-card-in-margin.png` | The composition itself: the title, the lead and the rule beneath them all stop at the reading column's right edge, the margin runs as one reserved gutter, and the card now carries enough substance to hold it. | unreduced |
| `detail-concern-card-focus.png` | Keyboard focus on the card's own "Correct the wording" action. | unreduced |
| `detail-concern-card-stacked-phone-390.png` | The same card at 390: flat rather than floating, because in the flow a raised full-width card inside the workbench card is the "card within a card" reading finding V9 rejected. | unreduced |
| `detail-context-strip.png` | The context strip ruled into equal cells with the authority's vertical hairlines and tinted icon tiles. Three chips where image 02 draws five — Role and Employer come from AI interpretation in OS-2 and inventing them would be fabrication — so the cells divide three ways instead of leaving two thirds of the bar empty. | unreduced |
| `detail-workbench-paper-texture.png` | Unreduced 1:1 crop of the off-white workbench surface. **The file to judge tone and grain from.** | unreduced |
| `detail-microphone.png` | The microphone rendered to the authority — large cobalt glyph on a white disc inside a periwinkle halo — and still honestly inert. | unreduced |
| `detail-upload-import-row.png` | The desktop upload/import row: cobalt icon above a display-serif title, the region ruled off above and below, the vertical hairline breaking around "or", and both honest availability chips. | unreduced |
| `detail-import-row-phone-390.png` | The same row at 390, laid as aligned rows instead of two tall centred columns. | unreduced |
| `detail-rail-card-depth.png` | The rail, showing card elevation and the hairline section rules against the modelled canvas. | |
| `detail-anonymous-truth-banner.png` | The `role="status"` public banner, which names the transit before it claims the locality, so the loudest sentence on the surface and the truth card below it tell the same story. | |
| `detail-inert-mic-and-unavailable-tiles.png` | The whole workbench: inert microphone, its "Dictation arrives in a later update" note, and the two tiles rendered per locked image 01 but never as controls that pretend to work. | |

## Verification run alongside this capture

| Check | Result |
|---|---|
| Workbench proportion at 1440 | Intake 767px = **53.3%** (image 01: 53.2%). Review 930px = **64.6%** (image 02: 64.6%). |
| Review geometry at 1440 | Workbench inner 853px; reading column 576px (67.5%); gap 45px (5.3%); concern card 242px (28.4%) running into the workbench gutter. Image 02's own ratios are 68% / 4.9% / 28.3%. |
| Reading measure across the width range | Swept 320–1600px. While the card is in the margin the measure holds **480–576px (~60–72 characters of Inter)**. Below a 700px workbench the card stacks and the column takes the full width. |
| Concern card against its document | Card 442px, residual gutter 160px on a 602px document — **27%**, against the authority's own 26%. |
| Card taller than the document | `member-12`: document 93px, card 442px, workbench height follows the card, `documentElement.scrollWidth == clientWidth`. |
| Horizontal overflow, both modes and both screens | Clean at 320 / 360 / 390 / 430 / 480 / 560 / 640 / 700 / 768 / 860 / 1024 / 1100 / 1200 / 1280 / 1366 / 1440 / 1600. `documentElement.scrollWidth` never exceeds `clientWidth` and no element's right edge crosses the viewport. |
| Text contrast | **No failures** at 1440 / 390 / 320 across intake, review and confirmed, both modes, measured against each element's resolved background. Lowest pair 4.90:1 — `--os-neutral-ink` on the off-white surface, the split the second round introduced and this round preserves. |
| Touch targets | No focusable target below 24×24 CSS px (WCAG 2.5.8) at any of the three viewports. The phone mic is 48×48. |
| Heading order on Review Source | `h1` Review · Source → `h2` Reviewed source → `h3` Extraction concerns → `h3` source sections. One `h1` per state. The concern card's heading now precedes the document because the `<aside>` precedes it in source order. |
| Honesty states | Mic `aria-disabled="true"`, accessible name ending "(not available yet)", `title` reason. Tiles honestly unavailable. Concern card "None flagged" + "PeerSlate has not read or analyzed this source", none of the authority's fabricated strings, no invented future capability. `<aside>` named by a real `h3`. Props `alt=""` + `aria-hidden="true"`. |
| User-visible copy against the previous round `077f4ac` | Rendered and diffed mechanically across six room states. The **only** difference anywhere is the four added lines of the concern card's "what to look for" checklist. Nothing removed. **Every trust and privacy sentence byte-identical.** |
| User-visible copy against the pre-pass commit `6684441` | Across all three rounds the only removal anywhere remains the label `Original source`, replaced by `Source captured` / `Source confirmed`. |
| `tests.test_opportunity_slate` + `tests.test_opportunity_slate_migration` | 114 tests, OK (1 skipped) |
| `tests.test_site_rules` + `tests.test_governance_pointers` | 33 tests, OK |
| Full suite, `unittest discover -s tests` | 1759 tests, OK (5 skipped), on the branch after merging `origin/main` at `bb24472` |

## Expected byte-identical pairs in the full working set

Recorded so a future reviewer who hashes the untracked working set does not
read these as a capture defect:

- `member-09-role-intake-reduced-motion-*` is byte-identical to
  `member-01-role-intake-desktop-1440.png`. The room has no at-rest motion on
  intake, and none of the three parity rounds added any: the elevation, halo and
  paper grain are static `box-shadow` and `background-image` values with no
  transition, so there is nothing for `prefers-reduced-motion` to suppress. A
  still frame is therefore **not** proof of reduced-motion handling; the CSS
  rule is.
- `member-10-review-source-no-javascript-*` is byte-identical to
  `member-02-review-source-desktop-1440.png`. The signed-in review screen is
  server-rendered and has no `noscript` branch, so disabling JavaScript changes
  nothing visible. That the JS-off context really took effect is proved by
  `public-03`, which *does* differ from `public-01`.

Neither is committed; both are in the working capture only.

## Honest limitations

1. **The `member-*` captures render the signed-out shell.** The harness patches
   only `opportunity_slate_routes.get_optional_identity`, while `base.html`
   derives `auth_navigation_state` from `get_optional_principal()`. The room
   content in every `member-*` frame is a faithful signed-in render; the
   surrounding chrome (header, navigation, the "Sign In" control) is **not**
   what a real signed-in member sees. Read these frames for the room, not for
   the shell.

2. **No database exists on this machine.** No SQL Server engine of any kind is
   reachable here, so every signed-in path ran against an in-memory stand-in
   returning the same `WorkingSourceView` shape as the real service, driven
   through the real save / correct / confirm / delete routes. The anonymous
   public mode has no persistence layer and ran completely unmodified. These
   frames are evidence of rendering and interaction, not of the stored
   procedures.

   **Corrected 2026-08-04.** This entry used to end "whose T-SQL has never
   executed anywhere (see the named unmet SQL gate in the migration header)",
   and said the migration was "deliberately applied nowhere". Both were true
   when these frames were captured and are false now: the slice OS-1 revision
   shipped to production with the 2026-08-04 apply, and the PS-OPPSLATE-001
   T-SQL has since been executed on a real engine by two isolated gates
   (2026-08-03 from empty, 2026-08-04 over a populated OS-1 database). What
   remains true is the sentence above: no engine was reachable *from this
   machine when these frames were captured*, so they evidence rendering, not
   the procedures. The gate record is in the migration header.

3. **The concern card is empty, and the authority's is full.** Image 02's card
   carries a flagged phrase and a correction pair; ours carries a truthful empty
   state because OS-1 runs no AI. The two cards are now the same *proportion* of
   their documents — 27% residual gutter against 26% — but they are not the same
   content, and they will not be until OS-2 has a real concern to show. What
   this round fixed is the composition and the substance; what it did not do,
   and could not honestly do, is show a concern.

Neither limitation 1 nor 2 affects the anonymous captures.
