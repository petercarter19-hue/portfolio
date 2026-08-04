# PS-OPPSLATE-001 slice OS-2 — committed visual evidence

Captured 2026-08-03 on branch `work/2026-08-03-opportunity-slate-os2`, after
the branch was reconciled onto the shipped slice OS-1 and its Review
Requirements screen was taken through the owner's visual-parity method
(`OWNER_VISUAL_REVIEW_2026-08-03.md`).

## This set REPLACES the earlier OS-2 capture

The previous twenty-eight frames in this directory were captured before two
things happened to the code they photographed:

1. **Slice OS-1's owner-directed visual pass merged** (PR 250) — a three-level
   elevation scale, a deeper canvas gradient, the off-white `#fcfbf8`
   workbench with procedural paper grain, restored decorative props, narrowed
   rails, per-screen workbench proportions and the `--os-neutral-ink` contrast
   split. Every earlier OS-2 frame was shot on the surface that pass replaced.
2. **This parity pass** then changed the Review Requirements screen itself.

Frames of a screen whose stylesheet has since changed are not evidence of
anything, so they were removed rather than carried forward with a caveat.
Nothing in this directory predates the current branch tip.

## Capture conditions

| | |
|---|---|
| Harness | Headless Chromium via Playwright, driven from the repository `venv`. Scripts live in `artifacts/2026-08-03-os2-visual-parity/` and are untracked |
| Server | The real Flask app served from this worktree by `werkzeug.serving.make_server` on `127.0.0.1:5731` |
| Flag | `PEERSLATE_OPPORTUNITY_SLATE_ENABLED = True` (it ships **default off**) |
| Spend guard | `PEERSLATE_OPPSLATE_DAILY_AI_CEILING = 500` (it ships **default 0**) |
| Rate limiting | Disabled for capture only |
| Templates / CSS / JS / shell | Real and unmodified, including `base.html` |
| Viewports | 1440x1100 desktop, 390x900 mobile, 320x820 narrow, 640x1040 for the 200% zoom frame |
| Theme | Light. The room is `color-scheme: light` by design (handoff §14-M8) and the site-wide dark theme is paused (PR 262) |

### What is real, and what is replayed

**The AI output in these frames is genuine model output.** It was generated
once against the live Anthropic API through this slice's actual prompt
contracts and validators, saved, and replayed during capture so the
screenshots are reproducible and the capture itself makes no network call.
The mock boundary is the transport client and never a validator: the real
request shape, the real prompt contracts and the real validation all ran.

- AI step 1 on a deliberately mis-captured source: **3 concerns**, from
  `claude-haiku-4-5-20251001`, contract `os-source-concerns-v1`.
- AI step 1 on the clean source: **0 concerns** — the correct answer for
  cleanly captured wording, and the reason the "None flagged" state exists.
- AI step 2: **22 statements**, from `claude-sonnet-5`, contract
  `os-statements-v1`, classified 6 required / 4 preferred / 9 responsibility /
  3 informational.

**The employer source is capture input, not product content.** It is a full
Systems Engineer role description carrying the six required qualifications
image 03 displays, pasted by the harness exactly as a visitor pastes a role,
plus a variant with a truncated sentence, a bullet that lost its object and a
requirement split by a stray line break. Nothing about it is seeded,
hardcoded or shipped; the product reads whatever text the visitor brings.

**The member-mode frames use a stubbed store.** The signed-in room needs a
database this machine does not have, so `opportunity_slate_service` is
replaced with a stub returning the same real proposal the public mode
replays, and identity resolution is stubbed to a member. Routes, view models,
templates, CSS and JS are the real ones. The public-mode frames use no stub
beyond the replayed transport — they are the real anonymous flow, driven
through the real UI from paste to confirmed requirements.

## Files

### Review Requirements, the parity screen (image 03)

| File | What it shows |
|---|---|
| `compare-03-review-requirements.png` | **The comparison sheet: locked authority left, real build right**, both at the same panel width. This is the sheet the parity claim rests on. |
| `member-05-review-requirements-desktop-1440.png` | The screen, signed in, at 1440. |
| `member-05-review-requirements-mobile-390.png` | 390. Rails stack; the table restacks to one small card per statement. |
| `member-05-review-requirements-narrow-320.png` | 320. |
| `public-05-review-requirements-desktop-1440.png` | The same screen in the anonymous public mode, with the truthful banner and the AI-transit sentences. |
| `public-05-review-requirements-mobile-390.png` | 390, public. |
| `public-05-review-requirements-narrow-320.png` | 320, public. |
| `compare-06-requirements-phone.png` | The 390 frame beside the desktop authority. There is no mobile authority (§14-M9), so the question this sheet answers is whether it reads as the same product, not whether it matches a frame that does not exist. |
| `compare-07-requirements-narrow.png` | The same for 320. |
| `member-08-review-requirements-200pct-zoom-640css.png` | 200% zoom, expressed as a 640px CSS viewport (WCAG 1.4.4). |

### Selection, and the interpretation tree

| File | What it shows |
|---|---|
| `member-06-selected-statement-desktop-1440.png` | A selected statement: the cobalt row outline, the dashed connector across to the rail, and the rail showing that statement's reading. |
| `detail-selected-statement-rail.png` | The rail alone — the quoted statement, the classification select, the Path A / OR / Path B tree, its plain-language explanation, the clarify field and the two actions. |
| `detail-statement-group-card.png` | One group card at reading size: title, count pill, the three row columns and the full-height rule before the review control. |

### The extraction-concern card, populated

| File | What it shows |
|---|---|
| `member-04-extraction-concerns-desktop-1440.png` | Review Source with three real concerns. The margin card takes the authority's amber treatment and names each flagged phrase; the correction cards sit in the reading column, where a textarea has room, with the employer's original wording read-only above the member's editable correction. |
| `detail-extraction-concern-card.png` | The card alone: "3 phrases flagged", each quoted phrase with its status, and the model and contract named. |

### Read-only while a request is in flight (image 08)

| File | What it shows |
|---|---|
| `public-08b-correction-rail-read-only-desktop-1440.png` | A correction genuinely in flight. |
| `detail-correction-rail-read-only.png` | The rail alone: the amber "Corrections are paused while PeerSlate is working. Cancel to keep editing." notice, the classification select and the clarify field disabled but **visible**, the member's own text preserved, Apply correction disabled — and **Cancel live and fully contrasted**. |
| `compare-08-analysis-read-only.png` | Authority 08 beside the build. **This compares a rule, not a composition** — see below. |

**Read this comparison as a rule check, not a parity check.** `compare-08` is
the one frame in this set that is not a composition comparison. It asks a
single question — does the build obey image 08's **read-only-while-working
rule**: controls visibly disabled rather than hidden, the member's own work
preserved on screen, and exactly one live escape? — and the answer is yes.
It does **not** claim that the build reproduces image 08's layout, and the
two frames are not expected to look alike. There is no parity finding, met or
missed, hiding in the difference between them.

**Why the compositions differ: image 08's centre belongs to OS-3.** Image
08's centre carries an evidence-alignment progress card ("Preparing your
evidence alignment", "Checking authorized evidence", "Preparing the evidence
map") and an "Analyzing…" primary. That is the slice OS-3 alignment run.
Slice OS-2 has no analysis engine, so **none of that card is built, and that
is correct rather than missing**: no stage of it is named anywhere in this
room, nothing on screen implies it is coming in this slice, and the primary
says exactly what pressing it does. Building it would have been the
fabrication, not the omission. It is scoped to OS-3 and will be compared
against image 08's composition there.

**Where that treatment lives.** The rail lock is a property of the room
script's own fetch, which is the anonymous transport. The signed-in path is a
progressive-enhancement form post that navigates, so there is no in-flight
state to photograph there. The frame is therefore public-mode, which is where
the behaviour actually is.

### The honest states

| File | What it shows |
|---|---|
| `member-07-requirements-confirmed-desktop-1440.png` | Checkpoint 2 confirmed. The banner states what was and was not done, and the next control is honestly inert with the reason beside it: the alignment comparison does not exist yet. |
| `public-09-interpretation-failure-desktop-1440.png` | AI step 2 refused by the provider. Confirmed inputs are preserved, nothing partial is shown, and no result is invented. |
| `detail-interpretation-failure-card.png` | The failure card at reading size: "We couldn't read the employer's statements. / Your confirmed source is unchanged. / Public session · Nothing was generated or stored." Produced by making the provider genuinely unreachable, so the real route contract ran — not by stubbing the response. |

## Measured parity, image 03 against the build at 1440

Both sides measured the same way: the authority by scanning the locked PNG row
by row for its warm panel surface against the cool canvas, the build by
`getBoundingClientRect` in the real browser.

| | authority (1448px frame) | build (1440px viewport) |
|---|---|---|
| Workbench | x269–1105, 837px, **57.8%** | x267–1098, 831px, **57.7%** |
| Right rail | x1131–1407, 277px | x1123–1400, 277px |
| Left rail ink | x45–225, 181px | x40–221, 181px |
| Left gap to workbench | 44px | 46px |
| Right gap to rail | 25px | 25px |
| Group card columns | 64.6% / 26.1% / 9.3% | 66% / 24% / 72px |
| Row height, one line | 65px | 63px |
| Row height, two lines | 84px | 84px |
| Group header | 46–48px | 46px |

The three implemented screens now hold three different proportions, each
measured off its own image rather than shared: intake 53.3%, review 64.6%,
requirements 57.7%. `test_each_screen_carries_its_own_layout_proportion`
locks all three to the conditions that select their partials.

## Accessibility and reflow

Checked on the real rendered screen in **both modes** at 320, 360, 390, 430,
480, 560, 640, 700, 768, 900, 1024, 1100, 1200, 1280, 1366, 1440 and 1600 —
34 mode/viewport combinations, all clean.

| Check | Result |
|---|---|
| Horizontal overflow | None. No element's right edge crosses the viewport at any width in either mode |
| Text contrast (1.4.3) | No failures. Every text pair meets 4.5:1, or 3:1 where it qualifies as large text |
| Target size (2.5.8) | No focusable target below 24x24 CSS px at any width |
| Heading order | Exactly one `h1` per state: `h1` Review · Requirements → `h2` Employer statements → the group and statement structure below it |
| Honesty strings | "Nothing is saved yet" (member) / "Nothing is stored" (public), the model-and-contract attribution, and the "does not save the slate or produce qualification results" sentence present at every width |
| Forbidden strings | No score, percentage, ranking, recommendation or candidate verdict anywhere, at any width, in either mode |

## Known deviations from image 03, named

- **A model-provenance line the authority does not draw.** Below the
  statement table the build adds one muted line the locked composition has no
  equivalent for: `Proposed by claude-sonnet-5 · contract os-statements-v1 ·
  read from Source Version 1`. The same line, without the source-version
  clause, sits at the foot of the extraction-concern card on Review Source.
  **This is a visible addition to a locked composition and is named here so
  it is accepted or rejected deliberately, not by omission.** It exists to
  serve the AI-proposes-people-decide invariant: the member is being asked to
  confirm an interpretation, and confirming one honestly means being able to
  see that a model produced it, which model, under which prompt contract, and
  which version of their own source it was read from. Without the line, the
  proposal reads as though the room simply knows these things. It is set in
  the muted help style so it recedes below the content, adds no control and
  no colour, and takes the same treatment already shipped elsewhere in the
  room; the hierarchy and dominant action are unchanged. If Pete would rather
  it were placed differently, worded differently, or carried somewhere other
  than the canvas, that is a visual-authority revision and returns to the
  ChatGPT creation lane — but it should not simply be deleted, because
  something has to carry the provenance.
- **Three chips, not five.** The authority's context strip carries Role and
  Employer. Neither is a fact this room has — nothing in the source is
  labelled as the role title or the employer name, and inventing them would
  be fabrication — so the strip renders the three chips that are true. The
  same decision OS-1 recorded for image 02.
- **"Review · Requirements" wraps to two lines** in the left rail where the
  authority holds it on one. Our display face is about 25% wider per
  character than the mockup's, so fitting it on one line at 181px would need
  type smaller than the rail's own body copy and would invert the hierarchy.
  The same deviation OS-1 accepted and composed on image 02.
- **The primary reads "Confirm requirements", not "Confirm requirements and
  analyze".** There is no analysis engine in this slice; the button says what
  pressing it does. The footer truth sentence differs for the same reason.
- **The informational-statement count differs from the authority's** because
  it is real model output on a real role description rather than a drawn
  number.
- **The dashed connector renders only above 1200px**, where the rail is
  actually beside the workbench. Below that the rail stacks under it and a
  line pointing rightwards would point at nothing; the relationship is
  carried at every width by `aria-current` on the selecting control and by
  the fragment link it addresses.

## What is not here, and why

1. **No reduced-motion frame.** The room has no at-rest motion on these
   screens, so a still frame could not differ. The CSS rule is the evidence.
2. **No dictation frame.** Every microphone in the room is still honestly
   inert on these surfaces; the shared dictation module landed as OS-5 and is
   not wired here.
3. **No production frame.** Nothing in this slice is deployed. The room is
   flag-off in production and the OS-2 schema revision is not applied.
