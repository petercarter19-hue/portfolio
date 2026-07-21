# PS-JOURNAL-001 — Visual Finish Addendum: the IDENTICAL bar

**Owner ruling (Pete, 2026-07-21, after bouncing the first build):** the build
must look **identical to the accepted mockups** — the colors, the visual
flares, the background, the little details, every element. The mockups' color
scheme is pinned for the Journal now (site-wide color conversation is separate
and later). **Process mandate:** Opus may not pass the build until it is
identical; a failed review is never silent — it kicks back to the architect
(Fable) to revise the spec, then re-implement, looping until identical. Only
then is it shown to Pete.

This addendum SUPERSEDES doc 10's "replace rendered colors with existing site
tokens" instruction **for the Journal surfaces**: the Journal renders in the
mockups' own palette, scoped to the Journal page (`--jbook-*` variables), not
the global site tokens.

## 1. The pinned Journal palette (sampled from the accepted PNGs)

| Token | Value (sampled) | Use |
|---|---|---|
| `--jbook-desk` | `#000a1e` → `#0a141e` subtle vertical gradient | The page background — the near-black navy "desk" the book sits on. NOT the site canvas |
| `--jbook-page` | `#f0f0e6` base, gradient hints of `#faf0e6` / `#f0e6dc` | The warm parchment page stage. NOT white, NOT #F6F7FA |
| `--jbook-page-edge` | `#e6d2b4` / `#dcc8aa` stacked strips | Visible stacked page edges on the book's outer sides |
| `--jbook-gold` | `#e6be78` bright / `#b48c50` mid / `#aa8246` deep | Ornament gold: ribbon, stitching, clasps, numerals, waveforms, stars |
| `--jbook-ink` | `#141e1e` | Body ink on parchment |
| `--jbook-dark-page` | `#0a141e` → `#000a14` | Dark-theme page stage (the same book by lamplight) |
| Gold on dark | `#e6be78` | Headings/accents in dark theme |

Contrast duty: body text on parchment uses `--jbook-ink` (≥4.5:1); gold is for
ornament, numerals, and large display only. Verify computed ratios.

## 2. Every-element checklist (each item is individually required)

**The book itself**
- Full-viewport near-black navy desk behind everything; the book floats on it
  with soft deep shadow.
- Book chrome: rounded outer spine, **gold stitched border** line inside the
  page edge, **stacked page-edge strips** on the outer edges, **gold ribbon
  bookmark** hanging over the right edge with the **leaf emblem**, subtle
  corner clasp accents. Both themes.

**Contents rail (left, on the parchment)**
- "CONTENTS" small-caps label; entries `01–06` with small gold numerals, icon,
  name, two-line whisper subtitle; active chapter = warm highlight pill with
  gold left tick; bottom **flourish ornament** + the italic line
  "Every moment today becomes tomorrow's legacy." exactly as in the mockups.

**This-season hero (the card at top of the page)**
- A real photo region left/behind with soft gradient into the card (fixtures
  use the fixture member's photo; real members use their profile photo asset —
  Pete's exists in-repo; an absent photo degrades to an elegant navy-gold
  gradient, still rich).
- "THIS SEASON" small-caps gold eyebrow; two-line serif italic headline
  ("Building clarity. Creating impact." in fixtures; member-editable field in
  real data with a tasteful default); the microline "Focus. Learn. Build.
  Share."; the **script signature** in gold; three stat tiles (gold serif
  numerals + small labels) separated by hairlines, real counts.

**Timeline**
- Large serif date numerals (day over month) left of a thin **gold spine line
  with gold node dots** connecting entries.
- Entry cards: warm parchment-white, soft shadow, rounded; meta row
  `9:41 AM · Voice Note · 🔒 Private` (time only when a real field exists —
  fixtures include times); serif italic titles; **gold waveform with round
  gold play button + duration** on voice rows; **rounded photo thumbnail on
  the card's right** for rows with media (fixtures include them); gold star
  milestone marker; the **handwritten gold script annotation** "Proud of this
  one ⭐" beside the first achievement (script font, rotated slightly).
- "Load more moments ⌄" centered quiet control.

**Composer (facing page) / Saved state / Empty / Manage / Detail**
- Composer renders as the book's facing right page in the same parchment;
  Type/Speak tabs with gold active underline; truth-line with small lock;
  attachment row with camera+film gold outline icons; gold Save Moment with
  pencil icon.
- Saved: gold **check medallion with sparkle burst** at top; the confirmation
  line; "Use This Moment" four chips **with their icons** in a 4-up grid;
  "Who can see it" row with the lock select showing "Only you"; preview
  reassurance line; gold Done; quiet Back to page.
- Empty: centered **gold open-book line illustration with sparkles**; "Your
  story starts here." serif; sub-line; gold CTA; "Private to you"; the
  **quote card** with left gold script bracket flourish, unattributed.
- Manage: the dense table exactly per accepted C (DATE numerals+time · KIND
  icon+label · MOMENT with inline waveform/thumbnail where the row has one ·
  STATUS lock Private · per-row ⋯), search field with gold focus ring, count
  footer + "You own your Moments. Only you can see them."
- Detail: serif date block, meta row, the member's words as serif hero,
  waveform player region, photo aside, Version history panel, lifecycle row,
  footer truth line — per accepted B.

**Both themes, all breakpoints** — the dark twin is the same book by
lamplight (deep navy page, gold accents, warm lamp vignette allowed); mobile
keeps the parchment-book character (chip-row rail, full-bleed warm page).

## 3. Fixture-richness rule (resolves the honesty tension)

Evidence screenshots and demo fixtures MUST demonstrate the full richness —
photo hero, season line, times, thumbnails, waveforms, annotations — using
fixture data (Maya-style), because the mockups are the bar. Real-member
rendering uses real assets (profile photo, authored season line) and degrades
*beautifully* when absent — but absence styling is also designed, never a
collapsed blank. Honesty governs **data**, never **finish**.

## 4. The review gate (binding process)

Opus review = a **per-element side-by-side audit** against the accepted PNGs
using this checklist. Any visible finish gap on any element = **NO-GO**, with
a delta list returned to the architect. There is no "acceptable translation"
category. The loop (spec → implement → review) repeats until Opus certifies
**identical or better**, and only then is the build shown to Pete.

## 5. Owner Review Round 1 — binding punch list (Pete, 2026-07-21)

Pete reviewed the first rebuilt light page against the mockup pair. Every item
below is binding, **applies to desktop AND mobile** (the 390px sheet inherits
the same proportions, type scale, chrome, and page size), and must be verified
individually by the reviewer before any GO.

**Typography override (supersedes doc 10's font-replacement row):** the
mockup's rendered typography IS the spec — faces, sizes, weights, and
proportions. The Bible's font rules yield to the accepted mockup. "Journal"
title, date numerals, card text, and rail text are all currently too small;
match the mockup's scale.

**Rail (left contents):**
1. Add the "CONTENTS" small-caps label at the top; push rail entries down
   accordingly.
2. Chapter numerals (01–06) render ABOVE each chapter name (stacked as in the
   mockup), not inline.
3. Loosen the vertical rhythm: **Reflections must land beside the May 19
   row**, and the "Every moment today becomes tomorrow's legacy." flourish
   line must land beside the **May 13 row** — these are alignment anchors.

**Header zone:**
4. "Journal" title much larger (mockup scale).
5. Manage + Capture a Moment sit directly above the This-season card.
6. The subtitle is EXACTLY the mockup's single line ("Your complete record of
   moments, ideas, and milestones — captured in your own words."). Remove the
   added "Nothing here is shared…" sentence (the privacy truth lives in the
   lock cue and composer truth-line).

**Proportions (measure, don't eyeball):**
7. Measure the mockup's aspect ratios and implement them: the This-season
   hero is too wide and not tall enough; entry cards likewise. Card width/
   type scale must make titles naturally wrap to two lines as in the mockup.
8. Card thumbnails proportionally larger, as in the mockup.

**Timeline:**
9. Date numerals larger (mockup scale).
10. The vertical spine line darker; the node dots centered ON the line, not
    floating beside it.
11. The waveform + play button are rejected as-built: rebuild to the mockup's
    dense elegant bars and rich gold circular play control.
12. First page shows ONLY the mockup's four entries (May 20/19/18/13); later
    Moments (e.g. May 09/06) appear via "Load more moments" or scroll-in.
13. Card text is a summary: long titles truncate elegantly; clicking the card
    opens the Moment detail with the full capture. (Full body text on detail
    requires the queued J1.2 read addition; until then detail shows its
    honest current fields.)

**Book chrome & color:**
14. The ribbon/leaf bookmark hangs over the page's top-right edge exactly as
    in the mockup — not inside the page.
15. Edges: left side gets the beige stacked page-edge treatment; the right
    edge fades as in the mockup; the outer surround is the deep near-black
    navy on BOTH themes (light mode included). The current pale blue edges
    are rejected.

**Mobile:** all of the above translate to 390px — mockup-scale type, the
book character, darker spine, four-entry first page, summary truncation, and
the corrected waveform component.

## 6. Owner Review Round 2 — the composer (Pete, 2026-07-21, binding)

Pete reviewed the composer (Type + Speak) against accepted screens 02/03.
Every item binds desktop AND mobile; **the Speak tab receives every Type-tab
item identically** (its stage is even taller than Type in the mockup).

**Proportions:**
17. The composer is far more vertical than built: roughly **twice as tall,
    slightly narrower** — it reads as the book's facing page, and the writing
    area fills almost the whole page. Measure the mockup's composer
    width:height and writing-area proportion and implement those numbers.

**Privacy block:**
18. "Private to you" renders **bold**, with the **gold lock icon**; the line
    "Only you can see this until you choose to share." sits **below it on its
    own line** — never inline.

**Attachment row:**
19. Keep the build's row design (owner preference: "I actually like what you
    did better") — camera + film icons + "Add a photo or video".
20. Implement the **attached state** from the mockup: thumbnail with remove ×
    and the caption "Attached to this Moment · Private". Runtime staging is
    unchanged (photo remains gated), but the state exists, renders when an
    attachment exists, and appears in fixture evidence.

**Footer:**
21. **Cancel on the left; Save Moment bigger, wider, and darker gold** per
    the mockup.

**Chrome:**
22. The composer card has a **× close control top-right** (missing in the
    build — owner: "a big deal").
23. **Real book pages**: the page layering must be clearly defined —
    visible page structure, colors fading in/out at the edges, and the subtle
    **edge texture** the mockup shows on both the main page and the composer
    card. "There are actually no pages" in the build — fix it. Desktop shows
    the full two-page book; mobile keeps the same page character (texture,
    edge fades, defined sheet) adapted to the single-column 390px sheet.

**Owner reinforcement (2026-07-21): every item in §5 and §6 binds on MOBILE
exactly as on desktop — no item may be verified desktop-only. The reviewer's
per-item pass/fail must cite both form factors.**


## 6b. Owner Review Round 3 — the saved state (Pete, 2026-07-21, binding)

Compared against accepted screen 05 (the "Moment saved" panel, bottom-right of
the composer sheet). Every item binds on desktop, MOBILE, and the DARK theme
equally.

24. **The check medallion is rejected as built**: implement the mockup's
    refined gold check inside the navy circle with its sparkle burst, and make
    the medallion + sparkles + headline **evenly positioned/centered** — the
    current composition is uneven.
25. **Use This Moment chips**: icons larger per the mockup; chip proportions
    (length:width) measured from the mockup and matched; overall finish
    lifted. (Owner allows the chips to remain slightly larger than the mockup
    — the proportions and polish are what must match.)
26. **"Who can see it" is missing its prompt**: render the mockup's
    dropdown-style selector — lock icon + "Only you" + chevron affordance in
    the gold-outlined select — under the "Who can see it" heading, with the
    preview reassurance line. It remains truthfully locked/disabled in J1,
    but it must LOOK like the mockup's prompt, not a flat row.
27. **Done button rejected as built**: the mockup's "✓ Done" — check icon
    present, correct gold color and size.
28. **The lock under the headline**: bigger and better colored (gold) per the
    mockup.
29. **The saved card gets the same real book-page treatment** as item 23 —
    defined page, edge texture, fading edges. ("As always there's issues with
    the page part.")
30. **Dark theme parity**: every saved-state item verified on the dark
    version and on mobile, per the §6 mobile reinforcement.

## 7. Process escalation (owner mandate, 2026-07-21)

- The reviewer must verify §5 and §6 **item by item** (pass/fail each) with
  pixel/proportion measurements, on desktop and mobile, before any GO. A
  reviewer that passes a visible mismatch has failed its role.
- **Circuit breaker:** if the loop returns NO-GO twice consecutively — or the
  same item fails twice — the loop STOPS and the package returns to the
  architect (Fable) with the full delta history for a spec/architecture
  revision. It never grinds silently and never reaches Pete unpassed.
