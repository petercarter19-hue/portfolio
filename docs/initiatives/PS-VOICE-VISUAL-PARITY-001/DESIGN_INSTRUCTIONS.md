# PS-VOICE-VISUAL-PARITY-001 — Design Instructions

_Claude Code frontend lane. Drafted 2026-07-19 for Pete (owner) and ChatGPT Work
(manager/visual authority) review. No implementation begins until both approve
this document or amend it._

- **Branch:** `work/2026-07-19-voice-visual-parity-001`
- **Worktree:** `C:\Users\peter\Documents\portfolio-voice-visual-parity`
- **Base:** `origin/main` at `eede8565d703a466bd788962d494e8b385b53409` (verified tip, "PS-VOICE-001 private Voice Capture")
- **Governing standard:** `docs/governance/OWNER_VISUAL_INTEGRITY_STANDARD.md`

## 1. V0 — Authority and truth boundary

### 1.1 Named visual authority

1. The approved homepage Voice walkthrough — the simulated flow the homepage
   hero (`templates/partials/homepage/_voice_hero.html`) links into:
   - `/feed-living-stream?state=voice` — recording overlay
     (`openVoiceOverlay()` in `static/js/feed-living-stream.js:544`)
   - `/feed-living-stream?state=review` — review overlay
     (`reviewOverlayHTML()` in `static/js/feed-living-stream.js:609`)
   - Styles: `static/css/feed-living-stream.css:280–344` (overlay, modal,
     listening stage, review grid) and `:433–446` (mobile bottom sheet).
2. The approved Voice screenshots. **Resolved 2026-07-19:** four production
   mobile screenshots (Safari, `peerslate.com`, live `/feed-living-stream`) are
   committed at
   `docs/initiatives/PS-VOICE-VISUAL-PARITY-001/visual-authority/approved-mobile-0{1..4}-*.png`.
   They show the recording/listening modal, the review stage's audience rail,
   the review stage's attach/connect row, and the Feed entry point — all in
   **navy** primary/selected treatment, matching the current
   `feed-living-stream.css` exactly. Two desktop screenshots were also shown
   in chat (recording + review, in a **marigold-toned** treatment that does not
   match current code) but arrived as inline chat content with no underlying
   file path, so they could not be copied into the repository as binary
   evidence; only the committed mobile set and the inspectable walkthrough
   source are durable V0 authority. See §8.2 for how the color discrepancy
   between the two desktop images and the four mobile images is resolved.

### 1.2 Truth boundary (what is live vs. presentation)

| Element | Status in this package |
|---|---|
| Recording, mic permission after explicit start, 3-min/20 MB limits | Live (unchanged JS contract) |
| Upload → server-side Azure Speech transcription → review | Live (unchanged routes/lifecycle) |
| Audio playback + download, editable transcript, immutable provider transcript | Live (unchanged) |
| Retry, delete draft, deletion-pending recovery | Live (unchanged) |
| **Save private Capture** (sole completion action) | Live (unchanged) |
| Audience choices other than Keep private; Connections/Community/Selected people | **Presentation-only capability preview — disabled, labeled "Coming later"** |
| + My Story, + Slate Board, + Résumé destination chips | Capability preview — disabled, "Coming later" |
| Photo / Video / Document attachments | Capability preview — disabled, "Coming later" |
| AI-assisted wording card | Capability preview — no fabricated suggestion, "Coming later" |
| Publishing | Not present as an action; nearby copy: "Publishing and audience choices are coming later." |
| Live streaming transcript during recording | **Not implemented and not simulated** (see §4.1) |

Frontend capability flags are presentation controls only. Backend authorization
still governs every action; toggling a browser flag must never grant access.

### 1.3 Dominant object / dominant action per state

| State | Dominant object | Dominant action |
|---|---|---|
| Opening | Capture stage with Speak + Type first-class | Start speaking (Type equally reachable) |
| Recording | Focused modal: listening ring + serif prompt | Stop and review |
| Processing | Same modal, quieted | (wait; status announced) |
| Review | Focused review stage, transcript column | **Save private Capture** (gold-highlighted primary; see §8 Q2) |
| Failure/retry | Review stage with alert composition | Retry / Switch to Type |

### 1.4 Out of writable scope

Backend routes, SQL, Blob/Speech services, authentication, lifecycle
contracts; global header/nav/theme; `chatbot.js`/`chatbot.css`; the feed
walkthrough itself; any non-Voice section of `owner-app.css`. Writable:
`templates/owner_capture.html`, Voice-scoped selectors in
`static/css/owner-app.css`, `static/js/owner-capture-voice.js`, focused Voice
UI tests, this initiative's evidence.

## 2. Shared visual system (extracted from the walkthrough)

Voice-scoped custom properties, defined once on the Voice stage root (values
identical to `#feed-app` tokens):

```
--pv-navy: #203767;        --pv-navy-strong: #132447;
--pv-ink: #101b30;         --pv-text: #1B2C47;      --pv-muted: #6F7F99;
--pv-line: #DDE4F0;        --pv-line-soft: #E8EDF5;
--pv-cloud: #F6F8FC;       --pv-marigold: #B87900;
--pv-shadow-2: 0 24px 70px rgba(17,31,68,.16);
--pv-serif: "Newsreader", Georgia, "Times New Roman", serif;
--pv-ease: cubic-bezier(.2,.8,.2,1);
```

Key measurements to reproduce exactly (light theme):

| Element | Spec (from feed-living-stream.css) |
|---|---|
| Backdrop | `rgba(8,18,37,.42)` + `backdrop-filter: blur(8px)` |
| Modal card | `min(760px, 100vw−48px)`, white, radius 28px, shadow-2, 1px `rgba(255,255,255,.8)` border |
| Modal head | 22/25/17px padding, bottom hairline `--pv-line-soft`; h2 Newsreader 26px/600 ink; 38px close button, radius 12px |
| Listening ring | 128px circle, radial navy gradient (`#203767 → #3a5aa0 → #DFE6F5 → #F5F7FC`), shadow `0 20px 55px rgba(32,55,103,.25)`, white mic glyph |
| "Listening…" | 21px/800 ink; help 13px `#76869D` |
| Serif stage text | Newsreader 26px/1.45 `#273852`, max-width 620px, min-height 112px |
| Waveform | 46px tall, 4px bars, radius 3, navy gradient, 5-step height rhythm, animated only while genuinely recording |
| Cancel / Stop | 46px buttons, radius 14px; Stop = navy fill/white 800; Cancel = white, `--pv-line` border, `#687891` |
| Review grid | `minmax(0,1fr) 265px`; main 24/26/27px; side `#F8FAFE` with left hairline |
| Field label | 11px uppercase, ls .9px, `#8A99AE`, 800 |
| Transcript box | radius 15px, 15/16px padding, `#35465F` 14px/1.55, min-height 112px; focus ring `#B9C2F5` + 3px `rgba(79,91,213,.14)` |
| Privacy option | radius 12px rows, selected `#EDEFFF`, 17px custom radio, navy dot |
| Chips | pill 999, 6/9px, `#EEF1F8`/`#5B6B82` 10px/750 |
| Proposal card | radius 16px, `#FBFCFF`, `#DDE2F7` border |
| Review footer | full-width row, top hairline, meta 11px `#7A899F`, primary right-aligned |
| Motion | overlay ease-in .22s; wave ~.9s alternate; all off under reduced motion |

Dark theme (`body[data-theme="dark"]`): ring and wave shift to the gold ramp
(`#d8a928/#e3b83a/#f5e7b6`), focus rings gold — mirror the feed's dark rules
with Voice-scoped selectors.

## 3. Desktop composition, state by state

### 3.1 Opening (Capture page)

Keep the existing page frame ("Private owner workspace" / Capture). Replace the
plain Type/Speak toggle + inline stage with a walkthrough-grade opening:

- One dominant capture stage card. Serif prompt "What happened today that you
  may want to remember?" over the waveform motif (idle, static).
- Two first-class choices side by side: **Talk about what happened** (mic icon,
  navy primary) and **Type it instead** (equal-size secondary). Neither is
  hidden or demoted; Voice may be visually emphasized per the standard.
- Choosing Talk opens the focused Voice modal (§3.2). Choosing Type reveals the
  existing server-rendered form, restyled to the shared system (labels,
  transcript-box input, primary button) — its POST behavior is untouched.
- Existing status strings ("Ready. Microphone access has not been requested.",
  noscript fallback, "Text Capture is always available") are preserved.

### 3.2 Recording modal (parity target: `?state=voice`)

Portal-mounted overlay (see §6.1) with the exact modal card spec from §2.

- Head: Newsreader h2 **"Talk about what happened"** + close ✕.
- **Ready sub-state** (truth adaptation — the walkthrough opens mid-listening,
  the real product must ask permission after an explicit start): identical
  composition; ring is the start control, label **Start recording**; help text
  "Your browser asks for microphone permission when you start. Everything
  stays private until you explicitly save."
- **Listening sub-state:** ring in listening treatment; "Listening…" 21px;
  help "Speak naturally. You review everything before anything is saved.";
  serif stage slot shows the reflective prompt (not a fake transcript, §4.1);
  live waveform + timer `0:32 / 3:00` (tabular numerals); actions centered:
  **Cancel** + **Stop and review** (navy primary, autofocus).
- **Processing sub-state:** ring quiets to breathe animation, title
  "Preparing your private draft…", help "Uploading the private recording,
  then transcribing it. Keep this page open."; actions disabled; `role=status`
  announcements preserved.
- Errors (denied/unsupported/offline/too large) render in-modal in the status
  slot with the alert treatment and a first-class **Switch to Type** action;
  existing message strings preserved verbatim (tests assert them).

### 3.3 Review stage (parity target: `?state=review`)

The server still redirects to the Capture page with `voice_draft` rendered.
With JS, that markup is presented as the focused review stage over the same
backdrop, auto-opened on load; without JS it renders inline as the identical
composition in document flow (§6.2).

- Head: Newsreader h2 **"Review before saving"** + close ✕ (close ≠ discard:
  the private draft is kept; the page shows a **Resume review** affordance).
- Immediately under the head, a private-status line (marigold-accented chip +
  copy): **"This Capture is private and visible only to you."**
- **Main column** (order):
  1. Field label "What you said"
  2. Audio player pill — walkthrough's voice-player composition (round play
     button, wave, duration) driving the **real** `<audio>` element; native
     controls remain the no-JS fallback; **Download original audio** stays.
  3. Editable transcript in the transcript-box treatment (autofocus,
     resize: vertical, grows for long content).
  4. **View original provider transcript** disclosure, restyled to the shared
     system; provenance copy unchanged ("This provenance record is
     immutable…").
  5. **AI card** — proposal-card shape and hierarchy, but truthful:
     head "✦ AI-assisted wording — coming later"; body "Your original
     transcript will always remain unchanged. Future suggestions will require
     your approval." No fabricated suggestion, no fake chips.
  6. **Add to this Capture** row — Photo / Video / Document as capability
     previews (§5); the real recording appears as a live attach-chip
     ("Your recording · 1:12") that is informational, not removable here.
- **Right rail** ("Who can see this?"):
  - **Keep private** — selected, active, real (maps to the existing hidden
    confirm semantics; the explicit-consent checkbox contract is preserved,
    presented as the selected private option + confirm control per current
    template requirements).
  - Connections / Community / Selected people — capability previews, disabled,
    "Coming later".
  - "Also connect to": + My Story, + Slate Board, + Résumé — capability
    previews, disabled, "Coming later".
  - Rail footnote: "Publishing and audience choices are coming later."
- **Footer:** meta "This Capture is private and visible only to you." · left;
  **Delete private draft** stays reachable via its existing guarded disclosure
  (not in the footer); primary right-aligned: **Save private Capture**
  (see §8 Q2 for navy vs gold). "Keep editing"-style dismiss returns to page.

### 3.4 Failure / recovery states

`uploading`, `queued`, `processing`, `failed` (±attempt), `deletion_pending`,
`confirmed` keep their exact current copy and `role="alert"`/`role="status"`
semantics, presented inside the same review-stage composition with the status
line in the alert treatment and **Retry transcription** as the stage primary
where the state allows it. No state loses its escape hatch (retry, delete,
Switch to Type).

## 4. Truth-safe adaptations (documented deviations from the walkthrough)

1. **No live transcript.** The real pipeline transcribes server-side after
   upload; browser SpeechRecognition would send audio to a third-party service
   and is prohibited by the privacy claims. The serif stage slot keeps the
   walkthrough's typographic composition but shows the reflective prompt.
   Deviation class: truthfulness (explicitly permitted by the standard).
2. **Ready sub-state before Listening.** Permission is requested only after an
   explicit start (tested contract). Same composition, one extra beat.
3. **Publish → Save private Capture.** The walkthrough's audience-dependent
   primary is replaced by the single live action; audiences become previews.
4. **AI proposal card carries no fabricated output.**
5. **Provider-transcript disclosure and draft-delete guard are additive** —
   truth elements the walkthrough lacks; styled to the shared system.
6. **Close keeps the draft.** The walkthrough's Escape discards a simulated
   draft; the real draft is server-persisted, so dismissal never destroys it.

## 5. Capability-preview component (build once, activate later)

A single Jinja macro + CSS pattern used by every future affordance:

```
{{ capability_chip(kind='audience'|'destination'|'attachment'|'ai',
                   label='Community', state='unavailable') }}
```

- Renders the walkthrough's real silhouette (privacy-option row, destination
  chip, pill button, proposal card) so later activation is a state flip, not a
  redesign.
- Genuinely disabled: `disabled` + `aria-disabled="true"`, excluded from the
  form, no pointer affordance, reduced-contrast-but-AA text, small lock/clock
  glyph, visible **Coming later** tag (not tooltip-only).
- Screen-reader text: "Community — coming later. Not yet available."
- One `data-capability` map in the template mirrors the manager's flag list
  (`community, connections, selected_people, story, slate_board, resume,
  attachments, ai_proposal, publication` → `unavailable`); presentation only.

## 6. Mobile (purpose-designed, parity target: walkthrough ≤640px)

### 6.1 Recording — bottom sheet

Full-width sheet, radius `25px 25px 0 0`, max-height 92vh, backdrop above
everything: head 18/18/14, h2 22px, ring 105px, serif prompt 21px (min-height
96px), waveform + timer, Cancel / Stop and review full-width-friendly.

### 6.2 Review — progressive disclosure sheet

Single column, internal scroll (max-height ~92vh):

1. "Review before saving" + private-status line.
2. Playback pill, then editable transcript (readable, full-width).
3. Provider-transcript disclosure.
4. **More ways to use this** — collapsed accordion containing audience
   previews, destination chips, attachments, and the AI card (all §5 states).
5. **Sticky footer** with **Save private Capture** always visible (persistent
   primary action); safe-area padding; the meta line collapses.

Retry/failure states use the same sheet with the alert composition and the
state's action as the sticky primary. Landscape and 200% zoom reflow to the
same single column.

## 7. Engineering constraints

1. **Portal the overlay to `<body>`.** `.main-content` sets
   `isolation: isolate` (style.css:340–343), which traps `position: fixed`
   overlays beneath the sticky header. `owner-capture-voice.js` moves/creates
   the overlay root as a direct child of `<body>`; no-JS keeps everything in
   document flow.
2. **Ask Pete widget** is fixed at z-index 998/999. Voice overlay z-index 1300
   covers it; scroll is locked and background marked `inert`/`aria-hidden`
   while the stage is open. In the no-JS inline layout, Voice-scoped bottom
   clearance keeps the save footer clear of the launcher at mobile widths.
   `chatbot.*` files are not modified.
3. **Focus management** per the walkthrough: trap within the dialog,
   `role="dialog" aria-modal="true"` + `aria-labelledby`, Escape dismisses
   (draft kept), focus returns to the invoker; `data-autofocus` on the state's
   primary.
4. **Reduced motion:** no wave/breathe/overlay animation; instant transitions.
5. **Test contracts.** Focused Voice UI tests are updated deliberately:
   - `tests/test_owner_voice_ui.py:65` (`assertNotIn("position: fixed",
     STYLES)`) is revised — fixed positioning becomes allowed **only** for the
     Voice overlay block; the mobile document-flow intent is re-asserted by
     checking the no-JS inline layout and scoped selectors instead.
     Requires manager sign-off (listed in §8).
   - Every asserted string in `test_owner_voice_ui.py` (permission, failure,
     retry, provenance, "Save private Capture", Type/Speak, prompts) is
     preserved verbatim in the new markup.
   - New focused tests: capability previews render disabled and outside the
     form; overlay portals to body; private-status copy present; sticky mobile
     primary exists; reduced-motion guard.
   - Guardrails `tests/test_site_rules.py` and
     `tests/test_governance_pointers.py` must stay green; full suite runs
     before handoff.
6. **CSS scoping:** all new rules under `.owner-app__voice*` /
   `.owner-voice-stage` prefixes in `owner-app.css`; no global selectors, no
   edits outside the Voice block.
7. **Assets:** Newsreader/Inter already load via the base page; no new
   external dependencies.

## 8. Owner decisions

**2026-07-19 — Pete approved this document as written** ("we approve -
implement this. merge with current color schemes. I signoff") and provided
the four production mobile screenshots now committed under
`visual-authority/`. Resolutions below.

1. ~~Approved screenshots~~ — **Resolved.** Four real mobile screenshots
   committed (§1.1). Desktop authority remains the inspectable walkthrough
   source (§2–3), since the two desktop images shown in chat had no file path
   to commit.
2. ~~Primary button color~~ — **Superseded by the binding manager correction.**
   This original design checkpoint resolved the action to navy, but
   `06_VISUAL_PARITY_CORRECTION.md` later required the Voice Save action to use
   an accessible gold treatment in both themes. The final accepted
   implementation follows that correction: Save is gold; other primary actions
   remain navy; ring, waveform, focus, and selected accents retain their
   Deep Navy Gold semantics. This note preserves the decision history without
   presenting the earlier navy-Save direction as current authority.
3. **Test-contract revision** in §7.5 (scoped `position: fixed`) — approved by
   implication of "implement this."
4. **Review dismissal copy** — "Close keeps your private draft; resume any time
   from this page." is rendered literally and was accepted at V3 on 2026-07-19.

## 9. Evidence plan (V2)

Named screenshots (Playwright headless, per the overnight-verification
practice): desktop 1440×900 and mobile 390×844 for — opening (Speak+Type),
recording ready, listening, processing, review, review long transcript,
mic denied, unsupported browser, upload failure, retry states, keyboard focus
visible, reduced motion, 200% zoom reflow, dark theme ring/wave. Each pairs
with its walkthrough counterpart in a parity/deviation matrix covering
silhouette, hierarchy, dominant action, typography, spacing, color semantics,
density, interaction states, mobile behavior, focus, zoom, motion, and
failure/recovery, with §4 deviations cross-referenced. Handoff follows the
required format; no merge request until Pete and ChatGPT Work accept the real
visuals.
