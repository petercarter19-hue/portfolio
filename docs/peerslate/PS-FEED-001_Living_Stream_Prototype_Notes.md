# PS-FEED-001 — Living Stream Feed Prototype (Fable deliverable)

**Route:** `/_internal/feed-living-stream` (state map at `/_internal/feed-living-stream/states`)
**Source package:** `PeerSlate_Feed_Vision_Handoff_v1` (Bible v1.1 → Feed Implementation Brief v1)
**Status:** connected clickable prototype, fixture data only. No database, no persistence,
no production navigation changes. Gated like the other internal previews: always available on
local hosts; a deployed review environment opts in with `ENABLE_FEED_PROTOTYPE=1`
(or the existing `ENABLE_DESIGN_SYSTEM_PREVIEW=1`). Production stays closed by default.

## What is implemented (and what is not)

- **Implemented (prototype behavior):** all 16 production mockup states as one connected
  experience — stream, gallery, video, conditional Catch Up rail, voice listening with live
  transcript, transcript review, AI-assisted publish review, audience selection,
  keep-private versus publish, conversation detail with useful replies and Offer Help,
  caught-up, loading, error/retry, tablet, and mobile (bottom-sheet capture and review).
- **Fixture-only:** every author, post, comment, transcript, AI proposal, confidentiality
  result, and Catch Up summary. Publishing only updates the in-page fixture stream.
- **Requires backend/schema work (deferred to the Codex phases):** real Journal projection,
  server-side visibility rules, media storage/renditions, actual voice transcription, AI
  calls, comments, saves, follows, and the unseen-updates signal that decides when the
  Catch Up rail earns its place.

## Page/state map

| # | Mockup | In the prototype |
|---|--------|------------------|
| 01 | Desktop default | Default view; no rail; stream centered |
| 02 | Photo/gallery | `?state=gallery` |
| 03 | Video | `?state=video` |
| 04 | Catch Up rail | `?state=rail` (rail only renders when unseen updates exist; default has none, so none shows) |
| 05 | Voice listening | `?state=voice`, composer mic, Capture button, mobile Capture |
| 06 | Transcript review | `?state=review`, or “Stop and review” |
| 07 | AI publish review | `?state=publish`, or “Publish update” from 06 |
| 08 | Conversation detail | `?state=detail`, or Comment on any post |
| 09 | Caught-up | `?state=empty`, or the Following tab |
| 10 | Loading | `?state=loading` (held); shown briefly on load and retry |
| 11 | Error recovery | `?state=error`; “Try again” really retries |
| 12–16 | Tablet/mobile | Same states at ≤1100px / ≤700px viewports |
| 17 | Component anatomy | Inventory below |
| 18 | Responsive map | Behavior table below |

## Component inventory (mockup 17)

One post shell renders every content shape; media/actions are slots, not variants.

- **Shell:** app shell grid, sidebar nav, topbar (search, Capture), mobile top bar,
  mobile bottom nav with central Capture.
- **Feed header:** editorial page title, subtitle, `For You`/`Following` tablist.
- **Post:** `postHTML()` = identity row (avatar, name, context dot + kind, time, audience),
  title/copy, media slot, provenance linkline, action row (Encourage/Celebrate, Comment,
  Save — Save right-aligned and private).
- **Media:** landscape image with badge, video (overlay gradient, play, caption, duration),
  1–3 image gallery, voice player (play, waveform, duration).
- **Capture/review:** voice dialog (listening ring, live transcript, level meter,
  Cancel/Stop), review dialog (editable transcript, PeerSlate proposal with chips,
  confidentiality notice on the AI step, audience radio group, connect-to chips,
  footer with trust line and primary action).
- **Conversation:** back link, detail post, comment thread, comment actions
  (Encourage/Reply/Offer help), reply composer with voice entry.
- **Utility/states:** Catch Up rail panel + AI-summary note, honest skeletons,
  caught-up terminal state, error panel that preserves cached content.

Design tokens are ported 1:1 from `specs/design_tokens.json` into
`static/css/feed-living-stream.css` custom properties.

## Responsive behavior (mockup 18)

| Viewport | Navigation | Stream | Rail |
|----------|-----------|--------|------|
| >1100px | Full sidebar + topbar | 790px readable column | Conditional Catch Up only |
| ≤1100px (tablet) | Icon rail | Single centered stream | Removed |
| ≤700px (mobile) | Compact top bar + bottom nav, Capture central | Full-width, document flow | Removed; dialogs become bottom sheets with sticky publish action |

Removing the rail recenters the stream — no reserved empty column.

## Accessibility and motion

- Real buttons/links everywhere; visible `:focus-visible` rings; skip link;
  44px minimum touch targets on mobile.
- Tabs are a `tablist` with roving tabindex and arrow-key navigation.
- Dialogs: `role="dialog" aria-modal`, focus trapped, `data-autofocus` on the meaningful
  control, Escape cancels safely, focus returns to the invoking control.
- Audience options are native radios (arrow-key operable); state changes are announced
  through a polite `aria-live` region (listening, saved, published, refreshed, errors).
- All fixture images carry alt text; video/voice controls are labeled with duration.
- `prefers-reduced-motion`: transcript renders instantly, waveform and cursor stop,
  transitions and smooth scrolling are removed. Skeletons are static (no shimmer).

## Intentional deviations from the supplied mockups (and why)

1. **Fonts:** the mockup renders fell back to Georgia/Helvetica; the prototype loads the
   approved Foundation C faces (Newsreader for editorial headings, Inter for interface),
   matching `specs/design_tokens.json` and the Design Bible rather than the render artifact.
2. **06 → 07 as a two-step flow:** “Publish update” on *Review before saving* advances to
   the *AI-assisted publish review* (confidentiality check) instead of publishing directly,
   because the brief requires the confidentiality cue and explicit approval before
   publication. Publishing happens only on the second, explicit confirmation.
3. **“Save privately” label:** when *Keep private* is selected, the primary action renames
   itself and nothing enters the Feed — making the privacy rule visible instead of implied.
4. **Saved state feedback:** Save toggles to “Saved” (still private to the viewer);
   Encourage shows a quiet pressed state with no public counts.
5. **Provenance on published fixture posts** includes “AI-assisted draft” in the linkline so
   the AI-assistance state stays inspectable in the stream.
6. **Simulated playback:** video and voice play controls announce that playback is simulated
   rather than pretending to stream media (no fake success).
7. **Search field is presentational** in the prototype; wiring it to product search is a
   build-phase decision, per the brief’s “ship now / do not ship now” table.
8. **Sidebar labels** use the mockup’s Home/Journal/Feed/Board/Work/Studio and link to the
   closest existing routes (`/`, `/the-slate/my-slate`, `/slate-board`, `/work`,
   `/interview-studio`). The real navigation mapping is a Codex planning-phase task; this
   prototype adds no production navigation.

## Next steps (not part of this deliverable)

- Codex planning phase: repository audit + `docs/initiatives/PS-FEED-001/` work package
  (the handoff’s `work_package_template/` is copy-ready once the audit is approved).
- Backend phases 2–8 in the brief: projection + authorization first, then core stream,
  interaction, voice/AI, optional rail, hardening.
