# PS-OPPORTUNITY-SLATE-001 · slice OS-3 · visual and state evidence

> Historical pre-clarification evidence: these captures honestly show the
> 12px build reviewed on 2026-08-04. Pete subsequently resolved the source
> set's internal spacing conflict in favor of image 04's measured geometry;
> the implemented shared gap is now 24px. Fresh post-clarification captures
> are recorded below; this original set remains the honest pre-change record.

Captured 2026-08-04 from the real Flask application in a headless Chromium at
the viewports the owner named, driven end to end through the room's own
anonymous public session: paste → review wording → confirm source → read the
statements → **Confirm requirements and analyze** → the Alignment workbench.

**How the model was stood in for.** Every capture runs the real prompt
contracts, the real validators and the real composition templates; only the
Anthropic client is replaced, by a scripted stand-in that answers each step
with a reply grounded in exactly what it was given. Nothing here made a network
call. The separate live model-selection trial is recorded in
`OS-3_COMPLETION_REPORT.md` section 1 and is not part of this set.

**Whose evidence is in the pictures.** The anonymous public session grounds on
Workshop's own demo library (`services/workshop_demo_library.py`), which
belongs to the fictional Jordan Ellis. Every screen that shows it says so.
No real member's evidence appears anywhere in this set.

## Owner-gap clarification evidence — 2026-08-04

The following files in `owner-gap-2026-08-04/` were captured from the real
local Flask route with the normal anonymous public flow and a deterministic
model stand-in at the client boundary. They contain only the labeled Jordan
Ellis fictional demo library. The capture harness asserted the computed
`--os-card-gap` value was exactly `24px` before each screenshot; the machine
record is `os3-owner-gap-evidence.json`.

| File | Viewport and result |
|---|---|
| `os3-alignment-owner-gap-desktop-1440x1024.png` | 1440×1024. Three-column workbench remains intact; separate summary and qualification cards use the clarified rhythm without overlap or clipping. |
| `os3-alignment-owner-gap-mobile-390x844.png` | 390×844 from page start. Header, public-session truth, state heading, and result truth card remain readable without horizontal overflow. |
| `os3-alignment-owner-gap-mobile-cards-390x844.png` | 390×844 at the card stack. The two summary cards and first qualification card remain distinct, readable, and visibly separated by the clarified gap. |

## Comparison sheets — authority left, build right

| File | What it shows |
|---|---|
| `compare-04-alignment-desktop.png` | Image 04, the package's exact geometry authority, beside the built workbench at 1440. |
| `compare-04-alignment-mobile.png` | The same authority beside the 390 build. There is no mobile authority (handoff 14-M9), so the question this sheet answers is whether it reads as the same product. |
| `compare-04-alignment-narrow.png` | The same, at 320. |

## Built states

| File | State |
|---|---|
| `public-10-alignment-desktop-1440.png` | `ALIGNMENT_UNSAVED`, the full workbench: context strip, the two count summaries, the four separate cards, both rails, the footer. |
| `public-11-alignment-mobile-390.png` | The same at 390. The alignment table restacks into one card per qualification, preserving image 04's reading order: number and wording, explanation, status, authorized evidence, review control. |
| `public-12-alignment-narrow-320.png` | The same at 320. |
| `public-13-analysis-processing-desktop-1440.png` | `ANALYSIS_PROCESSING` — image 08's bounded three-stage rail, captured while a request is genuinely in flight, with the correction rail read-only and Cancel live. |
| `public-14-analysis-failure-desktop-1440.png` | `ANALYSIS_FAILED` — image 09-b's card, word for word, with every confirmed input still on screen behind it. |
| `public-15-alignment-200pct-zoom-640css.png` | WCAG 1.4.10 reflow: 1280 at 200% zoom, i.e. an effective 640 CSS px viewport. |
| `public-16-alignment-reduced-motion-1440.png` | `prefers-reduced-motion: reduce`. |
| `public-17-response-stored-desktop-1440.png` | A member response stored and shown back for confirmation, with the panel's own statement that it changed no status and became no evidence. |

## The SIGNED-IN workbench (independent review finding F6)

Added 2026-08-04 after independent review. Every capture above is the anonymous
public session; §15's image-04 acceptance item is the **private** workbench,
which differs in visible chrome — no public banner, no amber demo-evidence
note, a different truth-card sentence, a "Session private" context chip, and
the member's own evidence titles instead of the demo persona's.

| File | What it shows |
|---|---|
| `compare-04-alignment-signed-in-desktop.png` | Image 04 beside the **signed-in** build at 1440. |
| `member-18-alignment-signed-in-desktop-1440.png` | The private workbench at 1440, analysed, first qualification selected. |
| `member-19-alignment-signed-in-mobile-390.png` | The same at 390. Finding F4's reflow: the response and evidence rails are in-flow sections **beneath** the qualification cards, in the markup as well as on screen — see the tab-order tables below. |
| `member-20-alignment-signed-in-narrow-320.png` | The same at 320. |
| `member-21-alignment-signed-in-rails-selected-1440.png` | Qualification 3 selected — the finding-F1 shape (head and tail cited, middle uncited) rendering **Partially supported**, with the member's stored response shown back. |
| `member-22-alignment-signed-in-rails-selected-390.png` | The same selection at 390. |

**What is real in these captures, and what is stood in.** This has to be exact,
because the room's whole subject is not claiming more than is true.

* **Real:** the alignment prompt contract, the reply validators, the coverage
  derivation on *both* the write path and `_derive_from_stored`'s read path,
  the composition templates, every Jinja template, the real CSS, the real room
  script, rendered by the real Flask application in headless Chromium.
* **Stood in:** the Anthropic client — a scripted stand-in whose every citation
  is a verbatim span of exactly the text it was given, so each one still has to
  survive the real validators. **No network call was made.** Also stood in: the
  database row → view mapping. The SQL path has its own separate proof, the
  isolated apply/verify/rollback gate in `tests/test_opportunity_slate_migration.py`
  and `OS-3_COMPLETION_REPORT.md` §4.
* **Fictional:** the member and their Workshop library. No real member's
  evidence appears anywhere in this set.
* **One capture artifact, called out rather than cropped:** the site header
  still shows `Sign In`, because the room was rendered outside a real login
  session. The *room* is in signed-in mode throughout — the chrome around it is
  not. That is the harness, not the product.

Truth checks run against the rendered signed-in page, all passing: no public
banner; "Session private" chip present; no demo-evidence note; member evidence
titles present; the F1 shape derives Partially supported; F5's quotes present;
the F9 footer constants rendered; `data-os-focus` and `data-os-swap-announce`
present.

Derived statuses in the captured run, showing the composed sentences a member
actually reads:

```
[supported             ] Your evidence covers every part of this qualification.
[partially_supported   ] Your evidence covers “Strong understanding of systems
                         engineering”. Not established: “Strong understanding of
                         systems engineering processes”.
[partially_supported   ] Your evidence covers “Experience of verification” and
                         “in a regulated environment”. Not established:
                         “Experience of verification and validation”.
[supported             ] Your evidence covers every part of this qualification.
[not_enough_information] No authorized evidence was matched to this.
```

### Responsive sweep, signed-in build

`document.scrollWidth <= document.clientWidth` at 320, 360, 390, 430, 480, 560,
640, 700, 768, 900, 1024, 1100, 1200, 1280, 1366, 1440 and 1600. **No overflow
at any width.**

### Finding F4, second correction — the measured tab order

The first F4 fix reordered the **painted** layout below 640 (`display: contents`
plus `order`) and left the markup alone, so keyboard and screen-reader users
still met the response rail before any qualification. The regions are emitted in
reading order now, and desktop rebuilds image 04's three columns from that
markup with grid areas. Walked with real `Tab` presses in headless Chromium,
recording each stop's region and its y position on the page. Stops 1–4 are the
site header (skip link, home, Menu, Sign In) and stop 5 is the room's own
`Back` link in the subheader above the layout; all five sit outside the three
regions and are identical before and after.

**Before, at `7bd18d8`:**

| Build | Stops | Region | Painted at |
|---|---|---|---|
| 390 signed-in | 6–13 | response rail (inside the left rail) | y 3102–3699 |
| | 14–24 | workbench, qualification cards | y 443–2785 |
| | 25 | evidence rail | y 4326 |
| 320 signed-in | 6–13 | response rail | y 3353–3980 |
| | 14–24 | workbench | y 506–3038 |
| | 25 | evidence rail | y 4648 |
| 390 public | 6–13 | response rail | y 2818–3415 |
| | 14–22 | workbench | y 694–2501 |
| | 23 | evidence rail | y 4071 |
| 320 public | 6–13 | response rail | y 3100–3726 |
| | 14–22 | workbench | y 821–2784 |
| | 23 | evidence rail | y 4443 |

**After:**

| Build | Stops | Region | Painted at |
|---|---|---|---|
| 390 signed-in | 6–16 | workbench, qualification cards | y 438–2780 |
| | 17–24 | response rail | y 3098–3695 |
| | 25 | evidence rail | y 4321 |
| 320 signed-in | 6–16 | workbench | y 501–3033 |
| | 17–24 | response rail | y 3349–3975 |
| | 25 | evidence rail | y 4643 |
| 390 public | 6–14 | workbench | y 689–2496 |
| | 15–22 | response rail | y 2813–3410 |
| | 23 | evidence rail | y 4066 |
| 320 public | 6–14 | workbench | y 816–2779 |
| | 15–22 | response rail | y 3095–3721 |
| | 23 | evidence rail | y 4439 |

Focus moves monotonically down the page in all four after-runs. The signed-in
build gains stops 6–16 rather than 6–13 in the workbench because the closing
strip's three controls are inside it.

Region positions on the phone builds, after:

| Build | Lead | Workbench | First qualification card | Closing strip | Response rail | Evidence rail |
|---|---|---|---|---|---|---|
| 390 signed-in | y=146 | y=380 | y=743 | y=2548 | y=2931 | y=3764 |
| 320 signed-in | y=146 | y=402 | y=850 | y=2763 | y=3182 | y=4044 |
| 390 public | y=397 | y=631 | y=1088 | y=2263 | y=2646 | y=3479 |
| 320 public | y=441 | y=717 | y=1279 | y=2529 | y=2928 | y=3791 |

### Desktop 1440 is unchanged, measured rather than asserted

Every region's bounding box at 1440, before (`7bd18d8`) and after, in both
modes. All ten are byte-identical.

| Region | member 1440 | public 1440 |
|---|---|---|
| workbench | 304,162 844×1266 | 304,279 844×1089 |
| first qualification card | 304,376 844×422 | 304,549 844×235 |
| response rail | 25,487 235×860 | 25,624 235×860 |
| evidence rail | 1204,162 211×921 | 1204,279 211×952 |
| closing strip | 304,1194 844×202 | 304,1134 844×202 |

The response rail sits 12px under the truth card and the closing strip 12px
under the last workbench card, in both modes — the room's own card gap, exactly
as when the rail was that card's sibling.

**One measured phone difference, and it is a restoration.** With the left rail
no longer `display: contents`, the gaps between the state title, the intro and
the truth card return to the room's 12px card rhythm from the 14.4px page-grid
row gap the first correction had given them; everything below shifts up 4.8px.
Every other step in the room already uses 12px there.

### What was re-captured, and what was not

Re-captured 2026-08-04 for this correction, from the rebuilt harness described
above: `compare-04-alignment-desktop/mobile/narrow`,
`compare-04-alignment-signed-in-desktop`, `public-10`, `public-11`, `public-12`,
`public-15`, `public-16`, and `member-18` through `member-22`.

**The signed-in fixture was rebuilt** for this round, because the earlier
round's harness was not retained: five qualifications (one supported, one
partially supported on a sub-span, one carrying the finding-F1 head-and-tail
shape with a stored member response, one supported, one with no citation at
all), one responsibility, one informational statement, and two member evidence
records. It exercises the same states as the accepted round.

Not re-captured, and unaffected because desktop geometry is measured identical:
`public-13` (processing), `public-14` (failure) and `public-17` (response
stored), all 1440 frames from the accepted round.

### Finding F3, the trust-sentence rendering matrix

Measured by rendering every room at every step in both modes and counting the
exact sentences. The full table is in `OS-3_COMPLETION_REPORT.md` §8. Summary:
the public banner's two sentences render on **every** step including alignment;
the public session-truth card renders on Role, Replace, Review Source and
Review Requirements but **not** on Alignment, where image 04's amber card takes
the slot; "PeerSlate stores none of it." survives on Alignment inside that amber
card. Two sentences lose a surface, not three, and the AI-transit disclosure
remains on the screen where the model call happens.

## Measurements taken off the locked PNG

Image 04 is a 1365px frame. Scanning each row for the near-white card surface
(253,253,253) against the cool canvas (247,248,250):

| | authority | built at 1440 |
|---|---|---|
| workbench | x287–1087, 800px = **58.6%** | **58.6%** |
| left rail | 223px = 235 CSS px | 235px |
| right rail | 200px = 211 CSS px | 211px |
| gap, rail → workbench (left) | 42px = 44 CSS px | 44px |
| gap, workbench → rail (right) | 53px = 56 CSS px | 44 + 12 margin = 56px |
| page margin | 24 / 27px | 25px |

The unequal gaps are the authority's, reproduced the way finding R1 established:
the smaller value on the grid's column gap and the difference on the rail's own
margin. Image 04 puts the response rail CLOSER to the workbench than the
evidence rail, which is the reverse of image 03 and reads correctly — the
response panel is where the member acts and the evidence panel is where they
check.

**One measured discrepancy is reported rather than resolved.** The locked
`00-READ-ME-FIRST.md` states a "uniform 12-pixel card spacing" and the
architecture repeats it; measured off the PNG, image 04's own card gaps are
23–27px in a 1365 frame, i.e. ~24–28 CSS px at 1440. The build ships the
written rule (`--os-card-gap: 12px`, which is also what OS-1 and OS-2 ship
throughout the room). Changing a locked written rule is not a writer's
decision — see `OS-3_COMPLETION_REPORT.md` section 5.

## Responsive sweep

`document.scrollWidth <= document.clientWidth` at every one of 320, 360, 390,
430, 480, 560, 640, 700, 768, 900, 1024, 1100, 1200, 1280, 1366, 1440 and 1600.
No element forces a horizontal scroll at any width.
