# Owner Visual Direction — Spectacular Mixed-Media Journal (2026-07-21)

**Owner feedback (Pete), on the first JOURNAL-01 generation:** the restrained
text-list version is "boring… terrible." The Journal must read as a **rich,
living record of a whole life** — voice notes, typed notes, photos, videos,
milestones — "like your own profile of your own life," where the owner sees
everything and later decides what others see. Spectacular, creative, warm —
**not** a legal-document list.

This direction is **binding as the richness/quality bar for all Journal visual
rounds and for the eventual build.** It does not pre-approve any specific
generated screen: every image still flows through the README's acceptance gate
(Pete + designated manager, under the Visual Integrity Standard) before it
becomes accepted visual authority. The earlier restraint list (no dashboard, no social feed, no KPI grid)
still applies — richness and restraint together: *a beautifully bound memoir,
not a busy feed.*

## The required richness (every future Journal visual round)

1. **Mixed-media timeline, not a list.** Each Moment kind has its own
   treatment: voice = warm card with playable waveform + duration; photo = the
   image is the hero, beautifully framed; video = thumbnail + play; milestone =
   gold-marked timeline marker; text = the serif quote treatment.
2. **Chapters like a bound book.** Month/season headers with a one-line summary
   band ("May — 12 moments · 3 wins · 1 milestone").
3. **A living opening ("This season").** Latest voice note ready to play,
   latest photo, quiet momentum cue — something alive above the fold. This is
   private self-record surfacing of the owner's own items only — never an
   activity/engagement feed, and never streak/points/reset framing (site
   rule 24).
4. **Human touches.** A whisper of the Slate Board's handwritten warmth: a
   small annotation, a pinned "moment that mattered." Subtle, never scrapbook.
5. **Meaningful gold.** Marigold does real work (kind markers, waveforms,
   milestones), not decoration.
6. **Whole life, not an HR file.** Fixtures mix personal and work moments.

Still prohibited: like counts, comments, followers, engagement bait, KPI card
grids, identical-tile grids. Privacy cues stay on every Moment.

## The decoupled generation workflow (owner decision, 2026-07-21)

ChatGPT generates from **one long self-contained prompt with minimal context**
(no repo files needed). It is free to invent placeholder chrome — its header,
side-nav, and labels are **explicitly non-binding placeholders**, because it
cannot see the live site and the signed-in route map is an open decision.

After Pete accepts an image, the architect/manager (Claude Code) writes an
**image→architecture translation** before any implementation:

| From the accepted image | Binding? |
|---|---|
| Composition, hierarchy, mixed-media treatments, chapter rhythm, mood, richness | **Yes — match or exceed** |
| Placeholder header/side-nav/chrome, invented labels or routes | No — replaced by the real product shell, approved labels, and the approved route map |
| Exact hexes/typography as rendered | No — replaced by the real Deep Navy Gold tokens and Newsreader/Inter |
| Any implied social/public behavior | No — architecture rules control |

The translation doc + the accepted images together form the visual authority
for the build. Generated screens remain references, never shipped UI.

The one-shot generation prompt currently in use is preserved below for reuse.

---

<details>
<summary>One-shot JOURNAL-01 prompt (self-contained, 2026-07-21)</summary>

Design one premium product-UI concept image. 16:10 widescreen, approx 1440x900,
full-screen application composition — no laptop frames, no hands, no marketing
collage, no photoreal office.

THE PRODUCT: "Journal" — the private, personal record at the heart of a
professional-growth platform called PeerSlate. It is the owner's complete life
record: voice notes, typed reflections, photos, videos, and milestones, all on
one beautiful timeline. Private by default — only the owner sees it. It should
feel like a beautifully bound, living memoir: cinematic, editorial, warm,
premium. NOT a social feed, NOT a dashboard, NOT a to-do app.

VISUAL WORLD: deep navy architectural frame (#132447–#203767 range) around a
warm ivory reading stage; marigold-gold accents (#B87900 family) used
meaningfully (milestones, waveforms, markers — not decoration); elegant serif
display type for moment text (Newsreader-like); clean humanist sans for
controls; generous space; quiet glass/material depth. Premium restraint with
real richness — think a luxury print magazine meets a personal archive.

THE PAGE MUST SHOW, top to bottom:
1. A minimal app shell: "Journal" heading, a lock icon with "Private to you",
   one gold "Capture a Moment" button, and small "Timeline | Manage" view
   controls. Keep any left nav abstract and understated — it is a placeholder,
   not final navigation.
2. A living opening band called "This season": the newest voice note with a
   playable gold waveform, the newest photo as a small hero, and a quiet
   momentum line ("12 moments · 3 wins · 1 milestone").
3. A mixed-media chronological timeline under an elegant month header ("May"),
   with 6–7 moments of VISIBLY DIFFERENT kinds, each with its own treatment:
   two voice notes (waveform, duration, play), one photo moment (photo is the
   hero), one video moment (thumbnail + play), one milestone (gold star marker,
   "Passed the PMP exam"), two short typed reflections in the serif treatment.
   Mix personal AND work life — this is a whole life, not an HR file.
4. One or two warm human touches: a small handwritten-style annotation or a
   pinned "moment that mattered" star. Subtle, not scrapbook.

RULES: every moment shows a tiny "Private to you" cue; no like counts, no
comments, no followers, no KPI cards, no grid of identical tiles; short, real,
legible interface text only — no lorem ipsum; one dominant vertical reading
flow. Fictional owner: "Maya Thompson".

Bottom-left corner, outside the product frame, small caption:
"Production-intent concept — Journal is not currently live."

</details>
