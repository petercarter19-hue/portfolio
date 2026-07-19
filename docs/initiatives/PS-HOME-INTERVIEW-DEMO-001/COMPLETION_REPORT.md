# PS-HOME-INTERVIEW-DEMO-001 — Owner Technical Completion Report

## 1. Status and identifiers

- Package: PS-HOME-INTERVIEW-DEMO-001
- Status: **Accepted, deployed, and verified live for the fixed illustrative
  walkthrough. Writer self-review: Pass. Manager result: Pass for the current
  demonstration; Downstream Package Required for final 5A/5C homepage parity.**
- Branch: `work/2026-07-19-home-interview-demo-001`
- Worktree: `C:\Users\peter\Documents\portfolio-home-interview-demo`
- Base: `origin/main` @ `31864e43287d7cefb5a0d1c0441e94bec0bd6b1f`
- Architecture commit: `9c4b1e4`; first implementation (inline): `db01e2a`;
  final clean pushed source tip:
  `90d035a25344c850e6ed732c1efb6e4d0a240787`.
- Release: Azure PR 86; squash merge
  `a98cced519a1f853ad9f4462fd438efa67d6f260`; automatic pipeline 122
  (`20260719.30`) passed Build and Deploy for that exact merge.
- Design authority: `PS-HOME-INTERVIEW-DEMO-001_Design_Authority_Package.zip`,
  SHA-256 `968BFD9723A216939AB078C77D9725102A47746DB10D35D5DE07AEF6EEC082E3`;
  Direction A — Editorial Studio Ledger. Interaction pattern set by owner
  direction 2026-07-19 to match the Voice hero overlay (see §2).

## 2. What changed in this revision, and why

Owner feedback (Pete, 2026-07-19): the first build's inline panel-swap "wasn't
an easy walkthrough." The Voice hero's "Talk about what happened" flow — a
modal that **pops out over a dimmed backdrop and walks you through** — is the
target experience, and the Interview walkthrough should match it for
continuity.

I studied the Voice flow directly (`/feed-living-stream?state=voice`,
`static/js/feed-living-stream.js` `openVoiceOverlay` / `openReviewOverlay`, and
its overlay CSS) to capture its exact pattern: a full-viewport dimmed +
blurred backdrop, a centered white card, stages that replace content in place,
focus trap + Escape, and a bottom-sheet variant on mobile.

The scene was then reworked from inline to that pattern, keeping the visual
design and **all** fixed copy and truth labels:

- **On-page poster** (`_interview_demo_scene.html`): kicker, title, the
  question as a quoted preview, the listening line, one **"Walk me through
  it"** button, and a persistent truth bar.
- **Pop-out modal**: `role="dialog"`, `aria-modal="true"`, labelled; dimmed
  (`rgb(8 18 37 / 42%)`) + `blur(8px)` backdrop; serif title; step rail
  (Question → Sample answer → Coaching review → Improved retry); the four
  server-rendered steps (2–4 ship `hidden`); a sticky truth strip in the
  footer; Back / Next; and, on step 4, a normal Interview Studio link.
- **Portaled to `<body>`** on init, inside a `home-v3` wrapper, so it escapes
  `main.main-content { isolation: isolate }` (which otherwise traps a fixed
  overlay below the sticky global header) and covers the full viewport like the
  Voice overlay. The wrapper keeps the design-system classes/tokens resolving;
  the modal palette is pinned paper-light in both themes to match the poster.

## 3. Files changed (all within the package's writable set)

- `templates/partials/homepage/_interview_demo_scene.html` — poster + modal.
- `static/js/homepage-interview-demo.js` — open/close, portal, focus trap,
  Escape, backdrop click, step machine, method toggle. No network/storage/media
  API (grep-verified).
- `static/css/homepage-scenes.css` — overlay/modal/poster styles matching the
  Voice overlay's values; `[hidden]` guards; portaled-modal theming.
- `templates/homepage.html` — unchanged this revision (include + script tag
  from the prior commit stand).
- `tests/test_homepage_scenes.py` — tests updated for the modal structure
  (42 scene tests) including new dialog/trigger/poster-no-JS tests and an
  extended `[hidden]`-guard regression test.
- `artifacts/ps-home-interview-demo-001/` — screenshots replaced with the
  modal experience (12 PNGs).

No product Interview Studio file, `app.py`, `base.html`, global nav, shared
theme token, or governance pointer was changed (verified §7).

## 4. What visitors can do now

- See an inviting poster (the question + truth bar) in the Interview Studio
  scene, and press **Walk me through it**.
- The modal pops out and steps through Question → Sample answer → Coaching
  review → Improved retry, by Next/Back or the step rail, with the Voice/Text
  framing on step 1; step 4 links to the real `/interview-studio`.
- Operate it fully by keyboard: focus enters the modal, is trapped, each step
  announces once, Escape / close / backdrop-click dismiss and restore focus to
  the trigger.
- Without JavaScript: read the poster's question and truth bar and follow a
  normal **Open Interview Studio** link; the modal never opens and no dead
  controls appear.

## 5. Fit to authority and boundaries

- Owner interaction direction of 2026-07-19 recorded in file `01`'s amendment
  and file `02`. Truth boundary and pinned copy (file `01` §2–§3) unchanged and
  re-verified. Both owner copy corrections still hold
  (`capture, to presentation, to practice`; no invented "repeatable review
  process").
- The real `/interview-studio` package remains separate and untouched.

## 6. Verification and validation evidence

**Automated tests — green:**
```
pytest tests/test_homepage_scenes.py -q      # 42 passed
pytest tests/test_navigation.py -q            # 6 passed, 7 subtests
pytest tests/test_site_rules.py -q            # 8 passed
pytest tests/test_governance_pointers.py -q   # 14 passed, 40 subtests
pytest -q                                     # 419 passed, 1 skipped,
                                               #  171 subtests passed
git diff --check                              # clean
```
The single suite-wide failure
(`test_voice_adapters.py … azure.storage`) is pre-existing and unrelated —
`git diff` against base shows zero changes under `services/` or that test.

**Behavioral verification** (this worktree run locally on :5000; driven with a
stdlib-only Chrome DevTools Protocol client because the interactive preview
pane had an unrelated scroll/screenshot quirk this session):
- Modal closed by default (`data-int-overlay` `hidden`); open button visible,
  poster no-JS link hidden with JS.
- Open → overlay visible, `is-open` class, body scroll locked, focus on the
  step-1 heading, counter/back/next/finish states correct.
- Step Next 1→2→3→4: counters, step visibility, one live-region announcement
  per step, focus moves to each step heading, completed step aria-labels, Back
  appears from step 2, Next→Finish swap on step 4 with `href=/interview-studio`.
- Back and step-rail jump (both directions) work.
- Voice/Text toggle flips `aria-pressed` and swaps only the explanation panel;
  fixed transcript never changes.
- **Focus trap:** exactly 8 visible focusables on step 1 (after fixing the
  Back/Next/Finish `[hidden]` bug); Tab/shift-Tab wrap within the modal.
- Escape, close button, and backdrop click all close and restore focus to the
  trigger; body scroll restored.
- **Overlay covers the full viewport including the global header**
  (`elementFromPoint(200,30)` resolves to the overlay) after portaling — the
  key parity item with the Voice overlay.
- No-JS (script execution disabled): poster + Open-Interview-Studio link
  present, modal never opens, question visible.
- Dark theme: modal stays paper-light and legible; primary button is the
  theme's gold, matching the poster.

**Two bugs found and fixed during verification, each with a regression test:**
1. `.hv-int-overlay` uses `display: grid`, which outranks the UA `[hidden]`
   rule — the modal would show through its `hidden` attribute. Guarded with
   `.hv-int-overlay[hidden] { display: none }`.
2. The Back/Next/Finish controls carry the shared `.hv-btn`
   (`display: inline-flex`), same trap — they rendered even when `hidden`
   (the focus-trap check caught 10 focusables instead of 8, and shift-Tab
   landed on the "hidden" finish link). Guarded with
   `.hv-int-back/next/finish[hidden] { display: none }`.
   The `[hidden]`-guard regression test now covers all three element groups.
3. Separately, the header-coverage issue (fixed overlay trapped by
   `main.main-content { isolation: isolate }`) was resolved by portaling to
   `<body>` per the repository's modal-stacking guidance, rather than altering
   the shared isolation rule.

**Screenshot evidence** — `artifacts/ps-home-interview-demo-001/` (12 PNGs):
`poster-desktop`, `poster-desktop-dark`, `poster-mobile`, `poster-no-js`;
`modal-desktop-step1..4`, `modal-desktop-dark-step1/step3`,
`modal-mobile-sheet-step1/step3`.

**Self-review verdict: Pass.** File `01` §2 (pinned copy), §3 (prohibited
APIs), the amendment's interaction contract, and file `03` §1 (accessibility)
were re-checked against the running implementation.

## 7. Boundary confirmations

- [x] No product Studio file changed — `git diff --stat` vs base for
      `templates/interview_studio.html`, `static/css/interview-studio.css`,
      `static/js/interview-studio.js`, `tests/test_interview_studio.py`,
      `app.py`, `templates/base.html`, and `static/css/style.css`
      (the shared file that holds `main.main-content`'s isolation) is empty.
- [x] No `app.py`, `base.html`, global-nav, shared-token, deployment, or
      governance-pointer change.
- [x] No input, microphone, AI request, network call, or browser storage added
      — `homepage-interview-demo.js` grep-clean of `fetch(` / `XMLHttpRequest` /
      `localStorage` / `sessionStorage` / `indexedDB` / `document.cookie` /
      `getUserMedia` / `mediaDevices` / `MediaRecorder` / `SpeechRecognition` /
      `AudioContext`; the partial has no `<form>` / `<textarea>` / `<input>`.
- [x] Truth bar present on the poster and in the modal footer; no-JS behavior
      truthful.

## 8. Known limitations, risks, deferred work

- The modal is portaled to `<body>` inside a `home-v3` wrapper. Its palette is
  pinned paper-light so it stays consistent in dark theme; the primary button
  adopts the theme's gold (matching the poster) — intentional, not a defect.
- The walkthrough is intentionally static/fictional; any future
  personalization, analytics, or real-Studio convergence is a separate,
  not-yet-authorized initiative.
- Pre-existing unrelated `azure.storage` test gap in the borrowed venv is not
  this package's concern.
- `.claude/launch.json` remains machine-local (points at a borrowed venv for
  local runs) and is excluded from the commit via `skip-worktree`.

## 9. Rollback

Remove the one `{% include %}` line and the `<script>` tag from
`templates/homepage.html`; the partial, script, appended CSS, and tests go
inert. Standard path: `git revert` the squash-merge commit. No data, route, or
backend state exists to clean up.

## 10. Manager acceptance and release closeout

- **Owner acceptance:** Pete stated that he likes the demo and that it does what
  it is supposed to do. This acceptance applies to the current fixed,
  illustrative walkthrough.
- **Manager live visual acceptance:** Pass at desktop and 390px mobile. The
  poster opens the labelled modal; Question, Sample answer, Coaching review,
  and Improved retry all advance correctly; truth remains visible; the final
  action links to `/interview-studio`; and the 390px page has no document-level
  horizontal overflow.
- **Implementation:** exact source tip
  `90d035a25344c850e6ed732c1efb6e4d0a240787`.
- **Deployment:** Azure PR 86 completed with squash merge
  `a98cced519a1f853ad9f4462fd438efa67d6f260`. Automatic pipeline 122
  (`20260719.30`) passed for that exact merge. Automatic pipeline 123
  (`20260719.31`) also passed for descendant main
  `6cb49f135cc3a2749dd4539f8261d176b43dad9a`; the demo-owned paths are
  unchanged between those commits. Manual pipeline 124 (`20260719.32`) passed
  for the same descendant SHA and was redundant successful evidence, not a
  CI-trigger failure.
- **Live production:** `https://peerslate.com/` returned 200 and contained the
  walkthrough poster, modal marker, final Studio link, and versioned assets.
  `homepage-scenes.css?v=interview-demo-1` and
  `homepage-interview-demo.js?v=int-demo-1` each returned 200. The four-state
  flow was exercised against live production.
- **Infrastructure:** no schema, storage, identity, secret, or service change.
  This package is static frontend demonstration code only.
- **Historical worktree:** preserved at
  `C:\Users\peter\Documents\portfolio-home-interview-demo`; no cleanup,
  switching, stashing, or deletion was performed.

## 11. Required downstream action

This package is closed as the current illustrative demonstration. It does not
close the cross-product homepage projection contract. After the real public
Studio passes the complete 5A-light/5C-dark design, implementation, acceptance,
Azure release, and live-verification gates, create a fresh downstream branch
that maps the homepage walkthrough to that exact release. Replace the current
Voice-default emphasis and paper-light dark modal with the accepted product
hierarchy and theme treatments while preserving the fixed, fictional,
no-side-effect truth boundary. That later convergence requires its own exact
branch/SHA, visual acceptance, PR, pipeline, and live evidence.
