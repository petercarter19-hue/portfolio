# PeerSlate Completion & Handoff Report — PS-VOICE-VISUAL-PARITY-001

## A. Status

- **Package:** PS-VOICE-VISUAL-PARITY-001 — Voice visual-parity correction
- **Status:** Complete (implementation, tests, and evidence). **Not merged** —
  awaiting Pete and ChatGPT Work real-visual acceptance per role boundaries.
- **Branch and commit:** `work/2026-07-19-voice-visual-parity-001`, pushed to
  `origin`. Design-instructions checkpoint at `0158daf22d26e7c38be494e2b32e6b51fdaca0fb`;
  implementation commit follows this report (exact SHA in the next message).
- **Base:** `origin/main` at `eede8565d703a466bd788962d494e8b385b53409`
  ("PS-VOICE-001 private Voice Capture") — verified via `git merge-base
  --is-ancestor`, not assumed.
- **PR / pipeline / environment:** No PR opened. Claude does not merge,
  deploy, or provision infrastructure per role boundaries.
- **Production state:** Not deployed. Nothing in this package has touched
  production.
- **Visual authority and status:** In Review. Authority: the approved
  homepage Voice walkthrough (`/feed-living-stream?state=voice` /
  `?state=review`) plus four committed real production mobile screenshots
  (`docs/initiatives/PS-VOICE-VISUAL-PARITY-001/visual-authority/`).
  Implementation evidence is in
  `docs/initiatives/PS-VOICE-VISUAL-PARITY-001/evidence/` with a full
  parity/deviation matrix at `PARITY_MATRIX.md`.
- **Pete / ChatGPT Work visual acceptance:** Not yet recorded. This report
  and its evidence are the submission for that review.

## B. What changed technically

**Files touched** (all within the assigned writable scope):
- `templates/owner_capture.html` — full rewrite of the capture-mode chooser,
  the recording modal, and the review stage. Backend contract untouched: same
  route (`owner.capture`), same `voice_draft` fields consumed
  (`state`, `source_key`, `provider_transcript`, `row_version_token`,
  `attempt_number`), same form actions/hidden fields/required-checkbox name
  (`confirm_voice`) on the real save action, same `max_body_length`/
  `max_voice_bytes`/`max_voice_duration_seconds` context variables. Six inline
  SVG icon macros added (mic, close, lock, spark, photo, video, document) —
  presentational only, no new template variables.
- `static/css/owner-app.css` — Voice-scoped selectors only (`.owner-app__voice-*`,
  `.owner-app__capture-methods`, `.owner-app__method`; confirmed via repo-wide
  grep that none of these classes are used on any other page). Adds: the
  recording-modal shell and sub-state visuals (ready/requesting/recording/
  processing/error), the two-column review grid with a right-rail audience/
  destination "capability preview" pattern, a body-level portal/backdrop
  (`#voice-overlay-root`, `.owner-app__voice-backdrop`), mobile bottom-sheet
  rules (`@media max-width:540px`), a native-`<details>`-based "More ways to
  use this" mobile disclosure, dark-theme accents, and an expanded
  reduced-motion block.
- `static/js/owner-capture-voice.js` — the existing recording lifecycle
  (`startRecording`/`uploadRecording`/`cancelRecording`/`chooseMimeType`/
  `formatTime`) is unchanged in behavior; added: a generic portal-to-`<body>`
  helper with focus trap, `Escape`-to-dismiss, and scroll lock; a `ready`
  sub-state before `requesting`; auto-open of the review stage when a
  `voice_draft` is server-rendered (guarded so the recording modal does not
  also auto-open in that case — see bug fixes below); mobile-only collapse of
  the "More ways to use this" disclosure via `matchMedia`.
- `tests/test_owner_voice_ui.py` — every previously-asserted string/contract
  is preserved verbatim (permission-after-explicit-start, failure/denial
  copy, retry/delete copy, mobile/reduced-motion/focus-visible/resize-vertical
  markers, homepage-authority strings). One assertion is revised with owner
  sign-off (see below); four new tests added for capability-preview
  disablement, explicit private-status copy, dialog/portal semantics, and the
  mobile sticky-save/progressive-disclosure pattern.
- New, non-code: `docs/initiatives/PS-VOICE-VISUAL-PARITY-001/PARITY_MATRIX.md`,
  `DESIGN_INSTRUCTIONS.md` (already committed as the pre-implementation
  checkpoint, now updated with owner resolutions), `evidence/*.png` (19
  screenshots), `visual-authority/*.png` (4 committed real screenshots).

**Test-contract revision (owner-approved in advance, design doc §7.5/§8.3):**
`test_mobile_focus_reduced_motion_and_document_flow_are_scoped` no longer
asserts a blanket absence of `position: fixed`. It now asserts that every CSS
rule using `position: fixed` is scoped to `.owner-app__voice-backdrop`
specifically (via regex over the stylesheet), preserving the original intent
(no incidental fixed-position layout elsewhere) while permitting the one
overlay that genuinely needs it.

**Why the overlay needs `position: fixed` at all:** `templates/base.html`
renders page content inside `<main id="main-content" class="main-content">`,
and `static/css/style.css` sets `.main-content { position: relative;
isolation: isolate; }`. `isolation: isolate` unconditionally creates a new
CSS stacking context (independent of `position`/`z-index`), and the sticky
global header (`.global-header { position: sticky; z-index: 1200; }`) sits in
the *parent* stacking context with an explicit positive stack level. Because
`.main-content`'s own box has no explicit `z-index` (it participates in the
parent context at stack level 0), nothing painted inside its stacking
context — including a deeply nested `position: fixed` element with an
arbitrarily high `z-index` — can paint above the header, regardless of that
z-index value. This was verified directly against the current CSS (not
assumed from memory), and the same conclusion is recorded as
`reference-modal-stacking-context` in project memory, first hit in an
unrelated Projects Board modal. The fix: `owner-capture-voice.js` moves
(`appendChild`) the recording modal and, when present, the review stage into
a dedicated root appended to `<body>`, so they compete in the root stacking
context instead.

**Two real bugs found and fixed during headless verification (not in the
current evidence, both covered by re-run screenshots):**
1. `.owner-app__voice-confirm { flex: 1 1 20rem; }` sizes that block's
   **width** in the desktop row-direction footer. The mobile media query
   switches the footer to `flex-direction: column`, which silently
   re-interpreted the same `flex-basis` as a 320px **height**, collapsing the
   transcript textarea and leaving a large blank gap above the sticky Save
   button. Fixed with a mobile-scoped `flex: 0 0 auto` reset.
2. Modern Chromium's native `<details>` collapse state is implemented via an
   internal `::details-content` pseudo-element that ordinary class-based CSS
   cannot force open once collapsed. The original approach (closed by
   default, CSS-forced open at desktop widths) silently rendered the entire
   audience/destinations rail as zero-height on desktop. Fixed by rendering
   `<details open>` by default (works with or without JavaScript, every
   viewport) and having JavaScript remove the `open` attribute specifically
   at mobile widths via `matchMedia`, rather than fighting the browser's
   internal sizing with CSS.
3. (Found alongside the above) The recording modal auto-opened by default
   (existing, tested behavior) *and* the review stage separately auto-opened
   whenever a `voice_draft` was present, stacking two backdrops. Fixed by
   skipping the recording modal's auto-open when a review stage exists.

**Final pre-handoff review pass (2026-07-19), additional fixes:**
4. **Modal focus-trap leak (accessibility).** The focus trap counted content
   inside a closed `<details>` as focusable (`content-visibility:hidden` is
   invisible to `offsetParent`) and ignored keyboard-focusable `<summary>`
   elements, so it miscomputed its first/last boundaries and could let focus
   escape the modal. Fixed by using `HTMLElement.checkVisibility({
   contentVisibilityAuto: true })` and adding `summary`/`audio[controls]` to
   the focusable set; re-verified live that Tab/Shift+Tab wrap correctly and
   the disabled capability previews stay out of the tab order. New test
   `test_focus_trap_accounts_for_summary_and_content_visibility`.
5. **Purposeful initial focus.** `data-autofocus` now lands focus on the mic
   ring (recording) and the transcript textarea (review) instead of the Close
   button.
6. **Stale error-state evidence corrected.** The committed CSS already hid the
   waveform/timer in the recording modal's error state, but the first-pass
   `desktop-12`/`desktop-13` screenshots were captured before that rule landed
   and showed the wave. All 19 screenshots were re-captured against the final
   committed code so the evidence and code agree.
7. **Asset cache-bust bumped.** The `owner-app.css`/`owner-capture-voice.js`
   query string moved from `?v=ps-voice-001-1` to
   `?v=ps-voice-visual-parity-001` so returning users' browsers fetch the
   rewritten assets rather than a cached prior version on deploy.

## C. What this means in plain English

The private Voice Capture screen a member actually sees when they record or
review a note has been rebuilt to look like the polished demo you and
ChatGPT approved on the homepage, instead of the plain form it looked like
before. Recording now opens as a focused, centered dialog with a big
microphone circle, a live waveform, and a timer — the same visual language as
the homepage walkthrough. Reviewing a transcript now shows a two-column
layout with the transcript on one side and, on the other side, a preview of
where a Capture could eventually go (Connections, Community, My Story, Slate
Board, Résumé) and what it could eventually attach (a photo, video, or
document) — all of that is visibly there for context, but every one of those
buttons is genuinely disabled and clearly marked "Coming later," so nothing
pretends to work that doesn't. The one real, working action stays "Save
private Capture." On a phone, the screen is redesigned specifically for a
phone — not a squeezed desktop layout — with the transcript and a
persistently-visible Save button up top, and everything about future features
tucked behind a small "More ways to use this" expander.

## D. What the website or member can do now

**Live/working, unchanged from before:** recording (after an explicit Start
click asks for microphone permission), the 3-minute/20MB limit, upload,
server-side transcription, editable transcript review, the immutable
original-provider-transcript disclosure, audio playback and download, retry
on a stuck/failed transcription, deleting a private draft, and the single
explicit **Save private Capture** action. Text Capture remains fully
available and unchanged.

**Visible but genuinely inert (new in this package):** Connections,
Community, Selected people, My Story, Slate Board, Résumé, Photo, Video,
Document attachment, and "AI-assisted wording" all render with the
walkthrough's visual weight and a "Coming later" tag, but every one is a real
HTML `disabled` control — not clickable, not focusable, not submittable. No
backend exists for any of them yet; nothing about this package changes that.

**Did not change:** backend routes, SQL, Blob/Speech behavior, authentication,
lifecycle contracts, or anything outside `templates/owner_capture.html`,
`static/css/owner-app.css` (Voice-scoped rules only), and
`static/js/owner-capture-voice.js`.

## E. How this connects to PeerSlate

This corrects the visual-acceptance withdrawal recorded against
`PS-VOICE-CAPTURE-MANAGER-001`/`PS-VOICE-001`: the backend and lifecycle were
already accepted technically, but the UI did not match the bound visual
authority (`docs/governance/OWNER_VISUAL_INTEGRITY_STANDARD.md`'s "Private
Voice Capture" binding). It does not change the Capture-to-Moment model, the
private/public boundary (Capture stays private-only end to end), or any
downstream consumer. The capability-preview pattern is built exactly to the
owner's 2026-07-19 instruction so that later packages (Story, Slate Board,
Résumé placement, Connections, Community, attachments, AI-assisted
publishing) can each be activated independently later without another visual
rebuild of this screen — none of those are activated or backed by real
authorization now.

## F. Verification and validation

**Automated tests:** `tests/test_owner_voice_ui.py` (13/13 pass, focused
Voice contract); full repository suite `python -m unittest discover -s tests`
— 397 tests, `OK (skipped=1)`, run from a local venv with the repo's own
declared `requirements.txt` installed (this machine had neither
`flask_limiter` nor `azure-storage-blob` installed globally; both are already
in `requirements.txt`, so this is environment setup, not a new dependency).
Guardrail suites `tests/test_site_rules.py` and
`tests/test_governance_pointers.py` are included in that run and pass.

**Visual verification:** the in-app Browser pane's screenshot capture timed
out consistently (a known, previously-documented pattern in this project when
the host machine is idle — compositor frames aren't produced, though DOM
reads/JS execution work normally). Verified instead with headless Playwright
against the real running Flask app (`app.py`, unmodified), with the same
three call sites `tests/test_owner_voice_capture.py` already mocks
(`owner_routes.get_current_identity`, `owner_routes.database_service.first_result`,
`owner_routes.voice_capture_service.get_draft`) patched to fixture data —
the template, CSS, and JS rendering path is exactly what production serves.
19 named screenshots plus a full parity/deviation matrix are in
`docs/initiatives/PS-VOICE-VISUAL-PARITY-001/` (see §A and `PARITY_MATRIX.md`).
Real device/UI states verified: desktop recording (ready + listening),
desktop review, Type/opening, long transcript, upload/failure/retry states,
keyboard focus, reduced motion (verified via computed
`animation-duration: 0s`, not just visually), 200% zoom/reflow, dark theme,
microphone denied, unsupported browser, and purpose-designed mobile
(recording, review collapsed, review expanded, long transcript).

**Not verified:** a live end-to-end recording → real Azure Speech
transcription → review round trip (no Azure SQL/Speech credentials in this
environment, and Claude does not request or handle those per repository
policy). The server-rendered review branches are proven via the same mocking
seam the existing test suite already uses. Landscape mobile orientation was
not separately captured.

**Visual authority comparison:** see `PARITY_MATRIX.md` for the full
dimension-by-dimension comparison and every intentional deviation with its
reason. Headline deviations: a pre-recording "ready" sub-state (permission
timing), a static reflective prompt instead of a live transcript during
recording (truthfulness — no client-side speech API), navy (not marigold)
primary/selected color reconciled to the current Deep Navy Gold system per
owner instruction and confirmed against real production mobile screenshots,
and the capability-preview treatment for every not-yet-backed feature.

## G. Known gaps, risks, and exclusions

- **Not merged.** This branch must not be merged until Pete and ChatGPT Work
  review the actual implementation (not just this report) and accept it
  visually, per role boundaries in the task instructions.
- **Opening behavior — one judgment call for ChatGPT to confirm.** On a plain
  `/app/capture` load with JavaScript, the recording modal auto-opens over the
  page (faithful to the accepted "voice is the production-intent opening path"
  from PS-VOICE-001, and it gives immediate visual parity with the
  walkthrough). Type stays first-class as the "Switch to Type" action inside
  the modal and via dismissing. The trade-off: on that cold load — and again
  after a save redirects back — the recent-captures list and any "Saved
  privately" confirmation sit behind the modal until it is dismissed. This was
  deliberately **not** changed here, because altering the accepted opening
  default is outside a visual-parity correction and would invalidate the
  evidence set; it is surfaced for ChatGPT (the visual authority) to confirm
  or redirect. An alternative — landing on the Speak/Type chooser and opening
  the modal on the Speak click (closer to the homepage hero's click-to-enter
  pattern) — is a small change if preferred.
- The two desktop screenshots shown earlier in chat (marigold-toned) could
  not be committed as durable evidence — they arrived as inline chat content
  with no underlying file path. If exact-pixel desktop authority images are
  wanted beyond the walkthrough source and the four committed mobile shots,
  they need to be supplied as actual files.
- Review-dismissal copy ("Close keeps your private draft; resume any time
  from this page" behavior, no literal on-screen copy added for it) was
  implemented as designed but not separately re-confirmed in writing; flagged
  in the design doc §8 for a final wording pass if Pete wants a change.
- No production dependency was added. `flask_limiter`/`azure-storage-blob`
  were already in `requirements.txt`; a local `.venv` (gitignored, not
  committed) was created solely to run the existing test suite and a
  Playwright-based screenshot harness in this environment.
- A placeholder `ANTHROPIC_API_KEY` value was set as a transient process
  environment variable (never written to disk, never a real credential)
  purely to satisfy an unrelated import-time guard in `app.py` so the full
  test suite could run; this machine has no real key configured at all.

## H. Clear next step

Pete and ChatGPT Work review `PARITY_MATRIX.md` and the screenshots in
`docs/initiatives/PS-VOICE-VISUAL-PARITY-001/evidence/` against the named
visual authority, and record visual acceptance (or requested changes) per
`docs/governance/OWNER_VISUAL_INTEGRITY_STANDARD.md`'s V3 gate. This unlocks
opening the Azure DevOps PR and the standard merge/deploy/verify flow (owned
by the manager, not Claude). In parallel, Pete can confirm or amend the two
open items already flagged in `DESIGN_INSTRUCTIONS.md` §8 (review-dismissal
copy wording; whether exact-pixel desktop screenshots should still be
supplied as files).

## I. What Pete needs to do or decide

- Review the evidence and either accept the visual result or state what to
  change.
- Optional: confirm the review-dismissal copy, or supply the two desktop
  mockup images as actual files if pixel-exact desktop color/typography
  matching (beyond the walkthrough source and the four real mobile
  screenshots already used) is wanted.
