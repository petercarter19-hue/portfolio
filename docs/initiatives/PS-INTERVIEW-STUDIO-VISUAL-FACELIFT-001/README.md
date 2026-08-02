# PS-INTERVIEW-STUDIO-VISUAL-FACELIFT-001

> **RETIRED — HISTORICAL RECORD ONLY.** Pete withdrew this material visual
> direction on 2026-08-01 before release. Do not implement the twelve
> pearl/forest-green and smoky-teal/champagne screens. PR 223 released only
> session editing in the Interview Me right rail and the Interview AI desktop
> overlap fix. The current runtime remains the released Deep Navy Gold Studio.
> See `CORRECTION_ROUND_4_COMPLETION_REPORT.md` for the controlling decision.

## Assignment and status

- **Owner and final visual authority:** Pete
- **Production-intent visual creator:** ChatGPT visual-creation lane
- **Implementation manager:** none; lane closed
- **Implementation writer:** none; the retired implementation branch was
  removed after its rejected commit was preserved under the archival tag
  `archive/interview-studio-rejected-facelift-2026-08-01`
- **Delivery path:** Protected, because this is a materially revised visual direction
- **Historical repository base:** Azure DevOps `origin/main` at
  `2494aa73ed95bfbe97d8cf42f712b9929759e0b2`
- **Package branch (deleted at closeout):**
  `codex/2026-08-01-interview-studio-visual-facelift-package`
- **Reserved implementation branch (deleted at closeout):**
  `work/2026-08-01-interview-studio-visual-facelift-001`
- **Status:** retired by Pete on 2026-08-01 before release. The twelve screens
  and the specification below are retained only as withdrawn historical
  evidence; they are not current visual authority or implementation scope.

## Outcome

Apply the approved pearl/forest-green light treatment and smoky-teal/champagne
dark treatment to the released public Interview Studio while preserving its
current routes, state machine, requests, storage, media lifecycle, privacy
truth, accessibility behavior, and natural progression.

This is a visual facelift. It is not a new Interview product, workflow,
architecture, persistence system, AI contract, or navigation domain.

## Page purpose and truth boundary

- **Audience:** public visitors using Pete's fixture-backed public profile.
- **Primary purpose:** rehearse an interview answer, request explicit content
  coaching, improve the answer, rehearse locally on camera, and inspect
  browser-local practice history.
- **Routes:** `/interview-studio` and `/interview-studio/history`, including
  the released `mode=me`, `mode=ai`, and `mode=video` behavior.
- **Dominant object by mode:** the editable answer, the source-labeled AI answer,
  the local camera stage, or the browser-local history list.
- **Primary actions:** the current state-specific explicit action. No action is
  automatic merely because the page is opened or text is entered.
- **Truth boundary:** drafts, goals, attempts, and History remain browser-local;
  media remains local and is not uploaded or analyzed; question/answer text is
  transmitted only for the released explicit request; AI output remains a
  proposal; scores remain practice signals.

## Authority and precedence

Use this order when authorities appear to conflict:

1. Current Constitution v3.0, site rules, privacy/accessibility invariants, and
   released route/request/storage/media behavior.
2. This package's state and implementation contracts.
3. The exact 12 Pete-locked PNGs under
   `visual-authority/2026-08-01-pete-lock/`.
4. The released `PS-INTERVIEW-FOCUS-UI-001` contracts for states not pictured
   by the new PNG set.

A raster typo or an illustrative raster value never changes a real label,
payload, score meaning, profile boundary, or browser-local truth. Any necessary
truth, accessibility, focus, or text-reflow adaptation must be narrow and
recorded in the completion report. A material visual substitution must stop and
return to Pete and the ChatGPT visual-creation lane.

## Locked visual direction

### Light

- pearl and soft-white sculptural stage environment;
- forest/emerald active states and primary actions;
- crisp elevated white cards with fine tactile texture;
- restrained pale-green illumination, layered shadows, and clear depth;
- charcoal text with strong contrast; and
- no beige, purple, botanical imagery, or flat generic-dashboard treatment.

### Dark

- smoky-teal studio environment rather than black or navy;
- champagne active states and actions;
- visible overhead stage lamps with soft beams;
- vertical acoustic architecture at the far sides;
- textured elevated dark cards, edge separation, and restrained floor
  reflection; and
- identical DOM, function, action order, and state to the light theme.

### Microphone and answer entry

- The centered microphone remains the emotional and functional centerpiece of
  Interview Me drafting/listening.
- Typing remains the normal path; optional dictation writes into the same
  textarea.
- The visible helper copy remains
  `TYPE OR TALK — Both build the same answer.`
- Long typed, pasted, restored, dictated, transferred, and improved content
  grows naturally without clipping or covering actions.

## Page-local navigation adjudication

The approved PNGs show a compact Interview Studio route header. Implement it
inside the Studio template and Studio stylesheet only. Do not edit or establish
a new site-wide navigation layer in `base.html`, `public-navigation.css`, or
shared shell JavaScript.

All labels must resolve to existing destinations:

| Visual label | Existing destination |
| --- | --- |
| Home | `url_for('home')` |
| My Story | `portfolio_story_url` |
| Living Résumé | `portfolio_resume_url` |
| Interview Studio | current Studio route |
| Career Impact | `portfolio_resume_url#impact` |
| Pete Carter / View public page | `portfolio_resume_url` |

The existing global header may be visually suppressed only on the two Studio
routes so the approved route-local shell is not duplicated. Existing shared
destinations, search data, other routes, and shared navigation files remain
unchanged.

## Functional lock

Preserve every capability in the released functionality matrix:

- Interview Me typing, optional dictation, same textarea, word/save state,
  explicit coaching request, processing, failure recovery, review, STAR map,
  improvement, retry, next-question, settings, queue, nudge, example, and safe
  transfer behavior.
- Interview AI question entry, optional dictation, three answer bases, explicit
  generation, source labels, evidence, no-grounding and failure states,
  follow-up continuity, and safe Practice This Answer transfer.
- Video Practice explicit media permission, device states, preview, recording,
  timer, stop/finalize, local playback, retake, discard, cleanup, transcript
  typing/paste/optional dictation, and text-only content coaching.
- History browser-local records, filters, goals, detail, written/video metadata,
  storage-unavailable state, and explicit local clear/delete behavior.
- Theme persistence, state retention, route/query behavior, direct links,
  confirmation behavior, and public demo identity truth.

Do not remove the released orientation state. It is not pictured in the new
set; preserve its current content and interaction structure while applying the
new theme and compact route shell.

## Pictured and unpictured states

The 12 PNGs are exact authority for the pictured desktop states. Unpictured
states retain current geometry and function, then inherit the closest pictured
mode's tokens, card finish, typography, spacing rhythm, and background:

- idle/empty Interview Me derives from the listening composition;
- submit processing and coaching failure remain in-place Interview Me states;
- Interview AI empty/generating/compare/no-grounding/failure retain current
  structure;
- Video permission, preview, recording, stopping, playback, retake, discard,
  and transcript-review states retain current camera-dominant structure;
- History empty, detail, filter, delete, and storage-unavailable states retain
  current list/detail structure; and
- mobile and 200% reflow preserve released order and reachable actions rather
  than shrinking the desktop canvas.

## Writable scope

Runtime:

- `templates/interview_studio.html`
- `static/css/interview-studio.css`
- `static/js/interview-studio.js` only when required to preserve existing
  handlers after a markup move; no request, storage, media, AI, scoring, or
  transition semantics may change
- `tests/test_interview_studio.py`
- a new focused visual-contract test file if useful
- `tests/test_governance_pointers.py` only to keep the control-plane date
  assertion aligned with this package activation

Package and evidence:

- `docs/initiatives/PS-INTERVIEW-STUDIO-VISUAL-FACELIFT-001/**`
- `artifacts/interview-studio-visual-facelift/**`
- `docs/governance/CURRENT_BASELINE.yaml` only for this package's current
  ownership/status and later verified release fact

## Forbidden scope

Without a new explicit owner gate, do not change:

- `app.py`, routes, API endpoints, payloads, enums, prompts, rubrics, provider
  or model strings;
- storage keys, migrations, SQL, authentication, authorization, private data,
  cloud sync, or account-backed History;
- media upload, retention, processing, transcription, or delivery analysis;
- `templates/base.html`, shared header/footer templates, shared navigation CSS
  or JavaScript, homepage runtime, Living Résumé, My Story, Career Impact,
  Community, Journal, Studio, or another lane's files;
- dependencies, deployment definitions, environment configuration, or feature
  flags; or
- new controls, renamed actions, combined actions, automatic save/publish, a
  ten-point score, or AI-generated canonical truth.

## Implementation sequence

1. Record a repository-grounded map of the current DOM hooks, JavaScript
   handlers, routes, storage keys, requests, media objects, and relevant tests.
2. Add contract tests for the locked shell labels/destinations, microphone/type
   parity, required state actions, dark/light single-DOM behavior, and truth
   copy before structural styling work.
3. Recompose the Studio-local template without changing data attributes,
   names, values, form ownership, event targets, state transitions, or hidden
   semantics.
4. Implement the light tokens and responsive geometry, then the dark token
   twin. Do not duplicate DOM by theme.
5. Verify every released mode/state, long content, direct routes, theme
   retention, permission/failure behavior, and browser-local boundaries.
6. Capture comparable 1536×1024 light/dark evidence for all 12 authorities,
   plus representative 390×844 mobile and 844×390 Video Practice landscape.
7. Perform a complete-diff self-review. Add a fresh independent reviewer only
   if implementation touches a mandatory risk trigger, evidence conflicts, or
   Pete requests one.
8. Return the implementation for Pete's browser visual acceptance. Do not
   merge or deploy from the implementation task.

## Acceptance gates

### Functional parity

- Existing focused tests pass with no weakened assertion.
- No route, request, payload, storage key, media lifecycle, score meaning, or
  privacy boundary changes.
- Direct mode/history routes and mode switching retain current behavior.
- Light/dark use one DOM and preserve state during theme changes.

### Visual fidelity

- Each pictured state is recognizably the locked screen at the same viewport.
- Light is pearl/white/forest-green with texture, elevation, and depth.
- Dark is smoky teal/champagne with visible overhead stage lights and depth.
- The primary task remains dominant; the rail stays subordinate.
- No overlap, clipping, accidental horizontal task scroll, or hidden action.

### Accessibility and responsive behavior

- Keyboard and visible focus pass for essential paths.
- Semantic headings, labels, status regions, dialogs, and hidden states remain
  valid.
- Contrast meets WCAG 2.2 AA; color is never the sole state cue.
- 200% zoom, 390×844 portrait, and 844×390 Video Practice landscape preserve
  usable order and reachable primary/destructive controls.
- Reduced motion and long content remain safe.

### Trust

- No permission request on route load.
- No audio/video upload or persistent media storage.
- No fabricated delivery analysis.
- History and goals remain browser-local with truthful unavailable/clear states.
- AI proposals remain labeled and require explicit member action.

## Homepage impact

The homepage currently presents a fixed illustrative Interview walkthrough, so
this material Studio change requires a bounded downstream parity refresh. That
work remains separate under the existing homepage Interview parity lane. No
homepage file is writable here, and the Studio implementation is not evidence
that the homepage has been updated.

## Release boundary

This activation authorizes package creation, implementation, local testing,
comparison evidence, and review. It does not authorize an Azure PR merge,
Candidate, production deployment, or live claim. Those remain separate owner
decisions after Pete sees the browser implementation.
