# Owner visual review — OS-1, 2026-08-03

Pete reviewed the real build against the locked authority
(`visual-authority/2026-08-02-chatgpt-lock/`). Overall: "Pretty close, I do
like it. It just needs a little extra... it's mostly visual love."

**Disposition: implementation parity findings, not a direction change.** Every
item below asks the implementation to match the locked authority more closely.
No composition, hierarchy, dominant action, typography family, colour
language, or responsive model is being revised, so this stays in the Claude
implementation lane under `OWNER_VISUAL_INTEGRITY_STANDARD.md`; it does not
return to the ChatGPT visual-creation lane.

## Screen 1 — Role · Bring a role (image 01)

| # | Finding (owner's words, expanded) | Authority reference |
|---|---|---|
| V1 | **Microphone button is too small and not blue.** In the authority it is a large blue circular control with a lighter halo/glow ring, sitting inside the lower-right of the paste box. The build renders it small and pale. | 01, paste box |
| V2 | **Centre workbench colour is off, and the authority's card is wider.** Owner: "the color of the center page is a little bit different... it's wider and looks better." | 01, centre card |
| V3 | **Left rail replaced the "Why start here?" block with a card.** Restore the authority's treatment: the paper-stack-and-magnifying-glass illustration plus the "Why start here?" heading and copy — not a generic card. | 01, left rail |
| V4 | **Cards do not pop.** They need genuinely deep, layered shadows. The build reads flat next to the authority. | 01, all cards |
| V5 | **The front/centre card is missing its texture.** The authority's workbench surface has a subtle paper texture. | 01, centre card |
| V6 | **Upload document / Import public link section is under-styled.** Missing the authority's finer type treatment above each title (the icon + title pairing), and missing the horizontal rule above and below the `or` divider region. | 01, upload/import row |
| V7 | **Left and right rails lack depth generally.** Owner: "look at the left and the right sides of the page... there's way more shadow" in the authority. | 01, both rails |

## Screen 2 — Review · Source (image 02)

Owner: "The second one's got a lot of issues."

| # | Finding | Authority reference |
|---|---|---|
| V8 | **The "What you'll do" section is missing entirely.** | 02, centre |
| V9 | **Card within a card in the centre**, and the inner one is a different colour. Remove the nesting; the centre is one workbench surface. | 02, centre |
| V10 | **Type and spacing are too loose** — fonts spaced out too much, and **bullet spacing is far too wide**. Tighten to the authority's rhythm. | 02, centre |
| V11 | **Footer actions are in the wrong place.** Correct wording / Replace source / Delete source (and the public-session status) belong at the **bottom**, on the right, exactly as the authority places them. | 02, footer |
| V12 | **A "Source confirmed" card is missing** from the left rail. | 02, left rail |
| V13 | **The extraction-concern card is missing** — owner calls this "a major card". *(Architect note: the concern content is AI-proposed and arrives in OS-2; the card's placement, geometry and styling must be built now so the screen is not missing a structural element.)* | 02, centre/right |
| V14 | **Move the "Original source" card** out of the top-right rail and down the **left** side, between "Why review the source" and the public-session card. | 02, rails |
| V15 | **Shrink both rails** — narrower, with slightly smaller text, tastefully, horizontally and vertically — and **stretch the centre content** into the reclaimed space. | 02, layout |
| V16 | **Centre surface colour is wrong** — currently reads yellow/cream; it should be **white with texture**, matching the authority. | 02, centre |
| V17 | **Shadows are way off on every card** — deeper shadows, more layering, more texture, so cards pop. | 02, all |

## Owner directive — full visual-parity pass

"Go through all of them. Fix them." Apply the same review to **every**
implemented screen and viewport — desktop, mobile 390, narrow 320 — against
its locked authority, checking each of: type family and size, colour, shadow
depth and layering, texture, spacing/rhythm, and element placement. The
rail-shrinking and centre-widening treatment applies to **all** screens, not
only screen 2. Owner: "It's the same situation with all of them."

Screen 1's V1–V7 remain in scope; owner re-emphasised that "Bring a role" is
"particularly bad" on colour and fonts.

## Decorative artwork

Owner said to proceed ("just go through all of them, fix them"), so the
illustrations are being cropped from the locked authority PNGs (route 1
below). If they do not hold up at the sizes used, route 2 remains available.

1. **Crop from the locked authority PNG** — uses artwork Pete commissioned
   and locked; extracted from a composite render.
2. **Commission clean standalone assets from ChatGPT** — better source
   quality, adds a visual-lane round trip.

## Scope note

OS-1 implements screens 1 and 2 only. Image 03's screen is implemented on the
stacked OS-2 branch and receives the same treatment after OS-1's shared room
CSS is corrected, since OS-2 inherits it. Images 04–09 are not yet built.

## Owner clarification, 2026-08-03

Pete, after the findings above were recorded:

> "Use your best judgment to make sure this happens right... You don't have to
> go verbatim what I said. It was more of, like, how do I want you to do until
> it's right."

V1–V17 are therefore **symptoms and direction, not a checklist**. The target is
that the built screens read like the locked authority. Where a literal reading
of an item would produce a worse result than the intent behind it, the intent
wins and the deviation is named below. What does not flex: the honesty states,
the byte-identical trust and privacy copy, accessibility, and the rule against
inventing visual direction.

## Disposition, 2026-08-03

Implemented on `work/2026-08-02-opportunity-slate-os1`. Evidence:
[`evidence/os-1/`](evidence/os-1/EVIDENCE_MANIFEST.md), including
`compare-01-role-intake.png` and `compare-02-review-source.png` — authority
left, build right.

| # | Disposition |
|---|---|
| V1 | Done. 66px white disc, solid cobalt glyph, periwinkle halo, seated lower-right of the paste box. Still honestly inert (§14-M18). |
| V2 | Done, revised in the second round. The centre holds ~57% of a 1440 viewport, between image 01's 53% and image 02's 64%. The surface is no longer white: see the second round's tone decision below. |
| V3 | Done. "Why start here?" / "Why review the source?" are plain canvas blocks again, and both decorative props are restored from the locked PNGs (§14-M5 superseded). |
| V4 / V7 / V17 | Done. Three-level `--os-*` elevation scale plus a deeper, greyer canvas gradient sampled from image 01. Most of the missing "shadow on the left and the right" was the canvas modelling, not the cards. |
| V5 / V16 | Done, revised in the second round. Procedural inline-SVG paper grain over an off-white `#fcfbf8` base, per the owner's later "off white that has texture" (§14-M19). |
| V6 | Done. Cobalt icon above a display-serif title, rules above and below the region, hairline divider breaking around "or". |
| V8 | Not a build defect. The renderer already promotes "What you'll do" to a heading; the 2026-08-02 evidence used a four-line fixture that had no such section. The recapture uses a full role description and the section appears. |
| V9 | Done. The reviewed source sits on the workbench surface; no nested card. |
| V10 | Done, taken further in the second round. Bullets now carry no space beyond the line-height, the whole document sets at 1rem on one 1.5 rhythm, and headings sit barely more than a line above their content — measured against image 02 rather than estimated. |
| V11 | Done. Truth left, all actions bottom-right with hairline separators and the primary last, on one row at 1440. The disclosures remain as one quiet utility row — they are the keyboard and JavaScript-off path and cannot simply be deleted. |
| V12 | Done, state-dependent. The left-rail source card reads "Source confirmed" with a green check once confirmed (image 03's card) and "Source captured" before that. Rendering "confirmed" on an unconfirmed source would have been a truth violation. |
| V13 | Done as structure only, **recomposed in the second round**. The first attempt put the card in a grid column, which pinched the reading column; it now sits in the margin the reading measure leaves, as image 02 draws it. The content is still an AI proposal arriving with OS-2, so the card renders "None flagged / PeerSlate has not read or analyzed this source" and deliberately does not take the authority's amber concern treatment (§14-M17). |
| V14 | **Followed, with the underlying problem fixed differently as well.** The source card did move to the left rail. But the real complaint — an overloaded right rail and a cramped centre — was that the first pass boxed all three standing-help sections. The authority reserves a card in that rail for state-specific data and sets standing help as plain ruled sections (image 01). That is now implemented (§14-M15, §14-M16), which is what actually rebalanced the page. |
| V15 | Done, held at "tastefully". Rails 260/300 → 232/244; rail type one notch down, not two — the rail intro was pulled back up to 0.88rem after 0.86rem read thin against the authority. |

### Named deviations from a literal reading

- **V14**: image 02 itself puts this card in the **right** rail. It is in the
  left rail because Pete asked for it there and because image 03 uses that
  placement for its own source card. Recorded as §14-M15.
- **V12**: the card's heading is state-dependent rather than always
  "Source confirmed", for the truth reason above.
- **V6**: the authority has a rule above this region but not below. The rule
  below is Pete's explicit request and is kept.
- One label changed: `Original source` → `Source captured` /
  `Source confirmed`. It is the only user-visible copy removed anywhere on
  either screen; every trust and privacy sentence is byte-identical, verified
  mechanically across six room states.

### Still short of the authority, honestly

- The right rail's standing help is a truth adaptation of image 01's copy
  (which promises requirement extraction and an alignment map that do not
  exist yet), so its wording — not its treatment — differs from the authority.

## Second round, 2026-08-03

Pete reviewed the corrected build. Two things came back.

### Screen 2 composition

The reviewed source still read airier and less composed than image 02, and the
cause was structural rather than cosmetic: the extraction-concern card was
placed **inside** the centre content flow, taking a grid column. That squeezed
Overview, What you'll do, Required qualifications and Preferred qualifications
into a ~460px measure, and left a hard-edged void beside them once the card ran
out of height.

The first round's own closing note recorded the symptom ("a strip of quiet
space sits to its right") and recorded a rejected fix ("a float was tried; it
produced a 1200px measure"). Both attempts share one cause: the reading column
was being **sized by what was left over** instead of being sized deliberately.
A float only helps if the text already has a measure to keep.

Measured off image 02 (a 1295px render): the workbench is 835px wide, its inner
content 755px, and that inner width divides 68.5% reading column / 4.1% gap /
27.4% margin, with the card running 17px further right into the workbench's own
gutter. The body copy holds that one measure from the first line to the last and
is never re-flowed around the card. Image 02 also rules the title block off at
the **reading column's** right edge, not the workbench's.

That is now what is built:

- the reading column, the heading and the ruled lead all share one measure
  (`--os-measure`, 32rem — about 64 characters of Inter);
- the card is laid over the margin that measure leaves, 224px wide, running
  12px into the gutter;
- both children occupy the same grid cell, so the row is as tall as the taller
  of them and a card taller than the source cannot overflow the workbench
  (`member-12-review-source-short-source-desktop-1440.png` is that case);
- the arrangement is governed by a container query on the workbench, not a
  viewport breakpoint, because a 1200px viewport is a 1057px workbench with the
  rails gone and a 534px workbench with them still there. Below a 700px
  workbench the card stacks under the document.

Density went further toward image 02 in the same pass. The reviewed source now
sets at 1rem — larger than the rails, as the authority sets it — on a single 1.5
line rhythm with no extra space between list items, headings sitting barely more
than a line above what they introduce, and about two lines before the next
section. Measured against image 02: section gap 1.90 line-units against its
1.92; heading-to-content 1.09 against its 1.09–1.28.

**The dashed leader is still not drawn**, and the empty state settles the
question §14-M10 left open: with nothing flagged there is no phrase to point at,
and a leader landing on an arbitrary line of the member's own wording would
imply PeerSlate had picked it out. The relationship is carried by position, by
the accent rule on the card's leading edge, and by the `<aside>` being named
after the card's own heading — which is now a real `h3`, so the card appears in
the document outline where it sits. Locked by
`test_the_extraction_concern_card_is_tied_to_the_source_it_describes`.

### Workbench surface tone

Owner decision, superseding the V2/V5/V16 reading of "white with texture":

> "Make it an off white that has texture."

Pure white was wrong in the other direction. Against this cool canvas it
sampled **bluer** than the authority's own paper — R−B = −2, where image 01's
surface measures +2 and image 02's is neutral — so it read clinical rather than
like paper. `--os-surface-paper` is now `#fcfbf8`, a warm-neutral off-white at
R−B = +4 and 252 lightness; the rejected `#f7f6f1` was +6 at 247, five steps
darker and half again as warm, which is the difference between paper and yellow.
Candidates from `#fdfcfa` to `#fbf9f5` were rendered and compared against the
locked images in context: `#fdfcfa` still read as white and `#fbf9f5` started to
read cream. The grain and the top-lit sheen are unchanged; only the base tone
moved, and the sheen's cool `#f3f7fd` foot went warm-neutral with it.

One accessibility consequence, fixed in the same change: moving off pure white
cost every text pair about 0.25 of contrast ratio, which took the neutral slate
`#6b7590` from 4.59:1 to 4.44:1 as text. `--os-neutral-ink` (`#656e88`, 4.90:1)
now carries the two neutral TEXT uses, following the same split `--os-warning` /
`--os-warning-ink` already uses. Borders and icons keep `--os-neutral`.

### What did not change

No user-visible copy — the six rendered room states are byte-identical to the
first round. No behaviour, route, service, or migration. Every honesty state
intact: the mic stays inert, the two tiles stay honestly unavailable, the public
banner stays truthful, and the concern card still flags nothing and claims no
analysis. Screen 1 was not regressed; the tone change moved it closer to image
01, where the cool paste-box well now reads as cut into warm paper.

## Third round, 2026-08-03 — "Resolve the gaps"

Pete reviewed the second round's sheets and asked for the two gaps the
previous writer had named honestly in its own report, plus the viewports
nobody had judged with the same eye.

### Gap 1 — workbench proportion

The second round set both screens to ~57% of a 1440 viewport and called it a
deliberate compromise between image 01's 53% and image 02's 64%. It matched
neither. Measured off the locked PNGs by scanning each row for the workbench's
warm surface against the cool canvas:

| | render | workbench | share |
|---|---|---|---|
| image 01 | 1448px | x332–1102, 770px | **53.2%** |
| image 02 | 1295px | x239–1075, 836px | **64.6%** |

That difference is the design, not noise. Screen 1 is an intake form whose
object is a paste box and it wants air around it; screen 2 is a reading
document and it wants the width. Image 02 shrinks its rails *and* widens its
centre to get there — measured, its left rail is 197 CSS px against image 01's
227, and its rail type is a notch smaller with it.

Each screen now carries its own proportion. `.os-layout--review` is gated on
exactly the condition that selects `_review.html`, so the geometry cannot drift
from the screen it belongs to, and
`test_each_screen_carries_its_own_layout_proportion` locks that.

Built: **intake 53.3%, review 64.6%** at 1440.

Image 01 also spends far more of its side zones on air than on rail — a 58px
gap to the workbench where ours had 29 — which is what makes its workbench
read as a card floating in a room rather than one panel of three. The intake
gap moved to match; image 02's own gap measures ~33px, so the review screen
keeps the existing 2vw.

**One named deviation.** Image 02 keeps "Why review the source?" on one line in
its 197px rail. Our display face (Newsreader, which the site actually loads) is
about 25% wider per character than the mockup's, so at that rail width the same
string needs ~12px type to fit — below its own body copy, which would destroy
the hierarchy. The wrap is accepted and composed instead: the eyebrow is
top-aligned so the icon sits with the first line rather than floating between
two. The state title was reduced to image 02's own modest rail-title scale and
fits on one line.

### Gap 2 — the quiet margin below the concern card

Ours was 331px of card above 319px of empty gutter. The cause was two things,
and only one of them was content.

**Composition.** The second round fixed the measure at 32rem. That was right
for an 826px workbench and wrong once the workbench went to 929px: the column
stayed put and the margin grew, so widening the screen made the void *worse*.
Image 02 sets the measure as a ratio of its own inner width — on its 754px
inner content, 68% reading column / 4.9% gap / 28.3% card, the card running 8px
past the workbench's inner edge. Those ratios are now what is built, card and
gap included; a fixed card was 28% of the workbench at 1440 but 38% of it at
1280, which dragged the measure to ~55 characters exactly where the screen was
already tightest.

**Content.** The card was given real substance, under the hard constraint that
it may not fabricate a concern, imply analysis has run, or take the authority's
amber treatment while nothing is flagged. The obvious filler — a promise about
what PeerSlate will detect once OS-2 lands — was rejected: that is a
specification invented at the stylesheet level, and a member reads it as a
capability that exists. What was added instead is what the **member** is being
asked to check, in the present tense, which is true today and is the actual job
of this screen:

> What to look for as you read:
> · every section of the posting is here
> · lists did not run together
> · no sentence is cut off part-way

`test_the_extraction_concern_card_never_claims_a_concern` now asserts both the
honest framing and the absence of the dishonest one ("PeerSlate will check",
"we checked", "has been checked", …).

Result at 1440: card 442px, residual gutter 160px on a 602px document — **27%,
against the authority's own 26%.** The card stays top-aligned rather than
centred or offset, deliberately: it is a reading instruction, so it has to be
visible when the member starts reading, and centring would float it into the
middle of a long posting while an offset would strand it below a short one
(`member-12`).

Nothing was invented to fill space, and no source metadata was duplicated into
the gutter — the left rail's source card stays where Pete put it.

### Gap 3 — the phone and narrow frames

Previously checked only for "no overflow". Judged properly this round, and four
things were actually wrong:

| | Found | Fixed |
|---|---|---|
| Paste box | `rows="10"` plus 5rem of reserved mic space made the empty box ~370px tall at 390 — most of a phone screen given to a box with nothing in it, on the screen whose whole job is to invite text | Five comfortable visible lines; mic to a 48px target, still twice the 2.5.8 minimum. `rows="10"` stays on the element so the no-CSS rendering is unchanged |
| Import tiles | Two centred columns stacked to ~370px — the most vertical space on the screen given to the two things that are honestly unavailable | Laid as rows: badge, title, body, availability chip, all aligned. Same elements, same honest chip |
| Concern card | Stacked full-width *after* the whole document, carrying the float elevation — a raised card inside the workbench card, which is the "card within a card" finding V9 rejected | Moved before the document in **source order** (so it is also what a screen-reader user hears first), and the float elevation now applies only inside the container query, where the card actually floats |
| Duplicate actions | "Correct wording" and "Delete source" appeared three times within one screenful once the layout went single-column — rail card, disclosure, footer | The footer's two *reveal* links are hidden below 640px. The controls they point at stay visible, focusable and operable; no capability is removed |

At 320 the workbench padding came in from 1.1rem to 0.9rem — at that width the
padding is worth more as measure than as margin, four or five characters on
every line — and the document sets a step down with it.

The 390 and 320 frames now sit beside the desktop authority in
`compare-04-*` and `compare-05-*`. There is no mobile authority (§14-M9), so
the question those sheets answer is whether it reads as the same product, not
whether it matches a frame that does not exist.

### Verification

| Check | Result |
|---|---|
| Workbench proportion at 1440 | intake 767px = 53.3% (authority 53.2%); review 930px = 64.6% (authority 64.6%) |
| Review geometry at 1440 | inner 853px; measure 576 (67.5%, authority 68%); gap 45 (5.3%, authority 4.9%); card 242 (28.4%, authority 28.3%) |
| Reading measure, swept 320–1600 | 60–72 characters wherever the card is in the margin (was 55–72 before the card was made proportional). Below a 700px workbench the card stacks and the column takes the full width |
| Horizontal overflow | Clean at 320/360/390/430/480/560/640/700/768/860/1024/1100/1200/1280/1366/1440/1600, both modes, both screens. No element's right edge crosses the viewport |
| Card taller than the document | `member-12`: document 93px, card 442px, workbench grows to the card, no overflow |
| Contrast | **No failures** at 1440/390/320 across intake, review and confirmed, both modes. Lowest pair 4.90:1 — `--os-neutral-ink`, preserved from the second round |
| Touch targets | No focusable target below 24×24 CSS px at any of the three viewports |
| Heading order | `h1` Review · Source → `h2` Reviewed source → `h3` Extraction concerns → `h3` source sections. One `h1` per state |
| Honesty states | Mic `aria-disabled` with "(not available yet)" name and title; tiles honestly unavailable; concern card "None flagged" + "has not read or analyzed"; no fabricated strings; aside named by a real `h3`; props `alt=""` + `aria-hidden` |
| User-visible copy vs the second round `077f4ac` | The **only** change anywhere in six rendered room states is the four added lines of the concern card's checklist. Nothing removed. Every trust and privacy sentence byte-identical |
| User-visible copy vs the pre-pass `6684441` | Across all three rounds the only removal anywhere remains the label `Original source` |
| Tests | 114 + 33 = 147 focused/guardrail, OK (1 skipped); full suite below |

## Status

Findings recorded 2026-08-03; three rounds of corrections implemented the same
day. Evidence: [`evidence/os-1/`](evidence/os-1/EVIDENCE_MANIFEST.md). PR 250
remains open and unmerged; OS-1 does not merge until Pete accepts the corrected
build. Nothing is deployed.
