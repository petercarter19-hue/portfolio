# PS-VOICE-VISUAL-PARITY-001 — Parity / Deviation Matrix

Visual authority: the approved homepage Voice walkthrough
(`/feed-living-stream?state=voice` and `?state=review`, source inspected at
`static/js/feed-living-stream.js` / `static/css/feed-living-stream.css`) plus
four production mobile screenshots committed at
`docs/initiatives/PS-VOICE-VISUAL-PARITY-001/visual-authority/`.

All screenshots referenced below are in
`docs/initiatives/PS-VOICE-VISUAL-PARITY-001/evidence/`, captured headless
(Playwright, Chromium) against the real templates/CSS/JS with fixture data
standing in for the database — the render path (Jinja, `owner-app.css`,
`owner-capture-voice.js`) is exactly what production serves.

## Recording modal — desktop

| Dimension | Walkthrough | Implementation | Verdict |
|---|---|---|---|
| Silhouette/composition | 760px white card, blurred navy backdrop, centered | 46rem (~736px) white card, blurred navy backdrop (`desktop-01-recording-ready.png`) | Match |
| Dominant object | 128px radial-navy mic ring | 128px (8rem) radial-navy mic ring, doubles as the Start control | Match |
| Hierarchy | Title → ring → state text → prompt → wave/timer → actions | Same order | Match |
| Typography | Newsreader h2 26px; serif stage text 26px | Newsreader h2 25.6px (1.6rem); serif prompt 25.6px | Match |
| Actions | Cancel (white) + Stop and review (navy fill) | Cancel (white) + Stop and review (navy fill), both disabled pre-recording | Match |
| Color | Navy ring/wave/buttons | Navy ring/wave/buttons (`desktop-02-recording-listening.png`) | Match |
| Listening state | Animated wave, live timer | Animated wave, live timer counting from a real `MediaRecorder` | Match |

## Recording modal — truth-safe deviations (documented, approved)

| Deviation | Reason | Evidence |
|---|---|---|
| "Ready" sub-state precedes "Listening" | Microphone permission may only be requested after an explicit start (existing tested contract); the walkthrough opens directly into a simulated Listening state | `desktop-01-recording-ready.png` |
| Serif prompt slot shows a static reflective prompt, not a live word-by-word transcript | Real transcription happens server-side after upload; a browser-side live transcript would send audio to a third-party speech API mid-recording, contradicting the "nothing is shared" promise shown in the same modal | `desktop-02-recording-listening.png` |
| Error states (denied / unsupported / offline / too large) render inline in the modal's status region | The walkthrough has no failure states to compare against (it's a scripted simulation); composition, color, and dismissal affordances otherwise match | `desktop-12-microphone-denied.png`, `desktop-13-unsupported-browser.png` |

## Review stage — desktop

| Dimension | Walkthrough | Implementation | Verdict |
|---|---|---|---|
| Silhouette/composition | Wide card, `1fr + 265px` two-column grid, footer spanning both | 63rem card, `1fr + 17rem` grid, footer spans both (`desktop-04-review.png`) | Match |
| Main column order | Transcript → provider text (n/a in mockup) → AI proposal → attach row | What you said → transcript → provider disclosure → AI card → attach row | Match (provider disclosure is additive, see deviations) |
| Right rail | Audience radio group → "Also connect to" chips | Same, plus "Coming later" tags | Match + truth labels |
| Footer | Meta text + primary button | Required confirm checkbox + Save private Capture | Match in position/weight; content adapted (see deviations) |
| Typography/spacing/color | Field labels 11px uppercase muted; navy selected-state; marigold AI-card accent | Same values ported from `feed-living-stream.css` | Match |
| Long content | Not demonstrated in the walkthrough | Textarea grows via `resize:vertical`; card scrolls internally past `92vh` | Verified, no walkthrough baseline to compare |

## Review stage — truth-safe deviations (documented, owner-approved)

| Deviation | Reason | Evidence |
|---|---|---|
| Primary button and every "selected" state are **navy**, not the marigold shown in two desktop images pasted into chat | Owner instruction: "merge with current color schemes." The four **committed, real production** mobile screenshots (`visual-authority/approved-mobile-0{1,2,3}-*.png`) show navy in this exact composition today; `feed-living-stream.css`'s own dark-theme rules keep primary actions navy as well. The marigold-toned chat images are treated as a superseded/alternate pass, not color authority | `desktop-04-review.png` vs. `visual-authority/approved-mobile-02-review-audience.png` |
| Private-status banner ("This Capture is private and visible only to you.") | Additive truth element; the walkthrough has no equivalent because its "Community" default audience is a demo default, not a truth boundary | `desktop-04-review.png` |
| Native `<audio controls>` element, not a custom round play-button + fabricated waveform | The custom player would need real waveform peak data extracted from the audio, which isn't available; the native control is the honest, fully-functional choice and is still wrapped in the walkthrough's pill styling | `desktop-04-review.png` |
| Every future capability (Connections, Community, Selected people, My Story, Slate Board, Résumé, Photo, Video, Document, AI wording) renders as a real, native-`disabled` control with a visible "Coming later" tag | Per owner's 2026-07-19 guidance: build the full approved composition now as capability previews, not working controls, so later packages activate them without a redesign | `desktop-04-review.png` |
| AI card carries no fabricated suggestion | The walkthrough shows a scripted AI-written post title/body; ours must never claim the system produced wording it didn't | `desktop-04-review.png` |
| "Publish update" → "Save private Capture" is the only submit action | The real product has no publishing/audience backend yet; this is the single live, tested completion action | `desktop-04-review.png` |
| Close (✕ / Escape) de-portals the review to normal in-page flow rather than discarding | The draft is real, server-persisted content (unlike the walkthrough's simulated draft); nothing is lost by closing | Verified via `document.body.style.overflow` / DOM-position checks, not separately screenshotted |

## Mobile — purpose-designed, not a compressed desktop column

| State | Evidence | Notes |
|---|---|---|
| Recording, ready | `mobile-01-recording-ready.png` | Bottom sheet, radius 22px top corners, full-width controls |
| Recording, listening | `mobile-02-recording-listening.png` | Live wave + timer, fake-mic-verified |
| Review, collapsed | `mobile-03-review-collapsed.png` | Transcript + playback first; sticky "Save private Capture" footer always reachable |
| Review, "More ways to use this" expanded | `mobile-04-review-more-expanded.png` | Audience/destination previews tucked behind one disclosure, per owner's mobile guidance |
| Review, long transcript | `mobile-05-review-long-transcript.png` | Textarea and sheet both scroll correctly |

Two bugs were found and fixed during this verification pass (not present in the final evidence):
1. A `flex: 1 1 20rem` rule on the confirm-checkbox block, written for the desktop row-direction footer, was silently re-interpreted as a 320px **height** once the mobile media query switched the footer to `flex-direction: column` — collapsing the transcript and leaving a large blank gap. Fixed by resetting `flex: 0 0 auto` in the mobile footer rule.
2. Modern Chromium's native `<details>` uses an internal `::details-content` pseudo-element for the collapsed state that author CSS cannot reliably force open; the "More ways to use this" disclosure is now server-rendered `open` by default (works with or without JS on every viewport) and JS collapses it specifically on mobile widths via `matchMedia`, rather than fighting the browser's internal sizing with CSS.

## Accessibility states

| State | Evidence | Notes |
|---|---|---|
| Keyboard focus visible | `desktop-05-review-keyboard-focus.png` | Visible focus ring on the confirm checkbox after Tab navigation from the transcript |
| Reduced motion | `desktop-10-reduced-motion-recording.png` | `animation-duration` computed as `0s` (verified via `getComputedStyle`, not just visual inspection) |
| 200% zoom / reflow | `desktop-11-review-200pct-zoom-reflow.png` | Halved logical viewport (720×450), standard technique for zoom-reflow testing without native browser zoom; content stays legible, no overlap |
| Dark theme | `desktop-09-recording-dark-theme.png`, `desktop-09b-review-dark-theme.png` | Ring/wave/focus/selected-tint shift to gold, matching `feed-living-stream.css`'s own dark-theme rules exactly; primary actions stay navy in both themes |

## Failure and recovery states

| State | Evidence |
|---|---|
| Microphone denied | `desktop-12-microphone-denied.png` |
| Unsupported browser | `desktop-13-unsupported-browser.png` |
| Upload stored, transcription not started (retry available) | `desktop-08-review-uploading.png` |
| Transcription failed with a retryable attempt | `desktop-07-review-failure-retry.png` |

## Not covered by this evidence pass

- A live end-to-end recording → real Azure Speech transcription → review round trip was not exercised (this environment has no Azure SQL/Speech credentials; per repository policy, Claude does not request or handle those). The `needs_review`/`failed`/`uploading` review states were exercised via the same mock seam `tests/test_owner_voice_capture.py` already uses (`owner_routes.voice_capture_service.get_draft`), so the server-rendered branches are proven, but the live upload→transcribe path itself is unverified beyond its existing automated test coverage.
- Landscape mobile orientation was not separately captured.
