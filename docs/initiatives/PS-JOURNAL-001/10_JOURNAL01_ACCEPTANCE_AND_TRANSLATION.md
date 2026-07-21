# PS-JOURNAL-001 — JOURNAL-01 Acceptance and Image→Architecture Translation

**Accepted by:** Peter Carter (owner), 2026-07-21 — one-word acceptance
("Accepted") of the merged light/dark JOURNAL-01 pair, with the designated
manager (Claude Code / Fable) concurring.
**Accepted asset:** `visual-authority/accepted/journal-v1-01-owner-journal-light-and-dark.png`
(supersedes the matrix's single-image stable name `journal-v1-01-owner-journal-desktop.png`; this accepted asset is the light+dark pair)
**Scope of acceptance:** JOURNAL-01 (the owner Journal opening view), light and
dark, as the **working visual direction** for the J1 frontend. Screens 02
(composer desktop), 03 (composer mobile), and 05 (saved-with-options) are still
in generation and require their own acceptance. Round 2–4 state coverage (per
`03_SCREEN_SET_AND_STATE_MATRIX.md`) remains open.

This document is the **binding translation contract**: what the build must take
from the image, and what it must replace with the real product. The implementer
builds from THIS document plus the accepted image — never from the image alone.

## 1. BINDING — the build must match or exceed

| Element | Requirement |
|---|---|
| Bound-book character | Page-edge/ribbon/clasp framing; the Journal reads as a premium bound memoir, light "day" and dark "lamplight" as the same book |
| Contents rail (left) | Chapters 01–06: Timeline, Voice, Photos, Videos, Milestones, Reflections — each with its one-line subtitle. These are **local views/filters of the Journal page** (site rule 22 / PS-JRN-JRN-007), styled as book contents. They must NOT be global navigation or new routes |
| Editorial date numerals | Large "20 / MAY" date blocks as the timeline's left rhythm |
| This-season hero | Member photo, a short season line, and quiet totals ("128 moments · 27 voice notes · 14 milestones"). Totals are lifetime/season counts — never streaks, resets, points, or guilt framing (site rule 24) |
| Mixed-media rows | Voice = playable gold waveform + duration; photo = true-color image prominent; video = thumbnail + play; milestone = gold star marker; text = serif reflection treatment |
| Per-row privacy cue | Every Moment shows "Private" with a lock, not color-only |
| Handwritten warmth | Occasional gold handwritten annotation ("Proud of this one" ⭐) and the footer line "Every moment today becomes tomorrow's legacy." Subtle, sparse |
| Palette discipline | Deep Navy Gold only. No purple/pink/teal/neon anywhere |
| One dominant flow | Single vertical reading order; no grid of equal tiles in the default Timeline view |

## 2. REPLACED — placeholder elements the build must swap for the real product

| In the image | In the build |
|---|---|
| Top nav "Home / Journal / Slate / Connections", search/bell icons, avatar menu | The real authenticated shell. Route/nav labels come from the route map once approved through doc 07's gate (currently a proposal; recommends `/app/journal`, not yet locked) — the image's nav is explicitly non-binding placeholder chrome |
| Rendered fonts | Real Newsreader (display/serif) + Inter (UI) per the Design Bible |
| Rendered colors | Exact Deep Navy Gold tokens (`#132447/#203767` navy, `#F6F7FA/#FFFFFF` light stage, `#B87900`/`#8A5A00` gold) and the approved Layered Ink dark tokens; contrast-checked (gold on white is large-text/UI only; body text uses text-safe values) |
| "Maya Thompson" fixture, sample stats, motto copy | Real member data; the season line is member-authored/curated copy, never AI-imposed |
| Any implied behavior | The locked architecture controls: private by default, derived membership, no Add-to-Journal, authorization before retrieval |

## 3. ADDITIONS the image does not show

Items 1, 2, 6, and 7 are **hard requirements**. Items 3, 4, and 5 are **banked
directions** — approved intent whose specific visuals must still pass their own
visual gate before implementation treats them as accepted style.

1. **Text-only rows.** Real text Moments will usually have no image. Use the
   serif reflection treatment alone (as in earlier accepted batches); never
   decorative stock imagery.
2. **Manage view + search.** The Manage (dense list/search/filter/edit/archive/
   export) view and the Journal search field from earlier rounds remain
   requirements (PS-JRN-JRN-005/006) even though this hero image omits them.
   Timeline chapter = this accepted view; Manage = the working view.
3. **Empty/first-Moment state.** Banked direction: a warm illustrated
   "the trail starts here" empty state leading to Capture a Moment (from the
   exploration round). Required before pilot (PS-JRN-JRN-014).
4. **Photos/Videos chapter views.** Banked direction: the media bento/grid
   treatment is appropriate INSIDE the Photos/Videos chapters only — never the
   default Timeline.
5. **Kind icon language.** The circular kind icons (mic/pen/camera/film/star)
   from the exploration round may mark Moment kinds, with accessible names.
6. **Accessibility non-negotiables.** Semantic chronological order; keyboard
   operability including waveform play controls; visible focus; 200% zoom
   reflow; reduced-motion variant; screen-reader labels for every control;
   long-content, loading, partial, and error states (PS-JRN-JRN-014 and doc 02's accessibility section for the Journal view;
   PS-JRN-CAP-014 applies to the Capture action/composer).
7. **Performance.** Keyset pagination against `usp_ListJournalMomentsForOwner`
   ("Load more moments" maps to the cursor); bounded first paint on multi-year
   histories.

## 4. Status ledger

| Screen | Status |
|---|---|
| JOURNAL-01 light + dark | **Accepted 2026-07-21 (this record)** |
| 02 composer desktop | In generation |
| 03 composer mobile | In generation |
| 05 saved-with-options | In generation |
| 04 neutral saved-minimal | Adjusted per doc 08 (origin moved from a mocked My Story to Journal/Home); its purpose — proving Save does not auto-insert into any destination — is retained. 05 was added alongside it, not as a replacement; both remain required Round-1 saved-state screens |
| Round 2–4 state coverage | Open; required before the frontend passes its visual gate |

The J1 frontend implementation brief may be drafted against this contract but
implementation of the composer/saved states must not finalize until 02/03/05
are accepted.
