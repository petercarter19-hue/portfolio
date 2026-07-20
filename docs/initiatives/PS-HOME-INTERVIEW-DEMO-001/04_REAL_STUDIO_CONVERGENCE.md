# PS-HOME-INTERVIEW-DEMO-001 — 04: Real Studio Convergence Architecture

_PS-HOME-INTERVIEW-PARITY-001 writer architecture, 2026-07-20. Written by the
Claude Code writer before any product edit, per the activation package and
`01_CLAUDE_ARCHITECTURE_AND_IMPLEMENTATION_BRIEF.md`. This document explains
how to implement the accepted experience against the released Studio; it does
not redesign or weaken either. Product implementation starts only after
manager confirmation of this architecture._

## 1. Writer branch and base

| Item | Value |
|---|---|
| Package | `PS-HOME-INTERVIEW-PARITY-001` |
| Writer | Claude Code (sole writer) |
| Branch | `work/2026-07-20-home-interview-parity-001` |
| Base | Azure `origin/main` at `b7b674415f1f7c9ac2844fa0482091b62a7ec979` (PR 103 activation merge) |
| Worktree | `/Users/petercarter/Documents/Website/ps-home-interview-parity-001` — fresh, created from `origin/main` for this package |

## 2. Clean worktree state

At creation the worktree was clean at exactly the base SHA with zero unique
commits, tracking `origin/main`. `origin/main` was fetched and re-verified
immediately before creation and had not advanced past the activation merge.
The historical demo worktree, the manager activation worktree
(`ps-home-interview-parity-manager`, at `44761d4`), the primary Mac checkout,
and every other preserved worktree/stash/branch were left untouched. This
branch was not created from, and does not reuse, the deleted demo source
branch or the manager activation branch.

## 3. Released Studio manifest and verification

Verified 2026-07-20 (this session), directly against the local Azure clone and
live production — not only from the handoff transcription:

| Fact | Value | Verified how |
|---|---|---|
| Accepted implementation checkpoint | `39bc9a3f890ec8020eb84c4e3e416db6cd6912d2` | resolves locally; subject `PS-INTERVIEW: close Codex Conditional review corrections` |
| Final release source | `0aaf41768a33810b089f5fea3a66a5272e8b61d8` | **not resolvable locally** — expected: writer tip of a squash-merged, Azure-deleted branch; the merge SHA is the authoritative record (same pattern as the Photo sources) |
| Azure PR 101 squash merge | `39002f5130a1766d2090007c16582e0dbe07226c` | resolves on `main`; subject `PS-INTERVIEW: release accepted public Studio` |
| Release-governance PR 102 merge | `2e811f4eec3e915bdb6a0aefa7bd744d6bc7553b` | resolves on `main` |
| Activation PR 103 merge | `b7b674415f1f7c9ac2844fa0482091b62a7ec979` | current `origin/main`; this branch's base |
| Pipelines 149/150/151 | Build + Deploy passed | per package records on `main` (16_MANAGER_IMPLEMENTATION_ACCEPTANCE.md, PARITY README); not re-queried from Azure this session |
| Live `/interview-studio` | HTTP 200 | curl, this session |
| Live `/interview-studio/history` | HTTP 200 | curl, this session |
| Live asset signatures | `studio-5a5c-2` ×2, `ps-theme-001-2` ×1 in live Studio HTML | curl, this session |
| `Video Me` retired | zero occurrences in live Studio HTML | curl, this session |
| Homepage still pre-convergence | live `/` serves `homepage-scenes.css?v=interview-demo-1` and `homepage-interview-demo.js?v=int-demo-1` | curl, this session |

The last row is the gap this package closes: production homepage still runs
the accepted Voice-first, paper-modal walkthrough while the released 5A/5C
Studio is live.

## 4. Reserved-file map

Writable on this branch, exactly as activated:

| File | Bounded change |
|---|---|
| `templates/homepage.html` | Interview include and the two asset cache keys only (`?v=interview-demo-1` → `?v=interview-parity-1`; `?v=int-demo-1` → `?v=int-parity-1`) |
| `templates/partials/homepage/_interview_demo_scene.html` | poster, modal, four fixed states, truth copy, modal theme proxy |
| `static/css/homepage-scenes.css` | the bounded Interview scene/portal sections only; unrelated homepage selectors preserved byte-for-byte (one recorded exception, deviation D4) |
| `static/js/homepage-interview-demo.js` | deterministic modal/step/accessibility/inertness controller only |
| `tests/test_homepage_scenes.py` | `HomepageInterviewDemoTests` class updates/extensions only; `HomepageSceneTests` untouched |
| `docs/initiatives/PS-HOME-INTERVIEW-DEMO-001/04_REAL_STUDIO_CONVERGENCE.md` | this document |
| `docs/initiatives/PS-HOME-INTERVIEW-PARITY-001/**` completion documents | writer completion report |
| `artifacts/ps-home-interview-parity-001/**` | evidence |

Not touched, restated: the real Studio template/CSS/JS/tests/routes,
`base.html`, `theme-toggle.js`, auth/database code, Capture/Voice/Photo/Owner
Home/Placement, `auth_routes.py`, `owner_routes.py`, global navigation/tokens,
shared governance, deployment configuration.

Parallel-lane check at base: Owner Home frontend and Photo lifecycle work
reserve no file in the list above; no overlap exists. If another branch merges
to `main` while this branch is open, current `origin/main` is merged in
(never rebased) and all affected tests and browser evidence rerun.

## 5. Old-state → released-Studio-state parity matrix

The poster plus four modal steps project the released journey: orientation →
active written practice → processing → bottom-line review → improve/continue.
The step count stays **four** (handoff recommendation; no released-state
mismatch forces a change): the released 5-stage rail (Draft, Coaching request,
Review, Improve, Continue) maps 1:1 onto modal steps 1–4 with the Continue
stage carried by step 4's real-Studio CTA.

| Unit | Old (live) state | Released Studio authority it must project | Convergence action |
|---|---|---|---|
| Poster | Kicker, "Answer → understand → improve", fixed question card, listening line, truth bar, "Walk me through it" | Orientation (`PUBLIC-01`): "Real practice. Real coaching. Real growth.", one dominant Start Interview Me action, baseline "No sign-in. No account. No cloud history." | Keep poster shape and fixed question; reword orientation copy to written-first; keep truth bar; primary button stays the walkthrough trigger; ledger-card treatment in light, cinematic card in dark (D1) |
| Step 1 "Question" — **Voice-first** framing: Voice/Text toggle with `Voice (Default)`, "Voice is front and center in the real Studio" | **Stale.** Released `PUBLIC-02`: written composer is dominant ("Your answer" label, word count, transmit line, gold Submit answer); dictation is a quiet side-rail aid ("Start dictation… Dictation is optional.") | **Step 1 "Write your answer":** fixed written-answer surface presenting the existing fictional answer as a composed draft (no textarea/input/form — a styled static block); transmit-truth line quoted from the released Studio; dictation demoted to one optional-aid note; Voice/Text toggle removed (D2) |
| Step 2 "Sample answer" — "Illustrative voice transcript" chip, decorative waveform | **Stale framing.** Released `PUBLIC-03`: processing with answer preserved — "Preparing your coaching review / The submitted answer remains visible…", coaching-status card rows pinned **row 1 done / row 2 current / row 3 pending**: **Answer received / Checking the question rubric / Preparing bottom-line feedback** | **Step 2 "Submit for coaching":** same fixed answer shown preserved (verbatim repeat), static three-row coaching-status sequence pinned to the exact released row states and verbatim supporting copy (§6), explanation that the real Studio sends the question and answer only after explicit submit; waveform and voice-transcript chips removed |
| Step 3 "Coaching review" — bottom line, What worked / Improve next, STAR tiles | Aligned in shape. Released `PUBLIC-04` hierarchy: "Bottom line first.", verdict, score ring + **"Practice signal — not an employer prediction"**, "What worked well", "Improve next time", "Framework map · STAR" | **Step 3 "Bottom line first":** adopt released headings verbatim; add fixed score ring (D3); keep existing fixed verdict/bullets/STAR content (already coherent with the fictional answer); practice-signal caption always visible |
| Step 4 "Improved retry" — original vs improved compare, change tiles, CTA | Aligned in shape. Released improve panel: "Keep your voice. Strengthen the proof.", Original answer / Improved draft compare, "What changed" | **Step 4 "Improve and practice again":** adopt released heading language; keep the fixed original/retry pair verbatim (accepted fictional content, §2.6 of the boundary contract including the owner copy corrections); keep change tiles; CTA "Practice this question in Interview Studio" → `/interview-studio` unchanged |
| Modal chrome | Step rail `Question / Sample answer / Coaching review / Improved retry`; white card both themes | Released stage rail semantics (`aria-current="step"`, done states) and the two theme expressions | Rail labels become **Write your answer / Submit for coaching / Bottom line / Improve & retry**; `aria-current`/done semantics kept; dark modal becomes Cinematic Studio (§7) |

Fixed fictional content **retained verbatim**: the question, the listening
line, the sample answer, the improved retry (with its owner-corrected ending),
the change tiles, and the What worked / Improve next bullets. They are
accepted, attribution-free, truthful, and nothing in the released Studio
contradicts them. Only framing (voice-first), structure labels, and missing
released elements (status rows, score, headings) change.

## 6. Semantic DOM and deterministic state controller

### DOM (server-rendered, one DOM for both themes)

The accepted shell is preserved exactly in structure:

```
section.hv-interview[data-home-interview-demo]
├─ .hv-interview__copy            editorial column (updated copy)
├─ article.hv-int-poster          poster: kicker, title, question card,
│                                 truth bar, [data-int-open] + no-JS link
└─ .hv-int-overlay[data-int-overlay][hidden]     (portaled to body on init)
   └─ section.hv-int-modal[role=dialog][aria-modal=true]
      ├─ header: kicker, title, step count [data-int-count],
      │   theme proxy button (below), close [data-int-close]
      ├─ ol.hv-int-steps          4 × button[data-int-step="1..4"]
      ├─ p[role=status][data-int-live]            single live region
      ├─ .hv-int-modal__body      4 × section[data-int-state="1..4"],
      │                           2–4 ship `hidden`; each leads with
      │                           h3.hv-int-state__title[tabindex="-1"]
      └─ footer: truth strip (accessible — see correction below),
          Back / Next / Finish controls
```

**Correction — modal truth strip accessibility.** The current released markup
at `templates/partials/homepage/_interview_demo_scene.html:287` sets
`aria-hidden="true"` on the modal footer's `.hv-int-modal__truth` block. That
was tolerable only because the on-page poster's own truth bar (`hv-int-
truthbar`) remained in the accessibility tree as a redundant source. Once
background inertness (§6 below) makes the entire poster — including its
truth bar — inaccessible while the modal is open, `aria-hidden="true"` on the
modal's own truth strip would leave assistive-technology users with **no**
accessible truth statement anywhere in the open dialog. This is corrected:
**`aria-hidden="true"` is removed from `.hv-int-modal__truth`.** It renders as
a normal, perceivable footer element in both themes; no other attribute on
that block changes.

New within-state structures project released components with demo-scoped
classes (never `is__*`, so demo and Studio styles can never collide):

- Step 1: `.hv-int-composer` — "Your answer" label row, static answer block
  (`<div>`, not a form control), word-count/meta line, transmit-truth line,
  demo-honest primary advance; `.hv-int-aid` one-line optional-dictation note.
- Step 2: `.hv-int-preserved` — preserved-answer card ("Your submitted answer ·
  preserved" pattern); `.hv-int-status` — three static
  `.hv-int-status-row`s in a fixed, pinned state (this is a walkthrough of
  the moment just after submission, not a live progression): **row 1 done**,
  **row 2 current**, **row 3 pending**. Each row transcribes its released
  supporting line verbatim from `templates/interview_studio.html:427-441`:
  - Row 1 (done, ✓): **Answer received** — "The submitted text is attached
    to this coaching request."
  - Row 2 (current): **Checking the question rubric** — "Reviewing
    relevance, structure, specificity, and result."
  - Row 3 (pending): **Preparing bottom-line feedback** — "Feedback appears
    only when the complete review is ready."
- Step 3: `.hv-int-bottomline` (kept) + `.hv-int-score` fixed ring +
  `.hv-int-ring-caption` practice-signal caption + existing review columns and
  STAR grid.
- Step 4: existing compare/changes structure, released heading language.

The modal header gains the Studio's **exact** released proxy composition —
not only the `role="switch"`/`aria-checked` attribute contract, but the full
visible markup, transcribed verbatim from the released reference at
`templates/interview_studio.html:823` (the Queue/Settings/History-detail
dialog proxies):

```html
<button class="theme-toggle hv-int-theme" type="button" role="switch"
        aria-checked="false" aria-label="Dark theme" title="Dark theme"
        data-theme-toggle-proxy>
    <span class="hv-int-theme-label">Theme</span>
    <span class="theme-toggle__track" aria-hidden="true">
        <span class="theme-toggle__thumb"></span>
    </span>
</button>
```

The visible `Theme` label span (`hv-int-theme-label`, mirroring the Studio's
`is__dialog-theme-label`) and the `theme-toggle__track`/`theme-toggle__thumb`
spans are load-bearing, not decorative shorthand — they are what makes the
proxy visually legible as a theme switch rather than an unlabeled icon
button, matching the released Studio dialogs exactly. `hv-int-theme` is the
demo-scoped modifier class (parallel to the Studio's `is__dialog-theme`); the
base `theme-toggle` class is what `theme-toggle.js` and its existing CSS
already style, so the proxy inherits correct visual treatment in both themes
with zero new CSS beyond the demo-scoped modifier's placement rules.

`static/js/theme-toggle.js` (v `ps-theme-001-2`, loaded by `base.html` on every
page) discovers `[data-theme-toggle-proxy]` at init, binds it, and keeps all
switches synchronized. The proxy exists in server HTML at load, so no dynamic
registration is needed; portaling moves the element without breaking its
listener. **The demo controller contains zero theme logic**, mirroring the
Studio's theme-agnostic architecture.

### Controller (`homepage-interview-demo.js`)

Retained: module IIFE, double-init guard, portal-to-body (the
`main.main-content` `isolation: isolate` stacking-context fix), `go(n)` with
`hidden`-toggling, `aria-current`/`data-done` rail updates, single live-region
announcement per transition, focus-to-heading on step change, focus trap,
Escape/close/backdrop close, focus restoration to the invoker, body scroll
lock.

Removed: `setMethod()` and every method-toggle reference (D2).

Added — **background inertness** (the one behavioral correction the handoff
orders): on open, for each child of `document.body` except the portal wrapper
(and `script`/`style`/`template` nodes), set the `inert` attribute **only if
the element was not already inert**, recording each element actually changed;
on close, remove `inert` from exactly the recorded set and clear it. This
restores prior state exactly, is idempotent, uses no timers or observers, and
makes the sticky global header (including the header theme switch)
non-interactive while the dialog is open — which is precisely why the
modal-local proxy exists. The focus trap is retained as a belt-and-suspenders
layer for browsers with partial `inert` support.

Prohibited-API contract unchanged and re-asserted by tests: no `fetch`,
`XMLHttpRequest`, `sendBeacon`, `WebSocket`, `EventSource`, storage of any
kind, cookies, forms/inputs, microphone/camera/speech/media APIs, timers,
observers, or animation frames. The controller manages only modal
presentation, steps, accessibility attributes, inertness, and fixed state.

### Theme-switch state retention

Theme is applied entirely through `body[data-theme]` token overrides; the demo
controller neither observes nor reacts to it, and no DOM is recreated on
switch. Open modal, current step, fixed answer, focused control (the proxy
itself), and scroll positions are therefore structurally preserved — proven,
not assumed, by the browser-evidence plan (§10). The known pre-existing
sitewide ~20–60px scroll drift on theme toggle is out of scope (it lives in
the shared controller, not here) and is recorded as an expected observation,
not a regression.

## 7. Light and dark token/component mapping

The production Studio stylesheet is **not** imported and no `is__*` selector
is reused. Instead, the bounded Interview section of `homepage-scenes.css`
defines demo-scoped custom properties (`--hvi-*`) on the two demo roots
(`.home-v3 .hv-interview`, `.home-v3 .hv-int-portal`), with values transcribed
from the released Studio token layer — the same
token-values-only-under-`body[data-theme="dark"]` architecture the Studio
uses. No new global token, second theme system, or `theme-toggle.js` change.

| Semantic token | Light — Editorial Studio Ledger (released value) | Dark — Cinematic Studio (released value) |
|---|---|---|
| canvas | `#fbf8f2` | `#03101d` |
| canvas-2 | `#fffdfa` | `#071a2b` |
| surface | `#fffefa` | `#091827` |
| surface-2 | `#f7f1e7` | `#0c2235` |
| ink (headings) | `#0c2345` | `#f4efe6` |
| text | `#283b58` | `#d7dde6` |
| text-muted | `#60708a` | `#9facbd` |
| gold-text | `#8A5A00` | `#d99a2b` |
| gold | `#B87900` | `#d99a2b` |
| gold-bright | `#d2a24b` | `#f1bd5c` |
| gold-soft | `#f6e9c9` | `rgb(217 154 43 / 12%)` |
| line | `#d9d1c4` | `rgb(207 159 70 / 26%)` |
| line-strong | `#c9bca9` | `rgb(207 159 70 / 42%)` |
| action-primary | `#0d356d` | `#f4bd58` |
| action-primary-strong | `#092954` | `#d79220` |
| action-primary-text | `#ffffff` | `#101722` |
| focus | `#0b2f62` | `#f1bd5c` |
| success | `#1E725F` | `#54b696` (fills pinned to `#1E725F` where a white glyph sits on them — the Studio's measured 5.79:1 correction is inherited, not re-derived) |
| overlay (backdrop) | `rgb(10 27 54 / 30%)` | `rgb(0 0 0 / 55%)` |

Component mapping:

- **Light modal** = ledger paper: warm `#fbf8f2` canvas, `#fffefa` cards, fine
  warm rules, Newsreader headings (already the homepage serif), navy actions,
  sparse gold accents, quiet STAR/review cards. Recognizably the released
  light Studio compressed into the bounded walkthrough; the Studio's right
  rail (status card, aid, demo profile) is represented by the step-2 status
  card and the step-1 aid note rather than copied wholesale.
- **Dark modal** = cinematic: layered `#03101d`/`#071a2b` canvas, `#091827`
  navy card surfaces, fine gold rules at the released alpha values, gold
  primary action with dark text, gold current-step and answer-focus
  treatment, readable `#d7dde6` text with `#9facbd` muted-blue secondary copy,
  restrained shadow depth (`0 24px 64px rgb(0 0 0 / 35%)` class of values).
  **No white paper surface anywhere in the dark modal.** The backdrop keeps
  its dim+blur but at the dark overlay value.
- **Focus outlines**: 3px, navy in light / gold in dark — the released focus
  contract.
- Contrast: every text/control/focus pairing uses released, already-measured
  Studio pairs; any demo-specific composite not present in the Studio will be
  measured and recorded in the completion report.

The current dark-mode treatment (scene as a light "paper band" with a
paper-white modal) is exactly the recorded stale state and is replaced. Band
treatment of the **poster** is deviation D1 (§11) and awaits the manager's
choice; the modal treatment above is fixed by the handoff and not optional.

## 8. Modal, inertness, focus, theme-switch, responsive, reduced-motion, no-JS

| Behavior | Contract |
|---|---|
| Trigger | Bounded poster button `[data-int-open]`, JS-gated, unchanged |
| Portal | Overlay portaled to `body` inside `.home-v3.hv-int-portal`, unchanged |
| Open | Backdrop dim+blur, `is-open` class, body scroll lock, background inert (§6), focus to step-1 heading |
| Close | Escape, close button, backdrop click; inert removed exactly; scroll restored; focus returned to invoker |
| Focus | Trap retained; every interactive control ≥44px; visible focus outline both themes |
| Theme switch in modal | Only via the modal proxy (header switch is inert); preserves open dialog, step, fixed answer, focused control, scroll (§6); both switch states stay synchronized via the shared controller |
| Live region | Single `role="status"`, one announcement per step change ("Step n of 4: <name>"), empty at load |
| Responsive | Desktop dialog; ≤~640px bottom-sheet presentation retained; content reflows and scrolls internally (`max-height` cap, never fixed height); no page-level horizontal overflow at 390px/844px-landscape/200% |
| Reduced motion | All transitions instant under `prefers-reduced-motion: reduce` (existing blanket `.home-v3 *` rule retained; no new animation depends on motion) |
| No-JS | Poster (question + truth bar + written-first copy) fully server-rendered; controls hidden; `.hv-int-nojs` normal link "Open Interview Studio" shown; modal can never open |
| Long content | Longest state (step 3) scrolls within the modal at 390×844 and at 200% zoom without clipping the truth strip or actions |

## 9. Truth-copy inventory and banned claims

### Pinned strings (exact, both themes, server-rendered)

Demo-boundary truth (retained):

1. Truth bar (poster and modal footer): `Fictional example` · `No visitor
   input` · `No AI request` · `No answer or practice data stored`. (Corrected
   from `Nothing stored`: the modal theme proxy invokes the shared global
   theme controller, which legitimately writes the `ps-theme` preference to
   `localStorage` — see `static/js/theme-toggle.js` lines 22–23. The absolute
   claim would be false the moment the proxy exists; the corrected claim is
   true and matches the actual scope of what the demo protects.)
2. Editorial checklist item 1: `Fictional answer—not Pete's and not the
   visitor's.` (retained; the walkthrough content itself never names Pete).
3. Editorial checklist item 2: `No microphone, AI request, draft, attempt,
   history, or media storage.` (retained).
4. Editorial checklist item 3: `The final action opens the real public
   Interview Studio.` (retained).
5. Step-1 inline note: `Illustrative only. The next step shows this fixed
   sample submitted for coaching. No visitor response is captured.`
6. Step-3 inline note: `Fixed walkthrough coaching. No AI request or profile
   history is used.` (retained).

Released-Studio truth (replacing the Voice-first set — each maps to live
Studio copy):

7. Scene lede (replaces `Voice first. Text always available. …`): `Write your
   answer in your own words. One realistic question, clear coaching, and one
   stronger retry.`
8. Step-1 transmit line (verbatim released copy, presented as what the real
   Studio does): `In the real Studio, questions and your answers are sent to
   PeerSlate only when you click Submit answer for coaching.`
9. Step-1 aid note (mirrors the released aid card): `Dictation is optional in
   the real Studio — speak and it transcribes into the answer box. Written
   practice comes first.`
10. Step-2 status rows, pinned **row 1 done / row 2 current / row 3 pending**,
    verbatim released copy (`templates/interview_studio.html:427-441`):
    `Answer received` — "The submitted text is attached to this coaching
    request."; `Checking the question rubric` — "Reviewing relevance,
    structure, specificity, and result."; `Preparing bottom-line feedback` —
    "Feedback appears only when the complete review is ready."
11. Step-2 explanation: `The real Studio sends your question and answer only
    after you explicitly submit. This walkthrough sends nothing.`
12. Step-3 score ring: pinned to **72/100** (D3), `role="img"`,
    `aria-label="Overall interview score: 72 out of 100"`, with the caption
    (verbatim, always visible): `Practice signal — not an employer
    prediction`.
13. Step-4 footer note: `Ready for real practice. Open the full public Studio
    to write your answer and submit for real coaching.` (de-voiced from the
    current `answer by voice or text` line).
14. Browser-local truth where History/drafts are mentioned (poster orientation
    line): `Practice stays in your browser until you submit an answer for
    coaching.` (released orientation copy).

Retained fixed fictional content: question, listening line, sample answer,
improved retry, change tiles, review bullets, STAR tiles — all verbatim from
the accepted boundary contract §2 including both owner copy corrections
(`capture, to presentation, to practice`; no `repeatable review process`
claim).

Step rail labels: `Write your answer` / `Submit for coaching` / `Bottom line`
/ `Improve & retry`. Advance labels: step 1 → `Submit sample answer` (the
accepted demo-honest form; never bare `Submit answer`); step 2 → `Show the
bottom line`; step 3 → `Show the improved retry`. Final CTA (unchanged):
`Practice this question in Interview Studio` → `url_for('interview_studio')`.

### Banned claims (asserted by tests where string-testable)

Stale voice-first framing: `Voice first`, `Voice is front and center`,
`Illustrative voice transcript`, `Default` as a voice-method tag, the
Voice/Text method toggle. Identity/persistence: any of `signed in`,
`your history`, `Use my history`, `saved to your account`, login, private
cloud history, account sync, saved results. Capability: media upload or
analysis, Capture, Moment, Placement, Story or résumé edits, sharing,
publication, `/app/interview-studio`. The demo also never claims to store a
draft, send a request, or accept input.

## 10. Automated tests and browser-evidence plan

### Automated (`tests/test_homepage_scenes.py`, demo class only)

Updated: method-switch tests removed with the toggle; state-name/label
assertions updated; voice-first strings move to the banned list.

Retained: four-state server-render with 2–4 `hidden`; no
`<form>`/`<textarea>`/`<input>` in scene; no network/storage/media APIs in the
JS source; truth bar server-rendered; single-`Pete` attribution rule; final
CTA resolution; button `type="button"`; step-rail `aria-current` uniqueness;
empty live region; focus-target headings; modal dialog semantics; JS-gated
trigger; poster no-JS completeness; reduced-motion coverage; no
fixed-viewport-height lock; `[hidden]`-vs-`display` companion rules.

New: (a) written-primary copy present, voice-first strings absent; (b) three
coaching-status rows present in step 2 with released row copy; (c)
`Practice signal — not an employer prediction` present; (d) modal theme proxy
present with `role="switch"`, `aria-checked`, `data-theme-toggle-proxy`, and
exactly one per scene; (e) JS source contains the inert set/restore logic and
still no banned API; (f) `body[data-theme="dark"]` demo token override block
exists and contains the cinematic canvas value, and the demo's dark modal
rules contain no white/paper surface value; (g) `homepage.html` carries the
two new cache keys and no stale `int-demo-1`/`interview-demo-1` reference;
(h) unrelated scene markers (`hv-hero`, `hv-resume`, `hv-story`, `hv-invite`)
still untouched.

Runs: focused `tests.test_homepage_scenes`; the governance/site-rule suites;
the complete configured repository suite; bundled-Node `--check` on the demo
JS; `git diff --check`; complete-diff review against
`b7b674415f1f7c9ac2844fa0482091b62a7ec979`.

### Browser evidence (`artifacts/ps-home-interview-parity-001/`)

Both themes, desktop 1440×900 and mobile 390×844: poster, step 1, step 2,
step 3, step 4 (20 primary captures). Plus: mobile landscape 844×390; 200%
reflow; visible keyboard focus; **theme switch inside the open modal** with
step/answer/focus/scroll retained (before/after pairs, both directions);
**background inertness** (header and page controls unreachable while open;
restored on close); reduced motion; long content; no-JavaScript poster and
fallback link; no page-level horizontal overflow; browser console clean.
Side-by-side comparison shots against the released Studio implementation
evidence in `artifacts/ps-interview-public-gate-001/implementation-evidence/`
for: orientation vs poster, PUBLIC-02 vs step 1, PUBLIC-03 vs step 2,
PUBLIC-04 vs step 3, improve panel vs step 4 — light and dark. An
`EVIDENCE_INDEX.md` maps every item above to its file.

## 11. Intended deviations register

| # | Deviation | Reason | Status |
|---|---|---|---|
| D1 | **Poster dark treatment.** In dark theme the poster card renders as a cinematic navy/gold Studio card while the surrounding scene band keeps the homepage's existing dark-mode band alternation (currently a light paper band). | The handoff's hard "no paper floating over the dark homepage" requirement names the modal; the poster must still read as the released product in dark. Restyling the card, not the band, converges the product object without redesigning homepage rhythm. | **Approved as recommended** |
| D2 | Voice/Text method toggle removed; replaced by a static optional-dictation aid note. | The toggle's `Voice (Default)` framing is the exact stale claim this package retires; the released Studio has no such switch — dictation is a quiet optional aid. Removing it also removes two demo-only interactive controls that existed to present a retired model. | Approved |
| D3 | Fixed score ring added to step 3, pinned to **72/100**. The ring carries `role="img"` and `aria-label="Overall interview score: 72 out of 100"`, plus the mandatory `Practice signal — not an employer prediction` caption always visible beside it. | The released PUBLIC-04 hierarchy leads with verdict + score + practice-signal disclaimer; a review state without it would not be recognizably the released review. 72 is fixed, fictional, mid-range (consistent with the accepted review copy: strong ownership/coordination, one improvable dimension), and labeled exactly as required. | **Approved — value pinned** |
| D4 | Bounded exception to byte-for-byte preservation: the released dark-band CSS groups `.hv-resume`, `.hv-story`, and `.hv-interview` in shared selector lists; converging the Interview scene requires removing `.hv-interview` from those grouped selectors. | The other scenes' rules remain textually present and functionally identical; only the Interview membership changes. A pure-addition approach would leave conflicting stale rules fighting new ones on specificity. | Approved |
| D5 | Advance-button labels are demo-honest variants (`Submit sample answer`, not `Submit answer`). | A control labeled exactly as the real submission action would overclaim inside a walkthrough that sends nothing; this follows the accepted demo pattern. | Approved |
| D6 | Modal-local theme proxy added using the released `data-theme-toggle-proxy` mechanism and the Studio's exact proxy markup, including the visible `Theme` label plus track/thumb spans (§6). | Ordered by the handoff; mirrors the Studio's D22 acceptance correction (header switch is unavailable during a properly modal interaction). No `theme-toggle.js` change needed — the proxy contract is already released. | Ordered by handoff; markup pinned |
| D7 | Background regions programmatically `inert` while the modal is open, restored exactly on close (previously scroll-lock + focus trap only). | Ordered by the handoff as the background-contract correction. | Ordered by handoff |
| D8 | Editorial-column lede and orientation copy rewritten from voice-first to written-first. | Scene copy is inside the reservation; the old lede is a retired product claim. | Approved |
| D9 | Step rail labels renamed to the converged journey names. | The old names described the voice-era journey; the new names mirror the released stages. | Approved |
| D10 | Truth-bar corrected string: `No answer or practice data stored` replaces `Nothing stored` in both the poster and modal truth strips. | The modal theme proxy invokes the shared global controller, which writes `ps-theme` to `localStorage` (`static/js/theme-toggle.js:22`); the absolute claim would be false once the proxy exists. | Manager-required correction |
| D11 | `aria-hidden="true"` removed from the modal footer's `.hv-int-modal__truth` block (currently present at `_interview_demo_scene.html:287`). | Background inertness (§6, D7) makes the poster's own truth bar inaccessible while the modal is open; leaving the modal's truth strip `aria-hidden` would leave no accessible truth statement anywhere in the open dialog. | Manager-required correction |

No other deviation is intended. If implementation discovers that any change
requires a file outside §4, work stops for a manager reservation before that
file is touched.

## 12. Manager review disposition — 2026-07-20

Conditionally approved. D1 approved as recommended: cinematic navy/gold
poster card in dark theme; the surrounding scene band keeps the homepage's
existing light paper-band alternation. All other deviations (D2, D4–D9)
approved. Five required documentation corrections applied in this revision
before any product edit: the truth-strip wording (D10), modal truth-strip
accessibility (D11), the D3 score pinned to 72/100 with its `role="img"`
label, the exact modal theme-proxy composition (D6, including the visible
`Theme` label and track/thumb spans), and the pinned Step 2 row states with
verbatim released supporting copy. `origin/main` advanced to
`5217247d811d81af6ca92504dda62d9a2c756563` during review (Owner Home
governance/package files and `tests/test_governance_pointers.py` only, no
reserved-file overlap) and was merged into this branch, not rebased.

---

_Architecture approved with the corrections above. No product file has been
edited on this branch. Product implementation may proceed without a further
architecture stop._
